---
name: villa-render
description: Take a furnished, lit villa layout (any design option, villa or furniture set) to authentic photoreal renders at the bedroom standard (ADR-0013). Use for whole-villa render sets, adding furniture types or views, and whenever a villa render looks fake or wrong.
---

The standard is the bedroom image `bedroom-overcast-door.png` and its ten parts
([ADR-0013](../../../docs/decisions/ADR-0013-presentation-renders.md), with
both 2026-09-27 amendments). The client wants images that are
indistinguishable from photographs **and** show what would be built: no
retouching, no guessed exposure, nothing added that is not labelled. Read
the D1 rows at the end of [lessons](../../../docs/LEARNINGS.md) before
starting; every guard below exists because a real defect reached a client.
For single-room diagnosis and the order of causes, use `photoreal-render`.

## Inputs (all checked before rendering)

1. Layout and structure (`villa_r11.design`, `revit_spec.build`).
2. Furnished layout with checked footprints (`villa_furnish.layout`,
   `villa_furnish3d.spec`); Gate A passed.
3. Lighting design with verified products (`villa_lighting.design`,
   `bind_products`) and its carded task points.
4. Finishes schedule: each finish a **stated base colour and reflectance**
   (`villa_render.M`, `FINISH`). If none is given, assume one, label it
   ASSUMED in the scene notes. Every surface is finished, exterior and fence
   included.

## Order

