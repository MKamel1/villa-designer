# RV2 hand-back (Revit-free 2D drawings, 2026-11-21)

Generate: `python -m archpipe.documents --out out/documents/D1 --scene <scene.json> --previews src/archpipe/documents/samples`
(`--scene` enables the Line Art sections and elevations; Blender 4.5 at `~/opt/blender/blender`). `out/` is not committed.

## Sheets (17; combined `out/documents/D1/D1-set.pdf` with bookmarks)

Composition rule: paper = the smallest ISO A size on which the views fit at a standard scale (1:20, 1:25 interiors, 1:50, 1:100) and fill the
drawing area (>= 60 %); text >= 1.8 mm cap height (room names >= 2.5 mm). Both floor plans share one sheet.
A-001 cover (A3) | A-100 site plan 1:100 A2 (grid, legend, set-back table, notes) | A-101 GA plans B + GF 1:50 A1 | A-111 furnished (clearance
zones, door/window colours, furniture by room, design-model rationale) | A-121 reflected ceiling and lighting + lux table | A-131 colour-fill + room-area
table | A-141 stair 1:20 | A-142 wet rooms 1:20 | A-143 NE yard wall plan and elevation 1:25 A3 | A-201 four elevations 1:50 A1 | A-211 interior
elevations (parents, kids A, kids B) 1:25 A1 | A-301 stair section 1:20 A1 with riser infill bars, glass guards, understair cupboard | A-302 garden section
+ cross-sections 3, 4, 5 at 1:50 A1 | A-601 door/window/room, A-602 finish, A-603 furniture, A-604 luminaire schedules.
Renumbering from the first hand-back: A-102/112/122/132 and A-202 retired (merged into the sheet above them); A-143 and A-211 are new.

## Fix 1 composition (before -> after, fill = share of 40 mm cells with ink, from the PDFs)

| sheet | before | after |
|---|---|---|
| furnished A-111 + A-112 (now A-111) | 0.22 / 0.16 | 0.66 |
| GA A-101 + A-102 (now A-101) | 0.38 / 0.34 | 0.76 |
| lighting A-121 + A-122 (now A-121) | 0.26 / 0.19 | 0.62 |
| colour-fill A-131 + A-132 (now A-131) | 0.23 / 0.16 | 0.61 |
| A-100 site | 0.34 | 0.77 |
| A-201 elevations (A-202 before) | 0.28 / 0.44 | 0.90 |
| A-301 stair section | 0.30 | 0.91 |
| A-302 sections | 0.28 | 0.75 |
| A-141 / A-142 callouts | 0.83 / 0.66 | 0.85 / 0.66 |

Text: smallest printed cap height 0.72 mm (furniture labels), tags 0.87-1.0, room names 1.34 mm -> all >= 1.80 mm, room names 2.57 mm (10 pt), enforced by
`standard.TEXT_MIN_PT` in `_Sheet.text`. Schedule sheets are exempt from the fill rule (tables), not from the text rule.
New QA (`sheetqa.fill_ratio`, `text_violations`, results `DS2 drawing-area fill` and `DS2 print text height` per sheet): on copies of the old A-112, A-301,
A-201 (`tests/drawings2d/fixtures/old-*.pdf`) fill is 0.10-0.30 against 0.60 and 49 (A-301) to 127 (A-112) text spans are below the minimum, so both fail; a stray legend in a
far corner scores < 0.05 (a bounding box would have passed). All 17 sheets pass; `sheet-qa.json` totals are 0 (orientation, tags, levels, chains, handing,
views, text, fill, stair_detail, interior, yardwall); 1 model finding (door rotation, below).

## Fix 2 Arabic

Cause: our own Presentation-Forms shaping and reversal were applied on top of matplotlib 3.11's libraqm shaping (double processing). Now logical text with
`font.family = [DejaVu Sans, Noto Naskh Arabic]`; the shaping module is deleted. Read on the produced PNGs (titles, room names, banner, cover index): joined and
right-to-left. Test `test_arabic_render.py`: ink overlap with an independent PIL/libraqm layout 0.87-0.90 for three sheet strings; the OLD path scores
0.13-0.22 and reversed text 0.18-0.22 (both rejected, thresholds 0.7 / 0.45). Noto Naskh Arabic must be installed on the machine that builds the set
(on Windows DejaVu Sans carries the Arabic glyphs, shaping needs matplotlib >= 3.10 with raqm).

## Fix 3 stair detail (A-301, 1:20)

`drawings2d/stairdetail.py`, from the model: 15 horizontal flat bars (40 x 10 mm, cut), the glazed open-side guard (900) and the GF void guard (1100) beyond the plane,
the understair cupboard (end wall and toe panel cut, stepped side wall and 600 x 950 door beyond). New QA `stair_detail_violations` counts them in the PDF by
fill colour and printed bar size: 15/2/3 found, and 15/2/3 missing on the old A-301 (`test_stair_detail_missing_on_the_old_section`).

## Fix 4 parity (see RV2-parity.md for each row)

Closed: grid on the site plan; A-143 dimensioned NE yard wall; door/window colour coding with legend; furniture clearance zones (catalogue values, diagnostic);
lux table on A-121 (L6b `villa-after-rows.json`, vendored snapshot of 7f0a31a because it is not on integ yet); furniture 'why' text; interior elevations
(parents, kids A, kids B) as A-211. Left: furniture fit-check PASS list and decision pages (not in the model); 'what makes it beautiful' lighting narrative; D2/D3 and
Compare sheet (need model snapshots); revision clouds (C14) and sun overlays (C16); yard wall section; finish tone on elevations and interior elevations.

## Fix 5 door-B-cinema-store-ramp

Drawing code already follows the host wall (lesson RV2-01); the report `opening_axis_findings` still lists `door-B-cinema-store-ramp`
(rotation_deg 0 on a wall along y): for lane M to correct in the model data (not edited here).

## Fix 6 scene

integ/aplus does not build a scene yet (lane RA not merged), so sections and elevations still use scene sha256 `28bc8df3...54dacc` (printed on each sheet
and in `sheetset.json`). /tmp/ra-scene/scene.json (sha c523d524...) belongs to lane RA with bypass receipts, so it was not used. Re-run with the new scene when RA lands.

## Decisions (no human was available)

1. A1 at 1:50 for plans (two levels side by side) rather than 1:75 on A2 (not a standard scale); the left column holds the legend and a table per variant.
2. Fill measured as cell occupancy (40 mm cells), threshold 0.60; table sheets exempt; A-111 reached 0.66 only after the rationale list was added.
3. Text standard: cap height = 0.729 x font size; minimum 1.8 mm, room names 2.5 mm (house policy, `POLICY` source card).
4. Sections 3, 4, 5 are new (cut at model x = 13.2, 20.6, 6.4) to fill A-302 and show the bedrooms; section 2 window cropped to the extent of its cut.
5. Clearance zones use the legacy catalogue values and say so; no passage is certified.

## Known gaps / notes

`scripts/verify.py` still fails to import on this base (`archpipe.model` has no `SpecError`): not touched. `python -m pytest tests/drawings2d tests/documents`: 57 pass.
