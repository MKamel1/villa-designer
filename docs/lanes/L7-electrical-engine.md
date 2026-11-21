# L7 electrical engine

Package `src/archpipe/electrical/`, data in `knowledge/electrical/`, tests in `tests/electrical/`. Governing
standard: IEC 60364 (BS 7671 / IET guidance where it gives worked examples). Site facts only: 220/380 V 50 Hz,
likely TT earthing (unconfirmed), 45-50 C roof ambient. No national-code dependency.

Run the demo (a 4-room test house, not the villa):

```
PYTHONPATH=src python -m archpipe.electrical.demo [--out DIR]     # writes out/checks/L7.json and DIR/{board_schedule.csv,md,sld.svg,...}
PYTHONPATH=src python -m pytest tests/electrical -q               # 88 tests (pytest from the system Python; the project venv has none)
python knowledge/electrical/build_data.py                         # rebuild cards.json / tables.json from the snapshots
```

A committed copy of the demo output is in `tests/electrical/demo/` (`out/` is git-ignored).

## Method

| step | module | rule | criterion |
|---|---|---|---|
| placement | `placement.py` | per room type: switch on the latch side of every door at 1.15 m, both bedside sides, desk/TV/sofa clusters, worktop pitch <= 1.2 m, AC isolator, dedicated cooker/appliance spurs, nothing but an FCU outside the zones in a bathroom | EA1 (policy cards) |
| bathroom zones | `zones.py` | zone 0 basin interior, zone 1 above to 2.25 m (or highest head), zone 2 = 0.6 m beyond; no-basin shower = 1.2 m radius, zone 0 height 0.10 m. Socket in zones 0-2 = fail (gate); a socket within 2.5 m of zone 1 = warn (UK national rule, not IEC) | EA2 |
| circuits | `circuits.group_circuits` | lighting zones (from `contracts.LightingZone`) packed first-fit into circuits of <= 10 A (Ib = W/(V x 0.9)), a zone is never split; 16 A socket radials per room (<= 8 outlets), 20 A kitchen worktop radial; one dedicated circuit per equipment item | EA3 |
| demand | `demand.py` | per-category diversity (Whitfield Table 6.2 household/shop/hotel columns; EIG A14 for AC); result as A per phase and kVA | EA4 |
| sizing | `sizing.py` | `Ib <= In <= Iz`, `Iz = parallel x I_tab x factor`; factors per route **segment** (Ca ambient, Cg grouping, Ci thermal insulation multiply inside a segment, worst segment governs; `combine="product"` is the stricter whole-route product) | EA5 |
| voltage drop | `sizing.vd_*` | mV/A/m (BS 7671:1992 multicore columns <= 16 mm2 single-phase, else EIG Fig G30); from the origin = incomer + final circuit vs 3 % lighting / 5 % other | EA6 |
| fault protection | `circuits._protection` | TT: RA x IDn <= 50 V and RCD <= 0.2 s (0.04 s at 5 x IDn); TN: Uo/Zs >= k x In (B 5, C 10, D 20), limit 0.4 s. Needs RA (TT) or Ze (TN) from the fixture, otherwise `not_evaluated` | EA7 |
| RCD | `circuits.group_circuits` | every final circuit 30 mA Type A RCBO (policy; Fig Q7 + s.701 require it for sockets and bathrooms), Type S 300 mA at the TT origin | EA8 |
| phase balance | `circuits.assign_phases` | greedy + local swaps on Ib, check within 10 % of the mean | EA11 |
| schedule + SLD | `schedule.py` | one `Design` drives the CSV/markdown schedule and the SVG; EA12 checks circuit ids in model = schedule = SVG and >= 20 % spare ways | EA12 |
| lighting join | `checks.py` | each luminaire in exactly one zone, each zone on exactly one circuit, circuit W = sum of luminaire W (1 W) | EA13 |

Outputs use `contracts.Circuit` (`circuits.to_contract`) and `contracts.CheckResult` (`checks.run_checks`,
written with `contracts.write_results("L7", ...)`). Internally a richer `CircuitSpec` keeps phase, curve, method, Zs.

## Sources: what is sourced, std, policy, unverified

`knowledge/electrical/cards.json` holds 42 `SourceCard`s (25 std, 7 sourced, 7 policy, 3 unverified); every std/sourced
card has a verbatim quote that `tests/electrical/test_el_cards.py` finds in the committed text snapshot under
`knowledge/electrical/source_snapshots/`. Every numeric table cell in `tables.json` that came from a web table is
compared with the snapshot row by row in the same test file (G20, G21, G30, Ca, Cg, Ci, Whitfield 4.6/4.7).

