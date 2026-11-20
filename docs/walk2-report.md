# Walkthrough version 2 — complete preview; final rendering gated

Updated 2026-10-22. The **75-second diagnostic preview is complete** at
30 frames per second, with all 2,250 frames. Final sampling, 1920-by-1080
rendering, temporal acceptance and master/web delivery are **not accepted or
complete**. Fixed imaging inputs currently conflict with existing image guards;
the failures remain visible and client disposition is pending.

The completed [diagnostic preview](../out/walk2/production8/preview/walkthrough.mp4)
is 480 by 270 pixels, H.264 video, 2,250 frames at 30 frames per second and exactly
75 seconds. Every frame has fresh native exact-grid QA. **2,214 image checks pass;
36 remain failed:** 11 clipped fence-window frames and 25 sunlit-room/shaded-garden
brightness comparisons. All 2,250 physical camera guards pass. The 56 false
brightness failures were eliminated by correcting the room sample population;
no image threshold or rendered pixel changed. Both appearance limits are awaiting
explicit client disposition before final graphics.

The new package independently repeated admission and exact geometry agreement,
then imported unchanged pixels under the strict QA-only source/transport proof.
All 57 chronological contact sheets cover every frame. Independent contact review
cannot prove full-size sharpness, fine flicker, playback smoothness or encoding
fidelity. No old quality verdict or preview approval transferred. Preparation 6
and interrupted QA package 7 remain intact; a legacy-adapter regression found
during that work is fixed and all affected tests now pass.

QA means quality assurance. RGB means red, green and blue image channels.
PNG is the native developed image format; MP4 is the video container. SHA-256
fingerprints bind input and output bytes. All image-error, motion and numerical
agreement limits below are explicitly **ASSUMED**, not architectural standards.
This remains a fixed-model capability example, not approval of villa design gates.

## Route, camera and physical state

[Policy](../knowledge/walk2-policy.json), [route](../knowledge/walk2-route.json):
75 seconds, 30 frames per second, 2,250 frames, final resolution 1920 by 1080.
The sampled path is 24.037884 metres, at model level B. Peak speed is
0.625985 metres per second against the retained 0.8 limit; peak yaw is
16.874875 degrees per second against 20. Quintic translation and yaw easing
have zero velocity and acceleration at waypoints, followed by a three-second
final position hold.

The level camera retains the existing 1.35-metre eye height, 24-millimetre lens
and 36-millimetre sensor from [ADR-0013](decisions/ADR-0013-presentation-renders.md).
Real Cycles motion blur uses a centered 0.5-frame shutter; the 180-degree
cinematography convention is ASSUMED. Native API, rendered edge-blur and actual
parser-to-stage dispatch tests pass. Compatible quaternion signs prevent long
rotation during interpolation. Complete native preflight verifies 11,250 shutter
poses against independent analytic yaw; maximum direction error is 0.000181887
degrees against the registered 0.01-degree numerical limit.

| Physical room/context | Zero-based frames |
| --- | --- |
| Entrance | 0–217 |
| Kitchen-island flank | 218–367 |
| Hall beside stair foot | 368–637 |
| Lounge | 638–884 |
| Family circulation | 885–1127 |
| Kitchen | 1128–1329 |
| Dining | 1330–1682 |
| Living, bar-alcove context, south-garden threshold | 1683–2249 |

The connected lounge/stair detour precedes dining. The stair is viewed from its
foot and is not climbed. Bar coverage is room context from living circulation;
individual frames do not claim a complete furniture inventory. All doors and
glazing remain closed. The endpoint is indoors; there is no modeled operable
pane or passage into the garden. Plant species, counts and root positions stay
fixed. No design content was moved for a camera or numerical guard.

All 2,250 native production camera rows pass standing, lens, finite-wall,
opening, physical-sweep and motion guards. Production 5 independently reproduced
exact evaluated geometry fingerprint
`c9764d74e1a8937516cd0e65bbf866aff63973ebc47c783fe8b79f5392ceb880`.
Production 8 independently passed all 2,250 rows in 277.51 seconds, then
passed unchanged-pixel import in 42.31 seconds. All 2,253 preview/draft contexts
were regenerated in 778.07 seconds. Interrupted package 7 remains intact.

## Frozen speckle failure and construction/render corrections

The [speckle policy](../knowledge/walk2-speckle-policy.json) was registered before
replacement measurements. An isolated pixel differs from its centered 3-by-3
grayscale median by more than 35 byte values. Counts exclude the one-pixel image
border. Density counts isolated pixels per 10,000 interior pixels. Flicker counts
the exclusive-or of consecutive masks at the same screen coordinates, conservatively
including true motion. Every full-size frame must have density at most 5, and
every adjacent pair flicker at most 8; there is no percentile exemption.

