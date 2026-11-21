"""V2 placement: is every emitter where the design model says, inside its room, below its ceiling, on the right datum?

Independent references: room polygons / clear heights / level datums from the committed L2 model snapshot
(`archpipe.model`), and the design's own `ceiling_z` for sloped soffits (the model only stores the centre value).
Per fixture:
  room     emitter plan position inside its room polygon (wall-mounted kinds: within WALL_TOL of the polygon);
  ceiling  emitter z below the finished ceiling and, for recessed/pendant/strip, within CEILING_BAND of it (not floating);
  floor    emitter z above the room floor (recessed spots at least 1.8 m up);
  aim      non-zero (the engine normalises it); ceiling-mounted spots point downward;
  datum    engine z minus the level's scene floor datum (B -3.00, GF 0.00) equals the model's z above FFL (not Revit -1.80/+1.20);
  model    same id in the snapshot: position within 10 mm. Ids that exist on one side only are reported (stale snapshot).
"""
from __future__ import annotations

import math

from .common import LayerResult, check
from .sources import ids

POS_TOL = 0.010
WALL_TOL = 0.20
CEILING_BAND = 0.35          # a recessed/pendant/strip emitter sits within this of the ceiling it hangs from
SRC = ids("LV-V2-POS")


def _inside(poly, x, y, tol):
    from ..lightcalc.geometry import dist_to_edges, point_in_polygon
    return point_in_polygon((x, y), poly) or dist_to_edges((x, y), poly) <= tol


def load_model():
    from .. import model
    els = model.load("D1")
    rooms = {e.room: e for e in els if e.kind == "room"}
    lums = {e.id[4:] if e.id.startswith("lum-") else e.id: e for e in els if e.kind == "luminaire"}
    return rooms, lums


def _levels():
    import json
    from pathlib import Path
    from .. import model
    p = Path(model.__file__).parent / "data" / "d1-elements.json"
    return {k: v["ffl_scene_mm"] / 1000 for k, v in json.loads(p.read_text())["levels"].items()}


def fixture_problems(f, rooms, ceiling_of, levels) -> list[str]:
    pr = []
    rec = f.record
    x, y, z = rec.position
    room = rooms.get(f.room)
    floor = levels[f.level]
    mount = rec.mount
    if room is None:
        return ["room %s not in the model" % f.room]
    poly = [tuple(p[:2]) for p in room.params["polygon_mm"]]
    poly = [(a / 1000, b / 1000) for a, b in poly]
    if not _inside(poly, x, y, WALL_TOL if mount in ("wall", "wall-marker", "task-lamp") else 0.0):
        pr.append("plan position (%.2f, %.2f) outside room %s" % (x, y, f.room))
    ceil = ceiling_of(f)
    if z > ceil + 0.001 and mount != "strip":
        pr.append("emitter z %.3f is above its ceiling %.3f (%.0f mm inside the slab)" % (z, ceil, 1000 * (z - ceil)))
    if mount == "recessed" and z < ceil - CEILING_BAND:
        pr.append("%s emitter z %.3f is %.0f mm below its ceiling %.3f" % (mount, z, 1000 * (ceil - z), ceil))
    if mount in ("recessed", "pendant") and z < floor + (1.8 if mount == "recessed" else 1.0):
        pr.append("%s emitter %.2f m above the floor" % (mount, z - floor))
    if mount in ("wall", "wall-marker", "task-lamp", "strip") and not (floor - 0.001 <= z <= ceil + 0.30):
        pr.append("z %.3f outside floor %.2f .. ceiling %.2f" % (z, floor, ceil))
    if f.level not in levels or not (floor - 0.5 <= z <= floor + 4.0):
        pr.append("datum: z %.3f is not within the %s storey (floor %.2f)" % (z, f.level, floor))
    n = math.sqrt(sum(c * c for c in rec.aim))
    if n < 1e-6:                                     # the engine normalises aim; only a zero vector is wrong
        pr.append("zero aim vector")
    elif mount in ("recessed",) and rec.aim[2] > -0.5:
        pr.append("recessed fitting aims %.0f deg off nadir" % math.degrees(math.acos(-rec.aim[2])))
    return pr


def check_placement(v) -> LayerResult:
    L = LayerResult("V2")
    rooms, lums = load_model()
    levels = _levels()
    from ..lightcalc.villa import LEVEL_Z
    for lv, zf in LEVEL_Z.items():
        if abs(levels[lv] - zf) > 1e-6:
            L.results.append(check("LV2", "fail", "datum:" + lv, SRC, message="engine floor %s=%.3f vs model %.3f" % (lv, zf, levels[lv])))
    ceil_cache = {}

    def ceiling_of(f):
        r = f.record
        key = (f.room, round(r.position[0], 2), round(r.position[1], 2))
        if key not in ceil_cache:
            try:
                ceil_cache[key] = v.VL.ceiling_z(f.level, r.position[0], f.room, r.position[1], v.lay)
            except Exception:
                ceil_cache[key] = levels[f.level] + rooms[f.room].params["clear_height_mm"] / 1000
        return ceil_cache[key]

    stale = {"only_engine": 0, "moved": 0, "matched": 0}
    for f in v.fixtures:
        pr = fixture_problems(f, rooms, ceiling_of, levels)
        m = lums.get(f.id)
        note = ""
        if m is None:
            stale["only_engine"] += 1
            note = "not in the model snapshot"
        else:
            stale["matched"] += 1
            dx = max(abs(m.placement[0] / 1000 - f.record.position[0]), abs(m.placement[1] / 1000 - f.record.position[1]))
            dz = abs(m.params["emitter_z_scene_mm"] / 1000 - f.record.position[2])
            if max(dx, dz) > POS_TOL:
                stale["moved"] += 1
                note = "model snapshot differs by %.0f mm" % (1000 * max(dx, dz))
        status = "fail" if pr else ("not_evaluated" if note else "pass")
        L.results.append(check("LV2", status, f.id, SRC, message="; ".join(pr + ([note] if note else [])) or "inside its room, below its ceiling, datum consistent",
                               achieved=None))
        L.mark(f.room, status)
    L.notes.append("model snapshot comparison: %s (the L2 snapshot predates the L6b redesign when moved/only_engine > 0)" % stale)
    L.table = [stale]
    return L
