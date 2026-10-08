---
Document Outline:
  - [Overview](#overview)
  - [Migrated Scripts](#migrated-scripts)
  - [Skipped Scripts and Justification](#skipped-scripts-and-justification)
  - [Refactor Audit Compliance](#refactor-audit-compliance)
  - [Tests and Proofs](#tests-and-proofs)
  - [Documentation and Learnings](#documentation-and-learnings)
  - [Files Changed](#files-changed)
Executive Summary:
  Execution context Phase 2 Batch B migrates 13 command-line entry points to the shared launch preflight contract while skipping the dual-interpreter Blender worker.
  All CLI entry points strictly invoke project_context at the command-line boundary with declared inputs, outputs, and requirements, remaining side-effect free on import.
  Comprehensive AST verification, import isolation tests, and exit-code 2 failure proofs have been added to the test suite alongside documentation and learning record updates.
---

# Execution Context Phase 2 Batch B Report

## Overview

In Phase 2 Batch B of the execution-context migration, 14 target entry-point scripts were analyzed:
- 13 scripts were successfully migrated to the shared launch preflight boundary (`archpipe.execution_context.project_context`).
- 1 script (`scripts/products_worker.py`) was safely skipped because it runs as a headless Blender worker (`blender -b -P`) at the native workstation tool boundary.

All migrations follow the strict fail-closed contract established in Phase 1 and Batch A:
- Preflight runs strictly on the command-line path (inside `main()` or `if __name__ == "__main__"`).
- Top-level imports remain completely side-effect free.
- Required inputs, outputs, and third-party dependencies are explicitly declared.
- Any invalid context raises `ContextError`, resulting in a clean exit with code 2 and a single error message to stderr without tracebacks.

## Migrated Scripts

The following 13 scripts have been migrated:

1. [`scripts/configure_assistants.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/configure_assistants.py)
   - Refactored from top-level script execution into guarded `def main() -> None:`.
   - Preflight: declares input `ROOT / "scripts/archpipe_mcp.py"`.
   - All original top-level statements, variables, and assignments preserved verbatim in `main()`.

2. [`scripts/cubicasa_calibrate.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/cubicasa_calibrate.py)
   - Preflight inside `main()`: declares output directory `a.out.parent`, required modules `["numpy", "PIL"]`.
   - Catches `ContextError`, prints single preflight error message to stderr, exits 2.

3. [`scripts/delegate_implementation.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/delegate_implementation.py)
   - Preflight inside `main()`: declares input `args.task`.
   - Catches `ContextError`, prints single preflight error message to stderr, exits 2.

4. [`scripts/fetch_asset_library.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/fetch_asset_library.py)
   - Preflight inside `main()`: declares input `ROOT / "ops/workstation/library-manifest.json"`.
   - Catches `ContextError`, prints single preflight error message to stderr, exits 2.

5. [`scripts/fetch_families.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/fetch_families.py)
   - Preflight inside `main()`: declares output directory `a.out`.
   - Catches `ContextError`, prints single preflight error message to stderr, exits 2.

6. [`scripts/handoff.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/handoff.py)
   - Preflight inside `main()`: declares input `a.spec`, required modules `["yaml", "shapely", "ifcopenshell", "numpy"]`.
   - Catches `ContextError`, prints single preflight error message to stderr, exits 2.

7. [`scripts/preview_furniture_orientation.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/preview_furniture_orientation.py)
   - Refactored from top-level script execution into guarded `def main() -> None:`.
   - Preflight: declares input `a.scene`, required module `["PIL"]`.
   - All original top-level statements, variables, and assignments preserved verbatim in `main()`.

8. [`scripts/swiss_calibrate.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/swiss_calibrate.py)
   - Preflight inside `main()`: declares input `a.root / "geometries.csv"`, output directory `a.out.parent`, required module `["shapely"]`.
   - Catches `ContextError`, prints single preflight error message to stderr, exits 2.

9. [`scripts/swiss_stack_calibrate.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/swiss_stack_calibrate.py)
   - Preflight inside `main()`: declares input `a.root / "geometries.csv"`, output directory `a.out.parent`, required module `["shapely"]`.
   - Catches `ContextError`, prints single preflight error message to stderr, exits 2.

10. [`scripts/sync_agent_assets.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/sync_agent_assets.py)
    - Preflight inside `main()`: declares input `ROOT / "agents/roles.json"`.
    - Catches `ContextError`, prints single preflight error message to stderr, exits 2.

11. [`scripts/thermal_job.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/thermal_job.py)
    - Preflight inside `main()`: declares inputs `[a.input, a.epw]`, output directory `a.out`.
    - Catches `ContextError`, prints single preflight error message to stderr, exits 2.

12. [`scripts/villa_climate.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/villa_climate.py)
    - Refactored from top-level script execution into guarded `def main() -> None:`.
    - Preflight: declares input `[EPW]` (when run in `run` mode), required module `["shapely"]`.
    - All original top-level statements, variables, and assignments preserved verbatim in `main()`.

13. [`scripts/villa_concepts.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/villa_concepts.py)
    - Preflight inside `main()`: declares output directory `OUT`, required modules `["matplotlib", "numpy"]`.
    - Catches `ContextError`, prints single preflight error message to stderr, exits 2.

## Skipped Scripts and Justification

- [`scripts/products_worker.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/products_worker.py)
  - **Boundary and Rationale**: `products_worker.py` is a specialized dual-mode worker designed to run on the remote workstation:
    - Mode `fetch`: runs under workstation Python to download assets.
    - Mode `render`: runs directly inside headless Blender via `blender -b --factory-startup -P products_worker.py -- render ...`.
  - Inside Blender's `-P` execution, `products_worker.py` runs inside Blender's embedded Python interpreter where native host libraries like `bpy` exist, but project environment preflights (designed for CPython) are neither valid nor safe.
  - Like the pyRevit scripts in `revit/` and headless AutoCAD scripts in `scripts/build_sheet.py` (which were skipped in Batch A), `products_worker.py` is invoked through controlled driver boundaries (`scripts/products.py` and `scripts/villa_render.py`). Those drivers already perform preflight and environment validation before launching Blender.
  - Therefore, `products_worker.py` was skipped per the task specification: *"If a script cannot be migrated safely (e.g. it is a long-running server, or it needs Revit/AutoCAD which the preflight already handles differently), skip it and explain why in the report."*

## Refactor Audit Compliance

In Batch A, an agent inadvertently deleted a functional line (`compare_lux`'s `rendered = json.loads(...)`) while wrapping script code into `main()`.
For Batch B, strict discipline was maintained against `scripts/refactor_audit.py --base 247814a`:
- Every assignment, call target, and statement was preserved verbatim.
- For scripts refactored from module top-level into functions (`scripts/configure_assistants.py`, `scripts/preview_furniture_orientation.py`, `scripts/villa_climate.py`), statements were moved into `main()` without dropping any expressions, variables, or call targets.
- Zero functional lines or assignments were deleted or renamed.

## Tests and Proofs

Extended [`tests/test_execution_context.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_execution_context.py) with 4 new tests covering the entire Batch B migration:

1. `test_batch_b_scripts_call_preflight_in_main_and_not_at_module_top_level`:
   - Uses Python AST parsing to scan each of the 13 migrated scripts.
   - Verifies that `project_context` is invoked inside `main()` or `if __name__ == "__main__"` blocks.
   - Asserts that zero calls to `project_context` exist at module top level.

2. `test_importing_batch_b_scripts_does_not_run_preflight`:
   - Patches `archpipe.execution_context.project_context` with a mock that raises `AssertionError("preflight ran on import")`.
   - Iterates through all 13 migrated scripts and dynamically imports each via `importlib.import_module`.
   - Proves that importing any migrated script is completely side-effect free and never triggers preflight.

3. `test_handoff_subprocess_exits_2_on_missing_input`:
   - Executes `scripts/handoff.py --spec tests/fixtures/nonexistent_spec_batch_b.yaml` in a subprocess.
   - Verifies exit code 2 and verifies stderr output starts with `PREFLIGHT FAILED:` with no unhandled traceback.

4. `test_swiss_calibrate_subprocess_exits_2_on_missing_dependency`:
   - Executes `scripts/swiss_calibrate.py` in a subprocess with `ARCHPIPE_TEST_EXTRA_MODULES=nonexistent_missing_module_batch_b`.
   - Verifies exit code 2 and verifies stderr output starts with `PREFLIGHT FAILED:` detailing the missing module with no unhandled traceback.

## Documentation and Learnings

1. [`docs/execution-context.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/execution-context.md):
   - Updated inventory table rows for all 14 Batch B entry points (13 Shared, 1 Skipped).
   - Added subsection `### Completed Phase 2 item: Phase 2 Batch B entry points`.
   - Appended Batch B checkpoint entry to `## Checkpoint evidence`.

2. [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md):
   - Appended a learning line to the existing `execution-context-wrong-interpreter` entry recording the Batch B migration and the Blender `-P` worker skip boundary.

## Files Changed

Only the following 17 files were modified or created:
- [`scripts/configure_assistants.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/configure_assistants.py)
- [`scripts/cubicasa_calibrate.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/cubicasa_calibrate.py)
- [`scripts/delegate_implementation.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/delegate_implementation.py)
- [`scripts/fetch_asset_library.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/fetch_asset_library.py)
- [`scripts/fetch_families.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/fetch_families.py)
- [`scripts/handoff.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/handoff.py)
- [`scripts/preview_furniture_orientation.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/preview_furniture_orientation.py)
- [`scripts/swiss_calibrate.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/swiss_calibrate.py)
- [`scripts/swiss_stack_calibrate.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/swiss_stack_calibrate.py)
- [`scripts/sync_agent_assets.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/sync_agent_assets.py)
- [`scripts/thermal_job.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/thermal_job.py)
- [`scripts/villa_climate.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/villa_climate.py)
- [`scripts/villa_concepts.py`](file:///C:/Users/mmbka/arch-pipeline-agy/scripts/villa_concepts.py)
- [`tests/test_execution_context.py`](file:///C:/Users/mmbka/arch-pipeline-agy/tests/test_execution_context.py)
- [`docs/execution-context.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/execution-context.md)
- [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/LEARNINGS.md)
- [`docs/exec4-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy/docs/exec4-report.md)
