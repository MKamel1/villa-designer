"""The source registry's acquisition side: what to buy, and taking delivery.

`knowledge/library.json` lists every source. Each one moves through three
states. Only the last one lets a numerical rule be enabled
(`guidance.evidence_status` reads it):

    identified        we know the edition and what it would unlock
    held              a readable copy sits in the private source store
    content_verified  a person or agent read the edition's title and
                      copyright pages and the passages cited from it

Licensed originals never enter the repository. They live in SOURCES_ROOT,
outside git (default ~/archpipe-sources). The repository keeps paraphrased
evidence cards with page locators and the file hashes.

A copy is only "held" if its text can actually be read. A DRM-locked or
password-protected file is reported and stays "identified". An image-only
scan is accepted but flagged: every page must be read from the image.
"""
from __future__ import annotations

import hashlib
import html as _html
import json
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "knowledge" / "library.json"
SOURCES_ROOT = Path(os.environ.get("ARCHPIPE_SOURCES", Path.home() / "archpipe-sources"))
READABLE_SUFFIXES = (".pdf", ".epub")


def load(path: Path = REGISTRY) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(lib: dict, path: Path = REGISTRY) -> None:
    """Keep the file's existing format (2-space, ASCII-escaped, CRLF) so a save changes only content."""
    text = json.dumps(lib, indent=2, ensure_ascii=True) + "\n"
    raw = path.read_bytes() if path.is_file() else b""
    if b"\r\n" in raw[:4096]:
        text = text.replace("\n", "\r\n")
    path.write_bytes(text.encode("utf-8"))


def purchase_rows(lib: dict) -> list[dict]:
    """Sources still to obtain, grouped by tier. Deferred ones are left out, and
    so are web pages and legacy attributions (no acquisition cost recorded)."""
    rows = [s for s in lib["sources"]
            if s.get("status") == "identified" and s.get("purchase") != "deferred"
            and s.get("priority") in (1, 2, 3) and "cost_usd_approx" in s]
    return sorted(rows, key=lambda s: (s.get("free", False), s["priority"], s["id"]))


def _cost(rows) -> int:
    return sum(int(s.get("cost_usd_approx") or 0) for s in rows)


def purchase_markdown(lib: dict) -> str:
    rows = purchase_rows(lib)
    out = []
    for free, heading in ((False, "To buy"), (True, "Free: fetched by the tool (or you, if the site blocks tools)")):
        group = [s for s in rows if bool(s.get("free")) == free]
        if not group:
            continue
        out.append(f"### {heading}\n")
        for tier in (1, 2, 3):
            tier_rows = [s for s in group if s["priority"] == tier]
            if not tier_rows:
                continue
            cost = f" (about ${_cost(tier_rows):,})" if not free else ""
            out.append(f"**Tier {tier}**{cost}\n")
            out.append("| Id | Title | Edition | What it unlocks | ≈ USD |")
            out.append("|---|---|---|---|---|")
            for s in tier_rows:
                title = f"[{s['title']}]({s['url']})" if s.get("url") else s["title"]
                isbn = f", ISBN {s['isbn']}" if s.get("isbn") else ""
                out.append(f"| `{s['id']}` | {s['author']}: {title} | {s['edition']}{isbn} | "
                           f"{s.get('unlocks') or s.get('coverage', '')} | "
                           f"{'free' if free else s.get('cost_usd_approx', '?')} |")
            out.append("")
    paid = [s for s in rows if not s.get("free")]
    out.append(f"Paid total about **${_cost(paid):,}** (prices approximate; confirm at checkout).")
    return "\n".join(out) + "\n"


