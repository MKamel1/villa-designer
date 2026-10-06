# C4 phase 2 approved b/c and package d CHECKPOINT - incomplete, uncommitted

Updated 2026-10-05. No commit, native Revit rebuild, workstation deployment,
or replacement of `out/villa/render-d1/scene.json` was made. The uncommitted
[prior checkpoint](c4-phase2bc-checkpoint.md) and all its original schedules
remain intact. Current resume command: `scripts/checkpoint_mounting_d.py`.
This is candidate geometry evidence, not presentation or real design approval.

All coordinates are metres: model x runs street to garden, model y toward
plot east, model z upward. Millimetres are used for movement and clearance
results. Bounds schedules give minimum x/y/z, then maximum x/y/z.

All **58 approved schedule rows applied**, including 16 finished-face records.
The explicit authored authority in `knowledge/c4-bc-approvals.json` checks
identifier, host and old/new bounds before application; drift fails closed.
The original `out/c4-phase2bc/movements-over-5mm.csv` is preserved.

The stair remains unchanged from its previous approved checkpoint: all 22
wall-side components pass signed-plane and finite-host guards.

## Three guest fixes

- Handset: scheduled assembly translation is 23 mm toward model negative x.
  It leaves the recorded 8 mm burial. The separately authorized rigid 23 mm
  correction applies after it: **46 mm total from the frozen original**, with
  **15 mm achieved signed body clearance**. Height and body shape are retained.
- Hose: regenerated hanging spatial curve from the corrected handset connection
  to the existing riser outlet. Both connections retained by value. Radius is
  **6 mm**; additional **2 mm assumed design clearance**. Every centreline point
  is at least radius plus clearance from the finished face; tube vertices are
  independently checked. **24.263 mm achieved minimum tube-surface clearance**.
  The curve hangs into the room, without flattening against the wall.
- Sconce 03: slides **99 mm toward positive model y**, on its own wall, with
  unchanged height and normal. Its conservative **120 mm fixing envelope**
  has a **5 mm assumed edge margin**. The procedural globe has no separate
  measured product back plate; its full tangent body envelope is used rather
  than a single sphere tangent vertex. Product back-plate data remains unverified.

Frozen pre-fix proposal: **five guard findings**. Corrected three-component
subset: **zero findings**. Tests preserve the rigid handset shape and prove
hose-endpoint, hose-burial and sconce-footprint mutations fire. Unrelated wall
orientations demonstrate the hose construction generalises.

First-fix previews generated and inspected:
[guest corrections](../out/c4-phase2d/guest-fixes-preview.png),
[ceiling fixing sections](../out/c4-phase2d/ceiling-preview.png).
These are measured diagnostic diagrams. Neutral-light photoreal preview,
independent lighting probes and native coordination remain pending before
presentation integration. The analytical/rendered lighting verdict is unverified
following the approved fitting/emitter changes; no lighting pass is claimed.
Light-source records retain the pre-move analytical positions. Propagating
approved emitter translations into analytical inputs and proving them with
independent rendered probes is pending before presentation/probe integration.

## Clearance and route results

Measured sanitary displacement and full assembly bounds feed conservative
furniture envelopes. All room approaches use the moved geometry, with actual
projecting shower parts and finished-wall strips as route obstacles. Basins
use the source's **700 mm approach width**. Existing door-swing squares are
retained. Routes use the existing circular path body on a **20 mm raster**;
achievable widths are lower bounds in **10 mm steps**, capped at 1500 mm.

Depths for WC (water closet), basin and bath access follow UK Approved Document
M Volume 1 (2015, incorporating 2016 amendments), Diagram 2.5, printed p.20,
re-read from the held original page image. This is the project's ageing-in-place
guidance, not jurisdictional compliance. Shower approach uses the verified
NKBA (National Kitchen & Bath Association) card from its 2016 guidelines,
printed p.5; routes use Mitton, Residential Interior Design, fourth edition,
2022, printed p.68. Project wet-floor dimensions and geometric non-overlap
requirements are separately labelled assumptions/design conditions.

