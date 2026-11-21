# RV1 stage 2a: independent built-scene checks (Revit replacement)

Code: `src/archpipe/parity/` (own geometry in `geom.py`; scene/IFC/box loaders in `world.py`, `ifc_kernel.py`).
Tests: `tests/parity/`. CLI: `python -m archpipe.parity.run_d1 --scene S --ifc I`.
Independence: no module in `src/archpipe/parity` imports `concept.revit_spec`, `concept.villa_daylight`,
`concept.villa_render`, or the model generator (`model.export` etc.); `tests/parity/test_independence.py` enforces it.
The design model JSON (`src/archpipe/model/data/d1-elements.json`) is read only as the *intended* side of a comparison.

## PRE-REGISTRATION (written and committed before any mutation was run)

### Checks (id, replaces, method)

| id | replaces | measures |
|---|---|---|
| K01 stair-structure | D01 D02 I08 U12 | stair surfaces crossing column/beam/slab/wall surfaces (triangle-triangle crossings, touching excluded) |
| K02 wall-slab | D03 U10 | wall surfaces crossing ramp/deck surfaces |
| K03 opening-column | D05 U11 | door/window surfaces crossing column surfaces |
| K04 door-soffit | D04 U10 | clearance from door head to the first surface overhead (vertical rays) |
| K05 window-credit | D06 U11 I04 | each model window has glass faces in the scene, with width/sill/head as modelled; doors likewise for width/height |
| K06 glazing-to-beam | D07 | full-height windows: glass from floor to the soffit above, gap measured by ray |
| K07 fixture-ceiling | D08 U03 U02 | non-recessed fixtures do not pass the ceiling; emitter datum vs intended height |
| K08 bbox-catalogue | D09 U04 | built item bounding box vs catalogue/model size |
| K09 identity | I09 D10 D11 D12 U18 I10 | every model element built exactly once, no unowned mesh, details carry ids |
| K10 placement | D12 U18 | built position and yaw vs model (rotation dropped is caught here) |
| K11 net-area | D14 U19 | room floor area from scene floor faces vs frozen Revit area |
| K12 environment | D13 U13 U17 | kept columns, slabs, beams, context shapes, levels vs frozen env read-back |
| K13 detail-solids | I10 D10 D11 | hatch, buildout, rail, vent, swing-lamp solids exist and carry ids |
| K14 guards | D21 | a guard of at least its modelled height at every modelled drop edge |
| K15 mounting | D19 | wall-mounted fittings touch their host face, facing into the room; glazed-door intent glazed |
| K16 stair-headroom | D16 | vertical clearance above every tread nosing, sampled by rays |
| K17 ifc-clash | I01 | the same crossing test on the IFC export through IfcOpenShell geometry (second kernel) |
| K18 datum-levels | I02 D20 | storey z of built elements vs frozen level table |

### Seeded mutation set (each applied in memory to a copy of the D1 scene; originals untouched)

1. M1 wall into the ramp: `wall-B-ext-07` translated (0, -0.5, 0) into the ramp interior. Expect K02.
2. M2 door head vs soffit: the head of `door-B-cinema-store-ramp` (all vertices above its mid-height) raised 0.30 m
   so the head stands above the soffit overhead (the D04 geometry: leaf taller than the clear height). Expect K04.
   Negative control: head 5 mm below the soffit must stay quiet.
3. M3 window removed while credited: all surfaces of `window-GF-kids-a-3` deleted from the scene, model unchanged. Expect K05.
4. M4 fixture through the ceiling: the first pendant luminaire raised 0.60 m. Expect K07.
5. M5 tread into a column: `stair-main` translated toward the nearest kept column until it penetrates 30 mm. Expect K01.
6. M6 rotation dropped: the first furniture item with model rotation 90 or 180 and unequal plan sides gets its surfaces
   rotated back by that angle about its centre. Expect K10.

One per check beyond those: K03 door translated 50 mm into the nearest column; K05b glass width halved;
K06 glass top lowered 0.30 m; K07b emitter datum moved 0.25 m; K08 item scaled 1.15; K09 element deleted and element
duplicated; K11 0.2 m strip removed from one floor; K12 column moved 20 mm; K13 a detail mesh deleted; K14 stair-void
guard deleted; K15 sconce moved 0.30 m off its wall; K16 soffit above the stair lowered 0.30 m; K17 an IFC wall moved
into the ramp; K18 B-level slab shifted 0.10 m.

Negative tests per check: a legitimate near-case that must stay quiet (door 5 mm below soffit, touching-not-penetrating
join, 1 mm scene rounding, item scaled 1 mm).

Recall reporting rule: a miss is reported as a miss with its cause. Nothing is tuned after seeing a result; any
change made after the first run is listed in the "Changes after first run" section below.

