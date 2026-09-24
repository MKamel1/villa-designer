---
name: photoreal-render
description: Make or fix presentation (photoreal) renders of the Blender scene -- daylight, glass, finishes, camera, bedding, dressing -- and turn every visible defect into an automatic check. Use before changing render quality, and whenever a render "looks fake".
---

Read [the decision](../../../docs/decisions/ADR-0013-presentation-renders.md)
and the "Presentation rendering" rows in [lessons](../../../docs/LEARNINGS.md).
Presentation is `--profile final` only. Never let it touch `--measure`,
ADR-0009/0010 or `run_bedroom.py` agreement; re-run that gate after edits.

**Diagnose before tuning.** Samples, texture resolution and light strength
cannot fix a structural cause; five rounds were lost that way. For a fake
look, check in this order and name the cause before changing anything:
1. Does daylight physically enter? Glass must pass shadow/diffuse rays.
2. Is there a sun and a sky (Nishita, from the real site and time)?
3. Does the eye see a view through the window? A camera ray becomes a
   transmission ray inside glass; helper geometry must be hidden from every
   eye-ray type, not just camera rays.
4. Is the camera metered, white-balanced and level with lens shift?
5. Are finishes stated finishes, not CAD shading colours or one shared
   reflectance?
6. Do soft goods drape (cloth), and is the simulation physically sane?
7. Is the room dressed?

**Render through the driver**, `scripts/render_hyperreal.py`, which places
the sun from `spec/villa-site.yaml` and runs `archpipe.render_qa` on every
image (`out/photoreal/*.qa.json`). Drafts are 256 samples; ask before
spending on final 2048-sample sets, and state the cost. Look at the images
after QA passes: QA catches known defects, not new ones.

**Lighting is a specification, not a look.** The render must be faithful to
the fixtures' photometry: IES distribution, lumens and colour temperature.
If lamps look wrong, find the error in the light's spec or conversion
(e.g. display-sRGB lamp colour used as linear light) and fix it there.
Never compensate with white balance, exposure or tone-curve tuning; the
camera uses standard presets (daylight 5500 K, tungsten 3200 K).

**The critic sees it before the user does.** After `render_qa` passes, run
the `render_critic` role on the set. `render_qa` only knows defects it has
already met; shape realism (curtains, fixtures, bedding) needs judgement.
Check the critic's claims against physics before turning them into guards.

**Measure, don't guess, renderer facts.** Unit scales, axis conventions and
ray semantics are probed with a tiny scene (`calibrate_sky.py`,
`calibrate_photometry.py`) and written down with the measured values.

**Every defect becomes a guard.** For each new defect record, in
`docs/LEARNINGS.md`: what happened, *why it was missed*, and the guard.
Prefer an automatic check (a `render_qa` check with a unit test, a
`verify.py` lint, a script post-condition) over prose. Prove the guard
catches the real defect: reproduce it (`render_hyperreal.py --qa-break`, or
the historical input) and watch it fail. A guard that has only seen
synthetic data can miss the real case; two guards here did at first.
