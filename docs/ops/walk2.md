# Longer walkthrough and fine-geometry temporal proof

Use the project virtual environment with `PYTHONPATH=src` and `NO_COLOR=1`.
The selected input is `knowledge/walk2-policy.json`, whose route is
`knowledge/walk2-route.json`. Version 1 policy and evidence remain intact.
FPS means frames per second. QA means the production quality-assurance checks.
RGB means red, green and blue byte image channels. SHA-256 fingerprints bind
source, geometry, path, measured exposure and output bytes.

1. Freeze failing native images, actual organ geometry, measured values and a
   visually identified crop before rebuilding. Register density, adjacent-mask
   flicker and encoding thresholds in `knowledge/walk2-speckle-policy.json`
   before computing replacement measurements. Disclose assumed thresholds.
2. Build closed tubular flowers seated on their spike axes; read back actual
   closed child/parent faces at shared contact witnesses. Test actual old Mona
   overlap as well as truly detached Petrea pedicels: a failed axial-seat
   witness alone does not prove disconnection. Audit leaves, corolla lobes,
   sloping stalks and independent east-yard builders. Preserve plant inventory,
   species and root positions. Do not inflate foliage for a camera.
3. Render and review matched isolated before/after specimens with their exact
   original face materials, neutral lighting and the 1.8-metre scale reference.
   Bind the reviewed bytes and actual geometry/material/light receipts. Retain
   macro facets and botanical-likeness limits rather than claiming a numerical
   attachment check proves realism.
4. Select a physically connected route and test every frame using the existing
   guards. Pre-existing evaluated meshes are an early screen only: regenerate
   the native assembly over the whole new route before rendering. Keep doors
   and glazing closed. Model B is the living floor; the endpoint is indoors.
5. Run `tests/blender_walk2_camera.py` in pinned Blender before expensive work;
   it exercises the actual parser-to-stage branch, selected diagnostic root
   and physical rendered edge spread with the shutter enabled/disabled. Run
   `python scripts/walk2_queue.py --phase preview`
   (use `--out` for a fresh package after source changes). Its stages are scene
   preparation, native assembly/admission, same-camera diagnostic, native opaque
   coverage, complete-clip source metering, representative draft, all-frame
   preview, all-frame preview QA and preview encoding. It stops for complete
   chronological visual review, with every frame on contact sheets. Every
   graphics process uses the shared graphics lock and pinned Blender 4.5.14.
6. The same-camera diagnostic reuses native v1 cameras 588–604, original
   exposure/lighting and rebuilt geometry. It uses a centered half-frame
   exposure at 30 FPS but retains the original timestamps, independently of
   the longer route. A failure stops the queue before the complete preview.
   Diagnose a construction, sampling or renderer cause; never tune the already
   measured threshold until it passes.
7. Review the complete preview. Write `preview/visual-review.json` beneath the selected output directory
   with `passed`, `path_sha256` and `video_sha256` only when the review supports
   final diagnostic rendering. Attach the substantive review. The final
   coordinator, reference renders, sample selection and final renders each
   refuse a missing or stale receipt before graphics; silence cannot supply it.
8. Run `python scripts/walk2_queue.py --phase final`. The first passing sample
   candidate must meet the original reference-image criterion and production
   QA at three representative cameras, plus static temporal and speckle screens
   at route-derived maximum travel, maximum yaw and garden-approach pairs.
   Reference and candidate cameras both use real Cycles motion blur. Camera
   transforms use the same analytic eased path during the shutter interval.
9. Final frames are resumable packages of the policy size, with image and
   position-buffer receipts. Recheck every adjacent static pair and every
   full-size frame/mask pair. Encode only after all required gates pass.
   Encode the master at the policy quality, then bounded web candidates. Decode
   every web frame and compare it with the native PNG, explicitly reporting
   the fast-motion subset and worst frame. The web copy must meet both the
   registered image-error screen and 15,000,000-byte ceiling.
10. Inspect delivery videos/images and record exact route coverage, limits,
    samples, times, guard totals, before/after metrics and video paths in
    `docs/walk2-report.md`. Run focused affected tests and portable verification
    in normal and initially empty HOME environments. Synchronize adapters after
    skill edits. The lead owns the full suite and commits.

Frame rate, count, duration, representative indices, QA stride, shutter and
package size come from policy; no delivery constant belongs in encoder checks.
An admitted cache or old test log is not current visual acceptance. If source
fingerprints change, retain the old package and prepare a fresh isolated output.

Residual fine-foliage aliasing can survive correct attachment and high sample
counts. Before integrating a native reconstruction change, retain the failed
fixed-geometry sample sweep and register bounded type/width controls. Every
control preserves normals, materials, camera, lighting, exposure, shutter and
image thresholds. Require independent full-size sharpness review including a
stationary view; an over-soft image still refuses despite passing numerically.
The current reviewed beauty setting is Blackman–Harris width 2.5 image pixels
(ASSUMED); the 3.0-pixel trial was rejected for softness and 2.0 fails speckle.
All source-isolation and exposure metering retain native width 1.5 pixels.
`tests/blender_walk2_camera.py` proves actual type/width readback and isolation.
A sandbox GPU refusal is an environment preflight failure: retry the identical
prepared package through the managed GPU permission path, never a CPU fallback
or relaxed device check. Keep its failed process receipt.

