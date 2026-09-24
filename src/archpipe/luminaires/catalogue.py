"""Search across both layers of the luminaire library.

    catalogue.sqlite   every product a manufacturer lists (spec line from its
                       pages, market availability) -- UNVERIFIED: no files yet
    library.sqlite     products whose manufacturer files were imported and
                       checked (library.verify_product) -- VERIFIED, pickable

A design picks only verified products. A catalogue hit is where the search
starts: it says what exists and where it is sold, and `download_links`
gives the manufacturer's own file links to fetch in a browser.
"""
from __future__ import annotations

import html as _html
import json
import sqlite3
from pathlib import Path

from archpipe.luminaires import library as lib
from archpipe.luminaires.library import LIBRARY


def _catalogue_rows(library: Path = LIBRARY):
    db = library / "catalogue.sqlite"
    if not db.is_file():
        return []
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute("select * from products")]
    con.close()
    for r in rows:
        for k in ("lm", "watts", "cct_k", "cri", "beam_deg", "size_mm", "files"):
            r[k] = json.loads(r[k]) if r.get(k) else []
    return rows


def search_catalogue(*, mount=None, lm=None, cct=None, market=None, text=None, max_size_mm=None,
                     ip_min=None, manufacturer=None, library: Path = LIBRARY, limit=50) -> list[dict]:
    """Filter the unverified catalogue. `lm` is (min, max) against ANY lumen package."""
    out = []
    for r in _catalogue_rows(library):
        if manufacturer and r["manufacturer"] != manufacturer.lower():
            continue
        if mount and r["mount"] != mount:
            continue
        if lm and not any(lm[0] <= v <= lm[1] for v in r["lm"]):
            continue
        if cct is not None and not any(abs(v - cct) < 1 for v in r["cct_k"]):
            continue
        if market and market.upper() not in (r["markets"] or "").split(","):
            continue
        if text and text.lower() not in (r["title"] + " " + r["family"] + " " + r["sku"]).lower():
            continue
        if max_size_mm is not None and r["size_mm"] and max(r["size_mm"]) > max_size_mm:
            continue
        if ip_min is not None and (not r["ip"] or int(r["ip"][2:]) < ip_min):
            continue
        out.append(r)
    return out[:limit]


def status(manufacturer: str, sku: str, library: Path = LIBRARY) -> str:
    """'verified' | 'imported, failed checks' | 'catalogue only' | 'unknown'."""
    rows = lib.search(library=library, text=sku, manufacturer=manufacturer, include_unverified=True) \
        if (library / "library.sqlite").is_file() else []
    rows = [r for r in rows if r["sku"] == sku]
    if rows:
        return "verified" if all(r["verified"] for r in rows) else "imported, failed checks"
    return "catalogue only" if any(r["sku"] == sku for r in _catalogue_rows(library)) else "unknown"


def download_links(manufacturer: str, sku: str, library: Path = LIBRARY) -> dict:
    """The manufacturer's own file links for one product, for a person to open."""
    for r in _catalogue_rows(library):
        if r["manufacturer"] == manufacturer.lower() and r["sku"] == sku:
            return {"product_page": r["url"], **r["files"]}
    raise KeyError(f"{manufacturer}/{sku} is not in the catalogue")


def write_checklist(products: list[dict], dest: Path, title: str = "Luminaire downloads") -> Path:
    """A local page of download links to click through in a browser, then drop
    the files into assets/user/luminaires/inbox/<manufacturer>/ and import."""
    rows = []
    for p in products:
        f = p.get("files") or {}
        links = " ".join(f'<a href="{_html.escape(u)}">{k.upper()}</a>' for k, u in f.items())
        rows.append(f"<tr><td>{_html.escape(p['manufacturer'])}</td><td>{_html.escape(p['sku'])}</td>"
                    f"<td><a href=\"{_html.escape(p['url'])}\">{_html.escape(p['title'])}</a></td>"
                    f"<td>{_html.escape(p['markets'] or '')}</td><td>{links}</td></tr>")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        f"<!doctype html><meta charset=utf-8><title>{_html.escape(title)}</title>"
        "<style>body{font:14px system-ui;margin:16px}td,th{padding:4px 8px;border-bottom:1px solid #ddd}</style>"
        f"<h1>{_html.escape(title)}</h1><p>{len(products)} products. Click each file link; save everything into "
        "<code>assets/user/luminaires/inbox/&lt;manufacturer&gt;/</code>, then run "
        "<code>python scripts/luminaires.py import</code>.</p>"
        "<table><tr><th>Maker</th><th>SKU</th><th>Product</th><th>Markets</th><th>Files</th></tr>"
        + "".join(rows) + "</table>", encoding="utf-8")
    return dest
