"""Every `sourced` quote in rules.json must appear on the cited page of the held book.

Guard against a fabricated or mis-transcribed citation (CLAUDE.md: never invent a figure). Skips
when the licensed PDF is not on this machine; the lane workstation holds them.
"""
import glob
import json
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
            if s["status"] != "sourced" or not s["book"]:
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


if __name__ == "__main__":
    unittest.main()


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
