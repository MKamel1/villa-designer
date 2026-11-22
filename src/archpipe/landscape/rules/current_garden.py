"""The CURRENT D1 garden (concept/villa_landscape.py, read-only) as a landscape-layout/1 dict.

Run `python -m archpipe.landscape.rules.current_garden` to print the rule results; `--write` refreshes
knowledge/landscape/rules/current-garden-layout.json (the snapshot the tests use, so they need no build).
Every value is read from the garden code or palette; the few interpretive choices are listed in ASSUMPTIONS
and in docs/lanes/LDK.md. Missing data stays missing, so the rules report not_evaluated rather than pass.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parents[4] / "knowledge/landscape/rules/current-garden-layout.json"
ASSUMPTIONS = (
    "paths: every door-link route is class 'secondary' (the garden has no main path); width = the short side of its rectangle",
    "seats: a bench counts floor(length / 0.5 m) seats (TS 520-24: 500 mm bench space per person); each chair one seat",
    "plant form: mature height <= 0.5 m -> ground_cover, otherwise shrub; no height -> unknown (not evaluated)",
    "trees: mature spread = upper bound of the verified palette range (Plumeria 7.6 m)",
    "boundary: fence-street = street side; fence-east, fence-west, fence-rear = neighbour side; height = z1 - z0 of the Revit element",
    "water_need, slopes, soil depth under trees, steps: not present in the garden data, so left absent",
)


def build() -> dict:
    from ...concept import revit_spec as RS, villa_landscape as VL, villa_r11 as R
    from ... import villa_env as E
    lay = R.design("D1")
    _, _, _, plan = VL.review_candidate(RS.build(lay), lay)
    pal = {s["species"]: s for s in json.loads(VL.PALETTE.read_text())["species"]}

    def form(species):
        hr = (pal.get(species, {}).get("height") or {}).get("range_m")
        return None if not hr else ("ground_cover" if hr[1] <= 0.5 else "shrub")

    zones = [
        {"id": "south-garden", "use": "lounge", "rect": list(VL.SOUTH), "surface": "artificial-turf",
         "enclosure_height_m": 4.0},
        {"id": "north-court", "use": "quiet", "rect": list(VL.NORTH_COURT), "surface": "planting",
         "enclosure_height_m": 4.0},
        {"id": "east-yard", "use": "other", "rect": [15.412, -23.591, VL.SOUTH[0], -20.351], "surface": "artificial-turf"},
        {"id": "top-deck", "use": "other", "rect": list(VL.TOP), "surface": "paving"},
    ]
    paths = []
    for pid, (x0, y0, x1, y1) in plan["paths"].items():
        paths.append({"id": pid, "class": "secondary", "width_m": round(min(x1 - x0, y1 - y0), 3)})
    seating = []
    for o in plan["objects"]:
        if o.get("part_kind") == "outdoor-seating":
            x0, y0, x1, y1 = o["rect"]
            n = max(1, int(max(x1 - x0, y1 - y0) / 0.5)) if "bench" in o["id"] else 1
            seating.append({"id": o["id"], "zone": "south-garden", "rect": list(o["rect"]), "seats": n})
    groups = []
    for bed, rect in plan["beds"].items():
        members = [p for p in plan["plants"] if p.get("bed") == bed]
        groups.append({"id": "bed-" + bed, "rect": list(rect), "over_structure": False,
                       "plants": [{"species": p["species"], "form": form(p["species"])} for p in members]})
    for t in plan["top_troughs"]:
        depth = round((t["soil_z_m"] - t["bottom_m"]) * 1000)
        groups.append({"id": t["id"], "rect": list(t["rect"]), "over_structure": True, "soil_depth_mm": depth,
                       "plants": [{"species": t["species"], "form": form(t["species"])}]})
    trees = []
    for tree in plan["trees"]:
        sp = tree[2]
        spread = pal[sp]["spread"]["range_m"][1]
        trees.append({"id": tree[1], "species": sp, "center": list(tree[3]), "mature_spread_m": spread,
                      "form": "large_tree", "over_structure": True})
    boundary = []
    side = {"fence-street": "street"}
    elements = {e["id"]: e for e in E.spec()["elements"]}
    for b in plan["boundary_obstacles"]:
        if b["id"].startswith("fence-"):
            e = elements[b["id"]]
            boundary.append({"id": b["id"], "side": side.get(b["id"], "neighbour"), "kind": "wall",
                             "height_m": (e["z1"] - e["z0"]) / 1000})
    buildings = [[v / 1000 for v in r] for r in (E.FRONT, E.BAR, E.BUMP)]
    return {"schema": "landscape-layout/1", "source": "src/archpipe/concept/villa_landscape.py review_candidate (read-only)",
            "frame": "model metres; street side = north = -x; south garden = +x", "assumptions": list(ASSUMPTIONS),
            "zones": zones, "paths": paths, "paved_areas": [], "steps": [], "tables": [], "seating": seating,
            "planting_groups": groups, "trees": trees, "features": [], "boundary": boundary,
            "buildings": buildings, "obstacles": []}


def load_snapshot() -> dict:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    from . import evaluate, summarize
    layout = build()
    if "--write" in argv:
        SNAPSHOT.write_text(json.dumps(layout, indent=1) + "\n", encoding="utf-8")
    for r in evaluate(layout):
        if r.status != "pass":
            print(f"{r.status:14} {r.criterion:18} {r.subject:40} {r.message}")
    print(json.dumps(summarize(evaluate(layout)), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
