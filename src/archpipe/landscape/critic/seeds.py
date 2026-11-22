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
            {"id": "yard-standing", "use": "standing", "rect": [18.6, -23.4, 22.7, -20.9], "surface": "paving", "label": "standing / BBQ", "design_people": 7},
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
            {"id": "bench-north", "zone": "north-court", "rect": [1.9, -27.0, 2.5, -25.6], "seats": 2},
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
            {"id": "bed-rear", "rect": [26.6, -29.4, 28.2, -25.0], "over_structure": False, "plants": _plants(("Pittosporum tobira", 3, "shrub"), ("Ophiopogon japonicus", 6, "ground_cover"), ("Justicia brandegeeana", 3, "shrub"))},
            {"id": "bed-pond", "rect": [15.6, -22.4, 18.0, -20.8], "over_structure": False, "plants": _plants(("Acorus gramineus", 4, "ground_cover"), ("Farfugium japonicum", 4, "ground_cover"), ("Alpinia zerumbet", 3, "shrub"))},
            {"id": "bed-north", "rect": [-0.1, -28.5, 1.1, -23.9], "over_structure": False, "plants": _plants(("Fatsia japonica", 2, "shrub"), ("Aspidistra elatior", 4, "ground_cover"), ("Farfugium japonicum", 3, "ground_cover"))},
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


# ------------------------------------------------------------------------------------------------ seeded defects
POOL = ["Agapanthus praecox", "Salvia leucantha", "Pentas lanceolata", "Gazania rigens", "Lavandula dentata", "Strelitzia reginae",
        "Hibiscus rosa-sinensis", "Pennisetum alopecuroides", "Muhlenbergia capillaris", "Liriope muscari", "Nandina domestica", "Aloe vera",
        "Rosmarinus officinalis", "Callistemon citrinus", "Murraya paniculata", "Phoenix roebelenii", "Lantana montevidensis", "Thymus vulgaris", "Origanum majorana", "Mentha spicata", "Plumbago auriculata"]


def _seat_chairs(lay, pts, zone):
    lay["seating"] = [s for s in lay["seating"] if not s["id"].startswith("chair-")] + [_chair(i + 1, x, y, zone) for i, (x, y) in enumerate(pts)]


def d_lone_specimens(l):
    """Every shrub and ground plant a different species, one each, in place of drifts (a collector's border)."""
    k = 0
    for g in l["planting_groups"]:
        new = []
        for p in g["plants"]:
            for _ in range(p["count"]):
                new.append({"species": POOL[k % len(POOL)], "count": 1, "form": p.get("form")}); k += 1
        g["plants"] = new


def d_no_enclosure(l):
    """The plot boundary 0.9 m high instead of 4.0 m, and no hedge or trellis (a low-fenced, open plot)."""
    for w in l["walls"]: w["height_m"] = 0.9
    l["screens"] = []
    for g in l["planting_groups"]: g["plants"] = [p for p in g["plants"] if p["species"] != "Pittosporum tobira"]


def d_path_to_nowhere(l):
    """A 1.2 m main path from the lounge to the south-west corner of the garden, ending at the bare hedge."""
    l["paths"].append({"id": "path-to-corner", "class": "main", "width_m": 1.2, "polyline": [[25.0, -27.0], [27.0, -29.0], [27.9, -29.4]]})
    l["planting_groups"] = [g for g in l["planting_groups"] if g["id"] != "bed-rear"]


def d_seat_in_summer_sun(l):
    """The lounge and quiet seats moved onto the strip along the east fence, which gets 6.0-6.5 h of sun on 21 Jun, and the tree and pergola removed."""
    _seat_chairs(l, [(23.6, -20.95), (24.4, -20.95), (25.2, -20.95), (26.0, -20.95), (23.6, -21.8), (24.8, -21.8)], "dining")
    l["tables"] = []
    l["seating"] += [{"id": "bench-sun", "zone": "dining", "rect": [26.6, -21.3, 27.8, -20.75], "seats": 2}]
    l["canopies"] = []; l["trees"] = []
    l["features"] = [f for f in l["features"] if f["kind"] != "herb_bed"]


def d_pond_deep_shade(l):
    """The pond moved to the north court (1.3 h of sun on 21 Jun) instead of the sunny yard."""
    for f in l["features"]:
        if f["kind"] == "pond": f["center"] = [1.0, -26.2]
    l["planting_groups"] = [g for g in l["planting_groups"] if g["id"] != "bed-pond"]


