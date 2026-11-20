# R5 consultant review: architecture + interior design (D1, r12 / furnish-d1 / finals-2026-10-15)

Evidence looked at: `designs-r12/D1-plan-GF` PNG, `furnish-d1/D1-furnished.pdf` (all 6 pages), renders v01, v02, v03, v05, `stairs-readback.json`, `rules.py`, `docs/guidance/rule-audit.md`, `knowledge/finish-build-ups.json`. The r12 PDFs could not be opened because poppler is missing, so I judged the plans from the PNG exports.

## Reviewer 1: Architect (Egypt practice)

**What is sound**
- The structure is respected. Kept columns are drawn on every sheet, and the furniture check reports "no piece on a kept column".
- The checks report achieved against required values (e.g. "1.219 m, min 1.219", the soffit "2.307 m; with a 0.100 lining 2.207 m"). That is how a consultant should report.
- The zoning works: living at -1.80 opening to a shaded sunken garden, bedrooms at +1.20, the dirty kitchen and laundry split from the open kitchen. This fits the shade-first brief and Egyptian family habits.
- Trade-offs are explained to the client, e.g. "a separate shower and double basin do not both fit in 2.32 x 2.18 m".

**Would be rejected**
1. **Wrong jurisdiction.** Every verified rule cites UK (AD K, AD M, AD G, NDSS) or US (IRC) documents. Nothing checks the Egyptian Unified Building Law 119/2008, its executive regulations, or the Egyptian fire code. A licensing authority would return this. Clause numbers must come from held texts.
2. **Basement as the main living floor.** Living, kitchen, dining and cinema are all at -1.80. Many Egyptian zoning authorities treat basement area as non-habitable or count it against the floor-area allowance. Lighting and ventilation of habitable rooms through the sunken courts also has to be shown. No check covers this, and the risk is not flagged.
3. **Stair and guard safety.** In v03 the stair has open risers with gaps clearly over 100 mm, and the void side is guarded by a single raking rail with no infill. This is unacceptable in a house with two young girls. No rule checks guard height, infill sphere or riser gaps. `stairs-readback.json` also shows treads 13 to 15 of an earlier flight clashing with an assumed 250x600 beam, so headroom is not proven against real structure.
4. **Egress and fire.** The upper floor is served by a single stair. The GF hall is a long dead-end corridor about 10 m or more, and no secondary escape route (window sizes, roof access) is shown. There is no fire separation at the basement cinema and store, and no smoke-detection layout.
5. **Ceiling heights.** The cinema desk soffit is 2.307 m, and Egyptian habitable-room heights are commonly larger. The rule DIM-01 uses an "unsourced generic 2.4 m".
6. **Climate.** The east bedrooms face the yard with full-height glazing. No shading device, glazing g-value or cross-ventilation path has been designed.
7. **Drawing standard.** Plans are screen-style (dark background), undimensioned, with no grids, title block, scale bar, levels or north point. These are not issuable sheets.

**Missing from the stage package**
- Schematic: site plan with setbacks and coverage/height calculation, sections, four elevations, area schedule.
- Design development: wall types, window and door schedules, stair details, roof plan, structural/MEP coordination drawings.
- Construction documents: dimensioned GA plans, wet-room enlargements, details, specification, and a permit set in Arabic with the stamp block.

**Grade: D+.** The method is credible (checked, honest, respects structure), but jurisdiction, life safety and documentation are not at a professional level yet.

## Reviewer 2: Senior interior designer

**What is sound**
- Furniture planning with clearance cards, a viewing-distance check (1.24 to 1.46 x screen), NKBA kitchen aisles, and a re-check with the dining table extended for 10. These ergonomic checks are better than many junior designers'.
- The "why" column on every item is excellent client communication.
- v05: a calm, warm-minimal bedroom with a slatted-oak headboard wall and bedside globes. The materials are coherent.

