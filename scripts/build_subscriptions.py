#!/usr/bin/env python3
"""Build a reviewed TVBox multi-source manifest and config index."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_catalog


def build(catalog_dir: Path = ROOT / "catalog") -> tuple[dict, dict]:
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
        item = {"name": entry["name"].strip(), "url": url}
        if url not in seen_index_urls:
            index.append({"id": entry["id"], **item, "source": entry["source"]})
            seen_index_urls.add(url)
        if entry["id"] in playback_ids and url not in seen_urls:
            urls.append(item)
            seen_urls.add(url)
    return {"urls": urls}, {"configs": index}


def write_json(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_outputs(output_dir: Path, subscriptions: dict, index: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "configs.json", index)
    write_json(output_dir / "subscriptions" / "tvbox-multi.json", subscriptions)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    try:
        subscriptions, index = build()
        write_outputs(args.output_dir, subscriptions, index)
    except (OSError, ValueError, TypeError) as exc:
        print(f"Subscription build failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built {len(subscriptions['urls'])} playback-evidence-qualified subscription URLs and {len(index['configs'])} unique config index entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
