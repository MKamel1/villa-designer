"""A-100 site plan from the design model: plot, street, neighbours, sister villa, apartment above, sunken yard, gardens,
kept existing columns, set-back distances. Client frame (street side north). No survey exists: the plot line is the
fence's outer face and the neighbours are the model's ASSUMED boxes; the sheet says so.
"""
from __future__ import annotations

import math

from matplotlib.patches import Circle, Polygon, Rectangle

from archpipe.contracts import DesignElement
from archpipe.documents import plans

from . import orient, standard


def _box_poly(e: DesignElement):
    cx, cy, (w, d) = e.placement[0], e.placement[1], (e.size[0], e.size[1])
    return [(cx - w / 2, cy - d / 2), (cx + w / 2, cy - d / 2), (cx + w / 2, cy + d / 2), (cx - w / 2, cy + d / 2)]


def plot_rect(cels: list[DesignElement]) -> tuple[float, float, float, float]:
    xs, ys = [], []
    for e in cels:
        if e.id.startswith("ctx-fence-"):
            for x, y in _box_poly(e):
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def setbacks(els: list[DesignElement]) -> dict[str, float]:
    """GF envelope (the villa body above the sunken yard) to the plot line in metres, client compass.

    The basement yard retaining walls run out to within 0.35 m of the fence (see `retaining_to_plot_m`), so the GF body
    is the set-back that matters for the villa; W is to the plot's outer fence (the sister villa lies between).
    """
    cels = orient.to_client(els)
    px0, py0, px1, py1 = plot_rect(cels)
    walls = [e for e in cels if e.kind == "wall" and e.level == "GF"]
    xs = [v for w in walls for v in (w.params["x0_mm"], w.params["x1_mm"])]
    ys = [v for w in walls for v in (w.params["y0_mm"], w.params["y1_mm"])]
    bx0, by0, bx1, by1 = min(xs), min(ys), max(xs), max(ys)
    return {"E": (px1 - bx1) / 1000.0, "W": (bx0 - px0) / 1000.0, "N": (py1 - by1) / 1000.0, "S": (by0 - py0) / 1000.0}


