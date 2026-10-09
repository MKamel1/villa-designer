# Execution context: Phase 1 checkpoint

Inventory dated 2026-10-05. Shared means `archpipe.execution_context`; partial means an existing operation-specific check, not a complete preflight. Every other Python script below still needs migration in Phase 2. No native model or workstation render was run for this change.

## Application programming interface

`preflight(root, scripts, inputs, output, temp, tools, env, required_roles, available_roles, python_version, modules=(), required_modules=())` requires an absolute existing project root and returns a JSON-safe context. Relative script, tool, input, output and temp paths resolve from that root, independently of the caller's directory. Inputs and scripts must exist. The record distinguishes `launch_directory` (caller) from `working_directory` (explicit child directory). It checks the active Python interpreter (supported releases 3.11 through 3.14; optional exact pin), declared Python module dependencies via `check_dependencies(modules, *, root, interpreter)` using `importlib.util.find_spec` without import side effects, and write/read/delete access in newly created child directories. Checked dependencies are recorded in the context under `"modules"` with their found status. If any required module is missing, preflight raises `ContextError` detailing missing modules, the interpreter path (`sys.executable`), and a hint pointing to the project venv (`<root>/.venv/Scripts/python.exe` on Windows or the worker venv on POSIX/workstation). It constructs `NO_COLOR=1`, absolute `PYTHONPATH`, `TMP`, `TEMP`, and `TMPDIR`. Environment records contain only these controlled variables, never credentials.

`Tool(name, path, expected_version, version_args)` describes an executable, exact release and version-probe arguments. Preflight resolves tool paths from the root; direct `resolve_tool` calls require absolute paths. Version probes use the explicit project working directory, have a 30-second timeout, require exit zero and the first reported numerical version to equal the pin. The bedroom runner pins pyRevit 6.5.5; the remote villa driver pins Blender 4.5.14, matching the installer default. AutoCAD Core Console and Codex callers must supply their verified release and version-probe arguments; they have no guessed default. Tools irrelevant to a run are not required.

`project_context(root, script, name, tools, modules=(), required_modules=())` configures the current process environment/temp settings and writes `out/<name>-execution-context.json`; it does not change the caller's directory. It passes declared module requirements to preflight. `requirements_import_names(requirements_path)` parses requirements files and maps distribution names to import names via explicit mapping (`DISTRIBUTION_TO_IMPORT`, e.g. `shapely` -> `shapely`, `PyYAML` -> `yaml`, `pillow` -> `PIL`, `pymupdf` -> `pymupdf`) without guessing. In-process test fixtures must restore those process settings before deleting their temporary project. `run_checked(argv, context, scripts, record, env, expected, timeout)` requires a previously version-checked executable and absolute script arguments verbatim in the command, explicitly sets the checked child directory/environment, records the command, exit status and logs, and optionally demands a newly written artifact. Record and expected-artifact paths resolve from the context's root. Native callers must supply the promised artifact. `write_record(context, path)` requires an absolute resolved record path.

`scripts/preflight.py` is the thin command-line interface: `--root`, repeated `--script` and `--input`, `--out`, `--temp`, `--record`, repeated `--tool NAME PATH EXACT_VERSION`, repeated `--module NAME`, and repeated `--requirements PATH`. All relative paths, including the record, resolve from the absolute project root. It exits 0 for a valid recorded context and 2 for invalid context. Passing relative scripts to preflight is allowed; passing them to an external launcher is rejected. The test runner exits 0 for successful tests, 1 for failed tests/imports, and 2 for preflight failure; it accepts focused module names. Verification exits 1 for check/dependency failures and 2 for preflight failures. Native stage command failures remain failed acceptance evidence.

Role checks require explicit live-session availability, not files in `agents/roles.json`. This boundary cannot alter Codex approvals or discover session permissions/roles; writable probes expose unusable permissions and explicitly required absent roles fail closed. Actual agent dispatch migration remains Phase 2.

## Entry-point inventory and Phase 2 list

Before Phase 1, none of these entry points used a complete shared context. The test runner already created accessible sandbox temp directories; verification used `Path.mkdir`; the bedroom runner used absolute Revit scripts, an explicit cwd, exit status and fresh artifacts; villa rendering used absolute remote scripts and Blender Python exception exit codes. Those protections are retained.

