# Dominant-light exposure groups — client decision 2026-10-15

All **38 active drafts** were rendered through `scripts/villa_render.py` on the
RTX 3090 GPU with Blender 4.5.14, 256 samples and 960 × 640 pixels. The
registered automatic rule changes 3 active view groups.
**35/38 pass production image QA**, versus 35/38
in the lead's retained single-lock drafts. Remaining failures are listed below;
no design source or image threshold was adjusted to make a draft pass.
The three motivating views still fail: v15 has a cool cast of
0.076804; v29 has
25.4962% near-black pixels;
v36 has 18.9050%.
The new policy therefore does **not** resolve those three presentation findings.
No presentation finals or real villa design gates are approved.

QA means quality assurance; GPU means graphics processor. CCT means correlated
colour temperature, measured in kelvin (K). RGB means red, green and blue.
Linear luminance is 0.2126 times red plus 0.7152 times green plus 0.0722 times blue.
One camera exposure stop doubles gain. Near-black fraction counts production
sample pixels whose every RGB channel is at most 0.01; its failure limit is 8%.
EXR is the retained linear image format; PNG is the developed image format.
A group is the full authored camera cohort assigned by the measured rule.

## Registered rule, frozen evidence and limits

The [ADR-0013 amendment](decisions/ADR-0013-presentation-renders.md) cites
**“client decision 2026-10-15”**. The [rule](../knowledge/exposure-group-rule.json)
was written before source isolation or any new group verdict; its immutable
SHA-256 content fingerprint is `be87dd5bc2bbefe668524b5f13febf906cf30ca081c5dd7e21326501ebd5efb6`.
The [expanded baseline comparison](../out/expogroups/transport-comparison.json)
finds exact physical mesh/material/light/camera equality, but **85 separate garment
appearance records differ**: the lead saved scene predates the garment polish
already present at this branch's starting head. Its polish policy binding is
absent. [Frozen appearance comparison](../out/expogroups/appearance-baseline-comparison.json)
records every differing field. No garment was changed in this task, but clothing
views are not an exposure-only pixel comparison; inherited appearance changes
must not be credited to grouping. The earlier core-field equality statement
is explicitly superseded by this expanded comparison.

Both 0.50 thresholds are explicitly **ASSUMED photographic classifications**,
not published design standards. No threshold changed after measurement.

Independent lamps-only and daylight-only renders use the same full production
scene, camera, opened doors, switches and dimmers: 144 × 96 pixels, 256 samples,
seed zero, no denoising, 16 total bounces. Exterior daytime views also get a
sky-only render with the Nishita sun disc disabled. The common meter mask is
the lowest 97% of lamps-plus-daylight pixel luminances, excluding zero values.
Lamp fraction is summed lamp luminance divided by summed lamps plus daylight;
solar fraction is daylight minus sky-only luminance divided by daylight,
bounded between zero and one. It includes bounced sunlight.

Existing evening and exterior-dusk exposure presets are preserved, including
the day-state gallery already assigned evening. Other views with more than
0.50 lamp fraction enter lamp-dominant. Remaining exterior-day views with solar
fraction at most 0.50 enter exterior-shade; all others retain day/exterior-day.
All 41 authored cameras retain assigned cohorts. Every requested group meters
all its authored members, including retired members, for compatibility. Exactly
38 active views are delivered. This batch meters 39 cameras: the two exterior-dusk
cameras (v07/v42) are retired and their group is not requested; retired v38 still
participates in the requested exterior-day cohort.
No identifier, caption keyword or QA result assigns a group.

[Measurements and assignments](../knowledge/exposure-groups.json) are frozen by
value, with measurement fingerprint `f11c0267c9b1c14377a7022e01e27dc7c8b70d9e4f22e4f5865c1570d110b4b8`.
Original source isolates and renderer logs remain in workstation job
`/home/omar/archpipe/villa-render/4b63a93bf27ddd8bce0ca1e2`;
its source scene and fetched readings are in [measurement](../out/expogroups/measurement/).
[The source-binding migration](../out/expogroups/source-binding-migration.json)
adds runtime garment/imported appearance inputs to the fingerprint from that
identical original scene. It asserts exact equality of every measurement,
assignment, population and white balance; no measurement was regenerated.

