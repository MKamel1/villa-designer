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
