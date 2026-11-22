# WT: whole-villa walkthrough (2026-11-22)

Extends the 30 s level-B clip (`docs/flythrough-report.md`) to every room on both floors and the three garden zones. The clip code is
unchanged; the villa route is a second path type (`flythrough-villa-path/1`) sharing its guards. Branch `lane/WT` from `integ/aplus`.

## Route

Authored in `knowledge/flythrough/villa-route.json` (tour order, holds, garden placeholders), planned by `archpipe.flythrough.plan_villa_route`
over per-level grids built from the production standing-point policy (`VillaMap`: walls, columns, furniture footprints and meshes, props,
evaluated cloth/curtains, the GF flight opening, the under-stair rectangle on B). Level changes only on the real flight (17 risers, 280 mm going, y -28.42..-27.47),
floor height from a least-squares line through the real tread tops (eye 1.35 m above it).

Rooms in order of first visit (all 30 rooms of the design, GF 13 and B 17 plus the store-ramp/extension rooms; `test_every_room_on_both_floors_is_visited`):
GF: landing-gf, study-game, stair-gf, gallery-end, family-bath, corridor, kids-a, kids-b, parents-entry, parents-bed, parents-dressing,
parents-dressing-ext, parents-ensuite; down the flight; B: stair-b, hall-b, family, lounge (+ north-court placeholder), lounge-nook, pantry, cinema,
store-ramp, guest-wc, kitchen, dirty-kitchen, dining, entry-b, kitchen-island, dining-side (+ east-yard placeholder from the dining door), living
(+ south-garden placeholder), bar-alcove. Dead ends are entered and left by the same door.

The route is **7,507 frames = 312.8 s at 24 fps, 196.1 m**: 6,193 interior frames (258.0 s) plus 1,314 garden-placeholder frames (54.8 s).
Holds (real pauses, 47.5 s in total): landing arrival 4 s, study 3, parents' bed 4, lounge 4, cinema 3, kitchen 3, entry 2, dining 4, living 4,
bar alcove 5, top of the flight 3, each garden threshold 3 s.

**Pacing.** Cruise 1.272 m/s, the lowest published mean comfortable gait speed, 127.2 cm/s (Bohannon 1997, Age and Ageing 26(1):15-19,
doi:10.1093/ageing/26.1.15; abstract only, full text not read: UNVERIFIED against the table). The upper bound for the speed check is the highest mean there, 1.462 m/s.
Flight 0.7 m/s, acceleration 0.8 m/s2 and the 30 deg/s yaw bound are ASSUMED (policy basis fields say so). Speed slows wherever the look direction has to turn
faster than the yaw bound, so the interior mean is about 0.55 m/s and the route is longer in time than distance/1.27 (143 s) + holds (48 s).

## Doors

All 12 door leaves are modelled **closed** (the stills hid a leaf only when a camera stood in its opening; hiding is not allowed here).
* 10 interior leaves block the route. Each is **rotated open about a jamb** (`open_interior_doors`: nothing hidden, every vertex kept, handle faces move with it).
  Hinge end and side are not authored, so all four are tried at 90/75/60/45 deg and the first with no contact with furniture, walls or the
  route is used (gap 0.35 m, then 0.25, then 0.18). Result in `out/wt/villa3/door-states.json`: 10 open (the parents' dressing door at a reduced gap), 0 left closed.
* 2 entrance leaves (core entrance on GF, entry-b on B) lead to the unmodelled shared core, are not on the route and stay closed.
* Garden glazing: 4 exits (lounge/north, dining/east, living/east, living/south) are closed fixed panes; none has an operable pane. The route
  stops 0.7 m inside each one, looking out (hold 3 s). The legs outside are **placeholders** (`segment: garden-placeholder`), authored as simple out-and-back loops;
  they cannot pass the glass and are reported separately: 456 of 1,314 placeholder frames fail admission (glazing/window frames, boundary and landscape meshes). LDB must supply the garden and an open state.

## Admission (every frame)

Per frame (`admit_villa_path`): eye height rule, central-sightline 1 m wall rule, lens clearance (props, planting, furniture; plan items skipped on the flight), standing-point policy (flat
frames), no wall crossing, the swept 0.15 m walking envelope against authored geometry **and** the Blender-evaluated meshes (cloth, curtains, dressing, imported models),
speed and yaw-rate bounds. Flight frames are judged by the 3D sweep only (the plan-view checks cannot see height). The sweep height is 1.8 m (ASSUMED operator), 1.40 m in the store-ramp (soffit 1.45 m measured).

Result on the assembled scene: **interior 6,193 / 6,193 pass**, max speed 1.272 m/s, max yaw rate 27.6 deg/s (bound 30). History of failures and fixes is in
`docs/lessons/WT.md` (first sampled path: 1,135 of 6,719 interior frames failed: wall sightlines, the under-stair joinery, standing-policy corner clips, dining/vanity chairs, bedside books, a curtain).
Known tight spot: the parents' dressing door is reached only through a **0.47 m gap** between the duvet and the pulled-out vanity chair; the walk is centred in it (0.235 m each side)
and any change to the chair or vanity re-routes automatically. Tucking the chair would remove the pinch (design finding).

Hand-guard evidence: `out/wt/villa3/assembly/guards.json`.
