# awesome-tvbox candidate snapshot

- Upstream: https://raw.githubusercontent.com/jiji262/awesome-tvbox/main/README.md
- Fetched: 2026-11-21 (UTC)
- SHA-256: `9d19b1315996f5a2a7f1c5f261c4fff2e57b0b9cbaf55b1b45430e6e267a8be3`
- The audit extracts only the `优选接口` and `备用接口` markdown tables: 50 rows, 48 unique literal URLs.
- The full upstream README remains the canonical input; this snapshot manifest records provenance/hash, not duplicated third-party source configuration.

## Reproduction

```sh
curl -L --connect-timeout 12 --max-time 30 \
  https://raw.githubusercontent.com/jiji262/awesome-tvbox/main/README.md \
  -o /tmp/awesome-tvbox-current.md
python3 scripts/audit_single_sources.py \
  --readme-file /tmp/awesome-tvbox-current.md
```

The JSON report records the exact hash of the README used. A changed upstream README produces a different hash and potentially a different candidate set.