def d_pond_no_view(l):
    """A 1.8 m hedge screen between the yard seats and the pond, and the only pond seat removed."""
    l["screens"].append({"id": "hedge-pond", "kind": "hedge", "rect": [18.1, -22.6, 18.5, -20.9], "height_m": 1.8, "opacity": 0.9})
    l["seating"] = [s for s in l["seating"] if s["id"] != "bench-pond"]
    l["seating"] = [s for s in l["seating"] if s["id"] != "bench-north"]


def d_fire_upwind(l):
    """The fire pit moved to the east side of the lounge (the prevailing wind blows toward the west), with the chairs west of it: smoke at every seat."""
    for f in l["features"]:
        if f["kind"] == "firepit": f["center"] = [24.55, -25.2]
    _seat_chairs(l, [(23.4, -27.0), (24.55, -27.4), (25.7, -27.0), (23.0, -28.4), (24.55, -28.7), (26.1, -28.4)], "lounge")


def d_privacy_exposed(l):
    """The pergola, trellis, hedge and tree removed: the seats are open to the apartment above and the neighbours."""
    l["canopies"] = []; l["screens"] = []; l["trees"] = []
    l["planting_groups"] = [g for g in l["planting_groups"] if g["id"] != "bed-rear"]


def d_toxic_by_herbs(l):
    """Oleander (highly toxic) planted three deep in a strip right beside the herb bed and the quiet bench."""
    l["planting_groups"].append({"id": "bed-oleander", "rect": [26.4, -21.9, 26.7, -21.7], "over_structure": False, "plants": [{"species": "Nerium oleander", "count": 3, "form": "shrub"}]})
    for g in l["planting_groups"]:
        if g["id"] == "bed-oleander": g["rect"] = [25.9, -22.0, 26.6, -21.5]


def d_single_layer(l):
    """No tree and one layer only: everything is low ground cover."""
    l["trees"] = []
    for g in l["planting_groups"]:
        g["plants"] = [{"species": "Liriope muscari", "count": sum(p["count"] for p in g["plants"]), "form": "ground_cover"}]


def d_oversize_tree(l):
    """A jacaranda (7.6 m mature spread) in the 3.7 m wide lounge in place of the lemon."""
    l["trees"] = [{"id": "jacaranda", "species": "Jacaranda mimosifolia", "center": [24.55, -26.2], "mature_spread_m": 7.6, "form": "large_tree", "over_structure": False, "mature_height_m": 15.2, "water_demand": "moderate"}]


def d_not_viable_plants(l):
    """The existing palette's Ixora coccinea (needs warmer than the 5.1 C typical-year minimum) as the main drift in the south beds."""
    for g in l["planting_groups"]:
        if g["id"] == "bed-rear": g["plants"] = [{"species": "Ixora coccinea", "count": 8, "form": "shrub"}, {"species": "Ophiopogon japonicus", "count": 6, "form": "ground_cover"}]


def d_sun_misfit(l):
    """Full-sun herbs and perennials (lavender, rosemary, gazania) planted in the north court, 1.3 h of summer sun."""
    for g in l["planting_groups"]:
        if g["id"] in ("bed-north", "bed-north-2"):
            g["plants"] = [{"species": "Lavandula dentata", "count": 4, "form": "shrub"}, {"species": "Gazania rigens", "count": 6, "form": "ground_cover"}]


def d_no_lounge_seats(l):
    """Four seats in the whole south garden: the lounge chairs and one dining chair are missing (capacity 4 against the brief's 10-20)."""
    l["seating"] = [s for s in l["seating"] if not s["id"].startswith("chair-")]
    l["tables"][0]["seats"] = 3


def d_dining_cut_off(l):
    """A 1.0 m planting bed across the door and a hedge between lounge and dining: seats unreachable on walkable ground."""
    l["planting_groups"].append({"id": "bed-block", "rect": [22.6, -27.1, 23.6, -25.2], "over_structure": False, "plants": [{"species": "Fatsia japonica", "count": 1, "form": "shrub"}]})
    l["screens"].append({"id": "hedge-mid", "kind": "hedge", "rect": [22.7, -25.1, 26.4, -24.7], "height_m": 1.8, "opacity": 0.9})
    l["canopies"] = []


