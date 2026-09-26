"""The five stair / service options as complete layouts: they pass the critic, and option 5 keeps the basement bar
clear across its full width (client 2026-09-26)."""
import unittest

from archpipe.concept import revit_spec as R
from archpipe.concept import stair_options as SO
from archpipe.concept import villa as V
from archpipe.concept import villa_options as VO


class Options(unittest.TestCase):
    def test_every_option_passes_the_critic(self):
        for lay in VO.options():
            self.assertEqual(V.critique(lay)["fails"], [], lay["id"])

    def test_every_option_builds_a_revit_spec_with_its_stair_and_opening(self):
        for lay in VO.options():
            s = R.build(lay)
            self.assertTrue(s["walls"] and s["doors"] and s["rooms"] and s["stair"], lay["id"])
            self.assertIsNotNone(s["gf_opening"], lay["id"])

    def test_option5_bar_holds_no_closed_room_but_the_stair(self):
        lay = VO.s5()
        bar = (V.X0, V.YP, V.XR, V.YE)
        closed_in_bar = [rid for rid, r in lay["rooms"].items() if r["level"] == "B" and
                         r["occupancy"] not in SO.OPEN_OCC | {"stair"} and
                         r["rect"][0] >= bar[0] - 1e-6 and r["rect"][2] <= bar[2] + 1e-6 and
                         r["rect"][1] >= bar[1] - 1e-6 and r["rect"][3] <= bar[3] + 1e-6]
        self.assertEqual(closed_in_bar, [])

    def test_option5_blocks_sit_in_the_east_yard_and_leave_a_path(self):
        for x0, y0, x1, y1 in V._exts(VO.s5()["extension"]):
            self.assertGreaterEqual(y0, V.YE - 1e-6)
            self.assertLessEqual(y1, V.FENCE_E + 1e-6)
        self.assertGreaterEqual(V.FENCE_E - VO.POD_DIRTY[3], 0.9)       # service path beside the dirty kitchen

    def test_a_block_covers_the_bar_window_behind_it(self):
        """Negative: the bar's east face behind a block is no longer a window face; beyond it, it still is."""
        faces = V.window_faces("B", VO.s5()["extension"])
        east = [f for f in faces if f[0] == "h" and abs(f[1] - V.YE) < 1e-6]
        mid_dirty = (VO.POD_DIRTY[0] + VO.POD_DIRTY[2]) / 2
        self.assertFalse(any(f[2] <= mid_dirty <= f[3] for f in east))
        self.assertTrue(any(f[2] <= 17.0 <= f[3] for f in east))

    def test_services_mid_plan_still_block_the_entrance_view(self):
        self.assertEqual(SO.analyse_layout(VO.s1())["entrance_view_share"], 0.0)
        self.assertEqual(SO.analyse_layout(VO.s2())["entrance_view_share"], 1.0)


if __name__ == "__main__":
    unittest.main()
