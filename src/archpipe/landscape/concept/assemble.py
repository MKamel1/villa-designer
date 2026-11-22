"""Steps 3-6: assemble site concepts (south x north x east), rank, select, and write knowledge/landscape/concept/."""
from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

from ..rules import load
from . import checks as K, courts_eval as CE, layout as LY, pipeline as PP, planting as PL, plan_draft, programme, site as S, south as SO, species, zoning

OUT = PP.OUT
ROLE_USE = {"screen": "U-PRIVACY", "south": "U-PRIVACY", "edge": "U-PRIVACY", "herb": "U-S-HERB", "orchard": "D-SHADE-OVER-SUN", "street": "U-PRIVACY",
            "pond-edge": "U-POND", "yard": "U-PRIVACY", "east-edge": "U-PRIVACY"}


def res_dicts(res):
    return [asdict(r) for r in res]


def tally(res):
    t = {"pass": 0, "fail": 0, "warn": 0, "not_evaluated": 0}
    for r in res:
        t[r.status] += 1
    return t


def site_features_check(Ls, Ln, Le, rs):
    from ..rules.checks import evaluate
    merged = {"schema": "landscape-layout/1", "features": Ls["features"] + Ln["features"] + Le["features"]}
    return [r for r in evaluate(merged, rs) if r.criterion == "LS-BRIEF-FEATURES"]


def covers_model(c):
    return [LY.M(r) for r in c["cover"]]


def package(idea, sv, sopen, nopt, eopt, pond_where, pool, rs):
    """One site concept: the south garden (a variant), the north court, the east yard."""
    S_ = sv
    Ls, Ln, Le = S_["layout"], nopt["layout"], eopt["layout"]
    res = list(S_["results"]) + list(nopt["results"]) + list(eopt["results"]) + site_features_check(Ls, Ln, Le, rs)
    total = 0.6 * S_["score"] + 0.2 * nopt["score"] + 0.2 * eopt["score"]
    return {"idea": idea, "south": S_, "north": nopt, "east": eopt, "pond": pond_where, "score": round(total, 4), "results": res}


def element_trace(pk):
    rows = {}
    known = set(programme.build()["uses"]) | set(load().rules) | {r for r in load().advisory_ids}
    bad = []
    for zone in ("south", "north", "east"):
        L = pk[zone]["layout"]
        for key in ("zones", "paths", "paved_areas", "tables", "seating", "planting_groups", "trees", "features", "boundary", "obstacles", "seatwalls"):
            for it in L.get(key, []):
                tr = it.get("trace", [])
                rows[f"{zone}/{key}/{it['id']}"] = tr
                if not tr or any(t not in known for t in tr):
                    bad.append((zone, key, it["id"], tr))
        roles = {b["id"]: b["role"] for b in pk[zone]["cand"]["beds"]}
        for bid, p in pk[zone]["plan"]["beds"].items():
            for inst in p["instances"]:
                rows[f"{zone}/plant/{bid}/{inst['species']}"] = [ROLE_USE.get(roles.get(bid), "U-PRIVACY"), "D-COLOUR-DRIFTS"]
    return rows, bad


def schedule_of(zone_item, pool):
    inst = [i for p in zone_item["plan"]["beds"].values() for i in p["instances"]]
    rows = PL.schedule(inst, pool)
    for t in zone_item["plan"].get("trees", []):
        sp = pool[t["species"]]
        rows.append({"species": sp.name, "slug": sp.slug, "count": 1, "layer": "canopy", "verdict": sp.verdict, "conditions": sp.conditions,
                     "water": sp.water, "toxic": sp.toxic, "drawable": sp.drawable, "mature_h_m": sp.h_max, "mature_spread_m": sp.s_max})
    for pt in zone_item["plan"].get("pots", []):
        sp = pool[pt["species"]]
        rows.append({"species": sp.name + " (terracotta pot)", "slug": sp.slug, "count": 1, "layer": "container tree", "verdict": sp.verdict,
                     "conditions": sp.conditions + ["height and spread are a GAP in LDL: not evaluated; winter protection or shelter needed (frost conditional)"],
                     "water": sp.water, "toxic": sp.toxic, "drawable": sp.drawable, "mature_h_m": sp.h_max, "mature_spread_m": sp.s_max})
    return rows


def draw_package(pk, name, title, pond_label=""):
    layouts = {z: pk[z]["layout"] for z in ("south", "north", "east")}
    layouts["_cover"] = covers_model(pk["south"]["cand"])
    if pk["north"]["cand"].get("quiet"):
        layouts["_cover"].append(pk["north"]["cand"]["quiet"])
    plans = {z: pk[z]["plan"] for z in ("south", "north", "east")}
    path = OUT / "plans" / f"{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    notes = [f"score {pk['score']:.3f}", f"south seats (dining+lounge) {pk['south']['parts']['seats_dl']} + quiet 2", f"south hard share {pk['south']['parts']['hard_share']}",
             f"west line: {pk['south']['cand']['variant']}", f"pond in: {pk['pond']}"]
    plan_draft.draw(layouts, plans, title, path, pond_label, notes)
    return str(path.relative_to(S.ROOT))


def main(n_south=240000, seed=7, chunks=60, procs=30):
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    rs = load()
    pool = species.pool()
    programme.write(OUT / "programme.json")
    json.dump(zoning.build(), open(OUT / "zoning.json", "w"), indent=1)
    print("programme + zoning written", round(time.time() - t0), flush=True)
    best_s, counts_s = PP.run_south(n_south, seed, 25, 8, chunks=chunks, procs=procs)
    print("south done", round(time.time() - t0), flush=True)
    courts, counts_c = {}, {}
    for zone in ("north", "east"):
        for pond in (False, True):
            out, st = CE.run_zone(zone, pond, 20000, seed, 10, 8, pool, rs)
            courts[(zone, pond)] = out
            counts_c[f"{zone}/{'pond' if pond else 'no-pond'}"] = st
    print("courts done", round(time.time() - t0), flush=True)
    json.dump({"south": counts_s, "courts": counts_c, "sampler": "random sequential packing at rule distances; see docs/lanes/LDG.md"}, open(OUT / "candidate-counts.json", "w"), indent=1)
    concepts = {}
    for idea in SO.IDEAS:
        sv = best_s.get((idea, "screened")) or []
        so = best_s.get((idea, "open")) or []
        variants = {"screened": sv[0] if sv else None, "open": so[0] if so else None}
        concepts[idea] = {"variants": variants}
    # pond-location options (north court / east yard)
    for idea, cd in concepts.items():
        cd["packages"] = {}
        for vname, S_ in cd["variants"].items():
            if S_ is None:
                continue
            for where in ("north", "east"):
                n_ = courts[("north", where == "north")]
                e_ = courts[("east", where == "east")]
                if not n_ or not e_:
                    continue
                cd["packages"][(vname, where)] = package(idea, S_, None, n_[0], e_[0], where, pool, rs)
    return concepts, best_s, courts, counts_s, counts_c, pool, rs


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 48000
    concepts, best_s, courts, cs, cc, pool, rs = main(n, 7, 24, 30)
    for idea, cd in concepts.items():
        for k, pk in cd["packages"].items():
            print(idea, k, pk["score"], tally(pk["results"]))
