#!/usr/bin/env python3
"""Fetch both upstream directories and report what changed since the last run.

Both upstreams are hand-written Markdown tables plus one JSON resource file, so "did anything
change" is answered on the extracted rows rather than the page text: renaming a row, editing
its description, or repointing its link all show up, while unrelated README churn does not.

The catalog is then brought in line. A link upstream repoints is followed and the old address
kept under fallback_urls, so nothing already published goes dead. Rows upstream adds are taken
in at once, built by the same code the manual importers use, so the catalog keeps up with the
lists it tracks. A row upstream deletes is only reported: dropping it would take an address
that may still work off the page.

Output is reports/upstream-changes.json. Nonzero exit means a fetch failed and the run saw an
incomplete picture, not that something changed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import check_catalog  # noqa: E402
from scripts import import_apps, import_upstream  # noqa: E402

REPORT = ROOT / "reports" / "upstream-changes.json"
CHECKED_AT = (ROOT / "reports" / "upstream-checked.json")

SOURCES = [
    {
        "id": "awesome-zhuiju-free",
        "url": "https://raw.githubusercontent.com/laoma528/awesome-zhuiju-free/main/resources/resources.json",
        "kind": "json",
        # Upstream ids map onto this catalog's ids and nothing else; the list is authoritative
        # for the rows it owns, so a row it drops is a row that disappeared upstream.
        "owns": True,
    },
    {
        "id": "awesome-tvbox",
        "url": "https://raw.githubusercontent.com/jiji262/awesome-tvbox/main/README.md",
        "kind": "readme",
        "owns": False,
    },
]

TVBOX_UA = "tvbox-resource-catalog-check/1.0"
TVBOX_HEADERS = {"User-Agent": TVBOX_UA, "X-Requested-With": "com.github.tvbox.osc"}


def fetch(url: str, timeout: int = 30) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": TVBOX_UA})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(4 * 1024 * 1024).decode("utf-8", "replace")


def keyed(raw: dict) -> dict[str, dict]:
    """Extract rows by id; only fields whose change would mean something to a client."""
    if raw["kind"] == "json":
        return {
            item["id"]: {"name": item["name"].strip(), "url": item["url"].strip()}
            for item in import_upstream.load_upstream_text(raw["text"])["resources"]
            if item.get("id") and item.get("url")
        }
    # The client list has no ids of its own; its repository URL is the stable key.
    return {
        "app:" + row["url"].rstrip("/"): {"name": row["name"], "url": row["url"].rstrip("/")}
        for row in import_apps.parse_text(raw["text"])
    }


def compare(previous: dict[str, dict], current: dict[str, dict]) -> dict[str, list]:
    changed, added, removed = [], [], []
    for entry_id, now in current.items():
        before = previous.get(entry_id)
        if before is None:
            added.append({"id": entry_id, **now})
        elif before["url"] != now["url"] or before["name"] != now["name"]:
            changed.append({"id": entry_id, "before": before, "after": now})
    removed = [{"id": entry_id, **row} for entry_id, row in previous.items() if entry_id not in current]
    return {"added": added, "changed": changed, "removed": removed}


def catalog_id(upstream_id: str) -> str:
    """Upstream keys are not catalog ids: the client list keys rows by repository URL."""
    return upstream_id[4:] if upstream_id.startswith("app:") else import_upstream.slug(upstream_id)


def append(path: Path, rows: list[dict]) -> int:
    if not rows:
        return 0
    existing = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(existing + rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(rows)


def import_rows(catalog_dir: Path, source_id: str, ids: set[str], text: str) -> dict[str, int]:
    """Add the given upstream rows the catalog does not already carry, using the same builders
    the manual importers use, so an automatically added row is shaped exactly like a reviewed one."""
    if not ids:
        return {}
    if source_id == "awesome-zhuiju-free":
        groups = import_upstream.build(import_upstream.load_upstream_text(text), only=ids)
        targets = import_upstream.TARGETS
        return {targets[name]: append(catalog_dir / targets[name], rows)
                for name, rows in groups.items() if rows}
    rows = [row for row in import_apps.build([r for r in import_apps.parse_text(text)
                                              if "app:" + r["url"].rstrip("/") in ids])]
    return {"apps.json": append(catalog_dir / "apps.json", rows)}


def catalog_urls(catalog_dir: Path) -> set[str]:
    """Every address the catalog already carries, normalised the same way as the snapshot."""
    urls: set[str] = set()
    for path in catalog_dir.glob("*.json"):
        for entry in json.loads(path.read_text(encoding="utf-8")):
            urls.add(import_upstream.url_key(entry["url"]))
    return urls


def find_entry(catalog_dir: Path, entry_id: str) -> tuple[Path, dict] | None:
    for path in sorted(catalog_dir.glob("*.json")):
        for entry in json.loads(path.read_text(encoding="utf-8")):
            if entry.get("id") == entry_id:
                return path, entry
    return None


def repoint(catalog_dir: Path, entry_id: str, new_url: str, new_name: str | None = None) -> bool:
    """Follow a repointed link and keep the old address as a fallback."""
    found = find_entry(catalog_dir, entry_id)
    if found is None:
        return False
    path, entry = found
    old = entry["url"]
    if old == new_url and (not new_name or entry["name"] == new_name):
        return False
    entry["name"] = new_name or entry["name"]
    if old == new_url:
        entry["url"] = new_url
        rows = json.loads(path.read_text(encoding="utf-8"))
        path.write_text(json.dumps([entry if row.get("id") == entry_id else row for row in rows],
                                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return True
    entry["url"] = new_url
    fallbacks = [url for url in entry.get("fallback_urls", []) if url != old]
    entry["fallback_urls"] = [old] + fallbacks
    rows = json.loads(path.read_text(encoding="utf-8"))
    rows = [entry if row.get("id") == entry_id else row for row in rows]
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def probe_new(rows: list[dict]) -> None:
    """One bounded request per newly appearing address; failure here never blocks the run."""
    for row in rows:
        row["probe"] = {"status": "ok"}
        try:
            check_catalog.validate_public_target(row["url"])
            check_catalog.validate_remote(row.get("category", "online"), {"url": row["url"]},
                                          request_profile="tvbox")
        except Exception as exc:  # noqa: BLE001 - the reason is the payload, not a crash
            row["probe"] = {"status": "failed", "reason": f"{type(exc).__name__}: {str(exc)[:160]}"}


def run(catalog_dir: Path, report: Path, fetch_fn=fetch, now: str | None = None) -> dict:
    stamp = now or dt.datetime.now(dt.timezone.utc).isoformat()
    previous = {}
    if CHECKED_AT.exists():
        previous = json.loads(CHECKED_AT.read_text(encoding="utf-8"))
    snapshot, errors, fetched = {}, [], {}
    for source in SOURCES:
        try:
            text = fetch_fn(source["url"])
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            errors.append(f"{source['id']}: {type(exc).__name__}: {exc}")
            continue
        fetched[source["id"]] = text
        snapshot[source["id"]] = keyed({**source, "text": text})

    changed_written: list[dict] = []
    added: list[dict] = []
    removed: list[dict] = []
    imported: list[dict] = []
    for source in SOURCES:
        if source["id"] not in snapshot:
            continue
        diff = compare(previous.get(source["id"], {}), snapshot[source["id"]])
        for item in diff["changed"]:
            moved = item["before"]["url"] != item["after"]["url"]
            if repoint(catalog_dir, catalog_id(item["id"]), item["after"]["url"], item["after"]["name"]):
                item["action"] = ("address followed; previous kept as fallback" if moved
                                  else "row renamed in place")
            else:
                item["action"] = "no catalog row with this id; reported only"
            changed_written.append(item)
        # A row this list does not own may legitimately appear in both; count it once.
        added.extend({**item, "source": source["id"]} for item in diff["added"])
        if source["owns"]:
            removed.extend({**item, "source": source["id"]} for item in diff["removed"])

    # Upstream adds rows this catalog already holds under a different id; matching on address
    # is what decides whether a row is actually new to the page.
    known = catalog_urls(catalog_dir)
    fresh = []
    for row in added:
        address = import_upstream.url_key(row["url"])
        if address in known:
            continue
        known.add(address)
        fresh.append(row)
    added = [row for index, row in enumerate(fresh)
             if row["id"] not in {other["id"] for other in fresh[:index]}]
    probe_new(added)

    # New rows are taken in now; they are rows the page did not have, and leaving them out
    # until a human looks would mean the catalog drifts behind the list it tracks.
    for source in SOURCES:
        if source["id"] not in fetched:
            continue
        mine = {row["id"] for row in added if row["source"] == source["id"]}
        for file, count in import_rows(catalog_dir, source["id"], mine, fetched[source["id"]]).items():
            if count:
                imported.append({"source": source["id"], "file": file, "rows": count})

    doc = {
        "generated_at": stamp,
        "errors": errors,
        "changed": changed_written,
        "added": added,
        "removed": removed,
        "imported": imported,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if snapshot:
        CHECKED_AT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-dir", type=Path, default=ROOT / "catalog")
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    doc = run(args.catalog_dir, args.report)
    taken = sum(item["rows"] for item in doc["imported"])
    print(f"Upstream check: {len(doc['changed'])} repointed, {taken} of {len(doc['added'])} new imported, "
          f"{len(doc['removed'])} gone, {len(doc['errors'])} fetch errors")
    for error in doc["errors"]:
        print(error, file=sys.stderr)
    return 1 if doc["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
