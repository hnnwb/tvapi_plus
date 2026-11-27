#!/usr/bin/env python3
"""Validate catalog metadata and optionally probe resource URLs without executing them."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import http.client
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog"
ALLOWED_FORMATS = {
    "vod-single": {"tvbox-json"},
    "vod-multi": {"tvbox-multi"},
    "live": {"m3u", "txt", "tvbox-live-json"},
    "epg": {"epg-xml", "logo-library"},
    "tools": {"documentation", "utility", "project"},
    "online": {"web"},
    "magnet": {"web"},
    "search": {"web"},
    # An app row may be the project repository, the product's own page, or the download
    # landing page the catalog owner keeps for a build — all three are the app's entry point.
    "apps": {"web", "link-page", "project"},
}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
PLAYBACK_EVIDENCE_FIELDS = {"id", "client", "version", "tested_at", "scope", "duration_seconds", "result"}
MIN_PLAYBACK_SECONDS = 30
VERIFICATION_CHECK_FIELDS = {"id", "subject", "subject_zh", "kind", "status", "method", "method_zh", "snapshot", "limitations"}
VERIFICATION_STATUSES = {"passed", "failed", "not-tested"}
RATING_DIMENSIONS = {"more", "speed", "clean", "stable", "ease"}
RATING_FIELDS = {"average", "scores", "status", "checked_at"}
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
MAX_BODY = 512 * 1024
# Guide feeds routinely exceed a few MiB; keep a separate hard ceiling while allowing
# structural XMLTV validation. This is still a bounded metadata check, not a mirror.
MAX_EPG_BODY = 32 * 1024 * 1024
MAX_LOGO_BODY = 16 * 1024 * 1024
# Community live lists are often a megabyte or two of channel records, which is normal for the
# format rather than a broken response; M3U and TXT get their own bound so the 512 KiB default
# keeps guarding configurations and web pages.
MAX_LIVE_BODY = 4 * 1024 * 1024
TIMEOUT = 12


def fail(errors: list[str], where: str, message: str) -> None:
    errors.append(f"{where}: {message}")


def is_http_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urllib.parse.urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname) and not parsed.username and not parsed.password and parsed.port != 0
    except ValueError:
        return False


# Network environments that route DNS through a local proxy resolver answer with addresses from
# RFC 2544 benchmarking space (198.18.0.0/15). Those answers still traverse the proxy, so treat the
# block as user-opt-in rather than deleting the guard outright.
SYNTHETIC_PROXY_NET = "198.18.0.0/15"


def validate_public_target(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname
    if not host:
        raise ValueError("URL has no hostname")
    try:
        import ipaddress
        import socket
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)}
        synthetic = ipaddress.ip_network(SYNTHETIC_PROXY_NET)
        parsed_addresses = [ipaddress.ip_address(address.split("%", 1)[0]) for address in addresses]
        # The shared resolver answers with this fully synthetic range, which never
        # reaches the public internet from here; internal addresses are still refused.
        synthetic_resolver = bool(parsed_addresses) and all(address in synthetic for address in parsed_addresses)
        if not parsed_addresses or (any(not address.is_global for address in parsed_addresses) and not synthetic_resolver):
            raise ValueError("URL resolves to a non-public network address")
    except (OSError, ValueError) as exc:
        raise ValueError("URL hostname did not resolve to a safe public address") from exc


def load_json(path: Path, errors: list[str]):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        try:
            label = str(path.relative_to(ROOT))
        except ValueError:
            label = str(path)
        fail(errors, label, f"cannot read JSON: {exc}")
        return None


def validate_playback_evidence(catalog_entries: list[tuple[str, dict]], errors: list[str], evidence_path: Path | None = None) -> set[str]:
    entries_by_id = {entry.get("id"): (category, entry) for category, entry in catalog_entries if isinstance(entry.get("id"), str)}
    evidence_path = evidence_path or (CATALOG / "playback-evidence.json")
    document = load_json(evidence_path, errors)
    if not isinstance(document, list):
        fail(errors, "catalog/playback-evidence.json", "expected a JSON array")
        return set()

    verified: set[str] = set()
    seen: set[str] = set()
    for index, item in enumerate(document):
        where = f"catalog/playback-evidence.json[{index}]"
        if not isinstance(item, dict):
            fail(errors, where, "expected an object")
            continue
        missing = PLAYBACK_EVIDENCE_FIELDS - item.keys()
        extra = item.keys() - PLAYBACK_EVIDENCE_FIELDS
        if missing:
            fail(errors, where, f"missing keys: {', '.join(sorted(missing))}")
        if extra:
            fail(errors, where, f"unexpected keys: {', '.join(sorted(extra))}")
        entry_id = item.get("id")
        if not isinstance(entry_id, str) or entry_id not in entries_by_id:
            fail(errors, where, "id must reference an existing catalog entry")
            continue
        if not ID_RE.fullmatch(entry_id):
            fail(errors, where, "id must match the catalog ID pattern")
        if entry_id in seen:
            fail(errors, where, f"duplicate playback evidence for id: {entry_id}")
        seen.add(entry_id)
        category, _entry = entries_by_id[entry_id]
        if category not in {"vod-single", "vod-multi"}:
            fail(errors, where, "playback evidence only applies to VOD configuration entries")
        for field in ("client", "version", "scope"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                fail(errors, where, f"{field} must be a non-empty string")
        tested_at = item.get("tested_at")
        try:
            if not isinstance(tested_at, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", tested_at):
                raise ValueError("not an ISO date")
            dt.date.fromisoformat(tested_at)
        except (TypeError, ValueError):
            fail(errors, where, "tested_at must be a valid YYYY-MM-DD date")
        duration = item.get("duration_seconds")
        if isinstance(duration, bool) or not isinstance(duration, int) or duration < MIN_PLAYBACK_SECONDS:
            fail(errors, where, f"duration_seconds must be an integer of at least {MIN_PLAYBACK_SECONDS}")
        if item.get("result") != "passed":
            fail(errors, where, "result must be passed to qualify for a subscription")
        if (not missing and not extra and item.get("result") == "passed"
                and category in {"vod-single", "vod-multi"}
                and all(isinstance(item.get(field), str) and item[field].strip() for field in ("client", "version", "scope"))
                and isinstance(duration, int) and not isinstance(duration, bool) and duration >= MIN_PLAYBACK_SECONDS):
            try:
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", item["tested_at"]):
                    raise ValueError("not an ISO date")
                dt.date.fromisoformat(item["tested_at"])
                verified.add(entry_id)
            except (TypeError, ValueError):
                pass
    return verified


def validate_verification_report(errors: list[str], report_path: Path | None = None) -> None:
    report_path = report_path or (ROOT / "reports" / "verification-report.json")
    report = load_json(report_path, errors)
    label = "reports/verification-report.json"
    if not isinstance(report, dict):
        fail(errors, label, "expected an object")
        return
    if report.get("schema_version") != 1:
        fail(errors, label, "schema_version must be 1")
    generated_at = report.get("generated_at")
    try:
        if not isinstance(generated_at, str):
            raise ValueError("not a timestamp")
        dt.datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError:
        fail(errors, label, "generated_at must be an ISO timestamp")
    summary = report.get("summary")
    if not isinstance(summary, dict):
        fail(errors, label, "summary must be an object")
    else:
        for field in ("client_playback_verified", "true_4k_verified"):
            if not isinstance(summary.get(field), bool):
                fail(errors, label, f"summary.{field} must be a boolean")
        count = summary.get("local_unit_tests_passed")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            fail(errors, label, "summary.local_unit_tests_passed must be a non-negative integer")
    checks = report.get("checks")
    if not isinstance(checks, list) or not checks:
        fail(errors, label, "checks must be a non-empty array")
        return
    seen: set[str] = set()
    for index, check in enumerate(checks):
        where = f"{label}.checks[{index}]"
        if not isinstance(check, dict):
            fail(errors, where, "expected an object")
            continue
        missing = VERIFICATION_CHECK_FIELDS - check.keys()
        extra = check.keys() - VERIFICATION_CHECK_FIELDS
        if missing:
            fail(errors, where, f"missing keys: {', '.join(sorted(missing))}")
        if extra:
            fail(errors, where, f"unexpected keys: {', '.join(sorted(extra))}")
        check_id = check.get("id")
        if not isinstance(check_id, str) or not ID_RE.fullmatch(check_id):
            fail(errors, where, "id must match catalog ID pattern")
        elif check_id in seen:
            fail(errors, where, f"duplicate id: {check_id}")
        else:
            seen.add(check_id)
        if check.get("status") not in VERIFICATION_STATUSES:
            fail(errors, where, f"status must be one of: {', '.join(sorted(VERIFICATION_STATUSES))}")
        for field in VERIFICATION_CHECK_FIELDS - {"status"}:
            if not isinstance(check.get(field), str) or not check[field].strip():
                fail(errors, where, f"{field} must be a non-empty string")


def validate_rating(rating: object, errors: list[str], where: str) -> None:
    if not isinstance(rating, dict):
        fail(errors, where, "rating must be an object")
        return
    missing = RATING_FIELDS - rating.keys()
    extra = rating.keys() - RATING_FIELDS
    if missing:
        fail(errors, where, f"rating missing keys: {', '.join(sorted(missing))}")
    if extra:
        fail(errors, where, f"rating unexpected keys: {', '.join(sorted(extra))}")
    scores = rating.get("scores")
    if not isinstance(scores, dict) or set(scores) != RATING_DIMENSIONS:
        fail(errors, where, f"rating.scores must have exactly: {', '.join(sorted(RATING_DIMENSIONS))}")
    else:
        for dimension, value in scores.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 1 <= value <= 5:
                fail(errors, where, f"rating.scores.{dimension} must be a number from 1 to 5")
    average = rating.get("average")
    if isinstance(average, bool) or not isinstance(average, (int, float)) or not 1 <= average <= 5:
        fail(errors, where, "rating.average must be a number from 1 to 5")
    elif isinstance(scores, dict) and set(scores) == RATING_DIMENSIONS and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in scores.values()):
        expected = round(sum(scores.values()) / len(RATING_DIMENSIONS), 2)
        if abs(float(average) - expected) > 0.005:
            fail(errors, where, f"rating.average must equal the mean of scores ({expected})")
    for field in ("status", "checked_at"):
        if not isinstance(rating.get(field), str) or not rating[field].strip():
            fail(errors, where, f"rating.{field} must be a non-empty string")
    checked_at = rating.get("checked_at")
    if isinstance(checked_at, str) and checked_at.strip() and not DATE_RE.fullmatch(checked_at):
        fail(errors, where, "rating.checked_at must be a YYYY-MM-DD date")


def validate_catalog(errors: list[str], playback_ids: set[str] | None = None, catalog_dir: Path = CATALOG) -> list[tuple[str, dict]]:
    seen: set[str] = set()
    entries: list[tuple[str, dict]] = []
    required = {"id", "name", "url", "format", "source", "license", "notes"}
    for category, formats in ALLOWED_FORMATS.items():
        path = catalog_dir / f"{category}.json"
        doc = load_json(path, errors)
        if not isinstance(doc, list):
            try:
                label = str(path.relative_to(ROOT))
            except ValueError:
                label = str(path)
            fail(errors, label, "expected a JSON array")
            continue
        for index, entry in enumerate(doc):
            try:
                relative_path = path.relative_to(ROOT)
            except ValueError:
                relative_path = path
            where = f"{relative_path}[{index}]"
            if not isinstance(entry, dict):
                fail(errors, where, "expected an object")
                continue
            missing = required - entry.keys()
            if missing:
                fail(errors, where, f"missing keys: {', '.join(sorted(missing))}")
            allowed = required | {"fallback_urls", "rating"}
            extra = entry.keys() - allowed
            if extra:
                fail(errors, where, f"unexpected keys: {', '.join(sorted(extra))}")
            fallback_urls = entry.get("fallback_urls", [])
            if not isinstance(fallback_urls, list) or any(not isinstance(url, str) or not is_http_url(url) for url in fallback_urls):
                fail(errors, where, "fallback_urls must be an array of credential-free http(s) URLs")
            elif len(set(fallback_urls)) != len(fallback_urls) or entry.get("url") in fallback_urls:
                fail(errors, where, "fallback_urls must be unique and different from url")
            if "rating" in entry:
                validate_rating(entry["rating"], errors, where)
            entry_id = entry.get("id")
            if not isinstance(entry_id, str) or not ID_RE.fullmatch(entry_id):
                fail(errors, where, "id must match ^[a-z0-9][a-z0-9-]{1,63}$")
            elif entry_id in seen:
                fail(errors, where, f"duplicate id: {entry_id}")
            else:
                seen.add(entry_id)
            for field in ("url", "source"):
                if not is_http_url(entry.get(field)):
                    fail(errors, where, f"{field} must be an http(s) URL without embedded credentials")
            if entry.get("format") not in formats:
                fail(errors, where, f"format must be one of: {', '.join(sorted(formats))}")
            for field in ("name", "license", "notes"):
                if not isinstance(entry.get(field), str) or (field != "notes" and not entry[field].strip()):
                    fail(errors, where, f"{field} must be a non-empty string" if field != "notes" else "notes must be a string")
            entries.append((category, entry))
    verified = validate_playback_evidence(entries, errors, evidence_path=catalog_dir / "playback-evidence.json")
    validate_verification_report(errors)
    if playback_ids is not None:
        playback_ids.update(verified)
    return entries


class PublicRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        if not is_http_url(new_url):
            raise ValueError("redirected to a non-http(s) URL")
        validate_public_target(new_url)
        if len(getattr(request, "redirect_history", [])) >= 4:
            raise ValueError("too many redirects")
        return super().redirect_request(request, response, code, message, headers, new_url)


def fetch_bounded(url: str, opener=None, request_profile: str = "catalog", max_body: int = MAX_BODY) -> tuple[bytes, str, int]:
    if not isinstance(max_body, int) or max_body <= 0:
        raise ValueError("max_body must be a positive integer")
    validate_public_target(url)
    headers = {"User-Agent": "tvbox-resource-catalog-check/1.0", "Accept": "*/*"}
    if request_profile == "tvbox":
        headers.update({"User-Agent": "okhttp/3.15", "X-Requested-With": "com.github.tvbox.osc"})
    elif request_profile != "catalog":
        raise ValueError("request_profile must be 'catalog' or 'tvbox'")
    request = urllib.request.Request(url, headers=headers)
    with (opener.open(request, timeout=TIMEOUT) if opener else urllib.request.urlopen(request, timeout=TIMEOUT)) as response:
        final = urllib.parse.urlparse(response.geturl())
        if final.scheme not in {"http", "https"}:
            raise ValueError("redirected to a non-http(s) URL")
        try:
            body = response.read(max_body + 1)
        except http.client.IncompleteRead as exc:
            raise ValueError(f"incomplete response: received {len(exc.partial)} bytes") from None
        if len(body) > max_body:
            raise ValueError(f"response exceeded {max_body} bytes")
        return body, response.headers.get_content_type(), response.status


IMAGE_MAGIC = {
    b"\xff\xd8\xff": "jpeg",
    b"GIF8": "gif",
    b"\x89PNG\r\n\x1a\n": "png",
    b"BM": "bmp",
    b"RIFF": "webp",
}


def _drop_trailing_commas(text: str) -> str:
    """Strip commas that precede a closing bracket, which clients accept and json.loads does not."""
    out: list[str] = []
    index, length = 0, len(text)
    in_string = escaped = False
    while index < length:
        char = text[index]
        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
        elif char == ",":
            look = index + 1
            while look < length and text[look] in " \t\r\n":
                look += 1
            if look < length and text[look] in "]}":
                index += 1
                continue
        out.append(char)
        index += 1
    return "".join(out)


def _strip_jsonc(text: str) -> str:
    """Remove // and /* */ comments that TVBox clients skip, leaving strings untouched."""
    out: list[str] = []
    index, length = 0, len(text)
    in_string = escaped = False
    while index < length:
        char = text[index]
        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            out.append(char)
            index += 1
        elif text.startswith("//", index):
            while index < length and text[index] not in "\r\n":
                index += 1
        elif text.startswith("/*", index):
            end = text.find("*/", index + 2)
            index = length if end == -1 else end + 2
        else:
            out.append(char)
            index += 1
    return "".join(out)


