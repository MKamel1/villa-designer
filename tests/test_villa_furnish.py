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
        self.assertEqual(len(res), 9)

    def test_every_item_has_a_reason_and_a_catalogue_type(self):
        for it in F.layout():
            self.assertTrue(it["why"], it["id"])
            cat.get(it["type"])

    def test_the_route_check_really_examines_rooms(self):
        # the kids A beds' shared gap is a node: closing it must fail the route check (the first draft had 0.909 m)
        res = _run(lambda items, ids: ids["ka-bed-2"].update(cy=-25.85))
        self.assertTrue(any("ka-bed-1" in p for p in res["routes"]["problems"]), res["routes"])


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
        res = _run(lambda items, ids: ids["lounge-coffee"].update(cy=-25.62))      # the first draft: 452 mm
        self.assertEqual(res["clearances"]["status"], "fail")

    def test_bedside_table_outside_zone_a_is_refused(self):
        res = _run(lambda items, ids: ids["pb-bedside-1"].update(cx=19.3))       # moved along the bed side
        self.assertTrue(any("pb-bed" in p for p in res["clearances"]["problems"]))

    def test_bedside_table_in_zone_a_is_allowed(self):
        self.assertEqual(F.check()["clearances"]["status"], "pass")

    def test_door_swing(self):
        res = _run(lambda items, ids: ids["kb-wardrobe"].update(cx=16.689))      # in front of the kids B door
        self.assertEqual(res["doors"]["status"], "fail")

    def test_pocket_door_is_what_lets_the_parents_bed_fit(self):
        orig = dict(F.DOOR_TYPES)
        try:
            F.DOOR_TYPES.clear()
            self.assertTrue(any("pb-bedside-1" in p for p in F.check()["doors"]["problems"]))
        finally:
            F.DOOR_TYPES.update(orig)

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
