# A+ lighting and electrical package: villa, Egypt

Source keys: **IES** = IES Lighting Handbook 10th ed. (held). **SLL** = SLL Code for Lighting 2012 (held). **HELD** means the value was read on the page this session. **STD** means the standard is not held: the value comes from my professional knowledge of that clause, and a card for it needs the source page before it can gate approval. **UNVERIFIED** means I could not confirm it.

## A. Deliverables

**Lighting (IALD-style issue set)**
- **L-01 Design intent and criteria.** Layers per room (ambient, task, accent, decorative, exterior), the target card per task, scene intent, and colour and flicker policy.
- **L-02 Luminaire schedule.** Columns: type tag, manufacturer and code, lm, W, lm/W, CCT, CRI Ra and R9, SDCM, beam, UGR/cut-off, IP, IK, driver, dimming protocol, flicker data (Pst LM, SVM, % flicker), mounting and cut-out, emergency variant, qty, LDT file hash.
- **L-03 Reflected ceiling plans per level.** Dimensioned setting-out to room and joinery axes, cove and slot details, wall-washer setback.
- **L-04 Lighting/power coordination plans.** Every luminaire carries a circuit ID and a control-zone ID. Includes the exterior/landscape plan.
- **L-05 Calculation report per room and per exterior zone.** Grid definition, Em, Emin, Emax, U0, max:avg, Ez/Ecyl, vertical E at the vanity and mirror, UGR or a luminance check, MF, reflectances. One page per scene.
- **L-06 Controls intent.** Zone list, DALI-2/phase-cut addressing, scene table with levels, keypad engraving, presence/astronomical logic, night path.
- **L-07 Exterior and obtrusive-light report.** Ev on the boundary, I toward neighbours, ULR, curfew.
- **L-08 Emergency and night-safety layout.** Stair, basement egress, sunken-garden steps.
- **L-09 Daylight report.** sDA, ASE, DGP, shading operation.
- **L-10 Energy and maintenance.** W/m², LENI, MF basis, lamp/driver replacement.

**Electrical (consultant issue set)**
- **E-01 Design basis.** Supply (EEHC, 1 ph or 3 ph, 220/380 V, 50 Hz), earthing system, codes, ambient (45–50 °C roof), design assumptions.
- **E-02 Small-power layouts per level.** Sockets, switches, FCUs/isolators, AC and heater points, data, TV and SAT, with heights.
- **E-03 Lighting circuit layouts**, home-runs keyed to L-04.
- **E-04 Small-power and equipment schedule.**
- **E-05 Load schedule and maximum demand.** Connected kW, demand factors, kVA, phase balance, meter/contract size.
- **E-06 Cable schedule.** Ib, In, Iz with Ca/Cg/Ci, method, csa, ΔV %, Zs, disconnection time.
- **E-07 Panel (DB) schedules.** Ways, MCB/RCBO/RCD rating and curve, RCD type, SPD.
- **E-08 Single-line diagram.** Meter to MDB to sub-DBs, ratings, Icu/Icn, discrimination notes, IEC 61439 assembly declaration.
- **E-09 Earthing, bonding and lightning protection.** Electrode, RA target, main and supplementary bonding, LPS risk assessment (IEC 62305-2).
- **E-10 ELV.** Structured data/Wi-Fi APs, CCTV, intercom/gate, fire detection (smoke/heat per level, basement priority), with a containment plan.
- **E-11 Special locations.** Bathrooms (60364-7-701), pool/fountain (7-702, if present), garden/outdoor (7-714 luminaires; outdoor sockets on RCD).
- **E-12 Revit model.** Electrical fixtures, circuits, panels, and the read-back report.

## B1. Lighting A+ criteria

Residential applicability: EN 12464-1 covers workplaces, so it applies here only to the study/home office. For the home, IES Table 33.2 (residential) is primary and SLL is guidance. IES says residential uniformity ratios are "relatively broad", and IES requires that "minima and maxima must be achieved as intended", with ±10 % on averages (IES p. 33.25, HELD).

