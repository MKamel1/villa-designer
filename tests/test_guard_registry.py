"""Tests for archpipe.guard_registry: registered guards runner, review steps, and coverage auditor.

Validates that:
1. Every registered guard runs on both cases (fires on real, stays quiet on clean).
2. Guards without a frozen incident case are explicitly tracked as 'needs real case'.
3. Tier 3 lessons register named review steps (with text and location).
4. Coverage audit correctly reads docs/lessons-audit.md and reports coverage.
5. Unreadable inputs raise UnreadableInputError across all modes, never treated as 'no guard' or 'NONE'.

Quick Test:
    python -m unittest tests/test_guard_registry.py

Example Usage:
    >>> import unittest
    >>> from tests.test_guard_registry import TestGuardRegistry
    >>> suite = unittest.TestLoader().loadTestsFromTestCase(TestGuardRegistry)
    >>> result = unittest.TextTestRunner().run(suite)
    >>> result.wasSuccessful()
    True
"""
from __future__ import annotations

import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from archpipe.evidence import EvidenceStatus
from archpipe.guard_registry import (
    GuardCase,
    RegisteredGuard,
    RegisteredReviewStep,
    UnreadableInputError,
    all_guards,
    all_review_steps,
    audit_lesson_coverage,
    case,
    clear_registry,
    coverage_report,
    find_guards_for_lesson,
    find_review_steps_for_lesson,
    format_coverage_report,
    get_guard,
    get_review_step,
    register,
    register_guard,
    register_review_step,
    report_uncovered_lessons,
)


