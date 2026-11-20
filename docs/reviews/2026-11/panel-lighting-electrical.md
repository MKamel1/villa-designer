# R5: Lighting and electrical review (read-only, current main)

## Lighting: grade C+ (measurement instruments B+, design package D)

**What is strong, and better than most practices:**
- The IES/LDT reader, maintained illuminance (MF 0.8), and an honest "direct only" scope with U0 deliberately withheld (`lighting.py:36-60`, ADR-0009).
- The Cycles photometric calibration is derived from closed-form cases (`IES_POINT_POWER = 4πC`, ADR-0010). The render works as a light meter: `render-d1/lighting-measurements.json` records 24 task points with direct and total (inter-reflected) lux, 256 samples, and real occlusion.
- Radiance daylight is validated against the closed-form box case (3.05 vs 2.90 % DF), checked for convergence, and has annual DA300/UDI results through `dctimestep` (`daylight/summary-r12.json`).
- Targets come from IES HB10 Table 33.2 (25–65 column) and are traced to cards. Unknown values are labelled ASSUMED (the 3.0× excess ratio, generic photometry). `lighting-rebalance-report.md` found a real sensor-occlusion defect (17 of 25 sensors) and did not tune the result to pass.

**Design faults, from the renders and the data:**
1. **Over-lit task planes.** The dining-table centre gets 797 lx against a 100 lx target (8×). Island prep gets about 1,419 lx against 500 lx. The rule only reports ratios above 3× and has no source for that limit. Nothing limits how bright a task can get, and there is no dimmed-scene calculation.
2. **Glare is not assessed at all.** The code has no UGR, DGP, evalglare or luminance-ratio check. In v05 two bare opal globes sit at pillow height in a reclining person's view. In v09 three 800 lm opal globes are the brightest thing in the frame. Opal decorative sources need a luminance cap (about 3,000 cd/m² or less) or shielding.
3. **The ceilings show "downlight acne".** v09 has about 20 randomly spaced points with no alignment to the furniture, the coves or each other. There is no reflected ceiling plan setting-out logic (axes, alignment to joinery, spacing-to-height ratio).
4. **Scallops land on curtains and timber panels** (v05, v09). Wall-washer setback and pitch are not designed. WW is a substitute: a 33° flood at 0.3 m from the wall (`fixture_record.py:94`).
5. **There is no exterior lighting.** No fixture kind exists for it: no landscape uplights, façade, path bollards, pool, gate, or IP/IK ratings. v07 "terrace dusk" shows an unlit frangipani in grey twilight.
6. **There are no controls.** The model has no circuits, dimming protocol (DALI-2, phase-cut or 0–10 V), scenes, keypads, presence sensing or night-path logic. The products are specified "phase-cut", but nothing groups them.
7. **There is no emergency or night-safety intent.** A battery or maintained stair and exit path, which a professional would recommend even though not mandated, is missing. Stair STEP markers at 60 lm are not checked for tread illuminance.
8. **CCT is uneven.** Spec DLN is 3000 K and the bound product is 2700 K (it is documented, but the schedule still lists the spec). Vanity sconces are 3000 K and coves 2700 K. There is no SDCM, R9 or TM-30 requirement, and no flicker requirement (IEEE 1789 / SVM).
9. **Daylight lacks ASE1000,250 and glare.** sDA is a single-point DA300 per sensor, with no 50 %-of-hours area aggregation (as in LM-83). Shading is not operated, so there is no blind schedule. Points are a 9-stamp set, not 8,760 h for DGP.

**What is missing compared with a professional package:** a luminaire schedule with type tags, wattage, driver, dimming, IP and mounting detail; a calc report per room (Em, U0, Emin, UGR/limits, cylindrical illuminance Ez in living and dining, vertical illuminance at the vanity); a controls intent document (zones, DALI addresses, scene table, keypad engraving); a reflected ceiling plan with dimensions; aiming schedules for ADJ; LENI or W/m²; and maintenance.

## Electrical: grade F (absent)

Electrical design is absent. The only trace is the word "sockets" in `5-systems.md:14`, and line 55 lists electrical as missing consultant scope. `Luminaire.watts` exists but is not totalled.

**Minimum viable module, `archpipe.electrical`:**
- **Inputs:** the room list and use, furniture layout (bed, desk, TV wall and worktop spans from `villa_furnish`), the lighting fixture list with W, the equipment list (split AC per room, water heaters, oven, hob, washer, pump, EV charger, gate), and the supply (220/380 V 50 Hz, 1 ph or 3 ph, earthing system confirmed with the utility, often TT).
- **Placement rules (carded):**
  - Sockets per room type: each side of a bed, a desk cluster, a TV-wall cluster with data and SAT, worktop spacing, dedicated appliances, and fused spurs.
  - Switches by the door on the latch side at a 1.1–1.2 m height, with two-way switching at the stair and the bedroom-to-bed position.
  - Data points in each bedroom and the study, plus Wi-Fi access points.
  - Bathroom zones per IEC 60364-7-701, with clearances from the fixed basin, shower and bath.
