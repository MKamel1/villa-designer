# LDK: sourced landscape rules

Lane LDK of the landscape programme (docs/quality/LANDSCAPE-METHOD.md, stage LD-K). 2026-11-22.

## What exists

| Path | Content |
|---|---|
| `knowledge/landscape/rules/rules.json` | 30 source cards, 24 computed rules, 34 advisory rules, 16 GAPs |
| `knowledge/landscape/rules/current-garden-layout.json` | the current D1 garden as a layout (snapshot, generated) |
| `src/archpipe/landscape/rules/loader.py` | `load()` validates the JSON, builds `archpipe.rules.Rule` objects and `contracts.SourceCard`s |
| `src/archpipe/landscape/rules/checks.py` | `evaluate(layout)` returns `contracts.CheckResult` records; `summarize()` |
| `src/archpipe/landscape/rules/current_garden.py` | read-only adapter from `concept/villa_landscape.py`; `python -m archpipe.landscape.rules.current_garden [--write]` |
| `tests/landscape/rules/` | rule positives and negatives, loader fail-closed tests, quote-vs-PDF guard, current-garden method guard |

## Use

```python
from archpipe.landscape.rules import load, evaluate
rs = load()                       # RuleSet: .rules (Rule), .params, .sources (SourceCard), .gaps, .advisory_ids
results = evaluate(layout, rs)    # list[CheckResult]: pass | fail | warn | not_evaluated
```

A rule with `severity: warning` reports `warn` when not met. A rule whose input is absent reports
`not_evaluated`, never `pass`. Every result carries its source card ids and achieved/required/unit.
CheckResult `criterion` is the rule id (`LS-...`); there are no landscape criteria in `docs/quality/a-plus-*.md`
yet, so the lead should map them when the critic calibration (LD-C) is written.

## Layout schema: `landscape-layout/1`

Metres, model frame (street side = north = -x; south garden = +x). Shapes are `rect: [x0, y0, x1, y1]`, or
`center: [x, y]` with `diameter_m` (or `size_m: [w, d]`). Every list item has an `id`. Unknown keys are ignored.

| Key | Item fields |
|---|---|
| `zones` | `use` (dining, lounge, quiet, other), `rect`, `surface` (paving, lawn, artificial-turf, gravel, planting, water), `slope_pct`, `enclosure_height_m` |
| `paths` | `class` (main, secondary, service), `width_m`, `cross_slope_pct`, `long_slope_pct` |
| `paved_areas` | `rect`, `material` (concrete, flagstone, brick, ...), `slope_pct` |
| `steps` | `riser_mm`, `going_mm`, `count`, `width_mm`, `tread_pitch_pct` |
| `seatwalls` | `height_mm`, `width_mm` |
| `tables` | `zone`, `center` + `diameter_m` or `size_m`, `seats` |
| `seating` | `zone`, `rect`, `seats` (benches, sofas, chairs) |
| `planting_groups` | `rect`, `over_structure`, `soil_depth_mm`, `plants[]` of `{species, water_need: low/medium/high, form: ground_cover/shrub/small_tree/large_tree}` |
| `trees` | `species`, `center`, `mature_spread_m`, `form`, `over_structure`, `soil_depth_mm` |
| `features` | `kind` (firepit, heater, bbq, pond, herb_bed, fruit_tree), footprint; fire: `flush`, `cover.load_rating_kN`, `product_clearance_mm`; pond: `edge` (hard, soft), `freeboard_mm`, `flush`, `margin_slope_back_mm`, `volume_m3`, `depth_mm` |
| `boundary` | `side` (neighbour, street), `kind` (wall, fence, hedge), `height_m` |
| `buildings` | list of `[x0, y0, x1, y1]` |
| `obstacles` | extra walls, planters, kerbs a clear zone must keep free |

## Rules (computed)