def tvbox_json_document(body: bytes) -> dict:  # noqa: C901 - four short response shapes
    """Parse a config body, unwrapping the disguises upstream servers actually use.

    Several hosts answer a configuration request with an image content type and an image
    payload that has a JSON document pasted after the image bytes, or with a base64 body.
    Both are read by clients and must not be scored as failures. Success still requires a
    parsable object: the check reports the body as it really is, it does not claim playback.
    """
    text = body.decode("utf-8-sig", errors="replace")
    first = text.lstrip()[:1]
    if first == "{":
        # The body is already a document; the other paths exist only for disguised payloads.
        # Clients tolerate the comments and trailing commas maintainers actually ship, so the
        # probe uses the same leniency instead of failing a config a client would load.
        decoder = json.JSONDecoder()
        try:
            doc, end = decoder.raw_decode(text.lstrip())
        except ValueError:
            doc, end = None, None
        if isinstance(doc, dict) and not text.lstrip()[end:].strip(" \r\n\t"):
            return doc
        stripped = _drop_trailing_commas(_strip_jsonc(text)).lstrip()
        try:
            doc, end = json.JSONDecoder(strict=False).raw_decode(stripped)
        except ValueError:
            raise ValueError("config body is not parsable JSON (comments and trailing commas are tolerated)") from None
        if not isinstance(doc, dict):
            raise ValueError("config body is not a JSON object")
        return doc
    magic = next((name for prefix, name in IMAGE_MAGIC.items() if body.startswith(prefix)), None)
    if text.lstrip().lower().startswith(("<!doctype", "<html")):
        raise ValueError("served an HTML page instead of a configuration")
    attempts: list[tuple[str, str]] = []
    if magic:
        start = text.find("{")
        if start == -1:
            raise ValueError(f"{magic} image response carries no JSON document")
        attempts.append((f"{magic}-wrapped JSON", text[start:]))
    else:
        # Chinese comments and headings are ordinary in shipped configurations, so binary is
        # recognised by control bytes rather than by the presence of non-ASCII text.
        controls = sum(1 for char in text[:4096] if ord(char) < 9 or 13 < ord(char) < 32)
        if controls > 8:
            raise ValueError("config body is binary and carries no JSON document")
        attempts.append(("body", text))
        attempts.append(("body", _drop_trailing_commas(_strip_jsonc(text))))
        stripped = text.strip()
        if stripped and "{" not in text[:64]:
            try:
                decoded = base64.b64decode(stripped, validate=False)
            except ValueError:
                decoded = b""
            if decoded:
                attempts.append(("base64-body", decoded.decode("latin-1")))
    last: Exception | None = None
    for label, candidate in attempts:
        try:
            doc = json.loads(candidate.lstrip())
        except ValueError as exc:
            last = exc
            continue
        if not isinstance(doc, dict):
            last = ValueError(f"{label} is not a JSON object")
            continue
        if len(candidate) < len(text) - 64:
            doc["__decoded_as"] = label
        return doc
    raise ValueError(f"config body is not parsable JSON ({last})")


