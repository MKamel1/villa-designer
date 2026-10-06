# C4 phase 2 packages a/b/c CHECKPOINT - incomplete, uncommitted

Updated 2026-10-05. Stop here after bathroom fittings and wall lights. No
commit, native Revit rebuild, workstation deployment or replacement of
`out/villa/render-d1/scene.json` was made. All earlier uncommitted work is
retained. The first-fix checkpoint and original outputs are historical
evidence; this record is the current resume point.

Coordinates are metres: model x runs street to garden, model y toward plot
east, model z upward. Movement schedules give minimum x/y/z followed by
maximum x/y/z bounds. Their `mm` column measures millimetres.

## Stair: lead decisions applied, 22 of 22 pass

The 23 original movement rows are approved. Their approval history is in
[stair-approved-movements.csv](../out/c4-phase2bc/stair-approved-movements.csv).
The final geometry also follows the lead's more specific host decisions:

- Stringers 00-06 bind to the actual core/partition return. The authored
  100 mm partition centreline is model y -28.671 m; structural face is
  -28.621 m, outward normal points toward positive y. VERIFIED two-coat
  gypsum plaster adds 13 mm, giving finished face -28.608 m. No wall moves.
  Stringer 06 has a stepped fixing end at the return's actual end,
  model x 6.940 m; its remaining portion reaches the party-wall face.
- The party-wall structural face remains -28.471 m and plaster face
  -28.458 m. The identical coplanar basement/ground-floor wall finish
  continues across the existing 200 mm slab edge. Only this finish strip
  bridges the gap; neither wall footprint is extended. Tests reject offset
  walls, different finishes even at equal thickness, and excessive gaps.
- Stringer 15 binds to the actual existing basement floor face at
  model z -3.000 m. Its lower bearing trims 3.529 mm to that level.
  No floor elevation, build-up thickness or structural alteration is inferred.
- Treads, rail clearance/width and all other design elevations stay retained.
  The existing rail and plate corrections remain 13 mm.

All 22 stair components pass signed-plane and finite-host coverage checks.
[Final bounds movements](../out/c4-phase2bc/stair-final-bounds-movements.csv)
record the result against the frozen phase-1 meshes. Return-host stringers
now have a 63 mm wall-end correction rather than the original party-wall
proposal's 213 mm. Stringer 06 has changed topology; this stair schedule
measures maximum corresponding **bounds** difference, not vertex displacement.
The original approval schedule remains separately preserved.

## Bathroom fittings and wall lights

Package b declares hosts and contracts for 40 parts: the two rain-head
assemblies, hand showers with rails/brackets/sliders/heads/hoses, three
mirrors, six water-closet (WC)/basin assemblies and the two existing extract valves.
Package c covers 22 sconce, articulated SWING reading-lamp and wall-reading-light parts.

Hosts come from actual exported finite room wall polygons, ceiling surfaces
and the SWING side panels of the generated daybed. All coplanar triangles
of a selected source mesh contribute coverage. Structural source polygons,
material and source mesh identity are retained with the host record. Child
projections are explicitly relative to their assembly's fixing plane.

The sole thickness authority is
[finish-build-ups.json](../knowledge/finish-build-ups.json): marble wall
hosts use ASSUMED 20 mm marble plus an ASSUMED selected 3 mm thinset bed
within the VERIFIED 3-6 mm range. Plaster is VERIFIED 13 mm. The tiled-wall
path uses the tile record (ASSUMED 10 mm porcelain plus that bed); the actual
selected bathroom walls are marble. Rain-heads and valves use existing
finished ceiling datums without guessing board thickness or clear void.
SWING panel datums come from actual generated geometry; no extra panel
finish thickness is invented.

[Movements over 5 mm](../out/c4-phase2bc/movements-over-5mm.csv) has **58
PENDING rows**: 38 bathroom and 20 wall-light rows, including 42 component
movements and 16 finish-face additions. Every row gives identifier, host,
old/new bounds, maximum corresponding-vertex displacement and reason.
None of these movements is applied. Pending working mesh geometry matches
the frozen pre-change fixtures. The separate proposal is not approval.

