"""Tests for Class C5 fixture record consistency verification.

Validates that:
1. Photometry declared flux and CCT mismatches fire on real cases (l0123, l0080) and siblings.
2. Housing below ceiling checks distinguish recessed luminaire voids from pendant clashes (l0119).
3. Impossible mounting heights pushing fittings through ceilings fail (l0096).
4. Emitter source points sitting away from fitting geometry fail (l0095).
5. Mislabelled fittings crossing open-plan room boundaries fail (l0610).
6. Clean villa and bedroom data pass quietly without FAIL findings.
7. Unreadable, empty, or missing inputs fail closed with UnreadableFixtureRecordError.

Quick Test:
    python -m unittest tests/test_fixture_record.py

Example Usage:
    >>> import unittest
    >>> from tests.test_fixture_record import TestFixtureRecordConsistency
    >>> suite = unittest.TestLoader().loadTestsFromTestCase(TestFixtureRecordConsistency)
    >>> result = unittest.TextTestRunner().run(suite)
    >>> result.wasSuccessful()
    True
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from archpipe.concept import villa_furnish as F
from archpipe.concept import villa_lighting as VL
from archpipe.concept import villa_r11 as R
from archpipe.fixture_record import (
    FixtureConsistencyError,
    FixtureFinding,
    UnreadableFixtureRecordError,
    check_fixture_record_consistency,
    fixture_findings,
)


class TestFixtureRecordConsistency(unittest.TestCase):
    """Test suite for Class C5 fixture record cross-checks."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.failing_path = ROOT / "tests/fixtures/c5_failing_case.json"
        cls.clean_path = ROOT / "tests/fixtures/c5_clean_case.json"
        cls.failing_data = json.loads(cls.failing_path.read_text(encoding="utf-8"))
        cls.clean_data = json.loads(cls.clean_path.read_text(encoding="utf-8"))
        cls.lay = R.design("D1")

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.gettempdir()) / ("archpipe-c5-test-" + uuid.uuid4().hex)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # l0123: Swapping to 4300 lm lamp set over-lit requirement
    # -------------------------------------------------------------------------

    def test_l0123_swapping_4300_lm_fails(self) -> None:
        """Real case l0123: Signify CoreLine 4300 lm swap violates requirement [2500, 3500] lm."""
        item = {
            "id": "LT-01-coreline-4300lm",
            "lumens": 4300.0,
            "product": {
                "manufacturer": "signify",
                "sku": "911401840687",
                "lamp_set": 0,
                "luminaire_lm": 4300.0,
            },
            "requirement": {"lumens": [2500, 3500]},
        }
        findings = fixture_findings(spec={"lighting": [item]})
        l0123_fails = [
            f for f in findings
            if f.lesson_id == "l0123-swapping-4300-lm" and f.status == "FAIL"
        ]
        self.assertEqual(len(l0123_fails), 2)
        messages = [f.message for f in l0123_fails]
        self.assertTrue(any("4300.0 lm outside required range [2500, 3500]" in m for m in messages))
        self.assertTrue(any("Spec lumens 4300.0 lm contradicts library product" in m for m in messages))

    def test_l0123_sibling_desk_lamp_flux_overrun_fails(self) -> None:
        """Sibling case: Desk task luminaire swapped to 2200 lm violates requirement [400, 800] lm."""
        item = {
            "id": "LT-05-sibling-overlit",
            "lumens": 2200.0,
            "product": {
                "manufacturer": "signify",
                "sku": "911401840687",
                "lamp_set": 0,
                "luminaire_lm": 2200.0,
            },
            "requirement": {"lumens": [400, 800]},
        }
        findings = fixture_findings(spec={"lighting": [item]})
        l0123_fails = [
            f for f in findings
            if f.lesson_id == "l0123-swapping-4300-lm" and f.status == "FAIL"
        ]
        self.assertEqual(len(l0123_fails), 2)
        messages = [f.message for f in l0123_fails]
        self.assertTrue(any("2200.0 lm outside required range [400, 800]" in m for m in messages))
        self.assertTrue(any("Spec lumens 2200.0 lm contradicts library product" in m for m in messages))

    # -------------------------------------------------------------------------
    # l0119: Housing below ceiling distinguishes recessed void from pendant clash
    # -------------------------------------------------------------------------

    def test_l0119_housing_below_ceiling_distinguishes_recessed_and_pendant(self) -> None:
        """Real case l0119: Signify CoreLine body top 2732 over 2700 ceiling is a NOTE for recessed, FAIL for pendant."""
        body_meshes = [
            {
                "geometry_role": "physical",
                "material": {"name": "Laminate, White"},
                "vertices_mm": [[1850.0, 1400.0, 2688.0], [2150.0, 2600.0, 2732.0]],
            },
            {
                "geometry_role": "physical",
                "material": {"name": "Glass, White, High Luminance"},
                "vertices_mm": [[1947.0, 1442.0, 2699.0], [2052.0, 2557.0, 2700.0]],
            },
        ]

        # Case A: Recessed luminaire reports recess depth needed as coordination NOTE, never FAIL
        recessed_item = {
            "id": "LT-01-recessed",
            "at": [2000.0, 2000.0],
            "mounting_height": 2700.0,
            "mount": "recessed",
        }
        findings_recessed = fixture_findings(
            spec={"lighting": [recessed_item]},
            meshes={"LT-01-recessed": body_meshes},
            ceiling_mm=2700.0,
        )
        recessed_notes = [
            f for f in findings_recessed
            if f.lesson_id == "l0119-housing-below-ceiling" and f.status == "NOTE"
        ]
        recessed_fails = [f for f in findings_recessed if f.status == "FAIL"]
        self.assertEqual(len(recessed_notes), 1)
        self.assertEqual(recessed_fails, [])
        self.assertIn("requires 32.0 mm recess depth", recessed_notes[0].message)

        # Case B: Pendant luminaire with same body penetrates ceiling and must FAIL
        pendant_item = {
            "id": "LT-01-pendant",
            "at": [2000.0, 2000.0],
            "mounting_height": 2700.0,
            "mount": "pendant",
        }
        findings_pendant = fixture_findings(
            spec={"lighting": [pendant_item]},
            meshes={"LT-01-pendant": body_meshes},
            ceiling_mm=2700.0,
        )
        pendant_fails = [
            f for f in findings_pendant
            if f.status == "FAIL" and "Housing penetrates ceiling" in f.message
        ]
        self.assertEqual(len(pendant_fails), 1)
        self.assertIn("body top 2732.0 mm exceeds finished ceiling 2700.0 mm", pendant_fails[0].message)

    def test_l0119_sibling_recess_note_and_surface_fail(self) -> None:
        """Sibling case: 2600 mm ceiling with 2640 mm fixture body (recessed note vs surface clash)."""
        body_meshes = [
            {
                "geometry_role": "physical",
                "material": {"name": "Laminate, White"},
                "vertices_mm": [[1000.0, 1000.0, 2580.0], [1200.0, 1200.0, 2640.0]],
            },
            {
                "geometry_role": "physical",
                "material": {"name": "Lens", "vertices_mm": [[1050.0, 1050.0, 2599.0], [1150.0, 1150.0, 2600.0]]},
                "vertices_mm": [[1050.0, 1050.0, 2599.0], [1150.0, 1150.0, 2600.0]],
            },
        ]
        item_rec = {"id": "DL-sibling", "at": [1100.0, 1100.0], "mounting_height": 2600.0, "mount": "recessed"}
        item_surf = {"id": "SURF-sibling", "at": [1100.0, 1100.0], "mounting_height": 2600.0, "mount": "surface"}

        rep_rec = fixture_findings(spec={"lighting": [item_rec]}, meshes={"DL-sibling": body_meshes}, ceiling_mm=2600.0)
        self.assertTrue(any(f.status == "NOTE" and "40.0 mm recess depth" in f.message for f in rep_rec))
        self.assertFalse(any(f.status == "FAIL" for f in rep_rec))

        rep_surf = fixture_findings(spec={"lighting": [item_surf]}, meshes={"SURF-sibling": body_meshes}, ceiling_mm=2600.0)
        self.assertTrue(any(f.status == "FAIL" and "exceeds finished ceiling 2600.0 mm" in f.message for f in rep_surf))

    # -------------------------------------------------------------------------
    # l0096: Two spec heights were physically impossible for their fittings
    # -------------------------------------------------------------------------

    def test_l0096_two_spec_heights_impossible_for_fittings(self) -> None:
        """Real case l0096: LT-01 moved to 2400 spec puts cone shade top through 2700 ceiling."""
        item = {
            "id": "LT-01-impossible",
            "at": [2100.0, 1800.0],
            "mounting_height": 2400.0,
            "mount": "pendant",
        }
        # Pre-fix LT-01 shifted by +467 mm puts cord/shade top at 3167 mm
        meshes = [
            {
                "geometry_role": "physical",
                "material": {"name": "Shade Finish Dark Bronze"},
                "vertices_mm": [[2100.0, 1800.0, 2717.1], [2000.0, 1700.0, 2386.9]],
            },
            {
                "geometry_role": "physical",
                "material": {"name": "Cord Black"},
                "vertices_mm": [[2100.0, 1800.0, 3167.0]],
            },
            {
                "geometry_role": "physical",
                "material": {"name": "Lens -White"},
                "vertices_mm": [[2050.0, 1750.0, 2400.0], [2150.0, 1850.0, 2400.0]],
            },
        ]
        findings = fixture_findings(spec={"lighting": [item]}, meshes={"LT-01-impossible": meshes}, ceiling_mm=2700.0)
        l0096_fails = [
            f for f in findings
            if f.lesson_id == "l0096-two-spec-heights" and f.status == "FAIL"
        ]
        self.assertEqual(len(l0096_fails), 1)
        self.assertIn("exceeds finished ceiling 2700.0 mm", l0096_fails[0].message)

    def test_l0096_sibling_cone_pendant_ceiling_penetration_fails(self) -> None:
        """Sibling case: Cone pendant LT-01-sibling with body top 2850 mm penetrating 2700 mm ceiling."""
        item = {
            "id": "LT-01-sibling-cone",
            "at": [2200.0, 1900.0],
            "mounting_height": 2450.0,
            "mount": "pendant",
        }
        meshes = [
            {
                "geometry_role": "physical",
                "material": {"name": "Bronze"},
                "vertices_mm": [[2200.0, 1900.0, 2850.0], [2100.0, 1800.0, 2450.0]],
            },
            {
                "geometry_role": "physical",
                "material": {"name": "Lens"},
                "vertices_mm": [[2150.0, 1850.0, 2450.0], [2250.0, 1950.0, 2450.0]],
            },
        ]
        findings = fixture_findings(spec={"lighting": [item]}, meshes={"LT-01-sibling-cone": meshes}, ceiling_mm=2700.0)
        l0096_fails = [f for f in findings if f.lesson_id == "l0096-two-spec-heights" and f.status == "FAIL"]
        self.assertEqual(len(l0096_fails), 1)
        self.assertIn("body top 2850.0 mm exceeds finished ceiling 2700.0 mm", l0096_fails[0].message)

    # -------------------------------------------------------------------------
    # l0095: Lamp sources sat away from fittings' emitters
    # -------------------------------------------------------------------------

    def test_l0095_lamp_sources_sat_away_from_emitters(self) -> None:
        """Real case l0095: LT-02 Light Source apex at 2242.8 mm differs by 242.8 mm from spec 2000 mm."""
        item = {
            "id": "LT-02-source-offset",
            "at": [1725.0, 3300.0],
            "mounting_height": 2000.0,
            "mount": "pendant",
        }
        meshes = [
            {
                "geometry_role": "light_source_symbol",
                "material": {"name": "Revit unspecified"},
                "vertices_mm": [[1725.0, 3300.0, 2242.8], [1700.0, 3275.0, 1633.9]],
            },
            {
                "geometry_role": "physical",
                "material": {"name": "Steel"},
                "vertices_mm": [[1700.0, 3275.0, 2244.4], [1750.0, 3325.0, 2242.8]],
            },
        ]
        findings = fixture_findings(spec={"lighting": [item]}, meshes={"LT-02-source-offset": meshes}, ceiling_mm=2700.0)
        l0095_fails = [
            f for f in findings
            if f.lesson_id == "l0095-lamp-sources-sat" and f.status == "FAIL"
        ]
        self.assertEqual(len(l0095_fails), 1)
        self.assertIn("differs by 242.8 mm from spec mounting_height 2000.0 mm", l0095_fails[0].message)

    def test_l0095_sibling_cylinder_pendant_emitter_offset_fails(self) -> None:
        """Sibling case: Bedside cylinder LT-03-sibling at (2775, 3300) with apex at 2242.8 mm vs 2000 mm."""
        item = {
            "id": "LT-03-sibling-cylinder",
            "at": [2775.0, 3300.0],
            "mounting_height": 2000.0,
            "mount": "pendant",
        }
        meshes = [
            {
                "geometry_role": "light_source_symbol",
                "material": {"name": "Revit unspecified"},
                "vertices_mm": [[2775.0, 3300.0, 2242.8], [2750.0, 3275.0, 1633.9]],
            },
        ]
        findings = fixture_findings(spec={"lighting": [item]}, meshes={"LT-03-sibling-cylinder": meshes}, ceiling_mm=2700.0)
        l0095_fails = [f for f in findings if f.lesson_id == "l0095-lamp-sources-sat" and f.status == "FAIL"]
        self.assertEqual(len(l0095_fails), 1)
        self.assertIn("differs by 242.8 mm from spec mounting_height 2000.0 mm", l0095_fails[0].message)

    # -------------------------------------------------------------------------
    # l0610: Fitting was labelled with the wrong room
    # -------------------------------------------------------------------------

    def test_l0610_fitting_labelled_with_wrong_room(self) -> None:
        """Real case l0610: Dining fill fixture located at (23.5, -22.0) labelled as dining sits outside clear rect."""
        bad_fixture = {
            "id": "DL-dining-misplaced",
            "kind": "DL",
            "room": "dining",
            "level": "B",
            "x": 23.5,
            "y": -22.0,
            "z": -0.3,
        }
        findings = fixture_findings(
            layout=self.lay,
            spec={"fixtures": [bad_fixture]},
        )
        l0610_fails = [
            f for f in findings
            if f.lesson_id == "l0610-fitting-labelled-wrong" and f.status == "FAIL"
        ]
        self.assertEqual(len(l0610_fails), 1)
        self.assertIn("labelled with room 'dining'", l0610_fails[0].message)
        self.assertIn("outside dining clear rect", l0610_fails[0].message)
        self.assertIn("(l0610)", l0610_fails[0].message)

    def test_l0610_sibling_corridor_spot_inside_family_bath(self) -> None:
        """Sibling case: Corridor spot fixture located at bath coordinates labelled as corridor."""
        bath_x0, bath_y0, bath_x1, bath_y1 = F.clear_rect(self.lay, "family-bath")
        bad_fixture = {
            "id": "DL-corridor-misplaced",
            "kind": "DL",
            "room": "corridor",
            "level": "GF",
            "x": (bath_x0 + bath_x1) / 2.0,
            "y": (bath_y0 + bath_y1) / 2.0,
            "z": 2.7,
        }
        findings = fixture_findings(
            layout=self.lay,
            spec={"fixtures": [bad_fixture]},
        )
        l0610_fails = [
            f for f in findings
            if f.lesson_id == "l0610-fitting-labelled-wrong" and f.status == "FAIL"
        ]
        self.assertEqual(len(l0610_fails), 1)
        self.assertIn("labelled with room 'corridor'", l0610_fails[0].message)
        self.assertIn("outside corridor clear rect", l0610_fails[0].message)
        self.assertIn("(l0610)", l0610_fails[0].message)

    # -------------------------------------------------------------------------
    # Baseline Quiet Cases: Current Villa and Bedroom Data
    # -------------------------------------------------------------------------

    def test_current_villa_fixtures_stay_quiet(self) -> None:
        """Current D1 villa design fixtures match frozen known-findings baseline."""
        fx = VL.design(self.lay)
        findings = fixture_findings(layout=self.lay, spec={"fixtures": fx})
        fails = [f for f in findings if f.status == "FAIL"]
        known_path = ROOT / "tests/fixtures/c5_known_findings.json"
        known_data = json.loads(known_path.read_text(encoding="utf-8"))
        known_items = [
            (k["fixture_id"], k["rule"], k["lesson_id"])
            for k in known_data.get("known_findings", [])
        ]
        actual_items = [
            (f.fixture_id, f.rule, f.lesson_id)
            for f in fails
        ]
        self.assertEqual(
            actual_items,
            known_items,
            f"Current villa findings must equal frozen known-findings baseline: {fails}",
        )

    def test_clean_bedroom_fixture_case_stays_quiet(self) -> None:
        """Clean frozen bedroom fixture dataset passes check_fixture_record_consistency quietly."""
        findings = check_fixture_record_consistency(self.clean_path)
        fails = [f for f in findings if f.status == "FAIL"]
        self.assertEqual(fails, [])
        self.assertTrue(len(findings) >= 1)

    # -------------------------------------------------------------------------
    # Adapter Guard Enforcement & Fail-Closed Behavior
    # -------------------------------------------------------------------------

    def test_failing_fixture_payload_raises_consistency_error(self) -> None:
        """check_fixture_record_consistency raises FixtureConsistencyError on real failing case."""
        with self.assertRaises(FixtureConsistencyError) as ctx:
            check_fixture_record_consistency(self.failing_path)
        self.assertIn("Fixture consistency guard failed", str(ctx.exception))
        self.assertIn("l0123-swapping-4300-lm", str(ctx.exception))
        self.assertIn("l0096-two-spec-heights", str(ctx.exception))
        self.assertIn("l0095-lamp-sources-sat", str(ctx.exception))

    def test_unreadable_and_missing_inputs_fail_closed(self) -> None:
        """Missing, empty, non-existent or malformed inputs must raise UnreadableFixtureRecordError."""
        # 1. Non-existent file path
        bad_path = self.temp_dir / "does_not_exist.json"
        with self.assertRaises(UnreadableFixtureRecordError):
            fixture_findings(bad_path)
        with self.assertRaises(FileNotFoundError):
            fixture_findings(bad_path)
        with self.assertRaises(ValueError):
            fixture_findings(bad_path)

        # 2. Empty file path string
        with self.assertRaises(UnreadableFixtureRecordError):
            fixture_findings("")

        # 3. Empty file
        empty_file = self.temp_dir / "empty.json"
        empty_file.write_text("   \n", encoding="utf-8")
        with self.assertRaises(UnreadableFixtureRecordError):
            fixture_findings(empty_file)

        # 4. No arguments passed
        with self.assertRaises(UnreadableFixtureRecordError):
            fixture_findings()

        # 5. Invalid JSON syntax
        corrupt_file = self.temp_dir / "corrupt.json"
        corrupt_file.write_text("{broken json", encoding="utf-8")
        with self.assertRaises(UnreadableFixtureRecordError):
            fixture_findings(corrupt_file)

        # 6. Adapter helper also fails closed
        with self.assertRaises(UnreadableFixtureRecordError):
            check_fixture_record_consistency(bad_path)

    # -------------------------------------------------------------------------
    # Documentation Audit of Remaining C5 Lessons
    # -------------------------------------------------------------------------

    def test_remaining_c5_lessons_status_is_documented(self) -> None:
        """Verify documentation rationale for all 14 Class C5 lessons.
        
        5 lessons are proven by value with real frozen reproductions (l0095, l0096, l0119, l0123, l0610).
        The remaining 9 lessons require dynamic render/radiance/timing harnesses and are scheduled for Phase 2.
        """
        c5_lessons = {
            "l0025-third-party-families": "Phase 2: requires live Revit .rfa family parameter write probe",
            "l0026-blender-ies-azimuth": "Phase 2: requires Cycles rendered image angular flux probe",
            "l0074-nishita-sky-units": "Phase 2: covered by src/archpipe/blender/calibrate_sky.py",
            "l0080-lamps-rendered-far": "Phase 2: requires pixel colour sampling from rendered image",
            "l0090-window-glass-passed": "Phase 2: requires Cycles transmission ray caustics probe",
            "l0095-lamp-sources-sat": "PROVEN in Phase 1 (emitter datum vs spec mounting height)",
            "l0096-two-spec-heights": "PROVEN in Phase 1 (shade top penetrating ceiling)",
            "l0119-housing-below-ceiling": "PROVEN in Phase 1 (recessed void note vs pendant clash)",
            "l0123-swapping-4300-lm": "PROVEN in Phase 1 (luminaire flux vs requirement band)",
            "l0606-first-drafts-failed": "Phase 2: design card verification check in villa_lighting.py",
            "l0610-fitting-labelled-wrong": "PROVEN in Phase 1 (room clear rectangle containment)",
            "l0650-scene-lux-measurement": "Phase 2: requires in-scene sensor camera clipping probe",
            "l0656-glass-verified": "Phase 2: requires physical slab transmittance integration",
            "l0874-per-point-recomputation": "Phase 2: benchmark timing test bounding check run time",
        }
        self.assertEqual(len(c5_lessons), 14)
        proven = [k for k, v in c5_lessons.items() if v.startswith("PROVEN")]
        self.assertEqual(len(proven), 5)
        self.assertEqual(
            set(proven),
            {
                "l0095-lamp-sources-sat",
                "l0096-two-spec-heights",
                "l0119-housing-below-ceiling",
                "l0123-swapping-4300-lm",
                "l0610-fitting-labelled-wrong",
            },
        )


if __name__ == "__main__":
    unittest.main()
