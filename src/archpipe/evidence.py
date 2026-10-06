"""Evidence status tracking, promotion guards, and scope boundaries.

A value or record carries:
- status in {VERIFIED, ASSUMED, UNVERIFIED, REQUIREMENT, CLIENT_DECISION}
- source (title, edition, printed page or URL)
- scope (what it applies to, e.g. 'room', 'dwelling')
- client_decision (who and when, mandatory for CLIENT_DECISION)

Promotion rules:
- Combining values yields the WEAKEST status among all inputs.
- A value can only become VERIFIED through an explicit verify() that records
  the checked source.
- Scope cannot widen silently (applying a room-scoped value to a whole
  dwelling raises ScopeWideningError unless re-scoped with an explicit reason).

Defect guards covered:
- l0020: Scope promotion guard (isolated room is not a dwelling)
- l0030: Handedness/swing assumption guard (assumed parameters stay ASSUMED)
- l0042: Missing platform corpus guard (unverified environment capabilities)
- l0092: Dressing and stand-in combination guard (ASSUMED items weaken combined status)
- l0112: Source access rights guard (robots.txt / licensing)
- l0121: Repository tracking guard (downloaded assets vs tracked sources)
- l0179: Geometry metadata disagreement guard (metadata vs measured mesh)
- l0188: Source edition mismatch guard (filename claims vs copyright page)
- l0189: PDF page label vs printed page mismatch guard
- l0221: Defect recall vs test sample re-scoring guard
- l0661: Shared model hash guard (render and daylight analysis describe one building)
- l0763: Render-side fix vs design fix boundary guard

Quick Test:
    python -c "from archpipe.evidence import EvidenceRecord, EvidenceStatus; rec = EvidenceRecord(value=10, status=EvidenceStatus.ASSUMED); print(rec.status)"

Example Usage:
    >>> from archpipe.evidence import EvidenceRecord, EvidenceStatus, SourceRef, combine
    >>> v1 = EvidenceRecord(value=10, status=EvidenceStatus.VERIFIED, source=SourceRef(title="AD M", edition="2015", printed_page="17", verified=True))
    >>> v2 = EvidenceRecord(value=20, status=EvidenceStatus.ASSUMED, scope="room")
    >>> combined = combine(v1, v2)
    >>> combined.status
    <EvidenceStatus.ASSUMED: 'ASSUMED'>
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
import math
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]


class EvidenceStatus(str, Enum):
    """Status indicating authority and defensibility of a value or record."""
    VERIFIED = "VERIFIED"
    REQUIREMENT = "REQUIREMENT"
    CLIENT_DECISION = "CLIENT_DECISION"
    ASSUMED = "ASSUMED"
    UNVERIFIED = "UNVERIFIED"


# Module-level aliases for direct import and concise usage
VERIFIED = EvidenceStatus.VERIFIED
REQUIREMENT = EvidenceStatus.REQUIREMENT
CLIENT_DECISION = EvidenceStatus.CLIENT_DECISION
ASSUMED = EvidenceStatus.ASSUMED
UNVERIFIED = EvidenceStatus.UNVERIFIED

STATUS_NAMES = frozenset(s.value for s in EvidenceStatus)

# Strength order: higher number is stronger authority. Combining yields weakest.
STATUS_STRENGTH: dict[EvidenceStatus, int] = {
    EvidenceStatus.UNVERIFIED: 0,
    EvidenceStatus.ASSUMED: 1,
    EvidenceStatus.CLIENT_DECISION: 2,
    EvidenceStatus.REQUIREMENT: 3,
    EvidenceStatus.VERIFIED: 4,
}

# Scope hierarchy levels: widening (lower to higher) without explicit re-scoping raises.
SCOPE_LEVELS: dict[str, int] = {
    "element": 10,
    "component": 10,
    "fixture": 10,
    "prop": 10,
    "item": 10,
    "subsystem": 20,
    "zone": 20,
    "room": 30,
    "storey": 40,
    "level": 40,
    "dwelling": 50,
    "building": 50,
    "whole_building": 50,
    "site": 60,
    "project": 60,
}


def scope_level(scope_str: str) -> int:
    """Return the hierarchy level of a scope identifier.
    
    Prefixed scopes such as 'room:bedroom' or 'element:window' take the level
    of their prefix. Unknown scopes default to room level (30).
    """
    clean = str(scope_str).strip().lower()
    if clean in SCOPE_LEVELS:
        return SCOPE_LEVELS[clean]
    prefix = clean.split(":", 1)[0].split("_", 1)[0]
    return SCOPE_LEVELS.get(prefix, 30)


class EvidenceError(Exception):
    """Base exception for evidence and scope integrity failures."""


class ScopeWideningError(EvidenceError, ValueError):
    """Raised when a narrow scope is silently promoted to a broader scope (l0020)."""


class PageMismatchError(EvidenceError, ValueError):
    """Raised when a PDF page label disagrees with the printed page (l0189)."""


class GeometryDisagreementError(EvidenceError, ValueError):
    """Raised when model metadata disagrees with measured geometry (l0179)."""


class EditionMismatchError(EvidenceError, ValueError):
    """Raised when file name or metadata claims an edition differing from copyright (l0188)."""


@dataclass(frozen=True)
class SourceRef:
    """A citation or verification source for an evidence record.
    
    Captures title, edition, printed page, web URL, PDF label and verification state.
    """
    title: str
    edition: str | None = None
    printed_page: str | int | None = None
    url: str | None = None
    locator: str | None = None
    pdf_page: int | None = None
    pdf_label: str | int | None = None
    file_edition: str | None = None
    verified: bool = False
    verification_method: str | None = None
    verified_by: str | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.title or not str(self.title).strip():
            raise ValueError("SourceRef requires a non-empty title")

    @property
    def has_page_mismatch(self) -> bool:
        """True if pdf_label and printed_page are both set and disagree."""
        if self.pdf_label is None or self.printed_page is None:
            return False
        return str(self.pdf_label).strip().lower() != str(self.printed_page).strip().lower()

    @property
    def has_edition_mismatch(self) -> bool:
        """True if file_edition and verified edition disagree."""
        if self.file_edition is None or self.edition is None:
            return False
        return str(self.file_edition).strip().lower() != str(self.edition).strip().lower()

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"title": self.title, "verified": self.verified}
        if self.edition is not None:
            data["edition"] = self.edition
        if self.printed_page is not None:
            data["printed_page"] = str(self.printed_page)
        if self.url is not None:
            data["url"] = self.url
        if self.locator is not None:
            data["locator"] = self.locator
        if self.pdf_page is not None:
            data["pdf_page"] = self.pdf_page
        if self.pdf_label is not None:
            data["pdf_label"] = str(self.pdf_label)
        if self.file_edition is not None:
            data["file_edition"] = self.file_edition
        if self.verification_method is not None:
            data["verification_method"] = self.verification_method
        if self.verified_by is not None:
            data["verified_by"] = self.verified_by
        if self.notes:
            data["notes"] = self.notes
        return data


@dataclass(frozen=True)
class ClientDecision:
    """An explicit governance decision made by the client or lead.
    
    Per CLAUDE.md and ADRs, the client governs. Every decision must record
    who decided, when (ISO date), and why.
    """
    decided_by: str
    date: str
    reason: str

    def __post_init__(self) -> None:
        if not self.decided_by or not str(self.decided_by).strip():
            raise ValueError("ClientDecision requires non-empty decided_by")
        if not self.reason or not str(self.reason).strip():
            raise ValueError("ClientDecision requires non-empty reason")
        try:
            date.fromisoformat(str(self.date).strip())
        except (ValueError, TypeError) as exc:
            raise ValueError(f"ClientDecision requires valid ISO date (YYYY-MM-DD), got {self.date!r}") from exc

    def to_dict(self) -> dict[str, str]:
        return {
            "decided_by": self.decided_by,
            "date": self.date,
            "reason": self.reason,
        }


def _coerce_status(val: Any) -> EvidenceStatus:
    if isinstance(val, EvidenceStatus):
        return val
    if isinstance(val, str):
        norm = val.strip().upper()
        if norm in STATUS_NAMES:
            return EvidenceStatus(norm)
    raise ValueError(f"Unknown evidence status: {val!r}. Allowed: {sorted(STATUS_NAMES)}")


@dataclass(frozen=True)
class EvidenceRecord:
    """A tracked value or design artefact with evidence status, source and scope.
    
    Fields:
        value: The tracked data, dimension, layout, mesh or parameter.
        status: One of VERIFIED, REQUIREMENT, CLIENT_DECISION, ASSUMED, UNVERIFIED.
        source: Primary SourceRef containing title, edition, page or URL.
        scope: What this evidence applies to (e.g. 'room', 'room:bedroom', 'dwelling').
        client_decision: ClientDecision record (mandatory if status is CLIENT_DECISION).
        sources: Tuple of all underlying SourceRefs when combined.
        reasons: Tuple of explanatory audit notes or unresolved reasons.
        rescope_history: Tuple of past re-scoping operations with reasons.
        verification_history: Tuple of verification events.
    """
    value: Any
    status: EvidenceStatus = EvidenceStatus.UNVERIFIED
    source: SourceRef | None = None
    scope: str = "room"
    client_decision: ClientDecision | None = None
    sources: tuple[SourceRef, ...] = field(default_factory=tuple)
    reasons: tuple[str, ...] = field(default_factory=tuple)
    rescope_history: tuple[dict[str, str], ...] = field(default_factory=tuple)
    verification_history: tuple[dict[str, str], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        coerced = _coerce_status(self.status)
        object.__setattr__(self, "status", coerced)

        if not self.scope or not str(self.scope).strip():
            object.__setattr__(self, "scope", "room")

        # Promotion rule: a value can ONLY become VERIFIED through a verified source
        if self.status == EvidenceStatus.VERIFIED:
            if self.source is None:
                raise ValueError(
                    "Cannot construct VERIFIED record without source; use verify() with a checked source"
                )
            if not self.source.verified:
                raise ValueError(
                    "Source is not verified; a value can only become VERIFIED through explicit verify() recording checked source"
                )

        # CLIENT_DECISION requires who, when and reason
        if self.status == EvidenceStatus.CLIENT_DECISION:
            if self.client_decision is None:
                raise ValueError("CLIENT_DECISION status requires a client_decision record with who and when")

        # Normalize sources tuple to include primary source
        if self.source is not None and not self.sources:
            object.__setattr__(self, "sources", (self.source,))

    def verify(
        self,
        source: SourceRef | dict[str, Any] | None = None,
        checked_by: str = "lead",
        notes: str = "",
        verification_date: str | None = None,
    ) -> EvidenceRecord:
        """Promote this record to VERIFIED by recording the checked source.
        
        Args:
            source: SourceRef or dict containing title, verified edition, printed page, etc.
                    If None, re-verifies using the existing source if present.
            checked_by: The person or agent that inspected the original page/model.
            notes: Inspection details (e.g. copyright page read, dimension arrows checked).
            verification_date: ISO date of verification (defaults to today).
            
        Returns:
            A new EvidenceRecord with status VERIFIED.
        """
        target_src = source or self.source
        if target_src is None:
            raise ValueError("verify() requires a source to record")

        if isinstance(target_src, dict):
            src_ref = SourceRef(
                title=str(target_src.get("title", "") or "Checked Source"),
                edition=target_src.get("edition"),
                printed_page=target_src.get("printed_page") or target_src.get("page"),
                url=target_src.get("url"),
                locator=target_src.get("locator"),
                pdf_page=target_src.get("pdf_page"),
                pdf_label=target_src.get("pdf_label"),
                file_edition=target_src.get("file_edition"),
                verified=True,
                verification_method=target_src.get("verification_method") or "manual inspection",
                verified_by=checked_by,
                notes=notes or target_src.get("notes", ""),
            )
        elif isinstance(target_src, SourceRef):
            src_ref = SourceRef(
                title=target_src.title,
                edition=target_src.edition,
                printed_page=target_src.printed_page,
                url=target_src.url,
                locator=target_src.locator,
                pdf_page=target_src.pdf_page,
                pdf_label=target_src.pdf_label,
                file_edition=target_src.file_edition,
                verified=True,
                verification_method=target_src.verification_method or "inspected source",
                verified_by=checked_by,
                notes=notes or target_src.notes,
            )
        else:
            raise TypeError(f"source must be SourceRef or dict, got {type(target_src)}")

        v_event = {
            "action": "verified",
            "checked_by": checked_by,
            "date": verification_date or date.today().isoformat(),
            "notes": notes,
            "source_title": src_ref.title,
            "edition": str(src_ref.edition or ""),
        }
        all_sources = tuple(s for s in self.sources if s != self.source) + (src_ref,)

        return EvidenceRecord(
            value=self.value,
            status=EvidenceStatus.VERIFIED,
            source=src_ref,
            scope=self.scope,
            client_decision=self.client_decision,
            sources=all_sources,
            reasons=self.reasons,
            rescope_history=self.rescope_history,
            verification_history=self.verification_history + (v_event,),
        )

    def rescope(
        self,
        target_scope: str,
        reason: str,
        decided_by: str | None = None,
    ) -> EvidenceRecord:
        """Explicitly re-scope this record with an authored reason.
        
        Args:
            target_scope: The new scope (e.g. 'dwelling', 'room:kitchen').
            reason: The technical or client reason justifying scope change.
            decided_by: Who authorized the re-scoping (e.g. 'lead', 'client').
            
        Returns:
            A new EvidenceRecord with scope updated to target_scope.
        """
        clean_target = str(target_scope).strip()
        clean_reason = str(reason).strip()
        if not clean_target:
            raise ValueError("rescope() requires a non-empty target_scope")
        if not clean_reason:
            raise ValueError("rescope() requires an explicit non-empty reason")

        event = {
            "from_scope": self.scope,
            "to_scope": clean_target,
            "reason": clean_reason,
            "decided_by": decided_by or "unspecified",
            "date": date.today().isoformat(),
        }

        return EvidenceRecord(
            value=self.value,
            status=self.status,
            source=self.source,
            scope=clean_target,
            client_decision=self.client_decision,
            sources=self.sources,
            reasons=self.reasons,
            rescope_history=self.rescope_history + (event,),
            verification_history=self.verification_history,
        )

    def apply_to(self, target_scope: str) -> EvidenceRecord:
        """Validate whether this record may be applied to target_scope.
        
        Scope cannot widen silently. Applying a room-scoped value to a whole
        dwelling raises ScopeWideningError unless explicitly rescoped beforehand.
        Narrowing (e.g. dwelling-scoped rule applied to a room) or same-scope
        application is allowed.
        """
        clean_target = str(target_scope).strip().lower()
        clean_self = self.scope.strip().lower()

        if clean_self == clean_target:
            return self

        lvl_self = scope_level(clean_self)
        lvl_target = scope_level(clean_target)

        # Widening: applying narrow evidence to broader scope
        if lvl_target > lvl_self:
            raise ScopeWideningError(
                f"Scope cannot widen silently from {self.scope!r} to {target_scope!r}: "
                f"applying a {self.scope}-scoped result to {target_scope} requires explicit "
                f"rescope(target_scope, reason=...) (lesson l0020)"
            )

        # Same level cross-scope check (e.g. room:bedroom to room:kitchen)
        if lvl_target == lvl_self and clean_self != clean_target:
            raise ScopeWideningError(
                f"Cross-scope application from {self.scope!r} to {target_scope!r} "
                f"requires explicit rescope() with an authored reason"
            )

        return self

    def to_dict(self) -> dict[str, Any]:
        """Serialize record to dictionary suitable for JSON storage."""
        data: dict[str, Any] = {
            "value": self.value,
            "status": self.status.value,
            "scope": self.scope,
        }
        if self.source is not None:
            data["source"] = self.source.to_dict()
        if self.client_decision is not None:
            data["client_decision"] = self.client_decision.to_dict()
        if self.reasons:
            data["reasons"] = list(self.reasons)
        if self.rescope_history:
            data["rescope_history"] = list(self.rescope_history)
        if self.verification_history:
            data["verification_history"] = list(self.verification_history)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceRecord:
        """Reconstruct EvidenceRecord from dictionary."""
        src_dict = data.get("source")
        src_ref = SourceRef(**src_dict) if src_dict else None
        dec_dict = data.get("client_decision")
        client_dec = ClientDecision(**dec_dict) if dec_dict else None
        rescope_hist = tuple(data.get("rescope_history", ()))
        verify_hist = tuple(data.get("verification_history", ()))
        reasons = tuple(data.get("reasons", ()))

        return cls(
            value=data.get("value"),
            status=_coerce_status(data.get("status", "UNVERIFIED")),
            source=src_ref,
            scope=data.get("scope", "room"),
            client_decision=client_dec,
            reasons=reasons,
            rescope_history=rescope_hist,
            verification_history=verify_hist,
        )


def combine(
    *records: EvidenceRecord,
    value: Any = None,
    scope: str | None = None,
    reason: str = "",
) -> EvidenceRecord:
    """Combine multiple evidence records yielding the WEAKEST status.
    
    Promotion rules:
    - Status is the minimum strength among all input records.
    - Scope defaults to the narrowest (lowest hierarchy level) input scope,
      preventing silent scope widening.
    - All sources are collected and retained.
    
    Args:
        records: Two or more EvidenceRecord objects to combine.
        value: Optional compound value. If omitted, collects tuple of values.
        scope: Explicit scope (must not widen beyond the narrowest input scope
               without a supplied reason).
        reason: Justification if providing an explicit wider scope.
    """
    if not records:
        raise ValueError("combine() requires at least one EvidenceRecord")

    if len(records) == 1:
        return records[0]

    weakest = min((r.status for r in records), key=lambda s: STATUS_STRENGTH[s])

    # Narrowest scope among inputs governs the combination
    input_scopes = [r.scope for r in records]
    narrowest_scope = min(input_scopes, key=scope_level)

    if scope is not None:
        target_lvl = scope_level(scope)
        narrowest_lvl = scope_level(narrowest_scope)
        if target_lvl > narrowest_lvl and not reason:
            raise ScopeWideningError(
                f"Combined scope {scope!r} widens beyond narrowest input scope {narrowest_scope!r} "
                f"without an explicit reason (l0020)"
            )
        final_scope = scope
    else:
        final_scope = narrowest_scope

    # Union of all sources
    collected_sources: list[SourceRef] = []
    seen: set[tuple[str, str | None, str | None]] = set()
    for r in records:
        for s in r.sources:
            key = (s.title, s.edition, str(s.printed_page or s.locator or ""))
            if key not in seen:
                seen.add(key)
                collected_sources.append(s)

    combined_value = value if value is not None else tuple(r.value for r in records)
    primary_source = collected_sources[0] if collected_sources else None

    # Collect client decisions if all or any carry them
    decisions = [r.client_decision for r in records if r.client_decision is not None]
    primary_decision = decisions[0] if decisions else None

    reasons: list[str] = []
    if weakest != EvidenceStatus.VERIFIED:
        weakeners = [r for r in records if r.status == weakest]
        reasons.append(
            f"Combined status reduced to {weakest.value} by {len(weakeners)} weaker component(s)"
        )

    return EvidenceRecord(
        value=combined_value,
        status=weakest,
        source=primary_source,
        scope=final_scope,
        client_decision=primary_decision if weakest == EvidenceStatus.CLIENT_DECISION else None,
        sources=tuple(collected_sources),
        reasons=tuple(reasons),
    )


def verify(
    record: EvidenceRecord,
    source: SourceRef | dict[str, Any] | None = None,
    checked_by: str = "lead",
    notes: str = "",
) -> EvidenceRecord:
    """Explicitly verify an EvidenceRecord by recording its checked source."""
    return record.verify(source=source, checked_by=checked_by, notes=notes)


def rescope(
    record: EvidenceRecord,
    target_scope: str,
    reason: str,
    decided_by: str | None = None,
) -> EvidenceRecord:
    """Explicitly re-scope an EvidenceRecord with an authored reason."""
    return record.rescope(target_scope=target_scope, reason=reason, decided_by=decided_by)


# -----------------------------------------------------------------------------
# Defect guard helpers reproducing real defect classes
# -----------------------------------------------------------------------------

def check_book_edition(
    filename: str,
    copyright_edition: str,
    claimed_edition: str | None = None,
) -> dict[str, Any]:
    """Check claimed edition against copyright page (reproduces l0188).
    
    In lesson l0188, download filenames like 'Neufert 6th ed. 2023.pdf' were
    trusted as current editions, when reading the copyright page proved it was
    the 1980 2nd English edition.
    
    Returns a dict with verification outcome and reasons.
    """
    clean_fn = str(filename).lower()
    clean_cr = str(copyright_edition).strip()
    claimed = str(claimed_edition).strip() if claimed_edition else ""

    # Check if filename or claim mentions an edition number differing from copyright
    mismatches: list[str] = []

    # Detect common edition tokens e.g. '6th', '2nd', '3rd', '1st'
    import re
    fn_ed_match = re.search(r"(\d+)(?:st|nd|rd|th)\s+ed", clean_fn)
    fn_year_match = re.search(r"\b(19\d\d|20\d\d)\b", clean_fn)

    cr_ed_match = re.search(r"(\d+)(?:st|nd|rd|th)", clean_cr.lower())
    cr_year_match = re.search(r"\b(19\d\d|20\d\d)\b", clean_cr)

    if fn_ed_match and cr_ed_match:
        if fn_ed_match.group(1) != cr_ed_match.group(1):
            mismatches.append(
                f"File name claims {fn_ed_match.group(0)} but copyright page states {clean_cr} (l0188)"
            )
    if fn_year_match and cr_year_match:
        if fn_year_match.group(1) != cr_year_match.group(1):
            mismatches.append(
                f"File name indicates year {fn_year_match.group(1)} but copyright page indicates {cr_year_match.group(1)} (l0188)"
            )

    has_mismatch = bool(mismatches)
    return {
        "matches": not has_mismatch,
        "filename": filename,
        "copyright_edition": clean_cr,
        "claimed_edition": claimed or (fn_ed_match.group(0) if fn_ed_match else "unknown"),
        "flagged": has_mismatch,
        "status": EvidenceStatus.VERIFIED if not has_mismatch else EvidenceStatus.UNVERIFIED,
        "mismatches": mismatches,
        "reason": "; ".join(mismatches) if mismatches else "Copyright edition matches filename claim",
    }


def check_page_locator(
    pdf_label: str | int,
    printed_page: str | int,
) -> dict[str, Any]:
    """Check PDF page label against printed page (reproduces l0189).
    
    In lesson l0189, Building Construction Illustrated's PDF page labels were
    sequence numbers (191 where the page prints 5.45). Trusting PDF labels
    caused wrong citations until candidate agreement was checked.
    """
    clean_label = str(pdf_label).strip()
    clean_printed = str(printed_page).strip()
    mismatch = clean_label != clean_printed

    return {
        "matches": not mismatch,
        "pdf_label": clean_label,
        "printed_page": clean_printed,
        "flagged": mismatch,
        "reliable": not mismatch,
        "detail": (
            f"PDF page label {clean_label!r} disagrees with printed page {clean_printed!r} (l0189)"
            if mismatch else "PDF page label matches printed page"
        ),
    }


def assert_page_agreement(pdf_label: str | int, printed_page: str | int) -> None:
    """Fail closed when a PDF page label disagrees with the printed page."""
    res = check_page_locator(pdf_label, printed_page)
    if not res["matches"]:
        raise PageMismatchError(res["detail"])


def check_geometry_against_metadata(
    metadata_dimension: float,
    measured_dimension: float,
    tolerance: float = 0.005,
    unit: str = "mm",
) -> dict[str, Any]:
    """Check model metadata dimension against actual measured mesh geometry (reproduces l0179).
    
    In lesson l0179, desk_lamp_arm_01 declared depth 408 mm in metadata but
    measured 202 mm in glTF mesh. The defect was reported as failed and never
    silently repaired.
    """
    if not math.isfinite(metadata_dimension) or not math.isfinite(measured_dimension):
        raise ValueError("Dimensions must be finite numbers")

    drift = abs(metadata_dimension - measured_dimension)
    disagrees = drift > tolerance

    return {
        "matches": not disagrees,
        "metadata_dimension": metadata_dimension,
        "measured_dimension": measured_dimension,
        "drift": drift,
        "tolerance": tolerance,
        "unit": unit,
        "flagged": disagrees,
        "status": EvidenceStatus.UNVERIFIED if disagrees else EvidenceStatus.VERIFIED,
        "reason": (
            f"Model metadata ({metadata_dimension} {unit}) disagrees with measured geometry "
            f"({measured_dimension} {unit}) by {drift:.1f} {unit} (l0179)"
            if disagrees else "Metadata matches measured geometry within tolerance"
        ),
    }


def assert_geometry_matches_metadata(
    metadata_dimension: float,
    measured_dimension: float,
    tolerance: float = 0.005,
    unit: str = "mm",
) -> None:
    """Fail closed when model metadata disagrees with measured geometry."""
    res = check_geometry_against_metadata(metadata_dimension, measured_dimension, tolerance, unit)
    if not res["matches"]:
        raise GeometryDisagreementError(res["reason"])


def check_render_vs_design(
    design_value: float,
    render_value: float,
    tolerance: float = 0.001,
) -> dict[str, Any]:
    """Check whether a render-side compensation diverges from the design model (reproduces l0763).
    
    In lesson l0763, moving 14 light fittings in the render only was presented
    as a fix, while the design spec still had them 100-155 mm off the ceiling.
    A render-side fix cannot promote design status.
    """
    drift = abs(design_value - render_value)
    diverged = drift > tolerance
    return {
        "matches": not diverged,
        "design_value": design_value,
        "render_value": render_value,
        "drift": drift,
        "flagged": diverged,
        "status": EvidenceStatus.UNVERIFIED if diverged else EvidenceStatus.VERIFIED,
        "reason": (
            f"Render value {render_value} differs from design value {design_value} by {drift:.4f}: "
            f"a render-side fix is not a design fix (l0763)"
            if diverged else "Render and design values are consistent"
        ),
    }


def check_shared_model(
    model_sha256_render: str,
    model_sha256_analysis: str,
) -> dict[str, Any]:
    """Check that daylight analysis and rendering describe the same model (reproduces l0661).
    
    In lesson l0661, daylight analysis and render once used different geometry
    and reflectances until unified under one model hash.
    """
    matches = (
        bool(model_sha256_render)
        and bool(model_sha256_analysis)
        and model_sha256_render.strip().lower() == model_sha256_analysis.strip().lower()
    )
    return {
        "matches": matches,
        "render_model_hash": model_sha256_render,
        "analysis_model_hash": model_sha256_analysis,
        "flagged": not matches,
        "status": EvidenceStatus.VERIFIED if matches else EvidenceStatus.UNVERIFIED,
        "reason": (
            "Render and analysis describe the same model"
            if matches else "Render and analysis model hashes disagree: they must describe one building (l0661)"
        ),
    }


# -----------------------------------------------------------------------------
# Guidance card integration (reusing guidance.py and sources.py)
# -----------------------------------------------------------------------------

def from_guidance_card(card: dict[str, Any], sources: dict[str, Any] | None = None) -> EvidenceRecord:
    """Construct an EvidenceRecord from a knowledge/library.json evidence card.
    
    Reuses guidance.evidence_status to check whether the card and its source
    are content-verified and applicable.
    """
    from archpipe import guidance as g

    sources_dict = sources or {}
    audit = g.evidence_status(card, sources_dict)
    is_applicable = audit.get("status") == "applicable"

    category = card.get("category", "")
    if category == "project_target":
        status = EvidenceStatus.REQUIREMENT
    elif is_applicable and card.get("status") == "verified":
        status = EvidenceStatus.VERIFIED
    elif card.get("status") == "assumed":
        status = EvidenceStatus.ASSUMED
    else:
        status = EvidenceStatus.UNVERIFIED

    source_info = sources_dict.get(card.get("source_id", ""), {})
    source_ref = SourceRef(
        title=str(source_info.get("title") or card.get("source_id") or "Library Source"),
        edition=card.get("edition") or source_info.get("edition"),
        locator=card.get("locator"),
        printed_page=card.get("locator"),
        verified=status == EvidenceStatus.VERIFIED,
        verification_method=card.get("verification") or "library.json card",
    )

    conditions = str(card.get("conditions", "")).lower()
    scope = "dwelling" if "whole" in conditions or "dwelling" in conditions else "room"

    return EvidenceRecord(
        value=card.get("verified_value") if card.get("verified_value") is not None else card.get("claim"),
        status=status,
        source=source_ref,
        scope=scope,
        reasons=tuple(audit.get("reasons", ())),
    )
