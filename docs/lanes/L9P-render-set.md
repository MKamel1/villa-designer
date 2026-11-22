# L9P: final still-render set, critic gate, draft pass

Lane `L9P`, branch `lane/L9P`. Date 2026-11-22. Data: `knowledge/render-set/` (views, exposure record), code `src/archpipe/critic/render_set.py`, `extension.py`.

## 1. Camera set (48 views: 36 interior, 12 garden placeholders)

Source of truth is `knowledge/render-set/views.json` (purpose of every view is a field). `villa_render.py` and `villa_scene.py` are L6d's, so the set is data and `render_set.resolve()` turns it into the `views` list that `villa_render.build(views=...)` accepts; `render_set.write_scene()` is `villa_render.write()` with a record-path argument.

**What the render script must read (for L6d):** (a) `render_set.load()` + `resolve(data, lay, VR.VIEWS(lay))` for the `views` argument; (b) the exposure record `knowledge/render-set/exposure-groups.json` instead of `knowledge/exposure-groups.json` (the old record is bound to the old 41-view inventory and fails `require_record`); (c) one line in `write()`: take a `group_record` path. Until then call `render_set.write_scene`.

Every one of the 30 rooms of the design model is covered by at least one 24 mm view: `render_set.coverage()` checks each declared room against the camera's field of view on plan (a wrong `covers` is dropped), `test_real_set_covers_every_room_at_24mm` fails otherwise. No interior view uses a lens under 24 mm: the old 16 mm views (v01, v12, v15, v16, v17, v20, v32, v35) were replaced by single-subject 24 mm views (`n02`, `n15`, `n17`, `n08`, `n09`, `n03`, `n14`, `n21`). Camera checks (`scripts/villa_render_views.py` on the set's scene): no new problem; the only line is the existing `v27-east-yard-above` garden camera 0.2 m from a wall.

Day and dusk: living (v02/v10), lounge (v03/v21), dining (n01/v09), kitchen (n02/n03), parents' bedroom (n13/v05), study (n11/n12; same frame, two states), south terrace and north garden dusk placeholders (v07, v42). Single-state rooms are wet rooms, stores and the kids' rooms (one view each, as before).