## Check reference: resolution limits and SourceCards

All thresholds are SourceCards (`src/archpipe/parity/sources.py`): `policy` where ours, the two published ones are read from
`knowledge/eg/best-practice-cards.json` (`ukadk-stair-headroom-min`: 2 m over flight and landings, Approved Document K Diagram 1.3;
`ukadk-guarding-height-external` is held there but K14 compares against the modelled height, not the published minimum).
"Resolution" is what the check cannot see; a pass never claims more.

| check | threshold (card) | resolution limit |
|---|---|---|
| K01 K02 K03 K17 | crossing depth <= 2 mm scene / 0.05 mm exact boxes (`RV1-TOL-SCENE`, `RV1-TOL-EXACT`) | scene vertices are rounded to 1 mm, so a contact below 2 mm is invisible in the scene. D02 (0.2 mm) is caught only on exact box geometry. "Depth" is the poke-through of the shorter side of the crossing triangles (exact for boxes). K02 allows half a wall thickness of plan overlap (a join at the slab edge) |
| K04 | head <= soffit (`RV1-SOFFIT-CLEAR`) | vertical rays at 3 points across the door; the first surface above, excluding the door and its host wall |
| K05 | 10 mm (`RV1-TOL-FIT`) | pocket and sliding doors show retracted panels: width is not measurable, only height |
| K06 | gap <= 150 mm (`RV1-GLAZE-HEAD`, policy) | one ray at the glass centre; one full-height window in D1 |
| K07 | 10 mm, pendant top <= ceiling + 2 mm (`RV1-TOL-FIT`) | only pendant and recessed mounts; the scene datum of a task lamp is not the modelled placement and is not compared |
| K08 | 5 % or 10 mm (`RV1-TOL-CAT`) | stated size parsed from the Revit type name; items with no size in the name are not evaluated |
| K09 K13 | exactly one build; every face carries an id | luminaires drawn only as a light source (cove, strip) have no mesh and read as "built 0 times" |
| K10 | footprint contains the carcass within 10 mm; centre within half the smaller side + accessories (`RV1-TOL-FIT`) | an axis-aligned footprint cannot see a 180 degree turn (M6-180 misses) or a 0.1 m shift of a large item |
| K11 | 1 % of area (`RV1-TOL-AREA`) | scene floor mesh area, not Revit's room boundary |
| K12 | 2 mm (`RV1-ENV`) | asks that a face exists within 2 mm of each Revit plane; it does not prove nothing extra is there |
| K14 | built height >= modelled (`RV1-GUARD`) | height of the tagged surfaces; does not test the infill or the fixing |
| K15 | 10 mm (`RV1-MOUNT`) | needs a mounting_hosts record and a wall-plate part |
| K16 | 2000 mm (`ukadk-stair-headroom-min`) | 20 mm sampling along the pitch line between nosings; first surface overhead |
| K18 | 10 mm (`RV1-TOL-FIT`) | median sole of hinged doors per level |

## Row coverage

U02 U03 U04 -> K07 K08 K10 (bedroom Revit path retired; the same checks run on the frozen bedroom meshes); U10 -> K02 K04; U11 -> K03 K05;
U12 I08 -> K01 K17; U13 U17 -> K12; U18 -> K09 K10; U19 -> K11; I04 -> K05; I09 -> K09; I10 -> K13; D01-D14, D16, D19, D21 as in the recall table.

## Changes after the first run (nothing is tuned to pass; each is a defect in my check or mutation, found by looking at real data)

1. `geom.fan` replaced by ear clipping (lessons/RV1 entry 1). Removed two false findings (K01 23 mm, K16 64 mm).
2. K02: a wall now fails only when its plan overlap with the slab exceeds half its thickness (join rule), measured from the VERTICAL
   faces of both (lessons 2, 6). Before this the D1 scene showed 5 "walls through the ramp/deck"; four were joins at the edge and one
   came from finish skins tagged to the deck.
3. K10: the centre-offset bound became half the carcass's smaller side plus accessory slack (plumbing items use a different placement convention).
4. K09: duplicate detection needs at least half of an element's triangles duplicated (coincident skins are common in the scene).
5. Mutations: M1 was a valid geometry and is reported as a miss; M1b added; M5 and K03 read the column faces from the model (lessons 2, 3);
   M6 split into 90 and 180 degrees; M-K16/N-K16/M-K17 added (K16 and K17 had no D1 mutation); the first N-K16 put the soffit 2.01 m above one
   pitch point but the 0.6 m box also sits over higher points of the rising flight (a wrong negative, not a false alarm): rebuilt at 2.26 m.
6. D03 reproductions use a 10 mm tolerance because the Revit read-back reports wall tops to 10 mm (lessons 4).
