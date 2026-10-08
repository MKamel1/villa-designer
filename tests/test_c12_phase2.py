"""Phase 2 Batch 1 migration tests for evidence status checks (C12).

Tests the wiring of evidence.py verification functions into four migrated call sites:
1. src/archpipe/asset_intake.py validate_entry(): geometry metadata drift guard (l0179)
2. src/archpipe/sources.py intake(): book edition mismatch screening (l0188)
3. (knowledge_index.py page_labels: rejected in lead review, not in this batch)
4. scripts/villa_daylight_finished.py: shared render and daylight model hash (l0661)

Quick Test:
    python -m unittest tests/test_c12_phase2.py

Example Usage:
    >>> import unittest
    >>> suite = unittest.defaultTestLoader.loadTestsFromName("tests.test_c12_phase2")
    >>> runner = unittest.TextTestRunner()
    >>> result = runner.run(suite)
    >>> result.wasSuccessful()
    True
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from archpipe.asset_intake import BOUNDS_TOLERANCE_M, validate_entry
from archpipe.evidence import (
    EditionMismatchError,
    check_book_edition,
    check_geometry_against_metadata,
    check_page_locator,
    check_shared_model,
)
from archpipe import sources as src
import scripts.villa_daylight_finished as vdf


class MockPage:
    """Mock page object with a get_label() method."""

    def __init__(self, label: str):
        self._label = label

    def get_label(self) -> str:
        return self._label


class MockDoc:
    """Mock PDF document returning MockPage instances."""

    def __init__(self, labels: list[str]):
        self._pages = [MockPage(lbl) for lbl in labels]

    def __getitem__(self, idx: int) -> MockPage:
        return self._pages[idx]

    def __len__(self) -> int:
        return len(self._pages)


class TestAssetIntakeGeometryEvidence(unittest.TestCase):
    """Test Site 1: src/archpipe/asset_intake.py validate_entry().
    
    Verifies that drift > BOUNDS_TOLERANCE_M delegates to
    evidence.check_geometry_against_metadata so the evidence module is
    the single authority.
    """

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.model_path = self.tmpdir / "test_model.gltf"
        self.model_path.write_text("{}", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_l0179_real_recorded_failure_fails_closed(self) -> None:
        """Real recorded failure from lesson l0179: desk_lamp_arm_01 declared
        depth 408 mm in metadata but measured 202 mm in glTF mesh (drift 206 mm).
        Fails closed with exact bounds disagreement error.
        """
        # Metadata declared 408 mm along Y; mesh measured 202 mm (0.206 m drift)
        entry = {
            "id": "desk_lamp_arm_01",
            "role": "task-lamp",
            "source_url": "https://example.com/lamp",
            "licence": "CC0",
            "author": "Test Author",
            "credit": "Test Credit",
            "units_normalised": True,
            "up_axis": "+Z",
            "front_axis": "+X",
            "bounds_m": {
                "min": [0.0, 0.0, 0.0],
                "max": [0.300, 0.408, 0.450],
            },
            "expected_size_range": [[0.1, 0.1, 0.1], [0.8, 0.8, 0.8]],
            "contents": {},
            "preview_image": "preview.png",
        }
        measured = {
            "min": [0.0, 0.0, 0.0],
            "max": [0.300, 0.202, 0.450],
        }

        # Verify evidence module alone marks this unverified / flagged
        check = check_geometry_against_metadata(0.408 - 0.202, 0.0, tolerance=BOUNDS_TOLERANCE_M)
        self.assertTrue(check["flagged"])
        self.assertFalse(check["matches"])

        # Call site validate_entry() now fails closed
        errors = validate_entry(entry, model_path=self.model_path, measure=lambda _: measured)
        disagreement_errors = [e for e in errors if "bounds_m disagrees with local file" in e]
        self.assertEqual(len(disagreement_errors), 1)
        self.assertIn("0.2060 m", disagreement_errors[0])

    def test_clean_input_stays_quiet(self) -> None:
        """Current clean input within 5 mm tolerance stays quiet."""
        entry = {
            "id": "desk_lamp_arm_clean",
            "role": "task-lamp",
            "source_url": "https://example.com/lamp",
            "licence": "CC0",
            "author": "Test Author",
            "credit": "Test Credit",
            "units_normalised": True,
            "up_axis": "+Z",
            "front_axis": "+X",
            "bounds_m": {
                "min": [0.0, 0.0, 0.0],
                "max": [0.300, 0.408, 0.450],
            },
            "expected_size_range": [[0.1, 0.1, 0.1], [0.8, 0.8, 0.8]],
            "contents": {},
            "preview_image": "preview.png",
        }
        # Drift 0.002 m <= BOUNDS_TOLERANCE_M (0.005 m)
        measured = {
            "min": [0.0, 0.0, 0.0],
            "max": [0.300, 0.406, 0.450],
        }
        errors = validate_entry(entry, model_path=self.model_path, measure=lambda _: measured)
        disagreement_errors = [e for e in errors if "bounds_m disagrees" in e]
        self.assertEqual(disagreement_errors, [])

    def test_sibling_failure_fails_closed(self) -> None:
        """Translated / renamed sibling failure also fails closed."""
        entry = {
            "id": "nightstand_table_02",
            "role": "bedside-table",
            "source_url": "https://example.com/table",
            "licence": "CC0",
            "author": "Sibling Author",
            "credit": "Sibling Credit",
            "units_normalised": True,
            "up_axis": "+Z",
            "front_axis": "+X",
            "bounds_m": {
                "min": [1.0, -2.0, 0.0],
                "max": [1.5, -1.5, 0.6],
            },
            "expected_size_range": [[0.3, 0.3, 0.3], [1.0, 1.0, 1.0]],
            "contents": {},
            "preview_image": "preview.png",
        }
        # Sibling drift: 100 mm along X (0.100 m > 0.005 m)
        measured = {
            "min": [1.0, -2.0, 0.0],
            "max": [1.6, -1.5, 0.6],
        }
        errors = validate_entry(entry, model_path=self.model_path, measure=lambda _: measured)
        disagreement_errors = [e for e in errors if "bounds_m disagrees with local file" in e]
        self.assertEqual(len(disagreement_errors), 1)
        self.assertIn("0.1000 m", disagreement_errors[0])


class TestSourcesEditionScreeningEvidence(unittest.TestCase):
    """Test Site 2: src/archpipe/sources.py intake().
    
    Verifies that intake() screens incoming files with check_book_edition
    before marking them held, and fails closed with EditionMismatchError
    on edition claim discrepancies (lesson l0188).
    """

    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        (self.tmpdir / "inbox").mkdir()
        self.lib = {
            "sources": [
                {
                    "id": "neufert",
                    "title": "Architects' Data",
                    "edition": "2nd (International) English ed., 1980, reprinted to 1998 (Blackwell Science, ISBN 0-632-02339-2)",
                    "status": "identified",
                    "priority": 1,
                    "cost_usd_approx": 120,
                },
                {
                    "id": "lighting-design-basics",
                    "title": "Lighting Design Basics",
                    "edition": "1st edition 2004",
                    "status": "identified",
                    "priority": 1,
                    "cost_usd_approx": 60,
                },
                {
                    "id": "metric-handbook",
                    "title": "Metric Handbook: Planning and Design Data",
                    "edition": "7th edition 2022",
                    "isbn": "9780367511395",
                    "status": "identified",
                    "priority": 1,
                    "cost_usd_approx": 90,
                },
            ]
        }

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_mock_pdf(self, path: Path, text: str) -> None:
        import pymupdf
        doc = pymupdf.open()
        page = doc.new_page()
        filler = "\nPlanning data reference text for the readability threshold." * 6
        page.insert_textbox(pymupdf.Rect(40, 40, 560, 800), text + filler, fontsize=9)
        doc.save(path)

    def test_l0188_real_recorded_failure_fails_closed(self) -> None:
        """Real recorded failure from lesson l0188: A downloaded file named
        'Neufert Architects Data 6th ed. 2023.pdf' was matched to the neufert
        registry entry whose copyright page states 1980 2nd English edition.
        Must fail closed with EditionMismatchError and the evidence module's reason.
        """
        filename = "Neufert Architects Data 6th ed. 2023.pdf"
        target_file = self.tmpdir / "inbox" / filename
        self._create_mock_pdf(target_file, "ARCHITECTS' DATA\nErnst Neufert planning data")

        neufert_source = next(s for s in self.lib["sources"] if s["id"] == "neufert")
        self.assertEqual(neufert_source["status"], "identified")

        with self.assertRaises(EditionMismatchError) as ctx:
            src.intake(self.lib, self.tmpdir, log=lambda *_: None)

        self.assertIn("6th ed", str(ctx.exception))
        self.assertIn("1980", str(ctx.exception))
        self.assertIn("l0188", str(ctx.exception))

        # Source is not marked held
        self.assertEqual(neufert_source["status"], "identified")

    def test_clean_input_stays_quiet_and_marks_held(self) -> None:
        """Clean input agreeing with copyright edition stays quiet and marks held."""
        filename = "Metric_Handbook_7th_ed_2022.pdf"
        target_file = self.tmpdir / "inbox" / filename
        self._create_mock_pdf(target_file, "Metric Handbook Planning and Design Data\nDwelling dimensions")

        metric_source = next(s for s in self.lib["sources"] if s["id"] == "metric-handbook")
        self.assertEqual(metric_source["status"], "identified")

        rep = src.intake(self.lib, self.tmpdir, log=lambda *_: None)
        self.assertEqual([h["id"] for h in rep["held"]], ["metric-handbook"])
        self.assertEqual(metric_source["status"], "held")

    def test_sibling_failure_fails_closed(self) -> None:
        """Sibling failure from lesson l0188: Lighting Design Basics 3rd ed 2020
        claiming 3rd ed when registered copyright is 1st edition 2004.
        """
        filename = "Lighting Design Basics 3rd ed. 2020.pdf"
        target_file = self.tmpdir / "inbox" / filename
        self._create_mock_pdf(target_file, "Lighting Design Basics\nLuminaire layouts and illuminance")

        lighting_source = next(s for s in self.lib["sources"] if s["id"] == "lighting-design-basics")
        self.assertEqual(lighting_source["status"], "identified")

        with self.assertRaises(EditionMismatchError) as ctx:
            src.intake(self.lib, self.tmpdir, log=lambda *_: None)

        self.assertIn("3rd ed", str(ctx.exception))
        self.assertIn("1st", str(ctx.exception))
        self.assertIn("l0188", str(ctx.exception))
        self.assertEqual(lighting_source["status"], "identified")


class TestVillaDaylightSharedModelEvidence(unittest.TestCase):
    """Test Site 4: scripts/villa_daylight_finished.py verify_shared_model / run().
    
    Verifies that the daylight simulation refuses to run when its model
    hash differs from the render scene model hash (lesson l0661).
    """

    def test_l0661_real_recorded_failure_refuses_to_run(self) -> None:
        """Real recorded failure from lesson l0661: render and daylight analysis
        used different geometry / model hashes.
        verify_shared_model() must raise RuntimeError citing l0661 and refuse to run.
        """
        differing_render_hash = "a" * 64
        with self.assertRaises(RuntimeError) as ctx:
            vdf.verify_shared_model(render_scene_hash=differing_render_hash)
        self.assertIn("l0661", str(ctx.exception))
        self.assertIn("Render and analysis model hashes disagree", str(ctx.exception))

    def test_clean_input_stays_quiet(self) -> None:
        """Clean input with identical model hashes stays quiet."""
        from archpipe.concept import villa_render as VR
        matching_hash = VR.source_provenance(vdf.ROOT)["source_hash"]

        res = vdf.verify_shared_model(render_scene_hash=matching_hash)
        self.assertTrue(res["matches"])
        self.assertFalse(res["flagged"])
        self.assertEqual(res["render_model_hash"], matching_hash)
        self.assertEqual(res["analysis_model_hash"], matching_hash)

    def test_sibling_failure_refuses_to_run(self) -> None:
        """Sibling failure: another divergent hash fails closed."""
        sibling_render_hash = "f" * 64
        with self.assertRaises(RuntimeError) as ctx:
            vdf.verify_shared_model(render_scene_hash=sibling_render_hash)
        self.assertIn("l0661", str(ctx.exception))

    def test_missing_render_hash_reported_not_faked(self) -> None:
        """When no render scene hash is available, reports that without faking one."""
        # Pass empty string / None with non-existent scene.json path
        fake_empty_hash = ""
        check = check_shared_model(fake_empty_hash, "valid_analysis_hash")
        self.assertFalse(check["matches"])
        self.assertTrue(check["flagged"])


if __name__ == "__main__":
    unittest.main()
