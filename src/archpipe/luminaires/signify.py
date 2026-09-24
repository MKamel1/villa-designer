"""Signify (Philips) professional catalogue, from the pages its robots.txt allows.

What this reads, and what it deliberately does not:

    www.signify.com  category and family pages -- allowed by robots.txt. Each
                     family page lists every product with its full spec line.
    api.microservices.signify.com  the photometry / Revit file server --
                     robots.txt `Disallow: /`. NEVER fetched here. For a picked
                     product this module prints the file links for the user to
                     download in a browser; `library.import_inbox` takes over.

Market availability is read from the per-country sites: a family listed on
/en-eg/ category pages is offered in Egypt, and so on. It is family-level:
an individual SKU can still vary by market.

Polite by construction: one request at a time, a fixed delay, an honest
User-Agent, and an on-disk cache so a rerun or a resume costs nothing.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from archpipe.luminaires.library import LIBRARY

BASE = "https://www.signify.com"
UA = "archpipe-luminaire-catalogue/1.0 (architectural design research; pages only, robots.txt respected)"
DELAY_S = 2.5
LOCALES = {"global": None, "en-eg": "EG", "en-ae": "AE", "en-sa": "SA", "en-gb": "GB"}
SECTIONS = ("indoor-luminaires", "outdoor-luminaires")
FILE_SERVER = "https://api.microservices.signify.com/api/configurator/v2/getPhotometricAssets"
CATEGORY_MOUNT = {
    "recessed": "recessed", "downlights": "recessed", "accent-downlights": "recessed",
    "suspended": "pendant", "surface-mounted": "surface", "battens": "linear",
    "panels-on-track": "track", "high-bay-and-low-bay": "industrial",
}
CACHE = LIBRARY / "_catalogue" / "signify" / "cache"
_last = [0.0]


def fetch(url: str, refresh: bool = False) -> str:
    """One polite GET, cached on disk. Refuses the file server outright."""
    if "api.microservices.signify.com" in url:
        raise PermissionError("the Signify file server disallows automated access (robots.txt); "
                              "download product files in a browser and import them")
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (hashlib.sha256(url.encode()).hexdigest()[:24] + ".html")
    if f.is_file() and not refresh:
        return f.read_text(encoding="utf-8")
    wait = DELAY_S - (time.monotonic() - _last[0])
    if wait > 0:
        time.sleep(wait)
    missing = f.with_suffix(".404")
    if missing.is_file() and not refresh:
        raise FileNotFoundError(url)
    # Product slugs can hold non-ASCII ("milewide²"); urllib sends ASCII only.
    req = urllib.request.Request(urllib.parse.quote(url, safe=":/?&=%#"), headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                text = r.read().decode("utf-8", "replace")
            break
        except urllib.error.HTTPError as exc:
            _last[0] = time.monotonic()
            if 400 <= exc.code < 500:            # a client error will not change on retry
                missing.write_text(str(exc.code))
                raise FileNotFoundError(url) from None
            if attempt == 2:
                raise
            time.sleep(10 * (attempt + 1))
        except Exception:
            if attempt == 2:
                raise
            time.sleep(10 * (attempt + 1))
    _last[0] = time.monotonic()
    f.write_text(text, encoding="utf-8")
    return text


def categories(locale: str, section: str) -> list[str]:
    page = fetch(f"{BASE}/{locale}/prof/{section}")
    return sorted(set(re.findall(rf"/{locale}/prof/{section}/[^\"'\s\\<>]+/category", page)))


def families(locale: str, category_path: str) -> list[str]:
    page = fetch(BASE + category_path)
    return sorted(set(re.findall(rf"/{locale}/prof/[^\"'\s\\<>]+/family", page)))


_PRODUCT = re.compile(
    r'<a href="(?P<url>https://www\.signify\.com/[^"]+/(?P<code>(?P<sku>[0-9A-Za-z]+)_(?P<region>[A-Z]+))/product)"'
    r'[^>]*>\s*(?P<title>[^<]+?)\s*</a>')
_DESC = re.compile(r'product-table-list__product-description[^>]*>\s*(?P<d>[^<]+?)\s*</div>')


def parse_family(page: str, family_path: str) -> list[dict]:
    """Every product on a family page with its spec line."""
    page_u = page.replace("\\u002F", "/")
    fam_name = html.unescape((re.search(r"<title>([^<|]+)", page) or [None, ""])[1]).strip()
    out = []
    for m in _PRODUCT.finditer(page_u):
        tail = page_u[m.end(): m.end() + 6000]
        d = _DESC.search(tail)
        desc = html.unescape(d.group("d")).strip() if d else ""
        title = html.unescape(m.group("title")).strip()
        spec = parse_spec(title + ", " + desc)
        out.append({"sku": m.group("sku"), "region": m.group("region"), "url": m.group("url"),
                    "title": title, "description": desc, "family": fam_name,
                    "family_path": family_path, **spec})
    seen, uniq = set(), []
    for p in out:
        if p["sku"] not in seen:
            seen.add(p["sku"])
            uniq.append(p)
    return uniq


def parse_spec(text: str) -> dict:
    """Numbers from Signify's spec line. Lists where the product is multi-lumen."""
    num = lambda pat: [float(x.replace(",", "")) for x in re.findall(pat, text)]
    dims = re.search(r"(\d{2,4})\s*x\s*(\d{2,4})\s*mm", text)
    dia = re.search(r"(?:D|Ø|diameter\s*)(\d{2,4})\s*mm", text, re.I)
    ip = re.search(r"\bIP(\d{2})", text)
    return {
        "lm": sorted(set(num(r"([\d,]+)\s*lm\b(?!/)"))),
        "watts": sorted(set(num(r"(\d+(?:\.\d+)?)\s*W\b"))),
        "cct_k": sorted(set(num(r"\b(\d{4})\s*K\b"))),
        "cri": sorted(set(num(r"CRI\s*>?\s*(\d{2})"))) or sorted(set(
            float(x[0]) * 10 for x in re.findall(r"/(\d)(\d)\d\b", text))),
        "ugr": (num(r"UGR\s*(\d{2})") or [None])[0],
        "beam_deg": sorted(set(num(r"(\d{1,3})\s*°"))),
        "size_mm": [float(dims.group(1)), float(dims.group(2))] if dims else
                   ([float(dia.group(1))] if dia else []),
        "ip": f"IP{ip.group(1)}" if ip else None,
    }


