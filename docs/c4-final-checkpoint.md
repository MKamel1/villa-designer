# C4 final lead decisions: CHECKPOINT, uncommitted

2026-10-05. Continued from [package f](c4-phase2f-checkpoint.md), retained unchanged. No commit, full suite, native rebuild, workstation deployment or presentation integration. The lead runs the full suite and render review. These are authored candidate results, not installation proof or real villa gate approval.

Coordinates are metres: model x runs street to garden, model y toward plot east, and model z upward. Widths, movements and clearance values below are millimetres. WC means water closet. The exterior direction suffixes retain package-f meanings. The 10 mm headboard margin and approved movements are lead decisions, not published standards.

## Applied final decisions

All **14 package-f pending rows** are applied against frozen old/new bounds and host identifiers in [final authority](../knowledge/c4-final-approvals.json). Any schedule drift refuses the complete final approval package before applying a row. The twelve trellis/branch/climber rows retain their shapes and common assembly displacement: east 113 mm, west 177 mm, north 191 mm and south 135.660 mm. Both grilles move 12 mm outdoors; their rear fixing face now sits at the modeled exterior face. No wall or finish thickness is invented. The south polygon edge still has no modeled wall solid, and its construction/fixing capacity remains unverified.

The parents' decorative slatted headboard is **1,980 mm before, 1,586 mm after**. Its original centre was offset from the bed. The replacement width is symmetric about the unchanged bed centreline at model x 20.330 m. Its left end is x 19.537 m, **10 mm short** of the actual full-height wall end at x 19.527 m; its right end is x 21.123 m. Bed geometry and position remain unchanged. Only the decorative panel's width coordinates change; wall geometry, height and mounting depth are retained.

Each coffee assembly lifts **12 mm from the retained package-f pose**, carrying its body, tray, spout and water tank rigidly. The lowest complete assembly part defines the worktop fixing plane; the original shapes and generated relative positions are retained. Bodies no longer pretend their own lower housing plane is the complete assembly support. Builder-declared ownership now binds all six coffee children and the hood chimney. `attached_assembly.translate` carries the root and children once during explicit approvals, final seating and automatic small corrections. An unconditional relative-position check reports split movements. The regression freezes actual package-f parts, injects parent-only moves, exercises both coffee machines and the hood, and translates/renames clean and mutated siblings.

The [final decisions and vertex proof](../out/c4-final/final-decisions.json) records the headboard dimensions and every coffee-part displacement. [Final coffee seating schedule](../out/c4-final/final-assembly-movements.csv) is the correction after the historical approved translations in [applied schedule](../out/c4-final/movements-applied.csv). There are **zero pending movements**; the pending schedule contains its header only.

## Verification and remaining findings

Authoritative [delivery verify log](../out/c4-final-verify-delivery.log), [exit](../out/c4-final-verify-delivery.exit): **exit 1; 124 passing checks; only the bathroom-clearance check fails**, with exactly these three family-bath rows. No other `verify.py` failure remains.

| Family-bath finding | Achieved | Required |
|---|---:|---:|
| WC narrow centreline side | 197 mm | 350 mm |
| WC wide centreline side | 200 mm | 1,000 mm |
| Basin front approach | 0 mm | 1,100 mm |

The next client job is the WC on the east wall. The family layout is unchanged here. Working/proposed mounting findings, missing hosts, signed-plane errors, finite coverage errors, child support penetrations and unresolved numeric clearance rows are all **zero**. See [mounting report](../out/c4-final/mounting-report.json) and [clearance table](../out/c4-final/clearance-results.csv). The [comparison with package f](../out/c4-final/geometry-diff-from-f.json) records exactly **23 changed meshes**, **zero changed family-bath meshes**, and **unchanged cameras**.

