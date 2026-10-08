"""Tests for C14 Phase 2 Batch A1 stage result migrations.

Covers the four entry scripts migrated to atomic stage-result contracts:
1. scripts/villa_option_pdfs.py
2. scripts/villa_furnish_pdf.py
3. scripts/villa_concepts.py
4. scripts/make_render_input.py

For each script:
(a) The real recorded failure from docs/LEARNINGS.md (l0029: a script printed FAIL
    and exited 0) reproduced with the script's own failure condition now exits
    non-zero through enforce_clean_verdict and writes a FAIL stage record.
(b) A clean run (mocking heavy builders, no Blender/Revit) exits 0 with an OK record.
(c) The stage record hashes the declared inputs and outputs.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from archpipe.stage_result import validate_stage_result
import make_render_input
import villa_concepts
import villa_furnish_pdf
import villa_option_pdfs
import yaml

# Exact quote from docs/LEARNINGS.md (line 214):
L0029_LEARNINGS_LINE = (
    "| Gates | A script printing FAIL but returning zero cannot gate a pipeline | "
    "Assert failed, missing and stale cases as well as passing cases; inspect saved "
    "evidence, not shell exit alone |"
)


class MockPdfPages:
    """Mock context manager for matplotlib.backends.backend_pdf.PdfPages."""

    def __init__(self, path: Path | str):
        self.path = Path(path)

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(b"%PDF-1.4 mock pdf content\n")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def savefig(self, *args, **kwargs):
        pass


class TestC14Phase2aVillaOptionPdfs(unittest.TestCase):
    """Proofs for scripts/villa_option_pdfs.py stage-result contract."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.opt_dir = self.tmp / "options"
        self.opt_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_l0029_option_pdfs_failure_exits_nonzero_and_writes_fail_record(self):
        """l0029 reproduction: rb['failed'] non-empty now exits non-zero and writes FAIL stage record."""
        # Quote: L0029_LEARNINGS_LINE
        readback_content = {
            "options": [
                {
                    "id": "D1",
                    "built": {"walls": 10, "doors": 4, "windows": 5},
                    "failed": ["BUILT: walls/doors under the ramp fit 1 problems"],
                    "rooms": [],
                }
            ]
        }
        (self.opt_dir / "readback.json").write_text(json.dumps(readback_content), encoding="utf-8")

        mock_layout = {"id": "D1", "title": "Design 1", "rooms": {}, "links": []}

        with patch.dict(villa_option_pdfs.SETS, {"s": (lambda: [mock_layout], self.opt_dir)}), \
             patch.object(villa_option_pdfs, "OPT", self.opt_dir), \
             patch("matplotlib.backends.backend_pdf.PdfPages", MockPdfPages), \
             patch.object(villa_option_pdfs, "plan_page", lambda *a, **k: None), \
             patch.object(villa_option_pdfs, "views_page", lambda *a, **k: None), \
             patch.object(villa_option_pdfs, "checks_page", lambda *a, **k: None), \
             patch.object(villa_option_pdfs.V, "critique", lambda lay: {"sizes": {}}), \
             patch.object(villa_option_pdfs.SO, "analyse_layout", lambda lay: {}):
            with self.assertRaises(SystemExit) as cm:
                villa_option_pdfs.main(argv=["s"])
            self.assertEqual(cm.exception.code, 1)

        stage_record = self.opt_dir / "villa-option-pdfs.stage-result.json"
        self.assertTrue(stage_record.is_file())
        record = json.loads(stage_record.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "fail")
        self.assertEqual(record["exit_code"], 1)
        self.assertIn("D1: BUILT: walls/doors under the ramp fit 1 problems", record["metadata"]["failed"])

    def test_clean_option_pdfs_exits_zero_with_ok_record_and_hashed_io(self):
        """Clean run exits 0 with status 'ok' and hashes declared inputs/outputs."""
        readback_content = {
            "options": [
                {
                    "id": "D1",
                    "built": {"walls": 10, "doors": 4, "windows": 5},
                    "failed": [],
                    "rooms": [],
                }
            ]
        }
        (self.opt_dir / "readback.json").write_text(json.dumps(readback_content), encoding="utf-8")

        mock_layout = {"id": "D1", "title": "Design 1", "rooms": {}, "links": []}

        with patch.dict(villa_option_pdfs.SETS, {"s": (lambda: [mock_layout], self.opt_dir)}), \
             patch.object(villa_option_pdfs, "OPT", self.opt_dir), \
             patch("matplotlib.backends.backend_pdf.PdfPages", MockPdfPages), \
             patch.object(villa_option_pdfs, "plan_page", lambda *a, **k: None), \
             patch.object(villa_option_pdfs, "views_page", lambda *a, **k: None), \
             patch.object(villa_option_pdfs, "checks_page", lambda *a, **k: None), \
             patch.object(villa_option_pdfs.V, "critique", lambda lay: {"sizes": {}}), \
             patch.object(villa_option_pdfs.SO, "analyse_layout", lambda lay: {}):
            rc = villa_option_pdfs.main(argv=["s"])
            self.assertEqual(rc, 0)

        stage_record = self.opt_dir / "villa-option-pdfs.stage-result.json"
        self.assertTrue(stage_record.is_file())
        valid, reason, record = validate_stage_result(stage_record, root=ROOT)
        self.assertTrue(valid)
        self.assertEqual(reason, "ok")
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["exit_code"], 0)
        self.assertTrue(record["completeness"]["complete"])

        # Hashes declared inputs and outputs
        input_keys = list(record["inputs"].keys())
        self.assertTrue(any("readback.json" in k for k in input_keys))
        output_keys = list(record["outputs"].keys())
        self.assertTrue(any("Option-D1.pdf" in k for k in output_keys))
        for out_info in record["outputs"].values():
            self.assertTrue(out_info["exists"])
            self.assertIsNotNone(out_info["sha256"])
            self.assertGreater(out_info["size_bytes"], 0)