**The measured rule does not produce every anticipated group.** V29 measures
40.4187% lamp light over the camera meter and stays day. That camera population
includes the foreground and surroundings; it is not a storage-cavity-only
measurement. V36's solar fraction is 65.3660%, so it stays exterior-day even
though its planting is intended to be shaded. Sun-derived bounced light and
other metered surfaces count; this fraction does not establish direct sunlight
on the planting. V37's solar fraction, 0.499739, is only 0.000261 below the
assumed boundary; no convergence interval was measured. Membership is frozen
to this declared measurement, rather than changed to obtain a desired verdict.

## Shared camera settings and changed groups

Exposure uses the existing `photoreal.camera_meter` unchanged: 24-sample
pre-render at 15% image scale, top 3% removed, logarithmic average, −0.4 stop
bias and unchanged capped highlight protection. Each group takes the same
upper-median statistic used by the previous state cohorts: sort the readings
and choose the higher middle reading when the count is even. A subset request
meters the whole group. Receipt validation compares the exact single-precision
camera representation of that median, not an adjustable tolerance.

Daylit groups retain 5500 K, evening 3000 K and exterior-dusk 4300 K.
Lamp-dominant uses **2739 K**, the nearest integer of authored active
emitted-flux-weighted CCT over its complete member population, with driver/view
dimming. Each source counts once per member view; analytic companion lenses
are not counted twice, and emissive-only lamps use measured area times exitance.
The AgX Medium High Contrast look and white-balance tint 10 remain unchanged.
Evening retains its 16-member cohort and 3000 K; its fresh lock is −5.914052
stops versus −5.922120 in the baseline. That small numerical change is reported,
not attributed exclusively to exposure policy: garment appearances also differ.
The two retired dusk cameras keep their declared cohort and 4300 K policy;
no active dusk draft is requested.

| Group | Active / authored members | Exposure, stops | White balance K |
| --- | ---: | ---: | ---: |
| day | 11 / 11 | -10.082933 | 5500 |
| evening | 16 / 16 | -5.914052 | 3000 |
| exterior-day | 8 / 9 | -12.654824 | 5500 |
| exterior-dusk | 0 / 2 | not requested: retired cohort | 4300 |
| exterior-shade | 2 / 2 | -9.587266 | 5500 |
| lamp-dominant | 1 / 1 | -9.718289 | 2739 |

Changed active groups: v15-family-bath (day → lamp-dominant), v37-north-garden-lounge (exterior-day → exterior-shade), v39-north-garden-hanging-retreat (exterior-day → exterior-shade).

Every receipt and caption records the group, raw rule measurements, complete
cohort, actual exposure and white balance. Guards recompute assignments,
reject stale transport/cameras, edited membership, a missing group record,
incomplete cohorts, a nonmedian exposure or multiple camera settings in one
group. Real v15/v29/v36 receipts, a renamed store sibling and clean controls
prove the guards. Valid singleton groups are accepted. The [guard registry](../knowledge/exposure-group-guards.json)
links the frozen fixture and proving tests. Production `render_qa.py` is unchanged,
including its context, all thresholds and existing warning behaviour.

## Every active view, compared with the lead

[All 38 drafts](../out/expogroups/drafts/), [complete QA values and comparisons](../out/expogroups/draft-comparison.json),
and [independently replayed QA and delivery checks](../out/expogroups/delivery-check.json).
Baseline paths are preserved per row: lead `laneR/out/villa/render-d1`, falling
back to `drafts-review` only when that view is absent from the former.
In the table, paired values read **single-lock before → new group after**.
Near-black values are percentages; median luminance and cast are dimensionless.
Every individual check, verdict and measured detail remains in the linked JSON.

