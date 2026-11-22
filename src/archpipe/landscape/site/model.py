"""What the model holds about the site: zones, surface classes, openings and viewers.

All geometry comes from `villa_env` (CAD/Revit measured, brief, or assumed - each flagged there) and
`concept.revit_spec` (our openings). Nothing here is invented; values the model lacks are listed in GAPS.
"""
from __future__ import annotations

import numpy as np

from ... import villa_env as E
from . import grid as G

FT = E.FENCE_T / 1000.0
PX0, PY0, PX1, PY1 = (v / 1000 for v in E.plot())
AXIS = E.AXIS_Y / 1000.0
BAR = tuple(v / 1000 for v in E.BAR)
X0I, X1I, Y1I = PX0 + FT, PX1 - FT, PY1 - FT          # inner faces of the street, rear and east fences
FENCE_TOP_Z = (E.B + E.FENCE_H) / 1000.0               # 4.00 m from the basement floor
GROUND_Z = E.B / 1000.0                                # yard floor, -3.0
EYE_STANDING, EYE_SEATED = 1.525, 1.125                # Time-Saver 2nd ed. p.340-4 note 3 (fig 340-8, p.340-7)
LEVEL_Z = {"B": -3.0, "GF": 0.0, "APT": 3.0}           # APT = ASSUMED same 3.0 m storey (villa_env ASSUMPTIONS)

# garden zones (client names), model rectangles to the fences' inner faces; the west side is the open line to the sister plot
ZONES = {
    "north-garden": (X0I, AXIS, BAR[0], BAR[3], "street-side sunken court, client NORTH"),
    "east-ramp": (X0I, BAR[3], 6.877, Y1I, "east strip: car ramp, z -1.2..0 (structure over the basement)"),
    "east-deck": (6.877, BAR[3], 12.777, Y1I, "east strip: parking deck, top z 0.0 (structure)"),
    "east-roof": (12.777, BAR[3], 15.412, Y1I, "east strip: extension roof, top z 0.0 (structure, planted per the current design)"),
    "east-yard": (15.412, BAR[3], BAR[2], Y1I, "open sunken yard in front of the dirty kitchen and the dining/living doors, z -3.0"),
    "south-garden": (BAR[2], AXIS, X1I, Y1I, "rear (south) sunken garden, z -3.0"),
}
CLASSES = {0: "outside", 1: "ground", 2: "covered-ground", 3: "ramp", 4: "deck", 5: "roof", 6: "steps-block",
           7: "yard-wall", 8: "fence", 9: "building", 10: "thin-solid (cell centre inside a modelled guard rail)"}
ANALYSED = (1, 2, 3, 4, 5)
RAMP_PROFILE = [(-0.123, -1.2), (0.877, -1.1), (5.877, -0.1), (6.877, 0.0)]   # concept.revit_spec parking2.ramp
STEPS = (X0I, AXIS, BAR[0], -28.671)                   # entrance-steps box (villa_env) inside our half of the core strip
YARD_WALL = tuple(v / 1000 for v in E.YARD_WALL)
GF_TERRACE = tuple(v / 1000 for v in E.FRONT)          # GF slab over the north court, x 1.787..3.617