version 1 native frames 588–604 were frozen by value, including image fingerprints,
measurements and frame-600 crop: left 940, top 715, right 1210, bottom 875, with a
top-left origin and exclusive right/bottom bounds. Frozen density is
13.846946–15.573582 and worst flicker 27.137692: all 17 frames and 16 pairs fail.
Fixtures: `tests/fixtures/walk2-speckle-before.json`, frame 599/600 crops, and
`out/walk2/diagnosis/speckle-before.json`.

Mona Lavender now has closed tubular corollas seated on each spike axis, replacing
thin isolated-looking lamina florets. The old florets could narrowly overlap the
stalk; a claim of complete geometric separation was disproved and corrected.
Petrea flowers have closed hubs/throats; lateral pedicels now join their actual
sloping stalk. Leaves, jasmine, loquat and the independent east-yard builder were
audited using actual closed child/parent faces and contact witnesses. No
camera-dependent feature inflation or minimum on-screen feature rule was added.
Neutral previews retain exact face materials and independent review receipts.
Macro faceting/repetition and botanical-likeness limitations remain disclosed.

The first construction fix correctly failed the original cameras: density
9.673–11.970, flicker 17.890–20.865. Frozen first-fix measurements and crop remain
repository fixtures. Registered 64/128/256/512/1024 sampling controls showed that
higher samples still resolve unstable fine contrast. A normal-only control barely
helped; disabling denoising was worse. Neither control was integrated.

Native reconstruction controls preserved geometry, normals, materials, camera,
lighting, exposure and thresholds. Width 3.0 pixels passed numerically but was
rejected for whole-image softness; width 2.0 failed speckle. The registered
Blackman–Harris width 2.5 pixels passed bounded image/sharpness review, including
a stationary view. This width is ASSUMED. Source metering retains its original
width 1.5 pixels; beauty/reference/candidate paths read back width 2.5. No image
postprocessing was used.

Under this corrected construction and rendering, **all 17 original cameras and
all 16 adjacent pairs pass**: density 1.600887–2.026500, worst flicker 3.728954.
Evidence: `out/walk2/production2/same-camera/speckle.json`, independently repeated
in production 3. This is the frozen-case pass, not complete-new-clip acceptance.
Every final frame and all 2,249 adjacent pairs remain mandatory.

## Complete preview diagnosis and retained quality failures

Production 3 rendered all 2,250 preview frames in **5,181.18 seconds**. Its original
window QA falsely sampled foreground wall and falsely omitted glazing behind
hidden-render curtains. Actual evaluated first-hit glazing masks now exclude
hidden-render/camera-invisible geometry and include opaque instances. Original
pixels/meters may be reused only after exact non-QA source comparison, unchanged
physical scene/path/photometry/transport and fresh equal-geometry native admission.
Original packages and receipts stay intact; new native contexts are mandatory.

Production 5 regenerated all 2,253 preview/draft contexts in **691.88 seconds**,
exit 0. All-frame image checks and diagnostic encoding took **211.99 seconds**.
Its 92 failed frames comprise 11 clipping failures and 81 brightness failures.

Independent native diagnosis establishes:

- **56 false brightness failures:** another window was counted as inside the
  room. The corrected background excludes every visible glazing owner, including
  panes too small for an individual check. Separate exact native two-pixel window
  and three-pixel room grids preserve the existing sample spacings and thresholds.
  All 27 independently frozen room masks match the corrected native producer
  exactly, with zero missing/extra pixels. Required indoor comparisons refuse
  missing/stale ownership and empty room populations. Legacy contexts retain an
  explicit rectangle/cell approximation.
- **11 genuine clipping failures, frames 1212–1222:** 60.0781–61.5320% of a cropped
  side-window detail population is clipped, against the unchanged 60% maximum.
  Local detail 0.0294–0.0338 exceeds the 0.01 minimum. Native continuation attributes
  98.49–99.58% of clipped samples to the specified sunlit east fence, with the
  correct pale grey-green finish; no helper card or triangle-splitting error was
  found. [Independent review](../out/walk2/diagnosis/window-clipping-before/independent-clipping-review.md).
- **25 genuine brightness failures, frames 1980–2004:** exact glazing exclusion
  leaves an actual sunlit living-room plaster wall brighter than the shaded
  garden. For frame 1992, room 90th-percentile luminance is 0.818424 against window
  median 0.750944. The strict comparison remains failed. [Independent review](../out/walk2/diagnosis/window-room-population-before/independent-review.md).

