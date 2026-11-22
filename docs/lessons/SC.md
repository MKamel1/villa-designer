# SC lessons (scene completion, 2026-11-21)

* **"Built 0 times" had three different causes, and only a diagnosis per element tells them apart.** Of the 8 safety/structure
  items: 3 slabs and the wet zone were *built but tagged with another id* (`env-slab-B`, `furn-gwc-shower`); the two guards, the
  riser infill and the cupboard were *never drawn* (the spec and Revit builder had them, the scene builder did not). A fix that
  only added geometry would have duplicated the slabs; a fix that only re-tagged would have left a 3.0 m drop unguarded.
  Guard: `tests/test_villa_render_g1_geometry.py` (geometry from the spec's own numbers, identity rules) and RV1 K09/K13/K14 on the
  built scene.
* **A closed check on the model/spec side cannot prove the built side.** The riser infill and the cupboard had been "modelled in
  spec, Revit and scene" (G1 decision text) for a day while the scene had neither. Only a mesh-level read of the built scene
  (RV1) saw it. Guard: K09 (every model element has faces), K14 (every guard has height at its edge).
* **New geometry in a crowded space has to be tested against the members already there.** The spec's cupboard side wall and the
  infill bars both ran through the scene's ASSUMED steel (wall stringer bearings and plate, open-side stringer, glass shoe):
  11 crossings of 35 to 177 mm on the first build, invisible to a bounding-box test and to the parity K01 (it does not look at
  joinery). Guard: `g1_geometry.steel_clear_y` reads the built steel; every new part was crossing-tested with
  `parity.geom.tri_cross_segments` (0 crossings on the final scene) and the tests check the stepped wall against the treads.
* **A tread overlap makes a stepped wall poke into the lower tread.** The model's profile steps every 0.28 m, the treads are
  0.296 m wide (G1 16 mm overlap): each step must stop where the next lower tread begins (same cause RA2 hit in the soffit check).
* **"Several ids, no per-face split" is ambiguous, and a strict loader reports it as unowned.** `attach` now makes a declared
  multi-id part shared (every id owns every face) instead of leaving the loader to guess. Guard: `test_declared_shared_mesh_gives_every_id_every_face`.
* **Non-model dressing needs an explicit class, not an empty id.** `nonmodel-<class>` (rug, garden-structure, garden-surface,
  garden-planting-dressing, garden-uplight, ventilation-fitting, curtain-track, kitchen-hatch) lets K13 pass and still tells
  dressing from a lost id; an unexplained mesh stays unresolved and `tag_non_model` returns it.
* **K09 reads meshes only.** 28 `prop-*` (imported glTF assets placed from `scene["props"]`) and 15 light-only luminaires are
  real in the scene but not as meshes; the scene now states them in `scene["element_contract"]`. The check does not read it yet
  (parity is RV1's): until it does, K09 keeps reporting them. Proposed check change in `docs/lanes/SC-scene-completion.md`.
