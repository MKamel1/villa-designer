# ADR-0013 — Presentation renders: fix the structural causes, not the samples

- **Status:** accepted
- **Date:** 2026-09-24
- **Relates to:** ADR-0001 (Revit is the source of truth), ADR-0009/0010
  (the photometric path this must never disturb)

## Context

Several rounds of "hyperreal" renders still read as CG, whatever sample
count or texture resolution we used. The user's review was that the window
looked like a mirror, the daylight and interior lighting looked fake, and
the bed looked fake. An audit of the code, checked against archviz practice,
found causes that more samples cannot fix:

| Cause (verified in code) | Effect |
|---|---|
| Window glass was a refractive Principled slab. Cycles treats it as an occluder for shadow rays, so sun and sky only entered as caustics. | No sun patch and no frame shadow; the room looked lit by nothing. |
| The "day" world was a pure-sky HDRI: no sun disc, no ground. The render-input site was Boston, not Cairo. | No hard light, and a void outside the window. |
| The window's ~4 % reflection of a lit room sat over a dim exterior. | The window read as a mirror. |
| Blender 4.2 has no display white balance. | Everything looked orange. |
| Every Revit material was rescaled to one reflectance of 0.35. | The Revit colour [64,0,0] became a pure-red lamp shade, the door frame turned orange, ivory bedding turned grey. |
| Bedding was built from boxes and ellipsoids. | No drape. |
| The camera was pitched with no lens shift. | Converging verticals. |
| `output: 0` became 1.0 because of `x or 1.0`. | No lights-off shots were possible. |
| The room was empty. | A CG tell in itself. |

## Decision

A `--profile final` presentation path. It is never active with `--measure`,
so the validated photometry stays byte-identical. It has these parts:

1. **Blender 4.5 LTS** (from 4.2), for display white balance. It was
   re-validated before use: the bare-light ratio is 0.99984, and the IES
   beam agrees within 1 %. LGLled gives the same numbers as on 4.2, and
   `run_bedroom.py` passes with a median ratio of 0.9743.
2. **Architectural glass** (`photoreal.architectural_glass`). Shadow and
   diffuse rays see a Transparent BSDF; camera and glossy rays see the glass.
3. **Physical sun and sky.** The Nishita sky is positioned from the site
   (Cairo, `spec/villa-site.yaml`) with `archpipe.solar`. Two calibration
   facts were **measured** (`calibrate_sky.py`), not assumed:
   - `sun_rotation` equals the compass azimuth, measured clockwise from +Y.
   - At strength 1, Nishita gives 30.5 / 76.7 / 120 in this project's lux
     units at 15 / 35 / 60° elevation. Real clear-sky values are about
     25k / 60k / 100k lx, so the constant ×800 (±5 %) makes the sky read
     in lux. Its shape with sun height is already right.
4. **A photographed view for the eye only.** The lighting comes from Nishita.
   "Eye rays" are camera rays plus transmission rays that have not yet hit
   anything diffuse or glossy. `Is Camera Ray` alone is wrong: a camera ray
   comes out of window glass as a transmission ray, and the first draft
   showed a white plain for exactly that reason.
5. An **exterior ground** for bounce light, hidden from eye rays. A **portal**
   fills each window opening.
6. A **camera meter** instead of a fixed lux target. It takes the
   log-average luminance of a fast pre-render, excluding the top 3 %, and
   applies a −0.4 stop bias. **White balance** is 5500 K for daylight and
   3000 K for lamps.
7. **Real finishes** replace CAD shading colours. Textiles get per-material
   presentation reflectances: bedding 0.70, linen 0.40, throw 0.20.
   Photo textures are mean-matched to those values. All of these are logged
   assumptions.
8. **A level camera with lens shift**, 24 mm, eye height 1.35 m, six named
   views.
9. **Cloth-simulated duvet and throw** over the extracted mattress. The
   Revit bed frame and footprint stay authoritative (ADR-0001).
10. **Dressing** with CC0 props, skirting, curtains and a rug.

## Alternatives rejected

- **More samples, textures or HDRI strength.** Tried over several rounds; it
  cannot fix any cause above.
- **Downloaded substitute bed.** FurniMesh models are AI-generated single
  meshes with no bedding and no stated licence. Poly Haven has no modern
  bed. Cloth simulation keeps the specified bed, and `assets/user/bed/` is
  reserved for a model the user supplies.

## Consequences

- These renders are presentation. They are never a lighting verdict, which
  remains ADR-0004/0009.
- The site sun is illustrative until the real site replaces the placeholder
  in `villa-site.yaml`.

## Sources

- iMeshh, *Why Blender's default glass looks wrong*
- Blender Manual, *Sky Texture*
- Blender 4.3 release notes, *White Balance*
- Superrendersfarm, *Cycles settings* (portals, bounces)
- Render Infinity, *realistic textiles*
- D5 and XYZ360, *archviz camera height and lens shift*