[Applied schedule](../out/c4-phase2bc/movements-applied.csv) has 26 rows,
including 22 zero movements. The four nonzero authorized moves are the two
extract valves, 3 mm each to their finished ceilings, and two SWING arm
fixing-end trims, 1.636307 mm each. Generated body shapes and all exported
emitter/photometry records remain unchanged. The proposed wall-light moves
have not been propagated into analytical lighting or rendered probes.

New host-face meshes are camera-hidden diagnostic records. Pending finish
records retain their structural source plane in the working scene; their
offset faces exist only in the proposal. They must be excluded from a future
presentation/probe export when replacing real visible finishes. This is not
visible cladding integration or a completed presentation render.

## Design findings retained for lead review

Applying the b/c pending schedule alone would still leave these real issues:

- Guest handset: 8.000 mm signed burial into its actual east-wall finished
  plane. Its body is preserved as a rigid proposed 23 mm translation.
- Guest hose: 65.961 mm signed burial into the same finished wall. The
  generated curve extends toward the wall; its shape has not been flattened.
- Guest sconce 03: centre at model y -23.625 m beyond the intended wall's
  end at -23.591 m, a 34 mm centre overrun. Finite coverage fails.

The first two each produce a plane and finite-coverage finding; the sconce
produces one finite-coverage finding. The separate proposal therefore has
five non-missing-host findings on these three components. Do not choose a
different room's wall, distort their bodies or move walls to silence them.
These need an explicit design correction in a later lead decision.

During first verification, the handset regression caught a nearest-distance
selector choosing a door jamb outside the fixing footprint. The selector now
ranks actual finite coverage before distance in each direction and between
directions. This construction fix is registered; the real body collisions
remain OPEN. See `c4-bc-body-and-wall-edge` in
[LEARNINGS.md](LEARNINGS.md) and
[finished-surface mounting](ops/finished-surface-mounting.md).

## Evidence and validation

[Working scene](../out/c4-phase2bc/working-scene.json),
[proposal](../out/c4-phase2bc/proposed-scene.json) and
[mounting report](../out/c4-phase2bc/mounting-report.json) are kept separately.
The checkpoint command exits **1** because the proposal retains the five
design findings; the stair guard has zero findings.

Measured previews were produced and inspected:
[stair](../out/c4-phase2bc/a-stair-preview.png),
[bathroom](../out/c4-phase2bc/b-bathroom-preview.png),
[wall lights](../out/c4-phase2bc/c-wall-lights-preview.png).
These are diagnostic orthographic diagrams, not photoreal review or native
model acceptance. No presentation integration is claimed.

All test commands use `NO_COLOR=1` and process exit status. Final focused
mounting suite: **17 tests, exit 0**, 27.197 seconds. Its frozen fixtures prove
large moves remain unchanged, small moves apply, real body/edge errors fire,
clean SWING hosts stay quiet, and the 5 mm threshold generalises.

Final full suite via `scripts/run_tests.py`: **696 tests, exit 0**, 481.784
seconds. The earlier superseded run also passed (696 tests, 423.121 seconds),
but the final run includes the corrected finite-host selector and rigid-body
regression. A mock worker test prints `FAIL worker unavailable`; this is
expected test output and is not used as the suite verdict. Both actual runner
exit statuses are zero.

`verify.py`: **exit 1**, **571 findings**, including **500 MISSING mounting
hosts** and 71 signed-plane/finite-coverage findings on bound pending parts.
All its other checks pass. The broader guard includes furniture and remaining
support parts as well as ceiling/joinery fittings; the 500 count is the actual
whole-scene missing-host count, not an estimate of two package sizes.

Logs: `out/c4-phase2bc-focused-final.log`,
`out/c4-phase2bc-full-tests-final.log`,
`out/c4-phase2bc-verify-final.log`,
`out/c4-phase2bc-checkpoint-final.log`. Earlier local failing/superseded logs
are retained alongside them.

## Next job

Keep packages d (ceiling fittings) and e (TV/shelves/joinery/trellis and
associated parts) deferred. Keep unknown downlight housing depths, ceiling
voids and exterior finish data missing. Review the b/c pending schedule and
the three design collisions before applying any larger moves. Re-measure
lighting after future approved emitter/fitting moves. Obtain the required
isolated neutral-light photoreal previews with scale figures before visible
integration; native Revit coordination remains separate. This checkpoint
does not close Phase 2 or any real villa design gate.
