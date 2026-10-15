# Blender 5.2 side-by-side evaluation

**Recommendation: stay on Blender 4.5.14 for production. Keep 5.2.2 alongside it for the official Model Context Protocol (MCP) tools.** The 5.2 batch retains all 25 lighting targets and the same 35/38 image-quality passes, but it changes photometric light transfer, evaluated bevel geometry, colour/shader defaults and visible local appearance. The speed ladder below does not establish an acceptable setting for every representative view. These are evaluation drafts and numerical probes; no presentation release or real villa design gate is approved.

Worktree `codex/blender52`, integration head `6be1230`; completed 2026-10-15. No commit. No default renderer, 4.5.14 pin, production cache, existing result, shared asset or agent connection configuration was changed. The canonical render workflow and generated Claude adapter were synchronized.

All full-precision measurements are in [comparison.json](../out/blender52/comparison.json). Each view has a before/after/difference panel and individual difference image in [the comparison folder](../out/blender52/comparison/); [contact sheet](../out/blender52/comparison/contact-sheet.jpg). The independent [visual review](../out/blender52/visual-review-final.md) covers all 38 pairs on contact sheets and four original-resolution pairs; the [fresh-reference addendum](../out/blender52/visual-review-addendum.md) confirms the local finding and inspects the neutral preview.

## Runtime and explicit selection

| Property | 4.5.14 | 5.2.2 |
|---|---|---|
| Build | 62c1db4208e8 | d13f752e3b9c |
| Bundled Python | 3.11.15 (main, Apr 25 2025, 12:39:20) [GCC 11.2.1 20220127 (Red Hat 11.2.1-9)] | 3.13.13 (main, Apr 25 2025, 12:39:20) [GCC 14.2.1 20250110 (Red Hat 14.2.1-11)] |
| Bundled NumPy | 1.26.4 | 2.3.4 |
| Executable SHA-256 | 050c02562f81fe80ba616a80198fa02d381e60f8b61b8d39add881f4bca0d7d8 | bafec183e960819c76fe213c000cdb2284c53a87ef6791812f8728b51f07145b |

SHA-256 means the recorded 256-bit content digest. The RTX 3090 graphics processing unit (GPU) has 24 GiB (gibibytes) of video memory; the host driver is 595.99.02, reporting CUDA 13.2. GPU timings use the enabled OptiX device. Processes use eight central processing unit (CPU) threads, low CPU priority and the existing shared graphics lock. No `render-*` lead tmux session was active at launch; other shared jobs retain the same lock. Queue/build/probe time is separate from per-image render time. [GPU receipt](../out/blender52/gpu-host.txt).

`scripts/villa_render.py` accepts `--blender /absolute/workstation/path --expected-version 5.2.2`. Omitting them retains the existing symlink and exact 4.5.14 preflight. Explicit executable/version become part of job identity, so evaluation results cannot reuse production cache identity. `scripts/prove_reproducibility.py` also accepts `--expected-version`, defaulting to 4.5.14. `scripts/blender52_eval.py` records exact runtime, scene, source and optical-input receipts and uses an isolated user configuration.

```bash
PYTHONPATH=src /home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python scripts/blender52_eval.py \
  --blender /home/omar/opt/blender-5.2.2-linux-x64/blender --expected-version 5.2.2 \
  --out out/blender52/new-evaluation --batch
```

Version-dependent surfaces: executable/build and bundled Python/NumPy; Cycles sampling, denoisers and light transport; evaluated bevel/subdivision geometry; shader socket defaults; OpenColorIO configuration and white-balance calculation; glTF importer and source measurements; cloth runtime/cache identity and therefore pattern seed; add-on compatibility and user preferences. [Runtime inventory](../out/blender52/version-inventory.txt), [saved-state comparison](../out/blender52/state-comparison.json), [preservation record](../out/blender52/preservation.json).

## Python application programming interface (API) and compatibility fixes

Only one executed API break was found: assigning `ShaderNodeTexSky.sky_type = "NISHITA"` fails in 5.2. The original sites were `src/archpipe/blender/photoreal.py:133` and `src/archpipe/blender/calibrate_sky.py:90`. `blender.sky_compat.configure_legacy_sky` now selects supported `NISHITA` or `SINGLE_SCATTERING`, retaining zero altitude and unit air/aerosol/ozone density. The old `dust_density` property becomes `aerosol_density`. A new 5.2 node defaults to `MULTIPLE_SCATTERING` at 100 metres altitude; accepting it would change the source. Unknown APIs refuse rather than falling back. No numerical calibration multiplier was changed.

Both actual-runtime daylight API tests pass in two directions. The standalone calibration entry point also runs successfully in each runtime: its 35-degree/zero-rotation CPU probe reports 76.692252468 versus 76.719520412 lux (0.03555% change). Adding the shared adapter initially exposed a standalone import regression because Blender ignores PYTHONPATH by default; `calibrate_sky.py:34` now resolves its own checkout before importing it. An isolated relocated-checkout regression accepts the fixed imports and rejects removal of that bootstrap. This final bootstrap change occurred after the complete render batches; it does not change their exercised scene builder, adapter or optical values. The original failed command and both successful replays are retained in `calibrate-sky*.log`. Under 5.2, the full villa builder/importer, all task measurements, three evaluated-ray tests, one importer precision test, all ten cloth templates in independent processes, standalone bedroom build/glTF export and the neutral preview tool were executed. The bedroom fixture build reports four walls, one floor, two cut openings, six furniture items and five lights. It is a frozen fixture replay, not a fresh native Revit acceptance. Logs are `sky-compat*.log`, `task-probe-api-resume.log`, `importer-api-resume.log`, `bedroom-api.log`, `preview52.log` and `cloth/`.

