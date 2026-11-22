# Lane SC3: south B wall roof slot, dining pendant body (2026-11-22)

Base `origin/lane/L6d` `e5e8d48`. Evidence `knowledge/approvals-review/evidence-sc3/`, previews `knowledge/approvals-review/previews-sc3/`.

## 1. South B wall roof slot

* **Diagnosis.** `spec.walls[9]` (`wall-B-ext-09`, x 6.877..15.412, y -20.701) is one piece, 2.65 m high. The deck ends at x 12.777; beyond it
  `slab-roof-0` (soffit 2.80 m above the B floor). The wall runs 2.635 m (12.777..15.412) under that roof: **150 mm open** (top -0.35, soffit -0.20).
  `clearance_problems` hid it: it measured walls along the ramp against the deck soffit only.
* **Fix (append, not split, not a stepped top).** An infill `{"what": "wall top up to the extension roof soffit", x 12.777..15.412, y -20.801..-20.601,
  z -0.35..-0.20}` is appended to `spec["infills"]` (scene id `spec-ramp-wall-infill-3`; indices 0-2 and all 36 wall indices unchanged).
  Why: splitting wall 9 renumbers `wall-B-ext-10..` and `wall-GF-*` (ids are list indices) and every approval keyed on them; a wall has
  one height field (no stepped top without a new wall schema and new scene/model/IFC support); the ramp already closes exactly this kind of gap with
  `infills` (the existing `clearance_problems` cover logic reads them). `clearance_problems` now measures along-ramp walls against the roof beyond
  the deck as well (it still reports the slot on the spec without the infill: "150 mm open under the soffit at its high end"), so the ramp-clearance critic was not loosened.
* **Guard.** `revit_spec.wall_top_readings / wall_top_problems` (every wall, both levels): the soffit above a wall is the ramp/deck/roof soffit for B walls in the
  extension and the next slab (2.80 m) for any other wall; an infill ending at the wall's high end closes a gap. `tests/model/test_sc3_walltop.py`: all 36 walls read,
  0 problems; **positive** (the real spec without its appended infill) -> exactly wall #9, 150 mm open; negative (36 walls, none flagged); a 2.95 m wall is reported as through its soffit; id stability.
* **Readings (every wall; gap = soffit - max(top, infill top); tolerance 20 mm; 0 through):**

