"""Client-approved D1 changes: checked on the actual authored layout and spec."""
import copy
import unittest
from unittest.mock import patch

from archpipe.concept import revit_spec as RS
from archpipe.concept import villa_furnish as F
from archpipe.concept import villa_furnish3d as F3
from archpipe.concept import villa_lighting as L
from archpipe.concept import villa_r11 as R


LAY = R.design("D1")


class Design(unittest.TestCase):
    def test_kitchen_bank_and_aisle_pass(self):
        items = {i["id"]: i for i in F.layout(LAY)}
        self.assertNotIn("k-tall", items)
        # client option A (2026-09-28): fridge + oven bank, microwave in the island, folding counter kept
        self.assertEqual([k for k, _ in items["dk-appliance-bank"]["modules"]], ["fridge", "oven"])
        self.assertIn("microwave", [k for k, _ in items["k-island"]["modules"]])
        self.assertEqual([k for k, _ in items["k-island"]["modules"] if k in ("hob", "single-induction")],
                         ["single-induction"])
        self.assertEqual([k for k, _ in items["dk-run"]["modules"] if k == "hob"], ["hob"])
        self.assertIn("dk-fold", items)
        result = F.check(list(items.values()), LAY)
        self.assertEqual(result["kitchen"]["status"], "pass")
        self.assertEqual(result["routes"]["status"], "pass")
        self.assertIn("1.219", result["kitchen"]["measured"]["main work aisle"])
        self.assertIn("0.299", result["kitchen"]["measured"]["dk fridge across-run landing"])
        self.assertIn("via door", result["kitchen"]["measured"]["shared fridge relationship"])
        self.assertIn("0.60 / 1.50", result["kitchen"]["measured"]["k-island single-induction"])

    def test_guest_open_shower_clearances_and_route(self):
        items = {i["id"]: i for i in F.layout(LAY)}
        shower = items["gwc-shower"]
        wet = F.footprint(shower)
        basin = F.footprint(items["gwc-basin"])
        wc = F.footprint(items["gwc-wc"])
        self.assertEqual((shower["enclosure"], shower["drain"]), ("none", "linear"))
        self.assertGreaterEqual(round(wet[3] - wet[1], 3), 1.219)  # card nkba-shower-clear-floor-762
        self.assertGreaterEqual(round(wet[2] - wet[0], 3), 0.762)
        self.assertGreaterEqual(round(wet[1] - basin[3], 3), 0.150)
        self.assertGreaterEqual(round(wc[1] - wet[3], 3), 0.130)
        self.assertEqual(F.check(list(items.values()), LAY)["routes"]["status"], "pass")

    def test_old_tall_wall_and_narrow_aisle_fail_on_this_layout(self):
        items = F.layout(LAY)
        old = F.against("k-tall", F.clear_rect(LAY, "kitchen-island"), "y0", 11.197, "base_run",
                        w=2.25, d=0.6, h=2.3, modules=[("counter", .45), ("fridge", .6),
                                                       ("oven", .6), ("counter", .6)], why="old")
        old.update(room="kitchen-island", level="B")
        self.assertTrue(any("hall-facing tall appliances" in p for p in
                            F.check(items + [old], LAY)["kitchen"]["problems"]))
        moved = copy.deepcopy(items)
        next(i for i in moved if i["id"] == "k-island")["cy"] += 0.05
        self.assertTrue(any("main work aisle" in p for p in F.check(moved, LAY)["kitchen"]["problems"]))
        no_landing = copy.deepcopy(items)
        modules = next(i for i in no_landing if i["id"] == "dk-run")["modules"]
        modules[-1] = ("washer", 0.457)
        modules[3] = ("washer", 0.61)
        self.assertTrue(any("dk-appliance-bank fridge has no 381 mm landing" in p
                            for p in F.check(no_landing, LAY)["kitchen"]["problems"]))

    def test_library_nook_is_reached_and_old_sofa_position_blocks_it(self):
        items = F.layout(LAY)
        ids = {i["id"]: i for i in items}
        self.assertTrue({"library-cabinet-left", "library-daybed", "library-cabinet-right",
                         "library-end-panel"} <= ids.keys())
        self.assertEqual(ids["library-daybed"]["mattress"], (2.0, 0.9))
        self.assertEqual(ids["library-daybed"]["nook_top"], 2.1)
        self.assertEqual(F.check(items, LAY)["routes"]["status"], "pass")
        bad = copy.deepcopy(items)
        next(i for i in bad if i["id"] == "living-sofa")["cy"] -= 0.6
        self.assertTrue(any("library-daybed" in p for p in F.check(bad, LAY)["routes"]["problems"]))

    def test_cinema_desk_has_two_chairs_and_full_standing_height(self):
        items = F.layout(LAY)
        desk = next(i for i in items if i["id"] == "cinema-desk")
        self.assertEqual(desk["chairs"], 2)
        self.assertEqual(len(F3.extras(desk)), 2)
        self.assertIn("2.307", F.check(items, LAY)["clearances"]["measured"]["cinema desk soffit"])
        bad = copy.deepcopy(items)
        next(i for i in bad if i["id"] == "cinema-desk")["cx"] -= 0.5
        self.assertTrue(any("cinema desk soffit" in p for p in F.check(bad, LAY)["clearances"]["problems"]))

    def test_built_cinema_chairs_can_close_the_store_route(self):
        # Moving the actual desk and its two built chairs into the passage reproduces a missed 914 mm route.
        items = copy.deepcopy(F.layout(LAY))
        next(i for i in items if i["id"] == "cinema-desk")["cy"] = -22.3
        spec = RS.build(LAY)
        basement = [i for i in items if i["level"] == "B"]
        with_chairs = [p for p, _ in F.route_problems(LAY, spec, basement, "B")]
        self.assertTrue(any("door cinema/store-ramp" in p for p in with_chairs))
        with patch.object(F, "_cinema_chair_rects", return_value=[]):
            without_chairs = [p for p, _ in F.route_problems(LAY, spec, basement, "B")]
        self.assertFalse(any("door cinema/store-ramp" in p for p in without_chairs))


