# Walkthrough requirements (client, 2026-11-24)

The client watched the first whole-villa preview (lane WT, out/wt/villa3/preview/walkthrough.mp4) and said:

- "it had some non informative scenes where the camera [turns] back to where we want to actually look"
- "I want a 360 at each room"
- "I want both floors and the stairs covered"
- "before spending a lot of time in 1080 feel free to follow a more efficient way just to confirm the walkthrough is working as expected"

## Requirements that follow
1. **A full 360° turn in every room** on both floors, from the most informative standing point, with a short hold on the room's best view.
2. **No non-informative stretches.** Between rooms the camera looks along the direction of travel or at the next subject, never backward, and turns are eased. An automatic check fails any run of more than 1 s dominated by a near wall or near-black.
   - Lead review on 2026-11-24 of the first preview, sampled every 6 s: about 30 % of frames were wardrobe fronts or walls at close range, about 12 % were near-black, and about 40 % were good room views.
3. **Both floors and the stair** (a continuous flight, the landing, the gallery), plus the gardens.
4. **Validate cheaply first:** a Workbench shape preview of every frame, then a low-sample Cycles preview, with contact sheets and the wall-check report. The 1080p final starts only after the client approves the route.
5. **Dark rooms** (cinema, stores) use their own exposure groups, not one house-wide exposure.

## Client decision (2026-11-24, later): 16 mm in small rooms
- **Lens:** small rooms (those where the geometric audit finds a 24 mm 360 wall-dominated: guest WC, parents' ensuite and dressing, pantry, family bath, kids-b, landing-GF and similar, decided by the audit's rule, not by eye) use a **16 mm** lens for their 360. Everywhere else stays at 24 mm.
- **Labelling:** the video LABELS those scenes as 16 mm, with an on-screen caption such as "16 mm wide lens: small room" for as long as the lens is wider than 24 mm.
- **Transitions:** 24→16 and 16→24 are SMOOTH. Ease the focal length over a stated duration (about 1–1.5 s, policy) while the camera is moving or turning, never as a cut. The audit and the preview check the transition frames too.

## Lead review of the revision-1 contact sheets and decisions taken (lane WT, 2026-11-24, after the audit)

* **The wall-sightline waiver is declined** (lead). The client's answer for the small rooms is the 16 mm lens; the waiver is no longer a quality argument anywhere in this lane. Admission still records the physical fact (a 0.5 m pantry has no 1 m sightline) per frame.
* **Which rooms get 16 mm** is decided by the audit's rule, not by eye: a room whose 24 mm 360 (sweep and hold frames) is `wall_dominated` in at least **25 %** of its frames in the audit of the revision-1 route (`knowledge/flyaudit/wt-villa4-tour/frames.json`).
  The 25 % threshold is policy (ours); at 35 % it kept hall-B, bar-alcove, kitchen-island and dirty-kitchen at 24 mm. `scripts/lens_rooms.py` writes `knowledge/flythrough/lens-rooms.json` (shares, rule, rooms).
