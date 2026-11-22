"""The common plan-drawing renderer for `landscape-layout/1`: ONE fixed graphic standard (STYLE_VERSION) for every garden,
so a critic judges the design and not the drafting. `plan_png(layout, path)` is the whole public surface.

Standard `ldc-plan-style/2` (landscape-architecture plan conventions; sources in docs/lanes/LDC.md):
  * client NORTH (street, model -x) up; scale bar, north arrow and title outside the drawing (Time-Saver Standards for
    Landscape Architecture, 2nd ed., section 110 p. 110-8: "scale, date and north arrow ... required in all plan drawings");
  * trees = circle at MATURE spread + trunk dot + cast shadow (shadow falls down-right on the sheet);
  * shrubs, perennials, ground cover = massed DRIFT outlines (union of the plants' mature spreads), one hatch per species;
  * paving = joint pattern in true metres (unit paving in running bond, timber deck boards, gravel stipple, turf ticks);
  * water = ripple lines, with the child-protection grille outlined; pergola = dashed overhead outline + beams + posts;
  * furniture in outline (white fill), level changes = step treads + fall arrow, or hachured retaining line;
  * every label sits OUTSIDE the drawing on a leader; a plant key with codes (T tree, S shrub, G ground) and a symbol key below.
"""
from __future__ import annotations

import hashlib
import math
import random

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle, Polygon, Rectangle
from shapely.geometry import MultiPolygon, Point
from shapely.ops import unary_union

from .common import extent, plant_positions, rect_poly, species_info, path_line

STYLE_VERSION = "ldc-plan-style/2"
INK = "#1d1d1d"
GREEN = "#1d4a22"
LAYER_FILL = {"canopy": (0.18, 0.42, 0.20, .38), "understorey": (0.35, 0.60, 0.29, .38), "shrub": (0.56, 0.75, 0.42, .55), "ground": (0.78, 0.90, 0.55, .55)}
HATCHES = ["////", "\\\\\\\\", "xxxx", "....", "oo", "++", "---", "|||", "**", "OO"]
SURFACE_FILL = {"paving": "#e4dfd6", "lawn": "#d6ebc0", "artificial-turf": "#cfe4b8", "gravel": "#ece1c2", "planting": "#e9dfc9", "water": "#bcd9ee", "other": None}
SURFACE_KIND = {"paving": "unit", "lawn": "turf", "artificial-turf": "turf", "gravel": "gravel", "water": "water"}
FEATURE_NAME = {"firepit": "fire pit", "heater": "patio heater", "bbq": "BBQ", "pond": "pond", "herb_bed": "herb bed", "fruit_tree": "fruit tree"}
FIG_W = 16.0           # inches at dpi 100 = 1600 px
PLAN_W_IN, PLAN_H_MAX_IN = 9.6, 15.0
SHADOW = (0.22, -0.22)  # of the canopy radius, plot axes (east right, north up)


def _xy(p):          # model (x south, y east) -> plot (east right, north up)
    return (p[1], -p[0])


def _rect_pts(r):
    x0, y0, x1, y1 = r
    return [_xy((x0, y0)), _xy((x0, y1)), _xy((x1, y1)), _xy((x1, y0))]


def _kind_of(material: str) -> str:
    m = (material or "").lower()
    if any(k in m for k in ("deck", "timber", "wood")): return "deck"
    if any(k in m for k in ("gravel", "pebble", "stabil")): return "gravel"
    if any(k in m for k in ("turf", "lawn", "grass")): return "turf"
    if "water" in m: return "water"
    return "unit"


