# C14 Phase 2, Batch B

Branch-start audit: `0943c1bc5b06c92fb65b1cd7338ccaf605e920a2`.
All twelve Batch B inventory entry scripts now publish `stage-result/1`
records through `archpipe.stage_result` and use `enforce_clean_verdict`
on their command paths. No commit was made. The bedroom remains a
capability example; no villa design gate is approved by this work.

SHA-256 means the 256-bit Secure Hash Algorithm used to identify file
contents. IES means Illuminating Engineering Society; the `.ies` files
here contain measured luminaire photometry. QA means quality assurance;
RVT and RFA are Revit project and family files respectively. A fingerprint
is a deterministic hash of the declared job dependencies and parameters.

## Per-command migration

Every record includes file sizes and content hashes, source hashes, git
revision and dirty state, expected-output completeness and exit status.
The table lists the existing computed failure predicate used for each
command; there are no new geometry, light, comfort or image thresholds.
The shared writer additionally records missing/empty expected artifacts,
as in Batch A. Thermal, worker and workstation records explicitly declare
primary deliverables; diagnostic logs retain hashes and may legitimately
be empty. Missing/empty primary files and changed diagnostic bytes still fail
validation; an empty diagnostic adds no new simulation failure predicate.

| Script | Existing failure predicate | Recorded inputs and outputs; record location |
|---|---|---|
| `scripts/run_bedroom.py` | `not result['passed']`, including existing caught errors, build/room/finish/drawing/lighting gates and end-of-run source-hash comparison | Input-hash paths from `input_hashes()`; acceptance JSON and actual declared artifacts. `out/bedroom.stage-result.json`. Full reuse retains its original predicate and writes a proof with `reused=True`. Worker runtime fingerprint and before/after runtime values are recorded. |
| `scripts/villa_daylight_finished.py` | Existing `fetch()` return: 1 when `not val['all_pass']`, 2 when not DONE; `run()` launch errors retain their existing exception behavior | Run: actual generated job files and adjacent job archive. Fetch: expectation, actual sensor `out.txt` files, available render scene, resulting report. `daylight-run.stage-result.json` / `daylight-fetch.stage-result.json` under the job directory. No Radiance or daylight calculation changes. |
| `scripts/thermal_job.py` | `not result.get('passed', True)`; study/climate jobs keep their existing execution-success semantics | Job JSON, weather, optional `.stat`, present EnergyPlus executable and Radiance files; tool hashes and Python version. Saves `thermal-results.json` before stdout, records actual case outputs and `thermal-job.stage-result.json` under `--out`. |
| `scripts/render_hyperreal.py` | `qa_failed and not a.allow_qa_fail`; the existing explicit override remains recorded | Extract, site, actual deployed IES bytes copied to content-addressed proof-input files; PNG, log, QA and caption per view. `out/photoreal/render-hyperreal.stage-result.json`. Records actual remote Blender version, release and exact command parameters. Rendering flags, tonal retry, promotion and exposure locking are unchanged. |
| `scripts/worker_entry.py` | `not all(r['passed'] for r in results)` and existing benchmark discrepancy greater than five percent (`> 0.05`) | Deployment/environment/model/IES files, per-attempt artifacts, report and bundle. Status writes `worker-status.stage-result.json`; batch writes `batches/<id>/worker.stage-result.json`. The exact existing per-job manifest includes Python/packages, Blender version and binary digest, graphics driver, Radiance files, relevant source and assets. A proof is persisted before the fragile archive step, then updated with its hash. Candidate `design_passed` is not an execution failure. |
| `scripts/workstation.py` | Remote non-zero exit or `report.get('passed') is False` | Submitted model or thermal job/weather archive, local stdout/stderr log, parsed report and downloaded artifacts. `out/workstation/<action>.stage-result.json`, or `thermal.stage-result.json`. Retains structured failed-worker stdout. Worker runtime and per-job manifests retain renderer/tool identity. |
| `revit/build_bedroom.py` | Existing `report['errors']`, existing unplaced-item flags and caught exceptions | Spec, actual template, family/IES inputs; saved model and build report. `<model>.stage-result.json`. |
| `revit/extract_model.py` | Existing `main()` returning `None` for no document, or extraction exception | Actual input model; written extract. `<extract>.stage-result.json`. |
| `revit/export_views.py` | Existing `report['errors']`, false `pdf_exported`, or exception | Pre-save input model; saved model, native PDF and views report. `export-views.stage-result.json` in the views directory. |
| `revit/build_villa_option.py` | Existing per-option `failed` lists or exception | Options spec and source model; actual returned `saved` model paths (including existing version suffixes), images and readback. `build-villa-option.stage-result.json` in the output directory. |
| `revit/build_villa_env.py` | Existing `image export failed:` log entry or exception | Environment spec and source model; saved model, images and readback. `<readback>.stage-result.json`. |
| `revit/build_villa_stairs.py` | Existing `image_errors` or exception | Stair spec and source model; saved model, images and readback. `<readback>.stage-result.json`. Intersections remain measured results, not newly invented failure criteria. |

