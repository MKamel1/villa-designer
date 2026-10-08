# Garden rebuild R3b-4 — G2 / D4 final handoff

2026-10-06, uncommitted worktree; follows the frozen G1 diagnosis in [garden-g1-report.md](garden-g1-report.md). **D4 resolves the real low-branch blocker; the authoritative scene builds and exports.** The tree is **in the lawn, offset from centre for a clear door route**. All prior G1/G2 work is retained. No render, photographic approval, commit, full-suite acceptance or real villa design-gate approval is claimed; the lead renders and runs the full suite.

All positions and dimensions are metres in the scene frame: x and y are horizontal coordinates; z is height. The court ground is z = −3.0. Native glTF uses y as height; the importer converts its coordinates to scene (x, −z, y). “Hours” below are hourly samples, not a detailed shadow simulation: the existing `archpipe.solar` June 21, 09:00–17:00 enclosure screen, at the illustrative site with a 3.0 m wall proxy. “ASSUMED” describes authored planting or appearance intent, not verified local nursery performance.

## Lead decisions recorded in the sole palette

- **D1 — lead decision 2026-10-06.** Use uniform scale so actual maximum native horizontal span becomes 4.6 m, with no rotation, nonuniform scale or mesh pruning. Record ASSUMED “rendered stage: young pruned tree”, because “stand-in model proportions wider than the species; canopy span held to the verified 4.6 m spread”. The verified mature height/spread ranges remain 4.6–7.6 m. The mature-circle check still uses 4.6 m.
- **D2 — lead decision 2026-10-06.** Walking occupancy is actual geometry from the route ground to 2.0 m above it. The height is the same passage height used in `render_support.blocked_openings`; its doorway check uses the actual door width and a band on either side of the wall. Route occupancy uses real indexed glTF triangles through node transforms, scale, yaw and floor seating; procedural meshes use their faces. Every prop follows the same rule. Extent/canopy checks still use their full bounds for property/building clearance.
- **D3 — lead decision 2026-10-06.** Client decision 2026-10-05 makes south lawn, paths and one tree only. The layer guard receives the beds actually built: east and north. Adding an unplanted bed under any name still fails; there is no south ID skip.

- **D4 — lead decision 2026-10-06.** Real branches enter the living-south walking envelope at about 1.71 m. The brief means one tree in the lawn; exact centring is secondary to a clear door route. The court has approximately 5.7 m clear width and 9.56 m total length, giving slack along its long axis. Search the whole lawn with x within 0.5 m of the court centre line and y limited by model canopy, mature 4.6 m circle, fence inner faces and plot. Move the pit with the trunk; retain the same uniform scale, no rotation or pruning. Choose the minimum distance from the court centre that passes every guard.

`knowledge/garden-palette.json` remains the sole species and botanical/placement-size authority. It also records the new procedural young-clump envelopes, thin trellis envelopes, door-pot assumption and the RHS sun definition. Egypt performance and root behaviour over the basement slab remain UNVERIFIED.

## D4 tree placement and minimum-offset proof

| Measurement / guard | Achieved versus required |
|---|---|
| Court centre, retained from G1/G2 | (25.577, −25.133330) m |
| Selected measured trunk / pit centre | (25.577, −24.411115286384) m |
| Offset in x / y | 0.000000 / +0.722214713616 m (positive y, east in these court names) |
| Distance from court centre | **0.722214713616 m** |
| Maximum permitted x offset | 0.000000 achieved ≤ 0.500000 m required |
| Uniform scale / rotation | 1.183860391617 / (0, 0, 0) degrees; unchanged; no pruning |
| Actual horizontal span / rendered height | 4.600000 / 3.277387 m; young pruned appearance ASSUMED |
| Conservative placed model bounds | (23.704286, −26.222016, −3.000000, 28.304294, −22.034702, 0.277517) m |
| Mature 4.6 m circle bounds | (23.277, −26.711115, 27.877, −22.111115) m |
| Full model / mature circle within fence inner faces and plot | Pass; rear fence gap remains 0.002705838 m ≥ 0; mature rear gap 0.430 m ≥ 0 |
| Actual walking geometry | No intersecting triangles in any D2 route or any built stepping-stone path, each checked from its actual ground to ground + 2.0 m |
| Trunk seated in pit / turf opening | Zero trunk/pit centre error; rebuilt 1.2 m diameter pit and turf annulus; no capped opening |
| All other landscape guards | Extent, canopy, mature circle, south-only contents, spacing, drifts/layers, sunlight, swing and species/dimension guards all pass; conflicts = [] |

