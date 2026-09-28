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

## Amendment (2026-09-24): faithful before beautiful

The client's position: *"photos are our main source of our design in real
life so it has to be faithful representation"*, and lighting errors must be
fixed at the specification, *"don't cheat by basically photoshopping it"*.
Renders are therefore evidence for design decisions, and every choice is
judged by whether it could mislead one.

- **Lighting specifications are fixed at the source.** Lamp colour was
  display-sRGB treated as linear light, which made the lamps cooler than
  their spec. It is now a CIE 1931 blackbody, and `verify.py` checks it
  against the Planckian locus. Camera settings are standard presets
  (daylight 5500 K, tungsten 3200 K), never tuned to hide an error.
- **Glass transmits what the model says:** Revit transparency 85 gives
  Tv 0.85, applied as sqrt(Tv) on each face of the slab. It was 100%,
  which overstated daylight by about 15%.
- **Exposure and tone curve are locked across a set.** Metering each
  view separately equalised a dark corner with a sunlit bed, hiding the
  very differences a designer needs to see. Each image records its
  absolute exposure (EV).
- **Every image carries a record** (`*.caption.json`) separating:
  - what comes from the design;
  - invented dressing (props, rug, curtains, skirting);
  - stand-ins that are not specified products (procedural furniture,
    generic Revit fixture families and generic IES files, a photographed
    view that is not the site);
  - every optical assumption.

  `--no-dress` renders the design alone.
- **Appearance swaps must be the specified product.** Replacing a
  generic fixture with a nicer generic model would be decoration. The
  faithful route is a chosen real product, whose manufacturer publishes
  both a family and a measured IES file.

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

## Amendment (2026-09-27): this is the standard for every render

The client, comparing the villa set with `bedroom-overcast-door.png`: *"that should be our standards and our
process for all renders"*. The first villa set was built on a new renderer that reused only the glass, sky and
calibration parts of this decision and dropped the rest (16-20 mm lenses at 1.55 m, pre-guessed fixed exposures,
bump-textured paint, box furniture, no skirting or frames); it looked like CG. Every presentation render now follows
all ten parts above: 24 mm level camera at eye height with lens shift; exposure metered by
`photoreal.camera_meter` and locked per state; real finishes (smooth paint, photo textures mean-matched to stated
reflectances); `archpipe.furniture` geometry where a builder exists; cloth bedding; skirting, frames and labelled
dressing; the caption record; `render_qa` and a render-critic pass before anyone sees an image.
`tests/test_render_standard.py` fails if a villa scene departs from it.

### Amendment (2026-09-27, client review of draft 8): framing, textures

- **Framing is set by where the camera stands, not by the lens.** 24 mm stays the standard (client: "the 24 mm is
  faithful to the human eye, may be just back up to cover more"). Each camera stands where a photographer could:
  its room, 0.30 m off walls and columns, 0.15 m off furniture, or in one of its door openings with that door open
  for that view only (stated in the caption). Where 24 mm cannot hold every subject from any such point, the view
  uses **16 mm** (client decision), with the measured angle that forced it recorded on the camera and checked.
- **Textures keep their pattern; the finish keeps its stated colour.** Each photo texture is mean-matched per
  channel to the stated base colour at the stated reflectance. Luminance-only matching let a pink marble photo
  stand in for a cream stone.

### Amendment (2026-09-27): reusable whole-villa render handoff

The ten-part bedroom presentation standard and the later camera and colour
amendments apply to a whole-villa set. The reusable handoff requires a checked
layout and furniture envelopes, a lighting design with verified products and
photometry, and a finish schedule that states colour and reflectance. The
exporter owns those choices and captions; the renderer consumes the scene
contract. Whole-subject framing, camera clearances, generated furniture
orientation, cloth cut, scene validity and support on rendered surfaces are
checked before a workstation draft. Automatic image checks and a full-size
render critic review follow the draft. The review page joins the images,
captions, quality reports and measured lighting and daylight before a client
decision. Every image must identify assumed finishes, procedural stand-ins,
generic photometry, dressing and view-specific opened doors.

The current D1 exporter, view checker, finished-daylight command and review
page still contain D1 room names, mappings, view choices and output paths.
Their existence demonstrates the process on D1; it is not evidence that a
second villa can be run without adapting those inputs and testing its own
geometry. The scene contract and workstation driver are the reusable
boundaries. The operating sequence and known limits are recorded in the
`docs/MCP.md` and `docs/villa-render-scene.md`.
