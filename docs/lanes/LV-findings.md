# LV findings (independent lighting verification, D1)

Run: `python -m archpipe.lightverify --design D1` (252 pass / 37 fail / 61 not evaluated; per room x scene table in `LV-report.md`,
raw in `knowledge/lighting-verify/checks/LV.json`). Radiance results are the LV run of the merged L6b design (`villa_run --tag lv`, ab 6 + 12),
frozen in `knowledge/lighting-verify/radiance/`.

## ENGINE / DESIGN BUGS (not fixed: not mine to edit)

1. **GF-parents-bed is calculated as the 0.68 m2 entry, not the 11.66 m2 bedroom.** `lightcalc.villa.union_rects` returns one outline only; the
   bedroom clear rect (y -26.591..-23.791) and entry (y -27.321..-26.641) are 50 mm apart (not touching), so the walk over `edges` follows one component.
   Reproduction: `Villa().cluster_room("GF-parents-bed").polygon` -> a 1.0 x 0.68 m rectangle; every bedroom emitter and the pillow planes lie outside it.
   Consequence: every bedroom number in L6b (pillow-1/2, room-parents-bed, 143 lx) comes from a wrong closed volume. Caught by V2 (`volume:GF-parents-bed`),
   V6 (engine 143 lx vs hand 1262 lx) and the V5 bedroom row. Fix: bridge or merge adjoining rooms across the wall gap, or model entry separately.
2. **Radiance `ab 6` under-converges small bright rooms**: ab 6 -> 12 changes room-parents-ensuite -6.4 %, fb-basin -4.7 %, corridor -4.7 %, store -4.0 %,
   10 of 39 planes exceed the 3 % bar (V7). All reported numbers are low by that much; use ab 12.
3. **Task-plane heights vs host surfaces (V3, 5 mm bar)**: desk planes at 0.75 m sit 28 mm above the modelled desk tops (study-desk, study-adult-desk, ka-desk-1/2, kb-desk,
   cinema-desk); sink plane 38 mm above the worktop; basin planes (fb, pe, gwc) 180 mm above the basin top. Also: sensors inside chairs/shower/hanging rails
   (island-prep 2/14, dirty-kitchen-run 2/14, study desks, cinema desk 5/18; rooms study-game 11 %, parents-dressing 17 %, pantry 29 %, family-bath 24 %,
   parents-ensuite 24 % of room-plane points). The dining-table sensors are clear (the October vase is not in this scene). Scene used: the RV1 workstation scene
   (`/tmp/RV1-scene/scene.json`); a fresh build of the merged design fails at `mounting_resume` ("lamp-SCONCE-family-bath-04: approved schedule drift"), an L2/L6b integration
   issue for the lead.
4. **V12 exceptions** (zone driver > 0.80 of maximum in the owning scene): family bath basin 121 % (needs more than rated output; the engine silently caps bound-product
   dimmers at 1.0), dirty-kitchen run 95 %, study desks 86 %, kids-b desk 85 %. island-seating/homework-end sit at 79 %.
5. **V5 direct agreement fails for the circulation volume (+7.6 %) and the bedroom (+8.8 %)**: Radiance and Cycles agree with each other (direct 128.2 vs 127.4 lx; total
   226.5 vs 226.9 lx), the analytic path has no occlusion, so it over-reports in non-convex volumes (and in the bedroom, finding 1).
6. **L2 model snapshot is stale** vs the L6b design: of 104 luminaires with the same id, 26 differ by more than 10 mm, 28 engine fixtures are not in it (V2 reports
   these rooms not_evaluated). Regenerate `src/archpipe/model/data/d1-elements.json` after the L6b merge.

## Layer results

