# Execution context: Phase 1 checkpoint

Inventory dated 2026-10-05. Shared means `archpipe.execution_context`; partial means an existing operation-specific check, not a complete preflight. Every other Python script below still needs migration in Phase 2. No native model or workstation render was run for this change.

## Application programming interface

`preflight(root, scripts, inputs, output, temp, tools, env, required_roles, available_roles, python_version)` requires an absolute existing project root and returns a JSON-safe context. Relative script, tool, input, output and temp paths resolve from that root, independently of the caller's directory. Inputs and scripts must exist. The record distinguishes `launch_directory` (caller) from `working_directory` (explicit child directory). It checks the active Python interpreter (supported releases 3.11 through 3.14; optional exact pin), and write/read/delete access in newly created child directories. It constructs `NO_COLOR=1`, absolute `PYTHONPATH`, `TMP`, `TEMP`, and `TMPDIR`. Environment records contain only these controlled variables, never credentials.

`Tool(name, path, expected_version, version_args)` describes an executable, exact release and version-probe arguments. Preflight resolves tool paths from the root; direct `resolve_tool` calls require absolute paths. Version probes use the explicit project working directory, have a 30-second timeout, require exit zero and the first reported numerical version to equal the pin. The bedroom runner pins pyRevit 6.5.5; the remote villa driver pins Blender 4.5.14, matching the installer default. AutoCAD Core Console and Codex callers must supply their verified release and version-probe arguments; they have no guessed default. Tools irrelevant to a run are not required.

`project_context(root, script, name, tools)` configures the current process environment/temp settings and writes `out/<name>-execution-context.json`; it does not change the caller's directory. In-process test fixtures must restore those process settings before deleting their temporary project. `run_checked(argv, context, scripts, record, env, expected, timeout)` requires a previously version-checked executable and absolute script arguments verbatim in the command, explicitly sets the checked child directory/environment, records the command, exit status and logs, and optionally demands a newly written artifact. Record and expected-artifact paths resolve from the context's root. Native callers must supply the promised artifact. `write_record(context, path)` requires an absolute resolved record path.

`scripts/preflight.py` is the thin command-line interface: `--root`, repeated `--script` and `--input`, `--out`, `--temp`, `--record`, and repeated `--tool NAME PATH EXACT_VERSION`. All relative paths, including the record, resolve from the absolute project root. It exits 0 for a valid recorded context and 2 for invalid context. Passing relative scripts to preflight is allowed; passing them to an external launcher is rejected. The test runner exits 0 for successful tests, 1 for failed tests/imports, and 2 for preflight failure; it accepts focused module names. Verification exits 1 for check/dependency failures and 2 for preflight failures. Native stage command failures remain failed acceptance evidence.

Role checks require explicit live-session availability, not files in `agents/roles.json`. This boundary cannot alter Codex approvals or discover session permissions/roles; writable probes expose unusable permissions and explicitly required absent roles fail closed. Actual agent dispatch migration remains Phase 2.

## Entry-point inventory and Phase 2 list

Before Phase 1, none of these entry points used a complete shared context. The test runner already created accessible sandbox temp directories; verification used `Path.mkdir`; the bedroom runner used absolute Revit scripts, an explicit cwd, exit status and fresh artifacts; villa rendering used absolute remote scripts and Blender Python exception exit codes. Those protections are retained.

