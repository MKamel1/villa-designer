# A+ interior package and render standard: villa (Egypt)

**Sources.** Book pages are printed pages, read through `knowledge.py`. The books are:
- IDRS: *Interior Design Reference + Specification*
- RID: *Residential Interior Design*
- TSI: *Time-Saver Interior* (US)
- NKBA: NKBA kitchen guidelines (free ed.) and the NKBA design-concepts summary, 4th ed.
- IES: *IES Handbook*, 10th ed.
- NEU: *Neufert* (1980)
- ADO: UK Approved Document O

Labels:
- web: a web source, listed at the end
- POLICY: a pipeline threshold I set and pre-registered. It is not a published value.
- UNVERIFIED: not checked against a primary source.

I did not consult NCIDQ, ASID or BIID; the phases below follow IDRS.

## A. Deliverables by phase (IDRS p.12 checklist; p.22–23)

1. **Brief**
   - Needs, goals and EGP budget cap.
   - Existing-conditions survey.
   - Consultants list.
2. **Concept**
   - Two or three concepts (POLICY), each with a named style statement and a mood board.
   - A palette with LRVs.
   - Material direction.
   - The client selects one concept and the sign-off is recorded.
3. **Schematic** (IDRS p.12)
   - Layouts with clearance overlays.
   - Preliminary reflected ceiling plan (RCP) and lighting intent.
   - Conceptual estimate approved against the cap.
4. **Design development**
   - Plans and RCP.
   - Interior elevations for every wall with joinery, tile or a feature.
   - Sample boards: proportional areas; floors, ceilings, walls, furniture, fabrics, hardware (IDRS p.62).
   - Draft FF&E list.
   - Art and accessory programme (IDRS p.22).
5. **Documentation**
   - Drawing set in this order (IDRS p.42): 100 demolition, 200 plans, 300 RCP, 400 finish plans, 500 furniture plans, 600 elevations, 700 sections, 800 millwork, 900 details.
   - Finish schedule: rows are rooms; columns are floor, base, walls and ceiling, plus remarks (RID p.41).
   - Elevations follow RID p.40: title, reference symbol keyed to the plan, scale, line-weight hierarchy, and countertops, frames and hardware shown.
   - Millwork drawings.
   - Specifications.
6. **Procurement and construction administration**
   - FF&E schedule columns (web: Programa, Fohlio, Nova Scotia template): tag, room, category, description, manufacturer, Egyptian supplier, SKU, finish or fabric code, W×D×H, qty, unit EGP, extended EGP, owner vs contract allocation, lead time, approval, PO status, alternate, revision, install notes.
   - Shop-drawing approvals and punch list (IDRS p.23).

## B. Interior acceptance criteria

