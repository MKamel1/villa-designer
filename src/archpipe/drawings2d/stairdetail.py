"""Stair section detail (A-301): riser infill bars, guards and the understair cupboard, drawn from the DESIGN MODEL.

The scene's line art shows treads and shell, not these items (lead review 2026-11-21), so they are drawn here from the
model elements (`stair.riser_infill`, `railing` profiles, `furniture` understair cupboard), in the section's (u, z)
frame (scene z, metres). Items on the cut plane are drawn as cut (dark); items beyond it as outline.
Colours are fixed so `sheetqa.stair_detail_violations` can count them in the produced PDF.
"""
from __future__ import annotations

from matplotlib.patches import Polygon, Rectangle

from archpipe.contracts import DesignElement

BAR_FC = "#d62728"         # riser infill bar (cut)
GLASS_FC = "#9fd3e6"       # glazed guard (beyond the plane)
CUPBOARD_FC = "#f2d9a6"    # understair cupboard walls (cut or beyond)


def applies(els: list[DesignElement], view) -> bool:
    """The section plane crosses the flight: plane y inside the stair's y range."""
    st = next((e for e in els if e.kind == "stair"), None)
    if st is None or view.kind != "section":
        return False
    ys = [b[1] for b in st.params["tread_boxes_mm"]] + [b[4] for b in st.params["tread_boxes_mm"]]
    return abs(view.d[1]) > 0.5 and min(ys) / 1000 <= view.p0[1] <= max(ys) / 1000


def draw(sh, P, els: list[DesignElement], view, sc: float, lw_cut: float, lw_proj: float) -> dict:
    """Draw into sh.ax. P(u_m, z_m) -> paper mm. Returns what was drawn (counts) for the report."""
    ax = sh.ax
    st = next(e for e in els if e.kind == "stair")
    cnt = {"riser_bars": 0, "guards": [], "cupboard_walls": 0, "cupboard_door": False}
    sgn = 1.0 if view.u_axis[0] > 0 else -1.0                      # u = +x or -x
    U = lambda x_mm: sgn * x_mm / 1000.0                           # noqa: E731

    def rect(x0, x1, z0, z1, **kw):                                 # x in model mm, z scene mm
        a, b = P(U(x0), z0 / 1000.0), P(U(x1), z1 / 1000.0)
        ax.add_patch(Rectangle((min(a[0], b[0]), min(a[1], b[1])), abs(b[0] - a[0]), abs(b[1] - a[1]), **kw))

    # riser infill: horizontal flat bars across the flight, cut by the plane (bars run the stair width, y -28421..-27471)
    inf = st.params.get("riser_infill") or {}
    for x0, y0, z0, x1, y1, z1 in inf.get("bar_boxes_mm", []) if inf.get("present") else []:
        rect(x0, x1, z0, z1, fc=BAR_FC, ec=BAR_FC, lw=0.1, zorder=8)
        cnt["riser_bars"] += 1
    # guards beyond the plane: glass panel from the nosing line (or the GF edge) up by the guard height
    for r in els:
        if r.kind != "railing" or r.id not in ("rail-stair-open-glass", "rail-gf-stair-void"):
            continue
        h = r.params["guard_height_mm"] / 1000.0
        if r.id == "rail-stair-open-glass":
            pts = [(p[0], p[2]) for p in r.params["profile_mm"]]       # nosing line (x, z)
        else:
            xs = sorted(p[0] for p in r.params["path_mm"])
            pts = [(xs[0], r.params["path_mm"][0][2]), (xs[-1], r.params["path_mm"][0][2])]
        up = [P(U(x), z / 1000.0 + h) for x, z in pts]
        dn = [P(U(x), z / 1000.0) for x, z in pts]
        ax.add_patch(Polygon(up + dn[::-1], closed=True, fc=GLASS_FC, ec="#2a7f9e", lw=lw_proj, alpha=0.55, zorder=5))
        cnt["guards"].append(r.id)
    # understair cupboard: end wall and toe panel are cut by the plane; the side wall (stepped top) and its door are beyond
    cb = next((e for e in els if e.id == "joinery-understair-cupboard"), None)
    if cb is not None:
        z_floor = -3000.0
        for w in cb.params["walls"]:
            if w["role"].startswith("end wall"):
                rect(w["x0_mm"] - w["thickness_mm"] / 2, w["x0_mm"] + w["thickness_mm"] / 2, z_floor, z_floor + w["height_mm"],
                     fc=CUPBOARD_FC, ec="k", lw=lw_cut, zorder=7)
            elif w["role"].startswith("toe panel"):
                rect(w["x0_mm"] - w["thickness_mm"] / 2, w["x0_mm"] + w["thickness_mm"] / 2, z_floor, z_floor + w["height_mm"],
                     fc=CUPBOARD_FC, ec="k", lw=lw_cut, zorder=7)
            else:                                                   # side wall, top steps with the treads
                prof = w["top_profile_mm"]
                outline = [(prof[0][0], z_floor)]
                for xa, xb, h in prof:
                    outline += [(xa, z_floor + h), (xb, z_floor + h)]
                outline.append((prof[-1][1], z_floor))
                ax.add_patch(Polygon([P(U(x), z / 1000.0) for x, z in outline], closed=True, fc=CUPBOARD_FC, ec="#7a5c2e",
                                     lw=lw_proj, alpha=0.7, zorder=4))
            cnt["cupboard_walls"] += 1
        d = cb.params["door"]
        rect(d["x_mm"] - d["width_mm"] / 2, d["x_mm"] + d["width_mm"] / 2, z_floor + 50, z_floor + 50 + d["height_mm"],
             fc="none", ec="#7a5c2e", lw=lw_proj, ls=(0, (4, 2)), zorder=6)
        cnt["cupboard_door"] = True
        c = P(U(cb.params["interior_mm"][0] + 1400), (z_floor + 600) / 1000.0)
        sh.text(c, "understair cupboard\n%.2f m³, 11 treads enclosed\n(G1 LS1)" % cb.params["volume_m3"], size=7, color="#5a431f", bg=True, z=9)
    return cnt