| Entry point | Current coverage |
|---|---|
| `scripts/archpipe_mcp.py` | Phase 2: no shared preflight |
| `scripts/build_sheet.py` | Phase 2: no shared preflight |
| `scripts/capture_plot_prompts.py` | Phase 2: no shared preflight |
| `scripts/check_bedroom.py` | Phase 2: no shared preflight |
| `scripts/compare_lux.py` | Phase 2: no shared preflight |
| `scripts/concept.py` | Phase 2: no shared preflight |
| `scripts/configure_assistants.py` | Phase 2: no shared preflight |
| `scripts/cubicasa_calibrate.py` | Phase 2: no shared preflight |
| `scripts/delegate_implementation.py` | Phase 2: no shared preflight |
| `scripts/demo_bedroom_lighting.py` | Phase 2: no shared preflight |
| `scripts/demo_guidance.py` | Phase 2: no shared preflight |
| `scripts/export_bedroom_glb.py` | Phase 2: no shared preflight |
| `scripts/fetch_asset_library.py` | Phase 2: no shared preflight |
| `scripts/fetch_families.py` | Phase 2: no shared preflight |
| `scripts/handoff.py` | Phase 2: no shared preflight |
| `scripts/knowledge.py` | Phase 2: no shared preflight |
| `scripts/lighting_report.py` | Phase 2: no shared preflight |
| `scripts/luminaire_demo.py` | Phase 2: no shared preflight |
| `scripts/luminaires.py` | Phase 2: no shared preflight |
| `scripts/make_bedroom_extract.py` | Phase 2: no shared preflight |
| `scripts/make_bedroom_spec.py` | Phase 2: no shared preflight |
| `scripts/make_render_input.py` | Phase 2: no shared preflight |
| `scripts/preflight.py` | thin shared preflight command; context record; invalid context exits 2 |
| `scripts/preview_furniture_orientation.py` | Phase 2: no shared preflight |
| `scripts/products.py` | Phase 2: no shared preflight |
| `scripts/products_worker.py` | Phase 2: no shared preflight |
| `scripts/render_hyperreal.py` | partial: worker environment paths and render quality checks |
| `scripts/render_remote.py` | partial: absolute scene script, SSH status and returned artifacts |
| `scripts/review_model.py` | Phase 2: no shared preflight |
| `scripts/run_bedroom.py` | shared preflight and checked stage launcher; pyRevit version; absolute scripts; fresh artifacts |
| `scripts/run_tests.py` | shared preflight; focused modules; accessible Windows temp allocator; exit-status result record |
| `scripts/semantic.py` | Phase 2: no shared preflight |
| `scripts/sources.py` | Phase 2: no shared preflight |
| `scripts/swiss_calibrate.py` | Phase 2: no shared preflight |
| `scripts/swiss_stack_calibrate.py` | Phase 2: no shared preflight |
| `scripts/sync_agent_assets.py` | Phase 2: no shared preflight |
| `scripts/test_mcp.py` | partial: protocol/subprocess checks |
| `scripts/thermal_job.py` | Phase 2: no shared preflight |
| `scripts/verify.py` | shared preflight; result and context records; relative native-path registry checks |
| `scripts/villa_climate.py` | Phase 2: no shared preflight |
| `scripts/villa_concepts.py` | Phase 2: no shared preflight |
| `scripts/villa_daylight.py` | Phase 2: no shared preflight |
| `scripts/villa_daylight_finished.py` | Phase 2: no shared preflight |
| `scripts/villa_daylight_pdf.py` | Phase 2: no shared preflight |
| `scripts/villa_daylight_summary.py` | Phase 2: no shared preflight |
| `scripts/villa_env.py` | Phase 2: no shared preflight |
| `scripts/villa_furnish_build.py` | Phase 2: no shared preflight |
| `scripts/villa_furnish_pdf.py` | Phase 2: no shared preflight |
| `scripts/villa_lighting_pdf.py` | Phase 2: no shared preflight |
| `scripts/villa_option_pdfs.py` | Phase 2: no shared preflight |
| `scripts/villa_r11_compare.py` | Phase 2: no shared preflight |
| `scripts/villa_render.py` | shared local preflight and remote preflight before Blender launch/reuse; context in result and image reports |
| `scripts/villa_render_selftest.py` | Phase 2: no shared preflight |
| `scripts/villa_render_views.py` | Phase 2: no shared preflight |
| `scripts/villa_review_page.py` | Phase 2: no shared preflight |
| `scripts/villa_stair_options.py` | Phase 2: no shared preflight |
| `scripts/villa_stairs.py` | Phase 2: no shared preflight |
| `scripts/worker_entry.py` | partial: explicit cwd/environment, process exit status, runtime fingerprints |
| `scripts/workstation.py` | partial: explicit local cwd, deployed release paths, worker runtime identity |
| `scripts/yard_wall_pdf.py` | Phase 2: no shared preflight |

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

