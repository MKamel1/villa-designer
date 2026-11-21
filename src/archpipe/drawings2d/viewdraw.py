"""Draw sections and elevations on sheets: poche, line-art strokes by depth, level lines, grid, room labels, dimensions."""
from __future__ import annotations

import json
from pathlib import Path

from matplotlib.patches import PathPatch
from matplotlib.path import Path
from matplotlib.patches import Rectangle
from shapely.geometry import LineString, box

from archpipe.contracts import DesignElement
from archpipe.documents import plans

from . import modelcut, orient, section, standard
from .section import View

LEVEL_NAMES = [("B", "Basement FFL"), ("GF", "Ground floor FFL"), ("L1", "Apartment FFL (not ours)"), ("ROOF", "Roof slab top")]
SKIN_MATERIALS = {"glass-clear", "door-oak", "alu-bronze", "black-metal"}

SECTION_1 = View("Section 1: through the stair", "section", (0.0, 1.0, 0.0), (0.0, -27.95), (3.2, -3.5, 11.6, 6.4), "A-301", 50.0)
SECTION_2 = View("Section 2: through the sunken garden", "section", (0.0, 1.0, 0.0), (0.0, -22.2), (-0.8, -3.6, 24.0, 6.8), "A-302", 100.0)
ELEVATIONS = [
    View("North elevation (street)", "elevation", (1.0, 0.0, 0.0), (0.0, -26.0), (20.0, -3.5, 32.5, 6.8), "A-201", 100.0),
    View("South elevation", "elevation", (-1.0, 0.0, 0.0), (30.0, -26.0), (-32.5, -3.5, -20.0, 6.8), "A-201", 100.0),
    View("East elevation", "elevation", (0.0, -1.0, 0.0), (10.0, 0.0), (-24.5, -3.5, -3.0, 6.8), "A-202", 100.0),
    View("West elevation", "elevation", (0.0, 1.0, 0.0), (10.0, -40.0), (3.0, -3.5, 24.5, 6.8), "A-202", 100.0),
]
ALL_VIEWS = [SECTION_1, SECTION_2] + ELEVATIONS


def left_right(view: View) -> tuple[str, str]:
    ux, uy = view.u_axis
    return orient.compass_of_model_vector(-ux, -uy), orient.compass_of_model_vector(ux, uy)


def facade(view: View) -> str:
    """Client compass side of the building an elevation shows (the viewer stands on that side)."""
    return orient.compass_of_model_vector(-view.d[0], -view.d[1])


def room_labels(els: list[DesignElement], view: View) -> list[dict]:
    """Rooms whose plan polygon the cut plane crosses: name, u-extent, ceiling height, level."""
    from shapely.geometry import Polygon
    ceil = {e.room: e for e in els if e.kind == "ceiling"}
    out = []
    for r in els:
        if r.kind != "room":
            continue
        poly = Polygon([(x * 0.001, y * 0.001) for x, y in r.params["polygon_mm"]])
        for u0, u1 in modelcut._u_intervals(poly, view):
            if u1 - u0 > 0.3:
                c = ceil.get(r.room)
                out.append({"room": r.room, "name": r.params["name"], "level": r.level, "u0": u0, "u1": u1,
                            "ceiling_mm": c.params["height_mm"] if c else None})
    return out


def grid_u(els: list[DesignElement], view: View) -> list[tuple[str, float]]:
    """Grid lines the view's horizontal axis crosses (model x lines when looking along y), numbered/lettered like the plans."""
    cels = orient.to_client(els)
    g = plans.grid_lines(cels)
    ux, uy = view.u_axis
    out = []
    if abs(ux) > 0.5:                                 # horizontal axis is model x: grid lines are client y (numbers)
        for i, v in enumerate(sorted(g["y"])[::-1]):  # client y = -model x; number 1 is the southernmost line (as the plans)
            out.append((str(len(g["y"]) - i), ux * (-v) / 1000.0))
        out = [(str(i + 1), u) for i, (_, u) in enumerate(sorted(out, key=lambda t: t[1], reverse=True))]
    else:                                             # horizontal axis is model y: grid lines are client x (letters)
        for i, v in enumerate(sorted(g["x"])):
            out.append(("ABCDEFGHJK"[i], uy * v / 1000.0))
    return out


