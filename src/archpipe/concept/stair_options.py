"""Stair options for the villa, scored on the client's openness goal: as much open basement as possible that sees
the back garden, and the view from the basement entrance through to the garden (villa_01 brief: "Sightlines: ensure
the view from the entrance looks through the room to the garden"; main walkway 1.20 m dining-to-garden).

Each option is a stair (3D, concept/stairs.py) plus where the closed rooms go (flex room kept by the client; dirty
kitchen and guest WC either mid-spine by the shaft, or clustered at the street end). Metrics are measured, not
judged:
  - garden_view_m2: open basement floor (not a closed room, not the stair) from which a straight sight line reaches
    the rear glazing (inner face of the rear wall, between the rear columns), at eye level, past every closed room,
    column and the stair footprint;
  - entrance_view: share of the rear glazing visible from the basement entrance door;
  - clashes (3D, columns and beams), new GF slab opening, core doors to move, facade length the stair takes on the GF.
Coordinates in m (Revit axes), as concept.villa.
"""
from __future__ import annotations

import math

from . import stairs as S
from . import villa as V

XR_IN = V.XR - V.EXT_WALL
GLAZING = (XR_IN, -28.161, -24.101)          # rear inner face between the rear columns' faces (CAD)
FLEX_FRONT = (V.X0, V.YC, V.SX0, V.YE)       # flex room as in concept A
SERVICES_MID = [(11.397, V.YP, 13.797, V.YK), (13.797, V.YP, 15.197, V.YK)]       # dirty kitchen, guest WC
SERVICES_FRONT = [(V.X0, V.YP, 5.55, V.YK), (5.55, V.YP, 6.94, V.YK)]              # beside the laundry, street window


def u_front_bay():
    """U-stair in the street-end bay, between the columns' faces x 3.977 and 7.017; flights 1.0 m, landing short
    of the east perimeter beam."""
    return S.u_stair(3977, 3977 + 2100, S.YC, 9, 8, 1000, 280, "U-stair in the street-end bay")


OPTIONS = [
    {"id": "S1", "name": "U-stair in the old stair bay (current A)", "stair": S.u_in_old_bay, "services": "mid",
     "flex": FLEX_FRONT, "entrance": (8.3, V.YP + 0.3), "opening": "existing (DWG), +0.37 m", "core_doors": "stay",
     "gf_facade_m": V.SX1 - V.SX0},
    {"id": "S2", "name": "U-stair in the old bay, services moved to the street end", "stair": S.u_in_old_bay,
     "services": "front", "flex": (V.X0, V.YK, V.SX0, V.YE), "entrance": (8.3, V.YP + 0.3),
     "opening": "existing (DWG), +0.37 m", "core_doors": "stay", "gf_facade_m": V.SX1 - V.SX0},
    {"id": "S3", "name": "U-stair in the street-end bay, services at the street end", "stair": u_front_bay,
     "services": "front-behind-stair", "flex": (6.077, V.YC, V.SX1, V.YE), "entrance": (8.3, V.YP + 0.3),
     "opening": "new 2.1 x 3.4 m at the street end; old opening infilled", "core_doors": "stay",
     "gf_facade_m": 2.1},
    {"id": "S4", "name": "Straight flight along the party wall, services at the street end",
     "stair": S.party_flight_fixed, "services": "front-beside-flight", "flex": (5.55, -27.471, 8.9, V.YE),
     "entrance": (15.0, V.YP + 0.3), "opening": "new 3.4 x 1.0 m along the party wall; old opening infilled",
     "core_doors": "both move (basement to the second lobby x 14.1-15.7; GF door onto the top landing)",
     "gf_facade_m": 0.0},
]


def stair_footprint(st):
    """Plan footprint of the stair (treads and landing), m."""
    bs = [p["box"] for p in st["parts"] if "headroom" not in p["what"]]
    return (min(b[0] for b in bs) / 1000, min(b[1] for b in bs) / 1000, max(b[3] for b in bs) / 1000,
            max(b[4] for b in bs) / 1000)


def _seg_hits_rect(p, q, r, eps=1e-9):
    """Does segment p-q pass through the interior of axis-aligned rectangle r (Liang-Barsky)?"""
    x0, y0, x1, y1 = r
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, p[0] - x0), (dx, x1 - p[0]), (-dy, p[1] - y0), (dy, y1 - p[1])):
        if abs(pp) < eps:
            if qq < 0:
                return False
        else:
            t = qq / pp
            if pp < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return False
    return t1 - t0 > 1e-6


def obstacles(opt):
    st = opt["stair"]()
    services = SERVICES_MID if opt["services"] == "mid" else SERVICES_FRONT
    if opt["services"] == "front-behind-stair":
        services = [(6.077, V.YP, 7.377, V.YK)]              # WC behind the stair; dirty kitchen by the laundry
    if opt["services"] == "front-beside-flight":             # the flight takes the party-wall spine at the front
        services = [(V.X0, -27.471, 5.55, -25.3), (V.X0, -25.3, 5.55, V.YE)]
    fp = stair_footprint(st)
    for r in services + [opt["flex"]]:                       # guard: no closed room may sit on the stair
        if min(r[2], fp[2]) - max(r[0], fp[0]) > 1e-3 and min(r[3], fp[3]) - max(r[1], fp[1]) > 1e-3:
            raise ValueError("%s: closed room %s overlaps the stair %s" % (opt["id"], r, fp))
    cols = [tuple(v / 1000 for v in c) for c in V.E.COLUMNS]
    return {"stair": stair_footprint(st), "flex": opt["flex"], "services": services, "columns": cols}


