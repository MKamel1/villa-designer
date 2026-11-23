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

The garden views use the production exposure groups of `knowledge/exposure-group-rule.json` (dominant light: lamps > 0.5 -> lamp-dominant; exterior-day with solar fraction <= 0.5 -> exterior-shade; evening / dusk presets
preserved), **measured, not set**: the production scene was built with `write(measure_exposure_groups=True)`, the Blender probe run through jobq (`GI-measure-exposure-3`, GPU, `villa_scene.py --views none
--measure-exposure-groups`, scene with ERCO IES, 46 views), the output copied byte-for-byte to `knowledge/exposure-groups.json`, and `write()` then accepted it (`require_record`). Results for the garden:

| group | members (garden) | locked EV100 | white balance |
|---|---|---|---|
| exterior-day | v19 v25 v26 v27 v28 v36 v38 v39 v40 v41, gi-living-door, gi-dining-firepit, gi-dining-crown-summer / -winter (14) | 13.53 | 5500 K |
| exterior-shade | v37-north-garden-lounge, gi-north-court-pond (solar fraction 0.47 / 0.46 <= 0.5) | 9.49 | 5500 K |
| exterior-dusk | v07-terrace-dusk, v42-north-garden-evening | 0.61 | 4300 K |

Consequences stated, not tuned: the deep-shade north court views v36 and v39 fall in exterior-day (solar fraction 0.61, 0.66 > 0.5: their sky patch is bright) and render near-black at that lock; the dusk lock is set by the darker
of its two views, so v07 is over-exposed. `render_qa` on every garden image is run (`tools/gi_qa.py`, the same checks `scripts/villa_render.py` runs); no exposure was changed per view.

## Previews, critic, honest reading

Draft = Cycles GPU, 64 samples, 1920 x 1280; the three key views at **256 samples** (jobq `GI-final-draft-1`, `GI-final-key-1`); scene `out/gi/final/scene.json` (production build, receipts and record active). JPEGs (1500 px) and the
`render_qa` / caption / critic records are in `knowledge/landscape/build/production/{draft,key}/` (PNGs stay in `out/gi/final/`). The L3 critic (`frozen-v1` rubric, Ollama VLM through jobq, `scripts/critic_vlm_batch.py` then
`critic_run.py --vlm DIR`) was run on every image; **only gi-living-door passes** (R8 asset fidelity warns on it). I looked at every image myself; the reading below is mine, the critic's findings agree.

