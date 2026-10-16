# White-balance reciprocity check

**Result:** camera/source reciprocity failed at 2700, 3000 and 4300 kelvin.
The camera daylight-tint assumption was corrected at its cause; all five
registered grey-card cases now pass. Four of five room drafts pass QA; v15
improves but retains its cool-cast failure.

QA means quality assurance. RGB means red, green and blue.

## Pre-registration — before measurements, 2026-10-15

A diffuse grey card has equal linear red, green and blue reflectance of 0.5.
Only one source family illuminates it: a lamp using the unchanged production
`build_scene.kelvin_to_rgb(T)` at each of 2700, 3000, 4300 and 5500 kelvin,
or the production legacy Nishita sky with sun (40.07 degrees elevation,
135.34 degrees azimuth), viewed with 5500 kelvin white balance. T means the
source colour temperature in kelvin (K). The sky has no single authored colour
temperature; its 5500 kelvin case tests the declared daylight camera preset.

Expected display red/green, blue/green and red/blue ratios are each 1.000.
The pre-registered tolerance for every ratio is 0.950 to 1.050 inclusive.
Midtone cast (standard deviation of display channel means) must be below
0.020, the stricter production lamp-lit cool limit (also below the 0.050
daylight cool and 0.100 warm limits). These are diagnostic tolerances chosen
for this experiment, not a published architectural requirement. No threshold
will be changed after observing a result. All four lamp cases and the daylight
control must be reported separately; an actual sky spectrum is not assumed to
be a 5500 kelvin blackbody merely because the camera preset says 5500.

The camera path is production AgX, Medium High Contrast, tint 10, production
`photoreal.white_balance(T)` and `photoreal.camera_meter` with minus 0.4 stop
bias and unchanged highlight protection. Meter before white balance, as the
production villa driver does. A single view is the complete cohort in this
minimal experiment. Use a flat, frame-filling card, an orthographic camera,
a black world for lamp cases, 128 by 128 pixels, 64 samples, seed zero,
no denoising, and the shared graphics lock. Read developed PNG values through
Pillow and use the production midtone mask. Save linear EXR and source/camera
receipts as well. No material, light output, QA threshold or villa camera
will be adjusted to improve neutrality.

If any case fails, compare lamp chromaticity and camera white-point model
against primary CIE/Blender sources before deciding which implementation to
change. A daylight-only failure must first be distinguished from a different
physical sky chromaticity. Preserve failing values, test a sibling and a clean
case, and render five small production drafts after a justified correction.

The measured results and disposition follow below; the pre-registered expected
values and tolerances above were retained unchanged.

## Diagnosis checkpoint and first correction

The pre-registered lamp cases failed at 2700, 3000 and 4300 kelvin. The
5500 kelvin lamp and daylight controls passed. This falsifies the proposed
“all temperatures pass; mixed light alone explains it” branch.

| Source / camera kelvin | Before display red, green, blue | Red/green | Blue/green | Red/blue | Cast | Registered verdict |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Lamp 2700 | 0.388235, 0.392157, 0.439216 | 0.990000 | 1.120000 | 0.883929 | 0.023163 | FAIL |
| Lamp 3000 | 0.392157, 0.392157, 0.427451 | 1.000000 | 1.090000 | 0.917431 | 0.016638 | FAIL ratios |
| Lamp 4300 | 0.396078, 0.388235, 0.407843 | 1.020202 | 1.050505 | 0.971154 | 0.008058 | FAIL ratios |
| Lamp 5500 | 0.400000, 0.388235, 0.400000 | 1.030303 | 1.030303 | 1.000000 | 0.005546 | PASS |
| Nishita sky/sun, camera 5500 | 0.401198, 0.387464, 0.384711 | 1.035446 | 0.992895 | 1.042855 | 0.007211 | PASS |

CIE is the International Commission on Illumination. Chromaticity coordinates
x and y are X and Y respectively divided by the sum of the CIE tristimulus
values X, Y and Z; Y represents luminance. These coordinates describe colour
independently of light level. PNG is the developed display image format; EXR
retains linear light. GPU means graphics processor. QA means quality assurance.