def write_purchase_html(lib: dict, dest: Path) -> Path:
    rows = purchase_rows(lib)
    body = []
    for s in rows:
        link = (f'<a href="{_html.escape(s["url"])}">{_html.escape(s["title"])}</a>' if s.get("url")
                else _html.escape(s["title"]))
        body.append(f"<tr><td>{'free' if s.get('free') else 'Tier ' + str(s['priority'])}</td>"
                    f"<td>{_html.escape(s['author'])}: {link}</td><td>{_html.escape(str(s['edition']))}"
                    f"{' / ISBN ' + s['isbn'] if s.get('isbn') else ''}</td>"
                    f"<td>{_html.escape(s.get('unlocks') or s.get('coverage', ''))}</td>"
                    f"<td>{'' if s.get('free') else s.get('cost_usd_approx', '')}</td><td>{s['id']}</td></tr>")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        "<!doctype html><meta charset=utf-8><title>Books and standards to obtain</title>"
        "<style>body{font:14px system-ui;margin:16px}td,th{padding:4px 8px;border-bottom:1px solid #ddd;"
        "vertical-align:top}</style><h1>Books and standards to obtain</h1>"
        f"<p>Save each file into <code>{_html.escape(str(SOURCES_ROOT / 'inbox'))}</code>, then run "
        "<code>python scripts/sources.py intake</code>. Buy DRM-free PDF/EPUB; if checkout shows Kindle, "
        "VitalSource, Adobe DRM, FileOpen or Locklizard, buy print instead and scan the pages requested.</p>"
        "<table><tr><th>Tier</th><th>Title</th><th>Edition</th><th>Unlocks</th><th>≈ USD</th><th>Id</th></tr>"
        + "".join(body) + "</table>", encoding="utf-8")
    return dest


# ---------------------------------------------------------------- free sources

GOV = "https://assets.publishing.service.gov.uk/media/"
ONEBUILDING = "https://climate.onebuilding.org/WMO_Region_1_Africa/EGY_Egypt/QH_Al_Qahirah_Cairo/"
# The exact public files behind each free registry entry, found on the
# publisher's own page (2026-09-24). Current editions for dwellings.
FREE_FILES = {
    "uk-ad-o": [GOV + "6218c5aad3bf7f4f0b29b624/ADO.pdf"],
    "uk-ad-m": [GOV + "5a7f8a82ed915d74e622b17b/BR_PDF_AD_M1_2015_with_2016_amendments_V3.pdf",
                GOV + "5a804045e5274a2e8ab4f118/AD_M_Corrigenda_SECURE.pdf"],
    "uk-ad-k": [GOV + "60d5bdcde90e07716f516cfd/Approved_Document_K.pdf"],
    "uk-ad-f": [GOV + "69c12224d588c92c483e4b6a/ADF1_2026.pdf"],
    "uk-ad-l": [GOV + "69c122a6cfa346b9d4704a55/ADL1_2026.pdf"],
    "ada-2010": ["https://www.ada.gov/assets/pdfs/2010-design-standards.pdf"],
    # Cairo International (the site file set in spec/villa-site.yaml) and
    # Cairo West, the station nearest the western suburbs.
    "cairo-epw": [ONEBUILDING + "EGY_QH_Cairo.Intl.AP.623660_TMYx.2011-2025.zip",
                  ONEBUILDING + "EGY_QH_Cairo.West.AP.623680_TMYx.zip"],
}


def fetch_free(lib: dict, root: Path = SOURCES_ROOT, only: list[str] | None = None, log=print) -> dict:
    """Download the public files in FREE_FILES (robots.txt checked) and mark them held."""
    from archpipe import fetch
    by_id = {s["id"]: s for s in lib["sources"]}
    report = {"held": [], "failed": []}
    for sid, urls in FREE_FILES.items():
        if only and sid not in only:
            continue
        s = by_id[sid]
        held = {h["sha256"]: h for h in s.get("held_files", [])}
        for url in urls:
            dest = root / sid / url.rsplit("/", 1)[-1]
            try:
                fetch.download(url, dest)
            except Exception as exc:
                report["failed"].append({"id": sid, "url": url, "detail": str(exc)})
                log(f"  FAILED {sid}: {url}: {exc}")
                continue
            entry = {"file": f"{sid}/{dest.name}", "sha256": sha256(dest), "url": url}
            if dest.suffix.lower() == ".pdf":
                r = readability(dest)
                entry.update(pages=r["pages"], image_only=r["image_only"])
                if not r["readable"]:
                    report["failed"].append({"id": sid, "url": url, "detail": r["detail"]})
                    continue
            held[entry["sha256"]] = entry
            report["held"].append(entry)
            log(f"  held {entry['file']}")
        if held:
            s["held_files"] = list(held.values())
            s["access_location"] = "archpipe-sources"
            if s.get("status") == "identified":
                s["status"] = "held"
    return report


