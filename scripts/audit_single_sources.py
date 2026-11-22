#!/usr/bin/env python3
"""Bounded, non-executing audit of single-source URLs in awesome-tvbox."""
from __future__ import annotations
import argparse
import concurrent.futures
import datetime as dt
import base64
import gzip
import hashlib
import ipaddress
import json
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

README_URL = "https://raw.githubusercontent.com/jiji262/awesome-tvbox/main/README.md"
UA = "tvapi-plus-safe-audit/1.0 (+https://github.com/hnnwb/tvapi_plus)"
MAX_CONFIG = 2 * 1024 * 1024
MAX_API = 256 * 1024
TIMEOUT = 8
TEST_WORD = "4K"
SEARCH_WORDS = ("4K", "2160p", "UHD")
MAX_CMS_PER_CONFIG = 3
MAX_RESULTS_PER_SEARCH = 1
MAX_MEDIA_PER_CONFIG = 1
MEDIA_TIMEOUT = 12

class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urljoin(req.full_url, newurl)
        check_public_http(target)
        count = getattr(req, "redirect_count", 0)
        if count >= 4:
            raise urllib.error.HTTPError(req.full_url, code, "redirect limit exceeded", headers, fp)
        redirected = super().redirect_request(req, fp, code, msg, headers, target)
        if redirected is not None:
            redirected.redirect_count = count + 1
        return redirected

OPENER = urllib.request.build_opener(PublicRedirect)

def check_public_http(url: str) -> None:
    p = urllib.parse.urlparse(url)
    if p.scheme not in {"http", "https"} or not p.hostname or p.username or p.password:
        raise ValueError("URL must be credential-free http(s)")
    try:
        addresses = {x[4][0].split("%")[0] for x in socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise ValueError(f"DNS: {exc}") from exc
    if not addresses or any(not ipaddress.ip_address(x).is_global for x in addresses):
        raise ValueError("host did not resolve exclusively to public IP addresses")

def get(url: str, cap: int) -> dict:
    check_public_http(url)
    p = urllib.parse.urlparse(url)
    safe_path = urllib.parse.quote(p.path, safe="/%:@!$&'()*+,;=-._~%")
    safe_query = urllib.parse.quote(p.query, safe="=&%:@/?+!$'()*,-._~")
    safe_url = urllib.parse.urlunparse((p.scheme, p.netloc.encode("idna").decode("ascii"), safe_path, p.params, safe_query, p.fragment))
    request = urllib.request.Request(safe_url, headers={"User-Agent": UA, "Accept": "application/json,text/plain,*/*", "Accept-Encoding": "identity"})
    started = time.monotonic()
    try:
        response = OPENER.open(request, timeout=TIMEOUT)
    except urllib.error.HTTPError as exc:
        raise
    with response:
        body = response.read(cap + 1)
        if len(body) > cap:
            raise ValueError(f"response exceeds {cap} byte safety cap")
        return {"status": response.status, "url": response.geturl(), "content_type": response.headers.get_content_type(),
                "bytes": len(body), "ms": round((time.monotonic() - started) * 1000), "body": body}

def candidates(markdown: str) -> list[dict]:
    found: dict[str, dict] = {}
    section = ""
    for line in markdown.splitlines():
        if line.startswith("### "):
            section = line[4:].strip()
            continue
        if section not in {"优选接口", "备用接口"}:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in {"名称", "---"}:
            continue
        match = re.search(r"`(https?://[^`]+)`", cells[2])
        if not match:
            continue
        url = match.group(1).strip()
        key = url
        if key not in found:
            found[key] = {"name": cells[0], "url": url, "listed_in": [section]}
        else:
            found[key]["listed_in"].append(section)
    return list(found.values())

def strip_jsonc(text: str) -> str:
    out = []
    i = 0
    in_string = False
    escaped = False
    while i < len(text):
        ch = text[i]
        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
        elif ch == "/" and i + 1 < len(text) and text[i + 1] == "/":
            i = text.find("\n", i)
            if i < 0:
                break
        elif ch == "/" and i + 1 < len(text) and text[i + 1] == "*":
            end = text.find("*/", i + 2)
            if end < 0:
                raise ValueError("unterminated JSONC block comment")
            i = end + 2
        else:
            out.append(ch)
            i += 1
    text = "".join(out)
    out = []
    in_string = escaped = False
    for i, ch in enumerate(text):
        if in_string:
            out.append(ch)
            if escaped: escaped = False
            elif ch == "\\": escaped = True
            elif ch == '"': in_string = False
        elif ch == '"':
            in_string = True
            out.append(ch)
        elif ch == ",":
            j = i + 1
            while j < len(text) and text[j].isspace(): j += 1
            if j < len(text) and text[j] in "}]": continue
            out.append(ch)
        else:
            out.append(ch)
    return "".join(out)

def json_doc(body: bytes):
    if body.startswith(bytes((0x1f, 0x8b))):
        body = gzip.decompress(body)
    text = body.decode("utf-8-sig").strip()
    if not text.startswith(("{", "[")):
        try:
            decoded = base64.b64decode(text, validate=True)
            text = decoded.decode("utf-8-sig").strip()
        except Exception:
            pass
    if not text.startswith(("{", "[")):
        raise ValueError("body is not plain/base64/gzip JSON")
    return json.loads(strip_jsonc(text))

def api_probe(base: str, params: dict) -> dict:
    p = urllib.parse.urlsplit(base)
    query = urllib.parse.parse_qsl(p.query, keep_blank_values=True) + list(params.items())
    url = urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, urllib.parse.urlencode(query), ""))
    try:
        response = get(url, MAX_API)
        doc = json_doc(response["body"])
        if not isinstance(doc, dict):
            return {"ok": False, "http": response["status"], "ms": response["ms"], "error": "expected CMS JSON object"}
        data = doc.get("list", doc.get("data"))
        rows = data if isinstance(data, list) else (data.get("list", []) if isinstance(data, dict) and isinstance(data.get("list"), list) else None)
        valid_shape = rows is not None and (not rows or all(isinstance(x, dict) for x in rows))
        result = {"ok": response["status"] == 200 and valid_shape, "http": response["status"], "ms": response["ms"],
                  "nonempty": bool(rows), "rows": len(rows) if isinstance(rows, list) else None,
                  "schema": "list/data array" if valid_shape else "unexpected CMS response shape",
                  "code": doc.get("code"), "total": doc.get("total"), "items": rows if isinstance(rows, list) else []}
        return result
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:200]}"}

