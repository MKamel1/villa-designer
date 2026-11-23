# GI: the decided garden in the PRODUCTION villa scene (2026-11-22)

Lane `GI`, branch `lane/GI`, from `lane/L6d` + `integ/aplus` (LDG star-jasmine layout and FG merged). Code: `src/archpipe/landscape/build/production.py` (adapter), `src/archpipe/blender/garden_ldb.py` (Blender
side), tests `tests/landscape/build/test_production.py`. Driver for look development: `python -m archpipe.landscape.build.tools.gi_scene OUT --dev` (receipts bypassed: diagnostic only).

## Why

The client reviewed LDB's previews ("very poor"): blank white walls, flat midday light, climbers like wallpaper, flat brown beds and beige gravel, a faceted BBQ and white-box benches, smooth egg plants.
They were drawn in an isolated preview scene (invented context boxes, a preview light rig). GI puts the garden into the scene the interiors use, so it is lit, exposed, framed and checked the same way.

## The hook

* `villa_render.GARDEN_SOURCE = "ldb"` and `villa_render.garden_ldb(mats, views, shell_meshes)` replace `villa_landscape.build(sp, lay)` in `_build`. The legacy path is kept behind `GARDEN_SOURCE = "legacy"`
  (its own G-series tests still run). `scene["garden_source"]` carries the switch.
* `production.garden()` builds `knowledge/landscape/concept/final/layout-final.json` (LDB `build_scene`, age 3) and returns `meshes`, `props`, `notes`, a minimal `plan`, `materials`. Element ids `ld-*` are kept (every mesh and
  prop declares `element_ids`); the visualisation layout is refused (`guard.refuse`, tested, no `ld-vis-*` in the scene).
* The house, facade, windows and doors, neighbours and street are the production scene's own: the preview's context boxes are NOT used. Only what the model does not hold is added: the plot fences the layout's own walls do
  not cover, and ground (ours, and a labelled neutral grey outside our yard).
