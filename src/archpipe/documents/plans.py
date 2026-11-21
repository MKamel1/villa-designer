"""Model-generated plan sheets (vector PDF / SVG): the fallback drawing set when Revit cannot run.

Every sheet carries the banner "GENERATED FROM THE DESIGN MODEL": the geometry is drawn from the L2 design model
(`archpipe.model.load("D1")`), not from a Revit view, so it is not evidence of BM1 (Revit as the source).
It does give DS1-DS4 / SC1 something to measure: title block, grids, levels, room tags with name and area,
door/window tags, overall + grid + opening dimension chains on every exterior wall, bilingual titles.

`render_plan()` returns a report (tags drawn, dimension chains drawn) so `qa()` can count untagged elements and
undimensioned exterior walls without re-reading the image.
"""
from __future__ import annotations

import math
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Arc, Circle, Polygon, Rectangle  # noqa: E402

from archpipe.contracts import DesignElement  # noqa: E402

from archpipe.drawings2d import orient, standard  # noqa: E402

from . import arabic, names, schedules  # noqa: E402

PAPER = (420.0, 297.0)
SCALE = 100.0            # 1:100
PT = 25.4 / 72.0         # mm per point
STRIP = 88.0             # title-block strip width (right)
LEFT, EDGE = 20.0, 10.0
BANNER_AR = "مولّد من نموذج التصميم"

matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["svg.fonttype"] = "none"
matplotlib.rcParams["font.family"] = ["DejaVu Sans"]   # has Arabic presentation forms; installed on Windows and Linux alike


def _pip(pt, poly) -> bool:
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _level_geometry(els: list[DesignElement], level: str) -> dict:
    walls = [e for e in els if e.kind == "wall" and e.level == level]
    rooms = [e for e in els if e.kind == "room" and e.level == level]
    xs = [v for w in walls for v in (w.params["x0_mm"], w.params["x1_mm"])]
    ys = [v for w in walls for v in (w.params["y0_mm"], w.params["y1_mm"])]
    return {"walls": walls, "rooms": rooms,
            "doors": [e for e in els if e.kind == "door" and e.level == level],
            "windows": [e for e in els if e.kind == "window" and e.level == level],
            "columns": [e for e in els if e.kind == "column" and e.level in (level, "B")],
            "stairs": [e for e in els if e.kind == "stair" and (e.level == level or (level == "GF" and e.level == "B"))],
            "level": level,
            "bbox": (min(xs), min(ys), max(xs), max(ys))}


def _cluster(vals: list[float], tol: float = 250.0) -> list[float]:
    out: list[list[float]] = []
    for v in sorted(vals):
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return [round(sum(c) / len(c)) for c in out]


def grid_lines(els: list[DesignElement]) -> dict[str, list[float]]:
    """Structural grid derived from the column centres (ST1 grid): x lines lettered, y lines numbered."""
    cols = [e for e in els if e.kind == "column"]
    return {"x": _cluster([c.placement[0] for c in cols]), "y": _cluster([c.placement[1] for c in cols])}


def outward_normal(w: DesignElement, geo: dict) -> tuple[float, float]:
    p = w.params
    dx, dy = p["x1_mm"] - p["x0_mm"], p["y1_mm"] - p["y0_mm"]
    L = math.hypot(dx, dy) or 1.0
    n = (-dy / L, dx / L)
    mx, my = (p["x0_mm"] + p["x1_mm"]) / 2, (p["y0_mm"] + p["y1_mm"]) / 2
    d = p["thickness_mm"] / 2 + 450
    sides = []
    for s in (1, -1):
        pt = (mx + s * n[0] * d, my + s * n[1] * d)
        sides.append(any(_pip(pt, r.params["polygon_mm"]) for r in geo["rooms"]))
    if sides[0] != sides[1]:
        return (-n[0], -n[1]) if sides[0] else n
    bx0, by0, bx1, by1 = geo["bbox"]
    c = ((bx0 + bx1) / 2, (by0 + by1) / 2)
    return n if (mx - c[0]) * n[0] + (my - c[1]) * n[1] > 0 else (-n[0], -n[1])


