# Lighting rebalance diagnosis — 2026-10-09

Current instrumentation result (2026-10-11): **25/25 targets met in a fresh complete measurement**, applying the lead's same-host covered-point rule. The [covered dining continuation](#covered-dining-task-point--lead-decision-applied-2026-10-11) records the offset and acceptance; earlier diagnoses and refusals below are retained historical evidence.

Baseline: `codex/lightbal`, clean `d400cec0ec84ad4ab86cc52f2f675c57bd2ae23f` (integration 4). **No lighting-design correction is applied.** The v15 warmth is reproduced at its physical sources, not traced to an erroneous lamp, material or colour conversion. A separate production measurement defect hides 17 of 25 sensors beneath finished task surfaces. Diagnostic probes at the measured surfaces support review; they do not repair or approve the production measurement gate. The existing maximum task ratio is explicitly **ASSUMED 3.0**, with an unresolved source, so it cannot be presented as a cited maximum that authorises automatic dimming.

Lux (lx) measures illuminance; lumens (lm) measure emitted light. CCT means correlated colour temperature, in kelvin (K). RGB means red, green and blue channels. Linear RGB values here precede camera development; they are not lux. Display luminance is a weighted pixel brightness between zero and one. EXR denotes linear high dynamic range image files; PNG denotes developed image files. Coordinates give the two horizontal model axes followed by elevation, in metres; ground-floor finished floor is zero and basement finished floor is −3 m. A millimetre is 0.001 m. One exposure stop doubles camera gain. QA means quality assurance. PASS, WARN and FAIL are the existing check classifications; a warning is retained, not waived.

D1 identifies the example villa option; C4/C4i identify historical bathroom/finish work packages. IES names the Illuminating Engineering Society and, for light files, its photometric file format. Fixture prefixes are project identifiers: DL is a wide downlight, DLN a medium task downlight, WW a wall washer and VANITY-LIN a linear vanity light. A dimmer is a fraction of declared full output: 1.0 is full, 0.4 is 40%, zero is off. View layer dimmers multiply the fitting's driver setting; exported source flux already includes that driver setting. In tables, direct / total lists those two separate measurements; total / target is measured total illuminance divided by the card value. Blue/red is blue-channel mean divided by red-channel mean.

The bedroom remains an end-to-end capability example. This diagnosis approves no real villa design gate.

## Evidence and source authority

The requested local `out/villa/render-d1` has a historical scene but no presentation images. A fresh export to `out/lighting-rebalance/scene.json` passes `validate_scene` and records source hash `be9d392b48f24f3f0b0959bc92e673528926a546e09e3b57f864fc674d05f137`, clean baseline provenance. The local historical scene instead records `7ae430d` and dirty source; it is not substituted for current geometry.

The earlier job was found at `/home/omar/archpipe/logs/lanes/laneB-v15cast.log`, with retained probes under `/home/omar/archpipe/work/laneB/out/v15-cast`. Its report is recoverable with `git show a14f549:docs/v15-cast-report.md`; a local historical copy is in [prior-v15-cast-report.md](../out/lighting-rebalance/prior-v15-cast-report.md). The report was not present in the current working tree. The named production job is `b1ee556e3d7886fde1d5b502`, clean `1a4ba1a`, 256 samples at 960 × 640 pixels. Its raw evidence, rather than a recollected diagnosis, was read.

Task targets come from the existing verified cards in [knowledge/library.json](../knowledge/library.json), IES Lighting Handbook, 10th edition (2011), Table 33.2, printed pages 33.8, 33.10 and 33.12, with the card-specific plane and age 25–65 column. They are maintained residential recommendations, not legal requirements or maximum illuminance limits. The vanity card's horizontal target is 300 lx; its separate 400 lx vertical face target is not tested by these horizontal probes. The cards record original-page checking and `tests/test_evidence_values.py`. This workstation lacks the private book/index at the default `archpipe-sources` path; the attempted original-page read failed and is retained in the execution record. No new standard or numerical design rule is claimed from that failed read.

The upper-ratio screen in [villa_lighting.check](../src/archpipe/concept/villa_lighting.py) says `ASSUMED maximum 3.0` and `TODO ies-task-excess-ratio`. There is no corresponding verified card in the library. Its 16 analytical flags are useful prompts for review, not a verified maximum ratio. General room floor averages are advisory; in particular, a full functional working-light state must not be compared as if it were a film or digital-game scene.

Current binding uses the held manufacturer photometric files: [LSEVO-AAK3EW](../assets/user/luminaires/iguzzini/LSEVO-AAK3EW/LSEVO-AAK3EW.ldt) and [LSEVO-AAIIA6](../assets/user/luminaires/iguzzini/LSEVO-AAIIA6/LSEVO-AAIIA6.ldt) both specify `ww/2700`. The former has 1110 lamp lumens and 66% output ratio, giving 732.6 outgoing lumens; the latter has 1460 and 92%, giving 1343.2. The DLN generic fallback's 3000 K is superseded by the explicitly bound 2700 K product in both consumers. This longstanding choice was already investigated in the prior v15 job; it is not evidence for silently changing a lamp to 3000 K. CCT is carded/authored by fixture kind and selected product, not by the illuminance cards. Generic fixture assumptions remain labelled.

## Source isolation for v15

Current-versus-production comparison by value finds the family-bath IES lights, luminous sconce meshes/materials, marble and glass definitions, exposure preset, sky and north bearing unchanged. The v15 camera geometry is unchanged. The hidden door identifier and migration receipts differ; bathroom furniture, finished solids and metadata also differ. Consequently the historical image's 0.110 cast score is reproduced as historical QA, not claimed as a freshly rendered current image. Full comparison: [v15-input-comparison.json](../out/lighting-rebalance/v15-input-comparison.json).

New current-geometry probes use all authored meshes, real source spectra/distributions, production glass, existing view dimmers, 192 × 128 pixels, 512 samples, no denoising, 16 total/diffuse bounces, eight glossy and 16 transmission/transparent bounces, with clamping off. Imported models, props, cloth and curtains are omitted from this bounded colour-transport diagnostic; none is in the family bathroom, but small neighbouring-room contributions remain approximate. Sky-only disables all lamp emissions; lamps-only disables the sky and sun. All active emission nodes are included in source switching, including per-mesh sconces and visible lens shaders. Outputs are linear EXRs only. No presentation image or re-metered camera lock is produced.

The mask is 13,989 pixels whose actual first visible surface is `marble-bath`. Luminance is 0.2126 times red plus 0.7152 times green plus 0.0722 times blue. Source shares divide each group's masked mean luminance by the full masked mean; independently sampled shares need not add to exactly 100%.

| Current isolated source | Mean linear RGB on visible marble | Mean linear luminance | Share of full marble luminance |
| --- | --- | --- | --- |
| Combined | 211.9813, 108.2728, 44.4074 | 125.7101 | 100.0% |
| Daylight only | 69.9027, 53.7724, 33.4618 | 55.7353 | 44.34% |
| Lamps only | 141.1563, 54.1326, 10.8595 | 69.5095 | 55.29% |
| Ambient downlight | 12.9189, 4.5966, 0.7688 | 6.0895 | 4.84% |
| Shower downlight | 37.8404, 13.8925, 2.4724 | 18.1593 | 14.45% |
| Basin downlight | 52.9962, 20.2098, 3.8640 | 26.0000 | 20.68% |
| Two 3000 K sconces | 30.8865, 13.3425, 3.4290 | 16.3566 | 13.01% |
| Other lamps/visible emitters | 6.9327, 2.2348, 0.3460 | 3.0972 | 2.46% |

Daylight plus lamps reconstructs the combined mean RGB with 0.4116% vector-relative error. Blue/red ratios are 0.2095 combined, 0.4787 daylight-only and 0.0769 lamps-only. This confirms the earlier source attribution on current authored geometry: warm lamps mixed with daylight, amplified by cream marble, viewed using the specified day camera preset. It does not demonstrate a rendering conversion defect. Data and eight linear probes: [contributions.json](../out/lighting-rebalance/v15-current-source-probes/contributions.json).

The retained texture read-back measured final marble mean linear RGB 0.6546, 0.6172, 0.5422 at luminance 0.6197 versus authored reflectance 0.62, with zero clamped texels. Ray hits identify the same `marble-bath` / Marble014 on visible v12, v15 and v16 walls. The named `marble-ensuite` definition alone does not establish the actual wall assignment. Current material definitions are equal to those measured definitions.

The earlier exact archived pre-C4 diagnostic cast was 0.113, after C4i 0.114, and current-at-that-time 0.114 under the same saved development. Warmth predates those finish changes. Its source isolation gave daylight-only cast 0.030, lamps-only 0.186, and a luminance-preserving equal-channel marble counterfactual 0.087 versus specified-scene 0.114. These nonlinear display-score changes are not additive causal percentages and are not proposed finish replacements.

