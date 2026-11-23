"""Pass 2 runner: assemble the three typology concepts x two pond options, check, critique, draw, write knowledge/landscape/concept/pass2/."""
from __future__ import annotations

import json
import math
from pathlib import Path

from shapely.geometry import Point, box
from shapely.ops import unary_union

from . import site as S, ty_core as C, ty_courts as TC, ty_south as TS
from .species import sun_ok
from .ty_core import A, B, POOL, RM

OUT = S.ROOT / "knowledge" / "landscape" / "concept" / "pass2"
PREC = {"hard": (0.52, 0.82), "trees": (1.56, 3.26)}      # targets-2.json (frozen 2026-11-22), south_combined

# furniture parameters fitted at the rule distances (probe scripts, see docs/lanes/LDG.md); the typology fixes everything else
PARAMS = {
    "A": dict(tree=(4.8, 1.8), gravel_b1=4.0, bench_b0=1.9, bench_b1=6.9, table_a0=1.3, table_b0=2.55, pit=(2.5, 5.45), bbq=(2.0, 6.8), pot=(5.1, 8.35)),
    "B": dict(pit=(2.6, 2.7), bbq=(2.05, 4.05), table_a0=1.2, table_b0=5.75, east_b0=7.85, gravel=(3.2, 7.2, 5.6), wbench=(0.9, 5.2), rbench=(2.4, 7.2), tree=(4.4, 8.4), pot=(5.1, 7.5)),
    "C": dict(axis_b=4.0, pit=(2.45, 4.0), bbq=(2.0, 2.15), east_b0=8.05, tree=(3.4, 8.4), gravel=(2.2, 7.2, 4.7), rw_b1=2.6, table_a0=1.2, table_b0=5.95, wbench=(0.9, 4.3), qbench_b0=5.0, pot=(0.3, 8.7)),
}
SOUTH = {"A": TS.south_A, "B": TS.south_B, "C": TS.south_C}
NAMES = {"A": "Tree court", "B": "Two rooms", "C": "Axial terrace"}
HARD_WARN = ("LS-TREE-BUILDING", "LS-FIRE-STRUCT", "LS-HYDROZONE", "LS-FIRE-SEAT", "LS-ROOTZONE")     # LDK grades these "warn"; here a shortfall is a hard fail (LS-FIRE-CLEAR between 900 and 1200 mm stays a warning)


def seat_rooms(L):
    """Privacy and evening-shade are judged where people sit: the table (+0.6 m chairs) and each bench (+0.6 m), south and the quiet bench of the north court.
    (The LDK area rules use the larger room rectangles; those include circulation and are not a seated place.)"""
    rooms = {}
    ZB = [(22.597, -29.916, 28.307, -20.601), (15.412, -23.591, 22.597, -20.601), (-0.123, -28.671, 3.617, -23.841)]      # south garden, east yard, north court

    def clip(r):
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        z = next((b for b in ZB if b[0] <= cx <= b[2] and b[1] <= cy <= b[3]), None)
        return r if z is None else [max(r[0], z[0]), max(r[1], z[1]), min(r[2], z[2]), min(r[3], z[3])]

    for t in L["tables"]:
        cx, cy = t["center"]
        w, h = t["size_m"]
        rooms["table"] = (clip([cx - w / 2 - 0.6, cy - h / 2 - 0.6, cx + w / 2 + 0.6, cy + h / 2 + 0.6]), 0.30)
    for s_ in L["seating"]:
        x0, y0, x1, y1 = s_["rect"]
        north = s_["rect"][0] < 20          # north court bench: policy 75 % (the exposure comes across the steps block and street; pass 1 used the same)
        rooms[s_["id"]] = (clip([x0 - 0.6, y0 - 0.6, x1 + 0.6, y1 + 0.6]), 0.75 if north else 0.25 if "quiet" in s_["id"] else 0.30)
    return rooms


def build(concept, pond_where):
    fs, rs, cs = SOUTH[concept](PARAMS[concept])
    fn, rn, cn = TC.build_court(TC.north_kit(concept, pond_where == "north"), "n")
    fe, re_, ce = TC.build_court(TC.east_kit(concept, pond_where == "east"), "e")
    L = C.assemble(C.site_frag(), fs, fn, fe)
    free = free_floor(L)                                   # the standing zone declares the people the FREE floor holds (not the zone rectangle, which includes furniture)
    for z in L["zones"]:
        if z.get("use") == "standing":
            area = (z["rect"][2] - z["rect"][0]) * (z["rect"][3] - z["rect"][1])
            z["design_people"] = min(int(free / 1.3), int(area / 1.3))
    rooms = seat_rooms(L)
    covers = [c["rect"] for c in L["canopies"]]
    return L, rooms, covers


