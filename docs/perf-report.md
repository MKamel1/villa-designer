# Scene-build performance after G6b

Starting HEAD: `3d4fee3aae77d35e2f2d351464d074f20c0b9b02`.
The measured producer is `archpipe.concept.villa_render.build()` with its
complete default D1 example layout and view set. D1 is the example's design
identifier. This is construction performance work; no render or design gate
approval is implied.

Python: `/home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python`,
`PYTHONPATH=src`, `NO_COLOR=1`. No packages were installed.

## Output identity

The frozen starting-HEAD producer emits 393,657,772 bytes through
`json.dumps(scene, sort_keys=True).encode()`; JSON is JavaScript Object
Notation. Its SHA-256 (Secure Hash Algorithm, 256-bit) content digest is
`3db13de7513b146051ad1a99ba60d6cb543c20def565c09884418745d9d754ed`.
Comparison reads every baseline byte; a digest alone is not the equality
check. No float-noise exception is used.

Baseline: `/tmp/laneA-scene-before-frozen.json`.
Final fresh, profiled and warm producer comparisons all exit 0 with every
byte identical. The final source-guarded fresh comparison also exits 0 with
the unchanged source fingerprint
`1b1edcb4519958632796addf5d963c33c1594ff4b5f9b9437f074b2d52288d4f`.
Metrics: `/tmp/laneA-final-guarded-build-metrics.json`,
`/tmp/laneA-delivery-build-metrics.json`,
`/tmp/laneA-delivery-profile-metrics.json`, and
`/tmp/laneA-delivery-warm-metrics.json`.

## Measurement method

The original source package was frozen with `git archive` into
`/tmp/laneA-starting-head/src`, with read-only use of the repository's data.
This ensures late Python imports cannot pick up edited modules. An initial
in-place profile did pick up the changed late toilet-slide import and is
excluded from the before/after table. The archived starting source reproduces
exactly the same scene bytes.

The archived baseline's profiled build took 406.382 s. Profiling overhead is
substantial: the profile recorded 2.120 billion calls. Profile timings are
cumulative seconds including callees; rows overlap and must not be added.
Whole-build times stop when `build()` returns, before JSON serialization or
comparison. The lead's reported unprofiled reference at `fedcc91` was 184 s;
it is historical comparison, not a fresh measurement of this checkout.

Final source-guarded unprofiled fresh build: **59.366 s**. An earlier fresh
sample took **61.805 s**; the same-interpreter warm build took **56.323 s**.
The final fresh and warm samples meet the approximately 60 s target, while
the earlier fresh sample illustrates timing variation around it. All use
the full view set. No budget or geometric threshold was relaxed.

Matched fresh-process profiles: **406.382 -> 94.789 s**, a 4.29-fold speedup.
The final profile records 365.568 million calls, versus 2.120 billion before.
Profiles: `/tmp/laneA-before-frozen.prof`, `/tmp/laneA-delivery.prof`.

| Function | Before cumulative seconds | After cumulative seconds | Before / after calls |
|---|---:|---:|---:|
| `render_views.py::choose` | 61.821 | 7.579 | 31 / 31 |
| `wc_slides.py::apply` | 135.067 | 0.397 | 1 / 1 |
| `physical_part.py::__post_init__` | 120.067 | 16.770 | 3,253 / 1,097 |
| `physical_part.py::geometry_errors` | 94.889 | 13.149 | 3,388 / 1,232 |
| `villa_landscape.py::review_candidate` | 111.469 | 33.139 | 1 / 1 |
| `villa_landscape.py::candidate_violations` | 73.793 | 16.218 | 1 / 1 |
| `villa_landscape.py::_mesh_rect` | 65.401 | 5.734 | 5,278 / 1,564 |
| `villa_landscape.py::route_violations` | 57.740 | 2.033 | 6 / 6 |
| `render_support.py::_triangles` | 10.173 | 3.668 | 196 / 196 |
| `render_support.py::_islands` | 8.833 | 5.540 | 133 / 133 |
| `garden_g6.py::clump` | 15.619 | 6.605 | 37 / 37 |
| `garden_g6.py::findings` | 30.156 | 8.751 | 2 / 2 |

The identical 31 camera calls include the original coarse/refined searches.
Scene equality also covers their candidate counts, framing diagnostics, scores,
positions and targets. Toilet trials no longer reconstruct the mesh list, so
2,156 redundant Part admissions disappear without removing validation of any
built part. Rectangle calls drop from 5,278 to 1,564 without skipping routes.


## Construction changes and proofs

- Camera choice retains every standing point, yaw, refined search, framing
  condition, score and traversal tie order. Whole-subject angles use a vector
  batch to find contenders and original scalar `math.atan2` to confirm maxima.
  Pointwise bearing arithmetic and visible counts are batched; original
  Python `sum` combines subject penalties. Frozen toilet vertices, translated
  rooms, exact frame edges and the complete scene comparison prove parity.
- Toilet slide trials copy their slide map, mesh container, translated member
  records and new faces. Unrelated geometry and metadata remain read-only.
  Trials match a full deep copy by value while caller state remains isolated.
  Existing mounting/clearance regressions review the real decisions and frozen
  failures. The observed Part admissions fall from 3,253 to 1,097 because
  deep-copy reconstruction no longer re-admits unrelated scene parts.
- Physical validation uses build-local keys containing complete immutable
  geometry, surface status and occupied-side direction. Callers receive fresh
  error lists. Each Part shares one face snapshot between its geometry and
  proxy checks. Kind, support, axes, provenance and glass checks remain outside
  the geometry cache. Shared vertices are rounded once per validation; vector
  subtraction and dot products avoid generator overhead while retaining
  Python's summation operator. Existing malformed, proxy, winding, surface,
  support and glass frozen cases remain in the focused batch.
