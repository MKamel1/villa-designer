"""FURN-02 bed clearances per UK AD M Vol 1 para 2.25 (b, c, d): positive and negative cases."""
import unittest

from archpipe import model, rules

WT = (model.WallType("W", 200.0, (), True, ""),)
LV = (model.Level("L00", "L00", 0, 3000),)


def _room(width=4000, depth=4000):
    walls = (model.Wall("S", "L00", "W", (0, 0), (width, 0)), model.Wall("E", "L00", "W", (width, 0), (width, depth)),
             model.Wall("N", "L00", "W", (width, depth), (0, depth)), model.Wall("Wst", "L00", "W", (0, depth), (0, 0)))
    room = model.Room("R", "L00", "Bedroom", ((100, 100), (width - 100, 100), (width - 100, depth - 100), (100, depth - 100)),
                      "bedroom")
    return walls, room


def _msgs(bed_type, x_centre, width=4000):
    walls, room = _room(width)
    # bed 1600 x 2000, head against the north wall, foot (front) facing south
    bed = model.Furniture("B", "L00", bed_type, (x_centre, 4000 - 100 - 1000), rotation=180)
    p = model.Project("t", levels=LV, wall_types=WT, walls=walls, rooms=(room,), furniture=(bed,))
    return [f.message for f in rules.r_furniture_clearance(p, "L00")]


class BedClearanceTests(unittest.TestCase):
    def test_principal_double_needs_both_sides(self):
        self.assertEqual(_msgs("bed_double", 2000), [])            # 1100 mm each side, 1900 at the foot
        self.assertTrue(_msgs("bed_double", 100 + 800 + 300))      # one side only 300 mm

    def test_other_double_needs_one_side_and_foot(self):
        self.assertEqual(_msgs("bed_double_other", 100 + 800 + 50), [])     # against a wall, 1250 mm on the other side
        self.assertEqual(_msgs("bed_double_other", 100 + 800 + 50, width=2700), [])  # 850 mm on one side: enough
        self.assertTrue(_msgs("bed_double_other", 1350, width=2700))   # centred: 450 mm each side, neither reaches 750

    def test_single_needs_one_side_only(self):
        self.assertEqual(_msgs("bed_single", 100 + 450 + 20), [])


if __name__ == "__main__":
    unittest.main()