def playable_urls(item: dict) -> list[str]:
    urls = []
    for key, value in item.items():
        if key in {"vod_play_url", "url", "play_url"} and isinstance(value, str):
            urls.extend(re.findall(r"https?://[^$#|,\s]+", value))
        elif key in {"vod_play_url", "url", "play_url"} and isinstance(value, list):
            urls.extend(x for x in value if isinstance(x, str) and x.startswith(("http://", "https://")))
    return list(dict.fromkeys(urls))

def probe_media(url: str) -> dict:
    # Disabled: ffprobe may recursively fetch HLS/DASH child URLs without per-hop SSRF validation.
    return {"status": "not-probed", "reason": "No isolated network sandbox for recursive playlist requests"}

def title_is_explicit_4k(title: str | None) -> bool:
    if not title:
        return False
    return bool(re.search(r"(?i)(?<![a-z0-9])(?:4k|2160p|uhd)(?![a-z0-9])", title) and
                not re.search(r"(?i)4k\s*(?:修复|修复版|修复高清|remaster(?:ed)?)", title))

def api_probe_4k(base: str, word: str) -> dict:
    result = api_probe(base, {"ac": "list", "wd": word, "pg": 1})
    items = result.pop("items", [])
    result["keyword"] = word
    result["results"] = [{"id": x.get("vod_id"), "name": x.get("vod_name"), "remarks": x.get("vod_remarks"),
                          "title_explicitly_mentions_4k": title_is_explicit_4k(x.get("vod_name")),
                          "play_urls": playable_urls(x)[:5]} for x in items[:MAX_RESULTS_PER_SEARCH] if isinstance(x, dict)]
    return result

def site_api_key(site: dict, base_url: str) -> str | None:
    raw = site.get("api")
    if not isinstance(raw, str) or not raw.strip() or raw.startswith(("./", "/", "csp_")):
        return None
    try:
        url = urllib.parse.urljoin(base_url, raw.strip())
        p = urllib.parse.urlparse(url)
        if p.scheme not in {"http", "https"} or not p.hostname:
            return None
        # Strip query/fragment to prevent source-specific secrets from being copied into reports.
        return urllib.parse.urlunparse((p.scheme, p.netloc, p.path.rstrip("/"), "", "", ""))
    except ValueError:
        return None

