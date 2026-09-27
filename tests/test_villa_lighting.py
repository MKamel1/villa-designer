"""D1 lighting (Phase 3): the client's rules, the cards, and checks that fail on real mistakes."""
import copy
import unittest

from archpipe import photometry as ph
from archpipe.concept import villa_furnish as F
from archpipe.concept import villa_lighting as VL
from archpipe.concept import villa_r11 as R

LAY = R.design("D1")
FX = VL.design(LAY)


class ClientRules(unittest.TestCase):
    def test_general_spots_are_flush(self):
        # client 2026-09-27: general-purpose spots are flush (recessed trimless, in the ceiling plane)
        for f in FX:
            if f.layer == "ambient":
                self.assertEqual(VL.KINDS[f.kind]["mount"], "recessed", f.id)
                self.assertAlmostEqual(f.z, VL.ceiling_z(f.level, f.x, f.room), places=3, msg=f.id)

    def test_pendants_are_task_or_centrepiece_only(self):
        for f in FX:
            if VL.KINDS[f.kind]["mount"] == "pendant":
                self.assertIn(f.layer, ("task", "decorative"), f.id)

    def test_questionnaire_features_are_all_there(self):
        kinds = {(f.kind, f.room) for f in FX}
        self.assertIn(("PEN-GLOBE", "kitchen"), kinds)             # pendant over the island
        self.assertIn(("PEN-LIN", "dining"), kinds)                # pendant over the dining table
        self.assertTrue(any(k == "COVE" for k, _ in kinds))       # cove / indirect ceiling light
        self.assertTrue(any(k == "BACK" for k, _ in kinds))       # backlit shelves
        self.assertTrue(any(k == "WW" for k, _ in kinds))         # wall washers
        self.assertTrue(any(k == "STEP" for k, _ in kinds))       # stair step lights
        self.assertTrue(any(k == "PATH" for k, _ in kinds))       # low path lights to the bathrooms
        self.assertTrue({"kids-a", "kids-b"} <= {r for k, r in kinds if k == "NL"})   # kids' night lights


class Cards(unittest.TestCase):
    def test_pendants_hang_762_above_the_island_and_the_table(self):
        it = {i["id"]: i for i in F.layout(LAY)}
        for f in FX:
            if f.kind == "PEN-GLOBE" and f.room == "kitchen":
                bottom = f.z - 0.0                                  # z is the globe's lowest point + r
                self.assertAlmostEqual(f.z - (VL.LEVEL_Z["B"] + it["k-island"]["h"]), 0.762 + 0.15, places=3)
            if f.kind == "PEN-LIN":
                self.assertAlmostEqual(f.z - (VL.LEVEL_Z["B"] + it["dining-table"]["h"]), 0.762, places=3)

    def test_vanity_sconces_914_to_1016_apart(self):
        by = {}
        for f in FX:
            if f.kind == "SCONCE":
                by.setdefault(f.room, []).append(f)
        self.assertEqual(set(by), {"guest-wc", "family-bath", "parents-ensuite"})
        for room, (a, b) in by.items():
            d = ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5
            self.assertTrue(0.914 <= d <= 1.016, (room, d))

    def test_every_task_and_room_target_is_met(self):
        res = VL.check(LAY, FX)
        self.assertEqual([t for t in res["tasks"] if t["status"] != "pass"], [])
        self.assertEqual([r for r in res["rooms"] if r["status"] == "fail"], [])


class ChecksFailOnRealMistakes(unittest.TestCase):
    def test_island_without_its_task_lights_fails_prep(self):
        fx = [f for f in FX if not (f.kind == "DLN" and f.room == "kitchen")]
        res = VL.check(LAY, fx)
        self.assertTrue(any(t["card"] == "ies-res-kitchen-prep-500" and t["status"] == "fail" for t in res["tasks"]))

    def test_basins_lit_only_by_sconces_fail_grooming(self):
        # the first draft: sconces alone gave 87-142 lx on the counter
        fx = [f for f in FX if not (f.kind == "DLN" and f.card == "ies-res-vanity-grooming-300")]
        res = VL.check(LAY, fx)
        self.assertEqual(sum(t["card"] == "ies-res-vanity-grooming-300" and t["status"] == "fail"
                             for t in res["tasks"]), 3)


class Photometry(unittest.TestCase):
    def test_generic_distribution_carries_its_lumens_and_beam(self):
        for lm, beam in ((650, 55), (750, 36), (500, 24)):
            p = ph.parse(VL.generic_ies(lm, beam), name="t")
            self.assertAlmostEqual(p.integrated_flux(), lm, delta=0.02 * lm)
        iso = ph.parse(VL.generic_ies(800, None), name="iso")
        self.assertAlmostEqual(iso.integrated_flux(), 800, delta=16)   # the whole sphere (opal globe)

    def test_recessed_fittings_sit_in_their_room_clear_of_columns(self):
        for f in FX:
            if VL.KINDS[f.kind]["mount"] != "recessed":
                continue
            x0, y0, x1, y1 = F.clear_rect(LAY, f.room)
            self.assertTrue(x0 + 0.1 <= f.x <= x1 - 0.1 and y0 + 0.1 <= f.y <= y1 - 0.1, (f.id, f.x, f.y))
            for c in F._columns():
                self.assertFalse(c[0] - 0.05 <= f.x <= c[2] + 0.05 and c[1] - 0.05 <= f.y <= c[3] + 0.05, f.id)


if __name__ == "__main__":
    unittest.main()
