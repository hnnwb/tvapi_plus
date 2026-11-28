#!/usr/bin/env python3
"""Build local provenance-aware candidate and sampled-decoded live playlists.

The optional channel probe fetches bounded public HTTP(S) samples and locally decodes them;
it is not client playback or proof of ongoing availability or redistribution rights.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import datetime as dt
import html
import ipaddress
import json
import re
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from dataclasses import dataclass, field, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_catalog  # noqa: E402

DEFAULT_CONFIG = ROOT / "config" / "custom-live-sources.json"
DEFAULT_CATALOG = ROOT / "catalog"
DEFAULT_OUTPUT = ROOT / "dist"
MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_CHANNEL_BYTES = 256 * 1024
TIMEOUT_SECONDS = 4
DECODE_TIMEOUT_SECONDS = 5
MAX_CONCURRENT_PER_HOST = 2
MAX_CHANNEL_PROBES_PER_HOST = 12
MAX_PROBES_PER_RUN = 500
PROBE_BUDGET_SECONDS = 12
PROBE_RUN_BUDGET_SECONDS = 20 * 60
MAX_PROBE_BYTES = 256 * 1024
MAX_FFMPEG_OUTPUT_BYTES = 64 * 1024
_probe_lock = threading.Lock()
_host_semaphores: dict[str, threading.BoundedSemaphore] = {}
GROUP_ORDER = ["央视", "卫视", "地方频道", "特色频道", "港澳台", "国际频道", "其他频道"]
QUALITY_SUFFIX = re.compile(r"\s*(?:\[[^\]]*(?:geo-blocked|not\s*24/7)[^\]]*\]|\([^)]*\b(?:\d{3,4}[pi]|sd|hd|fhd|uhd)\b[^)]*\))\s*", re.I)
VOD_NAME = re.compile(r"(?i)(回放|录播|点播|宣传|群号|公众号|更新时间|永不失联|电影片段|全场回放|精选\d+首|\bvod\b|\bvideo\s*on\s*demand\b|\bmovie\s*on\s*demand\b|\banime\s*on\s*demand\b|\bfull\s*match\s*replay\b|\breplay\s*of\s*\d{4}\b|^\d{6,8}[-_]\d+|\([^)]*(?:电影|影片|恐怖片|剧情片)\s*\))")
VOD_PATH = re.compile(r"(?i)\.(?:mp4|mkv|mov|avi|wmv)(?:$|[?#])")
SPECIAL_TERMS = re.compile(r"(?i)(少儿|儿童|教育|纪录|戏曲|音乐|电影|影视|体育|财经|新闻|法治|文化|旅游|购物|天气|生活|综艺|宗教|kids|news|sports|movie|music|documentary|education|religious|weather|culture|business|entertainment)")
PROVINCES = "北京上海天津重庆河北山西辽宁吉林黑龙江江苏浙江安徽福建江西山东河南湖北湖南广东海南四川贵州云南陕西甘肃青海台湾内蒙古广西西藏宁夏新疆"
REGION_TERMS = re.compile(r"(" + "|".join(map(re.escape, ["北京", "上海", "天津", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南", "广东", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海", "内蒙古", "广西", "西藏", "宁夏", "新疆", "广州", "深圳", "杭州", "南京", "成都", "武汉", "长沙", "济南", "青岛", "大连", "厦门", "福州", "南昌", "郑州", "合肥", "昆明", "贵阳", "兰州", "西安", "哈尔滨", "长春", "沈阳", "石家庄", "乌鲁木齐", "拉萨", "银川", "呼和浩特", "苏州", "无锡", "宁波", "温州", "佛山", "东莞", "珠海", "汕头", "湛江", "潮州", "安顺", "赤峰", "滁州", "敦煌", "邯郸", "合阳", "鹤壁", "衡水", "淮安", "黄山", "济宁", "荆门", "酒泉", "凉山", "南充", "南通", "萍乡", "钦州", "泉州", "日照", "三门峡", "汕尾", "韶关", "石嘴山", "四平", "朔州", "铜川", "通化", "潍坊", "新乡", "徐州", "延边", "宜昌", "玉溪", "张家口", "肇庆", "中山", "周口"])) + r")")
REGION_ENGLISH = re.compile(r"(?i)\b(?:beijing|shanghai|tianjin|chongqing|hebei|shanxi|liaoning|jilin|heilongjiang|jiangsu|zhejiang|anhui|fujian|jiangxi|shandong|henan|hubei|hunan|guangdong|hainan|sichuan|guizhou|yunnan|shaanxi|gansu|qinghai|guangxi|tibet|ningxia|xinjiang|guangzhou|shenzhen|hangzhou|nanjing|chengdu|wuhan|changsha|jinan|qingdao|dalian|xiamen|fuzhou|nanchang|zhengzhou|hefei|kunming|guiyang|lanzhou|xian|harbin|changchun|shenyang|shijiazhuang|urumqi|lhasa|yinchuan|hohhot|suzhou|wuxi|ningbo|wenzhou|foshan|dongguan|zhuhai|shantou|zhanjiang|chaozhou|anshun|chifeng|chuzhou|dunhuang|handan|heyang|hebi|hengshui|huaian|huangshan|jining|jingmen|jiuquan|liangshan|nanchong|nantong|pingxiang|qinzhou|quanzhou|rizhao|sanmenxia|shanwei|shaoguan|shizuishan|siping|shuozhou|tongchuan|tonghua|weifang|xinxiang|xuzhou|yanbian|yichang|yuxi|zhangjiakou|zhaoqing|zhongshan|zhoukou)(?:\b|\s)")


@dataclass
class Channel:
    name: str
    url: str
    source_id: str
    source_name: str
    source_url: str
    catalog_status: str
    group_hint: str = ""
    tvg_id: str = ""
    logo: str = ""
    country: str = ""
    group: str = "其他频道"
    status: str = "not-tested"
    status_detail: str = ""
    alternatives: list[dict] = field(default_factory=list)
    source_feed_url: str = ""


def sensitive_query_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", key.lower())
    sensitive = {
        "token", "access_token", "authtoken", "auth", "authorization", "secret", "signature", "sign",
        "credential", "password", "passwd", "session", "wssecret", "txsecret", "expires", "expire",
        "timestamp", "nonce", "accessid", "accesscode", "hdnts", "hdnea", "hmac", "policy", "jwt",
        "vkey", "ckey", "authkey", "playtoken", "ticket", "userid", "username", "apikey", "key",
    }
    return normalized in sensitive or normalized.endswith(("token", "secret", "signature", "authkey", "accesscode"))


SAFE_QUERY_KEYS = {"id", "cid", "chid", "channel", "lang", "language", "quality", "type", "source", "format", "output", "stream", "program", "platform", "client"}


def sensitive_path_segment(segment: str) -> bool:
    decoded = urllib.parse.unquote(segment).split(".", 1)[0]
    compact = re.sub(r"[^A-Za-z0-9_-]", "", decoded)
    if re.fullmatch(r"(?i)[0-9a-f]{32,}", compact):
        return True
    has_letter = bool(re.search(r"[A-Za-z]", compact))
    has_digit = bool(re.search(r"[0-9]", compact))
    mixed_case = bool(re.search(r"[a-z]", compact) and re.search(r"[A-Z]", compact))
    return len(compact) >= 14 and has_letter and has_digit and (mixed_case or len(compact) >= 20)


def safe_url(url: str) -> str:
    """Redact userinfo, query values and likely bearer-like path segments in reports."""
    try:
        if not check_catalog.is_http_url(url):
            return "[REDACTED_URL]"
        parsed = urllib.parse.urlsplit(url)
        host = parsed.hostname or ""
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        try:
            if parsed.port:
                host += f":{parsed.port}"
        except ValueError:
            pass
        path_parts = ["[REDACTED]" if sensitive_path_segment(part) else part for part in parsed.path.split("/")]
        query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        redacted = [(key, "[REDACTED]") for key, _ in query]
        return urllib.parse.urlunsplit((parsed.scheme, host, "/".join(path_parts), urllib.parse.urlencode(redacted), ""))
    except (TypeError, ValueError):
        return "[REDACTED_URL]"


def channel_url_allowed(url: str, reject_vod_path: bool = True) -> tuple[bool, str]:
    if not check_catalog.is_http_url(url):
        return False, "non-http-url"
    parsed = urllib.parse.urlsplit(url)
    if parsed.username or parsed.password:
        return False, "embedded-credentials"
    if parsed.fragment:
        return False, "url-fragment-not-supported"
    if re.search(r"%(?:00|0a|0d)", parsed.path, re.I):
        return False, "encoded-control-character"
    query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query_keys = [key for key, _ in query_pairs]
    if any(sensitive_query_key(key) for key in query_keys):
        return False, "credential-or-expiring-query"
    if any(key.lower() not in SAFE_QUERY_KEYS for key in query_keys):
        return False, "unrecognized-query-parameter"
    if any(len(value) > 64 or not re.fullmatch(r"[A-Za-z0-9._~-]*", value) for _, value in query_pairs):
        return False, "opaque-or-long-query-value"
    if any((len(value) > 32 and not value.isdecimal()) or re.fullmatch(r"(?i)[a-f0-9]{24,}", value)
           for _, value in query_pairs):
        return False, "opaque-or-long-query-value"
    if reject_vod_path and VOD_PATH.search(parsed.path):
        return False, "vod-file-extension"
    decoded_path = urllib.parse.unquote(parsed.path)
    if any(segment in {".", ".."} for segment in decoded_path.split("/")):
        return False, "path-traversal-segment"
    if any(sensitive_path_segment(part) for part in decoded_path.split("/") if part):
        return False, "opaque-or-signed-path-segment"
    if parsed.scheme not in {"http", "https"}:
        return False, "unsupported-scheme"
    host = (parsed.hostname or "").lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".internal", ".lan")):
        return False, "non-public-host"
    try:
        address = ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        return False, "non-public-address"
    return True, "included"


def _extinf_fields(line: str) -> tuple[str, dict[str, str]]:
    payload = line.partition(":")[2]
    quoted = False
    separator = -1
    for index, char in enumerate(payload):
        if char == '"':
            quoted = not quoted
        elif char == "," and not quoted:
            separator = index
            break
    if separator < 0 or quoted:
        return "", {}
    metadata, display = payload[:separator], payload[separator + 1:].strip()
    attrs = {key: html.unescape(value) for key, value in re.findall(r'([A-Za-z0-9_-]+)="([^\"]*)"', metadata)}
    return display, attrs


def parse_m3u(text: str) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    counts = defaultdict(int)
    metadata = None
    extgrp = ""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF:"):
            if metadata is not None:
                counts["missing_url"] += 1
            metadata = line
        elif line.startswith("#EXTGRP:"):
            extgrp = line.partition(":")[2].strip()
        elif line.startswith("#"):
            continue
        elif metadata is not None:
            name, attrs = _extinf_fields(metadata)
            if name and check_catalog.is_http_url(line):
                rows.append({"name": name, "url": line, "group": attrs.get("group-title", "") or extgrp,
                             "tvg_id": attrs.get("tvg-id", ""), "logo": attrs.get("tvg-logo", ""),
                             "country": attrs.get("tvg-country", "")})
                counts["parsed"] += 1
            else:
                counts["invalid_rows"] += 1
            metadata = None
            extgrp = ""
        elif metadata is None and line.startswith(("http://", "https://")):
            counts["orphan_urls"] += 1
    if metadata is not None:
        counts["missing_url"] += 1
    return rows, dict(counts)


def parse_txt(text: str) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    counts = defaultdict(int)
    current_group = ""
    for raw in text.splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line or line.startswith(("#", "//")):
            continue
        if ",#genre#" in line.lower():
            current_group = line[:line.lower().find(",#genre#")].strip()
            counts["group_headers"] += 1
            continue
        if "," not in line:
            counts["unrecognized_lines"] += 1
            continue
        name, url = line.split(",", 1)
        name, url = name.strip(), url.strip()
        # TVBox TXT source annotations such as $LR•6•IPV4『线路1』 are not part of the URI.
        if "$" in url:
            url = url.split("$", 1)[0].strip()
        if name and url:
            rows.append({"name": name, "url": url, "group": current_group,
                         "tvg_id": "", "logo": "", "country": ""})
            counts["parsed"] += 1
    return rows, dict(counts)


def clean_name(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip()
    value = QUALITY_SUFFIX.sub(" ", value)
    value = re.sub(r"(?i)[\s_-]*(?:超高清|高清|标清|普清|高码|fhd|uhd|hd|sd|4k|8k)$", "", value)
    value = re.sub(r"\s+", " ", value).replace(",", " ").replace("\r", " ").replace("\n", " ").strip(" -_·|，")
    # Strip source-specific bracket decorations, not meaningful channel words.
    value = re.sub(r"^(?:🇨🇳\s*)+", "", value)
    value = re.sub(r"^\([^)]{1,4}\)", "", value).strip()
    value = re.sub(r"(?i)^CCTV\s*[-_ ]?\s*(\d{1,2})\b", r"CCTV\1", value)
    value = re.sub(r"(?i)^CCTV\s*[-_ ]?\s*(\d{1,2})(?=\D)", r"CCTV\1", value)
    return value or "未命名频道"


def canonical_name(name: str, tvg_id: str = "", country: str = "") -> str:
    cleaned = clean_name(name)
    cctv = re.fullmatch(r"(?i)cctv\s*[-_ ]?\s*(\d{1,2})(\+)?[\s_-]*(?:(?:综合|财经|军事|国防军事|农业农村|科教|戏曲|社会与法|新闻|少儿|音乐|奥林匹克|奥运|纪录|体育赛事|电视剧|综艺|中文国际|国际|体育|电影).*)?", cleaned)
    if cctv:
        return "id:cctv" + cctv.group(1) + ("plus" if cctv.group(2) else "")
    if tvg_id:
        stable_id = tvg_id.split("@", 1)[0].lower()
        match = re.fullmatch(r"cctv[-_ ]*(\d+)(?:\.(?:cn|chn))?", stable_id)
        if match:
            return "id:cctv" + match.group(1)
        if stable_id:
            return "id:" + stable_id
    value = cleaned.lower()
    value = re.sub(r"(?:超高清|高清|标清|高码|普清|fhd|uhd|hd|sd)$", "", value, flags=re.I)
    value = re.sub(r"\([^)]*\)|\[[^]]*\]", "", value)
    value = re.sub(r"[^0-9a-z\u3400-\u9fff]+", "", value)
    inferred_country = country.lower()
    if not inferred_country and tvg_id:
        match = re.search(r"\.([a-z]{2})(?:@|$)", tvg_id, re.I)
        inferred_country = match.group(1).lower() if match else ""
    return "name:" + value + ("|country:" + inferred_country if inferred_country else "")


def classify(name: str, tvg_id: str = "", country: str = "", group_hint: str = "") -> str:
    combined = f"{name} {tvg_id} {country} {group_hint}".lower()
    country_code = country.upper().strip()
    if not country_code and tvg_id:
        match = re.search(r"\.([a-z]{2})(?:@|$)", tvg_id, re.I)
        country_code = match.group(1).upper() if match else ""
    has_han = any("\u3400" <= char <= "\u9fff" for char in name + " " + group_hint)
    if country_code in {"HK", "TW", "MO"} or any(x in combined for x in ("香港", "台湾", "澳門", "澳门", "hong kong", "taiwan", "macau")):
        return "港澳台"
    if re.search(r"(?i)(?:cctv\s*[-_ ]?\s*\d|cctv\+|央视|中央电视台|央视频道)", name):
        return "央视"
    if country_code and country_code not in {"CN", "CHN"}:
        return "国际频道"
    is_china = country_code in {"CN", "CHN"} or bool(re.search(r"\.cn(?:@|$)", tvg_id, re.I)) or has_han
    china_indicators = is_china or bool(REGION_ENGLISH.search(name + " " + group_hint))
    satellite_marker = re.search(r"(?i)(?:卫视|卫星)", name + " " + group_hint)
    if satellite_marker or (china_indicators and re.search(r"(?i)satellite\s*(?:tv|channel)?", name + " " + group_hint)):
        return "卫视"
    if is_china:
        if REGION_TERMS.search(name) or REGION_ENGLISH.search(name) or re.search(r"(地方|省|市|县|州|综合|融媒|地面|地方台|comprehensive|municipal|prefecture|county|provincial|city channel)", name + " " + group_hint, re.I):
            return "地方频道"
        if SPECIAL_TERMS.search(name) or SPECIAL_TERMS.search(group_hint):
            return "特色频道"
        if has_han:
            return "地方频道"
        return "其他频道"
    if country_code:
        return "国际频道"
    return "特色频道" if SPECIAL_TERMS.search(name + " " + group_hint) else "其他频道"


def load_catalog(catalog_dir: Path) -> tuple[list[dict], dict]:
    entries = json.loads((catalog_dir / "live.json").read_text(encoding="utf-8"))
    report_path = catalog_dir.parent / "probe-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {"probes": []}
    statuses = {row.get("id"): row for row in report.get("probes", []) if isinstance(row, dict)}
    return entries, statuses


def decode_playlist(body: bytes) -> str:
    try:
        return body.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError:
        return body.decode("gb18030", errors="replace")


def _safe_exception(exc: Exception, limit: int = 180) -> str:
    message = str(exc)
    message = re.sub(r"https?://[^\s'\"]+", lambda match: safe_url(match.group(0)), message)
    message = re.sub(r"(?i)(token|auth|key|secret|signature|sig|credential|password|passwd|session|wssecret|txsecret|expires|expire|timestamp|nonce)=([^&\s]+)", r"\1=[REDACTED]", message)
    return f"{type(exc).__name__}: {message[:limit]}"


def fetch_source(entry: dict, opener, max_body: int = MAX_SOURCE_BYTES) -> tuple[bytes, str, int]:
    check_catalog.validate_public_target(entry["url"])
    return check_catalog.fetch_bounded(entry["url"], opener=opener, max_body=max_body)


def _fetch_source_job(entry: dict, status: str = "unknown",
                      max_source_bytes: int = MAX_SOURCE_BYTES) -> tuple[dict, list[Channel], dict]:
    opener = urllib.request.build_opener(check_catalog.PublicRedirectHandler())
    source_id = entry["id"]
    item_report = {"id": source_id, "name": entry["name"],
                   "catalog_source_reference": safe_url(entry.get("source", "")),
                   "catalog_status": status, "fetch_status": "not-tested",
                   "parsed": 0, "accepted": 0, "rejected": {}, "error": None}
    source_rows: list[Channel] = []
    try:
        # Share a small per-host gate between list fetches and channel probes.
        with _host_gate(entry["url"]):
            body, content_type, http_status = fetch_source(entry, opener, max_source_bytes)
        if not 200 <= http_status < 300:
            raise ValueError(f"HTTP status {http_status}")
        text = decode_playlist(body)
        parser = parse_m3u if entry["format"] == "m3u" else parse_txt
        raw_rows, parser_counts = parser(text)
        item_report.update({"fetch_status": "ok", "http_status": http_status,
                            "content_type": content_type, "bytes": len(body),
                            "parsed": len(raw_rows), "parser_counts": parser_counts})
        if not raw_rows:
            item_report["fetch_status"] = "failed"
            item_report["error"] = "ValueError: playlist contained no recognized channel rows"
            return item_report, source_rows, {}
        rejected = defaultdict(int)
        for raw in raw_rows:
            allowed, reason = channel_url_allowed(raw["url"])
            raw_name = raw["name"].strip()
            clean = clean_name(raw_name)
            if not allowed:
                rejected[reason] += 1
                continue
            if not clean or clean == "未命名频道":
                rejected["empty-name"] += 1
                continue
            if re.search(r"(?i)(geo[\s_-]*blocked|not\s*24/7|地理限制|仅限.*地区)", raw_name):
                rejected["annotated-unavailable"] += 1
                continue
            if VOD_NAME.search(raw_name):
                rejected["vod-or-promotion-name"] += 1
                continue
            logo = raw.get("logo", "")
            logo_allowed, _ = channel_url_allowed(logo) if logo else (False, "missing")
            if not logo_allowed:
                logo = ""
            group = classify(clean, raw.get("tvg_id", ""), raw.get("country", ""), raw.get("group", ""))
            source_rows.append(Channel(name=clean, url=raw["url"], source_id=source_id,
                source_name=entry["name"], source_url=entry["source"], catalog_status=status,
                source_feed_url=entry["url"], group_hint=raw.get("group", ""), tvg_id=raw.get("tvg_id", ""),
                logo=logo, country=raw.get("country", ""), group=group))
        item_report["accepted"] = len(source_rows)
        item_report["rejected"] = dict(rejected)
    except Exception as exc:
        item_report["fetch_status"] = "failed"
        item_report["error"] = _safe_exception(exc)
    return item_report, source_rows, {}


def validate_config(config: dict, catalog_dir: Path) -> dict:
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise ValueError("custom live config must have schema_version 1")
    selected = config.get("source_ids")
    excluded = config.get("excluded_source_ids")
    if not isinstance(selected, list) or not all(isinstance(item, str) for item in selected):
        raise ValueError("source_ids must be a list of strings")
    if not isinstance(excluded, dict) or not all(isinstance(key, str) and isinstance(value, str) and value.strip() for key, value in excluded.items()):
        raise ValueError("excluded_source_ids must map IDs to non-empty rationale strings")
    if len(selected) > 100 or len(set(selected)) != len(selected):
        raise ValueError("source_ids must be unique and contain at most 100 entries")
    policy = config.get("policy")
    if not isinstance(policy, dict):
        raise ValueError("policy must be an object")
    numeric_limits = {
        "max_source_bytes": (1, MAX_SOURCE_BYTES),
        "max_channel_probe_bytes": (1, MAX_PROBE_BYTES),
        "channel_probe_timeout_seconds": (1, TIMEOUT_SECONDS),
        "channel_probe_budget_seconds": (1, PROBE_BUDGET_SECONDS),
        "max_channel_probe_run_seconds": (1, PROBE_RUN_BUDGET_SECONDS),
        "max_channel_probes_per_run": (1, MAX_PROBES_PER_RUN),
    }
    for key, (minimum, maximum) in numeric_limits.items():
        value = policy.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
            raise ValueError(f"policy.{key} must be an integer in {minimum}..{maximum}")
    overlap = set(selected) & set(excluded)
    if overlap:
        raise ValueError("source ids cannot be both selected and excluded: " + ", ".join(sorted(overlap)))
    groups = policy.get("channel_groups")
    if groups != GROUP_ORDER:
        raise ValueError("policy.channel_groups must match the supported group order")
    catalog, _ = load_catalog(catalog_dir)
    if not isinstance(catalog, list) or not all(isinstance(entry, dict) for entry in catalog):
        raise ValueError("catalog/live.json must be an array of objects")
    catalog_id_values = [entry.get("id") for entry in catalog]
    if not all(isinstance(value, str) and value for value in catalog_id_values):
        raise ValueError("catalog/live.json entries must have non-empty string IDs")
    if len(catalog_id_values) != len(set(catalog_id_values)):
        raise ValueError("catalog/live.json contains duplicate IDs")
    catalog_ids = set(catalog_id_values)
    missing = set(selected) - catalog_ids
    unknown_excluded = set(excluded) - catalog_ids
    unaccounted = catalog_ids - set(selected) - set(excluded)
    if missing or unknown_excluded or unaccounted:
        raise ValueError("source selection must account for catalog IDs; "
                         f"missing={sorted(missing)}, unknown_excluded={sorted(unknown_excluded)}, "
                         f"unaccounted={sorted(unaccounted)}")
    unsafe = []
    invalid_entries = []
    by_id = {entry["id"]: entry for entry in catalog}
    for source_id in selected:
        entry = by_id[source_id]
        allowed, reason = channel_url_allowed(entry.get("url", ""))
        if not allowed:
            unsafe.append(f"{source_id} ({reason})")
        if entry.get("format") not in {"m3u", "txt"}:
            invalid_entries.append(f"{source_id} (unsupported format)")
        if not isinstance(entry.get("name"), str) or not entry["name"].strip() or not isinstance(entry.get("source"), str):
            invalid_entries.append(f"{source_id} (missing source metadata)")
    if unsafe:
        raise ValueError("selected source URLs fail channel URL safety checks: " + ", ".join(unsafe))
    if invalid_entries:
        raise ValueError("selected source entries are not supported: " + ", ".join(invalid_entries))
    return {"catalog_sources": len(catalog_ids), "selected_sources": len(selected),
            "excluded_sources": len(excluded), "selected_source_ids": selected}


def collect_candidates(config: dict, catalog_dir: Path, workers: int = 8) -> tuple[list[Channel], dict]:
    validate_config(config, catalog_dir)
    max_source_bytes = config["policy"]["max_source_bytes"]
    catalog, source_statuses = load_catalog(catalog_dir)
    by_id = {entry["id"]: entry for entry in catalog}
    missing = [source_id for source_id in config["source_ids"] if source_id not in by_id]
    if missing:
        raise ValueError("configured source ids are absent from live.json: " + ", ".join(missing))
    entries = [by_id[source_id] for source_id in config["source_ids"]]
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_fetch_source_job, entry, source_statuses.get(entry["id"], {}).get("status", "unknown"), max_source_bytes): entry["id"]
            for entry in entries
        }
        for future in concurrent.futures.as_completed(futures):
            source_id = futures[future]
            try:
                results[source_id] = future.result()
            except Exception as exc:
                entry = by_id[source_id]
                results[source_id] = ({"id": source_id, "name": entry["name"],
                    "catalog_status": source_statuses.get(source_id, {}).get("status", "unknown"),
                    "fetch_status": "failed", "parsed": 0, "accepted": 0, "rejected": {},
                    "error": _safe_exception(exc)}, [], {})
    source_rows: list[Channel] = []
    source_report: list[dict] = []
    counts = defaultdict(int)
    for entry in entries:
        item_report, rows, _ = results[entry["id"]]
        source_rows.extend(rows)
        source_report.append(item_report)
        counts[item_report["fetch_status"]] += 1
    return source_rows, {"sources": source_report, "summary": dict(counts)}


def rank_candidate(channel: Channel, source_order: dict[str, int]) -> tuple:
    status_score = 0 if channel.catalog_status == "ok" else 1
    scheme_score = 0 if channel.url.lower().startswith("https://") else 1
    host = urllib.parse.urlsplit(channel.url).hostname or ""
    host_score = 1 if re.fullmatch(r"\d+(?:\.\d+){3}", host) else 0
    name_score = 0 if any("\u3400" <= ch <= "\u9fff" for ch in channel.name) else 1
    return (status_score, host_score, scheme_score, source_order.get(channel.source_id, 999), name_score, channel.url)


def _normalized_channel_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    try:
        port = parsed.port
    except ValueError:
        port = None
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if port and not ((parsed.scheme.lower() == "http" and port == 80) or (parsed.scheme.lower() == "https" and port == 443)):
        host = f"{host}:{port}"
    query = urllib.parse.urlencode(sorted(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)))
    return urllib.parse.urlunsplit((parsed.scheme.lower(), host, parsed.path, query, ""))


def deduplicate(rows: list[Channel], source_ids: list[str]) -> tuple[list[Channel], dict]:
    """Merge only explicit channel identities; shared placeholder URLs are not identity."""
    source_order = {source_id: index for index, source_id in enumerate(source_ids)}
    components: dict[str, list[Channel]] = defaultdict(list)
    seen_source_rows: set[tuple[str, str, str]] = set()
    exact_url_names: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        normalized_url = _normalized_channel_url(row.url)
        identity = canonical_name(row.name, row.tvg_id, row.country)
        exact_url_names[normalized_url].add(identity)
        guard = (identity, normalized_url, row.source_id)
        if guard not in seen_source_rows:
            seen_source_rows.add(guard)
            components[identity].append(row)

    selected: list[Channel] = []
    for options in components.values():
        options = sorted(options, key=lambda row: rank_candidate(row, source_order))
        winner = replace(options[0], alternatives=[])
        localized = [item for item in options if any("\u3400" <= ch <= "\u9fff" for ch in item.name)]
        if localized:
            candidate = min(localized, key=lambda row: rank_candidate(row, source_order))
            if candidate.group == winner.group:
                winner.name = candidate.name
                winner.logo = candidate.logo or winner.logo
        seen_alternatives: set[tuple[str, str, str]] = set()
        for item in options[1:]:
            normalized_url = _normalized_channel_url(item.url)
            alternative_key = (item.source_id, normalized_url, item.name)
            if alternative_key in seen_alternatives:
                continue
            seen_alternatives.add(alternative_key)
            winner.alternatives.append({
                "source_id": item.source_id, "source_name": item.source_name,
                "name": item.name, "group": item.group,
                "catalog_feed_reference": safe_url(item.source_feed_url),
                "source_reference": safe_url(item.source_url),
                "url": safe_url(item.url), "catalog_status": item.catalog_status,
            })
        selected.append(winner)

    # The same normalized stream URL is one playable endpoint even when feeds label it differently.
    # Keep the best-ranked display row and preserve the alternate labels/source provenance in JSON.
    by_url: dict[str, Channel] = {}
    duplicate_url_count = 0
    for row in sorted(selected, key=lambda item: rank_candidate(item, source_order)):
        url_key = _normalized_channel_url(row.url)
        existing = by_url.get(url_key)
        if existing is None:
            by_url[url_key] = row
            continue
        duplicate_url_count += 1
        seen = {(item.get("source_id"), item.get("url"), item.get("name")) for item in existing.alternatives}
        alias = {"source_id": row.source_id, "source_name": row.source_name,
                 "name": row.name, "group": row.group,
                 "catalog_feed_reference": safe_url(row.source_feed_url),
                 "source_reference": safe_url(row.source_url),
                 "url": safe_url(row.url), "catalog_status": row.catalog_status}
        key = (alias["source_id"], alias["url"], alias["name"])
        if key not in seen:
            existing.alternatives.append(alias)
            seen.add(key)
        for alias in row.alternatives:
            key = (alias.get("source_id"), alias.get("url"), alias.get("name"))
            if key not in seen:
                existing.alternatives.append(alias)
                seen.add(key)

    selected = list(by_url.values())
    selected.sort(key=lambda row: (GROUP_ORDER.index(row.group) if row.group in GROUP_ORDER else len(GROUP_ORDER), row.name.casefold(), row.url))
    duplicate_names = sum(max(0, len(options) - 1) for options in components.values())
    shared_url_conflicts = sum(1 for identities in exact_url_names.values() if len(identities) > 1)
    stats = {"candidate_rows": len(rows), "unique_channels": len(selected),
             "duplicate_source_rows_removed": len(rows) - len(selected),
             "duplicate_channel_urls_removed": duplicate_url_count,
             "duplicate_name_rows_merged": duplicate_names,
             "shared_url_name_conflicts_merged": shared_url_conflicts,
             "channels_with_alternatives": sum(bool(row.alternatives) for row in selected)}
    return selected, stats


def _host_gate(url: str) -> threading.BoundedSemaphore:
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    with _probe_lock:
        if host not in _host_semaphores:
            _host_semaphores[host] = threading.BoundedSemaphore(MAX_CONCURRENT_PER_HOST)
        return _host_semaphores[host]


@contextlib.contextmanager
def _acquire_host(url: str, deadline: float | None):
    gate = _host_gate(url)
    if deadline is None:
        acquired = gate.acquire(timeout=TIMEOUT_SECONDS)
    else:
        acquired = gate.acquire(timeout=max(0.0, min(TIMEOUT_SECONDS, deadline - time.monotonic())))
    if not acquired:
        raise TimeoutError("per-host probe concurrency limit timed out")
    try:
        yield
    finally:
        gate.release()


def _remaining(deadline: float | None, timeout: float = TIMEOUT_SECONDS) -> float:
    if deadline is None:
        return timeout
    remaining = min(timeout, deadline - time.monotonic())
    if remaining <= 0:
        raise TimeoutError("channel probe total time budget exceeded")
    return remaining


def _request_url(url: str) -> str:
    """ASCII-encode a validated HTTP URL without changing its path/query delimiters."""
    if not check_catalog.is_http_url(url):
        raise ValueError("probe URL must be HTTP(S)")
    parsed = urllib.parse.urlsplit(url)
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("probe URL contains unsupported credentials or fragment")
    host = parsed.hostname or ""
    if ":" in host:
        host = f"[{host}]"
    else:
        host = host.encode("idna").decode("ascii")
    if parsed.port is not None:
        host += f":{parsed.port}"
    path = urllib.parse.quote(parsed.path, safe="/%:@!$&'()*+,;=-._~%")
    query = urllib.parse.quote(parsed.query, safe="/?:@!$&'()*+,;=-._~%")
    return urllib.parse.urlunsplit((parsed.scheme.lower(), host, path, query, ""))


def _fetch_probe(url: str, opener, max_bytes: int, timeout: float, deadline: float | None = None) -> tuple[bytes, str, int, str]:
    _remaining(deadline, timeout)
    check_catalog.validate_public_target(url)
    request = urllib.request.Request(_request_url(url), headers={
        "User-Agent": "TVAPIPlus-Custom-Live-Check/1.0",
        "Accept": "*/*",
        "Range": f"bytes=0-{max_bytes - 1}",
    })
    with _acquire_host(url, deadline):
        with opener.open(request, timeout=_remaining(deadline, timeout)) as response:
            final_url = response.geturl()
            final = urllib.parse.urlsplit(final_url)
            if final.scheme not in {"http", "https"}:
                raise ValueError("redirected to unsupported scheme")
            # Recheck the final target so custom/test openers cannot bypass public-address validation.
            check_catalog.validate_public_target(final_url)
            return _read_probe_response(response, max_bytes, timeout, deadline, final_url)


def _read_probe_response(response, max_bytes: int, timeout: float,
                         deadline: float | None, final_url: str) -> tuple[bytes, str, int, str]:
    raw = getattr(getattr(response, "fp", None), "raw", None)
    socket_obj = getattr(raw, "_sock", None)
    chunks = bytearray()
    while len(chunks) <= max_bytes:
        if socket_obj is not None:
            try:
                if socket_obj.fileno() < 0:
                    socket_obj = None
                else:
                    socket_obj.settimeout(_remaining(deadline, timeout))
            except (AttributeError, OSError, ValueError):
                socket_obj = None
        remaining = max_bytes + 1 - len(chunks)
        if remaining <= 0:
            break
        piece = response.read(min(8192, remaining))
        if not piece:
            break
        chunks.extend(piece)
    if len(chunks) > max_bytes:
        del chunks[max_bytes:]
    return bytes(chunks), response.headers.get_content_type(), response.status, final_url


def _looks_html(body: bytes, content_type: str) -> bool:
    head = body[:512].lstrip().lower()
    return "html" in content_type.lower() or head.startswith((b"<!doctype html", b"<html", b"<head"))


def _looks_playlist(body: bytes, content_type: str) -> bool:
    return "mpegurl" in content_type.lower() or body.lstrip().startswith(b"#EXTM3U")


def _media_format(data: bytes, content_type: str) -> str | None:
    if not data or _looks_html(data, content_type) or _looks_playlist(data, content_type):
        return None
    head = data[:16]
    media_type = content_type.lower().split(";", 1)[0].strip()
    if len(data) >= 376 and data[0] == 0x47 and data[188] == 0x47:
        return "mpegts"
    if head.startswith(b"FLV"):
        return "flv"
    if head[4:8] == b"ftyp" or (head.startswith(b"\x00\x00\x00") and b"ftyp" in data[:64]):
        return "mov"
    if head.startswith(b"ID3") or (len(data) > 1 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0):
        return "mp3"
    if len(data) > 2 and data[0] == 0xFF and data[1] & 0xF6 == 0xF0:
        return "aac"
    return {
        "video/mp2t": "mpegts", "application/mp2t": "mpegts",
        "video/mp4": "mov", "audio/mp4": "mov", "application/mp4": "mov",
        "video/x-flv": "flv", "audio/mpeg": "mp3", "audio/aac": "aac",
    }.get(media_type)


def _hls_targets(body: bytes, base_url: str) -> tuple[str | None, str | None, str | None, str | None]:
    """Return (variant, init-map, latest segment, error); byte-range/encrypted HLS is unsupported."""
    text = body.decode("utf-8-sig", errors="replace")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or lines[0] != "#EXTM3U":
        return None, None, None, "not-an-extended-M3U-playlist"
    if any(line.startswith("#EXT-X-BYTERANGE") for line in lines):
        return None, None, None, "byte-range-playlist-not-supported"
    if any(line.startswith(('#EXT-X-KEY:', '#EXT-X-SESSION-KEY:')) and not re.search(r'METHOD=NONE(?:,|$)', line)
           for line in lines):
        return None, None, None, "encrypted-HLS-not-supported"
    if any(line.upper() == "#EXT-X-PLAYLIST-TYPE:VOD" for line in lines):
        return None, None, None, "VOD-HLS-playlist-not-included"
    for index, line in enumerate(lines):
        if line.startswith("#EXT-X-STREAM-INF"):
            for child in lines[index + 1:]:
                if not child.startswith("#"):
                    variant = urllib.parse.urljoin(base_url, child)
                    allowed, _ = channel_url_allowed(variant)
                    return (variant, None, None, None) if allowed else (None, None, None, "invalid-variant-url")
    init_map = None
    for line in lines:
        if line.startswith("#EXT-X-MAP:"):
            match = re.search(r'URI="([^"]+)"', line)
            if not match:
                return None, None, None, "invalid-init-map-tag"
            candidate = urllib.parse.urljoin(base_url, match.group(1))
            allowed, _ = channel_url_allowed(candidate, reject_vod_path=False)
            if not allowed:
                return None, None, None, "invalid-init-map-url"
            init_map = candidate
            break
    segment_lines = []
    for index, line in enumerate(lines):
        if line.startswith("#EXTINF"):
            for child in lines[index + 1:]:
                if not child.startswith("#"):
                    segment_lines.append(child)
                    break
    if not segment_lines:
        return None, init_map, None, "media-playlist-without-segment"
    segment = urllib.parse.urljoin(base_url, segment_lines[-1])
    allowed, _ = channel_url_allowed(segment, reject_vod_path=False)
    if not allowed:
        return None, init_map, None, "invalid-segment-url"
    return None, init_map, segment, None


def _decode_media(data: bytes, input_format: str, timeout: float = DECODE_TIMEOUT_SECONDS) -> tuple[bool, str]:
    """Decode fetched bytes with bounded pipes and no remote protocols."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False, "ffmpeg unavailable; media not decoded"
    if not data or len(data) > MAX_CHANNEL_BYTES * 3:
        return False, "media sample empty or exceeds byte limit"
    if input_format not in {"mpegts", "mov", "flv", "mp3", "aac"}:
        return False, "media container not recognized for safe decoding"
    command = [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-max_alloc", str(32 * 1024 * 1024),
               "-protocol_whitelist", "pipe", "-threads", "1", "-filter_threads", "1",
               "-f", input_format, "-i", "pipe:0", "-map", "0:v:0?", "-map", "0:a:0?",
               "-t", "2", "-f", "framehash", "-hash", "sha256", "pipe:1"]
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, close_fds=True)
    except OSError:
        return False, "unable to start local ffmpeg"
    captured = {"stdout": bytearray(), "stderr": bytearray()}
    overflow = threading.Event()

    def drain(stream, key: str) -> None:
        while True:
            chunk = stream.read(8192)
            if not chunk:
                return
            remaining = MAX_FFMPEG_OUTPUT_BYTES - len(captured[key])
            if remaining > 0:
                captured[key].extend(chunk[:remaining])
            if len(chunk) > remaining:
                overflow.set()
                try:
                    process.kill()
                except OSError:
                    pass

    readers = [threading.Thread(target=drain, args=(process.stdout, "stdout"), daemon=True),
               threading.Thread(target=drain, args=(process.stderr, "stderr"), daemon=True)]
    for reader in readers:
        reader.start()

    def feed() -> None:
        try:
            process.stdin.write(data)
            process.stdin.flush()
        except (BrokenPipeError, OSError):
            pass
        finally:
            try:
                process.stdin.close()
            except OSError:
                pass

    writer = threading.Thread(target=feed, daemon=True)
    writer.start()
    try:
        returncode = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        return False, "local ffmpeg decode timed out"
    finally:
        writer.join(timeout=1)
        for reader in readers:
            reader.join(timeout=1)
    if overflow.is_set():
        return False, "local ffmpeg output exceeded byte limit"
    if returncode != 0:
        return False, "fetched bytes failed local media decode"
    frame_rows = [line for line in captured["stdout"].decode("ascii", errors="ignore").splitlines()
                  if line and not line.startswith("#") and "," in line]
    if not frame_rows:
        return False, "local ffmpeg produced no decoded audio/video frames or packets"
    return True, "local ffmpeg decoded bounded media bytes and emitted frame/packet hashes"


