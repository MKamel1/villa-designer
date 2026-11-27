"""Door handing and operation for every door of the model (plan rows I11, A13).

Stated rules, applied in this order to every hinged door the spec does not already author:
  R1  A swing is never across a stair landing: rooms in STAIR_ZONE (landing-gf, stair-gf, stair-b) and the plan
      footprint of the flight are excluded as swing rooms.
  R2  The leaf swings into the room that is entered, ranked by PRIVACY (bedrooms, dressing, sanitary, store, utility
      above living / media / study, above kitchen / dining, above circulation). A tie is a JUDGEMENT.
  R3  Away from walls and furniture: of the two hinge jambs, take the one whose 90-degree swing sector overlaps least
      with furniture, columns, stair and other doors' sectors; remaining ties go to the jamb nearer the room's end
      wall (the open leaf folds back against that wall). An overlap that cannot be avoided, or a tie, is a JUDGEMENT.
Sliding and pocket doors sweep nothing. Authored swings (spec `swing`, DOOR_TYPES, the under-stair cupboard) are kept and
recorded as authored. `judgement` and `judgement_reasons` on a door say where the rule did not decide alone.

Hinge side words are model-axis, as the authored G1 doors use them: west / east = -x / +x for a door in a wall that runs
along x; south / north = -y / +y for a wall that runs along y. NOT the client compass. `hinge_xy_mm` is exact.
`handing`: LH / RH as seen from the push side (the side the leaf swings away from), hinge on the left / right.
"""
from __future__ import annotations

import math

from shapely.affinity import rotate
from shapely.geometry import Polygon, box

STAIR_ZONE = ("landing-gf", "stair-gf", "stair-b")
PRIVACY = {"ensuite": 3, "bathroom": 3, "wc": 3, "dressing": 3, "bedroom": 3, "store": 3, "utility": 3,
           "living": 2, "media": 2, "study": 2, "kitchen": 1, "dining": 1,
           "corridor": 0, "hall": 0, "entrance": 0, "landing": 0, "stair": 0}


def _sector(hx, hy, ux, uy, nx, ny, r, steps=12):
    pts = [(hx, hy)] + [(hx + r * (math.cos(a) * ux + math.sin(a) * nx), hy + r * (math.cos(a) * uy + math.sin(a) * ny))
                        for a in (i * math.pi / 2 / steps for i in range(steps + 1))]
    return Polygon(pts)


def _furniture_polys(elements, level):
    out = []
    for e in elements:
        if e.kind != "furniture" or e.level != level or not e.size[0] or not e.size[1]:
            continue
        p = box(e.placement[0] - e.size[0] / 2, e.placement[1] - e.size[1] / 2,
                e.placement[0] + e.size[0] / 2, e.placement[1] + e.size[1] / 2)
        out.append((e.id, rotate(p, e.rotation_deg, origin=(e.placement[0], e.placement[1]))))
    return out


def _room_of(lay, level, x, y):
    for rid, r in lay["rooms"].items():
        x0, y0, x1, y1 = r["rect"]
        if r["level"] == level and x0 - 1e-6 <= x <= x1 + 1e-6 and y0 - 1e-6 <= y <= y1 + 1e-6:
            return rid
    return None


def _axis(d) -> str:
    sp = d.get("span")
    if sp:
        return sp[0]
    return None


