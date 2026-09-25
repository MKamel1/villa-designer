"""Source intake: only readable copies become 'held', matched by ISBN or title;
locked and unmatched files are reported, never filed."""
import json
import tempfile
import unittest
from pathlib import Path

import pymupdf

from archpipe import sources as src

LOREM = "Planning data for dwellings. " * 40


def pdf(path: Path, text: str, password: str | None = None) -> Path:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_textbox(pymupdf.Rect(40, 40, 560, 800), text, fontsize=9)
    kw = {}
    if password:
        kw = dict(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw=password, user_pw=password)
    doc.save(path, **kw)
    return path


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "inbox").mkdir()
        self.lib = {"sources": [
            {"id": "metric-handbook", "title": "Metric Handbook: Planning and Design Data",
             "isbn": "9780367511395", "status": "identified", "priority": 1, "cost_usd_approx": 90},
            {"id": "human-dimension", "title": "Human Dimension & Interior Space",
             "isbn": None, "status": "identified", "priority": 1, "cost_usd_approx": 45},
            {"id": "yourhome-brief", "title": "Preliminary Research", "status": "content_verified"}]}

    def test_readable_copy_is_matched_by_isbn_and_held(self):
        pdf(self.root / "inbox" / "download (3).pdf", "ISBN 978-0-367-51139-5\n" + LOREM)
        rep = src.intake(self.lib, self.root, log=lambda *a: None)
        self.assertEqual([h["id"] for h in rep["held"]], ["metric-handbook"])
        s = self.lib["sources"][0]
        self.assertEqual(s["status"], "held")                     # not content_verified: nobody read it yet
        self.assertTrue((self.root / "metric-handbook" / "download (3).pdf").is_file())
        self.assertEqual(len(s["held_files"][0]["sha256"]), 64)

    def test_title_match_when_no_isbn(self):
        pdf(self.root / "inbox" / "scan.pdf", "HUMAN DIMENSION & INTERIOR SPACE\n" + LOREM)
        rep = src.intake(self.lib, self.root, log=lambda *a: None)
        self.assertEqual([h["id"] for h in rep["held"]], ["human-dimension"])

    def test_locked_copy_is_reported_not_held(self):
        pdf(self.root / "inbox" / "neufert.pdf", LOREM, password="secret")
        rep = src.intake(self.lib, self.root, log=lambda *a: None)
        self.assertEqual(len(rep["locked"]), 1)
        self.assertFalse(rep["held"])
        self.assertTrue((self.root / "inbox" / "neufert.pdf").is_file())   # left where it was

    def test_unmatched_copy_stays_in_inbox(self):
        pdf(self.root / "inbox" / "mystery.pdf", LOREM)
        rep = src.intake(self.lib, self.root, log=lambda *a: None)
        self.assertEqual([u["file"] for u in rep["unmatched"]], ["mystery.pdf"])
        self.assertTrue(all(s["status"] != "held" for s in self.lib["sources"]))

    def test_purchase_list_excludes_held_and_web_sources(self):
        self.lib["sources"][0]["status"] = "held"
        ids = [s["id"] for s in src.purchase_rows(self.lib)]
        self.assertEqual(ids, ["human-dimension"])

    def test_save_keeps_crlf_and_ascii(self):
        p = self.root / "lib.json"
        p.write_bytes(b'{\r\n  "a": 1\r\n}\r\n')
        src.save({"a": "é"}, p)
        raw = p.read_bytes()
        self.assertIn(b"\r\n", raw)
        self.assertIn(b"\\u00e9", raw)
        self.assertEqual(json.loads(raw)["a"], "é")


class RegistryTests(unittest.TestCase):
    def test_real_registry_ids_unique_and_tiers_valid(self):
        lib = src.load()
        ids = [s["id"] for s in lib["sources"]]
        self.assertEqual(len(ids), len(set(ids)))
        for s in src.purchase_rows(lib):
            self.assertIn(s["priority"], (1, 2, 3))
            self.assertTrue(s["free"] or s["cost_usd_approx"] > 0, s["id"])


if __name__ == "__main__":
    unittest.main()