| view | group | EV100 | spp | render_qa | critic | what I see, honestly |
|---|---|---|---|---|---|---|
| `gi-dining-firepit` | exterior-day | 13.53 | 256 | pass | fail (2 WARNs (R10, R8) escalate to FAIL) | Looking along the table to the fire pit and the west screen opening: real facade, sunlit; slab paving with the flush fire-pit cover as a plain disc; leaf-card trellis; BBQ; two big egg stand-ins in the left bed. The white facade fills the upper right (critic R10). |
| `gi-living-door` | exterior-day | 13.53 | 256 | pass | pass | From the living door: textured pale-green render wall with coping, a dense leaf-card wall (generic stand-in leaves, dark green) and a star-jasmine trellis (yellow-olive real leaf cut-outs), real BBQ, free table and chairs, slab paving, two smooth matte egg stand-ins and a real lady palm. The 4 m wall above the planting is still a large blank plane. |
| `gi-north-court-pond` | exterior-shade | 9.49 | 256 | pass | fail (score 0 on R12 (hero view); 2 WARNs (R10, R11) escalate to FAIL) | Pond from the lounge side: dark water, fine mesh grille, flush dark lip, mulch bed with steel edging, lady palm (asset), star-jasmine card wall, a row of green sphere stand-ins on the pond edge, a 2 m capsule stand-in cut by the frame. |
| `gi-dining-crown-summer` | exterior-day | 13.53 | 64 | pass | fail (score 0 on R11, R12, R8 (hero view)) | October: the crape stand-in leaf-on (translucent fuzzy balls on straight limbs), star jasmine and stand-in walls, plumeria in flower at the left edge. |
| `gi-dining-crown-winter` | exterior-day | 13.53 | 64 | pass | fail (score 0 on R11, R12, R3 (hero view); 2 WARNs (R10, R8) escalate to FAIL) | January, same camera: leaf-off crape (straight pole limbs and twig tufts, a candelabra), lower sun moves the wall shadow, evergreens unchanged. Proves the per-view season; the bare tree itself still reads as a diagram. |
| `v07-terrace-dusk` | exterior-dusk | 0.61 | 64 | FAIL: colour_cast | fail (score 0 on R12, R3, R4 (hero view); 3 WARNs (R10, R11, R8) escalate to FAIL) | Dusk view from inside the crape crown: washed out, hazy and cold (cast 0.06 against 0.02): the dusk lock is set by the darker north-court view, so this brighter view is over-exposed. |
| `v19-garden-facade` | exterior-day | 13.53 | 64 | pass | fail (score 0 on R3 (hero view); 4 WARNs (R10, R11, R4, R8) escalate to FAIL) | Camera nudged out of the wall corner; looks through the crape crown (stand-in) at the real facade with its real sliding window. Facade is the production white plaster in direct sun (bright but not clipped at the group exposure). |
| `v25-top-garden-gate` | exterior-day | 13.53 | 64 | pass | fail (score 0 on R11 (hero view)) | Ground-floor terrace: the decided layout has no planting up here, so the view shows the production terrace floor (small cobble mosaic), parapet and neighbours. Not a garden view any more. |
| `v26-top-garden-east` | exterior-day | 13.53 | 64 | pass | fail (score 0 on R11 (hero view)) | Same terrace, east end. No garden content. |
| `v27-east-yard-above` | exterior-day | 13.53 | 64 | pass | fail (score 0 on R10, R11, R3, R4 (hero view)) | East yard: real dark pond with the fine grille, bench, mulch beds, real facade glazing. A 2.3 m dark stand-in capsule (fatsia) fills the left third: the stand-in problem at its worst. |
| `v28-east-yard-below` | exterior-day | 13.53 | 64 | FAIL: crushed_shadows | fail (score 0 on R10, R4, R8 (hero view)) | East yard from the pond end: wall, pond edge, facade and glazing read well; the same capsule stand-in dominates; 17 % of pixels near black in the shaded wall side (render_qa crushed shadows). |
| `v36-north-garden` | exterior-day | 13.53 | 64 | FAIL: crushed_shadows | fail (score 0 on R10, R4 (hero view); 2 WARNs (R11, R8) escalate to FAIL) | North court bench and paving in deep shade at the exterior-day lock: mostly black (11 % near black). The court faces a 9 m house wall; low light is real, the group assignment (solar fraction 0.61 > 0.5) is the rule's. |
| `v37-north-garden-lounge` | exterior-shade | 9.49 | 64 | pass | fail (4 WARNs (R10, R11, R12, R8) escalate to FAIL) | North court through the lounge glass at the exterior-shade lock: balanced. Dark pond with fine grille (reads as a floor grate; no koi visible), mulch bed, star-jasmine card wall, stand-in capsules and spheres along the pond edge, glass reflections. |
| `v39-north-garden-hanging-retreat` | exterior-day | 13.53 | 64 | FAIL: crushed_shadows | fail (score 0 on R10, R11, R4 (hero view); not evaluated: R12 (fail closed)) | The hanging swing no longer exists; the camera now faces a blank shaded wall (8 % near black). The view has lost its subject. |
| `v40-south-garden-espalier` | exterior-day | 13.53 | 64 | pass | fail (score 0 on R4 (hero view); 2 WARNs (R10, R8) escalate to FAIL) | Best of the set: potted frangipani (graded asset, real flowers), star jasmine cards on the wall, mulch bed with edging, bench with slat seat. The espalier it was authored for is gone. |
| `v41-south-garden-terrace` | exterior-day | 13.53 | 64 | pass | fail (2 WARNs (R11, R8) escalate to FAIL) | Dining table and chairs (free assets), crape stand-in (leaf-on), star jasmine and stand-in leaf-card walls, BBQ, paving, coping, real wall and sky. The overall reading is plausible; the leaf walls read as hedges (uniform stand-in leaves), the crown as fuzzy balls. |
| `v42-north-garden-evening` | exterior-dusk | 0.61 | 64 | FAIL: colour_cast | fail (score 0 on R12 (hero view); 2 WARNs (R10, R11) escalate to FAIL) | Dusk at the exterior-dusk lock: cool blue cast (0.09 against a limit of 0.05), pond grille and card walls visible; no garden lighting of the decided layout exists, so nothing is lit. |


