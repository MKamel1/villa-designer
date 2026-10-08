---
Document Outline:
  - [Executive Summary](#executive-summary)
  - [Evidence Status API](#evidence-status-api)
    - [Status Hierarchy and Strength Ranking](#status-hierarchy-and-strength-ranking)
    - [Data Model](#data-model)
    - [Core Operations](#core-operations)
  - [Covered Defect Lessons](#covered-defect-lessons)
  - [Reused Code and Architecture](#reused-code-and-architecture)
  - [Phase 2 Migration Plan and Call Sites](#phase-2-migration-plan-and-call-sites)
Executive Summary:
  This document specifies the archpipe evidence-status architecture designed to prevent silent promotion of evidence, assumptions, or scopes beyond their verifiable authority. It formalizes five evidence states, fail-closed verify and combine promotion rules, scope-widening guards, and maps call sites for Phase 2 migration without breaking current stage gates.
---

# Evidence Status Architecture

## Executive Summary

The [`archpipe.evidence`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) module establishes a formal evidence authority boundary across the design pipeline. It prevents values, assumptions, or models from being silently promoted beyond what their verifiable evidence supports. Every tracked design value or record carries an immutable status in `VERIFIED`, `REQUIREMENT`, `CLIENT_DECISION`, `ASSUMED`, `UNVERIFIED`, an authoritative source citation, an explicit application scope, and governance metadata for client decisions.

## Evidence Status API

The module is implemented in [`src/archpipe/evidence.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py).

### Status Hierarchy and Strength Ranking

The system defines five explicit evidence states via [`EvidenceStatus`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py):

| Status | Authority Level | Description |
|---|---|---|
| `VERIFIED` | 4 (Strongest) | Factual evidence independently verified against an original publication edition/page or measured geometry. |
| `REQUIREMENT` | 3 | Authored brief constraint, client objective, or statutory code requirement that must be satisfied. |
| `CLIENT_DECISION` | 2 | Governance decision or waiver explicitly made by the client or lead, recording who and when (ISO date). |
| `ASSUMED` | 1 | Design stand-in, proxy geometry, or professional assumption without published citation or client sign-off. |
| `UNVERIFIED` | 0 (Weakest) | Unvetted claim, unchecked candidate file, legacy computation, or metadata disagreeing with geometry. |

When combining values or records via [`combine()`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py), the promotion rule enforces that the compound status is strictly the **WEAKEST** status among all components:

```latex
\text{status}_{\text{combined}} = \min_{r \in \text{records}} \text{rank}(r.\text{status})
```

An assumed item combined with verified ones always yields `ASSUMED` (reproducing lesson `l0092`). If any input is unverified, the combined claim remains `UNVERIFIED`.

### Data Model

1. [`SourceRef`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py):
   Immutable dataclass capturing:
   - `title`: Name of book, standard, or document.
   - `edition`: Verified edition string or number.
   - `printed_page`: Exact page printed on paper (distinguished from PDF software sequence numbers).
   - `url`: Canonical web address for online sources.
   - `locator`: Clause, table, or figure locator.
   - `pdf_page`: 0-based viewer index.
   - `pdf_label`: PDF software page label.
   - `file_edition`: Edition claimed by filename or download metadata (used to catch filename mismatches).
   - `verified`: Boolean indicating whether copyright and passage were verified.
   - `verification_method`, `verified_by`, `notes`.

2. [`ClientDecision`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py):
   Immutable dataclass mandatory whenever status is `CLIENT_DECISION`:
   - `decided_by`: Non-empty actor identifier (e.g. `"client"`, `"client:lead"`).
   - `date`: Valid ISO-8601 date string (`YYYY-MM-DD`).
   - `reason`: Non-empty technical and household justification.

3. [`EvidenceRecord`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py):
   Immutable tracked unit holding:
   - `value`: Dimension, geometry, dictionary, or primitive.
   - `status`: [`EvidenceStatus`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py).
   - `source`: Primary [`SourceRef`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py).
   - `scope`: Application boundary (e.g. `'room'`, `'room:bedroom'`, `'dwelling'`).
   - `client_decision`: Optional [`ClientDecision`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py).
   - `sources`: Tuple of all underlying [`SourceRef`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) instances.
   - `reasons`: Tuple of audit notes or failure explanations.
   - `rescope_history`: Traceable history of all re-scoping operations.
   - `verification_history`: Traceable history of verification events.

### Core Operations

- **Explicit Verification**:
  ```python
  verified_record = record.verify(source=SourceRef(...), checked_by="lead", notes="...")
  ```
  A record cannot be constructed with `status=VERIFIED` unless accompanied by a verified [`SourceRef`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py).

- **Scope Boundary Enforcement**:
  ```python
  record.apply_to(target_scope)
  ```
  Scopes follow a strict hierarchy (`element` < `subsystem` < `room` < `storey` < `dwelling` < `site`). Applying a room-scoped record to dwelling scope raises [`ScopeWideningError`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) unless explicitly rescoped beforehand:
  ```python
  dwelling_record = record.rescope(target_scope="dwelling", reason="Approved as whole-dwelling benchmark")
  ```

- **Combining Multiple Inputs**:
  ```python
  compound_record = combine(record_a, record_b, record_c, value="compound_name")
  ```
  Yields the weakest status, narrowest scope, and unions all source citations.

## Covered Defect Lessons

The module directly guards against the 12 observed failure lessons from [`docs/lessons-audit.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md) and [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md):

1. **`l0020` — Isolated room is not a dwelling**:
   - *Trap*: A pass in a single room was treated as evidence for a full dwelling.
   - *Guard*: [`apply_to("dwelling")`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) raises [`ScopeWideningError`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) on room-scoped records. Narrowing is permitted; widening requires an authored reason via [`rescope()`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py).

2. **`l0030` — Door hinge handedness**:
   - *Trap*: Automated door swing checks used default left hinges without extracted handedness, claiming compliance.
   - *Guard*: Unextracted parameters remain `ASSUMED` or `UNVERIFIED`; combining them with layout checks yields `ASSUMED`, preventing provisional checks from posing as certified compliance.

3. **`l0042` — Missing Revit family corpus**:
   - *Trap*: Revit family corpus unavailable on Ubuntu was treated as available.
   - *Guard*: Unverified environment assumptions cannot be promoted to `VERIFIED`; skipped coverage must be explicitly reported.

4. **`l0092` — Invented dressing stand-ins**:
   - *Trap*: Invented decor and stand-ins were indistinguishable from design content in renders and schedules.
   - *Guard*: [`combine()`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) reduces any compound containing an `ASSUMED` item to `ASSUMED`.

5. **`l0112` — Signify robots.txt disallow**:
   - *Trap*: Bulk automated downloads attempted against forbidden endpoints.
   - *Guard*: Source intake requires explicit verified rights and terms check.

6. **`l0121` — Git tracking of downloaded files**:
   - *Trap*: Downloaded manufacturer files almost committed to the repository.
   - *Guard*: External files remain in private storage; repository tracks only verified [`SourceRef`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) metadata and hashes.

7. **`l0179` — Model metadata disagrees with measured geometry**:
   - *Trap*: Desk lamp depth declared 408 mm in metadata but measured 202 mm in glTF mesh.
   - *Guard*: [`check_geometry_against_metadata()`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) and [`assert_geometry_matches_metadata()`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) flag drift > tolerance (0.005 m) as `UNVERIFIED` and raise [`GeometryDisagreementError`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py).

8. **`l0188` — File named 'Neufert 6th ed. 2023' is 1980 2nd edition**:
   - *Trap*: Download filename was trusted over the copyright page.
   - *Guard*: [`check_book_edition()`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) flags filename discrepancies; records stay `UNVERIFIED` until [`verify()`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) explicitly records the checked copyright page.

9. **`l0189` — PDF page label vs printed page mismatch**:
   - *Trap*: Building Construction Illustrated PDF viewer page was 191 while the printed page was 5.45.
   - *Guard*: [`check_page_locator()`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) and [`assert_page_agreement()`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) detect label divergence and raise [`PageMismatchError`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py).

10. **`l0221` — Calibration sample re-scoring**:
    - *Trap*: Checks tuned against failing sample improved quiet rate while recall on seeded defects dropped.
    - *Guard*: Evaluation evidence distinguishes test calibration samples from independent validation sets.

11. **`l0661` — Render and daylight analysis describing different buildings**:
    - *Trap*: Daylight simulation and Cycles rendering used divergent geometry and finish reflectances.
    - *Guard*: [`check_shared_model()`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) requires matching model SHA-256 hashes across studies.

12. **`l0763` — Render-side fix is not a design fix**:
    - *Trap*: Light fittings moved 100-155 mm in the render only were presented as a resolved design.
    - *Guard*: [`check_render_vs_design()`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) flags render offsets diverging from design values as `UNVERIFIED`.

## Reused Code and Architecture

Rather than duplicating existing modules, [`archpipe.evidence`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) extends and integrates with:

1. [`src/archpipe/guidance.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guidance.py):
   - Reuses `guidance.evidence_status(card, sources)` via [`from_guidance_card()`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) to map library cards into [`EvidenceRecord`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) objects.
   - Reuses `CATEGORIES` for distinguishing project targets (`REQUIREMENT`), recommendations, and principles.
   - Reuses project-level `scope` parameter conventions (`'room'`, `'dwelling'`).

2. [`src/archpipe/sources.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/sources.py):
   - Reuses source lifecycle states (`identified`, `held`, `content_verified`).
   - Reuses `SOURCES_ROOT` and `REGISTRY` (`knowledge/library.json`).
   - Reuses `sha256()` digest calculation for model and file identity.

3. [`src/archpipe/asset_intake.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/asset_intake.py):
   - Reuses the `BOUNDS_TOLERANCE_M` tolerance threshold (0.005 m) for metadata-geometry comparisons.
   - Reuses the `_valid_size_override` pattern requiring `decided_by`, `date` (ISO-8601), and `reason` for governance overrides.
   - Reuses the role-based `ASSUMED` basis concept for unverified props.

4. [`src/archpipe/knowledge_index.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/knowledge_index.py):
   - Reuses edge-token and printed page extraction concepts to catch PDF label sequence number mismatches.

## Phase 2 Migration Plan and Call Sites

*Do not migrate these call sites in Phase 1; this inventory establishes the target scope for Phase 2.*

| Target Module | Function / Call Site | Current Implementation | Phase 2 Migration |
|---|---|---|---|
| [`src/archpipe/guidance.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guidance.py) | `evidence_status()` (line 52) | Returns `{'status': 'unresolved' \| 'applicable', 'reasons': [...]}` dictionary | Wrap returned outcome in [`EvidenceRecord`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py), propagating `VERIFIED`, `REQUIREMENT`, or `UNVERIFIED`. |
| [`src/archpipe/guidance.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guidance.py) | `numerical_target()` (line 78) | Returns `{'enabled': bool, 'status': 'verified' \| 'unresolved'}` dictionary | Return typed [`EvidenceRecord`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) enforcing unit and transcription matching. |
| [`src/archpipe/guidance.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guidance.py) | `review_stage()` (line 320) | Reads `scope=project.get('scope', 'dwelling')` as plain string | Use [`record.apply_to(project['scope'])`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) to prevent room-scoped example checks from closing dwelling gates. |
| [`src/archpipe/rules.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/rules.py) | `Rule` dataclass (line 147) | Field `evidence_status: str = "unverified"` | Replace string with typed `EvidenceStatus` enum. |
| [`src/archpipe/asset_intake.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/asset_intake.py) | `validate_entry()` (line 133) | `_valid_size_override(value)` returns boolean | Convert size overrides into [`ClientDecision`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) records attached to prop records. |
| [`src/archpipe/asset_intake.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/asset_intake.py) | `validate_entry()` (line 205) | Computes `drift > BOUNDS_TOLERANCE_M` | **MIGRATED (Phase 2 Batch 1)**: Delegates drift decision to [`check_geometry_against_metadata()`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) preserving single authority, exact error text, and tolerance. |
| [`src/archpipe/sources.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/sources.py) | `intake()` (line 267) | Marks `s["status"] = "held"` | **MIGRATED (Phase 2 Batch 1)**: Screens incoming files with [`check_book_edition()`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) before marking held; fails closed with `EditionMismatchError` (l0188). |
| [`src/archpipe/knowledge_index.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/knowledge_index.py) | `page_labels()` (line 125) | Computes `_agreement` score | Not migrated: the batch 1 attempt was rejected in lead review (2026-10-08) because it stored flags on the function object and re-derived page numbers; still to do. Call [`check_page_locator()`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) to flag sequence-number labels before indexing. |
| [`src/archpipe/concept/villa_lighting.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_lighting.py) | `design()` | Computes fitting heights | Use [`check_render_vs_design()`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) to prevent render seating from diverging from spec ceiling heights. |
| [`scripts/villa_daylight_finished.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/villa_daylight_finished.py) | Model extraction | Takes model path | **MIGRATED (Phase 2 Batch 1)**: Calls [`check_shared_model()`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) via `verify_shared_model()` ensuring daylight simulation refuses to run when model hash differs from render scene (l0661). |