| id | kind | rooms covered | purpose |
|---|---|---|---|
| v33-basement-north-south | reuse | living, dining, kitchen | Basement open plan, living end from the north: hero day view (audit B-) |
| v34-basement-south-north | reuse | bar-alcove, living | Basement open plan from the bar alcove looking north: hero day view (audit B) |
| v02-garden-living | reuse | living | Garden living by day: sofa and library toward the south garden (audit C+, camera kept) |
| v10-living-evening | reuse | living | Garden living at dusk: cove lighting and library (audit C+, camera kept) |
| v03-street-lounge | reuse | lounge, family | Street lounge by day: sofa and TV (audit D for exposure, not camera) |
| v21-lounge-evening | reuse | lounge | Street lounge at dusk (audit B-) |
| v09-dining-evening | reuse | dining, kitchen-island | Dining and island at dusk (audit C+, camera kept) |
| n01-dining-day | new | dining | Dining table by day (new: dining had only a dusk view) |
| n02-kitchen-island-day | new | kitchen, kitchen-island | Kitchen island by day at 24 mm (v01 was 16 mm, C-, pendant cropped) |
| n03-kitchen-run-evening | new | kitchen | Kitchen run at dusk at 24 mm (v20 was 16 mm, C) |
| n04-library-nook-evening | new | bar-alcove | Library and daybed nook at dusk, camera inside the alcove (v24 stood behind the drape, C) |
| v08-cinema | reuse | cinema | Cinema: seating and screen (audit D; camera 24 mm already) |
| v29-under-stair-store | reuse | stair-b, lounge-nook | Under-stair storage from the lounge (audit F for exposure) |
| v30-under-ramp-store | reuse | store-ramp | Under-ramp store shelving (audit F) |
| n05-pantry-evening | new | pantry | Pantry shelving (new: room had no view) |
| n07-family-corner-day | new | family, lounge | Family / TV corner and lounge from the kitchen edge (new: room had no view) |
| n06-stair-foot-hall-evening | new | hall-b, family | Stair-foot hall looking north into the family corner (new: room had no view) |
| n08-guest-wc-evening | new | guest-wc | Guest bathroom WC and basin at 24 mm (v16 was 16 mm, D+, 30 % occluding wall) |
| n09-dirty-kitchen-day | new | dirty-kitchen | Dirty kitchen run at 24 mm (v17 was 16 mm, C) |
| v11-stair-void | reuse | stair-b, stair-gf, hall-b | Stair up through the void (audit C: mostly blank wall; kept for the draft pass to judge) |
| n10-gf-hall-east-day | new | corridor, gallery-end | Ground-floor hall looking east from the stair gallery to the parents' door (v23 looked west at a blank wall) |
| n18-stair-gallery-day | new | stair-gf, landing-gf, gallery-end | Stair void, landing and gallery from the gallery end (new: GF stair rooms had no 24 mm view) |
| n19-entry-lobby-evening | new | entry-b | Entrance lobby looking in from the core door (new: room had no view) |
| n20-dining-side-day | new | dining-side, dining | Dining party side and sideboard (new: room had no view) |
| n11-study-desks-day | new | study-game | Study desks at the windows (v04 stood behind armchairs, C-) |
| n12-study-sofa-evening | new | study-game | Study sofa at dusk seen from the front (v18 showed the sofa back, C-) |
| v06-kids-room | reuse | kids-a | Kids' room A by day: bunk and desk (audit D+ for asset quality) |
| v13-kids-b | reuse | kids-b | Kids' room B at bedtime (audit D+ for asset quality) |
| n13-parents-day | new | parents-bed, parents-entry | Parents' bedroom by day (v22 cropped the headboard, D+) |
| v05-parents-bedroom | reuse | parents-bed | Parents' bedroom at dusk: best interior mood (audit B-) |
| v31-dressing-hers | reuse | parents-dressing | Dressing room, her section (audit C) |
| n14-dressing-his-evening | new | parents-dressing, parents-dressing-ext | Dressing room, his section at 24 mm (v32 was 16 mm, C-) |
| n15-ensuite-bath-evening | new | parents-ensuite | Parents' ensuite bath at 24 mm (v12 was 16 mm, D+) |
| n16-ensuite-basin-day | new | parents-ensuite | Parents' ensuite basin (new second angle) |
| n17-family-bath-basin-day | new | family-bath | Family bathroom basin at 24 mm (v15 was 16 mm, D, blue cast) |
| n21-family-bath-wc-day | new | family-bath | Family bathroom WC wall at 24 mm (v35 was 16 mm, D+, door slab filling the right third) |
| v19-garden-facade | garden placeholder | - | PLACEHOLDER until LDB: south garden pergola by day |
| v41-south-garden-terrace | garden placeholder | - | PLACEHOLDER until LDB: south terrace by day (audit B-) |
| v40-south-garden-espalier | garden placeholder | - | PLACEHOLDER until LDB: espalier wall |
| v25-top-garden-gate | garden placeholder | - | PLACEHOLDER until LDB: top garden from the street gate |
| v26-top-garden-east | garden placeholder | - | PLACEHOLDER until LDB: top garden east |
| v27-east-yard-above | garden placeholder | - | PLACEHOLDER until LDB: east court from above |
| v28-east-yard-below | garden placeholder | - | PLACEHOLDER until LDB: east yard at basement level |
| v36-north-garden | garden placeholder | - | PLACEHOLDER until LDB: north garden shade planting |
| v37-north-garden-lounge | garden placeholder | - | PLACEHOLDER until LDB: north garden through the lounge glass |
| v39-north-garden-hanging-retreat | garden placeholder | - | PLACEHOLDER until LDB: balcony hanging retreat |
| v07-terrace-dusk | garden placeholder | - | PLACEHOLDER until LDB: south terrace at dusk (retired flag in scene; set aside for the dusk garden) |
| v42-north-garden-evening | garden placeholder | - | PLACEHOLDER until LDB: north garden at dusk |

Garden views are the existing 10 day views plus the 2 dusk views, unchanged, **placeholders until LDB**.