class TestC14Phase2aVillaFurnishPdf(unittest.TestCase):
    """Proofs for scripts/villa_furnish_pdf.py stage-result contract."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.out_dir = self.tmp / "furnish-d1"
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_l0029_furnish_pdf_failure_exits_nonzero_and_writes_fail_record(self):
        """l0029 reproduction: clearance status 'fail' now exits non-zero and writes FAIL stage record."""
        failing_check_res = {
            "clearances": {
                "status": "fail",
                "problems": ["k-island front 1219 mm: a wall", "dining-table left: a column"],
                "measured": {"k-island": "clearance failure"},
            },
            "inside_room": {"status": "pass", "problems": [], "measured": {}},
        }
        mock_lay = {"id": "D1", "rooms": {}}

        with patch.object(villa_furnish_pdf, "OUT", self.out_dir), \
             patch.object(villa_furnish_pdf.R, "design", lambda d: mock_lay), \
             patch.object(villa_furnish_pdf.F, "layout", lambda l: []), \
             patch.object(villa_furnish_pdf.RS, "build", lambda l: {"doors": [], "windows": []}), \
             patch.object(villa_furnish_pdf.F, "check", lambda items, lay: failing_check_res), \
             patch("matplotlib.backends.backend_pdf.PdfPages", MockPdfPages), \
             patch.object(villa_furnish_pdf, "plan", lambda *a, **k: None):
            with self.assertRaises(SystemExit) as cm:
                villa_furnish_pdf.main()
            self.assertEqual(cm.exception.code, 1)

        stage_record = self.out_dir / "villa-furnish-pdf.stage-result.json"
        self.assertTrue(stage_record.is_file())
        record = json.loads(stage_record.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "fail")
        self.assertEqual(record["exit_code"], 1)
        self.assertTrue(any("clearances: k-island front 1219 mm: a wall" in f for f in record["metadata"]["failed_checks"]))

    def test_clean_furnish_pdf_exits_zero_with_ok_record_and_hashed_io(self):
        """Clean run exits 0 with status 'ok' and hashes declared inputs/outputs."""
        passing_check_res = {
            "clearances": {"status": "pass", "problems": [], "measured": {}},
            "inside_room": {"status": "pass", "problems": [], "measured": {}},
        }
        mock_lay = {"id": "D1", "rooms": {}}

        with patch.object(villa_furnish_pdf, "OUT", self.out_dir), \
             patch.object(villa_furnish_pdf.R, "design", lambda d: mock_lay), \
             patch.object(villa_furnish_pdf.F, "layout", lambda l: []), \
             patch.object(villa_furnish_pdf.RS, "build", lambda l: {"doors": [], "windows": []}), \
             patch.object(villa_furnish_pdf.F, "check", lambda items, lay: passing_check_res), \
             patch("matplotlib.backends.backend_pdf.PdfPages", MockPdfPages), \
             patch.object(villa_furnish_pdf, "plan", lambda *a, **k: None):
            rc = villa_furnish_pdf.main()
            self.assertEqual(rc, 0)

        stage_record = self.out_dir / "villa-furnish-pdf.stage-result.json"
        self.assertTrue(stage_record.is_file())
        valid, reason, record = validate_stage_result(stage_record, root=ROOT)
        self.assertTrue(valid)
        self.assertEqual(reason, "ok")
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["exit_code"], 0)
        self.assertTrue(record["completeness"]["complete"])

        # Hashes declared outputs
        output_keys = list(record["outputs"].keys())
        self.assertTrue(any("D1-furnished.pdf" in k for k in output_keys))
        for out_info in record["outputs"].values():
            self.assertTrue(out_info["exists"])
            self.assertIsNotNone(out_info["sha256"])
            self.assertGreater(out_info["size_bytes"], 0)


class TestC14Phase2aVillaConcepts(unittest.TestCase):
    """Proofs for scripts/villa_concepts.py stage-result contract."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.out_dir = self.tmp / "concepts"
        self.spec_dir = self.tmp / "spec"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.spec_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _mock_draw(self, lay, res, path):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        Path(str(p) + ".pdf").write_bytes(b"%PDF-1.4 mock\n")
        Path(str(p) + ".png").write_bytes(b"\x89PNG\r\n\x1a\nmock\n")

    def _mock_write(self, lay, res, folder):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"concept-{lay['id']}.json").write_text(json.dumps({"id": lay["id"]}), encoding="utf-8")

    def test_l0029_concepts_failure_exits_nonzero_and_writes_fail_record(self):
        """l0029 reproduction: res['fails'] non-zero now exits non-zero and writes FAIL stage record."""
        mock_concept = {"id": "C1", "rooms": {}, "links": []}
        failing_critique = {
            "id": "C1",
            "fails": ["wc_access", "suite_privacy"],
            "warnings": [],
            "elevation_checks": [],
        }

        with patch.object(villa_concepts, "OUT", self.out_dir), \
             patch.object(villa_concepts, "SPEC", self.spec_dir), \
             patch.object(villa_concepts.V, "concepts", lambda: [mock_concept]), \
             patch.object(villa_concepts.V, "critique", lambda lay: failing_critique), \
             patch.object(villa_concepts.V, "elevation_checks", lambda lay: []), \
             patch.object(villa_concepts.V, "write", self._mock_write), \
             patch.object(villa_concepts, "draw", self._mock_draw), \
             patch.object(villa_concepts, "draw_section", self._mock_draw):
            with self.assertRaises(SystemExit) as cm:
                villa_concepts.main()
            self.assertEqual(cm.exception.code, 1)

        stage_record = self.out_dir / "villa-concepts.stage-result.json"
        self.assertTrue(stage_record.is_file())
        record = json.loads(stage_record.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "fail")
        self.assertEqual(record["exit_code"], 1)
        self.assertIn("C1: wc_access", record["metadata"]["failures"])

    def test_clean_concepts_exits_zero_with_ok_record_and_hashed_io(self):
        """Clean run exits 0 with status 'ok' and hashes declared inputs/outputs."""
        mock_concept = {"id": "C1", "rooms": {}, "links": []}
        clean_critique = {
            "id": "C1",
            "fails": [],
            "warnings": [],
            "elevation_checks": [],
        }

        with patch.object(villa_concepts, "OUT", self.out_dir), \
             patch.object(villa_concepts, "SPEC", self.spec_dir), \
             patch.object(villa_concepts.V, "concepts", lambda: [mock_concept]), \
             patch.object(villa_concepts.V, "critique", lambda lay: clean_critique), \
             patch.object(villa_concepts.V, "elevation_checks", lambda lay: []), \
             patch.object(villa_concepts.V, "write", self._mock_write), \
             patch.object(villa_concepts, "draw", self._mock_draw), \
             patch.object(villa_concepts, "draw_section", self._mock_draw):
            rc = villa_concepts.main()
            self.assertEqual(rc, 0)

        stage_record = self.out_dir / "villa-concepts.stage-result.json"
        self.assertTrue(stage_record.is_file())
        valid, reason, record = validate_stage_result(stage_record, root=ROOT)
        self.assertTrue(valid)
        self.assertEqual(reason, "ok")
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["exit_code"], 0)
        self.assertTrue(record["completeness"]["complete"])

        # Hashes declared outputs
        output_keys = list(record["outputs"].keys())
        self.assertTrue(any("concept-C1.json" in k for k in output_keys))
        self.assertTrue(any("concept-C1-r4.pdf" in k for k in output_keys))
        self.assertTrue(any("section-C1-r4.pdf" in k for k in output_keys))
        for out_info in record["outputs"].values():
            self.assertTrue(out_info["exists"])
            self.assertIsNotNone(out_info["sha256"])
            self.assertGreater(out_info["size_bytes"], 0)


