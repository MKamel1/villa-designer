# L6d: lighting fixes after LV's final verification of L6c (2026-11-21)

Branch `lane/L6d` from `origin/integ/staging` (L6c + LV + INT2). Every item was diagnosed on data before anything was changed; the numbers below
are from this lane's runs (`out/L6d*`, reproduced by the commands at the end). LV result: `python -m archpipe.lightverify --design D1 --scene
<INT2 scene>`: **389 pass / 9 fail / 3 not evaluated** (was 353 / 17 / 29); room-plane rows **verified 34 of 40** (was 8 of 39). Per layer (pass/fail/n.e.): V1 20/0/0, V2 145/0/0 (was 119/0/26), V3 40/0/0, V4 26/0/0, V5 20/0/0 (was 14/6/0), V6 12/1/0, V7 40/0/0 (was 36/3/0), V8 9/0/0, V10 37/8/0, V11 0/0/3, V12 40/0/0. Unverified rows: lounge x2 and dining x2 (LV's V10 does not know A9003138 / QA03), dining x2 and daybed (V6 n/e), dressing room (V6 -40 %, documented); the 9 failures are that dressing row (1) and V10 against the old products (8).

## 1. Cycles throws the wallwasher 90 deg off (LV defect A)

* **Cause.** `villa_scene.add_light` built the light with `to_track_quat("-Z","Y")` plus a fixed +90 deg azimuth, calibrated on straight-down lights where
  roll about the aim is invisible. For a tilted aim the track quaternion's roll differs from the engine's (`Placement.rotation()` = Rz(az) Ry(-tilt) Rz(spin)).
  Probe (LV `kind_orientation`, one WW at its design aim): total +35.6 %, pattern error 153 %.
* **Fix.** `ies_rotation(aim, spin)`: the light's matrix is the engine's own rotation composed with the calibrated Rz(90). General for every aim and spin, no
  wallwasher special case. Inside `add_light` and its helpers only.
* **Proof.** LV probe, every kind, before -> after (total / pattern L1): WW +35.6 / 153 % -> **+1.2 / 2.8 %**; DL -1.19 / 2.62 % -> -1.19 / 2.62 % (same numbers); PEN-LIN
  (Jilly) -0.93 / 2.77 % -> unchanged; DESK -7.7 -> +1.0 %. `tests/lightcalc/test_light_orientation.py` (13 cases incl. all four tilt azimuths; straight-down matrices
  identical to the old construction; negative: the old matrix differs for the WW aim). V5 for the rooms with wallwashers: corridor (stair / circulation) direct **+164 % -> -2.2 %**,
  cinema **-0.1 %** (direct +2.0 %), parents' ensuite direct **+9 % -> -0.6 %**; all 20 V5 rows pass (bars 3 % direct / 10 % total; worst total -6.8 % stair, -4.9 % pantry).
* ADJ in the probe reads -9.0 / -4.4 / -0.9 / +1.9 % for 0 / 45 / 90 / 180 deg of roll about its own axis although the file is axisymmetric: a 5.7 deg beam
  sampled by points 1 m apart, i.e. probe sampling noise, not orientation. The new 28 deg ADJ reads -4.8 % (L1 5.6 %).

## 2. Lucy -7.7 %, parents' bedroom Cycles -4.2 % (LV defects B, C)

* **Cause (renderer error, found by experiment).** Blender 4.5's IES import renders a Type-C file with several horizontal planes dimmer than the same
  candela table as one plane. One ERCO downlight table written as 1, 2 (0 and 360), 3, 5, 6 (with and without the 360 plane), 9, 37 planes reads
  -1.2, -1.2, -5.1, -7.3, -8.0, -8.0, -8.3, -8.6 % against the analytic path; per point a uniform factor 0.914 (not a shape error). Lucy has 73 planes (-7.7 %),
  the wallwasher 145 (-7.5 %). `IES_POINT_POWER` was calibrated on single-plane files. Flux normalisation (`ies_flux`) is right for all files (1066.0 vs 1065.9 lm DL;
  233.8 vs 233.9 DESK), so it is the import, not the maths.
* **Fix.** `IES_MULTIPLANE_GAIN = 1.094` for files with >= 6 planes (`ies_plane_gain`). Residuals after: DESK +1.0 %, WW +1.2 %, DL table as 37 planes +0.0 %.
  Guard: `test_multiplane_files_get_the_measured_gain...`.
* **Bedroom.** The -4.2 % was not Lucy or the wallwasher (neither is in the room): in the L6b/L6c frozen results the bedroom's direct light at LV's points was 69-99 % the
  wall reading lights and 18-58 % the bed / entry downlights seen 34-44 deg off their axes. The single-light probe shows where Cycles reads low for a single-plane
  downlight: 0.903 of the analytic value at 46 deg off the axis (the steep cut-off edge, I falls 179 -> 51 cd between 44 and 46 deg) against 1.00-1.03 elsewhere. That is the
  renderer's IES interpolation at a steep edge, a limit of the method (analytic = Radiance to 0.0 % there). With the design change (LA4) and the finer grid the bedroom reads
  direct **+0.9 %**, total **+3.7 %** vs Radiance. Not tuned.

## 3. Bed downlight glare (LA4)

* **Cause.** LA4 had one reclined sightline (toward the foot, 17 deg up); `DL-parents-bed-04` is 53.7 deg from it, outside the 45 deg cone, so it passed at **89 953 cd/m2**
  (cap 3000) although it is 39.4 deg off the vertical of a person lying on the pillow (inside the cone). On the pillow eyes of a double bed: 118 820 cd/m2 (bed DL), **122 595
  (entry-lobby DL, open to the bedroom, no door)**, kids' B ambient DL 113 931. The ERCO DL stays above 3000 cd/m2 up to 48 deg off its axis, so a DL must be >= 2.0 m in plan from every pillow eye.
* **Check.** `villa_checks.bed_lying_sightlines`: eye on each pillow, looking straight up, every bed of every bedroom (parents' two pillows; kids' B head to the west wall; the bunk's
  head end is not declared so both ends, upper berth eye 1.5 m ASSUMED from the 1.7 m bunk). Policy SourceCard `L6-POLICY-LA4-bed-lying-looking-up`.
  `tests/lightcalc/test_la4_bed_lying.py`: today's positions fail (113-123 kcd/m2), the old sightline passes them (the gap), the design passes, a DL 2.3 m away / a shielded DL stay quiet.
* **Design (smallest change).** Parents' ambient DL (19.03, -25.19) -> foot of the bed on its axis (20.33, -23.95), 2.28 m from the nearer pillow; kids' B ambient DL -> over the desk axis
  (17.65, -25.86), 2.25 m from the pillow. The entry-lobby DL cannot be placed 2.0 m from both pillows (the lobby is 1.0 x 0.68 m): replaced by a **cove** (generic, hidden behind its upstand: ASSUMED,
  not an LA4 product check). A deeper/low-luminance optic was not an option: the cap is 3000 cd/m2 and no V10-verifiable product is that dim inside 48 deg. New plane `room-parents-entry`
  (passage card, min 30 lx): Radiance 71 lx mean, 57 lx min (the lobby had no plane; the DL's removal would have left it at about 4 lx direct). Bedroom cards re-checked by Radiance:
  pillow-1 207 lx, pillow-2 201 lx (card 200), room plane Emin 84 lx (card 50). V12 (all 40 planes): worst 0.761.
* The new ADJ in the bedroom reads 1656 cd/m2 toward pillow 2 (cap 3000).

## 4. Dining pendant (ERCO Jilly, 3.9 % / 6.1 %)

* **Product.** ERCO has no pendant that fits (Jilly 3558 lm and up; Atrium with uplight). **iGuzzini QA03** Laser pendant O59 (831.6 lm, 44 deg, 2700 K, CRI 90, DALI-2, no light above 90 deg):
  V10 pass (lumens 0.08 %, Imax 0.5 %, beam 0.7 %); alternate QA11 (766.8 lm, 38 deg). Product page gives no minimum dimming level and no flicker data: **flagged**, the supplier row asks.
  Size 59 mm, the 1.8 m table x 2/3 = 1.2 m limit (policy; no source held: marked policy).
* **Design.** ONE pendant (a single point lights a pool of ~0.65 m), hung 0.15 m west of the table centre so the homework end (Day, 200 lx) is reached. Two pendants cannot be run at 15 %.
* **Levels per scene (zone driver 0.35):** Day 35 % (was 13 %), Dinner **15.1 %** (was 6.1 %; scene level 0.43), Evening **15.8 %** (was 3.9 %; level 0.45). Results: dining table (Dinner) **104 lx** (card 100),
  homework end (Day) 199 lx (card 200). Guard: every zone x scene >= 15 % outside Night/Film (`test_l6d.py`).
* The render draws the pendant with the linear-pendant branch (a 59 x 59 x 60 mm body; the real body is 250 mm): the 250 mm body makes a wire shape `c3-part-exemptions.json` does not admit.
  **Open item for the render lane.**

## 5. ADJ (A9000028, V10 partial)

* **Product.** ERCO **A9003138** Optec New spotlight S, flood 28 deg, 760 lm, 2700 K, CRI 92, DALI-2 track adapter, dimming 1-100 % CCR: V10 pass (lumens 1.4 %, Imax 1.5 %, lux on axis 1-5 m <= 1.9 %,
  beam diameters <= 3.1 %, beam angle published 28.0 vs file 28.9 deg). Alternates in the supplier row: ERCO 68887 Starpoint (recessed, 551 lm, 26.8 vs 27.7 deg), 68119 Gimbal. The 14 deg spots (A9002988, 68116) are V10 partial
  (file beam 6 % wider than published) and not used; Optec New M/L exist only as 4-5 deg spots.
* **Armchair (card 200 lx, Reading).** Driver **0.35** (was 0.66). Pessimistic reading of the beam (20 % narrower than the file): Imax kept (flux falls) needs **0.42**; flux kept needs **0.27**; both <= 0.80
  (`test_armchair_card_is_met_at_or_below_080_under_the_pessimistic_beam`, computed from the Radiance zone results and the analytic direct ratio 0.84 / 1.30).
* ADJ is now a flood; the sideboard and vanity accents are wider pools than the 5.7 deg spot made.

## 6. Other zones below 15 %

* Island globes (Reading) 14 % -> **15.4 %** (Reading level of the island pendants 0.22; cheap, no card moves). Table pendant: item 4.
* Night / Film at 10 % are intended. ERCO DL (`Z-B-LOUNGE-ROUTE-NIGHT`): datasheet 41321 "Dimming range 1 %-100 %", CCR, TLA SVM <= 0.1, PstLM <= 1 (level of the measurement not stated): floor 1 % < 10 %. **Generic night
  kinds (NL, TOE, STEP, PATH: 14 zones) have no datasheet: flagged.** The supplier schedule now requires DALI-2 1-100 % and asks for the lowest level and the flicker data at it (needed <= 1 %).

## 7. Radiosity test

* Restored: three converging rooms at **6 %** with 16 patches (guest WC +2.0 %, dressing +0.9 %, family bath -0.8 %). The pantry is a strict `xfail` with the numbers.
* **Pantry diagnosis (not an engine error).** Its Radiance plane is 8 points (x 4.50-6.06, y -29.42 / -29.02) of a 2.92 x 1.00 m floor; the radiosity averaged the whole floor including the dark ends. At the plane's own 8 points the same solver gives
  197.0 / 197.8 / 197.5 lx at 16 / 24 / 32 patches vs Radiance 199.1 (-1.0 / -0.7 / -0.8 %); the area mean 185.1 / 181.9 / 180.5 lx (-7.0 / -8.7 / -9.3 %) falls as the ends are resolved. Direct light at those points: analytic 106.6 lx = Radiance 106.6.
  `radiosity.floor_lux_at` + `test_radiosity_at_the_plane_points_agrees_with_radiance` (all four rooms within 6 %: pantry -1.0, guest WC +2.7, family bath +1.8, dressing +0.6 %).

## 8. V7 grid pitch

Corridor 0.85 m -> **0.30 m** (LV V7 now 0.28 m actual: halving -0.77 %; was -6.23 %); parents' bedroom 0.43 m -> **0.20 m** (halving +0.17 %; was -3.39 %, a hot spot of the old bed DL: with the DL moved even 0.43 m gives +0.6 %).
`test_l6d_grids_converge_under_2_percent`. Worst remaining halving change of any plane: 2.41 % (ka-desk-1, bar 3 %). ab 12 -> 24 worst 1.36 % (pillow-2).

## Receipts, exposure record, production scene (last step, after merging `origin/integ/staging` `b577bf5`)

Baseline-relative procedure (RA2/INT2b): old = `origin/integ/staging` tree (worktree), new = this branch, both exported with receipts bypassed (`refresh_furniture_integ5.py export`). **The old tree reproduces all 8 stored
section digests** (`section_diff.py`: `receipt_component` true for every section). Differences (everything else identical: layout, specification, furniture, architecture, models, props):

| section | change | cause (all this lane's fixes; no change from lanes already on staging) |
|---|---|---|
| meshes | removed `fix-/lens-DL-parents-entry-01` | the entry-lobby downlight replaced by a cove (LA4) |
| meshes | changed `fix-/lens-DL-parents-bed-04`, `fix-/lens-DL-kids-b-01` | those downlights moved out of the 45 deg cone over the pillows (LA4) |
| meshes | changed `fix-ADJ-parents-bed-05` | the ADJ product A9000028 -> A9003138 (housing/trim from its file) |
| materials | changed `led-lin-2700` | the table pendant's emissive diffuser: 3558 lm over the Jilly's diffuser -> the QA03's lumens over its own |

17 baseline-relative reviews (16 individual + joint): all ok, 0 findings (`refresh_furniture_integ5.py review-current`); receipts rewritten with `refresh_receipts.py` (visual approvals retained: none of the sixteen items is in a room whose look changed:
the pendant, a cove and three downlight trims). Evidence: `out/L6d-rc/section-diff.json`, `out/L6d-rc/review.log` (not committed).

Exposure record re-measured on the L6d lighting (stale transport hash: the lights changed): jobq `L6d-measure-exposure-1` (GPU lock, `villa_scene.py --measure-exposure-groups` on the measure scene, full ies dir including `erco/A9003138.ies`), the
measured `exposure-group-measurements.json` copied byte-for-byte to `knowledge/exposure-groups.json`. **Staging then moved** (SC and MK merged, `06cdd7e`): merged again (only `knowledge/exposure-groups.json` conflicted: their version taken), the production
build passed the receipt guard unchanged (SC's changes are outside every receipt section, so the receipts above stand), the exposure record was stale again and re-measured (`L6d-measure-exposure-2`, copied unedited). Production scene rebuilt without bypass
(`scripts/benchmark_scene_build.py --write-scene`, receipts and record active): **1,221 meshes** (SC's additions included; this lane alone removed the entry-lobby downlight's trim and lens), 113 lights (4 ADJ on `erco/A9003138.ies`),
scene sha256 `5968c5b8c580fcc93fdb27f0e8f70e4dbd9d8e2562236391d44fd72fc6a8dd77`, ids-stripped sha256 `d6e66841555083529fa5a0b278a96345c1dd162d33331f142605019a96e61773`,
producer source hash `8273ba79af3be2119625c60809c8774ce6fa1b34afb015f3e86e2461ca6aa96e`.

## Receipts, exposure record, production scene (after merging `origin/integ/aplus`, SC2)

Merge conflicts: only `knowledge/exposure-groups.json`, `knowledge/furniture-stage2.json.gz`, `knowledge/parents-bed.json.gz` (their version taken, then regenerated below). Code merged without conflict (SC2's `d1-elements.json`, `revit_spec.py`, `parity/*` kept alongside this lane's changes).

Receipts (RA2 procedure; old = `origin/integ/aplus` worktree, new = this branch, both exported with receipts bypassed): the old tree reproduces all 8 stored section digests. Changed sections, all this lane's:
meshes (removed `fix-/lens-DL-parents-entry-01`; changed `fix-/lens-DL-parents-bed-04`, `fix-/lens-DL-kids-b-01`, `fix-ADJ-parents-bed-05`) and materials (`led-lin-2700`): the same four causes as before (LA4 entry cove, LA4 downlight moves, ADJ A9003138, QA03 pendant diffuser).
**No section changed because of SC2** beyond what the stored receipts already hold (layout, specification, furniture, architecture, models, props identical). 17 baseline-relative reviews all ok, 0 findings. Evidence `out/L6d-rc2/` (not committed).

Exposure: re-measured (jobq `L6d-measure-exposure-3`, copied unedited). Changes against SC2's record are the L6d lights plus SC2 geometry reading through: lamp fractions move <= 0.01 in every view (largest v33 0.0197->0.0247, v29 0.4726->0.4722, v23 0.848->0.854);
no group flips its side of the 0.5 threshold. Production scene (`benchmark_scene_build.py --write-scene`, receipts and record active, no bypass, jobq `L6d-prod9`, clean checkout at `875781b`): scene.json sha256 `a32842521bab9896bc03b155ef12d2b6f798ab137f0a89b1255abc9c4be9bd19`, ids stripped
`0165935f48b5de45a39a1594281fdf143acf4b77f99f2ae08b4a81475ef6c3d4`, **1,221 meshes** (SC2 1,223 minus the entry-lobby downlight's two), **113 lights** (4 ADJ on `erco/A9003138.ies`), source hash `4fcb8572777f8913de5739239faa33c9e62e90e3fca09f840f99f31435ece1e9`.

`lightverify --design D1 --scene` on it: 401 results, 389 pass / 9 fail / 3 n/e; **35 of 40 rows verified**. The 9 fails: 8 are LV10 on the old products (ADJ A9000028 bound-file + beam dia 1-5 m + beam angle; Jilly 50674 bound-file), the cause of the 4 LV tests pinned to old products;
1 is the documented LV6 miss `GF-parents-dressing` (engine 390 lx vs lumen method 646 lx, room index 0.43). Nothing else fails. LV owns `docs/lanes/LV-report.md`; the regenerated copy is not committed.

## Open items

* **LV's V10 is hard-wired to the old products** (ADJ A9000028, Jilly 50674): it reports the new bound files as "DIFFERS" (8 failures); `tests/lightverify`: 51 pass, 4 fail by design (`test_v10_erco.py` x2: ADJ partial / Jilly points; `test_v1_design.py` x2: the Jilly's 8 samples), all four encode the L6c products and are LV's to update; the orientation and radiance-baseline tests pass.
  The new products' own V10 numbers are in `knowledge/lighting-products/*/source.json` (lane L6d, from the maker's data sheet / page). LV must add A9003138 and QA03 (and the 8-sample Jilly logic goes).
* LV's `run_cycles` cache and jobq id do not include the renderer source: a renderer fix is invisible to a re-run. Hash `villa_scene.py` into the job.
* V6 n/e for dining-table, homework-end and daybed (LV does not read `v6-subplanes.json`); the dressing room V6 -40 % is the documented miss (lumen method at room index 0.43).
* V11 (DIALux) not run; V9 declined. QA03 minimum dimming level and flicker: supplier. Generic night strips: supplier states the lowest level.
* `tests/test_mounting_scene.py::test_lead_ceiling_requirements...` pins ADJ housing depth 169 mm; A9003138's is 174 mm (SC's file, one number).

Reproduce: `python -m archpipe.lightverify --design D1 --scene <scene.json> [--regen-radiance --freeze]`; `python -m archpipe.lightcalc.villa_run --tag d2 --out out/L6d` (all clusters, ab 12 + 24) then `villa_tune_cli` (dry run: drivers equal the table for the zones this lane changed) and
`villa_emit`; `python -m archpipe.luminaires.spec_sheet`; `python -m archpipe.exchange.integrate`.

## Final round (2026-11-22, after merging `origin/integ/aplus` again)

* Merge clean. Spec sheet regenerated (no prices); `exchange.integrate` re-run: downstream outputs unchanged except the lighting load (committed); its suite 761 pass, 4 fail (the LV tests that pin QA03/old products, below).
* Production build first refused (stale exposure transport hash, as designed): exposure record re-measured (max lamp-fraction change 0.0003), then the build passed with receipts and record active, no bypass: scene sha256 `a15e7078d2875995923651c0f2781577852cab539e7c6e142f5177b820f6c08a`, source hash `c1cb03c1b33fed4674cc516d1747f619918c42827e7975336819188872d4673c`. The receipts needed no rewrite (the merge touched no receipt section).
* `lightverify --design D1 --scene` on it: 450 pass / 1 fail / 3 n/e; **39 of 40 rows verified**; the one fail is the documented LV6 miss `GF-parents-dressing` (-40 %, room index 0.43).
* Previews re-rendered (jobq, 32 samples) in `knowledge/lighting/previews-l6d/`. Trap met again: **a jobq id that already exists returns the OLD job** (three of my "new" builds were old results); use a unique id per run.
* Tests pinning the old product (LV's to update): `tests/lightverify/test_v10_erco.py` x3 (`test_tables_follow_the_binding_not_ids_in_the_code`, `test_a_wrong_iguzzini_lumen_figure_is_caught`, `test_cri_overstated_in_the_record_fails_and_understated_is_flagged`), `test_v1_design.py::test_bound_pendant_is_one_emitter_at_its_record_flux`.
  `test_v5_orientation.py::test_orientation_probe_stays_quiet_for_a_symmetric_downlight` fails only in a fresh clone re-using a clone path: LV's `lv-cycles-DL-*` jobq id is keyed on the job JSON (which holds the path), so a deleted clone's finished job is returned and its exr files are gone. Passes in the lane tree; not a design fault.
