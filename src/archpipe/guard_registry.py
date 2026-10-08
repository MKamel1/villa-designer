"""Lesson Guard and Review Step Registry.

Provides a registration mechanism, execution runner, and coverage auditor
for defect guards and review steps mapped to lessons from docs/lessons-audit.md
and docs/LEARNINGS.md.

Hierarchy of controls:
- Tier 1: Prevent by construction.
- Tier 2: Detect early and fail closed (registered guard with real failing case
  and clean case).
- Tier 3: Human judgement or client intent (registered review step with text
  and where it lives).

Quick Test:
    python -c "from archpipe.guard_registry import all_guards; print(len(all_guards()))"

Example Usage:
    >>> from archpipe.guard_registry import register_guard, case, all_guards
    >>> @register_guard(
    ...     name="example_guard",
    ...     lesson_ids=("l0999",),
    ...     real_case=case(bad=True),
    ...     clean_case=case(bad=False),
    ...     expected_real=ValueError,
    ...     expected_clean=None,
    ... )
    ... def my_guard(bad: bool):
    ...     if bad:
    ...         raise ValueError("Disallowed value")
    >>> len(all_guards()) >= 1
    True
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
import functools
import io
import json
import math
from pathlib import Path
import re
import tempfile
from typing import Any, Callable, Iterable
import uuid
import zipfile

from PIL import Image

from archpipe.evidence import (
    EvidenceError,
    EvidenceRecord,
    EvidenceStatus,
    GeometryDisagreementError,
    PageMismatchError,
    ScopeWideningError,
    SourceRef,
    assert_geometry_matches_metadata,
    assert_page_agreement,
    check_book_edition,
    check_render_vs_design,
    check_shared_model,
    combine,
)
from archpipe.external_claims import (
    CompletenessShortfallError,
    UnsafeDestinationError,
    check_cct_and_watts_agreement,
    check_photometry_fitting_agreement,
    ingest_bytes,
)
from archpipe import (
    asset_intake,
    evidence,
    execution_context,
    external_claims,
    material_basis,
    refactor_audit,
    render_qa,
    rfa,
    safe_io,
    stage_result,
    villa_render_contract,
)
from archpipe.execution_context import ContextError
from archpipe.concept import (
    authored_guard,
    authored_values,
    critic,
    mounting,
    physical_part,
    render_support,
    render_views,
    revit_spec,
    stairs,
    villa,
    villa_furnish,
    villa_furnish3d,
    villa_landscape,
    villa_lighting,
    villa_parking,
    villa_r11,
)
from archpipe.luminaires import install
from archpipe.fixture_record import (
    FixtureConsistencyError,
    check_fixture_record_consistency,
)
from archpipe.units_guard import (
    UnitsConversionError,
    check_units_guard,
)

__all__ = [
    "EvidenceStatus",
    "FixtureConsistencyError",
    "GuardCase",
    "GuardExecutionResult",
    "RegisteredGuard",
    "RegisteredReviewStep",
    "UnreadableInputError",
    "all_guards",
    "all_review_steps",
    "audit_lesson_coverage",
    "case",
    "check_asset_bounds_normalisation",
    "check_asset_contents_and_licence",
    "check_asset_role",
    "check_authored_guard_unexplained_changes",
    "check_authored_values_override_audit",
    "check_authored_values_override_existing_field",
    "check_concept_critic_upper_supported",
    "check_element_id_exact_integer",
    "check_evidence_composition_verified",
    "check_evidence_door_swing_certification",
    "check_evidence_render_vs_design",
    "check_evidence_scope_promotion",
    "check_evidence_shared_model",
    "check_execution_context_absolute_path",
    "check_execution_context_dependencies",
    "check_execution_context_fresh_artifact_check",
    "check_execution_context_noninteractive_stdin",
    "check_execution_context_python_interpreter_path",
    "check_execution_context_roles",
    "check_execution_context_writable_directory",
    "check_external_claims_manifest_completeness",
    "check_external_claims_safe_destination",
    "check_external_claims_search_relevance",
    "check_falsy_zero_lint",
    "check_fixture_photometry_ownership",
    "check_landscape_bench_dimensions",
    "check_landscape_standin_disclosure",
    "check_landscape_tree_extent",
    "check_lighting_beam_clashes",
    "check_luminaire_flux_requirement",
    "check_fixture_record_consistency",
    "check_material_appearance_basis",
    "check_mounting_handrail_finished_face",
    "check_physical_part_climber_proxy",
    "check_physical_part_duvet_footprint",
    "check_physical_part_garment_proxy",
    "check_physical_part_solid_winding",
    "check_raw_copy_lint",
    "check_refactor_silent_deletion",
    "check_render_contract_scene_geometry",
    "check_render_qa_photometry_bound",
    "check_render_qa_verticals_level",
    "check_render_qa_window_brightness",
    "check_render_support_blocked_openings",
    "check_render_support_unsupported",
    "check_render_views_subject_framing",
    "check_render_views_subject_presence",
    "check_revit_spec_clearance_problems",
    "check_revit_spec_wp1_detail_constraints",
    "check_rfa_portable_compatibility",
    "check_round2_spec_details",
    "check_round2_stair_glass_boundary",
    "check_stage_result_fail_verdict_rejection",
    "check_stage_result_failed_exit_refusal",
    "check_stage_result_output_integrity",
    "check_stage_result_stale_input_invalidation",
    "check_stage_result_stale_upstream_source",
    "check_stair_pitch_headroom",
    "check_utf16_or_utf8_json",
    "check_villa_concept_reachability_and_links",
    "check_villa_concept_stair_access",
    "check_villa_concept_stair_structure",
    "check_villa_furnish3d_opening_spec_id",
    "check_villa_furnish_bedside_zone_a",
    "check_villa_furnish_coffee_table_clearance",
    "check_villa_furnish_column_clearance",
    "check_villa_furnish_door_wall_clearance",
    "check_villa_furnish_inside_room_boundary",
    "check_villa_furnish_kitchen_run_modules",
    "check_villa_furnish_kitchen_work_aisle",
    "check_villa_furnish_pocket_door_approach",
    "check_villa_furnish_principal_window_reachable",
    "check_villa_furnish_room_route_connectivity",
    "check_villa_furnish_route_corner_disc",
    "check_villa_furnish_stair_foot_reachable",
    "check_villa_furnish_under_stair_storage_profile",
    "check_villa_landscape_camera_canopy_clearance",
    "check_villa_landscape_plant_spacing",
    "check_villa_landscape_prop_room_extent",
    "check_villa_landscape_route_obstruction",
    "check_villa_lighting_grooming_task",
    "check_villa_lighting_prep_task",
    "check_villa_lighting_windowless_store_target",
    "check_villa_route_width_stair_void",
    "clear_registry",
    "coverage_report",
    "find_guards_for_lesson",
    "find_review_steps_for_lesson",
    "format_coverage_report",
    "get_guard",
    "get_review_step",
    "register",
    "register_guard",
    "register_review_step",
    "report_uncovered_lessons",
    "safe_io_spec_echo_rejection",
    "verify_tier3_review_steps",
]


ROOT = Path(__file__).resolve().parents[2]


class UnreadableInputError(FileNotFoundError, ValueError):
    """Raised when an audit input file or identifier is missing, unreadable, or invalid.
    
    Subclasses both FileNotFoundError (which is an OSError) and ValueError so callers
    handling either exception type remain compatible.
    """
    pass


@dataclass(frozen=True)
class GuardCase:
    """Fixture container for real failing or clean test inputs."""
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] = field(default_factory=dict)
    description: str = ""


def case(*args: Any, **kwargs: Any) -> GuardCase:
    """Convenience factory creating a GuardCase."""
    return GuardCase(args=args, kwargs=kwargs)


def _normalize_case(c: Any) -> GuardCase:
    if isinstance(c, GuardCase):
        return c
    if isinstance(c, dict) and ("args" in c or "kwargs" in c):
        return GuardCase(args=tuple(c.get("args", ())), kwargs=dict(c.get("kwargs", {})))
    if c is None:
        return GuardCase(args=())
    return GuardCase(args=(c,))


@dataclass(frozen=True)
class GuardExecutionResult:
    """Result of running a guard against a test fixture."""
    guard_name: str
    case_type: str
    passed: bool
    fired: bool
    error_message: str
    detail: Any = None


def _evaluate_outcome(result: Any, exc: Exception | None, expected: Any) -> tuple[bool, str]:
    """Evaluate whether actual execution outcome matches expected outcome.
    
    Returns (matched, error_description).
    """
    if exc is not None:
        if isinstance(expected, type) and issubclass(expected, BaseException):
            if isinstance(exc, expected):
                return True, ""
            return False, f"Expected exception {expected.__name__}, got {type(exc).__name__}: {exc}"
        if isinstance(expected, tuple) and all(isinstance(t, type) and issubclass(t, BaseException) for t in expected):
            if isinstance(exc, expected):
                return True, ""
            names = tuple(t.__name__ for t in expected)
            return False, f"Expected one of exceptions {names}, got {type(exc).__name__}: {exc}"
        if expected == "raises":
            return True, ""
        return False, f"Unexpected exception raised: {type(exc).__name__}: {exc}"

    # No exception was raised
    if isinstance(expected, type) and issubclass(expected, BaseException):
        return False, f"Expected exception {expected.__name__}, but guard returned without raising: {result!r}"
    if isinstance(expected, tuple) and all(isinstance(t, type) and issubclass(t, BaseException) for t in expected):
        names = tuple(t.__name__ for t in expected)
        return False, f"Expected one of exceptions {names}, but guard returned without raising: {result!r}"
    if expected == "raises":
        return False, f"Expected guard to raise, but returned without raising: {result!r}"

    if expected is None or expected in ("quiet", "pass"):
        if isinstance(result, EvidenceRecord):
            if result.status == EvidenceStatus.UNVERIFIED:
                return False, f"EvidenceRecord stayed UNVERIFIED on clean case: {result.reasons}"
        elif isinstance(result, dict):
            if result.get("status") in ("FAIL", "UNVERIFIED"):
                return False, f"Dict result status was {result.get('status')!r} on clean case"
            if result.get("matches") is False:
                return False, "Dict result matches is False on clean case"
            if result.get("flagged") is True:
                return False, "Dict result flagged is True on clean case"
        elif result is False:
            return False, "Guard returned False on clean case"
        return True, ""

    if isinstance(expected, EvidenceStatus):
        if isinstance(result, EvidenceRecord):
            if result.status == expected:
                return True, ""
            return False, f"Expected EvidenceStatus {expected.value}, got {result.status.value}"
        if isinstance(result, dict) and result.get("status") == expected:
            return True, ""
        if result == expected:
            return True, ""
        return False, f"Expected EvidenceStatus {expected.value}, got {result!r}"

    if isinstance(expected, dict):
        if not isinstance(result, dict):
            return False, f"Expected dict result, got {type(result).__name__}: {result!r}"
        for k, v in expected.items():
            if result.get(k) != v:
                return False, f"Key {k!r}: expected {v!r}, got {result.get(k)!r}"
        return True, ""

    if callable(expected):
        try:
            ok = bool(expected(result))
            return ok, ("" if ok else f"Expected predicate returned False for result: {result!r}")
        except Exception as pred_exc:
            return False, f"Expected predicate raised exception: {pred_exc}"

    if result == expected:
        return True, ""

    return False, f"Expected {expected!r}, got {result!r}"


@dataclass
class RegisteredGuard:
    """A registered verification guard tied to one or more lesson IDs."""
    name: str
    lesson_ids: tuple[str, ...]
    guard_fn: Callable[..., Any]
    real_case: Any
    clean_case: Any
    expected_real: Any
    expected_clean: Any
    tier: int = 2
    description: str = ""
    notes: str = ""
    needs_real_case: bool = False

    def run_case(self, case_type: str = "real") -> GuardExecutionResult:
        """Run guard on either 'real' (failing) or 'clean' (quiet) case."""
        if case_type == "real":
            target_case = self.real_case
            expected = self.expected_real
            is_real = True
        elif case_type == "clean":
            target_case = self.clean_case
            expected = self.expected_clean
            is_real = False
        else:
            raise ValueError(f"Unknown case_type {case_type!r}; must be 'real' or 'clean'")

        if self.needs_real_case and is_real:
            return GuardExecutionResult(
                guard_name=self.name,
                case_type=case_type,
                passed=False,
                fired=False,
                error_message="Guard has no frozen real case registered ('needs real case')",
                detail=None,
            )

        norm = _normalize_case(target_case)
        exc: Exception | None = None
        result: Any = None
        temp_files: list[Path] = []
        try:
            args = list(norm.args)
            kwargs = dict(norm.kwargs)

            # Case setup: write frozen bytes to a temporary file when guard expects a file path
            if self.name == "safe_io_utf16_bom_decode" or self.guard_fn in (check_utf16_or_utf8_json, safe_io.load_json):
                if args and isinstance(args[0], (bytes, bytearray)):
                    tf = Path(tempfile.gettempdir()) / f"guard_utf16_{uuid.uuid4().hex}.json"
                    tf.write_bytes(bytes(args[0]))
                    temp_files.append(tf)
                    args[0] = tf

            result = self.guard_fn(*args, **kwargs)
        except Exception as e:
            exc = e
        finally:
            for tf in temp_files:
                try:
                    if tf.exists():
                        tf.unlink()
                except OSError:
                    pass

        passed, msg = _evaluate_outcome(result, exc, expected)

        # Fired indicator: exception raised or failed status returned
        fired = (
            (exc is not None)
            or (isinstance(result, EvidenceRecord) and result.status == EvidenceStatus.UNVERIFIED)
            or (
                isinstance(result, dict)
                and (
                    result.get("status") in ("FAIL", "UNVERIFIED")
                    or result.get("matches") is False
                    or result.get("flagged") is True
                )
            )
            or (result is False)
            or (result == EvidenceStatus.UNVERIFIED)
            or (result == "FAIL")
        )

        return GuardExecutionResult(
            guard_name=self.name,
            case_type=case_type,
            passed=passed,
            fired=fired,
            error_message=msg,
            detail=result if exc is None else exc,
        )

    def run(self) -> tuple[GuardExecutionResult, GuardExecutionResult]:
        """Run guard on both real and clean cases."""
        real_res = self.run_case("real")
        clean_res = self.run_case("clean")
        return real_res, clean_res


@dataclass(frozen=True)
class RegisteredReviewStep:
    """A registered Tier 3 review step for human judgement or intent."""
    name: str
    lesson_ids: tuple[str, ...]
    text: str
    location: str
    reviewer: str = "lead"
    tier: int = 3
    notes: str = ""


# Global registries
_GUARDS: dict[str, RegisteredGuard] = {}
_REVIEW_STEPS: dict[str, RegisteredReviewStep] = {}


def register_guard(
    fn: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    lesson_ids: str | Iterable[str] = (),
    real_case: Any = None,
    clean_case: Any = None,
    expected_real: Any = None,
    expected_clean: Any = None,
    tier: int = 2,
    description: str = "",
    notes: str = "",
    needs_real_case: bool = False,
) -> Any:
    """Register a guard function protecting specified lesson IDs.
    
    Can be used as a decorator or a direct registration function.
    """
    if isinstance(lesson_ids, str):
        l_ids = (lesson_ids,)
    else:
        l_ids = tuple(lesson_ids)

    if not l_ids or all(not str(lid).strip() for lid in l_ids):
        raise UnreadableInputError("Guard must specify at least one valid non-empty lesson ID")

    # If no real_case provided and not explicitly marked, flag as needing real case
    if real_case is None and not needs_real_case:
        needs_real_case = True

    def decorator(target_fn: Callable[..., Any]) -> Callable[..., Any]:
        guard_name = name or getattr(target_fn, "__name__", "unnamed_guard")
        guard = RegisteredGuard(
            name=guard_name,
            lesson_ids=l_ids,
            guard_fn=target_fn,
            real_case=real_case,
            clean_case=clean_case,
            expected_real=expected_real,
            expected_clean=expected_clean,
            tier=tier,
            description=description,
            notes=notes,
            needs_real_case=needs_real_case,
        )
        _GUARDS[guard_name] = guard
        return target_fn

    if fn is not None:
        return decorator(fn)
    return decorator


register = register_guard


def register_review_step(
    name: str,
    lesson_ids: str | Iterable[str],
    text: str,
    location: str,
    reviewer: str = "lead",
    notes: str = "",
) -> RegisteredReviewStep:
    """Register a Tier 3 named review step with its location and description."""
    if not name or not str(name).strip():
        raise UnreadableInputError("Review step requires non-empty name")
    if isinstance(lesson_ids, str):
        l_ids = (lesson_ids,)
    else:
        l_ids = tuple(lesson_ids)

    if not l_ids or all(not str(lid).strip() for lid in l_ids):
        raise UnreadableInputError("Review step must specify at least one valid non-empty lesson ID")

    if not text or not str(text).strip():
        raise UnreadableInputError("Review step requires non-empty description text")
    if not location or not str(location).strip():
        raise UnreadableInputError("Review step requires non-empty location")

    step = RegisteredReviewStep(
        name=name,
        lesson_ids=l_ids,
        text=text,
        location=location,
        reviewer=reviewer,
        notes=notes,
    )
    _REVIEW_STEPS[name] = step
    return step


def get_guard(name: str) -> RegisteredGuard:
    """Retrieve a registered guard by name."""
    if not name or not str(name).strip():
        raise UnreadableInputError("Guard name cannot be empty or missing")
    if name not in _GUARDS:
        raise KeyError(f"No guard registered with name {name!r}")
    return _GUARDS[name]


def get_review_step(name: str) -> RegisteredReviewStep:
    """Retrieve a registered review step by name."""
    if not name or not str(name).strip():
        raise UnreadableInputError("Review step name cannot be empty or missing")
    if name not in _REVIEW_STEPS:
        raise KeyError(f"No review step registered with name {name!r}")
    return _REVIEW_STEPS[name]


def all_guards() -> list[RegisteredGuard]:
    """Return all registered guards."""
    return list(_GUARDS.values())


def all_review_steps() -> list[RegisteredReviewStep]:
    """Return all registered review steps."""
    return list(_REVIEW_STEPS.values())


def clear_registry() -> None:
    """Clear all registered guards and review steps."""
    _GUARDS.clear()
    _REVIEW_STEPS.clear()


def find_guards_for_lesson(lesson_id: str) -> list[RegisteredGuard]:
    """Find guards mapped to a lesson ID (exact full ID or base prefix)."""
    if not lesson_id or not str(lesson_id).strip():
        raise UnreadableInputError("lesson_id cannot be empty or missing")
    clean = str(lesson_id).strip()
    base_prefix = clean.split("-")[0]
    matched: list[RegisteredGuard] = []
    for g in _GUARDS.values():
        for lid in g.lesson_ids:
            if lid == clean or lid == base_prefix or lid.split("-")[0] == base_prefix:
                matched.append(g)
                break
    return matched


def find_review_steps_for_lesson(lesson_id: str) -> list[RegisteredReviewStep]:
    """Find review steps mapped to a lesson ID (exact full ID or base prefix)."""
    if not lesson_id or not str(lesson_id).strip():
        raise UnreadableInputError("lesson_id cannot be empty or missing")
    clean = str(lesson_id).strip()
    base_prefix = clean.split("-")[0]
    matched: list[RegisteredReviewStep] = []
    for r in _REVIEW_STEPS.values():
        for lid in r.lesson_ids:
            if lid == clean or lid == base_prefix or lid.split("-")[0] == base_prefix:
                matched.append(r)
                break
    return matched


# -----------------------------------------------------------------------------
# Coverage auditor parsing docs/lessons-audit.md
# -----------------------------------------------------------------------------

def audit_lesson_coverage(
    audit_file: Path | str | None = None,
) -> dict[str, Any]:
    """Audit coverage of lessons from docs/lessons-audit.md.
    
    Identifies lessons with neither a registered guard nor a review step.
    Always raises UnreadableInputError on missing or unreadable inputs.
    
    Args:
        audit_file: Path to docs/lessons-audit.md. If None, uses default project path.
        
    Returns:
        dict containing total_lessons, covered_by_guard_count, covered_by_review_count,
        uncovered_count, errors, uncovered_lessons, and detailed records.
        
    Raises:
        UnreadableInputError: If audit_file does not exist, is not a file, is unreadable,
            is empty, or lacks a valid lesson inventory table.
    """
    if audit_file is not None and isinstance(audit_file, str) and not audit_file.strip():
        raise UnreadableInputError("Audit input file path cannot be empty")

    path = Path(audit_file) if audit_file is not None else (ROOT / "docs/lessons-audit.md")
    errors: list[str] = []

    if not path.exists():
        raise UnreadableInputError(f"Audit input file not found or unreadable: {path}")

    if not path.is_file():
        raise UnreadableInputError(f"Audit path is not a regular file: {path}")

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as exc:
        raise UnreadableInputError(f"Failed to read audit file {path}: {exc}") from exc

    if not content.strip():
        raise UnreadableInputError(f"Audit file is empty: {path}")

    # Locate ## Lesson inventory section
    lines = content.splitlines()
    in_inventory = False
    in_table = False
    parsed_lessons: dict[str, dict[str, Any]] = {}

    for line_idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("## Lesson inventory"):
            in_inventory = True
            continue

        if in_inventory:
            if stripped.startswith("## ") and in_table:
                # Reached next section
                break

            if stripped.startswith("| ID |"):
                in_table = True
                continue

            if in_table:
                if stripped.startswith("|---"):
                    continue
                if not stripped.startswith("|"):
                    if stripped == "":
                        continue
                    # Unexpected non-empty line inside table
                    errors.append(f"Unreadable non-table line inside inventory at line {line_idx}: {line!r}")
                    continue

                # Split row columns preserving empty entries between pipes
                raw_cols = stripped.split("|")
                # Remove outer bounding empty items
                if len(raw_cols) >= 3:
                    cols = [c.strip() for c in raw_cols[1:-1]]
                else:
                    cols = []

                if len(cols) != 7:
                    errors.append(
                        f"Unreadable table row (expected 7 columns, got {len(cols)}) at line {line_idx}: {line!r}"
                    )
                    continue

                lesson_id = cols[0]
                one_line = cols[1]
                root_class = cols[2]
                raw_tier = cols[3]
                enforcement = cols[4]
                proposed = cols[5]
                proof = cols[6]

                try:
                    tier = int(raw_tier)
                except ValueError:
                    errors.append(f"Unreadable tier {raw_tier!r} at line {line_idx}: {line!r}")
                    continue

                parsed_lessons[lesson_id] = {
                    "id": lesson_id,
                    "short_id": lesson_id.split("-")[0],
                    "one_line": one_line,
                    "root_class": root_class,
                    "tier": tier,
                    "current_enforcement": enforcement,
                    "proposed_control": proposed,
                    "proof": proof,
                    "line_number": line_idx,
                }

    if not in_table:
        raise UnreadableInputError(f"Could not find valid '## Lesson inventory' table in {path}")

    # Classify coverage
    covered_by_guard: list[str] = []
    covered_by_review: list[str] = []
    needs_real_case: list[str] = []
    uncovered: list[str] = []

    for lid, ldata in parsed_lessons.items():
        guards = find_guards_for_lesson(lid)
        reviews = find_review_steps_for_lesson(lid)

        if guards:
            # Check if all matching guards are flagged as needs_real_case
            if all(g.needs_real_case for g in guards):
                needs_real_case.append(lid)
            else:
                covered_by_guard.append(lid)
        elif reviews:
            covered_by_review.append(lid)
        else:
            uncovered.append(lid)

    return {
        "total_lessons": len(parsed_lessons),
        "covered_by_guard_count": len(covered_by_guard),
        "covered_by_review_count": len(covered_by_review),
        "needs_real_case_count": len(needs_real_case),
        "uncovered_count": len(uncovered),
        "errors": errors,
        "unreadable_inputs": [str(path)] if errors else [],
        "covered_by_guard": covered_by_guard,
        "covered_by_review": covered_by_review,
        "needs_real_case": needs_real_case,
        "uncovered_lessons": uncovered,
        "covered_lessons": covered_by_guard + covered_by_review,
        "lessons": parsed_lessons,
    }


def report_uncovered_lessons(
    audit_file: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Return list of lesson records from docs/lessons-audit.md with neither a guard nor a review step.
    
    Raises UnreadableInputError if the audit file is missing, unreadable, or contains errors.
    Never returns an empty list on bad input.
    """
    audit = audit_lesson_coverage(audit_file=audit_file)
    if audit.get("errors"):
        raise UnreadableInputError(f"Unreadable audit input: {'; '.join(audit['errors'])}")
    uncovered_ids = audit["uncovered_lessons"]
    return [audit["lessons"][lid] for lid in uncovered_ids if lid in audit["lessons"]]


