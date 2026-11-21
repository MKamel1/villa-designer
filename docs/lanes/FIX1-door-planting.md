# FIX1: lounge street door vs north-garden planting

Cause: lane D widened the D1 lounge/yard glazed door to 3.71 m (door at x 3.62, y -26.16, on a vertical wall, so its
passage spans y -27.995..-24.325, x 3.27..3.97). `landscape-north-mid-02` (Aspidistra, 0.5 m spread) sat at
(3.40, -24.17) and its mesh reached into the passage. The guard (`blocked_openings`) is unchanged.

## Move (knowledge/garden-palette.json, north_garden_g4 drifts, Aspidistra "mid")

| Plant | Before | After |
|---|---|---|
| landscape-north-mid-02 | (3.40, -24.17) | (3.00, -24.17) |

A 0.40 m shift west, nothing else touched. It stays beside the Rhapis accent bed and the trellis start, so the drift
of three Aspidistra and the shade/colour intent are unchanged. `landscape build` passes all candidate checks
(spacing, drift 3-5, layers, door passage); no other plant was reported by the guard.

## Snapshot (src/archpipe/model/data/d1-elements.json)

Regenerated with `model.export --snapshot` (readback furnish-d1). 520 elements: room 30, wall 36, door 18, window 8,
stair 1, column 9, beam 24, slab 4, railing 8, furniture 81, luminaire 142, plant 80, fixture 7, garden 14, context 58.

## Test changes (tests/model/test_model_snapshot.py)

- railing count 6 -> 8 (adds rail-gf-stair-void, rail-gf-terrace-edge, rail-patio-steps-edge; the 3 old rail-edge-* remain).
- furniture `>= 52` -> `== 81` (stricter; includes the under-stair cupboard).
- guards: `in_revit_spec` now True for all three G1 guards (terrace edge and steps edge `in_scene` False);
  terrace slab and entrance steps now assert `guard_present` True with the matching `guard_id`
  (previously asserted unguarded). Drop figures kept.

## Results

`pytest tests/model tests/compliance tests/design`: 76 passed, 2 skipped. `run_d1`: 68 gate rows pass, 0 fail,
11 not_evaluated. `lane_guard.py FIX1`: clean.