- Route checks compute each item's rectangle once per invocation rather than
  once per walking route. Mesh rectangles reuse live coordinate values within
  a build. Geometry mutations, crossing routes and clear routes are tested.
- Botanical placement batches its unchanged subtract/scale/add operations,
  preserving face order, winding and values. Local mound templates are keyed
  on their exact generator arguments; per-instance material/index/record lists
  remain independent. Yard checks classify unique shared coordinates. Island
  connectivity rounds shared points once and carries the current union root;
  frozen original connectivity and support regressions establish equivalence.
  Repeated triangulation uses immutable arrays keyed by exact live float bits
  and face boundaries. Signed zero remains distinct for geometry hashes; each
  caller receives fresh writable arrays with the original owner order.

The arithmetic differential test rejected an early NumPy cumulative sum:
8.80918087200645 versus Python sum's 8.809180872006449. Python 3.12 uses
compensated summation. A sibling dot-product addition shortcut was also
corrected. Both now retain `sum`; the cancellation case `(1e16, 1, -1e16)`
returns the original 1. No tolerance or design geometry changed.

## Refactor audit

`scripts/refactor_audit.py` did not exist at starting HEAD. The added audit
compares Python definitions, imports, assertions, raises and uppercase
constant names against the base without importing scene producers. It also
reports deleted files. It is a structural inventory, not semantic approval;
byte equality and the frozen regressions supply the behavioral proofs.

Command:

```bash
PYTHONPATH=src NO_COLOR=1 /home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python scripts/refactor_audit.py --base 3d4fee3aae77d35e2f2d351464d074f20c0b9b02
```

The only reported removal is `copy.deepcopy` from `wc_slides.py`, justified by
copying only the trial's changed records and containers. No definition,
assertion, raise, constant name or file is removed. The scalar looming helper
remains available as a reference. Audit guard-removal and relocation tests
pass. Final audit output: `/tmp/laneA-refactor-audit.json`, exit 0.

## Acceptance

HOME denotes the process's home-directory environment setting; the empty
case uses a new directory under `/tmp`, without modifying the user's home.
All checks below pass by process exit status. There are 238 focused tests per
environment: the main 236-case batch and two additional benchmark guards.

| Check | Normal HOME wall seconds | Initially empty HOME wall seconds | Exit status, both |
|---|---:|---:|---:|
| Main focused batch, 236 tests | 2,198.570 | 2,220.659 | 0 |
| Benchmark source/byte guards, 2 tests | 0.093 | 0.120 | 0 |
| `scripts/verify.py --portable` | 73.159 | 72.675 | 0 |

The main batches report 2,125.801 s and 2,147.687 s of unittest time,
respectively; wall time also includes imports and process startup.
Exit/timing records: `/tmp/laneA-acceptance-metrics.json` and
`/tmp/laneA-benchmark-test-metrics.json`. Logs:
`/tmp/laneA-normal-focused.log`, `/tmp/laneA-empty-focused.log`,
`/tmp/laneA-normal-verify.log`, `/tmp/laneA-empty-verify.log`,
`/tmp/laneA-normal-benchmark-tests.log`, and
`/tmp/laneA-empty-benchmark-tests.log`.

The focused batch includes performance, refactor audit, physical parts, build
cache, camera choice, landscape, render standard, final and scene mounting,
G6/G6b garden/support/consumer/view cases, and asset route geometry. The lead
runs the full suite.

The focused command uses the supplied Python interpreter and environment:

```bash
PYTHONPATH=src NO_COLOR=1 /home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python -m unittest tests.test_scene_build_performance tests.test_refactor_audit tests.test_build_cache tests.test_physical_part tests.test_render_views tests.test_landscape tests.test_render_standard tests.test_final_mounting tests.test_mounting_scene tests.test_garden_g6 tests.test_garden_g6_consumers tests.test_garden_g6_support tests.test_garden_g6b tests.test_garden_g6_east tests.test_garden_g6_views tests.test_asset_route_geometry
PYTHONPATH=src NO_COLOR=1 /home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python -m unittest tests.test_scene_build_benchmark
PYTHONPATH=src NO_COLOR=1 /home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python scripts/verify.py --portable
```

New proving tests and the construction changes are registered under
`scene-build-repeated-geometry` and `scene-build-profile-source-drift` in
`knowledge/build-input-guards.json` and
indexed in `docs/LEARNINGS.md`. Agent adapters were unchanged;
`sync_agent_assets.py --check` and `tests.test_agent_assets` pass.

## Repeatable comparison

Capture from the starting producer before editing, then compare the corrected
producer against that same file. The baseline recorder refuses overwrites;
the comparator exits nonzero on any byte difference. The command also
fingerprints declared source inputs before and after construction, refusing
source drift before it writes a baseline or reports success. Add `--profile` to save
Python cumulative timing data and `--metrics` to save timings/digest/equality.

```bash
PYTHONPATH=src NO_COLOR=1 /home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python scripts/benchmark_scene_build.py --baseline /tmp/scene-before.json --record-baseline
PYTHONPATH=src NO_COLOR=1 /home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python scripts/benchmark_scene_build.py --baseline /tmp/scene-before.json --profile /tmp/scene-after.prof --metrics /tmp/scene-after-metrics.json
```

No rendering, commits, full-suite execution or shared-data edits are part of
this delivery. `out/villa/round3` and `assets/user` were not modified.
