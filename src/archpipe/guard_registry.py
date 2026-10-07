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

from dataclasses import dataclass, field
import io
import json
from pathlib import Path
import re
import tempfile
from typing import Any, Callable, Iterable
import uuid
import zipfile

from archpipe.evidence import (
    EvidenceError,
    EvidenceRecord,
    EvidenceStatus,
    GeometryDisagreementError,
    PageMismatchError,
    assert_geometry_matches_metadata,
    assert_page_agreement,
    check_book_edition,
)
from archpipe.external_claims import (
    check_cct_and_watts_agreement,
    check_photometry_fitting_agreement,
    ingest_bytes,
)
from archpipe import render_qa, safe_io
from archpipe.units_guard import (
    UnitsConversionError,
    check_units_guard,
)

__all__ = [
    "EvidenceStatus",
    "GuardCase",
    "GuardExecutionResult",
    "RegisteredGuard",
    "RegisteredReviewStep",
    "UnreadableInputError",
    "all_guards",
    "all_review_steps",
    "audit_lesson_coverage",
    "case",
    "check_element_id_exact_integer",
    "check_falsy_zero_lint",
    "check_raw_copy_lint",
    "check_utf16_or_utf8_json",
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
# Safe I/O & Serialization guards (Phase 2, Batch 1)
# -----------------------------------------------------------------------------

_FALSY_ZERO_PATTERN = re.compile(r"float\(.*\bor\s+([1-9][0-9.]*|[A-Z_]{3,})\s*\)")


def check_falsy_zero_lint(line: str) -> None:
    """Fails closed when code line uses float(x or <nonzero>) swallowing zero (l0067)."""
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

# 10. l0067: falsy-zero lint catches an or-default that swallows an explicit zero
register_guard(
    fn=check_falsy_zero_lint,
    name="safe_io_falsy_zero_lint",
    lesson_ids=("l0067-first-falsy-zero", "l0067"),
    real_case=case('energy = P * float(fx.get("output") or 1.0)'),  # falsy-ok: l0067 real bug fixture
    clean_case=case('energy = P * (float(fx["output"]) if fx.get("output") is not None else 1.0)'),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Fails closed on code lines using float(x or <nonzero>) that swallow an explicit zero (l0067)",
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
