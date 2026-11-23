# TVBox Resource Catalog

[简体中文](README.md) | **English**

A resource directory and format checker for the TVBox ecosystem and compatible clients. This repository records resource links and provenance; it does not mirror third-party configuration payloads or run source plugins.

## Scope

- Maintain one canonical catalog organized by resource type.
- Track automated URL reachability; client import and playback require running the actual client.
- Validate catalog metadata automatically, with optional bounded HTTP and basic format checks.
- No automatic decryption, rewriting, proxying, or republication of third-party configurations; no JS, Python, or JAR plugin execution in CI.

The catalogs currently contain a small set of live playlists, VOD configuration indexes, EPG feeds, and tooling references with recorded provenance and bounded accessibility/structure checks; this is not a complete review. Do not copy every link from Awesome TVBox or another directory. Add only links you are authorized to publish. Public reachability is not proof of copyright permission, safety, compatibility, or playback quality. Malformed, unclear-provenance, or rights-unclear configurations (such as the currently invalid XYQ JSON) are not listed as usable interfaces. Never commit credentials, private URLs, tokens, or account data.

## Repository layout

```text
catalog/
  vod-single.json    # Single-repository configuration links
  vod-multi.json     # Multi-repository (urls) configuration links
  live.json          # M3U/TXT/JSON live playlists
  epg.json           # EPG and logo resources
  tools.json         # Open-source repositories (link and upstream rating only)
  online.json        # Streaming sites and download landing pages (browser use)
  search.json        # Cloud-drive search and subtitle sites
  magnet.json        # Magnet and BT search sites
  apps.json          # Apps: repositories, product and download pages, each naming its systems
schemas/
  catalog.schema.json       # Reference catalog entry structure
  probe-report.schema.json   # Availability report structure
scripts/
  check_catalog.py           # Metadata checks and optional URL probes
  refresh_status.py          # Scheduled retry/fallback status refresh
  import_upstream.py         # Merge upstream catalog entries by URL (optional)
  import_apps.py             # Merge upstream client lists by URL (optional)
.github/workflows/
  catalog-check.yml
```

## Add an entry

Each catalog file is a JSON array. Use the allowed `format` for its category. Entry IDs must be unique across all catalogs.

```json
{
  "id": "reviewed-multi-source",
  "name": "Reviewed multi-source catalog",
  "url": "https://example.org/catalog.json",
  "format": "tvbox-multi",
  "source": "https://github.com/owner/project",
  "license": "See upstream terms",
  "notes": "Reviewed for public linking on 2026-11-20",
  "rating": {
    "average": 4.4,
    "scores": { "more": 5, "speed": 4, "clean": 4, "stable": 4, "ease": 5 },
    "status": "recommended",
    "checked_at": "2026-06-06"
  }
}
```

`rating` is optional and may only republish an upstream self-assessment: `scores` must carry the five 1–5 values `more`, `speed`, `clean`, `stable` and `ease`, `average` must equal their mean, and `checked_at` is a `YYYY-MM-DD` date. The checker rejects a wrong mean, an out-of-range value or a missing field. It is the upstream maintainer's judgement: this project measured none of it and does not treat it as a recommendation.

Allowed formats by catalog file:

| File | `format` values |
| --- | --- |
| `vod-single.json` | `tvbox-json` |
| `vod-multi.json` | `tvbox-multi` |
| `live.json` | `m3u`, `txt`, `tvbox-live-json` |
| `epg.json` | `epg-xml`, `logo-library` |
| `tools.json` | `documentation`, `utility`, `project` |
| `online.json` | `web` |
| `search.json` | `web` |
| `magnet.json` | `web` |
| `apps.json` | `web`, `link-page`, `project` — all three are entry points to that app |

See [`schemas/catalog.schema.json`](schemas/catalog.schema.json) for the entry structure. The catalog displays automated link-probe results; client import or playback requires running the client and is not shown as a placeholder status. The current checker implements its own field checks; it does not load or validate against the JSON Schema file yet.