| data | table | source (all read second-hand, so `std`) | status |
|---|---|---|---|
| current-carrying capacity, PVC, 3 loaded Cu/Al, methods A1 A2 B1 B2 C D1 D2, 1.5-300 mm2 | IEC 60364-5-52 Table B.52.4 | Schneider Electrical Installation Guide (EIG) Fig G20 | std |
| simplified ampacity (F, 3 PVC column only) | IEC 60364-5-52 simplified table | EIG Fig G21 | std; A1/A2 header cells are inconsistent in the scrape and are not used |
| Ca ambient 10-80 C PVC / XLPE | B.52.14 | EIG Fig G12 | std |
| Cg grouping | B.52.17 (bunched row) | EIG Fig G16 | std; buried grouping (G18 has a bad cell) left out |
| Ci thermal insulation, single-phase twin <= 16 mm2 current ratings and mV/A/m | BS 7671:1992 App. 4 (16th ed.) | Whitfield, The Electrician's Guide 5th ed., Tables 4.3-4.7 via TLC | std (superseded edition) |
| voltage drop V/A/km Cu 1.5-500 mm2 | Fig G30 | EIG | std |
| voltage-drop limits 3 % / 5 % | IEC 60364-5-52 Table G.52.1 | EIG Fig G25 | std |
| disconnection times TT 0.2 s, TN 0.4 s at 230 V, 1 s / 5 s distribution | IEC 60364-4-41 | EIG Figs F13, F19 | std |
| RCD operating times, RA limits, IDn <= 50/RA | 60364-4-41 | EIG F14, F12, TT Principle | std |
| MCB magnetic bands B 3-5 In, C 5-10, D 10-20 | IEC 60898 | EIG Fig H28 | std |
| bathroom zones, 30 mA RCD | IEC 60364-7-701 / BS 7671 s.701 | SELECT pocket guide TS 19-001 | std |
| demand/diversity | Table 6.2 (household, shop, hotel) | Whitfield 5th ed.; secondary sources describe the same household percentages for the IET On-Site Guide (not verified against the guide) | std |
| placement minima, circuit limits (10 A lighting, 16/20 A radials), phase balance 10 %, spare ways 20 %, RCD type A, breaker ladder, minimum csa | - | ours | policy |
| IEC 60364-5-52 Tables B.52.2/B.52.3/B.52.5 (two-loaded PVC, all XLPE) | - | not obtained | unverified: not used; single-phase finals use Whitfield 2-core columns, feeders use B.52.4 (3 loaded) |
| IET On-Site Guide Appendix A table and worked example | - | not obtained | unverified: Whitfield Table 6.2 used instead |
| RA, TT confirmation, roof ambient | - | client brief | unverified inputs |

Web access: electrical-installation.org blocks direct fetches (403), so the snapshots are Wayback copies
(`web.archive.org/web/2023id_/...`); the IEC and OSG standards were not purchased, so none of the IEC numbers is
read from the standard itself. The IEC/BS cards stay `std`, not `sourced`.

## Reference results

All inputs and expected values are the source's own (cards `EL-EX-*`, status `sourced`). Tolerance as pre-set
(demand +-2 %; sizing same size; voltage drop 1-5 % because the sources round).

| case | criterion | quantity | expected | achieved | error | source |
|---|---|---|---|---|---|---|
| Whitfield Ex. 6.1 shop, 415 V 3-ph | EA4 | total single-phase current | 486.2 A | 486.0 A | 0.04 % | Whitfield 5th ed. p. 6.2.3 |
| same | EA4 | three-phase line current | 162 A | 162.0 A | 0.0 % | same |
| Whitfield Ex. 6.2 cooker 14 kW + socket | EA4 | demand | 29.5 A | 29.5 A | 0.0 % | 6.5.2 |
| EIG A12 25 flats x 6 kVA | EA4 | apparent power / current | 69 kVA / 100 A | 69.0 kVA / 99.6 A | 0 % / 0.4 % | EIG Fig A11 |
| Whitfield Ex. 4.1 50 C roof, 8 bunched, 50 mm insulation | EA5 | csa (6 mm2 = 32 A is rejected) | 10 mm2 | 10 mm2 | same size | Whitfield 4.3.9 |
| same, two bunches of four | EA5 | csa | 6 mm2 | 6 mm2 | same size | same |
| Whitfield Ex. 4.5 | EA6 | drop 6 mm2, 12.5 A, 14 m | 1.28 V | 1.278 V | 0.2 % | 4.3.11 |
| Schneider cable example C1/C3/C7 (method F, 3 PVC, 400 V) | EA5 | csa per conductor | 240 / 120 / 95 mm2 | 240 / 120 / 95 mm2 | same size | EIG worked example; its Ecodial run gives 2x240, 2x120, 1x95 |
| same, Fig G72 | EA6 | drop C1/C3/C7, total | 0.12/0.47/0.13 %, 0.73 % | 0.125/0.473/0.128 %, 0.726 % | 4.2/0.7/1.6 %, 0.5 % | EIG G72 |
| Schneider Example 2 feeder + final | EA6 | 10.1 V, 4.4 % | 10.1 V, 4.4 % | 10.15 V, 4.42 % | 0.5 % | EIG G32 |

