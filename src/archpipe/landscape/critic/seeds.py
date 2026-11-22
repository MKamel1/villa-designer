"""The reference scheme ("base") and the seeded defects made from it.

`base()` is OUR hand-built reference layout for the south garden, yard strip and north court of the villa site.
It is not a professional design and not LDG's output; it only has to be clean on the criteria a defect targets,
so that a seeded defect can be scored differentially (clean before, flagged after). Each defect is built from
named quantities (a moved fire pit, a wall height, a species swap) and lists the criteria it must trip
(`expect`), pre-registered in knowledge/landscape/critic/PREREG.md before any scoring.
"""
from __future__ import annotations

import copy
import json

from . import site as S
from .common import KNOW

OUT = KNOW / "critic/seeded"


def _chair(i, x, y, zone):
    return {"id": f"chair-{i}", "zone": zone, "rect": [round(x - .3, 2), round(y - .3, 2), round(x + .3, 2), round(y + .3, 2)], "seats": 1}


def _plants(*items):
    return [{"species": sp, "count": n, "form": form} for sp, n, form in items]


def base() -> dict:
    inv = json.loads((KNOW / "site/inventory.json").read_text())
    walls = [{"id": e["id"], "rect": e["rect_m"], "height_m": e["z_m"][1] - e["z_m"][0]} for e in inv["structure"] if e["id"].startswith(("fence-", "yard-wall"))]
    lay = {
        "schema": "landscape-layout/1", "id": "base", "source": "LDC reference scheme (hand-built; not a professional design)",
        "frame": "model metres; street side = north = -x; south garden = +x",
        "buildings": [[3.617, -28.671, 22.597, -23.591], [19.604, -31.311, 22.324, -28.671]],
        "walls": walls,
        "doors": [{"id": o["id"], "at": list(o["at"]), "faces": o["faces"], "room": o["room"], "width_m": o["width_m"]} for o in S.doors()],
        "zones": [
            {"id": "lounge", "use": "lounge", "rect": [22.7, -29.4, 26.4, -25.0], "surface": "gravel"},
            {"id": "dining", "use": "dining", "rect": [22.7, -25.0, 26.4, -20.9], "surface": "paving"},
            {"id": "quiet-south", "use": "quiet", "rect": [26.4, -24.8, 28.1, -21.9], "surface": "gravel"},
            {"id": "yard-standing", "use": "standing", "rect": [18.6, -23.4, 22.7, -20.9], "surface": "paving", "label": "standing / BBQ"},
            {"id": "yard-west", "use": "other", "rect": [15.5, -23.4, 18.6, -20.9], "surface": "paving", "label": "pond court"},
            {"id": "north-court", "use": "quiet", "rect": [-0.1, -28.0, 3.6, -24.4], "surface": "paving"},
        ],
        "paths": [
            {"id": "main-yard-dining", "class": "main", "width_m": 1.2, "polyline": [[20.557, -23.2], [20.557, -22.3], [22.7, -22.3]]},
            {"id": "north-approach", "class": "secondary", "width_m": 0.9, "polyline": [[3.0, -26.156], [2.4, -26.156]]},
            {"id": "service-edge", "class": "service", "width_m": 0.9, "polyline": [[22.7, -21.3], [18.6, -21.3]]},
        ],
        "tables": [{"id": "dining-table", "zone": "dining", "center": [24.55, -23.0], "diameter_m": 1.4, "seats": 4}],
        "seating": [
            _chair(1, 23.4, -27.5, "lounge"), _chair(2, 24.55, -27.0, "lounge"), _chair(3, 25.7, -27.5, "lounge"),
            _chair(4, 23.0, -26.0, "lounge"), _chair(5, 24.55, -25.6, "lounge"), _chair(6, 26.1, -26.0, "lounge"),
            {"id": "bench-quiet", "zone": "quiet-south", "rect": [27.2, -23.8, 27.8, -22.4], "seats": 2},
            {"id": "bench-pond", "zone": "yard-standing", "rect": [18.8, -22.5, 19.4, -21.3], "seats": 2},
            {"id": "bench-north", "zone": "north-court", "rect": [0.7, -27.0, 1.3, -25.6], "seats": 2},
        ],
        "canopies": [{"id": "pergola-dining", "kind": "pergola", "canopy": True, "rect": [22.9, -24.8, 26.2, -21.1], "height_m": 2.5, "shade_fraction": 0.6}],
        "screens": [
            {"id": "hedge-west", "kind": "hedge", "rect": [22.6, -29.9, 28.3, -29.5], "height_m": 2.4, "opacity": 0.9},
            {"id": "trellis-quiet", "kind": "trellis", "rect": [26.4, -24.9, 26.6, -23.3], "height_m": 1.8, "opacity": 0.8},
        ],
        "features": [
            {"id": "fire", "kind": "firepit", "center": [24.55, -28.7], "diameter_m": 0.9, "flush": True, "cover": {"load_rating_kN": 15}, "product_clearance_mm": 600},
            {"id": "bbq", "kind": "bbq", "center": [21.6, -21.6], "diameter_m": 0.6},
            {"id": "pond", "kind": "pond", "center": [16.8, -21.6], "diameter_m": 1.2, "flush": True, "edge": "soft", "freeboard_mm": 150, "depth_mm": 900, "volume_m3": 1.0, "margin_slope_back_mm": 600},
            {"id": "herbs", "kind": "herb_bed", "rect": [26.6, -21.7, 28.2, -20.7]},
        ],
        "planting_groups": [
            {"id": "bed-rear", "rect": [26.6, -29.4, 28.2, -25.0], "over_structure": False, "plants": _plants(("Pittosporum tobira", 4, "shrub"), ("Ophiopogon japonicus", 6, "ground_cover"), ("Justicia brandegeeana", 4, "shrub"))},
            {"id": "bed-pond", "rect": [15.6, -22.4, 18.0, -20.8], "over_structure": False, "plants": _plants(("Acorus gramineus", 4, "ground_cover"), ("Farfugium japonicum", 4, "ground_cover"), ("Alpinia zerumbet", 3, "shrub"))},
            {"id": "bed-north", "rect": [-0.1, -28.5, 0.4, -23.9], "over_structure": False, "plants": _plants(("Fatsia japonica", 3, "shrub"), ("Aspidistra elatior", 3, "ground_cover"), ("Rhapis excelsa", 2, "shrub"))},
            {"id": "bed-north-2", "rect": [0.4, -24.4, 3.0, -23.95], "over_structure": False, "plants": _plants(("Farfugium japonicum", 3, "ground_cover"), ("Acorus gramineus", 3, "ground_cover"))},
        ],
        "trees": [{"id": "lemon", "species": "Citrus limon", "center": [27.0, -27.3], "mature_spread_m": 3.8, "form": "small_tree", "over_structure": False, "mature_height_m": 4.5, "water_demand": "moderate"}],
        "boundary": [{"id": "fence-street", "side": "street", "kind": "wall", "height_m": 4.0}, {"id": "fence-east", "side": "neighbour", "kind": "wall", "height_m": 4.0},
                     {"id": "fence-rear", "side": "neighbour", "kind": "wall", "height_m": 4.0}, {"id": "fence-west", "side": "neighbour", "kind": "wall", "height_m": 4.0}],
        "steps": [], "paved_areas": [], "obstacles": [],
    }
    lay["planting_groups"] = [g for g in lay["planting_groups"] if g["plants"]]
    return lay


def save_base():
    (KNOW / "critic/base-good.json").write_text(json.dumps(base(), indent=1) + "\n")