Additional changed RNA (Blender’s runtime API metadata), without a failing call in the exercised paths: Cycles removes `feature_set`; view settings replace `use_hdr_view` with `is_hdr`; 5.2 adds display emulation, texture-cache controls and a `use_pixel_jitter` field observed false. The default compositor device changes CPU to GPU. [The full property diff](../out/blender52/state-comparison.json) retains added/removed fields. Unexercised graphical-interface tools are not certified.

## Matched scene, settings and colour controls

The isolated `scene.json` equals the lead laneR scene by value; canonical authored hash `122c6c86bdf1bf1175d5799deae247454389528287a1fa401de80ab608e641c0`. Its raw file SHA-256 is `319c413e7b7e0dbf7a665ce4789fd95c531a3e2c6f9f699199c3724791054f78`. There are 41 authored views, of which 38 are active. All 38 were rendered afresh in each version at 256 maximum samples, 960×640, OpenImageDenoise, seed zero, identical cameras and lead per-view exposure. Adaptive sampling remains enabled. Image comparison checks samples, resolution, exposure, white balance, bounces, clamping and authored scene identity. Every row matches.

Factory view transform/look/display are identical: AgX / None / sRGB, gamma 1 and exposure zero. The production camera recipe explicitly selects AgX / AgX – Medium High Contrast / sRGB and the reference exposure. Nevertheless the bundled OpenColorIO configurations have different hashes: `aa4142b29b5a472aa5cb895020aa8cb673c95a31660eeee451f8a820694d3b16` versus `f10891fc7d34e78e71b535e3f92b3c612177320f990641283247cb84bb8d62ad`. The recorded 5500 K whitepoint changes from [1.1041641235351562, 0.9868673086166382, 0.823180079460144] to [1.104345679283142, 0.9868429899215698, 0.8229822516441345]. These are derived controls, not a changed authored temperature.

Explicitly resetting the matching display/view/look/gamma/exposure in the 5.2 saved-scene control gives mean channel error 0.000000 and 95th-percentile error 0.000000. It does not remove the cross-version differences: the native-config explicit control versus the fresh 4.5 reference has mean error 0.002253. Using the old OpenColorIO configuration in 5.2 restores the old derived whitepoint but changes cross-version mean error only from 0.002253 to 0.002251. The separate experiment is in [receipt](../out/blender52/ocio-control/comparison.json); matching control names is not proof that their transforms are identical.

Principled’s default Subsurface Scale changes from 0.05 to 0.005 in all 320 measured materials; 5.2 adds Thin Wall=false. An unused factory Material has index of refraction 1.45 versus 1.5. These are recorded default differences, not proof that every one affects rendered light. [Shader socket diff](../out/blender52/state-comparison.json).

Exactly 100 of 1,956 evaluated mesh records differ; all 50 curtain panels and all draped garment mesh records agree. All 100 changed objects have bevel modifiers. Common recorded modifier settings, vertex counts and polygon connectivity agree. Maximum corresponding evaluated world-vertex displacement is 69.906 mm; maximum outer-bound difference is 0.001013 mm. The largest changed record is `landscape-north-mid-00`; 83 of the 100 are render-visible in v01. A separate vertex-order-independent nearest-vertex control has maximum distance 17.293444 mm and nonzero changes in all 100 records; this rules out pure index reordering, while not measuring full point-to-triangle surface distance. [Order control](../out/blender52/mesh-order-control.json). Thus this is the effect of migrating the complete scene runtime, not a renderer-only test with identical evaluated meshes. [Every changed object and its values](../out/blender52/evaluated-geometry-details.json); [modifier parameter comparison](../out/blender52/modifier-differences.json).

## All 38 views

QA means the existing `render_qa` quality checks. Both versions pass 35/38, with the same failures: v15 colour cast, v36 crushed shadows and v29 crushed shadows. Existing camera/geometry/light/exposure and thresholds were preserved. In the fresh matched replay, summed frame-render time is 367.805 seconds versus 345.858 seconds (-5.97% change). These one-pass draft totals include per-view scene update costs and are not an isolated throughput guarantee. The supplied lead draft sum was 357.761 seconds.

Mean absolute error averages absolute encoded standard red/green/blue (sRGB) channel differences on a zero-to-one scale; P95 is their 95th percentile. “Seconds” is the complete per-view render call. Full-precision values and individual QA checks remain in the JSON receipts.

