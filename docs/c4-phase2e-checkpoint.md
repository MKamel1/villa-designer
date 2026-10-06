# C4 package (e) CHECKPOINT ? incomplete, uncommitted

2026-10-05. Continued from [the retained lead checkpoint](c4-phase2d-lead-checkpoint.md). No commit, native rebuild, workstation deployment or presentation-scene replacement. The original uncommitted checkpoints remain intact. These are authored candidate results, not verified-as-built installation or real villa gate approval.

Coordinates are metres: model x runs street to garden, model y toward plot east, model z upward. Movements and clearance tables use millimetres. WC means water closet; B means basement; GF means ground floor. CSV means comma-separated values. The same held cards remain authoritative: UK Approved Document M Volume 1 (2015 with 2016 amendments), Diagram 2.5 printed p.20; `nkba-shower-clear-floor-762`; and `mitton-path-of-travel-min`, Mitton printed p.68. This is the existing ageing-in-place guidance scope, not a jurisdictional compliance claim.

## Authorized same-wall WC slides

Both slides are feasible and APPLIED under the explicit lead authority, separately from the 5 mm mounting limit. They retain the WC wall, normal, height, rotation and rigid body geometry. Exact piecewise side-zone events consider both handednesses; every candidate then reruns the full measured front/side, wet-zone, door and route review. Neither basin, bath, shower, door nor wall is relocated.

| Fixture | Old measured centre x / y, m | New measured centre x / y, m | Applied movement |
|---|---|---|---|
| gwc-wc | 10.100000000 / -21.099000000 | 9.999509862 / -21.099000000 | 100.490138 mm; negative model x |
| pe-wc | 21.851000000 / -30.051000000 | 21.851000000 / -30.011000000 | 40.0 mm; positive model y |

Guest front approach reduces from 2167 to 1476 mm when the moved WC frontage meets the basin as its limiter; it still exceeds 1100 mm. Guest wide-side becomes exactly 1000 mm, with 699.510 mm on the other side. Parents narrow-side becomes exactly 350 mm, with 1057 mm on the other side; route lower bound changes from 1310 to 1290 mm against 914 mm. These exact boundary values have no construction tolerance reserve; native coordination must preserve the full carded dimensions.

All clearances are reported below. Routes retain the existing 20 mm raster, circular body and lower-bound widths in 10 mm steps; door swings retain conservative squares. No numeric drain installation minimum is invented.

| Room | Check | Before mm | After mm | Required mm | Status |
|---|---|---:|---:|---:|---|
| guest-wc | gwc-wc front approach | 2167.0 | 1476.0 | 1100.0 | PASS |
| guest-wc | gwc-wc centreline side 350 | 800.0 | 699.51 | 350.0 | PASS |
| guest-wc | gwc-wc centreline side 1000 | 899.51 | 1000.0 | 1000.0 | PASS |
| guest-wc | gwc-basin front approach | 1327.0 | 1327.0 | 1100.0 | PASS |
| guest-wc | gwc-shower front approach | 1027.0 | 1027.0 | 762.0 | PASS |
| guest-wc | door swing family/guest-wc | 30.0 | 30.0 | 0 | PASS |
| guest-wc | door-to-all-fixtures route | 1310.0 | 1330.0 | 914.0 | PASS |
| family-bath | fb-shower front approach | 780.0 | 780.0 | 762.0 | PASS |
| family-bath | fb-wc front approach | 1577.0 | 1577.0 | 1100.0 | PASS |
| family-bath | fb-wc centreline side 350 | 197.0 | 197.0 | 350.0 | FAIL |
| family-bath | fb-wc centreline side 1000 | 200.0 | 200.0 | 1000.0 | FAIL |
| family-bath | fb-basin front approach | 0 | 0 | 1100.0 | FAIL |
| family-bath | door swing gallery-end/family-bath | 102.0 | 102.0 | 0 | PASS |
| family-bath | door-to-all-fixtures route | 1310.0 | 1500.0 | 914.0 | PASS |
| parents-ensuite | pe-wc front approach | 1774.0 | 1774.0 | 1100.0 | PASS |
| parents-ensuite | pe-wc centreline side 350 | 310.0 | 350.0 | 350.0 | PASS |
| parents-ensuite | pe-wc centreline side 1000 | 1097.0 | 1057.0 | 1000.0 | PASS |
| parents-ensuite | pe-bath front approach | 780.0 | 780.0 | 700.0 | PASS |
| parents-ensuite | pe-basin front approach | 1774.0 | 1774.0 | 1100.0 | PASS |
| parents-ensuite | door swing parents-dressing-ext/parents-ensuite | 51.0 | 51.0 | 0 | PASS |
| parents-ensuite | door-to-all-fixtures route | 1310.0 | 1290.0 | 914.0 | PASS |
| guest-wc | open wet-zone depth | 800.0 | 800.0 | 800.0 | PASS |
| guest-wc | open wet-zone carded minimum | 800.0 | 800.0 | 762.0 | PASS |
| guest-wc | open wet-zone length | 1219.0 | 1219.0 | 1219.0 | PASS |
| guest-wc | gwc-wc separation from wet floor | 109.869 | 166.12 | 0 | PASS |
| guest-wc | gwc-wc horizontal wet-floor separation | 27.0 | 127.49 | 0 | PASS |
| guest-wc | gwc-basin separation from wet floor | 548.069 | 548.069 | 0 | PASS |
| guest-wc | drain within finished wet floor | -0.0 | -0.0 | 0 | PASS |
| guest-wc | drain to gwc-wc | 775.094 | 873.505 | 0 | PASS |
| guest-wc | drain to gwc-basin | 1274.504 | 1274.504 | 0 | PASS |
| guest-wc | drain service/installation clearance | MISSING | MISSING | MISSING | CONSTRUCTION REQUIREMENT |

