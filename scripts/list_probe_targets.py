#!/usr/bin/env python3
"""Assemble a plain-text list of every catalog URL with its category and name.

Used to hand a complete batch to a normal curl process, so that bulk probing is not
constrained by the sandbox's proxy resolver. Output format, one record per line:

    <category> TAB <id> TAB <url> TAB <name>

Records are separated by newlines only; the name is last because it may contain spaces.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_catalog


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-dir", type=Path, default=ROOT / "catalog")
    parser.add_argument("--category", action="append", help="limit to these catalog categories (repeatable)")
    args = parser.parse_args()
    errors: list[str] = []
    entries = check_catalog.validate_catalog(errors, catalog_dir=args.catalog_dir)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    for category, entry in entries:
        if args.category and category not in args.category:
            continue
        name = " ".join(entry["name"].split())
        print(f"{category}\t{entry['id']}\t{entry['url']}\t{name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
