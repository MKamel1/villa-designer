"""DIM-01 by room type (NDSS via Metric Handbook 7th ed. p. 22-4): positive and negative cases."""
import unittest

from archpipe import model, rules


def _p(*rooms):
    lv = model.Level("L00", "L00", 0, 3000)
    rs = tuple(model.Room(i, "L00", i, ((x, 0), (x + w, 0), (x + w, 4000), (x, 4000)), occ)
               for i, (occ, w, x) in enumerate(rooms) for i in [f"R{i}"])
    return model.Project("t", levels=(lv,), rooms=rs)


def _msgs(p):
    return [f.message for f in rules.r_room_min_width(p, "L00")]


class RoomWidthTests(unittest.TestCase):
    def test_single_bedroom_2150_passes_2100_fails(self):
        self.assertEqual(_msgs(_p(("bedroom_single", 2150, 0))), [])
        self.assertEqual(len(_msgs(_p(("bedroom_single", 2100, 0)))), 1)

    def test_other_double_2550_passes_when_a_first_double_is_2750(self):
        self.assertEqual(_msgs(_p(("bedroom", 2750, 0), ("bedroom", 2550, 5000))), [])

    def test_double_below_2550_fails(self):
        self.assertTrue(any("2550" in m for m in _msgs(_p(("bedroom", 2750, 0), ("bedroom", 2500, 5000)))))

    def test_no_double_reaches_2750_fails_once(self):
        m = _msgs(_p(("bedroom", 2600, 0), ("bedroom", 2600, 5000)))
        self.assertEqual(sum("2750" in x for x in m), 1)

    def test_living_still_uses_legacy_generic_width(self):
        self.assertEqual(len(_msgs(_p(("living", 2300, 0)))), 1)
        self.assertEqual(_msgs(_p(("living", 2400, 0))), [])


if __name__ == "__main__":
    unittest.main()
