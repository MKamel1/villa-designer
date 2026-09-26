"""Stair options scored on the client's openness goal (view from the basement to the back garden)."""
import copy
import unittest

from archpipe.concept import stair_options as O


def opt(i):
    return next(o for o in O.OPTIONS if o["id"] == i)


class Openness(unittest.TestCase):
    def test_services_mid_plan_block_the_entrance_view(self):
        """S1 (current A): the dirty kitchen and guest WC in the spine cut every sight line from the entrance."""
        r = O.analyse(opt("S1"))
        self.assertEqual(r["entrance_view_share"], 0.0)

    def test_moving_the_services_opens_the_view_without_moving_the_stair(self):
        s1, s2 = O.analyse(opt("S1")), O.analyse(opt("S2"))
        self.assertEqual(s2["entrance_view_share"], 1.0)
        self.assertGreaterEqual(s2["garden_view_share"], 0.95)
        self.assertGreater(s2["garden_view_m2"], s1["garden_view_m2"] + 10)

    def test_every_option_is_clash_free(self):
        for o in O.OPTIONS:
            self.assertEqual(O.analyse(o)["clashes"], [], o["id"])

    def test_a_closed_room_on_the_stair_is_refused(self):
        bad = copy.deepcopy(opt("S4"))
        bad["services"] = "front"                   # the first S4 draft: services drawn over the flight
        with self.assertRaises(ValueError):
            O.obstacles(bad)

    def test_sight_line_blocker_negative(self):
        """A segment beside a rectangle is not blocked; one through it is."""
        r = (1.0, 1.0, 2.0, 2.0)
        self.assertTrue(O._seg_hits_rect((0.0, 1.5), (3.0, 1.5), r))
        self.assertFalse(O._seg_hits_rect((0.0, 2.5), (3.0, 2.5), r))


if __name__ == "__main__":
    unittest.main()
