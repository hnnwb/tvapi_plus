import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.refresh_status import load_previous, probe_entry, safe_endpoint


class RefreshStatusTests(unittest.TestCase):
    def setUp(self):
        self.entry = {
            "id": "demo-source", "url": "https://primary.example/config.json",
            "fallback_urls": ["https://backup.example/config.json"], "format": "tvbox-json",
        }
        self.previous = {"demo-source": {"status": "ok", "last_success_at": "2026-01-02T03:04:05+00:00"}}

    @patch("scripts.refresh_status.check_catalog.validate_public_target", return_value=None)
    @patch("scripts.refresh_status.check_catalog.validate_remote")
    def test_uses_explicit_fallback_after_primary_failure(self, validate, _validate_target):
        validate.side_effect = [OSError("offline"), None]
        result = probe_entry("vod-single", self.entry, self.previous, retries=0, delay=0)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["used_fallback"])
        self.assertEqual(result["used_endpoint"], "https://backup.example/config.json")
        self.assertEqual(result["previous_last_success_at"], "2026-01-02T03:04:05+00:00")
        self.assertEqual(self.entry["url"], "https://primary.example/config.json")

    @patch("scripts.refresh_status.check_catalog.validate_public_target", return_value=None)
    @patch("scripts.refresh_status.check_catalog.validate_remote")
    def test_failure_preserves_last_success_and_marks_stale(self, validate, _validate_target):
        validate.side_effect = OSError("https://primary.example/config.json?token=secret offline")
        result = probe_entry("vod-single", self.entry, self.previous, retries=0, delay=0)
        self.assertNotIn("secret", json.dumps(result))
        self.assertIn("token=%5BREDACTED%5D", json.dumps(result))
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["stale"])
        self.assertEqual(result["last_success_at"], "2026-01-02T03:04:05+00:00")

    @patch("scripts.refresh_status.check_catalog.validate_public_target", return_value=None)
    @patch("scripts.refresh_status.check_catalog.validate_remote")
    def test_oversize_response_does_not_retry_same_endpoint(self, validate, _validate_target):
        validate.side_effect = ValueError("response exceeded 524288 bytes")
        result = probe_entry("vod-single", self.entry, self.previous, retries=3, delay=0)
        self.assertEqual(validate.call_count, 2)
        self.assertTrue(result["stale"])

    @patch("scripts.refresh_status.check_catalog.validate_public_target", return_value=None)
    @patch("scripts.refresh_status.check_catalog.validate_remote")
    def test_without_prior_success_is_not_mislabeled_stale(self, validate, _validate_target):
        validate.side_effect = [
            HTTPError("https://primary.example/config.json", 404, "gone", {}, None),
            HTTPError("https://backup.example/config.json", 404, "gone", {}, None),
        ]
        result = probe_entry("vod-single", self.entry, {}, retries=3, delay=0)
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["stale"])
        self.assertEqual(validate.call_count, 2)
        self.assertEqual(result["attempts"][-1]["endpoint"], "https://backup.example/config.json")

    @patch("scripts.refresh_status.check_catalog.validate_public_target", return_value=None)
    @patch("scripts.refresh_status.check_catalog.validate_remote")
    def test_tvbox_profile_is_forwarded_but_default_profile_remains_catalog(self, validate, _validate_target):
        entry = {"id": "single-config", "url": "https://primary.example/config.json", "format": "tvbox-json"}
        probe_entry("vod-single", entry, {}, retries=0, delay=0)
        self.assertEqual(validate.call_args.kwargs["request_profile"], "catalog")
        probe_entry("vod-single", entry, {}, retries=0, delay=0, request_profile="tvbox")
        self.assertEqual(validate.call_args.kwargs["request_profile"], "tvbox")

    @patch("scripts.check_catalog.validate_public_target", return_value=None)
    @patch("scripts.check_catalog.validate_remote")
    def test_catalog_cli_forwards_tvbox_profile(self, validate, _validate_target):
        from scripts import check_catalog
        with patch.object(check_catalog, "validate_catalog", return_value=([("vod-single", {"id": "single-config", "url": "https://primary.example/config.json", "format": "tvbox-json"})])):
            with patch("sys.argv", ["check_catalog.py", "--check-urls", "--request-profile", "tvbox"]):
                self.assertEqual(check_catalog.main(), 0)
        self.assertEqual(validate.call_args.kwargs["request_profile"], "tvbox")

    def test_endpoint_redaction_drops_credentials_and_masks_sensitive_values(self):
        self.assertEqual(safe_endpoint("https://user:pass@example.test/a%20b?token=secret&lang=zh#frag"),
                         "https://example.test/a%20b?token=%5BREDACTED%5D&lang=zh")

    def test_missing_initial_report_is_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_previous(Path(tmp) / "missing.json"), {})

    def test_corrupt_report_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "probe-report.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_previous(path)


if __name__ == "__main__":
    unittest.main()
