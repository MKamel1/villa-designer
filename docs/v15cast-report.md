# V15 family-bath colour diagnosis — integration 7

**Result: faithful warmth; no specification or exporter correction is justified.**
The exact retained draft reproduces the **0.111 warm colour-cast FAIL** against
the unchanged 0.100 limit. The cream marble, 2700 K downlights and 3000 K
sconces agree with their authored sources. Keep this failure for the lead's
client discussion. No camera, exposure, white balance, material, fixture,
dimmer, geometry or quality-assurance limit was changed.

RGB means red, green and blue channels. Linear RGB describes the light before
display development; display RGB is the developed image, between zero and one.
Chromaticity here means each channel divided by the sum of the three channel
means, recorded in the evidence. Luminance uses weights 0.2126, 0.7152 and
0.0722 for red, green and blue. The blue/red ratio divides the blue mean by
the red mean. The cast score is the standard deviation of the three display
channel means over midtone pixels. QA means quality assurance; CCT means
correlated colour temperature, in kelvin (K). EXR is the linear image format;
PNG is the developed image format. Lumens (lm) describe emitted luminous
flux. One exposure stop doubles camera gain. D1 is this villa capability
example, not approval of a real villa design gate.

## Exact evidence and method

Branch `codex/v15cast` starts at `6be12303c9a7efa0d3a93bac63a2d42cc9ed1cdc`.
The integration-7 scene records source hash
`cc09afcf3d2d7299eb159aee47f89d7ce642b06b86fc9bf97267084e2229ccd9` and a clean
working tree. The lead's `laneR/out/villa/render-d1` draft receipts identify
retained worker job `/home/omar/archpipe/villa-render/7a390e7b6f6958861b70b88b`.
Its original linear EXRs exist: no substitute render was needed.

The original v12, v15 and v16 PNGs, EXRs and renderer receipts are copied
byte-for-byte into [out/v15cast](../out/v15cast/). Their file hashes and the
source scene/texture hashes are in [readback.json](../out/v15cast/readback.json).
The scene is generated input and was never hand-edited.

Production QA was rerun with `villa_qa_context`, using the original scene and
per-view renderer receipt. This reproduces v12 PASS **0.053**, v15 FAIL
**0.111**, and v16 PASS **0.055**. The two comparison views pass their complete
QA records, with existing advisory tonal warnings retained.

[readback.py](../out/v15cast/readback.py) constructs all 1,242 authored mesh
records through the production stone-union, material-slot, bevel and subdivision
builders. A centre ray every four pixels attributes the retained 960 × 640
EXR and PNG samples to their first surface: 38,400 rays per view. The sampled
surface table uses midtones selected on the original full-resolution PNG;
production QA separately retains its normal 800-pixel resize. Glass and mirror
labels identify the first interface, not the surface behind or reflected in it.
No imported asset or runtime cloth occurs inside these bathrooms; the attribution
does not independently verify remote imported objects visible through reflection.

## Materials and per-surface measurements

All three views' visible wall/floor stone actually hits **`marble-bath` /
Marble014**. `marble-ensuite` / Marble020 exists as a separate definition but
is not their visible wall assignment. The
[finish schedule](../src/archpipe/concept/villa_render.py) explicitly assigns
`marble-bath` to all three rooms. A definition's name alone is insufficient
evidence of its use.

There is **no specified buyable marble product, measured stone sample or
manufacturer colour target**. The finish says “cream marble, large format
(ASSUMED)”; Marble014 is an ambientCG appearance, with its provenance in the
[library manifest](../ops/workstation/library-manifest.json). This diagnosis
establishes agreement with that authored assumption, not with a purchased stone.

