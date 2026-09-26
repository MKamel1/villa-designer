"""Round 7 parking options: raised deck in the east yard, rooms under the ramp and deck."""
import unittest

from archpipe.concept import revit_spec as RS
from archpipe.concept import villa as V
from archpipe.concept import villa_parking as P


class ParkingGeometry(unittest.TestCase):
    def test_ramp_reaches_the_deck_at_the_card_gradient(self):
        self.assertAlmostEqual((P.RAMP_X1 - P.RAMP_X0) * P.GRADIENT, P.DECK_TOP, places=3)

    def test_clear_height_under_the_ramp(self):
        # street gate: +0.00 - 0.35 build-up over the -1.80 floor = 1.45 m; deck: 0.85 - 0.35 + 1.80 = 2.30 m
        self.assertAlmostEqual(P.clear_at(P.RAMP_X0), 1.45, places=3)
        self.assertAlmostEqual(P.clear_at(P.RAMP_X1), 2.30, places=3)
        self.assertAlmostEqual(P.clear_at(P.X_LOW), 2.00, places=3)
        self.assertAlmostEqual(P.clear_at(P.RAMP_X1 + 5), 2.30, places=3)


class ParkingOptions(unittest.TestCase):
    def setUp(self):
        self.opts = P.options()

    def test_four_options_pass_the_critic(self):
        self.assertEqual([o["id"] for o in self.opts], ["P1", "P2", "P3", "P4"])
        for lay in self.opts:
            self.assertEqual(V.critique(lay)["fails"], [], lay["id"])

    def test_under_rooms_reach_the_fence_without_gaps(self):
        for lay in self.opts:
            under = sorted((r for r in lay["rooms"].values() if r.get("ext")), key=lambda r: r["rect"][0])
            self.assertAlmostEqual(under[0]["rect"][0], V.FENCE_N, places=3)
            for a, b in zip(under, under[1:]):
                self.assertAlmostEqual(a["rect"][2], b["rect"][0], places=3, msg=lay["id"])
            self.assertAlmostEqual(under[-1]["rect"][2], lay["parking2"]["deck"][2], places=3)
            for r in under:
                self.assertAlmostEqual(r["rect"][3], V.FENCE_E, places=3)

    def test_rooms_under_the_ramp_have_their_working_height(self):
        need = {"utility": 2.0, "wc": 2.3, "store": 0.0}
        for lay in self.opts:
            for r in lay["rooms"].values():
                if r.get("ext"):
                    self.assertGreaterEqual(P.clear_at(r["rect"][0]) + 1e-6, need[r["occupancy"]], r["name"])

    def test_dirty_kitchen_opens_off_the_kitchen(self):
        for lay in self.opts:
            self.assertIn(("kitchen", "dirty-kitchen"), [tuple(l) for l in lay["links"]])

    def test_parking_elevation_rows_pass(self):
        for lay in self.opts:
            rows = [e for e in V.elevation_checks(lay) if e.get("group") == "parking2" or "deck" in e["item"]
                    or "ramp" in e["item"]]
            self.assertTrue(rows, lay["id"])
            self.assertFalse([e for e in rows if e["status"] == "fail"], lay["id"])

    def test_spec_has_ramp_deck_cars_and_high_sills_over_the_deck(self):
        for lay in self.opts:
            sp = RS.build(lay)
            pk = sp["parking2"]
            self.assertEqual(len(pk["cars"]), lay["parking2"]["cars"])
            self.assertAlmostEqual(pk["deck"]["z_top"], -1.2 + P.DECK_TOP, places=3)
            for car in pk["cars"]:
                self.assertLessEqual(car[2], pk["deck"]["x1"] + 1e-6)
            over = [w for w in sp["windows"] if w["level"] == "GF" and abs(w["y"] - V.YE) < 1e-6
                    and P.RAMP_X0 <= w["x"] <= pk["deck"]["x1"]]
            self.assertTrue(over)
            self.assertTrue(all(w["sill"] >= 1.5 for w in over))
            self.assertEqual(sp["roofs"], [])


