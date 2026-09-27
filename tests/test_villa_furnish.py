"""D1 furnishing (round 12): the authored layout passes every check, and each check fails on a real bad placement
(several taken from this layout's own first drafts)."""
import copy
import unittest

from archpipe import catalogue as cat
from archpipe.concept import villa_furnish as F
from archpipe.concept import villa_r11 as R


def _run(mutate):
    lay = R.design("D1")
    items = copy.deepcopy(F.layout(lay))
    ids = {it["id"]: it for it in items}
    mutate(items, ids)
    return F.check(items, lay)


class Layout(unittest.TestCase):
    def test_d1_passes_every_check(self):
        res = F.check()
        self.assertEqual({k: v["problems"] for k, v in res.items() if v["status"] != "pass"}, {})
        self.assertEqual(len(res), 10)                      # 9 checks + the extended-table re-run

    def test_a_table_too_long_to_extend_is_caught(self):
        orig = F.EXTENDED_TABLE
        try:
            F.EXTENDED_TABLE = 3.8                           # reaches the island end and the living sofa
            self.assertEqual(F.check()["extended_table"]["status"], "fail")
        finally:
            F.EXTENDED_TABLE = orig

    def test_stair_foot_must_stay_reachable(self):
        res = _run(lambda items, ids: items.append(F.item("console", "hall-b", "sideboard", 10.1, -28.0, 90, w=1.2,
                                                          d=0.45, h=0.8, why="x", level="B")))
        self.assertTrue(any("stair end of stair-b" in p for p in res["routes"]["problems"]), res["routes"])

    def test_principal_bedroom_window_must_stay_reachable(self):
        # AD M Diagram 2.4 note 1: clear access to the window (a wardrobe against the garden window, vanity moved)
        def m(items, ids):
            items.remove(ids["pb-vanity"])
            items.append(F.item("robe", "parents-bed", "wardrobe", 22.397 - 0.275, -25.4, 90, w=2.6, d=0.55, h=2.2,
                                why="x", level="GF"))
        res = _run(m)
        self.assertTrue(any("window of parents-bed" in p for p in res["routes"]["problems"]), res["routes"])

    def test_the_window_guard_follows_the_room_not_the_bed_type(self):
        # it was keyed on bed_king: the queen bed (bed_double) silently switched it off
        F.TRACE = {}
        try:
            F.check()
            nodes = [n for n, _ in F.TRACE["parents-bed+parents-entry"]["nodes"]]
        finally:
            F.TRACE = None
        self.assertEqual(nodes.count("window of parents-bed"), 2)
        self.assertIn("door corridor/parents-entry", nodes)      # a pocket door still gives a route node

    def test_every_item_has_a_reason_and_a_catalogue_type(self):
        for it in F.layout():
            self.assertTrue(it["why"], it["id"])
            cat.get(it["type"])

    def test_the_route_check_really_examines_rooms(self):
        # the kids A wardrobe moved into the room's middle shuts the bunk and both desks off from the door
        res = _run(lambda items, ids: ids["ka-wardrobe"].update(cx=13.4))
        self.assertTrue(any(p.startswith("ka-bunk") for p in res["routes"]["problems"]), res["routes"])

    def test_the_body_turns_a_corner_the_path_turns(self):
        # the dressing: the rail end and a column 1.24 m apart on the diagonal, legs 1.05 and 0.94 m: a 914 mm path
        # turns there (a 914 mm SQUARE did not). And a straight 0.90 m aisle is still refused:
        self.assertEqual(F.check()["routes"]["status"], "pass")
        res = _run(lambda items, ids: ids["pd-hang-2"].update(cy=ids["pd-hang-2"]["cy"] + 0.04))   # aisle 0.90 m
        self.assertTrue(any(p.startswith("pd-hang-1") for p in res["routes"]["problems"]), res["routes"])

    def test_a_door_running_into_a_wall_is_caught(self):
        # the real defect: the dressing door at x 22.10 ran 153 mm into the 0.2 m south wall
        orig = F.VP.DRESSING_DOOR_X
        try:
            F.VP.DRESSING_DOOR_X = 22.10
            self.assertIn("door parents-bed/parents-dressing runs 153 mm into a wall", F.check()["doors"]["problems"])
        finally:
            F.VP.DRESSING_DOOR_X = orig

    def test_a_door_without_a_span_is_cut_from_its_own_wall(self):
        # the cinema door (no span in the spec) defaulted to "h" and stayed walled up
        lay = R.design("D1")
        walls = F._walls(F.RS.build(lay), "B")
        self.assertFalse(any(F._ov((3.12, -22.4, 3.13, -21.8), w) for w in walls))


