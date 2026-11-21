# A+ architectural package: villa, Egypt (definition to judge the pipeline against)

**Source keys.** **ER** = Executive Regulations of Building Law 119/2008 (Decree 144/2009 as amended). The text read is the *unofficial* Andersen English translation (eg.andersen.com, read 2026-11-20). Before any ER row gates approval, check it against the Arabic Gazette text. **ADK** = UK Approved Document K 2013 (page read). **MH** = Metric Handbook (page read). **NF** = Neufert, 1980 edition held (page read). Rows marked "UNVERIFIED" have no source read and must not gate anything yet.

## A. Deliverables per stage

The stage names follow RIBA PoW 2020 (2 Concept, 3 Spatial coordination, 4 Technical) and AIA B101 (SD/DD/CD). **UNVERIFIED: only secondary summaries were read; the exact output lists need the RIBA Overview and the B101 text.** Sheet numbers follow the US NCS (A = architecture; type digit 0 general, 1 plans, 2 elevations, 3 sections, per secondary sources; digits 4–9 UNVERIFIED). Scales follow MH p.1-3, Table III: location 1:500/1:200, general 1:200–1:50, assembly and component 1:20–1:5.

| Stage | Deliverables (required contents) |
|---|---|
| 0 Brief/site | Statement of site validity and building requirements (ER Art.110). Survey: plot, levels, neighbours, the apartment above, trees, utilities. Soil report. Room-data brief. |
| 2 Concept | Parti diagrams; sun-path and shade study; massing in its context; A-100 site plan 1:200 showing the envelope (coverage, height, setbacks taken from the validity statement); plans and 2 sections at 1:100; area schedule against the brief. |
| 3 Schematic/DD | A-001 cover, sheet index, legend. A-100 site and roof 1:200. A-101…103 GA plans (−1.80 / GF / L1) 1:100→1:50 with grids, levels, room names and areas. A-201/202 all four elevations 1:100. A-301/302 two sections (one through the stair, one through the sunken garden) 1:50. Structural grid agreed with the engineer. Outline specification. Fire/egress strategy diagram. Daylight and shading report. |
| Permit | Per ER Art.112: application form, ownership deeds, ID, works-value form, Certificate of Suitability of Works with the validity statement, **three copies of drawings approved by the engineer**, the insurance policy plus structural drawings, soil study and calculation note where Law Art.46 applies. Every sheet carries the ER Art.111 data. Arabic drawings and a stamp: **UNVERIFIED — needs source.** |
| 4 CD | Dimensioned GA plans 1:50. RCP A-401…. Enlarged stair A-501 1:20 and wet rooms 1:20. Wall sections 1:20. Details 1:5. Door/window, finish and area schedules. Specification. Clash-free model coordinated with structural and MEP. |

## B. Acceptance criteria

Gate = the Egyptian legal minimum. A+ = the stricter target, where a better source exists. V: auto = script on the model or sheets; meas = measured on the drawing or model; rev = named reviewer step.

