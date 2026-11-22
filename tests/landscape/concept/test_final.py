"""Final design (round 2): zero hard fails, plus a negative for every new check ("does it stay quiet when it should / fail when it should")."""
import copy
import unittest

from archpipe.landscape.concept import final as F, final_checks as K, final_fire as FF, final_vis as V, ty_core as C, ty_run as R

L0 = F.build()
ROOMS = R.seat_rooms(L0)
COVERS = [c["rect"] for c in L0["canopies"]]
RES, SEEN, GDATA = K.evaluate_all(L0, ROOMS, COVERS)


def fresh():
    return copy.deepcopy(L0)


class Design(unittest.TestCase):
    def test_zero_hard_fails(self):
        self.assertEqual([(r.criterion, r.subject) for r in K.hard_fails(RES)], [])

    def test_fire_pit_is_on_the_west_line_and_manual_replaces_floor_visibly(self):
        pit = next(f for f in L0["features"] if f["kind"] == "firepit")
        self.assertAlmostEqual(pit["center"][1], -29.916, 3)
        sup = K.superseded(RES)
        self.assertEqual(len(sup), 1)                         # LDK 2.0 m floor still reported, never dropped
        self.assertEqual(sup[0].subject, "s-firepit")
        self.assertIn(sup[0], [r for r in RES])
        self.assertNotIn(id(sup[0]), {id(r) for r in K.hard_fails(RES)})

    def test_opening_has_no_screen_and_stubs_have_climbers_only_outside_clearance(self):
        segs = sorted(s["rect"] for s in L0["screens"])
        self.assertEqual(len(segs), 2)
        self.assertAlmostEqual(segs[1][0] - segs[0][2], F.OPEN_A[1] - F.OPEN_A[0], 2)
        self.assertTrue(all(s["height_m"] == 2.1 for s in L0["screens"]))

    def test_dining_8_extends_to_10_not_12(self):
        ext = R.extension_checks(L0)
        self.assertEqual(ext[10]["status"], "pass")
        self.assertEqual(ext[12]["status"], "fail")

    def test_both_ponds_with_section_that_fits(self):
        ponds = [f for f in L0["features"] if f["kind"] == "pond"]
        self.assertEqual({p["id"] for p in ponds}, {"n-pond", "e-pond"})
        for r in K.pond_section_check(L0):
            self.assertEqual(r.status, "pass", r.message)

    def test_grape_summer_shade_winter_unchanged(self):
        self.assertLessEqual(GDATA["summer"]["leafed"], 0.5 * GDATA["summer"]["open"])
        self.assertGreaterEqual(GDATA["winter"]["bare"], 0.8 * GDATA["winter"]["open"])

    def test_wind_summer_evening_runs_west_and_our_seats_are_upwind(self):
        tw, per, mir = K.wind_check(L0)
        self.assertGreater(tw["summer-evening-17-20 (Jun-Aug)"][0], 90.0)
        k = "summer-evening-17-20 (Jun-Aug)"
        self.assertLess(per["s-dining-table"][k], 10.0)         # our table is east of the pit: upwind
        self.assertGreater(mir[k], per["s-dining-table"][k])     # the sister seat is downwind

    def test_build_lane_finds_no_clip_gap_or_warning(self):
        from archpipe.landscape.build import build, checks
        sc = build.build_scene(L0, age=3)
        self.assertEqual(sc.warnings, [])
        self.assertEqual([o.id for o in sc.objects if o.id.startswith("ld-ground")], [])
        for st in ("closed", "open"):
            self.assertEqual([f for f in checks.run_all(sc, st) if f["status"] == "fail"], [])


