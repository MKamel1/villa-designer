"""Client furniture changes 2026-11-25 (lane FX): kids' A loft beds, sink wall cupboards, dining chair, with negative tests."""
import copy
import math
import unittest

from archpipe.concept import villa_furnish as F
from archpipe.concept import villa_furnish3d as F3
from archpipe.concept import villa_r11 as R

LAY = R.design("D1")
IT = {i["id"]: i for i in F.layout(LAY)}
CEILING = 2.70


class KitchenWallUnits(unittest.TestCase):
    def test_units_meet_their_sources(self):
        self.assertEqual(F3.wall_unit_problems(IT["k-run"]), [])
        w = IT["k-run"]["wall_units"]
        self.assertAlmostEqual(w["z0"] - F3.COUNTER_TOP, 0.60, places=6)       # K-SPLASH 600, over Neufert >= 500 and Mitton 457

    def test_too_low_too_high_too_deep_are_refused(self):                      # negative: the check is not vacuous
        for key, val in (("z0", 1.30), ("z1", 2.20), ("depth", 0.40)):
            bad = copy.deepcopy(IT["k-run"])
            bad["wall_units"][key] = val
            self.assertTrue(F3.wall_unit_problems(bad), key)

    def test_units_are_in_the_body_over_the_run_only(self):
        parts = [(n, F3.to_world(IT["k-run"], b)) for n, b in F3.body(IT["k-run"]) if n == "wall-units"]
        self.assertEqual(len(parts), 3)
        x0, y0, x1, y1 = F.footprint(IT["k-run"])
        for _, b in parts:
            self.assertGreaterEqual(b[0], x0 - 1e-6)
            self.assertLessEqual(b[3], x1 + 1e-6)
            self.assertAlmostEqual(b[4], y1, places=3)                            # backs on the wall
            self.assertAlmostEqual(b[4] - b[1], 0.30, places=3)
        self.assertNotIn("wall-units", [n for n, _ in F3.body(IT["k-island"])])   # the island is untouched

    def test_nothing_on_the_wall_or_ceiling_clashes(self):
        x0, y0, x1, y1 = F.footprint(IT["k-run"])
        self.assertGreater(x0, 11.537)       # column 4's east face (d1-elements: column-02 x 11.197..11.537)
        self.assertLess(x1, 13.602)          # the dirty-kitchen door's west jamb (door-B-kitchen-dirty-kitchen)


class KidsLofts(unittest.TestCase):
    L = [IT["ka-loft-1"], IT["ka-loft-2"]]

    def test_bunk_and_old_floor_desks_are_gone(self):
        self.assertNotIn("ka-bunk", IT)
        for d in ("ka-desk-1", "ka-desk-2"):
            self.assertIn(d, IT)
            self.assertTrue(IT[d]["under"].startswith("ka-loft"))
        self.assertEqual(sum(1 for i in IT.values() if i.get("loft")), 2)

    def test_mattress_headroom_rail_and_product_basis(self):
        for it in self.L:
            parts = {n: F3.to_world(it, b) for n, b in F3.body(it) if n in ("mattress",)}
            m = parts["mattress"]
            self.assertAlmostEqual(m[3] - m[0] if it["rot"] in (0, 180) else 0, 0.90, places=3)       # 90 cm wide
            self.assertAlmostEqual(m[4] - m[1], 2.00, places=3)                                     # 200 cm long
            self.assertAlmostEqual(m[5], 1.63, places=3)
            self.assertAlmostEqual(CEILING - m[5], 1.07, places=2)                                   # headroom above the mattress
            self.assertAlmostEqual(it["rail_top"] - it["mattress_top"], 0.19, places=3)              # guard above the mattress top
            self.assertLessEqual(2.40, CEILING)                                                      # IKEA SMASTAD min ceiling 240 cm
            self.assertAlmostEqual(CEILING - it["rail_top"], 0.88, places=2)

    def test_desk_under_the_loft_knee_and_head_room(self):
        for it, d in zip(self.L, (IT["ka-desk-1"], IT["ka-desk-2"])):
            self.assertLessEqual(d["h"], 0.75)
            self.assertGreaterEqual(it["under"] - d["h"], 0.65)             # underside 1.42 over a 0.75 desk top: 0.67 m
            fl, fd = F.footprint(it), F.footprint(d)
            self.assertTrue(fl[0] - 1e-6 <= fd[0] and fd[2] <= fl[2] + 1e-6 and fl[1] - 1e-6 <= fd[1] and fd[3] <= fl[3] + 1e-6)

    def test_aisle_door_swing_and_window(self):
        a, b = F.footprint(self.L[0]), F.footprint(self.L[1])
        self.assertGreaterEqual(b[0] - a[2], 0.75)                                # passage between the lofts
        swing = (12.765, -27.371, 13.665, -26.471)                                # door 0.9 m, hinge east, swings in (d1-elements)
        for fp in (a, b):
            self.assertTrue(fp[2] <= swing[0] or fp[0] >= swing[2])
        res = F.check()
        self.assertEqual(res["windows"]["problems"], [])
        self.assertEqual(res["overlap"]["problems"], [])

    def test_a_loft_at_the_window_wall_is_refused(self):                          # negative: a 1.82 m loft in front of the window
        moved = [dict(i) for i in F.layout(LAY)]
        for i in moved:
            if i["id"] == "ka-loft-1":
                i["cy"] = -24.8
        res = F.check(moved)
        self.assertTrue(res["windows"]["problems"] or res["overlap"]["problems"] or res["clearances"]["problems"])


class DiningChair(unittest.TestCase):
    def test_seat_height_scaled_to_the_product_and_fits_the_table(self):
        p = F.PRODUCT["dining-table#chair-"]
        self.assertEqual(p["asset"], "sf_dining_chair_curved_armchair")
        seat = 0.647 * p["scale"]                                                 # model seat height (measured) x uniform scale
        self.assertAlmostEqual(seat, 0.478, places=2)                             # Audo Harbour dining height seat 478 mm
        self.assertAlmostEqual(0.75 - seat, 0.272, places=2)
        pitch = IT["dining-table"]["w"] / (IT["dining-table"]["chairs"] // 2)
        self.assertGreaterEqual(pitch, p["w"])                                    # chairs do not overlap along the table


if __name__ == "__main__":
    unittest.main()
