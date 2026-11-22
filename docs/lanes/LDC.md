# LDC: landscape critics and their calibration (2026-11-22)

Stage LD-C of `docs/quality/LANDSCAPE-METHOD.md`. Pre-registration: `knowledge/landscape/critic/PREREG.md` (read it for what was seen before scoring).
Results: `knowledge/landscape/critic/calibration.json` (computed criteria), `vlm-calibration.json`, `runs/` (every VLM reply). Tests: `tests/landscape/critic/` (10).

## Headline
**No critic criterion is calibrated under A3** (`calibrated: false` everywhere); nothing here may be used as a gate yet. Why, per critic, is in the table. The computed
critics catch every seeded defect and fail D1, but cannot show a false-fail rate because the professional precedents have no brief, species or site layers; the
site-independent architect criteria were measured on the precedents and missed (30 % false-fail); the VLM plan criteria have no separating power and are demoted.

## API (for LDG)
```python
from archpipe.landscape.critic import critique, verdict, plan_png
findings = critique(layout)            # list[Finding]; critique(layout, vlm=True) adds the advisory VLM composition findings (needs Ollama)
verdict(findings)                      # {critic: "fail"|"pass"}; fail = any blocking/major finding with status fail
plan_png(layout, "plan.png", view=[x0, y0, x1, y1])   # fixed style ldc-plan-style/1; view optional (model metres)
```
`Finding`: `critic, criterion, status (pass|fail|warn|not_evaluated), severity, evidence (achieved vs required), source (rule/card id or "policy"), kind (computed|vlm), subject, calibrated`.
Critics read the design artifact only (layout + site layers + brief); no generator rationale is an input. Hard LDK rules (`LS-*`) are passed through with their source card ids.
**Layout extensions** (optional keys, ignored by LDK): `walls[{rect,height_m}]`, `screens[{rect,kind hedge|trellis|wall,height_m,opacity}]`, `canopies[{rect,kind pergola,height_m,shade_fraction}]`,
`doors[{at,faces,room}]` (default: the LDS openings), path `polyline`/`rect`, plant `at`/`count`/`spread_m`. Seat = a `seating` rect (`seats` along its long side) or a `tables` ring. Zone `use`: dining, lounge, quiet, standing, other.

## Plan renderer (`plan.py`)
One standard for every garden: client north (street) up, scale bar, north arrow, plants as circles at **mature** spread coloured by layer, hatch per surface, walls black, buildings hatched, doors red diamonds, seats, tables, features, pergola dashed, legend. Width 1600 px.

## Critics and criteria (computed vs VLM)
| Critic | Computed (from layout + `plants.json` + LDS layers) | VLM (plan image, advisory) |
|---|---|---|
| landscape-architect | A-ENCLOSURE (share of room perimeter walled/screened >= 1.8 m), A-PATH-TERMINUS, A-THRESHOLD, A-FOCAL, A-HIERARCHY, A-ROOMS; LDK LS-ENCLOSURE, steps, seat walls, lounge cluster | V-ENCLOSURE, V-FOCAL, V-AXIS, V-RHYTHM, V-LAYERING, V-ROOMS, V-OVERALL (prompts quote the AD-COMP advisories; frozen-v0) |
| horticulturist | H-SPECIES-KNOWN, H-SITE-VIABLE, H-SIZE-VS-SPACE, H-BED-CROWDING, H-DRIFTS, H-REPETITION, H-LAYERS, H-SEASONALITY, H-SUN-FIT (species sun class vs LDS sun), H-TOXIC-PLACEMENT, H-FISH-TOXIC (not_evaluated: LDL GAP); LDK tree-building, root zone, soil depth, hydrozone, herb sun, pond shade, hedge spacing | none needed |
| user | U-GATHER-SEATS/-GROUPS/-ROUTE, U-WINTER-STAY, U-QUIET-SOUTH/-NORTH, U-FIRE, U-BBQ, U-POND-VIEW, U-PICKING, U-SERVICE (walk each use from the real doors over walkable ground >= 0.6 m); LDK capacity, dine/lounge/stand area, brief features, path widths | none |
| climate | C-SUMMER-SHADE (6 h full-sun definition), C-SUMMER-EVENING (DST clock), C-WINTER-SUN, C-PRIVACY (per seat, LDS eye points minus layout screens), C-FIRE-WIND, C-POND-SUN; LDK hydrozone, screen height, pond shade | none |

