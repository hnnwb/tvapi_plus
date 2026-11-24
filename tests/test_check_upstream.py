import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from urllib.error import URLError

from scripts import check_upstream


def resources(*rows):
    return json.dumps({"resources": [dict(id=i, name=n, url=u) for i, n, u in rows]})


README = """
### 开源客户端

| 名称 | 说明 | Star |
| --- | --- | --- |
| [A](https://github.com/acme/a) | TVBox 分支 | 1.2k |
"""

CATALOG = {
    "online.json": [
        {"id": "zhuiju-site", "name": "Site", "url": "https://old.example/", "format": "web",
         "source": "u", "license": "l", "notes": "n"},
    ],
    "apps.json": [],
}


class UpstreamCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.catalog = root / "catalog"
        self.catalog.mkdir()
        for name, rows in CATALOG.items():
            (self.catalog / name).write_text(json.dumps(rows), encoding="utf-8")
        self.report = root / "report.json"
        self.fetched = {}
        self.previous = root / "prev.json"
        patcher = unittest.mock.patch.object(check_upstream, "CHECKED_AT", self.previous)
        self.addCleanup(patcher.stop)
        patcher.start()

    def tearDown(self):
        self.tmp.cleanup()

    def fetch(self, url):
        return self.fetched[url]

    def run_check(self, site_url="https://old.example/", site_name="Site", readme=README):
        self.fetched[check_upstream.SOURCES[0]["url"]] = resources(("site", site_name, site_url))
        self.fetched[check_upstream.SOURCES[1]["url"]] = readme
        with unittest.mock.patch.object(check_upstream, "probe_new"):
            return check_upstream.run(self.catalog, self.report, fetch_fn=self.fetch, now="2026-01-01T00:00:00+00:00")

    def row(self):
        return json.loads((self.catalog / "online.json").read_text(encoding="utf-8"))[0]

    def test_first_run_reports_everything_and_writes_snapshot(self):
        doc = self.run_check()
        # "site" is already in the catalog under that address, so it is not new to the page.
        self.assertEqual([row["id"] for row in doc["changed"]], [])
        self.assertEqual({row["id"] for row in doc["added"]}, {"app:https://github.com/acme/a"})
        self.assertEqual(doc["removed"], [])
        self.assertTrue(self.previous.exists())

    def test_unchanged_round_reports_nothing(self):
        self.run_check()
        doc = self.run_check()
        self.assertEqual((doc["added"], doc["changed"], doc["removed"]), ([], [], []))

    def test_repointed_link_is_followed_and_old_kept_as_fallback(self):
        self.run_check()
        doc = self.run_check(site_url="https://new.example/")
        self.assertEqual(self.row()["url"], "https://new.example/")
        self.assertEqual(self.row()["fallback_urls"], ["https://old.example/"])
        self.assertIn("kept as fallback", doc["changed"][0]["action"])

    def test_renamed_row_keeps_its_address(self):
        self.run_check()
        doc = self.run_check(site_name="Site Renamed")
        self.assertEqual(self.row()["name"], "Site Renamed")
        self.assertEqual(self.row()["url"], "https://old.example/")
        self.assertEqual(len(doc["changed"]), 1)

    def test_row_already_held_under_another_id_is_not_new(self):
        self.run_check()
        self.fetched[check_upstream.SOURCES[0]["url"]] = resources(("brand-new", "Site", "https://old.example/"))
        with unittest.mock.patch.object(check_upstream, "probe_new"):
            doc = check_upstream.run(self.catalog, self.report, fetch_fn=self.fetch)
        self.assertEqual(doc["added"], [])

    def test_removed_upstream_rows_are_reported_not_dropped(self):
        self.run_check()
        self.fetched[check_upstream.SOURCES[0]["url"]] = resources()
        with unittest.mock.patch.object(check_upstream, "probe_new"):
            doc = check_upstream.run(self.catalog, self.report, fetch_fn=self.fetch)
        self.assertEqual([row["id"] for row in doc["removed"]], ["site"])
        self.assertEqual(len(json.loads((self.catalog / "online.json").read_text(encoding="utf-8"))), 1)

    def test_fetch_failure_keeps_previous_snapshot_and_reports_error(self):
        self.run_check()
        before = self.previous.read_text(encoding="utf-8")

        def explode(url):
            raise URLError("offline")

        doc = check_upstream.run(self.catalog, self.report, fetch_fn=explode)
        self.assertEqual(len(doc["errors"]), 2)
        self.assertEqual(self.previous.read_text(encoding="utf-8"), before)
        self.assertEqual(doc["removed"], [])


if __name__ == "__main__":
    unittest.main()
