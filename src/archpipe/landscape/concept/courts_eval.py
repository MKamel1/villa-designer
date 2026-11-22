"""Layouts, checks, planting and scores for the north court and east yard candidates (courts.py)."""
from __future__ import annotations

import random
from collections import Counter

from shapely.geometry import Point, box
from shapely.ops import unary_union

from ...contracts import CheckResult
from ..rules import evaluate
from . import checks as K, courts as CT, planting as PL, site as S
from .geom import rbox, rects_of
from .layout import BUILDINGS, planting_entries

ZONE_RECT = {"north": [CT.N_X0, CT.N_Y0, CT.N_X1, CT.N_Y1], "east": [CT.E_X0, CT.E_Y0, CT.E_X1, CT.E_Y1]}


def floor_rects(c):
    z = rbox(ZONE_RECT[c["zone"]])
    cut = [rbox(b["rect"]) for b in c["beds"]]
    if c["pond"]:
        cut.append(rbox(c["pond"]["rect"]))
    if c["zone"] == "north":
        cut.append(box(CT.N_X0 - 1, CT.N_Y0, CT.N_X1 + 1, CT.N_Y0))     # (nothing: the steps block lies outside the rect)
    return rects_of(z.difference(unary_union(cut)))


def plan_zone(c, rng, pool):
    plan = {"beds": {}, "trees": []}
    seats = [rbox(c["bench"])] if c.get("bench") else []
    for b in c["beds"]:
        june = S.mean("sun", "sun_hours_summer_solstice", b["rect"]) or 0.0
        near = any(rbox(b["rect"]).distance(s) < 2.0 for s in seats) or b["role"] == "herb"
        p = PL.plant_bed(b, b["rect"], june, near, rng, pool)
        p["june"] = round(june, 2)
        p["rect_local"] = b["rect"]
        plan["beds"][b["id"]] = p
    return plan


def to_layout(c, plan, pool):
    L = {"schema": "landscape-layout/1", "frame": f"model metres; zone: {c['zone']}", "buildings": BUILDINGS, "zones": [], "tables": [], "seating": [],
         "trees": [], "boundary": [], "obstacles": [], "seatwalls": []}
    if c.get("bench"):
        q = c["quiet"]
        L["zones"].append({"id": "quiet", "use": "quiet", "rect": q, "enclosure_height_m": 4.0, "trace": ["U-N-QUIET"]})
        L["seating"].append({"id": "bench", "zone": "quiet", "rect": c["bench"], "seats": 2, "trace": ["U-N-QUIET"]})
    L["paved_areas"] = [{"id": f"paving-{i}", "rect": r, "material": "unit-paving", "slope_pct": 1.5, "trace": ["U-ACCESS", "LS-SLOPE"]}
                        for i, r in enumerate(floor_rects(c))]
    L["paths"] = [{"id": "path-main", "class": "main", "width_m": 1.2, "cross_slope_pct": 1.5, "rect": c["path"], "trace": ["U-ACCESS", "LS-PATH-MAIN"]}]
    L["planting_groups"] = [{"id": b["id"], "rect": b["rect"], "over_structure": False,
                             "plants": planting_entries(plan["beds"].get(b["id"], {}).get("species", []), pool) if plan else [],
                             "trace": ["U-POND" if b["role"] == "pond-edge" else "U-HERB" if b["role"] == "herb" else "U-PRIVACY", "LS-HYDROZONE"]}
                            for b in c["beds"]]
    feats = []
    for b in c["beds"]:
        if b["role"] == "herb":
            sun = S.mean("sun", "sun_hours_summer_solstice", b["rect"])
            feats.append({"id": "herb-bed", "kind": "herb_bed", "rect": b["rect"], "midsummer_sun_hours": round(sun, 2) if sun is not None else None,
                          "trace": ["U-S-HERB", "LS-HERB-SUN"]})
    if c["pond"]:
        p = c["pond"]
        feats.append({"id": "pond", "kind": "pond", "rect": p["rect"], "flush": True, "edge": p["edge"], "freeboard_mm": p["freeboard_mm"],
                      "depth_mm": p["depth_mm"], "volume_m3": p["volume_m3_est"], "koi_count": p["koi_count"],
                      "koi_adult_length_cm": p["koi_adult_length_cm"], "aerated": p["aerated"], "child_protection": "rigid_grille",
                      "edge_slope_run_per_rise": 4, "margin_slope_back_mm": 600,
                      "trace": ["U-POND", "D-FLUSH", "LS-POND-GUARD", "LS-POND-DEPTH", "LS-POND-STOCK", "LS-POND-FLUSH-MARGIN"]})
    L["features"] = feats
    return L