## Family bath: client decision, unchanged

No same-wall slide exists. WC sides remain 197/350 mm and 200/1000 mm; basin frontage remains 0/1100 mm. Continuous necessary constraints still allow only 280/295 mm separation where 550 mm is needed. All existing family-bath mesh geometry is unchanged, including its shower; the 2 mm tray penetration relative to the modeled finished floor is declared geometrically with installation requirements, not moved. [Same-view geometry comparison](../out/c4-phase2e/geometry-diff.json) records zero changed family meshes.

The earlier client options and cost table are retained without applying an alternative. The held budget and trade rates remain unpriced.

| Option | Space cost / clearance consequence | Work cost / monetary status |
|---|---|---|
| Relocate the basin to the opposite wall; slide WC at least 153 mm along its wall | No additional room area; changes basin wall, outside the authorized same-wall slide. Existing finished cross-room depth 2104 mm less 550 mm pan and 450 mm basin leaves only 1104 mm between bodies: 4 mm over the 1100 mm front requirement. Full route, door, sides, tolerances and native plumbing coordination still need proof. | Relocate basin waste/hot/cold supply, mirror and two vanity sconces; adjust WC waste/support; re-waterproof and replace affected tiles. Smaller construction scope than moving a partition, but very tight dimensional margin. Monetary cost UNPRICED: contractor/manufacturer quotes required. |
| Replan/lengthen the bathroom with coordinated door, shower and fixture positions | With these same-wall fixture sizes, the side-zone/strip/shower necessary constraints require at least 255 mm additional length just to obtain 550 mm centre separation; full 1000 mm WC wide-side zone can require more. This is a lower bound, not a passing redesign. Additional room area and impact on the neighbouring room must be checked. | Partition and possibly door relocation, coordinated WC/basin/shower waste and supply, waterproofing/finishes and drawing changes. Larger construction scope. Monetary cost UNPRICED; neighbour-space loss and contractor quotes required. |
| Reduce/relocate shower footprint or use a genuinely shallower basin installation while retaining the room | No added room area, but changes the shower or fixture brief. Merely buying a narrower basin does not reduce its required 700 mm approach strip. Any basin rear-wall encroachment must fit the source's 300 mm maximum; no suitable verified product is selected. | Product selection, potential waste/supply relocation, waterproofing and tile changes, then full-zone/route verification. Monetary cost UNPRICED; product and installer quotes required. |

Neither successful WC slide needs a client fallback option. The family decision remains with the client.

## Package (e): hosts and bounded corrections

**Zero missing hosts:** all 300 original sites now bind to declared finite sources. Their host kinds are 206 floor, 56 joinery panel, 28 wall and 10 ceiling. Mount contracts comprise 202 floor-standing assembly records, 80 surface-mounted fixing records, 12 wall-hung child records and six recessed records. Generated furniture children retain a named independent floor-bearing root and generated projection; they are not individually asserted to touch the floor. Rails identify their supporting brackets. These relationships prove necessary geometric support only, not fastener or load capacity.

