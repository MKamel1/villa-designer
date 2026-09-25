"""DOOR-01 per UK AD M Vol 1 para 2.20 and Table 2.1: positive and negative cases."""
import unittest

from archpipe import model, rules

WT = (model.WallType("INT", 100.0, (), False, ""), model.WallType("EXT", 300.0, (), True, ""))
LV = (model.Level("L00", "L00", 0, 3000),)


def _room(i, occ, x0, y0, x1, y1):
    return model.Room(i, "L00", i, ((x0, y0), (x1, y0), (x1, y1), (x0, y1)), occ)


def _corridor_side_door(corridor_w, door_w):
    """A 6 m east-west corridor of width corridor_w with a bedroom north of it; door in the shared wall."""
    rooms = (_room("C", "corridor", 0, 0, 6000, corridor_w), _room("B", "bedroom", 0, corridor_w + 100, 6000, corridor_w + 4100))
    wall = model.Wall("W", "L00", "INT", (0, corridor_w + 50), (6000, corridor_w + 50))
    return model.Project("t", levels=LV, wall_types=WT, walls=(wall,),
                         openings=(model.Opening("D", "W", "door", door_w, 2100, 3000),), rooms=rooms)


def _corridor_end_door(door_w):
    """A 900 mm north-south corridor with a bedroom at its north end; door in the end wall (head on)."""
    rooms = (_room("C", "corridor", 0, 0, 900, 6000), _room("B", "bedroom", -2000, 6100, 3000, 10000))
    wall = model.Wall("W", "L00", "INT", (-2000, 6050), (3000, 6050))
    return model.Project("t", levels=LV, wall_types=WT, walls=(wall,),
                         openings=(model.Opening("D", "W", "door", door_w, 2100, 2450),), rooms=rooms)


def _n(p):
    return len(rules.r_door_clear_width(p, "L00"))


class DoorWidthTests(unittest.TestCase):
    def test_900_corridor_side_door_needs_800(self):
        self.assertEqual(_n(_corridor_side_door(900, 800)), 0)
        self.assertEqual(_n(_corridor_side_door(900, 775)), 1)

    def test_1050_corridor_side_door_needs_775(self):
        self.assertEqual(_n(_corridor_side_door(1050, 775)), 0)
        self.assertEqual(_n(_corridor_side_door(1050, 750)), 1)

    def test_1200_corridor_side_door_needs_750(self):
        self.assertEqual(_n(_corridor_side_door(1200, 750)), 0)
        self.assertEqual(_n(_corridor_side_door(1200, 700)), 1)

    def test_head_on_from_900_corridor_needs_750(self):
        self.assertEqual(_n(_corridor_end_door(750)), 0)
        self.assertEqual(_n(_corridor_end_door(700)), 1)

    def test_entrance_needs_775(self):
        rooms = (_room("H", "hall", 0, 150, 3000, 3000),)
        wall = model.Wall("W", "L00", "EXT", (0, 0), (3000, 0))
        for w, n in ((775, 0), (750, 1)):
            p = model.Project("t", levels=LV, wall_types=WT, walls=(wall,),
                              openings=(model.Opening("D", "W", "door", w, 2100, 1500),), rooms=rooms)
            self.assertEqual(_n(p), n, w)


if __name__ == "__main__":
    unittest.main()
