"""DXF plans (R2018, millimetres 1:1) per level and a site plan, AIA-style layer names, written with ezdxf.

One file per sheet: D1-B.dxf, D1-GF.dxf, D1-SITE.dxf. Model coordinates are used unchanged (the shared origin of the IFC
files), so the DXFs overlay the IFC in any CAD viewer. Plan symbols only: this is not a drawing set (RV2 owns drawings).
True .dwg needs the ODA File Converter or Autodesk; neither is on the workstation (see docs/lanes/RV3-exchange.md).
"""
from __future__ import annotations

import math
from pathlib import Path

import ezdxf
from ezdxf import units
from ezdxf.audit import Auditor

from ..contracts import DesignElement
from . import common as C

# AIA CAD Layer Guidelines style names (discipline-major-minor), colours are ACI.
LAYERS = {
    "A-WALL": 7, "A-DOOR": 3, "A-GLAZ": 5, "A-FLOR-OTLN": 8, "A-FLOR-STRS": 6, "A-FLOR-HRAL": 4, "A-AREA-IDEN": 2,
    "A-FURN": 30, "A-FLOR-FIXT": 31, "E-LITE": 40, "S-COLS": 1, "S-BEAM": 1, "A-GRID": 9, "G-ANNO-TTLB": 7,
    "L-PLNT": 94, "L-SITE": 92, "X-CNTX": 8,
}


def _rect_pts(cx, cy, w, d, ang_deg=0.0):
    a = math.radians(ang_deg)
    ca, sa = math.cos(a), math.sin(a)
    return [(cx + ca * x - sa * y, cy + sa * x + ca * y) for x, y in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2))]


def _wall_pts(w: DesignElement):
    (x0, y0), (x1, y1) = C.wall_line(w)
    L = math.dist((x0, y0), (x1, y1))
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    h = float(w.params["thickness_mm"]) / 2
    nx, ny = -uy * h, ux * h
    return [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]


class _Sheet:
    def __init__(self, title: str, scale_note="1:1, millimetres, model coordinates (shared origin with the IFC)"):
        self.doc = ezdxf.new("R2018", setup=True)
        self.doc.units = units.MM
        self.doc.header["$MEASUREMENT"] = 1
        for n, c in LAYERS.items():
            self.doc.layers.add(n, color=c)
        self.msp = self.doc.modelspace()
        self.title, self.note = title, scale_note
        self.counts: dict[str, int] = {}

    def _n(self, layer):
        self.counts[layer] = self.counts.get(layer, 0) + 1

    def poly(self, pts, layer, closed=True):
        self.msp.add_lwpolyline(pts, close=closed, dxfattribs={"layer": layer})
        self._n(layer)

    def circle(self, c, r, layer):
        self.msp.add_circle(c, r, dxfattribs={"layer": layer})
        self._n(layer)

    def line(self, a, b, layer):
        self.msp.add_line(a, b, dxfattribs={"layer": layer})
        self._n(layer)

    def text(self, s, at, h, layer, ang=0.0):
        t = self.msp.add_text(s, height=h, rotation=ang, dxfattribs={"layer": layer})
        t.set_placement(at)
        self._n(layer)

    def save(self, path: Path):
        pts = [(v[0], v[1]) for e in self.msp.query("LWPOLYLINE") for v in e.get_points("xy")]
        if pts:
            x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
            self.text(f"{self.title}  |  {self.note}", (x0, y0 - 1500), 250, "G-ANNO-TTLB")
        aud = Auditor(self.doc)
        aud.run()
        if aud.has_errors:
            raise C.ExchangeError([f"{path.name}: ezdxf audit errors: {[str(e.message) for e in aud.errors][:5]}"])
        path.parent.mkdir(parents=True, exist_ok=True)
        self.doc.saveas(str(path))
        return len(aud.errors), len(aud.fixes)


