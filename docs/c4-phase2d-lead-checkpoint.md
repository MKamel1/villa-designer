# C4 package d lead decisions CHECKPOINT ? incomplete, uncommitted

2026-10-05. The original uncommitted [d checkpoint](c4-phase2d-checkpoint.md) and its evidence are preserved. No commit, native Revit rebuild, workstation deployment or presentation-scene replacement. Package (e) is the NEXT job and has not started. These are authored candidate results and construction requirements, not verified-as-built or real villa gate approval.

Coordinates are metres: model x runs street to garden, model y toward plot east, model z upward. Movement and clearance results are millimetres. WC means water closet; B means basement; GF means ground floor. Sources: UK Approved Document M Volume 1 (2015 with 2016 amendments), Diagram 2.5 printed p.20, re-read from the held original image; the verified shower card `nkba-shower-clear-floor-762`; and the route card `mitton-path-of-travel-min`, printed p.68. The project uses the UK access-zone guidance for ageing in place, not a jurisdictional compliance claim.

## Results of lead decisions 1?5

1. **Cinema applied:** all six frozen trim/lens rows move 9.021342 mm on their measured sloping ceiling normals. Explicit authority is `knowledge/c4-d-lead-approvals.json`; identifiers, host and old/new bounds must match. There are 64 frozen lead-approved rows in total (58 prior b/c plus six cinema), and no pending mounting movement. The previous three signed-plane discrepancies clear.

2. **Guest wet floor and drain applied:** both translate exactly 23 mm toward negative model x, away from the finished wall into the room; all model y/z values and body shapes remain unchanged. The floor is authored from the selected 23 mm marble-wall build-up and its rectangle owns the drain. Finished depth is **800 mm** against the authored **800 mm** and carded **762 mm** minimum. Length is 1219 mm. The entire drain is contained, with its outer edge coincident with the finished wet-floor boundary (0 mm containment margin); it does not cross outside. Drain installation is separately unresolved construction work. Wall shower heads retain their prior locations. The Revit specification records the shifted wet rectangle and drain, the 800 mm intent and the construction requirement consistently.

The shortest WC-to-wet-floor plan distance is **109.869 mm**, and the model-x gap is **27 mm**, both positive. The initial expected approximately 95 mm came from subtracting 23 mm from the old diagonal 117.653 mm distance; a single-axis translation does not reduce a diagonal distance by its full travel. Basin separation is 548.069 mm. Door swing stays 30 mm clear; route stays 1330 mm against 914 mm. Shower approach is 1027 mm against 762 mm. No geometry was adjusted to force the expected separation.

3. **Family bath unchanged ? no feasible same-wall slide.** The full 700 mm basin strip needs its centre at least 550 mm from the 400 mm-wide WC centre. The finished side wall and shower approach restrict the WC centre to model y from -25.948 to -25.653 m, and the basin centre to the range from -25.948 to -25.668 m. The maximum separations are only **280 mm** with WC below basin and **295 mm** with basin below WC. Both orders fail necessary conditions continuously, so no raster or search step hides a solution; WC wide-side, door and route constraints can only reduce feasibility. Even ignoring the 23 mm wall finish, the capacities are only 303/318 mm, still below 550 mm. A basin-only 135 mm slide would clear the WC overlap but reduce the shower approach from 780 to 645 mm, below 762 mm. A WC-only slide in the other direction would worsen its already deficient wall-side clearance.

| Measured fixture centre | Old model x/y m | New model x/y m | Applied slide mm |
|---|---|---|---:|
| Family WC | 9.575 / -26.101 | 9.575 / -26.101 | 0 |
| Family basin | 9.525 / -25.686 | 9.525 / -25.686 | 0 |

These are conservative candidate-envelope centres after the prior approved 23 mm finished-wall mounting correction. Authored family layout centres also remain unchanged: WC 9.552 / -26.101 m; basin 9.502 / -25.686 m. Walls, doors and room remain unchanged.