def format_coverage_report(
    audit_file: Path | str | None = None,
) -> str:
    """Generate a human-readable text coverage report of lessons audit.
    
    Catches UnreadableInputError on bad inputs to render a report whose FIRST line
    states the error and which never shows covered/uncovered counts.
    """
    try:
        audit = audit_lesson_coverage(audit_file=audit_file)
        if audit.get("errors"):
            raise UnreadableInputError(f"Audit input contains errors: {'; '.join(audit['errors'])}")
    except UnreadableInputError as exc:
        lines = [
            f"ERROR: Unreadable audit input: {exc}",
            "ERRORS ENCOUNTERED (UNREADABLE INPUTS):",
            f"  - {exc}",
            "No coverage counts available.",
        ]
        return "\n".join(lines)

    lines = [
        "Lesson Guard & Review Coverage Report",
        "=====================================",
        f"Total Lessons:           {audit['total_lessons']}",
        f"Covered by Guard:        {audit['covered_by_guard_count']}",
        f"Covered by Review Step:  {audit['covered_by_review_count']}",
        f"Needs Real Case:         {audit['needs_real_case_count']}",
        f"Uncovered:               {audit['uncovered_count']}",
        "",
        f"Coverage: {((audit['covered_by_guard_count'] + audit['covered_by_review_count']) / max(audit['total_lessons'], 1)):.1%}",
    ]
    if audit["uncovered_lessons"]:
        lines.append("")
        lines.append("Uncovered Lessons (neither guard nor review step):")
        for lid in audit["uncovered_lessons"]:
            lines.append(f"  - {lid}")
    return "\n".join(lines)


coverage_report = format_coverage_report


def _slugify_heading(heading: str) -> str:
    """Normalize a markdown heading into a GitHub-compatible anchor slug."""
    text = heading.strip().lower()
    cleaned = [ch for ch in text if ch.isalnum() or ch in (" ", "-")]
    joined = "".join(cleaned).strip()
    slug = re.sub(r"\s+", "-", joined)
    return slug.strip("-")


def verify_tier3_review_steps(
    audit_file: Path | str | None = None,
    review_steps_file: Path | str | None = None,
) -> dict[str, Any]:
    """Verify that every Tier 3 lesson has a registered review step pointing to an existing doc section.

    Validates that:
    1. Both audit_file and review_steps_file exist, are non-empty, and can be read.
    2. Every Tier 3 lesson defined in audit_file has at least one registered review step.
    3. Every matching review step specifies a section anchor that exists in review_steps_file.

    Args:
        audit_file: Path to docs/lessons-audit.md. If None, uses default project path.
        review_steps_file: Path to docs/review-steps.md. If None, uses default project path.

    Returns:
        dict containing passed (bool), total_tier3, covered_tier3_count, checked_steps_count,
        errors (list[str]), and tier3_lessons (list[str]).

    Raises:
        UnreadableInputError: If either file is missing, empty, unreadable, or invalid.
    """
    if audit_file is not None and isinstance(audit_file, str) and not audit_file.strip():
        raise UnreadableInputError("Audit file path cannot be empty")
    if review_steps_file is not None and isinstance(review_steps_file, str) and not review_steps_file.strip():
        raise UnreadableInputError("Review steps file path cannot be empty")

    a_path = Path(audit_file) if audit_file is not None else (ROOT / "docs/lessons-audit.md")
    r_path = Path(review_steps_file) if review_steps_file is not None else (ROOT / "docs/review-steps.md")

    if not a_path.exists():
        raise UnreadableInputError(f"Audit file not found: {a_path}")
    if not a_path.is_file():
        raise UnreadableInputError(f"Audit path is not a regular file: {a_path}")

    if not r_path.exists():
        raise UnreadableInputError(f"Review steps doc file not found: {r_path}")
    if not r_path.is_file():
        raise UnreadableInputError(f"Review steps doc path is not a regular file: {r_path}")

    try:
        r_content = r_path.read_text(encoding="utf-8")
    except Exception as exc:
        raise UnreadableInputError(f"Failed to read review steps file {r_path}: {exc}") from exc

    if not r_content.strip():
        raise UnreadableInputError(f"Review steps file is empty: {r_path}")

    # Audit lessons coverage
    audit = audit_lesson_coverage(audit_file=a_path)
    if audit.get("errors"):
        raise UnreadableInputError(f"Audit input contains errors: {'; '.join(audit['errors'])}")

    tier3_lessons = {lid: data for lid, data in audit["lessons"].items() if data["tier"] == 3}
    if not tier3_lessons:
        raise UnreadableInputError(f"No Tier 3 lessons found in audit file {a_path}")

    # Extract all heading slugs from review_steps_file
    slugs: set[str] = set()
    raw_headings: set[str] = set()
    for line in r_content.splitlines():
        line_s = line.strip()
        if line_s.startswith("#"):
            heading_text = line_s.lstrip("#").strip()
            if heading_text:
                slugs.add(_slugify_heading(heading_text))
                raw_headings.add(heading_text.lower())

    errors: list[str] = []
    checked_steps: list[RegisteredReviewStep] = []
    covered_tier3: list[str] = []

    for lid in tier3_lessons:
        steps = find_review_steps_for_lesson(lid)
        if not steps:
            errors.append(f"Tier 3 lesson {lid} has no registered review step")
            continue
        covered_tier3.append(lid)
        for step in steps:
            checked_steps.append(step)
            loc = step.location.strip()
            if not loc:
                errors.append(f"Review step {step.name} (lesson {lid}) has empty location")
                continue
            file_part, has_anchor, anchor = loc.partition("#")
            if not has_anchor or not anchor.strip():
                errors.append(
                    f"Review step {step.name} (lesson {lid}) location {loc!r} does not specify a section anchor"
                )
                continue
            anchor_slug = _slugify_heading(anchor)
            if anchor_slug not in slugs and anchor.lower().strip() not in raw_headings:
                errors.append(
                    f"Review step {step.name} (lesson {lid}) section {anchor!r} not found in {r_path.name}"
                )

    return {
        "passed": len(errors) == 0,
        "total_tier3": len(tier3_lessons),
        "covered_tier3_count": len(covered_tier3),
        "checked_steps_count": len(checked_steps),
        "errors": errors,
        "tier3_lessons": list(tier3_lessons.keys()),
    }


# -----------------------------------------------------------------------------
# Pre-registered guards with frozen real cases
# -----------------------------------------------------------------------------

# 1. l0188: Book filename edition mismatch vs copyright page
register_guard(
    fn=check_book_edition,
    name="evidence_book_edition",
    lesson_ids=("l0188-file-named-neufert", "l0188"),
    real_case=case("Neufert Architects Data 6th ed. 2023.pdf", "2nd English edition 1980"),
    clean_case=case("Metric_Handbook_7th_ed_2022.pdf", "7th edition 2022"),
    expected_real={"status": EvidenceStatus.UNVERIFIED, "matches": False},
    expected_clean={"status": EvidenceStatus.VERIFIED, "matches": True},
    tier=2,
    description="Detects discrepancy between book download filename edition and copyright page (l0188)",
)

# 2. l0189: PDF page sequence label vs printed page number
register_guard(
    fn=assert_page_agreement,
    name="evidence_page_locator_agreement",
    lesson_ids=("l0189-building-construction-il", "l0189"),
    real_case=case(191, "5.45"),
    clean_case=case("17", "17"),
    expected_real=PageMismatchError,
    expected_clean=None,
    tier=2,
    description="Fails closed when PDF page sequence label disagrees with printed page (l0189)",
)

# 3. l0179: Model metadata dimension disagrees with measured geometry
register_guard(
    fn=assert_geometry_matches_metadata,
    name="evidence_geometry_metadata_agreement",
    lesson_ids=("l0179-model-genuinely-disagree", "l0179"),
    real_case=case(408.0, 202.0, tolerance=5.0),
    clean_case=case(408.0, 408.2, tolerance=1.0),
    expected_real=GeometryDisagreementError,
    expected_clean=None,
    tier=2,
    description="Fails closed when model metadata disagrees with measured geometry (l0179)",
)

# 4. l0113: Zip bytes declared as application/json
def _guard_l0113_sniff_and_ingest(declared_type: str) -> EvidenceRecord:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("photometry.ies", "IESNA:LM-63-2002\nTILT=NONE\n")
    zip_bytes = buf.getvalue()
    return ingest_bytes(
        zip_bytes,
        declared_type=declared_type,
        url="https://api.signify.com/photometry/download?sku=123",
    )

register_guard(
    fn=_guard_l0113_sniff_and_ingest,
    name="external_claims_content_sniffing",
    lesson_ids=("l0113-signify-served-zip", "l0113"),
    real_case=case("application/json"),
    clean_case=case("application/zip"),
    expected_real=EvidenceStatus.UNVERIFIED,
    expected_clean=EvidenceStatus.VERIFIED,
    tier=2,
    description="Sniffs raw byte structure and refuses declared content-type mismatch (l0113)",
)

# 5. l0118: Cross-source CCT and wattage disagreement
register_guard(
    fn=check_cct_and_watts_agreement,
    name="external_claims_cct_and_watts_agreement",
    lesson_ids=("l0118-signify-s-revit", "l0118"),
    real_case=case(
        {"cct": 3200, "watts": 3.0, "format": "rfa", "source_id": "Signify_Family"},
        {"cct": 3000, "watts": 23.0, "format": "ldt", "source_id": "Signify_LDT"},
    ),
    clean_case=case(
        {"cct": 3000, "watts": 23.0, "format": "rfa"},
        {"cct": 3000, "watts": 23.2, "format": "ldt"},
    ),
    expected_real=EvidenceStatus.UNVERIFIED,
    expected_clean=EvidenceStatus.VERIFIED,
    tier=2,
    description="Cross-checks CCT and wattage between Revit family and LDT, staying UNVERIFIED on drift (l0118)",
)

# 6. l0098: Strip-light photometry file on round drum fitting
register_guard(
    fn=check_photometry_fitting_agreement,
    name="external_claims_photometry_fitting_agreement",
    lesson_ids=("l0098-photometric-file-describ", "l0098"),
    real_case=case((594.0, 24.0), (276.0, 276.0), fitting_label="LT-05 Round Drum"),
    clean_case=case((280.0, 280.0), (276.0, 276.0), fitting_label="LT-05 Round Drum"),
    expected_real=EvidenceStatus.UNVERIFIED,
    expected_clean=EvidenceStatus.VERIFIED,
    tier=2,
    description="Rejects photometric file whose luminous opening aspect/size disagrees with physical fitting (l0098)",
)

# 7. C9: Coordinate or unit conversion scattered (l0012, l0023, l0114, l0182, l0409, l0473, l0669)
def _guard_c9_units_conversion(target_root: Path | str | None = None) -> bool:
    check_units_guard(target_root)
    return True

register_guard(
    fn=_guard_c9_units_conversion,
    name="units_conversion_guard",
    lesson_ids=(
        "l0012-directshape-rotation-bak", "l0012",
        "l0023-revit-s-viewdirection", "l0023",
        "l0114-converted-ldt-agreed", "l0114",
        "l0182-thermal-results-3", "l0182",
        "l0409-section-drawn-mirrored", "l0409",
        "l0473-solar-sun-position", "l0473",
        "l0669-parents-bed-rendered", "l0669",
    ),
    real_case=case(ROOT / "tests/fixtures/c9_unallowlisted_case"),
    clean_case=case(ROOT),
    expected_real=UnitsConversionError,
    expected_clean=True,
    tier=2,
    description="Fails closed on raw unit conversion literals (304.8, 0.3048, 3.28084, 25.4) outside units boundary (C9)",
)

# -----------------------------------------------------------------------------
# C5: Emitter and fitting disconnected (l0095, l0096, l0119, l0123, l0610)
# -----------------------------------------------------------------------------
register_guard(
    fn=check_fixture_record_consistency,
    name="fixture_record_consistency",
    lesson_ids=(
        "l0095-lamp-sources-sat", "l0095",
        "l0096-two-spec-heights", "l0096",
        "l0119-housing-below-ceiling", "l0119",
        "l0123-swapping-4300-lm", "l0123",
        "l0610-fitting-labelled-wrong", "l0610",
    ),
    real_case=case(ROOT / "tests/fixtures/c5_failing_case.json"),
    clean_case=case(ROOT / "tests/fixtures/c5_clean_case.json"),
    expected_real=FixtureConsistencyError,
    expected_clean=None,
    tier=2,
    description="Cross-checks photometry declared flux/CCT, emitter position, housing geometry, spec mounting height, and room containment (C5)",
)

# -----------------------------------------------------------------------------
# Safe I/O & Serialization guards (Phase 2, Batch 1)
# -----------------------------------------------------------------------------

_FALSY_ZERO_PATTERN = re.compile(r"float\(.*\bor\s+([1-9][0-9.]*|[A-Z_]{3,})\s*\)")


def check_falsy_zero_lint(line: str) -> None:
    """Fails closed when code line uses float(x or <nonzero>) swallowing zero (l0067)."""
    safe_io.encode(0)
    if _FALSY_ZERO_PATTERN.search(line):
        raise ValueError(f"Falsy-zero lint violation: {line.strip()}")


def check_utf16_or_utf8_json(raw_input: bytes | Path | str) -> dict[str, Any]:
    """Decodes UTF-16 or UTF-8 JSON bytes with BOM detection, rejecting empty reads (l0117)."""
    if isinstance(raw_input, (bytes, bytearray)):
        tf = Path(tempfile.gettempdir()) / f"utf16_decode_{uuid.uuid4().hex}.json"
        tf.write_bytes(bytes(raw_input))
        try:
            return safe_io.load_json(tf)
        finally:
            if tf.exists():
                try:
                    tf.unlink()
                except OSError:
                    pass
    return safe_io.load_json(raw_input)


_RAW_COPY_PATTERN = re.compile(r"shutil\.copy(file|2)?\(")


def check_raw_copy_lint(line: str) -> None:
    """Fails closed when pipeline output replaces files via raw shutil.copy instead of safe_io (l0131)."""
    safe_io.encode("")
    if _RAW_COPY_PATTERN.search(line):
        raise ValueError(f"Raw copy lint violation (unsafe file replacement under Windows locks): {line.strip()}")


def check_element_id_exact_integer(val: Any) -> dict[str, Any]:
    """Enforces exact integer type representation for element identifiers, preventing float degradation (l0466)."""
    return safe_io.encode(safe_io.ElementId(val))


# 8. l0019: Revit Color channels are .NET bytes
register_guard(
    fn=safe_io.encode,
    name="safe_io_color_channels",
    lesson_ids=("l0019-revit-color-channels", "l0019"),
    real_case=case(safe_io.Color(256, 180, 0)),
    clean_case=case(safe_io.Color(0, 180, 255)),
    expected_real=ValueError,
    expected_clean={
        "type": "Color",
        "value": [
            {"type": "int", "value": 0},
            {"type": "int", "value": 180},
            {"type": "int", "value": 255},
        ],
    },
    tier=2,
    description="Validates that Color channels are within byte range (0-255) before JSON serialization (l0019)",
)

# 9. l0024: Revit TextNote stores carriage returns and trailing newline
register_guard(
    fn=safe_io.encode,
    name="safe_io_textnote_normalization",
    lesson_ids=("l0024-revit-textnote-stores", "l0024"),
    real_case=case(safe_io.Text("Review\rRegistered \u00ae\r\n\n", "Review\rRegistered \u00ae\r\n\n")),
    clean_case=case(safe_io.normalized_text("Review\rRegistered \u00ae\r\n\n")),
    expected_real=ValueError,
    expected_clean={
        "type": "Text",
        "value": [
            {"type": "str", "value": "Review\rRegistered \u00ae\r\n\n"},
            {"type": "str", "value": "Review\nRegistered \u00ae"},
        ],
    },
    tier=2,
    description="Enforces text normalization on TextNote records, rejecting un-normalized carriage returns (l0024)",
)

# 10. l0067, l0066: falsy-zero lint catches an or-default that swallows an explicit zero
register_guard(
    fn=check_falsy_zero_lint,
    name="safe_io_falsy_zero_lint",
    lesson_ids=(
        "l0067-first-falsy-zero", "l0067",
        "l0066-lights-could-not", "l0066",
    ),
    real_case=case('energy = P * float(fx.get("output") or 1.0)'),  # falsy-ok: l0067 real bug fixture
    clean_case=case('energy = P * (float(fx["output"]) if fx.get("output") is not None else 1.0)'),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Fails closed on code lines using float(x or <nonzero>) that swallow an explicit zero (l0066, l0067)",
)

# 11. l0117: IronPython read UTF-16 as empty and failed on non-ASCII symbols
register_guard(
    fn=check_utf16_or_utf8_json,
    name="safe_io_utf16_bom_decode",
    lesson_ids=("l0117-ironpython-read-utf", "l0117"),
    real_case=case(b""),
    clean_case=case(b'\xff\xfe{\x00"\x00n\x00a\x00m\x00e\x00"\x00:\x00"\x00\xae\x00"\x00}\x00'),
    expected_real=(json.JSONDecodeError, ValueError),
    expected_clean={"name": "\u00ae"},
    tier=2,
    description="Decodes UTF-16 and UTF-8 JSON bytes with BOM detection and rejects empty stream reads (l0117)",
)

# 12. l0131: Windows file lock when replacing an open image
register_guard(
    fn=check_raw_copy_lint,
    name="safe_io_raw_copy_lint",
    lesson_ids=("l0131-windows-file-lock", "l0131"),
    real_case=case("shutil." "copyfile(folder/'render.png',out/'bedroom.png')"),  # raw_copy.search( fixture
    clean_case=case("copy_file(folder/'render.png', out/'bedroom.png')"),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Fails closed when raw shutil.copy is used instead of safe_io for replacing pipeline outputs (l0131)",
)

# 13. l0272: Tests read deliverables back and reject spec echo
register_guard(
    fn=safe_io.assert_measured_readback,
    name="safe_io_measured_readback_agreement",
    lesson_ids=("l0272-tests-test-deliverables", "l0272"),
    real_case=case({"width": 1200}, {"width": 1000}, {"width": "model"}),
    clean_case=case({"width": 1000}, {"width": 1000}, {"width": "model"}),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Rejects authored specifications echoed over independently measured model geometry (l0272)",
)

# 14. l0466: Integer bridge degradation to float corrupts element identifiers
register_guard(
    fn=check_element_id_exact_integer,
    name="safe_io_element_id_exact_integer",
    lesson_ids=("l0466-json-fix-passed", "l0466"),
    real_case=case(1.25),
    clean_case=case(9223372036854775807),
    expected_real=ValueError,
    expected_clean={
        "type": "ElementId",
        "value": [
            {"type": "int", "value": 9223372036854775807},
        ],
    },
    tier=2,
    description="Enforces exact integer type representation for element IDs, preventing float degradation (l0466)",
)

