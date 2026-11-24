import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CatalogClassificationTests(unittest.TestCase):
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
