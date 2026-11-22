"""Every `sourced` quote in rules.json must appear on the cited page of the held book.

Guard against a fabricated or mis-transcribed citation (CLAUDE.md: never invent a figure). Skips
when the licensed PDF is not on this machine; the lane workstation holds them.
"""
import glob
import json
import os
import re
import unittest
from pathlib import Path

RULES = Path(__file__).resolve().parents[3] / "knowledge/landscape/rules/rules.json"
BOOKS = Path.home() / "ai-projects/archpipe-knowledge-data/drop_in/done"


def _norm(t: str) -> str:
    return re.sub(r"[\s\-­‐‑]+", "", t).lower()


def _on_page(quote: str, page) -> bool:
    """Contiguous match, else (the book's columns interleave line by line and break words) every
    number of the quote and 85 % of its words are on the page. That still catches a wrong figure
    or an invented sentence, which is what this guard is for."""
    full = page.get_text()
    page_n = _norm(full)
    if _norm(quote) in page_n:
        return True
    words = [_norm(w) for w in re.sub(r"[\u00ad\-]+ ?", "", quote).split()]
    words = [w for w in words if w]
    numbers = [w for w in words if any(ch.isdigit() for ch in w)]
    found = sum(1 for w in words if w in page_n)
    return all(n in page_n for n in numbers) and found >= 0.85 * len(words)


class SourceQuotes(unittest.TestCase):
    def test_quotes_are_on_the_cited_pdf_page(self):
        try:
            import pymupdf
        except ImportError:
            self.skipTest("pymupdf not installed")
        checked = 0
        docs = {}
        for s in json.loads(RULES.read_text(encoding="utf-8"))["sources"]:
            if s["status"] != "sourced" or not s.get("book"):
                continue
            hits = glob.glob(str(BOOKS / f"*[[]{s['book']}[]]*.pdf"))
            if not hits:
                continue
            doc = docs.setdefault(s["book"], pymupdf.open(hits[0]))
            pg = doc[s["pdf_page"]]
            self.assertTrue(_on_page(s["quote"], pg), f"{s['id']}: quote not found on pdf page {s['pdf_page']}")
            checked += 1
        if not checked:
            self.skipTest("no held PDFs on this machine")




class GuardFailsClosed(unittest.TestCase):
    def test_a_wrong_figure_is_caught(self):
        try:
            import pymupdf
        except ImportError:
            self.skipTest("pymupdf not installed")
        hits = glob.glob(str(BOOKS / "*[[]landscape-timesaver[]]*.pdf"))
        if not hits:
            self.skipTest("book not held here")
        page = pymupdf.open(hits[0])[251]
        good = "Risers for outdoor stairways should be a minimum of 115 mm (4.5 in) and a maximum of 150 mm (6 in)"
        self.assertTrue(_on_page(good, page))
        self.assertFalse(_on_page(good.replace("115", "125"), page))
        self.assertFalse(_on_page("Risers should never exceed any figure whatsoever", page))


def _web_ok(quote: str, text: str) -> bool:
    n = lambda t: re.sub(r"\s+", "", t).lower().replace("\u2019", "'").replace("\u2018", "'")
    return n(quote) in n(text)


class WebSources(unittest.TestCase):
    """Every web card carries a URL, a retrieval date and a text snapshot that contains its quote.

    The snapshot is the verbatim text fetched on the retrieval date, so the guard runs offline. Set
    LDK_LIVE=1 to re-fetch each URL and check the quote against today's page (the pages may change)."""
    cards = [s for s in json.loads(RULES.read_text(encoding="utf-8"))["sources"] if s.get("url")]

    def test_there_are_web_cards_and_each_has_the_fields(self):
        self.assertGreater(len(self.cards), 50)
        for s in self.cards:
            self.assertTrue(s["url"].startswith("https://"), s["id"])
            self.assertRegex(s["retrieved"], r"^\d{4}-\d{2}-\d{2}$", s["id"])
            self.assertEqual(s["status"], "sourced", s["id"])

    def test_quote_is_in_the_snapshot_and_the_snapshot_names_the_url(self):
        for s in self.cards:
            snap = (RULES.parent / s["snapshot"]).read_text(encoding="utf-8")
            self.assertIn(s["url"], snap.splitlines()[0], s["id"])
            self.assertTrue(_web_ok(s["quote"], snap), f"{s['id']}: quote not in its snapshot")

    def test_guard_fails_closed(self):
        s = self.cards[0]
        snap = (RULES.parent / s["snapshot"]).read_text(encoding="utf-8")
        self.assertTrue(_web_ok(s["quote"], snap))
        self.assertFalse(_web_ok(s["quote"] + " and then something never said", snap))
        digits = re.search(r"\d+", s["quote"])
        if digits:
            self.assertFalse(_web_ok(s["quote"].replace(digits.group(), str(int(digits.group()) + 7), 1), snap))

    @unittest.skipUnless(os.environ.get("LDK_LIVE"), "set LDK_LIVE=1 to re-fetch the live pages")
    def test_live_pages_still_say_it(self):
        import subprocess
        gone = []
        for s in self.cards:
            if s["url"].lower().endswith(".pdf"):
                continue
            html = subprocess.run(["curl", "-sL", "-m", "30", "-A", "Mozilla/5.0", s["url"]], capture_output=True).stdout.decode("utf-8", "replace")
            if not _web_ok(s["quote"], re.sub(r"<[^>]+>", "", html)):
                gone.append(s["id"])
        self.assertEqual(gone, [], "quotes no longer on the live page (page changed, or JS-rendered)")


if __name__ == "__main__":
    unittest.main()