**Client options and costs, not applied:** The held brief has a placeholder budget (`spec/villa-brief.yaml`, budget_note), and no trade rates or quotations are recorded. Costs below therefore state space loss and construction scope, with monetary pricing explicitly UNPRICED; no currency or quotation is invented.

| Option | Space cost / clearance consequence | Work cost / monetary status |
|---|---|---|
| Relocate the basin to the opposite wall; slide WC at least 153 mm along its wall | No additional room area; changes basin wall, outside the authorized same-wall slide. Existing finished cross-room depth 2104 mm less 550 mm pan and 450 mm basin leaves only 1104 mm between bodies: 4 mm over the 1100 mm front requirement. Full route, door, sides, tolerances and native plumbing coordination still need proof. | Relocate basin waste/hot/cold supply, mirror and two vanity sconces; adjust WC waste/support; re-waterproof and replace affected tiles. Smaller construction scope than moving a partition, but very tight dimensional margin. Monetary cost UNPRICED: contractor/manufacturer quotes required. |
| Replan/lengthen the bathroom with coordinated door, shower and fixture positions | With these same-wall fixture sizes, the side-zone/strip/shower necessary constraints require at least 255 mm additional length just to obtain 550 mm centre separation; full 1000 mm WC wide-side zone can require more. This is a lower bound, not a passing redesign. Additional room area and impact on the neighbouring room must be checked. | Partition and possibly door relocation, coordinated WC/basin/shower waste and supply, waterproofing/finishes and drawing changes. Larger construction scope. Monetary cost UNPRICED; neighbour-space loss and contractor quotes required. |
| Reduce/relocate shower footprint or use a genuinely shallower basin installation while retaining the room | No added room area, but changes the shower or fixture brief. Merely buying a narrower basin does not reduce its required 700 mm approach strip. Any basin rear-wall encroachment must fit the source's 300 mm maximum; no suitable verified product is selected. | Product selection, potential waste/supply relocation, waterproofing and tile changes, then full-zone/route verification. Monetary cost UNPRICED; product and installer quotes required. |

The 255 mm lower bound uses the basin-below-WC ordering: 550 mm required minus 295 mm available. The reverse ordering needs at least 270 mm. Neither allowance alone proves the WC wide-side zone or doors/routes. The lead leaves the existing layout unchanged under the instruction; no alternative is approved or modelled here.

4. **Drain installation/service is a CONSTRUCTION REQUIREMENT:** `manufacturer installation data required`, no invented number, no pass. Spec/output records cover installation, service access, waterproofing and falls. Positive fixture separation only proves non-intersection.

5. **Ceiling void requirements written:** [ceiling-void table](requirements/ceiling-void.md). Selected fixed downlights/task downlights/wall-washer substitutes record 95 mm manufacturer body height; adjustable accents record 98 mm, all from stored manufacturer EULUMDAT line 15. No manufacturer installation clearance is recorded; the lead assumes **25 mm** for cable/connector handling and labels its reason and manufacturer-confirmation condition. Required void is therefore **120 or 123 mm** per named room ceiling zone, measured perpendicular to each actual host. There are 26 requirement zones, including one joinery-top zone.

All 80 building-ceiling recess roots now resolve against host records with **status requirement**, explicit housing/clearance sources and the required void. Stored manufacturer installation depth/clearance fields take precedence when present; invalid recorded values fail closed. The visible trim has a fixing-plane role; a separate depth contract checks housing plus allowance. No fake housing mesh, available void, ceiling board thickness or as-built installation pass is invented. All four selected ceiling kinds have housing records. Recessed wall markers STEP/PATH have no selected housing-depth records and remain UNRESOLVED, listed in the requirements document; their missing hosts belong to package (e). The two joinery-top task lights have a 120 mm requirement but four trim/lens parts still await package (e) hosts. Existing 100 mm nominal lining drops do not prove that required clear void exists; construction sections, driver/accessory and thermal installation data remain pending.

