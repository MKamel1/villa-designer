"""LDB round 3: the decided garden (layout-final): pond section, half fire pit with a paver cover, pruned shade trees + root barrier, climber panels,
visualisation-only scene and its guard, outdoor assets, preview groups. Every positive has a negative."""
import copy
import json
import math
import re
import tempfile
import unittest
from pathlib import Path

import numpy as np

from archpipe.landscape.build import build, checks, elements as E, guard, outdoor, planting, policy as P, provisional, visualisation
from archpipe.landscape.build.geom import Obj, box

ROOT = Path(__file__).resolve().parents[3]
FIN = ROOT / "knowledge/landscape/concept/final"
L = build.load_layout(FIN / "layout-final.json")
V = json.loads((FIN / "layout-visualisation.json").read_text())
G = P.GROUND_Z
S = build.build_scene(L, outdoor={})          # the shipped outdoor assets are tested in OutdoorAssets; the rest is built with the labelled geometry


def fails(findings, check=None):
    return [f for f in findings if f["status"] == "fail" and (check is None or f["check"] == check)]


class PondSection(unittest.TestCase):
    def test_both_ponds_match_the_layout_section_measured_from_vertices(self):
        r = checks.pond_section(S)
        self.assertEqual(len(r), 18)
        self.assertEqual(fails(r), [])
        got = {f["id"]: f["achieved"] for f in r}
        self.assertEqual(got["ld-e-pond entry_run_m"], "0.600 m")
        self.assertEqual(got["ld-e-pond shelf_m"], "0.300 m")
        self.assertEqual(got["ld-e-pond trench_m"], "0.500 m")
        self.assertEqual(got["ld-e-pond trench_below_water_mm"], "900 mm")
        self.assertEqual(got["ld-e-pond entry slope"], "1:4.00")

    def test_water_footprint_is_the_layout_rect_and_ends_at_the_trench_floor(self):
        for f in (x for x in L["features"] if x["kind"] == "pond"):
            w = S.by_id("ld-%s-water" % f["id"]).bounds()
            for got, want in zip((w[0], w[1], w[3], w[4]), build.R(f["rect"])):
                self.assertAlmostEqual(got, want, delta=0.002)
            self.assertAlmostEqual(w[2], G - f["depth_mm"] / 1000, places=6)
            self.assertAlmostEqual(w[5], G - 0.15, places=6)

    def test_negative_a_wrong_declared_section_is_caught(self):
        s = build.build_scene(L)
        s.by_id("ld-e-pond").meta["declared"] = dict(s.by_id("ld-e-pond").meta["declared"], entry_run_m=0.9, shelf_below_water_mm=250)
        bad = " ".join(f["id"] for f in fails(checks.pond_section(s)))
        self.assertIn("entry_run_m", bad)
        self.assertIn("shelf_below_water_mm", bad)

    def test_negative_a_lip_that_stands_proud_or_matches_the_paving_fails(self):
        s = build.build_scene(L)
        lip = s.by_id("ld-n-pond-lip")
        lip.parts = [box("pond-edge", *lip.bounds()[:3], *lip.bounds()[3:5], G + 0.02)]
        self.assertEqual(len(fails(checks.pond_section(s))), 1)
        s = build.build_scene(L)
        s.by_id("ld-n-pond-lip").parts[0].material = "paving-unit"
        self.assertEqual(len(fails(checks.pond_section(s))), 1)

    def test_grille_rests_on_the_shelf_and_nothing_floats_or_clips_in_the_pond(self):
        self.assertEqual(fails(checks.support(S)), [])
        self.assertEqual([f for f in fails(checks.clips(S)) if "pond" in f["id"]], [])

    def test_water_is_a_closed_solid_and_no_koi_without_an_asset(self):
        w = S.by_id("ld-n-pond-water").parts[0]
        edges = {}
        for f in w.faces:
            for i in range(len(f)):
                e = tuple(sorted((f[i], f[(i + 1) % len(f)])))
                edges[e] = edges.get(e, 0) + 1
        self.assertTrue(all(n == 2 for n in edges.values()))
        self.assertEqual(S.spec["koi"], "none")
        rows = [r for r in S.schedule if r["species"] == "koi"]
        self.assertEqual({r["status"] for r in rows}, {"none"})
        self.assertTrue(any("no free koi asset" in w for w in S.warnings))

    def test_koi_at_the_stocking_count_sit_in_the_trench_below_the_grille(self):
        fake = dict(id="fake_koi", role="koi", grade="B", licence="CC0", author="t", size_m=[0.2, 0.7, 0.15], gltf="/nonexistent", source_url="u")
        s = build.build_scene(L, outdoor={"koi": fake})
        for f in (x for x in L["features"] if x["kind"] == "pond"):
            k = [o for o in s.objects if o.kind == "koi" and o.id.startswith("ld-%s-koi" % f["id"])]
            self.assertEqual(len(k), f["koi_count"])
            w = s.by_id("ld-%s-water" % f["id"]).bounds()
            gz = s.by_id("ld-%s-grille" % f["id"]).bounds()[5]
            for o in k:
                b = o.asset["bounds"]
                self.assertTrue(w[0] <= b[0] and b[3] <= w[3] and w[1] <= b[1] and b[4] <= w[4], o.id)
                self.assertLess(b[5], gz)
                self.assertGreater(b[2], w[2])


