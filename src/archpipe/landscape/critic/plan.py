"""The common plan-drawing renderer for `landscape-layout/1`: ONE fixed graphic standard for every garden,
so a critic judges the design and not the drafting. `plan_png(layout, path)` is the whole public surface.

Standard (STYLE_VERSION): client NORTH (street, model -x) at the top, east right; metre scale bar; north arrow;
one hatch + colour per surface; planting symbols drawn at MATURE spread, one colour per layer, a legend;
walls black, buildings hatched dark grey; seats, tables, features and doors as fixed glyphs; 1 px = fixed
resolution of 60 px/m clamped so every plan is the same sheet size (width 1600 px).
"""
from __future__ import annotations

import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle, FancyArrow

from .common import extent, plant_positions, rect_poly, species_info, path_line

STYLE_VERSION = "ldc-plan-style/1"
SURFACE = {   # facecolor, hatch
    "paving": ("#d9d4cb", "+"), "lawn": ("#bfe0a0", None), "artificial-turf": ("#a8d18a", "//"),
    "gravel": ("#e6d8b5", "."), "planting": ("#cfe3bd", None), "water": ("#9cc8e8", "~~"), "other": ("#efefef", None),
}
LAYER_COL = {"canopy": "#2e6b34", "understorey": "#5a9a4a", "shrub": "#8ec06c", "ground": "#d3e8a8"}
FEATURE = {"firepit": ("#e0702c", "fire pit"), "heater": ("#e0702c", "heater"), "bbq": ("#555555", "BBQ"),
           "pond": ("#5fa8d8", "pond"), "herb_bed": ("#6b8e3a", "herbs"), "fruit_tree": ("#c8a020", "fruit")}
W_PX = 1600


def _xy(p):          # model (x south, y east) -> plot (east right, north up)
    return (p[1], -p[0])


def _rect_patch(r, **kw):
    x0, y0, x1, y1 = r
    pts = [_xy((x0, y0)), _xy((x0, y1)), _xy((x1, y1)), _xy((x1, y0))]
    return Polygon(pts, closed=True, **kw)


