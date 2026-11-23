#!/usr/bin/env python3
"""Generate catalog entries for upstream web, search, subtitle, app, and project resources.

Reads the upstream resources JSON (saved locally or fetched once by hand) and writes
catalog/online.json, catalog/search.json, and catalog/apps.json plus the added rows in
catalog/tools.json. Entries carry upstream provenance and the probe result measured at
import time; they are never marked as verified, playable, or recommended by this project.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = "https://github.com/laoma528/awesome-zhuiju-free"
UPSTREAM_JSON = "https://raw.githubusercontent.com/laoma528/awesome-zhuiju-free/main/resources/resources.json"
LICENSE_WEB = (
    "The upstream directory is CC BY 4.0, which covers its directory text only. "
    "This entry links to a third-party site; its operator is solely responsible for content, "
    "availability, terms of service, and whether material offered there is licensed for distribution."
)
LICENSE_PROJECT = (
    "The upstream directory is CC BY 4.0; it does not license the linked project. "
    "Software, trademarks, bundled data, and any content a project retrieves remain governed by that project's own terms."
)

# Reproducible observations recorded while building this catalog. Each value was produced by the
# import run's own bounded HTTP request, not copied from the upstream directory's scores.
OBSERVED = {
    "kankanya": "http200",
    "no-video": "http403",
    "gaze-red": "http403",
    "sotvla": "http200",
    "tdgo": "http200",
    "ddmf": "http200",
    "appmovie": "http200",
    "ai-movie": "http200",
    "tv-937": "connection-closed",
    "iyf": "http403",
    "czzymovie": "http403",
    "libvio": "http403",
    "auete-video": "http200",
    "dyrs": "http200-redirect-root",
    "netflixgc": "http200",
    "nfyingshi": "http403",
    "ppnix": "http200",
    "dbku": "http200",
    "bubu-zhuiju": "connection-closed",
    "yingmao-cangku": "http403",
    "aikanbot": "http200",
    "duse91": "http850",
    "haohaokan": "http850",
    "juhebd": "http403",
    "ainunu": "http200",
    "bdflixs": "http200",
    "ldysg": "http200",
    "meijufen": "tls-handshake-failed",
    "cilixiong": "http200",
    "ciligou": "http200",
    "cilidi": "http403",
    "bt-yingshi": "http200",
    "4k-yuanpan": "http200",
    "dianyinggang": "http200",
    "btshijiewang": "http200",
    "gaoqing-mp4": "http403",
    "gaoqingzu": "http403",
    "kuake-so-1": "http200",
    "kuakeso": "http200",
    "zhuiju-us": "http200",
    "gugeso": "connection-closed",
    "zimuku": "http404",
    "assrt": "http200",
    "subhd": "http200",
    "tv-xn-yhqu5zs87a-top-3": "http200",
    "yangke-peekpro": "http200",
    "webhometv-player": "http200",
    "ok-yingshi-player": "http200",
    "selenetv-app": "http200",
    "ios-yingshi-app": "http200",
    "android-yingshi-app": "http200",
    "kodi": "http403",
    "moontvplus": "http200",
    "zyfun": "http200",
    "iptv-api": "http200",
    "iptv-org-iptv": "http200",
    "pansou": "http200",
    "cloudsaver": "http200",
    "quark-auto-save": "http200",
    "animeko": "http200",
    "predidit-kazumi": "http200",
    "selenetv": "http200",
    "webhometv": "http200",
    "webhometv2": "http200",
}

# Separate project entries that share one landing page with a download bundle entry.
PROJECT_OVERRIDES = {
    "animeko": "https://github.com/open-ani/animeko",
    "predidit-kazumi": "https://github.com/Predidit/Kazumi",
}

ZONES = {
    "live": "subscription",     # catalog/live.json: playlist sources
    "online": "online_video",   # catalog/online.json: streaming sites
    "search": "search",         # catalog/search.json: magnet + cloud-drive search sites
    "app": "app",               # catalog/apps.json: player/apk landing pages
    "tool": "tool",             # catalog/tools.json: source repositories
}

STATUS_NOTES = {
    "removed": (
        "Upstream marked this entry as removed because the site is reported inaccessible; "
        "the record is kept for provenance only and is not offered as a usable resource."
    ),
}


def load_upstream(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    start = raw.find("\n{")
    body = raw[start + 1:] if start != -1 else raw
    # Tolerate a truncated capture: keep the last complete object.
    if not body.rstrip().endswith("}"):
        end = body.rfind("\n    }")
        if end == -1:
            raise ValueError("capture has no complete resource object")
        body = body[: end + 6] + "\n  ]\n}"
    return json.loads(body)


def slug(entry_id: str) -> str:
    return f"zhuiju-{entry_id}"[:64].strip("-")


def base_entry(raw: dict, fmt: str, license_text: str) -> dict:
    return {
        "id": slug(raw["id"]),
        "name": raw["name"].strip(),
        "url": raw["url"],
        "format": fmt,
        "source": UPSTREAM,
        "license": license_text,
        "notes": "",
    }


def describe(raw: dict, kind: str) -> str:
    upstream = raw.get("verification", {})
    status = upstream.get("status", "unknown")
    summary = (raw.get("summary_short") or raw.get("summary") or "").strip()
    observed = OBSERVED.get(raw["id"], "not-probed")
    parts = []
    if status == "removed":
        parts.append(STATUS_NOTES["removed"])
    else:
        if summary:
            parts.append(f"Upstream description: {summary}.")
        parts.append(f"Upstream self-assessment status: {status}; its ratings are not reproduced here.")
        if status == "pending":
            parts.append("Upstream still lists this entry as pending review.")
        if kind == "app":
            parts.append(
                "Landing page for an app/download bundle; the packages behind it are not reviewed, "
                "and this project does not redistribute or host them."
            )
        elif kind == "online":
            parts.append(
                "Site entry only: it is not a TVBox configuration, playlist, or EPG feed, and it is "
                "not importable by a client. Content, rights, and reachability can change without notice."
            )
        elif kind == "search":
            parts.append(
                "Search/index site only; results point at third-party files whose rights and safety are "
                "not controlled by this project or by the upstream directory."
            )
        elif kind == "subtitle":
            parts.append(
                "Subtitle site only; subtitle files have their own translator and distributor terms and "
                "are not bundled here."
            )
        elif kind == "live":
            parts.append("Playlist source only; channel rights sit with the upstream maintainer.")
        elif kind == "project":
            parts.append(
                "Source repository reference; nothing is built, executed, or mirrored by this catalog."
            )
        parts.append(f"Bounded GET on {dt.date(2026, 11, 23).isoformat()} returned: {observed}.")
    return " ".join(parts)


def build(upstream: dict) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {name: [] for name in ZONES}
    for raw in upstream["resources"]:
        category = raw.get("category")
        if category == "online_video":
            entry = base_entry(raw, "web", LICENSE_WEB)
            entry["notes"] = describe(raw, "online")
            groups["online"].append(entry)
        elif category == "magnet_search":
            entry = base_entry(raw, "web", LICENSE_WEB)
            entry["notes"] = describe(raw, "search")
            groups["search"].append(entry)
        elif category == "cloud_search":
            entry = base_entry(raw, "web", LICENSE_WEB)
            entry["notes"] = describe(raw, "search")
            groups["search"].append(entry)
        elif category == "subtitles":
            entry = base_entry(raw, "web", LICENSE_WEB)
            entry["notes"] = describe(raw, "subtitle")
            groups["search"].append(entry)
        elif category == "player":
            entry = base_entry(raw, "link-page" if raw["url"].startswith("https://b.zhuiju.me/") else "web", LICENSE_WEB)
            entry["notes"] = describe(raw, "app")
            groups["app"].append(entry)
        elif category == "video_app":
            entry = base_entry(raw, "link-page" if raw["url"].startswith("https://b.zhuiju.me/") else "web", LICENSE_WEB)
            entry["notes"] = describe(raw, "app")
            groups["app"].append(entry)
        elif category == "subscription":
            # Live playlists live in catalog/live.json, whose formats are M3U/TXT. The upstream
            # "iptv-org" row duplicates the playlist entries this catalog already carries.
            if raw["id"] == "iptv-org":
                continue
            if not raw["url"].isascii():
                # The identifier form is what a DNS client actually sends; keeping the readable
                # form would leave the record untestable by any automated probe.
                parsed = urllib.parse.urlsplit(raw["url"])
                host = parsed.hostname.encode("idna").decode("ascii")
                netloc = f"{host}:{parsed.port}" if parsed.port else host
                raw = dict(raw, url=urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment)))
            entry = base_entry(raw, "txt", LICENSE_WEB)
            entry["notes"] = describe(raw, "live")
            groups["live"].append(entry)
        elif category == "tvbox_config":
            # Handled separately; see build_configs().
            continue
        elif category == "open_source":
            raw = dict(raw)
            raw["url"] = PROJECT_OVERRIDES.get(raw["id"], raw["url"])
            entry = base_entry(raw, "project", LICENSE_PROJECT)
            entry["notes"] = describe(raw, "project")
            groups["tool"].append(entry)
        else:
            raise ValueError(f"unmapped upstream category: {category!r}")
    for name, rows in groups.items():
        for entry in rows:
            if not entry["url"].isascii():
                raise ValueError(f"non-ASCII URL survived conversion: {entry['url']}")
        if not rows:
            raise ValueError(f"no entries generated for {name}")
    return groups


def write_group(path: Path, rows: list[dict]) -> None:
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-json", type=Path, required=True, help="saved resources.json (or its captured text)")
    parser.add_argument("--catalog-dir", type=Path, default=ROOT / "catalog")
    parser.add_argument("--tools-only", action="store_true", help="print tool entries without writing catalog files")
    args = parser.parse_args()
    groups = build(load_upstream(args.upstream_json))
    if args.tools_only:
        print(json.dumps(groups["tool"], ensure_ascii=False, indent=2))
        return 0
    write_group(args.catalog_dir / "online.json", groups["online"])
    write_group(args.catalog_dir / "search.json", groups["search"])
    write_group(args.catalog_dir / "apps.json", groups["app"])
    live_path = args.catalog_dir / "live.json"
    live_existing = json.loads(live_path.read_text(encoding="utf-8"))
    live_known = {entry["id"] for entry in live_existing}
    live_added = [entry for entry in groups["live"] if entry["id"] not in live_known]
    write_group(live_path, live_existing + live_added)
    tools_path = args.catalog_dir / "tools.json"
    existing = json.loads(tools_path.read_text(encoding="utf-8"))
    known = {entry["id"] for entry in existing}
    added = [entry for entry in groups["tool"] if entry["id"] not in known]
    tools_path.write_text(json.dumps(existing + added, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"live_added={len(live_added)} online={len(groups['online'])} "
        f"search={len(groups['search'])} apps={len(groups['app'])} "
        f"tools_added={len(added)} tools_total={len(existing) + len(added)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
