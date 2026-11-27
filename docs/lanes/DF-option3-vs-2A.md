# Lane DF: option 3 (site check) vs option 2A (self-closing doors), 2026-11-26

Step 1 only. **Nothing built.** Plans: `docs/lanes/DF-privacy-options/plan-2a.png` (new), `plan-3.png`, `plan-2.png` (original, unchanged).
Reproduce: `python scripts/df_privacy_options.py`, `python scripts/df_privacy_2a.py` (numbers in `results.json`, `results-2a.json`).

## Site check of option 3's 1.2 x 1.9 m south bump-out: FAILS in the modelled context
Source: `out/model/d1-elements.json` (frame: GF south facade at y -28.671; the bump-out occupies x 17.45..19.60, y -29.77..-28.47, 2.80 m² incl. the corridor part).
- **Sister villa: conflict.** The outside footprint (x 17.45..19.60, y -29.77..-28.67) lies **inside `ctx-sister-bath-GF`** (x 17.41..19.60, y -31.16..-28.67; 2.37 m² of overlap) and under `ctx-sister-bath-APT` / `ctx-apartment-above` (z 3.0 m, 2.8 m² overlap). The strip south of our GF facade is the shared core / sister bathroom block, not yard. The bump-out would have to take the sister villa's bathroom.
- **Below:** it also sits over `room-bar-alcove` (Basement, 2.37 m²; floor-to-beam garden window), so it would be a cantilever over that window as well.
- **Structure:** no column or beam in the footprint (only column-04 at 22.42, -28.42 and the ensuite beams from x 19.60). The GF slab edge is at y -28.671, so it would be a slab extension plus new walls, over an existing B room. Not a free-standing extension.
- **South garden (landscape lanes):** no conflict. Garden beds, paths, pond, fire pit are on the north court (x < 3.6), the east yard (y > -23.6) and the rear (x 26..28). Nothing lies near x 17..20, y -30.
- **Plot, setbacks:** the modelled fences give a plot of about x -0.12..28.3, y -39.2..-20.6, both villas on it. The bump-out is more than 9 m from the nearest boundary fence. **A setback source is NOT held:** `spec/villa-site.yaml` (4/3/3 m, 18 x 28 m plot) is flagged invented and uses a different frame from the model. The real setbacks and the separation rule between the two villas are **not authored and are flagged for the client.**
- Verdict: **do not build option 3 as drawn.** The fallback in the decision applies (keep today's layout, 1a), unless the client accepts a different dog-leg that stays inside our own footprint. A search in the earlier study found no inside-the-corridor screen that passes (corridor 1.05 m), so none is proposed here. (Alternative not explored: trade the 0.35 m storage and use a dog-leg of the cross wall inside the vestibule; it needs more width than the 1.05 m.)

## Option 2A: straight vestibule, NO bump-out, NO facade change, two self-closing doors
Changes against option 2 (plan-2a): storage in the vestibule 0.30 to 0.20 deep and the dressing doorway 0.80 to 0.90 (north jamb 0.10 m). **Pinch 0.702 to 0.802 m** (measured by the engine; 750 needed). Route corridor to dressing 3.81 m.
**Sightlines (371 outside viewpoints, 2D, worst-case furniture ignored):**

| State | Viewpoints seeing the dressing room / ensuite exit / route |
|---|---|
| both doors open | **367 / 371 FAIL** (up to 18 m, incl. stair landing and kids-b doorway) |
| suite door open, dressing door shut | 0 / 371 PASS |
| dressing door open, suite door shut | 0 / 371 PASS |
| both shut | 0 / 371 PASS |

So 2A passes only if the two leaves are never open together. That is the client's rule "a closed door must not be the only protection", so 2A does **not** meet the stated criterion by geometry. It meets it by operation.
- **Closers:** a surface overhead closer (e.g. GEZE TS 3000 / TS 5000, dormakaba TS 93, ASSA ABLOY DC 135 / DC 700) on the suite door; a concealed closer (e.g. GEZE Boxer / dormakaba ITS 96) on the 0.90 dressing leaf. These are named from memory as typical products; **no datasheet is held in the repo, none was verified here.**
- **Force, time, accessibility:** no closing-force or closing-time figure is held in the repo, so none is quoted. EN 1154 (closer sizes) and ADA 404.2.8 / 404.2.9 (sweep time, opening force) are the usual references; look them up with knowledge-search before specifying. Tension: a closer strong enough to latch makes the door heavy for children, the elderly and wheelchair users; a lighter size may not latch, which defeats the purpose. A latch-free, delayed-action closer (adjustable hold-open delay, about 10 to 30 s, to be set) helps with carrying things but lengthens the time the leaf is open.
- **Interlock / sequencing:** a mechanical interlock is not available for two ordinary leaves 3 m apart. Options: (a) an electric interlock with magnet or strike on each door (one opens only when the other is shut; needs power, fails safe open for fire), (b) a door-position contact with a light or chime, (c) delayed-action on the suite door only, with the dressing door spring-closed. (a) is the only one that enforces the rule; it adds an escape/fire question (door must release) and a cost.
- **Risks:** a leaf propped open (wedge, a child, a laundry basket) defeats it silently; a failed or detuned closer (oil leak, wear) does the same, and the fail is invisible; slowness while carrying things pushes people to prop the door. A door-contact alarm covers propping and failure.

## Comparison
| | 3 (as drawn) | 2A |
|---|---|---|
| Buildable | **No**: sits in the sister villa's bath block and over the B alcove window | Yes: inside our own footprint |
| Both doors open | PASS (geometry) | FAIL, 367/371 |
| Privacy depends on | walls | two doors that must close and not be propped |
| Cost (relative; no price source in repo) | highest: facade change, slab extension, planning, neighbour consent, 3 wall runs | low: 1 wall, 1 door, 2 closers (+ interlock if wanted) |
| Pinch | 0.739 | 0.802 |
| Bed centred, solid head wall, hers 2.72 m | yes | yes |

Residual risk of 2A: whenever both leaves are open, anyone in the corridor or on the stair landing sees the dressing room; interlock removes the case, at the price of power and release-on-fire.

## Recommendation
Option 3 is blocked by the site. If the client wants the vestibule: **2A with the electric interlock (so both leaves cannot be open together), delayed-action closer on the suite door and a door-contact alert**, which is the closest to the stated criterion without geometry. If the client will not rely on a door being shut: **keep 1a** (today), which passes with all doors open. Decisions I made: used 0.20 storage and 0.90 dressing door to clear 750 with margin (0.802); named closers from memory and flagged as unverified; gave relative not absolute cost (no source); treated the entry bay as exempt as before. Not built; model, spec and renders unchanged.

---
# Step 2: would rotating the bed let the dressing door sit where the bed head is now? (sketches only, 2026-11-26)
Plans (1:50): `docs/lanes/DF-privacy-options/plan-R1.png`, `plan-R2.png`, `plan-R3.png` (+ .svg, `results-rot.json`). Reproduce: `python scripts/df_privacy_rot.py`. Model, spec and renders unchanged.
**Answer: yes for the door, but only R3 (head north) keeps the bedsides.** The door is option 4's (x 19.577..20.377, west end of the south wall, beside the lobby opening, leaf into the dressing room). It passes all-doors-open in every variant (0/451 viewpoints, same engine and walls as option 4); the old east door is closed as in option 4. The south wall is no longer a head wall in any of them, so the bed never fights the door; the question is only what the room can hold. Room clear 3.92 x 2.80: a 1.6 m bed across the 2.80 m leaves only 1.20 m for two sides, i.e. **0.60 each** (R1, R2).
- **R1** head east: bed x 20.397..22.397, y -25.991..-24.391. Vanity moves to the west end of the north window (x 18.9..19.9, under the window's west edge at 19.36).
- **R2** head west: bed x 18.477..20.477, same y. Vanity stays at the east window (foot to vanity 1.52 m).
- **R3** head north (bed turned 180, the same as today's bed on the other wall): bed x 19.637..21.237 centred on the room, y -25.791..-23.791. Vanity stays at the east window. Foot to south wall 0.80 m, which is the lobby-to-dressing walk-by.

Bedside figure: 750 mm route inside a bedroom, card `ukadm-bedroom-route-750` (UK Approved Document M, a benchmark, not code compliance with no jurisdiction pack), with the repo's rule that both sides must keep 750 even with a 250 tray out (`DF-dressing-door-study.md`). I did not re-read Neufert or the Metric Handbook for this sketch, so no new book page is cited.

| | 1a today | 2A (vestibule, self-closing) | R1 head east | R2 head west | R3 head north |
|---|---|---|---|---|---|
| Bedsides (750 needed) | 1.05 W / 1.27 E* | 1.16 / 1.16 (centred) | **0.60 / 0.60 FAIL** | **0.60 / 0.60 FAIL** | **1.16 / 1.16 pass** (0.76 E beside the vanity) |
| Trays out 250, open width left | 0.80 / 1.02 | 0.91 / 0.91 | **0.35 / 0.35** | **0.35 / 0.35** | 0.91 / 0.91 (0.51 E at the vanity) |
| Route corridor to dressing (length, narrowest) | 11.2 m, 800 mm | 3.8 m, 802 mm | 5.9 m, 800 mm | 5.5 m, **600 mm** (strip between bed and south wall, 1 m long) | 5.9 m, 800 mm |
| Bed to ensuite at night (length, narrowest) | not re-run | not re-run | S side 4.3 m, **600**; N side 6.4 m, **536** | S 3.4 m, **600**; N 6.9 m, **600** | W 5.2 m, 800; E 5.4 m, 800 |
| All doors open: viewpoints seeing in (0 = pass) | 0/451 PASS | 367/371 FAIL (pass only by closers) | 0/451 PASS | 0/451 PASS | 0/451 PASS |
| Headboard under a window | no | no | **yes**, east window (sill 0.9, covers the whole headboard) | no | **yes**, north window (sill 0.9) |
| Hers hanging | 1.72 m | 2.72 m | 1.87 m (+0.15) | 1.87 m (+0.15) | 1.87 m (+0.15) |
| Slat feature wall behind the head | yes (south wall) | yes | **no** (east is the window wall) | **yes** (west wall solid, 2.69 m) | **no** (north is the window wall) |
| Envelope change / buildable | none | none | none | none | none |

\* 1a: bed x 19.53..21.13 in the 3.92 m room, so 1.05 W / 1.27 E by subtraction; the tray-out figures 803 / 1017 are the earlier study's (`DF-dressing-door-study.md`). The 1a and 2A route figures are from the options table above.
Not drawn: the free wall west of the foot in R1 (1.9 m) and east of the foot in R2 (1.5 m) could take a 0.6 m deep wardrobe run in the bedroom; not planned, so no extra hanging is claimed.
R2 variant not drawn: moving the bed 0.15 m north gives 0.75 south / 0.45 north, so only one side passes. Same for R1.

## Recommendation
1. **R3 is the only rotation that works.** It is the only one with both bedsides, both trays and every route at or above 750 (narrowest 800; 760 beside the vanity), it passes the privacy test with all doors open, it needs no envelope change. It costs the slat wall (the headboard sits under the 2.40 m north window, sill 0.9 m: glare, draught, curtain and a window behind the head) and the north wall can no longer be the feature wall. Whether a headboard in front of that window is acceptable is the client's call; I would put the slats on the west wall instead (the west wall is solid, as in R2) as a feature wall not behind the head.
2. **R1 and R2 fail the 750 on both bedsides** (0.60, 0.35 with a tray out). R2 also pinches the lobby route to 600. **Reject both.** R2 is the better of the two only for the slat wall.
3. Against **1a** (keep today): 1a keeps the slat wall and the bed against a solid wall but costs the 9-11 m arrival route. R3 cuts that to about 6 m and loses the slat wall behind the head. Against **2A**: 2A keeps everything but fails by geometry and passes only by two self-closing doors; R3 passes by walls.
**Recommended: R3, if the client accepts a headboard under the north window; otherwise stay on 1a.** 2A (with interlock) remains the fallback if the client wants the vestibule.

Decisions I made: used option 4's door position for all three (it already passed); did not search other positions on the south wall; vanity positions chosen by me (R1 moved out of the bed's north-side route); bedside = clear gap from bed edge to wall (duvet overhang 0.10-0.14 m not deducted, which would worsen every figure); the route length is to the dressing centre point used by earlier options, not to the door.
