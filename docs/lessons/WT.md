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

## Tour redesign (2026-11-24)

* **A per-frame render call re-exports the whole scene.** Workbench took 6 s/frame and Cycles 3-6 s of every 2 s render on the 1.1 GB production scene, so 16k frames was 30 h; one `render(animation=True)` over keyframed camera
  poses keeps the engine's scene (Workbench 0.14 s/frame, Cycles about 0.5 s/frame alone). Measure a render call's fixed cost before scaling a loop (`walkthrough.py` stages `workbench`, `lookdev`). Culling objects by distance did not help (cost is not object count).
* **`Scene.ray_cast` ignores `hide_render` and returns evaluated-mesh face indices.** The depth metric hit the day state's hidden closed curtains at 0.6 m (garden pans flagged 100 % "near") and indexing the original mesh raised IndexError.
  **Guard:** hidden objects and glass (by evaluated-mesh material, not object name: panes are merged into `villa-merged-*`) are skipped; frame 1250 debug showed the real hit list. Calibration was re-run on the fixed code (same 10/12, 0/20).
* **A rule registered before measurement can be too weak.** The registered near>0.5 / plane>0.6 rule caught 5 of 12 frames the client called bad; the calibrated third clause (near+plane>=0.9) catches 10, with 0 of 20 good frames flagged. Both are recorded; the calibration labels are in the repo.
* **A 360 and "no wall frames" conflict in a room with no 1 m point.** 16 of 31 turn points cannot clear 1 m from every wall. The sightline finding is waived (recorded per frame, 912 frames), never dropped, and the non-informative arcs are reported per room, not hidden.
* **Editing a hashed source after `prepare` invalidates the directory.** `walkthrough.py` and `flythrough.py` are in the manifest. Workbench-only edits refreshed the hash in the manifest (noted in it); anything touching path, scene or assembly needs a fresh prepare.
* **Do not start a GPU stage as a CPU job and call it jobq-safe.** `--gpu` is what takes the slot; a chained prepare+assembly+render job without it would have rendered unqueued.

## Tour revision 2 (2026-11-24, client: 16 mm in small rooms; lead and audit review)

* **A wall-sightline waiver is not a fix.** Revision 1 recorded the 1 m forward-wall finding as waived in 16 rooms and called the arcs "reported, not hidden"; the audit (lane WTA, independent
  geometry) then measured 30.2 % of frames wall-dominated and the lead declined the waiver. **Guard:** the quality bar is now the audit's own wall-dominated share per room (`scripts/wt_summary.py`, `scripts/wt_chain.sh`), measured on
  the planned path before any render; the admission waiver stays only as a recorded physical fact about a 0.5 m pantry, never as the answer to "is the frame informative".
* **A guard tuned on its own measure can disagree with the independent one.** My depth-grid rule (plane/near clauses, 24 mm) read 31.5 % of moving frames, the audit's v2 wall-dominated read 30.2 % of all frames and agreed per frame only 76.5 %.
  The 360-point and walking-aim searches therefore use the audit's classifier on the audit's geometry (`scripts/tour_points.py`, `scripts/tour_aim.py` import `archpipe.flyaudit.core`), not a proxy of my own; and every result is re-audited by the unmodified tool.
* **A search proxy can improve while the audit does not.** Widening the walking-aim range to +-90 deg cut the search's own bad samples 137 -> 83 but the audit moved 14.4 % -> 14.8 %: the search ran on the un-aimed plan, and the aim changes the speed profile (slower where it turns), so the sampled positions move.
  Result: ranges kept at +-60 deg of the look-ahead and 70 deg of travel (85 on the flight); the audit is the judge.
* **Candidates must be reachable, not just free.** The first 360-point search chose a free cell in kids-B that A* could not reach (`no walkable route`): `tour_points.py` now filters candidates by the planner's own `astar` from the current point.
* **A door-crossing polyline can overshoot its target.** `door_cross` puts its exit node past the door; the pantry target lay before it, so the camera walked past the point and came back (8 frames, 180 deg off the travel direction). **Guard:** `_walk_polyline` drops a vertex that reverses more than 120 deg when the shortcut is free;
  `direction_findings` in `test_walking_never_looks_backward_or_sideways` caught it.
* **Removing a turn removes the thing that joined two headings.** Taking out the in-place turns at the stair foot and top left the flight leg ending on one heading and the next leg starting on another: a 75 deg yaw snap in one frame (`motion_findings`: 1,793 deg/s).
  **Guard:** the flight and the walk off it are one leg; `test_motion_bounds_and_no_snap` fails on any snap.
* **A lens ease needs the same frame ownership as the turn.** The final hold frame carried `station=None`, so it fell outside the wide-room span and the lens eased 16 -> 24 on a still camera. `lens_findings` (changes only while the camera moves or turns, never a step, caption exactly when wider than 24 mm) is a test and a plan check.
* **One exposure for the house makes the dark rooms black and the garden white.** Revision 1 metered one lock for every interior frame (-8.34 stops). Frames now carry an `exposure_group` (house, each dark room, each garden pan); each group has its own measured lock
  and the exposure and white balance between groups move with a moving average of 1.25 s (`frame_exposure`, `smooth_series`), keyframed per frame in the lookdev render. Guard: `test_exposure_eases_between_groups_over_the_stated_time`; the contact sheets of the new preview.
