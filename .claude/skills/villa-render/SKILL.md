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
   - Duvets are cloth cut like the bedroom: 0.30 m over the sides and foot,
     starting on the generated mattress top, beyond the pillows.
   - Fixtures sit on the surface actually rendered: recessed fittings on the
     ceiling above them, cords to the real ceiling, markers flush on walls
     (`_seat_recessed_on_soffit`).
   - Views: 24 mm, level, eye 1.35 m (1.20 seated). `frame()` moves the
     camera (room, or its door opening with that door opened for that view)
     until every subject is wholly in frame; only where no standing point
     works, 16 mm, with the measured angle in `lens_basis`.
2. **Guards, locally, before the workstation** (all must pass):
   - `tests/test_render_standard.py`: lens and camera, set-metered
     exposure, cloth on every bed and its cut, smooth paint, construction
     details, generated pieces facing the plan, render contract, **nothing
     floats** (`render_support.unsupported`).
   - `scripts/villa_render_views.py`: whole subject in frame, camera
     clearances, doorway rule.
   - `tests/test_villa_lighting.py`.
3. **Draft**: `scripts/villa_render.py --samples 256 --res 960x640`.
   `render_qa` runs on every view; then look at every image, full size,
   next to the bedroom reference.
4. **Diagnose from data, not impressions.** A colour cast: read the linear
   EXR and the textures' mean colour before touching the camera (the pink
   D1 set was texture chroma, not white balance). An odd object: ray-cast the
   pixel to its mesh id. Fix the cause in the spec or exporter, add the
   guard, prove the guard on the real defect, record it in LEARNINGS.
5. **Re-measure lighting in the scene** after fixture moves
   (`--measure-lighting`).
6. **Finals**: 1024 samples, 1920×1280. Then `render_critic`, then the
   review page (`scripts/villa_review_page.py`) and publish.

## Extending

- **New furniture type**: add a builder (local frame: x across, +y front,
  z up, millimetres, verified primitives), name its parts, map parts to
  finishes in `villa_render.part_material`, keep it inside the envelope,
  and extend the orientation test.
- **New view**: declare its subjects by design id; let `frame()` place it;
  never hand-tune a camera to hide a problem.
- **New finish**: stated colour + reflectance; textures supply pattern
  only (per-channel mean matching in `villa_scene`).
- **Another villa or option**: the exporter, `VIEWS`, `FINISH`, the view
  checker and the review page still hold D1 names and paths. Generalise
  those (layout id in, output folder out) and run the guards on the new
  layout before its first render.

## Never

Compensate with exposure, white balance or tone curves; add unlabelled
content; move design geometry or photometry to make an image look better;
show an image that has not passed the guards and been looked at.
