# Garden G4e — shade appearance and north evening camera

2026-10-08. Baseline: lead-reviewed workstation scene at `1b4f33b`, retained read-only in `/home/omar/archpipe/villa-render/155b74a730c0d87aea2fcb8a/scene.json`. Appearance and camera corrections are complete and independently reviewed as neutral diagnostics. Evening presentation lighting acceptance remains open: the retained cool-cast failure is reproduced and its sky source measured. No presentation images were rendered; no commit was made.

QA means quality assurance. Coordinate lists give model x, y and z in that order: x and y are the two horizontal axes, z is elevation. Units m, mm, K and W mean metres, millimetres, kelvin colour temperature and renderer watts. PNG is the preview image format; EXR is the linear high dynamic range image format. SHA-256 is the 256-bit content identity hashing algorithm.

## Delivered appearance

Both existing shared plant builders now call `garden_g4e.clump`. Exactly ten plant face arrays change: one Rhapis and nine Aspidistra across north, east and south gardens. All other mesh faces, plant centers, roots, beds, paths, swing geometry and fixture geometry remain identical to the retained baseline. All 33 prop records are identical when compared by identifier; their list order differs. Lights, all four fixture records including aim, sky and exposure definitions remain identical. Evidence: `out/garden-g4e/acceptance-measurements.json`, `prop-scope-comparison.json` and the frozen real inputs `tests/fixtures/garden-g4e-before.json.gz`.

| Measurement | Delivered | Required / retained basis |
|---|---:|---|
| Rhapis canes | 13, varied heights, fibre-profile surfaces | Dense many-cane clump, authored young appearance |
| Rhapis fans | 52, each 7–9 deep segments | 5–10 segments in the review brief |
| Rhapis height / maximum plan spread | 1.70000 / 1.00000 m | Original recorded young envelope |
| Rhapis foliage gap above soil | 0.186234991 m | Existing maximum 0.20000 m |
| Cane top below its own foliage maximum | At least 0.09428 m | No bare cane above foliage |
| Aspidistra leaves per clump | 24 independent basal petioles/blades | No shared above-ground stalk |
| Aspidistra height / maximum plan spread | 0.50000 / 0.40000 m | Original recorded young envelope |
| Aspidistra basal root span | 0.117235 m by 0.120856 m | Distributed real soil attachments |
| Aspidistra foliage gap | 0.057183952 m, all nine | Existing maximum 0.20000 m |
| Aspidistra blade crown-to-tip drop | 0.04491–0.05857 m | Outward arch in actual geometry |