def analyse(opt, step=0.2):
    ob = obstacles(opt)
    blocks = [ob["stair"], ob["flex"]] + ob["services"] + ob["columns"]
    closed = [ob["stair"], ob["flex"]] + ob["services"]
    glaze = [(GLAZING[0], GLAZING[1] + (i + 0.5) * (GLAZING[2] - GLAZING[1]) / 12) for i in range(12)]
    x0, y0, x1, y1 = V.X0 + V.EXT_WALL, V.YP + V.EXT_WALL, XR_IN, V.YE - V.EXT_WALL
    seen, open_pts, pts = 0, 0, []
    nx, ny = int((x1 - x0) / step), int((y1 - y0) / step)
    for i in range(nx):
        for j in range(ny):
            p = (x0 + (i + 0.5) * step, y0 + (j + 0.5) * step)
            if any(r[0] <= p[0] <= r[2] and r[1] <= p[1] <= r[3] for r in closed + ob["columns"]):
                continue
            open_pts += 1
            vis = any(not any(_seg_hits_rect(p, g, r) for r in blocks) for g in glaze)
            seen += vis
            pts.append((p, vis))
    e = opt["entrance"]
    ent = sum(not any(_seg_hits_rect(e, g, r) for r in blocks) for g in glaze) / len(glaze)
    st = opt["stair"]()
    cl = S.clashes(st)
    return {"id": opt["id"], "name": opt["name"], "open_m2": round(open_pts * step * step, 1),
            "garden_view_m2": round(seen * step * step, 1), "garden_view_share": round(seen / open_pts, 2),
            "entrance_view_share": round(ent, 2), "clashes": sorted({h["structure"] for h in cl["hits"]}),
            "rise": round(st["rise"], 1), "going": st["going"],
            "pitch_deg": round(math.degrees(math.atan2(st["rise"], st["going"])), 1),
            "opening": opt["opening"], "core_doors": opt["core_doors"], "gf_facade_m": round(opt["gf_facade_m"], 2),
            "points": pts, "obstacles": ob}


OPEN_OCC = {"kitchen", "dining", "living", "hall", "corridor", "entrance", "landing"}


def analyse_layout(lay, step=0.2):
    """The same openness metric on a complete layout: closed rooms are the basement rooms that are not open plan
    (kitchen, dining, living, halls), plus the stair footprint and the columns; the entrance is the basement core
    door (the midpoint of the entry segment the layout uses)."""
    from . import revit_spec as R
    st = R._stair_model(lay)
    fp = stair_footprint(st)
    closed = [tuple(r["rect"]) for r in lay["rooms"].values()
              if r["level"] == "B" and r["occupancy"] not in OPEN_OCC and r["occupancy"] != "stair"]
    cols = [tuple(v / 1000 for v in c) for c in V.E.COLUMNS]
    ent = None
    for rid, lv, seg in lay["entries"]:
        if lv == "B":
            s = V.ENTRY_SEGMENTS["B"][seg]
            e = max(V.edges(lay["rooms"][rid]["rect"]), key=lambda e_: V.overlap_len(e_, s))
            lo, hi = max(e[2], s[2]), min(e[3], s[3])
            ent = ((lo + hi) / 2, e[1] + 0.3) if e[0] == "h" else (e[1] + 0.3, (lo + hi) / 2)
    opt = {"id": lay["id"], "name": lay["title"], "stair": lambda: st, "entrance": ent, "opening": "",
           "core_doors": "", "gf_facade_m": 0.0}
    ob = {"stair": fp, "flex": (0, 0, 0, 0), "services": closed, "columns": cols}
    blocks = [fp] + closed + cols
    glaze = [(GLAZING[0], GLAZING[1] + (i + 0.5) * (GLAZING[2] - GLAZING[1]) / 12) for i in range(12)]
    x0, y0, x1, y1 = V.X0 + V.EXT_WALL, V.YP + V.EXT_WALL, XR_IN, V.YE - V.EXT_WALL
    seen = n = 0
    pts = []
    for i in range(int((x1 - x0) / step)):
        for j in range(int((y1 - y0) / step)):
            p = (x0 + (i + 0.5) * step, y0 + (j + 0.5) * step)
            if any(r[0] <= p[0] <= r[2] and r[1] <= p[1] <= r[3] for r in [fp] + closed + cols):
                continue
            n += 1
            vis = any(not any(_seg_hits_rect(p, g, r) for r in blocks) for g in glaze)
            seen += vis
            pts.append((p, vis))
    evis = sum(not any(_seg_hits_rect(ent, g, r) for r in blocks) for g in glaze) / len(glaze) if ent else 0.0
    return {"open_m2": round(n * step * step, 1), "garden_view_m2": round(seen * step * step, 1),
            "garden_view_share": round(seen / n, 2), "entrance_view_share": round(evis, 2), "points": pts,
            "obstacles": ob, "entrance": ent}