* **One 360 per model room is redundancy, not coverage (client, 2026-11-24, version 2).** The stations followed the design model's rectangles, so an open plan of eight "rooms" got eight turns that each re-showed the same walls. Why it was missed: the guards counted
  *rooms visited* and *frames informative*, never *new surface shown*. **Guard:** `scripts/wt_cover.py` counts surface cells (0.5 m cells of walls, furniture, fixtures, dressing seen by informative audit frames); `select` chooses 360s (hubs) and arcs by greedy set cover, a point that
  sees an existing hub is in its space (one 360, a second only above 60 m2); `refine` plans the real route and drops any stop whose frames add less than its minimum in ROUTE ORDER (hub 12 m2, arc 6 m2), unless the drop leaves a room under 80 % of its coverable surface or loses a piece of
  furniture/sanitary fixture seen before (the guest-WC basin was lost once, caught by the audit's per-room feature list, now a rule); `measure` reports redundant seconds. Tests: `test_every_hub_has_a_full_360_and_every_room_is_covered_by_the_route`, `test_one_360_per_connected_space_and_arcs_only_for_what_is_not_yet_seen`.
* **Greedy set cover without a space rule repeats itself.** The first `select` took four 360s in `living` (each added 16-38 m2 at the margin). A 360 now needs the candidate NOT to see an existing hub (line of sight at eye height); otherwise it can only be an arc.
* **Coverage counted from wall-dominated frames is not coverage.** With every ray counted, pantry and guest-WC "covered" themselves by pointing the camera at a plaster wall; coverage now ignores views the audit calls wall_dominated/blocked (same rule, `Cover.keys`).
* **Model finding (not mine to fix): the GF slab opening over the flight is too short.** From x = 8.1 to 7.2 m the head (tread + 1.8 m) is above the slab underside (-0.2 m), and from 7.56 to 7.2 the camera eye itself is inside the slab (z > -0.2): the audit sees `slab-GF-floor` filling 0.5-0.95 of the
  frame at 0.06 m for about 1.5 s of the climb. Not a false positive of the wall rule: the ray data confirm it. Easing the pitch to level did not help (tried, reverted). The opening must start about 8.1 m (east) or the flight must start further west; owner: model/stair lane.

## Revision 8 (2026-11-27, merge of the parents' suite)

* **An authored via-point is a coordinate in a room that can change.** The pinch via-points of the dressing door survived DF's rotated bed and moved door as numbers in `tour_order.py` and `villa-route.json`, and the planner failed with "route endpoint not free". Why missed: the data round after the lofts did not touch the suite. **Guard:** the via-points are gone and the A* finds the route; `test_every_room_on_both_floors_is_visited`, the tour test (`suite-vestibule` and `parents-dressing` in the frames) and `plan_findings` fail on a stop that is not free.
* **A reveal that fits one route fails silently on the next.** The family-bath reveal (leaf shut while the WC is in view) disappeared when a route change left only 3 audit-blocked held frames, and the scheduler reported "unscheduled" without anyone looking. **Guard:** the schedule keys on frames where the reveal feature is in view (`tour-reveal.json`), tries the whole visit then the longest pass, and `test_the_ensuite_basin_and_the_family_bath_wc_are_revealed_by_their_animated_doors` fails if the family-bath door is not animated; `wt_reveal.py` proves the shut-leaf frames (94).
* **Frame count is an index bound, not a frame.** A leaf scheduled to be open "by len(frames)" is 0.1 % closed on the last frame (the route ends in the ensuite). **Guard:** the walk-out default is the last frame; `test_every_animated_leaf_starts_and_ends_open...` and the leave test accept a route that ends in the room.
* **Another lane's argument list is an interface.** SOFT added `args.no_soft` to `villa_scene.render`; the walkthrough's assembly namespace was never updated and the first assembly died with an AttributeError after a 7-minute prepare. **Guard:** the namespace sets it; the failure was caught by the real job, the cheap local admission could not see it. Next time, run the assembly stage on a small frame range first.
* **A group is chosen by room, so a room that goes dark needs a group.** The moved dressing door turned `parents-dressing` into an unlit passage and its walk rendered black (1.4 s), as did a family arc. The audit's `no_daylight` flag is in the report, but `dark_rooms` is authored. **Guard:** `scripts/wt_dark.py` (`tests/test_wt_dark.py`) reads the rendered frames, reports any run of near-black frames over 1 s and exits 1; on villa10 it finds exactly these two runs and no others (proven on the real render, not synthetic frames). Open: derive `dark_rooms` from the audit's `no_daylight` rooms instead of authoring it.
* **Peak VRAM must be measured per job.** The old sampler matched a command-line string, so two parallel shards (same `--root`) could not be told apart; `wt_vram_peak.sh` now sums the GPU memory of the job's own process tree. Exposure measured 8.6 GB this time against 13.4 GB recorded on the shared card in Revision 6; reservations should come from the latest measurement, not from the old one.