def plan_png(layout: dict, path: str, title: str | None = None, dpi: int = 100, view: list | None = None) -> str:
    """`view` = [x0, y0, x1, y1] model metres to crop to (default: everything in the layout)."""
    x0, y0, x1, y1 = view or extent(layout, pad=1.2)
    w_m, h_m = (y1 - y0), (x1 - x0)                          # plot width = y span, height = x span
    fig_w = W_PX / dpi
    fig_h = max(4.0, min(fig_w * 1.25, fig_w * h_m / w_m + 1.6))
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
    ax.set_aspect("equal"); ax.set_xlim(y0, y1); ax.set_ylim(-x1, -x0)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values(): sp.set_visible(False)
    clip = _rect_patch((x0, y0, x1, y1), fill=False, ec="none"); ax.add_patch(clip)

    def add(patch, z):
        patch.set_zorder(z); ax.add_patch(patch); patch.set_clip_path(clip); return patch

    for b in layout.get("buildings", []):
        add(_rect_patch(b, fc="#8a8a8a", ec="#333333", hatch="///", lw=1.2), 1)
    for z in layout.get("zones", []):
        if z.get("rect"):
            fc, h = SURFACE.get(z.get("surface", "other"), SURFACE["other"])
            add(_rect_patch(z["rect"], fc=fc, ec="#9a9a9a", hatch=h, lw=0.8, ls=(0, (4, 3))), 2)
    for a in layout.get("paved_areas", []):
        if a.get("rect"):
            add(_rect_patch(a["rect"], fc=SURFACE["paving"][0], ec="#8a8a8a", hatch="+", lw=0.8), 3)
    for g in layout.get("planting_groups", []):
        if g.get("rect"):
            add(_rect_patch(g["rect"], fc="#d6c7a4", ec="#7a6a48", lw=0.9), 3)
    for p in layout.get("paths", []):
        ln = path_line(p)
        if ln is None: continue
        wm = p.get("width_m", 1.0)
        pts = [_xy(q) for q in ln.coords]
        pts_pt = wm * (fig_w * dpi / (y1 - y0)) * 72 / dpi          # metres -> points
        ax.plot([q[0] for q in pts], [q[1] for q in pts], color="#c9b79a", lw=pts_pt, solid_capstyle="butt", zorder=4)
        ax.plot([q[0] for q in pts], [q[1] for q in pts], color="#8d7a5a", lw=0.8, ls=":", zorder=4)
    for f in layout.get("features", []):
        col, lab = FEATURE.get(f.get("kind"), ("#cccccc", f.get("kind", "?")))
        if f.get("rect"):
            add(_rect_patch(f["rect"], fc=col, ec="#222", lw=1, alpha=.85), 5); cx = ((f["rect"][0] + f["rect"][2]) / 2, (f["rect"][1] + f["rect"][3]) / 2)
        else:
            cx = f["center"]; r = (f.get("diameter_m") or max(f.get("size_m", [1, 1]))) / 2
            ax.add_patch(Circle(_xy(cx), r, fc=col, ec="#222", lw=1, alpha=.85, zorder=5))
        ax.text(*_xy(cx), lab, ha="center", va="center", fontsize=7, zorder=9, color="#111")
    for s in layout.get("seating", []):
        if s.get("rect"): add(_rect_patch(s["rect"], fc="#7a5230", ec="#2a1a0a", lw=.8), 6)
    for t in layout.get("tables", []):
        c = t["center"]; r = (t.get("diameter_m") or max(t.get("size_m", [1, 1]))) / 2
        ax.add_patch(Circle(_xy(c), r, fc="#c89a5e", ec="#2a1a0a", lw=1, zorder=6))
    for sc in layout.get("screens", []) + layout.get("canopies", []):
        if sc.get("rect"):
            kind = sc.get("kind", "")
            if sc.get("canopy") or kind == "pergola":
                add(_rect_patch(sc["rect"], fill=False, ec="#4a3a2a", lw=1.4, ls=(0, (6, 2))), 8)
            elif kind == "hedge":
                add(_rect_patch(sc["rect"], fc="#3f7d3a", ec="#1f4a1c", lw=.8), 6)
            else:
                add(_rect_patch(sc["rect"], fc="#555", ec="#111", lw=.8), 6)
    for wl in layout.get("walls", []):
        if wl.get("rect"): add(_rect_patch(wl["rect"], fc="#111111", ec="#111111", lw=.6), 7)
    for d in layout.get("doors", []):
        c = d["at"]; ax.plot(*_xy(c), marker="D", ms=6, mfc="#fff", mec="#b00020", mew=1.4, zorder=9)
    pls = plant_positions(layout)
    for q in sorted(pls, key=lambda q: -q["spread"]):
        r = q["spread"] / 2
        ax.add_patch(Circle(_xy(q["at"]), r, fc=LAYER_COL[q["layer"]], ec="#1d4a22", lw=.7, alpha=.78 if q["layer"] != "canopy" else .55, zorder=10))
        if q["layer"] == "canopy":
            ax.plot(*_xy(q["at"]), marker="+", color="#1d4a22", ms=7, zorder=11)
    for t in layout.get("trees", []):
        ax.text(*_xy(t["center"]), t["species"].split()[0][:10], fontsize=6.5, ha="center", va="top", zorder=12, color="#10300f")
    for z in layout.get("zones", []):
        if z.get("rect") and z.get("use") and z.get("label", True):
            c = ((z["rect"][0] + z["rect"][2]) / 2, (z["rect"][1] + z["rect"][3]) / 2)
            ax.text(*_xy(c), z.get("label") or z["use"], fontsize=8, ha="center", va="center", color="#555", style="italic", zorder=13)
    for p in layout.get("paths", []):
        ln = path_line(p)
        if ln is not None and p.get("class") == "main":
            pass
    # scale bar (bottom-left), 1:1 metres
    L = 5 if (y1 - y0) > 12 else 2
    bx, by = y0 + .4, -x1 + .4
    for k in range(L):
        ax.add_patch(Rectangle((bx + k, by), 1, .18, fc="#000" if k % 2 == 0 else "#fff", ec="#000", lw=.8, zorder=20))
    ax.text(bx, by + .3, "0", fontsize=7, zorder=20); ax.text(bx + L, by + .3, f"{L} m", fontsize=7, ha="center", zorder=20)
    # client-north arrow (top-right)
    ax_, ay_ = y1 - .8, -x0 - 2.0
    ax.add_patch(FancyArrow(ax_, ay_, 0, 1.2, width=.18, head_width=.5, head_length=.4, fc="#000", ec="#000", zorder=20))
    ax.text(ax_, ay_ + 1.45, "N (street)", fontsize=8, ha="center", zorder=20)
    # legend: layers + surfaces
    handles = [Rectangle((0, 0), 1, 1, fc=LAYER_COL[k], ec="#1d4a22") for k in LAYER_COL]
    labs = ["canopy tree", "small tree", "shrub", "ground / perennial"]
    for k, (fc, h) in SURFACE.items():
        if k in {z.get("surface") for z in layout.get("zones", [])}:
            handles.append(Rectangle((0, 0), 1, 1, fc=fc, hatch=h, ec="#888")); labs.append(k)
    ax.legend(handles, labs, loc="upper center", bbox_to_anchor=(.5, -0.01), ncol=4, fontsize=7, frameon=False)
    ax.set_title(title or layout.get("id", "garden plan"), fontsize=10)
    for t in ax.texts:
        if t.get_zorder() < 20: t.set_clip_on(True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path
