# L6b villa lighting design

Branch `lane/L6b`. Code: `src/archpipe/lightcalc/villa*.py`, design `src/archpipe/concept/villa_lighting.py`, kinds
`src/archpipe/fixture_record.py`. Data: `knowledge/lighting/` (`zones-d1.json`, `zone-drivers.json`, `villa-before-rows.json`,
`villa-after-rows.json`, `villa-table.md`, `truth/`, frozen IES and `products-frozen.json`). Checks: `out/checks/L6.json`
(copy `knowledge/lighting/checks/L6.json`). Tests: `tests/lightcalc/test_villa.py`, `test_truth_probe.py`.
All calculation ran on `ai-workstation` (Radiance 6.0.1, Python venv `laneP-venv`).

## 1. The truth question: 963 lx (engine) vs 405 lx (Cycles probe) at the D1 dining-table centre

**Answer: the engine is right and the recorded probe is the vase-obstructed reading. They measured different things at the same
coordinates.**

Method: a minimal Cycles scene (`knowledge/lighting/truth/truth_probe_blender.py`, Blender 4.5.14 on the workstation) that reuses the
production light constructor (`villa_scene.add_light`: IES node, `IES_POINT_POWER`, aim) and the production sensor method
(0.5-reflectance 4 cm plane 1 mm over the point, 20 mm ortho camera, 0 bounces, radiance x pi / 0.5), MF 0.8, with the lights
and meshes of the job that produced the recorded file (`834db2128a44f9b196d3e5bd`, Sep 28).

| variant | centre (16.95, -25.9) | table end (16.35, -25.9) |
|---|---|---|
| A. the two crossed adjustable spots, open table | **952** | 218 |
| B. spots + the emissive pendant | 1295 | 468 |
| C. spots + pendant + `dining-vase` on the sensor | **403** | 460 |
| D. spots + vase | 0 | 218 |
| E. pendant only | 343 | 251 |
| F. pendant + vase, no spots | 403 | 243 |
| G. vase only | 0 | 0 |
| recorded `lighting-measurements.json` | **405** | 467 |

* Engine side: analytic direct 939 lx at the emitter datum z = -0.30 and 952 lx at the rendered z = -0.33 (the 1.3 % is the 30 mm
  datum). Variant A (Cycles) equals it to 1.5 % at both points. The engine's 963 lx is **total** light (Radiance ab 6, closed walls: 939 direct + 24
  indirect, `L6-dining-result.json`), not direct. This rules out aiming, IES azimuth, lamp scaling, MF, units and the B = -3000 / -1800 datum
  (both sides use -3.0).
* Probe side: variant C reproduces the recorded file to 0.7 % and 1.4 %. The Sep 28 run therefore read spots + the emissive pendant with
  the vase (0.20 m wide, 0.40 m tall, open mouth) standing on the centre sensor: D shows the vase removes all spot light, and C and F read the
  same 403 lx, so what reaches the sensor is pendant light (the camera is probably metering the vase interior; unconfirmed mechanism).
* "The probe was moved off the vase" is **false for that file**: its points carry no `measurement_position` and the resolver
  (`task_probe.resolve_surface_probes`) is newer. The recorded numbers are an obstructed reading, not a relocated one.
* Not in this lane, **finding for the render lane**: `out/villa/render-d1/lighting-measurements.json` is stale (Sep 28; `scene.json` is Oct 7, and
  its fixtures and probe points differ from it); in the Oct 7 scene the table top is at z = -2.248, so a probe at plane -2.25 + 1 mm sits below the surface
  and the measurement needs a re-run with the task-probe binding. Do not quote its dining numbers.
* In this lane (fixed): `dining.py` "built" omitted the emissive pendant that the render emits (343 lx at the centre); a `render` variant (spots +
  Lambertian pendant) was added. The model's pendant (generic cos^n 90 deg) gave about 464 lx at the centre, 35 % more than the rendered Lambertian
  strip; the villa harness models the pendant as Lambertian.
* Tests: `tests/lightcalc/test_truth_probe.py` (frozen Cycles variants vs the analytic engine and the recorded file).

## 2. Result: before -> after (villa, 13 Radiance clusters, owning scene, MF 0.8)

