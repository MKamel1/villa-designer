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

## Results (run `python -m archpipe.parity.run_d1 --scene S --ifc I --prove`)

Primary run: INT2's built production scene (INT2 was still 'running' when this was produced; the scene file is the one it had built at 16:31, model data merged from `origin/lane/INT2`). Earlier run on RA2's scene (sha256 `f7a7fe76418a04ff1fe75b2fdfe8596e095783bb2923155fd303afa35b9ee7b3`): same check results except K10 (stair-flight-store 1.80 vs 1.20 m, fixed in the INT2 model) and 24 more K09 luminaire ids; mutation and recall results identical.

Scene `/home/omar/archpipe/lanes/INT2/out/int2/prod/scene.json` sha256 `045f0487868e3bce8af21d1ed298ec4df4081a8d1fd7657cd1e250eaaeb0b77f`  
IFC `/home/omar/archpipe/lanes/INT2/out/exchange/D1/D1-ARCH.ifc` sha256 `8598f929cd05dc4e2a320f299f8fc4b3df9a5626436c229581cf606917b86b5a`

### Checks on the D1 scene and IFC

| check | pass | fail | not evaluated |
|---|---|---|---|
| K01 | 1 | 0 | 0 |
| K02 | 6 | 0 | 0 |
| K03 | 1 | 0 | 0 |
| K04 | 18 | 0 | 0 |
| K05 | 25 | 1 | 0 |
| K06 | 0 | 1 | 0 |
| K07 | 73 | 3 | 0 |
| K09 | 0 | 55 | 0 |
| K10 | 50 | 2 | 0 |
| K11 | 12 | 13 | 2 |
| K12 | 90 | 0 | 0 |
| K13 | 0 | 89 | 0 |
| K14 | 1 | 2 | 0 |
| K15 | 2 | 0 | 0 |
| K16 | 1 | 0 | 0 |
| K17-K01 | 1 | 0 | 0 |
| K17-K02 | 3 | 0 | 0 |
| K17-K03 | 1 | 0 | 0 |
| K18 | 2 | 0 | 0 |

### Scene vs IFC kernel, per clash pair

No pair fails in either the scene or the IFC: they agree on every clash tested.

### Recall on the frozen reproductions

