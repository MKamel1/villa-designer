"""Staged-furniture circulation (src/archpipe/model/circulation.py). Positive: the pre-fix parents' bedroom, with the
vanity chair pulled out, fails. Negative: the tucked design and every other cluster stay quiet."""
import unittest

from archpipe.concept import villa_furnish as F
from archpipe.concept import villa_furnish3d as F3
from archpipe.concept import villa_landscape as LAND
from archpipe.concept import villa_render as VR
from archpipe.model import circulation as C

LAY = F.R.design("D1")


def _items(**vanity):
    return [dict(i, **vanity) if i["id"] == "pb-vanity" else i for i in F.layout(LAY)]


class StagedCirculation(unittest.TestCase):
    def test_pulled_out_vanity_chair_pinches_the_way_to_the_dressing_door(self):
        bad = C.pinches(LAY, _items(chair_pulled_out=True))
        self.assertEqual(len(bad), 1, [C.describe(r) for r in bad])
        r = bad[0]
        self.assertIn("parents-bed", r["cluster"])
        self.assertEqual(r["required"], F.BEDROOM_ROUTE)          # card ukadm-bedroom-route-750
        self.assertLess(r["achieved"], 0.60)                       # measured 0.56 m: bed side 21.13 -> chair 21.697

    def test_tucked_vanity_stool_leaves_the_route(self):
        r = next(r for r in C.routes(LAY) if "parents-bed" in r["cluster"] and r["to"] != "its own approach")
        self.assertTrue(r["ok"], C.describe(r))
        self.assertGreaterEqual(r["achieved"], F.BEDROOM_ROUTE)

    def test_whole_villa_has_no_pinch_as_staged(self):
        self.assertEqual([C.describe(r) for r in C.pinches(LAY)], [])
        self.assertGreater(len(C.routes(LAY)), 30)                 # it did look at every door approach

    def test_tucked_chair_projects_only_its_back(self):
        v = next(i for i in F.layout(LAY) if i["id"] == "pb-vanity")
        fx0, fy0, fx1, fy1 = F.footprint(v)
        for _, parts in F3.extras(v):
            for _, b in parts:
                x0, y0, _, x1, y1, _ = F3.to_world(v, b)
                m = 0.03 + 1e-6                      # only the back (0.03 m) may stand proud of the top's front edge
                self.assertTrue(fx0 - m <= x0 and x1 <= fx1 + m and fy0 - m <= y0 and y1 <= fy1 + m)

    def test_a_chair_elsewhere_is_not_flagged(self):
        # negative: pulling out a desk chair where there is room (kids-b desk) changes nothing
        items = [dict(i, chair_pulled_out=True) if i["id"] == "kb-desk" else i for i in F.layout(LAY)]
        self.assertEqual(C.pinches(LAY, items), [])


