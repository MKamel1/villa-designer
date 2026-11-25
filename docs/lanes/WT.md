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


# Tour redesign (2026-11-24): 360 in every room, look along the route, both floors, the flight, the gardens

The client watched the first preview and asked for: no scenes where the camera looks at a wall or backward and then turns to the subject; a 360 in each room;
both floors and the stair; no long 1080p before the route is confirmed. The old route (above) is kept for history; the new planner is
`src/archpipe/walkthrough_tour.py` (`plan_tour`), authored in `knowledge/flythrough/villa-tour.json`, policy in `tour-policy.json`.
Same path schema, so prepare / assembly / admission / exposure / render are the existing ones: `scripts/flythrough.py prepare --route tour`.

## Route (16,091 frames = **670.5 s = 11 min 10 s at 24 fps**, 150.9 m walked)

Time budget: 428 s in 360 turns (31 turns), 189 s walking, 43 s garden pans, 9 s on the flight.
Order: entry-b (arrival) -> dining side, dining (+ east-yard pan) -> living (+ south-garden pan) -> bar alcove -> kitchen island, kitchen, dirty kitchen ->
family, guest WC, stair-foot hall -> lounge (+ north-court pan) -> nook, pantry, cinema, store -> stair foot -> **up the flight** -> GF top of flight, landing, study, gallery,
family bath, corridor, kids A, kids B, parents' entry, bedroom, dressing (through the 0.47 m gap), dressing ext, ensuite. All 30 rooms (13 GF + 17 B) have a 360
(`test_route_connectivity_every_room_has_a_full_360`). The three garden zones are viewed **from inside the closed panes** (2.0 m back, pan +-30 deg): no placeholder legs, nothing hidden.

| room / garden | level | 360 point x, y (m) | starts (s) | turn s | shortest wall ray (m) | best view (still) |
|---|---|---|---|---|---|---|
| entry-b | B | 15.28, -26.81 | 0 | 11.4 | 1.70  | n19-entry-lobby-evening |
| dining-side | B | 15.78, -26.71 | 13 | 13.8 | 1.80  | n20-dining-side-day |
| dining | B | 15.58, -26.01 | 29 | 12.3 | 2.10  | v09-dining-evening |
| dining | B | 16.89, -24.59 | 29 | 13.6 | - | - |
| living | B | 18.48, -25.51 | 63 | 15.5 | 1.55  | v33-basement-north-south |
| living | B | 21.60, -26.13 | 63 | 13.8 | - | - |
| bar-alcove | B | 20.98, -28.71 | 114 | 13.3 | 1.00 **FLAG** | v34-basement-south-north |
| kitchen-island | B | 13.98, -27.11 | 135 | 14.8 | 1.35  | v09-dining-evening |
| kitchen | B | 14.88, -25.71 | 153 | 11.8 | 1.75  | n02-kitchen-island-day |
| dirty-kitchen | B | 13.98, -22.51 | 169 | 15.0 | 1.05  | n09-dirty-kitchen-day |
| family | B | 10.38, -26.41 | 193 | 15.3 | 2.05  | v03-street-lounge |
| guest-wc | B | 10.08, -22.51 | 213 | 15.8 | 0.80 **FLAG** | deepest-wedge |
| hall-b | B | 10.98, -26.81 | 235 | 14.7 | 1.70  | n06-stair-foot-hall-evening |
| lounge | B | 3.98, -26.31 | 258 | 14.9 | 1.70  | v03-street-lounge |
| lounge | B | 4.62, -26.16 | 258 | 15.8 | - | - |
| lounge-nook | B | 4.88, -27.61 | 293 | 11.9 | 1.00 **FLAG** | deepest-wedge |
| pantry | B | 4.58, -29.11 | 309 | 15.9 | 0.50 **FLAG** | n05-pantry-evening |
| cinema | B | 8.08, -22.41 | 337 | 13.2 | 1.05  | deepest-wedge |
| store-ramp | B | 2.18, -22.21 | 357 | 15.7 | 0.95 **FLAG** | v30-under-ramp-store |
| stair-b | B | 10.05, -27.95 | 385 | 14.1 | 0.55 **FLAG** | v11-stair-void |
| stair-gf | GF | 4.95, -27.95 | 408 | 12.4 | 0.55 **FLAG** | deepest-wedge |
| landing-gf | GF | 4.58, -27.61 | 422 | 14.0 | 0.75 **FLAG** | deepest-wedge |
| study-game | GF | 7.78, -25.11 | 443 | 15.4 | 1.05  | n11-study-desks-day |
| gallery-end | GF | 10.28, -27.31 | 463 | 14.0 | 0.95 **FLAG** | n18-stair-gallery-day |
| family-bath | GF | 10.28, -25.31 | 481 | 15.7 | 1.00 **FLAG** | deepest-wedge |
| corridor | GF | 9.28, -27.51 | 501 | 14.7 | 1.00 **FLAG** | n10-gf-hall-east-day |
| kids-a | GF | 13.18, -26.21 | 523 | 15.7 | 1.15  | v06-kids-room |
| kids-b | GF | 17.38, -26.21 | 548 | 15.9 | 1.00 **FLAG** | v13-kids-b |
| parents-entry | GF | 18.98, -26.71 | 573 | 11.7 | 0.50 **FLAG** | deepest-wedge |
| parents-bed | GF | 21.48, -25.11 | 593 | 15.5 | 0.85 **FLAG** | deepest-wedge |
| parents-dressing | GF | 21.28, -27.81 | 621 | 12.8 | 1.00 **FLAG** | v31-dressing-hers |
| parents-dressing-ext | GF | 21.68, -28.71 | 637 | 12.5 | 0.40 **FLAG** | n14-dressing-his-evening |
| parents-ensuite | GF | 20.98, -30.01 | 652 | 17.9 | 1.05  | deepest-wedge |

