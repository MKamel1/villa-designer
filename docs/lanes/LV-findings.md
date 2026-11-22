# LV findings (independent lighting verification, D1)

> Current state: see **"Final verification (L6c)"** at the end of this file. Everything above it describes the L6b design and is kept as history.

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


---

# Final verification (L6c): the ERCO-bound design (2026-11-21)

Command: `python -m archpipe.lightverify --design D1 --scene <scene.json>` (see the top of `LV-report.md`; exit 1 = a failing check, 0 = none; today 1).
Result: **353 pass / 17 fail / 29 not evaluated**; `out/checks/LV.json`, copy in `knowledge/lighting-verify/checks/LV.json`.
Merged `origin/integ/aplus` (L6c, `1cf511a`). Radiance: my own full re-run of the L6c design (`villa_run --tag lv3`, ab 12 + 24, all 13 clusters, frozen in
`knowledge/lighting-verify/radiance/`); it reproduces L6c's frozen zone sums within 1 % (parents' bedroom decorative zone 6 %, a 0.3 lx zone), so it is a
repeat of the same code, not a second engine; independence comes from the analytic path, Cycles and the lumen method.
**Scene used for V3: `/home/omar/archpipe/lanes/RA2/out/ra2/prod/scene.json`, sha256 `f7a7fe76418a04ff1fe75b2fdfe8596e095783bb2923155fd303afa35b9ee7b3`** (the newest
workstation scene, 12:24 today). It is NOT a scene of the L6c lighting (its 125 lights are the LSEVO ones, 83 ids in common with the 132 L6c fixtures): V3 uses only its
furniture/architecture geometry. A fresh build of the merged design fails (`jobq lv-scene-build-l6c`): `ValueError: support-marker-PATH-landing-gf-02: no real host at authored
fixing anchor`, the PATH marker INT2 is moving. Re-run V3 on INT2's scene with `--scene`.

## 1. The three failing tests (causes)
* `test_v1_design.py::test_design_inputs_pass`: **L6c's diagnosis confirmed on the data.** The table pendant is 8 samples of 57.8 lm; V1's instance check compared each
  with the whole fixture's record (462.5 lm); the 8 samples sum to 462.5 lm = the record. V1 was wrong: `instance_problems` now sums by parent. Tests: the sampled pendant
  passes (fails on the old code, verified by stash) and a fixture whose samples do not add up (4 of 8 doubled) is still caught.
* `test_v5_v6_v7.py` (2 tests): they read the frozen Radiance of the L6b design. Regenerated: `ARCHPIPE_L6_LOCAL=1 PATH=~/archpipe/tools/radiance-6.0.1/bin:$PATH PYTHONPATH=src
  python -m archpipe.lightcalc.villa_run --tag lv3 --out out/LV3` (or `python -m archpipe.lightverify --regen-radiance --freeze`), copied to `knowledge/lighting-verify/radiance/`.
  With the old files the two tests fail, with the regenerated ones all 6 pass; no tolerance was touched.

## 2. Layers V1-V8, V10, V12 on the L6c design
| layer | result |
|---|---|
| V1 | 20 / 20 kinds; DL integrates 1065.9 lm (bound 1065), PEN-LIN 3557.5 lm (bound 3558). |
| V2 | 119 pass, 0 fail, **26 n/e**: the L2 snapshot `d1-elements.json` is still stale (6 engine-only, 20 moved fixtures). Regenerating it frees 9 rows outright and removes one blocker from 11 more (lane L2/lead). |
| V3 | 39 / 39 planes (0 sensors inside/under any object, hosted planes within 5 mm) on the scene above. |
| V4 | 26 / 26 (engine untouched). |
| V5 | 14 / 20 (15 clusters + 5 single-light probes). Radiance vs analytic direct within 0.1 % except parents' bedroom +7.5 %. Cycles: see findings A and B. |
| V6 | 12 / 13: dressing room -40 % (explained in the L6b section, unchanged: 390 lx by Radiance, Cycles, analytic; lumen method 646 lx is a poor estimator at room index 0.43). Parents' bedroom +4 %. |
| V7 | ab 12 -> 24: 36 / 39 within 3 %. Fails: **pillow-1 +3.21 %** (pillow-2 +2.39 %, room-parents-bed +2.21 %: the least-converged plane, a small directional plane), and direct-light grid halving: **room-corridor -6.23 % (0.85 m grid)**, **room-parents-bed -3.39 % (0.43 m)**. Engine grid pitch, not mine to fix. |
| V8 | 9 / 9 seeded errors caught (unchanged). |
| V10 | see 3. |
| V12 | 20 / 20 headroom, **worst 0.761 (`pe-basin`, ensuite basin) confirmed** (second: dirty-kitchen run 0.756; island pendants 0.70). New: `cards_met` re-reads every average-gauged card from my own Radiance with the commissioned drivers: 20 of 20 within x0.91-1.08 (L6c says 0.91-1.09). |

