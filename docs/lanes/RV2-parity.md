# RV2 parity: old Revit-era 2D outputs vs the Revit-free set (plan rows U08, U09, U14, U17, U21, U22; D15, D17, D18)

Status: **covered** (same information, new sheet), **improved** (covered and more), **gap** (not reproduced, reason and owner stated),
**n/a** (not a 2D drawing or retired). Old outputs were read from `out/villa` on the laptop in the first RV2 session (notes in
`RV2-plan.md`). Sheets: `out/documents/D1/` (see `docs/lanes/RV2-handback.md` for the sheet list and scene used).

| # | old output / content | new | status | note |
|---|---|---|---|---|
| U14-1 | `env-site-plan`: plot 28.93 x 19.13 m | A-100 site plan, plot drawn from the fence boxes, size printed | covered | plot line = fence outer face, ASSUMED (no survey) |
| U14-2 | street strip | A-100 street strip, width ASSUMED | covered | |
| U14-3 | neighbours with heights (12 m), sister (9 m) | A-100 neighbours labelled with height from the model (12.0 m), sister villa + apartment | covered | boxes are ASSUMED (brief) |
| U14-4 | sunken yard -1.80, fence top +2.20 | A-100 notes + gardens drawn; sections A-302 show the yard level | covered | |
| U14-5 | building footprint and rooms | A-100 footprint (GF solid, B outline), kept columns purple; rooms not named on the site plan | covered (rooms deliberately not repeated) | rooms are on A-101/A-102 |
| U14-6 | grid | A-100 draws the structural grid (A-B, 1-7) over the villa with bubbles, the same lines as the plans | covered | `test_site_plan_draws_the_grid` |
| U14-7 | true-north arrow, street facade bearing 290 | A-100 N arrow (client north) plus dashed true N, note 290 deg | covered | true N 70 deg clockwise of sheet-up |
| U14-8 | (new) set-back distances | A-100: N 3.99, E 3.24, S 5.96, W 8.17 m to the plot line | improved | EG3 input; GF envelope |
| U14-9 | ENV 3D views (JPG) | Blender renders (other lanes) | n/a | not 2D |
| U17-1 | NE yard wall dimensioned plan and section for client confirmation | A-143: plan crop (basement) and elevation at 1:25 with length 3740, thickness 250, height 1400, base -1.80, top -0.40 (Revit datum), from `ctx-yard-wall-ne`; QA reads the numbers from the PDF | covered (plan and elevation, no section) | position relative to the street fence is as modelled, no survey |
| U21-1 | A-001 cover, sheet index, legend | A-001 (index lists 20 sheets, legend extended: handing flag, kept columns, hatches) | improved | |
| U21-2 | A-101 / A-102 GA plans, tags, chains | A-101 carries B and GF side by side on A1 at 1:50, north up; A-102 retired | improved | chains, grid, level mark, tags kept; authored door handing and "?" flags added |
| U21-3 | A-201 / A-202 elevations | A-201 carries all four (E, N street, W, S) at 1:50 from Blender Line Art; A-202 retired | covered | line drawings, no material rendering |
| U21-4 | A-301 / A-302 sections | A-301 stair 1:50 cropped; A-302 garden 1:100 | covered | stair section is cropped as the plan agreed; A-302 is 1:100 (full length does not fit 1:50) |
| U21-5 | A-601 door, window, room schedules | A-601 (door schedule now has handing, hinge side, to-confirm) | improved | |
| U21-6 | roof / site sheet | A-100 | covered | |
| U21-7 | finish schedule | A-602 (codes from the model per room: floor, walls, ceiling, kind, height) | covered | layer thicknesses are not authored where the knowledge file has none |
| U21-8 | Revit schedule counts `not_evaluated` | SC1 now reads only the model; schedule rows == model, tags drawn == rows | improved | |
| U22-1 | furnished plans, both storeys, street at top | A-111 / A-112 (furniture boxes with type labels, dressing as outline) | covered | |
| U22-2 | rooms colour-coded | A-131 / A-132 colour-fill by occupancy with area legend | improved | separate sheets |
| U22-3 | orange doors, blue glazing colour coding | orange door leaf and swing, blue window/glazing on A-111 and A-131 with legend entries; the GA sheet stays black and white | covered | |
| U22-4 | green clearance zones | A-111 draws zones from the `catalogue.py` per-side clearances (front = local +Y); the legend says legacy, diagnostic, unverified | covered, diagnostic | pieces without a catalogue entry or with 0 mm draw nothing; zones do not certify a passage |
| U22-5 | purple kept columns | purple cross-hatch on every plan layer set that has `existing` | covered | |
| U22-6 | furniture schedule: item, room, type, size, height | A-603 (id, level, room, type, w, d, h, product) | covered | |
| U22-7 | furniture schedule 'why' column, fit-check PASS list, decisions/notes pages | A-111 prints the model's own `why` text per piece (44 of 52 fit on the sheet, the rest are in the model) and a furniture-by-room table | partly covered | the fit-check PASS list and decision records are not in the model; link from the sheet when structured |
| U22-8 | lighting plans with symbol legend (DL, DLN, ADJ, WW, PEN-GLOBE, PEN-LIN, SCONCE, STEP, COVE, BACK, UC, TOE, NL) and product codes | A-121 / A-122 with type tags and a legend of all 21 marks with manufacturer codes | covered | marks beyond the old 13 exist in the current design |
| U22-9 | fixture table with product and lm/W | A-604 (type, code, CCT, lm, W, lm/W, counts per level, total W) | covered | lm/W computed from the model's lumens and watts |
| U22-10 | lux table achieved vs required | A-121 prints required vs achieved lux (39 rows, Em or Emin by gauge, U0) from lane L6b's `villa-after-rows.json` (vendored snapshot of origin/lane/L6b 7f0a31a; the knowledge file is not on integ yet, switch the loader to `knowledge/lighting/` when it lands) | covered (numbers are L6b's, not recomputed here) | the 'what makes it beautiful' narrative is not reproduced |
| U22-11 | finishes pages | A-602 | covered | |
| U22-12 | ceiling height tags (not in old set) | A-121 / A-122 CH tags per room | improved | |
| U09-1 | option plans cropped with room tags (per option) | A-101 / A-102 for D1 | covered | |
| U09-2 | 3D cutaways, garden views | Blender renders | n/a | |
| U09-3 | D2 / D3 plans, `Compare-D1-D3.pdf` | not produced | gap | D2/D3 need their own model snapshots (plan row E9, later) |
| U08-1 | bedroom native plan, RCP | bedroom is a villa room: B/GF plans, A-121/A-122 RCP, A-141/A-142 callouts at 1:20 | covered | |
| U08-2 | two interior elevations of the bedroom, bedroom section | A-211: four interior elevations each for the parents' bedroom, kids bedroom A and B (1:25, drawn from the model: openings, furniture, clear widths, ceiling height); sections 3, 4, 5 on A-302 cut across these rooms | covered | no finish tone; other rooms not elevated (view spec only) |
| U08-3 | TextNote and revision cloud round trip | not produced | gap | MK lane (markups) and plan row C14 (later) |
| D15 | mass shapes hidden in views; plan north | A-101..A-132 north up, `sheetqa.orientation_violations` | guarded | 0 of ~1,400 pairs wrong; three wrong frames each trip it |
| D17 | section/elevation mirrored or direction wrong | `viewdraw.left_right`, `facade`, `sheetqa.view_violations` (stroke extent vs model footprint) | guarded | A-201/A-202 extents match the model to 0.00 m |
| D18 | missing tags, level lines, dark canvas | tag read-back from the PDF, level text on every plan/section/elevation, white background | guarded | counts 0 |

## Sheet renumbering (2026-11-21, composition fix)

Both levels now share one A1 sheet at 1:50: A-101 (GA), A-111 (furnished), A-121 (lighting), A-131 (colour-fill) replace the
A-101/102, A-111/112, A-121/122, A-131/132 pairs. A-201 carries all four elevations (A-202 retired). New: A-143 (NE yard wall),
A-211 (interior elevations). Rows above that quote old sheet numbers refer to the Revit-era sheets.
