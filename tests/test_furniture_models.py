"""WP4-A: real furniture models replace a procedural stand-in only where a checked fit rule allows it (uniform
scale, never distorted). One function (villa_render.fit_uniform_scale) drives both the fallback decision and the
GUARD re-check below, using bounds read from ops/workstation/library-manifest.json itself -- never a pasted
literal -- so a re-export of an asset changes the fit here too.
"""
import json
import sys
import unittest
from pathlib import Path

from archpipe.concept import villa_render as VR
from archpipe.concept import villa_furnish as F
from archpipe import villa_render_contract as C
from archpipe.furniture_orientation import check_model_orientation, model_yaw
sys.path.insert(0, str(VR.ROOT / "ops" / "workstation"))
from front_axis import estimate_front, directional_role, measured_or_manual_front

MANIFEST = json.loads((VR.ROOT / "ops" / "workstation" / "library-manifest.json").read_text())
BOUNDS = {p["id"]: p["bounds_m"] for p in MANIFEST["props"] if p.get("bounds_m")}

SCENE = VR.build()


class FitRule(unittest.TestCase):
    def test_product_size_comes_from_native_bounds_with_one_scale(self):
        for mark, entry in F.PRODUCT.items():
            nx, ny, nz = VR.native_size(BOUNDS[entry["asset"]])
            self.assertAlmostEqual(entry["w"], nx * entry["scale"], places=5, msg=mark)
            self.assertAlmostEqual(entry["d"], nz * entry["scale"], places=5, msg=mark)
            self.assertAlmostEqual(entry["h"], ny * entry["scale"], places=5, msg=mark)

    def test_old_generic_footprint_fails_for_real_living_sofa(self):
        generic = next(i for i in F.layout(products=False) if i["id"] == "living-sofa")
        fit = VR.fit_uniform_scale(generic["w"], generic["d"], generic["h"], BOUNDS["sf_minotti_sofa"])
        self.assertFalse(fit["ok"])
        self.assertIn("aspect mismatch", fit["reason"])

    def test_old_coffee_position_rejects_real_living_sofa_but_relayout_passes(self):
        # Reproduce the WP4b failure with the old 0.6 m deep table at -26.113.
        items = F.layout(products=False)
        sofa = next(i for i in items if i["id"] == "living-sofa")
        coffee = next(i for i in items if i["id"] == "living-coffee")
        coffee.update(cy=-26.113, d=0.6)
        p = F.PRODUCT["living-sofa"]
        sofa["cy"] += (p["d"] - sofa["d"]) / 2
        sofa["w"], sofa["d"] = p["w"], p["d"]
        result = F.check(items, _extended=True)
        self.assertTrue(any("living-sofa" in p for p in result["clearances"]["problems"]), result["clearances"])
        placed = F.layout()
        self.assertEqual(next(i for i in placed if i["id"] == "living-sofa")["product"], "sf_minotti_sofa")
        self.assertEqual(F.check(placed)["clearances"]["status"], "pass")

    def test_lounge_fallback_reproduces_the_blocked_route_after_rearrangement(self):
        items = F.layout(products=False)
        by_id = {it["id"]: it for it in items}
        sofa = by_id["lounge-sofa"]
        p = F.PRODUCT["lounge-sofa"]
        sofa["cy"] += (p["d"] - sofa["d"]) / 2
        sofa["w"], sofa["d"] = p["w"], p["d"]
        by_id["lounge-coffee"].update(cy=-24.990)
        by_id["lounge-armchair"].update(cx=8.78)
        problems = F.check(items, _extended=True)["routes"]["problems"]
        self.assertTrue(any("lounge-nook/pantry" in problem for problem in problems), problems)
    def test_manifest_loaded_from_the_real_file(self):
        # VR.MANIFEST_BOUNDS must be the SAME data this test reads independently, not a copy that could drift.
        self.assertEqual(VR.MANIFEST_BOUNDS, BOUNDS)
        self.assertIn("sf_modern_low_sofa", BOUNDS)
        self.assertIn("sf_rug_round_jute", BOUNDS)

    def test_real_mismatch_triggers_the_fallback(self):
        """lounge-sofa (2.600 x 0.950 m, h 0.85) against sf_modern_low_sofa's REAL measured bounds -- this is the
        task's own assigned mapping, not a fabricated negative case. The model's footprint aspect (its width is
        much wider relative to its depth than the plan's 4-seat sofa footprint) misses by more than 12%, so the
        procedural builder stays and the reason is recorded."""
        fit = VR.fit_uniform_scale(2.600, 0.950, 0.850, BOUNDS["sf_modern_low_sofa"])
        self.assertFalse(fit["ok"])
        self.assertIn("aspect mismatch", fit["reason"])
        self.assertGreater(fit["aspect_mismatch"], VR.FIT_ASPECT_TOL)
        # measured, not asserted loosely: this specific pair mismatches by roughly a third
        self.assertAlmostEqual(fit["aspect_mismatch"], 0.347, places=2)

    def test_a_real_pass_the_living_rug_against_sf_rug_round_jute(self):
        """The living rug's footprint remains compatible with the real round jute rug."""
        fit = VR.fit_uniform_scale(2.6, 2.4, min(2.6, 2.4), BOUNDS["sf_rug_round_jute"], height_tol=1.0)
        self.assertTrue(fit["ok"], fit.get("reason"))
        self.assertLess(fit["aspect_mismatch"], VR.FIT_ASPECT_TOL)

    def test_degenerate_inputs_fall_back_not_crash(self):
        self.assertFalse(VR.fit_uniform_scale(0, 1, 1, BOUNDS["sf_chelsea_bed"])["ok"])
        self.assertFalse(VR.fit_uniform_scale(1, 1, 1, {})["ok"])
        self.assertFalse(VR.fit_uniform_scale(1, 1, 1, None)["ok"])

    def test_uniform_scale_never_distorts(self):
        """The SAME scale factor applies to every native axis -- there is no independent x/y/z scale anywhere in
        fit_uniform_scale's return value, only one `scale`."""
        fit = VR.fit_uniform_scale(2.6, 2.4, 1.2, BOUNDS["sf_rug_round_jute"], height_tol=1.0)
        self.assertEqual(set(fit) & {"scale"}, {"scale"})
        self.assertNotIn("scale_x", fit)
        self.assertNotIn("scale_z", fit)


