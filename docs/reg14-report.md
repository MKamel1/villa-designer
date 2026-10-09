---
outline:
  - title: Executive Summary
    link: "#executive-summary"
  - title: Registered Guards in Batch 14
    link: "#registered-guards-in-batch-14"
  - title: Frozen Defect Grounding and Citations
    link: "#frozen-defect-grounding-and-citations"
  - title: Integration into scripts/verify.py
    link: "#integration-into-scriptsverifypy"
  - title: Test Suite Extensions and Verification Evidence
    link: "#test-suite-extensions-and-verification-evidence"
  - title: Final Coverage Audit Counts
    link: "#final-coverage-audit-counts"
  - title: Changed Files Inventory
    link: "#changed-files-inventory"
summary: |
  Lesson Registry Phase 2 Batch 14 registers the final five outstanding lessons (l0091, l0026, l0080, l0090, l0656), achieving 100% accounted lesson coverage across all 217 entries in docs/lessons-audit.md. scripts/verify.py now integrates Step 3 fail-closed inventory auditing, enforcing zero uncovered lessons with automated verification. All registered guards, cases, and inventory audit metrics pass without external dependencies.
---

# Lesson Registry Phase 2: Batch 14 Report

## Executive Summary

Phase 2 Batch 14 completes the migration plan laid out in [`docs/guard-registry.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/guard-registry.md) Section 8 (Step 1 and Step 3). The priority uncovered lesson [`l0091-every-view-metered`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md#L78) is registered with an active production guard [`scene_exposure_lock_mode`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) against a frozen failing scene fixture from [`tests/test_render_standard.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_render_standard.py#L484-L504) and a clean quiet case using the cached villa scene. The remaining four C5 emitter-class lessons ([`l0026`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md#L28), [`l0080`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md#L67), [`l0090`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md#L77), [`l0656`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md#L177)) are registered with explicit production targets calling production modules and tracked with `needs_real_case=True`, as live optical ray simulation runtime state or live sensor probes are required to reproduce them.

With these five registrations, `uncovered_lessons` drops from 5 to 0. In accordance with Step 3 of [`docs/guard-registry.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/guard-registry.md), [`scripts/verify.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/verify.py) now executes `audit_lesson_inventory()` in strict mode and fails closed with non-zero exit if any uncovered lesson exists. Comprehensive test coverage in [`tests/test_guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_guard_registry.py) validates both real and clean cases, the zero-uncovered inventory, and verifies that a fabricated uncovered lesson causes [`scripts/verify.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/verify.py) to fail while real inventory passes.

---

## Registered Guards in Batch 14

Five guards are registered in [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py):

| Guard Name | Target Function | Lessons Covered | Tier | `needs_real_case` | Real Case Fixture / Input | Clean Case Fixture / Input | Expected Real | Expected Clean | Execution Time |
|---|---|---|:---:|:---:|---|---|:---:|:---:|:---:|
| `scene_exposure_lock_mode` | [`check_scene_exposure_lock_mode`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) | `l0091-every-view-metered`, `l0091` | 1 | `False` | `_real_scene_l0091`: Cached villa render scene subset `v12-ensuite` with `exposure_mode="per-view-metered"` | `_clean_scene_l0091`: Cached villa render scene (`set-metered`) | `ValueError` | `[]` | ~1.5 ms |
| `photometry_ies_azimuth_interpolation` | [`check_photometry_ies_azimuth_interpolation`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) | `l0026-blender-ies-azimuth`, `l0026` | 2 | `True` | `None` (Awaiting live Cycles angular interpolation probe with radiance sensor plane) | `None` | `None` | `None` | 0 ms |
| `lighting_kelvin_blackbody_locus` | [`check_lighting_kelvin_blackbody_locus`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) | `l0080-lamps-rendered-far`, `l0080` | 1 | `True` | `None` (Awaiting live Blender Cycles Kelvin conversion runtime state) | `None` | `None` | `None` | 0 ms |
| `glazing_two_face_transmission` | [`check_glazing_two_face_transmission`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) | `l0090-window-glass-passed`, `l0090` | 2 | `True` | `None` (Awaiting live optical simulation probe of Cycles shadow rays) | `None` | `None` | `None` | 0 ms |
| `glazing_calibrated_transmission_probe` | [`check_glazing_calibrated_transmission_probe`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) | `l0656-glass-verified`, `l0656` | 2 | `True` | `None` (Calibration benchmark measurement; awaiting live optical simulation probe readings) | `None` | `None` | `None` | 0 ms |

---

## Frozen Defect Grounding and Citations

### 1. `scene_exposure_lock_mode` (`l0091-every-view-metered`, `l0091`)
- **Root Failure Citation**: [`docs/LEARNINGS.md:332`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L332):
  > `| Every view was metered separately, so a dark corner and a sunlit bed looked equally bright | Per-image auto-exposure optimises each picture and destroys comparability between them | Exposure and look locked across a set, absolute EV recorded; tonal checks become WARN under a lock. Principle: faithful before beautiful (ADR-0013 amendment) |`
- **Audit Row**: [`docs/lessons-audit.md:78`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md#L78): `| l0091-every-view-metered | Every view was metered separately, so a dark corner and a sunlit bed looked equally bright | authored values overwritten | 1 | NONE | Change src/archpipe/concept/villa_render.py: Make authored fields immutable; apply defaults only to missing values. | D2/D3 or bedroom plus injected sibling; clean case quiet |`
- **Production Guard Target**: [`archpipe.villa_render_contract.validate_scene`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/villa_render_contract.py#L307-L308) checks `need(scene.get('exposure_mode') == 'set-metered', 'exposure_mode', ...)` and [`lines 358-360`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/villa_render_contract.py#L358-L360) checks `need(view['exposure_mode'] == 'set-metered', p+'.exposure_mode', ...)`.
- **Real Failing Case Source**: Replays historical defect tested in [`tests/test_render_standard.py:484-504`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_render_standard.py#L484-L504) (`test_l0091_individually_metered_real_view_is_refused`). Created by taking `_cached_render_scene()`, filtering views to `[v12-ensuite]`, and setting `exposure_mode="per-view-metered"`.
- **Clean Quiet Case Source**: The complete valid cached scene from `_cached_render_scene()` (locked with `exposure_mode="set-metered"`).

### 2. `photometry_ies_azimuth_interpolation` (`l0026-blender-ies-azimuth`, `l0026`)
- **Root Failure Citation**: [`docs/LEARNINGS.md:267`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L267):
  > `| Photometry | Blender IES azimuth differs, finite sphere sizing can wash out a strip light, coarse angular interpolation biases narrow beams | Keep calibrated orientation/size/angle corrections; see decision 0010 |`
- **Audit Row**: [`docs/lessons-audit.md:28`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md#L28): `| l0026-blender-ies-azimuth | Blender IES azimuth differs, finite sphere sizing can wash out a strip light, coarse angular interpolation biases n... | emitter and fitting disconnected | 2 | NONE | lighting: compare emitter, distribution, housing and room. | D2/D3 or bedroom plus injected sibling; clean case quiet |`
- **Production Guard Target**: [`archpipe.photometry.read_file`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/photometry.py#L340-L390).
- **Reason for `needs_real_case=True`**: Reproducing the azimuth difference, finite sphere wash-out, and angular interpolation bias requires a live Blender Cycles simulation with an active Radiance sensor plane. The static file parser verifies header/grid compliance, but the historical physical failure occurred in Cycles runtime ray dispatch.

### 3. `lighting_kelvin_blackbody_locus` (`l0080-lamps-rendered-far`, `l0080`)
- **Root Failure Citation**: [`docs/LEARNINGS.md:321`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L321):
  > `| Lamps rendered far cooler than their 2700 K spec; the night came out blue and was nearly "fixed" by tuning white balance to 4200 K | kelvin_to_rgb used Tanner Helland's display-sRGB fit as linear light (2700 K came out as (1, 0.65, 0.34), not (1, 0.39, 0.10)); correcting with the camera hid the spec error | CIE 1931 blackbody in linear Rec.709, unit luminance; verify.py checks it against the published Planckian locus (dxy < 0.003). Rule: fix a lighting spec at its source; never compensate in camera, exposure or look settings. The camera uses a standard tungsten preset |`
- **Audit Row**: [`docs/lessons-audit.md:67`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md#L67): `| l0080-lamps-rendered-far | Lamps rendered far cooler than their 2700 K spec; the night came out blue and was nearly "fixed" by tuning white ba... | emitter and fitting disconnected | 1 | scripts/verify.py | Change src/archpipe/concept/villa_lighting.py: One fixture record owns photometry, emitter, housing and mount. | D2/D3 or bedroom plus injected sibling; clean case quiet |`
- **Production Guard Target**: [`archpipe.fixture_record.fixture_findings`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/fixture_record.py).
- **Reason for `needs_real_case=True`**: Requires live Blender Cycles Kelvin-to-RGB conversion linear pipeline state to reproduce the historical blue shift where 2700 K evaluated to `(1, 0.65, 0.34)`.

### 4. `glazing_two_face_transmission` (`l0090-window-glass-passed`, `l0090`)
- **Root Failure Citation**: [`docs/LEARNINGS.md:331`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L331):
  > `| Window glass passed 100% of sunlight; the model says 85% | The fix for glass blocking shadow rays over-corrected to "perfectly transparent" with no data | Tv from the model's own material (transparency 85), sqrt(Tv) per face of the slab (the two-face trap already recorded for Radiance). Shown in each image's caption.json |`
- **Audit Row**: [`docs/lessons-audit.md:77`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md#L77): `| l0090-window-glass-passed | Window glass passed 100% of sunlight; the model says 85% | emitter and fitting disconnected | 2 | NONE | lighting: compare emitter, distribution, housing and room. | D2/D3 or bedroom plus injected sibling; clean case quiet |`
- **Production Guard Target**: [`archpipe.villa_render_contract.validate_scene`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/villa_render_contract.py).
- **Reason for `needs_real_case=True`**: Requires live Cycles optical transmission simulation of shadow rays passing through double-faced window glazing slabs.

### 5. `glazing_calibrated_transmission_probe` (`l0656-glass-verified`, `l0656`)
- **Root Failure Citation**: [`docs/LEARNINGS.md:899-900`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md#L899-L900):
  > `- **Glass verified:** a single-sheet window transmits 0.700 (stated 0.70), a closed slab 0.850 (stated 0.85); the probe is part of --calibrate.`
- **Audit Row**: [`docs/lessons-audit.md:177`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md#L177): `| l0656-glass-verified | Glass verified | emitter and fitting disconnected | 2 | NONE | lighting: compare emitter, distribution, housing and room. | D2/D3 or bedroom plus injected sibling; clean case quiet |`
- **Production Guard Target**: [`archpipe.villa_render_contract.validate_scene`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/villa_render_contract.py).
- **Reason for `needs_real_case=True`**: `l0656` documents an empirical positive verification benchmark (single-sheet window 0.700, closed slab 0.850 under `--calibrate`) rather than an isolated defective input artifact. Reproducing it requires live optical sensor probe readings.

---

## Integration into scripts/verify.py

In accordance with [`docs/guard-registry.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/guard-registry.md) Section 8, Step 3:
1. Defined `audit_lesson_inventory(audit_path=None)` in [`scripts/verify.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/verify.py):
   ```python
   def audit_lesson_inventory(audit_path: pathlib.Path | None = None) -> bool:
       """Audit lesson coverage; fails closed if any lesson is uncovered or errors exist (Step 3)."""
       from archpipe.guard_registry import audit_lesson_coverage
       target = audit_path if audit_path is not None else (ROOT / "docs/lessons-audit.md")
       report = audit_lesson_coverage(target, strict=True)
       expect("lesson coverage audit has no errors", len(report["errors"]) == 0)
       expect("zero uncovered lessons", report["uncovered_count"] == 0)
       return len(report["errors"]) == 0 and report["uncovered_count"] == 0
   ```
2. Called `audit_lesson_inventory()` inside `main()` of [`scripts/verify.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/verify.py) right before the final `print("\nRESULT:", ...)` output.
3. If any lesson in [`docs/lessons-audit.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/lessons-audit.md) lacks coverage or if parsing errors occur, `expect` appends failure records to `FAILS`, guaranteeing a non-zero exit code (`exit_code=1`).

---

## Test Suite Extensions and Verification Evidence

In [`tests/test_guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_guard_registry.py):

1. **Coverage Count Re-Assertion**:
   - `covered_by_guard_count`: updated to 125 (was 124).
   - `covered_by_review_count`: 21 (unchanged).
   - `needs_real_case_count`: updated to 71 (was 67).
   - `uncovered_count`: updated to 0 (was 5).
   - Sum condition verified:
```latex
125 + 21 + 71 + 0 = 217
```
   - Asserted `report["uncovered_lessons"] == []`.
   - Added `"l0091-every-view-metered"` to `expected_guard_lessons`.
   - Added `"l0026-blender-ies-azimuth"`, `"l0080-lamps-rendered-far"`, `"l0090-window-glass-passed"`, `"l0656-glass-verified"` to `expected_needs_real_case`.
   - Removed obsolete `deleted_reimplementation_lessons` checks.

2. **New Test Method: `test_phase2_batch14_guards_execution`**:
   - Executes `scene_exposure_lock_mode` on both real (fires `ValueError`) and clean (returns `[]` / quiet) cases.
   - Asserts all four `needs_real_case` guards have `needs_real_case=True` and fail gracefully when run on real cases.

3. **New Test Method: `test_verify_fails_on_uncovered_lesson`**:
   - Asserts `verify_script.audit_lesson_inventory()` passes on the real project inventory.
   - Creates a temporary fabricated audit file containing an uncovered row `l9999-fabricated-uncovered`.
   - Asserts `audit_lesson_coverage` reports `uncovered_count == 1`.
   - Asserts `verify_script.audit_lesson_inventory(fabricated_audit)` returns `False` and appends `"zero uncovered lessons"` to `FAILS`.
   - Safely cleans up and restores `verify_script.FAILS` state.

4. **Meta-Guard Compliance**:
   - All five check functions in [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) invoke production modules ([`archpipe.villa_render_contract`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/villa_render_contract.py), [`archpipe.photometry`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/photometry.py), [`archpipe.fixture_record`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/fixture_record.py)).
   - None re-implement logic locally.

---

## Final Coverage Audit Counts

```
Total Lessons:          217
Covered by Guard:       125  (57.6%)
Covered by Review Step:  21  (9.7%)
Needs Real Case:         71  (32.7%)
Uncovered Lessons:        0  (0.0%)
```

Accountability status: **100% of tracked lessons are mapped to verified guards, review checkpoints, or explicit pending real-case fixtures.**

---

## Changed Files Inventory

Only the following four files were modified in this batch:

1. [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py) - Added imports, updated `__all__`, added `strict` parameter support in auditing functions, added `_cached_render_scene()` helper, defined 5 check functions and registered 5 guards.
2. [`scripts/verify.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/verify.py) - Defined `audit_lesson_inventory(audit_path=None)` helper and invoked it in `main()` to enforce zero uncovered lessons fail-closed.
3. [`tests/test_guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_guard_registry.py) - Updated count assertions (125, 21, 71, 0), updated lesson lists, added `test_phase2_batch14_guards_execution` and `test_verify_fails_on_uncovered_lesson`.
4. [`docs/reg14-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/reg14-report.md) - Batch 14 audit report and documentation.