def draw_view(sh, built: dict, cut: dict, els, levels, view: View, origin_mm: tuple[float, float], *, label_rooms=True) -> dict:
    """Draw one view with its window's lower-left at paper (ox, oy) mm. Returns counts for QA."""
    sc = view.scale
    u0, z0, u1, z1 = view.window
    sh.ox, sh.oy, sh.x0, sh.y0 = origin_mm[0], origin_mm[1], u0 * 1000.0, z0 * 1000.0
    ax = sh.ax
    w, h = (u1 - u0) * 1000 / sc, (z1 - z0) * 1000 / sc
    clip = Rectangle(sh.p(u0 * 1000, z0 * 1000), w, h, transform=ax.transData, fc="none", ec="none")
    ax.add_patch(clip)
    n0 = (len(ax.patches), len(ax.lines), len(ax.texts))
    P = lambda u, z: sh.p(u * 1000.0, z * 1000.0)                                    # noqa: E731
    cnt = {"structure_polys": 0, "context_polys": 0, "strokes": 0}
    def ring_patch(poly, **kw):
        """A shapely polygon with its holes as one compound path (holes stay empty: the room air shows through)."""
        verts, codes = [], []
        for ring in [poly.exterior, *poly.interiors]:
            pts = [P(*q) for q in ring.coords]
            verts += pts
            codes += [Path.MOVETO] + [Path.LINETO] * (len(pts) - 2) + [Path.CLOSEPOLY]
        return PathPatch(Path(verts, codes), **kw)

    for poly in cut["context"]:
        ax.add_patch(ring_patch(poly, fc="#eeeeee", ec="#999999", hatch="..", lw=standard.lw("ctx", sc), zorder=1))
        cnt["context_polys"] += 1
    for poly in cut["structure"]:
        ax.add_patch(ring_patch(poly, fc="#2e2e2e", ec="k", lw=standard.lw("cut", sc), zorder=4))
        cnt["structure_polys"] += 1
    dmin = min((min(l["depth"]) for l in built["lines"]), default=0.0)
    for l in built["lines"]:
        d = min(l["depth"]) - dmin
        role = "proj" if d < 2.0 else "beyond"
        pts = [P(*q) for q in l["uz"]]
        sh.ax.plot([p[0] for p in pts], [p[1] for p in pts], color="#111111" if role == "proj" else "#777777",
                   lw=standard.lw(role, sc), zorder=6 if role == "proj" else 3, solid_capstyle="butt")
        cnt["strokes"] += 1
    for a, b, m in built["cut_segments"]:                 # scene skins at the cut that are not poche: glazing, door leaves
        if m in SKIN_MATERIALS:
            sh.line(P(*a), P(*b), lw=standard.lw("proj", sc), z=7)
    # levels (Revit elevation = scene + 1.2), ground and street lines
    zlev = []
    for key, nm in LEVEL_NAMES:
        st = levels.get(key)
        if not st:
            continue
        zs = st["ffl_scene_mm"] / 1000.0
        zlev.append((zs, "%s %+.2f" % (nm, st["ffl_revit_mm"] / 1000.0)))
    zlev += [(-1.2, "Street level +0.00 (Revit datum)")]
    for zs, label in zlev:
        sh.line(P(u0, zs), P(u1, zs), lw=standard.lw("grid", sc), ls=(0, (10, 3, 1.5, 3)), color="#0b5394", z=2)
        sh.text((P(u0, zs)[0] + 1.0, P(u0, zs)[1] + 1.4), label, size=3.6, ha="left", color="#0b5394", z=9)
    # section: room labels, grid bubbles
    if view.kind == "section" and label_rooms:
        for r in room_labels(els, view):
            lvl = levels[r["level"]]["ffl_scene_mm"] / 1000.0
            cx = (r["u0"] + r["u1"]) / 2
            if u0 <= cx <= u1:
                ch = "  CH %.2f" % (r["ceiling_mm"] / 1000.0) if r["ceiling_mm"] else ""
                sh.text(P(cx, lvl + 0.55), plans.names.short_en(r["name"]) + ch, size=3.8, bg=True, z=9)
    for lab, u in grid_u(els, view):
        if u0 <= u <= u1:
            top = P(u, z1 - 0.2)
            sh.line(P(u, z0 + 0.1), top, lw=standard.lw("grid", sc), ls=(0, (8, 2, 1, 2)), color="#c0392b", z=2)
            from matplotlib.patches import Circle
            ax.add_patch(Circle((top[0], top[1] + 2.4), 2.4, fc="white", ec="#c0392b", lw=0.3, zorder=9))
            sh.text((top[0], top[1] + 2.4), lab, size=5, color="#c0392b", z=10)
    # vertical dimension chain at the right edge: storey heights (scene levels in the window)
    zs = sorted({st["ffl_scene_mm"] / 1000.0 for k, st in levels.items() if k in ("B", "GF", "L1", "ROOF")})
    x = P(u1, 0)[0] - 7
    for a, b in zip(zs, zs[1:]):
        pa, pb = P(u1, a), P(u1, b)
        sh.line((x, pa[1]), (x, pb[1]), lw=standard.lw("dim", sc), z=8)
        for p_ in (pa, pb):
            sh.line((x - 0.9, p_[1] - 0.9), (x + 0.9, p_[1] + 0.9), lw=0.35, z=8)
        sh.text((x - 1.3, (pa[1] + pb[1]) / 2), "%d" % round((b - a) * 1000), size=3.8, rot=90, z=9)
    for art in list(ax.patches[n0[0]:]) + list(ax.lines[n0[1]:]) + list(ax.texts[n0[2]:]):
        if art is not clip:
            art.set_clip_path(clip)
            art.set_clip_on(True)
    ax.add_patch(Rectangle(sh.p(u0 * 1000, z0 * 1000), w, h, fc="none", ec="k", lw=0.3, zorder=12))
    left, right = left_right(view)
    if view.kind == "section":
        title = view.name
        sub = "looking %s; left = %s, right = %s" % (orient.compass_of_model_vector(view.d[0], view.d[1]), left, right)
    else:
        title = view.name
        sub = "seen from the %s side; left = %s, right = %s" % (facade(view), left, right)
    sh.text((sh.ox, sh.oy + h + 6), title, size=7.5, ha="left", weight="bold")
    sh.text((sh.ox, sh.oy + h + 2.2), "1:%g   %s" % (sc, sub), size=4.5, ha="left", color="#444444")
    cnt["size_mm"] = (w, h)
    return cnt
