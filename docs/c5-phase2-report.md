# C5 Phase 2: shared fixture records and two source corrections

**Current decision: replace both infeasible side pairs with centred over-mirror bars.**
The [Client decision round](#client-decision-round) implements the client’s
2026-10-08 instruction and supersedes the blocked placement status in the
Lead review round. Earlier placement and preview claims remain historical.

Branch start: `codex/c5p2`, `c2ecf32ec9c870dfd1baab8adf7a273ee55aff28`.
Uncommitted work; the lead owns integration. C5 means the lesson class
“emitter and fitting disconnected”. Coordinates below are model metres:
x and y locate the fitting in plan, z is elevation. Millimetres are used
for small displacement; lumens measure luminous flux, lux illuminance,
and kelvin colour temperature.

## Diagnosis before fixing

The actual baseline is `out/c5-phase2/before.json`; portable frozen values
are in `tests/fixtures/c5_phase2_before.json` and `c5_pair_scene.json`.
Phase 1’s known-findings names were correct, but its room-inset measurements
and interpretation of the parents render were not current evidence.

| Named finding | Old spec centre in metres | Actual built centre in metres | What disagreed |
|---|---|---|---|
| SCONCE-guest-wc-03 | (9.337, -23.625, -1.400) | (9.360, -23.526, -1.400) | The approved finished wall moved the render 23 mm in x; the approved same-wall slide moved it 99 mm in y. Neither reached the lighting spec. Current clear-floor y starts at -23.541: old spec is 84 mm outside, not phase 1’s 34 mm. |
| VSCONCE-parents-ensuite-05 | (19.864, -28.806, 1.600) | (19.887, -28.806, 1.600) | Approved finish moved the render 23 mm in x, with no y correction. The centre is 125 mm beyond the current ensuite limit -28.931, within parents-dressing-ext. The built fitting was not inside the ensuite as phase 1 claimed. |

Their photometry, flux, temperature, shape and heights did not disagree:
guest sconces remain generic 450-lumen, 3000-kelvin globes, diameter
120 mm; parents sconces remain generic 450-lumen fittings dimmed to
180 lumens, 3000 kelvin, procedural 60 by 60 by 500 mm bodies.
The defect is source placement, room containment and the spec/render
mounting handoff. The parent room label names the intended grooming task;
relabeling the light as dressing would conceal the placement fault.

The original authoring placed pairs at the basin centre plus/minus
475 mm without ensuring their complete fitting envelopes fit the room end.
Moving only each named outlier would break the authored 950 mm separation.
Each of the two fixes therefore carries the complete pair: **four fixture
placements are the explicitly declared correction exceptions**. This scope
was stated at the diagnosis checkpoint and before applying the corrections.
No camera, meter, requirement or check tolerance was adjusted to accommodate
them. The mirror and basin placements remain unchanged.

## Source correction and measured result

`vanity_pair_datum` retains 950 mm separation and constructs the complete
fitting envelope inside the room, including the existing lead-approved
5 mm end allowance. It refuses a wall unable to hold the pair. For these
corrected pairs the authored emitter also carries the existing 23 mm
marble-wall finish already applied by the render mounting approval.
Frozen C4 approval inputs remain intact. `reconcile_vanity_emitters` moves
the complete lamp/bracket assemblies to the current record after those
historical approvals; `vanity_scene_findings` checks final measured mesh
centres against the records and rejects missing emitters or disagreement, both
at reconciliation and after every later scene assembly migration.

| Fixture | Current authored centre in metres | Change from old spec, millimetres | Change from old built geometry, millimetres |
|---|---|---|---|
| SCONCE-guest-wc-03 | (9.360, -23.476, -1.400) | x +23, y +149 | y +50 |
| SCONCE-guest-wc-04 | (9.360, -22.526, -1.400) | x +23, y +149 | y +149 |
| VSCONCE-parents-ensuite-04 | (19.887, -29.916, 1.600) | x +23, y -160 | y -160 |
| VSCONCE-parents-ensuite-05 | (19.887, -28.966, 1.600) | x +23, y -160 | y -160 |

The guest first globe envelope starts at -23.536, 5 mm inside its room's
clear boundary. The parents last body ends at -28.936, 5 mm inside its
clear boundary. Room labels, height, flux, temperature and dimming remain
as authored. Both known findings are removed from
`tests/fixtures/c5_known_findings.json`, now an empty baseline.

Frozen old spec positions still fail the production C5 room check for both
original names and renamed siblings. Frozen old built meshes fail against
all four current pair records. Actual fixed meshes stay quiet. A renamed
clean assembly stays quiet, a 5 mm sibling displacement fails, and a missing
built emitter fails. Translated room rectangles exercise the construction
without D1 names; unchanged family-bath is the clean sibling.

## One owner and numeric preservation

`fixture_record.py` owns 23 immutable `FixtureKind` definitions and placed
`FixtureRecord` snapshots, including nested metadata. Their read-only
compatibility views replace the old `KINDS` and product-choice copies.
`record_for` selects effective library or generic flux, retains explicit
fixture overrides and dimming, and `kind_photometry` reads the same photometry
for calculations. Render point emitters read `render_position`; fitting
geometry reads named housing dimensions from the record. Legacy analytic
and render datum offsets remain explicit and unchanged rather than silently
recalibrated. Generic fittings remain labelled generic; procedural housing
is not a verified manufacturer housing or native family.

`revit_spec.lighting_spec` now exports lighting from these same records,
using millimetres for native emitter datums. **The old `revit_spec.build`
never exported villa lighting.** Its existing shell/detail output is exactly
unchanged; no nonexistent old lighting-family output is claimed as tested,
and no native Revit build/save/read-back was performed. The new adapter is
tested against frozen legacy fixture datums, flux, temperature and housing.

Before applying source corrections, `before.json` versus `unified.json`
compared exactly for all 144 authored fixtures, the complete lighting-check
result, all 125 scene light records, all 357 fixture mesh records and the
Revit shell specification. After applying corrections:

- 140 fixture placements are unchanged; the four pair members above are
  the only source-coordinate exceptions. Every one of 144 effective raw
  flux and colour-temperature values is unchanged.
- All 125 scene light records compare exactly: positions, flux, photometry,
  aim, temperature and metadata. The sconces emit through their existing
  mesh materials, so their geometry changes are checked separately.
- 351 of 357 fixture meshes are unchanged. The four diffuser meshes and
  the two parent brackets move rigidly as listed; no shape change occurs.
- All 19 room floor averages and statuses are unchanged.
- Parent basin task: **698 to 699 lux**; guest basin: **1354 to 1357 lux**.
  Both remain above their 300-lux targets. Every other task value/status is
  unchanged. The existing guest excess-light diagnostic consequently changes
  only its printed reading, 1354 to 1357; no existing excess warning is retired.
- Existing Revit shell/detail output compares exactly. Lighting adapter
  entries preserve all raw flux/temperature values and use the same four
  explicitly corrected native emitter datums.

`scripts/checkpoint_c5_phase2.py::numeric_findings` verifies these exact
exceptions and fails on any other lighting result, light record, fixture
identity or geometry change. Result: **zero unexpected differences**.
Receipts: `out/c5-phase2/numeric-comparison.json` and the final current-source
`out/c5-phase2/final-source-comparison.json`, both with zero differences.
The latter also checks final emitter bounds against current records.

The baseline preserves raw source flux rather than reversing rounded render
output. The branch-start `Fixture.lumens` function was executed in an isolated
module on the frozen before placements and unchanged product library.
Measured bound products are DL/WW **732.6**, DLN **1343.2**, ADJ **511.5** lumens,
all **2700 kelvin**. Phase 1’s 670/780/510-lumen summaries are historical,
not these current measured bindings. No product data was changed.

## Neutral preview and review

Actual final fitting geometry and adjacent room shell/furniture were rendered
with neutral light and lamp material emission disabled, at 32 samples.
The diagnostic pose inherits the complete production camera schema.
There are no presentation renders or lighting-acceptance claims.

- `out/c5-phase2/previews-after/guest-wc/guest-wc-neutral.png`
- `out/c5-phase2/previews-after/parents-ensuite/parents-ensuite-neutral.png`

Both images were inspected before handoff. Both members of each pair are
fully framed, remain either side of the retained mirror, and show no fitting
cut into the room-end corner. Their centres intentionally have the minimum
source correction needed for the retained envelope and separation.
Each room retains its own `context-preview-evidence.json` with camera,
geometry hash, material warnings and frame readings. The lead can review
these images before integration; this is not client approval. The receipts
also disclose existing importer face-winding repair notices: two guest
sanitary parts, two parents downlight surfaces and one parents bracket.
Their source geometry is unchanged except the declared bracket translation;
interpretation of those notices belongs to the topology review, not a new
C5 fixture claim.

The first scratch guest preview refused a partial camera missing `sensor_mm`.
Its actual input is frozen in `c5_preview_camera_before.json`; construction
now copies the complete production camera and fails early on incomplete
schemas. A real/clean/renamed-sibling regression covers it. A scratch literal
prefix substitution also caused an import-time syntax error; the focused
import test rejected it. Named record dimensions replace literal-prefix
substitution, and neither failed result was accepted as evidence.

## Remaining nine lessons: explicitly open

The source-quoted audit is `knowledge/c5-phase2-lessons.json`, read by the
fixture-record test. No record mismatch or invented failing input is used
as a surrogate for an optical or runtime failure.

| Lesson | Held LEARNINGS evidence | Why this record does not close it |
|---|---|---|
| l0025 | Line 225: “Third-party families may override photometry even when writes appear successful.” | No saved live family parameter-write/read-back values are frozen here. A record/native adapter cannot prove the family survived save. |
| l0026 | Line 226: “Blender IES azimuth differs, finite sphere sizing can wash out a strip light, coarse angular interpolation biases narrow beams.” | Cycles orientation, finite source transport and angular interpolation require their actual renderer probes. No scoped frozen angular failure values were recovered. |
| l0074 | Line 274: “Nishita sky units and sun direction were unknown”; correction “x800 scale to lux, measured at three elevations”. | Sky calibration belongs to calibrate_sky.py; a fitting record does not own the sky. |
| l0080 | Line 280: 2700 K incorrectly gave “(1, 0.65, 0.34), not (1, 0.39, 0.10)”. | Record CCT agreement cannot catch display-sRGB used as linear light. Preserve kelvin_to_rgb and the existing Planckian-locus verification; no new optical closure claimed. |
| l0090 | Line 290: “Window glass passed 100% of sunlight; the model says 85%.” | Glazing transmission and two-face transport are outside the lamp record. |
| l0606 | Lines 808–810: “Sconces alone gave 87-142 lx on the basin counters (300 needed)”. | Preserve task downlights and card checks, but exact old scene inputs for that range are absent here. The current removal test is not called a frozen historical optical reproduction. |
| l0650 | Lines 852–855: zero lux, camera 25 mm above sensor, default near clip 100 mm; corrected island 1473 versus 1419 lux. | The actual sensor-camera depth/clip probe is required, independent of emitter ownership. |
| l0656 | Lines 858–859: sheet 0.700 for stated 0.70; slab 0.850 for stated 0.85. | These are successful probe readings, not a frozen failure. Do not invent one or claim fixture unification governs glazing. |
| l0874 | Lines 1076–1079: 334k calls, 171 of 180 seconds, corrected 1.6 seconds; 110-times slowdown. | Preserve the per-room cluster and per-kind photometry caches. A real historical workload/timing harness remains outside this record refactor; call-count mocks would not establish the recorded failure. |

## Refactor audit and verification

Command:

```text
PYTHONPATH=src NO_COLOR=1 /home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python scripts/refactor_audit.py --base c2ecf32ec9c870dfd1baab8adf7a273ee55aff28 --allow knowledge/c5-phase2-refactor-allow.json
```

Exit **0**, no unallowed removals. Every removal is justified individually in
the allow file: declarations/cache and flux/photometry branches moved to the
record owner; render copies replaced with record properties; the lesson test
now reads actual source-quoted status; the existing missing-depth mutation
replaces an immutable mapping attribute rather than mutating it.
The audit also infers two coincidental empty-value “renames”: PRODUCTS to the
room counter and the binding flag to a correction flag. Those are not actual
semantic renames: the product cache and binding flag moved to fixture_record;
exact numeric comparison proves their preserved behavior. No production
check, generic fallback, task calculation or native output path was removed.
Full receipt: `out/c5-phase2/refactor-audit.log`.

Verification uses the supplied interpreter, PYTHONPATH=src, NO_COLOR=1 and
process exit status. Portable verification declares native Windows-only
coverage unavailable; it does not claim live family coverage.

- `scripts/verify.py --portable`, normal HOME: exit **0**, ALL PASS.
- `scripts/verify.py --portable`, empty HOME: exit **0**, ALL PASS.
- Required acceptance modules (`fixture_record`, `villa_lighting`, `d1_wp1`,
  `render_standard`, plus the new Phase-2 module): **114 tests**, exit **0**.
  The final expanded record and lighting modules were rerun after the last
  dimension consolidation: **45 tests**, exit **0** (the Phase-2 module
  expanded from 7 to 12 tests).
- Final record subset (`tests.test_fixture_record` plus
  `tests.test_fixture_record_phase2`): **27 tests** within the passing
  45-test final run; includes lossless flux, immutable nested metadata,
  historical/clean/renamed mesh proofs and the camera-schema reproduction and tuple/JSON comparison regression.
- Affected ceiling missing-depth/approval test in `tests.test_mounting_scene`:
  **1 test**, exit **0**.
- Numeric checkpoint: exit **0**, zero unexpected differences.
- Both neutral corner render processes: exit **0**; images inspected.

No commits, generated-extract edits, shared round3/user-asset writes, guard
registry edits, furniture implementation edits or agent-adapter edits were
made. The full suite and native read-back remain with the lead.

## Lessons to register

This is the handoff to agy, who owns `guard_registry.py`; the existing five
Phase-1 lesson mappings are strengthened, not counted as nine new closures.

- `l0610-fitting-labelled-wrong` -> `vanity_pair_datum`, `fixture_findings`;
  proving tests: frozen real old mounts, translated construction, current
  empty known-findings baseline.
- `l0095-lamp-sources-sat` -> `record_for`, `reconcile_vanity_emitters`,
  `vanity_scene_findings`; proving test:
  `test_real_built_pair_guard_fires_quiet_and_renamed_sibling`.
- `l0096-two-spec-heights` -> `FixtureRecord.native_spec`, `fixture_findings`;
  retain the existing frozen impossible-height and sibling proofs.
- `l0119-housing-below-ceiling` -> `FixtureRecord.mount`, `fixture_findings`;
  retain the existing real recessed-note / pendant-failure proofs. Procedural
  housing dimensions do not replace measured recess depth.
- `l0123-swapping-4300-lm` -> `record_for`, `fixture_findings`;
  retain the existing real flux-band failure and sibling proofs; add
  `test_all_effective_flux_and_colour_values_match_branch_start`.

Additional operating controls, separate from those lesson claims:
`emitter-fitting-phase2` -> `numeric_findings`;
`c5-preview-camera-schema` -> `neutral_input`;
`c5-flux-baseline-precision` ->
`test_all_effective_flux_and_colour_values_match_branch_start`.
All nine lesson identifiers in the preceding table remain open.

## Lead review round

**Placement acceptance is blocked.** The lead's 2026-10-08 review rejected
both Phase-2 block shifts. The placement and preview-acceptance claims above
are historical and superseded by this section; the accepted shared record,
reconciliation, emitter checks and numeric preservation remain intact.
No feasible corrected pair exists under the requested fixed-mirror rule,
so this round stops placement work without moving anything else. All 144
fixture placements, effective flux, dimmers, colour temperatures, fitting
shapes, mirror/basin placements and cameras remain as at round entry.

### Source and measured constraints

The rule source is the lead instruction of 2026-10-08: centre each pair on
its fixed mirror/basin axis; prefer the authored 950 mm separation; otherwise
choose the largest separation respecting complete fitting envelopes,
existing 5 mm boundary allowance and a clear mirror-edge gap. Do not shift
the axis or move another design element when these constraints conflict.

Held card `rid-vanity-sconces-914`, Mitton and Nystuen, *Residential Interior
Design*, 4th edition, 2022, Figure 7.55, printed page 218, recommends grooming
sconces each side of the mirror at adult eye level, 914–1016 mm apart. It does
not supply a minimum fitting-envelope-to-mirror-edge gap. Searches across
`knowledge/library.json`, `knowledge/rule-evidence.json` and the remaining
held knowledge JSON, including NKBA cards, found no numerical mirror-gap
rule. The original-page index is unavailable on this workstation (configured
`/home/omar/archpipe-sources/_index` is absent); no new original-page
verification or external published minimum is claimed.

Accordingly the fallback is **ASSUMED authored**: the intact side of the
current, lead-rejected design gives 284 mm in the guest WC and 325 mm in
the parents ensuite. These are actual complete-mesh gaps, rather than
estimates from perspective images. The initial diagnosis update mentioned
135/165 mm: those were the original design's intact-side gaps, not the
current rejected design. Both interpretations are tested and infeasible.

Actual rejected fixtures, fitting meshes, mirrors, clear boundaries and
gap assumptions are frozen **by value** in
`tests/fixtures/c5_lead_rejected_pairs.json`. Guest mirror edges along the
wall are -23.430/-22.870 m, basin/mirror axis -23.150 m; parents edges are
-29.561/-29.001 m, axis -29.281 m. Both mirrors are 560 mm wide. The basin
axes independently read from `villa_furnish.layout` match the measured
mirror centres; neither moves. Fitting half-widths are 60 mm for the guest
globes and 30 mm for the parents bars; the parents brackets are narrower.

| Measurement | Guest WC | Parents ensuite |
|---|---:|---:|
| Clear wall interval, model metres | -23.541 to -20.801 | -31.111 to -28.931 |
| Rejected pair midpoint offset from fixed axis | +149 mm | -160 mm |
| Rejected complete-envelope mirror gaps, low/high side | -14 / 284 mm | 325 / 5 mm |
| Maximum symmetric separation, including 5 mm end allowance | 652 mm | 630 mm |
| Gap each side at that maximum | **-14 mm overlap** | **5 mm clear** |
| ASSUMED current intact-side minimum gap | 284 mm | 325 mm |
| Minimum separation needed for that gap | 1248 mm | 1270 mm |
| Separation shortfall | **596 mm** | **640 mm** |
| Shortfall using original intact-side gaps 135/165 mm | 298 mm | 320 mm |

The maximum separation is twice the smaller available distance from the
fixed axis to a clear wall end, less fitting half-width and the 5 mm
allowance, capped at 950 mm. The minimum is mirror width plus two fitting
half-widths plus two minimum gaps. Thus the guest pair cannot clear the
mirror even with zero minimum gap. Parents allow only 5 mm each side,
below either authored fallback. The 914–1016 mm published nominal guidance
also cannot fit these constrained ends; no exception to it is labelled
published guidance.

### Control and regression evidence

`centred_vanity_pair` constructs around the fixed axis and returns the
largest feasible separation; it refuses with the measured shortfall when
none exists. It is intentionally not wired into the blocked production
placements: the historical `vanity_pair_datum` is explicitly marked
lead-rejected and retained to preserve the uncommitted rejected result.
No alternative placement, fitting substitution or mirror/basin move is
silently introduced. A future feasible proposal must use the centred solver.

`vanity_pair_findings` independently reviews measured centres, mirror
symmetry, complete fitting envelopes and both mirror gaps. The actual
rejected block shifts now fail the symmetry check despite passing the
older containment check. `checkpoint_c5_phase2.py` always separates design
acceptance from numeric preservation; `--lead-review` also recomputes current
live authored fixtures and analytical lighting. Both default and lead-review
modes refuse these actual placements rather than treating preservation as
acceptance. Result: **design_passed false; no proposed centres; no placement
change; zero unexpected numeric differences**.

`tests.test_c5_lead_review` proves the frozen real rejection, measured
shortfalls for both current and original-gap interpretations, clean feasible
pairs at authored spacing, a constrained clean pair at maximum spacing,
a symmetric enlargement that exceeds containment, a 5 mm asymmetric mutation,
translated real rooms and a translated clean sibling. Missing measured pair
members fail closed. The clean solver tests are synthetic feasible walls;
there is **no clean corrected real-room case**, because the instructed
constraints are infeasible. This is explicitly reported rather than moving
another design element to manufacture that proof. Registry handoff remains
with lead/agy: `c5-vanity-pair-symmetry` maps to the centred construction,
`vanity_pair_findings`, the checkpoint and those real/clean/sibling tests.

### Lighting and preservation

Fresh `villa_lighting.check` uses the unchanged fixtures, generic sconce
photometry and existing product bindings. It reports direct-only maintained
horizontal task-point illuminance, with maintenance factor 0.8 and probe
height 0.91 m above the finished floor. No flux or dimmer is tuned.

| Grooming counter task | Original phase-2 baseline | Rejected round-entry placement | This round, unchanged | Card target |
|---|---:|---:|---:|---:|
| Guest WC, gwc-basin | 1354 lux | 1357 lux | **1357 lux** | 300 lux: pass |
| Parents ensuite, pe-basin | 698 lux | 699 lux | **699 lux** | 300 lux: pass |

Target source: held verified card `ies-res-vanity-grooming-300`, *IES Lighting
Handbook*, 10th edition, 2011, Table 33.2, printed page 33.8, grooming row,
age 25–65 recommendation. The same card separately names 400 lux vertical
at the face; this horizontal task-point calculation does not establish that
vertical result or an area-average measurement. No new rendered-light probe
or native model read-back is claimed. The guest excess-light diagnostic
remains; neither target nor status was changed to excuse placement.

The extended receipt `out/c5-phase2/lead-review-comparison.json` includes
actual midpoint offsets, both gaps, separation bounds, refusal messages,
original/current task readings and the exact preservation audit. The
accepted baseline numeric exceptions still describe the earlier four
fixture corrections; this round adds **zero** corrections. All other tasks,
all 19 floor averages, all 125 scene-light records, all fitting geometry and
the Revit shell specification remain as at round entry. The scene geometry
used in the renewed diagnostics matches the existing rejected receipts.

### Neutral previews and review

Renewed 32-sample neutral previews use the **same cameras, complete geometry,
neutral fill and disabled material emission** as the rejected previews:

- `out/c5-phase2/lead-review/previews-unchanged/guest-wc/guest-wc-neutral.png`
- `out/c5-phase2/lead-review/previews-unchanged/parents-ensuite/parents-ensuite-neutral.png`

Each folder holds `context-preview-evidence.json`. These images show the
unchanged rejected design; no corrected preview can be generated without
violating the instruction to stop when infeasible. The render critic
inspected old and renewed full-size PNGs and confirmed matching camera,
geometry hash, fill and subject projections. Both pair members are wholly
framed. Guest overlap and parents unequal gaps remain visible. Cabinetry is
below the crop: these are mirror/pair detail diagnostics, not whole-vanity
views or presentation/lighting acceptance. Review:
`out/c5-phase2/lead-review/critic-review.md`.

An initial renewed guest command omitted `--views guest-wc`: Blender exited
zero but produced the empty receipt `[]` and no PNG. It was rejected on
receipt inspection and rerun with explicit view selection. Both retries
produce the required files. `preview_receipt_findings` and the real empty
receipt/clean/renamed/missing-file regression reject this execution-success
trap. The workflow now requires explicit `--views`, receipt identity/count
and image existence before visual review.

### Acceptance

Verification uses the supplied Linux interpreter, `PYTHONPATH=src`,
`NO_COLOR=1`, and process exit status. The required portable checks and
focused acceptance runs are recorded below. A green code check does not
approve these rejected placements. No commit, shared-data write,
generated-extract edit, dependency install, agent-asset edit, central
registry edit or native Revit operation is performed in this round.

- New lead-review regressions: **9 tests**, exit **0**;
  `out/c5-phase2/lead-review-final-tests.log`.
- Affected ceiling approval regression plus the first eight review tests:
  **9 tests**, exit **0**;
  `out/c5-phase2/lead-review-final-affected-tests.log`.
- Final `scripts/verify.py --portable`, normal HOME: exit **0**, ALL PASS;
  `out/c5-phase2/lead-review-verify-normal-final.log`.
- Lead-review checkpoint with fresh analytical calculation: exit **1**,
  **expected design refusal**, zero unexpected numeric differences;
  `out/c5-phase2/lead-review-checkpoint-final.log`. Default checkpoint also
  exits **1** on the same symmetry/infeasibility result.
- Both renewed render processes: exit **0**; required PNGs and one-view
  receipts verified and visually reviewed. Explicit camera/geometry/fill/
  subject comparison: zero differences,
  `out/c5-phase2/lead-review/preview-comparison.json`.
- All **144** round-entry fixture inputs compare exactly;
  `out/c5-phase2/lead-review/round-entry-preservation.json`.
- Final `scripts/verify.py --portable`, fresh empty HOME
  (`/tmp/c5-lead-review-clean-home-qfulqV`, empty at launch): exit **0**,
  ALL PASS; `out/c5-phase2/lead-review-verify-fresh-empty-home.log`.
  The earlier normal/empty-HOME runs also exited 0; the fresh run avoids
  treating a cache-populated HOME from an earlier verification as empty.
- Required focused modules (`fixture_record`, `fixture_record_phase2`,
  `c5_lead_review`, `villa_lighting`, `d1_wp1`, `render_standard`):
  **127 tests**, exit **0**;
  `out/c5-phase2/lead-review-acceptance-tests.log`. This run loaded the first
  eight lead-review tests; the final nine-test subset above additionally
  includes the real empty-preview-receipt regression and the latest
  missing-measured-member assertion. The lead runs the full suite.

Round outcome: accepted record/refactor work preserved; the asymmetric
placement is rejected by an independent check; both centred proposals
refuse with measured shortfalls. Real placement acceptance remains open.

## Client decision round

**Change source: CLIENT DECISION 2026-10-08.** The client replaced each
infeasible side-sconce pair with one linear light centred above its fixed
mirror/basin axis. This is a fixture decision for the D1 capability example,
not approval of a real villa stage. No mirror, basin, other fixture, existing
dimmer, task point, target or camera is moved or changed.

The shared immutable fixture record now supplies kind `VANITY-LIN`, a
wall-mounted linear mirror light, to the analytical calculation, procedural
render fitting and `revit_spec.lighting_spec`. Retired active identities are
`SCONCE-guest-wc-03/-04` and `VSCONCE-parents-ensuite-04/-05`; replacements are
`VANITY-LIN-guest-wc-03` and `VANITY-LIN-parents-ensuite-04`. The authoring
counter reserves both old pair slots so every following fixture keeps its
identity. There are 142 current fixtures, including 140 unchanged fixtures.
Frozen C4 schedules, migration receipts and finite wall-host identifiers
retain their historical names; they do not restore the removed fittings.

### Source and assumptions

A search of held cards in `knowledge/library.json` and the remaining
knowledge JSON found `rid-vanity-sconces-914` and
`ies-res-vanity-grooming-300`, but no numerical over-mirror bar offset or
lumen output, including NKBA guidance. The former cites Mitton and Nystuen,
*Residential Interior Design*, 4th edition, 2022, Figure 7.55, printed page
218, and describes overhead-only light as the fallback. It does not set
this new bar’s dimensions or height. The held original-page index remains
unavailable on this workstation; no new book-page verification is claimed.

The existing grooming target remains 300 lux, from IES *Lighting Handbook*,
10th edition, 2011, Table 33.2, printed page 33.8. The held verified card
states maintained horizontal illuminance at 0.91 m and separately recommends
400 lux vertically at the face. This round checks the existing horizontal
task point only; it does not claim verified facial cross-lighting.

Both fittings are **ASSUMED generic linear LED bars; no product verified**.
The shared record owns these ASSUMED authored figures: 500 mm length,
40 mm total height, 40 mm total depth, centre 100 mm above the mirror top,
and 100 lumens raw output at 3000 kelvin. Each fixed mirror is 560 mm wide;
the casing therefore has 30 mm inset at each end and 80 mm clear gap above
the mirror. The diffuser is a closed opal solid within the rear plate and
perimeter casing. Native adapter entries also carry the assumption and
client-source labels. No product catalogue binding or manufacturer family
is claimed.

| Geometry, model metres | Guest WC | Parents ensuite |
|---|---:|---:|
| Finished wall face, x | 9.300 | 19.827 |
| Fixed basin/mirror axis, y | -23.150 | -29.281 |
| Mirror top, z | -1.200 | 1.800 |
| Bar/emitter centre, x / y / z | 9.320 / -23.150 / -1.100 | 19.847 / -29.281 / 1.900 |
| Complete casing y limits | -23.400 to -22.900 | -29.531 to -29.031 |
| Room-end clearance, nearer end | 141 mm | 100 mm |

Here x and y are horizontal model coordinates and z is vertical elevation;
the basement finished floor is at -3 m and the ground floor at 0 m. Both
bar centres are therefore 1900 mm above their own finished floor. The full
casing contacts the measured finished wall face, stays within the room’s
clear boundary with the existing 5 mm allowance, and clears the mirror and
ceiling. This allowance remains an authored design value, not a standard.

### Lighting result and retained excess

The new bars retain the existing generic isotropic photometry family
(`beam=None` means equal intensity in every direction), with 3000 kelvin
colour temperature. Guest output is 100 lumens effective; the parents’
existing 0.4 dimmer gives 40 lumens effective from the same 100-lumen raw
output. No existing driver setting changes.

| Grooming task point | Before, rejected pairs | Retained lights only | After, single bar | Target |
|---|---:|---:|---:|---:|
| Guest WC basin | 1357 lx | 1292 lx | 1298 lx | 300 lx |
| Parents ensuite basin | 699 lx | 673 lx | 676 lx | 300 lx |

Lux measures illuminance and lumens measure light output. These are rounded
analytical maintained direct-light values with maintenance factor 0.8,
without furniture shadows or inter-reflection; the neutral previews disable
emission. The task downlights and other retained sources alone already
exceed the target by 992 and 373 lux. No nonnegative bar output can reduce
the totals to near 300 lux while those sources and dimmers remain fixed.
The low authored 100-lumen selection adds approximately 6 and 3 lux, less
than one percent of each retained subtotal. Both tasks pass; the guest’s
existing excess warning remains (1298 versus the unchanged ASSUMED 900-lux
warning threshold). This round does not claim to eliminate the retained
overshoot or calibrate finite casing/diffuser transport in Blender.

### Guards and neutral review

`over_mirror_datum` constructs from the fixed basin axis and recorded mirror
top, never clamps the axis to a room end. `vanity_pair_findings` accepts one
centred fitting only when the caller explicitly declares an over-mirror
configuration; a missing member of a side pair still fails. Actual mesh
review additionally measures the entire casing, diffuser centre, mirror
axis/top, wall contact, room limits and ceiling clearance. The two known
findings are removed from `c5_known_findings.json`; real original mounts,
lead-rejected block shifts and their asymmetric gaps remain frozen tests.

Frozen actual scene input is `tests/fixtures/c5_client_vanity_scene.json`.
New Phase-2 proofs cover real clean bars; missing, shifted, overlapping and
off-wall bodies; a renamed and translated villa sibling; opposite-wall
placement; overlong fitting refusal; and explicit single-versus-pair review.
Historical pair and C4 host-coverage regressions retain their original
failing values rather than being weakened for removed elements.

Both 32-sample neutral previews reuse the **exact previous cameras and
neutral fill**, with all material emission disabled:

- `out/c5-phase2/client-decision/previews/guest-wc/guest-wc-neutral.png`
- `out/c5-phase2/client-decision/previews/parents-ensuite/parents-ensuite-neutral.png`

Both were inspected at full size and independently reviewed by the
`render_critic` role: bars centred, clear top gaps and corners, old pairs
absent, whole new emitters framed, no introduced visible issue. Per-room
`context-preview-evidence.json` receipts record unchanged camera/fill,
geometry hashes, subject framing and importer notices. These are diagnostic
geometry previews, not photometric or presentation-render acceptance.

### Verification receipts

Final current-source capture and required acceptance results are recorded
below after execution. No native Revit build/save/read-back was performed;
this round verifies its specification adapter on Linux. The lead retains
full-suite and integration ownership. No commits or shared round3/user-asset
writes are made.

The fresh capture (`out/c5-phase2/client-decision/comparison.json`) exits
**0**, with `passed: true` and no unexpected differences. It compares with
the completed `final-after.json` record/native checkpoint and the preserved
`after-scene.json` physical geometry, rather than an earlier setup snapshot.
All 140 retained fixture inputs and native adapter entries, all 125 explicit
scene-light records, shell/furniture/dressing geometry, models, cloth, curtains
and props compare exactly through their exported JSON contracts. The complete
fixture-mesh set changes from 357 to 355: six retired pair meshes become four
new casing/diffuser meshes. All 17 other floor averages stay unchanged;
parents changes 116 to 112 lux and guest 263 to 253 lux, with statuses and
targets unchanged. No other task reading changes.

Final previews were regenerated from that fresh source capture. Their
`preview-comparison.json` passes current geometry hashes, identical camera
and fill, disabled emission and wholly framed emitters. Independent final
review is recorded in `client-decision/critic-review.md`. The first comparison
receipt remains as `preview-comparison-first.json`: it rejected old preview
hashes after the final pipeline changed mesh ordering and added authored
local-axis/basis metadata to the new meshes. Fitting faces and dimensions
were unchanged. Regeneration restores
exact input/receipt agreement without a geometry, camera or fill adjustment.

Executed acceptance commands use the supplied Python interpreter,
`PYTHONPATH=src`, `NO_COLOR=1`, and process exit status:

- `scripts/verify.py --portable`, normal HOME: exit **0**, ALL PASS;
  `out/c5-phase2/client-decision/verify-normal-final.log`.
- `scripts/verify.py --portable`, fresh empty HOME: exit **0**, ALL PASS;
  `out/c5-phase2/client-decision/verify-empty-home.log`.
- `scripts/refactor_audit.py` against the original branch checkpoint with
  `knowledge/c5-phase2-refactor-allow.json`: exit **0**, no unallowed removals;
  `out/c5-phase2/client-decision/refactor-audit.log`.
- Both final neutral render processes: exit **0**; each has exactly one
  requested image and a passing final receipt comparison.
- `scripts/sync_agent_assets.py` regenerated 38 adapters after the canonical
  villa-render workflow update; subsequent `--check` exits **0**.
- Expanded record/lead-review subset: **27 tests**, exit **0**;
  `out/c5-phase2/client-decision/record-final.log`.
- Final acceptance coverage: **164 distinct tests** across the six required
  modules, `test_c5_lead_review` and `test_agent_assets`. The combined
  `focused-final.log` run loaded the mounting retirement assertion before
  its last edit: **163 pass, 1 failure, exit 1**, solely
  `test_real_scene_build_approvals_applied_to_single_channel`, which expected
  the removed guest sconce to remain active. All other 137 tests outside
  the mounting module passed; their code and expectations remained unchanged.
- Corrected complete `tests.test_mounting_scene` rerun: **27 tests**,
  exit **0**, OK; `out/c5-phase2/client-decision/mounting-final.log`.
  It now verifies retired fitting absence AND preserved frozen approval
  history, while still checking the retained finite wall-host geometry.
  The two directly affected approval cases also ran separately: **2 tests**,
  exit **0**; `retired-approval-tests.log`. These passing reruns supersede
  the single stale assertion in the combined receipt; no threshold changed.

Current requested test coverage is passing across those executions. The
initial `focused-first.log` failures are retained diagnostic evidence of
pre-decision expectations, not accepted results. The lead runs the full
suite and commits; all work remains uncommitted on `codex/c5p2`.