The independent reference integrates Planck radiation against the official
[CIE 1931 two-degree observer, CIE 018:2019 Table 6](https://cie.co.at/datatable/cie-1931-colour-matching-functions-2-degree-observer),
360–830 nanometres at one-nanometre steps. The downloaded table matches the
published Message Digest 5 (MD5) content checksum `17cca777db64b17170f06f67ce9d3ab7`.
The [official dataset metadata](https://files.cie.co.at/Publications-datasets/CIE_xyz_1931_2deg.csv_metadata.json)
licenses the table under Creative Commons Attribution-ShareAlike 4.0; source
bytes remain in the diagnostic output folder.
Linear lamp RGB is transformed back to CIE XYZ using the linear Rec.709
(International Telecommunication Union Radiocommunication Recommendation BT.709) primaries and D65 daylight white point
(approximately 6504 kelvin) matrix; RGB uses the production unit-luminance normalization. The exact
integration, downloaded table and [reference results](../out/wbcheck/reference.json)
are retained with [the independent calculation](../out/wbcheck/reference.py).

| Kelvin | CIE Planck reference x, y | Production lamp x, y | Blender camera tint 10 x, y | Blender camera tint 0 x, y |
| ---: | --- | --- | --- | --- |
| 2700 | 0.459863, 0.410600 | 0.458552, 0.411817 | 0.465648, 0.421001 | 0.459806, 0.410510 |
| 3000 | 0.436934, 0.404075 | 0.435902, 0.405025 | 0.441773, 0.414093 | 0.436842, 0.403907 |
| 4300 | 0.368113, 0.368691 | 0.367722, 0.369081 | 0.369799, 0.376691 | 0.368049, 0.368489 |
| 5500 | 0.332436, 0.341037 | 0.332295, 0.341244 | 0.332456, 0.347454 | 0.332405, 0.340848 |

The lamp Gaussian observer approximation has a small error (largest coordinate
error 0.001311 here). The larger discrepancy is the camera's daylight tint.
[Blender 4.5.14 `whitepoint_from_temp_tint`](https://github.com/blender/blender/blob/v4.5.14/source/blender/blenlib/intern/math_color.cc#L758)
interpolates a Planckian locus at tint zero and offsets it at nonzero tint.
The pinned installation's Illuminant A preset uses 2856 kelvin, tint zero;
its D55 daylight preset uses 5501 kelvin, tint 10. A daylight offset is therefore
inappropriate for a Planckian lamp even though both inputs say the same kelvin.

**Cause:** one shared camera helper interpreted every temperature as daylight.
**Escape:** lamp RGB and camera temperature were checked separately, with no
combined neutral-card calibration. **Class and siblings:** inconsistent source
and adaptation loci; all evening, lamp-dominant and bedroom lamp callers of the
shared helper. Daylight and dusk callers need an explicit daylight model too.
This diagnosis was reported before changing production code.

The construction fix makes the illuminant explicit in
`photoreal.white_balance`: Planckian lamps use tint zero, daylight uses tint 10.
Villa evening/lamp-dominant and the bedroom lamp path select Planckian;
day/daylit exterior/dusk and bedroom daylight select daylight. Source colours,
photometry, temperatures, authored groups, materials, cameras and image-QA limits
are unchanged. No per-view parameter was fitted to these measurements.
The camera default is Planckian, making the requested equal-temperature lamp
test meaningful; production daylight callers opt into their daylight locus.

At the first corrected checkpoint, **all four lamp cards develop to
0.388235, 0.392157, 0.388235**, ratios **0.990000, 0.990000, 1.000000**,
cast **0.001849**, all PASS. Daylight is byte-identical to the original control.
The small residual is within the original tolerance; it was not tuned away.
[Before guard](../out/wbcheck/before/guard.json),
[after guard](../out/wbcheck/after/guard.json).

The new `render_qa.grey_card_check` is a separate calibration guard; it never
requires coloured rooms to be neutral. It uses the existing production PNG
decoder and midtone mask, fails without measurable midtones, and enforces the
registered cast and ratio limits. Frozen real 2700 K and 3000 K cases fire;
corrected and 5500 K controls stay quiet; a relabelled 3200 K colour mutation
also fires. Pure-Python regressions additionally execute the production camera
helper against a minimal view-settings object, so restoring the erroneous tint
fails without needing a GPU. The independent CIE reference constrains lamp
chromaticity and unit luminance. The production GPU command applies the same
guard to fresh saved PNGs and returns nonzero for a failing set.

The first wrapper startup exposed reversed arguments to `write_record` before
any render. The corrected call is exercised by a portable full-command test
that writes a real context record, passes the complete clean frozen set and
fails on the historical 2700 K PNG values. The failed startup log is retained
as diagnostic evidence, not accepted execution.

Independent review confirmed the card pixels and reference comparison. It also
found `scripts/darkviews_drafts.py` redeveloping historical daylight images via
an implicit helper default. That sibling now explicitly selects daylight;
`test_all_render_callers_name_the_source_locus` checks every renderer/script
call and pins the historical replay's daylight selection. No archived image
is redeveloped as a Planckian source by that helper-default change.

A fresh run through the reusable command completed with process exit zero and
all five cases PASS: [current GPU guard](../out/wbcheck/current/guard.json),
[execution and source hashes](../out/wbcheck/current/process.json).
The independent [card and draft review](../out/wbcheck/visual-review.md)
is retained separately from automatic QA.

## Execution notes

Work starts from `codex/wbcheck`, snapshot
`24b5a61910f7e9625ff33dc1cfc6de215241c2bb`. The sandbox hid the graphics device;
the existing production GPU admission correctly refused a CPU fallback.
Host runs used Blender 4.5.14 and the existing shared graphics lock, with
eight central-processing-unit (CPU) threads. No dependencies were installed.

The first draft command completed a fresh authored export, then correctly
refused missing `generic/GARDEN-UP.ies` in this worktree's default photometry
folder. A second supplied measurement directory contained only generic files
and correctly refused an absent iGuzzini file. Neither attempt reached GPU
rendering. The successful retry uses the complete five-file photometry set
recorded by the expogroups batch, copied byte-for-byte into an isolated
`out/wbcheck/ies` directory. [Source inventory and hashes](../out/wbcheck/photometry.json)
prove that no photometry was changed. The original generated scene is reused
without editing it; the retry uses the production scene/hash and QA admissions.
Failed attempt logs remain under `out/wbcheck`; no failed or interrupted command
is counted as acceptance.

## Five production drafts and remaining failure

All five requested frames rendered through the production driver, Blender
4.5.14, RTX 3090, 256 samples, 960 × 640 pixels. Complete authored cohorts
were metered by the unchanged exposure procedure. The renderer completed
successfully; the driver exits **1** because v15 still fails image QA. This
is completed diagnostic rendering with a retained presentation failure.

[Independent full QA replay and numerical comparison](../out/wbcheck/draft-comparison.json)
uses the exact expogroups drafts as the before set, the current authored scene,
and production `villa_qa_context`. Every check and warning is retained there.
Cast values below are display-midtones standard deviations, not colour temperatures.

| View | White balance, kelvin | Cast before → after | Direction | Full QA before → after |
| --- | ---: | ---: | --- | --- |
| [v15 family bath — diagnostic FAIL](../out/wbcheck/drafts/v15-family-bath.png) | 2739 | 0.076804 → 0.058501 | cool → cool | FAIL → FAIL: colour_cast |
| [v12 ensuite](../out/wbcheck/drafts/v12-ensuite.png) | 3000 | 0.053426 → 0.066069 | warm → warm | PASS → PASS |
| [v16 guest WC](../out/wbcheck/drafts/v16-guest-wc.png) | 3000 | 0.055169 → 0.066733 | warm → warm | PASS → PASS |
| [v05 parents bedroom, evening](../out/wbcheck/drafts/v05-parents-bedroom.png) | 3000 | 0.055386 → 0.066388 | warm → warm | PASS → PASS |
| [v09 dining, evening](../out/wbcheck/drafts/v09-dining-evening.png) | 3000 | 0.057961 → 0.068487 | warm → warm | PASS → PASS |

All five change from tint 10 to Planckian tint **0**, with their stated temperatures unchanged.
V15's complete-group exposure is −9.718289 → −9.718656 stops; the evening
cohort is −5.914052 → −5.914906 stops. These tiny fresh-meter differences
(0.000366 and 0.000854 stop) are reported rather than credited to tint. One
stop doubles camera gain. No exposure was chosen to obtain a QA pass.

**Evening views do change:** they become modestly warmer, as expected when
removing the erroneous blue correction. For the two additional controls,
v05 midtone blue falls from 0.390431 to 0.357851; v09 falls from 0.561598 to
0.532948. Their warm cast rises by 0.011003 and 0.010526 respectively. The
independent reviewer saw the same change and found no unexpected evening
delta. The bathrooms v12/v16 likewise become warmer and remain PASS. These
are coloured interiors under mixed lamp temperatures, not neutral cards.

**V15 remains visibly blue and fails:** 0.058501 exceeds the unchanged 0.050
cool limit. Its frozen meter population is 58.7151% lamp light and 41.2849%
daylight. The neutral-card failure demonstrated a real adaptation defect;
removing that defect reduces but does not erase the cool mixed-light room
under a 2739 kelvin lamp balance. This check does not authorise a new balance,
group, finish or lighting change to hide the remaining failure.

[Authored-input equality](../out/wbcheck/authored-input-equality.json) establishes
exact equality of **every** scene field except provenance against expogroups,
including appearance inputs, materials, lighting, cameras, visibility and groups.
All five [runtime comparisons](../out/wbcheck/draft-comparison.json) also have
identical evaluated mesh content hashes, complete mesh rows, curtains, cloth,
emissive sources, imported models and subject projections. The full scene
receipt changes only its authored-scene content hash because source provenance
changes: [receipt difference](../out/wbcheck/runtime-receipt-differences.json).
Thus inherited garment or geometry differences are not hidden in this comparison.
Linear EXRs remain in the retained production job
`/home/omar/archpipe/villa-render/8480d5105605199b95eebbc5/out`.

The [independent visual review](../out/wbcheck/visual-review.md) inspected all
five original-size before/after pairs. It supports the source-locus correction,
not presentation or real-design approval. Inherited subject cropping remains
outside this colour package; no camera moved. The accepted bedroom comparison
image is absent from this worktree. Source spectra, fixture emitter alignment,
new physical design and native Revit validation are outside this check.

The reviewer also found captions omitted tint and illuminant even though actual
renderer receipts contain both. `villa_caption` now copies the full measured
white point at the caption's top level. All five captions were regenerated
through that production API: [caption read-back](../out/wbcheck/caption-readback.json)
proves original caption fields, PNGs, receipts and QA unchanged, and new fields
matching the receipts. The nested legacy `render_evidence` schema is unchanged;
actual top-level temperature/tint/illuminant describe the rendered camera, while
`exposure` remains the authored preset. A frozen real omission, renamed evening
sibling and clean daylight case prove the caption regression.

## Acceptance

All required code checks passed by **process exit status**, with `NO_COLOR=1`,
`PYTHONPATH=src` and the requested interpreter
`/home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python`.
The settled new-test run supersedes its earlier five-/seven-test checkpoints.
No interrupted or failing positive check is treated as a pass.

| Check | Tests / exit status | Evidence |
| --- | --- | --- |
| New white-balance regressions | 8 / 0 | [settled log](../out/wbcheck/test_white_balance-settled.log), [runner result](../out/wbcheck/settled-new-tests-result.json) |
| test_render_qa | 27 / 0 | [log](../out/wbcheck/test_render_qa.log) |
| test_render_standard | 61 / 0 | [log](../out/wbcheck/test_render_standard.log) |
| test_villa_lighting | 18 / 0 | [log](../out/wbcheck/test_villa_lighting.log) |
| test_agent_assets | 3 / 0 | [log](../out/wbcheck/test_agent_assets.log) |
| Affected dark-view / exposure regressions | 17 / 0 | [log](../out/wbcheck/test-caption-exposure-regressions.log) |
| verify.py --portable, normal HOME | 0, ALL PASS | [log](../out/wbcheck/verify-normal.log) |
| verify.py --portable, initially empty HOME | 0, ALL PASS | [log](../out/wbcheck/verify-empty-home.log) |
| Fresh five-case GPU reciprocity guard | 0, all five PASS | [guard](../out/wbcheck/current/guard.json), [process](../out/wbcheck/current/process.json) |
| Historical actual-PNG guard reproduction | 1, expected rejection | [log](../out/wbcheck/historical-guard-replay.log), [failing cases](../out/wbcheck/before/guard.json) |

That is **134 focused tests passed**, including the affected caller/caption
regressions and adapter checks. Agent assets were synchronized after skill
edits; `sync_agent_assets.py --check` and `git diff --check` pass.
[Final acceptance](../out/wbcheck/final-acceptance.json) distinguishes code
acceptance from the retained 4/5 draft QA result.
[Artifact and changed-source hashes](../out/wbcheck/artifact-manifest.json)
bind the evidence. Protected `out/villa/round3` and `assets/user` symlinks were
not modified. No dependencies were installed, no full suite was run and no
commit was created; the lead retains full-suite and commit ownership.

**Lessons to register:** `white-balance-illuminant-reciprocity`,
`white-balance-probe-entrypoint`, `white-balance-caption-model`. Their records,
proving tests and construction controls are registered in `docs/LEARNINGS.md`
and `knowledge/exposure-group-guards.json`; the photoreal workflow and generated
Claude adapter now require source-locus calibration and complete caption white
points. The camera-model defect is controlled; v15's remaining mixed-light
presentation failure remains open.