| id | criterion | threshold | V | source |
|---|---|---|---|---|
| EG1 | Fire-code applicability test | Top floor ≤16 m above street; every storey incl. basement ≤400 m²; basement ≤3 m below street. If any one fails, the full Egyptian fire code applies (**UNVERIFIED content**). | auto | ER Art.106 |
| EG2 | Basement classification | GF finished floor ≤1.5 m above pavement | meas | ER definitions |
| EG3 | Planning envelope | Coverage, height, setbacks and projections match the validity statement; the site plan shows all four façades with their set-back distances | auto vs statement | ER Art.92, 110, 117; licence form |
| EG4 | Clear floor height | ≥2.70 m; ≥2.30 m allowed in halls, corridors and baths, and on slopes ≤25 % of a room | auto | ER Art.93 |
| EG5 | Room minimums | Habitable 7.5 m² / 2.5 m; kitchen 3.0 / 1.5; bath 1.5 / 1.2; WC 0.8 / 0.8 | auto | ER Art.94 |
| EG6 | Door widths | Rooms ≥80 cm; kitchen, bath, WC ≥70 cm | auto | ER Art.97 |
| EG7 | Natural light and air | Openings onto a road or courtyard ≥8 % of floor area (habitable), ≥10 % (kitchen, bath, stair); each opening ≥0.5 m² (habitable) or ≥0.25 m² (utility). Applies to **basement rooms too**. | auto | ER Art.96 |
| EG8 | Sunken gardens as legal courtyards | Habitable: min dimension ≥max(0.25H, 3 m), internal area ≥max(9 m², (H/4)²). Utility: 2.5 m. Rainwater drainage provided. | auto | ER Art.98 |
| EG9 | Window sill | ≥0.9 m, or a guard ≥0.9 m | auto | ER Art.96 |
| LS1 | Stair geometry | Width ≥110 cm; tread ≥27 cm; riser ≤17 cm; ≤14 risers per flight, then a landing ≥4 treads; headroom ≥2.1 m. A+ also requires ADK: 2R+G rule, uniform steps (1.5), pitch ≤42°. | auto | ER Art.100; ADK p.5–6 |
| LS2 | Open risers / gaps | No opening passes a 100 mm sphere (ER: objects ≥10 cm); open risers only with ≥16 mm tread overlap. A+: closed risers. | auto (sphere test) | ADK 1.9 p.6, 1.6; ER Art.103 |
| LS3 | Guards | Stair, landing and internal edge ≥900 mm; balcony, roof and **sunken-garden edge** ≥1100 mm (ADK). ER minimum 0.9 m. Not climbable (no horizontal rails). | auto | ADK Diag 3.1 p.24, 3.1(a) p.23; ER Art.100/103 |
| LS4 | Door onto a flight | ≥1 m clear from the nosing | auto | ER Art.96 |
| LS5 | Escape | No inner habitable rooms. Every room has an escape route or an escape window ≥0.33 m², ≥450×450, sill ≤1100. Remedy for the dead-end hall plus single stair: a protected stair or a second exit from the −1.80 level. | auto + rev | MH p.11-17 (UK guidance, applicability noted) |
| LS6 | Smoke detection | Interlinked alarms in the hall at each level and in the kitchen. **UNVERIFIED — needs source** (MH 11-28 snippet only). | auto | — |
| LS7 | Fire separation basement/GF | **UNVERIFIED — needs source** (Egyptian fire code not read) | rev | — |
| AC1 | Accessibility | Comply with the Egyptian Code for persons with disabilities. Content **UNVERIFIED**; until read, an accessible GF WC and step-free entry are A+ targets. | rev | ER Art.108 bis |
| CL1 | Shading | Every west, south and east opening of a habitable room has external shade tested on a sun path (solar-angle cut-off documented). The client prefers shade, so the score is shade hours, not daylight. Numeric target **UNVERIFIED**. | auto (sun-path) | constr.-illustr. p.1.22 (snippet only); Lechner ch.8 (not read) |
| CL2 | Daylight reported | Average daylight factor reported per room. 2 % reads as "gloomy" and >5 % as "generous" (descriptive bands only, not to be maximised). | auto | MH p.9-7 |
| ST1 | Structure coordinated | Gridlines on every plan; columns and beams match the structural model; zero hard clashes (arch/struct/MEP) | auto (clash run) | ER Art.112 (structural set) |
| DS1 | Sheet data | Project, owner, address; engineer, Syndicate no.; scale; date; drawing title and no.; revision log with location; issue sequence | auto (title-block parse) | ER Art.111; NF p.3 |
| DS2 | Graphics | White background; north point on every plan; graphic scale; levels on plans and sections; grids; room tags with name and area; door/window tags; section and elevation callouts resolve to sheets; ≥3 line weights (cut > projection > beyond) | auto + rev | NF p.3 (north); line weights UNVERIFIED |
| DS3 | Dimensions | Overall, grid and opening chains on every exterior wall; key internal dimensions; nothing left undimensioned | auto | — (professional norm, UNVERIFIED) |
| DS4 | Bilingual | Arabic and English titles and room names | rev | UNVERIFIED for drawings (Art.90 covers only signs) |
| SC1 | Schedules | Door, window, room-area and room-finish schedules generated from the model; counts equal the tags | auto | B101 / RIBA (UNVERIFIED) |
| BM1 | Model is the source | Drawings are generated from the Revit model; round-trip without loss; LOD 200 at concept, 300 at DD/permit, 350 at CD (BIMForum LOD Spec, UNVERIFIED) | auto | — |

## C. Grade ladder

- **A+**: All gates pass with sources. A+ targets are met. Coordinated, dimensioned, bilingual set at every stage. Design rubric (D) ≥16/20.
- **A**: All gates pass. ≤3 A+ targets missed, each documented. Rubric ≥12.
- **B**: Gates pass. The set is incomplete (e.g. no CD details, or schedules not generated). Rubric ≥8.
- **C**: One or more gates are unverified or failed but fixable without re-planning. The drawing set is not submittable.
- **D**: A life-safety gate fails (stair, guard, escape, basement light) or the envelope is exceeded. Not buildable or permittable.

## D. Design-quality rubric

Each item is scored 0 / 1 / 2 by a reviewer, with evidence cited. 10 items, total 20.

1. **Parti clarity**: 0 no organising idea; 1 an idea is stated but the plans contradict it; 2 one diagram explains the plan, section and garden (Ching, *Form, Space & Order*).
2. **Section as generator**: 2 means the −1.80 level and the sunken gardens read as one designed section, with light and views shown.
3. **Proportion and order**: 2 means openings, grids and heights follow a stated system (module or ratio) that is visible in the elevations.
4. **Light and shade**: 2 means every habitable room has controlled, shaded daylight with an intended light quality (client brief: shade).
5. **Threshold sequence**: 2 means street → gate → court → entry → hall form a deliberate privacy gradient, with compression and release.
6. **Privacy and overlooking**: 2 means no window is overlooked by the apartment above or the neighbours without screening.
7. **Climate fit**: 2 means orientation, mass, cross-ventilation and courtyards work together (Lechner, passive strategies).
8. **Material honesty and palette**: 2 means few materials, used for what they do, with junctions detailed.
9. **Circulation economy**: 2 means circulation is ≤15 % of the gross area and no corridor is dead space. The 15 % threshold is UNVERIFIED and is a reviewer norm.
10. **Coherence of the set**: 2 means plans, sections, elevations and renders agree; a reviewer finds no contradiction in 15 minutes.
