# Villa walkthrough — preview delivered; final rendering in progress

The [30-second preview](../out/flythrough/preview/walkthrough.mp4) is complete:
**720 frames at 24 frames per second, 480 by 270 pixels, H.264 video in an MP4
container, yuv420p pixel format**. All 720 camera-admission rows and all 720
individual production image checks pass. Independent chronological contact
review found no new camera blocker. Contact review is not actual video playback
or final temporal acceptance. Final rendering is underway at the measured
**64 samples, 1920 by 1080 pixels**; no accepted final clip is claimed yet.

QA means quality assurance. RGB means red, green and blue image channels.
SHA-256 is the content-fingerprint algorithm used to bind inputs and outputs.
PNG is the saved developed-image format. One exposure stop doubles camera gain.
This is a fixed-model capability example, not approval of real villa design gates.

## Real model, connected route and fixed state

The source plan calls the requested living floor **B**, at elevation minus
3.0 metres; **GF** is its bedroom/study floor. The route follows the requested
living spaces with that naming difference disclosed:

| Physical room | Frames, numbered from zero | Display interval, seconds |
| --- | --- | --- |
| Entrance, entry-b | 0–49 | 0–2.083333 |
| Dining, passing the kitchen-island flank | 50–321 | 2.083333–13.416667 |
| Living, finishing inside the south garden threshold | 322–719 | 13.416667–30 |

Dining precedes living because that is the measured connected route toward the
south garden. The kitchen-island flank is visible from the entry/dining
circulation. Model positive X is the client's south garden, as recorded in
[site orientation](../knowledge/site-orientation.json); solar true north is
handled separately.

**Garden glazing stays closed.** All four existing exits have physical closed
panes. The authored data supplies no operable pane, track/open position or
open-state transform. Under the lead's 18:05 instruction, the route therefore
ends inside the threshold looking out. No pane is hidden, deleted, shrunk or
moved; no passage outside is shown. The original measured exits remain in
[out/flythrough/diagnosis](../out/flythrough/diagnosis/).

Geometry, furniture, plants, materials, photometry, dimmers and curtains remain
fixed. The daytime state is 2026-10-15 at 10:30 +03:00, ambient/accent layers
at 50%, other functional layers off, and the stills' open-stacked daytime
curtains. The shared timestamp conversion preserves sun altitude 40.07 degrees
and true azimuth 135.34 degrees. The [authenticity receipt](../out/flythrough/authenticity.json)
records exact source-transport and complete evaluated-mesh equality: all 1,956
meshes retain fingerprint
681bbfeca3a3949f1f3232e2a3434f61b36201ccbeed029e3780e4f5ad8b4e7d.

Framing is contextual: island, table, sofa and terrace edges are cropped;
fixed planting and window structure naturally screen some garden content.
No complete room or terrace inventory is claimed in each frame. Explicit
room queries resolve actual model geometry, and the production opening and
subject-overlap checks remain active. This follows the existing contextual
stills' disclosed partial framing. Both delivery folders contain a companion
caption identifying these crops, closed glazing, model assumptions and camera lock.

## Path, guards and determinism

The level camera uses **24 millimetres** focal length, a 36-millimetre-wide
sensor and **1.35 metres eye height above the floor**. Source:
[ADR-0013, decision part 8](decisions/ADR-0013-presentation-renders.md) and
[the existing view chooser](../src/archpipe/concept/render_views.py).
Every frame reuses the production standing-point, interior lens-clearance,
finite-wall sightline and opening guards. Standing-point policy retains
0.30-metre wall/column and 0.15-metre furniture clearance; finite-wall forward
sightlines retain their one-metre requirement. The chooser's one-metre
foreground composition penalty is a score, separate from hard standing clearance.

Additional physical admission sweeps a 0.15-metre horizontal operator margin
between successive poses, from 0.05 to 1.80 metres above the floor. The
1.80-metre operator height is explicitly **ASSUMED**. Shared production
triangle/box arithmetic includes transparent panes, imported furniture,
plants and settled curtains. Admission must also pass against actual visible
evaluated Blender faces; an authored-only pass cannot permit rendering.

