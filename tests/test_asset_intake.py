"""Asset intake regressions, including frozen values from the round-three manifest."""
import json
import importlib.util
import sys
import types
from unittest.mock import patch
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from archpipe.asset_intake import (audit_scene_manifest, validate_entry, validate_manifest,
                                   manifest_assumptions, manifest_overrides, require_registered_asset)

MANIFEST = json.loads((ROOT / "ops/workstation/library-manifest.json").read_text(encoding="utf-8"))
PROPS = {p["id"]: p for p in MANIFEST["props"]}


def complete(role="armchair"):
    # The named dimensions and range belong to this fixture, not to a real catalogue.
    return dict(id="measured_test_chair", role=role, source_url="https://example.org/test-chair",
                licence="CC-BY", author="Fixture author", credit="Fixture author, CC-BY",
                units_normalised={"scale_factor": 1.0, "reason": "fixture coordinates are metres"},
                up_axis="+Y", front_axis="+Z", bounds_m={"min": [0, 0, 0], "max": [0.8, 0.9, 0.8]},
                expected_size_range={"min_m": [0.7, 0.8, 0.7], "max_m": [0.9, 1.0, 0.9],
                                     "source": "test fixture card: 0.7-0.9 m width, 0.8-1.0 m height, 0.7-0.9 m depth"},
                contents={}, preview_image="previews/measured_test_chair.png")


