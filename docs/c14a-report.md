---
document_outline:
  - title: "Executive Summary"
    link: "#executive-summary"
  - title: "Migrated Scripts and Failure Conditions"
    link: "#migrated-scripts-and-failure-conditions"
  - title: "Verification Proofs"
    link: "#verification-proofs"
  - title: "Lessons Registered"
    link: "#lessons-registered"
  - title: "Changed Files Register"
    link: "#changed-files-register"
executive_summary:
  This report documents the migration of Stage-Result Defect Class C14 Phase 2 Batch A1 scripts to atomic stage-result contracts.
  All four scripts (scripts/villa_option_pdfs.py, scripts/villa_furnish_pdf.py, scripts/villa_concepts.py, and scripts/make_render_input.py) now hash declared inputs and outputs and fail closed via enforce_clean_verdict upon existing failure conditions.
  The changes eliminate silent zero-exit defects (l0029) without altering downstream artifacts or public APIs, backed by unit proofs in tests/test_c14_phase2a.py.
---

# Stage-Result Class (C14) Phase 2 Batch A1 Report

## Executive Summary
Defect Class C14 ("pipeline result lacks atomic proof") Phase 2 Batch A1 migrates four pure CPython pipeline entry scripts to atomic stage-result records using [`write_stage_result`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/stage_result.py#L198) and fail-closed exit gating using [`enforce_clean_verdict`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/stage_result.py#L453).

The three presentation/critique scripts that previously printed check failures but returned zero ([`villa_option_pdfs.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_option_pdfs.py), [`villa_furnish_pdf.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_furnish_pdf.py), and [`villa_concepts.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_concepts.py)), and the render input bridge script ([`make_render_input.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/make_render_input.py)), now record cryptographic input/output manifests and refuse shell zero exit whenever their existing failure conditions evaluate to True.

---

## Migrated Scripts and Failure Conditions

### 1. `scripts/villa_option_pdfs.py`
- **Existing Failure Condition (`file:line`)**:
  [scripts/villa_option_pdfs.py:295](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_option_pdfs.py#L295) printed `failed: len(rb['failed'])` where `rb` is the Revit option read-back object.
  Gated at [scripts/villa_option_pdfs.py:301](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_option_pdfs.py#L301) on `bad = len(failed_items) > 0`, where `failed_items` collects all non-empty `rb['failed']` strings across rendered options.
- **Change**:
  - In `is_spec` branch: writes atomic stage record [`villa-option-pdfs.stage-result.json`](file:///C:/Users/mmbka/arch-pipeline-agy2/out/villa/options/villa-option-pdfs.stage-result.json) for `options-spec.json` and exits 0 via `enforce_clean_verdict(True)`.
  - In main PDF generation branch: writes atomic stage record for generated `Option-<id>.pdf` outputs and upstream inputs (`readback.json`, `options-spec.json`, view PNGs), passing `exit_code=1 if bad else 0`.
  - Returns `enforce_clean_verdict({"passed": not bad, "failed": failed_items}, exit_code=1)`.
- **Imports**:
  `from archpipe.stage_result import enforce_clean_verdict, write_stage_result` is invoked strictly on the CLI execution path within `main()`, avoiding import-time execution.

### 2. `scripts/villa_furnish_pdf.py`
- **Existing Failure Condition (`file:line`)**:
  [scripts/villa_furnish_pdf.py:199](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_furnish_pdf.py#L199) printed `{k: v["status"] for k, v in res.items()}` where `res = F.check(items, lay)` computes clearances, columns, overlap, door swings, and window checks.
  Gated at [scripts/villa_furnish_pdf.py:205](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_furnish_pdf.py#L205) on `bad = len(failed_checks) > 0`, where `failed_checks` checks for any check with `v.get("status") == "fail"`.
- **Change**:
  - Replaces unconditional `return 0` at [scripts/villa_furnish_pdf.py:200](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_furnish_pdf.py#L200) with atomic stage record written to `OUT / "villa-furnish-pdf.stage-result.json"`.
  - Hashes declared outputs (`D1-furnished.pdf`) and upstream layout specs.
  - Returns `enforce_clean_verdict({"passed": not bad, "failures": failed_checks, "checks": ...}, exit_code=1)`.

### 3. `scripts/villa_concepts.py`
- **Existing Failure Condition (`file:line`)**:
  [scripts/villa_concepts.py:286](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_concepts.py#L286) printed `lay["id"], "fails", res["fails"], "warnings", res["warnings"]` where `res = V.critique(lay)`.
  Gated at [scripts/villa_concepts.py:296](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_concepts.py#L296) on `bad = len(all_failures) > 0`, checking for any non-zero critique fails list.
- **Change**:
  - Replaces unconditional `return 0` at [scripts/villa_concepts.py:287](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_concepts.py#L287) with atomic stage record written to `OUT / "villa-concepts.stage-result.json"`.
  - Hashes generated concept specifications (`SPEC / concept-<id>.json`) and client presentation drawings (`OUT / concept-<id>-r4.pdf`, `png`, `section-<id>-r4.pdf`, `png`).
  - Returns `enforce_clean_verdict({"passed": not bad, "failures": all_failures, "concepts": ...}, exit_code=1)`.

### 4. `scripts/make_render_input.py`
- **Existing Failure Condition (`file:line`)**:
  [scripts/make_render_input.py:186](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/make_render_input.py#L186) returned `1 if (orphans or unmatched or no_source) else 0`.
  Preserved exactly at [scripts/make_render_input.py:186](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/make_render_input.py#L186) as `bad = bool(orphans or unmatched or no_source)`.
- **Change**:
  - Writes atomic stage record to `a.out.parent / "make-render-input.stage-result.json"`.
  - Manifest hashes input Revit extract (`a.extract`), lighting specification (`a.spec`), and local IES photometric curves; outputs hash `bedroom-render.json`.
  - Returns `enforce_clean_verdict({"passed": not bad, "exit_code": 1 if bad else 0, "orphans": orphans, ...}, exit_code=1)`.

---

## Verification Proofs

Comprehensive unit test suite created in [`tests/test_c14_phase2a.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_c14_phase2a.py):
1. **Real Recorded Failure Proof (l0029)**:
   - Cites verbatim lesson [docs/LEARNINGS.md:214](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/LEARNINGS.md#L214):
     `| Gates | A script printing FAIL but returning zero cannot gate a pipeline | Assert failed, missing and stale cases as well as passing cases; inspect saved evidence, not shell exit alone |`
   - For all four scripts, injects each script's real recorded failure condition:
     - `villa_option_pdfs`: `rb["failed"]` non-empty with clearance violations.
     - `villa_furnish_pdf`: `res["clearances"]["status"] == "fail"`.
     - `villa_concepts`: `res["fails"] = ["wc_access", "suite_privacy"]`.
     - `make_render_input`: orphan fixture in model not in specification.
   - Asserts each script exits non-zero (`SystemExit` code 1) and writes a stage result record with `status: "fail"` and `exit_code: 1`.
2. **Clean Run Proof**:
   - Executes clean inputs for all four scripts with heavy builders mocked (no Revit, Blender, or network dependencies).
   - Asserts `main()` exits with status `0` and writes stage result record with `status: "ok"` and `exit_code: 0`.
3. **Cryptographic Completeness and Hash Proof**:
   - Validates each stage record via [`validate_stage_result`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/stage_result.py#L269).
   - Proves all declared inputs and outputs exist on disk, are non-empty (`size_bytes > 0`), and have computed SHA-256 digests.

---

## Lessons Registered

Mapping of Defect Class C14 lessons to migrated scripts:
- **`l0029`** -> [`scripts/villa_option_pdfs.py:main`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_option_pdfs.py#L242)
- **`l0029`** -> [`scripts/villa_furnish_pdf.py:main`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_furnish_pdf.py#L121)
- **`l0029`** -> [`scripts/villa_concepts.py:main`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_concepts.py#L265)
- **`l0029` / `l0068`** -> [`scripts/make_render_input.py:main`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/make_render_input.py#L61)

---

## Changed Files Register

The following files were modified or created for Batch A1:
1. [`scripts/villa_option_pdfs.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_option_pdfs.py) - Added stage-result record write and `enforce_clean_verdict` gating on `rb['failed']`.
2. [`scripts/villa_furnish_pdf.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_furnish_pdf.py) - Added stage-result record write and `enforce_clean_verdict` gating on clearance check status.
3. [`scripts/villa_concepts.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/villa_concepts.py) - Added stage-result record write and `enforce_clean_verdict` gating on `res['fails']`.
4. [`scripts/make_render_input.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/make_render_input.py) - Added stage-result record write and `enforce_clean_verdict` gating on orphans/unmatched/no_source.
5. [`tests/test_c14_phase2a.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_c14_phase2a.py) - Added test proofs for (a) failure exit, (b) clean run, and (c) hash validation across all 4 scripts.
6. [`docs/stage-result-phase2-inventory.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/stage-result-phase2-inventory.md) - Marked the 4 scripts as migrated in Section 1 inventory table and Section 2 plan.
7. [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/LEARNINGS.md) - Appended Batch A1 migration line to `pipeline-result-lacks-atomic-proof` lesson entry.
8. [`docs/c14a-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/c14a-report.md) - This report.
