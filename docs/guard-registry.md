---
Document Outline:
  - "[1. Executive Summary](#1-executive-summary)"
  - "[2. Overview & Architectural Motivation](#2-overview--architectural-motivation)"
  - "[3. Hierarchy of Controls & Lesson Mapping](#3-hierarchy-of-controls--lesson-mapping)"
  - "[4. Registry API Reference](#4-registry-api-reference)"
  - "[5. How to Register Guards & Review Steps](#5-how-to-register-guards--review-steps)"
  - "[6. Pre-Registered Phase 1 Guards](#6-pre-registered-phase-1-guards)"
  - "[7. Coverage Auditing & Reporting](#7-coverage-auditing--reporting)"
  - "[8. Phase 2 Migration & scripts/verify.py Integration Plan](#8-phase-2-migration--scriptsverifypy-integration-plan)"
Executive Summary: |
  This document details the Lesson Guard and Review Step Registry ([guard_registry.py](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py)).
  It provides the mechanism by which pipeline checks and tests declare the lesson IDs they enforce, proving each against frozen real incident fixtures and clean negative cases.
  It also details coverage auditing against [lessons-audit.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md) and lays out the Phase 2 plan to fail scripts/verify.py on uncovered lessons.
---

# Lesson Guard and Review Step Registry

## 1. Executive Summary

