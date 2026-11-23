"""Lane GI: the decided garden in the production scene (landscape/build/production.py and the Blender hook's contract). Pure Python; Blender itself is proven by renders."""
import ast
import copy
import unittest
from pathlib import Path

from archpipe.landscape.build import build, guard, production as PR

ROOT = Path(__file__).resolve().parents[3]
G = PR.garden()
ITEMS = G["meshes"] + G["props"]          # a generated plant's leaf states are props (built in Blender), the fire pit's and fallback plants' are meshes


class Seasons(unittest.TestCase):
    def test_december_to_february_are_leaf_off_and_the_rest_leaf_on(self):
        self.assertEqual([PR.season_for("2026-%02d-15T10:30:00+02:00" % m) for m in range(1, 13)], ["winter", "winter"] + ["summer"] * 9 + ["winter"])

    def test_a_deciduous_object_has_both_variants_under_one_element_id_and_an_evergreen_one_variant(self):
        by = {}
        for m in ITEMS:
            by.setdefault(m["element_ids"][0], set()).add(m.get("ld_season"))
        self.assertEqual(by["ld-plant-s-bed-screen-n-00"], {"summer", "winter"})        # the grape
        self.assertEqual(by["ld-plant-s-bed-wall-00"], {None})                          # petrea: evergreen, one geometry
        self.assertEqual(by["ld-s-tree-crape"], {"summer", "winter"})                   # the crape: FG's tree in both states
        winter = [m for m in ITEMS if m.get("ld_season") == "winter"]
        self.assertTrue(winter and all(m["ldb"]["fg"]["state"] == "leaf-off" for m in winter if "ldb" in m))     # leaf-off = the same skeleton without leaves

    def test_a_summer_view_hides_the_winter_meshes_and_the_open_pit_and_a_winter_view_the_reverse(self):
        s = set(PR.view_hides(ITEMS, "summer"))
        w = set(PR.view_hides(ITEMS, "winter"))
        ids = {m["id"]: m for m in ITEMS}
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
            self.assertIn(p["ldb"]["mode"], ("height", "xyz", "box", "fish", "fg"))
            if p["ldb"]["mode"] != "fg":
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

    def test_every_plant_species_FG_generates_is_a_generated_plant_with_an_honest_label_and_no_standin_remains(self):
        self.assertEqual(G["summary"]["standins"], 0)
        self.assertEqual(G["summary"]["generated"], 65)                      # 59 stand-ins + 6 atlas-card star jasmines of the earlier build
        self.assertEqual(G["summary"]["drawn"] + G["summary"]["generated"], G["summary"]["plants"])
        self.assertEqual(G["summary"]["generated_species_fidelity"], 8)      # star jasmine 6 + grape 2: the only species whose leaf scan is that species
        from archpipe.landscape.foliage import library as FL
        gen = [p for p in G["props"] if p["ldb"]["mode"] == "fg"]
        self.assertTrue(gen)
        for p in gen:
            fg = p["ldb"]["fg"]
            FL.validate_label(fg["label"])
            self.assertEqual(p["fidelity"], fg["label"]["fidelity"])
            self.assertIn(fg["label"]["fidelity"], ("species", "form-class"))
            self.assertTrue(p["caption"] and (fg["label"]["fidelity"] == "species" or "form-class" in p["caption"]))
            self.assertEqual(fg["label"]["seed"], FL.seed_of(p["element_ids"][0]))     # seed from the element id: stable across rebuilds

    def test_the_standin_fallback_still_builds_when_FG_is_switched_off(self):
        from archpipe.landscape.build import planting as PL
        PL.FG = False
        try:
            g = PR.garden()
        finally:
            PL.FG = True
        self.assertEqual(g["summary"]["standins"], 59)                      # the earlier build's count
        self.assertTrue([m for m in g["materials"] if m.startswith("garden-standin-")])

    def test_generated_climbers_stand_off_their_wall_face_in_its_plane_and_reach_a_sourced_height(self):
        from archpipe.landscape.build import planting as PL
        cl = [p for p in G["props"] if p["ldb"]["mode"] == "fg" and p["ldb"]["fg"]["climbing"]]
        self.assertEqual(len(cl), 26)                                       # 24 climbers; the two grapes carry a second (leaf-off) prop
        for p in cl:
            fg = p["ldb"]["fg"]
            c = fg["climbing"]
            self.assertGreaterEqual(c["lift"], PL.FG_CLIMB_LIFT)
            self.assertLessEqual(fg["height_m"], 4.0 - PL.FG_TOP_CLEAR + 1e-6)         # never above the coping of a 4 m wall
            self.assertIn(fg["yaw_deg"], (0.0, 180.0, 90.0, -90.0))
            self.assertLessEqual(fg["spread_m"], c["hi"] - c["lo"] + 1e-6)
        f = PL.species_facts("trachelospermum_jasminoides")
        mat, h3, why = PL.climber_heights("trachelospermum_jasminoides", f, 4.0, 3)
        self.assertAlmostEqual(mat, 3.85)                                    # sourced upper 6.1 m capped 0.15 m under a 4 m coping
        self.assertLess(h3, mat)                                             # age 3 is shorter than mature
        self.assertIn("SOURCED", why)
        self.assertIn("POLICY", PL.climber_heights("vitis_vinifera", PL.species_facts("vitis_vinifera"), 2.1, 3)[2])       # grape: no sourced height, said so


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
        self.assertTrue(set(w["hide_meshes"]) & {m["id"] for m in ITEMS if m.get("ld_season") == "summer"})
        self.assertTrue(set(o["hide_meshes"]) & {m["id"] for m in ITEMS if m.get("ld_season") == "winter"})
        self.assertFalse(set(w["hide_meshes"]) & {m["id"] for m in ITEMS if m.get("ld_season") == "winter"})

    def test_an_interior_view_gets_the_season_hides_but_keeps_its_subjects(self):
        v = self.view(id="v33-basement-north-south", subjects=["living-sofa"])
        PR.prepare_view(v, G)
        self.assertEqual(v["subjects"], ["living-sofa"])
        self.assertTrue(set(v["hide_meshes"]) & {m["id"] for m in ITEMS if m.get("ld_season") == "winter"})

    def test_a_camera_on_the_terrace_has_no_garden_subject(self):
        v = self.view(id="v25-top-garden-gate", camera=dict(position=[4.4, -21.7, 1.35], target=[12.4, -22.0, 1.35], lens_mm=24, sensor_mm=36, shift_x=0.0, shift_y=0.0))
        PR.prepare_view(v, G)
        self.assertEqual(v["subjects"], [])

    def test_the_january_twin_of_the_dining_crown_view_shows_the_leaf_off_crape_and_the_october_one_the_leaf_on(self):
        base = [dict(self.view(), id="v41-south-garden-terrace", state="day", final_only=True, sun={"altitude_deg": 40.07, "azimuth_true_deg": 135.34})]
        ks = {k["id"]: k for k in PR.key_views(base)}
        w, s = ks["gi-dining-crown-winter"], ks["gi-dining-crown-summer"]
        self.assertEqual(w["camera"]["position"], s["camera"]["position"])                   # one camera, two dates
        self.assertNotEqual(w["sun"], s["sun"])                                              # the sun follows the date
        PR.prepare_view(w, G)
        PR.prepare_view(s, G)
        crape_summer = {m["id"] for m in ITEMS if m["element_ids"][0] == "ld-s-tree-crape" and m.get("ld_season") == "summer"}
        crape_winter = {m["id"] for m in ITEMS if m["element_ids"][0] == "ld-s-tree-crape" and m.get("ld_season") == "winter"}
        self.assertTrue(crape_summer and crape_winter)
        self.assertTrue(crape_summer <= set(w["hide_meshes"]) and not crape_winter & set(w["hide_meshes"]))
        self.assertTrue(crape_winter <= set(s["hide_meshes"]) and not crape_summer & set(s["hide_meshes"]))

    def test_the_key_views_are_garden_views_with_level_24mm_cameras(self):
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


