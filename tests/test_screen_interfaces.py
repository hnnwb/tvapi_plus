import unittest
from unittest.mock import patch

from scripts.screen_interfaces import collect, test_interface


class CollectTests(unittest.TestCase):
    def test_only_extracts_type1_from_refetched_structural_configs(self):
        config = {"sites": [
            {"type": 1, "name": "CMS", "api": "https://api.example/vod"},
            {"type": 3, "name": "Spider", "api": "https://api.example/spider.js"},
        ]}
        report = {"results": [{"name": "Config", "url": "https://cfg.example/a.json", "config": {"result": "tvbox-json-structural", "url": "https://cfg.example/a.json"}}]}
        with patch("scripts.screen_interfaces.audit.fetch_json_document", return_value=config), patch("scripts.screen_interfaces.audit.candidates", return_value=[{"url": "https://cfg.example/a.json", "name": "Config"}]):
            rows, errors, parsed = collect("", report)
        self.assertEqual([row["api"] for row in rows], ["https://api.example/vod"])
        self.assertEqual((errors, parsed), ([], 1))

    def test_duplicate_api_from_multiple_configs_retains_all_origins(self):
        cfg1 = {"sites": [{"type": 1, "name": "API", "api": "https://api.example/vod"}]}
        configs = [
            {"name": "A", "url": "https://a.example/c.json", "config": {"result": "tvbox-json-structural", "url": "https://a.example/c.json"}},
            {"name": "B", "url": "https://b.example/c.json", "config": {"result": "tvbox-json-structural", "url": "https://b.example/c.json"}},
        ]
        with patch("scripts.screen_interfaces.audit.fetch_json_document", side_effect=[cfg1, cfg1]), patch("scripts.screen_interfaces.audit.candidates", return_value=[{"url": x["url"], "name": x["name"]} for x in configs]):
            rows, errors, parsed = collect("", {"results": configs})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["config_origins"], ["A", "B"])
        self.assertEqual((errors, parsed), ([], 2))

    def test_historical_samples_are_excluded_from_current_collection(self):
        report = {"results": [{"name": "Old", "url": "https://cfg.example/a", "cms": [{"api": "https://api.example/vod", "status": 200}], "config": {"result": "failed"}}]}
        rows, errors, parsed = collect("", report)
        self.assertEqual(rows, [])
        self.assertEqual((errors, parsed), ([], 0))


class ScreeningTests(unittest.TestCase):
    @patch("scripts.screen_interfaces.audit.socket.getaddrinfo", return_value=[(None, None, None, None, ("198.18.0.5", 80))])
    def test_policy_block_is_not_reported_as_upstream_failure(self, _dns):
        result = test_interface({"api": "https://api.example/vod", "name": "Example", "config_origins": []})
        self.assertEqual(result["screen_status"], "blocked-policy")
        self.assertEqual(result["decision"], "exclude")
        self.assertNotIn("http", result["tests"])

    @patch("scripts.screen_interfaces.audit.api_probe")
    @patch("scripts.screen_interfaces.audit.socket.getaddrinfo", return_value=[(None, None, None, None, ("93.184.216.34", 80))])
    def test_cms_flow_records_api_only_not_client_playback(self, _dns, probe):
        probe.side_effect = [
            {"ok": True, "http": 200, "ms": 10, "nonempty": True, "rows": 1, "schema": "vod-list", "items": [{"vod_name": "A", "vod_id": "1"}]},
            {"ok": True, "http": 200, "ms": 11, "nonempty": True, "rows": 1, "schema": "vod-list", "items": [{"vod_name": "A", "vod_id": "1"}]},
            {"ok": True, "http": 200, "ms": 12, "nonempty": True, "rows": 1, "schema": "vod-detail", "items": [{"vod_name": "A", "vod_play_url": "HD$https://media.example/a.m3u8"}]},
        ]
        result = test_interface({"api": "https://api.example/vod", "name": "Example", "config_origins": []})
        self.assertEqual(result["screen_status"], "cms-api-tested")
        self.assertEqual(result["decision"], "include")
        self.assertTrue(result["detail_has_stream_url"])
        self.assertNotIn("stream_manifest", result["tests"])
        self.assertIn("not tested", result["reason"])


if __name__ == "__main__":
    unittest.main()