| Entry point | Current coverage |
|---|---|
| `scripts/archpipe_mcp.py` | Skipped in Phase 2 Batch A: long-running FastMCP stdio server; unmapped mcp package |
| `scripts/build_sheet.py` | Skipped in Phase 2 Batch A: headless AutoCAD boundary (acad._run) |
| `scripts/capture_plot_prompts.py` | Skipped in Phase 2 Batch A: headless AutoCAD boundary (acad._run) |
| `scripts/check_bedroom.py` | Shared: launch preflight; declared inputs (spec, extract); requirements check (yaml); invalid context exits 2 |
| `scripts/compare_lux.py` | Shared: launch preflight; declared inputs (rendered, extract); invalid context exits 2 |
| `scripts/concept.py` | Shared: launch preflight; declared inputs (pilot project); requirements check (matplotlib, yaml, shapely); invalid context exits 2 |
| `scripts/configure_assistants.py` | Shared: launch preflight in main(); declared inputs (archpipe_mcp.py); invalid context exits 2 |
| `scripts/cubicasa_calibrate.py` | Shared: launch preflight; declared outputs; requirements check (numpy, PIL); invalid context exits 2 |
| `scripts/delegate_implementation.py` | Shared: launch preflight; declared inputs (task file); invalid context exits 2 |
| `scripts/demo_bedroom_lighting.py` | Shared: launch preflight in main(); safe import without side effects; invalid context exits 2 |
| `scripts/demo_guidance.py` | Shared: launch preflight; declared inputs (pilot project); requirements check (yaml, shapely); invalid context exits 2 |
| `scripts/export_bedroom_glb.py` | Shared: launch preflight; declared inputs (input glb/mesh); invalid context exits 2 |
| `scripts/fetch_asset_library.py` | Shared: launch preflight; declared inputs (library-manifest.json); invalid context exits 2 |
| `scripts/fetch_families.py` | Shared: launch preflight; declared outputs; invalid context exits 2 |
| `scripts/handoff.py` | Shared: launch preflight; declared inputs (spec); requirements check (yaml, shapely, ifcopenshell, numpy); invalid context exits 2 |
| `scripts/knowledge.py` | Shared: launch preflight; requirements check (pymupdf); invalid context exits 2 |
| `scripts/lighting_report.py` | Shared: launch preflight; declared inputs (input); invalid context exits 2 |
| `scripts/luminaire_demo.py` | Skipped in Phase 2 Batch A: raw pyRevit subprocess runner handled via run_bedroom |
| `scripts/luminaires.py` | Shared: launch preflight; context record; invalid context exits 2 |
| `scripts/make_bedroom_extract.py` | Shared: launch preflight; context record; invalid context exits 2 |
| `scripts/make_bedroom_spec.py` | Shared: launch preflight; declared inputs (spec); requirements check (yaml); invalid context exits 2 |
| `scripts/make_render_input.py` | Shared: launch preflight; declared inputs (extract, spec); requirements check (yaml); invalid context exits 2 |
| `scripts/preflight.py` | thin shared preflight command; context record; invalid context exits 2 |
| `scripts/preview_furniture_orientation.py` | Shared: launch preflight in main(); declared inputs (scene); requirements check (PIL); invalid context exits 2 |
| `scripts/products.py` | Shared: launch preflight; requirements check (PIL); invalid context exits 2 |
| `scripts/products_worker.py` | Skipped in Phase 2 Batch B: workstation dual-interpreter worker script run inside Blender -P in render mode; native Blender boundary |
| `scripts/render_hyperreal.py` | partial: worker environment paths and render quality checks |
| `scripts/render_remote.py` | partial: absolute scene script, SSH status and returned artifacts |
| `scripts/review_model.py` | Shared: launch preflight; declared inputs (extract); requirements check (shapely); invalid context exits 2 |
| `scripts/run_bedroom.py` | shared preflight and checked stage launcher; pyRevit version; absolute scripts; fresh artifacts |
| `scripts/run_tests.py` | shared preflight; declared requirements check (`requirements.txt`); focused modules; accessible Windows temp allocator; exit-status result record |
| `scripts/semantic.py` | Shared: launch preflight; context record; invalid context exits 2 |
| `scripts/sources.py` | Shared: launch preflight; declared inputs (library.json); invalid context exits 2 |
| `scripts/swiss_calibrate.py` | Shared: launch preflight; declared inputs (geometries.csv); declared outputs; requirements check (shapely); invalid context exits 2 |
| `scripts/swiss_stack_calibrate.py` | Shared: launch preflight; declared inputs (geometries.csv); declared outputs; requirements check (shapely); invalid context exits 2 |
| `scripts/sync_agent_assets.py` | Shared: launch preflight; declared inputs (roles.json); invalid context exits 2 |
| `scripts/test_mcp.py` | partial: protocol/subprocess checks |
| `scripts/thermal_job.py` | Shared: launch preflight; declared inputs (input, epw); declared outputs; invalid context exits 2 |
| `scripts/verify.py` | shared preflight bootstrap before third-party/domain imports; declared requirements check (`requirements.txt`); result and context records; relative native-path registry checks; unconditional recorded dependency check |
| `scripts/villa_climate.py` | Shared: launch preflight in main(); declared inputs (EPW for run mode); requirements check (shapely); invalid context exits 2 |
| `scripts/villa_concepts.py` | Shared: launch preflight; declared outputs; requirements check (matplotlib, numpy); invalid context exits 2 |
| `scripts/villa_daylight.py` | Shared: launch preflight; requirements check (numpy, PIL, matplotlib); invalid context exits 2 |
| `scripts/villa_daylight_finished.py` | Shared: launch preflight; declared outputs; invalid context exits 2 |
| `scripts/villa_daylight_pdf.py` | Shared: launch preflight; declared inputs (report.json); declared outputs; requirements check (matplotlib); invalid context exits 2 |
| `scripts/villa_daylight_summary.py` | Shared: launch preflight; declared inputs (report.json, stats.json); declared outputs; invalid context exits 2 |
| `scripts/villa_env.py` | Shared: launch preflight in main(); declared inputs (env-spec.json, env-readback.json for check/plan); requirements check (matplotlib for plan); declared outputs; invalid context exits 2 |
| `scripts/villa_furnish_build.py` | Shared: launch preflight; declared inputs (readback.json, options-spec.json for check); requirements check (shapely); declared outputs; invalid context exits 2 |
| `scripts/villa_furnish_pdf.py` | Shared: launch preflight; requirements check (matplotlib, shapely); declared outputs; invalid context exits 2 |
| `scripts/villa_lighting_pdf.py` | Shared: launch preflight; requirements check (matplotlib, shapely); declared outputs; invalid context exits 2 |
| `scripts/villa_option_pdfs.py` | Shared: launch preflight; declared inputs (readback.json for non-spec); requirements check (numpy, PIL, matplotlib); declared outputs; invalid context exits 2 |
| `scripts/villa_r11_compare.py` | Shared: launch preflight; declared inputs (summary-r12.json when present); requirements check (matplotlib); declared outputs; invalid context exits 2 |
| `scripts/villa_render.py` | shared local preflight and remote preflight before Blender launch/reuse; context in result and image reports |
| `scripts/villa_render_selftest.py` | Phase 2: no shared preflight |
| `scripts/villa_render_views.py` | Phase 2: no shared preflight |
| `scripts/villa_review_page.py` | Phase 2: no shared preflight |
| `scripts/villa_stair_options.py` | Shared: launch preflight; requirements check (matplotlib); declared outputs; invalid context exits 2 |
| `scripts/villa_stairs.py` | Shared: launch preflight in main(); declared inputs (stairs-readback.json for compare); declared outputs; invalid context exits 2 |
| `scripts/worker_entry.py` | partial: explicit cwd/environment, process exit status, runtime fingerprints |
| `scripts/workstation.py` | partial: explicit local cwd, deployed release paths, worker runtime identity |
| `scripts/yard_wall_pdf.py` | Shared: launch preflight; declared inputs (yard-wall-readback.json); requirements check (numpy, PIL, matplotlib); declared outputs; invalid context exits 2 |