def audit(item: dict) -> dict:
    out = {**item, "config": {}, "cms": []}
    try:
        response = get(item["url"], MAX_CONFIG)
        cfg = json_doc(response["body"])
        if not isinstance(cfg, dict) or not isinstance(cfg.get("sites"), list) or not cfg["sites"]:
            raise ValueError("JSON parsed but has no non-empty sites array")
        sites = cfg["sites"]
        counts = Counter(str(s.get("type", "missing")) for s in sites if isinstance(s, dict))
        out["config"] = {k: response[k] for k in ("status", "url", "content_type", "bytes", "ms")}
        out["config"].update({"result": "tvbox-json-structural", "sites": len(sites), "types": dict(counts),
                              "spider_present": bool(cfg.get("spider")),
                              "executable_refs_present": bool(cfg.get("spider")) or any(isinstance(s, dict) and
                                  (str(s.get("api", "")).endswith((".js", ".py", ".jar")) or "csp_" in str(s.get("api", ""))) for s in sites)})
        seen = set()
        media_seen = set()
        out["four_k"] = {"tested_words": list(SEARCH_WORDS), "media": []}
        for site in sites:
            if not isinstance(site, dict) or str(site.get("type")) != "1":
                continue
            api = site_api_key(site, response["url"])
            if not api or api in seen or len(out["cms"]) >= MAX_CMS_PER_CONFIG:
                continue
            seen.add(api)
            cms = {"key": str(site.get("key", ""))[:80], "name": str(site.get("name", ""))[:100], "api": api, "four_k_searches": []}
            for word in SEARCH_WORDS:
                search = api_probe_4k(api, word)
                cms["four_k_searches"].append(search)
                for item in search["results"]:
                    item_id = item.get("id")
                    if item_id is None:
                        continue
                    detail = api_probe(api, {"ac": "detail", "ids": str(item_id)})
                    detail_rows = detail.pop("items", [])
                    item["detail"] = {"ok": detail.get("ok", False), "http": detail.get("http"), "error": detail.get("error")}
                    item["detail"]["returned_play_urls"] = []
                    for row in detail_rows:
                        if not isinstance(row, dict):
                            continue
                        item["detail"]["returned_play_urls"] = playable_urls(row)[:5]
                        item["play_urls"] = item["detail"]["returned_play_urls"]
                        for media_url in item["play_urls"]:
                            if media_url in media_seen or len(media_seen) >= MAX_MEDIA_PER_CONFIG:
                                continue
                            media_seen.add(media_url)
                            item["detail"].setdefault("streams", []).append({"url": media_url, "probe": probe_media(media_url)})
                            out["four_k"]["media"].append({"site": cms["name"], "title": item.get("name"), "keyword": search["keyword"], "url": media_url, "probe": item["detail"]["streams"][-1]["probe"]})
            out["cms"].append(cms)
        out["classification"] = "config parsed; up to three type-1 CMS APIs searched for 4K titles; play URL extraction only; no adapters/media executed"
    except Exception as exc:
        out["config"] = {"result": "failed", "error": f"{type(exc).__name__}: {str(exc)[:240]}"}
        out["classification"] = "config not structurally parsed; CMS and playback not tested"
    return out

