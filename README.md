# TVBox Resource Catalog

A source-attributed directory and format checker for TVBox-family clients, including Yingxia and 影视仓. This repository catalogs links and metadata; it does not mirror third-party source payloads or run source plugins.

## Scope

- One canonical catalog, organized by resource kind rather than client branches.
- Client compatibility is recorded separately from URL availability and actual playback testing.
- Automated checks validate catalog metadata and syntax, then optionally perform bounded HTTP reachability checks.
- No automatic decryption, rewriting, proxying, execution of JS/Python/JAR plugins, or republishing of third-party payloads.

Only add links you have permission to publish. Public reachability is not proof of copyright authorization, safety, compatibility, or playback quality. Do not commit credentials, private URLs, tokens, or account data.

## Repository layout

```text
catalog/
  clients.json       # Client capability registry
  vod-single.json    # Single TVBox configuration links
  vod-multi.json     # Multi-repository (urls) links
  live.json          # M3U/TXT/JSON live playlist links
  epg.json           # EPG and logo resources
  tools.json         # Documentation and utilities
schemas/
  catalog.schema.json
scripts/
  check_catalog.py   # Offline structure checks and optional URL checks
.github/workflows/
  catalog-check.yml
```

Catalog entries start empty by design. Add reviewed entries using the format below; do not copy the Awesome TVBox list wholesale.

## Add an entry

```json
{
  "id": "my-reviewed-multi-source",
  "name": "Reviewed multi-source catalog",
  "url": "https://example.org/catalog.json",
  "format": "tvbox-multi",
  "source": "https://github.com/owner/project",
  "license": "See upstream terms",
  "notes": "Reviewed for publication on 2026-11-20",
  "clients": {
    "yingxia": { "status": "format-claimed", "tested_version": null, "tested_at": null },
    "yingshicang": { "status": "format-claimed", "tested_version": null, "tested_at": null }
  }
}
```

Allowed client states: `unknown`, `format-claimed`, `import-tested`, `playback-tested`, `incompatible`. Use `playback-tested` only after a real playback test, and record the client version and date. Keep the client key stable (`yingshicang` denotes 影视仓).

Each catalog file is a JSON array. Use the matching resource category and allowed format listed in `schemas/catalog.schema.json`. Entry IDs must be unique across all catalog files.

## Local checks

Requires Python 3.10+ and the standard library only.

```sh
python3 scripts/check_catalog.py
python3 scripts/check_catalog.py --check-urls
```

URL checks are opt-in because they contact third-party hosts. They only issue bounded GET requests, do not follow redirects to non-HTTP(S) schemes, limit response size, and never execute returned content. A failed probe is reported as a transient check result, not an automatic catalog deletion. HTTP results may vary by network, geographic location, user agent, or service policy.

## GitHub Actions

Pull requests and pushes run offline schema/format validation. A scheduled/manual job can run URL checks and publish a report artifact; it does not commit catalog changes or rewrite entries. See `.github/workflows/catalog-check.yml`.

## Publishing

The catalog JSON files are the canonical output and can be served through GitHub Pages or `raw.githubusercontent.com`. They are indexes to upstream resources, not mirrors. Enable Pages from the repository's Actions workflow only after reviewing every entry and its publication rights.

## Legal and safety

This is a technical index, not an endorsement. Resource providers control their own content and terms. Add only resources whose links and metadata you are entitled to publish; honor takedown requests. Keep automated checks to syntax and availability. Treat all external configuration and plugin code as untrusted and never execute it in CI. Users remain responsible for complying with local law and service terms.
