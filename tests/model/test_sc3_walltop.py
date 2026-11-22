"""Lane SC3: every wall's top meets the soffit above it (or its infill does); the south B wall's roof slot is closed
without renumbering a wall id."""
import unittest

from archpipe.concept import revit_spec as RS, villa_render as VR


class WallTop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lay = VR.R.design("D1")
        cls.sp = RS.build(cls.lay)

    def test_every_wall_is_read_and_meets_its_soffit(self):
        r = RS.wall_top_readings(self.lay, self.sp["walls"], self.sp["infills"])
        self.assertEqual(len(r), len(self.sp["walls"]))                       # 36: nothing skipped
        self.assertEqual(RS.wall_top_problems(self.lay, self.sp["walls"], self.sp["infills"]), [])
        self.assertEqual(max(x["gap_mm"] for x in r), 10)                     # the two cross walls cut at the low face

    def test_positive_it_fails_on_the_pre_sc3_south_wall(self):
        # the failing reproduction: the real spec without the appended roof-strip infill (today's south wall, 150 mm open)
        probs = RS.wall_top_problems(self.lay, self.sp["walls"], self.sp["infills"][:-1])
        self.assertEqual(len(probs), 1)
        self.assertIn("wall #9", probs[0])
        self.assertIn("150 mm open", probs[0])
        self.assertTrue(RS.clearance_problems(self.lay, self.sp["walls"], self.sp["doors"], self.sp["infills"][:-1]))

    def test_negative_it_stays_quiet_on_the_walls_that_meet_their_soffit(self):
        walls = [dict(w) for w in self.sp["walls"]]
        r = RS.wall_top_readings(self.lay, walls, self.sp["infills"])
        self.assertEqual([x["index"] for x in r if x["gap_mm"] > 20], [])
        self.assertEqual([x["index"] for x in r if x["above_mm"] > 10], [])

    def test_a_wall_through_its_soffit_is_reported(self):
        walls = [dict(w) for w in self.sp["walls"]]
        walls[16] = dict(walls[16], height=2.95)
        self.assertTrue(any("wall #16" in p and "150 mm through" in p for p in
                            RS.wall_top_problems(self.lay, walls, self.sp["infills"])))

    def test_ids_are_not_renumbered(self):
        self.assertEqual(self.sp["walls"][9]["x1"], 15.412)                   # still one piece, same index
        self.assertEqual(len(self.sp["walls"]), 36)
        self.assertEqual(len(self.sp["infills"]), 4)                          # the 3 ramp infills keep indices 0-2
        self.assertEqual(self.sp["infills"][3]["what"], "wall top up to the extension roof soffit")
        self.assertEqual(self.sp["infills"][3]["profile"][0][0], 12.777)      # starts at the deck's end


if __name__ == "__main__":
    unittest.main()