def crawl(sections=SECTIONS, locales=LOCALES, log=print) -> int:
    """Walk categories and families; write the catalogue table. Resumable."""
    fam_markets: dict[str, set] = {}
    fam_category: dict[str, str] = {}
    fam_seen_at: dict[str, list] = {}
    for loc, market in locales.items():
        for section in sections:
            try:
                cats = categories(loc, section)
            except Exception as exc:
                log(f"  {loc}/{section}: {exc}")
                continue
            for cat in cats:
                cat_slug = cat.split("/")[-3]
                for fam in families(loc, cat):
                    key = "/".join(fam.split("/")[3:])           # locale-free path
                    fam_markets.setdefault(key, set())
                    if market:
                        fam_markets[key].add(market)
                    fam_category.setdefault(key, f"{section}/{cat_slug}")
                    fam_seen_at.setdefault(key, []).append(fam)
            log(f"  {loc}/{section}: {len(cats)} categories, {len(fam_markets)} families so far")
    rows = []
    for i, (key, markets) in enumerate(sorted(fam_markets.items()), 1):
        # Some families exist only on market sites, not under /global/.
        prods, path = None, None
        for path in ["/global/" + key] + [f for f in fam_seen_at.get(key, []) if not f.startswith("/global/")]:
            try:
                prods = parse_family(fetch(BASE + path), path)
                break
            except FileNotFoundError:
                continue
            except Exception as exc:
                log(f"  family {key}: {exc}")
                break
        if prods is None:
            log(f"  family {key}: no page found in any market")
            continue
        section, cat = fam_category[key].split("/")
        for p in prods:
            p.update(category=cat, section=section, markets=sorted(markets),
                     mount=CATEGORY_MOUNT.get(cat, "outdoor" if section.startswith("outdoor") else "unknown"),
                     files={k: f"{FILE_SERVER}/{k}?id={p['sku']}&locale=en_AA" for k in ("ldt", "ies", "revit")})
            rows.append(p)
        if i % 10 == 0:
            log(f"  {i}/{len(fam_markets)} families, {len(rows)} products")
    write_catalogue(rows)
    log(f"catalogue: {len(rows)} Signify products in {len(fam_markets)} families")
    return len(rows)


def write_catalogue(rows: list[dict], library: Path = LIBRARY) -> None:
    db = library / "catalogue.sqlite"
    con = sqlite3.connect(db)
    con.execute("create table if not exists products (manufacturer, sku, region, title, family, category,"
                " section, mount, lm, watts, cct_k, cri, ugr, beam_deg, size_mm, ip, markets, url,"
                " files, description, crawled, primary key (manufacturer, sku))")
    con.executemany(
        "insert or replace into products values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [("signify", r["sku"], r["region"], r["title"], r["family"], r["category"], r["section"], r["mount"],
          json.dumps(r["lm"]), json.dumps(r["watts"]), json.dumps(r["cct_k"]), json.dumps(r["cri"]), r["ugr"],
          json.dumps(r["beam_deg"]), json.dumps(r["size_mm"]), r["ip"], ",".join(r["markets"]), r["url"],
          json.dumps(r["files"]), r["description"], time.strftime("%Y-%m-%d")) for r in rows])
    con.commit()
    con.close()