def probe_channel(url: str, timeout: float = TIMEOUT_SECONDS, max_bytes: int = MAX_CHANNEL_BYTES,
                  deadline: float | None = None) -> tuple[str, str]:
    """Fetch bounded public samples and locally decode; this is not client playback."""
    opener = urllib.request.build_opener(check_catalog.PublicRedirectHandler())
    max_bytes = min(max_bytes, MAX_PROBE_BYTES)
    try:
        body, content_type, status, final_url = _fetch_probe(url, opener, max_bytes, timeout, deadline)
        if not 200 <= status < 300 or not body:
            return "failed", f"HTTP {status}; empty or unavailable response"
        if _looks_html(body, content_type):
            return "failed", "HTML/interstitial response"
        if _looks_playlist(body, content_type):
            variant, init_map, target, hls_error = _hls_targets(body, final_url)
            if hls_error:
                return "failed", f"HLS playlist unsupported: {hls_error}"
            if variant:
                child_body, child_type, child_status, child_final = _fetch_probe(variant, opener, max_bytes, timeout, deadline)
                if not 200 <= child_status < 300 or not child_body or _looks_html(child_body, child_type):
                    return "failed", f"HLS variant returned HTTP {child_status} or non-media content"
                if _looks_playlist(child_body, child_type):
                    variant2, init_map, target, hls_error = _hls_targets(child_body, child_final)
                    if hls_error or variant2 or not target:
                        return "failed", f"HLS media playlist unsupported: {hls_error or 'nested master or missing segment'}"
                    segment_body, segment_type, segment_status, _ = _fetch_probe(target, opener, max_bytes, timeout, deadline)
                    if not 200 <= segment_status < 300 or not segment_body:
                        return "failed", f"HLS segment returned HTTP {segment_status}"
                    media, content_type = segment_body, segment_type
                else:
                    input_format = _media_format(child_body, child_type)
                    if not input_format:
                        return "failed", "HLS variant returned neither a media playlist nor recognized media bytes"
                    media, content_type = child_body, child_type
            else:
                if not target:
                    return "failed", "HLS playlist has no segment"
                segment_body, segment_type, segment_status, _ = _fetch_probe(target, opener, max_bytes, timeout, deadline)
                if not 200 <= segment_status < 300 or not segment_body:
                    return "failed", f"HLS segment returned HTTP {segment_status}"
                media, content_type = segment_body, segment_type
            if init_map:
                map_body, map_type, map_status, _ = _fetch_probe(init_map, opener, max_bytes, timeout, deadline)
                if not 200 <= map_status < 300 or not map_body or _looks_html(map_body, map_type):
                    return "failed", f"HLS init map returned HTTP {map_status} or non-media content"
                media = map_body + media
                content_type = map_type
            input_format = _media_format(media, content_type)
            if not input_format:
                return "failed", "HLS init/segment response is not a recognized media container"
        else:
            input_format = _media_format(body, content_type)
            if not input_format:
                return "failed", "HTTP response is neither an HLS playlist nor a recognized media container"
            media = body
        decode_timeout = min(DECODE_TIMEOUT_SECONDS, _remaining(deadline, DECODE_TIMEOUT_SECONDS)) if deadline is not None else DECODE_TIMEOUT_SECONDS
        decoded, detail = _decode_media(media, input_format, timeout=decode_timeout)
        return ("sample-decoded", detail) if decoded else ("failed", detail)
    except Exception as exc:
        return "failed", _safe_exception(exc)


