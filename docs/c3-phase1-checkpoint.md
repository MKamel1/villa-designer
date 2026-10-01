# C3 phase 1 checkpoint

Real scene: `villa_render.build()` on the D1 example. This is a diagnostic collection run; strict construction raises on the first failure. No scene geometry, layout, material or camera was changed.

903 visible mesh records; 632 failing records. A record may have several reasons. The full per-part evidence is in `out/c3-part-failures.json`.

| Part kind | Failures | Room counts |
|---|---:|---|
| fitting-assembly | 272 | bar-alcove 9, cinema 10, corridor 15, dining 7, dining-side 6, dirty-kitchen 22, entry-b 4, family 4, family-bath 7, gallery-end 2, guest-wc 7, hall-b 4, kids-a 5, kids-b 5, kitchen 26, kitchen-island 4, landing-gf 2, living 10, lounge 15, lounge-nook 3, pantry 4, parents-bed 14, parents-dressing 4, parents-ensuite 12, parents-entry 2, stair-b 35, stair-gf 6, store-ramp 12, study-game 16 |
| building-shell | 143 | bar-alcove 5, cinema 4, corridor 5, dining 3, dining-side 3, dirty-kitchen 3, entry-b 4, family 3, family-bath 4, gallery-end 4, guest-wc 2, hall-b 3, kids-a 4, kids-b 3, kitchen 4, kitchen-island 3, landing-gf 4, living 8, lounge 5, lounge-nook 4, pantry 5, parents-bed 5, parents-dressing 5, parents-dressing-ext 3, parents-ensuite 6, parents-entry 4, stair-b 1, store-ramp 2, study-game 4, unassigned 30 |
| site-context | 67 | unassigned 67 |
| landscape-element | 38 | unassigned 38 |
| furniture-assembly | 37 | bar-alcove 1, cinema 2, dirty-kitchen 1, family-bath 3, guest-wc 3, kids-a 3, kids-b 1, kitchen 1, living 1, lounge 2, lounge-nook 4, parents-bed 2, parents-ensuite 1, stair-b 2, store-ramp 7, study-game 3 |
| dressing-object | 22 | kids-a 1, parents-dressing 7, parents-dressing-ext 14 |
| plant | 12 | unassigned 12 |
| book | 8 | bar-alcove 8 |
| box | 7 | kitchen 1, lounge-nook 1, parents-dressing 3, parents-dressing-ext 2 |
| lamp-head | 5 | cinema 2, kids-a 2, kids-b 1 |
| climber | 4 | unassigned 4 |
| rain-head | 4 | guest-wc 2, parents-ensuite 2 |
| trellis | 4 | unassigned 4 |
| suitcase | 3 | stair-b 1, store-ramp 2 |
| fan-grille | 2 | dirty-kitchen 1, guest-wc 1 |
| riser-rail | 2 | guest-wc 1, parents-ensuite 1 |
| shower-head | 2 | guest-wc 1, parents-ensuite 1 |

## Boundary

`Part(kind, solid, local_axes, material, basis, support)` is the constructor in `src/archpipe/concept/physical_part.py`. The scene uses `PartMeshList` for every mesh append and extend. Strict mode is `villa_render.build(collect_part_failures=False)`; default collection mode is temporary for this checkpoint. The kind comes from authored identity and is attached to each mesh as `part_kind`. Imported glTF products use the `measured-gltf` basis and remain under C2 intake. The constructor rejects rectangular proxies except approved box kinds; procedural solids must have nonzero triangle area, matched directed edges and outward signed volume. Duvets with a declared mattress support must remain inside its footprint.

The current scene also exposes many open building surfaces and combined assemblies at this strict solid boundary. These are counted as failures; the checkpoint needs a decision about how building surface assemblies are represented as closed construction solids. No exception was added for them.

The current `cloth` scene records are simulation instructions, not mesh records, so they are absent from the 903-mesh table. The duvet constructor checks a declared mattress footprint and support top when a solid is supplied; phase 2 must apply the same check to the evaluated cloth mesh after simulation. Imported glTF references are likewise validated through C2 intake rather than reconstructed from this scene's mesh list. This report therefore describes the authored procedural mesh boundary, not every final Blender triangle.

## Existing rectangular-solid admissions for review

| Kind | Physical reason |
|---|---|
| cabinet-carcass | Planar cabinet boards and rectangular enclosure are the finished joinery shape. |
| shelf | A straight shelf is a rectangular board with stated thickness. |
| worktop | A straight worktop is a rectangular slab with stated thickness. |
| wall-panel | A flat wall panel is a rectangular construction layer. |
| plinth | A joinery plinth is a rectangular support block. |

These entries are proposed for lead approval. No additional kind will be admitted to make the present scene pass.

## Phase 2 plan

1. Replace climbers and plants with measured glTF products through `asset_intake.py` or branched procedural growth; replace flat garments with hanger-supported draped forms and towels with rolled or folded cloth geometry.
2. Replace rain heads with circular bodies and nozzle faces; add the riser slider and hose, shaped hand shower and louvred fan grille. Review the guest shower fittings and v16 view in R3b-7b.
3. Give books spines, pages and varied dimensions; give storage boxes lids and seams and suitcases handles, wheels and measured proportions. Replace lamp heads with closed housings and diffusers. Review beds, desks and wardrobes in R3b-8.
4. Close shell and landscape construction surfaces as actual assemblies and split combined furniture meshes into typed components. Repair winding, zero-area triangles and duvet support violations at their source builders.
5. Preview each new visible kind before integration; then switch the scene to strict construction and rerun the real scene, regression tests and project verifier.

C2 files were not changed. `hanging_picture_frame_01` remains a known empty black frame without artwork; its imported mesh is outside this procedural mesh report. The unrelated v07 terrace dusk colour cast finding remains untouched.