The scene contains 271 host records. Of the original 300 sites, 201 have applied movements at most 5 mm, 49 retain original geometry awaiting approval, and 50 gain bindings with unchanged geometry. There are also 10 pending diagnostic finish-face movements. The same-view comparison records 205 changed original meshes overall: those 201 small corrections plus four mesh parts in the two authorized WC assemblies. Cameras and their targets/lenses are unchanged.

No selected floor thickness exists in `knowledge/finish-build-ups.json`. Floor-standing roots use their actual modeled finished floor level: usually 0.002 m at ground floor and -2.998 m in basement rooms; stair storage uses the actual -3.000 m basement stair datum. Oak 15 mm plus 2?3 mm underlay is **UNVERIFIED and not added**. The two pantry shelves use exact full-span floor edges instead of their previously rounded centres: each shifts -0.5 mm in model y and +2 mm vertically, a 2.061553 mm total movement.

The two nook downlight roots bind to the actual underside of the daybed joinery top (`furn-library-daybed-0`), not the building ceiling. Their four trim/lens parts preserve relative geometry. Each host carries the existing 95 mm recorded housing plus the labelled 25 mm installation allowance: 120 mm construction void requirement, not available/as-built void. Five desk-light assemblies move with their tables; together with the two nook lights there are seven carried analytical emitter records. Photometric intensities are unchanged. Thirty-seven associated imported-model, cloth and prop records follow applied furniture corrections. Independent lighting remeasurement remains for the lead before integration.

The six wall-marker hosts resolve against real wall faces, including the already declared stair party-wall finish. Their surface-mounted contracts check the visible fixing face only. Actual recessed STEP/PATH housing depth, recess construction, installation clearance and product selection remain **UNRESOLVED construction requirements**; no housing or available void is fabricated. Drain and wet-floor depth contracts describe existing mesh penetration only; manufacturer installation, falls and waterproofing remain requirements.

## Movements awaiting approval

**59 rows: 49 original items and 10 diagnostic finish faces. None is applied.** Full identifiers, host, old/new bounds, displacement, reason and status are in [movements-over-5mm.csv](../out/c4-phase2e/movements-over-5mm.csv). Approved WC slides are separate in [wc-slides.csv](../out/c4-phase2e/wc-slides.csv).

| Pending group | Rows including diagnostic faces | Maximum corresponding-vertex movement mm |
|---|---:|---|
| TV fluting / headboard slats and their finish faces | 4 | 13 |
| Lounge / study TV assemblies and wall finish faces | 6 | 13 |
| Open-side stair stringer floor bearing | 1 | 33.529412 |
| Dressing rail brackets | 10 | 6 or 14 |
| Coffee appliance bodies | 2 | 10 |
| Dirty-kitchen hood and wall finish face | 2 | 13 |
| Guest / dirty-kitchen vent grilles and finish faces | 4 | 223 / 213; finish faces 23 / 13 |
| Four trellises, branches and climber forms | 12 | east 113; south 9450.320; north 191; west 177 |
| Six wall-marker faces and three new corridor finish faces | 9 | markers 12; finish faces 13 |
| Eight cabinet shelf-light strips | 8 | 8 |
| Parents second curtain-track end overrun | 1 | 30, tangential to the existing ceiling |

The south trellis is 9.450320 m from its actual boundary wall. The other three are embedded in the boundary faces. Hosts explicitly identify the actual fence-rear/fence-west/fence-east/fence-street sources; no wall is inserted at a trellis and no remote gap becomes an invented mounting projection. Review the planting brief and support design before authorizing a south relocation. Dressing bracket proposals also require review together with their rails. The stringer proposal requires structural bearing/landing coordination; this is not structural approval.

Applying the entire pending proposal still leaves three finite-coverage findings: the headboard slats extend 47 mm beyond the selected wall patch, while the hood and dirty-kitchen grille project onto an adjacent column-sized wall patch rather than a full supporting wall face. **A blanket approval of the translations will not resolve those three.** Coordinate their real wall extent/support or replan their placement first; do not extend a wall to hide them. All three remain unapplied, in the approval schedule and raw findings.

## Verification, focused tests and previews

`verify.py` ran exactly once, at the end: **exit 1**. Only two checks fail: whole-scene mounting and affected bathroom clearances. All other checks pass, including guard registry, scene contract and held evidence. [Verify log](../out/c4-phase2e-verify.log), [exit](../out/c4-phase2e-verify.exit).

