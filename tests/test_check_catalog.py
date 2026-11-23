import base64
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_catalog


def entry(format_name="web"):
    return {"id": "web-site", "name": "Web site", "url": "https://example.test/",
            "format": format_name, "source": "https://source.test",
            "license": "Reviewed upstream terms", "notes": "Test fixture"}


class LandingPageValidationTests(unittest.TestCase):
    def check(self, body, content_type, format_name="web"):
        with patch.object(check_catalog, "fetch_bounded", return_value=(body, content_type, 200)):
            return check_catalog.validate_remote("online", entry(format_name))

    def test_accepts_document_markup(self):
        self.assertEqual(self.check(b"\n<!doctype html><html></html>", "text/html"), "ok")
        self.assertEqual(self.check(b"<html><body>x</body></html>", "application/xhtml+xml"), "ok")

    def test_rejects_gateway_page_served_as_html(self):
        with self.assertRaises(ValueError) as caught:
            self.check(b"<title>502 Bad Gateway</title>", "text/html")
        self.assertIn("gateway or interstitial page", str(caught.exception))

    def test_still_rejects_non_html_content_type(self):
        with self.assertRaises(ValueError) as caught:
            self.check(b"\x89PNG", "image/png")
        self.assertIn("expected an HTML landing page", str(caught.exception))

    def test_non_web_formats_keep_size_only_contract(self):
        self.assertEqual(self.check(b"anything", "text/plain", "documentation"), "ok")


def rated(**overrides):
    base = {"average": 4.0, "scores": {"more": 4, "speed": 5, "clean": 3, "stable": 4, "ease": 4},
            "status": "recommended", "checked_at": "2026-06-06"}
    base.update(overrides)
    return base


class RatingValidationTests(unittest.TestCase):
    def errors_for(self, rating):
        errors: list[str] = []
        check_catalog.validate_rating(rating, errors, "where")
        return errors

    def test_accepts_upstream_assessment(self):
        self.assertEqual(self.errors_for(rated()), [])

    def test_accepts_fractional_dimension_when_average_matches(self):
        scores = {"more": 4.5, "speed": 4, "clean": 5, "stable": 4.8, "ease": 3.8}
        self.assertEqual(self.errors_for(rated(average=4.42, scores=scores)), [])

    def test_rejects_average_that_does_not_match_dimensions(self):
        errors = self.errors_for(rated(average=5))
        self.assertTrue(any("mean of scores" in error for error in errors), errors)

    def test_rejects_out_of_range_and_missing_dimensions(self):
        errors = self.errors_for(rated(average=5, scores={"more": 6, "speed": 5, "clean": 3, "stable": 4}))
        self.assertTrue(any("exactly" in error for error in errors), errors)
        errors = self.errors_for(rated(average=5, scores={"more": 6, "speed": 5, "clean": 3, "stable": 5, "ease": 6}))
        self.assertTrue(any("1 to 5" in error for error in errors), errors)

    def test_rejects_bad_status_and_date(self):
        errors = self.errors_for(rated(status=" ", checked_at="06/06/2026"))
        self.assertTrue(any("rating.status" in error for error in errors), errors)
        self.assertTrue(any("rating.checked_at" in error for error in errors), errors)

    def test_rating_is_rejected_when_it_is_not_an_object(self):
        self.assertEqual(self.errors_for([4, 4, 4]), ["where: rating must be an object"])


if __name__ == "__main__":
    unittest.main()


class ConfigBodyUnwrapping(unittest.TestCase):
    """Upstream hosts disguise configs; the probe must read through it, not score a failure."""

    def test_image_prefix_is_skipped(self):
        body = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b'{"sites": [{"key": "a"}]}'
        self.assertEqual(len(check_catalog.tvbox_json_document(body)["sites"]), 1)

    def test_bmp_prefix_is_skipped_for_multi(self):
        body = b"BM\x36\x00\x00\x00" + b'{"urls": [{"url": "http://x/y"}]}'
        self.assertEqual(check_catalog.tvbox_json_document(body)["urls"][0]["url"], "http://x/y")

    def test_base64_body_is_decoded(self):
        body = base64.b64encode(b'{"lives": []}')
        self.assertEqual(check_catalog.tvbox_json_document(body), {"lives": []})

    def test_binary_without_document_still_fails(self):
        with self.assertRaises(ValueError):
            check_catalog.tvbox_json_document(b"\x00\x01binary")


class ConfigBodyShapes(unittest.TestCase):
    """Shapes real config hosts serve: plain, commented, comment-and-trailing-comma, appended HTML."""

    def test_plain_document(self):
        self.assertEqual(check_catalog.tvbox_json_document(b'{"sites": []}'), {"sites": []})

    def test_line_comments_and_trailing_commas(self):
        body = b'{\n  "sites": [\n    {"key": "a"},  // note\n  ],\n}\n//////////\n'
        self.assertEqual(check_catalog.tvbox_json_document(body)["sites"][0]["key"], "a")

    def test_html_appended_after_document(self):
        body = ('{"urls": [{"url": "http://x/y"}]}\n<div style="text-align:center">x</div>').encode()
        self.assertEqual(check_catalog.tvbox_json_document(body)["urls"][0]["url"], "http://x/y")

    def test_utf8_bom_and_chinese_text(self):
        body = ('\ufeff{"urls": [{"name": "老李📚在线", "url": "http://x/y"}]}').encode("utf-8")
        self.assertEqual(check_catalog.tvbox_json_document(body)["urls"][0]["name"], "老李📚在线")


class ConfigBodyNotAConfig(unittest.TestCase):
    def test_html_landing_page_is_named(self):
        with self.assertRaisesRegex(ValueError, "HTML page instead of a configuration"):
            check_catalog.tvbox_json_document(b"<!DOCTYPE html><html><body>x</body></html>")
