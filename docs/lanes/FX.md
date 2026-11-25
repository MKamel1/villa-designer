# FX: client furniture changes 2026-11-25 (items 1, 3, 4, 5 of `docs/decisions/client-changes-2026-11-25.md`)

Branch `lane/FX`. Tests: `tests/test_villa_render_fx.py` (10), `tests/compliance/test_checks.py` (waiver, 3 new), `tests/design/test_g1_fixes.py`,
`tests/test_villa_render_g1_geometry.py`.

## 1. Kids' room A: two loft beds, a desk under each (replaces `furn-ka-bunk`)

Room 3.475 x 3.78 m (clear 3.375 x 3.53), ceiling 2.70 m, window north (2.40 wide, sill 0.90, head 2.30), door south (0.90, hinge east, swings in).
Mattress **90 x 200** (the project's `bed_single`, client-approved 900 x 2000; kids smaller than queen 160 x 200; Time-Saver Standards for Interior
Design table 1: youth/bunk mattresses 30-36 in wide).

**Product basis:** IKEA SMASTAD loft bed frame with desk and storage, 504.540.36 (ikea.com/gb product page, read 2026-11-25): mattress 90 x 200, max
mattress thickness 20 cm, frame 205 x 104 cm, overall height 182, height under the loft bed 142, desk 148 x 60 x 73, minimum ceiling 240, not for children
under 6. Built as oak joinery to those dimensions (`villa_furnish3d.loft_parts`); the sleeping height is exact, the slat-base thickness (6 cm) and the 15 cm mattress
are ASSUMED (the page publishes neither).

| quantity | achieved | required / source |
|---|---|---|
| mattress top above the floor | 1.63 m (base 1.42 + 0.06 frame + 0.15 mattress) | product: under-height 1.42, overall 1.82 |
| headroom above the mattress top | 2.70 - 1.63 = **1.07 m** | product: minimum ceiling 2.40 (we have 2.70); the rail top is 0.88 m under the ceiling |
| guard rail above the mattress top | 1.82 - 1.63 = **0.19 m** (0.14 m with the 20 cm maximum mattress) | EN 747-1 (bunk and high beds) governs; its barrier, ladder and headroom figures are NOT in the held books and could not be confirmed (clause numbers only: 2024 ed. 4.1.4 barriers, 4.1.5 means of access), so no compliance claim: the product's own EN 747-1 certification must be checked at purchase |
| ladder | vertical, 0.40 m wide, 5 rungs at 0.28 m pitch to 1.40 m, on the room side at the foot, 0.46 m gap in the rail | product ladder; same EN 747-1 caveat |
| desk under the loft | 1.40 x 0.60 x 0.75 (product 148 x 60 x 73); desktop to the loft underside 1.42 - 0.75 = **0.67 m**; chair pulled in under the frame | seated-child head and knee height: no held-book child figure was found (Time-Saver has adult sitting-height definitions only): UNVERIFIED, stated as measured |
| passage between the lofts | 13.862 - 12.567 = **1.295 m** | >= 0.75 m (card `ukadm-bedroom-route-750`) |
| door swing | leaf swings in the quadrant x 12.765..13.665, y < -26.471; loft faces at 12.567 and 13.862: 0.198 / 0.197 m clear | no overlap |
| window | both lofts at the south ends; the window zone (north 0.30 m) is clear; `villa_furnish.check` windows = [] | existing window check |
| wardrobe | **1.36 m** where 1.5 m was asked (east wall, north of loft 2) | the loft frame (2.05) + wardrobe must fit 3.53 and the window check keeps 2.2 m pieces 0.30 m off the window wall; open item for the client |
| task light | under-loft iGuzzini Underscore15 ST49 basis (5 W/m, 680 lm/m, 2700 K) strip + the child's own ERCO Lucy 31327; target 400 lx (`ies-res-desk-400`) | see section 5 |

Bunk, its ladder and the two floor desks are removed (`ka-desk-1/2` keep their ids and moved under the lofts; chairs follow). Heads: loft 1 south, loft 2 north.

## 3. Stair: infill removed, recorded as a waiver

`stairs.party_flight_r8()` now builds `infill=False` and carries `INFILL_WAIVER`; the 16 mm nosing overlap and every guard are unchanged. The compliance
model reads the waiver (`model.spec_source` -> `compliance.model.Stair.infill_waiver`); `check_open_risers` keeps the row a **FAIL** but off the gate:

