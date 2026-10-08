"""Polite, resumable iGuzzini product pages and photometry importer.

Only www.iguzzini.com is contacted. Robots is fetched afresh for every
command, and every requested path (including redirects) is checked first.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sqlite3
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path

from archpipe import external_claims
from archpipe.luminaires import library
from archpipe.luminaires.signify import write_coverage

BASE = "https://www.iguzzini.com"
HOST = "www.iguzzini.com"
UA = "archpipe-luminaire-catalogue/1.0 (architectural design research; robots respected)"
DELAY_S = 2.5
CACHE = library.LIBRARY / "_catalogue" / "iguzzini" / "cache"
_last = [0.0]


class _SameHost(urllib.request.HTTPRedirectHandler):
    def __init__(self, rules=None):
        self.rules = rules

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).netloc != HOST:
            raise PermissionError(f"redirect to another host refused: {newurl}")
        if self.rules is not None and not self.rules.can_fetch(UA, newurl):
            raise PermissionError(f"robots.txt disallows redirect: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _request(url: str, rules=None) -> bytes:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.netloc != HOST:
        raise PermissionError(f"iGuzzini crawler refuses another host: {url}")
    wait = DELAY_S - (time.monotonic() - _last[0])
    if wait > 0:
        time.sleep(wait)
    try:
        opener = urllib.request.build_opener(_SameHost(rules))
        with opener.open(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as response:
            if urllib.parse.urlsplit(response.url).netloc != HOST:
                raise PermissionError(f"response from another host refused: {response.url}")
            return response.read()
    finally:
        _last[0] = time.monotonic()


def robots() -> urllib.robotparser.RobotFileParser:
    """Read live robots rules; a failed read stops the crawl."""
    raw = _request(BASE + "/robots.txt").decode("utf-8", "replace")
    if not re.search(r"^\s*User-agent\s*:", raw, re.I | re.M):
        raise PermissionError("iGuzzini robots.txt has no usable rules")
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(raw.splitlines())
    return parser


def fetch(url: str, *, rules=None, refresh: bool = False) -> bytes:
    rules = rules if rules is not None else robots()
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.netloc != HOST:
        raise PermissionError(f"iGuzzini crawler refuses another host: {url}")
    if not rules.can_fetch(UA, url):
        raise PermissionError(f"robots.txt disallows {url}")
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / hashlib.sha256(url.encode()).hexdigest()
    if path.is_file() and not refresh:
        return path.read_bytes()
    data = _request(url, rules)
    path.write_bytes(data)
    return data


def _numbers(page: str, patterns: tuple[str, ...]) -> list[float]:
    values = []
    for pattern in patterns:
        for match in re.finditer(pattern, page, re.I):
            values.append(float(match.group(1).replace(",", ".")))
    return sorted(set(values))


def _mount(page: str, family: str) -> str:
    # Category and installation breadcrumbs precede the product title.
    category = " ".join(re.findall(r'(?:category|installation|mounting)[^<>]{0,80}[>:" ]+([^<>]{2,90})',
                                   page, re.I))
    words = (category + " " + family).lower()
    for mount, terms in (
        ("strip", ("strip", "underscore", "cove")),
        ("track", ("track",)), ("pendant", ("pendant", "suspension")),
        ("wall", ("wall", "walky", "marker", "step")),
        ("recessed", ("recessed", "trimless", "laser blade", "laser", "light up")),
        ("surface", ("surface", "bollard", "ipro", "i pro")),
        ("linear", ("linear", "profile")),
    ):
        if any(word in words for word in terms):
            return mount
    return "unknown"


def parse_product(page: str, code: str, url: str) -> dict:
    """Read visible product facts and embedded photometric URLs; missing facts stay empty."""
    code = code.upper()
    decoded = html.unescape(page).replace("\\/", "/")
    title = re.search(r"<title[^>]*>(.*?)</title>", decoded, re.I | re.S)
    title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", title.group(1))).strip() if title else code
    family = re.sub(r"\s*[-|].*", "", title).strip() or code
    files = {}
    for path in re.findall(r'(?:https://www\.iguzzini\.com)?(/globalassets/[^\s"\'<>]+?\.(?:ldt|ies))(?:[?"\'<>\s]|$)', decoded, re.I):
        kind = path.rsplit(".", 1)[-1].lower()
        if f"/{code.lower()}/" in path.lower():
            files.setdefault(kind, BASE + path)
    # Serialized JSON can escape slashes and Unicode, so decode those before
    # looking for the same URLs. No page markup is persisted in the catalogue.
    if not files:
        try:
            unescaped = decoded.encode().decode("unicode_escape")
            for path in re.findall(r'(/globalassets/[^\s"\'<>]+?\.(?:ldt|ies))', unescaped, re.I):
                if f"/{code.lower()}/" in path.lower():
                    files.setdefault(path.rsplit(".", 1)[-1].lower(), BASE + path)
        except UnicodeError:
            pass
    ip = re.search(r"\bIP\s*([0-9]{2})\b", decoded, re.I)
    dims = re.search(r"(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*(?:[x×]\s*(\d+(?:[.,]\d+)?)\s*)?mm", decoded, re.I)
    diameter = re.search(r"(?:Ø|diameter)\s*(\d+(?:[.,]\d+)?)\s*mm", decoded, re.I)
    size = ([float(x.replace(",", ".")) for x in dims.groups() if x] if dims else
            [float(diameter.group(1).replace(",", "."))] if diameter else [])
    markets = sorted(set(re.findall(r"\b(?:EG|AE|SA|GB|UK|EU)\b", decoded)))
    return {"manufacturer": "iguzzini", "sku": code, "region": "", "title": title,
            "family": family, "category": family.lower(), "section": "", "mount": _mount(decoded, family),
            "lm": _numbers(decoded, (r'(\d+(?:[.,]\d+)?)\s*lm\b',)),      # a bare "." once matched ([\d.,]+)
            "watts": _numbers(decoded, (r'(\d+(?:[.,]\d+)?)\s*W\b',)),
            "cct_k": _numbers(decoded, (r'\b(\d{4})\s*K\b',)),
            "cri": _numbers(decoded, (r'\bCRI\s*[≥>=]*\s*(\d{2})\b', r'\bRa\s*[≥>=]*\s*(\d{2})\b')),
            "ugr": None, "beam_deg": _numbers(decoded, (r'\b(\d{1,3})\s*°',)),
            "size_mm": size, "ip": "IP" + ip.group(1) if ip else None,
            "markets": ["GB" if m == "UK" else m for m in markets], "url": url,
            "files": files, "description": ""}


def _codes_from_family(page: str) -> list[str]:
    return sorted({c.upper() for c in re.findall(r'href=["\'](?:https://www\.iguzzini\.com)?/en/([a-z0-9]{4,8})/["\']',
                                                  html.unescape(page), re.I)})


def write_catalogue(rows: list[dict], lib: Path = library.LIBRARY) -> None:
    lib.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(lib / "catalogue.sqlite")
    con.execute("create table if not exists products (manufacturer, sku, region, title, family, category,"
                " section, mount, lm, watts, cct_k, cri, ugr, beam_deg, size_mm, ip, markets, url,"
                " files, description, crawled, primary key (manufacturer, sku))")
    con.executemany("insert or replace into products values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [
        ("iguzzini", r["sku"], r["region"], r["title"], r["family"], r["category"], r["section"],
         r["mount"], json.dumps(r["lm"]), json.dumps(r["watts"]), json.dumps(r["cct_k"]),
         json.dumps(r["cri"]), r["ugr"], json.dumps(r["beam_deg"]), json.dumps(r["size_mm"]),
         r["ip"], ",".join(r["markets"]), r["url"], json.dumps(r["files"]), r["description"],
         time.strftime("%Y-%m-%d")) for r in rows])
    con.commit()
    con.close()


def crawl_products(codes=None, family_paths=None, *, lib: Path = library.LIBRARY, log=print) -> list[dict]:
    rules = robots()
    requested = {str(c).strip().upper() for c in (codes or []) if str(c).strip()}
    families = list(family_paths or [])
    for family in families:
        path = urllib.parse.urlsplit(family).path if family.startswith("https://") else family
        if not re.fullmatch(r"/en/[a-z0-9-]+/", path, re.I):
            raise ValueError(f"invalid iGuzzini family path: {family}")
        requested.update(_codes_from_family(fetch(BASE + path, rules=rules).decode("utf-8", "replace")))
    if not requested:
        raise ValueError("supply codes or family paths")
    rows, unread = [], []
    for code in sorted(requested):
        if not re.fullmatch(r"[A-Z0-9]{4,8}", code):
            raise ValueError(f"invalid iGuzzini code: {code}")
        url = f"{BASE}/en/{code.lower()}/"
        try:
            row = parse_product(fetch(url, rules=rules).decode("utf-8", "replace"), code, url)
            rows.append(row)
            log(f"{code}: {row['mount']}, {', '.join(row['files']) or 'no photometry'}")
        except Exception as exc:
            unread.append(code)
            log(f"{code}: {exc}")
    write_catalogue(rows, lib)
    write_coverage("iguzzini", len(requested), len(rows), len(rows), unread, lib)
    external_claims.assert_manifest_complete(
        len(requested),
        len(rows),
        label="iGuzzini product crawl",
        min_coverage_ratio=1.0,
        missing_items=unread,
    )
    return rows


def fetch_photometry(sku: str, *, lib: Path = library.LIBRARY, log=print) -> dict:
    code = sku.upper()
    if not re.fullmatch(r"[A-Z0-9]{4,8}", code):
        raise ValueError(f"invalid iGuzzini code: {sku}")
    rules = robots()
    url = f"{BASE}/en/{code.lower()}/"
    row = parse_product(fetch(url, rules=rules).decode("utf-8", "replace"), code, url)
    if "ldt" not in row["files"]:
        raise FileNotFoundError(f"{code}: no LDT linked on product page")
    write_catalogue([row], lib)
    dest = lib / "inbox" / "iguzzini" / code
    dest.mkdir(parents=True, exist_ok=True)
    for kind in ("ldt", "ies"):
        if kind in row["files"]:
            data = fetch(row["files"][kind], rules=rules)
            rec = external_claims.ingest_bytes(data, declared_type=kind, url=row["files"][kind])
            if rec.status != external_claims.VERIFIED:
                raise ValueError(f"{code} {kind}: downloaded content is not {kind}")
            (dest / f"{code}.{kind}").write_bytes(data)
            log(f"{code}: saved {kind} ({len(data)} bytes)")
    return library.import_inbox(lib, log=log)
