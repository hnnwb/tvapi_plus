#!/usr/bin/env python3
"""Refresh bounded availability evidence; never mirror or execute catalog resources."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import check_catalog  # noqa: E402

DEFAULT_REPORT = ROOT / "probe-report.json"
MAX_RETRIES = 2
RETRY_DELAY = 1.0
RETRYABLE_HTTP = {408, 425, 429, 500, 502, 503, 504}
SAFE_OPENER = urllib.request.build_opener(check_catalog.PublicRedirectHandler())
PROBE_ERRORS = (OSError, urllib.error.URLError, TimeoutError, ValueError, UnicodeError, json.JSONDecodeError, ET.ParseError, RuntimeError)


def load_previous(path: Path) -> dict:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot safely read previous status report: {exc}") from exc
    if not isinstance(doc, dict) or not isinstance(doc.get("probes"), list):
        raise ValueError("previous status report has an unexpected shape; refusing to overwrite it")
    return {item["id"]: item for item in doc["probes"] if isinstance(item, dict) and isinstance(item.get("id"), str)}


SECRET_QUERY = re.compile(r"(token|key|auth|signature|sig|password|passwd|secret|session|credential)", re.IGNORECASE)


def safe_endpoint(url: str) -> str:
    try:
        parsed = urllib.parse.urlsplit(url)
    except ValueError:
        return "invalid-endpoint"
    host = parsed.hostname or "invalid-host"
    if ":" in host:
        host = f"[{host}]"
    try:
        port = f":{parsed.port}" if parsed.port else ""
    except ValueError:
        port = ""
    path = parsed.path if len(parsed.path) <= 80 else parsed.path[:77] + "..."
    safe_path = urllib.parse.quote(urllib.parse.unquote(path), safe="/%:@-._~")
    safe_path = re.sub(r"(?i)(token|key|auth|signature|sig|password|passwd|secret)=([^/&]+)", r"\1=[REDACTED]", safe_path)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    safe_query = urllib.parse.urlencode([(key, "[REDACTED]" if SECRET_QUERY.search(key) else value) for key, value in query])
    return urllib.parse.urlunsplit((parsed.scheme, host + port, safe_path, safe_query, ""))


def scrub_error(exc: Exception, endpoints: list[str]) -> str:
    message = str(exc)
    for endpoint in sorted(endpoints, key=len, reverse=True):
        message = message.replace(endpoint, safe_endpoint(endpoint))
    message = re.sub(r"(?i)(token|key|auth|signature|sig|password|passwd|secret|session|credential)=([^&\s]+)", r"\1=[REDACTED]", message)
    message = re.sub(r"https?://[^\s'\"]+", lambda match: safe_endpoint(match.group(0)), message)
    return f"{type(exc).__name__}: {message[:240]}"


def probe_entry(category: str, entry: dict, previous: dict, retries: int = MAX_RETRIES, delay: float = RETRY_DELAY) -> dict:
    checked_at = dt.datetime.now(dt.timezone.utc).isoformat()
    endpoints = [entry["url"]]
    fallback_urls = entry.get("fallback_urls", [])
    if isinstance(fallback_urls, list):
        for candidate in fallback_urls:
            if isinstance(candidate, str) and candidate not in endpoints:
                endpoints.append(candidate)
    errors = []
    attempts = []
    for endpoint_index, url in enumerate(endpoints):
        for attempt in range(retries + 1):
            try:
                old_url = entry["url"]
                try:
                    entry["url"] = url
                    check_catalog.validate_public_target(url)
                    check_catalog.validate_remote(category, entry, opener=SAFE_OPENER)
                finally:
                    entry["url"] = old_url
                attempts.append({"endpoint": safe_endpoint(url), "attempt": attempt + 1, "result": "ok"})
                prior = previous.get(entry["id"], {})
                return {
                    "id": entry["id"], "status": "ok", "stale": False,
                    "checked_at": checked_at, "last_success_at": checked_at,
                    "configured_url": safe_endpoint(entry["url"]), "used_endpoint": safe_endpoint(url),
                    "used_fallback": endpoint_index > 0,
                    "attempts": attempts,
                    "previous_last_success_at": prior.get("last_success_at") or prior.get("checked_at"),
                }
            except PROBE_ERRORS as exc:
                retryable = (
                    not isinstance(exc, urllib.error.HTTPError)
                    and not (isinstance(exc, ValueError) and "response exceeded" in str(exc))
                ) or (isinstance(exc, urllib.error.HTTPError) and exc.code in RETRYABLE_HTTP)
                error_text = scrub_error(exc, endpoints)
                attempts.append({"endpoint": safe_endpoint(url), "attempt": attempt + 1, "result": "failed", "error": error_text})
                errors.append(f"{safe_endpoint(url)}: {error_text}")
                if not retryable or attempt == retries:
                    break
                time.sleep(delay * (attempt + 1))
    prior = previous.get(entry["id"], {})
    last_success = prior.get("last_success_at") or (prior.get("checked_at") if prior.get("status") == "ok" else None)
    return {
        "id": entry["id"], "status": "failed", "stale": bool(last_success),
        "checked_at": checked_at, "last_success_at": last_success,
        "configured_url": safe_endpoint(entry["url"]), "used_endpoint": None, "used_fallback": False,
        "attempts": attempts, "error": errors[-1] if errors else "no endpoint configured",
    }


def refresh(entries: list[tuple[str, dict]], previous: dict, retries: int = MAX_RETRIES, delay: float = RETRY_DELAY) -> dict:
    probes = [probe_entry(category, entry, previous, retries, delay) for category, entry in entries]
    return {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "schema_version": 2, "probes": probes}


def atomic_write(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    try:
        temp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--retries", type=int, default=MAX_RETRIES)
    parser.add_argument("--delay", type=float, default=RETRY_DELAY)
    args = parser.parse_args()
    if not 0 <= args.retries <= 5:
        parser.error("--retries must be between 0 and 5")
    if not 0 <= args.delay <= 30:
        parser.error("--delay must be between 0 and 30 seconds")
    metadata_errors: list[str] = []
    entries = check_catalog.validate_catalog(metadata_errors)
    if metadata_errors:
        print("\n".join(metadata_errors), file=sys.stderr)
        return 1
    try:
        previous = load_previous(args.report)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    report = refresh(entries, previous, retries=args.retries, delay=args.delay)
    atomic_write(args.report, report)
    failed = sum(item["status"] == "failed" for item in report["probes"])
    stale = sum(item["stale"] for item in report["probes"])
    print(f"Status refresh: {len(entries)} entries, {failed} currently failing, {stale} stale with prior success; plugins not executed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
