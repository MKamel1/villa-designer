---
document_outline:
  - "[1. Overview and Scope](#1-overview-and-scope)"
  - "[2. Migrated Scripts (16)](#2-migrated-scripts-16)"
  - "[3. Skipped Scripts and Rationale (4)](#3-skipped-scripts-and-rationale-4)"
  - "[4. Shared Preflight Integration Pattern](#4-shared-preflight-integration-pattern)"
  - "[5. Proving Tests in tests/test_execution_context.py](#5-proving-tests-in-teststest_execution_contextpy)"
  - "[6. Documentation and Learning Updates](#6-documentation-and-learning-updates)"
  - "[7. Inventory of Changed Files](#7-inventory-of-changed-files)"
executive_summary: >
  Execution context Phase 2 Batch A migrates 16 command-line entry points in branch agy/exec3 to the shared launch preflight, enforcing fail-closed launch validation for declared inputs and dependencies while keeping module imports completely side-effect free. Four scripts with external or long-running boundaries (archpipe_mcp.py, build_sheet.py, capture_plot_prompts.py, luminaire_demo.py) were safely skipped with clear technical justifications. Proving tests in tests/test_execution_context.py verify AST-level call placement, import-time isolation, and exit-2 subprocess behavior on invalid context.
---

# Execution Context Phase 2 Batch A Migration Report

## 1. Overview and Scope

This migration implements Phase 2 Batch A of the execution context program in branch `agy/exec3` under `C:/Users/mmbka/arch-pipeline-agy`.

The objective was to evaluate the 20 designated entry-point scripts in `scripts/`, migrate safe command-line entry points to the shared launch preflight (`archpipe.execution_context.project_context`), verify that all public functions and imports remain side-effect free, and establish comprehensive test proofs for call placement, import isolation, and invalid-context exit code 2.

Of the 20 candidate scripts:
- **16 scripts** were migrated to the shared `project_context` preflight.
- **4 scripts** were skipped due to long-running server lifecycles or distinct external automation boundaries (AutoCAD / raw pyRevit).

## 2. Migrated Scripts (16)

The following 16 scripts were migrated to call `archpipe.execution_context.project_context` within their CLI paths:

1. [`scripts/check_bedroom.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/check_bedroom.py):
   - Declared inputs: `--spec` (default `spec/bedroom-revit.yaml`), `--extract` (default `out/bedroom-extract.json`).
   - Declared requirements: `yaml`.
   - Entry point: `main()`.

2. [`scripts/compare_lux.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/compare_lux.py):
   - Declared inputs: `--rendered` (default `out/bedroom-rendered-lux.json`), `--extract` (default `out/bedroom-extract.json`).
   - Entry point: `main()`.

3. [`scripts/concept.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/concept.py):
   - Declared inputs: `knowledge/projects/villa-pilot.json`.
   - Declared requirements: `matplotlib`, `yaml`, `shapely`.
   - Entry point: `main()`.

4. [`scripts/demo_bedroom_lighting.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/demo_bedroom_lighting.py):
   - Refactored top-level script execution into `def main() -> int` protected by `project_context`.
   - Previously executed IES photometry resolution on module import; now completely import-safe across environments without local IES assets.
   - Entry point: `main()`.

5. [`scripts/demo_guidance.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/demo_guidance.py):
   - Declared inputs: `knowledge/projects/villa-pilot.json`.
   - Declared requirements: `yaml`, `shapely`.
   - Entry point: `main()`.

6. [`scripts/export_bedroom_glb.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/export_bedroom_glb.py):
   - Declared inputs: positional `input` model file.
   - Entry point: `main()`.

7. [`scripts/knowledge.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/knowledge.py):
   - Declared requirements: `pymupdf`.
   - Entry point: `main()`.

8. [`scripts/lighting_report.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/lighting_report.py):
   - Declared inputs: positional `input` file.
   - Entry point: `main()`.

