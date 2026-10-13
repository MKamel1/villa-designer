# C6 view intent and l0091

Branch `codex/c6wire`, starting at `0dda200` (`codex/c3p2c`). No commit.
Beds, the library manifest, `guard_registry.py` and its tests are untouched.
Protected shared data is untouched. No camera, design geometry, exposure
value, metering arithmetic or clearance threshold changed.

The requested helper and `tests/test_c6_remaining.py` were absent from this
checkout and its available history. The helper is now implemented in
`archpipe.concept.render_views` and exposed by `scripts/villa_render_views.py`.
Arithmetic stays in Python. Production plan review, scene-build validation
and the exported-scene contract call the same `wall_sightline_findings`.

The check measures a level camera's central forward ray against existing
finite architectural Host faces from C8, the shared geometry-topology
interface. It rejects an opaque face less than 1.0 m ahead. It preserves
actual openings, skips transparent materials and distinguishes a lens
leaving an outward face at zero distance from one looking into that face.
It is a forward-wall screen; it does not prove every subject's visibility.

## Current views and allowances

Measured all **41 current D1 views before enabling** production invocation,
including final-only and retired definitions. There are **zero failing
views under the forward-wall screen** and **no per-view allowances**.
Complete measurements: `out/c6wire/host-clearance.json`.

| View | Diagnostic measurement | Disposition |
|---|---|---|
| v27-east-yard-above | Door-cut rectangle ray hit: 0.012338 m; no actual opaque host face within 1.0 m along the ray | Through-window view. Rectangles do not cut windows; production uses actual finite faces. No allowance. |
| v30-under-ramp-store | Lens on exterior finish face at 0.000000 m, looking outward | No wall ahead. Current view passes; reversing its aim fails at 0.000000 m. Moving the lens 1 mm inside also fails. No allowance. |

The complete plan review produced and was visually inspected at
`out/c6wire/views-plan.png`. **That command exits 1** on one separate,
existing check: v27 is flagged as within 0.2 m of rectangle
`[15.212, -23.591, 15.412, -20.601]`. Its nearest rectangle distance is
0.012 m in plan. This older camera-position check also omits window cuts.
The new finite-face forward check passes v27. The older position check is
unchanged and remains a lead follow-up; no camera was moved to satisfy it.
Evidence: `out/c6wire/plan-review.log`. This diagnostic preview is not a new
presentation render or design approval.

Frozen real v27/v30 camera and nearby face inputs are in
`tests/fixtures/c6-wall-clearance.json`. Tests cover inward/outward rays,
an inside-wall lens, opaque glazing substitution, translated geometry and
renamed views, plus production plan, builder and contract invocation.
The historical S1 record describes an approximately one-metre partition;
no exact historic render geometry is claimed to have been recovered.

## l0091 exposure control

The renderer already has `exposure_mode: set-metered` and
`villa_scene.exposure_locks`. It meters the complete scene cohort for each
selected exposure state and uses one lock per state even for subset render
requests. The contract previously did not validate the controlling mode.

The real current ensuite view with `per-view-metered` reproduced that
escape: the new refusal test failed before the fix (exit 1,
`out/c6wire/exposure-before.log`). `validate_scene` now rejects independent
scene modes, missing modes and independent per-view overrides. The actual
locked scene passes; existing selection-invariance tests prove its full
cohort remains metered for isolated, peer and mixed-state selections.
Historic meter readings were not recorded, so none were fabricated.

The villa-render skill's stale statement that subset requests meter only
the subset is corrected. Agent adapters were synchronised.

## Validation

All Python checks use `/home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python`,
`PYTHONPATH=src` and `NO_COLOR=1`; results are judged by exit status.
No packages were installed. The lead owns the full-suite run.

| Check | Result | Evidence |
|---|---|---|
| `tests.test_render_views`, `tests.test_c6_remaining`, `tests.test_render_standard`, existing `ExposureCohortTest` | Exit 0, 87 tests in 1895.427 s | `out/c6wire/focused.log` |
| `scripts/verify.py --portable`, normal HOME | Exit 0, ALL PASS | `out/c6wire/verify-normal.log` |
| `scripts/verify.py --portable`, initially empty HOME | Exit 0, ALL PASS | `out/c6wire/verify-empty-home.log` |
| `tests.test_agent_assets` | Exit 0, 3 tests | `out/c6wire/agent-assets.log` |
| `scripts/sync_agent_assets.py` | Exit 0, 38 adapters synchronised | `out/c6wire/sync.log` |
| `git diff --check` | Exit 0 | Final workspace check |

The five new C6 tests also passed independently before the combined run.

## Lessons to register

agy owns registry integration; no registry files were edited here.

| Lesson | Production control | Proving tests | Stage |
|---|---|---|---|
| l0481-camera-sees-wall | `render_views.wall_sightline_findings`, using `camera_wall_sightline_clearance`; plan review, builder and exported-scene contract | `tests.test_c6_remaining.WallSightlineTest`; `tests.test_render_standard.RenderStandard.test_l0481_real_wall_is_refused_by_contract_and_scene_build` | 7, before render |
| l0091-every-view-metered | `villa_render_contract.validate_scene`; existing `villa_scene.exposure_locks` | `tests.test_render_standard.RenderStandard.test_l0091_individually_metered_real_view_is_refused`; `tests.test_villa_exposure_assets.ExposureCohortTest.test_lock_is_independent_of_selected_views` | 7, before render |

Measured diagnosis, escape, siblings, control tiers and proofs are appended
to `docs/LEARNINGS.md`. Both controls are production-wired; registration is
handed to agy, not claimed complete here.
