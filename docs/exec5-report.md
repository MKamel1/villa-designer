---
Document Outline:
- [Executive Summary](#executive-summary)
- [Migration Methodology and Safety Invariants](#migration-methodology-and-safety-invariants)
- [Batch C Migrated Entry-Point Scripts](#batch-c-migrated-entry-point-scripts)
- [Defect Controls and Verification Proofs](#defect-controls-and-verification-proofs)
- [Documentation Updates](#documentation-updates)
- [Changed Files List](#changed-files-list)

Executive Summary:
This report records the completion of Phase 2 Batch C migrating 13 entry-point scripts to the shared project_context launch preflight. All target scripts execute the preflight strictly inside command-line entry points, ensuring module imports remain side-effect free and preserving all original calculations and dispatch semantics. Four proving tests were added to tests/test_execution_context.py, and documentation was synchronized in docs/execution-context.md and docs/LEARNINGS.md.
---

# Execution Context Phase 2 Batch C Migration Report

## Migration Methodology and Safety Invariants

The migration follows the established pattern from Batch A and Batch B while adhering to strict behavioral invariants:
1. **Command-Line Only Preflight**: Preflight (`project_context`) is invoked strictly on the CLI path inside `main(argv=None) -> int` or under an `if __name__ == "__main__":` block. Top-level module imports by other tools, test suites, or pipeline stages remain completely side-effect free.
2. **Preservation of Statements and Semantics**: Top-level script blocks were wrapped into guarded `main()` entry points without deleting or altering any variable assignments, function calls, or error handling (e.g. `KeyError` on unknown commands in dictionary dispatch, `raise SystemExit(__doc__)` in `villa_env.py`).
3. **Fail-Closed Execution Contract**: Real inputs, output directories, and third-party dependencies mapped from `requirements.txt` (such as `numpy`, `PIL`, `shapely`, `matplotlib`) are verified prior to execution. Missing dependencies or inputs raise `ContextError`, exiting with code 2 and a single descriptive message without Python tracebacks.

## Batch C Migrated Entry-Point Scripts

The following 13 scripts were migrated:

1. [scripts/villa_daylight.py](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/villa_daylight.py)
   - **Invocation**: Wrapped CLI logic into `main(argv=None) -> int`.
   - **Preflight Parameters**: Declared root `ROOT`, output `LOCAL.parent`, required modules `["numpy", "PIL", "matplotlib"]`.
   - **Dispatch**: Preserved command dispatch dictionary `{"run": run, "fetch": fetch}[cmd]()` retaining standard `KeyError` on invalid commands.

2. [scripts/villa_daylight_finished.py](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/villa_daylight_finished.py)
   - **Invocation**: Wrapped CLI logic into `main(argv=None) -> int`.
   - **Preflight Parameters**: Declared root `ROOT`, output `LOCAL.parent`.
   - **Dispatch**: Preserved command dispatch `{"report": report, "fetch": fetch}[cmd]()` retaining standard `KeyError` on invalid commands and `IndexError` on missing arguments.

3. [scripts/villa_daylight_pdf.py](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/villa_daylight_pdf.py)
   - **Invocation**: Updated existing `main(argv=None) -> int` to invoke `project_context` before generating PDF.
   - **Preflight Parameters**: Declared root `ROOT`, inputs `[LOCAL / "report.json"]`, output `LOCAL.parent`, required modules `["matplotlib"]`.

4. [scripts/villa_daylight_summary.py](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/villa_daylight_summary.py)
   - **Invocation**: Updated `main(argv=None) -> int` to invoke `project_context` before loading report files.
   - **Preflight Parameters**: Declared root `ROOT`, inputs `[LUX_JOB / "report.json", DF_JOB / "report.json", OUT / "views" / "stats.json"]`, output `OUT`.
   - **Variables**: Maintained module-level constants `OUT`, `DF_JOB`, `LUX_JOB`, `CASES`, `OPTIONS`, `SUMMARY`.

5. [scripts/villa_env.py](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/villa_env.py)
   - **Invocation**: Updated `main(argv=None) -> int` with command validation before dispatch.
   - **Preflight Parameters**: Conditioned on command: `check` verifies `[OUT / "env-spec.json", rb_path]`; `plan` verifies `[OUT / "env-spec.json", OUT / "env-readback.json"]` and requires `["matplotlib"]`; `spec` declares output `OUT`.
   - **Unknown Commands**: Retained `raise SystemExit(__doc__)` for unrecognized commands.

6. [scripts/villa_furnish_build.py](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/villa_furnish_build.py)
   - **Invocation**: Updated `main(argv=None) -> int` with `project_context` call.
   - **Preflight Parameters**: Declared root `ROOT`, output `OUT`, required modules `["shapely"]`. In non-spec check mode, inputs include `[OUT / "readback.json", OUT / "options-spec.json"]`.

7. [scripts/villa_furnish_pdf.py](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/villa_furnish_pdf.py)
   - **Invocation**: Updated `main(argv=None) -> int` to invoke `project_context` before generating floor plans.
   - **Preflight Parameters**: Declared root `ROOT`, output `OUT`, required modules `["matplotlib", "shapely"]`.

8. [scripts/villa_lighting_pdf.py](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/villa_lighting_pdf.py)
   - **Invocation**: Updated `main(argv=None) -> int` to invoke `project_context` before rendering lighting layouts.
   - **Preflight Parameters**: Declared root `ROOT`, output `OUT`, required modules `["matplotlib", "shapely"]`.

9. [scripts/villa_option_pdfs.py](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/villa_option_pdfs.py)
   - **Invocation**: Updated `main(argv=None) -> int` with `project_context` call.
   - **Preflight Parameters**: Declared root `ROOT`, output `OPT`, required modules `["numpy", "PIL", "matplotlib"]`. Inputs in PDF generation mode require `[OPT / "readback.json"]`.

10. [scripts/villa_r11_compare.py](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/villa_r11_compare.py)
    - **Invocation**: Updated `main(argv=None) -> int` to invoke `project_context`.
    - **Preflight Parameters**: Declared root `ROOT`, output `OUT`, required modules `["matplotlib"]`. Input `[SUM]` is declared when present on disk, preserving existing fallback behavior (`(daylight pending)`).

11. [scripts/villa_stair_options.py](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/villa_stair_options.py)
    - **Invocation**: Updated `main(argv=None) -> int` to invoke `project_context`.
    - **Preflight Parameters**: Declared root `ROOT`, output `OUT`, required modules `["matplotlib"]`.

12. [scripts/villa_stairs.py](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/villa_stairs.py)
    - **Invocation**: Wrapped CLI execution block into `main(argv=None) -> int`.
    - **Preflight Parameters**: Declared root `ROOT`, output `OUT`. Inputs for `compare` mode require `[OUT / "stairs-readback.json"]`.

13. [scripts/yard_wall_pdf.py](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/yard_wall_pdf.py)
    - **Invocation**: Updated `main(argv=None) -> int` to invoke `project_context`.
    - **Preflight Parameters**: Declared root `ROOT`, inputs `[DIR / "yard-wall-readback.json"]`, output `DIR`, required modules `["numpy", "PIL", "matplotlib"]`.

*Note*: As instructed, `scripts/villa_render_views.py`, `scripts/villa_review_page.py`, and `scripts/villa_render_selftest.py` were not modified as they are undergoing concurrent edits elsewhere.

## Defect Controls and Verification Proofs

Four proving tests were added to [tests/test_execution_context.py](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_execution_context.py):

1. **`test_batch_c_scripts_call_preflight_in_main_and_not_at_module_top_level`**:
   - Parses the abstract syntax tree of all 13 Batch C scripts.
   - Asserts zero calls to `project_context` or `preflight` at module top level.
   - Asserts at least one call to `project_context` or `preflight` inside `main()` or the `__main__` block.

2. **`test_importing_batch_c_scripts_does_not_run_preflight`**:
   - Patches `execution_context.preflight` and `execution_context.project_context` with side effects that raise `AssertionError`.
   - Iterates through all 13 Batch C scripts, loading each dynamically via `importlib.util.spec_from_file_location` and `exec_module`.
   - Verifies that importing each module produces zero preflight calls.

3. **`test_yard_wall_pdf_subprocess_exits_2_on_missing_input`**:
   - Executes `scripts/yard_wall_pdf.py` as a subprocess where declared input `out/villa/yard-wall/yard-wall-readback.json` is absent.
   - Verifies return code equals 2.
   - Asserts stderr contains `"PREFLIGHT FAILED:"` and `"missing file"`, with zero tracebacks.

4. **`test_villa_furnish_pdf_subprocess_exits_2_on_missing_dependency`**:
   - Executes `scripts/villa_furnish_pdf.py` as a subprocess with `ARCHPIPE_TEST_EXTRA_MODULES` injecting an uninstalled dependency.
   - Verifies return code equals 2.
   - Asserts stderr contains `"PREFLIGHT FAILED:"`, the missing dependency name, and the project venv hint, with zero tracebacks.

## Documentation Updates

- [docs/execution-context.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/execution-context.md):
  - Updated the inventory table rows for all 13 Batch C scripts from `Phase 2: no shared preflight` to `Shared: ...`.
  - Added section `### Completed Phase 2 item: Phase 2 Batch C entry points`.
- [docs/LEARNINGS.md](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md):
  - Appended the Phase 2 Batch C summary line under the existing `### execution-context-wrong-interpreter — interpreter environment, not just version` entry without creating a duplicate section.

## Changed Files List

The following 16 files were modified:
- `scripts/villa_daylight.py`
- `scripts/villa_daylight_finished.py`
- `scripts/villa_daylight_pdf.py`
- `scripts/villa_daylight_summary.py`
- `scripts/villa_env.py`
- `scripts/villa_furnish_build.py`
- `scripts/villa_furnish_pdf.py`
- `scripts/villa_lighting_pdf.py`
- `scripts/villa_option_pdfs.py`
- `scripts/villa_r11_compare.py`
- `scripts/villa_stair_options.py`
- `scripts/villa_stairs.py`
- `scripts/yard_wall_pdf.py`
- `tests/test_execution_context.py`
- `docs/execution-context.md`
- `docs/LEARNINGS.md`