Historical v15 uses day balance 5500 K and gain −10.33598 stops, with median display luminance 0.26 (WARN against 0.30). v12/v16 use 3000 K and −6.00519 stops, a 20.12-fold higher gain. Their 0.048/0.049 warm scores do not establish equal-camera marble brightness. v35, at the same day gain/preset as v15, scores 0.079 warm but frames a different surface population. The current isolation probes do not change any of those locks or claim a new image pass.

**Proposed action at the cause:** retain the specified sources and finish, and disclose the faithful mixed-light warmth with its retained QA failure. If the client wants a cooler daytime bathroom, the lead should propose a different daylight lamp scene or product/finish choice and obtain a design decision, followed by measured lighting proof and neutral preview review. That is a room-character choice. Neither dimming warm lamps solely to make the cast statistic pass nor changing white balance/exposure is justified as a bug fix.

## A separate measurement defect

The unmodified furnished-scene run reports `all_targets_met=false`: induction 20.2 direct / 128.6 total against 300 lx, dining homework 164.9 / 198.4 against 200. Actual camera-to-sensor ray inspection finds opaque surfaces 1 mm above both sensors. The induction task plane is −2.074 m; its sensor is −2.073, while the rendered black hob top is −2.072. Dining homework's nominal plane is −2.250; its sensor is −2.249, while the rendered walnut top is −2.248. The camera at nominal plane plus 25 mm sees the host surface instead of the calibrated 0.5-reflectance sensor. Converting those pixels as if they were the sensor yields false lux.

The same root occurs at **17 of 25** centres: all seven island points, both dining points, the dirty-kitchen run, two study desks, three children's desks and two cinema desk points. Eight remaining central sensors are geometrically clear. Source-facing segment probes independently find the same local blocking faces; induction's first vertical hit is exactly 1 mm above its sensor. Evidence: [sensor-audit.json](../out/lighting-rebalance/sensor-audit.json), [task-paths.json](../out/lighting-rebalance/task-paths.json), and the unmodified [production readings](../out/lighting-rebalance/current-measurements/lighting-measurements.json).

Cause: floor-mounted furniture is correctly rebound to the rendered finished floor 2 mm above nominal floor. The measurement consumer still adds only 1 mm to nominal task heights, and does not check which object its camera sees. The unoccluded analytical minimum tests cannot see this; calibration of a clean isolated sensor cannot establish ownership in a furnished scene. Class: a measurement consumer retains nominal coordinates after the geometry producer binds to a measured finish datum. This is instrumentation, not proof of a dim induction zone or a displaced fitting.

Diagnostic rerun: for just those 17 points, bind the virtual task plane to the actual upward task-surface hit. The host is 2 mm above the nominal plane in each case; the existing sensor remains 1 mm above that measured plane. All lights, meshes, materials and targets stay identical. The diagnostic permits a measured horizontal surface only within 10 mm of nominal, refusing a more remote obstruction instead of moving a sensor around an appliance. That 10 mm bound is a diagnostic safety bound, not a published design dimension. A second independent geometry audit finds **zero of 25** central sensors hidden. The raw readings and corrected diagnostic readings are kept separately in the table.

The diagnostic run meets all 25 minimum targets. Induction changes from invalid apparent 128.6 to **1302.7 lx**, dining homework from invalid 198.4 to **587.7 lx**, and study desks from invalid 447.3/489.8 to **1012.9/975.5 lx**. Some apparent readings were too high rather than too low: the first island seating point changes from invalid 1737.4 to **1097.3 lx**. A hidden sensor can read any host material's reflectance; detecting only zero or low lux would miss siblings. The untouched family basin remains **1616.4 lx**, guest basin **1599.5 lx**, and existing dimmed ensuite basin **757.8 lx**. These are measured functional-scene figures for review, with generic photometry and assumed reflectances still disclosed.

**Historical diagnosis status: OPEN at the time of the audit.** The proposed construction fix is explicit task-host/surface ownership at scene export, with the probe plane derived from that actual surface. The earliest scene/measurement guard should fail closed when a camera pixel or source path hits its host before the sensor. Prove against these frozen island/dining cases, translated or renamed hosts, clear cases and mutations before integrating. No producer, meter or guard was changed in the original diagnosis package; the guard registry was left untouched. The diagnostic ownership audit is evidence; the later production repair and its regressions are recorded below.

## Room and task measurements

Illuminance figures use maintenance factor 0.8. The analytical calculation is unoccluded direct light. The production probe found 17 of 25 sensors hidden beneath actual task surfaces; its raw column is **apparent lux, invalid where marked**, not an illuminance verdict. The diagnostic probes bind those 17 planes to measured surfaces without changing geometry, materials, lights or camera exposure. Both Cycles sets use black sky and direct/16-bounce total light. Fixture driver dimmers are retained; view dimmers are excluded from this functional test. A floor average is diagnostic, even when its card names a different plane. Source card identifiers and exact task positions are retained in the JSON evidence.

| Room | Task | Card | Target lx | Analytical lx | Raw production total / validity | Surface-bound diagnostic direct / total lx | Diagnostic total / target | Diagnostic minimum |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| kitchen | island prep side | ies-res-kitchen-prep-500 | 500 | 1137 | 2107.2 INVALID | 1077.2 / 1363.6 | 2.73 | PASS |
| kitchen | island seating side | ies-res-breakfast-200 | 200 | 904 | 1737.4 INVALID | 838.0 / 1097.3 | 5.49 | PASS |
| kitchen | island prep side | ies-res-kitchen-prep-500 | 500 | 1149 | 2020.7 INVALID | 1033.6 / 1227.1 | 2.45 | PASS |
| kitchen | island seating side | ies-res-breakfast-200 | 200 | 920 | 1725.6 INVALID | 850.9 / 1113.9 | 5.57 | PASS |
| kitchen | island prep side | ies-res-kitchen-prep-500 | 500 | 921 | 1444.3 INVALID | 835.4 / 1114.1 | 2.23 | PASS |
| kitchen | island seating side | ies-res-breakfast-200 | 200 | 760 | 1268.6 INVALID | 676.6 / 928.9 | 4.64 | PASS |
| kitchen | single induction zone | ies-res-kitchen-cooktop-300 | 300 | 1156 | 128.6 INVALID | 1004.7 / 1302.7 | 4.34 | PASS |
| kitchen | sink | ies-res-kitchen-sink-300 | 300 | 1157 | 1344.6 sensor clear | 1153.6 / 1344.1 | 4.48 | PASS |
| dining | dining table centre | ies-res-dining-informal-100 | 100 | 797 | 467.5 INVALID | 405.8 / 467.5 | 4.67 | PASS |
| dining | table end (homework) | ies-res-dining-study-200 | 200 | 247 | 198.4 INVALID | 462.1 / 587.7 | 2.94 | PASS |
| dirty-kitchen | dirty kitchen run | ies-res-kitchen-prep-500 | 500 | 689 | 1135.5 INVALID | 679.0 / 812.5 | 1.62 | PASS |
| study-game | study-desk | ies-res-desk-400 | 400 | 919 | 447.3 INVALID | 931.6 / 1012.9 | 2.53 | PASS |
| study-game | study-adult-desk | ies-res-desk-400 | 400 | 902 | 489.8 INVALID | 905.8 / 975.5 | 2.44 | PASS |
| kids-a | ka-desk-1 | ies-res-desk-400 | 400 | 1214 | 1590.0 INVALID | 1391.5 / 1506.3 | 3.77 | PASS |
| kids-a | ka-desk-2 | ies-res-desk-400 | 400 | 1214 | 1613.7 INVALID | 1390.4 / 1511.4 | 3.78 | PASS |
| kids-b | kb-desk | ies-res-desk-400 | 400 | 1212 | 1588.9 INVALID | 1389.4 / 1500.9 | 3.75 | PASS |
| parents-bed | pillow | ies-res-bed-reading-200 | 200 | 1091 | 1191.0 sensor clear | 1111.0 / 1191.2 | 5.96 | PASS |
| parents-bed | pillow | ies-res-bed-reading-200 | 200 | 1086 | 1189.4 sensor clear | 1115.0 / 1187.8 | 5.94 | PASS |
| family-bath | fb-basin | ies-res-vanity-grooming-300 | 300 | 1270 | 1616.4 sensor clear | 1337.5 / 1616.4 | 5.39 | PASS |
| parents-ensuite | pe-basin | ies-res-vanity-grooming-300 | 300 | 676 | 757.8 sensor clear | 631.2 / 757.8 | 2.53 | PASS |
| guest-wc | gwc-basin | ies-res-vanity-grooming-300 | 300 | 1298 | 1599.5 sensor clear | 1375.2 / 1599.5 | 5.33 | PASS |
| lounge | armchair | ies-res-chair-reading-200 | 200 | 619 | 953.4 sensor clear | 787.6 / 953.4 | 4.77 | PASS |
| bar-alcove | daybed nook | ies-res-chair-reading-200 | 200 | 255 | 426.5 sensor clear | 327.6 / 425.6 | 2.13 | PASS |
| cinema | cinema desk | ies-res-desk-400 | 400 | 1305 | 1564.5 INVALID | 1483.9 / 1521.8 | 3.80 | PASS |
| cinema | cinema desk | ies-res-desk-400 | 400 | 1321 | 1567.3 INVALID | 1492.4 / 1526.1 | 3.82 | PASS |

