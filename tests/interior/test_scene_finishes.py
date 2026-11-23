"""What the production scene really draws of the client's finish mix (2026-11-23). One diagnostic build (receipts bypassed:
the receipts are checked by the production build and tests/test_furniture_stage2*, not here)."""
import unittest
from unittest.mock import patch

import numpy as np

from archpipe.blender import grain
from archpipe.interior import chosen as CH

_SCENE = None


def scene():
    global _SCENE
    if _SCENE is None:
        from archpipe.concept import villa_render as V
        with patch("archpipe.concept.furniture_stage2.apply", side_effect=lambda s, *a: s), \
                patch("archpipe.concept.parents_bed.apply", side_effect=lambda s, *a: s):
            _SCENE = V.build()
    return _SCENE


def bbox(m):
    P = np.array([p for f in m["faces"] for p in f])
    return P.min(0), P.max(0)


def collapsed(grain_axis, half):
    """Real defect class (v33 draft, 2026-11-23: stone floor striped): the grain rotation sends a thin extent into a
    sampled coordinate. Compared with the identity mapping 'x', so a legitimately narrow strip is not flagged."""
    u, v = grain.mapping_rotated_span(grain_axis, tuple(half))
    u0, v0 = grain.mapping_rotated_span("x", tuple(half))
    return min(u, v) < 0.2 * min(u0, v0)


class FinishLayers(unittest.TestCase):
    def test_no_finish_layer_samples_a_collapsed_texture_coordinate(self):
        sc = scene()
        bad = []
        for m in sc["meshes"]:
            ga = (sc["materials"].get(m["material"]) or {}).get("grain_axis")
            if ga and m.get("part_kind") == "finish-layer":
                lo, hi = bbox(m)
                if (hi - lo).max() > 0.1 and collapsed(ga, (hi - lo) / 2):
                    bad.append((m["id"], m["material"], ga))
        self.assertEqual(bad, [])

    def test_the_guard_catches_the_real_v33_defect(self):
        """Negative control on the REAL geometry: the lounge floor with the grain axis the first chosen.json forced on stone."""
        floor = next(m for m in scene()["meshes"] if m["id"] == "floor-lounge")
        lo, hi = bbox(floor)
        self.assertTrue(collapsed("z", (hi - lo) / 2))
        self.assertFalse(collapsed("x", (hi - lo) / 2))

    def test_stone_and_tile_slots_carry_no_grain_axis(self):
        ch = CH.load()
        for sid in ("floor-basement", "floor-wet", "wall-tile-wet", "worktop"):
            self.assertNotIn("grain_axis", ch["slots"][sid]["render"], sid)

    def test_every_room_floor_is_its_scheduled_floor(self):
        sc = scene()
        want = CH.room_finish()
        for rid, (floor, _) in want.items():
            m = next((m for m in sc["meshes"] if m["id"] == "floor-" + rid), None)
            if rid == "stair-b":                 # the stair has no floor layer (the builder skips it)
                self.assertIsNone(m)
                continue
            self.assertEqual(m["material"], floor, rid)


class FeatureWall(unittest.TestCase):
    def test_nile_clay_only_on_the_parents_head_wall(self):
        sc = scene()
        meshes = [m for m in sc["meshes"] if m["material"] == "fin-wall-feature"]
        self.assertTrue(meshes)
        self.assertEqual({m["room"] for m in meshes}, {"parents-bed"})
        for m in meshes:
            lo, hi = bbox(m)
            self.assertTrue(18.4 < lo[0] and hi[0] < 22.7 and -26.7 < lo[1] and hi[1] < -26.5, m["id"])   # the head wall only


class KitchenAndJoinery(unittest.TestCase):
    def test_kitchen_zone_takes_B_and_nothing_else_takes_the_kitchen_front(self):
        sc = scene()
        kitchen = ("kitchen", "kitchen-island", "dirty-kitchen")
        for m in sc["meshes"]:
            if m["material"] == "greige-lacquer":
                self.assertIn(m.get("room"), kitchen, m["id"])          # the fenix front is the kitchen's only
            if m.get("room") in kitchen:
                self.assertNotIn(m["material"], ("walnut", "walnut-grain-x", "oak"), m["id"])   # kitchen timber is B's joinery
        self.assertTrue(any(m["material"] == "marble-white" and m.get("room") in kitchen for m in sc["meshes"]))


class CushionHeight(unittest.TestCase):
    """Real defect (v34 draft, 2026-11-23): a 0.58 m LAGERPOPPEL leaning at 22 deg on the 0.89 m library sofa stood 10 cm proud
    of its back and read as a dark panel from behind."""

    def test_the_first_lean_stood_proud_and_the_chosen_lean_does_not(self):
        from archpipe.interior import soft_dressing as SD
        def top(alpha, z0=0.44, h=580):
            faces = SD.leaning_cushion(0, 0, 0, 0, 0.1, z0, 500, h, alpha)
            return max(p[2] for f in faces for p in f)
        self.assertGreater(top(22.0, z0=0.48 - 0.04) - 0.89, 0.04)       # the first render's setting: proud
        self.assertLess(top(30.0, z0=0.48 - 0.04, h=SD.lumbar(400, 580)[1]) - 0.89, 0.03)     # the chosen one: lumbar, landscape
        self.assertLess(top(30.0, z0=0.48 - 0.04, h=500) - 0.89, 0.03)                      # and a 500 mm SANELA

    def test_scene_cushions_stay_near_their_sofa_back(self):
        sc = scene()
        from archpipe.concept import villa_furnish as F, villa_r11 as R
        items = {i["id"]: i for i in F.layout(R.design("D1"))}
        for m in sc["meshes"]:
            if m["id"].startswith("dress-cushion-") and not m["id"].startswith("dress-cushion-pb-bed"):
                sofa = m["id"][len("dress-cushion-"):].rsplit("-", 1)[0]
                lo, hi = bbox(m)
                base = -3.0 if items[sofa]["room"] in ("lounge", "living", "cinema", "bar-alcove") else 0.0
                self.assertLess(hi[2] - base - items[sofa]["h"], 0.05, m["id"])


class SoftSchedule(unittest.TestCase):
    def test_every_scheduled_cushion_throw_and_rug_is_drawn_except_the_documented_gaps(self):
        sc = scene()
        used = {m["material"] for m in sc["meshes"]}
        ch = CH.load()
        slots = [s for s in ch["slots"].values() if s["group"] == "soft" and s.get("scene_materials")]
        missing = [n for s in slots for n in s["scene_materials"] if n not in used and n not in sc.get("cloth_materials", [])
                   and not any(c.get("material") == n for c in sc.get("cloth", []))]
        self.assertEqual(missing, [])

    def test_the_single_throw_pillow_prop_is_gone(self):
        self.assertFalse([p for p in scene().get("props", []) if p["asset"] == "throw_pillows_01"])

    def test_cushions_rest_on_their_seat(self):
        sc = scene()
        for m in sc["meshes"]:
            if m["id"].startswith("dress-cushion-"):
                lo, hi = bbox(m)
                self.assertTrue(0.3 < lo[2] - (-3.0 if m["room"] in ("lounge", "living", "cinema", "bar-alcove") else 0.0) < 0.7, (m["id"], lo[2]))


if __name__ == "__main__":
    unittest.main()