def hard_fails(res):
    return [r for r in res if r.status == "fail" or (r.status == "warn" and r.criterion in HARD_WARN)]


def sun_checks(L):
    out, seen = [], {}
    for g in L["planting_groups"]:
        june = C.bed_sun(g["rect"])
        for p in g["plants"]:
            sp = POOL[p["species"]]
            res = sun_ok(sp, june)
            seen.setdefault((g["id"], p["species"]), (res, june))
    bad = [(k, v) for k, v in seen.items() if v[0] == "fail"]
    out.append(C._r("LDG-SUNFIT", "pass" if not bad else "fail", "site", "every plant's sun class is met by its bed's 21-June sun (policy thresholds: part shade 2 h, 1.5 h conditional)"
                    if not bad else f"sun class not met: {[(k, round(v[1], 1)) for k, v in bad][:4]}", len(bad), 0, "bed-species"))
    return out, seen


def tree_checks(L):
    res = []
    for t in L["trees"]:
        cx, cy = t.get("crown_center") or t["center"]          # the pruned head may lean off the trunk (final.shade_tree)
        if cx < 20:
            continue
        r = t["mature_spread_m"] / 2
        circ = Point(cx, cy).buffer(r, 24)
        allow = box(S.SX0 - 0.0, S.SY0 + 0.0, S.SX0 + A + 0.3, S.SY0 + B + 0.3)
        if cx < S.SX0:                                   # east yard (x 15.4-22.6, y -23.6..-20.6): its own walls, and the open mouth into the south garden
            allow = unary_union([box(15.412, -23.591, S.SX0, -20.601 + 0.3), allow])
        out = circ.difference(allow).area
        res.append(C._r("LDG-SPREAD", "pass" if out < 1e-6 else "fail", t["id"], f"{t['id']}: canopy radius {r:.2f} m (sourced minimum spread {t['mature_spread_m']} m), {out:.2f} m2 outside the garden (0.3 m over the fences allowed)", round(out, 2), 0, "m2"))
    return res


def extension_checks(L):
    """Does the table still clear 1.2 m when extended to 10 (3.0 m) and 12 (3.6 m)? Re-run LS-DINE-CLEAR on a lengthened table."""
    from ..rules import evaluate
    t0 = L["tables"][0]
    out = {}
    for n, length in ((8, 2.4), (10, 3.0), (12, 3.6)):
        t = dict(t0)
        # the long side is the larger of size_m; extend it symmetrically
        w, h = t0["size_m"]
        size = [length, h] if w >= h else [w, length]
        t["size_m"] = size
        L2 = dict(L, tables=[t])
        r = [x for x in evaluate(L2, C.RS) if x.criterion == "LS-DINE-CLEAR"][0]
        out[n] = {"length_m": length, "clear_mm": r.achieved, "required_mm": r.required, "status": r.status}
    return out


def free_floor(L):
    """Standing room at an event: paved + gravel floor minus table (+0.6 m chairs), seats (+0.45 m), fire pit (+0.9 m ring is NOT removed: people may stand on the lid), BBQ (+0.6), pot, plus benches' seat depth."""
    south = box(S.SX0, S.SY0, S.SX0 + A, S.SY0 + B)
    floor = unary_union([box(*a["rect"]) for a in L["paved_areas"]] + [box(*z["rect"]) for z in L["zones"] if z.get("surface") == "gravel"]).intersection(south)
    cut = []
    for t in L["tables"]:
        cx, cy = t["center"]
        w, h = t["size_m"]
        cut.append(box(cx - w / 2 - 0.6, cy - h / 2 - 0.6, cx + w / 2 + 0.6, cy + h / 2 + 0.6))
    for s in L["seating"]:
        if s["rect"][0] > 20:
            cut.append(box(*s["rect"]).buffer(0.45))
    for f in L["features"]:
        if f["kind"] == "bbq":
            cut.append(box(*f["rect"]).buffer(0.6))
    for o in L["obstacles"]:
        if o["id"].startswith("pot"):
            cut.append(box(*o["rect"]).buffer(0.3))
    free = floor.difference(unary_union(cut))
    return free.area