| id | criterion | threshold | verified by (reference case) | source |
|---|---|---|---|---|
| LA1 | Task illuminance, full scene | Avg within ±10 % of the card; Min/Max-gauged tasks met | Radiance grid per room; must reproduce the CIE 171:2006 cases within ±5 % | IES p. 33.25 (HELD); IES Table 33.2 cards |
| LA2 | Over-lighting cap | Task Eavg ≤ 1.5× target in the design scene (dining is currently 8×, the island 2.8×) | Same calc; fail if exceeded, no unsourced 3× | IES max:avg concept p. 33.25 (HELD); the 1.5× factor is **proposed and needs a carded basis** |
| LA3 | Uniformity | Report U0, max:avg and avg:min per IES Table 33.2 where cited; study U0 ≥ 0.6 (EN 12464-1 task) | Grid calc; grid spacing per EN 12464-1 formula | IES §33.3.4 (HELD); EN 12464-1 (STD) |
| LA4 | Glare: interior | Study UGR ≤ 19 (EN 12464-1 office writing). Elsewhere: no source > 3,000 cd/m² visible within 45° of the bed, sofa or dining sightlines unless shielded; downlight cut-off ≥ 30° | UGR by the CIE 117 tabular method; reproduce the CIE 190 worked example exactly and one manufacturer UGR table within ±1; luminance render at the 3 viewpoints | SLL §2.2.3.3, IES §10.9.2 (HELD, method); 3,000 cd/m² is a panel figure: **UNVERIFIED**, needs a card |
| LA5 | Modelling | Ez/Eh 0.3–0.6 at 1.2 m seated in living/dining; vanity vertical E on the face ≥ the card | Cylindrical-illuminance grid | SLL §13 cylindrical (HELD, definition); range per EN 12464-1 (STD) |
| LA6 | Colour consistency | One CCT per layer per room (2700 K interior, 2700/3000 K exterior); Ra ≥ 90, R9 ≥ 50; SDCM ≤ 3; schedule = bound product | Schedule lint against the LDT/product record | SLL §2.1.7 (HELD, principle); R9/SDCM thresholds are professional practice: **UNVERIFIED** |
| LA7 | Flicker | At the dimmed minimum: % flicker ≤ 0.08 × f (f ≥ 90 Hz) or SVM ≤ 0.4, Pst LM ≤ 1 | Driver datasheet field must be present and pass | SLL §2.1.8 "avoid flicker" (HELD); IEEE 1789-2015 factor 0.08 (web, boundaries UNVERIFIED); SVM/Pst (STD) |
| LA8 | Layering | Each habitable room has ≥ 2 independently switched layers; each card task has a dedicated task layer | Zone graph check | IES Ch. 33 (HELD); practice |
| LA9 | RCP setting-out | 100 % of ceiling luminaires on a declared axis/grid ±10 mm; spacing ≤ the luminaire SHR; wall-wash setback 0.6–1.0 m at equal pitch; no scallop on a curtain or timber panel | Golden-file test on 3 hand-designed rooms; visual QA | SLL spacing tables §12 (HELD, method) |
| LA10 | Controls and scenes | Scenes Day / Evening / Dinner / Film / Night / Off per living space; each card is met in its scene; Evening room:task ≤ 3:1; two-way switching at every stair and room with 2 doors; night path ≤ 5 lx at ≤ 10 % | Per-scene recalc; scene CSV round-trips to a DALI/Lutron import | Panel L4; values are proposals (**UNVERIFIED**) |
| LA11 | Exterior | Paths/steps meet carded IES/EN 12464-2 values; IP65+ in ground, IP67/68 buried, IK ≥ 08 walk-over; 2700 K | Exterior grid calc | IES exterior chapter (card needed); EN 12464-2 (STD) |
| LA12 | Obtrusive light (zone E3 suburb) | Boundary Ev ≤ 10 lx pre-curfew / 2 lx post; I ≤ 10,000/1,000 cd toward neighbours; ULR ≤ 0.15; facade Lb ≤ 10 cd/m² | Boundary vertical grid; ULR from LDT in the installed attitude | SLL Table 3.2, printed p. 90 (HELD) |
| LA13 | Emergency/night safety | Battery or maintained luminaires on the stair, basement route and garden steps; ≥ 1 lx on the escape-route centre line, ≥ 1 h; one per flight and change of direction | Point calc on the route with battery lumens | SLL §1.6.1/§7.4.2 (HELD, principle); EN 1838 1 lx / 1 h (STD); residential use is advisory |
| LA14 | Daylight | sDA300/50 % ≥ 55 % (preferred 75 %); ASE1000,250 ≤ 10 %; DGP < 0.40 for 95 % of occupied hours, with an operated-shading schedule | Reproduce the LM-83 reference within ±3 sDA points | IES LM-83-12 (STD; thresholds **UNVERIFIED**, web inconclusive); EN 17037 (STD). Brief: shade over sun, so report, don't push |
| LA15 | Energy | Interior LPD ≤ the carded value (target ≤ 5 W/m² **UNVERIFIED**; card it from the Egyptian energy code for residential buildings) | Sum W / area per room, from the schedule | IES p. 17.15 LPD method (HELD) |

## B2. Electrical A+ criteria

The governing code is the Egyptian Code for the design principles and execution conditions of electrical connections and installations in buildings (الكود المصري لأسس تصميم وشروط تنفيذ التوصيلات والتركيبات الكهربائية في المباني). It is multi-volume (vol. 1: design). Its code number and edition are **UNVERIFIED**; get them from HBRC. The EEHC/distribution-company connection rules and meter sizes are also **UNVERIFIED**. Until those are held, IEC 60364 is used, flagged as STD.

