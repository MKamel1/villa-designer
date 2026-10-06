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
from pathlib import Path
import re
from typing import Any, Callable, Iterable
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
        try:
            result = self.guard_fn(*norm.args, **norm.kwargs)
        except Exception as e:
            exc = e

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

# Guard without real case listed as 'needs real case' (l0061: window_view passing void)
register_guard(
    fn=lambda img: False,
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

# -----------------------------------------------------------------------------
# Pre-registered Tier-3 review steps
# -----------------------------------------------------------------------------

register_review_step(
    name="review_direct_lighting_interreflection",
    lesson_ids=("l0027-direct-calculations-omit", "l0027"),
    text="Direct calculations omit shadows and inter-reflection; an empty-room probe is calibration. Named review of preview and client intent.",
    location="docs/method/stage5-lighting.md",
    reviewer="lead",
    notes="Aesthetic lighting quality has no reliable purely numeric surrogate",
)

register_review_step(
    name="review_negative_bed_shifts",
    lesson_ids=("l0041-both-negative-bed", "l0041"),
    text="Both negative bed shifts failed design review while worker batch completed successfully; named review of preview and client intent.",
    location="scripts/worker_entry.py",
    reviewer="lead",
    notes="Client design approval requires human spatial review",
)

register_review_step(
    name="review_render_photorealism",
    lesson_ids=("l0058-five-render-rounds", "l0058"),
    text="Five render rounds changed samples, textures and HDRI strength, and images still read as CG; named review of preview and client intent.",
    location=".agents/skills/photoreal-render/SKILL.md",
    reviewer="client",
    notes="Photorealistic perception requires explicit lead/client visual review checkpoint",
)
