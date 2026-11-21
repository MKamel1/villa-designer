# L7b villa electrical (D1)

The L7 engine (`docs/lanes/L7-electrical-engine.md`) run on the whole D1 villa from `archpipe.model.load("D1")`.

```
PYTHONPATH=src python -m archpipe.electrical.d1_run [--out DIR] [--docs docs/lanes/L7b-d1] [--data tests/electrical/d1]
PYTHONPATH=src python -m pytest tests/electrical -q          # 133 tests (96 engine + 37 villa)
```

Outputs: `out/electrical/d1/` (git-ignored), `out/checks/L7.json`, and committed copies. Lane L7b owns only `docs/lanes/L7*.md`
(lane guard), so the markdown schedules are in `docs/lanes/L7b-d1/` and the csv, svg and json copies are in `tests/electrical/d1/`:

| file | content |
|---|---|
| `board_schedule_{MDB,DB-B,DB-GF}.md/.csv` | ways, device, Ib, In, cable, length, Iz, voltage drop from the origin, disconnection |
| `sld_{MDB,DB-B,DB-GF}.svg` | single-line diagram per board (generated from the same `Design` as the schedule) |
| `cable_schedule.csv` | incomer, two sub-board feeders, 57 final circuits: csa, method, Ca/Cg/Ci, Iz, dV |
| `load_schedule.md/.csv` | connected load, diversity by category and board, maximum demand, supply recommendation, sensitivity |
| `device_list.csv`, `device_list_by_room.md` | every switch, socket, FCU, isolator, luminaire and ELV device by room with its circuit |
| `elv_devices.csv` | smoke, heat, data, TV/SAT, Wi-Fi, CCTV, intercom, rack |
| `summary.json`, `L7.json` | all numbers below; the contract check records (EA1 to EA15) |

## Summary

| item | result |
|---|---|
| boards | 3: MDB (pantry, B), DB-B (stair-foot hall, B), DB-GF (stair-head gallery, GF). DB-B and DB-GF are stacked, riser about 3 m |
| ways (used / total) | MDB 8 / 10 (6 circuits + 2 feeders), DB-B 32 / 40, DB-GF 19 / 24 |
| final circuits | 57: 5 lighting, 26 socket radials (2 kitchen worktop, 1 garden), 26 dedicated |
| devices | 140 sockets (22 of them floor boxes), 33 switches, 14 FCUs, 8 AC isolators, 2 cooker units (plus 17 data, 3 TV/SAT, 142 luminaires) |
| connected load | 143.1 kVA (sum of Ib at 220 V, single-phase equivalent) |
| **maximum demand** | **80.8 kVA** = 367 A single-phase equivalent, 122 A on the worst phase of three (Whitfield Table 6.2, household column). This is an **upper bound** (see below) |
| **supply recommendation** | **three-phase 220/380 V**; incomer 125 A, 50 mm2 Cu PVC, 15 m (length assumed), 0.37 % drop. Holds in every sensitivity row |
| sub-board feeders | MDB to DB-B: 80 A, 25 mm2, 10.4 m. MDB to DB-GF: 50 A, 16 mm2, 14.9 m |
| phase balance | L1 216.7 A, L2 216.9 A, L3 216.7 A (0.1 % from the mean) |
| worst voltage drop | 4.93 % from the origin (`DB-B/S5`, lounge socket radial, 32.6 m, 2.5 mm2) (limit 5 %; lighting 3 %) |
| alarm grade | ADB minimum Grade D2 LD3 (no storey over 200 m2: B 168.6, GF 117.5 gross); design Grade D1 LD2 or better, all interlinked |

**Demand caveat.** The carded rule takes 100 % of the largest and 40 % of every other circuit, applied to the breaker rating of each of the
26 socket radials. Sockets are 40 of the 80.8 kVA, so the headline is conservative. The load schedule gives the same calculation with the
socket radials at 50 % and 25 % of their rating: 60.8 kVA and 50.8 kVA (policy factors, not sourced). Every row is above the 63 A single-phase
limit, so the three-phase recommendation does not depend on the choice. The 63 A limit is our policy threshold (card `EL-POL-SUPPLY`);
the utility's own single-phase limit was not verified.

## What was added to the engine

- **Polygon-aware placement** (`placement.room_walls`): one `Wall` per polygon edge (N, E, S, W, then N2, E2, ...), inward normals, and
  furniture/door positions projected onto the wall. A 4-vertex rectangle gives the same walls as the old rectangle code (the test-house demo output is
  byte-identical). All 30 D1 rooms are 4-vertex rectangles, so the non-rectangular branch is exercised by an L-shaped test room, not by D1.
