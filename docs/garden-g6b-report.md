# Garden G6b — appearance fixes and constrained view split

2026-10-07, Linux laneA worktree. Four appearance corrections are complete and the six matched isolated neutral previews are independently accepted. The existing v40 loquat companion remains; the requested separate terrace view is **OPEN**. Rejected camera candidates have not been integrated. No presentation renders or commits were made.

Coordinates are metres: x and y are horizontal model axes and z is up. Client naming follows model −x north, +y east, +x south and −y west; true solar bearing is a separate input. ASSUMED means an authored design or appearance assumption, not surveyed, engineered or nursery-verified evidence. G6 remains a capability example and does not approve a real villa design gate.

## Fixed design and appearance

The recorded G6 plant roots, pergola posts, bowl, bed and wall runs, seat positions and seat facing remain fixed. Frozen actual G6 geometry and metadata are retained in `tests/fixtures/garden-g6b-appearance-before.json.gz`; the fixed-layout regression compares the delivered JSON representation. Envelopes remain the recorded assumptions.

- **Climbers:** both recorded side-post vines now have twining stems from soil to rafters. Petrea on the sunnier recorded side has rough folded elliptic leaves and hanging lavender-purple sprays; star jasmine has smaller glossy leaves and sparse white star flowers. The projected leaf-area union covers approximately 58.85% of the whole pergola plan frame; the denominator is the fixed full frame, not just each trained half. Timber remains partly visible. Petrea's actual maximum height is 2.9273502196 m above root, within the unchanged 2.95 m assumption.
- **Outdoor furniture:** the unchanged 1.40 × 0.65 m two-seat bench and two approximately 0.65 × 0.65 m chairs use original slatted timber lounge frames, armrests and substantial separate seat/back cushions. Actual height is 0.800 m, within the recorded 0.760–0.840 m range. They are labelled **procedural stand-ins**, with authored timber/cushion finishes and unverified weather performance.
- **Loquat:** unchanged run x 24.550–26.850 m, root and envelope. Dense terminal leaf clusters sit on horizontal tier arms tied to the unchanged wall wires. Dark-green folded leaves have physical midribs and pinnate veins; trunk, tiers and frame remain partly visible. Repeated clusters remain a disclosed procedural appearance.
- **Dwarf Pittosporum:** continuous low branching rounded mounds replace bare-trunk lollipops in the south bed, bowl and east yard. Glossy obovate leaves occur in tip whorls; actual low foliage surrounds all eight measured crown sectors within the existing 0.20 m soil-gap limit. The same builder supplies both yards.