| layer | result |
|---|---|
| V1 | 20 luminaire kinds, all pass. Integrated vs product lumens: DL 732.3 / 732.6 lm, ADJ 510.9 / 511.5, WW (substitute of DL, flagged) same. 3 product kinds, 17 generic kinds (assumed, not products; share of lumens reported in the table). |
| V2 | 90 pass, 1 fail (the bedroom volume), 54 n/e (stale snapshot). No emitter above its ceiling, wrong datum or outside its room. |
| V3 | 22 pass / 17 fail (finding 3). |
| V4 | 26 / 26 within 5 %: case 5.2 (both photometries, 20 points, worst 0.07 %), case 5.8 rho 0.05, 0.1, 0.3, 0.4, 0.6, 0.7 (worst +1.2 %, closed form agreed). L6 already did 0.2/0.5/0.8. Not run: 5.3 (charts only), 5.5, 5.9-5.14, 5.6 (sketches only), 5.7 (table erroneous in the source). Source: DAU Iray validation report 2016 (NVIDIA developer site); CIE 171 itself is not held. |
| V5 | 15 clusters, three engines. Direct vs Radiance: 13 rows within 0.4 %; Cycles direct within 2.2 % (bar 3 %); Cycles vs Radiance total within 1.9 %. Fails: circulation and parents' bedroom (finding 5/1). Cycles probe initially read indirect light 9 % low because of its own default sample clamp; the production renderer already disables it (`measure_lux`, `villa_scene`); the probe now does too. The cube test (Radiance vs Cycles, 4 points) agrees within 1.2 % on total. Sources are shared between engines (same placements), so V5 tests transport, not source modelling. |
| V6 | 11 / 13 clusters within 25 % (guest WC +5 %, family bath +3 %, open plan +6 %, cinema +15 %); misses: parents-bed (bug 1) and parents-dressing (engine 356 lx vs hand 615 lx, -42 %: strips/hanging-rail light is mostly on garments and walls, unexplained further; flagged, not argued away). UF is derived (first-incidence geometry + closed-form inter-reflection), no UF table is held; stated in the module. |
| V7 | 29 / 39 planes within 3 % (finding 2); grid halving on direct light: worst +6.5 % (cinema room plane, 0.63 m grid). |
| V8 | 9 / 9 seeded errors caught: doubled lumens (V1), doubled watts (V1), fitting 300 mm into the slab (V2), datum +1.2 m (V2), vase on a sensor (V3, real scene), plane 30 mm high (V3), IES rotated 90 deg (V10 .ies vs .ldt), Radiance output doubled (V5), driver 0.42 -> 0.95 (V12). |
| V10 | The manufacturer's .ies and .ldt (same lab, 2026-04-09) agree to 0.04 % (lumens, watts, peak, axis points); header-stated 12 W 730 lm / 11.8 W 1340 lm / 12.6 W 510 lm vs integrated 732.3 / 1342.5 / 510.9 lm; engine axial lux at 1, 2, 3 m equals the file (AAK3EW 2291/573/255 lx, AAIIA6 5029/1257/559, AAHENX 4130/1032/459) with beam diameters tabulated. **NOT achieved: published data-sheet cone/UGR points.** iGuzzini has no public page or PDF for these configurator codes (`iguzzini.com/<code>` 404; cdn PDF unreachable); ArchDaily family ranges (Soft 540-1110 lm, Cone 540-1380 lm) contain the products. Slot ready in `manufacturer-published.json`: paste the product-selector datasheet points and V10 checks them at +/-5 %. |
| V11 | Package ready: `knowledge/lighting-verify/dialux/` (B-open incl. dining+kitchen, GF-family-bath, GF-parents-bed; DXF, luminaires.csv, planes.csv, reflectances, IES, expected engine values, STEPS.md). Note GF-parents-bed expected values come from the buggy volume (finding 1): do not run that room until it is fixed. Compare with `python -m archpipe.lightverify.dialux_compare`. Expected values are filled for all three spaces. |
| V12 | 15 pass / 5 fail (finding 4). |

## Rooms verified vs unverified

2 of 39 room-plane rows verified; the rest are unverified, mostly because V7 (ab 6), V2 (stale snapshot, n/e), V3 and V12 fail or cannot run. See `LV-report.md`.

## Decisions

- Sensors tested in the RV1 scene (built before the L6b design; furniture geometry is unchanged by L6b), because the merged design fails to build a scene.
- Radiance run with the merged L6b design as the lane baseline; results frozen into the repo so the command is reproducible without a re-run.
- Hand-calc UF derived, not looked up (no table held). Thresholds are policy SourceCards (`sources.py`).
- V9 not built (declined by the client). `lane_guard.py LV` lists the files merged from lane/L6b (29, all L6b-owned) as outside LV's ownership, as expected for this merge.

## Re-verification (2026-11-21): L6b after-state, ab 12 (+ ab 24), LV scene loader fixed

Run: `python -m archpipe.lightverify --design D1 --scene /tmp/RV1-scene/scene.json` -> 286 pass / 4 fail / 64 not evaluated (was 252 / 37 / 61).
Scene geometry: the same frozen RV1 scene L6b used (`/tmp/RV1-scene/scene.json`); the merged design's scene still does not build (lane RA).
Radiance: my own full re-run of the merged L6b design (`villa_run --tag lv2`, ARCHPIPE_L6_LOCAL=1, ab 12 and ab 24, all 13 clusters), frozen in
`knowledge/lighting-verify/radiance/`. Data-sheet inputs for V10: none arrived (`~/archpipe/shared/luminaires-inbox/` does not exist; no `*.points.json` on origin/lane/LP).