class ChecksFailOnRealMistakes(unittest.TestCase):
    def test_three_recliners_close_the_store(self):
        # first draft: three recliners across the 2.99 m cinema cut off the store under the ramp
        def m(items, ids):
            items[:] = [i for i in items if not i["id"].startswith("cinema-seat")]
            for n, yy in enumerate((-23.05, -22.1, -21.15)):
                items.append(F.item("cinema-seat-%d" % n, "cinema", "recliner", 5.875, yy, -90, h=1.0,
                                    why="x", views="cinema-screen", level="B"))
        self.assertTrue(any("store-ramp" in p for p in _run(m)["routes"]["problems"]))

    def test_coffee_table_too_close(self):
        # 440 mm from the sofa front, where 457 is needed
        res = _run(lambda items, ids: ids["lounge-coffee"].update(
            cy=ids["lounge-sofa"]["cy"] + ids["lounge-sofa"]["d"] / 2 + 0.44 + ids["lounge-coffee"]["d"] / 2))
        self.assertEqual(res["clearances"]["status"], "fail")

    def test_bedside_table_outside_zone_a_is_refused(self):
        res = _run(lambda items, ids: ids["pb-bedside"].update(cy=ids["pb-bedside"]["cy"] + 0.9))  # along the bed
        self.assertTrue(any("pb-bed" in p for p in res["clearances"]["problems"]))

    def test_bedside_table_in_zone_a_is_allowed(self):
        self.assertEqual(F.check()["clearances"]["status"], "pass")

    def test_door_swing(self):
        res = _run(lambda items, ids: ids["kb-wardrobe"].update(cx=16.689))      # in front of the kids B door
        self.assertEqual(res["doors"]["status"], "fail")

    def test_the_parents_entry_must_stay_passable(self):
        # a pocket door has no swing zone, but its approach is a route node: a chest in the entry blocks it
        res = _run(lambda items, ids: items.append(F.item("chest", "parents-entry", "sideboard", 18.977, -26.95, 0,
                                                          w=0.9, d=0.45, h=0.8, why="x", level="GF")))
        self.assertTrue(any("door corridor/parents-entry" in p or "parents-entry" in p
                            for p in res["routes"]["problems"]), res["routes"])

    def test_tall_piece_in_front_of_a_window(self):
        res = _run(lambda items, ids: ids["kb-wardrobe"].update(cx=16.9, cy=-23.866, rot=180))
        self.assertEqual(res["windows"]["status"], "fail")

    def test_sink_landing(self):
        res = _run(lambda items, ids: ids["k-run"]["modules"].__setitem__(0, ("counter", 0.3)))
        self.assertTrue(any("sink landing" in p for p in res["kitchen"]["problems"]))

    def test_dishwasher_far_from_the_sink(self):
        def m(items, ids):
            ids["dk-run"]["modules"] = [("counter", 0.5), ("sink", 0.8), ("counter", 1.0), ("dw", 0.6), ("range", 0.9)]
        self.assertTrue(any("dishwasher" in p for p in _run(m)["kitchen"]["problems"]))

    def test_hob_landing(self):
        res = _run(lambda items, ids: ids["k-island"].update(modules=[("counter", 0.2), ("hob", 0.9), ("counter", 1.4)]))
        self.assertTrue(any("hob landing" in p for p in res["kitchen"]["problems"]))

    def test_stools_need_room_to_walk_past(self):
        # first draft: the seated side faced the cook's aisle; with the stools toward the tall wall the island
        # must keep 1118 mm behind them (card nkba-seating-walk-past-1118): 0.3 m nearer fails
        res = _run(lambda items, ids: ids["k-island"].update(cy=-26.46))
        self.assertTrue(any("k-island back 1118" in p for p in res["clearances"]["problems"]), res["clearances"])

    def test_viewing_distance(self):
        res = _run(lambda items, ids: ids["lounge-tv"].update(screen_in=55))        # 2.78 m from a 55 in screen
        self.assertEqual(res["viewing"]["status"], "fail")

    def test_piece_outside_its_room(self):
        res = _run(lambda items, ids: ids["kb-desk"].update(cy=-23.4))
        self.assertEqual(res["inside_room"]["status"], "fail")

    def test_piece_on_a_column(self):
        res = _run(lambda items, ids: ids["kb-desk"].update(cx=15.0))
        self.assertEqual(res["columns"]["status"], "fail")


if __name__ == "__main__":
    unittest.main()
