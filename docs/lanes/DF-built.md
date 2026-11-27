# Lane DF: the client's FINAL parents' suite, BUILT (2026-11-26)

Client decision: `docs/decisions/privacy-2026-11-26.md`, section "FINAL decision": R3 (sheet DF-102) plus the annexed GF corridor end. Everything below is in the **design model D1**
(sources, snapshot, receipts), not a proposal. As-built sheet: `docs/lanes/DF-plans/DF-102-plan-AS-BUILT.{pdf,png}` (reproduce: `PYTHONPATH=src python scripts/df_asbuilt.py`).
Compass: client convention, street = north; model +y = client east, model +x = client south.

## What was built
| Item | Where | Value |
|---|---|---|
| Bed turned, head to the east window wall, centred | `villa_furnish._layout` `pb-bed` (rot 180) | centre x 20.437, head on y -23.791; 1160 mm each side, 800 mm at the foot; trays kept |
| Low upholstered head panel | `furniture.JOINERY_BED` `panel_z1` 1350 -> **900** | stops at the 0.90 m window sill; 50 mm, floats from the mattress top (0.525) |
| Roller blackout + fixed side drapes | `villa_render` (`fixed_drapes` curtain, roller cassette and fabric meshes), `villa_scene.setup_view` | cassette 60 x 60 mm in the reveal at the window head; fabric lowered in night views only; heavy leaves stacked on the piers (0.18 m each), no sheer, no draw layer; `CURTAIN_PARK` emptied (the old parked stack belonged to this window) |
| Reading lights on arms clamped to the panel | `villa_lighting` `WALL-READ`, `villa_render` post + tube arm, `fitting_mounting` | post from the panel's top rail (0.90) to the lamp at 1.30 m, head 0.10 m in front of the panel face, aimed at the pillow |
| **Power route** | `electrical/placement.py` (`EA1-bed-head-supply`), `villa.py` | a 24 V DC SELV driver/junction (device `SOC-parents-bed-068`, kind `socket_selv`) in the sill wall BEHIND the panel at z 0.30, centred on the bed (x 20.437), fed from the lamps' own lighting circuit `DB-GF/L2`; a 24 V lead runs inside the panel's rear cavity to a connector in each arm's clamp. No floor box: nothing stands beside the head (glass above 0.90 m, piers 0.88 / 0.64 m) and a floor box under the deck would be unreachable. The panel lifts off its cleats for service. Bedside mains sockets stay (`EA1-bedside-both-sides`, 0.30 m either side of the bed, z 0.45, below the sill). Regenerated outputs: `docs/lanes/L7b-d1/`, `tests/electrical/d1/`. |
| Cove moved to the slat wall | `villa_lighting` `COVE-parents-bed-01` | strip 0.12 m off the corridor-side wall (x 18.597), 2.30 m long along y, aimed +x and up: it no longer faces glass |
| Slat feature on the corridor-side wall | `villa_render` `detail-headboard-slats` (id kept: mounting rows and tests key on it) | x 18.477, y -26.541..-23.981 (the solid run: from the lobby mouth to the 0.16 m return), 30 x 30 at 50 pitch, to 2.10 m; hosted on the west wall (outward +x) |
| Vanity | `villa_furnish.PB_VANITY_Y0` -25.3 -> **-26.2** | the brief's ~0.30 m measures **0.50 m** between the open tray and the vanity corner; 0.90 m measures **0.76 m** (see below). The tucked chair is now flush (it stood 0.03 m proud) |
| Dressing: new door at the lobby end | `villa_parking.DRESSING_DOOR_X` 21.897 -> **19.977** | 800 x 2100 leaf, opening x 19.577..20.377 in the head wall, **hinged on the +x (client south) jamb** (`villa_furnish.DOOR_HINGE`), swings into the dressing room so the open leaf screens the view |
| Old head-wall door | no door pinned there any more | the wall is continuous (`wall-GF-int-24`), asserted in `tests/model/test_suite_built.py` |
| Hers | `pd-hang-1` | 1.87 m from the new door's jamb to the east wall (HS 0.20, DR 0.42, DH 0.60, LH 0.65 from the door); his unchanged (1.346 m) |
| ANNEX: suite vestibule | `villa_parking` room `suite-vestibule` (x 17.50..19.477, y -28.471..-27.421, clear; occupancy `corridor` with `closed=True`), wall x 17.45 | the corridor end past kids-b becomes the suite vestibule |
| ANNEX: suite door | `door-GF-corridor-suite-vestibule` | x 17.45, opening centred at y -27.931 (returns 90 mm south, 60 mm north of the 1.05 m clear corridor), **leaf 0.80** (opening 0.90), **hinged on the north jamb, swings INTO the vestibule**, **self-closing** (`door.params.self_closing`, `villa_furnish.SELF_CLOSING`: the second layer, never the first) |
| Vestibule storage | `sv-store` (`store_shelving`) | flat 130 mm cabinet, 1.70 m long, on the facade wall (y -28.471..-28.341): folded wraps, prayer mats, scarves, keys |
| Entry from the vestibule | `door-GF-suite-vestibule-parents-entry` | the old corridor pocket door (900), now vestibule to lobby |

