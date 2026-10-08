---
Document Outline:
  - [Executive Summary](#executive-summary)
  - [Phase 2 Batch 4 Registration Overview](#phase-2-batch-4-registration-overview)
  - [Lesson-by-Lesson Guard Registration Details](#lesson-by-lesson-guard-registration-details)
  - [Deep Dive: Geometry, Stairs, Openings, Routes & Readback](#deep-dive-geometry-stairs-openings-routes--readback)
  - [Grouping Justifications](#grouping-justifications)
  - [Uncovered Lessons Analysis](#uncovered-lessons-analysis)
  - [Coverage Audit Metrics](#coverage-audit-metrics)
  - [Changed Files List](#changed-files-list)
  - [Verification Evidence and Review Readiness](#verification-evidence-and-review-readiness)
  - [Fix Round 1](#fix-round-1)
Executive Summary:
  This report documents Phase 2 Batch 4 of the defect guard registry migration covering geometry, stairs, openings, routes, landscape extents, render support, and Revit readback across 14 audited lessons. Eleven active guards were registered using existing production functions in villa, stairs, villa_furnish, villa_landscape, render_support, and villa_furnish3d with frozen real defect cases and clean cases. Three examined lessons lacking automated production controls were recorded as uncovered, leaving 117 uncovered lessons and maintaining the 217-lesson inventory invariant.
---

# Phase 2 Batch 4 Guard Registration Report

## Executive Summary

This report documents Phase 2 Batch 4 of the defect guard registry migration ([`docs/guard-registry.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/guard-registry.md) Section 8, Step 1) covering **geometry, stairs, openings, routes, landscape extents, render support, and Revit readback** across 14 audited lessons ([`l0310`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0312`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0319`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0504`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0512`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0531`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0557`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0576`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0591`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0695`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0713`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0820`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0834`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0863`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)).

Eleven active guards have been registered using production functions in [`src/archpipe/concept/villa.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa.py), [`src/archpipe/concept/stairs.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/stairs.py), [`src/archpipe/concept/villa_furnish.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py), [`src/archpipe/concept/villa_landscape.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_landscape.py), [`src/archpipe/concept/render_support.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/render_support.py), and [`src/archpipe/concept/villa_furnish3d.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish3d.py), proven on frozen real failure cases and clean quiet cases. Three examined candidate lessons ([`l0030`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0286`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0856`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)) were confirmed to lack production-level pipeline controls and are retained in the uncovered lessons list. In total, covered lessons by guard increased from 55 to 69, lessons flagged `needs_real_case` remained at 10, review steps remained at 21, and uncovered lessons dropped from 131 to 117, strictly preserving the 217-lesson inventory invariant.

---

## Phase 2 Batch 4 Registration Overview

Per [`docs/guard-registry.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/guard-registry.md) Section 8 (Step 1), Phase 2 Batch 4 migration targets geometry, stair pitch and circulation void width, door clearances, route sweep disc transitions, kitchen module spans, landscape property and route boundaries, render support physical resting checks, and Revit opening read-back postconditions.

In accordance with project integrity standards:
- All registered guard functions call production modules ([`archpipe.concept.villa`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa.py), [`archpipe.concept.stairs`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/stairs.py), [`archpipe.concept.villa_furnish`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py), [`archpipe.concept.villa_landscape`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_landscape.py), [`archpipe.concept.render_support`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/render_support.py), or [`archpipe.concept.villa_furnish3d`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish3d.py)), satisfying the AST meta-guard in [`tests/test_guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_guard_registry.py). Local re-implementations inside `guard_registry.py` were strictly avoided.
- Real defect cases were frozen **by value** directly from historical incidents documented in [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md) and regression test suites ([`tests/test_stairs.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_stairs.py), [`tests/test_villa_parking.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_villa_parking.py), [`tests/test_d1_wp3.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_d1_wp3.py), [`tests/test_villa_landscape.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_villa_landscape.py), [`tests/test_render_support.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_render_support.py), [`tests/test_d1_wp5.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_d1_wp5.py)). No mutable live outputs under `out/` are referenced.
- No dummy or fake production logic was authored for examined lessons lacking production checks ([`l0030`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0286`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md), [`l0856`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md)); they are preserved as uncovered ("no guard yet").

---

## Lesson-by-Lesson Guard Registration Details

| Lesson ID | Guard Name | Production Function | Real Failing Case & Source | Clean Quiet Case | needs_real_case | Status / Notes |
|---|---|---|---|---|---|---|
| `l0312`, `l0310`, `l0319` | `villa_concept_stair_access` | [`check_villa_concept_stair_access`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`villa.critique`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa.py#L650) | Concept A layout with stair-b end terminating at wall coordinate without circulation connection. Frozen from [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L312). | Baseline `villa.concept_a()` where all stair ends open onto connected circulation corridors. | `False` | Real raises `ValueError("Stair access check failed: ...")`. Clean returns check dict with status pass. |
| `l0504` | `stair_pitch_headroom` | [`check_stair_pitch_headroom`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`stairs.pitch_headroom`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/stairs.py#L358) | R8 party flight stair under short slab opening `[5177, -28421, 8537, -27471]` giving 1957.5 mm headroom (< 2000 mm). Frozen from [`tests/test_stairs.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_stairs.py#L60). | R8 party flight stair under lengthened opening `[5177, -28421, 8887, -27471]` giving 2073.0 mm headroom (>= 2000 mm). | `False` | Real raises `ValueError("Stair pitch headroom 1957.5 mm is below required 2000.0 mm")`. Clean returns 2073.0. |
| `l0512` | `villa_route_width_stair_void` | [`check_villa_route_width_stair_void`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`villa.gf_route_width`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa.py#L604) | Villa parking Option 0 with corridor pinched to 0.57 m around stair void. Frozen from [`tests/test_villa_parking.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_villa_parking.py#L45). | Nominal `villa_parking.options()[0]` with 1.14 m clear route around void. | `False` | Real raises `ValueError("GF route width around stair void 0.57 m is below minimum 0.90 m")`. Clean returns 1.14. |
| `l0557` | `villa_furnish_door_wall_clearance` | [`check_villa_furnish_door_wall_clearance`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`villa_furnish.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py#L828) | Option D1 layout with parents-dressing door shifted to y=22.10 running into perpendicular wall corner. Frozen from [`tests/test_d1_wp3.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_d1_wp3.py#L50). | Baseline `villa_r11.design("D1")` layout with compliant door clearance. | `False` | Real raises `ValueError("Door clearance check failed: ...")`. Clean returns doors check dict with status pass. |
| `l0576`, `l0531` | `villa_furnish_route_corner_disc` | [`check_villa_furnish_route_corner_disc`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`villa_furnish.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py#L828) | Option D1 furniture layout with wardrobe unit pd-hang-2 shifted by cy+=0.24 pinching route turn below 600 mm disc. Frozen from [`tests/test_d1_wp3.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_d1_wp3.py#L80). | Baseline D1 layout and furniture with unobstructed 600 mm disc sweep. | `False` | Real raises `ValueError("Route corner disc clearance check failed: ...")`. Clean returns routes check dict with status pass. |
| `l0591` | `villa_furnish_kitchen_run_modules` | [`check_villa_furnish_kitchen_run_modules`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`villa_furnish.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py#L828) | Option D1 furniture layout where dirty kitchen run dk-run has overrunning 0.4 m counter module. Frozen from [`tests/test_d1_wp3.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_d1_wp3.py#L95). | Baseline D1 furniture layout with kitchen modules matching wall run length. | `False` | Real raises `ValueError("Kitchen module checks failed: ...")`. Clean returns kitchen check dict with status pass. |
| `l0820` | `villa_landscape_prop_room_extent` | [`check_villa_landscape_prop_room_extent`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`villa_landscape.extent_violations`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_landscape.py#L380) | Searsia lucida prop at (13.25, -21.65) penetrating basement room guest-living. Frozen from [`tests/test_villa_landscape.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_villa_landscape.py#L85). | Nominal built landscape props tested against garden-level rooms. | `False` | Real raises `ValueError("Landscape prop extent violations: [('draft-searsia', 'enters room guest-living')]")`. Clean returns empty list. |
| `l0834` | `villa_landscape_route_obstruction` | [`check_villa_landscape_route_obstruction`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`villa_landscape.route_violations`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_landscape.py#L400) | Teak sofa placed at rect (24.0, -26.25, 26.1, -25.40) obstructing terrace-main walking corridor. Frozen from [`tests/test_villa_landscape.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_villa_landscape.py#L110). | Built landscape items maintaining required clearance across all defined paths. | `False` | Real raises `ValueError("Landscape route violations: [('draft-teak-sofa', 'obstructs route terrace-main')]")`. Clean returns empty list. |
| `l0695` | `render_support_unsupported_objects` | [`check_render_support_unsupported`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`render_support.unsupported`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/render_support.py#L120) | Scene containing floating lamp shade mesh suspended at z=2.5 with no supporting geometry underneath. Frozen from [`tests/test_render_support.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_render_support.py#L30). | Scene containing floor slab and table resting on floor slab. | `False` | Real raises `ValueError("Floating unsupported scene items detected: ['lamp-floating-shade']")`. Clean returns empty list. |
| `l0713` | `render_support_blocked_openings` | [`check_render_support_blocked_openings`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`render_support.blocked_openings`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/render_support.py#L170) | Unconstrained slatted headboard panel extending 0.6 m past bed each way into parents-entry opening and dressing door envelope. Frozen from [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L880). | Headboard slats constrained to solid wall backing, keeping passages clear. | `False` | Real raises `ValueError("Blocked openings detected in scene: ...")`. Clean returns empty list. |
| `l0863` | `villa_furnish3d_opening_spec_id` | [`check_villa_furnish3d_opening_spec_id`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) calls [`villa_furnish3d.round2_postcondition`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish3d.py#L555) | Revit readback with wall opening hatch lacking mark, comments, and spec_id. Frozen from [`tests/test_d1_wp5.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_d1_wp5.py#L125). | Readback where hatch includes spec_id matching specification id. | `False` | Real raises `ValueError("Revit wall opening readback postcondition failed: ['hatch hatch-01: missing in readback']")`. Clean returns empty list. |

---

## Deep Dive: Geometry, Stairs, Openings, Routes & Readback

### 1. `l0312`, `l0310`, `l0319` (`villa_concept_stair_access`)
- **Defect Background**: In early concept critiques, stairs were evaluated either in isolation or with unconstrained endpoints, allowing flight ends to land against boundary walls rather than circulation paths.
- **Production Guard**: [`villa.critique(lay)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa.py#L650) executes check `"stair_access"`, verifying that both top and bottom stair segments terminate in rooms classified under circulation or hall zones.
- **Adapter Logic**: [`check_villa_concept_stair_access`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) verifies that the `stair_access` check is present and reports status `"pass"`. When endpoints hit solid walls, it fails closed with `ValueError`.

### 2. `l0504` (`stair_pitch_headroom`)
- **Defect Background**: Opening cuts in floor slabs were computed based on floor-to-floor heights rather than tracking vertical headroom perpendicular along the pitch line under the soffit, resulting in head clearances dropping to 1957.5 mm.
- **Production Guard**: [`stairs.pitch_headroom(stair, opening_mm)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/stairs.py#L358) traces each step riser/going edge along the 3D pitch line against the slab opening bounding polygon and calculates the least clearance under the soffit.
- **Adapter Logic**: [`check_stair_pitch_headroom`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) asserts that least clearance meets or exceeds the required 2000 mm threshold.

### 3. `l0512` (`villa_route_width_stair_void`)
- **Defect Background**: Modifications to ground floor rooms adjacent to the stair void reduced clear circulation passage width into the bedroom wing to 0.57 m, creating an illegal pinch point.
- **Production Guard**: [`villa.gf_route_width(lay)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa.py#L604) evaluates minimum horizontal distance between the void enclosure edge and enclosing partitions.
- **Adapter Logic**: [`check_villa_route_width_stair_void`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) fails closed if calculated route width drops below the 0.90 m minimum corridor standard.

### 4. `l0557` (`villa_furnish_door_wall_clearance`)
- **Defect Background**: Door positions specified close to partition intersections allowed door swings to collide with perpendicular return walls.
- **Production Guard**: [`villa_furnish.check(items, lay)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py#L828) validates `"doors"` clearance by computing swing envelopes against intersecting wall geometry.
- **Adapter Logic**: [`check_villa_furnish_door_wall_clearance`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) evaluates `res["doors"]` and fails closed on collision problems.

### 5. `l0576`, `l0531` (`villa_furnish_route_corner_disc`)
- **Defect Background**: Simplified rectangular body models or straight-line paths failed to catch pinch points when turning corners, where a human body sweep requires a 600 mm circular disc clearance throughout the corner arc.
- **Production Guard**: [`villa_furnish.check(items, lay)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py#L828) tests `"routes"` clearance using disc offset path sweeping around corners.
- **Adapter Logic**: [`check_villa_furnish_route_corner_disc`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) checks `res["routes"]` and raises `ValueError` if any corner turn pinches the clearance envelope.

### 6. `l0591` (`villa_furnish_kitchen_run_modules`)
- **Defect Background**: Kitchen modular unit planning placed standard counter modules that accumulated beyond the available wall length.
- **Production Guard**: [`villa_furnish.check(items, lay)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py#L828) validates `"kitchen"` runs by checking the sum of individual module widths against declared wall run lengths.
- **Adapter Logic**: [`check_villa_furnish_kitchen_run_modules`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) verifies `res["kitchen"]` and raises `ValueError` on overruns.

### 7. `l0820` (`villa_landscape_prop_room_extent`)
- **Defect Background**: Landscape vegetation props placed on upper terraces or sloping ground penetrated downward through ceilings into lower-level habitable rooms.
- **Production Guard**: [`villa_landscape.extent_violations(props, rooms)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_landscape.py#L380) checks prop bounding boxes against garden-level rooms and reports room penetration.
- **Adapter Logic**: [`check_villa_landscape_prop_room_extent`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) fails closed if any prop enters building rooms.

### 8. `l0834` (`villa_landscape_route_obstruction`)
- **Defect Background**: Outdoor furniture placement on terraces obstructed primary walking corridors between interior doors and outdoor gardens.
- **Production Guard**: [`villa_landscape.route_violations(items, routes)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_landscape.py#L400) tests bounding rectangles of landscape elements against required path widths.
- **Adapter Logic**: [`check_villa_landscape_route_obstruction`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) fails closed on route obstruction.

### 9. `l0695` (`render_support_unsupported_objects`)
- **Defect Background**: Procedural dressing or fixture generation left objects floating in 3D space without physical floor, wall, or ceiling contact.
- **Production Guard**: [`render_support.unsupported(scene, lay)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/render_support.py#L120) verifies vertical or lateral contact between non-structural meshes/props and supporting architectural building geometry.
- **Adapter Logic**: [`check_render_support_unsupported`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) fails closed on floating objects.

### 10. `l0713` (`render_support_blocked_openings`)
- **Defect Background**: Dressing objects placed near doorways blocked door circulation envelopes, trapping simulated occupants or blocking sightlines.
- **Production Guard**: [`render_support.blocked_openings(scene, lay)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/render_support.py#L170) checks 3D mesh bounding volumes against door passage envelopes with non-zero thickness in z.
- **Adapter Logic**: [`check_render_support_blocked_openings`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) fails closed on doorway obstruction.

### 11. `l0863` (`villa_furnish3d_opening_spec_id`)
- **Defect Background**: Generic Revit wall opening extrusions lacking mark and comment parameters were dropped or misidentified during read-back.
- **Production Guard**: [`villa_furnish3d.round2_postcondition(spec, readback, layout)`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish3d.py#L555) matches openings using `spec_id` metadata when `mark` is empty.
- **Adapter Logic**: [`check_villa_furnish3d_opening_spec_id`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) fails closed when unmatched hatches are detected.

---

## Grouping Justifications

1. **`villa_concept_stair_access` covers `l0312`, `l0310`, and `l0319`**:
   - `l0312` (*"stair access check"*): Stair access validation requiring ends to terminate in circulation.
   - `l0310` (*"critic treated stair as independent"*): Critic treated stair independently rather than verifying connection to circulation.
   - `l0319` (*"check stair by endpoints"*): Stair endpoint verification against room connectivity.
   - **Justification**: All three audit rows represent the identical failure mode: assessing stairs without verifying that both endpoints connect to legal circulation corridors. The production check `villa.critique(lay)["checks"]["stair_access"]` directly evaluates both stair endpoints against room circulation properties.

2. **`villa_furnish_route_corner_disc` covers `l0576` and `l0531`**:
   - `l0576` (*"square body failed corner turn"*): Simplified square body approximation failed when rotating around interior corners.
   - `l0531` (*"body rounded down to disc for corner clearance"*): Circulation clearance requires disc sweep rather than point or bounding box checks around corners.
   - **Justification**: Both audit rows address the same geometric problem: swept volume clearance of the human body around corners. The production routine `villa_furnish.check(items, lay)["routes"]` implements circular disc sweeping to prevent pinch points.

---

## Uncovered Lessons Analysis

1. **`l0030` (`l0030-current-extract-lacks`)**:
   - **Audit Row**: Current enforcement: `NONE`. Proposed control: `Change revit/extract.py: enforce explicit orientation and handedness metadata in export schema`.
   - **Analysis**: No automated production schema check currently validates handedness or orientation metadata in extract JSON files. Preserved as uncovered ("no guard yet").

2. **`l0286` (`l0286-revit-probe-villa`)**:
   - **Audit Row**: Current enforcement: `revit/probe_villa_inventory.py`. Proposed control: `Automate inventory assertions in archpipe`.
   - **Analysis**: `revit/probe_villa_inventory.py` is a standalone IronPython diagnostic probe, not an automated pipeline check in `archpipe`. Preserved as uncovered ("no guard yet").

3. **`l0856` (`l0856-stair-s-wall`)**:
   - **Audit Row**: Current enforcement: `tests/test_render_standard.py:buried_behind_walls`. Proposed control: `Move buried wall check to archpipe production module`.
   - **Analysis**: The check exists solely in `tests/test_render_standard.py`. Per meta-guard rules, test helper functions cannot be called by guard registry adapters. Preserved as uncovered ("no guard yet").

---

## Coverage Audit Metrics

Audit evaluation against [`docs/lessons-audit.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md) via [`audit_lesson_coverage`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L545):

| Metric | Before Batch 4 | After Batch 4 | Net Change |
|---|---|---|---|
| **Total Lessons Tracked** | 217 | 217 | 0 |
| **Covered by Guard** | 55 | **69** | +14 (`l0310`, `l0312`, `l0319`, `l0504`, `l0512`, `l0531`, `l0557`, `l0576`, `l0591`, `l0695`, `l0713`, `l0820`, `l0834`, `l0863`) |
| **Covered by Review Step** | 21 | **21** | 0 |
| **Needs Real Case** | 10 | **10** | 0 |
| **Uncovered Lessons** | 131 | **117** | -14 |
| **Inventory Sum Check** | 217 | **217** | 69 + 21 + 10 + 117 = 217 (exact invariant) |

The new uncovered count reported by [`report_uncovered_lessons`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py#L696) is **117**.

---

## Changed Files List

Only the following files were modified or created in this batch:

1. [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py):
   - Added imports for `render_support`, `stairs`, `villa`, `villa_furnish`, `villa_parking`.
   - Exported 11 new check functions in `__all__`: `check_villa_concept_stair_access`, `check_stair_pitch_headroom`, `check_villa_route_width_stair_void`, `check_villa_furnish_door_wall_clearance`, `check_villa_furnish_route_corner_disc`, `check_villa_furnish_kitchen_run_modules`, `check_villa_landscape_prop_room_extent`, `check_villa_landscape_route_obstruction`, `check_render_support_unsupported`, `check_render_support_blocked_openings`, `check_villa_furnish3d_opening_spec_id`.
   - Registered 11 guards covering 14 lessons with frozen real failure cases and clean quiet cases.

2. [`tests/test_guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_guard_registry.py):
   - Updated count assertions in `test_coverage_audit_parses_real_lessons_audit_md` to 69, 21, 10, 117.
   - Appended Batch 4 lesson IDs to `expected_guard_lessons`.
   - Added `test_phase2_batch4_guards_execution` asserting real (fires) and clean (quiet) execution across all 11 new guards.

3. [`docs/reg4-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/reg4-report.md):
   - Created this Batch 4 report.

---

## Verification Evidence and Review Readiness

1. **Meta-Guard Compliance**:
   All 11 newly defined functions in [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) delegate directly to production functions in [`archpipe.concept.villa`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa.py), [`archpipe.concept.stairs`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/stairs.py), [`archpipe.concept.villa_furnish`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py), [`archpipe.concept.villa_landscape`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_landscape.py), [`archpipe.concept.render_support`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/render_support.py), or [`archpipe.concept.villa_furnish3d`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish3d.py). The AST parser in `test_meta_guard_guard_registry_functions_call_production_modules` validates and approves all delegating calls.

2. **No Emojis**:
   All new Python code, docstrings, comments, and markdown documentation contain zero emojis across identifiers, comments, and docstrings.

3. **Strict Invariant Maintained**:
   The four audit categories (`covered_by_guard`: 69, `covered_by_review`: 21, `needs_real_case`: 10, `uncovered`: 117) sum exactly to 217.

4. **Strict Mode Untouched**:
   `scripts/verify.py` remains in permissive mode per task constraints.

---

## Fix Round 1

Following the lead test suite run reported in `docs/reg4-lead-test-failures.log`, two Batch 4 guards exhibited case discrepancies under `tests.test_guard_registry`:

### 1. `render_support_unsupported_objects` (Clean Case Restructuring)
- **Problem**: The clean case defined `table-resting` using two detached horizontal quads (`z=0.0` and `z=0.8`) with no vertical faces. Because `render_support._islands()` groups faces by shared vertices, the two disconnected faces were partitioned into two independent islands. The top island at `z=0.8` did not touch the floor slab at `z=0.0` and was correctly flagged as a floating unsupported item (`[('table-resting', [0.5, 0.5, 0.8, 1.5, 1.5, 0.8])]`).
- **Fix**: Rebuilt `table-resting` in `_unsupported_clean_scene` as a continuous, closed 6-face rectangular box sharing all 8 vertices between `z=0.0` and `z=0.8`. As a single connected island whose lowest vertices lie at `z=0.0`, it rests flush against the `floor-slab` (`group: "building"`) at `z=0.0`. `render_support.unsupported` now returns `[]`, correctly verifying the clean quiet state.

### 2. `render_support_blocked_openings` (Real Defect Case Reproduction)
- **Problem**: The initial real case used a synthetic scene without the real villa layout geometry. `render_support.blocked_openings` resolves doorway positions from `revit_spec.build(lay)["doors"]` and derives doorless openings (0.6 m to 1.6 m wide) from shared room boundary edges. Without the real layout geometry, no doorway envelopes were registered, causing `blocked_openings` to return `[]` and failing to trigger the guard.
- **Fix**: Reconstructed the real failing case (`_blocked_real_scene`) with the authentic historical defect documented in [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L880) (`l0713`). A slatted headboard panel (`detail-headboard-slats`, `group: "furniture"`, `material: "oak"`) was placed along the bed headwall `y = -26.591`, extending 0.6 m past the bed width (`x` spanning `[18.93, 22.03]`). This spans directly across both:
  - The doorless passage between `parents-bed` and `parents-entry` (`y = -26.591`, `x` in `[18.427, 19.527]`), and
  - The ensuite dressing door (`y = -26.591`, centered at `x = 21.897`).
  `render_support.blocked_openings` identifies both blocked passages, causing the guard to fail closed with `ValueError`.
- **Clean Case**: The corresponding clean scene (`_blocked_clean_scene`) restricts the headboard slats strictly to solid wall backing (`x` in `[19.60, 21.40]`), preserving clear circulation across both doorways and returning `[]`.

### Coverage Invariant Verification
The four audit totals remain exactly at:
- `covered_by_guard`: **69**
- `covered_by_review`: **21**
- `needs_real_case`: **10**
- `uncovered`: **117**
- **Total**: 69 + 21 + 10 + 117 = **217** (exact invariant maintained)

### Files Actually Changed in Fix Round 1
Only the following files were modified in Fix Round 1:
1. [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py)
2. [`docs/reg4-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/reg4-report.md)
