"""Scene geometry for the G1 safety decisions that live in the spec (revit_spec._g1_fixes) and the design model:
the two guards the scene did not draw, the stair riser infill bars and the under-stair cupboard (lane SC).

Pure functions: spec in, `Part`s out. `villa_render._build` turns each Part into a mesh. Metres, scene datum.
Every position, height and rule comes from the spec; the small departures are stated where they happen.
"""
from __future__ import annotations

import math
from typing import NamedTuple

FLOOR_B = -3.0            # scene z of the basement finished floor (villa_render.LZ["B"])
STRINGER_BEARING = 0.025  # villa_render: the wall stringer's tread bearing plate reaches 25 mm under the tread edge


class Part(NamedTuple):
    mesh_id: str
    material: str
    faces: list
    group: str
    kind: str
    element_ids: list
    room: str | None = None
    label: str = ""


def _segment_box(a, b, t, z0, z1, lead, tail):
    """Box of thickness t centred on the axis-aligned segment a->b; `lead` shortens the start, `tail` lengthens the end."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy)
    if min(abs(dx), abs(dy)) > 1e-9:
        raise ValueError("guard segment is not axis-aligned: %s -> %s" % (a[:2], b[:2]))
    ux, uy = dx / n, dy / n
    s = (a[0] + ux * lead, a[1] + uy * lead)
    e = (b[0] + ux * tail, b[1] + uy * tail)
    h = t / 2
    return (min(s[0], e[0]) - abs(uy) * h, min(s[1], e[1]) - abs(ux) * h, z0,
            max(s[0], e[0]) + abs(uy) * h, max(s[1], e[1]) + abs(ux) * h, z1)


def glass_guard(g, box_faces, mesh_id, element_id):
    """Frameless glass guard on the spec path: one closed pane per segment. Each pane runs through its corner to the
    next pane's outer face and the next one starts at that face: face to face, no overlap."""
    t, z0 = g["thickness_m"], g["path"][0][2]
    pts, last = g["path"], len(g["path"]) - 2
    boxes = [_segment_box(a, b, t, z0, z0 + g["height_m"], t / 2 if i else 0.0, t / 2 if i < last else 0.0)
             for i, (a, b) in enumerate(zip(pts, pts[1:]))]
    return Part(mesh_id, "glass-guard", [f for b in boxes for f in box_faces(*b)], "furniture", "glass-pane", [element_id],
                label="guard %s: %.0f mm of %s, %.0f mm closed pane (G1)" % (
                    g["id"], g["height_m"] * 1000, g["material"].split(",")[0], t * 1000))


def bar_guard(g, box_faces, mesh_id, element_id):
    """Vertical flat bars with the clear opening <= the spec maximum, and the top rail, along one segment on x."""
    (xa, ya, z0), (xb, yb, _) = g["path"][0], g["path"][-1]
    if len(g["path"]) != 2 or abs(ya - yb) > 1e-9:
        raise ValueError("bar guard path must be one segment along x")
    w, t = g["bar_w_mm"] / 1000, g["thickness_m"]
    rail_w, rail_h = 0.040, 0.020                  # spec: "top rail 40 x 20 mm"
    top, L = z0 + g["height_m"], xb - xa
    n = math.ceil((L - w) / (w + g["max_opening_mm"] / 1000)) + 1     # fewest bars whose clear opening is <= the maximum
    pitch = (L - w) / (n - 1)
    boxes = [(xa + k * pitch, ya - t / 2, z0, xa + k * pitch + w, ya + t / 2, top - rail_h) for k in range(n)]
    boxes.append((xa, ya - rail_w / 2, top - rail_h, xb, ya + rail_w / 2, top))
    return Part(mesh_id, "stainless", [f for b in boxes for f in box_faces(*b)], "fixture", "guard-bars", [element_id],
                label="guard %s: %d flat bars %.0f x %.0f mm, clear %.1f mm, rail 40 x 20 (G1)" % (
                    g["id"], n, w * 1000, t * 1000, (pitch - w) * 1000))


def steel_clear_y(meshes):
    """(wall_side_y, open_side_y): the y planes the scene's own assumed steel leaves free under the stair. The wall stringer
    bearings and wall plate reach out from the party wall; the open-side stringer, base shoe and glass sit on the tread edge.
    Everything the G1 infill and cupboard add stays between the two (no member passes through another)."""
    def ys(prefixes):
        return [p[1] for m in meshes if m["id"].startswith(prefixes) for f in m["faces"] for p in f]
    return (max(ys(("detail-stair-wall-stringer-", "detail-stair-wall-plate"))),
            min(ys(("detail-stair-open-stringer", "detail-stair-glass-shoe", "detail-stair-glass-0", "detail-stair-glass-1"))))