| Room | General card | Target / analytical floor lx | Functional CCT mix | Fixture driver dimmers |
| --- | --- | --- | --- | --- |
| bar-alcove | No room card | — | 2700 K (12 fittings) | DLN-bar-alcove-11=0.4; DLN-bar-alcove-12=0.4 |
| cinema | ies-res-media-lcd-20 | 20 / 199 | 2700 K (5 fittings); 3000 K (2 fittings) | 1.0 for every fitting |
| corridor | ies-res-passage-30 | 30 / 203 | 2700 K (6 fittings) | 1.0 for every fitting |
| dining | No room card | — | 2700 K (2 fittings) | 1.0 for every fitting |
| dining-side | No room card | — | 2700 K (3 fittings) | 1.0 for every fitting |
| dirty-kitchen | ies-res-laundry-200 | 200 / 438 | 2700 K (6 fittings) | 1.0 for every fitting |
| entry-b | No room card | — | 2700 K (2 fittings) | 1.0 for every fitting |
| family | ies-res-family-room-100 | 100 / 333 | 2700 K (2 fittings) | 1.0 for every fitting |
| family-bath | ies-res-shower-50 | 50 / 409 | 2700 K (3 fittings); 3000 K (2 fittings) | 1.0 for every fitting |
| gallery-end | No room card | — | 2700 K (1 fittings) | 1.0 for every fitting |
| guest-wc | ies-res-shower-50 | 50 / 253 | 2700 K (2 fittings); 3000 K (1 fittings) | 1.0 for every fitting |
| hall-b | ies-res-passage-30 | 30 / 325 | 2700 K (2 fittings) | 1.0 for every fitting |
| kids-a | ies-res-bedroom-general-50 | 50 / 135 | 2700 K (2 fittings); 3000 K (2 fittings) | 1.0 for every fitting |
| kids-b | ies-res-bedroom-general-50 | 50 / 141 | 2700 K (2 fittings); 3000 K (1 fittings) | 1.0 for every fitting |
| kitchen | ies-res-kitchen-general-50 | 50 / 653 | 2700 K (11 fittings) | 1.0 for every fitting |
| kitchen-island | ies-res-kitchen-general-50 | 50 / 279 | 2700 K (2 fittings) | 1.0 for every fitting |
| landing-gf | No room card | — | 2700 K (1 fittings) | 1.0 for every fitting |
| living | ies-res-living-30 | 30 / 131 | 2700 K (6 fittings) | 1.0 for every fitting |
| lounge | ies-res-family-room-100 | 100 / 181 | 2700 K (9 fittings) | 1.0 for every fitting |
| lounge-nook | No room card | — | 2700 K (2 fittings) | 1.0 for every fitting |
| pantry | ies-res-storage-frequent-50 | 50 / 226 | 2700 K (2 fittings) | 1.0 for every fitting |
| parents-bed | ies-res-bedroom-general-50 | 50 / 204 | 2700 K (8 fittings) | 1.0 for every fitting |
| parents-dressing | ies-res-dressing-general-100 | 100 / 400 | 2700 K (2 fittings); 3000 K (5 fittings) | 1.0 for every fitting |
| parents-dressing-ext | No room card | — | 3000 K (2 fittings) | 1.0 for every fitting |
| parents-ensuite | ies-res-shower-50 | 50 / 112 | 2700 K (3 fittings); 3000 K (2 fittings) | WW-parents-ensuite-01=0.4; WW-parents-ensuite-02=0.4; DLN-parents-ensuite-03=0.4; VANITY-LIN-parents-ensuite-04=0.4; MIRROR-parents-ensuite-06=0.4 |
| parents-entry | No room card | — | 2700 K (1 fittings) | 1.0 for every fitting |
| stair-b | No room card | — | 2700 K (3 fittings) | 1.0 for every fitting |
| stair-gf | No room card | — | 2700 K (3 fittings) | 1.0 for every fitting |
| store-ramp | ies-res-storage-frequent-50 | 50 / 83 | 3000 K (3 fittings) | 1.0 for every fitting |
| study-game | ies-res-game-digital-6 | 6 / 366 | 2700 K (7 fittings) | 1.0 for every fitting |

## View QA, dimmers and camera cohorts

QA means quality assurance. These are fresh checks of the latest **retained** image for each exact view identifier using its saved scene and production context; they are not new renders of the current export. The room/task table above describes the current design. Blank task coverage means no horizontal task card was authored for that view, not zero measured light.

Cast is the midtone display RGB channel standard deviation: warm limit 0.100; cool daylight limit 0.050; cool lamp-lit limit 0.020. Highlights are the 99.5th luminance percentile, minimum 0.900; midtones are median display luminance, minimum 0.300; clipping is pixels with a clipped channel, maximum 3%. Existing exposure-lock policy makes tonal violations WARN; cast still FAILs. Other QA warnings/failures are retained verbatim. A QA pass is only a historical image result.