class PondSlab(unittest.TestCase):
    """The yard slab's layers under a pond opening hid the liner and every koi (a floor 49 mm under the water, found by ray cast). The cut must remove them at the pond and ONLY there."""
    Z = -3.0

    def mesh(self):
        big = lambda z, up: [[-5, -5, z], [5, -5, z], [5, 5, z], [-5, 5, z]][::1 if up else -1]
        return [dict(id="shell-000", group="shell", material="m", faces=[big(self.Z - 0.2, False), big(self.Z - 0.199, True), big(self.Z, True)], label="")]

    def test_a_pond_opening_is_cut_through_the_slab_layers_and_nothing_else_is(self):
        from shapely.geometry import box as sbox
        ms = self.mesh()
        n = PR._cut_slab_under_ponds(ms, [sbox(-1, -1, 1, 1)], self.Z)
        self.assertEqual(n, 2)                                              # the two layers under the finish; the finish top (z = ground) is reveal_ground's job
        from shapely.geometry import Point, Polygon
        hole = Point(0, 0)
        for f in ms[0]["faces"]:
            z = f[0][2]
            if z < self.Z - 0.05:
                self.assertFalse(Polygon([p[:2] for p in f]).buffer(0).contains(hole), "a slab face still spans the pond")
        self.assertTrue(any(Polygon([p[:2] for p in f]).buffer(0).contains(Point(4.3, 3.1)) for f in ms[0]["faces"] if f[0][2] < self.Z - 0.05))      # negative: the slab away from the pond is kept
        self.assertTrue(any(abs(f[0][2] - self.Z) < 1e-9 for f in ms[0]["faces"]))                                                              # negative: the finish layer is untouched here
        self.assertIn("slab layers cut", ms[0]["label"])

    def test_no_pond_means_no_cut(self):
        ms = self.mesh()
        before = [f for f in ms[0]["faces"]]
        self.assertEqual(PR._cut_slab_under_ponds(ms, [], self.Z), 0)
        self.assertEqual(ms[0]["faces"], before)

    def test_winding_of_the_cut_pieces_follows_the_original_face(self):
        from shapely.geometry import box as sbox
        ms = self.mesh()
        PR._cut_slab_under_ponds(ms, [sbox(-1, -1, 1, 1)], self.Z)
        for f in ms[0]["faces"]:
            if f[0][2] < self.Z - 0.05:
                self.assertEqual(PR._ccw(f), abs(f[0][2] - (self.Z - 0.199)) < 1e-9, f[0][2])         # up face counter-clockwise, down face clockwise


