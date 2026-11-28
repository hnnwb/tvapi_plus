import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_custom_live as live


class FakeProcess:
    def __init__(self, stdout=b"", stderr=b"", returncode=0):
        self.stdin = mock.Mock()
        self.stdin.write = mock.Mock()
        self.stdin.flush = mock.Mock()
        self.stdin.close = mock.Mock()
        self.stdout = io.BytesIO(stdout)
        self.stderr = io.BytesIO(stderr)
        self.returncode = returncode
        self.killed = False

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9


class CustomLiveParserTests(unittest.TestCase):
    def test_m3u_parser_keeps_metadata_and_parses_utf8(self):
        text = ('#EXTM3U\n#EXTINF:-1 tvg-id="CCTV1.cn@HD" tvg-logo="https://logo.test/1.png" group-title="China",CCTV-1 综合\nhttps://stream.test/cctv1.m3u8\n')
        rows, counts = live.parse_m3u(text)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "CCTV-1 综合")
        self.assertEqual(rows[0]["tvg_id"], "CCTV1.cn@HD")
        self.assertEqual(rows[0]["group"], "China")
        self.assertEqual(counts["parsed"], 1)

    def test_m3u_parser_handles_commas_in_quoted_attributes_and_names(self):
        text = '#EXTM3U\n#EXTINF:-1 tvg-id="news.cn" group-title="News, China",Channel, East\nhttps://stream.test/live.m3u8\n'
        rows, counts = live.parse_m3u(text)
        self.assertEqual(rows[0]["group"], "News, China")
        self.assertEqual(rows[0]["name"], "Channel, East")
        self.assertEqual(counts["parsed"], 1)

    def test_m3u_parser_rejects_broken_rows_and_counts_missing_url(self):
        rows, counts = live.parse_m3u('#EXTM3U\n#EXTINF:-1,Missing\n#EXTINF:-1,Bad URL\nfile:///tmp/x\n')
        self.assertEqual(rows, [])
        self.assertEqual(counts["missing_url"], 1)
        self.assertEqual(counts["invalid_rows"], 1)

    def test_txt_parser_uses_genre_sections_and_strips_source_suffix(self):
        rows, counts = live.parse_txt("央视,#genre#\nCCTV1综合,https://stream.test/cctv.m3u8$线路一\n")
        self.assertEqual(rows[0]["group"], "央视")
        self.assertEqual(rows[0]["url"], "https://stream.test/cctv.m3u8")
        self.assertEqual(counts["group_headers"], 1)

    def test_probe_request_url_encodes_unicode_and_rejects_fragments(self):
        encoded = live._request_url("https://example.test/频道 1.m3u8?id=12&lang=中文")
        self.assertEqual(encoded, "https://example.test/%E9%A2%91%E9%81%93%201.m3u8?id=12&lang=%E4%B8%AD%E6%96%87")
        with self.assertRaisesRegex(ValueError, "fragment"):
            live._request_url("https://example.test/live.m3u8#part")

    def test_probe_response_survives_unavailable_socket_metadata(self):
        socket_obj = mock.Mock()
        socket_obj.fileno.side_effect = OSError("closed socket")
        response = mock.Mock()
        response.fp.raw._sock = socket_obj
        response.read.side_effect = [b"sample", b""]
        response.headers.get_content_type.return_value = "video/mp2t"
        response.status = 200
        body, content_type, status, final_url = live._read_probe_response(
            response, 32, 1, None, "https://example.test/live")
        self.assertEqual((body, content_type, status), (b"sample", "video/mp2t", 200))
        self.assertEqual(final_url, "https://example.test/live")

    def test_signed_or_non_http_urls_are_excluded(self):
        self.assertEqual(live.channel_url_allowed("https://x.test/live.m3u8?wsSecret=abc")[1], "credential-or-expiring-query")
        self.assertEqual(live.channel_url_allowed("rtmp://x.test/live")[1], "non-http-url")
        self.assertEqual(live.channel_url_allowed("https://x.test/live.m3u8#fragment")[1], "url-fragment-not-supported")
        self.assertEqual(live.channel_url_allowed("https://x.test/live.m3u8?id=" + "a" * 40)[1], "opaque-or-long-query-value")
        self.assertEqual(live.channel_url_allowed("https://x.test/live.m3u8?id=" + "1" * 40)[1], "opaque-or-long-query-value")
        self.assertEqual(live.channel_url_allowed("https://x.test/live.m3u8?id=12345678901234567890")[1], "included")
        self.assertEqual(live.channel_url_allowed("https://x.test/replay.mp4")[1], "vod-file-extension")
        self.assertEqual(live.channel_url_allowed("http://127.0.0.1/live.m3u8")[1], "non-public-address")
        self.assertFalse(live.channel_url_allowed("http://user:pass@x.test/live.m3u8")[0])
        self.assertTrue(live.channel_url_allowed("https://x.test/live.m3u8")[0])

    def test_channel_classification_handles_cctv_satellite_regional_and_special(self):
        self.assertEqual(live.classify("CCTV-1 综合", "CCTV1.cn@HD", "CN"), "央视")
        self.assertEqual(live.classify("北京卫视", "BeijingSatelliteTV.cn@HD", "CN"), "卫视")
        self.assertEqual(live.classify("Anshun Comprehensive News Channel", "Anshun.cn@SD", "CN"), "地方频道")
        self.assertEqual(live.classify("CCTV-14 少儿", "CCTV14.cn@HD", "CN"), "央视")
        self.assertEqual(live.classify("Hong Kong News", "HongKongNews.hk@SD"), "港澳台")
        self.assertEqual(live.classify("ABC News", "ABC.au@HD"), "国际频道")

    def test_deduplicates_by_tvg_id_but_preserves_source_alternatives(self):
        a = live.Channel("CCTV-1 (720p)", "https://a.test/cctv1.m3u8", "a", "A", "https://a.test", "ok", tvg_id="CCTV1.cn@SD")
        b = live.Channel("CCTV1综合", "https://b.test/cctv1.m3u8", "b", "B", "https://b.test", "ok", tvg_id="CCTV1.cn@HD")
        selected, stats = live.deduplicate([a, b], ["a", "b"])
        self.assertEqual(len(selected), 1)
        self.assertEqual(len(selected[0].alternatives), 1)
        self.assertEqual(stats["channels_with_alternatives"], 1)

    def test_default_source_config_accounts_for_every_catalog_feed(self):
        config = json.loads(live.DEFAULT_CONFIG.read_text(encoding="utf-8"))
        summary = live.validate_config(config, live.DEFAULT_CATALOG)
        self.assertEqual(summary["catalog_sources"], 50)
        self.assertEqual(summary["selected_sources"] + summary["excluded_sources"], 50)

    def test_source_config_rejects_unknown_ids_and_unsafe_urls(self):
        catalog = [{"id": "one", "name": "One", "url": "https://feed.test/list.m3u",
                    "format": "m3u", "source": "https://repo.test/one", "license": "n/a", "notes": "test"}]
        with tempfile.TemporaryDirectory() as tmp:
            catalog_dir = Path(tmp) / "catalog"
            catalog_dir.mkdir()
            (catalog_dir / "live.json").write_text(json.dumps(catalog), encoding="utf-8")
            config = json.loads(live.DEFAULT_CONFIG.read_text(encoding="utf-8"))
            config["source_ids"] = ["one"]
            config["excluded_source_ids"] = {}
            self.assertEqual(live.validate_config(config, catalog_dir)["selected_sources"], 1)
            config["excluded_source_ids"] = {"gone": "removed upstream"}
            with self.assertRaisesRegex(ValueError, "unknown_excluded"):
                live.validate_config(config, catalog_dir)

    def test_probe_channels_applies_caps_and_round_robins_groups(self):
        rows = [live.Channel(f"CCTV {i}", f"https://{i}.test/live.m3u8", "s", "S", "https://repo.test", "ok", group="央视") for i in range(4)]
        rows += [live.Channel(f"News {i}", f"https://news{i}.test/live.m3u8", "s", "S", "https://repo.test", "ok", group="特色频道") for i in range(4)]
        with mock.patch.object(live, "probe_channel", return_value=("sample-decoded", "ok")) as probe:
            report = live.probe_channels(rows, max_probes=4, workers=2, budget_seconds=1)
        self.assertEqual(report["selected_for_probe"], 4)
        self.assertEqual(report["sample_decoded"], 4)
        self.assertEqual(probe.call_count, 4)
        self.assertTrue(all("deadline" in call.kwargs for call in probe.call_args_list))
        self.assertEqual(len({call.args[0] for call in probe.call_args_list}), 4)
        with self.assertRaises(ValueError):
            live.probe_channels(rows, max_probes=0)

    def test_probe_limit_is_per_host_and_duplicates_do_not_consume_quota(self):
        rows = [live.Channel(f"CCTV {i}", f"https://same.test/{i}.m3u8", "s", "S", "https://repo.test", "ok", group="央视") for i in range(15)]
        rows.append(live.Channel("CCTV alias", "https://same.test/0.m3u8", "other", "Other", "https://repo.test/other", "ok", group="央视"))
        with mock.patch.object(live, "probe_channel", return_value=("sample-decoded", "ok")) as probe:
            report = live.probe_channels(rows, max_probes=20, workers=4, budget_seconds=1)
        self.assertEqual(report["selected_for_probe"], live.MAX_CHANNEL_PROBES_PER_HOST)
        self.assertEqual(probe.call_count, live.MAX_CHANNEL_PROBES_PER_HOST)
        self.assertEqual(report["sample_decoded"], live.MAX_CHANNEL_PROBES_PER_HOST)
        self.assertEqual(report["not_tested"], 3)

    def test_deduplicates_identical_streams_but_preserves_distinct_labels_as_alternatives(self):
        rows = [
            live.Channel("CCTV1 综合", "https://shared.test/live.m3u8", "a", "A", "https://repo.test/a", "ok", group="央视"),
            live.Channel("央视频道1", "https://shared.test/live.m3u8", "b", "B", "https://repo.test/b", "ok", group="央视"),
            live.Channel("卫视新闻", "https://shared.test/live.m3u8", "c", "C", "https://repo.test/c", "ok", group="卫视"),
        ]
        selected, stats = live.deduplicate(rows, ["a", "b", "c"])
        self.assertEqual(len(selected), 1)
        self.assertEqual(stats["duplicate_channel_urls_removed"], 2)
        self.assertEqual(len(selected[0].alternatives), 2)

    def test_daily_workflow_is_read_only_and_uploads_only_generated_outputs(self):
        workflow = ROOT / ".github" / "workflows" / "custom-live.yml"
        text = workflow.read_text(encoding="utf-8")
        self.assertIn('cron: "23 6 * * *"', text)
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("contents: read", text)
        self.assertIn('timeout-minutes: 45', text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("ffmpeg", text.lower())
        self.assertIn("actions/upload-artifact@v4", text)
        self.assertIn("retention-days: 14", text)
        self.assertIn("!cancelled()", text)
        self.assertNotIn("git push", text.lower())
        self.assertNotIn("pages", text.lower())
        pages_workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
        self.assertIn("[skip-pages]", pages_workflow)
        self.assertIn("github.event.head_commit.message", pages_workflow)
        for filename in ("custom-live.m3u", "custom-live.txt", "custom-live-sample-decoded.m3u",
                         "custom-live-sample-decoded.txt", "custom-live-status.json"):
            self.assertIn(filename, text)

    def test_outputs_keep_grouped_channels_and_redact_secret_queries_from_report(self):
        row = live.Channel("CCTV1 综合", "https://x.test/live.m3u8?token=secret", "src", "Source", "https://repo.test", "ok", group="央视", status="not-tested")
        txt = live.txt_text([row])
        m3u = live.m3u_text([row], "2026-11-28T00:00:00+00:00")
        self.assertIn("央视,#genre#", txt)
        self.assertIn("CCTV1 综合,https://x.test/live.m3u8?token=secret", txt)
        self.assertIn('group-title="央视"', m3u)
        doc = live.row_document(row)
        self.assertIn("token=%5BREDACTED%5D", doc["url"])
        self.assertNotIn("secret", json.dumps(doc))
        self.assertEqual(live.safe_url("not a url?token=secret"), "[REDACTED_URL]")
        self.assertEqual(live.safe_url("file:///etc/passwd"), "[REDACTED_URL]")
        self.assertNotIn("user:pass", live.safe_url("https://user:pass@x.test/live.m3u8"))

    def test_arbitrary_http_body_is_not_a_successful_media_probe(self):
        with mock.patch.object(live, "_fetch_probe", return_value=(b"not-html", "application/octet-stream", 200, "https://stream.test/live")):
            status, detail = live.probe_channel("https://stream.test/live")
        self.assertEqual(status, "failed")
        self.assertIn("recognized media container", detail)

    def test_ffmpeg_decode_requires_nonempty_framehash_output(self):
        output = b"# framehash header\n0,0,0,1,1,1,sha256:abc\n"
        with mock.patch.object(live.shutil, "which", return_value="/usr/bin/ffmpeg"), \
             mock.patch.object(live.subprocess, "Popen", return_value=FakeProcess(stdout=output)) as popen:
            ok, detail = live._decode_media(b"some bytes", "mpegts")
        self.assertTrue(ok)
        self.assertIn("decoded", detail)
        self.assertIn("pipe", popen.call_args.args[0])
        self.assertIn("-protocol_whitelist", popen.call_args.args[0])

    def test_ffmpeg_decode_zero_frames_is_failure(self):
        with mock.patch.object(live.shutil, "which", return_value="/usr/bin/ffmpeg"), \
             mock.patch.object(live.subprocess, "Popen", return_value=FakeProcess(stdout=b"# framehash header\n")):
            ok, detail = live._decode_media(b"some bytes", "mpegts")
        self.assertFalse(ok)
        self.assertIn("no decoded", detail)

    def test_ffmpeg_decode_rejects_excessive_output(self):
        process = FakeProcess(stdout=b"x" * (live.MAX_FFMPEG_OUTPUT_BYTES + 10))
        with mock.patch.object(live.shutil, "which", return_value="/usr/bin/ffmpeg"), \
             mock.patch.object(live.subprocess, "Popen", return_value=process):
            ok, detail = live._decode_media(b"some bytes", "mpegts")
        self.assertFalse(ok)
        self.assertIn("output exceeded", detail)

    def test_hls_targets_latest_segment_and_init_map(self):
        playlist = b"""#EXTM3U
#EXT-X-VERSION:7
#EXT-X-MAP:URI=\"init.mp4\"
#EXTINF:4.0,
old.m4s
#EXTINF:4.0,
new.m4s
"""
        variant, init_map, segment, error = live._hls_targets(playlist, "https://streams.test/live/index.m3u8")
        self.assertIsNone(variant)
        self.assertEqual(init_map, "https://streams.test/live/init.mp4")
        self.assertEqual(segment, "https://streams.test/live/new.m4s")
        self.assertIsNone(error)

    def test_hls_rejects_encryption_and_byte_ranges(self):
        encrypted = b"#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI=\"key.bin\"\n#EXTINF:4,\na.ts\n"
        _, _, _, error = live._hls_targets(encrypted, "https://streams.test/live.m3u8")
        self.assertEqual(error, "encrypted-HLS-not-supported")
        byte_range = b"#EXTM3U\n#EXT-X-BYTERANGE:100@0\n#EXTINF:4,\na.ts\n"
        _, _, _, error = live._hls_targets(byte_range, "https://streams.test/live.m3u8")
        self.assertEqual(error, "byte-range-playlist-not-supported")

    def test_build_keeps_good_source_when_another_fails_and_reports_provenance(self):
        catalog = [
            {"id": "one", "name": "CN", "url": "https://source.test/a.m3u", "format": "m3u", "source": "https://repo.test/one", "license": "n/a", "notes": "test"},
            {"id": "two", "name": "Backup", "url": "https://source.test/b.m3u", "format": "m3u", "source": "https://repo.test/two", "license": "n/a", "notes": "test"},
        ]
        config = json.loads(live.DEFAULT_CONFIG.read_text(encoding="utf-8"))
        config["source_ids"] = ["one", "two"]
        config["excluded_source_ids"] = {}
        config["policy"].update({"channel_groups": live.GROUP_ORDER,
                                  "max_source_bytes": live.MAX_SOURCE_BYTES,
                                  "max_channel_probe_bytes": live.MAX_PROBE_BYTES,
                                  "channel_probe_timeout_seconds": live.TIMEOUT_SECONDS,
                                  "channel_probe_budget_seconds": live.PROBE_BUDGET_SECONDS,
                                  "max_channel_probe_run_seconds": live.PROBE_RUN_BUDGET_SECONDS,
                                  "max_channel_probes_per_run": 160})
        body = b'#EXTM3U\n#EXTINF:-1 tvg-id="CCTV1.cn@HD",CCTV-1\nhttps://stream.test/cctv.m3u8\n'
        def fetch(entry, opener, max_body=live.MAX_SOURCE_BYTES):
            if entry["id"] == "two":
                raise OSError("simulated source unavailable")
            return body, "audio/x-mpegurl", 200
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            catalog_dir = root / "catalog"
            catalog_dir.mkdir()
            (catalog_dir / "live.json").write_text(json.dumps(catalog), encoding="utf-8")
            (root / "probe-report.json").write_text(json.dumps({"probes": [{"id": "one", "status": "ok"}]}), encoding="utf-8")
            config_path = root / "sources.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            with mock.patch.object(live, "fetch_source", side_effect=fetch):
                result = live.build(config_path, catalog_dir, root / "dist", do_probe=False)
            self.assertTrue((root / "dist/custom-live.m3u").exists())
            self.assertTrue((root / "dist/custom-live.txt").exists())
            report = json.loads((root / "dist/reports/custom-live-status.json").read_text())
        self.assertEqual(result["summary"]["playlist_channels_written"], 1)
        self.assertEqual(report["sources"][0]["fetch_status"], "ok")
        self.assertEqual(report["sources"][1]["fetch_status"], "failed")
        self.assertEqual(report["channels"][0]["group"], "央视")
        self.assertEqual(report["channels"][0]["channel_status"], "not-tested")
        self.assertEqual(report["channels"][0]["catalog_feed_reference"], "https://source.test/a.m3u")


if __name__ == "__main__":
    unittest.main()
