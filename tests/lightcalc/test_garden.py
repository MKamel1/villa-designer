"""Garden lighting (lane LG): every rule and check has a positive test (the design passes) and a negative one (a seeded fault is caught)."""
import math
import shutil
import tempfile
import unittest
from pathlib import Path

from archpipe.lightcalc import garden as g
from archpipe.lightcalc.sources import CARDS

L = g.layout()
BOXES = g.occluders(L)
PLANES = {p.id: p for p in g.planes(L)}


def stats_at(levels, plane_id, fixtures=g.FIXTURES, **kw):
    return g.stats(g.placements(levels, fixtures, **kw), PLANES[plane_id], BOXES)


class Cards(unittest.TestCase):
    def test_every_threshold_is_carded(self):
        for cid in ("LS-POND-EDGE-LIGHT-IES-T33.2", "SLL-T3.5-walkway", "LG-POLICY-dining-30lx", "SLL-T3.2-E3", "L6-POLICY-V12-headroom"):
            self.assertIn(cid, CARDS)
        self.assertEqual(CARDS["LS-POND-EDGE-LIGHT-IES-T33.2"].status, "sourced")
        self.assertEqual(CARDS["LG-OBTRUSIVE-GN01-CIE150-not-held"].status, "unverified")      # GN01 / CIE 150 are cited as NOT held

    def test_edge_figures_are_the_rule_values(self):
        self.assertEqual((g.EDGE_MIN_LX, g.EDGE_REC_LX), (4.0, 8.0))


class SafetyPlanes(unittest.TestCase):
    def results(self, scene, levels=None):
        lv = levels or g.SCENES[scene]["levels"]
        out = []
        for pid, pl in PLANES.items():
            if pl.kind in ("edge", "path"):
                out += g.check_plane(pl, stats_at(lv, pid), lv[pl.zone_req], scene)
        return out

    def test_every_scene_meets_every_edge_and_path_plane(self):
        for scene in g.SCENES:
            res = self.results(scene)
            self.assertEqual(len(res), 4, scene)             # 2 ponds + pit + 1 path
            self.assertTrue(all(r.status == "pass" for r in res), [r.message for r in res if r.status != "pass"])

    def test_pond_edge_recommended_8_lx_is_met_not_just_4(self):
        for pid in ("n-pond-edge-ring", "e-pond-edge-ring", "s-firepit-edge-ring"):
            self.assertGreaterEqual(stats_at(g.SCENES["summer-night-dining"]["levels"], pid)["min"], g.EDGE_REC_LX, pid)

    def test_negative_dark_pond_edge_fails(self):
        lv = dict(g.SCENES["summer-night-dining"]["levels"], **{"pond-N": 0.02})
        res = [r for r in self.results("x", lv) if "n-pond" in r.subject]
        self.assertEqual(res[0].status, "fail")
        self.assertLess(res[0].achieved, 4.0)

    def test_negative_dark_path_fails(self):
        lv = dict(g.SCENES["summer-night-dining"]["levels"], **{"path-S": 0.02})
        self.assertEqual([r.status for r in self.results("x", lv) if "path" in r.subject], ["fail"])

    def test_negative_patchy_path_fails_uniformity(self):
        one = [f for f in g.FIXTURES if f.id == "PS-2"]        # one light on a 4.6 m path: average may pass, Uo may not
        st = stats_at({"path-S": 0.5}, "s-path-door", one)
        res = g.check_plane(PLANES["s-path-door"], st, 0.5, "x")[0]
        self.assertLess(st["u0"], g.PATH_U0)
        self.assertEqual(res.status, "fail")

    def test_a_blocked_light_gives_no_light(self):
        """Occlusion works: the pit ring fixtures behind a wall add nothing."""
        wall = [(24.0, -29.8, g.G, 24.2, -29.5, g.G + 4.0, 0.4)]
        p = [q for q in g.placements({"pit": 1.0}) if q.id == "FP-1"]
        pt = PLANES["s-firepit-edge-ring"].points[0]
        self.assertGreater(g.eh(p, pt, BOXES), 0)
        self.assertTrue(g._blocked(p[0].position, (24.9, -29.55, g.G), wall))
        self.assertFalse(g._blocked(p[0].position, (24.9, -29.55, g.G), []))

    def test_ring_excludes_slivers_and_furniture(self):
        for p in PLANES["e-pond-edge-ring"].points:           # the 0.24 m strip behind the east-yard bench is not a place to stand
            self.assertFalse(20.41 <= p[0] <= 20.86 and -22.24 <= p[1] <= -20.84)
        self.assertGreater(len(PLANES["e-pond-edge-ring"].points), 100)


