"""Searchable index over the held books and standards (the "dictionary" layer).

The originals are licensed, so the index lives in the private source store
(SOURCES_ROOT/_index/knowledge.sqlite), never in the repository. It holds:

    books    one row per held file: id, title, edition, pages, label basis
    pages    every page's text with BOTH references a card needs:
             pdf_page (0-based, what a viewer opens) and label (the PRINTED
             page number, what a citation states). figure_heavy marks pages
             that are mostly drawing: much of the dimensional data (Neufert,
             Metric Handbook, Time-Saver) is inside drawings, where text
             search cannot see it. A hit on such a page means "read the
             image" (page_image), and no hit never means "no source".
    toc      the book's outline, or its printed contents pages when the
             outline is missing or thin (Neufert has none; the IES Handbook
             outline has 4 entries)
    terms    the back-of-book index, term -> printed pages -> pdf pages
    pages_fts  SQLite FTS5 (BM25) over page text, for exact terms and numbers

An EPUB has no printed pages: its "pages" come from reflowing and change
with layout settings, so EPUB hits are cited by section, never by page.

Semantic search ("what does the literature say about ...") is the second
layer: the client's agent-rag-research system on the workstation, as its own
corpus. This module is the fast, exact, offline layer.
"""
from __future__ import annotations

import collections
import json
import re
import sqlite3
from pathlib import Path

from archpipe import sources as src

DB = src.SOURCES_ROOT / "_index" / "knowledge.sqlite"
PAGE_IMAGES = src.SOURCES_ROOT / "_index" / "page-images"
FIGURE_NOTE = "page is mostly drawing: text search may miss its dimensions; read the page image"

DDL = """
create table if not exists books(id text primary key, title text, edition text, file text, kind text,
  pages integer, label_basis text, sha256 text);
create table if not exists pages(book text, pdf_page integer, label text, section text, chars integer,
  image_ratio real, figure_heavy integer, text text, primary key(book, pdf_page));
create table if not exists toc(book text, level integer, title text, pdf_page integer, label text, basis text);
create table if not exists terms(book text, term text, norm text, refs text, pdf_pages text);
create virtual table if not exists pages_fts using fts5(text, book unindexed, pdf_page unindexed,
  tokenize='porter unicode61');
create virtual table if not exists terms_fts using fts5(term, book unindexed, rowid_ref unindexed,
  tokenize='porter unicode61');
"""


def connect(db: Path = DB) -> sqlite3.Connection:
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    con.executescript(DDL)
    return con


# ------------------------------------------------------------------ page labels

_NUM = re.compile(r"^\s*(\d{1,4})\s*$")
# printed page tokens: "123", "15-11", "14.12", "5.45" (chapter-page numbering)
_TOKEN = re.compile(r"(?<![\w.,])(\d{1,2}[.\-–]\d{1,3}|\d{1,4})(?![\w,]|\.\d)")


def _edge_tokens(text: str) -> list[str]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    out = []
    for l in lines[:3] + lines[-3:]:
        if len(l) <= 80:
            out += [tok.replace("–", "-") for tok in _TOKEN.findall(l)]
    return out


def _edge_numbers(text: str) -> list[int]:
    return [int(t) for t in _edge_tokens(text) if t.isdigit()]


_HEAD = re.compile(r"^(\d{1,2}[.\-–]\d{1,3})\s+\D|\D\s+(\d{1,2}[.\-–]\d{1,3})$")