| Room | Check | Achieved mm | Required mm | Result |
|---|---|---:|---:|---|
| guest-wc | gwc-wc front approach | 2167 | 1100 | PASS |
| guest-wc | gwc-basin front approach | 1327 | 1100 | PASS |
| guest-wc | gwc-shower front approach | 1050 | 762 | PASS |
| guest-wc | door swing family/guest-wc | 30 | 0 | PASS |
| guest-wc | door-to-all-fixtures route | 1330 | 914 | PASS |
| family-bath | fb-shower front approach | 780 | 762 | PASS |
| family-bath | fb-wc front approach | 1577 | 1100 | PASS |
| family-bath | fb-basin front approach | 0 | 1100 | FAIL |
| family-bath | door swing gallery-end/family-bath | 102 | 0 | PASS |
| family-bath | door-to-all-fixtures route | 1500 | 914 | PASS |
| parents-ensuite | pe-wc front approach | 1774 | 1100 | PASS |
| parents-ensuite | pe-bath front approach | 780 | 700 | PASS |
| parents-ensuite | pe-basin front approach | 1774 | 1100 | PASS |
| parents-ensuite | door swing parents-dressing-ext/parents-ensuite | 51 | 0 | PASS |
| parents-ensuite | door-to-all-fixtures route | 1310 | 914 | PASS |
| guest-wc | open wet-zone depth | 777 | 800 | FAIL |
| guest-wc | open wet-zone length | 1219 | 1219 | PASS |
| guest-wc | gwc-wc separation from wet floor | 117.653 | 0 | PASS |
| guest-wc | gwc-basin separation from wet floor | 570.219 | 0 | PASS |
| guest-wc | drain within finished wet floor | -23 | 0 | FAIL |
| guest-wc | drain to gwc-wc | 797.573 | 0 | PASS |
| guest-wc | drain to gwc-basin | 1297.19 | 0 | PASS |
| guest-wc | drain service/installation clearance | MISSING | MISSING | UNRESOLVED |

**Findings retained; no redesign applied:**
- Family basin: the 700 mm-wide approach strip intersects the WC. Clear
  depth over the entire required strip is 0 mm, where 1100 mm is required.
  This wider-zone obstruction also exists before the approved translation;
  it is a newly exposed limitation of the earlier body-width check.
- Guest finished wet-floor depth is 777 mm against the authored 800 mm.
- The guest drain crosses the finished wet-floor boundary by 23 mm.
- Drain service/installation minimum is missing. Positive drain-to-fixture
  separations establish only non-intersection, not service clearance or
  drainage design. No verified splash-distance minimum exists in this check.
- WC side-access/turning-space, fixing capacity, plumbing/falls and full native
  coordination are outside this limited existing clearance/route rerun.

Complete per-row authority and limiting obstacle:
[clearance CSV](../out/c4-phase2d/clearance-results.csv),
[clearance report](../out/c4-phase2d/clearance-results.json).
`verify.py` runs this review unconditionally; the design findings keep it red.

## Package d: recessed and surface ceiling fittings

**200 additional components** declare measured finite finished-ceiling hosts.
Existing b/c rain-head drops/heads/nozzles and extract valves retain their
finished-ceiling contracts. Surface pendant canopies and suspension parts
bind to actual finished datums; ramp batten bracket upper ends follow their
own sloping soffit. Body levels are retained. Signed fixing coordinates use
all components of the actual host normal, avoiding horizontal-height shortcuts.

**194 movement rows applied at 5 mm or less**, including zero movements.
**80 recessed fitting roots are UNRESOLVED**: housing depth and clear ceiling
void are both MISSING. Decorative trim thickness and emitter elevation are
not housing evidence. `knowledge/finish-build-ups.json` remains unchanged:
ceiling build-up UNVERIFIED, clear void MISSING. These records are never passed.
No invented board thickness or void is assigned.