class Negatives(unittest.TestCase):
    def test_duplicate_id_fails(self):
        L = fresh()
        L["paved_areas"].append(dict(L["paved_areas"][0]))
        self.assertEqual(K.id_check(L).status, "fail")
        self.assertEqual(K.id_check(L0).status, "pass")

    def test_missing_surface_fails(self):
        L = fresh()
        L["paved_areas"] = [a for a in L["paved_areas"] if not a["id"].startswith("n-")]
        self.assertEqual(K.surface_check(L).status, "fail")

    def test_dining_zone_swallowing_the_rear_bench_fails(self):
        L = fresh()
        z = next(z for z in L["zones"] if z["id"] == "s-dining")
        z["rect"] = [22.597, -29.216, 28.307, -23.216]          # the round-1 mistake: dining zone over the whole depth
        self.assertEqual(K.zone_check(L).status, "fail")
        self.assertEqual(K.zone_check(L0).status, "pass")

    def test_gravel_zone_over_paving_fails(self):
        L = fresh()
        z = next(z for z in L["zones"] if z["id"] == "s-dining")
        z["surface"] = "gravel"
        self.assertEqual(K.gravel_check(L).status, "fail")

    def test_tree_inside_pergola_fails(self):
        L = fresh()
        L["trees"][0]["center"] = [(L["canopies"][1]["rect"][0] + L["canopies"][1]["rect"][2]) / 2, (L["canopies"][1]["rect"][1] + L["canopies"][1]["rect"][3]) / 2]
        self.assertEqual(K.tree_pergola_check(L).status, "fail")

    def test_plant_inside_solid_fails(self):
        L = fresh()
        pot = next(o for o in L["obstacles"] if o["id"].startswith("pot"))
        cx, cy = (pot["rect"][0] + pot["rect"][2]) / 2, (pot["rect"][1] + pot["rect"][3]) / 2
        L["planting_groups"][0]["plants"].append({"species": "salvia_leucantha", "at": [cx, cy], "spread_m": 0.5, "form": "shrub"})
        self.assertEqual(K.plant_solid_check(L).status, "fail")

    def test_pot_near_fence_fails(self):
        L = fresh()
        pot = next(o for o in L["obstacles"] if o["id"].startswith("pot"))
        pot["rect"] = [28.0, -25.3, 28.6, -24.7]               # against the rear fence (LDB finding: 0.31 m)
        self.assertEqual(K.pot_check(L).status, "fail")

    def test_planting_inside_fire_clearance_fails(self):
        L = fresh()
        pit = next(f for f in L["features"] if f["kind"] == "firepit")
        cx, cy = pit["center"]
        L["planting_groups"].append({"id": "x-bed", "rect": [cx + 0.3, cy + 0.5, cx + 0.7, cy + 0.9], "plants": [], "role": "strip", "over_structure": False})
        self.assertEqual(K.fire_manual_check(L)[0].status, "fail")
        self.assertEqual(K.fire_manual_check(L0)[0].status, "pass")

    def test_pergola_over_pit_fails_overhead(self):
        L = fresh()
        pit = next(f for f in L["features"] if f["kind"] == "firepit")
        cx, cy = pit["center"]
        L["canopies"].append({"id": "x", "rect": [cx - 1, cy - 1, cx + 1, cy + 1], "kind": "pergola", "height_m": 2.0, "shade_fraction": 0.6})      # underside 1.7 m: inside the 2.0 m overhead clearance
        self.assertEqual(K.fire_manual_check(L)[1].status, "fail")

    def test_pond_too_narrow_for_its_section_fails(self):
        L = fresh()
        p = next(f for f in L["features"] if f["kind"] == "pond")
        p["width_m"] = 1.0
        self.assertTrue(any(r.status == "fail" for r in K.pond_section_check(L)))

    def test_vine_with_no_summer_leaf_fails_season_check(self):
        old = F.GRAPE["summer_density"]
        try:
            F.GRAPE["summer_density"] = 0.0
            r, _ = K.grape_check(L0)
            self.assertEqual(r.status, "fail")
        finally:
            F.GRAPE["summer_density"] = old


class Visualisation(unittest.TestCase):
    def test_every_element_tagged_and_ids_prefixed(self):
        v = V.mirror(L0)
        self.assertTrue(V.tagged_everywhere(v))
        ids = [o["id"] for k in C.KEYS for o in v.get(k, []) if o.get("id")]
        self.assertTrue(all(i.startswith("vis-") for i in ids))
        self.assertTrue(any("LABEL" not in str(z.get("label")) and "VISUALISATION ONLY" in str(z.get("label")) for z in v["zones"]))

    def test_mirror_is_a_reflection_about_the_west_line(self):
        v = V.mirror(L0)
        t0, t1 = L0["tables"][0], v["tables"][0]
        self.assertAlmostEqual(t0["center"][1] + t1["center"][1], 2 * V.LINE_Y, 3)
        self.assertEqual(t0["center"][0], t1["center"][0])

    def test_design_layout_is_clean_and_a_leak_is_caught(self):
        V.assert_excluded(L0)
        L = fresh()
        L["tables"].append(V.mirror(L0)["tables"][0])
        with self.assertRaises(AssertionError):
            V.assert_excluded(L)

    def test_untagged_vis_element_detected(self):
        v = V.mirror(L0)
        v["seating"][0].pop("visualisation_only")
        self.assertFalse(V.tagged_everywhere(v))

    def test_quantities_do_not_change_with_the_vis_file(self):
        m = V.merge_for_view(L0, V.mirror(L0))
        self.assertGreater(len(m["tables"]), len(L0["tables"]))
        self.assertEqual(len(L0["tables"]), 1)                  # merge_for_view copies; the design layout is untouched
        self.assertTrue(R.seats(L0)["dining"] == 8)


class FireProducts(unittest.TestCase):
    def test_every_quote_is_in_its_manual(self):
        for pid, q in FF.quotes_ok().items():
            self.assertTrue(all(q.values()), (pid, q))

    def test_design_clearances_cover_every_shortlisted_manual(self):
        self.assertGreaterEqual(round(F.FIRE_SIDE_M * 1000), FF.SIDE_MM)
        self.assertGreaterEqual(round(F.FIRE_OVER_M * 1000), FF.OVER_MM)

    def test_no_product_claims_a_cover_rating(self):
        self.assertTrue(all("none stated" in p["cover"] for p in FF.PRODUCTS))


if __name__ == "__main__":
    unittest.main()
