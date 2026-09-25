"""TV-01 (Mitton Fig. 4.10b) and DOOR-02 (AD M Appendix A, 90 degrees): positive and negative cases.

Fixtures are built from the quantity under test (seat distance, where the obstacle sits relative to the
leaf's sweep) and check their own geometry before the rule runs (see docs/LEARNINGS.md, 2026-09-25)."""
import math
import unittest

from archpipe import catalogue, model, rules

LV = (model.Level("L00", "L00", 0, 3000),)
WT = (model.WallType("W", 100.0, (), False, ""),)


def tv_room(seat_distance, lateral=0.0, screen_w=None):
    """A screen at the origin facing +Y and a 3-seat sofa `seat_distance` in front, `lateral` to the side."""
    screen_w = screen_w or catalogue.CATALOGUE["tv_screen"].width
    tv = model.Furniture("TV", "L00", "tv_screen", (0.0, 0.0), rotation=0, size=(screen_w, 80))
    sofa = model.Furniture("SOFA", "L00", "sofa_3seat", (lateral, seat_distance), rotation=180)
    assert sofa.at[1] - tv.at[1] == seat_distance and sofa.at[0] - tv.at[0] == lateral
    return model.Project("t", levels=LV, furniture=(tv, sofa))


def diag(screen_w):
    return screen_w * math.hypot(16, 9) / 16


class TVViewingTests(unittest.TestCase):
    W = catalogue.CATALOGUE["tv_screen"].width

    def test_inside_the_uhd_range_is_quiet(self):
        for f in (1.0, 1.25, 1.5):
            self.assertEqual(rules.r_tv_viewing(tv_room(f * diag(self.W)), "L00"), [], f)

    def test_too_close_and_too_far_are_reported_with_the_distance(self):
        for f in (0.9, 1.6):
            out = rules.r_tv_viewing(tv_room(f * diag(self.W)), "L00")
            self.assertEqual(len(out), 1, f)
            self.assertAlmostEqual(out[0].measured.achieved, f * diag(self.W), places=3)

    def test_seat_outside_the_view_cone_or_behind_is_not_judged(self):
        d = 0.9 * diag(self.W)
        self.assertEqual(rules.r_tv_viewing(tv_room(d, lateral=d), "L00"), [])      # 45 degrees off axis
        self.assertEqual(rules.r_tv_viewing(tv_room(-2000), "L00"), [])              # behind the screen

    def test_bigger_screen_moves_the_range(self):
        big = 1.5 * self.W
        self.assertEqual(rules.r_tv_viewing(tv_room(1.2 * diag(big), screen_w=big), "L00"), [])
        self.assertTrue(rules.r_tv_viewing(tv_room(1.2 * diag(big)), "L00"))         # too far for the 65 in


HINGE_X, LEAF = 1550.0, 900.0      # door 900 wide centred at 2000 on a wall along +X; left swing opens to +Y


def door_room(block_dx, block_y0):
    """An obstacle whose near corner sits `block_dx` along the closed leaf and `block_y0` out from the wall.
    The opening leaf first touches that corner, at atan2(block_y0, block_dx), if the corner is within the
    leaf's length."""
    wall = model.Wall("W1", "L00", "W", (0.0, 0.0), (4000.0, 0.0))
    door = model.Opening("D1", "W1", "door", LEAF, 2100, 2000.0, swing="left")
    width, depth = 600.0, 600.0
    centre = (HINGE_X + block_dx - width / 2, block_y0 + depth / 2)     # right edge at hinge + block_dx
    block = model.Furniture("B", "L00", "wardrobe", centre, rotation=0, size=(width, depth))
    assert abs((centre[0] + width / 2) - (HINGE_X + block_dx)) < 1e-9 and abs((centre[1] - depth / 2) - block_y0) < 1e-9
    return model.Project("t", levels=LV, wall_types=WT, walls=(wall,), openings=(door,), furniture=(block,))


class DoorSwingTests(unittest.TestCase):
    def test_obstacle_near_the_open_position_limits_the_angle(self):
        out = rules.r_door_swing_clear(door_room(block_dx=100.0, block_y0=300.0), "L00")
        self.assertEqual(len(out), 1)
        expected = math.degrees(math.atan2(300.0, 100.0))                  # near corner: about 71.6 degrees
        self.assertTrue(expected - 2 <= out[0].measured.achieved < expected, out[0].measured)
        self.assertEqual(out[0].measured.required, 90)

    def test_obstacle_beyond_the_leaf_is_quiet(self):
        self.assertEqual(rules.r_door_swing_clear(door_room(block_dx=100.0, block_y0=LEAF + 50), "L00"), [])

    def test_obstacle_behind_the_hinge_is_quiet(self):
        self.assertEqual(rules.r_door_swing_clear(door_room(block_dx=-20.0, block_y0=300.0), "L00"), [])


if __name__ == "__main__":
    unittest.main()