# -----------------------------------------------------------------------------
# Render QA guards (Phase 1 and Phase 2, Batch 1)
# -----------------------------------------------------------------------------

# Guard without real case listed as 'needs real case' (l0061: window_view passing void)
register_guard(
    fn=render_qa.check,
    name="render_qa_window_view_detail",
    lesson_ids=("l0061-first-window-view", "l0061"),
    real_case=None,
    clean_case=None,
    expected_real=None,
    expected_clean=None,
    tier=2,
    description="Requires local detail in window view and fails on smooth void gradients (l0061)",
    notes="needs real case: requires frozen pixel render of void sky gradient",
    needs_real_case=True,
)

# l0078: Thresholds set on synthetic images failed on real renders (window detail, colour cast, highlight floor)
register_guard(
    fn=render_qa.check,
    name="render_qa_threshold_calibration",
    lesson_ids=("l0078-thresholds-set-synthetic", "l0078"),
    real_case=None,
    clean_case=None,
    expected_real=None,
    expected_clean=None,
    tier=2,
    description="Calibrates render QA thresholds against real measured render data rather than synthetic tests (l0078)",
    notes="needs real case: requires frozen renders for window void detail (0.0026 vs 0.0365), warm colour cast (0.052-0.070 vs 0.06), and highlight floor",
    needs_real_case=True,
)

# l0079: Blue lamp-lit night passed colour cast at 0.036
register_guard(
    fn=render_qa.check,
    name="render_qa_cool_lamplit_cast",
    lesson_ids=("l0079-blue-lamp-lit", "l0079"),
    real_case=None,
    clean_case=None,
    expected_real=None,
    expected_clean=None,
    tier=2,
    description="Direction-aware colour cast guard failing cool cast above 0.02 on lamp-lit night views (l0079)",
    notes="needs real case: requires frozen pixel render of cool lamp-lit night view (measured 0.036 cool cast)",
    needs_real_case=True,
)

# l0081: Highlight-priority metering still clipped 4.1%
register_guard(
    fn=render_qa.check,
    name="render_qa_highlight_clipping",
    lesson_ids=("l0081-highlight-priority-meter", "l0081"),
    real_case=None,
    clean_case=None,
    expected_real=None,
    expected_clean=None,
    tier=2,
    description="Fails closed when highlight clipping exceeds 3% under highlight-priority metering (l0081)",
    notes="needs real case: requires frozen pixel render of view clipping 4.1% under highlight-priority metering",
    needs_real_case=True,
)

# l0082: Highlight priority underexposed two views (median 0.18 and 0.23)
register_guard(
    fn=render_qa.check,
    name="render_qa_exposure_midtones",
    lesson_ids=("l0082-highlight-priority-then", "l0082"),
    real_case=None,
    clean_case=None,
    expected_real=None,
    expected_clean=None,
    tier=2,
    description="Enforces midtone floor of at least 0.30 median luminance to prevent gloomy underexposure (l0082)",
    notes="needs real case: requires frozen pixel render of underexposed view (measured 0.18 and 0.23 median)",
    needs_real_case=True,
)

# l0100: Detail view named for pendant never framed it (sat at screen height 2.59)
register_guard(
    fn=render_qa.check,
    name="render_qa_view_subject_framing",
    lesson_ids=("l0100-detail-view-named", "l0100"),
    real_case=None,
    clean_case=None,
    expected_real=None,
    expected_clean=None,
    tier=2,
    description="Fails closed when declared view subject is out of frame in rendered camera view (l0100)",
    notes="needs real case: requires frozen scene render where pendant LT-03 sat at screen height 2.59 outside [0, 1] frame",
    needs_real_case=True,
)

# l0136: highlights_present failed soft overcast light
register_guard(
    fn=render_qa.check,
    name="render_qa_overcast_highlights",
    lesson_ids=("l0136-highlights-present-faile", "l0136"),
    real_case=None,
    clean_case=None,
    expected_real=None,
    expected_clean=None,
    tier=2,
    description="Treats highlight floor as advisory WARN on soft overcast scenes lacking direct light sources (l0136)",
    notes="needs real case: requires frozen pixel render of soft overcast scene reaching 0.86 without direct source",
    needs_real_case=True,
)

# -----------------------------------------------------------------------------
# Asset & Intake and Photometrics & Lighting guards (Phase 2, Batch 2)
# -----------------------------------------------------------------------------

def check_asset_role(entry: dict[str, Any]) -> list[str]:
    """Validates that asset role belongs to accepted role vocabulary (l0011)."""
    errs = asset_intake.validate_entry(entry)
    if any("unknown role" in e for e in errs):
        raise ValueError(f"Unknown role in entry: {errs}")
    return errs


def check_asset_bounds_normalisation(entry: dict[str, Any]) -> None:
    """Fails closed when asset extent is outside expected size range without normalisation (l0014)."""
    errs = asset_intake.validate_entry(entry)
    if any("outside" in e and "range" in e for e in errs):
        raise ValueError(f"Bounds normalisation error: {errs}")


def check_asset_contents_and_licence(entry: dict[str, Any]) -> None:
    """Enforces licence provenance and required component contents before shortlisting (l0075)."""
    errs = asset_intake.validate_entry(entry)
    if any("bed requires bedding" in e or "missing licence" in e or "not allowed" in e for e in errs):
        raise ValueError(f"Contents or licence missing: {errs}")


def safe_io_spec_echo_rejection(actual: dict[str, Any], measured: dict[str, Any], sources: dict[str, Any]) -> None:
    """Rejects read-back echoing specification values rather than measured model geometry (l0496)."""
    safe_io.assert_measured_readback(actual, measured, sources)


def check_landscape_tree_extent(props: list[dict[str, Any]]) -> None:
    """Fails closed when landscape trees enter building footprint or exceed yard boundaries (l0772)."""
    violations = villa_landscape.extent_violations(props)
    if violations:
        raise ValueError(f"Landscape tree extent violation: {violations}")


def check_landscape_standin_disclosure(props: list[dict[str, Any]]) -> None:
    """Enforces explicit stand-in disclosure for placeholder plant assets (l0846)."""
    violations = villa_landscape.standin_violations(props)
    if violations:
        raise ValueError(f"Stand-in disclosure violation: {violations}")


def check_landscape_bench_dimensions(props: list[dict[str, Any]]) -> None:
    """Enforces real seat height and length bounds on landscape benches (l0960)."""
    violations = villa_landscape.bench_violations(props)
    if violations:
        raise ValueError(f"Bench dimension violations: {violations}")


def check_fixture_photometry_ownership(item: dict[str, Any], ies_dir: Path | None = None) -> dict[str, Any]:
    """Ensures verified product figures govern fixture photometry and rejects contradictory spec values (l0025)."""
    target_dir = ies_dir or (Path(tempfile.gettempdir()) / "archpipe_ies_test")
    target_dir.mkdir(parents=True, exist_ok=True)
    return install.resolve(item, ies_dir=target_dir)


def check_luminaire_flux_requirement(item: dict[str, Any], requirement: dict[str, Any] | None = None) -> list[tuple[str, bool, str]]:
    """Validates installed luminaire flux against design luminous output requirement band (l0123)."""
    rows = install.expectations(item, requirement)
    for name, ok, detail in rows:
        if name == "luminaire flux" and not ok:
            raise ValueError(f"Luminaire flux requirement failed: {detail}")
    return rows


def check_lighting_beam_clashes(fixtures: list[Any]) -> None:
    """Detects physical clash between ceiling light fixtures and structural perimeter beams (l0650)."""
    clashes = villa_lighting.beam_clashes(fixtures)
    if clashes:
        raise ValueError(f"Lighting fixture clashes with structural beam: {clashes}")


# 15. l0011: Asset intake role vocabulary enforcement
register_guard(
    fn=check_asset_role,
    name="asset_intake_role_vocabulary",
    lesson_ids=("l0011-template-contains-doors", "l0011"),
    real_case=case(dict(
        id="measured_test_chair",
        role="lounge chair",
        source_url="https://example.org/test-chair",
        licence="CC-BY",
        author="Fixture author",
        credit="Fixture author, CC-BY",
        units_normalised={"scale_factor": 1.0, "reason": "fixture coordinates are metres"},
        up_axis="+Y",
        front_axis="+Z",
        bounds_m={"min": [0, 0, 0], "max": [0.8, 0.9, 0.8]},
        expected_size_range={"min_m": [0.7, 0.8, 0.7], "max_m": [0.9, 1.0, 0.9], "source": "test fixture card"},
        contents={},
        preview_image="previews/measured_test_chair.png",
    )),
    clean_case=case(dict(
        id="measured_test_chair",
        role="armchair",
        source_url="https://example.org/test-chair",
        licence="CC-BY",
        author="Fixture author",
        credit="Fixture author, CC-BY",
        units_normalised={"scale_factor": 1.0, "reason": "fixture coordinates are metres"},
        up_axis="+Y",
        front_axis="+Z",
        bounds_m={"min": [0, 0, 0], "max": [0.8, 0.9, 0.8]},
        expected_size_range={"min_m": [0.7, 0.8, 0.7], "max_m": [0.9, 1.0, 0.9], "source": "test fixture card"},
        contents={},
        preview_image="previews/measured_test_chair.png",
    )),
    expected_real=ValueError,
    expected_clean=[],
    tier=2,
    description="Validates asset role against accepted catalogue role vocabulary (l0011)",
)

# 16. l0014: Real Minotti sofa scale normalisation
register_guard(
    fn=check_asset_bounds_normalisation,
    name="asset_intake_bounds_normalisation",
    lesson_ids=("l0014-real-minotti-sofa", "l0014"),
    real_case=case(dict(
        id="sf_minotti_sofa",
        role="sofa",
        source_url="https://example.org/test-sofa",
        licence="CC-BY",
        author="Fixture author",
        credit="Fixture author, CC-BY",
        units_normalised={"scale_factor": 1.0, "reason": "native"},
        up_axis="+Y",
        front_axis="+Z",
        bounds_m={"min": [-147.9281, -44.2003, -49.6586], "max": [147.9281, 44.2003, 49.6586]},
        expected_size_range={"min_m": [2, 0.6, 0.7], "max_m": [3.5, 1.2, 1.5], "source": "test sofa card"},
        contents={},
        preview_image="previews/sofa.png",
    )),
    clean_case=case(dict(
        id="sf_minotti_sofa",
        role="sofa",
        source_url="https://example.org/test-sofa",
        licence="CC-BY",
        author="Fixture author",
        credit="Fixture author, CC-BY",
        units_normalised={"scale_factor": 0.01, "reason": "native coordinates measured as centimetres"},
        up_axis="+Y",
        front_axis="+Z",
        bounds_m={"min": [-147.9281, -44.2003, -49.6586], "max": [147.9281, 44.2003, 49.6586]},
        expected_size_range={"min_m": [2, 0.6, 0.7], "max_m": [3.5, 1.2, 1.5], "source": "test sofa card"},
        contents={},
        preview_image="previews/sofa.png",
    )),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Fails closed when asset extent is outside expected size range without normalisation (l0014)",
)

# 17. l0072: All six props recorded as downloaded while folders empty
register_guard(
    fn=asset_intake.validate_manifest,
    name="asset_intake_empty_package",
    lesson_ids=("l0072-all-six-props", "l0072"),
    real_case=None,
    clean_case=None,
    expected_real=None,
    expected_clean=None,
    tier=2,
    description="Rejects asset packages recorded as downloaded when folders on disk are empty (l0072)",
    notes="needs real case: requires frozen empty-directory asset download manifest fixture where props are declared downloaded but folders are empty",
    needs_real_case=True,
)

# 18. l0075: Free modern bed candidate requires bedding and licence
register_guard(
    fn=check_asset_contents_and_licence,
    name="asset_intake_contents_and_licence",
    lesson_ids=("l0075-free-modern-bed", "l0075"),
    real_case=case(dict(
        id="test_bed",
        role="bed",
        source_url="https://example.org/bed",
        author="A",
        credit="A",
        units_normalised={"scale_factor": 1.0, "reason": "m"},
        up_axis="+Y",
        front_axis="+Z",
        bounds_m={"min": [0, 0, 0], "max": [2.0, 1.0, 1.8]},
        expected_size_range={"min_m": [1.8, 0.5, 1.5], "max_m": [2.2, 1.2, 2.0], "source": "bed card"},
        contents={"bedding": False},
        preview_image="previews/bed.png",
    )),
    clean_case=case(dict(
        id="test_bed",
        role="bed",
        source_url="https://example.org/bed",
        licence="CC0",
        author="A",
        credit="A",
        units_normalised={"scale_factor": 1.0, "reason": "m"},
        up_axis="+Y",
        front_axis="+Z",
        bounds_m={"min": [0, 0, 0], "max": [2.0, 1.0, 1.8]},
        expected_size_range={"min_m": [1.8, 0.5, 1.5], "max_m": [2.2, 1.2, 2.0], "source": "bed card"},
        contents={"bedding": True},
        preview_image="previews/bed.png",
    )),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Enforces asset licence provenance and required component contents before shortlisting (l0075)",
)

# 21. l0496: Revit window read-back echoing spec rejected
register_guard(
    fn=safe_io_spec_echo_rejection,
    name="safe_io_spec_echo_rejection",
    lesson_ids=("l0496-revit-window-read", "l0496"),
    real_case=case({"width": 1200, "sill": 0}, {"width": 1200, "sill": 0}, {"width": "spec", "sill": "spec"}),
    clean_case=case({"width": 1200, "sill": 0}, {"width": 1200, "sill": 0}, {"width": "model", "sill": "model"}),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Rejects read-back echoing specification values rather than measured model geometry (l0496)",
)

# 22. l0772: Landscape trees placed outside yard or in building footprint
register_guard(
    fn=check_landscape_tree_extent,
    name="villa_landscape_tree_extent",
    lesson_ids=("l0772-landscape-trees-placed", "l0772"),
    real_case=case([dict(id="draft-north-jacaranda", asset="jacaranda_tree", position=[18.30, -21.55, -3.0], rotation_deg=[0, 0, 0], scale=1.0)]),
    clean_case=case([dict(id="ok-tree", asset="jacaranda_tree", position=[26.0, -28.0, -3.0], rotation_deg=[0, 0, 0], scale=0.05)]),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Fails closed when landscape trees enter building footprint or exceed yard boundaries (l0772)",
)

# 23. l0846: Stand-in plant assets require explicit disclosure
register_guard(
    fn=check_landscape_standin_disclosure,
    name="villa_landscape_standin_disclosure",
    lesson_ids=("l0846-asset-stand-s", "l0846"),
    real_case=case([dict(id="old-north-tree", asset="tree_small_02", label="dressing: Bauhinia variegata; care: https://example/ (round3); nursery height 2.55 m ASSUMED")]),
    clean_case=case([dict(id="ok-tree", asset="tree_small_02", label="dressing: ASSUMED visual stand-in; Bauhinia variegata; care: https://x")]),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Enforces explicit stand-in disclosure for placeholder plant assets (l0846)",
)

# 24. l0960: Top-garden bench dimension and aspect ratio checks
register_guard(
    fn=check_landscape_bench_dimensions,
    name="villa_landscape_bench_dimensions",
    lesson_ids=("l0960-top-garden-bench", "l0960"),
    real_case=case([villa_landscape._prop("draft-old-bench", "sf_wooden_bench", (10.70, -21.15), 0.0, 0.48, "old scale", zone="top", yaw=90)]),
    clean_case=case([dict(id="clean-bench", asset="sf_wooden_bench", position=[11.5, -21.75, 0.0], rotation_deg=[0, 0, 0], scale=[1.80 / 3.5797, 1.80 / 3.5797, 0.40 / 0.4778], zone="top")]),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Enforces real seat height and length bounds on landscape benches (l0960)",
)

# 25. l0025: Third-party family photometry overrides rejected when spec contradicts product
register_guard(
    fn=check_fixture_photometry_ownership,
    name="luminaires_spec_contradiction_rejection",
    lesson_ids=("l0025-third-party-families", "l0025"),
    real_case=case(dict(id="LT-01", product={"manufacturer": "signify", "sku": "911401840687", "lamp_set": 0}, lumens=500)),
    clean_case=case(dict(id="LT-01", product={"manufacturer": "signify", "sku": "911401840687", "lamp_set": 0})),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Ensures verified product figures govern fixture photometry and rejects contradictory spec values (l0025)",
)

# 26. l0074: Nishita sky units and sun direction calibration
register_guard(
    fn=villa_lighting.design,
    name="lighting_nishita_sky_calibration",
    lesson_ids=("l0074-nishita-sky-units", "l0074"),
    real_case=None,
    clean_case=None,
    expected_real=None,
    expected_clean=None,
    tier=2,
    description="Calibrates Nishita sky sun rotation to azimuth and scales radiance units to physical lux (l0074)",
    notes="needs real case: requires frozen sensor render of Nishita sky calibration probe",
    needs_real_case=True,
)

# 27. l0123: Swapping 4300 lm lamp exceeds flux requirement
register_guard(
    fn=check_luminaire_flux_requirement,
    name="luminaires_flux_requirement",
    lesson_ids=("l0123-swapping-4300-lm", "l0123"),
    real_case=case({"product": {"luminaire_lm": 4300}}, {"lumens": [300, 500]}),
    clean_case=case({"product": {"luminaire_lm": 400}}, {"lumens": [300, 500]}),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates installed luminaire flux against design luminous output requirement band (l0123)",
)

# 28. l0650: Fixture clashing with perimeter beam
register_guard(
    fn=check_lighting_beam_clashes,
    name="villa_lighting_beam_clashes",
    lesson_ids=("l0650-scene-lux-measurement", "l0650"),
    real_case=case([villa_lighting.Fixture("x", "ADJ", "bar-alcove", "B", 22.147, -29.241, -0.3)]),
    clean_case=case([villa_lighting.Fixture("ok", "DL", "living", "B", 20.0, -25.0, -0.3)]),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Detects physical clash between ceiling light fixtures and structural perimeter beams (l0650)",
)

# -----------------------------------------------------------------------------
# Material appearance basis guard (Class C7, Phase 1)
# -----------------------------------------------------------------------------

def check_material_appearance_basis(scene_or_spec: Any = None) -> list[dict[str, Any]]:
    """Fails closed when material appearance lacks verified basis or violates physical optics (C7)."""
    findings = material_basis.material_findings(scene_or_spec)
    errors = [f for f in findings if f.get("severity") == "ERROR"]
    if errors:
        first = errors[0]
        raise ValueError(
            f"Material appearance basis violation in '{first.get('material')}' "
            f"[{first.get('category')}]: {first.get('message')} (lesson {first.get('lesson_id')})"
        )
    return findings


# 29. C7: Material appearance basis (l0016, l0028, l0049, l0062, l0064, l0065, l0083, l0084, l0677, l0724, l0795, l0891, l0900, l0910)
register_guard(
    fn=check_material_appearance_basis,
    name="appearance_basis_phase1",
    lesson_ids=(
        "l0016-solid-magenta-box", "l0016",
        "l0028-revit-paint-hue", "l0028",
        "l0049-extracted-glass-solid", "l0049",
        "l0062-whole-room-rendered", "l0062",
        "l0064-pure-red-lamp", "l0064",
        "l0065-ivory-bedding-rendered", "l0065",
        "l0083-oak-grain-ran", "l0083",
        "l0084-dark-bronze-rendered", "l0084",
        "l0677-stone-wood-read", "l0677",
        "l0724-codex-pass-removed", "l0724",
        "l0795-wood-grain-rotated", "l0795",
        "l0891-artificial-grass-rendere", "l0891",
        "l0900-island-stair-void", "l0900",
        "l0910-ensuite-bath-screen", "l0910",
    ),
    real_case=case({
        "materials": {
            "lamp-shade-cad": {
                "kind": "principled",
                "base_rgb": [1.0, 0.0, 0.0],
                "reflectance": 0.35,
                "roughness": 0.5,
                "note": "Revit shade cad color rescaled to 0.35",
            }
        }
    }),
    clean_case=case({
        "materials": {
            "plaster-white": {
                "kind": "principled",
                "base_rgb": [0.82, 0.81, 0.79],
                "reflectance": 0.72,
                "roughness": 0.85,
                "specular": 0.35,
                "basis": "Dulux Natural White LRV 72",
            }
        }
    }),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Fails closed when material appearance lacks verified basis or violates physical optics (C7)",
)


# -----------------------------------------------------------------------------
# Scene & geometry builders guards (Phase 2, Batch 3)
# -----------------------------------------------------------------------------

def check_round2_spec_details(sp: dict[str, Any], rb: dict[str, Any], lay: dict[str, Any]) -> list[str]:
    """Fails closed when approved option spec details are ignored or missing in Revit readback (l0587)."""
    problems = villa_furnish3d.round2_postcondition(sp, rb, lay)
    if any("guest-wc-extract-grille" in p or "built 0 times" in p for p in problems):
        raise ValueError(f"Option spec details missing in readback: {problems}")
    elif problems:
        raise ValueError(f"Round 2 postcondition detail failure: {problems}")
    return problems


def check_round2_stair_glass_boundary(sp: dict[str, Any], rb: dict[str, Any], lay: dict[str, Any]) -> list[str]:
    """Fails closed when open-side glass extrusion projects outside stair room (l0589)."""
    problems = villa_furnish3d.round2_postcondition(sp, rb, lay)
    if any("leaves room" in p for p in problems):
        raise ValueError(f"Stair glass boundary failure: {problems}")
    elif problems:
        raise ValueError(f"Round 2 postcondition failure: {problems}")
    return problems