## Suite door: width, swing, handing (privacy best with the door OPEN)
`scripts/df_suite_door_choice.py` (built model, 2D, furniture ignored, leaf swung 90 deg into the vestibule): points of the vestibule, lobby and bedroom floor (0.1 m grid) that ANY public corridor point can see through the open door.
| leaf | hinge | vestibule | lobby | bedroom |
|---|---|---|---|---|
| 0.80 | north / south / none | 200/200 | 27/70 | **0/1092** |
| 0.90 | north / south / none | 200/200 | 31/70 | 31/1092 |
| 1.00 | north / south / none | 200/200 | 31/70 | 31/1092 |
The hinge side changes nothing (a leaf at 90 deg lies along a side wall and screens no ray that reaches the entry), **the width does**: a narrower opening leaves wall beside the entry's sightline. So 0.80. Swing INTO the vestibule is forced (out across the corridor it would sweep kids-b's approach and the public passage); the north hinge keeps the open leaf against the kids-b side wall and clear of the storage on the south wall. The protected zones (dressing, en-suite, route) are seen by 0 viewpoints in every variant. The closer is the second layer: it shortens the time the leaf is open; it is not what the criterion rests on.

## Privacy, all suite doors open, on the BUILT model
`archpipe.model.suite_privacy` on `model.load("D1")`: **0 of 532 outside viewpoints see the dressing room, the en-suite floor and doorway, or the route between them** (corridor every 0.25 x 0.1 m from the west to the suite door, the stair landing, the stair void, the gallery, kids-a and kids-b rooms and their doorways; targets: 324 points at 0.2 m, plus the en-suite doorway at 0.1 m). The kids-b doorway and the corridor now stop at the suite door. Furniture and door leaves are ignored (worst case); leaves of two suite doors swung open: still 0.
Regression tests (`tests/model/test_suite_privacy.py`): positive control on **option 2's geometry** (an opening straight from the vestibule into the dressing room, cut into the built walls): > 100 viewpoints see in, incl. the corridor and the landing; negative: the build shows 0. `tests/model/test_suite_built.py` carries 16 more (door, kids-b untouched, escape, vestibule passage, hers, bed, trays, power).

## Routes and widths (model/circulation.py, 20 mm grid, widest disc; all routes of the villa pass, both trays open 0.25 m)
| Route | Achieved | Required | Source |
|---|---|---|---|
| Vestibule: suite door to entry door | **0.920 m** | 0.914 m | card `mitton-path-of-travel-min` (36 in); the 0.90 m hall card `ukadm-hall-min-m42` (UK AD M M4(2) para 2.22a) is met by the same width |
| Vestibule passage left (1.05 m clear less the 0.13 m cabinet) | 0.92 m | | same; also front-of-storage 914 mm (card `tss-front-of-storage-914`) |
| Bedroom: dressing door to the entry (trays open) | 0.849 m | 0.750 m | card `ukadm-bedroom-route-750` (UK AD M 2.25a) |
| Dressing door approach | 0.988 m | 0.750 m | same |
| Dressing: door to en-suite door | 0.880 m | 0.750 m | same, with the private-suite project waiver |
| Bedsides W / E | 1160 / 1160 mm | 750 | same |
| Foot to the south wall | 800 mm | 750 | same |
| Past the open tray at the vanity (door to the head end) | 0.76 m | 0.750 m | same; `test_open_trays_keep_750_past_the_vanity` |
All are benchmarks, not code compliance (no jurisdiction pack). Kids-b's door (centre 16.689, 0.90 leaf, jambs 16.239..17.139) is unmoved, swings into kids-b, and its 0.30 m approach strip is free; the suite wall's face (x 17.40) stands 0.26 m east of its jamb. The kids' escape: kids-a and kids-b reach the GF core door through the corridor and landing with every suite room removed from the door graph, and no suite room links two public rooms (`test_kids_escape_route_never_passes_through_the_suite`, with a negative control).

## Decisions I made (no one to ask)
* Vanity 0.90 m, not ~0.30 m (measured, above). Vanity chair flush.
* Vestibule cabinet 130 mm deep so the passage stays above 0.914 m; the passage would be 0.80 m with a 0.25 m cabinet and 0.88 m with 0.17 m.
* Suite door leaf 0.80 (measured table above), hinge north.
* Reading lights are 24 V SELV off the lamps' own circuit via a driver behind the panel; no floor box.
* Lighting: the corridor's last wall washer (x 18.537) now stands in the vestibule as `WW-suite-vestibule-01`, plus `DL-suite-vestibule-02`; the corridor's counter skips the old slot 06 so the approved `marker-PATH-corridor-07..09` keep their ids. The parents' ambient downlight moved from the head end to the bed foot (y -26.431; at the head it put 240 kcd/m2 into the pillow eye, LA4 cap 3000): `lightcalc` results, sensors, zones and the electrical outputs were regenerated (Radiance `villa_run`, `villa_emit`, `handcalc`); the reading zone solves at driver 0.56, the table keeps 0.70.
* The vestibule has occupancy `corridor` with `closed=True` (a new layout flag: walls and a door even between two open occupancies). As `bedroom` it failed EG5 (area, width) and LS5 (inner room) gates.
* Approval rows voided and retired in place (`retired_rows`): six `WALL-READ-parents-bed` rows in `c4-bc-approvals.json` and the `detail-headboard-slats` rows in `c4-e-lead-approvals.json`.
* The imported vanity model's stored position moved with the item (receipt `furniture-stage2`, `neutral_review.selection.position`); the neutral image approval is **retained, not repeated**.
* The exposure record is measured on the GPU: `exposure_groups.require_record` refuses a CPU-measured record ("GPU evidence differ"), whatever the instruction to use the CPU. Renders on the GPU through jobq.