| Marble014 measurement | Linear red, green, blue |
| --- | --- |
| Raw texture mean, all 2,048 × 2,048 texels | 0.638005, 0.553927, 0.442887 |
| Shader's sampled raw mean | 0.638235, 0.554169, 0.443232 |
| Authored base colour | 0.700000, 0.660000, 0.580000 |
| Target after normalization to authored reflectance 0.62 | 0.654869, 0.617448, 0.542606 |
| Applied per-channel multipliers | 1.026063, 1.114187, 1.224202 |
| Actual final texture mean | 0.654633, 0.617179, 0.542183 |

The colour texture is correctly tagged **sRGB** and decoded before mean
normalization. Final linear luminance is **0.619727**, 0.0441% below the
authored 0.62 due to sampled mean estimation. **Zero texels clamp.** Final
blue/red is **0.8282**, versus target **0.8286** and raw texture **0.6942**:
normalization already removes excess photographed warmth. These same texture
values apply to v12 and v16. Marble020's separate final luminance is 0.579920
against 0.58; wet stone is 0.549757 against 0.55. Neither establishes a wrong
Marble014 conversion. [Full texture measurements](../out/v15cast/readback.json).

The following values come from the **original v15 draft**, not the source
probes. Shares are fractions of sampled midtone pixels; the tiny remaining
population consists of brass and other materials.

| First surface | Midtone share | Mean linear RGB | Linear RGB chromaticity | Mean display RGB | Display cast |
| --- | ---: | --- | --- | --- | ---: |
| Marble | 56.45% | 244.140, 125.816, 53.264 | 0.5769, 0.2973, 0.1259 | 0.4821, 0.3392, 0.2070 | 0.1123 |
| Shower glass (`glass-guard`) | 17.72% | 231.103, 106.740, 36.495 | 0.6174, 0.2851, 0.0975 | 0.4701, 0.3085, 0.1545 | 0.1289 |
| Mirror | 9.13% | 176.190, 105.592, 56.979 | 0.5201, 0.3117, 0.1682 | 0.4091, 0.3093, 0.2215 | 0.0766 |
| Ceramic | 7.74% | 686.644, 320.881, 104.425 | 0.6175, 0.2886, 0.0939 | 0.7021, 0.5405, 0.3940 | 0.1258 |
| Ceiling | 7.07% | 176.205, 97.337, 43.768 | 0.5553, 0.3068, 0.1379 | 0.4111, 0.2956, 0.1883 | 0.0910 |

The ceiling's base RGB is 0.86, 0.85, 0.83; ceramic is 0.85, 0.85, 0.84.
Warmth on these nearly neutral materials corroborates warm illumination.
Shower and window glass have equal-channel white base colours, with neutral
declared transmittances 0.85 and 0.70 respectively; they do not introduce an
authored amber filter. Window glass has **195 first-hit samples but zero
selected midtone samples**. No separately modelled grout material or grout
mesh exists in this scene, so no grout contribution can be measured or
invented. The exporter is not being credited with a resolved tile/grout detail.
[Candidate definitions and current-source equality](../out/v15cast/material-source-comparison.json).

For comparison, v12 marble midtones have linear RGB **32.438, 11.975, 2.276**
and display cast **0.0575**; v16 has **55.245, 19.586, 3.475** and **0.0566**.
Both are strongly warm in linear light too; their different camera development
explains why those values should not be compared directly with v15's display.

## Lamp sources and camera locks

The manufacturer EULUMDAT files, which describe photometry and lamp metadata,
state `ww/2700` for both selected products. Their bytes were read directly:
[source-records.json](../out/v15cast/source-records.json). The
[fixture record](../src/archpipe/fixture_record.py) selects these products and
its placed-record CCT property uses the selected product before the generic
fallback. The generic medium downlight's 3000 K value therefore does not
demonstrate a mis-binding.

| v15 fitting | Authored/exported CCT | Source and output |
| --- | ---: | --- |
| Ambient `DL-family-bath-01` | 2700 K | iGuzzini LSEVO-AAK3EW: 1,110 lamp lm × 66% output = 732.6 lm |
| Shower `DLN-family-bath-02` | 2700 K | iGuzzini LSEVO-AAIIA6: 1,460 lamp lm × 92% output = 1,343.2 lm |
| Basin `DLN-family-bath-03` | 2700 K | Same selected medium downlight, 1,343.2 lm |
| Left/right `SCONCE-family-bath-04/05` | 3000 K each | Explicit generic opal sconces; nominal 450 lm each |