| id | criterion | threshold | verified by (reference case) | source |
|---|---|---|---|---|
| EA1 | Device provision | Carded minimum per room type: both sides of each bed, desk, TV wall (power, data, SAT), worktop spacing, dedicated appliances; switches at the latch side, 1.1–1.2 m | Rules engine; ≥ 95 % recall against 3 engineer-marked rooms | Egyptian code (UNVERIFIED); Metric Handbook (card needed) |
| EA2 | Bathroom zones | No socket in zones 0–2 (except SELV/shaver unit); every circuit serving the room on 30 mA RCD; supplementary bonding where required | Geometric zone test, including negative tests | IEC 60364-7-701 (STD) |
| EA3 | Circuits | Lighting ≤ 10 A and each control zone wholly on one circuit; sockets 16/20 A radials per room; dedicated circuits for AC, cooker, heater, washer, pump, EV, gate | Graph check: luminaire → 1 circuit | Panel E3; Egyptian code (UNVERIFIED) |
| EA4 | Max demand | Connected → demand using carded factors; result → kVA and meter | Reproduce the IET OSG Appendix A worked example ±2 % (guidance until the Egyptian table is held) | IET OSG (STD) |
| EA5 | Sizing | Ib ≤ In ≤ Iz × Ca·Cg·Ci, with Ca at 45–50 °C for roof runs | Match an IEC 60364-5-52 worked example and one commercial tool run within ±1 size step | IEC 60364-5-52 Annex B (STD) |
| EA6 | Voltage drop | ≤ 3 % lighting, ≤ 5 % other, measured from the origin | Same calc, mV/A/m from a carded table | IEC 60364-5-52 Annex G (STD) |
| EA7 | Fault protection | Zs gives disconnection ≤ 0.4 s (TN) / 0.2 s (TT) on final circuits ≤ 32 A; TT: RA·IΔn ≤ 50 V | Zs calc per circuit | IEC 60364-4-41 §411 (STD) |
| EA8 | RCD | 30 mA additional protection on sockets ≤ 32 A, bathrooms, outdoor, luminaires in reach; Type A minimum for electronic loads; outdoor/garden circuits on RCD | DB schedule lint | IEC 60364-4-41 §411.3.3 (STD); 7-714 (STD) |
| EA9 | Surge and lightning | Type 2 SPD at the MDB; LPS decision by IEC 62305-2 risk calc | Risk-calc record present | IEC 60364-5-534, IEC 62305-2 (STD) |
| EA10 | Earthing | Electrode RA target recorded; main bonding of water, gas, structure; test points | Schedule present; RA × IΔn check | IEC 60364-5-54 (STD) |
| EA11 | Phase balance | Phase loads within 10 % of the mean | Load schedule | practice (UNVERIFIED) |
| EA12 | Boards and SLD | Every circuit appears in the DB schedule and the SLD with rating, curve, RCD and cable; ≥ 20 % spare ways; IEC 61439-3 DBO | Second-tool cross-check that SLD = schedule = model | IEC 61439-3 (STD) |
| EA13 | Lighting coordination | Every luminaire in L-02 has a circuit; every control zone maps to circuits; circuit W = sum of luminaire W | Join check | panel E6 |
| EA14 | Revit read-back | Read-back circuit loads equal module loads within 1 W; panels and circuits count equal; no fixture unconnected | Revit API read-back report | ADR read-back practice |
| EA15 | ELV and fire | Data at each bedroom/study/TV; AP coverage; smoke detection on each level and in the stair, heat in the kitchen; CCTV at the gate and perimeter | Layout lint | BS 5839-6 grade D LD2 as guidance (STD) |

## C. Grade ladders

**Lighting**
- **A+:** All of LA1–LA15 pass. The reference cases reproduce. Every value has a card. The package L-01 to L-10 is issued.
- **A:** LA1–LA13 pass. Daylight or energy is incomplete but reported honestly.
- **B:** Interior calcs, glare, RCP and controls pass. Exterior and emergency are missing.
- **C:** Calibrated calcs, but over-lighting, glare, setting-out and controls are unaddressed. This is the current state, C+.
- **D:** Fixtures placed without calculated verification.

**Electrical**
- **A+:** EA1–EA15 pass. The Egyptian code is carded with page citations. The SLD, schedules and Revit agree.
- **A:** All pass on IEC/IET values, with the Egyptian-code cards pending and flagged.
- **B:** Devices, circuits, load and sizing are done. SLD, earthing or ELV are incomplete.
- **C:** Device layouts and a load schedule only.
- **D:** Device layouts only. **F:** No electrical design, which is the current state.
