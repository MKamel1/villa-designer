---
document_outline:
  - title: "1. Entry Script Pipeline Result Inventory"
    link: "#1-entry-script-pipeline-result-inventory"
  - title: "2. Concrete Migration Plan for Unmigrated Scripts"
    link: "#2-concrete-migration-plan-for-unmigrated-scripts"
  - title: "3. Defect Class C14 Lesson Coverage (Learnings Mapping)"
    link: "#3-defect-class-c14-lesson-coverage-learnings-mapping"
  - title: "4. Scope Exclusions (Skip Rationale)"
    link: "#4-scope-exclusions-skip-rationale"
executive_summary:
  This inventory audits all 30 pipeline entry scripts across scripts/ and revit/ for Defect Class C14 ("pipeline result lacks atomic proof").
  It maps four already-migrated Phase 1 stages, details concrete input/output hashing and verdict migrations for unmigrated stages across Batch A (pure CPython) and Batch B (Revit/Blender/workstation), and grounds the six class lessons (l0029, l0040, l0068, l0089, l0133, l0287) in exact code lines and recorded real cases.
---

# Stage-Result Class (C14) Phase 2 Inventory

## 1. Entry Script Pipeline Result Inventory

Every script in `scripts/` and `revit/` producing consumed pipeline artifacts (renders, extracts, PDFs, lux, daylight, thermal, Revit builds) is audited below.