| View | Room / task table | Current layer dimmers | Archive/state | Gain stops / balance K | Measured image QA | Other nonpassing QA / applicability |
| --- | --- | --- | --- | --- | --- | --- |
| v01-kitchen-garden | kitchen | ambient 0.5; accent 0.5 | J3: day | -9.48413 / 5500 | cast: mid-tone cast 0.058 PASS; highlights: 99.5th-percentile luminance 1.00 PASS; midtones: median luminance 0.38 PASS; clip: 1.5% of pixels clipped PASS | window_brightness:ear-18: view median 0.57 vs room 90th percentile 0.60 FAIL; window_brightness:ear-19: view median 0.57 vs room 90th percentile 0.60 FAIL |
| v02-garden-living | living | ambient 0.5; accent 0.5 | J9: day | -10.04362 / 5500 | cast: mid-tone cast 0.067 PASS; highlights: 99.5th-percentile luminance 0.96 PASS; midtones: median luminance 0.44 PASS; clip: 0.0% of pixels clipped PASS | — |
| v03-street-lounge | lounge | ambient 0.5; accent 0.5 | J4: day | -10.41267 / 5500 | cast: mid-tone cast 0.012 PASS; highlights: 99.5th-percentile luminance 0.68 WARN; midtones: median luminance 0.10 WARN; clip: 0.0% of pixels clipped PASS | — |
| v04-study-deck | study-game | All design lamps off | J6: day | -10.19408 / 5500 | cast: mid-tone cast 0.022 PASS; highlights: 99.5th-percentile luminance 0.99 PASS; midtones: median luminance 0.42 PASS; clip: 0.2% of pixels clipped PASS | — |
| v05-parents-bedroom | parents-bed | ambient 0.3; task 0.5; accent 0.4; decorative 1 | J11: evening | -5.96568 / 3000 | cast: mid-tone cast 0.060 PASS; highlights: 99.5th-percentile luminance 0.89 WARN; midtones: median luminance 0.43 PASS; clip: 0.4% of pixels clipped PASS | — |
| v06-kids-room | kids-a | All design lamps off | J4: day | -10.41267 / 5500 | cast: mid-tone cast 0.031 PASS; highlights: 99.5th-percentile luminance 0.99 PASS; midtones: median luminance 0.35 PASS; clip: 0.4% of pixels clipped PASS | — |
| v08-cinema | cinema | ambient 1; task 1; accent 1; decorative 1 | J6: evening | -7.02888 / 3000 | cast: mid-tone cast 0.040 PASS; highlights: 99.5th-percentile luminance 0.85 WARN; midtones: median luminance 0.14 WARN; clip: 0.0% of pixels clipped PASS | — |
| v09-dining-evening | dining | ambient 0.35; task 0.5; accent 1; decorative 1 | J4: evening | -5.96017 / 3000 | cast: mid-tone cast 0.060 PASS; highlights: 99.5th-percentile luminance 1.00 PASS; midtones: median luminance 0.68 PASS; clip: 0.9% of pixels clipped PASS | — |
| v10-living-evening | living | ambient 0.25; task 0.5; accent 1; decorative 1 | J9: evening | -5.96211 / 3000 | cast: mid-tone cast 0.069 PASS; highlights: 99.5th-percentile luminance 1.00 PASS; midtones: median luminance 0.44 PASS; clip: 1.3% of pixels clipped PASS | — |
| v11-stair-void | Multi-room/exterior | ambient 1; task 1; accent 1; decorative 1 | J5: evening | -5.60317 / 3000 | cast: mid-tone cast 0.059 PASS; highlights: 99.5th-percentile luminance 0.99 PASS; midtones: median luminance 0.72 PASS; clip: 0.6% of pixels clipped PASS | — |
| v12-ensuite | parents-ensuite | ambient 0.5; task 1; accent 1; decorative 1 | J8: evening | -6.00519 / 3000 | cast: mid-tone cast 0.048 PASS; highlights: 99.5th-percentile luminance 0.97 PASS; midtones: median luminance 0.54 PASS; clip: 0.4% of pixels clipped PASS | shadows_present: 1st-percentile luminance 0.20 (max 0.1) (exposure locked across the set) WARN |
| v13-kids-b | kids-b | ambient 1; task 1; accent 1; decorative 1 | J4: evening | -5.96017 / 3000 | cast: mid-tone cast 0.059 PASS; highlights: 99.5th-percentile luminance 0.86 WARN; midtones: median luminance 0.38 PASS; clip: 0.0% of pixels clipped PASS | — |
| v15-family-bath | family-bath | ambient 1; task 1; accent 1 | J8: day | -10.33598 / 5500 | cast: mid-tone cast 0.110 FAIL; highlights: 99.5th-percentile luminance 0.99 PASS; midtones: median luminance 0.26 WARN; clip: 0.1% of pixels clipped PASS | shadows_present: 1st-percentile luminance 0.14 (max 0.1) (exposure locked across the set) WARN |
| v35-family-bath-wc | family-bath | ambient 1; task 1; accent 1 | J8: day | -10.33598 / 5500 | cast: mid-tone cast 0.079 PASS; highlights: 99.5th-percentile luminance 0.41 WARN; midtones: median luminance 0.26 WARN; clip: 0.0% of pixels clipped PASS | shadows_present: 1st-percentile luminance 0.16 (max 0.1) (exposure locked across the set) WARN |
| v16-guest-wc | guest-wc | ambient 1; task 1; accent 1; decorative 1 | J8: evening | -6.00519 / 3000 | cast: mid-tone cast 0.049 PASS; highlights: 99.5th-percentile luminance 0.89 WARN; midtones: median luminance 0.72 PASS; clip: 0.1% of pixels clipped PASS | shadows_present: 1st-percentile luminance 0.48 (max 0.1) (exposure locked across the set) WARN |
| v17-dirty-kitchen | dirty-kitchen | ambient 0.5; accent 0.5 | J11: day | -10.41895 / 5500 | cast: mid-tone cast 0.033 PASS; highlights: 99.5th-percentile luminance 0.66 WARN; midtones: median luminance 0.38 PASS; clip: 0.0% of pixels clipped PASS | — |
| v18-study-evening | study-game | ambient 0.4; task 0.6; accent 1; decorative 1 | J4: evening | -5.96017 / 3000 | cast: mid-tone cast 0.063 PASS; highlights: 99.5th-percentile luminance 0.67 WARN; midtones: median luminance 0.40 PASS; clip: 0.0% of pixels clipped PASS | — |
| v19-garden-facade | Multi-room/exterior | All design lamps off | J1: day | -12.37520 / 5500 | cast: mid-tone cast 0.021 PASS; highlights: 99.5th-percentile luminance 0.95 PASS; midtones: median luminance 0.34 PASS; clip: 0.0% of pixels clipped PASS | — |
| v20-kitchen-run | kitchen | ambient 0.4; task 0.8; accent 1; decorative 1 | J11: evening | -5.96568 / 3000 | cast: mid-tone cast 0.048 PASS; highlights: 99.5th-percentile luminance 1.00 PASS; midtones: median luminance 0.79 PASS; clip: 3.4% of pixels clipped WARN | shadows_present: 1st-percentile luminance 0.15 (max 0.1) (exposure locked across the set) WARN |
| v21-lounge-evening | lounge | ambient 0.3; task 1; accent 0.6; decorative 1 | J10: evening | -2.72743 / 3000 | cast: mid-tone cast 0.082 PASS; highlights: 99.5th-percentile luminance 1.00 PASS; midtones: median luminance 0.92 PASS; clip: 5.6% of pixels clipped WARN | shadows_present: 1st-percentile luminance 0.29 (max 0.1) (exposure locked across the set) WARN |
| v22-parents-day | parents-bed | All design lamps off | J4: day | -10.41267 / 5500 | cast: mid-tone cast 0.052 PASS; highlights: 99.5th-percentile luminance 0.98 PASS; midtones: median luminance 0.68 PASS; clip: 0.4% of pixels clipped PASS | shadows_present: 1st-percentile luminance 0.21 (max 0.1) (exposure locked across the set) WARN |
| v23-gf-gallery | Multi-room/exterior | ambient 1; accent 1 | J6: day | -7.02888 / 3000 | cast: mid-tone cast 0.037 PASS; highlights: 99.5th-percentile luminance 0.90 PASS; midtones: median luminance 0.60 PASS; clip: 0.1% of pixels clipped PASS | shadows_present: 1st-percentile luminance 0.39 (max 0.1) (exposure locked across the set) WARN |
| v24-bar-alcove | living | ambient 0.3; task 1; accent 0.8; decorative 1 | J6: evening | -7.02888 / 3000 | cast: mid-tone cast 0.059 PASS; highlights: 99.5th-percentile luminance 1.00 PASS; midtones: median luminance 0.24 WARN; clip: 0.8% of pixels clipped PASS | — |
| v25-top-garden-gate | Multi-room/exterior | All design lamps off | J9: day | -11.76006 / 5500 | cast: mid-tone cast 0.015 PASS; highlights: 99.5th-percentile luminance 0.96 PASS; midtones: median luminance 0.82 PASS; clip: 0.0% of pixels clipped PASS | shadows_present: 1st-percentile luminance 0.12 (max 0.1) (exposure locked across the set) WARN |
| v26-top-garden-east | Multi-room/exterior | All design lamps off | J9: day | -11.76006 / 5500 | cast: mid-tone cast 0.017 PASS; highlights: 99.5th-percentile luminance 0.94 PASS; midtones: median luminance 0.64 PASS; clip: 0.0% of pixels clipped PASS | — |
| v27-east-yard-above | Multi-room/exterior | All design lamps off | J1: day | -12.37520 / 5500 | cast: mid-tone cast 0.025 PASS; highlights: 99.5th-percentile luminance 0.89 WARN; midtones: median luminance 0.50 PASS; clip: 0.0% of pixels clipped PASS | — |
| v28-east-yard-below | Multi-room/exterior | All design lamps off | J9: day | -11.76006 / 5500 | cast: mid-tone cast 0.023 PASS; highlights: 99.5th-percentile luminance 0.93 PASS; midtones: median luminance 0.54 PASS; clip: 0.0% of pixels clipped PASS | — |
| v36-north-garden | Multi-room/exterior | All design lamps off | J9: day | -11.76006 / 5500 | cast: mid-tone cast 0.017 PASS; highlights: 99.5th-percentile luminance 0.97 PASS; midtones: median luminance 0.13 WARN; clip: 0.0% of pixels clipped PASS | — |
| v37-north-garden-lounge | Multi-room/exterior | All design lamps off | J9: day | -11.76006 / 5500 | cast: mid-tone cast 0.034 PASS; highlights: 99.5th-percentile luminance 0.50 WARN; midtones: median luminance 0.14 WARN; clip: 0.0% of pixels clipped PASS | — |
| v39-north-garden-hanging-retreat | Multi-room/exterior | All design lamps off | J9: day | -11.76006 / 5500 | cast: mid-tone cast 0.044 PASS; highlights: 99.5th-percentile luminance 0.28 WARN; midtones: median luminance 0.12 WARN; clip: 0.0% of pixels clipped PASS | — |
| v29-under-stair-store | Multi-room/exterior | ambient 0.5; accent 1 | J2: day | -5.93954 / 5500 | cast: mid-tone cast 0.087 PASS; highlights: 99.5th-percentile luminance 0.90 PASS; midtones: median luminance 0.45 PASS; clip: 0.0% of pixels clipped PASS | — |
| v30-under-ramp-store | store-ramp | task 1 | J2: evening | -3.80265 / 3000 | cast: mid-tone cast 0.007 PASS; highlights: 99.5th-percentile luminance 0.62 WARN; midtones: median luminance 0.22 WARN; clip: 0.0% of pixels clipped PASS | — |
| v31-dressing-hers | parents-dressing | ambient 0.6; task 1; accent 1; decorative 1 | J2: evening | -3.80265 / 3000 | cast: mid-tone cast 0.092 PASS; highlights: 99.5th-percentile luminance 0.83 WARN; midtones: median luminance 0.43 PASS; clip: 0.0% of pixels clipped PASS | — |
| v32-dressing-his | Multi-room/exterior | ambient 0.6; task 1; accent 1; decorative 1 | J2: evening | -3.80265 / 3000 | cast: mid-tone cast 0.076 PASS; highlights: 99.5th-percentile luminance 0.71 WARN; midtones: median luminance 0.30 WARN; clip: 0.0% of pixels clipped PASS | — |
| v33-basement-north-south | Multi-room/exterior | ambient 0.5; accent 0.5 | J7: day | -10.53829 / 5500 | cast: mid-tone cast 0.071 PASS; highlights: 99.5th-percentile luminance 0.94 PASS; midtones: median luminance 0.42 PASS; clip: 0.0% of pixels clipped PASS | — |
| v34-basement-south-north | Multi-room/exterior | ambient 0.5; accent 0.5 | J4: day | -10.41267 / 5500 | cast: mid-tone cast 0.074 PASS; highlights: 99.5th-percentile luminance 0.99 PASS; midtones: median luminance 0.42 PASS; clip: 0.2% of pixels clipped PASS | — |
| v40-south-garden-espalier | Multi-room/exterior | All design lamps off | J9: day | -11.76006 / 5500 | cast: mid-tone cast 0.024 PASS; highlights: 99.5th-percentile luminance 0.92 PASS; midtones: median luminance 0.62 PASS; clip: 0.0% of pixels clipped PASS | — |
| v41-south-garden-terrace | Multi-room/exterior | All design lamps off | J1: day | -12.37520 / 5500 | cast: mid-tone cast 0.020 PASS; highlights: 99.5th-percentile luminance 0.94 PASS; midtones: median luminance 0.34 PASS; clip: 0.0% of pixels clipped PASS | — |
| v07-terrace-dusk (retired diagnostic) | Multi-room/exterior | ambient 0.5; task 0.4; accent 1; decorative 1 | J9: exterior-dusk | -2.51719 / 4300 | cast: mid-tone cast 0.088 FAIL; highlights: 99.5th-percentile luminance 0.97 PASS; midtones: median luminance 0.37 PASS; clip: 4.5% of pixels clipped WARN | — |
| v38-north-garden-floor-bed (retired diagnostic) | Multi-room/exterior | All design lamps off | J9: day | -11.76006 / 5500 | cast: mid-tone cast 0.016 PASS; highlights: 99.5th-percentile luminance 0.95 PASS; midtones: median luminance 0.15 WARN; clip: 0.0% of pixels clipped PASS | crushed_shadows: 8.5% of pixels near black (limit 8%) FAIL |
| v42-north-garden-evening (retired diagnostic) | Multi-room/exterior | evening-garden 1 | J1: exterior-dusk | -1.27044 / 4300 | cast: mid-tone cast 0.105 FAIL; highlights: 99.5th-percentile luminance 0.76 WARN; midtones: median luminance 0.43 PASS; clip: 0.1% of pixels clipped PASS | —; Historical alias image only; current camera has no presentation QA |