def _pattern_segments(kind, bounds, seed):
    """Material pattern as line segments / points in plot metres inside `bounds` = (xmin, ymin, xmax, ymax)."""
    xa, ya, xb, yb = bounds
    segs, pts = [], []
    if kind == "unit":            # 0.6 x 0.3 m units, running bond
        row, y = 0, ya
        while y <= yb + 1e-9:
            segs.append(((xa, y), (xb, y)))
            x = xa + (0.3 if row % 2 else 0.0)
            while x <= xb:
                segs.append(((x, y), (x, min(y + 0.3, yb)))); x += 0.6
            y += 0.3; row += 1
    elif kind == "deck":          # 140 mm boards along the long side
        if (xb - xa) >= (yb - ya):
            y = ya
            while y <= yb: segs.append(((xa, y), (xb, y))); y += 0.14
        else:
            x = xa
            while x <= xb: segs.append(((x, ya), (x, yb))); x += 0.14
    elif kind == "gravel":
        rnd = random.Random(seed)
        pts = [(rnd.uniform(xa, xb), rnd.uniform(ya, yb)) for _ in range(int(35 * (xb - xa) * (yb - ya)))]
    elif kind == "turf":
        rnd = random.Random(seed)
        for _ in range(int(5 * (xb - xa) * (yb - ya))):
            x, y = rnd.uniform(xa, xb), rnd.uniform(ya, yb)
            segs += [((x, y), (x - .05, y + .12)), ((x, y), (x + .05, y + .12))]
    elif kind == "water":         # ripple lines
        y = ya + .12
        while y < yb:
            x = xa; prev = (x, y + .04 * math.sin(0))
            while x < xb:
                x += .1; cur = (x, y + .04 * math.sin(x * 9)); segs.append((prev, cur)); prev = cur
            y += .22
    return segs, pts


def _seed(*a):
    return int(hashlib.md5(repr(a).encode()).hexdigest()[:8], 16)


class _Canvas:
    def __init__(self, ax, ov, s, px0, py0, x0, y0, x1, y1):
        self.ax, self.ov, self.s, self.px0, self.py0 = ax, ov, s, px0, py0
        self.view = (x0, y0, x1, y1)
        self.labels = []          # (anchor_plot_xy, text, kw)

    def inch(self, pt):           # plot metres -> overlay inches
        return (self.px0 + (pt[0] - self.view[1]) * self.s, self.py0 + (pt[1] + self.view[2]) * self.s)

    def inside(self, pt):
        return self.view[1] <= pt[0] <= self.view[3] and -self.view[2] <= pt[1] <= -self.view[0]

    def label(self, pt_model, text, **kw):
        p = _xy(pt_model)
        if self.inside(p): self.labels.append((p, text, kw))

    def poly(self, pts, z, **kw):
        p = Polygon(pts, closed=True, zorder=z, **kw); self.ax.add_patch(p); return p

    def pattern(self, patch_pts, kind, color, z, lw=.45, seed=0):
        clip = Polygon(patch_pts, closed=True, fill=False, ec="none"); self.ax.add_patch(clip)
        xs, ys = [q[0] for q in patch_pts], [q[1] for q in patch_pts]
        segs, pts = _pattern_segments(kind, (min(xs), min(ys), max(xs), max(ys)), seed)
        if segs:
            lc = LineCollection(segs, colors=color, linewidths=lw, zorder=z); self.ax.add_collection(lc); lc.set_clip_path(clip)
        if pts:
            sc = self.ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=1.2, c=color, linewidths=0, zorder=z); sc.set_clip_path(clip)


def _display(sp):
    return sp.replace("_", " ").capitalize() if "_" in sp or sp.islower() else sp