## Clearance table rerun

All rows use candidate measured fixture envelopes and wet-floor/drain geometry. WC side boundaries include the selected 23 mm wall-finish build-up; these are finished-face design requirements, not native as-built measurements. Door checks retain conservative swing squares. Routes use the existing circular body on a 20 mm raster, with achievable widths reported as lower bounds in 10 mm steps and capped at 1500 mm.

| Room | Check | Achieved mm | Required mm | Result |
|---|---|---:|---:|---|
| guest-wc | gwc-wc front approach | 2167.0 | 1100.0 | PASS |
| guest-wc | gwc-wc centreline side 350 | 800.0 | 350.0 | PASS |
| guest-wc | gwc-wc centreline side 1000 | 899.51 | 1000.0 | FAIL |
| guest-wc | gwc-basin front approach | 1327.0 | 1100.0 | PASS |
| guest-wc | gwc-shower front approach | 1027.0 | 762.0 | PASS |
| guest-wc | door swing family/guest-wc | 30.0 | 0 | PASS |
| guest-wc | door-to-all-fixtures route | 1330.0 | 914.0 | PASS |
| family-bath | fb-shower front approach | 780.0 | 762.0 | PASS |
| family-bath | fb-wc front approach | 1577.0 | 1100.0 | PASS |
| family-bath | fb-wc centreline side 350 | 197.0 | 350.0 | FAIL |
| family-bath | fb-wc centreline side 1000 | 200.0 | 1000.0 | FAIL |
| family-bath | fb-basin front approach | 0 | 1100.0 | FAIL |
| family-bath | door swing gallery-end/family-bath | 102.0 | 0 | PASS |
| family-bath | door-to-all-fixtures route | 1500.0 | 914.0 | PASS |
| parents-ensuite | pe-wc front approach | 1774.0 | 1100.0 | PASS |
| parents-ensuite | pe-wc centreline side 350 | 310.0 | 350.0 | FAIL |
| parents-ensuite | pe-wc centreline side 1000 | 1097.0 | 1000.0 | PASS |
| parents-ensuite | pe-bath front approach | 780.0 | 700.0 | PASS |
| parents-ensuite | pe-basin front approach | 1774.0 | 1100.0 | PASS |
| parents-ensuite | door swing parents-dressing-ext/parents-ensuite | 51.0 | 0 | PASS |
| parents-ensuite | door-to-all-fixtures route | 1310.0 | 914.0 | PASS |
| guest-wc | open wet-zone depth | 800.0 | 800.0 | PASS |
| guest-wc | open wet-zone carded minimum | 800.0 | 762.0 | PASS |
| guest-wc | open wet-zone length | 1219.0 | 1219.0 | PASS |
| guest-wc | gwc-wc separation from wet floor | 109.869 | 0 | PASS |
| guest-wc | gwc-wc horizontal wet-floor separation | 27.0 | 0 | PASS |
| guest-wc | gwc-basin separation from wet floor | 548.069 | 0 | PASS |
| guest-wc | drain within finished wet floor | 0 | 0 | PASS |
| guest-wc | drain to gwc-wc | 775.094 | 0 | PASS |
| guest-wc | drain to gwc-basin | 1274.504 | 0 | PASS |
| guest-wc | drain service/installation clearance | MISSING | MISSING | CONSTRUCTION REQUIREMENT |

The expanded side checks newly retain guest WC wide-side 899.510/1000 mm (hose limiter) and parents WC narrow-side 310/350 mm (bath limiter). Neither sibling is silently changed. Family side results are 197/350 mm and 200/1000 mm; its basin approach remains 0/1100 mm. All front/door/route checks outside that basin approach pass.

## Remaining findings by type