**720 of 720 production admission rows pass**, with zero lens, wall, opening
or swept-obstacle failures. Total travel is **10.547162 metres**. Quintic
straight corridors give zero velocity and acceleration at each waypoint;
orientation eases independently. Travel ends at 27 seconds, followed by a
three-second hold. Frame 719 starts at 29.958333 seconds; its display interval
completes the 30-second clip.

Peak sampled speed is **0.732426 metres per second** and peak yaw rate is
**14.999691 degrees per second**. Registered bounds are **0.8 metres per
second** and **20 degrees per second**, explicitly **ASSUMED slow camera
operation**, not a claimed published standard.

The [authored route](../knowledge/flythrough-route.json), policy and complete
frame list are content-bound. Path fingerprint:
ab89939d1b5ac6d803af18fa189bbfafde88c428350ce3067502c541e313287b.
Blender is pinned to **4.5.14**, seeds are fixed at zero, animated seed is off,
and all frames use unchanged production AgX Medium High Contrast development.
Source, scene, photometry, cached native geometry, camera lock, settings and
saved bytes must match before an interrupted frame can be reused.

Evidence: [all-frame guards](../out/flythrough/assembly/guards.json),
[route/motion plot](../out/flythrough/route-and-motion.png) and
[720-row preview evidence table](../out/flythrough/preview/per-frame-evidence.csv),
including speeds, room, guard result, render time and image fingerprint.

## One measured exposure and white point

[The registered exposure-group rule](../knowledge/exposure-group-rule.json)
was applied to **all 720 path cameras**. Each received unchanged source
isolations at 144 by 96 pixels, 256 samples, no denoising and seed zero,
plus the production camera meter. Summed measured lamp luminance contributes
**1.52727633%**, selecting the **day** group. All 720 meter readings supply
one upper-median exposure: **minus 9.6848554233 stops**, with **5500 kelvin**,
daylight illuminant and tint **10**, locked for the entire clip.

The [complete lock](../out/flythrough/exposure/lock.json) records every source
observation and meter value. Its fingerprint is
ac3e4d1ad9ccfa05bdcc2c73140954e9f2ee8370f45af298be8a87580fc9f1d4.
The earlier path's observations remain under superseded-empty-subject and
were not reused for the corrected cameras. The corrected run resumed 717
complete measurements and measured the remaining three, exiting zero.
Exposure was not selected from appearance or QA outcomes.

## Delivered preview and measured final samples

The preview uses 32 samples with denoising on every frame. Completed-frame
render times: median **1.755694 seconds**, mean **1.769796 seconds**, range
**1.691691–7.100762 seconds**, total **1274.253 seconds** (21.24 minutes).
These exclude orchestration and interruption time. A process exited 143 after
437 complete frames without a known cause; all saved byte hashes were valid.
Resumption completed the remaining frames with exit zero. The interrupted
frame was not accepted without a complete receipt.

- [Preview MP4](../out/flythrough/preview/walkthrough.mp4)
- [Preview poster](../out/flythrough/preview/poster.png)
- [Companion caption](../out/flythrough/preview/caption.txt)
- [All 720 individual image checks](../out/flythrough/preview/all-frame-qa.json)
- [Independent complete contact review](../out/flythrough/preview/visual-review.md)
- [Encoded format and video fingerprint](../out/flythrough/preview/video.json)

[The imaging policy](../knowledge/flythrough-policy.json) registered the sample
and temporal thresholds before measurements. Frames 0, 359 and 719 each received
a 1024-sample reference. Candidate order is 64, 128, 256, 512, 1024; the first
candidate must pass unchanged production QA and mean absolute developed RGB
error at most **0.01**, after dividing byte-channel values by 255, at all three
cameras. **64 samples passed**, so higher candidates were unnecessary.

| Frame | Error against 1024-sample reference | Reference render seconds | 64-sample render seconds |
| --- | ---: | ---: | ---: |
| 0 | 0.0065376662 | 122.843 | 15.801 |
| 359 | 0.0065525877 | 105.077 | 9.853 |
| 719 | 0.0067935881 | 89.315 | 8.787 |

