# Lane SC: scene completion (2026-11-21)

Base `origin/integ/staging` `e8aea48`. Goal: the production D1 scene builds every model element that has physical form, with
its element id, so renders and the RV1 independent checks can be trusted. Code: `src/archpipe/blender/g1_geometry.py` (new),
`blender/element_ids.py`, `concept/villa_render.py`. Tests: `tests/test_villa_render_g1_geometry.py` (14, each with a negative twin).

## Per item: missing or untagged, fix, evidence (RV1 on the same IFC, before = INT2's scene at staging, after = SC production scene)

| item | diagnosis | fix | RV1 before -> after |
|---|---|---|---|
| `rail-gf-terrace-edge` | **missing** (spec `guards` and Revit had it, the scene builder drew only the stair-void guard) | glass guard on the spec path, 1100 mm, 12 mm closed panes meeting face to face (`G1.glass_guard`), mesh `detail-guard-gf-terrace-edge` | K14 fail -> pass, K09 fail -> clear |
| `rail-patio-steps-edge` | **missing** | stainless flat bars 25 x 6 mm, clear opening 74.2 mm (spec max 75), top rail 40 x 20, 1100 mm (`G1.bar_guard`), `detail-guard-patio-steps-edge` | K14 fail -> pass, K09 fail -> clear |
| other guards (all 8 `railing` elements checked) | `rail-gf-stair-void`, `rail-stair-open-glass`, `rail-stair-wall-handrail`, `rail-edge-0/1/2` already built and tagged | none | K14 3/3 pass (was 1/3) |
| G1 stair riser infill | **missing** (a spec key only) | 15 horizontal flat bars 40 x 10 mm in the 116.5 mm riser gaps, `detail-stair-riser-infill`, id `stair-main` (the infill is a parameter of the stair; the model has no separate element) | not covered by a check on the stair; v11 shows the bars |
| `joinery-understair-cupboard` | **missing** | stepped side wall, toe panel, end wall, closed oak leaf with a pull (`G1.understair_cupboard`), 5 meshes | K09 fail -> clear |
| `slab-B-floor`, `slab-GF-floor`, `slab-gf-terrace` | **built, tagged `env-slab-B/GF/GF-front`** (villa_env slabs with the same outline and level); the model's basement slab also covers the east extension, built as `env-yard-ours` faces | re-tagged: `MODEL_SLABS`, and the yard faces inside the model outline (`_footprint`) go to `slab-B-floor`; context slabs (APT, roof, sister yard) keep `env-` ids | K09 3 fails -> clear |
| `wetzone-gwc-shower` | **built, tagged only `furn-gwc-shower`** (the wet-floor part has the wet zone's size and position) | the wet-floor mesh declares both ids (shared: every id owns every face) | K09 fail -> clear |
| 89 meshes without ids | 85 genuinely not in the model; 3 are model elements; 1 had two ids and no per-face split | see "Identity" below | K13 89 fails -> 0 (pass), unowned meshes 89 -> 0 |

### Identity (item 4)

* 3 given a model id (by outline/centre against the model): `landscape-accent-bed-north` = `garden-bed-north-accent` (exact outline),
  `landscape-tree-pit-south` = `plant-landscape-tree-south` (centred on the tree), `landscape-g6-bed-south-espalier` = `plant-landscape-g6-loquat-plant`.
* 1 (`finish-stair-stacked-slab-edge`): it already named two walls but gave no per-face owner, which a strict loader reports as unowned. A declared
  multi-id mesh is now **shared** (every id owns every face), `faces_by_element` filled by `attach`.
* 85 tagged `nonmodel-<class>` (basis `non-model`): garden-structure 43, garden-uplight 12, curtain-track 10, kitchen-hatch 5,
  garden-surface 5, rug 4, ventilation-fitting 4, garden-planting-dressing 2. An unexplained mesh stays unresolved and `tag_non_model` returns it
  (test). RV1 K09 lists the 8 classes as "informational" (not_evaluated), never as failures.
* final scene: 0 meshes without ids.

## Luminaires and props (item 5): decisions

K09 reads meshes only, so these remain K09 findings until the check reads `scene["element_contract"]` (written by this lane:
`light_only{id: kind, reason}` and `imported_props{id: asset, position}`). RV1 is not an SC path; the change it needs is one clause in
`k09_identity`: skip an id listed in `scene["element_contract"]["light_only"]` or `["imported_props"]`.

| class | count | decision | reason |
|---|---|---|---|
| `VSTRIP` 03/04/05 | 3 | **built** (`detail-vstrip-*`, 20 x 12 mm opal housing, no emission, light unchanged) | visible strip on the wardrobe front face; stands on the face, no crossing, mounting guard quiet |
| `VSTRIP-ext` 01/02 | 2 | light only | the model puts them 20 mm behind the wall plane their wardrobe stands against; built geometry fails the mounting host guard (finished-face error 32 mm). Position is the lighting lane's |
| `COVE` | 5 | light only | concealed behind the cove fascia, which is built (`ceiling-<room>` lip) |
| `NL` | 4 | light only | recessed night strips in the skirting line, no visible body |
| `TOE` | 3 | light only | recessed behind the plinth |
| `RAIL` | 2 | light only | inside the wardrobe (the scene's wardrobe is a solid carcass) |
| `MIRROR` | 1 | light only | the model puts the bar 47 mm off the wall with no host; a body would float (open item) |
| `prop-*` | 28 (33 props incl. plants) | built, **as imported glTF assets** from `scene["props"]` | they are placed by Blender at the stated position; recorded in `element_contract.imported_props` |

## K06 `window-B-dirty-kitchen-0` (report only)

Not a beam. The window (`full_height`, sill 0, height 2300) sits in `wall-B-ext-16` (x 15.312, 2.65 m high, top z -0.35). Rays up from the glass head
(z -0.700): the host wall's own header to its top at -0.351/-0.350, then the extension roof slab `slab-roof-0` soffit at **-0.200** (2.80 m above the
floor). So the glass stops 2.30 m up under a 2.65 m wall under a 2.80 m soffit: K06's 500 mm gap is 350 mm of wall header plus a **150 mm open slot
between the wall top and the roof soffit** (the model's other east-end wall, `wall-B-ext-17`, is 2.80 m). This is the D07 class (glazing short of the
structure, not a beam to be added to the check's band) plus a second model inconsistency: `wall-B-ext-16` is 2.65 m where the roof above it is at 2.80 m.
The 2.30 m is the standard window head (`HEAD`), applied to a window marked full-height. No design change made.

## Departures from the model (all forced, all reported)

* **Cupboard is 128 mm shallower than modelled** (872 vs 1000 mm; K10 now reports `joinery-understair-cupboard` short by 128 mm, centre 11 mm off).
  The model's side wall (y -27.571..-27.471) and structural back face (-28.471) are where the scene's ASSUMED steel is (open-side stringer, base shoe,
  glass at y -27.536..-27.496; wall stringer bearings and plate to y -28.396). Panels were first built to the model and crossed the steel by up to 177 mm
  (11 crossings); they now stop at the steel (`G1.steel_clear_y`, read from the built meshes). Interior volume about 2.2 m3 against 2.62 m3. Needs a
  lead decision: move the assumed steel, or change the model's cupboard to the built one.
* Each cupboard step ends where the next lower tread begins (the 16 mm G1 tread overlap), as RA2 did for the soffit check.
* Riser bars span the tread between the steel members (y -28.396..-27.536) rather than the full 950 mm; the slot at the tread edge is 65 mm, under the 100 mm sphere.
* Guards have no base-shoe geometry (the model says "in a base shoe"; the existing stair-void guard has none either).

## Receipts, exposure, production scene

* **Receipt sections reviewed baseline-relative** (RA method): staging tree and SC tree both exported with receipts bypassed
  (`refresh_furniture_integ5.py export`), `section_diff.py`: layout, specification, furniture, architecture, meshes, models, props, materials **all unchanged by SC**
  (`evidence-sc/section-diff-vs-staging.json`): the 11 new meshes (guards 2, infill 1, cupboard 5, strips 3) are outside every receipt room.
  The staging receipts were already stale before SC (a build with receipts active fails on `origin/integ/staging` itself: "changed sections: meshes"):
  the only changed meshes against INT2's pre-approval scene are `marker-PATH-landing-gf-01/02` (lead approval `158023a`). 16 individual + joint
  reviews: all ok, 0 findings (`evidence-sc/room-review-summary.json`); `refresh_receipts.py` rewrote `furniture-stage2.json.gz`, `parents-bed.json.gz`
  (room_context `b0d60ad21e1c8a06` / `03eb73a322988584`).
* **Exposure groups re-measured** through the documented Blender procedure (`write(measure_exposure_groups=True)`, then `villa_scene.py
  --measure-exposure-groups` via jobq `SC-measure-exposure-2`), record copied byte for byte. Result: transport hash changed (new meshes); sums moved
  by under 1 %; **one group flips: `v37-north-garden-lounge` exterior-shade -> exterior-day** (solar fraction 0.4983 -> 0.5023 across the 0.5
  threshold). The measurement is deterministic (staging and INT2 give identical 0.4983), so the shift is the new terrace guard in that frame, not noise.
  v37 will be exposed as exterior-day.
* **Production build** (`scripts/benchmark_scene_build.py --write-scene`, receipts and exposure record active, no bypass, jobq `SC-prod2`, 353 s):
  scene.json 631,331,061 bytes sha256 `6cb3e29198365a7d614af715262dee72cce3d80725682598d2cadfb7d0f9ba33`; ids stripped (`json.dumps(without_ids(scene), sort_keys=True)`)
  `59e6ff79a67014e33712bdcd96643cea26b2ba244d675b76cd7847471e9754e3`; **1,223 meshes** (staging 1,212: +11), 64 lead-approved rows, `source_hash`
  `a31e85b7137f4da4def8d821d8c6316fdb5db702d8ff1716029f8b77948fbc86`. The file hash includes `provenance` (HEAD, dirty flag).

## RV1 on the production scene (`--prove`)

Checks (pass/fail/not evaluated), changed only: K09 0/55/0 -> 0/45/8; K13 0/89/0 -> 1/0/0; K14 1/2/0 -> 3/0/0; **K10 50/2/0 -> 50/3/0** (the cupboard depth above).
All other checks identical. Recall: 40/40 frozen reproductions as expected, identical rows before and after. Mutations: 39, 36 caught as before; the same
three documented misses (M1, M6-180, M-K10-move0.1), nothing dropped. K09 remaining 45 = 28 props + 17 light-only luminaires (decisions above).

## Previews (draft, 32 samples, 800x500, jobq GPU jobs, each looked at; `knowledge/approvals-review/previews-sc/`)

* `v11-stair-void.png` (production scene): open-riser flight; between every pair of treads a thin dark horizontal bar now closes the riser gap; glass guard on the open side, handrail on brackets. Nothing floats; bars read as part of the steel.
* `v29-under-stair-store.png` (production scene): very dark draft (store lights off, as in RA2). The cupboard end wall shows as a pale painted panel at the left under the soffit; the oak leaf at centre-right is the existing store door. Not judged for lighting; the two views below show the cupboard properly.
* `sc-cupboard-front.png`, `sc-cupboard-oblique.png` (lounge evening state, camera added for the preview): a pale painted side wall under the flight, its top stepping with the tread undersides and stopping below the black stringer; an oak access leaf with a small pull, flush with the wall; sits on the floor, nothing clips.
* `sc-terrace-edge.png`: the glass guard stands on the terrace slab edge (faint top edge and its reflection), corner turning to the ramp side; over a 3.0 m drop to the patio.
* `sc-patio-steps.png`: vertical stainless bars with a top rail on the steps' north edge, standing on the paving, the patio court and the terrace glass edge beyond; nothing floating.
  (The two terrace/patio cameras and the two cupboard cameras are preview-only views injected into a copy of the SC scene built by the same code; they are not part of the production views.)

## Open items

1. Cupboard depth (above): lead decision, and K10 will keep reporting 128 mm until the model or the steel moves.
2. RV1 K09 should read `scene["element_contract"]` (45 K09 findings are intended light-only or imported props).
3. `VSTRIP-ext-01/02` and `MIRROR-parents-ensuite-06` positions: lighting lane (L6d).
4. K06 / `wall-B-ext-16`: 2.65 m wall under a 2.80 m soffit, glazing to 2.30 m (design decision, not changed).
5. v37 changes exposure group (exterior-day); the lead should know before v37 is re-presented.
6. Receipts/exposure/scene are generated files: after `origin/integ/staging` takes INT2's refreshed receipts and L6d's lighting, merge and repeat the last step (SC adds no receipt change of its own, so INT2's receipts should hold; the exposure record must be re-measured again).
7. `python scripts/lane_guard.py SC` compares with `origin/integ/aplus` by default and lists staging's 114 files; against `--base origin/integ/staging` it is clean.