A separate focused render regression still reports a historical support-datum issue: `test_indoor_plants_have_integrated_pots_floor_support_and_clear_tv` checks lounge-plant, living-plant-table, living-plant, bedroom-plant and study-plant against pre-migration levels. Every plant differs by +2 mm from that old datum. Their measured candidate bases are respectively -2.998, -2.598, -2.998, +0.002 and +0.002 m; the legacy check expects -3.000, -2.600, -3.000, 0.000 and 0.000 m. The [before/after reproduction](../out/c4-final-indoor-plant-baseline.json) gives the same five messages in package f and the final candidate. This is **OPEN**, separately captured in LEARNINGS. No plant was lowered and no tolerance or check was suppressed. It does not appear as a `verify.py` failure; the focused render module is not wholly passing.

## Focused tests and exits

All commands used the project `.venv/Scripts/python.exe` from the project working directory, with explicit modules through `scripts/run_focused_tests.py`. No discovery/full suite.

| Focused modules / command | Result | Process exit |
|---|---|---:|
| Final mounting, latest five regressions | 5 passed; [log](../out/c4-final-assembly-delivery.log) | 0 |
| Support + exterior mounting | 10 passed; [log](../out/c4-final-support-exterior.log) | 0 |
| Mounting scene | 22 passed; [log](../out/c4-final-mounting-scene.log) | 0 |
| Render standard | 54 passed, one historical plant-datum failure; [log](../out/c4-final-render-standard.log) | 1 |
| Candidate checkpoint | Only the three retained family-bath rows; [log](../out/c4-final-checkpoint.log) | 1 |
| Delivery `verify.py` | Only the three retained family-bath rows | 1 |

**37 distinct core mounting tests pass across the three passing processes.** The render-standard module additionally passes 54 tests and retains one historical test failure.

Failed attempts are retained: `c4-final-focused-first-fix` captures the invalid positive-offset surface contract and the earlier support-only mutation expectation. `c4-final-focused-before-final-expectation` retains the now-obsolete assertion that the whole scene must contain mounting findings. `c4-final-mounting-scene-first` captures a standalone package call without a scene mesh inventory; child lookup now preserves that existing API. `c4-final-render-standard-first` retains the old inward grille-face expectation and historical plant-datum failure. The final test expectations use the approved outdoor grille fixing face and a clean whole-scene mounting result; frozen bad geometry and mutation checks remain active. `git diff --check` exits 0.

## Previews and views for the lead

Generated and visually inspected [approved exterior preview](../out/c4-final/approved-exterior-preview.png) and [assembly preview](../out/c4-final/assembly-first-fix-preview.png). These show complete before/after bounds, actual fixing datums, the symmetric headboard and the lifted rigid coffee assemblies. They are geometric diagnostics. The lead's render review and independent lighting/native proof remain pending before presentation integration.

| Render area | Views / close-ups |
|---|---|
| Four boundary assemblies | v27-north-garden-above, v28-north-garden-below; all four fixing-face close-ups, south edge explicitly unverified |
| Parents' headboard | v05-parents-bedroom; panel left end, wall end and bed centreline close-up |
| Coffee assemblies and dirty hood | v20-kitchen-run, v17-dirty-kitchen; both tray/worktop sections and hood/chimney connection |
| Exterior grilles | Exterior close-up of guest-WC and dirty-kitchen grilles; v17-dirty-kitchen for context |
| Prior C4 televisions | v03-street-lounge, v04-study-deck |
| Prior C4 bar strips / nook lights | v24-bar-alcove; independent probes for moved emitters |
| Prior C4 brackets / rails | v31-dressing-hers, v32-dressing-his |
| Prior C4 stringer / markers | v11-stair-void, v23-gf-gallery, v29-under-stair-store, v30-under-ramp-store |
| Retained WC slides / client bathroom | v16-guest-wc, v12-ensuite, v15-family-bath |

Render from the clearly labelled [final working candidate](../out/c4-final/working-scene.json). Do not silently substitute the retained package-f scene. Finishes, product/installation data and shared-axis boundary construction retain their earlier limitations.

**STOP: CHECKPOINT delivered; uncommitted.**