class KoiDepth(unittest.TestCase):
    def test_every_koi_swims_below_the_grille_and_above_the_trench_floor(self):
        from archpipe.landscape.build import policy as P
        for p in G["props"]:
            if p["ldb"]["kind"] != "koi":
                continue
            L = p["ldb"]["length_m"]
            top = p["ldb"]["at"][2] + 0.43 * L / 2            # the asset is banked: measured height 0.30 m for 0.70 m length (0.43 of it)
            water = p["position"][2]
            self.assertLess(top, water - P.POND["grille_top_below_water"] - P.POND["grille_t"], p["id"])
            self.assertGreater(p["ldb"]["at"][2] - 0.43 * L / 2, water - 0.9, p["id"])


class PondSlabArea(unittest.TestCase):
    def test_the_slab_loses_exactly_the_pond_area_even_on_an_L_shaped_face(self):
        """The first cut (Delaunay + covers filter) lost 22.25 m2 per layer where the ponds are 7.28 m2: it dropped triangles over the concave corner. Area is conserved now."""
        from shapely.geometry import Polygon, box as sbox
        L = [[0, 0, -3.2], [10, 0, -3.2], [10, 4, -3.2], [4, 4, -3.2], [4, 10, -3.2], [0, 10, -3.2]]
        ms = [dict(id="s", group="shell", material="m", faces=[L, L[::-1]], label="")]
        pond = sbox(1, 1, 3, 2)
        PR._cut_slab_under_ponds(ms, [pond], -3.0)
        total = sum(Polygon([p[:2] for p in f]).area for f in ms[0]["faces"])
        self.assertAlmostEqual(total, 2 * (Polygon([p[:2] for p in L]).area - pond.area), places=6)
