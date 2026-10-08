---
Document Outline:
  - [Executive Summary](#executive-summary)
  - [Phase 2 Batch 8 Overview](#phase-2-batch-8-overview)
  - [Registered Guards and Lesson Coverage](#registered-guards-and-lesson-coverage)
  - [Grouping and Mapping Justification](#grouping-and-mapping-justification)
  - [Examined Lessons Left Uncovered](#examined-lessons-left-uncovered)
  - [Execution Timing and Performance](#execution-timing-and-performance)
  - [Coverage Accounting and Audit Reconciliation](#coverage-accounting-and-audit-reconciliation)
  - [Files Modified](#files-modified)
Executive Summary: |
  This report documents Phase 2, Batch 8 of the lesson guard registry migration for archpipe.
  Seven previously uncovered lessons are now registered across 6 new production guards and 1 extended existing guard, covering
  falsy-zero lint protection, handrail finished-face plaster mounting, authored design dimensions preservation,
  intent-based view subject presence and framing, camera foliage clearance, under-stair storage profiles, and windowless store illuminance.
  All guards delegate directly to production modules, execute in under 30 milliseconds combined,
  and strictly preserve the 217-lesson accounting invariant (110 covered by guard, 21 review, 10 needs real case, 76 uncovered).
---

# Executive Summary

This report documents Phase 2, Batch 8 of the lesson guard registry migration for archpipe. Seven previously uncovered lessons are now registered across 6 new production guards and 1 extended existing guard, covering falsy-zero lint protection, handrail finished-face plaster mounting, authored design dimensions preservation, intent-based view subject presence and framing, camera foliage clearance, under-stair storage profiles, and windowless store illuminance. All guards delegate directly to production modules, execute in under 30 milliseconds combined, and strictly preserve the 217-lesson accounting invariant (110 covered by guard, 21 review, 10 needs real case, 76 uncovered).

# Phase 2 Batch 8 Overview

Phase 2 Batch 8 prioritises Revit/extract/read-back, stair/opening/route geometry, and lighting-measurement subsystems with existing production controls:
1. **Falsy-Zero Code Lint ([`archpipe.safe_io.encode`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/safe_io.py))**: Extended existing guard `safe_io_falsy_zero_lint` to register lesson `l0066`, preventing expressions of the form `float(x or <nonzero>)` that swallow explicit zeroes on lighting and energy inputs.
2. **Finished Face Handrail Mounting ([`archpipe.concept.mounting.check_mesh`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/mounting.py))**: Registers `mounting_handrail_finished_face` (`l0856`), verifying that wall handrails mount clear of plaster faces within 1 mm tolerance using the historical failing coordinates from `tests/test_mounting_scene.py`.
3. **Authored Design Dimensions Preservation ([`archpipe.concept.authored_guard.unexplained_changes`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/authored_guard.py))**: Registers `authored_guard_unexplained_changes` (`l0099`), ensuring that authored dimensions cannot be modified or defaulted without an explicit, non-empty audit override record.
4. **View Subject Presence and Intent Framing ([`archpipe.concept.render_views.choose`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/render_views.py), [`archpipe.concept.villa_furnish.layout`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py))**: Registers `render_views_subject_presence` (`l0830`), failing closed when declared camera view subjects are missing from the room layout or fail to fit fully within the sensor frame.
5. **Camera Canopy Proximity Clearance ([`archpipe.concept.villa_landscape.prop_world_box`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_landscape.py))**: Registers `villa_landscape_camera_canopy_clearance` (`l0973`), checking that camera viewpoints do not stand inside or within 1.0 m of prop foliage canopies, frozen from the historical v26 top-garden olive defect.
6. **Under-Stair Storage Profile and Soffit Clearance ([`archpipe.concept.villa_furnish.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py))**: Registers `villa_furnish_under_stair_storage_profile` (`l0984`), validating that required under-stair storage joinery units are present and fit within the descending stair soffit.
7. **Windowless Store Maintained Illuminance ([`archpipe.concept.villa_lighting.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_lighting.py))**: Registers `villa_lighting_windowless_store_target` (`l0989`), validating that windowless storage rooms (`store-ramp`) achieve maintained direct illuminance targets (`ies-res-storage-frequent-50`), catching historical v30 pitch-black renders when lighting was omitted.

# Registered Guards and Lesson Coverage

A total of 7 uncovered lessons were registered across 6 new production guards and 1 extended existing guard:

| Lesson ID | Guard Name | Guard Function | Real Case Source | Clean Case | Needs Real Case | Execution Time |
|---|---|---|---|---|---|---|
| `l0066` (`l0066-lights-could-not`) | `safe_io_falsy_zero_lint` | `check_falsy_zero_lint` | String expression `'energy = P * float(fx.get("output") or 1.0)'` swallowing explicit zero output | Clean expression `'energy = P * (float(fx["output"]) if fx.get("output") is not None else 1.0)'` | `False` | < 0.1 ms |
| `l0856` (`l0856-stair-s-wall`) | `mounting_handrail_finished_face` | `check_mounting_handrail_finished_face` | Historical coordinates from [`tests/test_mounting_scene.py#L46`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_mounting_scene.py#L46) with rail at `y=-28.611`, buried 140 mm behind wall face (-225 mm error) | Clean rail mesh positioned at `y=-28.386`, exactly 85 mm clear of plaster face | `False` | < 0.1 ms |
| `l0099` (`l0099-design-dimensions-silent`) | `authored_guard_unexplained_changes` | `check_authored_guard_unexplained_changes` | Declared dimensions `{"mounting_height": 0, "ceiling_height": 2700}` modified in written record to 2400 without override entry | Clean written record with explicit audit override entry: `{"field": "mounting_height", "prior": 0, "new": 2400, "reason": "ADR-0012 updated mounting height"}` | `False` | < 0.1 ms |
| `l0830` (`l0830-view-subject-can`) | `render_views_subject_presence` | `check_render_views_subject_presence` | D1 layout in `parents-dressing` requesting stale/outlived subject `["historical-stale-wardrobe"]` | Nominal D1 layout in `parents-dressing` requesting existing fixture `["pd-hang-1"]` with 24mm lens and cached spec | `False` | ~2 ms |
| `l0973` (`l0973-v26-camera-stood`) | `villa_landscape_camera_canopy_clearance` | `check_villa_landscape_camera_canopy_clearance` | Historical v26 camera position `[14.5, -22.0, 1.35]` standing inside the top-garden olive tree (`landscape-top-olive`) canopy ([tests/test_render_views.py#L108](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_render_views.py#L108)) | Clean camera position `[9.0, -20.80, 1.35]` located > 4 m clear of the olive tree | `False` | < 0.1 ms |
| `l0984` (`l0984-v29-missed-under`) | `villa_furnish_under_stair_storage_profile` | `check_villa_furnish_under_stair_storage_profile` | Cached D1 furniture items with `stair-flight-store` omitted | Nominal cached D1 furniture items with complete under-stair storage | `False` | ~10 ms |
| `l0989` (`l0989-v30-read-black`) | `villa_lighting_windowless_store_target` | `check_villa_lighting_windowless_store_target` | Cached D1 lighting fixtures with all `store-ramp` luminaires omitted (achieved 0 lx < 50 lx required) | Nominal cached D1 lighting fixtures achieving required maintained lux | `False` | ~15 ms |

# Grouping and Mapping Justification

1. **`l0066` into `safe_io_falsy_zero_lint`**: Both `l0066` and `l0067` share the exact defect class where an authored or calculated value of `0` or `0.0` was swallowed by python falsy-coalescing `x or default`, substituting a non-zero default when zero was intended. The existing `safe_io_falsy_zero_lint` check directly scans and catches this anti-pattern.
2. **`l0856` into `mounting_handrail_finished_face`**: Stair wall handrail was mounted to the unfinished core instead of the finished plaster face, leaving it buried in plaster. [`archpipe.concept.mounting.check_mesh`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/mounting.py) measures signed vertex error relative to declared finished face datums, enforcing a 1 mm tolerance.
3. **`l0099` into `authored_guard_unexplained_changes`**: Authored dimensions (such as ceiling and sill heights) were silently altered or defaulted without audit trails. [`archpipe.concept.authored_guard.unexplained_changes`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/authored_guard.py) enforces full provenance and non-empty reasons for every field modification.
4. **`l0830` into `render_views_subject_presence`**: View subjects outlived the pieces they named as the layout evolved. [`archpipe.concept.render_views.choose`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/render_views.py) and [`archpipe.concept.villa_furnish.layout`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py) verify that named subjects exist and are frameable within camera frustum bounds.
5. **`l0973` into `villa_landscape_camera_canopy_clearance`**: The v26 camera stood inside the potted olive tree foliage canopy. [`archpipe.concept.villa_landscape.prop_world_box`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_landscape.py) transforms prop bounding boxes to scene coordinates, verifying that cameras maintain >= 1.0 m clearance from vegetative canopies.
6. **`l0984` into `villa_furnish_under_stair_storage_profile`**: The v29 camera missed the under-stair storage module because the casework and modules were omitted or misplaced. [`archpipe.concept.villa_furnish.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_furnish.py) enforces the presence of `stair-flight-store` and `stair-landing-store`, sliding doors, and headroom clearance beneath the stair soffit.
7. **`l0989` into `villa_lighting_windowless_store_target`**: The v30 view of the windowless store read pitch black without artificial illumination. [`archpipe.concept.villa_lighting.check`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/concept/villa_lighting.py) validates that `store-ramp` achieves the maintained 50 lx direct illuminance requirement (`ies-res-storage-frequent-50`).

# Examined Lessons Left Uncovered

The following candidate lessons were audited against production code and tests but left uncovered because no standalone deterministic production control currently exists without external toolchains or live simulation dependencies:

1. **`l0180-thermal-hand-check`**: Thermal hand-check and solar heat gain verification; requires external EnergyPlus/Radiance simulation engines.
2. **`l0181-energyplus-fatal-errors`**: EnergyPlus simulation fatal errors during building energy analysis; requires external EnergyPlus IDF compiler and weather file runtimes.
3. **`l0026-blender-ies-azimuth`**: Blender IES azimuthal rotation orientation; requires live Blender Cycles rendering engine execution.
4. **`l0080-lamps-rendered-far`**: Photometric emitter placement distance; requires full scene rendering and camera probe.
5. **`l0090-window-glass-passed`**: Window glass transmission in Cycles; requires live Cycles ray-tracing engine.
6. **`l0656-glass-verified`**: Glass verification in render; requires live Cycles rendering probe.
7. **`l0046-fine-extraction-exposed`**: Revit fine geometry extraction exposure; managed by native Revit UI/API in C#/.NET rather than internal Python validation rule.
8. **`l0177-good-texture-poly` & `l0178-good-model-failed`**: External Poly Haven mesh/texture crawler format validation; lacks deterministic internal production control.

# Execution Timing and Performance

To keep test runtimes low and maintain test suite agility:
- Module-level pre-calculated fixtures (`_lay_d1_base`, `_cached_spec()`, `_cached_furnish_layout()`, `_fx_lighting_clean`) are reused rather than rebuilding the full villa layout.
- `safe_io_falsy_zero_lint`: < 0.1 ms.
- `mounting_handrail_finished_face`: < 0.1 ms.
- `authored_guard_unexplained_changes`: < 0.1 ms.
- `render_views_subject_presence`: ~2 ms.
- `villa_landscape_camera_canopy_clearance`: < 0.1 ms.
- `villa_furnish_under_stair_storage_profile`: ~10 ms.
- `villa_lighting_windowless_store_target`: ~15 ms.
- **Total Combined Overhead**: < 30 milliseconds across all 7 guard test cases.

# Coverage Accounting and Audit Reconciliation

After registering the 7 lessons in Batch 8:

- `covered_by_guard`: **110** (previously 103, +7)
- `covered_by_review`: **21** (unchanged)
- `needs_real_case`: **10** (unchanged)
- `uncovered`: **76** (previously 83, -7)
- **Total Lessons**: **217** (`110 + 21 + 10 + 76 = 217`)

All 4 categories strictly sum to 217, preserving the audit accounting invariant.

# Files Modified

Only the following files were modified in this batch:
1. [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py): Exported 6 new guard check functions in `__all__`, imported `mounting`, extended `safe_io_falsy_zero_lint` with `l0066`, and registered guards #77 through #82.
2. [`tests/test_guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_guard_registry.py): Updated coverage count assertions (`covered_by_guard_count=110`, `uncovered_count=76`) and appended 7 Batch 8 lesson IDs to `expected_guard_lessons`.
3. [`docs/reg8-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/reg8-report.md): This report.
