# RV2 plan: Revit-free 2D drawings (status: steps 1-8 built, see RV2-handback.md and RV2-parity.md)

Nothing in the sheet set has been changed yet. Step 1 was reconnaissance plus one proof; the proof and the findings are
recorded here so the plan can be approved before building.

## Done (measured)

- Scene built on the workstation at this branch's base: `~/archpipe/work/RV2`, `/tmp/RV2-scene/scene.json`
  (631,583,581 bytes, sha256 `28bc8df3...54dacc`, 89 s build). Same bytes as lane P's earlier scene.
- Scene content relevant to drawings: `meshes` (1242) in groups `shell` (167, merged by material, mostly boxes, polygon
  faces, outward normals), `context` (68, neighbours and fence, to z 9), `ground` (52), `fixture` (355), `furniture`
  (288), `dressing` (312, 1.56 M faces, not needed). Metres; scene z: B floor -3.0, GF 0, L1 3.0, roof 6.0. Revit
  levels (use for annotation): B -1.80, GF +1.20, L1 +4.20, roof +7.20 (`ffl_revit_mm` = scene + 1.2 m). Fence top
  scene +1.0 = Revit +2.20. `shell-039-paving` spans +-60..100 m and must be clipped; `diagnostic_meshes` skipped.
- PROOF: Grease Pencil Line Art bakes headless in Blender 4.5.14 and strokes read back as world-space 3D points
  (`src/archpipe/blender/lineart_probe.py`, run on the workstation: `LINEART-PROBE ok strokes=7`, occluded edges
  removed). API facts (new GP type is `bpy.data.grease_pencils_v3`, modifier `"LINEART"`) are in that file.
- Available on the workstation venv: pytest 9.2, shapely 2.1.2, matplotlib 3.11.2, numpy, pymupdf. No scipy.
  DejaVu Sans (has Arabic presentation forms) is installed; the Windows fonts named in `plans.py` are not.

## Findings that change the existing sheets

1. **North is wrong in `documents/plans.py`.** It draws model +y up with an arrow labelled N. Client convention
   (memory `feedback_orientation_naming`): street side (model -x) = NORTH, +y = EAST, +x = SOUTH, -y = WEST. The old
   Revit furnished and lighting PDFs have the street at the top. Plan: rotate plans so N is up by mapping model
   (x, y) to sheet (y, -x) (a pure rotation), implemented as a transformed copy of the elements (wall endpoints, room
   polygons, tread boxes, rotations -90 degrees) so the existing drawing code is reused; true north (20 degrees, street
   facade 290 degrees) only as a labelled secondary on the site plan.
2. Paper and scale are module globals (A3, 1:100): add per-sheet paper and scale (A-302 full-length garden section does
   not fit A3 at 1:50; the A+ doc asks 1:50; plan: A-301 stair at 1:50 cropped, A-302 at 1:100 and the gap stated).
3. Stale text: `sheetset.GENERATOR` says elevations and sections "need Revit"; cover text and banner say "NOT REVIT";
   `tests/documents` asserts sheet order `[:3]` (breaks when the site plan is inserted).

## Plan (to be approved)

Engine split: Blender Line Art for visible projected lines (hidden-line removal is not hand-rolled); pure Python
(numpy, shapely) for the cut plane, poche, levels, dimensions and sheet composition, so tests need no Blender.

1. `drawings2d/scene_slim.py`: stream scene.json, keep architecture groups (shell, context, ground, architectural
   fixtures: glass, doors, stair details, railings), clip paving, write a small JSON (not committed).
2. `blender/lineart_view.py`: reads slim JSON plus a view spec (origin, direction, up, extent, cut plane), builds meshes
   (for a section, polygon-clips away the viewer side of the cut plane), bakes Line Art, writes strokes with depth.
3. `drawings2d/section.py`: cut-plane slice of the polygon soup, poche by shapely polygonize plus winding number
   (union of overlapping boxes, nonzero rule), line classes by depth (cut > projection > beyond), ground line,
   level markers with Revit elevations, key dimensions, room/space names on sections, grid bubbles.
4. Views: four elevations named N (street, model -x), E, S, W, each looking at the facade from outside; section 1 along
   the stair (plane y = -27.95, looking east = +y); section 2 through the sunken gardens (plane y about -22.2: cinema,
   guest WC, dirty kitchen, east garden and south garden). Callouts on the plans resolve to sheets (DS2).