Revit execution is **unproven at runtime**: there is no Revit/pyRevit on
this workstation. The six native commands have guarded entry points and
use `revit/stage_command.py`, which imports `safe_io` and `stage_result`
through the extractor's explicit `src` path pattern. Portable tests screen
for Python 3-only syntax and exercise the shared wrapper without Autodesk.
They are not an IronPython interpreter or live native-model test.

The shared module now uses Python 2.7-compatible syntax and standard-library
path, subprocess and binary-length handling. Its source hash framing is
unchanged. Provenance retains its explicit source-path scope, so validation
compares that scope rather than an unrelated default source sweep. Optional
pre-run input/provenance snapshots preserve the consumed revision. Exact
input/output overlaps identify intentional in-place saves: validation checks
the produced revision's output hash. Changed input-only sources, forged
input-only overwrite markers and damaged saved outputs still fail closed.

The inventory's bedroom Markdown output is historical: this runner actually
writes `bedroom-acceptance.json`; the migration records its actual outputs.
The command-only worker checkpoint captures a completed batch before further
copies or serialization. The before/after runtime fields diagnose the open
resume hypothesis without changing what is rendered or the reuse predicate.

## Real frozen cases and honest proof limits

Frozen evidence is under `tests/fixtures/c14b/`; local native evidence is under
`out/c14b-final-real/`. `scripts/reproduce_c14b.py` runs without SSH or network.
It uses the existing Blender scene builder and the real measured bedroom
extract from `/home/omar/archpipe/bedroom-e2e/model.json`, copied by value,
plus the three actually referenced IES files. Text-only deployed releases
materialize identical bytes from `ies-text.json`; the regression verifies
byte identity, without changing the deployment filter. Runtime tests remap IES paths
to the frozen local copies. Five fixtures reference those three files.

- **l0040: REAL native replay.** `docs/LEARNINGS.md:281` says:
  “Three unchanged camera jobs were all reused after unrelated
  documentation/orchestration changes; a modified cached artifact fails
  the hash check”. Bed, window and overview were actually rendered at
  32 samples and 128 by 128 pixels. After documentation and unrelated-engine
  fingerprint mutations, `unchanged_reused=3`. Corrupting the cached bed
  image gave `corrupt_output_reused=false` and a new real attempt. Frozen
  scene digest: `e3040b12ad6c4aa1fcf45198c1cfb39d25e91398fab7892167466e16b9dbc533`.