## Local checks

Requires Python 3.10+ and no third-party Python packages:

```sh
python3 scripts/check_catalog.py
python3 scripts/check_catalog.py --check-urls --report probe-report.json
python3 scripts/refresh_status.py --report /tmp/probe-report.json --retries 0 --delay 0
# Optional: TVBox-like config-fetch headers (not app/runtime playback)
python3 scripts/refresh_status.py --request-profile tvbox --report /tmp/probe-report.json --retries 0 --delay 0
```

The default command performs offline metadata validation. `--check-urls` contacts only public third-party hosts using GET requests with timeouts and a response-size limit. Redirects are restricted to public HTTP(S) targets, and response content is never executed. Basic structural checks cover TVBox JSON, multi-repository `urls`, M3U/TXT, live JSON, and EPG XML. Probe failures are written to the report; they do not delete or rewrite catalog entries. Results can differ by network, location, User-Agent, or upstream policy. The refresh script uses a project-identifying UA by default; optional `--request-profile tvbox` simulates only TVBox-style configuration-fetch headers (`okhttp/3.15` and `X-Requested-With: com.github.tvbox.osc`) to compare server compatibility. It does not run a client, Spider, or player and is not an import/playback test.

## GitHub Actions

- Pushes and pull requests affecting catalog, schema, checker, or workflow files run offline metadata checks.
- Twice-daily scheduled runs and manually requested URL checks perform bounded probes with short retries. Optional `fallback_urls` must be reviewed and explicitly added; the job never discovers or writes them automatically. A pass means only that the link/format probe succeeded at that time, not that a client can import or play it.
- The job atomically updates and commits only `probe-report.json`, preserving the previous successful timestamp and marking current failures as failed/stale. The checked-in empty report is a first-run baseline, not a passing probe. It does not delete catalog entries or overwrite resource configurations. The scheduled job deploys Pages in the same run so its status commit is published despite GitHub's `GITHUB_TOKEN` workflow-trigger restrictions.
- It does not download/mirror third-party configurations or execute Spider/JS/Python/JAR code. Link reachability probes are not client playback tests. Detailed failures are also uploaded as a 14-day artifact.

See [`.github/workflows/catalog-check.yml`](.github/workflows/catalog-check.yml). The scheduled runs are set to `05:23` and `17:23 UTC` and may be delayed by GitHub Actions scheduling.

## Playback verification

The current checker covers metadata, bounded HTTP access and basic configuration structure only. It does not run Spider/JS/Python/JAR code, resolve playback URLs or decode media. HTTP 200 is not a playback pass.

1. Record the client/version, OS, network, timestamp, config URL and selected site/type. Confirm the complete config is readable; wrapped or encrypted responses require a trusted client's supported parser, not an arbitrary online decoder.
2. In the actual client, verify search and details using content you are authorized to access. CMS list JSON alone does not verify client search, details or playback.
3. Select an episode/line and determine from redacted client logs whether playback URL resolution completed. Never publish tokens, credentials or signed media URLs.
4. Verify picture and sound for at least 30 seconds. Record buffering and errors. Only actual successful client playback supports playback-tested, scoped to that client/version and sample. This duration is this project's proposed smoke-test threshold, not an upstream standard.
5. Repeat with another site/content item and on another date; keep failures. One passing sample does not establish whole-config quality.

For an endless spinner, first identify whether loading stalls at search, details, URL resolution or player startup. Search failures suggest checking the site API/network; details failures suggest checking the detail API or Spider compatibility; startup failures require checking the resolved URL, redirects/headers/TLS and decoder errors. These are diagnostic hypotheses, not established causes. Compare with a known authorized test asset in the same player.

Do not execute unknown plugins in this repository or CI. Without the selected site and redacted client logs, configuration JSON cannot establish the cause of a spinner. This is a manual protocol, not an implemented end-to-end test runner.

