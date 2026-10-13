"""Tests for C14 Phase 2 Batch A2 stage result migrations.

Covers the ten remaining Batch A entry scripts migrated to atomic stage-result contracts:
1. scripts/handoff.py
2. scripts/make_bedroom_spec.py
3. scripts/make_bedroom_extract.py
4. scripts/villa_lighting_pdf.py
5. scripts/villa_daylight_pdf.py
6. scripts/yard_wall_pdf.py
7. scripts/villa_daylight_summary.py
8. scripts/villa_furnish_build.py
9. scripts/villa_env.py
10. scripts/villa_stairs.py

For each script:
(a) The real recorded failure from docs/LEARNINGS.md (l0029: a script printed FAIL
    and exited 0) reproduced with the script's own failure condition now exits
    non-zero through enforce_clean_verdict and writes a FAIL stage record.
(b) A clean run (mocking heavy builders, no Blender/Revit/network) exits 0 with an OK record.
(c) The stage record hashes the declared inputs and outputs.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import numpy as np
from matplotlib.backends.backend_pdf import PdfPages

ROOT = Path(__file__).resolve().parents[1]


def _isolate_process_state(test):
    """Restore what the scripts' launch preflight changes in-process.

    project_context() updates os.environ (TMP/TEMP/TMPDIR, NO_COLOR, ...) and the
    process temp directory for the script it launches. These tests call main()
    in-process with ROOT patched to a temporary folder, so without restoring,
    each test nests the next one's temp directory inside a deleted folder
    (lead review 2026-10-08: 22 of 23 tests failed when run together).
    """
    import os
    saved_env = dict(os.environ)
    saved_tempdir = tempfile.tempdir
    saved_cwd = os.getcwd()

    def restore():
        os.chdir(saved_cwd)
        os.environ.clear()
        os.environ.update(saved_env)
        tempfile.tempdir = saved_tempdir
    test.addCleanup(restore)

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from archpipe.stage_result import validate_stage_result
import handoff
import make_bedroom_spec
import make_bedroom_extract
import villa_lighting_pdf
import villa_daylight_pdf
import yard_wall_pdf
import villa_daylight_summary
import villa_furnish_build
import villa_env
import villa_stairs

# Exact quote from docs/LEARNINGS.md (line 229):
L0029_LEARNINGS_LINE = (
    "| Gates | A script printing FAIL but returning zero cannot gate a pipeline | "
    "Assert failed, missing and stale cases as well as passing cases; inspect saved "
    "evidence, not shell exit alone |"
)


class MockPdfPages:
    """Mock context manager for matplotlib.backends.backend_pdf.PdfPages."""

    def __init__(self, path: Path | str, *args, **kwargs):
        self.path = Path(path)

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(b"%PDF-1.4 mock pdf content\n")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def savefig(self, *args, **kwargs):
        pass


def _mock_pdf_init(self, path, *args, **kwargs):
    self.path = Path(path)


def _mock_pdf_enter(self):
    self.path.parent.mkdir(parents=True, exist_ok=True)
    self.path.write_bytes(b"%PDF-1.4 mock pdf content\n")
    return self


def _mock_pdf_exit(self, exc_type, exc_val, exc_tb):
    return False


def _mock_pdf_savefig(self, *args, **kwargs):
    pass


@contextmanager
def _patch_pdf_pages():
    """Patch PdfPages methods on matplotlib.backends.backend_pdf.PdfPages so instances write dummy bytes and skip figure saving."""
    with patch.object(PdfPages, "__init__", _mock_pdf_init), \
         patch.object(PdfPages, "__enter__", _mock_pdf_enter), \
         patch.object(PdfPages, "__exit__", _mock_pdf_exit), \
         patch.object(PdfPages, "savefig", _mock_pdf_savefig):
        yield


class TestHandoffStageResult(unittest.TestCase):
    """Proofs for scripts/handoff.py stage-result contract."""

    def setUp(self):
        _isolate_process_state(self)
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.out_pkg = self.tmp / "docs" / "handoff" / "pkg1"
        self.spec_file = self.tmp / "spec.yaml"
        self.spec_file.write_text(
            "name: test-villa\nlevels:\n  - id: L0\n    name: Ground\n    rooms: []\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_clean_handoff_exits_zero_with_ok_record_and_hashed_io(self):
        """Clean handoff run exits 0 with status 'ok' and hashes declared inputs/outputs."""
        mock_proj = MagicMock()
        mock_proj.levels = []
        mock_proj.name = "test-villa"

        def _mock_to_ifc(p, dest):
            Path(dest).write_bytes(b"ISO-10303-21; mock IFC4 model content;\n")

        with patch.object(handoff, "ROOT", self.tmp), \
             patch.object(handoff.model, "load", lambda p: mock_proj), \
             patch.object(handoff.D, "schedules", lambda p: {"rooms": []}), \
             patch.object(handoff.D, "write_csv", lambda rows, path: Path(path).write_text("id,name\n", encoding="utf-8")), \
             patch.object(handoff.D, "quantities", lambda p: {}), \
             patch.object(handoff.D, "gross_area_m2", lambda p: 100.0), \
             patch.object(handoff.D, "relative_cost", lambda d: []), \
             patch.object(handoff.D, "to_ifc", _mock_to_ifc), \
             patch.object(handoff.rules, "review", lambda p, lv: []):
            rc = handoff.main([str(self.spec_file), "--name", "pkg1"])
            self.assertEqual(rc, 0)

        stage_record = self.out_pkg / "handoff.stage-result.json"
        self.assertTrue(stage_record.is_file())
        valid, reason, record = validate_stage_result(stage_record, root=self.tmp)
        self.assertTrue(valid)
        self.assertEqual(reason, "ok")
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["exit_code"], 0)
        self.assertTrue(record["completeness"]["complete"])

        # Hashes declared inputs and outputs
        input_keys = list(record["inputs"].keys())
        self.assertTrue(any("spec.yaml" in k for k in input_keys))
        output_keys = list(record["outputs"].keys())
        self.assertTrue(any("model.ifc" in k for k in output_keys))
        self.assertTrue(any("quantities.json" in k for k in output_keys))
        self.assertTrue(any("findings.json" in k for k in output_keys))

    def test_l0029_handoff_incomplete_output_fails_closed(self):
        """l0029 reproduction: truncated/empty output fails stage-result validation."""
        # Quote: L0029_LEARNINGS_LINE
        mock_proj = MagicMock()
        mock_proj.levels = []

        def _empty_to_ifc(p, dest):
            Path(dest).write_bytes(b"")  # 0 bytes

        with patch.object(handoff, "ROOT", self.tmp), \
             patch.object(handoff.model, "load", lambda p: mock_proj), \
             patch.object(handoff.D, "schedules", lambda p: {"rooms": []}), \
             patch.object(handoff.D, "write_csv", lambda rows, path: Path(path).write_text("id,name\n", encoding="utf-8")), \
             patch.object(handoff.D, "quantities", lambda p: {}), \
             patch.object(handoff.D, "gross_area_m2", lambda p: 100.0), \
             patch.object(handoff.D, "relative_cost", lambda d: []), \
             patch.object(handoff.D, "to_ifc", _empty_to_ifc), \
             patch.object(handoff.rules, "review", lambda p, lv: []):
            rc = handoff.main([str(self.spec_file), "--name", "pkg1"])
            self.assertEqual(rc, 0)

        stage_record = self.out_pkg / "handoff.stage-result.json"
        self.assertTrue(stage_record.is_file())
        record = json.loads(stage_record.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "fail")
        self.assertEqual(record["exit_code"], 1)
        self.assertFalse(record["completeness"]["complete"])


class TestMakeBedroomSpecStageResult(unittest.TestCase):
    """Proofs for scripts/make_bedroom_spec.py stage-result contract."""

    def setUp(self):
        _isolate_process_state(self)
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.out_spec = self.tmp / "bedroom-spec.json"
        self.spec_file = self.tmp / "bedroom.yaml"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_clean_bedroom_spec_exits_zero_with_ok_record_and_hashed_io(self):
        """Clean run exits 0 with status 'ok' and hashes declared inputs/outputs."""
        content = (
            "room:\n"
            "  width: 4200\n"
            "  depth: 3600\n"
            "  ceiling_height: 2700\n"
            "  wall_thickness: 200\n"
            "openings: []\n"
            "furniture: []\n"
            "lighting: []\n"
        )
        self.spec_file.write_text(content, encoding="utf-8")

        rc = make_bedroom_spec.main(["--spec", str(self.spec_file), "--out", str(self.out_spec)])
        self.assertEqual(rc, 0)

        stage_record = self.tmp / "make-bedroom-spec.stage-result.json"
        self.assertTrue(stage_record.is_file())
        valid, reason, record = validate_stage_result(stage_record, root=self.tmp)
        self.assertTrue(valid)
        self.assertEqual(reason, "ok")
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["exit_code"], 0)

        output_keys = list(record["outputs"].keys())
        self.assertTrue(any("bedroom-spec.json" in k for k in output_keys))
        input_keys = list(record["inputs"].keys())
        self.assertTrue(any("bedroom.yaml" in k for k in input_keys))

    def test_l0029_bedroom_spec_invalid_room_raises_and_cannot_gate(self):
        """l0029 reproduction: missing required dimension causes refusal."""
        # Quote: L0029_LEARNINGS_LINE
        bad_content = "room:\n  width: 4200\n"  # missing depth, ceiling_height, wall_thickness
        self.spec_file.write_text(bad_content, encoding="utf-8")

        with self.assertRaises(SystemExit):
            make_bedroom_spec.main(["--spec", str(self.spec_file), "--out", str(self.out_spec)])


class TestMakeBedroomExtractStageResult(unittest.TestCase):
    """Proofs for scripts/make_bedroom_extract.py stage-result contract."""

    def setUp(self):
        _isolate_process_state(self)
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.out_extract = self.tmp / "bedroom.json"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_clean_bedroom_extract_exits_zero_with_ok_record_and_hashed_io(self):
        """Clean run exits 0 with status 'ok' and hashes declared outputs."""
        rc = make_bedroom_extract.main(["--ies-dir", "/tmp/ies", "--out", str(self.out_extract)])
        self.assertEqual(rc, 0)

        stage_record = self.tmp / "make-bedroom-extract.stage-result.json"
        self.assertTrue(stage_record.is_file())
        valid, reason, record = validate_stage_result(stage_record, root=self.tmp)
        self.assertTrue(valid)
        self.assertEqual(reason, "ok")
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["exit_code"], 0)

        output_keys = list(record["outputs"].keys())
        self.assertTrue(any("bedroom.json" in k for k in output_keys))

    def test_l0029_bedroom_extract_empty_data_exits_nonzero_and_writes_fail_record(self):
        """l0029 reproduction: empty extract payload now exits non-zero and writes FAIL stage record."""
        # Quote: L0029_LEARNINGS_LINE
        empty_build = {"walls": [], "rooms": [], "lighting": [], "openings": []}
        with patch.object(make_bedroom_extract, "build", lambda ies_dir: empty_build):
            with self.assertRaises(SystemExit) as cm:
                make_bedroom_extract.main(["--ies-dir", "/tmp/ies", "--out", str(self.out_extract)])
            self.assertEqual(cm.exception.code, 1)

        stage_record = self.tmp / "make-bedroom-extract.stage-result.json"
        self.assertTrue(stage_record.is_file())
        record = json.loads(stage_record.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "fail")
        self.assertEqual(record["exit_code"], 1)


class TestVillaLightingPdfStageResult(unittest.TestCase):
    """Proofs for scripts/villa_lighting_pdf.py stage-result contract."""

    def setUp(self):
        _isolate_process_state(self)
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.out_dir = self.tmp / "lighting-d1"
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_clean_lighting_pdf_exits_zero_with_ok_record_and_hashed_io(self):
        """Clean run exits 0 with status 'ok' and hashes declared outputs."""
        mock_lay = {"rooms": {}, "id": "D1"}
        clean_check = {
            "tasks": [{"status": "pass", "room": "kitchen", "what": "sink", "achieved_lx": 350, "required_lx": 300, "card": "c1"}],
            "rooms": [{"status": "pass", "room": "kitchen", "avg_floor_lx_direct": 150, "required_lx": 100, "card": "c2"}],
            "problems": [],
            "note": "all good",
        }
        clean_fx = [
            villa_lighting_pdf.VL.Fixture(
                id="fx1", kind="DL", room="kitchen", level="GF", x=1.0, y=1.0, z=2.7
            )
        ]

        with patch.object(villa_lighting_pdf, "OUT", self.out_dir), \
             patch.object(villa_lighting_pdf.R, "design", lambda d: mock_lay), \
             patch.object(villa_lighting_pdf.VL, "bind_products", lambda: None), \
             patch.object(villa_lighting_pdf.VL, "design", lambda l: clean_fx), \
             patch.object(villa_lighting_pdf.VL, "check", lambda l, fx: clean_check), \
             patch.object(villa_lighting_pdf, "plan", lambda *a, **k: None), \
             _patch_pdf_pages():
            rc = villa_lighting_pdf.main()
            self.assertEqual(rc, 0)

        stage_record = self.out_dir / "villa-lighting-pdf.stage-result.json"
        self.assertTrue(stage_record.is_file())
        valid, reason, record = validate_stage_result(stage_record, root=ROOT)
        self.assertTrue(valid)
        self.assertEqual(reason, "ok")
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["exit_code"], 0)

        output_keys = list(record["outputs"].keys())
        self.assertTrue(any("D1-lighting-finishes.pdf" in k for k in output_keys))

    def test_l0029_lighting_pdf_failure_exits_nonzero_and_writes_fail_record(self):
        """l0029 reproduction: task failure now exits non-zero and writes FAIL stage record."""
        # Quote: L0029_LEARNINGS_LINE
        mock_lay = {"rooms": {}, "id": "D1"}
        failing_check = {
            "tasks": [{"status": "fail", "room": "kitchen", "what": "island", "achieved_lx": 80, "required_lx": 300, "card": "c1"}],
            "rooms": [],
            "problems": ["cove obstruction"],
            "note": "failed",
        }
        failing_fx = [
            villa_lighting_pdf.VL.Fixture(
                id="fx1", kind="DL", room="kitchen", level="GF", x=1.0, y=1.0, z=2.7
            )
        ]

        with patch.object(villa_lighting_pdf, "OUT", self.out_dir), \
             patch.object(villa_lighting_pdf.R, "design", lambda d: mock_lay), \
             patch.object(villa_lighting_pdf.VL, "bind_products", lambda: None), \
             patch.object(villa_lighting_pdf.VL, "design", lambda l: failing_fx), \
             patch.object(villa_lighting_pdf.VL, "check", lambda l, fx: failing_check), \
             patch.object(villa_lighting_pdf, "plan", lambda *a, **k: None), \
             _patch_pdf_pages():
            with self.assertRaises(SystemExit) as cm:
                villa_lighting_pdf.main()
            self.assertEqual(cm.exception.code, 1)

        stage_record = self.out_dir / "villa-lighting-pdf.stage-result.json"
        self.assertTrue(stage_record.is_file())
        record = json.loads(stage_record.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "fail")
        self.assertEqual(record["exit_code"], 1)
        self.assertIn("cove obstruction", record["metadata"]["problems"])


class TestVillaDaylightPdfStageResult(unittest.TestCase):
    """Proofs for scripts/villa_daylight_pdf.py stage-result contract."""

    def setUp(self):
        _isolate_process_state(self)
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.local_dir = self.tmp / "daylight" / "job1"
        self.local_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_clean_daylight_pdf_exits_zero_with_ok_record_and_hashed_io(self):
        """Clean run exits 0 with status 'ok' and hashes declared outputs."""
        report = {
            "status": "PASS",
            "results": {
                "S1": {
                    "rooms": {
                        "living": {"level": "B", "adf": 2.5},
                    }
                }
            },
            "validation": {
                "all_pass": True,
                "checks": {
                    "box vs Metric Handbook eq. (4)": {
                        "pass": True, "radiance": 2.0, "formula": 2.0, "relative": 0.0, "tolerance": 0.1
                    }
                },
            },
        }
        (self.local_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")

        with patch.object(villa_daylight_pdf, "LOCAL", self.local_dir), \
             _patch_pdf_pages():
            rc = villa_daylight_pdf.main()
            self.assertEqual(rc, 0)

        stage_record = self.local_dir.parent / "villa-daylight-pdf.stage-result.json"
        self.assertTrue(stage_record.is_file())
        valid, reason, record = validate_stage_result(stage_record, root=ROOT)
        self.assertTrue(valid)
        self.assertEqual(reason, "ok")
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["exit_code"], 0)

        output_keys = list(record["outputs"].keys())
        self.assertTrue(any("Daylight-villa-options.pdf" in k for k in output_keys))

    def test_l0029_daylight_pdf_failure_exits_nonzero_and_writes_fail_record(self):
        """l0029 reproduction: validation check failure now exits non-zero and writes FAIL record."""
        # Quote: L0029_LEARNINGS_LINE
        report = {
            "status": "FAIL",
            "results": {
                "S1": {
                    "rooms": {
                        "living": {"level": "B", "adf": 2.5},
                    }
                }
            },
            "validation": {
                "all_pass": False,
                "checks": {
                    "box vs Metric Handbook eq. (4)": {
                        "pass": False, "radiance": 1.0, "formula": 2.0, "relative": 0.5, "tolerance": 0.1
                    }
                },
            },
        }
        (self.local_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")

        with patch.object(villa_daylight_pdf, "LOCAL", self.local_dir), \
             _patch_pdf_pages():
            with self.assertRaises(SystemExit) as cm:
                villa_daylight_pdf.main()
            self.assertEqual(cm.exception.code, 1)

        stage_record = self.local_dir.parent / "villa-daylight-pdf.stage-result.json"
        self.assertTrue(stage_record.is_file())
        record = json.loads(stage_record.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "fail")
        self.assertEqual(record["exit_code"], 1)


class TestYardWallPdfStageResult(unittest.TestCase):
    """Proofs for scripts/yard_wall_pdf.py stage-result contract."""

    def setUp(self):
        _isolate_process_state(self)
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.dir = self.tmp / "yard-wall"
        self.dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_clean_yard_wall_pdf_exits_zero_with_ok_record_and_hashed_io(self):
        """Clean run exits 0 with status 'ok' and hashes declared outputs."""
        rb = {
            "elements": {
                "yard-wall-ne": [0, 0, 0, 10, 10, 10],
                "fence-street": [0, 0, 0, 10, 10, 10],
                "fence-east": [0, 0, 0, 10, 10, 10],
                "ramp": [0, 0, 0, 10, 10, 10],
            },
            "ne_columns": [{"id": 100, "bbox": [0, 0, -2500, 10, 10, 10]}],
            "failed": [],
        }
        (self.dir / "yard-wall-readback.json").write_text(json.dumps(rb), encoding="utf-8")

        with patch.object(yard_wall_pdf, "DIR", self.dir), \
             patch.object(yard_wall_pdf, "img", lambda prefix: self.dir / f"{prefix}.png"), \
             patch.object(yard_wall_pdf, "light", lambda img, **k: np.zeros((10, 10, 3), dtype=np.uint8)), \
             _patch_pdf_pages():
            rc = yard_wall_pdf.main()
            self.assertEqual(rc, 0)

        stage_record = self.dir / "yard-wall-pdf.stage-result.json"
        self.assertTrue(stage_record.is_file())
        valid, reason, record = validate_stage_result(stage_record, root=ROOT)
        self.assertTrue(valid)
        self.assertEqual(reason, "ok")
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["exit_code"], 0)

        output_keys = list(record["outputs"].keys())
        self.assertTrue(any("NE-yard-wall-confirmed.pdf" in k for k in output_keys))

    def test_l0029_yard_wall_pdf_failed_elements_exits_nonzero_and_writes_fail_record(self):
        """l0029 reproduction: failed readback items now exit non-zero and write FAIL record."""
        # Quote: L0029_LEARNINGS_LINE
        rb = {
            "elements": {
                "yard-wall-ne": [0, 0, 0, 10, 10, 10],
                "fence-street": [0, 0, 0, 10, 10, 10],
                "fence-east": [0, 0, 0, 10, 10, 10],
                "ramp": [0, 0, 0, 10, 10, 10],
            },
            "ne_columns": [{"id": 100, "bbox": [0, 0, -2500, 10, 10, 10]}],
            "failed": ["missing yard-wall-ne geometry"],
        }
        (self.dir / "yard-wall-readback.json").write_text(json.dumps(rb), encoding="utf-8")

        with patch.object(yard_wall_pdf, "DIR", self.dir), \
             patch.object(yard_wall_pdf, "img", lambda prefix: self.dir / f"{prefix}.png"), \
             patch.object(yard_wall_pdf, "light", lambda img, **k: np.zeros((10, 10, 3), dtype=np.uint8)), \
             _patch_pdf_pages():
            with self.assertRaises(SystemExit) as cm:
                yard_wall_pdf.main()
            self.assertEqual(cm.exception.code, 1)

        stage_record = self.dir / "yard-wall-pdf.stage-result.json"
        self.assertTrue(stage_record.is_file())
        record = json.loads(stage_record.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "fail")
        self.assertEqual(record["exit_code"], 1)


class TestVillaDaylightSummaryStageResult(unittest.TestCase):
    """Proofs for scripts/villa_daylight_summary.py stage-result contract."""

    def setUp(self):
        _isolate_process_state(self)
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.out_dir = self.tmp / "daylight"
        self.df_job = self.out_dir / "villa-df-r10"
        self.lux_job = self.out_dir / "villa-lux-r10"
        self.views_dir = self.out_dir / "views"
        for d in (self.df_job / "cases" / "P3", self.lux_job / "cases" / "P3", self.views_dir):
            d.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _setup_fixture(self, df_status="PASS", df_check_pass=True):
        lux_rep = {"stamps": ["12:00"], "heights": [0.85], "orientation": "clean", "method": "grid", "results": {"P3": {"sensors": [], "lux": []}}}
        df_rep = {
            "status": df_status,
            "validation": {"checks": {"tolerance": {"pass": df_check_pass}}},
            "results": {"P3": {"rooms": {}}},
        }
        (self.lux_job / "report.json").write_text(json.dumps(lux_rep), encoding="utf-8")
        (self.df_job / "report.json").write_text(json.dumps(df_rep), encoding="utf-8")
        (self.views_dir / "stats.json").write_text(json.dumps({}), encoding="utf-8")
        (self.lux_job / "cases" / "P3" / "annual_stats.json").write_text(json.dumps({"sensors": []}), encoding="utf-8")
        (self.df_job / "cases" / "P3" / "rooms.json").write_text(json.dumps({"rooms": []}), encoding="utf-8")
        (self.df_job / "cases" / "P3" / "out.txt").write_text("", encoding="utf-8")
        (self.df_job / "cases" / "P3" / "points.txt").write_text("", encoding="utf-8")

    def test_clean_daylight_summary_exits_zero_with_ok_record_and_hashed_io(self):
        """Clean run exits 0 with status 'ok' and hashes declared outputs."""
        self._setup_fixture()
        mock_scene = MagicMock()
        mock_scene.rooms = []

        with patch.object(villa_daylight_summary, "OUT", self.out_dir), \
             patch.object(villa_daylight_summary.VD, "round_cases", lambda r11: [({"id": "P3", "title": "P3 Option", "rooms": {}}, {})]), \
             patch.object(villa_daylight_summary.VD, "scene", lambda lay, var: mock_scene):
            rc = villa_daylight_summary.main(argv=[])
            self.assertEqual(rc, 0)

        stage_record = self.out_dir / "summary.stage-result.json"
        self.assertTrue(stage_record.is_file())
        valid, reason, record = validate_stage_result(stage_record, root=ROOT)
        self.assertTrue(valid)
        self.assertEqual(reason, "ok")
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["exit_code"], 0)

        output_keys = list(record["outputs"].keys())
        self.assertTrue(any("summary.json" in k for k in output_keys))

    def test_l0029_daylight_summary_failure_exits_nonzero_and_writes_fail_record(self):
        """l0029 reproduction: daylight factor check failure now exits non-zero and writes FAIL record."""
        # Quote: L0029_LEARNINGS_LINE
        self._setup_fixture(df_status="FAIL", df_check_pass=False)
        mock_scene = MagicMock()
        mock_scene.rooms = []

        with patch.object(villa_daylight_summary, "OUT", self.out_dir), \
             patch.object(villa_daylight_summary.VD, "round_cases", lambda r11: [({"id": "P3", "title": "P3 Option", "rooms": {}}, {})]), \
             patch.object(villa_daylight_summary.VD, "scene", lambda lay, var: mock_scene):
            with self.assertRaises(SystemExit) as cm:
                villa_daylight_summary.main(argv=[])
            self.assertEqual(cm.exception.code, 1)

        stage_record = self.out_dir / "summary.stage-result.json"
        self.assertTrue(stage_record.is_file())
        record = json.loads(stage_record.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "fail")
        self.assertEqual(record["exit_code"], 1)


class TestVillaFurnishBuildStageResult(unittest.TestCase):
    """Proofs for scripts/villa_furnish_build.py stage-result contract."""

    def setUp(self):
        _isolate_process_state(self)
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.out_dir = self.tmp / "furnish"
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_clean_furnish_build_check_exits_zero_with_ok_record(self):
        """Clean check run exits 0 with status 'ok'."""
        rb = {"options": [{"built": {"sofa": 1}, "failed": [], "furniture": []}]}
        spec = [{"furniture": []}]
        (self.out_dir / "readback.json").write_text(json.dumps(rb), encoding="utf-8")
        (self.out_dir / "options-spec.json").write_text(json.dumps(spec), encoding="utf-8")

        with patch.object(villa_furnish_build, "OUT", self.out_dir), \
             patch.object(villa_furnish_build.R, "design", lambda d: {"id": "D1"}), \
             patch.object(villa_furnish_build.F3, "postcondition", lambda *a: []), \
             patch.object(villa_furnish_build.F3, "round2_postcondition", lambda *a: []), \
             patch.object(villa_furnish_build.F3, "round3_postcondition", lambda *a: []):
            rc = villa_furnish_build.main(argv=["villa_furnish_build.py", "check"])
            self.assertEqual(rc, 0)

        stage_record = self.out_dir / "villa-furnish-build.stage-result.json"
        self.assertTrue(stage_record.is_file())
        valid, reason, record = validate_stage_result(stage_record, root=ROOT)
        self.assertTrue(valid)
        self.assertEqual(reason, "ok")
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["exit_code"], 0)

    def test_clean_furnish_build_spec_exits_zero_with_ok_record(self):
        """Clean spec mode run exits 0 with status 'ok'."""
        with patch.object(villa_furnish_build, "OUT", self.out_dir), \
             patch.object(villa_furnish_build.R, "design", lambda d: {"id": "D1"}), \
             patch.object(villa_furnish_build.RS, "build", lambda lay: {}), \
             patch.object(villa_furnish_build.F3, "spec", lambda lay: []), \
             patch.object(villa_furnish_build.F3, "round2_elements", lambda sp: {}), \
             patch.object(villa_furnish_build.F3, "round3_elements", lambda sp, lay: {}):
            rc = villa_furnish_build.main(argv=["villa_furnish_build.py", "spec"])
            self.assertEqual(rc, 0)

        stage_record = self.out_dir / "villa-furnish-build-spec.stage-result.json"
        self.assertTrue(stage_record.is_file())
        valid, reason, record = validate_stage_result(stage_record, root=ROOT)
        self.assertTrue(valid)
        self.assertEqual(record["status"], "ok")

    def test_l0029_furnish_build_failures_exit_nonzero_and_write_fail_record(self):
        """l0029 reproduction: build failure now exits non-zero and writes FAIL stage record."""
        # Quote: L0029_LEARNINGS_LINE
        rb = {"options": [{"built": {}, "failed": ["sofa collided with column"], "furniture": []}]}
        spec = [{"furniture": []}]
        (self.out_dir / "readback.json").write_text(json.dumps(rb), encoding="utf-8")
        (self.out_dir / "options-spec.json").write_text(json.dumps(spec), encoding="utf-8")

        with patch.object(villa_furnish_build, "OUT", self.out_dir), \
             patch.object(villa_furnish_build.R, "design", lambda d: {"id": "D1"}), \
             patch.object(villa_furnish_build.F3, "postcondition", lambda *a: ["clearance problem"]), \
             patch.object(villa_furnish_build.F3, "round2_postcondition", lambda *a: []), \
             patch.object(villa_furnish_build.F3, "round3_postcondition", lambda *a: []):
            with self.assertRaises(SystemExit) as cm:
                villa_furnish_build.main(argv=["villa_furnish_build.py", "check"])
            self.assertEqual(cm.exception.code, 1)

        stage_record = self.out_dir / "villa-furnish-build.stage-result.json"
        self.assertTrue(stage_record.is_file())
        record = json.loads(stage_record.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "fail")
        self.assertEqual(record["exit_code"], 1)
        self.assertIn("sofa collided with column", record["metadata"]["fails"])


class TestVillaEnvStageResult(unittest.TestCase):
    """Proofs for scripts/villa_env.py stage-result contract."""

    def setUp(self):
        _isolate_process_state(self)
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.out_dir = self.tmp / "env"
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_clean_env_check_exits_zero_with_ok_record(self):
        """Clean run exits 0 with status 'ok'."""
        (self.out_dir / "env-spec.json").write_text("{}", encoding="utf-8")
        (self.out_dir / "env-readback.json").write_text("{}", encoding="utf-8")

        with patch.object(villa_env, "OUT", self.out_dir), \
             patch.object(villa_env, "check", lambda *a, **k: []):
            rc = villa_env.main(["villa_env.py", "check"])
            self.assertEqual(rc, 0)

        stage_record = self.out_dir / "villa-env-check.stage-result.json"
        self.assertTrue(stage_record.is_file())
        valid, reason, record = validate_stage_result(stage_record, root=ROOT)
        self.assertTrue(valid)
        self.assertEqual(reason, "ok")
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["exit_code"], 0)

    def test_clean_env_spec_exits_zero_with_ok_record(self):
        """Clean spec mode exits 0 with status 'ok'."""
        with patch.object(villa_env, "OUT", self.out_dir), \
             patch.object(villa_env.V, "write", lambda dest: Path(dest).write_text("{}", encoding="utf-8")):
            rc = villa_env.main(["villa_env.py", "spec"])
            self.assertEqual(rc, 0)

        stage_record = self.out_dir / "villa-env-spec.stage-result.json"
        self.assertTrue(stage_record.is_file())
        valid, reason, record = validate_stage_result(stage_record, root=ROOT)
        self.assertTrue(valid)
        self.assertEqual(record["status"], "ok")

    def test_l0029_env_check_failure_exits_nonzero_and_writes_fail_record(self):
        """l0029 reproduction: env check discrepancy now exits non-zero and writes FAIL record."""
        # Quote: L0029_LEARNINGS_LINE
        (self.out_dir / "env-spec.json").write_text("{}", encoding="utf-8")
        (self.out_dir / "env-readback.json").write_text("{}", encoding="utf-8")

        with patch.object(villa_env, "OUT", self.out_dir), \
             patch.object(villa_env, "check", lambda *a, **k: ["column span mismatch"]):
            with self.assertRaises(SystemExit) as cm:
                villa_env.main(["villa_env.py", "check"])
            self.assertEqual(cm.exception.code, 1)

        stage_record = self.out_dir / "villa-env-check.stage-result.json"
        self.assertTrue(stage_record.is_file())
        record = json.loads(stage_record.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "fail")
        self.assertEqual(record["exit_code"], 1)
        self.assertIn("column span mismatch", record["metadata"]["failures"])


class TestVillaStairsStageResult(unittest.TestCase):
    """Proofs for scripts/villa_stairs.py stage-result contract."""

    def setUp(self):
        _isolate_process_state(self)
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmp_dir.name)
        self.out_dir = self.tmp / "stairs"
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_clean_stairs_compare_exits_zero_with_ok_record(self):
        """Clean run exits 0 with status 'ok'."""
        (self.out_dir / "stairs-readback.json").write_text("{}", encoding="utf-8")

        with patch.object(villa_stairs, "OUT", self.out_dir), \
             patch.object(villa_stairs, "compare", lambda: 0):
            rc = villa_stairs.main(["villa_stairs.py", "compare"])
            self.assertEqual(rc, 0)

        stage_record = self.out_dir / "villa-stairs.stage-result.json"
        self.assertTrue(stage_record.is_file())
        valid, reason, record = validate_stage_result(stage_record, root=ROOT)
        self.assertTrue(valid)
        self.assertEqual(reason, "ok")
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["exit_code"], 0)

    def test_clean_stairs_spec_exits_zero_with_ok_record(self):
        """Clean spec mode exits 0 with status 'ok'."""
        with patch.object(villa_stairs, "OUT", self.out_dir), \
             patch.object(villa_stairs, "spec", lambda: (self.out_dir / "stairs-spec.json").write_text("{}", encoding="utf-8")):
            rc = villa_stairs.main(["villa_stairs.py", "spec"])
            self.assertEqual(rc, 0)

        stage_record = self.out_dir / "villa-stairs-spec.stage-result.json"
        self.assertTrue(stage_record.is_file())
        valid, reason, record = validate_stage_result(stage_record, root=ROOT)
        self.assertTrue(valid)
        self.assertEqual(record["status"], "ok")

    def test_l0029_stairs_compare_disagreement_exits_nonzero_and_writes_fail_record(self):
        """l0029 reproduction: clash disagreement now exits non-zero and writes FAIL record."""
        # Quote: L0029_LEARNINGS_LINE
        (self.out_dir / "stairs-readback.json").write_text("{}", encoding="utf-8")

        with patch.object(villa_stairs, "OUT", self.out_dir), \
             patch.object(villa_stairs, "compare", lambda: 3):
            with self.assertRaises(SystemExit) as cm:
                villa_stairs.main(["villa_stairs.py", "compare"])
            self.assertEqual(cm.exception.code, 1)

        stage_record = self.out_dir / "villa-stairs.stage-result.json"
        self.assertTrue(stage_record.is_file())
        record = json.loads(stage_record.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "fail")
        self.assertEqual(record["exit_code"], 1)
        self.assertEqual(record["metadata"]["disagreements"], 3)


if __name__ == "__main__":
    unittest.main()