- **l0619: REAL-input reproduction of the omitted-renderer mechanism.**
  `docs/LEARNINGS.md:2258` says: “reconstructed scene-and-IES-only identity
  reused a real image after requested renderer mutation (`legacy_stale_reused=true`)”;
  it records the exact version and resume values below; the historical summary is `docs/lessons-audit.md:173`,
  “A render job resumed a stale result”. A reconstructed old identity with
  only scene and IES hashes reused a real completed image when the requested
  version changed: `legacy_stale_reused=true`. The production worker manifest
  already included the renderer at branch start: no omission is claimed
  in that worker. Actual Blender was `Blender 4.5.14 LTS`; the injected sibling
  was `Blender 4.5.14 LTS [mutation]`. Production job ID changed from
  `9334d0990e6b0f0a445a5db9a13f28d2fd13be9da61ba48f9a5240a6130870bd`
  to `ec88c15b0ee46c272748660313a41f1b7b2f241a3d41c7aed12df1cb3a1356be`,
  with `version_mutation_reused=false`. Both attempts completed in Blender.
  This is a version-string mutation using one installed binary, not proof
  across two installed Blender versions. The old historical driver and its
  original stale-output bundle are not recovered.
- **l0068: REAL Blender light-node reproduction.** `docs/LEARNINGS.md:309`
  says: “An ad-hoc driver did not remap IES paths, and the fallback only
  printed a note”. With the real five-fixture input, the actual Blender
  node graph measured `count=5, with_ies=5`; redirecting those paths to a
  missing file measured `count=5, with_ies=0` and printed the existing
  isotropic-source note. `photometry-probe.json` freezes these measured
  values. The existing `photometry_bound` check passes the former and fails
  the latter; the command proof returns non-zero for that QA failure.
  The explicit `--allow-qa-fail` behavior is retained and recorded.
- **l0089: portable controlled proof, no new historical REAL bundle.**
  `docs/LEARNINGS.md:330` says: “Another session edited the same repo
  concurrently”. The new source-snapshot test captures `version one`,
  injects `concurrent edit`, then proves `CodeDriftError`; source-path-scoped
  validation also stays quiet for unrelated source changes. No commit is
  made, and no other lane's owned files are edited.
- **l0133 remains OPEN.** `docs/LEARNINGS.md:374` says: “right after a passing
  run, `run_bedroom --resume` once re-ran the downstream stages (6 s, worker
  jobs reused) where full reuse was expected”. Its cause is still explicitly
  “Hypothesis, unverified”. Before/after worker runtime capture and a clean
  full-resume command test are provided. Neither is a recovered reproduction
  of the historical symptom; do not mark this lesson closed.
- **l0287: portable interruption proof, native history remains unproven.**
  `docs/LEARNINGS.md:530` says: “in a slow session, persist the expensive
  result first, then do the fragile work.” Tests interrupt worker archive
  creation after completed images, thermal stdout after saved results,
  and native serialization after a saved-model stand-in. Artifacts and
  their stage proofs survive. No 17-minute Revit upgrade is replayed here.

IES content digests: `EWL2A19.ies` =
`8434ad442c158123638f8d9c62061e916918dec8985f9050190d0a8a226d2126`,
`LGLled.ies` = `3c53a083e007947cb3c333bb4ff43ae3d61939f48fd1afdadcb5f9548a777e9e`,
`PLD1A21.ies` = `efb8d1cb91b1629ed44147c2de978c57c260d58f85726d37b4e5bce99ee10bde`.
The frozen replay retains the source digests of its producing run; the live
acceptance replay regenerates identities from current source. The smoke
preview was inspected: it is the low-resolution procedural bedroom
view used for execution/reuse evidence, not a presentation-quality approval.

## Refactor audit and verification

`out/c14b-refactor-audit.json` compares all twelve scripts against branch
start. Every pre-existing top-level calculation/build/render helper is
unchanged; only `main`, added command-proof helpers and the workstation
thermal submission wrapper changed. The nested worker `action` and hyperreal
`render` bodies are also structurally identical. The per-job manifest helper
is an exact extraction of the existing dependency filter. Portable frozen
function hashes in `refactor-audit.json` enforce the unchanged computations.
Native `main` returns actual built-option records for proof and the previously
unguarded build/drawing entry points now have `__main__` guards.