def check_physical_part_solid_winding(faces: list[Any]) -> list[str]:
    """Fails closed when closed solid mesh faces are wound inward with negative volume (l0047)."""
    errors = physical_part.geometry_errors(faces)
    if any("inward-facing solid" in e for e in errors):
        raise ValueError(f"Inward-facing solid error: {errors}")
    elif errors:
        raise ValueError(f"Solid geometry errors: {errors}")
    return errors


def check_render_contract_scene_geometry(scene: dict[str, Any]) -> list[str]:
    """Validates scene mesh polygons and fails closed on zero-area or degenerate geometry (l0686)."""
    errors = villa_render_contract.validate_scene(scene)
    poly_errors = [e for e in errors if "degenerate polygon" in e or "faces" in e]
    if poly_errors:
        raise ValueError(f"Render contract degenerate geometry error: {poly_errors}")
    return poly_errors


def check_physical_part_duvet_footprint(faces: list[Any], support: tuple[float, ...]) -> physical_part.Part:
    """Fails closed when duvet mesh vertices leave mattress support footprint (l0069)."""
    return physical_part.Part(
        kind="duvet",
        solid=faces,
        local_axes=("x", "y", "z"),
        material="linen",
        basis="authored-procedural",
        support=support,
    )


def check_physical_part_climber_proxy(faces: list[Any]) -> physical_part.Part:
    """Fails closed when climbing plant is drawn as a bare rectangular box proxy (l0878)."""
    return physical_part.Part(
        kind="climber",
        solid=faces,
        local_axes=("x", "y", "z"),
        material="greenery",
        basis="authored-procedural",
    )


def check_physical_part_garment_proxy(faces: list[Any]) -> physical_part.Part:
    """Fails closed when dressing room garment is modeled as a bare rectangular slab proxy (l0923)."""
    return physical_part.Part(
        kind="garment",
        solid=faces,
        local_axes=("x", "y", "z"),
        material="cotton",
        basis="authored-procedural",
    )


@functools.lru_cache(maxsize=1)
def _cached_villa_layout() -> dict[str, Any]:
    return _d1_round2_fixtures()[2]


@functools.lru_cache(maxsize=1)
def _cached_spec() -> dict[str, Any]:
    return _d1_round2_fixtures()[0]


@functools.lru_cache(maxsize=1)
def _cached_furnish_layout() -> list[dict[str, Any]]:
    return villa_furnish.layout(_cached_villa_layout())


@functools.lru_cache(maxsize=1)
def _cached_landscape_build() -> tuple[Any, list[dict[str, Any]], Any, dict[str, Any]]:
    return villa_landscape.build(_cached_spec(), _cached_villa_layout())


@functools.lru_cache(maxsize=1)
def _cached_lighting_design() -> list[Any]:
    return villa_lighting.design(_cached_villa_layout())


@functools.lru_cache(maxsize=1)
def _cached_parking_layout() -> dict[str, Any]:
    return copy.deepcopy(villa_parking.options()[0])


@functools.lru_cache(maxsize=1)
def _cached_parking_spec() -> dict[str, Any]:
    return revit_spec.build(_cached_parking_layout())


@functools.lru_cache(maxsize=1)
def _d1_round2_fixtures() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    lay = villa_r11.design("D1")
    spec = revit_spec.build(lay)
    spec["furniture"] = villa_furnish3d.spec(lay)
    hatch = spec["hatches"][0]
    z = revit_spec.LEVELS_Z[hatch["level"]]
    suite = next(d for d in spec["doors"] if set(d["rooms"]) == {"parents-bed", "parents-dressing"})
    rb = {
        "details": [
            {
                "mark": e["mark"],
                "category": e["category"],
                "comments": e["comments"],
                "bbox_mm": [v * 1000 for v in e["bbox"]],
            }
            for e in villa_furnish3d.round2_elements(spec)
        ],
        "hatches": [
            {
                "mark": hatch["id"],
                "category": "Openings",
                "comments": hatch["closure"],
                "host_wall": 81,
                "expected_host_wall": 81,
                "host_line_mm": [[3617, hatch["y"] * 1000], [15412, hatch["y"] * 1000]],
                "bbox_mm": [
                    hatch["x0"] * 1000,
                    (hatch["y"] - 0.1) * 1000,
                    (z + hatch["sill"]) * 1000,
                    hatch["x1"] * 1000,
                    (hatch["y"] + 0.1) * 1000,
                    (z + hatch["head"]) * 1000,
                ],
            }
        ],
        "doors": [
            {
                "rooms": ["kitchen", "dirty-kitchen"],
                "width": 1.2,
                "mark": "kitchen-dirty-sliding",
                "category": "Doors",
                "comments": "telescopic-pocket-3; 3 leaves",
                "bbox_mm": [0] * 6,
            },
            {
                "rooms": suite["rooms"],
                "width": suite["width"],
                "category": "Doors",
                "bbox_mm": [0] * 6,
                "point_mm": [suite["x"] * 1000, suite["y"] * 1000],
            },
        ],
        "windows": [
            {
                "mark": "window-study-game-%.3f-%.3f" % (w["x"], w["y"]),
                "category": "Windows",
                "bbox_mm": [0] * 6,
                "sill": w["sill"],
                "height": w["height"],
                "width": w["width"],
            }
            for w in spec["windows"]
            if w.get("room") == "study-game"
        ],
        "furniture": [
            {
                "mark": f["mark"],
                "bbox": f["envelope"],
                "comments": f["type"],
                "bbox_mm": [
                    (v + (revit_spec.LEVELS_Z[f["level"]] if k in (2, 5) else 0)) * 1000
                    for k, v in enumerate(f["envelope"])
                ],
            }
            for f in spec["furniture"]
        ],
    }
    return spec, rb, lay


def _make_box_faces(x0: float, y0: float, z0: float, x1: float, y1: float, z1: float) -> list[list[list[float]]]:
    """Six outward CCW quads of an axis-aligned box."""
    return [
        [[x0, y0, z0], [x0, y1, z0], [x1, y1, z0], [x1, y0, z0]],
        [[x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]],
        [[x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1]],
        [[x1, y1, z0], [x0, y1, z0], [x0, y1, z1], [x1, y1, z1]],
        [[x0, y1, z0], [x0, y0, z0], [x0, y0, z1], [x0, y1, z1]],
        [[x1, y0, z0], [x1, y1, z0], [x1, y1, z1], [x1, y0, z1]],
    ]


def _make_triangular_prism_faces(
    x0: float = 0.0,
    y0: float = 0.0,
    z0: float = 0.0,
    x1: float = 2.0,
    y1: float = 1.5,
    z1: float = 0.7,
    x_mid: float = 1.0,
) -> list[list[list[float]]]:
    """A closed watertight outward-wound triangular prism with 3 distinct x coordinates."""
    return [
        [[x0, y0, z0], [x0, y1, z0], [x1, y1, z0], [x1, y0, z0]],
        [[x0, y0, z0], [x_mid, y0, z1], [x_mid, y1, z1], [x0, y1, z0]],
        [[x_mid, y0, z1], [x1, y0, z0], [x1, y1, z0], [x_mid, y1, z1]],
        [[x_mid, y0, z1], [x0, y0, z0], [x1, y0, z0]],
        [[x1, y1, z0], [x0, y1, z0], [x_mid, y1, z1]],
    ]


_round2_spec, _round2_clean_rb, _round2_lay = _d1_round2_fixtures()
_round2_missing_grille_rb = copy.deepcopy(_round2_clean_rb)
_round2_missing_grille_rb["details"] = [
    x for x in _round2_missing_grille_rb["details"] if x["mark"] != "guest-wc-extract-grille"
]
_round2_outside_glass_rb = copy.deepcopy(_round2_clean_rb)
_glass_panel = next(x for x in _round2_outside_glass_rb["details"] if x["mark"].startswith("stair-open-glass"))
_glass_panel["bbox_mm"][4] += 10

_headboard_clean_box = _make_box_faces(0.0, 0.0, 0.0, 1.0, 0.2, 1.0)
_headboard_inward_box = [f[::-1] for f in _headboard_clean_box]

_duvet_clean_faces = _make_triangular_prism_faces(0.0, 0.0, 0.5, 2.0, 1.5, 0.7, 1.0)
_duvet_slid_faces = [[[p[0] + 0.6, p[1], p[2]] for p in face] for face in _duvet_clean_faces]

_climber_box_faces = _make_box_faces(0.0, 0.0, 0.3, 0.08, 0.08, 0.38)
_climber_clean_faces = _make_triangular_prism_faces(0.0, 0.0, 0.0, 0.5, 0.5, 0.5, 0.25)

_garment_slab_faces = _make_box_faces(0.0, 0.0, 0.0, 0.30, 0.025, 1.0)
_garment_clean_faces = _make_triangular_prism_faces(0.0, 0.0, 0.0, 0.30, 0.20, 1.0, 0.15)


# 30. l0587: Option spec listed approved details that Revit builder ignored
register_guard(
    fn=check_round2_spec_details,
    name="villa_furnish3d_spec_details",
    lesson_ids=("l0587-option-spec-listed", "l0587"),
    real_case=case(_round2_spec, _round2_missing_grille_rb, _round2_lay),
    clean_case=case(_round2_spec, _round2_clean_rb, _round2_lay),
    expected_real=ValueError,
    expected_clean=[],
    tier=2,
    description="Fails closed when approved option spec details are ignored or missing in Revit readback (l0587)",
)

# 31. l0589: First open-side glass extrusion projected outside stair room
register_guard(
    fn=check_round2_stair_glass_boundary,
    name="villa_furnish3d_stair_glass_boundary",
    lesson_ids=("l0589-first-open-side", "l0589"),
    real_case=case(_round2_spec, _round2_outside_glass_rb, _round2_lay),
    clean_case=case(_round2_spec, _round2_clean_rb, _round2_lay),
    expected_real=ValueError,
    expected_clean=[],
    tier=2,
    description="Fails closed when open-side glass extrusion projects outside stair room (l0589)",
)

# 32. l0047: Inward-facing triangles on closed solid headboard mesh
register_guard(
    fn=check_physical_part_solid_winding,
    name="physical_part_solid_winding",
    lesson_ids=("l0047-closed-consistently-conn", "l0047"),
    real_case=case(_headboard_inward_box),
    clean_case=case(_headboard_clean_box),
    expected_real=ValueError,
    expected_clean=[],
    tier=2,
    description="Fails closed when closed solid mesh faces are wound inward with negative volume (l0047)",
)

# 33. l0686: 1,780 zero-area triangles refused whole draft on workstation
register_guard(
    fn=check_render_contract_scene_geometry,
    name="villa_render_contract_zero_area_triangles",
    lesson_ids=("l0686-1-780-zero", "l0686"),
    real_case=case({
        "schema": "villa-render/1",
        "id": "scene-degenerate-geometry",
        "library_root": "assets",
        "materials": {"metal": {"kind": "principled", "base_rgb": [0.2, 0.2, 0.2]}},
        "meshes": [
            {
                "id": "mesh-zero-area-triangle",
                "group": "fixture",
                "material": "metal",
                "label": "zero area degenerate face",
                "faces": [[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]]],
            }
        ],
    }),
    clean_case=case({
        "schema": "villa-render/1",
        "id": "scene-clean-geometry",
        "library_root": "assets",
        "materials": {"metal": {"kind": "principled", "base_rgb": [0.2, 0.2, 0.2]}},
        "meshes": [
            {
                "id": "mesh-triangle-valid",
                "group": "fixture",
                "material": "metal",
                "label": "valid triangle",
                "faces": [[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]],
            }
        ],
    }),
    expected_real=ValueError,
    expected_clean=[],
    tier=2,
    description="Validates scene mesh polygons and fails closed on zero-area or degenerate geometry (l0686)",
)

# 34. l0069: Duvet slid 0.6 m and hung onto floor
register_guard(
    fn=check_physical_part_duvet_footprint,
    name="physical_part_duvet_footprint",
    lesson_ids=("l0069-duvet-slid-0", "l0069"),
    real_case=case(_duvet_slid_faces, (0.0, 0.0, 2.0, 1.5)),
    clean_case=case(_duvet_clean_faces, (0.0, 0.0, 2.0, 1.5)),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Fails closed when duvet mesh vertices leave mattress support footprint (l0069)",
)

# 35. l0878: Climbing plant drawn as 80 mm magenta box floating 0.30 m above ground
register_guard(
    fn=check_physical_part_climber_proxy,
    name="physical_part_climber_proxy",
    lesson_ids=("l0878-climbing-plant-drawn", "l0878"),
    real_case=case(_climber_box_faces),
    clean_case=case(_climber_clean_faces),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Fails closed when climbing plant is drawn as a bare rectangular box proxy (l0878)",
)

# 36. l0923: Dressing room clothes flat 25 mm vertical slabs
register_guard(
    fn=check_physical_part_garment_proxy,
    name="physical_part_garment_proxy",
    lesson_ids=("l0923-dressing-room-clothes", "l0923"),
    real_case=case(_garment_slab_faces),
    clean_case=case(_garment_clean_faces),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Fails closed when dressing room garment is modeled as a bare rectangular slab proxy (l0923)",
)

# 37. l0059: Refractive glass slab blocks Cycles shadow rays (no sunlight enters)
register_guard(
    fn=render_qa.check,
    name="render_qa_glass_daylight_transmission",
    lesson_ids=("l0059-no-sunlight-entered", "l0059"),
    real_case=None,
    clean_case=None,
    expected_real=None,
    expected_clean=None,
    tier=2,
    description="Fails closed when architectural glass fails to transmit daylight and blocks Cycles shadow rays (l0059)",
    notes="needs real case: requires frozen pixel render of room where refractive glass slab blocked Cycles shadow rays",
    needs_real_case=True,
)

# 38. refactor-silent-deletion: Behaviour-preserving refactor silently deleted code
_OLD_COMPARE_LUX_INCIDENT = """
def main() -> int:
    rendered = json.loads(a.rendered.read_text(encoding="utf-8"))
    extract = json.loads(a.extract.read_text(encoding="utf-8"))
    return 0
"""

_NEW_COMPARE_LUX_INCIDENT = """
def main() -> int:
    extract = json.loads(a.extract.read_text(encoding="utf-8"))
    return 0
"""

_OLD_DEMO_LIGHTING_INCIDENT = """
IES = ph.revit_ies_dir()

def main() -> int:
    ies = ph.revit_ies_dir()
    return 0
"""

_NEW_DEMO_LIGHTING_INCIDENT = """
def main() -> int:
    ies = ph.revit_ies_dir()
    return 0
"""


def check_refactor_silent_deletion(
    old_src: str,
    new_src: str,
    path: str = "scripts/compare_lux.py",
    allowed: Any = None,
) -> list[Any]:
    """Audits behaviour-preserving refactors and fails closed on un-allowed code removals (refactor-silent-deletion)."""
    findings = refactor_audit.audit_source(old_src, new_src, path=path, allowed=allowed)
    removals = [f for f in findings if f.is_removal]
    if removals:
        first = removals[0]
        raise ValueError(
            f"Un-allowed refactor removal in {first.path}:{first.scope}: "
            f"{first.name} ({first.detail or first.kind})"
        )
    return findings


register_guard(
    fn=check_refactor_silent_deletion,
    name="refactor_silent_deletion",
    lesson_ids=("refactor-silent-deletion",),
    real_case=case(_OLD_COMPARE_LUX_INCIDENT, _NEW_COMPARE_LUX_INCIDENT, "scripts/compare_lux.py"),
    clean_case=case(_OLD_DEMO_LIGHTING_INCIDENT, _NEW_DEMO_LIGHTING_INCIDENT, "scripts/demo_bedroom_lighting.py"),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Audits behaviour-preserving refactors and fails closed on un-allowed code removals (refactor-silent-deletion)",
)


# -----------------------------------------------------------------------------
# Phase 2 Batch 4: Geometry, Stairs, Openings, Routes & Readback Guards
# -----------------------------------------------------------------------------

# 39. l0312, l0310, l0319: Stair access and circulation connectivity
def check_villa_concept_stair_access(lay: dict[str, Any]) -> dict[str, Any]:
    """Validates that all stair ends open onto circulation in villa concept layout (l0312, l0310, l0319)."""
    res = villa.critique(lay)
    chk = next((c for c in res.get("checks", []) if c.get("check") == "stair_access"), None)
    if chk is None or chk.get("status") == "fail":
        raise ValueError(f"Stair access check failed: {chk}")
    return chk


_lay_stair_access_bad = copy.deepcopy(villa.concept_a())
_lay_stair_access_bad["rooms"]["stair-b"]["ends"] = [["h", villa.YE, villa.SX0, villa.SX0 + 0.9]]

register_guard(
    fn=check_villa_concept_stair_access,
    name="villa_concept_stair_access",
    lesson_ids=("l0312-stair-access-check", "l0312", "l0310-critic-treated-stair", "l0310", "l0319-check-stair-by", "l0319"),
    real_case=case(_lay_stair_access_bad),
    clean_case=case(villa.concept_a()),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that all stair ends open onto circulation rather than walls or unreached rooms (l0312, l0310, l0319)",
)


# 40. l0504: Headroom measured from pitch line under slab soffit
def check_stair_pitch_headroom(
    stair: dict[str, Any],
    opening_mm: list[float] | None,
    min_headroom_mm: float = 2000.0,
) -> float:
    """Validates that stair pitch line headroom under slab soffit and beams meets minimum clearance (l0504)."""
    least_clearance, _ = stairs.pitch_headroom(stair, opening_mm)
    if least_clearance < min_headroom_mm:
        raise ValueError(
            f"Stair pitch headroom {least_clearance:.1f} mm is below required {min_headroom_mm:.1f} mm"
        )
    return least_clearance


register_guard(
    fn=check_stair_pitch_headroom,
    name="stair_pitch_headroom",
    lesson_ids=("l0504-headroom-measured-from", "l0504"),
    real_case=case(stairs.party_flight_r8(), [5177, -28421, 8537, -27471]),
    clean_case=case(stairs.party_flight_r8(), [5177, -28421, 8887, -27471]),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that stair pitch line headroom under slab soffit and beams meets minimum 2000 mm clearance (l0504)",
)


# 41. l0512: Clear route width from stair top around void
def check_villa_route_width_stair_void(lay: dict[str, Any], min_width_m: float = 0.90) -> float:
    """Validates clear route width from stair top around void to bedroom corridor (l0512)."""
    width = villa.gf_route_width(lay)
    if width < min_width_m:
        raise ValueError(
            f"GF route width around stair void {width:.2f} m is below minimum {min_width_m:.2f} m"
        )
    return width


_lay_route_pinch_bad = copy.deepcopy(_cached_parking_layout())
_r_pinch = _lay_route_pinch_bad["rooms"]
_r_pinch["kids-a"]["rect"][0] = _r_pinch["study-game"]["rect"][2] = 9.227
_r_pinch["gallery-end"]["rect"] = [8.657, -27.371, 9.227, -26.371]
_r_pinch["stair-gf"]["rect"][2] = _r_pinch["corridor"]["rect"][0] = 8.657
_r_pinch["study-game"].pop("open", None)

register_guard(
    fn=check_villa_route_width_stair_void,
    name="villa_route_width_stair_void",
    lesson_ids=("l0512-way-from-stair", "l0512"),
    real_case=case(_lay_route_pinch_bad),
    clean_case=case(_cached_parking_layout()),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates clear route width from stair top around void into bedroom corridor meets 0.90 m requirement (l0512)",
)


