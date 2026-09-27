"""Round 11 (client 2026-09-27): four designs on the settled base, the extension stopped at the fifth column."""
import unittest

from archpipe.concept import revit_spec as RS
from archpipe.concept import villa as V
from archpipe.concept import villa_parking as P
from archpipe.concept import villa_r11 as R


class Designs(unittest.TestCase):
    def setUp(self):
        self.lays = R.designs()

    def test_four_designs_pass_every_check(self):
        self.assertEqual([l["id"] for l in self.lays], ["D1", "D2", "D3", "D4"])
        for lay in self.lays:
            sp = RS.build(lay)
            self.assertEqual(V.critique(lay)["fails"], [], lay["id"])
            self.assertFalse([e for e in V.elevation_checks(lay) if e["status"] == "fail"], lay["id"])
            self.assertEqual(RS.opening_problems(sp), [], lay["id"])
            self.assertEqual(RS.clearance_problems(lay, sp["walls"], sp["doors"], sp.get("infills", [])), [], lay["id"])
            self.assertEqual(RS.window_credit_problems(lay, sp["windows"], sp["doors"]), [], lay["id"])
            self.assertEqual(RS.glazing_problems(lay, sp["windows"], sp["doors"]), [], lay["id"])
            self.assertGreaterEqual(V.gf_route_width(lay), 0.9, lay["id"])

    def test_the_extension_ends_on_the_fifth_column_and_carries_one_car(self):
        col5 = sorted(c for c in V.E.COLUMNS if abs(c[3] / 1000 - V.YE) < 0.06)[4]
        for lay in self.lays:
            self.assertAlmostEqual(max(r[2] for r in lay["extension"]), col5[2] / 1000, places=3)
            pk = lay["parking2"]
            self.assertEqual(pk["cars"], 1)
            self.assertGreaterEqual(pk["deck"][2] - pk["deck"][0], P.CARS[1] - 1e-6)
            self.assertLess(max(r[2] for r in lay["extension"]) - P.RAMP_X1, P.CARS[2])   # two cars would not fit

    def test_the_rear_store_is_used_in_every_design(self):
        rear = V.REAR_SHARE
        for lay in self.lays:
            uses = [r for r in lay["rooms"].values() if r["level"] == "B" and r["rect"][1] < V.YP - 0.5
                    and r["rect"][0] >= rear[0] - 1e-6]
            self.assertTrue(uses and not all(r["occupancy"] == "store" for r in uses), lay["id"])

    def test_the_d4_void_stops_inside_the_perimeter_beams(self):
        sp = RS.build(R.design("D4"))
        (x0, y0, x1, y1), = sp["gf_voids"]
        self.assertAlmostEqual(x0, V.X0 + 0.25, places=3)
        self.assertAlmostEqual(y1, V.YE - 0.25, places=3)
        self.assertEqual(RS.build(R.design("D1"))["gf_voids"], [])


if __name__ == "__main__":
    unittest.main()
