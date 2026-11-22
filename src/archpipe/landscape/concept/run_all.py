"""Full LD-G run: python -m archpipe.landscape.concept.run_all [n_south_samples]. Writes knowledge/landscape/concept/*."""
from __future__ import annotations

import json
import sys
from dataclasses import asdict

from ..rules import load
from . import assemble as A, planting as PL, programme, site as S, south as SO, species
from .pipeline import OUT, PREC


def compact(res):
    return [{"criterion": r.criterion, "status": r.status, "subject": r.subject, "achieved": r.achieved, "required": r.required, "unit": r.unit,
             "message": r.message, "source_ids": list(r.source_ids)} for r in res]


def programme_table(pk):
    """Achieved versus required for the uses, from the check records (no adjectives)."""
    want = {"U-S-DINE": ("LS-DINE-AREA", "LS-DINE-CLEAR"), "U-S-LOUNGE": ("LS-LOUNGE-AREA", "LS-LOUNGE-CLUSTER", "LS-CAPACITY"), "U-S-STAND": ("LS-STAND-AREA",),
            "U-S-FIRE": ("LS-FIRE-CLEAR", "LS-FIRE-SEAT", "LS-FIRE-STRUCT", "LS-FIRE-OVERHEAD", "LS-FIRE-COVER", "LS-FLUSH-LIP", "LS-FLUSH-OPENING", "LS-FIRE-PRODUCT"),
            "U-S-BBQ": ("LS-FIRE-CLEAR",), "U-S-HERB": ("LS-HERB-SUN",), "U-ACCESS": ("LS-PATH-MAIN",),
            "U-POND": ("LS-POND-DEPTH", "LS-POND-STOCK", "LS-POND-GUARD", "LS-POND-FREEBOARD", "LS-POND-FLUSH-MARGIN", "LS-POND-EDGE-SLOPE", "LS-POND-SHADE", "LS-POND-EDGE-LIGHT"),
            "U-PRIVACY": ("LDG-PRIV", "LS-SCREEN"), "D-SHADE-OVER-SUN": ("LDG-SHADE", "LS-TREE-BUILDING", "LS-ROOTZONE")}
    rows = []
    for use, crits in want.items():
        for r in pk["results"]:
            if r.criterion in crits:
                rows.append({"use": use, "criterion": r.criterion, "subject": r.subject, "status": r.status, "achieved": r.achieved, "required": r.required,
                             "unit": r.unit, "message": r.message})
    return rows


def describe(pk, pool):
    S_, N_, E_ = pk["south"], pk["north"], pk["east"]
    sc = S_["cand"]
    return {
        "idea": pk["idea"], "idea_name": SO.IDEAS[pk["idea"]], "west_line": sc["variant"], "pond": pk["pond"], "score": pk["score"],
        "scores": {"south": S_["score"], "north": N_["score"], "east": E_["score"]},
        "south_parts": S_["parts"], "north_parts": N_["parts"], "east_parts": E_["parts"],
        "tally": A.tally(pk["results"]),
        "precedent_position": {
            "south_hard_share": {"achieved": S_["parts"]["hard_share"], "range": PREC["hard"], "position": "inside" if PREC["hard"][0] <= S_["parts"]["hard_share"] <= PREC["hard"][1] else ("above" if S_["parts"]["hard_share"] > PREC["hard"][1] else "below")},
            "south_trees_per_100m2": {"achieved": S_["parts"]["trees_per_100m2"], "range": PREC["trees"], "position": "inside" if PREC["trees"][0] <= S_["parts"]["trees_per_100m2"] <= PREC["trees"][1] else "below" if S_["parts"]["trees_per_100m2"] < PREC["trees"][0] else "above"}},
        "south_seats": {"dining": sc["table"]["seats"], "lounge": sum(s["seats"] for s in sc["seats"]), "quiet": 2, "event_standing_capacity": S_["parts"]["event_standing"]},
        "south_params": sc["params"], "cover_rooms": sc["cover_rooms"],
        "programme_table": programme_table(pk),
        "schedules": {"south": A.schedule_of(S_, pool), "north": A.schedule_of(N_, pool), "east": A.schedule_of(E_, pool)},
        "pond": {"where": pk["pond"], **(N_["cand"]["pond"] if pk["pond"] == "north" else E_["cand"]["pond"])},
        "checks": compact(pk["results"]),
    }


def main(n=240000):
    concepts, best_s, courts, cs, cc, pool, rs, _, _ = A.main(n, 7, 60, 30, 40, 12, 40000)
    (OUT / "plans").mkdir(parents=True, exist_ok=True)
    summary = {}
    trace_all = {}
    for idea, cd in concepts.items():
        out = {"idea": idea, "name": SO.IDEAS[idea], "packages": {}}
        for (vname, where), pk in cd["packages"].items():
            d = describe(pk, pool)
            png = A.draw_package(pk, f"{idea}-{vname}-pond-{where}", f"Concept {idea}: {SO.IDEAS[idea]} | west line {vname} | pond in the {where} {'court' if where == 'north' else 'yard'} | score {pk['score']:.3f}",
                                 f"pond: {where}")
            d["plan_png"] = png
            rows, bad = A.element_trace(pk)
            d["traceability"] = {"elements": len(rows), "untraced": [list(b) for b in bad]}
            trace_all[f"{idea}-{vname}-{where}"] = {"elements": rows, "untraced": [list(b) for b in bad]}
            out["packages"][f"{vname}/{where}"] = d
        json.dump(out, open(OUT / f"concept-{idea}.json", "w"), indent=1, default=str)
        summary[idea] = {k: {"score": v["score"], "tally": v["tally"], "plan": v["plan_png"]} for k, v in out["packages"].items()}
    json.dump(trace_all, open(OUT / "traceability.json", "w"), indent=1)
    json.dump({"south": cs, "courts": cc, "n_samples_per_south_cell": n}, open(OUT / "candidate-counts.json", "w"), indent=1)
    json.dump(summary, open(OUT / "summary.json", "w"), indent=1)
    # held-back species (not scheduled)
    json.dump({"allowed": {k: {"verdict": v.verdict, "conditions": v.conditions, "drawable": v.drawable} for k, v in pool.items()},
               "held_back_heat_gap_or_not_viable": species.held_back()}, open(OUT / "species-pool.json", "w"), indent=1)
    json.dump({k: {"statement": v[0], "basis": v[1], "status": "policy"} for k, v in __import__("archpipe.landscape.concept.checks", fromlist=["POLICY"]).POLICY.items()},
              open(OUT / "policy-cards.json", "w"), indent=1)
    return summary


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 240000
    print(json.dumps(main(n), indent=1))
