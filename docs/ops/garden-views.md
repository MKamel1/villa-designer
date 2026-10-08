# Garden camera diagnosis and promotion

Read [the measured report](../garden-views-report.md). Camera coordinates
are repository metres: x and y are horizontal, z is vertical. A target
defines the viewing direction. Lens shift is measured in sensor-width
units; it changes framing while keeping the camera level.

1. Preserve the reviewed source image, its camera, scene and exposure
   receipt. A naming snapshot stays frozen: later approved appearance
   changes require individual item, field, old value, new value and
   decision records. Never overwrite the historical snapshot.
2. Diagnose image failures before changing the camera. Use
   `scripts/garden_view_diagnose.py` in Blender with the authoritative
   scene and a request containing the actual view and normalised pixel
   coordinates (x rightwards, y downwards). Trace glass to the next
   physical hit. A geometric alpha-cutout hit does not establish that
   an opaque surface produced the pixel; disclose that limit.
3. Measure complete physical subjects and their required sightlines with
   the existing garden framing, visibility, enclosure, proximity and
   opening checks. Broad garden intent must explicitly include the bed,
   trellis and stepping route. Keep earlier required targets when replacing
   a view. Cross-yard captions declare `caption_camera_garden` and name the
   actual camera side measured from geometry; historical search labels do
   not establish the camera's compass side. Reject candidates that pass composition but fail another guard.
   Historical mutations keep their frozen semantic role as well as pose:
   an exterior clearance proof must not inherit a later indoor camera's
   allowance merely because its view identifier is unchanged.
4. For duplicate stone surfaces, run `stone_union.prepare` at the renderer
   boundary. This joins identical-material, identical-height overlapping
   stone prisms into their exact occupied union. Never shift authored
   stones to remove a seam. Prove original route overlaps, other routes,
   renamed/translated siblings, exact plan union, closed surfaces and the
   isolated clean case with `tests/test_garden_views.py`.
5. Preview candidate cameras with `scripts/garden_g6_preview.py --scene`.
   `--candidate-view` accepts a single view or a list; geometry stays in
   the source export. Neutral fill establishes composition and surface
   defects, not actual daylight, evening illuminance or exposure. Obtain
   independent image review before integrating the camera.
6. Where numerical tonal evidence is needed, use
   `scripts/garden_view_probes.py` with the retained whole-set exposure
   receipt. It resolves every actual Illuminating Engineering Society
   photometry file before assembly, prefers current generated sources,
   falls back to the retained manufacturer bundle and records hashes.
   Copy retained inputs through `archpipe.safe_io.copy_file`, the shared
   atomic output writer; raw output copies are refused by portable lint.
   Its small probes are diagnostic evidence, not presentation deliveries.
   Never meter only the changed cameras or alter a threshold to pass.
   Record numeric exceedances even if a locked-exposure check is advisory.
7. Export a fresh local scene. Compare decoded delivery values exactly
   against G4d: meshes, props, materials, lights and camera domains must
   remain unchanged for camera work. Preview the integrated cameras again
   from that export and bind receipts to the source geometry hash.
8. Run all affected garden, orientation, landscape, render-standard and
   render-view tests. Run `scripts/verify.py --portable` with `NO_COLOR=1`
   in normal and newly empty HOME environments; judge exit status. Record
   the logs, numeric limits, independent review and before/after cameras
   in the report. The lead runs the full suite and commits.

A newly requested view whose accepted natural screening conflicts with
its required sightline contract stays a reviewable candidate until an
explicit lead decision resolves the intent. Record any reviewed allowance
in `visibility_allowances`, keyed by the exact subject and bound to the
view identifier, with the sample count, minimum visible rays and reason.
All other subjects retain seven of thirteen; invalid or copied allowances
fail closed. The 2026-10-07 v41 rear-chair decision permits six, never five.
Retire faithful views that cannot meet presentation targets with
`presentation_retired` and `presentation_decision`; both presentation batches
and the review page exclude them, while explicit diagnostic requests remain
available. Do not alter QA limits, exposure or sky to force acceptance.
Do not write to the shared `out/villa/round3` or `assets/user` symlinks.
