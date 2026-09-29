"""D1 round-2 post-condition, using the actual authored D1 option spec."""
import unittest

from archpipe.concept import revit_spec as RS
from archpipe.concept import villa_furnish3d as F3
from archpipe.concept import villa_r11 as R


LAY = R.design("D1")
SPEC = RS.build(LAY)
SPEC["furniture"] = F3.spec(LAY)


def readback():
    hatch = SPEC["hatches"][0]
    z = RS.LEVELS_Z[hatch["level"]]
    suite = next(d for d in SPEC["doors"] if set(d["rooms"]) == {"parents-bed", "parents-dressing"})
    return {
        "details": [{"mark": e["mark"], "category": e["category"],
                     "comments": e["comments"],
                     "bbox_mm": [v * 1000 for v in e["bbox"]]} for e in F3.round2_elements(SPEC)],
        "hatches": [{"mark": hatch["id"], "category": "Openings", "comments": hatch["closure"], "host_wall": 81,
                     "expected_host_wall": 81,
                     "host_line_mm": [[3617, hatch["y"] * 1000], [15412, hatch["y"] * 1000]],
                     "bbox_mm": [hatch["x0"] * 1000, (hatch["y"] - 0.1) * 1000,
                                 (z + hatch["sill"]) * 1000, hatch["x1"] * 1000,
                                 (hatch["y"] + 0.1) * 1000, (z + hatch["head"]) * 1000]}],
        "doors": [{"rooms": ["kitchen", "dirty-kitchen"], "width": 1.2,
                   "mark": "kitchen-dirty-sliding", "category": "Doors",
                   "comments": "telescopic-pocket-3; 3 leaves", "bbox_mm": [0] * 6},
                  {"rooms": suite["rooms"], "width": suite["width"], "category": "Doors",
                   "bbox_mm": [0] * 6, "point_mm": [suite["x"] * 1000, suite["y"] * 1000]}],
        "windows": [{"mark": "window-study-game-%.3f-%.3f" % (w["x"], w["y"]), "category": "Windows",
                     "bbox_mm": [0] * 6, "sill": w["sill"], "height": w["height"], "width": w["width"]}
                    for w in SPEC["windows"] if w.get("room") == "study-game"],
        "furniture": [{"mark": f["mark"], "bbox": f["envelope"], "comments": f["type"],
                       "bbox_mm": [(v + (RS.LEVELS_Z[f["level"]] if k in (2, 5) else 0)) * 1000
                                   for k, v in enumerate(f["envelope"])]}
                      for f in SPEC["furniture"]],
    }


