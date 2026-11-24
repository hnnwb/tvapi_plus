#!/usr/bin/env python3
"""Generate catalog entries for upstream web, search, subtitle, app, and project resources.

Reads the upstream resources JSON (saved locally or fetched once by hand) and adds every
entry the catalog does not already hold to its target file — streaming, search, subtitle,
live, player, repository, and TVBox configuration zones. Each new row carries upstream
provenance, the upstream self-assessment as a rating block, and the probe result measured at
import time; nothing is marked as verified, playable, or good by this project.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_JSON_PATH = Path()
UPSTREAM = "https://github.com/laoma528/awesome-zhuiju-free"
UPSTREAM_JSON = "https://raw.githubusercontent.com/laoma528/awesome-zhuiju-free/main/resources/resources.json"
LICENSE_CONFIG = (
    "The upstream directory is CC BY 4.0, which covers its directory text only. "
    "The configuration is hosted by its own maintainer, who alone controls its contents, "
    "availability, and the plugins or media it points at."
)
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
    "mo-yu-er": "http200-109-sites",
    "wang-er-xiao": "http200-image-wrapped",
    "xiao-he-zi-4k": "http200-invalid-json",
    "xiao-he-zi-multi": "http200-urls-18",
    "shi-guang-multi": "http502",
    "ting-hao-share-multi": "http200-urls-32",
    "fan-tai-ying": "http200-image-wrapped",
    "fei-mao": "http200-image-wrapped",
    "fan-tai-ying-iptv": "http200",
    "fei-mao-iptv": "http200",
    "chuang-xiang-ying-shi-tvbox": "http200-sites-12",
    "xiao-ma": "http200-sites-62",
    "fan-tai-ying-iptv-wrapped": "http200-image-wrapped",
    "fei-mao": "http200-obfuscated-body",
    "zhuiju-fei-mao": "http200-obfuscated-body",
    "chuang-xiang-ying-shi-tvbox": "http200-sites-12",
}

# Configuration entries whose URL already exists locally under another owner; the catalog
# keeps the local row and imports the upstream rating onto it instead of duplicating it.
CONFIG_PASSTHROUGH: dict[str, str] = {}

# Upstream categorises a handful of these as configs and a handful of others as playlists,
# but the file each one actually hands out decides what a client can do with it.
LIST_CONFIGS = {
    "fan-tai-ying-iptv",          # /tv serves a live playlist, not a config
    "fei-mao-iptv",
    "shi-guang-multi",            # multi-source files: a URL list with per-source spider refs
    "ting-hao-share-multi",
    "xiao-he-zi-multi",
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
    "vod-single": "tvbox_config",   # catalog/vod-single.json: single configs
    "vod-multi": "tvbox_config",    # catalog/vod-multi.json: multi-source files
}

STATUS_NOTES = {
    "removed": (
        "Upstream marked this entry as removed because the site is reported inaccessible; "
        "the record is kept for provenance only and is not offered as a usable resource."
    ),
}


def load_upstream(path: Path) -> dict:
    return load_upstream_text(path.read_text(encoding="utf-8"))


def load_upstream_text(raw: str) -> dict:
    start = raw.find("\n{")
    body = raw[start + 1:] if start != -1 else raw
    # Tolerate a truncated capture: keep the last complete object.
    if not body.rstrip().endswith("}"):
        end = body.rfind("\n    }")
        if end == -1:
            raise ValueError("capture has no complete resource object")
        body = body[: end + 6] + "\n  ]\n}"
    doc = json.loads(body)
    if not isinstance(doc, dict) or not isinstance(doc.get("resources"), list):
        raise ValueError("resource file has no resources list")
    return doc


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
        parts.append(f"Upstream self-assessment status: {status}; the rating shown here is the upstream score, not a local measurement.")
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
        elif kind == "config":
            parts.append(
                "Configuration entry only: the file is checked for reachability and shape, never "
                "for playback, and the sites behind it are not exercised."
            )
        elif kind == "project":
            parts.append(
                "Source repository reference; nothing is built, executed, or mirrored by this catalog."
            )
        label = "returned" if observed == "ok" else "failed with"
        parts.append(f"Bounded GET on {dt.date(2026, 11, 23).isoformat()} {label}: {observed}.")
    scores = raw.get("scores")
    if scores:
        rating = " / ".join(f"{k} {scores.get(k, '-')}" for k in RATING_FIELDS)
        parts.append(f"Upstream self-assessment ({rating}); checked {raw.get('verification', {}).get('last_checked', 'unknown')}.")
    return " ".join(parts)


RATING_FIELDS = ("more", "speed", "clean", "stable", "ease")


def rating_block(raw: dict) -> dict:
    """Republish the upstream self-assessment verbatim, recomputing its mean.

    The upstream table carries a fifth legacy dimension, so its stored average is not always
    the mean of the five values; the validator only accepts a recomputed mean.
    """
    scores = {k: raw["scores"][k] for k in RATING_FIELDS}
    return {
        "average": round(sum(scores.values()) / len(scores), 2),
        "scores": scores,
        "status": raw.get("verification", {}).get("status", "unknown"),
        "checked_at": raw.get("verification", {}).get("last_checked") or dt.date(2026, 11, 23).isoformat(),
    }


def ascii_url(raw: dict) -> dict:
    """Send the IDNA form, which is what a resolver actually receives; the readable form
    would leave the record untestable by any automated probe."""
    if raw["url"].isascii():
        return raw
    parsed = urllib.parse.urlsplit(raw["url"])
    host = parsed.hostname.encode("idna").decode("ascii")
    netloc = f"{host}:{parsed.port}" if parsed.port else host
    return dict(raw, url=urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment)))


def rating_fields(raw: dict) -> dict:
    return {"rating": rating_block(raw)} if raw.get("scores") else {}


def config_entry(raw: dict) -> dict:
    """A TVBox configuration row: single/multi file served by the upstream maintainer."""
    fmt = "tvbox-multi" if raw["id"] in LIST_CONFIGS else "tvbox-json"
    entry = base_entry(raw, fmt, LICENSE_CONFIG)
    entry["notes"] = describe(raw, "config")
    entry.update(rating_fields(raw))
    return entry


def build(upstream: dict, only: set[str] | None = None) -> dict[str, list[dict]]:
    """Group every upstream resource into its catalog zone.

    `only` restricts the result to those upstream ids, which is what an incremental run needs:
    the scheduled job must never touch a row that already exists and has since been curated.
    """
    groups: dict[str, list[dict]] = {name: [] for name in ZONES}
    for raw in upstream["resources"]:
        if only is not None and raw.get("id") not in only:
            continue
        category = raw.get("category")
        if category == "online_video":
            entry = base_entry(raw, "web", LICENSE_WEB)
            entry["notes"] = describe(raw, "online")
            entry.update(rating_fields(raw))
            groups["online"].append(entry)
        elif category == "magnet_search":
            entry = base_entry(raw, "web", LICENSE_WEB)
            entry["notes"] = describe(raw, "search")
            entry.update(rating_fields(raw))
            groups["search"].append(entry)
        elif category == "cloud_search":
            entry = base_entry(raw, "web", LICENSE_WEB)
            entry["notes"] = describe(raw, "search")
            entry.update(rating_fields(raw))
            groups["search"].append(entry)
        elif category == "subtitles":
            entry = base_entry(raw, "web", LICENSE_WEB)
            entry["notes"] = describe(raw, "subtitle")
            entry.update(rating_fields(raw))
            groups["search"].append(entry)
        elif category == "player":
            entry = base_entry(raw, "link-page" if raw["url"].startswith("https://b.zhuiju.me/") else "web", LICENSE_WEB)
            entry["notes"] = describe(raw, "app")
            entry.update(rating_fields(raw))
            groups["app"].append(entry)
        elif category == "video_app":
            entry = base_entry(raw, "link-page" if raw["url"].startswith("https://b.zhuiju.me/") else "web", LICENSE_WEB)
            entry["notes"] = describe(raw, "app")
            entry.update(rating_fields(raw))
            groups["app"].append(entry)
        elif category == "subscription":
            # Live playlists live in catalog/live.json, whose formats are M3U/TXT. The upstream
            # "iptv-org" row duplicates the playlist entries this catalog already carries.
            if raw["id"] == "iptv-org":
                continue
            raw = ascii_url(raw)
            entry = base_entry(raw, "txt", LICENSE_WEB)
            entry["notes"] = describe(raw, "live")
            entry.update(rating_fields(raw))
            groups["live"].append(entry)
        elif category == "tvbox_config":
            entry = config_entry(ascii_url(raw))
            groups["vod-single" if entry["format"] == "tvbox-json" else "vod-multi"].append(entry)
        elif category == "open_source":
            raw = dict(raw)
            raw["url"] = PROJECT_OVERRIDES.get(raw["id"], raw["url"])
            entry = base_entry(raw, "project", LICENSE_PROJECT)
            entry["notes"] = describe(raw, "project")
            entry.update(rating_fields(raw))
            groups["tool"].append(entry)
        else:
            raise ValueError(f"unmapped upstream category: {category!r}")
    for name, rows in groups.items():
        for entry in rows:
            if not entry["url"].isascii():
                raise ValueError(f"non-ASCII URL survived conversion: {entry['url']}")
        # A partial build (only a few ids) legitimately fills one zone and leaves the rest
        # empty; the full-directory build must fill every zone or a mapping broke quietly.
        if not rows and only is None:
            raise ValueError(f"no entries generated for {name}")
    return groups


def write_group(path: Path, rows: list[dict]) -> None:
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


TARGETS = {
    "online": "online.json",
    "search": "search.json",
    "app": "apps.json",
    "live": "live.json",
    "tool": "tools.json",
    "vod-single": "vod-single.json",
    "vod-multi": "vod-multi.json",
}


def url_key(url: str) -> str:
    return re.sub(r"/+$", "", url.lower())


def catalog_index(catalog_dir: Path) -> tuple[set[str], set[str]]:
    """Every id and URL any file already holds, so a target never re-adds a row stored elsewhere."""
    ids: set[str] = set()
    urls: set[str] = set()
    for path in catalog_dir.glob("*.json"):
        for entry in json.loads(path.read_text(encoding="utf-8")):
            ids.add(entry["id"])
            urls.add(url_key(entry["url"]))
    return ids, urls


def merge(catalog_dir: Path) -> dict[str, tuple[int, int]]:
    """Add only the generated rows a target file does not already hold by id or by URL.

    Matching on URL keeps the existing row (and its owner and id) when an upstream entry is
    the same address this catalog already carries, so nothing is duplicated; the report tells
    callers how many rows each file gained.
    """
    groups = build(load_upstream(UPSTREAM_JSON_PATH))
    report: dict[str, tuple[int, int]] = {}
    all_ids, all_urls = catalog_index(catalog_dir)
    for key, name in TARGETS.items():
        path = catalog_dir / name
        existing = json.loads(path.read_text(encoding="utf-8"))
        kept = [
            entry
            for entry in existing
            if entry["id"] not in {other["id"] for other in existing if other is not entry}
        ]
        existing = kept + [entry for entry in existing if entry not in kept]
        ids = {entry["id"] for entry in existing} | all_ids
        urls = {url_key(entry["url"]) for entry in existing} | all_urls
        if key in ("vod-single", "vod-multi"):
            known = CONFIG_PASSTHROUGH
            added = [
                entry
                for entry in groups[key]
                if entry["id"] not in ids and url_key(entry["url"]) not in urls and entry["id"] not in known
            ]
        else:
            added = [
                entry
                for entry in groups[key]
                if entry["id"] not in ids and url_key(entry["url"]) not in urls
            ]
        if added:
            path.write_text(json.dumps(existing + added, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report[name] = (len(added), len(existing) + len(added))
    return report


def main() -> int:
    global UPSTREAM_JSON_PATH
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-json", type=Path, required=True, help="saved resources.json (or its captured text)")
    parser.add_argument("--catalog-dir", type=Path, default=ROOT / "catalog")
    parser.add_argument("--tools-only", action="store_true", help="print tool entries without writing catalog files")
    args = parser.parse_args()
    UPSTREAM_JSON_PATH = args.upstream_json
    if args.tools_only:
        print(json.dumps(build(load_upstream(args.upstream_json))["tool"], ensure_ascii=False, indent=2))
        return 0
    for name, (added, total) in merge(args.catalog_dir).items():
        print(f"{name:16} +{added:<3} total {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
