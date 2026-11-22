import unittest

from scripts.audit_single_sources import candidates, json_doc, playable_urls, site_api_key, title_is_explicit_4k


class CandidateTests(unittest.TestCase):
    def test_extracts_and_deduplicates_priority_and_backup(self):
        source = """### 优选接口
| 名称 | 说明 | 接口 |
|---|---|---|
| A | x | `https://example.com/a.json` |
### 备用接口
| B | x | `https://example.com/a.json` |
| C | x | `http://example.com/b.json` |
### 多仓接口
| D | x | `https://example.com/c.json` |
"""
        result = candidates(source)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["listed_in"], ["优选接口", "备用接口"])

    def test_rejects_wrapped_body_without_decoding(self):
        with self.assertRaises(ValueError):
            json_doc(b"\x89PNG\r\n")

    def test_requires_json(self):
        self.assertEqual(json_doc(b'{"sites": []}'), {"sites": []})

    def test_type1_api_is_based_on_subscription_url(self):
        self.assertEqual(site_api_key({"api": "api.php/provide/vod/"}, "https://example.com/cfg.json"),
                         "https://example.com/api.php/provide/vod")
        self.assertIsNone(site_api_key({"api": "csp_Demo"}, "https://example.com/cfg.json"))

    def test_jsonc_comments_trailing_commas_and_literals(self):
        self.assertEqual(json_doc(b'{// comment\n"url":"https://a//b/*literal*/", "x":[1,],}'),
                         {"url": "https://a//b/*literal*/", "x": [1]})

    def test_base64_and_gzip_json(self):
        import base64, gzip
        payload = b'{"sites":[]}'
        self.assertEqual(json_doc(base64.b64encode(payload)), {"sites": []})
        self.assertEqual(json_doc(gzip.compress(payload)), {"sites": []})

    def test_gzip_decompression_is_bounded(self):
        import gzip
        from scripts.audit_single_sources import decompress_gzip_bounded
        bomb = gzip.compress(b"0" * 4096)
        with self.assertRaisesRegex(ValueError, "decompressed body exceeds"):
            decompress_gzip_bounded(bomb, cap=1024)

    def test_extracts_play_urls(self):
        self.assertEqual(playable_urls({"vod_play_url": "1080p$https://cdn.test/a.m3u8#tag"}),
                         ["https://cdn.test/a.m3u8"])

    def test_4k_title_detection_rejects_incidental_number(self):
        self.assertFalse(title_is_explicit_4k("我的24k氪金神眼"))
        self.assertTrue(title_is_explicit_4k("电影 4K UHD"))
        self.assertTrue(title_is_explicit_4k("纪录片2160p"))
        self.assertFalse(title_is_explicit_4k("普通影片 4K修复"))
        self.assertTrue(title_is_explicit_4k("电影-4K版"))

    def test_media_probe_is_disabled_without_network_sandbox(self):
        from scripts.audit_single_sources import probe_media
        self.assertEqual(probe_media("https://cdn.test/a.m3u8")["status"], "not-probed")


if __name__ == "__main__":
    unittest.main()