class RevitInputs(unittest.TestCase):
    def test_door_hatch_and_pocket_wall_pass(self):
        spec = RS.build(LAY)
        self.assertEqual(RS.check_wp1_spec(LAY, spec), [])
        door = next(d for d in spec["doors"] if set(d["rooms"]) == {"kitchen", "dirty-kitchen"})
        hatch = spec["hatches"][0]
        self.assertEqual(door["width"], 1.2)
        self.assertEqual(door["leaf_count"], 3)
        self.assertGreaterEqual(door["pocket_span"][0] - hatch["x1"], 0.1)
        self.assertEqual(hatch["sill"], 1.0)
        self.assertEqual(hatch["closure"], "roll-up-shutter")

    def test_low_hatch_and_pocket_collision_fail_on_real_spec(self):
        spec = RS.build(LAY)
        spec["hatches"][0]["sill"] = 0.85
        self.assertTrue(any("upstand" in p for p in RS.check_wp1_spec(LAY, spec)))
        spec = RS.build(LAY)
        spec["hatches"][0]["x1"] = spec["doors"][next(i for i, d in enumerate(spec["doors"])
                                                              if set(d["rooms"]) == {"kitchen", "dirty-kitchen"})]["pocket_span"][0]
        self.assertTrue(any("pocket" in p for p in RS.check_wp1_spec(LAY, spec)))
        spec = RS.build(LAY)
        spec["hatches"][0]["x0"] = 11.4
        self.assertTrue(any("structural column" in p for p in RS.check_wp1_spec(LAY, spec)))
        spec = RS.build(LAY)
        spec["pocket_buildouts"][0]["thickness"] = 0.1
        self.assertTrue(any("wall buildout" in p for p in RS.check_wp1_spec(LAY, spec)))
        spec = RS.build(LAY)
        door = next(d for d in spec["doors"] if set(d["rooms"]) == {"kitchen", "dirty-kitchen"})
        door["width"] = 0.8
        self.assertTrue(any("0.914 m route body" in p for p in RS.check_wp1_spec(LAY, spec)))

    def test_bath_glass_stair_glass_and_vent_placeholders_pass(self):
        spec = RS.build(LAY)
        self.assertEqual(RS.check_wp1_spec(LAY, spec), [])
        self.assertEqual({v["room"] for v in spec["ventilation"]}, {"guest-wc", "dirty-kitchen"})
        vents = {v["room"]: v for v in spec["ventilation"]}
        self.assertEqual((vents["guest-wc"]["rate_ls"], vents["guest-wc"]["card"]),
                         (15.0, "ukadf-bathroom-intermittent-15"))
        self.assertEqual(RS.sanitary_extract_requirement(F.layout(LAY, products=False), "guest-wc"),
                         ("ukadf-bathroom-intermittent-15", 15.0))
        bare = [i for i in F.layout(LAY, products=False) if i["id"] != "gwc-shower"]
        self.assertEqual(RS.sanitary_extract_requirement(bare, "guest-wc"),
                         ("ukadf-sanitary-intermittent-6", 6.0))
        self.assertEqual((vents["dirty-kitchen"]["rate_ls"], vents["dirty-kitchen"]["card"]),
                         (30.0, "ukadf-kitchen-intermittent-hood-30"))
        wet = next(x for x in spec["bath_fittings"] if x["id"] == "gwc-linear-drain")
        self.assertEqual((wet["upstand_m"], wet["enclosure"], wet["kind"]), (0.0, "none", "linear-drain"))
        # an extract below Approved Document F's rate fails the check
        import copy
        bad = copy.deepcopy(spec)
        stale = next(v for v in bad["ventilation"] if v["room"] == "guest-wc")
        stale["rate_ls"], stale["card"] = 6.0, "ukadf-sanitary-intermittent-6"
        self.assertTrue(any("guest-wc extract" in e for e in RS.check_wp1_spec(LAY, bad)))
        screen = next(x for x in spec["bath_fittings"] if x["id"] == "pe-bath-screen")
        self.assertAlmostEqual(screen["entry_clear"], 0.8)

    def test_dirty_kitchen_duct_rises_from_the_hood_chimney(self):
        # Round-2 draft v17: the spec fan sat at x 13.30 while the hood (over dk-run's hob) is at x 13.827, so the
        # rendered duct hung in the air beside the chimney. The fan must sit inside the chimney's 0.23 x 0.16 m box.
        vent = next(v for v in RS.build(LAY)["ventilation"] if v["room"] == "dirty-kitchen")
        run = next(i for i in F.layout(LAY) if i["id"] == "dk-run")
        from archpipe.concept import villa_furniture_detail as FD
        hob = next((a, b) for k, a, b in F3._local_modules(run) if k == "hob")
        hx = FD.to_world_point(run, sum(hob) / 2, 0, 0, 0)[0]
        wall_y = F.clear_rect(LAY, "dirty-kitchen")[3]   # finished face the chimney stands against
        self.assertLessEqual(abs(vent["fan"][0] - hx), 0.115)
        self.assertTrue(wall_y - 0.16 <= vent["fan"][1] <= wall_y)
        self.assertGreater(abs(13.3 - hx), 0.115, "the draft's fan x (the real defect) lies outside the chimney")

    def test_bath_entry_steel_rail_and_dead_duct_fail_on_real_spec(self):
        spec = RS.build(LAY)
        next(x for x in spec["bath_fittings"] if x["id"] == "pe-bath-screen")["x1"] += 0.1
        self.assertTrue(any("bath entry" in p for p in RS.check_wp1_spec(LAY, spec)))
        spec = RS.build(LAY)
        next(x for x in spec["balustrades"] if x["id"] == "stair-open-glass")["material"] = "steel bars"
        self.assertTrue(any("frameless glass" in p for p in RS.check_wp1_spec(LAY, spec)))
        spec = RS.build(LAY)
        spec["ventilation"][0]["duct_route"][-1] = spec["ventilation"][0]["fan"]
        self.assertTrue(any("external wall" in p for p in RS.check_wp1_spec(LAY, spec)))


