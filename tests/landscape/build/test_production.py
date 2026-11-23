"""Lane GI: the decided garden in the production scene (landscape/build/production.py and the Blender hook's contract). Pure Python; Blender itself is proven by renders."""
import ast
import copy
import unittest
from pathlib import Path

from archpipe.landscape.build import build, guard, production as PR

ROOT = Path(__file__).resolve().parents[3]
G = PR.garden()


class Seasons(unittest.TestCase):
    def test_december_to_february_are_leaf_off_and_the_rest_leaf_on(self):
        self.assertEqual([PR.season_for("2026-%02d-15T10:30:00+02:00" % m) for m in range(1, 13)], ["winter", "winter"] + ["summer"] * 9 + ["winter"])

    def test_a_deciduous_object_has_both_variants_under_one_element_id_and_an_evergreen_one_variant(self):
        by = {}
        for m in G["meshes"]:
            by.setdefault(m["element_ids"][0], set()).add(m.get("ld_season"))
        self.assertEqual(by["ld-plant-s-bed-screen-n-00"], {"summer", "winter"})        # the grape
        self.assertEqual(by["ld-plant-s-bed-wall-00"], {None})                          # petrea: evergreen, one geometry
        winter = [m for m in G["meshes"] if m.get("ld_season") == "winter"]
        self.assertTrue(winter and all("leaf" not in m["material"] for m in winter))     # leaf-off = stems and limbs only

    def test_a_summer_view_hides_the_winter_meshes_and_the_open_pit_and_a_winter_view_the_reverse(self):
        s = set(PR.view_hides(G["meshes"], "summer"))
        w = set(PR.view_hides(G["meshes"], "winter"))
        ids = {m["id"]: m for m in G["meshes"]}
        self.assertTrue(s and w and not (s & w - {i for i, m in ids.items() if m.get("ld_state") == "open"}))
        self.assertTrue(all(ids[i].get("ld_season") == "winter" or ids[i].get("ld_state") == "open" for i in s))
        self.assertTrue(all(ids[i].get("ld_season") == "summer" or ids[i].get("ld_state") == "open" for i in w))
        self.assertFalse(set(PR.view_hides(G["meshes"], "summer", "open")) & {i for i, m in ids.items() if m.get("ld_state") == "open"})       # the open state shows the open pit

    def test_variant_meshes_are_never_merged_by_the_renderer(self):
        self.assertTrue(all(m["keep_object"] for m in G["meshes"] if m.get("ld_season") or m.get("ld_state")))