Layout shade: tree crowns and pergolas shade by ray test on the LDS sun samples; crown density is **assumed** (0.8 evergreen, 0.7 deciduous in summer, 0.15 in December, pergola = declared `shade_fraction`). Privacy removes viewers whose sight line to the seat is cut by a layout screen, crown or pergola roof: an approximation (viewers already blocked by the 4 m fences are skipped; the reduction is capped at the raw LDS count). Policy thresholds (not sourced; named in each finding): drift >= 3 plants and 60 % of plants in drifts, >= 3 of 4 layers, flowers in >= 8 months incl. winter, toxic plant >= 2 m from herbs and seats, privacy <= 8 eye points seated on >= 70 % of seats (**relaxed from LDS's 5 so that the reference scheme is the baseline**), >= 2 h winter sun, wind: <= 40 % of seats downwind for > 35 % of hours, pond >= 2 h summer sun.

## Calibration (rules in PREREG.md)
Known-bad: D1 as drawn; 19 seeded defects (set 1; **iterated until each tripped its criterion, so it is a code sensitivity test, not independent evidence**); 9 held-out seeded defects (set 2; written first, not iterated). All made from named quantities on `seeds.base()` (our hand-built reference scheme; not a professional design).
Known-good: 10 LDP precedent plans re-drawn coarsely (`precedents.py`: SME-01/02/05/08, SAU-01/02/04/05, S2-04/20; surfaces, walls/buildings, trees, water, tables, drawn paths; planting species are layer stand-ins; paths I had invented were removed after a first run).
**Only the architect criteria can run on a precedent**: a precedent has no brief, no real species and no site sun/privacy layers.

| Critic | Seeded defects targeting it, caught (n) | of which held-out set 2 | D1 verdict | Known-good false-fail (n) | A3 |
|---|---|---|---|---|---|
| landscape-architect (computed) | 2 of 3 (66.7 %, lower95 25 %) | 0 of 1 (A-ENCLOSURE missed `west-hedge-removed`: the lounge stays at exactly 50 % enclosed) | fail | **3 of 10 (30 %)** | **missed** (false-fail) |
| horticulturist | 11 of 11 | 4 of 4 | fail | not measurable (0 evaluable) | not calibrated: recall-only |
| user | 7 of 7 | 3 of 3 | fail | not measurable | recall-only |
| climate | 8 of 8 | 2 of 2 | fail | not measurable | recall-only |
| VLM plan criteria (7) | n/a: no criterion gated | held-out 4 bad / 5 good, see below | D1 scored 2 on 6 of 7 | 0 of 5 (no gate, so no verdict) | **demoted** |

Architect criteria on the precedents (n evaluated, false-fail): A-ENCLOSURE 10, 3 (SME-08, SAU-02, SAU-04); A-FOCAL 10, 2 (SME-08, SME-02); A-PATH-TERMINUS 2, 2 (the two with drawn paths); A-ROOMS 10, 0 (warn only); A-HIERARCHY / A-THRESHOLD too few. Not tuned. Several of these are plan-reading limits (a garden open to a view is not a defect; my hand-drawn walls are partial), which is exactly why they cannot be a gate yet.

**VLM (qwen3.8:27b-mtp, temperature 0, one criterion per call, frozen-v0).** Tuning half (4 bad, 6 good): no criterion met the pre-registered gate (V-ENCLOSURE and V-FOCAL separation 0.25 with a good item scored 0; five criteria scored 2 on nearly everything, including D1). Held-out (4 bad: oversize-tree, single-layer, no-enclosure, capacity-4; 5 good): V-ENCLOSURE flagged 1 bad / 0 good, V-LAYERING 1 / 0, V-FOCAL 2 / 2 (two good scored 0), the other four 0 bad. Recall 0/4 with the empty gate set. **All seven VLM criteria are demoted to advisory** and `critique(vlm=True)` labels them so. Not tuned further (the D1 defects are brief-level, not visible as composition in a symbol plan, so a prompt edit would only fit noise).
**Photo level (confounded by medium, never gating):** 33 precedent photos vs the 9 D1 renders: P-ENCLOSURE flags 1/9 bad, 5/33 good; P-LAYERS 5/9 vs 14/33 (5 good scored 0); P-FOCAL 3/9 vs 10/33. No separation; the D1 grades are asset-quality grades, so a medium-driven score would have looked like a pass.

## Excluded / not measurable (listed, not hidden)
No seeded defect targets A-FOCAL, A-HIERARCHY, A-THRESHOLD, A-ROOMS, H-REPETITION, H-BED-CROWDING, H-FISH-TOXIC (GAP), U-FIRE, U-PICKING, U-WINTER-STAY, C-SUMMER-EVENING (the sunken south garden gets 0.07 h of DST-evening sun on average, so it cannot fail) and the LDK passthroughs; they are `recall: null`. No defect was excluded for a dirty base.

## The D1 garden's critique (`knowledge/landscape/critic/d1-layout.json`, whole plot)
All four critics fail it. Blocking/major findings: **user**: 4 fixed seats against 10 (no dining group), no quiet seat south or north, no fire pit, BBQ, pond, herb bed or fruit tree, no service path (D1 predates the brief; 10 of the 12 U- checks fail, the route and winter-stay checks pass). **horticulturist**: the frangipani's 7.6 m mature spread in a 6.0 m wide garden (limit 4.8 m); ground-cover soil depth 245 mm against 250 over structure; H-SEASONALITY (flowers 8 months, none in winter), tree-to-building 2.98 m against 5.7 m and 2.0 m of paving inside the dripline (warn). **climate**: 3 of 4 south seats overlooked by more than 8 eye points (raw median 13, 10 after the tree). **landscape-architect**: 4 of 6 paths end at nothing (turf), a single path class. Passes: enclosure (the 4 m walls), sun fit, toxicity, viability, layers (3 of 4).

## Decisions taken (no human available)
1. `calibrated` needs recall >= 90 % over >= 2 bad items AND false-fail <= 10 % over >= 5 evaluated professional-good items; a criterion with no evaluable good item stays `calibrated: false` ("recall-only"). Stricter than reporting recall alone.
2. Photo calibration run but marked confounded and non-gating; no photo criterion ships in `critique()`.
3. One plan view for VLM scoring of our site: the south garden (x 14..29.5, y -31..-19.5).
4. The pre-registration was committed before the VLM and set-2 runs; the held-out VLM half was scored once with `frozen-v0`.
5. Used the project venv's matplotlib for the renderer (no new dependency); the L3 critic's `archpipe.critic.vlm.chat` is reused unchanged.
6. The south "gathering" garden for the user/climate critics is every seat with model x >= 15 (south garden plus yard strip); the north court is x < 8.

## Site facts the critics surfaced (for LDG)
* The sunken south garden gets **no direct sun in a DST summer evening** (mean 0.07 h of 3, max 1.5): shade for summer nights is free, and the real sun problem is the **winter day**: 2.8 h of 5 on average in the south block, **0 h in the yard strip** and 0.1 h in the north court. Gathering seats belong in the south block (x 22.7..26.4), not the yard.
* Full summer sun (>= 6 h on 21 Jun) exists only in a 0.5-1 m strip along the east fence (x 22.5..28, y -21.2..-20.6). Herbs (6 h) can only go there.
* The prevailing wind blows toward the sister plot (west, -y): a fire pit belongs at the west end, seats upwind (east of it).
* West edge: the south block has no wall on y = -29.9 (the sister yard). It needs a screen; the reference scheme uses a 2.4 m hedge.
* North court: only about 9 m2 is open ground (the rest is under the entrance slab) and it is deeply shaded; a pond there fails C-POND-SUN, the yard (3.8-5.5 h) passes.

## Open items
* **Professional known-good for the site critics**: needs scaled professional plans with planting schedules (HALS/APLD/RHS) and a brief-equivalent; or LDG's accepted concept as a control. Until then user/climate/horticulture stay recall-only.
* A larger known-bad/known-good set for the architect criteria (now 3 bad, 10 coarse good) and a measured transcription of the precedent plans; today a 30 % false-fail may partly be my drawing.
* The VLM plan critic needs either a symbol-level plan with legends or a different input (3D perspective renders); the plan image alone did not separate D1 from professional plans.
* Policy thresholds need the client or a source (privacy eye-point limit, winter hours, drift size, crown density); PRIV_MAX was relaxed to fit the reference scheme.
* C-PRIVACY approximates screening; verify it with LDS's ray-caster by re-running `analyse.privacy` on a model that contains the proposed screens.
* H-FISH-TOXIC and several `LS-*` passthroughs report `not_evaluated` until LDL/LDK close their GAPs.