def validate_remote(category: str, entry: dict, opener=None, request_profile: str = "catalog") -> str:
    format_name = entry.get("format")
    if format_name == "epg-xml":
        max_body = MAX_EPG_BODY
    elif format_name == "logo-library":
        max_body = MAX_LOGO_BODY
    elif format_name in {"m3u", "txt"}:
        max_body = MAX_LIVE_BODY
    else:
        max_body = MAX_BODY
    body, content_type, status = fetch_bounded(entry["url"], opener=opener, request_profile=request_profile, max_body=max_body)
    if not 200 <= status < 300:
        raise ValueError(f"HTTP status {status}")
    fmt = entry["format"]
    if fmt == "tvbox-multi":
        doc = tvbox_json_document(body)
        if not isinstance(doc, dict) or not isinstance(doc.get("urls"), list) or not doc["urls"]:
            raise ValueError("multi-repository JSON must contain a non-empty urls array")
        for index, item in enumerate(doc["urls"]):
            if not isinstance(item, dict) or not isinstance(item.get("url"), str) or not is_http_url(item["url"]):
                raise ValueError(f"urls[{index}] must contain an absolute http(s) url")
    elif fmt == "tvbox-json":
        doc = tvbox_json_document(body)
        if not isinstance(doc, dict):
            raise ValueError("TVBox single-source config must be a JSON object")
        if not any(key in doc for key in ("sites", "urls", "lives")):
            raise ValueError("JSON object has none of the expected TVBox fields: sites, urls, lives")
    elif fmt == "tvbox-live-json":
        doc = tvbox_json_document(body)
        if not isinstance(doc, dict) or not isinstance(doc.get("lives"), list):
            raise ValueError("TVBox live JSON must contain a lives array")
    elif fmt == "m3u":
        text = body.decode("utf-8-sig", errors="strict")
        if not text.lstrip().startswith("#EXTM3U") or "#EXTINF" not in text:
            raise ValueError("M3U should begin with #EXTM3U and contain #EXTINF")
    elif fmt == "txt":
        text = body.decode("utf-8-sig", errors="strict")
        if not any("," in line and line.strip() for line in text.splitlines()):
            raise ValueError("TXT playlist contains no recognizable channel lines")
    elif fmt == "epg-xml":
        root = ET.fromstring(body)
        if root.tag not in {"tv", "tv-programme", "programme"}:
            raise ValueError(f"unexpected XML root element: {root.tag}")
    elif fmt == "logo-library":
        if not body:
            raise ValueError("logo-library response body is empty")
        if "json" not in content_type.lower():
            raise ValueError(f"logo-library expected JSON, got {content_type}")
        try:
            logos = json.loads(body.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"logo-library response is not valid JSON ({exc})") from None
        if not isinstance(logos, list) or not logos:
            raise ValueError("logo-library JSON must be a non-empty array")
        for index, logo in enumerate(logos):
            if not isinstance(logo, dict) or not isinstance(logo.get("url"), str) or not is_http_url(logo["url"]):
                raise ValueError(f"logo-library[{index}] must contain an absolute http(s) url")
    elif fmt in {"documentation", "utility", "project", "web", "link-page"}:
        if not body:
            raise ValueError("response body is empty")
        if fmt in {"web", "link-page"} and b"html" not in content_type.encode() and content_type not in {"application/xhtml+xml", "text/plain"}:
            raise ValueError(f"expected an HTML landing page, got {content_type}")
        if fmt in {"web", "link-page"} and content_type in {"text/html", "application/xhtml+xml"}:
            head = body[:4096].lstrip().lower()
            if not head.startswith((b"<!doctype html", b"<html")):
                raise ValueError("landing page did not return document markup (gateway or interstitial page)")
    return "ok"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-urls", action="store_true", help="make bounded HTTP requests to catalog URLs")
    parser.add_argument("--request-profile", choices=("catalog", "tvbox"), default="catalog",
                        help="headers for URL checks; tvbox simulates config-fetch headers only, not playback")
    parser.add_argument("--report", type=Path, help="write JSON probe report to this path")
    args = parser.parse_args()

    errors: list[str] = []
    entries = validate_catalog(errors)
    probes = []
    if args.check_urls:
        opener = urllib.request.build_opener(PublicRedirectHandler())
        for category, entry in entries:
            try:
                validate_remote(category, entry, opener=opener, request_profile=args.request_profile)
                probes.append({"id": entry.get("id"), "status": "ok", "checked_at": dt.datetime.now(dt.timezone.utc).isoformat()})
            except (OSError, urllib.error.URLError, TimeoutError, ValueError, UnicodeError, json.JSONDecodeError, ET.ParseError) as exc:
                probes.append({"id": entry.get("id"), "status": "failed", "error": str(exc), "checked_at": dt.datetime.now(dt.timezone.utc).isoformat()})

    for message in errors:
        print(f"ERROR {message}", file=sys.stderr)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        report = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "probes": probes}
        temp = args.report.with_suffix(args.report.suffix + f".{os.getpid()}.tmp")
        try:
            temp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temp.replace(args.report)
        finally:
            temp.unlink(missing_ok=True)
    failed = sum(item["status"] == "failed" for item in probes)
    print(f"Catalog validation: {len(entries)} entries, {len(errors)} metadata errors, {len(probes)} URL probes, {failed} probe failures")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
