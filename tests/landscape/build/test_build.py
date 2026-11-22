"""LDB: layout -> 3D garden. Positive tests on concept A (pond east), negative tests for every check, and concept-agnostic builds of all six pass-2 layouts."""
import copy
import glob
import json
import math
import unittest
from pathlib import Path

import numpy as np

from archpipe.landscape.build import build, checks, planting, policy as P
from archpipe.landscape.build.geom import Obj, box

ROOT = Path(__file__).resolve().parents[3]
PASS2 = ROOT / "knowledge/landscape/concept/pass2"
from archpipe.landscape.build import outdoor as _od
_real_load = _od.load


def setUpModule():
    _od.load = lambda *a, **k: {}      # legacy concept-A tests are written for the labelled geometry; the shipped outdoor assets are tested in test_build2


def tearDownModule():
    _od.load = _real_load


A = build.load_layout(PASS2 / "layout-A-pond-east.json")
AP = A       # pergola tests build concept A with pergolas on: the client replaced pergolas by shade trees, the builder keeps the capability behind pergolas=True
G = P.GROUND_Z


def fails(findings, check=None):
    return [f for f in findings if f["status"] == "fail" and (check is None or f["check"] == check)]


class Footprints(unittest.TestCase):
    def test_every_rect_object_matches_the_layout_within_20mm_both_states(self):
        s = build.build_scene(A)
        for st in ("closed", "open"):
            r = checks.footprints(s, st)
            self.assertGreater(len(r), 25)
            self.assertEqual(fails(r), [], st)

    def test_layout_rects_are_the_built_extents(self):
        s = build.build_scene(A)
        for pa in A["paved_areas"][:3]:
            o = [x for x in s.objects if x.layout_id == pa["id"] and x.kind == "paving"][0]
            b = o.bounds()
            for got, want in zip((b[0], b[1], b[3], b[4]), build.R(pa["rect"])):
                self.assertAlmostEqual(got, want, delta=0.02)

    def test_negative_footprint_30mm_off_fails(self):
        s = build.build_scene(A, pergolas=True)
        o = s.by_id("ld-pergola-dining")
        o.footprint = (o.footprint[0] - 0.03, *o.footprint[1:])
        self.assertEqual(len(fails(checks.footprints(s), "footprint")), 1)

    def test_negative_wrong_size_object_fails(self):
        s = build.build_scene(A)
        w = s.by_id("ld-fence-rear")
        w.parts = [box("wall-render", 28.307, -29.916, G, 28.7, -20.601, G + 4)]      # 150 mm too thick
        self.assertEqual([f["id"] for f in fails(checks.footprints(s))], ["ld-fence-rear"])

    def test_standin_mature_spread_equals_layout_spread(self):
        s = build.build_scene(A, age=None)
        r = [f for f in checks.plant_footprints(s) if f["status"] != "info"]
        self.assertGreater(len(r), 25)
        self.assertEqual(fails(r), [])

    def test_young_standin_never_wider_than_mature_layout_spread(self):
        s = build.build_scene(A, age=3)
        for o in s.objects:
            if o.standin and not o.meta.get("climbing"):
                b = o.bounds()
                self.assertLessEqual(max(b[3] - b[0], b[4] - b[1]), o.meta["layout_spread"] + 0.02, o.id)


class Ids(unittest.TestCase):
    def test_all_ids_ld_prefixed_and_unique(self):
        s = build.build_scene(A)
        r = checks.ids(s)
        self.assertEqual(fails(r), [])
        self.assertTrue(all(o.id.startswith("ld-") for o in s.objects))

    def test_every_layout_element_has_a_built_object(self):
        s = build.build_scene(A, pergolas=True)
        built = {o.layout_id or o.meta.get("layout_id") for o in s.objects} | {o.meta.get("also") for o in s.objects}
        want = set()
        for k in ("paved_areas", "paths", "planting_groups", "seating", "tables", "features", "trees", "walls", "screens", "canopies"):
            want |= {e["id"] for e in A[k]}
        want |= {o["id"] for o in A["obstacles"] if o["id"].startswith("pot")}
        self.assertEqual(want - built, set())

    def test_duplicate_layout_ids_across_gardens_get_distinct_element_ids(self):
        s = build.build_scene(A)
        pv = [o.id for o in s.objects if o.kind == "paving"]
        self.assertEqual(len(pv), len(set(pv)))
        self.assertIn("ld-paving-0-r1", pv)          # the north court's paving-0 (the layout reuses 'paving-0' in each garden)

    def test_two_states_of_the_cover_share_one_id(self):
        s = build.build_scene(A)
        self.assertEqual([o.state for o in s.objects if o.id == "ld-firepit-cover"].count("closed"), 1)
        self.assertEqual({o.id for o in s.select("open")} - {o.id for o in s.select("closed")}, {"ld-firepit-flame"})


