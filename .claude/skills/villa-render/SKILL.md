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
   - Shell faces are classified by their real normal, not by tags.
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
     horizontally AND its top above the frame bottom (hard); the main
     subject seen from its front; no piece within 1.0 m of the lens in view;
     no subject behind a wall; then how much of the room shows, depth and
     windows. 24 mm, level, eye 1.35 m (1.20 seated); 16 mm only where no
     standing point holds the subjects, recorded in `lens_basis`. Exteriors
     and the stair keep authored, level cameras (lens shift, never tilt).
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
   - `tests/test_render_views.py`: facing, looming, occlusion, height,
     door-band rules, each proven on the draft that broke it.
   - `scripts/villa_render_views.py`: whole subject in frame, clearances,
     doorway doors opened.
   - `tests/test_villa_lighting.py`, and the render report must carry
     `qa_scene` so every render_qa check runs (none silently skipped).
3. **Draft**: `scripts/villa_render.py --views review --samples 256
   --res 960x640` (`review` skips `final_only` views). Every final-only
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
6. **Finals**: `--views all --samples 1024 --res 1920x1280`; if the driver
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
- **New finish**: stated colour + reflectance; textures supply pattern only
  (per-channel mean matching). Check the tint survives in the final image
  (the first grey-green exterior read warm grey under the sun).
- **Another villa or option**: `VIEWS`, `FINISH`, the view checker and the
  review page still hold D1 names and paths; generalise them (layout id in,
  output folder out) and run the guards before its first render. A street
  elevation needs the site frontage modelled first.

## Never

Compensate with exposure, white balance or tone curves; add unlabelled
content; move design geometry or photometry to make an image look better;
show an image that has not passed the guards and been looked at.