class GuardOnThePlacedScene(unittest.TestCase):
    """Re-derive each placed model's world footprint from its own scale/native size and check it against the
    GUARD: inside its plan footprint + 20 mm, using the SAME fit_uniform_scale the fallback decision used (so
    nothing that passed fit can fail this guard)."""

    def test_every_placed_model_world_box_is_within_footprint_plus_20mm(self):
        self.assertTrue(SCENE["models"], "expected at least one real model placed (the living rug)")
        for m in SCENE["models"]:
            bounds = BOUNDS[m["asset"]]
            nx, ny, nz = VR.native_size(bounds)
            world_w, world_d = nx * m["scale"], nz * m["scale"]
            # rot is a multiple of 90 degrees; at +-90 the footprint axes swap
            swapped = round(m["rotation_deg"][2]) % 180 == 90
            fw, fd = (world_d, world_w) if swapped else (world_w, world_d)
            mark = m["replaces"].removeprefix("furn-")
            item = next((i for i in F.layout() if i["id"] == mark), None)
            if item is not None:
                fp = F.footprint(item)
                self.assertLessEqual(fw, fp[2] - fp[0] + 0.020, m["id"])
                self.assertLessEqual(fd, fp[3] - fp[1] + 0.020, m["id"])

    def test_replaced_procedural_mesh_stays_in_the_scene_but_hidden(self):
        """The duvet cloth sim and any other collider keys objects by their "furn-<mark>-" name prefix
        (villa_scene.build_curtains / the duvet loop), so a replaced piece's procedural mesh must still be an
        object in the scene -- only hidden from every ray, never deleted."""
        replaced_prefixes = {m["replaces"] for m in SCENE["models"]}
        self.assertTrue(replaced_prefixes)
        hide_vis = {"camera": False, "shadow": False, "diffuse": False, "glossy": False, "transmission": False}
        for prefix in replaced_prefixes:
            hidden = [mesh for mesh in SCENE["meshes"] if mesh["id"] == prefix or mesh["id"].startswith(prefix)]
            self.assertTrue(hidden, prefix)
            for mesh in hidden:
                self.assertEqual(mesh.get("visibility"), hide_vis, mesh["id"])

    def test_fallback_pieces_keep_their_procedural_mesh_visible(self):
        """lounge-sofa is the real fallback (see FitRule above): its procedural mesh must render normally, not be
        hidden by a model that was never placed."""
        lounge_meshes = [m for m in SCENE["meshes"] if m["id"].startswith("furn-lounge-sofa-")]
        self.assertTrue(lounge_meshes)
        for m in lounge_meshes:
            self.assertNotIn("visibility", m)

    def test_models_pass_the_villa_render_contract(self):
        errors = [e for e in C.validate_scene(SCENE) if e.startswith("models")]
        self.assertEqual(errors, [])

    def test_real_minotti_old_yaw_fires_and_corrected_scene_is_quiet(self):
        sofa = next(m for m in SCENE["models"] if m["asset"] == "sf_minotti_sofa")
        old = dict(sofa, rotation_deg=[0, 0, sofa["layout_rotation_deg"]])
        # The historical defect is captured by value: native +Z, uncorrected layout yaw.
        self.assertEqual(old["front_axis"], "+Z")
        with self.assertRaisesRegex(ValueError, "front-axis yaw"):
            check_model_orientation(old)
        for model in SCENE["models"]:
            check_model_orientation(model)
        reversed_chair = next(m for m in SCENE["models"] if m["asset"] == "sf_probber_cane_armchair")
        self.assertEqual(reversed_chair["front_axis"], "-Z")
        with self.assertRaisesRegex(ValueError, "front-axis yaw"):
            check_model_orientation(dict(reversed_chair, rotation_deg=[0, 0, reversed_chair["layout_rotation_deg"] + 180]))

    def test_real_mesh_half_statistics_estimate_opposite_fronts(self):
        # Fixed measurements of the actual glTF vertices, in native units, at the 98th height percentile.
        minotti = {"+X": 87.4405, "-X": 86.5686, "+Z": 57.7909, "-Z": 87.4536}
        probber = {"+X": 63.5876, "-X": 64.5777, "+Z": 64.4515, "-Z": 57.3433}
        self.assertEqual(estimate_front(minotti), "+Z")
        self.assertEqual(estimate_front(probber), "-Z")
        self.assertFalse(directional_role("bedside table"))
        self.assertTrue(directional_role("parents' bed"))
        manual = {"id": "sf_minotti_sofa", "role": "garden-living sofa", "front_axis": "+Z"}
        measured_or_manual_front(manual, Path("unused.gltf"))
        self.assertEqual(manual["front_axis_basis"], "lead-verified")
        with self.assertRaisesRegex(ValueError, "front_axis"):
            model_yaw(0, None)
        for axis in ("+X", "-X", "+Z", "-Z"):
            clean = {"id": "any-model", "front_axis": axis,
                     "rotation_deg": [0, 0, model_yaw(37, axis)], "layout_rotation_deg": 37}
            check_model_orientation(clean)
            with self.assertRaisesRegex(ValueError, "front-axis yaw"):
                check_model_orientation(dict(clean, rotation_deg=[0, 0, clean["rotation_deg"][2] + 2]))


