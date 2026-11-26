# Lane DF: the way to the parents' dressing room (2026-11-25)

Client, walkthrough v3 at 6:21 (`~/archpipe/lanes/briefs/evidence/df-books-at-dressing-door-6m21.jpg`): a row of books on a dark surface
in front of the dressing door opening. Base `origin/integ/aplus` `1a238c6` (it had not moved at the end).

## 1. The object: `prop-bedside-books` on `furn-pb-bedside`

| | measured | source |
|---|---|---|
| Bedside `furn-pb-bedside` | x 21.130..21.480, y -26.591..-26.191, top 0.55 m (0.35 x 0.40) | `villa_furnish.layout` |
| Dressing door `door-GF-parents-bed-parents-dressing` | opening x 21.497..22.297 in the head wall y -26.641; swings INTO the dressing room | spec, `DOOR_TYPES` |
| Books before | x 21.286..21.837, z 0.55..0.79 (`evaluated-obstacles.json`, 20 volumes) = **0.357 m past the bedside, 0.34 m inside the door opening, nothing under them** | glTF bounds x -0.019..0.532 (origin at the left end), placed with the origin at the bedside centre at scale 1 |
| Door swing zone | not touched (leaf swings away); the opening and the required approach (0.30 m deep x door width) were | `_door_approaches` |

Yes: it sat in the opening/approach and it floated (0.36 m of the 0.55 m set unsupported).
**Fix (dressing, applied):** scale 0.6, measured bounds seated on the top's centre: x 21.139..21.470, y -26.440..-26.342, wholly on the
top (9 mm and 24 mm margin at the ends). Guard `villa_render.dressing_overhang_violations`.

## 2. The chair pinch and the route (design model, furniture as staged)

Requirement: 0.750 m clear route inside the bedroom (`ukadm-bedroom-route-750`, UK AD M para 2.25a, applied for ageing in place) and for the
private dressing suite (project waiver already in `villa_furnish._route_problems`); 0.914 m elsewhere (`mitton-path-of-travel-min`).
Achieved is the widest disc that can travel the route (`model/circulation.py`, 20 mm cells).

| route entry door -> dressing door | before (chair pulled out 0.30 m) | after (chair tucked) | required |
|---|---|---|---|
| plan pieces + loose chairs | **0.560 m** (bed side 21.13 -> chair 21.697 = 0.567) | **0.780 m** | 0.750 m |
| with the evaluated duvet (+0.10 m) | 0.446 m (WT: 0.47 duvet to chair) | see sensitivity | 0.750 m |

The vanity top itself is not the constraint (bed side to its front 0.867 m); neither is the bedside (it ends 17 mm short of the jamb) nor the bed
position. **Fix (a), applied:** the vanity's chair is staged tucked, as designed furniture (`villa_furnish3d.TUCKED_SEAT`, seat under the top, only the
0.03 m back proud of it); `chair_pulled_out=True` restores the old staging for tests. No bed, room or vanity move.

### Sensitivity, NOT gated, proposal to the lead (nothing applied)
With the simulated cloth as obstacles (`evaluated-obstacles.json`, WT assembly) the same route reads **0.45 m**: the duvet hangs 0.155 m past the mattress
foot (plan gap foot-to-south wall 0.80 m -> 0.645 m) and the heavy-open curtain stacks at the foot corners (x 19.17..19.61 and 21.50..21.94, y -23.98..-23.85)
leave 0.46 m between them and the duvet corner. Options, cheapest first: (1) park the two curtain stacks at the window jambs outside x 19.39..21.23 + 0.75;
(2) cut the pb-bed duvet foot drop (`foot_over` 0.26 -> 0.10 in `villa_render` cloth) and re-simulate; (3) nothing (a person steps round soft cloth).
These touch the dressing/cloth only; none moves the bed. Say which and I apply it.

## 3. General check and villa-wide pinch list

`src/archpipe/model/circulation.py` (`routes`, `pinches`): every door approach of every open cluster (45 rows, B and GF), with chairs and stools as obstacles.
It is wired into `villa_render._build` (raises `staged circulation: ...`), so a chair staged into a required passage cannot reach a render.
Tests `tests/model/test_circulation.py` (7): positive = pre-fix parents' bedroom fails at 0.56 m; negative = tucked design, every other cluster, a pulled-out
desk chair elsewhere (kids-b) stay quiet; dressing overhang positive on the real old books placement.
**Villa-wide, as staged: 0 pinches.** Tightest margins (achieved / required): parents' route 0.780 / 0.750 (+0.030); living-yard from the pantry door
0.966 / 0.914; cinema 0.980 / 0.914; kids-a corridor 1.040 / 0.914; everything else >= +0.1 m.

## 4. Shared-file procedure (no bypass)
Receipts regenerated baseline-relative (old tree `origin/integ/aplus` worktree vs new; only `furn-pb-vanity-chair-1-*` meshes and `bedside-books` differ; 16 individual +
joint reviews ok, 0 findings), both exposure records re-measured with new ids and copied byte for byte (membership flips 0), model snapshot regenerated
(`d1-elements.json`: the bedside books only). Job ids and results are in the hand-back.