| View | QA 4.5 / 5.2 | Mean error | P95 error | Seconds 4.5 / 5.2 |
|---|---|---:|---:|---:|
| v01-kitchen-garden | PASS / PASS | 0.002250 | 0.007843 | 16.438 / 17.580 |
| v02-garden-living | PASS / PASS | 0.001905 | 0.007843 | 9.481 / 8.639 |
| v03-street-lounge | PASS / PASS | 0.002801 | 0.007843 | 10.343 / 9.778 |
| v04-study-deck | PASS / PASS | 0.000911 | 0.003922 | 7.378 / 7.191 |
| v05-parents-bedroom | PASS / PASS | 0.009557 | 0.019608 | 10.755 / 10.647 |
| v06-kids-room | PASS / PASS | 0.000864 | 0.003922 | 8.386 / 8.106 |
| v08-cinema | PASS / PASS | 0.013455 | 0.023529 | 9.363 / 8.929 |
| v09-dining-evening | PASS / PASS | 0.010090 | 0.019608 | 11.736 / 10.913 |
| v10-living-evening | PASS / PASS | 0.007904 | 0.019608 | 11.072 / 10.254 |
| v11-stair-void | PASS / PASS | 0.011000 | 0.023529 | 12.391 / 11.527 |
| v12-ensuite | PASS / PASS | 0.017005 | 0.027451 | 13.062 / 12.211 |
| v13-kids-b | PASS / PASS | 0.016526 | 0.023529 | 11.397 / 10.718 |
| v15-family-bath | FAIL colour_cast / FAIL colour_cast | 0.006719 | 0.019608 | 12.915 / 11.832 |
| v35-family-bath-wc | PASS / PASS | 0.004246 | 0.011765 | 12.141 / 11.420 |
| v16-guest-wc | PASS / PASS | 0.014602 | 0.023529 | 12.771 / 12.381 |
| v17-dirty-kitchen | PASS / PASS | 0.001866 | 0.003922 | 10.316 / 9.241 |
| v18-study-evening | PASS / PASS | 0.008280 | 0.015686 | 11.830 / 10.977 |
| v19-garden-facade | PASS / PASS | 0.001674 | 0.007843 | 5.648 / 5.302 |
| v20-kitchen-run | PASS / PASS | 0.010034 | 0.023529 | 12.746 / 12.010 |
| v21-lounge-evening | PASS / PASS | 0.009626 | 0.023529 | 11.363 / 10.760 |
| v22-parents-day | PASS / PASS | 0.000786 | 0.003922 | 7.446 / 7.044 |
| v23-gf-gallery | PASS / PASS | 0.010076 | 0.015686 | 11.242 / 10.470 |
| v24-bar-alcove | PASS / PASS | 0.008600 | 0.019608 | 11.143 / 10.273 |
| v25-top-garden-gate | PASS / PASS | 0.000527 | 0.003922 | 5.731 / 5.378 |
| v26-top-garden-east | PASS / PASS | 0.000809 | 0.003922 | 5.875 / 5.393 |
| v27-east-yard-above | PASS / PASS | 0.000675 | 0.003922 | 7.217 / 6.586 |
| v28-east-yard-below | PASS / PASS | 0.000727 | 0.003922 | 7.792 / 7.146 |
| v36-north-garden | FAIL crushed_shadows / FAIL crushed_shadows | 0.000766 | 0.003922 | 6.455 / 6.018 |
| v37-north-garden-lounge | PASS / PASS | 0.001308 | 0.003922 | 7.934 / 7.449 |
| v39-north-garden-hanging-retreat | PASS / PASS | 0.001179 | 0.003922 | 6.965 / 6.576 |
| v29-under-stair-store | FAIL crushed_shadows / FAIL crushed_shadows | 0.001555 | 0.007843 | 9.021 / 8.070 |
| v30-under-ramp-store | PASS / PASS | 0.001714 | 0.003922 | 10.722 / 10.224 |
| v31-dressing-hers | PASS / PASS | 0.009601 | 0.023529 | 9.311 / 8.811 |
| v32-dressing-his | PASS / PASS | 0.009098 | 0.023529 | 8.517 / 8.076 |
| v33-basement-north-south | PASS / PASS | 0.001948 | 0.007843 | 9.935 / 8.791 |
| v34-basement-south-north | PASS / PASS | 0.003598 | 0.015686 | 9.706 / 8.668 |
| v40-south-garden-espalier | PASS / PASS | 0.000608 | 0.003922 | 5.860 / 5.534 |
| v41-south-garden-terrace | PASS / PASS | 0.001748 | 0.007843 | 5.402 / 4.936 |

The following values and statuses are copied from the actual render_qa checks, which reduce images to 800 pixels wide. The checker reports clipping to 0.1%, cast to 0.001 and median to 0.01. Each pair is 4.5 / 5.2. WARN means the existing policy made that check advisory; fixed exposure across the set makes the tonal checks advisory. These are the original policy results, not newly relaxed thresholds. Full-resolution analogous statistics are additionally retained as qa_values_45 and qa_values_52 in the comparison JSON and are not the verdict basis.

Clipping counts pixels whose maximum encoded channel is at least 0.995. Cast measures the spread of mean red/green/blue among midtones strictly between 0.25 and 0.75. Median is encoded-display luminance using red/green/blue weights 0.2126/0.7152/0.0722.