The Guard Registry ([`guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py)) operationalizes the defect-learning discipline defined in [`.agents/skills/defect-learning/SKILL.md`](file:///C:/Users/mmbka/arch-pipeline-agy/.agents/skills/defect-learning/SKILL.md) and [`CLAUDE.md`](file:///C:/Users/mmbka/arch-pipeline-agy/CLAUDE.md) Non-Negotiable Discipline 7: **Every defect leaves a guard behind.**

Instead of relying on prose claims or unverified assertions, every registered guard explicitly binds one or more lesson IDs from [`docs/lessons-audit.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md) and [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md) to:
1. A **real failing case** frozen by value from the actual incident (or explicitly flagged as `needs_real_case=True` if awaiting a frozen incident asset);
2. A **clean case** that proves the guard stays quiet on correct work (negative test discipline);
3. Expected outcomes defining what constitutes firing and staying quiet.

For Tier 3 lessons where numerical automation is inappropriate (aesthetic qualities, client intent, human spatial judgement), the registry records an explicit, named **review step** specifying the review text and exact file location.

---

## 2. Overview & Architectural Motivation

### The "Check Built from Incomplete Examples" Defect Pattern

An audit of project defect records ([`docs/lessons-audit.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), Root Class: *check built from incomplete examples*, 18 lessons) identified a systematic recurring failure mode:
* Checks and tests written and "proven" solely on synthetic, positive-only, or idealized inputs repeatedly missed the actual defect in production or broke on valid work.
* Notable real incidents:
  - `l0061`: The first `window_view` check passed an empty void because it checked global standard deviation rather than local pixel gradient detail.
  - `l0077`: The render critic identified five visible defects that every automated QA check had passed.
  - `l0078`: Thresholds calibrated on synthetic images failed three times on real renders (window detail, colour cast, highlight floor).
  - `l0079`: A blue lamp-lit night passed `colour_cast` because the check had not been tested on warm nighttime lighting.
  - `l0093`: `verticals_level` reported 0 deg pitch for level cameras due to missing non-level test cases.
  - `l0136`: `highlights_present` failed soft overcast daylight because the check assumed every photograph contains near-white specular highlights.
  - `l0466`: A JSON serialization fix passed its synthetic unit test but crashed on the client's actual model due to unhandled .NET byte types.

### Architectural Invariant

To eliminate this class of error:
- No guard is admitted as complete unless verified against a frozen real failure case and a clean negative test case.
- No synthetic fixture may be invented to satisfy the runner; guards awaiting real assets must be explicitly recorded with `needs_real_case=True`.
- Unreadable inputs must immediately fail closed and be reported as explicit errors, never recorded as "no guard" or silently treated as `NONE`.

---

## 3. Hierarchy of Controls & Lesson Mapping

The registry maps each lesson according to the hierarchy of controls defined in [`.agents/skills/defect-learning/SKILL.md`](file:///C:/Users/mmbka/arch-pipeline-agy/.agents/skills/defect-learning/SKILL.md):

| Control Tier | Description | Registry Mechanism | Example Lessons |
|---|---|---|---|
| **Tier 1** | **Prevent by Construction**<br>Mistake-proofing APIs, immutable builders, closed geometric solids, and single typed coordinate boundaries so defects cannot be expressed. | Registered guard verifying builder invariant or schema rejection. | `l0010` (inactive family symbols), `l0012` (DirectShape rotation), `l0118` (LDT governs over Revit family). |
| **Tier 2** | **Detect Early & Fail Closed**<br>Unconditional pipeline checks at the earliest informed stage (ingest, export, render QA, verify). | Registered guard with frozen real failing case and clean case. | `l0188` (edition mismatch), `l0189` (page label mismatch), `l0179` (mesh metadata drift), `l0113` (MIME sniffing), `l0098` (photometry aspect ratio). |
| **Tier 3** | **Human Judgement or Client Intent**<br>Aesthetic perception, design approval, or irreducible subjective review. Never fake a numerical check for human judgement. | Registered named review step with explicit text, reviewer role, and location. | `l0027` (empty-room probe calibration), `l0041` (negative bed shifts design review), `l0058` (photorealism perception review). |

---

## 4. Registry API Reference

The registry module is located at [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py).

### Core Data Structures

- [`GuardCase`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L61-L67): Frozen container for input arguments `args` (tuple) and `kwargs` (dict).
- [`case(*args, **kwargs)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L69-L72): Convenience constructor factory.
- [`GuardExecutionResult`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L84-L93): Execution report containing `guard_name`, `case_type` ("real" or "clean"), `passed` (bool), `fired` (bool), `error_message` (str), and `detail`.
- [`RegisteredGuard`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L168-L245): Encapsulates the guard function, associated lesson IDs, real case, clean case, expected outcomes, tier, and `needs_real_case` flag.
  - Method `run_case(case_type)`: Executes the guard against either "real" or "clean" case.
  - Method `run()`: Executes both cases and returns `(real_result, clean_result)`.
- [`RegisteredReviewStep`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L247-L257): Encapsulates a Tier 3 review checkpoint: `name`, `lesson_ids`, `text`, `location`, `reviewer`, and `notes`.

### Registration Functions

- [`register_guard(...)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L264-L315) / [`register(...)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L318): Decorator or direct callable to register a Tier 1 or Tier 2 guard.
- [`register_review_step(...)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L321-L349): Registers a Tier 3 review step.

### Lookup & Inspection Functions

- [`get_guard(name)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L351-L356): Retrieves a registered guard by name.
- [`all_guards()`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L365-L368): Returns list of all registered guards.
- [`find_guards_for_lesson(lesson_id)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L381-L392): Returns guards matching a lesson ID (exact slug or base prefix, e.g. "l0188").
- [`get_review_step(name)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L358-L363): Retrieves a review step by name.
- [`all_review_steps()`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L370-L373): Returns list of all registered review steps.
- [`find_review_steps_for_lesson(lesson_id)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L394-L405): Returns review steps matching a lesson ID.
- [`clear_registry()`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L375-L379): Clears in-memory registry (used for test isolation).

### Coverage Auditing Functions

- [`audit_lesson_coverage(audit_file=None, strict=False)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L411-L618): Parses [`docs/lessons-audit.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), matches lessons against registered guards and review steps, and reports coverage counts. Reports unreadable inputs as explicit errors.
- [`report_uncovered_lessons(audit_file=None, strict=False)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L621-L634): Returns list of lesson dictionaries that have neither a registered guard nor a review step.
- [`format_coverage_report(audit_file=None, strict=False)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L637-L670) / [`coverage_report(...)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L673): Returns a formatted human-readable audit text summary.

---

## 5. How to Register Guards & Review Steps

### Pattern A: Function Raising an Exception on Real Defect

```python
from archpipe.evidence import PageMismatchError, assert_page_agreement
from archpipe.guard_registry import register_guard, case

register_guard(
    fn=assert_page_agreement,
    name="evidence_page_locator_agreement",
    lesson_ids=("l0189-building-construction-il", "l0189"),
    real_case=case(191, "5.45"),      # Real incident: PDF label sequence 191 vs printed 5.45
    clean_case=case("17", "17"),       # Clean case: PDF label agrees with printed page
    expected_real=PageMismatchError,   # Fires: raises PageMismatchError
    expected_clean=None,               # Quiet: returns None without raising
    tier=2,
    description="Fails closed when PDF page sequence label disagrees with printed page (l0189)",
)
```

### Pattern B: Function Returning an EvidenceRecord

```python
from archpipe.evidence import EvidenceRecord, EvidenceStatus
from archpipe.external_claims import check_cct_and_watts_agreement
from archpipe.guard_registry import register_guard, case

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
    expected_real=EvidenceStatus.UNVERIFIED,  # Fires: stays UNVERIFIED on cross-source drift
    expected_clean=EvidenceStatus.VERIFIED,    # Quiet: promotes to VERIFIED on agreement
    tier=2,
    description="Cross-checks CCT and wattage between Revit family and LDT (l0118)",
)
```

### Pattern C: Guard Needing a Real Case (No Invented Fixtures)

```python
from archpipe.guard_registry import register_guard

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
    needs_real_case=True,  # Explicitly tracked as needing real incident fixture
)
```

### Pattern D: Decorator Registration on a Custom Guard

```python
from archpipe.guard_registry import register_guard, case

@register_guard(
    name="boundary_extent_guard",
    lesson_ids=("l0820-prop-extent-guard", "l0820"),
    real_case=case(bounds_m={"min": [0, 0, 0], "max": [10.5, 3.0, 5.0]}, room_boundary={"max_x": 10.0}),
    clean_case=case(bounds_m={"min": [0, 0, 0], "max": [9.5, 3.0, 5.0]}, room_boundary={"max_x": 10.0}),
    expected_real=ValueError,
    expected_clean=None,
    tier=2,
    description="Detects prop bounds exceeding storey boundary envelope",
)
def check_boundary_extent(bounds_m: dict, room_boundary: dict) -> None:
    if bounds_m["max"][0] > room_boundary["max_x"]:
        raise ValueError("Prop extent exceeds room boundary")
```

### Pattern E: Registering a Tier 3 Review Step

```python
from archpipe.guard_registry import register_review_step

register_review_step(
    name="review_direct_lighting_interreflection",
    lesson_ids=("l0027-direct-calculations-omit", "l0027"),
    text="Direct calculations omit shadows and inter-reflection; an empty-room probe is calibration. Named review of preview and client intent.",
    location="docs/method/stage5-lighting.md",
    reviewer="lead",
    notes="Aesthetic lighting quality has no reliable purely numeric surrogate",
)
```

---

## 6. Pre-Registered Phase 1 Guards

The following 6 guards with frozen real incident fixtures, 1 guard flagged as `needs_real_case`, and 3 Tier 3 review steps are pre-registered in [`guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py):

| Guard Name | Lesson ID | Guard Target | Real Failing Case | Clean Quiet Case | Expected Outcome |
|---|---|---|---|---|---|
| `evidence_book_edition` | `l0188` | [`check_book_edition`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) | "Neufert Architects Data 6th ed. 2023.pdf", "2nd English edition 1980" | "Metric_Handbook_7th_ed_2022.pdf", "7th edition 2022" | Real: `UNVERIFIED` (`matches=False`)<br>Clean: `VERIFIED` (`matches=True`) |
| `evidence_page_locator_agreement` | `l0189` | [`assert_page_agreement`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) | PDF sequence `191` vs printed `"5.45"` | PDF sequence `"17"` vs printed `"17"` | Real: raises [`PageMismatchError`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py)<br>Clean: `None` |
| `evidence_geometry_metadata_agreement` | `l0179` | [`assert_geometry_matches_metadata`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py) | Declared depth `408.0` mm vs measured `202.0` mm (tol `5.0`) | Declared `408.0` mm vs measured `408.2` mm (tol `1.0`) | Real: raises [`GeometryDisagreementError`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/evidence.py)<br>Clean: `None` |
| `external_claims_content_sniffing` | `l0113` | [`ingest_bytes`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/external_claims.py) | Zip bytes declared as `application/json` | Zip bytes declared as `application/zip` | Real: `UNVERIFIED`<br>Clean: `VERIFIED` |
| `external_claims_cct_and_watts_agreement` | `l0118` | [`check_cct_and_watts_agreement`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/external_claims.py) | Revit `3200 K / 3 W` vs LDT `3000 K / 23 W` | Revit `3000 K / 23 W` vs LDT `3000 K / 23.2 W` | Real: `UNVERIFIED`<br>Clean: `VERIFIED` |
| `external_claims_photometry_fitting_agreement` | `l0098` | [`check_photometry_fitting_agreement`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/external_claims.py) | `(594, 24)` mm strip on `(276, 276)` mm round drum | `(280, 280)` mm round on `(276, 276)` mm round drum | Real: `UNVERIFIED`<br>Clean: `VERIFIED` |
| `render_qa_window_view_detail` | `l0061` | `render_qa` detail | `None` (`needs_real_case=True`) | `None` | Marked `needs_real_case=True` pending frozen void render |

### Pre-Registered Tier 3 Review Steps

1. `review_direct_lighting_interreflection` ([`l0027`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)): Direct calculations omit shadows and inter-reflection; an empty-room probe is calibration. Location: [`docs/method/stage5-lighting.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/method/stage5-lighting.md), Reviewer: `lead`.
2. `review_negative_bed_shifts` ([`l0041`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)): Both negative bed shifts failed design review while worker batch completed successfully. Location: [`scripts/worker_entry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/worker_entry.py), Reviewer: `lead`.
3. `review_render_photorealism` ([`l0058`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)): Five render rounds changed samples, textures and HDRI strength, and images still read as CG. Location: [`.agents/skills/photoreal-render/SKILL.md`](file:///C:/Users/mmbka/arch-pipeline-agy/.agents/skills/photoreal-render/SKILL.md), Reviewer: `client`.

---

## 7. Coverage Auditing & Reporting

The function [`audit_lesson_coverage`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L411-L618) parses the lesson table from [`docs/lessons-audit.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md):
- Total lessons tracked: **217** (61 Tier 1, 135 Tier 2, 21 Tier 3).
- Lessons are classified into:
  - `covered_by_guard`: Mapped to at least one registered guard with a verified real failing case.
  - `covered_by_review`: Mapped to a registered Tier 3 review step.
  - `needs_real_case`: Mapped to a guard whose real case is not yet frozen (`needs_real_case=True`).
  - `uncovered_lessons`: Currently lacking both a registered guard and a review step.
- **Fail-Closed Unreadable Handling**: If the input file is missing, unreadable, empty, or contains malformed table rows, the audit reports explicit entries in `errors` and `unreadable_inputs`. It **never** reports unreadable entries as "no guard" or `NONE`.

---

## 8. Phase 2 Migration & scripts/verify.py Integration Plan

### Objective

Achieve 100% accountable coverage of all 217 lessons in [`docs/lessons-audit.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), and make [`scripts/verify.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/verify.py) fail closed on any lesson lacking an active guard or review step.

### Step-by-Step Execution Plan

1. **Step 1: Batch Registration by Subsystem**
   - **Asset & Intake Modules** ([`asset_intake.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/asset_intake.py), [`products.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/products.py)): Register guards for `l0011`, `l0014`, `l0072`, `l0075`, `l0177`, `l0178`, `l0496`, `l0772`, `l0846`, `l0960` freezing bounds from [`tests/test_asset_intake.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_asset_intake.py) (`jacaranda_tree`, `sf_minotti_sofa`).
   - **Scene & Geometry Builders** ([`villa_render.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_render.py), [`villa_furnish3d.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish3d.py), [`physical_part.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/physical_part.py)): Register guards for `l0046`, `l0047`, `l0059`, `l0069`, `l0587`, `l0589`, `l0686`, `l0878`, `l0923`.
   - **Photometrics & Lighting** ([`photometry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/photometry.py), [`lighting.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/lighting.py)): Register guards for `l0025`, `l0026`, `l0074`, `l0080`, `l0090`, `l0095`, `l0096`, `l0114`, `l0119`, `l0123`, `l0650`, `l0656`.
   - **Safe I/O & Serialization** ([`safe_io.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/safe_io.py), [`jsonsafe.py`](file:///C:/Users/mmbka/arch-pipeline-agy/revit/jsonsafe.py)): Register guards for `l0019`, `l0024`, `l0067`, `l0101`, `l0117`, `l0131`, `l0272`, `l0466`.
   - **Render QA Checks** ([`render_qa.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/render_qa.py)): Register guards for `l0061`, `l0078`, `l0079`, `l0081`, `l0082`, `l0100`, `l0136`.
   - **Tier 3 Review Steps**: Register remaining Tier 3 review checkpoints (all 21 lessons) across `docs/method/` and skill guides.

2. **Step 2: Real Fixture Freezing**
   - For all guards flagged `needs_real_case`, extract and freeze the real failing asset or image into `tests/data/frozen_defects/` (by value, never pointing to mutable live outputs).
   - Once frozen, update the registration to bind `real_case` and remove `needs_real_case=True`.

3. **Step 3: Integration into scripts/verify.py**
   - Add a preflight gate to [`scripts/verify.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/verify.py):
     ```python
     from archpipe.guard_registry import all_guards, audit_lesson_coverage
     
     # Run all registered guards on real and clean cases
     for guard in all_guards():
         if not guard.needs_real_case:
             real_res, clean_res = guard.run()
             expect(f"guard {guard.name} fires on real case", real_res.passed and real_res.fired)
             expect(f"guard {guard.name} quiet on clean case", clean_res.passed and not clean_res.fired)
     
     # Audit lesson coverage
     audit = audit_lesson_coverage(ROOT / "docs/lessons-audit.md", strict=True)
     expect("lesson coverage audit has no errors", len(audit["errors"]) == 0)
     # In Phase 2 strict mode:
     expect("zero uncovered lessons", audit["uncovered_count"] == 0)
     ```
   - Any lesson with neither a guard nor a review step causes [`scripts/verify.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/verify.py) to exit with non-zero exit code.
