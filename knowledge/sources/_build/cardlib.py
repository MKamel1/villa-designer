"""Lane R card builder: a card's quote is checked verbatim against the page text before it is written.

Held books: text comes from archpipe.knowledge_index.read (pdf page index; printed label recorded).
Web/PDF sources: text comes from a local file saved by the caller.
Comparison is whitespace- and ligature-insensitive (NFKC, hyphenated line breaks joined); the stored
quote is the normalised form of the text that was matched.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from archpipe.contracts import SourceCard  # noqa: E402

OUT = ROOT / "knowledge" / "sources"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("−", "-").replace("­", "")
    s = re.sub(r"(\w)-\n(\w)", r"\1\2", s)
    return re.sub(r"\s+", " ", s).strip()


def held_pages(book: str):
    from archpipe import knowledge_index as k
    n = next(s["pages"] for s in k.stats() if s["id"] == book)
    for i in range(n):
        p = k.read(book, i, 1)[0]
        yield p["pdf_page"], p["label"], norm(p["text"])


_cache: dict[str, list] = {}


def held_quote(book: str, quote: str, label: str | None = None):
    """Find the quote in a held book. Returns (printed_label, pdf_page, normalised quote)."""
    if book not in _cache:
        _cache[book] = list(held_pages(book))
    q = norm(quote)
    hits = [(pdf, lab) for pdf, lab, t in _cache[book] if q in t and (label is None or str(lab) == str(label))]
    if len(hits) != 1:
        raise ValueError(f"{book}: quote on {len(hits)} pages {hits[:5]} (need exactly 1): {q[:80]!r}")
    return hits[0][1], hits[0][0], q


def text_quote(textfile, quote: str):
    t = norm(Path(textfile).read_text(encoding="utf-8", errors="ignore"))
    q = norm(quote)
    if q not in t:
        raise ValueError(f"{textfile}: quote not found: {q[:80]!r}")
    return q


def write(filename: str, cards: list[SourceCard]) -> Path:
    ids = [c.id for c in cards]
    assert len(ids) == len(set(ids)), "duplicate ids"
    p = OUT / filename
    p.write_text(json.dumps([asdict(c) for c in cards], indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return p
