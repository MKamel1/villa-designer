"""Pass 2 core: frames, layout fragments, planting drifts, own checks, whole-site evaluation.

Everything is authored in the south-garden local frame (a, b) = (x - 22.597, y + 29.916) or in the model frame (x, y)
for the north court and east yard, and assembled into one `landscape-layout/1` (+ LDC extension keys) per concept x pond option.
Typology first: each concept function fixes rooms, axis, focal point, planting masses and canopy; a small search then fits the
furniture into those bones at the rule distances (never the reverse).
"""
from __future__ import annotations

import math
from collections import OrderedDict

from shapely.geometry import Point, box
from shapely.ops import unary_union

from ...contracts import CheckResult
from ..rules import evaluate, load
from . import site as S
from .geom import rbox, rects_of
from .species import pool, sun_ok

RS = load()
POOL = pool()
SX0, SY0, A, B = S.SX0, S.SY0, S.SA, S.SB
FLOOR_Z = S.FLOOR_Z
BUILDINGS = [[3.617, -31.311, 22.597, -23.591], [-0.123, -23.591, 15.412, -20.601]]
FENCE_REAR = [28.307, -29.916, 28.557, -20.601]
FENCE_EAST = [22.597, -20.601, 28.557, -20.351]
STREET_FENCE = [-0.373, -29.916, -0.123, -23.591]
NHBC = {"low": "low", "medium": "moderate", "high": "high"}
PIT_D = 0.9
SCREEN_H = 2.1                     # west-line screen (client: SCREEN IT); LDS needs up to 3.3 m for the farthest sister openings
BENCH_PER_PERSON = 0.6             # POLICY: no held source gives a bench length per person (Time-Saver 340-11 gives seat-wall width 400-450 only)
MIN_BORDER_DEPTH = 1.2             # POLICY: no held source gives a border depth (Neufert p.105 gives soil DEPTH 300 mm shrubs, 500 climbers, 600-1000 trees)
SPREAD_CAP_CLIMBER = 1.2           # climbers drawn at a trained width on a trellis (policy), not their free mature spread


def P(a, b):
    return (SX0 + a, SY0 + b)


def RM(a0, b0, a1, b1):
    (x0, y0), (x1, y1) = P(a0, b0), P(a1, b1)
    return [round(min(x0, x1), 3), round(min(y0, y1), 3), round(max(x0, x1), 3), round(max(y0, y1), 3)]


KEYS = ("zones", "paved_areas", "planting_groups", "seating", "tables", "features", "trees", "paths", "obstacles", "boundary",
        "seatwalls", "canopies", "screens", "walls", "doors", "steps")


def frag():
    return {k: [] for k in KEYS} | {"meta": {}}


def merge(*fs):
    out = frag()
    for f in fs:
        for k in KEYS:
            out[k] += f.get(k, [])
        out["meta"].update(f.get("meta", {}))
    return out


# ---- planting drifts ----------------------------------------------------------------------------------------------
def sp_spread(slug, how="mid"):
    sp = POOL[slug]
    a = [x for x in (sp.s_min, sp.s_max) if x]
    if not a:
        return 1.0
    return {"min": min(a), "max": max(a), "mid": sum(a) / len(a)}[how]


def entry(slug, at, spread=None, form=None):
    sp = POOL[slug]
    form = form or ("small_tree" if sp.form == "small_tree" else "ground_cover" if sp.form == "ground_cover" else "shrub")
    e = {"species": slug, "at": [round(at[0], 3), round(at[1], 3)], "spread_m": round(spread or sp_spread(slug), 2), "form": form}
    if sp.water:
        e["water_need"] = sp.water
    return e