class FirePit(unittest.TestCase):
    def test_only_our_half_of_the_shared_pit_is_built(self):
        self.assertEqual(S.spec["pit_half"], ("y", 1))
        line = L["features"][0]["center"][1]
        for st in ("closed", "open"):
            r = checks.pit_half(S, st)
            self.assertGreaterEqual(len(r), 2)
            self.assertEqual(fails(r), [])
        for o in S.objects:
            if "firepit" in o.id:
                self.assertGreaterEqual(o.bounds()[1], line - 1e-6, o.id)

    def test_negative_a_whole_pit_across_the_line_is_caught(self):
        s = build.build_scene(L)
        f = L["features"][0]
        whole = E.firepit("ld-s-firepit", "s-firepit", f, G)
        s.objects = [o for o in s.objects if "firepit" not in o.id] + whole
        self.assertGreaterEqual(len(fails(checks.pit_half(s))), 1)

    @staticmethod
    def _grid_lines():
        xs, ys = set(), set()
        for o in S.objects:
            if o.kind == "paving":
                for p in o.parts:
                    if p.material == "paving-unit":
                        xs |= {round(float(v), 3) for v in p.verts[:, 0]}
                        ys |= {round(float(v), 3) for v in p.verts[:, 1]}
        return np.array(sorted(xs)), np.array(sorted(ys))

    @staticmethod
    def _on_grid_share(parts, cx, cy, r):
        """Share of a cover's straight-edge vertices (not on the disc rim) that lie on a paving unit line in x or y."""
        xs, ys = FirePit._grid_lines()
        n = ok = 0
        for p in parts:
            if p.material != "paving-unit":
                continue
            for x, y, _ in p.verts:
                if abs(math.hypot(x - cx, y - cy) - r) < 0.006:      # on the rim (the units are inset 4 mm)
                    continue
                n += 1
                ok += bool(np.isclose(xs, x, atol=1.5e-3).any() or np.isclose(ys, y, atol=1.5e-3).any())
        return ok / n

    def test_cover_continues_the_paver_pattern_on_the_paving_grid(self):
        cov = S.by_id("ld-s-firepit-cover", "closed")
        f = L["features"][0]
        self.assertGreaterEqual(len([p for p in cov.parts if p.material == "paving-unit"]), 3)
        self.assertEqual(self._on_grid_share(cov.parts, *f["center"], f["diameter_m"] / 2), 1.0)       # every cut edge follows a paving joint line
        self.assertAlmostEqual(cov.bounds()[5] - G, 0.006, places=6)                                    # layout lip

    def test_negative_a_cover_on_the_wrong_grid_is_not_aligned(self):
        f = L["features"][0]
        shifted = E.cover_parts(f["center"][0], f["center"][1], f["diameter_m"], G + 0.006, [((25.123, -30.0, 26.0, -29.0), "x")], ("y", 1))
        self.assertLess(self._on_grid_share(shifted, *f["center"], f["diameter_m"] / 2), 0.6)

    def test_both_states_clean_and_the_open_cover_lies_on_the_paving(self):
        for st in ("closed", "open"):
            r = checks.footprints(S, st) + checks.support(S, st) + [f for f in checks.clips(S, st) if "firepit" in f["id"]]
            self.assertEqual(fails(r), [], st)
        o = S.by_id("ld-s-firepit-cover", "open")
        self.assertAlmostEqual(o.bounds()[2], G, places=6)
        self.assertIn("ld-s-firepit-flame", [x.id for x in S.select("open")])

    def test_a_pit_not_on_the_boundary_is_built_whole(self):
        l2 = copy.deepcopy(L)
        l2["features"][0].pop("shared_boundary")
        s = build.build_scene(l2)
        self.assertIsNone(s.spec["pit_half"])
        b = s.by_id("ld-s-firepit").bounds()
        self.assertAlmostEqual(b[4] - b[1], 0.8, places=3)


