# RV2 hand-back (Revit-free 2D drawings, 2026-11-21)

Generate: `python -m archpipe.documents --out out/documents/D1 --scene <scene.json> --previews src/archpipe/documents/samples`
(`--scene` enables the Line Art sections and elevations; Blender 4.5 at `~/opt/blender/blender`). `out/` is not committed.

## Sheets (20, A2 unless noted; combined `out/documents/D1/D1-set.pdf` with bookmarks)

A-001 cover (A3) | A-100 site plan 1:150 | A-101/A-102 GA plans B/GF 1:100 | A-111/A-112 furnished | A-121/A-122 reflected ceiling and
lighting (type tags, legend, CH tags) | A-131/A-132 room colour-fill with area legend | A-141 stair B+GF 1:20 | A-142 wet rooms 1:20
(family bath, ensuite, guest WC) | A-201 elevations N (street) and S | A-202 E and W | A-301 stair section 1:50 (cropped) |
A-302 garden section 1:100 | A-601 door (with handing), window, room schedules (A3) | A-602 finish | A-603 furniture | A-604 luminaire (A3).
All plans are north-up in the client convention (street side up, east right). The 8 door-handing judgement calls from lane M
carry a pink "?" on A-101, A-102, A-111, A-112 and the callouts, and "YES" in the to-confirm column of the door schedule.

## Which scene the section/elevation sheets came from

`e645041`-equivalent scene (sha256 `28bc8df33ab45f9dc097d00714746b8daee36b0a876b107b270b8bacaa54dacc`, the build in
`/tmp/RV2-scene/scene.json`): integ/aplus does not build a scene yet (approval drift, lane RA). The poche comes from the
current design model (696 elements), so the cut is current; the projected lines come from that older scene. **Re-run when RA
lands** (same command with the new scene.json): the scene hash is printed on each sheet and recorded in `sheetset.json`.

## Decisions (no human was available)

1. Plans on A2 at 1:100, not A3: in the client frame the 22.7 m length runs up the sheet and does not fit A3 with dimension chains.
2. Elevations/sections: cut poche from design-model solids (the scene shell is finish skins, so it has no closed solids); lines from
   Blender Line Art; strokes on the cut plane dropped. Lesson RV2-03.
3. Elevations draw our building only (plot-wide fence, sister, neighbours filtered per face); the fence top is annotated, not drawn.
4. Door/window axis follows the host wall, not `rotation_deg` (one model door is inconsistent: reported, lesson RV2-01).
5. True north on the site plan is 70 degrees clockwise of sheet-up (street facade azimuth 290, `villa_env`).
6. Site plan scale is 1:150 (A2); the plot line is the fence outer face (ASSUMED, no survey).
7. Door "judgement" flags are drawn as "?" markers, not text, to keep the plans readable; the legend explains them.
8. The banner now reads "GENERATED FROM THE DESIGN MODEL" (no longer "NOT REVIT").
9. Ramp slab is cut only for planes along the y axis (profile origin documented as absolute model x).

## Known gaps

Parity gaps in `RV2-parity.md` (9). Not done: lux table, furniture "why", clearance zones (data elsewhere); interior elevations;
D2/D3; revision clouds (C14); sun overlays (C16). Elevations are line drawings (no material tone). `scripts/verify.py` fails to
import on this base (`archpipe.model` has no `SpecError`, imported by `cli.py`): not touched by this lane.