def plan_png(layout: dict, path: str, title: str | None = None, dpi: int = 100, view: list | None = None) -> str:
    """`view` = [x0, y0, x1, y1] model metres to crop to (default: everything in the layout)."""
    x0, y0, x1, y1 = view or extent(layout, pad=1.2)
    W, H = (y1 - y0), (x1 - x0)
    s = min(PLAN_W_IN / W, PLAN_H_MAX_IN / H)
    pw, ph = W * s, H * s

    # ---- what goes in the keys (decided before sizing the sheet)
    pls = plant_positions(layout)
    species = {}
    for q in pls: species.setdefault(q["species"], q["layer"])
    prefix = {"canopy": "T", "understorey": "T", "shrub": "S", "ground": "G"}
    codes, count = {}, {}
    for sp, ly in sorted(species.items(), key=lambda kv: (["canopy", "understorey", "shrub", "ground"].index(kv[1]), kv[0])):
        count[prefix[ly]] = count.get(prefix[ly], 0) + 1
        codes[sp] = f"{prefix[ly]}{count[prefix[ly]]}"
    hatch_of = {sp: HATCHES[i % len(HATCHES)] for i, sp in enumerate(codes)}
    sym = []
    if any(b for b in layout.get("buildings", [])): sym.append(("building (context)", "bld"))
    if layout.get("paved_areas") or any(z.get("surface") == "paving" for z in layout.get("zones", [])): sym.append(("unit paving, running bond joints", "unit"))
    if any(_kind_of(a.get("material", "")) == "deck" for a in layout.get("paved_areas", [])): sym.append(("timber deck boards", "deck"))
    if any(_kind_of(a.get("material", "")) == "gravel" for a in layout.get("paved_areas", [])) or any(z.get("surface") == "gravel" for z in layout.get("zones", [])): sym.append(("gravel", "gravel"))
    if any(z.get("surface") in ("lawn", "artificial-turf") for z in layout.get("zones", [])): sym.append(("lawn / turf", "turf"))
    if any(f.get("kind") == "pond" for f in layout.get("features", [])): sym.append(("water: ripple, grille dashed", "water"))
    if layout.get("canopies"): sym.append(("pergola: dashed, beams, posts", "perg"))
    if layout.get("seating") or layout.get("tables"): sym.append(("furniture in outline", "furn"))
    if layout.get("steps") or layout.get("level_changes"): sym.append(("step treads / hachure: level change", "steps"))
    if layout.get("walls"): sym.append(("wall", "wall"))
    if layout.get("doors"): sym.append(("door", "door"))
    sym.append(("tree: canopy, trunk dot, shadow", "tree"))
    n_rows = math.ceil(len(codes) / 2)
    key_h = 0.45 + n_rows * 0.25 + 0.5 + math.ceil(len(sym) / 3) * 0.25 + 0.3
    top, bottom = 0.7, 0.9 + key_h
    fig_h = top + ph + bottom
    px0 = (FIG_W - pw) / 2; py0 = bottom
    fig = plt.figure(figsize=(FIG_W, fig_h), dpi=dpi)
    ax = fig.add_axes([px0 / FIG_W, py0 / fig_h, pw / FIG_W, ph / fig_h])
    ax.set_xlim(y0, y1); ax.set_ylim(-x1, -x0); ax.set_aspect("auto")
    ax.set_xticks([]); ax.set_yticks([])
    for sp_ in ax.spines.values(): sp_.set_linewidth(.8); sp_.set_color("#777")
    ov = fig.add_axes([0, 0, 1, 1], facecolor="none"); ov.set_xlim(0, FIG_W); ov.set_ylim(0, fig_h); ov.axis("off"); ov.set_zorder(50)
    C = _Canvas(ax, ov, s, px0, py0, x0, y0, x1, y1)
    P = lambda r: _rect_pts(r)

    # ---- ground and surfaces
    seen = set()
    for b in layout.get("buildings", []):
        k = tuple(round(v, 2) for v in b)
        if k in seen: continue
        seen.add(k)
        C.poly(P(b), 1, fc="#7d7d7d", ec=INK, lw=1.2, hatch="///"); (C.label(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), "building (context)") if len(seen) == 1 else None)
    for z in layout.get("zones", []):
        if not z.get("rect"): continue
        fc = SURFACE_FILL.get(z.get("surface", "other"))
        pts = P(z["rect"])
        C.poly(pts, 2, fc=fc or "none", ec="#9a9a9a", lw=.7, ls=(0, (2, 3)))
        kind = SURFACE_KIND.get(z.get("surface"))
        if kind: C.pattern(pts, kind, "#7a8f6a" if kind == "turf" else "#6f87a0" if kind == "water" else "#8e867a", 2.2, seed=_seed(z["rect"]))
        if z.get("use") and z.get("label", True):
            C.label(((z["rect"][0] + z["rect"][2]) / 2, (z["rect"][1] + z["rect"][3]) / 2), z.get("label") or z["use"], style="italic")
    for a in layout.get("paved_areas", []):
        if not a.get("rect"): continue
        pts = P(a["rect"]); kind = _kind_of(a.get("material", ""))
        C.poly(pts, 3, fc=SURFACE_FILL["paving"] if kind == "unit" else "#d8c8a4" if kind == "deck" else SURFACE_FILL["gravel"], ec="#7f786c", lw=.8)
        C.pattern(pts, kind, "#6f685d", 3.2, seed=_seed(a["rect"]))
    for g in layout.get("planting_groups", []):
        if g.get("rect"): C.poly(P(g["rect"]), 3.5, fc="#e6dcc4", ec="#8b7a52", lw=.9)
    for p in layout.get("paths", []):
        ln = path_line(p)
        if p.get("rect") and not p.get("polyline"):
            C.poly(P(p["rect"]), 3.6, fc="#ddd2bc", ec="#8d7a5a", lw=.7)
            C.pattern(P(p["rect"]), "unit", "#8d7a5a", 3.7, seed=_seed(p["rect"]))
        elif ln is not None:
            pts = [_xy(q) for q in ln.coords]
            lw = p.get("width_m", 1.0) * s * 72
            ax.plot([q[0] for q in pts], [q[1] for q in pts], color="#ddd2bc", lw=lw, solid_capstyle="butt", zorder=3.6)
            ax.plot([q[0] for q in pts], [q[1] for q in pts], color="#8d7a5a", lw=.8, ls=":", zorder=3.7)
        if ln is not None and p.get("class") == "main":
            m = ln.interpolate(.5, normalized=True); C.label((m.x, m.y), "main path")
    for st in layout.get("steps", []):                       # level change: treads across the run, arrow down the fall
        if not st.get("rect"): continue
        a, b, c, d = st["rect"]; n = int(st.get("count", 3)); pts = P(st["rect"])
        C.poly(pts, 4, fc="#efece6", ec=INK, lw=.9)
        horiz = abs(c - a) >= abs(d - b)               # run direction in model coords
        for k in range(1, n):
            t = k / n
            seg = ((_xy((a + (c - a) * t, b)), _xy((a + (c - a) * t, d))) if horiz else (_xy((a, b + (d - b) * t)), _xy((c, b + (d - b) * t))))
            ax.plot([seg[0][0], seg[1][0]], [seg[0][1], seg[1][1]], color=INK, lw=.7, zorder=4.1)
        mid = ((a + c) / 2, (b + d) / 2); ln_ = (c - a) if horiz else (d - b)
        tail, head = ((a + c) / 2 - ln_ * .35, (b + d) / 2) if horiz else ((a + c) / 2, (b + d) / 2 - ln_ * .35), ((a + c) / 2 + ln_ * .35, (b + d) / 2) if horiz else ((a + c) / 2, (b + d) / 2 + ln_ * .35)
        if st.get("down") == "start": tail, head = head, tail
        ax.annotate("", xy=_xy(head), xytext=_xy(tail), arrowprops=dict(arrowstyle="-|>", color=INK, lw=.9), zorder=4.2)
        C.label(mid, f"steps x{n} (fall to arrow)")
    for lc_ in layout.get("level_changes", []):              # retaining / sunken edge: bold line with hachure on the low side
        ln = lc_.get("polyline") or []
        if len(ln) < 2: continue
        pts = [_xy(q) for q in ln]
        ax.plot([q[0] for q in pts], [q[1] for q in pts], color=INK, lw=2.2, zorder=4.3)
        for (p0, p1) in zip(pts, pts[1:]):
            L = math.hypot(p1[0] - p0[0], p1[1] - p0[1]); n = max(1, int(L / .25))
            nx, ny = -(p1[1] - p0[1]) / (L or 1), (p1[0] - p0[0]) / (L or 1)
            sgn = -1 if lc_.get("low") == "left" else 1
            ax.add_collection(LineCollection([((p0[0] + (p1[0] - p0[0]) * (k + .5) / n, p0[1] + (p1[1] - p0[1]) * (k + .5) / n),
                                               (p0[0] + (p1[0] - p0[0]) * (k + .5) / n + sgn * nx * .18, p0[1] + (p1[1] - p0[1]) * (k + .5) / n + sgn * ny * .18)) for k in range(n)],
                                              colors=INK, linewidths=.6, zorder=4.3))
        m = ln[len(ln) // 2]; C.label(m, lc_.get("label") or "level change (hachure on the low side)")

    # ---- features (water with ripple + grille, fire, bbq, herbs) and furniture (outline only)
    for f in layout.get("features", []):
        kind = f.get("kind"); name = FEATURE_NAME.get(kind, kind or "feature")
        if f.get("rect"):
            r = f["rect"]; pts = P(r); cen = ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
            if kind == "pond":
                C.poly(pts, 5, fc=SURFACE_FILL["water"], ec="#2f6f9f", lw=1.3)
                C.pattern(pts, "water", "#4f86b3", 5.1, seed=_seed(r))
                if f.get("child_protection") == "rigid_grille":
                    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
                    gx0, gx1, gy0, gy1 = min(xs) + .12, max(xs) - .12, min(ys) + .12, max(ys) - .12
                    ax.add_patch(Rectangle((gx0, gy0), gx1 - gx0, gy1 - gy0, fill=False, ec=INK, lw=1.0, ls=(0, (5, 2)), zorder=5.3))
                    ax.plot([gx0, gx1], [gy0, gy1], color=INK, lw=.6, zorder=5.3); ax.plot([gx0, gx1], [gy1, gy0], color=INK, lw=.6, zorder=5.3)
                    name = "pond (grille outlined)"
            elif kind == "herb_bed":
                C.poly(pts, 5, fc="#e6dcc4", ec="#5f7a2e", lw=1.1); C.pattern(pts, "turf", "#5f7a2e", 5.1, seed=_seed(r))
            else:
                C.poly(pts, 5, fc="white", ec=INK, lw=1.1)
                xs, ys = [q[0] for q in pts], [q[1] for q in pts]
                ax.plot([min(xs), max(xs)], [min(ys), max(ys)], color=INK, lw=.6, zorder=5.2); ax.plot([min(xs), max(xs)], [max(ys), min(ys)], color=INK, lw=.6, zorder=5.2)
        else:
            cen = f["center"]; r = (f.get("diameter_m") or max(f.get("size_m", [1, 1]))) / 2
            if kind == "pond":
                cx_, cy_ = _xy(cen); ring = [(cx_ + r * math.cos(a / 20 * math.pi), cy_ + r * math.sin(a / 20 * math.pi)) for a in range(40)]
                C.poly(ring, 5, fc=SURFACE_FILL["water"], ec="#2f6f9f", lw=1.3); C.pattern(ring, "water", "#4f86b3", 5.1, seed=_seed(cen))
            else:
                ax.add_patch(Circle(_xy(cen), r, fc="white", ec=INK, lw=1.1, zorder=5)); ax.add_patch(Circle(_xy(cen), r * .5, fc="#e8885a", ec=INK, lw=.7, zorder=5.1))
        C.label(cen, name)
    for sw in layout.get("seatwalls", []):
        if sw.get("rect"): C.poly(P(sw["rect"]), 6, fc="white", ec=INK, lw=1.1)
    for sd in layout.get("seating", []):
        if sd.get("rect"):
            C.poly(P(sd["rect"]), 6, fc="white", ec="#5a3a1a", lw=1.0)
    if layout.get("seating"):
        r = [sd["rect"] for sd in layout["seating"] if sd.get("rect")]
        if r:
            mx, my = sum((q[0] + q[2]) / 2 for q in r) / len(r), sum((q[1] + q[3]) / 2 for q in r) / len(r)
            near = min(r, key=lambda q: ((q[0] + q[2]) / 2 - mx) ** 2 + ((q[1] + q[3]) / 2 - my) ** 2)   # anchor on a real seat, not the centroid
            C.label(((near[0] + near[2]) / 2, (near[1] + near[3]) / 2), f"seating ({sum(sd.get('seats', 1) for sd in layout['seating'])} seats)")
    for t in layout.get("tables", []):
        c = t["center"]; sz = t.get("size_m")
        if t.get("diameter_m"):
            rr = t["diameter_m"] / 2; ax.add_patch(Circle(_xy(c), rr, fc="white", ec="#5a3a1a", lw=1.1, zorder=6))
            for k in range(int(t.get("seats", 0))):
                a = 2 * math.pi * k / max(1, int(t["seats"])); ax.add_patch(Rectangle((c[1] + (rr + .28) * math.cos(a) - .22, -(c[0] + (rr + .28) * math.sin(a)) - .22), .44, .44, fc="white", ec="#5a3a1a", lw=.7, zorder=6))
        else:
            sx, sy = sz; C.poly(P([c[0] - sx / 2, c[1] - sy / 2, c[0] + sx / 2, c[1] + sy / 2]), 6, fc="white", ec="#5a3a1a", lw=1.1)
            n = int(t.get("seats", 0)); per = (n + 1) // 2
            for side in (-1, 1):
                for k in range(per if side == -1 else n - per):
                    off = (-sx / 2 + sx * (k + .5) / max(1, per)) if sx >= sy else 0
                    off2 = (-sy / 2 + sy * (k + .5) / max(1, per)) if sy > sx else 0
                    cx_, cy_ = (c[0] + off, c[1] + side * (sy / 2 + .3)) if sx >= sy else (c[0] + side * (sx / 2 + .3), c[1] + off2)
                    p = _xy((cx_, cy_)); ax.add_patch(Rectangle((p[0] - .22, p[1] - .22), .44, .44, fc="white", ec="#5a3a1a", lw=.7, zorder=6))
        C.label(c, f"table ({t.get('seats', '?')} seats)")

    # ---- screens and walls, pergolas
    for sc in layout.get("screens", []):
        if not sc.get("rect"): continue
        kind = sc.get("kind", "")
        if kind == "hedge": C.poly(P(sc["rect"]), 6, fc=(0.35, 0.62, 0.30, .75), ec=GREEN, lw=.9, hatch="oo")
        else: C.poly(P(sc["rect"]), 6, fc="#777", ec=INK, lw=.8)
        C.label(((sc["rect"][0] + sc["rect"][2]) / 2, (sc["rect"][1] + sc["rect"][3]) / 2), f"{kind or 'screen'} {sc.get('height_m', '')} m".strip())
    for wl in layout.get("walls", []):
        if wl.get("rect"): C.poly(P(wl["rect"]), 7, fc=INK, ec=INK, lw=.6)
    for cn in layout.get("canopies", []):
        if not cn.get("rect"): continue
        pts = P(cn["rect"]); xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        xa, xb, ya, yb = min(xs), max(xs), min(ys), max(ys)
        ax.add_patch(Rectangle((xa, ya), xb - xa, yb - ya, fill=False, ec="#4a3a2a", lw=1.4, ls=(0, (6, 2)), zorder=12))
        beams = [];
        if (xb - xa) >= (yb - ya):
            x = xa + .25
            while x < xb: beams.append(((x, ya), (x, yb))); x += .5
        else:
            y = ya + .25
            while y < yb: beams.append(((xa, y), (xb, y))); y += .5
        ax.add_collection(LineCollection(beams, colors="#4a3a2a", linewidths=.55, zorder=12))
        for qx, qy in ((xa, ya), (xa, yb), (xb, ya), (xb, yb)): ax.add_patch(Rectangle((qx - .1, qy - .1), .2, .2, fc=INK, ec=INK, zorder=12.1))
        C.label(((cn["rect"][0] + cn["rect"][2]) / 2, (cn["rect"][1] + cn["rect"][3]) / 2), f"pergola (overhead, {cn.get('height_m', '')} m)" if cn.get("height_m") else "pergola (overhead)")
    for d in layout.get("doors", []):
        ax.plot(*_xy(d["at"]), marker="D", ms=5, mfc="#fff", mec="#b00020", mew=1.3, zorder=13)

    # ---- planting: drifts then trees (shadow, canopy at mature spread, trunk)
    trees = [q for q in pls if q["layer"] in ("canopy", "understorey")]
    drifts = {}
    for q in pls:
        if q["layer"] in ("canopy", "understorey"): continue
        drifts.setdefault((q["group"], q["species"]), []).append(q)
    order = {"shrub": 10, "ground": 10.5}
    for (grp, sp), qs in drifts.items():
        poly = unary_union([Point(_xy(q["at"])).buffer(q["spread"] / 2, 24) for q in qs]).buffer(.12).buffer(-.12)
        ly = qs[0]["layer"]
        for pg in (poly.geoms if isinstance(poly, MultiPolygon) else [poly]):
            if pg.is_empty: continue
            ax.add_patch(Polygon(list(pg.exterior.coords), closed=True, fc=LAYER_FILL[ly], ec=GREEN, lw=1.1, hatch=hatch_of[sp], zorder=order[ly]))
        c = poly.representative_point()
        C.labels.append(((c.x, c.y), codes[sp], {"bold": True}))
    for q in sorted(trees, key=lambda q: -q["spread"]):
        r = q["spread"] / 2; c = _xy(q["at"])
        ax.add_patch(Circle((c[0] + SHADOW[0] * r, c[1] + SHADOW[1] * r), r, fc="#000", alpha=.22, ec="none", zorder=11))
        ax.add_patch(Circle(c, r, fc=LAYER_FILL[q["layer"]], ec=GREEN, lw=1.2, hatch=hatch_of[q["species"]], zorder=11.2))
        ax.add_patch(Circle(c, r * .55, fill=False, ec=GREEN, lw=.6, ls=(0, (3, 2)), zorder=11.3))
        ax.add_patch(Circle(c, .13, fc=INK, ec=INK, zorder=11.4))
        C.labels.append((c, codes[q["species"]], {"bold": True}))

    # ---- labels outside the drawing, on leaders; two columns
    left, right = [], []
    for (pt, text, kw) in C.labels:
        (left if pt[0] < (y0 + y1) / 2 else right).append((C.inch(pt), text, kw))
    for col, sgn in ((left, -1), (right, 1)):
        col.sort(key=lambda t: -t[0][1])
        ys = [t[0][1] for t in col]
        gap = .2
        for _ in range(60):                                   # relax overlaps top to bottom
            moved = False
            for i in range(1, len(ys)):
                if ys[i - 1] - ys[i] < gap: ys[i] = ys[i - 1] - gap; moved = True
            if not moved: break
        shift = max(0, py0 + ph - 0.05 - ys[0]) if ys else 0
        lx = px0 - .2 if sgn < 0 else px0 + pw + .2
        for (anchor, text, kw), yy in zip(col, ys):
            ov.plot([anchor[0], lx - sgn * .03], [anchor[1], yy], color="#555", lw=.45, zorder=1)
            ov.plot([anchor[0]], [anchor[1]], marker="o", ms=2.2, color="#555", zorder=1)
            ov.text(lx, yy, text, fontsize=7.2, ha="right" if sgn < 0 else "left", va="center", style=kw.get("style", "normal"), fontweight="bold" if kw.get("bold") else "normal", color=INK)

    # ---- title, north arrow, scale bar
    ov.text(.4, fig_h - .35, title or layout.get("id", "garden plan"), fontsize=11, fontweight="bold", va="center")
    ov.text(.4, fig_h - .6, f"plan, {STYLE_VERSION}; trees and shrubs at mature spread; client north up", fontsize=7, color="#555", va="center")
    nx, ny = FIG_W - .8, fig_h - .55
    ov.add_patch(Circle((nx, ny), .22, fill=False, ec=INK, lw=1)); ov.annotate("", xy=(nx, ny + .2), xytext=(nx, ny - .2), arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.2))
    ov.text(nx, ny - .33, "N (client north, street)", fontsize=6.5, ha="center", va="top")
    L = 10 if W > 40 else 5 if W > 12 else 2
    bx, by = px0, py0 - .32
    for k in range(L): ov.add_patch(Rectangle((bx + k * s, by), s, .09, fc=INK if k % 2 == 0 else "white", ec=INK, lw=.7))
    ov.text(bx, by + .13, "0", fontsize=6.5, ha="center"); ov.text(bx + L * s, by + .13, f"{L} m", fontsize=6.5, ha="center")

    # ---- plant key (codes) and symbol key
    ky = py0 - .62
    kx0 = .6
    ov.text(kx0, ky, "Plant key (code, species, layer; drawn at mature spread)", fontsize=8, fontweight="bold", va="top")
    items = list(codes.items())
    for i, (sp, code) in enumerate(items):
        col, row = divmod(i, n_rows); x = kx0 + col * 7.6; y = ky - .3 - row * .25
        ly = species[sp]
        ov.add_patch(Rectangle((x, y - .09), .36, .18, fc=LAYER_FILL[ly], ec=GREEN, lw=.9, hatch=hatch_of[sp]))
        sz = f", {max(q['spread'] for q in pls if q['species'] == sp):.1f} m spread drawn"
        ov.text(x + .45, y, f"{code}  {_display(sp)} ({ly}{sz})", fontsize=6.8, va="center", style="italic" if False else "normal")
    ky2 = ky - .3 - n_rows * .25 - .15
    ov.text(kx0, ky2, "Symbols", fontsize=8, fontweight="bold", va="top")
    for i, (txt, k) in enumerate(sym):
        col, row = divmod(i, 3); x = kx0 + col * 5.1; y = ky2 - .3 - row * .25
        box = [(x, y - .09), (x, y + .09), (x + .36, y + .09), (x + .36, y - .09)]
        if k in ("unit", "deck", "gravel", "turf", "water"):
            ov.add_patch(Polygon(box, fc=SURFACE_FILL.get({"unit": "paving", "deck": "paving", "gravel": "gravel", "turf": "lawn", "water": "water"}[k]), ec="#777", lw=.6))
            sg, pt = _pattern_segments(k, (0, 0, .36 / s, .18 / s), 1)
            ov.add_collection(LineCollection([((x + a[0] * s, y - .09 + a[1] * s), (x + b[0] * s, y - .09 + b[1] * s)) for a, b in sg], colors="#666", linewidths=.4))
            if pt: ov.scatter([x + p[0] * s for p in pt], [y - .09 + p[1] * s for p in pt], s=1, c="#666", linewidths=0)
        elif k == "bld": ov.add_patch(Polygon(box, fc="#7d7d7d", ec=INK, lw=.8, hatch="///"))
        elif k == "wall": ov.add_patch(Polygon(box, fc=INK, ec=INK))
        elif k == "perg": ov.add_patch(Rectangle((x, y - .09), .36, .18, fill=False, ec="#4a3a2a", ls=(0, (4, 2)), lw=1.2)); [ov.plot([x + d, x + d], [y - .09, y + .09], color="#4a3a2a", lw=.5) for d in (.09, .18, .27)]
        elif k == "furn": ov.add_patch(Rectangle((x + .04, y - .08), .28, .16, fc="white", ec="#5a3a1a", lw=1))
        elif k == "steps": [ov.plot([x + d, x + d], [y - .09, y + .09], color=INK, lw=.7) for d in (.06, .14, .22, .30)]
        elif k == "door": ov.plot([x + .18], [y], marker="D", ms=5, mfc="#fff", mec="#b00020", mew=1.3)
        elif k == "tree":
            ov.add_patch(Circle((x + .2, y - .02), .09, fc="#000", alpha=.22, ec="none")); ov.add_patch(Circle((x + .18, y), .09, fc=LAYER_FILL["canopy"], ec=GREEN, lw=.9)); ov.add_patch(Circle((x + .18, y), .02, fc=INK))
        ov.text(x + .45, y, txt, fontsize=6.8, va="center")
    fig.savefig(path, dpi=dpi, facecolor="white")
    plt.close(fig)
    return path
