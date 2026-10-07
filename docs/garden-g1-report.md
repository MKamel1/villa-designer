# Garden rebuild R3b-4 — G1 review candidate


**Follow-up 2026-10-06:** lead decisions D1–D3 and the east/north G2 candidate are measured in [garden-g2-report.md](garden-g2-report.md). This G1 report retains the historical diagnosis; its mature-height scale and missing-bed conflicts are superseded. The new physical low-branch route blocker remains open.

2026-10-06, baseline `1a4ba1a`. G1 means the south-garden chunk; G2 covers east/north gardens and G3 covers the top garden.

**Acceptance is blocked.** The agreed species record and south content are implemented, but the required uniformly scaled frangipani model does not fit the court and overlaps the inherited door-route envelope. The inherited three-layer border rule also conflicts with the lawn-only south brief and with removal of unapproved planting pending G2/G3. None of those guards was weakened. `villa_landscape.build()` raises `ValueError`; `review_candidate()` exposes the measured proposal and its conflicts for diagnosis, not scene export. This is not an accepted render or a real villa design gate.

## Changes

- `knowledge/garden-palette.json` is the sole botanical and placement-size record. It contains exactly the ten agreed species, their zones, sourced ranges/quotes/URLs, per-field evidence status, eight exclusions and exclusion reasons. It preserves missing ranges; Ixora's unstated spread has a separately labelled ASSUMED 1.2 m spacing envelope with a reason. Egypt performance and root behaviour over the basement slab are UNVERIFIED for every species. Missing lower/upper bounds are explicitly UNVERIFIED.
- Removed `SPREAD`, `CLUMP_SPREAD`, `EXTRA_CARE` and the landscape dependency on shared `out/villa/round3/plant-palette.json`. Asset-to-species bindings remain identity mappings. Unknown/excluded plant assets fail before construction; scene checks also reject absent identity or relabelled models. Procedural climber meshes carry species and recorded assumed dimensions.
- The full south court has artificial turf with an actual opening, stepping stones for its living-south door, one `sf_frangipani`, and a gravel tree pit. Turf is an annulus around the opening, not a capped lawn hidden beneath gravel. Existing routes to the other garden doors remain.
- Removed all south furniture, pots, beds, other plants and trellises. The old bed/trellis called “east” at x=24–27 m was physically within the full south court and therefore also removed. The east turf now stops at the south-court edge, eliminating overlapping lawn faces.
- Outside the south court, removed unapproved plant placements without choosing replacement species or relabelling look-alike assets. Existing approved north/top placements, bench, beds and pots/containers retain their geometry; former lemon/olive and lavender containers remain empty. G2/G3 replacement planting, approved-zone reconciliation and court lighting suitability are pending. No G2/G3 replacement design was authored.
- Scene provenance now hashes the authoritative tracked palette. Its regression changes that file and proves an old scene becomes stale. This small `villa_render.py` change is necessary to prevent a palette edit from silently reusing an old scene.

## Measured tree and conflicts

Coordinates and dimensions below are metres in the existing scene frame; x and y are horizontal, z is height. Native glTF uses y as height, which the importer converts to scene z.

| Measurement | Result |
|---|---|
| Full south court rectangle | x=22.597–28.557, y=−29.91566–−20.351 |
| Court size to plot edge | 5.960 × 9.56466 |
| Court centre / measured trunk base position | x=25.577, y=−25.13333 |
| Rear/south fence thickness | 0.250, existing `villa_env` input |
| Width inside rear fence | 5.710 |
| Actual native asset bounds, minimum | (−1.585174441, approximately 0, −2.006321907) |
| Actual native asset bounds, maximum | (2.300418854, 2.768474340, 1.530686140) |
| Uniform scale for actual 4.6 m height | 1.661564975629 |
| Scaled model's maximum horizontal span | approximately 6.456 |
| Conservative world bounds from rounded manifest | x=22.948619–29.404796, y=−27.674955–−21.798000 |
| Plot overrun on rear side | 0.847796 |
| Overrun of fence inner face | 1.097796 |

Read the local `/home/omar/archpipe/assets/library/props/sf_frangipani/model.gltf` and its binary buffer without changing them. Native accessor bounds and node transforms agree with the manifest within 0.00003 m. The record includes both file hashes, measured bounds, scale, axes and CC Attribution credit. A bark-vertex read-back measured the trunk base from 26 ground vertices; the scene centres that base rather than the asymmetric canopy box. The latter construction would put the trunk outside the 1.2 m opening and is reproduced in a regression. Rounded manifest bounds remain the existing conservative extent-check input, so its reported height exceeds 4.6 m by approximately 0.000043 m; actual measured height is 4.6 m.

The verified lower mature spread is **4.6 m**, unchanged. Its centred circle clears the court and physical fence inner faces. The modelled canopy does not. Even the smaller axis-aligned model projection at 90 degrees is approximately 5.877 m, wider than the 5.710 m usable court width. No tree rotation, relocation, nonuniform scaling or pruning of mesh geometry was used to satisfy a check.

`extent_violations` finds 75 sampled model-footprint points outside the yard/plot. `canopy_violations` additionally checks the inner fence faces. `route_violations` flags the tree against `living-south`: that guard compares whole prop footprints, including canopy. The route and guard are retained. A centred mature tree also naturally overhangs this approach; resolving canopy-over-path policy requires an explicit design/guard decision, not silent filtering of the tree from route checks.

`layer_violations` remains unchanged and reports east: 0/3, south: 0/3, north: 2/3 primary layers. An south border directly conflicts with the agreed lawn-only brief. East/north planting restoration is G2 work; no unapproved front species was retained to make this check pass. The lead must resolve the asset/route/layer conflicts before export. A changed asset or justified policy decision needs its own measured proof and review.

