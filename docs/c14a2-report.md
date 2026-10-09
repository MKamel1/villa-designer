---
document_outline:
  - title: "1. Changed Files Summary"
    link: "#1-changed-files-summary"
  - title: "2. Per-Script Migration Details"
    link: "#2-per-script-migration-details"
    subsections:
      - title: "scripts/handoff.py"
        link: "#scriptshandoffpy"
      - title: "scripts/make_bedroom_spec.py"
        link: "#scriptsmake_bedroom_specpy"
      - title: "scripts/make_bedroom_extract.py"
        link: "#scriptsmake_bedroom_extractpy"
      - title: "scripts/villa_lighting_pdf.py"
        link: "#scriptsvilla_lighting_pdfpy"
      - title: "scripts/villa_daylight_pdf.py"
        link: "#scriptsvilla_daylight_pdfpy"
      - title: "scripts/yard_wall_pdf.py"
        link: "#scriptsyard_wall_pdfpy"
      - title: "scripts/villa_daylight_summary.py"
        link: "#scriptsvilla_daylight_summarypy"
      - title: "scripts/villa_furnish_build.py"
        link: "#scriptsvilla_furnish_buildpy"
      - title: "scripts/villa_env.py"
        link: "#scriptsvilla_envpy"
      - title: "scripts/villa_stairs.py"
        link: "#scriptsvilla_stairspy"
  - title: "3. Test Verification Suite"
    link: "#3-test-verification-suite"
  - title: "4. Lessons to Register"
    link: "#4-lessons-to-register"
  - title: "5. Fix Round: PDF Drawing Test Suite Resolution"
    link: "#5-fix-round-pdf-drawing-test-suite-resolution"
executive_summary:
  This report documents the completion of Defect Class C14 Phase 2 Batch A2, migrating all ten remaining Batch A entry scripts to atomic stage-result contracts.
  Each script now writes an atomic SHA-256 hashed stage-result record, verifies input/output completeness, and exits non-zero through enforce_clean_verdict strictly on existing failure conditions.
  Full test coverage in tests/test_c14_phase2a2.py reproduces the real l0029 failure, verifies clean passing executions, and asserts cryptographic artifact hashing without external dependencies.
---

# Stage-Result Class (C14) Phase 2 Batch A2 Report

## 1. Changed Files Summary

Only the following files in the repository were created or modified as part of Batch A2:

1. [scripts/handoff.py](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/handoff.py) — Stage-result recording and verdict gating for consultant handoff package deliverables.
2. [scripts/make_bedroom_spec.py](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/make_bedroom_spec.py) — Stage-result recording for YAML-to-JSON bedroom spec compilation.
3. [scripts/make_bedroom_extract.py](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/make_bedroom_extract.py) — Stage-result recording and empty-extract failure gating for mock extract generation.
4. [scripts/villa_lighting_pdf.py](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_lighting_pdf.py) — Stage-result recording and lux check failure gating for lighting presentation PDF.
5. [scripts/villa_daylight_pdf.py](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_daylight_pdf.py) — Stage-result recording and validation check gating for daylight options PDF.
6. [scripts/yard_wall_pdf.py](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/yard_wall_pdf.py) — Stage-result recording and readback error gating for yard wall client confirmation PDF.
7. [scripts/villa_daylight_summary.py](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_daylight_summary.py) — Stage-result recording and daylight check failure gating for daylight summary.
8. [scripts/villa_furnish_build.py](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_furnish_build.py) — Stage-result recording and post-condition failure gating across spec and check modes.
9. [scripts/villa_env.py](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_env.py) — Stage-result recording and geometry discrepancy gating across spec, check, and plan modes.
10. [scripts/villa_stairs.py](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_stairs.py) — Stage-result recording and clash disagreement gating across spec and compare modes.
11. [tests/test_c14_phase2a2.py](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_c14_phase2a2.py) — Complete unit tests covering failure reproduction, clean execution, and artifact hashing for all ten scripts.
12. [docs/stage-result-phase2-inventory.md](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/stage-result-phase2-inventory.md) — Updated inventory marking all ten Batch A2 scripts as migrated.
13. [docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/LEARNINGS.md) — Appended Batch A2 migration entry to the C14 stage-result record.
14. [docs/c14a2-report.md](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/c14a2-report.md) — This report document.

---

## 2. Per-Script Migration Details