No camera, exposure, finish, light or image threshold was changed to conceal
these genuine failures. Straight-ray attribution is not a full refracted
light-transport proof; unclipped per-pixel linear radiance was not retained.
Fresh whole-preview revalidation confirms exactly the same 11 clipping and
25 brightness refusals, with every other frame passing. All-frame image QA took
184.13 seconds; preview encoding took 3.98 seconds and contact generation 8.07
seconds. Evidence: `out/walk2/production8/revalidation-queue.json` and
`preview/all-frame-qa.json`. Final rendering remains gated pending explicit
disposition of both retained appearance limits. No final-preview approval exists.

## Exposure, samples and delivery gates

All 2,250 source populations select the day group: lamps contribute 3.027541% of
measured linear luminance. One exposure stop doubles camera gain. The
complete-clip upper-median exposure is locked at
minus 9.589567255 stops, 5500 kelvin, daylight white point and tint 10. Unchanged
source metering took 12,200.01 seconds including native reopening/preflight.
Evidence: `out/walk2/production3/exposure/lock.json`. Reuse requires exact unchanged
transport, source-rule and individual meter-row agreement.

**No final sample count is selected.** Candidates 64, 128, 256, 512, 1024 are compared
with 1024-sample references at three registered cameras, with motion blur enabled.
Each must pass production QA and normalized mean absolute RGB error at most 0.01,
plus static temporal/speckle checks on route-derived fastest travel, fastest yaw
and garden-approach adjacent pairs. Every final static pair requires at least 1000
matched pixels and normalized mean RGB change at most 0.01. Final packages contain
48 frames and resume only with matching input/byte receipts.

The web copy must be at most 15,000,000 bytes. Every decoded frame is compared
with its native PNG; at most 0.001 of pixels may differ by more than 40 byte values
in any RGB channel. Fast-motion frames are separately identified by route speed
and yaw upper quartiles. version 1 reproduction confirms compression was not the original
speckle cause: frame 474 has 0.0650% pixels over 40, and the whole-clip worst is
frame 609 at 0.09394%, below the registered 0.1% screen.

Current review video:
`out/walk2/production8/preview/walkthrough.mp4` — **diagnostic, quality refusals retained**.
Preview fingerprint: `e77dd98f18be6d9ff6ff2e19e5dd8ef8883b35f43fc89fed365ea7b06bbfc3a6`.
Planned, not delivered:
`out/walk2/production8/final/walkthrough-master.mp4` and
`out/walk2/production8/final/walkthrough-web.mp4`.
Final render time, selected samples, complete temporal/speckle and encoding
artifact/size results remain pending.

## Verification

The latest 46 focused window/QA/reuse/adapter tests pass, exit 0:
`out/walk2/resume9-room-settled-tests3.log`. Native tests pass 6 camera/dispatch/
blur cases and 4 window cases, including actual small-pane geometry and its
translated/renamed sibling. The independent native 27-camera producer proof also
passes with unchanged evaluated geometry. Adapter synchronization checks 38 files.
The initial requested focused run passed 202 tests, exit 0, in 2,585.65 seconds
(`out/walk2/resume9-focused-tests.log`). An expanded run exposed the legacy
adapter regression; its original failures remain retained. The updated 46-test
subset passes. The fresh complete rendering-standard run passes all 61 tests,
exit 0, in 1,157.34 seconds (`out/walk2/resume9-standard-final.log`). The directly
rerun existing six-check adapter regression also passes, exit 0. Settled portable verification passed with both normal and initially empty HOME,
exit 0 in 244.79 and 240.38 seconds respectively
(`out/walk2/resume9-settled-verification.json`). An interrupted
portable verification process exited 143 with no completed verdict; it is retained
and the fresh settled runs above passed. Earlier normal/empty-home passes are
historical. Final fresh verification after the legacy correction passes in
both environments, exit 0 in 233.66 and 231.41 seconds
(`out/walk2/resume9-final-verification.json`).

No full suite, commit, dependency installation, credential access or protected
shared-data modification was performed. The lead owns full-suite execution and
commits.

**Lessons to register:** walkthrough-detached-plant-organs,
walkthrough-temporal-speckle, walkthrough-policy-encode,
walkthrough-visibility-topology, walkthrough-fresh-stage-directory,
walkthrough-preview-gate, walkthrough-native-dispatch,
walkthrough-pixel-reconstruction, walkthrough-shutter-quaternion,
walkthrough-window-pixel-ownership and walkthrough-window-room-population.
Controls, frozen failures, quiet/mutation/sibling proofs and workflow changes are
registered in LEARNINGS and the garden guard registry. Whole-clip acceptance
remains open.
