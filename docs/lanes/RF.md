# RF: interior render fixes from the L9P draft pass (2026-11-22)

Branch `lane/RF` from `origin/lane/L6d`, merged with `origin/integ/aplus` (`098439f`, which already holds LV, FG and L9P). Every defect below was diagnosed on the L9P drafts
and the scene data before a change; before/after images are drafts (96 spp, 1920x1280, GPU, jobq) in `knowledge/render-set/rf/before-after/` (left L9P draft, right RF final pass, 8 of the views).
L9P drafts: `~/archpipe/lanes/L9P/out/l9p/final-drafts/`; RF final pass: `out/RF/final/all/` (not committed, 36 PNG + JSON).

## Per defect (L9P section 3)

| # | defect | cause (on data) | fix | evidence / guard |
|---|---|---|---|---|
| 1 | over-scaled marble and oak grain (13 views) | `tile_m` was the scan's own width: marble 1.2 m, door oak 1.83 m, walnut 1.0 m. Vein blotches measure 10-20 cm and the oak cathedrals 45 cm on screen (texture dimensions and the render agree: the mapping is right, the chosen scale is not). The Marble014 per-channel mean match also pushes the brown veins to rust. | `tile_m` marble/travertine 1.2 -> 0.6, white worktop 1.4 -> 0.7, walnut 1.0 -> 0.6, door oak 1.83 -> 0.6; `contrast` 0.8 on the three cream marbles. **ASSUMED policy, not a published figure** (`TEXTURE_FIGURE_MAX_M`). | n08, n02 before/after. `tests/test_villa_render_texture_scale.py` (class limit, 1000 px/m texel density, draft values as negative control). Residual: veins are still rust-brown on the cream marble (a texture property); door oak grain still reads large on the n10 door. |
| 2 | faceted, cropped, blown globe pendants (n02 n03 n19) | `sphere()` 16 x 10, flat-shaded fixture mesh. Cropping is camera (L9P). Blown: the globe is lit by an emissive core of the full flux; the shell reads about 600-1000 cd/m2 against walls of 30-50. | globe shell 48 x 28, core 24 x 14, both `smooth_shaded` (new mesh key, `villa_scene.add_mesh_detail`); evening views n05/n06/n19 use the design's Evening scene (see 3). | n02, n19 before/after. Smooth now; **n19's globe is still clipped** (clipped fraction 1.08 % -> 1.09 %): the zone level of the island pendants in the Evening scene (0.4) is not rendered (the render has layer dimmers only; `villa_render_contract` and `exposure_groups` are not RF files). Open item. |
| 3 | near-black stores, cinema, under-stair (v29 v30 v03 v08 n07 n17 n21) | v03/v29: the basement day views used a typed ambient 0.5 while the lighting design's Day scene for the open plan is ambient 1.0 / accent 0.5. v30: the store is lit only by three 630 lm battens to the 50 lx card; at the evening group's exposure that is a dark image by design. | `BASEMENT_DAY` and the render-set `basement-day` preset read `villa_lighting.SCENES["B-open"]["Day"]`; evening views n06/n19 use `design-evening` (the design's Evening scene). The exposure records were re-measured (below): v29's day state moved to the 2700 K lamp group at 37 % daylight (blue), so v29 is shown in the design's Evening scene (evening group, 3000 K). | Median luminance (display, 0-1): v03 0.145 -> 0.165, v29 0.078 -> 0.353 (evening state), v30 0.063 -> 0.059 (unchanged). `tests/test_villa_render_light_state.py`. **v30 is unchanged and still near-black**: the cure is a design change (more store light) or an own exposure group (a new pre-registered rule in `src/archpipe/exposure_groups.py`, not RF's file). |
| 4 | office chairs in the cinema (v08) | **Not a binding error.** `cinema-desk` is a scheduled work-place desk with two chairs (`villa_furnish.py:296`, card `ies-res-desk-400`); the seating is the `cinema-sofa`. The chairs are the detailed task-chair builder. | none | Reported, not changed: an alternative chair would be an invented product. If the client wants no desk in the cinema that is a layout decision. |
| 5 | bunk drawn as a white box; lamps floating as black T shapes (v06 v13) | Bunk: the only bunk that fits is the procedural fallback; both licensed bunk assets (`sf_bunk_home_series` CC-BY-4.0, `sf_bunk_simple_3dworkbench`) fail the fit checks (`docs/beds-report.md`), so the frame was all `white-paint-joinery`. Lamps: **not floating**: `lamp-arm-DESK-*` base starts at the desk top z 0.752 (data); the base is hidden behind the chair and the head is a flat box seen edge-on, so it reads as a T. | kids' bed/bunk frame `oak-grain-x` (geometry identical, bounding box unchanged). Lamps unchanged. | v06 before/after. The bunk is honest procedural geometry in oak, not a real asset. |
| 6 | the same cushion pattern on every sofa | one licensed prop (`throw_pillows_01`) is placed on the lounge and the living sofa. There is **no cushion schedule**, so varying the pattern would be inventing a design. | none | Open item: needs a schedule (client choice of cushion fabrics) and a second licensed cushion asset. |
| 7 | blown windows | The glass is the model's Tv 0.70 (Metric Handbook p. 9-8) at one locked exposure per group; the sky outside is about 8 stops above the interior. Probe (lamps-off n10, shared exposure): hiding the glass changes the mean by +4 %, hiding the exterior context lowers it, so the sky light is not a window artefact. | none | Physical result of one locked exposure; closing the sheers by day would also hide the garden views. Open item for a design decision. |
| 8 | smeared curtain texture (v10 v21 n12) | **Not reproduced as stretch.** `rough_linen`/curtain textures are 7 700 px/m on a 0.27 m tile, minified at 3 m, so the weave averages out to a flat soft colour; the vertical streaks are cloth shading. | none | Open item (a weave bump at metre scale would be a look decision). |
| 9 | blue cast in the east hall (n10) | 35 % of the metered luminance is daylight (record: lamps 312 605, daylight 169 447) and the lamp-dominant group is balanced to its lamps' 2700 K (pre-registered rule). Lamps-off render is evenly blue. A ray probe (20 000 directions per origin, shell and context without glazing) shows the hall closed everywhere except its **open west end** (36 rays escape from x 12.5 m, none from x >= 15 m): the daylight comes down the hall from the open plan. Not a geometry leak. | none | `tests/test_villa_render_daylight_leak.py` (windowless views <= 10 % daylight; n10 is a strict xfail so the fix must remove the mark). Options for the lead: put the view in the evening state, close the hall's west end, or a mixed-light white-balance rule. My first experiment (hiding the glass) could not show the path: removing glazing only opens more paths. |
| 10 | other material/asset classes | #11 (kitchen backsplash), #12 (shelving, bent ceiling line) are finish/geometry additions that need a client finish choice and new geometry; the garments (v31) and wedge pillows are bedding/garment builders. | none | Open items. |

