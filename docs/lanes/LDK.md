# LDK: sourced landscape rules

Lane LDK of the landscape programme (docs/quality/LANDSCAPE-METHOD.md, stage LD-K). 2026-11-22.

## What exists

| Path | Content |
|---|---|
| `knowledge/landscape/rules/rules.json` | 210 source cards, 41 computed rules, 30 advisory rules, 11 open GAPs (10 closed, recorded in `closed_gaps`), 27 withdrawn Pattern Language rules (`withdrawn`) |
| `knowledge/landscape/rules/snapshots/` | text snapshot per web card (the verbatim page text fetched 2026-11-22), so the quote guard runs offline |
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

The 30 advisory rules (`AD-*`) are prompts for the critics; they carry no number (the loader raises if one does). They are: 14 composition
prompts (`AD-COMP-*`) quoting Ching and Clark & Pause; 6 from public bodies (`AD-EXT-*`: shade placement, overlook by sight-line, pond siting,
root barriers, hedge setback, lawn in shade); `AD-FIRE-VENT-LID`, `AD-POND-EDGE-LEGIBLE`, `AD-POND-DEPTH-HAZARD`; and the Time-Saver and Lechner prompts.

## Second pass (2026-11-22): rules added, all with a positive and a negative test

| Id | Requirement | Source |
|---|---|---|
| LS-PATH-SERVICE | 600 mm wheelbarrow path (fail), 900 mm access path (warn) | Neufert 1980 p.106 Fig. 22 (values read from the rendered figure) |
| LS-LOUNGE-AREA | 1.8 m2 per lounge seat (warn) | Neufert p.211 cocktail lounge (indoor analogue) |
| LS-LOUNGE-CLUSTER | lounge zone at least 3.66 m across (warn) | Mitton & Nystuen p.80 |
| LS-STAND-AREA | 1.3 m2 per standing person; no standing zone reports not_evaluated (warn) | Neufert p.211 (Metric Handbook Table III 0.3 m2 is a crowd maximum, card `...-NOT-COMFORT`, unused) |
| LS-FIRE-STRUCT | 2 000 mm to structure, fence and planting; 4 572 mm for wood fuel (warn; product instructions govern) | Calgary Fire Dept; International Fire Code 307.4.3 (printed "15 feet (3048 mm)": 15 ft is 4 572 mm, the printed conversion is wrong) |
| LS-FIRE-OVERHEAD | 2 000 mm clear above the fire (warn) | MAD Design, Solus (1.95 m) manuals |
| LS-FIRE-COVER | declared flush-cover load rating at least 15 kN (warn) | BS EN 124 Group 1 A15, via a supplier table; the nearest class, **not** a fire-pit standard |
| LS-FLUSH-LIP / -OPENING | vertical lip 6.4 mm (bevel to 13 mm); openings 13 mm (warn) | ADA Standards 2010 s.303, 302.3 (accessibility standard borrowed for trips) |
| LS-POND-GUARD | flush pond declares a rigid grille or a 1.1 m fence (violation; client may waive) | RoSPA pond safety; Belfast Trust; no load figure exists |
| LS-POND-EDGE-SLOPE | shore slope 1:4 or gentler (warn) | Time-Saver 330 s.7.6 (stormwater ponds; out of scale) |
| LS-POND-EDGE-LIGHT | 4 lx at the edge, 8 lx over age 65 (warn) | IES Handbook Table 33.2 pool deck and steps (analogue) |
| LS-POND-DEPTH / -STOCK / -SHADE | deepest section 900 mm; 12 in fish per 0.42 m2 (aerated 43 in/m2); 50-75 % plant shade (warn) | Oklahoma State University Extension, Water Gardens 2017 |
| LS-TREE-BUILDING | trunk to building 1.25 / 0.75 / 0.5 x mature height by water demand, unknown = high (warn) | NHBC Standards 2024 ch. 4.2 Table 3b (UK clay; the site soil test governs) |
| LS-HEDGE-SPACING | in-row 300-600 mm (warn) | RHS hedge planting guide |
| LS-HERB-SUN | 6 h midsummer sun on herb and fruit beds (warn); needs the LDS sun study | RHS; Arizona says afternoon shade in a desert |

`LS-FIRE-COVER` was "never a pass" in the first pass; it can now pass at 15 kN. The pass means only "declared at the EN 124 A15 pedestrian class": the
supplier must certify the rating for a heated cover, and no cover surface-temperature figure exists (GAP-FIRE-COVER-TEMP).

**Web cards.** Each carries `url`, `retrieved` and a `snapshot`. `test_source_quotes.WebSources` checks the quote is in the snapshot and fails closed;
`LDK_LIVE=1` re-fetches the live pages. The NHBC public edition is 2024 (the current edition sits behind a login). Round-1 and round-2 research outputs were
produced by research agents, then every quote was machine-checked against its snapshot or PDF page, and 52 of the 71 web quotes were re-fetched live (`LDK_LIVE=1`); 19 were not (NHBC refuses curl and was read through a browser; a few pages are JS-rendered): those rest on their snapshot only.

