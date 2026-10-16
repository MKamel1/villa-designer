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
8. Does every generated piece face the way the plan says, and does soft
   goods' cut match the bedroom (0.30 m drop over sides and foot)?
9. Do textures carry the stated finish colour (per-channel mean), or
   their photo's own chroma?
10. Does anything float? (`render_support.unsupported`)
11. Is each subject wholly in frame at 24 mm from a real standing point?

For a whole-villa set, follow the `villa-render` skill.

**Render through the driver**, `scripts/render_hyperreal.py`, which places
the sun from `spec/villa-site.yaml` and runs `archpipe.render_qa` on every
image (`out/photoreal/*.qa.json`). Drafts are 256 samples; ask before
spending on final 2048-sample sets, and state the cost. Look at the images
after QA passes: QA catches known defects, not new ones.

**Faithful before beautiful.** Renders are the client's main basis for real
design decisions (ADR-0013 amendment). Keep exposure and look locked
across a comparison set (the driver's default). Use model data for
optics, e.g. glass transmittance, never 100%. Label everything not in
the design: every render writes `*.caption.json`, and `--no-dress` shows
the design alone. Replace appearances only with the actually specified
product.

**Lighting is a specification, not a look.** The render must be faithful to
the fixtures' photometry: IES distribution, lumens and colour temperature.
If lamps look wrong, find the error in the light's spec or conversion
(e.g. display-sRGB lamp colour used as linear light) and fix it there.
Follow the client decision 2026-10-15 in ADR-0013 for measured villa groups:
one locked exposure and white balance per pre-registered dominant-light group.
Daylit groups use 5500 K; lamp-group white balance follows authored dimmed
flux/CCT population. Use the explicit source locus in `photoreal.white_balance`:
Planckian lamps (including evening) use tint zero; daylight/dusk use tint 10.
Temperature alone does not identify a white point. After a source-colour or
camera-adaptation change run `scripts/check_white_balance.py` on the workstation
under its built-in graphics lock. It enforces the pre-registered grey-card
cast/ratio guard at 2700/3000/4300/5500 K plus the daylight control; retained
failing values and independent CIE references are in `docs/wbcheck-report.md`.
Carry the actual temperature, tint and illuminant model from render receipts
into generated captions; the authored exposure preset alone is insufficient.
Never tune per view or use group changes to waive QA.
The bedroom path retains its standard presets.

**Views are declared by what they show.** Each view lists its subjects
by design id (`photoreal.VIEW_SUBJECTS`); `render_qa` fails a view whose
subject is out of frame. A fixed camera over a moving design goes stale
silently. Choose framings with the projection model before rendering, not
by trial renders.

**Guards inherit the defects they were calibrated on.** After fixing an
upstream defect (e.g. lamps outside their shades), re-read every threshold
set on renders that contained it before trusting a new pass or fail;
`highlights_present` was set when misplaced lamps blasted the ceiling.
A guard must never push toward in-camera compensation: warm light under
the tungsten preset is advisory, not a failure. Camera presets are
standard: daylight 5500 K, cloudy 6500 K, tungsten 3200 K.

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

For an approved side-by-side Blender evaluation, select both the explicit
executable and expected version; retain the production default and isolated
output/configuration. Run `tests/blender_version_api.py` in both runtimes
before a batch, and execute affected standalone entry points too. Blender
ignores PYTHONPATH by default: shared imports must resolve from each entry
point’s checkout and pass an isolated relocated-checkout import test. Sky API renames must retain the legacy light-source model
and atmospheric defaults, rather than accepting new node defaults. Lock
camera/exposure/settings and report every evaluated geometry difference.
A version-bound procedural seed can change the initial cloth pattern: require
equal recorded pattern seeds and initial-vertex hashes before attributing
output differences to the solver. Keep normal migration and fixed-pattern
controls in separate receipts. See `docs/ops/workstation-jobs.md` and
`scripts/summarize_blender52.py` for the evaluation guards.