def d_gathering_in_winter_shade(l):
    """Dining and lounge moved to the yard strip, which gets 0 h of sun on 21 Dec 10-15."""
    for z in l["zones"]:
        if z["id"] == "yard-west": z["use"] = "lounge"
        if z["id"] == "yard-standing": z["use"] = "dining"
    _seat_chairs(l, [(16.4, -22.0), (17.2, -22.0), (18.6, -22.0), (19.4, -22.0), (20.2, -22.0), (21.0, -22.0)], "yard-west")
    l["tables"][0]["center"] = [19.6, -21.5]; l["tables"][0]["zone"] = "yard-standing"
    l["features"] = [f for f in l["features"] if f["kind"] != "pond"]
    l["planting_groups"] = [g for g in l["planting_groups"] if g["id"] != "bed-pond"]


def d_evergreen_over_lounge(l):
    """A Ficus microcarpa (evergreen, 8 m spread, held to 6 m) on the west boundary, where the low winter sun comes from (it comes from the south-west): no winter sun."""
    l["trees"] = [{"id": "ficus", "species": "Ficus microcarpa", "center": [24.5, -29.4], "mature_spread_m": 8.0, "form": "large_tree", "over_structure": False, "mature_height_m": 6.0, "water_demand": "high"}]


def d_no_quiet(l):
    """The quiet bench removed from the south and north gardens."""
    l["seating"] = [s for s in l["seating"] if s["id"] not in ("bench-quiet", "bench-north")]


def d_green_only(l):
    """Only non-flowering foliage plants (no month of bloom): a green garden without seasonal colour."""
    k = ["Ophiopogon japonicus", "Aspidistra elatior", "Chlorophytum comosum", "Acorus gramineus", "Alpinia zerumbet", "Monstera deliciosa", "Cymbopogon citratus", "Ficus pumila"]
    n = 0
    for g in l["planting_groups"]:
        for p in g["plants"]:
            p["species"] = k[n % len(k)] if p["form"] != "shrub" else "Alpinia zerumbet"; n += 1
    l["trees"][0]["species"] = "Ficus carica"
    for g in l["planting_groups"]:
        g["plants"] = [{"species": q["species"], "count": q["count"], "form": q["form"]} for q in g["plants"]]


DEFECTS = {   # id: (builder, named quantity is in the docstring, criteria it must trip, split fixed in PREREG.md)
    "lone-specimens": (d_lone_specimens, ["H-DRIFTS"]),
    "no-enclosure": (d_no_enclosure, ["A-ENCLOSURE"]),
    "path-to-nowhere": (d_path_to_nowhere, ["A-PATH-TERMINUS"]),
    "seat-in-summer-sun": (d_seat_in_summer_sun, ["C-SUMMER-SHADE"]),
    "pond-deep-shade": (d_pond_deep_shade, ["C-POND-SUN"]),
    "pond-no-view": (d_pond_no_view, ["U-POND-VIEW"]),
    "fire-upwind": (d_fire_upwind, ["C-FIRE-WIND"]),
    "privacy-exposed": (d_privacy_exposed, ["C-PRIVACY"]),
    "toxic-by-herbs": (d_toxic_by_herbs, ["H-TOXIC-PLACEMENT"]),
    "single-layer": (d_single_layer, ["H-LAYERS"]),
    "oversize-tree": (d_oversize_tree, ["H-SIZE-VS-SPACE"]),
    "not-viable-plants": (d_not_viable_plants, ["H-SITE-VIABLE"]),
    "sun-misfit": (d_sun_misfit, ["H-SUN-FIT"]),
    "capacity-4": (d_no_lounge_seats, ["U-GATHER-SEATS"]),
    "dining-cut-off": (d_dining_cut_off, ["U-GATHER-ROUTE"]),
    "gathering-in-winter-shade": (d_gathering_in_winter_shade, ["C-WINTER-SUN"]),
    "evergreen-over-lounge": (d_evergreen_over_lounge, ["C-WINTER-SUN"]),
    "no-quiet": (d_no_quiet, ["U-QUIET-SOUTH", "U-QUIET-NORTH"]),
    "green-only": (d_green_only, ["H-SEASONALITY"]),
}


def make(defect_id: str) -> dict:
    lay = copy.deepcopy(base())
    fn, expect = DEFECTS[defect_id]
    fn(lay)
    lay["id"] = "seed-" + defect_id
    lay["seeded_defect"] = {"id": defect_id, "what": " ".join((fn.__doc__ or "").split()), "expect": expect}
    return lay


def save_all():
    OUT.mkdir(parents=True, exist_ok=True)
    save_base()
    for k in DEFECTS:
        (OUT / f"{k}.json").write_text(json.dumps(make(k), indent=1) + "\n")
