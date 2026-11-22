#!/usr/bin/env python3
"""Build reviewed TVBox configuration indexes and subscriptions."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_catalog
from build_custom_single import build as build_custom_single

CUSTOM_REPORT = ROOT / "reports" / "interface-screening.json"


def build(catalog_dir: Path = ROOT / "catalog", custom_evidence: Path | None = None) -> tuple[dict, dict]:
    errors: list[str] = []
    playback_ids: set[str] = set()
    entries = check_catalog.validate_catalog(errors, playback_ids=playback_ids, catalog_dir=catalog_dir)
    if errors:
        raise ValueError("catalog validation failed:\n" + "\n".join(errors))

    urls: list[dict[str, str]] = []
    index: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    seen_index_urls: set[str] = set()
    for category, entry in entries:
        if category not in {"vod-single", "vod-multi"}:
            continue
        url = entry["url"]
        if url not in seen_index_urls:
            index.append({"id": entry["id"], "name": entry["name"].strip(), "url": url, "source": entry["source"]})
            seen_index_urls.add(url)
        if entry["id"] in playback_ids and url not in seen_urls:
            urls.append({"name": entry["name"].strip(), "url": url})
            seen_urls.add(url)

    custom_config = None
    if custom_evidence is not None and custom_evidence.exists():
        custom_config = build_custom_single(custom_evidence)
        if custom_config["sites"]:
            index.append({"id": "tvapi-plus-custom-single", "name": "TVAPI Plus 自建单仓", "url": "subscriptions/tvbox-custom-single.json", "source": "TVAPI Plus bounded screening report"})
    return {"urls": urls}, {"configs": index}, custom_config


def write_json(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_outputs(output_dir: Path, subscriptions: dict, index: dict, custom_config: dict | None = None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "configs.json", index)
    write_json(output_dir / "subscriptions" / "tvbox-multi.json", subscriptions)
    custom_path = output_dir / "subscriptions" / "tvbox-custom-single.json"
    if custom_config and custom_config.get("sites"):
        write_json(custom_path, custom_config)
    elif custom_path.exists():
        custom_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--custom-evidence", type=Path, default=CUSTOM_REPORT)
    args = parser.parse_args()
    try:
        subscriptions, index, custom_config = build(custom_evidence=args.custom_evidence)
        write_outputs(args.output_dir, subscriptions, index, custom_config)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Subscription build failed: {exc}", file=sys.stderr)
        return 1
    custom_count = len(custom_config["sites"]) if custom_config else 0
    print(f"Built {len(subscriptions['urls'])} playback-evidence-qualified subscription URLs, {len(index['configs'])} config index entries, and {custom_count} custom single sites")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
