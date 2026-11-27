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

    def test_reference_indexes_are_listed_as_open_source_projects(self):
        rows = json.loads((ROOT / "catalog/tools.json").read_text(encoding="utf-8"))
        indexed = {row["id"]: row for row in rows}
        expected = {
            "reference-awesome-tvbox": (
                "https://github.com/jiji262/awesome-tvbox",
                "CC0 1.0",
            ),
            "reference-awesome-zhuiju-free": (
                "https://github.com/laoma528/awesome-zhuiju-free",
                "CC BY 4.0",
            ),
        }
        for entry_id, (url, license_note) in expected.items():
            with self.subTest(entry=entry_id):
                row = indexed[entry_id]
                self.assertEqual(row["url"], url)
                self.assertEqual(row["format"], "project")
                self.assertIn(license_note, row["license"])
                self.assertIn("Upstream description:", row["notes"])
                self.assertTrue(row["source"])

    def test_tvapp_reference_and_voyatv_are_listed_with_scope_limits(self):
        tools = json.loads((ROOT / "catalog/tools.json").read_text(encoding="utf-8"))
        apps = json.loads((ROOT / "catalog/apps.json").read_text(encoding="utf-8"))
        tool_rows = {row["id"]: row for row in tools}
        app_rows = {row["id"]: row for row in apps}

        tvapp = tool_rows["reference-youhun-tvapp"]
        self.assertEqual(tvapp["url"], "https://github.com/youhunwl/TVAPP")
        self.assertEqual(tvapp["format"], "project")
        self.assertIn("Apache", tvapp["license"])
        self.assertIn("third-party APKs", tvapp["license"])
        self.assertIn("index only", tvapp["notes"])

        voyatv = app_rows["voyatv-iptv-player"]
        self.assertEqual(voyatv["url"], "https://xptv.nb9.xyz/")
        self.assertEqual(voyatv["format"], "link-page")
        self.assertIn("Android TV", voyatv["notes"])
        self.assertIn("M3U/M3U8/TXT", voyatv["notes"])
        self.assertIn("不提供或托管直播源", voyatv["notes"])
        self.assertTrue(voyatv["source"])

        kodi = app_rows["app-kodi-media-center"]
        self.assertEqual(kodi["url"], "https://github.com/xbmc/xbmc")
        self.assertEqual(kodi["format"], "project")
        self.assertIn("GPL-2.0-or-later", kodi["license"])
        self.assertIn("macOS", kodi["notes"])

    def test_free_tv_playlist_is_separate_from_iptv_org_and_has_rights_caveat(self):
        rows = json.loads((ROOT / "catalog/live.json").read_text(encoding="utf-8"))
        indexed = {row["id"]: row for row in rows}
        free_tv = indexed["free-tv-global-playlist"]
        self.assertEqual(free_tv["url"], "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8")
        self.assertEqual(free_tv["format"], "m3u")
        self.assertIn("No repository-wide license", free_tv["license"])
        self.assertIn("#EXTM3U", free_tv["notes"])
        self.assertIn("No playback", free_tv["notes"])

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

    def test_backup_index_rows_keep_their_measured_shape(self):
        index = "https://lubin776.github.io/tvbox-api-backup/"
        vod = [row for row in json.loads((ROOT / "catalog/vod-single.json").read_text(encoding="utf-8"))
               if row["id"].startswith("backup-")]
        live = [row for row in json.loads((ROOT / "catalog/live.json").read_text(encoding="utf-8"))
                if row["id"].startswith("backup-")]
        self.assertGreaterEqual(len(vod), 14)
        self.assertGreaterEqual(len(live), 35)
        for row in vod:
            self.assertEqual(row["format"], "tvbox-json")
            self.assertEqual(row["source"], index)
            self.assertIn("sites", row["notes"])
        for row in live:
            self.assertIn(row["format"], {"m3u", "txt"})
            self.assertEqual(row["source"], index)
            self.assertTrue("#EXTINF" in row["notes"] or "channel lines" in row["notes"])
        rows = vod + live
        self.assertEqual(len({row["id"] for row in rows}), len(rows))
        urls = [row["url"] for row in rows]
        self.assertEqual(len(set(urls)), len(urls))
        for row in rows:
            # Reachability, not playback or rights: the wording has to stay honest.
            notes = row["notes"]
            self.assertTrue("no client import or playback was tested" in notes
                            or "no playback or client import was tested" in notes)


if __name__ == "__main__":
    unittest.main()
