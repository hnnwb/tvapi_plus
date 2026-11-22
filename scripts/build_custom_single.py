#!/usr/bin/env python3
"""Build a custom TVBox single config from reviewed CMS endpoint evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "reports" / "interface-screening.json"
DEFAULT_CANDIDATES = ROOT / "reports" / "single-source-audit.json"
CANDIDATE_REPORT = ROOT / "reports" / "custom-single-candidates.json"
DEFAULT_OUTPUT = ROOT / "dist" / "tvbox-custom-single.json"
DEFAULT_STATUS_OUTPUT = ROOT / "dist" / "reports" / "custom-single-candidates.json"


def build_candidate_config(candidate_path: Path = DEFAULT_CANDIDATES) -> dict:
    """Build an explicitly unverified aggregate from APIs in the historical config audit."""
    report = json.loads(candidate_path.read_text(encoding="utf-8"))
    sites = []
    seen = set()
    used_keys = set()
    for config in report.get("results", []):
        if (config.get("config") or {}).get("result") != "tvbox-json-structural":
            continue
        for api_row in config.get("cms", []):
            api = api_row.get("api")
            if not isinstance(api, str) or not api.startswith(("http://", "https://")) or api in seen:
                continue
            seen.add(api)
            base_key = str(api_row.get("key") or f"candidate_{len(sites) + 1}")
            key = base_key
            suffix = 2
            while key in used_keys:
                key = f"{base_key}_{suffix}"
                suffix += 1
            used_keys.add(key)
            name = api_row.get("name") or key
            sites.append({"key": key, "name": name, "type": 1, "api": api,
                          "searchable": 1, "quickSearch": 1, "filterable": 1})
    return {"spider": "", "wallpaper": "", "sites": sites, "parses": [], "lives": [], "ads": []}


def candidate_status(candidate_path: Path = DEFAULT_CANDIDATES, screening_path: Path | None = None) -> dict:
    audit = json.loads(candidate_path.read_text(encoding="utf-8"))
    api_sites = build_candidate_config(candidate_path)["sites"]
    results = audit.get("results", [])
    screening_summary = {}
    screening = {}
    if screening_path is not None and screening_path.exists():
        screening = json.loads(screening_path.read_text(encoding="utf-8"))
        screening_summary = screening.get("summary", {})
    status_counts = audit.get("status_counts", {})
    error_text = " ".join(
        str(row.get("config", {}).get("error", ""))
        for row in results
    )
    network_denied = sum(
        marker in error_text
        for marker in ("URL hostname did not resolve", "non-public IP", "non-public address")
    )
    return {
        "schema_version": 1,
        "generated_at": audit.get("generated_at"),
        "source_readme": audit.get("source_readme"),
        "source_sha256": audit.get("source_sha256"),
        "candidate_config": "subscriptions/tvbox-custom-single.json",
        "verification_status": "unverified-candidate",
        "screening_summary": screening_summary,
        "selection_scope": "Candidates extracted only from the 20 structurally parsed configs in a 48-URL README snapshot; the audit's 28 other entries failed parsing or access checks. This is not a complete source catalog.",
        "structurally_parsed_configs": sum((row.get("config") or {}).get("result") == "tvbox-json-structural" for row in results),
        "historical_api_samples": sum(len(row.get("cms", [])) for row in results),
        "historical_4k_title_hits": audit.get("four_k_title_hits", 0),
        "historical_direct_play_url_hits": audit.get("direct_play_url_hits", 0),
        "historical_title_search_detail_url_hits": audit.get("four_k_direct_play_url_hits", 0),
        "historical_verified_4k_streams": audit.get("verified_4k_streams", 0),
        "historical_network_denied_config_requests": network_denied,
        "historical_failed_or_unparsed_configs": status_counts.get("failed", 0),
        "historical_config_status_counts": dict(status_counts),
        "historical_failure_types": {},
        "historical_failure_detail": "Failure categories were not retained in the supplied audit report; only aggregate status counts are available.",
        "latest_config_candidates_blocked_by_policy": (screening.get("limits") or {}).get("dns_policy_blocked_candidates", 0) if screening_path is not None and screening_path.exists() else 0,
        "latest_config_structural_passes": (screening.get("limits") or {}).get("structural_passes_in_pinned_config_audit", 0) if screening_path is not None and screening_path.exists() else 0,
        "screened_interfaces": screening_summary.get("interfaces_tested", 0),
        "tested_cms_apis": screening_summary.get("cms_api_tested", 0),
        "screened_api_candidates": (screening_summary.get("interfaces_tested", 0) + screening_summary.get("blocked_by_policy", 0) + screening_summary.get("request_failed", 0)),
        "network_denied_api_candidates": screening_summary.get("blocked_by_policy", 0),
        "media_validated": screening_summary.get("media_validated", 0),
        "unique_candidate_apis": len(api_sites),
        "historical_checks": "Only up to three type-1 APIs per config were searched for 4K/2160p/UHD titles; no general list/search/detail validation, media probe or playback test. Title hits are not 4K evidence.",
        "note": "Candidate rows are unverified and may be stale. Import and playback are at the user's discretion."
    }


def build(evidence_path: Path = DEFAULT_EVIDENCE) -> dict:
    report = json.loads(evidence_path.read_text(encoding="utf-8"))
    if report.get("schema_version") != 1 or not isinstance(report.get("interfaces"), list):
        raise ValueError("unexpected interface screening report schema")
    sites = []
    seen = set()
    for row in report["interfaces"]:
        if not isinstance(row, dict) or row.get("decision") != "include" or row.get("screen_status") != "cms-api-tested":
            continue
        tests = row.get("tests") or {}
        if not all((tests.get(name) or {}).get("ok") for name in ("list", "search", "detail")) or not row.get("detail_has_stream_url"):
            continue
        api = row.get("api")
        name = row.get("name")
        key = row.get("key")
        if not all(isinstance(x, str) and x.strip() for x in (api, name, key)):
            raise ValueError("included interface is missing key/name/api")
        if api in seen:
            continue
        seen.add(api)
        sites.append({"key": key, "name": name, "type": 1, "api": api, "searchable": 1, "quickSearch": 1, "filterable": 1})
    return {
        "spider": "",
        "wallpaper": "",
        "sites": sites,
        "parses": [],
        "lives": [],
        "ads": [],
    }


def build_candidates(candidate_path: Path = DEFAULT_CANDIDATES) -> dict:
    return build_candidate_config(candidate_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--status-output", type=Path, default=DEFAULT_STATUS_OUTPUT)
    args = parser.parse_args()
    try:
        config = build(args.evidence) if args.evidence.exists() else build_candidate_config(args.candidates)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        status = candidate_status(args.candidates, args.evidence)
        args.status_output.parent.mkdir(parents=True, exist_ok=True)
        args.status_output.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Custom single build failed: {exc}", file=sys.stderr)
        return 1
    build_mode = "screened" if args.evidence.exists() else "unverified candidate"
    print(f"Built {build_mode} custom single with {len(config['sites'])} CMS interfaces: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
