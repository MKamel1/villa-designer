# Bed intake and neutral review

Furniture phase step 1 keeps the existing layout dimensions. A model is an
appearance stand-in until manufacturer identity and specification are verified.
The client requested CC0, CC-BY with credit, or a documented permitted free tier.
C2 means the existing asset-intake control; C4 means finished-face mounting;
C8 means the existing geometry-topology review.

1. Prefer Poly Haven, then permitted downloadable Sketchfab models. Check
   robots.txt before accessing a source. Use the existing fetch script and
   an authorized stored token; never print/copy the token or enter a password.
   A missing authorized token leaves authentication-dependent candidates with
   the lead. A listing, face count or thumbnail is not measured geometry.
2. Measure the cached glTF through `scripts/measure_bed.py`. It reuses
   `asset_intake.measure_gltf_bounds`, `asset_intake.validate_entry`, and the
   existing exact triangle reader. Record bounds, actual triangles, position
   vertices, units, front/up axes, all buffer/texture hashes and licence/author.
   Intake disagreements stay failures; never normalize away a size mismatch.
3. Apply the client decision of 2026-10-08: source-size mattresses, with
   only source-declared unit conversion; no fit scaling. `fit_bed` needs each
   actual mattress and unchanged planned width/length. The tolerance is
   20 mm per mattress dimension. Parents require 1.600 × 2.000 m, kids A
   0.900 × 2.000 m for each berth, kids B 1.200 × 2.000 m. The frame may
   overhang and must undergo real-frame room checks. Whole-frame footprint
   and five-percent height fitting in the historical round-1/2 records are
   superseded. Missing or partial mattress geometry is refused; source
   bedding bounds and support platforms cannot replace a full mattress.
   `placed_bed_findings` checks uniform source scale and the unchanged
   mattress centre using actual imported vertices.
4. Preview each measured candidate in neutral light with a 1.8 m scale figure,
   then in its room from the existing camera. Disable material emission as
   well as design lights. Preserve the before image and bind receipts to actual
   geometry/material/cloth hashes. Require lead review before selection.
   Derive clipping, staging plane and diagnostic light from actual extents.
   Use a floor gap below the lowest vertex of the smaller of 5 mm and
   0.25 percent of the longest extent; this is diagnostic staging, not a
   physical tolerance. Every diagnostic emitter corner stays above the
   model and scale figure. Extreme source sizes need a separate labelled
   asset close-up alongside the figure view, without scaling the model.
5. Before activating a replacement, import it BEFORE cloth simulation; select
   its actual mattress/frame meshes as colliders and remove procedural bed
   geometry from the collision set. Derive cloth cut and starting height from
   actual mattress geometry. Keep the existing duvet material and drape.
   Whole models now import before simulation. Bed instances require
   `review_geometry` (actual converted faces and source-file hashes),
   `orientation_evidence`, and an accepted `neutral_review` bound to those
   same hashes and orientation. Exact native `measured_bounds_m` drive fit;
   conservative C2 accessor bounds remain separately labelled.
   `mattress_bindings.lower` and `.upper` each name real parts and record
   `head_at_max`, the measured head end along the existing world length axis.
   Never infer lower direction from upper direction or ladder/access side.
   `bind_model_cloth` / `mattress_cloth` derive each duvet cut from those faces;
   every real frame/mattress/source-bedding surface participates in collision.
   Hidden procedural parts are removed from the collision set. Bed decimation
   is disabled so reviewed and colliding geometry agree.
   `cloth_model_clearance` measures evaluated thickness/loft/subdivision
   crossings and enclosed vertices, refusing either defect.
   `scene_with_model_geometry` supplies transformed model faces to C8 and
   render_support. Geometry expansion is idempotent and source faces remain
   immutable. Legacy non-bed instances retain labelled conservative route
   envelopes, without a new exact-support claim.
6. Retain the procedural bed as the runtime fallback when a file is missing.
   Keep mesh `label` unchanged: it is also a camera subject identifier.
   `fallback_label` and `asset_status` provide the explicit stand-in disclosure;
   scene notes repeat it. Changing the identifier to prose broke built-subject lookup
   in the first actual preview and is covered by a frozen regression. The
   before/after camera records are identical; existing bed-bottom crops
   remain disclosed.
