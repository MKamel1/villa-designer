# C4 retained package-e lead review: CHECKPOINT, uncommitted

2026-10-05. Continued from [package e](c4-phase2e-checkpoint.md), which remains intact with its evidence. No commit or full suite. No native rebuild, workstation deployment or presentation integration. These are authored candidate results, not verified installations or real villa gate approval.

Coordinates are metres: model x runs street to garden, model y toward plot east, model z upward. Movement and clearance values below are millimetres. WC means water closet; LED means light-emitting diode. Direction names in the movement table are the existing landscape identifier suffixes: east/west are positive/negative model x; north/south are positive/negative model y. The 300 mm host-search maximum is the lead-selected design limit, not a published standard. The existing held bathroom evidence and applicability remain those recorded in package e.

Applied authority is frozen in [c4-e-lead-approvals.json](../knowledge/c4-e-lead-approvals.json): 45 approved old schedule rows. **43 apply exactly; two approved inward grille finish-face movements are retired because exterior modeled-face hosts replace them.** All 14 rejected item movements remain unapplied. The old 9450.320 mm south proposal is retained by value in [the reproduction fixture](../tests/fixtures/c4-e-rejected-hosts.json).

The approved translations include television assemblies, feature panels, dressing brackets, the curtain track slide, open stringer floor bearing, coffee bodies, hood, wall markers and bar LED strips. Six attached coffee parts and one hood chimney follow their roots rigidly. Eight analytical bar-strip emitters follow their moved geometry with unchanged photometry. Wall markers emit through their luminous mesh material; no separate analytical marker lights are invented. The earlier seven carried emitter assemblies remain recorded separately. Independent lighting probes remain required before integration.

Yard hosts now come from the finite modeled yard polygon. The street, rear and east whole-plot fences retain their actual modeled **250 mm** thickness and inner faces; selection is clipped to the applicable yard edge. Both shared-axis yard edges have no modeled wall solid: their polygon edge is explicitly declared the inner structural face, with wall thickness, height and fixing capacity UNVERIFIED. The proposed south assembly uses that declared yard edge, not the distant sister-side fence. Modeled exterior paint/render is retained; finish build-up is UNVERIFIED and no finish thickness is added. The host normal points into the yard.

Host selection requires the entire conservative fixing envelope on one finite convex source face and refuses more than 300 mm authored fixing-plane travel. Concave/incomplete or remote faces are refused before a movement is generated. Both exterior grilles select a wall face with their authored room on its inward side and no room on its outward side, with the same distance and footprint constraints. The proposed bodies now move outward, not into the rooms. The hood uses independently recorded actual coplanar wall patches instead of the column-sized room-labelled patch; no wall is extended.

## Remaining movements above 5 mm for approval

**14 rows; none applied.** Each landscape group comprises trellis, branch and climber records, all translated together with retained geometry. The [complete comma-separated movement schedule](../out/c4-phase2f/movements-over-5mm.csv) supplies every identifier, host and old/new bounds.

| Identifier suffix / item | Rows | Revised movement | Direction / actual fixing face |
|---|---:|---:|---|
| east trellis, branches, climber | 3 | 113 mm | negative model x; modeled inner face x 28.307 m |
| south trellis, branches, climber | 3 | 135.660 mm | negative model y; declared polygon inner face y -29.915660 m |
| north trellis, branches, climber | 3 | 191 mm | negative model y; modeled inner face y -20.601 m, with actual fence coverage at x 24?26 m |
| west trellis, branches, climber | 3 | 177 mm | positive model x; modeled inner face x -0.123 m |
| detail-vent-guest-wc-grille | 1 | 12 mm | positive model y; exterior face y -20.601 m |
| detail-vent-dirty-kitchen-grille | 1 | 12 mm | positive model y; exterior face y -20.601 m |

The remaining moves are all within 300 mm, but still exceed the existing 5 mm automatic application limit. Re-proposing them does not inherit approval from the rejected old rows.

## Verification findings by type

**The expected ?only three family-bath failures? state is not reached.** Pending exterior proposals retain working-scene mounting failures. Three support defects also remain even in the fully proposed scene: the headboard's actual 47 mm wall-edge overrun, and both coffee drip trays penetrating their modeled worktops by 12 mm after the approved rigid moves. The coffee support selection used the body and omitted its lower tray. The new generic associated-child support-plane guard retains these real collisions; it does not deform the tray or revise an approved pose. New appliance poses and headboard support need lead decisions.

