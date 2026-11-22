"""The stair's steel as model data (lane SC2). ASSUMED: dimensions as the scene builder draws them, pending an engineer.

The scene builder (concept/villa_render.py) drew the wall-stringer bearings, wall plate, open-side stringer and glass
shoe while the model held none of them ("add to Revit"). Joinery under the flight must yield to this structure, so the
offsets live here once and both sides read them. Metres, scene datum, y positive towards the lounge."""
from ..concept import stair_mounting as SM

BEARING_OVER_M = 0.025                 # wall stringer bearing reaches 25 mm past the tread's wall-side edge
OPEN_STRINGER_M = (0.055, 0.025)       # open-side stringer: outer / inner face, inboard of the tread's open edge
GLASS_SHOE_M = (0.065, 0.025)          # base shoe under the glass: outer / inner face
BASIS = "ASSUMED stair steel as built in the scene (villa_render), pending structural engineer sizing"


def _treads(sp):
    return sorted((b for b in sp["stair"] if b[5] - b[2] < 300), key=lambda b: b[0])


def clear_y(sp):
    """(wall_side_y, open_side_y): the y planes the steel leaves free under the flight."""
    t = _treads(sp)
    return (round(min(b[1] for b in t) / 1000 + BEARING_OVER_M, 4), round(max(b[4] for b in t) / 1000 - GLASS_SHOE_M[0], 4))


def members(sp):
    """Steel members keyed by the scene mesh id that builds them, with their y extent (mm)."""
    t = _treads(sp)
    wall_y, open_y = clear_y(sp)
    plate0 = SM.finished_y(SM.wall_host(sp)) + SM.PLATE_CLEARANCE_M
    out = [dict(id="detail-stair-wall-stringer-%02d" % n, role="wall stringer and tread bearing", y1_mm=round(b[1] + BEARING_OVER_M * 1000, 1))
           for n, b in enumerate(t)]
    out.append(dict(id="detail-stair-wall-plate", role="continuous wall stringer plate",
                    y0_mm=round(plate0 * 1000, 1), y1_mm=round((plate0 + SM.PLATE_WIDTH_M) * 1000, 1)))
    ob = max(b[4] for b in t)
    out.append(dict(id="detail-stair-open-stringer", role="continuous open-side steel stringer",
                    y0_mm=round(ob - OPEN_STRINGER_M[0] * 1000, 1), y1_mm=round(ob - OPEN_STRINGER_M[1] * 1000, 1)))
    out.append(dict(id="detail-stair-glass-shoe", role="steel base shoe under the stair glass",
                    y0_mm=round(ob - GLASS_SHOE_M[0] * 1000, 1), y1_mm=round(ob - GLASS_SHOE_M[1] * 1000, 1)))
    return [dict(m, basis=BASIS) for m in out]
