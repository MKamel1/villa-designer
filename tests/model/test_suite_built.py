"""The parents' suite as BUILT (client FINAL 2026-11-26: R3 plus the annexed corridor end), checked on the design model.
Each test names what it would catch; the negative controls prove the guard bites on the old geometry."""
import collections
import unittest

from archpipe import model
from archpipe.concept import villa_furnish as F
from archpipe.concept import villa_parking as VP
from archpipe.concept import villa_r11 as R
from archpipe.model import circulation as C

EL = None
LAY = None


def setUpModule():
    global EL, LAY
    EL = {e.id: e for e in model.load("D1")}
    LAY = R.design("D1")


class Annexe(unittest.TestCase):
    def test_suite_door_across_the_corridor_just_past_kids_b(self):
        d = EL["door-GF-corridor-suite-vestibule"]
        self.assertAlmostEqual(d.placement[0], 17450.0)
        self.assertEqual(d.params["width_mm"], 800.0)                       # 0.80 leaf: a 0.90 leaf shows 31 bedroom points to the corridor
        self.assertEqual(d.params["swing_into"], "suite-vestibule")          # never out across kids-b's approach
        self.assertEqual(d.params["hinge_side"], "north")
        self.assertIs(d.params["self_closing"], True)                          # second layer, not the first
        self.assertIs(EL["door-GF-parents-bed-parents-dressing"].params["self_closing"], False)

    def test_kids_b_door_is_untouched_public_and_swings_into_kids_b(self):
        d = EL["door-GF-corridor-kids-b"]
        self.assertEqual((d.placement[0], d.placement[1], d.params["width_mm"]), (16689.0, -27371.0, 900.0))
        self.assertEqual(d.params["swing_into"], "kids-b")
        jamb_east = 16689.0 + 450.0
        suite_wall_face = 17450.0 - 50.0
        self.assertGreaterEqual(suite_wall_face - jamb_east, 250.0)          # 0.26 m of corridor between kids-b's jamb and the suite wall
        approach = (16.239, -27.671, 17.139, -27.371)                         # its 0.30 m approach strip, corridor side
        for it in F.layout(LAY):                                               # nothing of the suite stands in it
            self.assertFalse(F._ov(F.footprint(it), approach), it["id"])
        sp = F.RS.build(LAY)
        self.assertFalse(any(F._ov(w, approach) for w in F._walls(sp, "GF") if w[1] > -27.671 and w[3] < -27.371 and abs(w[0] - 17.4) < 0.06))

    def test_corridor_end_is_the_vestibule_with_storage_and_a_wide_passage(self):
        sv = LAY["rooms"]["suite-vestibule"]
        self.assertTrue(sv["suite"])
        st = next(i for i in F.layout(LAY) if i["id"] == "sv-store")
        self.assertEqual(st["room"], "suite-vestibule")
        self.assertLessEqual(st["d"], 0.13 + 1e-9)
        r = [x for x in C.routes(LAY, level="GF") if x["cluster"] == "suite-vestibule"]
        self.assertGreaterEqual(len(r), 3)
        for x in r:
            self.assertTrue(x["ok"], C.describe(x))
        door_to_door = next(x for x in r if x["to"].startswith("door suite-vestibule/parents-entry") or x["frm"].startswith("door suite-vestibule/parents-entry"))
        self.assertGreaterEqual(door_to_door["achieved"], F.BODY - 1e-9)      # 0.914 m path of travel (card mitton-path-of-travel-min)

    def test_negative_control_a_deep_cabinet_would_close_the_passage(self):
        items = [dict(i, d=0.50) if i["id"] == "sv-store" else i for i in F.layout(LAY)]
        bad = [x for x in C.routes(LAY, items, level="GF") if x["cluster"] == "suite-vestibule" and not x["ok"]]
        self.assertTrue(bad, "a 0.50 m deep cabinet must fail the 0.914 m passage")

    def test_kids_escape_route_never_passes_through_the_suite(self):
        """Escape = door graph from each kids room to the GF core door. Removing every suite room must leave it intact, and no
        suite room may be a link between two non-suite rooms."""
        links = LAY["links"]
        suite = {r for r, v in LAY["rooms"].items() if v.get("suite")}
        self.assertIn("suite-vestibule", suite)
        ends = {a for a, b in links} | {b for a, b in links}
        adj = collections.defaultdict(set)
        for a, b in links:
            if a not in suite and b not in suite:
                adj[a].add(b); adj[b].add(a)
        exit_room = next(r for r, lv, seg in LAY["entries"] if lv == "GF")
        for kid in ("kids-a", "kids-b"):
            seen, todo = {kid}, [kid]
            while todo:
                for n in adj[todo.pop()] - seen:
                    seen.add(n); todo.append(n)
            self.assertIn(exit_room, seen, kid + " cannot reach the GF exit without the suite")
        # no suite room is a thoroughfare: each has links only to suite rooms or to ONE public room
        for s in suite:
            public = {b if a == s else a for a, b in links if s in (a, b) and (b if a == s else a) not in suite}
            self.assertLessEqual(len(public), 1, (s, public))

    def test_negative_control_a_door_from_kids_b_into_the_vestibule_would_be_caught(self):
        links = LAY["links"] + [["kids-b", "suite-vestibule"]]
        public = {b if a == "suite-vestibule" else a for a, b in links if "suite-vestibule" in (a, b)
                  and (b if a == "suite-vestibule" else a) not in {r for r, v in LAY["rooms"].items() if v.get("suite")}}
        self.assertGreater(len(public), 1)