| View | Clipped % / status | Cast / status | Median / status |
|---|---:|---:|---:|
| v01-kitchen-garden | 0.4% PASS / 0.4% PASS | 0.046 PASS / 0.046 PASS | 0.26 WARN / 0.26 WARN |
| v02-garden-living | 0.0% PASS / 0.0% PASS | 0.067 PASS / 0.067 PASS | 0.43 PASS / 0.43 PASS |
| v03-street-lounge | 0.0% PASS / 0.0% PASS | 0.010 PASS / 0.011 PASS | 0.12 WARN / 0.12 WARN |
| v04-study-deck | 0.3% PASS / 0.3% PASS | 0.025 PASS / 0.024 PASS | 0.44 PASS / 0.44 PASS |
| v05-parents-bedroom | 0.4% PASS / 0.4% PASS | 0.055 PASS / 0.055 PASS | 0.42 PASS / 0.41 PASS |
| v06-kids-room | 11.8% WARN / 11.8% WARN | 0.038 PASS / 0.038 PASS | 0.49 PASS / 0.49 PASS |
| v08-cinema | 0.3% PASS / 0.2% PASS | 0.073 PASS / 0.072 PASS | 0.26 WARN / 0.25 WARN |
| v09-dining-evening | 0.9% PASS / 0.9% PASS | 0.058 PASS / 0.058 PASS | 0.69 PASS / 0.68 PASS |
| v10-living-evening | 1.2% PASS / 1.2% PASS | 0.069 PASS / 0.068 PASS | 0.42 PASS / 0.42 PASS |
| v11-stair-void | 0.6% PASS / 0.6% PASS | 0.062 PASS / 0.059 PASS | 0.70 PASS / 0.69 PASS |
| v12-ensuite | 0.0% PASS / 0.0% PASS | 0.053 PASS / 0.053 PASS | 0.51 PASS / 0.49 PASS |
| v13-kids-b | 0.0% PASS / 0.0% PASS | 0.072 PASS / 0.070 PASS | 0.39 PASS / 0.37 PASS |
| v15-family-bath | 1.7% PASS / 1.7% PASS | 0.111 FAIL / 0.109 FAIL | 0.30 PASS / 0.30 WARN |
| v35-family-bath-wc | 0.0% PASS / 0.0% PASS | 0.091 PASS / 0.088 PASS | 0.30 WARN / 0.29 WARN |
| v16-guest-wc | 0.1% PASS / 0.0% PASS | 0.055 PASS / 0.056 PASS | 0.68 PASS / 0.67 PASS |
| v17-dirty-kitchen | 0.0% PASS / 0.0% PASS | 0.028 PASS / 0.028 PASS | 0.42 PASS / 0.42 PASS |
| v18-study-evening | 0.0% PASS / 0.0% PASS | 0.067 PASS / 0.066 PASS | 0.42 PASS / 0.41 PASS |
| v19-garden-facade | 0.0% PASS / 0.0% PASS | 0.021 PASS / 0.022 PASS | 0.34 PASS / 0.34 PASS |
| v20-kitchen-run | 3.5% WARN / 3.4% WARN | 0.050 PASS / 0.049 PASS | 0.80 PASS / 0.79 PASS |
| v21-lounge-evening | 0.7% PASS / 0.7% PASS | 0.057 PASS / 0.057 PASS | 0.56 PASS / 0.55 PASS |
| v22-parents-day | 10.5% WARN / 10.5% WARN | 0.045 PASS / 0.045 PASS | 0.76 PASS / 0.76 PASS |
| v23-gf-gallery | 1.9% PASS / 1.8% PASS | 0.037 PASS / 0.035 PASS | 0.76 PASS / 0.75 PASS |
| v24-bar-alcove | 1.5% PASS / 1.5% PASS | 0.068 PASS / 0.068 PASS | 0.40 PASS / 0.39 PASS |
| v25-top-garden-gate | 0.0% PASS / 0.0% PASS | 0.010 PASS / 0.010 PASS | 0.76 PASS / 0.76 PASS |
| v26-top-garden-east | 0.0% PASS / 0.0% PASS | 0.015 PASS / 0.015 PASS | 0.54 PASS / 0.54 PASS |
| v27-east-yard-above | 0.0% PASS / 0.0% PASS | 0.025 PASS / 0.025 PASS | 0.51 PASS / 0.51 PASS |
| v28-east-yard-below | 0.0% PASS / 0.0% PASS | 0.020 PASS / 0.020 PASS | 0.44 PASS / 0.44 PASS |
| v36-north-garden | 0.0% PASS / 0.0% PASS | 0.013 PASS / 0.013 PASS | 0.14 WARN / 0.14 WARN |
| v37-north-garden-lounge | 0.0% PASS / 0.0% PASS | 0.028 PASS / 0.028 PASS | 0.15 WARN / 0.15 WARN |
| v39-north-garden-hanging-retreat | 0.0% PASS / 0.0% PASS | unreported (no midtones) / unreported (no midtones) | 0.12 WARN / 0.12 WARN |
| v29-under-stair-store | 0.0% PASS / 0.0% PASS | 0.026 PASS / 0.025 PASS | 0.04 WARN / 0.04 WARN |
| v30-under-ramp-store | 0.0% PASS / 0.0% PASS | 0.006 PASS / 0.007 PASS | 0.06 WARN / 0.06 WARN |
| v31-dressing-hers | 0.1% PASS / 0.1% PASS | 0.053 PASS / 0.053 PASS | 0.21 WARN / 0.21 WARN |
| v32-dressing-his | 0.1% PASS / 0.1% PASS | 0.061 PASS / 0.062 PASS | 0.18 WARN / 0.17 WARN |
| v33-basement-north-south | 0.0% PASS / 0.0% PASS | 0.065 PASS / 0.065 PASS | 0.45 PASS / 0.45 PASS |
| v34-basement-south-north | 4.3% WARN / 4.3% WARN | 0.065 PASS / 0.065 PASS | 0.43 PASS / 0.43 PASS |
| v40-south-garden-espalier | 0.0% PASS / 0.0% PASS | 0.023 PASS / 0.023 PASS | 0.52 PASS / 0.52 PASS |
| v41-south-garden-terrace | 0.0% PASS / 0.0% PASS | 0.021 PASS / 0.021 PASS | 0.34 PASS / 0.34 PASS |

The next table linearises the display PNG through inverse sRGB; it is **not** pre-tone-map physical radiance. Luminance uses the same three weights. Difference percentiles are absolute per-pixel differences at P50/P95/P99 (50th/95th/99th percentiles). Chromaticity is the International Commission on Illumination (CIE) 1931 x/y from linearised display RGB converted to XYZ tristimulus values; pixels whose XYZ sum is below 0.000001 are excluded. A pair gives x/y; a triple gives the declared percentile order. All values are dimensionless.