class TestGuardRegistry(unittest.TestCase):
    """Test suite for guard and review step registry and coverage auditing."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.gettempdir()) / ("archpipe-reg-test-" + uuid.uuid4().hex)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_registered_guards_run_on_both_cases(self) -> None:
        """Enumerate all registered guards with real cases and run both cases.
        
        Must fire on the real failing case and stay quiet on the clean case.
        """
        guards = [g for g in all_guards() if not g.needs_real_case]
        self.assertGreaterEqual(len(guards), 6, "Expected at least 6 registered guards with real cases")

        for guard in guards:
            with self.subTest(guard=guard.name, stage="real"):
                real_res = guard.run_case("real")
                self.assertTrue(
                    real_res.passed,
                    f"Guard {guard.name} failed on real case: {real_res.error_message}",
                )
                self.assertTrue(
                    real_res.fired,
                    f"Guard {guard.name} did not fire on real case",
                )

            with self.subTest(guard=guard.name, stage="clean"):
                clean_res = guard.run_case("clean")
                self.assertTrue(
                    clean_res.passed,
                    f"Guard {guard.name} failed on clean case: {clean_res.error_message}",
                )
                self.assertFalse(
                    clean_res.fired,
                    f"Guard {guard.name} fired unexpectedly on clean case",
                )

    def test_needs_real_case_guards_are_tracked_without_invented_fixtures(self) -> None:
        """Guards without a frozen incident case must be listed as 'needs real case'."""
        needs_cases = [g for g in all_guards() if g.needs_real_case]
        self.assertGreaterEqual(len(needs_cases), 1, "Expected at least one guard tracked as needs real case")

        for guard in needs_cases:
            self.assertTrue(guard.needs_real_case)
            real_res = guard.run_case("real")
            self.assertFalse(real_res.passed)
            self.assertIn("needs real case", real_res.error_message.lower())

    def test_tier3_review_steps_are_registered_with_text_and_location(self) -> None:
        """Tier 3 lessons register named review steps with description and location."""
        steps = all_review_steps()
        self.assertGreaterEqual(len(steps), 3, "Expected at least 3 registered Tier 3 review steps")

        for step in steps:
            self.assertEqual(step.tier, 3)
            self.assertTrue(step.lesson_ids, f"Review step {step.name} missing lesson IDs")
            self.assertTrue(step.text.strip(), f"Review step {step.name} has empty text")
            self.assertTrue(step.location.strip(), f"Review step {step.name} has empty location")
            self.assertTrue(step.reviewer.strip(), f"Review step {step.name} has empty reviewer")

    def test_coverage_audit_parses_real_lessons_audit_md(self) -> None:
        """Audit coverage against real docs/lessons-audit.md.
        
        Verifies all 217 lessons are parsed, with zero parsing errors,
        and coverage properly mapped.
        """
        audit_path = ROOT / "docs/lessons-audit.md"
        report = audit_lesson_coverage(audit_path)

        self.assertEqual(report["errors"], [], f"Real audit file should have zero errors: {report['errors']}")
        self.assertEqual(report["total_lessons"], 217, "Expected 217 lessons in docs/lessons-audit.md inventory")
        self.assertGreaterEqual(report["covered_by_guard_count"], 6)
        self.assertGreaterEqual(report["covered_by_review_count"], 3)
        self.assertGreaterEqual(report["needs_real_case_count"], 1)
        self.assertGreater(report["uncovered_count"], 0)

        # Check specific registered lessons are in covered_by_guard
        expected_guard_lessons = [
            "l0188-file-named-neufert",
            "l0189-building-construction-il",
            "l0179-model-genuinely-disagree",
            "l0113-signify-served-zip",
            "l0118-signify-s-revit",
            "l0098-photometric-file-describ",
        ]
        for lid in expected_guard_lessons:
            self.assertIn(lid, report["covered_by_guard"], f"Lesson {lid} should be covered by registered guard")

        # Check Tier-3 review step lessons
        expected_review_lessons = [
            "l0027-direct-calculations-omit",
            "l0041-both-negative-bed",
            "l0058-five-render-rounds",
        ]
        for lid in expected_review_lessons:
            self.assertIn(lid, report["covered_by_review"], f"Lesson {lid} should be covered by review step")

        # Check needs_real_case
        self.assertIn("l0061-first-window-view", report["needs_real_case"])

    def test_coverage_audit_reports_unreadable_inputs_as_errors_never_no_guard(self) -> None:
        """Unreadable or missing input files must raise UnreadableInputError, never reported as 'no guard' / 'NONE'."""
        # 1. Non-existent file raises UnreadableInputError in all modes (compatible with FileNotFoundError and ValueError)
        non_existent = self.temp_dir / "missing-lessons-audit.md"
        with self.assertRaises(UnreadableInputError):
            audit_lesson_coverage(non_existent)
        with self.assertRaises(FileNotFoundError):
            audit_lesson_coverage(non_existent)
        with self.assertRaises(ValueError):
            audit_lesson_coverage(non_existent)

        # 2. Empty file raises UnreadableInputError in all modes (compatible with ValueError and OSError)
        empty_file = self.temp_dir / "empty-audit.md"
        empty_file.write_text("", encoding="utf-8")
        with self.assertRaises(UnreadableInputError):
            audit_lesson_coverage(empty_file)
        with self.assertRaises(ValueError):
            audit_lesson_coverage(empty_file)

        # 3. Malformed table row (missing columns)
        malformed_file = self.temp_dir / "malformed-audit.md"
        malformed_content = """# Lessons audit
## Lesson inventory