**Pattern Language.** Withdrawn: the 27 rules are in `withdrawn` with status `unverified — not used`, are not `Rule` objects, and the source card is gone. The
loader refuses a withdrawn rule that is also active. 15 have a held equivalent in Ching or Clark & Pause (re-grounded as `AD-COMP-*`, listed under
`regrounded_as`); 12 have none: 105 South Facing Outdoors, 172 Garden Growing Wild, 71 Still Water, 246 Climbing Plants, 177 Vegetable Garden,
170 Fruit Trees, 125 Stair Seats, 245 Raised Flowers, 247 Paving with Cracks Between the Stones, 168 Connection to the Earth, 104 Site Repair, 60 Accessible Green.
**Unwin's *Analysing Architecture* is an image-only PDF** (0 characters of text on 207 pages; no OCR on this machine), so it was not used.

## Decisions

1. **Rules framework.** `rules.Rule` (stage 4 "Rooms" as the nearest stage; the fix ladder is in-stage, then Order/L1, then Fit/L2) holds every rule; results use `contracts.CheckResult`, as `docs/quality/LANES.md` asks. `rules.Finding` was not used because its stage model is for building rooms.
2. **Quote guard.** Each `sourced` card's quote is checked against the cited PDF page by `test_source_quotes.py` (skips where the book is absent). It first tries a contiguous match, then every number plus 85 % of the words, because the two-column Time-Saver pages interleave lines. It catches a wrong figure; it cannot prove a paraphrase.
3. **Derived figure.** 3.46 m2 per dining seat is ours, derived from a 4-seat drawing (Fig. 210-3). The card says so. The brief asks for 10-20 people; a per-seat rule at 3.46 m2 puts a 12-seat dining group at 41.5 m2 before circulation.
4. **Stricter than the source.** LS-SCREEN uses 1.8 m on all neighbour sides (the source allows 1.2 m at party fences) because the brief makes privacy critical. LS-DINE-CLEAR applies the 1 200 mm on all sides. Both are marked policy on their cards.
5. **Warning grade.** Where a source figure is typical, perceptual or from a different context (seat walls, enclosure, fire-ring seat distance, root zone, hydrozone) the rule reports `warn`, not `fail`.
6. **Koi depth is not 450 mm.** Time-Saver's 300-450 mm is a US fountain-pool figure tied to a code reading. It is recorded as a card named `...-depth-NOT-KOI` that no rule uses (a test asserts this), so nobody uses it for koi.
7. **No new dependency.** shapely, pymupdf (test only) were already installed.

## GAPs

Closed (rule -> figure) are in `closed_gaps` in rules.json and in the hand-back. Open after the second pass:

| Id | What is still missing |
|---|---|
| GAP-POND-EDGE-SAFETY | a contrast figure, a koi-pond safety-shelf width, a pond-grille load figure |
| GAP-POND-EDGE-CONTRAST | published luminance-contrast or margin width for a pond edge |
| GAP-POND-GRILLE-LOAD | a kN or kg figure for a pond grille (RoSPA says "rigid", fire services "a child's weight") |
| GAP-FIRE-COVER-TEMP | surface temperature and walk-on load of the chosen product's flush cover (supplier certificate) |
| GAP-POND-TREES-SUN | a distance in metres from trees |
| GAP-SHADE-TARGET | the percentage target (client); BR 209 not held |
| GAP-OVERLOOK-ABOVE | no published height; LDS sight-line geometry |
| GAP-LAWN-WIDTH | minimum width and wear |
| GAP-SPACING-TREES | per-species spread (LDL) and a spacing principle |
| GAP-SCREEN-DENSITY | evergreen hedge opacity |
| GAP-BOOKS-NOT-HELD | Pattern Language, Site Analysis, BR 209; OCR for Unwin |

**Books not held (first-pass text, superseded above).** On this workstation only the Time-Saver landscape PDF (plus Metric Handbook, Lechner, Time-Saver
Interior, Neufert) exists in `~/ai-projects/archpipe-knowledge-data/drop_in/done`. The knowledge index (`~/archpipe-sources/_index`)
is empty here (0 books) and the `archpipe_books` corpus does not include Pattern Language, Site Analysis or BR 209.
So the A Pattern Language rules cite number and name only (status `unverified`; no text quoted or paraphrased as from the book),
and the dry-climate planting guide is the xeriscape section of Time-Saver 550. Re-grade the `AD-APL-*` rules once the book is held.

## Result on the current garden (read-only), second pass

`python -m archpipe.landscape.rules.current_garden`: 6 fail, 1 warn, 13 pass, 15 not evaluated (was 6 / 1). The new rules added: LS-TREE-BUILDING warns (frangipani
trunk 2.98 m from the facade where 5.7 m = 0.75 x 7.6 m is the NHBC zone, moderate water demand assumed); LS-LOUNGE-AREA and -CLUSTER pass; LS-STAND-AREA is not
evaluated because the garden has no standing zone; the flush-feature rules, pond rules and LS-HERB-SUN do not run because the garden has none of those features.
The adapter now passes the palette's mature height; `water_demand` is set to NHBC's default "moderate" (LDL should confirm).

## Result on the current garden (read-only), first pass

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