7. Check the complete furnished scene with C4/C8 support, routes, doors and
   swings; test lifted and obstructing siblings. Tests and a review receipt
   serve different purposes. Record rejected models and exact reasons.

Current diagnostic commands (use the specified project Python, with
`PYTHONPATH=src`; no package installation):

```text
scripts/measure_bed.py --asset sf_chelsea_bed --model /path/to/model.gltf --output out/beds/chelsea-intake.json
/home/omar/opt/blender/blender -b --python-exit-code 1 -P scripts/preview_beds.py -- --scene out/beds/scene-fixed.json --output out/beds/previews-after
scripts/run_tests.py tests.test_beds tests.test_villa_furnish tests.test_render_standard tests.test_render_views tests.test_geometry_topology tests.test_asset_intake
scripts/verify.py --portable
```

`preview_beds.py` preserves the current fallback geometry, cloth parameters,
room camera, and production glass setup; it creates no design light objects.
It holds the configured workstation graphics lock read-only by descriptor.
Its context scope is actual architecture and room furniture; curtains and
incidental props are omitted and disclosed. It also accepts
`--rejected-model /path/to/model.gltf` for a native-size rejection diagnostic.
Selection still requires a fitting, reviewed candidate; every round-2 model
fails the current real-size mattress rule. The importer capability proof is isolated and does
not change that decision.


Round-2 reproducible operations:

```text
/home/omar/opt/blender/blender -b --python-exit-code 1 -P scripts/prepare_bed_geometry.py -- --models /path/to/model.gltf --output out/beds/round2/geometry
scripts/bed_axis_evidence.py --geometry out/beds/round2/geometry --output out/beds/round2/axes-measured.json
/home/omar/opt/blender/blender -b --python-exit-code 1 -P scripts/preview_beds.py -- --scene out/beds/scene-fixed.json --candidates out/beds/round2/candidates-corrected.json --output out/beds/round2/candidates-preview-corrected
/home/omar/opt/blender/blender -b --python-exit-code 1 -P scripts/check_bed_import.py
scripts/run_tests.py tests.test_beds tests.test_bed_models tests.test_villa_furnish tests.test_render_standard tests.test_render_views tests.test_geometry_topology tests.test_asset_intake
scripts/verify.py --portable
```

Use the environment-specified Python interpreter, `PYTHONPATH=src` and
`NO_COLOR=1`; judge tests and verification by process exit status. The lead
owns the full suite. `check_bed_import.py` serializes on the existing graphics
lock. Its mechanical control uses rejected Scandi geometry at its own
envelope and mocks only registration inside the test harness; production
intake/review gates are never bypassed. Retain the importer-proof JSON,
neutral image and failed attempts. Staging floor/figure height derive from
actual vertices, never rotated local bounding boxes. Measure signed native
end bands and welded pillow components with `bed_axis_evidence.py`, and
record unresolved semantic directions explicitly. Reviewer interpretation
is still required for style, stains and missing functional parts.

Round-4 source-size intake is reproducible without changing any source:

```text
scripts/recheck_beds_round4.py --recipes docs/beds-intake-round4.json --geometry out/beds/round4/geometry --output out/beds/round4/recheck.json
/home/omar/opt/blender/blender -b --python-exit-code 1 -P scripts/preview_beds.py -- --scene out/beds/round4/scene.json --candidates out/beds/round4/candidates-preview.json --output out/beds/round4/candidate-previews-final
```

The authored recipe names actual mattress meshes or reviewed frozen connected
components, with expected vertex counts. Source hashes are rechecked before
measurement. Component-only identification inside a fused mesh is diagnostic;
activation still needs proper production bindings and accepted neutral review.
Two round-4 candidates have no independently identified full mattress: they
remain refused, and partial exposed geometry/frame boxes are reported separately.
Rejected candidates never run fictitious in-room C8 or replacement cloth checks.