class JoineryBedTrays(unittest.TestCase):
    """Client 2026-11-26: a joinery queen bed with a hidden pull-out tray in each side rail replaces the floating ledges, which
    stood in the entry opening (0.77 m left) and 9 cm from the dressing door. Nothing may project when closed; open, the way
    round the bed and both doors stay clear."""
    ITEMS = {i["id"]: i for i in F.layout(LAY)}
    BASE = F.layout(LAY)

    def _route(self, items, dressed=False):
        return next(r for r in C.routes(LAY, items=items, dressed=dressed)
                    if "parents-bed" in r["cluster"] and r["to"].startswith("door corridor") and r["frm"].startswith("door parents-bed"))

    def test_no_ledge_no_bedside_and_the_bed_is_where_it_was(self):
        self.assertFalse({"pb-ledge-w", "pb-ledge-e", "pb-bedside"} & set(self.ITEMS))
        bed = self.ITEMS["pb-bed"]
        self.assertEqual((bed["cx"], bed["cy"], bed["w"], bed["d"]), (20.33, -25.591, 1.6, 2.0))     # mattress 1600 x 2000, unmoved
        self.assertTrue(bed["joinery"])

    def test_mattress_is_1600_by_2000_with_its_top_at_0p525(self):
        m = dict(F3.body(self.ITEMS["pb-bed"]))["mattress"]
        self.assertEqual((round(m[3] - m[0], 4), round(m[4] - m[1], 4), round(m[5], 4)), (1.6, 2.0, 0.525))

    def test_closed_nothing_projects_beyond_the_bed_footprint_and_no_handle(self):
        spec = next(s for s in F3.spec(LAY, self.BASE) if s["mark"] == "pb-bed")
        fx0, fy0, fx1, fy1 = F.footprint(self.ITEMS["pb-bed"])
        e = spec["envelope"]
        for got, lim in ((e[0], fx0), (e[1], fy0), (-e[3], -fx1), (-e[4], -fy1)):
            self.assertGreaterEqual(got, lim - 1e-6)
        names = set(spec["parts"])
        self.assertFalse({"handle", "pull", "knob"} & names, names)
        self.assertEqual({"tray-front-w", "tray-front-e"} - names, set())

    def test_tray_fronts_are_flush_with_the_rail_faces(self):
        parts = dict(F3.body(self.ITEMS["pb-bed"]))
        self.assertAlmostEqual(parts["tray-front-w"][0], -0.8, 6)
        self.assertAlmostEqual(parts["tray-front-e"][3], 0.8, 6)

    def test_headboard_is_50_mm_and_floats_on_the_mattress_top(self):
        parts = F3.body(self.ITEMS["pb-bed"])
        for n, b in parts:
            if n.startswith("headboard-frame"):
                self.assertAlmostEqual(b[4] - b[1], 0.05, 6)
                self.assertGreaterEqual(b[2], 0.525 - 1e-9)
        self.assertAlmostEqual(max(b[5] for n, b in parts if n.startswith("headboard")), 1.35, 6)

    def test_open_trays_leave_the_route_and_both_door_approaches_their_750(self):
        items = C.with_trays(self.BASE, 0.25)
        r = self._route(items)
        self.assertGreaterEqual(r["achieved"], F.BEDROOM_ROUTE, C.describe(r))                 # 0.766 m with both trays out
        for frm in ("door parents-bed/parents-dressing", "door corridor/parents-entry"):
            a = next(x for x in C.routes(LAY, items=items) if x["frm"] == frm and x["to"] == "its own approach" and "parents-bed" in x["cluster"])
            self.assertTrue(a["ok"], C.describe(a))

    def test_the_first_draft_window_would_have_pinched_the_vanity_corner(self):
        # negative control from the real first draft: trays 0.10 m further down the bed (v 0.45-0.90), pulled 0.25 m,
        # left 0.708 m between the east tray corner and the vanity: the gate must catch it
        shifted = [dict(i, cy=i["cy"] + 0.10) if i["id"].startswith("pb-tray-open") else i for i in C.with_trays(self.BASE, 0.25)]
        self.assertLess(self._route(shifted)["achieved"], F.BEDROOM_ROUTE)

    def test_closed_trays_change_nothing(self):
        self.assertAlmostEqual(self._route(self.BASE)["achieved"], self._route(C.with_trays(self.BASE, 0.0))["achieved"], 6)

    def test_dressed_route_with_the_evaluated_cloth_as_obstacles(self):
        # evaluated cloth (duvet, throw, parked curtain stacks) from the Blender build; see knowledge/flythrough
        r = next(r for r in C.routes(LAY, dressed=True) if "parents-bed" in r["cluster"] and r["to"].startswith("door corridor"))
        self.assertGreaterEqual(r["achieved"], F.BEDROOM_ROUTE, C.describe(r))


    def test_dressed_route_with_both_trays_out(self):
        r = self._route(C.with_trays(self.BASE, 0.25), dressed=True)
        self.assertGreaterEqual(r["achieved"], F.BEDROOM_ROUTE, C.describe(r))                 # 0.766 m: cloth and both trays out at once


class DressingOverhang(unittest.TestCase):
    def test_props_sit_wholly_on_their_supports(self):
        self.assertEqual(VR.dressing_overhang_violations(VR.props(LAY), LAY), [])

    def test_books_with_origin_at_the_top_centre_overhang_the_top(self):
        # the same mistake as the pre-fix bedside books (scale 1, origin at the top's centre, 0.357 m past the top into the dressing
        # door's opening), reproduced on the vanity, the one piece in the room that still carries a top: the set hangs past its east edge
        old = {"id": "vanity-books", "asset": "book_encyclopedia_set_01", "position": [22.30, -24.8, 0.75],
               "rotation_deg": [0, 0, 0.0], "scale": 1.0}
        bad = VR.dressing_overhang_violations([old], LAY)
        self.assertEqual(len(bad), 1, bad)
        self.assertIn("pb-vanity", bad[0])


if __name__ == "__main__":
    unittest.main()
