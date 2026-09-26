"""The villa concept critic: the concepts as generated, and one seeded defect per check (it must fail when it should
and stay quiet when it should)."""
import copy
import unittest

from archpipe.concept import villa as V


def status(res, name):
    return next(c for c in res["checks"] if c["check"] == name)["status"]


class Concepts(unittest.TestCase):
    def test_a_and_b_have_no_failures(self):
        for lay in (V.concept_a(), V.concept_b()):
            res = V.critique(lay)
            self.assertEqual(res["fails"], [], (lay["id"], res["fails"]))

    def test_b_parking_alternative_has_no_failures_and_the_extra_room_has_windows(self):
        res = V.critique(V.concept_b())
        self.assertEqual(res["fails"], [])
        self.assertGreaterEqual(res["window_m"]["extra-room"], 1.0)     # front-yard side + the yard end

    def test_the_street_strip_is_not_floor(self):
        """The strip is an outdoor terrace (Revit: 900 mm parapet walls, sliding door): no room may sit on it."""
        for lay in V.concepts():
            for rid, r in lay["rooms"].items():
                if r["level"] == "GF":
                    self.assertGreaterEqual(r["rect"][0], V.X0 - 1e-6, rid)


class StairStructure(unittest.TestCase):
    def test_u_stair_clears_the_kept_structure(self):
        from archpipe.concept import stairs as S
        self.assertEqual(S.clashes(S.u_in_old_bay())["hits"], [])

    def test_round3_flight_hits_column_1590377(self):
        """The real round-3 geometry: the flight's top runs into the front party-side column (CAD/Revit 1590377)."""
        lay = V.concept_a()
        lay["stair"] = "r3"
        chk = next(c for c in V.critique(lay)["checks"] if c["check"] == "stair_structure")
        self.assertEqual(chk["status"], "fail")
        self.assertTrue(any("1590377" in c for c in chk["clashes"]), chk["clashes"])

    def test_u_stair_uses_the_old_bay_and_280_goings(self):
        g = V.stair_geometry()
        self.assertEqual(g["going"], 280)
        self.assertTrue(g["fits"])
        self.assertLessEqual(g["rise"], 220)
        self.assertTrue(550 <= g["two_r_plus_g"] <= 700)


class StairAccess(unittest.TestCase):
    def test_every_stair_end_opens_onto_circulation(self):
        for lay in V.concepts():
            chk = next(c for c in V.critique(lay)["checks"] if c["check"] == "stair_access")
            self.assertEqual(chk["status"], "pass", (lay["id"], chk["ends"]))

    def test_stair_end_facing_no_circulation_fails(self):
        """The class of the round-2 defect: a stair end that only a room (or nothing) touches."""
        lay = copy.deepcopy(V.concept_a())
        lay["rooms"]["stair-b"]["ends"] = [["h", V.YE, V.SX0, V.SX0 + 0.9]]      # the facade end: nothing there
        res = V.critique(lay)
        self.assertEqual(status(res, "reachability"), "pass")          # the graph alone does not see it
        self.assertEqual(status(res, "stair_access"), "fail")

    def test_undeclared_ends_fail(self):
        lay = copy.deepcopy(V.concept_a())
        del lay["rooms"]["stair-gf"]["ends"]
        self.assertEqual(status(V.critique(lay), "stair_access"), "fail")


class Elevations(unittest.TestCase):
    def test_all_elevation_checks_pass_for_a_and_b(self):
        for lay in (V.concept_a(), V.concept_b()):
            bad = [c["item"] for c in V.elevation_checks(lay) if c["status"] == "fail"]
            self.assertEqual(bad, [], lay["id"])

    def test_room_under_the_deck_at_basement_level_is_too_low(self):
        """Negative: the old sheet's room at the basement floor under a street-level deck has 1.45 m."""
        old = V.EXTRA_FFL
        try:
            V.EXTRA_FFL = -1.80
            row = next(c for c in V.elevation_checks(V.concept_b()) if c["item"].startswith("room under the deck"))
            self.assertEqual(row["status"], "fail")
            self.assertAlmostEqual(row["achieved"], 1.45, places=2)
        finally:
            V.EXTRA_FFL = old

    def test_landing_pushed_into_the_facade_columns_fails_the_run(self):
        old = V.U_LANDING_LIMIT
        try:
            V.U_LANDING_LIMIT = -24.4             # 2.97 m to the column line: 8 goings of 280 + a 0.95 landing do not fit
            row = next(c for c in V.elevation_checks(V.concept_a()) if c["item"].startswith("private stair run"))
            self.assertEqual(row["status"], "fail")
        finally:
            V.U_LANDING_LIMIT = old

    def test_every_programme_room_is_placed(self):
        import json
        prog = json.loads((V.ROOT / V.PROJECT).read_text(encoding="utf-8"))["programme"]
        need = {p["id"] for p in prog} - {"stair"}
        for lay in V.concepts():
            ids = {r.replace("-gf", "").replace("-b", "") if r.startswith("stair") else r for r in lay["rooms"]}
            have = ids | {"living" for r in lay["rooms"] if lay["rooms"][r]["occupancy"] == "living"}
            self.assertFalse(need - have, (lay["id"], need - have))

    def test_suite_is_on_one_storey_with_its_bathroom(self):
        for lay in V.concepts():
            lv = {r["level"] for r in lay["rooms"].values() if r.get("suite")}
            self.assertEqual(len(lv), 1, lay["id"])