### My own bug (loader)
`scene_geom.load_scene` ignored `scale_xyz` on fitted models (rule now = renderer's `import_models`: `scale_xyz` when `scaling` or `furniture_fitting`, else scalar `scale`).
Old loader: study desk 0.45 x 1.1 x 0.72 m, desk chair 0.78 x 2.01 x 1.32 m. Fixed: desk 0.70 x 1.80 x 0.75, chair 0.45 x 1.01 x 0.91. Tests: `test_load_scene_applies_scale_xyz_of_fitted_models`
(fails on the old loader, verified by stashing the fix) and its negative. Artefacts of that bug: the six "desk plane 28 mm above host" findings (now 2 mm) and the chair hits on
cinema-desk / study-adult-desk. Real, now fixed by L6b: sink, basins, rails, shower/bath, pantry, hob, bowl.
Second correction: V3 tested every grid point, while the engine drops points inside `exclude` footprints; `v3_sensors.plane_points` now tests the points actually sent to Radiance
(`test_plane_points_apply_the_engine_exclusions`). Result: 39 of 39 planes pass (0 points inside/under any object; hosted planes 0-4 mm from their host).

### Per layer
| layer | result |
|---|---|
| V1 | 20 of 20 kinds pass |
| V2 | 92 pass, 0 fail, 57 n/e: the L2 snapshot (`d1-elements.json`) still predates the L6b redesign (30 engine-only, 27 moved fixtures). Bedroom volume now passes. |
| V3 | 39 / 39 |
| V4 | 26 / 26 (unchanged; engine not touched) |
| V5 | 14 / 15 clusters. Radiance vs analytic direct within 0.5 % everywhere; Cycles direct within 2.2 % except the parents' bedroom -3.6 % (bar 3 %; Radiance = analytic there, Cycles total vs Radiance -1.8 %). Cycles vs Radiance total within 4.1 % (bar 10 %). The old circulation failure is gone (now +0.0 % direct). |
| V6 | 12 / 13. Parents' bedroom -89 % -> +6 %. Parents' dressing -39 % remains a flagged miss (see below). |
| V7 | ab 12 -> 24: all 39 planes within 3 % (worst pillow-2 2.39 %, pillow-1 0.68 %, parents-bed room 0.28 %; all others < 0.25 %). Direct-grid halving fails for room-cinema (+6.35 %, 0.63 m grid) and daybed (-3.07 %, 0.12 m grid): coarse-grid sampling of direct light, not a bounce issue. |
| V8 | 9 / 9 |
| V10 | 17 pass, 4 n/e (published data-sheet cone points not obtainable) |
| V11 | package regenerated for the current design (all three spaces, bedroom now with the real volume); still not run in DIALux (3 n/e) |
| V12 | 20 / 20; worst zone 0.772 (island pendants, `Z-B-KITCHEN-ISLAND-PENDANTS` 77 % in Day). Previous 5 exceptions gone. |

### L6b's claims, checked independently
* Bedroom polygon: 11.706 m2 vs model rooms 11.656 m2 (+0.43 %, the 0.05 m2 bridged wall gap). The other 12 clusters match the model: 11 exactly, circulation +0.37 %. Confirmed.
* ab 12 -> 24: my own run of all 39 planes (not just 3), max 2.39 % (pillow-2; L6b measured 0.71 % on that plane: Radiance sampling noise between runs; still < 3 % but the least margin). Confirmed.
* Sensors within 50 mm of objects: 0 of 39 planes, tested against the independent triangle scene with the engine's actual points. Confirmed.
* Task planes on their surfaces: desks 2 mm, hob 4 mm, others 0 mm. Confirmed.
* V12 worst 0.772: confirmed (recomputed by V12 from `zone-drivers.json`, zone watts and levels).
* Parents' dressing: Radiance room mean 378 lx, Cycles total 364.5 vs Radiance 369.7 (-1.4 %), analytic direct agrees within 0.3 % / Cycles 1.5 %. So two engines with different code agree that the room is ~370-380 lx; L6b's radiosity (377) is a third. The lumen-method 615 lx is a poor estimator here (room index 0.43, 79 % of first-incidence flux on walls). I accept the explanation as supported by independent engines; the row stays "unverified" because V6 cannot pass (a documented, explained miss, not argued away).

### Rows: verified vs unverified (39 room-plane rows; `LV-report.md` has the table)
Verified: 8 (kids-a x3, kids-b x2, kitchen-island, pantry, store-ramp). Unverified: 31:
* 22 rows: V2 only (stale L2 snapshot; every other layer passes). Fix = regenerate `src/archpipe/model/data/d1-elements.json` (lane L2/lead); LV cannot do it.
* parents-bed x3 (pillow-1, pillow-2, room): V2 n/e plus V5 Cycles direct -3.6 % (bar 3 %).
* room-parents-dressing: V2 n/e plus the explained V6 miss (above).
* dining-table, homework-end: V6 n/e (no lumen-method estimate for an open-plan sub-plane); daybed: V6 n/e plus V7 direct-grid -3.07 %.
* cinema-desk is clean but room-cinema (+6.35 %) and the cinema row sharing its cluster fail V7 grid only: 2 rows.
Nothing is verified for V11 (DIALux not run) or V9 (declined); V10 data-sheet points absent.

### Open
1. Regenerate the L2 model snapshot (frees ~24 rows).
2. Parents' bedroom: Cycles direct is 3.6 % under analytic/Radiance (0.6 point over the bar). Not diagnosed: possible Cycles sampling at the bridged outline or at the 0.7 m sensor height; no engine or design defect shown (analytic = Radiance).
3. Room-plane grid for the cinema (0.63 m) is too coarse for a +/-3 % direct result; a finer grid or an accepted tolerance (engine/L6b decision).
4. V10 data-sheet points and V11 DIALux run (client/laptop).
5. Fresh scene build of the merged design (lane RA) to repeat V3 on the true scene.
