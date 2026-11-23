# WT: whole-villa walkthrough (2026-11-22)

Extends the 30 s level-B clip (`docs/flythrough-report.md`) to every room on both floors and the three garden zones. The clip code is
unchanged; the villa route is a second path type (`flythrough-villa-path/1`) sharing its guards. Branch `lane/WT` from `integ/aplus`.

## Route

Authored in `knowledge/flythrough/villa-route.json` (tour order, holds, garden placeholders), planned by `archpipe.flythrough.plan_villa_route`
over per-level grids built from the production standing-point policy (`VillaMap`: walls, columns, furniture footprints and meshes, props,
evaluated cloth/curtains, the GF flight opening, the under-stair rectangle on B). Level changes only on the real flight (17 risers, 280 mm going, y -28.42..-27.47),
floor height from a least-squares line through the real tread tops (eye 1.35 m above it).

Rooms in order of first visit (all 30 rooms of the design: 13 on GF, 17 on B; `test_every_room_on_both_floors_is_visited`):
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

## Preview (draft, current production scene)

`out/wt/villa3/preview/walkthrough.mp4` (absolute: `/home/omar/archpipe/lanes/WT/out/wt/villa3/preview/walkthrough.mp4`): H.264 yuv420p, 480x270,
**every 3rd interior frame (2,065 frames) played at 8 fps = 258.1 s, real-time pace**. 32 samples, denoised, AgX, fixed interior exposure
**-9.80 stops, 5500 K (day group, lamp fraction 2.5 %)** metered on every 24th interior frame (259 frames; a registered deviation from "every frame", 10,000
metered frames would cost more than the preview). Render time per frame: median 1.84 s, mean 2.40 s, max 24.9 s; 82.5 min of GPU in total. Door leaves open,
garden frames not rendered. Contact sheets (every 90th frame, captioned with the room): `preview/contact-00.jpg`, `preview/contact-01.jpg`.

What the sheets show (looked at, not scripted):
* The path is physically sound: both floors, the flight (frames 2700-2790: looking down into the open-plan floor), open doors, no clipping, no floating handles.
* **Close, blank frames in the GF bedroom wing**: kids-a, kids-b, the corridor and parents' dressing room are many frames of plaster or timber wardrobe fronts at 1-1.5 m. The 1 m
  forward-wall rule is met, but nothing is shown. A longer look-ahead or a hold at each door looking in is needed (open item 1).
* **Cinema, lounge-nook and parts of the lounge are nearly black** under the one interior exposure. That is the registered day state (functional lights off, cinema has no daylight), not a camera
  fault; it is exactly what a fixed exposure per group does. If the walk should show the cinema, it needs its own lighting scene or group (open item 2).
* Window-facing frames (parents' bed, dining, living) are bright and partly blown at the glass, again from the single interior exposure; the interior reads well at the same time in the kitchen/dining/living frames.
* The dining pendant is still the old globe/wire stand-in (L6d); the gardens through the glass are the pre-LDB planting. Both will change.

## Final render plan (1080p, 64 samples)

Measured through jobq with the interior exposure lock, 1920x1080, 64 samples (`out/wt/villa3/sampling/64/frame-*.json`): frame 1207 (corridor) **11.47 s**, frame 2755 (flight) **10.90 s**,
frame 6710 (living, glass) **13.84 s**; mean 12.07 s.
* Frames 7,507 (6,193 interior + 1,314 garden). **GPU time 7,507 x 12.07 s = 25.2 h** (interior 20.8 h, garden 4.4 h), plus about 5 % for process start and QA = about 26.5 h.
  The 64-sample choice for this scene was measured only as a timing; the clip's 1024-sample reference test is not repeated (open item 3).
* Chunking: `scripts/flythrough.py final --frames a,b,c...` in chunks of 300 frames (about 1 h), one jobq job each (`wt-final-000` ... `wt-final-025`, `--gpu --timeout 7200`). A frame is skipped when its receipt,
  identity (path, lock, resolution, samples) and PNG hash match, so a died or timed-out chunk is simply resubmitted (`--retry`) and resumes. Order: interior first; the garden chunks only after LDB lands, a fresh `prepare` (the
  path hash changes with any scene or route change) and a garden exposure lock (`measure --segments garden-placeholder`).
* Per 24th-frame production QA and the MP4 (`encode-villa --every 1`) follow the last chunk.

## Open items
1. Blank close frames in the GF wing (see above): add look-in holds at doors or a longer look-ahead; needs a re-prepare.
2. Cinema/lounge-nook darkness under one interior exposure: decide a lighting state or a second exposure group for them.
3. `choose-samples`, `temporal` and `encode` (final) are still hard-wired to the 720-frame clip; the villa route needs the same acceptance for its own frame count before a final is accepted.
4. Garden: placeholders only; need LDB's garden, an operable/open exit state, and a garden exposure lock. Their 456 failed frames are glazing and landscape meshes.
5. Parents' dressing door pinch (0.47 m between duvet and vanity chair) and the 1.45 m store-ramp soffit are design findings.
6. Bohannon speeds are from the abstract only; confirm against the paper's table. Hinge sides of interior doors are assumed.
7. Dining pendant draws the old stand-in; scene will change, so the prepared directory and path hash will too.
