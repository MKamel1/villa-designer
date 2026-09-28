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
        self.assertEqual([k for k, _ in items["dk-appliance-bank"]["modules"]],
                         ["fridge", "oven", "microwave"])
        result = F.check(list(items.values()), LAY)
        self.assertEqual(result["kitchen"]["status"], "pass")
        self.assertEqual(result["routes"]["status"], "pass")
        self.assertIn("1.219", result["kitchen"]["measured"]["main work aisle"])
        self.assertIn("0.340", result["kitchen"]["measured"]["dk fridge across-run landing"])
        self.assertIn("via door", result["kitchen"]["measured"]["shared fridge relationship"])

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
        self.assertEqual((vents["guest-wc"]["rate_ls"], vents["guest-wc"]["card"]), (6.0, "ukadf-sanitary-intermittent-6"))
        self.assertEqual((vents["dirty-kitchen"]["rate_ls"], vents["dirty-kitchen"]["card"]),
                         (30.0, "ukadf-kitchen-intermittent-hood-30"))
        # an extract below Approved Document F's rate fails the check
        import copy
        bad = copy.deepcopy(spec)
        next(v for v in bad["ventilation"] if v["room"] == "guest-wc")["rate_ls"] = 5.0
        self.assertTrue(any("guest-wc extract" in e for e in RS.check_wp1_spec(LAY, bad)))
        screen = next(x for x in spec["bath_fittings"] if x["id"] == "pe-bath-screen")
        self.assertAlmostEqual(screen["entry_clear"], 0.8)

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
    def test_library_and_cinema_tasks_are_carded_and_met(self):
        result = L.check(LAY)
        points = [p for p in result["tasks"] if p["what"] in ("daybed nook", "cinema desk")]
        self.assertEqual(len(points), 3)
        self.assertTrue(all(p["status"] == "pass" for p in points), points)
        self.assertEqual({p["card"] for p in points}, {"ies-res-chair-reading-200", "ies-res-desk-400"})

    def test_removed_task_lamps_fail_real_reading_and_desk_points(self):
        fixtures = [f for f in L.design(LAY) if not ((f.room == "bar-alcove" and f.kind == "WALL-READ") or
                                                      (f.room == "cinema" and f.kind == "DESK"))]
        failed = {p["what"] for p in L.check(LAY, fixtures)["tasks"] if p["status"] == "fail"}
        self.assertTrue({"daybed nook", "cinema desk"} <= failed)


if __name__ == "__main__":
    unittest.main()
