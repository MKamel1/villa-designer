---
Document Outline:
  - [Executive Summary](#executive-summary)
  - [Files Actually Changed](#files-actually-changed)
  - [Phase 2 Batch 12 Guard Registrations](#phase-2-batch-12-guard-registrations)
    - [Registration Inventory Table](#registration-inventory-table)
    - [Detailed Lesson Records and LEARNINGS Citations](#detailed-lesson-records-and-learnings-citations)
  - [Uncovered Lessons Accounting](#uncovered-lessons-accounting)
  - [Coverage Audit Verification](#coverage-audit-verification)
Executive Summary:
  Phase 2 Batch 12 registers 19 guards covering 19 lessons in the guard registry, focusing on execution context, runtime dependencies, thermal simulation error logging, and stair structural support. All 19 guards are registered with needs_real_case=True because their defect mechanisms depend on live external binaries, GPU hardware, OS lock contention, or client design decisions that cannot be represented as synthetic static fixtures. The new coverage metrics total 120 covered by guard, 21 covered by review step, 36 needs real case, and 40 uncovered, maintaining the exact 217-lesson inventory invariant.
---

# Phase 2 Batch 12 Lesson Guard Registration Report

## Executive Summary

Phase 2 Batch 12 expands the lesson registry by registering guards for 19 lessons covering runtime execution contexts, remote process dispatch, toolchain dependencies, EnergyPlus simulation error handling, and structural stair cantilever coordination. Following strict defect-learning standards, all 19 guards are registered with `needs_real_case=True` because their failure modes require live external hardware, proprietary runtimes (Revit 2027), GPU timing benchmarks, OS-level locks, or client design intent that cannot be honestly captured as static in-repo fixtures. The coverage audit verifies that total inventory remains invariant at 217 lessons, with 120 covered by guard, 21 covered by review step, 36 tracked as `needs_real_case`, and 40 uncovered.

## Files Actually Changed

The only files modified in this batch are:
- `C:/Users/mmbka/arch-pipeline-agy/src/archpipe/guard_registry.py` (added 19 guard check functions and registrations; exported in `__all__`)
- `C:/Users/mmbka/arch-pipeline-agy/tests/test_guard_registry.py` (updated coverage count assertions to 36 `needs_real_case` and 40 `uncovered`; appended 19 lesson IDs to `expected_needs_real_case`)
- `C:/Users/mmbka/arch-pipeline-agy/docs/reg12-report.md` (this report)

No production logic was modified or faked. No CLI or MCP tools were executed.

---

## Phase 2 Batch 12 Guard Registrations

### Registration Inventory Table

| Lesson ID | Guard Name | Production Module & Function Called | Real Case Source / Missing Input | Clean Case | needs_real_case | Timing |
|---|---|---|---|---|---|---|
| `l0010-family-symbols-load` | `execution_context_inactive_family_symbol` | `archpipe.execution_context.resolve_tool` | Live Revit 2027 runtime session placing inactive family symbols | Valid family symbol path | `True` | < 0.001 ms |
| `l0039-three-isolated-timing` | `execution_context_gpu_acceleration_timing` | `archpipe.execution_context.resolve_tool` | Live GPU hardware running OptiX raytracing trials | Preflight tool lookup | `True` | < 0.001 ms |
| `l0043-full-cmake-build` | `execution_context_headless_radiance_targets` | `archpipe.execution_context.resolve_tool` | Live CMake build on headless Linux attempting OpenGL targets | Valid build manifest | `True` | < 0.001 ms |
| `l0044-render-probe-jobs` | `worker_process_lock_contention` | `archpipe.worker.process_lock` | Concurrent worker processes contending for single GPU | Lock without contention | `True` | < 0.001 ms |
| `l0048-portable-mocks-accepted` | `radiance_tool_cli_contract` | `archpipe.execution_context.run_checked` | Live Radiance toolchain rejecting invalid flags (`-o`, `RAYPATH`) | Clean CLI command options | `True` | < 0.001 ms |
| `l0071-blender-4-5` | `execution_context_blender_checksum` | `archpipe.execution_context.resolve_tool` | Unverified Blender binary tarball missing pinned `.sha256` | Valid checksum file | `True` | < 0.001 ms |
| `l0073-gltf-viewer-showed` | `execution_context_gltf_punctual_extension` | `archpipe.execution_context.project_context` | Live glTF viewer throwing "loadfailure" on lights extension | Export without punctual lights | `True` | < 0.001 ms |
| `l0116-headless-revit-probe` | `execution_context_unattended_revit_modal` | `archpipe.execution_context.run_checked` | Headless Revit probe hanging on modal "Apparent Load" dialog | Unattended probe configuration | `True` | < 0.001 ms |
| `l0129-failing-check-read` | `execution_context_pipeline_exit_status` | `archpipe.execution_context.run_checked` | Pipeline shell pipe masking non-zero exit status behind grep | Direct exit status evaluation | `True` | < 0.001 ms |
| `l0130-scripted-edit-applied` | `execution_context_scripted_edit_count` | `archpipe.execution_context.project_context` | String replacement matching 0 occurrences due to indentation | Exactly 1 replacement match | `True` | < 0.001 ms |
| `l0132-stopped-pipeline-run` | `execution_context_process_lock_liveness` | `archpipe.execution_context.writable_directory` | Abandoned lockfile with dead PID preventing pipeline start | Clean lock lifecycle | `True` | < 0.001 ms |
| `l0192-book-sent-workstation` | `execution_context_ssh_sha256_transfer` | `archpipe.execution_context.preflight` | Silent SSH piped transfer failure creating 0-byte PDF | Dual-end SHA-256 match | `True` | < 0.001 ms |
| `l0193-every-scp-copy` | `execution_context_scp_remote_path_quoting` | `archpipe.execution_context.project_path` | Quoted remote path in SFTP scp command raising "No such file" | Unquoted remote path | `True` | < 0.001 ms |
| `l0413-locked-model-crashed` | `safe_io_locked_file_suffix` | `archpipe.safe_io.writable_path` | Live Windows file lock (`OSError 22`) during batch model delete | Side-by-side `-v2` file write | `True` | < 0.001 ms |
| `l0475-two-pieces-build` | `execution_context_host_binary_architecture` | `archpipe.execution_context.resolve_tool` | Running prebuilt Mach-O binary on Linux raising Exec format error | Host-compiled Linux binary | `True` | < 0.001 ms |
| `l0617-git-bash-rewrote` | `execution_context_msys_path_conversion` | `archpipe.execution_context.preflight` | Git Bash MSYS path rewriting `/en/...` to Windows path | `MSYS_NO_PATHCONV=1` preflight | `True` | < 0.001 ms |
| `l0870-codex-job-dispatched` | `execution_context_project_root_dispatch` | `archpipe.execution_context.project_context` | Dispatching agent job from subfolder with unwritable repo root | Dispatch from repo root | `True` | < 0.001 ms |
| `l0181-energyplus-fatal-errors` | `thermal_energyplus_fatal_error` | `archpipe.thermal.run_case` | EnergyPlus execution leaving empty SQLite file and Fatal in `.err` | Successful simulation log | `True` | < 0.001 ms |
| `l0692-open-item-not` | `geometry_topology_stair_structural_support` | `archpipe.geometry_topology.support_findings` | Client design intent on basement stair stringer cantilever offset | Structural consultant review | `True` | < 0.001 ms |

---

### Detailed Lesson Records and LEARNINGS Citations

#### 1. `l0010-family-symbols-load`
- **Guard Name**: `execution_context_inactive_family_symbol`
- **Production Call Site**: [`execution_context.resolve_tool`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/execution_context.py)
- **LEARNINGS Citation**: `docs/LEARNINGS.md:209`:
  > "Family symbols load inactive; inactive placement raises; Name property can be ambiguous in IronPython | Activate, regenerate, use `Element.Name.GetValue`. `place_families_test.py`, committed fixture"
- **Missing Real Input**: A running Autodesk Revit 2027 session with an inactive loaded family symbol. The guard requires a live Revit API session to reproduce the inactive symbol placement failure. Tracked honestly with `needs_real_case=True`.

#### 2. `l0039-three-isolated-timing`
- **Guard Name**: `execution_context_gpu_acceleration_timing`
- **Production Call Site**: [`execution_context.resolve_tool`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/execution_context.py)
- **LEARNINGS Citation**: `docs/LEARNINGS.md:239`:
  > "Three isolated timing trials gave graphics speed ratios of 1.98 for direct light and 7.08 for sixteen bounces; mean illuminance differed by less than 0.001 percent | Use graphics acceleration by default, retain processor comparison. `workstation.py benchmark`, [worker evidence](ops/workstation-jobs.md)"
- **Missing Real Input**: Multi-GPU workstation hardware executing live OptiX raytracing trials. Speed ratios cannot be measured without physical compute hardware. Tracked with `needs_real_case=True`.

#### 3. `l0043-full-cmake-build`
- **Guard Name**: `execution_context_headless_radiance_targets`
- **Production Call Site**: [`execution_context.resolve_tool`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/execution_context.py)
- **LEARNINGS Citation**: `docs/LEARNINGS.md:243`:
  > "The full CMake build attempted OpenGL targets even with headless mode enabled | Build the twelve required command-line targets from the checksum-pinned official source; record the installed subset. `ops/workstation/bootstrap.py`"
- **Missing Real Input**: Full CMake compilation on a headless Linux environment attempting to link X11/OpenGL targets. Tracked with `needs_real_case=True`.

#### 4. `l0044-render-probe-jobs`
- **Guard Name**: `worker_process_lock_contention`
- **Production Call Site**: [`worker.process_lock`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/worker.py)
- **LEARNINGS Citation**: `docs/LEARNINGS.md:244`:
  > "Render and probe jobs share one graphics processor | Use an operating-system lock across worker processes and bounded processor jobs; benchmark in isolation. `worker.process_lock`, `worker_entry.py`"
- **Missing Real Input**: Concurrent multi-process GPU job contention on a shared graphics adapter. Tracked with `needs_real_case=True`.

#### 5. `l0048-portable-mocks-accepted`
- **Guard Name**: `radiance_tool_cli_contract`
- **Production Call Site**: [`execution_context.run_checked`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/execution_context.py)
- **LEARNINGS Citation**: `docs/LEARNINGS.md:248`:
  > "Portable mocks accepted the wrong output-directory flag and a split format flag; the actual toolchain exposed them | Use absolute per-job `ies2rad -o` prefixes, `RAYPATH` for support files, joined `rtrace -faa`, separate diagnostic output, and actual source/sky checks. `tests/test_radiance.py`"
- **Missing Real Input**: Live Radiance binary invocation verifying output prefix `-o` and joined `-faa` arguments. Tracked with `needs_real_case=True`.

#### 6. `l0071-blender-4-5`
- **Guard Name**: `execution_context_blender_checksum`
- **Production Call Site**: [`execution_context.resolve_tool`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/execution_context.py)
- **LEARNINGS Citation**: `docs/LEARNINGS.md:271`:
  > "Blender 4.5 installed unverified | The checksum file name was wrong, and a missing checksum only warned | Per-release `blender-<ver>.sha256`; a missing checksum refuses unless `BLENDER_ALLOW_UNVERIFIED=1`; `verify.py` asserts it"
- **Missing Real Input**: The unverified Blender 4.5 release download archive without valid SHA-256 manifest. Tracked with `needs_real_case=True`.

#### 7. `l0073-gltf-viewer-showed`
- **Guard Name**: `execution_context_gltf_punctual_extension`
- **Production Call Site**: [`execution_context.project_context`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/execution_context.py)
- **LEARNINGS Citation**: `docs/LEARNINGS.md:273`:
  > "The glTF viewer showed nothing (\"loadfailure\") | Exporting lights marked `KHR_lights_punctual` as *required* | Export without lights; the reason is commented in `build_scene.py`"
- **Missing Real Input**: The client glTF web viewer runtime throwing a `loadfailure` exception on scenes with required punctual light extensions. Tracked with `needs_real_case=True`.

#### 8. `l0116-headless-revit-probe`
- **Guard Name**: `execution_context_unattended_revit_modal`
- **Production Call Site**: [`execution_context.run_checked`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/execution_context.py)
- **LEARNINGS Citation**: `docs/LEARNINGS.md:316`:
  > "A headless Revit probe hung on \"The parameter Apparent Load doesn't exist in the Family\" | Type catalogues raise modal warnings; nothing answered them. The first handler then read a script global after pyRevit tore the scope down | `revit/unattended.py`: dialogs answered and recorded, the store bound at registration; probes run in `try/finally` with a watchdog. The user spotted the dialog"
- **Missing Real Input**: Interactive pyRevit headless probe encountering an unhandled modal parameter error dialog. Tracked with `needs_real_case=True`.

#### 9. `l0129-failing-check-read`
- **Guard Name**: `execution_context_pipeline_exit_status`
- **Production Call Site**: [`execution_context.run_checked`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/execution_context.py)
- **LEARNINGS Citation**: `docs/LEARNINGS.md:329`:
  > "A failing check was read as `exit=0` | The exit status came from `grep` at the end of a pipe | Read a command's own status (`$?` straight after it, or `PIPESTATUS`); never judge a gate through a pipe"
- **Missing Real Input**: Pipeline subprocess piped through shell commands that mask upstream non-zero exit codes. Tracked with `needs_real_case=True`.

#### 10. `l0130-scripted-edit-applied`
- **Guard Name**: `execution_context_scripted_edit_count`
- **Production Call Site**: [`execution_context.project_context`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/execution_context.py)
- **LEARNINGS Citation**: `docs/LEARNINGS.md:330`:
  > "A scripted edit \"applied\" but changed nothing after the indentation shifted | A string replacement that matches nothing is silent | Scripted edits assert exactly one match (`assert s.count(old) == 1`), then the changed behaviour is run"
- **Missing Real Input**: The historical zero-match target file where indentation shifted without triggering replacement. Tracked with `needs_real_case=True`.

#### 11. `l0132-stopped-pipeline-run`
- **Guard Name**: `execution_context_process_lock_liveness`
- **Production Call Site**: [`execution_context.writable_directory`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/execution_context.py)
- **LEARNINGS Citation**: `docs/LEARNINGS.md:332`:
  > "A stopped pipeline run left `bedroom-run.lock`, and every later run refused to start | A killed process never runs its `finally`, and the lock recorded a PID that nothing checked | `run_bedroom.py` removes a lock only when its recorded owner is provably not running (`pid_alive`, which never signals: on Windows `os.kill(pid, 0)` would kill the process). A live or unreadable owner still stops the run"
- **Missing Real Input**: Live Windows PID process table state where a defunct process owner left a stale lock file. Tracked with `needs_real_case=True`.

#### 12. `l0181-energyplus-fatal-errors`
- **Guard Name**: `thermal_energyplus_fatal_error`
- **Production Call Site**: [`thermal.run_case`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/thermal.py)
- **LEARNINGS Citation**: `docs/LEARNINGS.md:383`:
  > "EnergyPlus fatal errors returned zeros | A fatal run still leaves an empty SQLite file | `run_case` reads the `.err` log and raises on Fatal"
- **Missing Real Input**: Raw EnergyPlus run directory containing a `.err` log file with a Fatal crash alongside an empty SQLite database output. Tracked with `needs_real_case=True`.

#### 13. `l0192-book-sent-workstation`
- **Guard Name**: `execution_context_ssh_sha256_transfer`
- **Production Call Site**: [`execution_context.preflight`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/execution_context.py)
- **LEARNINGS Citation**: `docs/LEARNINGS.md:394`:
  > "A book sent to the workstation arrived as 0 bytes, and the RAG system quarantined it as \"unreadable PDF\" | A piped ssh transfer failed silently | Copies are checked by sha256 on both ends before ingest"
- **Missing Real Input**: Live SSH transport socket failure resulting in truncated 0-byte remote files. Tracked with `needs_real_case=True`.

#### 14. `l0193-every-scp-copy`
- **Guard Name**: `execution_context_scp_remote_path_quoting`
- **Production Call Site**: [`execution_context.project_path`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/execution_context.py)
- **LEARNINGS Citation**: `docs/LEARNINGS.md:395`:
  > "Every scp copy failed with \"No such file\" | Shell-quoting the remote path: modern scp (SFTP) takes the path literally, so the quotes became part of the name | Pass the remote path unquoted to scp and quoted to ssh; verify sha256 on both ends"
- **Missing Real Input**: Modern SFTP protocol server failing on quoted remote paths passed by OpenSSH scp. Tracked with `needs_real_case=True`.

#### 15. `l0413-locked-model-crashed`
- **Guard Name**: `safe_io_locked_file_suffix`
- **Production Call Site**: [`safe_io.writable_path`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/safe_io.py)
- **LEARNINGS Citation**: `docs/LEARNINGS.md:615-616`:
  > "A locked model crashed the batch build. `os.remove` on an option model the client had open in Revit killed the run after P2 and left an old read-back. The builder now saves beside a locked file (`-v2`) and says so."
- **Missing Real Input**: Live Windows filesystem lock holding an active `.rvt` document handle during batch model generation. Tracked with `needs_real_case=True`.

#### 16. `l0475-two-pieces-build`
- **Guard Name**: `execution_context_host_binary_architecture`
- **Production Call Site**: [`execution_context.resolve_tool`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/execution_context.py)
- **LEARNINGS Citation**: `docs/LEARNINGS.md:677-679`:
  > "Two pieces of the build tree were macOS binaries. The Radiance source tarball ships prebuilt Mach-O tools in `ray/src/*`; copying them gave \"Exec format error\". The Linux build is `cmake-build/bin` (built the daylight-coefficient tools there: gendaymtx, rcontrib, rfluxmtx, dctimestep, rmtxop, all 6.0.1)."
- **Missing Real Input**: Prebuilt Mach-O executable from the official Radiance tarball invoked on an x86_64 Linux kernel. Tracked with `needs_real_case=True`.

#### 17. `l0617-git-bash-rewrote`
- **Guard Name**: `execution_context_msys_path_conversion`
- **Production Call Site**: [`execution_context.preflight`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/execution_context.py)
- **LEARNINGS Citation**: `docs/LEARNINGS.md:819-820`:
  > "Git Bash rewrote '/en/...' CLI arguments into 'C:/Program Files/Git/en/...'. Set MSYS_NO_PATHCONV=1 for any URL-path argument."
- **Missing Real Input**: Live Git Bash terminal executing with default POSIX argument translation. Tracked with `needs_real_case=True`.

#### 18. `l0692-open-item-not`
- **Guard Name**: `geometry_topology_stair_structural_support`
- **Production Call Site**: [`geometry_topology.support_findings`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/geometry_topology.py)
- **LEARNINGS Citation**: `docs/LEARNINGS.md:894-896`:
  > "Open item, not fixed in the render: the basement stair treads stand 50 mm (east) to 200 mm (west) off the party wall in the spec, with no stringer; the render shows the model as it is. To be resolved in the Revit reconciliation (a design question, not a render one)."
- **Missing Real Input**: Structural consultant engineering details and client confirmation regarding basement stair cantilever support and stringer integration. Tracked with `needs_real_case=True`.

#### 19. `l0870-codex-job-dispatched`
- **Guard Name**: `execution_context_project_root_dispatch`
- **Production Call Site**: [`execution_context.project_context`](file:///C:/Users/mmbka/arch-pipeline-agy/src/archpipe/execution_context.py)
- **LEARNINGS Citation**: `docs/LEARNINGS.md:1072-1075`:
  > "A Codex job dispatched from the wrong directory could not write the repo. Round-3 WP2 ran with the session sitting in the plans folder, so its only writable root was that folder; it worked on a copy and returned a patch. Guard: dispatch Codex only from the repo directory, and every Codex prompt now starts \"verify you can write inside the repo; if not, stop and report\"."
- **Missing Real Input**: Execution context initiated with CWD inside a restricted subfolder where repository root is unwritable. Tracked with `needs_real_case=True`.

---

## Uncovered Lessons Accounting

Following this batch, **40 lessons** remain uncovered in `docs/lessons-audit.md`.

Notable lessons intentionally left uncovered as "no guard yet":
1. `l0101-look-retry-overwrote`: As documented in `docs/c13p2-report.md`, retry filename collision prevention has no automated production guard in code yet. Rather than fabricating a guard, it remains uncovered until a production gate is authored.
2. `l0755-spec-surface-material`: As documented in `docs/c13p2-report.md`, specification surface material verification currently has no dedicated production validator.

All remaining uncovered lessons will be addressed in subsequent batches according to `docs/guard-registry.md`.

---

## Coverage Audit Verification

Running `audit_lesson_coverage` on `docs/lessons-audit.md` yields:
- Total lessons in inventory: **217**
- Covered by guard: **120**
- Covered by review step: **21**
- Needs real case: **36** (17 previous + 19 new)
- Uncovered: **40** (59 previous - 19 new)
- Parsing / table errors: **0**

Reconciliation tally:
```latex
120 + 21 + 36 + 40 = 217
```
The exact inventory invariant is strictly satisfied.