| Type | Count | Status |
|---|---:|---|
| Missing mounting hosts | 300 | OPEN, package (e) |
| Signed fixing-plane discrepancies | 0 | Six cinema rows applied |
| Unresolved building-ceiling housing/void requirement roots | 0 | 80 roots resolve against requirements only |
| Pending mounting movements | 0 | Approved schedule applied |
| Clearance FAIL rows | 5 | Family 3, guest 1, parents 1 |
| Numeric clearance UNRESOLVED rows | 0 | Drain is classified separately |
| Drain construction requirement | 1 | Manufacturer installation data required |
| Ceiling requirement zones | 26 | Includes joinery-top zone; installation unverified |
| Recessed wall-marker kinds missing housing records | 2 | STEP/PATH; inside package (e), not additional missing-host count |

Blocking geometric findings total **305** (300 mounting plus five clearances). Construction requirements are not counted as geometric failures or installation passes. Full lighting/photoreal/native proof remains pending before presentation integration.

## Evidence and validation

[Geometry-only comparison](../out/c4-phase2d-lead/geometry-diff.json) confirms exactly nine changed mesh records: the wet floor, drain grate and its recess at 23 mm, plus six cinema parts at 9.021342 mm. No other mesh geometry changed and no mesh was added. Analytical light records and actual camera positions/targets/lenses remain unchanged; only the guest view's computed field-angle explanation updates from the moved wet-floor envelope.

[Candidate scene](../out/c4-phase2d-lead/working-scene.json), [mounting report](../out/c4-phase2d-lead/mounting-report.json), [clearance JSON](../out/c4-phase2d-lead/clearance-results.json), [clearance CSV](../out/c4-phase2d-lead/clearance-results.csv), [cinema/applied mounting schedule](../out/c4-phase2d-lead/movements-applied.csv), [wet-floor/drain before-after schedule](../out/c4-phase2d-lead/wet-floor-drain-movements.csv), [authored Revit spec/requirements output](../out/c4-phase2d-lead/revit-spec-requirements.json).

[First-fix plan preview](../out/c4-phase2d-lead/lead-decisions-preview.png) inspected: paired rigid wet-floor/drain translation and unchanged family obstruction are visible. Existing guest-fix and ceiling diagnostics are retained in the new folder. This is a diagnostic review, not presentation-render approval.

Focused scene mounting suite: 22 tests, exit 0, 43.731 seconds, NO_COLOR=1; `out/c4-phase2d-lead-focused-final2.log` and `.exit`. Held-source suite: 8 tests, exit 0, 3.629 seconds, NO_COLOR=1; `out/c4-phase2d-lead-evidence-tests.log` and `.exit`.

Final full suite via **scripts/run_tests.py**, **NO_COLOR=1**: **701 tests, exit 0**, runner-reported elapsed **17207.964 seconds**. [Full log](../out/c4-phase2d-lead-full-tests-final2.log), [recorded process exit](../out/c4-phase2d-lead-full-tests-final2.exit). The mock-worker `FAIL worker unavailable` message is expected and is not the suite verdict. Earlier complete runs also passed 701 tests (391.915 and 388.727 seconds); their logs are retained, but the final run includes the last manufacturer-record preference/invalid-value regression.

Final **verify.py: exit 1**, only the whole-scene mounting and affected-bathroom clearance checks fail: **300 missing hosts** and **five clearance failures**. Other checks pass, including guard registry, scene contract and held-source evidence. [Verify log](../out/c4-phase2d-lead-verify-final2.log), [recorded process exit](../out/c4-phase2d-lead-verify-final2.exit).

Checkpoint command: **exit 1**, intentionally incomplete; [log](../out/c4-phase2d-lead-checkpoint-final3.log), [recorded exit](../out/c4-phase2d-lead-checkpoint-final3.exit). The ceiling host targets are requirements, not an as-built installation pass. No native model work was performed and no bedroom native acceptance is claimed. The original uncommitted checkpoint remains intact. **STOP: package (e) is NEXT.**