# 42. l0557: Door running into cross wall
def check_villa_furnish_door_wall_clearance(
    items: list[dict[str, Any]] | None = None,
    lay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validates that doors do not run into intersecting walls across openings (l0557)."""
    res = villa_furnish.check(items, lay)
    door_res = res.get("doors", {})
    if door_res.get("status") != "pass" or door_res.get("problems"):
        raise ValueError(f"Door clearance check failed: {door_res.get('problems')}")
    return door_res


_lay_d1_base = _cached_villa_layout()
_lay_door_wall_bad = copy.deepcopy(_lay_d1_base)
_lay_door_wall_bad["rooms"]["parents-dressing"]["door_at"]["parents-bed"] = 22.10

register_guard(
    fn=check_villa_furnish_door_wall_clearance,
    name="villa_furnish_door_wall_clearance",
    lesson_ids=("l0557-door-can-run", "l0557", "l0720-codex-fix-cut", "l0720"),
    real_case=case(_cached_furnish_layout(), _lay_door_wall_bad),
    clean_case=case(_cached_furnish_layout(), _lay_d1_base),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that doors do not run into intersecting walls across openings (l0557, l0720)",
)


# 43. l0576, l0531: Route corner disc path sweep
def check_villa_furnish_route_corner_disc(
    items: list[dict[str, Any]] | None = None,
    lay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validates that circulation routes admit clear disc path sweep round corners without pinch (l0576, l0531)."""
    res = villa_furnish.check(items, lay)
    routes_res = res.get("routes", {})
    if routes_res.get("status") != "pass" or routes_res.get("problems"):
        raise ValueError(f"Route corner disc clearance check failed: {routes_res.get('problems')}")
    return routes_res


_items_disc_bad = copy.deepcopy(_cached_furnish_layout())
_by_id_disc = {it["id"]: it for it in _items_disc_bad}
_by_id_disc["pd-hang-2"]["cy"] += 0.24

register_guard(
    fn=check_villa_furnish_route_corner_disc,
    name="villa_furnish_route_corner_disc",
    lesson_ids=("l0576-square-body-failed", "l0576", "l0531-body-rounded-down", "l0531"),
    real_case=case(_items_disc_bad, _lay_d1_base),
    clean_case=case(_cached_furnish_layout(), _lay_d1_base),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that circulation routes admit clear disc path sweep round corners without pinch (l0576, l0531)",
)


# 44. l0591: Kitchen run modules overrunning run length
def check_villa_furnish_kitchen_run_modules(
    items: list[dict[str, Any]] | None = None,
    lay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validates that kitchen counter run modules match run length and spacing requirements (l0591)."""
    res = villa_furnish.check(items, lay)
    k_res = res.get("kitchen", {})
    if k_res.get("status") != "pass" or k_res.get("problems"):
        raise ValueError(f"Kitchen module checks failed: {k_res.get('problems')}")
    return k_res


_items_k_bad = copy.deepcopy(_cached_furnish_layout())
_by_id_k = {it["id"]: it for it in _items_k_bad}
_by_id_k["dk-run"]["modules"][-1] = ("counter", 0.4)

register_guard(
    fn=check_villa_furnish_kitchen_run_modules,
    name="villa_furnish_kitchen_run_modules",
    lesson_ids=("l0591-run-s-modules", "l0591"),
    real_case=case(_items_k_bad, _lay_d1_base),
    clean_case=case(_cached_furnish_layout(), _lay_d1_base),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that kitchen counter run modules do not overrun available run length (l0591)",
)


# 45. l0820: Prop extent checked against basement rooms
def check_villa_landscape_prop_room_extent(
    props: list[dict[str, Any]],
    rooms: tuple[Any, ...] | list[Any] = (),
) -> list[tuple[str, str]]:
    """Validates that landscape props do not enter building footprint or basement rooms (l0820)."""
    violations = villa_landscape.extent_violations(props, rooms)
    if violations:
        raise ValueError(f"Landscape prop extent violations: {violations}")
    return violations


_rooms_garden_b = villa_landscape.garden_level_rooms(_lay_d1_base)
_draft_searsia_prop = [
    {
        "id": "draft-searsia",
        "asset": "searsia_lucida",
        "position": [13.25, -21.65, villa_landscape.GROUND + 0.38],
        "rotation_deg": [0, 0, 0],
        "scale": 0.7,
    }
]
_meshes_land, _props_land, _notes_land, _plan_land = _cached_landscape_build()

register_guard(
    fn=check_villa_landscape_prop_room_extent,
    name="villa_landscape_prop_room_extent",
    lesson_ids=("l0820-prop-extent-guard", "l0820"),
    real_case=case(_draft_searsia_prop, _rooms_garden_b),
    clean_case=case(_props_land, _rooms_garden_b),
    expected_real=ValueError,
    expected_clean=[],
    tier=2,
    description="Validates that landscape props do not enter building footprint or basement rooms (l0820)",
)


# 46. l0834: Landscape route obstruction check
def check_villa_landscape_route_obstruction(
    items: list[dict[str, Any]],
    routes: dict[str, Any] | None = None,
) -> list[tuple[str, str]]:
    """Validates that landscape props and furniture keep clear routes (l0834)."""
    violations = villa_landscape.route_violations(items, routes=routes or villa_landscape.PATHS)
    if violations:
        raise ValueError(f"Landscape route violations: {violations}")
    return violations


_draft_teak_sofa_item = [{"id": "draft-teak-sofa", "rect": (24.0, -26.25, 26.1, -25.40)}]

register_guard(
    fn=check_villa_landscape_route_obstruction,
    name="villa_landscape_route_obstruction",
    lesson_ids=("l0834-landscape-change-must", "l0834"),
    real_case=case(_draft_teak_sofa_item),
    clean_case=case(_props_land + _plan_land["objects"]),
    expected_real=ValueError,
    expected_clean=[],
    tier=2,
    description="Validates that landscape props and furniture keep required clear walking routes (l0834)",
)


# 47. l0695: Render support unsupported items check
def check_render_support_unsupported(
    scene: dict[str, Any],
    lay: dict[str, Any] | None = None,
) -> list[Any]:
    """Validates that all furniture, fixtures, dressing parts and props have physical support (l0695)."""
    floating = render_support.unsupported(scene, lay=lay)
    if floating:
        raise ValueError(f"Floating unsupported scene items detected: {floating}")
    return floating


_unsupported_real_scene = {
    "meshes": [
        {
            "id": "lamp-floating-shade",
            "group": "fixture",
            "material": "black-metal",
            "faces": [
                [[0.0, 0.0, 2.5], [1.0, 0.0, 2.5], [1.0, 1.0, 2.5], [0.0, 1.0, 2.5]],
            ],
        }
    ],
    "props": [],
}

_unsupported_clean_scene = {
    "meshes": [
        {
            "id": "floor-slab",
            "group": "building",
            "material": "plaster",
            "faces": [
                [[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [2.0, 2.0, 0.0], [0.0, 2.0, 0.0]],
            ],
        },
        {
            "id": "table-resting",
            "group": "furniture",
            "material": "oak",
            "faces": [
                [[0.5, 0.5, 0.0], [0.5, 1.5, 0.0], [1.5, 1.5, 0.0], [1.5, 0.5, 0.0]],
                [[0.5, 0.5, 0.8], [1.5, 0.5, 0.8], [1.5, 1.5, 0.8], [0.5, 1.5, 0.8]],
                [[0.5, 0.5, 0.0], [1.5, 0.5, 0.0], [1.5, 0.5, 0.8], [0.5, 0.5, 0.8]],
                [[1.5, 1.5, 0.0], [0.5, 1.5, 0.0], [0.5, 1.5, 0.8], [1.5, 1.5, 0.8]],
                [[0.5, 1.5, 0.0], [0.5, 0.5, 0.0], [0.5, 0.5, 0.8], [0.5, 1.5, 0.8]],
                [[1.5, 0.5, 0.0], [1.5, 1.5, 0.0], [1.5, 1.5, 0.8], [1.5, 0.5, 0.8]],
            ],
        },
    ],
    "props": [],
}

register_guard(
    fn=check_render_support_unsupported,
    name="render_support_unsupported_objects",
    lesson_ids=("l0695-floating-objects-found", "l0695"),
    real_case=case(_unsupported_real_scene),
    clean_case=case(_unsupported_clean_scene),
    expected_real=ValueError,
    expected_clean=[],
    tier=2,
    description="Validates that all furniture, fixtures, dressing parts and props have physical support (l0695)",
)


# 48. l0713: Render support blocked openings check
def check_render_support_blocked_openings(
    scene: dict[str, Any],
    lay: dict[str, Any] | None = None,
) -> list[Any]:
    """Validates that doors and room entrances remain passable without obstructive render geometry (l0713)."""
    blocked = render_support.blocked_openings(scene, lay=lay)
    if blocked:
        raise ValueError(f"Blocked openings detected in scene: {blocked}")
    return blocked


# Historical defect (l0713): The slatted headboard panel ran 0.6 m past the bed
# each way without checking for solid wall backing, blocking both the doorless
# parents' entry opening (y = -26.591, x in [18.427, 19.527]) and the dressing
# door (y = -26.591, x centred at 21.897).
_blocked_real_faces = []
for _k in range(int((21.13 + 0.9 - (19.53 - 0.6)) / 0.05)):
    _xa = round(19.53 - 0.6 + _k * 0.05, 3)
    _x0, _x1 = _xa, _xa + 0.03
    _y0, _y1 = -26.591, -26.561
    _z0, _z1 = 0.0, 2.10
    _blocked_real_faces.extend([
        [[_x0, _y0, _z0], [_x0, _y1, _z0], [_x1, _y1, _z0], [_x1, _y0, _z0]],
        [[_x0, _y0, _z1], [_x1, _y0, _z1], [_x1, _y1, _z1], [_x0, _y1, _z1]],
        [[_x0, _y0, _z0], [_x1, _y0, _z0], [_x1, _y0, _z1], [_x0, _y0, _z1]],
        [[_x1, _y1, _z0], [_x0, _y1, _z0], [_x0, _y1, _z1], [_x1, _y1, _z1]],
        [[_x0, _y1, _z0], [_x0, _y0, _z0], [_x0, _y0, _z1], [_x0, _y1, _z1]],
        [[_x1, _y0, _z0], [_x1, _y1, _z0], [_x1, _y1, _z1], [_x1, _y0, _z1]],
    ])

_blocked_real_scene = {
    "meshes": [
        {
            "id": "detail-headboard-slats",
            "group": "furniture",
            "material": "oak",
            "faces": _blocked_real_faces,
        }
    ]
}

# Clean case: headboard slats constrained to the solid wall backing (x in [19.60, 21.40]),
# leaving both the entry opening (x < 19.527) and dressing door (x > 21.497) completely clear.
_blocked_clean_faces = []
for _k in range(int((21.40 - 19.60) / 0.05)):
    _xa = round(19.60 + _k * 0.05, 3)
    _x0, _x1 = _xa, _xa + 0.03
    _y0, _y1 = -26.591, -26.561
    _z0, _z1 = 0.0, 2.10
    _blocked_clean_faces.extend([
        [[_x0, _y0, _z0], [_x0, _y1, _z0], [_x1, _y1, _z0], [_x1, _y0, _z0]],
        [[_x0, _y0, _z1], [_x1, _y0, _z1], [_x1, _y1, _z1], [_x0, _y1, _z1]],
        [[_x0, _y0, _z0], [_x1, _y0, _z0], [_x1, _y0, _z1], [_x0, _y0, _z1]],
        [[_x1, _y1, _z0], [_x0, _y1, _z0], [_x0, _y1, _z1], [_x1, _y1, _z1]],
        [[_x0, _y1, _z0], [_x0, _y0, _z0], [_x0, _y0, _z1], [_x0, _y1, _z1]],
        [[_x1, _y0, _z0], [_x1, _y1, _z0], [_x1, _y1, _z1], [_x1, _y0, _z1]],
    ])

_blocked_clean_scene = {
    "meshes": [
        {
            "id": "detail-headboard-slats",
            "group": "furniture",
            "material": "oak",
            "faces": _blocked_clean_faces,
        }
    ]
}

register_guard(
    fn=check_render_support_blocked_openings,
    name="render_support_blocked_openings",
    lesson_ids=("l0713-parents-entrance-closed", "l0713"),
    real_case=case(_blocked_real_scene, _lay_d1_base),
    clean_case=case(_blocked_clean_scene, _lay_d1_base),
    expected_real=ValueError,
    expected_clean=[],
    tier=2,
    description="Validates that doors and room entrances remain passable without obstructive render geometry (l0713)",
)


# 49. l0863: Revit wall opening spec_id match check
def check_villa_furnish3d_opening_spec_id(
    spec: dict[str, Any],
    readback: dict[str, Any],
    layout: dict[str, Any],
) -> list[str]:
    """Validates that wall openings without mark/comments are correctly matched via spec_id (l0863)."""
    problems = villa_furnish3d.round2_postcondition(spec, readback, layout)
    if problems:
        raise ValueError(f"Revit wall opening readback postcondition failed: {problems}")
    return problems


_spec_d1_wp5 = _round2_spec
_hatch_wp5 = _spec_d1_wp5["hatches"][0]
_hatch_z_wp5 = revit_spec.LEVELS_Z[_hatch_wp5["level"]]
_suite_door_wp5 = next(
    d for d in _spec_d1_wp5["doors"] if set(d["rooms"]) == {"parents-bed", "parents-dressing"}
)

_readback_base = copy.deepcopy(_round2_clean_rb)
_readback_base["hatches"][0]["mark"] = None
_readback_base["hatches"][0]["category"] = "Rectangular Straight Wall Opening"

_readback_opening_bad = copy.deepcopy(_readback_base)
_readback_opening_clean = copy.deepcopy(_readback_base)
_readback_opening_clean["hatches"][0]["spec_id"] = _hatch_wp5["id"]

register_guard(
    fn=check_villa_furnish3d_opening_spec_id,
    name="villa_furnish3d_opening_spec_id",
    lesson_ids=("l0863-revit-wall-opening", "l0863"),
    real_case=case(_spec_d1_wp5, _readback_opening_bad, _lay_d1_base),
    clean_case=case(_spec_d1_wp5, _readback_opening_clean, _lay_d1_base),
    expected_real=ValueError,
    expected_clean=[],
    tier=2,
    description="Validates that Revit wall openings lacking mark and comments are matched via spec_id (l0863)",
)


# -----------------------------------------------------------------------------
# Phase 2 Batch 5: Geometry, Routes, Spec Clearances & Execution Proof Guards
# -----------------------------------------------------------------------------

# 50. l0307: Straight flight clash with structural column
def check_villa_concept_stair_structure(lay: dict[str, Any]) -> dict[str, Any]:
    """Validates that stair geometry does not clash with structural columns or beams (l0307)."""
    res = villa.critique(lay)
    chk = next((c for c in res.get("checks", []) if c.get("check") == "stair_structure"), None)
    if chk and chk.get("status") == "fail":
        clashes = chk.get("clashes", [])
        raise ValueError(f"Stair structure clash detected: {clashes}")
    return chk or {}


_lay_stair_structure_bad = copy.deepcopy(villa.concept_a())
_lay_stair_structure_bad["stair"] = "r3"

register_guard(
    fn=check_villa_concept_stair_structure,
    name="villa_concept_stair_structure",
    lesson_ids=("l0307-villa-concept-round", "l0307"),
    real_case=case(_lay_stair_structure_bad),
    clean_case=case(villa.concept_a()),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that stair geometry does not clash with kept columns/beams such as column 1590377 (l0307)",
)


# 51. l0518: Clearance under ramp/deck soffit
def check_revit_spec_clearance_problems(
    lay: dict[str, Any],
    walls: list[dict[str, Any]],
    doors: list[dict[str, Any]],
    infills: tuple[Any, ...] | list[Any] = (),
) -> list[str]:
    """Validates that walls and doors under ramp and deck clear soffits without breaches (l0518)."""
    problems = revit_spec.clearance_problems(lay, walls, doors, infills)
    if problems:
        raise ValueError(f"Clearance problems detected under ramp/deck: {problems}")
    return problems


_lay_p_opt = _cached_parking_layout()
_sp_p_opt = _cached_parking_spec()
_sp_clearance_bad = copy.deepcopy(_sp_p_opt)
_cross_wall = next(
    w for w in _sp_clearance_bad["walls"]
    if w["level"] == "B" and abs(w["y0"] - w["y1"]) > 1e-6
    and w["y1"] > villa.YE + 0.3 and w["x0"] < villa_parking.RAMP_X1
)
_cross_wall["height"] = revit_spec.WALL_H

register_guard(
    fn=check_revit_spec_clearance_problems,
    name="revit_spec_clearance_problems",
    lesson_ids=("l0518-r9-follow-ups", "l0518"),
    real_case=case(_lay_p_opt, _sp_clearance_bad["walls"], _sp_clearance_bad["doors"], _sp_clearance_bad["infills"]),
    clean_case=case(_lay_p_opt, _sp_p_opt["walls"], _sp_p_opt["doors"], _sp_p_opt["infills"]),
    expected_real=ValueError,
    expected_clean=[],
    tier=2,
    description="Validates that under-ramp/deck cross walls and doors do not breach soffits or leave gaps (l0518)",
)


# 52. l0536: Kitchen island multi-cook work aisle clearance
def check_villa_furnish_kitchen_work_aisle(
    items: list[dict[str, Any]] | None = None,
    lay: dict[str, Any] | None = None,
) -> list[str]:
    """Validates that opposing kitchen counters maintain multi-cook work aisle clearance (l0536)."""
    res = villa_furnish.check(items, lay)
    k = res.get("kitchen", {})
    if k.get("status") == "fail":
        raise ValueError(f"Kitchen work aisle clearance failure: {k.get('problems')}")
    return k.get("problems", [])


_items_aisle_bad = copy.deepcopy(_cached_furnish_layout())
next(i for i in _items_aisle_bad if i["id"] == "k-island")["cy"] += 0.05

register_guard(
    fn=check_villa_furnish_kitchen_work_aisle,
    name="villa_furnish_kitchen_work_aisle",
    lesson_ids=("l0536-seating-card-assumed", "l0536"),
    real_case=case(_items_aisle_bad, _lay_d1_base),
    clean_case=case(_cached_furnish_layout(), _lay_d1_base),
    expected_real=ValueError,
    expected_clean=[],
    tier=2,
    description="Validates that kitchen island keeps 1219 mm multi-cook work aisle clearance (l0536)",
)


# 53. l0542: Stair foot must remain reachable on circulation routes
def check_villa_furnish_stair_foot_reachable(
    items: list[dict[str, Any]] | None = None,
    lay: dict[str, Any] | None = None,
) -> list[str]:
    """Validates that stair foot remains reached by circulation routes without obstruction (l0542)."""
    res = villa_furnish.check(items, lay)
    r = res.get("routes", {})
    if r.get("status") == "fail":
        raise ValueError(f"Stair foot route obstruction: {r.get('problems')}")
    return r.get("problems", [])


_items_stair_foot_bad = copy.deepcopy(_cached_furnish_layout())
_items_stair_foot_bad.append(
    villa_furnish.item("console", "hall-b", "sideboard", 10.1, -28.0, 90, w=1.2, d=0.45, h=0.8, why="x", level="B")
)

register_guard(
    fn=check_villa_furnish_stair_foot_reachable,
    name="villa_furnish_stair_foot_reachable",
    lesson_ids=("l0542-stair-flight-counted", "l0542"),
    real_case=case(_items_stair_foot_bad, _lay_d1_base),
    clean_case=case(_cached_furnish_layout(), _lay_d1_base),
    expected_real=ValueError,
    expected_clean=[],
    tier=2,
    description="Validates that stair foot is reachable and not blocked by furniture on circulation routes (l0542)",
)


# 54. l0566: Principal bedroom window route access
def check_villa_furnish_principal_window_reachable(
    items: list[dict[str, Any]] | None = None,
    lay: dict[str, Any] | None = None,
) -> list[str]:
    """Validates that principal bedroom window route access remains enforced across bed types (l0566)."""
    res = villa_furnish.check(items, lay)
    r = res.get("routes", {})
    if r.get("status") == "fail":
        raise ValueError(f"Principal bedroom window route obstruction: {r.get('problems')}")
    return r.get("problems", [])


_items_win_bad = copy.deepcopy(_cached_furnish_layout())
_ids_win_bad = {it["id"]: it for it in _items_win_bad}
_items_win_bad.remove(_ids_win_bad["pb-vanity"])
_items_win_bad.append(
    villa_furnish.item(
        "robe", "parents-bed", "wardrobe", 22.397 - 0.275, -25.4, 90, w=2.6, d=0.55, h=2.2, why="x", level="GF"
    )
)

register_guard(
    fn=check_villa_furnish_principal_window_reachable,
    name="villa_furnish_principal_window_reachable",
    lesson_ids=("l0566-principal-bedroom-window", "l0566"),
    real_case=case(_items_win_bad, _lay_d1_base),
    clean_case=case(_cached_furnish_layout(), _lay_d1_base),
    expected_real=ValueError,
    expected_clean=[],
    tier=2,
    description="Validates that principal bedroom window has clear 750 mm access route regardless of bed type (l0566)",
)


# 55. l0570: Pocket door approach route node access
def check_villa_furnish_pocket_door_approach(
    items: list[dict[str, Any]] | None = None,
    lay: dict[str, Any] | None = None,
) -> list[str]:
    """Validates that pocket door approaches provide route node connectivity without obstruction (l0570)."""
    res = villa_furnish.check(items, lay)
    r = res.get("routes", {})
    if r.get("status") == "fail":
        raise ValueError(f"Pocket door approach route obstruction: {r.get('problems')}")
    return r.get("problems", [])


_items_pocket_bad = copy.deepcopy(_cached_furnish_layout())
_items_pocket_bad.append(
    villa_furnish.item(
        "chest", "parents-entry", "sideboard", 18.977, -26.95, 0, w=0.9, d=0.45, h=0.8, why="x", level="GF"
    )
)

register_guard(
    fn=check_villa_furnish_pocket_door_approach,
    name="villa_furnish_pocket_door_approach",
    lesson_ids=("l0570-pocket-door-gave", "l0570"),
    real_case=case(_items_pocket_bad, _lay_d1_base),
    clean_case=case(_cached_furnish_layout(), _lay_d1_base),
    expected_real=ValueError,
    expected_clean=[],
    tier=2,
    description="Validates that pocket door entry vestibules maintain clear route approach nodes (l0570)",
)


# 56. l0551: Furniture placed against room boundaries (inside room)
def check_villa_furnish_inside_room_boundary(
    items: list[dict[str, Any]] | None = None,
    lay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validates that furniture items sit fully within room interior outlines (l0551)."""
    res = villa_furnish.check(items, lay)
    ir = res.get("inside_room", {})
    if ir.get("status") != "pass" or ir.get("problems"):
        raise ValueError(f"Furniture placed outside room boundary: {ir.get('problems')}")
    return ir


_items_inside_bad = copy.deepcopy(_cached_furnish_layout())
next(i for i in _items_inside_bad if i["id"] == "kb-desk")["cy"] = -23.4

register_guard(
    fn=check_villa_furnish_inside_room_boundary,
    name="villa_furnish_inside_room_boundary",
    lesson_ids=("l0551-furniture-placed-against", "l0551"),
    real_case=case(_items_inside_bad, _lay_d1_base),
    clean_case=case(_cached_furnish_layout(), _lay_d1_base),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that furniture pieces sit inside room boundary rather than overlapping walls (l0551)",
)


# 57. l0017: Bedside table placement within head-end Zone A clearance
def check_villa_furnish_bedside_zone_a(
    items: list[dict[str, Any]] | None = None,
    lay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validates bedside table placement within head-end Zone A clearance (l0017)."""
    res = villa_furnish.check(items, lay)
    c = res.get("clearances", {})
    if c.get("status") != "pass" or c.get("problems"):
        raise ValueError(f"Bedside clearance violation: {c.get('problems')}")
    return c


_items_bedside_bad = copy.deepcopy(_cached_furnish_layout())
_pb_bedside = next(i for i in _items_bedside_bad if i["id"] == "pb-bedside")
_pb_bedside["cy"] += 0.9

register_guard(
    fn=check_villa_furnish_bedside_zone_a,
    name="villa_furnish_bedside_zone_a",
    lesson_ids=("l0017-desk-chair-occupies", "l0017"),
    real_case=case(_items_bedside_bad, _lay_d1_base),
    clean_case=case(_cached_furnish_layout(), _lay_d1_base),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that bedside tables occupy only head-end Zone A and do not block bed side use zones (l0017)",
)


# 58. l0849: Dirty kitchen ventilation duct and detail constraints
def check_revit_spec_wp1_detail_constraints(
    lay: dict[str, Any],
    spec: dict[str, Any],
) -> list[str]:
    """Validates WP1 specification detail constraints including ventilation ducts and clearances (l0849)."""
    errors = revit_spec.check_wp1_spec(lay, spec)
    if errors:
        raise ValueError(f"WP1 spec constraint errors: {errors}")
    return errors


_spec_wp1_bad = copy.deepcopy(_cached_spec())
_spec_wp1_bad["ventilation"][0]["duct_route"][-1] = _spec_wp1_bad["ventilation"][0]["fan"]

register_guard(
    fn=check_revit_spec_wp1_detail_constraints,
    name="revit_spec_wp1_detail_constraints",
    lesson_ids=("l0849-dirty-kitchen-duct", "l0849"),
    real_case=case(_lay_d1_base, _spec_wp1_bad),
    clean_case=case(_lay_d1_base, _cached_spec()),
    expected_real=ValueError,
    expected_clean=[],
    tier=2,
    description="Validates that ventilation extract ducts rise from hood chimney to external wall (l0849)",
)


# 59. l0606: Vanity grooming and task illumination check
def check_villa_lighting_grooming_task(
    lay: dict[str, Any] | None = None,
    fixtures: list[Any] | None = None,
) -> list[dict[str, Any]]:
    """Validates task illumination requirements for grooming and work planes (l0606)."""
    res = villa_lighting.check(lay, fixtures)
    failed = [t for t in res.get("tasks", []) if t.get("status") == "fail"]
    if failed:
        raise ValueError(f"Lighting task targets failed: {failed}")
    return failed


_fx_lighting_clean = _cached_lighting_design()
_fx_lighting_bad = [
    f for f in _fx_lighting_clean
    if not (
        f.card == "ies-res-vanity-grooming-300"
        or (f.kind in ("SCONCE", "VSCONCE") and f.room in ("family-bath", "parents-ensuite", "guest-wc"))
    )
]

register_guard(
    fn=check_villa_lighting_grooming_task,
    name="villa_lighting_grooming_task",
    lesson_ids=("l0606-first-drafts-failed", "l0606"),
    real_case=case(_lay_d1_base, _fx_lighting_bad),
    clean_case=case(_lay_d1_base, _fx_lighting_clean),
    expected_real=ValueError,
    expected_clean=[],
    tier=2,
    description="Validates vanity grooming task illumination and fails closed when task downlights are omitted (l0606)",
)


# 60. l0029: Non-zero exit when stage report or verdict indicates failure
def check_stage_result_fail_verdict_rejection(report_or_verdict: Any) -> int:
    """Enforces non-zero exit when report or verdict contains any failure (l0029).

    The production helper exits the process (SystemExit, a BaseException the guard runner does not
    catch); translate a non-zero exit into a ValueError so the registry can observe it.
    """
    try:
        return stage_result.enforce_clean_verdict(report_or_verdict)
    except SystemExit as exc:
        if exc.code not in (0, None):
            raise ValueError(f"stage verdict FAIL: production enforce_clean_verdict exited {exc.code}") from exc
        return 0


_bad_report_incident = {
    "stage": "photometry_agreement",
    "passed": False,
    "verdict": "FAIL -- direct-light agreement outside 5%",
    "failures": ["clear-point median 1.0820 outside 5% band"],
    "checks": [{"check": "clear_point_agreement", "passed": False}],
}
_clean_report_incident = {
    "stage": "photometry_agreement",
    "passed": True,
    "verdict": "PASS -- direct-light median ratio within 5%",
    "failures": [],
    "checks": [{"check": "clear_point_agreement", "passed": True}],
}

register_guard(
    fn=check_stage_result_fail_verdict_rejection,
    name="stage_result_fail_verdict_rejection",
    lesson_ids=("l0029-script-printing-fail", "l0029"),
    real_case=case(_bad_report_incident),
    clean_case=case(_clean_report_incident),
    expected_real=ValueError,
    expected_clean=0,
    tier=2,
    description="Fails closed (production enforce_clean_verdict exits non-zero) when script verdict indicates FAIL (l0029)",
)


# 61. l0040: Cached stage result invalidation upon stale/modified inputs
def check_stage_result_stale_input_invalidation(
    record_or_path: dict[str, Any] | Path | str,
    root: Path | str | None = None,
    current_inputs: Iterable[Path | str] | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    """Validates that cached stage results fail closed when inputs are modified or stale (l0040)."""
    return stage_result.validate_stage_result(
        record_or_path,
        root=root,
        current_inputs=current_inputs,
        raise_on_error=True,
    )


_site_spec_file = ROOT / "spec/villa-site.yaml"
_site_sha, _site_size = stage_result.digest_file(_site_spec_file)

_record_clean = {
    "stage": "site_stage",
    "status": "ok",
    "exit_code": 0,
    "completeness": {"complete": True, "missing_outputs": [], "empty_outputs": []},
    "outputs": {
        "spec/villa-site.yaml": {
            "path": str(_site_spec_file),
            "sha256": _site_sha,
            "size_bytes": _site_size,
        }
    },
    "inputs": {
        "spec/villa-site.yaml": {
            "path": str(_site_spec_file),
            "sha256": _site_sha,
            "size_bytes": _site_size,
        }
    },
}

_record_stale_bad = copy.deepcopy(_record_clean)
_record_stale_bad["inputs"]["spec/villa-site.yaml"]["sha256"] = "0" * 64

register_guard(
    fn=check_stage_result_stale_input_invalidation,
    name="stage_result_stale_input_invalidation",
    lesson_ids=("l0040-three-unchanged-camera", "l0040"),
    real_case=case(_record_stale_bad, root=ROOT),
    clean_case=case(_record_clean, root=ROOT),
    expected_real=stage_result.StaleInputError,
    expected_clean=None,
    tier=2,
    description="Fails closed with StaleInputError when cached stage inputs differ from recorded hashes (l0040)",
)


# -----------------------------------------------------------------------------
# Phase 2 Batch 6: Revit Families, Geometry Critics, Authored Values & Render QA
# -----------------------------------------------------------------------------

# 62. l0042: Revit family format version compatibility without opening Revit
def check_rfa_portable_compatibility(
    family_path_or_bytes: Path | str | bytes,
    target_year: int = 2025,
) -> bool:
    """Validates that a Revit family file is compatible with target Revit release (l0042)."""
    if isinstance(family_path_or_bytes, bytes):
        with tempfile.NamedTemporaryFile(suffix=".rfa", delete=False) as tf:
            tf.write(family_path_or_bytes)
            tf_path = Path(tf.name)
        try:
            info = rfa.read(tf_path)
        finally:
            tf_path.unlink(missing_ok=True)
    else:
        info = rfa.read(family_path_or_bytes)

    usable = info.usable_in(target_year)
    if usable is not True:
        raise ValueError(
            f"Family {info.path.name} is not usable in Revit {target_year}: {info.describe(target_year)}"
        )
    return True


_rfa_2027_bytes = (
    rfa.OLE_MAGIC
    + b"\0" * 512
    + "Revit Build: Autodesk Revit 2027 (Build: 27.0.1)\nFormat: 2027".encode("utf-16-le")
    + b"\0" * 512
)
_rfa_2025_bytes = (
    rfa.OLE_MAGIC
    + b"\0" * 512
    + "Revit Build: Autodesk Revit 2025 (Build: 25.0.1)\nFormat: 2025".encode("utf-16-le")
    + b"\0" * 512
)

register_guard(
    fn=check_rfa_portable_compatibility,
    name="rfa_portable_compatibility",
    lesson_ids=("l0042-installed-native-revit", "l0042"),
    real_case=case(_rfa_2027_bytes, 2025),
    clean_case=case(_rfa_2025_bytes, 2025),
    expected_real=ValueError,
    expected_clean=True,
    tier=2,
    description="Validates Revit family version compatibility without Revit and rejects forward-incompatible files (l0042)",
)


# 63. l0200: Villa concept room reachability and link buildability
def check_villa_concept_reachability_and_links(layout: dict[str, Any]) -> dict[str, Any]:
    """Validates that room adjacency links can build real doors and all rooms are reachable (l0200)."""
    res = villa.critique(layout)
    failed = [
        c
        for c in res.get("checks", [])
        if c.get("check") in ("links_built", "reachability") and c.get("status") == "fail"
    ]
    if failed:
        raise ValueError(f"Villa concept reachability or links check failed: {failed}")
    return res


_lay_reach_bad = copy.deepcopy(villa.concept_a())
_lay_reach_bad["links"].append(["kids-a", "parents-bed"])

register_guard(
    fn=check_villa_concept_reachability_and_links,
    name="villa_concept_reachability_and_links",
    lesson_ids=("l0200-critic-caught-through", "l0200"),
    real_case=case(_lay_reach_bad),
    clean_case=case(villa.concept_a()),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that room adjacency links can build doors and all rooms remain reachable (l0200)",
)


# 64. l0209: Multi-level upper rooms supported by ground floor footprint
def check_concept_critic_upper_supported(layout: dict[str, Any]) -> dict[str, Any]:
    """Validates that upper level rooms are supported by ground floor footprint (l0209)."""
    res = critic.critique(layout)
    check = next((c for c in res.get("checks", []) if c.get("check") == "upper_supported"), None)
    if not check or check.get("status") == "fail":
        raise ValueError(f"Upper supported check failed: {check}")
    return check


_lay_upper_clean = {
    "id": "concept_upper_clean",
    "parti": "bar",
    "plot": {"width_m": 30.0, "depth_m": 40.0},
    "levels": {"L00": 0.0, "L01": 3.0},
    "entrance": "entry",
    "rooms": {
        "entry": {"level": "L00", "rect": [5.0, 5.0, 9.0, 9.0], "occupancy": "entrance"},
        "living": {"level": "L00", "rect": [9.0, 5.0, 15.0, 9.0], "occupancy": "living"},
        "bed-1": {"level": "L01", "rect": [5.0, 5.0, 9.0, 9.0], "occupancy": "bedroom"},
    },
    "links": [["entry", "living"]],
    "vertical": [],
}
_lay_upper_bad = copy.deepcopy(_lay_upper_clean)
_lay_upper_bad["rooms"]["bed-1"]["rect"] = [5.0, 5.0, 11.0, 11.0]

register_guard(
    fn=check_concept_critic_upper_supported,
    name="concept_critic_upper_supported",
    lesson_ids=("l0209-guards", "l0209"),
    real_case=case(_lay_upper_bad),
    clean_case=case(_lay_upper_clean),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that upper level rooms are supported by ground floor structure below (l0209)",
)


# 65. l0999, l0992: Window daylight brightness vs interior room luminance
def check_render_qa_window_brightness(
    view_median: float,
    room_p90: float,
    *,
    exterior_camera: bool = False,
) -> str:
    """Validates that daylight through windows exceeds room interior brightness (l0999, l0992)."""
    if exterior_camera:
        return "PASS"
    status = render_qa.window_brightness_status(view_median, room_p90)
    if status != "PASS":
        raise ValueError(
            f"Window brightness failed: view median {view_median:.2f} < room 90th percentile {room_p90:.2f}"
        )
    return status


register_guard(
    fn=check_render_qa_window_brightness,
    name="render_qa_window_brightness",
    lesson_ids=(
        "l0999-v01-interior-draft",
        "l0999",
        "l0992-v25-exterior-draft",
        "l0992",
    ),
    real_case=case(0.80, 0.81, exterior_camera=False),
    clean_case=case(0.85, 0.81, exterior_camera=False),
    expected_real=ValueError,
    expected_clean="PASS",
    tier=2,
    description="Validates daylight window view median brightness against interior room 90th percentile (l0999, l0992)",
)


# 66. l1004, l0555, l0682: Authored record fields override require reason and audit trail
def check_authored_values_override_audit(
    record: dict[str, Any],
    key: str,
    value: Any,
    reason: str,
) -> dict[str, Any]:
    """Validates that authored records cannot be overwritten without a reasoned audit chain (l1004, l0555, l0682)."""
    rec = copy.deepcopy(record)
    res = authored_values.override(rec, key, value, reason)
    unexplained = authored_guard.unexplained_changes(record, res, (key,))
    if unexplained:
        raise ValueError(f"Unexplained change detected for authored fields: {unexplained}")
    return res


_record_authored_clean = {"lens_mm": 16, "pinned_door": 21.847}

register_guard(
    fn=check_authored_values_override_audit,
    name="authored_values_override_audit",
    lesson_ids=(
        "l1004-later-pass-overwrote",
        "l1004",
        "l0555-pinned-doors-re",
        "l0555",
        "l0682-forcing-24-mm",
        "l0682",
    ),
    real_case=case(_record_authored_clean, "lens_mm", 24, ""),
    clean_case=case(_record_authored_clean, "lens_mm", 24, "camera normalisation"),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that authored fields require a non-empty audit reason to override without silent overwrites (l1004, l0555, l0682)",
)


# 67. l0018: Override requires an existing field rather than unauthored fallback creation
def check_authored_values_override_existing_field(
    record: dict[str, Any],
    key: str,
    value: Any,
    reason: str,
) -> dict[str, Any]:
    """Validates that override requires an existing field rather than fallback creation (l0018)."""
    rec = copy.deepcopy(record)
    return authored_values.override(rec, key, value, reason)


_record_missing_field = {"id": "item-01"}
_record_existing_field = {"id": "item-01", "comments": "authored-notes"}

register_guard(
    fn=check_authored_values_override_existing_field,
    name="authored_values_override_existing_field",
    lesson_ids=("l0018-falling-back-comments", "l0018"),
    real_case=case(_record_missing_field, "comments", "metadata", "fallback"),
    clean_case=case(_record_existing_field, "comments", "metadata", "explicit revision"),
    expected_real=KeyError,
    expected_clean=None,
    tier=2,
    description="Validates that override requires an existing authored field rather than fallback creation (l0018)",
)


# 68. l0528: Room route connectivity check
def check_villa_furnish_room_route_connectivity(
    items: list[dict[str, Any]] | None = None,
    lay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validates that room interior furniture does not sever circulation route connectivity (l0528)."""
    res = villa_furnish.check(items, lay)
    routes = res.get("routes", {})
    if routes.get("status") != "pass" or routes.get("problems"):
        raise ValueError(f"Room route connectivity check failed: {routes.get('problems')}")
    return routes


_items_route_conn_bad = copy.deepcopy(_cached_furnish_layout())
_by_id_route_conn = {it["id"]: it for it in _items_route_conn_bad}
_by_id_route_conn["ka-wardrobe"]["cx"] = 13.4

register_guard(
    fn=check_villa_furnish_room_route_connectivity,
    name="villa_furnish_room_route_connectivity",
    lesson_ids=("l0528-20-mm-grid", "l0528"),
    real_case=case(_items_route_conn_bad, _lay_d1_base),
    clean_case=case(_cached_furnish_layout(), _lay_d1_base),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that interior furniture arrangement maintains circulation route connectivity between doors and pieces (l0528)",
)


# 69. l0534: Coffee table clearance from seating
def check_villa_furnish_coffee_table_clearance(
    items: list[dict[str, Any]] | None = None,
    lay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validates that coffee tables maintain minimum required clearance (457 mm) from sofa fronts (l0534)."""
    res = villa_furnish.check(items, lay)
    clearances = res.get("clearances", {})
    if clearances.get("status") != "pass" or clearances.get("problems"):
        raise ValueError(f"Furniture clearance check failed: {clearances.get('problems')}")
    return clearances


_items_coffee_bad = copy.deepcopy(_cached_furnish_layout())
_by_id_coffee = {it["id"]: it for it in _items_coffee_bad}
_l_sofa = _by_id_coffee["lounge-sofa"]
_l_coffee = _by_id_coffee["lounge-coffee"]
_l_coffee["cy"] = _l_sofa["cy"] + _l_sofa["d"] / 2 + 0.44 + _l_coffee["d"] / 2

register_guard(
    fn=check_villa_furnish_coffee_table_clearance,
    name="villa_furnish_coffee_table_clearance",
    lesson_ids=("l0534-corner-not-side", "l0534"),
    real_case=case(_items_coffee_bad, _lay_d1_base),
    clean_case=case(_cached_furnish_layout(), _lay_d1_base),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that coffee tables maintain at least 457 mm clearance from seating fronts (l0534)",
)


# -----------------------------------------------------------------------------
# Phase 2 Batch 7: Render QA, Camera Intent, Lighting Tasks, Output Integrity & Plant Spacing
# -----------------------------------------------------------------------------

# 70. l0093, l0063: Camera verticals level check
_qa_sample_img_path = Path(tempfile.gettempdir()) / "archpipe_render_qa_sample.png"
if not _qa_sample_img_path.exists() or _qa_sample_img_path.stat().st_size == 0:
    _im_sample = Image.new("RGB", (20, 20), (128, 128, 128))
    _im_sample.putpixel((0, 0), (255, 255, 255))
    _im_sample.putpixel((0, 1), (255, 255, 255))
    for _k in range(5):
        _im_sample.putpixel((19, _k), (5, 5, 5))
    _im_sample.save(_qa_sample_img_path)


def check_render_qa_verticals_level(
    image_path: Path | str,
    qa: dict[str, Any],
) -> dict[str, Any]:
    """Validates that camera pitch maintains level verticals within tolerance (l0093, l0063)."""
    report = render_qa.check(image_path, qa)
    if "verticals_level" in report.get("failed", []):
        raise ValueError(f"Camera pitch departs from level: {report.get('failed')}")
    return report


_qa_verticals_bad = {
    "camera": {"pitch_deg": 81.0, "shift_y": 0.0},
}
_qa_verticals_clean = {
    "camera": {"pitch_deg": 90.0, "shift_y": -0.05},
}

register_guard(
    fn=check_render_qa_verticals_level,
    name="render_qa_verticals_level",
    lesson_ids=(
        "l0093-verticals-level-reported",
        "l0093",
        "l0063-walls-leaned",
        "l0063",
    ),
    real_case=case(_qa_sample_img_path, _qa_verticals_bad),
    clean_case=case(_qa_sample_img_path, _qa_verticals_clean),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that camera pitch maintains level verticals within tolerance (l0093, l0063)",
)


# 71. l0068: Light fixture photometry bound with measured IES
def check_render_qa_photometry_bound(
    image_path: Path | str,
    qa: dict[str, Any],
) -> dict[str, Any]:
    """Validates that all light fixtures in the render have bound measured IES photometry (l0068)."""
    report = render_qa.check(image_path, qa)
    if "photometry_bound" in report.get("failed", []):
        raise ValueError(f"Render fixtures missing measured IES photometry: {report.get('failed')}")
    return report


_qa_photometry_bad = {
    "lights": {"on": True, "count": 5, "with_ies": 0},
}
_qa_photometry_clean = {
    "lights": {"on": True, "count": 5, "with_ies": 5},
}

register_guard(
    fn=check_render_qa_photometry_bound,
    name="render_qa_photometry_bound",
    lesson_ids=("l0068-fixtures-rendered-as", "l0068"),
    real_case=case(_qa_sample_img_path, _qa_photometry_bad),
    clean_case=case(_qa_sample_img_path, _qa_photometry_clean),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that all active render light fixtures have bound measured IES photometry (l0068)",
)


# 72. l0731: Camera view intent subject framing
def check_render_views_subject_framing(
    layout: dict[str, Any],
    room: str,
    subjects: list[str],
    lens_mm: float = 24.0,
    sp: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validates that chosen camera view frames all declared subjects within sensor bounds (l0731)."""
    res = render_views.choose(layout, room, subjects, lens_mm=lens_mm, sp=sp)
    if not res.get("subjects_in_frame"):
        raise ValueError(
            f"Subjects not in frame for {room} with {lens_mm}mm lens: "
            f"framed_candidates={res.get('framed_candidates')}"
        )
    return res


register_guard(
    fn=check_render_views_subject_framing,
    name="render_views_subject_framing",
    lesson_ids=("l0731-hand-typed-cameras", "l0731"),
    real_case=case(_lay_d1_base, "family-bath", ["fb-wc"], 24.0),
    clean_case=case(_lay_d1_base, "family-bath", ["fb-wc"], 16.0),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that chosen camera view frames all declared subjects within sensor bounds (l0731)",
)


# 73. l0689, l0874: Kitchen prep task illuminance target
def check_villa_lighting_prep_task(
    lay: dict[str, Any] | None = None,
    fixtures: list[Any] | None = None,
) -> list[dict[str, Any]]:
    """Validates kitchen prep task illuminance target (ies-res-kitchen-prep-500) (l0689, l0874)."""
    res = villa_lighting.check(lay, fixtures)
    failed_prep = [
        t for t in res.get("tasks", [])
        if t.get("card") == "ies-res-kitchen-prep-500" and t.get("status") == "fail"
    ]
    if failed_prep:
        raise ValueError(f"Kitchen prep task illumination check failed: {failed_prep}")
    return failed_prep


_fx_lighting_no_prep = [
    f for f in _fx_lighting_clean
    if not (f.kind == "DLN" and f.room == "kitchen")
]

register_guard(
    fn=check_villa_lighting_prep_task,
    name="villa_lighting_prep_task_illuminance",
    lesson_ids=(
        "l0689-lighting-negative-test",
        "l0689",
        "l0874-per-point-recomputation",
        "l0874",
    ),
    real_case=case(_lay_d1_base, _fx_lighting_no_prep),
    clean_case=case(_lay_d1_base, _fx_lighting_clean),
    expected_real=ValueError,
    expected_clean=[],
    tier=2,
    description="Validates kitchen prep task illuminance target fails closed when task downlights are omitted (l0689, l0874)",
)


# 74. l0089, l0133: Stage result output integrity check
def check_stage_result_output_integrity(
    record_or_path: dict[str, Any] | Path | str,
    root: Path | str | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    """Validates that stage result outputs match recorded SHA-256 digests without modification (l0089, l0133)."""
    return stage_result.validate_stage_result(
        record_or_path,
        root=root,
        raise_on_error=True,
    )


_record_tampered_output = copy.deepcopy(_record_clean)
_record_tampered_output["outputs"]["spec/villa-site.yaml"]["sha256"] = "0" * 64

register_guard(
    fn=check_stage_result_output_integrity,
    name="stage_result_output_integrity",
    lesson_ids=(
        "l0089-another-session-edited",
        "l0089",
        "l0133-open-right-after",
        "l0133",
    ),
    real_case=case(_record_tampered_output),
    clean_case=case(_record_clean),
    expected_real=stage_result.IncompleteOutputError,
    expected_clean=None,
    tier=2,
    description="Validates stage result output file integrity, failing closed when outputs are modified or tampered on disk (l0089, l0133)",
)


# 75. l0741: Landscape plant neighbour spacing
def check_villa_landscape_plant_spacing(
    plants: list[dict[str, Any]],
) -> list[tuple[str, str, float, float]]:
    """Validates that planting arrangements maintain minimum neighbour spacing (l0741)."""
    violations = villa_landscape.spacing_violations(plants)
    if violations:
        raise ValueError(f"Landscape plant spacing violations: {violations}")
    return violations


_plants_spacing_bad = [
    {"id": "plant-a", "bed": "east", "layer": "mid", "spread_m": 0.9, "center": (27.0, -25.0)},
    {"id": "plant-b", "bed": "east", "layer": "mid", "spread_m": 0.9, "center": (27.0, -24.73)},
]
_plants_spacing_clean = [
    {"id": "plant-a", "bed": "east", "layer": "mid", "spread_m": 0.9, "center": (27.0, -25.0)},
    {"id": "plant-b", "bed": "east", "layer": "mid", "spread_m": 0.9, "center": (27.0, -24.20)},
]

register_guard(
    fn=check_villa_landscape_plant_spacing,
    name="villa_landscape_plant_spacing",
    lesson_ids=("l0741-plants-placed-without", "l0741"),
    real_case=case(_plants_spacing_bad),
    clean_case=case(_plants_spacing_clean),
    expected_real=ValueError,
    expected_clean=[],
    tier=2,
    description="Validates that landscape plants maintain required minimum spacing (0.8 * max spread) between neighbours (l0741)",
)


# 76. l0013: Furniture placement clear of structural columns
def check_villa_furnish_column_clearance(
    items: list[dict[str, Any]] | None = None,
    lay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validates that placed furniture items do not clash with structural columns (l0013)."""
    res = villa_furnish.check(items, lay)
    col = res.get("columns", {})
    if col.get("status") != "pass" or col.get("problems"):
        raise ValueError(f"Furniture piece clashes with structural column: {col.get('problems')}")
    return col


_items_column_bad = copy.deepcopy(_cached_furnish_layout())
next(i for i in _items_column_bad if i["id"] == "kb-desk")["cx"] = 15.0

register_guard(
    fn=check_villa_furnish_column_clearance,
    name="villa_furnish_column_clearance",
    lesson_ids=("l0013-dropping-unknown-chairs", "l0013"),
    real_case=case(_items_column_bad, _lay_d1_base),
    clean_case=case(_cached_furnish_layout(), _lay_d1_base),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that placed furniture pieces do not clash with structural columns (l0013)",
)


# -----------------------------------------------------------------------------
# Phase 2 Batch 8: Stair / Opening / Route Geometry, Revit Mounting & Lighting
# -----------------------------------------------------------------------------

# 77. l0856: Handrail mounting to finished face
def check_mounting_handrail_finished_face(
    mesh: dict[str, Any],
    hosts: dict[str, Any],
) -> list[str]:
    """Validates that wall handrails are mounted clear of plaster face within tolerance (l0856)."""
    errors = mounting.check_mesh(mesh, hosts)
    if errors:
        raise ValueError(f"Mounting finished-face error: {errors}")
    return errors


_host_l0856 = mounting.Host(
    "historic-wall", "wall", (0, -28.471, 0), (0, 1, 0), mounting.Finish("historic-modeled-face", 0)
)
_rail_l0856_bad = dict(
    id="frozen-l0856",
    part_kind="handrail",
    faces=[
        [[5.317, -28.611, 0.70], [9.517, -28.611, -1.95],
         [9.517, -28.581, -1.95], [5.317, -28.581, 0.70]]
    ],
)
_rail_l0856_bad["mounting"] = mounting.binding(
    mounting.MountItem(_rail_l0856_bad["id"]), _host_l0856, 0.085, "wall-hung"
)

_rail_l0856_clean = dict(
    id="clean-l0856",
    part_kind="handrail",
    faces=[
        [[5.317, -28.386, 0.70], [9.517, -28.386, -1.95],
         [9.517, -28.356, -1.95], [5.317, -28.356, 0.70]]
    ],
)
_rail_l0856_clean["mounting"] = mounting.binding(
    mounting.MountItem(_rail_l0856_clean["id"]), _host_l0856, 0.085, "wall-hung"
)

register_guard(
    fn=check_mounting_handrail_finished_face,
    name="mounting_handrail_finished_face",
    lesson_ids=("l0856-stair-s-wall", "l0856"),
    real_case=case(_rail_l0856_bad, {_host_l0856.id: _host_l0856}),
    clean_case=case(_rail_l0856_clean, {_host_l0856.id: _host_l0856}),
    expected_real=ValueError,
    expected_clean=[],
    tier=2,
    description="Validates that stair wall handrails are mounted clear of plaster face within 1 mm tolerance (l0856)",
)


# 78. l0099: Authored design dimensions preserved without unexplained modifications
def check_authored_guard_unexplained_changes(
    declared: dict[str, Any],
    written: dict[str, Any],
    fields: tuple[str, ...],
) -> list[str]:
    """Validates that authored fields are preserved without unexplained changes or silent defaults (l0099)."""
    changes = authored_guard.unexplained_changes(declared, written, fields)
    if changes:
        raise ValueError(f"Authored fields modified without explanation: {changes}")
    return changes


_declared_dim_clean = {"mounting_height": 0, "ceiling_height": 2700}
_written_dim_bad = {"mounting_height": 2400, "ceiling_height": 2700}
_written_dim_clean = {
    "mounting_height": 2400,
    "ceiling_height": 2700,
    "overrides": [
        {"field": "mounting_height", "prior": 0, "new": 2400, "reason": "ADR-0012 updated mounting height"}
    ],
}

register_guard(
    fn=check_authored_guard_unexplained_changes,
    name="authored_guard_unexplained_changes",
    lesson_ids=("l0099-design-dimensions-silent", "l0099"),
    real_case=case(_declared_dim_clean, _written_dim_bad, ("mounting_height", "ceiling_height")),
    clean_case=case(_declared_dim_clean, _written_dim_clean, ("mounting_height", "ceiling_height")),
    expected_real=ValueError,
    expected_clean=[],
    tier=2,
    description="Validates that authored dimensions cannot be modified or defaulted without an override audit trail (l0099)",
)


# 79. l0830: View subject existence and frameability in layout
def check_render_views_subject_presence(
    layout: dict[str, Any],
    room: str,
    subjects: list[str],
    lens_mm: float = 24.0,
    sp: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validates that declared view subjects exist and are frameable within the room layout (l0830)."""
    items = {i["id"]: i for i in villa_furnish.layout(layout)}
    missing = [s for s in subjects if s not in items and not s.startswith("detail-")]
    if missing:
        raise ValueError(f"View subjects not found in room layout: {missing}")
    res = render_views.choose(layout, room, subjects, lens_mm=lens_mm, sp=sp)
    if not res.get("subjects_in_frame"):
        raise ValueError(f"View subjects not in frame for room '{room}': {subjects}")
    return res


register_guard(
    fn=check_render_views_subject_presence,
    name="render_views_subject_presence",
    lesson_ids=("l0830-view-subject-can", "l0830"),
    real_case=case(_lay_d1_base, "parents-dressing", ["historical-stale-wardrobe"], 24.0, _cached_spec()),
    clean_case=case(_lay_d1_base, "parents-dressing", ["pd-hang-1"], 24.0, _cached_spec()),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that declared view subjects exist in layout and are fully in frame (l0830)",
)


# 80. l0973: Camera proximity to prop foliage canopies
def check_villa_landscape_camera_canopy_clearance(
    camera_pos: tuple[float, float, float] | list[float],
    prop: dict[str, Any],
    min_clearance_m: float = 1.0,
) -> float:
    """Validates that a camera does not stand inside or within clearance distance of a prop canopy (l0973)."""
    px, py, pz = camera_pos
    x0, y0, z0, x1, y1, z1 = villa_landscape.prop_world_box(
        prop["asset"],
        prop["position"],
        prop.get("rotation_deg", [0, 0, 0]),
        prop.get("scale", 1.0),
    )
    dist = math.sqrt(sum(d * d for d in (
        max(x0 - px, 0, px - x1),
        max(y0 - py, 0, py - y1),
        max(z0 - pz, 0, pz - z1),
    )))
    if dist < min_clearance_m:
        raise ValueError(
            f"Camera at ({px:.2f}, {py:.2f}, {pz:.2f}) stands within {dist:.3f} m "
            f"of prop canopy '{prop.get('id', prop['asset'])}' (minimum clearance {min_clearance_m:.2f} m)"
        )
    return dist


_prop_top_olive = villa_landscape._prop(
    "landscape-top-olive", "sf_olive_old", (14.10, -22.10), 0.0, 2.00, "olive"
)

register_guard(
    fn=check_villa_landscape_camera_canopy_clearance,
    name="villa_landscape_camera_canopy_clearance",
    lesson_ids=("l0973-v26-camera-stood", "l0973"),
    real_case=case([14.5, -22.0, 1.35], _prop_top_olive, 1.0),
    clean_case=case([9.0, -20.80, 1.35], _prop_top_olive, 1.0),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that camera positions maintain minimum clearance from prop foliage canopies (l0973)",
)


# 81. l0984: Under-stair storage joinery presence and soffit clearance
def check_villa_furnish_under_stair_storage_profile(
    items: list[dict[str, Any]] | None = None,
    lay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validates that under-stair storage casework and modules are present and fit the stair soffit (l0984)."""
    res = villa_furnish.check(items, lay)
    chk = res.get("under_stair_storage", {})
    if chk.get("status") != "pass" or chk.get("problems"):
        raise ValueError(f"Under-stair storage check failed: {chk.get('problems')}")
    return chk


_items_no_stair_store = [
    it for it in _cached_furnish_layout()
    if it["id"] != "stair-flight-store"
]

register_guard(
    fn=check_villa_furnish_under_stair_storage_profile,
    name="villa_furnish_under_stair_storage_profile",
    lesson_ids=("l0984-v29-missed-under", "l0984"),
    real_case=case(_items_no_stair_store, _lay_d1_base),
    clean_case=case(_cached_furnish_layout(), _lay_d1_base),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that under-stair storage modules are present and fit within stair soffit headroom (l0984)",
)


# 82. l0989: Maintained illuminance for windowless storage rooms
def check_villa_lighting_windowless_store_target(
    lay: dict[str, Any] | None = None,
    fixtures: list[Any] | None = None,
) -> dict[str, Any]:
    """Validates that windowless storage rooms achieve maintained illuminance targets (ies-res-storage-frequent-50) (l0989)."""
    res = villa_lighting.check(lay, fixtures)
    store_room = next((r for r in res.get("rooms", []) if r.get("room") == "store-ramp"), None)
    if store_room is None:
        raise ValueError("Room 'store-ramp' not found in lighting check")
    if store_room.get("avg_floor_lx_direct", 0.0) < store_room.get("required_lx", 50.0):
        raise ValueError(
            f"Store room illuminance {store_room.get('avg_floor_lx_direct')} lx is below required "
            f"{store_room.get('required_lx')} lx"
        )
    return store_room


_fx_lighting_no_store = [
    f for f in _fx_lighting_clean
    if f.room != "store-ramp"
]

register_guard(
    fn=check_villa_lighting_windowless_store_target,
    name="villa_lighting_windowless_store_target",
    lesson_ids=("l0989-v30-read-black", "l0989"),
    real_case=case(_lay_d1_base, _fx_lighting_no_store),
    clean_case=case(_lay_d1_base, _fx_lighting_clean),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that windowless storage rooms achieve required maintained lux target (ies-res-storage-frequent-50) (l0989)",
)


# -----------------------------------------------------------------------------
# Phase 2, Batch 9: Evidence Integrity & Execution Context Boundaries
# -----------------------------------------------------------------------------

# 83. l0020: Scope promotion guard (isolated room is not a dwelling)
def check_evidence_scope_promotion(
    record: EvidenceRecord,
    target_scope: str,
) -> EvidenceRecord:
    """Validates that a room-scoped evidence record cannot widen silently to dwelling scope (l0020)."""
    return evidence.EvidenceRecord.apply_to(record, target_scope)


_rec_bedroom_lux = EvidenceRecord(
    value={"maintained_lux": 320},
    status=EvidenceStatus.VERIFIED,
    source=SourceRef(title="Bedroom Lighting Calc", verified=True),
    scope="room",
)

register_guard(
    fn=check_evidence_scope_promotion,
    name="evidence_scope_promotion",
    lesson_ids=("l0020-isolated-room-not", "l0020"),
    real_case=case(_rec_bedroom_lux, "dwelling"),
    clean_case=case(_rec_bedroom_lux, "room"),
    expected_real=ScopeWideningError,
    expected_clean=None,
    tier=2,
    description="Validates that a room-scoped evidence record cannot widen silently to dwelling scope (l0020)",
)


# 84. l0092: Dressing and stand-in combination guard (ASSUMED items weaken composite status)
def check_evidence_composition_verified(
    *records: EvidenceRecord,
    value: Any = None,
) -> EvidenceRecord:
    """Validates that composite evidence records achieve VERIFIED status without assumed stand-ins (l0092)."""
    res = evidence.combine(*records, value=value)
    if res.status != EvidenceStatus.VERIFIED:
        raise ValueError(
            f"Composite evidence status is {res.status.value}, expected VERIFIED: {res.reasons}"
        )
    return res


_rec_bed_design = EvidenceRecord(
    value={"name": "bed_king", "width_mm": 1930, "depth_mm": 2030},
    status=EvidenceStatus.VERIFIED,
    source=SourceRef(title="Revit Model Extract", edition="2027", verified=True),
    scope="room:bedroom",
)
_rec_table_design = EvidenceRecord(
    value={"name": "bedside_table", "width_mm": 500, "depth_mm": 450},
    status=EvidenceStatus.VERIFIED,
    source=SourceRef(title="Revit Model Extract", edition="2027", verified=True),
    scope="room:bedroom",
)
_rec_vase_assumed = EvidenceRecord(
    value={"name": "decor_vase", "bounds_m": [0.2, 0.3, 0.2]},
    status=EvidenceStatus.ASSUMED,
    source=SourceRef(title="Procedural Stand-in", verified=False),
    scope="room:bedroom",
    reasons=("Invented dressing stand-in, not design content (l0092)",),
)

register_guard(
    fn=check_evidence_composition_verified,
    name="evidence_composition_verified",
    lesson_ids=("l0092-invented-dressing-stand", "l0092"),
    real_case=case(_rec_bed_design, _rec_table_design, _rec_vase_assumed, value="bedroom_furnishing_cluster"),
    clean_case=case(_rec_bed_design, _rec_table_design, value="bedroom_furnishing_cluster"),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that composite evidence records achieve VERIFIED status without assumed stand-ins (l0092)",
)


# 85. l0661: Shared model hash agreement between render and daylight analysis
def check_evidence_shared_model(
    model_sha256_render: str,
    model_sha256_analysis: str,
) -> dict[str, Any]:
    """Validates that daylight analysis and rendering describe the same model hash (l0661)."""
    res = evidence.check_shared_model(model_sha256_render, model_sha256_analysis)
    if not res.get("matches"):
        raise ValueError(res.get("reason", "Model hashes disagree"))
    return res


_hash_render_case = "a" * 64
_hash_analysis_diff = "b" * 64

register_guard(
    fn=check_evidence_shared_model,
    name="evidence_shared_model",
    lesson_ids=("l0661-render-daylight-analysis", "l0661"),
    real_case=case(_hash_render_case, _hash_analysis_diff),
    clean_case=case(_hash_render_case, _hash_render_case),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that daylight analysis and rendering describe the same model hash (l0661)",
)


# 86. l0763: Render-side compensation vs design spec consistency
def check_evidence_render_vs_design(
    design_value: float,
    render_value: float,
    tolerance: float = 0.001,
) -> dict[str, Any]:
    """Validates that render-side adjustments do not diverge from the design model (l0763)."""
    res = evidence.check_render_vs_design(design_value, render_value, tolerance=tolerance)
    if not res.get("matches"):
        raise ValueError(res.get("reason", "Render-side fix diverges from design"))
    return res


_design_fitting_z = 2545.0
_render_fitting_z = 2700.0

register_guard(
    fn=check_evidence_render_vs_design,
    name="evidence_render_vs_design",
    lesson_ids=("l0763-render-side-fix", "l0763"),
    real_case=case(_design_fitting_z, _render_fitting_z, tolerance=1.0),
    clean_case=case(_render_fitting_z, _render_fitting_z, tolerance=1.0),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that render-side adjustments do not diverge from the design model (l0763)",
)


# 87. l0009: Strict absolute path requirements for execution boundaries
def check_execution_context_absolute_path(
    path: Path | str,
    label: str = "script",
    *,
    file: bool = True,
) -> Path:
    """Validates that script and tool execution paths are strictly absolute (l0009)."""
    return execution_context.absolute(path, label, file=file)


register_guard(
    fn=check_execution_context_absolute_path,
    name="execution_context_absolute_path",
    lesson_ids=("l0009-relative-script-path", "l0009"),
    real_case=case(Path("revit/build_bedroom.py"), "script", file=True),
    clean_case=case(ROOT / "scripts/verify.py", "script", file=True),
    expected_real=ContextError,
    expected_clean=None,
    tier=2,
    description="Validates that script and tool execution paths are strictly absolute (l0009)",
)


# 88. l0076: Required agent roles presence in live session context
_test_ctx_out = Path(tempfile.gettempdir()) / "archpipe_ctx_out"
_test_ctx_tmp = Path(tempfile.gettempdir()) / "archpipe_ctx_tmp"


def check_execution_context_roles(
    required_roles: Iterable[str],
    available_roles: Iterable[str],
    *,
    root: Path = ROOT,
    output: Path | None = None,
    temp: Path | None = None,
) -> dict[str, Any]:
    """Validates that required agent roles are present in the live session (l0076)."""
    out_dir = output or _test_ctx_out
    tmp_dir = temp or _test_ctx_tmp
    return execution_context.preflight(
        root=root,
        output=out_dir,
        temp=tmp_dir,
        required_roles=tuple(required_roles),
        available_roles=tuple(available_roles),
    )


register_guard(
    fn=check_execution_context_roles,
    name="execution_context_roles",
    lesson_ids=("l0076-project-s-agents", "l0076"),
    real_case=case(["render_critic"], []),
    clean_case=case(["render_critic"], ["render_critic"]),
    expected_real=ContextError,
    expected_clean=None,
    tier=2,
    description="Validates that required agent roles are present in the live session (l0076)",
)


# 89. l0134: Python dependency verification without import side-effects
def check_execution_context_dependencies(
    modules: Iterable[str],
    *,
    root: Path = ROOT,
    interpreter: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Validates that declared Python dependencies can be located without import side-effects (l0134)."""
    return execution_context.check_dependencies(modules, root=root, interpreter=interpreter)


register_guard(
    fn=check_execution_context_dependencies,
    name="execution_context_dependencies",
    lesson_ids=("l0134-tests-could-not", "l0134"),
    real_case=None,
    clean_case=None,
    expected_real=None,
    expected_clean=None,
    tier=2,
    description="Validates that declared Python dependencies can be located without import side-effects (l0134)",
    notes="needs real case: the recorded failure is a Windows PYTHONPATH joined with ':' instead of ';' "
          "(docs/LEARNINGS.md 'could not import archpipe'); a made-up module name is a sibling, not that case "
          "(lead review of batch 9, 2026-10-08)",
    needs_real_case=True,
)



# -----------------------------------------------------------------------------
# Phase 2, Batch 10: External Claims Ingestion & Stage Result Proofs
# -----------------------------------------------------------------------------

# 90. l0122: Manifest and catalogue crawl completeness verification
def check_external_claims_manifest_completeness(
    expected_count: int,
    received_count: int,
    label: str = "Manifest",
    min_coverage_ratio: float = 1.0,
) -> None:
    """Validates that catalogue crawl or manifest contains all expected items without shortfall (l0122)."""
    return external_claims.assert_manifest_complete(
        expected_count, received_count, label=label, min_coverage_ratio=min_coverage_ratio
    )


register_guard(
    fn=check_external_claims_manifest_completeness,
    name="external_claims_manifest_completeness",
    lesson_ids=("l0122-catalogue-crawl-lost", "l0122"),
    real_case=case(381, 223, label="Luminaire Catalogue Crawl"),
    clean_case=case(381, 381, label="Luminaire Catalogue Crawl"),
    expected_real=CompletenessShortfallError,
    expected_clean=None,
    tier=2,
    description="Validates that catalogue crawl or manifest contains all expected items without shortfall (l0122)",
)


# 91. l0191: Search query relevance and nonsense query filtering
def check_external_claims_search_relevance(
    query: str,
    text: str,
) -> EvidenceRecord:
    """Validates that search results satisfy term relevance thresholds to prevent spurious hits (l0191)."""
    return external_claims.check_search_relevance(query, text)


register_guard(
    fn=check_external_claims_search_relevance,
    name="external_claims_search_relevance",
    lesson_ids=("l0191-fallback-then-returned", "l0191"),
    real_case=case(
        "xylophonic quasar marmalade",
        "The breakfast dining table is served with toast and citrus marmalade preserve.",
    ),
    clean_case=case(
        "overheating criteria operative temperature",
        "Thermal comfort assessment relies on criteria for operative temperature to prevent summer overheating in residential rooms.",
    ),
    expected_real=EvidenceStatus.UNVERIFIED,
    expected_clean=EvidenceStatus.VERIFIED,
    tier=2,
    description="Validates that search results satisfy term relevance thresholds to prevent spurious hits (l0191)",
)


# 92. l0120: Destination isolation from deployed asset repositories
_safe_temp_dir_l0120 = Path(tempfile.gettempdir()) / "archpipe_safe_dest_check"
_safe_temp_dest_l0120 = _safe_temp_dir_l0120 / "test.ies"


def check_external_claims_safe_destination(
    dest: Path | str,
    forbidden_roots: list[Path] | None = None,
    allowed_roots: list[Path] | None = None,
) -> Path:
    """Validates that output destinations are isolated from deployed asset stores (l0120)."""
    return external_claims.check_safe_destination(
        dest, forbidden_roots=forbidden_roots, allowed_roots=allowed_roots
    )


register_guard(
    fn=check_external_claims_safe_destination,
    name="external_claims_safe_destination",
    lesson_ids=("l0120-unit-test-exported", "l0120"),
    real_case=case(ROOT / "assets/user/luminaires/signify/test_sku/test.ies"),
    clean_case=case(_safe_temp_dest_l0120, allowed_roots=[_safe_temp_dir_l0120]),
    expected_real=UnsafeDestinationError,
    expected_clean=None,
    tier=2,
    description="Validates that output destinations are isolated from deployed asset stores (l0120)",
)


# 93. l0287: Non-zero exit code or failed status stage result refusal
def check_stage_result_failed_exit_refusal(
    record_or_path: dict[str, Any] | Path | str,
    root: Path | str | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    """Validates that stage results with failed status or non-zero exit refuse consumption (l0287)."""
    return stage_result.validate_stage_result(
        record_or_path,
        root=root,
        raise_on_error=True,
    )


_record_l0287_failed: dict[str, Any] = {
    "stage": "expensive_simulation_stage",
    "status": "fail",
    "exit_code": 1,
    "completeness": {"complete": True, "missing_outputs": [], "empty_outputs": []},
    "inputs": {},
    "outputs": {},
}
_record_l0287_clean: dict[str, Any] = {
    "stage": "expensive_simulation_stage",
    "status": "ok",
    "exit_code": 0,
    "completeness": {"complete": True, "missing_outputs": [], "empty_outputs": []},
    "inputs": {},
    "outputs": {},
}

register_guard(
    fn=check_stage_result_failed_exit_refusal,
    name="stage_result_failed_exit_refusal",
    lesson_ids=("l0287-slow-session-persist", "l0287"),
    real_case=None,
    clean_case=None,
    expected_real=None,
    expected_clean=None,
    tier=2,
    description="Validates that stage results with failed status or non-zero exit refuse consumption (l0287)",
    notes="needs real case: l0287's recorded failure is losing an expensive Revit upgrade because serialisation failed before the result was saved (docs/LEARNINGS.md 'persist the expensive result first'); a failed exit status is a different lesson (lead review of batch 10, 2026-10-08)",
    needs_real_case=True,
)


# 94. l0619: Render job upstream input staleness invalidation
def check_stage_result_stale_upstream_source(
    record_or_path: dict[str, Any] | Path | str,
    root: Path | str | None = None,
    current_inputs: Iterable[Path | str] | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    """Validates that render jobs fail closed when upstream source inputs have changed (l0619)."""
    return stage_result.validate_stage_result(
        record_or_path,
        root=root,
        current_inputs=current_inputs,
        raise_on_error=True,
    )


_record_l0619_stale = copy.deepcopy(_record_clean)
_record_l0619_stale["inputs"]["spec/villa-site.yaml"]["sha256"] = "a" * 64

register_guard(
    fn=check_stage_result_stale_upstream_source,
    name="stage_result_stale_upstream_source",
    lesson_ids=("l0619-render-job-resumed", "l0619"),
    real_case=None,
    clean_case=None,
    expected_real=None,
    expected_clean=None,
    tier=2,
    description="Validates that render jobs fail closed when upstream source inputs have changed (l0619)",
    notes="needs real case: l0619's recorded failure is a resumed render whose job id hashed the scene and IES files but not the renderer (docs/LEARNINGS.md 'A render job resumed a stale result'); a tampered input digest is a sibling (lead review of batch 10, 2026-10-08)",
    needs_real_case=True,
)



# -----------------------------------------------------------------------------
# Phase 2, Batch 11: Execution Context & Evidence Boundaries
# -----------------------------------------------------------------------------

# 95. l0015: Temporary directory writability in restricted sandbox environments
def check_execution_context_writable_directory(
    path: Path | str,
    label: str = "temporary directory",
) -> Path:
    """Validates that execution context directories are writable, readable, and removable (l0015)."""
    return execution_context.writable_directory(path, label)


register_guard(
    fn=check_execution_context_writable_directory,
    name="execution_context_writable_directory",
    lesson_ids=("l0015-python-3-14", "l0015"),
    real_case=None,
    clean_case=None,
    expected_real=None,
    expected_clean=None,
    tier=2,
    description="Validates that execution context directories are writable, readable, and removable (l0015)",
    notes="needs real case: l0015's recorded failure is a Python 3.14 sandbox environment where tempfile.mkdtemp created a directory under out/tmp that child processes could not write into (docs/LEARNINGS.md line 182); live OS sandbox permissions cannot be reproduced statically as a frozen file without OS container isolation",
    needs_real_case=True,
)


# 96. l0031: Non-interactive stdin for child tool processes under Windows protocol servers
def check_execution_context_noninteractive_stdin(
    tool: execution_context.Tool,
    env: dict[str, str],
    cwd: Path,
) -> dict[str, Any]:
    """Validates that external tool probing runs with non-interactive stdin (l0031)."""
    return execution_context.resolve_tool(tool, env, cwd)


register_guard(
    fn=check_execution_context_noninteractive_stdin,
    name="execution_context_noninteractive_stdin",
    lesson_ids=("l0031-windows-python-3", "l0031"),
    real_case=None,
    clean_case=None,
    expected_real=None,
    expected_clean=None,
    tier=2,
    description="Validates that external tool probing runs with non-interactive stdin (l0031)",
    notes="needs real case: l0031's recorded failure is a non-interactive subprocess inheriting the live MCP protocol stdin pipe under Python 3.14.7 on Windows and hanging on lock acquisition (docs/LEARNINGS.md line 198); live process stdin pipe inheritance cannot be frozen statically as a file",
    needs_real_case=True,
)


# 97. l0135: Explicit Python interpreter path resolution avoiding bash PATH confusion
def check_execution_context_python_interpreter_path(
    modules: Iterable[str],
    *,
    root: Path = ROOT,
    interpreter: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Validates that declared Python dependencies locate the correct interpreter without bash PATH confusion (l0135)."""
    return execution_context.check_dependencies(modules, root=root, interpreter=interpreter)


register_guard(
    fn=check_execution_context_python_interpreter_path,
    name="execution_context_python_interpreter_path",
    lesson_ids=("l0135-python-not-found", "l0135"),
    real_case=None,
    clean_case=None,
    expected_real=None,
    expected_clean=None,
    tier=2,
    description="Validates that declared Python dependencies locate the correct interpreter without bash PATH confusion (l0135)",
    notes="needs real case: l0135's recorded failure is invoking 'python' from bash on Windows where .venv is not on the bash PATH (docs/LEARNINGS.md line 302); shell PATH absence is an OS shell process state, not a static fixture",
    needs_real_case=True,
)


# 98. l0622: Fresh artifact verification on zero-exit child processes
def check_execution_context_fresh_artifact_check(
    argv: list[str],
    *,
    context: dict[str, Any],
    scripts: list[Path | str],
    record: Path,
    expected: Path | None = None,
) -> Any:
    """Validates that native tool commands produce fresh output artifacts upon exit zero (l0622)."""
    return execution_context.run_checked(argv, context=context, scripts=scripts, record=record, expected=expected)


register_guard(
    fn=check_execution_context_fresh_artifact_check,
    name="execution_context_fresh_artifact_check",
    lesson_ids=("l0622-blender-exited-0", "l0622"),
    real_case=None,
    clean_case=None,
    expected_real=None,
    expected_clean=None,
    tier=2,
    description="Validates that native tool commands produce fresh output artifacts upon exit zero (l0622)",
    notes="needs real case: l0622's recorded failure is Blender exiting 0 after a Python exception during mesh construction with keyhole polygons, producing no render image (docs/LEARNINGS.md lines 789-791); running external Blender binary with crash reproduction is not frozen as a static fixture",
    needs_real_case=True,
)


# 99. l0030: Handedness/swing assumption demotion guard
def check_evidence_door_swing_certification(
    door_extract: EvidenceRecord,
    room_geometry: EvidenceRecord,
) -> EvidenceRecord:
    """Validates that door swing extract achieves VERIFIED status without provisional handedness assumptions (l0030)."""
    res = evidence.combine(door_extract, room_geometry, value="door_swing_certification")
    if res.status != EvidenceStatus.VERIFIED:
        raise ValueError(
            f"Door swing evidence status is {res.status.value}, expected VERIFIED (l0030): {res.reasons}"
        )
    return res


_rec_door_extract_assumed_l0030 = EvidenceRecord(
    value={"door_id": "D-01", "family": "Single-Flush", "swing": "left", "handedness": "assumed_default_left"},
    status=EvidenceStatus.ASSUMED,
    source=SourceRef(
        title="Revit Model Extract",
        edition="2027",
        verified=False,
        notes="Extract lacks actual hinge/facing handedness; adapter uses default left hinge (l0030)",
    ),
    scope="room:bedroom",
    reasons=("Provisional handedness assumption: extract lacks hinge/facing handedness (l0030)",),
)
_rec_door_extract_verified_l0030 = EvidenceRecord(
    value={"door_id": "D-01", "family": "Single-Flush", "swing": "left", "handedness": "left_hand_reverse"},
    status=EvidenceStatus.VERIFIED,
    source=SourceRef(
        title="Revit Native View Extract",
        edition="2027",
        verified=True,
        notes="Handedness extracted from authored native view (l0030)",
    ),
    scope="room:bedroom",
)
_rec_room_geometry_verified_l0030 = EvidenceRecord(
    value={"room": "bedroom", "width_mm": 4200, "length_mm": 5100},
    status=EvidenceStatus.VERIFIED,
    source=SourceRef(title="Revit Model Extract", edition="2027", verified=True),
    scope="room:bedroom",
)

register_guard(
    fn=check_evidence_door_swing_certification,
    name="evidence_door_swing_certification",
    lesson_ids=("l0030-current-extract-lacks", "l0030"),
    real_case=case(_rec_door_extract_assumed_l0030, _rec_room_geometry_verified_l0030),
    clean_case=case(_rec_door_extract_verified_l0030, _rec_room_geometry_verified_l0030),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Validates that door swing extract achieves VERIFIED status without provisional handedness assumptions (l0030)",
)



# -----------------------------------------------------------------------------
# Pre-registered Tier-3 review steps
# -----------------------------------------------------------------------------

# Moment A: Fact-Finding and Client Intent
register_review_step(
    name="review_client_brief_ownership",
    lesson_ids=("l0645-document-taken-as", "l0645"),
    text="Verify that brief documents and design targets are explicitly confirmed and owned by the client rather than adopted unconfirmed.",
    location="docs/review-steps.md#moment-a-fact-finding-and-client-intent",
    reviewer="lead",
    notes="A document was taken as the client's brief without the client owning it.",
)

register_review_step(
    name="review_existing_wall_survey_confirmation",
    lesson_ids=("l0415-wall-position-assumed", "l0415"),
    text="Verify that existing boundary and party wall positions and thicknesses are confirmed by survey or client confirmation before driving geometry.",
    location="docs/review-steps.md#moment-a-fact-finding-and-client-intent",
    reviewer="lead",
    notes="A wall position assumed as fact.",
)

register_review_step(
    name="review_client_privacy_override",
    lesson_ids=("l0728-study-windows-inherited", "l0728"),
    text="Verify that departures from standard privacy or window-sill rules are backed by explicit client decision records.",
    location="docs/review-steps.md#moment-a-fact-finding-and-client-intent",
    reviewer="client",
    notes="Study windows: an inherited privacy rule overridden by the client.",
)

register_review_step(
    name="review_facade_composition_glazing",
    lesson_ids=("l0486-extension-s-end", "l0486"),
    text="Verify that facade compositions meet architectural and client expectations for floor-to-beam glazing on key street and garden faces beyond per-room utility rules.",
    location="docs/review-steps.md#moment-a-fact-finding-and-client-intent",
    reviewer="lead",
    notes="The client reads the facade, not the room list.",
)

# Moment B: Layout and Design Option Acceptance
register_review_step(
    name="review_structural_placeholder_sizing",
    lesson_ids=("l0588-placeholder-size-not", "l0588"),
    text="Verify that unengineered structural members, glass balustrades, and fittings are marked ASSUMED in specifications pending structural sizing.",
    location="docs/review-steps.md#moment-b-layout-and-design-option-acceptance",
    reviewer="lead",
    notes="A placeholder size is not structural design.",
)

register_review_step(
    name="review_negative_bed_shifts",
    lesson_ids=("l0041-both-negative-bed", "l0041"),
    text="Both negative bed shifts failed design review while worker batch completed successfully; verify candidate layouts pass human spatial and design review.",
    location="docs/review-steps.md#moment-b-layout-and-design-option-acceptance",
    reviewer="lead",
    notes="Client design approval requires human spatial review.",
)

register_review_step(
    name="review_stair_assumed_construction_details",
    lesson_ids=("l0738-stair", "l0738"),
    text="Verify that open risers, steel stringers, bearings, and balustrade tectonic details are documented as ASSUMED construction details for modeling.",
    location="docs/review-steps.md#moment-b-layout-and-design-option-acceptance",
    reviewer="lead",
    notes="Stair: open risers kept; steel stringers, bearings, open-side balustrade and handrails added as ASSUMED construction details.",
)

register_review_step(
    name="review_lighting_function_and_beauty_cards",
    lesson_ids=("l0601-function-beauty-both", "l0601"),
    text="Verify that the lighting design satisfies both numerical lux targets and aesthetic design cards (pendant heights, sconce spacing, fixture hierarchy).",
    location="docs/review-steps.md#moment-b-layout-and-design-option-acceptance",
    reviewer="lead",
    notes="Function and beauty, both carded.",
)

register_review_step(
    name="review_direct_lighting_interreflection",
    lesson_ids=("l0027-direct-calculations-omit", "l0027"),
    text="Direct calculations omit shadows and inter-reflection; an empty-room probe is calibration. Verify lighting in rendered scenes with full inter-reflection.",
    location="docs/review-steps.md#moment-b-layout-and-design-option-acceptance",
    reviewer="lead",
    notes="Aesthetic lighting quality has no reliable purely numeric surrogate.",
)

# Moment C: Camera and Composition Choice
register_review_step(
    name="review_camera_view_framing_and_depth",
    lesson_ids=("l0743-view-chooser-s", "l0743"),
    text="Verify that camera positions stand on the primary subject's front side, avoid near-lens clipping (<0.8 m), and reveal room depth and design features.",
    location="docs/review-steps.md#moment-c-camera-and-composition-choice",
    reviewer="lead",
    notes="The view chooser's first scoring picked uninformative frames.",
)

# Moment D: Render Realism and Aesthetics
register_review_step(
    name="review_render_photorealism",
    lesson_ids=("l0058-five-render-rounds", "l0058"),
    text="Five render rounds changed samples, textures and HDRI strength, and images still read as CG; verify physical causes before image parameter tuning.",
    location="docs/review-steps.md#moment-d-render-realism-and-aesthetics",
    reviewer="client",
    notes="Photorealistic perception requires explicit lead/client visual review checkpoint.",
)

register_review_step(
    name="review_simulated_soft_goods_drape",
    lesson_ids=("l0086-curtains-looked-corrugat", "l0086"),
    text="Verify that simulated soft goods (curtains, bedding, cushions) display organic relaxation and irregular gathering rather than machine-stiff corrugations.",
    location="docs/review-steps.md#moment-d-render-realism-and-aesthetics",
    reviewer="lead",
    notes="Curtains looked corrugated, and then still machine-made after cloth simulation.",
)

register_review_step(
    name="review_surface_material_tint_in_image",
    lesson_ids=("l0768-specified-tint-must", "l0768"),
    text="Verify that specified finish tints (such as facade plaster) sample with the intended chromaticity in the rendered image under sun/sky illumination.",
    location="docs/review-steps.md#moment-d-render-realism-and-aesthetics",
    reviewer="lead",
    notes="A specified tint must be checked in the image.",
)

register_review_step(
    name="review_climber_foliage_visual_density",
    lesson_ids=("l0880-bougainvillea-climbers-r", "l0880"),
    text="Verify that trellis climber foliage density provides adequate visible coverage without appearing sparse or almost invisible.",
    location="docs/review-steps.md#moment-d-render-realism-and-aesthetics",
    reviewer="lead",
    notes="The bougainvillea climbers were replaced by scattered leaf/bract polygons (WP4) but stayed sparse enough to read as 'almost invisible'.",
)

register_review_step(
    name="review_terrace_garden_planting_fullness",
    lesson_ids=("l0967-top-garden-looked", "l0967"),
    text="Verify that terrace and roof gardens have adequate perimeter planting and container shrubs to avoid reading as bare.",
    location="docs/review-steps.md#moment-d-render-realism-and-aesthetics",
    reviewer="lead",
    notes="The top garden looked bare.",
)

# Moment E: Evaluating Automated Checks and Critics
register_review_step(
    name="review_automated_critic_claims_as_leads",
    lesson_ids=("l0751-automated-critic-s", "l0751"),
    text="Verify that automated critic flags are treated as investigative leads and verified against scene geometry and physical data before taking action.",
    location="docs/review-steps.md#moment-e-evaluating-automated-checks-and-critics",
    reviewer="lead",
    notes="An automated critic's claims are leads, not findings.",
)

register_review_step(
    name="review_critic_brightness_physics_validity",
    lesson_ids=("l0088-critic-claimed-garden", "l0088"),
    text="Verify critic claims of relative surface darkness against photometric physics and surface albedo before turning them into pipeline guards.",
    location="docs/review-steps.md#moment-e-evaluating-automated-checks-and-critics",
    reviewer="lead",
    notes="The critic claimed a garden darker than sunlit bedding was a defect.",
)

register_review_step(
    name="review_tungsten_warm_cast_physical_intent",
    lesson_ids=("l0102-colour-cast-could", "l0102"),
    text="Verify that warm color cast advisories on lamp-lit night views are accepted as physically correct under tungsten presets rather than compensated in camera.",
    location="docs/review-steps.md#moment-e-evaluating-automated-checks-and-critics",
    reviewer="lead",
    notes="colour_cast could fail a warm lamp-lit night that is physically correct under the tungsten preset.",
)

register_review_step(
    name="review_shielded_night_highlight_contrast",
    lesson_ids=("l0103-open-night-door", "l0103"),
    text="Verify that failed highlight thresholds on shielded night views reflect correct luminaire housing shielding rather than an underexposed scene.",
    location="docs/review-steps.md#moment-e-evaluating-automated-checks-and-critics",
    reviewer="lead",
    notes="Open: the night door view fails highlights_present after lamps were moved inside their fittings.",
)

# Moment F: Delegating Research and Debugging
register_review_step(
    name="review_scientific_work_preliminary_research",
    lesson_ids=("l0045-claude-code-s", "l0045"),
    text="Verify that broad scientific and simulation tasks begin with literature research, pinned evidence, and documented physical formulas before writing code.",
    location="docs/review-steps.md#moment-f-delegating-research-and-debugging",
    reviewer="lead",
    notes="Claude Code's actual session identified claude-sonnet-5; broad scientific work required substantial research before writing code.",
)

register_review_step(
    name="review_minimal_reproduction_library_bug",
    lesson_ids=("l0278-broken-library-diagnosis", "l0278"),
    text="Verify that diagnosing a third-party library as broken requires an isolated minimal reproduction that does not share project codebase patterns.",
    location="docs/review-steps.md#moment-f-delegating-research-and-debugging",
    reviewer="lead",
    notes="A 'broken library' diagnosis needs a minimal reproduction that does not share my own code's pattern.",
)