class SeededDefects(unittest.TestCase):
    def mutate(self, fn):
        lay = copy.deepcopy(V.concept_a())
        fn(lay)
        return V.critique(lay)

    def test_room_pushed_into_the_core_fails_envelope(self):
        def f(lay):
            lay["rooms"]["kids-a"]["rect"][1] = V.YP - 0.5
        self.assertEqual(status(self.mutate(f), "within_envelope"), "fail")

    def test_overlapping_rooms_fail(self):
        def f(lay):
            lay["rooms"]["kids-b"]["rect"][0] -= 0.5
        self.assertEqual(status(self.mutate(f), "no_overlap"), "fail")

    def test_bedroom_below_ndss_fails_but_small_bathroom_only_warns(self):
        def small_bed(lay):
            lay["rooms"]["kids-a"]["rect"][2] = lay["rooms"]["kids-a"]["rect"][0] + 2.9
        self.assertEqual(status(self.mutate(small_bed), "min_area"), "fail")

        def small_bath(lay):
            r = lay["rooms"]["family-bath"]["rect"]
            r[3] = r[1] + 1.6
        res = self.mutate(small_bath)
        self.assertEqual(status(res, "min_area"), "warning")
        self.assertNotIn("min_area", res["fails"])

    def test_narrow_first_bedroom_fails_width(self):
        def f(lay):
            r = lay["rooms"]["parents-bed"]["rect"]
            r[0] = r[2] - 2.7                     # 2.45 m clear < 2.75
        self.assertEqual(status(self.mutate(f), "min_width"), "fail")

    def test_habitable_room_on_the_party_wall_only_is_dark(self):
        def f(lay):
            lay["rooms"]["gallery"]["occupancy"] = "study"    # basement gallery: party wall + partitions only
        res = self.mutate(f)
        self.assertIn("gallery", next(c for c in res["checks"] if c["check"] == "window")["rooms"])

    def test_room_on_the_street_face_is_not_dark(self):
        """Negative of the above: the flex room's street face is 3.78 m, the NE corner column takes 0.51 + 0.1 margin,
        leaving 3.12 m clear, so it can have a window."""
        def f(lay):
            lay["rooms"]["flex"]["occupancy"] = "study"
        res = self.mutate(f)
        self.assertNotIn("flex", next(c for c in res["checks"] if c["check"] == "window")["rooms"])

    def test_a_street_face_taken_by_a_column_is_dark(self):
        """Round 8: the hall's street face is 1.30 m, but the party-side column takes 0.51 m + a 0.1 m frame margin,
        leaving 0.69 m (< the 1.0 m a window face needs): as a habitable room it would be dark."""
        def f(lay):
            lay["rooms"]["hall-b"]["occupancy"] = "study"
        res = self.mutate(f)
        self.assertIn("hall-b", next(c for c in res["checks"] if c["check"] == "window")["rooms"])

    def test_unbuildable_door_fails(self):
        def f(lay):
            lay["links"].append(["kids-a", "parents-bed"])     # they do not touch
        self.assertEqual(status(self.mutate(f), "links_built"), "fail")

    def test_entrance_off_the_core_fails(self):
        def f(lay):
            lay["entries"][0][2] = "core-lobby"                 # GF lobby door is at x 14.1-15.9; the corridor is,
            lay["rooms"]["corridor"]["rect"][2] = 12.0          # after this cut, short of it
            lay["rooms"]["corridor"]["rect"][0] = 3.617
        res = self.mutate(f)
        self.assertEqual(status(res, "entrances"), "fail")

    def test_suite_reached_through_living_fails_privacy(self):
        def f(lay):
            # only the basement entrance, and the GF hall turned into a living room: the suite is then reached
            # only across a public room
            lay["entries"] = [e for e in lay["entries"] if e[1] == "B"]
            lay["rooms"]["corridor"]["occupancy"] = "living"
        res = self.mutate(f)
        self.assertEqual(status(res, "suite_privacy"), "fail")

    def test_room_only_reachable_through_the_suite_fails_privacy(self):
        def f(lay):
            lay["links"] = [l for l in lay["links"] if l != ["corridor", "family-bath"]]
            lay["links"].append(["parents-bed", "family-bath"])
        res = self.mutate(f)
        chk = next(c for c in res["checks"] if c["check"] == "suite_privacy")
        self.assertEqual(chk["status"], "fail")
        self.assertIn("family-bath", chk["reached_only_through_suite"])

    def test_no_wc_on_an_entrance_storey_fails(self):
        def f(lay):
            lay["rooms"]["guest-wc"]["occupancy"] = "store"
        self.assertEqual(status(self.mutate(f), "wc_access"), "fail")


if __name__ == "__main__":
    unittest.main()
