# Lane P2: element identity on scene meshes (Revit plan stage 1, rows I09 / I08)

Every mesh of the built scene now says which design-model element(s) it represents, so an independent check can
take "the faces of `wall-B-ext-03`" instead of classifying merged surfaces by normal and z.

Code: `src/archpipe/blender/element_ids.py` (all logic), hooks in `concept/villa_render.py::_build`,
`scripts/benchmark_scene_build.py` (`--strip-ids`, `--coverage`), tests `tests/pipeline/test_element_ids.py` (28 tests
with `test_platform_hint.py`).

## Blocker found first: the integration base cannot build the scene

`origin/integ/aplus` (`14578c8`) does **not** build: `villa_render.build()` stops in the mounting stage with
`ValueError: detail-stair-open-stringer: approved schedule drift; new lead review required`
(`exterior_mounting.apply_lead_review`; lane LV hits the same family at `lamp-SCONCE-family-bath-04`). Cause: lane D
(stair tread overlap, `a814402`) and lane FIX1 (planting / sconces, `a412835`) changed geometry that the frozen lead
approvals in `knowledge/c4-*-approvals.json` pin to 1e-8 m. That needs a new lead review (client authority), not a
workaround from this lane.

So the before/after proof ran on the last commit that builds, **`e645041`** (lane P, the commit behind the documented
baseline `b3075f18...`), in a detached worktree. `villa_render.py`, `villa_daylight.py`, `daylight.py`,
`physical_part.py` and `passes.py` are byte-identical between `e645041` and this branch's base, so the patch applies
unchanged. Until the lead re-approves the stair/sconce rows, no scene with ids can be built on the base itself.

## Schema (additive; three fields per mesh)

| field | type | meaning |
|---|---|---|
| `element_ids` | list[str] | design-model element ids the mesh represents; `[]` when the model has no such element |
| `faces_by_element` | {id: [face index]} | present when faces were attributed one by one (shell, merged detail meshes); a face missing from it has no owner |
| `element_id_basis` | str | how the ids were obtained: `face-tracked`, `face-registry`, `source-mesh`, `declared`, `declared-stale`, `generator-name`, `unresolved` |

Without `faces_by_element` the whole mesh belongs to every id in `element_ids` (single id in practice).
Ids are the design-model ids (`model/spec_source.py`, `fit_source.py`): `wall-B-ext-03`, `door-B-...`,
`window-GF-...`, `column-04`, `beam-0-e2`, `slab-deck`, `rail-gf-stair-void`, `stair-main` (all treads),
`furn-k-island`, `lum-DL-lounge-01`, `fixture-gwc-rain-head`, `plant-landscape-east-back-00`, `room-lounge`.
Ids with **no design-model element** use a visible prefix so nobody mistakes them for model ids: `env-slab-*`,
`env-yard-*`, `env-share-*-ceiling` (existing building), `spec-ramp-*infill*` (ramp wall tops), `site-ground`.

Where ids come from (never from geometry alone):

1. **Shell** (`villa_daylight.scene` emits faces tagged by material only). `trace_adds()` records which `Scene.add`
   call made which faces; `shell_owners()` replays the call order of `villa_daylight.scene` (ground, environment
   boxes, columns, environment slabs, shares, walls, stair boxes, roofs, ramp, deck, infills, rails) and names each
   call's element. Inside a wall, door/glass faces get the door/window whose opening they fill (same `_owners` /
   along-wall / sill-head test the daylight scene used). A different call count raises, so a change to
   `villa_daylight.scene` cannot silently mislabel the shell.
2. Faces the finish merge splits (plaster at the stair wall, glazed-slider panes) are registered with their source
   face's owner in the build loop. Passes that rebuild shell faces (construction skins `backed_polygon`, door-leaf
   assembly) are matched back to the tracked face they came from (`Registry.lookup`: same plane within 2 mm and
   centre inside its box; exact vertices first). Only meshes made from tracked faces use this
   (`DERIVED_FROM_SHELL`): a ceiling that merely touches a wall is not mislabelled.