class _Sheet:
    """One sheet: paper size (mm) and plan scale (denominator) are per sheet; `p` maps client-frame mm to paper mm."""

    def __init__(self, ox: float, oy: float, x0: float, y0: float, paper=PAPER, scale: float = SCALE):
        self.paper, self.scale = paper, float(scale)
        self.fig = plt.figure(figsize=(paper[0] / 25.4, paper[1] / 25.4), facecolor="white")
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, paper[0])
        self.ax.set_ylim(0, paper[1])
        self.ax.axis("off")
        self.ox, self.oy, self.x0, self.y0 = ox, oy, x0, y0

    def p(self, x, y):
        return (self.ox + (x - self.x0) / self.scale, self.oy + (y - self.y0) / self.scale)

    def line(self, a, b, lw=0.3, color="k", ls="-", z=3):
        self.ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=lw, ls=ls, zorder=z, solid_capstyle="butt")

    def text(self, xy, s, size=5.0, ha="center", va="center", rot=0, color="k", z=8, weight="normal", bg=False):
        s = arabic.visual(s)
        kw = {"bbox": dict(fc="white", ec="none", pad=0.15, alpha=0.85)} if bg else {}
        self.ax.text(xy[0], xy[1], s, fontsize=size, ha=ha, va=va, rotation=rot, color=color, zorder=z,
                     weight=weight, **kw)


def _wall_poly(p: dict) -> list[tuple[float, float]]:
    a, b = (p["x0_mm"], p["y0_mm"]), (p["x1_mm"], p["y1_mm"])
    L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
    n = (-u[1], u[0])
    h = p["thickness_mm"] / 2
    return [(a[0] - u[0] * h + n[0] * h, a[1] - u[1] * h + n[1] * h), (b[0] + u[0] * h + n[0] * h, b[1] + u[1] * h + n[1] * h),
            (b[0] + u[0] * h - n[0] * h, b[1] + u[1] * h - n[1] * h), (a[0] - u[0] * h - n[0] * h, a[1] - u[1] * h - n[1] * h)]


def _draw_walls(sh: _Sheet, geo: dict) -> None:
    """Cut walls: exterior solid, interior hatched (core material is not authored, so the hatch says 'structure')."""
    for w in geo["walls"]:
        p = w.params
        ext = p["wall_kind"] == "ext"
        sh.ax.add_patch(Polygon([sh.p(*q) for q in _wall_poly(p)], closed=True, fc="#222222" if ext else "#e8e8e8",
                                ec="k", lw=standard.lw("cut", sh.scale), hatch=None if ext else "//////", zorder=2))


def _wall_of(geo: dict, host: str):
    return next((w for w in geo["walls"] if w.id == host), None)


def _side_toward(geo: dict, e: DesignElement, n: tuple[float, float], room_id: str) -> int:
    room = next((r for r in geo["rooms"] if r.room == room_id), None)
    if room is None:
        return 1
    for s in (1, -1):
        pt = (e.placement[0] + s * n[0] * 600, e.placement[1] + s * n[1] * 600)
        if _pip(pt, room.params["polygon_mm"]):
            return s
    return 1


def _opening_frame(e: DesignElement, geo: dict):
    w = _wall_of(geo, e.host)
    t = w.params["thickness_mm"] if w else e.size[1]
    horizontal = abs(math.sin(math.radians(e.rotation_deg))) < 0.5
    u = (1.0, 0.0) if horizontal else (0.0, 1.0)
    n = (-u[1], u[0])
    return u, n, t


