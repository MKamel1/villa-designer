"""Sheet <-> model mapping, taken from the SAME transform RV2 draws with (never re-derived).

RV2 draws a plan panel at `paper_mm = (ox + (cx - x0)/scale, oy + (cy - y0)/scale)` where (cx, cy) = `orient.pt(model x, y)`
(client north-up: street side -x is up). The panel offsets are only known while the sheet is drawn, so `record` re-runs
RV2's own `render_plan` with a recorder on `plans._draw_plan` and keeps what the sheet used. `verify` then checks the
recorded frame against the ISSUED PDF (room tags must land inside their rooms), so a mirrored/rotated frame or a sheet that
was re-laid-out since is refused instead of silently mislinking (D17 class).
Supported: plan sheets (A-101, A-111, A-121, A-131). Site, section, elevation, callout and schedule sheets have no frame yet.
"""
from __future__ import annotations

from archpipe.units import in_to_mm
import json
import re
import tempfile
from pathlib import Path

from archpipe import model
from archpipe.documents import plans, schedules, sheetset
from archpipe.drawings2d import orient, variants

PT_PER_MM = 72.0 / in_to_mm(1)
FRAMES_PATH = Path(__file__).resolve().parents[3] / "knowledge" / "markup" / "frames-D1.json"
MIN_TAG_HIT = 0.8        # share of room tags that must land inside their room for a frame to count as verified


class FrameError(ValueError):
    pass


def sheet_no(path) -> str:
    m = re.search(r"A-\d{3}", Path(path).name)
    if not m:
        raise FrameError("cannot read a sheet number (A-nnn) from %s" % path)
    return m.group(0)


def record(design: str = "D1") -> dict:
    """Re-render every plan sheet with RV2's code into a temp dir and keep the panel frames it used."""
    els = model.load(design)
    spec = sheetset.build(design, elements=els)
    spec["levels"] = json.loads(Path(model.api.snapshot_path(design)).read_text(encoding="utf-8")).get("levels", {})
    frames: dict[str, dict] = {}
    cur: dict = {}
    orig = plans._draw_plan

    def spy(sh, els_, cels, spec_, level, layers, tagmap, extras, crop, first):
        bbox = crop or plans._level_geometry(cels, level)["bbox"]
        frames[cur["no"]]["panels"].append({"level": level, "ox": sh.ox, "oy": sh.oy, "x0": sh.x0, "y0": sh.y0,
                                            "scale": sh.scale, "bbox_client_mm": list(bbox)})
        return orig(sh, els_, cels, spec_, level, layers, tagmap, extras, crop, first)

    plans._draw_plan = spy
    try:
        with tempfile.TemporaryDirectory() as td:
            for s in spec["sheets"]:
                if s["generator"] != "model" or s["kind"] != "plan":
                    continue
                cur["no"] = s["no"]
                frames[s["no"]] = {"paper_mm": list(plans.standard.PAPERS[s.get("paper", "A3 landscape").split()[0]]),
                                   "variant": s["variant"], "layers": list(variants.LAYERS[s["variant"]]), "panels": []}
                plans.render_plan(els, spec, s, Path(td) / s["no"], formats=("pdf",), layers=variants.LAYERS[s["variant"]],
                                  extras=variants.extras_for(s["variant"]))
                frames[s["no"]]["paper_mm"] = list(plans.standard.PAPERS[s.get("paper", "A3 landscape").split()[0]])
    finally:
        plans._draw_plan = orig
    return {"design": design, "frame_rule": "paper = o + (orient.pt(x,y) - x0)/scale; page y is flipped", "sheets": frames}


def load(path: Path = FRAMES_PATH) -> dict:
    if not Path(path).exists():
        raise FrameError("no frames file %s: run `python -m archpipe.markup frames`" % path)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def frames_for(no: str, data: dict | None = None) -> dict:
    data = data or load()
    if no not in data["sheets"]:
        raise FrameError("sheet %s has no model frame (supported: %s)" % (no, ", ".join(sorted(data["sheets"]))))
    return data["sheets"][no]


def model_to_page(fr: dict, p: dict, x: float, y: float, to_client=orient.pt) -> tuple[float, float]:
    cx, cy = to_client(x, y)
    px, py = p["ox"] + (cx - p["x0"]) / p["scale"], p["oy"] + (cy - p["y0"]) / p["scale"]
    return (px * PT_PER_MM, (fr["paper_mm"][1] - py) * PT_PER_MM)


def page_to_model(fr: dict, p: dict, X: float, Y: float, from_client=orient.inv) -> tuple[float, float]:
    px, py = X / PT_PER_MM, fr["paper_mm"][1] - Y / PT_PER_MM
    return from_client(p["x0"] + (px - p["ox"]) * p["scale"], p["y0"] + (py - p["oy"]) * p["scale"])


def panels_at(fr: dict, X: float, Y: float) -> list[dict]:
    """Panels whose drawn plan extent contains the page point (title block and margins match none)."""
    out = []
    for p in fr["panels"]:
        x0, y0 = model_to_page_client(fr, p, p["bbox_client_mm"][0], p["bbox_client_mm"][3])
        x1, y1 = model_to_page_client(fr, p, p["bbox_client_mm"][2], p["bbox_client_mm"][1])
        if x0 <= X <= x1 and y0 <= Y <= y1:
            out.append(p)
    return out


def model_to_page_client(fr, p, cx, cy):
    return model_to_page(fr, p, *orient.inv(cx, cy))


def verify(fr: dict, pdf: Path | str, els, to_client=orient.pt) -> dict:
    """Frame vs the issued PDF: each room tag (Rnn) must sit inside its room once mapped to the model. Raises on mismatch."""
    from archpipe.drawings2d import sheetqa
    tags = schedules.tag_numbers(els)
    rooms = {tags[e.id]: e for e in els if e.kind == "room"}
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    doc = fitz.open(str(pdf))
    page = doc[0]
    size = (page.rect.width / PT_PER_MM, page.rect.height / PT_PER_MM)
    doc.close()
    if abs(size[0] - fr["paper_mm"][0]) > 1 or abs(size[1] - fr["paper_mm"][1]) > 1:
        raise FrameError("page is %.0fx%.0f mm but the frame is for %s mm" % (size + (tuple(fr["paper_mm"]),)))
    from shapely.geometry import Point, Polygon
    pos = sheetqa.pdf_tag_positions(pdf)
    hit = n = 0
    for tag, (X, Y) in pos.items():
        if tag not in rooms:
            continue
        r = rooms[tag]
        for p in fr["panels"]:
            if p["level"] != r.level:
                continue
            n += 1
            mx, my = page_to_model(fr, p, X, Y, from_client=_inverse_of(to_client))
            hit += Polygon(r.params["polygon_mm"]).buffer(150).contains(Point(mx, my))
    if n == 0:
        return {"verified": False, "reason": "no room tags on this sheet to check against", "tags": 0}
    if hit / n < MIN_TAG_HIT:
        raise FrameError("frame does not match the PDF: only %d of %d room tags land in their room (mirrored/rotated frame "
                         "or the sheet was re-laid-out: run `frames`)" % (hit, n))
    return {"verified": True, "tags": n, "inside": hit}


def _inverse_of(to_client):
    if to_client is orient.pt:
        return orient.inv
    # numeric inverse for the test-only alternative mappings (linear, 2x2)
    a, b = to_client(1, 0), to_client(0, 1)
    det = a[0] * b[1] - a[1] * b[0]
    return lambda cx, cy: ((b[1] * cx - b[0] * cy) / det, (-a[1] * cx + a[0] * cy) / det)