def _running_head(text: str) -> str:
    """A chapter-page number ('22-4 Houses and flats', 'Auditoria 15-11') on the first or
    last line; section numbers further down ('22.3 Typical ...') are ignored."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for l in lines[:1] + lines[-1:]:
        m = _HEAD.search(l) if len(l) <= 80 else None
        if m:
            return (m.group(1) or m.group(2)).replace("–", "-")
    toks = [x for x in _edge_tokens(text) if not x.isdigit()]
    return toks[0] if len(set(toks)) == 1 else ""


def _decode_label(label: str) -> str:
    """Some PDFs store labels as UTF-16 hex ('<FEFF0034...>')."""
    m = re.fullmatch(r"<FEFF([0-9A-Fa-f]+)>(.*)", label or "")
    if m:
        h = m.group(1)
        try:
            return bytes.fromhex(h).decode("utf-16-be") + m.group(2)
        except ValueError:
            return label
    return label or ""


def _agreement(labels: list[str], texts: list[str], sample: int = 60) -> float:
    idx = [i for i, l in enumerate(labels) if l]
    if not idx:
        return 0.0
    step = max(1, len(idx) // sample)
    checked = agree = 0
    for i in idx[::step]:
        toks = _edge_tokens(texts[i])
        if not toks:
            continue
        checked += 1
        agree += labels[i].replace("–", "-") in toks
    return agree / checked if checked >= 5 else 0.0


def page_labels(doc, texts: list[str]) -> tuple[list[str], str]:
    """Printed page per PDF page: the best of three candidates, scored by agreement with the
    numbers actually printed at the top or bottom of the pages. PDF labels can be plain
    sequence numbers (Building Construction Illustrated prints '5.45' where the label says 191)."""
    n = len(texts)
    cands = {}
    pdf = [_decode_label(doc[i].get_label()) for i in range(n)]
    if sum(1 for l in pdf if l) > 0.5 * n:
        cands["pdf page labels"] = pdf
    offsets = collections.Counter()
    for i, t in enumerate(texts):
        for v in _edge_numbers(t):
            if 0 < v <= n + 50:
                offsets[v - i] += 1
    if offsets:
        off, support = offsets.most_common(1)[0]
        if support >= 5:
            cands[f"header/footer offset {off:+d}"] = [str(i + off) if i + off > 0 else "" for i in range(n)]
    chap = [_running_head(t) for t in texts]     # chapter-page tokens read from each page
    if sum(1 for c in chap if c) > 0.3 * n:
        cands["printed chapter-page numbers"] = chap
    if not cands:
        return [""] * n, "none"
    scored = sorted(((round(_agreement(v, texts), 2), k) for k, v in cands.items()), reverse=True)
    best_score, best = scored[0]
    labels = cands[best]
    if best_score < 0.7:
        return labels, f"UNRELIABLE: {best} agrees {best_score:.0%} with printed numbers; verify printed page from the image"
    return labels, f"{best} (agrees {best_score:.0%} with printed numbers)"


# ------------------------------------------------------------------ contents and index

_CONTENTS_LINE = re.compile(r"^(?P<title>[A-Za-z][^\n]{2,90}?)[\s.·…]{1,}(?P<page>\d{1,4})\s*$")


def printed_contents(texts: list[str], labels: list[str]) -> list[dict]:
    """Parse 'Title .... 123' lines from contents pages in the first 30 pages."""
    out = []
    for i, t in enumerate(texts[:30]):
        if "contents" not in t.lower()[:400] and not out:
            continue
        lines = [l.strip() for l in t.splitlines() if l.strip()]
        hits = []
        for j, l in enumerate(lines):
            m = _CONTENTS_LINE.match(l)
            if m:
                hits.append((m.group("title").strip(" ."), m.group("page")))
            elif _NUM.match(l) and j > 0 and not _NUM.match(lines[j - 1]) and len(lines[j - 1]) > 3:
                hits.append((lines[j - 1].strip(" ."), l.strip()))    # title and page on separate lines
        if len(hits) < 3 and out:
            break
        for title, page in hits:
            pdf = next((k for k, l in enumerate(labels) if l == page), None)
            out.append({"level": 1, "title": title, "label": page, "pdf_page": pdf, "basis": "printed contents"})
    return out


# "Term 12, 45-7" and "Main: sub one 19, sub two 74" (several entries on one line, as in
# Neufert's index). Each (words, pages) run becomes one entry under the current main term.
_PAIR = re.compile(r"(?P<words>[A-Za-z][^\d:;]{0,80}?)\s*,?\s*(?P<pages>\d{1,4}(?:\s*[-–—]\s*\d{1,4})?"
                   r"(?:\(\d+\))?(?:\s*,\s*\d{1,4}(?:\s*[-–—]\s*\d{1,4})?(?:\(\d+\))?)*)")


def back_index(texts: list[str], labels: list[str]) -> list[dict]:
    """Term -> printed pages from the back-of-book index (last 20 % of the book)."""
    n = len(texts)
    start = next((i for i in range(int(n * 0.8), n) if re.match(r"\s*(\d+\s*)?index", texts[i][:200], re.I)
                  or re.search(r"^\s*index\s*$", texts[i][:300], re.I | re.M)), None)
    if start is None:
        return []
    label_to_pdf = {l: k for k, l in enumerate(labels) if l}
    out, main = [], ""
    for t in texts[start:]:
        for line in t.splitlines():
            line = line.strip()
            if not line or line.lower() == "index" or _NUM.match(line):
                continue
            if ":" in line[:60]:
                main, line = line.split(":", 1)[0].strip(), line.split(":", 1)[1]
            pairs = list(_PAIR.finditer(line))
            if not pairs:
                if not any(c.isdigit() for c in line) and len(line) < 60 and line[:1].isupper():
                    main = line.rstrip(",")
                continue
            for m in pairs:
                words = m.group("words").strip(" ,")
                if not words:
                    continue
                term = words if words[:1].isupper() or not main else f"{main}, {words}"
                if words[:1].isupper() and ":" not in line:
                    main = words
                pages = re.findall(r"\d{1,4}", re.sub(r"\(\d+\)", "", m.group("pages")))
                out.append({"term": term, "refs": m.group("pages").strip(),
                            "pdf_pages": [label_to_pdf[p] for p in pages if p in label_to_pdf]})
    return out


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


# ------------------------------------------------------------------ build

def build(lib: dict | None = None, db: Path = DB, only: list[str] | None = None, log=print) -> dict:
    """(Re)index every held PDF/EPUB in the registry. Idempotent per book (by sha256)."""
    import pymupdf
    lib = lib or src.load()
    con = connect(db)
    report = {}
    for s in lib["sources"]:
        for h in s.get("held_files", []):
            path = src.SOURCES_ROOT / h["file"]
            if path.suffix.lower() not in (".pdf", ".epub") or (only and s["id"] not in only):
                continue
            key = s["id"] if len(s.get("held_files", [])) == 1 else f"{s['id']}#{path.stem}"
            row = con.execute("select sha256 from books where id=?", (key,)).fetchone()
            if row and row["sha256"] == h["sha256"]:
                continue
            for t in ("pages", "toc", "terms"):
                con.execute(f"delete from {t} where book=?", (key,))
            con.execute("delete from pages_fts where book=?", (key,))
            con.execute("delete from terms_fts where book=?", (key,))
            doc = pymupdf.open(path)
            kind = path.suffix.lower()[1:]
            texts = [doc[i].get_text() for i in range(doc.page_count)]
            if kind == "epub":
                labels, basis = [""] * len(texts), "epub: cite by section, not page"
            else:
                labels, basis = page_labels(doc, texts)
            outline = doc.get_toc()
            toc = [{"level": lv, "title": ti.replace("\x00", "").strip(), "pdf_page": p - 1, "label": labels[p - 1] if 0 < p <= len(labels) else "",
                    "basis": "pdf outline"} for lv, ti, p in outline]
            if len(toc) < 8 and kind == "pdf":
                toc += printed_contents(texts, labels)
            # section for every page = deepest outline entry at or before it
            marks = sorted((e["pdf_page"], e["level"], e["title"]) for e in toc if e["pdf_page"] is not None)
            section, sec_at = "", []
            j = 0
            stack = {}
            for i in range(len(texts)):
                while j < len(marks) and marks[j][0] <= i:
                    stack = {k: v for k, v in stack.items() if k < marks[j][1]}
                    stack[marks[j][1]] = marks[j][2]
                    j += 1
                sec_at.append(" > ".join(stack[k] for k in sorted(stack)))
            for i, t in enumerate(texts):
                page = doc[i]
                area = abs(page.rect) or 1.0
                img = sum(abs(pymupdf.Rect(b["bbox"]) & page.rect) for b in page.get_image_info())
                ratio = min(1.0, img / area)
                if ratio > 0.95:
                    # a scanned page: the whole page is one image with an OCR text layer, so
                    # coverage says nothing; little text on it means it is mostly drawing
                    heavy = len(t) < 1500
                else:
                    heavy = ratio > 0.45 or (len(t) < 900 and ratio > 0.15)
                    if not heavy and len(t) < 1500 and kind == "pdf":
                        heavy = len(page.get_cdrawings()) > 150      # vector drawings
                con.execute("insert into pages values(?,?,?,?,?,?,?,?)",
                            (key, i, labels[i], sec_at[i], len(t), round(ratio, 3), int(heavy), t))
                con.execute("insert into pages_fts(text, book, pdf_page) values(?,?,?)", (t, key, i))
            for e in toc:
                con.execute("insert into toc values(?,?,?,?,?,?)",
                            (key, e["level"], e["title"], e["pdf_page"], e["label"], e["basis"]))
            terms = back_index(texts, labels) if kind == "pdf" else []
            for e in terms:
                cur = con.execute("insert into terms values(?,?,?,?,?)",
                                  (key, e["term"], _norm(e["term"]), e["refs"], json.dumps(e["pdf_pages"])))
                con.execute("insert into terms_fts(term, book, rowid_ref) values(?,?,?)", (e["term"], key, cur.lastrowid))
            con.execute("insert or replace into books values(?,?,?,?,?,?,?,?)",
                        (key, s["title"], s.get("edition"), h["file"], kind, len(texts), basis, h["sha256"]))
            con.commit()
            report[key] = {"pages": len(texts), "label_basis": basis, "toc": len(toc), "terms": len(terms),
                           "figure_heavy": sum(1 for i in range(len(texts)) if con.execute(
                               "select figure_heavy from pages where book=? and pdf_page=?", (key, i)).fetchone()[0])}
            log(f"  {key:34s} {len(texts):5d}p toc={len(toc):4d} terms={len(terms):5d} "
                f"figures={report[key]['figure_heavy']:4d}  labels: {basis}")
            doc.close()
    con.close()
    return report


# ------------------------------------------------------------------ query

_STOP = {"the", "a", "an", "of", "for", "to", "in", "and", "or", "on", "at", "by", "with", "is", "be", "what"}


def _fts_query(q: str, mode: str = "all") -> str:
    """Plain words -> an FTS5 query. 'all': every word must appear. 'any': pages are ranked
    by how many of the words they hold (BM25), for longer questions where no page has all."""
    words = [w for w in re.findall(r"[\w.]+", q) if w.lower() not in _STOP or mode == "all"]
    return (" " if mode == "all" else " OR ").join(f'"{w}"' for w in words)


def search(query: str, book: str | None = None, limit: int = 10, db: Path = DB) -> list[dict]:
    """Best pages for a query (BM25), each with the printed page to cite and a figure warning.

    Pages holding every word come first (match 'all'); if there are fewer than `limit`,
    pages holding some of the words follow (match 'partial'), so a long question never
    returns nothing just because no single page uses all of its words."""
    con = connect(db)
    seen, rows = set(), []
    for mode in ("all", "any"):
        if len(rows) >= limit:
            break
        fq = _fts_query(query, mode)
        if not fq or (mode == "any" and len(fq.split(" OR ")) < 2):
            continue
        sql = ("select f.book, f.pdf_page, bm25(pages_fts) score, snippet(pages_fts, 0, '[', ']', ' ... ', 18) snip "
               "from pages_fts f where pages_fts match ?")
        args = [fq]
        if book:
            sql += " and f.book = ?"
            args.append(book)
        sql += " order by score limit ?"
        args.append(limit * 4 if mode == "any" else limit)
        words = [w.lower() for w in re.findall(r"[\w.]+", query) if w.lower() not in _STOP]
        need = max(2, (len(words) + 1) // 2)
        for r in con.execute(sql, args).fetchall():
            if mode == "any":
                # a page matching one word of a long question is not an answer: require at
                # least half the words (and never fewer than two)
                text = con.execute("select lower(text) from pages where book=? and pdf_page=?",
                                   (r["book"], r["pdf_page"])).fetchone()[0]
                if sum(1 for w in set(words) if w in text) < need:
                    continue
            if (r["book"], r["pdf_page"]) not in seen:
                seen.add((r["book"], r["pdf_page"]))
                rows.append((mode, r))
    out = []
    for mode, r in rows[:limit]:
        p = con.execute("select label, section, figure_heavy from pages where book=? and pdf_page=?",
                        (r["book"], r["pdf_page"])).fetchone()
        b = con.execute("select title, edition, kind, label_basis from books where id=?", (r["book"],)).fetchone()
        unreliable = b["label_basis"].startswith("UNRELIABLE")
        out.append({"book": r["book"], "title": b["title"], "edition": b["edition"], "pdf_page": r["pdf_page"],
                    "printed_page": p["label"] or None, "section": p["section"],
                    "match": "all" if mode == "all" else "partial",
                    "cite": (f"section '{p['section']}'" if b["kind"] == "epub" else
                             f"p. {p['label']}" + (" (verify printed page)" if unreliable else "") if p["label"]
                             else f"PDF page {r['pdf_page'] + 1} (no printed number)"),
                    "snippet": r["snip"], "figure_heavy": bool(p["figure_heavy"]),
                    "note": FIGURE_NOTE if p["figure_heavy"] else ""})
    con.close()
    return out


def lookup_term(term: str, limit: int = 20, db: Path = DB) -> list[dict]:
    """The dictionary: back-of-book index entries across every book."""
    con = connect(db)
    rows = con.execute("select t.book, t.term, t.refs, t.pdf_pages from terms_fts f join terms t on t.rowid = f.rowid_ref "
                       "where terms_fts match ? order by bm25(terms_fts) limit ?", (_fts_query(term), limit)).fetchall()
    con.close()
    return [{"book": r["book"], "term": r["term"], "printed_pages": r["refs"], "pdf_pages": json.loads(r["pdf_pages"])}
            for r in rows]


def toc(book: str, db: Path = DB) -> list[dict]:
    con = connect(db)
    rows = [dict(r) for r in con.execute("select level, title, label, pdf_page, basis from toc where book=?", (book,))]
    con.close()
    return rows


def read(book: str, pdf_page: int, count: int = 1, db: Path = DB) -> list[dict]:
    con = connect(db)
    rows = [dict(r) for r in con.execute(
        "select pdf_page, label, section, figure_heavy, text from pages where book=? and pdf_page between ? and ? "
        "order by pdf_page", (book, pdf_page, pdf_page + count - 1))]
    con.close()
    return rows


def page_image(book: str, pdf_page: int, dpi: int = 110, db: Path = DB) -> Path:
    """Render one page to PNG (private store) so its drawings can be read."""
    import pymupdf
    con = connect(db)
    f = con.execute("select file from books where id=?", (book,)).fetchone()["file"]
    con.close()
    out = PAGE_IMAGES / f"{book}-{pdf_page:04d}.png"
    if not out.is_file():
        out.parent.mkdir(parents=True, exist_ok=True)
        with pymupdf.open(src.SOURCES_ROOT / f) as doc:
            doc[pdf_page].get_pixmap(dpi=dpi).save(out)
    return out


def label_agreement(book: str, sample: int = 40, db: Path = DB) -> dict:
    """How often the stored printed page equals a number printed at the page's top or bottom.
    A PDF's own page labels can be plain sequence numbers; this catches that."""
    con = connect(db)
    rows = con.execute("select pdf_page, label, text from pages where book=? and label != '' order by pdf_page",
                       (book,)).fetchall()
    con.close()
    if not rows:
        return {"book": book, "checked": 0, "agree": 0, "ratio": None}
    step = max(1, len(rows) // sample)
    picked = rows[::step][:sample]
    with_numbers = [r for r in picked if _edge_tokens(r["text"])]
    agree = sum(1 for r in with_numbers if r["label"] in _edge_tokens(r["text"]))
    return {"book": book, "checked": len(with_numbers), "agree": agree,
            "ratio": round(agree / len(with_numbers), 2) if with_numbers else None}


def stats(db: Path = DB) -> list[dict]:
    con = connect(db)
    rows = [dict(r) for r in con.execute(
        "select b.id, b.pages, b.label_basis, (select count(*) from toc t where t.book=b.id) toc, "
        "(select count(*) from terms t where t.book=b.id) terms, "
        "(select sum(figure_heavy) from pages p where p.book=b.id) figure_pages from books b order by b.id")]
    con.close()
    return rows