Native quaternion motion must be continuous through every shutter, not merely
correct at integer frame centres. A quaternion and its negation describe the
same orientation; interpolating their four components without compatible signs
can turn a camera almost 180 degrees during an otherwise slow turn. Construct
successive keyframes in the same sign hemisphere. Mandatory native preflight
reads actual evaluated forward direction at five shutter fractions for every
route frame and compares it with independent analytic yaw. The numerical
agreement tolerance is pre-registered in `camera_motion_check` in the selected
policy (0.01 degree, ASSUMED). Source correction requires a fresh package;
retain interrupted diagnostics and never transfer an old preview approval.

Use the policy-aware command interface for review QA as well as rendering:
`scripts/flythrough.py ... --policy knowledge/walk2-policy.json --out <selected-output>`.
Here `<selected-output>` means the actual package directory, currently
`out/walk2/production5`. If embedding its Python APIs, set
`ARCHPIPE_FLYTHROUGH_POLICY` to the absolute selected policy path before calling
them; an unset variable intentionally selects v1. A source-refusal error can be
correctly caused by an incorrect calling policy, without any file changing.
First restore the declared policy and compare source fingerprints; never edit a
manifest or rebuild solely to bypass that refusal. The actual early-review
refusal and clean retry are retained in `early-preview-review-before.log` and
`early-preview-policy-context.json` beneath the production3 package.


Window image samples must belong to actual visible glazing, not its projected
rectangle. `archpipe.window_qa` reads first-hit evaluated render geometry at the
production image check's two-pixel grid. Hidden-render and camera-invisible
objects do not block; opaque instances do. The former 12% rectangle inset
approximated exclusion of the frame/reveal; actual pixel ownership now excludes
those by construction. Keep the existing 3% visible dimensions and brightness,
local-detail and 60% clipping limits. A native geometry fingerprint permits a
batch tree cache only while the complete visibility/transform state matches.
Run `tests/blender_window_qa.py` in the pinned native runtime as well as portable
window/QA tests. Report the number of actual measured windows, including frames
that formerly had false omissions behind hidden curtains.

After an analysis-only correction, `scripts/walk2_reuse_qa.py` can revalidate
unchanged pixels in a fresh package. Its source-tree comparison refuses any
rendering, metering, policy, scene, path or photometry change outside the exact
post-render QA boundary. Fresh preparation and native assembly must independently
match the old physical scene and evaluated geometry. Retain original source,
manifest, images and receipts; copy native pixels, never overwrite the original
package or transfer an old QA verdict/preview approval. Generate fresh QA
contexts in Blender, check every preview frame, and bind a new complete-preview
review to the new package before reference/sample/final graphics. Importing
completed source meters also requires exact unchanged transport, lock and row
agreement. This bounded exception cannot reuse pixels after a rendering or
design correction.

Room brightness uses one inside-room population outside **all** visible glazing,
not just the pane currently tested. Native measurement retains every small pane
for this background even when the existing three-percent individual-window size
screen skips it. Window detail/median use their unchanged two-pixel grid; the
room percentile uses separately measured exact three-pixel native ownership,
carried as `room_glazing_pixels` through shared native and host QA adapters.
Missing/stale declared ownership refuses. Historical contexts may retain the
explicit legacy cell/rectangle approximation. Do not classify another bright
window as room interior, or round the two grids onto each other.

The bounded QA-only reuse proof also admits only the exact new room-mask field
in the post-render host adapter's returned context; all other adapter structure
and all non-QA sources remain equal. Retain the failed actual room-population
cases and native exact-grid/small-pane proofs before fresh preparation. A sampling
correction cannot waive genuine clipping or a real sunlit interior brighter than
a shaded garden. Preserve those quality failures and obtain explicit disposition
when locked imaging inputs cannot meet the unchanged guards.

Assign evidence-file ownership before parallel diagnostics, including registration
and snapshots. Independent reviewers consume their own immutable fingerprinted
inputs; never replace another producer's registration schema in place.

A required indoor window-brightness comparison also refuses an empty room
population. Do not silently skip it because a declared mask covers the whole
image. Exterior cameras retain their explicit comparison exemption.

Native versus legacy ownership is explicit: a record with `visible_pixels` needs
its declared native room mask; a rectangle-only report is a supported legacy
context even when an optional adapter field is `None`. Both brightness and
window-view checks must still run. Before acquiring fresh graphics after a QA
API change, finish the new bounded context tests **and affected existing adapter/
consumer regressions**, including `tests.test_render_standard`'s six-check adapter
case. Do not begin the next native package while those results are pending.
