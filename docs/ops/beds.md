# Bed intake and neutral review

Furniture phase step 1 keeps the existing layout dimensions. A model is an
appearance stand-in until manufacturer identity and specification are verified.
The client requested CC0, CC-BY with credit, or a documented permitted free tier.
C2 means the existing asset-intake control; C4 means finished-face mounting;
C8 means the existing geometry-topology review.

The shared scaling/unit/contents implementation is now
`archpipe.furniture_fit`; bed APIs preserve their existing contracts and
bed-specific datums. See [furniture-fit.md](furniture-fit.md) for desk/chair
intake, item-only screening and multiple required height datums. Shared
validators accept read-only mappings from C8 as well as ordinary dictionaries.

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
3. Apply **client decision 2026-10-09**, superseding the 2026-10-08 source-size
   rule after twelve refusals. `scaled_bed_fit` derives independent width and
   length factors from each complete measured mattress. Both must be 0.5–2.0;
   the larger divided by smaller minus one must not exceed 15%. Match parents
   1.600 × 2.000 m, kids A 0.900 × 2.000 m per berth, kids B 1.200 × 2.000 m
   exactly with one mattress/bedding transform. Source-unit conversion stays separate.
   Derive vertical scale independently from retained frame bottom and design
   mattress top (round 6 kids A uses the upper top); cite the procedural source and label authored assumptions.
   Record resulting headboard height and the bound/basis. Record every bunk top:
   matching the lower cannot silently replace the upper datum. Bed-only contents
   require reviewed separate omissions; fused extras refuse. Missing/partial
   mattress geometry still refuses. `real_size_findings` and source-size
   `fit_bed` calls are retained only to reproduce historical rounds and controls.
   Current scaled contracts use `scaled_model_fit`; do not reuse an old accepted
   receipt. `villa_render.build(bed_replacements=...)` admits explicit reviewed
   models only after fixed placement, every design berth height and real-frame
   C8 checks. Keep fallbacks when those gates remain closed.
   **Round 6 client decision, 2026-10-09:** classify every retained mesh as
   frame, mattress or bedding; scale frame parts alone in plan about the actual
   source mattress centre. Record converted source X/Y factors separately from
   mattress width/length factors. `slim_frame_fit` enforces a minimum 0.5 frame
   factor and derives no more than 50 mm side/foot extension, 100 mm at the head.
   The mattress 15% proportion rule stays unchanged and is not imposed on the
   frame. Refuse visible frame distortion at neutral review. `slim_frame_findings`
   measures actual faces after transformation and Blender read-back, independent
   of predicted edges. Snapshot the classification and factors with the review.
   Proposed room geometry may be measured after a frame-factor refusal, but
   `require_bed_geometry` refuses its import even in neutral mode. For kids A,
   derive vertical scale from upper design top, report lower top and clearance;
   both authored berth heights must still pass before activation.
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

Round-5 scaled operations (all source library files remain immutable):

```text
scripts/prepare_beds_round5.py
/home/omar/opt/blender/blender -b --python-exit-code 1 -P scripts/check_scaled_beds.py -- --output out/beds/round5/importer-cloth-proof.json
/home/omar/opt/blender/blender -b --python-exit-code 1 -P scripts/preview_beds.py -- --scene out/beds/round4/scene.json --scaled-models out/beds/round5/models-pending.json --beds pb-bed ka-bunk kb-bed --output out/beds/round5/previews --samples 32
scripts/run_tests.py tests.test_bed_scaling tests.test_beds tests.test_bed_models
scripts/verify.py --portable
```

Generated semantic face selections are reproduced in the importer without
changing source faces or material assignments. Pending imports are admitted
only in explicitly neutral diagnostics. A cloth refusal writes evidence;
raw source bedding may be previewed with the refusal disclosed, but the
preview script must exit nonzero and cannot certify physical cloth acceptance.
Start cloth above real retained surfaces over its cut, partitioning lower-bunk
initialization from overhead surfaces at the midpoint to the upper underside.
Keep every collider; verify lower evaluated cloth cannot enter the upper berth.
Containment uses closed connected shells with three independent ray directions;
open-shell negative-side points or inconsistent rays refuse as unresolved.
The exact surface-crossing and 0.1 mm numerical thresholds are unchanged.
Snapshot selections by deep copy, including contents, factors, placement and
actual geometry digest. Record room crops honestly; never change the existing
room camera or furniture to make a candidate pass.

Imported-bed headings anchor only across the measured mattress width. Their
heights use the retained source envelope over one grid-cell ring (the
neighbors used by subdivision), plus the existing 4 mm collider and 4 mm
cloth offsets. Inset sheets start on that support envelope; hanging cuts keep
their free collision-safe plane and anchor only the supported heading. A
point-only ray anchor on wrinkled bedding can leave adjacent subdivided
faces intersecting it. Record the construction shape and actual anchor gaps;
the envelope is conservative support, not exact contact. Bind throws to the
real mattress and already evaluated duvet; retain the authored throw cut and
require its own evaluated clearance record against both. Missing duvet
support refuses. No evaluated crossing, enclosed or unresolved vertex can be
hidden by a successful importer/fallback result. Review the new neutral
images before any integration claim.

