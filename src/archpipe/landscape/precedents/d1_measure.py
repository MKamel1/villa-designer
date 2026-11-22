"""Measure the CURRENT D1 garden on the precedent metrics. Read-only: imports concept.villa_landscape and calls
review_candidate; nothing is written to the scene. Run: PYTHONPATH=src python -m archpipe.landscape.precedents.d1_measure

Definitions (same as docs/lanes/LDP.md): hard = paving, stepping stones and gravel (a gravel/stone surface is not
planted); soft = everything else inside the garden rectangle (lawn, beds, tree pit). Artificial turf is counted soft
and flagged. Layer shares count plan symbols (individual plants): canopy = tree; shrub = back/mid/dome/accent;
ground = front/underplanting/edge. Trees per 100 m2 counts tree symbols. Drift = clump size recorded by the plan (3)."""
import json
from collections import Counter
from datetime import date
from pathlib import Path
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from . import DATA

HARD_MATERIALS = {"stepping-stone", "garden-gravel"}
LAYER_OF = {"tree": "canopy", "back": "shrub", "mid": "shrub", "dome": "shrub", "accent": "shrub",
            "front": "ground", "underplanting": "ground", "edge": "ground"}


def _foot(m):
    polys = []
    for f in m["faces"]:
        pts = [(v[0], v[1]) for v in f]
        if len(pts) >= 3:
            p = Polygon(pts)
            if p.is_valid and p.area > 0:
                polys.append(p)
    return unary_union(polys) if polys else None


def measure(region, meshes, plan, *, rooms, path_primary, notes):
    area = region.area
    hard = unary_union([f for m in meshes if m["id"].startswith("landscape-") and m["material"] in HARD_MATERIALS
                        and (f := _foot(m)) is not None]).intersection(region).area
    plants = [p for p in plan["plants"] if region.contains(Point(p["center"]))]
    lay = Counter(LAYER_OF[p["planting_layer"]] for p in plants)
    n = sum(lay.values())
    trees = lay["canopy"]
    species = {p["species"] for p in plants}
    return {
        "area_m2": round(area, 2), "hard_share": round(hard / area, 3), "soft_share": round(1 - hard / area, 3),
        "water_share": 0.0, "n_rooms": rooms, "path_primary_m": path_primary,
        "trees_per_100m2": round(trees / area * 100, 2), "drift_size_median": 3,
        "layer_canopy": round(lay["canopy"] / n, 3), "layer_shrub": round(lay["shrub"] / n, 3),
        "layer_ground": round(lay["ground"] / n, 3),
        "species_per_100m2": round(len(species) / area * 100, 2), "n_species": len(species),
        "enclosure_ratio": None, "room_area_mean_m2": None, "path_secondary_m": None,
        "notes": notes,
    }


def run():
    import sys
    from archpipe.concept import villa_landscape as L, villa_r11 as R, revit_spec as RS
    lay = R.design("D1")
    meshes, _, _, plan = L.review_candidate(RS.build(lay), lay)
    out = {
        "date": str(date.today()), "source": "concept/villa_landscape.review_candidate(revit_spec.build(D1)), read-only",
        "gardens": {
            "south": measure(box(*L.SOUTH), meshes, plan, rooms=2, path_primary=0.914,
                             notes="rooms: g6 terrace (12.36 m2, pergola) and the lawn; the lawn is artificial turf; "
                                   "no water feature; boundary heights and room widths not measured (GAP)"),
            "north": measure(box(*L.NORTH_COURT), meshes, plan, rooms=1, path_primary=0.914,
                             notes="gravel court counted hard; one swing/lounge room; no water feature (a pond is new in the brief)"),
        },
    }
    (DATA / "d1.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


if __name__ == "__main__":
    print(json.dumps(run(), indent=1))