The morphology follows the client brief and the descriptions of clustered fibrous canes / palmate leaves in [NC State Rhapis](https://plants.ces.ncsu.edu/plants/rhapis-excelsa/) and solitary basal glossy lanceolate leaves in [NC State Aspidistra](https://plants.ces.ncsu.edu/plants/aspidistra-elatior/). The envelope and quantitative habit thresholds are authored example assumptions. Leaf roughness 0.32, dark-green optical appearance and cane fibre proxy are explicitly assumed; nursery identity, procurement, photographic likeness and measured gloss remain unverified.

An intermediate palm that resembled repeated umbrellas was rejected. A later 0.235 m soil gap failed the existing guard; moving the first fan attachment lower corrected the plant itself. No guard limit changed. The full reconstruction passes existing soil-contact and new real-face habit checks. Tests reproduce all ten frozen old habits, actual raised cane tips, concentrated petioles and elevated foliage, and translated/renamed specimens.

## Cameras and alias

`v42-north-garden-evening` records `v41-north-garden-evening` in `aliases`; the existing `v41-south-garden-terrace` retains its number. The contract rejects duplicate numeric view prefixes, including differently named v41 and v07 siblings.

| View | Position in metres | Target in metres | Lens / vertical shift |
|---|---|---|---|
| v42 evening | [3.900, -26.550, -1.650] | [1.739460010, -24.468638198, -1.650] | 24 mm / -0.1542019543 |
| v37 lounge | [4.067, -28.021, -1.650] | [2.056193095, -25.794645223, -1.650] | 24 mm / -0.0431147162 |

Both cameras remain level, with the existing 36 mm sensor and 1.35 m eye height above the lower floor. Vertical shift is the image offset as a fraction of sensor width; a negative value frames downward while the lens stays level. The evening camera stands inside the lounge and shows the rear swing basket/cushions through existing glazing. Its caption states this; v39 continues to show the seating face. The foreground spike housing clears the composition guard. Actual first-hit subject counts are 10 palm / 8 Fatsia / 8 basket out of 13 rays, against the unchanged minimum 7. Full subject framing, standing-domain, lens clearance and central opening-frame checks are quiet.

Denser palm foliage hid the feature stone from the original v37 camera: 6 of 13 rays. Camera-only searches in the lounge failed to recover it. The first nook candidate recovered 7 rays but failed the central window-frame guard. The final nook camera passes all existing checks with 7 stone / 12 palm / 9 Fatsia rays. Independent review recognises the partially screened angular stone; it remains a garden view with foliage in front. Search evidence is retained under `out/garden-g4e/companion-search*.json` and `.log`; unsuccessful searches are diagnosis, not accepted cameras.

## Evening diagnosis

The retained display image is assessed using the production `villa_qa_context` adapter. `out/garden-g4e/retained-qa.json` reproduces **cool cast 0.105 against limit 0.02**, and **99.5th-percentile display luminance 0.76 against minimum 0.9**. The existing locked-exposure policy labels the latter WARN; colour cast is FAIL. This classification was preserved. Retained exposure is **-1.27043736 stops**. Retained linear image mean luminance is 0.52573178 and its 99.5th percentile is 1.82525204; linear values and display QA values use different transformations and must not be compared to the same limit.

Four source-isolation probes use the actual nearby scene geometry, production glass, actual generic photometry and physical snoots at 320 pixels wide by 216 high, 96 samples and eight bounces. They output linear EXR files only. RGB means linear red, green and blue; luminance is `0.2126 × red + 0.7152 × green + 0.0722 × blue`, where × means multiplication and + means addition. Values below are linear pixel means over first-hit surface masks. Sky-only disables the uplights; uplights-only disables the sky; zero-gravel means a temporary black albedo diagnostic that is restored after measurement. Sampling noise prevents exact addition of independently sampled variants.

| Original camera / surface | Combined | Sky only | Uplights only | Sky, zero gravel albedo |
|---|---:|---:|---:|---:|
| Foliage | 0.44352 | 0.16614 | 0.28951 | 0.14794 |
| Pale gravel | 0.77119 | 0.75617 | 0.01650 | 0.02288 |
| Walls | 0.70449 | 0.68886 | 0.01675 | 0.63788 |

The evening HDRI (high dynamic range environment image), Belfast sunset at the unchanged 30 lux horizontal illuminance, has horizontal-weighted blue/red ratio **1.379**. The unchanged 2700 K lamp source has blue/red ratio **0.0996**. About 98% of original visible gravel/wall mean luminance remains with the sky alone. Removing gravel reflection reduces sky-lit wall luminance about 7.4% and foliage about 11%. The pale gravel has warm-neutral base colour [0.74, 0.71, 0.65]; it reflects and amplifies the blue sky. The uplight source is warm.

Each uplight retains 120 source lumens, approximately 92.989–93.634 outgoing lumens after the physical snoot, and its 30° beam. Original uplights-only foliage 99.5th-percentile linear luminance is **14.29662**: the lights reach foliage and create strong local highlights. Their warm contribution covers too little of the displayed court/background to satisfy whole-image QA at the locked exposure. Increasing output or aiming warm light at the pale background would compensate for the sky-driven cast; the evidence does not establish an erroneous original aim.

The final v42 linear probe measures a different visible surface population through glass: combined / sky-only / uplights-only foliage means **0.10530 / 0.09759 / 0.01117**, and uplights-only foliage 99.5th percentile **0.43707**. Visible gravel remains **0.75941 / 0.75071 / 0.00854**. The new camera clears foreground hardware but sees less of the strongly uplighted foliage faces. This is recorded as a lighting limitation, not a claimed improvement or new QA pass. Aim, flux, beam, sky, gravel, exposure, white balance and QA limits remain unchanged. An overall evening lighting correction needs a separate sky/lighting design decision beyond the authorised appearance/camera/aim scope. No new presentation QA result exists.

Probe data and four linear images per set:

- `out/garden-g4e/diagnosis-before-production-glass/diagnosis.json` and `{combined,sky-only,uplights-only,sky-no-gravel-bounce}.exr`.
- `out/garden-g4e/diagnosis-after-production/diagnosis.json` and the same four filenames.

## Neutral before/after previews

Each changed element has a neutral pair at the paths below. Isolated specimens use identical recorded staging, camera and 1.8 m scale reference. Actual shape and material receipts match; staging translation is diagnostic only.

| Element | Before | After |
|---|---|---|
| Rhapis north accent | `out/garden-g4e/before-all/landscape-north-rhapis-accent.png` | `out/garden-g4e/after-all-final/landscape-north-rhapis-accent.png` |
| Aspidistra north 00 | `out/garden-g4e/before-all/landscape-north-mid-00.png` | `out/garden-g4e/after-all-final/landscape-north-mid-00.png` |
| Aspidistra north 01 | `out/garden-g4e/before-all/landscape-north-mid-01.png` | `out/garden-g4e/after-all-final/landscape-north-mid-01.png` |
| Aspidistra north 02 | `out/garden-g4e/before-all/landscape-north-mid-02.png` | `out/garden-g4e/after-all-final/landscape-north-mid-02.png` |
| Aspidistra east 00 | `out/garden-g4e/before-all/landscape-east-edge-00.png` | `out/garden-g4e/after-all-final/landscape-east-edge-00.png` |
| Aspidistra east 01 | `out/garden-g4e/before-all/landscape-east-edge-01.png` | `out/garden-g4e/after-all-final/landscape-east-edge-01.png` |
| Aspidistra east 02 | `out/garden-g4e/before-all/landscape-east-edge-02.png` | `out/garden-g4e/after-all-final/landscape-east-edge-02.png` |
| Aspidistra south 0 | `out/garden-g4e/before-all/landscape-g6-foliage-front-0.png` | `out/garden-g4e/after-all-final/landscape-g6-foliage-front-0.png` |
| Aspidistra south 1 | `out/garden-g4e/before-all/landscape-g6-foliage-front-1.png` | `out/garden-g4e/after-all-final/landscape-g6-foliage-front-1.png` |
| Aspidistra south 2 | `out/garden-g4e/before-all/landscape-g6-foliage-front-2.png` | `out/garden-g4e/after-all-final/landscape-g6-foliage-front-2.png` |
| Evening camera | `out/garden-g4e/context-production-before/v41-north-garden-evening-neutral.png` | `out/garden-g4e/context-production-after/v42-north-garden-evening-neutral.png` |
| Affected lounge camera | `out/garden-g4e/context-production-before/v37-north-garden-lounge-neutral.png` | `out/garden-g4e/context-production-v37-after/v37-north-garden-lounge-neutral.png` |

Receipts: `before-all/isolated-preview-evidence.json`, `after-all-final/isolated-preview-evidence.json`, and `context-preview-evidence.json` in each context directory above, all beneath `out/garden-g4e`. Contexts disable every design luminous shader and use production glass interface transmittance. The identical white 1000 W, 3 m diagnostic softbox is separately recorded at [0.2, -26.5, -0.1], aimed at [1.3, -25.2, -1.7]; it never enters the authored scene. Earlier warm/dark or frame-failing context previews are superseded.

Independent scoped review: `out/garden-g4e/plant-preview-review.md` and `final-preview-review.md`. The accepted integrated geometry identity digest (SHA-256) is `3f7722f94ecd2c1ca5941fdacc32e86ca980b49feea9513e880b8d3f77236a2b`. Staged versus integrated plant differences are metadata only: labels, basis, local axes, the existing south element tag and the restored Aspidistra spread record. Face arrays and material assignments match. Both cameras and all immutable design geometry were reviewed without presentation illumination.

## Verification and operating changes

Used `/home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python`, `PYTHONPATH=src`, `NO_COLOR=1`, `OPENBLAS_NUM_THREADS=1`. No package installation. Protected shared symlinks were untouched.

| Check | Result |
|---|---|
| Complete production `validate_scene` | 0 findings |
| Focused garden views | Exit 0; 11 tests in 89.559 s; `out/garden-g4e/focused-garden-views.log` |
| Combined landscape, render standard/views, remaining garden regressions, fixture record/material basis and agent adapters | 203 tests in 2083.318 s: 201 passed; exit 1 from the two historical test defects below. Log retained at `out/garden-g4e/focused-final.log` |
| Corrected G4d module, including fixture records/material basis and negative camera | Exit 0; all 13 tests in 10.088 s; `out/garden-g4e/focused-g4d-final.log` |
| Corrected G6b module, including actual finish omission and renamed replacement | Exit 0; all 9 tests in 31.485 s; `out/garden-g4e/focused-g6b-final.log` |
| Final focused coverage | All 214 unique cases verified after the affected-module reruns; 236 test executions across these four final logs |
| `scripts/verify.py --portable`, normal HOME | Exit 0; 143 PASS, 0 FAIL |
| `scripts/verify.py --portable`, newly empty HOME | Exit 0; 143 PASS, 0 FAIL |

The first focused run exposed a non-garden early-return mistake and the historical fixture's incomplete unchanged-material definitions. The early return now stays quiet for non-garden cameras. The combined final run found that the negative historical camera still used the partial fixture, and that G6b's expected omitted-finish list lacked `aspidistra-leaf`. Both are test-context/expectation fixes: every historical physical-ray variant now uses the completed material definitions, and the independent omission/replacement proof explicitly covers the new approved finish. The affected modules were rerun in full and exited zero; no production guard or limit was relaxed. The 201 other combined-run cases and all 11 garden-view cases passed. This report preserves the failed combined exit status instead of relabelling its log as successful.

A final metadata audit restored Aspidistra's original recorded spread 0.5 m (the actual young geometry remains 0.4 m wide); the real-case preservation test now asserts this separately. One intermediate focused run was interrupted to apply this correction. Earlier failures and the v37 frame failure are retained in diagnostic logs. Full suite and commit belong to the lead.

`docs/LEARNINGS.md`, `knowledge/garden-render-guards.json`, `docs/ops/garden-g4e.md`, the canonical villa-render skill and generated Claude adapter were updated together. `scripts/sync_agent_assets.py` was run after the skill edit. The repeated escape is that valid individual geometry and a neutral world alone do not establish a valid visible result: habit changes must recheck existing camera sightlines, and neutral context must explicitly isolate emission and preserve production glass. The bedroom remains a capability example; this work approves no real villa design gate.