class Planting(unittest.TestCase):
    def setUp(self):
        self.s = build.build_scene(A)

    def test_concept_a_asset_and_standin_counts(self):
        c = {}
        for r in self.s.schedule:
            if r["species"] != "koi":
                c[r["status"]] = c.get(r["status"], 0) + 1
        self.assertEqual(c, {"standin": 36, "asset": 19, "omitted": 1})      # LDL pass 5 (Fab FBX) made aspidistra, pennisetum, origanum, rhapis drawable
        self.assertLessEqual({"punica_granatum", "plumeria_rubra", "aspidistra_elatior"}, {r["species"] for r in self.s.schedule if r["status"] == "asset"})

    def test_standins_are_labelled_in_object_and_schedule(self):
        r = checks.standins(self.s)
        self.assertEqual(fails(r), [])
        for o in self.s.objects:
            if o.standin:
                self.assertIn("STAND-IN", o.label)
                self.assertIn(o.meta["species"], o.label)

    def test_assets_are_graded_ab_and_scaled_to_sourced_height_at_age(self):
        t = self.s.by_id("ld-tree-0-punica")
        self.assertIn(t.asset["grade"], "AB")
        mature = build.build_scene(A, age=None).by_id("ld-tree-0-punica")
        self.assertAlmostEqual(mature.bounds()[5] - mature.bounds()[2], 3.7, places=3)           # layout/NCSU mature height
        h3 = t.bounds()[5] - t.bounds()[2]
        self.assertAlmostEqual(h3, 3.7 * planting.size_fraction(3, "moderate", "small_tree"), places=3)
        self.assertLess(h3, 3.7)

    def test_age_default_is_three_years_and_mature_is_larger(self):
        self.assertEqual(self.s.age, 3)
        m = build.build_scene(A, age=None)
        for a, b in zip(self.s.schedule, m.schedule):
            if a["status"] in ("asset", "standin") and a["species"] != "koi":
                self.assertLessEqual(a["shown_height_m"], b["shown_height_m"] + 1e-9)

    def test_negative_species_without_asset_is_a_labelled_standin_never_a_lookalike(self):
        for slug in ("no_such_species_xyz", "salvia_leucantha", "citrus_x_sinensis"):    # unknown, undrawable, and a species whose only asset is a lemon
            L = copy.deepcopy(A)
            L["planting_groups"][0]["plants"] = [dict(species=slug, at=[24.0, -29.0], spread_m=0.8, form="shrub", water_need="medium")]
            s = build.build_scene(L)
            o = s.by_id("ld-plant-bed-west-00")
            self.assertTrue(o.standin, slug)
            self.assertIsNone(o.asset, slug)
            self.assertIn("STAND-IN", o.label)
            row = [r for r in s.schedule if r["id"] == o.id][0]
            self.assertEqual(row["status"], "standin")
            self.assertNotIn("asset", row or {}) if False else None
            self.assertIsNone(row.get("asset"))

    def test_resolve_refuses_the_lemon_for_the_orange(self):
        self.assertFalse(planting.resolve("citrus_x_sinensis")["drawable"])
        self.assertTrue(planting.resolve("citrus_limon")["drawable"])

    def test_resolve_ignores_a_c_grade_asset(self):
        a = copy.deepcopy(planting._assets())
        for x in a["assets"]:
            if "punica_granatum" in (x.get("maps_to") or []):
                x["grade"] = "C"
        self.assertFalse(planting.resolve("punica_granatum", assets=a)["drawable"])

    def test_standin_colour_follows_the_sourced_foliage_text(self):
        o = [x for x in self.s.objects if x.meta.get("species") == "salvia_leucantha"][0]
        col = o.parts[0].material
        r, g, b = (float(v) for v in col.split(":")[1].split(","))
        self.assertAlmostEqual(r, 0.46, places=2)          # "gray-green"
        row = [r for r in self.s.schedule if r["id"] == o.id][0]
        self.assertIn("gray-green", row["colour_basis"])

    def test_climbers_cling_to_the_screen_face(self):
        c = [o for o in self.s.objects if o.meta.get("climbing")]
        self.assertEqual(len(c), 5)
        scr = self.s.by_id("ld-sister-screen").bounds()
        for o in c:
            b = o.bounds()
            self.assertAlmostEqual(b[1], scr[4], delta=P.CLIMBER["lift"] + 0.003)       # the panel stands 20 mm off the screen's garden face
            self.assertLessEqual(b[5], G + 2.1 + 1e-6)

    def test_plant_inside_a_pot_is_omitted_and_reported(self):
        r = [x for x in self.s.schedule if x["status"] == "omitted"]
        self.assertEqual(len(r), 1)
        self.assertIn("pot-0-plumeria", r[0]["reason"])


