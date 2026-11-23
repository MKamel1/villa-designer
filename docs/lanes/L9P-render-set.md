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

## 2. Critic gate: L3 calibration extended (frozen-v1, nothing tuned)

Pre-registration: `knowledge/critic/extension-L9P.json` (written before any draft was opened). Labels: `extension-L9P-labels.json`, by the lane agent (an AI) looking at each draft, committed before the critic ran. Scorer: `python -m archpipe.critic.extension`; results `knowledge/critic/extension-L9P-results.json`. The 36 draft images are all held out (never used for tuning). Rubric, prompts, gates (R8/R10/R11 + deterministic six) unchanged.

**Scorer bug found and fixed (disclosed):** `calibrate.load_vlm_dir` globbed `v*.json`, so every new `n*` view was scored "VLM unavailable: fail closed" (a first table showed 29/29 fails, which was an artefact). Fixed to `*.json` with a regression test. The table below is the corrected one.

| measure | new set (n) | Wilson 95 % | pooled with 38 audit views (n) | target |
|---|---|---|---|---|
| recall on D+ or worse (must fail) | 10/11 | 0.62-0.98 | 28/29 = 97 % (0.83-0.99) | >= 90 % **met** (point estimate) |
| false-fail on B- (should pass) | 4/7 = 57 % | 0.25-0.84 | 6/12 = 50 % (0.25-0.75) | <= 10 % **missed** |
| fail of C-or-worse | 25/29 | 0.69-0.95 | 55/62 | not set |
| fail of C+/C/C- | 15/18 | 0.61-0.94 | 27/33 | not set |

Misses: the one D+ passed is `n21-family-bath-wc-day` (pan cut off at the bottom edge; nothing in the rubric sees cropping of a subject by the frame). False fails of B- views: v21 (R3 lean from the stair, as before), v34, n04 and n19 (R4 = 1 from window glare in the subject box plus R8/R11 = 1 from the VLM; n19 is a blown globe pendant). Same causes as the L3 failure examples; adding the extension did not move the false-fail rate. **The false-fail target is still missed, with n = 12 good views and a wide interval.** Honest reading: the critic is a high-recall filter, not a one-shot gate; as a gate it will send about half of the good views to human review. Next step if wanted is a v2 rubric (R4 on window-masked subject box, R3 excluding stair bins) scored only on views that did not inform it, e.g. the finals.

Labels are mine, not a human's, and the three B- views the pre-registration counted as good are the lane's own new views; treat as supportive evidence only.

## 3. Draft pass (36 interior views, current production scene, jobq L9P-draft-1..3)

All 36 rendered at draft quality through jobq (GPU OPTIX, 96 samples, 1920x1280) and viewed by me on a contact sheet and individually when graded. Draft artefacts (noise, small fireflies) are excluded. Real defects, with root cause per the photoreal-render skill and the owner who must fix them before finals:

| # | defect | views | root cause | owner / must fix before finals? |
|---|---|---|---|---|
| 1 | Marble and oak/walnut grain grossly over-scaled and rust-veined/blotchy | n06 n08 n10 n15 n16 n17 n21 v09 v11 v31 n01 n14 n20 | material texel density / UV scale not per-object metric (R7) | L6d (villa_scene materials). Yes |
| 2 | Strong blue cast over whole corridor, 60 % blank wall | n10 | sky/ambient bleed through an unshaded opening and no interior fill, plus unlit corridor; exposure group too low for a dusk-lit corridor | L6d/L6b lighting. Yes |
| 3 | Faceted paper-globe pendants cropped and blown | n02 n03 n19 | low-poly globe asset (R8) and pendant above frame; subject emissive blows out at group exposure | L6d asset swap. Yes (camera tilt/pendant clear is mine, trivial) |
| 4 | Near-black subject under fixed exposure | v29 v30 v03 v08 n07 n17 n21 | exposure group fixed for bright rooms; dark stores sit under the lock (memory rule: fixed exposure per group) | Lane L6b: per-group light for stores/cinema, not a per-view exposure change. Yes |
| 5 | Office chairs at a desk instead of cinema seating | v08 | wrong asset bound to the cinema seating intent | L6d/furniture binding. Yes |
| 6 | Bunk bed is a plain white box frame; wall/desk lamps float as black T shapes (nothing floats) | v06 v13 | lamp mount offset not hosted to the wall; bunk is a placeholder mesh | L6d/LDL assets. Yes (floating lamps are a guard failure) |
| 7 | Zig-zag cushion pattern reused on every sofa; rigid wedge pillows; melted-plate garments | v02 v10 v33 n01 n04 n13 v05 v31 | cloned dressing asset, no variation; low-poly bedding | L6d dressing. Yes for the hero views |
| 8 | Windows blown to white massing | n11 n13 n17 v06 v34 | exterior sky/garden brightness vs fixed interior exposure; window glass/curtain not tamed | L6d. Yes for n11 n13 |
| 9 | Stair stringer / dark panel / marble pier intrudes 10-20 % at frame edge | v03 v21 n07 n18 v34 | camera placement beside a structural element | L9P: adjust cameras in a second pass (small) |
| 10 | Subject cropped at the frame (WC pan, basin, tub, shower head, sofa) | n21 n17 n15 n16 v02 v05 | camera framing too tight/low at 24 mm in small wet rooms | L9P: reframe, but wet rooms at 24 mm are 2 m deep and may need the camera in the doorway; flag whether 24 mm is achievable |
| 11 | Sterile blank wall, no backsplash | n09 n05 n02 | kitchen run finishes not modelled | L6d finishes. Not blocking for n05/n09 as secondary views |
| 12 | Bent wall/ceiling line, empty white shelving | v30 n05 | shelving/under-ramp geometry placeholders; lens distortion not applicable | L6d/LDL. Yes |
| 13 | Smeared curtain texture | v10 v21 n12 | texture stretched on pleated curtain mesh | L6d materials. Yes |

No floating furniture other than #6 found. No clipping through walls seen other than the piers in #9.

Critic result per view is in section 2 output; it agrees with my grades on 25 of 29 C-or-worse views. The draft set has **no view graded better than B-**, so none is ready as a final: finals need fixes 1, 3, 4, 5, 6, 7, 8, 12, 13 from L6d first.

## 4. GPU-hours estimate for the finals

Measured: one 1024-sample frame ~138 s render (`L9P-final-timing`, v05) plus scene load ~40 s, i.e. ~3 min/view; draft ~20 s. Finals: 36 interior + 12 garden = 48 views ~ 2.4 GPU-h, plus the critic VLM (~30 s/view, 0.4 h). Allowing one re-render of about half the views after the gate and the camera second pass: **~4 GPU-h total** (3-5 h range), plus 0.6 h of exposure measurement per scene change (measured 637 s per run, jobq L9P-measure-exposure-1). Garden views are placeholders and need re-render after LDB.

## Open items
- L6d to read the render-set (section 1) and fix the material/asset defects above; exposure record must be re-measured after the scene changes.
- Camera second pass (items 9, 10) after L6d lands.
- Blind photo test (L9) not started: needs finals.
- Critic false-fail target missed; v2 rubric proposal above, not run.