* **Ease:** smoothstep over **1.25 s** (policy, inside the client's 1-1.5 s) on the walk arriving at the room and on the walk leaving it, so the focal length only changes while the camera moves or turns; two wide rooms with a short walk between never go back to 24 mm in between (the profile is the minimum over the rooms).
  Largest step 0.4 mm per frame (test: <= 0.5).
* **Caption:** "16 mm wide lens: small room", lower left, white on a dark box, text height 5.5 % of the frame height (15 px at 480x270, 59 px at 1080p), on every frame whose lens is wider than 24 mm, burned into the encoded frames and the contact sheets (`burn_caption`). It says "16 mm" while the lens is easing (e.g. 20 mm): the client's wording, kept as asked.
* **The 360 point** of every non-transit room is the standing cell (0.3 m grid... 0.2 m pitch, reachable by the planner's A*) with the smallest share of wall-dominated/blocked frames in a simulated full turn at that room's lens, scored by the audit's own classifier on the audit's geometry (`scripts/tour_points.py` -> `tour-points.json`). The best-view hold uses the still's heading if the audit finds it informative from that point, else the not-bad heading with the longest sightline.
* **The 360 itself** sweeps at 44 deg/s through headings the audit finds wall-dominated and 30 deg/s through the others (both inside the client's 30-45 band), instead of 40 throughout. Walking yaw rate raised 30 -> 40 deg/s (same band) so the slow bends are shorter.
* **Walking aim** (`scripts/tour_aim.py` -> `tour-aim.json`): every 0.25 s the heading is chosen within +-60 deg of the look-ahead heading and 70 deg of the travel direction (85 on the flight), by dynamic programming on the audit's classifier (preferring the look-ahead heading, 5 deg per step).
* **The stair rooms are transit.** No in-place turn at the foot or the top: one continuous leg from the last room, up the real flight (view up the flight), and off the top into the landing, aimed across the landing instead of at the plaster at the end of the flight. They are exempt from the "full 360" check (they have none by design); the other 28 rooms keep it.
* **Exposure groups** (revision-1 contact sheets: store-ramp and cinema near-black for 25 s, garden pans blown out): each frame carries an `exposure_group` (`interior`, `dark-<room>` for the six rooms the audit finds without glazing visible, `pan-<garden>`), each group has its own measured lock (camera meter on at least six frames of the group, the registered rule-3 classification of the metered sources gives its group and white balance),
  and exposure and white balance between groups move with a 1.25 s moving average (keyframed per frame, no cut). The render-set stills' own groups for the same rooms (cinema `evening`, store-ramp `lamp-low-key`, ensuite `lamp-low-key`) are listed in the report next to the groups the walkthrough meter measured.
* **Not done (stated):** the "exempt the flight from the one-plane clause" candidate fix concerned my own depth-grid rule; the audit (not mine) has no plane clause and judges the flight frames itself, so nothing was exempted. Garden pans were not shortened separately: the audit calls no pan frame wall-dominated (pans are outside the interior categories).

## Client feedback on version 2 (2026-11-24): too much redundancy
"the walkthrough has many redundancy of the 360, it covers everything but it is redundant."
- The design-model "rooms" inside one open space (entry-b, dining, dining-side, kitchen, kitchen-island, living, lounge and so on) each got their own 360, so the same views repeat.
- **Rule from now on:** one 360 per VISUALLY CONNECTED SPACE, not per model room, placed where it shows the most. Smaller sub-areas get a short look or a partial arc only if they show something not yet seen.
- **Coverage drives the route.** Use the geometric audit's per-surface coverage. A turn, arc or hold must add new coverage (a stated minimum share of the space's surfaces and features not seen before); otherwise shorten or drop it. Report the redundancy before → after (seconds spent on already-seen surfaces).
- Keep everything covered (every room, both floors, the stair, the gardens), with 16 mm in the small rooms.

## Revision 3 (lane WT, 2026-11-24): coverage-driven route after the "too much redundancy" feedback
* **Spaces, not model rooms.** `scripts/wt_cover.py select` finds the stops by greedy set cover of surface cells (0.5 m cells, 0.25 m2 each, informative frames only). A candidate that can see an existing 360 (line of sight, eye height) belongs to that space and may only add an arc, or a second 360 if it adds >= 60 m2;
  rooms narrower than 2.0 m (corridors, halls, landings) never get a 360, only arcs; the stair rooms stay transit. Thresholds are policy (ours): 360 >= 12 m2 new, arc >= 6 m2 new (arc = at most 4 consecutive 30-degree headings, starting and ending on informative ones).
* **Result:** 8 full 360s and 21 arcs (was 30 turns). The basement open plan has 3 360s (living, dirty-kitchen/kitchen side, lounge) plus short arcs, down from 14 turns; each GF bedroom keeps one.
* **Prune in route order** (`refine`): every stop must add >= its minimum of new surface after all earlier frames of the route (walking counts); the weakest is dropped first and the route re-measured. A drop is refused (stop kept, listed as `protected` in `tour-prune.json`) when a room would fall under 80 % of its coverable surface or a furniture/fixture piece seen before would be lost.
* **Redundant second** (stated rule, `wt_cover.py measure`): a second of the route in which the frames show < 1.0 m2 of surface not shown by any earlier informative frame. Before (version 2, 670.5 s): 438 s redundant (65 %); after: see docs/lanes/WT.md.
* **Wide lens pad:** the 16 mm span of a small-room stop is kept 1.5 s either side (the door crossings, wall-dominated at 24 mm), then eased out over 1.25 s; the caption follows the lens.