All active v15 fixture driver and view dimmers are 1.0. The 2200 K toe light
is on the night layer and disabled in these views. Emitting downlight lenses
also use 2700 K. The original receipt measures each sconce's mesh emission at
about **438.77 lm**; its shared discretized-sphere appearance is retained,
not changed to clear the cast statistic.

V12 has two 2700 K wall washers and a 2700 K basin downlight, plus 3000 K
mirror and over-mirror sources. V16 has 2700 K general/basin downlights and
a 3000 K over-mirror source. Their complete individual records and emissive
materials are retained in `readback.json`; no hidden 5500 K bathroom lamp
explains the passing views.

The renderer uses CCT-derived **linear RGB blackbody approximations**, not
measured lamp spectral power distributions. For 2700 K the unit-luminance
RGB is **1.914220, 0.809936, 0.190729**; at 3000 K it is
**1.754631, 0.849265, 0.271068**. Both light and emissive-material paths use
the same conversion. The final probe receipt includes actual local light and
emission-node colours. This verifies the implemented CCT conversion, not
spectral fidelity or manufacturer colour-rendering performance.

| Original draft | State / white balance | Locked exposure, stops | QA cast |
| --- | --- | ---: | --- |
| v12 ensuite | Evening / 3000 K | −5.922120 | 0.053 PASS |
| v15 family bath | Day / 5500 K | −10.055175 | 0.111 FAIL |
| v16 guest WC | Evening / 3000 K | −5.922120 | 0.055 PASS |

All use the AgX display transform, its Medium High Contrast look,
white-balance tint 10 and the original
256-sample, 960 × 640 draft settings. Locks are shared by the full view
cohort for each exposure state, not selected anew for this diagnostic.
Evening gain is **17.5458 times** day gain. Thus the passing rooms are useful
material/binding controls, not equal-light or equal-camera controls. The
historical −10.33598/−6.00519 locks in the lighting-rebalance report belong
to an older set; they are not silently reused here.

## Fresh source isolation

[isolate.py](../out/v15cast/isolate.py) runs nine bounded 192 × 128 probes,
512 maximum samples, no denoising, 16 total/diffuse bounces, eight glossy,
16 transmission/transparent bounces and no clamping. It uses the exact saved
authored scene, production material/glass/light builders, original camera,
sun altitude 40.07° and true azimuth 135.34°, and existing layer switches.
The RTX 3090 runs under the existing shared graphics lock with eight CPU
threads. Imported assets and runtime cloth/curtains outside this bathroom
are omitted; their indirect influence from neighbouring rooms is approximate.
These EXRs are labelled source diagnostics, not replacement presentation drafts.

The following measurements use the **same 9,958 marble pixels selected as
midtones in the original draft**, even when a source-only probe darkens them.
Means include reflected light. Independent Monte Carlo samples need not sum
exactly; daylight plus lamps reconstructs the combined RGB with **0.360%**
relative vector error. Combined linear RGB is **245.686, 127.735, 53.889**;
daylight alone is **84.617, 65.643, 41.380**; lamps alone is
**160.145, 61.688, 12.400**.

| Source group | Mean linear luminance | Share of combined marble luminance | Blue/red |
| --- | ---: | ---: | ---: |
| Combined | 147.4797 | 100.00% | 0.2193 |
| Window daylight, sky and sun | 67.9249 | 46.06% | 0.4890 |
| All lamps | 79.0611 | 53.61% | 0.0774 |
| Ambient downlight and lens | 6.3630 | 4.31% | 0.0603 |
| Shower downlight and lens | 19.7544 | 13.39% | 0.0668 |
| Basin downlight and lens | 33.0742 | 22.43% | 0.0746 |
| Sconce 04 | 6.6191 | 4.49% | 0.1043 |
| Sconce 05 | 10.2520 | 6.95% | 0.1148 |
| Other lamps and emitters | 3.1752 | 2.15% | 0.0486 |

