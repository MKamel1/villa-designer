"""Interior elevations (plan row I15): each wall of a room seen from inside, drawn from the DESIGN MODEL (no Blender).

For each room: the four walls (client compass, viewer inside looking at the wall), the clear width from the room's net
polygon, the ceiling height from the ceiling element, doors and windows hosted on that wall (tag, width x height, sill),
and furniture standing within 900 mm of the wall (type, height). Floor = 0. Not drawn: finishes (no tone), wall
thickness, joinery detail. Opening and furniture positions come from the model; nothing is invented.
"""
from __future__ import annotations

from matplotlib.patches import Rectangle

from archpipe.contracts import DesignElement
from archpipe.documents import plans, schedules

from . import layers as L
from . import orient, standard

ROOMS = [("parents-bed", "GF"), ("kids-a", "GF"), ("kids-b", "GF")]
WALLS = ("N", "E", "S", "W")
NEAR_MM = 900.0                     # furniture this close to the wall face counts as standing at it


def _bbox(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def wall_frame(box, wall: str):
    """(length, face, u(x, y)) in the client frame: the viewer looks at the wall, u grows to the viewer's right."""
    x0, y0, x1, y1 = box
    return {"N": (x1 - x0, y1, lambda x, y: x - x0), "S": (x1 - x0, y0, lambda x, y: x1 - x),
            "E": (y1 - y0, x1, lambda x, y: y1 - y), "W": (y1 - y0, x0, lambda x, y: y - y0)}[wall]


def _dist_to_face(wall: str, face: float, bb) -> float:
    x0, y0, x1, y1 = bb
    return {"N": face - y1, "S": y0 - face, "E": face - x1, "W": x0 - face}[wall]


def elevation_items(cels: list[DesignElement], room: str, level: str, wall: str) -> dict:
    """What one interior elevation shows, in wall coordinates (u mm from the viewer's left, z mm above the floor)."""
    r = next(e for e in cels if e.kind == "room" and e.room == room and e.level == level)
    box = _bbox(r.params["net_polygon_mm"])
    length, face, U = wall_frame(box, wall)
    ceil = next((e for e in cels if e.kind == "ceiling" and e.room == room), None)
    height = ceil.params["height_mm"] if ceil else r.params.get("clear_height_mm", 2700.0)
    horizontal = wall in "NS"
    openings = []
    for e in cels:
        if e.kind not in ("door", "window") or e.level != level or room not in ([e.room] + list(e.params.get("rooms", []))):
            continue
        along = e.placement[0] if horizontal else e.placement[1]
        across = e.placement[1] if horizontal else e.placement[0]
        if abs(across - face) > 260:
            continue
        w = e.params.get("width_mm", e.size[0])
        x, y = e.placement[0], e.placement[1]
        uc = U(x, y)
        if not (-100 <= uc <= length + 100):
            continue
        sill = e.params.get("sill_mm", 0.0) if e.kind == "window" else 0.0
        openings.append({"id": e.id, "kind": e.kind, "u0": uc - w / 2, "u1": uc + w / 2, "z0": sill,
                         "z1": sill + e.params.get("height_mm", e.size[2]), "w": w})
    furn = []
    for e in cels:
        if e.kind != "furniture" or e.level != level or e.room != room or e.params.get("type") == "dressing":
            continue
        poly = L.rect_poly(e.placement[0], e.placement[1], e.size[0], e.size[1], e.rotation_deg)
        bb = _bbox(poly)
        if _dist_to_face(wall, face, bb) > NEAR_MM:
            continue
        us = [U(*q) for q in poly]
        furn.append({"id": e.id, "type": e.params.get("type", "").replace("_", " "), "u0": min(us), "u1": max(us), "h": e.size[2]})
    return {"room": room, "wall": wall, "length": length, "height": height, "openings": openings, "furniture": furn,
            "name": (lambda n: n[:1].upper() + n[1:])(r.params["name"].split(" (")[0])}


def draw_elevation(sh, items: dict, tagmap: dict[str, str], origin_mm: tuple[float, float]) -> dict:
    sc = sh.scale
    ox, oy = origin_mm
    ax = sh.ax
    P = lambda u, z: (ox + u / sc, oy + z / sc)                                           # noqa: E731
    Lw, H = items["length"], items["height"]
    ax.add_patch(Rectangle(P(0, 0), Lw / sc, H / sc, fc="white", ec="k", lw=standard.lw("proj", sc), zorder=2))
    sh.line(P(-150, 0), P(Lw + 150, 0), lw=standard.lw("cut", sc), z=4)                    # floor
    sh.line(P(-150, H), P(Lw + 150, H), lw=standard.lw("cut", sc), z=4)                    # ceiling
    tags = []
    for o in items["openings"]:
        a, b = P(max(o["u0"], 0), o["z0"]), P(min(o["u1"], Lw), o["z1"])
        col = plans.DOOR_COLOUR if o["kind"] == "door" else plans.WINDOW_COLOUR
        ax.add_patch(Rectangle(a, b[0] - a[0], b[1] - a[1], fc="#f4f9ff" if o["kind"] == "window" else "#fff6ec", ec=col,
                               lw=standard.lw("proj", sc), zorder=3))
        if o["kind"] == "window":
            sh.line(((a[0] + b[0]) / 2, a[1]), ((a[0] + b[0]) / 2, b[1]), lw=standard.lw("fine", sc), color=col, z=4)
        lab = "%s  %d x %d%s" % (tagmap[o["id"]], o["w"], o["z1"] - o["z0"], ("  sill %d" % o["z0"]) if o["kind"] == "window" else "")
        sh.text(((a[0] + b[0]) / 2, b[1] + 2.4), lab, size=7, z=9)
        tags.append(tagmap[o["id"]])
    for f in items["furniture"]:
        a, b = P(max(f["u0"], 0), 0), P(min(f["u1"], Lw), f["h"])
        ax.add_patch(Rectangle(a, max(b[0] - a[0], 0.2), b[1] - a[1], fc="#fffdf5", ec="#7a5c2e", lw=standard.lw("proj", sc), zorder=5, alpha=0.9))
        if (b[0] - a[0]) > 12:
            sh.text(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), "%s\nh %d" % (f["type"], f["h"]), size=7, color="#5a431f", z=9)
    # clear width below, ceiling height at the right
    y = oy - 5
    sh.line((ox, y), (ox + Lw / sc, y), lw=0.2, z=6)
    for xx in (ox, ox + Lw / sc):
        sh.line((xx - 0.9, y - 0.9), (xx + 0.9, y + 0.9), lw=0.35, z=6)
    sh.text((ox + Lw / sc / 2, y - 3.0), "%d" % round(Lw), size=7)
    sh.text((ox + Lw / sc + 3.4, oy + H / sc / 2), "CH %d" % round(H), size=7, rot=90)
    names = {"N": "north", "E": "east", "S": "south", "W": "west"}
    sh.text((ox, oy + H / sc + 5.5), "%s, %s wall (looking %s)" % (items["name"], names[items["wall"]], names[items["wall"]]), size=8.5, ha="left", weight="bold")
    return {"room": items["room"], "wall": items["wall"], "tags": tags, "furniture": [f["id"] for f in items["furniture"]], "size_mm": (Lw / sc, H / sc)}