`PYTHONPATH=src python scripts/garden_tree_position.py` reproduces the search. It starts from the measured tree at the court centre and intersects the entire lawn with the x band and the conservative model/mature-circle constraints. The resulting admissible translation domain is x = [−0.500000, +0.002705838368] m and y = [−2.482330, +2.155916615831] m. These bounds cover both ends of the long axis; the search is continuous, not a grid or local radius.

The deterministic Python calculation clips every actual transformed tree triangle to every route's ground-to-2.0 m band. For each clipped polygon and route rectangle it constructs the forbidden horizontal translations, unions all 5,359 contributing polygons and subtracts them from the domain. The closest clear boundary is 0.722213713616 m from the court centre, at zero x shift. The chosen position lies one micrometre beyond that boundary: 0.722214713616 m. That numerical separation avoids touching triangles being reported as intersection; it is not an ergonomic clearance claim. Because the full admissible clear set is searched, no smaller continuous offset clears walking contact. The returned position then passes the independent triangle intersection, canopy/mature and extent guards, and the authored whole-candidate build passes every guard including south contents and planting spacing.

The centred failing tree is frozen by value in `tests/fixtures/garden-g2-tree-centred-before.json`. It still fails the low-branch and export-refusal proofs. Moving the chosen tree 0.01 mm back towards centre fails the route; unrelated triangles, coordinates, floor height and a renamed route prove the search generalises, including a no-solution domain and head-clear geometry. The pit and turf are constructed from the same tracked centre as the measured trunk. Paths, thresholds, boundaries, scales and meshes are unchanged.

The first authoritative portable check then exposed stale pre-D1 scale metadata in the intake manifest: 0.830774788 recorded versus 1.183860391617 built. The old entry is frozen in `tests/fixtures/garden-d4-intake-before.json`; only its independent placement scale/source/reason fields are refreshed to the approved palette. Native bounds and unit conversion are unchanged. Its guard fires on the real old record and a renamed sibling mutation and stays quiet on the current record. This was a downstream mismatch hidden by the earlier upstream build refusal, not a reason to weaken intake.

## Boundary beds and drifts

Bed rectangles below are (minimum x, minimum y, maximum x, maximum y). Three primary layers mean three declared planting height strata; unlike `layer`, which controls lights in the renderer, these use the distinct `planting_layer` field.

| Bed | Rectangle | Centre direct-sun hours | Sample times |
|---|---|---|---|
| north | (-0.05, -29.8, 1.5, -26.9) | 5/9 | 10, 11, 12, 13, 14 |
| east | (17.45, -22.7, 20.05, -20.65) | 9/9 | 9, 10, 11, 12, 13, 14, 15, 16, 17 |

| Bed | Layer | Species | Drift | Centres | Rendered height / maximum span | Spacing required / achieved | Direct-sun samples at plants |
|---|---|---|---|---|---|---|---|
| north | back | Strelitzia reginae | 3 | (1.2, -29.3), (1.2, -28.3), (1.2, -27.3) | 1.100 / 0.500 m | 0.800 / 1.000 m | 5, 5, 5/9 |
| north | mid | Ixora coccinea | 3 | (0.75, -29.3), (0.75, -28.3), (0.75, -27.3) | 0.600 / 0.867 m | 0.960 / 1.000 m | 5, 5, 5/9 |
| north | front | Aspidistra elatior | 3 | (0.18, -29.3), (0.18, -28.3), (0.18, -27.3) | 0.500 / 0.400 m | 0.400 / 1.000 m | 4, 4, 4/9 |
| east | back | Strelitzia reginae | 3 | (17.9, -20.95), (18.75, -20.95), (19.6, -20.95) | 1.100 / 0.500 m | 0.800 / 0.850 m | 8, 8, 8/9 |
| east | mid | Ixora coccinea | 3 | (17.9, -21.75), (18.9, -21.75), (19.6, -22.45) | 0.550 / 0.795 m | 0.960 / 0.990 m | 9, 9, 9/9 |
| east | front | Aspidistra elatior | 3 | (17.9, -22.43), (18.75, -22.43), (19.6, -22.43) | 0.500 / 0.400 m | 0.400 / 0.850 m | 9, 9, 9/9 |

