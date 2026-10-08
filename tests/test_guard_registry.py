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

import ast
import inspect
import io
from pathlib import Path
import shutil
import sys
import tempfile
import textwrap
import types
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
    verify_tier3_review_steps,
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
        self.assertGreaterEqual(len(steps), 21, "Expected at least 21 registered Tier 3 review steps")

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
        self.assertEqual(report["covered_by_guard_count"], 93)
        self.assertEqual(report["covered_by_review_count"], 21)
        self.assertEqual(report["needs_real_case_count"], 10)
        self.assertEqual(report["uncovered_count"], 93)

        # Check specific registered lessons are in covered_by_guard
        expected_guard_lessons = [
            "l0188-file-named-neufert",
            "l0189-building-construction-il",
            "l0179-model-genuinely-disagree",
            "l0113-signify-served-zip",
            "l0118-signify-s-revit",
            "l0098-photometric-file-describ",
            "l0019-revit-color-channels",
            "l0024-revit-textnote-stores",
            "l0067-first-falsy-zero",
            "l0117-ironpython-read-utf",
            "l0131-windows-file-lock",
            "l0272-tests-test-deliverables",
            "l0466-json-fix-passed",
            # Phase 2 Batch 2 Asset & Intake
            "l0011-template-contains-doors",
            "l0014-real-minotti-sofa",
            "l0075-free-modern-bed",
            "l0496-revit-window-read",
            "l0772-landscape-trees-placed",
            "l0846-asset-stand-s",
            "l0960-top-garden-bench",
            # Phase 2 Batch 2 Photometrics & Lighting
            "l0025-third-party-families",
            "l0123-swapping-4300-lm",
            "l0650-scene-lux-measurement",
            "l0095-lamp-sources-sat",
            "l0096-two-spec-heights",
            "l0119-housing-below-ceiling",
            "l0610-fitting-labelled-wrong",
            # Phase 1 Class C7 Material Appearance Basis
            "l0016-solid-magenta-box",
            "l0028-revit-paint-hue",
            "l0049-extracted-glass-solid",
            "l0062-whole-room-rendered",
            "l0064-pure-red-lamp",
            "l0065-ivory-bedding-rendered",
            "l0083-oak-grain-ran",
            "l0084-dark-bronze-rendered",
            "l0677-stone-wood-read",
            "l0724-codex-pass-removed",
            "l0795-wood-grain-rotated",
            "l0891-artificial-grass-rendere",
            "l0900-island-stair-void",
            "l0910-ensuite-bath-screen",
            # Phase 2 Batch 3 Scene & Geometry Builders
            "l0047-closed-consistently-conn",
            "l0069-duvet-slid-0",
            "l0587-option-spec-listed",
            "l0589-first-open-side",
            "l0686-1-780-zero",
            "l0878-climbing-plant-drawn",
            "l0923-dressing-room-clothes",
            # Phase 2 Batch 4 Geometry, Stairs, Openings, Routes & Readback
            "l0312-stair-access-check",
            "l0310-critic-treated-stair",
            "l0319-check-stair-by",
            "l0504-headroom-measured-from",
            "l0512-way-from-stair",
            "l0557-door-can-run",
            "l0576-square-body-failed",
            "l0531-body-rounded-down",
            "l0591-run-s-modules",
            "l0820-prop-extent-guard",
            "l0834-landscape-change-must",
            "l0695-floating-objects-found",
            "l0713-parents-entrance-closed",
            "l0863-revit-wall-opening",
            # Phase 2 Batch 5 Geometry, Routes, Spec Clearances & Execution Proof
            "l0307-villa-concept-round",
            "l0518-r9-follow-ups",
            "l0536-seating-card-assumed",
            "l0542-stair-flight-counted",
            "l0566-principal-bedroom-window",
            "l0570-pocket-door-gave",
            "l0551-furniture-placed-against",
            "l0017-desk-chair-occupies",
            "l0849-dirty-kitchen-duct",
            "l0606-first-drafts-failed",
            "l0029-script-printing-fail",
            "l0040-three-unchanged-camera",
            # Phase 2 Batch 6 Revit Families, Geometry Critics, Authored Values & Render QA
            "l0042-installed-native-revit",
            "l0200-critic-caught-through",
            "l0209-guards",
            "l0999-v01-interior-draft",
            "l0992-v25-exterior-draft",
            "l1004-later-pass-overwrote",
            "l0555-pinned-doors-re",
            "l0682-forcing-24-mm",
            "l0018-falling-back-comments",
            "l0528-20-mm-grid",
            "l0534-corner-not-side",
            "l0720-codex-fix-cut",
        ]
        for lid in expected_guard_lessons:
            self.assertIn(lid, report["covered_by_guard"], f"Lesson {lid} should be covered by registered guard")

        # Lessons whose local re-implementations were deleted or no production guard exists yet
        deleted_reimplementation_lessons = [
            "l0177-good-texture-poly",
            "l0178-good-model-failed",
            "l0026-blender-ies-azimuth",
            "l0080-lamps-rendered-far",
            "l0090-window-glass-passed",
            "l0656-glass-verified",
            "l0046-fine-extraction-exposed",
        ]
        # l0095, l0096 and l0119 lost their batch-2 re-implementations but are now covered by the
        # production fixture_record check (C5 phase 1), so they are asserted covered above.
        for lid in deleted_reimplementation_lessons:
            self.assertIn(lid, report["uncovered_lessons"], f"Lesson {lid} should be uncovered (no production guard yet)")

        # Check Tier-3 review step lessons (all 21 must be covered)
        expected_review_lessons = [
            "l0027-direct-calculations-omit",
            "l0041-both-negative-bed",
            "l0045-claude-code-s",
            "l0058-five-render-rounds",
            "l0086-curtains-looked-corrugat",
            "l0088-critic-claimed-garden",
            "l0102-colour-cast-could",
            "l0103-open-night-door",
            "l0278-broken-library-diagnosis",
            "l0415-wall-position-assumed",
            "l0486-extension-s-end",
            "l0588-placeholder-size-not",
            "l0601-function-beauty-both",
            "l0645-document-taken-as",
            "l0728-study-windows-inherited",
            "l0738-stair",
            "l0743-view-chooser-s",
            "l0751-automated-critic-s",
            "l0768-specified-tint-must",
            "l0880-bougainvillea-climbers-r",
            "l0967-top-garden-looked",
        ]
        for lid in expected_review_lessons:
            self.assertIn(lid, report["covered_by_review"], f"Lesson {lid} should be covered by review step")

        # Check needs_real_case lessons
        expected_needs_real_case = [
            "l0061-first-window-view",
            "l0078-thresholds-set-synthetic",
            "l0079-blue-lamp-lit",
            "l0081-highlight-priority-meter",
            "l0082-highlight-priority-then",
            "l0100-detail-view-named",
            "l0136-highlights-present-faile",
            "l0072-all-six-props",
            "l0074-nishita-sky-units",
            # Phase 2 Batch 3 Scene & Geometry Builders
            "l0059-no-sunlight-entered",
        ]
        for lid in expected_needs_real_case:
            self.assertIn(lid, report["needs_real_case"], f"Lesson {lid} should be tracked as needs_real_case")

        # Check lesson left uncovered (no guard in code yet)
        self.assertIn("l0101-look-retry-overwrote", report["uncovered_lessons"])

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

    def test_every_tier3_lesson_has_registered_review_step_with_existing_doc_section(self) -> None:
        """Every tier-3 lesson in docs/lessons-audit.md has a registered review step
        whose referenced doc section exists in docs/review-steps.md.
        
        The test reads both files directly, verifies coverage, and asserts all section anchors resolve.
        """
        audit_file = ROOT / "docs/lessons-audit.md"
        review_steps_file = ROOT / "docs/review-steps.md"

        self.assertTrue(audit_file.exists(), f"Audit file not found: {audit_file}")
        self.assertTrue(review_steps_file.exists(), f"Review steps doc file not found: {review_steps_file}")

        # Run verification via registry helper
        result = verify_tier3_review_steps(audit_file=audit_file, review_steps_file=review_steps_file)

        self.assertTrue(result["passed"], f"Tier-3 review verification failed: {result['errors']}")
        self.assertEqual(result["total_tier3"], 21, "Expected exactly 21 Tier 3 lessons in audit")
        self.assertEqual(result["covered_tier3_count"], 21, "Expected all 21 Tier 3 lessons to be covered")
        self.assertEqual(len(result["errors"]), 0)

        # Directly read and check both files independently in this test
        audit_content = audit_file.read_text(encoding="utf-8")
        review_doc_content = review_steps_file.read_text(encoding="utf-8")

        # Parse headings from review_steps_file
        doc_headings = set()
        for line in review_doc_content.splitlines():
            s = line.strip()
            if s.startswith("#"):
                doc_headings.add(s.lstrip("#").strip().lower())

        tier3_ids = [
            "l0027-direct-calculations-omit",
            "l0041-both-negative-bed",
            "l0045-claude-code-s",
            "l0058-five-render-rounds",
            "l0086-curtains-looked-corrugat",
            "l0088-critic-claimed-garden",
            "l0102-colour-cast-could",
            "l0103-open-night-door",
            "l0278-broken-library-diagnosis",
            "l0415-wall-position-assumed",
            "l0486-extension-s-end",
            "l0588-placeholder-size-not",
            "l0601-function-beauty-both",
            "l0645-document-taken-as",
            "l0728-study-windows-inherited",
            "l0738-stair",
            "l0743-view-chooser-s",
            "l0751-automated-critic-s",
            "l0768-specified-tint-must",
            "l0880-bougainvillea-climbers-r",
            "l0967-top-garden-looked",
        ]

        for lid in tier3_ids:
            self.assertIn(lid, audit_content, f"Lesson {lid} missing from docs/lessons-audit.md")
            steps = find_review_steps_for_lesson(lid)
            self.assertGreaterEqual(len(steps), 1, f"Lesson {lid} must have at least one registered review step")
            for step in steps:
                self.assertEqual(step.tier, 3)
                self.assertTrue(step.location, f"Review step {step.name} has empty location")
                self.assertIn("#", step.location, f"Review step {step.name} location must specify section anchor")
                _, _, anchor = step.location.partition("#")
                self.assertTrue(anchor.strip(), f"Review step {step.name} has empty section anchor")
                anchor_words = anchor.replace("-", " ").lower().split()
                matched = any(all(w in h for w in anchor_words) for h in doc_headings)
                self.assertTrue(
                    matched,
                    f"Section anchor {anchor!r} from review step {step.name} did not match any heading in docs/review-steps.md",
                )

    def test_verify_tier3_review_steps_unreadable_inputs_fail_closed(self) -> None:
        """verify_tier3_review_steps raises UnreadableInputError on missing, empty, or unreadable input files."""
        valid_audit = ROOT / "docs/lessons-audit.md"
        valid_review_doc = ROOT / "docs/review-steps.md"

        # 1. Non-existent audit file raises UnreadableInputError (compatible with FileNotFoundError and ValueError)
        missing_audit = self.temp_dir / "missing-audit.md"
        with self.assertRaises(UnreadableInputError):
            verify_tier3_review_steps(audit_file=missing_audit, review_steps_file=valid_review_doc)
        with self.assertRaises(FileNotFoundError):
            verify_tier3_review_steps(audit_file=missing_audit, review_steps_file=valid_review_doc)
        with self.assertRaises(ValueError):
            verify_tier3_review_steps(audit_file=missing_audit, review_steps_file=valid_review_doc)

        # 2. Empty audit file raises UnreadableInputError
        empty_audit = self.temp_dir / "empty-audit.md"
        empty_audit.write_text("", encoding="utf-8")
        with self.assertRaises(UnreadableInputError):
            verify_tier3_review_steps(audit_file=empty_audit, review_steps_file=valid_review_doc)

        # 3. Non-existent review steps doc file raises UnreadableInputError
        missing_doc = self.temp_dir / "missing-review-steps.md"
        with self.assertRaises(UnreadableInputError):
            verify_tier3_review_steps(audit_file=valid_audit, review_steps_file=missing_doc)
        with self.assertRaises(FileNotFoundError):
            verify_tier3_review_steps(audit_file=valid_audit, review_steps_file=missing_doc)
        with self.assertRaises(ValueError):
            verify_tier3_review_steps(audit_file=valid_audit, review_steps_file=missing_doc)

        # 4. Empty review steps doc file raises UnreadableInputError
        empty_doc = self.temp_dir / "empty-review-steps.md"
        empty_doc.write_text("", encoding="utf-8")
        with self.assertRaises(UnreadableInputError):
            verify_tier3_review_steps(audit_file=valid_audit, review_steps_file=empty_doc)

        # 5. Review steps doc missing expected section headings returns failed verification
        broken_doc = self.temp_dir / "broken-review-steps.md"
        broken_doc.write_text("# Document Without Moments\n\nSome text.", encoding="utf-8")
        res = verify_tier3_review_steps(audit_file=valid_audit, review_steps_file=broken_doc)
        self.assertFalse(res["passed"])
        self.assertGreater(len(res["errors"]), 0)
        self.assertTrue(any("not found in" in err for err in res["errors"]))

        # 6. Empty string path inputs raise UnreadableInputError
        with self.assertRaises(UnreadableInputError):
            verify_tier3_review_steps(audit_file="", review_steps_file=valid_review_doc)
        with self.assertRaises(UnreadableInputError):
            verify_tier3_review_steps(audit_file=valid_audit, review_steps_file="")

    def test_phase2_batch1_guards_execution(self) -> None:
        """Every guard added in Phase 2 Batch 1 executes as expected."""
        # 1. Safe I/O & Serialization guards run on real (fires) and clean (quiet)
        batch1_safe_io = [
            "safe_io_color_channels",
            "safe_io_textnote_normalization",
            "safe_io_falsy_zero_lint",
            "safe_io_utf16_bom_decode",
            "safe_io_raw_copy_lint",
            "safe_io_measured_readback_agreement",
            "safe_io_element_id_exact_integer",
        ]
        for name in batch1_safe_io:
            guard = get_guard(name)
            self.assertFalse(guard.needs_real_case, f"{name} should not need real case")
            real_res = guard.run_case("real")
            self.assertTrue(real_res.passed, f"{name} real failed: {real_res.error_message}")
            self.assertTrue(real_res.fired, f"{name} real did not fire")

            clean_res = guard.run_case("clean")
            self.assertTrue(clean_res.passed, f"{name} clean failed: {clean_res.error_message}")
            self.assertFalse(clean_res.fired, f"{name} clean fired unexpectedly")

        # 2. Render QA guards are registered with needs_real_case=True
        batch1_render_qa = [
            "render_qa_window_view_detail",
            "render_qa_threshold_calibration",
            "render_qa_cool_lamplit_cast",
            "render_qa_highlight_clipping",
            "render_qa_exposure_midtones",
            "render_qa_view_subject_framing",
            "render_qa_overcast_highlights",
        ]
        for name in batch1_render_qa:
            guard = get_guard(name)
            self.assertTrue(guard.needs_real_case, f"{name} should have needs_real_case=True")
            real_res = guard.run_case("real")
            self.assertFalse(real_res.passed)
            self.assertFalse(real_res.fired)
            self.assertIn("needs real case", real_res.error_message.lower())

    def test_phase2_batch2_guards_execution(self) -> None:
        """Every guard added in Phase 2 Batch 2 executes as expected."""
        # 1. Active Asset & intake and Photometrics & lighting guards run on real (fires) and clean (quiet)
        batch2_active = [
            "asset_intake_role_vocabulary",
            "asset_intake_bounds_normalisation",
            "asset_intake_contents_and_licence",
            "safe_io_spec_echo_rejection",
            "villa_landscape_tree_extent",
            "villa_landscape_standin_disclosure",
            "villa_landscape_bench_dimensions",
            "luminaires_spec_contradiction_rejection",
            "luminaires_flux_requirement",
            "villa_lighting_beam_clashes",
        ]
        for name in batch2_active:
            guard = get_guard(name)
            self.assertFalse(guard.needs_real_case, f"{name} should not need real case")
            real_res = guard.run_case("real")
            self.assertTrue(real_res.passed, f"{name} real failed: {real_res.error_message}")
            self.assertTrue(real_res.fired, f"{name} real did not fire")

            clean_res = guard.run_case("clean")
            self.assertTrue(clean_res.passed, f"{name} clean failed: {clean_res.error_message}")
            self.assertFalse(clean_res.fired, f"{name} clean fired unexpectedly")

        # 2. Batch 2 guards registered with needs_real_case=True
        batch2_needs_real = [
            "asset_intake_empty_package",
            "lighting_nishita_sky_calibration",
        ]
        for name in batch2_needs_real:
            guard = get_guard(name)
            self.assertTrue(guard.needs_real_case, f"{name} should have needs_real_case=True")
            real_res = guard.run_case("real")
            self.assertFalse(real_res.passed)
            self.assertFalse(real_res.fired)
            self.assertIn("needs real case", real_res.error_message.lower())

    def test_c7_material_appearance_basis_guard_execution(self) -> None:
        """appearance_basis_phase1 executes on real case (fires) and clean case (quiet)."""
        guard = get_guard("appearance_basis_phase1")
        self.assertFalse(guard.needs_real_case, "appearance_basis_phase1 should not need real case")
        real_res = guard.run_case("real")
        self.assertTrue(real_res.passed, f"appearance_basis_phase1 real failed: {real_res.error_message}")
        self.assertTrue(real_res.fired, "appearance_basis_phase1 real did not fire")

        clean_res = guard.run_case("clean")
        self.assertTrue(clean_res.passed, f"appearance_basis_phase1 clean failed: {clean_res.error_message}")
        self.assertFalse(clean_res.fired, "appearance_basis_phase1 clean fired unexpectedly")

    def _get_production_calls(self, fn: Any) -> list[str]:
        """Parses AST of fn and returns all calls to production modules (archpipe.* != guard_registry, or revit/*)."""
        src = textwrap.dedent(inspect.getsource(fn))
        tree = ast.parse(src)
        fn_globals = getattr(fn, "__globals__", {})
        calls: list[str] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            target_func = node.func
            resolved_module = ""
            call_repr = ""

            if isinstance(target_func, ast.Name):
                func_name = target_func.id
                call_repr = func_name
                obj = fn_globals.get(func_name)
                if obj is not None:
                    resolved_module = getattr(obj, "__module__", "")
            elif isinstance(target_func, ast.Attribute):
                chain: list[str] = []
                curr: ast.AST = target_func
                while isinstance(curr, ast.Attribute):
                    chain.append(curr.attr)
                    curr = curr.value
                if isinstance(curr, ast.Name):
                    chain.append(curr.id)
                    chain.reverse()
                    call_repr = ".".join(chain)
                    base_obj = fn_globals.get(chain[0])
                    if base_obj is not None:
                        curr_obj = base_obj
                        for part in chain[1:]:
                            curr_obj = getattr(curr_obj, part, None)
                            if curr_obj is None:
                                break
                        if curr_obj is not None:
                            resolved_module = getattr(curr_obj, "__module__", "")
                            if not resolved_module and isinstance(curr_obj, types.ModuleType):
                                resolved_module = getattr(curr_obj, "__name__", "")
                        elif isinstance(base_obj, types.ModuleType):
                            resolved_module = getattr(base_obj, "__name__", "")

            resolved_module = resolved_module or ""  # some callables report __module__ = None
            is_archpipe_prod = (
                resolved_module.startswith("archpipe.")
                and resolved_module != "archpipe.guard_registry"
                and not resolved_module.endswith(".guard_registry")
            )
            is_revit_prod = resolved_module.startswith("revit.") or resolved_module == "revit"

            if is_archpipe_prod or is_revit_prod:
                calls.append(f"{resolved_module}:{call_repr}")

        return calls

    def _assert_calls_production_module(self, fn: Any) -> list[str]:
        """Asserts that fn calls at least one production module function."""
        calls = self._get_production_calls(fn)
        if not calls:
            raise AssertionError(
                f"Function {getattr(fn, '__name__', str(fn))} does not call any production module "
                f"(archpipe.* != guard_registry, or revit/*)."
            )
        return calls

    def test_meta_guard_guard_registry_functions_call_production_modules(self) -> None:
        """Meta-guard: every guard fn defined in guard_registry must call a production module, not re-implement logic."""
        registry_defined_guards = [
            g for g in all_guards()
            if getattr(g.guard_fn, "__module__", "") in ("archpipe.guard_registry", "src.archpipe.guard_registry")
        ]
        self.assertGreater(len(registry_defined_guards), 0, "Expected registry-defined guard functions")

        for guard in registry_defined_guards:
            calls = self._assert_calls_production_module(guard.guard_fn)
            self.assertGreater(
                len(calls),
                0,
                f"Guard '{guard.name}' has fn defined in guard_registry but does not call any production "
                f"module (archpipe.* != guard_registry, or revit/*). Re-implementations inside "
                f"guard_registry are rejected."
            )

        # Negative test: a function doing only local re-implementation arithmetic must be rejected
        def dummy_reimplementation_check(val: float) -> float:
            threshold = 100.0 * 2.5
            if val > threshold:
                raise ValueError("Too large")
            return val * 1.5

        with self.assertRaises(AssertionError) as ctx:
            self._assert_calls_production_module(dummy_reimplementation_check)
        self.assertIn("does not call any production module", str(ctx.exception))

        # Negative test 2: a function using only standard library (math) must also be rejected
        def dummy_stdlib_only_check(val: float) -> float:
            import math
            return math.sin(val)

        with self.assertRaises(AssertionError) as ctx_stdlib:
            self._assert_calls_production_module(dummy_stdlib_only_check)
        self.assertIn("does not call any production module", str(ctx_stdlib.exception))
    def test_c5_fixture_record_guard_execution(self) -> None:
        """Class C5 fixture record consistency guard executes on real and clean cases."""
        guard = get_guard("fixture_record_consistency")
        self.assertFalse(guard.needs_real_case)
        real_res = guard.run_case("real")
        self.assertTrue(real_res.passed, f"fixture_record_consistency real failed: {real_res.error_message}")
        self.assertTrue(real_res.fired, "fixture_record_consistency real did not fire")

        clean_res = guard.run_case("clean")
        self.assertTrue(clean_res.passed, f"fixture_record_consistency clean failed: {clean_res.error_message}")
        self.assertFalse(clean_res.fired, "fixture_record_consistency clean fired unexpectedly")

    def test_phase2_batch3_scene_and_geometry_guards_execution(self) -> None:
        """Every guard added in Phase 2 Batch 3 executes as expected."""
        # 1. Active scene and geometry builder guards run on real (fires) and clean (quiet)
        batch3_active = [
            "villa_furnish3d_spec_details",
            "villa_furnish3d_stair_glass_boundary",
            "physical_part_solid_winding",
            "villa_render_contract_zero_area_triangles",
            "physical_part_duvet_footprint",
            "physical_part_climber_proxy",
            "physical_part_garment_proxy",
        ]
        for name in batch3_active:
            guard = get_guard(name)
            self.assertFalse(guard.needs_real_case, f"{name} should not need real case")
            real_res = guard.run_case("real")
            self.assertTrue(real_res.passed, f"{name} real failed: {real_res.error_message}")
            self.assertTrue(real_res.fired, f"{name} real did not fire")

            clean_res = guard.run_case("clean")
            self.assertTrue(clean_res.passed, f"{name} clean failed: {clean_res.error_message}")
            self.assertFalse(clean_res.fired, f"{name} clean fired unexpectedly")

        # 2. Batch 3 guards registered with needs_real_case=True
        batch3_needs_real = [
            "render_qa_glass_daylight_transmission",
        ]
        for name in batch3_needs_real:
            guard = get_guard(name)
            self.assertTrue(guard.needs_real_case, f"{name} should have needs_real_case=True")
            real_res = guard.run_case("real")
            self.assertFalse(real_res.passed)
            self.assertFalse(real_res.fired)
            self.assertIn("needs real case", real_res.error_message.lower())

    def test_refactor_silent_deletion_guard_execution(self) -> None:
        """Refactor silent deletion guard executes on real (fires) and clean (quiet) cases."""
        guard = get_guard("refactor_silent_deletion")
        self.assertFalse(guard.needs_real_case)
        real_res = guard.run_case("real")
        self.assertTrue(real_res.passed, f"refactor_silent_deletion real failed: {real_res.error_message}")
        self.assertTrue(real_res.fired, "refactor_silent_deletion real did not fire")

        clean_res = guard.run_case("clean")
        self.assertTrue(clean_res.passed, f"refactor_silent_deletion clean failed: {clean_res.error_message}")
        self.assertFalse(clean_res.fired, "refactor_silent_deletion clean fired unexpectedly")

    def test_phase2_batch4_guards_execution(self) -> None:
        """Every guard added in Phase 2 Batch 4 executes on real (fires) and clean (quiet) cases."""
        batch4_guards = [
            "villa_concept_stair_access",
            "stair_pitch_headroom",
            "villa_route_width_stair_void",
            "villa_furnish_door_wall_clearance",
            "villa_furnish_route_corner_disc",
            "villa_furnish_kitchen_run_modules",
            "villa_landscape_prop_room_extent",
            "villa_landscape_route_obstruction",
            "render_support_unsupported_objects",
            "render_support_blocked_openings",
            "villa_furnish3d_opening_spec_id",
        ]
        self.assertEqual(len(batch4_guards), 11, "Expected exactly 11 guards in Batch 4")

        for name in batch4_guards:
            with self.subTest(guard=name):
                guard = get_guard(name)
                self.assertFalse(guard.needs_real_case, f"{name} should not need real case")
                real_res = guard.run_case("real")
                self.assertTrue(real_res.passed, f"{name} real failed: {real_res.error_message}")
                self.assertTrue(real_res.fired, f"{name} real did not fire")

                clean_res = guard.run_case("clean")
                self.assertTrue(clean_res.passed, f"{name} clean failed: {clean_res.error_message}")
                self.assertFalse(clean_res.fired, f"{name} clean fired unexpectedly")

    def test_phase2_batch5_guards_execution(self) -> None:
        """Every guard added in Phase 2 Batch 5 executes on real (fires) and clean (quiet) cases."""
        batch5_guards = [
            "villa_concept_stair_structure",
            "revit_spec_clearance_problems",
            "villa_furnish_kitchen_work_aisle",
            "villa_furnish_stair_foot_reachable",
            "villa_furnish_principal_window_reachable",
            "villa_furnish_pocket_door_approach",
            "villa_furnish_inside_room_boundary",
            "villa_furnish_bedside_zone_a",
            "revit_spec_wp1_detail_constraints",
            "villa_lighting_grooming_task",
            "stage_result_fail_verdict_rejection",
            "stage_result_stale_input_invalidation",
        ]
        self.assertEqual(len(batch5_guards), 12, "Expected exactly 12 guards in Batch 5")

        for name in batch5_guards:
            with self.subTest(guard=name):
                guard = get_guard(name)
                self.assertFalse(guard.needs_real_case, f"{name} should not need real case")
                real_res = guard.run_case("real")
                self.assertTrue(real_res.passed, f"{name} real failed: {real_res.error_message}")
                self.assertTrue(real_res.fired, f"{name} real did not fire")

                clean_res = guard.run_case("clean")
                self.assertTrue(clean_res.passed, f"{name} clean failed: {clean_res.error_message}")
                self.assertFalse(clean_res.fired, f"{name} clean fired unexpectedly")

    def test_phase2_batch6_guards_execution(self) -> None:
        """Every guard added in Phase 2 Batch 6 executes on real (fires) and clean (quiet) cases."""
        batch6_guards = [
            "rfa_portable_compatibility",
            "villa_concept_reachability_and_links",
            "concept_critic_upper_supported",
            "render_qa_window_brightness",
            "authored_values_override_audit",
            "authored_values_override_existing_field",
            "villa_furnish_room_route_connectivity",
            "villa_furnish_coffee_table_clearance",
        ]
        self.assertEqual(len(batch6_guards), 8, "Expected exactly 8 new guards in Batch 6")

        for name in batch6_guards:
            with self.subTest(guard=name):
                guard = get_guard(name)
                self.assertFalse(guard.needs_real_case, f"{name} should not need real case")
                real_res = guard.run_case("real")
                self.assertTrue(real_res.passed, f"{name} real failed: {real_res.error_message}")
                self.assertTrue(real_res.fired, f"{name} real did not fire")

                clean_res = guard.run_case("clean")
                self.assertTrue(clean_res.passed, f"{name} clean failed: {clean_res.error_message}")
                self.assertFalse(clean_res.fired, f"{name} clean fired unexpectedly")


if __name__ == "__main__":
    unittest.main()