def render_markdown(report: dict) -> str:
    rows = ["# TVBox single-source safe audit", "", f"Generated: {report['generated_at']}",
            f"Source snapshot SHA-256: `{report['source_sha256']}`", f"Candidates: {report['candidate_count']} unique URLs from {report['table_rows']} rows", "",
            "Only credential-free HTTP(S) requests to public IPs are made; max four redirects, checked at each hop. Config cap 2 MiB, CMS cap 256 KiB, 8 s HTTP timeout, four configs concurrently, three unique CMS APIs/config. No Spider/JAR/JS/Python execution.", "",
            "CMS searches use 4K, 2160p, UHD as broad filters, one result per term. Search hits are not necessarily 4K titles: for example, `我的24k氪金神眼` was returned for the 4K query but is not an explicit 4K label. Detail play URLs are extracted only; no media is fetched or decoded because the host denied sandbox-exec and unrestricted ffprobe may follow nested playlist URLs.", "",
            "| Candidate | Config | CMS APIs | Search hits | Explicit 4K titles | Titles with play URLs | Detail lookups passed |", "|---|---:|---:|---:|---:|---:|---:|"]
    for r in report["results"]:
        c = r["config"]
        searches = [p for site in r["cms"] for p in site.get("four_k_searches", [])]
        label_hits = sum(len(p.get("results", [])) for p in searches)
        hits = [item for api in r["cms"] for search in api.get("four_k_searches", []) for item in search.get("results", [])]
        explicit = [item for item in hits if item.get("title_explicitly_mentions_4k")]
        direct = [item for item in hits if item.get("detail", {}).get("returned_play_urls")]
        detail_ok = sum(bool(item.get("detail", {}).get("ok")) for item in hits)
        rows.append(f"| {r['name']} | {c.get('result','failed')} | {len(r['cms'])} | {label_hits} | {len(explicit)} | {len(direct)} | {detail_ok} |")
    rows += ["", "## 4K evidence", "", "Title labels and CMS responses are not media measurements. No media is fetched or decoded, so no result confirms resolution, bitrate, Mac playback, sustained quality, or rights. Spider/JAR/JS/Python rules remain untested.", "", f"Totals: {report.get('parsed_config_count', 0)} parsed configs; {report.get('cms_api_count', 0)} CMS APIs sampled; {report.get('four_k_title_hits', 0)} broad search results; {report.get('explicit_4k_title_hits', 0)} explicit 4K/UHD/2160p titles; {report.get('direct_play_url_hits', 0)} titles with play URLs; {report.get('explicit_4k_with_direct_url', 0)} explicit-label titles with URLs; {report.get('detail_successes', 0)} detail responses passed; {report.get('verified_4k_streams', 0)} streams verified as 4K."]
    return "\n".join(rows) + "\n"

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readme", default=README_URL)
    parser.add_argument("--readme-file")
    parser.add_argument("--json", default="reports/single-source-audit.json")
    parser.add_argument("--markdown", default="reports/single-source-audit.md")
    args = parser.parse_args()
    if args.readme_file:
        source = Path(args.readme_file).read_text(encoding="utf-8-sig")
    else:
        source = get(args.readme, 2 * 1024 * 1024)["body"].decode("utf-8-sig")
    items = candidates(source)
    if not items:
        parser.error("no candidate URLs found; refusing to write an empty report")
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(audit, item): item for item in items}
        results = []
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            print(f"Progress: {len(results)}/{len(items)} ({futures[future]['name']})", flush=True)
    # Evidence grouping only; no composite quality score.
    results.sort(key=lambda x: (x["config"].get("result") != "tvbox-json-structural",
        -sum(bool(i.get("title_explicitly_mentions_4k") and i.get("play_urls")) for c in x["cms"] for s in c.get("four_k_searches", []) for i in s.get("results", [])),
        -sum(bool(i.get("play_urls")) for c in x["cms"] for s in c.get("four_k_searches", []) for i in s.get("results", [])),
        -sum(bool(i.get("detail", {}).get("ok")) for c in x["cms"] for s in c.get("four_k_searches", []) for i in s.get("results", []))))
    report = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "source_readme": args.readme,
              "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(), "table_rows": sum(len(x["listed_in"]) for x in items),
              "method": "Bounded non-executing config/CMS audit; 4K title searches and detail URL extraction only. No media requests, decoder, Spider/JAR/JS/Python execution or client playback claim.",
              "media_probe": "disabled: sandbox-exec was denied by the host (sandbox_apply: Operation not permitted); recursive HLS/DASH requests cannot be safely constrained",
              "search_words": list(SEARCH_WORDS),
              "parsed_config_count": sum(x["config"].get("result") == "tvbox-json-structural" for x in results),
              "cms_api_count": sum(len(x["cms"]) for x in results),
              "four_k_title_hits": sum(len(s.get("results", [])) for x in results for c in x["cms"] for s in c.get("four_k_searches", [])),
              "explicit_4k_title_hits": sum(bool(i.get("title_explicitly_mentions_4k")) for x in results for c in x["cms"] for s in c.get("four_k_searches", []) for i in s.get("results", [])),
              "direct_play_url_hits": sum(bool(i.get("detail", {}).get("returned_play_urls")) for x in results for c in x["cms"] for s in c.get("four_k_searches", []) for i in s.get("results", [])),
              "explicit_4k_with_direct_url": sum(bool(i.get("title_explicitly_mentions_4k") and i.get("detail", {}).get("returned_play_urls")) for x in results for c in x["cms"] for s in c.get("four_k_searches", []) for i in s.get("results", [])),
              "detail_successes": sum(bool(i.get("detail", {}).get("ok")) for x in results for c in x["cms"] for s in c.get("four_k_searches", []) for i in s.get("results", [])),
              "media_streams_probed": 0,
              "verified_4k_streams": 0,
              "candidate_count": len(items), "status_counts": dict(Counter(x["config"].get("result", "failed") for x in results)),
        "results": results}
    for path, payload in ((args.json, json.dumps(report, ensure_ascii=False, indent=2) + "\n"), (args.markdown, render_markdown(report))):
        target = Path(path); target.parent.mkdir(parents=True, exist_ok=True); target.write_text(payload, encoding="utf-8")
    print(f"Audited {len(results)} candidates from {report['table_rows']} table rows; states={report['status_counts']}; JSON={args.json}; Markdown={args.markdown}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