class ShadeTree(unittest.TestCase):
    def setUp(self):
        self.L = provisional.with_shade_tree(L)
        self.s = build.build_scene(self.L)
        self.m = build.build_scene(self.L, age=None)

    def test_pergolas_are_not_built_and_the_report_says_why(self):
        self.assertFalse([o for o in self.s.objects if o.kind == "pergola"])
        self.assertEqual(len([w for w in self.s.warnings if "pergola NOT built" in w]), 4)
        self.assertTrue([o for o in build.build_scene(L, pergolas=True).objects if o.kind == "pergola"])

    def test_pruned_standin_olive_is_held_to_the_pruned_size_not_the_natural_size(self):
        t = self.m.by_id("ld-ldb-prov-shade-tree")
        b = t.bounds()
        self.assertTrue(t.standin and "STAND-IN" in t.label and "pruned" in t.label)
        self.assertAlmostEqual(b[5] - b[2], 3.6, delta=0.02)                       # pruned height (natural olive is 6-9 m)
        self.assertLessEqual(max(b[3] - b[0], b[4] - b[1]), 3.4 + 0.02)            # pruned spread (natural 4.6-7.6 m)
        crown = [p for p in t.parts if p.material.startswith("standin")]
        self.assertGreaterEqual(min(p.bounds()[2] for p in crown), G + 1.9 - 0.02)  # clear stem
        self.assertTrue([p for p in t.parts if p.material == "trunk-bark"])
        row = next(r for r in self.m.schedule if r["id"] == t.id)
        self.assertTrue(row["pruned"])
        self.assertIn("PRUNED", row["size_basis"])

    def test_young_pruned_tree_is_smaller(self):
        h3 = self.s.by_id("ld-ldb-prov-shade-tree").bounds()[5] - G
        self.assertLess(h3, 3.6)

    def test_graded_asset_tree_is_scaled_to_the_pruned_canopy(self):
        l2 = provisional.with_shade_tree(L, species="citrus_limon", spread=3.0, height=3.2)
        s = build.build_scene(l2, age=None)
        t = s.by_id("ld-ldb-prov-shade-tree")
        if t.standin:
            self.skipTest("lemon asset file not on this machine")
        b = t.asset["bounds"]
        self.assertAlmostEqual(b[5] - b[2], 3.2, delta=0.02)
        self.assertLessEqual(max(b[3] - b[0], b[4] - b[1]), 3.0 + 0.02)
        self.assertEqual(t.asset["mode"], "xyz")
        self.assertIn(t.asset["grade"], "AB")

    def test_root_barrier_is_built_only_where_declared_and_is_below_ground(self):
        rb = self.s.by_id("ld-ldb-prov-shade-tree-root-barrier")
        b = rb.bounds()
        self.assertAlmostEqual(b[5], G, places=6)
        self.assertAlmostEqual(G - b[2], P.ROOT_BARRIER["depth"], places=6)
        self.assertEqual(fails(checks.support(self.s)), [])
        self.assertEqual([f for f in fails(checks.clips(self.s)) if "root-barrier" in f["id"]], [])
        self.assertFalse([o for o in S.objects if o.kind == "root-barrier"])        # the unmodified layout declares none

    def test_the_tree_pit_does_not_clip_anything_at_age_three(self):
        self.assertEqual(fails(checks.clips(self.s)), [])

    def test_a_layout_declared_root_barrier_feature_is_built(self):
        l2 = copy.deepcopy(L)
        l2["features"].append(dict(id="rb-test", kind="root_barrier", rect=[23.0, -22.0, 24.0, -21.9], depth_m=1.2))
        o = build.build_scene(l2).by_id("ld-rb-test")
        self.assertAlmostEqual(G - o.bounds()[2], 1.2, places=6)