| Finding type | Working scene | Fully proposed scene |
|---|---:|---:|
| Missing hosts | 0 | 0 |
| Signed fixing-plane discrepancies | 14 | 0 |
| Finite coverage messages | 13: 12 pending landscape items and headboard | 1: headboard |
| Associated appliance support penetrations | 2: coffee trays, 12 mm each | 2 |
| Numeric bathroom clearance failures | 3 | 3 |
| Numeric clearance unresolved rows | 0 | 0 |
| Total mounting messages | 29 | 3 |

The legacy report field `unexplained_findings` lists the three nonpending support findings; all three are diagnosed above. None is suppressed. The family bath still measures WC narrow side **197 / 350 mm**, WC wide side **200 / 1000 mm**, and basin frontage **0 / 1100 mm** (achieved / required). The client's WC/bathroom decision remains open. The [geometry comparison](../out/c4-phase2f/geometry-diff.json) confirms **zero changed family meshes and unchanged cameras**, with 52 changed prior records including approved parts, their rigid children and diagnostic host replacements.

The completed [delivery verify log](../out/c4-phase2f-verify-delivery.log) and [process exit](../out/c4-phase2f-verify-delivery.exit) are authoritative: **exit 1**, only whole-scene mounting and affected bathroom clearances fail. The prior completed run reports 123 passing checks and these same two failing checks. Guard registry, scene contract and held evidence pass. The initial system-Python attempt could not import Shapely; its [failed-start log](../out/c4-phase2f-verify-system-python.log) is retained separately. Verification uses the project `.venv/Scripts/python.exe`.

## Focused tests and checkpoint exits

All commands ran from the project working directory. No full suite was run; the lead runs it.

| Focused modules / evidence | Tests | Exit |
|---|---:|---:|
| exterior mounting, support mounting, mounting scene: [combined log](../out/c4-phase2f-focused.log) | 31 passed | 0 |
| latest support and exterior construction, including rigid children, real tray collisions and quiet/mutated siblings: [complete log](../out/c4-phase2f-focused-complete.log), [exit](../out/c4-phase2f-focused-complete.exit) | 9 passed | 0 |
| final exterior module, including coordinate/container comparison regression: [log](../out/c4-phase2f-exterior-final.log), [exit](../out/c4-phase2f-exterior-final.exit) | 5 passed | 0 |
| candidate checkpoint: [complete log](../out/c4-phase2f-checkpoint-complete.log), [exit](../out/c4-phase2f-checkpoint-complete.exit) | findings intentionally retained | 1 |

These runs provide passing evidence for 32 distinct current focused tests. Intermediate failed carried-emitter lookup runs are retained (`focused-carried`, `checkpoint-final`, `verify-final`); wall markers have material emission rather than a separate light record. The final runs above supersede those attempts. `git diff --check` exits 0. Learnings, guard registry and mounting workflow were updated together.

## Previews and render views for the lead

The [finite exterior-host preview](../out/c4-phase2f/exterior-first-fix-preview.png) and [approved assembly support preview](../out/c4-phase2f/approved-assemblies-preview.png) were generated and visually inspected. They are geometric diagnostics, not photoreal acceptance. The full north trellis is visible; the south host is explicitly labelled as having no modeled wall solid. Coffee tray collisions and headboard overrun remain visible. The lead's preview review and independent lighting/native proof remain pending before presentation integration.

Render small neutral-light diagnostic packages from the clearly labelled working candidate. Keep the revised unapproved exterior proposal separate.

| Area | Existing views / additional close-up |
|---|---|
| Four boundary assemblies | v27-north-garden-above, v28-north-garden-below; all four fixing-face close-ups, including south polygon edge |
| Exterior grilles and dirty hood | v17-dirty-kitchen plus exterior close-ups of each grille |
| Coffee appliances and their tray collisions | v20-kitchen-run, v17-dirty-kitchen; tray/worktop sections |
| Television and headboard support | v03-street-lounge, v04-study-deck, v05-parents-bedroom; headboard left edge |
| Bar strips and nook lights | v24-bar-alcove; independent probes for moved bar/nook emitters |
| Brackets and rails | v31-dressing-hers, v32-dressing-his |
| Stringer and luminous markers | v11-stair-void, v23-gf-gallery, v29-under-stair-store, v30-under-ramp-store |
| Retained authorized WC slides / client bathroom | v16-guest-wc, v12-ensuite, v15-family-bath |

Evidence: [working scene](../out/c4-phase2f/working-scene.json), [separate proposal](../out/c4-phase2f/proposed-scene.json), [mounting report](../out/c4-phase2f/mounting-report.json), [clearance table](../out/c4-phase2f/clearance-results.csv), [applied schedule](../out/c4-phase2f/movements-applied.csv). The report preserves before/after vertices for the seven carried appliance parts and old/new positions for eight bar-strip emitters.

**STOP: CHECKPOINT delivered; uncommitted.**