## Publishing

The catalog JSON files are the canonical data and also drive the bilingual static catalog site. The catalog merges the upstream awesome-zhuiju-free directory: one row per URL, imported rows inherit the upstream rating, and `scripts/import_upstream.py` dedupes by URL before writing, so a re-run never appends twice. The page is a single catalog panel whose categories are tabs — single and multi configs, live, EPG, magnet and BT, cloud search and subtitles, streaming sites, apps, and open-source projects — each with its own count. Rows sort by passing check first, then higher upstream rating, then name. Stars are drawn as half-star glyphs with the numeric value alongside, and shrink to small glyphs on narrow screens. The site searches names, formats, and sources, and filters by category. It displays automated link-probe results but never runs source plugins. A GitHub Pages workflow deploys on pushes to `main`; before the first deployment, a repository administrator must set Settings → Pages → Source to GitHub Actions. Catalog URLs point to upstream resources; they are not mirrored by this repository.

“Broad coverage” is an ongoing collection and review process, not indiscriminate copying. Entries need traceable provenance, a basis for linking, and a stated format; actual playback claims require client test evidence.

## Verification Record

The published page's “Reproducible verification” panel reads [`reports/verification-report.json`](reports/verification-report.json). It distinguishes fetch/fallback integration, media decoding, and client playback. A fallback exercised with a temporary local server is not evidence of client compatibility. `passed` applies only to the named step; `failed` applies to that sample step; `not-tested` means it was not run. The current report explicitly marks TVBox client playback and true 4K as unverified. When refreshing it, retain the tested snapshot, method, and limitations, and update the bilingual page data consistently.

## Self-hosted subscriptions

This project generates its own multi-repository subscription and a separate custom single-source candidate config. It prefers type-1 CMS APIs passing current bounded list/search/detail checks; if none pass, it falls back to unique type-1 API candidates recorded in structurally parsed historical configs. Fallback entries are explicitly unverified: they are not confirmed reachable, searchable, or playable. It does not download or mirror entire third-party configs or execute Spider, JS, JAR, or Python.

`scripts/build_subscriptions.py` validates the catalog through the offline validator and writes `configs.json`, `subscriptions/tvbox-multi.json`, and `subscriptions/tvbox-custom-single.json` under one output root. The custom config prefers current CMS-tested APIs; if none qualify, it deduplicates type-1 candidates from `reports/single-source-audit.json`. Historical fallback candidates are not confirmed reachable, searchable, or playable. The config contains no remote Spider/plugin code, and no media request, decode, or client playback is performed. The homepage labels the custom candidate unverified. The screening report covers only a prior audit subset; an empty strict screen does not mean all upstream APIs are down. The index keeps the first catalog record for each unique upstream URL and adds the separate custom candidate when it has sites. The multi-source manifest includes only VOD entries with qualifying playback evidence in `catalog/playback-evidence.json`: client, version, date, scope, and at least 30 seconds of successful playback. Link probes are not playback evidence. The evidence file is currently empty, so that manifest is empty. Outputs exclude live playlists, EPG, documentation, and unreviewed fallback URLs. Published URLs: `https://hnnwb.github.io/tvapi_plus/configs.json`, `https://hnnwb.github.io/tvapi_plus/subscriptions/tvbox-multi.json`, and, when non-empty, `https://hnnwb.github.io/tvapi_plus/subscriptions/tvbox-custom-single.json`. Build tests verify file structure only, not import or playback. Do not label unauthorized, dead, duplicate, or unverified links as quality sources.

## Legal and safety

This is a technical directory, not an endorsement. Resource providers control their content and terms. List only links and metadata you are authorized to publish, and honor takedown requests. Automation is limited to metadata, syntax, and reachability checks. Treat external configurations and plugin code as untrusted and never execute them in CI. Users must comply with applicable laws and upstream service terms.