| Script | Primary Outputs | Success Signaling Mechanism | Has Stage-Result? | PASS/FAIL Decision (`file:line`) |
|---|---|---|---|---|
| `scripts/compare_lux.py` | `compare-lux.stage-result.json`, stdout lux table | Exits 0 via `enforce_clean_verdict` (line 211) | Yes (`compare-lux.stage-result.json:198-210`) | [compare_lux.py:192](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/compare_lux.py#L192) (`bad`), [211](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/compare_lux.py#L211) |
| `scripts/check_bedroom.py` | `check-bedroom.stage-result.json`, stdout report | Exits 0 via `enforce_clean_verdict` (line 303) | Yes (`check-bedroom.stage-result.json:291-298`) | [check_bedroom.py:288](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/check_bedroom.py#L288) (`bad = c.report()`), [303](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/check_bedroom.py#L303) |
| `scripts/verify.py` | `verify.stage-result.json`, stdout test report | Exits 0 via `enforce_clean_verdict` (line 971) | Yes (`verify.stage-result.json:963-970`) | [verify.py:957](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/verify.py#L957) (`ALL PASS if not FAILS`), [971](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/verify.py#L971) |
| `scripts/villa_render.py` | `villa-render.stage-result.json`, renders, `.qa.json` | Exits 0 via `enforce_clean_verdict` (line 377) | Yes (`villa-render.stage-result.json:322-335`) | [villa_render.py:321](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_render.py#L321) (`all_qa_passed`), [377](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_render.py#L377) |
| `scripts/run_bedroom.py` | `out/bedroom-acceptance.json`, `out/bedroom-acceptance.md` | Exits 0 if `result['passed']` else 1 (line 247) | No (ad-hoc dict `result:245`) | [run_bedroom.py:247](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/run_bedroom.py#L247) (gates at lines 177, 185, 203, 219, 231) |
| `scripts/handoff.py` | `out/handoff/<proj>/model.ifc`, `quantities.json`, CSVs | Prints destination (line 89); returns 0 (line 90) | No | [handoff.py:90](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/handoff.py#L90); validation at [deliverables.py:126](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/deliverables.py#L126) |
| `scripts/make_bedroom_spec.py` | `out/bedroom-spec.json` | Writes JSON (line 93); returns 0 (line 102) | No | [make_bedroom_spec.py:102](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/make_bedroom_spec.py#L102) (validation aborts at lines 31, 40, 45, 54, 65) |
| `scripts/make_bedroom_extract.py` | `out/bedroom.json` | Writes JSON (line 105); returns 0 (line 109) | No | [make_bedroom_extract.py:109](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/make_bedroom_extract.py#L109) |
| `scripts/make_render_input.py` | `out/bedroom-render.json` | Exits 1 on missing/orphan/unmatched else 0 (line 186) | No | [make_render_input.py:186](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/make_render_input.py#L186) (`1 if (orphans or unmatched or no_source) else 0`) |
| `scripts/villa_option_pdfs.py` | `out/villa/options/Option-<id>.pdf` | Prints path (line 284); returns 0 (lines 264, 286) | No | [villa_option_pdfs.py:285](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_option_pdfs.py#L285) (reports `bad`), [286](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_option_pdfs.py#L286) (`return 0`) |
| `scripts/villa_furnish_pdf.py` | `out/villa/furnish/D1-furnished.pdf` | Prints table (lines 189-199); returns 0 (line 200) | No | [villa_furnish_pdf.py:200](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_furnish_pdf.py#L200) (`return 0` regardless of check failures) |
| `scripts/villa_lighting_pdf.py` | `out/villa/lighting/D1-lighting-finishes.pdf` | Prints path (line 207); returns 0 (line 208) | No | [villa_lighting_pdf.py:208](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_lighting_pdf.py#L208) (`return 0`) |
| `scripts/villa_daylight_pdf.py` | `out/villa/daylight/Daylight-villa-options.pdf` | Prints path (line 135); returns 0 (line 136) | No | [villa_daylight_pdf.py:136](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_daylight_pdf.py#L136) (`return 0`) |
| `scripts/villa_daylight_summary.py` | `out/villa/daylight/summary.json` | Writes JSON (line 116); returns 0 (line 125) | No | [villa_daylight_summary.py:125](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_daylight_summary.py#L125) (`return 0`) |
| `scripts/villa_daylight_finished.py`| `out/villa/daylight/<job>/report.json`, sensor logs | Returns 0 if `val["all_pass"]` else 1 (line 97) | No | [villa_daylight_finished.py:94](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_daylight_finished.py#L94) (`status`), [97](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_daylight_finished.py#L97) (`return 0 if val["all_pass"] else 1`) |
| `scripts/yard_wall_pdf.py` | `out/villa/yard-wall/NE-yard-wall-confirmed.pdf` | Prints path (line 177); returns 0 (line 178) | No | [yard_wall_pdf.py:178](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/yard_wall_pdf.py#L178) (`return 0`) |
| `scripts/thermal_job.py` | `out/villa/thermal/<job>/thermal-results.json` | Returns 0 if `result.get("passed", True)` else 1 | No | [thermal_job.py:124](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/thermal_job.py#L124) (`return 0 if result.get("passed", True) else 1`) |
| `scripts/render_hyperreal.py` | `out/photoreal/bedroom-<stamp>.png`, `.qa.json` | Returns 0 (line 279); exits 1 on QA fail (line 278) | No | [render_hyperreal.py:274](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/render_hyperreal.py#L274) (`not report["passed"]`), [278](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/render_hyperreal.py#L278) (`return 1`) |
| `scripts/worker_entry.py` | `batch/report.json`, `batch/results.tar.gz` | Prints structured JSON on stdout (line 238) | No | [worker_entry.py:210](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/worker_entry.py#L210) (`all(r['passed'])`), [225](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/worker_entry.py#L225) (`report['passed']=False`) |
| `scripts/workstation.py` | `out/workstation/<action>-latest.json`, `.tar.gz` | Exits 1 if `report.get('passed') is False` (line 164) | No | [workstation.py:163](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/workstation.py#L163) (`if report.get('passed') is False: return 1`), [167](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/workstation.py#L167) |
| `scripts/villa_furnish_build.py` | `options-spec.json`, check summary | Exits 1 if `probs or fails` else 0 (line 63) | No | [villa_furnish_build.py:63](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_furnish_build.py#L63) (`return 1 if probs or fails else 0`) |
| `scripts/villa_env.py` | `out/villa/env-spec.json`, `env-site-plan.pdf/.png` | Exits 1 if `bad` else 0 on check (line 190) | No | [villa_env.py:190](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_env.py#L190) (`return 1 if bad else 0`) |
| `scripts/villa_stairs.py` | `out/villa/stairs-spec.json`, clash report | Exits 1 if `compare()` returns > 0 (line 72) | No | [villa_stairs.py:47-50](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_stairs.py#L47-L50) (`bad += 1`), [72](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_stairs.py#L72) (`return 1 if compare() else 0`) |
| `scripts/villa_concepts.py` | `spec/concepts/villa/*.json`, PDFs, PNGs | Prints fails/warnings (line 286); returns 0 (line 287) | No | [villa_concepts.py:287](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_concepts.py#L287) (`return 0` unconditionally even when `res["fails"] > 0`) |
| `revit/build_bedroom.py` | `out/revit2027/bedroom.rvt`, `<dest>.build.json` | Prints `"archpipe: wrote %s"` (line 928) | No | [build_bedroom.py:937-938](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/build_bedroom.py#L937-L938) (prints errors), [945](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/build_bedroom.py#L945) (traceback catch) |
| `revit/extract_model.py` | `out/bedroom-from-revit.json` | Prints `"archpipe: wrote %s"` (line 742); returns path | No | [extract_model.py:735](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/extract_model.py#L735) (`return None`), [744](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/extract_model.py#L744) (`return dest`) |
| `revit/export_views.py` | `bedroom-native-views.pdf`, `views-report.json` | Prints `'ARCHPIPE VIEWS '` (line 180) | No | [export_views.py:175](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/export_views.py#L175) (`report['pdf_exported'] = doc.Export`), [187](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/export_views.py#L187) |
| `revit/build_villa_option.py` | `omar-option-<id>.rvt`, PNGs, `readback.json` | Prints `"archpipe: wrote readback"` (line 777) | No | [build_villa_option.py:756](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/build_villa_option.py#L756) (`rb["failed"].append`), [777](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/build_villa_option.py#L777) (`return 0`) |
| `revit/build_villa_env.py` | `omar-env.rvt`, PNGs, `env-readback.json` | Prints `"wrote %s"` (line 338) | No | [build_villa_env.py:304](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/build_villa_env.py#L304) (logs error), [338](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/build_villa_env.py#L338) (`return 0`) |
| `revit/build_villa_stairs.py` | `omar-stairs.rvt`, `stairs-readback.json`, PNGs | Prints `"wrote %s"` (line 151) | No | [build_villa_stairs.py:149](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/build_villa_stairs.py#L149) (image errors appended), [151](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/build_villa_stairs.py#L151) (`return 0`) |

---

## 2. Concrete Migration Plan for Unmigrated Scripts

### Batch A: Pure CPython (Testable locally without Revit, Blender, or network)
1. **`scripts/handoff.py` / `src/archpipe/deliverables.py`**:
   - *Inputs to hash*: `spec/bedroom-test.yaml` (or project spec), `out/bedroom-from-revit.json`.
   - *Outputs to hash*: `out/handoff/<proj>/model.ifc`, `quantities.json`, CSV schedules, `findings.json`.
   - *Verdict / Gating*: Gated on `len(findings["errors"]) == 0` via `enforce_clean_verdict(findings)`.
   - *Risk / Consumers*: External estimating, engineering handoff, quantity verification. Pure CPython, testable immediately.
2. **`scripts/make_bedroom_spec.py`**:
   - *Inputs to hash*: `spec/bedroom-test.yaml`.
   - *Outputs to hash*: `out/bedroom-spec.json`.
   - *Verdict / Gating*: Validated dict from `convert()` passed to `write_stage_result()` and `enforce_clean_verdict()`.
   - *Risk / Consumers*: Consumed by `revit/build_bedroom.py` and downstream extract verifiers. Pure CPython.
3. **`scripts/make_bedroom_extract.py`**:
   - *Inputs to hash*: Static mock constants (or fixture parameter file).
   - *Outputs to hash*: `out/bedroom.json`.
   - *Verdict / Gating*: Gated on non-empty walls/rooms/lighting extract record.
   - *Risk / Consumers*: Stand-in extractor consumed by Blender bridge tests. Pure CPython.
4. **`scripts/make_render_input.py`**:
   - *Inputs to hash*: `out/bedroom-from-revit.json` (or `out/bedroom.json`), `spec/bedroom-test.yaml`, referenced IES photometric files.
   - *Outputs to hash*: `out/bedroom-render.json`.
   - *Verdict / Gating*: Gated on `not (orphans or unmatched or no_source)` directly into `enforce_clean_verdict()`.
   - *Risk / Consumers*: Consumed by all Blender render and lux probe jobs. Pure CPython.
5. **Presentation PDF Suite (`scripts/villa_option_pdfs.py`, `scripts/villa_furnish_pdf.py`, `scripts/villa_lighting_pdf.py`, `scripts/villa_daylight_pdf.py`, `scripts/yard_wall_pdf.py`)**:
   - *Inputs to hash*: Upstream readback JSONs (`readback.json`, `options-spec.json`, `yard-wall-readback.json`, `report.json`), view PNGs.
   - *Outputs to hash*: Generated client PDFs (`Option-<id>.pdf`, `D1-furnished.pdf`, `D1-lighting-finishes.pdf`, etc.).
   - *Verdict / Gating*: Gated on zero bad geometry items and non-empty output PDF (`stat().st_size > 0`). Eliminates [villa_option_pdfs.py:286](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_option_pdfs.py#L286) and [villa_furnish_pdf.py:200](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_furnish_pdf.py#L200) returning 0 on failed checks.
   - *Risk / Consumers*: Client decision packages and design sign-offs. Pure CPython (uses matplotlib Agg).
6. **Summary & Verification Scripts (`scripts/villa_daylight_summary.py`, `scripts/villa_furnish_build.py`, `scripts/villa_env.py`, `scripts/villa_stairs.py`, `scripts/villa_concepts.py`)**:
   - *Inputs to hash*: Job reports, layout specs, readback JSONs.
   - *Outputs to hash*: Summary JSONs, spec JSONs, site plan PDFs.
   - *Verdict / Gating*: Feed post-condition check lists and `res["fails"] == 0` into `enforce_clean_verdict()`. Prevents silent zero exits at [villa_concepts.py:287](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_concepts.py#L287).
   - *Risk / Consumers*: Design option critique and layout freeze. Pure CPython.

### Batch B: Complex Environment (Requires Blender, Revit pyRevit, or Workstation network)
1. **`scripts/run_bedroom.py`**:
   - *Inputs to hash*: `spec/bedroom-test.yaml`, `revit/build_bedroom.py`, `src/archpipe/**`.
   - *Outputs to hash*: `out/bedroom-acceptance.json`, `out/bedroom-acceptance.md`, render outputs.
   - *Verdict / Gating*: Replace ad-hoc `result` dictionary at [run_bedroom.py:245](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/run_bedroom.py#L245) with `write_stage_result()` and `enforce_clean_verdict(result["passed"])`.
   - *Risk / Consumers*: Whole bedroom pipeline acceptance coordinator. Consumed by lead reviewer.
2. **`scripts/villa_daylight_finished.py` & `scripts/thermal_job.py`**:
   - *Inputs to hash*: Workstation output sensor data, EPW weather file, model geometry.
   - *Outputs to hash*: `out/villa/daylight/<job>/report.json`, `out/villa/thermal/<job>/thermal-results.json`.
   - *Verdict / Gating*: Gated on `val["all_pass"]` ([villa_daylight_finished.py:97](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_daylight_finished.py#L97)) and EnergyPlus/Radiance pass flags ([thermal_job.py:124](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/thermal_job.py#L124)).
   - *Risk / Consumers*: Statutory compliance (SLL daylight factors, comfort criteria). Requires Radiance/EnergyPlus workstation.
3. **`scripts/render_hyperreal.py`, `scripts/worker_entry.py`, `scripts/workstation.py`**:
   - *Inputs to hash*: `out/bedroom-render.json`, release manifests, camera views, scene scripts.
   - *Outputs to hash*: Rendered PNGs, `.qa.json`, captions, tarball bundles.
   - *Verdict / Gating*: Gated on `qa_failed == []` ([render_hyperreal.py:276](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/render_hyperreal.py#L276)) and `all(r['passed'])` ([worker_entry.py:210](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/worker_entry.py#L210)).
   - *Risk / Consumers*: High-end client renders and GPU probes. Requires Blender and workstation SSH.
4. **Revit Model Builders & Extractors (`revit/build_bedroom.py`, `revit/extract_model.py`, `revit/export_views.py`, `revit/build_villa_option.py`, `revit/build_villa_env.py`, `revit/build_villa_stairs.py`)**:
   - *Inputs to hash*: Input specs (`out/bedroom-spec.json`, `options-spec.json`), template RVTs, family directories.
   - *Outputs to hash*: Output RVT models (`bedroom.rvt`, `omar-option-*.rvt`), extract JSONs, sheet PDFs, readbacks.
   - *Verdict / Gating*: Emit stage-result records using IronPython 2.7 compatible writer helper; gate on `report['errors'] == []` and `report['pdf_exported'] is True`.
   - *Risk / Consumers*: Foundational BIM assets for drawings and extraction. Requires Revit/pyRevit execution.

---

## 3. Defect Class C14 Lesson Coverage (Learnings Mapping)

Mapping the six class lessons from `docs/LEARNINGS.md` to migration batches:

1. **`l0029-script-printing-fail`**:
   - *LEARNINGS.md:214 quote*: `| Gates | A script printing FAIL but returning zero cannot gate a pipeline | Assert failed, missing and stale cases as well as passing cases; inspect saved evidence, not shell exit alone |`
   - *Batch Coverage*: **Batch A**. Directly covers `scripts/villa_option_pdfs.py:285-286` (prints `bad` checks, returns 0), `scripts/villa_furnish_pdf.py:200` (prints clearance failures, returns 0), and `scripts/villa_concepts.py:286-287` (prints non-zero `res["fails"]`, returns 0).
   - *Status*: **REAL recorded case available**. Frozen in [tests/test_stage_result.py:126](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_stage_result.py#L126) (`test_l0029_fail_verdict_refuses_zero_exit_and_clean_verdict_passes`).
2. **`l0040-three-unchanged-camera`**:
   - *LEARNINGS.md:225 quote*: `| Reuse | Three unchanged camera jobs were all reused after unrelated documentation/orchestration changes; a modified cached artifact fails the hash check | Fingerprint job dependencies and actual runtime; verify artifacts, preserve failed attempts. worker.cached_job, tests/test_worker.py |`
   - *Batch Coverage*: **Batch B**. Covers `scripts/worker_entry.py:198-200` and `scripts/run_bedroom.py:224-231` (fingerprinting dependencies and verifying output completeness before reuse).
   - *Status*: **REAL recorded case available**. Frozen in [tests/test_stage_result.py:157](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_stage_result.py#L157) (`test_l0040_cached_stage_reused_after_input_change_fails_closed`).
3. **`l0068-fixtures-rendered-as`**:
   - *LEARNINGS.md:253 quote*: `| Fixtures rendered as isotropic points | An ad-hoc driver did not remap IES paths, and the fallback only printed a note | render_qa check photometry_bound; the driver remaps like worker_entry.py |`
   - *Batch Coverage*: **Batch B** (`scripts/render_hyperreal.py` / `scripts/worker_entry.py`) and **Batch A** (`scripts/make_render_input.py:182-186`). Fallback noted instead of failing closed; stage-result enforces missing IES inputs raise `IncompleteOutputError` / fail clean verdict.
   - *Status*: **REAL recorded case available**. Historical driver failure reproduced in `render_qa.check_photometry_bound` and frozen output set tests.
4. **`l0089-another-session-edited`**:
   - *LEARNINGS.md:274 quote*: `| Another session edited the same repo concurrently | Broad git add would have committed its unfinished work | Stage only your own hunks; confirm with git diff --cached before committing |`
   - *Batch Coverage*: **Batch A & Batch B**. Addressed by `stage_result.compute_code_provenance()` capturing `source_hash`, `git_head`, and `git_dirty`; validated by `validate_stage_result()` raising `CodeDriftError`.
   - *Status*: **REAL recorded case available**. Frozen in [tests/test_stage_result.py:202](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_stage_result.py#L202) (`test_stale_scene_consumed_by_render_fails_closed`).
5. **`l0133-open-right-after`**:
   - *LEARNINGS.md:318 quote*: `| **Open**: right after a passing run, run_bedroom --resume once re-ran the downstream stages (6 s, worker jobs reused) where full reuse was expected; the next call reused fully | Not yet known. The test's pre-check (inputs and artifacts) agreed, so the likely differing key is worker_runtime, possibly captured before the run's own asset deployment. **Hypothesis, unverified** | None yet. Next step: record the runtime fingerprint before and after worker_bedroom and compare. test_mcp.py --cached-run catches the symptom |`
   - *Batch Coverage*: **Batch B** (`scripts/run_bedroom.py --resume`).
   - *Status*: **LACKS recoverable real case**. The entry in `LEARNINGS.md:318` remains explicitly marked "Open / Hypothesis, unverified" without a deterministic, isolated historical input bundle. Batch B migration will provide the cryptographic recording infrastructure to capture this runtime fingerprint.
6. **`l0287-slow-session-persist`**:
   - *LEARNINGS.md:465 & 472 quote*: Line 465: `## Reading a real Revit 2021 model in 2027: two serialisation failures after a 17-minute upgrade (2026-09-25)`; Line 472: `- **Lesson:** in a slow session, persist the expensive result first, then do the fragile work.`
   - *Batch Coverage*: **Batch B** (`revit/probe_villa_inventory.py:471`, `revit/build_villa_option.py:737`, `scripts/run_bedroom.py:245`).
   - *Status*: **REAL recorded case available**. Recorded in `revit/probe_villa_inventory.py` and `out/villa/original-sha256-before.txt`. Atomic staging via `stage_result.py` guarantees expensive upstream outputs are safely persisted and hashed before executing fragile serialization or post-processing.

---

## 4. Scope Exclusions (Skip Rationale)

The following scripts in `scripts/` and `revit/` are excluded from stage-result migration:
- `scripts/export_bedroom_glb.py`: Viewing aid only. Explicitly documented at [export_bedroom_glb.py:11-12](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/export_bedroom_glb.py#L11-L12): *"This is a one-off viewing aid, not a pipeline stage: it does not go through worker.cached_job, so it is not part of run_bedroom.py's acceptance record."*
- `scripts/archpipe_mcp.py`: Long-running FastMCP protocol daemon server, not a discrete pipeline stage.
- `scripts/preflight.py`, `scripts/run_tests.py`, `scripts/test_mcp.py`: Diagnostic and test suite runners.
- `scripts/configure_assistants.py`, `scripts/delegate_implementation.py`, `scripts/sync_agent_assets.py`: Agent/developer maintenance tools.
- `revit/diag_context.py`, `revit/dump_mcp_tools.py`, `revit/jsonsafe.py`, `revit/unattended.py`: pyRevit execution support modules.
- `revit/probe_villa_inventory.py`, `revit/probe_yard_wall.py`, `revit/probe_room_shapes.py`, `revit/probe_view_crop.py`, `revit/probe_d1_levels.py`: Interactive read-only diagnostic inspection probes.