| Id | Requirement | Source (held, page read) |
|---|---|---|
| LS-PATH-MAIN / -SECONDARY | clear width 1 200 / 600 mm | Time-Saver Landscape 2nd ed. 340-5 |
| LS-STEP-RISER | 115-150 mm (175 utilitarian: warn) | TS 340-8 |
| LS-STEP-2RG | 2R + G = 650-675 mm | TS 340-8 |
| LS-STEP-COUNT | at least 2 steps (no single step) | TS 340-8 |
| LS-STEP-WIDTH / -LANDING | private stair 1 050 mm; rise between landings 1 500 mm | TS 340-11 |
| LS-SEATWALL | height 350-450, width 400-450 mm (warn) | TS 340-11 |
| LS-DINE-AREA | 3.46 m2 per seat (derived from Fig. 210-3: 4 200 mm circle / 4 seats) | TS 210-3 (figure read) |
| LS-DINE-CLEAR | 1 200 mm table edge to obstruction (conservative: all sides) | TS Fig. 210-3; Time-Saver Interior 268 |
| LS-CAPACITY | at least 10 seats | client brief (policy) |
| LS-BRIEF-FEATURES | fire pit/heater, BBQ, pond, herb bed/fruit tree present | client brief (policy) |
| LS-FIRE-CLEAR | 900 mm clear level ground (fail), 1 200 mm recommended (warn) | TS 240-19 |
| LS-FIRE-SEAT | 1 500 mm fire to seat (warn) | TS 520-24 |
| LS-FIRE-PRODUCT | product clearance, entered by the designer; not_evaluated until then | client brief (policy) |
| LS-FIRE-COVER | a declared cover load rating is a warn, never a pass | client brief; GAP |
| LS-POND-FREEBOARD | hard edge 75 mm, soft edge 150 mm below rim | TS 530-15 |
| LS-POND-FLUSH-MARGIN | paving sloped back to the pond from 600 mm beyond clearance (warn) | TS 530-15 |
| LS-SOIL-DEPTH | over structure: lawn 200, ground cover 250, shrub 600, small tree 750, large tree 1 500 mm | TS 610-9 Table 610-4 |
| LS-SLOPE | terrace 0.5-2 % (unit paving 0.75-2 %), walk cross 1-4 % (main path <= 2 %), long. <= 10 %, recreation lawn 1-5 % | TS 320-13 Table 320-2; 240-8 |
| LS-HYDROZONE | one water-need class per planting group (warn) | TS 750-11 |
| LS-ENCLOSURE | enclosing height : room width >= 1:4 (warn) | TS 340-4 |
| LS-SCREEN | neighbour boundary 1.8 m (hedge: warn on density) | Metric Handbook 7th ed. 22-18; brief |
| LS-ROOTZONE | no paving or building inside the mature dripline (warn); turf over it not_evaluated | TS 550-6 |

The 34 advisory rules (`AD-*`) are prompts for the critics: 27 A Pattern Language patterns by number and name,
plus Time-Saver enclosure, water setting, stair rhythm, step announcement, turf purpose, lush dry planting,
and Lechner shade-by-compass. They carry no number (the loader raises if one does).

## Decisions

1. **Rules framework.** `rules.Rule` (stage 4 "Rooms" as the nearest stage; the fix ladder is in-stage, then Order/L1, then Fit/L2) holds every rule; results use `contracts.CheckResult`, as `docs/quality/LANES.md` asks. `rules.Finding` was not used because its stage model is for building rooms.
2. **Quote guard.** Each `sourced` card's quote is checked against the cited PDF page by `test_source_quotes.py` (skips where the book is absent). It first tries a contiguous match, then every number plus 85 % of the words, because the two-column Time-Saver pages interleave lines. It catches a wrong figure; it cannot prove a paraphrase.
3. **Derived figure.** 3.46 m2 per dining seat is ours, derived from a 4-seat drawing (Fig. 210-3). The card says so. The brief asks for 10-20 people; a per-seat rule at 3.46 m2 puts a 12-seat dining group at 41.5 m2 before circulation.
4. **Stricter than the source.** LS-SCREEN uses 1.8 m on all neighbour sides (the source allows 1.2 m at party fences) because the brief makes privacy critical. LS-DINE-CLEAR applies the 1 200 mm on all sides. Both are marked policy on their cards.
5. **Warning grade.** Where a source figure is typical, perceptual or from a different context (seat walls, enclosure, fire-ring seat distance, root zone, hydrozone) the rule reports `warn`, not `fail`.
6. **Koi depth is not 450 mm.** Time-Saver's 300-450 mm is a US fountain-pool figure tied to a code reading. It is recorded as a card named `...-depth-NOT-KOI` that no rule uses (a test asserts this), so nobody uses it for koi.
7. **No new dependency.** shapely, pymupdf (test only) were already installed.

## GAPs (no held source; not filled)

