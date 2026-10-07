---
Document Outline:
  - [Executive Summary](#executive-summary)
  - [Phase 2 Batch 3 Registration Overview](#phase-2-batch-3-registration-overview)
  - [Lesson-by-Lesson Guard Registration Details](#lesson-by-lesson-guard-registration-details)
  - [Deep Dive: Scene and Geometry Builders](#deep-dive-scene-and-geometry-builders)
  - [Uncovered Lesson Analysis: l0046](#uncovered-lesson-analysis-l0046)
  - [Needs Real Case Analysis: l0059](#needs-real-case-analysis-l0059)
  - [Coverage Audit Metrics](#coverage-audit-metrics)
  - [Changed Files List](#changed-files-list)
  - [Verification Evidence and Review Readiness](#verification-evidence-and-review-readiness)
Executive Summary:
  This report documents Phase 2 Batch 3 of the defect guard registry migration covering the Scene & geometry builders subsystem across 9 audited lessons. Seven active guards were registered using production functions in villa_furnish3d, physical_part, and villa_render_contract with frozen real cases; one guard was registered with needs_real_case=True awaiting historical pixel renders, and one lesson was recorded as uncovered with no production guard yet. Total covered by guard is 55, review steps is 21, needs_real_case is 10, and uncovered is 131, summing to 217.
---

# Phase 2 Batch 3 Guard Registration Report

## Executive Summary

This report documents Phase 2 Batch 3 of the defect guard registry migration ([`docs/guard-registry.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/guard-registry.md) Section 8, Step 1) covering the **Scene & geometry builders** subsystem across nine audited lessons ([`l0046`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0047`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0059`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0069`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0587`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0589`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0686`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0878`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0923`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)). All nine lessons belong to the root class *"proxy lacks physical geometry"* with the recommended construction control *"Require typed physical solids and local axes at builder boundaries"*.

Seven active guards have been registered using production functions in [`src/archpipe/concept/villa_furnish3d.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish3d.py), [`src/archpipe/concept/physical_part.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/physical_part.py), and [`src/archpipe/villa_render_contract.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/villa_render_contract.py), proven on frozen real failure cases and clean quiet cases. One guard ([`l0059`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)) was registered under [`render_qa.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/render_qa.py) with `needs_real_case=True` pending frozen rendered images demonstrating shadow-ray daylight blocking. Exactly one lesson ([`l0046`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)) was confirmed to have no automated production guard in the pipeline and is preserved as uncovered ("no guard yet"). In total, covered lessons by guard increased from 48 to 55, lessons flagged `needs_real_case` increased from 9 to 10, and uncovered lessons dropped from 139 to 131, maintaining the strict 217 lesson inventory invariant.

---

## Phase 2 Batch 3 Registration Overview

Per [`docs/guard-registry.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/guard-registry.md) Section 8 (Step 1), Phase 2 Batch 3 migration targets the **Scene & geometry builders** subsystem.

In accordance with project integrity standards:
- All registered guard functions call production modules ([`archpipe.concept.villa_furnish3d`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish3d.py), [`archpipe.concept.physical_part`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/physical_part.py), [`archpipe.villa_render_contract`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/villa_render_contract.py), or [`archpipe.render_qa`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/render_qa.py)), satisfying the AST meta-guard in [`tests/test_guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_guard_registry.py). Local re-implementations inside `guard_registry.py` were strictly avoided.
- Real defect cases were frozen **by value** directly from historical incidents documented in [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md) and established regression test suites ([`tests/test_d1_wp5.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_d1_wp5.py), [`tests/test_furniture.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_furniture.py)). No mutable outputs under `out/` are referenced.
- No synthetic data was fabricated for missing historical pixel renders; [`l0059`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md) is registered with `needs_real_case=True`.
- No dummy or fake production logic was invented for [`l0046`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md); it is recorded as "no guard yet" and maintained in the uncovered lessons list.

---

## Lesson-by-Lesson Guard Registration Details

| Lesson ID | Guard Name | Production Function | Real Failing Case & Source | Clean Quiet Case | needs_real_case | Status / Notes |
|---|---|---|---|---|---|---|
| `l0046` | *None* | *None* | *No production guard in pipeline* (only IronPython extraction probe [`revit/probe_fixture_geometry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/revit/probe_fixture_geometry.py) exists). | *N/A* | `N/A` | Left uncovered as "no guard yet". Documented in [Uncovered Lesson Analysis](#uncovered-lesson-analysis-l0046). |
| `l0047` | `physical_part_solid_winding` | [`check_physical_part_solid_winding`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`physical_part.geometry_errors`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/physical_part.py#L68) | Closed headboard solid box mesh with clockwise-wound inverted faces (negative volume). Frozen from [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L182) and [`tests/test_furniture.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_furniture.py#L88). | Closed headboard solid box mesh with CCW outward-facing winding and positive volume. | `False` | Real raises `ValueError("Inward-facing solid error: ['inward-facing solid']")`. Clean returns `[]`. |
| `l0059` | `render_qa_glass_daylight_transmission` | [`render_qa.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/render_qa.py#L86) | *Missing frozen pixel render of room where refractive glass slab blocked Cycles shadow rays.* | *None* | `True` | Awaiting frozen pixel render of shadow-ray daylight blocking. Documented in [Needs Real Case Analysis](#needs-real-case-analysis-l0059). |
| `l0069` | `physical_part_duvet_footprint` | [`check_physical_part_duvet_footprint`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`physical_part.Part`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/physical_part.py#L110) | Duvet mesh shifted 0.6 m outside mattress support footprint `(0.0, 0.0, 2.0, 1.5)`. Frozen from [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L214). | Shaped duvet mesh (triangular prism with 3 distinct x coordinates) contained within mattress footprint. | `False` | Real raises `ValueError` (`PartError: duvet leaves mattress footprint`). Clean instantiates `Part` successfully. |
| `l0587` | `villa_furnish3d_spec_details` | [`check_round2_spec_details`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`villa_furnish3d.round2_postcondition`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish3d.py#L555) | Authored D1 spec read-back with approved `guest-wc-extract-grille` omitted from `details`. Frozen from [`tests/test_d1_wp5.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_d1_wp5.py#L100). | Full D1 read-back containing all elements returned by `villa_furnish3d.round2_elements(spec)`. | `False` | Real raises `ValueError("Option spec details missing in readback: ['guest-wc-extract-grille: built 0 times']")`. Clean returns `[]`. |
| `l0589` | `villa_furnish3d_stair_glass_boundary` | [`check_round2_stair_glass_boundary`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`villa_furnish3d.round2_postcondition`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish3d.py#L555) | `stair-open-glass` panel with `bbox_mm[4] += 10` projecting outside room `stair-b`. Frozen from [`tests/test_d1_wp5.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_d1_wp5.py#L110). | Full D1 read-back with `stair-open-glass` strictly within room `stair-b` bounding rectangle. | `False` | Real raises `ValueError("Stair glass boundary failure: ['stair-open-glass-01: leaves room stair-b']")`. Clean returns `[]`. |
| `l0686` | `villa_render_contract_zero_area_triangles` | [`check_render_contract_scene_geometry`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`villa_render_contract.validate_scene`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/villa_render_contract.py#L118) | Villa render contract scene with degenerate collinear zero-area triangle `[[0, 0, 0], [1, 0, 0], [2, 0, 0]]`. Frozen from [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L853). | Valid quad polygon `[[[0, 0, 0], [0.1, 0, 0], [0.1, 0.1, 0], [0, 0.1, 0]]]`. | `False` | Real raises `ValueError("Render contract degenerate geometry error: ['meshes[0].faces[0]: degenerate polygon']")`. Clean returns `[]`. |
| `l0878` | `physical_part_climber_proxy` | [`check_physical_part_climber_proxy`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`physical_part.Part`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/physical_part.py#L110) | Bare 80 mm rectangular box mesh (`0.08 x 0.08 x 0.08 m`) for climber plant. Frozen from [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L558). | Shaped non-proxy climber mesh (triangular prism with 3 distinct x coordinates). | `False` | Real raises `ValueError` (`PartError: bare rectangular proxy for climber`). Clean instantiates `Part` successfully. |
| `l0923` | `physical_part_garment_proxy` | [`check_physical_part_garment_proxy`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`physical_part.Part`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/physical_part.py#L110) | Bare 25 mm flat vertical slab mesh (`0.30 x 0.025 x 1.0 m`) for dressing room garment. Frozen from [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L601). | Shaped garment mesh (triangular prism with 3 distinct x coordinates). | `False` | Real raises `ValueError` (`PartError: bare rectangular proxy for garment`). Clean instantiates `Part` successfully. |

---

## Deep Dive: Scene and Geometry Builders

### 1. `l0587` (`villa_furnish3d_spec_details`)
- **Defect Background**: In Option D1, approved detail elements authored in the specification (such as bathroom extract grilles and acoustic baffles) were omitted by the Revit family placement pass without triggering an error.
- **Production Guard**: [`villa_furnish3d.round2_postcondition(spec, readback, layout)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish3d.py#L555) cross-checks all elements declared in `villa_furnish3d.round2_elements(spec)` against the read-back details. When an approved detail row is absent, it reports `<mark>: built 0 times`.
- **Adapter Logic**: [`check_round2_spec_details`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) invokes `round2_postcondition` and fails closed (`ValueError`) if any detail was built 0 times. Clean read-back passes with zero problems.

### 2. `l0589` (`villa_furnish3d_stair_glass_boundary`)
- **Defect Background**: The open-side frameless glass balustrade extrusion projected 10 mm outside the bounding rectangle of room `stair-b`, intersecting adjacent wall finishes.
- **Production Guard**: [`villa_furnish3d.round2_postcondition`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish3d.py#L584) checks every detail row with an associated room against `lay["rooms"][room]["rect"]` and appends `<mark>: leaves room <room>`.
- **Adapter Logic**: [`check_round2_stair_glass_boundary`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) fails closed (`ValueError`) on room escape. Clean read-back stays strictly inside room bounds.

### 3. `l0047` (`physical_part_solid_winding`)
- **Defect Background**: A closed headboard mesh exported with all faces consistently connected nevertheless had inward-pointing surface normals and negative signed volume due to clockwise face vertex ordering.
- **Production Guard**: [`physical_part.geometry_errors`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/physical_part.py#L104) computes signed volume via tetrahedra cross-dot products and reports `"inward-facing solid"` if closed mesh volume is negative.
- **Adapter Logic**: [`check_physical_part_solid_winding`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) fails closed (`ValueError`) when inward-facing solid errors are found. Outward-wound CCW box returns empty errors.

### 4. `l0686` (`villa_render_contract_zero_area_triangles`)
- **Defect Background**: Loft ring corner radiuses produced collinear vertices generating 1,780 zero-area degenerate triangles that caused the workstation renderer to abort scene ingestion.
- **Production Guard**: [`villa_render_contract.validate_scene`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/villa_render_contract.py#L201) checks mesh face normals and cross-product areas, appending `degenerate polygon` when normal calculation fails or polygon area is zero.
- **Adapter Logic**: [`check_render_contract_scene_geometry`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) executes `validate_scene` and fails closed (`ValueError`) on degenerate polygons. Valid quad meshes return empty error lists.

### 5. `l0069` (`physical_part_duvet_footprint`)
- **Defect Background**: Procedural duvet drape shifted 0.6 m along the bed length, hanging off the mattress support onto the floor.
- **Production Guard**: [`physical_part.Part`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/physical_part.py#L141) verifies `duvet` vertices against the declared `support` footprint `(x0, y0, x1, y1)` and raises `PartError("duvet leaves mattress footprint")`.
- **Adapter Logic**: [`check_physical_part_duvet_footprint`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) instantiates `Part(kind="duvet", support=...)`. Shifted duvet raises `PartError` (subclass of `ValueError`), while centered triangular prism passes.

### 6. `l0878` (`physical_part_climber_proxy`)
- **Defect Background**: A climbing trellis plant was modeled as an unshaped 80 mm rectangular box proxy floating in air.
- **Production Guard**: [`physical_part.Part`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/physical_part.py#L130) executes `_rectangular_proxy(faces)`. Since `climber` is not in `BOX_KINDS`, rectangular proxies are rejected with `PartError("bare rectangular proxy for climber")`.
- **Adapter Logic**: [`check_physical_part_climber_proxy`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls `Part(kind="climber", solid=faces)`. Rectangular box raises `ValueError`, while shaped prism passes.

### 7. `l0923` (`physical_part_garment_proxy`)
- **Defect Background**: Dressing room hanging garments were represented as flat 25 mm rectangular vertical slabs.
- **Production Guard**: [`physical_part.Part`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/physical_part.py#L130) rejects rectangular proxy slabs for `garment`, raising `PartError("bare rectangular proxy for garment")`.
- **Adapter Logic**: [`check_physical_part_garment_proxy`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls `Part(kind="garment", solid=faces)`. Flat slab raises `ValueError`, while shaped prism passes.

---

## Uncovered Lesson Analysis: l0046

### `l0046` (`l0046-fine-extraction-exposed`)
- **Audit Row**: Current enforcement: `revit/probe_fixture_geometry.py`. Proposed control: `Change src/archpipe/concept/villa_furnish3d.py: Require typed physical solids and local axes at builder boundaries`.
- **Learnings Entry**: "Fine extraction exposed a 1,828.8 mm housing across the west wall and 2,624-triangle light-source display webs below the ceiling." ([`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L178)).
- **Codebase Status**: [`revit/probe_fixture_geometry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/revit/probe_fixture_geometry.py) is a standalone manual IronPython diagnostic probe script designed to inspect family instance geometry inside an active Revit document. It is not an automated assertion, pipeline step, or regression guard in `archpipe` or `tests/`. No automated production guard currently verifies or rejects 1,828.8 mm housing spans or light-source display web triangles during export.
- **Disposition**: Per prompt instruction (*"Find the EXISTING guard in the code that prevents or catches it (do not write new production logic unless no guard exists; if none exists, record the lesson as 'no guard yet' in the report and do NOT fake one)"*), `l0046` is honestly recorded as **no guard yet** and retained in `uncovered_lessons`.

---

## Needs Real Case Analysis: l0059

### `l0059` (`l0059-no-sunlight-entered`)
- **Audit Row**: Current enforcement: `NONE`. Proposed control: `Change src/archpipe/concept/villa_furnish3d.py: Require typed physical solids and local axes at builder boundaries`.
- **Learnings Entry**: "No sunlight entered: a refractive glass slab blocks Cycles shadow rays, so sun/sky arrived only as caustics." ([`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L210)).
- **Why Needs Real Case**: Production logic exists in [`render_qa.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/render_qa.py) for image illumination quality, but the historical defective rendering showing an unlit interior where shadow-ray blocking occurred is not present in repository test fixtures. Synthetic renders cannot prove physical optical transport calibration. Registered under `render_qa_glass_daylight_transmission` with `needs_real_case=True`.

---

## Coverage Audit Metrics

Audit evaluation against [`docs/lessons-audit.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md) via [`audit_lesson_coverage`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L509):

| Metric | Before Batch 3 | After Batch 3 | Net Change |
|---|---|---|---|
| **Total Lessons Tracked** | 217 | 217 | 0 |
| **Covered by Guard** | 48 | **55** | +7 (`l0047`, `l0069`, `l0587`, `l0589`, `l0686`, `l0878`, `l0923`) |
| **Covered by Review Step** | 21 | **21** | 0 |
| **Needs Real Case** | 9 | **10** | +1 (`l0059`) |
| **Uncovered Lessons** | 139 | **131** | -8 (-7 guard, -1 needs real case; `l0046` remains uncovered) |
| **Inventory Sum Check** | 217 | **217** | 55 + 21 + 10 + 131 = 217 (exact invariant) |

The new uncovered count reported by [`report_uncovered_lessons`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L617) is **131**.

---

## Changed Files List

Only the following files were modified or created in this batch:

1. [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py):
   - Exported adapter symbols: `check_round2_spec_details`, `check_round2_stair_glass_boundary`, `check_physical_part_solid_winding`, `check_render_contract_scene_geometry`, `check_physical_part_duvet_footprint`, `check_physical_part_climber_proxy`, `check_physical_part_garment_proxy`.
   - Defined fixtures: `_d1_round2_fixtures()`, `_make_box_faces()`, `_make_triangular_prism_faces()`.
   - Registered 8 guards: `villa_furnish3d_spec_details` (`l0587`), `villa_furnish3d_stair_glass_boundary` (`l0589`), `physical_part_solid_winding` (`l0047`), `villa_render_contract_zero_area_triangles` (`l0686`), `physical_part_duvet_footprint` (`l0069`), `physical_part_climber_proxy` (`l0878`), `physical_part_garment_proxy` (`l0923`), and `render_qa_glass_daylight_transmission` (`l0059`, `needs_real_case=True`).

2. [`tests/test_guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_guard_registry.py):
   - Updated count assertions in `test_coverage_audit_parses_real_lessons_audit_md` to 55, 21, 10, 131.
   - Appended Batch 3 lesson IDs to `expected_guard_lessons`, `deleted_reimplementation_lessons` (`l0046`), and `expected_needs_real_case` (`l0059`).
   - Added `test_phase2_batch3_scene_and_geometry_guards_execution` asserting real (fires) and clean (quiet) execution across all new guards.

3. [`docs/reg3-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/reg3-report.md):
   - Created this Batch 3 report.

---

## Verification Evidence and Review Readiness

1. **Meta-Guard Compliance**:
   All seven newly defined functions in [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) delegate directly to production functions in [`archpipe.concept.villa_furnish3d`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish3d.py), [`archpipe.concept.physical_part`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/physical_part.py), or [`archpipe.villa_render_contract`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/villa_render_contract.py). The AST parser in `test_meta_guard_guard_registry_functions_call_production_modules` detects and approves these calls.

2. **No Emojis**:
   All new Python code and markdown documentation contain zero emojis across identifiers, comments, and docstrings.

3. **Strict Invariant Maintained**:
   The four audit categories (`covered_by_guard`: 55, `covered_by_review`: 21, `needs_real_case`: 10, `uncovered`: 131) sum exactly to 217.

4. **Strict Mode Untouched**:
   `scripts/verify.py` remains in permissive mode per task constraints.