def riser_infill(sp, box_faces, wall_side_y, open_side_y):
    """One horizontal flat bar per riser gap (spec["stair_infill"], mm boxes), spanning the tread width between the
    steel members: the spec box runs the full 950 mm and would sit 25 mm inside the wall stringer bearings and 50 mm
    inside the open-side stringer, shoe and glass. The slot left at the tread edge is 65 mm wide: no 100 mm sphere."""
    boxes = [(b[0] / 1000, wall_side_y, b[2] / 1000, b[3] / 1000, open_side_y, b[5] / 1000) for b in sp.get("stair_infill") or []]
    if not boxes:
        return None
    spec = sp["stair_infill_spec"]
    return Part("detail-stair-riser-infill", "black-metal", [f for b in boxes for f in box_faces(*b)], "fixture",
                "stair-infill-bar", ["stair-main"],
                label="%d x %s %d x %d mm in the %.1f mm riser gaps, no 100 mm sphere passes (G1 LS2)" % (
                    len(boxes), spec["type"], spec["bar_h_mm"], spec["bar_t_mm"], spec["gap_mm"]))


def understair_cupboard(sp, box_faces, wall_side_y, open_side_y):
    """Side wall (top stepping with the tread undersides), toe panel, end wall and the access leaf, after
    sp["understair_cupboard"], with three departures forced by what the scene already carries:
      * the model's side wall (y -27.571..-27.471) sits where the assumed open-side stringer, shoe and glass are, so its
        outer face stands at `open_side_y` and the cupboard is that much shallower;
      * the toe and end panels start at `wall_side_y`, in front of the wall stringer bearings and plate (the model's
        structural face -28.471 is behind them);
      * each wall step ends where the next lower tread begins (the 16 mm tread overlap, as RA2 did for the soffit check),
        or the step would poke into that tread."""
    cb = sp.get("understair_cupboard")
    if not cb:
        return []
    eid = ["joinery-" + cb["id"]]
    front, end = (next(w for w in cb["walls"] if w["id"].endswith(s)) for s in ("front", "end"))
    d, t = cb["door"], cb["walls"][0]["thickness"]
    ys0, ys1 = open_side_y - t, open_side_y
    dx0, dx1 = d["x"] - d["width"] / 2, d["x"] + d["width"] / 2
    floor_mm = FLOOR_B * 1000
    treads = sorted((b for b in sp["stair"] if b[5] - b[2] < 300 and b[2] - floor_mm < 2000.0), key=lambda b: -b[3])
    boxes = []
    for k, b in enumerate(treads):
        hi = b[3] / 1000 if k == 0 else treads[k - 1][0] / 1000      # up to the lower tread's start
        lo, top = b[0] / 1000, (b[2] - floor_mm) / 1000
        cuts = sorted({lo, hi} | {c for c in (dx0, dx1) if lo < c < hi})
        for a, z in zip(cuts, cuts[1:]):         # under the access opening only the lintel above the leaf remains
            in_door = dx0 - 1e-9 <= a and z <= dx1 + 1e-9
            boxes.append((a, ys0, FLOOR_B + (d["height"] if in_door else 0.0), z, ys1, FLOOR_B + top))
    parts = [Part("joinery-understair-cupboard-side", "white-paint-joinery", [f for b in boxes for f in box_faces(*b)],
                  "furniture", "cabinet-carcass", eid, cb["room"],
                  "understair cupboard side wall, top stepping with the treads, access opening %.2f x %.2f m (G1 LS1)" % (
                      d["width"], d["height"])),
             Part("joinery-understair-cupboard-toe", "white-paint-joinery",
                  box_faces(front["x0"] - t / 2, wall_side_y, FLOOR_B, front["x0"] + t / 2, ys0, FLOOR_B + front["height"]),
                  "furniture", "cabinet-carcass", eid, cb["room"], "understair cupboard toe panel under tread 1"),
             Part("joinery-understair-cupboard-end", "white-paint-joinery",
                  box_faces(end["x0"] - t / 2, wall_side_y, FLOOR_B, end["x0"] + t / 2, ys0, FLOOR_B + end["height"]),
                  "furniture", "cabinet-carcass", eid, cb["room"], "understair cupboard end wall under tread 11")]
    r = 0.003                                      # closed leaf flush in the side wall, 3 mm reveal; flat pull on its free edge
    leaf = (dx0 + r, ys0, FLOOR_B, dx1 - r, ys1, FLOOR_B + d["height"] - r)
    px = dx0 + r + 0.04
    parts.append(Part("joinery-understair-cupboard-door", "oak", box_faces(*leaf), "furniture", "door-leaf", eid, cb["room"],
                      "understair cupboard access leaf (hinged east, swings into the lounge), closed (G1 LS1)"))
    parts.append(Part("joinery-understair-cupboard-pull", "brass",
                      box_faces(px - 0.006, ys1, FLOOR_B + 0.50, px + 0.006, ys1 + 0.012, FLOOR_B + 0.70), "furniture",
                      "joinery-pull", eid, cb["room"], "ASSUMED flat pull on the cupboard leaf"))
    return parts