## Defect controls and proving tests

Guard registry: `execution-context-implicit-phase1` -> `execution_context.preflight`, `run_checked`, the four migrated entry points and two unconditional `verify.py` checks -> `tests/test_execution_context.py`, `tests/test_villa_render_scene.py`, `tests/test_villa_scene_provenance.py` -> launch boundary.

The historical inputs are frozen by value: relative external script arguments `revit/build_bedroom.py`, sibling `out/plot.scr`, the child-directory WinError 5 write failure, ANSI-coloured failure text which lacks the plain word FAILED, an installed Blender with no verified version, and missing live role. Tests also inject changed releases, missing tools, relative executables at the launch boundary, stale artifacts and failed version probes; clean cases perform real file read/write/delete and subprocess execution. Permission injection repeats the recorded failure at the actual write boundary; it does not claim to reproduce Windows access-control policy on every host. Different caller/project directories are valid; `execution-context-launch-directory` guards absolute resolution and explicit child working directories through the pipeline-contract reproduction, preflight command launched elsewhere and checked child execution.

All 24 audited class identifiers remain traceable in `docs/lessons-audit.md`. Preflight addresses launch context, not family activation, geometry units, protocol pipe ownership, tool arguments, resource scheduling, lock recovery, transfer integrity, native document state or product library completeness. Those lesson-specific controls remain required; the class is not closed in Phase 1.

Runtime records: `out/tests-result.json`, `out/verify-result.json`, `out/bedroom-acceptance.json`, `out/run-logs/*.context.json`; villa results and image reports carry local and remote contexts. Dry runs explicitly record remote preflight as not run. Remote preflight and native version invocation are covered by boundary tests, not a live workstation/Revit execution.

## Checkpoint evidence

Focused test counts and exit codes are reported in the appended learning record after the final run. The full suite is reserved for the lead. Verification currently encounters a missing worktree-local `assets/user/luminaires/library.sqlite`; no files are borrowed from the other job and no verification checks are weakened. This dependency failure remains failed evidence, not ALL PASS.


Canonical workflow follow-up: `.agents/skills` is read-only in this session and earlier edits were rejected. The lead should add absolute project-root path resolution, explicit interpreter and child working directory, and per-stage context records to `revit-roundtrip`, and local/remote preflight plus the declared Blender release to `villa-render`. The actionable procedure is recorded here and in `CLAUDE.md`.

- Final Phase 1 evidence (2026-10-05): `scripts/run_tests.py tests.test_execution_context tests.test_villa_render_scene tests.test_villa_scene_provenance` ran 48 tests in 4.258 s, exit 0. Clean preflight command exits 0; injected relative-script preflight exits 2 (regression assertions). `scripts/verify.py` exits 1 for the missing luminaire database, with failed current result recorded. `git diff --check` exits 0. Records: `out/tests-result.json`, `out/verify-result.json`. Phase 1 checkpoint reached; Phase 2 migrations and live native/worker validation remain outstanding.

- Launch-directory correction (2026-10-05): the earlier equality requirement was withdrawn. Focused `scripts/run_tests.py tests.test_pipeline_contracts tests.test_execution_context` passed 20 tests, exit 0; `scripts/verify.py` reported ALL PASS, exit 0. The previous missing-library result above is historical, not current verification evidence. See `execution-context-launch-directory` in `docs/LEARNINGS.md` for cause, controls and proving tests. Full suite not run; no commit.