The CCT mix is listed by room above; garden uplights are four 2700 K sources at driver/layer dimmer 1.0, with 120 source lumens each. Daylight-only views still see material colour and sky. Multi-room views inherit each visible room’s listed mix. Night-only 2200 K markers/strips are excluded from functional CCT counts; none of the listed presentation views enables their night layer.

Each archive key below is local to this report. Cohorts belong to the job **and** exposure state, so equal state names in different rows do not mean equal camera gain. The machine-readable inventory stores full named cohorts, source SHA-256 hashes (256-bit Secure Hash Algorithm content identities), lock records and the exact historical dimmers. Older jobs without a recorded named cohort cannot substantiate a current comparison lock.

| Key | Retained workstation job | Scene provenance | Meter cohort by state |
| --- | --- | --- | --- |
| J3 | 5558f89eb7b1c854783e6b7c | None | day: named cohort not recorded |
| J9 | bef71f6a8927ef2561d0b1b3 | {'source_hash': 'f4bc2ece560c62e4537961f3df0d710c0b7e793c5041a736ed3c0bab147c176c', 'git_head': '3d4fee3aae77d35e2f2d351464d074f20c0b9b02', 'git_dirty': False} | day: v01-kitchen-garden, v02-garden-living, v03-street-lounge, v04-study-deck, v06-kids-room, v15-family-bath, v35-family-bath-wc, v17-dirty-kitchen, v22-parents-day, v29-under-stair-store, v33-basement-north-south, v34-basement-south-north; evening: v05-parents-bedroom, v08-cinema, v09-dining-evening, v10-living-evening, v11-stair-void, v12-ensuite, v13-kids-b, v16-guest-wc, v18-study-evening, v20-kitchen-run, v21-lounge-evening, v23-gf-gallery, v24-bar-alcove, v30-under-ramp-store, v31-dressing-hers, v32-dressing-his; exterior-day: v19-garden-facade, v25-top-garden-gate, v26-top-garden-east, v27-east-yard-above, v28-east-yard-below, v36-north-garden, v37-north-garden-lounge, v38-north-garden-floor-bed, v39-north-garden-hanging-retreat, v40-south-garden-espalier; exterior-dusk: v07-terrace-dusk |
| J4 | 8196ee87bd77256a05df0497 | None | day: named cohort not recorded; evening: named cohort not recorded |
| J6 | 99e805532a4632399c98c3a5 | None | day: named cohort not recorded; evening: named cohort not recorded |
| J11 | e251f7c4383aa6c8f0390c3f | {'source_hash': 'ac138a4e5339e84a8c24280bede9a51543df965904ba8ed0ddff1df7c640b35f', 'git_head': '9069c245a19be278edae3615a53409388b13f4ef', 'git_dirty': False} | day: v01-kitchen-garden, v02-garden-living, v03-street-lounge, v04-study-deck, v06-kids-room, v15-family-bath, v17-dirty-kitchen, v22-parents-day, v29-under-stair-store, v33-basement-north-south, v34-basement-south-north; evening: v05-parents-bedroom, v08-cinema, v09-dining-evening, v10-living-evening, v11-stair-void, v12-ensuite, v13-kids-b, v16-guest-wc, v18-study-evening, v20-kitchen-run, v21-lounge-evening, v23-gf-gallery, v24-bar-alcove, v30-under-ramp-store, v31-dressing-hers, v32-dressing-his |
| J5 | 8535c55a0fd7a275f354049b | {'source_hash': '9f14757f7dc38e400c63c712a1ef7391663d2c7ebb009e011118b4535a58646d', 'git_head': 'f4eaaeba5c34c2f9e3a8db609efa4736a89b235b', 'git_dirty': False} | evening: v05-parents-bedroom, v08-cinema, v09-dining-evening, v10-living-evening, v11-stair-void, v12-ensuite, v13-kids-b, v16-guest-wc, v18-study-evening, v20-kitchen-run, v21-lounge-evening, v23-gf-gallery, v24-bar-alcove, v30-under-ramp-store, v31-dressing-hers, v32-dressing-his |
| J8 | b1ee556e3d7886fde1d5b502 | {'source_hash': '1e74ed4eee359d0045ac5c670fa5e3d04f8c112a7742602ef1895a3159ae5909', 'git_head': '1a4ba1afc658060bff9f86df54f2bd8e372f79d2', 'git_dirty': False} | day: v01-kitchen-garden, v02-garden-living, v03-street-lounge, v04-study-deck, v06-kids-room, v15-family-bath, v35-family-bath-wc, v17-dirty-kitchen, v22-parents-day, v29-under-stair-store, v33-basement-north-south, v34-basement-south-north; evening: v05-parents-bedroom, v08-cinema, v09-dining-evening, v10-living-evening, v11-stair-void, v12-ensuite, v13-kids-b, v16-guest-wc, v18-study-evening, v20-kitchen-run, v21-lounge-evening, v23-gf-gallery, v24-bar-alcove, v30-under-ramp-store, v31-dressing-hers, v32-dressing-his |
| J1 | 155b74a730c0d87aea2fcb8a | {'source_hash': 'ad7947a216673b7d5f5c3142c96d9de49e240e07358f564f1e77dc60c573ca27', 'git_head': '1b4f33b15078a1ca4f09a8b11bbbb639662e040d', 'git_dirty': False} | exterior-day: v19-garden-facade, v25-top-garden-gate, v26-top-garden-east, v27-east-yard-above, v28-east-yard-below, v36-north-garden, v37-north-garden-lounge, v38-north-garden-floor-bed, v39-north-garden-hanging-retreat, v40-south-garden-espalier, v41-south-garden-terrace; exterior-dusk: v07-terrace-dusk, v41-north-garden-evening |
| J10 | c9c7ce9007be475bf731bd5e | None | evening: named cohort not recorded |
| J2 | 23dd04922a022850f8206220 | {'source_hash': 'f5a8be7e0378d0d34fa40af8b4bb5a72919c910f645e9984597ef4d1d14c1012', 'git_head': '0e0efc827f4a06784babe5b0bc94bf02468ed533', 'git_dirty': True} | day: named cohort not recorded; evening: named cohort not recorded |
| J7 | b01ce934df2015971b23c4eb | None | day: named cohort not recorded |