The Ecodial figures on the same EIG page serve as the "commercial tool" cross-check for EA5 (same csa); a separate
ProDesign/ETAP run was not available. The IET On-Site Guide Appendix A example itself was not found.

Negative tests: socket in zone 0, 1 and 2 fail; a shaver unit is allowed in zone 2 but not zone 1; a socket 2.5 m
rule only warns; a zone > 10 A fails EA3; a luminaire in two zones or a watt mismatch fails EA13; a circuit removed from
the SVG fails EA12; TN with Ze 6 ohm fails EA7; TT without RA is `not_evaluated`; a 300 mA final circuit fails EA8;
a whole-route product method needs a larger cable than the segment method.

## Demo result (test house)

15 circuits (4 lighting, 5 socket radials, 6 dedicated), balanced L1/L2/L3 = 58.2 A each, max demand 24.5 kVA (111.5 A
single-phase equivalent), 40 A incomer on 10 mm2 (0.60 % drop), 20 ways (25 % spare). `out/checks/L7.json` has 0 fail
and 0 warn; `not_evaluated`: EA1 recall, EA9, EA10, EA14, EA15. Caveats a reader must keep:

- Passing EA1/EA3/EA8/EA11/EA12 only means the policy rules are met; EA1 has no recall test. EA12 compares one design
  with its own renderings (a tamper test proves the check can fail), not a second tool.
- RA = 30 ohm is an assumption in the fixture; EA7 passes only on that assumption.
- CPC size is assumed equal to the phase conductor (TN path only, not exercised in the demo).
- Single-phase finals use BS 7671:1992 table values (16th edition), which for <= 16 mm2 PVC equal later editions for
  the cells checked, but that equality is not verified here.

## What is needed to run on the villa (D1 model, `docs/lanes/L2-model.md`)

1. **Geometry adapter** `archpipe.model.load("D1")` -> `electrical.model.House`:
   - `room` elements: `params.polygon_mm`, `clear_height_mm`, `finish_codes`; id `room-<rid>`; other elements carry the
     plain `<rid>` in `room`. The engine uses axis-aligned rectangles; non-rectangular rooms need polygon-aware wall
     walking in `placement.py` (30 rooms, B 17 and GF 13).
   - `door` elements: `placement` is a wall midpoint offset, `host` the nearest wall, `size` width. Hinge/swing and
     latch side are not in the model, so switch placement on the latch side needs `params.hinge` from L2 (or the Revit family).
   - `furniture` (80; `product_id` empty for stand-ins): beds, desks, TVs, sofas, worktops map to `Furniture.kind`;
     a wall/head-wall side must be derived from `rotation_deg` and the nearest wall.
   - `fixture` (7, bath fittings and wet zones) -> `zones.WetArea`: need `has_basin`, tray/bath rim height and shower
     head height. The model has wet zones as boxes, not zone-0/1/2 volumes.
   - `luminaire` (142; `watts`, `layer`, `product_id`) -> `Luminaire`; L6's `LightingZone` list is the join input.
     Until L6 publishes it, zone ids must come from `layer` + room.
2. **Equipment schedule** (AC per room, water heaters, oven/hob, washer, pump, EV, gate, lifts) is not in the model;
   it is a brief/interview input (`Equipment` records with kW and pf).
3. **Levels**: B (-3000 scene datum / -1.80 Revit) and GF need a sub-board per level and a riser; the engine currently
   writes one board. Route lengths need real board positions and wall/slab routing instead of Manhattan x 1.15.
4. **Supply**: 1- or 3-phase (client TBD), meter size, earthing confirmation and measured RA, the incomer length and
   the roof route ambient (45-50 C) split between roof and indoor segments per circuit.
5. **Missing data**: IEC 60364-5-52 B.52.2/B.52.3/B.52.5 (two-loaded and XLPE tables) and the IET OSG Appendix A would
   remove the conservative substitutions; an engineer's marked-up rooms are needed to measure EA1 recall; ELV, earthing,
   SPD risk (EA9, EA10, EA14, EA15) are separate modules.
6. **Revit**: circuit loads must be read back from the model (EA14) once E-12 exists.