| Finding type | Count | Disposition |
|---|---:|---|
| Missing hosts | 0 | Goal reached |
| Signed fixing-plane discrepancies | 48 | All identified pending approval items |
| Finite host coverage findings | 49 | All identified pending approval items |
| Unexplained mounting findings | 0 | None |
| Client-decision clearance failures | 3 | Unchanged family bath |
| Numeric clearance unresolved rows | 0 | None |
| Pending movement rows | 59 | Unapplied, schedule supplied |

The 97 mounting messages are multiple geometric findings on pending items, not 97 missing hosts. Construction installation requirements are retained separately; they are not numeric geometry passes.

| Focused command | Tests | Process exit | Evidence |
|---|---:|---:|---|
| `scripts/run_focused_tests.py test_mounting_scene test_support_mounting` ? initial run | 26; mounting 22 passed, support 3/4 passed | 1 | [log](../out/c4-phase2e-focused.log), [exit](../out/c4-phase2e-focused.exit) |
| `scripts/run_focused_tests.py test_support_mounting` ? final expanded module | 5 passed | 0 | [log](../out/c4-phase2e-support-final.log), [exit](../out/c4-phase2e-support-final.exit) |

Initial failure was an ordinal shell-identifier comparison across different opened-door view sets; it matched the guest door with the family door. The regression now uses stable authored fixture/floor identifiers. The independent actual same-view geometry comparison proves every existing family mesh remains unchanged. No production code changed after the initial focused run; the final module adds translated pantry/boundary sibling proof. The 22 existing mounting tests all passed; 27 distinct final tests have passing evidence across these focused runs. **No full suite was run; the lead runs it.**

Checkpoint command: **exit 1**, intentionally incomplete with approval/client findings. [Log](../out/c4-phase2e-checkpoint.log), [exit](../out/c4-phase2e-checkpoint.exit). First-fix diagnostic images were generated and visually inspected: [support preview](../out/c4-phase2e/support-first-fix-preview.png), [WC-slide plan preview](../out/c4-phase2e/wc-slides-preview.png). They show the floor datum, joinery underside contact, retained south mismatch and marker-wall offset, plus both rigid WC slides. They are not neutral-light photoreal acceptance.

Proofs cover frozen missing sites, independent root/child mutation, absent finite floor contact, 5/5.001 mm movement threshold, translated full-span shelf placement, retained real boundary mismatch, removed support brackets, undersized nook voids, full successful WC tables and unchanged family geometry. Learning index, guard registry and mounting workflow were updated together. The focused runner requires explicit test module names and reuses the managed-Windows accessible temporary-directory adapter.

## Views for the lead

Render small neutral-light diagnostic packages first, with the working (unapproved) geometry clearly labelled.

| Review area | Existing views |
|---|---|
| Authorized WC slides and unchanged client bathroom | `v16-guest-wc`, `v12-ensuite`, `v15-family-bath` |
| Nook top / shelf lighting and library support | `v24-bar-alcove` |
| TV / feature-panel hosts, table lamp and parent furniture | `v03-street-lounge`, `v04-study-deck`, `v05-parents-bedroom` |
| Appliance/grille support and kitchen floor roots | `v17-dirty-kitchen`, `v20-kitchen-run` |
| Open stringer, wall markers and storage supports | `v11-stair-void`, `v23-gf-gallery`, `v29-under-stair-store`, `v30-under-ramp-store` |
| Dressing panels, shelves and rail brackets | `v31-dressing-hers`, `v32-dressing-his` |
| Boundary overlaps and south location | `v27-north-garden-above`, `v28-north-garden-below`, plus isolated close-ups of all four trellis-to-boundary relationships; the 9.45 m south separation needs a plan/section diagnostic |

After those reviews/approval corrections, render all affected interior views for the 201 small furniture/support changes, including dining, living and both children?s rooms. Run independent analytical/rendered lighting probes for the seven moved emitter assemblies before presentation integration. Native model/read-back and housing/installation coordination remain pending; no bedroom native acceptance is claimed.

Evidence: [working scene](../out/c4-phase2e/working-scene.json), [separate proposal](../out/c4-phase2e/proposed-scene.json), [mounting report](../out/c4-phase2e/mounting-report.json), [full clearance CSV](../out/c4-phase2e/clearance-results.csv), [applied mounting schedule](../out/c4-phase2e/movements-applied.csv), [geometry comparison](../out/c4-phase2e/geometry-diff.json).

**STOP: package (e) checkpoint delivered; uncommitted.**
