#!/usr/bin/env python3
"""Validate catalog metadata and optionally probe resource URLs without executing them."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog"
ALLOWED_FORMATS = {
    "vod-single": {"tvbox-json"},
    "vod-multi": {"tvbox-multi"},
    "live": {"m3u", "txt", "tvbox-live-json"},
    "epg": {"epg-xml", "logo-library"},
    "tools": {"documentation", "utility"},
}
CLIENT_STATES = {"unknown", "format-claimed", "import-tested", "playback-tested", "incompatible"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
MAX_BODY = 512 * 1024
TIMEOUT = 12


def fail(errors: list[str], where: str, message: str) -> None:
    errors.append(f"{where}: {message}")


def is_http_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urllib.parse.urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname) and not parsed.username and not parsed.password and parsed.port != 0
    except ValueError:
        return False


def validate_public_target(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname
    if not host:
        raise ValueError("URL has no hostname")
    try:
        import ipaddress
        import socket
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)}
        if not addresses or any(not ipaddress.ip_address(address.split("%", 1)[0]).is_global for address in addresses):
            raise ValueError("URL resolves to a non-public network address")
    except (OSError, ValueError) as exc:
        raise ValueError("URL hostname did not resolve to a safe public address") from exc


def load_json(path: Path, errors: list[str]):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(errors, str(path.relative_to(ROOT)), f"cannot read JSON: {exc}")
        return None


def validate_catalog(errors: list[str]) -> list[tuple[str, dict]]:
    clients_doc = load_json(CATALOG / "clients.json", errors)
    clients: set[str] = set()
    if isinstance(clients_doc, dict) and isinstance(clients_doc.get("clients"), list):
        for client in clients_doc["clients"]:
            if isinstance(client, dict) and isinstance(client.get("id"), str):
                clients.add(client["id"])
    else:
        fail(errors, "catalog/clients.json", "expected an object with a clients array")

    seen: set[str] = set()
    entries: list[tuple[str, dict]] = []
    required = {"id", "name", "url", "format", "source", "license", "notes", "clients"}
    for category, formats in ALLOWED_FORMATS.items():
        path = CATALOG / f"{category}.json"
        doc = load_json(path, errors)
        if not isinstance(doc, list):
            fail(errors, str(path.relative_to(ROOT)), "expected a JSON array")
            continue
        for index, entry in enumerate(doc):
            where = f"{path.relative_to(ROOT)}[{index}]"
            if not isinstance(entry, dict):
                fail(errors, where, "expected an object")
                continue
            missing = required - entry.keys()
            if missing:
                fail(errors, where, f"missing keys: {', '.join(sorted(missing))}")
            allowed = required | {"fallback_urls"}
            extra = entry.keys() - allowed
            if extra:
                fail(errors, where, f"unexpected keys: {', '.join(sorted(extra))}")
            fallback_urls = entry.get("fallback_urls", [])
            if not isinstance(fallback_urls, list) or any(not isinstance(url, str) or not is_http_url(url) for url in fallback_urls):
                fail(errors, where, "fallback_urls must be an array of credential-free http(s) URLs")
            elif len(set(fallback_urls)) != len(fallback_urls) or entry.get("url") in fallback_urls:
                fail(errors, where, "fallback_urls must be unique and different from url")
            entry_id = entry.get("id")
            if not isinstance(entry_id, str) or not ID_RE.fullmatch(entry_id):
                fail(errors, where, "id must match ^[a-z0-9][a-z0-9-]{1,63}$")
            elif entry_id in seen:
                fail(errors, where, f"duplicate id: {entry_id}")
            else:
                seen.add(entry_id)
            for field in ("url", "source"):
                if not is_http_url(entry.get(field)):
                    fail(errors, where, f"{field} must be an http(s) URL without embedded credentials")
            if entry.get("format") not in formats:
                fail(errors, where, f"format must be one of: {', '.join(sorted(formats))}")
            for field in ("name", "license", "notes"):
                if not isinstance(entry.get(field), str) or (field != "notes" and not entry[field].strip()):
                    fail(errors, where, f"{field} must be a non-empty string" if field != "notes" else "notes must be a string")
            mapping = entry.get("clients")
            if not isinstance(mapping, dict) or not mapping:
                fail(errors, where, "clients must be a non-empty object")
            else:
                unknown = mapping.keys() - clients
                if unknown:
                    fail(errors, where, f"unknown clients: {', '.join(sorted(unknown))}")
                for client_id, result in mapping.items():
                    if not isinstance(result, dict) or set(result) != {"status", "tested_version", "tested_at"}:
                        fail(errors, where, f"clients.{client_id} must contain status, tested_version, tested_at")
                        continue
                    if result.get("status") not in CLIENT_STATES:
                        fail(errors, where, f"clients.{client_id}.status is invalid")
                    tested_at = result.get("tested_at")
                    if tested_at is not None:
                        try:
                            dt.date.fromisoformat(tested_at)
                        except (TypeError, ValueError):
                            fail(errors, where, f"clients.{client_id}.tested_at must be YYYY-MM-DD or null")
                    if result.get("status") in {"import-tested", "playback-tested"} and (not result.get("tested_version") or not tested_at):
                        fail(errors, where, f"clients.{client_id} tested states require tested_version and tested_at")
            entries.append((category, entry))
    return entries


class PublicRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        if not is_http_url(new_url):
            raise ValueError("redirected to a non-http(s) URL")
        validate_public_target(new_url)
        if len(getattr(request, "redirect_history", [])) >= 4:
            raise ValueError("too many redirects")
        return super().redirect_request(request, response, code, message, headers, new_url)


def fetch_bounded(url: str, opener=None) -> tuple[bytes, str, int]:
    validate_public_target(url)
    request = urllib.request.Request(url, headers={"User-Agent": "tvbox-resource-catalog-check/1.0", "Accept": "*/*"})
    with (opener.open(request, timeout=TIMEOUT) if opener else urllib.request.urlopen(request, timeout=TIMEOUT)) as response:
        final = urllib.parse.urlparse(response.geturl())
        if final.scheme not in {"http", "https"}:
            raise ValueError("redirected to a non-http(s) URL")
        body = response.read(MAX_BODY + 1)
        if len(body) > MAX_BODY:
            raise ValueError(f"response exceeded {MAX_BODY} bytes")
        return body, response.headers.get_content_type(), response.status


def validate_remote(category: str, entry: dict, opener=None) -> str:
    body, _content_type, status = fetch_bounded(entry["url"], opener=opener)
    if not 200 <= status < 300:
        raise ValueError(f"HTTP status {status}")
    fmt = entry["format"]
    if fmt == "tvbox-multi":
        doc = json.loads(body.decode("utf-8-sig"))
        if not isinstance(doc, dict) or not isinstance(doc.get("urls"), list) or not doc["urls"]:
            raise ValueError("multi-repository JSON must contain a non-empty urls array")
        for index, item in enumerate(doc["urls"]):
            if not isinstance(item, dict) or not isinstance(item.get("url"), str) or not is_http_url(item["url"]):
                raise ValueError(f"urls[{index}] must contain an absolute http(s) url")
    elif fmt == "tvbox-json":
        doc = json.loads(body.decode("utf-8-sig"))
        if not isinstance(doc, dict):
            raise ValueError("TVBox single-source config must be a JSON object")
        if not any(key in doc for key in ("sites", "urls", "lives")):
            raise ValueError("JSON object has none of the expected TVBox fields: sites, urls, lives")
    elif fmt == "tvbox-live-json":
        doc = json.loads(body.decode("utf-8-sig"))
        if not isinstance(doc, dict) or not isinstance(doc.get("lives"), list):
            raise ValueError("TVBox live JSON must contain a lives array")
    elif fmt == "m3u":
        text = body.decode("utf-8-sig", errors="strict")
        if not text.lstrip().startswith("#EXTM3U") or "#EXTINF" not in text:
            raise ValueError("M3U should begin with #EXTM3U and contain #EXTINF")
    elif fmt == "txt":
        text = body.decode("utf-8-sig", errors="strict")
        if not any("," in line and line.strip() for line in text.splitlines()):
            raise ValueError("TXT playlist contains no recognizable channel lines")
    elif fmt == "epg-xml":
        root = ET.fromstring(body)
        if root.tag not in {"tv", "tv-programme", "programme"}:
            raise ValueError(f"unexpected XML root element: {root.tag}")
    elif fmt in {"logo-library", "documentation", "utility"}:
        if not body:
            raise ValueError("response body is empty")
    return "ok"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-urls", action="store_true", help="make bounded HTTP requests to catalog URLs")
    parser.add_argument("--report", type=Path, help="write JSON probe report to this path")
    args = parser.parse_args()

    errors: list[str] = []
    entries = validate_catalog(errors)
    probes = []
    if args.check_urls:
        opener = urllib.request.build_opener(PublicRedirectHandler())
        for category, entry in entries:
            try:
                validate_remote(category, entry, opener=opener)
                probes.append({"id": entry.get("id"), "status": "ok", "checked_at": dt.datetime.now(dt.timezone.utc).isoformat()})
            except (OSError, urllib.error.URLError, TimeoutError, ValueError, UnicodeError, json.JSONDecodeError, ET.ParseError) as exc:
                probes.append({"id": entry.get("id"), "status": "failed", "error": str(exc), "checked_at": dt.datetime.now(dt.timezone.utc).isoformat()})

    for message in errors:
        print(f"ERROR {message}", file=sys.stderr)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        report = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "probes": probes}
        temp = args.report.with_suffix(args.report.suffix + f".{os.getpid()}.tmp")
        try:
            temp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temp.replace(args.report)
        finally:
            temp.unlink(missing_ok=True)
    failed = sum(item["status"] == "failed" for item in probes)
    print(f"Catalog validation: {len(entries)} entries, {len(errors)} metadata errors, {len(probes)} URL probes, {failed} probe failures")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
