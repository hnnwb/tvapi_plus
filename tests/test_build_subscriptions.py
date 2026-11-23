import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_subscriptions
import check_catalog


def record(entry_id, name, url, format_name):
    return {"id": entry_id, "name": name, "url": url, "format": format_name,
            "source": "https://source.test", "license": "Reviewed upstream terms",
            "notes": "Test fixture"}


def evidence(entry_id):
    return {"id": entry_id, "client": "TVBox test fixture", "version": "1.0",
            "tested_at": "2026-11-22", "scope": "one sample, picture and sound",
            "duration_seconds": 30, "result": "passed"}


class BuildSubscriptionTests(unittest.TestCase):
    def write_catalog(self, root, single=None, multi=None, evidence_rows=None):
        catalog = root / "catalog"
        catalog.mkdir(parents=True, exist_ok=True)
        documents = {
            "vod-single.json": single or [], "vod-multi.json": multi or [],
            "live.json": [], "epg.json": [], "tools.json": [],
            "playback-evidence.json": evidence_rows or [],
        }
        for name, document in documents.items():
            (catalog / name).write_text(json.dumps(document), encoding="utf-8")
        return catalog

    def test_validated_evidence_gates_subscription_and_outputs_are_deduplicated(self):
        single = record("single-config", "Single", "https://example.test/single.json", "tvbox-json")
        multi = record("multi-config", "Multi", "https://example.test/multi.json", "tvbox-multi")
        duplicate = record("duplicate-config", "Duplicate", single["url"], "tvbox-multi")
        untested = record("untested-config", "Untested", "https://example.test/untested.json", "tvbox-multi")
        with tempfile.TemporaryDirectory() as tmp:
            catalog = self.write_catalog(Path(tmp), [single], [multi, duplicate, untested], [evidence("single-config"), evidence("multi-config")])
            subscriptions, index, custom = build_subscriptions.build(catalog, custom_candidates=Path("/missing/candidates.json"))
        self.assertIsNone(custom)
        self.assertEqual([item["url"] for item in index["configs"]], [single["url"], multi["url"], untested["url"]])
        self.assertEqual(subscriptions["urls"], [
            {"name": "Single", "url": single["url"]},
            {"name": "Multi", "url": multi["url"]},
        ])

    def test_empty_real_catalog_builds_empty_manifests(self):
        with tempfile.TemporaryDirectory() as tmp:
            catalog = self.write_catalog(Path(tmp))
            subscriptions, index, custom = build_subscriptions.build(catalog, custom_candidates=Path("/missing/candidates.json"))
            self.assertEqual((subscriptions, index, custom), ({"urls": []}, {"configs": []}, None))

    def test_rejects_non_http_urls_through_shared_validator(self):
        unsafe = record("unsafe-config", "Unsafe", "file:///etc/passwd", "tvbox-json")
        with tempfile.TemporaryDirectory() as tmp:
            catalog = self.write_catalog(Path(tmp), [unsafe])
            with self.assertRaisesRegex(ValueError, "url must be an http\(s\) URL"):
                build_subscriptions.build(catalog)

    def test_rejects_wrong_format_through_shared_validator(self):
        wrong = record("wrong-config", "Wrong", "https://example.test/", "m3u")
        with tempfile.TemporaryDirectory() as tmp:
            catalog = self.write_catalog(Path(tmp), [wrong])
            with self.assertRaisesRegex(ValueError, "format must be one of"):
                build_subscriptions.build(catalog)

    def test_invalid_evidence_fails_closed(self):
        item = record("single-config", "Single", "https://example.test/single.json", "tvbox-json")
        short_test = evidence("single-config")
        short_test["duration_seconds"] = 29
        with tempfile.TemporaryDirectory() as tmp:
            catalog = self.write_catalog(Path(tmp), [item], evidence_rows=[short_test])
            with self.assertRaisesRegex(ValueError, "duration_seconds"):
                build_subscriptions.build(catalog)

    def test_validator_contract_matches_catalog_and_evidence_schemas(self):
        root = Path(__file__).resolve().parents[1]
        catalog_schema = json.loads((root / "schemas/catalog.schema.json").read_text())
        evidence_schema = json.loads((root / "schemas/playback-evidence.schema.json").read_text())
        self.assertEqual(set(catalog_schema["required"]), {"id", "name", "url", "format", "source", "license", "notes"})
        self.assertEqual(set(catalog_schema["properties"]) - {"fallback_urls"}, set(catalog_schema["required"]))
        self.assertEqual(catalog_schema["$defs"]["playbackEvidenceList"]["type"], "array")
        self.assertEqual(catalog_schema["$defs"]["playbackEvidenceList"]["items"]["$ref"], "#/$defs/playbackEvidence")
        self.assertEqual(evidence_schema["type"], "array")
        self.assertEqual(evidence_schema["items"]["$ref"], "#/$defs/playbackEvidence")
        evidence_list = catalog_schema["$defs"]["playbackEvidenceList"]
        self.assertEqual(evidence_list["type"], "array")
        self.assertEqual(evidence_list["items"]["$ref"], "#/$defs/playbackEvidence")
        evidence_shape = catalog_schema["$defs"]["playbackEvidence"]
        self.assertEqual(set(evidence_shape["required"]), check_catalog.PLAYBACK_EVIDENCE_FIELDS)
        self.assertEqual(evidence_shape["properties"]["duration_seconds"]["minimum"], check_catalog.MIN_PLAYBACK_SECONDS)
        self.assertEqual(evidence_schema["$schema"], catalog_schema["$schema"])

    def test_custom_single_index_and_file_are_built_once_from_report(self):
        from build_custom_single import build as build_custom_single
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            catalog = self.write_catalog(root)
            report = {
                "schema_version": 1,
                "generated_at": "2026-11-22T00:00:00Z",
                "source_snapshot_sha256": "abc",
                "summary": {"included": 1},
                "limits": {"config_candidates": 48},
                "interfaces": [
                    {"decision": "include", "screen_status": "cms-api-tested", "api": "https://api.example/vod", "name": "CMS", "key": "cms", "detail_has_stream_url": True, "tests": {name: {"ok": True} for name in ("list", "search", "detail")}},
                ],
            }
            evidence_path = root / "screening.json"
            evidence_path.write_text(json.dumps(report), encoding="utf-8")
            subscriptions, index, config = build_subscriptions.build(catalog, evidence_path)
            output = root / "public"
            build_subscriptions.write_outputs(output, subscriptions, index, config)
            written = json.loads((output / "subscriptions/tvbox-custom-single.json").read_text())
        self.assertEqual(len(index["configs"]), 1)
        self.assertEqual(index["configs"][0]["id"], "tvapi-plus-custom-single")
        self.assertEqual(index["configs"][0]["display_order"], 1)
        self.assertEqual(written["sites"], [{"key": "cms", "name": "CMS", "type": 1, "api": "https://api.example/vod", "searchable": 1, "quickSearch": 1, "filterable": 1}])
        self.assertEqual(set(written), {"spider", "wallpaper", "sites", "parses", "lives", "ads"})

    def test_custom_candidate_is_first_ahead_of_xiaoma_and_multi(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            catalog = self.write_catalog(root, single=[record("xiaoma-tvbox-config", "Xiaoma", "https://xiaoma.example/config.json", "tvbox-json")], multi=[record("tvboxorg-multi-subscription", "Multi", "https://multi.example/config.json", "tvbox-multi")])
            audit_path = root / "audit.json"
            audit_path.write_text(json.dumps({"results": [{"config": {"result": "tvbox-json-structural"}, "cms": [{"api": "https://cms.example/vod", "key": "cms", "name": "CMS"}]}]}), encoding="utf-8")
            _, index, _ = build_subscriptions.build(catalog, custom_candidates=audit_path)
        self.assertEqual([row["id"] for row in index["configs"]], ["tvapi-plus-custom-single", "xiaoma-tvbox-config", "tvboxorg-multi-subscription"])
        self.assertEqual([row["display_order"] for row in index["configs"]], [1, 2, 3])

    def test_candidate_fallback_builds_deduplicated_unverified_apis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit_report = {
                "results": [
                    {"name": "First", "config": {"result": "tvbox-json-structural"}, "cms": [
                        {"api": "https://cms.example/api.php/provide/vod", "key": "first", "name": "CMS A"},
                        {"api": "https://cms.example/api.php/provide/vod", "key": "dupe", "name": "CMS duplicate"},
                    ]},
                    {"name": "Third-party parser config", "config": {"result": "failed"}, "cms": [
                        {"api": "https://not-structural.example/vod", "key": "ignored", "name": "Ignored"},
                    ]},
                ]
            }
            audit_path = root / "audit.json"
            audit_path.write_text(json.dumps(audit_report), encoding="utf-8")
            catalog = self.write_catalog(root)
            screening_path = root / "screening.json"
            screening_path.write_text(json.dumps({"schema_version": 1, "interfaces": [], "summary": {"included": 0}}), encoding="utf-8")
            subscriptions, index, config = build_subscriptions.build(catalog, screening_path, audit_path)
            output = root / "public"
            build_subscriptions.write_outputs(output, subscriptions, index, config, build_subscriptions.build_custom_candidates_status(audit_path))
            written = json.loads((output / "subscriptions/tvbox-custom-single.json").read_text())
        self.assertEqual([row["id"] for row in index["configs"]], ["tvapi-plus-custom-single"])
        self.assertEqual([row["display_order"] for row in index["configs"]], [1])
        self.assertEqual(len(written["sites"]), 1)
        self.assertEqual([x["api"] for x in config["sites"]], ["https://cms.example/api.php/provide/vod"])
        self.assertTrue(all(site["type"] == 1 for site in config["sites"]))
        self.assertIn("候选未实播", index["configs"][0]["name"])
        with tempfile.TemporaryDirectory() as tmp:
            status_path = Path(tmp) / "audit.json"
            status_path.write_text(json.dumps(audit_report), encoding="utf-8")
            status = build_subscriptions.build_custom_candidates_status(status_path)
        self.assertEqual(status["verification_status"], "unverified-candidate")
        self.assertEqual(status["unique_candidate_apis"], 1)
        self.assertEqual(status["structurally_parsed_configs"], 1)
        self.assertEqual(status["screened_api_candidates"], 0)
        self.assertEqual(status["historical_failed_or_unparsed_configs"], 0)
        self.assertEqual(status["historical_config_status_counts"], {})

    def test_candidate_status_preserves_failure_categories_without_calling_them_policy_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            audit = {
                "results": [
                    {"config": {"result": "failed", "error": "HTTPError: HTTP Error 404: Not Found"}, "cms": []},
                    {"config": {"result": "failed", "error": "ValueError: URL hostname did not resolve to a safe public address"}, "cms": []},
                ],
                "status_counts": {"failed": 2},
            }
            path = Path(tmp) / "audit.json"
            path.write_text(json.dumps(audit), encoding="utf-8")
            status = build_subscriptions.build_custom_candidates_status(path)
        self.assertEqual(status["historical_failed_or_unparsed_configs"], 2)
        self.assertEqual(status["historical_network_denied_config_requests"], 1)
        self.assertEqual(status["historical_config_status_counts"], {"failed": 2})

    def test_custom_single_requires_current_cms_flow_and_direct_url(self):
        report = {
            "schema_version": 1,
            "generated_at": "2026-11-22T00:00:00Z",
            "source_snapshot_sha256": "abc",
            "interfaces": [
                {"decision": "include", "screen_status": "cms-api-tested", "api": "https://api.example/vod", "name": "CMS", "key": "cms", "detail_has_stream_url": True, "tests": {name: {"ok": True} for name in ("list", "search", "detail")}},
                {"decision": "include", "screen_status": "blocked-policy", "api": "https://blocked.example/vod", "name": "Blocked", "key": "blocked", "detail_has_stream_url": True, "tests": {name: {"ok": True} for name in ("list", "search", "detail")}},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            evidence_path = Path(tmp) / "screening.json"
            evidence_path.write_text(json.dumps(report), encoding="utf-8")
            config = build_subscriptions.build_custom_single(evidence_path)
        self.assertEqual([site["api"] for site in config["sites"]], ["https://api.example/vod"])
        self.assertEqual(set(config), {"spider", "wallpaper", "sites", "parses", "lives", "ads"})

    def test_writes_contract_paths_under_one_output_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            catalog = self.write_catalog(root)
            subscriptions, index, custom = build_subscriptions.build(catalog, custom_candidates=Path("/missing/candidates.json"))
            output = root / "public"
            build_subscriptions.write_outputs(output, subscriptions, index, custom)
            self.assertEqual(json.loads((output / "configs.json").read_text()), index)
            self.assertEqual(json.loads((output / "subscriptions/tvbox-multi.json").read_text()), subscriptions)
            self.assertFalse((output / "subscriptions/tvbox-custom-single.json").exists())

if __name__ == "__main__":
    unittest.main()