Each ground-bed drift is three of one species. Ixora provides the repeated colour masses; Strelitzia is the taller stratum and Aspidistra the base stratum. North Aspidistra sits on the shadier boundary side (four sampled hours); north Ixora and Strelitzia occupy the brighter five-hour band. The bare-court screen returns nine hours throughout the east bed, so it cannot verify shaded east corners or shade from the future understory. The east Aspidistra base-layer recipe follows the client's part-shade court description; its actual planting microclimate needs a refined shadow/nursery review and is not claimed verified by this proxy.

No Callistemon or Ursinia was added to either court. North has only four/five hours, below the full-sun criterion. East has nine sampled hours, but the recorded 2.5 m minimum mature Callistemon spread cannot form a three-plant drift in its 2.6 m long bed at the existing spacing guard. Ursinia's existing appearance is a 2.30 m wide multi-plant pack, unsuitable for a single court-layer specimen without changing its appearance; its approved existing top placement remains G3 scope. The guard rejects either full-sun-only species in a north ground bed. [RHS shade definitions](https://www.rhs.org.uk/garden-design/shade-gardening) define full sun as more than six direct hours at midsummer; this source and applicability limitation are in the palette.

## Pots and containers

Six hollow, tapered glazed ceramic pots have a distinct raised rim and soil surface 5 mm below the rim. Their ASSUMED bottom/top radii are 0.18/0.25 m; height 0.40 m; rim outer radius 0.259 m. Glaze is TERRACOTTA-RED, client decision 2026-10-05; authored appearance colour and roughness are ASSUMED, not a buyable manufacturer finish. They stand directly on the turf, with no plinth/base. Plant roots are seated at the soil surface. Geometry is closed and outward, and neither soil nor planting is hidden beneath a cap.

| Door-pot name | Centre | Species |
|---|---|---|
| dining-n | (15.882, -22.97) | Ixora coccinea |
| dining-s | (17.896, -22.97) | Ixora coccinea |
| living-east-n | (19.55, -22.97) | Ixora coccinea |
| living-east-s | (21.564, -22.97) | Ixora coccinea |
| lounge-north-w | (2.9, -26.98) | Aspidistra elatior |
| lounge-north-e | (2.9, -25.149) | Aspidistra elatior |

East pots sit in the turf strip between the bed and doorway envelopes. They clear both the garden walking routes and actual doorway volumes. Empty former lemon/olive and unplanted top long containers are removed, rather than rendered empty or replanted with an unapproved asset. Existing two planted top Ixora pots remain for G3; their existing finishes and planting are not claimed to be a finished G3 design.

## Open timber trellises

| Assembly | Wall face / extent | Climber | Direct-sun samples | Coverage |
|---|---|---|---|---|
| east | fence inner face y = −20.601; frame x = 17.988–19.512, y = −20.641–−20.601, z = −3.0–−0.805 | Bougainvillea glabra | 9/9 at (18.75, −20.641): 09–17 | ASSUMED young planting target 35% |
| north | street-fence inner face x = −0.123; frame x = −0.123–−0.083, y = −25.412–−23.888, z = −3.0–−0.805 | Trachelospermum jasminoides | 4/9 at (−0.123, −24.65): 10–13 | ASSUMED young planting target 35% |

