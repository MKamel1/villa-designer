# GI lessons (garden into the production scene)

Each row: the defect, why it was missed, the guard that now catches it. Guards are automatic unless stated.

* **Black leaves (first production render).** The scene JSON used for the render was built before the mesh field `leaf_uv` existed; the Blender hook skipped leaf meshes without it, so every card sampled UV (0, 0) and rendered black.
  Missed because the hook failed *open* on a missing field. **Guard:** `garden_ldb.finish_meshes` raises `leaf cards without UV windows`; `test_leaf_cards_are_closed_solids_with_uv_windows_...` pins the field.
* **A second stone pattern through the pavers, and ponds drawn as paving.** The production shell already carries a flat `paving` yard floor at z = -3.0 (shell-039); the garden's surfaces were coplanar with it (z-fight) and its ponds
  (liner below the floor) were closed over by it. Missed because the preview scene had no floor of its own to collide with. **Guard:** `production.reveal_ground` (cut back under every garden surface and pond) and
  `test_the_shell_yard_floor_is_cut_back_under_the_garden_and_the_pond_is_open` (the pond centre is uncovered, the floor under the house is kept, negative on both).
* **A camera inside a stand-in mass rendered black (v40).** The placeholder cameras were authored for the old garden; nothing checked a camera against the garden's solids. **Guard:** `production.camera_clearance` / `clear_camera`
  (0.6 m, least move, recorded) and its positive and negative tests.
* **A texture chosen unseen.** The first boundary-wall plaster (Poly Haven `white_rough_plaster`) is a heavily peeling wall: the wall read as mouldy. Found only by looking at the render. **Guard (process, no automatic check yet):** look at a
  candidate texture's colour map before binding it (`/tmp` contact sheet of the three candidates was the check); the wall's stated colour and reflectance are mean-matched so a texture can add pattern but not change the finish.
* **A prop asset named `...plant...` was taken for an indoor potted plant.** `indoor_plant_violations` keys on the substring `plant` in `asset`. **Guard:** garden props carry `ldb-<id>` with `plant` replaced, and
  `test_no_prop_asset_name_trips_the_indoor_pot_guard_and_every_prop_carries_its_placement`.
* **The geometry-topology review failed closed on the first garden prop** (no route-geometry record, no `PROP_BOUNDS` row), after the scene had built. Missed because the build only touches props through subjects. **Guard:**
  `ldb-prop-bounds.json` + `PROP_BOUNDS` merge + `test_the_committed_bounds_table_is_current_and_places_every_prop_at_its_built_size`.
* **Open meshes refused by the physical-part guard, groups hashed by the receipts.** Leaf cards, water, ground quads were open surfaces; walls and coping were in group `shell`, which the furniture receipts hash as architecture.
  **Guards:** the physical-part guard itself (the garden builds only if every mesh is admitted), and the receipt guard; `production.GROUPS` comment says why never `shell`/`context`.
* **A decision recorded after the layout was built (star jasmine) was not in the layout.** The build applied it as a rule; LDG then put it in the layout. **Guard:** the rule yields to a layout that already names star jasmine
  (`has_star`), with tests for both (`test_the_layout_puts_star_jasmine_away_from_the_seats...`, `test_a_layout_that_predates_the_decision_gets_the_swap_and_the_rule_can_be_switched_off`).
* **Invented context hides what the production scene already knew.** The preview drew house boxes with no windows; the production scene has the real facade. **Guard:** `production.garden()` takes no context box (only fences and
  ground); `test_ids_are_unique_and_every_mesh_and_prop_names_its_element` and the render itself.
