# ADR-0018: Making the held books searchable

**Status:** accepted, 2026-09-24.

## Context

The AI is the only design expert, so it must find the right passage in
roughly 16,000 pages of books and standards, read it, and cite it. The
content is too large to read in full for every question. The client already
runs a local RAG system (`agent-rag-research`: MinerU parsing, page-anchored
chunks, dense + sparse retrieval, reranker, MCP) on the workstation.

## Decision: three layers, used in this order

1. **Dictionary.** A back-of-book index for every book, merged:
   `lookup_book_term`. Expert-curated terms point to printed pages. There
   are 22,000+ terms today; IES alone has 7,388.
2. **Local full text.** `archpipe.knowledge_index`, SQLite FTS5/BM25, on
   the laptop, offline, rebuilt in about 90 s. It is best for exact terms
   and numbers ("hall or landing 900"). Each page records:
   - the 0-based PDF page;
   - the **printed page** to cite;
   - its section (from the outline, or the printed contents);
   - whether it is **mostly drawing**.

   Tools: `scripts/knowledge.py` and MCP `search_books`, `book_page`.
3. **Search by meaning.** The client's `agent-rag-research`, as a separate
   corpus (`~/ai-projects/archpipe-knowledge-data`, collection
   `archpipe_books`, on the shared GPU lock). Use it for questions phrased
   differently from the books. It also OCRs the one scanned book
   (Analysing Architecture). It does not replace layer 2, which is better
   at exact values.

Every answer then goes: read the page (and the page image if it is a
drawing), then write an evidence card citing the printed page, then add a
regression test.

## Rules learned while building it

- **Filenames lie; the copyright page decides.** The file named "Neufert
  6th ed. 2023" is the 2nd International English Edition of 1980. "Lighting
  Design Basics 3rd ed." is the 1st edition (2004). Each held source's
  edition is confirmed from its own copyright page before it can be cited
  (37 confirmed).
- **Printed page numbers are chosen by evidence.** Three candidates are
  scored against the numbers actually printed at the page edges: the PDF's
  own labels, a constant offset, and chapter-page tokens such as 5.45,
  15-11 or 14.12. Building Construction Illustrated's PDF labels are plain
  sequence numbers (label 191 on printed page 5.45). A book below 70 %
  agreement is marked UNRELIABLE and each hit says "verify printed page".
  Currently flagged: Acoustics, Landscape Time-Saver, NKBA 2nd, Problem
  Seeking and Lighting Design Basics.
- **An EPUB is cited by section, never by page.** Its pages come from
  reflowing.
- **No hit never means no rule.** Much of the dimensional data (Neufert,
  Metric Handbook, Time-Saver) is inside drawings. Hits on such pages carry
  `figure_heavy`; read `book_page(image=True)`.
- **Longer questions fall back to partial matches, but not below half the
  words.** Requiring every word returned nothing for "overheating criteria
  operative temperature", although Lechner covers it. Letting any single
  word count made nonsense return a page; the negative test caught that.

## Verification

`tests/test_knowledge_index.py` checks:
- 10 known answers, read by hand from the originals, come back in the top 5
  with the right printed page or EPUB section;
- nonsense returns nothing;
- the EPUB is cited by section;
- the dictionary resolves terms;
- unreliable numbering is labelled;
- chapter-page tokens and hex-encoded labels are handled.

It skips on machines where the private index is not built.

## Rejected

- **Embedding everything and dropping keyword search.** Dense retrieval is
  weak on exact numbers and clause wording, which are what a rule needs.
- **Copying book text into the repository.** Licensed text lives only in
  the private store (`~/archpipe-sources/_index`).
- **Trusting a PDF's page labels without checking them.**
