"""Asset intake regressions, including frozen values from the round-three manifest."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from archpipe.asset_intake import validate_entry, validate_manifest

MANIFEST = json.loads((ROOT / "ops/workstation/library-manifest.json").read_text(encoding="utf-8"))
PROPS = {p["id"]: p for p in MANIFEST["props"]}


def complete(role="lounge chair"):
    # The named dimensions and range belong to this fixture, not to a real catalogue.
    return dict(id="measured_test_chair", role=role, source_url="https://example.org/test-chair",
                licence="CC-BY", author="Fixture author", credit="Fixture author, CC-BY",
                units_normalised={"scale_factor": 1.0, "reason": "fixture coordinates are metres"},
                up_axis="+Y", front_axis="+Z", bounds_m={"min": [0, 0, 0], "max": [0.8, 0.9, 0.8]},
                expected_size_range={"min_m": [0.7, 0.8, 0.7], "max_m": [0.9, 1.0, 0.9],
                                     "source": "test fixture card: 0.7-0.9 m width, 0.8-1.0 m height, 0.7-0.9 m depth"},
                contents={}, preview_image="previews/measured_test_chair.png")


class AssetIntakeTests(unittest.TestCase):
    def test_real_19_m_jacaranda_exceeds_named_range(self):
        entry = dict(complete("shade tree"), bounds_m=PROPS["jacaranda_tree"]["bounds_m"],
                     contents={"root_ball": True}, front_axis="none", front_axis_reason="radial canopy",
                     expected_size_range={"min_m": [1, 2, 1], "max_m": [10, 10, 10],
                                          "source": "test size card: 10 m maximum tree height"})
        self.assertTrue(any("Y extent 19.4689 m outside" in e for e in validate_entry(entry)))

    def test_real_cm_scale_sofa_requires_normalisation(self):
        entry = dict(complete("garden-living sofa"), bounds_m=PROPS["sf_minotti_sofa"]["bounds_m"],
                     expected_size_range={"min_m": [2, 0.6, 0.7], "max_m": [3.5, 1.2, 1.5],
                                          "source": "test sofa size card: 2-3.5 m wide"})
        self.assertTrue(any("X extent 295.8562 m outside" in e for e in validate_entry(entry)))
        entry["units_normalised"] = {"scale_factor": 0.01, "reason": "native coordinates measured as centimetres"}
        self.assertFalse(any("outside cited range" in e for e in validate_entry(entry)))

    def test_sofa_without_front(self):
        entry = dict(complete("garden-living sofa"), front_axis="none")
        self.assertTrue(any("directional role" in e for e in validate_entry(entry)))

    def test_bed_without_bedding(self):
        entry = dict(complete("parents' bed"), contents={"bedding": False})
        self.assertIn("bed requires bedding", validate_entry(entry))

    def test_missing_licence(self):
        entry = complete()
        del entry["licence"]
        self.assertIn("missing licence", validate_entry(entry))

    def test_correct_entry_stays_quiet(self):
        self.assertEqual(validate_entry(complete()), [])

    def test_local_file_drift(self):
        entry = dict(complete(), bounds_m=PROPS["sf_chelsea_bed"]["bounds_m"])
        model = ROOT / "out/villa/round3/stage-props/sf_chelsea_bed/model.gltf"
        if model.is_file():
            self.assertFalse(any("disagrees" in e for e in validate_entry(entry, model)))
            entry["bounds_m"] = dict(entry["bounds_m"], max=[1.5, 1.0548, 1.206])
            self.assertTrue(any("disagrees" in e for e in validate_entry(entry, model)))

    def test_real_manifest_reports_every_prop(self):
        findings = validate_manifest(ROOT / "ops/workstation/library-manifest.json", ROOT)
        self.assertEqual(set(findings), set(PROPS))


if __name__ == "__main__":
    unittest.main()