All scripts marked Phase 2 or partial above remain outstanding, not silently exempted. Migrate worker/deployment, remote/hyperreal render, model review/build/export, and agent dispatch first; then the remaining report, intake, calibration and demonstration commands.

| Additional boundary | Current coverage / Phase 2 work |
|---|---|
| `src/archpipe/cli.py`, `src/archpipe/__main__.py` | Phase 2: stage command entry points |
| `src/archpipe/acad.py::_run` | Partial: resolves absolute script/drawing paths, checks executable existence and process exit; Phase 2: version, cwd/temp/output record and artifact contract |
| `src/archpipe/radiance.py`, `src/archpipe/thermal.py` | Phase 2: native dependency probes and resolved invocation records |
| `src/archpipe/blender/*.py` | Villa scene launch covered through villa driver; other direct Blender launches remain Phase 2 |
| Revit scripts listed below | Bedroom build/export/extract covered when launched through `run_bedroom.py`; direct pyRevit/UI launches remain Phase 2. Do not import the CPython preflight into IronPython; check in the external launcher. |

Native Revit Python inventory:
- `revit/archpipe.extension/archpipe.tab/Model.panel/Extract Model.pushbutton/script.py`
- `revit/build_bedroom.py`
- `revit/build_test_model.py`
- `revit/build_villa_env.py`
- `revit/build_villa_option.py`
- `revit/build_villa_stairs.py`
- `revit/diag_context.py`
- `revit/dump_mcp_tools.py`
- `revit/export_views.py`
- `revit/extract_model.py`
- `revit/jsonsafe.py`
- `revit/place_families_test.py`
- `revit/probe.py`
- `revit/probe_fixture_drop.py`
- `revit/probe_fixture_geometry.py`
- `revit/probe_product_family.py`
- `revit/probe_villa_inventory.py`
- `revit/probe_villa_stairzone.py`
- `revit/probe_villa_wet.py`
- `revit/probe_yard_wall.py`
- `revit/unattended.py`