9. [`scripts/luminaires.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/luminaires.py):
   - Declared context record: `out/luminaires-execution-context.json`.
   - Entry point: `main()`.

10. [`scripts/make_bedroom_extract.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/make_bedroom_extract.py):
    - Declared context record: `out/make-bedroom-extract-execution-context.json`.
    - Entry point: `main()`.

11. [`scripts/make_bedroom_spec.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/make_bedroom_spec.py):
    - Declared inputs: `--spec` (default `spec/bedroom-revit.yaml`).
    - Declared requirements: `yaml`.
    - Entry point: `main()`.

12. [`scripts/make_render_input.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/make_render_input.py):
    - Declared inputs: `--extract` (default `out/bedroom-extract.json`), `--spec` (default `spec/bedroom-revit.yaml`).
    - Declared requirements: `yaml`.
    - Entry point: `main()`.

13. [`scripts/products.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/products.py):
    - Declared requirements: `PIL`.
    - Entry point: `main()`.

14. [`scripts/review_model.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/review_model.py):
    - Declared inputs: `--extract` (default `out/bedroom-extract.json`).
    - Declared requirements: `shapely`.
    - Entry point: `main()`.

15. [`scripts/semantic.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/semantic.py):
    - Declared context record: `out/semantic-execution-context.json`.
    - Entry point: `main()`.

16. [`scripts/sources.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/sources.py):
    - Declared inputs: `knowledge/library.json`.
    - Entry point: `main()`.

## 3. Skipped Scripts and Rationale (4)

Four scripts from Batch A were evaluated and intentionally skipped from this command-line batch:

1. [`scripts/archpipe_mcp.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/archpipe_mcp.py):
   - **Rationale**: Long-running FastMCP standard I/O server (`mcp.run(transport='stdio')`). It runs indefinitely waiting on RPC requests, rather than a bounded CLI task. Furthermore, `mcp` is an optional server dependency not declared in project `requirements.txt`.

2. [`scripts/build_sheet.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/build_sheet.py):
   - **Rationale**: External headless AutoCAD console runner (`src/archpipe/acad.py::_run`, `accoreconsole.exe`). As specified in [`docs/execution-context.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/execution-context.md) line 89, AutoCAD execution is a separate native integration boundary requiring executable release detection, version probes, and drawing/script path contracts.

3. [`scripts/capture_plot_prompts.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/capture_plot_prompts.py):
   - **Rationale**: External headless AutoCAD runner using `src/archpipe/acad.py::_run`. Same boundary as `build_sheet.py`.

4. [`scripts/luminaire_demo.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/luminaire_demo.py):
   - **Rationale**: Raw pyRevit 6.5.5 subprocess runner executing without `run_checked` or `Tool` contracts. Managed pyRevit runs are executed through [`scripts/run_bedroom.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/run_bedroom.py).

## 4. Shared Preflight Integration Pattern

To support clean integration across all 16 scripts:
1. [`src/archpipe/execution_context.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/execution_context.py) was enhanced to allow `project_context` to accept:
   - `inputs=()`: declared files that must exist at project root or absolute paths.
   - `output: Path | None = None`: declared output path.
   - `temp: Path | None = None`: declared temporary directory.
   - Automatic inclusion of `ARCHPIPE_TEST_EXTRA_MODULES` into required module checks for testing invalid context injection.

2. In each migrated script:
   - `project_context` is invoked inside `main()` or under the `if __name__ == "__main__":` block.
   - Any `ContextError` is caught immediately:
     ```python
     try:
         project_context(ROOT, Path(__file__), "name", inputs=[...], required_modules=[...])
     except ContextError as exc:
         sys.stderr.write(f"PREFLIGHT FAILED: {exc}\n")
         return 2
     ```
   - On context failure, the script outputs a single diagnostic line to `sys.stderr` without tracebacks and exits with status 2.
   - Module imports remain side-effect free, ensuring tests and other importers can load the modules without triggering preflight or file system access.

## 5. Proving Tests in tests/test_execution_context.py

Four comprehensive proving tests were added to [`tests/test_execution_context.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_execution_context.py):

