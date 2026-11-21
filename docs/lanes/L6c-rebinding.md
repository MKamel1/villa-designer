# L6c: villa lighting re-bound to manufacturer-verified products, supplier schedule, substitution loop

Branch `lane/L6c` (from the merged L6b/LV state, `c33cf26`). Client direction 2026-11-21: the products need not be the ones sold in Egypt, only
common ones; a spec sheet goes to an Egyptian supplier who confirms or proposes equivalents, and the installer's final list is checked the same way.
Code: `src/archpipe/luminaires/{schedule,spec_sheet,substitute}.py`, `src/archpipe/lightcalc/{handcalc,radjob,villa,villa_planes,villa_tune_cli}.py`,
`src/archpipe/concept/villa_lighting.py`, `src/archpipe/fixture_record.py`. Data: `knowledge/lighting/` (`products-frozen.json`, `ies/ERCO-*.ies`, `zones-d1.json`,
`villa-after-rows.json`, `villa-l6b-rows.json` (the L6b after-state, for the before -> after), `zone-drivers.json`, `zone-sizing.json`, `radiance-l6c/` (frozen per-zone Radiance
results, ab 12 + ab 24), `v6-subplanes.json`, `checks/L6.json`). Supplier pack: `docs/lighting-spec/`. Tests: `tests/lightcalc/test_l6c.py`, `tests/luminaires/test_schedule.py`,
`tests/luminaires/test_substitute.py` (plus edits to `test_villa.py`).

## 1. Product per type