def classify():
    """(class code array, surface z array) on the grid. z is NaN where a cell is not analysed."""
    X, Y = G.centres()
    cls = np.zeros(X.shape, int)
    zs = np.full(X.shape, np.nan)
    inplot = (X >= PX0) & (X < PX1) & (Y >= AXIS) & (Y < PY1)
    cls[inplot] = 9                                    # building unless a zone claims it
    for name, (x0, y0, x1, y1, _) in ZONES.items():
        m = G.rect_mask(x0, y0, x1, y1)
        code = {"east-ramp": 3, "east-deck": 4, "east-roof": 5}.get(name, 1)
        cls[m] = code
        zs[m] = GROUND_Z
    ramp = cls == 3
    xr, zr = zip(*RAMP_PROFILE)
    zs[ramp] = np.interp(X[ramp], xr, zr)
    zs[(cls == 4) | (cls == 5)] = 0.0
    cls[G.rect_mask(*STEPS)] = 6
    cls[G.rect_mask(*YARD_WALL)] = 7
    # fences: the 250 mm bands inside the plot line (street, rear, east); not on the open sister line
    for x0, y0, x1, y1 in ((PX0, AXIS, X0I, PY1), (X1I, AXIS, PX1, PY1), (PX0, Y1I, PX1, PY1)):
        cls[G.rect_mask(x0, y0, x1, y1)] = 8
    cls[G.rect_mask(*GF_TERRACE)] = np.where(cls[G.rect_mask(*GF_TERRACE)] == 1, 2, cls[G.rect_mask(*GF_TERRACE)])
    # a 50 mm guard rail is a solid in the model: a cell centre inside it is not a place anyone stands
    from . import raycast as RC
    idx = np.argwhere(np.isin(cls, ANALYSED))
    pts = [(X[j, i], Y[j, i], zs[j, i] + 0.05) for j, i in idx]
    for (j, i), inside in zip(idx, RC.inside_solid(pts)):
        if inside:
            cls[j, i] = 10
    zs[~np.isin(cls, ANALYSED)] = np.nan
    return cls, zs


def zone_of_cells():
    """(NY, NX) array of zone index into list(ZONES) (-1 where none)."""
    z = np.full((G.NY, G.NX), -1, int)
    for k, (x0, y0, x1, y1, _) in enumerate(ZONES.values()):
        z[G.rect_mask(x0, y0, x1, y1)] = k
    return z


# ---------------------------------------------------------------------------------------------- openings
def _face(o):
    """(normal(2), face coordinate, centre-along-face) of an exterior opening, or None."""
    x, y = o["x"], o["y"]
    if abs(x - BAR[0]) < 1e-3:
        return (-1, 0), x, y
    if abs(x - BAR[2]) < 1e-3:
        return (1, 0), x, y
    if abs(x - 15.412) < 1e-3:
        return (1, 0), x, y
    if abs(y - BAR[3]) < 1e-3:
        return (0, 1), y, x
    return None


def our_openings():
    """Every exterior door/window of ours with a face normal: dict(id, level, room, kind, n, f, c, w, sill, head)."""
    from ...concept import revit_spec as RS, villa_r11 as R
    sp = RS.build(R.design("D1"))
    out = []
    for kind, items in (("door", sp["doors"]), ("window", sp["windows"])):
        for k, o in enumerate(items):
            fc = _face(o)
            if fc is None:
                continue
            n, f, c = fc
            both = o.get("rooms") or [o.get("room")]
            if kind == "door" and not {"yard", "deck"} & set(both):
                continue                               # internal door that happens to lie on an exterior-wall line
            rooms = [r for r in both if r not in ("yard", "deck", "core", None)]
            out.append(dict(id="%s-%s-%d" % (kind, o["level"], k), level=o["level"], room=rooms[0] if rooms else "?",
                            kind=kind, n=n, f=f, c=c, w=o["width"], sill=o.get("sill", 0.0) if kind == "window" else 0.0,
                            head=(o.get("sill", 0.0) + o["height"]) if kind == "window" else o["height"],
                            garden=bool(o.get("garden"))))
    return out


