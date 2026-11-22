# LDG: landscape concept generation (2026-11-22)

> **Pass 2 (2026-11-22, typology first) supersedes pass 1 for the concepts shown.** Read `knowledge/landscape/concept/pass2/REPORT.md` (generated; the three concepts, programme tables, schedules, trade-offs, recommendation) and the section below. Pass 1 (random furniture packing) is kept below as the record of what was rejected.

## Pass 2: typology first, then furniture (what changed and why)
Lead review of pass 1: three functional packings, not landscapes (a large paved rectangle with a 0.6 m perimeter strip, two with no tree, identical north court and east yard, a 4-seat table for a 10-20 person brief).
Pass 2 reverses the order. A **typology** fixes the bones (rooms, axis and focal point, planting masses, canopy); the furniture is then fitted into the bones at the rule distances, and the LDK rules plus our policy checks decide what survives.

| | A Tree court | B Two rooms | C Axial terrace |
|---|---|---|---|
| organising idea | courtyard room around one focal tree (centralised organisation, Ching) | sociable terrace + quiet garden room (the east yard) divided by a planted mass; graded public-to-private | terrace wrapped by deep borders with a main axis door -> fire pit -> sculpture place |
| focal point | pomegranate (+ the pond in the yard) | the pond in the quiet yard room | fire pit on the axis, lit sculpture place at its end |
| hearth | east (fire pit 5.45 m from the west line) | west end (wind), bench along the screen | on the axis (b 4.0), BBQ west, table east |
| own north court | gravel room around a fatsia/Phoenix mass | quiet niche behind a planted screen | axis to a sculpture place / the pond |
| own east yard | layered fence border; bench + pergola facing the pond | quiet room with the pond as focal | service path to a sculpture place / long pond |

Code: `src/archpipe/landscape/concept/ty_core.py` (frames, planting drifts, own checks, assembly), `ty_south.py` (three south typologies), `ty_courts.py` (north court and east yard kits), `ty_run.py` (runner), `ty_report.py` (REPORT.md). Run: `python -m archpipe.landscape.concept.ty_run` then `python -m archpipe.landscape.concept.ty_report` (plans and massing need LDC plan style 2 and `massing_png`, i.e. `origin/lane/LDC`, and jobq). Tests: `tests/landscape/concept/test_pass2.py` (24 with the pass-1 tests).
Furniture parameters in `ty_run.PARAMS` were fitted by hand-guided probes at the rule distances (not a random search); the typology is the part that is designed.

**What the rules fix in a 5.71 x 9.32 m garden (why every concept has a paved hearth court):** the fire pit needs 2.0 m from the house, fences, beds, trees' crowns and the pot (LS-FIRE-STRUCT) and 1.5 m from any seat or table (LS-FIRE-SEAT), so its centre sits at depth 2.45-3.26 m and no bed can come within 2 m; a table needs 1.2 m from beds, walls, seats and the BBQ (LS-DINE-CLEAR), so an 8-seat table (2.4 m) plus pit, BBQ, 1.2 m border and herb strip uses the whole 9.3 m width with 0.1-0.3 m to spare. Planting therefore goes where the fire is not: the west and east borders, the rear corners and the yard.

Results (all six packages, west line screened): zero hard failures (LDK `fail` plus the LDK shortfalls graded `warn` for FIRE-STRUCT, FIRE-SEAT, ROOTZONE, HYDROZONE, TREE-BUILDING, plus ours: privacy, evening shade, border depth, spread, toxicity, sun fit, geometry). Dining 8 (end chairs 10; 12 does not clear 1.2 m: measured 600-700 mm), built-in benches 0.6 m per person (policy), seated 15-23, standing 18-21 at 1.3 m2. One canopy tree per south garden (1.88 per 100 m2, inside the range; 1.34 on south + yard). Hard share 0.818 (A, inside), 0.856 (B) and 0.826 (C) against 0.52-0.82. LDC critics (uncalibrated) fail 5-9 findings per package; C fewest. Recommendation: **C, pond in the east yard** (runner-up A). Details, caveats and what is rejected are in the REPORT.

