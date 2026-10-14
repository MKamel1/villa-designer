# Integration 6 repair and reproducibility

Final revalidation: 2026-10-14, branch `codex/repro`. The bedroom remains a
capability example; this work approves no real villa-design gate. All partial
edits and earlier evidence were preserved. No commits, package installations,
presentation images, or changes to shared `assets/user` / `out/villa/round3`
were made.

## Integration repairs

**a. Fixed-room reviews.** The production full-view and empty-view furniture
signature is `3e92fb1f3c189262cefce3be61e8071e17348f74d7831b1a9e0363855e22dd56`,
identical in HEAD and the refreshed receipt. The failing historical mounting
fixtures suppress finished layers, family bathroom toilet relocation or final
mounting. Those are real fixed-input changes, unlike the normal integrated
scene. Historical diagnostic fixtures retain their procedural furniture bodies. The production guard remains unconditional
and names changed input sections.

The actual garment source migration affects only `parents-dressing` and
`parents-dressing-ext`: 51 mesh rows removed, 191 added and 46 changed. None of
the seven desks, eight chairs or parents bed occupies those rooms. The baseline
uses existing procedural furniture; the candidate uses its replacement. All sixteen individual baseline-relative reviews and their joint
review were rerun:
**zero new relative findings; zero changed stored access/boundary rows**.
The parents-bed absolute diagnostics remain 14 candidate findings versus 16
baseline findings; relative acceptance does not claim an absolute clean bill.
Numerical snapshots were refreshed; unchanged source/room/camera visual
receipts were retained. Exact comparisons and per-item counts are in
`out/integ6/review-differences.json`; refresh evidence is
`out/integ6/review-refresh.json`. This grants no new garment appearance approval.

**b. Stand-in lifecycle.** Each imported appearance mesh has a closed physical
stand-in used for review. Removing models retained their old appearance/body
pairs. The frozen bed-free case has `models=[]` but four orphan rows:
`model-pb-bed::Object_4`, `model-pb-bed::measured-lower-mattress`,
`model-pb-bed::source-pillow-left` and `model-pb-bed::source-pillow-right`.
The scoped dressing fixture likewise retains `model-living-sofa::Object_2`
after declaring no models. These are selection-lifecycle errors, not evidence
of a source-hash merge conflict. `imported_appearance.with_models` validates
incoming admission and constructs matching pairs for the new selection.
Furniture/bed activation, bed baselines and Blender missing-asset fallback use
it. Expanded review inputs refuse selection before orphan colliders can remain.
Actual/renamed stale cases refuse; clean and translated selections pass with
independent pair copies (`tests.test_integ6`, `tests.test_garments`).

The supplied suite's separate “Bedroom acceptance failed / worker unavailable”
text is intentional output from
`PipelineTests.test_worker_failure_replaces_previous_success`, which asserts
that a failed worker replaces stale success. Its actual stand-in traceback is
in `FreshDressingScene`, not a fresh native bedroom run. Native Revit bedroom
acceptance was not run on Linux; no native-model success is claimed.

**c. Provenance.** Fixtures now copy the production `provenance_inputs`
inventory instead of a hand list. It includes imported component policy and
measurements, garment dimensions/retirements and reviewed furniture receipts.
Missing inputs continue to refuse before export.

**d. Closed garments and mounting.** Twelve historical folded/luggage proxy
rows are retired by exact value, requiring all three closed replacements per
row: 36 strict textile parts, without proxy exemptions. The original full-scene
preview checksum is checked after replaying the exact frozen dressing
migration; no unrelated indoor/outdoor rows are excluded. Ten old bracket
approvals retain their existing exact retirement contract, with idempotent
registration. The frozen support inventory changes from 294 to 267 before
fresh contents construction, removing 27 historical dressing entries.
All five rebuilt rails now declare both existing end brackets; removing either
end refuses in garment and mounting review. Only support metadata changed.

**e. Documentation.** The absent `docs/kids-beds-candidates.json` was restored
from its originating search branch. Documentation-link checks pass; generated
`out/` targets are not used to conceal a missing source document.

**f. Performance.** The unchanged full-build limit is 120 seconds. The lead's
original failure was 156.350 seconds. An instrumented diagnostic measured
218.485 seconds: landscape construction 101.565, freezing 46.889, thawing 36.439,
garments 0.863 and legacy stand-in construction 0.123 seconds. The later
instrumented production profile measured 204.814 seconds, including 28.203
seconds in pair construction/copy and 20.881 seconds in JSON encoding.
These instrumented totals are not isolated budget-test timings.

Construction now caches garments by complete authored recipe/floor/policy
inputs and stand-in measurements/pairs by exact source/model values. Callers
receive independent copies. Topology snapshots preserve exact scalar values;
route exclusion precedes unnecessary thawing. Route caching binds layout,
specification, furniture, columns, catalogue, body/direction settings, room
selection and raster resolution; requested diagnostic traces still execute.
Changed recipe/geometry/placement and caller-mutation tests prove invalidation.
The five focused cache tests passed in **117.686 seconds total**, including the
unchanged full-build budget. The lead's complete suite also passed that budget
test. Earlier refusals at 125.998, 121.416, 120.526 and 120.270 seconds are retained
in `out/integ6/`; no limit, geometry or physical allowance was loosened.