1. **AST Placement Test (`test_batch_a_scripts_call_preflight_in_main_and_not_at_module_top_level`)**:
   - Parses each of the 16 migrated scripts using Python's `ast` module.
   - Asserts 0 calls to `project_context` or `preflight` at module top level.
   - Asserts >=1 call to `project_context` or `preflight` inside `main()` or the `if __name__ == "__main__":` guard block.

2. **Import Isolation Test (`test_importing_batch_a_scripts_does_not_run_preflight`)**:
   - Patches `archpipe.execution_context.preflight` and `archpipe.execution_context.project_context` to raise an `AssertionError` if invoked.
   - Dynamically loads and executes each of the 16 scripts using `importlib.util.spec_from_file_location` and `spec.loader.exec_module`.
   - Confirms that importing any migrated module never triggers preflight.

3. **Subprocess Exit-2 on Missing Dependency (`test_check_bedroom_subprocess_exits_2_on_missing_dependency`)**:
   - Launches `scripts/check_bedroom.py` in a subprocess with `ARCHPIPE_TEST_EXTRA_MODULES` set to an absent module.
   - Verifies the process terminates with exit code 2.
   - Confirms `sys.stderr` contains `PREFLIGHT FAILED:`, identifies the missing module, names the active interpreter, provides the `.venv` hint, contains no Python tracebacks, and prints exactly one output line.

4. **Subprocess Exit-2 on Missing Input File (`test_make_render_input_subprocess_exits_2_on_missing_input`)**:
   - Launches `scripts/make_render_input.py` in a subprocess with `--extract out/nonexistent_extract_test_c9x.json`.
   - Verifies the process terminates with exit code 2.
   - Confirms `sys.stderr` contains `PREFLIGHT FAILED:`, identifies the missing file, contains no tracebacks, and prints exactly one output line.

## 6. Documentation and Learning Updates

1. [`docs/execution-context.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/execution-context.md):
   - Updated the inventory table for all 20 Batch A scripts (lines 23-55), changing migrated scripts to `Shared: ...` and skipped scripts to `Skipped in Phase 2 Batch A: ...` with reasons.
   - Added `### Completed Phase 2 item: Phase 2 Batch A entry points` detailing the 16 migrated scripts, 4 skipped scripts, and 4 test proofs.
   - Appended a Phase 2 Batch A checkpoint evidence note under `## Checkpoint evidence`.

2. [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md):
   - Appended a Phase 2 Batch A record to the existing entry `### execution-context-wrong-interpreter — interpreter environment, not just version` without creating any duplicate section.

## 7. Inventory of Changed Files

The following 21 files represent the complete list of files modified or created for this task:

1. [`src/archpipe/execution_context.py`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/execution_context.py)
2. [`scripts/check_bedroom.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/check_bedroom.py)
3. [`scripts/compare_lux.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/compare_lux.py)
4. [`scripts/concept.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/concept.py)
5. [`scripts/demo_bedroom_lighting.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/demo_bedroom_lighting.py)
6. [`scripts/demo_guidance.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/demo_guidance.py)
7. [`scripts/export_bedroom_glb.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/export_bedroom_glb.py)
8. [`scripts/knowledge.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/knowledge.py)
9. [`scripts/lighting_report.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/lighting_report.py)
10. [`scripts/luminaires.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/luminaires.py)
11. [`scripts/make_bedroom_extract.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/make_bedroom_extract.py)
12. [`scripts/make_bedroom_spec.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/make_bedroom_spec.py)
13. [`scripts/make_render_input.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/make_render_input.py)
14. [`scripts/products.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/products.py)
15. [`scripts/review_model.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/review_model.py)
16. [`scripts/semantic.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/semantic.py)
17. [`scripts/sources.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/sources.py)
18. [`tests/test_execution_context.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_execution_context.py)
19. [`docs/execution-context.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/execution-context.md)
20. [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md)
21. [`docs/exec3-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/exec3-report.md)