Five uprights and three rails form each open frame; bounded branched growth stays on the yard side. The render uses species-specific foliage/flowers: white star jasmine on north, magenta bougainvillea on east. The existing procedural coverage model estimates roughly 42% after its safety margin, below 50%; photographic coverage still requires lead preview. Actual finite C4 boundary hosts support all six frame/branch/climber members with **zero mounting movement**. Nothing is floated toward an old wall-plane guess.

The 12 obsolete landscape movement approvals are retired as data in `knowledge/c4-final-approvals.json`: south/west assemblies removed; east/north rebuilt at their new faces. Original approval coordinates remain under `retired_rows` for the frozen tests. Applying obsolete approvals to new geometry is refused. The two active exterior grille approvals remain. Scene provenance now hashes this authority record as well as the palette.

## Requested furniture

Both pieces fit in the north garden and are flagged **“relocated from the south garden; client to confirm”**. Neither is returned to south. There is no marker alias pretending to be a removed sofa.

| Piece | Centre | Achieved geometry and space |
|---|---|---|
| outdoor_table_chair_set_01 | (2.05, -24.65) | Footprint 0.776 × 1.831 m; bounds (1.662, -25.5655, 2.438, -23.7344) |
| sf_egg_chair | (2.6, -28.35) | Footprint 1.465 × 1.426 m; bounds (1.8675, -29.0631, 3.3325, -27.6369) |

The native bistro is a two-person coffee set, satisfying the lower end of the client's 2–4 range; four seats are not claimed. It has about 0.133 m plan separation from the lounge-north route and 0.143 m from the east court edge. The swing is 1.99 m high on its own stand. With the existing ASSUMED 0.25 m motion allowance on each side, its required free envelope is about 1.965 × 1.926 m; it fits inside the court, with about 0.117 m between its envelope and the bed, 0.034 m to the inner garden-room edge, and about 0.148 m to the nearest pot. These are achieved geometric gaps, not independently sourced ergonomic recommendations. Route, extent, swing-envelope and scene support/door checks are the present physical guards; lead preview and client confirmation remain open.

## Final authoritative validation

All commands used `NO_COLOR=1`, `PYTHONPATH=src`, and `/home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python`; results are judged by process exit status. No packages were installed. Shared `out/villa/round3` and `assets/user` were not modified.

| Check | Final result |
|---|---|
| Combined `tests.test_render_standard`, `tests.test_render_views`, `tests.test_final_mounting`, `tests.test_support_mounting`, `tests.test_landscape`, `tests.test_villa_scene_provenance`, `tests.test_garden_render_subjects` | **120 tests, exit 0** |
| Additional affected `tests.test_asset_intake` | **26 tests, exit 0** |
| `scripts/verify.py --portable` | **exit 0, RESULT: ALL PASS** |
| `render_support.unsupported(VR.build())` | **[]**, authoritative build, no candidate substitution |
| `render_support.blocked_openings(VR.build())` | **[]**, same authoritative build |
| `VR.write()` / scene contract / provenance | **exit 0**, exported `out/villa/render-d1/scene.json`, 35 views including v36 |
| `scripts/garden_tree_position.py` | **exit 0**, continuous minimum and independent tree guards reproduced |
| `scripts/villa_render_views.py` | **exit 0**, full-set framing/clearances and `views-plan.png`; inspected as a plan preview |
| `git diff --check` | **exit 0** |

The support acceptance contains no in-memory candidate replacement. The historical 82-test diagnostic harness, earlier blocked scene tests and failed portable runs in the G2 checkpoint are superseded by this authoritative validation. The first D4 portable failure was retained and fixed as the intake regression above. Tests and geometric projections do not approve photographic appearance: the lead still needs to render and review the new/revised views. A plan preview was produced and inspected, without invoking Blender or rendering.

Initial diagnostic findings were fixed by construction: metre-scale petioles avoid a millimetre furniture helper; fresh-coordinate transforms avoid repeated shared-vertex transforms; curved leaf sides export triangles instead of nonplanar quads; planting strata use `planting_layer` rather than the lighting field. `garden-g2-clump-before.json` freezes the real nonplanar/lighting-namespace failure; the contract fires on it, stays quiet on both current species, and rejects renamed namespace mutations. The actual Blender QA function and render-call expression are also exercised without rendering, preserving a frozen wrong-import-result-name failure. Imported props now resolve directly as view subjects, both from transformed asset vertices in local framing and actual imported mesh vertices in Blender QA; no invisible marker is added.