def render_interior(els, spec, sheet, out_stem, *, page=1, pages=1, formats=("pdf", "svg", "png")) -> dict:
    paper = standard.PAPERS[sheet["paper"].split()[0]]
    scale = plans.parse_scale(sheet["scale"])
    cels = orient.to_client(els)
    tagmap = schedules.tag_numbers(els)
    sh = plans._Sheet(0, 0, 0, 0, paper=paper, scale=scale)
    rep = {"sheet": sheet["no"], "frame": "client-north-up", "scale": scale, "elevations": []}
    xmin, xmax = plans.LEFT + 12, paper[0] - plans.EDGE - plans.STRIP - 8
    ytop = paper[1] - plans.EDGE - 26
    for room, level in ROOMS:
        row = [elevation_items(cels, room, level, w) for w in WALLS]
        x, rowh = xmin, 0.0
        for it in row:
            w, h = it["length"] / scale, it["height"] / scale
            rowh = max(rowh, h)
        gapx = max(8.0, (xmax - xmin - sum(it["length"] / scale for it in row)) / 4)
        for it in row:
            rep["elevations"].append(draw_elevation(sh, it, tagmap, (x, ytop - 22 - it["height"] / scale)))
            x += it["length"] / scale + gapx
        ytop -= rowh + 40
    sh.text((plans.LEFT + 12, plans.EDGE + 8), "Interior elevations at 1:%g: floor = 0, widths are clear room widths (net polygon), CH = ceiling height. "
            "Doors orange, windows blue; furniture within 900 mm of the wall. Finishes are not drawn (see A-602)." % scale, size=7, ha="left", color="#444444")
    return plans.finish_sheet(sh, spec, sheet, page, pages, out_stem, formats, rep)
