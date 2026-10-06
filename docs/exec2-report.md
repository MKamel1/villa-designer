---
outline:
  - "[Executive Summary](#executive-summary)"
  - "[Incident Background](#incident-background)"
  - "[Architectural Solution](#architectural-solution)"
  - "[Test Suite and Verification Proofs](#test-suite-and-verification-proofs)"
  - "[Documentation and Learning Registry](#documentation-and-learning-registry)"
  - "[Changed Files Inventory](#changed-files-inventory)"
summary:
  This report documents the resolution of the Phase 2 execution-context defect
  where an unsupported interpreter environment passed python version checks but
  crashed at import time due to missing dependencies. Preflight dependency checks
  via find_spec, early entry point bootstrapping, and automated exit code 2 guards
  now guarantee immediate diagnostic feedback pointing to the project venv.
---

# Execution Context Phase 2 Report: Interpreter Environment Verification

<a id="executive-summary"></a>
## Executive Summary

On 2026-10-06, a 31-minute failure occurred when the Windows test suite was executed using the system Python interpreter (`C:\Python314\python.exe`) rather than the project virtual environment. Although the interpreter version (3.14) passed preflight release version checks, it lacked third-party project packages, causing 24 test modules to crash with `ModuleNotFoundError: No module named 'shapely'` and [`scripts/verify.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/verify.py) to abort at top-level import.

This phase resolved the issue by extending [`preflight`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/execution_context.py#L185-L231) and [`project_context`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/execution_context.py#L241-L250) in [`src/archpipe/execution_context.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/execution_context.py) with declared Python module dependency checks via [`importlib.util.find_spec`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/execution_context.py#L89-L92) (avoiding import side effects). Both [`scripts/run_tests.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/run_tests.py) and [`scripts/verify.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/verify.py) now execute this preflight check before any third-party or application domain imports, exiting with code 2 and a single clear diagnostic error pointing to the project virtual environment.

<a id="incident-background"></a>
## Incident Background

- **Incident Date**: 2026-10-06 (lead review).
- **Observed Behavior**: Windows full suite was launched using system interpreter `C:\Python314\python.exe` instead of the project venv (`C:\Users\mmbka\arch-pipeline\.venv\Scripts\python.exe`).
- **Escape Analysis**: `preflight` checked Python version release numbers (`3.11 <= sys.version_info[:2] <= 3.14`), but did not verify installed packages in the active environment. In addition, [`scripts/verify.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/verify.py) imported `yaml` and `archpipe.rules` at top level before invoking [`project_context`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/execution_context.py#L241-L250), crashing with `ModuleNotFoundError` before the execution context could even initialize.
- **Impact**: 31 minutes were lost diagnosing errors that appeared as application code regressions rather than environment configuration mistakes.

<a id="architectural-solution"></a>
## Architectural Solution

1. **Explicit Package Mapping (`DISTRIBUTION_TO_IMPORT`)**:
   [`DISTRIBUTION_TO_IMPORT`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/execution_context.py#L24-L42) in [`src/archpipe/execution_context.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/execution_context.py) explicitly maps distribution package names to Python top-level module import names (e.g. `PyYAML` -> `yaml`, `pillow` -> `PIL`, `pymupdf` -> `pymupdf`, `shapely` -> `shapely`, `matplotlib` -> `matplotlib`).
2. **Requirements Parsing ([`requirements_import_names`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/execution_context.py#L45-L66))**:
   Parses a given `requirements.txt` file and resolves each dependency to its mapped import module without guessing unlisted packages.
3. **Non-Intrusive Dependency Inspection ([`check_dependencies`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/execution_context.py#L69-L116))**:
   Uses `importlib.util.find_spec` to locate modules without triggering module execution or import side effects. If any module is missing:
   - Constructs a single diagnostic message:
     `missing required Python module(s): <modules>; interpreter: <sys.executable>; use the project environment (e.g. <root>/.venv/Scripts/python.exe on Windows or the worker venv on the workstation)`
   - Computes the venv hint dynamically from the project root (`root / ".venv"`), avoiding hardcoded user directories.
   - Raises [`ContextError`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/execution_context.py#L119-L120), mapping to exit code 2 at the CLI boundary.
4. **Context Record Enrichment**:
   Recorded in the JSON execution context record under the `"modules"` key (`{module_name: {"found": bool}}`).
5. **Entry Point Integration**:
   - [`scripts/preflight.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/preflight.py): Added `--module` and `--requirements` arguments.
   - [`scripts/run_tests.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/run_tests.py): Passes required modules derived from `requirements.txt` (and optional `ARCHPIPE_TEST_EXTRA_MODULES` / `ARCHPIPE_TEST_REQUIREMENTS_FILE`) to [`project_context`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/execution_context.py#L241-L250). Catches [`ContextError`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/execution_context.py#L119-L120) and exits 2.
   - [`scripts/verify.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/verify.py): Restructured bootstrap so standard library imports and [`project_context`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/execution_context.py#L241-L250) execute *before* third-party `yaml` and `archpipe` domain imports. In `main()`, unconditionally asserts that dependencies are recorded and that `shapely` is found.

<a id="test-suite-and-verification-proofs"></a>
## Test Suite and Verification Proofs

In [`tests/test_execution_context.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_execution_context.py):
1. **Missing Module Verification ([`test_missing_declared_module_fails_with_interpreter_and_hint`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_execution_context.py#L238-L245))**:
   Asserts that an uninstalled module (e.g. `archpipe_nonexistent_mod_c9x`) raises [`ContextError`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/execution_context.py#L119-L120) containing the module name, interpreter executable path, and `.venv` hint.
2. **Present Modules Stay Quiet ([`test_all_present_modules_stay_quiet_and_recorded_in_context`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_execution_context.py#L247-L252))**:
   Asserts that present modules (`json`, `pathlib`) pass quietly and are recorded under `context["modules"]` with `{"found": True}`.
3. **Real Incident Reproduction by Value ([`test_real_incident_reproduced_by_value_shapely_missing`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_execution_context.py#L253-L276))**:
   Simulates `find_spec("shapely")` returning `None` against the real list of required imports from `requirements.txt`. Asserts the raised [`ContextError`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/execution_context.py#L119-L120) names `shapely`, the interpreter, and the venv hint.
4. **Subprocess Test Runner Guard ([`test_run_tests_subprocess_exits_2_on_missing_dependency`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_execution_context.py#L277-L293))**:
   Runs [`scripts/run_tests.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/run_tests.py) with `ARCHPIPE_TEST_EXTRA_MODULES=archpipe_nonexistent_mod_c9x`. Proves that the runner exits 2 (not 1), prints the clean error to `stderr`, and emits no traceback.
5. **Subprocess Verifier Guard ([`test_verify_subprocess_exits_2_on_missing_dependency`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_execution_context.py#L294-L310))**:
   Runs [`scripts/verify.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/verify.py) with `ARCHPIPE_TEST_EXTRA_MODULES=archpipe_nonexistent_mod_c9x`. Proves that the verifier bootstrap exits 2 (not 1), prints the error to `stderr`, and emits no traceback.
6. **Requirements Import Mapping Test ([`test_requirements_import_names_mapping`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_execution_context.py#L311-L316))**:
   Verifies that `requirements.txt` maps accurately to `["ezdxf", "matplotlib", "PIL", "pymupdf", "yaml", "shapely", "ifcopenshell"]`.

<a id="documentation-and-learning-registry"></a>
## Documentation and Learning Registry

- [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/LEARNINGS.md): Added learning entry `execution-context-wrong-interpreter — interpreter environment, not just version` covering observation, discovery, reproduction, root cause, escape mechanism, class & siblings, two-tier control, proofs, and registry reference.
- [`docs/execution-context.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/execution-context.md): Documented the new dependency check parameters and API, updated entry-point inventory coverage for [`scripts/run_tests.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/run_tests.py) and [`scripts/verify.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/verify.py), marked the Phase 2 item completed with incident details, and added `execution-context-wrong-interpreter` to the Guard registry.

<a id="changed-files-inventory"></a>
## Changed Files Inventory

The following files were modified or created for this task:

1. [`src/archpipe/execution_context.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/execution_context.py)
2. [`scripts/preflight.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/preflight.py)
3. [`scripts/run_tests.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/run_tests.py)
4. [`scripts/verify.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/verify.py)
5. [`tests/test_execution_context.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_execution_context.py)
6. [`docs/execution-context.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/execution-context.md)
7. [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/LEARNINGS.md)
8. [`docs/exec2-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/exec2-report.md)
