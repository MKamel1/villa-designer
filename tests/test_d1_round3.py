"""Round-3 guards on the authored D1 geometry, including the round-2 lamp reproduction."""
import copy
import unittest
from dataclasses import replace

from archpipe.concept import revit_spec as RS
from archpipe.concept import villa_furnish as F
from archpipe.concept import villa_furnish3d as F3
from archpipe.concept import villa_lighting as L
from archpipe.concept import villa_r11 as R


class D1Round3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lay = R.design("D1")
        cls.items = F.layout(cls.lay)
        cls.fixtures = L.design(cls.lay)

    def test_furniture_checks_positive_and_negative_on_real_d1(self):
        good = F.check(self.items, self.lay)
        by_id_good = {item["id"]: item for item in self.items}
        self.assertEqual(by_id_good["living-sofa"].get("product"), "sf_minotti_sofa")
        self.assertAlmostEqual(by_id_good["living-coffee"]["d"], 0.45)
        self.assertEqual(by_id_good["pb-bed"].get("product"), None)
        for key in ("nook_curtain", "seating_focal", "wardrobe_capacity",
                    "under_stair_storage", "clearances", "doors", "routes"):
            self.assertEqual(good[key]["status"], "pass", (key, good[key]["problems"]))
        bad_items = copy.deepcopy(self.items)
        by_id = {item["id"]: item for item in bad_items}
        by_id["library-daybed"]["curtain"] = True
        by_id["lounge-armchair"]["rot"] = -90  # the real round-2 orientation
        by_id["pd-hang-1"]["modules"] = [("drawers", by_id["pd-hang-1"]["w"])]
        bad_items.remove(by_id["stair-flight-store"])  # real round-2 omission
        bad = F.check(bad_items, self.lay)
        for key in ("nook_curtain", "seating_focal", "wardrobe_capacity", "under_stair_storage"):
            self.assertEqual(bad[key]["status"], "fail", key)

    def test_real_island_shadow_reproduction_and_clear_relayout(self):
        self.assertFalse(L.task_beam_obstructions(self.lay, self.fixtures))
        globes = [f for f in self.fixtures if f.room == "kitchen" and f.kind == "PEN-GLOBE"]
        old = [replace(next(f for f in self.fixtures if f.room == "kitchen" and f.kind == "DLN"),
                       id="round2-DLN-%d" % number, x=x, y=-25.710)
               for number, x in enumerate((12.075, 13.075, 14.075), 1)]
        blocked = L.task_beam_obstructions(self.lay, globes + old)
        self.assertEqual(len(blocked), 3, blocked)

    def test_swing_envelope_and_lighting_targets(self):
        self.assertFalse(L.swing_envelope_problems(self.lay, self.fixtures))
        swing = next(f for f in self.fixtures if f.kind == "SWING")
        bad_swing = replace(swing, y=swing.y + 0.5)
        self.assertTrue(L.swing_envelope_problems(self.lay, [bad_swing]))
        report = L.check(self.lay, self.fixtures)
        points = {row["what"]: row for row in report["tasks"] if row["what"] in ("daybed nook", "pe-basin")}
        for row in points.values():
            self.assertEqual(row["status"], "pass")
            self.assertLessEqual(row["achieved_lx"], row["required_lx"] * 3)
        island = [row for row in report["tasks"] if row["what"].startswith("island ")]
        self.assertEqual(len(island), 6)
        self.assertTrue(all(row["status"] == "pass" for row in island))
        bad = [replace(f, extra={**f.extra, "dimmer": 1.5}) if f.room == "parents-ensuite" else f
               for f in self.fixtures]
        self.assertTrue(any("pe-basin" in p and "maximum" in p for p in L.check(self.lay, bad)["problems"]))

    def test_fitted_storage_and_bath_screen(self):
        by_id = {item["id"]: item for item in self.items}
        for name in ("stair-flight-store", "stair-landing-store", "store-shelves", "pd-hang-1", "pd-hang-2"):
            self.assertGreater(len(F3.body(by_id[name])), 3)
        spec = RS.build(self.lay)
        self.assertFalse(RS.check_wp1_spec(self.lay, spec))
        screen = next(f for f in spec["bath_fittings"] if f["id"] == "pe-bath-screen")
        self.assertEqual((screen["transmittance"], screen["ior"]), (0.91, 1.52))
        screen["ior"] = 0
        self.assertTrue(any("optical" in error for error in RS.check_wp1_spec(self.lay, spec)))


if __name__ == "__main__":
    unittest.main()
