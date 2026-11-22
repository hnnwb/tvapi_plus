#!/usr/bin/env python3
"""Build a custom TVBox single config from reviewed CMS endpoint evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "reports" / "interface-screening.json"
DEFAULT_OUTPUT = ROOT / "dist" / "tvbox-custom-single.json"


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        config = build(args.evidence)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Custom single build failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built custom single with {len(config['sites'])} screened CMS interfaces: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