class TestC14Phase2aMakeRenderInput(unittest.TestCase):
    """Proofs for scripts/make_render_input.py stage-result contract."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.extract_path = self.tmp / "bedroom-from-revit.json"
        self.spec_path = self.tmp / "bedroom-test.yaml"
        self.ies_dir = self.tmp / "ies"
        self.ies_dir.mkdir(parents=True, exist_ok=True)
        self.ies_file = self.ies_dir / "test.ies"
        self.ies_file.write_text("IESNA:LM-63-2002\nTILT=NONE\n1 1000 1 1 1 1 1 0 0 0\n1\n0\n0\n1000\n", encoding="utf-8")
        self.out_path = self.tmp / "bedroom-render.json"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_l0029_make_render_input_failure_exits_nonzero_and_writes_fail_record(self):
        """l0029 reproduction: orphan fixtures in model now exit non-zero and write FAIL stage record."""
        # Extract contains orphan fixture not defined in spec
        extract_data = {
            "rooms": [{"id": "bedroom"}],
            "lighting": [
                {
                    "mark": "LT-ORPHAN",
                    "family": "Cylinder",
                    "at": [1000, 1500],
                    "mounting_height": 2400,
                    "meshes": [],
                }
            ],
        }
        self.extract_path.write_text(json.dumps(extract_data), encoding="utf-8")

        spec_data = {
            "room": {"ceiling_height": 2700},
            "lighting": [
                {
                    "id": "LT-01",
                    "ies": "test.ies",
                    "lumens": 1000,
                    "kelvin": 3000,
                    "watts": 10,
                }
            ],
        }
        self.spec_path.write_text(yaml.safe_dump(spec_data), encoding="utf-8")

        args = [
            "--extract", str(self.extract_path),
            "--spec", str(self.spec_path),
            "--ies-dir", str(self.ies_dir),
            "--out", str(self.out_path),
        ]

        with patch.object(make_render_input.ph, "find_ies", lambda name, d: self.ies_file), \
             patch.object(make_render_input, "source_point", lambda m: [1000, 1500, 2400, "measured"]), \
             patch.object(make_render_input, "photometry_matches_fitting", lambda dims, m: []):
            with self.assertRaises(SystemExit) as cm:
                make_render_input.main(args)
            self.assertEqual(cm.exception.code, 1)

        stage_record = self.out_path.parent / "make-render-input.stage-result.json"
        self.assertTrue(stage_record.is_file())
        record = json.loads(stage_record.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "fail")
        self.assertEqual(record["exit_code"], 1)
        self.assertEqual(len(record["metadata"]["orphan_fixtures"]), 1)
        self.assertEqual(record["metadata"]["orphan_fixtures"][0]["mark"], "LT-ORPHAN")

    def test_clean_make_render_input_exits_zero_with_ok_record_and_hashed_io(self):
        """Clean run exits 0 with status 'ok' and hashes declared inputs/outputs."""
        extract_data = {
            "rooms": [{"id": "bedroom"}],
            "lighting": [
                {
                    "mark": "LT-01",
                    "family": "Pendant",
                    "at": [1000, 1500],
                    "mounting_height": 2400,
                    "meshes": [],
                }
            ],
        }
        self.extract_path.write_text(json.dumps(extract_data), encoding="utf-8")

        spec_data = {
            "room": {"ceiling_height": 2700},
            "lighting": [
                {
                    "id": "LT-01",
                    "ies": "test.ies",
                    "lumens": 1000,
                    "kelvin": 3000,
                    "watts": 10,
                }
            ],
        }
        self.spec_path.write_text(yaml.safe_dump(spec_data), encoding="utf-8")

        args = [
            "--extract", str(self.extract_path),
            "--spec", str(self.spec_path),
            "--ies-dir", str(self.ies_dir),
            "--out", str(self.out_path),
        ]

        with patch.object(make_render_input.ph, "find_ies", lambda name, d: self.ies_file), \
             patch.object(make_render_input, "source_point", lambda m: [1000, 1500, 2400, "measured"]), \
             patch.object(make_render_input, "photometry_matches_fitting", lambda dims, m: []):
            rc = make_render_input.main(args)
            self.assertEqual(rc, 0)

        stage_record = self.out_path.parent / "make-render-input.stage-result.json"
        self.assertTrue(stage_record.is_file())
        valid, reason, record = validate_stage_result(stage_record, root=ROOT)
        self.assertTrue(valid)
        self.assertEqual(reason, "ok")
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["exit_code"], 0)
        self.assertTrue(record["completeness"]["complete"])

        # Hashes declared inputs and outputs
        input_keys = list(record["inputs"].keys())
        self.assertTrue(any("bedroom-from-revit.json" in k for k in input_keys))
        self.assertTrue(any("bedroom-test.yaml" in k for k in input_keys))
        output_keys = list(record["outputs"].keys())
        self.assertTrue(any("bedroom-render.json" in k for k in output_keys))
        for out_info in record["outputs"].values():
            self.assertTrue(out_info["exists"])
            self.assertIsNotNone(out_info["sha256"])
            self.assertGreater(out_info["size_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
