"""FURN-02 bed clearances per UK AD M Vol 1 para 2.25 (b, c, d): positive and negative cases.

Fixtures are built from the clearances they are meant to produce (left gap, right gap, foot gap),
never from hand-computed coordinates, and each fixture asserts its own geometry before the rule
runs. Two hand-arithmetic slips in test fixtures (2026-09-25) are why: a wrong fixture fails
exactly like a wrong rule, and the temptation is to "fix" the rule.
"""
import unittest

from archpipe import catalogue, model, rules

WALL = 200.0                     # wall thickness; walls centred on the room outline
HALF = WALL / 2
WT = (model.WallType("W", WALL, (), True, ""),)
LV = (model.Level("L00", "L00", 0, 3000),)


def bedroom(bed_type, left_gap, right_gap, foot_gap=1500.0):
    """A room whose inner faces sit exactly `left_gap` / `right_gap` / `foot_gap` mm from the bed,
    with the bed's head against the north wall. The bed size is the one the rule itself uses."""
    bed_w, BED_D = catalogue.CATALOGUE[bed_type].width, catalogue.CATALOGUE[bed_type].depth
    inner_w = left_gap + bed_w + right_gap
    inner_d = BED_D + foot_gap
    W, D = inner_w + WALL, inner_d + WALL          # outline (wall centrelines)
    walls = (model.Wall("S", "L00", "W", (0, 0), (W, 0)), model.Wall("E", "L00", "W", (W, 0), (W, D)),
             model.Wall("N", "L00", "W", (W, D), (0, D)), model.Wall("Wst", "L00", "W", (0, D), (0, 0)))
    room = model.Room("R", "L00", "Bedroom", ((HALF, HALF), (W - HALF, HALF), (W - HALF, D - HALF), (HALF, D - HALF)),
                      "bedroom")
    bed = model.Furniture("B", "L00", bed_type, (HALF + left_gap + bed_w / 2, D - HALF - BED_D / 2), rotation=180)
    p = model.Project("t", levels=LV, wall_types=WT, walls=walls, rooms=(room,), furniture=(bed,))
    # the fixture proves its own geometry before any rule is asked anything
    xs = [c[0] for c in bed.corners(bed_w, BED_D)]
    ys = [c[1] for c in bed.corners(bed_w, BED_D)]
    assert abs((min(xs) - HALF) - left_gap) < 1e-6 and abs((W - HALF - max(xs)) - right_gap) < 1e-6
    assert abs((min(ys) - HALF) - foot_gap) < 1e-6 and abs(D - HALF - max(ys)) < 1e-6
    return p


def findings(p):
    return [f.message for f in rules.r_furniture_clearance(p, "L00")]


class BedClearanceTests(unittest.TestCase):
    def test_principal_double_needs_750_both_sides_and_foot(self):
        self.assertEqual(findings(bedroom("bed_double", 750, 750, 750)), [])
        self.assertTrue(findings(bedroom("bed_double", 750, 740, 750)))     # one side short
        self.assertTrue(findings(bedroom("bed_double", 750, 750, 740)))     # foot short

    def test_other_double_needs_one_side_and_foot(self):
        self.assertEqual(findings(bedroom("bed_double_other", 0, 750, 750)), [])   # against a wall
        self.assertEqual(findings(bedroom("bed_double_other", 850, 50, 750)), [])  # 850 on one side is enough
        self.assertTrue(findings(bedroom("bed_double_other", 450, 450, 750)))      # centred: neither side 750
        self.assertTrue(findings(bedroom("bed_double_other", 0, 750, 740)))        # foot short

    def test_single_needs_one_side_only(self):
        self.assertEqual(findings(bedroom("bed_single", 0, 750, 0)), [])  # no foot zone for singles
        self.assertTrue(findings(bedroom("bed_single", 0, 740, 0)))


if __name__ == "__main__":
    unittest.main()