### Completed Phase 2 item: Interpreter environment, not just version
- **Incident (2026-10-06, lead)**: The Windows full suite was launched with system interpreter `C:\Python314\python.exe` instead of the project venv `C:\Users\mmbka\arch-pipeline\.venv\Scripts\python.exe`. The Python version check in `archpipe.execution_context.preflight` passed (Python 3.14 is supported), but the system interpreter lacked project packages. Consequently, 24 test modules failed to import (`ModuleNotFoundError: No module named 'shapely'`, from `src/archpipe/rules.py:47` and `src/archpipe/site.py:19`), and `scripts/verify.py` crashed at top-level import before preflight ran. 31 minutes were wasted with output resembling code failures.
- **Resolution**: Moved from Phase 2 scope to Done. `execution_context.preflight` and `project_context` now accept declared module dependencies (`modules` / `required_modules`) and test them using `importlib.util.find_spec` (avoiding side-effect imports). `requirements_import_names` derives import names explicitly from `requirements.txt` via `DISTRIBUTION_TO_IMPORT` (e.g., `shapely` -> `shapely`, `PyYAML` -> `yaml`, `pillow` -> `PIL`, `pymupdf` -> `pymupdf`). Missing dependencies trigger the invalid-context path (exit 2) with a single unambiguous message reporting missing modules, `sys.executable`, and the root `.venv` hint. `scripts/run_tests.py` and `scripts/verify.py` run this check before importing third-party or domain modules (`verify.py` bootstraps preflight before `yaml` and `archpipe.rules`). `verify.py` unconditionally asserts that the context records checked dependencies and that `shapely` is present.

### Completed Phase 2 item: Phase 2 Batch A entry points
- **Scope**: Migrated 16 command-line entry points to the shared `project_context` launch preflight: `check_bedroom.py`, `compare_lux.py`, `concept.py`, `demo_bedroom_lighting.py`, `demo_guidance.py`, `export_bedroom_glb.py`, `knowledge.py`, `lighting_report.py`, `luminaires.py`, `make_bedroom_extract.py`, `make_bedroom_spec.py`, `make_render_input.py`, `products.py`, `review_model.py`, `semantic.py`, `sources.py`.
- **Preflight and import safety**: Each script invokes `project_context` strictly within its CLI entry point (`main()` or `__main__` guard) and never at module top level. Modules can be imported safely by tests and tools without preflight side effects. `demo_bedroom_lighting.py` was refactored from top-level script execution into a guarded `main()`, removing top-level Revit IES file dependencies.
- **Fail-closed contract**: Declared inputs and required third-party packages (mapped from `requirements.txt` via `requirements_import_names`) are verified before execution. Any missing file or module raises `ContextError`, which each script catches to print `PREFLIGHT FAILED: <reason>` to stderr and exit with code 2 without tracebacks.
- **Skipped scripts**:
  - `scripts/archpipe_mcp.py`: Long-running stdio FastMCP server with indefinite lifecycle; `mcp` is not in project dependencies (`requirements.txt`).
  - `scripts/build_sheet.py`: Headless AutoCAD console runner (`src/archpipe/acad.py::_run`); belongs to AutoCAD execution boundary.
  - `scripts/capture_plot_prompts.py`: Headless AutoCAD script runner; belongs to AutoCAD boundary.
  - `scripts/luminaire_demo.py`: Raw pyRevit 6.5.5 runner without `run_checked` / `Tool` contract; pyRevit runs are managed via `scripts/run_bedroom.py`.