1. **Export the scene**: `villa_render.write()` → `scene.json`.
   - Scene build uses tracked inputs. Walking-envelope asset triangles come
     from `knowledge/asset-route-geometry.json.gz`, not the build machine's HOME
     or the render library. On the render host, measure new/replaced landscape
     assets with `PYTHONPATH=src python scripts/generate_asset_route_geometry.py
     --library-root /path/to/library --assets <asset ids>`; this updates both
     the compressed record and manifest source/buffer hashes. The tracked
     `knowledge/asset-route-policy.json` records admissible scale ranges and
     the walking-height margin. Keep exact triangles intersecting that native
     band with original face order, winding and connectivity; never hull or
     decimate walking triangles. Framing uses only unrounded full-height 3D
     convex-hull vertices. The policy declares route coordinate precision:
     frangipani stays lossless for micrometre translation; other assets admit
     at most 1 mm scene grid steps (0.866026 mm Euclidean rounding error).
     Do not relax collision tolerances. Keep the gzip record below 1.5 MB;
     generation and portable verification enforce this budget. Compare
     hull-only and all-vertex results with
     `scripts/generate_asset_framing_proof.py --library-root /path/to/library
     --check` for real assets. Measure bytes, before/after counts and errors. Upright uniform scales
     are required except the recorded axiswise bench exception. Scales or
     walking tops outside coverage fail closed; widen the policy and regenerate
     instead of extrapolating. Review the policy, record and manifest together.
     Missing or stale records stop build even for nonoverlapping props.
     Run `tests.test_asset_route_geometry` and portable verification
     with HOME pointing at an empty directory before returning the package.
   - Shell faces are classified by their real normal, not by tags.
     Ground-only finishes cannot occur on downward faces (normal z < -0.7,
     where z is vertical). Closed ground solids carry mineral substrate on
     their undersides using explicit per-face slots, preserved by Blender.
     At ground-level soil beds, retire the architectural paving cap at the
     actual bed boundary using `villa_landscape.reveal_ground_soil`; never
     raise soil to hide a competing finish. Contract and portable verification
     run `garden_render_review.soil_visibility_findings` against real faces.
     Review the bed in architectural context after its isolated preview.
   - Procedural basal plants identify actual leaf faces and the root-soil
     datum. `garden_render_review.plant_form_findings` measures foliage,
     separately from stems; the authored maximum foliage gap is 0.20 m.
     Preview the real plant form as well as checking the gap.
     A species label, a token basal leaf or flower presence does not establish
     likeness. Species-specific builders use measured leaf surfaces and
     attachment geometry; dwarf mounds fill the low crown continuously,
     hanging racemes clear timber, and lounge furniture carries separate
     thick seat/back cushions. `garden_g6.appearance_findings` supplements
     support and envelope checks. Preserve the rejected real geometry and
     regenerate neutral comparisons with `garden_g6_preview.py
     --reference-receipt` to keep the same staging, camera and scale reference.
     Independent image review remains required after construction checks.
     Species-specific forms also require botanical structure and physical
     continuity: continuous palmate leaf surfaces, distinct fan nodes and
     physical petioles joining ivy leaves to training stems. Use
     `garden_shade.form_findings` and `climber_placement.ivy_connection_findings`
     with the real rejected preview geometry frozen in a regression fixture.
     These checks prove authored construction, not photographic likeness.
     Climber coverage uses projected leaf-area union. State whether the
     denominator is the training envelope or the whole timber-frame rectangle;
     a percentage measured in one cannot be claimed for the other.
   - Furniture: generator pieces (`archpipe.furniture`) through
     `generator_rotation`; other types through `villa_furniture_detail`;
     boxes only where neither exists. Every vertex stays inside the checked
     envelope.
   - Duvets are cloth cut like the bedroom, a 0.26 m drop over the sides
     and foot on these low beds (the foot corners must clear the floor),
     starting on the generated mattress top beyond the pillows; coverage is
     judged on the mattress, not the footprint.
   - Fixtures sit on the surface actually built: the lighting design takes
     each recessed fitting's height from the finished ceiling above it (cove
     field, ramp soffit); `_seat_recessed_on_soffit` is then a CHECK that
     moves nothing. Pendant cords reach the real ceiling; markers are flush.
   - Views are declared by INTENT (room + subjects + state) and placed by
     `render_views.choose`: standing points 0.30 m off walls, 0.15 m off
     furniture and floor props, or in one of the room's own door openings
     (0.25 m clear of each jamb; entrance and garden doors excluded; a point
     in a door's wall band is a doorway point and that door is opened for
     that view only). Score, in order: every subject wholly in frame
     horizontally AND its top above the frame bottom (hard); WCs also project
     every vertex of the physical pan and flush plate vertically, with a finer
     standing-point search when the coarse grid cannot hold them; the main
     subject seen from its front; no piece within 1.0 m of the lens in view;
     no subject behind a wall; then how much of the room shows, depth and
     windows. 24 mm, level, eye 1.35 m (1.20 seated); 16 mm only where no
     searched standing point holds the subjects, recorded in `lens_basis` as
     structured horizontal and vertical needs/limits at both lenses, camera
     points, search spacing and count of fully framed candidates. Assertions
     check the failed 24 mm constraint and every successful 16 mm constraint;
     never infer the reason from a view identifier or parse caption prose. Exteriors
     and the stair keep authored, level cameras (lens shift, never tilt).
     Exterior garden cameras stand inside the measured yard polygon
     and outside all architectural overhead cover. Through-door/window
     cameras declare `standing_room`, which must contain the camera on the
     same level; these use the existing 0.15 m interior clearance. The yard
     polygon alone does not establish open sky: report roofed strips and
     actual overhead cover separately, using the camera's garden storey.
     Swing motion envelopes include the
     measured fence/wall thickness, rather than trusting the outer yard line.
     Foreground opening frame members
     must avoid the image's central third. Contract, plan review and portable
     verification run the garden checks recorded in
     `knowledge/garden-render-guards.json`.
     Include procedural ground foliage and feature stones in lens clearance,
     just like imported props and top-garden planting. Landscape candidates
     also check the full physical door passage with `blocked_openings`, not
     only the authored path strip. Street-based client garden names and
     true-north solar bearing have separate roles; keep legacy identifiers
     until an explicitly scoped migration.
     Presentation retirement is explicit: record `presentation_retired` and
     its `presentation_decision`; both review/all batches and the review page
     exclude it while explicit diagnostic view requests remain available.
     A lead-approved natural screening allowance must be keyed by one exact
     subject in `visibility_allowances`, bound to its view identifier, with
     sample count, minimum visible rays and reason. Other subjects retain
     seven of thirteen rays; copied or invalid allowances fail closed.
     Never lower global visibility or QA limits to accommodate a local decision.
   - Exposure is metered per view and LOCKED per state across the whole
     set: `day`, `evening`, `exterior-dusk`, `exterior-day`. Rendering a
     subset re-meters that subset, so a state's lock is only comparable when
     the whole set (or a state rendered alone) is rendered together.
   - Rooms without daylight (a windowless corridor) use the lamp white
     balance; bathrooms and basement rooms by day have their lights on,
     stated in the caption. Never correct a physical cast in camera.
