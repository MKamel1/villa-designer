"""Search the held books and standards (the private knowledge index).

    python scripts/knowledge.py build                      # (re)index held files; unchanged files are skipped
    python scripts/knowledge.py search "stair headroom" [--book uk-ad-k] [--limit 10]
    python scripts/knowledge.py term "kitchens"            # the dictionary: back-of-book index entries
    python scripts/knowledge.py toc neufert
    python scripts/knowledge.py read neufert 72 [--count 2] # text of PDF page 72 (0-based)
    python scripts/knowledge.py image neufert 72            # render the page (drawings) to PNG
    python scripts/knowledge.py stats

Workflow: dictionary or search -> table of contents -> read the pages (and the
page image where the hit is marked FIG) -> cite the PRINTED page in an evidence
card. A search with no hit never means "no rule": the value may be in a drawing.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from archpipe import knowledge_index as k  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=["build", "search", "term", "toc", "read", "image", "stats"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--book")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--count", type=int, default=1)
    a = ap.parse_args(argv)
    if a.cmd == "build":
        k.build()
        return 0
    if a.cmd == "search":
        for h in k.search(" ".join(a.args), book=a.book, limit=a.limit):
            print(f"  {h['book']:30s} {h['cite']:28s} {'FIG ' if h['figure_heavy'] else ''}"
                  f"{' '.join(h['snippet'].split())[:160]}")
        return 0
    if a.cmd == "term":
        for h in k.lookup_term(" ".join(a.args), limit=a.limit):
            print(f"  {h['book']:30s} {h['term'][:60]:60s} pp. {h['printed_pages']}")
        return 0
    if a.cmd == "toc":
        for e in k.toc(a.args[0]):
            print(f"  {'  ' * (e['level'] - 1)}{e['title'][:80]}  (p. {e['label'] or '?'}, pdf {e['pdf_page']})")
        return 0
    if a.cmd == "read":
        for p in k.read(a.args[0], int(a.args[1]), a.count):
            print(f"--- pdf {p['pdf_page']} / printed {p['label'] or '?'} / {p['section']}"
                  f"{' / FIGURE PAGE: read the image' if p['figure_heavy'] else ''}\n{p['text']}")
        return 0
    if a.cmd == "image":
        print(k.page_image(a.args[0], int(a.args[1])))
        return 0
    print(json.dumps(k.stats(), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