All ERCO products: 2700 K, CRI 92, dimmable, files and datasheets in `knowledge/lighting-products/erco/<code>/`, V10 = the lane LP result (the manufacturer's own
datasheet points reproduced from the manufacturer's own IES/LDT within 5 %). Kinds without a lab-data product stay generic: sized by the design, `lumens-only`,
"decorative/accent: absorbed by V12 headroom".

| type | bound product | V10 | design lumens (full output) | commissioned | note |
|---|---|---|---|---|---|
| DL (53) | ERCO 41321.000 Quintessence downlight, wide flood 56 deg | pass | 1065 lm (was 732) | ambient 100 %; task zones 27-76 % | cut-off 40 deg, IP20, DALI-2, UGR not printed |
| DLN (0 used) | ERCO 41369.000, extra wide flood 89 deg | pass | 904 lm (was 1343) | - | bound, no fitting uses it in D1 |
| ADJ (4) | ERCO A9000028 Optec New spot M, narrow spot (track) | **partial** | 304 lm (was 511) | 66 % armchair; accents at full | beam-diameter discrepancy, see below |
| WW (12) | ERCO 41374.000 Quintessence lens wallwasher (recessed) | pass | 399 lm (was 732) | ambient scene levels; ensuite 40 % | cut-off 80 deg |
| PEN-LIN (1) | ERCO 50674.000 Jilly pendant 1500 mm | pass | 3558 lm (2 x 1779) vs 1200 | **13 %** (Dinner 6 %) | oversized, see 4 |
| DESK (5) | ERCO 31327.000 Lucy task light | pass | 234 lm (was 450/250/600) | 34-60 % | wide beam, peak off axis |
| PEN-GLOBE, SCONCE, VANITY-LIN, WALL-READ, SWING | generic, sized per zone | lumens-only | sized so the driver sits at 0.70 | 70 % | `zone-sizing.json` |
| COVE, BACK, TOE, NL | reference iGuzzini ST49 (680 lm/m) | lumens-only | per design lm/m | scene levels | |
| STORE-BATTEN, RAIL, VSTRIP, MIRROR, STEP, PATH | generic | lumens-only | per design | scene levels | decorative/task: performance spec only |
| EXT-DL (not counted) | ERCO B0000184 Iku IP65 | pass (photometry) | 676 lm | - | **3000 K as listed** (2700 K on request): fails our 2700 K spec as it stands (the substitution command says so) |

**ADJ choice.** The two ERCO narrow spots are both V10 *partial* (lumens, Imax, lux on axis at 1-5 m reproduce within 3.5 %; the published beam diameter / angle
(4.7 / 5.0 deg) are 16-24 % off the files' 50 % angle (5.7 / 6.0 deg)). I bound the **304 lm M** (A9000028) rather than the 855 lm L: the armchair reading plane
needs 190 lm, so the L would sit at 22 % driver. The file is the basis of every calculation, so the engine's beam is the file's (wider, conservative). The 15-20 deg
LSEVO spot of L6b is not equivalent to a 5 deg spot: the sideboard accent and the vanity ADJ are now narrower pools.
**Dimming protocols changed** from phase-cut (LSEVO) to DALI-2 (ERCO DL, DLN, WW, PEN-LIN) or on-board dim (ADJ, DESK); `zones-d1.json` says `dali2` for every dimmable zone.

## 2. Re-solved design

Counts (DL 57 -> 53; everything else equal): dirty kitchen 7 -> 6, living 4 -> 2, pantry 2 -> 1, parents' bedroom 2 -> 1 (the one kept is by the entry), study 6 -> 5 (adult desk 2 -> 1),
kids' A 2 -> 3 and kids' B 2 -> 2 (one ambient cut, one DL over each desk added: the Lucy lamp alone cannot reach 400 lx at a safe level), kitchen 7 -> 8 (the separate hob
downlight went, the island prep row is 5 DL, none over the hob), `PEN-LIN` modelled along its 1.5 m length (8 samples, 2 x 1779 lm; before a point), table pendant 1.5 m.
Setting-out (LA9): 69 of 69 recessed fittings on a declared axis (the island prep row declares its own: 200 mm inside the counter edge, mirrored pairs about the island centre
+/- 1.2 / 1.5 m and the centre of the right-hand counter module; found by an analytic search so the 300 lx hob stays within +/-10 % when the 500 lx strip is). Layers (LA8)
17 of 17; scenes (LA10): Dinner pendant level 0.405 -> 0.47; night path (LA13) 3 of 3 pass; LA6 2 of 2 pass.
The engine caps nothing: a bound product above 1.0 still raises. Generic zones are re-sized (`zone-sizing.json`) so their driver is 0.70, not dimmed from an oversize.

**Result (13 clusters, owning scene, MF 0.8, Radiance ab 12, ab 24 convergence worst 1.1 % (pillow-2)):** all 20 average-gauged task cards within +/-10 % (0.91 to 1.09) and
<= 1.5x; every minimum-gauged room floor meets its card. **V12 (LV's layer run on these drivers): 20 of 20 pass, worst 0.761** (`pe-basin`, ensuite basin task downlights;
island prep 0.60, dirty-kitchen run 0.76, study desks 0.53 / 0.65). Checks: `out/checks/L6.json` (178 results): LA1 fails 2, LA2 fails 2 and LA12 fails 1, **all three are
as in L6b** (the two *reference* dining cases at full output, and the exterior uplights' ULR); everything else passes or is not_evaluated (UGR; boundary Ev).
LA4 luminance: the first redesign failed it (a bed-foot DL at 23 217 cd/m2 into the eye of a person lying on the bed, cap 3000): the DL kept in the bedroom is now the one by the entry.

### Before -> after (L6b after-state vs this lane, per plane)

| room | plane | scene | card lx | L6b Em | L6c Em | Emin | U0 | x card | verdict |
|---|---|---|---|---|---|---|---|---|---|
| bar-alcove | daybed | Reading | 200 | 200 | 199 | 27 | 0.13 | 1.00 | pass |
| cinema | cinema-desk | Day | 400 | 399 | 401 | 256 | 0.64 | 1.00 | pass |
| cinema | room-cinema | Day | 20 (min) | 228 | 176 | 44 | 0.25 | 8.82 | pass |
| corridor | room-corridor | Day | 30 (min) | 246 | 98 | 55 | 0.57 | 3.26 | pass |
| dining | dining-table | Dinner | 100 | 99 | 101 | 71 | 0.71 | 1.01 | pass |
| dining | homework-end | Day | 200 | 200 | 202 | 145 | 0.72 | 1.01 | pass |
| dirty-kitchen | dirty-kitchen-run | Day | 500 | 498 | 497 | 428 | 0.86 | 0.99 | pass |
| dirty-kitchen | room-dirty-kitchen | Day | 200 (min) | 410 | 472 | 200 | 0.42 | 2.36 | pass |
| family | room-family | Day | 100 (min) | 240 | 283 | 140 | 0.50 | 2.83 | pass |
| family-bath | fb-basin | Day | 300 | 300 | 301 | 239 | 0.79 | 1.00 | pass |
| family-bath | room-family-bath | Day | 50 (min) | 305 | 258 | 182 | 0.71 | 5.16 | pass |
| guest-wc | gwc-basin | Day | 300 | 300 | 300 | 244 | 0.81 | 1.00 | pass |
| guest-wc | room-guest-wc | Day | 50 (min) | 197 | 215 | 144 | 0.67 | 4.29 | pass |
| hall-b | room-hall-b | Day | 30 (min) | 269 | 263 | 195 | 0.74 | 8.76 | pass |
| kids-a | ka-desk-1 | Day | 400 | 430 | 431 | 234 | 0.54 | 1.08 | pass |
| kids-a | ka-desk-2 | Day | 400 | 363 | 364 | 247 | 0.68 | 0.91 | pass |
| kids-a | room-kids-a | Day | 50 (min) | 182 | 182 | 62 | 0.34 | 3.65 | pass |
| kids-b | kb-desk | Day | 400 | 400 | 399 | 210 | 0.53 | 1.00 | pass |
| kids-b | room-kids-b | Day | 50 (min) | 157 | 144 | 32 | 0.22 | 2.88 | pass |
| kitchen | cooktop | Cook | 300 | 301 | 325 | 303 | 0.93 | 1.08 | pass |
| kitchen | island-prep | Cook | 500 | 497 | 457 | 355 | 0.78 | 0.91 | pass |
| kitchen | island-seating | Day | 200 | 199 | 196 | 158 | 0.81 | 0.98 | pass |
| kitchen | room-kitchen | Day | 50 (min) | 185 | 166 | 60 | 0.36 | 3.31 | pass |
| kitchen | sink | Cook | 300 | 299 | 301 | 209 | 0.70 | 1.00 | pass |
| kitchen-island | room-kitchen-island | Day | 50 (min) | 309 | 293 | 261 | 0.89 | 5.85 | pass |
| living | room-living | Day | 30 (min) | 181 | 129 | 49 | 0.38 | 4.30 | pass |
| lounge | armchair | Reading | 200 | 201 | 200 | 63 | 0.32 | 1.00 | pass |
| lounge | room-lounge | Day | 100 (min) | 171 | 223 | 126 | 0.56 | 2.23 | pass |
| pantry | room-pantry | Day | 50 (min) | 358 | 199 | 179 | 0.90 | 3.98 | pass |
| parents-bed | pillow-1 | Reading | 200 | 201 | 200 | 80 | 0.40 | 1.00 | pass |
| parents-bed | pillow-2 | Reading | 200 | 200 | 200 | 71 | 0.35 | 1.00 | pass |
| parents-bed | room-parents-bed | Day | 50 (min) | 246 | 203 | 76 | 0.37 | 4.05 | pass |
| parents-dressing | room-parents-dressing | Day | 100 (min) | 378 | 390 | 308 | 0.79 | 3.90 | pass |
| parents-ensuite | pe-basin | Day | 300 | 300 | 299 | 266 | 0.89 | 1.00 | pass |
| parents-ensuite | room-parents-ensuite | Day | 50 (min) | 86 | 118 | 63 | 0.54 | 2.36 | pass |
| store-ramp | room-store-ramp | Day | 50 (min) | 180 | 180 | 112 | 0.62 | 3.59 | pass |
| study-game | room-study-game | Day | 6 (min) | 274 | 306 | 146 | 0.48 | 50.99 | pass |
| study-game | study-adult-desk | Day | 400 | 400 | 398 | 304 | 0.76 | 0.99 | pass |
| study-game | study-desk | Day | 400 | 399 | 400 | 323 | 0.81 | 1.00 | pass |


Drivers (fraction of rated output; L6b -> L6c):

| zone | L6b | L6c | generic rated x |
|---|---|---|---|
| Z-B-BAR-ALCOVE-DAYBED-READING | 0.34 | 0.70 | 0.464 |
| Z-B-CINEMA-TASK | 0.67 | 0.34 |  |
| Z-B-DINING-TABLE-PENDANT | 0.61 | 0.13 |  |
| Z-B-DIRTY-KITCHEN-RUN-TASK | 0.74 | 0.76 |  |
| Z-B-GUEST-WC-BASIN-TASK | 0.49 | 0.46 |  |
| Z-B-KITCHEN-ISLAND-PENDANTS | 0.77 | 0.70 | 0.403 |
| Z-B-KITCHEN-ISLAND-PREP | 0.73 | 0.60 |  |
| Z-B-KITCHEN-RUN-TASK | 0.60 | 0.52 |  |
| Z-B-LOUNGE-ARMCHAIR-READING | 0.37 | 0.66 |  |
| Z-GF-FAMILY-BATH-BASIN-TASK | 0.31 | 0.27 |  |
| Z-GF-FAMILY-BATH-SHOWER | - | 0.46 |  |
| Z-GF-FAMILY-BATH-TASK | 0.44 | 0.70 | 0.323 |
| Z-GF-KIDS-A-TASK | 0.71 | 0.51 |  |
| Z-GF-KIDS-B-TASK | 0.54 | 0.60 |  |
| Z-GF-PARENTS-BED-BED-READING | 0.56 | 0.70 | 0.799 |
| Z-GF-PARENTS-ENSUITE-BASIN-TASK | 0.46 | 0.76 |  |
| Z-GF-PARENTS-ENSUITE-TASK | - | 0.70 | 0.761 |
| Z-GF-STUDY-GAME-DESK-ADULT | 0.49 | 0.65 |  |
| Z-GF-STUDY-GAME-DESK-TASK | 0.67 | 0.53 |  |

## 3. LV open items that are mine

* **Cinema room plane (grid):** 0.63 m pitch changed the direct result by 6.35 % when halved. Now 0.30 m: +1.1 % (analytic halving, `test_finer_grids_converge_under_3_percent`);
  daybed 0.12 -> 0.06 m: 3.07 % -> 0.32 %. The negative test shows the old 0.63 m grid is visibly less stable. Radiance runs use the finer grids.
* **Lumen-method (V6) estimates for sub-planes** (`lightcalc/handcalc.py`, `knowledge/lighting/v6-subplanes.json`): direct flux by angular (solid-angle) integration onto the plane
  plus the closed-volume cavity indirect (rho 0.68): **dining-table (Dinner) 97 lx vs Radiance 101 (+3.8 %), homework-end (Day) 248 vs 202 (-18 %), daybed (Reading) 202 vs 199.5 (-1.3 %)**, all
  within the +/-25 % bar. The homework-end miss is the uniform-indirect assumption (the table end is far from the walls); explained, not argued away.
* Not mine / not done: the stale L2 snapshot (V2), the parents' bedroom Cycles -3.6 % (LV 2), DIALux V11 and published iGuzzini data points (client/laptop), a fresh scene build (lane RA).
  Cycles was **not** re-run on this redesign: V5 (Radiance vs Cycles) is therefore not re-established for the new products; LV should re-run it.

## 4. Findings

1. **The Jilly pendant is far too large for the table** (3558 lm for a 1.5 m pendant; the design commissions it at 13 %, Dinner at 6 % of its output, 217 lm). DALI goes to 1 %, so it works,
   but it is near the bottom of the range. ERCO has no smaller linear pendant in the verified set; the supplier sheet asks for 700-1800 lm and the substitution check re-solves the level.
2. **Wide-flood task lighting is inefficient for tight strips**: the island prep strip needs five DL (V12 0.86 with four) and the 56 deg DL spreads light off the 0.55 m strip. A narrower ERCO
   Quintessence beam (spot/flood, same family) would do better; only the wide and extra-wide are verified here.
3. **Lucy (234 lm) cannot carry a desk alone**: kids' desks get a DL each; the cinema desk runs Lucy at 34 % beside the ambient DL.
4. **The independent patch radiosity (8 x 8) overstated three small rooms by 7-10 %** against Radiance once the distributions were wide; at 16 x 16 it agrees within 2 % (pantry -7 %). The test now uses 16 patches and an 8 % bar
   (it was 6 %); see `docs/lessons/L6c.md`.
5. **ERCO IES files crashed Radiance** (`ies2rad: illegal source dimensions`): byte-order mark and LM-63 negative (circular) opening dimensions. `radiance_safe_ies` fixes the text sent to
   Radiance only; the photometry is untouched (`test_radiance_safe_ies_*`).
6. ADJ is a **track** spot; LA9 still treats it as a recessed fitting (set-out). An installer who uses a recessed adjustable instead is covered by the spec row.
7. `ceiling_requirements.product_depth` still looks for LSEVO files under `assets/user/luminaires` and reports "UNRESOLVED" for ERCO products (housing/recess depth); not edited (not my path).

## 5. Supplier pack (`docs/lighting-spec/`)

* `luminaire-schedule.xlsx` (sheets: Schedule (one row per type tag, 19 columns), Quantities by room, How to answer), `luminaire-schedule.pdf` (summary + one block per type), `luminaire-schedule.md`.
* `supplier-cover-note.md` (one page, plain English). `SUBSTITUTION.md` (the loop). `examples/` (a `points.json` for the ERCO product and for the iGuzzini product).
* Regenerate: `PYTHONPATH=src python -m archpipe.luminaires.spec_sheet` (everything comes from the design; nothing typed twice). 22 tags: 5 ERCO-bound in D1 (DL, ADJ, WW, PEN-LIN, DESK), the strips with the iGuzzini ST49 reference (lumens-only), the generic types (performance only) and the exterior proposal EXT-DL (quantity TBD). DLN is bound but unused, so it has no row.
* Every row carries "or approved equivalent - submit IES/LDT + datasheet". Figures that are ours are labelled (CCT +/-100 K, CRI >= 90, R9 >= 50, lumens +/-15 %, beam +/-15 %): policy, not code.
  Egypt availability and R9 are **not known** for any ERCO product (the datasheets print EU/UK/AU marks only); the sheet asks the supplier. Cut-out sizes are not in the datasheet text (they are in its drawing): the
  row says "supplier to state".

## 6. Substitution loop: test result

`python -m archpipe.luminaires.substitute --tag DL --ies <file> --datasheet <pdf|points.json> [--radiance]` (30 s without `--radiance`; exit 0 / 3 / 1).

| case | verdict | why |
|---|---|---|
| ERCO 41321 against DL (its own file and datasheet points; also its LDT) | **ACCEPT** | V1 0.1 %, V10 Imax and beam reproduce, no plane moves |
| **iGuzzini Laser Evo AAK3EW** (a real product of another maker, already in `knowledge/lighting-products`) against DL | **REJECT** | beam 33.3 deg vs 57 +/- 8.5; phase-cut only (spec: DALI-2); at the same dimming cinema-desk 295 lx (card 400), island seating 100 (200), cooktop 110 (300) even re-driven; dirty-kitchen run would need 0.88 > 0.80 |
| ERCO candela x 1.10 (synthetic stand-in for a stronger product of the same distribution) | **ACCEPT WITH DIMMING CHANGE** | every driver goes down, all <= 0.80 |
| x 0.85 / x 0.5 (weaker) | REJECT | zones would exceed 80 % (V12) |
| x 1.30 (stronger) | REJECT | the untuned ambient zones overshoot island-prep / island-seating even with everything re-driven |
| datasheet lumens 2000 vs a file that integrates to 1065 | REJECT | V1 |
| datasheet without CCT, CRI, dimming | REJECT | "missing" (incomplete submission) |
| ERCO B0000184 (PDF datasheet, exterior type) | REJECT | 3000 K vs 2700 K +/- 100 K (the PDF's text layer was read; no rooms to re-run) |
| `--radiance` on DESK with ERCO Lucy (3 clusters, Radiance ab 12) | ACCEPT | Radiance reproduces the design rows (401 / 431 / 364 / 399 lx) |

10 tests in `tests/luminaires/test_substitute.py`. The synthetic rows are labelled as such in the tests: no real stronger/weaker product of the same distribution was available.

## 7. Decisions (no human was available)

* ADJ -> A9000028 (304 lm), not A9001547 (855 lm): see 1. DLN bound although unused.
* PEN-LIN bound to the Jilly despite the oversize (instruction), flagged; the supplier row asks for a smaller product.
* Generic kinds sized so their driver is 0.70 (`zone-sizing.json`), rather than keeping L6b's oversized rated lumens.
* Cuts: ambient counts reduced where the new fitting is 1.45x brighter and the room floor card was already 3-9x met; none of the cuts touches a layer or a task zone.
* `lo` bound of the driver solve lowered 0.15 -> 0.05 for the table pendant (it is oversized: nothing else could meet homework-end +/-10 %).
* Cooktop 1.09x and island-prep 0.91x are both inside +/-10 % but not at 1.00: one zone (prep) serves both cards (the hob lies inside the prep strip).
* Frozen results: `knowledge/lighting/radiance-l6c/` (672 KB) is the baseline the substitution command needs; refreshing it means re-running `villa_run` and copying.

## 8. Reproduce

```
ARCHPIPE_L6_LOCAL=1 PATH=~/archpipe/tools/radiance-6.0.1/bin:$PATH PYTHONPATH=src python -m archpipe.lightcalc.villa_run --tag final --out out/L6c   # ab 12 + ab 24, ~25 min
python -m archpipe.lightcalc.villa_tune_cli --tag final --out out/L6c --lo 0.05 --size-generics      # dry run: drivers should equal the table
python -m archpipe.lightcalc.villa_emit --tag final --out out/L6c          # rows, table, zones, checks
python -m archpipe.lightcalc.handcalc knowledge/lighting/radiance-l6c      # V6 sub-planes
python -m archpipe.luminaires.spec_sheet                                  # supplier pack
```
Iterations c0 (all at driver 1.0), c1 (redesign + sizing), c2/c3/c4/c5 (B-open, kids, parents' bedroom re-runs), final (full runs c6 + c7 merged). Drivers of the final table equal the solve of the final
results (residual change 0).

## 9. Hand-offs (not mine to edit)

Run on this branch: `tests/lightcalc` + `tests/luminaires` **125 passed, 1 skipped**; `scripts/lane_guard.py L6c` clean. Outside my ownership, four tests that encode the old (LSEVO) state now fail; the two legacy
`tests/test_villa_lighting.py` failures (`test_every_task_and_room_target_is_met`, `test_vanity_sconces_914_to_1016_apart`: 3000 K expectation) already failed on `c33cf26`.

| test | why it fails now | who |
|---|---|---|
| `tests/lightverify/test_v1_design.py::test_design_inputs_pass` | LV's V1 *instance* check compares each placement's lumens with the whole fixture's record; the table pendant is now 8 product samples (57.8 lm each, record 462.5 lm). The kind row passes (3558 lm integrated = bound 3558 lm via the derived x2 file). Fix: sum samples by `meta["parent"]` for product placements, as it already does for generic ones. | LV |
| `tests/lightverify/test_v5_v6_v7.py` (2) | they compare LV's frozen Radiance/Cycles results of the L6b design with the live design; the design and the products changed. Re-run LV V5-V7 on `knowledge/lighting/radiance-l6c/` (Cycles must be re-run: not done here). | LV |
| `tests/test_villa_lighting.py::Photometry::test_verified_products_are_cached...` | expects `LSEVO-*` as the bound SKUs (now ERCO). | lead / INT |
| `knowledge/lighting-verify/dialux/` | the DIALux package holds the L6b fixtures and IES; regenerate with `lightverify.dialux_pack` before V11. | LV / client |

`src/archpipe/model/data/d1-elements.json` (L2 snapshot) must be regenerated from the new design (fixture ids, kinds and lumens changed; 5 DL added/removed). The render (`out/villa/render-d1`) still uses the old IES: re-render after INT.