- **Wall and opening clearance** from the model's `wall`, `window` and `door` elements: every wall device must sit on a wall element of its
  level and outside every window and door box (z range included). The projection must fall inside the wall segment (no credit for a point beyond a wall end). A device that does not pass is slid along the wall (up to 1.5 m), turned into a floor box
  600 mm inside the room (sockets on open-plan edges; not inside furniture or the stair footprint, else dropped with a warning), or dropped with a warning. Stairs get no general sockets. Boards need a 600 mm clear stretch of wall. EA1 re-checks the finished list independently.
- **Multi-board design**: one sub-board per level plus a main board; the main board also carries the site loads. Sub-board feeders are sized on the
  sub-board's own diversified demand; the voltage drop of each final circuit includes incomer and feeder.
- **Routes** (stated assumption, `EL-POL-ROUTE`): Manhattan distance x 1.15 through all the circuit's load points (nearest-neighbour chain, one point per room
  for lighting plus 4 m per room) plus 3 m of vertical drops. No wall or slab routing.
- **Door hinge data**: used when `params.hinge` exists in the model (none does), else the hinge is put at the end of the opening nearer the wall corner, the
  switch goes on the open (latch) side at 1.15 m, and every such switch is listed (EA1 warning, card `EL-POL-LATCH`). Rooms under 2 m2 take no door switch.
- **Open-plan rooms** (no door): one control point at the nearest wall to the opening; `lighting control` there is for L6b to define.
- **ELV** (`elv.py`): detector grid by coverage radius, data and TV/SAT points from the placed furniture clusters, Wi-Fi APs by greedy coverage,
  CCTV, intercom. Smoke and heat count only when in the room or in an open-plan neighbour (no door between).
- **External circuits** (gate, EV, garden, irrigation): buried armoured cable, IEC B.52.4 method D2 (3 loaded, conservative).

## EA checks (out/checks/L7.json): 0 fail

| criterion | result | note |
|---|---|---|
| EA1 device provision | 30 rooms pass plus the clearance record (31 pass), 8 warnings, recall not evaluated | the warnings: 22 switches on a policy latch side (no hinge data); 7 devices not placed (1 dirty-kitchen socket in a full-height window; 6 floor boxes that fell inside the sofas, kitchen island or dining table). Recall against engineer-marked rooms cannot run: no markup exists |
| EA2 bathroom zones | 6 pass (zones and RCD for family bath, ensuite, guest WC) | zone data from the model fixtures (rain-head position and height, tray rim). A heater FCU is the only device in each bathroom, outside the zones |
| EA3 circuits | 90 pass | each luminaire in one zone, each zone on one circuit, lighting circuits <= 10 A (packed to <= 2 A, about 400 W, so a trip does not black out a level), one dedicated circuit per equipment item |
| EA4 max demand | installation and 3 board records **not evaluated** (figure reported, no limit to pass against: the main breaker is computed, not given); 5 reference cases pass within 2 % | IET OSG Appendix A was not obtained; Whitfield Table 6.2 used |
| EA5 sizing | 65 pass (57 circuits, incomer, 2 feeders, 5 reference cases) | smallest margin of Iz over In is 0.1 A (`DB-B/D1`); the 2.5 mm2 socket radials are Iz 16.1 A vs In 16 A under the group-of-3 policy |
| EA6 voltage drop | 66 pass | worst 4.93 % (`DB-B/S5`); the garden radial is 3.9 % |
| EA7 fault protection | **not evaluated** (1 record) | the electrode resistance RA has not been measured and TT is unconfirmed. For a Type S 300 mA origin RCD the requirement is RA <= 50 V / 0.3 A = 167 ohm; the 30 mA finals allow 1667 ohm. No RA was invented |
| EA8 RCD | 57 pass | 30 mA Type A RCBO on every final circuit; Type S 300 mA at the origin (drawn on the MDB SLD) |
| EA9 surge and lightning | not evaluated | SPD Type 2 is drawn; the IEC 62305-2 risk calculation is not done |
| EA10 earthing | not evaluated | needs the measured RA and bonding survey |
| EA11 phase balance | pass on the installation; 3 warnings | MDB alone (99.5 % off mean, few large single-phase site loads), DB-B alone (20.4 %) and DB-GF alone (15.3 %) are not balanced by themselves; the installation total is |
| EA12 boards and SLD | 4 pass | 57 circuits + 2 feeders in model = schedule = SLD, spare ways 20 % / 20 % / 21 % per board (MDB / DB-B / DB-GF). The check compares one design with its own renderings, not a second tool |
| EA13 lighting coordination | 6 pass | on **provisional** zones (below) |
| EA14 Revit read-back | not evaluated | no Revit electrical model (E-12) |
| EA15 ELV and fire | 29 pass | grade, smoke on both levels and in both stairs, heat in kitchen and dirty kitchen, coverage of every point of 27 alarm rooms, none in bathrooms, G1 cinema mitigation (lounge and cinema both interlinked), data at each bedroom, study and TV wall, AP coverage (5 indoor, 1 outdoor), longest ELV cable 35 m, CCTV at gate and 4 corners (+ deck), intercom |

