# TVBox Resource Catalog

[简体中文](README.md) | **English**

A resource directory and format checker for the TVBox ecosystem, including Yingxia and 影视仓 (Yingshicang), as well as other compatible clients. This repository records resource links and provenance; it does not mirror third-party configuration payloads or run source plugins.

## Scope

- Maintain one canonical catalog organized by resource type, not separate Git branches per client.
- Track client compatibility claims, URL reachability, and actual playback tests separately.
- Validate catalog metadata automatically, with optional bounded HTTP and basic format checks.
- No automatic decryption, rewriting, proxying, or republication of third-party configurations; no JS, Python, or JAR plugin execution in CI.

The catalogs currently contain a small set of live playlists, VOD configuration indexes, EPG feeds, and tooling references with recorded provenance and bounded accessibility/structure checks; this is not a complete review. Do not copy every link from Awesome TVBox or another directory. Add only links you are authorized to publish. Public reachability is not proof of copyright permission, safety, compatibility, or playback quality. Malformed, unclear-provenance, or rights-unclear configurations (such as the currently invalid XYQ JSON) are not listed as usable interfaces. Never commit credentials, private URLs, tokens, or account data.

## Repository layout

```text
catalog/
  clients.json       # Client capability reference
  vod-single.json    # Single-repository configuration links
  vod-multi.json     # Multi-repository (urls) configuration links
  live.json          # M3U/TXT/JSON live playlists
  epg.json           # EPG and logo resources
  tools.json         # Developer documentation and utilities
schemas/
  catalog.schema.json       # Reference catalog entry structure
  probe-report.schema.json   # Availability report structure
scripts/
  check_catalog.py           # Metadata checks and optional URL probes
  refresh_status.py          # Scheduled retry/fallback status refresh
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
  "clients": {
    "yingxia": { "status": "format-claimed", "tested_version": null, "tested_at": null },
    "yingshicang": { "status": "format-claimed", "tested_version": null, "tested_at": null }
  }
}
```

Client states: `unknown`, `format-claimed`, `import-tested`, `playback-tested`, and `incompatible`. Use `import-tested` or `playback-tested` only after an actual test, and record the client version and a `YYYY-MM-DD` date. `format-claimed` only records a format/upstream compatibility claim; it does not mean the source has been verified in Yingxia or 影视仓. Behavior may vary by app version, runtime, and source type.

Allowed formats by catalog file:

| File | `format` values |
| --- | --- |
| `vod-single.json` | `tvbox-json` |
| `vod-multi.json` | `tvbox-multi` |
| `live.json` | `m3u`, `txt`, `tvbox-live-json` |
| `epg.json` | `epg-xml`, `logo-library` |
| `tools.json` | `documentation`, `utility` |

See [`catalog/clients.json`](catalog/clients.json) for client references and [`schemas/catalog.schema.json`](schemas/catalog.schema.json) for the entry structure. The current checker implements its own field checks; it does not load or validate against the JSON Schema file yet.

## Local checks

Requires Python 3.10+ and no third-party Python packages:

```sh
python3 scripts/check_catalog.py
python3 scripts/check_catalog.py --check-urls --report probe-report.json
python3 scripts/refresh_status.py --report /tmp/probe-report.json --retries 0 --delay 0
```

The default command performs offline metadata validation. `--check-urls` contacts only public third-party hosts using GET requests with timeouts and a response-size limit. Redirects are restricted to public HTTP(S) targets, and response content is never executed. Basic structural checks cover TVBox JSON, multi-repository `urls`, M3U/TXT, live JSON, and EPG XML. Probe failures are written to the report; they do not delete or rewrite catalog entries. Results can differ by network, location, User-Agent, or upstream policy.

## GitHub Actions

- Pushes and pull requests affecting catalog, schema, checker, or workflow files run offline metadata checks.
- Twice-daily scheduled runs and manually requested URL checks perform bounded probes with short retries. Optional `fallback_urls` must be reviewed and explicitly added; the job never discovers or writes them automatically.
- The job atomically updates and commits only `probe-report.json`, preserving the previous successful timestamp and marking current failures as failed/stale. The checked-in empty report is a first-run baseline, not a passing probe. It does not delete catalog entries or overwrite resource configurations. The scheduled job deploys Pages in the same run so its status commit is published despite GitHub's `GITHUB_TOKEN` workflow-trigger restrictions.
- It does not download/mirror third-party configurations or execute Spider/JS/Python/JAR code. Availability probes are not client playback tests. Detailed failures are also uploaded as a 14-day artifact.

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

The catalog JSON files are the canonical data and also drive the bilingual static catalog site. The site searches names, formats, and sources, and filters by category and client test status. It displays probe and hands-on test states but never runs source plugins. A GitHub Pages workflow deploys on pushes to `main`; before the first deployment, a repository administrator must set Settings → Pages → Source to GitHub Actions. Catalog URLs point to upstream resources; they are not mirrored by this repository.

“Broad coverage” is an ongoing collection and review process, not indiscriminate copying. Entries need traceable provenance, a basis for linking, and a stated format; playback-tested status requires a client version and date. Scheduled probes are bounded observations of reachability, not guarantees of channel quality or continued availability. Do not label unauthorized, dead, duplicate, or unverified links as quality sources just to inflate the list.

## Legal and safety

This is a technical directory, not an endorsement. Resource providers control their content and terms. List only links and metadata you are authorized to publish, and honor takedown requests. Automation is limited to metadata, syntax, and reachability checks. Treat external configurations and plugin code as untrusted and never execute them in CI. Users must comply with applicable laws and upstream service terms.