| View | Group | Stops before → after | K before → after | Lamp fraction / solar fraction | QA before → after | Near black % | Median | Cast |
| --- | --- | ---: | ---: | --- | --- | ---: | ---: | ---: |
| [v01-kitchen-garden](../out/expogroups/drafts/v01-kitchen-garden.png) | day | -10.055175 → -10.082933 | 5500 → 5500 | 0.083615 / — | PASS → PASS | 0.6098 → 0.6187 | 0.261781 → 0.257875 | 0.046309 → 0.046145 |
| [v02-garden-living](../out/expogroups/drafts/v02-garden-living.png) | day | -10.055175 → -10.082933 | 5500 → 5500 | 0.021184 / — | PASS → PASS | 0.0629 → 0.0654 | 0.434557 → 0.429424 | 0.066847 → 0.066704 |
| [v03-street-lounge](../out/expogroups/drafts/v03-street-lounge.png) | day | -10.055175 → -10.082933 | 5500 → 5500 | 0.220795 / — | PASS → PASS | 3.6993 → 3.7976 | 0.124270 → 0.122052 | 0.010443 → 0.010740 |
| [v04-study-deck](../out/expogroups/drafts/v04-study-deck.png) | day | -10.055175 → -10.082933 | 5500 → 5500 | 0.000000 / — | PASS → PASS | 0.2380 → 0.2470 | 0.444783 → 0.440002 | 0.024504 → 0.024374 |
| [v05-parents-bedroom](../out/expogroups/drafts/v05-parents-bedroom.png) | evening | -5.922120 → -5.914052 | 3000 → 3000 | 0.999737 / — | PASS → PASS | 0.0174 → 0.0174 | 0.425232 → 0.426580 | 0.055338 → 0.055386 |
| [v06-kids-room](../out/expogroups/drafts/v06-kids-room.png) | day | -10.055175 → -10.082933 | 5500 → 5500 | 0.000000 / — | PASS → PASS | 0.2319 → 0.2432 | 0.491198 → 0.485326 | 0.038089 → 0.037969 |
| [v08-cinema](../out/expogroups/drafts/v08-cinema.png) | evening | -5.922120 → -5.914052 | 3000 → 3000 | 1.000000 / — | PASS → PASS | 0.7136 → 0.7045 | 0.263387 → 0.264289 | 0.073130 → 0.073191 |
| [v09-dining-evening](../out/expogroups/drafts/v09-dining-evening.png) | evening | -5.922120 → -5.914052 | 3000 → 3000 | 0.999818 / — | PASS → PASS | 0.0225 → 0.0244 | 0.692753 → 0.694261 | 0.057953 → 0.057961 |
| [v10-living-evening](../out/expogroups/drafts/v10-living-evening.png) | evening | -5.922120 → -5.914052 | 3000 → 3000 | 0.999736 / — | PASS → PASS | 0.0108 → 0.0103 | 0.424331 → 0.426086 | 0.068763 → 0.068895 |
| [v11-stair-void](../out/expogroups/drafts/v11-stair-void.png) | evening | -5.922120 → -5.914052 | 3000 → 3000 | 0.999772 / — | PASS → PASS | 0.1841 → 0.1834 | 0.700684 → 0.702387 | 0.061736 → 0.061938 |
| [v12-ensuite](../out/expogroups/drafts/v12-ensuite.png) | evening | -5.922120 → -5.914052 | 3000 → 3000 | 1.000000 / — | PASS → PASS | 0.0000 → 0.0000 | 0.507961 → 0.510729 | 0.053370 → 0.053426 |
| [v13-kids-b](../out/expogroups/drafts/v13-kids-b.png) | evening | -5.922120 → -5.914052 | 3000 → 3000 | 0.999565 / — | PASS → PASS | 0.0638 → 0.0629 | 0.391574 → 0.393139 | 0.071897 → 0.072014 |
| [v15-family-bath](../out/expogroups/drafts/v15-family-bath.png) | lamp-dominant | -10.055175 → -9.718289 | 5500 → 2739 | 0.587151 / — | FAIL: colour_cast → FAIL: colour_cast | 0.0030 → 0.0000 | 0.304907 → 0.388896 | 0.111388 → 0.076804 |
| [v16-guest-wc](../out/expogroups/drafts/v16-guest-wc.png) | evening | -5.922120 → -5.914052 | 3000 → 3000 | 0.999967 / — | PASS → PASS | 0.0000 → 0.0000 | 0.684431 → 0.685265 | 0.055222 → 0.055169 |
| [v17-dirty-kitchen](../out/expogroups/drafts/v17-dirty-kitchen.png) | day | -10.055175 → -10.082933 | 5500 → 5500 | 0.028099 / — | PASS → PASS | 0.6384 → 0.6606 | 0.422334 → 0.417563 | 0.028303 → 0.028186 |
| [v18-study-evening](../out/expogroups/drafts/v18-study-evening.png) | evening | -5.916996 → -5.914052 | 3000 → 3000 | 0.987737 / — | PASS → PASS | 0.0009 → 0.0005 | 0.417353 → 0.418322 | 0.066837 → 0.066843 |
| [v19-garden-facade](../out/expogroups/drafts/v19-garden-facade.png) | exterior-day | -12.372886 → -12.654824 | 5500 → 5500 | 0.000000 / 0.829216 | PASS → PASS | 5.8422 → 6.3921 | 0.343737 → 0.301476 | 0.021467 → 0.023092 |
| [v20-kitchen-run](../out/expogroups/drafts/v20-kitchen-run.png) | evening | -5.916996 → -5.914052 | 3000 → 3000 | 0.999641 / — | PASS → PASS | 0.0216 → 0.0239 | 0.795707 → 0.795440 | 0.049751 → 0.049702 |
| [v21-lounge-evening](../out/expogroups/drafts/v21-lounge-evening.png) | evening | -5.916996 → -5.914052 | 3000 → 3000 | 0.999868 / — | PASS → PASS | 0.0851 → 0.0978 | 0.556687 → 0.556404 | 0.057271 → 0.057301 |
| [v22-parents-day](../out/expogroups/drafts/v22-parents-day.png) | day | -10.055175 → -10.082933 | 5500 → 5500 | 0.000000 / — | PASS → PASS | 0.0005 → 0.0005 | 0.755359 → 0.751773 | 0.045231 → 0.045111 |
| [v23-gf-gallery](../out/expogroups/drafts/v23-gf-gallery.png) | evening | -5.916996 → -5.914052 | 3000 → 3000 | 0.900784 / — | PASS → PASS | 0.0000 → 0.0000 | 0.759009 → 0.759292 | 0.036888 → 0.036904 |
| [v24-bar-alcove](../out/expogroups/drafts/v24-bar-alcove.png) | evening | -5.916996 → -5.914052 | 3000 → 3000 | 0.999801 / — | PASS → PASS | 0.0293 → 0.0263 | 0.395033 → 0.395300 | 0.068253 → 0.068247 |
| [v25-top-garden-gate](../out/expogroups/drafts/v25-top-garden-gate.png) | exterior-day | -12.372886 → -12.654824 | 5500 → 5500 | 0.000000 / 0.788094 | PASS → PASS | 0.0026 → 0.0075 | 0.759101 → 0.725207 | 0.009534 → 0.007541 |
| [v26-top-garden-east](../out/expogroups/drafts/v26-top-garden-east.png) | exterior-day | -12.372886 → -12.654824 | 5500 → 5500 | 0.000000 / 0.810110 | PASS → PASS | 0.0267 → 0.0490 | 0.539853 → 0.489938 | 0.014516 → 0.012209 |
| [v27-east-yard-above](../out/expogroups/drafts/v27-east-yard-above.png) | exterior-day | -12.372886 → -12.654824 | 5500 → 5500 | 0.000000 / 0.916237 | PASS → PASS | 0.4301 → 0.8044 | 0.505729 → 0.454700 | 0.025088 → 0.023579 |
| [v28-east-yard-below](../out/expogroups/drafts/v28-east-yard-below.png) | exterior-day | -12.372886 → -12.654824 | 5500 → 5500 | 0.000000 / 0.864954 | PASS → PASS | 2.0256 → 2.9186 | 0.440131 → 0.391806 | 0.019767 → 0.018021 |
| [v29-under-stair-store](../out/expogroups/drafts/v29-under-stair-store.png) | day | -10.055175 → -10.082933 | 5500 → 5500 | 0.404187 / — | FAIL: crushed_shadows → FAIL: crushed_shadows | 25.0084 → 25.4962 | 0.040034 → 0.038845 | 0.026031 → 0.025896 |
| [v30-under-ramp-store](../out/expogroups/drafts/v30-under-ramp-store.png) | evening | -5.916996 → -5.914052 | 3000 → 3000 | 0.999993 / — | PASS → PASS | 4.6876 → 4.6712 | 0.059940 → 0.059940 | 0.006436 → 0.006451 |
| [v31-dressing-hers](../out/expogroups/drafts/v31-dressing-hers.png) | evening | -5.922120 → -5.914052 | 3000 → 3000 | 1.000000 / — | PASS → PASS | 0.0206 → 0.0129 | 0.212917 → 0.215933 | 0.053105 → 0.053454 |
| [v32-dressing-his](../out/expogroups/drafts/v32-dressing-his.png) | evening | -5.916996 → -5.914052 | 3000 → 3000 | 1.000000 / — | PASS → PASS | 3.5582 → 4.4765 | 0.175616 → 0.179131 | 0.061190 → 0.060789 |
| [v33-basement-north-south](../out/expogroups/drafts/v33-basement-north-south.png) | day | -10.055175 → -10.082933 | 5500 → 5500 | 0.024817 / — | PASS → PASS | 0.0197 → 0.0204 | 0.448430 → 0.443571 | 0.064869 → 0.064681 |
| [v34-basement-south-north](../out/expogroups/drafts/v34-basement-south-north.png) | day | -10.055175 → -10.082933 | 5500 → 5500 | 0.012346 / — | PASS → PASS | 0.0094 → 0.0120 | 0.434813 → 0.429770 | 0.065275 → 0.065140 |
| [v35-family-bath-wc](../out/expogroups/drafts/v35-family-bath-wc.png) | day | -10.055175 → -10.082933 | 5500 → 5500 | 0.415767 / — | PASS → PASS | 0.0000 → 0.0000 | 0.298351 → 0.294430 | 0.091437 → 0.090370 |
| [v36-north-garden](../out/expogroups/drafts/v36-north-garden.png) | exterior-day | -12.372886 → -12.654824 | 5500 → 5500 | 0.000001 / 0.653660 | FAIL: crushed_shadows → FAIL: crushed_shadows | 12.3909 → 18.9050 | 0.141516 → 0.119371 | 0.012568 → 0.012525 |
| [v37-north-garden-lounge](../out/expogroups/drafts/v37-north-garden-lounge.png) | exterior-shade | -12.372886 → -9.587266 | 5500 → 5500 | 0.000001 / 0.499739 | PASS → PASS | 7.3403 → 0.1034 | 0.146035 → 0.535743 | 0.028414 → 0.037190 |
| [v39-north-garden-hanging-retreat](../out/expogroups/drafts/v39-north-garden-hanging-retreat.png) | exterior-shade | -12.372886 → -9.587266 | 5500 → 5500 | 0.000001 / 0.487666 | PASS → PASS | 6.0659 → 0.0115 | 0.117153 → 0.469101 | 0.000000 → 0.040692 |
| [v40-south-garden-espalier](../out/expogroups/drafts/v40-south-garden-espalier.png) | exterior-day | -12.372886 → -12.654824 | 5500 → 5500 | 0.000000 / 0.777415 | PASS → PASS | 0.6846 → 1.0141 | 0.516895 → 0.465915 | 0.022688 → 0.021921 |
| [v41-south-garden-terrace](../out/expogroups/drafts/v41-south-garden-terrace.png) | exterior-day | -12.372886 → -12.654824 | 5500 → 5500 | 0.000000 / 0.622819 | PASS → PASS | 0.8182 → 1.1674 | 0.340371 → 0.298366 | 0.020535 → 0.015977 |

