"""Parents' suite privacy on the BUILT model (client 2026-11-26): every suite door open, no outside viewpoint sees the dressing room,
the en-suite or the route between them. Positive control: the client's straight-vestibule idea (option 2, docs/lanes/DF-privacy-options.md)
on the same walls DOES show them from far away, so the engine is not blind; negative: the build itself shows none."""
import unittest

from shapely.geometry import box

from archpipe import model
from archpipe.model import suite_privacy as SP

# option 2: a door straight from the vestibule's end into the dressing room (opening in the wall at x 19.527, y -28.346..-27.546)
OPTION_2_CUT = [box(19.477, -28.346, 19.577, -27.546)]


class SuitePrivacy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.els = model.load("D1")
        cls.built = SP.seeing(cls.els)

    def test_built_model_has_zero_outside_viewpoints_seeing_in(self):
        self.assertGreater(self.built["viewpoints"], 300)
        self.assertGreater(self.built["targets"], 200)
        self.assertEqual(self.built["seeing"], [], self.built["seeing"][:3])

    def test_option_2_geometry_is_seen_from_the_corridor_and_the_landing(self):
        r = SP.seeing(self.els, cuts=OPTION_2_CUT)
        labels = {v[2] for v in r["seeing"]}
        self.assertGreater(len(r["seeing"]), 100)                 # the earlier sketch counted 367 of 371
        self.assertIn("corridor", labels)
        self.assertTrue(labels & {"stair landing", "kids-b doorway"}, labels)

    def test_the_suite_door_does_not_have_to_be_shut(self):
        """The criterion is geometric: leaves ignored, every door of the suite is in the open state."""
        doors = {e.id for e in self.els if e.kind == "door"}
        self.assertTrue(set(SP.SUITE_DOORS) <= doors)
        open_leaves = SP.seeing(self.els, leaves=SP.SUITE_DOORS[:1] + SP.SUITE_DOORS[2:3])
        self.assertEqual(open_leaves["seeing"], [])

    def test_kids_b_door_and_corridor_are_outside_viewpoints(self):
        labels = {v[2] for v in SP.viewpoints(self.els)}
        self.assertTrue({"corridor", "kids-b doorway", "stair landing"} <= labels, labels)


if __name__ == "__main__":
    unittest.main()