| View | Mean luminance 4.5 / 5.2 | Difference P50/P95/P99 | Mean absolute x/y difference | P95 absolute x/y difference |
|---|---:|---:|---:|---:|
| v01-kitchen-garden | 0.104695 / 0.104046 | 0.000539/0.003497/0.007677 | 0.001862/0.001562 | 0.004885/0.004122 |
| v02-garden-living | 0.184988 / 0.184735 | 0.000455/0.004048/0.006843 | 0.001437/0.001216 | 0.005220/0.004587 |
| v03-street-lounge | 0.040024 / 0.039598 | 0.000401/0.003374/0.007738 | 0.004770/0.004116 | 0.013529/0.012378 |
| v04-study-deck | 0.231827 / 0.231804 | 0.000000/0.002804/0.005348 | 0.000657/0.000763 | 0.002593/0.003261 |
| v05-parents-bedroom | 0.210875 / 0.202997 | 0.006584/0.021207/0.027661 | 0.001494/0.001169 | 0.004169/0.003288 |
| v06-kids-room | 0.300893 / 0.300900 | 0.000000/0.003111/0.004830 | 0.000735/0.000797 | 0.002599/0.002796 |
| v08-cinema | 0.110425 / 0.102227 | 0.005863/0.022490/0.027960 | 0.002854/0.002402 | 0.006839/0.006221 |
| v09-dining-evening | 0.413251 / 0.401250 | 0.012484/0.022643/0.031459 | 0.001608/0.001046 | 0.005243/0.003153 |
| v10-living-evening | 0.209304 / 0.204575 | 0.004425/0.016631/0.023637 | 0.002677/0.001702 | 0.008908/0.005641 |
| v11-stair-void | 0.393884 / 0.381304 | 0.013154/0.023171/0.032315 | 0.001963/0.001330 | 0.006379/0.003808 |
| v12-ensuite | 0.296266 / 0.279119 | 0.016880/0.027498/0.032716 | 0.001670/0.001140 | 0.003981/0.002830 |
| v13-kids-b | 0.170559 / 0.158145 | 0.012257/0.026479/0.030504 | 0.001992/0.001497 | 0.004491/0.003478 |
| v15-family-bath | 0.121702 / 0.116981 | 0.003031/0.015334/0.022898 | 0.002297/0.001252 | 0.004820/0.003117 |
| v35-family-bath-wc | 0.083116 / 0.080612 | 0.002473/0.004330/0.006574 | 0.002360/0.001252 | 0.004450/0.002894 |
| v16-guest-wc | 0.441013 / 0.421765 | 0.019676/0.026353/0.032595 | 0.001604/0.000998 | 0.003597/0.002576 |
| v17-dirty-kitchen | 0.162995 / 0.162787 | 0.000188/0.003752/0.011772 | 0.001007/0.001153 | 0.002622/0.003089 |
| v18-study-evening | 0.175105 / 0.168577 | 0.006514/0.013721/0.017837 | 0.001718/0.001417 | 0.004767/0.003678 |
| v19-garden-facade | 0.228596 / 0.228505 | 0.000000/0.003650/0.006813 | 0.001434/0.002196 | 0.006647/0.009597 |
| v20-kitchen-run | 0.579077 / 0.565857 | 0.013912/0.026952/0.041075 | 0.001300/0.000997 | 0.004482/0.003258 |
| v21-lounge-evening | 0.252857 / 0.245252 | 0.008088/0.019165/0.027660 | 0.002522/0.001633 | 0.009167/0.005590 |
| v22-parents-day | 0.539065 / 0.539043 | 0.000000/0.004668/0.006434 | 0.000318/0.000348 | 0.001397/0.001613 |
| v23-gf-gallery | 0.557376 / 0.541580 | 0.017525/0.022707/0.024243 | 0.000555/0.000586 | 0.001489/0.001391 |
| v24-bar-alcove | 0.197645 / 0.192352 | 0.004619/0.017349/0.027279 | 0.003131/0.001959 | 0.010546/0.006539 |
| v25-top-garden-gate | 0.484563 / 0.484579 | 0.000000/0.002332/0.004980 | 0.000334/0.000421 | 0.001738/0.002533 |
| v26-top-garden-east | 0.349766 / 0.349727 | 0.000000/0.002550/0.004906 | 0.000574/0.000750 | 0.003150/0.003986 |
| v27-east-yard-above | 0.305118 / 0.305116 | 0.000000/0.002239/0.005109 | 0.000634/0.000984 | 0.003102/0.004846 |
| v28-east-yard-below | 0.266019 / 0.266053 | 0.000000/0.002360/0.005032 | 0.000676/0.000929 | 0.003123/0.004534 |
| v36-north-garden | 0.037789 / 0.037811 | 0.000000/0.001523/0.002956 | 0.001694/0.003294 | 0.007168/0.015753 |
| v37-north-garden-lounge | 0.024245 / 0.024291 | 0.000065/0.001235/0.001947 | 0.002022/0.003339 | 0.006071/0.009864 |
| v39-north-garden-hanging-retreat | 0.013135 / 0.013169 | 0.000000/0.000876/0.001610 | 0.001865/0.002929 | 0.006420/0.010217 |
| v29-under-stair-store | 0.006472 / 0.006271 | 0.000086/0.000936/0.001715 | 0.006214/0.005086 | 0.020760/0.017604 |
| v30-under-ramp-store | 0.008361 / 0.008341 | 0.000069/0.000867/0.002482 | 0.003556/0.004060 | 0.009937/0.011423 |
| v31-dressing-hers | 0.082107 / 0.077742 | 0.002164/0.022272/0.027468 | 0.003782/0.002237 | 0.011799/0.006770 |
| v32-dressing-his | 0.062906 / 0.061810 | 0.001340/0.010032/0.026052 | 0.007027/0.004247 | 0.022950/0.017698 |
| v33-basement-north-south | 0.184309 / 0.184075 | 0.000581/0.004348/0.007915 | 0.001172/0.001026 | 0.004205/0.003677 |
| v34-basement-south-north | 0.230315 / 0.230045 | 0.000588/0.005412/0.013885 | 0.003212/0.001753 | 0.018180/0.007901 |
| v40-south-garden-espalier | 0.242334 / 0.242360 | 0.000000/0.002001/0.004466 | 0.000461/0.000777 | 0.002241/0.003890 |
| v41-south-garden-terrace | 0.201479 / 0.201393 | 0.000022/0.004011/0.008574 | 0.001072/0.001701 | 0.004530/0.007094 |