## Remaining failures, with unchanged limits

- **v15-family-bath** (lamp-dominant): colour_cast: mid-tone cast 0.077 (cool; limit 0.1 warm, 0.05 cool).
- **v29-under-stair-store** (day): crushed_shadows: 25.5% of pixels near black (limit 8%).
- **v36-north-garden** (exterior-day): crushed_shadows: 18.9% of pixels near black (limit 8%).

## Visual checkpoints and contact sheet

The four-view checkpoint compares v01, v15, v29 and v36 at native resolution,
under the same frozen rules and complete group memberships as the batch. Its separate
review precedes the 38-view batch. Each job meters afresh: [pilot/batch readings](../out/expogroups/pilot-batch-meter-comparison.json) differ by at most 0.001062 stop; no cause is inferred for that small difference. The final critic reviewed the contact sheet
and every native-size draft; [visual review](../out/expogroups/visual-review.md)
retains its findings and limits. An image-QA pass does not establish photographic
approval. Failures remain visible diagnostic findings.

![All 38 grouped GPU drafts, with group, exposure, white balance and QA labels](../out/expogroups/contact-sheet.jpg)

## Acceptance and execution limits

All 199 focused tests pass, as do both portable verification runs.

| Check | Exit status / evidence |
| --- | --- |
| test_render_qa | 0; 27 tests; [log](../out/expogroups/test_render_qa.log) |
| test_villa_exposure_assets | 0; 7 tests; [log](../out/expogroups/test_villa_exposure_assets.log) |
| test_agent_assets | 0; 3 tests; [log](../out/expogroups/test_agent_assets.log) |
| test_render_views | 0; 20 tests; [log](../out/expogroups/test_render_views-settled.log) |
| test_villa_lighting | 0; 18 tests; [log](../out/expogroups/test_villa_lighting.log) |
| test_render_standard | 0; 61 tests; [log](../out/expogroups/test_render_standard.log) |
| test_garden_views | 0; 12 tests; [log](../out/expogroups/test_garden_views.log) |
| test_darkviews | 0; 10 tests; [log](../out/expogroups/test_darkviews.log) |
| test_exposure_groups | 0; 10 tests; [log](../out/expogroups/test_exposure_groups.log) |
| test_villa_render_scene | 0; 31 tests; [log](../out/expogroups/test_villa_render_scene.log) |
| verify.py --portable, normal | 0; [log](../out/expogroups/verify-normal.log) |
| verify.py --portable, empty-home | 0; [log](../out/expogroups/verify-empty-home.log) |

