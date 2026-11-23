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


if __name__ == "__main__":
    unittest.main()