class YardWall(unittest.TestCase):
    """The kept NE yard wall (client 2026-09-26): NE column to the street fence, 1.40 m from the basement floor."""

    def test_wall_runs_from_the_street_fence_to_the_ne_column(self):
        from archpipe import villa_env as E
        x0, y0, x1, y1 = E.YARD_WALL
        self.assertEqual(x1, E.BAR[0])
        self.assertEqual(x0, E.BAR[0] - E.OFFSET_N)
        self.assertEqual(y1, E.BAR[3])                           # east face flush with the villa's (client)
        self.assertEqual(y1 - y0, 250)

    def test_ramp_clears_the_wall_and_the_gate_fits_a_car(self):
        rows = {e["item"].split(" (")[0].split(":")[0]: e for e in V.elevation_checks(P.option("u", 1))}
        self.assertEqual(rows["NE yard wall top"]["status"], "pass")
        self.assertEqual(rows["car gate"]["status"], "pass")

    def test_a_higher_wall_would_hit_the_ramp(self):
        from archpipe import villa_env as E
        old = E.YARD_WALL_H
        try:
            E.YARD_WALL_H = 1500                                   # top at -0.30: above the -0.35 soffit at the gate
            rows = [e for e in V.elevation_checks(P.option("u", 1)) if e["item"].startswith("NE yard wall")]
            self.assertEqual(rows[0]["status"], "fail")
        finally:
            E.YARD_WALL_H = old

    def test_store_side_on_the_wall_is_not_a_window(self):
        lay = P.option("u", 1)
        faces = V.window_faces("B", lay["extension"])
        self.assertFalse([f for f in faces if f[0] == "h" and abs(f[1] - V.YE) < 1e-6 and f[2] < V.X0])


    def test_store_uses_the_kept_wall_with_an_infill_to_the_ramp(self):
        from archpipe import villa_env as E
        sp = RS.build(P.option("u", 1))
        on_wall = [w for w in sp["walls"] if w["level"] == "B" and abs(w["y0"] - w["y1"]) < 1e-6
                   and abs(w["y0"] - V.YE) < 0.2 and max(w["x0"], w["x1"]) <= E.YARD_WALL[2] / 1000 + 1e-6]
        self.assertEqual(on_wall, [])
        prof = sp["infill"]["profile"]
        self.assertAlmostEqual(prof[0][1], -3.0 + 1.4, places=3)          # starts on the wall top
        self.assertAlmostEqual(prof[3][1] - prof[0][1], 0.05, places=3)   # 50 mm at the gate
        self.assertAlmostEqual(prof[2][1] - prof[1][1], 0.424, places=3)  # 424 mm at the villa

    def test_non_parking_spec_has_no_infill(self):
        from archpipe.concept import villa_options as VO
        self.assertNotIn("infill", RS.build(VO.s1()))


class UnderRampFit(unittest.TestCase):
    """Client review r7: walls came through the ramp and a 2.1 m door opened under a 1.9 m soffit."""

    def test_every_option_fits_under_the_soffit(self):
        for lay in P.options():
            sp = RS.build(lay)
            self.assertEqual(RS.clearance_problems(lay, sp["walls"], sp["doors"], sp["infills"]), [], lay["id"])

    def test_a_full_height_cross_wall_is_caught(self):
        lay = P.option("u", 2)
        sp = RS.build(lay)
        cross = [w for w in sp["walls"] if w["level"] == "B" and abs(w["x0"] - 5.377) < 1e-6]
        cross[0]["height"] = RS.WALL_H                                   # the as-built defect
        self.assertTrue(RS.clearance_problems(lay, sp["walls"], sp["doors"], sp["infills"]))

    def test_a_flat_fence_wall_without_infill_is_caught(self):
        lay = P.option("u", 2)
        sp = RS.build(lay)
        self.assertTrue(any("open under the soffit" in p
                            for p in RS.clearance_problems(lay, sp["walls"], sp["doors"], [])))

    def test_a_room_door_under_the_low_ramp_is_caught(self):
        lay = P.option("u", 1)
        sp = RS.build(lay)
        d = [d for d in sp["doors"] if d.get("rooms") == ["lounge", "store-ramp"]][0]
        d.update(x=4.497, height=2.10)                                   # where and how it was built
        self.assertTrue(any(p.startswith("door") for p in
                            RS.clearance_problems(lay, sp["walls"], sp["doors"], sp["infills"])))

    def test_door_fit_kinds(self):
        self.assertEqual(P.door_fit(3.617, 5.377, 0.8, "store")[3], "low")
        self.assertEqual(P.door_fit(3.617, 5.377, 0.8, "utility")[3], "none")
        self.assertEqual(P.door_fit(5.377, 7.377, 0.8, "utility")[3], "reduced")
        self.assertEqual(P.door_fit(9.227, 11.2, 0.8, "wc")[3], "full")


class Negative(unittest.TestCase):
    def test_a_closed_windowless_room_still_fails_window(self):
        lay = P.option("u", 1)
        lay["rooms"]["laundry"]["occupancy"] = "bedroom"          # habitable, closed door, no window to the fence
        self.assertIn("window", V.critique(lay)["fails"])

    def test_steeper_ramp_fails(self):
        lay = P.option("u", 1)
        lay["parking2"] = dict(lay["parking2"], gradient=0.15)
        rows = [e for e in V.elevation_checks(lay) if "gradient" in e["item"].lower() or "ramp" in e["item"].lower()]
        self.assertTrue(any(e["status"] == "fail" for e in rows))

    def test_non_parking_layout_keeps_block_roofs(self):
        from archpipe.concept import villa_options as VO
        sp = RS.build(VO.s5())
        self.assertNotIn("parking2", sp)
        self.assertTrue(sp["roofs"])


if __name__ == "__main__":
    unittest.main()