Command exit statuses, group/source fingerprints and artifact hashes are retained
in [acceptance](../out/expogroups/acceptance.json). GPU render execution and image
QA are separate: a driver exit of 1 retains completed drafts whose QA failed.
The earlier deliberately interrupted export/verification attempts are retained
under `interrupted-before-source-binding/`; they are not counted as passes.
The two initial test no-op mutations are preserved and corrected from real
membership, without changing a rule or camera setting. The initial complete-fixture
collector also mistook `villa-render.stage-result.json` for a view because of a
filename prefix; it now collects exact declared active identifiers, and the
real-receipt test proves the complete unique 38-view inventory. The incomplete
fixture test log remains retained. The intermediate raw-view verification
failures and one unexplained supervisor exit 143 remain under
`failed-cohort-verification/` and `failed-raw-view-call/`; no interrupted result
is counted as passed and no external termination cause is asserted.

Canonical render workflows and their Claude adapters were synchronized.
No dependencies were installed, no protected shared symlink was changed,
no full-suite run or commit was performed. Full-suite and commit ownership
remain with the lead. Native Revit and presentation finals are outside this package.

**Lessons to register:** `dominant-light-exposure-policy`,
`dominant-light-source-binding`, and `dominant-light-final-view-context`; anticipated categories and singleton cohorts
must not become hard-coded test expectations. Source-majority grouping does
not guarantee subject-specific adaptation or a passing image.