def _door(sh: _Sheet, e: DesignElement, by, centroid):
    p = e.params
    hw = by[e.host]
    t = float(hw.params["thickness_mm"])
    a, _ = C.project_on_wall(hw, e.placement[:2])
    (x0, y0), (x1, y1) = C.wall_line(hw)
    L = C.wall_length(hw)
    u = ((x1 - x0) / L, (y1 - y0) / L)
    c = (x0 + u[0] * a, y0 + u[1] * a)
    W = float(p["width_mm"])
    sh.poly(_rect_pts(c[0], c[1], W, t, math.degrees(math.atan2(u[1], u[0]))), "A-DOOR")
    hinge, room = p.get("hinge_xy_mm"), p.get("swing_into")
    if p.get("operation") == "hinged" and hinge and room in centroid:
        h = (float(hinge[0]), float(hinge[1]))
        dc = (c[0] - h[0], c[1] - h[1])
        n0 = (-u[1], u[0])
        rc = centroid[room]
        n = n0 if (n0[0] * (rc[0] - c[0]) + n0[1] * (rc[1] - c[1])) > 0 else (-n0[0], -n0[1])
        dcn = math.hypot(*dc)
        dcu = (dc[0] / dcn, dc[1] / dcn)
        sh.line(h, (h[0] + n[0] * W, h[1] + n[1] * W), "A-DOOR")
        s, en = math.degrees(math.atan2(dcu[1], dcu[0])), math.degrees(math.atan2(n[1], n[0]))
        if dcu[0] * n[1] - dcu[1] * n[0] < 0:
            s, en = en, s
        sh.msp.add_arc(h, W, s, en, dxfattribs={"layer": "A-DOOR"})
        sh._n("A-DOOR")


def level_sheet(elements: list[DesignElement], level: str) -> _Sheet:
    by = {e.id: e for e in elements}
    sh = _Sheet(f"D1 plan {level}")
    centroid = {}
    for r in (e for e in elements if e.kind == "room" and e.level == level):
        poly = r.params["polygon_mm"]
        centroid[r.id[5:]] = (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))
    for e in elements:
        p, k = e.params, e.kind
        on = e.level == level
        if k == "wall" and on:
            sh.poly(_wall_pts(e), "A-WALL")
        elif k == "room" and on:
            sh.poly([tuple(v) for v in p["polygon_mm"]], "A-AREA-IDEN")
            cx, cy = centroid[e.id[5:]]
            sh.text(f"{p.get('name') or e.id[5:]}  {p.get('net_area_m2', p.get('area_m2'))} m2", (cx, cy), 150, "A-AREA-IDEN")
        elif k == "slab" and on and p.get("polygon_mm"):
            sh.poly([tuple(v) for v in p["polygon_mm"]], "A-FLOR-OTLN")
            for h in p.get("holes_mm") or []:
                sh.poly([tuple(v) for v in h], "A-FLOR-OTLN")
        elif k == "slab" and on:
            sh.poly(_rect_pts(e.placement[0], e.placement[1], e.size[0], e.size[1], e.rotation_deg), "A-FLOR-OTLN")
        elif k == "door" and on:
            _door(sh, e, by, centroid)
        elif k == "window" and on:
            hw = by[e.host]
            a, _ = C.project_on_wall(hw, e.placement[:2])
            (x0, y0), (x1, y1) = C.wall_line(hw)
            L = C.wall_length(hw)
            u = ((x1 - x0) / L, (y1 - y0) / L)
            c = (x0 + u[0] * a, y0 + u[1] * a)
            sh.poly(_rect_pts(c[0], c[1], float(p["width_mm"]), float(hw.params["thickness_mm"]),
                              math.degrees(math.atan2(u[1], u[0]))), "A-GLAZ")
        elif k == "stair" and on:
            for x0, y0, _, x1, y1, _ in p["tread_boxes_mm"]:
                sh.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "A-FLOR-STRS")
        elif k == "railing" and (on or e.level == "SITE" and level == "GF"):
            path = p.get("path_mm") or p.get("profile_mm")
            if path and len(path[0]) == 3 and e.id.startswith("rail-stair"):
                path = [(v[0], v[1]) for v in path]
            elif path and p.get("path_mm"):
                path = [(v[0], v[1]) for v in path]
            else:
                path = None
            if path:
                sh.poly(path, "A-FLOR-HRAL", closed=False)
            elif e.size[0] > 0:
                sh.poly(_rect_pts(e.placement[0], e.placement[1], e.size[0], max(e.size[1], 20.0), e.rotation_deg), "A-FLOR-HRAL")
        elif k == "column" and level in ("B", "GF"):
            sh.poly(_rect_pts(e.placement[0], e.placement[1], e.size[0], e.size[1], e.rotation_deg), "S-COLS")
        elif k == "beam" and on:
            sh.poly(_rect_pts(e.placement[0], e.placement[1], e.size[0], e.size[1], e.rotation_deg), "S-BEAM")
        elif k == "furniture" and on and e.size[0] > 0 and e.size[1] > 0:
            sh.poly(_rect_pts(e.placement[0], e.placement[1], e.size[0], e.size[1], e.rotation_deg), "A-FURN")
        elif k == "fixture" and on and e.size[0] > 0 and e.size[1] > 0:
            sh.poly(_rect_pts(e.placement[0], e.placement[1], e.size[0], e.size[1], e.rotation_deg), "A-FLOR-FIXT")
        elif k == "luminaire" and on:
            sh.circle((e.placement[0], e.placement[1]), max(e.size[0], 60.0) / 2, "E-LITE")
    _grid(sh, elements)
    return sh