What still reads as fake, with its cause:
* **Stand-in plants** (59 of 101): smooth matte eggs, capsules and spheres. Cause: no graded asset for 11 species; the brief forbids inventing foliage; FG (approved later) is not integrated. Matte and correctly sized now, still unmistakable.
* **Climber walls**: dense, uniformly coloured oval leaves on a flat plane of stems; no flowers, no wall visible through the leaf mass; star jasmine (the only real-leaf species) olive-yellow. Cause: generic stand-in leaf (ASSUMED
  size, one shape); layout climber widths from policy; the atlas has only 15 live leaves.
* **The 4 m walls** remain big blank planes above 1.5-2 m planting; the weathering is only readable in the foot band and in raking light. Cause: the layout fixes 4 m walls and age-3 climbers 1.3-1.9 m; no wall architecture is specified.
* **Pond**: reads as a dark floor grate; the koi are not visible through the 50 mm grille and the water reflection; the water is a flat surface with a ripple bump. Cause: POLICY grille at 44 mm aperture on a 6 mm bar, camera angles, no caustics.
* **Crape**: both states exist but the limbs are straight poles and the crown fuzzy translucent balls (candelabra); the olive is the Fab scan (reads fine). Cause: generic stand-in tree (FG would replace it).
* **Paving**: honed slabs with flush joints read clean and flat; no wear, no edge chips, the flush fire-pit cover is a plain disc. Cause: ASSUMED detail level.
* **House facade**: the production white plaster blows to near-white in direct sun at the exterior-day lock and fills the upper frame in the dining view (critic R10). Cause: the shell's exterior finish is its interior white (`plaster-warm-white`), not
  the grey-green exterior paint the boundary walls use (RF / L6d scope).
* **Placeholder cameras** (v19, v25, v26, v27, v28, v36, v39): authored for the old garden; several now look through a crown, into a stand-in mass, at a terrace with no garden or at a blank wall.
* **Light**: hard 10:30 sun (40 degrees) from the production sky; north court in shade at that lock; no garden lighting exists for the decided layout (the previous garden's G4d fittings are still in the scene at their old positions).

## Receipts and scene hashes

Receipts (`knowledge/furniture-stage2.json.gz`, `parents-bed.json.gz`) were regenerated by the RA method, baseline-relative, in this order: (1) diagnostic exports with the receipts bypassed of the base tree (`20c01e4`, git worktree)
and of this tree (`scripts/refresh_furniture_integ5.py export`); (2) `knowledge/approvals-review/section_diff.py`: **the old tree reproduces all eight stored section digests**; layout, specification, furniture, meshes, models, props
**unchanged**; **materials changed: 31 `garden-*` finishes added, 0 removed, 0 changed**; **architecture changed: 253 faces removed / 368 added, every one a finish-layer face of the shell yard floor (paving and stone-substrate at z = -3.0)**,
cut back under the garden's surfaces and ponds, **0 unexplained**; (3) `review-current`: **16 individual + joint baseline-relative reviews, all ok, 0 relative findings**; (4) `refresh_receipts.py` (now writes a second record `refresh_2026_11_22_GI`
beside the first). Evidence: `knowledge/approvals-review/evidence-gi/`. Visual approvals are retained (no room look changed).