`scripts/review_beds_round5.py` regenerates both per-bed room reports and
achieved-versus-design mattress heights from the unchanged scene. A
diagnostic report can complete successfully with `activation_allowed: false`;
`integrate_bed_models` enforces the room and every-berth height gates.
The indoor boundary query is unconditional for every retained bed part,
including source bedding, against its full room-cluster union. Joined rooms
do not waive containment; a concave union cannot be checked only at corners.
`bed_room_boundary_findings` reports conservative outside plan-bound area
versus zero and keeps all source parts. This is a bounds screen, not an exact
solid-penetration measurement.

Choose focused test module names from existing files (`rg --files tests`)
before launching. `run_tests.py` uses a fresh loader and refuses any collected
selection/import error before executing valid suites, recording exit 1 and
zero tests executed. This also covers discovery-time imports; dependency
preflight failures still exit 2. Passing valid tests cannot erase a malformed
selection. Preserve the failed invocation separately and rerun the corrected
selection, judging the actual process exit status.

Round-6 reproducible operations:

```text
scripts/prepare_beds_round6.py
scripts/review_beds_round5.py --models out/beds/round6/models-proposed.json --output out/beds/round6/c8-complete.json
/home/omar/opt/blender/blender -b --python-exit-code 1 -P scripts/preview_beds.py -- --scene out/beds/round4/scene.json --scaled-models out/beds/round6/models-previewable.json --beds pb-bed ka-bunk kb-bed --output out/beds/round6/previews --samples 32
scripts/run_tests.py tests.test_bed_slim_frames tests.test_bed_scaling tests.test_beds tests.test_bed_models tests.test_bed_clearance tests.test_furniture_fit
scripts/verify.py --portable
```

`models-proposed.json` includes ineligible proposals for diagnosis;
`models-previewable.json` admits only eligible mattress/frame geometry and
does not waive room, cloth or visual gates. A preview exit 1 remains a failure,
even if diagnostic images were written. Keep those images and refusal receipts;
review them as evidence and retain the fallbacks.

Round 7, lead/client decision 2026-10-09: use the identical fixed-room review
on the CURRENT procedural item as well as the proposed retained model.
Consume the builder's `authoring_room_context`; freeze and include evaluated
procedural duvet/throw geometry from neutral previews. Missing generated soft
goods are an incomplete physical baseline. A model must not worsen any
access side by more than 5 mm, add a route/swing/storage-front failure or a
fixed-element body conflict, or enlarge boundary overrun. Keep inherited
findings in the report. `integrate_bed_models` requires the evaluated baseline
and selection-bound passing cloth for every soft good; an empty absolute
finding list alone cannot activate an un-compared bed.

`frame_slimming.head_depth_m` and `side_extension_m` may tighten the existing
100/50 mm maxima down to zero; recompute measured factors and neutral review
bindings after any change. This does not waive retained-bedding checks or
authorize omitting a source mesh. The current parent proposal has zero head
extension and zero permitted side extension, retains all source meshes, and
still refuses because source Object_6 bedding adds fixed-element overlap
screens absent from the procedural baseline. Kids fallbacks remain unchanged.

Cloth spatial indices use local query coordinates and each straight ray
counts a planar source triangle at most once. World geometry never moves.
The real parents throw previously counted one triangle twice due to
single-precision advancement at distant coordinates. Exact crossing,
closed-shell containment, open-shell and unresolved refusals retain their
existing tolerances. `scripts/prove_bed_ray_precision.py` proves the real,
translated, outside and enclosed cases in Blender; neutral previews then
prove the complete generated duvet/throw.

Lead decision 2026-10-11 permits omitting complete connected source quilt/throw/blanket components only when frame/mattress triangles remain identical. Generated cloth still derives from the actual mattress. `prepare_furniture_oct11.bed_without_source_covers` partitions exact source face indices, preserves every face in the measured receipt, omits only reviewed complete covers, and recomputes retained bounds. Retained source pillows need their own relative room pass. Fused mattress/frame bedding remains refused. `knowledge/parents-bed.json.gz` binds accepted source selection, baseline evaluated cloth, physical-cloth records, current room inputs, credits and unchanged v22 before default activation after measured furniture.

For every neutral preview invoke Blender with `--python-exit-code 1`; Blender otherwise may return zero after a Python exception. Evidence files and bound fresh images remain required. A stored relative bed review can be reused only under identical room inputs, model selections and evaluated-baseline hash; authored cloth specification and reviewed camera bindings remain independent gates.
