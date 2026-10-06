# C3 phase 2b — Chunk B checkpoint

This is a code and geometry checkpoint. No commit was made. The scene source was rebuilt on 2026-10-01. Photographic lead review is still required; no real villa design gate is approved.

## Changes and assumptions

- The guest bathroom and dirty-kitchen ducts remain in the Revit services specification, with their original fan and facade route. Their uncoordinated rectangular render proxies are omitted because the route belongs in the ceiling void. An **ASSUMED 130 mm white round ceiling extract valve** is shown at each fan position, flush below the finished plane; the external louvred grilles remain.
- The guest drain is **ASSUMED 70 mm wide**, because the former 20 mm strip was unreadable as a tile-in grate and no product has been selected. Its length and wet-zone edge location remain; the outer edge aligns with the wet-zone boundary. The Revit input and render read the same dimensions. Falls and waterproofing remain unmodelled.
- Dressing rails are closed brass tubes with end brackets. Storage boxes have separate lids and handles. Suitcases have a lidded body, outward carry handle and wheels; **ASSUMED maximum 550 × 350 × 300 mm**, fitted within the existing bays. The source under-stair handle footprint was also moved to the outward side of its case. These are render details within the authored storage locations.
- Seven door-pot containers, the lemon and olive pots, and two northern roof pots are tapered hollow vessels with rims and visible soil. The two long raised beds are thin-walled trays with soil rather than solid blocks. Four trellises use open uprights and crossmembers, with woody branches supporting the procedural leaves and bracts. Their authored centres and beds remain unchanged.
- `hanging_picture_frame_01` was an empty black front. It is removed from the D1 render scene. Reinstating artwork requires a licensed C2 intake, source, licence and isolated preview.

Each added physical kind declares a Part kind and is checked for a closed outward solid. The fresh real scene has zero failures in the Chunk B physical kinds; 163 other C3 legacy part failures remain in collection mode.

## Checks and visual status

- `NO_COLOR=1` focused Chunk B, landscape and furnishing regressions: 35 tests passed, exit 0 in the final run. An earlier test-only trellis assertion incorrectly demanded more than 50 faces from eight six-face members; it now checks at least 48, with Part separately rejecting a solid wall.
- The full-scene support test found 16 unsupported grille subparts once the duct proxy was removed. The duct had provided accidental contact. The first 1 mm frame adjustment failed because the service endpoint was 100 mm beyond the built facade. The render now derives the facade face from the built walls and places the grille frame against it; each louvre overlaps the frame. The fresh `test_nothing_floats` and two Chunk B tests passed together, 3 tests, exit 0.
- Extending the same pot builder to roof planters exposed nine unsupported plants: soil was 20–30 mm below their authored base. Soil now finishes 5 mm below the rim, so the plants keep their positions. The north-planter regression counts body parts only, and rectangular raised-bed soil has an explicit closed-solid Part admission. The three previously failed real-scene tests passed after correction, exit 0.
- `NO_COLOR=1` `scripts/verify.py`: exit 0, `RESULT: ALL PASS`.
- `NO_COLOR=1` `scripts/villa_render_views.py`: exit 0; geometric preview `out/villa/render-d1/views-plan.png` inspected. It checks camera intent and plan framing, not photographic appearance.
- The final `scripts/villa_render.py --dry-run` rebuilt and validated a fresh scene, listed all 13 requested review views, reported `stale_scene: false`, and exited 0. Its source hash is `f5a8be7e0378d0d34fa40af8b4bb5a72919c910f645e9984597ef4d1d14c1012`.
- Photographic draft command for `v16-guest-wc,v19-garden-facade` at 64 samples and 640 × 426 stopped before deployment. Git SSH in the managed Windows sandbox failed `CreateFileMapping ... Win32 error 5`; no new image or render QA result was produced. No local Blender executable is available in this environment.

## Lead rendering list

First review `v16-guest-wc`, `v17-dirty-kitchen`, `v31-dressing-hers`, `v32-dressing-his`, `v29-under-stair-store`, `v30-under-ramp-store`, `v19-garden-facade`, `v25-top-garden-gate`, `v26-top-garden-north`, `v27-north-garden-above` and `v28-north-garden-below`, plus `v12-ensuite` to retain the Chunk A brass fitting check. C4 retires the duplicate v14 camera; the two retained dressing views cover both detailed rail sets. Review isolated neutral-light close-ups of the valve, drain, rail/bracket, box/case, planter and trellis before integration.

Lead acceptance remains open for visible duct concealment, valve and drain legibility, case scale and handle direction, absence of blocky pot bases and a solid trellis wall, and the removed empty frame.

## Climber follow-up (2026-10-01)

The lead's full-suite yard guard found the north branched climber beyond the boundary; inspection found the west sibling also beyond the boundary and all four branch sets extending past their supporting frames. The shared branch constructor now intersects each stem with its own wall-mounted frame. The per-climber D1 regression failed on all four before the fix, including north, and passes after it. The ASSUMED young-planting target is 35 percent face coverage (the model estimates 41.6 percent with its edge safety margin), leaving most of the lattice open. A current geometry and foliage elevation preview is at `out/c3-climber-open-lattice-preview.png`; it is schematic, so photographic lead acceptance remains open.
