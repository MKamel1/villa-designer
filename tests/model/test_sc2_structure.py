"""Lane SC2: joinery yields to the stair steel (model and scene agree); the B extension wall meets the roof soffit."""
import unittest

import numpy as np

from archpipe.blender import g1_geometry as G1
from archpipe.concept import revit_spec as RS, villa_render as VR
from archpipe.model import spec_source as SS, stair_steel as ST


class Sc2Structure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sp = RS.build(VR.R.design("D1"))
        cls.cup = SS.cupboard(cls.sp)[0]

    def test_steel_members_are_model_data_with_ids_and_assumed_basis(self):
        stair = SS.stairs(None, self.sp)[0]
        ids = [m["id"] for m in stair.params["steel"]["members"]]
        self.assertEqual(len(ids), 16 + 3)                       # 16 bearings, wall plate, open stringer, glass shoe
        self.assertIn("detail-stair-open-stringer", ids)
        self.assertTrue(all("ASSUMED" in m["basis"] for m in stair.params["steel"]["members"]))

    def test_cupboard_stays_between_the_steel_planes(self):
        wall_y, open_y = ST.clear_y(self.sp)
        i = self.cup.params["interior_mm"]
        self.assertAlmostEqual(i[1], wall_y * 1000, places=3)                    # back face = bearing face
        self.assertLessEqual(i[3] + 100, open_y * 1000 + 1e-6)                   # side wall's outer face = shoe face
        self.assertAlmostEqual(self.cup.size[1], (open_y - wall_y) * 1000, places=3)
        self.assertLess(self.cup.params["volume_m3"], 2.62)
        self.assertAlmostEqual(self.cup.params["volume_m3"], 2.21, places=2)

    def test_negative_the_spec_cupboard_does_cross_the_steel(self):
        # the pre-SC2 footprint (spec): the guard must see it, or the test above proves nothing
        wall_y, open_y = ST.clear_y(self.sp)
        c = self.sp["understair_cupboard"]
        self.assertLess(c["y0"], wall_y)
        self.assertGreater(c["y1"], open_y)

    def test_model_footprint_equals_what_the_scene_builder_draws(self):
        wall_y, open_y = ST.clear_y(self.sp)
        parts = G1.understair_cupboard(self.sp, VR.box_faces, wall_y, open_y)
        v = np.array([p for part in parts if not part.mesh_id.endswith("pull") for f in part.faces for p in f])
        self.assertAlmostEqual(v[:, 1].min() * 1000, self.cup.params["interior_mm"][1], places=3)
        self.assertAlmostEqual(v[:, 1].max() * 1000, self.cup.params["interior_mm"][1] + self.cup.size[1], places=3)

    def test_b_extension_wall_meets_the_roof_soffit_like_its_twin(self):
        els = {e.id: e for e in SS.walls(self.sp)}
        self.assertEqual(els["wall-B-ext-16"].size[2], 2800.0)
        self.assertEqual(els["wall-B-ext-17"].size[2], 2800.0)

    def test_negative_walls_under_the_deck_keep_the_deck_soffit(self):
        els = {e.id: e for e in SS.walls(self.sp)}
        under = [w for w in els.values() if w.level == "B" and w.rotation_deg in (90.0, -90.0) and 9000 < w.placement[0] < 12000]
        self.assertTrue(under and all(w.size[2] == 2650.0 for w in under))

    def test_window_heads_are_the_one_storey_standard(self):
        heads = {round(e.params["sill_mm"] + e.params["height_mm"]) for e in SS.windows(self.sp, SS.walls(self.sp))}
        self.assertEqual(heads, {2300})


if __name__ == "__main__":
    unittest.main()
