"""A small layout that satisfies every quantitative rule. Tests mutate copies to make negatives."""
import copy


def good():
    return copy.deepcopy({
        "schema": "landscape-layout/1",
        "zones": [
            {"id": "z-dine", "use": "dining", "rect": [0, 0, 6, 6], "surface": "paving", "enclosure_height_m": 2.0},
            {"id": "z-lounge", "use": "lounge", "rect": [8, 0, 14, 6], "surface": "paving", "enclosure_height_m": 2.0},
            {"id": "z-lawn", "use": "other", "rect": [0, 8, 6, 14], "surface": "lawn", "slope_pct": 2},
        ],
        "paths": [{"id": "p-main", "class": "main", "width_m": 1.4, "cross_slope_pct": 1.5, "long_slope_pct": 2},
                  {"id": "p-sec", "class": "secondary", "width_m": 0.9, "cross_slope_pct": 2}],
        "paved_areas": [{"id": "pave-dine", "zone": "z-dine", "rect": [0, 0, 6, 6], "material": "concrete", "slope_pct": 1}],
        "steps": [{"id": "st-1", "riser_mm": 140, "going_mm": 380, "count": 3, "width_mm": 1200}],
        "seatwalls": [{"id": "sw-1", "height_mm": 420, "width_mm": 420}],
        "tables": [{"id": "t-1", "zone": "z-dine", "center": [3, 3], "diameter_m": 1.2, "seats": 6}],
        "seating": [{"id": "sofa-1", "zone": "z-lounge", "rect": [10, 2, 12.5, 3], "seats": 5}],
        "planting_groups": [{"id": "bed-a", "rect": [20, 0, 24, 3], "over_structure": True, "soil_depth_mm": 700,
                             "plants": [{"species": "A", "water_need": "low", "form": "shrub"},
                                        {"species": "B", "water_need": "low", "form": "shrub"}]}],
        "trees": [{"id": "tree-1", "species": "T", "center": [10, 12], "mature_spread_m": 4, "form": "small_tree"}],
        "features": [
            {"id": "fire-1", "kind": "firepit", "center": [16, 10], "diameter_m": 1.0, "flush": True,
             "cover": {"load_rating_kN": 5}, "product_clearance_mm": 1500},
            {"id": "pond-1", "kind": "pond", "rect": [20, 8, 23, 10], "edge": "soft", "freeboard_mm": 150, "flush": True,
             "margin_slope_back_mm": 600},
        ],
        "boundary": [{"id": "b-n", "side": "neighbour", "kind": "wall", "height_m": 1.8}],
        "buildings": [[-10, -10, -2, 20]],
        "obstacles": [],
    })
