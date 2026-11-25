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


class DressingOverhang(unittest.TestCase):
    def test_bedside_books_sit_wholly_on_the_bedside(self):
        self.assertEqual(VR.dressing_overhang_violations(VR.props(LAY), LAY), [])

    def test_books_with_origin_at_the_bedside_centre_overhang_into_the_door(self):
        # the pre-fix placement: scale 1, origin at the top's centre; the set reaches x 21.84, the door opening starts 21.497
        old = {"id": "bedside-books", "asset": "book_encyclopedia_set_01", "position": [21.305, -26.391, 0.55],
               "rotation_deg": [0, 0, 0.0], "scale": 1.0}
        bad = VR.dressing_overhang_violations([old], LAY)
        self.assertEqual(len(bad), 1, bad)
        self.assertIn("pb-bedside", bad[0])
        self.assertGreater(LAND.prop_world_box(old["asset"], old["position"], old["rotation_deg"], 1.0)[3], 21.497)


if __name__ == "__main__":
    unittest.main()