class SceneShape(unittest.TestCase):
    def test_ids_are_unique_and_every_mesh_and_prop_names_its_element(self):
        ids = [m["id"] for m in G["meshes"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(m["element_ids"] and m["element_ids"][0].startswith("ld-") for m in G["meshes"] + G["props"]))

    def test_the_visualisation_garden_is_not_in_the_production_scene(self):
        self.assertFalse([m for m in G["meshes"] + G["props"] if "ld-vis-" in m["id"]])
        from archpipe.landscape.build import visualisation
        L = build.load_layout(PR.LAYOUT)
        V = build.load_layout(ROOT / "knowledge/landscape/concept/final/layout-visualisation.json")
        with self.assertRaises(guard.VisualisationOnlyError):
            guard.refuse(visualisation.build_visualisation(L, V, age=3), "the production villa scene")

    def test_no_prop_asset_name_trips_the_indoor_pot_guard_and_every_prop_carries_its_placement(self):
        for p in G["props"]:
            self.assertNotIn("plant", p["asset"])
            self.assertTrue(p["label"].startswith("dressing: "))
            self.assertIn(p["ldb"]["mode"], ("height", "xyz", "box", "fish"))
            self.assertTrue(Path(p["ldb"]["gltf"]).exists(), p["ldb"]["gltf"])

    def test_every_material_is_a_complete_production_finish_and_every_look_exists_in_blender(self):
        looks = set()
        for name, spec in G["materials"].items():
            self.assertEqual(spec["kind"], "principled", name)
            self.assertEqual(len(spec["base_rgb"]), 3, name)
            self.assertTrue(spec["note"], name)
            if spec.get("garden_look"):
                looks.add(spec["garden_look"])
        tree = ast.parse((ROOT / "src/archpipe/blender/garden_ldb.py").read_text())
        known = next(n.value for n in tree.body if isinstance(n, ast.Assign) and n.targets[0].id == "LOOKS")
        self.assertLessEqual(looks, {k.value for k in known.keys})

    def test_an_unknown_part_material_raises_instead_of_rendering_with_a_guess(self):
        with self.assertRaises(KeyError):
            PR.material("no-such-finish", {})

    def test_standin_masses_are_matte_and_labelled_and_the_count_is_the_plants_without_a_graded_asset(self):
        stand = [m for m in G["materials"] if m.startswith("garden-standin-")]
        self.assertTrue(stand and all(G["materials"][m]["garden_look"] == "standin" and G["materials"][m]["roughness"] == 1.0 and G["materials"][m]["specular"] == 0.0 for m in stand))
        self.assertEqual(G["summary"]["standins"], sum(1 for p in G["plants"] if "STAND-IN" in p["label"]))
        self.assertEqual(G["summary"]["drawn"] + G["summary"]["standins"], G["summary"]["plants"])

    def test_leaf_cards_are_closed_solids_with_uv_windows_and_the_atlas_is_the_real_cutouts(self):
        cards = [m for m in G["meshes"] if m.get("leaf_rects") is not None]
        self.assertTrue(cards)
        for m in cards:
            self.assertEqual(len(m["faces"]), 6 * len(m["leaf_rects"]), m["id"])
            self.assertTrue(all(0 <= r < len(m["leaf_uv"]) for r in m["leaf_rects"]))
            self.assertTrue(all(0 <= c <= 1 for w in m["leaf_uv"] for c in w))
        atlas = [m for m in cards if m["leaf_atlas"] == "star-jasmine"]
        self.assertTrue(atlas and all(len(m["leaf_uv"]) == 15 for m in atlas))             # the 15 live leaves of the atlas, the 5 dead ones dropped


class PropBounds(unittest.TestCase):
    def test_the_committed_bounds_table_is_current_and_places_every_prop_at_its_built_size(self):
        import json
        self.assertEqual(json.loads(PR.BOUNDS_FILE.read_text()), PR.prop_bounds(G["props"]))       # python -m archpipe.landscape.build.production rewrites it
        from archpipe.concept import villa_landscape as LAND
        for p in G["props"]:
            self.assertIn(p["asset"], LAND.PROP_BOUNDS, p["id"])                                    # else the geometry-topology review fails closed on the first garden prop
            x0, y0, z0, x1, y1, z1 = LAND.prop_world_box(p["asset"], p["position"], p["rotation_deg"], p["scale"])
            self.assertAlmostEqual(z0, p["position"][2], places=6)
            if p["ldb"]["mode"] == "height":
                self.assertAlmostEqual(z1 - z0, p["ldb"]["scale_to_height_m"], places=6, msg=p["id"])


class Views(unittest.TestCase):
    def view(self, **kw):
        v = dict(id="v41-south-garden-terrace", when="2026-10-15T10:30:00+03:00", resolution=[1920, 1280], subjects=["landscape-g6-pergola"], hide_meshes=["curtain-x"], visibility_targets=["x"],
                 camera=dict(position=[22.8, -21.6, -1.65], target=[25.57, -25.76, -1.65], lens_mm=24, sensor_mm=36, shift_x=0.0, shift_y=0.0))
        v.update(kw)
        return v

    def test_a_garden_view_loses_the_old_subjects_and_names_only_meshes_no_prop_can_prefix(self):
        v = self.view()
        PR.prepare_view(v, G)
        self.assertNotIn("visibility_targets", v)
        self.assertNotIn("landscape-g6-pergola", v["subjects"])
        ids = {m["id"] for m in G["meshes"]}
        self.assertTrue(all(s in ids and not any(p["id"].startswith(s) for p in G["props"]) for s in v["subjects"]))
        self.assertIn("curtain-x", v["hide_meshes"])                                       # the authored hides stay

    def test_a_view_dated_in_january_hides_the_leaf_on_meshes_and_one_in_october_the_leaf_off(self):
        w = self.view(when="2027-01-15T10:30:00+02:00")
        PR.prepare_view(w, G)
        o = self.view()
        PR.prepare_view(o, G)
        self.assertTrue(set(w["hide_meshes"]) & {m["id"] for m in G["meshes"] if m.get("ld_season") == "summer"})
        self.assertTrue(set(o["hide_meshes"]) & {m["id"] for m in G["meshes"] if m.get("ld_season") == "winter"})
        self.assertFalse(set(w["hide_meshes"]) & {m["id"] for m in G["meshes"] if m.get("ld_season") == "winter"})

    def test_an_interior_view_gets_the_season_hides_but_keeps_its_subjects(self):
        v = self.view(id="v33-basement-north-south", subjects=["living-sofa"])
        PR.prepare_view(v, G)
        self.assertEqual(v["subjects"], ["living-sofa"])
        self.assertTrue(set(v["hide_meshes"]) & {m["id"] for m in G["meshes"] if m.get("ld_season") == "winter"})

    def test_a_camera_on_the_terrace_has_no_garden_subject(self):
        v = self.view(id="v25-top-garden-gate", camera=dict(position=[4.4, -21.7, 1.35], target=[12.4, -22.0, 1.35], lens_mm=24, sensor_mm=36, shift_x=0.0, shift_y=0.0))
        PR.prepare_view(v, G)
        self.assertEqual(v["subjects"], [])

    def test_the_three_key_views_are_garden_views_with_level_24mm_cameras(self):
        base = [dict(self.view(), id="v41-south-garden-terrace", state="day", final_only=True)]
        ks = PR.key_views(base)
        self.assertEqual({k["id"] for k in ks}, set(PR.KEY_VIEWS))
        for k in ks:
            self.assertTrue(PR.is_garden_view(k))
            self.assertEqual(k["camera"]["lens_mm"], 24)
            self.assertEqual(k["camera"]["position"][2], k["camera"]["target"][2])           # level: framing by lens shift, not by tilting the camera


class CamerasAndGround(unittest.TestCase):
    def cam(self, pos, tgt=(26.0, -25.0, -1.65)):
        return dict(id="v40-south-garden-espalier", camera=dict(position=list(pos), target=list(tgt), lens_mm=24, sensor_mm=36, shift_x=0.0, shift_y=0.0))

    def test_a_camera_inside_a_garden_solid_is_moved_the_least_distance_and_the_move_is_recorded(self):
        v = self.cam((22.0, -21.8, -1.65))                         # inside the olive's stand-in in the placeholder set (rendered black)
        self.assertLess(PR.camera_clearance(v["camera"]["position"], G)[0], PR.CLEAR_M)
        self.assertTrue(PR.clear_camera(v, G))
        self.assertGreaterEqual(PR.camera_clearance(v["camera"]["position"], G)[0], PR.CLEAR_M)
        self.assertEqual(v["camera"]["target"], [26.0, -25.0, -1.65])           # the target is kept
        (o,) = v["camera"]["overrides"]
        self.assertEqual(o["field"], "position")
        self.assertIn("GI:", o["reason"])
        self.assertLess(((o["new"][0] - o["prior"][0]) ** 2 + (o["new"][1] - o["prior"][1]) ** 2) ** .5, 3.5)

    def test_a_clear_camera_is_untouched(self):
        v = self.cam((24.5, -22.5, -1.65))
        before = list(v["camera"]["position"])
        if PR.camera_clearance(before, G)[0] >= PR.CLEAR_M:
            self.assertFalse(PR.clear_camera(v, G))
            self.assertEqual(v["camera"]["position"], before)
            self.assertNotIn("overrides", v["camera"])

    def test_the_shell_yard_floor_is_cut_back_under_the_garden_and_the_pond_is_open(self):
        from shapely.geometry import Point, Polygon
        face = [[-0.37, -29.92, -3.0], [28.56, -29.92, -3.0], [28.56, -20.35, -3.0], [-0.37, -20.35, -3.0]]
        shell = [dict(id="shell-039-paving", group="shell", material="paving", faces=[face])]
        self.assertGreater(PR.reveal_ground(shell, G), 50)
        polys = [Polygon([q[:2] for q in f]) for f in shell[0]["faces"]]
        covered = lambda x, y: any(p.contains(Point(x, y)) for p in polys)
        self.assertFalse(covered(1.2, -24.9))                      # the north pond opening is no longer closed over by the floor
        self.assertFalse(covered(25.3, -25.4))                     # nor the paving under the dining table (the garden's own surface is drawn there)
        self.assertTrue(covered(10.0, -22.0))                      # but the floor under the house stays
        self.assertLess(sum(p.area for p in polys), 0.8 * 28.93 * 9.57)


class Rules(unittest.TestCase):
    def test_star_jasmine_stays_two_metres_from_seats_and_arabian_jasmine_by_them(self):
        s = build.build_scene(build.load_layout(PR.LAYOUT), age=3)
        L = build.load_layout(PR.LAYOUT)
        seats = [build.R(x["rect"]) for x in L["seating"]] + [build.R(o["rect"]) for o in L["obstacles"] if o["id"].startswith("pot")]
        t = L["tables"][0]
        seats.append((t["center"][0] - t["size_m"][0] / 2 - .6, t["center"][1] - t["size_m"][1] / 2 - .6, t["center"][0] + t["size_m"][0] / 2 + .6, t["center"][1] + t["size_m"][1] / 2 + .6))
        from archpipe.landscape.build import policy as P
        for o in s.objects:
            if o.meta.get("climbing") and o.meta.get("species") == "trachelospermum_jasminoides":
                self.assertGreaterEqual(min(build._dist_pt_rect(o.meta["at"], r) for r in seats), P.STAR_JASMINE_MIN_FROM_SEAT, o.id)
            if o.meta.get("climbing") and o.meta.get("species") == "jasminum_sambac":
                self.assertLess(min(build._dist_pt_rect(o.meta["at"], r) for r in seats), P.STAR_JASMINE_MIN_FROM_SEAT, o.id)       # a sambac climber far from every seat would have been swapped

    def test_every_wall_has_a_coping_and_every_bed_an_edging_and_the_bbq_is_the_graded_asset(self):
        s = build.build_scene(build.load_layout(PR.LAYOUT), age=3)
        ids = {o.id for o in s.objects}
        for o in s.objects:
            if o.kind == "wall":
                self.assertIn(o.id + "-coping", ids)
            if o.kind == "bed":
                self.assertIn(o.id + "-edging", ids)
        self.assertTrue(s.by_id("ld-s-bbq").asset)
        self.assertEqual(s.by_id("ld-s-bbq").asset["asset_id"], "skf_10162879")


if __name__ == "__main__":
    unittest.main()
