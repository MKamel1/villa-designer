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

# Lane DF, round 3: slim bed-mounted headboard with floating ledges (2026-11-25, client revision)

Brief: `docs/decisions/interior-presentation-2026-11-22.md` (2026-11-25 revision, the last section governs). The built-out wall failed the foot route.

## What was built (design model, not render dressing)
| Item | Where | Measured |
|---|---|---|
| Headboard = 50 mm panel fixed to the bed | DESIGN MODEL only: `villa_furnish` pb-bed `headboard_m=0.05` -> `villa_furnish3d` headboard part (Revit/d1-elements), and the generated procedural bed (`furniture._build_bed_double(headboard_mm)`) | was 220 mm (generated) / 60 mm (model parts). **NOT DONE in the render: the rendered pb-bed is the imported CyberFox upholstered bed (`knowledge/parents-bed.json.gz`), whose headboard is about 0.12 m deep (source 0.147 m x 0.835 frame slimming) and still renders at that depth.** Thinning it means editing a lead-reviewed imported mesh (new frame-slimming rule, neutral previews); not attempted. |
| Matched pair of floating ledges `pb-ledge-w`/`pb-ledge-e` (type `bedside_ledge`) | `villa_furnish.layout`, parts in `villa_furnish3d.body` | 280 wide x 300 deep (50 mm panel wing to z 0.96 in taupe fabric + 250 mm ledge), top 0.525 m, walnut top, 80 mm walnut drawer front, oak body, no handle, no legs. Mounting: the wing is hosted on the bed headboard's end face, the body on the wing (`support_mounting`), so the floor-standing/finished-face checks stay quiet |
| `pb-bedside` (and its books) removed; the "west wall shelf" never existed as a model element (only a sentence in a `why` string), so there was nothing to delete | | |
| Wardrobe, bed position, cove, swing-arm lamps | untouched. The bed moved 0 mm of the 50 allowed: the lead-approved mounting rows and the slat trim are bound to its x | |
| Duvet cut (`PB_DUVET_OVER/FOOT` 0.03/0.0, was 0.26/0.26) and ledge colliders | `villa_render` | |
| Curtain stacks parked east (`CURTAIN_PARK`), one-way draw | `villa_render` + `villa_scene.build_curtains` | stacks x 21.695..22.376 |

Ledge width is 280, not 300: at 300 the west passage was 0.753 m, which the 20 mm grid reads as 0.746 (the gate would tolerate it by half a cell; not relied on).

## Measurements before -> after (`model/circulation.py`, 20 mm grid, +-10 mm)
| | before | after | required |
|---|---|---|---|
| Foot route entry door -> dressing door, plan pieces | 0.78 m | 0.76 m | 0.75 m (UK AD M 2.25a, card ukadm-bedroom-route-750; project waiver for the dressing suite) |
| same, WITH the evaluated cloth as obstacles | 0.45 m | 0.76 m | 0.75 m |
| West entry passage, ledge face to west wall face (18.477) | n/a (bedside on the east) | 0.773 m | 0.75 m, same card |
| Dressing door approach (0.30 m deep, door width) | 0.92 m, bedside 17 mm from the jamb | 1.02 m plan / 0.88 m with cloth; east ledge 87 mm from the jamb | 0.75 m |
| Ledge top vs mattress top | bedside top 0.55 vs 0.525 | 0.525 vs 0.525 (0 mm); duvet top 0.629 | client intent: top at mattress height |
| Reach from pillow centre (19.96/20.70, y -26.271, z 0.586) to drawer front | 0.45 m to the bedside | 0.43 m horizontal to the ledge edge, 0.57 m to the drawer front centre (0.58 m with the 0.13 m drop) | **no sourced reach figure found** (knowledge search returned nothing): reported as achieved only, not judged |

The foot passage is 0.80 m between the bed foot and the south wall's FINISHED face (y -23.791, not -23.591: the wall solid spans -23.791..-23.591), so the
duvet may hang at most 0.05 m past the foot. Measured (Blender-evaluated cloth, `scripts/df_evaluated_boxes.py`): duvet y to -24.573 (0.018 m past the foot), x 19.485..21.178.

## Why the curtains had to move to one side
With stacks at the jambs the route reads 0.58-0.63 m (raster over the evaluated boxes). The SW column and the 0.77 m west passage leave no room for a stack on the west side at all (0.63 m even at x 18.88),
so both leaves draw east, gathered tighter (0.34 m a leaf instead of 0.18 x width = 0.42 m): stacks start at x 21.70, where the route is no longer the limit.

