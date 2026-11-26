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


class SlimHeadboardLedges(unittest.TestCase):
    """Client 2026-11-25: a ~50 mm bed-mounted headboard panel with a matched pair of floating ledges replaces the bedside tables.
    The earlier built-out wall failed the foot route (0.60-0.65 m), so these pin what makes the slim version pass."""
    ITEMS = {i["id"]: i for i in F.layout(LAY)}

    def test_no_bedside_table_and_a_matched_pair_of_ledges(self):
        self.assertNotIn("pb-bedside", self.ITEMS)
        w, e = self.ITEMS["pb-ledge-w"], self.ITEMS["pb-ledge-e"]
        self.assertEqual((w["w"], w["d"], w["h"]), (e["w"], e["d"], e["h"]))
        self.assertAlmostEqual(w["cx"] + e["cx"], 2 * self.ITEMS["pb-bed"]["cx"], 6)           # mirrored about the bed

    def test_ledge_top_is_the_mattress_top_and_nothing_stands_on_legs(self):
        from archpipe.furniture import build_furniture
        bed = self.ITEMS["pb-bed"]
        comps = VR.generated_components(bed, "bed_double", 1.05)
        mattress_top = max(v[2] for c in comps if c["name"].endswith(":mattress") for v in c["vertices_mm"]) / 1000.0
        self.assertAlmostEqual(self.ITEMS["pb-ledge-e"]["h"], mattress_top, 3)
        names = [n for n, _ in F3.body(self.ITEMS["pb-ledge-e"])]
        self.assertFalse({"leg", "plinth", "handle", "pull"} & set(names), names)

    def test_headboard_is_a_50_mm_panel_and_the_bed_did_not_move(self):
        bed = self.ITEMS["pb-bed"]
        hb = dict(F3.body(bed))["headboard"]
        self.assertAlmostEqual(hb[4] - hb[1], 0.05, 6)
        self.assertEqual((bed["cx"], bed["cy"]), (20.33, -25.591))                             # moved 0 mm of the 50 allowed

    def test_west_ledge_leaves_the_entry_passage_its_750(self):
        w = F.footprint(self.ITEMS["pb-ledge-w"])
        west_wall = max(x1 for x0, y0, x1, y1 in F._walls(F.RS.build(LAY), "GF") if abs(x0 - 18.377) < 1e-3)
        self.assertGreaterEqual(w[0] - west_wall, F.BEDROOM_ROUTE)                              # 0.773 m clear, 0.75 required

    def test_a_0p30_ledge_would_have_read_below_750_on_the_grid(self):
        # the first draft: 0.30 wide left 0.753 m, which the 20 mm path grid reads as 0.746 m < 0.75 (negative control)
        items = [dict(i, w=0.30, cx=i["cx"] - 0.01) if i["id"] == "pb-ledge-w" else i
                 for i in F.layout(LAY)]
        r = next(r for r in C.routes(LAY, items=items) if "parents-bed" in r["cluster"] and r["to"] != "its own approach")
        self.assertLess(r["achieved"], F.BEDROOM_ROUTE, C.describe(r))     # 0.746; the gate tolerates half a cell, a design should not lean on it

    def test_door_approach_to_the_dressing_room_stays_clear(self):
        r = next(r for r in C.routes(LAY) if r["frm"] == "door parents-bed/parents-dressing" and r["to"] == "its own approach"
                 and "parents-bed" in r["cluster"])
        self.assertTrue(r["ok"], C.describe(r))

    def test_dressed_route_with_the_evaluated_cloth_as_obstacles(self):
        # evaluated cloth (duvet, throw, parked curtain stacks) from the Blender build; see knowledge/flythrough
        r = next(r for r in C.routes(LAY, dressed=True) if "parents-bed" in r["cluster"] and r["to"].startswith("door corridor"))
        self.assertGreaterEqual(r["achieved"], F.BEDROOM_ROUTE, C.describe(r))


class DressingOverhang(unittest.TestCase):
    def test_props_sit_wholly_on_their_supports(self):
        self.assertEqual(VR.dressing_overhang_violations(VR.props(LAY), LAY), [])

    def test_books_with_origin_at_the_top_centre_overhang_into_the_door(self):
        # the pre-fix placement (then on the bedside, now the same mistake on the east ledge): scale 1, origin at the top's
        # centre; the set reaches x 21.84, the door opening starts 21.497
        old = {"id": "bedside-books", "asset": "book_encyclopedia_set_01", "position": [21.305, -26.391, 0.525],
               "rotation_deg": [0, 0, 0.0], "scale": 1.0}
        bad = VR.dressing_overhang_violations([old], LAY)
        self.assertEqual(len(bad), 1, bad)
        self.assertIn("pb-ledge-e", bad[0])
        self.assertGreater(LAND.prop_world_box(old["asset"], old["position"], old["rotation_deg"], 1.0)[3], 21.497)


if __name__ == "__main__":
    unittest.main()