class Headroom(unittest.TestCase):
    def test_v12_every_safety_zone_meets_its_recommended_value_under_80_percent(self):
        lv = g.solve_levels(L)
        self.assertEqual(len(lv), 4)
        for pid, s in lv.items():
            self.assertTrue(g.check_headroom(s["level_for_target"], pid).status == "pass", pid)
            self.assertLessEqual(s["level_for_target"], g.V12_MAX_LEVEL)

    def test_negative_headroom_over_80_fails(self):
        self.assertEqual(g.check_headroom(0.85, "x").status, "fail")
        self.assertEqual(g.check_headroom(0.80, "x").status, "pass")

    def test_scene_levels_never_below_the_safety_floor_when_the_zone_is_in_use(self):
        lv = g.solve_levels(L)
        for sc in g.SCENES.values():
            for pid, s in lv.items():
                self.assertGreaterEqual(sc["levels"][s["zone"]], s["level_for_target"] - 1e-9, (pid, sc["label"]))

    def test_all_levels_at_most_80_percent(self):
        for sc in g.SCENES.values():
            self.assertLessEqual(max(sc["levels"].values()), g.V12_MAX_LEVEL)


class Dining(unittest.TestCase):
    def test_design_levels_are_inside_the_band_and_cap(self):
        for scene in ("summer-night-dining", "social-gathering"):
            lv = g.SCENES[scene]["levels"]
            res = g.check_dining(PLANES["s-dining-table"], stats_at(lv, "s-dining-table"), g.SCENES[scene]["dining_target"], scene)
            self.assertTrue(all(r.status == "pass" for r in res), [r.message for r in res])

    def test_negative_overlit_table_fails_la2_and_la1(self):
        lv = {"dining": 0.6}
        res = g.check_dining(PLANES["s-dining-table"], stats_at(lv, "s-dining-table"), 30.0, "x")
        self.assertEqual([r.criterion for r in res if r.status == "fail"], ["LA1", "LA2"])

    def test_negative_dark_table_fails_minimum(self):
        res = g.check_dining(PLANES["s-dining-table"], stats_at({"dining": 0.05}, "s-dining-table"), 30.0, "x")
        self.assertIn("fail", [r.status for r in res])


class Spill(unittest.TestCase):
    def worst(self, pls):
        res, info = g.spill(pls, BOXES)
        return {r.subject.split("/")[-1].split(" ")[0]: r for r in res}, info

    def test_design_passes_e3_post_curfew(self):
        for scene in g.SCENES:
            res, info = g.spill(g.placements(g.SCENES[scene]["levels"]), BOXES)
            self.assertTrue(all(r.status == "pass" for r in res), (scene, [r.message for r in res if r.status != "pass"]))
            self.assertLess(max(info["ev_max_by_group"].values()), 2.0)

    def test_negative_floodlight_at_the_apartment_facade_fails_ev(self):
        bad = g.Fix("BAD", "uplight", "beauty", "iku", (24.0, -26.0, 3.0), (22.8, -26.0, 4.5), "test")
        res, _ = g.spill(g.placements({"uplight": 1.0}, [bad]), BOXES)
        self.assertEqual([r.status for r in res if "Ev" in r.subject], ["fail"])

    def test_negative_uplight_missing_its_crown_fails_ulr(self):
        bad = g.Fix("BAD", "uplight", "beauty", "up-assumed", (23.5, -28.5, 0.05), (23.5, -28.5, 9.0), "straight up, no crown above")
        res, _ = g.spill(g.placements({"uplight": 1.0}, [bad]), BOXES)
        ulr = [r for r in res if r.subject.endswith("ULR")][0]
        self.assertEqual(ulr.status, "fail")
        self.assertGreater(ulr.achieved, 0.5)

    def test_uplight_aimed_into_its_crown_is_caught_by_the_crown(self):
        res, info = g.spill(g.placements(g.SCENES["social-gathering"]["levels"]), BOXES)
        self.assertEqual(info["ulr_raw"]["UP-1"] > 0.99, True)     # raw ULR of an uplight is 1 by definition
        self.assertLess(info["ulr"]["UP-1"], 0.05)                  # but its beam ends in the crape crown

    def test_walls_stop_the_light(self):
        """Every fence is 4 m: ground-floor neighbour windows get nothing even from a floodlight at full."""
        bad = g.Fix("BAD", "uplight", "beauty", "iku", (27.0, -23.0, 3.0), (27.0, -20.3, 0.0), "test")
        pls = g.placements({"uplight": 1.0}, [bad])
        low = [pt for name, pt in g.neighbour_points() if name == "east-neighbour" and pt[2] < g.G + 2]
        self.assertEqual(sum(g.eh(pls, pt, BOXES) for pt in low), 0.0)
        self.assertGreater(sum(g.eh(pls, pt, []) for pt in low), 0.0)          # without the wall the same light arrives: the wall is what stops it


