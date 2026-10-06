"""Tests for atomic stage-result contract, completeness proofs, and fail-closed verdict gating.

Reproduces the class "pipeline result lacks atomic proof" as data:
1. l0029: FAIL printed with exit 0.
2. l0040: Cached job reused after an input change.
3. Partial output set reported complete (missing or 0-byte output).
4. villa-render-stale-scene: Stale scene consumed by the render driver.
Plus quiet cases for each.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from archpipe.stage_result import (
    CodeDriftError,
    FailedStageError,
    IncompleteOutputError,
    StageResultError,
    StaleInputError,
    digest_file,
    enforce_clean_verdict,
    fail_closed_exit,
    report_has_failure,
    validate_stage_result,
    write_stage_result,
)


class StageResultContractTests(unittest.TestCase):
    def test_l0029_fail_verdict_refuses_zero_exit_and_clean_verdict_passes(self):
        """A script printing FAIL but returning zero cannot gate a pipeline (l0029)."""
        # Real failure case 1: Dict report with passed=False and failures list
        bad_report_dict = {
            "stage": "photometry_agreement",
            "passed": False,
            "verdict": "FAIL -- direct-light agreement outside 5%",
            "failures": ["clear-point median 1.0820 outside 5% band"],
            "checks": [{"check": "clear_point_agreement", "passed": False}],
        }
        has_fail, issues = report_has_failure(bad_report_dict)
        self.assertTrue(has_fail)
        self.assertIn("Field 'passed' is False", issues)
        with self.assertRaises(SystemExit) as cm:
            enforce_clean_verdict(bad_report_dict, exit_code=1)
        self.assertEqual(cm.exception.code, 1)

        # Real failure case 2: Log text containing VERDICT: FAIL or FAIL
        bad_report_text = "Comparing 180 points inside room\nVERDICT: FAIL -- direct-light agreement outside 5%"
        has_fail, issues = report_has_failure(bad_report_text)
        self.assertTrue(has_fail)
        with self.assertRaises(SystemExit) as cm:
            fail_closed_exit(bad_report_text, exit_code=1)
        self.assertEqual(cm.exception.code, 1)

        # Real failure case 3: Check failure count (e.g. check_bedroom bad count)
        has_fail, issues = report_has_failure(3)
        self.assertTrue(has_fail)
        with self.assertRaises(SystemExit) as cm:
            enforce_clean_verdict(3, exit_code=2)
        self.assertEqual(cm.exception.code, 2)

        # Quiet case: Clean report exits 0 and never raises
        clean_report_dict = {
            "stage": "photometry_agreement",
            "passed": True,
            "verdict": "PASS -- direct-light median ratio within 5%",
            "failures": [],
            "checks": [{"check": "clear_point_agreement", "passed": True}],
        }
        has_fail, issues = report_has_failure(clean_report_dict)
        self.assertFalse(has_fail)
        self.assertEqual(issues, [])
        exit_code = enforce_clean_verdict(clean_report_dict)
        self.assertEqual(exit_code, 0)

        # Quiet case 2: Zero failure count
        has_fail, issues = report_has_failure(0)
        self.assertFalse(has_fail)
        self.assertEqual(enforce_clean_verdict(0), 0)

    def test_l0040_cached_stage_reused_after_input_change_fails_closed(self):
        """A cached job reused after an input change must fail closed (l0040)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            spec_file = tmp / "spec.yaml"
            spec_file.write_text("room: bedroom\nwidth: 4000\ndepth: 3000\n", encoding="utf-8")

            output_file = tmp / "bedroom-render.json"
            output_file.write_text('{"room": "bedroom", "fixtures": 4}\n', encoding="utf-8")

            stage_record = tmp / "spec-stage.json"

            # Initial stage execution records inputs and outputs
            write_stage_result(
                "spec_stage",
                record_path=stage_record,
                inputs=[spec_file],
                outputs=[output_file],
                root=tmp,
            )

            # Quiet case: When inputs and outputs are untouched, reuse is validated
            valid, reason, record = validate_stage_result(stage_record, root=tmp)
            self.assertTrue(valid)
            self.assertEqual(reason, "ok")

            # Real failure case: An input file is modified after the stage ran
            spec_file.write_text("room: bedroom\nwidth: 4200\ndepth: 3000\n", encoding="utf-8")

            # Consumer validates stage record before reusing outputs
            with self.assertRaises(StaleInputError) as cm:
                validate_stage_result(stage_record, root=tmp)
            self.assertIn("is stale / modified", str(cm.exception))

            # Non-raising validation also reports False and the specific reason
            valid, reason, _ = validate_stage_result(stage_record, root=tmp, raise_on_error=False)
            self.assertFalse(valid)
            self.assertIn("spec.yaml", reason)

    def test_partial_output_set_reported_complete_fails_closed(self):
        """A partial output set (missing or 0 bytes) must fail completeness check."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            inp = tmp / "input.yaml"
            inp.write_text("render: view1\n", encoding="utf-8")

            out1 = tmp / "view1.png"
            out1.write_bytes(b"\x89PNG\r\n\x1a\nfakeimagebytes")
            out2 = tmp / "view1.json"
            out2.write_text('{"view": "view1"}\n', encoding="utf-8")
            out3_missing = tmp / "view1.qa.json"
            # out3_missing is intentionally NOT written

            stage_record = tmp / "render-stage.json"

            # Case A: Missing output file
            rec = write_stage_result(
                "render_driver",
                record_path=stage_record,
                inputs=[inp],
                outputs=[out1, out2, out3_missing],
                expected_outputs=[out1, out2, out3_missing],
                root=tmp,
            )
            self.assertFalse(rec["completeness"]["complete"])
            self.assertIn("view1.qa.json", rec["completeness"]["missing_outputs"])
            self.assertEqual(rec["status"], "fail")
            self.assertEqual(rec["exit_code"], 1)

            with self.assertRaises(IncompleteOutputError) as cm:
                validate_stage_result(stage_record, root=tmp)
            self.assertIn("view1.qa.json", str(cm.exception))

            # Case B: Output exists on disk but is 0 bytes (e.g. broken pipe or interrupted write)
            out3_missing.write_bytes(b"")  # 0 bytes
            rec2 = write_stage_result(
                "render_driver",
                record_path=stage_record,
                inputs=[inp],
                outputs=[out1, out2, out3_missing],
                expected_outputs=[out1, out2, out3_missing],
                root=tmp,
            )
            self.assertFalse(rec2["completeness"]["complete"])
            self.assertIn("view1.qa.json", rec2["completeness"]["empty_outputs"])

            with self.assertRaises(IncompleteOutputError) as cm:
                validate_stage_result(stage_record, root=tmp)
            self.assertIn("empty", str(cm.exception).lower())

            # Quiet case: When all outputs are present and non-empty, completeness passes
            out3_missing.write_text('{"passed": true}\n', encoding="utf-8")
            rec3 = write_stage_result(
                "render_driver",
                record_path=stage_record,
                inputs=[inp],
                outputs=[out1, out2, out3_missing],
                expected_outputs=[out1, out2, out3_missing],
                root=tmp,
            )
            self.assertTrue(rec3["completeness"]["complete"])
            self.assertEqual(rec3["status"], "ok")
            valid, reason, _ = validate_stage_result(stage_record, root=tmp)
            self.assertTrue(valid)
            self.assertEqual(reason, "ok")

    def test_stale_scene_consumed_by_render_fails_closed(self):
        """Render driver consuming an old scene.json must fail closed (villa-render-stale-scene)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            source_py = tmp / "villa_render_source.py"
            source_py.write_text("# Scene generator version 1\n", encoding="utf-8")

            scene_json = tmp / "scene.json"
            scene_json.write_text('{"schema": "villa-render/1", "views": ["v1"]}\n', encoding="utf-8")

            scene_stage_record = tmp / "scene.stage-result.json"

            # Stage 1: Scene export runs from source_py (V1)
            write_stage_result(
                "scene_export",
                record_path=scene_stage_record,
                inputs=[source_py],
                outputs=[scene_json],
                root=tmp,
            )

            # Quiet case: Render stage consumes fresh scene
            valid, reason, _ = validate_stage_result(
                scene_stage_record,
                root=tmp,
                current_inputs=[source_py],
            )
            self.assertTrue(valid)

            # Failure injection: Source changes (e.g. wall or finish edited in code/spec)
            source_py.write_text("# Scene generator version 2 with wall shift\n", encoding="utf-8")

            # Render stage validates the scene stage result before starting render
            with self.assertRaises(StaleInputError) as cm:
                validate_stage_result(
                    scene_stage_record,
                    root=tmp,
                    current_inputs=[source_py],
                )
            self.assertIn("stale / modified", str(cm.exception))

    def test_tampered_output_fails_closed(self):
        """Modifying an output file after stage completion invalidates the stage."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            inp = tmp / "in.txt"
            inp.write_text("data\n", encoding="utf-8")
            out = tmp / "out.txt"
            out.write_text("initial output\n", encoding="utf-8")
            rec = tmp / "stage.json"

            write_stage_result("test_stage", record_path=rec, inputs=[inp], outputs=[out], root=tmp)
            self.assertTrue(validate_stage_result(rec, root=tmp)[0])

            # Tamper with output
            out.write_text("tampered output\n", encoding="utf-8")

            with self.assertRaises(IncompleteOutputError) as cm:
                validate_stage_result(rec, root=tmp)
            self.assertIn("modified on disk", str(cm.exception))

    def test_failed_exit_code_stage_refuses_consumption(self):
        """A stage that completed with exit_code != 0 cannot be treated as valid output."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            inp = tmp / "in.txt"
            inp.write_text("data\n", encoding="utf-8")
            out = tmp / "partial_out.txt"
            out.write_text("partial data\n", encoding="utf-8")
            rec = tmp / "failed_stage.json"

            write_stage_result(
                "failing_stage",
                record_path=rec,
                inputs=[inp],
                outputs=[out],
                exit_code=1,
                status="fail",
                root=tmp,
            )

            with self.assertRaises(FailedStageError) as cm:
                validate_stage_result(rec, root=tmp)
            self.assertIn("failed with exit code 1", str(cm.exception))

    def test_self_referential_record_path_filtered_and_pure_check_stage(self):
        """Passing record_path in outputs is filtered out to avoid hash cycle, and pure check passes."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            inp = tmp / "spec.yaml"
            inp.write_text("setting: true\n", encoding="utf-8")
            rec = tmp / "check.stage-result.json"

            # Stage where outputs contains rec (or outputs is just [rec])
            record = write_stage_result(
                "check_stage",
                record_path=rec,
                inputs=[inp],
                outputs=[rec],
                exit_code=0,
                root=tmp,
            )
            self.assertTrue(record["completeness"]["complete"])
            self.assertEqual(record["outputs"], {})
            self.assertEqual(record["status"], "ok")
            valid, reason, _ = validate_stage_result(rec, root=tmp)
            self.assertTrue(valid)
            self.assertEqual(reason, "ok")


if __name__ == "__main__":
    unittest.main()