| id | criterion | threshold | verified by | source |
|---|---|---|---|---|
| I1 | Concept coherence | One named concept; every room sheet cites it | Reviewer rubric (concept trace) | IDRS p.22 |
| I2 | Palette LRV | Every colour has an LRV (manufacturer value, or converted from Munsell value). Declared ceiling/wall/floor bands match the lighting-calc inputs. Bands are POLICY; IES uses 65/40/40 as a worked example. | Script: palette.json vs calc inputs | NEU p.17; IES p.26.20 |
| I3 | Material discipline | Per room: ≤3 woods/stones and ≤2 metals. 0 materials that are missing from the board. | Script: model materials vs board | POLICY |
| I4 | No clone heroes | Sofa, cushion set and pendant are not repeated across spaces unless the concept says so | Geometry and material hash | Audit class 5 |
| I5 | Real products | 100 % of FF&E rows have SKU, Egyptian supplier, EGP price no older than 90 days (POLICY), and lead time. Model dimensions are within ±10 mm of the product (POLICY). No "assumed envelope" rows. | Schema script, plus a 10 % URL spot-check | web FF&E |
| I6 | Budget | Total ≤ cap. Every lead time fits the programme float. Every row has an alternate. | Script | IDRS p.12 |
| I7 | Finishes coded | Every floor, base, wall face and ceiling resolves to a finish-schedule code; 0 uncoded | Script walks room boundaries | RID p.41; IDRS p.36 |
| I8 | Wet-floor slip | Shod wet floors: DIN 51130 R10/R11. Barefoot shower floors: DIN 51097 class B, or wet PTV ≥36. Steps into water: class C. | Rating field on the finish row | NKBA guidelines (bath floors slip-resistant); IDRS p.105; web HSA, NBS, V&B |
| I9 | Kitchen | Work aisle ≥1219 mm (multiple cooks; family). Walkway ≥914 mm. Sink landing 610 mm on one side and 457 mm on the other. Microwave landing ≥381 mm. | Existing clearance checks | NKBA pp.6, 13, 25; Guideline 7 |
| I10 | Bath planning | NKBA clear floor space at each fixture | Clearance script | NKBA summary p.1.5 (values UNVERIFIED, read the figure) |
| I11 | Furniture clearances | Dining: 813 mm for chair plus access; 965 mm for chair plus passage; 1219 mm from table to base cabinet. Circulation, bedside and seating are in existing checks. | Clearance script | TSI p.81 (US); other values UNVERIFIED |
| I12 | Storage | Bedroom closet 610 mm deep. Parents' closet ≥1524 mm long, others ≥914 mm. Hanging ≥1625 mm. Lowest shelf ≤1880 mm. | Script | TSI p.87 (US) |
| I13 | Lighting integration | Every task surface (island, desk, vanity, bedside) has a task source. Vanity light comes from the sides. Fixtures appear on both the RCP and the elevations. | Script cross-reference; reviewer | IDRS p.105 |
| I14 | Child safety | Bunk guard top ≥160 mm above the mattress (US: 130 mm). Bed-base gaps ≤75 mm. Looped cords have safety devices or are cordless. Tall storage is anchored (UNVERIFIED). | Geometry script; FF&E flags | EN 747-1 via a test report (secondary, UNVERIFIED); 16 CFR 1513.3; ADO p.14 |
| I15 | Elevations and joinery | 100 % of joinery and tiled walls have an elevation that meets RID conventions, plus a millwork sheet with materials and hardware | Sheet inventory; reviewer | RID p.40; IDRS p.42 |
| I16 | Boards | One board per major element, keyed to the finish schedule | Reviewer | IDRS p.62 |
| I17 | Styling | Every living space and bedroom has a rug, art or an object group, a plant (frangipani, terracotta pots), textiles and books. ≥0.5 props/m². | Tagged-prop count | POLICY; brief |
| I18 | Brief fit | Shade, colourful planting, a distinct identity for each daughter | Reviewer checklist | Client brief |

## C. Render standard

| id | criterion | threshold | critic / human | source |
|---|---|---|---|---|
| R1 | Lens | 24 mm by default. 24–35 mm allowed. 16–20 mm only with a written reason. | Metadata | Owner benchmark memory; web VDCI |
| R2 | Height | 1.2–1.6 m standing; about 1.1 m seated or bedroom | Metadata | web VDCI, D5 |
| R3 | Verticals | Level camera with shift. Pitch and vertical-edge deviation ≤0.5° (POLICY). No bent straight edges. | Line detection | web (tilt-shift practice); audit |
| R4 | Subject exposure | On the subject mask: clipped ≤1 %, crushed ≤2 % (POLICY) | Mask statistics | Audit rubric 3 |
| R5 | Context | Windows show a textured exterior. Neighbours are textured, not white or clay massing. No blank sky slab. | Critic | Audit rubric 4 |
| R6 | Texel density | One texel ≤ one pixel at subject distance: px/cm ≥ W_px / (2·d·tan(FOV/2)·100) | UV and camera script | Derived (sampling); web Maxon/Rebus are game-only references |
| R7 | Physical scale | Grain width, vein spacing and tile size within ±20 % (POLICY) of the supplier sample | Scale field; critic vs reference | Audit class 3 |
| R8 | Asset fidelity | Chord sagitta <1 px at render distance (derived). No card or disc foliage. No box bedding or clothing. | Mesh check; critic 0–2 | Audit class 1 |
| R9 | Contact | 0 objects floating with a gap >2 mm. 0 interpenetrations (POLICY). | BVH script | Audit rubric 2 |
| R10 | Composition | Near occluder ≤15 % of the frame. Subject not cropped. Empty wall ≤40 %. No edge bands, seams or haze. | Critic | Audit rubrics 7–8 |
| R11 | Truth and styling | The room's name matches what is shown. I17 density is visible. I4 holds. | Critic; human | Audit rubrics 10–11 |
| R12 | Colour | Mid-tone cast and wood/stone hue limits to be pre-registered, with a stricter cool limit | Script | Audit rubric 6 |
| R13 | Benchmark parity | Wins or ties the blind "more photographic" judgement | Critic, then human final gate | Audit rubric 12 |