2. **Guards, locally, before the workstation** (all must pass):
   - `tests/test_render_standard.py`: lens and camera, set-metered
     exposure, cloth and its cut, smooth paint, construction details,
     generated pieces facing the plan, render contract, **nothing floats**
     (`render_support.unsupported`: exact contact, keyhole-safe
     triangulation, only the building grounds a group), **openings
     passable** (`render_support.blocked_openings`), appliances and fittings.
   - Nonzero finished host datums require physical `finish-layer-` solids,
     not diagnostic host/support planes. `finish_layers` preserves complete
     source wall contours and openings, partitions shared shell polygons by
     room where finish assemblies differ, and replaces covered source faces.
     Verify render-only finished-face distance and closed outward winding;
     prove both on the real scene with finish construction suppressed.
   - Indoor plants bind to the actual upward face of their named finished
     floor or furniture support after mounting migration. Check exported
     positions with `indoor_plant_violations(props, layout, scene)`; authored
     room levels and furniture heights are only pre-migration inputs.
     `scene_findings` also checks live support geometry and recorded datums.
   - `tests/test_render_views.py`: facing, looming, occlusion, height,
     door-band rules, each proven on the draft that broke it.
   - `scripts/villa_render_views.py`: whole subject in frame (built WC vertices
     horizontally and vertically, including lens shift), clearances,
     doorway doors opened.
   - `tests/test_villa_lighting.py`, and the render report must carry
     `qa_scene` so every render_qa check runs (none silently skipped).
3. **Draft**: `scripts/villa_render.py --views review --samples 256
   --res 960x640` (`review` skips `final_only` and retired views). Every final-only
   view needs one draft of its own before the final set. `render_qa` runs
   on every view; then look at every image next to the bedroom reference,
   and let a `render_critic` pass (a cheaper model is fine) list defects,
   each checked in code or data before acting.
4. **Diagnose from data, not impressions.** A colour cast: read the linear
   EXR and the textures' mean colour before touching the camera. An odd
   object: ray-cast the pixel to its mesh id. A "plain wall outside": ray-cast
   the window (the D1 study window showed open sky, a context gap). Fix the
   cause in the spec or exporter, add the guard, prove it on the real defect,
   record it in LEARNINGS.
5. **Re-measure lighting in the scene** after any fixture or furniture move
   (`--views none --measure-lighting`); a lamp base, an appliance or a hood
   on a task point shows up here and nowhere else.
6. **Finals**: `--views all --samples 1024 --res 1920x1280` (retired views excluded); if the driver
   loses the job, rerun the identical command to resume it. Then the review
   page (`scripts/villa_review_page.py`: QA flags explained per view state,
   decisions awaiting the client) and publish.

## Extending

- **New furniture type**: a builder (local frame: x across, +y front, z up,
  millimetres, verified primitives), named parts mapped in
  `villa_render.part_material`, inside the envelope, orientation test.
- **New view**: declare room, subjects and state; let
  `render_views.choose` place it; never hand-tune a camera to hide a
  problem. If the subjects cannot fit, choose honest subjects and say what
  is out of frame in `caption_notes`.
  Projecting a bed footprint inside the frame does not prove all corners
  visible: measure camera-to-corner sightlines and disclose unavoidable
  window-frame screening. Carry shared authored-appearance and photographic /
  procurement limits into every related caption; scene metadata alone is
  insufficient when a caption names a species.
- **New finish**: stated colour + reflectance; textures supply pattern only
  (per-channel mean matching). Check the tint survives in the final image
  (the first grey-green exterior read warm grey under the sun).