class DressingDoor(unittest.TestCase):
    def test_new_door_at_the_lobby_end_hinged_on_the_east_jamb(self):
        d = EL["door-GF-parents-bed-parents-dressing"]
        self.assertAlmostEqual(d.placement[0], 19977.0)
        self.assertEqual((d.params["hinge_side"], d.params["swing_into"]), ("east", "parents-dressing"))
        self.assertEqual(d.params["hinge_xy_mm"], [20377.0, -26641.0])

    def test_old_head_wall_door_is_built_in(self):
        wall = EL["wall-GF-int-24"]
        doors = [e for e in EL.values() if e.kind == "door" and e.level == "GF" and abs(e.placement[1] + 26641.0) < 1.0]
        self.assertEqual([e.id for e in doors], ["door-GF-parents-bed-parents-dressing"])
        for e in doors:
            self.assertLess(e.placement[0], 21000.0)                          # nothing left at the old east position 21.897

    def test_hers_is_1870_on_the_freed_wall_and_his_is_unchanged(self):
        its = {i["id"]: i for i in F.layout(LAY)}
        h = its["pd-hang-1"]
        self.assertAlmostEqual(h["w"], 1.87)
        x0, _, x1, _ = F.footprint(h)
        self.assertAlmostEqual(x0, 20.477, places=3)
        self.assertAlmostEqual(x1, 22.347, places=3)
        self.assertEqual(h["rot"], 180)
        self.assertAlmostEqual(its["pd-hang-2"]["w"], 1.346, places=3)           # his run: unchanged
        self.assertEqual([m for m, _ in h["modules"]], ["hat-shelf", "drawers", "double-hang", "long-hang"])
        self.assertAlmostEqual(sum(w for _, w in h["modules"]), 1.87)