def decide(sp, lay, elements, columns_mm) -> dict[tuple, dict]:
    """{(level, rooms joined '/', index among equal keys): operation dict} for every spec door.

    `elements` are the model's DesignElements (furniture footprints). Returns decisions keyed by the door's position in
    sp['doors'] (int)."""
    cols = [box(a / 1000, b / 1000, c / 1000, d / 1000) for a, b, c, d in columns_mm]
    stair = [box(b[0] / 1000, b[1] / 1000, b[3] / 1000, b[4] / 1000) for b in sp["stair"]]
    stair_zone_rects = [box(*lay["rooms"][r]["rect"]) for r in STAIR_ZONE if r in lay["rooms"]]
    furn = {lv: [(i, p.__class__(
        [(x / 1000, y / 1000) for x, y in p.exterior.coords])) for i, p in _furniture_polys(elements, lv)] for lv in ("B", "GF")}
    decisions: dict[int, dict] = {}
    sectors: list[tuple[int, object]] = []                                   # chosen sectors, for door-door conflicts
    for i, d in enumerate(sp["doors"]):
        if d.get("sliding") or d.get("garden"):
            decisions[i] = dict(operation="sliding", decided_by="spec: sliding/garden door", judgement=False,
                                judgement_reasons=[], handing="n/a", swing_clear=True)
            continue
    for i, d in enumerate(sp["doors"]):
        if i in decisions:
            continue
        key = "/".join(d["rooms"])
        from ..concept import villa_furnish as F
        typ = F.DOOR_TYPES.get(key) or ""
        if typ == "pocket":
            decisions[i] = dict(operation="pocket", decided_by="spec: DOOR_TYPES pocket (leaf retracts into the wall)",
                                judgement=True, judgement_reasons=["pocket side not authored: the leaf retracts to one side of the opening and the spec does not say which"],
                                handing="n/a", swing_clear=True)
            continue
        decisions[i] = _hinged(i, d, lay, sp, furn[d["level"]], cols, stair, stair_zone_rects, typ, sectors)
        if decisions[i].get("_sector") is not None:
            sectors.append((i, decisions[i].pop("_sector")))
        else:
            decisions[i].pop("_sector", None)
    return decisions


def _geometry(d, lay):
    """Hinge candidates: (jamb xy, closed-leaf direction u) for both jambs, plus the two wall normals."""
    w, x, y = d["width"], d["x"], d["y"]
    horizontal = d.get("span", [None])[0] == "h" if d.get("span") else None
    if horizontal is None:                                    # span not authored: the wall runs along the axis the rooms share
        a, b = (lay["rooms"].get(r) for r in d["rooms"])
        horizontal = any(r and (abs(r["rect"][1] - y) < 0.06 or abs(r["rect"][3] - y) < 0.06) for r in (a, b))
    if horizontal:
        jambs = [((x - w / 2, y), (1, 0)), ((x + w / 2, y), (-1, 0))]
        normals = [(0, 1), (0, -1)]
    else:
        jambs = [((x, y - w / 2), (0, 1)), ((x, y + w / 2), (0, -1))]
        normals = [(1, 0), (-1, 0)]
    return horizontal, jambs, normals


