"""D1 round-3 Revit payload and measured read-back contract."""
import unittest

from archpipe.concept import revit_spec as RS
from archpipe.concept import villa_furnish3d as F3
from archpipe.concept import villa_r11 as R


LAY = R.design("D1")
SPEC = RS.build(LAY)
SPEC["furniture"] = F3.spec(LAY)
DETAILS = F3.round3_elements(SPEC, LAY)
SPEC["round3_elements"] = DETAILS


def readback():
    return {
        "round3_details": [{"spec_id": d["mark"], "mark": d["mark"], "category": d["category"],
                            "comments": d["comments"], "bbox_mm": [v * 1000 for v in d["bbox"]]}
                           for d in DETAILS],
        "furniture": [{"mark": f["mark"], "category": f["category"], "comments": f["type"],
                       "bbox_mm": [(v + (RS.LEVELS_Z[f["level"]] if k in (2, 5) else 0)) * 1000
                                   for k, v in enumerate(f["envelope"])]}
                      for f in SPEC["furniture"]],
    }


class Round3BuilderContract(unittest.TestCase):
    def test_real_spec_round_trip_and_counts(self):
        self.assertEqual(len(SPEC["furniture"]), 72)  # gwc-shower: the new guest open wet zone belongs in Revit
        self.assertIn("gwc-shower", {item["mark"] for item in SPEC["furniture"]})
        self.assertEqual(len(DETAILS), 75)   # round 3b: open bays, sides, shelves, bike hooks; stored contents excluded
        self.assertEqual(sum(d["mark"].startswith("SWING-") for d in DETAILS), 6)
        self.assertEqual(sum(d["mark"].startswith("DLN-") for d in DETAILS), 2)
        self.assertEqual(sum("-module-" in d["mark"] for d in DETAILS), 8)
        self.assertEqual(sum("-body-" in d["mark"] for d in DETAILS), 59)   # 51 + 8 new joinery parts (round 3b)
        self.assertFalse(any("curtain" in d["mark"].lower() for d in DETAILS))
        bath = next(d for d in F3.round2_elements(SPEC) if d["mark"] == "pe-bath-screen")
        self.assertIn("transmittance 0.91; ior 1.52", bath["comments"])
        by_mark = {f["mark"]: f for f in SPEC["furniture"]}
        for module in (d for d in DETAILS if "-module-" in d["mark"]):
            parent = by_mark[module["mark"].split("-module-")[0]]
            z = RS.LEVELS_Z[parent["level"]]
            envelope = [v + (z if k in (2, 5) else 0) for k, v in enumerate(parent["envelope"])]
            self.assertTrue(all(module["bbox"][k] >= envelope[k] - F3.TOL for k in range(3)))
            self.assertTrue(all(module["bbox"][k] <= envelope[k] + F3.TOL for k in range(3, 6)))
        self.assertEqual(F3.round3_postcondition(SPEC, readback(), LAY), [])

    def test_moved_swing_lamp_fails(self):
        rb = readback()
        next(d for d in rb["round3_details"] if d["mark"].startswith("SWING-") and
             d["mark"].endswith("-head"))["bbox_mm"][0] += 10
        self.assertTrue(any("SWING-" in p and "bbox" in p for p in F3.round3_postcondition(SPEC, rb, LAY)))

    def test_missing_dressing_module_fails(self):
        rb = readback()
        rb["round3_details"] = [d for d in rb["round3_details"] if d["mark"] != "pd-hang-1-module-01"]
        self.assertTrue(any("pd-hang-1-module-01" in p for p in F3.round3_postcondition(SPEC, rb, LAY)))

    def test_storage_body_above_soffit_fails(self):
        rb = readback()
        next(d for d in rb["round3_details"] if d["mark"].startswith("stair-flight-store-body-")
             and "-back" in d["comments"])["bbox_mm"][5] += 10
        self.assertTrue(any("stair-flight-store-body" in p and "bbox" in p
                            for p in F3.round3_postcondition(SPEC, rb, LAY)))

    def test_swapped_owner_fails(self):
        rb = readback()
        next(d for d in rb["round3_details"] if d["mark"] == "pd-hang-1-module-01")["comments"] = \
            "owner his; kind long-hang"
        self.assertTrue(any("pd-hang-1-module-01" in p and "Comments" in p
                            for p in F3.round3_postcondition(SPEC, rb, LAY)))

    def test_moved_armchair_and_curtain_fail(self):
        rb = readback()
        next(d for d in rb["furniture"] if d["mark"] == "lounge-armchair")["bbox_mm"][0] += 10
        rb["round3_details"].append(dict(mark="library-nook-curtain"))
        problems = F3.round3_postcondition(SPEC, rb, LAY)
        self.assertTrue(any("lounge-armchair" in p for p in problems))
        self.assertTrue(any("curtain" in p for p in problems))

    def test_generic_fixture_requires_kind_tag(self):
        rb = readback()
        row = next(d for d in rb["round3_details"] if d["mark"].startswith("SWING-"))
        row["category"] = "Generic Models"
        row["comments"] += "; fixture kind SWING"
        self.assertEqual(F3.round3_postcondition(SPEC, rb, LAY), [])


if __name__ == "__main__":
    unittest.main()


class StoredContentsStayOutOfRevit(unittest.TestCase):
    def test_contents_are_not_construction(self):
        # the round-3 storage change put suitcases, boxes and a vacuum into the Revit payload (67 -> 93 details)
        kinds = {d["comments"].split("; ")[1] for d in F3.round3_elements(SPEC) if "-body-" in d["mark"]}
        self.assertFalse(kinds & F3.STORED_CONTENTS, kinds & F3.STORED_CONTENTS)