The raw comparison also records each image’s P5/P50/P95 luminance and valid chromaticity-pixel count. The lead-original comparison, all original QA and amplified difference panels are retained in [lead-comparison](../out/blender52/lead-comparison/comparison.json). [Fresh-reference repeatability](../out/blender52/reference45-lead-stability.json) establishes its observed noise floor; evaluated geometry agrees exactly with the lead receipt.

The critic sees a v32 garment/timber contrast difference despite unchanged garment geometry: the rectangle at columns 420–439, rows 250–449 changes mean encoded luminance from 0.03967 in fresh 4.5 to 0.09988 in 5.2 (original lead 4.5: 0.04047). This local appearance difference remains an OPEN migration-review item; the global QA pass does not certify it. Existing partial island/sofa framing and the three QA failures also remain open. No design was altered to compensate.

## All 25 task points

These are maintained-illuminance predictions in lux with the existing maintenance factor 0.8, black sky, 256 samples, denoising/white balance disabled, a 0.5-reflectance diffuse sensor 1 mm above each task plane, and direct versus 16-bounce total light kept separate. Both fresh runs use the same authored scene and identical nominal/measurement positions. Every one of the 25 existing targets passes in both versions. Targets remain project evidence-card values, not new design rules. Point numbers are one-based recorded order; repeated labels are distinct points. Delta percentages use the fresh 4.5 reading as denominator.

| Point / room / label | Required | Direct 4.5 / 5.2 | Direct change % | Total 4.5 / 5.2 | Total change % |
|---|---:|---:|---:|---:|---:|
| 1 / kitchen / island prep side | 500 | 1077.166 / 976.580 | -9.3380 | 1370.553 / 1254.410 | -8.4742 |
| 2 / kitchen / island seating side | 200 | 837.983 / 761.321 | -9.1484 | 1099.280 / 1010.858 | -8.0437 |
| 3 / kitchen / island prep side | 500 | 1030.154 / 944.357 | -8.3285 | 1228.897 / 1132.670 | -7.8303 |
| 4 / kitchen / island seating side | 200 | 850.942 / 779.431 | -8.4038 | 1115.275 / 1030.907 | -7.5648 |
| 5 / kitchen / island prep side | 500 | 835.446 / 771.825 | -7.6152 | 1113.862 / 1039.409 | -6.6842 |
| 6 / kitchen / island seating side | 200 | 676.593 / 623.591 | -7.8336 | 926.533 / 861.294 | -7.0412 |
| 7 / kitchen / single induction zone | 300 | 1004.738 / 974.719 | -2.9877 | 1308.343 / 1265.494 | -3.2751 |
| 8 / kitchen / sink | 300 | 1154.108 / 1058.653 | -8.2709 | 1355.513 / 1248.377 | -7.9037 |
| 9 / dining / dining table centre | 100 | 546.253 / 531.536 | -2.6941 | 651.848 / 632.967 | -2.8965 |
| 10 / dining / table end (homework) | 200 | 462.132 / 445.560 | -3.5860 | 584.258 / 561.091 | -3.9652 |
| 11 / dirty-kitchen / dirty kitchen run | 500 | 679.030 / 621.179 | -8.5196 | 814.496 / 746.053 | -8.4032 |
| 12 / study-game / study-desk | 400 | 931.578 / 836.580 | -10.1976 | 1009.970 / 909.769 | -9.9212 |
| 13 / study-game / study-adult-desk | 400 | 905.816 / 833.888 | -7.9407 | 974.566 / 898.857 | -7.7684 |
| 14 / kids-a / ka-desk-1 | 400 | 1391.480 / 1272.225 | -8.5703 | 1498.953 / 1372.418 | -8.4416 |
| 15 / kids-a / ka-desk-2 | 400 | 1390.369 / 1271.372 | -8.5587 | 1551.094 / 1420.166 | -8.4410 |
| 16 / kids-b / kb-desk | 400 | 1389.363 / 1270.335 | -8.5671 | 1478.462 / 1353.514 | -8.4512 |
| 17 / parents-bed / pillow | 200 | 1110.905 / 1029.208 | -7.3541 | 1182.981 / 1097.868 | -7.1948 |
| 18 / parents-bed / pillow | 200 | 1114.985 / 1033.778 | -7.2833 | 1181.648 / 1096.613 | -7.1963 |
| 19 / family-bath / fb-basin | 300 | 1337.476 / 1195.843 | -10.5896 | 1608.766 / 1448.036 | -9.9909 |
| 20 / parents-ensuite / pe-basin | 300 | 631.213 / 567.165 | -10.1467 | 759.376 / 685.724 | -9.6990 |
| 21 / guest-wc / gwc-basin | 300 | 1375.235 / 1222.517 | -11.1048 | 1602.438 / 1427.657 | -10.9072 |
| 22 / lounge / armchair | 200 | 789.702 / 716.896 | -9.2195 | 955.117 / 877.740 | -8.1013 |
| 23 / bar-alcove / daybed nook | 200 | 324.603 / 316.917 | -2.3680 | 420.821 / 408.968 | -2.8168 |
| 24 / cinema / cinema desk | 400 | 1483.930 / 1363.040 | -8.1466 | 1523.844 / 1399.543 | -8.1570 |
| 25 / cinema / cinema desk | 400 | 1492.440 / 1373.977 | -7.9375 | 1527.212 / 1406.000 | -7.9368 |