## Assumptions

- Tree pit: ASSUMED 1.2 m diameter, gravel surface; drainage/root detail remains UNVERIFIED.
- Frangipani: ASSUMED pruning intent at 4.6 m height and spread, each at the lower end of the verified mature range. The target is not represented as achieved 4.6 m model spread.
- Existing Callistemon, Ixora and Bougainvillea nursery/pruned sizes and Ursinia multi-plant appearance dimensions remain ASSUMED envelopes, with reasons and existing placement contexts in the record. The dimension guard measures actual model height and maximum horizontal span. It accepts only the sourced range or a record-supplied assumption, never an exception invented in a scene label.
- Existing turf, stepping-stone geometry, containers, drip irrigation, rail allowance and illustrative sun screen retain their previous assumption status. No new Egypt, root, structural, drainage or nursery-performance claim was made.

## Guard proofs and validation

`tests/fixtures/garden-g1-before.json` freezes the real pre-change props and relevant south surfaces by value. Tests do not recreate the old failure by importing the new builder.

| Guard / construction | Real failure and sibling proof | Current candidate |
|---|---|---|
| Approved identity | Old excluded Bauhinia; excluded Pennisetum; unknown Citrus; missing/mismatched identity | Pass |
| South-only contents | Old south beds/furniture/two trees; renamed real bistro; duplicated frangipani | Pass |
| Actual plant dimensions | Old 2.3 m frangipani; oversized/nonuniform tree; overgrown procedural climber | Pass against sourced/ASSUMED ranges |
| Centred trunk / open pit | Canopy-centred placement misses pit; frozen old lawn quad caps opening | Pass |
| Mesh boundary / physical parts | All candidate landscape vertices checked against yard; closed parts and upward surfaces checked independently | Pass |
| Mature canopy | Boundary-shifted mature circle fails; actual centred 4.6 m circle stays quiet | Pass |
| Model canopy / extent | Required actual scaled model exceeds wall/plot; 90-degree projection still fails | **Fail, reported** |
| Door route | Frozen real teak-sofa obstruction and current tree footprint | **Fail for tree, reported** |
| Garden-level rooms / object extent | Old planting inside dirty kitchen; top rail-crossing object | Pass on retained objects/other props |
| Spacing / drift | Frozen close plant centres and thinned Ixora drift | Pass |
| Layer | Old single-row bed fails; constructed three-layer case stays quiet | **Fail on candidate, reported** |
| Swing / bench / stand-in | Old swing motion collision; old bench slab/wrong facing; old mislabelled generic tree | Pass; swing absent by brief |
| Palette provenance | Copied palette edit makes scene stale | Pass |

Executed with `NO_COLOR=1`, `PYTHONPATH=src` and `/home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python`; judged by process exit status:

- Landscape, scene provenance, climber placement, exterior mounting, asset intake and villa concepts: **90 tests, exit 0**.
- `tests.test_render_standard`: **exit 1**, import-time scene build refuses the known landscape conflicts. Its obsolete Bauhinia/swing presence assertions now follow the G1 brief; physical trellis checks refer to the retained north trellis.
- `tests.test_final_mounting` and `tests.test_support_mounting`: **exit 5**, scene setup fails on the same garden export guard.
- `tests.test_render_views`: **exit 1**, 13 tests run, four scene-dependent errors from the same garden guard.
- `scripts/verify.py --portable`: **exit 1** at scene construction, before later checks can execute.
- `render_support.unsupported(VR.build())`: **blocked by `ValueError` before a scene exists**. An empty unsupported list is not claimed.
- `git diff --check`: exit 0. No full-suite acceptance is claimed; the lead runs the full suite.

The proof tests establish the candidate contracts and preserve rejection of physical conflicts; they do not establish whole-scene acceptance. Existing scene-dependent mounting tests also refer to removed south/west assemblies and must be reconciled after the export blockers are resolved, retaining their frozen historical failure proofs.

## Lead view handoff

No Blender/presentation render or preview was produced, as instructed. Checkpoint 2 is the measured candidate plus guard evidence; visual acceptance remains open. Do not bypass `build()` to render an invalid scene.

After the blockers are resolved, inspect and rerender:

- `v07-terrace-dusk` and `v19-garden-facade`: direct south-garden presentation. `v07` still names removed `landscape-sofa`; revise its view intent instead of restoring an invisible marker or forbidden furniture.
- `v02-garden-living` and `v10-living-evening`: south garden seen through the living openings.
- `v26-top-garden-east`, `v27-east-yard-above`, `v28-east-yard-below`: their sightlines reach the full south court. Old east bed/trellis subjects were removed; an empty lemon container is not the former planted specimen. Revise captions/subjects, then rerun framing, occlusion and camera-clearance checks without moving design content for the camera.
- `v25-top-garden-gate`: affected by removal of unapproved top planting; final top-garden review belongs to G3.

Retain this report and `garden-g1-authority` in `docs/LEARNINGS.md` as the diagnosis/first-fix checkpoints. Future G2/G3 work must read the same tracked record and must not restore botanical dimensions or care data in local constants or shared generated files.

Current naming authority: [site orientation](../knowledge/site-orientation.json). Historical numeric sun-proxy results in this report are superseded by [the orientation and ray-cast report](orientation-naming-report.md).

<!-- garden-side: -x; name: north -->
<!-- garden-side: +y; name: east -->
<!-- garden-side: +x; name: south -->
<!-- garden-side: -y; name: west -->
