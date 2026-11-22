"""LD-G pipeline: programme -> zoning -> structure candidates -> planting -> checks -> rank -> concepts.

Every stage writes its output to knowledge/landscape/concept/. Run: PYTHONPATH=src python -m archpipe.landscape.concept.pipeline
"""
from __future__ import annotations

import json
import random
import time
from collections import Counter
from pathlib import Path

from shapely.affinity import translate
from shapely.geometry import box
from shapely.ops import unary_union

from ..rules import evaluate, load
from . import checks as K
from . import courts, layout as LY, planting as PL, site as S, south as SO, species
from .geom import circle, rbox

OUT = S.ROOT / "knowledge" / "landscape" / "concept"
SKIP = {"LS-BRIEF-FEATURES"}          # pond lives in another zone: judged at site level
W = {"cap": .22, "wsun": .12, "priv": .22, "hard": .10, "tree": .06, "quiet": .08, "herb": .05, "view": .05, "pit": .05, "soft": .05}
PREC = {"hard": (0.52, 0.82), "trees": (1.56, 3.26)}       # targets-2.json, south_combined


def _fit(v, lo, hi, tol):
    return 1.0 if lo <= v <= hi else max(0.0, 1 - (lo - v if v < lo else v - hi) / tol)


def to_model_shape(g):
    return translate(g, S.SX0, S.SY0)


def plan_south(c, rng, pool):
    plan = {"beds": {}, "trees": [], "pots": c.get("pots", [])}
    seats = [rbox(s["rect"]) for s in c["seats"]] + [rbox(c["quiet"]["bench"])]
    for b in c["beds"]:
        rm = LY.M(b["rect"])
        june = S.mean("sun", "sun_hours_summer_solstice", rm) or 0.0
        near = any(rbox(b["rect"]).distance(s) < 2.0 for s in seats) or b["role"] == "herb"
        plan["beds"][b["id"]] = PL.plant_bed(b, rm, june, near, rng, pool)
        plan["beds"][b["id"]]["june"] = round(june, 2)
        plan["beds"][b["id"]]["rect_local"] = b["rect"]
    for t in c["trees"]:
        bed = next((b["id"] for b in c["beds"] if rbox(b["rect"]).contains(Point_(t["center"]))), None)
        plan["trees"].append({**t, "bed": bed})
    return plan


def Point_(xy):
    from shapely.geometry import Point
    return Point(*xy)


def evaluate_south(c, plan, pool, rs):
    L = LY.to_layout(c, plan, pool)
    res = [r for r in evaluate(L, rs) if r.criterion not in SKIP]
    res += K.south_checks(c, plan, pool) if plan is None else K.south_checks(c, plan, pool)
    return L, res


def south_reserved(c):
    """Reserved geometry in the MODEL frame: seats, door path, fire-pit clearance (0.9 m)."""
    g = [rbox(s["rect"]) for s in c["seats"]] + [rbox(c["quiet"]["bench"]), rbox(c["path"]), circle(c["pit"]["center"], SO.PIT_D + 1.8)]
    return [to_model_shape(x) for x in g]


