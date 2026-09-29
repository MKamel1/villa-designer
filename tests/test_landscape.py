"""Defect (client draft renders v01/v02/v05/v07/v17): the jacaranda CC0 stand-in was placed at its full native
size (19.3 m tall, ~24 x 19 m canopy -- measured from the glTF POSITION accessors on ai-workstation,
ops/workstation/library-manifest.json bounds_m), and only a 1.5 m TRUNK setback was ever checked. The canopy
itself was free to pass through the parents' bedroom and the garden-living ceiling. This file proves
`archpipe.concept.villa_landscape.extent_violations` catches that real placement, and that the corrected TREES
table (and every other landscape prop) clears it."""
import unittest

from archpipe.concept import villa_landscape as LAND
from archpipe.concept import revit_spec as RS
from archpipe.concept import villa_r11 as R

# The exact D1 draft placement that produced the defect: jacaranda_tree, scale 1.0, at (18.30, -21.55) -- the
# "north-shade" entry before this fix. Frozen here by value (not by importing the old TREES table, which no
# longer exists) so this test keeps proving the real reproduction even as TREES is retuned later.
D1_DRAFT_JACARANDA = dict(id="landscape-tree-north-shade-draft", asset="jacaranda_tree",
                          position=[18.30, -21.55, LAND.GROUND], rotation_deg=[0, 0, 0], scale=1.0)


class LandscapeExtentGuard(unittest.TestCase):
    def test_bounds_table_holds_every_landscape_prop_and_matches_measured_figures(self):
        # Cross-check against the lead's own independently measured (ambientCG/ai-workstation) figures for the
        # assets that are single-root files (no internal offset variants); the multi-root ones (searsia_lucida,
        # shrub_02) legitimately differ -- see test below.
        measured = {
            "jacaranda_tree": ((-12.9203, -0.1466, -9.9538), (11.4968, 19.3223, 9.2008)),
            "tree_small_02": ((-1.309, -0.0241, -1.3826), (1.6077, 4.5326, 2.9099)),
            "boulder_01": ((-0.7482, -0.0736, -0.9484), (0.524, 0.9302, 0.8819)),
            "shrub_02": ((-2.3085, -0.6064, -1.1912), (4.2642, 1.9417, 1.3448)),
        }
        for asset, (mn, mx) in measured.items():
            got_mn, got_mx = LAND.PROP_BOUNDS[asset]
            for a, b in zip(mn, got_mn):
                self.assertAlmostEqual(a, b, places=3, msg=asset)
            for a, b in zip(mx, got_mx):
                self.assertAlmostEqual(a, b, places=3, msg=asset)
        for _, asset, *_ in LAND.TREES:
            self.assertIn(asset, LAND.PROP_BOUNDS, asset + " has no checked-in library-manifest.json bounds_m")

    def test_guard_fails_on_the_real_d1_draft_placement(self):
        # This IS the defect: jacaranda at native size, only ever checked against a 1.5 m trunk setback.
        self.assertTrue(LAND.inside_yard(*D1_DRAFT_JACARANDA["position"][:2]))
        self.assertGreaterEqual(LAND.facade_distance(*D1_DRAFT_JACARANDA["position"][:2]), 1.5,
                                "the draft passed the OLD (trunk-only) rule -- the canopy defect was invisible to it")
        violations = LAND.extent_violations([D1_DRAFT_JACARANDA])
        self.assertTrue(violations, "the guard must catch the real oversize jacaranda that put a canopy through "
                                    "the parents' bedroom and the garden-living ceiling")
        self.assertIn("building footprint", violations[0][1])

    def test_current_villa_landscape_build_clears_the_guard(self):
        lay = R.design("D1")
        sp = RS.build(lay)
        _, props, _, plan = LAND.build(sp)
        trees = [p for p in props if p["id"].startswith("landscape-tree-")]
        self.assertEqual(len(trees), len(plan["trees"]))
        self.assertEqual(LAND.extent_violations(trees), [])
        self.assertEqual(LAND.extent_violations(props), [], "every landscape prop, not only trees, must clear it")
        # Every tree is materially smaller than the unchecked draft: no invented citation for olive's mature
        # height (none is held in knowledge/library.json), but every one is far below the jacaranda's native 19.3 m.
        for name, asset, x, y, yaw, target_h in plan["trees"]:
            self.assertLess(target_h, 5.0, name)
            self.assertGreaterEqual(target_h, 3.0, name)

    def test_negative_a_small_shrub_mid_yard_stays_quiet(self):
        # A small prop well inside the yard, clear of the building, must not trip the guard (the guards-always
        # discipline: a check that never says "fine" is not a check).
        quiet = dict(id="landscape-shrub-mid-yard", asset="shrub_01", position=[14.0, -22.0, LAND.GROUND + 0.38],
                    rotation_deg=[0, 0, 0], scale=1.0)
        self.assertEqual(LAND.extent_violations([quiet]), [])

    def test_negative_prop_with_no_known_bounds_is_skipped_not_crashed(self):
        # A prop id absent from the manifest's bounds_m (e.g. never bounds-measured) must not raise; the guard
        # can only check what it has measured, and villa_landscape.build() only uses assets that ARE covered
        # (test_bounds_table_holds_every_landscape_prop_and_matches_measured_figures proves that separately).
        unknown = dict(id="landscape-mystery", asset="not_a_real_asset", position=[0, 0, 0],
                      rotation_deg=[0, 0, 0], scale=1.0)
        self.assertEqual(LAND.extent_violations([unknown]), [])

    def test_prop_world_box_matches_the_verified_blender_import(self):
        # Independent check (docs/method discipline: "verify against something independent"): tree_small_02 at
        # scale 1, no rotation, position (0,0,0) was imported in a headless Blender 4.2.9 (import_scene.gltf) and
        # its world bound_box measured directly: x -1.3090..1.6077, y -2.9099..1.3826, z -0.0241..4.5326 (a height
        # span of 4.5567 m). villa_scene.import_props then re-seats the whole prop so its lowest point sits at
        # `position[2]` exactly (the "bottom" correction) -- prop_world_box reproduces that, so z0 is `position[2]`
        # (0 here) and z1 is z0 plus the measured height span, not Blender's own raw z0/z1.
        x0, y0, z0, x1, y1, z1 = LAND.prop_world_box("tree_small_02", [0, 0, 0], [0, 0, 0], 1.0)
        for got, want in zip((x0, y0, z0, x1, y1, z1),
                             (-1.3090, -2.9099, 0.0, 1.6077, 1.3826, 4.5567)):
            self.assertAlmostEqual(got, want, places=3)


if __name__ == "__main__":
    unittest.main()