Comparison with the retained `knowledge/repro-lighting-baseline.json` is separately included for all 25 points in [lighting-comparison.json](../out/blender52/lighting-comparison.json), including direct/total historical readings and deltas. Its authored hash differs from the current draped-garment scene, so it cannot isolate a renderer effect. The fresh 4.5 receipt above is the required same-scene baseline. No allowance or calibration factor was widened to claim equality.

IES means the Illuminating Engineering Society photometric-file format. A separate four-case CPU calibration isolates a changed IES path from the villa geometry. At two metres, 256 samples, 32×32 pixels and 0.5-reflectance Lambertian sensor, bare 1000-power white gives 19.891257919 lux in 4.5 and 19.891257922 lux in 5.2 (closed-form expectation 19.894367886 lux). The same DESK IES at unchanged power 162.624 gives 79.376970725 versus 73.241999921 lux: −7.728905%. The 2700 K counterpart gives 79.376971905 versus 73.241999391 lux: −7.728907%. The bare warm counterpart also agrees to within 0.000000006 lux. Thus colour alone and villa geometry cannot explain this minimal-case shift. The internal Cycles IES cause and cross-angle calibration remain OPEN; no production calibration was changed. [Complete probe, file hash and readings](../out/blender52/photometry-control.json); executable reproduction is `out/blender52/physics_probe.py` with the explicit runtime and output directory.

## Imports, stand-ins and cloth

All 21 imports have identical mesh counts, vertex/face counts, placement hashes, review/source geometry and world bounds. Combined: 2,800,764 vertices and 5,209,608 faces. Maximum measured import-versus-review transform error is 0.001602173 mm in both builds. Eight unique source-asset measurement records compare identically, including ordered face/component and buffer/texture hashes. The unchanged scene pairs pass the renderer’s unconditional source/stand-in admission; enclosure uses the existing 0.010 mm numerical tolerance. No imported appearance was converted into a physical stand-in or source mesh edited. [Source hashes](../out/blender52/import-source-comparison.json), [all placement hashes and counts](../out/blender52/import-placement-comparison.json).

| Model | Vertices | Faces | Counts / placement / review / bounds |
|---|---:|---:|---|
| model-living-sofa | 139387 | 262118 | identical |
| model-living-chair-1 | 4965 | 7062 | identical |
| model-living-chair-2 | 4965 | 7062 | identical |
| model-lounge-armchair | 4965 | 7062 | identical |
| model-rug-living | 2038664 | 4066436 | identical |
| model-cinema-desk | 61038 | 87606 | identical |
| model-study-desk | 92374 | 131860 | identical |
| model-study-adult-desk | 95059 | 135794 | identical |
| model-ka-desk-1 | 61038 | 87606 | identical |
| model-ka-desk-2 | 61038 | 87606 | identical |
| model-kb-desk | 61038 | 87606 | identical |
| model-pb-vanity | 92374 | 131860 | identical |
| model-cinema-desk#chair-1 | 9860 | 12660 | identical |
| model-cinema-desk#chair-2 | 9860 | 12660 | identical |
| model-study-desk#chair-1 | 9860 | 12660 | identical |
| model-study-desk#chair-2 | 9860 | 12660 | identical |
| model-study-adult-desk#chair-1 | 9860 | 12660 | identical |
| model-ka-desk-1#chair-1 | 9860 | 12660 | identical |
| model-ka-desk-2#chair-1 | 9860 | 12660 | identical |
| model-kb-desk#chair-1 | 9860 | 12660 | identical |
| model-pb-bed | 4979 | 8650 | identical |

All ten normal 5.2 cloth inputs reproduce in two independent processes with different Python hash salts. Nine output meshes differ from the pinned cache because runtime identity contributes to the initial pattern seed. With the original pattern seed held fixed, all ten 5.2 meshes exactly equal the 4.5 geometry; hanging initial-vertex hashes also agree. Folded procedural layers have no cloth solver, and their phase follows the same seed. These controls do not change production seed semantics or cache files. All normal rebakes pass the existing enclosure/morphology screens, but were not integrated or visually accepted.

| Template | Normal rebake equals 4.5 | Max corresponding vertex change mm | Fixed-pattern result equals 4.5 |
|---|---|---:|---|
| dress-hers-long-hang-0-garment-0-0 | False | 364.524037 | True |
| dress-hers-long-hang-0-garment-0-1 | False | 1508.724645 | True |
| dress-hers-double-hang-1-garment-0-0 | True | 0.000000 | True |
| dress-hers-double-hang-1-garment-1-0 | False | 3.784313 | True |
| dress-hers-double-hang-1-garment-1-1 | False | 5.696974 | True |
| dress-hers-drawers-2-content-0-0-0 | False | 0.411323 | True |
| dress-hers-hat-shelf-3-stack-0-0 | False | 0.225551 | True |
| dress-his-trousers-pullout-1-stack-0-0 | False | 0.131416 | True |
| dress-his-drawers-2-content-0-0-0 | False | 0.044138 | True |
| dress-his-shelves-3-stack-0-0 | False | 0.153266 | True |