class Lighting(unittest.TestCase):
    def test_fresh_interpreter_matches_scene_bound_products(self):
        import os
        import subprocess
        import sys
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(root / "src")
        script = ("import json, sys\n"
                  "from archpipe.concept import villa_lighting as L\n"
                  "from archpipe.concept import villa_r11 as R\n"
                  "if len(sys.argv) > 1:\n"
                  " from archpipe.concept import villa_render as VR\n"
                  " VR.build()\n"
                  "row = next(p for p in L.check(R.design('D1'))['tasks'] if p['what'] == 'single induction zone')\n"
                  "print(json.dumps({'lux': row['achieved_lx'], 'product': L.PRODUCTS.get('DLN', {}).get('code')}))\n")
        def measure(*args):
            run = subprocess.run([sys.executable, "-c", script, *args], cwd=root, env=env,
                                 text=True, capture_output=True, check=True)
            import json
            return json.loads(run.stdout.splitlines()[-1])

        self.assertEqual(measure(), measure("scene"))

    def test_single_induction_task_and_prep_points(self):
        result = L.check(LAY)
        cooking = [p for p in result["tasks"] if p["what"] == "single induction zone"]
        self.assertEqual(len(cooking), 1)
        self.assertEqual((cooking[0]["achieved_lx"], cooking[0]["required_lx"], cooking[0]["status"]),
                         (1156, 300, "pass"))  # bound iGuzzini LSEVO-AAIIA6, not generic photometry
        self.assertEqual(len([p for p in result["tasks"] if p["what"] == "island prep side" and
                              p["status"] == "pass"]), 3)

    def test_library_and_cinema_tasks_are_carded_and_met(self):
        result = L.check(LAY)
        points = [p for p in result["tasks"] if p["what"] in ("daybed nook", "cinema desk")]
        self.assertEqual(len(points), 3)
        self.assertTrue(all(p["status"] == "pass" for p in points), points)
        self.assertEqual({p["card"] for p in points}, {"ies-res-chair-reading-200", "ies-res-desk-400"})

    def test_removed_task_lamps_fail_real_reading_and_desk_points(self):
        fixtures = [f for f in L.design(LAY) if not ((f.room == "bar-alcove" and f.kind in ("SWING", "DLN")) or
                                                      (f.room == "cinema" and f.kind == "DESK"))]
        failed = {p["what"] for p in L.check(LAY, fixtures)["tasks"] if p["status"] == "fail"}
        self.assertTrue({"daybed nook", "cinema desk"} <= failed)


if __name__ == "__main__":
    unittest.main()
