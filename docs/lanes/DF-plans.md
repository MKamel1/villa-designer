# AS-BUILT (2026-11-26): the plan sheets DF-101 / DF-102 are superseded

`docs/lanes/DF-plans/DF-102-plan-AS-BUILT.{pdf,png}` (sheet DF-102 rev P02, green banner "AS-BUILT / DESIGN MODEL D1") is drawn from the built design model by `scripts/df_asbuilt.py`
and replaces the two proposal plans below; DF-101 (today 1a) and DF-102-plan-R3 (PROPOSAL, red banner) stay in the folder as the record of what was proposed. DF-103/104 (elevations,
PROPOSAL) are not redrawn. What differs from the R3 proposal and why: `docs/lanes/DF-built.md`.

# Lane DF: parents' suite options as plans (2026-11-26)

PROPOSAL ONLY. The design model D1 is loaded and varied in memory (one door moved); nothing is written back. Reproduce: `PYTHONPATH=src python scripts/df_plans.py`.
Output in `docs/lanes/DF-plans/` (PDF + PNG each, A3 landscape): `DF-101-plan-today-1a` (1:50), `DF-102-plan-R3` (1:50), `DF-103-elevation-R3-bed-wall` (1:25), `DF-104-elevation-R3-slat-wall` (1:25); `numbers.json` holds the table values.
Walls, doors, windows come from the project's own drawers (`documents.plans`); furniture, curtains, hanging rails, trays, dimensions are drawn in `scripts/df_plans.py`. Each sheet carries the key-dimension table.

**Compass.** Sheets use the client convention (street = north, north-up). The earlier sketches used model axes, so their north/west/south/east are these sheets' EAST/NORTH/WEST/SOUTH: R3's "north window wall" is the EAST window wall; the "solid west wall" for the slats is the NORTH (corridor-side) wall; the dressing door is at the north end of the west wall.

## What the drawings showed that the sketches missed
1. **Curtain vs the bed head.** The model hangs the heavy curtain 0.15 m (sheer 0.10 m) off the wall face; R3's pillows start 0.07 m off the glass, so a draw curtain would cut through them. Drawn instead: fixed side drapes + roller blackout in the reveal (proposal).
2. **Headboard vs glass.** The model headboard rises to 1.35 m; the window sill is 0.90 m, so it would hide the glass from 0.90 to 1.35. Drawn: low upholstered panel to the sill (0.90).
3. **Reading lights.** There is no wall beside the R3 head (glass 2.40 m, piers 0.88 / 0.64 m); the old wall lights (1.45 m) have nowhere to go. Drawn: arms clamped on the panel; power route not designed.
4. **Cove.** The cove aims at the head wall; in R3 that is glass (reflects at night). Slat wall (north) would take it better. Not changed, flagged.
5. **East tray at the vanity.** East tray open leaves 510 mm to the vanity (750 needed); bedside 760 with trays closed. Shifting the vanity 0.30 m south (y -25.60..-24.60) would clear the tray window; not done (brief: vanity kept).
6. **Window not centred.** Window centre x 20.557 vs room centre 20.437 (120 mm): a room-centred bed sits 120 mm off the glass centre.
7. **Curtain through the vanity (today and R3).** The south window's floor-length curtain (0.15 m off the wall) runs through the 0.40 m deep vanity. Pre-existing in the model/render code; check the render.
8. **Handing.** Hinge at the SOUTH jamb: dressing floor seen from the lobby mouth 13% (no leaf) -> 1% (south hinge) vs 13% (north hinge, leaf flat on the wall). From the pillows the open doorway still shows 30% (34% without leaf): the bed looks straight at the doorway. 0 of 451 outside viewpoints see in (leaf ignored).
9. Today's bed is 107 mm east of room centre (bound to the lead-approved wall fittings); R3 is centred.
10. Open leaf stops 80 mm short of the hers run.

Assumed (not sourced): slat 30 x 40 at 60 pitch; curtain stack 0.43 m per side (villa_render's own 0.18 x width); hers double hang +150 mm.