**Would be rejected**
1. **No style identity.** v02 mixes dark walnut library joinery, beige sofa, grey-green walls and orange zig-zag cushions repeated in every room. The palette has no story and shows nothing Egyptian or Mediterranean.
2. **No real products.** The schedule's own caption says "sizes are assumed product envelopes until products are chosen". There are no SKUs, suppliers, lead times, prices or budget.
3. **Ergonomics gaps.** A 1.70 m bunk under a ceiling with no headroom check. A 3.05 m island hob with no extraction proven (v01). A 430 mm family basin. A 0.35 m single bedside table. The kids' second wardrobe "does not fit" and is pushed to corridor storage that does not exist.
4. **Render realism.** v01 has faceted low-poly pendant globes, and v03 is underexposed. The ceiling bulkheads in v02 look like unresolved soffits, not designed coffers.
5. **No finish schedule.** `finish-build-ups.json` holds only thicknesses (plaster, tile bed, granite); there are no products, colours or slip ratings for wet floors.

**Missing:** concept and mood boards; a material board per room; an FF&E schedule (code, product, finish, quantity, unit cost, supplier, lead time); a finish schedule keyed to a finish plan; interior elevations of every wall with joinery; joinery shop-drawing details; window treatments; a styling and art schedule.

**Grade: C-.** The space planning is strong and partly verified. The design, specification and documentation are largely absent.

## Six capability changes per discipline (engineering tasks)

**Architecture**
1. **Egypt jurisdiction pack.** Input: held PDFs of Law 119/2008 and its executive regulations, plus the Egyptian fire code. Work: extract evidence cards (page, clause, value) into a `codes.py` pack, and attach rules for ceiling heights, light-well minimums, basement use, setbacks/coverage and stair dimensions. Accept: verify.py runs with `pack=EG`; each rule has a positive and a negative fixture; output never cites UK/US text where an EG card exists.
2. **Life-safety checker.** Input: the Revit read-back of stairs, guards and openings. Check riser/going/2R+G, guard height, a 100 mm sphere through infill and riser gaps, headroom against framing (using the existing clash data), travel distance, dead-end length, and escape-window size. Accept: the v03 stair FAILS and a code-compliant fixture PASSES.
3. **Planning envelope stage.** Input: `villa-site.yaml` with real plot and zoning data. Output: a coverage/FAR/height table with the basement counted per the EG pack. Accept: the gate blocks design if the scheme exceeds the allowance.
4. **Climate and shading design.** Per façade, compute a sun-path mask against Egypt's latitude, select a device (louvre, mashrabiya, overhang depth), and report hours of direct sun on glazing. Accept: east bedrooms under N hours/day in summer, with the device modelled.
5. **Issuable drawing set.** Revit sheet automation: dimensions, grids, levels, tags, title block, scale, north point, 2 sections and 4 elevations, door/window schedules, white background, bilingual labels. Accept: a sheet-QA script counts zero undimensioned walls and zero untagged openings.
6. **Coordination gate.** Run Revit clash detection between architecture, structure and assumed MEP zones at every round. Accept: no tread or opening intersects framing, and the r3 flight is caught as a regression.

**Interior**
1. **Style engine.** Input: the client interview plus reference images. Output: a named concept, a 5 to 7 colour palette with LRV, 6 to 8 materials, and banned items. Every render and FF&E item is validated against the palette (colour distance). Accept: the orange zig-zag cushion is rejected.
2. **Product library with Egyptian sourcing.** Data: real SKUs from local suppliers and international brands available in Egypt, with dimensions, finish, EGP price, lead time and URL. Placement binds to a SKU bounding box, not an envelope. Accept: 100 % of the schedule has a SKU and price, and the budget total is within the client cap.
3. **FF&E and finish schedules.** Generate an xlsx/PDF keyed to finish plans: floor, wall and ceiling per room, slip rating in wet areas, and a door hardware set. Accept: every room face has a finish code, and wet floors meet the slip threshold from a held source.
4. **Interior elevations and joinery details.** Auto-generate elevations for every wall with joinery, MEP points and tile setting-out. Accept: one sheet per room with dimensions, and a joinery cut list consistent with the model.
5. **Ergonomics extensions.** Add bunk headroom, hob extraction, basin minimums, bedside widths and storage linear-metre targets per occupant, each from cited sources. Accept: the current D1 bunk/hob/storage findings are raised.
6. **Board generator plus render QA for style.** Produce a mood board and a per-room material board from library textures, and add render QA for faceted geometry (normal discontinuity) and exposure band. Accept: v01 pendants and v03 exposure are flagged automatically.
