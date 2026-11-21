"""Revised sheet: a COPY of the new sheet PDF with a revision cloud round every changed element and a revision-table row.

The sheet is not regenerated. Element positions are read from the model NOW (so a moved element is clouded where it is);
the page position goes through the same RV2 frame as ingest. Only closed requests of this sheet are stamped.
"""
from __future__ import annotations

import math
from pathlib import Path

from . import frames as F, link, store

RED = (0.85, 0.0, 0.1)
PAD_MM = 4.0
ROW_MM, TABLE_W_MM, MAX_ROWS = 4.6, 175.0, 8


class ReviseError(ValueError):
    pass


def _fitz():
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    return fitz


def cloud(shape, r, bulge=2.2 * F.PT_PER_MM, step=5.0 * F.PT_PER_MM):
    """Scalloped cloud outline round rect r (scallops bulge outward from a clockwise walk)."""
    corners = [(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1), (r.x0, r.y0)]
    for (ax, ay), (bx, by) in zip(corners, corners[1:]):
        L = math.hypot(bx - ax, by - ay)
        n = max(1, round(L / step))
        ux, uy = (bx - ax) / L, (by - ay) / L
        nx, ny = uy, -ux                       # outward for a clockwise walk in page (y-down) coordinates
        for i in range(n):
            p0 = (ax + ux * L * i / n, ay + uy * L * i / n)
            p1 = (ax + ux * L * (i + 1) / n, ay + uy * L * (i + 1) / n)
            k = 1.33 * bulge
            shape.draw_bezier(p0, (p0[0] + nx * k, p0[1] + ny * k), (p1[0] + nx * k, p1[1] + ny * k), p1)
    shape.finish(color=RED, width=1.2, fill=None, closePath=False)


def _boxes(fr, e) -> list:
    b = link.bbox_model(e)
    if b is None:
        return []
    out = []
    for p in fr["panels"]:
        if p["level"] != e.level:
            continue
        pts = [F.model_to_page(fr, p, x, y) for x in (b[0], b[2]) for y in (b[1], b[3])]
        out.append((min(q[0] for q in pts), min(q[1] for q in pts), max(q[0] for q in pts), max(q[1] for q in pts)))
    return out


def revise_pdf(pdf: Path, els, root=store.ROOT, out: Path | None = None, frames_data=None) -> Path:
    pdf = Path(pdf)
    if not pdf.exists():
        raise ReviseError("no such sheet file: %s" % pdf)
    no = F.sheet_no(pdf)
    fr = F.frames_for(no, frames_data)
    closed = sorted((r for r in store.all_requests(root) if r["sheet"] == no and r["status"] == "closed"),
                    key=lambda r: (r["closure"]["date"], r["id"]))
    if not closed:
        raise ReviseError("no closed requests for %s: nothing to stamp" % no)
    F.verify(fr, pdf, els)
    by_id = {e.id: e for e in els}
    fitz = _fitz()
    doc = fitz.open(str(pdf))
    page = doc[0]
    fitz_rect = fitz.Rect
    rows, notes = [], []
    for i, r in enumerate(closed):
        letter = chr(ord("A") + i)
        n_cl = 0
        for l in r["links"]:
            if l["tier"] == "context":
                continue
            e = by_id.get(l["element_id"])
            if e is None:
                notes.append("%s: %s is no longer in the model, not clouded" % (r["id"], l["element_id"]))
                continue
            for b in _boxes(fr, e):
                rect = fitz_rect(b[0] - PAD_MM * F.PT_PER_MM, b[1] - PAD_MM * F.PT_PER_MM, b[2] + PAD_MM * F.PT_PER_MM, b[3] + PAD_MM * F.PT_PER_MM)
                sh = page.new_shape()
                cloud(sh, rect)
                sh.commit()
                page.insert_text((rect.x1 + 1.5, rect.y0 - 1.5), "△" + letter if False else "REV " + letter, fontsize=8, color=RED, fontname="helv")
                n_cl += 1
        if not n_cl:
            notes.append("%s: element not drawn on this sheet's panels, no cloud" % r["id"])
        rows.append((letter, r["closure"]["date"], r["id"], r["text"][:58], r["closure"]["commit"][:10]))
    W, H = page.rect.width, page.rect.height
    shown = rows[-MAX_ROWS:]
    x1 = W * 0.875
    x0, rh = x1 - TABLE_W_MM * F.PT_PER_MM, ROW_MM * F.PT_PER_MM
    y1 = H - 14 * F.PT_PER_MM
    y0 = y1 - rh * (len(shown) + 1)
    page.draw_rect(fitz_rect(x0, y0, x1, y1), color=RED, fill=(1, 1, 1), width=0.8)
    cols = [0, 8, 28, 48, 150]
    hdr = ["Rev", "Date", "Request", "Description (closed request)", "Commit"]
    xs = [x0 + c * F.PT_PER_MM + 2 for c in cols]
    for j, row in enumerate([tuple(hdr)] + shown):
        y = y0 + rh * (j + 0.75)
        for x, t in zip(xs, row):
            page.insert_text((x, y), t, fontsize=7, color=RED if j == 0 else (0, 0, 0), fontname="helv")
        page.draw_line((x0, y0 + rh * (j + 1)), (x1, y0 + rh * (j + 1)), color=RED, width=0.4)
    dest = Path(out) if out else pdf.with_name(pdf.stem + "-rev.pdf")
    if dest.resolve() == pdf.resolve():
        raise ReviseError("refusing to overwrite the sheet: the revised sheet is a copy")
    doc.save(str(dest))
    doc.close()
    for n in notes:
        print("note: " + n)
    return dest