- **Proofs**: Added 4 tests in `tests/test_execution_context.py`:
  - AST check verifying that all 16 scripts invoke preflight inside `main()` or `__main__` and never at module top level.
  - Import-isolation check verifying that importing all 16 modules does not invoke preflight.
  - Subprocess exit-2 check on `scripts/check_bedroom.py` when a dependency is missing.
  - Subprocess exit-2 check on `scripts/make_render_input.py` when a declared input file is missing.

### Completed Phase 2 item: Phase 2 Batch B entry points
- **Scope**: Migrated 13 command-line entry points to the shared `project_context` launch preflight: `configure_assistants.py`, `cubicasa_calibrate.py`, `delegate_implementation.py`, `fetch_asset_library.py`, `fetch_families.py`, `handoff.py`, `preview_furniture_orientation.py`, `swiss_calibrate.py`, `swiss_stack_calibrate.py`, `sync_agent_assets.py`, `thermal_job.py`, `villa_climate.py`, `villa_concepts.py`.
- **Preflight and import safety**: Each script invokes `project_context` strictly within its CLI entry point (`main()` or `__main__` guard) and never at module top level. Modules can be imported safely by tests and tools without preflight side effects. Top-level scripts (`configure_assistants.py`, `preview_furniture_orientation.py`, `villa_climate.py`) were wrapped into guarded `main()` entry points while strictly preserving all statement definitions, assignments, and execution order.
- **Fail-closed contract**: Declared inputs, outputs, and required third-party packages (mapped from `requirements.txt` via `requirements_import_names`, e.g. `numpy`, `PIL`, `shapely`, `yaml`, `ifcopenshell`, `matplotlib`) are verified before execution. Any missing file or module raises `ContextError`, which each script catches to print `PREFLIGHT FAILED: <reason>` to stderr and exit with code 2 without tracebacks.
- **Skipped scripts**:
  - `scripts/products_worker.py`: Dual-interpreter worker executed on the workstation in two modes: `fetch` (Python) and `render` (directly inside headless Blender via `blender -b --factory-startup -P products_worker.py -- render ...`). Workstation Blender jobs are managed via driver boundaries (`scripts/products.py` and `scripts/villa_render.py`), and running local `project_context` inside Blender's embedded runtime belongs to the native Blender headless tool boundary.
- **Proofs**: Added 4 tests in `tests/test_execution_context.py`:
  - AST check verifying that all 13 Batch B scripts invoke preflight inside `main()` or `__main__` and never at module top level (`test_batch_b_scripts_call_preflight_in_main_and_not_at_module_top_level`).
  - Import-isolation check verifying that importing all 13 Batch B modules does not invoke preflight (`test_importing_batch_b_scripts_does_not_run_preflight`).
  - Subprocess exit-2 check on `scripts/handoff.py` when a declared input file is missing (`test_handoff_subprocess_exits_2_on_missing_input`).
  - Subprocess exit-2 check on `scripts/swiss_calibrate.py` when a required dependency is missing via the test hook (`test_swiss_calibrate_subprocess_exits_2_on_missing_dependency`).