## Findings, corrections and recommendations

The source-isolation results classify v15 as a faithful mixed-CCT/material condition, with its historical cast FAIL retained. The dusk cases are independently documented in [G2f](garden-g2f-report.md#f5--south-garden-v07-dusk-cool-cast) and [G4e](garden-g4e-report.md#evening-diagnosis): v07's latest retained cast is 0.088 cool against 0.020, and the original north-evening alias is 0.105 against 0.020. G4e's source probes found sky blue/red 1.379 versus lamp 0.0996; about 98% of gravel/wall luminance remains with sky alone. Preserve their disclosed faithful dusk conditions and retained failures. v07, v38 and v42 are already retired from presentation; their diagnostic rows do not promote them.

Tonal warnings describe each retained camera cohort, surface population and lighting state; a design cause still needs to be demonstrated. v03's median 0.10, v08's 0.14 and v24's 0.24 merit review, but these are older rendered scenes with different locks and geometry. They do not establish a current minimum-task shortfall. v17's highlights at 0.66 and the dressing/store highlight warnings likewise do not justify adding lamps. v20 and v21 clipping at 3.4% and 5.6% merit fixture/surface isolation under their saved scenes before changing light strengths. Window-brightness failures in v01 and v38's retired crushed-shadow failure are retained in the table, outside a demonstrated small fitting correction.

The current analytical targets all pass; the upper-ratio screen raises 16 flags. The furnished-scene raw readings cannot be used for dimming at the 17 obstructed sensors. The surface-bound diagnostic figures are the appropriate quantitative basis for the lead's next design review; they are not a production acceptance pass. Full-output functional tests also differ from the deliberately dimmed presentation scenes shown in the view table. A point above a minimum recommendation does not by itself establish excessive glare, room-average excess, or an erroneous fitting. Uniformity and glare acceptance are outside these probes.

Recommendations, in order:

1. Repair task-surface/probe ownership before using automated furnished-scene lighting acceptance. This is a small measurement repair for a separate lead package; preserve the actual geometry, targets and original failed run.
2. Review the upper-ratio assumption with a held source and the room's intended scenes. Use source-separated task-plane measurements to identify which driver can be reduced while every task in the connected open space still meets its card. Retain the existing ensuite 0.4 and library-top 0.4 driver settings as recorded intent. Do not reduce a whole open-plan layer from a single bright point.
3. For family/guest vanity, bedrooms, children's/cinema desks, island seating and the dining centre, consider independent functional scene controls if the lead/client considers the measured full-output levels excessive. Children's/desk/furniture work belongs to Codex-B; no changes in that scope are made here. Manufacturer replacements, additional/removed fittings, different aims or room character require the lead/client decision.
4. Keep v15's faithful warmth and the dusk cast disclosures pending that decision. A revised palette, sky or lighting scheme needs fresh source isolation, task proof and neutral preview review, then the lead's presentation render and critic review.

Applied lighting fixes: **none**. Before/after design light records, drivers, CCTs, geometry, camera presets and QA limits are therefore identical; no changed visible result requires a neutral preview. Diagnostic EXRs and virtual sensor placement are labelled separately and never promoted to presentation. There is no new presentation QA pass, native-model gate or closed lighting-design defect.

## Acceptance and reproducibility

| Check | Result | Evidence |
| --- | --- | --- |
| `test_villa_lighting`, `test_d1_wp1`, `test_fixture_record`, `test_fixture_record_phase2`, `test_render_standard` through `scripts/run_tests.py` | **Exit 0; all 127 tests pass**, 1100.100 seconds | `out/lighting-rebalance/focused-tests.log`, `focused-tests-result.json` |
| Final `scripts/verify.py --portable`, normal HOME | **Exit 0; 172 PASS** | `out/lighting-rebalance/verify-portable-final.log` |
| Final `scripts/verify.py --portable`, initially empty temporary HOME | **Exit 0; 172 PASS** | `out/lighting-rebalance/verify-empty-home-final.log`, `verify-empty-home-final-result.json` |
| Fresh exported scene validation | Zero findings; baseline clean source provenance recorded | `out/lighting-rebalance/scene.json`, `build-current.log` |
| Unmodified production task probes | Execution completes, but `all_targets_met=false`; 17 hidden sensors make those readings invalid | `out/lighting-rebalance/current-measurements/lighting-measurements.json`, `sensor-audit.json` |
| Measured-surface diagnostic probes | All 25 minimum targets met; zero hidden central sensors; production ownership defect remains OPEN | `out/lighting-rebalance/surface-bound-measurements/lighting-measurements.json`, `sensor-audit-corrected.json` |
| Current v15 source isolation | Eight linear modes complete; 0.4116% reconstruction error | `out/lighting-rebalance/v15-current-source-probes/contributions.json`, `v15-current-probes.log` |
| Report/evidence consistency | 25 matching card targets, intact content hashes and file links; `git diff --check` exits 0 | `out/lighting-rebalance/evidence-manifest.json` |

The final portable checks ran after the report and learning-index changes. Earlier successful check logs remain separately retained. Passing code checks does not resolve the production sensor defect or the retained image failures. `docs/LEARNINGS.md` records both current source attribution and the open measured-host defect; its proposed control is deliberately not registered as implemented.

All execution uses `/home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python`, `PYTHONPATH=src`, `NO_COLOR=1`, and `OPENBLAS_NUM_THREADS=1`; Blender is `/home/omar/opt/blender/blender` (4.5.14), bounded to eight CPU threads and the existing read-only-opened graphics lock. No installation, presentation render, full test suite, commit or protected shared-symlink modification was performed. In that diagnosis package, no `.agents` or adapters were edited, so adapter synchronization was not required. The later ownership repair below updates and synchronizes the lighting-proof skill. The lead owns full-suite execution and commit.

The task-owned scripts and evidence live in `out/lighting-rebalance`: `inventory.py` reproduces production-context QA on retained images; `compare_v15.py` compares inputs; `audit_sensors.py` and its `--surface-probes` rerun establish sensor ownership; `task_paths.py` independently traces source-facing segments; `measure_current.py` runs the existing production measurement, and `--surface-probes` records diagnostic placement changes; `probe_v15_current.py` isolates current colour transport; `tables.py` creates the deterministic tables. The complete named cohorts, individual fixture drivers/CCTs, task positions and photometry identities remain in their JSON records. These diagnostics are not a new deployed workflow.

## Production probe ownership fix — 2026-10-09

The repair follows the diagnosed datum through construction. Every task definition declares its owning furniture item. Before mounting, `archpipe.task_probe.author_bindings` records a mesh identity, an upward face index and the task's explicit clearance. After all mounting/assembly migrations, `bind_planes` derives the exported plane from that actual final face. Contact tasks use the measured top with zero clearance; a sink/vanity aperture uses its declared host's rim datum. Reading/grooming points retain their authored task clearance above their host rather than becoming seat/basin-bottom measurements. The existing diffuse sensor remains 1 mm above the resulting plane, and the virtual probe camera retains its existing 25 mm plane offset. No luminaire, target, design mesh, material, presentation camera or QA limit is adjusted.

The earliest guard runs at final scene construction and exported-scene validation, then at measurement entry. It refuses missing/stale/invalid ownership and traces all 256 metered pixel centres plus the local approach from each analytic light and luminous mesh. A hit names the room/task, the solid, its hit position and whether it blocks the upward view or source approach. Every visible solid is included, including glass; material cannot exempt a local obstruction. The source check covers the final 24 mm of approach, equal to the existing camera-to-sensor gap; remote furniture shadows remain part of the physical lighting calculation. The Blender measurement additionally traces its evaluated geometry before creating a sensor or rendering a probe, covering imported objects, cloth, bevels and subdivisions. Renderer reuse includes the new guard code.

The frozen reproduction is [task-probe-hidden-sensors.json.gz](../tests/fixtures/task-probe-hidden-sensors.json.gz): all 17 original failing points and their actual host faces by value from `sensor-audit.json` and the retained scene. [test_task_probe.py](../tests/test_task_probe.py) proves rejection of all 17, silence on corrected placement, construction of their corrected planes after mounting, a renamed/translated sibling, arbitrary host translation, missing/stale/invalid bindings, a foreign solid, a noncentral metered pixel and a grazing source approach. The shared evaluated-ray-provider interface exercises the same actual failing and clean data. `tests/blender_task_probe.py` also runs those 17 failing and 17 clean cases through Blender’s actual evaluated ray provider. The production vase face is separately frozen in `tests/fixtures/task-probe-evaluated-obstructions.json.gz`; Python and Blender tests reject it, accept its clear control, and the Python test rejects a renamed sibling. The frozen readings are retained unchanged; a low-lux screen is never substituted for ownership. First-fix checkpoint: [probe-placement-preview.png](../out/task-probe-fix/probe-placement-preview.png) was inspected against the frozen induction coordinates: the old sensor is 1 mm below the measured hob, the corrected sensor is 1 mm above; the camera-to-sensor gap stays 24 mm.

Lessons to register: `lighting-rebalance-sensor-host` is covered and registered in `knowledge/build-input-guards.json`, with the construction, fail-closed stages and proving tests. `docs/LEARNINGS.md`, the canonical lighting-proof workflow and its generated Claude adapter are updated together. The nominal-height construction defect is repaired and its guard proofs pass. The full production measurement gate remains failed on the separately retained vase obstruction; lighting-design and presentation findings keep their existing status.



### Production results

Fresh exported source hash: `1c8581a1571d95c79e68c9260e6ecfba3fe1021ad9f9f97a12fca725630f115f`, uncommitted work on `afe73479a3c6ffa3180cd69ed77a815275b6b193`. The full production consumer is rerun from [measure_production.py](../out/task-probe-fix/measure_production.py) with the pinned Blender binary. It refuses the dining-table centre before any sensor render. The complete evaluated audit finds **24 clear probes and one refused probe**: `prop-dining-vase-000`, face 9889, at `[16.9453125, -25.904687881469727, -2.237814426422119]` m, on an upward-view path. Its sensor elevation is −2.247 m, so the vase face is about 9.2 mm above the sensor. This is the same instrumentation-occlusion class on imported geometry, and the new guard catches it at the earliest stage that has that geometry. The earlier diagnostic claim that 25 returned readings met their minima did not establish that this foreign-solid pixel was a sensor reading; the new production result leaves it unavailable.

[Audit and measurement script](../out/task-probe-fix/audit_and_measure.py) audits the original 25-point export and runs the unchanged production consumer on its 24 accepted points, which the mandatory guards check again. It keeps every original mesh, model, prop, cloth, curtain, light and point coordinate. This is explicitly a **partial production measurement**, not a passed 25-point gate. It reports all original 25 points in [all-point-results.json](../out/task-probe-fix/all-point-results.json), retaining the refused point without inventing an illuminance value. The original full consumer and this audit command both exit nonzero for the refusal. No guard bypass, placement patch or decoration removal is used.

Measurements retain the existing maintenance factor 0.8, all functional layers at their authored output, black sky, 256 samples, 32 × 32 pixel probes, 16-bounce total and zero-bounce direct measurements, no denoising, actual furnished scene and existing optical assumptions. Twenty-four measured points meet their minima; none is a genuine measured shortfall. The remaining 100 lx dining-centre target has no valid achieved value. The existing assumed upper-ratio screen remains advisory and unchanged.

| Point | Room / task | Direct lx | Total lx | Target lx | Result |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | kitchen / island prep side | 1077.2 | 1362.7 | 500 | PASS |
| 2 | kitchen / island seating side | 838.0 | 1096.0 | 200 | PASS |
| 3 | kitchen / island prep side | 1033.6 | 1228.6 | 500 | PASS |
| 4 | kitchen / island seating side | 850.9 | 1114.0 | 200 | PASS |
| 5 | kitchen / island prep side | 835.4 | 1112.8 | 500 | PASS |
| 6 | kitchen / island seating side | 676.6 | 926.3 | 200 | PASS |
| 7 | kitchen / single induction zone | 1004.7 | 1301.4 | 300 | PASS |
| 8 | kitchen / sink | 1154.1 | 1348.3 | 300 | PASS |
| 9 | dining / dining table centre | unavailable | unavailable | 100 | REFUSED: vase |
| 10 | dining / table end (homework) | 462.1 | 580.8 | 200 | PASS |
| 11 | dirty-kitchen / dirty kitchen run | 679.0 | 812.5 | 500 | PASS |
| 12 | study-game / study-desk | 931.6 | 1014.2 | 400 | PASS |
| 13 | study-game / study-adult-desk | 905.8 | 972.3 | 400 | PASS |
| 14 | kids-a / ka-desk-1 | 1391.5 | 1513.5 | 400 | PASS |
| 15 | kids-a / ka-desk-2 | 1390.4 | 1500.0 | 400 | PASS |
| 16 | kids-b / kb-desk | 1389.4 | 1485.9 | 400 | PASS |
| 17 | parents-bed / pillow | 1114.0 | 1194.5 | 200 | PASS |
| 18 | parents-bed / pillow | 1116.5 | 1189.2 | 200 | PASS |
| 19 | family-bath / fb-basin | 1337.5 | 1616.4 | 300 | PASS |
| 20 | parents-ensuite / pe-basin | 631.2 | 757.8 | 300 | PASS |
| 21 | guest-wc / gwc-basin | 1375.2 | 1599.5 | 300 | PASS |
| 22 | lounge / armchair | 789.7 | 951.2 | 200 | PASS |
| 23 | bar-alcove / daybed nook | 324.6 | 421.8 | 200 | PASS |
| 24 | cinema / cinema desk | 1483.9 | 1521.8 | 400 | PASS |
| 25 | cinema / cinema desk | 1492.4 | 1526.1 | 400 | PASS |

Point numbers follow original export order; repeated labels identify distinct coordinates in the linked JSON. Raw linear probes are retained under [accepted-measurements](../out/task-probe-fix/accepted-measurements). The full obstruction audit is [evaluated-probe-audit.json](../out/task-probe-fix/evaluated-probe-audit.json), and the refusing consumer log is [production-measurement-final.log](../out/task-probe-fix/production-measurement-final.log). [unchanged-design-final.json](../out/task-probe-fix/unchanged-design-final.json) compares the full scene fields by value against the retained diagnosis export; it separately checks all point identities, targets and horizontal coordinates.


### Fix acceptance

| Check | Result | Evidence |
| --- | --- | --- |
| Focused lighting, render standard, scene contract, task guard and adapter selection | 124 tests, exit 0 | [focused-tests-final.log](../out/task-probe-fix/focused-tests-final.log) |
| Final task guard and adapter selection, including the glass and real vase cases | 16 tests, exit 0 | [guard-and-agent-tests-final.log](../out/task-probe-fix/guard-and-agent-tests-final.log) |
| Actual Blender evaluated-ray guard cases | 2 tests, exit 0; the 17 failing and 17 clean hosts plus vase/glass controls | [blender-guard-tests-final.log](../out/task-probe-fix/blender-guard-tests-final.log) |
| `scripts/verify.py --portable`, normal `HOME` | Exit 0 | [verify-portable-final.log](../out/task-probe-fix/verify-portable-final.log) |
| `scripts/verify.py --portable`, initially empty `HOME` | Exit 0 | [verify-empty-home-final.log](../out/task-probe-fix/verify-empty-home-final.log) |
| Full production measurement | Expected exit 1: named vase obstruction; no sensor rendered | [production-measurement-final.log](../out/task-probe-fix/production-measurement-final.log) |
| Guarded clear-subset production measurement | 24 measured minima met; expected exit 1 for the retained refused point | [audit-and-measure.log](../out/task-probe-fix/audit-and-measure.log) |
| Canonical agent adapters / diff whitespace | `sync_agent_assets.py --check` and `git diff --check`, exit 0 | 38 adapters checked |

[acceptance-status.json](../out/task-probe-fix/acceptance-status.json) retains exit statuses and log hashes, distinguishing code acceptance from the failed full measurement gate. [refresh_evidence.py](../out/task-probe-fix/refresh_evidence.py) verifies the matching export source and unchanged persisted scene values, then refreshes both production executions. [verify_both.py](../out/task-probe-fix/verify_both.py) runs the two portable contexts sequentially. The initial mistaken `tests.test_lighting` name was refused before test execution; the corrected existing module selection above passed. The final material-exemption correction was separately tested by the final guard and Blender selections and both portable contexts.

The pinned Python interpreter, `PYTHONPATH=src`, `NO_COLOR=1`, single-threaded OpenBLAS and Blender 4.5.14 were retained. Production rendering used eight CPU threads and the existing graphics lock. The lighting-proof skill was updated and `scripts/sync_agent_assets.py` run; adapters match. No package installation, full-suite run, protected shared-data modification or commit was performed. The lead retains full-suite and commit ownership. These results repair instrumentation ownership; they approve no real villa design gate.

## Covered dining task point — lead decision applied 2026-10-11

This continuation supersedes the 2026-10-09 full-measurement refusal above; the historical runs remain unchanged. **All 25 points are freshly measured; 25/25 meet their existing targets.** No scene geometry, furniture, vase/dressing, light, material, presentation camera, target or nominal task coordinate changed. [Measurement inputs and unchanged-scene comparisons](../out/dining-probe/measurement-inputs.json) compare every persisted design field and all 25 nominal points against the retained production export. Fresh source hash: `ea6899755501d8a12dc60801f336206d59544bb67ae98e72f203f9384c45708e`, uncommitted on `b5258666d39edb84795d912a5875ea06c89f6e09`.

The export names the blocked point **dining table centre**, card `ies-res-dining-informal-100`, target 100 lx. The separate **table end (homework)** uses `ies-res-dining-study-200`, target 200 lx, and remains at its original measurement position. Both [verified dining cards](../knowledge/library.json) cite IES Lighting Handbook, 10th edition (2011), Table 33.2, printed p. 33.8: horizontal maintained illuminance at the table plane, averaged over the area of coverage. The search area is conservatively bounded to the complete finite measured owning tabletop face (`furn-dining-table-0`, face 26), with every corner of the metered footprint inside it. These individual authored-point checks do not establish an area-average, glare or uniformity verdict.

`author_bindings` records that cited area. Before any sensor render, `resolve_surface_probes` checks the evaluated scene and confirms the obstructing object rests on the host: the measured vase bottom is −2.2479999065 m against tabletop −2.248 m. Only the instrument measurement position is selected nearby; `position` keeps the nominal target. A nominal-anchored square lattice searches outward at 5 mm spacing, ordered by squared distance and then signed horizontal x and y indices. The x and y axes are the first and second horizontal model axes; elevation is the third coordinate. The spacing is instrument sampling resolution, not a design rule. The selected point is the **nearest clear tested lattice point**; no lux value selects it. Every metered camera path and every local source approach must be clear. Missing/stale citation, a non-resting object or no clear candidate within that same finite task area remains failed, with no invented lux reading.

The actual production centre is measured at `[16.92, -25.805, -2.248]` m instead of nominal `[16.95, -25.9, -2.248]` m: offset **[-30.0, +95.0, +0.0] mm**, distance **99.624 mm**, after 567 recorded candidate tests including the nominal point. Its [measurement record](../out/dining-probe/measurements/lighting-measurements.json) carries nominal/effective coordinates, offset, pattern, cited area, original vase hit, complete measured resting-object bounds and every candidate's obstruction result. The other 24 points have no offset. Both raw and evaluated guards run again on selected positions. The complete vase and furnished scene remain in the light transport, including their shadows.

[Actual evaluated fixture](../tests/fixtures/task-probe-table-vase.json.gz) retains the table, local vase faces and complete measured vase bounds by value; provenance records Poly Haven `ceramic_vase_01`, James Ray Cock, CC0 as recorded in the existing intake manifest, metres converted to the scene's upward elevation axis. [First-fix instrumentation preview](../out/dining-probe/first-fix-preview.png) was inspected against that geometry before production measurement. Python regressions prove the real blocked case, an unchanged clean homework point, renamed/translated table and vase, fully covered task area despite adjacent furniture, overhead obstruction, missing/mutated citation and forged offset. The pinned Blender evaluated-ray tests also prove the real case, clean control and translated sibling with all 228 production analytic lights and emissive mesh centres frozen as segment sources. The initial analytic-only fixture selected [−25, +95, 0] mm; production rejected that candidate because the approach from emissive `marker-PATH-corridor-09` hits the vase. Both Python and Blender regressions now assert that rejection and the complete-source production selection. No production code or geometry changed for this fixture correction. The [complete-source instrumentation preview](../out/dining-probe/complete-source-preview.png) was also inspected against the final selected footprint. This is instrumentation acceptance, with the existing presentation/design findings retained.

The unchanged production consumer in [measure.py](../out/dining-probe/measure.py) runs all 25 points, with maintenance factor 0.8, all authored functional layers, black sky, 256 samples, 32 × 32 pixel probes, zero-bounce direct and 16-bounce total measurements, no denoising and the existing optical assumptions. Raw linear probes are in [measurements](../out/dining-probe/measurements). The existing assumed upper-ratio screen stays advisory and unchanged.

| Point | Room / task | Direct lx | Total lx | Target lx | Instrument offset mm (x, y, elevation) | Result |
| --- | --- | ---: | ---: | ---: | --- | --- |
| 1 | kitchen / island prep side | 1077.2 | 1364.2 | 500 | 0, 0, 0 | PASS |
| 2 | kitchen / island seating side | 838.0 | 1097.0 | 200 | 0, 0, 0 | PASS |
| 3 | kitchen / island prep side | 1033.6 | 1226.6 | 500 | 0, 0, 0 | PASS |
| 4 | kitchen / island seating side | 850.9 | 1113.8 | 200 | 0, 0, 0 | PASS |
| 5 | kitchen / island prep side | 835.4 | 1116.3 | 500 | 0, 0, 0 | PASS |
| 6 | kitchen / island seating side | 676.6 | 925.8 | 200 | 0, 0, 0 | PASS |
| 7 | kitchen / single induction zone | 1004.7 | 1302.7 | 300 | 0, 0, 0 | PASS |
| 8 | kitchen / sink | 1154.1 | 1348.7 | 300 | 0, 0, 0 | PASS |
| 9 | dining / dining table centre | 546.2 | 649.8 | 100 | -30.0, +95.0, +0.0 | PASS |
| 10 | dining / table end (homework) | 462.1 | 584.9 | 200 | 0, 0, 0 | PASS |
| 11 | dirty-kitchen / dirty kitchen run | 679.0 | 812.3 | 500 | 0, 0, 0 | PASS |
| 12 | study-game / study-desk | 931.6 | 1013.8 | 400 | 0, 0, 0 | PASS |
| 13 | study-game / study-adult-desk | 905.8 | 974.3 | 400 | 0, 0, 0 | PASS |
| 14 | kids-a / ka-desk-1 | 1391.5 | 1499.7 | 400 | 0, 0, 0 | PASS |
| 15 | kids-a / ka-desk-2 | 1390.4 | 1529.5 | 400 | 0, 0, 0 | PASS |
| 16 | kids-b / kb-desk | 1389.4 | 1509.1 | 400 | 0, 0, 0 | PASS |
| 17 | parents-bed / pillow | 1114.0 | 1194.5 | 200 | 0, 0, 0 | PASS |
| 18 | parents-bed / pillow | 1116.5 | 1187.4 | 200 | 0, 0, 0 | PASS |
| 19 | family-bath / fb-basin | 1337.5 | 1616.4 | 300 | 0, 0, 0 | PASS |
| 20 | parents-ensuite / pe-basin | 631.2 | 757.8 | 300 | 0, 0, 0 | PASS |
| 21 | guest-wc / gwc-basin | 1375.2 | 1599.5 | 300 | 0, 0, 0 | PASS |
| 22 | lounge / armchair | 789.7 | 952.0 | 200 | 0, 0, 0 | PASS |
| 23 | bar-alcove / daybed nook | 324.6 | 421.5 | 200 | 0, 0, 0 | PASS |
| 24 | cinema / cinema desk | 1483.9 | 1521.8 | 400 | 0, 0, 0 | PASS |
| 25 | cinema / cinema desk | 1492.4 | 1526.1 | 400 | 0, 0, 0 | PASS |

| Acceptance | Result | Evidence |
| --- | --- | --- |
| Focused lighting, probe, render standard, scene contract and adapters | 133 tests, exit 0 | [focused-tests.log](../out/dining-probe/focused-tests.log) |
| Final probe regressions with all production sources | 20 tests, exit 0 | [probe-tests-final.log](../out/dining-probe/probe-tests-final.log) |
| Pinned Blender evaluated-ray probes with all production sources | 3 tests, exit 0 | [blender-tests-complete-sources.log](../out/dining-probe/blender-tests-complete-sources.log) |
| `scripts/verify.py --portable`, normal HOME | Exit 0 | [verify-portable-final.log](../out/dining-probe/verify-portable-final.log) |
| `scripts/verify.py --portable`, initially empty HOME | Exit 0 | [verify-empty-home-final.log](../out/dining-probe/verify-empty-home-final.log) |
| Full production measurement | 25 measured, 25 targets met; exit 0 | [measurement.log](../out/dining-probe/measurement.log) |
| Adapters and whitespace | 38 adapters checked; `git diff --check`, exit 0 | [acceptance-status.json](../out/dining-probe/acceptance-status.json) |

[Acceptance receipts](../out/dining-probe/acceptance-status.json) record exit statuses and log hashes. The first added ordering assertion compared floating metre ties exactly; it was corrected to compare the recorded integer lattice indices, without changing search resolution or tolerance. An export begun before the final source edit correctly refused source drift; the settled-code export was rebuilt. Those earlier logs remain retained separately. `docs/LEARNINGS.md`, the build-input guard registry and canonical/generated lighting-proof workflows are updated together; `scripts/sync_agent_assets.py` was run. No installation, shared-symlink modification, full-suite run or commit was performed. Full-suite and commit ownership remain with the lead; no real villa design gate or presentation acceptance is approved.