* **Season and state per view.** A deciduous plant (crape, grape) is built twice under one id (`ld_season` summer / winter) and a view dated Dec-Feb (`production.season_for`) hides the leaf-on meshes, any other date the leaf-off;
  the fire-pit cover is built closed and open (`ld_state`), a view hides the one it does not show (`view_hides`, appended to the view's `hide_meshes`; the variants are `keep_object` so the renderer never merges them).
* **Blender side** (`villa_scene.py`, three small hooks): `add_material` -> `garden_ldb.apply_look` for a spec naming `garden_look` (water, pond liner, weathered render, matte stand-ins, leaf cut-outs); after `build_meshes`
  -> `garden_ldb.finish_meshes` (UVs of leaf cards, water reduced to its top face, stand-in masses smooth); `import_props` -> `garden_ldb.import_prop` (Fab FBX with the archive's maps and the **red-channel** opacity/roughness
  wiring of `fab_blender.py`, glTF, placed by height / xyz / box / fish, base centroid seated on the layout point, placement measured).
* **Other guards that had to know the garden changed** (each a minimal, commented gate; two are outside GI's paths and are listed under decisions): `villa_render_contract.validate_scene` skips the G-series sun / G6 / north-court /
  swing / G4d records when `garden_source == "ldb"` (they describe the previous garden); `final_mounting.apply` skips the previous garden's retired rows; the production shell's own yard floor (shell-039) is cut back under the
  garden's surfaces and ponds (`production.reveal_ground`, same routine the previous garden used for soil beds); `villa_landscape.PROP_BOUNDS` also reads `knowledge/landscape/build/ldb-prop-bounds.json` (written by
  `python -m archpipe.landscape.build.production`, a test keeps it current) so the geometry-topology review sees the garden assets at their built size.

## Fixes 1-5 (what, and from where)

| # | defect (lead review) | fix | source / licence |
|---|---|---|---|
| 1 | huge blank white walls; no coping, weathering, facade | walls in the house's own exterior colour (production `paint-exterior-grey-green`) on a textured render (library **Plaster003**, ambientCG CC0) with a weathered foot band, soft stains and run-off streaks in the shader; **stone coping** 60 mm with 40 mm overhang on every wall (`elements.coping`, own object); the **real facade, windows and doors** come from the production scene; a stucco look chosen after LOOKING at it (the first choice, Poly Haven `white_rough_plaster`, is peeling paint) | library Plaster003 (CC0); coping geometry ASSUMED |
| 2 | flat light | production sky, **production exterior exposure groups** (below); no preview rig | measured, not by eye |
| 3 | climbers = wallpaper | **3D leaf cards** on woody stems, 0.015-0.20 m off the face (`planting._climber_cards`): star jasmine from the **15 live real leaf cut-outs** of LDL's Megascans atlas (Opacity red channel; 5 dead leaves dropped), per-leaf tone; every other climber a labelled STAND-IN card set (generic oval leaf, ASSUMED size). Leaves are closed 0.4 mm solids (the scene admits solids only) with UV windows; a card set without UVs now raises (it rendered black once). Grape has a leaf-off geometry (stems only) | Megascans star jasmine via Fab (client download, Fab Standard) |
| 4 | flat brown beds, beige gravel | **mulch** (Poly Haven `wood_chip_path`, CC0, 2k) with a stone-scale bump, **steel edging** 4 mm, 15 mm proud (`elements.edging`), **gravel** (library `gravel_ground_01` + chip bump), bare ground (Poly Haven `park_dirt`, CC0), paving units on honed travertine texture at low contrast so it draws no second joint pattern. **Groundcover filling was NOT invented**: the layout plants none at density and a groundcover would be an invented planting (open item for LDG) | Poly Haven CC0 (`tools/fetch_gi_assets.py`) |
| 5 | faceted BBQ, white-box benches | **BBQ = Sketchfab "Charcoal Grill" (newArteest, CC-BY 4.0)**, a kettle on a wheeled tripod, 0.95 m, graded B (`outdoor-assets.json`, role `bbq`); **benches** = rendered plinth under **hardwood slats** (70 mm, 12 mm gaps, teak texture) | Sketchfab CC-BY: credit "Charcoal Grill by newArteest, CC-BY 4.0" |
| 6 | smooth egg plants | still labelled STAND-INS (no foliage invented): **matte** (specular 0, roughness 1, no sheen), two-scale tonal variation, albedo at ASSUMED 0.5 of the display colour, sized by the layout spread and the policy growth fraction | |
| 7 | crape candelabra | left as the labelled stand-in; both leaf states exist and the view date picks one | |

## Rules applied that the layout did not carry (and the one it now does)

* Star jasmine away from seats and herbs, Arabian jasmine by them (client 2026-11-22): `build_scene(..., star_jasmine=True)` swaps a climber's `jasminum_sambac` for `trachelospermum_jasminoides` when it stands >= 2.0 m (POLICY, ours)
  from every seat (benches, table + chair ring, pot, herb bed). LDG's updated layout now names star jasmine itself (6 individuals), so the swap stays off for it (`has_star`: the layout is authoritative); the rule remains for older layouts.
* Stand-in count (age 3, 101 plants): **59 labelled stand-ins, 42 drawn from graded assets** (Fab FBX 29: aspidistra 21, red fountain grass 3, oregano 2, olive 2, + palms / frangipani / pomegranate 7; star jasmine climbers 6
  as atlas-built leaf cards). Stand-in species: acorus 20, farfugium 8, jasminum sambac 10 (climbers), justicia 6, petrea 6 (climbers), salvia 3, fatsia 3, grape 2 (climbers), crape 1. Earlier LDB figure 60/96.
* FG (generated foliage, client-approved after the brief) is NOT integrated: the brief said keep the labelled stand-ins. Its integration note is the recipe (`foliage.library.plant_for` + `blender_build.build_plant` inside the job,
  `state` leaf-on / leaf-off); the per-view season machinery here is what it would plug into.

## Exposure

EXPOSURE_SECTION

## Previews, critic, honest reading

PREVIEW_SECTION

## Receipts and scene hashes

RECEIPT_SECTION

## Decisions (no human was available)

1. **Old garden fully replaced**, including its top (ground-floor) garden and the hanging swing: the decided layout is the garden-level garden only. v25/v26 (top garden) now show the bare ground-floor terrace; v39 (swing) shows the north court.
   Their `subjects` / captions were re-pointed (the authored ones named meshes that no longer exist) and each caption says so.
2. **Cameras**: the placeholder cameras were authored for the old garden. A camera inside or touching a garden solid is moved the least distance (`production.clear_camera`, 0.1 m grid, within 3.5 m) to 0.6 m clearance, the move recorded in
   the camera's `overrides`; one placeholder (v40) was inside a stand-in mass and rendered black. Nothing else about the placeholder set was changed (no re-framing).
3. **Key views** added to `VIEWS(lay)` (so the production scene and its exposure record carry them): `gi-living-door`, `gi-dining-firepit`, `gi-north-court-pond`, level 24 mm at the production eye height (1.35 m; seated 1.25 m at the table).
4. **Two edits outside GI's paths**, both minimal gates keyed on `garden_source == "ldb"`: `src/archpipe/villa_render_contract.py` (the five old-garden validators) and `src/archpipe/concept/final_mounting.py` (retired landscape rows). `lane_guard` will list them.
5. Garden group names: surfaces `ground`, benches/table/chairs/BBQ/pot `furniture`, everything else `dressing`; **never `shell` or `context`**, which the furniture receipts hash as architecture.
6. Part kinds the physical-part guard admits (`finish-layer`, `planter-soil`, `plinth`) for the rectangular finishes, closed thin solids for leaves and ground, the water as a closed solid whose sides Blender drops.

## Open items

OPEN_SECTION