### 3. V10: every bound ERCO product against its own lab data (`v10_erco.py`, data-sheet numbers parsed by me from the PDFs, not from LP's transcription)
Bound file = byte-identical ERCO download for DL, DLN, ADJ, WW, DESK; the Jilly's derived file integrates to exactly 2 x the per-module file (1.000). `.ies` vs `.ldt` agree.

| kind | product | lumens: integrated vs data sheet | Imax: file vs data sheet | cone / beam | status |
|---|---|---|---|---|---|
| DL | 41321 | 1065.9 vs 1065 (+0.08 %) | 1148 vs 1147 | beam angle 56 deg ok | pass |
| DLN | 41369 | 904.7 vs 904 (+0.08 %) | 535 vs 535 | 89 deg ok | pass |
| WW | 41374 | 399.1 vs 399 (+0.01 %) | 479 vs 471 (+1.6 %) | - | pass |
| PEN-LIN | 50674 (x2 file) | 3557.5 vs 3558 (-0.01 %) | 1054 vs 1055 | 86 deg ok | pass |
| DESK | 31327 | 233.8 vs 234 (-0.08 %) | 461 vs 454 (+1.6 %) | - | pass |
| **ADJ** | A9000028 | 300.3 vs 304 (-1.2 %) | 22055 vs 22846 (-3.5 %) | lux on axis 1-5 m -3.4 to -3.5 % (ok); **beam diameter at 50 %: file 0.100/0.199/0.299/0.398/0.498 m vs data sheet 0.08/0.16/0.25/0.33/0.41 (+20 to +25 %); angle 5.7 vs 4.7 deg** | **PARTIAL** |

