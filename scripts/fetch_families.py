"""Download Revit families from a free library and screen them by version.

    python scripts/fetch_families.py --category doors --limit 4
    python scripts/fetch_families.py --url https://bimlibrary.co/download/x/

Revit 2025 ships no doors, windows, furniture or light fixtures (ADR-0008),
so content has to come from somewhere. This fetches from bimlibrary.co,
which publishes `.rfa` files with no account required.

THE VERSION GATE IS THE POINT

Revit families are forward-compatible only. A family saved by Revit 2026
will not open in 2025 and cannot be downgraded, so a download that looks
fine can be useless -- and the sites rarely say which release they
published from. Every file is therefore screened by `archpipe.rfa`, which
reads the format version out of the file without launching Revit.

That matters beyond convenience: **opening a family in a newer Revit
upgrades it on save**, so checking by opening can destroy the thing being
checked. Nothing here opens anything.

Files that fail the gate are kept, in a `too-new/` folder, rather than
deleted -- they are still usable by anyone on a later Revit, and silently
discarding a download is worse than filing it.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from archpipe import rfa  # noqa: E402

BASE = "https://bimlibrary.co"
UA = "Mozilla/5.0 (compatible; archpipe family fetcher)"
OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

# The download link carries a `wpdmdl` id and the real filename.
_DL = re.compile(r'href="(https://bimlibrary\.co/download/[^"]*wpdmdl=[^"]*)"')
# Some items are deliberately gated behind an unlock (email or share).
# That is the site's access control and this script does not work around
# it -- it reports the item as locked so the choice is the user's.
_LOCKED = re.compile(r'wpdm-download-locked')
_PRODUCT = re.compile(r'href="(https://bimlibrary\.co/download/[a-z0-9-]+/)"')


class Locked(Exception):
    """The site gates this item behind an unlock step."""


def get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def product_urls(category: str, limit: int) -> list[str]:
    page = get(f"{BASE}/bim-category/{category}/").decode("utf-8", "ignore")
    seen, out = set(), []
    for m in _PRODUCT.finditer(page):
        u = m.group(1)
        if u not in seen:
            seen.add(u)
            out.append(u)
        if len(out) >= limit:
            break
    return out


def download_link(product_url: str) -> tuple[str, str] | None:
    """(download url, suggested filename) for a product page."""
    page = get(product_url).decode("utf-8", "ignore")
    m = _DL.search(page)
    if not m:
        if _LOCKED.search(page):
            raise Locked(product_url)
        return None
    url = html.unescape(m.group(1))
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    name = (q.get("filename") or [product_url.rstrip("/").split("/")[-1]])[0]
    if not name.lower().endswith((".rfa", ".zip")):
        name += ".rfa"
    return url, name


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--category",
                    help="doors, windows, furniture, lighting-fixtures, ...")
    ap.add_argument("--url", action="append", default=[],
                    help="a specific product page; repeatable")
    ap.add_argument("--limit", type=int, default=4)
    ap.add_argument("--target", type=int, default=2025,
                    help="the Revit release these must load into")
    ap.add_argument("--out", type=Path, default=Path("out/families"))
    a = ap.parse_args()

    pages = list(a.url)
    if a.category:
        pages += product_urls(a.category, a.limit)
    if not pages:
        print("Nothing to fetch: give --category or --url.")
        return 2

    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "too-new").mkdir(exist_ok=True)

    ok = too_new = unknown = failed = locked = 0
    for page in pages:
        try:
            link = download_link(page)
        except Locked:
            print(f"  LOCKED  {page.rstrip('/').split('/')[-1]} -- the site "
                  f"gates this one behind an unlock step; open it in a "
                  f"browser if you want it")
            locked += 1
            continue
        if not link:
            print(f"  SKIP  {page} -- no download link found")
            failed += 1
            continue
        url, name = link
        dest = a.out / name
        try:
            blob = get(url)
        except Exception as e:                      # noqa: BLE001
            print(f"  FAIL  {name}: {e}")
            failed += 1
            continue

        # An HTML error page saved as .rfa is the classic silent failure:
        # it has the right name, a plausible size, and is not a family.
        if not blob.startswith(OLE_MAGIC):
            print(f"  FAIL  {name}: not a Revit family (got "
                  f"{len(blob)} bytes, wrong magic -- probably an error page)")
            failed += 1
            continue

        dest.write_bytes(blob)
        info = rfa.read(dest)
        verdict = info.usable_in(a.target)
        if verdict is False:
            dest.replace(a.out / "too-new" / name)
            too_new += 1
        elif verdict is None:
            unknown += 1
        else:
            ok += 1
        print(f"  {info.describe(a.target)}  [{len(blob) // 1024} KB]")
        time.sleep(1.0)            # be a polite client

    print(f"\n{ok} usable, {too_new} too new, {unknown} unknown version, "
          f"{locked} locked, {failed} failed -> {a.out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
