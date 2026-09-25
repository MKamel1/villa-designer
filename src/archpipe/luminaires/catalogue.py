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


def coverage(library: Path = LIBRARY) -> dict:
    """Per manufacturer: families listed vs read at the last crawl."""
    db = library / "catalogue.sqlite"
    if not db.is_file():
        return {}
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        return {r["manufacturer"]: dict(r) for r in con.execute("select * from coverage")}
    except sqlite3.OperationalError:
        return {}
    finally:
        con.close()


def _meets(r: dict, req: dict) -> list[str]:
    """Why a catalogue product fails a requirement ([] = fits on its page figures)."""
    why = []
    if req.get("mount") and r["mount"] != req["mount"]:
        why.append("mount")
    if req.get("kelvin") and not any(abs(v - req["kelvin"]) < 1 for v in r["cct_k"]):
        why.append("colour temperature")
    if req.get("lumens"):
        lo, hi = req["lumens"]
        if not any(lo <= v <= hi for v in r["lm"]):
            why.append("lumen package")
    if req.get("max_size_mm") and r["size_mm"] and max(r["size_mm"]) > req["max_size_mm"]:
        why.append("size")
    if req.get("ip_min") and (not r["ip"] or int(r["ip"][2:]) < req["ip_min"]):
        why.append("IP rating")
    return why


def findability(r: dict) -> tuple:
    """Easier to find = sold in more markets, then more efficient on its page figures."""
    markets = len([m for m in (r["markets"] or "").split(",") if m])
    eff = (max(r["lm"]) / max(r["watts"])) if r["lm"] and r["watts"] else 0.0
    return (markets, eff)


def propose(requirement: dict, *, market: str | None = None, n: int = 2, verify_live: bool = True,
            library: Path = LIBRARY) -> list[dict]:
    """Two (n) products for one lighting role, from DIFFERENT product ranges.

    Filter the catalogue by the requirement and the market, rank by
    findability, take the best of each family, and confirm each still exists
    by re-reading its live product page (an allowed page, one request each).
    CRI is rarely on the page: it is confirmed from the LDT after download.
    """
    fits = [r for r in _catalogue_rows(library)
            if not _meets(r, requirement) and (not market or market.upper() in (r["markets"] or "").split(","))]
    fits.sort(key=findability, reverse=True)
    out, families = [], set()
    for r in fits:
        # the product range, from the URL (.../<range-slug>/<sku>_EU/product): the
        # page-title family name came back empty and collapsed every range into one
        fam = r["url"].rstrip("/").split("/")[-3]
        if fam in families:
            continue
        cand = {k: r[k] for k in ("manufacturer", "sku", "title", "family", "mount", "lm", "watts", "cct_k",
                                  "size_mm", "ip", "markets", "url")}
        cand["range"] = fam
        cand["findability"] = {"markets": findability(r)[0], "page_efficacy_lm_w": round(findability(r)[1], 1)}
        cand["cri_note"] = "CRI confirmed from the LDT after download" if not r["cri"] else f"page CRI {r['cri']}"
        if verify_live:
            cand["live"] = _still_listed(r)
            if not cand["live"]["listed"]:
                continue
        cand["files"] = r["files"]
        cand["status"] = status(r["manufacturer"], r["sku"], library)
        out.append(cand)
        families.add(fam)
        if len(out) == n:
            break
    return out


def _still_listed(r: dict) -> dict:
    import time as _t
    from archpipe.luminaires import signify
    try:
        page = signify.fetch(r["url"], refresh=True)
        ok = r["sku"] in page
        return {"listed": ok, "checked": _t.strftime("%Y-%m-%d %H:%M"),
                "detail": "product page live and lists the SKU" if ok else "page live but SKU not listed"}
    except Exception as exc:
        return {"listed": False, "checked": _t.strftime("%Y-%m-%d %H:%M"), "detail": f"page not reachable: {exc}"}


def shortfall(requirement: dict, *, market: str | None = None, library: Path = LIBRARY) -> dict:
    """Why fewer than two products fit: how many products each single
    constraint excludes among those that match the mount (and market)."""
    rows = [r for r in _catalogue_rows(library)
            if (not market or market.upper() in (r["markets"] or "").split(","))
            and (not requirement.get("mount") or r["mount"] == requirement["mount"])]
    counts = {}
    for r in rows:
        for why in _meets(r, requirement):
            counts[why] = counts.get(why, 0) + 1
    ccts = sorted({v for r in rows for v in r["cct_k"]})
    return {"same_mount_in_market": len(rows), "excluded_by": counts, "cct_available_k": ccts,
            "catalogues": sorted({r["manufacturer"] for r in _catalogue_rows(library)})}
