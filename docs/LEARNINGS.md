# Reusable engineering lessons

### units-and-frames-phase1 — coordinate or unit conversion scattered across subsystems
- Observed: repeated unit and coordinate frame escapes across pipeline subsystems: (1) `l0182`: EnergyPlus simulation results in Joules converted by Ladybug to kWh were divided by 3,600,000 a second time, collapsing calculated thermal loads by 3.6 million; (2) `l0473`: `solar.sun_position` calculated true solar minutes directly from `when.hour`, silently ignoring `tzinfo` when passed aware local time (Cairo UTC+2 gave an 81-degree altitude error); (3) `l0114`: converted EULUMDAT C0 azimuth differed by 90 degrees from IES LM-63 H0 azimuth; (4) `l0012`: DirectShape baked rotations caused world bounding box and insertion point misalignment; (5) `l0023`: Revit ViewDirection points toward the viewer, inverting interior elevations; (6) `l0409`: section cut planes drawn mirrored due to coordinate handedness inversion; (7) `l0669`: parents' bed rendered head-to-foot when generator rotation map inverted 0 and 180 degrees; (8) name collision where `revit/extract_model.py:mm()` converts feet to mm while `src/archpipe/radiance.py:mm()` converts mm to metres.
- Found by / stage: lessons audit (class C9), lead reviews, render visual verification, and energy/daylight simulation checks across stages 1 through 7.
- Reproduction: `tests/test_units.py` reproduces all real failure cases as data:
  1. `test_thermal_3_6_million_error_reconstruction`: freezes raw simulation energy (36 GJ = 10,000 kWh) and proves secondary division yields 0.002778 kWh (exact 3,600,000 ratio), resolved by `joules_to_kwh` and `JOULES_PER_KWH`.
  2. `test_solar_utc_contract_reconstruction`: proves 09:30 Cairo local time (UTC+2) produces a 2-hour (30-degree) hour angle error, and proves `require_utc` rejects naive and aware non-UTC inputs while accepting UTC.
  3. `test_gltf_yup_to_scene_zup_real_frangipani_bounds`: verifies `gltf_yup_to_scene_zup` on real `sf_frangipani` bounds from `ops/workstation/library-manifest.json` against `villa_landscape.py:78-80`.
  4. `test_guard_catches_unallowlisted_literal`: proves `check_units_guard` fails on raw 304.8 in a new file.
  5. `test_guard_passes_allowlisted_literal`: proves allowlisted historical lines pass quietly.
  6. `test_guard_fails_closed_on_unreadable_file`: proves corrupt/unreadable files raise `UnreadableInputError`.
  7. `test_units_conversion_guard_registration`: verifies C9 guard registration and coverage for all 7 C9 lessons in `guard_registry`.
- Direct cause: raw literal conversion factors (`304.8`, `0.3048`, `1000.0`, `0.001`, `90.0`, `3.6e6`) and coordinate swaps were written inline in separate callers without a single authoritative typed boundary.
- Escape: tests verified isolated caller math rather than checking that unit conversions pass through a typed boundary; static checkers did not detect raw conversion literals.
- Class (general root): coordinate or unit conversion scattered (audit entries l0012, l0023, l0114, l0182, l0409, l0473, and l0669).
- Siblings: all modules translating lengths (decimal feet, millimetres, metres, inches), angles, energies (Joules, kWh), timeframes (UTC vs local), or coordinate frames (glTF Y-up vs Blender Z-up, Revit ViewDirection, DirectShape rotation).
- Control tier: tier 1 (prevent by construction) via `src/archpipe/units.py`; tier 2 (detect early and fail closed) via `src/archpipe/units_guard.py` and `units_conversion_guard` in `guard_registry`.
- Control: `src/archpipe/units.py` defines exact physical constants citing the 1959 International Yard and Pound Agreement (NIST SP 811), typed conversion helpers (`mm_to_ft`, `ft_to_mm`, `m_to_mm`, `mm_to_m`, `m_to_ft`, `ft_to_m`, `in_to_mm`, `mm_to_in`, `joules_to_kwh`, `kwh_to_joules`), timezone validator `require_utc(dt)`, and frame converter `gltf_yup_to_scene_zup(x, y, z) -> (x, -z, y)`. The static guard `units_guard.py` scans `src/archpipe`, `revit`, and `scripts` for raw literals (`304.8`, `0.3048`, `3.28084`, `25.4`), failing closed on unallowlisted sites or unreadable inputs.
- Phase 1 Inventory: 21 conversion sites inventoried in `docs/units-and-frames.md`; 5 existing raw literal sites allow-listed in `knowledge/unit-conversion-allowlist.json`. Callers intentionally not refactored in Phase 1 (migration scheduled for Phase 2).
- Proofs: `tests/test_units.py` (all tests passing), registered guard `units_conversion_guard` verified on real failing fixture `tests/fixtures/c9_unallowlisted_case` and clean active codebase.
- Registry: `units-and-frames-phase1` -> `src/archpipe/units.py`, `src/archpipe/units_guard.py` (`units_conversion_guard`) -> `tests/test_units.py` -> unit and coordinate frame boundaries.

### pipeline-result-lacks-atomic-proof — pipeline stages report pass or reuse cached artifacts without proof of completeness and currency
- Observed: repeated pipeline escapes across multiple subsystems: (1) `l0029`: a script printed "FAIL" in its diagnostic report but returned exit code 0, allowing broken pipeline stages to pass undetected; (2) `l0040`: unchanged camera jobs were reused after unrelated documentation/orchestration modifications; (3) `l0068`: fixtures rendered as isotropic points because fallback paths printed a note without failing closed or remapping IES paths; (4) `l0089`: concurrent repository edits went unverified against current source hashes; (5) `l0133`: resume logic re-ran downstream stages despite intact outputs; (6) `l0287`: unpersisted expensive results were lost to downstream serialization crashes; (7) `villa-render-stale-scene`: renders showed an old `scene.json` (from 2026-09-30) while downstream QA reported pass.
- Found by / stage: lead review, integration tests, and presentation reviews across stages 3, 5, 6, and 7.
- Reproduction: `tests/test_stage_result.py` reproduces all real failure cases as data:
  1. `test_l0029_fail_verdict_refuses_zero_exit_and_clean_verdict_passes`: reproduces a report with FAIL (dict, text, bad count) returning exit 1 via `enforce_clean_verdict`, while clean reports return 0.
  2. `test_l0040_cached_stage_reused_after_input_change_fails_closed`: reproduces modifying an input specification after an initial stage run; consumer validation raises `StaleInputError` and refuses cached reuse.
  3. `test_partial_output_set_reported_complete_fails_closed`: reproduces a stage missing an expected output or emitting a 0-byte output file; raises `IncompleteOutputError`.
  4. `test_stale_scene_consumed_by_render_fails_closed`: reproduces the real stale-scene defect by modifying upstream source code after scene generation; render consumer raises `StaleInputError` before rendering.
  5. `test_tampered_output_fails_closed`: proves modified output bytes fail validation with `IncompleteOutputError`.
  6. `test_failed_exit_code_stage_refuses_consumption`: proves a stage that exited non-zero raises `FailedStageError`.
- Direct cause: stages reported success or downstream stages consumed outputs without verifying input freshness, code provenance, and output completeness against atomic content hashes.
- Escape: checks evaluated only local in-process data or exit codes without asserting that required disk artifacts were non-empty and matched current inputs.
- Class (general root): pipeline result lacks atomic proof (audit entries l0029, l0040, l0068, l0089, l0133, l0287, and villa-render-stale-scene).
- Siblings: all pipeline stages that produce or consume persistent artifacts (render driver, lighting measurement, daylight analysis, thermal analysis, Revit spec/extract, deliverables, verify).
- Control tier: tier 1 (prevent by construction) via `src/archpipe/stage_result.py`.
- Control: `stage_result.py` provides an atomic stage-result contract. Every stage writes a result record atomically (`safe_io.save_json`) with input SHA-256 hashes and sizes, code provenance (`compute_code_provenance`), output SHA-256 hashes and sizes, exit status, and completeness evaluation (all expected outputs present and size > 0). Downstream consumers must validate the record via `validate_stage_result()` (verifying status ok, all outputs present/non-empty/unmodified, and all inputs matching current hashes) before consuming outputs. The shared helper `enforce_clean_verdict()` ensures any script whose report says FAIL exits non-zero.
- Migrated in Phase 1: `scripts/compare_lux.py` (lighting measurement), `scripts/check_bedroom.py` (Revit spec/extract verification), `scripts/villa_render.py` (render driver), `scripts/verify.py` (whole-project verification). Remaining stages scheduled for Phase 2: `scripts/villa_daylight_finished.py`, `scripts/thermal_job.py`, `src/archpipe/deliverables.py`, `scripts/run_bedroom.py`.
- Proofs: `tests/test_stage_result.py` (6 tests covering all failure reproductions and quiet cases), `scripts/verify.py` learned guards asserting that `report_has_failure` catches FAIL and `validate_stage_result` refuses modified inputs.
- Registry: `pipeline-result-lacks-atomic-proof` -> `src/archpipe/stage_result.py` (`write_stage_result`, `validate_stage_result`, `enforce_clean_verdict`) -> `tests/test_stage_result.py` and `scripts/verify.py` -> pipeline stage boundaries (render, lighting, Revit check, verify).

### c3-climber-frame-bounds — branch growth crossed the yard boundary
- Observed: the lead's full suite found `landscape-climber-branches-north` outside the modeled yard; the real D1 north branch reached 90 mm beyond its trellis frame toward the neighbour. The west branch also reached 90 mm past its frame and outside the yard. East and south branches stayed in the yard but likewise overran their frames.
- Found by / stage: lead full-suite run at Stage 7; should have been caught when the branch meshes were constructed in the landscape scene.
- Reproduction: `tests.test_landscape.LandscapeGuards.test_each_climber_branch_stays_on_its_yard_side_trellis_frame` freezes the old north and west outside vertices by value and runs on the four real D1 trellises; before the fix it failed all four frame checks, including north.
- Direct cause: the new branch boxes used fixed 90 mm transverse extensions without intersecting them with the supporting frame. Escape: the focused Chunk B tests checked physical parts and frame face counts, while the existing yard test was absent from that focused run. The aesthetic density target also remained from a prior sparse-climber correction without a fresh open-lattice review.
- Class and siblings: growth or dressing built around a wall-mounted support can extend beyond that support and the property boundary. East, south, north and west are the sibling climbers.
- Control tier 1: the branch constructor now intersects every branch box with its own trellis frame bounds before emitting geometry. The renderer's ASSUMED young-planting target is 35 percent face coverage, estimated at about 42 percent after its existing safety margin, so most frame area remains open.
- Proofs: the per-climber regression fires on the old real geometry for all four siblings and stays quiet after clipping; `test_wp2b_landscape_plot_support_setbacks_and_routes` checks the whole yard. `test_young_planting_default_leaves_most_lattice_open` bounds modelled coverage below 50 percent. Visual acceptance still requires lead review of a current preview.
- Registry: `c3-climber-frame-bounds` -> `villa_landscape` branch constructor and `climber_placement.COVERAGE_TARGET` -> `test_landscape` and `test_climber_placement` -> Stage 7 scene construction and render review.

### c3-phase2b-chunk-b — service and dressing proxies in the real D1 scene
- Observed by the lead in fresh 2026-10-01 renders: rectangular black extract ducts appeared below the guest bathroom and dirty-kitchen ceilings; the guest drain read as a 20 mm line. The earlier review also found rectangular storage, planters and trellis, an inward suitcase handle, and an empty black picture frame. These reached Stage 7 visual review; scene export and isolated previews should have caught them.
- Direct cause: the render builder drew the service route at the specified fan elevation as a box, while the specification had no visible valve distinction. The drain directly reused a 20 mm footprint. Generic box geometry also stood in for functional storage and garden components. Escape: the part collector reported geometry defects, but photographic review had not yet integrated the replacements.
- Class and siblings: services drawn as exposed routing, narrowly represented fittings, and furnishing envelopes rendered as complete objects. The guest and kitchen vents, both storage types, both dressing sides, seven door pots, four other pots, two long raised beds and four trellises were checked as siblings.
- Control tier 1: the render shows an ASSUMED 130 mm closed round ceiling valve and omits the uncoordinated concealed duct; the Revit service route and facade grille remain. The Revit drain input now authors an ASSUMED 70 mm grate at the wet-zone edge and supplies the render. Wardrobe rails, storage, suitcases, hollow pots, raised beds and trellis frames now construct physical subparts. The empty frame is omitted until licensed artwork passes C2 intake.
- Tier 2 proof: `test_c3_chunk_b_visible_parts_and_removed_frame` checks declared kinds, closed outward solids, valve height and frame removal on the real D1 scene. The existing Chunk A bath test checks the drain width in both sources and absence of exposed duct meshes. These guards do not judge photographic appearance; the lead view review remains open.
- The first new trellis assertion mistakenly expected more than 50 faces, although five uprights and three rails make 48 six-face solids. Its real-scene run failed 48 versus 50. The corrected test checks at least 48 and relies on `Part` to reject a lone rectangular wall; the clean 48-face member assembly must stay quiet.
- The real `test_nothing_floats` then found 16 unsupported grille subparts after removing the duct. The duct proxy had accidentally connected the blades to the building. A first attempt moved the frame back by 1 mm and still failed: the route endpoint was actually 100 mm beyond the built wall face. The render now derives that face from the built walls, mounts the frame there, and overlaps each blade with the frame. The support regression is the fail-closed check for that dependency.
- A construction review caught a hidden-soil sibling before image integration: the first tapered pot had a closed top cap above its separate soil solid, so Part passed but the soil could never be seen. The shared pot constructor now forms a hollow closed vessel with inner wall and floor, then fills it with a separate tapered soil solid below the rim. The direct helper check and real-scene Part test cover closed geometry; photographic visibility still needs lead review.
- The raised-bed sibling run found nine plants unsupported: their authored bases were at planter-top elevation while the new soil lay 20–30 mm below it. Both pot and long-bed soil now finish 5 mm below the rim, within the pre-existing 12 mm resting tolerance, without moving plants. The same run exposed a count test that treated new rim and soil parts as extra containers; it now counts declared `planter` bodies. A long bed's rectangular soil fill is admitted explicitly as a closed physical volume in `BOX_KINDS`; the Part test still rejects a rectangular pot body.
- Registry: `c3-phase2b-chunk-b` -> `villa_render`, `villa_landscape`, `revit_spec` -> `tests.test_render_standard` Chunk B and bath tests -> Stage 7 scene export and preview.

### villa-render-stale-scene — a passing render checked old geometry
- Observed: lead verification on 2026-10-01 found `out/villa/render-d1/scene.json` had last been written on 2026-09-30 at 11:35. Later C2 gate, C3 light-fitting and C3 bathroom Chunk A runs used that old scene while reporting `qa_passed: true`. The lead's own C3 visual review therefore relied on an image of old geometry. The retained scene file and render/QA records are the evidence.
- Found by / stage: lead review at Stage 7 visual verification; should have been caught at scene export or render entry.
- Reproduction: `tests/test_villa_scene_provenance.py::VillaSceneProvenance.test_historical_unstamped_scene_refuses_before_render` freezes the actual D1 scene's missing provenance by value (D1, 34 views, 915 meshes); `test_real_stale_scene_refused_default_rebuilds_and_hash_is_reported` changes a copied source after export.
- Direct cause: `scripts/villa_render.py` defaulted to an existing scene path and never called `villa_render.write()`; `render_qa` measured the image but had no evidence that its geometry came from current source.
- Escape: the render job identity hashed scene bytes and renderer code, so it prevented reuse of a changed scene but could not detect an unchanged, stale scene. `qa_passed` described image checks only. The review process treated that result as current design verification.
- Contributing factors: scene export was a separate manual step, and neither the scene nor per-view QA named the source revision.
- Class (general root): pipeline result lacks atomic proof of its source inputs; related audit entries `l0029`, `l0040` and `l0068`.
- Siblings: any view, calibration or lighting measurement rendered from an explicit old scene; source changes in the package, asset manifest, plant palette, site, product library or project inputs.
- Control tier: 1, prevent by construction for the default render path; 2, fail closed for explicit scene files at render entry.
- Control: `write()` stamps a content hash of package Python source and scene data, Git HEAD and dirty state, refuses source drift during construction, and replaces the scene file atomically. The driver rebuilds by default, rejects an explicit scene with missing or mismatched provenance, and labels an allowed stale scene `STALE-SCENE` in the result and every view QA record. Both records carry the scene source hash.
- Proofs: the historical D1 scene and a changed source copy are refused with non-zero exit; the default path rewrites and reports the new hash; a changed palette copy triggers the stale label; an unchanged scene is accepted; `test_stale_override_marks_each_qa_record_and_result` checks a per-view QA record. These tests use copied inputs and do not require a workstation render. Existing C2/C3 images remain unverified against current geometry until rerendered.
- Registry: `villa-render-stale-scene` -> `source_provenance`, default `write()` and explicit-scene gate -> `tests/test_villa_scene_provenance.py` -> Stage 7 render entry and QA.

### windows-tempfile-suite-directories — Python test temp dirs denied by sandbox
- Observed: the first final full-suite run exited 1 after 835.1 s with 111 errors in 656 tests. The real `test_concept.GeneratorTests.test_best_variants_pass_structural_checks_and_specs_load` could not write `c.yaml` inside a `tempfile.TemporaryDirectory` under `out/tmp`, then could not remove that directory. `out/perf-suite-final.log` holds the traceback.
- Found by / stage: full regression run; should have been caught by a one-directory write/cleanup preflight before the suite.
- Reproduction: the named real test fails with ordinary Python 3.14 `mkdtemp` under this managed Windows sandbox and passes when the directory is created with `Path.mkdir`.
- Direct cause: Python 3.14 `tempfile.mkdtemp` creates a directory with permissions that this sandbox process cannot subsequently use. Changing `TMP` and `TEMP` between the system temp and `out/tmp` does not fix it.
- Escape: `scripts/verify.py` already avoided this trap with its own directory creation, but the unittest suite still invoked `tempfile.TemporaryDirectory` directly. Class and siblings: test-run setup can make many unrelated tests fail together; 111 errors across concept, guidance and other suites shared the same permission traceback.
- Control tier: 1, construction in the test launcher. `scripts/run_tests.py` sets a writable test root and creates `mkdtemp` directories through `Path.mkdir` within that test process. `CLAUDE.md` names the runner; normal result assessment still uses `NO_COLOR=1` and exit status.
- Proofs: the real concept test passes with the launcher-equivalent temporary directory function, and a file can be written, read and cleaned up. The first runner pass exposed an incomplete import path (`tests` and `scripts` unavailable); adding the repository root to the runner fixed that sibling. With `NO_COLOR=1`, `scripts/run_tests.py` completed 656 tests in 868.6 s wall time (768.4 s unittest time), exit 0, `OK`; evidence `out/perf-suite-supported-final.log`.
- Registry: `windows-tempfile-suite-directories` -> `scripts/run_tests.py` -> real concept test and full discovery -> regression setup.

### repeated-villa-build-work — repeated pure construction made full verification slow
- Observed: lead measured the full suite rising from 1,133 s to 3,937 s and one villa scene build near 360 s. A single profile found 29 camera searches, 185–215 furnishing layouts, 55 Revit spec builds, and 18 furnishing checks. Evidence: the lead's cProfile counts and `out/perf_build.py` reproduction.
- Found by / stage: lead performance review at scene export; should have been caught by a build timing guard during continuous verification.
- Reproduction: `tests/test_build_cache.py::BuildCache::test_full_villa_build_time_budget` runs the full real D1 view set. The pre-fix `HEAD` took 131.1 s without profiling; a historical `e9b89f8` profile took 311.3 s and counted 104 furnishing layouts, 55 Revit spec builds and 3,247 boundary segment builds. The lead's current profile counted 185–215 layouts, 55 spec builds and 6,577 boundary segment builds.
- Direct cause: repeated callers rebuilt the same layout and spec, while each room inset rebuilt envelope segments and camera scoring repeated expensive visibility geometry. Compared with `e9b89f8`, the later guest-shower/spec change added two `F.layout(lay, products=False)` calls inside `_d1_details`; with 55 unchanged spec builds, that can add up to 110 layout calls. The C1 authored-value pass did not remove a cache, C2 intake added a scene build to `verify.py`, and the C3 part boundary and lighting accessor did not create the repeated spec calls. The old product-fit cache covered only `products=True` and keyed only room rectangles.
- Escape: output tests checked correctness but no timing budget or per-build computation count.
- Class and siblings: pure derived geometry recomputed for identical inputs; rendering views, furnishing checks, spec details, room insets and route search. An older product fit cache used only room rectangles as its key, so a changed door or product could reuse a stale fit.
- Control tier: 1, prevent by construction, with a tier 2 timing guard.
- Control: `build_cache.scope` gives one scene build a value-keyed cache and returns independent copies for layout, spec and check results. `villa_furnish` keys accepted product fits on the full layout and product records and reuses immutable envelope segments. `render_views` rejects disjoint wall boxes and pieces before expensive visibility tests and reuses bearings per standing point. No camera score, design value or threshold changed.
- Proofs: scene bytes are identical before/after (SHA-256 `b8ab0ce9221fcd74db20977994dda11432deaf2a73fb117082ca39e1a77bdb83`, 8,490,121 bytes); Revit spec bytes are identical (SHA-256 `b9130b9490b981180defd232773a901600690bb5096669d9115d339c99f7efb2`, 20,065 bytes). Final fresh corrected build 56.0 s; same-interpreter warm build 48.7 s with the identical scene hash. `test_real_layout_and_spec_recompute_after_input_mutation` changes the real D1 lounge rectangle and proves a fresh result, while caller mutations stay isolated. `test_changed_product_record_invalidates_layout` mutates a real selected chair record inside one scope and requires a second layout computation. The 120 s timing test fails the 131.1 s pre-fix case.
- Post-fix profile: 29 view searches in 53.0 s, 53 calls to the furnishing accessor but only two layout computations in 10.5 s, 55 spec accessor calls but one spec computation in 0.1 s, 187 room insets and two boundary segment builds. The 18 furnishing checks and 36 route checks still compute distinct product trials; they were not cached across changed inputs. One profiled build took 103.7 s, versus 56.8 s without profiling.
- Full suite: lead's pre-fix run was 3,937 s; final `NO_COLOR=1` run through the Windows test runner was 868.6 s wall time, 656 tests, exit 0. The earlier unwrapped final run exited 1 with 111 temporary-directory errors and is recorded separately above; its elapsed time is not a passing performance result.
- Test-harness check: the first product-key mutation test counted the nested `products=False` spec layout as a product-mode computation and failed 3 versus 2. The counter now names its intended mode; both modes remain explicitly visible in the full-build count guard.
- Registry: `repeated-villa-build-work` -> `build_cache.scope`, value-keyed derived records and `render_views` prefilters -> `tests/test_build_cache.py` -> Stage 7 scene export and verification.

### c3-proxy-physical-geometry — procedural scene parts lacked a physical boundary
- Observed: the real D1 scene contains rectangular climber masses, rain-head plates, rail and grille proxies, storage boxes and other incomplete solids. The C3 phase 1 scan found 632 failing records among 903 procedural mesh records; per-part evidence and counts are in `docs/c3-phase1-checkpoint.md` and `out/c3-part-failures.json`.
- Found by / stage: lessons audit and render review at Stage 7; should have been caught at the scene builder boundary before preview.
- Reproduction: `tests/test_physical_part.py` freezes the historical climber box, 25 mm garment slab, 28 mm rain-head plate, degenerate triangle, reversed headboard and displaced duvet support case.
- Direct cause: scene mesh helpers accepted arbitrary face lists and bare boxes without a declared physical part type.
- Escape: render checks tested selected geometry and appearance after emission; no common typed constructor checked all mesh append paths.
- Class and siblings: any procedural recognisable object or incomplete solid can pass as a primitive. Audit links: l0046, l0047, l0059, l0069, l0587, l0589, l0686, l0878 and l0923; R3b-7b shower fittings and R3b-8 furniture consume the replacement work.
- Control tier: phase 1 tier 1 constructor and diagnostic collection at emission; strict default and renderer cloth evaluation remain pending phase 2.
- Control and proof: `physical_part.Part` rejects proxy and invalid solids; `PartMeshList` intercepts every authored mesh append/extend. Constructor tests fire on historical shapes and stay quiet on a cabinet carcass and measured glTF basis. The full D1 build exposes siblings. This is a checkpoint, not a closed defect.
- Phase 2a cause correction: id and label inference at the sink itself misclassified the library `BACK` LED strip as a book and concealed door leaves, stair stringers and finish layers in generic assemblies. Every procedural emitter now declares a physical kind; the sink raises on omission even in collection mode. The approved box admissions are written as named kinds with physical reasons. The surface contract checks a declared occupied-side direction, while a glass pane still requires a closed solid. The real scene drops from 632 to 212 failing records; see `docs/c3-phase2a-checkpoint.md` and `out/c3-phase2a-failures.json`.
- Phase 2a geometry siblings: a single-face `disc_down` generator caused repeated open downlight trims and lenses; it now builds closed outward shallow discs. Swing and desk shades and the sloped stair shoe were closed at their shared builders. The exterior ground-ring polygon repeated bridge vertices and generated the zero-area paving triangle; four non-overlapping quads replace it. The current scan has zero zero-area triangles and zero inward-facing light fittings. One inward suitcase handle remains for phase 2b, alongside open shell buckets and recognisable proxies. Focused boundary and landscape tests and `verify.py` pass; workstation preview review remains open. This defect remains a checkpoint, not closed.
- Phase 2b Chunk A: the two rain heads, two hand showers, two fan grilles and the guest drain were recognisable rectangular stand-ins. The emitter accepted boxes for physical objects, while the view intent only named the shower footprint, so a level 24 mm camera could omit the high rain head. The class is bath/ventilation fixtures whose silhouette, openings and view coverage are not represented by their physical function. The builder now uses closed circular sections, nozzle faces, a handset/rail/slider/hose assembly, open grille slots and a slotted drain at the authored position. `render_views.choose` includes bath fittings as view subjects and checks high fittings against the vertical frame; v16 requires 16 mm because the rain head is 28.3 degrees above the best 24 mm eye, beyond its 26.6 degree vertical half-frame. `tests.test_render_standard` checks each emitted kind against `Part` and `tests.test_render_views` checks the 24/16 mm real-case reproduction. The first support regression found that the bracket ends stopped short of the built walls; the bracket builder now derives its endpoint from the nearest wall face and embeds it slightly, so the full real scene returns `unsupported []`. The wet floor remains flat and is labelled with falls pending; this avoids claiming a fabricated gradient. Lead isolated previews and v16/v12/v17 renders are pending, so the visual defect remains open at the Chunk A checkpoint.
- The first render-standard rerun exposed one test-harness sibling: its historical blocked-opening reproduction appended deliberately obsolete meshes to the copied `PartMeshList`, so the new constructor refused them before the opening check ran. That test now converts the copied mesh collection to a plain list for the historical injection, while the production scene remains under `PartMeshList`. The attempted `tests.test_render_contract` module name did not exist; `tests.test_render_standard` is the affected suite. This is a test setup correction, not a production waiver.