def _draw_openings(sh: _Sheet, geo: dict, rep: dict, flag_judgement: bool = False) -> None:
    for e in geo["windows"] + geo["doors"]:
        u, n, t = _opening_frame(e, geo)
        wd = e.size[0]
        cx, cy = e.placement[0], e.placement[1]
        a = (cx - u[0] * wd / 2, cy - u[1] * wd / 2)
        b = (cx + u[0] * wd / 2, cy + u[1] * wd / 2)
        h = t / 2 + 20
        gap = [(a[0] + n[0] * h, a[1] + n[1] * h), (b[0] + n[0] * h, b[1] + n[1] * h),
               (b[0] - n[0] * h, b[1] - n[1] * h), (a[0] - n[0] * h, a[1] - n[1] * h)]
        sh.ax.add_patch(Polygon([sh.p(*q) for q in gap], closed=True, fc="white", ec="none", zorder=4))
        thin = standard.lw("fine", sh.scale)
        if e.kind == "window":
            for k in (-1, 0, 1):
                off = k * t / 3
                sh.line(sh.p(a[0] + n[0] * off, a[1] + n[1] * off), sh.p(b[0] + n[0] * off, b[1] + n[1] * off), lw=thin, z=5)
            continue
        op = e.params.get("operation")
        for off in (-t / 4, t / 4):
            sh.line(sh.p(a[0] + n[0] * off, a[1] + n[1] * off), sh.p(b[0] + n[0] * off, b[1] + n[1] * off), lw=thin, z=5)
        if op == "sliding" or e.params.get("garden"):
            # second leaf drawn offset, with a short arrow showing the travel
            o = t / 4
            m = (cx + n[0] * o, cy + n[1] * o)
            sh.line(sh.p(m[0] - u[0] * wd / 2, m[1] - u[1] * wd / 2), sh.p(m[0], m[1]), lw=standard.lw("proj", sh.scale), z=5)
            continue
        if op == "pocket":
            sh.line(sh.p(*a), sh.p(*b), lw=thin, ls=(0, (3, 2)), z=5)
            continue
        hx = e.params.get("hinge_xy_mm")
        if hx:
            ha, fa = (a, b) if math.dist(a, hx[:2]) <= math.dist(b, hx[:2]) else (b, a)
        else:
            ha, fa = a, b
        into = e.params.get("swing_into") or e.room
        s_ = _side_toward(geo, e, n, into)
        leaf_end = (ha[0] + s_ * n[0] * wd, ha[1] + s_ * n[1] * wd)
        sh.line(sh.p(*ha), sh.p(*leaf_end), lw=standard.lw("proj", sh.scale), z=5)
        ang0 = math.degrees(math.atan2(s_ * n[1], s_ * n[0]))
        ang1 = math.degrees(math.atan2(fa[1] - ha[1], fa[0] - ha[0]))
        d = (ang0 - ang1 + 180) % 360 - 180
        lo, hi = sorted((d, 0.0))
        sh.ax.add_patch(Arc(sh.p(*ha), 2 * wd / sh.scale, 2 * wd / sh.scale, theta1=ang1 + lo, theta2=ang1 + hi,
                            lw=thin, color="k", zorder=5))
        rep.setdefault("swings", []).append({"id": e.id, "hinge_xy": [round(ha[0]), round(ha[1])],
                                              "leaf_end": [round(leaf_end[0]), round(leaf_end[1])]})
    if flag_judgement:
        for e in geo["doors"]:
            if e.params.get("judgement"):
                u, n, t = _opening_frame(e, geo)
                sd = _side_toward(geo, e, n, e.params.get("swing_into") or e.room)
                c = sh.p(e.placement[0] + sd * n[0] * (t / 2 + 1000), e.placement[1] + sd * n[1] * (t / 2 + 1000))
                sh.ax.add_patch(Circle(c, 2.2, fc="#ffe9f3", ec="#c2185b", lw=0.4, zorder=9))
                sh.text(c, "?", size=5, color="#c2185b", z=10, weight="bold")
                rep.setdefault("handing_flags", []).append(e.id)


