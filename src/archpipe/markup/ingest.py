"""Ingest comments -> change requests. Two inputs: PDF annotations on an issued sheet, or a CSV/JSON comment export.

CSV/JSON columns: sheet, text, author, date, and either `element` (a model element id) or `x_mm`,`y_mm` (position on the
sheet in paper mm, origin lower-left, y up: the RV2 paper frame). Required columns missing -> IngestError (exit 2).
PDF: Text (anchor = icon top-left) / FreeText / Stamp / Highlight marks are picked at their centre; Square / Circle / Ink / Polygon marks use the
objects they enclose and fall back to their centre. A rotated page is refused.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import tempfile
from pathlib import Path

from . import frames as F
from . import link, store

AREA = {"Square", "Circle", "Ink", "Polygon"}
POINT = {"Text", "FreeText", "Stamp", "Caret", "Highlight", "Underline", "StrikeOut", "Line", "PolyLine"}


class IngestError(ValueError):
    pass


def _fitz():
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    return fitz


def _iso(d: str | None) -> str | None:
    m = re.match(r"D?:?(\d{4})(\d\d)(\d\d)", d or "")
    return "%s-%s-%s" % m.groups() if m else (d or None)


def _h(*parts) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:16]


def resolve(els, fr: dict | None, X: float, Y: float, ring_pdf=None) -> dict:
    """Page point (pt) on a framed sheet -> {model_point, link result}."""
    if fr is None:
        return {"model_point": None, "link_status": "unsupported-sheet", "links": [], "alternatives": [],
                "reason": "this sheet type has no model frame yet (plan sheets only)"}
    ps = F.panels_at(fr, X, Y)
    if not ps:
        return {"model_point": None, "link_status": "miss", "links": [], "alternatives": [],
                "reason": "outside the drawn plan (title block, legend or margin)"}
    p = ps[0]
    mx, my = F.page_to_model(fr, p, X, Y)
    res = None
    if ring_pdf:
        res = link.hit_area(els, p["level"], [F.page_to_model(fr, p, *q) for q in ring_pdf], p["scale"], fr["layers"])
    res = res or link.hit(els, p["level"], mx, my, p["scale"], fr["layers"])
    return {"model_point": {"x_mm": round(mx, 1), "y_mm": round(my, 1), "level": p["level"]}, "link_status": res["status"],
            "links": res["links"], "alternatives": res["alternatives"], "reason": res["reason"], "tolerance_mm": res["tolerance_mm"]}


def _record(src: dict, sheet: str, author, date, text, res: dict, sheet_pt, verified) -> dict:
    return {"source": src, "author": author, "date": date, "text": text, "sheet": sheet, "sheet_point_mm": sheet_pt,
            "model_point": res["model_point"], "link_status": res["link_status"], "link_reason": res["reason"],
            "tolerance_mm": res.get("tolerance_mm"), "links": res["links"], "alternatives": res["alternatives"],
            "frame_verified": verified}


def from_pdf(pdf: Path, els, root=store.ROOT, frames_data=None) -> list[tuple[dict, bool]]:
    pdf = Path(pdf)
    if not pdf.exists():
        raise IngestError("no such file: %s" % pdf)
    fitz = _fitz()
    doc = fitz.open(str(pdf))
    out = []
    for pno, page in enumerate(doc):
        annots = [a for a in page.annots() or [] if a.type[1] in AREA | POINT]
        if not annots:
            continue
        if page.rotation:
            raise IngestError("%s page %d is rotated %d degrees: refusing to map marks through a rotated sheet" % (pdf.name, pno + 1, page.rotation))
        try:
            no = F.sheet_no(pdf)
        except F.FrameError:
            m = re.search(r"A-\d{3}", page.get_text())
            if not m:
                raise IngestError("%s page %d: cannot tell which sheet this is" % (pdf.name, pno + 1))
            no = m.group(0)
        data = frames_data or (F.load() if F.FRAMES_PATH.exists() else {"sheets": {}})
        fr = data["sheets"].get(no)
        verified = None
        if fr:
            one = fitz.open()
            one.insert_pdf(doc, from_page=pno, to_page=pno)
            with tempfile.TemporaryDirectory() as td:
                one.save(str(Path(td) / "p.pdf"))
                try:
                    verified = F.verify(fr, Path(td) / "p.pdf", els)
                except F.FrameError as e:
                    raise IngestError("%s page %d (%s): %s" % (pdf.name, pno + 1, no, e))
        for a in annots:
            kind, r, info = a.type[1], a.rect, a.info
            ring = [(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1)] if kind in AREA else None
            cx, cy = (r.x0, r.y0) if kind == "Text" else ((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)    # a sticky note's anchor is its icon's top-left corner
            res = resolve(els, fr, cx, cy, ring)
            h = _h(no, pno, kind, round(r.x0, 1), round(r.y0, 1), round(r.x1, 1), round(r.y1, 1), info.get("content"), info.get("title"))
            src = {"file": pdf.name, "page": pno + 1, "annotation_id": info.get("id") or "xref-%d" % a.xref, "type": kind, "hash": h}
            sheet_pt = {"x": round(cx / F.PT_PER_MM, 1), "y": round((page.rect.height - cy) / F.PT_PER_MM, 1)}
            text = (info.get("content") or "").strip() or "(no text on the %s mark)" % kind
            out.append(store.add(_record(src, no, info.get("title") or None, _iso(info.get("modDate") or info.get("creationDate")),
                                         text, res, sheet_pt, verified), root))
    doc.close()
    if not out:
        raise IngestError("no annotations found in %s" % pdf)
    return out


def _rows(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        d = json.loads(path.read_text(encoding="utf-8"))
        return d["comments"] if isinstance(d, dict) else d
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def from_table(path: Path, els, root=store.ROOT, frames_data=None) -> list[tuple[dict, bool]]:
    path = Path(path)
    if not path.exists():
        raise IngestError("no such file: %s" % path)
    ids = {e.id: e for e in els}
    out = []
    for n, row in enumerate(_rows(path), 1):
        sheet, text = (row.get("sheet") or "").strip(), (row.get("text") or "").strip()
        el, xs, ys = (row.get("element") or "").strip(), row.get("x_mm"), row.get("y_mm")
        has_xy = xs not in (None, "") and ys not in (None, "")
        if not sheet or not text or not (el or has_xy):
            raise IngestError("%s row %d: needs sheet, text and either element or x_mm+y_mm" % (path.name, n))
        src = {"file": path.name, "page": None, "annotation_id": "row-%d" % n, "type": "export", "hash": _h(sheet, el, xs, ys, text, row.get("author"), row.get("date"))}
        if el:
            e = ids.get(el)
            if e is None:
                res = {"model_point": None, "link_status": "miss", "links": [], "alternatives": [], "reason": "unknown element id %s" % el}
            else:
                res = {"model_point": {"x_mm": e.placement[0], "y_mm": e.placement[1], "level": e.level}, "link_status": "linked",
                       "links": [{"element_id": el, "kind": e.kind, "distance_mm": 0.0, "tier": "named"}], "alternatives": [], "reason": "element id given in the export"}
            sheet_pt = None
        else:
            data = frames_data or (F.load() if F.FRAMES_PATH.exists() else {"sheets": {}})
            fr = data["sheets"].get(sheet)
            x, y = float(xs), float(ys)
            H = fr["paper_mm"][1] if fr else 0
            res = resolve(els, fr, x * F.PT_PER_MM, (H - y) * F.PT_PER_MM)
            sheet_pt = {"x": x, "y": y}
        out.append(store.add(_record(src, sheet, row.get("author") or None, _iso(row.get("date")), text, res, sheet_pt, None), root))
    if not out:
        raise IngestError("no comments in %s" % path)
    return out
