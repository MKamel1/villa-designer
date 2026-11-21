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

## 2. Result: before -> after (villa, 13 Radiance clusters, owning scene, MF 1.0)

Final run: `villa_run --tag after` (ab 6 and ab 12 both computed; the table reports ab 12 as the result, ab 6 as the convergence check).
Reflectances 0.80 / 0.85 / 0.33 are ASSUMED (see Limits). "Before" is the committed design with every zone at 100 % (frozen
`knowledge/lighting/villa-before-rows.json`). All 20 average-gauged task planes are within +/-10 % of their card (19 at 0.99 to 1.01, the adult desk
at 1.08); every minimum-gauged room floor meets its card. Convergence ab 12 vs ab 6: task planes at most 3.9 %, all planes at most 5.6 %
(parents' ensuite floor). **V12: every tuned zone driver is <= 0.80 of maximum output; no exception.** Two zones sit on the cap
(`FAMILY-BATH-TASK` 0.80, `KITCHEN-ISLAND-PENDANTS` 0.796). Checked by `villa_checks.check_v12` (published in `out/checks/L6.json`) and
`tests/lightcalc/test_villa.py::test_v12_driver_cap`.

### 2.1 Task cards: before -> after with the driver that owns them

| room | plane | scene | target lx | before Em | after Em | Emin | U0 | driver zone(s) at the owning scene | V12 |
|---|---|---|---|---|---|---|---|---|---|
| bar-alcove | daybed | Reading | 200 | 812 | 200 | 29 | 0.15 | bar-alcove-daybed-reading 0.34, kitchen-island-pendants 0.80, lounge-armchair-reading 0.38 | pass |
| cinema | cinema-desk | Day | 400 | 874 | 400 | 290 | 0.73 | cinema-task 0.71 | pass |
| dining | dining-table | Dinner | 100 | 858 | 100 | 61 | 0.61 | DINING-TABLE-PENDANT 0.62 x scene level 0.405 | pass |
| dining | homework-end | Day | 200 | 641 | 200 | 136 | 0.68 | dining-table-pendant 0.62, kitchen-island-pendants 0.80 | pass |
| dirty-kitchen | dirty-kitchen-run | Day | 500 | 958 | 500 | 365 | 0.73 | dirty-kitchen-run-task 0.74 | pass |
| family-bath | fb-basin | Day | 300 | 1491 | 300 | 287 | 0.96 | family-bath-basin-task 0.15, family-bath-task 0.80 | pass |
| guest-wc | gwc-basin | Day | 300 | 1324 | 300 | 260 | 0.87 | guest-wc-basin-task 0.42 | pass |
| kids-a | ka-desk-1 | Day | 400 | 513 | 398 | 113 | 0.28 | kids-a-task 0.77 | pass |
| kids-a | ka-desk-2 | Day | 400 | 517 | 401 | 120 | 0.30 | kids-a-task 0.77 | pass |
| kids-b | kb-desk | Day | 400 | 466 | 400 | 97 | 0.24 | kids-b-task 0.64 | pass |
| kitchen | cooktop | Cook | 300 | 1284 | 300 | 232 | 0.77 | kitchen-island-cook 0.37, kitchen-island-pendants 0.80, kitchen-island-prep 0.78, kitchen-run-task 0.51 | pass |
| kitchen | island-prep | Cook | 500 | 1128 | 500 | 317 | 0.63 | kitchen-island-cook 0.37, kitchen-island-pendants 0.80, kitchen-island-prep 0.78, kitchen-run-task 0.51 | pass |
| kitchen | island-seating | Day | 200 | 1049 | 200 | 162 | 0.81 | dining-table-pendant 0.62, kitchen-island-pendants 0.80 | pass |
| kitchen | sink | Cook | 300 | 1229 | 300 | 224 | 0.75 | kitchen-island-cook 0.37, kitchen-island-pendants 0.80, kitchen-island-prep 0.78, kitchen-run-task 0.51 | pass |
| lounge | armchair | Reading | 200 | 893 | 200 | 113 | 0.57 | bar-alcove-daybed-reading 0.34, kitchen-island-pendants 0.80, lounge-armchair-reading 0.38 | pass |
| parents-bed | pillow-1 | Reading | 200 | 902 | 200 | 60 | 0.30 | parents-bed-bed-reading 0.64 | pass |
| parents-bed | pillow-2 | Reading | 200 | 899 | 200 | 60 | 0.30 | parents-bed-bed-reading 0.64 | pass |
| parents-ensuite | pe-basin | Day | 300 | 658 | 300 | 256 | 0.85 | parents-ensuite-basin-task 0.37 | pass |
| study-game | study-adult-desk | Day | 400 | 800 | 432 | 222 | 0.51 | study-game-desk-adult 0.73, study-game-desk-task 0.72 | pass |
| study-game | study-desk | Day | 400 | 979 | 404 | 246 | 0.61 | study-game-desk-adult 0.73, study-game-desk-task 0.72 | pass |

Driver = fraction of maximum output, a fixed commissioning setting per control zone (`knowledge/lighting/zone-drivers.json`); several zones listed
means the plane also receives light from them (the island pendants are lit in Day/Cook/Reading at their own driver).
The dining table is met in Dinner (pendant driver 0.62 x scene level 0.405 = 25 % of the pendant's maximum, 100 lx).

### 2.2 All planes (task and room floor, `villa-table.md`)

| room | plane | card lx | scene | before Em (x target) | before U0 | after Em | after Emin | after U0 | x target | LA1 | LA2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bar-alcove | daybed | 200 | Reading | 812 (4.1x) | 0.59 | 200 | 29 | 0.15 | 1.00 | pass | pass |
| cinema | cinema-desk | 400 | Day | 874 (2.2x) | 0.69 | 400 | 290 | 0.73 | 1.00 | pass | pass |
| cinema | room-cinema | 20 (min) | Day | 172 (8.6x) | 0.14 | 223 | 35 | 0.16 | 11.16 | pass | n/a |
| corridor | room-corridor | 30 (min) | Day | 176 (5.9x) | 0.83 | 228 | 194 | 0.85 | 7.61 | pass | n/a |
| dining | dining-table | 100 | Dinner | 858 (8.6x) | 0.43 | 100 | 61 | 0.61 | 1.00 | pass | pass |
| dining | homework-end | 200 | Day | 641 (3.2x) | 0.48 | 200 | 136 | 0.68 | 1.00 | pass | pass |
| dirty-kitchen | dirty-kitchen-run | 500 | Day | 958 (1.9x) | 0.61 | 500 | 365 | 0.73 | 1.00 | pass | pass |
| dirty-kitchen | room-dirty-kitchen | 200 (min) | Day | 634 (3.2x) | 0.16 | 388 | 68 | 0.17 | 1.94 | pass | n/a |
| family | room-family | 100 (min) | Day | 499 (5.0x) | 0.53 | 238 | 69 | 0.29 | 2.38 | pass | n/a |
| family-bath | fb-basin | 300 | Day | 1491 (5.0x) | 0.88 | 300 | 287 | 0.96 | 1.00 | pass | pass |
| family-bath | room-family-bath | 50 (min) | Day | 594 (11.9x) | 0.42 | 307 | 186 | 0.61 | 6.13 | pass | n/a |
| guest-wc | gwc-basin | 300 | Day | 1324 (4.4x) | 0.80 | 300 | 260 | 0.87 | 1.00 | pass | pass |
| guest-wc | room-guest-wc | 50 (min) | Day | 325 (6.5x) | 0.25 | 185 | 55 | 0.30 | 3.70 | pass | n/a |
| hall-b | room-hall-b | 30 (min) | Day | 510 (17.0x) | 0.73 | 267 | 170 | 0.63 | 8.90 | pass | n/a |
| kids-a | ka-desk-1 | 400 | Day | 513 (1.3x) | 0.27 | 398 | 113 | 0.28 | 1.00 | pass | pass |
| kids-a | ka-desk-2 | 400 | Day | 517 (1.3x) | 0.29 | 401 | 120 | 0.30 | 1.00 | pass | pass |
| kids-a | room-kids-a | 50 (min) | Day | 198 (4.0x) | 0.17 | 182 | 30 | 0.16 | 3.64 | pass | n/a |
| kids-b | kb-desk | 400 | Day | 466 (1.2x) | 0.24 | 400 | 97 | 0.24 | 1.00 | pass | pass |
| kids-b | room-kids-b | 50 (min) | Day | 165 (3.3x) | 0.15 | 159 | 24 | 0.15 | 3.18 | pass | n/a |
| kitchen | cooktop | 300 | Cook | 1284 (4.3x) | 0.87 | 300 | 232 | 0.77 | 1.00 | pass | pass |
| kitchen | island-prep | 500 | Cook | 1128 (2.3x) | 0.70 | 500 | 317 | 0.63 | 1.00 | pass | pass |
| kitchen | island-seating | 200 | Day | 1049 (5.2x) | 0.72 | 200 | 162 | 0.81 | 1.00 | pass | pass |
| kitchen | room-kitchen | 50 (min) | Day | 928 (18.6x) | 0.17 | 186 | 82 | 0.44 | 3.73 | pass | n/a |
| kitchen | sink | 300 | Cook | 1229 (4.1x) | 0.69 | 300 | 224 | 0.75 | 1.00 | pass | pass |
| kitchen-island | room-kitchen-island | 50 (min) | Day | 442 (8.8x) | 0.68 | 307 | 229 | 0.75 | 6.15 | pass | n/a |
| living | room-living | 30 (min) | Day | 337 (11.2x) | 0.45 | 177 | 50 | 0.28 | 5.92 | pass | n/a |
| lounge | armchair | 200 | Reading | 893 (4.5x) | 0.59 | 200 | 113 | 0.57 | 1.00 | pass | pass |
| lounge | room-lounge | 100 (min) | Day | 400 (4.0x) | 0.56 | 165 | 45 | 0.27 | 1.65 | pass | n/a |
| pantry | room-pantry | 50 (min) | Day | 331 (6.6x) | 0.88 | 331 | 290 | 0.88 | 6.62 | pass | n/a |
| parents-bed | pillow-1 | 200 | Reading | 902 (4.5x) | 0.76 | 200 | 60 | 0.30 | 1.00 | pass | pass |
| parents-bed | pillow-2 | 200 | Reading | 899 (4.5x) | 0.76 | 200 | 60 | 0.30 | 1.00 | pass | pass |
| parents-bed | room-parents-bed | 50 (min) | Day | 208 (4.2x) | 0.05 | 143 | 3 | 0.02 | 2.87 | pass | n/a |
| parents-dressing | room-parents-dressing | 100 (min) | Day | 355 (3.5x) | 0.60 | 356 | 228 | 0.64 | 3.56 | pass | n/a |
| parents-ensuite | pe-basin | 300 | Day | 658 (2.2x) | 0.82 | 300 | 256 | 0.85 | 1.00 | pass | pass |
| parents-ensuite | room-parents-ensuite | 50 (min) | Day | 131 (2.6x) | 0.41 | 64 | 28 | 0.43 | 1.28 | pass | n/a |
| store-ramp | room-store-ramp | 50 (min) | Day | 119 (2.4x) | 0.50 | 173 | 105 | 0.61 | 3.45 | pass | n/a |
| study-game | room-study-game | 6 (min) | Day | 523 (87.2x) | 0.20 | 293 | 62 | 0.21 | 48.86 | pass | n/a |
| study-game | study-adult-desk | 400 | Day | 800 (2.0x) | 0.33 | 432 | 222 | 0.51 | 1.08 | pass | pass |
| study-game | study-desk | 400 | Day | 979 (2.4x) | 0.52 | 404 | 246 | 0.61 | 1.01 | pass | pass |

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
* Several zones need a driver below about 0.35 (daybed 0.34, family-bath basin DL 0.15, island hob 0.37, ensuite basin 0.37, armchair 0.38):
  the library has no lower-output recessed product; the family-bath counter DL at 0.15 is the extreme and is a candidate for a smaller product.
* Task-plane uniformity (U0) is reported, not gated (kids' desks 0.24 to 0.30, daybed 0.15, pillows 0.30): lamps are local sources.
* UGR is not evaluated (LA4 not_evaluated); unsourced policy values are `policy`/`unverified`, not code compliance.
* Ab 12 vs ab 6 differences up to 5.6 % on room floors: results are Radiance estimates, not measurements.

## 7. Finding for the render lane

`out/villa/render-d1/lighting-measurements.json` is **stale** (Sep 28; `scene.json` is Oct 7 and its fixtures and probe points differ). Its dining numbers
(405 / 467 lx) are the vase-obstructed probe (section 1) and the Oct 7 table top (z = -2.248) is above the 1 mm probe plane. Do not quote it; re-run with
the task-probe binding. The engine's after-state is in `knowledge/lighting/villa-after-rows.json`.

## 8. Reproduce

`villa_run --tag after --out out/L6b` (about 25 min, workstation) then `villa_emit --tag after`; solve drivers with `villa_tune_cli --tag <t> --write`
from a run made with the table applied (results embed the applied drivers). Iterations: iter1..iter3 as in git history; iter4 (V12 design changes, all 13
clusters) and iter5 (B-open, hob/prep split) are the last solves. Outputs: `out/L6b/<tag>/` (ignored by git).