Every open edge of an open-plan pair of rooms can receive a floor box from both rooms (not deduplicated).

Passing the policy checks (EA1, EA3, EA8, EA11, EA12, EA15) means the policy rules are met, not that an engineer would sign the layout.

**Alarm grade** (EA15 and `R-sources.md` D1): ADB vol. 1 para 1.1 minimum is Grade D2 LD3; paras 1.5 to 1.7 change this to Grade A (LD3 on two storeys, LD2 on three or
more) only if a storey exceeds 200 m2. From the model, net room area plus wall plan area gives B 168.6 m2 and GF 117.5 m2, so D2 LD3 applies. The design adopts D1 (mains with sealed
battery) at LD2 or better: 17 smoke and 2 heat alarms, one dedicated radial (`FIRE-ALARMS`, DB-B) so the hard-wired interlink stays on one phase. **G1 cinema waiver**: the lounge and
the cinema each have a smoke detector on the interlinked network (card `EL-G1-CINEMA`, check `G1-cinema-waiver`). The grade rule is the UK ADB (the Egyptian fire code is not carded); detector radii
(7.5 m smoke, 5.3 m heat) are our policy (`EL-POL-ELV`), not a code value.

## Assumptions to confirm with the client

Each equipment line is in `knowledge/electrical/d1-equipment-assumed.json` with `status: assumed` and a reason; correct the file and re-run.

1. **Equipment** (electrical input power, typical Egyptian villa, no datasheet): split ACs in kids A and B 1.5 HP (1.2 kW), parents 2 HP (1.7), study 1.5 HP, lounge 3 HP (2.4), living 3 HP, dining 2 HP, cinema 2 HP;
   water heaters 2.0 kW family bath and ensuite, 1.5 kW guest; electric oven 3 kW and **induction hob 6 kW** (a gas hob removes a 32 A circuit; the dirty kitchen is assumed gas); dishwasher 1.8, fridge 0.4, pantry freezer 0.3, washer 2.2, dryer 2.5 kW;
   booster pump 1.1 kW in the store under the ramp, irrigation pump 0.55 kW, gate motor 0.4 kW; **EV-ready 7.4 kW at the parking deck counted at full load**; garden lighting 300 W allowance (the model has no exterior luminaires);
   ELV rack 0.6 kW; 4 outdoor sockets.
2. **Supply**: three-phase (recommended), earthing TT and RA unconfirmed (EA7, EA10 not evaluated), meter at the street fence with a 15 m incomer, main board in the pantry. The roof/void ambient is 50 C for GF lighting runs (brief 45 to 50 C) and 40 C for B; the feeder ambient 40 C.
3. **Lighting zones are provisional.** `origin/lane/L6b` had no `knowledge/lighting/zones-d1.json` at run time, so zones are one per room and layer (59, dimming "switched") and 60 of the 142 luminaires (strips, pendants, lamps) have no watts in the model and use flux / 90 lm/W. The adapter reads L6b's file
   when it appears; re-run then. The 5 lighting circuits group zones by level in room order, so one circuit can span ten small rooms (route 104 m for `DB-GF/L1`); regroup when real zones exist.
4. **Door hinges** are not in the model (0 of 29 door records): 22 switches are on a policy latch side. A door schedule with hinge sides fixes this.
5. **Bed heads** are not authored: derived from the wall each bed stands against. The kids-A bunk stands along its wall with no short end near a wall, so bedside sockets sit at both ends of that wall.
6. **Open-plan edges** have no wall element: 22 sockets are floor boxes 600 mm inside the room instead of wall sockets (lounge, family, kitchen, dining, living, stairs, halls; marked `floor box` in `device_list.csv`; positions need the interior design). A floating sofa gets no end sockets.
7. **Positions** of the ELV cabinet (under-stair cupboard in stair-b), CCTV, intercom monitors (hall-b, corridor, parents-bed) and APs are layout proposals; the plot is the fence-bounded rectangle from the model context.
8. **Routes** are Manhattan x 1.15 with 3 m drops, not wall/slab routing; cable lengths can change by 20 to 30 % when routed.
9. **Max demand** is the carded upper bound; the client's electrical engineer should choose the socket diversity (the 52 to 85 kVA range above). The incomer (160 A) is sized on the upper bound.
10. Not done: SPD risk calculation, earthing and bonding design, lightning protection, Revit read-back, the EA1 recall test, and a second-tool cross-check of the SLD.