- **Another villa or option**: `VIEWS`, `FINISH`, the view checker and the
  review page still hold D1 names and paths; generalise them (layout id in,
  output folder out) and run the guards before its first render. A street
  elevation needs the site frontage modelled first.

## Integration discipline (generalised from the D1 round-3 failures)

Round 3 shipped a dozen visual defects that every numeric guard passed: a
sofa facing backwards, a trellis that read as a wall, flat mint "grass",
smoky pendant globes, a mirror-like bath screen, slab clothes, box lamps,
19 m trees, a bench as a black block, concrete-looking planters, blocked
cameras, a pitch-black store. One root cause: **"the tests pass" was taken
as "it looks right"**, and nobody looked at a new element until the full
draft. The rules that follow from it apply to any new element, material,
asset or view:

1. **Look before you integrate.** Every new builder, material or imported
   asset gets an isolated preview render (close-up, neutral light, a 1.8 m
   scale figure) that the lead reviews BEFORE it joins the scene. A report of
   "tests pass" without the preview image is not accepted.
   Bind the accepted receipt to actual geometry, used materials and light
   records; a later shield/aim/finish edit invalidates that preview. Resolve
   runtime material slots and complete fixture identity/colour-rendering
   metadata before rendering. Neutral staging must sit below authored ground
   surfaces, never coincide with them. Keep close swatches alongside the
   scale-reference view. See [G4d procedure](../../../docs/ops/garden-g4d.md).
   G4f morphology checks use actual blade faces for broadness, outward tip
   lean and arch-over drop; counts or a small local bend do not establish a
   species habit. State numerical morphology screens as authored assumptions.
   For an evening camera change, compare linear uplights-only foliage peaks
   AND screen population, with the same surface masks and source isolations;
   framing and first-hit rays alone do not prove the intended lit faces show.
   Disclose a faithful specified-sky cast in the live view/caption while
   retaining its QA failure and locked camera policy. Keep rebuilt geometry
   receipts explicitly pending until the lead accepts the neutral previews.
   Neutral context must disable every design emissive shader, including
   runtime lenses. Any diagnostic softbox is recorded separately and held
   identical across the comparison. A neutral world alone does not cancel
   existing luminous materials. After a plant-habit rebuild, recheck every
   existing named feature's first-hit visibility before integration; envelope
   equality cannot establish that foliage still leaves the same sightlines.
2. **No placeholder shapes in presentation renders.** A box, slab or flat
   colour standing in for a plant, garment, lamp or trellis is a defect even
   when labelled; if the real thing cannot be built, leave it out and say so.
3. **External assets are claims, not facts.** Measure every downloaded
   model's bounds, normalise its units, record its front axis and up axis,
   and prove orientation and scale in the preview. Never trust native size,
   units or facing. Enforced: seating/bed ingest estimates `front_axis`
   (tall-back side) into the manifest, a lead-verified value overrides it,
   placing a directional model without one raises, and export/import check
   the resulting front against the layout within 1 deg.
4. **Physics before looks.** Refractive glass is a closed solid with
   thickness; emitters sit inside diffusers; materials carry textures at
   real-world scale. Guard each of these as a geometric/data check.
5. **Cameras need line of sight, not just framing.** Subjects in frame is not
   enough: nothing (prop canopy, pot, wall edge, trellis) may stand between
   the lens and its subjects, and the lens may not start inside or within
   1.0 m of any object.
6. **The design is fixed; cameras move.** Never move plants, furniture or
   fittings to clear a camera, meter, or check. Move the camera, or record
   that the view cannot be taken.
7. **Every room meets its lighting card, stores included**, and windowless
   rooms are shown at interior exposure with their own lights on.
8. **Aesthetic briefs carry references.** Garden, joinery and furniture
   briefs include reference images and a plan sketch approved by the lead
   before building; words like "raised stone planter" alone produce
   concrete blocks.
9. **Small, checkpointed work packages.** One change area per agent job,
   with a stop-and-report after diagnosis and after the first fix (with its
   preview). Large batches hide defects until the end.

## Never

Compensate with exposure, white balance or tone curves; add unlabelled
content; move design geometry or photometry to make an image look better;
show an image that has not passed the guards and been looked at.