Final focused acceptance after the diagnostic/input-proof corrections:
**90 tests, exit 0**, using the instructed interpreter,
`PYTHONPATH=src` and `NO_COLOR=1`:

```text
python -m unittest tests.test_c14_phase2b tests.test_stage_result \
  tests.test_execution_context tests.test_worker tests.test_render_qa
```

This includes 19 new Batch B tests and a fresh actual Blender replay; no
Blender test was skipped here. When Blender is absent, only the live replay
skips with an explicit reason; frozen regressions and portable command tests
still run. The earlier broad run loaded an obsolete `lib2to3`-dependent test
and is superseded for Batch B acceptance by this corrected run. The full
suite belongs to the lead.

Final current-source verification after the diagnostic/input-proof
corrections completed with exit **0** in both modes:

```text
NO_COLOR=1 PYTHONPATH=src <instructed-python> scripts/verify.py --portable
env HOME=/tmp/c14b-empty-home NO_COLOR=1 PYTHONPATH=src \
  <instructed-python> scripts/verify.py --portable
```

Here `<instructed-python>` is
`/home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python`.
Both logs end in `RESULT: ALL PASS`; process exit status is the authority.
Logs: `/tmp/c14b-focused-final2.log`, `/tmp/c14b-verify-final2-normal.log`
and `/tmp/c14b-verify-final2-empty-home.log`. `git diff --check` also exits 0. No `.agents/` asset changed, so adapter synchronization is not required.

## Lessons to register (lead-owned registry)

1. `l0040-three-unchanged-camera`: exact relevant job manifest, verified
   artifact reuse; `test_live_blender_reuse` and
   `test_frozen_renderer_mutation_and_unrelated_edit`; render-driver stage.
2. `l0619-render-job-resumed`: renderer version/binary and tool runtime in
   production job identities; same two tests and the real omitted-renderer
   replay; render-driver stage. Replace `needs_real_case` only with the
   explicit controlled-reproduction scope above.
3. `l0068-fixtures-rendered-as`: recorded existing photometry QA verdict;
   `test_l0068_real_five_fixture_fallback_record_fails_closed` and
   `test_hyperreal_qa_failure_and_explicit_override`; render-driver stage.
4. `l0089-another-session-edited`: pre-run provenance and scoped validation;
   `test_l0089_code_snapshot_rejects_concurrent_edit`; native command proof.
   This does not replace hunk ownership and commit review.
5. `l0287-slow-session-persist`: persist thermal results and worker/native
   completed outputs before fragile steps; `test_l0287_thermal_result_survives_stdout_failure`,
   `test_worker_batch_verdict_and_pre_archive_checkpoint`,
   `test_native_exception_preserves_model_and_writes_failed_record`.
6. `l0133-open-right-after`: runtime-before/runtime-after capture only;
   `test_bedroom_early_failure_and_full_resume` is a quiet portable case.
   Keep historical cause and native immediate-resume closure pending.
7. C14b intentional input overwrite sibling: pre-save snapshot plus exact
   input/output overlap; `test_in_place_revision_accepts_saved_output_and_rejects_source_and_output_mutations`.
   Fires for source and output mutations, stays quiet for a declared saved
   model, and rejects an input-only forged overlap marker.

8. C14b empty-diagnostic sibling: explicit expected deliverables plus retained
   diagnostic hashes; `test_empty_optional_diagnostic_is_hashed_without_new_failure_predicate`
   and the clean/failed thermal and worker command tests; command-proof stage.
9. Portable replay packaging: exact IES text fixture, verified materialization;
   `test_text_only_worker_release_materializes_exact_frozen_ies` and live replay;
   worker verification stage. No network or native asset transfer is required.

The guard registry and its tests, `knowledge_index.py`, `guidance.py`, beds,
bed/model import, cloth and library manifest remain with their assigned lanes.