Production build with every receipt and the exposure record active, no bypass (`VR.write`): | | |
|---|---|
| `scene.json` (clean tree, HEAD `e792c538`, `git_dirty` false) | 300,962,796 bytes, sha256 `41288e1c9fdb145c15ccbeca94a248c5f61eb5ccb729a1ff490496d3997c8239` |
| ids stripped, provenance removed (`json.dumps(without_ids(scene minus provenance), sort_keys=True)`) | sha256 `558894802ba41acb6ec146f291e1db32f8021eb2cd717b2baac3bec0c724218a` (**identical** to the scene the images were rendered from, built on a dirty tree at `9c1a273`) |
| ids stripped incl. provenance | sha256 `38c7ea8a2bd9a6250799e367b1dc56c8ff25adff48757c19e4d9d876115c033b` |
| meshes / props / views | 1,298 / 80 / 46 |
| `source_hash` | `2d3afbaa4ca0c2bc16016eada416071b9cb18638f297e6fba2fcf195589dab8d` (build 83 s, linux) |
| exposure record | `knowledge/exposure-groups.json`: measurement_sha256 `89f73ea27b41e5b83b0c1fcb30736028a1973dc6f2aaff0c352ccb292c006ee5`, transport_sha256 `8322654bf3b66e2149036fbcb34aef378df629bdc617864f21d885a81ad34284` |
| receipts | `furniture-stage2` room_context `53ac20c763a7ef0b...`, `parents-bed` `665f87ad0ccb7739...` |

The file hash includes `provenance` and is tied to the build's checkout; the content hash above is not.

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

 1. **FG integration** (generated foliage, client-approved after the brief): would replace the 59 stand-ins and the candelabra crape. Plug-in points exist (per-view season, `import_prop` placement, material hooks); not done by instruction.
 2. **Cameras**: re-author the placeholder views for the decided garden (v19, v25-v28, v36, v39 especially); v25/v26/v39 need a decision (no garden up there; the swing is gone).
 3. **Exposure of the north court**: v36 / v39 sit in exterior-day (solar fraction just over 0.5) and render near-black; the dusk lock over-exposes v07. A rule question for the lighting lane, not a per-view change.
 4. **Garden lighting** of the decided layout (L6): none; the previous garden's G4d fittings remain at their old positions.
 5. **Groundcover / planting density** at age 3 is the layout's (LDG): beds show mulch between sparse plants.
 6. **Facade finish**: the house exterior is the interior white plaster; boundary walls use the exterior grey-green. One finish should be chosen (RF / L6d).
 7. **Design model** (`model/api.py`, not GI's) still derives the garden from `villa_landscape.build`; `LAND.build` -> the decided garden is a one-line change for the lead (the scene already carries `ld-*` ids and `plant-ld-*` model ids via `_live_model_ids`).
 8. **Lane guard**: two files outside GI paths were edited (decision 4); `lane_guard GI` lists them.
 9. **Tests not green, none caused by GI**: `tests/lightverify/test_v10_erco.py` (3) and `test_v1_design.py::test_bound_pendant_is_one_emitter_at_its_record_flux` (LV pins of the old pendant; fail on the base tree too);
    `tests/ops/test_jobq.py::...gpu_job_in_submit_order_but_cpu_in_parallel` (fails on the base tree too: the live runner's VRAM gating).
10. **Interleaving**: RF and LV had not landed in `integ/aplus` at hand-back time; when they do, take their receipt and exposure files, regenerate (this doc's procedure), re-measure exposure with a new jobq id, rebuild.