| # | lvl | from -> to (m) | top | soffit | closed by | gap mm |
|---|---|---|---|---|---|---|
| 0 | B | (3.62,-29.82)->(6.94,-29.82) | -0.200 | -0.200 | wall top | 0 |
| 1 | B | (17.27,-29.82)->(22.60,-29.82) | -0.200 | -0.200 | wall top | 0 |
| 2 | B | (6.74,-28.57)->(17.47,-28.57) | -0.200 | -0.200 | wall top | 0 |
| 3 | B | (3.62,-28.67)->(6.94,-28.67) | -0.200 | -0.200 | wall top | 0 |
| 4 | B | (15.41,-23.69)->(22.60,-23.69) | -0.200 | -0.200 | wall top | 0 |
| 5 | B | (3.62,-23.59)->(15.41,-23.59) | -0.200 | -0.200 | wall top | 0 |
| 6 | B | (-0.12,-20.70)->(0.88,-20.70) | -1.550 | -1.450 | infill | 0 |
| 7 | B | (0.88,-20.70)->(5.88,-20.70) | -1.450 | -0.450 | infill | 0 |
| 8 | B | (5.88,-20.70)->(6.88,-20.70) | -0.450 | -0.350 | infill | 0 |
| 9 | B | (6.88,-20.70)->(15.41,-20.70) | -0.350 | -0.200 | infill | 0 |
| 10 | B | (-0.02,-23.59)->(-0.02,-20.60) | -1.550 | -1.540 | wall top | 10 |
| 11 | B | (3.12,-23.59)->(3.12,-20.60) | -1.010 | -1.000 | wall top | 10 |
| 12 | B | (3.72,-29.92)->(3.72,-23.59) | -0.200 | -0.200 | wall top | 0 |
| 13 | B | (6.84,-29.92)->(6.84,-28.67) | -0.200 | -0.200 | wall top | 0 |
| 14 | B | (9.23,-23.59)->(9.23,-20.60) | -0.350 | -0.350 | wall top | 0 |
| 15 | B | (11.20,-23.59)->(11.20,-20.60) | -0.350 | -0.350 | wall top | 0 |
| 16 | B | (15.31,-23.59)->(15.31,-20.60) | -0.200 | -0.200 | wall top | 0 |
| 17 | B | (17.37,-29.92)->(17.37,-28.67) | -0.200 | -0.200 | wall top | 0 |
| 18 | B | (22.50,-29.92)->(22.50,-23.59) | -0.200 | -0.200 | wall top | 0 |
| 19 | GF | (19.60,-31.21)->(22.32,-31.21) | 2.800 | 2.800 | wall top | 0 |
| 20 | GF | (19.60,-28.88)->(22.32,-28.88) | 2.800 | 2.800 | wall top | 0 |
| 21 | GF | (3.62,-28.57)->(19.80,-28.57) | 2.800 | 2.800 | wall top | 0 |
| 22 | GF | (22.12,-28.57)->(22.60,-28.57) | 2.800 | 2.800 | wall top | 0 |
| 23 | GF | (11.48,-27.37)->(19.53,-27.37) | 2.800 | 2.800 | wall top | 0 |
| 24 | GF | (19.53,-26.64)->(22.60,-26.64) | 2.800 | 2.800 | wall top | 0 |
| 25 | GF | (9.23,-26.37)->(11.48,-26.37) | 2.800 | 2.800 | wall top | 0 |
| 26 | GF | (3.62,-23.69)->(22.60,-23.69) | 2.800 | 2.800 | wall top | 0 |
| 27 | GF | (3.72,-28.67)->(3.72,-23.59) | 2.800 | 2.800 | wall top | 0 |
| 28 | GF | (9.23,-26.37)->(9.23,-23.59) | 2.800 | 2.800 | wall top | 0 |
| 29 | GF | (11.48,-27.37)->(11.48,-23.59) | 2.800 | 2.800 | wall top | 0 |
| 30 | GF | (14.95,-27.37)->(14.95,-23.59) | 2.800 | 2.800 | wall top | 0 |
| 31 | GF | (18.43,-27.37)->(18.43,-23.59) | 2.800 | 2.800 | wall top | 0 |
| 32 | GF | (19.53,-28.67)->(19.53,-26.64) | 2.800 | 2.800 | wall top | 0 |
| 33 | GF | (19.70,-31.31)->(19.70,-28.67) | 2.800 | 2.800 | wall top | 0 |
| 34 | GF | (22.22,-31.31)->(22.22,-28.67) | 2.800 | 2.800 | wall top | 0 |
| 35 | GF | (22.50,-28.67)->(22.50,-23.59) | 2.800 | 2.800 | wall top | 0 |

  Walls 10 and 11 (cross walls) read 10 mm: they are cut to the clear height at their low face (a standing rule since r7), inside the 20 mm tolerance.
  Wall 9 reads 0 with the infill (150 without it).
* **Ownership exceptions.** `knowledge/c4-e-lead-approvals.json`: the approved row `host-face-support-appliance-hood-dirty-canopy` follows the new coplanar face (x0 15.212 -> 12.777 in `old`/`new`; the
  13 mm movement and the face top -0.20 unchanged; `re_review` recorded), same class as SC2's; lead to confirm. `src/archpipe/fixture_record.py` (item 2).

## 2. Dining pendant body

* **Source -> built.** `knowledge/lighting-products/iguzzini/QA03/QA03.ldt` header (lines 13-15): diameter **59**, width 0 (round), height **250** mm; the product page: "Diameter (mm) ø59". Before: lamp-body
  59 x 59 x **60** mm (`fixture_record.py` PEN-LIN housing `height=.06`), wire 1128 mm. After: **59 x 59 x 250** mm (z -1.488..-1.238, bottom unchanged, so the diffuser and the light positions did not move),
  the two 4 mm wires 938 mm from the top of the body to the ceiling, ending on the body top (test). The body stays the square 59 mm envelope (lamp-housing admits boxes); a round body was not drawn (not asked; appearance only).