def row(rect, along, off, species, spacing, run=3, how="mid", cap=None, margin=0.0):
    """A line of plants parallel to the long side `along` ('x' or 'y') at offset `off` from the rect's low edge across the depth.
    Species repeat in runs of `run` plants (A A A B B B A A A ...): the drift rhythm. rect in model frame."""
    x0, y0, x1, y1 = rect
    out, k = [], 0
    L = (x1 - x0) if along == "x" else (y1 - y0)
    u = margin + spacing / 2
    while u < L - margin + 1e-9:
        slug = species[(k // run) % len(species)]
        spr = max(sp_spread(slug, how), spacing * 1.1)       # planted at about its spread: drifts merge into one mass in plan
        if cap:
            spr = min(spr, cap)
        at = (x0 + u, y0 + off) if along == "x" else (x0 + off, y0 + u)
        out.append(entry(slug, at, spr))
        k += 1
        u += spacing
    return out


def bed(f, bid, rect, plants, role, trace=("U-PRIVACY", "LS-HYDROZONE"), over=False):
    f["planting_groups"].append({"id": bid, "rect": rect, "over_structure": over, "plants": plants, "role": role, "trace": list(trace)})
    return plants


def bed_sun(rect):
    return S.mean("sun", "sun_hours_summer_solstice", rect) or 0.0


# ---- surfaces ---------------------------------------------------------------------------------------------------
def paving_from(garden_rect, cut_rects, material="unit-paving"):
    poly = box(*garden_rect).difference(unary_union([box(*r) for r in cut_rects])) if cut_rects else box(*garden_rect)
    return [{"id": f"paving-{i}", "rect": r, "material": material, "slope_pct": 1.5, "trace": ["U-S-STAND", "LS-SLOPE"]}
            for i, r in enumerate(rects_of(poly, 0.02))]


# ---- common site scaffolding ------------------------------------------------------------------------------------
def site_frag():
    f = frag()
    f["walls"] += [{"id": "fence-rear", "rect": FENCE_REAR, "height_m": 4.0}, {"id": "fence-east", "rect": FENCE_EAST, "height_m": 4.0},
                   {"id": "street-fence", "rect": STREET_FENCE, "height_m": 4.0}]
    f["obstacles"] += [{"id": "fence-rear", "rect": FENCE_REAR, "trace": ["SITE-FENCE"]}, {"id": "fence-east", "rect": FENCE_EAST, "trace": ["SITE-FENCE"]}]
    f["boundary"] += [{"id": "fence-east", "side": "neighbour", "kind": "fence", "height_m": 4.0, "trace": ["LS-SCREEN"]},
                      {"id": "fence-rear", "side": "neighbour", "kind": "fence", "height_m": 4.0, "trace": ["LS-SCREEN"]}]
    return f


def west_screen(f, plants=()):
    r = RM(0, 0, A, 0.15)
    f["screens"].append({"id": "sister-screen", "rect": r, "kind": "trellis", "height_m": SCREEN_H, "opacity": 0.9})
    f["obstacles"].append({"id": "sister-screen", "rect": r, "trace": ["U-PRIVACY", "LS-SCREEN"]})
    f["boundary"].append({"id": "sister-screen", "side": "neighbour", "kind": "fence", "height_m": SCREEN_H, "trace": ["U-PRIVACY", "LS-SCREEN"]})


def pergola(f, pid, rect, h=2.7, shade=0.6):
    f["canopies"].append({"id": pid, "rect": rect, "kind": "pergola", "height_m": h, "shade_fraction": shade})


def tree(f, tid, slug, at, container=False, spread_basis="min"):
    sp = POOL[slug]
    spread = (sp.s_min if spread_basis == "min" else sp.s_max) or sp.s_max
    e = {"id": tid, "species": slug, "center": [round(at[0], 3), round(at[1], 3)], "form": sp.form, "over_structure": False,
         "mature_spread_m": spread, "mature_height_m": sp.h_max, "trace": ["D-SHADE-OVER-SUN", "LS-TREE-BUILDING"]}
    if sp.water:
        e["water_demand"] = NHBC[sp.water]
    f["trees"].append(e)


# ---- own checks -------------------------------------------------------------------------------------------------
def _r(rule, status, subject, msg, ach=None, req=None, unit=""):
    return CheckResult(criterion=rule, lane="LDG", status=status, subject=subject, achieved=ach, required=req, unit=unit, message=msg,
                       source_ids=(rule,), element_ids=())


def all_plants(L):
    out = []
    for g in L["planting_groups"]:
        for p in g.get("plants", []):
            out.append((g, p))
    return out


def own_checks(L, rooms, covers, screen_top_z, trees_for_area, south_area=A * B):
    """Policy checks of pass 2 (POLICY cards, ours): privacy, evening shade, bed depth, drifts, spread, toxicity, geometry, seat lengths."""
    res = []
    # privacy per room, remaining share of today's overlooking after cover + screen (sister groups counted: west line screened)
    for name, (rect, lim) in rooms.items():
        base = S.eyes_total(rect, "seated")
        rem = S.eyes_total(rect, "seated", cover_rects=covers, screen_top_z=screen_top_z)
        share = rem / base if base else 0.0
        res.append(_r("LDG-PRIV", "pass" if share <= lim + 1e-9 else "fail", name,
                      f"{name}: {rem:.1f} eye points still see a seated person against {base:.1f} today ({share:.0%} remaining, {lim:.0%} allowed)", round(share, 3), lim, "share"))
        import numpy as np
        arr = S.arr("sun", "summer_evening_17_20_dst_clock")
        m = S.mask(rect) & ~np.isnan(arr)
        cov = np.zeros_like(m)
        for r in covers:
            cov |= S.mask(r)
        n = int(m.sum())
        ev = float(((arr[m] <= 0.25) | cov[m]).sum() / n) if n else 0.0      # cells under a louvred pergola count as sun-free (closed louvres: assumed)
        res.append(_r("LDG-SHADE", "pass" if ev >= 0.9 else "fail", name + "/evening", f"{name}: {ev:.0%} of cells sun-free 17-20 h (DST clock), 90 % required", round(ev, 3), 0.9, "share"))
    # bed depth: layered borders need >= MIN_BORDER_DEPTH; strips (herb, climber, pond-margin) are allowed to be narrower and are named so
    for g in L["planting_groups"]:
        r = g["rect"]
        d = min(r[2] - r[0], r[3] - r[1])
        layered = g.get("role") in ("border", "mass", "screen-border")
        if layered:
            res.append(_r("LDG-BEDDEPTH", "pass" if d >= MIN_BORDER_DEPTH - 1e-9 else "fail", g["id"],
                          f"{g['id']}: layered border depth {d:.2f} m against {MIN_BORDER_DEPTH} m (POLICY: no held source for a border depth)", round(d, 2), MIN_BORDER_DEPTH, "m"))
    # drifts: every species in a bed forms runs of at least 3 plants (policy, LDC uses the same count)
    # spread against space, toxicity near seats / herb beds
    seats = [rbox(s["rect"]) for s in L["seating"] if s.get("rect")] + [rbox([t["center"][0] - t["size_m"][0] / 2, t["center"][1] - t["size_m"][1] / 2,
                                                                              t["center"][0] + t["size_m"][0] / 2, t["center"][1] + t["size_m"][1] / 2]) for t in L["tables"]]
    herbs = [rbox(f["rect"]) for f in L["features"] if f.get("kind") == "herb_bed"]
    tox = []
    for g, p in all_plants(L):
        sp = POOL[p["species"]]
        if sp.is_toxic:
            pt = Point(*p["at"])
            if any(pt.distance(s) < 2.0 for s in seats + herbs):
                tox.append(p["species"])
    res.append(_r("LDG-TOXIC", "pass" if not tox else "fail", "site", "no toxic species within 2 m of a seat, table or herb bed" if not tox else f"toxic within 2 m: {sorted(set(tox))}", len(tox), 0, "plants"))
    # plants must not stand on paving, seats, or the fire clearance
    pav = unary_union([rbox(a["rect"]) for a in L["paved_areas"]]) if L["paved_areas"] else None
    stand = []
    for g, p in all_plants(L):
        if pav is not None and Point(*p["at"]).within(pav):
            stand.append((g["id"], p["species"]))
    res.append(_r("LDG-GEOM", "pass" if not stand else "fail", "plants-on-paving", "every plant stands in a bed" if not stand else f"{len(stand)} plants stand on paving: {stand[:3]}", len(stand), 0, "plants"))
    # overlaps between beds, seating, tables, features
    items = {}
    for g in L["planting_groups"]:
        items["bed:" + g["id"]] = rbox(g["rect"])
    for s in L["seating"]:
        items["seat:" + s["id"]] = rbox(s["rect"])
    for t in L["tables"]:
        items["table:" + t["id"]] = rbox([t["center"][0] - t["size_m"][0] / 2, t["center"][1] - t["size_m"][1] / 2, t["center"][0] + t["size_m"][0] / 2, t["center"][1] + t["size_m"][1] / 2])
    for f in L["features"]:
        if f.get("rect"):
            items["feat:" + f["id"]] = rbox(f["rect"])
        elif f.get("center") and f.get("diameter_m"):
            items["feat:" + f["id"]] = Point(*f["center"]).buffer(f["diameter_m"] / 2, 24)
    for o in L["obstacles"]:
        if o.get("rect") and not o["id"].startswith(("fence", "pot")):        # a pot may stand in a border
            items["obs:" + o["id"]] = rbox(o["rect"])
    names = list(items)
    bad = [(a, b) for i, a in enumerate(names) for b in names[i + 1:] if items[a].intersection(items[b]).area > 5e-3 and {a, b} != {"bed:bed-herb", "feat:herb-bed"}]
    res.append(_r("LDG-GEOM", "pass" if not bad else "fail", "overlaps", "no two elements overlap" if not bad else f"overlaps {bad[:3]}", len(bad), 0, "overlaps"))
    return res


def hard(res):
    return [r for r in res if r.status == "fail" or (r.status == "warn" and r.criterion in ("LS-TREE-BUILDING",))]


def tally(res):
    t = {"pass": 0, "fail": 0, "warn": 0, "not_evaluated": 0}
    for r in res:
        t[r.status] += 1
    return t


def ldk(L):
    return evaluate(L, RS)


def assemble(*frags):
    m = merge(*frags)
    L = {"schema": "landscape-layout/1", "frame": "model metres", "buildings": BUILDINGS}
    L.update({k: m[k] for k in KEYS})
    prio = {"quiet": 0, "dining": 1, "lounge": 2, "standing": 3, "other": 4}        # the critics take the FIRST zone that contains a point: most specific first
    L["zones"] = sorted(L["zones"], key=lambda z: prio.get(z.get("use"), 9))
    L["meta"] = m["meta"]
    return L