Final run (after the verification fixes, section 9): `villa_run --tag after`, **ab 12 is the result and ab 24 the convergence run** (largest change on any
plane 1.65 %, section 9.2). Reflectances 0.80 / 0.85 / 0.33 are ASSUMED (see Limits). "Before" is the committed design with every zone at 100 % (frozen
`knowledge/lighting/villa-before-rows.json`, an ab 6 run on the old planes: compare the ratios, not the third digit). All 20 average-gauged task planes are within
+/-10 % of their card (17 at 0.99 to 1.01; kids' desks 1.07 and 0.91, which share one zone); every minimum-gauged room floor meets its card.
**V12: every zone driver x scene level is <= 0.772 of maximum output (limit 0.80); no exception.** Checked by `villa_checks.check_v12` (published in
`out/checks/L6.json`), by `tests/lightcalc/test_villa.py::test_v12_driver_cap`, and by LV's own V12 layer run on these drivers (20 of 20 pass).

### 2.1 Task cards: before -> after with the driver that owns them

| room | plane | scene | target lx | before Em | after Em | Emin | U0 | sensors | driver zone(s) at the owning scene (driver x scene level) | V12 |
|---|---|---|---|---|---|---|---|---|---|---|
| bar-alcove | daybed | Reading | 200 | 812 | 200 | 30 | 0.15 | 20 | bar-alcove-daybed-reading 0.34 | pass |
| cinema | cinema-desk | Day | 400 | 874 | 399 | 305 | 0.77 | 8 | cinema-task 0.67 | pass |
| dining | dining-table | Dinner | 100 | 858 | 99 | 61 | 0.62 | 18 | dining-table-pendant 0.25 (x0.405) | pass |
| dining | homework-end | Day | 200 | 641 | 200 | 137 | 0.69 | 20 | dining-table-pendant 0.61, kitchen-island-pendants 0.77 | pass |
| dirty-kitchen | dirty-kitchen-run | Day | 500 | 958 | 498 | 371 | 0.74 | 10 | dirty-kitchen-run-task 0.74 | pass |
| family-bath | fb-basin | Day | 300 | 1491 | 300 | 217 | 0.72 | 66 | family-bath-basin-task 0.31, family-bath-task 0.44 | pass |
| guest-wc | gwc-basin | Day | 300 | 1324 | 300 | 238 | 0.79 | 70 | guest-wc-basin-task 0.49 | pass |
| kids-a | ka-desk-1 | Day | 400 | 513 | 430 | 125 | 0.29 | 8 | kids-a-task 0.71 | pass |
| kids-a | ka-desk-2 | Day | 400 | 517 | 363 | 117 | 0.32 | 12 | kids-a-task 0.71 | pass |
| kids-b | kb-desk | Day | 400 | 466 | 400 | 89 | 0.22 | 8 | kids-b-task 0.54 | pass |
| kitchen | cooktop | Cook | 300 | 1284 | 301 | 233 | 0.77 | 25 | kitchen-island-cook 0.38, kitchen-island-pendants 0.23 (x0.300), kitchen-island-prep 0.73 | pass |
| kitchen | island-prep | Cook | 500 | 1128 | 497 | 321 | 0.65 | 12 | kitchen-island-cook 0.38, kitchen-island-prep 0.73 | pass |
| kitchen | island-seating | Day | 200 | 1049 | 199 | 162 | 0.81 | 14 | kitchen-island-pendants 0.77 | pass |
| kitchen | sink | Cook | 300 | 1229 | 299 | 184 | 0.62 | 9 | kitchen-run-task 0.60 | pass |
| lounge | armchair | Reading | 200 | 893 | 201 | 114 | 0.57 | 25 | lounge-armchair-reading 0.37 | pass |
| parents-bed | pillow-1 | Reading | 200 | 902 | 201 | 71 | 0.35 | 20 | parents-bed-bed-reading 0.56 | pass |
| parents-bed | pillow-2 | Reading | 200 | 899 | 200 | 74 | 0.37 | 20 | parents-bed-bed-reading 0.56 | pass |
| parents-ensuite | pe-basin | Day | 300 | 658 | 300 | 240 | 0.80 | 70 | parents-ensuite-basin-task 0.46 | pass |
| study-game | study-adult-desk | Day | 400 | 800 | 400 | 255 | 0.64 | 8 | study-game-desk-adult 0.49 | pass |
| study-game | study-desk | Day | 400 | 979 | 399 | 247 | 0.62 | 12 | study-game-desk-task 0.67 | pass |

Driver = fraction of maximum output, a fixed commissioning setting per control zone (`knowledge/lighting/zone-drivers.json`); several zones listed
means the plane also receives at least 10 % of its card from them. "sensors" = Radiance sensor points left after the objects and host holes are removed (9.3).
The dining table is met in Dinner (pendant driver 0.61 x scene level 0.405 = 25 % of its maximum, 99 lx).

### 2.2 All planes (task and room floor, `villa-table.md`)

| room | plane | card lx | scene | before Em (x target) | before U0 | after Em | after Emin | after U0 | x target | LA1 | LA2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bar-alcove | daybed | 200 | Reading | 812 (4.1x) | 0.59 | 200 | 30 | 0.15 | 1.00 | pass | pass |
| cinema | cinema-desk | 400 | Day | 874 (2.2x) | 0.69 | 399 | 305 | 0.77 | 1.00 | pass | pass |
| cinema | room-cinema | 20 (min) | Day | 172 (8.6x) | 0.14 | 228 | 41 | 0.18 | 11.41 | pass | n/a |
| corridor | room-corridor | 30 (min) | Day | 176 (5.9x) | 0.83 | 246 | 205 | 0.83 | 8.20 | pass | n/a |
| dining | dining-table | 100 | Dinner | 858 (8.6x) | 0.43 | 99 | 61 | 0.62 | 0.99 | pass | pass |
| dining | homework-end | 200 | Day | 641 (3.2x) | 0.48 | 200 | 137 | 0.69 | 1.00 | pass | pass |
| dirty-kitchen | dirty-kitchen-run | 500 | Day | 958 (1.9x) | 0.61 | 498 | 371 | 0.74 | 1.00 | pass | pass |
| dirty-kitchen | room-dirty-kitchen | 200 (min) | Day | 634 (3.2x) | 0.16 | 410 | 76 | 0.18 | 2.05 | pass | n/a |
| family | room-family | 100 (min) | Day | 499 (5.0x) | 0.53 | 240 | 71 | 0.30 | 2.40 | pass | n/a |
| family-bath | fb-basin | 300 | Day | 1491 (5.0x) | 0.88 | 300 | 217 | 0.72 | 1.00 | pass | pass |
| family-bath | room-family-bath | 50 (min) | Day | 594 (11.9x) | 0.42 | 305 | 192 | 0.63 | 6.10 | pass | n/a |
| guest-wc | gwc-basin | 300 | Day | 1324 (4.4x) | 0.80 | 300 | 238 | 0.79 | 1.00 | pass | pass |
| guest-wc | room-guest-wc | 50 (min) | Day | 325 (6.5x) | 0.25 | 197 | 61 | 0.31 | 3.93 | pass | n/a |
| hall-b | room-hall-b | 30 (min) | Day | 510 (17.0x) | 0.73 | 269 | 172 | 0.64 | 8.98 | pass | n/a |
| kids-a | ka-desk-1 | 400 | Day | 513 (1.3x) | 0.27 | 430 | 125 | 0.29 | 1.07 | pass | pass |
| kids-a | ka-desk-2 | 400 | Day | 517 (1.3x) | 0.29 | 363 | 117 | 0.32 | 0.91 | pass | pass |
| kids-a | room-kids-a | 50 (min) | Day | 198 (4.0x) | 0.17 | 182 | 33 | 0.18 | 3.64 | pass | n/a |
| kids-b | kb-desk | 400 | Day | 466 (1.2x) | 0.24 | 400 | 89 | 0.22 | 1.00 | pass | pass |
| kids-b | room-kids-b | 50 (min) | Day | 165 (3.3x) | 0.15 | 157 | 26 | 0.16 | 3.15 | pass | n/a |
| kitchen | cooktop | 300 | Cook | 1284 (4.3x) | 0.87 | 301 | 233 | 0.77 | 1.00 | pass | pass |
| kitchen | island-prep | 500 | Cook | 1128 (2.3x) | 0.70 | 497 | 321 | 0.65 | 0.99 | pass | pass |
| kitchen | island-seating | 200 | Day | 1049 (5.2x) | 0.72 | 199 | 162 | 0.81 | 0.99 | pass | pass |
| kitchen | room-kitchen | 50 (min) | Day | 928 (18.6x) | 0.17 | 185 | 84 | 0.45 | 3.70 | pass | n/a |
| kitchen | sink | 300 | Cook | 1229 (4.1x) | 0.69 | 299 | 184 | 0.62 | 1.00 | pass | pass |
| kitchen-island | room-kitchen-island | 50 (min) | Day | 442 (8.8x) | 0.68 | 309 | 231 | 0.75 | 6.18 | pass | n/a |
| living | room-living | 30 (min) | Day | 337 (11.2x) | 0.45 | 181 | 53 | 0.29 | 6.04 | pass | n/a |
| lounge | armchair | 200 | Reading | 893 (4.5x) | 0.59 | 201 | 114 | 0.57 | 1.00 | pass | pass |
| lounge | room-lounge | 100 (min) | Day | 400 (4.0x) | 0.56 | 171 | 52 | 0.30 | 1.71 | pass | n/a |
| pantry | room-pantry | 50 (min) | Day | 331 (6.6x) | 0.88 | 358 | 353 | 0.98 | 7.17 | pass | n/a |
| parents-bed | pillow-1 | 200 | Reading | 902 (4.5x) | 0.76 | 201 | 71 | 0.35 | 1.01 | pass | pass |
| parents-bed | pillow-2 | 200 | Reading | 899 (4.5x) | 0.76 | 200 | 74 | 0.37 | 1.00 | pass | pass |
| parents-bed | room-parents-bed | 50 (min) | Day | 208 (4.2x) | 0.05 | 246 | 87 | 0.35 | 4.92 | pass | n/a |
| parents-dressing | room-parents-dressing | 100 (min) | Day | 355 (3.5x) | 0.60 | 378 | 241 | 0.64 | 3.78 | pass | n/a |
| parents-ensuite | pe-basin | 300 | Day | 658 (2.2x) | 0.82 | 300 | 240 | 0.80 | 1.00 | pass | pass |
| parents-ensuite | room-parents-ensuite | 50 (min) | Day | 131 (2.6x) | 0.41 | 86 | 34 | 0.39 | 1.73 | pass | n/a |
| store-ramp | room-store-ramp | 50 (min) | Day | 119 (2.4x) | 0.50 | 180 | 112 | 0.62 | 3.59 | pass | n/a |
| study-game | room-study-game | 6 (min) | Day | 523 (87.2x) | 0.20 | 274 | 80 | 0.29 | 45.71 | pass | n/a |
| study-game | study-adult-desk | 400 | Day | 800 (2.0x) | 0.33 | 400 | 255 | 0.64 | 1.00 | pass | pass |
| study-game | study-desk | 400 | Day | 979 (2.4x) | 0.52 | 399 | 247 | 0.62 | 1.00 | pass | pass |

LA1 FAIL rows in `out/checks/L6.json` are the two *reference* dining cases (`D1-dining`, `D1-dining-built`) at full output, which show the
committed design's over-lighting (709 and 390 lx vs 100); they are not the villa after-state. The one villa failure is LA12 (exterior ULR, section 5).

## 3. Changes made to the design (and why)

* Downlights: `DL` (732 lm, flood) instead of `DLN` (1343 lm) over the kitchen run, the dirty-kitchen run, the study desks and the shower; the
  dining and island prep light was cut (island prep: three DL on the opal globes' axes plus one at the far end, the hob's own DL on a separate
  zone `island-cook` because the 300 lx induction zone lies inside the 500 lx prep strip); parents' reading spots cut (the swing arms light the pillow).
* V12 (this session): family bath counter downlight returned (the two sconces alone needed 1.20); adult desk 1 -> 2 DL (1.12); dirty-kitchen run
  4 -> 5 DL (0.85); kids' B desk lamp 450 -> 600 lm (0.85); hob/prep split (the single prep zone gave 351 lx at the hob and 371 lx on the strip).
* Control zones: room x function (`zone=` suffix) with task layer solved by `villa_tune`; 69 zones in `zones-d1.json`.
* Drivers: solved by least squares on the per-zone Radiance results (linear), bounds 0.15 to 3.0, then held <= 0.80 by design (V12).
* LA9 set-out snapping; route lights (night/emergency layer on stair and basement route); kinds and CCT policy per layer (2700 K interior, 2200 K night).
* Dinner scene level for the table pendant solved to 0.405 (others contribute 28 lx).

## 4. Scenes (`SCENES` in `concept/villa_lighting.py`)

| cluster | scene | zone levels (key = layer or zone-id suffix; missing = off) |
|---|---|---|
| B-open | Day | *ambient 1.00, island-pendants 1.00, table-pendant 1.00, *accent 0.50 |
| B-open | Cook | *ambient 1.00, island-pendants 0.30, island-prep 1.00, island-cook 1.00, run-task 1.00 |
| B-open | Dinner | table-pendant 0.41, island-pendants 0.30, *decorative 0.30, living-ambient 0.20, sideboard-accent 1.00 |
| B-open | Evening | *ambient 0.40, *decorative 0.70, *accent 0.70, table-pendant 0.30, island-pendants 0.40 |
| B-open | Reading | armchair-reading 1.00, daybed-reading 1.00, *ambient 0.15, *decorative 0.20 |
| B-open | Film | lounge-decorative 0.15, *night 0.10 |
| B-open | Night | *night 0.10 |
| B-cinema | Day | *ambient 1.00, *task 1.00, *accent 1.00, *decorative 1.00 |
| B-cinema | Evening | *ambient 0.40, *accent 0.70, *decorative 0.70 |
| B-cinema | Film | cinema-accent 0.15, *night 0.30 |
| B-cinema | Night | *night 0.10 |
| GF-circulation | Day | *ambient 1.00, *task 1.00, *accent 1.00, *decorative 1.00 |
| GF-circulation | Evening | *ambient 0.40, *accent 0.70, *decorative 0.70 |
| GF-circulation | Night | *night 0.10 |
| GF-kids-a | Day | *ambient 1.00, *task 1.00, *accent 1.00, *decorative 1.00 |
| GF-kids-a | Evening | *ambient 0.40, *accent 0.70, *decorative 0.70 |
| GF-kids-a | Night | *night 0.10 |
| GF-kids-b | Day | *ambient 1.00, *task 1.00, *accent 1.00, *decorative 1.00 |
| GF-kids-b | Evening | *ambient 0.40, *accent 0.70, *decorative 0.70 |
| GF-kids-b | Night | *night 0.10 |
| GF-parents-bed | Day | *ambient 1.00, *task 1.00, *accent 1.00, *decorative 1.00 |
| GF-parents-bed | Evening | *ambient 0.40, *accent 0.70, *decorative 0.70 |
| GF-parents-bed | Night | *night 0.10 |
| GF-parents-bed | Reading | bed-reading 1.00, *decorative 0.30 |
| GF-parents-dressing | Day | *ambient 1.00, *task 1.00, *accent 1.00, *decorative 1.00 |
| GF-parents-dressing | Night | *night 0.10 |
| GF-parents-ensuite | Day | *ambient 1.00, *task 1.00, *accent 0.40, *decorative 1.00 |
| GF-parents-ensuite | Night | *night 0.10 |
| GF-family-bath | Day | *ambient 1.00, *task 1.00, *accent 1.00, *decorative 1.00 |
| GF-family-bath | Night | *night 0.10 |
| B-guest-wc | Day | *ambient 1.00, *task 1.00, *accent 1.00, *decorative 1.00 |
| B-guest-wc | Night | *night 0.10 |
| B-dirty-kitchen | Day | *ambient 1.00, *task 1.00, *accent 1.00, *decorative 1.00 |
| B-pantry | Day | *ambient 1.00, *task 1.00, *accent 1.00, *decorative 1.00 |
| B-store | Day | *ambient 1.00, *task 1.00, *accent 1.00, *decorative 1.00 |

## 5. Exterior proposal (not built; LA12 currently FAILS: the four garden uplights give ULR 1.0 vs <= 0.15)

1. Path and step lights: down-only, fully shielded (ULR 0), low mounting, warm 2700 K or lower, none aimed above horizontal.
2. Terrace: shielded downlights under the soffit/pergola, ULR 0, instead of floods.
3. The tree/garden uplights: shield them (louvre/snoot so no light leaves above the horizon) or replace with down-lit-from-above fixtures.
4. Curfew: dim exterior layers to <= 50 % and hold 2700 K after the curfew hour (policy; the hour is the client's decision).
5. An exterior Radiance grid at the boundary is needed to compute boundary Ev and spill; not run in this lane.

## 6. Limits

* Radiance has no furniture or door shadows; the open basement is one closed volume; reflectances 0.80 (ceiling) / 0.85 / 0.33 are ASSUMED.
* Dimming is modelled linear in output; drivers are commissioning settings that must be confirmed on site (V12 leaves >= 25 % headroom).
* Several zones run at a driver below about 0.40 (daybed 0.34, family-bath basin DL 0.31, island hob 0.38, armchair 0.37): the library has no lower-output
  recessed product, so they are dimmed rather than fitted smaller.
* Task-plane uniformity (U0) is reported, not gated (kids' desks 0.24 to 0.30, daybed 0.15, pillows 0.30): lamps are local sources.
* UGR is not evaluated (LA4 not_evaluated); unsourced policy values are `policy`/`unverified`, not code compliance.
* Results are Radiance estimates at ab 12 (ab 24 changes every plane by < 1.7 %), not measurements.

## 7. Finding for the render lane

`out/villa/render-d1/lighting-measurements.json` is **stale** (Sep 28; `scene.json` is Oct 7 and its fixtures and probe points differ). Its dining numbers
(405 / 467 lx) are the vase-obstructed probe (section 1) and the Oct 7 table top (z = -2.248) is above the 1 mm probe plane. Do not quote it; re-run with
the task-probe binding. The engine's after-state is in `knowledge/lighting/villa-after-rows.json`.

## 8. Reproduce

`ARCHPIPE_L6_LOCAL=1 PATH=~/archpipe/tools/radiance-6.0.1/bin:$PATH villa_run --tag after --out out/L6b` (about 17 min on the 32-core workstation; `--fast` = ab 12 only, 4 min) then `villa_emit --tag after`; solve drivers with `villa_tune_cli --tag <t> --write`
from a run made with the table applied (results embed the applied drivers). Iterations: iter1..iter3 as in git history; iter4 (V12 design changes, all 13
clusters) and iter5 (B-open, hob/prep split) are the last solves. Outputs: `out/L6b/<tag>/` (ignored by git).

## 9. Verification fixes (lane LV findings, 2026-11-21)

LV (independent verification) found six defects in the first version of this lane. Each is fixed with a regression test that fails on the old code, and the
after-state was re-run. Detail of why each was missed: `docs/lessons/L6b.md`.

### 9.1 The six fixes, before -> after

| # | defect | before | after | guard |
|---|---|---|---|---|
| 1 | cluster `GF-parents-bed` was the entry, not the bedroom | polygon 0.68 m2 (1.0 x 0.68 m); every bedroom emitter and pillow plane outside it; room plane 143 lx; LV V6 -89 % | polygon 11.706 m2 = model rooms 11.656 m2 + 0.05 m2 gap bridge (0.4 %); room plane 246 lx; LV V6 **+5 %**; the closed volume is now the real bedroom | `union_rects` bridges <= 60 mm and raises on several outlines; `test_union_bridges_a_thin_wall_gap_and_refuses_a_wide_one`, `test_every_cluster_room_area_equals_the_design_model_room_area` (13 clusters vs `archpipe.model.load("D1")`, 1 %). All other 12 clusters already matched exactly. |
| 2 | ab 6 under-converged (ab 6 -> 12 moved ensuite -6.4 %, basin -4.7 %, 10 of 39 planes > 3 %) | results at ab 6 | results at **ab 12**; ab 12 -> 24 changes every plane by <= 1.65 % (table 9.2) | `villa.AB = 12`; every full run computes 2 x AB; the table below is regenerated from it |
| 3 | task planes off their surface; sensors in objects | sink plane 38 mm over the worktop slab top; basin planes 180 mm over the bowl bottom (60 mm over the rim); sensors inside the shower/bath (10 of 42 in two room planes), hanging rails (6 of 35), pantry shelving (4 of 14), the island bowl, cinema desk lamp arms, kitchen hob | every hosted plane at its host (<= 4 mm; worst the hob 4 mm; desks 2 mm; island/worktop 0 mm); the bowl and the sink cutout are dropped as holes; **0 of every plane's sensor points inside or within 50 mm under any object** on the RV1 scene geometry (LV's V3 test, 39 planes) | `knowledge/lighting/sensor-obstructions.json` (per-plane cells from the built scene, regenerated by `villa_sensors_gen`), `blocked_rects` raises when a plane moved without regeneration, `test_planes_sit_on_their_hosts_and_keep_sensors_out_of_objects`, `test_stale_obstruction_record_fails_loudly`, `test_sensor_grid_drops_points_inside_an_object_footprint` |
| 4 | engine silently capped a bound-product dimmer at 1.0 | `min(1.0, d)` in `apply_drivers`; LV: family-bath basin 121 % | raises `ValueError` above rated output; all zone drivers <= 0.772; no zone needed a design change after fixes 1 to 3 (the family-bath split moved from 0.15 / 0.80 to 0.31 / 0.44) | `test_driver_above_rated_output_of_a_bound_product_raises` (negative case included) |
| 5 | parents' dressing room -42 % against the lumen method | engine 356 lx vs 615 lx | **explained, engine right**: the lumen method spreads inter-reflected flux over all surfaces by area, but this room is 2.8 x 2.1 x 2.7 m (room index 0.43) with 79 % of the light first reaching the walls, so the floor receives far less. An independent patch radiosity (`radiosity.floor_mean_lux`, 8 x 8 patches per face, no Radiance code) gives **377 lx**, Radiance **378 lx**; the same check agrees on guest WC (197 vs 197), pantry (349 vs 358), family bath (320 vs 305) | `test_radiosity_agrees_with_radiance_on_box_rooms` (4 rooms, 6 %), negative `test_radiosity_negative_a_wrong_reflectance_is_caught`. LV's V6 still reports this room as a miss (-39 %); it stays a flagged, explained miss. |
| 6 | published data | stale | `zones-d1.json`, `villa-after-rows.json`, `villa-table.md`, `out/checks/L6.json` (and `knowledge/lighting/checks/L6.json`), `zone-drivers.json` regenerated; 177 check records | `villa_emit --tag after` |

### 9.2 Convergence (ab 12 result vs ab 24, owning scene, maintained lux)

All 39 planes: largest change 1.65 % (pillow-1, 20 sensors), next 0.71 % (pillow-2) and 0.33 % (parents' bedroom floor); all others below 0.2 %. A further doubling would
change no plane by 3 % (for comparison LV's 6 -> 12 moved planes by up to 6 %).

| plane | ab 12 Em | ab 24 Em | change |
|---|---|---|---|
| island-prep | 497.2 | 497.2 | -0.00 % |
| island-seating | 198.9 | 199.0 | -0.04 % |
| cooktop | 301.2 | 301.3 | -0.01 % |
| sink | 299.5 | 299.5 | +0.00 % |
| dining-table | 99.3 | 99.4 | -0.12 % |
| homework-end | 199.7 | 199.7 | -0.02 % |
| dirty-kitchen-run | 498.2 | 498.3 | -0.03 % |
| study-desk | 398.6 | 398.7 | -0.02 % |
| study-adult-desk | 400.4 | 400.5 | -0.04 % |
| ka-desk-1 | 429.6 | 429.7 | -0.03 % |
| ka-desk-2 | 362.7 | 362.7 | -0.01 % |
| kb-desk | 399.6 | 399.7 | -0.02 % |
| cinema-desk | 398.7 | 398.8 | -0.03 % |
| pillow-1 | 201.4 | 198.2 | +1.65 % |
| pillow-2 | 199.8 | 201.2 | -0.71 % |
| fb-basin | 300.5 | 300.7 | -0.09 % |
| pe-basin | 300.3 | 300.4 | -0.04 % |
| gwc-basin | 299.9 | 300.1 | -0.05 % |
| armchair | 200.6 | 200.2 | +0.16 % |
| daybed | 200.2 | 200.2 | +0.01 % |
| room-lounge | 171.1 | 171.1 | -0.02 % |
| room-family | 240.2 | 240.2 | -0.03 % |
| room-living | 181.1 | 181.2 | -0.04 % |
| room-kitchen | 184.9 | 184.9 | -0.02 % |
| room-kitchen-island | 308.9 | 309.0 | -0.01 % |
| room-hall-b | 269.3 | 269.4 | -0.03 % |
| room-corridor | 246.0 | 246.3 | -0.10 % |
| room-study-game | 274.3 | 274.4 | -0.04 % |
| room-kids-a | 181.8 | 181.9 | -0.04 % |
| room-kids-b | 157.3 | 157.4 | -0.04 % |
| room-parents-bed | 246.2 | 245.4 | +0.33 % |
| room-parents-dressing | 378.4 | 378.7 | -0.08 % |
| room-cinema | 228.2 | 228.3 | -0.03 % |
| room-dirty-kitchen | 409.9 | 410.1 | -0.04 % |
| room-pantry | 358.3 | 358.6 | -0.08 % |
| room-store-ramp | 179.7 | 179.8 | -0.06 % |
| room-family-bath | 305.1 | 305.3 | -0.08 % |
| room-parents-ensuite | 86.3 | 86.4 | -0.13 % |
| room-guest-wc | 196.7 | 196.8 | -0.07 % |

### 9.3 What the sensors are now (fix 3)

* A task plane is the area of its host top, at the height the built scene has it: worktop slab top 0.902 m, island 0.922 m, hob 0.926 m, washbasin **rim** 0.850 m
  (the bowl is a recess below it), desks and dining table 0.750 m (the fitted desk models are scaled to 0.75: see 9.5). Planes over a hole in the host (basin
  bowl, sink cutout) keep only their rim/worktop points; basin planes use a 30 mm pitch because the rim is about 9 cm wide (66 to 70 points each).
* The sink plane is now the whole sink run's worktop (2.0 x 0.5 m, 9 points after the cutout and the appliances are removed); it was a 0.9 x 0.5 m patch partly over
  the dishwasher and the cutout. Its card is therefore met on the worktop around the sink, not in the bowl.
* The reading planes (pillows, armchair, daybed) are positions in the air at book height; they are not hosted and have no height rule. They pass the occlusion test
  (0 of 85 points blocked).
* The test geometry is the last buildable scene (`/tmp/RV1-scene/scene.json`, built before this lane's redesign; furniture is unchanged). A fresh build of the merged
  design fails at `mounting_resume` (lamp-SCONCE-family-bath-04 schedule drift); that is an L2/L6b integration item for the lead, not changed here. Re-generate with
  `python -m archpipe.lightcalc.villa_sensors_gen <scene.json>` after any scene change (needs `archpipe.lightverify` from lane LV).

### 9.4 V12 and the other LV layers re-run here (scratch copies of LV's checkers, nothing of LV committed)

| layer | result on this branch |
|---|---|
| V12 | 20 of 20 pass; worst zone x level 0.772 (island pendants); LV had 5 exceptions |
| V3 (sensors) | 39 of 39 planes: 0 blocked points, hosted planes 0 to 4 mm from their host (with the `scale_xyz` correction of 9.5) |
| V6 (hand calc) | 12 of 13 within 25 %; parents' bedroom -89 % -> +5 %; dressing room -39 % (explained, fix 5) |

### 9.5 Finding for LV: its scene loader ignores `scale_xyz`

`lightverify/scene_geom.py:load_scene` scales imported models by `spec["scale"]` (1.0), but the renderer applies `spec["scale_xyz"]` to every fitted model (desks,
chairs, bed, vanity). With it ignored, desks come out 1.1 x 0.45 x 0.722 m (really 1.8 x 0.7 x 0.75 m) and the desk chairs 2 m long. So LV's "desk planes 28 mm too high" is an
artefact (real desk tops are 2 mm under the 0.75 m planes: they were right) and the chair hits on the desk planes are the oversized chairs. With `scale_xyz`
applied the desk and chair findings vanish; the sink, basin, rail, shower and bath findings were real and are fixed. I left the desk planes at 0.75 m and did
not lower them to 0.722 m. LV should re-run V3 with the loader fixed; I did not commit any LV file.

### 9.6 Files changed (verification round, from `git diff --stat`)

`src/archpipe/lightcalc/villa.py` (bridge, AB, plane exclude), `villa_planes.py` (hosted heights, sink run, basin rim, exclusion cells), `roomcalc.py` (sensor exclusion),
`villa_tune.py` / `villa_tune_cli.py` (absolute drivers, balanced split), `villa_run.py`, new `villa_sensors_gen.py`, `radiosity.py`;
`src/archpipe/concept/villa_lighting.py` (apply_drivers raises); `knowledge/lighting/` (`sensor-obstructions.json`, `zone-drivers.json`, `zones-d1.json`,
`villa-after-rows.json`, `villa-table.md`, `checks/L6.json`); `tests/lightcalc/test_villa.py`; `docs/lanes/L6b-villa-lighting.md`; `docs/lessons/L6b.md`.