3. Finish layers (`finish-layer-N-<source mesh>`) take the owner of the shell faces they record in `source_faces`.
4. **Declared** at creation (`mesh(..., element_ids=[...])`): appliances (hosted on their `furn-` support), TV
   fluting, headboard slats, the pocket door, and the merged detail meshes whose faces are appended in runs
   (skirting -> `room-*`, window frames -> the window, architraves and handles -> the door) with `faces_by_element`.
   Declarations live in a side table and are merged at the end: `furniture_stage2` hashes every mesh attribute, so a
   field in the dict at creation changed its receipt (`changed sections: architecture`).
5. **Generator name**: the mesh id embeds the source id the generator used (`lens-DL-lounge-01`,
   `furn-k-island-stool-2-1`, `detail-gwc-rain-head-drop`, `landscape-east-back-00`, garment modules ->
   their wardrobe). Resolved by longest match against the live id set (`_live_model_ids`: spec + furniture items +
   `VL.design` under `input_revision(False)` + props + garden plan; no snapshot file), never by position.

`attach()` runs as the last step of `_build`, after every pass, admission and probe binding, so no receipt or
appearance record that hashes or copies mesh attributes sees the fields.

### Consumers that hash whole meshes

`exposure_groups.transport_digest` (frozen measurements) and the drape/imported appearance records hash the mesh dicts.
Scenes carrying ids make `require_record` raise "Stale dominant-light rule or transport measurement". Handled by
`element_ids.without_ids(scene)` at the consumers in lane P2 paths: `villa_render.write` (exposure record and
`validate_scene`), `scripts/villa_render.py` (scene load), `blender/villa_scene.py` (Blender-side load; the render
receipt hash is therefore unchanged by ids) and `blender/walkthrough.py`. **Request to the lead** (not my paths):
make `exposure_groups.transport_digest` ignore `element_identity.FIELDS`, or any other script that validates a
loaded `scene.json` against the frozen record (`verify.py`, lane scripts) will fail on a scene with ids until it
calls `without_ids`.

## Coverage (D1 scene built at `e645041` + this patch, `scene.json`; model ids from that tree's `d1-elements.json`)

| group | meshes | faces | faces with any id | with a design-model id | share (model id) |
|---|---|---|---|---|---|
| shell | 167 | 7,383 | 7,359 | 6,510 | 88.2 % (99.7 % any id) |
| context | 68 | 412 | 412 | 412 | 100 % |
| furniture | 288 | 177,482 | 141,094 | 141,094 | 79.5 % |
| fixture | 355 | 12,393 | 9,903 | 9,903 | 79.9 % |
| dressing | 312 | 1,560,830 | 1,560,566 | 1,560,566 | 99.98 % |
| ground | 52 | 539 | 265 | 265 | 49.2 % |

The 100 % target for shell/furniture/fixture is **not** met, honestly: the remainder is geometry whose element does not
exist in the design model (the CLI fails if an uncovered mesh has no stated reason; the list is `NO_MODEL_ELEMENT`).
These are model gaps for the lead, not tagging gaps:

| group | uncovered faces | reason |
|---|---|---|
| shell: 849 faces carry non-model ids | `env-slab-B/GF/APT/ROOF/GF-front` (336), `env-yard-ours/sister` (268), `env-share-front/rear-ceiling` (79), `spec-ramp-*infill*` (146), `site-ground` (20) | existing building slabs, yards, share ceilings, ramp wall tops, street ground: no design-model element (`all_from_spec` has no env slabs) |
| shell: 24 | `detail-hatch-sill/head/left/right` | the kitchen pass-through hatch is not a model element |
| furniture: 36,364 | garden structures (swing 26,492 + cushions 3,264, pergola, seating, bowl, pots, troughs, trellis) 36,364 | garden structures are not model elements (the model has plants and beds only) |
| furniture: 24 | `rug-*` (4) | rugs are not model elements |
| fixture: 2,490 | garden uplights 2,240, vent grilles/valves 184, curtain tracks 60, hatch shutter box 6 | not model elements |
| dressing: 264 | north climber (108), feature stone (156) | no plant / garden element |
| ground: 274 | lawn 233, gravel 20, tree pits, bench slabs, accent bed | not model elements (beds and paths are) |