def own_checks(c, plan, pool):
    res = []
    items = {b["id"]: rbox(b["rect"]) for b in c["beds"]}
    if c["pond"]:
        items["pond"] = rbox(c["pond"]["rect"])
    if c.get("bench"):
        items["bench"] = rbox(c["bench"])
    names = list(items)
    bad = [(a, b) for i, a in enumerate(names) for b in names[i + 1:] if items[a].intersection(items[b]).area > 1e-6]
    res.append(K.mk("GEOM", "pass" if not bad else "fail", c["zone"], "elements do not overlap" if not bad else f"overlaps {bad[:3]}", len(bad), 0, "overlaps"))
    if c.get("bench"):
        zr = ZONE_RECT["north"]
        e_q = S.eyes_total(c["quiet"], "seated", cover_rects=[c["quiet"]])
        e_z = S.eyes_total([CT.N_X0, CT.N_Y0, CT.N_X1, CT.N_Y1], "seated")
        share = e_q / e_z if e_z else 0
        res.append(K.mk("PRIV", "pass" if share <= 0.75 else "warn", "north/quiet",
                        f"quiet corner under a pergola: {e_q:.1f} eye points see a seated person against {e_z:.1f} for the court on average ({share:.0%}, 75 % target; "
                        "the remaining exposure comes across the entrance-steps block and no screen inside the court cuts it)",
                        round(share, 3), 0.75, "share"))
    if plan:
        reserved = [rbox(c["path"])] + ([rbox(c["bench"])] if c.get("bench") else [])
        res += K.planting_checks(c["zone"], c, plan, pool, reserved=reserved, seats=[rbox(c["bench"])] if c.get("bench") else [],
                                 herb_rects=[rbox(b["rect"]) for b in c["beds"] if b["role"] == "herb"])
    return res


def evaluate_zone(c, plan, pool, rs):
    L = to_layout(c, plan, pool)
    res = [r for r in evaluate(L, rs) if r.criterion not in ("LS-BRIEF-FEATURES", "LS-CAPACITY", "LS-STAND-AREA")]
    return L, res + own_checks(c, plan, pool)


def score_zone(c, L, res, plan):
    P = {}
    soft = sum((b["rect"][2] - b["rect"][0]) * (b["rect"][3] - b["rect"][1]) for b in c["beds"])
    zr = ZONE_RECT[c["zone"]]
    zone_area = (zr[2] - zr[0]) * (zr[3] - zr[1])
    P["lush"] = min(1.0, soft / zone_area / 0.4)
    if c.get("bench"):
        P["quiet"] = 1 - (S.eyes_total(c["quiet"], "seated", cover_rects=[c["quiet"]]) / max(S.eyes_total(zr, "seated"), 1e-9))
    if c["pond"]:
        r = c["pond"]["rect"]
        P["pond_view"] = min(1.0, (S.mean("views", "rooms_seeing_cell", r) or 0) / 3)
        P["pond_size"] = min(1.0, c["pond"]["area_m2"] / 6)
    sp = {i["species"] for p in plan["beds"].values() for i in p["instances"]}
    P["species"] = min(1.0, len(sp) / 6)
    P["warns"] = sum(1 for r in res if r.status == "warn")
    score = sum(v for k, v in P.items() if k != "warns") / max(1, len(P) - 1) - 0.01 * P["warns"]
    return round(score, 4), {k: round(v, 3) for k, v in P.items()}


def run_zone(zone, pond, n, seed, top_k, n_plant, pool, rs):
    sample = CT.sample_north if zone == "north" else CT.sample_east
    rng = random.Random(f"{seed}-{zone}-{pond}")
    stats = Counter()
    keep = []
    seen = set()
    for _ in range(n):
        c = sample(pond, rng)
        if c is None:
            stats["packing failed"] += 1
            continue
        stats["packed"] += 1
        L, res = evaluate_zone(c, None, pool, rs)
        hf = [r for r in K.hard_fails(res) if r.criterion not in ("LDG-SPREAD", "LDG-TOXIC", "LDG-HYDRO")]
        if hf:
            for r in {r.criterion for r in hf}:
                stats[r] += 1
            continue
        key = (tuple(round(x, 1) for x in (c["pond"]["rect"] if c["pond"] else c.get("bench", [0]))), tuple(round(b["rect"][0], 1) for b in c["beds"]))
        if key in seen:
            continue
        seen.add(key)
        keep.append(c)
    stats["no_hard_fail_distinct"] = len(keep)
    out = []
    tried = 0
    for c in keep[:top_k * 4]:
        for k in range(n_plant):
            tried += 1
            plan = plan_zone(c, random.Random(f"{seed}-{zone}-{pond}-p{tried}"), pool)
            L, res = evaluate_zone(c, plan, pool, rs)
            if K.hard_fails(res):
                continue
            sc, P = score_zone(c, L, res, plan)
            out.append({"score": sc, "parts": P, "cand": c, "plan": plan, "layout": L, "results": res})
    out.sort(key=lambda d: -d["score"])
    stats["planted_tried"], stats["survivors"] = tried, len(out)
    return out, dict(stats)
