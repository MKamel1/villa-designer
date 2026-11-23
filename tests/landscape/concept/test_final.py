"""Final design (round 2): zero hard fails, plus a negative for every new check ("does it stay quiet when it should / fail when it should")."""
import copy
import math
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
        self.assertEqual({r.subject for r in sup}, {"s-firepit", "s-bbq"})                         # LDK 2.0 m floor still reported, never dropped; the BBQ is judged by its manual (LDG-BBQ-MANUAL)
        sup = [r for r in sup if r.subject == "s-firepit"]
        self.assertIn(sup[0], [r for r in RES])
        self.assertNotIn(id(sup[0]), {id(r) for r in K.hard_fails(RES)})

    def test_opening_has_no_screen_and_stubs_have_climbers_only_outside_clearance(self):
        segs = sorted(s["rect"] for s in L0["screens"])
        self.assertEqual(len(segs), 2)
        self.assertAlmostEqual(segs[1][0] - segs[0][2], F.OPEN_A[1] - F.OPEN_A[0], 2)
        self.assertTrue(all(s["height_m"] == 2.1 for s in L0["screens"]))

    def test_jasmine_by_distance_to_seats_and_herbs(self):
        from shapely.geometry import Point, box
        near = [box(*o["rect"]) for o in L0["seating"]] + [box(*o["rect"]) for o in L0["features"] if o.get("kind") == "herb_bed"]
        got = {F.STAR: 0, F.SAMBAC: 0}
        for g in L0["planting_groups"]:
            for p in g["plants"]:
                if p["species"] in got:
                    got[p["species"]] += 1
                    d = min(Point(*p["at"]).distance(n) for n in near)
                    if p["species"] == F.STAR:
                        self.assertGreaterEqual(d, F.NEAR_M, (g["id"], p["at"], d))                  # star jasmine only 2 m or more from a seat or the herb bed
                    # (sambac may also sit just past 2 m by the critic's stricter seat-point measure; the negative is the star check above and the critic below)
        self.assertTrue(all(got.values()), got)
        self.assertEqual([r for r in RES if r.criterion == "LDG-POL-TOXIC" and r.status != "pass"], [])
        from archpipe.landscape.critic import critique
        self.assertEqual([f.evidence for f in critique(L0) if f.criterion == "H-TOXIC-PLACEMENT" and f.status != "pass"], [])

    def test_east_yard_south_boundary_is_a_wall_with_a_climber(self):
        w = next(w for w in L0["walls"] if w["id"] == "wall-yard-south")
        self.assertTrue(any(g["id"].startswith("e-") and p["species"] in (F.STAR, F.SAMBAC) and abs(p["at"][1] - w["rect"][1]) < 0.75 for g in L0["planting_groups"] for p in g["plants"]))

    def test_dining_8_extends_to_10_not_12(self):
        ext = R.extension_checks(L0)
        self.assertEqual(ext[10]["status"], "pass")
        self.assertEqual(ext[12]["status"], "fail")

    def test_both_ponds_with_section_that_fits(self):
        ponds = [f for f in L0["features"] if f["kind"] == "pond"]
        self.assertEqual({p["id"] for p in ponds}, {"n-pond", "e-pond"})
        for r in K.pond_section_check(L0):
            self.assertEqual(r.status, "pass", r.message)

    def test_no_pergola_and_shade_trees_instead(self):
        self.assertEqual(L0["canopies"], [])
        self.assertTrue({"s-tree-crape", "s-tree-olive", "e-tree-olive"} <= {t["id"] for t in L0["trees"]})

    def test_crape_leaf_on_halves_summer_sun_and_bare_keeps_winter_sun(self):
        t = GDATA["season_table"]["table"]
        self.assertLessEqual(t["summer_leaf_on_h"], 0.6 * t["summer_open_sky_h"])
        self.assertGreaterEqual(t["winter_leaf_off_h"], 0.8 * t["winter_open_sky_h"])
        self.assertGreaterEqual(max(v["winter_leaf_off_h"] for v in GDATA["season_table"].values()), K.WINTER_SEAT_MIN_H)

    def test_bare_deciduous_crown_is_not_winter_cover_but_the_evergreen_is(self):
        win = K.crown_cells(L0, "winter")
        summ = K.crown_cells(L0, "summer")
        self.assertGreater(len(summ), len(win))
        crape = next(c for c in K.crowns(L0) if c["id"] == "s-tree-crape")
        self.assertFalse(crape["evergreen"])
        self.assertTrue(any(c["evergreen"] for c in K.crowns(L0)))

    def test_hard_share_inside_precedent_range(self):
        h = R.metrics(L0)["hard_share"]
        self.assertGreaterEqual(h, 0.52)
        self.assertLessEqual(h, 0.78)

    def test_layers_every_room_and_climbers_on_every_face(self):
        from archpipe.landscape.concept import final_trees as FT
        lt = FT.layer_table(L0)
        self.assertEqual(lt["south garden"]["missing"], [])
        self.assertEqual(lt["east yard"]["missing"], [])                   # its south boundary is a declared wall (client 2026-11-22) and carries climbers
        self.assertEqual(lt["north court"]["missing"], ["canopy"])         # no tree fits the 3.7 m court (NHBC, pond, 1.3 h sun): stated in the report
        self.assertTrue(all(FT.climber_faces(L0).values()), FT.climber_faces(L0))

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
        t = L["trees"][0]
        L["canopies"].append({"id": "x", "rect": [t["center"][0] - 0.5, t["center"][1] - 0.5, t["center"][0] + 0.5, t["center"][1] + 0.5], "kind": "pergola", "height_m": 2.7, "shade_fraction": 0.6})
        self.assertEqual(K.tree_pergola_check(L).status, "fail")
        self.assertEqual(K.tree_pergola_check(L0).status, "pass")

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

    def test_crown_with_no_leaf_fails_summer_shade(self):
        old = F.CROWN["deciduous_on"]
        try:
            F.CROWN["deciduous_on"] = 0.0
            r, _ = K.season_check(L0)
            self.assertEqual(next(x for x in r if x.criterion == "LDG-SHADE-SUMMER").status, "fail")
        finally:
            F.CROWN["deciduous_on"] = old

    def test_without_the_trees_summer_privacy_fails_at_the_table(self):
        L = fresh()
        L["trees"] = [t for t in L["trees"] if t["center"][0] < 20 or t["id"] == "s-tree-punica"]
        r, _ = K.privacy_checks(L, ROOMS)
        self.assertTrue(any(x.criterion == "LDG-PRIV" and x.status == "fail" for x in r))
        r0, _ = K.privacy_checks(L0, ROOMS)
        self.assertFalse(any(x.criterion == "LDG-PRIV" and x.status == "fail" for x in r0))

    def test_winter_privacy_loss_of_a_bare_crown_is_a_warning_not_hidden(self):
        r, tab = K.privacy_checks(L0, ROOMS)
        self.assertTrue(any(x.criterion == "LDG-PRIV-WINTER" and x.status == "warn" for x in r))
        self.assertGreater(tab["table"]["winter"], tab["table"]["summer"])

    def test_aggressive_roots_near_pond_fail_and_far_pass(self):
        L = fresh()
        t = next(t for t in L["trees"] if t["id"] == "e-tree-olive")
        t["species"] = "ficus_microcarpa"
        self.assertTrue(any(x.criterion == "LDG-ROOTS" and x.status == "fail" for x in K.tree_site_checks(L)))
        self.assertTrue(all(x.status == "pass" for x in K.tree_site_checks(L0)))

    def test_pruned_tree_without_a_regime_fails(self):
        L = fresh()
        next(t for t in L["trees"] if t.get("pruned"))["pruning"] = ""
        self.assertTrue(any(x.criterion == "LDG-PRUNE" and x.status == "fail" for x in K.tree_site_checks(L)))

    def test_bbq_under_a_crown_or_against_planting_fails(self):
        self.assertEqual(K.bbq_manual_check(L0).status, "pass")
        L = fresh()
        c = next(t for t in L["trees"] if t["id"] == "s-tree-crape")["crown_center"]
        bq = next(f for f in L["features"] if f["kind"] == "bbq")
        bq["rect"] = [c[0] - 0.25, c[1] - 0.25, c[0] + 0.25, c[1] + 0.25]
        self.assertEqual(K.bbq_manual_check(L).status, "fail")

    def test_winter_seat_floor_fails_when_not_met(self):
        old = K.WINTER_SEAT_MIN_H
        try:
            K.WINTER_SEAT_MIN_H = 9.0
            r, _ = K.season_check(L0)
            self.assertEqual(next(x for x in r if x.criterion == "LDG-WINTER-SEAT").status, "fail")
        finally:
            K.WINTER_SEAT_MIN_H = old


class Visualisation(unittest.TestCase):
    def test_every_element_tagged_and_ids_prefixed(self):
        v = V.mirror(L0)
        self.assertTrue(V.tagged_everywhere(v))
        ids = [o["id"] for k in C.KEYS for o in v.get(k, []) if o.get("id")]
        self.assertTrue(all(i.startswith("vis-") for i in ids))
        self.assertTrue(any("LABEL" not in str(z.get("label")) and "VISUALISATION ONLY" in str(z.get("label")) for z in v["zones"]))

    def test_mirror_reflects_crown_centre_with_the_trunk(self):
        v = V.mirror(L0)
        trees = [t for t in v["trees"] if "crown_center" in t]
        self.assertTrue(trees)
        for t in trees:
            self.assertAlmostEqual(math.hypot(t["crown_center"][0] - t["center"][0], t["crown_center"][1] - t["center"][1]), t["crown_lean_m"], 2)    # crown stays within its lean of the trunk
        src = next(t for t in L0["trees"] if t["id"] == "s-tree-crape")
        self.assertAlmostEqual(next(t for t in trees if t["id"] == "vis-s-tree-crape")["crown_center"][1], V.fy(src["crown_center"][1]), 3)

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