## Reproducibility causes and controls

Curtain pleats used Python's process-salted `hash(spec['id'])`. The frozen real
specifications are `tests/fixtures/curtain-repro-before.json`.
`scene_reproducibility.stable_seed` now derives an integer seed from SHA-256
(a stable 256-bit digest) of the entire canonical authored JSON record
(JavaScript Object Notation), with sorted keys and non-finite numbers refused.
The renderer binds every evaluated curtain and every evaluated mesh, including
modifiers, placement and polygon/material indices, without coordinate rounding.
Lighting/per-view receipts carry those bindings; missing/changed bindings refuse
replay equality. Cycles uses explicit seed zero without animated seeds.

The importer used single-precision world-coordinate cross/dot products and
silently reversed a negative result. Nine false reversals were observed; two
actual source solids are frozen in
`tests/fixtures/garment-importer-precision-before.json.gz`.
The bracket's positive volume is 0.0000126713534 cubic metres; the old arithmetic
reported a negative value. The shared `signed_volume` subtracts one common local
origin from authored double-precision coordinates before multiplication and
accurately sums tetrahedral volumes. Positive volume means outward winding.
Both shared physical-part admission and the importer use it; genuinely inverted
solids refuse instead of being reversed. No source faces or placement changed.
Actual Blender read-back, distant renamed/translated siblings, inverted controls,
clean cases and the whole fresh scene pass. The earlier 1242-mesh source audit
is retained in `out/repro/source-volume-audit.json`.

## Whole-tree randomness audit

Every Python file in `src/` and `scripts/` was searched for built-in hashes,
random generators, entropy and indirect seeds. These are all generator sites;
paths below are relative to `src/archpipe/`. Fixed integer seeds and Python's
deterministic string-seed conversion remain. No unseeded production generator
was found. Temporary identifiers, timestamps and run paths do not feed geometry,
materials, lighting or measurements.

| Site | Finding and action |
|---|---|
| `blender/villa_scene.py::build_curtains` | Built-in hash removed; full authored-record digest seed. |
| `blender/villa_scene.py::drape_cloth` | Fixed seed 7; retained. |
| `blender/photoreal.py::cloth_bedding` | Fixed seed 7; retained. |
| `blender/photoreal.py::dress_room` | Fixed seed 11; retained. |
| `blender/climber_placement.py::placements` | Explicit seed, default 7; scene supplies authored appearance seed or deterministic character-code sum. Retained. |
| `concept/generator.py::build` | Deterministic string from named layout organisation and authored seed; retained. |
| `concept/generator.py` wet-core adjustment | Fixed seed 0; retained. |
| `concept/garden_g6b.py::mound` | NumPy numerical-array generator, fixed seed 6062; retained. |
| `guard_registry.py::_make_c6_window_image` | Fixed seed 42 for diagnostic pixels; retained. |
| `scripts/` | No Python/NumPy random-generator or built-in hash site. |

Portable verification audits both trees with import-alias resolution. Old
curtain source, renamed/aliased unseeded generators and global sampling mutations
fire; current trees and owned seeded generators stay quiet. Blender shader noise
is deterministic, and the Cycles sampling seed is explicit.

## Fresh integrated numerical proof

