# Lane P: render pipeline repair (2026-11-20)

Problem reported by L2: on the laptop the D1 scene build fails at `furniture-stage2` with "furniture fixed-room inputs
changed ... changed sections: meshes", and a build takes 11-15 min instead of ~1 min.

## Root cause (measured)

Not a regression, not a stale receipt, not a missing asset. It is the platform.

1. **The guard compares bit-exact float digests recorded on the workstation.** `furniture_stage2.room_context` hashes
   `json.dumps` of every fixed input; the receipt `knowledge/furniture-stage2.json.gz` was recorded on Linux (glibc).
2. **Same commit (`76ce80d`), same inputs, two machines.** Workstation (Linux, Python 3.14.4, numpy 2.5.3): all 8
   component digests equal the receipt, build passes. Laptop (win32, Python 3.14.10, numpy 2.5.3): `layout`,
   `specification`, `furniture`, `architecture`, `models`, `props`, `materials` equal, only `meshes` differs.
3. **Which meshes.** Dumping the `meshes` section from both and diffing per mesh id: 169 meshes, same ids and order,
   exactly two differ: `furn-cinema-desk-chair-1-0` (20 coordinates) and `furn-cinema-desk-chair-2-0` (38 coordinates),
   largest difference 8.9e-16 m (last-bit float noise from the C maths library's sin/cos in the rotated chair). The two
   platforms' faces are otherwise identical. A receipt regeneration is therefore wrong: it would break the Linux build.
4. **Why not earlier.** Every receipt-bound build before 2026-11-20 ran on the workstation (`~/archpipe/work/lane*`).
   `docs/perf-report.md` numbers (59 s) are workstation numbers (`/home/omar/...` paths in the report), not laptop ones.

Two further Windows-only hazards found on the way (both would also hit the render step, neither is in lane P paths):

- `core.autocrlf=true` makes 1205 tracked text files CRLF in a Windows worktree. `exposure_groups.rule()` hashes
  `knowledge/exposure-group-rule.json` raw bytes and raises "Pre-registered dominant-light rule changed" on CRLF
  (sha `3f247cd3...` instead of `be87dd5b...`); `source_provenance()` hashes raw source bytes, so a scene built on
  one platform never matches the other's source hash in `scripts/villa_render.py` (`Scene provenance mismatch`).
  `git archive` honours autocrlf too: deploy with `git -c core.autocrlf=false archive HEAD`.
  Recommended for the lead (root-level, not mine): a `.gitattributes` with `* text=auto eol=lf` (or `eol=lf` for
  `src/`, `knowledge/`, `spec/`), then re-checkout.
- Without `assets/user` (git-ignored) the build ran ~9 min and died with a bare
  `sqlite3.OperationalError: unable to open database file`
  (`fixture_record.bind_products -> luminaires.library._connect`, `assets/user/luminaires/library.sqlite`).

## Slowness (measured)

| machine | what | time |
|---|---|---|
| workstation, Linux, idle | `villa_render.build()` at `76ce80d` | **89 s** (88.5 s via benchmark script) |
| workstation, Linux, idle | same code at integ-10 `e24189c` | 110 s |
| workstation | `benchmark_scene_build.py --write-scene` (build + exposure groups + 631 MB JSON) | 216 s |
| laptop, win32, other agents running | `build()` to the stage-2 failure | 404-450 s; profiled 533 s |

The laptop is 2.5x slower per interpreter loop (10 M `math.sqrt` iterations: 1.2-1.3 s vs 0.47 s) and shares its 8
cores with the other lanes; the 11-15 min figure is that plus contention. There is no persistent cache to be missing:
`build_cache` is a per-build `contextvars` memo (`scope()` in `build()`), so cold and warm builds are the same work;
repeat builds on the workstation (88-110 s) vary only with machine load. The Oct perf work (184 s to 59 s) is intact:
HEAD (89 s) is not slower than integ-10 (110 s) on the same machine. Hot spots, for a future pass (profile on laptop,
cumulative): `villa_landscape.review_candidate` 229 s, `physical_part._geometry_errors` 129 s, `VIEWS` 107 s,
`geometry_topology.landscape_route_findings` 97 s.

## Fix

The guard stays exactly as it is. What changed (all lane P paths):

- `model/passes.py`: a receipt-input mismatch raised off Linux now carries the explanation and the instruction below
  (`platform_hint`); the error still raises.
- `concept/villa_render.py`: `require_untracked_inputs()` fails at the start of `build()` with the exact fix when
  `assets/user/luminaires/library.sqlite` is missing (was a 9 min run ending in a bare sqlite error).
- `scripts/benchmark_scene_build.py`: `--write-scene PATH` builds with `villa_render.write()` and records the scene file
  sha256, platform and timing (the baseline/identity mode is unchanged).
- `tests/pipeline/test_platform_hint.py`: 4 tests (hint on win32, none on linux, guard still raises, library fail-fast).

Not done, needs an ownership decision (`furniture_stage2.py`, `parents_bed.py`, `beds.py` and the receipts are not lane P
paths): making the guard platform-portable. Design if wanted: add a `portable_digest` (floats rounded to 1e-6 m, `-0.0`
to `0.0`) used for the room-context, camera and cloth comparisons, store its values additively under a `portable` key
in `furniture-stage2.json.gz` and `parents-bed.json.gz` (recomputed from the unchanged Linux scene, whose exact digests
already match), keep the exact digests for audit, and keep exact `digest(receipt)` in the scene so scene bytes do not
change. Until then, the guard is the reason the scene must be built on the workstation.

## How to build (supported path)

Build on `ai-workstation`; the laptop cannot pass the receipt guard.

```
# from the repo (use a clean LF export; assets/user is git-ignored, copy it once)
git -c core.autocrlf=false archive HEAD | ssh ai-workstation 'rm -rf ~/archpipe/work/<lane> && mkdir -p ~/archpipe/work/<lane> && tar -x -C ~/archpipe/work/<lane>'
tar -C <main-checkout> -c assets/user | ssh ai-workstation 'tar -x -C ~/archpipe/work/<lane>'   # 226 MB, once
ssh ai-workstation 'cd ~/archpipe/work/<lane> && PYTHONPATH=src NO_COLOR=1 \
    ~/archpipe/envs/laneP-venv/bin/python scripts/benchmark_scene_build.py --write-scene /tmp/<lane>-scene/scene.json \
    --metrics /tmp/<lane>-metrics.json'
```

The old venv `~/archpipe/envs/b16842c6f2161c9d/venv` is broken (its interpreter `/usr/bin/python3.12` now resolves to
3.14.4, numpy missing); `~/archpipe/envs/laneP-venv` is the same pinned list (`installed.json`) on Python 3.14.4.

Byte-identity check of a change: record once with `benchmark_scene_build.py --baseline B --record-baseline`, then
rerun with `--baseline B` after the change; exit 0 means every byte equal.

## Proof (workstation, `76ce80d` + this lane's commit)

- Baseline (before the lane's edits) `json.dumps(scene, sort_keys=True)`: 631,340,470 bytes, sha256
  `b3075f187bf503cfc8624c55a3ac3da388e64a96d4cdfc365ee2d4a4e89e9aca`; rebuilt after the edits: byte-identical
  (the benchmark's exit-0 comparison), so the appearance is unchanged.
- `--write-scene` file (with provenance, exposure groups): 631,583,581 bytes, sha256
  `8458846dfe09c5569401e852705ca8ed93c427bf154d9d8448f4ccd70dac810a`, source_hash `08c7f978...` (LF export).
- Tests on the workstation: `tests/pipeline`, `tests/model/test_passes.py`, `tests/test_villa_render_scene.py`,
  `tests/test_scene_build_benchmark.py`, `tests/test_scene_build_performance.py`: 55 passed.
- Smoke render through the queue: see the section below.
