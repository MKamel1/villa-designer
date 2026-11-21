"""Lane R card builder: a card's quote is checked against the page text before it is written.

Held books: text comes from archpipe.knowledge_index.read (pdf page index; printed label recorded).
Web/PDF sources: text comes from a local file saved by the caller.

Matching is whitespace-insensitive and treats dashes and curly quotes as equal. The stored quote is the
SOURCE span itself (slice of the page text), changed only by: whitespace collapsed to single spaces, line-end
hyphenation joined, and the ligature code points fi/fl/ff/ffi/ffl expanded. Everything else (primes, degree signs,
en-dashes, curly quotes) is kept as in the source.
Value check: every number in a card's `value` must occur in its `quote`; otherwise the build lists the card.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from archpipe.contracts import SourceCard  # noqa: E402

OUT = ROOT / "knowledge" / "sources"
LIG = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "­": ""}
FOLD = str.maketrans({"–": "-", "—": "-", "−": "-", "’": "'", "‘": "'", "“": '"', "”": '"'})
VALUE_WARN: list = []


def lite(s: str) -> str:
    for a, b in LIG.items():
        s = s.replace(a, b)
    s = re.sub(r"(\w)-\n(\w)", r"\1\2", s)
    return re.sub(r"\s+", " ", s).strip()


def fold(s: str) -> str:
    return s.translate(FOLD)  # 1:1 character map, so indexes in fold(lite(t)) equal indexes in lite(t)


def locate(text: str, quote: str):
    """Return the source span of `quote` in `text` (exactly one occurrence), None if absent, 'AMBIGUOUS' if repeated."""
    t = lite(text)
    q = fold(lite(quote))
    ft = fold(t)
    i = ft.find(q)
    if i < 0:
        return None
    if ft.find(q, i + 1) >= 0:
        return "AMBIGUOUS"
    return t[i:i + len(q)]


def check_value(cid: str, value: str, quote: str, ctx: str = "") -> None:
    """Numbers in `value` must occur in the quote, or in the card's own id/locator/document/edition (clause and edition references)."""
    qd = re.sub(r"\s", "", fold(quote)).replace(",", ".")
    ctxn = set(re.findall(r"\d+(?:[.,]\d+)?", ctx.replace(",", ".")))
    miss = [n for n in re.findall(r"\d+(?:[.,]\d+)?", value) if n.replace(",", ".") not in qd and n.replace(",", ".") not in ctxn]
    if miss:
        VALUE_WARN.append((cid, miss)); print("VALUE?", cid, miss)


def held_pages(book: str):
    from archpipe import knowledge_index as k
    n = next(s["pages"] for s in k.stats() if s["id"] == book)
    for i in range(n):
        p = k.read(book, i, 1)[0]
        lab = p["label"]
        if not lab or book.startswith("sll"):  # no usable label basis (SLL): running-head number, e.g. "68 Chapter Two"
            m = re.match(r"(\d{1,3}) (?:Chapter|[A-Z])", lite(p["text"]))
            lab = f"{m.group(1)} (running head)" if m else ""
        yield p["pdf_page"], lab, p["text"]


_cache: dict = {}


def held_quote(book: str, quote: str, label: str | None = None):
    """Find the quote in a held book. Returns (printed_label, pdf_page, source span)."""
    if book not in _cache:
        _cache[book] = list(held_pages(book))
    hits = []
    for pdf, lab, text in _cache[book]:
        if label is not None and str(lab) != str(label):
            continue
        sp = locate(text, quote)
        if sp:
            hits.append((pdf, lab, sp))
    if len(hits) != 1 or hits[0][2] == "AMBIGUOUS":
        raise ValueError(f"{book}: quote on {len(hits)} pages {[(h[0], h[1]) for h in hits[:5]]} (need exactly 1): {quote[:80]!r}")
    pdf, lab, sp = hits[0]
    return lab, pdf, sp


def text_quote(textfile, quote: str):
    sp = locate(Path(textfile).read_text(encoding="utf-8", errors="ignore"), quote)
    if not sp or sp == "AMBIGUOUS":
        raise ValueError(f"{textfile}: quote not found (or repeated): {quote[:80]!r}")
    return sp


def write(filename: str, cards: list[SourceCard]) -> Path:
    ids = [c.id for c in cards]
    assert len(ids) == len(set(ids)), "duplicate ids"
    for c in cards:
        if c.quote:
            check_value(c.id, c.value, c.quote, " ".join([c.id, c.locator, c.document, c.edition]))
    p = OUT / filename
    p.write_text(json.dumps([asdict(c) for c in cards], indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


_pdf_cache: dict = {}


def _printed_guess(raw: str) -> str:
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip() and "O N L I N E" not in ln]
    for ln in lines[:4] + lines[-3:]:
        if re.fullmatch(r"\d{1,4}", ln):
            return ln
        m = re.fullmatch(r"[–-] ?(\d{1,4}) ?[–-]", ln)
        if m:
            return m.group(1)
    return "?"


def pdf_quote(pdf_path, quote: str, page_hint: int | None = None):
    """Find a quote in a local PDF (a web download). Returns (printed_guess, pdf_page_1based, source span)."""
    import pymupdf
    key = str(pdf_path)
    if key not in _pdf_cache:
        d = pymupdf.open(key)
        _pdf_cache[key] = [(i + 1, p.get_text()) for i, p in enumerate(d)]
    hits = []
    for i, t in _pdf_cache[key]:
        if page_hint is not None and i != page_hint:
            continue
        sp = locate(t, quote)
        if sp:
            hits.append((i, _printed_guess(t), sp))
    if len(hits) != 1 or hits[0][2] == "AMBIGUOUS":
        raise ValueError(f"{pdf_path}: quote on {len(hits)} pages {[(h[0], h[1]) for h in hits[:5]]}: {quote[:80]!r}")
    return hits[0][1], hits[0][0], hits[0][2]