Per-fitting contributions, each grouping its analytic source with its visible
emitting lens where applicable, are recorded in
[sources.json](../out/v15cast/sources.json). The residual includes other-room
sources. Warm lamps affect ceramic and ceiling too: their lamps-only blue/red
ratios are **0.0957** and **0.0772**, versus daylight-only **0.5375** and
**0.5205**. That is a transport-wide effect, not a uniquely saturated marble map.

## Decision, review and acceptance

Independent [render critic review](../out/v15cast/visual-review.md) inspected all three original PNGs at native
resolution and checked the numerical readback. It found v15's amber warmth on
marble, ceramic and ceiling consistent with the recorded mixed-light sources.
V12/v16 appear paler under their evening development. It grants no presentation
approval: v15's QA failure remains, the stone is ASSUMED, lamp spectra are
unmeasured, and geometry/fixture-placement approval was outside this review.
The accepted bedroom comparison image was unavailable in this scoped evidence.

This satisfies the task's **“faithful consequence: say so with numbers and
stop”** branch. There is no before/after design change, no purported corrected
draft, and no after-fix v12/v16 rerender. Their exact original drafts, EXRs and
fresh QA are retained instead. No new defect guard or mutation regression is
invented for correct specified behaviour. Existing QA already fires on the
actual rejected v15 and stays quiet on the actual v12/v16 controls. No new
code tests apply because no code or specification changed.

Portable verification passed with exit status zero under both normal HOME and
an initially empty HOME, using the pinned interpreter, `PYTHONPATH=src`,
`NO_COLOR=1` and one OpenBLAS thread. Logs:
[normal](../out/v15cast/verify-portable.log),
[empty HOME](../out/v15cast/verify-empty-home.log).
`test_render_qa` and `test_villa_lighting` passed **45 tests, exit 0**:
[focused log](../out/v15cast/qa-lighting-tests.log).
The earlier combined run was terminated with exit 143 after 47 completed tests;
it is retained as interrupted evidence, not a pass. A separate verbose standard
run stopped after 41 completed tests without an exit receipt; the kernel records
a Python interpreter protection fault at 19:13:13, retained in
[runtime-fault.txt](../out/v15cast/runtime-fault.txt). That run included a periodic
stack-dump timer. The fault's root cause is unresolved; it is not a test assertion
or evidence of a colour-conversion error. Neither interrupted run is accepted.
All 61 unchanged standard tests then passed in three isolated, supervised
focused groups, without the extra timer: **21 + 20 + 20 tests, each exit 0**.
Each group's process exit status is captured even on abnormal termination;
the supervisor confirms complete, unique coverage of the module's 61 tests.
Logs: [group 1](../out/v15cast/render-standard-shard-1.log),
[group 2](../out/v15cast/render-standard-shard-2.log),
[group 3](../out/v15cast/render-standard-shard-3.log).
This gives **106 requested focused tests passed** in total. Successful retries
do not resolve the earlier interpreter fault's cause. Captured exit statuses,
log hashes and artifact hashes are in [summary.json](../out/v15cast/summary.json)
and [evidence-manifest.json](../out/v15cast/evidence-manifest.json).
Changed-document link checks and `git diff
--check` also pass. The lead owns the full suite and commits.
Protected shared symlinks were not changed, no dependencies
were installed, and no agent skill/adapters were edited.

**Lessons to register:** the existing colour-diagnosis workflow is confirmed:
trace actual material assignments and product-bound CCTs; compare linear inputs
before display scores; retain faithful warmth and its QA failure for a client
design decision. No new demonstrated renderer defect or new control is closed.