> LS2 stair open-riser gap (100 mm sphere): fail, achieved 116.5 mm, required 100 mm. WAIVED by client 2026-11-25 (waived by client 2026-11-25): 116.5 mm gap
> where 100 mm is required (ukadk-open-risers-dwelling). Consequence: the gap between treads returns to the full open gap and a 100 mm sphere passes it: a child
> under about 5 can get a foot, leg or head through. The stair is no longer best practice on this item. Reversible: the infill bar can be refitted
> (stairs.straight(infill=True)) if small children use the house.

Guards: `test_waived_infill_keeps_ls2_a_visible_fail_with_numbers`, `test_unwaived_open_stair_still_fails_the_gate`, `test_waiver_does_not_hide_a_pass_or_an_infilled_stair`,
`test_d1_loads_g1_fields_and_has_no_failed_or_warned_gate`, `test_waived_spec_has_no_infill_part`.

## 4. Kitchen: wall cupboards over the sink run (`furn-k-run`, 2010 mm)

What is on the wall (d1-elements, measured): no window; column 4 (`column-02`) east face x 11.537 (run starts 11.54); the dirty-kitchen door west jamb x 13.602 (run ends
13.55); a 250 x 600 beam at z 2.40..3.00 along the wall; two sink downlights 0.65 m off the wall at the ceiling (2.70); no hood (the hob is on the island); the
dirty kitchen holds the extractor. **Nothing blocks the cupboards.**

| quantity | achieved | source |
|---|---|---|
| underside above the worktop | 1.50 - 0.90 = **0.60 m** | >= 500 mm Neufert 1980 (Habitat 75 fig. 1, read from the page image); >= 457 mm Mitton & Nystuen 4th ed. p. 121 fig. 5.28; 18 in (457) ID Reference + Specification Book p. 240; client brief K-SPLASH 600 / K-UPPER 1500 (advisory, adopted) |
| top | **2.00 m** (units 0.50 m high) | Neufert 2000 reach line (same figure); under the beam soffit 2.40 and the ceiling 2.70 |
| depth | **0.30 m** | Neufert 300; Mitton 12 in = 305 mm |
| head clearance over the sink | cupboard front is 0.30 m from the wall, the user stands at the 0.60 m worktop edge: 0.30 m clear in plan; the tap (0.90 + 0.33 = 1.23 m) is 0.27 m under the underside | geometry |
| finish | walnut fronts (EGGER Dijon Walnut via `part_material`), 3 bays of 0.67 m, push-to-open (no handles, as the tall units) | kitchen finishes 2026-11-24 |
| task light | the cupboards shade the back of the worktop from the two sink downlights: direct lux on the sink plane 288 -> 270 (-6 %), minimum 127 -> 6 lx at the wall (own probe, ray test against the unit box). One under-cupboard strip (kind `UC`, iGuzzini Underscore15 ST49 basis, 680 lm/m) lifts the minimum to about 274 lx at full output | target 300 lx (`ies-res-kitchen-sink-300`) |

## 2. Dining chairs (task item 2)

Reference: client images 28 and 31 (private, not committed): curved-back upholstered armchairs in light grey with slim tapered walnut legs.
**Product:** Audo Copenhagen (Menu) Harbour Arm Chair, dining height, oak base, upholstered, SKU 71103-006971 (us.audocph.com, inches converted): W 584, D 574,
H 810, arm 676, **seat 478 mm**. **Model (look-alike, not the product):** "Curved Armchair" by SaretiX, Sketchfab, CC-BY-4.0, 33 520 faces (credit in the manifest;
library copy `assets/library/props/sf_dining_chair_curved_armchair`, tinted light grey fabric / mid grey shell / walnut legs by base-colour factors).

| axis | model | product | ratio |
|---|---|---|---|
| width | 0.790 | 0.584 | 1.35 |
| depth | 0.701 | 0.574 | 1.22 |
| height | 1.177 | 0.810 | 1.45 |
| seat height | 0.647 | 0.478 | 1.35 |

No uniform scale matches every axis; the model is scaled 0.739 to the product **seat height** (what governs fit at the table): W 584 (0 %), D 518 (-9.7 %), H 870 (+7.4 %).
Table top 750 - seat 478 = 272 mm; arm tops 676 are 74 mm under the table top (they clear the top, not an apron deeper than 74 mm). Pitch: 3 per long side at
1.8 / 3 = 0.60 m centres (chair 0.584 wide: 16 mm between chairs; the project's own 0.6 m per place policy, not a book figure).
