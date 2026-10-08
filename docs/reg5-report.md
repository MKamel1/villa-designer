---
Document Outline:
  - [Executive Summary](#executive-summary)
  - [Phase 2 Batch 5 Registration Overview](#phase-2-batch-5-registration-overview)
  - [Subsystem Focus and Rationale](#subsystem-focus-and-rationale)
  - [Lesson-by-Lesson Guard Registration Details](#lesson-by-lesson-guard-registration-details)
  - [Deep Dive: Registered Guards and Defect Fixtures](#deep-dive-registered-guards-and-defect-fixtures)
  - [Examined Lessons Left Uncovered (No Production Guard)](#examined-lessons-left-uncovered-no-production-guard)
  - [Coverage Audit Metrics](#coverage-audit-metrics)
  - [Changed Files List](#changed-files-list)
  - [Verification Evidence and Review Readiness](#verification-evidence-and-review-readiness)
Executive Summary:
  This report documents Phase 2 Batch 5 of the defect guard registry migration covering 12 uncovered lessons across two critical subsystems: stair, opening, route geometry & spec clearances, and lighting measurement & pipeline stage execution proof. All 12 guards delegate strictly to production modules (villa, revit_spec, villa_furnish, villa_lighting, stage_result) and execute against historical defects frozen by value. Post-batch audit totals are 81 covered by guard, 21 covered by review step, 10 needs real case, and 105 uncovered, strictly preserving the 217 total lesson inventory invariant.
---

# Phase 2 Batch 5 Guard Registration Report

## Executive Summary

This report documents Phase 2 Batch 5 of the defect guard registry migration ([`docs/guard-registry.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/guard-registry.md) Section 8, Step 1). In accordance with the prompt guidance, this batch registers defect guards for 12 uncovered lessons across two high-priority subsystems:
1. **Stair, Opening & Route Geometry & Spec Clearances** ([`l0307`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0518`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0536`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0542`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0566`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0570`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0551`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0017`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0849`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md))
2. **Lighting Measurement & Pipeline Stage Execution Proof** ([`l0606`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0029`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0040`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md))

All 12 guards delegate directly to existing production modules in [`src/archpipe/concept/`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/) and [`src/archpipe/stage_result.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/stage_result.py). Every guard is tested against frozen real failure cases and clean quiet cases. Lessons examined that lack automated production controls ([`l0010`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0013`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0026`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0856`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)) are preserved as uncovered with explicit rationale.

The four audit categories update to:
- `covered_by_guard`: **81** (+12 from 69)
- `covered_by_review`: **21**
- `needs_real_case`: **10**
- `uncovered`: **105** (-12 from 117)
- **Total**: 81 + 21 + 10 + 105 = **217** (strictly preserving the invariant).

---

## Phase 2 Batch 5 Registration Overview

Following [`docs/guard-registry.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/guard-registry.md) Section 8 (Step 1), guards were registered strictly adhering to project conventions:
- **Production Delegation (Meta-Guard Compliant)**: Every registered guard function in [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls a production module (`archpipe.concept.*` or `archpipe.stage_result`), ensuring full compliance with the AST meta-guard in [`tests/test_guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_guard_registry.py). No local arithmetic re-implementations were introduced.
- **Frozen Real Defect Cases**: All failure cases are frozen **by value** directly from recorded incidents in [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md) and established production tests ([`tests/test_villa_concepts.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_villa_concepts.py), [`tests/test_villa_parking.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_villa_parking.py), [`tests/test_villa_furnish.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_villa_furnish.py), [`tests/test_d1_wp1.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_d1_wp1.py), [`tests/test_villa_lighting.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_villa_lighting.py), [`tests/test_stage_result.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_stage_result.py)). No mutable outputs under `out/` are referenced.
- **Clean Quiet Cases**: Clean cases execute identical checks on nominal geometry/specifications and pass without raising or firing.
- **Honest Demarcation of Uncovered Lessons**: If no production module exists to enforce a lesson, no synthetic guard is faked; the lesson remains uncovered and is catalogued with the exact missing mechanism.

---

## Subsystem Focus and Rationale

The two selected subsystems address the primary design integration and verification failure modes identified in the villa and bedroom pipelines:

### 1. Stair, Opening & Route Geometry & Spec Clearances
- **Structural and Headroom Intersections**: Straight flights clashing with existing structural columns ([`l0307`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)) and under-ramp/deck cross walls breaching variable soffit heights ([`l0518`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)).
- **Interior Circulation and Clearance Pinches**: Kitchen island work aisle clearance falling below NKBA multi-cook standards ([`l0536`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)), stair foot circulation obstruction ([`l0542`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)), principal bedroom window route access dropping for non-king beds ([`l0566`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)), pocket door approach route node omissions ([`l0570`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)), and furniture overlapping room wall outlines ([`l0551`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)).
- **Detailed Component Clearances**: Bedside table placement infringing on bed side use zones rather than head-end Zone A ([`l0017`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)), and dirty kitchen extract ducts floating away from hood chimneys ([`l0849`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)).

### 2. Lighting Measurement & Pipeline Stage Execution Proof
- **Illumination Target Enforcement**: Vanity grooming counter illumination failing when task downlights are omitted ([`l0606`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)).
- **Atomic Pipeline Result Integrity**: Fail-closed exit gating refusing exit code 0 when diagnostic reports indicate failure ([`l0029`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)), and stage result caching invalidation refusing stale outputs when input files are modified on disk ([`l0040`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)).

---

## Lesson-by-Lesson Guard Registration Details

| Lesson ID | Guard Name | Production Function | Real Failing Case & Source | Clean Quiet Case | needs_real_case | Status / Notes |
|---|---|---|---|---|---|---|
| `l0307` | `villa_concept_stair_structure` | [`check_villa_concept_stair_structure`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`villa.critique`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa.py#L323) | Concept A layout with stair model `"r3"` running into front party column 1590377. Source: [`tests/test_villa_concepts.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_villa_concepts.py#L37). | Nominal Concept A layout [`villa.concept_a()`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa.py#L247). | `False` | Real raises `ValueError("Stair structure clash detected: ['column 1590377']")`. Clean returns `status: "pass"` dict. |
| `l0518` | `revit_spec_clearance_problems` | [`check_revit_spec_clearance_problems`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`revit_spec.clearance_problems`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/revit_spec.py#L760) | Parking option P4 cross wall with `height = revit_spec.WALL_H` (2.7 m) breaching low ramp soffit. Source: [`tests/test_villa_parking.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_villa_parking.py#L404). | Nominal option P4 with sloped walls, doors, and infills. | `False` | Real raises `ValueError("Clearance problems detected under ramp/deck: ...")`. Clean returns `[]`. |
| `l0536` | `villa_furnish_kitchen_work_aisle` | [`check_villa_furnish_kitchen_work_aisle`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`villa_furnish.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py#L916) | D1 furniture layout with `k-island` shifted `cy += 0.05` pinching opposing work aisle under 1219 mm. Source: [`tests/test_villa_furnish.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_villa_furnish.py#L164). | Nominal D1 furniture layout [`villa_furnish.layout(LAY)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py#L58). | `False` | Real raises `ValueError("Kitchen work aisle clearance failure: ['main work aisle ...']")`. Clean returns `[]`. |
| `l0542` | `villa_furnish_stair_foot_reachable` | [`check_villa_furnish_stair_foot_reachable`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`villa_furnish.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py#L916) | D1 layout with sideboard console appended at stair foot `(10.1, -28.0)`. Source: [`tests/test_villa_furnish.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_villa_furnish.py#L33). | Nominal D1 layout. | `False` | Real raises `ValueError("Stair foot route obstruction: ['stair end of stair-b ...']")`. Clean returns `[]`. |
| `l0566` | `villa_furnish_principal_window_reachable` | [`check_villa_furnish_principal_window_reachable`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`villa_furnish.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py#L916) | D1 layout with vanity removed and wardrobe placed at garden window `(22.122, -25.4)`. Source: [`tests/test_villa_furnish.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_villa_furnish.py#L38). | Nominal D1 layout. | `False` | Real raises `ValueError("Principal bedroom window route obstruction: ['window of parents-bed ...']")`. Clean returns `[]`. |
| `l0570` | `villa_furnish_pocket_door_approach` | [`check_villa_furnish_pocket_door_approach`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`villa_furnish.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py#L916) | D1 layout with chest placed in `parents-entry` vestibule `(18.977, -26.95)`. Source: [`tests/test_villa_furnish.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_villa_furnish.py#L131). | Nominal D1 layout. | `False` | Real raises `ValueError("Pocket door approach route obstruction: ['door corridor/parents-entry ...']")`. Clean returns `[]`. |
| `l0551` | `villa_furnish_inside_room_boundary` | [`check_villa_furnish_inside_room_boundary`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`villa_furnish.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py#L916) | D1 layout with `kb-desk` shifted `cy = -23.4` outside kids bedroom B boundary. Source: [`tests/test_villa_furnish.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_villa_furnish.py#L173). | Nominal D1 layout. | `False` | Real raises `ValueError("Furniture placed outside room boundary: ['kb-desk ...']")`. Clean returns `status: "pass"` dict. |
| `l0017` | `villa_furnish_bedside_zone_a` | [`check_villa_furnish_bedside_zone_a`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`villa_furnish.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py#L916) | D1 layout with `pb-bedside` table shifted along the bed `cy += 0.9` into Zone B. Source: [`tests/test_villa_furnish.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_villa_furnish.py#L120). | Nominal D1 layout. | `False` | Real raises `ValueError("Bedside clearance violation: ['pb-bed ...']")`. Clean returns `status: "pass"` dict. |
| `l0849` | `revit_spec_wp1_detail_constraints` | [`check_revit_spec_wp1_detail_constraints`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`revit_spec.check_wp1_spec`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/revit_spec.py#L500) | D1 spec with dead dirty kitchen duct routing terminating at fan rather than external wall. Source: [`tests/test_d1_wp1.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_d1_wp1.py#L170). | Nominal D1 specification [`revit_spec.build(LAY)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/revit_spec.py#L653). | `False` | Real raises `ValueError("WP1 spec constraint errors: ['dirty-kitchen fan or duct does not reach its external wall']")`. Clean returns `[]`. |
| `l0606` | `villa_lighting_grooming_task` | [`check_villa_lighting_grooming_task`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`villa_lighting.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_lighting.py#L759) | D1 lighting design omitting vanity grooming task downlights (`DLN`) in bathrooms. Source: [`tests/test_villa_lighting.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_villa_lighting.py#L117). | Nominal D1 lighting design [`villa_lighting.design(LAY)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_lighting.py#L60). | `False` | Real raises `ValueError("Lighting task targets failed: [...]")`. Clean returns `[]`. |
| `l0029` | `stage_result_fail_verdict_rejection` | [`check_stage_result_fail_verdict_rejection`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`stage_result.enforce_clean_verdict`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/stage_result.py#L453) | Stage report dict containing `passed=False`, `verdict="FAIL ..."`, and failure items. Source: [`tests/test_stage_result.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_stage_result.py#L37). | Clean stage report dict with `passed=True`, `verdict="PASS"`, and empty failures. | `False` | Real raises `SystemExit(1)`. Clean returns exit code `0`. |
| `l0040` | `stage_result_stale_input_invalidation` | [`check_stage_result_stale_input_invalidation`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`stage_result.validate_stage_result`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/stage_result.py#L269) | Stage record with input file recorded SHA replaced with `"0" * 64` simulating modified input on disk. Source: [`tests/test_stage_result.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_stage_result.py#L88). | Stage record with exact current on-disk SHA digest of tracked repository file [`spec/villa-site.yaml`](file:///C:/Users/mmbka/arch-pipeline-agy/spec/villa-site.yaml). | `False` | Real raises `stage_result.StaleInputError`. Clean returns `(True, "ok", record)`. |

---

## Deep Dive: Registered Guards and Defect Fixtures

### 1. `l0307` (`villa_concept_stair_structure`)
- **Historical Defect**: In round 2/3 of concept generation, straight flight along the party wall had its basement foot running into existing structural column 1590377.
- **Production Guard**: [`archpipe.concept.villa.critique`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa.py#L323) runs `stairs.clashes(stair_model(lay.get("stair", "u")))`. When clashing with kept structure, it records check `stair_structure` with `status: "fail"` and lists the clashed structural column.
- **Registry Adapter**: [`check_villa_concept_stair_structure`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) evaluates `res["checks"]`, raising `ValueError` on failed stair structure check.

### 2. `l0518` (`revit_spec_clearance_problems`)
- **Historical Defect**: During round 7/8 client review, cross walls under the sloping parking ramp came through the ramp slab, and room doors were specified at standard 2.1 m height under a 1.9 m soffit.
- **Production Guard**: [`archpipe.concept.revit_spec.clearance_problems`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/revit_spec.py#L760) verifies wall `top` against `soffit = zb + P.clear_at(x)`, flagging any wall breaching the soffit by >10 mm.
- **Registry Adapter**: [`check_revit_spec_clearance_problems`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) fails closed with `ValueError` on any reported clearance problem.

### 3. `l0536` (`villa_furnish_kitchen_work_aisle`)
- **Historical Defect**: Authoring assumed nominal circulation around the kitchen island without verifying the opposing frontage work aisle width, causing pinch points between kitchen counters.
- **Production Guard**: [`archpipe.concept.villa_furnish.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py#L916) verifies that opposing counter frontages maintain 1219 mm clearance (NKBA multi-cook work aisle standard), reporting failure in `res["kitchen"]`.
- **Registry Adapter**: [`check_villa_furnish_kitchen_work_aisle`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) raises `ValueError` when `res["kitchen"]["status"] == "fail"`.

### 4. `l0542` (`villa_furnish_stair_foot_reachable`)
- **Historical Defect**: Circulation analysis treated stair flights as generic floor area; furniture placed at the foot of flight B blocked arrival/departure circulation.
- **Production Guard**: [`archpipe.concept.villa_furnish.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py#L916) verifies that every stair end remains reachable via unimpeded circulation route bodies.
- **Registry Adapter**: [`check_villa_furnish_stair_foot_reachable`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) raises `ValueError` on routes failure.

### 5. `l0566` (`villa_furnish_principal_window_reachable`)
- **Historical Defect**: Principal bedroom window clearance was keyed to `bed_king`; selecting `bed_double` accidentally disabled the check.
- **Production Guard**: [`archpipe.concept.villa_furnish.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py#L916) now binds route node checks to the room envelope regardless of bed model.
- **Registry Adapter**: [`check_villa_furnish_principal_window_reachable`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) raises `ValueError` when wardrobe placement obstructs the window route node.

### 6. `l0570` (`villa_furnish_pocket_door_approach`)
- **Historical Defect**: Pocket doors have no swing zone, which caused the route graph generator to omit approach route nodes, allowing vestibule furniture to block passage.
- **Production Guard**: [`archpipe.concept.villa_furnish.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py#L916) creates explicit approach route nodes for pocket doors.
- **Registry Adapter**: [`check_villa_furnish_pocket_door_approach`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) fails closed on approach node obstruction.

### 7. `l0551` (`villa_furnish_inside_room_boundary`)
- **Historical Defect**: Furniture placement routines snapped bounding boxes to boundary polylines rather than interior finished faces, embedding furniture partially inside walls.
- **Production Guard**: [`archpipe.concept.villa_furnish.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py#L916) check `inside_room` verifies all item bounding polygons are strictly interior to room boundaries.
- **Registry Adapter**: [`check_villa_furnish_inside_room_boundary`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) raises `ValueError` on room boundary escape.

### 8. `l0017` (`villa_furnish_bedside_zone_a`)
- **Historical Defect**: Furniture clearances treated entire bed perimeters identically; bedside tables intentionally occupy head-end Zone A but were flagged as encroaching on bedside approach Zone B.
- **Production Guard**: [`archpipe.concept.villa_furnish.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py#L916) check `clearances` permits bedside units within head-end Zone A but fails closed when shifted into bedside use zones.
- **Registry Adapter**: [`check_villa_furnish_bedside_zone_a`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) raises `ValueError` on clearance failures.

### 9. `l0849` (`revit_spec_wp1_detail_constraints`)
- **Historical Defect**: In round 2 draft v17, the dirty kitchen extract fan sat at x 13.30 while the hood chimney stood at x 13.827, causing the rendered duct to float in mid-air.
- **Production Guard**: [`archpipe.concept.revit_spec.check_wp1_spec`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/revit_spec.py#L500) checks fan coordinates against chimney bounds and requires extract duct routes to reach external walls.
- **Registry Adapter**: [`check_revit_spec_wp1_detail_constraints`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) raises `ValueError` on any reported WP1 constraint error.

### 10. `l0606` (`villa_lighting_grooming_task`)
- **Historical Defect**: Early lighting drafts evaluated general ambient lux levels but missed task-plane illuminance at mirrors and grooming counters.
- **Production Guard**: [`archpipe.concept.villa_lighting.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_lighting.py#L759) checks direct maintained illuminance against card `ies-res-vanity-grooming-300` (300 lx at 1.6 m AFF).
- **Registry Adapter**: [`check_villa_lighting_grooming_task`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) raises `ValueError` when task targets fail.

### 11. `l0029` (`stage_result_fail_verdict_rejection`)
- **Historical Defect**: A pipeline script printed `FAIL` in stdout/stderr but returned exit code 0, allowing an invalid stage output to be accepted by orchestrators.
- **Production Guard**: [`archpipe.stage_result.enforce_clean_verdict`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/stage_result.py#L453) inspects reports, logs, and dictionaries for failure keywords and forces non-zero exit (`SystemExit`).
- **Registry Adapter**: [`check_stage_result_fail_verdict_rejection`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls `enforce_clean_verdict` directly.

### 12. `l0040` (`stage_result_stale_input_invalidation`)
- **Historical Defect**: Cached stage outputs were reused across runs even after underlying input configuration files were modified.
- **Production Guard**: [`archpipe.stage_result.validate_stage_result`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/stage_result.py#L269) re-hashes all recorded input files on disk using SHA-256 and raises `StaleInputError` on hash mismatch.
- **Registry Adapter**: [`check_stage_result_stale_input_invalidation`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) executes `validate_stage_result` with `raise_on_error=True`.

---

## Examined Lessons Left Uncovered (No Production Guard)

Four lessons were carefully analyzed during subsystem selection but left uncovered because no automated production guard currently exists in the codebase:

1. **`l0010` (`l0010-family-symbols-load`)**:
   - *Learnings Context*: "Family symbols load inactive; inactive placement raises; Name property can be ambiguous in IronPython."
   - *Current Codebase Status*: Only [`revit/place_families_test.py`](file:///C:/Users/mmbka/arch-pipeline-agy/revit/place_families_test.py) references this behavior in an external manual script. No automated pure-Python production module in `archpipe` checks or activates family symbols before placement.
   - *Disposition*: Left uncovered as "no guard yet".
2. **`l0013` (`l0013-dropping-unknown-chairs`)**:
   - *Learnings Context*: "Dropping unknown chairs/tables makes clearances pass falsely."
   - *Current Codebase Status*: Proposed control requires a unified topology model for hosts, openings, and obstacles. Existing layout checks drop or warn on unknown types rather than failing closed at a single production boundary.
   - *Disposition*: Left uncovered as "no guard yet".
3. **`l0026` (`l0026-blender-ies-azimuth`)**:
   - *Learnings Context*: "Blender IES azimuth differs, finite sphere sizing can wash out a strip light..."
   - *Current Codebase Status*: The local re-implementation previously deleted in earlier batches has no corresponding production module in `src/archpipe`.
   - *Disposition*: Preserved in uncovered lessons list.
4. **`l0856` (`l0856-stair-s-wall`)**:
   - *Learnings Context*: "The stair's wall handrail was buried in the plaster."
   - *Current Codebase Status*: Enforced only within test assertion logic in [`tests/test_render_standard.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_render_standard.py); no production module in `archpipe.concept` provides an automated handrail-to-plaster clearance check.
   - *Disposition*: Left uncovered as "no guard yet".

---

## Coverage Audit Metrics

Audit execution against [`docs/lessons-audit.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md) yields the following updated distribution:

| Metric | Pre-Batch 5 Baseline | Post-Batch 5 New Total | Delta |
|---|---|---|---|
| **Total Lessons Audited** | 217 | 217 | 0 |
| **Covered by Guard** | 69 | **81** | +12 |
| **Covered by Review Step (Tier 3)** | 21 | **21** | 0 |
| **Needs Real Case Flag** | 10 | **10** | 0 |
| **Uncovered Lessons** | 117 | **105** | -12 |
| **Sum Invariant Check** | 69 + 21 + 10 + 117 = 217 | 81 + 21 + 10 + 105 = 217 | Valid (Sum = 217) |

---

## Changed Files List

The following files were modified in this phase (and only these files):
1. [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py)
   - Added `stage_result` import.
   - Added 12 new guard functions to `__all__`.
   - Registered 12 new Phase 2 Batch 5 guards with frozen real cases and clean cases.
2. [`tests/test_guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_guard_registry.py)
   - Updated `covered_by_guard_count` to 81 and `uncovered_count` to 105.
   - Added the 12 new lesson identifiers to `expected_guard_lessons`.
   - Added `test_phase2_batch5_guards_execution` asserting real case firing and clean case quietness.
3. [`docs/reg5-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/reg5-report.md)
   - Complete Batch 5 registration and coverage audit report.

---

## Verification Evidence and Review Readiness

- **AST Meta-Guard Compliance**: All 12 guard functions call functions in production modules (`villa.critique`, `revit_spec.clearance_problems`, `villa_furnish.check`, `revit_spec.check_wp1_spec`, `villa_lighting.check`, `stage_result.enforce_clean_verdict`, `stage_result.validate_stage_result`). None perform local re-implementations.
- **Fail-Closed Execution Proof**: Every real case raises its designated exception (`ValueError`, `SystemExit`, `StaleInputError`) when presented with historical defect geometry or manifests.
- **Clean Execution Proof**: Every clean case executes cleanly without raising or firing warnings.
- **Audit Parsing Verification**: Zero errors parsing [`docs/lessons-audit.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), with exact counts verified statically against the 217-lesson inventory.
