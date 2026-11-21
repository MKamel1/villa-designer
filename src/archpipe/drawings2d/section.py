"""Sections and elevations from a built scene: analytic cut (poche) + Blender Line Art for the visible projection.

Frame: a view looks along horizontal unit vector `d` (model frame, metres, scene z). Sheet horizontal axis
u = d x z (what is on the viewer's right), vertical = scene z. A section keeps the far side of the plane
`d . (p - p0) >= 0`; an elevation keeps everything. The cut is computed here (not by Blender): faces are sliced by the
plane, segments carry orientation from the face normal, polygonize + winding number give the solid poche, so the cut
needs no mesh-boolean. Visible edges beyond the cut come from Line Art (hidden-line removal is not hand-rolled);
strokes lying on the cut plane are dropped (the analytic outline replaces them).
"""
from __future__ import annotations

import json
import math
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import polygonize, unary_union

BLENDER = Path.home() / "opt" / "blender" / "blender"
LINEART_SCRIPT = Path(__file__).resolve().parents[1] / "blender" / "lineart_view.py"
Z_REVIT = 1.2                     # Revit level = scene z + 1.2 m
EPS = 1e-6


@dataclass(frozen=True)
class View:
    name: str
    kind: str                      # "section" | "elevation"
    d: tuple[float, float, float]  # horizontal unit view direction (model frame)
    p0: tuple[float, float]        # a point on the cut plane (model x, y metres); elevations: origin
    window: tuple[float, float, float, float]    # u0, z0, u1, z1 metres (crop)
    sheet: str = ""
    scale: float = 100.0

    @property
    def u_axis(self) -> tuple[float, float]:
        return (self.d[1], -self.d[0])            # d x z for horizontal d = (dy, -dx, 0)

    def uz(self, p) -> tuple[float, float]:
        ux, uy = self.u_axis
        return (p[0] * ux + p[1] * uy, p[2])

    def depth(self, p) -> float:
        return (p[0] - self.p0[0]) * self.d[0] + (p[1] - self.p0[1]) * self.d[1]


def clip_far(faces: list[list], view: View) -> list[list]:
    """Sutherland-Hodgman against the plane, keeping depth >= 0 (the far side)."""
    out = []
    for f in faces:
        pts = f["p"] if isinstance(f, dict) else f
        res = []
        for i, a in enumerate(pts):
            b = pts[(i + 1) % len(pts)]
            da, db = view.depth(a), view.depth(b)
            if da >= 0:
                res.append(a)
            if (da >= 0) != (db >= 0):
                t = da / (da - db)
                res.append([a[k] + t * (b[k] - a[k]) for k in range(3)])
        if len(res) >= 3:
            out.append(res)
    return out


def _normal(pts):
    n = np.zeros(3)
    for i in range(len(pts)):
        a, b = np.array(pts[i]), np.array(pts[(i + 1) % len(pts)])
        n += np.cross(a, b)
    return n


def slice_faces(faces: list[dict], view: View) -> list[tuple]:
    """Oriented cut segments ((u0,z0),(u1,z1), material) where faces cross the plane. Coplanar faces are skipped."""
    segs = []
    for f in faces:
        pts = f["p"]
        ds = [view.depth(p) for p in pts]
        if max(ds) - min(ds) < EPS or max(ds) < 0 or min(ds) > 0:
            continue
        cross = []
        for i, a in enumerate(pts):
            b = pts[(i + 1) % len(pts)]
            da, db = ds[i], ds[(i + 1) % len(pts)]
            if (da < 0) != (db < 0) or da == 0:
                if da == db:
                    continue
                t = da / (da - db)
                cross.append(tuple(a[k] + t * (b[k] - a[k]) for k in range(3)))
        cross = sorted(set((round(c[0], 5), round(c[1], 5), round(c[2], 5)) for c in cross),
                       key=lambda c: (c[0] * view.u_axis[0] + c[1] * view.u_axis[1], c[2]))
        if len(cross) < 2:
            continue
        n = _normal(pts)
        dn = np.array([view.d[0], view.d[1], 0.0])
        t3 = np.cross(n, dn)                                 # direction of the cut edge, oriented by the outward normal
        for a, b in zip(cross[::2], cross[1::2]):
            ua, ub = view.uz(a), view.uz(b)
            tv = np.array([view.u_axis[0] * t3[0] + view.u_axis[1] * t3[1], t3[2]])
            if np.dot(tv, [ub[0] - ua[0], ub[1] - ua[1]]) < 0:
                ua, ub = ub, ua
            if math.dist(ua, ub) > EPS:
                segs.append((ua, ub, f["m"]))
    return segs


def _winding(segs: np.ndarray, pt) -> int:
    x, y = pt
    a, b = segs[:, 0:2], segs[:, 2:4]
    up = (a[:, 1] <= y) & (b[:, 1] > y)
    dn = (b[:, 1] <= y) & (a[:, 1] > y)
    side = (b[:, 0] - a[:, 0]) * (y - a[:, 1]) - (x - a[:, 0]) * (b[:, 1] - a[:, 1])
    return int(np.sum(up & (side > 0)) - np.sum(dn & (side < 0)))


def poche(segs: list[tuple]) -> list[Polygon]:
    """Solid regions of the cut: polygonize the noded segments, keep faces with nonzero winding (overlapping solids union;
    touching solids' shared faces cancel)."""
    if not segs:
        return []
    lines = unary_union([LineString([s[0], s[1]]) for s in segs])
    arr = np.array([[s[0][0], s[0][1], s[1][0], s[1][1]] for s in segs])
    keep = []
    for poly in polygonize(lines):
        if poly.area < 1e-7:
            continue
        if _winding(arr, poly.representative_point().coords[0]) != 0:
            keep.append(poly)
    return keep


def run_lineart(faces: list[list], view: View, *, ortho: float = 60.0, timeout: int = 600) -> list[list]:
    """Line Art strokes as 3D polylines (metres). Needs Blender 4.5 (headless)."""
    cx, cy = view.p0
    spec = {"faces": faces, "dir": [view.d[0], view.d[1], 0.0], "origin": [cx, cy, 0.0], "ortho_scale": ortho, "back": 80.0}
    with tempfile.TemporaryDirectory() as td:
        i, o = Path(td) / "in.json", Path(td) / "out.json"
        i.write_text(json.dumps(spec))
        r = subprocess.run([str(BLENDER), "-b", "--factory-startup", "-P", str(LINEART_SCRIPT), "--", str(i), str(o)],
                           capture_output=True, text=True, timeout=timeout)
        if r.returncode or not o.exists():
            raise RuntimeError("Blender line art failed:\n" + r.stdout[-1500:] + r.stderr[-1500:])
        return json.loads(o.read_text())["strokes"]


def build_view(slim: dict, view: View, strokes_fn=run_lineart) -> dict:
    """Everything needed to draw one view, in view coordinates (u, z metres)."""
    faces = slim["faces"]
    if view.kind == "section":
        segs = slice_faces(faces, view)
        far = clip_far(faces, view)
    else:
        segs, far = [], [f["p"] for f in faces]
    strokes = strokes_fn(far, view)
    lines = []
    for s in strokes:
        pts = [(view.uz(p), view.depth(p)) for p in s]
        if view.kind == "section" and all(abs(d) < 0.004 for _, d in pts):
            continue                                        # lies on the cut plane: replaced by the analytic outline
        lines.append({"uz": [q for q, _ in pts], "depth": [d for _, d in pts]})
    return {"view": view, "cut_segments": segs, "poche": poche(segs), "lines": lines}