| Id | Brief item |
|---|---|
| GAP-PATH-SERVICE | service path width |
| GAP-LOUNGE-AREA | area per person for a lounge group and standing room |
| GAP-FIRE-SAFETY | fire pit/BBQ distance to combustible facade and planting (product instructions govern) |
| GAP-FIRE-COVER-LOAD | flush fire pit cover load rating, fall and burn protection |
| GAP-POND-DEPTH | koi depth and volume (supplier) |
| GAP-POND-EDGE-SAFETY | flush pond edge visibility, contrast margin, safety shelf, night lighting of the edge |
| GAP-POND-TREES-SUN | pond distance to trees (leaf fall), sun/shade on the water |
| GAP-TREE-BUILDING | tree distance to buildings, walls, services; root barriers |
| GAP-SPACING | planting spacing at maturity |
| GAP-SHADE-TARGET | shade-tree placement and shade percentage in summer (BR 209 not held) |
| GAP-SCREEN-PLANT | hedge heights and densities |
| GAP-OVERLOOK-ABOVE | screening from the apartment above |
| GAP-HERB-SUN | herb and fruit sun needs (belongs to the plant library) |
| GAP-LAWN-WIDTH | lawn minimum width and wear |
| GAP-TS-COMPOSITION | Time-Saver composition (focal points, rhythm, repetition, layering) |
| GAP-BOOKS-NOT-HELD | A Pattern Language, Site Analysis, BR 209 are not on this machine |

**Books not held.** On this workstation only the Time-Saver landscape PDF (plus Metric Handbook, Lechner, Time-Saver
Interior, Neufert) exists in `~/ai-projects/archpipe-knowledge-data/drop_in/done`. The knowledge index (`~/archpipe-sources/_index`)
is empty here (0 books) and the `archpipe_books` corpus does not include Pattern Language, Site Analysis or BR 209.
So the A Pattern Language rules cite number and name only (status `unverified`; no text quoted or paraphrased as from the book),
and the dry-climate planting guide is the xeriscape section of Time-Saver 550. Re-grade the `AD-APL-*` rules once the book is held.

## Result on the current garden (read-only)

`python -m archpipe.landscape.rules.current_garden`: 6 fail, 1 warn.

| Rule | Achieved vs required |
|---|---|
| LS-CAPACITY | 4 seats (a bench and two chairs) vs 10 |
| LS-BRIEF-FEATURES | fire pit/heater, BBQ, pond, herb bed/fruit tree: all absent |
| LS-SOIL-DEPTH | top trough (rosemary) 245 mm vs 250 mm: a 5 mm near miss; it is an upper bound on soil depth, so likely a real shortfall |
| LS-ROOTZONE (warn) | the mature Plumeria dripline (7.6 m spread, upper palette bound) covers 2.0 m2 of the building; trunk 2.98 m from the facade |

Not evaluated, with the reason: hydrozone (8 groups, no water need in the garden data), two Aloe troughs (height unverified in
the palette), frangipani soil depth, root zone under artificial turf (permeability UNVERIFIED), slopes, steps.
Passes: secondary path widths (914 mm vs 600), enclosure (ratio 0.67), screening (4.0 m fences).

The rules catch what the brief now asks that the garden lacks (use, capacity, features). They cannot say the garden does not look
like a landscape: that stays with the critics and precedent ranges.

## Brief risks the findings raise

- **Flush pond and flush fire pit** have almost no held source for their hazards: edge visibility, safety shelf, night lighting, cover load rating are all GAPs. The only held figure (Time-Saver 530-15, 600 mm sloped margin) is about splash, not a person stepping in. The client's addendum rests on professional input here.
- **10-20 people** has a per-seat dining figure but no lounge or standing figure; a 20-person event cannot be area-checked beyond the dining group.
- **Privacy from the apartment above** is not solvable by a boundary height; it needs the LDS sight-line work and a canopy rule that no held source gives.
- **Frangipani and the facade**: at the palette's upper mature spread the canopy reaches 3 m from the facade; roots near foundations of unknown depth stay with a professional (brief).

## Open items

- Acquire Pattern Language, Site Analysis, BR 209; then read the patterns and add the BR 209 sunlight-to-garden rule.
- LDL should supply `water_need` and `form` per species; the adapter then lets LS-HYDROZONE and LS-SOIL-DEPTH run.
- Map `LS-*` ids to A-plus criteria when the landscape criteria are written.
- Source cards are checked against the PDF only where the PDFs are present (the workstation).
