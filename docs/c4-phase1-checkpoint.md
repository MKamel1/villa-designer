# C4 Phase 1 checkpoint: finished-surface mounting

The per-component inventory is [c4-mounting-inventory.csv](c4-mounting-inventory.csv). It is generated from the current `out/villa/render-d1/scene.json` by `scripts/audit_mounting.py`; 582 scene components are listed separately by identifier. Multiple components of one fitting have separate rows. An empty `finished_face_error_mm` means the error cannot be measured from the current input, **not** that it is zero. `datum_gap_mm` is a measurable distance to the existing modeled datum and is not automatically a defect.

## Diagnosis

The direct cause is that mounting positions are calculated from unrelated room rectangles, fixture emitter positions, furniture backs, or wall bounds. The escape is that existing checks cover light levels, visual support, and some room clearances, while the finish schedule (`villa_render.FINISH`) names materials without their build-up thickness or a host identifier. The class is an item mounted on a building surface without a declared finished host face. Related records: l0856, l0551, l0119, l0096, l0692, the library nook swing-lamp record, and the manually concealed C3 ducts. The same class can affect every listed fixture and fixed furnishing, including other villa options.

The existing scene often assigns a finish material to a structural or zero-thickness shell face. Therefore a structural-to-finished-face error cannot be inferred from the material name. Phase 1 does not invent plaster, marble, tile, board, or cladding thicknesses. The inventory reports the measured geometric datum gap where available and leaves the actual finished-face error open until an assembly record exists.

## Inventory summary

| Site family in D1 | Count in scene | Current reference and measured result |
|---|---:|---|
| Stair wall handrail | 1 | Stated plaster face at y = -28.471 m; nearest rail face y = -28.386 m, **85 mm projection**. It was previously buried; the current offset is ad hoc and has no host binding. Four wall brackets and the stringer plate use the old wall datum. |
| Recessed downlights | 82 trims and 84 lens components | The design takes emitter height from `ceiling_z`; the trim is drawn 1.5 mm below it. Housing depth and clear void are not exported, so body fit is unmeasurable. Historic bedroom l0119 exceeded its 2700 mm ceiling by 32 mm. |
| Ceiling surface fittings, pendants, coves and strips | Individually listed in the inventory | Rain-head drops reach the modeled ceiling (0 mm gap). Two extract valves start 3 mm below the modeled ceiling and extend 12 mm below it. Three storage batten bodies have mounts reaching the soffit. Other cords, wires, canopies and strips use local offsets without a declared host. |
| Wall sconces, swing lamps, wall reading lamps and markers | Individually listed | The two swing plates now come from side-panel positions; no finished panel thickness is recorded. Six markers are 1 mm proud of the modeled wall face; whether that face includes finish is unstated. Other wall lights use fixture positions or wall rectangles and cannot be assigned a finished-face error. |
| Mirrors, riser rails, rain heads, grilles and valves | 3 mirrors, 4 riser-rail parts, 8 rain-head parts, 2 grilles, 2 valves, plus brackets | Mirror backs follow basin envelopes, without a wall host. Hand-shower bracket endpoints are placed 20 mm inside structural wall bounds; finish build-up is absent. External grilles reach the modeled exterior face (0 mm datum gap), but exterior coating thickness is unknown. |
| Television, wall-hung sanitaryware, fixed shelves and joinery | Individually listed | Television and sanitaryware inherit furniture envelopes and clear room rectangles. Shelves, wall units, wardrobes, kitchen runs, curtain tracks and wall panels use local geometry. The current clear rectangle moves furniture inside by 200 mm at the envelope or half a partition thickness at enclosed rooms, curing l0551's outline placement, but the final finish layer remains unrecorded. |
| Trellis and climbers | 4 trellises, 4 climbers, 4 branch sets | Trellises use fixed world coordinates; climbers follow their frame. None declares its boundary-wall finished face. |
| Wall art | 0 placed | The picture-frame asset is currently omitted because its front is empty; there is no active wall-art mounting site. |

The two omitted visible service ducts from C3 have no scene mesh to measure; their authored Revit service routes still require a coordinated ceiling void and host record. Stair treads and adjacent wall faces still use separate datums (`villa_render.py` hard-codes y = -28.671 m), so the 200 mm difference to the stated plaster face is not an authored build-up and cannot be reused as one.

## Phase 1 API and proof

`archpipe.concept.mounting` now declares a building host, structural point, outward normal, finish name and build-up thickness, and optional clear void. `mount(item, host, face, offset, kind)` returns the finished face and world fixing position. A recess fails if its fixing depth plus housing depth exceeds the declared clear void. The API has no D1 identifiers. Focused tests freeze the stair datum and current plaster face, a 32 mm housing against a 25 mm void at the 2700 mm ceiling, a 25 mm marble cladding, a 15 mm plaster build-up, and a finished floor. The API is not wired into D1 during Phase 1.

## Phase 2 migration plan

1. Declare finish build-up thickness, structural near-face, normal and clear void for each D1 wall, ceiling, floor, stair stringer and joinery panel, including room-specific marble, tile, plaster, ceiling board and exterior coating. Review those records before using them to move geometry.
2. Bind each row of the inventory to a host and one of the four mounting kinds. Migrate lighting design, rain heads and valves, sanitaryware, mirrors, furniture, joinery, trellis and climbers in small packages. Derive treads and adjacent wall faces from one structural datum. Delete local face offsets only after their intended projection, recess or fixing depth has been recorded.
3. Export host, finished face and mounting parameters with scene objects. Add an unconditional scene/spec guard for missing hosts, housing beyond void, and measured proud/buried positions. Freeze the real l0856, l0119 and sibling cases; prove the guard fires and stays quiet on clean cases, then preview the first migrated package before integrating it.
4. Have the lead approve any actual movement where measured burial or floating is found. Keep intended design elevations and locations otherwise.
5. Retire `v14-dressing` (same camera as `v31-dressing-hers`), keep `v31-dressing-hers` and `v32-dressing-his`, and update its captions, exposure cohort fixture, review lists and tests in Phase 2.

No D1 placement or camera was changed in Phase 1.