All references and candidates independently pass production QA.
[Sample-choice receipt](../out/flythrough/sampling/choice.json),
[full-size independent review](../out/flythrough/sampling/visual-review.md).
Actual final diagnostic-buffer renders retain the reference-error pass and
differ from the selected beauty candidates by only about 0.0000002 normalized
mean RGB: [early fidelity receipt](../out/flythrough/final/early-fidelity.json).

## Temporal acceptance and final status

Actual world-position buffers reproject opaque, nonemissive, high-roughness
static surfaces into the preceding camera. Glass, depth edges, disocclusions,
borders and unmatched surfaces are excluded. Every adjacent final pair must
retain at least **1000 matched pixels** and mean absolute developed RGB change
at most **0.01**. View-dependent changes count conservatively. Native coverage
already passed at the three representatives with 55,821 / 80,397 / 9,243
eligible preview-size pixels; a separate 32-camera screen had the same minimum.
This necessary coverage screen does not grant temporal acceptance.

Before accepted-path beauty rendering, three early pairs were registered from
path arithmetic. All now pass at full final resolution:

| Pair | Selection | Matched static pixels | Mean RGB change |
| --- | --- | ---: | ---: |
| 179–180 | Fastest turn | 929,338 | 0.0044620689 |
| 253–254 | Fastest travel | 1,164,021 | 0.0040935070 |
| 623–624 | First garden-subject frame | 189,789 | 0.0029863450 |

All nine early final images pass QA. These are early gates only:
[early temporal receipt](../out/flythrough/final/early-temporal.json).
The complete final is rendering in bounded packages using the same coordinator
and resume guards. Acceptance still requires **all 720 final frames**,
**all 719 adjacent temporal pairs**, and production QA on **every 24th frame**.
Only then may the coordinator encode the high-quality H.264/yuv420p final
at constant rate factor 16 and generate its poster. Intended final paths:

- out/flythrough/final/walkthrough.mp4
- out/flythrough/final/poster.png

## Photographic limits and verification

Full-size review found inherited opal-globe facets and angular/repeated
procedural planting in both candidates and 1024-sample references. Each globe
has 160 faces and 146 vertices without authored smoothing/subdivision.
These are unchanged source-appearance limits, not evidence that more samples
would fix the model. They remain openly recorded in the learning index and
captions. Sample similarity does not certify indistinguishability from a photograph.

**129 focused tests pass**, process exit zero: 18 walkthrough regressions,
108 requested rendering regressions and three agent-adapter tests. They include
actual frozen wall/pane and plant clipping failures, too-fast motion, a clean
delivered path, hash determinism, unresolved subjects and missing static
coverage. Portable verification with normal and initially empty HOME both
passed by exit status. [Settled verification evidence](../out/flythrough/settled-verification.json)
binds those logs. All 38 skill/role adapters match; no full suite or commit
was performed. Fresh portable verification after documentation updates also
passes in normal and initially empty HOME environments, both process exit zero:
[current verification ledger](../out/flythrough/final-verification.json).
The prepared production source inventory remains unchanged.

The lead's finals.done marker exists. Graphics work uses the shared lock and
eight processor threads. No dependencies were installed. Protected shared
out/villa/round3 and assets/user symlinks were not modified. The lead owns
full-suite execution and commits.

**Lessons to register:** flythrough-transparent-passage,
flythrough-authored-sun-time, flythrough-renderer-dependency-boundary,
flythrough-command-import-boundary, flythrough-static-opacity,
flythrough-curve-overshoot, flythrough-fixed-geometry-scan,
flythrough-room-subject-prefix, flythrough-cache-material-retention,
flythrough-unresolved-subject and flythrough-static-coverage. Real reproductions,
construction controls, proving tests and workflow updates are indexed in
[LEARNINGS](LEARNINGS.md) and the existing guard registry. Fixed-source fixture
and botanical photographic limits remain open; final video acceptance is pending.