def seats(L):
    dz = {z["id"]: z["use"] for z in L["zones"]}
    d = sum(t["seats"] for t in L["tables"])
    lounge = sum(s["seats"] for s in L["seating"] if dz.get(s["zone"]) == "lounge")
    quiet_s = sum(s["seats"] for s in L["seating"] if dz.get(s["zone"]) == "quiet" and s["rect"][0] > 20)
    quiet_n = sum(s["seats"] for s in L["seating"] if dz.get(s["zone"]) == "quiet" and s["rect"][0] < 20)
    return {"dining": d, "built_in_and_lounge": lounge, "quiet_south": quiet_s, "quiet_yard_or_north": quiet_n}


def metrics(L):
    soft = sum((g["rect"][2] - g["rect"][0]) * (g["rect"][3] - g["rect"][1]) for g in L["planting_groups"] if g["rect"][0] > 22.5)
    area = A * B
    n_trees = sum(1 for t in L["trees"] if t["center"][0] > 22.5)
    free = free_floor(L)
    return {"south_area_m2": round(area, 2), "soft_m2": round(soft, 2), "hard_share": round(1 - soft / area, 3), "canopy_trees": n_trees,
            "trees_per_100m2_south": round(n_trees / area * 100, 2), "trees_per_100m2_south_plus_yard": round(n_trees / (area + 21.48) * 100, 2),
            "free_floor_m2": round(free, 1), "standing_at_1.3m2": int(free / 1.3), "seats": seats(L)}


def evaluate_all(L, rooms, covers):
    res = [r for r in C.ldk(L)]
    own = C.own_checks(L, rooms, covers, S.FLOOR_Z + C.SCREEN_H, None)
    sunres, sun_seen = sun_checks(L)
    return res + own + sunres + tree_checks(L), sun_seen


def schedule(L, sun_seen):
    rows = {}
    for g in L["planting_groups"]:
        zone = "south" if g["rect"][0] > 22.5 else "east yard" if g["rect"][0] > 14 else "north court"
        for p in g["plants"]:
            k = (zone, p["species"], g["id"])
            r = rows.setdefault(k, {"zone": zone, "bed": g["id"], "species": p["species"], "count": 0, "form": p["form"]})
            r["count"] += 1
    out = []
    for (zone, slug, bid), r in rows.items():
        sp = POOL[slug]
        res, june = sun_seen.get((bid, slug), ("n/a", 0))
        layer = "climber" if slug in ("jasminum_sambac", "petrea_volubilis", "bougainvillea_glabra") else "canopy/understorey" if sp.form == "small_tree" else "ground" if sp.form == "ground_cover" or (sp.h_max or 1) < 0.5 else "shrub/perennial"
        out.append({"zone": zone, "bed": bid, "species": sp.name, "slug": slug, "count": r["count"], "layer": layer, "verdict": sp.verdict,
                    "conditions": sp.conditions + ([f"sun {res} at {june:.1f} h (21 Jun)"] if res not in ("pass", "n/a") else []),
                    "water": sp.water, "toxic": sp.toxic, "mature_h_m": sp.h_max, "mature_spread_m": sp.s_max})
    for t in L["trees"]:
        sp = POOL[t["species"]]
        out.append({"zone": "south" if t["center"][0] > 22.5 else "other", "bed": "-", "species": sp.name, "slug": t["species"], "count": 1, "layer": "canopy/understorey (tree)", "verdict": sp.verdict,
                    "conditions": sp.conditions + [f"canopy checked at the sourced minimum spread {t['mature_spread_m']} m (LDL range {sp.s_min}-{sp.s_max} m): keep pruned"],
                    "water": sp.water, "toxic": sp.toxic, "mature_h_m": sp.h_max, "mature_spread_m": sp.s_max})
    out.append({"zone": "south", "bed": "pot", "species": POOL["plumeria_rubra"].name + " (terracotta pot)", "slug": "plumeria_rubra", "count": 1, "layer": "container tree", "verdict": POOL["plumeria_rubra"].verdict,
                "conditions": POOL["plumeria_rubra"].conditions + ["height and spread are a GAP in LDL: not evaluated"], "water": None, "toxic": POOL["plumeria_rubra"].toxic, "mature_h_m": None, "mature_spread_m": None})
    return sorted(out, key=lambda r: (r["zone"], r["layer"], r["slug"]))


