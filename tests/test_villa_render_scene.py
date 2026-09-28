"""Contract checks for the laptop-side villa renderer inputs."""
import ast
import copy
import math
import sys
import subprocess
import unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import archpipe.villa_render_contract as render_contract
from archpipe.villa_render_contract import (emission_strength, emissive_mesh_output_factor,
                                            mesh_batch_key, mesh_bbox_corners, sky_state_for_view,
                                            validate_scene)
sys.path.insert(0, str(ROOT / "scripts"))
from villa_render import poll_remote, select_views, villa_caption, villa_qa_context, villa_qa_scope


def blender_function(name):
    """Load a bpy-independent renderer function without importing Blender."""
    source = (ROOT / "src/archpipe/blender/villa_scene.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
    namespace = {"contract": render_contract}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(ROOT / "src/archpipe/blender/villa_scene.py"), "exec"), namespace)
    return namespace[name]


class VillaRenderContractTest(unittest.TestCase):
    def test_poll_recovers_timeout_without_starting_another_job(self):
        completed = SimpleNamespace(returncode=0, stdout=b"0", stderr=b"")
        with patch("villa_render._ssh", side_effect=[subprocess.TimeoutExpired("ssh", 30), completed]) as ssh, \
                patch("villa_render.time.sleep"):
            self.assertIs(poll_remote("worker", "cat job/status", "job"), completed)
        self.assertEqual([c.args[1] for c in ssh.call_args_list], ["cat job/status"] * 2)

    def test_poll_distinguishes_missing_status_from_lost_connection(self):
        missing = SimpleNamespace(returncode=1, stdout=b"", stderr=b"not found")
        with patch("villa_render._ssh", return_value=missing) as ssh:
            self.assertIs(poll_remote("worker", "cat job/status", "job"), missing)
            ssh.assert_called_once()
        disconnected = SimpleNamespace(returncode=255, stdout=b"", stderr=b"connection lost")
        with patch("villa_render._ssh", return_value=disconnected) as ssh, patch("villa_render.time.sleep"):
            with self.assertRaisesRegex(RuntimeError, "detached job may still be rendering"):
                poll_remote("worker", "cat job/status", "job")
            self.assertEqual(ssh.call_count, 3)

    def test_calibrated_transport_does_not_discard_bounced_light(self):
        configure = blender_function("configure_cycles")
        scene = SimpleNamespace(cycles=SimpleNamespace(), render=SimpleNamespace())
        configure.__globals__["bpy"] = SimpleNamespace(context=SimpleNamespace(scene=scene))
        configure(True)
        self.assertEqual(scene.cycles.sample_clamp_indirect, 0)
        self.assertEqual(scene.cycles.sample_clamp_direct, 0)
        self.assertGreaterEqual(scene.cycles.diffuse_bounces, 16)
        self.assertGreaterEqual(scene.cycles.transparent_max_bounces, 16)

    @classmethod
    def setUpClass(cls):
        cls.valid = {
            "schema": "villa-render/1", "id": "test", "north": {"model_y_bearing_deg": 20},
            "library_root": "$HOME/archpipe/assets/library",
            "materials": {"white": {"kind": "principled", "base_rgb": [0.8, 0.8, 0.8]}},
            "meshes": [{"id": "floor", "group": "shell", "material": "white",
                        "room": "room", "label": "floor", "faces": [
                            [[0,0,0], [1,0,0], [1,1,0], [0,1,0]]]}],
            "lights": [{"id": "lamp", "room": "room", "layer": "ambient", "type": "ies",
                        "position": [0.5,0.5,2], "aim": [0,0,-1], "spin_deg": 0,
                        "ies": "test.ies", "lumens": 600, "cct_k": 3000, "cri": 90, "dimmer": 1,
                        "product": {"manufacturer": "test", "code": "test", "generic": True}}],
            "views": [{"id": "v01", "title": "Test view", "when": "2026-10-15T15:30:00+03:00",
                       "state": "day", "sun": {"altitude_deg": 30, "azimuth_true_deg": 200},
                       "camera": {"position": [0.5,-1,1], "target": [0.5,0.5,1],
                                  "lens_mm": 24, "sensor_mm": 36},
                       "resolution": [640,400], "samples": 64, "layers_on": ["ambient"],
                       "dimmers": {}, "subjects": ["floor"], "exposure": "day"}],
            "exposure": {"day": {"ev100": 9, "white_balance_k": 5500},
                         "evening": {"ev100": 3.5, "white_balance_k": 3200}},
            "sky": {"day": "nishita", "evening": {"hdri": "sky.exr", "horizontal_lux": 400}},
            "notes": []}

    def test_valid_scene(self):
        self.assertEqual(validate_scene(self.valid), [])

    def test_wrong_schema(self):
        scene = copy.deepcopy(self.valid)
        scene["schema"] = "villa-render/2"
        self.assertIn("schema", " ".join(validate_scene(scene)))

    def test_missing_material(self):
        scene = copy.deepcopy(self.valid)
        scene["meshes"][0]["material"] = "missing"
        self.assertIn("unknown material", " ".join(validate_scene(scene)))

    def test_nonplanar_face(self):
        scene = copy.deepcopy(self.valid)
        scene["meshes"][0]["faces"][0][0][2] += 0.002
        self.assertIn("nonplanar", " ".join(validate_scene(scene)))

    def test_planarity_tolerance(self):
        scene = copy.deepcopy(self.valid)
        scene["meshes"][0]["faces"][0][0][2] += 0.0005
        self.assertEqual(validate_scene(scene), [])

    def test_degenerate_polygon(self):
        scene = copy.deepcopy(self.valid)
        face = scene["meshes"][0]["faces"][0]
        face[1] = face[0]
        self.assertIn("degenerate", " ".join(validate_scene(scene)))

    def test_missing_ies_and_invalid_aim(self):
        scene = copy.deepcopy(self.valid)
        scene["lights"][0]["ies"] = "../escape.ies"
        scene["lights"][0]["aim"] = [0, 0, 0]
        errors = " ".join(validate_scene(scene))
        self.assertIn("safe relative IES", errors)
        self.assertIn("nonzero vector", errors)

    def test_invalid_view(self):
        scene = copy.deepcopy(self.valid)
        scene["views"][0]["camera"]["lens_mm"] = 0
        scene["views"][0]["layers_on"] = ["unknown"]
        scene["views"][0]["sun"] = None
        errors = " ".join(validate_scene(scene))
        self.assertIn("lens_mm", errors)
        self.assertIn("layers_on", errors)
        self.assertIn("sun", errors)

    def test_invalid_time_and_duplicate_id(self):
        scene = copy.deepcopy(self.valid)
        scene["views"][0]["when"] = "tomorrow"
        scene["lights"][0]["id"] = "floor"
        errors = " ".join(validate_scene(scene))
        self.assertIn("timezone-aware", errors)
        self.assertIn("unique nonempty", errors)

    def test_explicit_zero_dimmer(self):
        scene = copy.deepcopy(self.valid)
        scene["lights"][0]["dimmer"] = 0
        scene["views"][0]["dimmers"] = {"ambient": 0}
        self.assertEqual(validate_scene(scene), [])

    def test_emissive_exitance_integrates_to_requested_flux(self):
        radius = 0.15
        area = 4 * math.pi * radius**2
        exitance = 800 / area
        strength = emission_strength(exitance)
        # Independent midpoint integration of a Lambertian hemisphere.
        flux = 0.0
        bins = 10000
        for i in range(bins):
            theta = (i + 0.5) * (math.pi/2) / bins
            flux += strength * math.cos(theta) * 2*math.pi*math.sin(theta) * (math.pi/2)/bins * area
        self.assertAlmostEqual(flux, 800, delta=0.01)
        self.assertAlmostEqual((800/(4*math.pi))*2.55/(2.55**3), 9.7902, delta=0.001)

    def test_emissive_and_translucent_require_different_fields(self):
        scene = copy.deepcopy(self.valid)
        scene["materials"]["white"] = {"kind": "emissive", "base_rgb": [1,1,1],
                                         "emission_lm_per_m2": 1000, "cct_k": 3000}
        self.assertEqual(validate_scene(scene), [])
        scene["materials"]["white"] = {"kind": "translucent", "base_rgb": [1,1,1],
                                         "transmittance": 0.5}
        self.assertEqual(validate_scene(scene), [])
        del scene["materials"]["white"]["transmittance"]
        self.assertIn("transmittance", " ".join(validate_scene(scene)))

    def test_ray_visibility_and_keep_object(self):
        scene = copy.deepcopy(self.valid)
        mesh = scene["meshes"][0]
        mesh["visibility"] = {"camera": False, "shadow": True, "diffuse": False,
                              "glossy": True, "transmission": True}
        self.assertEqual(validate_scene(scene), [])
        self.assertIsNotNone(mesh_batch_key(mesh, "principled"))
        mesh["keep_object"] = True
        self.assertIsNone(mesh_batch_key(mesh, "principled"))
        mesh["visibility"]["bogus"] = True
        self.assertIn("visibility", " ".join(validate_scene(scene)))

    def test_mesh_detail_fields_accept_boundaries(self):
        scene = copy.deepcopy(self.valid)
        mesh = scene["meshes"][0]
        for bevel in (0, 0.006, 0.05):
            for subdivision in (0, 1, 2):
                mesh["bevel_m"] = bevel
                mesh["subdivide"] = subdivision
                self.assertEqual(validate_scene(scene), [])

    def test_mesh_detail_fields_reject_invalid_values(self):
        scene = copy.deepcopy(self.valid)
        mesh = scene["meshes"][0]
        for value in (-0.001, 0.051, True, "0.006", float("nan")):
            mesh["bevel_m"] = value
            self.assertIn("bevel_m", " ".join(validate_scene(scene)))
        del mesh["bevel_m"]
        for value in (-1, 3, True, 1.0, "1"):
            mesh["subdivide"] = value
            self.assertIn("subdivide", " ".join(validate_scene(scene)))

    def test_bevel_and_subdivision_force_separate_objects(self):
        plain = copy.deepcopy(self.valid["meshes"][0])
        other = copy.deepcopy(plain)
        other["id"] = "other"
        detail = copy.deepcopy(plain)
        detail["id"] = "detail"
        detail["bevel_m"] = 0.006
        detail["subdivide"] = 2
        self.assertEqual(mesh_batch_key(plain, "principled"), mesh_batch_key(other, "principled"))
        self.assertIsNone(mesh_batch_key(detail, "principled"))
        batches = []
        detailed = []
        build = blender_function("build_meshes")
        build.__globals__["add_mesh_batch"] = lambda specs, name, material, warnings: batches.append(
            ([spec["id"] for spec in specs], name)) or SimpleNamespace(name=name)
        build.__globals__["add_mesh_detail"] = lambda obj, spec: detailed.append((obj.name, spec["id"]))
        objects = build([plain, other, detail], {"white": object()},
                        {"white": {"kind": "principled"}}, [])
        self.assertEqual([ids for ids, _ in batches], [["floor", "other"], ["detail"]])
        self.assertIs(objects["floor"], objects["other"])
        self.assertIsNot(objects["floor"], objects["detail"])
        self.assertEqual(detailed, [("detail", "detail")])
        del detail["bevel_m"]
        self.assertIsNone(mesh_batch_key(detail, "principled"))

    def test_mesh_detail_modifiers_are_ordered_and_configured(self):
        class Modifiers:
            def __init__(self):
                self.items = []
            def new(self, name, kind):
                modifier = SimpleNamespace(name=name, type=kind)
                self.items.append(modifier)
                return modifier
        class BMesh:
            def __init__(self):
                self.faces = [SimpleNamespace(smooth=False)]
                self.edges = [SimpleNamespace(is_manifold=True, smooth=True,
                                              calc_face_angle=lambda fallback: math.radians(45))]
            def from_mesh(self, mesh):
                pass
            def to_mesh(self, mesh):
                pass
            def free(self):
                pass
        mesh = BMesh()
        obj = SimpleNamespace(data=object(), modifiers=Modifiers())
        detail = blender_function("add_mesh_detail")
        detail.__globals__.update(bmesh=SimpleNamespace(new=lambda: mesh), math=math)
        detail(obj, {"bevel_m": 0.006, "subdivide": 2})
        self.assertTrue(mesh.faces[0].smooth)
        self.assertFalse(mesh.edges[0].smooth)
        self.assertEqual([modifier.type for modifier in obj.modifiers.items], ["BEVEL", "SUBSURF"])
        bevel, subdivision = obj.modifiers.items
        self.assertEqual((bevel.width, bevel.segments, bevel.limit_method), (0.006, 2, "ANGLE"))
        self.assertAlmostEqual(bevel.angle_limit, math.radians(30))
        self.assertTrue(bevel.harden_normals)
        self.assertEqual((subdivision.levels, subdivision.render_levels), (2, 2))

    def test_optional_mesh_layer_and_emissive_dimming(self):
        scene = copy.deepcopy(self.valid)
        mesh = scene["meshes"][0]
        mesh["layer"] = "decorative"
        self.assertEqual(validate_scene(scene), [])
        view = scene["views"][0]
        self.assertEqual(emissive_mesh_output_factor(mesh, view), 0)
        view["layers_on"].append("decorative")
        view["dimmers"] = {"decorative": 0.4}
        self.assertEqual(emissive_mesh_output_factor(mesh, view), 0.4)
        view["dimmers"]["decorative"] = 0
        self.assertEqual(emissive_mesh_output_factor(mesh, view), 0)
        del mesh["layer"]
        self.assertEqual(emissive_mesh_output_factor(mesh, view), 1)
        mesh["layer"] = "unknown"
        self.assertIn("unknown lighting layer", " ".join(validate_scene(scene)))

    def test_layered_emitters_have_independent_strength_and_unlit_base(self):
        class Material:
            def __init__(self):
                self.name = "opal"
                self.node_tree = SimpleNamespace(nodes={
                    "Villa Emission": SimpleNamespace(inputs={"Strength": SimpleNamespace(default_value=100/math.pi)}),
                    "Principled BSDF": SimpleNamespace(base_rgb=(0.9, 0.9, 0.85))})
            def copy(self):
                return copy.deepcopy(self)
        shared = Material()
        specs = [{"id": "a", "material": "opal", "layer": "ambient"},
                 {"id": "b", "material": "opal", "layer": "decorative"},
                 {"id": "c", "material": "opal"}]
        objects = {spec["id"]: SimpleNamespace(data=SimpleNamespace(materials=[shared])) for spec in specs}
        split = blender_function("layered_emissive_materials")(
            specs, objects, {"opal": {"kind": "emissive"}})
        self.assertIsNot(objects["a"].data.materials[0], objects["b"].data.materials[0])
        self.assertIs(objects["c"].data.materials[0], shared)
        sources = [{"id": spec["id"], "exitance_lm_per_m2": 100, "emitted_lumens": 50}
                   for spec in specs]
        view = {"layers_on": ["decorative"], "dimmers": {"decorative": 0.4}}
        current = blender_function("set_emissive_view")(
            sources, {spec["id"]: spec for spec in specs}, split, view)
        self.assertEqual(split["a"].inputs["Strength"].default_value, 0)
        self.assertAlmostEqual(split["b"].inputs["Strength"].default_value, 40/math.pi)
        self.assertAlmostEqual(shared.node_tree.nodes["Villa Emission"].inputs["Strength"].default_value, 100/math.pi)
        self.assertEqual([item["emitted_lumens"] for item in current], [0, 20, 50])
        self.assertEqual(objects["a"].data.materials[0].node_tree.nodes["Principled BSDF"].base_rgb,
                         (0.9, 0.9, 0.85))

    def test_props_are_labelled_dressing_and_validated(self):
        scene = copy.deepcopy(self.valid)
        prop = {"id": "vase", "asset": "brass_vase_03", "position": [1,2,0.8],
                "rotation_deg": [0,0,90], "scale": 0.8, "label": "dressing: brass vase"}
        scene["props"] = [prop]
        self.assertEqual(validate_scene(scene), [])
        prop["label"] = "design vase"
        prop["asset"] = "../escape"
        errors = " ".join(validate_scene(scene))
        self.assertIn("dressing:", errors)
        self.assertIn("safe relative", errors)

    def test_night_sky_free_exposure_and_bounces(self):
        scene = copy.deepcopy(self.valid)
        scene["sky"]["night"] = {"hdri": "dikhololo_night.exr", "horizontal_lux": 0.3}
        scene["exposure"] = {"lamps": {"ev100": 1.25, "white_balance_k": 3200}}
        view = scene["views"][0]
        view["state"] = "night"
        view["exposure"] = "lamps"
        view["max_bounces"] = 12
        self.assertEqual(validate_scene(scene), [])
        view["max_bounces"] = -1
        self.assertIn("max_bounces", " ".join(validate_scene(scene)))
        del scene["sky"]["night"]
        self.assertIn("matching sky", " ".join(validate_scene(scene)))

    def test_exterior_dusk_reuses_evening_sky_with_own_exposure(self):
        scene = copy.deepcopy(self.valid)
        scene["exposure"] = {"dusk-facade": {"ev100": 7.25, "white_balance_k": 4600}}
        view = scene["views"][0]
        view["state"] = "exterior-dusk"
        view["exposure"] = "dusk-facade"
        self.assertEqual(validate_scene(scene), [])
        self.assertEqual(sky_state_for_view(view["state"]), "evening")
        # a render report must carry the scene measurements the QA checks read (qa_scene); a report without them
        # fails loudly rather than silently skipping those checks
        context = villa_qa_context(scene, view, {"subjects": [], "white_balance_applied": True,
                                                 "lights_on_count": 0, "camera_pitch_deg": 0.0, "qa_scene": {"windows": [], "glass": [], "materials": [], "textiles": [], "soft_goods": [], "bedding": []}})
        self.assertFalse(context["daylight"])
        del scene["sky"]["evening"]
        self.assertIn("matching sky", " ".join(validate_scene(scene)))

    def test_merging_keeps_source_subject_bounds(self):
        floor = copy.deepcopy(self.valid["meshes"][0])
        other = copy.deepcopy(floor)
        other["id"] = "far-floor"
        other["faces"] = [[[10+x,y,z] for x,y,z in floor["faces"][0]]]
        self.assertEqual(mesh_batch_key(floor, "principled"), mesh_batch_key(other, "principled"))
        self.assertEqual(max(p[0] for p in mesh_bbox_corners(floor)), 1)
        self.assertEqual(min(p[0] for p in mesh_bbox_corners(other)), 10)
        other["group"] = "furniture"
        self.assertIsNone(mesh_batch_key(other, "principled"))
        self.assertIsNone(mesh_batch_key(floor, "emissive"))

    def test_qa_daylight_is_day_only_and_zero_dimmed_ies_is_excluded(self):
        scene = copy.deepcopy(self.valid)
        view = scene["views"][0]
        report = {"subjects": [], "white_balance_applied": True, "lights_on_count": 1, "camera_pitch_deg": 0.0, "qa_scene": {"windows": [], "glass": [], "materials": [], "textiles": [], "soft_goods": [], "bedding": []}}
        self.assertTrue(villa_qa_context(scene, view, report)["daylight"])
        for state in ("evening", "night"):
            view["state"] = state
            context = villa_qa_context(scene, view, report)
            self.assertFalse(context["daylight"])
            self.assertFalse(context["sky"]["sun"])
        scene["lights"][0]["dimmer"] = 0
        self.assertEqual(villa_qa_context(scene, view, report)["lights"]["count"], 0)

    def test_qa_scope_and_caption_keep_props_out_of_design(self):
        scene = copy.deepcopy(self.valid)
        view = scene["views"][0]
        prop = {"id": "vase", "asset": "brass_vase_03", "label": "dressing: brass vase",
                "objects": ["prop-vase-000"], "in_frame": True}
        report = {"warnings": [], "imported_props": [prop]}
        qa = {"checks": [{"check": "highlight_clipping"}, {"check": "view_subject:floor"}]}
        scope = villa_qa_scope(qa)
        self.assertIn("highlight_clipping", scope["applied"])
        self.assertIn("window_view", scope["omitted"])
        caption = villa_caption(scene, view, report, qa)
        self.assertEqual(caption["dressing (not design)"], [prop])
        self.assertNotIn("vase", caption["design"]["meshes"])

    def test_calibration_only_selection(self):
        views = {"v01": {}, "v02": {}}
        self.assertEqual(select_views(views, "none", True), [])
        self.assertEqual(select_views(views, "all", False), ["v01", "v02"])
        with self.assertRaises(ValueError):
            select_views(views, "none", False)


if __name__ == "__main__":
    unittest.main()