| ID | One-line lesson | General root class | Tier | Current enforcement | Proposed control | Generalisation proof |
|---|---|---|---:|---|---|---|
| l9991-broken-row | only two columns |
| l9992-bad-tier | bad tier format | root | not_an_int | NONE | control | proof |
"""
        malformed_file.write_text(malformed_content, encoding="utf-8")
        rep_malformed = audit_lesson_coverage(malformed_file)
        self.assertGreaterEqual(len(rep_malformed["errors"]), 2)
        self.assertTrue(any("Unreadable table row" in err for err in rep_malformed["errors"]))
        self.assertTrue(any("Unreadable tier" in err for err in rep_malformed["errors"]))
        # Malformed entries are never admitted as valid uncovered lessons
        self.assertEqual(rep_malformed["total_lessons"], 0)
        self.assertEqual(rep_malformed["uncovered_count"], 0)
        with self.assertRaises(UnreadableInputError):
            report_uncovered_lessons(malformed_file)

    def test_custom_decorator_registration(self) -> None:
        """Test decorator registration with real and clean cases."""
        @register_guard(
            name="custom_test_boundary_guard",
            lesson_ids=("l9999-custom",),
            real_case=case(-10),
            clean_case=case(10),
            expected_real=ValueError,
            expected_clean=None,
            description="Boundary guard testing decorator registration",
        )
        def custom_guard(val: int) -> int:
            if val < 0:
                raise ValueError("Value cannot be negative")
            return val

        guard = get_guard("custom_test_boundary_guard")
        self.assertEqual(guard.name, "custom_test_boundary_guard")
        real_res = guard.run_case("real")
        self.assertTrue(real_res.passed)
        self.assertTrue(real_res.fired)

        clean_res = guard.run_case("clean")
        self.assertTrue(clean_res.passed)
        self.assertFalse(clean_res.fired)

    def test_coverage_reporting_functions(self) -> None:
        """Test report_uncovered_lessons and format_coverage_report."""
        uncovered = report_uncovered_lessons()
        self.assertIsInstance(uncovered, list)
        self.assertGreater(len(uncovered), 0)
        # Each item is a lesson dict
        first = uncovered[0]
        self.assertIn("id", first)
        self.assertIn("tier", first)
        self.assertIn("root_class", first)

        text_report = format_coverage_report()
        self.assertIn("Lesson Guard & Review Coverage Report", text_report)
        self.assertIn("Total Lessons:", text_report)
        self.assertIn("Covered by Guard:", text_report)

        # On unreadable inputs, report_uncovered_lessons raises UnreadableInputError in all modes
        bad_file = self.temp_dir / "non-existent.md"
        with self.assertRaises(UnreadableInputError):
            report_uncovered_lessons(bad_file)
        with self.assertRaises(FileNotFoundError):
            report_uncovered_lessons(bad_file)
        with self.assertRaises(ValueError):
            report_uncovered_lessons(bad_file)

        # format_coverage_report on bad file starts with the error and contains no counts
        bad_text_rep = format_coverage_report(bad_file)
        first_line = bad_text_rep.splitlines()[0]
        self.assertTrue(first_line.startswith("ERROR:"), f"First line must state error: {first_line}")
        self.assertIn("ERRORS ENCOUNTERED", bad_text_rep)
        self.assertNotIn("Total Lessons:", bad_text_rep)
        self.assertNotIn("Covered by Guard:", bad_text_rep)
        self.assertNotIn("Covered by Review Step:", bad_text_rep)
        self.assertNotIn("Needs Real Case:", bad_text_rep)
        self.assertNotIn("Uncovered:", bad_text_rep)
        self.assertNotIn("Coverage:", bad_text_rep)

    def test_missing_identifier_inputs_fail_closed(self) -> None:
        """Missing or empty inputs to lookup and registration functions must raise UnreadableInputError."""
        with self.assertRaises(UnreadableInputError):
            find_guards_for_lesson("")
        with self.assertRaises(UnreadableInputError):
            find_guards_for_lesson("   ")
        with self.assertRaises(UnreadableInputError):
            find_review_steps_for_lesson("")
        with self.assertRaises(UnreadableInputError):
            find_review_steps_for_lesson("   ")
        with self.assertRaises(UnreadableInputError):
            register_review_step(name="", lesson_ids=("l0001",), text="text", location="loc")
        with self.assertRaises(UnreadableInputError):
            register_review_step(name="step", lesson_ids=(), text="text", location="loc")


if __name__ == "__main__":
    unittest.main()