Current/frozen tests keep the historical excluded species, mature-size tree overrun, old teak sofa, dirty-kitchen bed intrusion, single-row bed, inadequate drift/spacing, swing collision, incorrect bench orientation, old canopy-centred trunk, retired mounting mismatch and lemon/olive camera failures. A process addendum is in [ops/garden-rebuild.md](ops/garden-rebuild.md); `.agents` is mounted read-only on this workstation, so its skill source was not changed.

## Lead render handoff — no render performed

The design is fixed. Cameras may move; plants, furniture, fixtures, routes and the D4 tree/pit must not move for framing. The local checker now projects actual imported vertices rather than fictitious empty corners of an asymmetric canopy box, consistent with actual Blender subject QA. All listed exterior subjects pass whole-vertex horizontal and vertical framing. Their camera proximity checks are empty; the north view's structural centre sightlines are also clear. These geometric checks do not substitute for the lead's photographic sightline/appearance review.

| Views | Final subjects / caption intent |
|---|---|
| v07-terrace-dusk | `landscape-tree-south`, `living-sofa`; “Lawn and young frangipani at dusk”, in the lawn, offset from centre for a clear door route. Camera (28.1, −20.81, −1.65), target (25.6363, −25.1509, −1.65), 24 mm, vertical shift +0.073. Camera-only correction after D4; no sofa alias. |
| v19-garden-facade | `landscape-tree-south`, `living-sofa`; south lawn, stepping approach and young frangipani offset for clear door route; no south furniture/bed/trellis. Camera (28.0, −33.0, −1.65), target (25.5240, −28.6561, −1.65), 24 mm, vertical shift +0.021. Exterior vantage crosses the shared axis, as did the historical façade view. |
| v02-garden-living, v10-living-evening | Existing interior subjects retained; captions describe updated south lawn/tree through living openings and state the D4 offset for a clear door route. |
| v26-top-garden-east, v27-east-yard-above | `landscape-bed-east`, `landscape-trellis-east`; young three-layer bed and thin bougainvillea on open timber; no lemon-pot subject. Existing cameras retained. |
| v28-east-yard-below | Same east bed/trellis subjects, target (19.0, −21.8), camera (14.2, −22.5, −1.65); caption names young bed, open trellis and planted terracotta-red glazed door pots. |
| v25-top-garden-gate | `landscape-top-bench`, `landscape-top-north-ixora`; empty long-planter subjects retired. Caption retains G3 replacement design as pending. |
| **v36-north-garden — added, final-only** | North bed plus each actual back/mid/front planting stratum, north trellis and star-jasmine climber, both planted terracotta-red glazed pot/plant assemblies, imported bistro and stand swing. Camera (0.7, −33.4, −1.65), target (1.4096, −28.4506, −1.65), **24 mm, level, 1.35 m above lower-yard ground**, vertical shift −0.088. Caption states the camera is on the sister side of the shared axis in the modelled lower front-yard strip without a dividing fence; bistro/swing “relocated from the south garden; client to confirm”. |

The north camera was selected around the fixed design. A deck vantage would look through building geometry at parts of the court; the chosen lower-yard view holds all requested contents with clear structural centre sightlines. The plan axis limits now include each actual camera with margin, so the southern exterior v19/v36 cameras are visible in the preview. The lead should render a draft of final-only v36 before its final batch, and inspect the young clumps, thin trellis, pot planting, relocated furniture and the head-low tree near the clear-route boundary. No photographic approval is claimed here.

Current naming authority: [site orientation](../knowledge/site-orientation.json). Historical numeric sun-proxy results in this report are superseded by [the orientation and ray-cast report](orientation-naming-report.md).

<!-- garden-side: -x; name: north -->
<!-- garden-side: +y; name: east -->
<!-- garden-side: +x; name: south -->
<!-- garden-side: -y; name: west -->