**Does the ADJ beam discrepancy matter for the armchair reading plane?** The file reaches the published 4.7 deg only at 65 % of its peak, so the published figure is a different
beam definition or a narrower core than the file; lumens, Imax and axial lux all agree with the file, so the file is internally consistent with three of the four published
numbers. What if the published beam were literal (everything x 4.7/5.7)? Armchair plane (card 200 lx, ADJ at driver 0.668, direct 147 lx of the 200):
(A) narrower with Imax kept (flux falls to 204 lm, contradicting the published 304 lm): ADJ direct 88 lx, plane ~141 lx, **driver needed 1.11 > 0.80: not absorbed**;
(B) narrower with flux kept (peak 32 400 cd, contradicting the published Imax): ADJ direct 130 lx, plane ~183 lx (-8.5 %), **driver 0.76 <= 0.80: absorbed by V12 headroom**.
Honest reading: for the lab file the reading plane is met; if the published beam is physically right and the file wrong, the armchair could fall to 141-183 lx and case (A) needs a
second spot. Lounge rows therefore stay **unverified** (V10 partial) until the supplier's actual sample or an ERCO statement of the beam definition closes it. The two accent
ADJ zones (dining sideboard, parents' bedroom) carry no card and do not block their rooms.

## 4. Judgement: L6c's patch-radiosity change (8 -> 16 patches, bar 6 % -> 8 %)
**Mostly a legitimate resolution correction; the 8 % bar is partly tuned to the pantry.** Floor mean, 100 % output, vs Radiance (Radiance = L6c's published full-output plane means, `villa-after-rows.json`; my own run reproduces them within 1 %):

| room | Radiance lx | 4 patches | 8 | 12 | **16** | 24 | 32 |
|---|---|---|---|---|---|---|---|
| guest WC | 214.6 | +26.9 % | **+9.9 %** | +4.2 % | **+2.0 %** | -0.3 % | |
| parents' dressing | 390.3 | +32.9 % | **+9.5 %** | +3.5 % | **+0.9 %** | -1.3 % | |
| family bath | 258.2 | +26.5 % | **+7.1 %** | +1.7 % | **-0.8 %** | -3.3 % | |
| pantry | 199.1 | +9.0 % | **+9.0 %** (8) | -3.2 % | **-7.0 %** | -8.7 % | -9.3 % |

For the three rooms the error is monotone in the patch size and crosses zero at ~16-24: classic discretisation error of a solver that never converged at 8 patches (it was 6 % only
for the old narrow distributions). Converged (24), the three agree with Radiance within 3.3 %. L6c's claim and its lesson are supported on evidence, and the 8-patch result was
the outlier, not the 16. **The pantry is not a resolution story:** it moves *away* from Radiance as the patches get finer (+9.0 -> -9.3 %); the 8 % bar passes it at 16 patches only
because the curve crosses -7 % there. Part of the gap is the sensor plane: Radiance's plane is inset 0.10 m from the walls of the 2.9 x 1.0 m room, the radiosity averages the full
floor; restricted to the inset footprint the converged (24) numbers are pantry -5.7 %, guest WC +2.3 %, family bath -1.1 %, dressing +0.6 %. A residual -5.7 % in the narrow room is
unexplained (candidates: the 2.9:1 patch aspect, the bounding-box idealisation). So: resolution 16 is justified; the **bar 8 % was set to fit the pantry** and is not independently
defended. Recommended (not mine to edit): footprint-matched comparison at 24 patches and a 6 % bar with the pantry's residual named. Guard in my tests:
`tests/lightverify/test_radiosity_resolution.py` (the 8-patch error > 6 %, 16 removes more than half, 24 within 3 %, monotone; a wrong wall reflectance is still caught).

## 5. LA4 glare and the lowest dimming levels
**LA4 (bed-foot DL 23 217 cd/m2).** The old bed-foot position is not in the repo (the intermediate design), so that figure is **unverified**. Independent recomputation for the DL that
stayed (`DL-parents-bed-04`, ERCO 41321, opening 76 mm, I(39.4 deg) = 315 cd): **L = 315 / (pi/4 * 0.076^2 * cos 39.4) = 89 953 cd/m2** (engine 89 877 at its dim 0.999), 30x the cap
of 3000. The check passes ("none in view") only because this DL is **53.7 deg** from the policy sightline (45 deg cone). The sightline set has one reclined view (toward the foot, 17 deg up);
for a person lying on the pillow end looking straight up, the DL is **39.4 deg** off the axis, inside the cone, at ~90 000 cd/m2 at Day (x1.0) and ~36 000 at Evening (x0.40). So LA4 is
satisfied by the choice of sightline, not by luminance. **Design finding (not fixed): add a "lying, looking up" sightline; the DL's cut-off (data sheet 40 deg) is exceeded at 39.4 deg by 0.6 deg.**
Reproduce: `luminance_toward(<placement DL-parents-bed-04>, (20.33, -26.191, 0.7))`.

**Output fraction (scene level x driver) below 15 % per zone** (131 zone-scene pairs; DALI `1 %-100 %` CCR printed on every ERCO data sheet used; flicker data printed "TLA SVM <= 0.1 / 0.4,
PstLM <= 1", the level at which it was measured is not stated; **driver datasheet minimum: 1 % (printed); flicker below 100 %: unknown**):
| zone | scene | output |
|---|---|---|
| Z-B-DINING-TABLE-PENDANT (Jilly) | Evening | **3.9 %** (lowest; was not mentioned) |
| same | Dinner | 6.1 % |
| same | Day | 13.0 % |
| Z-B-KITCHEN-ISLAND-PENDANTS (generic globe) | Reading | 14 % |
| night/orientation zones at level 0.10 (NL, TOE, STEP, PATH generics; `Z-B-LOUNGE-ROUTE-NIGHT` = ERCO DL) | Night / Film | 10 % |
The table pendant is the only bound product that works near the floor of its range (3.9 % is 3.9 x the 1 % minimum; the Jilly is CCR, so no PWM flicker by construction, but the
datasheet does not give SVM at that level). The generic night strips' driver floor is unknown (no datasheet). Recommendation: a smaller pendant (the supplier row already asks 700-1800 lm).

## 6. New defects (reproduced, not fixed)
A. **Production Cycles throws the ERCO wallwasher 90 deg away from the engine and Radiance.** Reproduce: `PYTHONPATH=src python -c "from archpipe.lightcalc.villa import Villa; from archpipe.lightverify import v5_engines as V; print([r for r in V.kind_orientation(Villa()) if r['kind']=='WW'])"`
(one WW at its design aim (0,-0.25,-1), spin 0, 25 floor points, Cycles with the production `add_light` vs the analytic path): total **+35.6 %**, pattern error **153 %**; with +90 deg of
extra spin **-7.5 % / 8 %**; +180 -> +34 % / 151 %; +270 -> +72 % / 253 %. Same for aims (+-0.25, 0, -1). The engine (and Radiance, which agrees with it) has the WW's C0 throw toward the
direction of the aim tilt; `villa_scene.add_light` (`to_track_quat("-Z","Y")` then `spin + IES_AZIMUTH_OFFSET_DEG`) is calibrated for straight-down lights (ADR-0010) and is 90 deg off for a
tilted aim. Consequences: the 12 WW in the production render wash sideways, and V5's Cycles rows fail where WW sit (corridor direct **+164 %**, ensuite +9 %); every V5-checked number of
those rooms is by Radiance + analytic only. A guard now exists (`v5_engines.kind_orientation`, 5 single-light probes, tests `test_v5_orientation.py`); it fails on this today.
B. DESK (Lucy): Cycles reads **7.7 % below** the analytic/Radiance path for a single light (pattern right, L1 8 %), which makes kids' A/B Cycles direct -4.1 / -4.5 % (bar 3 %). Not diagnosed.
C. Parents' bedroom: analytic direct is +7.5 % over Radiance and entirely from `Z-GF-PARENTS-ENTRY-AMBIENT` (the entry DL, partly hidden by the wall between entry and bedroom: analytic 1577 vs
Radiance 858 at pillow-1, 152 vs 0 at pillow-2; every other zone within 0.4 %). The analytic path has no occlusion; Radiance (with walls) is right. Cycles direct is a further -4.2 % under Radiance (undiagnosed).
D. The L2 snapshot is still stale (V2 26 n/e). `knowledge/lighting-verify/dialux/` still holds the L6b package (regenerate with `lightverify.dialux_pack` before V11).

## 7. Rows: verified vs unverified (39 room-plane rows)
**Verified (8):** family (Day) room-family; family-bath fb-basin + room; guest-wc gwc-basin + room; hall-b; kitchen-island; store-ramp.
**Unverified (31), by the first failing layer:**
* V2 n/e only (stale L2 snapshot; every other layer passes): dirty-kitchen x2, kitchen x5 (island-prep, island-seating, cooktop, sink, room), living, pantry = 9
* V6 n/e only (no lumen-method estimate for an open-plan sub-plane): dining-table, homework-end, daybed = 3 (dressing room: V6 -40 %, explained, = 1)
* V5 FAIL only (WW orientation in Cycles / ensuite Cycles +9 %): cinema x2, parents-ensuite x2 = 4; corridor V5 + V7 grid = 1
* V2 n/e + V5 FAIL: kids-a x3, kids-b x2, study-game x3 = 8; parents-bed x3 (V5, V7 pillow-1 / grid) = 3
* V10 partial (ADJ beam): lounge armchair, room-lounge = 2
Nothing is verified by V11 (DIALux not run) or V9 (declined).

## 8. What remains open before purchase
1. **V11 DIALux** (laptop): pending; the package must be regenerated for the L6c fixtures first.
2. ADJ beam: ERCO to state the beam definition or the supplier's sample to be measured; otherwise a second spot at the armchair. Do not buy the ADJ on the file alone.
3. Renderer: fix the tilted-aim azimuth of the asymmetric WW (finding A) before any render is used as evidence for wallwash; re-run V5.
4. L2 snapshot regeneration (frees 9 rows outright); INT2's scene to repeat V3 on the true scene.
5. Parents' bedroom: LA4 "lying, looking up" sightline against the bed DL (finding in 5); pendant oversizing (3.9 % at Evening).
6. Pantry radiosity bar (4); V7 grid pitches (corridor 0.85 m, parents' bedroom 0.43 m).
7. Egypt availability, R9 and cut-out sizes for the ERCO products (the supplier sheet asks).

## Verification of lane L6d (2026-11-22)

Run: `python -m archpipe.lightverify --design D1 --scene ~/archpipe/lanes/L6d/out/L6d/prod/scene.json` (sha256 5968c5b8..., matches L6d's report), Radiance baseline regenerated on the L6d design
and frozen. 452 pass / 1 fail / 3 n.e.; room-plane rows **verified 39 of 40** (L6d's own run: 34/40). Per layer pass/fail/n.e.: V1 20/0/0, V2 150/0/0 (incl. 5 LA4 lying sightlines),
V3 40/0/0, V4 26/0/0, V5 20/0/0, V6 15/1/0, V7 40/0/0, V8 9/0/0, V10 92/0/0, V11 0/0/3, V12 40/0/0.
Remaining: parents' dressing room V6 -40 % (engine 390 lx vs lumen method 646 lx at room index 0.43: the documented miss of the uniform-reflection closed form, not argued away);
V11 DIALux not run (3 n.e.); V9 declined.

* V10 (own parsing of the ERCO PDFs and the iGuzzini page text; no ids in code, products read from the binding): A9003138 lumens -1.46 %, Imax -1.54 %, lux 1-5 m -1.3..-1.9 %, beam angle +3.2 %;
  QA03 lumens -0.03 %, Imax -0.46 %, LOR 77.0 vs 77, flux >= 90 deg 0, beam -0.7 %; alternates 68887, 68119, QA11 pass. Disagreements with L6d's source.json: beam *diameter* (mine -1.4..-1.8 %
  at the 50 % of axial-lux level, theirs +3.1..3.5 %: a different level, both inside 5 %); 68887 lumens +0.31 % vs their +0.7 % (integration grid); **QA03 CRI: the page prints 92 (Rf 92), the bound record says 90**
  (understated; harmless to lux, fix the record).
* WW orientation fix confirmed: single-light probe WW +1.2 % total / 2.8 % pattern at its design aim; tilt 25 deg at azimuths 0/90/180/270: +0.9 % / 3.2 % each (before: +35.6 % / 153 %); ADJ -0.5 % / 3.7 %
  at all four; straight-down kinds unchanged (DL -1.2/2.6, DESK +1.0/1.0, PEN-LIN -1.2/2.3).
* IES multi-plane gain 1.094 holds on files L6d did not measure (straight down, total Cycles/analytic): 26141 (73 planes) -1.3 %, 35720 (73) -2.7 %, LSEVO-AAKR2I (37) -1.0 %, ST49 (19) -1.9 %; measured ones
  DESK +0.6 %, WW -0.3 %; single-plane DL -1.0, DLN -1.3, A9003138 -1.2, QA03 -1.1, 68887 -1.9 %. Worst residual -2.7 % (35720). Not checked: 2-5 plane files (none in the repo; L6d's own
  measurement shows -5.1 / -7.3 % at 3 / 5 planes, so a future 2-5 plane file would be under-corrected by the step at 6).
* LA4 lying sightlines reproduced from my own IES reading: pillow 1 nothing in view, pillow 2 ADJ 1656 cd/m2 (engine 1656), kids' B and the bunk 0. Fittings of other rooms in the cone (dressing-room DLs 82-101 kcd/m2,
  kids-a DL-kids-a-04 42 kcd/m2 as driven, 84 kcd/m2 full) are behind walls (4 vertical shell faces crossed each) so rightly excluded.
* Entry-lobby cove "hidden from the pillows": true by orientation, **not by built geometry**. The strip aims (0,-0.37,0.93), i.e. 155 deg from the direction to pillow 1's eye, outside its 120 deg spread, so
  nothing reaches the pillows. But the scene has no upstand mesh (assumed), and the strip sits at z 2.73 *above* the parents' ceiling mesh (2.70-2.701) in the render scene while the engine room's ceiling is 2.74:
  in Cycles the 1 mm ceiling plane is between the strip and the room, so the render may not show the cove light at all. Not rendered here; open item for the render/design lane.
* Open (not mine): `tests/luminaires/test_erco.py::test_stored_files_match_source_sha` fails on `QA11-product-page.txt` (file sha differs from QA11/source.json) already on origin/lane/L6d.
