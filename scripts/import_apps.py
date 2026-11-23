#!/usr/bin/env python3
"""Merge client applications from the original TVBox list into catalog/apps.json.

The list is a hand-curated table, not a JSON API, so it is parsed directly. Every row in its
client sections is a repository URL, which is what a catalog row points at anyway: the release
page lives there. Build and star counts become notes, and the number of GitHub stars is turned
into a 1-5 rating so the app list can sort itself the way the rest of the catalog does.

Stars are a popularity measure, not a quality or usability verdict, and the output says so.
Rows already present in any catalog file are skipped by URL, so repeat runs only add.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Sections of the list that hold clients a user installs, as opposed to configs, spiders,
# live playlists or tooling.
SECTIONS = {"开源客户端", "桌面与跨平台", "直播软件"}

# Rows the list marks as dead ends; kept, but not sorted to the top by their star count.
ARCHIVED = {"liu673cn/bug", "XiaoRanLiu3119/TVBoxOS-Mobile", "yaoxieyoulei/mytv-android"}

# A handful of rows point at a build-artifact repository rather than the app itself.
NOTES = {
    "j4Uq/TVBoxOSC": "自动构建发布仓，APK 在 Releases 里；源码在各自的分支仓库。",
    "xixu-me/fongmi-tv-actions-builder": "用 GitHub Actions 编译并签名 FongMi TV，产出 APK 供自建。",
    "liu673cn/bug": "已停更，仅作存档参考。",
    "XiaoRanLiu3119/TVBoxOS-Mobile": "已归档的竖屏适配版。",
    "yaoxieyoulei/mytv-android": "已归档的原项目。",
}

# Every row in the list's client sections is Android-side unless it says otherwise: the list
# is about TV boxes. "TV" alone is not a platform, so a row that only says TV is an Android app
# on a TV, not a desktop program.
PLATFORMS = [
    (r"Apple 全平台|iOS / iPadOS / tvOS / macOS / watchOS", "Apple 全平台（iOS·tvOS·macOS）"),
    (r"Android / TV / iOS / Windows", "Android·TV·iOS·Windows·macOS"),
    (r"Windows / macOS / Linux", "Windows·macOS·Linux"),
    (r"Android / TV / iOS", "Android·TV·iOS"),
    (r"Android TV", "Android TV"),
    (r"Android", "Android"),
    (r"iOS", "iOS"),
    (r"macOS|macOS|Apple Silicon", "macOS"),
    (r"Windows", "Windows"),
    (r"Linux", "Linux"),
    (r"Web\b", "Web"),
    (r"TV", "Android TV·盒子"),
]

ROW = re.compile(r"\|\s*\[([^\]]+)\]\((https://github\.com/[^)]+)\)\s*\|([^|]*)\|([^|]*)\|")


def stars_to_rating(stars: str) -> float:
    """Bucket a star count onto the 1-5 scale the validator accepts.

    The bands are deliberately coarse: below 50 stars a project's star count says little about
    whether it runs on the reader's machine, and the page shows the raw count next to it.
    """
    text = stars.strip().lower()
    if not text:
        return 1.0
    number = float(text.rstrip("k+") or 0)
    count = number * 1000 if text.endswith("k") else number
    for threshold, value in ((10000, 5.0), (3000, 4.5), (1000, 4.0), (300, 3.5), (100, 3.0), (30, 2.5), (10, 2.0)):
        if count >= threshold:
            return value
    return 1.0


def platforms(desc: str) -> str:
    for pattern, label in PLATFORMS:
        if re.search(pattern, desc):
            return label
    return "Android TV·盒子（上游只标 TV，未写具体系统）"


def entry_id(url: str) -> str:
    """Owner and repository, in full: two projects can share a repository name."""
    owner, repo = url.rstrip("/").rsplit("/", 2)[-2:]
    return "app-" + re.sub(r"[^a-z0-9]+", "-", f"{owner}-{repo}".lower()).strip("-")


def parse(source: Path) -> list[dict]:
    rows: list[dict] = []
    section = ""
    for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("### "):
            section = line[4:].strip()
            continue
        match = ROW.match(line)
        if not match or section not in SECTIONS:
            continue
        name, url, desc, stars = (part.strip() for part in match.groups())
        rows.append({"name": name, "url": url.rstrip("/"), "desc": desc, "stars": stars})
    return rows


def build(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        slug = "/".join(row["url"].rsplit("/", 2)[-2:])
        desc = re.sub(r"\s*·\s*\[[^\]]+\]\([^)]*\)", "", row["desc"])
        notes = [
            f"上游列表收录：{desc}" if desc and desc != "—" else "上游列表收录。",
            f"平台：{platforms(row['desc'])}。",
        ]
        if row["stars"]:
            notes.append(f"GitHub 星标 {row['stars']}，据此折算星级；星标表示热度，不代表可用或好用。")
        if slug in NOTES:
            notes.append(NOTES[slug])
        if slug in ARCHIVED:
            notes.append("star 数与当前可用性无关，已停更条目不要按星级优先。")
        out.append(
            {
                "id": entry_id(row["url"]),
                "name": row["name"],
                "url": row["url"],
                "format": "project",
                "source": "https://github.com/jiji262/awesome-tvbox",
                "license": "See the repository for its own licence; this catalog only links to it.",
                "notes": " ".join(notes),
                "rating": {"average": stars_to_rating(row["stars"]),
                           "scores": {"more": 3, "speed": 3, "clean": 3, "stable": 3, "ease": 3},
                           "status": "upstream-stars", "checked_at": "2026-11-23"},
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", type=Path, required=True, help="saved README of jiji262/awesome-tvbox")
    parser.add_argument("--catalog-dir", type=Path, default=ROOT / "catalog")
    args = parser.parse_args()

    known: set[str] = set()
    for path in args.catalog_dir.glob("*.json"):
        for row in json.loads(path.read_text(encoding="utf-8")):
            known.add(row["url"].rstrip("/").lower())

    target = args.catalog_dir / "apps.json"
    existing = json.loads(target.read_text(encoding="utf-8"))
    ids = {row["id"] for row in existing}
    added = [row for row in build(parse(args.list))
             if row["url"].lower() not in known and row["id"] not in ids]
    target.write_text(json.dumps(existing + added, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"apps +{len(added)} total {len(existing) + len(added)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