Merge note: pass 2 renders with LDC's `plan_png` style 2 and `massing_png` (origin/lane/LDC); this branch contains none of LDC's files (lane_guard clean against integ/staging).

---


Stage LD-G of `docs/quality/LANDSCAPE-METHOD.md`. Nothing is drawn freehand: concepts are composed from LDK rules, LDS layers, LDL plants (viable or conditional only)
and the frozen LDP ranges (`targets-2.json`), generated as random candidates, filtered by the hard checks, ranked and then selected.
Rebuild: `PYTHONPATH=src python -m archpipe.landscape.concept.run_all 240000` (about 10 min, 30 cores). Output: `knowledge/landscape/concept/`.
Tests: `python -m pytest tests/landscape/concept -q`.

## Method record (files in knowledge/landscape/concept/)
| step | file | content |
|---|---|---|
| 1 Programme | `programme.json` | uses with rule areas against measured zones, six seat/standing scenarios, honest summary |
| 2 Zoning | `zoning.json` | grid enumerations (229 dining rooms, 252 fire-pit positions, quiet-seat squares, 2 pond locations) scored on the LDS layers |
| 3-4 Structure, planting | `candidate-counts.json`, `concept-{H,O,W}.json`, `species-pool.json` | counts per stage; per concept 4 packages (west line screened/open x pond north/east) with checks, schedules, programme table |
| 6 Rank, select | `summary.json`, `traceability.json`, `policy-cards.json`, `plans/*.png` | scores, A1 trace of every element, our policy thresholds, plan drawings |

## Candidate counts
South garden, 240 000 random packings per (idea, west line) cell = 1 440 000 in total. A packing places table, fire pit, lounge seats, quiet nook, BBQ stand,
beds and pot one after another at the rule distances (table 1.2 m clear, pit 1.2 m from table, seats 1.2-1.5 m from the pit). Only 0.5-5.5 % pack at all: the space is that tight.

| cell | packed | no hard fail (structure) | planted variants tried | survivors |
|---|---|---|---|---|
| H / screened | 1 137 | 12 | 144 | 144 |
| O / screened | 1 313 | 11 | 132 | 50 |
| W / screened | 5 769 | 344 | 480 | 380 |
| H / open | 7 124 | 215 | 480 | 480 |
| O / open | 3 520 | 98 | 480 | 168 |
| W / open | 13 197 | 1 103 | 480 | 371 |

North court: 40 000 candidates without pond (450 distinct no-fail, 480 planted), 40 000 with pond (61 packed, 36 distinct, 360 planted).
East yard: 40 000 without pond (3 distinct structures), 40 000 with pond (3 479 packed, 90 distinct, 480 planted). Hard-fail reasons per cell are in `candidate-counts.json`
(largest: summer shade of the rooms on the DST clock, privacy, capacity, fire clear ground, geometry).

## Hard checks (A2): zero fails in every package shown
LDK `evaluate` (every `fail`; `LS-TREE-BUILDING` warn counted hard) plus ours (`policy-cards.json`, all POLICY, no published figure): privacy (remaining overlooking at most 30 % of today's
in a seated room, 25 % quiet corner), summer shade (evening cells sun-free 90 % on the DST clock; 50 % of the dining room under cover), mature spread vs space (shrubs, trees: sourced
minimum spread must stay in the garden and off the pit), toxicity (none within 2 m of a seat or herb bed), hydrozone incl. trees, geometry overlap. Result: 0 fail in all 12 packages;
2-5 warn, 8-9 not evaluated (below).

## Summer-evening clock decision (DST) and its source
Lead decision: judge "summer nights" on the local clock; the 17-20 DST-clock layer is primary. Source (secondary, not the gazette): Egypt reinstated daylight saving time by a 2023 law, clocks +60 min
from the last Friday of April to the last Thursday of October (UTC+3). Zawya "Egypt to apply daylight saving time from last Friday of April to October"; Ahram Online
"Egypt to reapply daylight-saving time annually" (english.ahram.org.eg/NewsContent/1/2/490952); timeanddate.com/news/time/dst-egypt-2023.html. Sources disagree on the law number (24 vs 34 of 2023); the gazette was not read. Status: secondary, to be confirmed.