**Policy (all in `tour-policy.json`, all stated as ASSUMED, none a published standard):** yaw 40 deg/s (client band 30-45), eased 0.44 s ramps (no snap), a 1.5 s hold on the room's best view
(the still view in `knowledge/render-set/views.json` that covers the room, from a camera standing in the room if one exists, else the deepest wedge), the sweep ends on the heading of the next leg so every walk starts already facing where it goes.
A full turn is 9 s; dead-end rooms add the turn to the exit heading. Walking heading = the route 1.5 m ahead (never backward by construction; `direction_findings` proves it: 0 frames more than 75 deg off).
Longer look-ahead (2.5, 3.5 m) was tried and is worse (frames with a wall within 1.5 m ahead: 7 %, 16 %, 20 %).

**The 1 m rule at the 360 point.** The point is the free cell with the best score (visible floor area + 1.5 per visible furniture piece) among those whose every direction clears a wall by 1.0 m.
**16 of 31 turn points cannot** (flagged in the table): bar-alcove, guest-wc, lounge-nook, pantry, store-ramp, stair-b, stair-gf, landing-gf, gallery-end, family-bath, corridor, kids-b, parents-entry,
parents-bed, parents-dressing, parents-dressing-ext (a 1.3 m corridor, 1.5 m hall, WC, pantry, bedrooms whose floor is mostly bed). Admission keeps the rule everywhere else; in a flagged room the
sightline finding is recorded as `waived_wall_sightline` (912 frames) and never dropped. `stair-b` / `stair-gf` are not walkable floor (under / over the flight): their 360 is at the foot and the top of the flight.
Authored hints (`point_bounds`): store-ramp east part (soffit 1.45 m at the west end), landing-gf 0.6 m back from the stair guard (swept envelope hit it).

**The flight.** Climbed continuously (3.0 m, 9.4 s at 0.7 m/s) with the camera pitched 12 deg up the flight (vertical lens shift, like every still); at the top the stair-gf 360 tilts 22 deg down the void
when facing it; then landing and gallery. `stair_findings`: climbs 3.0 m monotonically, pitch up.

## Admission

0 of 16,091 frames fail (clearance, no clipping, swept envelope against authored and evaluated meshes, speed, yaw rate <= 45 deg/s; max measured 40.0). Doors are rotated open, none hidden (`door-states.json`).
912 frames carry the recorded wall-sightline waiver (flagged rooms, and walks into them).

## Non-informative-frame rule

Registered **before** measuring (`knowledge/flythrough/informative-rule.json`, first commit): a 32x18 grid of rays through the 24 mm lens (glazing transparent); a frame is non-informative if more than 50 % of rays hit within 1.2 m,
or more than 60 % of hits lie on one plane (normals within ~6 deg, offset within 0.1 m). A run longer than 1 s fails.
**Calibration on the client-watched preview** (`out/wt/villa3`, frames labelled from its contact sheet: 12 known-bad = GF corridor, kids' and dressing wardrobe fronts, bathroom wall; 20 good;
`informative-calibration-labels.json`): the registered clauses flagged 5 of 12 bad, 0 of 20 good. Adding `near + plane >= 0.9` flags 10 of 12, still 0 of 20 good (best good frame 0.84); on the bad
stretches (stride 6) it flags 64/90 (kids/corridor), 17/19 and 10/24. Missed: the marble bathroom wall with its window (0.47+0.0) and one corridor frame (0.80). The final rule is the three-clause one.

