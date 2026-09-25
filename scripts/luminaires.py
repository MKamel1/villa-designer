"""Luminaire library: import manufacturer files, search, compare, pick.

    python scripts/luminaires.py import                     # files dropped in assets/user/luminaires/inbox/
    python scripts/luminaires.py crawl signify              # refresh the Signify catalogue (pages only)
    python scripts/luminaires.py search --mount pendant --lm 600-1200 --cct 2700 --cri 90 --market EG
    python scripts/luminaires.py search --catalogue --mount recessed --market EG      # not yet downloaded
    python scripts/luminaires.py show signify 911401840687
    python scripts/luminaires.py alternates signify 911401840687 --lamp-set 0
    python scripts/luminaires.py links signify 911401840687 [more skus]   # file links to click
    python scripts/luminaires.py checklist --mount recessed --market EG   # a page of links to click

Verified rows come from the manufacturer's own files, each checked (flux vs
LORL, LDT vs the manufacturer's IES, sanity). Catalogue rows come from
product pages and are marked unverified until their files are imported.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from archpipe.luminaires import catalogue as cat  # noqa: E402
from archpipe.luminaires import library as lib    # noqa: E402

COLS = ("manufacturer", "sku", "lamp_set", "mount", "luminaire_lm", "watts", "efficacy", "cct_k", "cri_ra",
        "beam_deg", "length_mm", "width_mm", "height_mm", "has_rfa", "verified", "name")


def _range(s):
    if not s:
        return None
    a, b = s.split("-")
    return float(a), float(b)


def _print_rows(rows, cols):
    for r in rows:
        print("  " + "  ".join(f"{k}={r.get(k)}" for k in cols))
    print(f"  ({len(rows)} rows)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("import")
    c = sub.add_parser("crawl")
    c.add_argument("manufacturer", choices=["signify"])
    for name in ("search", "checklist"):
        s = sub.add_parser(name)
        s.add_argument("--catalogue", action="store_true", help="search the unverified catalogue")
        s.add_argument("--manufacturer")
        s.add_argument("--mount")
        s.add_argument("--lm", help="min-max luminaire lumens")
        s.add_argument("--cct", type=float)
        s.add_argument("--cri", type=float)
        s.add_argument("--beam", help="min-max degrees (computed from the file)")
        s.add_argument("--market", help="EG, AE, SA, GB ...")
        s.add_argument("--text")
        s.add_argument("--max-length", type=float)
        s.add_argument("--max-size", type=float, help="catalogue: largest dimension, mm")
        s.add_argument("--ip-min", type=int)
        s.add_argument("--include-unverified", action="store_true")
        s.add_argument("--limit", type=int, default=30)
        s.add_argument("--out", type=Path, default=ROOT / "out/luminaire-downloads.html")
    for name in ("show", "alternates", "links"):
        s = sub.add_parser(name)
        s.add_argument("manufacturer")
        s.add_argument("sku", nargs="+")
        s.add_argument("--lamp-set", type=int, default=0)
    a = ap.parse_args(argv)

    if a.cmd == "import":
        rep = lib.import_inbox()
        return 0 if rep["products"] or not rep["skipped"] else 1
    if a.cmd == "crawl":
        from archpipe.luminaires import signify
        signify.crawl()
        cov = cat.coverage().get("signify") or {}
        ok = cov.get("families_read", 0) >= signify.MIN_COVERAGE * max(1, cov.get("families_listed", 1))
        return 0 if ok else 1
    if a.cmd in ("search", "checklist"):
        if a.catalogue or a.cmd == "checklist":
            rows = cat.search_catalogue(mount=a.mount, lm=_range(a.lm), cct=a.cct, market=a.market, text=a.text,
                                        max_size_mm=a.max_size, ip_min=a.ip_min, manufacturer=a.manufacturer,
                                        limit=a.limit if a.cmd == "search" else 100000)
            if a.cmd == "checklist":
                print(cat.write_checklist(rows, a.out, "Luminaire downloads"))
                print(f"  {len(rows)} products")
                return 0
            for m, cv in cat.coverage().items():
                if cv["families_read"] < cv["families_listed"]:
                    print(f"  NOTE {m} catalogue covers {cv['families_read']} of {cv['families_listed']} "
                          f"listed families (crawled {cv['crawled']})")
            for r in rows:
                r["status"] = cat.status(r["manufacturer"], r["sku"])
            _print_rows(rows, ("manufacturer", "sku", "mount", "lm", "watts", "cct_k", "ip", "size_mm",
                               "markets", "status", "title"))
            return 0
        rows = lib.search(manufacturer=a.manufacturer, mount=a.mount, lm=_range(a.lm), cct=a.cct, cri_min=a.cri,
                          beam=_range(a.beam), max_length_mm=a.max_length, market=a.market, text=a.text,
                          include_unverified=a.include_unverified, limit=a.limit)
        _print_rows(rows, COLS)
        return 0
    if a.cmd == "show":
        for sku in a.sku:
            r = lib.get(a.manufacturer, sku, a.lamp_set)
            print(json.dumps(r, indent=2) if r else f"{a.manufacturer}/{sku}: {cat.status(a.manufacturer, sku)}")
        return 0
    if a.cmd == "alternates":
        _print_rows(lib.alternates(a.manufacturer, a.sku[0], a.lamp_set), COLS)
        return 0
    if a.cmd == "links":
        for sku in a.sku:
            print(json.dumps(cat.download_links(a.manufacturer, sku), indent=2))
        print("Open each link in a browser, save into assets/user/luminaires/inbox/%s/, then run: "
              "python scripts/luminaires.py import" % a.manufacturer)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