def _grid(sh: _Sheet, elements):
    cols = [e for e in elements if e.kind == "column"]
    if not cols:
        return
    xs, ys = grid_axes(cols)
    x0, x1, y0, y1 = min(xs) - 1000, max(xs) + 1000, min(ys) - 1000, max(ys) + 1000
    for i, x in enumerate(xs):
        sh.line((x, y0), (x, y1), "A-GRID")
        sh.text(str(i + 1), (x, y1 + 100), 200, "A-GRID")
    for i, y in enumerate(ys):
        sh.line((x0, y), (x1, y), "A-GRID")
        sh.text(chr(ord("A") + i), (x0 - 300, y), 200, "A-GRID")


def grid_axes(cols, tol=200.0):
    def cluster(vals):
        out = []
        for v in sorted(vals):
            if out and v - out[-1][-1] <= tol:
                out[-1].append(v)
            else:
                out.append([v])
        return [sum(c) / len(c) for c in out]
    return cluster([c.placement[0] for c in cols]), cluster([c.placement[1] for c in cols])


def site_sheet(elements: list[DesignElement]) -> _Sheet:
    sh = _Sheet("D1 site plan")
    for e in elements:
        p, k = e.params, e.kind
        if k == "wall" and p.get("wall_kind") == "ext":
            sh.poly(_wall_pts(e), "A-WALL")
        elif k == "slab" and p.get("polygon_mm") and e.level == "B":
            sh.poly([tuple(v) for v in p["polygon_mm"]], "A-FLOR-OTLN")
        elif k == "slab" and not p.get("polygon_mm"):
            sh.poly(_rect_pts(e.placement[0], e.placement[1], e.size[0], e.size[1], e.rotation_deg), "A-FLOR-OTLN")
        elif k == "garden":
            sh.poly([tuple(v) for v in p["polygon_mm"]], "L-SITE")
            poly = p["polygon_mm"]
            sh.text(str(p.get("role") or e.id), (sum(v[0] for v in poly) / len(poly), sum(v[1] for v in poly) / len(poly)), 150, "L-SITE")
        elif k == "plant":
            sh.circle((e.placement[0], e.placement[1]), max(e.size[0], 100.0) / 2, "L-PLNT")
        elif k == "context":
            sh.poly(_rect_pts(e.placement[0], e.placement[1], e.size[0], e.size[1], e.rotation_deg), "X-CNTX")
        elif k == "column":
            sh.poly(_rect_pts(e.placement[0], e.placement[1], e.size[0], e.size[1], e.rotation_deg), "S-COLS")
        elif k == "railing" and p.get("path_mm"):
            sh.poly([(v[0], v[1]) for v in p["path_mm"]], "A-FLOR-HRAL", closed=False)
    _grid(sh, elements)
    return sh


def write_dxfs(elements: list[DesignElement], out_dir: Path | str, design: str = "D1") -> dict:
    out = Path(out_dir)
    info = {}
    for name, sh in (("B", level_sheet(elements, "B")), ("GF", level_sheet(elements, "GF")), ("SITE", site_sheet(elements))):
        path = out / f"{design}-{name}.dxf"
        errs, fixes = sh.save(path)
        info[path.name] = dict(path=path, audit_errors=errs, audit_fixes=fixes, entities_by_layer=dict(sorted(sh.counts.items())))
    return info
