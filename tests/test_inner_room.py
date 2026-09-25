"""FIRE-01 inner rooms per UK AD B Vol 1 paras 2.10-2.11: positive and negative cases.

Two 3.9 m rooms share a partition with a door; the 'outer' room has the only external door and the
inner room has one window in its north wall. Fixtures are built from the quantities under test (window
size and sill, storey height, occupancy) and check their own geometry (docs/LEARNINGS.md, 2026-09-25)."""
import unittest

from archpipe import model, rules

WT = (model.WallType("EXT", 300.0, (), True, ""), model.WallType("INT", 100.0, (), False, ""))


def plan(inner_occ="bedroom", win_w=900.0, win_h=1200.0, sill=900.0, elevation=0.0, inner_door_to="living",
         window=True):
    levels = (model.Level("G", "G", 0.0, 3000), model.Level("L", "L", elevation, 3000)) if elevation else \
        (model.Level("L", "L", 0.0, 3000),)
    walls = (model.Wall("S", "L", "EXT", (0, 0), (4000, 0)),            # outer room's external wall (entrance)
             model.Wall("P", "L", "INT", (4000, 0), (4000, 4000)),      # shared partition
             model.Wall("N", "L", "EXT", (4000, 4000), (8000, 4000)))   # inner room's window wall
    outer = model.Room("O", "L", "Outer", ((150, 150), (3950, 150), (3950, 3850), (150, 3850)), inner_door_to)
    inner = model.Room("I", "L", "Inner", ((4050, 150), (7850, 150), (7850, 3850), (4050, 3850)), inner_occ)
    ops = [model.Opening("DE", "S", "door", 1000, 2100, 2000.0), model.Opening("DI", "P", "door", 900, 2100, 2000.0)]
    if window:
        ops.append(model.Opening("W", "N", "window", win_w, win_h, 2000.0, sill=sill))
    p = model.Project("t", levels=levels, wall_types=WT, walls=walls, openings=tuple(ops), rooms=(outer, inner))
    # the fixture proves its own topology: the partition door joins exactly the two rooms
    a, b = rules.opening_sides(p, ops[1])
    assert {a.id, b.id} == {"O", "I"}
    if window:
        wa, wb = rules.opening_sides(p, ops[2])
        assert {x.id for x in (wa, wb) if x} == {"I"}
    return p


def fire(p):
    return rules.r_inner_room(p, "L")


class InnerRoomTests(unittest.TestCase):
    def test_ground_floor_bedroom_with_escape_window_is_permitted(self):
        self.assertEqual(fire(plan()), [])

    def test_window_below_escape_size_fails(self):
        self.assertTrue(fire(plan(win_w=440)))                     # under 450 mm wide
        self.assertTrue(fire(plan(win_w=500, win_h=600)))          # 0.30 m2 < 0.33
        self.assertEqual(fire(plan(win_w=550, win_h=600)), [])     # 0.33 m2 exactly

    def test_sill_above_1100_fails(self):
        self.assertTrue(fire(plan(sill=1110)))
        self.assertEqual(fire(plan(sill=1100)), [])

    def test_no_window_fails(self):
        self.assertTrue(fire(plan(window=False)))

    def test_storey_above_4_5_m_fails_even_with_escape_window(self):
        self.assertEqual(fire(plan(elevation=4500)), [])
        out = fire(plan(elevation=4600))
        self.assertTrue(out)
        self.assertEqual((out[0].measured.achieved, out[0].measured.required), (4600, 4500))

    def test_permitted_inner_room_types(self):
        for occ in ("kitchen", "utility", "dressing", "bathroom", "ensuite", "wc"):
            self.assertEqual(fire(plan(inner_occ=occ, window=False)), [], occ)

    def test_room_opening_onto_a_hall_is_not_inner(self):
        self.assertEqual(fire(plan(inner_door_to="hall", window=False)), [])


if __name__ == "__main__":
    unittest.main()
