import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CatalogClassificationTests(unittest.TestCase):
    def test_multi_source_catalog_notes_state_audited_count_and_limits(self):
        rows = json.loads((ROOT / "catalog/vod-multi.json").read_text(encoding="utf-8"))
        expected = {
            "tvboxorg-multi-subscription": "21 urls entries",
            "zhuiju-xiao-he-zi-multi": "18 urls entries",
            "zhuiju-shi-guang-multi": "54 urls entries",
            "zhuiju-ting-hao-share-multi": "32 urls entries",
            "noimank-multi-subscription": "14 urls entries",
            "lightconer-multi-subscription": "9 urls entries",
        }
        indexed = {row["id"]: row for row in rows}
        self.assertEqual(set(indexed), set(expected))
        for entry_id, count_note in expected.items():
            with self.subTest(entry=entry_id):
                row = indexed[entry_id]
                self.assertEqual(row["format"], "tvbox-multi")
                self.assertIn(count_note, row["notes"])
                self.assertIn("not tested", row["notes"])
                self.assertIn("client import", row["notes"])
                self.assertTrue(row["license"])
                self.assertTrue(row["source"])

    def test_open_source_intros_capture_useful_capabilities_from_upstream(self):
        rows = json.loads((ROOT / "catalog/tools.json").read_text(encoding="utf-8"))
        indexed = {row["id"]: row for row in rows}
        expected_phrases = {
            "zhuiju-cloudsaver": "桌面与移动端适配的 Web 界面",
            "zhuiju-animeko": "多视频源、弹幕和离线缓存",
            "zhuiju-github-com-49": "M3U/M3U8/TXT",
        }
        for entry_id, phrase in expected_phrases.items():
            with self.subTest(entry=entry_id):
                self.assertIn(phrase, indexed[entry_id]["notes"])
                self.assertIn("Upstream description:", indexed[entry_id]["notes"])

    def test_upstream_app_download_pages_are_catalogued_as_apps(self):
        app_ids = {
            "zhuiju-selenetv-app",
            "zhuiju-android-yingshi-app",
            "zhuiju-yangke-peekpro",
            "zhuiju-webhometv-player",
            "zhuiju-ok-yingshi-player",
        }
        apps = json.loads((ROOT / "catalog/apps.json").read_text(encoding="utf-8"))
        online = json.loads((ROOT / "catalog/online.json").read_text(encoding="utf-8"))
        app_rows = {row["id"]: row for row in apps if row["id"] in app_ids}
        online_ids = {row["id"] for row in online}

        self.assertEqual(set(app_rows), app_ids)
        self.assertFalse(app_ids & online_ids)
        for row in app_rows.values():
            self.assertEqual(row["format"], "link-page")
            self.assertIn("not independently confirmed", row["notes"])
            self.assertIn("not reviewed", row["notes"])
            self.assertTrue(row["license"])
            self.assertTrue(row["source"])


if __name__ == "__main__":
    unittest.main()
