"""The villa concept critic: the concepts as generated, and one seeded defect per check (it must fail when it should
and stay quiet when it should)."""
import copy
import unittest

from archpipe.concept import villa as V


def status(res, name):
    return next(c for c in res["checks"] if c["check"] == name)["status"]


class Concepts(unittest.TestCase):
    def test_a_and_c_have_no_failures(self):
        for lay in (V.concept_a(), V.concept_c()):
            res = V.critique(lay)
            self.assertEqual(res["fails"], [], (lay["id"], res["fails"]))

    def test_b_parking_alternative_has_no_failures_and_the_extra_room_has_windows(self):
        res = V.critique(V.concept_b())
        self.assertEqual(res["fails"], [])
        self.assertGreaterEqual(res["window_m"]["extra-room"], 1.0)     # front-yard side + the yard end

    def test_spine_stair_frees_the_facade(self):
        """The stair study: along the blind party wall the rooms on the facade are larger than with the dog-leg."""
        spine, bay = V.critique(V.concept_a("spine")), V.critique(V.concept_a("bay"))
        for rid in ("kids-a", "kids-b", "parents-bed", "kitchen"):
            self.assertGreater(spine["sizes"][rid]["net_m2"], bay["sizes"][rid]["net_m2"], rid)


class StairAccess(unittest.TestCase):
    def test_every_stair_end_opens_onto_circulation(self):
        for lay in V.concepts() + [V.concept_c()]:
            chk = next(c for c in V.critique(lay)["checks"] if c["check"] == "stair_access")
            self.assertEqual(chk["status"], "pass", (lay["id"], chk["ends"]))

    def test_round2_defect_is_caught(self):
        """The real defect the client found: the basement foot at the street end, touched only by the flex room
        and the laundry (and the wall), with the stair still 'linked' to the hall along its side."""
        lay = copy.deepcopy(V.concept_a())
        b = lay["rooms"]["stair-b"]
        b["rect"][0] = V.X0
        b["ends"] = [["v", V.X0, V.YP, V.YS1]]
        del lay["rooms"]["store-under"]
        lay["links"] = [l for l in lay["links"] if "store-under" not in l]
        lay["links"] += [["stair-b", "flex"], ["stair-b", "pantry"]]     # round 2 linked them along the flight
        res = V.critique(lay)
        self.assertEqual(status(res, "reachability"), "pass")          # the graph alone did not see it
        self.assertEqual(status(res, "stair_access"), "fail")

    def test_undeclared_ends_fail(self):
        lay = copy.deepcopy(V.concept_a())
        del lay["rooms"]["stair-gf"]["ends"]
        self.assertEqual(status(V.critique(lay), "stair_access"), "fail")


class Elevations(unittest.TestCase):
    def test_all_elevation_checks_pass_for_a_and_b(self):
        for lay in (V.concept_a(), V.concept_a("bay"), V.concept_b()):
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

    def test_short_stair_zone_fails_the_run(self):
        old = V.SPINE_X1
        try:
            V.SPINE_X1 = 7.217                   # 3.40 m clear: 15 goings of 240 do not fit
            row = next(c for c in V.elevation_checks(V.concept_a()) if c["item"].startswith("private stair run"))
            self.assertEqual(row["status"], "fail")
        finally:
            V.SPINE_X1 = old

    def test_stair_values_come_from_the_cards(self):
        g = V.stair_geometry("spine")
        self.assertLessEqual(g["rise"], 220)
        self.assertGreaterEqual(g["going"], 220)
        self.assertTrue(550 <= g["two_r_plus_g"] <= 700)

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
            lay["rooms"]["corridor"]["occupancy"] = "study"   # the GF hall: party wall + partitions, no facade
        res = self.mutate(f)
        self.assertIn("corridor", next(c for c in res["checks"] if c["check"] == "window")["rooms"])

    def test_room_on_the_street_face_is_not_dark(self):
        """Negative of the above: the strip's landing cell touches the street face, so it could have a window."""
        def f(lay):
            lay["rooms"]["landing-gf"]["occupancy"] = "study"
        res = self.mutate(f)
        self.assertNotIn("landing-gf", next(c for c in res["checks"] if c["check"] == "window")["rooms"])

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