[Cloth full values](../out/blender52/cloth/final-comparison.json) include every seed/input/output hash, bounds deltas, mean/P95 displacement, enclosure and morphology findings. [Controlled process receipts](../out/blender52/cloth-controlled/comparison.json). The 101 placed garment appearances in the matched scene continue to use the original admitted cache.

## Denoising and speed

The threshold was written to [protocol.json](../out/blender52/protocol.json) before measuring: candidate must pass existing render_qa, encoded-channel mean absolute error ≤0.02, and 95th-percentile absolute channel error ≤0.06 against the 4.5.14 1024-sample reference. The tested maximum-sample ladder is 64/128/256/512/1024 with OptiX denoising, versus OpenImageDenoise in the reference. All are 960×640 evaluation frames, with identical saved camera/exposure/settings; adaptive sampling remains enabled. They are not full-resolution presentation finals.

| View | Reference 1024 seconds / QA | First passing maximum samples | Candidate seconds |
|---|---:|---:|---:|
| v01-kitchen-garden | 42.948 / PASS | 64 | 9.065 |
| v08-cinema | 33.657 / PASS | 64 | 8.646 |
| v36-north-garden | 23.043 / FAIL | none | unavailable |

| View | Samples | Seconds | Mean error | P95 error | QA / threshold |
|---|---:|---:|---:|---:|---|
| v01-kitchen-garden | 64 | 9.065 | 0.010015 | 0.031373 | PASS / PASS |
| v01-kitchen-garden | 128 | 4.365 | 0.007720 | 0.027451 | PASS / PASS |
| v01-kitchen-garden | 256 | 8.485 | 0.006453 | 0.023529 | PASS / PASS |
| v01-kitchen-garden | 512 | 16.776 | 0.005591 | 0.019608 | PASS / PASS |
| v01-kitchen-garden | 1024 | 33.397 | 0.003675 | 0.011765 | PASS / PASS |
| v08-cinema | 64 | 8.646 | 0.015415 | 0.043137 | PASS / PASS |
| v08-cinema | 128 | 3.411 | 0.013925 | 0.035294 | PASS / PASS |
| v08-cinema | 256 | 6.573 | 0.012236 | 0.031373 | PASS / PASS |
| v08-cinema | 512 | 12.961 | 0.012740 | 0.031373 | PASS / PASS |
| v08-cinema | 1024 | 25.710 | 0.012450 | 0.027451 | PASS / PASS |
| v36-north-garden | 64 | 7.916 | 0.005346 | 0.015686 | FAIL / FAIL |
| v36-north-garden | 128 | 2.188 | 0.002982 | 0.011765 | FAIL / FAIL |
| v36-north-garden | 256 | 4.112 | 0.002286 | 0.007843 | FAIL / FAIL |
| v36-north-garden | 512 | 8.001 | 0.002068 | 0.007843 | FAIL / FAIL |
| v36-north-garden | 1024 | 15.754 | 0.001531 | 0.003922 | FAIL / FAIL |

Timing limits: the first reference and first ladder image include initial scene synchronization and acceleration-structure costs inside the render call; later ladder images reuse persistent data. Process startup and blend-file loading are excluded from these frame timings. This is one trial per setting, not a confidence interval or equal-warmth benchmark. A maximum sample count is an adaptive cap, not proof every pixel received that many samples. No temporal flicker, camera-motion sequence or full-resolution scaling was measured. Do not turn these still-frame times into a promised fly-through budget, particularly while the north-garden QA failure remains. [Full speed receipts](../out/blender52/speed/comparison.json).

## Official Blender MCP and validation

The official Blender Lab server is installed under `out/blender52/` only, revision `dbbf836ad4b1025f14a2b3b504c43903f39e0b04`, GPL-3.0-or-later, requiring Blender ≥5.1. Its separate virtual environment contains blender-mcp 1.0.2; the project virtual environment was untouched. All 26 tools were discovered. Actual CLI and background-bridge data-block summaries of a disposable villa copy pass; the bridge bound only to 127.0.0.1 and was stopped afterward. [Smoke receipt](../out/blender52/mcp-smoke-process.json), [results](../out/blender52/mcp-smoke.json), [tool schemas](../out/blender52/mcp-tools.json).

Windows Claude Code registration over SSH stdio, complete inventory and arbitrary-code safety notes are in [docs/ops/blender-mcp.md](ops/blender-mcp.md). No Claude/Codex connection configuration was edited. User configuration and scripts for the add-on are isolated from 4.5.

Validation: 62 focused regression tests pass, including version/cache identity, real sky API metadata, GPU refusal, optical-input preflight, controlled cloth attribution, repeated task identity and generated agent adapters. Actual Blender sky checks pass in both versions; 5.2 evaluated-ray/importer tests pass. `scripts/verify.py --portable` exits 0. The requested plain `scripts/verify.py` exits 1 only because the Linux workstation has no installed Windows Revit-family corpus for its RFA (Revit family file) parser check. The gate was not changed. [Focused log](../out/blender52/focused-complete.log), [portable verification](../out/blender52/verify-portable-complete.log), [plain verification](../out/blender52/verify-resume.log). The lead owns the full suite and commit.

Lessons to register: sky API adapters must preserve source defaults; prove actual GPU execution before timing; preflight the exact optical root; separate runtime-dependent pattern reseeding from solver drift; preserve recorded task indices when labels repeat; a global QA pass cannot establish local appearance equivalence; physical lighting calibration must be remeasured across runtimes even when all design targets pass. Closed controls are registered in `knowledge/build-input-guards.json`; IES-path transfer, bevel-runtime drift, local v32 appearance and inherited framing/QA failures remain open.