## Renders (jobq, Cycles on GPU, exposure records re-measured under new job ids; first attempts OOMed: host RAM kill, then VRAM held by other lanes)
`out/df/render6/v05/v05-parents-bedroom.png`, `out/df/render6/set/n13-parents-day.png`, `out/df/render6/set/n17-parents-headboard.png` (new view `n17-parents-headboard`
in `knowledge/render-set/views.json`), copies in `~/archpipe/lead/out/gallery/src-df/df3-*.png`. LOOKED at: slim ledges with walnut tops and no handles read at both sides of the bed; the wings are taupe against the
imported bed's grey headboard (no exact library match for its texture) and 0.96 m high against its 1.36 m; the thick imported headboard is unchanged (see above).

# Lane DF, round 4: custom joinery queen bed with a pull-out tray in each side rail (2026-11-26, client revision)

Brief: `docs/decisions/interior-presentation-2026-11-22.md` (2026-11-26 section governs). The floating ledges stood in the entry opening (0.77 m left) and 9 cm from the dressing door frame.

## What was built (design model AND render, one source: `furniture.JOINERY_BED`)
| Item | Measured / stated | Basis |
|---|---|---|
| `furn-pb-ledge-w` / `-e` | removed (item, catalogue type, mounting branch, schedule rows, tests) | client |
| Imported CyberFox bed | retired: `knowledge/parents-bed.json.gz` status `retired` (history kept), `parents_bed.apply` returns the scene untouched; `sf_chelsea_bed` binding dropped | client |
| Mattress | **1600 x 2000**, top 0.525 m, 170 mm thick; bed centre (20.33, -25.591) UNMOVED; footprint 1.6 x 2.0 | client |
| Frame | walnut deck = exactly the mattress outline (the deck sides ARE the side rails): plinth 100 mm recessed 60 mm, carcass 100-355 mm, top board 337-355 mm | own design |
| Headboard | 50 mm thick, walnut frame 50 mm wide + recessed upholstered panel (boucle, the lounge sofa's fabric), z 0.525-1.35 m, full bed width 1.6 m; floats from the mattress top (the mattress runs to the wall, so it adds nothing to the 0.80 m foot passage). Frame stile width = one slat pitch (50 mm); the 2.10 m oak slat wall continues above and beside it; the swing-arm lamps (1.45 m) and the ceiling cove are unchanged | own design |
| Trays | one per side rail: push-to-open, **no handle**, front 18 mm walnut flush with the rail face (3 mm reveal), 450 mm long along the bed (0.35-0.80 m from the head wall, beside the pillows), 122 mm tall front, stored 0.30 m deep under the mattress, tray body 100 mm high | own design |
| Runner basis | **Blum MOVENTO 760H, nominal length 270 mm, full extension, with TIP-ON (push-to-open)**, catalogue part 760H2700T. Load: Blum lists 40 kg dynamic for the 760H (retailer/catalogue extracts, https://publications.blum.com/2022/catalogue/en/442/ and https://publications.blum.com/2022/catalogue/en/436/); the 760H2700T's own column was NOT confirmed from the extracts: check the Blum datasheet before ordering. Design contents: a phone, glasses and a book, about 2 kg, ASSUMED. The tray is not a seat or a step. Alternative Häfele/Hettich runner of NL 270 is interchangeable in the same pocket | Blum |
| Pull-out | 0.25 m beyond the side rail at full extension (runner travel about NL less the retained overlap; ASSUMED, confirm on the datasheet). Usable surface 0.25 x 0.45 m exposed (a 148 x 210 mm paperback, a phone and glasses lie flat) | achieved only: no sourced reach or tray-size figure was found, nothing is judged |
| Tray rim height | 0.337 m (the deck): 0.19 m BELOW the mattress top (0.525). The brief asked for the tray top at mattress height; that cannot be done inside the footprint, because the runner has to live under the mattress. Reported, not hidden | physical |

## Measurements (`scripts/df_tray_measure.py`, `model/circulation.py`, 20 mm grid, +-10 mm)
| | closed | both trays out 0.25 m | required |
|---|---|---|---|
| Parts beyond the bed footprint | **0 mm** | west tray x 19.280, east tray x 21.380 (0.25 m past the rail) | nothing closed |
| Entry opening approach (lobby door) | 1.000 m | 1.000 m | 0.750 m (ukadm-bedroom-route-750) |
| Clear width west of the open west tray to the west wall face (18.477) | 1.053 m | **0.803 m** | 0.750 m |
| Dressing door approach | 1.183 m | 1.000 m | 0.750 m |
| Open east tray to the dressing door frame (x 21.497) | 0.367 m | **0.117 m in x**, 0.35 m in y from the door line; the leaf swings AWAY into the dressing room and the approach (0.30 m deep, x 21.497-22.297) is not touched | clear of swing and approach |
| Route entry -> dressing door, plan | 0.780 m | **0.766 m** | 0.750 m |
| Same WITH the evaluated cloth (`scripts/df_evaluated_boxes.py`, re-measured on this tree) | 0.780 m | **0.766 m** | 0.750 m |
| Duvet (evaluated) | y -26.076..-24.619, x 19.479..21.174 (foot 0.028 m inside the bed foot) | | |

The pinch with trays out is the east tray corner against the vanity corner (x 21.997, y -25.3). First draft (tray window 0.45-0.90 m from the head wall) read **0.708 m** there; moving it 0.10 m toward the head and fixing the pull at 0.25 m gave 0.766 m (negative control `test_the_first_draft_window_would_have_pinched_the_vanity_corner`).

## Shared-file procedure
Receipts regenerated (`refresh_furniture_integ5.py export / review-current`, `refresh_receipts.py`, now bed-retirement aware): 15 individual + joint reviews, 0 findings; record `refresh_2026_11_26_DF`. Evaluated cloth boxes for the parents' bedroom re-measured (job `DF4-cloth-boxes-2`) into `knowledge/flythrough/evaluated-obstacles.json`. Exposure records and the model snapshot re-measured; job ids in the hand-back.

## Renders (LOOKED at all four; jobq, Cycles on GPU, 96 spp, 1920 x 1280)
`out/df/render7/set/n13-parents-day.png`, `out/df/render7/set/n17-parents-headboard.png`, `out/df/render7/set/n18-parents-tray-open.png` (NEW view: the east tray pulled out 0.25 m, closed copy hidden, camera looks down: `eye_m`/`target_m` in `knowledge/render-set/views.json`), `out/df/render7/v05/v05-parents-bedroom.png`; copies `~/archpipe/lead/out/gallery/src-df/df4-*.png`.
Seen: the walnut deck reads as the rail with no handle and a 3 mm reveal; the open tray is a walnut-fronted open box; the cream boucle panel sits in a 50 mm walnut frame under the slat wall with the lamps above its top rail. Defects found and fixed on the way: a solid-box tray (now open), slat fronts showing through the panel (the wall trim re-spaces the slats, so a cut in plan coordinates missed the east end; the panel now stands 3 mm proud), the n18 camera framing the pillows (target now below the eye).
Jobs: `DF4-cloth-boxes-2` (evaluated cloth), `DF4-measure-prod-5` and `DF4-measure-set-6` (exposure on GPU: a CPU-measured record is refused as "GPU evidence differ"; `ARCHPIPE_CYCLES_CPU` is read nowhere in the source), `DF4-render-seq-6` (n13, n17, n18, then v05; parallel render jobs ran out of VRAM beside the client's RAG service, so one sequential job at `--vram-mb 12000`).

## Tests
exchange.integrate lane suite: 889 passed, 3 skipped, 1 xfailed; its one failure was the snapshot furniture count 79 -> 77 (the two ledges), expectation updated. Scene-building suites (snapshot, interior, villa, render_standard, beds, support_mounting, d1, mounting, exposure, furniture, views): 547 passed, 11 skipped, 5 failed, all five bed expectations, now updated with reasons and re-run green (8 selected tests): the 0.525 m mattress above the plan's h 0.5 (`F3.ABOVE`), the joinery bed's generated envelope height, the headboard part names, the parents' duvet cut (client route decision, no longer asserted to hang 0.25 m), the parked curtain stack (>= 0.30 m, <= the 0.18 ratio). `tests/model/test_circulation.py`: 17. verify.py: ALL PASS (two bed expectations rewritten: the joinery bed is not a fallback stand-in; the imported bed is retired). run_d1: 198 results, 13 `fail` rows, all outside this change (stair width/risers/closed risers, cinema/kitchen daylight and glazing, core door, cinema escape: informative or A+ targets); none concerns the bed or its trays.