* **Exemption.** The longer wire is a new shape: `c3-part-exemptions.json` gains record `c3-retained-lamp-wire-qa03` (kind lamp-wire, digest `6102b5cf...`) with `evidence` = the LDT/page data. The object was not shrunk.
  `add_light`, positions and photometry untouched (the pendant is an emissive mesh, no entry in `lights`).
* **Guard.** `tests/test_villa_render_pendant_dims.py` builds the scene and compares every `lamp-body-PEN-*` mesh with the LDT header of its product (`PRODUCT_CHOICE`), +-5 mm; it **fails on the old build**
  ("drawn 59 x 59 x 60 mm, published 59 x 59 x 250 mm", run on the stashed old housing) and passes now; a wire-reaches-ceiling check and a negative are included. Generic globe pendants have no published size and are not read (stated, not claimed).
* **Ownership exception.** `src/archpipe/fixture_record.py` (the housing constant lives there, outside SC3 paths).

## Receipts, exposure, production scene

* **Receipts (RA method).** Old = `origin/lane/L6d` worktree, new = this branch, both exported with receipts bypassed (jobq `SC3-export-old/new`). **The old tree reproduces all 8 stored digests.** layout, furniture, meshes,
  models, props, materials **unchanged**; specification changed in `infills` only; architecture **0 removed, 46 added, all inside x 12.777..15.412, y -20.814..-20.601, z -0.35..-0.20 (the infill and its finish layers), 0 unexplained**
  (`arch_attribution.py` new zone; 35 in it, 11 first matched SC2's wall-16 zone: same box). 16 individual + joint baseline-relative reviews: all ok, 0 findings (`SC3-review-current`). The dining pendant is in no receipt room, so it changes no section.
  Receipts rewritten by `refresh_receipts.py --write` (note extended). Evidence `evidence-sc3/`.
* **Exposure.** Re-measured through the documented procedure (`write(measure_exposure_groups=True)`, ERCO IES beside the scene, Blender `villa_scene.py --measure-exposure-groups`, jobq `SC3-measure-exposure-2`), copied byte for byte.
  Largest change in any lamp fraction: 0.0006 (`v17-dirty-kitchen` 0.1078 -> 0.1072); no group changes its side of the 0.5 threshold (0 flips of 41).
* **Production build** (`benchmark_scene_build.py --write-scene`, receipts and record active, no bypass, jobq `SC3-prod1`, 165 s): scene.json sha256 `a7558cfcdc43930505f86f5248e311b6a566e3f9e305ef0dc34fa7877e05a073`, ids stripped
  (`json.dumps(without_ids(scene), sort_keys=True)`) `9b6525448d3487abdbe62ede5e0d6118991957437849cec26d6579f40930f592`, **1,223 meshes** (L6d base 1,221: +2 because the new infill faces merge into the shell/finish-layer meshes and renumber them),
  113 lights, source hash `54d6ace351247d4291c0c040aa40318b8973ed8339271d10b439c1a4b94a46f5`. Base rebuilt the same way (`SC3-prod-old`): scene `bdd3cd558a9a...`, stripped `699ad32f8876...`, source hash `4fcb8572...` (= L6d's recorded), 1,221 meshes.
  Mesh differences old -> new: only the finish-layer renumbering, `shell-000/025/050`, the pendant body and its two wires, and the hood's `mounting.finished_face` metadata (geometry identical to 1e-15).
* **Model, IFC, schedules.** The infill is not a model element and the pendant body is scene-only: `tests/model` snapshot tests pass unchanged, so no model snapshot, schedule, drawing or IFC regeneration was needed (IFC regenerated only as the RV1 input: `SC3-exchange`).

## RV1 (`parity.run_d1 --scene <scene> --ifc out/exchange/D1/D1-ARCH.ifc --prove`), before (L6d base scene) -> after (SC3 scene)

| check | before pass/fail/n.e. | after |
|---|---|---|
| K06 | 0 / 1 / 0 (window-B-dirty-kitchen-0: 500 mm below the soffit) | 0 / 1 / 0 (identical) |
| K09 | 1 / 0 / 8 | 1 / 0 / 8 |
| K10 | 51 / 2 / 0 | 51 / 2 / 0 |
| K14 | 3 / 0 / 0 | 3 / 0 / 0 |

Totals 291 pass / 20 fail / 10 n.e. both; mutations 39, 36 caught, the same three documented misses (M1, M6-180, M-K10-move0.1); the historic/synthetic recall table and the 30 findings are identical (reports compared equal on `counts`, `mutations`). Nothing dropped; the wall slot was never an RV1 finding (K06's 500 mm is the full-height window head against the soffit, unchanged).

## Previews (draft, 32 samples, 800x500, jobq GPU `SC3-prev-new3/4`, `SC3-prev-old3`; preview cameras injected into a copy without the exposure record; each looked at)

* `sc3-wall-inside.png` (dirty kitchen, day, camera 14.1,-23.3,-1.8 looking at the south wall): the wall carries the hood and runs to the ceiling with no dark strip at its top; very dark draft exposure (not judged for lighting).
  `sc3-wall-inside-BEFORE.png` (same camera on the L6d scene): a distinct dark horizontal band at the wall top, ~2/3 of the wall's width, which is the 150 mm slot; it is gone in the new image.
* `sc3-wall-outside-a/b.png`: **the wall's outside is not visible from any camera I could place.** South of the wall is a tight lane bounded by a neighbouring wall (view a: a black wall 2 m away, only paving at the bottom edge); view b (from the east yard,
  looking west along it) shows a large dark wall, the lane's paving and dusk sky: dark and not informative about the strip. The outside is proven by the geometry guard and the RV1/receipt numbers, not by an image. (Day state rendered as dusk because the preview copy has no exposure record.)
* `sc3-dining-pendant.png` (evening, 26 mm): above the dining table a slim black cylinder, about four times as long as it is wide, hangs on two thin wires to the ceiling with a lit disc at its lower end; it reads as a Laser pendant and no longer as a 60 mm stub;
  the island globes and stair are unchanged. Nothing floats or pierces.

## Tests (fresh clone of the pushed branch)

Fresh clone of pushed `lane/SC3` `46db0fe` (jobq `SC3-tests1`, 2,197 s): the INT lane suite (luminaires, compliance, design, model, electrical, lightcalc, lightverify, critic, ops, documents, drawings2d,
pipeline, exchange, approvals, test_villa_lighting, test_exposure_groups) + tests/parity, tests/markup, tests/test_villa_render*.py, tests/test_mounting*.py, tests/test_d1_*.py, tests/test_villa_parking.py:
**878 passed, 7 skipped, 1 xfailed, 4 failed**. The 4 are exactly LV's old-product pins (`tests/lightverify/test_v10_erco.py` x2, `test_v1_design.py` x2); nothing else fails.
`python -m archpipe.compliance.run_d1` (jobq `SC3-compliance`): exit 0, 198 results, 0 failing gates (regenerated L1 report reverted).
`python scripts/lane_guard.py SC3 --base origin/lane/L6d`: reports 3 files: `knowledge/c4-e-lead-approvals.json`, `src/archpipe/fixture_record.py` (the two ownership exceptions above) and `ops/lanes.yaml` (the lead's own SC3 ownership commit, cherry-picked from the old lane head).

**Shared-file step not done:** `origin/integ/aplus` (`7203c57`) does not yet contain `origin/lane/L6d` / `lane/LV`; the final merge of integ/aplus, receipt regeneration, re-measure and rebuild is still to do once they merge (procedure above, all jobq ids reusable as templates).

## Open items

* The lead should confirm the re-reviewed hood host-face row (`c4-e-lead-approvals.json`) and the `fixture_record.py` ownership exception.
* An outside image of the south wall strip needs a camera inside the lane or a section view; none was found that shows it.
* K06 `window-B-dirty-kitchen-0` (500 mm header, full-height window) is unchanged, a design decision noted by SC2.