class Climbers(unittest.TestCase):
    def test_every_structure_with_a_declared_climber_has_a_panel_on_its_garden_face(self):
        self.assertEqual(set(S.spec["climbed"]), {"wall-fence-rear", "wall-fence-east", "sister-screen-n", "sister-screen-s"})
        panels = [o for o in S.objects if o.meta.get("climbing")]
        self.assertGreaterEqual(len(panels), 5)
        for o in panels:
            b = o.bounds()
            self.assertLess(b[5] - G, 4.0 + 1e-6)
            self.assertGreater(min(b[3] - b[0], b[4] - b[1]), 0.0)
            self.assertLessEqual(min(b[3] - b[0], b[4] - b[1]), P.CLIMBER["panel_t"] + 1e-6)     # a thin panel on the face, not a mass

    def test_a_structure_with_no_climber_is_a_warn_not_an_invented_planting(self):
        w = [f for f in checks.climber_coverage(S) if f["status"] == "warn"]
        self.assertEqual([f["id"] for f in w], ["wall-street-fence"])
        self.assertTrue(any("wall-street-fence" in x and "layout gap" in x for x in S.warnings))

    def test_a_panel_stops_at_a_bench_standing_against_the_face(self):
        structs = [((28.307, -29.916, 28.557, -20.601), 4.0, "w")]
        free = build.climb_target((28.15, -27.5), structs, G)
        self.assertEqual(free["span"], (-29.916, -20.601))
        blocked = build.climb_target((28.15, -27.5), structs, G, blockers=[(27.857, -25.216, 28.307, -23.016)])
        self.assertAlmostEqual(blocked["span"][1], -25.216)
        self.assertIsNone(build.climb_target((20.0, -27.5), structs, G))

    def test_panels_never_clip_benches_or_walls(self):
        self.assertEqual([f for f in fails(checks.clips(S)) if "plant" in f["id"] and "bench" in f["id"]], [])

    def test_deciduous_and_evergreen_climbers_are_marked_for_the_seasonal_render(self):
        mats = {o.meta["species"]: o.parts[0].material for o in S.objects if o.meta.get("climbing") and o.standin}
        self.assertTrue(any(m.endswith(":d") for m in mats.values()))
        self.assertTrue(any(m.endswith(":e") for m in mats.values()))
        self.assertTrue(mats["vitis_vinifera"].endswith(":d"))
        self.assertTrue([o for o in S.objects if o.meta.get("deciduous") and o.meta.get("climbing")])

    def test_climber_panel_assets_are_used_only_when_graded(self):
        self.assertEqual(planting.climber_panels(), [r for r in planting.climber_panels() if r["grade"] in "AB"])


