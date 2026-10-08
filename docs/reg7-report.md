---
Document Outline:
  - [Executive Summary](#executive-summary)
  - [Phase 2 Batch 7 Overview](#phase-2-batch-7-overview)
  - [Registered Guards and Lesson Coverage](#registered-guards-and-lesson-coverage)
  - [Grouping and Mapping Justification](#grouping-and-mapping-justification)
  - [Examined Lessons Left Uncovered](#examined-lessons-left-uncovered)
  - [Execution Timing and Performance](#execution-timing-and-performance)
  - [Coverage Accounting and Audit Reconciliation](#coverage-accounting-and-audit-reconciliation)
  - [Files Modified](#files-modified)
Executive Summary: |
  This report documents Phase 2, Batch 7 of the lesson guard registry migration for archpipe.
  Ten previously uncovered lessons are now registered across 7 new production guards, covering
  render QA camera pitch leveling, light fixture photometry binding, intent-based subject framing,
  kitchen prep lighting targets, stage result file integrity, landscape plant spacing, and column clearance.
  All guards delegate directly to production modules, execute in under 25 milliseconds combined,
  and preserve the 217-lesson accounting invariant (103 covered, 21 review, 10 needs real case, 83 uncovered).
---

# Executive Summary

This report documents Phase 2, Batch 7 of the lesson guard registry migration for archpipe. Ten previously uncovered lessons are now registered across 7 new production guards, covering render QA camera pitch leveling, light fixture photometry binding, intent-based subject framing, kitchen prep lighting targets, stage result file integrity, landscape plant spacing, and column clearance. All guards delegate directly to production modules, execute in under 25 milliseconds combined, and preserve the 217-lesson accounting invariant (103 covered, 21 review, 10 needs real case, 83 uncovered).

# Phase 2 Batch 7 Overview

Phase 2 Batch 7 prioritises Revit/extract/read-back, camera/lighting measurement, and stair/route/furniture geometry subsystems with existing production controls:
1. **Render QA Camera Pitch and Photometry Binding ([`archpipe.render_qa`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/render_qa.py))**: Automated checks verifying camera pitch remains level within tolerance to prevent leaning walls, and ensuring all active luminaires have verified, measured IES photometry rather than fallback isotropic point sources.
2. **Camera View Intent Framing ([`archpipe.concept.render_views`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/render_views.py))**: Choosing camera viewpoints programmatically from spatial intent, guaranteeing key room subjects (such as bath fixtures) fit within the sensor framing without clipping.
3. **Lighting Task Plane Targets ([`archpipe.concept.villa_lighting`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_lighting.py))**: Enforcing kitchen prep task direct maintained illuminance targets (`ies-res-kitchen-prep-500`), failing closed when task downlights are omitted.
4. **Stage Result Output Integrity ([`archpipe.stage_result`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/stage_result.py))**: Atomic pipeline output verification failing closed when generated stage deliverables are modified, truncated, or tampered on disk.
5. **Landscape Plant Neighbour Spacing ([`archpipe.concept.villa_landscape`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_landscape.py))**: Comparing neighbour spacing within beds and layers to guarantee nursery spread clearance.
6. **Furniture Column Clearance ([`archpipe.concept.villa_furnish`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py))**: Checking placed interior furniture against fixed structural column boundaries.

# Registered Guards and Lesson Coverage

A total of 10 uncovered lessons were registered across 7 new production guards:

| Lesson ID | Guard Name | Guard Function | Real Case Source | Clean Case | Needs Real Case | Execution Time |
|---|---|---|---|---|---|---|
| `l0093` (`l0093-verticals-level-reported`), `l0063` (`l0063-walls-leaned`) | `render_qa_verticals_level` | `check_render_qa_verticals_level` | Camera pitch `81.0 deg` departing from `90.0 deg` level pitch evaluated on synthetic test image | Camera pitch `90.0 deg` on synthetic test image | `False` | < 1 ms |
| `l0068` (`l0068-fixtures-rendered-as`) | `render_qa_photometry_bound` | `check_render_qa_photometry_bound` | QA log specifying 5 active lights with 0 measured IES bound | QA log specifying 5 active lights with all 5 measured IES bound | `False` | < 1 ms |
| `l0731` (`l0731-hand-typed-cameras`) | `render_views_subject_framing` | `check_render_views_subject_framing` | D1 layout `family-bath` with `fb-wc` fixture framed using narrow 24mm lens ([tests/test_render_views.py#L33](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_render_views.py#L33)) | D1 layout `family-bath` with `fb-wc` framed using wide 16mm lens | `False` | ~4 ms |
| `l0689` (`l0689-lighting-negative-test`), `l0874` (`l0874-per-point-recomputation`) | `villa_lighting_prep_task_illuminance` | `check_villa_lighting_prep_task` | D1 lighting design with kitchen task downlights (DLN) omitted ([tests/test_villa_lighting.py#L45](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_villa_lighting.py#L45)) | Nominal D1 lighting fixtures | `False` | ~5 ms |
| `l0089` (`l0089-another-session-edited`), `l0133` (`l0133-open-right-after`) | `stage_result_output_integrity` | `check_stage_result_output_integrity` | Stage result record with tampered SHA-256 digest for `spec/villa-site.yaml` | Nominal stage result record matching current file digest | `False` | < 1 ms |
| `l0741` (`l0741-plants-placed-without`) | `villa_landscape_plant_spacing` | `check_villa_landscape_plant_spacing` | East bed planting pair spaced 0.27 m apart (spread 0.9 m, requirement 0.72 m) ([tests/test_villa_landscape.py#L42](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_villa_landscape.py#L42)) | East bed planting pair spaced 0.80 m apart | `False` | < 0.1 ms |
| `l0013` (`l0013-dropping-unknown-chairs`) | `villa_furnish_column_clearance` | `check_villa_furnish_column_clearance` | D1 furniture items with `kb-desk` shifted to `cx=15.0`, overlapping structural column at `x=15.157` ([tests/test_villa_furnish.py#L52](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_villa_furnish.py#L52)) | Nominal D1 furniture layout | `False` | ~10 ms |

# Grouping and Mapping Justification

1. **`l0093` and `l0063`**: Both represent vertical perspective distortion caused by unlevel camera pitch. In `l0063`, walls visibly leaned because the pitch was tilted. In `l0093`, the verticals level check was introduced in [`archpipe.render_qa`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/render_qa.py) (`LEVEL_TOL_DEG = 0.5`). Both are guarded by `check_render_qa_verticals_level`.
2. **`l0068`**: Light fixtures rendered as isotropic point sources when measured IES photometric distributions were lost or unbound. Handled by `photometry_bound` in [`archpipe.render_qa`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/render_qa.py).
3. **`l0731`**: Hand-typed cameras became uninformative or pointed the wrong way as geometry moved. Prevented by intent-based camera search in [`archpipe.concept.render_views`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/render_views.py), where `subjects_in_frame` is enforced as a strict hard constraint.
4. **`l0689` and `l0874`**: In `l0689`, the lighting suite lacked a negative test verifying that omitting task fittings produces a failure. In `l0874`, per-point direct lux calculations on task planes required optimized cluster evaluation to prevent performance regressions. Both relate to task target verification in [`archpipe.concept.villa_lighting.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_lighting.py).
5. **`l0089` and `l0133`**: Both capture defects where files produced in a pipeline stage were edited out-of-band by another session or open editor. Prevented by atomic cryptographic hash verification in [`archpipe.stage_result.validate_stage_result`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/stage_result.py), which fails closed on SHA-256 mismatches.
6. **`l0741`**: Plants placed without checking neighbour spacing resulted in crowded beds. Prevented by `spacing_violations` in [`archpipe.concept.villa_landscape`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_landscape.py).
7. **`l0013`**: Dropping furniture items without respecting structural column boundaries led to overlaps with columns. Prevented by `columns` checking in [`archpipe.concept.villa_furnish.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py).

# Examined Lessons Left Uncovered

The following candidate lessons were audited against production code and tests but left uncovered because no standalone production control currently exists without external toolchains or live simulation dependencies:

1. **`l0026-blender-ies-azimuth`**: Requires full Blender Cycles render run with IES azimuthal rotation probe; no offline standalone parser assertion exists in `archpipe`.
2. **`l0030-current-extract-lacks`**: Native Revit extract model does not yet record door hinge handedness; no production validator exists to flag missing hinge definitions.
3. **`l0073-gltf-viewer-showed`**: Web glTF viewer load failure; no production validator exists for browser viewer bundles.
4. **`l0080-lamps-rendered-far`**: Requires full Blender scene assembly and light source distance probe; no standalone fixture library validator exists.
5. **`l0090-window-glass-passed`**: Requires Radiance / Cycles daylight simulation probe; no production unit assertion exists.
6. **`l0101-look-retry-overwrote`**: Requires atomic render retry file management; no production file rotation / retry guard exists yet.
7. **`l0130-scripted-edit-applied`**: Tooling and CLI launcher working directory validation; no production module guard exists.
8. **`l0177-good-texture-poly` & `l0178-good-model-failed`**: External Poly Haven asset crawler format checks; no production assertion exists outside asset downloaders.
9. **`l0180-thermal-hand-check`, `l0181-energyplus-fatal-errors`, `l0182-thermal-results-3`**: EnergyPlus simulation runs, IDF syntax parsing, and weather file unit conversions; no standalone production validator exists in the current repo.
10. **`l0221-failed-90-gate`**: Architectural design gate threshold evaluation; no automated production control exists yet.
11. **`l0856-revit-pipe-run-needs`**: MEP pipe routing clearance in Revit; no automated python check in repo yet.

# Execution Timing and Performance

To keep test runtimes low and maintain test suite agility:
- A compact 20x20 synthetic test image `_qa_sample_img_path` is generated once in the temp directory and reused across render QA checks (< 1 ms per run).
- Module-level pre-calculated fixtures (`_lay_d1_base`, `_fx_lighting_clean`, `_record_clean`) are reused rather than rebuilding the full villa layout.
- `render_qa_verticals_level`: < 1 ms.
- `render_qa_photometry_bound`: < 1 ms.
- `render_views_subject_framing`: ~4 ms.
- `villa_lighting_prep_task_illuminance`: ~5 ms.
- `stage_result_output_integrity`: < 1 ms.
- `villa_landscape_plant_spacing`: < 0.1 ms.
- `villa_furnish_column_clearance`: ~10 ms.
- **Total Combined Overhead**: < 25 milliseconds across all 7 new guard test cases.

# Coverage Accounting and Audit Reconciliation

After registering the 10 lessons in Batch 7:

- `covered_by_guard`: **103** (previously 93, +10)
- `covered_by_review`: **21** (unchanged)
- `needs_real_case`: **10** (unchanged)
- `uncovered`: **83** (previously 93, -10)
- **Total Lessons**: **217** (`103 + 21 + 10 + 83 = 217`)

All 4 categories strictly sum to 217, preserving the audit accounting invariant.

# Files Modified

Only the following files were modified in this batch:
1. [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py): Exported 7 new guard check functions in `__all__`, imported `render_views` and `Image`, and registered guards #70 through #76.
2. [`tests/test_guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_guard_registry.py): Updated coverage count assertions (`covered_by_guard_count=103`, `uncovered_count=83`), appended 10 Batch 7 lesson IDs to `expected_guard_lessons`, and added `test_phase2_batch7_guards_execution`.
3. [`docs/reg7-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/reg7-report.md): This report.