The nook's two downlights mount in its actual joinery top, not the building
ceiling. Their four trim/lens parts remain missing hosts for package e.

**Six movements awaiting approval:**

| Component | Proposed movement mm | Host |
|---|---:|---|
| fix-WW-cinema-03 | 9.021342 | ceiling-WW-cinema-03 |
| lens-WW-cinema-03 | 9.021342 | ceiling-WW-cinema-03 |
| fix-WW-cinema-04 | 9.021342 | ceiling-WW-cinema-04 |
| lens-WW-cinema-04 | 9.021342 | ceiling-WW-cinema-04 |
| fix-WW-cinema-05 | 9.021342 | ceiling-WW-cinema-05 |
| lens-WW-cinema-05 | 9.021342 | ceiling-WW-cinema-05 |

All six belong to the three cinema wall-washers on the sloping soffit. Working
meshes retain their original vertices. Three lens signed-plane findings remain
at -9.021 mm; recess roots independently remain unknown-depth findings.
The separate proposal clears those three lens discrepancies while retaining
all missing housing/void findings.

Whole-scene mounting result: **383 findings = 300 missing hosts + 80 unresolved
recess roots + 3 pending lens plane discrepancies**. The **300 missing hosts**
are the actual whole-scene count; package e remains to do, including furniture,
joinery/TV/shelves, support parts, trellis/climbers, curtain tracks, markers,
joinery-recessed lights and associated items. It is not a count inferred from
one package's size. The broader phase and real villa design gates remain open. Stop here; package e is not started.

Evidence:
[working candidate](../out/c4-phase2d/working-scene.json),
[separate proposal](../out/c4-phase2d/proposed-scene.json),
[mounting report](../out/c4-phase2d/mounting-report.json),
[applied schedule](../out/c4-phase2d/movements-applied.csv),
[pending schedule](../out/c4-phase2d/movements-awaiting-approval.csv).

## Validation

First focused mounting suite: **25 tests, exit 0**, 35.764 seconds,
`NO_COLOR=1`. After the full-suite scene-contract finding, the focused
regression also validates all scene labels, the frozen real failure and
batten-host sibling. Final focused suite: **25 tests, exit 0**, 36.043 seconds, `NO_COLOR=1`.
Log: `out/c4-phase2d-focused-final3.log`; process status:
`out/c4-phase2d-focused-final3.exit`.

First full suite: **699 tests, exit 1**, two failures in the render contract
(missing labels on 99 diagnostic ceiling host meshes). Both failures share
one constructor omission, now corrected. The frozen actual reproduction
and a stripped-label batten sibling prove the guard fires; the corrected
candidate passes the complete scene contract. Earlier log retained at
`out/c4-phase2d-full-tests.log`. Final full suite via `scripts/run_tests.py`: **699 tests, exit 0**,
379.203 seconds, `NO_COLOR=1`. Final log:
`out/c4-phase2d-full-tests-final.log`; recorded process exit:
`out/c4-phase2d-full-tests-final.exit`. The mock worker test prints
`FAIL worker unavailable` as expected; it is not the suite verdict.
The corrected final run includes the required scene-contract proof.

`verify.py`: **exit 1**, only the whole-scene mounting and affected-clearance
checks fail. It reports all 383 mounting findings and the three clearance
failures plus one missing drain requirement. Its other checks pass.
Log: `out/c4-phase2d-verify-final3.log`; process status: `out/c4-phase2d-verify-final3.exit`.

Checkpoint command: **exit 1**, intentionally unresolved. Final candidate
exports carry the existing complete view set and pass the scene contract;
these are candidate records, not rendered or deployed presentation views.
Log: `out/c4-phase2d-checkpoint-final3.log`. The guest correction
guards clear; the larger cinema moves, recess unknowns, clearance defects and
missing hosts remain reported. No commit was made.