class Visualisation(unittest.TestCase):
    def setUp(self):
        self.v = visualisation.build_visualisation(L, V)

    def test_sister_objects_are_tagged_and_ours_are_untouched(self):
        sis = [o for o in self.v.objects if guard.is_vis(o)]
        self.assertGreater(len(sis), 60)
        self.assertTrue(all(o.id.startswith("ld-vis-") and o.meta.get("visualisation_only") and "VISUALISATION ONLY" in o.label for o in sis))
        ours = [o for o in self.v.objects if not guard.is_vis(o)]
        self.assertEqual(sorted((o.id, o.state or "") for o in ours), sorted((o.id, o.state or "") for o in S.objects))
        self.assertTrue(self.v.visualisation_only)

    def test_sister_garden_is_mirrored_to_the_far_side_of_the_west_line(self):
        line = L["features"][0]["center"][1]
        for o in self.v.objects:
            if guard.is_vis(o) and o.kind in ("paving", "bench", "table"):
                self.assertLessEqual(o.bounds()[4], line + 0.02, o.id)

    def test_sister_half_of_the_pit_completes_the_circle(self):
        line = L["features"][0]["center"][1]
        ours = S.by_id("ld-s-firepit").bounds()
        sis = self.v.by_id("ld-vis-s-firepit").bounds()
        self.assertGreaterEqual(ours[1], line - 1e-6)
        self.assertLessEqual(sis[4], line + 1e-6)
        self.assertAlmostEqual(sis[0], ours[0], places=6)
        self.assertAlmostEqual(sis[3], ours[3], places=6)

    def test_checks_schedule_and_export_exclude_or_refuse_it(self):
        from archpipe.landscape.build import export, report
        self.assertEqual(checks.summary(checks.run_all(self.v)), checks.summary(checks.run_all(S)))
        self.assertTrue(all("vis" not in f["id"] for f in checks.run_all(self.v)))
        with self.assertRaises(guard.VisualisationOnlyError):
            export.to_villa_scene(self.v)
        with self.assertRaises(guard.VisualisationOnlyError):
            report.schedule(self.v)
        with self.assertRaises(guard.VisualisationOnlyError):
            report.element_table(self.v)
        export.to_villa_scene(S)                                              # the production scene is not refused
        self.assertEqual(report.schedule(S)["individuals"], report.schedule(self.v.__class__(**{**self.v.__dict__, "objects": guard.production_only(self.v).objects, "visualisation_only": False}))["individuals"])

    def test_a_flagless_scene_that_carries_sister_objects_is_still_refused(self):
        from dataclasses import replace
        from archpipe.landscape.build import export, preview
        sneaky = replace(self.v, visualisation_only=False)
        with self.assertRaises(guard.VisualisationOnlyError):
            export.to_villa_scene(sneaky)
        with self.assertRaises(guard.VisualisationOnlyError):
            preview.render(sneaky, tempfile.mkdtemp(), "x")

    def test_render_only_into_a_visualisation_directory(self):
        from archpipe.landscape.build import preview
        with self.assertRaises(guard.VisualisationOnlyError):
            preview.render(self.v, Path(tempfile.mkdtemp()) / "previews", "x")

    def test_band_is_stamped_and_detected_and_absence_is_detected(self):
        from PIL import Image
        d = Path(tempfile.mkdtemp())
        Image.new("RGB", (800, 500), (90, 120, 90)).save(d / "a.jpg")
        self.assertFalse(visualisation.band_present(d / "a.jpg"))
        visualisation.stamp_band(d / "a.jpg")
        self.assertTrue(visualisation.band_present(d / "a.jpg"))

    def test_no_production_module_imports_the_visualisation_builder(self):
        offenders = []
        for p in (ROOT / "src").rglob("*.py"):
            if "landscape/build" in str(p):
                continue
            if re.search(r"landscape\.build\.visualisation|from \.visualisation|import visualisation", p.read_text(errors="ignore")):
                offenders.append(str(p))
        self.assertEqual(offenders, [])
        prod = ROOT / "knowledge/landscape/build"
        for p in prod.glob("*/schedule.json"):
            self.assertNotIn("ld-vis-", p.read_text(), p)
        for p in prod.glob("*/checks.json"):
            self.assertNotIn("ld-vis-", p.read_text(), p)

    def test_a_non_visualisation_layout_is_refused(self):
        with self.assertRaises(ValueError):
            visualisation.build_visualisation(L, L)