### `scripts/handoff.py`
- **Failure condition**: Incomplete output / empty deliverable check evaluated via `write_stage_result` completeness verification ([stage_result.py:236-241](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/stage_result.py#L236-L241)). The script itself computes rule review findings as advisory guidance rather than mandatory gate errors ([handoff.py:74-75](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/handoff.py#L74-L75)).
- **Change**: Replaced raw `return 0` with `write_stage_result("handoff", record_path=stage_record, inputs=inputs, outputs=outputs, exit_code=0, metadata=...)` and returned `enforce_clean_verdict({"passed": True, ...})` at [handoff.py:89-114](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/handoff.py#L89-L114).
- **Inputs hashed**: `a.spec`, `out/workstation/thermal-cases-latest.json` (if present).
- **Outputs hashed**: `model.ifc`, `quantities.json`, `findings.json`, `README.md`, CSV schedules.
- **Stage record**: `out/handoff/<name>/handoff.stage-result.json`.

### `scripts/make_bedroom_spec.py`
- **Failure condition**: Missing required room dimensions, misplaced openings, or furniture items falling outside room boundaries in `convert()` ([make_bedroom_spec.py:29-65](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/make_bedroom_spec.py#L29-L65)), plus completeness check on `out/bedroom-spec.json`.
- **Change**: Replaced raw `return 0` with `write_stage_result("make-bedroom-spec", record_path=stage_record, inputs=[a.spec], outputs=[a.out], exit_code=0, metadata=...)` and returned `enforce_clean_verdict({"passed": True, ...})` at [make_bedroom_spec.py:102-123](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/make_bedroom_spec.py#L102-L123).
- **Inputs hashed**: `a.spec` (`spec/bedroom-test.yaml`).
- **Outputs hashed**: `a.out` (`out/bedroom-spec.json`).
- **Stage record**: `out/make-bedroom-spec.stage-result.json`.

### `scripts/make_bedroom_extract.py`
- **Failure condition**: Empty extract elements `bad = not (data.get("walls") and data.get("rooms") and data.get("lighting"))` at [make_bedroom_extract.py:107](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/make_bedroom_extract.py#L107).
- **Change**: Added `argv=None` support to `main()`, computed `bad`, called `write_stage_result("make-bedroom-extract", ...)` with `exit_code=1 if bad else 0`, and returned `enforce_clean_verdict` at [make_bedroom_extract.py:87-142](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/make_bedroom_extract.py#L87-L142).
- **Inputs hashed**: `scripts/make_bedroom_extract.py`.
- **Outputs hashed**: `a.out` (`out/bedroom.json`).
- **Stage record**: `out/make-bedroom-extract.stage-result.json`.

### `scripts/villa_lighting_pdf.py`
- **Failure condition**: Any task illuminance shortfall `t['status'] == 'fail'`, floor-average failure `r['status'] == 'fail'`, or fixture beam/swing obstruction in `res.get("problems", [])` at [villa_lighting_pdf.py:209-220](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_lighting_pdf.py#L209-L220).
- **Change**: Computed `failed_items = failed_tasks + failed_rooms + problems`, set `bad = len(failed_items) > 0`, called `write_stage_result("villa-lighting-pdf", ...)` with `exit_code=1 if bad else 0`, and returned `enforce_clean_verdict` at [villa_lighting_pdf.py:208-242](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_lighting_pdf.py#L208-L242).
- **Inputs hashed**: `knowledge/library.json`, `spec/villa-site.yaml`.
- **Outputs hashed**: `out/villa/render-d1/D1-lighting-finishes.pdf`.
- **Stage record**: `out/villa/render-d1/villa-lighting-pdf.stage-result.json`.

### `scripts/villa_daylight_pdf.py`
- **Failure condition**: Any Radiance validation check failing (`not c.get("pass", False)`), report status `FAIL`, or `not val.get("all_pass", True)` at [villa_daylight_pdf.py:137-145](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_daylight_pdf.py#L137-L145).
- **Change**: Extracted `failed_checks`, determined `bad = len(failed_checks) > 0`, called `write_stage_result("villa-daylight-pdf", ...)` with `exit_code=1 if bad else 0`, and returned `enforce_clean_verdict` at [villa_daylight_pdf.py:136-165](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_daylight_pdf.py#L136-L165).
- **Inputs hashed**: `out/villa/daylight/<job>/report.json`.
- **Outputs hashed**: `out/villa/daylight/Daylight-villa-options.pdf`.
- **Stage record**: `out/villa/daylight/villa-daylight-pdf.stage-result.json`.

### `scripts/yard_wall_pdf.py`
- **Failure condition**: Non-empty readback failure list `failed_items = rb.get("failed", [])` at [yard_wall_pdf.py:179](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/yard_wall_pdf.py#L179), and output PDF completeness.
- **Change**: Set `bad = len(failed_items) > 0`, called `write_stage_result("yard-wall-pdf", ...)` with `exit_code=1 if bad else 0`, and returned `enforce_clean_verdict` at [yard_wall_pdf.py:177-201](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/yard_wall_pdf.py#L177-L201).
- **Inputs hashed**: `out/villa/yard-wall/yard-wall-readback.json`, view PNGs.
- **Outputs hashed**: `out/villa/yard-wall/NE-yard-wall-confirmed.pdf`.
- **Stage record**: `out/villa/yard-wall/yard-wall-pdf.stage-result.json`.

### `scripts/villa_daylight_summary.py`
- **Failure condition**: Any daylight factor validation check failing (`not c.get("pass", True)`), DF report status `FAIL`, or zero options processed in summary at [villa_daylight_summary.py:126-135](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_daylight_summary.py#L126-L135).
- **Change**: Gathered `failed_checks`, determined `bad = len(failed_checks) > 0`, called `write_stage_result("villa-daylight-summary", ...)` with `exit_code=1 if bad else 0`, and returned `enforce_clean_verdict` at [villa_daylight_summary.py:125-156](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_daylight_summary.py#L125-L156).
- **Inputs hashed**: `out/villa/daylight/villa-lux-r10/report.json`, `villa-df-r10/report.json`, `views/stats.json`.
- **Outputs hashed**: `out/villa/daylight/summary.json`.
- **Stage record**: `out/villa/daylight/summary.stage-result.json`.

### `scripts/villa_furnish_build.py`
- **Failure condition**: `bad = bool(probs or fails)` from post-condition checks and build failures in check mode at [villa_furnish_build.py:62](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_furnish_build.py#L62). Spec mode verifies generated `options-spec.json` completeness.
- **Change**: In `spec` mode, called `write_stage_result("villa-furnish-build-spec", ...)` and returned `enforce_clean_verdict`; in `check` mode, wrote `write_stage_result("villa-furnish-build", ...)` with `exit_code=1 if bad else 0`, and returned `enforce_clean_verdict` at [villa_furnish_build.py:51-86](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_furnish_build.py#L51-L86).
- **Inputs hashed**: `options-spec.json`, `readback.json` (check mode); `spec/villa-site.yaml` (spec mode).
- **Outputs hashed**: `out/villa/furnish-d1/revit/options-spec.json` (spec mode).
- **Stage record**: `villa-furnish-build.stage-result.json` (check mode), `villa-furnish-build-spec.stage-result.json` (spec mode).

### `scripts/villa_env.py`
- **Failure condition**: Geometry, azimuth, column span, or level mismatch `bad = check(rb=rb)` in check mode at [villa_env.py:188](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_env.py#L188); artifact completeness in spec and plan modes.
- **Change**: Added atomic stage result generation and `enforce_clean_verdict` across all three subcommands (`spec`, `check`, and `plan`) at [villa_env.py:177-214](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_env.py#L177-L214).
- **Inputs hashed**: `env-spec.json`, `env-readback.json` (check and plan modes).
- **Outputs hashed**: `env-spec.json` (spec mode); `env-site-plan.pdf`, `env-site-plan.png` (plan mode).
- **Stage record**: `villa-env-spec.stage-result.json`, `villa-env-check.stage-result.json`, `villa-env-plan.stage-result.json`.

### `scripts/villa_stairs.py`
- **Failure condition**: Clash disagreement between Python analytical solver and Revit native clash test: `bad = compare() > 0` at [villa_stairs.py:84](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_stairs.py#L84); spec completeness in spec mode.
- **Change**: Handled `spec` subcommand with atomic stage recording; in `compare` mode, evaluated `bad`, recorded `write_stage_result("villa-stairs", ...)`, and returned `enforce_clean_verdict` with `exit_code=1 if bad else 0` at [villa_stairs.py:68-102](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_stairs.py#L68-L102).
- **Inputs hashed**: `stairs-readback.json` (compare mode).
- **Outputs hashed**: `stairs-spec.json` (spec mode).
- **Stage record**: `villa-stairs-spec.stage-result.json`, `villa-stairs.stage-result.json`.

---

## 3. Test Verification Suite

All ten scripts are covered by [tests/test_c14_phase2a2.py](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_c14_phase2a2.py), containing 23 unit test cases across ten test suites:

- `TestHandoffStageResult`:
  - `test_clean_handoff_exits_zero_with_ok_record_and_hashed_io`
  - `test_l0029_handoff_incomplete_output_fails_closed`
- `TestMakeBedroomSpecStageResult`:
  - `test_clean_bedroom_spec_exits_zero_with_ok_record_and_hashed_io`
  - `test_l0029_bedroom_spec_invalid_room_raises_and_cannot_gate`
- `TestMakeBedroomExtractStageResult`:
  - `test_clean_bedroom_extract_exits_zero_with_ok_record_and_hashed_io`
  - `test_l0029_bedroom_extract_empty_data_exits_nonzero_and_writes_fail_record`
- `TestVillaLightingPdfStageResult`:
  - `test_clean_lighting_pdf_exits_zero_with_ok_record_and_hashed_io`
  - `test_l0029_lighting_pdf_failure_exits_nonzero_and_writes_fail_record`
- `TestVillaDaylightPdfStageResult`:
  - `test_clean_daylight_pdf_exits_zero_with_ok_record_and_hashed_io`
  - `test_l0029_daylight_pdf_failure_exits_nonzero_and_writes_fail_record`
- `TestYardWallPdfStageResult`:
  - `test_clean_yard_wall_pdf_exits_zero_with_ok_record_and_hashed_io`
  - `test_l0029_yard_wall_pdf_failed_elements_exits_nonzero_and_writes_fail_record`
- `TestVillaDaylightSummaryStageResult`:
  - `test_clean_daylight_summary_exits_zero_with_ok_record_and_hashed_io`
  - `test_l0029_daylight_summary_failure_exits_nonzero_and_writes_fail_record`
- `TestVillaFurnishBuildStageResult`:
  - `test_clean_furnish_build_check_exits_zero_with_ok_record`
  - `test_clean_furnish_build_spec_exits_zero_with_ok_record`
  - `test_l0029_furnish_build_failures_exit_nonzero_and_write_fail_record`
- `TestVillaEnvStageResult`:
  - `test_clean_env_check_exits_zero_with_ok_record`
  - `test_clean_env_spec_exits_zero_with_ok_record`
  - `test_l0029_env_check_failure_exits_nonzero_and_writes_fail_record`
- `TestVillaStairsStageResult`:
  - `test_clean_stairs_compare_exits_zero_with_ok_record`
  - `test_clean_stairs_spec_exits_zero_with_ok_record`
  - `test_l0029_stairs_compare_disagreement_exits_nonzero_and_writes_fail_record`

Test execution command (run by lead):
```bash
python -m unittest tests/test_c14_phase2a2.py
```

---

## 4. Lessons to Register

The following lessons from `docs/LEARNINGS.md` map to the Batch A2 entry scripts and their `main()` entrypoints:

| Lesson ID | Script Entrypoint | Defect Mechanism & Guard |
|---|---|---|
| `l0029-script-printing-fail` | `scripts/handoff.py::main` | Empty or truncated deliverables bypass return code; gated by `write_stage_result` completeness and `enforce_clean_verdict`. |
| `l0029-script-printing-fail` | `scripts/make_bedroom_spec.py::main` | Room spec missing required dimensions or boundaries; gated by `convert()` abort and `enforce_clean_verdict`. |
| `l0029-script-printing-fail` | `scripts/make_bedroom_extract.py::main` | Empty extract produced silently; gated by `bad = not (walls and rooms and lighting)` and `enforce_clean_verdict`. |
| `l0029-script-printing-fail` | `scripts/villa_lighting_pdf.py::main` | Printed lux check failures returned 0; gated by `bad = len(failed_items) > 0` and `enforce_clean_verdict`. |
| `l0029-script-printing-fail` | `scripts/villa_daylight_pdf.py::main` | Daylight simulation validation failure returned 0; gated by `bad = len(failed_checks) > 0` and `enforce_clean_verdict`. |
| `l0029-script-printing-fail` | `scripts/yard_wall_pdf.py::main` | Yard wall readback failure printed but returned 0; gated by `bad = len(failed_items) > 0` and `enforce_clean_verdict`. |
| `l0029-script-printing-fail` | `scripts/villa_daylight_summary.py::main` | Daylight factor check failure returned 0; gated by `bad = len(failed_checks) > 0` and `enforce_clean_verdict`. |
| `l0029-script-printing-fail` | `scripts/villa_furnish_build.py::main` | Readback failure or clearance collision returned 0 in ad-hoc paths; gated by `bad = bool(probs or fails)` and `enforce_clean_verdict`. |
| `l0029-script-printing-fail` | `scripts/villa_env.py::main` | Geometry discrepancy printed `FAIL` returned 0; gated by `bad = check(rb=rb)` and `enforce_clean_verdict`. |
| `l0029-script-printing-fail` | `scripts/villa_stairs.py::main` | Stair clash disagreement printed `DISAGREE` returned 0; gated by `bad = compare() > 0` and `enforce_clean_verdict`. |

---

## 5. Fix Round: PDF Drawing Test Suite Resolution

During the verification run on Windows (`scripts/run_tests.py`), six unit test failures in [tests/test_c14_phase2a2.py](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_c14_phase2a2.py) were diagnosed and resolved without modifying any production scripts under `scripts/`:

1. **`TestVillaDaylightPdfStageResult` (`scripts/villa_daylight_pdf.py`)**:
   - *Failure mechanism*: The test fixture `report.json` provided an empty `results: {}` dictionary. In [villa_daylight_pdf.py:75-88](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_daylight_pdf.py#L75-L88), calculating room results against SLL cards yielded `rows = []`, causing matplotlib's `ax.table(cellText=rows, colLabels=[...])` to fail with `IndexError: list index out of range` in `matplotlib/table.py:774`.
   - *Fix applied*: Populated `results` in the test fixture with a minimal valid room entry (`"S1": {"rooms": {"living": {"level": "B", "adf": 2.5}}}`). This matches the `"living"` room occupancy from `VO.s1()`, resolving target SLL threshold `1.5` and producing a valid 1-row table input for both clean and failing test runs.

2. **`TestVillaLightingPdfStageResult` (`scripts/villa_lighting_pdf.py`)**:
   - *Failure mechanism*: [scripts/villa_lighting_pdf.py](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_lighting_pdf.py) imported `PdfPages` at module level (`from matplotlib.backends.backend_pdf import PdfPages`). When the test patched `matplotlib.backends.backend_pdf.PdfPages` to a replacement mock class, `villa_lighting_pdf` retained the original class reference. When `pdf.savefig(fig)` invoked `fig.savefig(self, format="pdf")`, matplotlib checked `isinstance(fname, backend_pdf.PdfPages)` against the patched mock class, causing type check failure with `ValueError: fname must be a PathLike or file handle`. Furthermore, empty fixtures array `[]` would have caused an empty `rows` list and `IndexError` on schedule table generation.
   - *Fix applied*: Implemented `_patch_pdf_pages()` context manager patching the underlying methods on `matplotlib.backends.backend_pdf.PdfPages` (`__init__`, `__enter__`, `__exit__`, and `savefig`). This preserves class identity across all modules while ensuring output PDF files exist on disk with valid dummy bytes and skipping figure file rendering. Provided a minimal valid fixture (`DL` kind on `GF`) so schedule and legend tables draw cleanly.

3. **`TestYardWallPdfStageResult` (`scripts/yard_wall_pdf.py`)**:
   - *Failure mechanism*: The mock for `yard_wall_pdf.light` returned a `MagicMock()`. At [yard_wall_pdf.py:111](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/yard_wall_pdf.py#L111), `np.rot90(light(...), k=-1)` raised `ValueError: Axes must be different` because `MagicMock` is not a 2-D or 3-D numpy array.
   - *Fix applied*: Updated the `light` mock to return a valid 3-D array `np.zeros((10, 10, 3), dtype=np.uint8)`. Removed the mock on `matplotlib.pyplot.figure` to allow real drawing routines to execute cleanly against `_patch_pdf_pages()`.

All test cases continue to adhere to isolation protocols via `_isolate_process_state(self)` at the beginning of each `setUp`. Clean test cases verify exit code 0 and valid hashed stage-result outputs, while `l0029` test cases verify non-zero exits with `fail` status records on each script's native failure condition.