def _hinged(i, d, lay, sp, furn, cols, stair, stair_rects, typ, sectors):
    level, w = d["level"], d["width"]
    from ..concept import villa_furnish as F
    key = "/".join(d["rooms"])
    horizontal, jambs, normals = _geometry(d, lay)
    reasons: list[str] = []
    probe = 0.3
    sides = []
    for n in normals:
        room = _room_of(lay, level, d["x"] + n[0] * probe, d["y"] + n[1] * probe)
        sides.append((n, room))
    sw = d.get("swing") or {}
    into = typ[5:] if typ.startswith("into:") else ""
    authored = bool(sw) or bool(into)
    if sw:
        into = sw["into"]
    if authored:
        n = next((n for n, r in sides if r == into), None)
        if n is None:                                         # authored into a room outside the plan (shared core)
            n = next(n for n, r in sides if r is None)
    else:
        cands = [(n, r) for n, r in sides if r and r not in STAIR_ZONE]
        outside = [(n, r) for n, r in sides if r is None]
        if not cands:
            raise ValueError(f"door {'/'.join(d['rooms'])}: every side is a stair zone or outside; no swing room can be chosen")
        rank = lambda r: PRIVACY[lay["rooms"][r]["occupancy"]]
        top = max(rank(r) for _, r in cands)
        best = [(n, r) for n, r in cands if rank(r) == top]
        if outside and len(cands) == 1:
            reasons.append("entrance door: swings into the villa by default (the GF core door is authored outward, G1 LS4)")
        if len(best) > 1:
            reasons.append("both rooms rank equally for privacy (%s): chose the room with the lower swing-sector conflict" % ", ".join(r for _, r in best))
        scored = []
        for n, r in best:
            for j in jambs:
                scored.append((_score(j, n, w, furn, cols, stair, stair_rects, sectors, r, lay), n, r, j))
        n, into = min(scored, key=lambda s: (s[0][0][0], s[0][1]))[1:3]
    # hinge choice in the swing room
    opts = []
    for (hx, hy), (ux, uy) in jambs:
        score = _score(((hx, hy), (ux, uy)), n, w, furn, cols, stair, stair_rects, sectors, into, lay)
        opts.append((score, (hx, hy), (ux, uy)))
    if authored and sw.get("hinge_side"):
        hs = sw["hinge_side"]
        pick = next((o for o in opts if _side_word(horizontal, o[1], d) == hs), min(opts, key=_key))
        decided = "authored in the spec (" + ("G1 swing" if sw else "DOOR_TYPES") + ")"
    elif authored and key in F.DOOR_HINGE:
        hs = F.DOOR_HINGE[key]
        pick = next(o for o in opts if _side_word(horizontal, o[1], d) == hs)
        decided = "swing room and hinge jamb authored in DOOR_HINGE (privacy: the open leaf screens the view)"
    else:
        pick, decided = min(opts, key=_key), "rules R1-R3" if not authored else "swing room authored in DOOR_TYPES; hinge by rule R3"
    ((cf, near), end), (hx, hy), (ux, uy) = pick
    other = [o for o in opts if o is not pick][0]
    if cf > 0:
        reasons.append("swing sector still overlaps %s (%.2f m2): unavoidable at this door position" % (", ".join(near), cf))
    elif abs(other[0][0][0] - cf) < 1e-9 and abs(other[0][1] - end) < 0.05 and not authored:
        reasons.append("the two hinge jambs are equivalent within 50 mm of the room end wall: hinge side is a free choice")
    sec = _sector(hx, hy, ux, uy, n[0], n[1], w)
    # handing seen from the push side: viewer on the side opposite to n, facing +n
    cx, cy = d["x"], d["y"]
    cross = n[0] * (hy - cy) - n[1] * (hx - cx)             # z of f x h; > 0: hinge on the viewer's left
    hand = "LH" if cross > 0 else "RH"
    stair_hit = any(sec.intersection(s).area > 1e-6 for s in stair) or into in STAIR_ZONE
    return dict(
        operation="hinged", swing_into=into or "", hinge_side=_side_word(horizontal, (hx, hy), d), handing=hand,
        hinge_xy_mm=[round(hx * 1000, 1), round(hy * 1000, 1)], swing_normal=list(n), swing_arc_radius_mm=round(w * 1000, 1),
        decided_by=decided, judgement=bool(reasons), judgement_reasons=reasons, swing_clear=cf == 0 and not stair_hit,
        swing_stair_clear=not stair_hit, authored=authored, _sector=sec)


def _key(o):
    return (o[0][0][0], o[0][1])


def _side_word(horizontal, hinge, d):
    if horizontal:
        return "west" if hinge[0] < d["x"] else "east"
    return "south" if hinge[1] < d["y"] else "north"


def _score(jamb, n, w, furn, cols, stair, stair_rects, sectors, room, lay):
    """((overlap m2, names), distance from the hinge to the room's end wall along the door wall)."""
    (hx, hy), (ux, uy) = jamb
    sec = _sector(hx, hy, ux, uy, n[0], n[1], w)
    area, names = 0.0, []
    for fid, p in furn:
        a = sec.intersection(p).area
        if a > 1e-4:
            area += a
            names.append(fid)
    for k, c in enumerate(cols):
        a = sec.intersection(c).area
        if a > 1e-4:
            area += a
            names.append(f"column-{k:02d}")
    for k, s in enumerate(stair):
        a = sec.intersection(s).area
        if a > 1e-4:
            area += 10 * a
            names.append("stair")
    for k, s in sectors:
        a = sec.intersection(s).area
        if a > 1e-4:
            area += a
            names.append(f"door#{k}")
    r = lay["rooms"].get(room)
    x0, y0, x1, y1 = r["rect"] if r else (hx, hy, hx, hy)
    end = min(abs(hx - x0), abs(hx - x1)) if ux else min(abs(hy - y0), abs(hy - y1))
    return (round(area, 4), tuple(names)), round(end, 3)