class ModelsContract(unittest.TestCase):
    """Negative tests for the villa-render/1 `models` field (WP4-A)."""

    def _base(self):
        return {"schema": "villa-render/1", "id": "x", "north": {"model_y_bearing_deg": 0},
                "library_root": "root", "materials": {}, "meshes": [], "lights": [], "props": [],
                "exposure": {}, "sky": {}, "views": [], "notes": []}

    def test_missing_replaces_prefix_is_rejected(self):
        scene = self._base()
        scene["models"] = [{"id": "m1", "asset": "sf_rug_round_jute", "position": [0, 0, 0],
                            "rotation_deg": [0, 0, 0], "scale": 1.0}]
        errors = C.validate_scene(scene)
        self.assertTrue(any("models[0].replaces" in e for e in errors), errors)

    def test_negative_scale_is_rejected(self):
        scene = self._base()
        scene["models"] = [{"id": "m1", "asset": "sf_rug_round_jute", "position": [0, 0, 0],
                            "rotation_deg": [0, 0, 0], "scale": -1.0, "replaces": "rug-living"}]
        errors = C.validate_scene(scene)
        self.assertTrue(any("models[0].scale" in e for e in errors), errors)

    def test_a_valid_model_produces_no_errors(self):
        scene = self._base()
        scene["models"] = [{"id": "m1", "asset": "props/rug", "position": [0, 0, 0],
                            "rotation_deg": [0, 0, 0], "layout_rotation_deg": 0,
                            "front_axis": "none", "scale": 0.5, "replaces": "rug-living"}]
        errors = [e for e in C.validate_scene(scene) if e.startswith("models")]
        self.assertEqual(errors, [])


class GlassIOR(unittest.TestCase):
    """WP4-B4: the parents' ensuite bath screen carries its own measured transmittance (0.91) and index of
    refraction (1.52) from revit_spec's bath_fittings, not the generic glass-guard material."""

    def test_scene_carries_the_measured_ior_and_transmittance(self):
        mat = SCENE["materials"]["glass-bath-screen"]
        self.assertAlmostEqual(mat["transmittance"], 0.91)
        self.assertAlmostEqual(mat["ior"], 1.52)
        self.assertEqual(mat["roughness"], 0.0)

    def test_out_of_range_ior_is_rejected(self):
        scene = {"schema": "villa-render/1", "id": "x", "north": {"model_y_bearing_deg": 0},
                 "library_root": "root", "meshes": [], "lights": [], "props": [], "exposure": {}, "sky": {},
                 "views": [], "notes": [],
                 "materials": {"bad-glass": {"kind": "glass", "base_rgb": [1, 1, 1], "transmittance": 0.9,
                                             "ior": 4.0}}}
        errors = C.validate_scene(scene)
        self.assertTrue(any("materials.bad-glass.ior" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
