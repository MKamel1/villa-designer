---
name: knowledge-search
description: Find, read and cite passages in the held books and standards (Neufert, Metric Handbook, Time-Saver, Mitton, NKBA, IES Handbook, SLL, Lechner, Ching, Allen & Iano, UK Approved Documents, ADA...). Use before stating any dimension, target or design rule, and whenever a claim needs a source.
---

Read [the decision](../../../docs/decisions/ADR-0018-knowledge-index.md).

**Order of search**
1. Dictionary: `python scripts/knowledge.py term "wardrobe"` (MCP
   `lookup_book_term`). These are the books' own index terms, pointing to
   printed pages.
2. Full text: `python scripts/knowledge.py search "hall landing width"`
   (MCP `search_books`). `match: all` hits come before `partial`.
3. By meaning, when the wording differs: the client's RAG corpus
   `archpipe_books` on the workstation (`semantic_search`).
4. Read before citing: `knowledge.py read <book> <pdf_page>`, or MCP
   `book_page`. If the hit is marked FIG, read the page image
   (`knowledge.py image <book> <pdf_page>`): the value may be in a drawing.

**Citing**
- Cite the edition in the registry, confirmed from the copyright page, and
  the PRINTED page (`cite` field). Never cite a PDF page index as a page.
- If the book's numbering is marked UNRELIABLE, read the printed number off
  the page image first.
- For the EPUB (Lechner), cite the section.
- Write an evidence card: locator, unit, value, conditions, exceptions. A
  numerical rule needs `original_page_checked` and a regression test before
  it can gate approval.

**Traps**
- No hit is not "no rule". Try the dictionary, synonyms, and pages marked FIG.
- Held editions differ from the purchase list. Neufert held is 1980, so its
  dimensions are 1980 practice; check them against Metric Handbook 2022 and
  Mitton 2022 before using them.
- UK and US sources can disagree. Record both and explain applicability;
  don't simply take the larger value.
