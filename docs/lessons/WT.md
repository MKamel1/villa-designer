# WT lessons (whole-villa walkthrough)

Each entry: why it was missed, and the guard that now catches it. Tests are in `tests/test_flythrough.py::VillaWalkthrough`.

* **A plan-view mask is not a route.** The standing-point policy was evaluated at 0.1 m cell centres; a straight line between
  two free centres clipped a corner by up to 0.07 m and 58 interior frames failed the exact policy. First tuning attempt (smaller
  cells) would have hidden it. **Guard:** `VillaMap.line_free` requires all four surrounding cell centres free;
  planning uses a one-cell-eroded mask; `plan_findings` re-checks every flat interior frame with the exact policy and
  `test_plan_admission_is_clean_on_every_flat_interior_frame` fails on any miss.
* **Doors are crossed on their centre line.** A diagonal crossing of a 0.8-0.9 m door left the jamb limit (policy slot is
  `width/2 - 0.25`). **Guard:** `VillaMap.door_cross` inserts entry/centre/exit nodes; the narrow-slot mask removes the policy
  slot's outer 0.06 m from planning.
* **Facing a wall.** 1,429 frames of the first sampled path faced a wall within 1 m (the rule measures only the central
  sightline). Projecting each look direction onto the nearest allowed one made yaw jump 838 deg/s. **Fix:** a Viterbi over
  72 direction buckets (`repair_yaw`), one bucket of change per 0.1 m; speed then slows wherever yaw changes fast. A bug in the back
  pointer (sign) had produced worse results than no repair: the check is the guard, not the code (`admit_villa_path` row per frame).
* **The room list is not the walkable list.** `stair-b` is a room rectangle lying wholly under the flight (cupboard, soffit down to
  the floor); the first plan stood in it and the swept guard hit the under-stair joinery. **Guard:** the rectangle is blocked
  on B in `VillaMap`; `test_flight_is_not_walkable_floor_on_gf_and_the_under_stair_is_blocked_on_b`.
* **Plan footprints miss pulled-out chairs and wall-mounted pieces.** Dining and vanity chairs were hit by the 3D swept guard
  although the plan footprints were clear. **Fix:** `_furniture_boxes` adds the real mesh boxes (0.17 m) to the mask; the
  policy-only mask remains the last fallback for the guest WC and dressing room.
* **The 1.8 m operator envelope cannot stand in the store-ramp.** Its soffit is 1.45 m at the west end (measured from the scene
  ceiling faces) and the door is 1.88 m clear. Policy now carries a per-room sweep height (eye height + 0.05 m) with that basis;
  the room is reported as a finding, not silently exempted.
* **Closed leaves are modelled.** All 12 interior and entrance door leaves are closed slabs; the stills hid a leaf only when a
  camera stood in its opening. Hiding is not allowed here: `open_interior_doors` rotates each interior leaf about a jamb (hinge end
  and side are not authored, so the first collision-free option is taken) and moves its handle faces; the two entrance leaves stay
  closed. `test_door_leaf_is_rotated_not_hidden_and_the_handle_follows`, `test_entrance_leaves_stay_closed`.
* **Garden glazing is closed and no pane is operable.** The route stops 0.7 m inside each garden exit; the outside legs are
  placeholders flagged `garden-placeholder` and reported separately (their admission failures are the closed glass and
  planting). `test_garden_glazing_is_never_free_floor`.
* **Blender assembly must be given the id-stripped scene.** Passing raw `scene.json` raised `stale or unbound drape cache
  reference` (element-id annotations are part of the part hash). `walkthrough.py` now strips ids exactly as `villa_render.py`.
* **A prepared directory is bound to its sources.** Editing `walkthrough.py` after `prepare` made `require_inputs` refuse the
  directory; edit first, then prepare into a fresh directory.
* **jobq `--gpu` already holds `graphics.lock`.** The old code locked again from the child and would deadlock; `graphics()` skips
  its own flock when `JOBQ_JOB_ID` is set.
