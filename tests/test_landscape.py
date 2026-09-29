"""Landscape guards exercised on the D1 placement and frozen draft failures."""
import unittest

from archpipe.concept import villa_landscape as L
from archpipe.concept import revit_spec as RS
from archpipe.concept import villa_r11 as R


class LandscapeGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lay = R.design("D1")
        cls.meshes, cls.props, cls.notes, cls.plan = L.build(RS.build(cls.lay), cls.lay)
        cls.rooms = L.garden_level_rooms(cls.lay)

    def test_old_native_jacaranda_enters_building(self):
        draft = dict(id="draft-north-jacaranda", asset="jacaranda_tree",
                     position=[18.30, -21.55, L.GROUND], rotation_deg=[0, 0, 0], scale=1.0)
        self.assertTrue(any("building footprint" in why for _, why in L.extent_violations([draft])))
        self.assertEqual(L.extent_violations(self.props, self.rooms), [])

    def test_old_north_bed_enters_basement_room(self):
        draft = dict(id="draft-searsia", asset="searsia_lucida",
                     position=[13.25, -21.65, L.GROUND+.38], rotation_deg=[0, 0, 0], scale=.7)
        self.assertTrue(any("dirty-kitchen" in why for _, why in L.extent_violations([draft], self.rooms)))
        self.assertEqual(L.extent_violations(self.props, self.rooms), [])

    def test_top_edge_and_rail_line(self):
        bad = dict(id="top-edge", asset="sf_hibiscus", position=[12.72, -21.7, 0],
                   rotation_deg=[0, 0, 0], scale=.7, zone="top")
        self.assertTrue(L.extent_violations([bad], self.rooms))
        self.assertTrue(L.object_extent_violations([dict(id="rail", zone="top",
                                                         rect=(6.9, -22.5, 7.4, -22.0))]))
        self.assertEqual(L.object_extent_violations(self.plan["objects"], self.rooms), [])

    def test_route_real_furniture_footprint_and_quiet(self):
        # A full-sized teak sofa, as in the discarded D1 outdoor layout,
        # reproduces the obstruction when set across the living door approach.
        sofa = dict(id="draft-teak-sofa", rect=(24.0, -26.25, 26.1, -25.40))
        self.assertIn(("draft-teak-sofa", "living-east"), L.route_violations([sofa]))
        self.assertEqual(L.route_violations(self.props + self.plan["objects"]), [])
        self.assertEqual(L.route_violations([dict(id="clear", rect=(26.0, -28.0, 26.5, -27.5))]), [])

    def test_spacing_real_three_tenths_spread_and_quiet(self):
        a = dict(id="a", bed="east", layer="mid", spread_m=.9, center=(27, -25))
        b = dict(id="b", bed="east", layer="mid", spread_m=.9, center=(27, -24.73))
        self.assertEqual(L.spacing_violations([a, b]), [("a", "b", .27, .72)])
        self.assertEqual(L.spacing_violations(self.plan["plants"]), [])
        self.assertEqual(L.spacing_violations([a, dict(b, center=(27, -24.2))]), [])

    def test_swing_envelope_and_quiet(self):
        swing = self.plan["swing"]
        x0, y0, x1, y1 = L._rect(swing)
        chair = dict(id="draft-chair", rect=(x1+.05, y0, x1+.25, y1))
        self.assertTrue(L.swing_violations(swing, [chair]))
        self.assertEqual(L.swing_violations(swing, [swing] + self.plan["objects"]), [])

    def test_source_labels_and_drift_counts(self):
        for p in self.plan["plants"]:
            self.assertIn("care: https://", p["label"])
            self.assertIn("ASSUMED", p["label"] if p["species"] == "Duranta erecta" else "ASSUMED")
        for bed in ("north", "west", "east", "south", "top-deck", "top-roof"):
            self.assertEqual(sum(p["bed"] == bed for p in self.plan["plants"]), 3)
        self.assertEqual(len([p for p in self.props if p["id"].startswith("landscape-tree-")]), 3)
        self.assertEqual(len([p for p in self.props if p["id"].startswith("landscape-top-bench-")]), 2)
        self.assertFalse(any("lounge" in m["label"].lower() for m in self.meshes))
        self.assertEqual(len([m for m in self.meshes if m["id"].startswith("landscape-sofa-")]), 1)
        self.assertTrue(any("artificial-grass" == m["material"] for m in self.meshes))
        self.assertEqual(set(self.plan["paths"]), {"dining", "living-north", "living-east", "lounge-west", "study"})


if __name__ == "__main__":
    unittest.main()
