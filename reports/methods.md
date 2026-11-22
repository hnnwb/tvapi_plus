# Existing TVBox validation methods

Inspected on 2026-11-21; source code was read, not executed.

- [TVboxorg/TVbox `scripts/probe.py`](https://raw.githubusercontent.com/TVboxorg/TVbox/main/scripts/probe.py): GET with a 65,536-byte read limit and 12s timeout; checks HTTP and shallow config markers (`sites`, `lives`, `spider`, `parses`, `wallpaper`). No CMS search/detail or media/decode test. Workflow: https://raw.githubusercontent.com/TVboxorg/TVbox/main/.github/workflows/probe.yml runs periodically and publishes `dist`.
- [juhe-subhub `checker.py`](https://raw.githubusercontent.com/zhuzhuyule/juhe-subhub/main/checker.py) and [`run_once.py`](https://raw.githubusercontent.com/zhuzhuyule/juhe-subhub/main/run_once.py): layered connectivity/structure/info checks, tolerant JSONC and wrapped config decoding, optional sampled CMS/playlist checks. Its optional `probe_play` can fetch direct m3u8/mp4 links and may use ffprobe, but does not run the actual TVBox Spider/JAR or app player. Probe code uses a 32MiB cap and at times disables TLS verification; not adopted wholesale.
- The hgtuj5688 desktop project `scripts/apply-sources.mjs` (read in an earlier round) uses a local app/CDP, deletes configured sources before import, checks only one result's detail and a Range request; not safe to run against an existing app and Range is not decoding.

This repo's `scripts/audit_single_sources.py` adopts bounded reads, explicit layers, and schema-aware API response checks while retaining certificate validation, checking public IPs, and not following redirects to private hosts. It does not claim playback validation.