## Concepts (all three: 4 dining seats + lounge seats + 2-seat quiet corner; flush gas pit, louvred non-combustible pergola over dining, lounge and quiet corner; terracotta pot with frangipani)
South garden is the only zone that differs between concepts; the north court and east yard candidates are the shared best of their zone (the per-concept pick did not diversify them: limitation).

| | H Hearth court | O Orchard room (recommended) | W Wall and floor |
|---|---|---|---|
| organising idea | two rooms side by side: dining west on the winter sun, fire lounge east, planting on the edges | a planted orchard corner (pomegranate and the quiet nook) at the south-west; lounge west, dining east | a seat wall along the rear fence carries the lounge seats; the floor stays open for standing |
| seats dining + lounge (+2 quiet) | 4 + 6 | 4 + 6 | 4 + 9 |
| standing at an event, furniture in place | 22.8 | 22.3 | 27.0 |
| south hard share (range 0.52-0.82) | 0.767 inside | 0.753 inside | 0.84 **above** |
| trees per 100 m2 (range 1.56-3.26) | 0.0 **below** | 1.88 inside | 0.0 **below** |
| privacy remaining, dining / lounge / quiet | 20 / 12 / 20 % | 15 / 20 / 3 % | 20 / 8 / 13 % |
| herb sun (east strip, needs 6 h) | 6.37 | 6.37 | 6.37 |
| score, west screened, pond east | 0.756 | **0.796** | 0.762 |
| score, west open, pond east | 0.795 | 0.823 | 0.792 |
| warns | 4 | 5 | 3 |
| plan, screened + pond east | `plans/H-screened-pond-east.png` | `plans/O-screened-pond-east.png` | `plans/W-screened-pond-east.png` |

Other plans: `plans/<idea>-<screened|open>-pond-<north|east>.png` (12 in all). I viewed H, O, W (screened, pond east) and W (screened, pond north). Each shows the three zones, client north up:
the south garden with the dining table and the pergola outlines, the fire pit with its 1.5 m seat ring, the BBQ stand, the herb strip, the quiet nook and the pot; the east yard with the flush pond between a path and
the fence in planted margins; the north court with a bench under a pergola. In H the lounge chairs sit clustered on one side of the fire, not around it: it passes the rules but would draw a composition criticism.

### Planting (schedule counts per concept are in the JSON; species, condition)
Pool = 24 viable or conditional species only. Used: bougainvillea, Petrea, Jasminum sambac (climbers on the screen, fences and pergola), Salvia leucantha and gazania (drifts), marjoram (herbs, only viable herb), pomegranate (O),
Pittosporum (north court, shade-tolerant, water need a GAP), zantedeschia (pond margins, toxic: kept 2 m from seats), Pontederia (pond, sun-limited), frangipani in a pot. Conditions carried: frost (Petrea, Jasminum, frangipani),
alkaline soil untested (bougainvillea, tipu), heat GAP, plant sun against the measured 21-June sun (most beds get 3-4 h: part-shade species only). Drawable (grade A/B asset): only frangipani; **everything else is not drawable yet**.
Rejected for the pool or a bed: oleander (highly toxic), lantana (toxic, invasive flag), olive (mature spread 4.6-7.6 m cannot fit: fails the spread check in every south position), jacaranda/tipu/poinciana (NHBC distance and spread),
all 54 species whose heat tolerance is a GAP (Fatsia, Strelitzia, Rhapis, Nymphaea, rosemary, thyme...). These would give the lush Japanese pond planting the brief wants; heat data from LDL unlocks them. Lush pond planting is therefore **thin** in every concept.