**Critic rules.** The thresholds above are POLICY: pre-registered and never tuned to pass.
- Score each item 0–2.
- A score of 0 on a hero view is a hard fail.
- Two or more WARNs make the view a FAIL.
- Seed the critic with the audit's 27 false passes and report its recall on that seeded set before it gates anything.

**Side-by-side protocol**
1. For each room type, pick bedroom-overcast-door.png plus 2 published studio photographs of a similar programme. Use the same aspect ratio.
2. Fix exposure and grading before comparing.
3. Show the render and a reference at the same size, with left/right order randomised.
4. Ask the critic and a human, blind: which is the photograph, which has more credible materials, and which is better styled.
5. A+ means the human picks the render as CG no better than chance over ≥5 pairs (POLICY).
6. Log every verdict.

## D. Grade ladder

**Interior**
- **A+**: I1–I18 pass. Fully priced in EGP, within the cap, with lead times. Board, elevations, joinery and schedules are complete and coherent.
- **A**: At most 2 minor gaps, such as an alternate or an unpriced accessory. All safety and slip items pass.
- **B**: Coherent concept and clearances. ≥80 % of FF&E rows are real products. Some elevations or styling are missing.
- **C**: Good clearances, but products are envelopes. No schedules or boards, and a weak identity. This is the current state.
- **D**: Clearance or safety failures, or no concept.

**Renders**
- **A+**: R1–R13 pass, and the render is indistinguishable from the references in the blind test.
- **A**: Everything passes, but the render loses a close benchmark.
- **B**: At most one item at 1. Credible assets and materials.
- **C**: Readable, but low-poly, mis-scaled or empty in places. This is most of the current set.
- **D**: Crushed or clipped subject, occluders, or faceted or card assets dominate.
- **F**: The subject is unreadable.

**Web sources**
- [HSA](https://hsa.ie/eng/topics/slips_trips_falls/pedestrian_surfaces/measuring_slip_resistance)
- [NBS](https://www.thenbs.com/knowledge/pendulum-ramp-and-tortus-slip-resistance-test-methods-are-you-confused)
- [Villeroy & Boch](https://pro.villeroy-boch.com/fileadmin/user_upload/Fliesen/PDFs/TECH_INFO/TECH_INFO_Trittsicherheit_EN_villeroybochtiles.pdf)
- [Programa](https://programa.design/blog/ffe-schedule-template-guide)
- [Fohlio](https://www.fohlio.com/blog/ffe-101-how-to-build-the-ultimate-schedule)
- [Nova Scotia](https://novascotia.ca/dhw/ccs/policies/appendix-j-ff-and-e-detail-report.pdf)
- [16 CFR 1513.3](https://www.ecfr.gov/current/title-16/chapter-II/subchapter-C/part-1513/section-1513.3)
- [VDCI](https://vdci.edu/learn/interior-design/interior-camera-settings-eye-level)
- [D5](https://d5render.com/posts/camera-setting-tips-must-known-for-archviz)
- [Maxon](https://help.maxon.net/c4d/en-us/Content/html/Texel_Density.html)