def south_score(c, L, res, plan, pool):
    P = {}
    seats_dl = c["table"]["seats"] + sum(s["seats"] for s in c["seats"])
    zs = [z for z in L["zones"] if z["use"] == "standing"]
    stand = zs[0].get("design_people", 0) if zs else 0
    event = SO.event_capacity(c, 1.3)
    P["cap"] = min(1.0, 0.5 * seats_dl / 14 + 0.5 * min(event / 20, 1.0))
    rm = [LY.M(c["dining"]), LY.M(c["lounge"])]
    ws = [S.mean("sun", "winter_day_10_15", r) or 0 for r in rm]
    P["wsun"] = min(1.0, (sum(ws) / 2) / 3.5)
    rem = [r.achieved for r in res if r.criterion == "LDG-PRIV"]
    P["priv"] = 1 - (sum(rem) / len(rem) if rem else 1)
    soft = sum((b["rect"][2] - b["rect"][0]) * (b["rect"][3] - b["rect"][1]) for b in c["beds"])
    total = SO.A * SO.B
    hard = 1 - soft / total
    P["hard"] = _fit(hard, *PREC["hard"], 0.3)
    ntree = len(plan["trees"]) if plan else len(c["trees"])
    tp = ntree / total * 100
    P["tree"] = _fit(tp, *PREC["trees"], 1.5)
    qp = c["pit"]["center"]
    qc = ((c["quiet"]["rect"][0] + c["quiet"]["rect"][2]) / 2, (c["quiet"]["rect"][1] + c["quiet"]["rect"][3]) / 2)
    P["quiet"] = min(1.0, ((qp[0] - qc[0]) ** 2 + (qp[1] - qc[1]) ** 2) ** .5 / 4)
    hb = [b for b in c["beds"] if b["role"] == "herb"]
    P["herb"] = min(1.0, (S.mean("sun", "sun_hours_summer_solstice", LY.M(hb[0]["rect"])) or 0) / 7) if hb else 0.0
    P["view"] = min(1.0, (S.mean("views", "rooms_seeing_cell", LY.M(c["beds"][-1]["rect"])) or 0) / 2) if True else 0
    # fire pit lee: farther from the east fence = more shelter from the 75 % east wind (station-level; no site wind data)
    P["pit"] = min(1.0, (SO.B - qp[1]) / 4)
    P["soft"] = min(1.0, soft / total / 0.3)
    warns = sum(1 for r in res if r.status == "warn")
    score = sum(W[k] * P[k] for k in W) - 0.01 * warns
    return round(score, 4), {k: round(v, 3) for k, v in P.items()} | {"warns": warns, "hard_share": round(hard, 3), "trees_per_100m2": round(tp, 2),
                                                                      "seats_dl": seats_dl, "event_standing": round(event, 1), "stand_zone_people": stand}


def run_south(n_samples: int, seed: int, top_k: int, n_plant: int):
    rs = load()
    pool = species.pool()
    counts = {}
    best = {}
    t0 = time.time()
    for variant in ("screened", "open"):
        for idea in SO.IDEAS:
            rng = random.Random(f"{seed}-{idea}-{variant}")
            valid, nofail, rejects = [], [], Counter()
            for _ in range(n_samples):
                c = SO.sample(idea, variant, rng, rs.params)
                if c is None:
                    rejects["packing failed"] += 1
                    continue
                L, res = evaluate_south(c, None, pool, rs)
                hf = K.hard_fails(res)
                hf = [r for r in hf if r.criterion not in ("LDG-SPREAD", "LDG-TOXIC", "LDG-HYDRO")]
                valid.append(1)
                if hf:
                    for r in {r.criterion for r in hf}:
                        rejects[r] += 1
                    continue
                sc, P = south_score(c, L, res, None, pool)
                nofail.append((sc, c, P))
            nofail.sort(key=lambda t: -t[0])
            # planting stage on the top structures
            planted = []
            for sc, c, P in nofail[:top_k]:
                for k in range(n_plant):
                    plan = plan_south(c, random.Random(f"{seed}-plant-{id(c)}-{k}"), pool)
                    L, res = evaluate_south(c, plan, pool, rs)
                    res += K.planting_checks("south", c, plan, pool, reserved=south_reserved(c),
                                             seats=[to_model_shape(rbox(s["rect"])) for s in c["seats"]] + [to_model_shape(rbox(c["quiet"]["bench"]))],
                                             herb_rects=[to_model_shape(rbox(b["rect"])) for b in c["beds"] if b["role"] == "herb"])
                    hf = K.hard_fails(res)
                    if hf:
                        continue
                    sc2, P2 = south_score(c, L, res, plan, pool)
                    planted.append({"score": sc2, "parts": P2, "cand": c, "plan": plan, "layout": L, "n_warn": P2["warns"]})
            planted.sort(key=lambda d: -d["score"])
            counts[f"{idea}/{variant}"] = {"sampled": n_samples, "packed": len(valid), "no_hard_fail_structures": len(nofail),
                                           "planted_variants_tried": min(top_k, len(nofail)) * n_plant, "survivors": len(planted),
                                           "rejects": dict(rejects.most_common(8))}
            best[(idea, variant)] = planted
            print(idea, variant, counts[f"{idea}/{variant}"], round(time.time() - t0), "s", flush=True)
    return best, counts


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    best, counts = run_south(n, 1, 6, 4)
    for k, v in best.items():
        if v:
            print(k, v[0]["score"], v[0]["parts"])