class Bedroom(unittest.TestCase):
    def test_bed_turned_head_to_the_window_wall_and_centred(self):
        b = {i["id"]: i for i in F.layout(LAY)}["pb-bed"]
        x0, y0, x1, y1 = F.footprint(b)
        PB = F.clear_rect(LAY, "parents-bed")
        self.assertEqual(b["rot"], 180)
        self.assertAlmostEqual(y1, PB[3])                                      # head on the window wall
        self.assertAlmostEqual((x0 + x1) / 2, (PB[0] + PB[2]) / 2)             # centred on the room
        self.assertAlmostEqual(x0 - PB[0], PB[2] - x1)                         # 1160 each side

    def test_head_panel_is_low_and_stops_at_the_sill(self):
        from archpipe.furniture import JOINERY_BED as J
        self.assertEqual(J["panel_z1"], 900.0)
        win = next(e for e in EL.values() if e.id == "window-GF-parents-bed-6")
        self.assertEqual(win.params["sill_mm"], 900.0)

    def test_cove_on_the_slat_wall_not_the_glass(self):
        from archpipe.concept import villa_lighting as VL
        cove = next(f for f in VL.design(LAY) if f.id == "COVE-parents-bed-01")
        PB = F.clear_rect(LAY, "parents-bed")
        self.assertAlmostEqual(cove.x, PB[0] + 0.12)
        self.assertGreater(cove.aim[0], 0)                                     # aims into the room from the west wall, not at the head wall
        self.assertAlmostEqual(cove.along[1] ** 2, 1.0)                         # runs along y, the slat wall's length

    def test_reading_lights_on_arms_clamped_to_the_panel_have_a_power_route(self):
        from archpipe.concept import villa_lighting as VL
        b = F.footprint({i["id"]: i for i in F.layout(LAY)}["pb-bed"])
        arms = [f for f in VL.design(LAY) if f.kind == "WALL-READ" and f.room == "parents-bed"]
        self.assertEqual(len(arms), 2)
        for a in arms:
            self.assertGreater(a.y, b[3] - 0.25)                               # at the head end, over the panel
            self.assertAlmostEqual(a.z, 1.30)
        from archpipe.electrical import villa, placement
        h = villa.load_villa()
        devs = placement.place_devices(h)
        sup = [d for d in devs if d.kind == "socket_selv" and d.room == "parents-bed"]
        self.assertEqual(len(sup), 1)
        self.assertEqual(sorted(sup[0].params["lamps"]), sorted("lum-" + a.id for a in arms))
        self.assertAlmostEqual(sup[0].x, 20437.0, delta=1.0)                  # centred behind the panel
        self.assertLess(sup[0].z, 900.0)                                        # below the sill: in the wall, not in the glass
        self.assertEqual(placement.clearance_violations(h, devs), [])

    def test_open_trays_keep_750_past_the_vanity(self):
        """Both trays pulled out 0.25 m: the widest body that gets from the dressing door to the head end is at least 0.75 m
        (card ukadm-bedroom-route-750). With the vanity where it was (y -25.3) it is 0.66 m: the guard bites."""
        for y0, ok in ((F.PB_VANITY_Y0, True), (-25.3, False)):
            old = F.PB_VANITY_Y0
            F.PB_VANITY_Y0 = y0
            try:
                items = C.with_trays(F.layout(LAY) if y0 == old else F._layout(LAY), 0.25)
                w = _east_head_width(items)
            finally:
                F.PB_VANITY_Y0 = old
            self.assertEqual(w >= F.BEDROOM_ROUTE - 0.01, ok, (y0, w))

    def test_every_route_incl_trays_open_meets_its_figure(self):
        for pull in (0.0, 0.25):
            items = C.with_trays(F.layout(LAY), pull) if pull else None
            bad = [C.describe(r) for r in C.routes(LAY, items, level="GF") if not r["ok"]]
            self.assertEqual(bad, [], pull)


def _east_head_width(items):
    import numpy as np
    sp = F.RS.build(LAY)
    cl = F._cluster(LAY, "parents-bed")
    rects = [LAY["rooms"][c]["rect"] for c in cl]
    x0, y0 = min(q[0] for q in rects), min(q[1] for q in rects)
    x1, y1 = max(q[2] for q in rects), max(q[3] for q in rects)
    cell = C.CELL
    nx, ny = int((x1 - x0) / cell) + 1, int((y1 - y0) / cell) + 1
    X, Y = np.meshgrid(x0 + (np.arange(nx) + .5) * cell, y0 + (np.arange(ny) + .5) * cell, indexing="ij")
    free = np.zeros((nx, ny), bool)
    for a, b, c, d in rects:
        free |= (X >= a) & (X < c) & (Y >= b) & (Y < d)
    obst = [F.footprint(i) for i in C.staged_items(LAY, items) if i["room"] in cl and i["h"] >= 0.3] + F._columns() + F._walls(sp, "GF")
    for a, b, c, d in obst:
        free &= ~((X > a) & (X < c) & (Y > b) & (Y < d))
    clear = np.full((nx, ny), np.inf)
    for a, b, c, d in obst:
        clear = np.minimum(clear, np.hypot(np.maximum(np.maximum(a - X, X - c), 0), np.maximum(np.maximum(b - Y, Y - d), 0)))
    ok = free & (clear > 0)
    start = (np.hypot(np.maximum(np.maximum(19.577 - X, X - 20.377), 0), np.maximum(np.maximum(-26.9 - Y, Y + 26.5), 0)) < 0.2) & ok
    best = C._widest(clear, ok, start, cell)
    m = (X >= 21.7) & (X <= 22.2) & (Y >= -24.3) & (Y <= -23.9) & (best > 0)
    return 2 * float(best[m].max()) if m.any() else 0.0


if __name__ == "__main__":
    unittest.main()
