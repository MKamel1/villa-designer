"""Planting composition (stage LD-G step 4): layers, repeated drifts, one hydrozone per bed.

Only species in species.pool() (viable / viable_with_conditions). A species is used in a bed only if its sun class
is met by the bed's measured 21-June sun (policy thresholds in species.sun_ok), it is not toxic within 2 m of a seat
or herb bed, and its mature spread fits the bed (<= 2 x depth, or the support length for climbers).
"""
from __future__ import annotations

import math
import random

from shapely.geometry import box

from . import site as S
from .geom import rbox
from .species import Sp, sun_ok

CLIMBER = {"bougainvillea_glabra", "petrea_volubilis", "jasminum_sambac"}
GROUND = {"gazania_rigens", "origanum_majorana", "muhlenbergia_capillaris", "salvia_leucantha", "lantana_montevidensis"}
SHRUB = {"pittosporum_tobira", "dodonaea_viscosa", "callistemon_citrinus", "murraya_paniculata"}
AQUATIC = {"zantedeschia_aethiopica", "pontederia_cordata", "ceratophyllum_demersum"}
DRY_LOW = {"gazania_rigens", "origanum_majorana", "bougainvillea_glabra"}      # hydrozone low
# species never scheduled in these roles, with the reason recorded in the rejected list
ROLE_LAYERS = {
    "screen": ("climber", "ground"), "south": ("climber", "ground"), "edge": ("ground",), "herb": ("herb", "ground"),
    "orchard": ("climber", "ground"), "street": ("climber", "shrub"), "pond-edge": ("aquatic", "climber", "ground"), "yard": ("climber", "ground"),
    "east-edge": ("ground",),
}


def spread_mid(sp: Sp) -> float:
    a = [x for x in (sp.s_min, sp.s_max) if x]
    return sum(a) / len(a) if a else 1.0


def mid_h(sp):
    a = [x for x in (sp.h_min, sp.h_max) if x]
    return sum(a) / len(a) if a else 1.0


def layer_of(sp: Sp) -> str:
    if sp.slug in CLIMBER:
        return "climber"
    if sp.slug in AQUATIC:
        return "aquatic"
    if sp.slug == "origanum_majorana":
        return "herb"
    if sp.slug in GROUND:
        return "ground" if (sp.h_max or 1) <= 0.5 else "perennial"
    if sp.form in ("small_tree", "large_tree"):
        return "canopy"
    return "shrub"


def feasible(pool, role, june, depth, length, near_seat, rng, taken_flowers=()):
    """Species usable in this bed, per layer; each carries its sun result."""
    out = {}
    for sp in pool.values():
        lay = layer_of(sp)
        if lay not in ROLE_LAYERS[role] and not (lay == "perennial" and "ground" in ROLE_LAYERS[role]):
            continue
        if sp.is_toxic and near_seat:
            continue
        if sp.slug in ("lantana_montevidensis",):                 # toxic and invasive-flagged: never beside seats, herbs or a pond
            continue
        if sp.slug == "ceratophyllum_demersum":                    # submerged: lives in the water, never in a land bed
            continue
        if sp.slug == "pontederia_cordata" and role != "pond-edge":
            continue
        if role != "pond-edge" and sp.slug in AQUATIC:
            continue
        if lay == "canopy":
            continue
        if lay in ("ground", "perennial", "herb") and spread_mid(sp) > 2 * depth:
            continue
        if lay == "shrub" and spread_mid(sp) > 2 * depth:
            continue
        sun = sun_ok(sp, june) if sp.sun_classes else "unknown"
        if sun == "fail":
            continue
        if sp.slug == "ceratophyllum_demersum":
            sun = "unknown"
        out.setdefault(lay, []).append((sp, sun))
    return out