# ---------------------------------------------------------------- intake

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def readability(path: Path, sample_pages: int = 12) -> dict:
    """Can the text be read? {'readable', 'locked', 'image_only', 'pages', 'text', 'detail'}.

    'text' holds the first sample pages, used to match the file to a source.
    """
    import pymupdf
    try:
        doc = pymupdf.open(path)
    except Exception as exc:
        return {"readable": False, "locked": False, "image_only": False, "pages": 0, "text": "",
                "detail": f"cannot open: {exc}"}
    with doc:
        if doc.needs_pass:
            return {"readable": False, "locked": True, "image_only": False, "pages": doc.page_count, "text": "",
                    "detail": "password or DRM protected: buy an unlocked copy or print and scan"}
        n = doc.page_count
        text = "".join(doc[i].get_text() for i in range(min(n, sample_pages)))
        images = sum(len(doc[i].get_images()) for i in range(min(n, sample_pages)))
    if len(text.strip()) < 200 and images:
        return {"readable": True, "locked": False, "image_only": True, "pages": n, "text": text,
                "detail": "image-only scan: readable page by page from the images"}
    if len(text.strip()) < 200:
        return {"readable": False, "locked": False, "image_only": False, "pages": n, "text": text,
                "detail": "no extractable text and no page images"}
    return {"readable": True, "locked": False, "image_only": False, "pages": n, "text": text, "detail": "text"}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def match(lib: dict, filename: str, text: str) -> str | None:
    """The registry id this file is: ISBN in the text first, then the title in text or filename."""
    digits = re.sub(r"[^0-9Xx]", "", text)
    for s in lib["sources"]:
        if s.get("isbn") and s["isbn"] in digits:
            return s["id"]
    hay = _norm(filename + " " + text[:20000])
    best, best_len = None, 0
    for s in lib["sources"]:
        title = _norm(s["title"].split(":")[0])
        if len(title) >= 8 and title in hay and len(title) > best_len:
            best, best_len = s["id"], len(title)
    if best:
        return best
    stem = _norm(Path(filename).stem)
    for s in lib["sources"]:
        if _norm(s["id"]) == stem:
            return s["id"]
    return None


def intake(lib: dict, root: Path = SOURCES_ROOT, log=print) -> dict:
    """Move readable, matched files from root/inbox to root/<id>/ and mark them held."""
    inbox = root / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    by_id = {s["id"]: s for s in lib["sources"]}
    report = {"held": [], "locked": [], "unmatched": [], "unreadable": []}
    for f in sorted(p for p in inbox.iterdir() if p.is_file()):
        if f.suffix.lower() not in READABLE_SUFFIXES:
            report["unreadable"].append({"file": f.name, "detail": "not a PDF or EPUB"})
            continue
        r = readability(f)
        if r["locked"]:
            report["locked"].append({"file": f.name, "detail": r["detail"]})
            continue
        if not r["readable"]:
            report["unreadable"].append({"file": f.name, "detail": r["detail"]})
            continue
        sid = match(lib, f.name, r["text"])
        if not sid:
            report["unmatched"].append({"file": f.name, "detail": "rename it to the registry id, e.g. neufert.pdf"})
            continue
        digest = sha256(f)
        dest = root / sid / f.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(f), dest)
        s = by_id[sid]
        held = [h for h in s.get("held_files", []) if h["sha256"] != digest]
        held.append({"file": f"{sid}/{f.name}", "sha256": digest, "pages": r["pages"],
                     "image_only": r["image_only"]})
        s["held_files"] = held
        s["access_location"] = "archpipe-sources"
        if s.get("status") == "identified":
            s["status"] = "held"          # content_verified only after the edition is read
        report["held"].append({"file": f.name, "id": sid, "pages": r["pages"], "image_only": r["image_only"]})
        log(f"  held {sid}: {f.name} ({r['pages']} pages{', image-only' if r['image_only'] else ''})")
    return report