class AssetIntakeTests(unittest.TestCase):
    def test_d4_real_stale_scale_fires_current_quiet_and_renamed_sibling(self):
        from copy import deepcopy
        from tempfile import TemporaryDirectory
        from archpipe.concept import villa_landscape as L
        before=json.loads((ROOT/'tests/fixtures/garden-d4-intake-before.json').read_text())
        tree=json.loads((ROOT/'tests/fixtures/garden-g2-tree-centred-before.json').read_text())
        current=PROPS['sf_frangipani']
        self.assertEqual(current['placed_scale'],L.require_species('Plumeria rubra')['appearance_measurements']['sf_frangipani']['scale'])
        self.assertEqual(current['units_normalised'],before['units_normalised'])
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'manifest.json'
            for entry,prop,expected in ((before,tree,True),(current,tree,False)):
                path.write_text(json.dumps({'props':[entry]}))
                found=audit_scene_manifest(path,{'props':[prop]},ROOT)['placed']
                self.assertEqual(bool(found),expected)
                if expected:
                    self.assertIn('placed_scale disagrees with built scene',found['sf_frangipani'])
                    self.assertIn('placement_scale_factors disagree with built scene',found['sf_frangipani'])
            sibling=deepcopy(current);sibling['id']='other-measured-plant'
            prop=dict(tree,asset=sibling['id'],scale=tree['scale']*.9)
            path.write_text(json.dumps({'props':[sibling]}))
            self.assertIn('placed_scale disagrees with built scene',audit_scene_manifest(path,{'props':[prop]},ROOT)['placed'][sibling['id']])

    def test_real_19_m_jacaranda_exceeds_named_range(self):
        entry = dict(complete("shade-tree"), bounds_m=PROPS["jacaranda_tree"]["bounds_m"],
                     contents={"root_ball": True}, front_axis="none", front_axis_reason="radial canopy",
                     expected_size_range={"min_m": [1, 2, 1], "max_m": [10, 10, 10],
                                          "source": "test size card: 10 m maximum tree height"})
        self.assertTrue(any("Y extent 19.4689 m outside" in e for e in validate_entry(entry)))

    def test_real_cm_scale_sofa_requires_normalisation(self):
        entry = dict(complete("sofa"), bounds_m=PROPS["sf_minotti_sofa"]["bounds_m"],
                     expected_size_range={"min_m": [2, 0.6, 0.7], "max_m": [3.5, 1.2, 1.5],
                                          "source": "test sofa size card: 2-3.5 m wide"})
        self.assertTrue(any("X extent 295.8562 m outside" in e for e in validate_entry(entry)))
        entry["units_normalised"] = {"scale_factor": 0.01, "reason": "native coordinates measured as centimetres"}
        self.assertFalse(any("outside cited range" in e for e in validate_entry(entry)))

    def test_sofa_without_front(self):
        entry = dict(complete("sofa"), front_axis="none")
        self.assertTrue(any("directional role" in e for e in validate_entry(entry)))

    def test_symmetric_bench_and_table_set_can_have_no_front(self):
        for role in ("bench-outdoor", "bistro-set"):
            entry = dict(complete(role), front_axis="none",
                         front_axis_reason="symmetric arrangement has no functional front")
            self.assertFalse(any("front_axis" in e for e in validate_entry(entry)))
            entry.pop("front_axis_reason")
            self.assertTrue(any("front_axis" in e for e in validate_entry(entry)))

    def test_placement_scale_is_distinct_from_native_unit_conversion(self):
        entry = dict(complete("shrub"), front_axis="none", front_axis_reason="radial foliage",
                     species="Callistemon citrinus",
                     bounds_m=PROPS["sf_bottlebrush"]["bounds_m"],
                     expected_size_range=PROPS["sf_bottlebrush"]["expected_size_range"],
                     placement_scale_factors=[1.315404852])
        self.assertFalse(any("outside cited range" in e for e in validate_entry(entry)))
        entry["placement_scale_factors"] = [1.0]
        self.assertFalse(any("outside cited range" in e for e in validate_entry(entry)))

    def test_plant_mature_minimum_is_not_a_placement_floor(self):
        entry = dict(complete("shrub"), species="Callistemon citrinus", front_axis="none",
                     front_axis_reason="radial foliage")
        entry["expected_size_range"] = {"min_m": [2.5, 4, 2.5], "max_m": [4, 8, 4],
                                        "basis": "species", "source": "https://www.rhs.org.uk/plants/2687/callistemon-citrinus/details"}
        self.assertEqual(validate_entry(entry), [])
        entry["bounds_m"] = {"min": [0, 0, 0], "max": [4.1, 0.9, 0.8]}
        self.assertTrue(any("X extent 4.1000 m outside" in e for e in validate_entry(entry)))
        furniture = dict(complete("armchair"), expected_size_range={"min_m": [1, .8, .7],
                          "max_m": [2, 1, 1], "source": "fixture furniture range"})
        self.assertTrue(any("X extent 0.8000 m outside" in e for e in validate_entry(furniture)))

    def test_ground_species_cards_match_in_ground_sources(self):
        bottlebrush = PROPS["sf_bottlebrush"]["expected_size_range"]
        frangipani = PROPS["sf_frangipani"]["expected_size_range"]
        self.assertEqual((bottlebrush["source"], bottlebrush["max_m"]),
                         ("https://www.rhs.org.uk/plants/2687/callistemon-citrinus/details", [4, 8, 4]))
        self.assertEqual((frangipani["source"], frangipani["max_m"]),
                         ("https://plantfinder.mobot.org/PlantFinderDetails.aspx?kempercode=d451", [7.62]*3))

    def test_real_placement_factor_guard_fires_on_changed_scene_scale(self):
        manifest = ROOT / "ops/workstation/library-manifest.json"
        clean = {"props": [{"asset": "sf_bottlebrush", "scale": 1.315404852}]}
        self.assertNotIn("sf_bottlebrush", audit_scene_manifest(manifest, clean, ROOT)["placed"])
        changed = {"props": [{"asset": "sf_bottlebrush", "scale": 1.0}]}
        changed_findings = audit_scene_manifest(manifest, changed, ROOT)["placed"]["sf_bottlebrush"]
        self.assertTrue(any("placement_scale_factors disagree" in error for error in changed_findings))

    def test_bed_without_bedding(self):
        entry = dict(complete("bed"), contents={"bedding": False})
        self.assertIn("bed requires bedding", validate_entry(entry))

    def test_missing_licence(self):
        entry = complete()
        del entry["licence"]
        self.assertIn("missing licence", validate_entry(entry))

    def test_correct_entry_stays_quiet(self):
        self.assertEqual(validate_entry(complete()), [])

    def test_unknown_role_fails(self):
        self.assertTrue(any("unknown role" in e for e in validate_entry(complete("lounge chair"))))

    def test_real_sofa_outside_held_role_figure(self):
        entry = dict(complete("sofa"), bounds_m=PROPS["sf_modern_low_sofa"]["bounds_m"])
        entry.pop("expected_size_range")
        self.assertTrue(any("outside cited range" in e for e in validate_entry(entry)))

    def test_size_override_requires_audited_decision_and_is_listed(self):
        entry = dict(complete("sofa"), bounds_m=PROPS["sf_minotti_sofa"]["bounds_m"],
                     units_normalised={"scale_factor": .01, "reason": "native centimetres"})
        entry.pop("expected_size_range")
        self.assertTrue(any("outside cited range" in error for error in validate_entry(entry)))
        entry["size_override"] = dict(PROPS["sf_minotti_sofa"]["size_override"])
        self.assertEqual(validate_entry(entry), [])
        self.assertIn("sf_minotti_sofa", {item["id"] for item in
                      manifest_overrides(ROOT / "ops/workstation/library-manifest.json")})
        entry["size_override"]["reason"] = ""
        self.assertTrue(validate_entry(entry))
        entry["size_override"] = dict(PROPS["sf_minotti_sofa"]["size_override"], decided_by="unreviewed")
        self.assertTrue(any("outside cited range" in error for error in validate_entry(entry)))

    def test_candidate_gaps_do_not_gate_but_placed_gaps_and_import_do(self):
        bad = dict(complete(), licence="forbidden")
        path = ROOT / "never-read-directly.json"
        with patch.object(Path, "read_text", return_value=json.dumps({"props": [bad]})):
            candidate = audit_scene_manifest(path, {"props": [], "models": []}, ROOT)
            self.assertEqual(candidate["placed"], {})
            self.assertEqual(candidate["candidates"][bad["id"]]["status"], "candidate")
            self.assertTrue(candidate["candidates"][bad["id"]]["violations"])
            placed = audit_scene_manifest(path, {"props": [{"asset": bad["id"]}], "models": []}, ROOT)
            self.assertTrue(placed["placed"][bad["id"]])
            with self.assertRaisesRegex(ValueError, "licence"):
                require_registered_asset(bad["id"], path)

    def test_placed_scale_must_match_built_scene(self):
        gazania = dict(PROPS["flower_gazania"], author="Fixture author",
                       preview_image="previews/fixture.png")
        path = ROOT / "never-read-directly.json"
        with patch.object(Path, "read_text", return_value=json.dumps({"props": [gazania]})):
            ok = audit_scene_manifest(path, {"props": [{"asset": gazania["id"],
                                                         "scale": gazania["placed_scale"]}], "models": []}, ROOT)
            self.assertEqual(ok["placed"], {})
            bad = audit_scene_manifest(path, {"props": [{"asset": gazania["id"], "scale": 1.0}], "models": []}, ROOT)
            self.assertIn("placed_scale disagrees with built scene", bad["placed"][gazania["id"]])

    def test_product_published_dimensions_pass(self):
        self.assertEqual(PROPS["sf_minotti_aston_armchair"]["expected_size_range"]["min_m"],
                         [0.74, 0.75, 0.84])
        entry = complete()
        entry["bounds_m"] = {"min": [0, 0, 0], "max": [0.74, 0.75, 0.84]}
        entry["expected_size_range"] = {"min_m": [0.74, 0.75, 0.84],
                                        "max_m": [0.74, 0.75, 0.84], "basis": "product",
                                        "source": "https://www.minotti.com/downloads/540/1358/ASTON_TECHNICAL_SHEET.pdf"}
        self.assertEqual(validate_entry(entry), [])
        entry["expected_size_range"]["source"] = "test card"
        self.assertIn("product dimensions require published source URL", validate_entry(entry))

    def test_indoor_plant_needs_pot_garden_shrub_does_not(self):
        indoor = dict(complete("indoor-floor-plant"), contents={}, front_axis="none",
                      front_axis_reason="radial foliage", species="Ixora coccinea")
        indoor["expected_size_range"] = {"min_m": [0, 0, 0], "max_m": [1.524, 1.8288, 1.524],
            "basis": "species", "source": "https://plantfinder.mobot.org/PlantFinderDetails.aspx?taxonid=286675"}
        self.assertIn("indoor plant requires pot", validate_entry(indoor))
        shrub = dict(indoor, role="shrub")
        self.assertEqual(validate_entry(shrub), [])

    def test_assumption_allowed_only_for_uncited_role_and_reported(self):
        assumed = {"min_m": [0, 0, 0], "max_m": [2, 2, 2],
                   "basis": "ASSUMED", "reason": "fixture has no held dimensions"}
        sofa = dict(complete("sofa"), expected_size_range=assumed)
        self.assertTrue(any("ASSUMED range requires an allowed role" in e for e in validate_entry(sofa)))
        decor = dict(complete("decor-small"), expected_size_range=assumed,
                     front_axis="none", front_axis_reason="nondirectional decor")
        self.assertEqual(validate_entry(decor), [])
        self.assertIn("book_encyclopedia_set_01", {a["id"] for a in manifest_assumptions(ROOT / "ops/workstation/library-manifest.json")})

    def test_species_citation_passes_and_outside_range_fails(self):
        entry = dict(complete("shrub"), species="Ixora coccinea", front_axis="none",
                     front_axis_reason="radial shrub")
        entry["expected_size_range"] = {"min_m": [0, 0, 0], "max_m": [1.524, 1.8288, 1.524],
            "basis": "species", "source": "https://plantfinder.mobot.org/PlantFinderDetails.aspx?taxonid=286675"}
        self.assertEqual(validate_entry(entry), [])
        entry["bounds_m"] = {"min": [0, 0, 0], "max": [1.6, .9, .8]}
        self.assertTrue(any("outside cited range" in e for e in validate_entry(entry)))

    def test_local_file_drift(self):
        entry = dict(complete(), bounds_m=PROPS["sf_chelsea_bed"]["bounds_m"])
        model = ROOT / "out/villa/round3/stage-props/sf_chelsea_bed/model.gltf"
        if model.is_file():
            self.assertFalse(any("disagrees" in e for e in validate_entry(entry, model)))
            entry["bounds_m"] = dict(entry["bounds_m"], max=[1.5, 1.0548, 1.206])
            self.assertTrue(any("disagrees" in e for e in validate_entry(entry, model)))

    def test_real_manifest_reports_only_failing_props(self):
        findings = validate_manifest(ROOT / "ops/workstation/library-manifest.json", ROOT)
        self.assertTrue(set(findings) <= set(PROPS))
        self.assertNotIn("hanging_picture_frame_01", findings)

    def test_import_boundary_refuses_unregistered_and_failing(self):
        manifest = ROOT / "never-read-directly.json"
        with patch.object(Path, "read_text", return_value=json.dumps({"props": [dict(complete(), licence="forbidden")]})):
            with self.assertRaisesRegex(ValueError, "unregistered"):
                require_registered_asset("absent", manifest)
            with self.assertRaisesRegex(ValueError, "licence"):
                require_registered_asset("measured_test_chair", manifest)
        with patch.object(Path, "read_text", return_value=json.dumps({"props": [complete()]})):
            self.assertEqual(require_registered_asset("measured_test_chair", manifest)["id"], "measured_test_chair")

    def test_backfill_keeps_underived_values_missing(self):
        path = ROOT / "ops/workstation/backfill_asset_intake.py"
        spec = importlib.util.spec_from_file_location("backfill_asset_intake", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.backfill_entry({"id": "unknown_poly", "role": "decor-small", "api": "polyhaven-model"})
        self.assertNotIn("author", result)
        self.assertNotIn("expected_size_range", result)
        self.assertEqual(result["contents"], {})
        self.assertEqual(result["front_axis"], "none")

    def test_fetcher_refuses_failing_entry_before_index_write(self):
        path = ROOT / "ops/workstation/fetch_asset_library.py"
        spec = importlib.util.spec_from_file_location("fetch_asset_library", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        index = {}
        fake_front = types.SimpleNamespace(measured_or_manual_front=lambda entry, path: None)
        with patch.dict(sys.modules, {"front_axis": fake_front}), \
             patch.object(Path, "is_dir", return_value=True), \
             patch.object(Path, "rglob", return_value=[Path("model.gltf")]), \
             patch("archpipe.asset_intake.measure_gltf_bounds", return_value=complete()["bounds_m"]):
            with self.assertRaisesRegex(ValueError, "licence"):
                module.do_prop(dict(complete(), licence="forbidden"), ROOT / "fake-library", index)
        self.assertNotIn("props", index)


if __name__ == "__main__":
    unittest.main()