class FirePit(unittest.TestCase):
    def setUp(self):
        self.s = build.build_scene(A)

    def test_closed_cover_is_flush_to_the_layout_lip(self):
        c = self.s.by_id("ld-firepit-cover", "closed")
        self.assertAlmostEqual(c.bounds()[5], G + 0.006, places=6)
        self.assertAlmostEqual(c.bounds()[3] - c.bounds()[0], 0.9, places=6)

    def test_open_state_shows_the_burner_flame_and_cover_set_aside(self):
        o = self.s.by_id("ld-firepit-cover", "open")
        c = self.s.by_id("ld-firepit-cover", "closed")
        self.assertGreater(o.bounds()[0] - c.bounds()[0], 0.9)       # moved off the opening
        self.assertIn("ld-firepit-flame", [x.id for x in self.s.select("open")])
        self.assertNotIn("ld-firepit-flame", [x.id for x in self.s.select("closed")])
        self.assertAlmostEqual(o.bounds()[2], G, places=6)           # lying on the paving

    def test_paving_is_cut_for_the_opening_and_clear_of_it(self):
        pv = [x for x in self.s.objects if x.kind == "paving" and abs(x.footprint[0] - 22.597) < 1e-3 and x.layout_id == "paving-2"][0]
        cx, cy = A["features"][0]["center"]
        for p in pv.parts:
            if p.material == "paving-unit":
                d = min(math.hypot(x - cx, y - cy) for x, y, _ in p.verts)
                self.assertGreaterEqual(d, 0.45 + 0.003 - 0.0045 - 1e-3)      # outside the opening (a corner may sit within the 4 mm joint half-width)

    def test_both_states_pass_footprint_support_and_clip(self):
        for st in ("closed", "open"):
            r = checks.footprints(self.s, st) + checks.support(self.s, st) + [f for f in checks.clips(self.s, st) if "firepit" in f["id"] or "paving" in f["id"]]
            self.assertEqual(fails(r), [], st)


