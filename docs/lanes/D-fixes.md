# Lane D: G1 design fixes on D1

Source of the decisions: `docs/decisions/G1-safety-decisions-2026-11-21.md`. Findings: `docs/lanes/L1-safety-report-D1.md`.
Branch `lane/D`. Revit was not available: nothing below was built or read back in Revit.

## What changed (files)

| File | Change |
|---|---|
| `src/archpipe/concept/stairs.py` | `straight(..., overlap, infill)`: treads run 16 mm under the next nosing (going stays 280 mm); one 40 x 10 mm flat bar per riser gap; `party_flight_r8()` uses both |
| `src/archpipe/concept/revit_spec.py` | spec keys `stair_infill`, `stair_infill_spec`, `stair_nosing_overlap_mm`, `guards`, `understair_cupboard`; GF core door `swing`; D1 lounge street door 3.41 -> 3.71 m (`tight`) |
| `src/archpipe/model/spec_source.py` | model elements for all of it (below) |
| `revit/build_villa_option.py` | infill bars in the stair DirectShape; `build_g1_details` (guards, cupboard walls and door); door swing flip |

## Gate rows, before and after

Gate rows are the `gate=True` rows of `python -m archpipe.compliance.run_d1` (the lead's run, snapshot regenerated locally).

| Row | Before | After (run_d1 unchanged) | After, once L1 reads the model fields (`tests/design/projected.py`) |
|---|---|---|---|
| LS2 tread overlap (open risers) | FAIL 0 vs 16 mm | **PASS** 16 mm (read from tread boxes) | pass |
| LS2 open-riser gap (100 mm sphere) | FAIL 116.5 mm | FAIL 116.5 (checker ignores the infill) | pass: 38.2 mm |
| LS2 closed risers (A+ target) | FAIL | FAIL | FAIL by design: the client kept open risers. Needs a waiver or info status |
| LS3 guards, 3 new railings (height, A+ 1100, sphere) | not present | 9 rows PASS (1100 mm, drop 3.0 m) | pass |
| LS3 GF stair void / terrace edge / entrance-steps edge | NOT_EVALUATED x3 | NOT_EVALUATED (hard-coded list in `compliance/model.py`) | pass |
| LS4 GF core door | WARN 0.075 vs 0.4 m | WARN (swing not read) | FAIL: the checker only compares jamb distance and has no "swings outward, away from the flight" rule. Needs the rule |
| LS1 space under the flight | WARN 3.08 m | WARN | pass (cupboard) |
| LS5 cinema | FAIL | FAIL | FAIL: recorded waiver |
| Totals (84 gate rows now; 78 before) | 63 pass, 4 fail, 2 warn, 9 NE | 70 pass, 3 fail, 2 warn, 9 NE | 72 pass, 3 fail (closed risers, LS4 rule, cinema), 6 NE |

Not mine, still open: 4 GF daylight rows (no simulation), basement garden doors to a place of safety, dead end.

So the gates do not pass from this lane alone: `compliance/model.py` (L1) still hard-codes the old state. The field list was sent to L1.

## Elements (what `archpipe.model.load("D1")` sees)

- `stair-main`: `going_mm` 280, `tread_depth_mm` 296, `nosing_overlap_mm` 16, `tread_thickness_mm` 60, `riser_infill` (horizontal flat bar 40 x 10 mm centred in each 116.5 mm gap, 15 bars, two openings of 38.2 mm each), `under_flight.enclosed`.
  Riser 176.5 mm, going 280 mm, 2R+G 633 mm, pitch 32.2 deg (ADK limits 220 / 220 / 550-700 / 42). True headroom `stairs.pitch_headroom` is unchanged (nosings did not move): 2041 mm.
  Tread boxes are now 296 mm wide, so a checker that takes the going from box width reads about 26 mm too much headroom: take it from the distance between tread fronts.
- Guards (`railing`): `rail-gf-stair-void` (laminated glass, 1100 mm, 3.71 m edge + 0.95 m return, drop 3.0 m); `rail-gf-terrace-edge` (glass, 1100 mm, 5.03 m west edge + 1.78 m ramp side at y -23.691, 100 mm inside the ramp-edge rail; drop 3.0 m west, 0.55-0.92 m on the ramp side); `rail-patio-steps-edge` (stainless vertical bars 25 mm at 100 mm centres, 75 mm clear, 1100 mm, 1.91 m, drop 3.0 m as villa_env models the steps block, 1.8 m at the gate end). The north patio itself is the low side: its edges are the three guards above and the existing ramp rail.
- `door-GF-landing-gf-core`: `swing_into` core, `swing_direction` outward, `hinge_side` west (hinge at x 4.102), `swing_known` true. The leaf sweeps x 4.102-5.102 beyond the core wall; the stair opening starts at 5.177.
- `joinery-understair-cupboard` (kind furniture): encloses the lowest 11 treads (x 6.561-9.657, y -28.471..-27.471), soffit 0.12-1.88 m, about 2.6 m3. Side wall (top steps with the treads), toe panel, end wall, one door 0.60 x 0.95 m hinged east, opening into the lounge, under treads 6-8 (soffit >= 1.0 m). A taller door at the high end would swing into the lounge sofa (x 4.92-7.52).
- Counts: wall 36, door 18, window 8 unchanged (the cupboard walls and door live inside the joinery element and the spec key, not in `walls` / `doors`), railing 6 -> 8, furniture +1.

## Basement daylight (CL2; client prefers shade)

Base: validated Radiance run on D1 (white finishes), mean DF by area. Everything else is labelled.

| # | Option, cheapest first | Lounge group DF | Kitchen DF | Basis | Cost |
|---|---|---|---|---|---|
| 0 | As simulated | 0.59 % | 0.33 % | measured | - |
| 1 | Widen the lounge street glazing 3.41 -> 3.71 m (**implemented**) | 0.64 % | 0.33 % | estimate: scale by glazed area | lowest |
| 2 | Glazing in kitchen walls facing a garden | - | - | not possible: no kitchen wall faces a garden (south dirty kitchen, north core, east open dining) | - |
| 3 | Glass partition kitchen / dirty kitchen | 0.59 | 0.36-0.44 | analog: measured P3/P4 glass-partition ratios 1.09-1.35 | medium; the wall is hatch + sliding door + column |
| 4 | Rooflight in the GF terrace slab over the loggia | 0.59 | 0.33 | blocked: the apartment terrace slab sits above, no sky | medium |
| 5 | 0.9 m grated slot along the east face under ramp/deck | 1.36-1.38 | 0.59-1.08 | analog: measured P3/P4 slot ratios | high: extension rooms (incl. cinema) lose 0.9 m, drive-over grating, new glazed wall; a light well in effect |

Chosen: option 1 for the lounge. The glazing is already floor to beam across the column-free run, so there is no larger glazing option: option 1 is the last 0.30 m. For the kitchen no glazing option is buildable and worth having (option 3 is at best +0.03 to +0.11 points); nothing implemented. Option 5 is the only one that moves either room materially (lounge to about 1.4 %, kitchen to 0.6-1.1 %); it needs client sign-off and was not built. Shading is kept in every implemented change. No Radiance run of the changed D1 was made. Reproduce the table: `PYTHONPATH=src python tests/design/daylight_options.py`.

## What Revit still needs (not run, no session)

1. Rebuild the option with `revit/build_villa_option.py`: stair DirectShape now includes 15 infill bars; `build_g1_details` adds three guards (DirectShapes in Railings) and the cupboard (walls in Walls, door leaf in Doors, shown closed). All are DirectShapes, not native families; a native door family for the cupboard and native railings are a later step.
2. Core door swing: `apply_swing` flips facing/hand under an unverified assumption (leaf swings opposite `FacingOrientation`; hand points to the hinge). The before/after vectors are in `rb["door_swings"]`; check that the leaf opens toward the core (-y) with the hinge at the smaller x, else flip.
3. The lounge street door type is now 3.71 x 2.20 m: `sized_door` duplicates a type; check the garden-door family allows it.
4. Read back: cupboard bounding boxes, guard heights, no clash of the terrace guard with the ramp-edge rail, riser bars against tread solids.

## Open items

- `compliance/model.py` must read the new fields (and needs an outward-swing rule and a waiver or info status for "closed risers (A+ target)"); the cinema is a recorded waiver.
- Existing `stair-flight-store` furniture (x 5.3-7.1, y -28.47..-28.07) overlaps the cupboard's end 0.54 m: trim it to x <= 6.5 or drop it (furniture layout, not lane D).
- L2-owned `tests/model/test_model_snapshot.py` asserts the pre-fix state (railing 6, `in_revit_spec` false for the void guard): update it. `tests/compliance/test_checks.py::test_headroom_agrees_with_pitch_headroom_for_r8` (27 mm apart now) and `test_d1_as_authored_fails_ls2` (overlap now passes) change with the going/overlap. `tests/test_d1_wp1.py` and `tests/test_d1_round3.py` error on a missing `assets/user/luminaires` library in the worktree (environment, not these changes).
- The guard at the entrance steps stands on shared steps (not ours); the steps' real profile is not in villa_env (a block at GF level).