## Validation passes

(a) **Workbench** (solid, cavity, 640x360) of every frame: one animation render (a render call per frame re-exports the 1.1 GB scene, 6 s/frame; one animation render is 0.14 s/frame), plus the depth-grid metric (0.17 s/frame): about 85 min.
Workbench draws glass as an opaque pane, so garden pans look like a blank wall there; the Cycles preview shows the glass.
(b) **Cycles** 480x270, 16 spp, denoised, every 2nd frame, interior exposure lock -8.34 stops 5500 K (337 metered frames, every 48th).
(c) Contact sheets every 2 s (every 48th frame).

## Results (2026-11-24)

Deliverables (absolute paths, all under `/home/omar/archpipe/lanes/WT/out/wt/villa4/`; `out/` is not in git):
* `walkthrough-workbench.mp4` : Workbench geometry preview, 640x360, 24 fps, all 16,091 frames, 670.5 s (`walkthrough-workbench.json`).
* `walkthrough-lookdev.mp4` : Cycles, 480x270, 16 spp denoised, every 2nd frame (8,046 frames) at 12 fps = 670.5 s real-time pace.
* contact sheets (every 48th frame = 2 s, captioned frame / second / room / phase): `contact-workbench-00..09.jpg`, `contact-lookdev-00..09.jpg`.
* `report.json` (non-informative-frame report), `assembly/guards.json` (admission), `path.json`, `door-states.json`.
Cycles frames: `lookdev/frame-NNNN.png`; no per-frame `render_qa` was run on this draft (a draft preview bypasses the per-frame receipts); the lead decides whether QA is needed before the client sees it.

**Non-informative-frame report (final rule, hidden objects and glass skipped).** 5,810 moving frames (walk, stair, pan): 1,832 (31.5 %) flagged, in **31 runs longer than 1 s (95.6 s in total)**:
* 17 are walks arriving at or leaving small rooms and the stair foot (guest WC 17.4 s, hall -> stair foot 4.0 s, lounge -> cinema 2.8, kids A -> B 2.7, family bath -> corridor 3.3, kids B -> parents' entry 3.0 ...): the camera looks along the route 1.5 m ahead and the route ends at a wall.
* 9 are garden-pan runs of 1.7-2.8 s: the pan crosses the mullion and the curtain stack at the end of the glass (the garden itself reads well in the Cycles frames).
* 1 is the flight (16.7 s): looking up the stair the stringer and soffit fill the frame, so the "one plane" clause fires; the Cycles frames show this is the intended view up the stair, i.e. a false positive of the rule for that segment.
* 360 arcs: 4,354 of 10,281 turn frames are wall-facing, 5,434 turn frames carry the waiver (flagged rooms). Per room: guest WC 0.90, pantry 0.83, dressing 0.69, kids B 0.62, bar alcove 0.63, ensuite 0.60; open rooms 0.0-0.35 (living 0.0).
**The "fail and fix any run over 1 s" requirement is NOT met**: the planner was tuned (turn points, bounds, look-ahead) but 31 moving runs remain; they are listed in `report.json`. Candidate fixes, not done: end each walk 0.5 s before the stop with
a hold looking at the room's best view; shorten the pan to the glass width; a different 360 point for the dead-end rooms; exempt the flight from the plane clause.

**Calibration** (final rule): 10 of 12 known-bad preview frames flagged, 0 of 20 good (re-run after the hidden-object fix gave the same result).
**What reads well** (contact sheets): the open-plan basement (entry, dining, island, living with the garden through the glass, kitchen), the ascent looking up the flight, the GF open stair/landing/gallery views, the parents' bedroom.
**What looks wrong:** store-ramp, cinema and the dressing rooms are nearly black under the one interior exposure (-8.34 stops); bare-wall frames at the stair foot (9,200-9,500) and some 360 arcs; Workbench shows glass as an opaque pane (garden pans look like a wall there, not in Cycles); the stair-gf 360 shows mostly plaster; dining pendants are still the old stand-ins.

**Final-render estimate (not started).** Measured earlier on this scene: 1080p, 64 spp, 12.07 s/frame (3 frames, shared GPU, per-render-call export). With the animation render the per-call export drops out; the Cycles preview ran about 0.5 s/frame at 480x270 16 spp alone,
so a 1080p 64 spp frame is estimated at about 8-12 s. 16,091 frames = **36-54 GPU-hours** at 24 fps (18-27 h at every 2nd frame, 12 fps), plus the 337-frame exposure metering (about 40 min) and QA/encode. Not scheduled.