### c2-unmeasured-asset-intake — model records could reach scenes without complete measurements
- Observed: the real manifest contains a 19.4689 m jacaranda and a 295.8562 m wide, centimetre-scale sofa; all 62 model entries fail the phase 1 intake schema. Evidence: `docs/asset-intake-phase1.md`.
- Found by / stage: render review and lessons audit at Stage 7; should have been caught at asset ingest before Stage 4 layout or Stage 7 rendering.
- Reproduction: `tests/test_asset_intake.py` freezes the recorded bounds of `jacaranda_tree` and `sf_minotti_sofa` and exercises the missing-front, bedding and licence cases.
- Direct cause: downloaded models were accepted with file bounds but without a complete unit, rights, contents, expected-size and preview record.
- Escape: front-axis and bounds checks covered only parts of the fetch path; scene consumers could read the manifest directly.
- Class and siblings: any external 3D furniture, plant, luminaire or prop can enter a scene before evidence is complete; the related audit entries are l0011, l0014, l0075, l0087, l0094, l0496, l0772, l0943 and l0960.
- Phase 2b review found a second cause: free-text `role` made each asset its own apparent category and the old validator used substring matches for bedding and plants. It escaped because the schema had no vocabulary gate. Siblings included the 50 distinct phrases in the real manifest. Controlled roles, exact role-based contents rules and a retained `use` field prevent that class at authoring and validation; missing role size evidence still fails closed.
- Phase 2c review found a third cause: the generic role screen treated plants as if their landscape species were interchangeable and offered no accountable place for uncited prop envelopes. It escaped because species placement and size evidence were separate, and the validator could only accept a cited range. The siblings are every plant model and the ten approved uncited prop roles. Plant entries now require a species and cited species range; assumptions are limited to those prop roles, require a reason and are counted separately by `verify.py`.
- Phase 2d review found that gating every catalogue candidate made `verify.py` fail even when its incomplete model was never used. `audit_scene_manifest` now derives placed IDs from `villa_render.build()`'s actual `props` and `models`, gates those entries, and reports every unplaced entry with `status: candidate` and its gaps. The importer still validates every imported model. Tests reproduce an incomplete candidate becoming a placed model and still being refused by the importer. A recorded `placed_scale` is checked against every built instance so an asset cannot borrow a compliant placed height while appearing at another scale. A size override requires a dated lead decision, is reported, and suppresses only size-range findings.
- Source evidence added 2026-09-30: [UF/IFAS ENH251/ST092](https://ask.ifas.ufl.edu/st092) gives *Bauhinia variegata* height 20–40 ft and spread 25–35 ft; the manifest tests nursery models against the mature upper limits. [RHS Ursinia anthemoides](https://www.rhs.org.uk/plants/161741/ursinia-anthemoides/details) gives maximum height 0.1–0.5 m and spread 0.1–0.5 m. The placed Ursinia is a multi-plant clump: height follows the species card; width follows measured clump spacing. Heliophila has no verifiable size card, so the west accent keeps its position and one-clump count but uses the blue-flowered *Plumbago auriculata* from the existing palette, supported by its [Missouri Botanical Garden card](https://plantfinder.mobot.org/PlantFinderDetails.aspx?kempercode=a542). The available Heliophila mesh is explicitly labelled a visual look-alike proxy, pending workstation preview review. Plumbago is the palette's direct blue-flowered counterpoint; Duranta is primarily a violet shrub with blue notes and thorns near a path.
- The placed Gazania clump already has a uniform 0.25 m landscape height (native bounds height 0.3987 m); `placed_scale` now records and checks that actual transform against the [Missouri Botanical Garden 0.3048 m ceiling](https://plantfinder.mobot.org/PlantFinderDetails.aspx?taxonid=277558). The glTF file is unavailable locally, so workstation node inspection must still determine whether non-plant geometry inflated the native height. The unidentified Sketchfab sofa is credited as “Minotti-style sofa (unidentified model)”; the lead's dated `size_override` accepts its measured 2.9586 m width and cites the passed layout clearances, while generic unrecorded oversize remains a failure.
- Three numbered indoor Poly Haven models carry no botanical identity. The plant contents record comes from their source descriptions showing integrated pots. The design now specifies *Ficus lyrata* for `potted_plant_01` ([RHS card](https://www.rhs.org.uk/plants/7207/ficus-lyrata/details)), *Syngonium podophyllum* for `potted_plant_02` ([RHS card](https://www.rhs.org.uk/plants/17899/syngonium-podophyllum/details)) and *Haworthiopsis attenuata* for `potted_plant_04` ([RHS card](https://www.rhs.org.uk/plants/504241/haworthiopsis-attenuata/details)), all accessed 2026-09-30. The first two are expressly labelled look-alike proxies, selected for the source model's wavy tree foliage and upright veined foliage respectively; the workstation preview must decide whether the visual match is acceptable. The cards supply species size ceilings; no species identity is claimed for Poly Haven's numbered models.
- Control tier: phase 1 schema plus phase 2a tier 1 fetch and importer registration gates; tier 2 `scripts/verify.py` manifest gate. Phase 2b tier 1 constrains `role` to a vocabulary and preserves descriptive `use`, so arbitrary descriptions cannot create new size categories. `measure_assets.py` re-measures files and writes neutral previews without silently replacing disagreements.
- Proofs: `tests.test_asset_intake` fires on unknown roles, a real sofa outside the held plan range, unregistered entries, invalid licences, wrong built scale and historically oversized bounds; it keeps a garden shrub without a pot quiet, an incomplete unplaced candidate out of the gate, and checks that an indoor plant without one fails. The 23 local files were previously re-measured. Placed records remain red pending workstation intake evidence; see `docs/asset-intake-phase2a-checkpoint.md`. This is a checkpoint, not a closed defect.
- Registry: `c2-unmeasured-asset-intake` -> `require_registered_asset`, fetcher `validate_entry`, `audit_scene_manifest` with built placement and scale, and the `verify.py` placed gate/candidate report -> `tests.test_asset_intake` and `tests.test_landscape` -> ingest, scene import and verification. Client preview review is still pending.

## R3b-1: imported furniture front axis

- Observed: the garden-living Minotti sofa faced backwards in the round-3 render. The lead found it at presentation review; asset ingest and scene export should have caught it.
- Reproduction: the real Minotti has native front +Z, while the old scene exported the layout yaw unchanged. `test_real_minotti_old_yaw_fires_and_corrected_scene_is_quiet` freezes that transform.
- Cause and escape: the manifest recorded bounds and up axis but no front axis; the exporter and importer therefore treated every asset as if its front were already the layout front. Geometric footprint checks could pass a reversed model.
- Class and siblings: directional furniture imported from glTF. The Probber chair has native front -Z; the other placed sofa, dining chair, desk chairs and bed have native +Z. A round rug has no front.
- Tier 1 control: measure the tall back against the low open side at ingest, allow a lead-verified override, record the front axis in the manifest, and compute scene yaw from it. Tier 2 backup: scene validation checks that the resulting yaw maps the native front to the layout front within one degree; Blender import repeats the check.
- Proof: the historical Minotti yaw fails, the corrected scene stays quiet, a deliberately reversed Probber chair fails, and fixed vertex statistics from both real meshes return their measured fronts. The check uses the asset axis and layout yaw without design-specific coordinates.
- Registry: `furniture-front-axis` -> `model_yaw` and `check_model_orientation` -> `tests.test_furniture_models.GuardOnThePlacedScene` -> asset ingest and scene export.

This index records observed behavior and its consequence. It is not a
source of architectural standards. The cited rule catalogue and decision
records remain authoritative for design guidance.

| Area | Observed behavior | Required consequence / evidence |
|---|---|---|
| Revit runner | A relative script path can exit zero without executing; model argument can leave no open document | Absolute paths, explicit document resolution, fresh artifact checks. `extract_model.resolve_doc`, `run_bedroom.run` |
| Revit 2027 | Family symbols load inactive; inactive placement raises; Name property can be ambiguous in IronPython | Activate, regenerate, use `Element.Name.GetValue`. `place_families_test.py`, committed fixture |
| Content | Template contains doors/windows although Libraries count suggests none; third-party categories and declared sizes are unreliable | Verify actual placed dimensions and bind by intent. Never substitute catalogue size for a measured family |
| Geometry | DirectShape rotation is baked; world bounding box is already rotated; family insertion point need not be footprint centre | Carry proxy direction, measured box centre and size. Quarter-turn reversal is exact; arbitrary rotation needs a local footprint. `from_extract.py`, regression tests |
| Review coverage | Dropping unknown chairs/tables makes clearances pass falsely | Keep every measurable piece as an obstacle, even without a published access figure |
| Product furniture bounds (WP4b) | The real Minotti sofa and modern low sofa have native width/depth ratios that the old generic envelopes miss; testing only a swapped footprint rejects a sofa because its neighbours keep their old positions | Normalize each manifest model with one scale, rearrange neighbouring furniture around its measured footprint, then rerun all furnishing checks. The living sofa passes with a 1.10 × 0.45 m table and two measured cane chairs; `test_old_coffee_position_rejects_real_living_sofa_but_relayout_passes` proves the original 0.60 m table placement fails. The 3.29 × 1.62 m lounge sofa still closes the 914 mm route to the pantry after moving its table and armchair, so its procedural fallback records the route failure. Cinema and parents' bed retain explicit client arrangement reasons. Ambiguous chair and rug scales remain explicitly ASSUMED. |
| Furniture orientation (R3b-1) | A glTF asset's front can differ from the plan's front; Minotti native +Z becomes scene -Y and the uncorrected layout yaw faces it backwards | Ingest records a measured or lead-verified front axis; scene export computes and checks the model yaw; importer checks again. `tests.test_furniture_models` freezes measured Minotti and Probber half statistics and tests the historical yaw. |
| Windows verifier temporary directory | Python 3.14 `tempfile.mkdtemp` created a directory under `out/tmp` that the sandbox process could not write into, so `scripts/verify.py` failed before its first fixture | Create a unique directory with `Path.mkdir` under `tempfile.gettempdir()`; the same verifier then ran to `RESULT: ALL PASS`. Keep `TMP` and `TEMP` pointed at `out/tmp` for test runs. |
| Climber mass (WP4b) | A solid magenta box reads as a wall rather than vegetation even when its trellis envelope is correct | Keep the measured envelope, replace its render visibility with seeded leaf and bract polygons, and check count per square metre, 70/30 mix and every centre inside the original bounds in `test_climber_placement`. |
| Accessory relationships | A desk chair occupies its desk's use zone; bedside tables intentionally occupy the bed's head-end zone | Explicit `accessory_to` intent is stored in Revit comments and disclosed in review. Exemption applies only to parent access; physical overlap and unrelated access still fail. It is a design interpretation, not an invented standard |
| Metadata | Falling back to Comments as an identity collides when comments contain shared structured metadata | Reserve `archpipe:` comments for intent; preserve Mark/ApplicationDataId as identity |
| Serialization | Revit `Color` channels are .NET bytes that IronPython's JSON encoder rejects | Convert to Python integers and serialize before opening the output, so failure cannot truncate the last extract |
| Scope | An isolated room is not a dwelling | Report unassessed dwelling rules and preserve their findings separately. Never quietly waive a missing bathroom in a full-house review |
| Native output | PDF export uses `PageOrientationType` and `ZoomType`; displayed headings do not prove a view's actual type | Verify native view types, scale, page count, vector geometry, and markup read-back; inspect pages |
| Native sheet layout | A blank sheet's content was off-centre and its viewport title overlapped the synthetic review note; long titles wrapped over the scale, despite passing vector-count checks | Create a native paper frame, reserve title spacing, use short display titles, and visually inspect exported pages. `revit/export_views.py` |
| Elevation direction | Revit's `ViewDirection` points toward the viewer, as documented in its installed application interface reference; a northward direction shows the south wall | Name interior elevations by the opposite direction and record the actual vector in the view report. Confirm the wall's openings/furniture visually |
| Markup text | Revit TextNote stores carriage-return line breaks and a trailing newline | Compare logical lines, preserving content; verify cloud vertices against chosen coordinates |
| Lighting ownership | Third-party families may override photometry even when writes appear successful | Join explicit spec photometry by model Mark, keep geometry from Revit, report unmatched identities. Never call the join wholly Revit-authored |
| Photometry | Blender IES azimuth differs, finite sphere sizing can wash out a strip light, coarse angular interpolation biases narrow beams | Keep calibrated orientation/size/angle corrections; see [decision 0010](decisions/ADR-0010-photometric-render-calibration.md) |
| Lighting claims | Direct calculations omit shadows and inter-reflection; an empty-room probe is calibration | Label the probe's contents. Do not claim furnished-room uniformity or real-world precision from it. [Decision 0009](decisions/ADR-0009-no-uniformity-verdict-from-direct-light.md) |
| Materials | Revit paint hue can be read; shading colour is not measured reflectance | Carry actual finish names/hues and separately disclose assumed optical values |
| Gates | A script printing FAIL but returning zero cannot gate a pipeline | Assert failed, missing and stale cases as well as passing cases; inspect saved evidence, not shell exit alone |
| Door handling | The current extract lacks actual hinge/facing handedness; the adapter uses the default left hinge | Native views show the authored door. Automated swing checks are provisional until handedness is extracted; do not claim general door-swing certification |
| MCP process input | On Windows with Python 3.14.7 and MCP library 1.30.0, a cached child inherited the live protocol input pipe and hung before creating its run lock; the same command completed directly | Give noninteractive children `stdin=subprocess.DEVNULL`. The real transport regression in `scripts/test_mcp.py --cached-run` verifies matching evidence first and requires a response within 30 seconds. Measured complete test: under two seconds |

## Update procedure

Workstation lessons measured on 2026-09-23:

| Area | Observed behavior | Reusable consequence / evidence |
|---|---|---|
| Probe placement | Three isolated timing trials gave graphics speed ratios of 1.98 for direct light and 7.08 for sixteen bounces; mean illuminance differed by less than 0.001 percent | Use graphics acceleration by default, retain processor comparison. `workstation.py benchmark`, [worker evidence](ops/workstation-jobs.md) |
| Reuse | Three unchanged camera jobs were all reused after unrelated documentation/orchestration changes; a modified cached artifact fails the hash check | Fingerprint job dependencies and actual runtime; verify artifacts, preserve failed attempts. `worker.cached_job`, `tests/test_worker.py` |
| Candidate interpretation | Both negative bed shifts failed design review while the worker batch completed successfully | Report execution success separately from design acceptance; never apply candidate geometry to a saved extract. `worker_entry.py` sweep |
| Portable verification | Installed native Revit family corpus is unavailable on Ubuntu and its transfer was not authorized | Keep live corpus checks on Windows; explicitly report skipped coverage and run synthetic parser cases remotely. `verify.py --portable`, `tests/test_rfa_portable.py` |
| Headless Radiance build | The full CMake build attempted OpenGL targets even with headless mode enabled | Build the twelve required command-line targets from the checksum-pinned official source; record the installed subset. `ops/workstation/bootstrap.py` |
| Worker contention | Render and probe jobs share one graphics processor | Use an operating-system lock across worker processes and bounded processor jobs; benchmark in isolation. `worker.process_lock`, `worker_entry.py` |
| External implementation | Claude Code's actual session identified `claude-sonnet-5`; broad scientific work required substantial research before writing code | Pin and verify the model; provide narrow ownership, bounded effort and existing evidence. The lead retains actual integration checks. [Delegation workflow](ops/delegated-implementation.md) |
| Native fixture geometry | Fine extraction exposed a 1,828.8 mm housing across the west wall and 2,624-triangle light-source display webs below each cylinder pendant | Check actual housing bounds and rotate the long fitting along the wall. Preserve `Light Source` subcategory geometry with an explicit symbolic role and exclude those display webs from physical rendering. `probe_fixture_geometry.py`, extractor, round-trip gate |
| Procedural solids | A closed, consistently connected headboard mesh still had inward-facing triangles because its two-dimensional profile walked clockwise | Test positive signed volume independently of paired edges; reverse the profile before extrusion. `tests/test_furniture.py` caught the error before final acceptance |
| Radiance tool contracts | Portable mocks accepted the wrong output-directory flag and a split format flag; the actual toolchain exposed them | Use absolute per-job `ies2rad -o` prefixes, `RAYPATH` for support files, joined `rtrace -faa`, separate diagnostic output, and actual source/sky checks. `tests/test_radiance.py` |
| Window simulation | An extracted glass solid has front and back faces; giving both a whole-window transmittance applies it twice | Use one planar surface from the actual glazing mesh, keep actual opaque frames, and state the optical assumption. `radiance._glazing_surface` regression |

### Presentation rendering (2026-09-24)

Every row says why the defect was missed, not only what broke. A guard
listed as a check is automatic, and is proven against the real defect.

| Defect | Why it was missed | Guard now in place |
|---|---|---|
| Five render rounds changed samples, textures and HDRI strength, and the images still read as CG | No diagnosis step: symptoms were tuned because nothing asked "what physical cause?" first | Diagnosis order in the `photoreal-render` skill; `render_critic` agent must rule out structural causes before tuning. [ADR-0013](decisions/ADR-0013-presentation-renders.md) |
| No sunlight entered: a refractive glass slab blocks Cycles shadow rays, so sun/sky arrived only as caustics | Nobody checked whether daylight physically reached the floor; brightening the sky hid it | `render_qa` check `glass_passes_daylight`; `photoreal.architectural_glass`; proven with `--qa-break glass` |
| The window looked like a mirror, then showed a void, then a white band | Assumed `Is Camera Ray` stays true through glass (it becomes a transmission ray), and helper ground was hidden from camera rays only | `render_qa` check `window_view` (local detail inside the window's projected rectangle); proven with `--qa-break view` |
| The first `window_view` check passed the void | It used global standard deviation, and a smooth gradient has spread but no content. It had only been tested on synthetic images | Measured metric (void 0.0026 vs garden 0.0365); rule: **prove every guard on a real reproduction** |
| The whole room rendered orange | Blender 4.2 had no display white balance; nothing measured colour cast | Blender 4.5 LTS; `render_qa` check `colour_cast`; `SCENE QA` reports white balance |
| Walls leaned | The camera was pitched down, with no lens shift; nobody inspected verticals | Level camera with `shift_y` (`photoreal.photographic_camera`); `render_qa` check `verticals_level` |
| Pure-red lamp shade and orange door frame | Revit shading colours were treated as finishes and rescaled to 0.35, saturating a channel | `photoreal.FINISHES`; `render_qa` check `cad_colour` for un-overridden saturated materials |
| Ivory bedding rendered grey | One 0.35 "furniture" reflectance was reused for textiles | Per-textile presentation reflectance; `render_qa` check `textile_reflectance` |
| Lights could not be switched off | `float(x or 1.0)` turned an explicit 0 into 1; the same line was repeated in `compare_lux.py` | Explicit `None` checks; `verify.py` falsy-zero lint (`# falsy-ok: reason` where 0 is invalid anyway) |
| The first falsy-zero lint found nothing | Its regex could not match the real line (inner parentheses) | The lint now asserts it matches the historical line before scanning |
| Fixtures rendered as isotropic points | An ad-hoc driver did not remap IES paths, and the fallback only printed a note | `render_qa` check `photometry_bound`; the driver remaps like `worker_entry.py` |
| The duvet slid 0.6 m and hung onto the floor | Cloth was too elastic and unpinned, and a simulation's output was trusted without numbers | Pinned head edge, stiffer cloth, floor collider; `render_qa` check `cloth_plausible` |
| Oak lost its colour after reducing grain contrast | The contrast blend pulled toward a grey of equal luminance, not the photo's mean colour | Blend to the mean linear RGB (reflectance is still exact) |
| Blender 4.5 installed unverified | The checksum file name was wrong, and a missing checksum only warned | Per-release `blender-<ver>.sha256`; a missing checksum refuses unless `BLENDER_ALLOW_UNVERIFIED=1`; `verify.py` asserts it |
| All six props were recorded as downloaded while their folders were empty | The API shape was one level deeper than assumed, and there was no post-condition on files | Raise when a package has no URL; confirm files on disk |
| The glTF viewer showed nothing ("loadfailure") | Exporting lights marked `KHR_lights_punctual` as *required* | Export without lights; the reason is commented in `build_scene.py` |
| Nishita sky units and sun direction were unknown | They were never measured | `calibrate_sky.py`: rotation equals azimuth; x800 scale to lux, measured at three elevations |
| "Free modern bed" candidates were AI-generated meshes with no bedding and no licence | Provenance was not checked before proposing | Check the licence, the generator and the contents before shortlisting an asset |
| The project's agents (`render_critic`, `lighting_reviewer`, and the rest) were unavailable in the working session | Claude Code discovers `.claude/agents` only in the directory it was launched from; this session started in the parent folder | Launch Claude Code from `arch-pipeline/`; otherwise point a general agent at the generated role file. Noted in `docs/HANDOVER.md` |
| The render critic found five defects that every QA check passed | Guards covered only defects already seen, and two pushed the wrong way: a clipping ceiling rewarded flat, milky images | The critic (`render_critic`) reviews every set before the user sees it; tonal checks bound all four sides (`highlight_clipping`, `highlights_present`, `shadows_present`, `exposure_midtones`) |
| Thresholds set on synthetic images were wrong on real renders three times (window detail, colour cast, highlight floor) | Synthetic cases prove the logic, not the calibration | Every threshold records the real measurements it was set from: `render_qa.py` constants |
| A blue lamp-lit night passed `colour_cast` at 0.036 | The check was direction-blind and calibrated only on warm failures | Direction-aware: a lamp-lit night fails any cool cast above 0.02; daylight allows up to 0.05 |
| Lamps rendered far cooler than their 2700 K spec; the night came out blue and was nearly "fixed" by tuning white balance to 4200 K | `kelvin_to_rgb` used Tanner Helland's display-sRGB fit as linear light (2700 K came out as (1, 0.65, 0.34), not (1, 0.39, 0.10)); correcting with the camera hid the spec error | CIE 1931 blackbody in linear Rec.709, unit luminance; `verify.py` checks it against the published Planckian locus (dxy < 0.003). **Rule: fix a lighting spec at its source; never compensate in camera, exposure or look settings.** The camera uses a standard tungsten preset |
| Highlight-priority metering still clipped 4.1% | It assumed every AgX look reaches white at +5 stops | Measured through Blender's own view transform: None +6.5, Medium High Contrast +5.5, High Contrast +4.75 (`AGX_WHITE_STOPS`) |
| Highlight priority then underexposed two views (median 0.18 and 0.23) | There was no floor on overall exposure | `exposure_midtones` (median at least 0.30); protection capped at 0.7 stop; the tonal look falls back automatically instead of being tuned per view |
| Oak grain ran horizontally on wardrobe doors and across the gap between doors | World-space box projection has no notion of a member's length | Per-object grain axis from each piece's longest extent (`presentation._grain_triplanar`) |
| "Dark bronze" rendered pale tan | A stated finish was never checked against its own description | `render_qa` check `finish_matches_name` |
| The garden view was scaled by an HDRI mean dominated by its photographed sun | The mean included the sun | Anchor on the sky mean with the sun excluded (`_sky_luminance`); for overcast and night, one HDRI serves as light and view, scaled to stated lux by integrating the image |
| Curtains looked corrugated, and then still machine-made after cloth simulation | Pleats pinned uniformly survived the simulation; `soft_goods_simulated` proves the process, not the outcome | Irregular gathered heading that relaxes toward the hem. Shape realism is judged by the critic, not by a process flag |
| Light fixtures look like CAD blocks (flat opal disc, crude shades) | Downloaded low-detail Revit families; materials cannot fix geometry | **Open.** Swap the visual housings for detailed models, keeping Revit's position and the IES photometry (as proposed for the bed) |
| The critic claimed a garden darker than sunlit bedding was a defect | Sunlit white bedding (0.70) really is brighter than sunlit foliage (0.15) | Check reviewer claims against physics before turning them into guards |
| Another session edited the same repo concurrently | Broad `git add` would have committed its unfinished work | Stage only your own hunks; confirm with `git diff --cached` before committing |
| Window glass passed 100% of sunlight; the model says 85% | The fix for glass blocking shadow rays over-corrected to "perfectly transparent" with no data | Tv from the model's own material (transparency 85), sqrt(Tv) per face of the slab (the two-face trap already recorded for Radiance). Shown in each image's `caption.json` |
| Every view was metered separately, so a dark corner and a sunlit bed looked equally bright | Per-image auto-exposure optimises each picture and destroys comparability between them | Exposure and look locked across a set, absolute EV recorded; tonal checks become WARN under a lock. Principle: faithful before beautiful (ADR-0013 amendment) |
| Invented dressing and stand-ins were indistinguishable from design content | Nothing labelled what an image's contents were based on | `*.caption.json` per image: from the design, invented, stand-ins, assumptions; `--no-dress` shows the design only |
| `verticals_level` reported a 0 deg pitch for level cameras | The check read `matrix_world` before any scene evaluation; only the metered first view had one | `view_layer.update()` before reading scene state. A check that reads state must force evaluation first |
| "Detailed fixture swap" would have used generic nicer models | Appearance was treated as decoration, not design evidence | Swap only to the specified product (manufacturer family plus its own IES file); a design decision for the client |
| Lamp sources sat 57-466 mm from the fittings' emitters (a drum's light below the drum, a cone's above its shade) | Build, check, lux engine and render all read the family INSERTION height, so they agreed with each other. `check_bedroom` compared the insertion to the spec: circular. The host offset it set was inert for these pendants (offsets -700/-400 both emitted at 2243 mm) | `archpipe.fixture_source` measures the emitter (Light Source symbol apex, else lens). `check_bedroom` compares it to the spec within 25 mm and checks the housing stays below the ceiling; it failed 5/5 on the old model. `build_bedroom` finds the lever by measurement (`Ceiling To B.O. Fixture`) and refuses a placement that would push a fitting through the ceiling. Rule: a check must measure the thing the spec names, not the value the builder wrote |
| Two spec heights were physically impossible for their fittings: LT-01 at 2400 put the cone's shade at 2717 mm through a 2700 ceiling; LT-04 is surface-mounted and emits at 2600 by construction | The spec never said what `mounting_height` measured, and nothing checked a fitting's body against the room | The spec now defines it as emitter height. The builder refuses an impossible placement instead of forcing it. `check_bedroom` checks the housing is below the ceiling, proven in `tests/test_check_bedroom.py` on the real meshes. Resolved as a client decision (LT-01 2233, LT-04 2600) |
| The lamp-source regression test broke when the model was rebuilt correctly | It read the live `out/` extract, so fixing the defect deleted its own reproduction | Reproductions are frozen data: `tests/data/bedroom-fixture-meshes-pre-fix.json`. Live outputs are for checks, never for the regression that proves a guard |
| A photometric file described a different product from its fitting (a 594 x 24 mm strip file on a round drum; a 2-ft strip on a 6-ft linear) | The lux engine reads only the file; nothing compared the file's luminous opening with the modelled lens | `fixture_source.photometry_matches_fitting` (x2 size, x3 shape), reported by `make_render_input`, the MCP tool `check_fixture_sources` and every render caption. Tested on the real meshes, including negative cases. **Open**: LT-02 to LT-05 await the specified products |
| Design dimensions were silently invented when missing (`mounting_height or 2400`, `ceiling_height or 2700`, wall `thickness or 100`, proxy `height or 800`, `default_h`) | The falsy-zero lint asked "does 0 survive?", not "is this value specified?"; its scan also skipped `revit/`, where the 2400 lived | `verify.py` invented-dimension lint over `src/`, `scripts/` and `revit/`, proven on both historical forms (literal and named default). Dimensions are now required; a genuine fallback needs `# default-ok: reason` on the line (two remain, both justified) |
| The detail view was named for "bedside, pendant and pillows" but never framed the pendant (it sat at screen height 2.59, where the frame spans 0 to 1) | A view is a fixed camera over a design that moves, and nothing checked what it showed. I then misreported the cause as the height fix, without checking | `photoreal.VIEW_SUBJECTS` declares each view's design ids; `render_qa` `view_subject:<id>` fails when one is out of frame, proven on the real old framing. Framings are chosen with the projection model, which matched Blender exactly (0.075, 2.591). Claims are checked by projection before they are reported |
| A look retry overwrote the first render; when the retry also failed, the files on disk disagreed with the report and the exposure lock | The retry reused the output name | Retries render under `-retry` and are promoted only if they pass; the records are renamed with them. Proven on the real night door view |
| `colour_cast` could fail a warm lamp-lit night that is physically correct under the tungsten preset | Its only remedy would have been retuning white balance: a guard that pushes toward cheating | A warm lamp-lit cast is advisory (WARN); a daylight cast still fails. Rule: a guard must never have in-camera compensation as its only remedy |
| **Open**: the night door view fails `highlights_present` (p99.5 0.84 against 0.90) after the lamps were moved inside their fittings | The floor was calibrated on renders where lamps outside their shades blasted the ceiling: a guard inherits the defects it was calibrated on | Not lowered and not exposed up. Lamps are not modelled as visible luminous surfaces; the fix is the specified products. The skill now requires re-reading thresholds after an upstream fix |
| Captions did not say the sun came from a placeholder site | The site file's EXAMPLE status was never carried into the image record | Captions record the sun altitude and azimuth, plus the site's latitude, longitude, north angle and `placeholder: true` |

### Luminaire library (2026-09-24)

See [ADR-0014](decisions/ADR-0014-luminaire-library.md) and the `lighting-library` skill.

| Defect or finding | Why it was missed | Guard now in place |
|---|---|---|
| Signify's photometry and Revit file server is `Disallow: /` in robots.txt; bulk download was the obvious plan | The pages and the file server are different hosts with different rules | Read robots.txt and terms for every host before fetching. The catalogue reads only allowed pages; the person downloads files. `signify.fetch` refuses the host; `verify.py` checks the refusal and that no code calls it |
| Signify served a zip labelled `application/json`; Revit type catalogues are UTF-16 with a BOM | Extensions and content types were assumed truthful | `library.sniff` identifies by content (zip, OLE, UTF-16 `##` header, IES, LDT); tested |
| Converted LDT agreed with the manufacturer's IES in flux and peak but differed by up to 34% in single directions | EULUMDAT C0 and IES 0 degrees are different axes; totals cannot show a rotation | IES h = EULUMDAT C + 90, proven on all three Signify lamp sets (within 0.02%). Every imported product with both formats is compared direction by direction; a 90-degree-rotated pair fails the unit test |
| The emitter rule found nothing on a Signify family | Its luminous face is "Glass, White, High Luminance"; the rule looked only for "lens" | `fixture_source.LUMINOUS_WORDS`; the IronPython copies are checked identical by `verify.py`, proven by reverting one copy |
| A headless Revit probe hung on "The parameter Apparent Load doesn't exist in the Family" | Type catalogues raise modal warnings; nothing answered them. The first handler then read a script global after pyRevit tore the scope down | `revit/unattended.py`: dialogs answered and recorded, the store bound at registration; probes run in `try/finally` with a watchdog. The user spotted the dialog |
| IronPython read UTF-16 as '' and died writing a registered sign (0xAE) mid-JSON | IronPython 2.7 text I/O is not Python 3's | Read bytes then decode; escape non-ASCII and serialise before opening the file (the trap `extract_model.py` already recorded) |
| Signify's Revit family says 3200 K and 3 W; its LDT says 3000 K and 23 W | Manufacturer BIM metadata is not checked by anyone | The LDT governs; the build writes its figures onto the family; `install.resolve` refuses a spec that contradicts the product |
| `housing below the ceiling` failed a recessed luminaire (body top 2732 over a 2700 ceiling) | The guard was written for pendants only | Mount-aware: recessed reports the recess depth needed as a coordination NOTE; test uses the measured geometry |
| A unit test exported a synthetic IES into the real product folder, which is deployed to the render worker | The export folder was a global default | `install.resolve(ies_dir=...)` in tests; `verify.py` rejects any product IES not in the library, proven with the real stray file |
| `git check-ignore` showed downloaded manufacturer files would have been committed | `assets/user/` was not ignored | Ignored; manifests carry source and hash instead of the files |
| The catalogue crawl lost 158 of 381 families (41%) and still looked finished | My URL builder dropped `prof/`, so every family listed only on the global site got a real 404; families also listed on a market site were rescued by the fallback, so the failure looked random. I first diagnosed throttling from a curl test that used the *correct* URL, and slowed the crawl for nothing | Key keeps the full path, tested. Coverage (families listed vs read) is stored with the catalogue and `luminaires.py crawl` exits 1 below 95%. Rules: **a scraper reports its coverage, never just its output**; **reproduce with the exact request the program made, not a hand-built equivalent** |
| Swapping to the 4300 lm lamp set over-lit the pillow: 501 lx against a 300-500 lx band | Not a defect: a swap changes results | Every swap re-runs the same requirement and lux gates (`scripts/luminaire_demo.py`, `out/demo/compare.json`) |

### Working practice (2026-09-24)

| Defect | Why it was missed | Guard now in place |
|---|---|---|
| A failing check was read as `exit=0` | The exit status came from `grep` at the end of a pipe | Read a command's own status (`$?` straight after it, or `PIPESTATUS`); never judge a gate through a pipe |
| A scripted edit "applied" but changed nothing after the indentation shifted | A string replacement that matches nothing is silent | Scripted edits assert exactly one match (`assert s.count(old) == 1`), then the changed behaviour is run |
| Windows file lock (`OSError 22`) when replacing an image being viewed, twice: in the render driver, then at the end of a 20-minute pipeline run | The first fix was local to the render driver, so the same error recurred in `run_bedroom.py`'s raw `shutil.copyfile` | Shared `archpipe.safe_io` (temp file plus retried replace) used by every writer of pipeline output; a `verify.py` lint rejects raw `shutil.copy*`, proven on the historical line. Rule: **fix a defect class where it lives, not where it was first seen** |
| A stopped pipeline run left `bedroom-run.lock`, and every later run refused to start | A killed process never runs its `finally`, and the lock recorded a PID that nothing checked | `run_bedroom.py` removes a lock only when its recorded owner is provably not running (`pid_alive`, which never signals: on Windows `os.kill(pid, 0)` would kill the process). A live or unreadable owner still stops the run |
| **Open**: right after a passing run, `run_bedroom --resume` once re-ran the downstream stages (6 s, worker jobs reused) where full reuse was expected; the next call reused fully | Not yet known. The test's pre-check (inputs and artifacts) agreed, so the likely differing key is `worker_runtime`, possibly captured before the run's own asset deployment. **Hypothesis, unverified** | None yet. Next step: record the runtime fingerprint before and after `worker_bedroom` and compare. `test_mcp.py --cached-run` catches the symptom |
| Tests "could not import archpipe" | Windows `PYTHONPATH` separates entries with `;`, not `:` | Use `PYTHONPATH="src;."` on Windows |
| `python` was not found from bash on Windows | The venv is not on the bash PATH | Call `.venv/Scripts/python.exe` explicitly |
| `highlights_present` failed soft overcast light | The rule "a photo has near-white somewhere" is true only with a direct source | Advisory without a sun or lamps (`test_overcast_without_direct_source_may_lack_white`) |

For a new failure, capture the input and expected versus measured result;
separate hypotheses from facts. Add a regression where it can catch the
same failure. Record the version/environment and link the owning code or
fixture here. Change a skill only when the lesson changes how the workflow
should be run. Change an agent role only when its responsibility changes.
Change an MCP tool when the reusable operation or its contract changes.

This is an explicit maintenance loop, not autonomous model training:
observed failure, regression, reusable fix, shared lesson, affected workflow.

For every defect, answer three questions before closing it:
1. **Why was it missed?** Which check did not exist, or which assumption
   went unverified?
2. **Which guard stops it recurring?** Prefer an automatic one: a
   `render_qa` or `verify.py` check, a script post-condition, or a
   regression test. Otherwise use a skill step, an agent instruction or an
   MCP tool.
3. **Does the guard catch the real defect?** Reproduce the defect and watch
   the guard fail. Checks that had only seen synthetic data missed the
   real case twice.

Do not copy bedroom coordinates, permissive example scope, or proxy
fallbacks into universal villa rules. A later real-site result must not
inherit the example's assumptions unnoticed.

## Evidence-aware design gates

Observed: existing rule records name books or general practice without edition-specific passages. Calculation tests validate arithmetic, not the target or its applicability. The new guidance boundary keeps those checks diagnostic and rejects wrong editions, unverified numerical transcriptions, incompatible climate assumptions and qualitative-to-numerical promotion. `tests/test_guidance.py` exercises these failures, the real bedroom obstacle case, source/artifact cache invalidation, project isolation and explicit approval bound to a reviewed content fingerprint. Missing facts and incomplete comfort/structure evidence remain unresolved even for attractive concepts.

Independent pilot critique caught a diagram route crossing a guest block although
the abstract connectivity graph passed. The diagram now reserves an entrance
strip; graph checks alone cannot establish plan geometry. Keep an explicit
diagram/graph comparison in the Order review, and mark incomplete narrative
facts missing or assumed rather than calling a generic pointer a known input.

## Product library and thermal (2026-09-24)

| Observed | Why it was missed | Guard now |
|---|---|---|
| A good texture (Poly Haven brown_leather) failed `maps_complete` | Map roles were guessed from file names (`_diff_`); this asset names its base map `_albedo_` | The source's role label wins (`find_maps(files=...)`); `tests/test_products.py` |
| A good model failed `polycount_match` (10 296 vs 2 548) | The published count's definition (base vs exported, subdivided mesh) is unstated | polycount is `not_checkable` with both numbers; size stays the gate |
| A model genuinely disagrees with its metadata (desk_lamp_arm_01 depth 202 vs 408 mm) | Nothing: the check caught it | Reported as failed, never repaired |
| The thermal hand check failed north by 16 % | It compared TOTAL solar with an isotropic sky; EnergyPlus uses Perez (north sky diffuse −17 %, south +34 %) | The check asserts beam only (within 0.7 %); totals are information; `tests/test_thermal.py` stops the change being reverted |
| EnergyPlus fatal errors returned zeros | A fatal run still leaves an empty SQLite file | `run_case` reads the `.err` log and raises on Fatal |
| Thermal results were 3.6 million times too small | Ladybug already converts joules to kWh | Units are asserted per collection (`kWh`) |

## Knowledge index (2026-09-24)

| Observed | Why it was missed | Guard now |
|---|---|---|
| A file named "Neufert 6th ed. 2023" is the 1980 2nd English edition; "Lighting Design Basics 3rd" is the 1st (2004) | Editions were taken from download filenames | Editions confirmed from each copyright page before citing; `edition_note` records the mismatch |
| Building Construction Illustrated's PDF page labels are sequence numbers (191 where the page prints 5.45) | PDF labels were trusted | Labels chosen from three candidates by agreement with printed edge numbers; < 70 % marked UNRELIABLE; `tests/test_knowledge_index.py` |
| "overheating criteria operative temperature" returned nothing although Lechner covers it | Every word was required on one page | Partial-match fallback |
| The fallback then returned a page for nonsense words | One matching word counted as a hit | At least half the words (min 2); the negative test caught it |
| A book sent to the workstation arrived as 0 bytes, and the RAG system quarantined it as "unreadable PDF" | A piped ssh transfer failed silently | Copies are checked by sha256 on both ends before ingest |
| Every scp copy failed with "No such file" | Shell-quoting the remote path: modern scp (SFTP) takes the path literally, so the quotes became part of the name | Pass the remote path unquoted to scp and quoted to ssh; verify sha256 on both ends |

## Concept generator: the critic caught one defect, the drawing caught two (2026-09-25)

**Defect 1: a room too narrow for a door.**
- Generator v1 sized rooms at area ÷ band depth. A 6 m² bath in a 5 m band came out 1.2 m wide, and no door fits on 1.2 m of corridor wall.
- It was missed because the generator placed no door-width constraint.
- **Guard:** the critic caught it through `reachability` and `links_built`. The bath had no door and could not be reached. The generator now has a minimum run (`MIN_RUN` 1.8 m).

**Defect 2: circulation area and stretched rooms were invisible to the checks.**
- Only a look at the plan PNGs showed them:
  - the L and U corridors were long;
  - one U room was stretched to 54 m² against 6 m²;
  - the U's east arm was a stub;
  - an L upper floor overhung the ground floor.
- Every check reported pass or advisory.
- **Guards:**
  - `circulation_area` reports achieved against the schedule allowance;
  - `area_match` now fails a room more than 25 % off its schedule;
  - `upper_supported` fails upper rooms with no ground room beneath.
- Tests: `tests/test_concept.py`, with positive and negative cases.

**Lesson:** read the generated drawings before trusting a clean check table.


## Real-plan calibration: seeded-defect recall exposed extraction bugs (2026-09-25)

**Calibration runs** (critic checks against CubiCasa5k, `scripts/cubicasa_calibrate.py`, pre-registered):
- **Run 1** failed the 90 % gate (75.7 %). The images showed flaws in the check definitions:
  - open-plan kitchen alcoves borrow the living room's daylight;
  - garages and plant rooms have their own outside doors.
- **Run 2** used amended checks on fresh plans. It passed, but seeded-defect recall fell, which exposed two parser bugs:
  - a doorway is a gap in the wall, so it was read as an open-plan connection;
  - balcony doors were read as entrances.

**Guard:** recall on seeded defects is reported next to the quiet rate. A rising quiet rate with falling recall means the checks got more lenient, not more accurate.

**Final run** (fresh plans 601–900):
- window passed;
- reachability failed (87.3 %), because doors inside thick walls are not matched to rooms. It stays not calibrated.

**Lesson:** never re-score the sample used to design a fix. Every amendment is judged on untouched plans.

## Adding documents to the workstation corpus (2026-09-25)

`app.ingest_local` stages files and then runs `app.ingest`, which runs `app.parse_phase` from a temporary folder holding a per-run `config.yaml`.
- Setting `RAG_CONFIG` overrides that per-run config. The parse phase then loses the document IDs and falls back to an arXiv query, which currently returns HTTP 406.
- A relative `PYTHONPATH=.` also breaks in that temporary folder.

**Working command:**
```
cd ~/ai-projects/archpipe-knowledge-data && PYTHONPATH=$HOME/ai-projects/research-system-rag \
  ~/miniconda3/envs/agent-rag-research/bin/python -m app.ingest --paper-ids-file drop_in/<manifest>.txt
```
Use `app.ingest_local` for new drops, run the same way. The run on 2026-09-25 added TM59, AD G and AECOM: 35 documents, 20,345 points.

## Test fixtures with hand arithmetic fail like wrong rules (2026-09-25)

**What happened.** Twice in one session a new test failed because its fixture was wrong, not the rule:
- SAN-01: the fixture put a bedroom on the entrance storey, which made the expected WC mandatory;
- FURN-02: the bed position was hand-computed, and the "failing" case actually left 850 mm on one side.

Both were caught only because the failure was diagnosed before any code changed. The risk is "fixing" a correct rule, or loosening a test, to match a wrong fixture.

**Guard** (`tests/test_bed_clearance.py` is the pattern):
- build fixtures from the quantities under test (left gap, right gap, foot gap), not from coordinates;
- take sizes from the object the rule reads (`catalogue.CATALOGUE[...]`);
- assert the fixture's own geometry before calling the rule;
- test exactly at the threshold (750 passes, 740 fails).

**Practice:** when a new test fails, check the fixture's arithmetic first, then the rule.

**Third instance** (DOOR-02 test, same day): I expected contact where the leaf tip reaches the obstacle edge (83.6°). The leaf actually meets the obstacle's near corner first (71.6°), and the rule was right. The practice caught it before any code changed. The fixture docstring now states the geometry it relies on.

## IFC export: a 1000x unit error, and a wrong diagnosis of the checker (2026-09-25)

**The unit error.**
- IfcOpenShell's `geometry.add_*_representation` helpers take SI metres and convert them to project units. Passing millimetres made every wall and space 1,000 times too large.
- The counts (walls, openings, spaces) were all correct, so a count check could not see it.
- **Guard:** `tests/test_deliverables.py` reads the written file back through the geometry engine and compares every space and wall with the spec, to within 0.5 mm. It was proven to fail with the bug reinstated (a 10,004,499 mm wall against 10,004 mm).

**The wrong diagnosis.**
- The first read-back returned no vertices, and I concluded the Windows Python 3.14 geometry build was broken.
- The real cause: `create_shape(...).geometry.verts` read inline frees the shape before the buffer is copied, so it returned nothing or garbage.
- Keeping the shape in a variable fixed it. A second environment (the workstation) exposed the cause.
- **Lesson:** a "broken library" diagnosis needs a minimal reproduction that does not share my own code's pattern.

## Reading a real Revit 2021 model in 2027: two serialisation failures after a 17-minute upgrade (2026-09-25)

- Opening `omar.rvt` (Revit 2021) in 2027 upgrades it for ~17 minutes on every run. Both first runs then died at the very end, writing JSON:
  1. Arabic text in names broke IronPython's `json.dumps` (UnicodeDecodeError);
  2. in 2027, `ElementId.Value` is a .NET Int64, which the IronPython json encoder rejects (`1586207L is not JSON serializable`).
- Why missed: the extractor had only ever read models we authored ourselves, with ASCII names and in 2027-native files.
- **Guards:** `revit/probe_villa_inventory.py` saves the upgraded copy (`ARCHPIPE_SAVE_UPGRADED`, new file only) BEFORE any serialisation, so a late failure no longer costs another upgrade; `_clean()` coerces strings to unicode and any non-Python number through float/int before writing.
- **Lesson:** in a slow session, persist the expensive result first, then do the fragile work.
- The original's SHA-256 is recorded in `out/villa/original-sha256-before.txt` and re-checked after each run.

## Building the villa environment in Revit 2027: two API traps (2026-09-25)

1. **`ElementId(int)` is ambiguous in 2027 under IronPython.** It fails with "Multiple targets could match:
   ElementId(BuiltInParameter), ElementId(BuiltInCategory), ElementId(Int64)".
   - **Guard:** `build_villa_env._eid()` passes `System.Int64`.
2. **Mass-category DirectShapes are hidden in views by default.** The first 3D export showed the neighbours' windows
   floating in the air with no buildings. The read-back check still passed, because bounding boxes exist whether or
   not a view shows them.
   - **Guard:** context volumes use Generic Models.
   - **Lesson:** a geometric read-back proves the model, not the picture, so look at every exported view before
     showing it.

The checker `scripts/villa_env.py check` has its own negative tests in `tests/test_villa_env.py`. They cover
azimuth, a fence height, a missing slab, a column span and a level elevation.

## A stair modelled as one room hid a blocked foot (2026-09-25, found by the client)

- **What happened.** In villa concept A (round 2) the straight flight along the party wall had its basement foot at
  the street end. Only the flex room and the laundry touched that end, so the bottom step could be reached only
  through a room.
- **Why every check passed.** The critic treated the stair as a single room linked to the hall along its long side.
  The graph said "reachable", and nothing asked where a person actually steps on and off.
- **Guard.** The `stair_access` check in `src/archpipe/concept/villa.py`:
  - every stair room declares its `ends` (the foot on the lower storey, the arrival on the upper);
  - each end must open onto a circulation room;
  - a stair without declared ends fails.
  - `tests/test_villa_concepts.py::StairAccess.test_round2_defect_is_caught` rebuilds the real round-2 geometry and
    proves the graph alone passes it while the new check fails it.
- **Also:** the plans now draw UP/DN arrows at the stair ends, so a reviewer sees the route.
- **Lesson.** Check a stair by its two ends, not as a room. And read the client's own sketches before choosing a
  direction: the villa_01 docx sketch had the flight rising from the basement hall toward the street end.

## The stair was never built in 3D, and the model already said where it belonged (2026-09-25, client review r3)

**What was wrong** (Revit ids from `out/villa/omar-2027.rvt`; CAD `01-GROUND_FLOOR_PLAN.dwg`):
1. **Stairs existed only as 2D rectangles**, so nothing was ever checked against the structure we must keep.
2. **The round-3 straight flight ran into column 1590377.** Its top treads and headroom (x 3.82-3.98, y -28.47 to
   -28.16) hit the GF column and its basement copy 1614989, and the assumed front and party-wall beams. Revit's
   intersection filter confirmed all four.
3. **The street strip is an outdoor terrace**, not floor:
   - its street and east walls are 900 mm parapets;
   - it is reached through the 68"x80" sliding door in the living room's front wall.
   Rounds 1-3 put a study, then the GF stair landing, on it.
4. **The old stair bay was ignored.** The DWG marks the built stair opening (layer A-DETL, x 7.377-9.387,
   y -26.721 to -23.771), and the old PDF has a U-stair there with 280 mm goings. Revit's floors carry no opening,
   and the environment build deleted those floors, so the checked model no longer showed it.
5. **The dog-leg variant assumed a clear 2.2 m bay.** The facade columns project 0.51 m, leaving 1.85 m between
   their faces.

**Guards:**
- `src/archpipe/concept/stairs.py` models each stair as treads, landings and a 2.0 m headroom envelope, and
  clash-checks them against the columns on all storeys and the beams.
- The critic's `stair_structure` check fails a layout whose stair clashes.
  `tests/test_villa_concepts.py::StairStructure::test_round3_flight_hits_column_1590377` rebuilds the real round-3
  geometry.
- `revit/build_villa_stairs.py` builds the same solids in a copy of the environment model and runs Revit's
  `ElementIntersectsSolidFilter`. `scripts/villa_stairs.py compare` shows the two checks agree.
- The critic no longer allows rooms on the terrace (the GF envelope excludes it), and a test asserts it.

**Lesson.** A plan rectangle is not a stair. Before showing a stair, build it in 3D against the kept structure and
read the existing model's marks (openings, parapet heights) before the old sheets.

## Revit image exports: dark canvas, missing tag text, far-off level lines (2026-09-26)

- **Dark canvas.** Revit 2027 exports plan and 3D images on the dark UI canvas, and setting
  `Application.BackgroundColor` did not change it.
- **Tag text.** Room tags were created but did not show in the exports.
- **Level lines.** The surroundings 3D view carried level lines far outside the model, shrinking the model to a
  corner.

**Guards (in `scripts/villa_option_pdfs.py` and `revit/build_villa_option.py`):**
- Plan images: the background turns white and the white linework turns dark.
- 3D images: only the background changes. Recolouring bright pixels in 3D blackened the white wall surfaces; the
  first composed page showed it and was redone.
- Room names are placed from the known crop box (109.5 px/m), with Revit's own room areas from the read-back.
- Levels are hidden in 3D views, and the images are cropped to their drawn content.

**Independent check.** Revit's room areas agree with the concept tool's net areas (flex room 12.17 m² against 12.4;
kitchen 16.66 against 16.6).

## Extension blocks built against each other counted their joints as windows (2026-09-26, round 7)

The round-7 rooms under the ramp and deck are contiguous blocks from the street gate to the deck end.
`villa.window_faces` added each block's two end faces as external window faces, so the joint between the store
and the laundry (x 5.377), the laundry and the WC, and so on counted as windows. A closed habitable room placed
there would have passed `window` with no daylight at all. It was missed because every earlier extension block
(S5) stood alone in the yard, so no end face ever touched another block. Guard: faces shared by two blocks are
dropped; `test_villa_parking.Negative.test_a_closed_windowless_room_still_fails_window` failed on the real P1
layout before the fix and passes after it. The same pass removed the store's side on the client's kept 1.40 m
NE yard wall as a window face (`YardWall.test_store_side_on_the_wall_is_not_a_window`).

## Walls came through the ramp, and a 2.1 m door opened under a 1.9 m soffit (2026-09-26, client review r7)

Two model errors the client found in the round-7 PDFs; I had reviewed the same 3D pages and missed both.

1. **Walls through the ramp and deck.** `revit_spec` clipped wall heights under the ramp with a guard meant to spare
   the villa's east face (`min(y) < YE + 0.05: skip`). Every cross wall of the rooms under the ramp *starts* on
   that face, so every one was skipped and built 2.8 m tall, 0.5-1.35 m through the ramp and deck. The wall along
   the fence took the lowest clear height (1.45 m) over its whole length, leaving 850 mm open under the deck.
2. **A door taller than the room it opens into.** Doors were put at the middle of the shared wall with whatever
   leaf the template had; nothing compared a door head with the clear height where it stands. The lounge door to
   the store under the ramp sat where the clear height is 1.91 m.

Why it was missed: new element types (a sloping ramp, a deck) were added without a geometric post-condition
against what they touch, and my check of the built model was a look at the images. A look is not a check.

Guards: `revit_spec.clearance_problems` (walls above the soffit, gaps under it, door leaf + frame vs clear
height), run on the spec (elevation-check row, `tests/test_villa_parking.UnderRampFit`) **and on Revit's read-back**
(the builder now reads back every wall top and every door's type size; the checks page has a BUILT row). Proven
on the real as-built specs: 8 problems in P1/P3, 9 in P2/P4, before the fix; 0 after. Doors under the ramp are
placed by `villa_parking.door_fit` (slid to the high end, leaf sized: full 2.10, reduced to >= 2.0 for rooms,
cupboard height for stores, else the check fails), and the builder makes exact-size door types instead of the
nearest stock type.

Rule going forward: any new element that bounds a space (slab, ramp, deck, beam, infill) gets a clearance
post-condition against its neighbours, checked on the Revit read-back, before a PDF goes out.

## Smaller catches in the same session (2026-09-26)

- **A section drawn mirrored.** My drawn section across the NE yard wall put east on the right while looking
  from the street toward the villa; facing +x, east (+y) is on the LEFT, as Revit's own export showed. I had
  labelled Revit's (correct) image as mirrored. Guard: the drawn section and Revit's export sit side by side in
  the PDF, same direction; derive left/right from the view direction, never assume.
- **A locked model crashed the batch build.** `os.remove` on an option model the client had open in Revit killed
  the run after P2 and left an old read-back. The builder now saves beside a locked file (`-v2`) and says so.
- **A wall position assumed as fact.** The NE yard wall's thickness and side were labelled ASSUMED and sent for
  confirmation before building on them; the client corrected the side (flush with the villa face, not the
  column face). Keep asking before an assumption drives geometry.

## Round 8 catches: guards that disagreed with each other (2026-09-26)

Five defects in one round; each was caught by a second, independent check disagreeing with the first.

1. **A stair touching a column that Python passed.** The lengthwise U's half landing started at x 3977, the CAD
   face of column 1590377. Revit holds that column face at 3977.2; the Python clash test counts an overlap only
   above 1 mm, so it passed, and Revit's intersection filter (`scripts/villa_stairs.py compare`) flagged it.
   Landing moved 20 mm clear. Guard: `tests/test_villa_parking.RevitStairCompare` requires every stair an option
   uses to be in the Revit comparison and the comparison to agree; the checks page no longer claims "Revit
   agrees" for a stair that was never compared (`villa.REVIT_STAIR_COMPARED`).
2. **Doors and windows through columns.** Openings were centred on the shared wall with no knowledge of the kept
   columns: the S4/P3/P4 GF entrance and basement pantry doors ran into column 1590377, a ramp door into the
   column at x 7.0, and a window on a column would have passed too. Present since S4. Guard:
   `revit_spec.opening_problems` on the spec and on Revit's read-back (checks page BUILT row); openings are placed
   in column-free runs (`_clear_columns`), doors under the ramp in the highest column-free run.
3. **A window credited but not built.** The critic took the kitchen's 1.5 m east face as a window; a column split it
   into two 0.5 m pieces and the spec dropped the window, so the checks said lit and the model had no window.
   Guard: the critic's window faces now subtract the columns (`villa._minus_columns`), and
   `revit_spec.window_credit_problems` compares the critic's credit with the windows Revit built (read-back);
   `WindowCredit.test_the_real_false_credit_is_caught` reproduces the real case. Dropped openings are listed on
   the checks page. A seeded test had assumed the hall's 1.30 m street face could hold a window; the column
   leaves 0.69 m, so the fixture was wrong, not the rule.
4. **Checks rows hard-wired to one stair.** The stair rows always measured the old U (`u_in_old_bay`), so the new
   stairs' pages showed the old U's slab opening. Guard: rows use `villa.stair_model(lay['stair'])`.
5. **Rounding under a threshold, and an id collision.** `X_LOW` rounded to x 3.124 where the clear height is
   1.999 m (the laundry "at 2.0 m" was 1 mm short): now rounded up to the mm and verified. A new GF room reused the
   id `landing-gf` and silently replaced the straight stair's landing, breaking three checks at once: layout
   builders must not reuse ids (caught by the critic's entrances/stair_access/suite checks).

## The daylight study found the generator under-glazing every room (2026-09-26)

The first whole-building daylight run put kids bedroom A at 0.47 % ADF even in S1, with no deck in front of it.
Cause: the spec sized a window as its facade run minus 0.4 m each side (`L - 0.8`), a margin meant for the room's
corners; after round 8 the runs were already cut clear of the columns with their own 0.1 m margin, so the margin
counted twice. The bedroom got a 0.63 m window and its second run's window (0.39 m) was dropped. Every option was
under-glazed, which would have blamed the architecture for the generator's default. Now `revit_spec.REVEAL = 0.2`
m each side; S1's kids bedroom A reads 1.24 % (two windows, 1.03 + 0.79 m).
Why missed: no check tied window size to anything but a plausible default; nothing read daylight until now.
Guard: the whole-building daylight study (archpipe.daylight, validated) now runs on every option, and its results
table sits next to the SLL cards; a window rule that starves rooms shows as a column of red.
Also caught while building it: a glazed opening drawn as two coincident panes would square the transmittance
(`test_window_is_one_glass_pane_and_leaves_a_hole`); an opening that lands on no wall would silently become wall
(`VillaScene.test_every_opening_lands_on_exactly_one_wall`); `villa_env.py check` ignored the read-back path it
was given (now `--readback`); a PDF open in the viewer crashed the writer (now `safe_io.writable_path`).

## Climate daylight, and a JSON fix that only a real model could test (2026-09-26)

- **The JSON fix passed its unit test and failed on the client's model.** Cleaning values (Arabic text, .NET
  Int64) was not enough: the model holds text in U+0080-U+00FF (Arabic stored as mis-decoded bytes, e.g. 0xD8), and
  IronPython's own json string escaper tries to re-decode that as UTF-8 and throws. The unit test only exercised
  CPython. Guard: `revit/jsonsafe.py` now writes JSON itself (ASCII, every non-ASCII char escaped; byte-identical
  to json.dumps for ASCII data, tested), the extractor prints a full traceback on failure (the runner showed only
  the message), and the proof is running the extractor on `omar-2027.rvt` itself. Lesson: a serialisation fix for
  IronPython is proven only under IronPython, on the data that failed.
- **`solar.sun_position` takes UTC and ignores tzinfo.** Passing Cairo local time with a tzinfo gave the sun at 81 deg
  at 09:30. The docstring says UTC; the parameter accepts an aware datetime silently. Caught by plausibility.
- **Two pieces of the build tree were macOS binaries.** The Radiance source tarball ships prebuilt Mach-O tools in
  `ray/src/*`; copying them gave "Exec format error". The Linux build is `cmake-build/bin` (built the daylight-
  coefficient tools there: gendaymtx, rcontrib, rfluxmtx, dctimestep, rmtxop, all 6.0.1).
- **Climate-based daylight validated before use:** sky orientation (a vertical sensor facing the sun gets > 2x the one
  facing away, pre-registered; measured 3.7-7x) and daylight coefficients vs direct rtrace under the same gendaylit
  sky (pre-registered 20 %; measured 11.6 % and 2.1 %).
- **A camera that sees a wall.** One render spot (S1 view 1) faced a partition 1 m away because S1's rooms sit
  differently; comparable views need a spot open in every layout (view 5, down the basement's length).

## Windows chosen by the room behind them, not by the face (client r8 review, 2026-09-26)

- **The extension's end had a 0.8 m high-sill window (P1/P3) or none (P2/P4); the street door was capped at 2.4 m.**
  The generator decided a window by the room's occupancy: a utility got 0.8 x 0.8 at sill 1.5, a store got nothing,
  living rooms a garden door capped at 2.4 m. The client reads the facade, not the room list: the basement's street
  face is floor to beam today, and the extension's end is the only face it has onto the garden.
  Why missed: every check asked "does the room have a window" (window_credit_problems), none asked "is this face
  glazed as intended". Guard: `revit_spec.full_height_faces` (street face + every extension end) and
  `glazing_problems`, a post-condition on the spec and on Revit's read-back (PDF row "BUILT: street face and
  extension end glazed floor to beam"); proven on the real round-7 read-back (P1, P2, P3 all caught; quiet on P1's
  street door, which already fills its run). The dirty kitchen now always sits at the end
  (`test_the_dirty_kitchen_is_the_last_room_of_the_extension`).
- **The Revit window read-back echoed the spec.** Windows were placed as the nearest stock type by width only, at
  the family's stock height, and the read-back copied the spec's width and sill, so a guard on the read-back could
  never see a wrong window. Now `build_villa_option.sized_door(..., what="window")` duplicates an exact-size type and
  the read-back reports the type's width/height and the instance's sill as built. Lesson: a read-back that copies
  its input is not a read-back; check each field's source.

## Stair headroom from the tread tops, and a pinch round the void (client r9, 2026-09-26)

- **Headroom was measured from the wrong line, under the wrong soffit.** AD K Diagram 1.3 (card
  ukadk-stair-headroom-min) measures 2.0 m above the PITCH line; our envelope started at each tread top, which is
  up to one rise lower at the back of the tread. And the GF slab zone was taken as -200..0 (slab only), ignoring the
  0.10 floor build-up: the soffit is at -300. Together they sized the slab opening to x 8.537, which leaves 1.82 m.
  Why missed: the envelope boxes WERE the check, so the generator and the check shared the error. Guards:
  `stairs.straight` slices the envelope to the pitch line, `stairs.SLAB_SOFFIT` (tested equal to FLOOR_BUILDUP +
  SLAB), and `stairs.pitch_headroom`, an independent sampled check shown as an elevation row; proven on the
  round-8 opening (1824 mm, `test_the_round8_opening_is_caught`). The opening now runs to x 8.887 (2045 mm).
- **The way from the stair top to the bedrooms was 0.69 m where it turned round the void.** Every room passed its
  own width check; nothing measured the route between rooms. Guard: `villa.gf_route_width` rasterises the open
  floor (void + balustrade and half partitions removed) and finds the widest body that gets from the landing to the
  corridor's end; row "GF route from the stair top to the bedrooms" against card ukadm-hall-min-m42. Round-8 plan:
  0.59 m (0.25 m once the void was right); now 0.91 m, kids A's wall moved to void + 1.0 m and the kids rooms kept
  at 11.5 m2 by narrowing the family bath (1.82 m). The old S4 plan reads 0.21 m (superseded, not rebuilt).
- **r9 follow-ups.** A door beside a corner landed on both walls of the corner in the daylight scene (the parking
  pass rebuilds doors without their `span`, so the direction test could not see it): each opening now goes to its
  nearest wall only (`villa_daylight._owners`); `scene().openings` spec == placed for every case. An alcove of a room
  (`part_of`, the lounge under the stair's top landing) is sized, lit and glazed with its room, so the street window
  runs column to column (3.41 m) instead of stopping at a utility wall. Occupied rooms under the ramp (the cinema)
  get a ceiling row: 2.3 m over 75 % of the floor (card mh-dwelling-ceiling-min), proven failing when the room is
  pushed toward the gate.

## Furnishing D1: three checker gaps found by their own negative tests (2026-09-27)

- **A 20 mm grid lost every shared room edge.** The furnished-route raster filled rooms with strict inequalities;
  on a 20 mm grid the cell centres fell exactly on the edges between rooms, so every open-plan join became a wall
  and nothing was reachable (a 0.5 m body failed). Guard: half-open fills; `test_the_route_check_really_examines_rooms`.
- **The body was rounded down.** 914 mm on a 50 mm grid became a 900 mm body, so a 909 mm gap between two beds
  passed. Guard: 20 mm grid, body rounded UP (never kinder than the card); the same test reproduces the first
  draft's 0.909 m gap.
- **A corner is not a side.** A body grazing the last centimetre of a bed's foot counted as reaching the bedside;
  nodes are now the middle of the side (`_middle`). Seats facing a table are reached from the front or a side.
- **The seating card assumed no traffic.** The island's seated side first faced the cook's aisle and passed on
  the 813 mm no-traffic card. NKBA 2nd ed. (held) gives 1118 mm where people walk past behind the diners; the
  stools now face the tall wall with 1.31 m behind them (cards nkba-seating-walk-past-1118 / -edge-past-914;
  `test_stools_need_room_to_walk_past`).
- Also carded from the held originals: NKBA landing areas (sink, hob, fridge), seating width, and AD M Diagram 2.4
  zone 'a' (bedside furniture within 600 mm of the bed head).
- **Stair flight counted as floor; slivers counted as reached.** Adding stair ends and the principal bedroom's
  window (AD M Diagram 2.4 note 1) as route nodes, the negative test (a console at the stair foot) still passed:
  the raster let the body stand on the flight, and a 9 mm overlap counted as reaching a node. Guards: the
  basement flight, the GF opening and voids are not floor; a node needs up to 0.1 m of real overlap
  (`test_stair_foot_must_stay_reachable`, `test_principal_bedroom_window_must_stay_reachable`). The dining table
  is also checked extended to 2.8 m (`extended_table`).

## Re-furnishing D1 for the questionnaire and the bigger dressing (2026-09-27)

- **Furniture was placed against room outlines, i.e. inside the walls.** Room rects run to wall centre lines (or
  the outer face on the envelope), so pieces "against a wall" sat 50-200 mm inside it and every check passed.
  Guards: `clear_rect` for authoring; the checks take the spec's real walls (`_walls`, cut at doors) as obstacles
  (inside_room fails a piece overlapping a wall).
- **Pinned doors were re-centred.** `_clear_columns` moved a door placed with `door_at`; pinned doors now move only
  if they hit a column. The critic's `min_area` fix overwrote `w`/`d` (min_width read 1.0); now `a_net`.
- **A door can run into the wall across it.** The bedroom->dressing door at x 22.10 ran 153 mm into the 0.2 m
  south wall (clear 0.75 m), and `_walls` cut *every* wall at a door gap, perpendicular ones too, so the clash was
  also invisible to the route raster. The new guard then found three more: the ensuite door 26 mm into its wall,
  the deck slider 25 mm into the study partition (centred between column faces, but the partition stands 50 mm
  proud), and a false one, because a door with no `span` defaulted to "h" (the cinema door was never cut from its
  wall). Guards: the doors check measures each opening against the walls (`test_a_door_running_into_a_wall_is_caught`,
  proven at 153 mm on the real position); `_door_axis`; walls cut only parallel to a door
  (`test_a_door_without_a_span_is_cut_from_its_own_wall`). Fixed: DRESSING_DOOR_X 21.847, ENSUITE_DOOR_X 21.65,
  STUDY_DOOR to the partition face.
- **The principal-bedroom window guard switched itself off.** It keyed on `bed_king`; the client's queen bed is
  `bed_double`, so no window node existed and the check passed silently. Now keyed on the room (PRINCIPAL_BEDROOM);
  `test_the_window_guard_follows_the_room_not_the_bed_type`. Its strip also started on the wall's line: a 0.2 m
  external wall swallowed it; it now starts at the inner face.
- **A pocket door gave no route node.** Route nodes came from swing zones, and a pocket door has none, so the
  parents' cluster started its route at a piece of furniture and never checked the way in. Nodes now come from
  approach strips at every door (`_door_approaches`); `test_the_parents_entry_must_stay_passable`. This exposed
  real pinches, fixed in the design: the queen bed's foot had exactly 0.750 m (PARENTS_BED_DEPTH 3.00 -> 3.05:
  0.80 m), kids B's bed corner to wardrobe corner 0.75 m (bed 0.1 m north), the ensuite approach 0.82 m (rail
  0.1 m shorter), the lounge sofa end to the pantry (sofa 0.12 m east: 1.10 m).
- **The square body failed corners the path turns.** Supersedes "body rounded UP" above: the body is now a DISC of
  the path width with exact distances to obstacles (no grid rounding at all). A path's width is measured across
  the direction of travel; a square of the same side sweeps outside that width at a turn (the dressing: rail end
  and column 1.24 m apart on the diagonal, legs 1.05/0.94 m, refused). Negative kept:
  `test_the_body_turns_a_corner_the_path_turns` refuses a straight 0.90 m aisle; all earlier negatives still fail.
- Messages now state the width checked (750 in bedrooms, card ukadm-bedroom-route-750; 914 elsewhere).

## D1 furniture in Revit (Phase 2, 2026-09-27)

### D1 round-2 native detail payload (2026-09-28)

- **The option spec listed approved details that the Revit builder ignored.** Doors, windows and furniture had a build path, while `hatches`, `pocket_buildouts`, `balustrades`, `bath_fittings` and `ventilation` did not. `villa_furnish_build.py spec` now includes `round2_elements`, derived from those fields; `build_villa_option.py` creates a Walls-category pocket buildout, a native wall Opening and tagged detail solids. `villa_furnish3d.round2_postcondition` checks measured world boxes, categories, the host wall, the 1.2 m door, suite door, study windows and structural columns. `tests/test_d1_wp5.py` moves the real-spec hatch, shortens the door, removes a grille, moves a glass panel and raises a study sill to prove the guard fails.
- **A placeholder size is not structural design.** The stair spec leaves laminated-glass thickness `null`. The native detail payload uses a 20 mm representation and writes `ASSUMED` in Comments; the lead must replace it after structural sizing. Fitting and ventilation proxy sizes are likewise labelled. The option spec still has no lighting fixture records, so corrected fitting heights in `villa_lighting` cannot be reconciled by this Revit option build.
- **The first open-side glass extrusion projected outside the stair room.** Its nosing line is the room edge; adding thickness toward positive y put the entire 20 mm panel into the adjacent room. The payload now puts that thickness inside `stair-b`; the room check and `test_glass_panel_outside_stair_room_fails` catch the old direction.

- **A run's modules overran the run.** Building the dirty kitchen in 3D, its modules added up to 3.64 m on a 3.60 m
  run; the 2D plan drew them and the landing check measured them without noticing. Guard: the kitchen check
  requires modules to fill their run to 1 mm (`test_modules_must_fill_their_run`, proven on the real 3.64 m).
- Post-condition PRE-REGISTERED before the first build (`villa_furnish3d.TOL`): each Mark built once, every face of
  its box within 5 mm, category exact (bound by intent), and every furniture check re-run on the as-built
  footprints. First build: 65/65 elements, PASS. Negatives: 10 mm off, missing/doubled, wrong category, a
  wardrobe built 0.5 m out (`tests/test_villa_furnish3d.py`).

## D1 lighting, products and the villa renderer (Phases 3-4, 2026-09-27)

- **Function and beauty, both carded.** Function: 24 IES HB10 Table 33.2 rows (maintained lux, 25-65 column) read
  on the held original, each a card with its row as the regression needle. Beauty: pendant 762 mm over a table
  (Residential Interior Design Fig. 4.9), vanity sconces 914-1016 mm apart, accent aimed ~30 deg (Lighting Design
  Basics p. 62). The client's rule (flush downlights for ambient; pendants/spots only for task and centrepieces) is
  a test (`tests/test_villa_lighting.py`).
- **First drafts failed their own checks, and that was the point.** Sconces alone gave 87-142 lx on the basin
  counters (300 needed): sconces light faces (Ev), not counters (Eh); a task downlight in front of each mirror was
  added (`test_basins_lit_only_by_sconces_fail_grooming` reproduces the draft). The island middle, tall-wall
  counters, dirty kitchen run and kids' desks were also short and fixed in the design, not the check.
- **A fitting was labelled with the wrong room.** A dining fill placed across an open-plan join kept the room it was
  authored for; fittings are now labelled by the room that contains them (`test_recessed_fittings_sit_in_their_room_clear_of_columns`).
- **Manufacturer data: parse, never repair.** iGuzzini LDTs write 'ww/3000' for the CCT: the parser now reads one
  Kelvin value beside a label (two values stay None). The number regex matched a bare '.'. Underscore ST49 and the
  Laser Evo wall washer fail our LDT/IES pair check (59.8 %, 100 %) and are not pickable; their positions use generic
  or a stated substitute, named in every caption. Product pages are fetched within robots.txt (iguzzini.com Allow /;
  the asset API host has no robots.txt); the configurator's LDT buttons were used in the browser as a person would.
- **Git Bash rewrote '/en/...' CLI arguments into 'C:/Program Files/Git/en/...'.** Set MSYS_NO_PATHCONV=1 for any
  URL-path argument.
- **A render job resumed a stale result.** The driver's job id hashed the scene and IES files but not the renderer,
  so a calibration after a renderer change returned the previous run's files. The renderer's code is now part of
  the identity.
- **Blender exited 0 after a Python exception**, so a crashed render reported success with no images: the driver
  now runs Blender with `--python-exit-code 1`. The crash: the shell's walls-with-openings are keyhole polygons that
  revisit a vertex; faces are now built with a fresh vertex for a repeat.
- Calibrations measured on the workstation: IES downlight 167.25 lx vs 172.75 analytic (3.2 %); an 800 lm emissive
  opal sphere 9.71 lx vs 9.79 analytic (0.8 %). Exposure presets were pre-registered before the first render.

## D1 continuation audit (2026-09-27)

- The final render driver stopped on a 30-second SSH polling timeout. Its surrounding shell
  still returned success because its last command appended `EXIT 1` to a log. The workstation
  finished all fourteen 1024-sample images. Re-running the identical content-addressed command
  retrieved them without rendering again. Five images fail image checks; execution is not acceptance.
- The villa renderer reintroduced indirect-light clamping at 10 in calibrated lumen units,
  despite `build_scene.configure_render` documenting why this discards interior reflected light.
  It also left diffuse bounce limits at Blender defaults. The villa configuration now disables
  direct and indirect clamping and explicitly sets the bounce limits. Regression:
  `test_calibrated_transport_does_not_discard_bounced_light`. The real old configuration fails
  this test. This is a configuration fix, not yet a measured improvement: the planned three-view
  comparison was blocked by SSH connection permission failures. Exposure and fixture powers
  have not been changed. Do not claim corrected renders until that comparison and review run.

## D1 authenticity pass (client: "authentic to the daylight and lighting ... what the villa would look like after construction", 2026-09-27)

- **A document was taken as the client's brief without the client owning it.** villa_01_guidelines.docx set
  4000 K for the kitchen and dressing; the client: "I have never specified that specifically". It is now ADVISORY
  (client decision): sound targets adopted, all 47 measured and reported by `villa_brief.check`, none enforced;
  withdrawn targets carry the client's words; `test_no_4000k_source_anywhere`. Why missed: the lighting design
  consulted the published cards but not the project brief file at all; now the brief check runs with the design.
- **An in-scene lux measurement read 0 lx on every surface.** Its sensor camera sat 25 mm above the sensor with
  Blender's default 100 mm near clip, so it saw the inside of the worktop. Once fixed, the measurement agrees with the
  analytic direct calculation (island 1473 vs 1419 lx) and found three real design faults the analytic check cannot
  see: reading spots tilted off the pillows (135 lx, now 1141), a desk lamp enclosed by its own shade, and a reading
  spot INSIDE a perimeter beam (1 lx). Guards: `beam_clashes` + `test_no_fitting_in_a_beam` (proven on the real
  position), step markers only below the beam soffit.
- **Glass verified:** a single-sheet window transmits 0.700 (stated 0.70), a closed slab 0.850 (stated 0.85); the
  probe is part of --calibrate.
- **Unclamped transport brightens the images, physically.** Removing the indirect clamp made every room brighter;
  the measurement's total/direct ratios (1.07-1.3 in lit rooms) are ordinary inter-reflection, so the earlier dark
  images were the defect, not the new ones. Exposure stays pre-registered.
- **The render and the daylight analysis now describe one building:** `scripts/villa_daylight_finished.py` puts the
  render's faces and reflectances into the validated Radiance method (living ADF 4.1 -> 5.0 with the chosen finishes;
  grid points under furniture read the shade beneath it).
- Soft goods: duvets are cloth draped onto the beds' own parts (photoreal._simulate, unchanged); furniture and
  sanitaryware are declared procedural stand-ins in every caption.

### D1 renders, client review of draft 8 (2026-09-27)

- **The parents' bed rendered head-to-foot.** The generator rotation map swapped 0 and 180 against the generator's
  own docstring; its tall headboard stood at the foot and the duvet draped over it ("duvet flying on the end").
  Missed because nothing compared the generated piece with the plan's orientation. Guard:
  `test_generated_pieces_face_the_way_the_plan_says` (headboard and bedside drawers vs the plan's own parts; fails on
  the old map with the real pb-bed).
- **Duvets stood out stiffly past the foot in every bedroom.** The villa cut stopped 20 mm past the foot, where the
  bedroom standard hangs 0.30 m over the foot and sides, and the sheet started from the plan's h, not the generated
  mattress top. Guard: `test_duvet_cut_hangs_like_the_bedroom` (fails on the old cut: foot overhang 0.02).
- **Stone and wood read pink.** Textures were mean-matched in luminance only, so each photo kept its own chroma
  (Marble014 G/R 0.87, B/R 0.69 against the stated cream 0.95 / 0.86); the floor tinted every bounce. Measured on the
  linear EXR before changing anything: the wall in v13 was redder than a 2700 K source on 0.80 plaster, so the cast
  was in the scene, not the camera. Fix: per-channel mean-matching to the stated base colour at the stated
  reflectance (ADR-0013 part 7). No white-balance change: that would have hidden a real cause.
- **Forcing 24 mm on cameras framed for 16-20 mm cut the rooms.** The views guard checked only subject centres.
  Guard: every footprint corner must be in frame. Cameras now stand where a photographer would (`frame`: same room
  or its door opening, 0.30 m off walls, door leaf hidden for that view only); where 24 mm still cannot hold the
  subjects, 16 mm by client decision, with the measured angle recorded and checked.
- **1,780 zero-area triangles refused the whole draft on the workstation.** Corner radius equal to half a loft ring
  made neighbouring arcs share end points. Guards: radii clamped below half; `test_scene_passes_the_render_contract`
  runs the contract locally.
- **A lighting negative test depended on test order.** `villa_render.build()` binds the real products into
  `villa_lighting` for the process; with them the ensuite basin reaches 526 lx from its sconces alone. The first-draft
  reproductions now pin the generic photometry per test.
- **Open item, not fixed in the render:** the basement stair treads stand 50 mm (east) to 200 mm (west) off the party
  wall in the spec, with no stringer; the render shows the model as it is. To be resolved in the Revit
  reconciliation (a design question, not a render one).
- **Floating objects, found by a new guard, not by eye** (`archpipe.concept.render_support.unsupported`,
  `test_nothing_floats`, proven by `test_the_float_guard_catches_the_real_defects` on the real draft-9 lamp and
  marker): desk-lamp shades bracketed to the window glass (now table lamps on their desks); stair step markers 70 mm
  off the party wall (set from the tread edge; the treads stop short of the wall); 11 downlights 100 mm below the
  cove rooms' slab field and 3 under the ramp 155 mm below the slab (the lighting design assumes one ceiling height
  per room, and the parking model's ramp differs from the rendered ramp); 3 stair-void pendant cords ending at 2.70 m
  in a double-height void; corridor path markers 21 mm proud; a vertical sconce 30 mm off its wall. All now seat on
  the surface actually rendered (`_seat_recessed_on_soffit`, wall-marker snap, sconce bracket), recorded in the scene
  notes for the Revit reconciliation. Lux must be re-measured in the scene after these moves.
- **How the guard itself was wrong four times before it was right** (each caught by proving it on a real defect):
  a merged mesh (every door handle in one object) had a house-sized bounding box that "touched" everything -> split
  meshes into connected parts; bounding boxes of wall triangles around a window span the glass, and a fan over a
  KEYHOLE polygon covers the opening -> ear-clipping and an exact triangle-box (separating-axis) test; sampled
  points straddled a door leaf at exactly the tolerance -> exact overlap, not samples; a lamp arm "rested" on its own
  shade while the shade hung from the arm -> only building surfaces ground a group, pieces only join groups.

### D1 renders, client punch list (2026-09-28)

- **The parents' entrance was closed by a render-only detail.** The slatted headboard panel ran 0.6 m past the bed
  each way, across the doorless entry opening and the dressing door. The furnished-plan route check could not see
  it (it checks layout pieces, not render details). Guard: `render_support.blocked_openings` (doors: any piece;
  doorless passages 0.6-1.6 m: render details and hanging fixtures, which the route check cannot see);
  `test_openings_passable` reproduces the old pendant and door. It also found a real LAYOUT defect the Gate A checks
  missed: the parents' bedside table stood 0.23 m into the dressing door (clear 0.67 of 0.90 m), and a bedside
  pendant hung at 1.15 m in the entry passage.
- **A Codex fix cut an exterior wall; rejected.** Centring the 0.8 m dressing door at 22.05 put its leaf 53 mm into
  the 0.2 m east wall and Codex added a recessed jamb reveal. The lead's arithmetic had used the room edge, not the
  wall's inner face. Final: door centred 21.897 (100 mm return), bedside 0.35 m. Also corrected: the code comment
  and ADR attributed the lead's door decision to the client; the route waiver it implies is pending, not accepted.
- **A Codex pass removed every photographed normal map**, reasoning that tangent normals have no UV basis on
  box-projected meshes; the renderer already had `triplanar_normal` for exactly that. Restored for stone, paving and
  wood; fabrics keep the subtle weave bump. Reduced wood grain contrast is a finish CHOICE (a calm, low-figure
  veneer) and is now labelled as such in the material notes, not presented as physics.
- **Study windows: an inherited privacy rule overridden by the client.** The 1.7 m sill came from the ramp/deck
  privacy adjustment in `revit_spec._parking`; ADR-0014 records the client's big low-sill windows. Daylight, glare
  and privacy must be re-evaluated.
- **Hand-typed cameras went stale and some looked the wrong way.** Interior views are now declared by intent (room +
  subjects) and placed by `render_views.choose` (standing points 0.30 m off walls, 0.15 m off furniture or in a
  door opening; score = subjects wholly in frame, then how much of the room's design shows, depth, windows).
  Two slips found on the way: a point ON a room's edge was classed "inside" (its door stayed shut with the camera in
  the leaf) -> strictly-inside test; a basement camera "opened" the ground-floor door above it -> same-storey match.
  Where no point holds the subjects even at 16 mm, the build stops (the dirty-kitchen run and fridge face each
  other: the view's subject became the run).
- **Stair**: open risers kept; steel stringers, bearings, open-side balustrade and handrails added as ASSUMED
  construction details (for the Revit model). **Kitchens**: microwave, coffee machine, hoods and a dirty-kitchen
  fridge as ASSUMED appliances; the fridge replaced a cleaning column whose storage moved under the folding counter.
- **Plants were placed without asking where a person would put one**: the bedroom plant stood in the vanity chair's
  way, the study plant in front of the new low window. Moved to corners; no guard yet beyond float/openings.
- **The view chooser's first scoring picked uninformative frames** (render critic on draft 11, checked by the lead):
  the parents' view stood at the entry facing the windows (headboard out of frame); the dressing view was 60 % a
  wardrobe end panel 0.68 m from the lens. Terms added to `render_views.choose`: stand on the main subject's front
  side, penalise a piece within 0.8 m of the lens and in view, penalise subjects behind a wall in plan; the frame
  constraint weighted so no bonus can outvote it. Guards: `tests/test_render_views.py` -- facing and looming FAIL on
  the old scoring (proven); the wall-occlusion test did NOT fail on the old scoring (the family-bath camera had plan
  line of sight to the WC), so it is not yet proven on a real case, and the critic's "WC not visible" has another
  cause, still to be found on the next render.
- **An automated critic's claims are leads, not findings.** The Sonnet render critic was right about the bath
  tap, ladder, pillows, hood, coffee machine, mirrors, boxy sofas, framing and the six omitted QA checks (each
  confirmed in code); it recommended brightening the cinema and lounge, which would contradict the locked-exposure,
  no-enhancement rule; not done.
- **Final renders, first pass (2026-09-28).** The driver reported a finished 24-view job as "stopped without status":
  it read the status file just before the shell wrote it, then saw the process gone. Fix: re-read status before
  declaring the job dead (the identical re-run resumed and fetched the results, as designed). The first final pass
  also showed what drafts had skipped: exteriors by day on the interiors' exposure lock were blown out (own locked
  state `exterior-day` now); a windowless corridor by day with lights off was black (lamps on, lamp white
  balance); a street camera at garden level looked at the underside of the ground; from the street and the front
  yard only the boundary wall and the ramp enclosure showed, so the street elevation is deferred until the site
  frontage is modelled. Final-only views need at least one draft before the final set.
- **A render-side fix is not a design fix.** The fixture seating moved 14 fittings in the render only; the lighting
  spec (and so Revit) still put them 100-155 mm below the ceiling. Source fix: `villa_lighting` reads the finished
  ceiling (cove field, extension roof); the render's seating is now a check that must move nothing (test proven
  on the old heights). Root cause of the ramp gap: the parking model's deck clearance was extended under the
  extension roof, which the spec builds at ground-floor level.
- **A specified tint must be checked in the image.** The grey-green exterior (G/R 1.06) read warm grey under the
  sun in the finals; at 1.14 the sunlit facade samples G > R > B. **A published explanation must be measured**: the
  v04 window flag was first explained as "a plain neighbouring wall"; a ray-cast showed the villa's own boundary
  wall, then open sky (no context modelled there).
- **Landscape trees were placed at their CC0 asset's native size, checked only against a trunk setback.**
  `villa_landscape.TREES` placed a jacaranda (measured on ai-workstation from the glTF POSITION accessors,
  ops/workstation/library-manifest.json `bounds_m`: 19.3 m tall, ~24 x 19 m canopy) at scale 1.0, 18.30 m from the
  north facade -- inside the 1.5 m trunk-setback rule, since the RULE only ever checked the trunk POINT.
  The canopy, never measured, put jacaranda foliage through the parents' bedroom and the garden-living ceiling
  (draft renders v01/v02/v05/v07/v17). Missed because: (1) no prop-size data existed anywhere in the repo -- Codex
  had no workstation access to measure a glTF, and the lead's own figures were hand-copied from an ssh session, not
  checked in; (2) `villa_landscape.facade_distance`/`inside_yard` operated on the TRUNK coordinate only, with no
  concept of a prop's world-space extent. Fix: `ops/workstation/library-manifest.json` now carries a `bounds_m`
  (native glTF Y-up world AABB, node-hierarchy-aware -- naively unioning every accessor's own min/max silently
  missed that some Poly Haven packs, e.g. `shrub_02` and `searsia_lucida`, hold several complete plant variants as
  separate offset root nodes; the union must walk the node TRS chain) for every landscape (and, cheaply, every
  other) prop; `ops/workstation/fetch_asset_library.py` measures and drift-checks it going forward.
  `villa_landscape.prop_world_box` reproduces `villa_scene.import_props`' glTF-Yup-to-Blender-Zup convention
  (scene xyz = gltf x, -z, y; verified against a real headless Blender 4.2.9 `import_scene.gltf` of `tree_small_02`
  and `shrub_02`, matching to < 1e-4 m) and `extent_violations` checks the FULL scaled/rotated/translated box, not
  a point, against the building footprint (a) and the yard polygon by perimeter sampling, not just 4 corners (b) --
  the yard is L-shaped, and a corner-only test can miss a bite its re-entrant corner takes from a wide canopy.
  Height is now an explicitly labelled ASSUMPTION (3.5-4.5 m per tree; no cited mature-height figure for the
  requested olive, Olea europaea, is held in knowledge/library.json) rather than the CC0 stand-in's raw mesh size.
  Guard: `tests/test_landscape.py` freezes the real D1 draft placement and proves `extent_violations` fails on it
  and passes on the corrected `TREES`/planting tables; four planting props (searsia, one grass, the rooibos, one
  shrub) also needed a smaller scale once their true multi-variant bounds were known, not a moved point.
- **Wood grain rotated into a Box-projected texture reads as a smeared streak, not a rotated grain.** Client:
  stair tread wood (v11-stair-void.png) and the ensuite vanity front (v12-ensuite.png) both showed long streaks,
  "annoyingly fake". Cause, confirmed against a real Blender 4.2.9 import on ai-workstation: `villa_scene
  .add_material` redirects a material's `grain_axis` by ROTATING the Object coordinate fed into a Box-projected
  `ShaderNodeTexImage`, but Blender's Box projection reads which PAIR of that vector's three components a face
  samples from the face's own UNROTATED geometric normal -- rotating the coordinate does not rotate that pairing,
  so a rotation can point one of the two sampled components at the face's own normal axis (which never varies
  across that face), collapsing it to a single texel row/column. Missed because no guard checked a material's
  `grain_axis` against the actual shape of the mesh it was assigned to, and the codebase's own existing workaround
  (`"walnut-grain-x"`/`"oak-grain-x"`, identity rotation, already used for "horizontal tops and shelves") was never
  applied to the stair treads (`villa_render.py` hardcoded plain `"walnut"`) or the washbasin/vanity front
  (`part_material`, same). New bpy-free module `archpipe/blender/grain.py` (`mapping_rotated_span`) reproduces the
  rotation and the per-face-normal axis pairing (matching `villa_scene.triplanar_normal`'s own convention) in pure
  Python, so it is unit-tested without a Blender runtime. Fix: stair treads now use a new `"walnut-grain-y"`
  (proven non-degenerate on the tread's Z-normal top face, and grains along its own 900 mm length, not its 280 mm
  depth); the vanity front now uses the existing `"walnut-grain-x"` (identity rotation -- proven non-degenerate
  regardless of which wall, and so which world axis, the panel's thin dimension ends up on, unlike `"walnut"`
  itself, which only degenerates for SOME wall orientations, which is why only some walnut surfaces show the
  defect). Guard: `tests/test_render_standard.py::WoodGrainMapping` reproduces the real collapse on the tread and
  on a vanity-front orientation, and proves the fix is non-degenerate. Not fully closed: an attempted visual
  (rendered-pixel) confirmation on ai-workstation was inconclusive -- real wood grain photos are intrinsically
  anisotropic, so a simple per-axis variance comparison cannot distinguish "correctly oriented grain" from "a
  collapsed axis" by itself; the geometric proof above does not depend on that measurement. Visually confirm on
  the next real render.
  Visually confirmed 2026-09-28 by the lead (second D1 round-2 draft, v11-stair-void.png): tread grain now runs along the tread.
- **The prop-extent guard only knew the GF storey, so the north planting bed stood inside the dirty kitchen.**
  Second round-2 draft, v17-dirty-kitchen.png: shrubs filled the basement dirty kitchen and showed through the new
  kitchen hatch (v01). Cause: the garden is at basement level, and the yard polygon's north strip runs over the
  basement store-ramp, cinema, guest WC and dirty kitchen; `extent_violations` checked only the GF rectangles
  (FRONT/BAR/BUMP), so a bed at x 13.0-14.05 inside the dirty kitchen (x 11.2-15.41) passed both tests. Missed
  because the first guard was proven only on the tree defect it was written for. Guard: `garden_level_rooms(lay)`
  feeds every level-B room to `extent_violations` and to the bed check in `build`;
  `tests/test_landscape.py::test_guard_fails_on_the_real_north_bed_inside_the_dirty_kitchen` shows the GF-only
  guard passing the real draft searsia and the room-aware guard failing it. The bed moved to the open strip
  east of the dirty kitchen.
- **A view subject can outlive the thing it names.** v07 kept the subject "terrace lounge set" after the
  landscape replaced that set, so the renderer matched no object and QA reported the subject out of frame.
  Guard: `tests/test_render_views.py::test_every_view_subject_matches_scene_content` mirrors
  `villa_scene.subjects`' matching over every view of the real scene.
- **A landscape change must close the route, roof edge and planting checks together.** The D1
  2026-09-29 artificial-grass rebuild removed the teak lounge, but the first scene export still
  failed `scripts/villa_render_views.py`: its terrace subject resolver required the old
  `landscape-sofa-` mesh prefix. The new bistro table retains that identifier as a documented
  view alias while its label and geometry identify the bistro. `tests/test_landscape.py` now
  freezes the old oversized tree and dirty-kitchen shrub, a sofa footprint across the garden
  approach, a plant at 0.3 times its maintained spread, a chair in the egg swing envelope,
  and a planter on the deck rail line; each violation has a passing placed-layout control.
  Run `villa_render.write()`, `scripts/villa_render_views.py`, both render-support guards,
  unittest discovery and `scripts/verify.py` after changing a garden prop. The Poly Haven
  `outdoor_table_chair_set_01` is absent from the checked manifest, so the bistro is a
  dimensioned assumed proxy until that asset is indexed and measured.
- **An asset stand-in's native size is a claim to check, not a default.** Codex placed CC0 trees without a
  workstation to see them; the first render showed the error. The lead must render or measure every new asset
  before trusting a guard that reasons about it.
- **The dirty-kitchen duct floated beside its hood.** Round-2 critic pass on the drafts (v17): the extract duct hung
  at x 13.30 while the hood chimney (over dk-run's hob) stands at x 13.827. The spec's fan position was typed in
  rather than derived from the hob, and the float guard passed it because the duct touches the external wall.
  Guard: `tests/test_d1_wp1.py::test_dirty_kitchen_duct_rises_from_the_hood_chimney` (the old x fails it). The
  same critic pass showed the fridge/oven bank in no view; v17 now names it as a subject. Critic claims were
  checked against scene data first: the hatch, pocket door, wall handrail, hand shower and library glass all
  exist, and those "missing" findings were misreadings of the drafts.
- **The stair's wall handrail was buried in the plaster.** Round-2 finals (v11): only the rail's brackets showed.
  The stair details take `wall_y` = -28.671 (the party-wall line), but the finished plaster beside the flight is
  at -28.471; the rail was offset 60-90 mm from the party-wall line, so it sat 0.11-0.14 m inside the wall. This is
  the same class as the dirty-kitchen chimney (room rect or structural line taken for the finished face). Guard:
  `tests/test_render_standard.py::BuriedFixtures` finds shell faces on the room side of a fixture within its span,
  and fails on the real old rail. The critic had called the rail missing; the scene data showed it existed and
  was hidden, so the fix is placement, not a new mesh.
- **A Revit wall Opening has no Mark or Comments, and the tag writer skipped them silently.** D1F round-2 build:
  the hatch Opening was built exactly (x 11.80-13.10, sill 1.0, head 2.1, correct host wall) but the
  post-condition reported "opening built 0 times", because `stamp()` finds no Mark parameter and writes nothing,
  and Revit 2027 names the category "Rectangular Straight Wall Opening". The synthetic read-back fixture had
  assumed a Mark. Now the builder records `spec_id` and logs the missing tag, and the check accepts the real
  category. Guard: `tests/test_d1_wp5.py::test_real_revit_opening_has_no_mark_and_is_matched_by_spec_id`, built
  from the real read-back shape.
- **A Codex job dispatched from the wrong directory could not write the repo.** Round-3 WP2 ran with the session
  sitting in the plans folder, so its only writable root was that folder; it worked on a copy and returned a
  patch. Guard: dispatch Codex only from the repo directory, and every Codex prompt now starts "verify you can
  write inside the repo; if not, stop and report".
- **A per-point recomputation made the lighting check 110x slower and the suite 4.2 hours long.** Round-3
  `villa_lighting.check` rebuilt the open-plan cluster (`villa_furnish._cluster`) for every fixture at every grid
  point (334k calls, 171 of 180 s). Fixed by computing each room's cluster once (1.6 s). Missed because no test
  bounds a check's run time; the suite's own duration (483 s vs 15,018 s) was the only signal.
- **A climbing plant was drawn as an 80 mm magenta box floating 0.30 m above the ground** (round-3 WP3); the float
  guard caught the lift, and the box itself is replaced by a realistic climber in the renderer (WP4).
- **The bougainvillea climbers were replaced by scattered leaf/bract polygons (WP4) but stayed sparse enough to
  read as "almost invisible"** (round-3 lead review, v01/v02/v24). `build_climbers` hardcoded `density=120`
  with no coverage target; nobody had checked what fraction of the trellis face that density actually covered.
  Missed because `test_climber_placement.py` only checked point counts and envelope containment, never coverage.
  Fixed by giving `climber_placement.py` an explicit 2D-Poisson coverage model (`coverage_estimate`,
  `density_for_coverage`) and having `villa_scene.build_climbers` call `density_for_coverage(target=0.80)`
  instead of a bare number. Guard: `test_old_density_fails_80_percent_coverage_on_real_envelope` reproduces the
  old default failing 80% on the REAL east-trellis envelope from `villa_landscape.py` (not a synthetic box), and
  `test_render_density_covers_the_real_east_trellis_envelope` proves the fix clears it on that same envelope.
  The four wall-trellis mass boxes were widened from 3-8 cm to 12 cm deep; the renderer clips each instance
  to that envelope. The regression also checks the east mass depth. This records the earlier sparse-planting
  correction; `c3-climber-frame-bounds` above supersedes its 80 percent target for the client's open lattice.
- **`artificial-grass` rendered as a flat, untextured mint-green plane** (round-3 lead review). Cause: the
  MATERIALS dict entry had no `asset` key, so `villa_scene.add_material`'s photo-texture branch
  (`if asset and kind in ("principled", "translucent")`) never ran and the court got a bare Principled BSDF
  colour. Every other "flat" finish in the file (paving, gravel, lawn) already carries an `asset`; grass alone
  did not, and nothing checked for that. Fixed by adding a real CC0 texture (ambientCG Grass002, verified to
  exist via `ambientcg.com/view?id=Grass002` before adding it -- distinct from the Grass004 set already used
  for the garden lawn) to the manifest and the MATERIALS entry, mapped at a 1.0 m tile.
  Guard: `ArtificialGrassGuard` asserts the material has an `asset` key that is a real manifest entry, and
  reproduces the old flat dict to show it fails that check.
- **The island/stair-void pendant globes read as "smoky grey glass", not glowing white opal** (round-3 lead
  review, v01-stair-void.png). Cause: the shell used `kind="glass"` (a rough, roughness=0.35, refractive
  Principled-BSDF dielectric). A rough glass BSDF has no bulk scattering: at most viewing angles it mostly
  REFLECTS the room (grey) and only shows the interior bulb through narrow refraction cones, and it also picked
  up `photoreal.architectural_glass()`'s shadow/diffuse-ray transparent mix, written for window panes, not a
  lamp shade. Fixed by switching to `kind="translucent"` (Principled diffuse + Translucent BSDF mix, already
  implemented in `add_material` for the curtains) -- a milky white diffuse body that also passes the inner
  bulb's light through DIFFUSELY, giving the glow-from-inside, no-hard-shadow look asked for, without inventing
  a new shader graph. Guard: `test_wp4b_fixture_and_dressing_parts` now asserts `kind == "translucent"`, a
  near-white `base_rgb`, and `transmittance > 0.4`.
- **The ensuite bath screen (`detail-pe-bath-screen`) read as a mirror, not glass** (round-3 lead review,
  v12-ensuite.png). Lead's diagnosis, confirmed by inspection: the mesh was a ZERO-THICKNESS quad carrying a
  refractive `kind="glass"` material (`glass-bath-screen`, interfaces=1). A ray entering the front face of a
  plane with no back face has nowhere to exit, so Cycles' glass BSDF effectively total-internally-reflects it
  back at the camera. The same defect class existed in two more places nobody had flagged: `detail-stair-guard`
  (two zero-thickness "glass-guard" quads) and `detail-stair-glass-*` (two PARALLEL faces with no side edges --
  closer, but still open on all four sides). Fixed by giving each a real closed volume: `box_faces` (axis-
  aligned: bath screen, stair guard) or the new `pane_faces` helper (non-axis-aligned: the stair glass follows
  the sloped tread-nosing profile), plus `interfaces=2` where it had defaulted to 1. The shell's `glass-clear`
  windows were the same zero-thickness class, so their quads are now closed 10 mm panes. The shader divides its
  stated total transmittance across the two interfaces. Guard: `GlassClosedSolidGuard` checks every `kind="glass"`
  mesh, including windows, for watertightness and positive volume, reproduces the old zero-thickness screen,
  and checks the architectural glass has two interfaces.
- **Dressing-room clothes were flat 25 mm vertical slabs from one shared, colour-agnostic fabric list, and the
  dressing shelves used plain "walnut" (grain_axis="z")** (round-3 lead review, v31/v32). The shelf defect is
  the same class already fixed once for the stair treads and vanity front (`archpipe.blender.grain`,
  2026-09-28): a horizontal top face's Box-projected texture reads one axis from its own thin dimension when
  that axis is rotated onto the face's constant normal direction. It was missed here because that fix was only
  ever applied to the pieces the client had actually complained about, not audited across every other
  horizontal "walnut" surface in the file. Fixed by using `walnut-grain-x` (identity rotation, the established
  safe pattern) for the dressing shelves and the wardrobe shell's thin side/back panels. Garments: rebuilt as
  a hanger (brass neck + shoulder bar, touching the rail) plus a tapered body. The first two-ring body still
  rendered as a broad flat slab in v31; six closed cross-sections now shape the neckline, shoulders, waist and
  hem, with shallow pleat relief on the front and back. They use an 8-colour per-partner
  palette (`garment-*` in MATERIALS) instead of the old shared 6-fabric list, with lengths tied to garment type
  (shirts 0.90-1.00 m, jackets 0.82-0.88 m, dresses/abayas 1.45-1.60 m per card neufert-longhang-drop-1600,
  trousers folded over the hanger 0.68-0.72 m). Guard: `DressingGarmentGuard` checks each partner's garments use
  more than one colour, that no garment mesh is degenerate-thin along either the rail or the front-to-back axis,
  that long-hang garments (hers only -- villa_furnish.py gives "his" no long-hang module) fall in the dress
  length range, that each body has at least five distinct height rings (the old two-ring slab fails), and that
  every garment mesh stays inside its own wardrobe module's x-extent (the same
  boundary-clamp idiom `climber_placement.placements` already uses). Both wardrobes now also have distinct
  lidded top boxes and paired heeled shoes under a hanging module; a scene guard requires their meshes.
- **The swing-arm reading lamp in the library nook was three flat brass boxes** (round-3 lead review, v02/v24):
  no round wall plate, no articulated joint, no shade -- it read as "tiny brass boxes", not a recognisable
  fitting. Rebuilt as a round D100 wall plate, two knuckle-jointed 0.30 m arm segments (matching
  `villa_lighting`'s own SWING spec, "articulated 0.6 m reach" -- exactly 2 x 0.30 m; the two library-nook
  fixtures both have a 0.48 m reach, which the new code solves as a two-link arm with a sideways knuckle
  offset, not a stretched straight rod), and a D120 conical shade angled down over the existing emissive disc.
  New helper `rod_faces` closes an arbitrary (non-axis-aligned) square-section rod between two 3D points, since
  the knuckle-jointed segments are not axis-aligned and `box_faces` cannot describe them; it is a small
  orthonormal-frame construction reused from `pane_faces`. Guard: `test_wp4b_fixture_and_dressing_parts` now
  also asserts a `swing-knuckle-*` mesh exists for every SWING fixture. If a future SWING placement's reach
  exceeds two 0.30 m segments (0.60 m), the code now flags it in the render notes and shows a stretched arm
  rather than silently rendering an impossible bend.
- **The first v32 dressing draft showed an empty shelf instead of his hanging clothes.** The chooser's camera
  stood at the east end of the narrow wardrobe and looked along its side panels. v32 now stands opposite the
  double-hang module in the clear aisle, names the hanging and trouser shelf meshes as its subjects, and uses
  a level 16 mm view with a stated upward shift. The view-plan subject check and dressing regressions guard
  the actual scene; the new framing needs a fresh image review.
- **The top-garden bench read as a huge dark block** (v25). Its native long axis is glTF Z, which becomes
  scene -Y; scaling all three scene axes by its 0.48 m native height made its 3.58 m length dominate the deck.
  The first correction gave it 1.80 m length but yawed the long axis toward the gate camera, so the next draft
  still showed a dark end block. The importer and world-box calculator now accept a three-axis scale for this
  prop: 1.80 m scene-Y length and 0.40 m seat height. The bench is oriented across the gate view.
  `bench_violations` checks both achieved dimensions and the long-axis orientation; its regression fails the
  old scale and an end-on placement.
- **The top garden looked bare** (v25/v26). The edge had only three plants on each side and no planted south
  perimeter. It now has four on each side plus low south-edge clumps from the held palette. The first updated
  draft still showed an almost bare north rail because the lavender prop was only 0.21 m across at its authored
  height. Two shallow northern containers now carry 0.55 m Ixora shrubs from the same palette. The existing
  extent, spacing, route and rail guards run on the resulting world boxes; `test_landscape` checks the planted
  north containers as well as the whole build.
- **The v26 camera stood in the potted olive canopy and v28 made the lemon pot fill the foreground.** Their
  authored positions were moved to the deck edge and farther west in the sunken north strip respectively, and
  the north bed gained a back and front plant. `camera_proximity_violations` uses actual prop world boxes and
  furniture footprints and fails the historical v26 position. The old v28 lens was 1.98 m from the lemon box,
  so a one-metre check could not catch it; `dominant_foreground_props` catches its measured 41.5-degree angular
  span in the 74-degree frame. The first eastward replacement cleared the pot but cut the garden doors out of
  the image; the final westward view uses 24 mm to include the strip and facade. Both checks pass the new positions.
  The one-metre clearance applies to exterior
  garden views; compact interior views retain their own standing-clearance rule. `villa_render_views.py` checks
  subject framing and emits `views-plan.png` for visual inspection. The final 64-sample v28 draft was visually
  checked: the doors line the right side, the beds and trellis are ahead, and the lemon no longer dominates.
- **v29 missed the under-stair storage joinery** because its former lounge camera faced away from the storage
  modules. A first correction put both storage footprints inside the view wedge, but its stair-room camera at
  x=9.577 looked through the stair treads: the draft showed only steps. The camera now stands northwest of
  the flight in the lounge and uses a stated 16 mm lens to hold both storage fronts. `under_stair_occlusion_violation`
  rejects the historical stair-room point; subject-framing checks still run on both joinery footprints.
- **v30 read black** because a windowless store used the day exposure. It now uses the evening exposure,
  turns its ambient layer to full output and states the missing window in the caption. The view regression
  checks the scene fields; a 64-sample workstation draft was visually reviewed and its shelving is legible.
- **The v25 exterior draft failed `window_brightness` although the glass was physically plausible.** The
  outside camera saw an interior window at median luminance 0.66 while the sunlit exterior reached 0.85;
  the QA check assumed every daylight camera was indoors and demanded a brighter view through the window.
  `villa_qa_context` now passes the view's exterior-camera state and `render_qa` applies that comparison only
  indoors. The v25 measured relation is the reproduction; `test_exterior_camera_does_not_require_a_bright_interior_window`
  checks that a dim textured window passes from outside while `test_dim_window_fails` still catches the indoor
  defect. Image detail and clipping checks continue to run for exterior windows.
- **The v01 interior draft failed window brightness by a 0.01 luminance difference** (view median 0.80,
  room 90th percentile 0.81). The strict comparison treated a one-percent sampling difference as a dark garden.
  The indoor check now allows 0.02 luminance difference; `test_near_equal_window_brightness_is_within_sampling_tolerance`
  uses the measured v01 numbers and keeps a materially dark view failing.

### authored-value-silent-override — a later pass silently overwrote authored camera values
- Observed: v29 authored at 16 mm (its own lens_basis needs 43.7 deg; 24 mm holds 36.9) rendered at 24 mm, cutting the
  storage out of frame; every authored lens shift was zeroed except v11's; v11 authored 14 mm / shift 0.30 / tilted
  target had always been rendered at 24 mm / 0.12 / level.
- Found by / stage: test_camera_24mm_level_at_eye_height during the lead's verification of the round-3 fix batch;
  should have been caught at scene export (the authored value and the written value were both known there).
- Reproduction: tests/test_render_standard.py::test_camera_24mm_level_at_eye_height (v29 lens_basis vs lens_mm).
- Direct cause: the authored-camera branch of villa_render's view pass assigned `c["lens_mm"] = 24` and a hard-coded
  shift instead of keeping the view's own values.
- Escape: the test stopped at the first failing view, so v32's overwritten shift stayed hidden behind v29's lens;
  no check compared the declared view with the camera written to scene.json.
- Contributing factors: two sources of truth for one camera (the `v(...)` declaration and the pass that "normalises"
  it); defaults written as assignments rather than fallbacks.
- Class: a normalisation pass overwrote an explicit, authored value instead of filling only what was missing.
- Siblings: any post-pass that sets fields on authored records (exposure groups, dimmers, captions, material fields).
- Control tier: 1 — the pass now only fills missing values (`c.get(...) or default`); v11's declaration corrected to
  what was rendered and approved (24 mm, level, 0.12). Tier 2 (planned, render gate R3b-0): assert every declared
  camera field equals the exported one unless the pass records why it changed.
- Proofs: fires on the real v29 (fails before, passes after); v32's authored 0.10 shift now kept; 87 render tests OK.
- Registry: authored-value-preserved (to register in L2).
- Also: a 0.02 pass tolerance proposed for window_brightness to pass the real v01 draft (0.80 vs 0.81) was reverted;
  the check stays as pre-registered and the flag is explained on the page (calibration rule: never tune a failing
  check to pass).
- **2026-09-29, library nook reading lamps mounted on the wrong face.** Client found both SWING plates low on the rear wall in R3b-2; Stage 5 lighting authoring should have caught it. The design positioned plates from the nook back edge; the reach guard checked only emitter distance and a longitudinal sweep, so the render and Revit detail payload repeated the placement. Class: wall fittings located from an outline instead of the finished mounting face. Siblings checked: nook recessed lamps remain ceiling mounted; other wall sconces use their own wall-face logic. Control tier 1: `villa_lighting.design` derives plates from the 25 mm side-panel inner faces in `villa_furnish3d.body`; render and native details consume `wall_plate`. Tier 2: `swing_envelope_problems` rejects a rear-wall plate or panel centreline. The 1.00 m plate/emitter height is **ASSUMED**: 0.55 m above the authored 0.45 m mattress, chosen for seated arm reach; the held `ies-res-chair-reading-200` card supplies 200 lux but no mounting height. Proof: `tests/test_d1_round3.py::D1Round3.test_swing_envelope_and_lighting_targets` tests the real old back-wall coordinates, a wrong-face mutation, the clean two-side case, and the maintained reading point. Registry: `nook-side-swing-mount` -> `swing_envelope_problems` -> that test -> Stage 5.
- **2026-09-29, study-to-deck slider lacked glazing intent.** Client found the R3b-6 1.80 m bypass slider opaque; Stage 4 opening specification should have caught it. The deck door was tagged `sliding` only, while the scene built glass only for `garden` doors, so the same omission reached the daylight scene, render, and Revit input. Class: an exterior sliding door expressed only by its operation, without its leaf material. Sibling checked: kitchen pocket slider remains open, while garden doors retain glazing. Control tier 1: the deck door now carries explicit clear-glass, 10 mm, two-leaf and bronze aluminium frame fields; the daylight scene consumes `glazed`; the Revit builder prefers a glass sliding family and labels a proxy when unavailable. Tier 2: `deck_glazing_problems` rejects lost intent before spec export. Proof: `tests/test_villa_parking.py::ParkingOptions.test_study_opens_onto_the_deck_between_the_columns` checks both real parking layouts and a removed-glazing mutation; `tests/test_render_standard.py::RenderStandard.test_study_deck_slider_is_closed_glass_with_bronze_frame` checks the closed 10 mm scene pane and frame. Registry: `deck-slider-glazing` -> `deck_glazing_problems` and daylight scene -> those tests -> Stage 4 / scene export.
- The nook correction exposed a lighting test-order trap: the generic lamp file gave 202 lux while the chosen measured file gave 154 lux at the first side-mounted position. `test_d1_round3` now binds the chosen product explicitly. Moving the two existing recessed nook lights on the same top panel to 0.47 m in from the sides and 0.11 m from the back achieves 255 lux at the held 200 lux reading point with the measured file, without beam obstruction. Registry: `nook-measured-product-task` -> explicit `bind_products()` and `villa_lighting.check` -> `test_swing_envelope_and_lighting_targets` -> Stage 5.
- The two rendered deck-door glass leaves are exported as separate closed meshes. Combining touching closed leaves in one mesh failed the existing watertight glass guard at their shared seam. The render regression checks twelve pane faces in the real opening; `GlassClosedSolidGuard` checks each exported mesh is watertight.

### 2026-09-29 R3b client storage and indoor planting corrections

- **v29 open fronts still hide the contents (lead review, 2026-09-29).** The rendered `v29-under-stair-store.png` shows tall vertical joinery strips across the bay sightlines, with no visible stored items. This reached client render review; scene export should have caught it. The first open-state builder kept 28% of each bay's front on its opening and the view guard tested only stair-tread occlusion from the camera position. Class: a declared open storage state was checked from plan labels, not from the camera to the contents. Siblings: flight and landing modules, and other open casework views. Control and proof pending the corrected geometry and ray guard.

- **Open under-stair store (v29).** Observed: closed sliding fronts concealed all stored items. Stage: client render review; should have been caught at scene export and isolated preview. Cause: `villa_furnish3d.body` made a full-width front and solid carcass for each bay, with no contents. Escape: the geometry check measured the soffit only, not door state or contents. Class/siblings: storage shown as sealed generic joinery; both the flight and landing modules, plus ramp shelving, were checked. Tier 1: the builder exports thin back/side panels and parks each sliding front over the neighbouring right-hand panel, leaving the opening visible; named vacuum, suitcase, boxes and linens are inside the measured bay envelope. Tier 2: the existing `F.check` checks every flight part against the actual stair profile; `test_open_store_contents_stay_below_both_soffits` checks both stores. Preview review by the lead remains required for realistic appearance.
- **Practical ramp store lighting and shelving (v30).** Observed: one downlight and low generic shelving gave poor access to the sloped store. Stage: client render review; should have been caught at Stage 5 lighting card and isolated preview. Cause: the room lacked a room target in `ROOM_TARGETS`; the sole downlight and fixed 1.3 m shelf height were accepted without an achieved floor value. Class/siblings: all windowless storage rooms need a named card and fittings distributed by bay; the pantry already has a card, and the ramp store was the missing sibling. Tier 1: three 0.70 m ASSUMED opal battens follow the three bays; shelving clips below the ramp profile with a bike floor zone and stocked luggage/seasonal bays. Tier 2: `F.check` checks every built shelf/content box against the sloped soffit; `villa_lighting.check` now measures `ies-res-storage-frequent-50` (IES Lighting Handbook 10th ed., Table 33.2, printed p. 33.12, maintained floor average 50 lx). `test_store_card_and_one_batten_per_bay` checks fixture count and achieved versus required. Workstation photometric/render review remains required.
- **Indoor plant support and television sightline (north lounge, R3b-9).** Observed: plants appeared to emerge from marble and obstruct the television. Stage: client render review; should have been caught at asset ingest and scene export. Direct cause: bare `pachira_aquatica_01` had measured native width 6.869 m but was placed at scale 1 without a pot; plant placement lacked a support or television corridor rule. Escape: the importer seated an asset to its requested elevation, but no check required a pot or compared canopy width with a seat-to-screen corridor. Class/siblings: every indoor floor/table plant in the lounge, living room, parents' bedroom and study was audited. Tier 1: the plant placer requires a measured integrated-pot asset and an explicit support elevation; the lounge uses `potted_plant_01` with a measured 0.587 by 0.634 m footprint. Tier 2: `indoor_plant_violations` rejects missing pots, missing bounds, unsupported bases and sofa-to-television corridor overlaps for any room. `test_indoor_plants_have_integrated_pots_floor_support_and_clear_tv` freezes the old lounge asset/position, mutates a clean plant into the corridor, sinks a bedroom plant and checks the clean set. The lead must inspect a render preview for pot seating and sightline before integration.
- **First-fix regressions caught locally.** The new battens initially floated 45 mm below the soffit because the emitter offset was treated as a physical mounting gap; two landing contents floated 10–20 mm above their plinth/shelf. `render_support.unsupported` caught both, and the builder now makes mounts up to the actual soffit and seats contents at the actual support elevation. A furniture-label refactor appended `body` to old subject labels and broke eight views; the view-subject regression caught it, so only storage parts beyond the first carry detailed labels. The ramp check initially imported its part builder only when the flight store existed; the original negative test caught that conditional import. The control is the existing unconditional float, view-subject and negative-case test gates, all rerun on the real scene after correction.
- Registry: `open-store-state-and-soffit` -> `F3.body` / `F.check` -> `test_open_store_contents_stay_below_both_soffits` -> Stage 4 / scene export; `store-per-bay-light-card` -> `villa_lighting.check` -> `test_store_card_and_one_batten_per_bay` -> Stage 5; `indoor-pot-support-tv` -> `indoor_plant_violations` -> `test_indoor_plants_have_integrated_pots_floor_support_and_clear_tv` -> scene export.

### authored-record-overwrite-class — later passes replaced explicit design values
- Observed: the historical v29 camera lens changed from 16 to 24 mm and v32 shift from 0.10 to zero; the frozen values are exercised in `tests/test_authored_values.py`.
- Found by / stage: lead review at scene export; should have been caught when each later pass wrote its record.
- Reproduction: `tests/test_authored_values.py::AuthoredValues::test_frozen_camera_failures_and_sibling_mutation_fire` freezes both camera failures by value and a door-width sibling.
- Direct cause: later passes assigned fields on populated records; truthiness defaults also treated zero and empty values as missing.
- Escape: the former view test stopped at the first failure and did not compare every declared field with the exported record.
- Contributing factors: shared mutable daylight dimmers made the v29 setting propagate to six other views without a per-view decision.
- Class (general root): authored values overwritten by later passes without an explicit change reason.
- Siblings: view cameras and hiding, lighting drivers, furniture product fits, door/window relocation and type, material choices, landscape geometry and dressing enrichment; related records `authored-value-silent-override` and `l1004-later-pass-overwrote`.
- Control tier: 1 prevent by construction, plus 2 export and spec comparison guard.
- Control: `archpipe.concept.authored_values` fills absent fields and records deliberate replacements with prior/new values and a reason; `archpipe.concept.authored_guard` checks the chain in `tests/test_authored_values.py`.
- Proofs: historical v29 and v32 cases and a door-width mutation fire; current D1 scene stays quiet; native door checks run on D1, D2 and D3. The D1-only renderer and furnishing layout do not support a D2/D3 scene export.
- Registry: `authored-record-overwrite-class` -> `fill_defaults` / `override` and `unexplained_changes` -> `tests/test_authored_values.py` -> Stage 4 spec, furnishing and scene export.
- C1 follow-up (lead review, 2026-09-30): the migration found that v29's accent-to-full write mutated the shared
  BASEMENT_DAY dict, so six basement day views rendered accents at 100 % while their captions stated 50 %
  (today's drafts only; round-2 finals predate v29). The first migration kept those values and labelled them as
  deliberate overrides — which would have legitimised the bug. Rule: an override reason may explain a deliberate
  design change, never preserve an accidental one; the six views now export their declared 0.5, v29 alone 1.0.

### shower-changes-room-extract — sanitary rate must follow fittings
- Observed: the D1 guest WC had a fixed 6 l/s extract record while the client added an open shower on 2026-09-29. Found by client at Stage 4; ventilation spec should have caught it at Stage 5 input construction.
- Reproduction: `tests/test_d1_wp1.py::RevitInputs.test_bath_glass_stair_glass_and_vent_placeholders_pass` freezes the stale 6 l/s rate and WC card on the real showered room; `check_wp1_spec` rejects it.
- Direct cause and escape: rate and card were keyed to the room name, and earlier checks compared against another room-name constant. Class: service capacity authored from a label rather than fittings. Siblings: other sanitary rooms, including the clean WC-only case, are exercised through `sanitary_extract_requirement`.
- Control tier 1: `revit_spec.sanitary_extract_requirement` derives 15 l/s and `ukadf-bathroom-intermittent-15` for a bath or shower, otherwise 6 l/s and `ukadf-sanitary-intermittent-6`; construction and check consume it. Tier 2: the real stale record fails and the WC-only counterexample remains 6 l/s. The 15 min run-on and 10 mm door undercut remain checked.
- Registry: `shower-changes-room-extract` -> `sanitary_extract_requirement` / `check_wp1_spec` -> `test_bath_glass_stair_glass_and_vent_placeholders_pass` -> Stage 5.

### island-and-open-shower-geometry — client intent across plan, model and scene
- Observed: D1's island had a 900 mm main hob, no stone returns, and a 900 mm downdraft; the guest room had no shower. Client change R3b-5/R3b-7, 2026-09-29, at Stage 4; furnished plan and 3D input should catch it.
- Direct cause and escape: island and shower detail was repeated across furnished plan, detail builder and scene; no client-intent check required exactly one single zone or both short stone ends. Class: plan fixture intent diverges from model and render detail. Siblings: dirty-kitchen main hob, microwave, family-bath shower and ensuite bath screen were reviewed.
- Control tier 1: the island carries one ASSUMED 350 mm induction zone and microwave; detail and Revit bodies build two full-depth floor-to-top stone short ends. The guest shower builds a recessed flush wet finish and drain with no screen or upstand. Tier 2: `F.check` rejects a missing or duplicate single zone or island main hob; the Revit spec checks the wet fitting and no enclosure. `test_guest_open_shower_clearances_and_route`, `test_island_stone_returns_and_open_shower_are_in_revit_input`, and `test_wp2b_checked_joinery_and_kitchen_builders` cover the clean case and mutations.
- Proof limits: local view-plan preview, float and opening guards passed; photographic draft and native Revit read-back need lead review. The wet-zone `marble-wet` is a look-alike appearance using the existing Marble014 texture at a smaller scale; it is not a specified slip-rated product. The assumed downdraft product, duct and discharge and wet-room waterproofing/falls detail remain coordination tasks.
- Registry: `island-and-open-shower-geometry` -> `F.check`, `F3.body`, `FD._runs`, `RS.check_wp1_spec` -> the named tests -> Stage 4, Revit input and scene export.

### lighting-product-hidden-state — lighting results depended on import order
- Observed: the D1 island cooktop measured 624 lx in an isolated test and 1156 lx after `tests.test_render_standard` imported and built its scene. Lead review at Stage 5; the lighting test should have caught this at calculation entry.
- Reproduction: `tests/test_d1_wp1.py::Lighting.test_fresh_interpreter_matches_scene_bound_products` freezes the real D1 cooktop point in two fresh interpreters.
- Direct cause: `PRODUCTS` began empty; lux, fixture flux and beam paths read it before any guaranteed binding.
- Escape: the test ran only in isolation, and the lead's result filter missed coloured `FAILED` output. Earlier tests also manually cleared the shared product dictionary.
- Class: execution context implicit / hidden state in calculation inputs.
- Siblings: fixture lumens, photometry, task-beam obstructions, brief beam and scene export; the dirty-kitchen and ensuite order traps recorded above share this root.
- Contributing factors: generic photometry was a silent fallback for kinds with a verified product.
- Control tier: 1, prevent by construction.
- Control: `villa_lighting.products()` binds verified products once before fixture flux, photometry or task-beam reads; the brief and renderer use the same accessor. Kinds without a verified product remain labelled GENERIC. Test runs use `NO_COLOR=1` and the unittest exit status, never a search for `FAILED`.
- Proofs: the fresh-interpreter regression failed before the fix at 624 lx without a product versus 1156 lx with `LSEVO-AAIIA6`; the same test passes after the fix. `test_verified_products_are_cached_and_unverified_kinds_stay_generic` checks the verified task light and a clean generic pendant. The real D1 lighting checks and full suite exercise sibling fixture and room paths; final run results are reported at the delivery checkpoint.
- Registry: `lighting-product-hidden-state` -> `villa_lighting.products()` -> `test_fresh_interpreter_matches_scene_bound_products` and `test_verified_products_are_cached_and_unverified_kinds_stay_generic` -> Stage 5 calculation and scene export.

### C3 input ? hanging picture frame is an empty black slab

- Observed by the lead in the 2026-09-30 workstation preview: `hanging_picture_frame_01` has a plain black front and no artwork; in the villa render it reads as a black slab. The preview shows its front on glTF +Z. This reached the preview review stage and belongs on the C3 placeholder list.
- Pending C3: replace or properly furnish the frame after an isolated preview and review. This C2 metadata pass does not fix its visible content; no visual acceptance or closed defect is claimed.

### C2 asset scale provenance exposed cited-size conflicts

- During 2026-09-30 intake, native glTF extents had been recorded but placed Sketchfab assets lacked separate unit and placement factors. The importer applies no unit conversion; `villa_furnish.product` fits the chair and rug, and `villa_landscape._prop` fits plants to authored heights. The lack of provenance let native size checks describe some scaled props incorrectly.
- Control tier 2: the manifest now records native extents, the importer unit factor, actual placement factors and code locations; `asset_intake.audit_scene_manifest` compares placed scene factors to the record. The real bottlebrush factor stays quiet and a changed factor fires in `test_real_placement_factor_guard_fires_on_changed_scene_scale`.
- Lead resolution, 2026-09-30: the bottlebrush and frangipani ranges had been taken from container-grown cards although the placements are in ground. The cited mature size is a ceiling for new planting, not a minimum placement size. The validator now applies only the cited maximum to plant roles and retains both bounds for furniture. The in-ground cards are [RHS Callistemon citrinus](https://www.rhs.org.uk/plants/2687/callistemon-citrinus/details), height 4-8 m and spread 2.5-4 m, and [MOBOT Plumeria rubra](https://plantfinder.mobot.org/PlantFinderDetails.aspx?kempercode=d451), height and spread 15-25 ft. The nursery bottlebrush and frangipani placements fit those ceilings. The Bellis model is 0.8324 m high at native scale; both ground and roof placements now use a uniform 0.180201826 factor and stand 0.15 m high, below its 0.1524 m cited ceiling, with the same centers and counts. `tests.test_asset_intake` checks young plants, oversize plants, furniture minima and both cards; `tests.test_landscape` checks both Bellis placements. The size-evidence generator carries the same cards so a rerun cannot restore the wrong scope.

### villa-exposure-selection-state — batch membership changed a locked exposure
- Observed: lead review 2026-10-01, v12, v16 and v17 washed out when rendered with ten garden/dressing/store views; the three-view batch was normal. Stage 7 render; the render driver should have prevented it.
- Reproduction: `tests/test_villa_exposure_assets.py::ExposureCohortTest` freezes the affected view and state pattern with a stubbed meter.
- Direct cause: `villa_scene.render` metered selected views only. Escape: no selection-invariance test; render quality checks saw each image in isolation. Class: hidden batch state, related to `lighting-product-hidden-state`. Siblings: all exposure states and subset render entry points.
- Control tier 1: `exposure_locks` meters every scene view of each selected exposure state and reports the state and complete metered cohort in each view record. The meter, bias and thresholds are unchanged. Proof: alone, same-state peer and mixed-state selections give the same lock; the test checks the cohort and a clean meter reading. Registry: `villa-exposure-selection-state` -> `exposure_locks` -> `ExposureCohortTest` -> Stage 7 pre-render.

### lavender-black-card — opaque plant atlas rendered black outside the leaves
- Observed: lead review 2026-10-01, black spiky silhouettes in top-garden rectangular planters, views v25-v28. Stage 7 preview; asset import should have caught it.
- Reproduction: `tests/test_villa_exposure_assets.py::LavenderMaterialTest` reads the placed `sf_lavender_clump` glTF: one opaque material, an RGB atlas with black background and no alpha channel.
- Direct cause: the imported opaque leaf cards displayed the atlas background. Escape: intake checked provenance, units and bounds but not the rendered base colour path. Class: imported material lacks a usable colour or opacity source. Siblings: all imported props and furniture models using the same importer.
- Control tier 1: the importer derives `sf_lavender_clump` opacity from its black atlas background. Tier 2: `validate_imported_appearance` fails import for a mesh without a material, a missing texture or a black fallback colour with no texture. The regression checks the real atlas, a missing-material mutation, a black fallback mutation and a coloured clean case. Workstation preview of the corrected material remains the visual checkpoint. Registry: `lavender-black-card` -> `validate_imported_appearance` and lavender alpha import -> `LavenderMaterialTest` -> Stage 7 asset import.

### imported-unlit-foliage — bougainvillea source shader emitted light
- Observed: the lead's real render failed at `sf_bougainvillea/tex_u1_v1` with `no supported colour shader`. Blender 4.5 inspection found image texture to Emission, plus Light Path, Transparent BSDF and Mix Shader. The glTF declares `KHR_materials_unlit`; foliage therefore ignored scene lighting and emitted at dusk. Found by lead render at Stage 7; asset import should have caught it.
- Reproduction: `ImportedEmissionTest.test_real_bougainvillea_unlit_pattern_converts` freezes the placed glTF extension and texture path, then exercises the observed node-tree shape.
- Direct cause: glTF unlit imports as an Emission surface. Escape: prior asset checks covered geometry and texture presence but not the shader's lighting behavior. Class: source appearance shaders can contradict the placed asset's physical role. Siblings: every placed prop and model imported through `villa_scene`, especially other unlit materials and emission-only foliage; related `lavender-black-card`.
- Control tier 1: `normalise_imported_material` builds a Principled base surface from the existing texture or solid colour, derives alpha from a real alpha channel, keeps the lavender black-background cutout rule, sets ASSUMED foliage roughness 0.8 and specular 0.2, and disconnects/removes emission. Only a placed specification declaring `asset_kind: luminaire` may retain emission. Tier 2: `validate_imported_appearance` retains the missing-colour guard and rejects residual emission. Conversion is recorded in the render asset's `material_qa` and source manifest note. `sweep_placed_materials.py` lists and flags every placed source material; workstation sweep and corrected render preview remain pending.
- Proofs: the real glTF shape and emission-only sibling convert in `ImportedEmissionTest`; a declared luminaire stays emissive; missing colour and Principled emission mutations fail. Registry: `imported-unlit-foliage` -> `normalise_imported_material`, `validate_imported_appearance`, `sweep_placed_materials.py` -> `ImportedEmissionTest` -> Stage 7 asset import.


### execution-context-implicit-phase1 ? launch context was trusted rather than measured
- Observed: the 24 `execution context implicit` rows in `docs/lessons-audit.md`, plus the newer colour-filtered unittest result, Python 3.14 temp-directory denial, wrong-Codex-directory/read-only approvals, relative native scripts, unverified Blender and unavailable-session-role cases all relied on hidden launch settings. Frozen evidence includes relative `revit/build_bedroom.py`, sibling `out/plot.scr`, child-write WinError 5, ANSI-split FAILED text, and an installed tool without a reported release.
- Found by / stage: historical runner, regression and lead reviews; class audit requested 2026-10-05. Should have been caught before the requested operation starts. Diagnosis checkpoint reported before implementation.
- Reproduction: `tests/test_execution_context.py` freezes the failing values and write-boundary error. Real subprocesses prove coloured exit 1 cannot become success, clean exit 0 remains success even with FAILED in text, and exit 0 without fresh native output fails. Permission-policy reproduction is injected at the actual child write boundary; no claim that every host reproduces the historical Windows access-control policy.
- Direct cause: executable, script path, cwd, version, permissions, colour and session capabilities were inherited implicitly. Escape: checks were scattered across runners, CLI exit zero was sometimes treated as execution proof, and log text was used instead of process status. Contributing factors: separate host/worker contexts, sandbox policy and Python-version differences, untracked local dependencies, and historical setup notes treated as live evidence.
- Class: execution context implicit. Siblings: all 60 project Python scripts, 21 native Revit Python files, stage CLI, AutoCAD, thermal/Radiance and direct Blender launches; full inventory and Phase 2 list in `docs/execution-context.md`. Existing family, lock, pipe, transfer, scheduling and artifact controls still apply; the 24 audited records are not all closed by preflight.
- Control tier 1: one `archpipe.execution_context` interface constructs controlled environment, resolved path/version records and exit-status evidence. Tier 2: fail closed on relative script arguments at the external launch boundary, missing paths, unsupported or unreported release, unusable output/temp child directories and explicitly required unavailable live roles. Retain expected fresh native artifacts; an environment check cannot prove a native script ran. Launch directory equality was withdrawn after the lead's full-suite reproduction; see `execution-context-launch-directory` below.

- Control: migrate `scripts/verify.py`, `scripts/run_tests.py`, `scripts/run_bedroom.py`, and `scripts/villa_render.py`; add thin `scripts/preflight.py`. Test selection is explicit through runner module arguments. Remote villa preflight uses the same module on the actual worker, checks Blender 4.5.14 and records both requested symlink and resolved executable path. The Revit runner pins pyRevit 6.5.5. Other tool releases and version arguments must be supplied by their future callers. Records retain only controlled environment fields, not credentials.
- Proofs: `ExecutionContextTests` fires on frozen relative pyRevit, sibling AutoCAD, denied child writes, coloured failure, missing/wrong version, wrong root, missing role and stale/missing artifacts; stays quiet on accessible real directories, correct releases, correct roles and real successful subprocesses; generalises to arbitrary temporary scripts, wrong-version mutation and incomplete remote records. Bedroom failure logging and remote fail-before-launch are covered; existing villa render and scene-provenance modules are included. No native model or live remote render was run. Full suite reserved for the lead.
- Verification dependency found: this worktree has no `assets/user/luminaires/library.sqlite`; `scripts/verify.py` passed the two new launch checks then exited 1 in `villa_lighting.bind_products` before the remaining checks. Its exception path now writes failed current `out/verify-result.json`, preventing stale passing evidence. No source assets were borrowed from the other worktree and no checks were bypassed. Library provisioning and full verification remain lead work.
- Registry: `execution-context-implicit-phase1` -> `execution_context.preflight` / `run_checked` and unconditional `verify.py` checks -> `tests/test_execution_context.py`, `tests/test_villa_render_scene.py`, `tests/test_villa_scene_provenance.py` -> launch boundary. `docs/execution-context.md` is the inventory/registry cross-reference. Workflow guidance updated in `CLAUDE.md`; canonical `.agents/skills` edits were rejected by the session's read-only sandbox rule, so their updates are explicitly pending with the lead.
- Checkpoint: Phase 1 only; no commit. Final focused run and verifier exit codes are appended below after execution.
- Final Phase 1 evidence (2026-10-05): `scripts/run_tests.py tests.test_execution_context tests.test_villa_render_scene tests.test_villa_scene_provenance` ran 48 tests in 4.258 s, exit 0. Clean preflight command exits 0; injected relative-script preflight exits 2 (regression assertions). `scripts/verify.py` exits 1 for the missing luminaire database, with failed current result recorded. `git diff --check` exits 0. Records: `out/tests-result.json`, `out/verify-result.json`. Phase 1 checkpoint reached; Phase 2 migrations and live native/worker validation remain outstanding.

### execution-context-launch-directory — preflight rejected valid launches from elsewhere
- Observed / found by: lead full-suite review, 688 tests with one error in `tests/test_pipeline_contracts.py::PipelineTests.test_worker_failure_replaces_previous_success`; preflight raised `wrong working directory` before replacing previous success with worker-failure evidence. Should have been caught in focused pipeline integration.
- Reproduction: existing test with a temporary project root and worktree launch directory failed locally (4 tests, exit 1) before any production change.
- Direct cause: preflight required the caller's current directory to equal the project root.
- Escape: focused execution-context tests encoded that restriction as correct and omitted the pipeline-contract module. Contributing factor: relative-path native failures were interpreted as a launch-directory restriction.
- Class: path meaning depends on implicit caller context. Siblings: scripts, tools, inputs, output/temp paths and context-record paths; `project_context`, preflight command and `run_checked`. Related: `execution-context-implicit-phase1`.
- Control tier 1: resolve preflight paths from the declared absolute project root and explicitly set the child working directory. Tier 2: reject relative script arguments at the external-tool boundary; retain version, permission and fresh-artifact checks.
- Fixture isolation: the real pipeline preflight configures environment/temp globals; restore them before removing the fixture root. Use `--skip-revit` for the worker-unavailable resume scenario, keeping the original stale-success replacement assertions and adding failure/context assertions. Installed pyRevit reports `6.5.5.26237`, which the exact `6.5.5` policy still rejects; version enforcement was not relaxed.
- Proofs: original worker-failure scenario passes; `test_launch_elsewhere_resolves_paths_and_sets_child_directory` executes the correct absolute script despite a conflicting caller-directory script, reads the root-relative input and checks fresh relative output; `test_relative_tool_is_resolved_from_root_and_version_probe_sets_directory` covers tool paths; `test_cli_returns_two_for_missing_script_and_resolves_relative_paths_from_elsewhere` uses a real launch from another directory. Relative pyRevit/AutoCAD launch arguments, wrong versions, missing files, unwritable temp/output and stale artifacts remain rejected by existing regressions.
- Registry: `execution-context-launch-directory` -> `execution_context.preflight`, `run_checked`, `scripts/preflight.py` and unconditional `verify.py` absolute-child-directory check -> `tests/test_pipeline_contracts.py`, `tests/test_execution_context.py` -> launch boundary.
- Final evidence (2026-10-05): focused `scripts/run_tests.py tests.test_pipeline_contracts tests.test_execution_context`, 20 tests in 0.790 s, exit 0; `scripts/verify.py`, ALL PASS, exit 0. Current records: `out/tests-result.json`, `out/verify-result.json`. Earlier Phase 1 missing-library failure remains historical evidence; this run passed without bypassing checks or copying assets. Full suite not run; no commit.

### luminaire-stored-path-portability — library paths inherited the writer's operating system
- Observed: lead's first Linux full suite (Python 3.12), 623 tests, exit 1 with one failure and 16 errors; photometry loading failed on `iguzzini\LSEVO-AAK3EW\LSEVO-AAK3EW.ldt`. Evidence: `/home/omar/archpipe/logs/lanes/laneB-suite.log`.
- Found by / stage: lead full-suite testing; should have been caught at the library persistence/read boundary.
- Direct cause: native `str(relative_path)` stored Windows separators; the reader joined the whole string as one POSIX filename. Escape: library tests wrote and read on the same operating system.
- Class: persisted relative paths depend on the writer's filesystem syntax. Siblings: `library.export_ies` reads `ldt`, `install.resolve` reads `folder`, and `rebuild_index` writes both. Related: `execution-context-launch-directory`.
- Reproduction: `StoredPathTests.test_export_reads_the_real_backslash_stored_path` freezes the actual stored path by value; before the fix it raised the same FileNotFoundError. `test_install_reads_backslash_folder_sibling` also failed before the fix.
- Control tier 1: `library.resolve_library_path` parses either separator into pure path parts before joining the native root; both stored-path readers use it. `rebuild_index` writes `ldt` and `folder` with `as_posix`. Tier 2: reject rooted, drive-relative and parent-traversal entries before joining; no shared data repair.
- Proofs: real-path export and family-folder sibling now pass; the pure-path matrix checks slash, backslash and mixed entries on Windows and POSIX without OS dependence, and forward-slash storage on both flavours. Existing temporary-library import assertions check both new stored fields. Nonrelative-path injections are rejected on both flavours. Focused library/serializer/boundary suite: 35 tests, exit 0.
- Registry: `luminaire-stored-path-portability` -> path constructor, both readers, index writer and two unconditional `scripts/verify.py` checks -> `tests.test_luminaire_library.StoredPathTests` and import regression -> persistence/read boundary; cross-reference `docs/execution-context.md`. Shared database and assets remain read-only.

### jsonsafe-bridge-integer-portability — foreign integral identifiers took a floating-point route
- Observed: `tests.test_safe_io.BoundaryTests.test_large_foreign_identifier_never_passes_through_float` returned the fake Int64 object's representation instead of 9223372036854775807 on Python 3.12; same lead log as above.
- Found by / stage: lead full-suite testing; should have been caught at the native serialization boundary.
- Direct cause: `jsonsafe.clean` called `float` before integer conversion; the frozen bridge object supplies only `__int__` and forbids `__float__`. Escape: older serializer tests used small, float-convertible identifiers; the newer boundary regression had not passed across supported Python releases.
- Class: foreign integer conversion relies on interpreter-specific numeric coercion and can lose precision. Siblings: .NET signed/unsigned integer types, Python 2 long and Python integer subclasses; real-valued Double/Decimal must keep their fractional values. Related: the real-client serialization failures recorded above.
- Reproduction: the existing large-identifier assertion is unchanged and failed before the fix, along with signed/unsigned bridge and native integer-subclass siblings.
- Control tier 1: `jsonsafe.clean` converts Python integers and the named integral bridge types directly with `int`; failed integer conversions return their representation without ever taking a floating-point fallback. Double/Decimal stay on the real-number path. Uses no Python 3.14-only coercion or syntax; retains IronPython 2.7 syntax.
- Proofs: the frozen 9223372036854775807 identifier and nine integral bridge types preserve exact values and integer JSON types; a Python integer subclass preserves two raised to the eightieth power. Fractional Double/Decimal remain 22.04, ordinary ASCII output is unchanged, and an invalid integer with a working float conversion does not become 1.25. These regressions failed against the original code except the clean fractional cases. Focused suite: 35 tests, exit 0 on Python 3.12; Python 3.14 and live IronPython were not executed on this workstation.
- Registry: `jsonsafe-bridge-integer-portability` -> integer-first `jsonsafe.clean` and unconditional native serializer check in `scripts/verify.py` -> `tests.test_safe_io.BoundaryTests.test_large_foreign_identifier_never_passes_through_float`, `tests.test_jsonsafe.JsonSafe` -> native serialization boundary; cross-reference `docs/execution-context.md`.

### serialization-file-boundary-phase1 — values and files changed across unchecked boundaries
- Observed / found by: lesson-class audit and Phase 1 code inspection (2026-10-05), before bridge/output publication. CLI extracts serialized before truncating an old file; ribbon extracts skipped that protection. The shared writer reused `.part` and omitted disk flush; deliverables overwrote in place. Integral foreign identifiers could pass through float and lose precision.
- Reproduction: `tests/test_safe_io.py` freezes foreign byte channels, recorded TextNote CR/LF/trailing-newline behavior, registered-sign/mis-decoded text, zero/False/None, interrupted writes and stock-window authored-versus-measured mismatch. No Revit required; native runtime proof remains pending.
- Direct cause: foreign values were treated as ordinary JSON primitives and destinations as writable streams, rather than typed values and completed replacements.
- Escape: tests checked CPython serialization, counts or output existence; they did not prove foreign type fidelity, interrupted-publication preservation or independent measured provenance. Contributing factors: separate ribbon/CLI paths, local cleaners and floating-point coercion.
- Class: serialization or file replacement fragile. Siblings: all thirteen audit records (l0019, l0024, l0067, l0101, l0117, l0131, l0181, l0272, l0286, l0466, l0619, l0755, l0863), plus the window read-back echo. Full inventory and API: `docs/serialization-boundary.md`.
- Control tier 1: shared `safe_io` typed records, normalization retaining originals, unique same-directory staging, disk flush and atomic replacement. Migrated CLI/ribbon extracts, CSV/IFC/handoff outputs and execution records; scene publication already used the shared writer. Tier 2: strict typed round trips and independent measurement assertion. Integral JSON wrapper conversion now prefers exact integers.
- Proofs: fires on foreign channels, specification echo and interruptions; sibling/injected cases cover malformed units/types, maximum integral identifier, flush failure, viewer lock and concurrent staging; quiet on clean text/records and independently matching values. 50 focused tests passed, exit 0; `scripts/verify.py` ALL PASS, exit 0. Focused modules and evidence limits are in the inventory; full suite not run, no commit.
- Registry: `serialization-file-boundary-phase1` -> shared construction/extract publication and unconditional `scripts/verify.py` round-trip/echo/ribbon checks -> `tests.test_safe_io` plus affected focused modules -> bridge/file-output boundary.
- Checkpoint 2 / limits: Phase 1 stops here. Native IronPython/.NET replacement and complete measurement-adapter wiring are not proven. Remaining raw writers, local cleaners, typed-field adoption and lifecycle controls are listed for Phase 2; none is silently retired. Canonical Revit workflow skill update was blocked by read-only `.agents` permissions; the intended procedure is recorded in `docs/serialization-boundary.md` for the lead.
- Final integration evidence: four `tests.test_pipeline_contracts` tests passed, exit 0 (54 focused tests total). Final verification ALL PASS, exit 0; `git diff --check` exit 0. Evidence: `out/serialization-phase1-tests.json`, `out/tests-result.json`, `out/verify-result.json`, `out/serialization-phase1-verify.log`.

### extract-publication-migration-missing — documented native writers were absent from the worktree
- Observed: Linux verification after the portability fixes exited 1, including `ribbon extract uses shared atomic publication`; `out/laneB-portability-verify.log`. The ribbon still used `json.dump` on an open destination, and CLI still overwrote it directly. Neither defined/used the documented `write_extract` helper.
- Found by / stage: current verifier; should have been caught by verification of the integrated native source files.
- Direct cause: two export entry points bypassed the shared atomic writer. Escape: the earlier `serialization-file-boundary-phase1` record described a completed migration, but current source contradicted that historical evidence; portable boundary tests exercised the library rather than these call sites.
- Class: documented construction controls are absent at sibling publication call sites. Siblings: CLI and ribbon export; shared writer regressions already cover other migrated outputs.
- Reproduction: `tests.test_extract_publication` executes actual CLI/ribbon code with native APIs stubbed. All three regressions failed before correction because `write_extract` was absent; evidence: `out/laneB-extract-publication-before.log`.
- Control tier 1: define `extract_model.write_extract` using `safe_io.save_json` with the native ASCII serializer and route both entry points through it. The native launcher resolves the repository `src` directory explicitly. No model or generated extract is edited.
- Proofs: both entry points call the same writer and produce identical bytes for Arabic text, integer zero and the maximum signed 64-bit identifier. Injected serialization and disk-flush failures preserve the old extract and clean staging files. Focused publication/boundary/serializer suite: 24 tests, exit 0; `out/laneB-extract-publication-after.log`. This is portable source execution, not live native acceptance.
- Registry: `extract-publication-migration-missing` -> shared `write_extract` at both call sites and existing unconditional ribbon verification -> `tests.test_extract_publication` -> native output publication. Related `serialization-file-boundary-phase1` evidence above is historical; current controls are verified against this worktree. Updated `docs/serialization-boundary.md` distinguishes publication from outstanding native field-adapter wiring.
- Final Linux integration evidence for all three corrections (2026-10-05): explicit `/home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python` (Python 3.12.3), `PYTHONPATH=src`, `NO_COLOR=1`. Full `scripts/run_tests.py`: 713 tests in 165.900 s, exit 0, 13 existing skips; no new skips or weakened assertions. The earlier post-portability-only full run passed 710 tests in 164.812 s, exit 0. The increase from the lead's 623 includes restored render-standard discovery and eleven added regressions.
- Final `scripts/verify.py`: exit 1 solely for the absent installed Windows Revit family corpus. `scripts/verify.py --portable`: ALL PASS, exit 0; explicitly skips that Windows-only corpus while portable family-parser regressions run in the full suite. The other existing verifier omissions are the unavailable installed Revit photometry and downloaded-family integration inputs. The ribbon publication failure from the first verification is corrected; no remaining Linux code failures.
- Current evidence: `out/laneB-portability-suite.log`, `out/laneB-portability-verify-final-default.log`, `out/laneB-portability-verify-portable.log`, `out/tests-result.json`, `out/verify-result.json`. `git diff --check`: exit 0. Shared symlinks are unchanged; the shared luminaire database SHA-256 checksum before/after is `98bc3eb5d73a184c048abe465d1223738f514dfe7829c6cd8ec902e28be61010`. No shared-data edits, environment installs or commits. No live native-model acceptance claimed.

### pipeline-result-lacks-atomic-proof — pipeline stages lacked cryptographic proof of output freshness, completeness, and non-zero exit on failure
- Observed / found by: historical audit in `docs/lessons-audit.md` (lessons l0029, l0040, l0068, l0089, l0133, l0287) and lead render review 2026-10-01 (`villa-render-stale-scene` where `out/villa/render-d1/scene.json` was an old export from the previous day; downstream C2/C3 render runs consumed the stale scene while reporting QA passed). Found by lead inspection across Stages 5, 7, and whole-project verification.
- Reproduction: `tests/test_stage_result.py::StageResultContractTests` reproduces each real defect as frozen data cases without live Blender or Revit:
  1. `test_l0029_fail_verdict_refuses_zero_exit_and_clean_verdict_passes`: dict reports with `passed: False`, failure lists, text containing `VERDICT: FAIL`, and integer failure counts all raise non-zero `SystemExit`; clean reports return 0.
  2. `test_l0040_cached_stage_reused_after_input_change_fails_closed`: cached job result validated against modified input raises `StaleInputError`.
  3. `test_partial_output_set_reported_complete_fails_closed`: missing output or 0-byte output fails completeness check and raises `IncompleteOutputError`.
  4. `test_stale_scene_consumed_by_render_fails_closed`: render stage validates upstream scene stage result against current source code; modified source raises `StaleInputError`.
  5. `test_tampered_output_fails_closed`: modified output on disk raises `IncompleteOutputError`.
  6. `test_failed_exit_code_stage_refuses_consumption`: stage completed with `exit_code != 0` raises `FailedStageError`.
  7. `test_self_referential_record_path_filtered_and_pure_check_stage`: passing `record_path` in `outputs` is filtered out without hash cycles, and pure check stages pass cleanly.
- Direct cause: pipeline stages printed loose terminal text or wrote disconnected files without binding their outputs to an atomic record of the exact input content hashes, repository code provenance, output byte sizes and SHA-256 digests, and exit status.
- Escape: downstream consumers tested only whether a file existed on disk or whether an in-memory boolean was True, ignoring input changes, 0-byte files, and broken pipes. Scripts evaluated reports and printed "FAIL" but returned exit code 0 because CLI exit codes were not directly gated on report verdicts.
- Class: pipeline result lacks atomic proof.
- Siblings: all seven audited lessons (`l0029-script-printing-fail`, `l0040-three-unchanged-camera`, `l0068-fixtures-rendered-as`, `l0089-another-session-edited`, `l0133-open-right-after`, `l0287-slow-session-persist`, and `villa-render-stale-scene`).
- Control tier 1: one atomic stage-result contract module `src/archpipe/stage_result.py`. Every stage publishes a JSON result record via `archpipe.safe_io.save_json` with top-level `_metadata`: inputs' SHA-256 hashes and byte sizes, repository code provenance (`source_provenance` hash, git HEAD, git dirty state), outputs' SHA-256 hashes and byte sizes, exit code and status (`ok` or `fail`), and an evaluated completeness check (all expected outputs present and `size_bytes > 0`). Downstream consumers validate the stage record via `validate_stage_result()` before consuming outputs, failing closed with typed errors (`FailedStageError`, `IncompleteOutputError`, `StaleInputError`, `CodeDriftError`). Shared fail-closed helper `enforce_clean_verdict` / `fail_closed_exit` inspects reports, dicts, failure lists, and text, terminating non-zero directly.
- Phase 1 Migrated Stages:
  - Render driver (`scripts/villa_render.py`): publishes `villa-render.stage-result.json` across all view outputs, captions, and QA files; gates exit via `enforce_clean_verdict`.
  - Lighting measurement (`scripts/compare_lux.py`): publishes `compare-lux.stage-result.json`; gates exit via `enforce_clean_verdict`.
  - Revit spec/extract check (`scripts/check_bedroom.py`): publishes `check-bedroom.stage-result.json`; gates exit via `enforce_clean_verdict`.
  - Whole-project verify (`scripts/verify.py`): publishes `verify.stage-result.json`; gates exit via `enforce_clean_verdict`; adds unconditional learned guards for `report_has_failure` and `validate_stage_result`.
- Proofs:
  - `tests/test_stage_result.py` (7 tests, all passing, exit 0).
  - Unconditional guards in `scripts/verify.py` verifying `report_has_failure` and `validate_stage_result` on modified inputs.
  - Quiet cases verified: clean reports exit 0 without raising; untouched inputs and complete non-empty outputs pass validation.
- Registry: `pipeline-result-lacks-atomic-proof` -> `stage_result.write_stage_result`, `stage_result.validate_stage_result`, `stage_result.enforce_clean_verdict`, and unconditional `scripts/verify.py` guards -> `tests.test_stage_result` -> stage boundaries across render, lighting, Revit extract, and verification.
- Checkpoint / Phase 2: Phase 1 checkpoint reached. Phase 2 migrations pending lead approval: `scripts/villa_daylight_finished.py`, `scripts/thermal_job.py`, `src/archpipe/deliverables.py`, and `scripts/run_bedroom.py`.

### c4-finish-hosts-absent — fittings have material names but no finished host
- Observed: phase-1 inventory has 582 separate components without declared finished hosts. l0856's original handrail was at model y -28.611 to -28.581 m, behind the then-rendered -28.471 m wall. l0119's housing top was 2732 mm against a 2700 mm ceiling; actual clear void was never established. Evidence: `docs/c4-phase1-checkpoint.md`, `docs/c4-mounting-inventory.csv`, `tests/fixtures/c4-stair-phase1.json` (22 frozen pre-migration meshes and source hash).
- Found by / stage: client renders and lead review at Stage 7; should have been caught at finish/spec and fixture construction.
- Direct cause: local outline, wall-bound and emitter offsets replaced a finished-face contract. Escape: finish names had no thickness authority, hosts had no binding, and support/light checks did not measure signed fixing-plane error. Contributing factor: structural wall thickness was conflated with finish build-up.
- Class: components placed against undeclared building surfaces. Siblings: bathroom fittings, all wall lights, recessed/surface ceiling fittings, TV/shelves/joinery and trellis/climbers; related l0856, l0119, l0551, l0096 and l0692. Full inventory remains the sibling list.
- Control tier 1: `knowledge/finish-build-ups.json` is the sole lead-reviewed thickness record; `stair_mounting.wall_host`, `stairs.party_flight_r8` and `revit_spec` share the measured CAD datum. First candidate package applies 13 mm plaster and constructs 22 stair components from its face. Tier 2: `mounting.check_mesh` independently measures signed vertex distances with an explicitly assumed 1 mm model tolerance; missing hosts, unknown recessed housing/void, excess depth and stale face records fail. `scripts/verify.py` runs the whole-scene guard unconditionally.
- Reproduction / proofs: `SceneMountingGuard.test_frozen_l0856_not_current_export` and `test_frozen_l0119_reports_unknown_void_and_depth` freeze the actual recorded dimensions. The latter distinguishes missing historic void from the chosen 25 mm witness. Injected burial/proud geometry, missing host and unknown-depth siblings fail; reverse-normal wall and floor cases stay quiet. `StairFirstPackage` proves 22 candidate plane contracts quiet, preserves horizontal/elevation coordinates, and checks the shared datum on D1/D2/D3.
- Checkpoint / remaining: `out/c4-phase2a/stair-section-preview.png` is an inspected measured diagnostic, not photoreal approval. 23 movement rows await lead approval; whole-scene verification still fails on 560 unbound siblings. The structural shell also contains a partition/core return alongside the party wall; the plane contract does not prove finite host coverage there. Review actual host extents and native coordination before integrating or closing. No structural wall was moved to make a check pass. Bathroom, wall-light, ceiling and joinery/landscape migration remains open.
- Registry: `knowledge/mounting-guards.json`; workflow: `docs/ops/finished-surface-mounting.md`. Defects remain OPEN pending first-fix preview review, host-coverage coordination and remaining migrations.

### c4-infinite-host-plane — a plane contract passed without wall coverage
- Observed / evidence: first C4 candidate had 22 correct fixing-plane offsets, but nine surface-fixing footprints lacked finite wall coverage. Stringers 00–06 cross the core return; bracket 04 straddles the ground-floor wall's lower edge; stringer 15 reaches 3.529 mm below the basement wall bottom. Evidence: `out/c4-phase2a/candidate-scene.json` and `tests/fixtures/c4-stair-host-coverage.json` (frozen unsupported stringer 04, supported sibling 08 and actual wall panels).
- Found by / stage: measured diagnostic-section review during first-fix checkpoint; should have been caught when resolving the host at construction.
- Direct cause: the host described an infinite plane. Escape: the new vertex projection guard proved face offsets but not finite wall presence; an existing wall-thickness transition made one datum insufficient to describe every fixing footprint. Class: an otherwise valid geometric mounting contract has no physical surface over its contact area. Siblings: every surface fixing at an opening, wall return, slab edge or ceiling edge; projected components also require their separately declared fixing/support parts.
- Control tier 2: `host_coverage_findings` checks back-plane vertices and their centre against actual exported finished host polygons, independent of the body's declared offset; `scene_findings` runs it unconditionally. This conservative check does not certify fixing capacity or containment across all holes. A complete native fixing/host check remains necessary. Do not add or move structural walls or change intended elevations to silence the finding.
- Reproduction / proofs: `SceneMountingGuard.test_frozen_actual_core_return_and_clean_sibling` fails on the actual first candidate by value, stays quiet on supported stringer 08, and fails when that sibling's host surface is removed. `StairFirstPackage.test_migrated_plane_contracts_quiet_but_core_coverage_fails` lists all nine actual contacts, distinguishes passing plane contracts from failed surface coverage, and proves the genuinely covered subset quiet. The control does not use D1 identifiers or coordinates.
- Checkpoint: construction remedy requires lead coordination of the core return and floor/slab edge. No layout correction is inferred from test failure. Registry: `knowledge/mounting-guards.json`. Status OPEN; first package is a candidate, not a completed migration.

### c4-view-retirement-index — deleting a camera shifted an ordinal review selector
- Observed / evidence: the full 691-test C4 run failed `ChosenViews.test_every_view_subject_matches_scene_content`; removing v14 made the ordinal slice at position 24 start at v26 and omit v25. Evidence: `out/c4-phase2a-full-tests-final.log` before the corrected rerun; the actual produced prefix list was v26 through v34.
- Found by / stage: full regression suite after camera retirement; should have been caught by the affected camera tests. Direct cause: a positional list slice selected views by their historical count. Escape: searches for the retired identifier did not reveal an ordinal dependency. Class: a stable entity is selected by mutable collection position. Sibling search: no other ordinal VIEWS/review slices found in `src`, `scripts` or `tests`; exposure fixtures were already migrated to v31/v32 by identifier.
- Control tier 1: the affected test selects the required v25–v34 view identities and explicitly requires their presence. Retiring or reordering earlier views cannot change membership; absence of an intended view still fails. Reproduction and quiet case: `tests/test_render_views.py::ChosenViews.test_every_view_subject_matches_scene_content` on the actual retired-camera scene retains all ten intended additions and their subject, level-camera, lens and exposure checks. The source-selection rule is recorded in `docs/ops/finished-surface-mounting.md`.
- Registry: `knowledge/mounting-guards.json`. Historical failure is retained in `out/c4-phase2a-full-tests-before-camera-selector-fix.log`; final tests are recorded in the C4 checkpoint.

### c4-bc-body-and-wall-edge - keep real collisions and finite edge failures visible
- Observed / evidence: the b/c proposal reveals the guest handset 8 mm and its hose 65.961 mm behind their finished wall plane, and guest sconce 03 beyond the end of its intended wall. Its centre is at model y -23.625 m; the finite wall ends at -23.591 m (34 mm overrun). Evidence: frozen pre-change geometry in `tests/fixtures/c4-bc-before.json`, `out/c4-phase2bc/proposed-scene.json` and the mounting report. Found during Stage 7 migration; should have been caught at fitting construction.
- Cause / escape / class: generated body envelopes and mirror-side placement were not tested against finite finished walls. A nearest-face search can select another room's wall or a closer door jamb outside the fixing footprint; flattening body vertices against a plane can produce a numerical pass by destroying the fitting. Siblings: handset heads/hoses, wall sconces at corners/openings, triangulated joinery-mounted plates, all surface-mounted bodies. The frozen handset regression caught the wrong jamb normal; host selection now ranks actual finite coverage before distance, both within a direction and between directions. Initial implementation also selected from an assembly centre rather than its back anchor and tried to mutate tuple vertices; anchors now use the authored back and proposals normalise vertex storage without changing retained meshes.
- Control tier 1: `fitting_mounting.measured_host` selects the intended room's measured source face and all its coplanar triangles. Host finish additions and item movements both obey the 5 mm authorization boundary. Only fixing ends may be shortened; handset/body geometry is translated intact. Child projections are relative to their declared assembly root. Tier 2: signed-plane and finite-coverage guards run on working and separate proposed scenes. The two design defects are deliberately not forced quiet.
- Proofs: `test_bc_pending_geometry_unchanged_small_moves_applied` compares all large moves with the frozen real meshes; valves move 3 mm. `test_bc_frozen_handset_and_wall_edge_are_not_silenced` proves the real findings persist, complete SWING plates stay quiet on their triangulated side-panel hosts, and the handset's proposed vertices are a rigid 23 mm translation toward model negative x (the correct wall normal). `test_bounded_movement_threshold_generalises` proves exactly 5 mm applies and 5.001 mm remains pending on an unrelated host. Registry: `knowledge/mounting-guards.json`.
- Stair follow-through: lead decisions 1-4 resolve the previous nine finite contacts. Model return plaster is derived from its 100 mm partition at model y -28.671 m, giving structural face -28.621 m and finished face -28.608 m. Stringer 06 steps at the actual return end, model x 6.940 m. Stringer 15 trims 3.529 mm to existing basement floor level -3.000 m. Coplanar stacked party-wall finish bridges only the 200 mm slab-edge strip; tests reject offset walls, different finishes (even equal thickness) and excessive gaps. All 22 stair components pass real finite hosts without structural changes.
- CHECKPOINT: b/c diagnostic previews are produced and inspected; they are not photoreal acceptance. Large b/c moves remain PENDING; ceiling and remaining joinery/landscape packages are deferred. These defects and the broader mounting migration remain OPEN. Repeatable procedure: `docs/ops/finished-surface-mounting.md`.


### c4-approved-move-clearance-recheck - approval geometry must reach the clearance engine
- Observed at the C4 resume checkpoint: applying 58 approved finish/fitting movements exposes a 777 mm guest wet floor against the authored 800 mm, and a drain extending 23 mm beyond the finished wet floor. The wider 700 mm basin approach also exposes a family-bath WC obstruction; the earlier furniture check used the 430 mm basin body width. Evidence: `out/c4-phase2d/clearance-results.json`, frozen b/c geometry and authored approval schedule `knowledge/c4-bc-approvals.json`.
- Direct cause: clearance and route checks consumed original furniture outlines, while finished-face corrections changed candidate meshes. Escape: the mounting guard measured fixing planes but did not rerun downstream working-space constraints. Class: a geometry approval invalidates cached or independently authored clearance inputs. Siblings: every sanitary assembly, fitting projection, wall finish, wet floor, drain and doorway; linked c4-finish-hosts-absent and c4-bc-body-and-wall-edge.
- Tier 1: `mounting_clearances.measured_items` carries measured sanitary displacement and full assembly bounds into conservative authored envelopes, with actual fitting projections and finished-wall strips as route obstacles. Obstacle-only items never become invented route destinations. Tier 2: `verify.py` unconditionally runs the affected-room review; missing drain installation requirements stay unresolved. Door checks retain existing conservative swing squares; route results use the existing 20 mm raster and circular path body, with achievable widths bounded in 10 mm steps.
- Proof: `test_real_clearance_failures_retained_and_movement_is_measured` proves the real wet-floor and drain failures fire, original-versus-approved sanitary positions differ, clean door/routes stay quiet, and unresolved manufacturer data is retained. These are OPEN design findings; no sanitaryware, wet zone, drain or walls were redesigned to silence them. The family-basin wider approach failure is a newly exposed pre-existing limitation, not demonstrated to be caused by the approved translations.
- Registry: `knowledge/mounting-guards.json`; workflow: `docs/ops/finished-surface-mounting.md`. Affected room clearance report is required at every subsequent sanitary/finish checkpoint.

### c4-bc-body-and-wall-edge - approved correction follow-through (2026-10-05)
- All 58 frozen schedule rows now apply only after identifier, host and before/after bounds match the authored approval record. A changed schedule fails closed rather than inheriting a broad approval. The separate guest correction translates the handset another rigid 23 mm after the scheduled 23 mm, leaving 15 mm signed body clearance (46 mm total from the original). Both translations retain body shape and elevation.
- `wall_safe_hose` constructs a hanging curve in the host's outward half-space with retained corrected handset and riser connections. The hose radius is 6 mm; the additional design clearance is 2 mm. Connection data and generated tube vertices are independently guarded. The measured nearest hose surface is 24.263 mm in front of the finished wall. The original hose/handset proposal still produces four findings in the frozen reproduction.
- The procedural sconce is a globe without a separate measured product back plate. A conservative fixing footprint uses its full 120 mm tangent envelope, not its single sphere tangent vertex. Sliding 99 mm along the same wall, with unchanged height/normal, leaves a stated 5 mm design edge margin. This clears the original finite-host finding; actual product back-plate specification remains unverified.
- Proofs: the frozen actual proposal has five findings; the three corrected components have zero. Rigid handset shape is checked vertex by vertex. Mutations of hose endpoints, path burial and sconce footprint fail. The hose construction also runs on unrelated x- and y-normal walls and rejects a buried connection. The generic 5 mm unapproved movement threshold remains unchanged.
- First-fix diagnostic images were generated and inspected at `out/c4-phase2d/guest-fixes-preview.png`; no presentation integration, photoreal acceptance, native rebuild or lighting probe proof is claimed.

### c4-sloping-ceiling-coordinate - signed coordinates must include the whole host normal
- Observed during package-d first-fix run: initial cinema ceiling proposals were incorrectly 653-694 mm because the assembly fixing coordinate used negative height while its actual ceiling normal was sloping. Frozen actual cinema trim geometry is retained in the b/c working scene and in the final movement schedule. Stage: candidate construction; caught before presentation integration by the independent signed-plane guard.
- Direct cause: a horizontal-ceiling shortcut was reused on a sloped host. Escape: earlier ceiling host data allowed only vertical normals, so horizontal-only assembly arithmetic had no sloped sibling. Class: a global coordinate is substituted for signed projection onto an arbitrary face. Siblings: cinema soffit, ramp batten mounts, any future sloped ceiling or fixing.
- Tier 1: ceiling assembly fixing coordinates use the full dot product with the measured host normal. Ramp batten upper ends are cut vertically to their own actual finite soffit polygons; body levels remain unchanged. Ceiling hosts accept downward unit normals and preserve missing void data. Tier 2: scene plane/finite guards independently measure the proposed vertices. `test_ceiling_unknowns_are_unresolved_and_small_moves_only` proves actual sloping proposals quiet except unknown recess data; current working cinema lens findings remain visible because six 9.021 mm moves are not approved.
- No void or housing is inferred from fixture height. Eighty building-ceiling recess roots are explicitly unresolved. Two nook downlights remain deferred to their actual joinery hosts in package e. Diagnostic ceiling preview generated and inspected; photoreal/native/lighting proof remains pending. Registry: `knowledge/mounting-guards.json`.


### c4-ceiling-host-render-contract - diagnostic hosts still need complete scene records
- Observed: the first full resume suite ran 699 tests and exited 1; two render-contract tests reported 99 missing mesh labels. Real reproduction: `tests/fixtures/c4-ceiling-label-before.json`, first candidate scene and `out/c4-phase2d-full-tests.log`. Found by full regression before integration; should have been caught by the ceiling host constructor/focused tests.
- Cause/escape/class: the new host constructor populated geometry/mounting fields but omitted the required presentation-scene label. Focused checks exercised mounting geometry, not the whole scene contract. Class: camera-hidden diagnostic records still share the exported scene schema. Siblings: every new ceiling/soffit host face, wall host record, future support diagnostic.
- Tier 1: `ceiling_host` constructs every diagnostic face with a named host-specific label. Tier 2: the focused ceiling regression runs `villa_render_contract.validate_scene` as well as signed-plane/finite guards. A frozen actual missing-label mesh and an independently stripped batten-host sibling fail; the complete candidate stays quiet. The check uses the general scene schema, not a D1-specific bypass. Reproduction/proof: `test_ceiling_unknowns_are_unresolved_and_small_moves_only`; registry: `knowledge/mounting-guards.json`.
- The same focused regression requires the existing b/c ceiling classification to contain only its original 10 parts; classification uses the stable package identity, avoiding mutation of original mesh references changing a historical subset. This previously inflated a first diagnostic report's b/c ceiling list to 210; final checkpoint reports 10 existing parts separately from 200 new d parts.
- Workflow: focused mounting validation includes the full scene contract before launching the full suite. Earlier failed full-suite log retained; final result is recorded in the checkpoint. No camera-visible integration occurred.

### c4-whole-access-zone-and-distance - lead follow-through (2026-10-05)
- Capture/reproduction: the retained d checkpoint reports 777 mm finished wet depth, -23 mm drain containment and a blocked 700 mm basin strip. `tests/fixtures/c4-lead-before.json` freezes the actual old wet-floor/drain meshes and table. The original WC side omission is visible in the historical table; the held original AD M Diagram 2.5, printed p.20, was re-read as an image before adding the missing 350/1000 mm side dimensions and 300 mm basin encroachment limit.
- Cause/escape/class: room-outline wet placement ignored finish thickness; clearance review checked fixture fronts and routes but omitted the complete access zone. A 135 mm basin-only slide would clear its strip while violating WC sides/shower approach. Siblings: all three bathrooms, compact fixtures, future same-wall layouts. Expanded review retains guest wide-side 899.510/1000 mm and parents narrow-side 310/350 mm failures, rather than silently exempting siblings.
- Tier 1: open wet floor is authored from the selected finished-wall build-up; the same floor rectangle owns the drain. Shower-head wall locations remain retained. Tier 2: actual generated wet-floor bounds feed the review, including strict positive WC/body separation. Generic WC side checks use both handednesses and the permitted rear-wall basin encroachment. Continuous necessary intervals prove both family slide orders impossible: 550 mm centre separation is required but only 280/295 mm is available. No family layout change is applied.
- Lead communication correction: subtracting the 23 mm translation from the old 117.653 mm diagonal separation gives an invalid 94.653 mm expectation. Measured post-move plan distance is 109.869 mm; horizontal gap is 27 mm. The independent rectangle-distance calculation was already correct. Class: confusing directional translation with change in diagonal distance; prevention is reporting directly measured axis and plan distances separately, not deriving a target from an expected subtraction.
- Proofs: `test_real_clearance_failures_retained_and_movement_is_measured` checks old real failures, exact rigid 23 mm floor/drain movement, new depth/containment/distances, measured sanitary positions, quiet routes/doors and drain requirement status. `test_full_side_clearance_blocks_partial_slide_and_generalises` retains the real family failure, proves both continuous orders fail, translates/renames the sibling geometry, rejects an obstructed unrelated WC zone and stays quiet on a clear zone/enlarged necessary interval. `test_evidence_values.py` re-reads all new side/encroachment values in the held original.
- Requirement separation: 95 mm fixed and 98 mm adjustable body heights come from selected manufacturer EULUMDAT line 15. The void requirement is 120/123 mm with a labelled 25 mm assumed cable/connector allowance. Trim-plane geometry is distinct from housing-depth capacity. `test_lead_ceiling_requirements_and_authority_fail_closed` proves missing depth, undersized void on horizontal/sloping siblings and authority drift fail, while sourced construction requirements stay quiet. Actual installation, driver/accessory and thermal instructions remain required; no as-built installation pass is claimed.
- Registry: `knowledge/mounting-guards.json`; workflow: `docs/ops/finished-surface-mounting.md`. Reviewed diagnostic preview: `out/c4-phase2d-lead/lead-decisions-preview.png`. No presentation/native integration, lighting acceptance, commit or package (e) work.

### c4-support-chain-contracts - remaining generated assemblies lack support contracts
- Capture: 300 sites in `out/c4-phase2d-lead/working-scene.json` lack hosts. Frozen real examples: `tests/fixtures/c4-e-before.json`. Found at C4 inventory before presentation integration; should be caught during assembly construction.
- Cause/escape/class: furniture generators describe body parts independently of building datums; earlier support checks did not export an explicit fixing chain. Above-floor child bodies cannot be certified by inventing their own floor offset. Siblings: all furniture roots and children, shelf contents, dressing supports, table lamps, joinery lighting, curtain tracks and boundary-wall trellises.
- Diagnosis checkpoint: bind independent roots to actual finished surfaces, preserve generated child projections relative to the root, and keep unknown construction data explicit. Floor build-ups are absent in the finish authority; use modeled levels, never an assumed oak/underlay stack. Larger corrections require approval.
- OPEN: first-fix and regression proofs pending package (e); native/presentation/lighting acceptance remains pending.

### c4-support-chain-contracts - first fix and sibling diagnosis (2026-10-05)
- Tier 1: `support_mounting` resolves furniture roots against actual modeled floors; generated children retain an explicit independent root and projection. Floor thickness is unverified and never added. Exact full-span floor edges remove the pantry shelves' 0.5 mm centre-rounding drift. Frozen pantry, family and boundary geometry is in `tests/fixtures/c4-e-before.json`.
- Siblings found by finite-host measurement: south trellis is 9450.320 mm from its actual boundary face; east/north/west intersect their boundary walls. Side brackets and shelf lighting also need corrections. Real boundary identifiers select actual walls; no wall is added at a trellis and no remote gap becomes an invented standoff. All corrections over 5 mm remain pending with original geometry retained.
- Tier 2: floor-bearing root contact receives the finite-polygon check; a generated child fails without an independent root. Rails name supporting brackets and require intersecting envelopes (necessary support evidence, not anchor capacity). Recessed nook roots use the actual joinery underside and the existing sourced housing/void requirement. Wall-marker hosts resolve but missing housing data remains a construction requirement.
- Authorized WC slides rerun complete room fronts/sides, wet geometry, door squares and routes; the family layout is unchanged. The continuous candidate calculation tests exact obstacle/required-gap events in both handednesses; no grid search hides a possible centre.
- First-fix diagnostic previews inspected: `out/c4-phase2e/support-first-fix-preview.png` and `wc-slides-preview.png`. Preview source faces come either from stored provenance or actual exported host patches; legacy stair hosts do not carry `source_faces`. Renderer/native/lighting proof remains pending. Imported replacements, cloth and attached props follow applied furniture translations; emitting assemblies carry analytical light positions with them.
- Proofs/registry: `tests/test_support_mounting.py`; `knowledge/mounting-guards.json`. Real missing sites fire; translated independent roots stay quiet; removed roots, displaced children, absent finite support, removed brackets and undersized nook voids fail. Boundary proposals remain unapplied; full-span correction is translation invariant. Focused run/exit evidence is recorded in the package-e checkpoint. Host-contract migration is complete only when those proofs pass; approval and installation findings remain OPEN.

- Final package-e proof status: all 22 existing mounting tests passed in the initial focused process; the final expanded support module passed all five tests, exit 0. The initial combined process exited 1 on a false geometry comparison using view-dependent shell ordinal IDs. Stable authored fixture/floor identity replaces that comparison; an independent comparison using the same actual view set proves zero changed family meshes and unchanged camera records. Final `verify.py` ran once, exit 1 only for 97 mounting messages on approval items and three family clearance failures; missing hosts are zero. See `docs/c4-phase2e-checkpoint.md`. Approvals and installation/presentation acceptance remain OPEN.

### c4-boundary-and-exterior-side - lead rejected remote and inward hosts
- Capture: lead review of retained `out/c4-phase2e/movements-over-5mm.csv` rejected 12 landscape and two external grille rows. Real frozen meshes and proposals: `tests/fixtures/c4-e-rejected-hosts.json`. South proposal was 9450.320 mm away; external grilles moved 223/213 mm into rooms.
- Cause: fence labels described whole-plot fences, not each finite yard edge; landscape search admitted 20 m distance. Grille mounting hard-coded the inward room normal. Escape: pending findings were documented without validating intended wall topology/side before proposing. Class: geometric proximity substituted for semantic host eligibility. Siblings: four trellis/branch/climber assemblies, both external extract grilles, corner/column-sized interior wall patches.
- Diagnosis checkpoint: declare yard-edge hosts from the modeled yard polygon; use modeled fence thickness where present and explicitly retain polygon inner-face datum where no wall solid exists. Require full finite fixing envelope coverage and maximum 300 mm authored-position travel. External hosts require room adjacency inward and no room outward. Rejected corrections remain unapproved.
- OPEN: construction fix and proof results follow in the new checkpoint.
- First fix: tier 1 `exterior_mounting` declares finite yard-edge hosts and selects complete convex fixing envelopes within 300 mm. Room adjacency selects exterior grille faces. Frozen authority applies 43 rows and retires two obsolete inward grille datum movements. The earlier statement that the south trellis was 9450.320 mm from its actual boundary was wrong: that number measured an unrelated whole-plot fence. The actual declared south yard edge requires 135.660 mm.
- Proofs: real south-to-west-fence reproduction and shifted unrelated boundary mutations are refused; 12 actual boundary placements resolve within 300 mm. Narrow/concave source mutations fail; actual complete faces stay quiet. Both real grilles choose the outdoor side; interior-only and added-outdoor-room siblings fail; translated/renamed rooms retain exterior selection. Frozen approval drift fails. `tests/test_support_mounting.py` compares unapplied revised geometry and separately evaluates the complete proposal.
- Sibling follow-through: hood support uses existing coplanar full wall faces with retained source provenance rather than a column-sized room-labelled patch. Approved headboard translation retains its real 47 mm finite-wall overrun; no wall extension is fabricated. This remaining support design finding stays OPEN.
- Registry: `knowledge/mounting-guards.json`; workflow: `docs/ops/finished-surface-mounting.md`. Focused exits, inspected preview and verify findings are recorded in `docs/c4-phase2f-checkpoint.md`. Revised proposals and installation/native/presentation acceptance remain OPEN.
- Final authorized Linux follow-through: all 14 revised exterior rows apply; headboard and coffee candidate geometry are corrected. Current candidate evidence is `docs/c4-final-linux-checkpoint.md`; installation/native/presentation proof remains pending. The retained package-f checkpoint describes the historical pending state.
- Approval follow-through checks preserve rigid assembly relationships: six coffee tray/spout/tank parts and one hood chimney follow the approved roots; eight bar-strip analytical records follow their fitting faces; six markers emit from their translated luminous mesh material. The carried-part regression compares every vertex displacement and emitter displacement independently. Independent lighting/native proof remains pending.
- Runtime escape during this round: the bare system `python` lacks the project Shapely dependency and `verify.py` stopped at import. Its exit 1 is retained as a failed start, not a geometric finding. The project `.venv/Scripts/python.exe` has the pinned dependency and completes verification. Use that interpreter explicitly for checkpoints, focused tests and verification; never infer the environment from historical bare-python setup notes.
- Diagnostic preview escape: fixed-size tangent plot limits clipped the 2024 mm north trellis. Preview limits now derive from complete before/after bounds; the revised image was inspected before checkpoint delivery.
- Carried-emitter first-fix failure: a generic name-prefix lookup assumed every wall marker had a separate analytical light and raised `StopIteration`. Real scene light inventory contains BACK strip records but no STEP/PATH records: the marker meshes themselves emit. Control uses the exporter?s actual emitter representation; the regression requires eight strip emitter moves and seven rigid appliance child moves, with markers handled by approved luminous geometry. Failed first-fix focused/checkpoint/verify logs are retained; final successful regressions and completed review are identified explicitly in the checkpoint.

### c4-approved-appliance-child-penetration - body-only fixing approval hides the lowest part
- Observed during approved-root follow-through: both coffee bodies move -10 mm in model z; their rigid drip trays move with them to -2.110 m against modeled worktop -2.098 m, 12 mm penetration. Real before/after child meshes are frozen by value in `out/c4-phase2f/mounting-report.json` and the retained package-e scene. Should have been caught at assembly support selection.
- Cause/escape/class: support datum was chosen from the inventoried body, omitting its lower tray. The child was not a mounting inventory site, so body-only contact passed. Siblings: both coffee machines, attached tanks/spouts, hood chimney, future attached parts.
- Tier 2: `scene_findings` checks every declared associated child against its root?s actual finished support half-space, without identifier exemptions. A tier-1 change to the whole assembly?s lowest fixing part would alter the frozen approved body pose and requires new lead approval; it is not applied.
- Proof: `test_joinery_recess_lights_and_support_siblings_fail_closed` retains both real 12 mm findings; a renamed child lifted to exact support stays quiet, and a new 20 mm penetration fires. Rigid child and emitter displacements are independently checked.
- OPEN: both approved positions and rigid geometry remain as authorized; installation pose needs correction after lead review. Registry: `knowledge/mounting-guards.json`; workflow requires complete assembly review before approving its fixing plane.
- Final lead authority supersedes the historical pose: both complete coffee assemblies lift 12 mm and retain all part relationships. Linux final mounting findings are zero; the frozen former penetrations still fire in focused tests. See `docs/c4-final-linux-checkpoint.md`; installed/native/render proof remains pending.

### c4-geometry-container-comparison - identical support coordinates counted as changed
- Observed: first delivery comparison counted three unchanged stair-floor diagnostic faces because in-memory points were tuples while the retained JSON used lists. Coordinates, polygon order and bounds were identical. Class: representation equality substituted for geometric equality; related to package-e view-ordinal comparison.
- Tier 1: checkpoint `geometry_diff` normalizes point containers before comparing coordinate values. `test_geometry_diff_compares_coordinates_not_container_types` stays quiet on tuple/list siblings and fires on an unrelated 5 mm floor-coordinate mutation. The regenerated comparison records 52 changed prior mesh records, zero changed family meshes and unchanged cameras. Registry: `knowledge/mounting-guards.json`.

### c4-final-rigid-assembly-and-panel-span ? final lead decisions
- Capture: retained package-f scene has two 12 mm coffee-tray penetrations and a 47 mm headboard overrun. Frozen by value in `tests/fixtures/c4-final-before.json`; final authority in `knowledge/c4-final-approvals.json`. Found at lead candidate review; assembly construction should have prevented the split/support error.
- Cause/escape/class: support selection used an appliance body rather than the complete attached assembly; ownership was inferred during one approval path rather than declared by the builder. The headboard used the structural room span before finite finished-wall coverage. Siblings: both coffee trays, spouts and tanks, hood chimney, wall panels on finite returns.
- Diagnosis checkpoint: bind attached parts at construction, translate through one assembly function, seat the lowest retained part on the measured worktop, and trim the panel about the unchanged bed centreline against a full-height source patch. Lead authorized all 14 revised exterior movements and these final corrections.
- Tier 1: `attached_assembly.bind/translate` owns rigid movement, replacing approval-time identifier inference. `final_mounting` seats the complete assembly and bounds panel width by its finite wall span. Automatic small corrections in `fitting_mounting.package` also carry attached parts, with a real coffee/hood regression; supplied package children are deferred to their own package iteration and never moved twice; the mixed-package regression proves this. Tier 2: unconditional split-movement detection joins `scene_findings`. No tolerance, wall, tray shape, camera or bed change.
- Proofs: `tests/test_final_mounting.py` freezes actual collisions/overrun, mutates parent-only translations of both coffee bodies and the hood, keeps rigid siblings quiet, and translates/renames assemblies and panel supports. Final candidate must have no mounting findings and retain exactly three family-bath clearances. Focused process evidence and preview review recorded in the final checkpoint.
- First-fix API rejection: positive generated child projections cannot use `surface-mounted` (it requires zero offset). The construction now uses the existing projected-part contract, as `fitting_mounting.package` does; zero-projection tray retains surface mounting. The failed first focused run is preserved separately. The automatic-move follow-through also exposed the standalone `package` API: its threshold regression passes members separately with no scene mesh inventory. Attached-child lookup now treats that absent inventory as empty; `test_bounded_movement_threshold_generalises` retains both sides of the 5 mm limit.
- Installation/native/photoreal/lighting acceptance stays pending; this closes candidate geometry only after final verification.

### c4-plant-support-legacy-datum — stale check after measured support migration
- Observed in final C4 focused `test_render_standard`: `test_indoor_plants_have_integrated_pots_floor_support_and_clear_tv` reports support failures for lounge-plant, living-plant-table, living-plant, bedroom-plant and study-plant. Reproduced unchanged in retained package-f and final scenes: `out/c4-final-indoor-plant-baseline.json`.
- Direct cause/escape/class: `indoor_plant_violations` compares positions after measured support migration with authored `LZ` room levels and pre-migration furniture heights. All five support comparisons differ by +2 mm; floor plants have measured finished support at -2.998 or +0.002 m, and the table plant is at -2.598 m. The legacy check still expects -3.000, 0.000 and -2.600 m. This is a stale datum check, not evidence to lower the plants. Siblings: post-migration props on floor or furniture; related `c4-support-chain-contracts`.
- OPEN: no plant geometry or tolerance changed. A future fix must compare against actual scene support geometry and prove both real clean cases and sunk/moved support mutations, retaining the existing placement/route checks. Captured for the lead rather than silently exempted.
- Reproduced again on Linux, unchanged in reconstructed package-f and final scenes: `out/c4-final-linux-indoor-plant-baseline.json`. Focused render/lighting modules pass 72 of 73 tests, exit 1; the sole failing test is this known stale-datum check.
- Final C4 test expectations also needed updating: whole-scene mounting findings are now empty, and exterior grilles fix with their minimum model-y face at the facade, projecting 12 mm outdoors. Frozen bad mounting cases and exterior-side mutations remain active.

- Lead diagnosis (Linux, 2026-10-05): commit `4245c7b` added package-e `support_mounting.migrate`. The existing `villa_render` floor constructor already emitted faces at room level plus 0.002 m; migration seated floor plants there and raised the coffee table (and its plant) by 0.002 m. No new floor thickness is inferred. The table plant also copied the table child's floor-bearing mounting contract instead of recording its actual tabletop contact. The original guard ran inside `props` before migration and was never rerun after it; its final-scene test exposed the stale authored levels.
- Found by / stage: focused render regression, then lead review; should have been caught at post-migration scene construction. Class: dependent placement and validation keep authored or parent-root datums after physical supports move. Siblings audited: all five indoor plants, four floor supports and the coffee-table top; imported models/cloth and other props retain their existing carried-movement guards. Related: `c4-support-chain-contracts`, `indoor-pot-support-tv`.
- Frozen reproduction: `tests/fixtures/c4-plant-support-before.json` holds all five actual plants and six physical source meshes by value. `test_c4_frozen_plant_support_datums` first reproduced all five failures (exit 1; `out/c4-plant-support-reproduction.log`), before the source change.
- Control tiers 1 and 2: `plant_support_face` selects the finite upward face of the explicitly named floor/furniture support; plant migration seats and binds directly to that face, rather than inferring an enclosing assembly or copying its floor contract. `plant_support_findings` compares base and recorded datum with live physical geometry. The final builder reruns the pot/support/TV guard with the scene; `mounting.scene_findings` invokes the support check unconditionally, including from `verify.py`. Migrated props without scene geometry fail closed. The 1 mm tolerance and all visible geometry are unchanged.
- Proofs: the frozen real table-root contract fires; clean rebindings stay quiet with unchanged positions. Every plant fires on a 2 mm sunk base, moved/removed physical support and stale-record mutation. Translated/renamed room, furniture and floor siblings pass, then an injected 2 mm base defect fires. Pot and television-corridor failures remain guarded. First-fix focused modules: 67 tests, exit 0 (`out/c4-plant-support-first-fix.log`). `out/c4-plant-support-source-proof.json` confirms identical visible mesh geometry and all five plant positions. No visible change requires a new presentation preview; existing render acceptance remains pending.
- Registry: `knowledge/mounting-guards.json`, lesson `c4-plant-support-legacy-datum`. Workflow and canonical villa-render skill updated together; synchronized adapter regenerated. Candidate source defect fixed; full execution results follow in the lead checkpoint, without closing native/render gates.

### c4-linux-library-paths — transferred index paths prevent Linux verification
- Observed: Linux `verify.py` and focused scene setup fail before review because the transferred index stores `iguzzini\\LSEVO-AAK3EW\\LSEVO-AAK3EW.ldt`. Evidence: initial `out/c4-final-linux-verify.log` and focused logs; frozen selected-product path fields in `tests/fixtures/c4-linux-library-paths.json`. Found during workstation continuation; should be prevented at index serialization and reading.
- Cause/escape/class: `str(relative_path)` serialized the importing operating system's separators; read APIs joined those strings directly to a native path. Earlier tests imported and consumed their own temporary index on the same operating system. Class: persisted relative paths acquire platform-specific filesystem meaning. Siblings: all indexed photometric files and Revit family folders consumed through `get` and `search`, including `install.resolve`.
- Diagnosis checkpoint: write index paths with forward slashes and normalize legacy separators at the common row-read boundary. Do not rebuild or modify the shared library, product files or selected photometry.
- Control tier 1: `rebuild_index` serializes relative paths with `as_posix`; `get` and `search` decode old separators through `_portable_row`, so photometric export and family resolution share the same portable boundary. The index remains unchanged during reading.
- Proofs: `LibraryTests.test_transferred_windows_index_paths_export_and_install_without_reindexing` fails before the fix on the actual frozen selected-product paths, exports all three siblings from temporary files after the fix, resolves their family folders, preserves database bytes and checks unrelated mixed-separator paths. Existing same-platform import/install tests remain quiet. Focused library module: 11 tests, exit 0. Registry: `knowledge/mounting-guards.json`; Linux delivery runs recorded in the checkpoint.

### 2026-10-05 — c4-finished-layer-bookkeeping-only (C4i diagnosis)

- Lead measured 51 unsupported islands on 9069c24. Bathroom fixing planes were 23 mm ahead of visible marble; every nonzero plaster/marble host is a sibling. Must be caught in scene construction.
- Cause: render bookkeeping rejection removed diagnostic fixing planes without constructing the finish assembly. Escape: finite mounting coverage accepted diagnostic geometry; it did not check the render building surface. Class: a correct finished datum without physical finish geometry.
- Control/proofs: C4i adds closed, opening-clipped solids from measured source polygons and a render-only finished-face distance guard; suppression of real layers reproduces the failure. Evidence and final results: `docs/c4i-report.md`.
- Three regression siblings: diagnostic source lookup used the render channel; frozen missing-label reproduction stopped replacing its target after channel migration; final authorized headboard/coffee changes lacked movement records and were compared with earlier approval poses. Preserve channel contracts and immutable movement history.
- C4i sibling probe found a partial-window clip: intersecting a keyhole at a window edge left a repeated slit and nonmanifold extrusion. The original real wall zones passed, but this class needed a polygon-topology repair before extrusion; add an opening-edge clip proof and reject disconnected clipped contours rather than silently exporting a partial solid.
- Final construction: 18 distinct solids; shared guest-WC/dirty-kitchen shell polygons are partitioned by finish zone, supplemental coplanar polygons are room-bounded, and already-finished stair faces are not offset twice. Exact source coverage replaces source faces without coincident interfaces. Tier 2 render-only guard rejects missing oriented finished surfaces within 2 mm; topology guard checks closed edges and outward winding.
- Proofs: real construction suppression yields 51 unsupported islands and 52 missing render-surface mesh IDs; clean scene yields zero of either. Keyhole windows, opening-edge notches, reversed normals, translated geometry, removed faces and reversed winding are tested; disconnected clips refuse before export. Rail/bracket contact uses actual rail-side triangles against the solid brackets: sampling only the rail's end-ring vertices falsely measured 22 mm separation despite the bracket crossing the rail side.
- Independent render-critic review accepts the neutral marble/bracket preview, with faint contact shadows and unchanged procedural faceting disclosed. The preview geometry matches the final candidate exactly. Results and retained logs: `docs/c4i-report.md`, `out/c4i/`. Native/presentation/lighting acceptance remains separate.

### 2026-10-06 — c4-sanitary-wall-relocation

- Capture: client chose east-wall family WC after the west-wall basin access strip intersected its pan. Frozen actual west assembly and host: `tests/fixtures/c4-family-west-before.json`; original three failed rows retained in `out/c4-family-east/before-scene.json` review.
- Cause/escape/class: historical sanitary layout put neighbouring bodies on one wall without constructing full access zones; body/front-only review missed the side and basin-strip requirements. A wall change also risks stale rotation, flush plate, host and native spec. Siblings: all sanitary assemblies and opposing-wall layouts; related `c4-full-bath-access-zones`.
- Tier 1: `sanitary_relocation.relocate` rigidly carries every generated member and rebinds via C4; current layout and native parts share one pose, with explicit historical input scope for frozen mounting approvals. Measured east host must match current pose. Tier 2: full review retains enclosed-shower obstacles regardless of their low height and checks wet-zone non-intersection. No soil-stack or concealed cistern shape invented; services coordination pending.
- Proofs, inspected diagnostic preview, focused exits and remaining native/render evidence are recorded in `docs/c4-family-east-report.md`.

- First proofs caught two assumptions: native pan/seat are separate boxes while the render body combines them; open level-access wet floor cannot be treated as an enclosure under the existing overlapping-zone guidance. Native assembly-union comparison and the open/enclosed distinction preserve real geometry and source applicability. The shower entry card is tested on its 1630 mm width and 780 mm clear-floor depth, not misapplied to interior depth. First focused exit 1 retained; final 57-test process, 44-test furnishing/evidence process (one unavailable-original skip), four-test final relocation rerun, default support/openings two-test process, portable verify and checkpoint all exit 0.
### c4-lens-basis-missing-vertical — a low subject's lens constraint was reported as horizontal
- Observed: full-suite lead found `test_camera_24mm_level_at_eye_height` failing on v35: recorded horizontal need 17.2 degrees, below the 24 mm horizontal half-frame 36.87 degrees. Old camera: position [9.727, -24.971, 1.35], target [12.025, -26.899, 1.35], lens 16 mm. Evidence: `out/c4-family-wc-camera-before.json`, `out/c4-family-wc-lens-before.log`.
- Found by / stage: full regression after east-wall WC relocation; should have been caught at view selection and its focused camera-standard test.
- Reproduction: `tests/fixtures/c4-family-wc-lens-before.json` freezes the actual layout, furniture, walls, columns and specification by value, before the lens-report fix.
- Diagnosis: every searched 24 mm standing point misses the low WC top vertically; best point [9.627, -24.871] needs 28.14 degrees below level eye, beyond the 26.57 degree vertical half-frame. Zero fully framed 24 mm candidate evaluations; minimum vertical excess 1.57 degrees.
- Direct cause: chooser includes low subject height in its miss score, but the exporter reports only horizontal corner angle except for a guest-rain-head identifier special case.
- Escape: the lens-standard regression parses prose and assumes every other wider view failed horizontally. The explanation and assertion do not share the chooser's actual framing criteria.
- Class and siblings: lens escalation diagnostics omit a framing constraint. Every room-selected view can fail horizontally or vertically; the guest rain head is the existing upper-frame sibling, and ordinary low furniture is the lower-frame sibling. Related: `c3-part-boundary` and the historical v29 lens override record.
- A second real defect found during diagnosis: projecting the unchanged built pan and flush plate showed a bottom vertex 40.05 degrees below the old 16 mm camera's axis, beyond its 36.87 degree vertical half-frame. The former height test checked only the top, using radial distance rather than forward camera depth, and the view-plan script checked only horizontal footprints. Class: a subject's visible top is mistaken for whole-object framing. The WC kind, including renamed/translated WCs, is now checked from the same physical builder as the render; other furniture retains its existing framing contract.
- Control tier 1: `render_views.choose` returns measured horizontal/vertical constraints for every lens decision, gives fully framed candidates strict priority over aesthetic score, projects all WC vertices and refines failed whole-WC searches from 0.10 to 0.025 m. `villa_render.VIEWS` records structured `lens_basis` for both lenses without view-identifier branches and passes the intended eye height. Tier 2: `subject_mesh_frame_violations` checks the exported built WC against both image dimensions; `test_camera_24mm_level_at_eye_height` requires zero fitting 24 mm candidates, an exceeded actual constraint and all 16 mm constraints satisfied. No assertion threshold or fixture pose changed.
- Proofs: `test_frozen_east_wc_vertical_lens_need_and_whole_mesh` fires on the actual former clipping, stays quiet on the corrected camera, and fires on narrower-lens/wrong-aim/missing-mesh mutations. `test_whole_wc_search_generalises_to_renamed_translated_room` proves the same search with other identifiers and a 7 m / -4 m translation. `test_live_east_wc_is_wholly_in_frame` measures exported meshes. The existing guest rain-head regression is the upper-vertical sibling. The first translated-proof run exposed a test-harness assumption that all bath-fitting records had point coordinates; it now preserves non-point zone/line records and translates the point records consumed by the search.
- Checkpoint 2: inspected `out/c4-family-wc-camera-preview.png`, a diagnostic projection of actual unchanged WC meshes (not a photoreal render). New position [9.602, -24.846, 1.35], target [12.200, -26.346, 1.35], lens 16 mm, zero shift. Whole vertical need 36.62 degrees / limit 36.87; the refined 24 mm best needs 36.30 / 26.57. The fixed design is unchanged; presentation image review remains separate.
- Registry: `knowledge/mounting-guards.json` / `c4-lens-basis-missing-vertical`; workflow: `.agents/skills/villa-render/SKILL.md`. Final requested check exits and evidence: `docs/c4-family-wc-lens-report.md`.
- Final scope proof repeats the known coordinate-container trap if a JSON-frozen layout is compared directly with Python tuples. Normalizing serialization before value comparison proves every fixture-layout value unchanged; the 204 unique exported WC vertices are exactly equal to the frozen physical geometry. Evidence: `out/c4-family-wc-unchanged-design.log`; this comparison procedure follows the existing container-normalization guard rather than relaxing geometry equality.