def opening_zone(o, cls=None, zone_idx=None):
    """Garden zone an opening looks onto: the zone cell 0.75 m outside its centre ('' when none)."""
    zone_idx = zone_of_cells() if zone_idx is None else zone_idx
    px = (o["f"] if o["n"][0] else o["c"]) + o["n"][0] * 0.75
    py = (o["f"] if o["n"][1] else o["c"]) + o["n"][1] * 0.75
    i, j = int((px - G.ORIGIN_X) // G.CELL), int((py - G.ORIGIN_Y) // G.CELL)
    if not (0 <= i < G.NX and 0 <= j < G.NY) or zone_idx[j, i] < 0:
        return ""
    return list(ZONES)[zone_idx[j, i]]


# ---------------------------------------------------------------------------------------------- viewers
def viewers():
    """Eye points that can overlook the garden. dict(id, group, eye(3), source)."""
    V = []
    off = 0.10 + 0.06                                  # clear of the 60 mm window box
    sill = E.WINDOW_SILL / 1000
    for e in E.spec()["elements"]:
        if e["category"] != "Windows":
            continue
        xs = [p[0] / 1000 for p in e["pts"]]; ys = [p[1] / 1000 for p in e["pts"]]
        group = "neighbour-east" if e["id"].startswith("neighbour-east") else "neighbour-rear"
        floor = e["z0"] / 1000 - sill
        eye = ((min(xs) + max(xs)) / 2, min(ys) - off, floor + EYE_STANDING) if group == "neighbour-east" \
            else (min(xs) - off, (min(ys) + max(ys)) / 2, floor + EYE_STANDING)
        V.append(dict(id=e["id"], group=group, eye=eye, source="villa_env neighbour window, position ASSUMED like ours"))
    for o in our_openings():
        n = o["n"]
        if o["level"] == "GF":
            # the apartment above repeats the GF openings +3.0 m (villa_env ASSUMPTIONS, client-confirmed 2026-09-25)
            V.append(dict(id="apt-" + o["id"], group="apartment-above", eye=_eye(o, 3.0, 0.10),
                          source="GF opening repeated +3.0 m (ASSUMED identical apartment)"))
        if n[0] == 0:
            continue                                   # only x-faces of the sister can see across the open line
        for lev in {"B": ("B",), "GF": ("GF", "APT")}[o["level"]]:
            eye = _eye(o, LEVEL_Z[lev], 0.10)
            V.append(dict(id="sister-%s-%s" % (lev, o["id"]), group="sister-openings",
                          eye=(eye[0], round(2 * AXIS - eye[1], 3), eye[2]),
                          source="mirror about the villa axis (BRIEF: sister mirrored)"))
    # apartment terrace over the north court: eyes just outside the solid parapet prism, on its north and east edges
    fx0, fy0, fx1, fy1 = GF_TERRACE
    for y in np.arange(fy0 + .5, fy1 - .4, 1.0):
        V.append(dict(id="apt-terrace-n-%.1f" % y, group="apartment-above", eye=(fx0 - .05, float(y), 3.0 + EYE_STANDING),
                      source="apartment terrace (villa_env apartment-above-front, ASSUMED use), north edge"))
    # sister's open yard: a standing person 1.0 m past the open line (no fence on the axis, villa_env ASSUMPTIONS)
    for x in np.arange(X0I + .5, X1I, 1.0):
        V.append(dict(id="sister-yard-%.1f" % x, group="sister-yard", eye=(float(x), AXIS - 1.0, GROUND_Z + EYE_STANDING),
                      source="standing eye at ground level in the sister's yard"))
    # shared entrance steps (modelled as a solid block to z 0.0: the real profile is unknown -> conservative)
    for x in (0.5, 1.5, 2.5, 3.4):
        V.append(dict(id="steps-%.1f" % x, group="entrance-steps", eye=(x, -29.3, 0.0 + EYE_STANDING),
                      source="walker on the shared entrance steps; block top z 0.0 used (conservative upper bound)"))
    # street pedestrian: negative control - the street fence is solid in the model, the gate is not modelled
    for y in np.arange(AXIS + 1, Y1I, 2.0):
        V.append(dict(id="street-%.1f" % y, group="street", eye=(PX0 - 1.0, float(y), E.STREET / 1000 + EYE_STANDING),
                      source="pedestrian on the street at +-0.00 (street z -1.2)"))
    return V


def _eye(o, floor_z, inset):
    n = o["n"]
    eye_z = min(max(floor_z + EYE_STANDING, floor_z + o["sill"] + 0.05), floor_z + o["head"] - 0.05)
    if n[0]:
        return (o["f"] + n[0] * inset, o["c"], eye_z)
    return (o["c"], o["f"] + n[1] * inset, eye_z)