class FloatAndClip(unittest.TestCase):
    def test_concept_a_at_three_years_nothing_floats_and_nothing_clips_except_the_named_layout_conflict(self):
        s = build.build_scene(A)
        self.assertEqual(fails(checks.support(s)), [])
        c = fails(checks.clips(s))
        self.assertTrue(all("ld-pergola-bench x ld-tree-0-punica" == f["id"] for f in c), c)      # the pomegranate stands inside the bench pergola's footprint (layout)

    def test_negative_floating_object_is_caught(self):
        s = build.build_scene(A)
        s.objects.append(Obj("ld-test-float", "bench", "x", [box("seat-timber", 25, -27, G + 0.05, 25.5, -26.5, G + 0.5)], footprint_mode=None))
        r = fails(checks.support(s))
        self.assertEqual([f["id"] for f in r], ["ld-test-float"])
        self.assertIn("50 mm", r[0]["achieved"])

    def test_negative_sunk_object_is_caught(self):
        s = build.build_scene(A)
        s.objects.append(Obj("ld-test-sunk", "bench", "x", [box("seat-timber", 25, -27, G - 0.1, 25.5, -26.5, G + 0.4)], footprint_mode=None))
        self.assertEqual([f["id"] for f in fails(checks.support(s))], ["ld-test-sunk"])

    def test_negative_clipping_objects_are_caught(self):
        s = build.build_scene(A)
        s.objects.append(Obj("ld-test-clip", "bench", "x", [box("seat-timber", 25.0, -26.9, G, 25.6, -26.5, G + 0.8)], footprint_mode=None))   # through the dining table top
        r = fails(checks.clips(s))
        self.assertIn("ld-dining-table", " ".join(f["id"] for f in r))

    def test_touching_is_not_a_clip(self):
        s = build.build_scene(A)
        s.objects.append(Obj("ld-test-touch", "bench", "x", [box("seat-timber", 27.0, -20.351, G, 27.5, -19.9, G + 0.4)], footprint_mode=None))   # shares only the fence face
        self.assertEqual([f for f in fails(checks.clips(s)) if "ld-test-touch" in f["id"]], [])

    def test_mature_pomegranate_hits_the_pergola_louvres_and_the_checker_sees_it(self):
        m = build.build_scene(A, age=None, pergolas=True)
        ids = " ".join(f["id"] for f in fails(checks.clips(m)))
        self.assertIn("ld-pergola-bench x ld-tree-0-punica", ids)
        self.assertIn("ld-pergola-dining x ld-tree-0-punica", ids)

    def test_posts_stand_on_ground_and_louvres_are_carried_by_beams(self):
        s = build.build_scene(A, pergolas=True)
        perg = s.by_id("ld-pergola-dining")
        zs = sorted(p.bounds()[2] for p in perg.parts)
        self.assertAlmostEqual(zs[0], G, places=6)
        self.assertEqual(perg.meta["posts"], 6)          # 4 corners + 1 intermediate on each 3.8 m side (spans over 3 m get a post where the plan is free)
        self.assertGreater(perg.meta["blades"], 15)


class Structures(unittest.TestCase):
    def test_west_screen_is_2_1m_trellis_with_posts_at_most_1_5m(self):
        s = build.build_scene(A)
        t = s.by_id("ld-sister-screen")
        self.assertAlmostEqual(t.bounds()[5] - t.bounds()[2], 2.1, places=6)
        posts = sorted(p.bounds()[0] for p in t.parts if p.bounds()[5] - p.bounds()[2] > 2.0)
        self.assertGreaterEqual(len(posts), 5)
        self.assertLessEqual(max(b - a for a, b in zip(posts, posts[1:])), 1.5 + P.SCREEN_POST[0])

    def test_pergola_heights_from_layout(self):
        s = build.build_scene(A, pergolas=True)
        for c in A["canopies"]:
            self.assertAlmostEqual(s.by_id("ld-" + c["id"]).bounds()[5] - G, c["height_m"], places=6)

    def test_bench_height_from_layout_seatwall_spec(self):
        s = build.build_scene(A)
        for b in A["seating"]:
            self.assertAlmostEqual(s.by_id("ld-" + b["id"]).bounds()[5] - G, 0.45, places=6)

    def test_paving_has_joints_between_units(self):
        s = build.build_scene(A)
        o = s.by_id("ld-paving-2")
        units = [p for p in o.parts if p.material == "paving-unit"]
        self.assertGreater(len(units), 30)
        self.assertEqual(len([p for p in o.parts if p.material == "paving-joint"]) >= 1, True)
        tops = {round(float(p.verts[:, 2].max()), 6) for p in units}
        self.assertEqual(tops, {G})                                   # units flush with the ground, joint base below
        self.assertLess(max(p.verts[:, 2].max() for p in o.parts if p.material == "paving-joint"), G)

    def test_chairs_and_table_are_labelled_simple_geometry(self):
        s = build.build_scene(A)
        self.assertEqual(len([o for o in s.objects if o.kind == "chair"]), 8)
        for o in s.objects:
            if o.kind in ("chair", "table", "bbq"):
                self.assertIn("SIMPLE GEOMETRY", o.label)


