# SC2 lessons (SC follow-ups, 2026-11-21)

* **A scene-only member is invented geometry, and joinery cannot yield to it until it is data.** The stair steel (16 wall
  bearings, wall plate, open stringer, glass shoe) existed only in `villa_render.py` ("add to Revit"), so the model's
  cupboard could not be sized against it. Now `model/stair_steel.py` holds the offsets once, the scene builder reads them,
  and `stair-main.params.steel` lists the members. Guard: `tests/model/test_sc2_structure.py` (the built cupboard footprint
  equals the model's; the pre-SC2 spec footprint does cross the steel).
* **Retagging an embedded part to the element it belongs to can turn an accepted embedment into a check failure.** The
  wall bearings sit 150 mm into the party wall by design; giving them the id `stair-main` made RV1 K01 report three
  crossings (33 to 363 mm). They kept their ids. Guard: run K01 after any retag, not only K09.
* **A wall-height fix moves approved host faces.** Raising `wall-B-ext-16` to 2.80 m changed the top of the host face of
  the approved dirty-kitchen hood canopy (-0.35 to -0.20), and the lead-review guard rightly refused the build. The
  approved movement (13 mm) did not change, only the face's top; the row was updated mechanically and flagged. Guard: the
  guard itself, which fired; read its row before touching the approval.
* **One post-condition cannot tell "the deck soffit" from "the roof beyond the deck".** `clearance_problems` measured every
  B wall against the deck's 2.65 m. A cross wall past the deck end now uses the roof slab soffit. The south B wall
  (x 6.877..15.412, one piece, 2.65 m) still runs 2.6 m under the roof for its last 2.635 m: a 150 mm slot, not fixed here
  because splitting it renumbers every later `wall-*` id (ids are list indices).
* **K09 reading the contract must also check the contract.** The first run of the new clause found five contract entries
  that named ids the model does not hold (`prop-landscape-*`: model ids are `plant-landscape-*`, and two benches are scene-only).
  Guard: `element_contract` lists a prop under the id the model holds and scene-only props as `non_model_props`;
  `tests/parity/test_checks.py` (stray entry fails) and `tests/test_villa_render_g1_geometry.py::ElementContract`.
* **A measured-exposure job needs the ERCO IES files beside the scene.** `write()` generates only `ies/generic`; the four ERCO
  files (`knowledge/lighting/ies/ERCO-<code>.ies` as `ies/erco/<code>.ies`) must be copied before Blender runs, or it dies with
  `FileNotFoundError .../ies/erco/41321.ies`.