def probe_channels(channels: list[Channel], max_probes: int = 160, workers: int = 8,
                   budget_seconds: int = PROBE_RUN_BUDGET_SECONDS,
                   per_channel_budget_seconds: int = PROBE_BUDGET_SECONDS,
                   probe_timeout: int = TIMEOUT_SECONDS, max_probe_bytes: int = MAX_PROBE_BYTES) -> dict:
    if not 1 <= max_probes <= MAX_PROBES_PER_RUN:
        raise ValueError(f"max_probes must be 1..{MAX_PROBES_PER_RUN}")
    if not 1 <= workers <= MAX_CONCURRENT_PER_HOST * 8:
        raise ValueError("workers exceed configured safety limit")
    if not 1 <= budget_seconds <= PROBE_RUN_BUDGET_SECONDS:
        raise ValueError(f"budget_seconds must be 1..{PROBE_RUN_BUDGET_SECONDS}")
    if not 1 <= per_channel_budget_seconds <= PROBE_BUDGET_SECONDS:
        raise ValueError(f"per_channel_budget_seconds must be 1..{PROBE_BUDGET_SECONDS}")
    if not 1 <= probe_timeout <= TIMEOUT_SECONDS:
        raise ValueError(f"probe_timeout must be 1..{TIMEOUT_SECONDS}")
    if not 1 <= max_probe_bytes <= MAX_PROBE_BYTES:
        raise ValueError(f"max_probe_bytes must be 1..{MAX_PROBE_BYTES}")
    run_deadline = time.monotonic() + budget_seconds
    # Deduplicate endpoints first, so duplicate aliases cannot consume the daily probe quota.
    unique: dict[str, Channel] = {}
    for row in channels:
        unique.setdefault(_normalized_channel_url(row.url), row)
    queues = {group: deque() for group in GROUP_ORDER}
    for row in unique.values():
        queues.setdefault(row.group, deque()).append(row)

    # Select a rotating, stable daily sample. This spreads a 160-channel budget over large catalogs
    # rather than checking the same first 160 rows every day.
    day_index = dt.datetime.now(dt.timezone.utc).date().toordinal()
    for group, queue in queues.items():
        items = list(queue)
        if items:
            offset = (day_index * max(1, max_probes // max(1, len(queues)))) % len(items)
            queues[group] = deque(items[offset:] + items[:offset])

    selected: list[Channel] = []
    host_counts: dict[str, int] = defaultdict(int)
    group_counts: dict[str, int] = defaultdict(int)
    while len(selected) < max_probes:
        progressed = False
        for group in list(queues):
            queue = queues[group]
            while queue:
                row = queue.popleft()
                host = (urllib.parse.urlsplit(row.url).hostname or "").lower()
                if host_counts[host] >= MAX_CHANNEL_PROBES_PER_HOST:
                    continue
                selected.append(row)
                host_counts[host] += 1
                group_counts[row.group] += 1
                progressed = True
                break
            if len(selected) >= max_probes:
                break
        if not progressed:
            break
    selected_urls = {_normalized_channel_url(row.url) for row in selected}
    pending = [row for row in channels if _normalized_channel_url(row.url) not in selected_urls]
    results: dict[str, tuple[str, str]] = {}
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=workers)

    def run_probe(url: str) -> tuple[str, str]:
        # Start the per-channel deadline when a worker actually begins, not while queued.
        deadline = min(run_deadline, time.monotonic() + per_channel_budget_seconds)
        return probe_channel(url, timeout=probe_timeout, max_bytes=max_probe_bytes, deadline=deadline)

    futures = {pool.submit(run_probe, row.url): row for row in selected}
    try:
        remaining = max(0.0, run_deadline - time.monotonic())
        for future in concurrent.futures.as_completed(futures, timeout=remaining):
            row = futures[future]
            key = _normalized_channel_url(row.url)
            try:
                results[key] = future.result()
            except Exception as exc:
                results[key] = ("failed", _safe_exception(exc))
    except concurrent.futures.TimeoutError:
        pass
    finally:
        for future in futures:
            if not future.done():
                future.cancel()
        pool.shutdown(wait=False, cancel_futures=True)

    passed = failed = timed_out = 0
    for row in selected:
        result = results.get(_normalized_channel_url(row.url))
        if result is None:
            row.status, row.status_detail = "not-tested", "daily probe wall-clock budget exhausted"
            timed_out += 1
        else:
            row.status, row.status_detail = result
            passed += row.status == "sample-decoded"
            failed += row.status == "failed"
    selected_url_keys = {_normalized_channel_url(row.url) for row in selected}
    for row in channels:
        key = _normalized_channel_url(row.url)
        if key in results:
            row.status, row.status_detail = results[key]
        elif key not in selected_url_keys:
            row.status = "not-tested"
            row.status_detail = "daily probe selection limit or per-host cap reached"
    return {"selected_for_probe": len(selected), "sample_decoded": passed, "failed": failed,
            "not_tested": len(pending) + timed_out, "timed_out": timed_out,
            "probes_by_group": dict(group_counts), "daily_rotation_ordinal": day_index,
            "probe_budget_seconds": budget_seconds,
            "per_channel_probe_budget_seconds": per_channel_budget_seconds,
            "probe_method": "bounded public HTTP fetch; HLS playlist/variant/latest segment and optional init map; forced-demuxer FFmpeg decode from pipe-only bytes; not client playback"}


def m3u_text(channels: list[Channel], generated_at: str) -> str:
    lines = ["#EXTM3U"]
    for row in channels:
        def attr(value: str) -> str:
            return html.escape(value.replace("\r", " ").replace("\n", " ").replace('"', ""), quote=True)
        logo = f' tvg-logo="{attr(row.logo)}"' if row.logo and check_catalog.is_http_url(row.logo) else ""
        stable_id = f' tvg-id="{attr(row.tvg_id)}"' if row.tvg_id and re.fullmatch(r"[A-Za-z0-9._@-]{1,120}", row.tvg_id) else ""
        display = row.name.replace("\r", " ").replace("\n", " ").replace(",", " ")
        lines.append(f'#EXTINF:-1 group-title="{attr(row.group)}" tvg-name="{attr(display)}"{stable_id}{logo},{display}')
        lines.append(row.url)
    return "\n".join(lines) + "\n"


def txt_text(channels: list[Channel]) -> str:
    lines = []
    for group in GROUP_ORDER:
        items = [row for row in channels if row.group == group]
        if not items:
            continue
        lines.append(f"{group},#genre#")
        lines.extend(f"{row.name},{row.url}" for row in items)
    return "\n".join(lines) + "\n"


def row_document(row: Channel) -> dict:
    return {"name": row.name, "group": row.group, "url": safe_url(row.url),
            "tvg_id": row.tvg_id, "catalog_source_id": row.source_id,
            "catalog_source_name": row.source_name,
            "catalog_feed_reference": safe_url(row.source_feed_url),
            "source_reference": safe_url(row.source_url),
            "catalog_list_status": row.catalog_status, "channel_status": row.status,
            "channel_status_detail": row.status_detail, "alternatives": row.alternatives}


def build(config_path: Path = DEFAULT_CONFIG, catalog_dir: Path = DEFAULT_CATALOG,
          output_dir: Path = DEFAULT_OUTPUT, do_probe: bool = False,
          max_probes: int = 160, workers: int = 8) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(config, catalog_dir)
    policy = config["policy"]
    raw, source_status = collect_candidates(config, catalog_dir, workers=workers)
    channels, dedupe_stats = deduplicate(raw, config["source_ids"])
    configured_probe_limit = min(max_probes, policy["max_channel_probes_per_run"])
    probe_summary = probe_channels(
        channels, max_probes=configured_probe_limit, workers=workers,
        budget_seconds=policy["max_channel_probe_run_seconds"],
        per_channel_budget_seconds=policy["channel_probe_budget_seconds"],
        probe_timeout=policy["channel_probe_timeout_seconds"],
        max_probe_bytes=policy["max_channel_probe_bytes"],
    ) if do_probe else {
        "selected_for_probe": 0, "sample_decoded": 0, "failed": 0, "not_tested": len(channels),
        "probes_by_group": {}, "probe_method": "not requested; channel-level reachability/playback not tested"}
    # Probes are diagnostics only; one transient failure never removes a channel automatically.
    # All source-list candidates remain in generated files, and per-channel status stays in the report.
    playlist_rows = channels
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    (output_dir / "custom-live.m3u").write_text(m3u_text(playlist_rows, generated_at), encoding="utf-8")
    (output_dir / "custom-live.txt").write_text(txt_text(playlist_rows), encoding="utf-8")
    decoded_rows = [row for row in channels if row.status == "sample-decoded"]
    (output_dir / "custom-live-sample-decoded.m3u").write_text(m3u_text(decoded_rows, generated_at), encoding="utf-8")
    (output_dir / "custom-live-sample-decoded.txt").write_text(txt_text(decoded_rows), encoding="utf-8")
    report = {
        "schema_version": 1,
        "generated_at": generated_at,
        "selection_policy": config.get("policy", {}),
        "excluded_sources": [{"id": source_id, "rationale": rationale}
                             for source_id, rationale in sorted(config["excluded_source_ids"].items())],
        "limits": {"max_source_bytes": policy["max_source_bytes"],
                   "max_channel_probe_bytes": policy["max_channel_probe_bytes"],
                   "probe_timeout_seconds": policy["channel_probe_timeout_seconds"],
                   "probe_run_budget_seconds": policy["max_channel_probe_run_seconds"],
                   "workers": workers, "probe_limit": configured_probe_limit if do_probe else 0},
        "summary": {**dedupe_stats, **probe_summary, "playlist_channels_written": len(playlist_rows),
                    "sample_decoded_playlist_channels": len(decoded_rows),
                    "playlist_status": "candidate-set; see channel_status; sample-decoded list contains only bounded media samples decoded locally" if do_probe else "candidate-set; channel-level test not requested"},
        "output_files": {"candidate_m3u": "custom-live.m3u", "candidate_txt": "custom-live.txt",
                         "sample_decoded_m3u": "custom-live-sample-decoded.m3u",
                         "sample_decoded_txt": "custom-live-sample-decoded.txt"},
        "source_summary": source_status["summary"],
        "sources": source_status["sources"],
        "channels": [row_document(row) for row in channels],
    }
    report_path = output_dir / "reports" / "custom-live-status.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--probe-channels", action="store_true", help="sample bounded HTTP media and locally decode with ffmpeg; not client playback")
    parser.add_argument("--max-probes", type=int, default=160, help="maximum unique channel endpoints to sample-decode (default: 160; config may impose a lower cap)")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--validate-only", action="store_true", help="validate source selection without network requests or output")
    args = parser.parse_args()
    if not 1 <= args.max_probes <= MAX_PROBES_PER_RUN or not 1 <= args.workers <= MAX_CONCURRENT_PER_HOST * 8:
        parser.error(f"--max-probes must be 1..{MAX_PROBES_PER_RUN} and --workers must be 1..{MAX_CONCURRENT_PER_HOST * 8}")
    try:
        if args.validate_only:
            config = json.loads(args.config.read_text(encoding="utf-8"))
            summary = validate_config(config, args.catalog)
            print("Custom live source selection is valid: " + json.dumps(summary, ensure_ascii=False))
            return 0
        result = build(args.config, args.catalog, args.output_dir, args.probe_channels, args.max_probes, args.workers)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Custom live build failed: {exc}", file=sys.stderr)
        return 1
    summary = result["summary"]
    print("Built local custom live outputs: "
          f"{summary['playlist_channels_written']} candidate channels in M3U/TXT; "
          f"{summary['unique_channels']} unique channels from {summary['candidate_rows']} parsed rows; "
          f"sample-decoded/failed/not-tested={summary['sample_decoded']}/{summary['failed']}/{summary['not_tested']}.")
    print("sample-decoded means bounded media bytes were locally decoded; not client playback or sustained availability.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