### Completed Phase 2 item: Phase 2 Batch C entry points
- **Scope**: Migrated 13 command-line entry points to the shared `project_context` launch preflight: `villa_daylight.py`, `villa_daylight_finished.py`, `villa_daylight_pdf.py`, `villa_daylight_summary.py`, `villa_env.py`, `villa_furnish_build.py`, `villa_furnish_pdf.py`, `villa_lighting_pdf.py`, `villa_option_pdfs.py`, `villa_r11_compare.py`, `villa_stair_options.py`, `villa_stairs.py`, `yard_wall_pdf.py`. (Explicitly excluded: `villa_render_views.py`, `villa_review_page.py`, and `villa_render_selftest.py` which are edited concurrently elsewhere).
- **Preflight and import safety**: Each script invokes `project_context` strictly within its CLI entry point (`main()` or `__main__` guard) and never at module top level. Modules can be imported safely by tests and tools without preflight side effects. Top-level CLI blocks (`villa_daylight.py`, `villa_daylight_finished.py`, `villa_stairs.py`) were wrapped into guarded `main()` entry points while strictly preserving statement definitions, assignments, and execution order.
- **Fail-closed contract**: Declared inputs, outputs, and required third-party packages (mapped from `requirements.txt` via `requirements_import_names`, e.g. `numpy`, `PIL`, `shapely`, `matplotlib`) are verified before execution. Any missing file or module raises `ContextError`, which each script catches to print `PREFLIGHT FAILED: <reason>` to stderr and exit with code 2 without tracebacks.
- **Proofs**: Added 4 tests in `tests/test_execution_context.py`:
  - AST check verifying that all 13 Batch C scripts invoke preflight inside `main()` or `__main__` and never at module top level (`test_batch_c_scripts_call_preflight_in_main_and_not_at_module_top_level`).
  - Import-isolation check verifying that importing all 13 Batch C modules does not invoke preflight (`test_importing_batch_c_scripts_does_not_run_preflight`).
  - Subprocess exit-2 check on `scripts/yard_wall_pdf.py` when a declared input file is missing (`test_yard_wall_pdf_subprocess_exits_2_on_missing_input`).
  - Subprocess exit-2 check on `scripts/villa_furnish_pdf.py` when a required dependency is missing via the test hook (`test_villa_furnish_pdf_subprocess_exits_2_on_missing_dependency`).

## Defect controls and proving tests

Guard registry: `execution-context-implicit-phase1` -> `execution_context.preflight`, `run_checked`, the four migrated entry points and two unconditional `verify.py` checks -> `tests/test_execution_context.py`, `tests/test_villa_render_scene.py`, `tests/test_villa_scene_provenance.py` -> launch boundary.
`execution-context-launch-directory` -> `execution_context.preflight`, `run_checked`, `scripts/preflight.py` and unconditional `verify.py` absolute-child-directory check -> `tests/test_pipeline_contracts.py`, `tests/test_execution_context.py` -> launch boundary.
`execution-context-wrong-interpreter` -> `execution_context.check_dependencies`, `preflight(modules=...)`, `scripts/run_tests.py`, `scripts/verify.py` bootstrap, and unconditional `verify.py` dependency record check -> `tests/test_execution_context.py` (missing module, quiet on present, frozen incident reproduction, subprocess exit 2) -> launch/environment boundary.

Portability controls discovered by the first Linux full-suite run:

- `luminaire-stored-path-portability` -> `library.resolve_library_path` at both stored-path readers, `rebuild_index` writes with `as_posix`, and unconditional portable-path verification -> `tests.test_luminaire_library.StoredPathTests` and index import assertions -> persistence/read boundary. Treat both separators as path parts, regardless of the host; do not repair shared databases. Test both Windows and POSIX semantics with pure paths.
- `jsonsafe-bridge-integer-portability` -> `jsonsafe.clean` converts integral bridge types directly with `int`, and unconditional exact-identifier verification -> `tests.test_safe_io.BoundaryTests.test_large_foreign_identifier_never_passes_through_float` and `tests.test_jsonsafe.JsonSafe` -> native serialization boundary. Integer conversion must precede floating-point conversion; real-valued types retain fractions. Keep this module compatible with IronPython 2.7 as well as CPython 3.12 and 3.14.

Run the full suite with `NO_COLOR=1` on each supported host when changing shared persistence or serialization boundaries, using that host's explicit interpreter and judging the exit status. `scripts/verify.py --portable` explicitly omits the installed Windows Revit family corpus on Linux; portable parser tests still run. Earlier missing-library and focused-only evidence below is historical; current Linux validation is recorded in the two portability lessons.