- **Circuits:**
  - Lighting at 10 A with 18 or fewer points, grouped by control zone and fed from the lighting design's zone IDs.
  - Sockets on 16 A radials grouped per room.
  - Dedicated circuits for the AC, cooker, heater, washer and pump.
  - Phase balancing for 3-phase supplies.
- **Load and demand:** connected load to maximum demand using carded demand factors (Egyptian code tables when sourced; otherwise IET OSG Appendix A, flagged as guidance). The output gives the contracted kVA and the meter size.
- **Sizing:** Ib ≤ In ≤ Iz with corrections Ca, Cg and Ci (IEC 60364-5-52, Annex B tables, 45–50 °C ambient for roof runs). Breaker curve; disconnection time via Zs; 30 mA RCD/RCBO on sockets ≤32 A, bathrooms and outdoors (60364-4-41 §411.3.3); Type A for appliances; SPD (60364-5-534).
- **Voltage drop:** following Annex G (3 % lighting, 5 % other from the origin).
- **Earthing:** an earth electrode with a target RA so that RA·IΔn ≤ 50 V, main bonding, and supplementary bonding in bathrooms.
- **Outputs:** the panel schedule (CSV/PDF), a single-line diagram (SVG/DXF), and Revit electrical fixtures, circuits and panels through the Revit API. Revit then provides home-run tags and plans per level.
- **Standards data to acquire:** the Egyptian Code for electrical installations in buildings (verify the exact code number and edition before carding); IEC 60364-4-41, -5-52 (current-carrying capacity tables, Annex G), -5-53/-534, and -7-701/-702/-714; IEC 60898/61009; EEHC utility connection rules and meter sizes; and the Egyptian ECP energy code for lighting power.

## Six lighting tasks to reach A+

| # | Task | Inputs | Method | Acceptance against a known reference |
|---|---|---|---|---|
| L1 | Radiance electric-light calc report per room | Revit geometry, LDT files, reflectances | `rtrace -ab 5` grid (EN 12464-1 grid sizing); Em, U0, Emin, Ez, vertical illuminance at the vanity | Reproduce CIE 171:2006 test cases 5.x within ±5 %; DIALux evo export of the same room within ±10 % |
| L2 | Glare | Luminaire luminance tables, viewpoints (bed, sofa, table) | UGR (CIE 117 tabular plus calculated); luminance ratios; evalglare DGP daylight | CIE 190 UGR worked example exact; one manufacturer UGR table reproduced within ±1 |
| L3 | RCP setting-out solver | Furniture, coves, beams, joinery axes | Constrained placement: align to axes, spacing-to-height ratio limits, symmetry; flags scallops on soft surfaces | Golden-file test on three hand-designed rooms (rule satisfied); visual QA shows no off-axis points |
| L4 | Controls and scenes | Layers, rooms, daily use | Zone graph, DALI-2 addressing, scene table (Day, Evening, Dinner, Film, Night-path, Off) with dim levels; recompute lux per scene | Every task card still met in its scene; Evening ≤ 3:1 room-to-task ratio; scene table round-trips to a Lutron/DALI config CSV |
| L5 | Exterior and emergency | Garden plan, facade, paths | Exterior kinds (IP65+, IK, 2700 K, low glare, shielded); EN 12464-2 / IES RP-33 path values; stair and route battery luminaires per EN 1838 as guidance | Path Emin and stair tread E against cards; dark-sky ULOR = 0 check |
| L6 | Daylight metrics completion | Annual .wea, blinds model | LM-83 sDA300/50 % with dynamic blinds, ASE1000,250, annual DGP (5-phase or imageless) | Reproduce the LM-83 reference office within ±3 sDA points |

## Six electrical tasks to reach A+

| # | Task | Inputs | Method | Acceptance against a known reference |
|---|---|---|---|---|
| E1 | Standards cards | Egyptian code, IEC 60364 tables | Card the current-carrying capacity tables, correction factors, demand factors and voltage-drop mV/A/m with page citations | `test_evidence_values` on 30 sampled table cells, compared against the source |
| E2 | Device placement | Room types, furniture | Rules engine (cited) placing sockets, switches and data; door-swing latch-side logic | Three rooms against a licensed engineer's marked-up plan; recall at least 95 %, no false bathroom-zone placements (negative tests) |
| E3 | Circuiting and load | Devices, fixtures, equipment | Grouping, phase balance, max demand | Reproduce the worked max-demand example from the IET OSG or the Egyptian code within ±2 % |
| E4 | Cable, protection and voltage drop | Circuits, routes from Revit | Ib/In/Iz, Zs, RCD selection, voltage drop | Match a published IEC 60364-5-52 worked example and a ProDesign/ETAP run within ±1 size step |
| E5 | Panel schedule and single-line diagram | E3/E4 | Generated SVG/DXF plus CSV | An engineer can construct from it; ways count, RCD groupings and ratings checked by a second tool |
| E6 | Revit and lighting coordination | Lighting zones, E2–E5 | Place electrical fixtures, build circuits and panels through the API; read back | Read-back of circuit loads equals the module's loads within 1 W; every luminaire on exactly one circuit; every DALI zone maps to circuits |