## Sister plot variants (open question)
Every concept exists with the west line screened (2.1 m screen with climbers on a 0.3-1.0 m bed) and open (low edge only). Screened privacy counts the sister groups; open leaves them out (the client's choice). Only 5.7-8 sister openings at 2-3 m+ behind the line
(needs screen top z up to 3.3) can never be screened at the boundary: overhead cover removes the rest. Screened H and O packed 10-12 structures in 240 000 tries; open allows more.

## Pond-location options
| | north court | east yard (in front of the dirty kitchen) |
|---|---|---|
| pond | 1.0-1.2 x 1.8 m = 1.98 m2, 1.1 m deep, 2 koi (28.7 in per m2 unaerated) | 4.0 x 1.0 m = 4.0 m2, 0.9 m deep, 4 koi |
| rooms that see it (LDS) | 1 (lounge) | 3 (dining, living, dirty kitchen) |
| sun 21 Jun / 21 Dec | 1.3 h / 0.1 h | 4.0 h / 0.2 h |
| planting | shade court, planting space left about 0 | fits between path and fence with 0.3 m margins |
| access | reached only through the lounge door | **no door from the dirty kitchen (LDS S8): view-only there** unless a door is added; dining and living doors open on it |
| score (packages) | H 0.70 / O 0.73 / W 0.70 | H 0.76 / O 0.80 / W 0.76 |
Recommendation: east yard. The north court then stays the quiet court (bench, shade planting).

## Recommendation
**Concept O, west line screened, pond in the east yard (0.796).** Reasons: the only concept with a tree inside the precedent range (1.88 per 100 m2) and hard share inside (0.753); the quiet corner is the least overlooked
(3 % of today's overlooking remaining); privacy under the pergolas 15-20 %; seats 10 (+2) with 22 standing at events, the same as H. Its cost: the lounge sits west of the dining (the winter-sun west half goes to the lounge and fire, not the table),
only one pomegranate gives canopy, the pomegranate dripline reaches 1.3 m2 of paving (`LS-ROOTZONE` warn), and capacity is the minimum 10. **W** seats 13 and holds 27 standing but its hard share is above range and the garden has no tree.
**H** is the simplest but has no tree and clumped lounge seating. The client answers the west-line and pond questions at the gate; the packages exist for every combination.

## What does not fit (programme)
20 seated needs 55.9 m2 > the 53.2 m2 garden; 10 seated plus 10 standing already takes 40.2 m2 (76 %). A wood fire needs 4.57 m clearance and cannot fit (gas specified). Every concept sets the dining to 4 seats (13.8 m2).
The east yard cannot hold seats or a herb bed (0.5 m2 at 6 h). Herbs: the east strip of the south garden only (3.4 m2 at 6 h).

## Rules not evaluated, and why
`LS-FIRE-PRODUCT` (no product chosen), `LS-POND-EDGE-LIGHT` (night lux comes from the lighting lane), `LS-POND-SHADE` (needs floating plants: Nymphaea/Nelumbo are heat-GAP, not in the pool), `LS-HYDROZONE`/`LDG-HYDRO` for beds with Pittosporum (water need GAP in LDL),
`LS-TREE-BUILDING`/`LS-ROOTZONE` for the potted frangipani (size GAP), `LS-SOIL-DEPTH` (no over-structure planting), steps (none; one level, z -3.0, no retaining walls). Pond specs (freeboard 150 mm, depth, rigid grille, shore 1:4, 600 mm sloped margin) and the pit cover (15 kN, lip 6 mm, opening 12 mm) are
**specifications to be certified by a pond or cover supplier**, not achievements. Advisory `AD-*` rules are not scored. Not evaluated at all: wind (station-level only; the pit is placed away from the east fence as a proxy), A3/A4 (LDC). Privacy credits for covers assume the pergola is opaque while closed
(LDK GAP-OVERLOOK-ABOVE); the same cover must be open for the winter sun, which is the main design tension of the brief.

## Test counts and diff
`python -m pytest tests/landscape -q` and `python scripts/lane_guard.py LDG` are recorded in the hand-back message. LDC (critics, `plan_png`) had not merged: ranking uses the LDK checks and our stated score
(weights in `pipeline.W`), plans use `plan_draft.py`; re-rank with `critique(layout)` once LDC lands.

## Open items
Merge LDC and re-rank; give each concept its own north court and east yard (the per-concept pick returned the same structure); lounge seats around the pit rather than clustered; heat data to unlock the lush plants; supplier certificates (cover, grille, pond);
a door from the dirty kitchen if the east pond is chosen; client answers (west line, pond, DST source confirmation).