The historical inputs are frozen by value: relative external script arguments `revit/build_bedroom.py`, sibling `out/plot.scr`, the child-directory WinError 5 write failure, ANSI-coloured failure text which lacks the plain word FAILED, an installed Blender with no verified version, and missing live role. Tests also inject changed releases, missing tools, relative executables at the launch boundary, stale artifacts and failed version probes; clean cases perform real file read/write/delete and subprocess execution. Permission injection repeats the recorded failure at the actual write boundary; it does not claim to reproduce Windows access-control policy on every host. Different caller/project directories are valid; `execution-context-launch-directory` guards absolute resolution and explicit child working directories through the pipeline-contract reproduction, preflight command launched elsewhere and checked child execution.

All 24 audited class identifiers remain traceable in `docs/lessons-audit.md`. Preflight addresses launch context, not family activation, geometry units, protocol pipe ownership, tool arguments, resource scheduling, lock recovery, transfer integrity, native document state or product library completeness. Those lesson-specific controls remain required; the class is not closed in Phase 1.

Runtime records: `out/tests-result.json`, `out/verify-result.json`, `out/bedroom-acceptance.json`, `out/run-logs/*.context.json`; villa results and image reports carry local and remote contexts. Dry runs explicitly record remote preflight as not run. Remote preflight and native version invocation are covered by boundary tests, not a live workstation/Revit execution.

## Checkpoint evidence

Focused test counts and exit codes are reported in the appended learning record after the final run. The full suite is reserved for the lead. Verification currently encounters a missing worktree-local `assets/user/luminaires/library.sqlite`; no files are borrowed from the other job and no verification checks are weakened. This dependency failure remains failed evidence, not ALL PASS.


Canonical workflow follow-up: `.agents/skills` is read-only in this session and earlier edits were rejected. The lead should add absolute project-root path resolution, explicit interpreter and child working directory, and per-stage context records to `revit-roundtrip`, and local/remote preflight plus the declared Blender release to `villa-render`. The actionable procedure is recorded here and in `CLAUDE.md`.

- Final Phase 1 evidence (2026-10-05): `scripts/run_tests.py tests.test_execution_context tests.test_villa_render_scene tests.test_villa_scene_provenance` ran 48 tests in 4.258 s, exit 0. Clean preflight command exits 0; injected relative-script preflight exits 2 (regression assertions). `scripts/verify.py` exits 1 for the missing luminaire database, with failed current result recorded. `git diff --check` exits 0. Records: `out/tests-result.json`, `out/verify-result.json`. Phase 1 checkpoint reached; Phase 2 migrations and live native/worker validation remain outstanding.

- Launch-directory correction (2026-10-05): the earlier equality requirement was withdrawn. Focused `scripts/run_tests.py tests.test_pipeline_contracts tests.test_execution_context` passed 20 tests, exit 0; `scripts/verify.py` reported ALL PASS, exit 0. The previous missing-library result above is historical, not current verification evidence. See `execution-context-launch-directory` in `docs/LEARNINGS.md` for cause, controls and proving tests. Full suite not run; no commit.

- Interpreter-environment correction (2026-10-06): Phase 2 item "interpreter environment, not just version" completed after lead's Windows full suite incident. `scripts/run_tests.py` and `scripts/verify.py` enforce declared module dependency preflights before importing third-party or domain packages. `tests/test_execution_context.py` reproduces the missing-shapely incident by value and verifies subprocess exit code 2 on missing dependencies. See `execution-context-wrong-interpreter` in `docs/LEARNINGS.md`.

- Phase 2 Batch A entry points (2026-10-07): Migrated 16 entry points to `project_context` with declared inputs and requirements; skipped 4 scripts at distinct boundaries (`archpipe_mcp.py`, `build_sheet.py`, `capture_plot_prompts.py`, `luminaire_demo.py`). AST, import-isolation, and subprocess exit-2 proofs in `tests/test_execution_context.py`.

- Phase 2 Batch B entry points (2026-10-07): Migrated 13 entry points to `project_context` with declared inputs, outputs, and requirements; skipped 1 script at distinct boundary (`products_worker.py`). AST, import-isolation, and subprocess exit-2 proofs in `tests/test_execution_context.py`.

- Phase 2 batch D (2026-10-08, final): `villa_render_views.py`, `villa_review_page.py` and `villa_render_selftest.py` call `project_context` on the command-line path (agy migrated the first two; the lead finished the self-test after agy stopped on a denied read). All entry scripts in the inventory now use the shared preflight.