def render_site(els, spec, sheet, out_stem, *, page=1, pages=1, formats=("pdf", "svg", "png")) -> dict:
    paper = standard.PAPERS[sheet["paper"].split()[0]]
    scale = plans.parse_scale(sheet["scale"])
    cels = orient.to_client(els)
    px0, py0, px1, py1 = plot_rect(cels)
    # window (client frame mm): the plot with street, the sister's half, and the neighbours' near faces
    wx0, wy0, wx1, wy1 = px0 - 3000, py0 - 5000, px1 + 9000, py1 + 8000
    sh = plans._Sheet(0, 0, wx0, wy0, paper=paper, scale=scale)
    sh.ox = plans.LEFT + 70
    sh.oy = plans.EDGE + (paper[1] - 2 * plans.EDGE - (wy1 - wy0) / scale) / 2 - 6
    ax = sh.ax
    rep = {"sheet": sheet["no"], "kind": "site", "frame": "client-north-up", "scale": scale}
    ctx = [e for e in cels if e.kind == "context" and "-w" not in e.id.split("neighbour-")[-1][:2]]
    ctx = [e for e in cels if e.kind == "context" and not ("-w" in e.id and "-z" in e.id)]

    clip = Rectangle(sh.p(wx0, wy0), (wx1 - wx0) / scale, (wy1 - wy0) / scale, transform=ax.transData, fc="none", ec="none")
    ax.add_patch(clip)

    def poly(pts, **kw):
        pa = Polygon([sh.p(*q) for q in pts], closed=True, **kw)
        ax.add_patch(pa)
        pa.set_clip_path(clip)

    # street
    for e in ctx:
        w = e.params.get("what")
        if w == "street":
            poly(_box_poly(e), fc="#d8d8d8", ec="none", zorder=1)
            c = sh.p(e.placement[0], e.placement[1])
            sh.text(c, "STREET (width ASSUMED)", size=5, color="#555555")
    # sunken yard / gardens
    gardens = [e for e in cels if e.kind == "garden"]
    for g in gardens:
        poly(g.params["polygon_mm"], fc="#cfe8c4", ec="#4c7a34", lw=standard.lw("proj", scale), zorder=1, hatch=None)
    # neighbours, sister, apartment, core, steps
    heights = {}
    for e in ctx:
        w = e.params.get("what")
        z0, z1 = e.params.get("z0_scene_mm"), e.params.get("z1_scene_mm")
        if w == "neighbour":
            poly(_box_poly(e), fc="#ececec", ec="#777777", lw=standard.lw("ctx", scale), hatch="..", zorder=2)
            c = sh.p(*e.placement[:2])
            h = (z1 - z0) / 1000.0
            sh.text(c, "NEIGHBOUR\n%.1f m high\n(plot ASSUMED mirrored)" % h, size=5, color="#444444")
            heights[e.id] = h
        elif w == "sister" and e.id == "ctx-sister":
            poly(_box_poly(e), fc="#e0e0e0", ec="#555555", lw=standard.lw("ctx", scale), hatch="////", zorder=2)
            sh.text(sh.p(*e.placement[:2]), "SISTER VILLA + apartment\n%.1f m high (not ours)" % ((z1 - z0) / 1000.0), size=5, color="#333333")
        elif w == "core":
            poly(_box_poly(e), fc="#f2f2f2", ec="#888888", lw=standard.lw("ctx", scale), zorder=2)
        elif w == "entrance":
            poly(_box_poly(e), fc="#e9e2d0", ec="#8a7a50", lw=standard.lw("ctx", scale), hatch="---", zorder=2)
            sh.text(sh.p(*e.placement[:2]), "shared entrance steps", size=3.6)
    # plot line (fence outer face): dashed heavy
    poly([(px0, py0), (px1, py0), (px1, py1), (px0, py1)], fc="none", ec="#b00020", lw=standard.lw("cut", scale), ls=(0, (6, 3)), zorder=6)
    fy = lambda e: e                                          # noqa: E731
    for e in ctx:
        if e.params.get("what") == "fence":
            poly(_box_poly(e), fc="#999999", ec="k", lw=standard.lw("proj", scale), zorder=4)
        if e.params.get("what") == "yard":
            poly(_box_poly(e), fc="#999999", ec="k", lw=standard.lw("proj", scale), zorder=4)
    # plants
    for e in cels:
        if e.kind == "plant":
            r = max(e.size[0], 300) / 2 / scale
            ax.add_patch(Circle(sh.p(*e.placement[:2]), r, fc="#9ccc84", ec="#4c7a34", lw=0.12, alpha=0.7, zorder=3))
    # apartment above: dashed footprint of the GF walls
    geo_gf = plans._level_geometry(cels, "GF")
    geo_b = plans._level_geometry(cels, "B")
    for w in geo_b["walls"]:
        poly(plans._wall_poly(w.params), fc="#cccccc", ec="#555555", lw=standard.lw("proj", scale), zorder=5)
    for w in geo_gf["walls"]:
        poly(plans._wall_poly(w.params), fc="#222222", ec="k", lw=standard.lw("cut", scale), zorder=6)
    for c in geo_b["columns"]:
        keep = bool(c.params.get("existing_id"))
        ax.add_patch(Rectangle(sh.p(c.placement[0] - c.size[0] / 2, c.placement[1] - c.size[1] / 2), c.size[0] / scale, c.size[1] / scale,
                               fc="#d9c3f0" if keep else "#444", ec="#6a1b9a", lw=0.3, hatch="xxxx", zorder=7))
    sb = setbacks(els)
    bx = [v for w in geo_gf["walls"] for v in (w.params["x0_mm"], w.params["x1_mm"])]
    by = [v for w in geo_gf["walls"] for v in (w.params["y0_mm"], w.params["y1_mm"])]
    bx0, bx1, by0, by1 = min(bx), max(bx), min(by), max(by)
    mx = (bx0 + bx1) / 2
    my = (by0 + by1) / 2
    for side, (a, b) in {"E": ((bx1, my), (px1, my)), "W": ((bx0, my), (px0, my)), "N": ((mx, by1), (mx, py1)), "S": ((mx, by0), (mx, py0))}.items():
        pa, pb = sh.p(*a), sh.p(*b)
        ax.annotate("", xy=pb, xytext=pa, arrowprops=dict(arrowstyle="<->", lw=0.4, color="#b00020"), zorder=8)
        sh.text(((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2 + 1.5), "%s set-back %.2f m" % (side, sb[side]), size=3.8, color="#b00020", bg=True)
    sh.text(sh.p(mx, my - 3500), "OUR VILLA\nB -1.80 / GF +1.20\n(apartment above: not ours, +4.20)", size=5, weight="bold", bg=True)
    # annotation: levels, plot, sources
    notes = ["Plot %.2f x %.2f m to the fence outer face (plot line ASSUMED: no survey)." % ((px1 - px0) / 1000, (py1 - py0) / 1000),
             "Sunken yard -1.80 (Revit datum; scene -3.00). Fence top +2.20. Street level +/-0.00.",
             "Street facade faces true azimuth 290 degrees; site coordinates are placeholders (spec/villa-site.yaml).",
             "Kept existing columns: purple cross-hatch. Neighbours and sister villa are ASSUMED boxes (brief), not surveyed.",
             "Set-backs are from the GF wall centre-lines to the plot line (fence outer face); the basement yard retaining walls run closer."]
    for i, t in enumerate(notes):
        sh.text((plans.LEFT + 6, plans.EDGE + 18 - i * 4.2), t, size=4.2, ha="left")
    rep["setbacks_m"] = {k: round(v, 3) for k, v in sb.items()}
    rep["neighbour_heights_m"] = heights
    rep["plot_mm"] = [px0, py0, px1, py1]
    geo = {"bbox": (px0, py0, px1, py1)}
    plans._north_scale(sh, geo, "SITE", {}, true_north=True)
    return plans.finish_sheet(sh, spec, sheet, page, pages, out_stem, formats, rep)