Reverse view (model elements that no mesh refers to): 19 luminaires (`COVE`, `TOE`, `NL` strips: light only, no body
mesh), 28 `prop-*` and the 3 plants that are imported glTF `models[]` rather than meshes (their `models[].id` /
`replaces` already identify them), `room-stair-gf`, `slab-gf-terrace`, `wetzone-gwc-shower`, `garden-north-patio`.
Every wall (36), door (18), window (8), column (9), beam (24), railing (6), context element (58), `furn-` furniture (52
of 52 non-prop) and 6 of 7 `fixture`/`wetzone` elements appear in at least one mesh.

Face-level faces-by-element ownership of the shell: 1 coincident end face is shared by `wall-B-ext-09` and
`wall-B-ext-16`; the first owner is kept (conflicts are recorded in `Registry.conflicts`).

## Hash evidence (appearance unchanged)

Baseline = `json.dumps(scene, sort_keys=True)` of an unmodified `e645041` build (`benchmark_scene_build.py
--baseline B --record-baseline`): 631,340,470 bytes, sha256
`b3075f187bf503cfc8624c55a3ac3da388e64a96d4cdfc365ee2d4a4e89e9aca` (reproduces the value in `P-pipeline.md`).

| build | bytes | sha256 |
|---|---|---|
| baseline `e645041` | 631,340,470 | `b3075f187bf503cfc8624c55a3ac3da388e64a96d4cdfc365ee2d4a4e89e9aca` |
| patched, ids stripped (`--strip-ids`) | 631,340,470 | `b3075f187bf503cfc8624c55a3ac3da388e64a96d4cdfc365ee2d4a4e89e9aca` (`byte_identical: true`, 97 s build) |

Per-key comparison (`sha1(json.dumps(scene[k]))` for every top-level key and every `meshes[i]`): **0 differing keys**
between the baseline and the patched build with the three fields stripped. A first patched build differed in
`_ceiling_sources` and `draped_appearances` (they hold references to / copies of the mesh dicts); that is why `attach`
runs last and why declarations are kept out of the mesh dicts.

With ids kept, `scene_bytes` of the written `scene.json` (`--write-scene`, provenance + exposure groups) is
631,741,125 against 631,583,581 for lane P's `e645041` scene (+157,544 bytes of ids, plus a new `source_hash`
because source files changed): sha256 `eded62a3cd2cce314e76987d01799f62b8df6722b38bede19089e5d1b0e17fcf`. `write()`
passed `validate_scene` and the frozen exposure-group check on it.

**Render** (`v08-cinema`, 32 samples, 800x500, Blender 4.5.14 through `jobq`, jobs `P2-render-before` /
`P2-render-after`, same command, same `villa_scene.py`): before = lane P's `e645041` `scene.json`, after = the patched
`scene.json` with ids. Pixels: maximum difference 1/255, 634 of 1,200,000 channel values differ (mean 0.0005): GPU
path-tracing noise, not geometry (`evaluated_meshes_sha256` is identical in both `scene-receipt.json`; the
`authored_scene_sha256` differs only because `provenance.source_hash` differs). The Blender side loads through
`without_ids`, so ids never reach the renderer.

## How a check looks up an element's faces

```python
from archpipe.blender.element_ids import faces_of
for mesh, faces in faces_of(scene, "wall-B-ext-03"):     # [(mesh dict, [polygon, ...])], metres
    ...                                                  # shell meshes split by faces_by_element, others whole
```
Coverage / gaps for any scene: `python -m archpipe.blender.element_ids scene.json [--model d1-elements.json]`
(exit 1 if an uncovered mesh has no stated reason). Count faces per element of a kind by iterating
`faces_by_element` (or `len(faces)` when absent). Treat `element_id_basis` as evidence strength: `face-tracked` /
`declared` are exact, `face-registry` allows 2 mm, `generator-name` trusts the generator's own id.

## Lessons (principle 7)

* Defect: first attach point broke `furniture_stage2` ("changed sections: architecture") and left stale copies in
  `_ceiling_sources` / `draped_appearances`. Why missed: receipts hash whole mesh dicts, not geometry. Guard: the
  per-key stripped comparison above, and `test_attach_strip_roundtrip_and_coverage`.
* Defect found on the way: the frozen exposure-group record is invalidated by any new mesh field. Guard:
  `without_ids` at the consumers and the written-scene run (`write()` passes `require_record` and `validate_scene`).
* The base does not build (see top); a scene-build smoke for the integration branch would have caught it at the lane D
  merge.