def plant_bed(bed: dict, rect_model: list, june: float, near_seat: bool, rng: random.Random, pool: dict, force_hz: str | None = None) -> dict:
    """Compose one bed. Returns {species: [...], instances: [{species, layer, count, positions}], hydrozone, notes}."""
    role = bed["role"]
    x0, y0, x1, y1 = rect_model
    w, h = x1 - x0, y1 - y0
    depth, length = min(w, h), max(w, h)
    along_y = h >= w
    feas = feasible(pool, role, june, depth, length, near_seat, rng)
    # one hydrozone per bed: pick the class with the most layers filled
    zones = {}
    for lay, lst in feas.items():
        for sp, sun in lst:
            zones.setdefault(sp.water, []).append((lay, sp, sun))
    if None in zones:                                  # water need is a GAP in LDL: kept as its own, unevaluated class
        zones["unknown"] = zones.pop(None)
    if not zones:
        return {"species": [], "instances": [], "hydrozone": None, "notes": ["no species fits this bed's sun and size"]}
    if force_hz and force_hz in zones:
        zones = {force_hz: zones[force_hz]}
    scored = sorted(zones.items(), key=lambda kv: (-len({l for l, _, _ in kv[1]}) + (0.5 if kv[0] == "unknown" else 0), rng.random()))
    hz, cands = scored[0] if rng.random() < .7 or len(scored) == 1 else scored[1]
    picks, seen = [], set()
    for lay in ROLE_LAYERS[role]:
        opts = [(sp, sun) for l, sp, sun in cands if (l == lay or (lay == "ground" and l == "perennial"))]
        rng.shuffle(opts)
        for sp, sun in opts[: (2 if lay in ("ground", "climber") and length > 2 else 1)]:
            if sp.slug not in seen:
                picks.append((lay if lay != "ground" else layer_of(sp), sp, sun))
                seen.add(sp.slug)
    inst = []
    # lay out: back row (climbers / shrubs) against the support side, front row ground / aquatic, in repeated drifts
    rows = {"back": [p for p in picks if p[0] in ("climber", "shrub")], "front": [p for p in picks if p[0] not in ("climber", "shrub")]}
    if not rows["back"] or depth < 0.55:
        rows["front"] += rows["back"] if depth >= 0.55 else []
        rows["back"] = rows["back"] if depth >= 0.55 else rows["back"]
    for rowname, plist in rows.items():
        if not plist:
            continue
        d0 = 0.0 if rowname == "back" else (depth * 0.45 if rows["back"] else 0.0)
        d1 = depth * 0.45 if rowname == "back" and rows["front"] else depth
        nseg = max(2, int(length / 1.3))
        for k in range(nseg):                                   # drifts A B A C B ...
            lay, sp, sun = plist[k % len(plist)] if len(plist) > 1 else plist[0]
            s = max(0.3, 0.8 * spread_mid(sp)) if lay != "climber" else 1.2
            a0, a1 = k * length / nseg, (k + 1) * length / nseg
            pts = []
            n_across = max(1, int((d1 - d0) / s))
            n_along = max(1, int((a1 - a0) / s))
            for i in range(n_along):
                for j in range(n_across):
                    u = a0 + (i + .5) * (a1 - a0) / n_along
                    v = d0 + (j + .5) * (d1 - d0) / n_across
                    pts.append((u, v))
            xy = [((x0 + (v if not along_y else v)) if True else 0, 0) for u, v in pts]
            xy = [(x0 + v, y0 + u) if along_y else (x0 + u, y0 + v) for u, v in pts]
            inst.append({"species": sp.slug, "layer": lay, "count": len(xy), "positions": xy, "sun": sun, "drift": k})
    # merge instances of the same species into one schedule row later; keep drifts for the plan
    species = sorted({i["species"] for i in inst})
    return {"species": species, "instances": inst, "hydrozone": hz, "notes": []}


def schedule(instances: list, pool: dict) -> list[dict]:
    """Planting schedule rows: species, count, layer, condition (carried from LDL), drawable flag."""
    rows = {}
    for i in instances:
        r = rows.setdefault(i["species"], {"species": i["species"], "layer": i["layer"], "count": 0, "sun": set()})
        r["count"] += i["count"]
        r["sun"].add(i.get("sun", ""))
    out = []
    for slug, r in sorted(rows.items(), key=lambda kv: (kv[1]["layer"], kv[0])):
        sp = pool[slug]
        out.append({"species": sp.name, "slug": slug, "count": r["count"], "layer": r["layer"], "verdict": sp.verdict,
                    "conditions": sp.conditions + ([f"sun {','.join(sorted(r['sun'] - {''}))} (21 Jun hours vs class)"] if r["sun"] - {""} else []),
                    "water": sp.water, "toxic": sp.toxic, "drawable": sp.drawable,
                    "mature_h_m": sp.h_max, "mature_spread_m": sp.s_max})
    return out
