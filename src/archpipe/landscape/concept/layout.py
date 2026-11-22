"""Candidate (local a,b frame) -> `landscape-layout/1` (model frame) for the LDK `evaluate`, with traceability."""
from __future__ import annotations

from . import site as S
from .geom import rects_of
from .south import A, B, PIT_D, floor_of, standing_zone

BUILDINGS = [[3.617, -31.311, 22.597, -23.591], [-0.123, -23.591, 15.412, -20.601]]
FENCES = {"fence-rear": [28.307, -29.916, 28.557, -20.601], "fence-east": [22.597, -20.601, 28.557, -20.351]}
NHBC = {"low": "low", "medium": "moderate", "high": "high"}


def M(r):
    return S.rect_to_model(r)


def planting_entries(sp_slugs, pool):
    out = []
    for s in sp_slugs:
        p = pool[s]
        out.append({"species": s, "water_need": p.water, "form": p.form if p.form != "large_tree" else "shrub"})
    return out


def to_layout(c: dict, plan: dict | None, pool: dict) -> dict:
    """plan = {"beds": {bed_id: [species,...]}, "trees": [...]} from planting.py, or None (structure stage)."""
    trees_in = plan["trees"] if plan is not None else c["trees"]
    plan = plan or {"beds": {}, "trees": []}
    ax = lambda p: (S.SX0 + p[0], S.SY0 + p[1])          # noqa: E731
    L: dict = {"schema": "landscape-layout/1", "frame": "model metres; zone: south garden", "buildings": BUILDINGS}
    zones = [
        {"id": "dining", "use": "dining", "rect": M(c["dining"]), "enclosure_height_m": 4.0, "trace": ["U-S-DINE", "LS-DINE-AREA"]},
        {"id": "lounge", "use": "lounge", "rect": M(c["lounge"]), "enclosure_height_m": 4.0, "trace": ["U-S-LOUNGE", "U-S-FIRE", "LS-LOUNGE-AREA"]},
        {"id": "quiet", "use": "quiet", "rect": M(c["quiet"]["rect"]), "enclosure_height_m": 4.0, "trace": ["U-S-QUIET"]},
    ]
    sz = standing_zone(c)
    if sz:
        n = int((sz[2] - sz[0]) * (sz[3] - sz[1]) / 1.3)
        zones.append({"id": "standing", "use": "standing", "rect": M(sz), "design_people": n, "trace": ["U-S-STAND", "LS-STAND-AREA"]})
    L["zones"] = zones
    t = c["table"]
    L["tables"] = [{"id": "dining-table", "zone": "dining", "center": ax(t["center"]), "size_m": [t["size"][0], t["size"][1]],
                    "seats": t["seats"], "trace": ["U-S-DINE", "LS-DINE-CLEAR"]}]
    seating = []
    for i, s in enumerate(c["seats"]):
        seating.append({"id": f"lounge-seat-{i}" if not s.get("wall") else "seat-wall", "zone": "lounge", "rect": M(s["rect"]), "seats": s["seats"],
                        "trace": ["U-S-LOUNGE", "LS-FIRE-SEAT"]})
    q = c["quiet"]
    seating.append({"id": "quiet-bench", "zone": "quiet", "rect": M(q["bench"]), "seats": 2, "trace": ["U-S-QUIET"]})
    L["seating"] = seating
    L["seatwalls"] = [{"id": "seat-wall", "height_mm": 450, "width_mm": 450, "trace": ["LS-SEATWALL"]}] if any(s.get("wall") for s in c["seats"]) else []
    overhead = 99 if not any(r == list(c["lounge"]) for r in c["cover"]) else 3.0
    feats = [
        {"id": "firepit", "kind": "firepit", "center": ax(c["pit"]["center"]), "diameter_m": PIT_D, "flush": True, "fuel": "gas",
         "cover": {"load_rating_kN": 15.0, "lip_mm": 6.0, "bevelled": False, "max_opening_mm": 12.0}, "overhead_clear_m": overhead,
         "trace": ["U-S-FIRE", "D-FLUSH", "LS-FIRE-CLEAR", "LS-FIRE-COVER"]},
        {"id": "bbq", "kind": "bbq", "rect": M(c["bbq"]), "trace": ["U-S-BBQ", "LS-FIRE-CLEAR"]},
    ]
    beds, trees = [], []
    for b in c["beds"]:
        sp = plan["beds"].get(b["id"], {}).get("species", [])
        beds.append({"id": b["id"], "rect": M(b["rect"]), "over_structure": False, "plants": planting_entries(sp, pool),
                     "trace": ["U-PRIVACY" if b["role"] in ("screen", "south", "east-edge") else "U-S-HERB" if b["role"] == "herb" else "U-S-QUIET", "LS-HYDROZONE"]})
        if b["role"] == "herb":
            sun = S.mean("sun", "sun_hours_summer_solstice", M(b["rect"]))
            feats.append({"id": "herb-bed", "kind": "herb_bed", "rect": M(b["rect"]), "midsummer_sun_hours": round(sun, 2) if sun is not None else None,
                          "trace": ["U-S-HERB", "LS-HERB-SUN"]})
    L["planting_groups"] = beds
    L["features"] = feats
    for i, tr in enumerate(trees_in):
        p = pool[tr["species"]]
        e = {"id": f"tree-{i}-{tr['species']}", "species": tr["species"], "center": ax(tr["center"]), "form": p.form, "over_structure": False,
             "trace": ["D-SHADE-OVER-SUN", "LS-TREE-BUILDING"]}
        if p.s_max:
            e["mature_spread_m"] = p.s_max
            e["canopy_r_m"] = (p.s_min or p.s_max) / 2          # drawn radius: the sourced minimum spread (trained tree)
        if p.h_max:
            e["mature_height_m"] = p.h_max
        if p.water:
            e["water_demand"] = NHBC[p.water]
        if tr.get("container"):
            e["container"] = True
        trees.append(e)
    L["trees"] = trees
    L["paved_areas"] = [{"id": f"paving-{i}", "rect": r, "material": "unit-paving", "slope_pct": 1.5, "trace": ["U-S-STAND", "LS-SLOPE"]}
                        for i, r in enumerate(rects_of_model(c))]
    L["paths"] = [{"id": "path-door", "class": "main", "width_m": 1.2, "cross_slope_pct": 1.5, "rect": M(c["path"]), "trace": ["U-ACCESS", "LS-PATH-MAIN"]}]
    L["obstacles"] = [{"id": k, "rect": r, "trace": ["SITE-FENCE"]} for k, r in FENCES.items()]
    for i, pt in enumerate(c.get("pots", [])):
        L["obstacles"].append({"id": f"pot-{i}-plumeria", "rect": M(pt["rect"]), "trace": ["D-FRANGIPANI", "D-TERRACOTTA"]})
    L["boundary"] = [{"id": "fence-east", "side": "neighbour", "kind": "fence", "height_m": 4.0, "trace": ["LS-SCREEN"]},
                     {"id": "fence-rear", "side": "neighbour", "kind": "fence", "height_m": 4.0, "trace": ["LS-SCREEN"]}]
    if c["screen_top_h"]:
        sc = S.SY0 + 0.15
        L["obstacles"].append({"id": "sister-screen", "rect": [S.SX0, S.SY0, S.SX0 + A, sc], "trace": ["U-PRIVACY", "LS-SCREEN"]})
        L["boundary"].append({"id": "sister-screen", "side": "neighbour", "kind": "fence", "height_m": c["screen_top_h"], "trace": ["U-PRIVACY", "LS-SCREEN"]})
    return L


def rects_of_model(c):
    return [M(r) for r in rects_of(floor_of(c))]