## Exposure records and receipts (re-done after the final merge; no bypass)

* Receipts `knowledge/furniture-stage2.json.gz`, `parents-bed.json.gz` regenerated baseline-relative (RA method): old tree = `06e74dc` (L6d), **reproduces all 8 stored section digests**; section diff old vs new
  (`knowledge/approvals-review/evidence-rf/section-diff.json`): layout, specification, furniture, architecture, models, props unchanged; **materials** changed ids = door-oak, marble-bath, marble-ensuite, marble-white, travertine, walnut, walnut-grain-x, walnut-grain-y;
  **meshes** changed ids = `lamp-/bulb-PEN-GLOBE-stair-gf-01..03` (tessellation, bounding boxes identical) and `furn-ka-bunk-0` (material only). `refresh_furniture_integ5.py review-current`: **16 individual + joint reviews, 0 findings**.
  The receipts carry a separate `refresh_2026_11_22_rf` note (the 2026-11-21 note is unchanged history).
* `knowledge/exposure-groups.json` (production views) re-measured through Blender (jobq `RF-measure-exposure-1`), copied byte-for-byte. Membership change: `v29-under-stair-store` day -> lamp-dominant (design Day ambient 1.0).
* `knowledge/render-set/exposure-groups.json` (the 48-view set) re-measured (jobq `RF-measure-set-3`, a new id each time: an existing id returns the old job). After v29 moved to the evening scene it is in the evening group (lamp fraction 1.0).
* Production builds, receipts and records active, no bypass (`out/RF/prod`, `out/RF/set`, builds from the committed tree, `git_dirty` false):

| scene | file bytes | sha256 | ids stripped sha256 | meshes / views | `source_hash` |
|---|---|---|---|---|---|
| production (`villa_render.write`, 41 views) | 633,556,539 | `bd1f9bf4b9e603eff894e3c36b73549564ccc045ede0a40e3d08e9626d9d4552` | `cda6551224d2fe72ef3867581873205a70933ec3905ff37e83a089df8a452a72` | 1,224 / 41 | `b3342bca1398ff4ab786165ee1f5d88a59bb48dbee6d8445cd7e1229e9452106` |
| render set (`render_set.write_scene`, 48 views) | 633,609,778 | `bd578c7deaa7ee0d936cdfffb7b963ad09afad2183cd9a5474dbd4232b4cacb6` | `a8fab14204d3cb92a68a285a7d93262ee3d771c90acb93e9a62bc9eb88b50ce0` | 1,224 / 48 | same |

