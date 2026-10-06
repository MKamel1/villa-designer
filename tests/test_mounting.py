"""Finished-face mounting, including frozen dimensions from D1 failures."""
import unittest

from archpipe.concept.mounting import Finish, Host, MountItem, mount


class MountingTest(unittest.TestCase):
    def test_stair_handrail_uses_plaster_face_then_projection(self):
        # D1 l0856: wall datum -28.671, plaster face -28.471; the old
        # rail's nearest surface was -28.386, but its original offset was
        # inside the plaster.  Values are frozen here, not imported from D1.
        wall = Host("stair-wall", "wall", (0.0, -28.671, 0.9),
                    (0.0, 1.0, 0.0), Finish("wall assembly through finished plaster", 0.200))
        p = mount(MountItem("stair-wall-handrail"), wall, "finished", 0.125, "wall-hung")
        self.assertAlmostEqual(p.finished_face[1], -28.471)
        self.assertAlmostEqual(p.position[1], -28.346)
        self.assertGreater(p.position[1], p.finished_face[1])

    def test_real_recessed_failure_and_clean_sibling(self):
        # l0119: a body top at 2732 mm exceeded the 2700 mm finished
        # ceiling; the implied housing depth was at least 32 mm beyond it.
        ceiling = Host("bedroom-ceiling", "ceiling", (0.0, 0.0, 2.712),
                       (0.0, 0.0, -1.0), Finish("ceiling-board", 0.012), 0.025)
        with self.assertRaisesRegex(ValueError, "exceeds the clear void"):
            mount(MountItem("LT-01", 0.032), ceiling, "finished", 0.0, "recessed")
        p = mount(MountItem("shallow-downlight", 0.020), ceiling, "finished", 0.0, "recessed")
        self.assertAlmostEqual(p.position[2], 2.700)

    def test_marble_cladding_and_structural_face_rejected(self):
        wall = Host("bath-wall", "wall", (1.0, 0.0, 1.5), (1.0, 0.0, 0.0),
                    Finish("marble-cladding", 0.025))
        p = mount(MountItem("vanity-sconce"), wall, "finished", 0.0, "surface-mounted")
        self.assertAlmostEqual(p.position[0], 1.025)
        with self.assertRaisesRegex(ValueError, "finished face"):
            mount(MountItem("vanity-sconce"), wall, "structural", 0.0, "surface-mounted")

    def test_plaster_build_up_is_applied_from_near_structural_face(self):
        wall = Host("plastered-partition", "wall", (0.0, 1.0, 1.2),
                    (0.0, 1.0, 0.0), Finish("plaster", 0.015))
        p = mount(MountItem("rail"), wall, "finished", 0.060, "wall-hung")
        self.assertAlmostEqual(p.finished_face[1], 1.015)
        self.assertAlmostEqual(p.position[1], 1.075)

    def test_floor_standing_and_invalid_host(self):
        floor = Host("finished-floor", "floor", (0.0, 0.0, 0.0),
                     (0.0, 0.0, 1.0), Finish("floor-finish", 0.002))
        p = mount(MountItem("cabinet"), floor, "finished", 0.0, "floor-standing")
        self.assertAlmostEqual(p.position[2], 0.002)
        with self.assertRaisesRegex(ValueError, "vertical host"):
            mount(MountItem("cabinet"), floor, "finished", 0.1, "wall-hung")


if __name__ == "__main__":
    unittest.main()