class Glare(unittest.TestCase):
    def test_design_passes_in_every_scene(self):
        for scene in g.SCENES:
            gl, worst = g.check_glare(g.placements(g.SCENES[scene]["levels"]), scene)
            self.assertTrue(all(r.status == "pass" for r in gl), scene)

    def test_negative_fitting_aimed_at_the_seat_fails(self):
        bad = g.Fix("BAD", "dining", "use", "iku", (27.5, -25.4, 2.6), (24.0, -25.4, 1.2), "aimed at the west-end seat")
        gl, worst = g.check_glare(g.placements({"dining": 1.0}, [bad]), "x")
        self.assertTrue(any(r.status == "fail" for r in gl))


class Verification(unittest.TestCase):
    def test_v1_inputs(self):
        rows = {r["product"]: r for r in g.v1_inputs()}
        self.assertEqual(rows["iku"]["status"], "pass")
        self.assertLess(abs(rows["iku"]["error"]), 0.02)
        self.assertFalse(rows["up-assumed"]["verified"])

    def test_v1_negative_doubled_lumens_is_flagged(self):
        self.assertEqual({r["product"]: r for r in g.v1_inputs(lumens_scale=2.0)}["iku"]["status"], "fail")

    def test_v2_design_clean_and_negative_shift_into_the_wall(self):
        self.assertEqual(g.v2_placement(), [])
        gr = [f for f in g.FIXTURES if f.id == "GR-1"]
        self.assertTrue(any("inside a solid" in p for p in g.v2_placement(gr, shift=(0.30, 0, 0))))
        self.assertTrue(any("height" in p for p in g.v2_placement([g.Fix("X", "graze", "beauty", "iku", (26, -22, 4.2), (26, -22, 0), "t")])))

    def test_v3_design_clean_and_negative_sensor_in_the_bench(self):
        self.assertEqual(g.v3_sensors(), [])
        bench = L["seating"][0]["rect"]
        bad = g.Plane("bad", "edge", "pit", [((bench[0] + bench[2]) / 2, (bench[1] + bench[3]) / 2, g.G, 0, 0, 1)])
        self.assertEqual(len(g.v3_sensors([bad])), 1)

    def test_v8_mutations_move_the_golden_values(self):
        """A seeded error must change a plane by more than 5 %: lumens x2, a fitting 300 mm along, aim rolled 90 degrees."""
        lv = g.SCENES["summer-night-dining"]["levels"]
        base = stats_at(lv, "n-pond-edge-ring")["avg"]
        for kw in (dict(lumens_scale=2.0), dict(shift=(0.3, 0.0, 0.0)), dict(aim_roll_deg=90.0)):
            self.assertGreater(abs(stats_at(lv, "n-pond-edge-ring", **kw)["avg"] / base - 1), 0.05, kw)

    def test_hand_calculation_one_point(self):
        """Inverse-square check done by hand for the nadir point of PS-2 (Imax 815.2 cd at 2.4 m, MF 0.8): 815.2/2.4^2 x 0.8 = 113.2 lx at full."""
        ps2 = [q for q in g.placements(None) if q.id == "PS-2"]
        ps2[0] = type(ps2[0])(**{**ps2[0].__dict__, "aim": (0, 0, -1)})
        e = g.MF * g.eh(ps2, (22.9, -25.4, g.G, 0, 0, 1), BOXES)
        self.assertAlmostEqual(e, 0.8 * 815.2 / 2.4 ** 2, delta=0.02 * e)


@unittest.skipUnless(shutil.which("rtrace") or (g.RADIANCE_BIN / "rtrace").exists(), "Radiance not installed")
class RadianceCrossCheck(unittest.TestCase):
    def test_v5_direct_agrees_and_v7_converges_on_the_pit_and_path(self):
        with tempfile.TemporaryDirectory() as d:
            r = g.radiance_check(Path(d), step=4, ab=3, plane_ids=("s-firepit-edge-ring", "s-path-door"))
        for pid, v in r.items():
            self.assertLess(abs(v["direct_diff"]), 0.03, (pid, v))            # V5 direct a <-> b within 3 %
            self.assertLess(abs(v["convergence"]), 0.03, (pid, v))            # V7 ab N vs 2N

    def test_negative_a_wrong_fixture_position_breaks_agreement(self):
        """The cross-check can fail: Radiance on the true layout vs analytic on a layout shifted 300 mm does not agree to 3 %."""
        with tempfile.TemporaryDirectory() as d:
            r = g.radiance_check(Path(d), step=4, ab=1, plane_ids=("s-path-door",))
        ana_shifted = stats_at(g.SCENES[g.RENDER_SCENE]["levels"], "s-path-door", shift=(0.3, 0, 0))["avg"]
        self.assertGreater(abs(ana_shifted / r["s-path-door"]["radiance_direct_avg"] - 1), 0.03)


if __name__ == "__main__":
    unittest.main()