def compact(res):
    return [{"criterion": r.criterion, "status": r.status, "subject": r.subject, "achieved": r.achieved, "required": r.required, "unit": r.unit, "message": r.message} for r in res]


FOCAL = {   # (concept, pond_where) -> (label, model point) for the LDS views check
    "A": {"east": ("pond in the east yard + the pomegranate", (19.0, -22.0)), "north": ("the pomegranate (south) and the fatsia mass (north)", (27.4, -28.0))},
    "B": {"east": ("pond, focal of the quiet east-yard room", (19.0, -22.0)), "north": ("pomegranate and east border; quiet north niche", (26.0, -21.5))},
    "C": {"east": ("fire pit on the axis, then the lit sculpture place", (25.1, -25.9)), "north": ("fire pit on the axis, then the lit sculpture place", (25.1, -25.9))},
}


def focal_views(concept, where):
    label, (x, y) = FOCAL[concept][where]
    v = S.point("views", "rooms_seeing_cell", x, y)
    return {"focal": label, "point": [x, y], "rooms_seeing_cell": v}


def critique_summary(L):
    from ..critic import critique, verdict
    fs = critique(L)
    by = {}
    for f in fs:
        d = by.setdefault(f.critic, {"pass": 0, "fail": 0, "warn": 0, "not_evaluated": 0})
        d[f.status] += 1
    return fs, by, verdict(fs)


def run(draw=True, massing=True):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "plans").mkdir(exist_ok=True)
    summary, full = {}, {}
    for c in "ABC":
        for w in ("east", "north"):
            L, rooms, covers = build(c, w)
            res, sun_seen = evaluate_all(L, rooms, covers)
            hf = hard_fails(res)
            fs, by, ver = critique_summary(L)
            m = metrics(L)
            ext = extension_checks(L)
            name = f"{c}-pond-{w}"
            rec = {"concept": c, "name": NAMES[c], "pond": w, "west_line": "screened (2.1 m)", "hard_fails": [r.criterion + ":" + r.subject for r in hf],
                   "tally": C.tally(res), "metrics": m, "precedent": {
                       "hard_share": {"achieved": m["hard_share"], "range": PREC["hard"], "inside": PREC["hard"][0] <= m["hard_share"] <= PREC["hard"][1]},
                       "trees_per_100m2_south": {"achieved": m["trees_per_100m2_south"], "range": PREC["trees"], "inside": PREC["trees"][0] <= m["trees_per_100m2_south"] <= PREC["trees"][1]}},
                   "table_extension": ext, "focal": focal_views(c, w), "critic_counts": by, "critic_verdict": ver,
                   "critic_findings": [f.to_dict() for f in fs if f.status in ("fail", "warn")], "checks": compact(res), "schedule": schedule(L, sun_seen)}
            full[name] = rec
            summary[name] = {k: rec[k] for k in ("tally", "hard_fails", "critic_counts", "critic_verdict")} | {"metrics": m}
            json.dump(L, open(OUT / f"layout-{name}.json", "w"))
            if draw:
                from ..critic import plan_png, massing_png
                plan_png(L, str(OUT / "plans" / f"{name}-south.png"), title=f"Concept {c} {NAMES[c]}: south garden and east yard (west line screened; pond {w})", view=[14.6, -30.8, 29.3, -19.8])
                plan_png(L, str(OUT / "plans" / f"{name}-north.png"), title=f"Concept {c} {NAMES[c]}: north court (pond {w})", view=[-0.9, -29.6, 4.6, -22.8])
                if massing:
                    massing_png(L, str(OUT / "plans" / f"{name}-massing.png"), view=[14.0, -31.5, 30.0, -19.5])
                    massing_png(L, str(OUT / "plans" / f"{name}-north-massing.png"), view=[-1.5, -30.5, 6.5, -22.5], azimuth=205, elevation=50)      # from the north: the house hides the court from the south
            print(name, rec["tally"], "HARD", rec["hard_fails"], m["hard_share"], m["trees_per_100m2_south"], m["standing_at_1.3m2"], m["seats"], {k: v for k, v in by.items()}, flush=True)
    json.dump(summary, open(OUT / "summary.json", "w"), indent=1)
    json.dump(full, open(OUT / "packages.json", "w"), indent=1, default=str)
    return full


if __name__ == "__main__":
    run()