| row | source | check | subject | expected | got | ok |
|---|---|---|---|---|---|---|
| D01 | historic | K01 | r3 party-wall flight | fail | fail | True |
| D01 | historic | K01 | U-stair in the old bay | fail | fail | True |
| D01 | historic | K01 | party-wall flight, corrected | fail | fail | True |
| D01 | historic | K01 | U-stair along the party wall | fail | fail | True |
| D01 | historic | K01 | party-wall flight (r8, landing 1.2 m) | fail | fail | True |
| D01 | historic | K01 | U-stair in the street-end bay | fail | fail | True |
| D02 | historic-reconstructed | K01 exact |  | fail | fail | True |
| D03 | historic-reconstructed | K02 | P3 | fail | fail | True |
| D03-fixed | control | K02 | P3 | pass | pass | True |
| D03 | historic-reconstructed | K02 | P4 | fail | fail | True |
| D03-fixed | control | K02 | P4 | pass | pass | True |
| D04 | historic-reconstructed | K04 |  | fail | fail | True |
| D04-fixed | control | K04 |  | pass | pass | True |
| D05-asbuilt | control | K03 | P3 | pass | pass | True |
| D05-asbuilt | control | K03 | P4 | pass | pass | True |
| D05 | synthetic | K03 | entrance over column 1590377 | fail | fail | True |
| D06 | control | K05 (credit vs built) |  | pass | pass | True |
| D06 | synthetic | K05 (credit vs built) |  | fail | fail | True |
| D07 | historic | K06 | P3 | fail | fail | True |
| D07 | historic | K06 | P4 | (info) | fail | True |
| D08 | historic | K07 | LT-02 | fail | fail | True |
| D08 | historic | K07 | LT-03 | fail | fail | True |
| D08 | historic | K07 | LT-05 | fail | fail | True |
| D08 | synthetic | K07 | LT-01 shade top 2717 vs ceiling 2700 (LEARNINGS l0096) | fail | fail | True |
| D09 | historic | K08 |  | fail (families whose bbox does not match | fail | True |
| D10/D11/D12 | control | K09 |  | pass | pass | True |
| D10 | historic | K09 keyed on Mark only (the old post-condition) |  | fail | fail | True |
| D11 | synthetic | K09 |  | fail | fail | True |
| D12 | synthetic | K09 |  | fail | fail | True |
| D12 | control | K10 (bbox vs spec) |  | (report) | pass | True |
| D12 | synthetic | K10 (bbox vs spec) |  | fail | fail | True |
| D13 | control | K12 |  | (report) | pass | True |
| D14 | historic | K11 (1 % band) | flex | fail | fail | True |
| D14 | historic | K11 (1 % band) | kitchen | (below band) | pass | True |
| D16 | historic-reconstructed | K16 | opening to x 8.537 | fail | fail | True |
| D16 | control | K16 | opening to x 8.887 | pass | pass | True |
| D19 | synthetic | K15 |  | fail | fail | True |
| D19 | synthetic | K15 |  | pass | pass | True |
| D21 | synthetic | K14 |  | fail | fail | True |
| D21 | synthetic | K14 |  | pass | pass | True |

### Mutation set

| id | check | kind | expected | result | detail |
|---|---|---|---|---|---|
| M1 | K02 | mutation | catch | quiet **(MISS)** | wall-B-ext-07 translated (0,-0.5,0) into the ramp |
| N-K02 | K02 | negative | quiet | quiet | wall moved 0.5 m away from the ramp |
| M1b | K02 | mutation | catch | caught | cross wall wall-B-int-11 (top 10 mm under the ramp soffit) raised 0.7 m through the ramp |
| M2 | K04 | mutation | catch | caught | door-B-cinema-store-ramp head raised 0.30 m (clearance was 112 mm) |
| N-K04 | K04 | negative | quiet | quiet | head raised to leave 5 mm below the soffit |
| M3 | K05 | mutation | catch | caught | all surfaces of window-GF-kids-a-3 deleted |
| M-K05b | K05 | mutation | catch | caught | glass width halved |
| N-K05 | K05 | negative | quiet | quiet | glass 3 mm narrower |
| M4 | K07 | mutation | catch | caught | pendant raised 0.60 m |
| M-K07b | K07 | mutation | catch | caught | emitter datum 0.25 m too low |
| N-K07 | K07 | negative | quiet | quiet | pendant 5 mm low |
| M5 | K01 | mutation | catch | caught | stair-main shifted [-1.23, 0.0, 0.0] m: 30 mm into column-06 (gap was 1200 mm) |
| N-K01-touch | K01 | negative | quiet | quiet | stair exactly touching the column |
| N-K01-gap | K01 | negative | quiet | quiet | stair 5 mm short of the column |
| M-K03 | K03 | mutation | catch | caught | door-B-dining-yard 50 mm into column-03 |
| N-K03 | K03 | negative | quiet | quiet | door 5 mm clear of the column |
| M6-90 | K10 | mutation | catch | caught | furn-lounge-armchair (model rotation 90, carcass 946x794) rotated back to 0 |
| M6-180 | K10 | mutation | catch | quiet **(MISS)** | furn-k-run (model rotation 180, carcass 2010x600) rotated back to 0 |
| M-K10-move | K10 | mutation | catch | caught | furn-lounge-sofa moved 1.0 m |
| M-K10-move0.1 | K10 | mutation | catch | quiet **(MISS)** | furn-lounge-sofa moved 0.1 m (the centre bound is half the smaller side: expected to be missed) |
| N-K10 | K10 | negative | quiet | quiet | furn-lounge-sofa moved 20 mm |
| M-K09-del | K09 | mutation | catch | caught | furn-lounge-sofa deleted |
| M-K09-dup | K09 | mutation | catch | caught | furn-lounge-sofa built twice |
| M-K08-down | K08 | mutation | catch | caught | furn-lounge-sofa scaled 0.85 |
| M-K08-up | K08 | mutation | catch | caught | furn-lounge-sofa scaled 1.15 |
| N-K08 | K08 | negative | quiet | quiet | furn-lounge-sofa scaled 1.002 |
| M-K11 | K11 | mutation | catch | caught | floor of bar-alcove shortened by 10 % |
| N-K11 | K11 | negative | quiet | quiet | floor of bar-alcove 0.05 % smaller |
| M-K12 | K12 | mutation | catch | caught | column-00 moved 20 mm |
| N-K12 | K12 | negative | quiet | quiet | column-00 moved 1 mm |
| M-K13 | K13 | mutation | catch | caught | one more mesh without an element id |
| M-K14 | K14 | mutation | catch | caught | rail-gf-stair-void deleted |
| M-K15 | K15 | mutation | catch | caught | lum-SWING-bar-alcove-09 moved 0.30 m off its host |
| N-K15 | K15 | negative | quiet | quiet | plate 5 mm off |
| M-K16 | K16 | mutation | catch | caught | a soffit 1.70 m above the pitch line at x7.49 |
| N-K16 | K16 | negative | quiet | quiet | a soffit 2.26 m above the pitch line at the sample (2.07 m above the highest pitch point under its 0.6 m width |
| M-K18 | K18 | mutation | catch | caught | every B-level door shifted +0.10 m |
| N-K18 | K18 | negative | quiet | quiet | every B-level door shifted +5 mm |
| M-K17 | K17 | mutation | catch | caught | IFC wall-B-int-11 extrusion +0.7 m (through the ramp), read back by IfcOpenShell |
