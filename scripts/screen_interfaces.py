#!/usr/bin/env python3
"""Bounded, non-executing screening of all type-1 CMS APIs in listed single configs."""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import sys
import re
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_single_sources as audit

DEFAULT_README = Path("/tmp/awesome-tvbox-current.md")
DEFAULT_CONFIG_AUDIT = Path("/tmp/tvapi-full-audit.json")
DEFAULT_OUTPUT = ROOT / "reports" / "interface-screening.json"
MAX_INTERFACES = 300
MAX_PER_CONFIG = 10000
MAX_RESPONSE = 256 * 1024


def key_for(api: str, index: int, used: set[str]) -> str:
    parsed = urllib.parse.urlsplit(api)
    raw = re.sub(r"[^A-Za-z0-9_-]+", "_", (parsed.hostname or "api").split(".")[0]).strip("_").lower() or "api"
    candidate = f"screen_{raw[:30]}_{hashlib.sha1(api.encode()).hexdigest()[:8]}"
    if candidate in used:
        candidate = f"{candidate}_{index}"
    used.add(candidate)
    return candidate


def collect(readme: str, config_report: dict) -> tuple[list[dict], list[dict], int]:
    sources = {x["url"]: x for x in audit.candidates(readme)}
    found: dict[str, dict] = {}
    config_errors = []
    parsed_configs = 0
    for result in config_report.get("results", []):
        config_info = result.get("config") or {}
        if config_info.get("result") != "tvbox-json-structural":
            continue
        try:
            config_url = config_info.get("url") or result["url"]
            config = audit.fetch_json_document(config_url, audit.MAX_CONFIG)
            sites = config.get("sites") if isinstance(config, dict) else None
            if not isinstance(sites, list):
                config_errors.append({"name": result.get("name"), "status": "invalid-structure"})
                continue
            parsed_configs += 1
        except Exception as exc:
            config_errors.append({"name": result.get("name"), "status": "refetch-failed", "error_type": type(exc).__name__})
            continue
        source_url = result.get("url") or config_info.get("url", "")
        source = sources.get(source_url)
        for site in sites[:MAX_PER_CONFIG]:
            if not isinstance(site, dict) or str(site.get("type")) != "1":
                continue
            api = audit.site_api_key(site, config_url)
            if not api:
                continue
            name = str(site.get("name") or api)[:100]
            row = found.setdefault(api, {"api": api, "name": name, "key": None, "config_origins": set()})
            if source:
                row["config_origins"].add(source["name"])
            if len(name) > len(row["name"]):
                row["name"] = name
    if len(found) > MAX_INTERFACES:
        raise ValueError(f"{len(found)} unique interfaces exceed safety cap {MAX_INTERFACES}")
    used: set[str] = set()
    rows = []
    for index, api in enumerate(sorted(found), 1):
        row = found[api]
        row["key"] = key_for(api, index, used)
        row["config_origins"] = sorted(row["config_origins"])
        rows.append(row)
    return rows, config_errors, parsed_configs


