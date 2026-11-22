"""Provisional plan drawing (matplotlib) for the concept plans; replaced by LDC's `plan_png` once that lane merges.

Client north (street) at the top, client east to the right: horizontal axis = model y, vertical axis = model x (down = south).
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle

from . import site as S

LAYER_COL = {"climber": "#7b3f98", "shrub": "#2e7d32", "ground": "#e8a317", "perennial": "#9c27b0", "herb": "#8bc34a", "aquatic": "#00897b", "canopy": "#1b5e20"}
SP_COL = {"salvia_leucantha": "#7e57c2", "gazania_rigens": "#fb8c00", "origanum_majorana": "#9ccc65", "petrea_volubilis": "#5e35b1", "jasminum_sambac": "#f5f5f5",
          "bougainvillea_glabra": "#d81b60", "zantedeschia_aethiopica": "#fffde7", "pittosporum_tobira": "#388e3c", "olea_europaea": "#78909c",
          "punica_granatum": "#ef6c00", "plumeria_rubra": "#f48fb1"}


def _rect(ax, r, **kw):
    x0, y0, x1, y1 = r
    ax.add_patch(Rectangle((y0, x0), y1 - y0, x1 - x0, **kw))        # plot x = model y, plot y = model x


def _zone_axes(ax, L, plan, extent, covers, label):
    """Draw one zone. extent = (y0, y1, x0, x1) in model metres; horizontal axis y, vertical axis x (north up)."""
    from .layout import FENCES
    ax.set_facecolor("#efe9dc")
    y0, y1, x0, x1 = extent
    for name, r in FENCES.items():
        _rect(ax, r, fc="#222", ec="#222", zorder=5)
    _rect(ax, [3.617, -31.3, 22.597, -23.591], fc="#b9b9b9", ec="#555", zorder=1)
    _rect(ax, [-0.123, -23.591, 15.412, -20.601], fc="#cfcfcf", ec="#555", zorder=1)
    _rect(ax, [-0.373, -29.916, -0.123, -20.351], fc="#222", ec="#222", zorder=5)
    _rect(ax, [N_X0S, N_Y0S, 3.617, -23.841], fc="none", ec="none")
    for a in L.get("paved_areas", []):
        _rect(ax, a["rect"], fc="#e3d9c6", ec="#d2c7b0", lw=0.3, zorder=2)
    for g in L.get("planting_groups", []):
        _rect(ax, g["rect"], fc="#a5c88a", ec="#3b6b2a", lw=0.6, zorder=3)
    for z in L.get("zones", []):
        col = {"dining": "#c0392b", "lounge": "#d35400", "quiet": "#2980b9", "standing": "#7f8c8d"}.get(z["use"], "#999")
        _rect(ax, z["rect"], fc="none", ec=col, lw=1.0, ls=":", zorder=3)
        a0, b0, a1, b1 = z["rect"]
        ax.text(b0 + 0.08, a0 + 0.22, z["use"], fontsize=7, color=col, zorder=9)
    for t in L.get("tables", []):
        _rect(ax, [t["center"][0] - t["size_m"][0] / 2, t["center"][1] - t["size_m"][1] / 2, t["center"][0] + t["size_m"][0] / 2, t["center"][1] + t["size_m"][1] / 2], fc="#8d6e63", ec="#4e342e", zorder=6)
        ax.text(t["center"][1], t["center"][0], f"table\n{t['seats']}", fontsize=6, ha="center", va="center", color="white", zorder=9)
    for s_ in L.get("seating", []):
        _rect(ax, s_["rect"], fc="#5d6d7e", ec="#2c3e50", zorder=6)
    for f in L.get("features", []):
        if f["kind"] == "firepit":
            ax.add_patch(Circle((f["center"][1], f["center"][0]), f["diameter_m"] / 2, fc="#ff9800", ec="#bf360c", zorder=7))
            ax.add_patch(Circle((f["center"][1], f["center"][0]), f["diameter_m"] / 2 + 1.5, fc="none", ec="#ff9800", ls="--", lw=0.7, zorder=4))
            ax.text(f["center"][1], f["center"][0] - 0.65, "flush gas fire pit", fontsize=6.5, ha="center", zorder=9)
        elif f["kind"] == "bbq":
            _rect(ax, f["rect"], fc="#455a64", ec="#263238", zorder=7)
            ax.text((f["rect"][1] + f["rect"][3]) / 2, f["rect"][0] - 0.12, "BBQ", fontsize=6.5, ha="center", zorder=9)
        elif f["kind"] == "pond":
            _rect(ax, f["rect"], fc="#4fa3d1", ec="#1a5f8a", zorder=6)
            ax.text((f["rect"][1] + f["rect"][3]) / 2, (f["rect"][0] + f["rect"][2]) / 2, "koi pond (flush, grille)", fontsize=7, ha="center", va="center", color="white", zorder=9)
        elif f["kind"] == "herb_bed":
            ax.text((f["rect"][1] + f["rect"][3]) / 2, f["rect"][0] + 0.25, "herbs", fontsize=6.5, ha="center", zorder=9)
    for o in L.get("obstacles", []):
        if o["id"].startswith("pot"):
            a0, b0, a1, b1 = o["rect"]
            ax.add_patch(Circle(((b0 + b1) / 2, (a0 + a1) / 2), 0.3, fc="#bf6b3f", ec="#7b3f1d", zorder=7))
        if o["id"] == "sister-screen":
            _rect(ax, o["rect"], fc="#6d4c41", ec="#3e2723", zorder=6)
    for t in L.get("trees", []):
        r = (t.get("canopy_r_m") or (t.get("mature_spread_m") or 3.0) / 2)
        ax.add_patch(Circle((t["center"][1], t["center"][0]), r, fc=SP_COL.get(t["species"], "#2e7d32"), alpha=0.35, ec="#1b5e20", ls="--", zorder=8))
        ax.add_patch(Circle((t["center"][1], t["center"][0]), 0.22, fc="#3e2723", zorder=8))
    for r in covers:
        _rect(ax, r, fc="none", ec="#6d4c41", lw=1.8, ls=(0, (6, 3)), zorder=8)
    if plan:
        for bid, p in plan["beds"].items():
            for inst in p["instances"]:
                col = SP_COL.get(inst["species"], LAYER_COL.get(inst["layer"], "#2e7d32"))
                ax.scatter([q[1] for q in inst["positions"]], [q[0] for q in inst["positions"]], s=38 if inst["layer"] != "climber" else 55, c=col,
                           edgecolors="#222", linewidths=0.4, zorder=9, marker="o" if inst["layer"] != "climber" else "^")
    ax.set_xlim(y0, y1)
    ax.set_ylim(x1, x0)
    ax.set_aspect("equal")
    ax.set_title(label, fontsize=10)
    ax.tick_params(labelsize=7)


N_X0S, N_Y0S = -0.123, -29.916


def draw(layouts: dict, plans: dict, title: str, path, pond_label: str = "", extra_notes: list[str] | None = None, species_names: dict | None = None):
    """layouts / plans: {"south": L, "north": L, "east": L}; `_cover` in layouts = pergola rects (model frame)."""
    fig = plt.figure(figsize=(16, 9))
    gs = fig.add_gridspec(3, 2, width_ratios=[1.55, 1], height_ratios=[1.35, 1, 0.7], hspace=0.28, wspace=0.08)
    axS = fig.add_subplot(gs[:, 0])
    axE = fig.add_subplot(gs[0, 1])
    axN = fig.add_subplot(gs[1, 1])
    axK = fig.add_subplot(gs[2, 1])
    cov = layouts.get("_cover", [])
    _zone_axes(axS, layouts["south"], plans["south"], (-30.4, -20.2, 22.2, 28.9), [r for r in cov if r[0] > 20], "SOUTH GARDEN (client south; sister plot open on the left edge)")
    _zone_axes(axE, layouts["east"], plans["east"], (-24.2, -20.0, 15.2, 23.0), [], "EAST YARD (doors: dining and living on its north side)")
    _zone_axes(axN, layouts["north"], plans["north"], (-29.4, -23.4, -0.6, 4.0), [r for r in cov if r[0] < 5], "NORTH COURT (street fence at top)")
    axE.invert_yaxis() if False else None
    axK.axis("off")
    lines = [title, ""] + (extra_notes or [])
    lines += ["", "key: grey = seats; brown = table; orange = flush fire pit;", "dashed brown = pergola (non-combustible, louvred);", "dotted frame = use room; triangles = climbers;",
              "dots = plants coloured by species (see schedule)", "client north is up; model x down = south"]
    axK.text(0, 1, "\n".join(lines), fontsize=7.2, va="top", family="monospace")
    fig.suptitle(title, fontsize=12)
    fig.savefig(path, dpi=105, bbox_inches="tight")
    plt.close(fig)
    return path
