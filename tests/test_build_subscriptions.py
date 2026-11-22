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
            subscriptions, index = build_subscriptions.build(catalog)
        self.assertEqual(subscriptions["urls"], [
            {"name": "Single", "url": single["url"]},
            {"name": "Multi", "url": multi["url"]},
        ])
        self.assertEqual([item["url"] for item in index["configs"]], [single["url"], multi["url"], untested["url"]])

    def test_empty_real_catalog_builds_empty_manifests(self):
        with tempfile.TemporaryDirectory() as tmp:
            catalog = self.write_catalog(Path(tmp))
            self.assertEqual(build_subscriptions.build(catalog), ({"urls": []}, {"configs": []}))

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

    def test_writes_contract_paths_under_one_output_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            catalog = self.write_catalog(root)
            subscriptions, index = build_subscriptions.build(catalog)
            output = root / "public"
            build_subscriptions.write_outputs(output, subscriptions, index)
            self.assertEqual(json.loads((output / "configs.json").read_text()), index)
            self.assertEqual(json.loads((output / "subscriptions/tvbox-multi.json").read_text()), subscriptions)


if __name__ == "__main__":
    unittest.main()