def test_interface(row: dict) -> dict:
    api = row["api"]
    started = time.monotonic()
    out = {**row, "tests": {}, "decision": "exclude", "screen_status": "not-tested"}
    try:
        parsed = urllib.parse.urlsplit(api)
        addresses = {item[4][0].split("%")[0] for item in __import__("socket").getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=__import__("socket").SOCK_STREAM)}
        if not addresses or any(not __import__("ipaddress").ip_address(address).is_global for address in addresses):
            out["screen_status"] = "blocked-policy"
            out["reason"] = "network policy rejected non-public DNS answer before request"
            out["elapsed_ms"] = round((time.monotonic() - started) * 1000)
            return out
    except Exception as exc:
        policy_block = isinstance(exc, ValueError) and "public" in str(exc)
        out["screen_status"] = "blocked-policy" if policy_block else "request-failed"
        out["reason"] = f"preflight: {type(exc).__name__}: {str(exc)[:160]}"
        out["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        return out
    out["screen_status"] = "tested"
    try:
        list_result = audit.api_probe(api, {"ac": "list", "pg": 1})
    except Exception as exc:
        out["screen_status"] = "request-failed"
        out["reason"] = f"CMS list request failed: {type(exc).__name__}"
        out["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        return out
    out["tests"]["list"] = {k: list_result.get(k) for k in ("ok", "http", "ms", "nonempty", "rows", "schema")}
    if not list_result.get("ok") or not list_result.get("nonempty"):
        out["reason"] = "CMS list did not return a non-empty parseable result"
        out["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        return out
    keyword = str((list_result.get("items") or [{}])[0].get("vod_name") or "")[:60]
    if not keyword:
        keyword = "电影"
    try:
        search = audit.api_probe(api, {"ac": "list", "wd": keyword, "pg": 1})
    except Exception as exc:
        out["screen_status"] = "request-failed"
        out["reason"] = f"CMS search request failed: {type(exc).__name__}"
        out["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        return out
    matches = search.get("items") or []
    out["tests"]["search"] = {k: search.get(k) for k in ("ok", "http", "ms", "nonempty", "rows", "schema")}
    if not search.get("ok") or not search.get("nonempty"):
        out["reason"] = "keyword search did not return parseable results"
        out["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        return out
    item = matches[0]
    item_id = item.get("vod_id")
    if item_id is None:
        out["reason"] = "search result lacks vod_id for detail check"
        out["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        return out
    try:
        detail = audit.api_probe(api, {"ac": "detail", "ids": str(item_id)})
    except Exception as exc:
        out["screen_status"] = "request-failed"
        out["reason"] = f"CMS detail request failed: {type(exc).__name__}"
        out["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        return out
    detail_items = detail.get("items") or []
    item = detail_items[0] if detail_items and isinstance(detail_items[0], dict) else {}
    streams = audit.playable_urls(item)
    out["tests"]["detail"] = {k: detail.get(k) for k in ("ok", "http", "ms", "nonempty", "rows", "schema")}
    out["sample_title"] = str(item.get("vod_name") or matches[0].get("vod_name") or "")[:100]
    out["detail_has_stream_url"] = bool(streams)
    if not detail.get("ok") or not detail.get("nonempty") or not streams:
        out["reason"] = "detail did not return a direct HTTP(S) play URL"
        out["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        return out
    out["screen_status"] = "cms-api-tested"
    out["decision"] = "include"
    out["reason"] = "CMS list/search/detail returned parseable data and a direct play URL; media and TVBox client playback were not tested"
    out["elapsed_ms"] = round((time.monotonic() - started) * 1000)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readme-file", type=Path, default=DEFAULT_README)
    parser.add_argument("--config-audit", type=Path, default=DEFAULT_CONFIG_AUDIT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.workers <= 6:
        parser.error("--workers must be 1..6")
    try:
        readme = args.readme_file.read_text(encoding="utf-8-sig")
        config_report = json.loads(args.config_audit.read_text(encoding="utf-8"))
        source_hash = hashlib.sha256(readme.encode("utf-8")).hexdigest()
        rows, config_errors, parsed_configs = collect(readme, config_report)
        if not rows:
            print("No current type-1 endpoints were extractable; writing an explicit empty screening report.", flush=True)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 1
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_rows = {pool.submit(test_interface, row): row for row in rows}
        for future in concurrent.futures.as_completed(future_rows):
            try:
                results.append(future.result())
            except Exception as exc:
                row = future_rows[future]
                results.append({**row, "tests": {}, "decision": "exclude", "reason": f"screening error: {type(exc).__name__}: {str(exc)[:160]}"})
            print(f"Progress: {len(results)}/{len(rows)}; included={sum(x['decision']=='include' for x in results)}", flush=True)
    results.sort(key=lambda x: (x["decision"] != "include", x["api"]))
    report = {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_readme": audit.README_URL,
        "source_snapshot_sha256": source_hash,
        "config_audit_source_sha256": config_report.get("source_sha256") or config_report.get("source_snapshot_sha256"),
        "config_audit_generated_at": config_report.get("generated_at"),
        "method": "Re-fetch only candidates marked structurally parsed in the pinned prior config audit; extract each type-1 API; test CMS list, deterministic first-result search, detail response and presence of a direct play URL. Include only passing control-plane checks. No media request, manifest validation, decoder or TVBox client playback is performed.",
        "selection_limitations": "Candidate coverage is limited to configs structurally parsed in the referenced prior audit. Inclusion means CMS API behavior plus syntactically extracted HTTP(S) play URL only; it is not playback validation.",
        "upstream_availability_for_unfetched_config_urls": "unknown; the configured environment DNS guard prevented requests before HTTP",
        "upstream_status_for_policy_blocked": "unknown; blocked before HTTP",
        "limits": {"config_snapshot_sha256": config_report.get("source_sha256") or config_report.get("source_snapshot_sha256"), "config_snapshot_generated_at": config_report.get("generated_at"), "config_candidates": len(config_report.get("results", [])), "structural_passes_in_pinned_config_audit": sum((x.get("config") or {}).get("result") == "tvbox-json-structural" for x in config_report.get("results", [])), "configs_refetched_and_parsed": parsed_configs, "interfaces": len(rows), "dns_policy_blocked_config_urls": sum("URL hostname did not resolve to a safe public address" in str((x.get("config") or {}).get("error", "")) for x in config_report.get("results", [])), "upstream_availability_for_dns_blocked": "unknown; blocked before HTTP", "workers": args.workers, "request_timeout_seconds": audit.TIMEOUT, "cms_response_cap_bytes": audit.MAX_API, "media_probe": "not run; no media URLs fetched", "client_playback": "not tested", "config_refetch_errors": config_errors},
        "summary": {"structurally_parsed_configs": parsed_configs, "interfaces_tested": sum(x.get("screen_status") == "tested" for x in results), "cms_api_tested": sum(x.get("screen_status") == "cms-api-tested" for x in results), "blocked_by_policy": sum(x.get("screen_status") == "blocked-policy" for x in results), "request_failed": sum(x.get("screen_status") == "request-failed" for x in results), "list_nonempty": sum(bool(x.get("tests", {}).get("list", {}).get("nonempty")) for x in results), "search_nonempty": sum(bool(x.get("tests", {}).get("search", {}).get("nonempty")) for x in results), "detail_with_stream_url": sum(bool(x.get("detail_has_stream_url")) for x in results), "included": sum(x["decision"] == "include" for x in results)},
        "interfaces": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Screened {len(results)} unique interfaces; included={report['summary']['included']}; report={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