Two separate Blender 4.5.14 processes used `PYTHONHASHSEED=0` and `987654`
(the environment variable controls Python's process hash salt). Both exited 0;
the comparator exited 0. Authored scene hashes, all 1956 evaluated mesh records
and all 50 curtain-panel records match exactly. Maximum direct/total
change: **0.000000 lux (0.000000 percent)**, within the unchanged 0.1 percent allowance.
**All 25 targets pass in each process.** Lux is the unit of illuminance.

- Authored scene digest: `913ce322afe629eeed2949f1b9381564fb5ca041ff86f85c59eb58d35f036bef`.
- Whole evaluated mesh digest: `cc445d1fa235b4402bfe0031b427cbc3f8cd63cffa39534867d074065f45cc19`.
- Commands, exit statuses, unchanged runtime-source/photometry hashes and logs:
  `out/repro/integ6-final/lighting/seed-0/` and `seed-987654/`.
- Comparison: `out/repro/integ6-final/lighting/comparison.json`.
- New baseline: [repro-lighting-baseline.json](../knowledge/repro-lighting-baseline.json),
  a byte-identical copy of the generated final `baseline-receipt.json`.

The new receipt explicitly states that the historical receipt came from a
random pleat seed. Equality with that historical receipt is **not claimed**.
Earlier deterministic proof files under `out/repro/lighting-complete/` remain
historical execution evidence; the current integrated proof is the directory above.

These are maintained horizontal illuminance predictions: maintenance factor
0.8, sky off, 256 samples, zero bounces for direct light and sixteen for total
light. Bound task datums and metered-pixel/source-path guards remain active.
Optical and fixture assumptions remain in the receipt. Both processes give the
following identical display values; the baseline retains unrounded readings.

| Index | Room | Task | Required lux | Direct lux | Total lux | Pass |
|---|---|---|---:|---:|---:|---|
| 1 | kitchen | island prep side | 500 | 1077.164542 | 1364.074941 | yes |
| 2 | kitchen | island seating side | 200 | 837.983761 | 1095.497033 | yes |
| 3 | kitchen | island prep side | 500 | 1033.556785 | 1230.139994 | yes |
| 4 | kitchen | island seating side | 200 | 850.944193 | 1114.747641 | yes |
| 5 | kitchen | island prep side | 500 | 835.447267 | 1113.844393 | yes |
| 6 | kitchen | island seating side | 200 | 676.593447 | 926.308693 | yes |
| 7 | kitchen | single induction zone | 300 | 1004.738223 | 1303.137236 | yes |
| 8 | kitchen | sink | 300 | 1154.108331 | 1348.682725 | yes |
| 9 | dining | dining table centre | 100 | 546.249602 | 649.791183 | yes |
| 10 | dining | table end (homework) | 200 | 462.119161 | 581.608217 | yes |
| 11 | dirty-kitchen | dirty kitchen run | 500 | 679.029388 | 812.590353 | yes |
| 12 | study-game | study-desk | 400 | 931.578619 | 1010.170727 | yes |
| 13 | study-game | study-adult-desk | 400 | 905.809725 | 973.651462 | yes |
| 14 | kids-a | ka-desk-1 | 400 | 1391.480616 | 1499.275933 | yes |
| 15 | kids-a | ka-desk-2 | 400 | 1390.370233 | 1549.446264 | yes |
| 16 | kids-b | kb-desk | 400 | 1389.362928 | 1478.435128 | yes |
| 17 | parents-bed | pillow | 200 | 1110.908604 | 1184.378339 | yes |
| 18 | parents-bed | pillow | 200 | 1114.988342 | 1180.945037 | yes |
| 19 | family-bath | fb-basin | 300 | 1337.479253 | 1617.279087 | yes |
| 20 | parents-ensuite | pe-basin | 300 | 631.213064 | 758.603258 | yes |
| 21 | guest-wc | gwc-basin | 300 | 1375.236241 | 1599.455268 | yes |
| 22 | lounge | armchair | 200 | 789.704300 | 952.244947 | yes |
| 23 | bar-alcove | daybed nook | 200 | 324.603539 | 421.606955 | yes |
| 24 | cinema | cinema desk | 400 | 1483.930549 | 1524.026047 | yes |
| 25 | cinema | cinema desk | 400 | 1492.439854 | 1527.473907 | yes |

## Acceptance

HOME names the child process environment variable for its user configuration
directory. Results use `NO_COLOR=1` and process exit status. The lead's required verdict
arrived before any resumed edit: `unittest=0 verify=0 secs=8066`.
No second full suite was started. The only subsequent executable-file change
extends the existing invalid-view regression; both affected contract tests pass.

| Check | Result | Evidence |
|---|---|---|
| Lead full discovery, including requested repro/garment/imported-admission/lighting/probe/render-standard tests | 1443 tests, 13 skipped; exit 0 | `~/archpipe/logs/lanes/laneB-suite.log`, `laneB.done` |
| Lead portable verification, normal HOME | 196 checks; exit 0 | `~/archpipe/logs/lanes/laneB-verify.log` |
| Final normal-HOME portable verification | 196 checks; exit 0 | `out/repro/integ6-final-verify-normal.log` |
| Final initially empty HOME portable verification, including registered view guard | 196 checks; exit 0 | `out/repro/integ6-final-verify-empty-home-registered.log` and matching process JSON |
| Affected adapter/documentation tests | 5 tests; exit 0 | `out/repro/integ6-final-workflow-tests-after-report.log` |
| Published-view refusal and clean contract tests | 2 tests; exit 0 | `out/repro/integ6-final-published-view-contract.log` |
| Actual Blender precision/inversion regression | 1 test; exit 0 | `out/repro/integ6-final-blender-importer.log` |
| Actual Blender evaluated-probe regressions | 3 tests; exit 0 | `out/repro/integ6-final-blender-probes.log` |
| Independent numerical processes and comparison | both processes and comparator exit 0; 25/25 targets | `out/repro/integ6-final-lighting-proof.log`, final lighting directory |

The first resumed export incorrectly passed the diagnostic `views=[]` to the
publisher. Its existing contract refused before publication; the failed attempt
is retained in `out/repro/integ6-final-export.log`. The corrected normal export
passed with 41 authored views; only the numerical render selection is `none`.
No authored camera was removed or edited. The workflow, negative/clean regression
and registry now preserve this distinction, with adapters synchronized.

Lessons to register: `lighting-runtime-curtain-seed-nonrepeatability` -> stable
seed construction, evaluated-scene receipts and whole-tree entropy audit;
`garments-importer-volume-precision` -> shared local double-precision volume and
inward refusal. These and the integration/proof-input/selection/cache/view
controls are mapped in `knowledge/build-input-guards.json`, proved by focused
regressions and indexed in `docs/LEARNINGS.md`. Numerical closure does not grant
presentation, construction or real villa-design approval.