5. Sheets: A-100 site plan, A-101/A-102 plans (fixed layout: larger plan, full room names), A-111/A-112 furnished plans,
   A-121/A-122 reflected ceiling and lighting plans with type tags and legend, A-201/A-202 elevations, A-301/A-302
   sections, A-601 schedules (add furniture schedule, luminaire schedule, finish schedule), cover with index and
   legend; combined `out/documents/D1/D1-set.pdf`; three PNG previews in `src/archpipe/documents/samples/`.
6. Tests: fixture geometry for slice, clip, poche (positive and negative), view naming/orientation (the four
   elevations map to the right model axes), sheet QA kept green.

## Parity targets from the old Revit outputs (read from `out/villa`)

| old output | what it communicated | planned replacement |
|---|---|---|
| `env-site-plan.pdf/png` | plot 28.93 x 19.13, street strip, neighbours with heights (12 m, 9 m sister), sunken yard -1.80, fence top +2.20, building footprint and rooms, grid, north arrow (true north), street facade bearing 290 | A-100 site plan from `context`, `garden`, `plant` elements and the scene `context` group; add set-back distances (EG3) |
| `env-view` plans B / GF | Revit plan views | A-101 / A-102 |
| `env-view` plan APT +4.20 (not ours) | apartment level | not ours: stated gap; could be drawn from the `L1` walls if the model carried them (it does not) |
| `env-view` 3D | perspective view | Blender renders (other lanes), not 2D |
| `furnish-d1/D1-furnished.pdf` (6 pp) | 2 furnished plans (street at top; rooms colour-coded; furniture boxes with labels; green clearance zones; orange doors; blue glazing; purple kept columns), furniture schedule (item, room, type, size, height, why), fit checks PASS list, decisions/notes | A-111/A-112 plus furniture schedule sheet; checks and decisions pages: carried from model params (`why`) or marked as gaps |
| `render-d1/D1-lighting-finishes.pdf` (5 pp) | 2 lighting plans with symbol legend (DL, DLN, ADJ, WW, PEN-GLOBE, PEN-LIN, SCONCE, STEP, COVE, BACK, UC, TOE, NL) with product codes, lux table (achieved vs required, PASS), "what makes it beautiful" per room, fixture table with product and lm/W | A-121/A-122 with the same legend and type tags; lux table and beauty table need lighting-lane data (`lighting-measurements.json`): include if the data is read from knowledge/, else stated gap; finishes: finish schedule from scene materials |
| `designs-r12` D1/D2/D3 plans, options PDFs, `Compare-D1-D3.pdf` | option comparison | D1 only is in this set; D2/D3 need their own model snapshots: stated gap |

## Revit 2D capabilities noticed that are not in the brief (candidates to add to the plan)

Schedules of every element class with live sorting/filtering (doors, windows, rooms, finishes, furniture, luminaires,
fixtures, areas); tags for every category (wall, ceiling height, spot elevations, spot coordinates, slopes, stair
number/riser tags, keynotes, material tags, area tags); view templates (one place for scale, line weights, visibility
by discipline); line-weight and line-style tables per view scale; material cut and surface hatch patterns (poche and
fills by material: concrete, masonry, plaster, glass, earth, insulation); area plans and gross/net area schemes
with colour-fill legends (room colour fill by occupancy or by finish, fire-compartment, daylight/shade);
detail callouts and enlarged plans/sections (stair 1:20, wet rooms 1:20, wall sections 1:20, details 1:5, per the A+
CD stage); detail components and keynote legends; revision clouds and revision schedule on every sheet; sheet
index, view list, drawing list schedule; print sets and PDF/DWG export settings (RV3 owns DWG); dependent
views and view-range control (plan cut height, view depth); linked-model display (neighbours, structure, MEP
overlays on plans); demolition/phasing graphics (existing vs new: the villa keeps existing columns); section and
elevation markers that update automatically with sheet/view numbers; project and shared parameters in title blocks;
scope boxes and crop regions; dimension styles with equality (EQ) and automatic chain dimensions; shadows and
sun-path study overlays on elevations (shade is a client priority); door/window swing and operation graphics;
stairs with UP/DN arrows and break lines; ceiling grids and slope arrows on RCPs; north point per view with
project/true north toggle; text notes and general-note blocks; legends (symbols, materials, line types);
scale bars; sheet revisions and issue/phase stamps. Items most likely to matter for this brief: schedules (incl.
finish and fixture schedules), material poche hatches, colour-fill room plans, revision table/clouds, enlarged
stair/wet-room callouts, and view templates (line weights).

## Next steps when resumed

Wait for the approved plan; then build steps 1 to 6 above, in order, committing and pushing `lane/RV2` after each.
Start with the plan orientation fix (smallest, fixes a client-visible error) and the slim-scene extractor, since the
Blender step depends on it.
