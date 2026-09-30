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

    def test_source_labels_and_bed_population(self):
        # Every plant carries a real care URL (round3 plant-palette.json or the
        # supplementary EXTRA_CARE fetch, both real sources -- never invented).
        for p in self.plan["plants"]:
            self.assertIn("care: https://", p["label"])
        # The v17 design's thin "3 per bed, one species" beds are gone: every
        # ground bed now carries a full layered border (>= 7 plants for the
        # 3-layer beds; south's 2-layer bed still carries 7 given its accent).
        counts = {bed: sum(p["bed"] == bed for p in self.plan["plants"])
                  for bed in ("north", "east", "west", "south")}
        for bed, n in counts.items():
            self.assertGreaterEqual(n, 7, "%s bed only has %d plants" % (bed, n))
        # Two ground-level shade specimens (east, south) plus the potted
        # lemon (landscape-tree-*); the top-garden olive is a separate
        # landscape-top-olive prop. None is the old mislabelled tree_small_02
        # stand-in (see test_standin_real_and_old_mislabelled_tree_fails).
        self.assertEqual(len([p for p in self.props if p["id"].startswith("landscape-tree-")]), 3)
        self.assertTrue(any(p["id"] == "landscape-top-olive" for p in self.props))
        # v25 defect: two near-touching benches read as one 3.58 x 1.66 m slab; one real bench now (see
        # test_bench_real_seat_height_and_old_slab_fails for the height/length guard itself).
        self.assertEqual(len([p for p in self.props if p["id"].startswith("landscape-top-bench-")]), 1)
        self.assertFalse(any("lounge" in m["label"].lower() for m in self.meshes))
        self.assertEqual(set(self.plan["paths"]), {"dining", "living-north", "living-east", "lounge-west", "study"})

    def test_bistro_is_the_real_asset_not_a_box_proxy(self):
        bistro = next(p for p in self.props if p["asset"] == "outdoor_table_chair_set_01")
        self.assertEqual(bistro["scale"], 1.0)
        # The legacy view-subject marker is a flat grass-material quad, not a
        # second copy of the table/chairs -- no "teak"/"bistro-table" box mesh.
        self.assertEqual(len([m for m in self.meshes if m["id"].startswith("landscape-sofa-")]), 1)
        self.assertEqual(
            next(m for m in self.meshes if m["id"].startswith("landscape-sofa-"))["material"],
            "artificial-grass")
        self.assertFalse(any(m["material"] == "teak" for m in self.meshes))

    def test_layers_real_and_old_single_row_bed_fails(self):
        # Positive: today's north/east/west beds each show 3 real layers.
        self.assertEqual(L.layer_violations(self.plan["plants"]), [])
        # Negative, on the real v17 reproduction: a single-row bed (one
        # layer, "mid", as the old Duranta/Hibiscus beds were) fails.
        draft = [dict(id="old-a", bed="north", layer="mid", spread_m=.8, center=(24.65, -20.88)),
                 dict(id="old-b", bed="north", layer="mid", spread_m=.8, center=(25.55, -20.88)),
                 dict(id="old-c", bed="north", layer="mid", spread_m=.8, center=(26.45, -20.88))]
        self.assertEqual(L.layer_violations(draft, beds=("north",)), [("north", ["mid"])])

    def test_drift_real_and_old_alternation_fails(self):
        # Positive: today's back/mid/front layers each carry a real drift.
        self.assertEqual(L.drift_violations(self.plan["plants"]), [])
        # Negative: a west-mid layer with only 2 Ixora (as if the drift had
        # been thinned back towards the v17 count) fails the >= 3 rule.
        draft = [dict(id="d-a", bed="west", layer="mid", species="Ixora coccinea"),
                 dict(id="d-b", bed="west", layer="mid", species="Ixora coccinea")]
        self.assertEqual(L.drift_violations(draft), [("west", "mid", "Ixora coccinea", 2)])

    def test_bench_real_seat_height_and_old_slab_fails(self):
        # Positive: today's single bench passes (real seat height, real length, matching the scale build() chose).
        self.assertEqual(L.bench_violations(self.props), [])
        # Negative, the real v25 defect: the old dict (two copies, each scaled ~1:1 by height alone) reproduced
        # here as its own world box -- a 3.58 m slab, not a bench.
        old = L._prop("draft-old-bench", "sf_wooden_bench", (10.70, -21.15), 0.0, .48,
                      "old scale", zone="top", yaw=90)
        self.assertTrue(L.bench_violations([old]))
        wrong_way = dict(next(p for p in self.props if p["asset"] == "sf_wooden_bench"))
        wrong_way["rotation_deg"] = [0, 0, 90]
        self.assertTrue(L.bench_violations([wrong_way]), "the old end-on gate view must fail")

    def test_top_garden_has_planted_north_perimeter_containers(self):
        shrubs = [p for p in self.props if p["id"].startswith("landscape-top-north-ixora-")]
        containers = [m for m in self.meshes if m["id"].startswith("landscape-top-north-planter-")]
        self.assertEqual(len(shrubs), 2)
        self.assertEqual(len(containers), 2)
        self.assertTrue(all(p["asset"] == "sf_ixora" and p["position"][2] == .30 for p in shrubs))
        self.assertEqual(L.route_violations(shrubs), [])

    def test_standin_real_and_old_mislabelled_tree_fails(self):
        # Positive: nothing in today's build uses the tree_small_02 stand-in
        # (it was dropped entirely -- see build()'s notes).
        self.assertEqual(L.standin_violations(self.props), [])
        # Negative, the real v17 defect: tree_small_02 (a generic small tree
        # with no species credit) labelled as Bauhinia variegata with no
        # "stand-in" disclosure at all.
        draft = [dict(id="old-north-tree", asset="tree_small_02",
                      label="dressing: Bauhinia variegata; care: https://example/ (round3); "
                            "nursery height 2.55 m ASSUMED")]
        self.assertEqual(L.standin_violations(draft),
                         [("old-north-tree", "tree_small_02 used for a named species without a "
                                             "stand-in disclosure")])
        # A properly disclosed stand-in (this build's own convention) stays quiet.
        disclosed = [dict(id="ok-tree", asset="tree_small_02",
                          label="dressing: ASSUMED visual stand-in; Bauhinia variegata; care: https://x")]
        self.assertEqual(L.standin_violations(disclosed), [])


if __name__ == "__main__":
    unittest.main()