Botanical records were read from [NC State Petrea](https://plants.ces.ncsu.edu/plants/petrea-volubilis/) (rough elliptic leaves 4–9 inches; Purple/Lavender racemes; Spring, Summer, Winter), [NC State star jasmine](https://plants.ces.ncsu.edu/plants/trachelospermum-jasminoides/) (opposite lustrous leaves and small white flowers), [UF/IFAS loquat](https://ask.ifas.ufl.edu/publication/ST235) (leaves 8–12 inches, equivalent to 0.2032–0.3048 m, pinnate venation) and [NC State Pittosporum](https://plants.ces.ncsu.edu/plants/pittosporum-tobira/) (rounded/mounding habit, compact dwarf cultivars and crowded obovate leaves at twig tips). Selected base leaf lengths are ASSUMED: Petrea 0.200 m, jasmine 0.085 m, loquat 0.250 m and Pittosporum approximately 0.062–0.078 m before its recorded plant-envelope scaling. Blade width, optical roughness, gloss, flower size and seasonal display remain appearance assumptions in `knowledge/garden-palette.json`; this display is not year-round flowering evidence.

## Furniture licence and uniform-scale screen

A bounded read-only library search found the available [Outdoor couch](https://sketchfab.com/3d-models/outdoor-couch-14ecedd104db478289ee12a88ab9bc59), by **3D_for_everyone**, recorded **CC Attribution**. Full imported geometry measured 4.1282767 × 3.7304679 × 1.4955132 m. Maximum uniform scale fitting the bench footprint is 0.1742409, producing only 0.2605795 m height versus the required 0.760–0.840 m. It was rejected; no asset was rescaled nonuniformly or integrated. This search does not claim that no suitable free model exists anywhere.

Receipts: `out/garden-g6b/furniture-library-search.json`, `furniture-library-candidate.json` and `furniture-scale-screen.json`. No new imported furniture was used, so no external attribution or imported route record is invented for the original stand-ins. Existing imported asset route geometry remains subject to the focused route/provenance tests. Protected shared asset/model symlinks were not modified.

## Matched neutral before/after previews

Every pair preserves the exact receipt camera, rotation, orthographic scale, rigid staging origin and 1.8 m scale reference. Geometry is translated only for isolated diagnosis. Final independent appearance review: `out/garden-g6b/isolated-critic-review.md`.

| Assembly | Before | After |
| --- | --- | --- |
| Pergola/climbers | `out/garden-g6b/before/pergola-climbers.png` | `out/garden-g6b/after/pergola-climbers.png` |
| Outdoor seating | `out/garden-g6b/before/outdoor-furniture.png` | `out/garden-g6b/after/outdoor-furniture.png` |
| Loquat espalier | `out/garden-g6b/before/loquat-espalier.png` | `out/garden-g6b/after/loquat-espalier.png` |
| South foliage | `out/garden-g6b/before/south-layered-foliage.png` | `out/garden-g6b/after/south-layered-foliage.png` |
| East foliage | `out/garden-g6b/before/east-layered-foliage.png` | `out/garden-g6b/after/east-layered-foliage.png` |
| Centrepiece | `out/garden-g6b/before/centrepiece.png` | `out/garden-g6b/after/centrepiece.png` |

Final Petrea image SHA-256 (content checksum): `cde335817a893d104ed66c3ca05baf8fb144b42b2c99a5c626a4eeaf5da80e09`. Staging/provenance receipts are `before/isolated-preview-evidence.json` and `after/isolated-preview-evidence.json` under `out/garden-g6b`.

Six existing context previews use the unchanged authored cameras. The first regenerated v27 landscape frame clipped a fuller shrub; its separately reviewed portrait correction retains the exact position, target and 24 mm lens, with the same physical full-frame sensor rotated. The accepted candidate is `out/garden-g6b/candidate-upper/v27-east-yard-above-neutral.png`; the final regenerated v27 path below uses that corrected aspect. Original paths are `out/garden-g6/<view>-neutral.png`; refreshed paths are `out/garden-g6b/after/<view>-neutral.png`, where `<view>` is one of `v02-garden-living`, `v07-terrace-dusk`, `v10-living-evening`, `v19-garden-facade`, `v27-east-yard-above`, `v28-east-yard-below`, `v40-south-garden-espalier`. Their review and limits are recorded in `out/garden-g6b/context-critic-review.md`. They do not collectively certify the missing single terrace view.

## Terrace camera result

The intended split is one 24 mm level-eye open-area terrace camera with both climbers, centrepiece and all three seating pieces, plus v40 for the complete loquat. v40 now explicitly requires full actual-vertex framing in both axes; build, render contract, view plan and portable verification execute that intent without a view-identifier whitelist.

The bounded 1.35 m standing-eye landscape search tested 5,358 positions on a 0.10 m grid. Of these, 4,401 passed open-sky/yard candidate screening, 2,124 framed all physical subject vertices, and 75 survived the unchanged 1.0 m exterior clearance screen. None passed the existing majority screen for all six named targets (bowl, bench, both chairs, Petrea, jasmine), which requires at least 7 of 13 first-hit rays per target. Final-authoritative receipt: `out/garden-g6b/terrace-camera-authoritative-search.json`; earlier staging receipt: `terrace-camera-accepted-search.json` (same measured counts); command exits 1 deliberately when no candidate is selected. Local refinements and physically rotated portrait 24 mm sensor candidates also retained all targets; portrait corner views framed the assemblies but planting screened the bowl/bench. These bounded results are not a mathematical impossibility proof.

Two reviewable camera-only diagnostics were rendered without changing exported design geometry:

- `out/garden-g6b/candidate-context-authoritative-west/v41-south-garden-terrace-neutral.png` (final export), with earlier staging image `out/garden-g6b/candidate-context/v41-south-garden-terrace-neutral.png`; input `candidate-terrace-west-view.json`: bowl and trained vines are identifiable, but the bench is almost end-on (92.986 degrees from its front, only 71.61 pixels wide in a 960-pixel image), and chair 1 has only 6/13 successful rays. The reviewer rejected closure of the seating ensemble.
- `out/garden-g6b/candidate-context-authoritative-east/v41-south-garden-terrace-neutral.png` (final export), with earlier staging image `out/garden-g6b/candidate-context-east/v41-south-garden-terrace-neutral.png`; input `candidate-terrace-east-view.json`: a better bench front angle (58.028 degrees) is outweighed by the retained imported frangipani physically screening much of the terrace. Jasmine has only 5/13 successful mesh rays. The reviewer rejected this candidate.

The existing sightline consumer traces authored meshes; imported props require actual neutral image review, as these rejected images demonstrate. Full framing or successful mesh-only rays cannot certify readability. No target was removed, no guard weakened, and no plant or seat moved to obtain a camera. A further view split would change the requested deliverable and remains a lead decision if camera-only continuation cannot resolve it. A separate 1.65 m eye-height diagnostic search (`terrace-camera-high-search.json`) tested the same 5,358 positions, found 2,155 fully framed and 75 clear candidates, and selected none. It is not an adopted camera and lies above the existing render-standard eye-height range. Local west-camera eye refinements also selected no solution (`terrace-eye-refinement.json`). No height rule was changed.

## Defect prevention and acceptance

Frozen original and first-fix geometry reproduce the real failures. Construction now prevents generic oval vines, stacked shrub rings and above-beam racemes. Species form, low foliage distribution, crown taper/continuity, actual leaf size, post twining, below-beam Petrea flowers, physical loquat veins/ties and lounge anatomy run through the authoritative scene guard. Renamed/translated siblings and missing-part mutations prove refusal; current south/east constructions stay quiet. Actual visual likeness still requires independent review.

The learning entry is `garden-g6b-species-forms` in `docs/LEARNINGS.md`; its registered proof list is in `knowledge/garden-render-guards.json`. Garden workflow and canonical villa-render skill were updated together; generated Claude adapters were synchronised. Final command results are bound to the receipt paths below. Numerical scene acceptance does not close the unresolved terrace view.

Acceptance requires exit 0 from all final commands and empty authoritative failure lists. Read the final execution receipts and logs below together with `out/garden-g6b/acceptance.json`; earlier runs are not final current-source proof.

| Acceptance | Final log / evidence |
| --- | --- |
| Focused landscape, render standard/views, final/support/exterior mounting, provenance, garden subjects, route geometry, all G6 families and agent adapters | `out/garden-g6b/focused-tests.log`; affected final reruns `final-regressions.log` and `final-camera-consumers.log` |
| `scripts/verify.py --portable`, normal environment | `out/garden-g6b/verify-portable-final.log`, `verify-normal-exit.json` |
| `scripts/verify.py --portable`, initially empty process HOME | `out/garden-g6b/verify-empty-home-final.log`, `verify-empty-exit.json` |
| Current-source authoritative scene producer | `out/garden-g6b/authoritative-final.log`, `authoritative-exit.json`, `acceptance.json`, `scene.json` |
| Actual view plan, direct output-scoped CLI | `out/garden-g6b/views-final.log`, `views-exit.json`, `views-plan.png` |

Commands use `/home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python`, `PYTHONPATH=src` and `NO_COLOR=1`. The lead owns the full-suite run. The appearance package is accepted; the unfulfilled terrace composition prevents complete G6b deliverable closure even when all numerical acceptance commands pass.


Upper-view failure proof: `tests/fixtures/garden-g6b-upper-frame-before.json.gz` records actual landscape-camera geometry. Its vertical extent is 0.7389477066 sensor-width units versus a 0.6666666667 landscape frame. The corrected portrait extent is 1.1084215598 versus a 1.5000000000 frame; the same position/target yields 12/13, 12/13 and 13/13 plant sightlines. Independent review accepts the whole three-layer grouping. The initial view-plan inline wrapper discarded the script's returned failure status; the new `--output` CLI is tested directly on the actual failing export (exit 1) and current export (required exit 0). The substantive naming/coordinate rereview preserves both garden identities and the fixed G6 run; no compass/solar mapping changed.


Final-source checkpoint: the staging camera scene was unstamped and used an unresolved-door state, so its whole-scene equality audit failed. The final authoritative export exactly matches the committed G6 scene's mesh identifiers and every unaffected mesh; only the permitted appearance meshes change (`out/garden-g6b/g6-fixed-scene-comparison.json`). Garden meshes/materials/imported props agree between staging and final inputs, but that narrower equality cannot certify the full context. Camera search now requires the current authoritative source stamp, before and after tracing. Repeated search on the actual export selects no camera; both repeated final-source context images retain their independent rejection. The final v27 portrait image is pixel-identical to its accepted candidate: decoded image values match exactly; file checksums differ only in PNG text metadata. Review: `out/garden-g6b/context-critic-review.md`.

The initial 199-test process exited 1: eight new finishes were missing from the independent register; it also retained old modules/view values while source changed. That run is preserved as `out/garden-g6b/focused-tests-before.log`. The eight appearances are now explicitly registered, preserving unknown-name refusal. Portable verification checks the literal independent finish register before scene build. Frozen actual old register, current clean material names and arbitrary renamed names prove the control. The stable-source affected subset passed 29 tests, exit 0; final full focused execution and returned exit status are in `focused-tests.log` and `focused-exit.json`. No failed or mixed-source run is reported as passing. Final camera-consumer reruns are recorded in `final-camera-consumers.log` and `camera-consumers-exit.json`. Both environment portable checks and authoritative/view-plan checks returned 0 at the prior checkpoint; final receipts listed above replace them after the documentation/control update. The source API is frozen before those final processes.
