"""G1 design fixes (docs/decisions/G1-safety-decisions-2026-11-21.md) exist in the D1 spec and the model, with dimensions.

Every number is derived from the spec or model, then compared with the named limit (ADK 2013 as carded by L1).
"""
import math
import unittest

from archpipe.concept import revit_spec as RS
from archpipe.concept import stairs as S
from archpipe.concept import villa_furnish as F
from archpipe.concept import villa_r11 as R
from archpipe.model import spec_source as SS
from archpipe.model.schema import validate


class G1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lay = R.design("D1")
        cls.sp = RS.build(cls.lay)
        cls.els = SS.all_from_spec(cls.lay, cls.sp)
        cls.by = {e.id: e for e in cls.els}

    # ---- LS2 open risers with infill
    def test_treads_overlap_16mm_and_going_unchanged(self):
        tr = self.sp["stair"]
        self.assertEqual(len(tr), 16)
        overlaps = [min(a[3], b[3]) - max(a[0], b[0]) for a, b in zip(tr, tr[1:])]      # plan overlap of consecutive treads
        self.assertGreaterEqual(min(overlaps), 16 - 1e-9)
        pitch = {round(a[3] - b[3], 3) for a, b in zip(tr, tr[1:])}
        self.assertEqual(pitch, {280.0})                                                 # nosing to nosing: the going is unchanged
        self.assertEqual(tr[0][3] - tr[0][0], 296.0)
        self.assertEqual(tr[-1][0], self.sp["gf_opening"][0] * 1000)                     # slab opening unchanged (x 5.177)

    def test_riser_and_going_within_adk(self):
        st = self.by["stair-main"].params
        self.assertLessEqual(st["riser_mm"], 220)
        self.assertGreaterEqual(st["tread_mm"], 220)
        self.assertEqual(st["going_mm"], 280.0)
        self.assertEqual(st["tread_depth_mm"], 296.0)
        self.assertTrue(550 <= 2 * st["riser_mm"] + st["going_mm"] <= 700)

    def test_infill_removed_by_client_waiver_2026_11_25(self):
        """Client veto 2026-11-25: no riser infill bars; recorded as a waiver with the consequence, overlap kept."""
        st = self.by["stair-main"].params
        self.assertEqual(self.sp["stair_infill"], [])
        self.assertFalse(st["riser_infill"])
        w = st["infill_waiver"]
        self.assertEqual((w["date"], w["by"], w["criterion"], w["required_mm"]), ("2026-11-25", "client", "LS2", 100.0))
        self.assertIn("child", w["consequence"])
        self.assertEqual(st["nosing_overlap_mm"], 16)                                    # the 16 mm overlap is kept

    def test_infill_not_counted_as_treads(self):
        self.assertTrue(all(b[5] - b[2] <= 60.0 + 1e-9 for b in self.sp["stair"]))
        self.assertEqual(len(self.sp["stair"]), 16)

    def test_true_headroom_at_least_2000(self):
        hr, _ = S.pitch_headroom(S.party_flight_r8(), [v * 1000 for v in self.sp["gf_opening"]])
        self.assertGreaterEqual(hr, S.HEAD)

    def test_stair_clashes_unchanged(self):
        c = S.clashes(S.party_flight_r8(), [v * 1000 for v in self.sp["gf_opening"]])
        self.assertEqual(c["hits"], [])
        self.assertEqual(c["outside_declared_opening"], [])

    # ---- LS3 guards
    def test_guards_present_with_dimensions(self):
        g = {x["id"]: x for x in self.sp["guards"]}
        self.assertEqual(set(g), {"guard-gf-stair-void", "guard-gf-terrace-edge", "guard-entrance-steps-patio-edge"})
        for x in g.values():
            self.assertGreaterEqual(x["height_m"], 1.1 - 1e-9)                           # 1100 mm (policy, external); >= 900 internal
            self.assertLess(x["max_opening_mm"], 100.0)
            self.assertFalse(x["climbable"])
        void = self.by["rail-gf-stair-void"].params
        self.assertEqual(void["edge_lengths_mm"][0], 3710.0)                             # the 3.71 m open edge
        self.assertEqual(void["edge_lengths_mm"][1], 950.0)
        self.assertEqual(void["drop_mm"], 3000.0)
        terrace = self.by["rail-gf-terrace-edge"].params
        self.assertAlmostEqual(terrace["edge_lengths_mm"][0], 5030.0, delta=60)          # the terrace west edge (5.08 m less 50 mm)
        self.assertEqual(terrace["drop_mm"], 3000.0)
        steps = self.by["rail-patio-steps-edge"].params
        self.assertEqual(steps["max_opening_mm"], 75.0)
        self.assertGreaterEqual(steps["drop_min_mm"], 1800.0)
        for gid in ("rail-gf-stair-void", "rail-gf-terrace-edge", "rail-patio-steps-edge"):
            self.assertEqual(self.by[gid].params["guard_height_mm"], 1100.0)
            self.assertTrue(self.by[gid].params["in_revit_spec"])
        self.assertTrue(self.by["slab-gf-terrace"].params["guard_present"])
        self.assertTrue(self.by["ctx-entrance-steps"].params["guard_present"])
        self.assertTrue(self.by["garden-north-patio"].params["guard_present"])

    def test_terrace_guard_clear_of_ramp_rail(self):
        ramp_rail = next(r for r in self.sp["rails"] if "north patio" in r["what"])
        g = next(x for x in self.sp["guards"] if x["id"] == "guard-gf-terrace-edge")
        south_y = g["path"][-1][1]
        self.assertLess(south_y, ramp_rail["y0"] - 0.012 / 2)                            # glass does not touch the rail

    # ---- LS4 door swing
    def test_core_door_swings_outward_away_from_the_stair(self):
        d = self.by["door-GF-landing-gf-core"].params
        self.assertEqual(d["swing_into"], "core")
        self.assertTrue(d["swing_known"])
        self.assertEqual(d["hinge_side"], "west")
        self.assertEqual(d["swing_direction"], "outward")
        door = next(x for x in self.sp["doors"] if set(x["rooms"]) == {"landing-gf", "core"})
        sw = door["swing"]
        self.assertLess(sw["hinge_x"], self.sp["gf_opening"][0])                         # hinge on the side away from the stair
        self.assertEqual(sw["near_jamb_to_top_step"], 0.075)                             # jamb distance as before: only the swing changed

    # ---- LS1 cupboard
    def test_cupboard_encloses_every_tread_under_2m(self):
        cb = self.sp["understair_cupboard"]
        low = [b for b in self.sp["stair"] if b[2] + 3000.0 < 2000.0]
        self.assertEqual(cb["treads"], len(low))
        self.assertEqual(cb["treads"], 11)
        self.assertLessEqual(cb["x0"], min(b[0] for b in low) / 1000 + 1e-9)
        self.assertGreaterEqual(cb["x1"], max(b[3] for b in low) / 1000 - 1e-9)
        self.assertLess(cb["soffit_max_m"], 2.0)
        self.assertTrue(cb["enclosed"])
        kinds = {w["id"] for w in cb["walls"]}
        self.assertEqual(kinds, {"understair-cupboard-side", "understair-cupboard-front", "understair-cupboard-end"})
        side = cb["walls"][0]
        for xa, xb, h in side["top_profile"]:                                            # wall top never above the soffit
            tread = next(b for b in low if abs(b[3] / 1000 - xa) < 1e-6)
            self.assertAlmostEqual(h, (tread[2] + 3000.0) / 1000, places=3)

    def test_cupboard_door_fits_under_the_soffit_and_clears_the_lounge_furniture(self):
        cb = self.sp["understair_cupboard"]
        d = cb["door"]
        x0, x1 = d["x"] - d["width"] / 2, d["x"] + d["width"] / 2
        low = [b for b in self.sp["stair"] if b[2] + 3000.0 < 2000.0]
        soffit = min((b[2] + 3000.0) / 1000 for b in low if b[0] / 1000 < x1 and b[3] / 1000 > x0)
        self.assertLessEqual(d["height"], soffit)
        self.assertGreaterEqual(d["width"], 0.6)
        side_y = cb["walls"][0]["y0"]
        swing = (x0, side_y + 0.05, x1, side_y + 0.05 + d["width"])                      # leaf swings into the lounge
        for it in F.layout(self.lay, products=False):
            fp = F.footprint(it)
            if it["room"] == "stair-b" and it["id"] == "stair-flight-store":
                continue                                                                 # existing under-stair store overlaps (open item)
            clash = fp[0] < swing[2] and fp[2] > swing[0] and fp[1] < swing[3] and fp[3] > swing[1]
            self.assertFalse(clash, "%s in the cupboard door swing" % it["id"])

    # ---- daylight option implemented
    def test_lounge_street_door_fills_its_run(self):
        door = next(d for d in self.sp["doors"] if d["rooms"] == ["lounge", "yard"] and d.get("full_height"))
        self.assertTrue(door["tight"])
        self.assertAlmostEqual(door["width"], 3.71, places=2)                            # was 3.41
        lo, hi = door["span"][2], door["span"][3]
        self.assertGreaterEqual(hi - lo - door["width"], 0.1 - 1e-6)                     # 50 mm reveal each side kept

    # ---- model
    def test_model_carries_all_of_it(self):
        self.assertEqual(validate(self.els), [])
        cup = self.by["joinery-understair-cupboard"]
        self.assertEqual(cup.params["treads_enclosed"], 11)
        self.assertEqual(cup.params["door"]["swing_into"], "lounge")
        self.assertTrue(self.by["stair-main"].params["under_flight"]["enclosed"])
        self.assertEqual(self.by["stair-main"].params["nosing_overlap_mm"], 16)

    def test_other_spec_counts_unchanged(self):
        kinds = {}
        for e in self.els:
            kinds[e.kind] = kinds.get(e.kind, 0) + 1
        self.assertEqual((kinds["wall"], kinds["door"], kinds["window"], kinds["stair"]), (36, 18, 8, 1))


if __name__ == "__main__":
    unittest.main()