class OutdoorAssets(unittest.TestCase):
    ROW = dict(id="t", role="dining_table", grade="B", licence="CC0", author="x", size_m=[2.0, 0.9, 0.76], gltf="/x", source_url="u", front="-y")
    CHAIR = dict(ROW, id="c", role="dining_chair", size_m=[0.5, 0.55, 0.9])

    def test_without_assets_table_and_chairs_are_labelled_simple_geometry(self):
        s = build.build_scene(L, outdoor={})
        t = s.by_id("ld-s-dining-table")
        self.assertIn("SIMPLE GEOMETRY", t.label)
        self.assertEqual(len([o for o in s.objects if o.kind == "chair"]), 8)
        self.assertTrue(all("SIMPLE GEOMETRY" in o.label for o in s.objects if o.kind == "chair"))

    def test_a_graded_table_is_fitted_to_the_layout_table(self):
        s = build.build_scene(L, outdoor={"dining_table": self.ROW, "dining_chair": self.CHAIR})
        t = s.by_id("ld-s-dining-table")
        self.assertEqual(t.asset["mode"], "box")
        self.assertEqual(t.asset["box_m"], [2.4, 0.9, 0.75])  # ROW long axis is x like the layout table
        self.assertEqual(fails(checks.footprints(s)), [])
        ch = [o for o in s.objects if o.kind == "chair"]
        self.assertEqual(len(ch), 8)
        self.assertTrue(all(o.asset["licence"] == "CC0" for o in ch))
        yaws = {round(o.asset["yaw_deg"]) % 360 for o in ch}
        self.assertEqual(yaws, {0, 90, 180, 270} & yaws)
        self.assertGreater(len(yaws), 1)

    def test_a_table_of_the_wrong_proportion_falls_back_to_geometry(self):
        round_table = dict(self.ROW, size_m=[1.2, 1.2, 0.75])
        s = build.build_scene(L, outdoor={"dining_table": round_table})
        self.assertIn("SIMPLE GEOMETRY", s.by_id("ld-s-dining-table").label)

    def test_load_uses_only_graded_ab_rows_whose_file_exists(self):
        d = Path(tempfile.mkdtemp())
        (d / "m.gltf").write_text("{}")
        rows = [dict(self.ROW, gltf=str(d / "m.gltf"), grade="B"), dict(self.CHAIR, gltf=str(d / "m.gltf"), grade="C"), dict(self.ROW, role="bench", gltf=str(d / "none.gltf"), grade="A")]
        (d / "o.json").write_text(json.dumps(dict(assets=rows)))
        self.assertEqual(list(outdoor.load(d / "o.json")), ["dining_table"])
        self.assertEqual(outdoor.load(d / "missing.json"), {})


class Agnostic(unittest.TestCase):
    def test_final_and_visualisation_layouts_build_clean_at_three_years(self):
        for lay in (L, V):
            s = build.build_scene(lay)
            self.assertEqual(fails(checks.ids(s)), [])
            self.assertEqual(fails(checks.footprints(s)), [])
            self.assertEqual(fails(checks.support(s)), [])
            self.assertEqual(fails(checks.clips(s)), [])

    def test_preview_view_groups_for_the_review_set(self):
        from archpipe.landscape.build import preview
        v = preview.default_views(S, "t")
        names = {x["name"] for x in v}
        self.assertTrue({"bird-south-east", "eye-living-door", "eye-dining-firepit", "court-north-pond", "yard-east-pond", "firepit-open", "firepit-closed"} <= names)
        self.assertTrue({"bird", "eye", "court", "pond"} <= {x["group"] for x in v})
        self.assertTrue(all(x["group"] in preview.EXPOSURE for x in v))
        vis = preview.default_views(visualisation.build_visualisation(L, V), "t")
        self.assertEqual([x["group"] for x in vis], ["vis"])

    def test_every_layout_element_is_built_or_reported(self):
        built = {o.layout_id or o.meta.get("layout_id") for o in S.objects} | {o.meta.get("also") for o in S.objects}
        want = set()
        for k in ("paved_areas", "paths", "planting_groups", "seating", "tables", "features", "trees", "walls", "screens"):
            want |= {e["id"] for e in L[k]}
        want |= {o["id"] for o in L["obstacles"] if o["id"].startswith("pot")}
        self.assertEqual(want - built, set())


if __name__ == "__main__":
    unittest.main()