def _draw_stairs_columns(sh: _Sheet, geo: dict, *, existing_distinct: bool = False) -> None:
    for c in geo["columns"]:
        x, y = c.placement[0], c.placement[1]
        w, d = c.size[0], c.size[1]
        keep = existing_distinct and c.params.get("existing_id")
        sh.ax.add_patch(Rectangle(sh.p(x - w / 2, y - d / 2), w / sh.scale, d / sh.scale,
                                  fc="#d9c3f0" if keep else "#444444", ec="#6a1b9a" if keep else "k",
                                  lw=standard.lw("cut", sh.scale), hatch="xxxx" if keep else None, zorder=3))
    for st in geo["stairs"]:
        allb = st.params["tread_boxes_mm"]
        lvl = geo.get("level")
        boxes = allb if lvl == "B" else allb[len(allb) // 2:]      # on GF only the upper half of the flight is seen
        for box in boxes:
            x0, y0, _, x1, y1, _ = box
            sh.ax.add_patch(Rectangle(sh.p(x0, y0), (x1 - x0) / sh.scale, (y1 - y0) / sh.scale, fc="none", ec="k",
                                      lw=standard.lw("fine", sh.scale), zorder=3))
        b0, b1 = boxes[0], boxes[-1]
        # the flight rises from the first tread toward the last; the arrow points UP the stair on the walking line
        c0 = ((b0[0] + b0[3]) / 2, (b0[1] + b0[4]) / 2)
        c1 = ((b1[0] + b1[3]) / 2, (b1[1] + b1[4]) / 2)
        up = lvl == "B"             # the stair climbs from B to GF: UP on B; on GF the same flight is seen arriving (DN)
        a, z = (c0, c1) if up else (c1, c0)
        sh.ax.annotate("", xy=sh.p(*z), xytext=sh.p(*a), arrowprops=dict(arrowstyle="->", lw=0.4), zorder=6)
        sh.ax.add_patch(Circle(sh.p(*a), 0.9, fc="k", ec="k", zorder=6))
        sh.text(sh.p(c0[0] + 0.0, c0[1] - 450), "UP" if up else "DN", size=4, z=6)
        # break line across the flight at 1.0 m of rise (plan convention: the cut plane crosses the stair)
        mid = boxes[len(boxes) // 2]
        horiz = abs(mid[3] - mid[0]) < abs(mid[4] - mid[1])
        cx, cy = (mid[0] + mid[3]) / 2, (mid[1] + mid[4]) / 2
        if horiz:
            sh.line(sh.p(cx - 700, cy - 120), sh.p(cx, cy + 120), lw=standard.lw("proj", sh.scale), z=6)
            sh.line(sh.p(cx, cy + 120), sh.p(cx + 700, cy - 120), lw=standard.lw("proj", sh.scale), z=6)
        else:
            sh.line(sh.p(cx - 120, cy - 700), sh.p(cx + 120, cy), lw=standard.lw("proj", sh.scale), z=6)
            sh.line(sh.p(cx + 120, cy), sh.p(cx - 120, cy + 700), lw=standard.lw("proj", sh.scale), z=6)


def _tags(sh: _Sheet, geo: dict, tagmap: dict[str, str], rep: dict, rooms_only: bool = False) -> None:
    for r in geo["rooms"]:
        poly = r.params["polygon_mm"]
        cx, cy = r.placement[0], r.placement[1]
        small = min(r.size[0], r.size[1]) < 1500 or r.params["area_m2"] < 3.0
        name = names.short_en(r.params["name"])
        if sum(1 for q in geo["rooms"] if names.short_en(q.params["name"]) == name) > 1:
            name = (r.params["name"][:1].upper() + r.params["name"][1:])[:48]
        ar = names.room_ar(r.room)
        area = "%.2f m²" % r.params.get("net_area_m2", r.params["area_m2"])
        tag = tagmap[r.id]
        if small:
            sh.text(sh.p(cx, cy), "%s\n%s" % (tag, area), size=3.6, bg=True)
        else:
            lines = textwrap.wrap(name, max(12, int(r.size[0] / 1000 * 3.2)))[:3]
            sh.text(sh.p(cx, cy + 250), "\n".join(lines), size=5.2, weight="bold", bg=True)
            if ar:
                sh.text(sh.p(cx, cy - 330 - 120 * (len(lines) - 1)), ar, size=5.0, bg=True)
            sh.text(sh.p(cx, cy - 750 - 120 * (len(lines) - 1)), "%s  %s" % (tag, area), size=4.6, bg=True)
        rep["room_tags"].append({"id": r.id, "tag": tag})
    for kind, items, shape in (("door", geo["doors"], "circle"), ("window", geo["windows"], "hex")):
        for e in items:
            u, n, t = _opening_frame(e, geo)
            side = _side_toward(geo, e, n, e.room)
            off = t / 2 + 330
            x, y = e.placement[0] + side * n[0] * off, e.placement[1] + side * n[1] * off
            c = sh.p(x, y)
            r = 1.9
            if shape == "circle":
                sh.ax.add_patch(Circle(c, r, fc="white", ec="k", lw=0.3, zorder=7))
            else:
                sh.ax.add_patch(Polygon([(c[0] + r * math.cos(math.radians(60 * i + 30)), c[1] + r * math.sin(math.radians(60 * i + 30)))
                                         for i in range(6)], closed=True, fc="white", ec="k", lw=0.3, zorder=7))
            sh.text(c, tagmap[e.id], size=3.4, z=9)
            rep[kind + "_tags"].append({"id": e.id, "tag": tagmap[e.id]})


def _chain(sh: _Sheet, rep: dict, vals: list[float], fixed: float, horizontal: bool, kind: str, owner: str,
           label_size: float = 3.8) -> None:
    """Draw a dimension chain through sorted model coordinates `vals` at model coordinate `fixed` on the other axis."""
    vals = sorted(vals)
    pts = [sh.p(v, fixed) if horizontal else sh.p(fixed, v) for v in vals]
    sh.line(pts[0], pts[-1], lw=0.2, z=6)
    for q in pts:
        sh.line((q[0] - 0.9, q[1] - 0.9), (q[0] + 0.9, q[1] + 0.9), lw=0.35, z=6)
        # extension line stub
        if horizontal:
            sh.line((q[0], q[1] - 1.4), (q[0], q[1] + 1.4), lw=0.12, z=6)
        else:
            sh.line((q[0] - 1.4, q[1]), (q[0] + 1.4, q[1]), lw=0.12, z=6)
    segs = [round(vals[i + 1] - vals[i]) for i in range(len(vals) - 1)]
    labels = standard.eq_label(segs)
    for i, lab in enumerate(labels):
        mid = ((pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2)
        if horizontal:
            sh.text((mid[0], mid[1] + 1.2), lab, size=label_size, z=7)
        else:
            sh.text((mid[0] - 1.2, mid[1]), lab, size=label_size, rot=90, z=7)
    rep["dimensions"].append({"kind": kind, "owner": owner, "segments_mm": segs, "total_mm": round(vals[-1] - vals[0])})


def _dimensions(sh: _Sheet, geo: dict, grid: dict, rep: dict) -> None:
    bx0, by0, bx1, by1 = geo["bbox"]
    side_walls: dict[str, list[DesignElement]] = {"N": [], "S": [], "E": [], "W": []}
    for w in geo["walls"]:
        if w.params["wall_kind"] != "ext":
            continue
        n = outward_normal(w, geo)
        side = ("E" if n[0] > 0 else "W") if abs(n[0]) > 0.5 else ("N" if n[1] > 0 else "S")
        side_walls[side].append(w)
        p = w.params
        horizontal = abs(p["y1_mm"] - p["y0_mm"]) < 1
        lo, hi = (min(p["x0_mm"], p["x1_mm"]), max(p["x0_mm"], p["x1_mm"])) if horizontal else (
            min(p["y0_mm"], p["y1_mm"]), max(p["y0_mm"], p["y1_mm"]))
        cuts = [lo, hi]
        for e in geo["doors"] + geo["windows"]:
            if e.host == w.id:
                c = e.placement[0] if horizontal else e.placement[1]
                cuts += [max(lo, c - e.size[0] / 2), min(hi, c + e.size[0] / 2)]
        cuts = sorted(set(round(v) for v in cuts))
        fixed = (p["y0_mm"] if horizontal else p["x0_mm"]) + (n[1] if horizontal else n[0]) * (p["thickness_mm"] / 2 + 6.5 * sh.scale)
        _chain(sh, rep, cuts, fixed, horizontal, "opening", w.id)
    rep["wall_side"] = {s: [w.id for w in ws] for s, ws in side_walls.items()}
    gx = [v for v in grid["x"] if bx0 - 300 <= v <= bx1 + 300]
    gy = [v for v in grid["y"] if by0 - 300 <= v <= by1 + 300]
    for side in "NSEW":
        horizontal = side in "NS"
        sgn = 1 if side in "NE" else -1
        edge = (by1 if side == "N" else by0) if horizontal else (bx1 if side == "E" else bx0)
        gfix, ofix = edge + sgn * 20 * sh.scale, edge + sgn * 31 * sh.scale
        lo, hi = (bx0, bx1) if horizontal else (by0, by1)
        gvals = sorted(set([lo] + [v for v in (gx if horizontal else gy)] + [hi]))
        _chain(sh, rep, gvals, gfix, horizontal, "grid", side)
        _chain(sh, rep, [lo, hi], ofix, horizontal, "overall", side)
    # Grid lines and bubbles on N and W (letters along x, numbers along y).
    letters = "ABCDEFGHJK"
    for i, x in enumerate(gx):
        a, b = sh.p(x, by0 - 9 * sh.scale), sh.p(x, by1 + 9 * sh.scale)
        sh.line(a, b, lw=0.12, ls=(0, (8, 2, 1, 2)), z=1, color="#c0392b")
        sh.ax.add_patch(Circle((b[0], b[1] + 2.6), 2.4, fc="white", ec="#c0392b", lw=0.3, zorder=7))
        sh.text((b[0], b[1] + 2.6), letters[i], size=5, color="#c0392b", z=9)
    for i, y in enumerate(gy):
        a, b = sh.p(bx0 - 9 * sh.scale, y), sh.p(bx1 + 9 * sh.scale, y)
        sh.line(a, b, lw=0.12, ls=(0, (8, 2, 1, 2)), z=1, color="#c0392b")
        sh.ax.add_patch(Circle((a[0] - 2.6, a[1]), 2.4, fc="white", ec="#c0392b", lw=0.3, zorder=7))
        sh.text((a[0] - 2.6, a[1]), str(i + 1), size=5, color="#c0392b", z=9)
    rep["grid"] = {"x": gx, "y": gy}


def _nice_bar(scale: float) -> float:
    """Graphic-scale bar length in metres: the largest of 1,2,5,10,20 m that is at most 60 mm on paper."""
    return max([m for m in (0.2, 0.5, 1, 2, 5, 10, 20) if m * 1000 / scale <= 60] or [0.2])


def _north_scale(sh: _Sheet, geo: dict, level: str, levels: dict, *, true_north: bool = False) -> None:
    bx0, by0, bx1, by1 = geo["bbox"]
    sc = sh.scale
    # client north (street side) is up in the sheet frame; pinned to paper position relative to the plan
    nx, ny = sh.p(bx1 + 10 * sc, by1 + 4 * sc)
    sh.ax.add_patch(Polygon([(nx, ny + 9), (nx - 3, ny), (nx + 3, ny)], closed=True, fc="k", ec="k", lw=0.3, zorder=6))
    sh.text((nx, ny + 11.5), "N", size=7, weight="bold")
    sh.text((nx, ny - 3.5), "north (street side)", size=3.5)
    if true_north:
        # secondary: true north, 20 degrees from the model frame; drawn dashed and labelled
        ang = math.radians(orient.TRUE_NORTH_DEG)
        tx, ty = nx + 20, ny
        sh.line((tx, ty), (tx + 9 * math.sin(ang), ty + 9 * math.cos(ang)), lw=0.5, ls=(0, (3, 1.5)), z=6)
        sh.text((tx + 9 * math.sin(ang) + 4, ty + 9 * math.cos(ang) + 2), "true N", size=3.6)
    bar = _nice_bar(sc)
    seg = bar / 5
    sx, sy = sh.p(bx0, by0 - 14 * sc)
    wmm = seg * 1000 / sc
    for i in range(5):
        sh.ax.add_patch(Rectangle((sx + i * wmm, sy), wmm, 1.4, fc="k" if i % 2 == 0 else "white", ec="k", lw=0.25, zorder=6))
    for i in range(6):
        sh.text((sx + i * wmm, sy - 2.2), ("%g" % (i * seg)), size=3.6)
    sh.text((sx + 5 * wmm + 2, sy + 0.7), "m", size=3.6, ha="left")
    sh.text((sx, sy + 4), "Graphic scale 1:%g" % sc, size=4, ha="left")
    ffl = levels[level]["ffl_revit_mm"] if level in levels else None
    if ffl is not None:
        lx, ly = sh.p(bx0 - 38 * sc / 10, by1 + 15 * sc / 10)
        sh.ax.add_patch(Polygon([(lx, ly), (lx + 3.2, ly + 4.5), (lx - 3.2, ly + 4.5)], closed=True, fc="k", ec="k", lw=0.3, zorder=6))
        sh.line((lx - 6, ly), (lx + 18, ly), lw=0.3, z=6)
        sh.text((lx + 7, ly + 3.2), "FFL %+.2f" % (ffl / 1000.0), size=4.5, ha="left")


def _title_block(sh: _Sheet, spec: dict, sheet: dict, page: int, pages: int) -> None:
    PAPER = sh.paper
    x1 = PAPER[0] - EDGE
    x0 = x1 - STRIP
    y0, y1 = EDGE, PAPER[1] - EDGE
    ax = sh.ax
    ax.add_patch(Rectangle((LEFT, y0), x1 - LEFT, y1 - y0, fc="none", ec="k", lw=0.9, zorder=10))
    ax.add_patch(Rectangle((x0, y0), STRIP, y1 - y0, fc="white", ec="k", lw=0.6, zorder=10))
    pr = spec["project"]
    na = lambda v: v if v else "NOT SUPPLIED"       # noqa: E731
    rows = [(("Project", "المشروع"), pr["project"]),
            (("Owner", "المالك"), na(pr["owner"])),
            (("Address", "العنوان"), pr["address"]),
            (("Engineer", "المهندس"), na(pr["engineer"])),
            (("Syndicate no.", "رقم النقابة"), na(pr["syndicate_no"]))]
    y = y1
    ax.add_patch(Rectangle((x0, y1 - 14), STRIP, 14, fc="#b00020", ec="k", lw=0.6, zorder=10))
    sh.text((x0 + STRIP / 2, y1 - 7), "GENERATED FROM THE DESIGN MODEL", size=6.5, color="white", weight="bold", z=12)
    sh.text((x0 + STRIP / 2, y1 - 11.5), BANNER_AR, size=5, color="white", z=12)
    y = y1 - 14
    for k, v in rows:
        y -= 14
        ax.plot([x0, x1], [y, y], color="k", lw=0.3, zorder=11)
        sh.text((x0 + 2, y + 11), k[0], size=3.8, ha="left", color="#444444", z=12)
        sh.text((x1 - 2, y + 11), k[1], size=3.8, ha="right", color="#444444", z=12)
        wrapped = "\n".join(textwrap.wrap(v, 34)[:2])
        sh.text((x0 + 2, y + 5), wrapped, size=5.4 if len(v) < 34 else 4.6, ha="left", z=12,
                color="#b00020" if v == "NOT SUPPLIED" else "k")
    y -= 4
    sh.text((x0 + 2, y - 4), "Drawing title", size=3.8, ha="left", color="#444444", z=12)
    sh.text((x1 - 2, y - 4), "اسم اللوحة", size=3.8, ha="right", color="#444444", z=12)
    sh.text((x0 + 2, y - 11), "\n".join(textwrap.wrap(sheet["title_en"], 30)), size=7.5, ha="left", weight="bold", z=12, va="center")
    sh.text((x0 + STRIP - 2, y - 24), sheet["title_ar"], size=7.5, ha="right", z=12)
    y -= 36
    ax.plot([x0, x1], [y, y], color="k", lw=0.3, zorder=11)
    cells = [("Sheet no.", sheet["no"]), ("Scale", sheet["scale"]), ("Paper", sheet.get("paper", "A3 landscape").split()[0]), ("Date", spec["project"]["date"])]
    for i, (k, v) in enumerate(cells):
        cx = x0 + (i % 2) * STRIP / 2
        cy = y - 11 * (i // 2)
        sh.text((cx + 2, cy - 3), k, size=3.8, ha="left", color="#444444", z=12)
        sh.text((cx + 2, cy - 8), v, size=7 if k == "Sheet no." else 5.5, ha="left", weight="bold" if k == "Sheet no." else "normal", z=12)
    ax.plot([x0 + STRIP / 2, x0 + STRIP / 2], [y, y - 22], color="k", lw=0.3, zorder=11)
    y -= 22
    ax.plot([x0, x1], [y, y], color="k", lw=0.3, zorder=11)
    sh.text((x0 + 2, y - 4), "Revision table", size=3.8, ha="left", color="#444444", z=12)
    sh.text((x1 - 2, y - 4), "جدول التعديلات", size=3.8, ha="right", color="#444444", z=12)
    sh.text((x0 + 2, y - 9), "Rev  %s   %s   draft issue 1 of %d" % (pr["revision"], pr["date"], pages), size=5, ha="left", z=12)
    sh.text((x0 + 2, y - 14), "Location: " + pr["revision_location"], size=4.2, ha="left", z=12)
    y -= 18
    ax.plot([x0, x1], [y, y], color="k", lw=0.3, zorder=11)
    sh.text((x0 + 2, y - 5), "Issue sequence: %d of %d" % (page, pages), size=5, ha="left", z=12)
    sh.text((x0 + 2, y - 11), "Status: DRAFT, not issued for permit", size=5, ha="left", z=12, color="#b00020")
    sh.text((x0 + 2, y - 17), "Not signed or stamped by an engineer", size=4.6, ha="left", z=12)
    sh.text((x0 + 2, y - 28), "Source: archpipe design model %s (L2)" % spec["design"], size=4.2, ha="left", z=12, color="#444444")
    sh.text((x0 + 2, y - 33), "Arabic text unreviewed (pipeline-written).", size=4.2, ha="left", z=12, color="#444444")
    # white background is the figure's own; make it explicit in the vector too
    ax.add_patch(Rectangle((0, 0), PAPER[0], PAPER[1], fc="white", ec="none", zorder=-5))


def x_title_ar(paper=PAPER) -> float:
    return paper[0] - EDGE - STRIP - 4


def parse_scale(txt: str) -> float:
    return float(txt.split(":")[1])


def render_plan(els: list[DesignElement], spec: dict, sheet: dict, out_stem: Path | str, *, page: int = 1,
                pages: int = 1, formats=("pdf", "svg", "png"), layers: tuple[str, ...] = ("tags", "dims"),
                crop: tuple[float, float, float, float] | None = None, extras=None) -> dict:
    """Draw one plan sheet from MODEL-frame elements (`els`); the client-north rotation is applied here.

    `sheet` carries no, level, scale ("1:100"), paper ("A3 landscape"), titles. `layers` selects what is drawn:
    tags, dims, furniture, luminaires, colorfill, handing, existing, truenorth. `crop` is (x0, y0, x1, y1) in the
    CLIENT frame (east, north) mm for enlarged callouts. `extras(sh, geo, rep, cels)` draws sheet-specific content.
    """
    paper = standard.PAPERS[sheet.get("paper", "A3 landscape").split()[0]]
    scale = parse_scale(sheet["scale"])
    cels = orient.to_client(els)
    level = sheet["level"]
    geo = _level_geometry(cels, level)
    levels = _model_levels(spec)
    bx0, by0, bx1, by1 = crop or geo["bbox"]
    geo["bbox"] = (bx0, by0, bx1, by1)
    avail_x0, avail_x1 = LEFT + (44 if not crop else 10), paper[0] - EDGE - STRIP - 10
    ox = avail_x0 + (avail_x1 - avail_x0 - (bx1 - bx0) / scale) / 2
    oy = EDGE + (paper[1] - 2 * EDGE - (by1 - by0) / scale) / 2 - 8
    sh = _Sheet(ox, oy, bx0, by0, paper=paper, scale=scale)
    rep = {"sheet": sheet["no"], "level": level, "room_tags": [], "door_tags": [], "window_tags": [], "dimensions": [],
           "scale": scale, "layers": list(layers), "frame": "client-north-up"}
    tagmap = schedules.tag_numbers(els)
    if crop:
        sh.ax.set_clip_on(True)
    from archpipe.drawings2d import layers as L

    if "colorfill" in layers:
        rep["colour_legend"] = L.colour_fill(sh, geo["rooms"])
    _draw_walls(sh, geo)
    _draw_stairs_columns(sh, geo, existing_distinct="existing" in layers)
    _draw_openings(sh, geo, rep, flag_judgement="handing" in layers)
    if "furniture" in layers:
        rep["furniture_drawn"] = L.furniture(sh, cels, level)
    if "luminaires" in layers:
        rep["luminaire_legend"] = L.luminaires(sh, cels, level, rep)
    if "tags" in layers:
        _tags(sh, geo, tagmap, rep, rooms_only=("colorfill" in layers or "luminaires" in layers))
    if "dims" in layers:
        _dimensions(sh, geo, grid_lines(cels), rep)
    if "scalebar" in layers or not crop:
        _north_scale(sh, geo, level, levels, true_north="truenorth" in layers)
    if extras:
        extras(sh, geo, rep, cels)
    _title_block(sh, spec, sheet, page, pages)
    sh.text((LEFT + 4, paper[1] - EDGE - 5), sheet["title_en"], size=9, ha="left", weight="bold")
    sh.text((x_title_ar(paper), paper[1] - EDGE - 5), sheet["title_ar"], size=9, ha="right", weight="bold")
    sh.text((LEFT + 4, paper[1] - EDGE - 10.5), "%s at %s.  GENERATED FROM THE DESIGN MODEL (no Revit).  North is the street side."
            % (sheet["scale"], sheet.get("paper", "A3 landscape").split()[0]), size=5, ha="left", color="#b00020")
    sh.text((x_title_ar(paper), paper[1] - EDGE - 10.5), BANNER_AR, size=5, ha="right", color="#b00020")
    stem = Path(out_stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    rep["files"] = []
    for fmt in formats:
        p = stem.with_suffix("." + fmt)
        sh.fig.savefig(p, dpi=110 if fmt == "png" else None, facecolor="white")
        rep["files"].append(p.name)
    plt.close(sh.fig)
    return rep


def _model_levels(spec: dict) -> dict:
    return spec.get("levels") or {"B": {"ffl_revit_mm": -1800}, "GF": {"ffl_revit_mm": 1200}}


def readback_pdf_tags(pdf_path: Path | str) -> set[str]:
    """Tag strings (D01, W01, R01) actually present as text in the exported PDF: the read-back, independent of the draw lists."""
    import re
    try:
        import pymupdf as fitz
    except ImportError:  # older PyMuPDF
        import fitz
    doc = fitz.open(str(pdf_path))
    text = "".join(page.get_text() for page in doc)
    doc.close()
    return set(re.findall(r"\b[DWR]\d\d\b", text))


def qa(els: list[DesignElement], rep: dict, pdf_path: Path | str | None = None) -> dict:
    """Count what is untagged and which exterior walls lack a complete dimension chain set (target 0)."""
    level = rep["level"]
    want = {k: {e.id for e in els if e.kind == k and e.level == level} for k in ("door", "window", "room")}
    got = {"door": {t["id"] for t in rep["door_tags"]}, "window": {t["id"] for t in rep["window_tags"]},
           "room": {t["id"] for t in rep["room_tags"]}}
    ext = {e.id for e in els if e.kind == "wall" and e.level == level and e.params.get("wall_kind") == "ext"}
    chained = {d["owner"] for d in rep["dimensions"] if d["kind"] == "opening"}
    sides_ok = {s for s in "NSEW" if {d["kind"] for d in rep["dimensions"] if d["owner"] == s} >= {"grid", "overall"}}
    wall_side = {wid: s for s, ids in rep["wall_side"].items() for wid in ids}
    bad = sorted(w for w in ext if w not in chained or wall_side.get(w) not in sides_ok)
    pdf = {}
    if pdf_path is not None:
        found = readback_pdf_tags(pdf_path)
        tags = schedules.tag_numbers(els)
        pdf = {"pdf_untagged_" + k + "s": len({tags[i] for i in want[k]} - found) for k in want}
    return {**pdf, "sheet": rep["sheet"], "untagged_doors": len(want["door"] - got["door"]),
            "untagged_windows": len(want["window"] - got["window"]), "untagged_rooms": len(want["room"] - got["room"]),
            "exterior_walls": len(ext), "exterior_walls_without_chains": len(bad), "walls_without_chains": bad}