class Agnostic(unittest.TestCase):
    def test_all_six_pass2_layouts_build_with_ids_footprints_and_support_clean(self):
        files = sorted(glob.glob(str(PASS2 / "layout-*.json")))
        self.assertEqual(len(files), 6)
        for f in files:
            s = build.build_scene(build.load_layout(f))
            for st in ("closed", "open"):
                r = checks.ids(s) + checks.footprints(s, st) + checks.support(s, st) + checks.standins(s)
                self.assertEqual(fails(r), [], (f, st))

    def test_not_a_layout_is_refused(self):
        with self.assertRaises(ValueError):
            build.build_scene(build.load_layout(ROOT / "knowledge/landscape/plants/assets.json"))

    def test_unbuilt_layout_features_are_warned_not_dropped_silently(self):
        s = build.build_scene(build.load_layout(PASS2 / "layout-C-pond-east.json"))
        self.assertTrue(any("polyline" in w for w in s.warnings))
        L = copy.deepcopy(A); L["steps"] = [dict(rect=[23, -26, 24, -25], count=3)]
        self.assertTrue(any("steps" in w for w in build.build_scene(L).warnings))


class PreviewSpec(unittest.TestCase):
    def test_spec_is_json_and_carries_every_object_and_views(self):
        from archpipe.landscape.build import preview
        s = build.build_scene(A)
        sp = preview.scene_spec(s, preview.default_views(s, "t"))
        json.dumps(sp)
        self.assertEqual(len(sp["objects"]), len(s.objects))
        self.assertEqual([v["name"] for v in sp["views"]][:3], ["bird-south-east", "eye-living-door", "eye-dining-firepit"])
        self.assertEqual({v["state"] for v in sp["views"]}, {"closed", "open"})

    def test_eye_views_are_at_the_lds_doors(self):
        from archpipe.landscape.build import preview
        from archpipe.landscape.critic import site
        d = {x["id"]: x["at"] for x in site.doors()}
        self.assertEqual(tuple(d["door-B-8"]), preview.DOORS["living"]["at"])
        self.assertEqual(tuple(d["door-B-6"]), preview.DOORS["dining"]["at"])


class BlenderReceipt(unittest.TestCase):
    """Reads the committed receipt of the real Blender run: measured, not assumed."""
    def test_assets_stand_on_the_ground_in_the_render(self):
        rec = ROOT / "knowledge/landscape/build/A-pond-east/previews/age3.receipt.json"
        if not rec.exists():
            self.skipTest("no committed Blender receipt")
        r = json.loads(rec.read_text())
        self.assertGreaterEqual(len(r["assets"]), 2)
        for a in r["assets"]:
            self.assertLess(abs(a["base_z_error_m"]), 0.001, a["id"])
            self.assertAlmostEqual(a["height_m"], a["target_height_m"], delta=0.01)


if __name__ == "__main__":
    unittest.main()


class Export(unittest.TestCase):
    def test_export_gives_one_mesh_per_object_material_with_declared_element_ids(self):
        from archpipe.landscape.build import export
        s = build.build_scene(A)
        meshes, props = export.to_villa_scene(s)
        self.assertTrue(all(m["element_ids"][0].startswith("ld-") and m["element_ids"][0] in m["id"] for m in meshes))
        self.assertEqual(len({m["id"] for m in meshes}), len(meshes))
        self.assertTrue(all(len(f) >= 3 and len(f[0]) == 3 for m in meshes[:5] for f in m["faces"]))
        self.assertLessEqual({"ld-tree-0-punica", "ld-pot-0-plumeria-plant"}, {p["id"] for p in props})
        self.assertTrue(all(Path(p["gltf"]).exists() for p in props))      # glTF or a Fab FBX, present on this machine
        self.assertNotIn("ld-firepit-cover", [m["id"] for m in export.to_villa_scene(s, "open")[0] if m["ld_state"] == "closed"])