class NativeDetails(unittest.TestCase):
    def test_approved_input_fields_reach_the_revit_payload(self):
        dressing = next(d for d in SPEC["doors"] if set(d["rooms"]) == {"parents-bed", "parents-dressing"})
        self.assertAlmostEqual(dressing["x"], 21.897)
        self.assertAlmostEqual(dressing["width"], 0.8)
        study = [w for w in SPEC["windows"] if w.get("room") == "study-game"]
        self.assertEqual(len(study), 2)
        self.assertTrue(all(abs(w["sill"] - 0.9) < 1e-8 and
                            abs(w["sill"] + w["height"] - 2.3) < 1e-8 for w in study))
        for option in ("D2", "D3"):
            other = RS.build(R.design(option))
            other_study = [w for w in other["windows"] if w.get("room") == "study-game"]
            self.assertEqual(len(other_study), 2)
            self.assertTrue(all(abs(w["sill"] - 0.9) < 1e-8 and
                                abs(w["sill"] + w["height"] - 2.3) < 1e-8 for w in other_study))
        furniture = {f["mark"]: f for f in SPEC["furniture"]}
        self.assertAlmostEqual(furniture["pb-bedside"]["footprint"][2] -
                               furniture["pb-bedside"]["footprint"][0], 0.35)
        self.assertTrue(any(p.startswith("ladder-") for f in SPEC["furniture"]
                            if f["type"].startswith("bed_") for p in f["parts"]))

    def test_real_spec_round_trip_is_quiet(self):
        self.assertEqual(F3.round2_postcondition(SPEC, readback(), LAY), [])

    def test_real_revit_opening_has_no_mark_and_is_matched_by_spec_id(self):
        # Revit 2027 build 2026-09-28: the Opening came back with mark None and category "Rectangular Straight Wall
        # Opening"; before spec_id was recorded the check reported "opening built 0 times" on a correct opening.
        rb = readback()
        rb["hatches"][0].update(mark=None, category="Rectangular Straight Wall Opening",
                                spec_id=SPEC["hatches"][0]["id"])
        self.assertEqual(F3.round2_postcondition(SPEC, rb, LAY), [])
        del rb["hatches"][0]["spec_id"]
        self.assertTrue(any("opening built 0 times" in p for p in F3.round2_postcondition(SPEC, rb, LAY)))

    def test_moved_hatch_fails(self):
        rb = readback()
        rb["hatches"][0]["bbox_mm"][0] += 10
        self.assertTrue(any("opening extent" in p for p in F3.round2_postcondition(SPEC, rb, LAY)))

    def test_hatch_on_wrong_wall_fails(self):
        rb = readback()
        rb["hatches"][0]["host_line_mm"][0][1] += 20
        self.assertTrue(any("wrong wall" in p for p in F3.round2_postcondition(SPEC, rb, LAY)))

    def test_wrong_door_width_fails(self):
        rb = readback()
        rb["doors"][0]["width"] = 1.1
        self.assertTrue(any("door" in p for p in F3.round2_postcondition(SPEC, rb, LAY)))

    def test_dressing_door_and_study_sill_are_measured(self):
        rb = readback()
        rb["doors"][1]["point_mm"][0] += 10
        rb["windows"][0]["sill"] = 1.7
        problems = F3.round2_postcondition(SPEC, rb, LAY)
        self.assertTrue(any("dressing door" in p for p in problems))
        self.assertTrue(any("window-study-game" in p for p in problems))

    def test_missing_grille_fails(self):
        rb = readback()
        rb["details"] = [x for x in rb["details"] if x["mark"] != "guest-wc-extract-grille"]
        self.assertTrue(any("guest-wc-extract-grille" in p for p in F3.round2_postcondition(SPEC, rb, LAY)))

    def test_glass_panel_ten_mm_off_fails(self):
        rb = readback()
        next(x for x in rb["details"] if x["mark"].startswith("stair-open-glass"))["bbox_mm"][3] += 10
        self.assertTrue(any("stair-open-glass" in p for p in F3.round2_postcondition(SPEC, rb, LAY)))

    def test_glass_panel_outside_stair_room_fails(self):
        rb = readback()
        panel = next(x for x in rb["details"] if x["mark"].startswith("stair-open-glass"))
        panel["bbox_mm"][4] += 10
        self.assertTrue(any("leaves room stair-b" in p for p in F3.round2_postcondition(SPEC, rb, LAY)))

    def test_wrong_category_column_and_room_fail(self):
        rb = readback()
        next(x for x in rb["details"] if x["mark"] == "pe-rain-head")["category"] = "Furniture"
        self.assertTrue(any("category" in p for p in F3.round2_postcondition(SPEC, rb, LAY)))
        rb = readback()
        fan = next(x for x in rb["details"] if x["mark"] == "guest-wc-extract-fan")
        fan["bbox_mm"][0] = 11200
        fan["bbox_mm"][3] = 11300
        fan["bbox_mm"][1] = -24000
        fan["bbox_mm"][4] = -23900
        problems = F3.round2_postcondition(SPEC, rb, LAY)
        self.assertTrue(any("structural column" in p for p in problems))
        self.assertTrue(any("leaves room" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