(The ids-stripped hash includes `provenance`, hence the source hash is part of it. Rebuilt after merging integ `7aec244` (L8 scene cache): receipts and both records still accepted, hashes above are of that build; before that merge the production hash was `648ac636...` / source `e14b08de...`.)

## Critic and grades (36 interior views, same method as L9P section 2, frozen rubric, gates R8/R10/R11 + deterministic six)

| | before (L9P drafts) | after (RF final pass) |
|---|---|---|
| critic pass / fail | 7 / 29 | **7 / 29** (no verdict flipped) |
| gating scores that moved | | v29 R10 0 -> 2, R11 0 -> 1; n02 R8 1 -> 2; n18 R8 1 -> 2, R4 1 -> 2; v03 R3 1 -> 2, R10 2 -> 1; v21 R11 2 -> 0; v30 R10 2 -> 1; v05 R11 2 -> 1; n16 R10 1 -> 2 |
| table (`knowledge/render-set/rf/critic-after-results.json`) | | recall on D+ or worse is computed against L9P's labels of the *old* images and is not meaningful for the new ones |

The critic is a noisy high-recall filter (L9P section 2: 50 % false fail on B- views); a first pass before the v29 change gave 5 / 31 (v09 and n20 flipped on a single R8/R11 point each), which shows the size of that noise.

My grades (AI, looked at every final image; the before grades are L9P's labels, `knowledge/critic/extension-L9P-labels.json`):

| view | before | after | | view | before | after |
|---|---|---|---|---|---|---|
| v33 | B- | B- | | n05 | D+ | D+ |
| v34 | B- | B- | | n06 | C | C+ |
| v02 | C+ | C+ | | n07 | C | C |
| v10 | C+ | C+ | | n08 | D+ | C- |
| v03 | D+ | C- | | n09 | C | C |
| v21 | B- | B- | | v11 | C+ | C+ |
| v09 | C+ | B- | | n10 | D | D |
| n01 | C+ | C+ | | n18 | C | C |
| n02 | C- | C | | n19 | B- | B- |
| n03 | C+ | B- | | n20 | B- | B- |
| n04 | B- | B- | | n11 | C | C |
| v08 | D | D | | n12 | C | C |
| v29 | F | C- | | v06 | D+ | C- |
| v30 | F | F | | v13 | D+ | C- |
| n13 | C+ | C+ | | n15 | C- | C |
| v05 | B- | B- | | n16 | C- | C |
| v31 | C | C | | n17 | D+ | D+ |
| n14 | C+ | C+ | | n21 | D+ | D+ |

Still no view better than B-: the finals gate (L9P) is **not** met by this lane; the remaining blockers are the open items below.

## Tests (fresh clone of `lane/RF`, `NO_COLOR=1`, laneP-venv)

Fresh clone at `26b9a15` (before the L8 merge): lane suite + `tests/parity tests/markup tests/landscape tests/test_villa_render*.py tests/critic` **1092 passed, 7 skipped, 2 xfailed, 0 failed** (15 min); scene group `tests/test_mounting*.py tests/test_d1_*.py` **76 passed** (27 min); `python -m archpipe.compliance.run_d1` exit 0, no failing gate (regenerated L1 report reverted). An earlier run at the pre-LV-merge tree had 4 `tests/lightverify` failures (LV pins of the old pendant: `test_v10_erco` x3, `test_v1_design::test_bound_pendant_is_one_emitter_at_its_record_flux`), identical on L6d base `06e74dc`; they pass once LV is in integ.

## Open items

1. Zone-level scene levels (island pendants 0.4 in Evening) are not rendered; needs `dimmers` keyed by zone in `villa_render_contract` and `exposure_groups` (not RF files). It is the cause of the clipped globe in n19.
2. v30 under-ramp store: design change (more light) or its own exposure group.
3. n10: choose the state / close the hall's west end / mixed-light white balance.
4. Cushion schedule and a second licensed cushion asset (defect 6); a real bunk asset needs a fit-checked product (defect 5).
5. Windows by day (defect 7) and the curtain weave (defect 8) are look decisions; kitchen backsplash, shelving, garments (defect 10).
6. Texture scales are an ASSUMED policy (0.6-0.7 m); a client-approved finish sample would replace it. Marble veins stay rust-brown (texture colour).
7. Camera items (L9P 9, 10) are not RF's.
