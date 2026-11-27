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
