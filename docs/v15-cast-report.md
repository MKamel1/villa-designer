# v15 family-bath colour-cast diagnosis — 2026-10-06

The warm cast predates C4. The measured cause is the specified warm lamps mixed with daylight and the specified cream marble, photographed with the day state's white balance. No incorrect marble assignment, new CCT conversion error or C4-induced darkening was found. Preserve the design, exposure and check. **The production `colour_cast` failure remains open; this report does not approve the image.**

RGB means red, green and blue, in that order. Linear RGB below is scene-linear Rec.709 colour before display development; texture values are reflectances, while EXR values are radiances in the renderer's calibrated units. Luminance is computed as 0.2126 times red plus 0.7152 times green plus 0.0722 times blue. CCT means correlated colour temperature, measured in kelvin (K). Positions are metres in the model's coordinates, with ground-floor finished floor at height zero. Exposure stops are Blender's logarithmic camera gain: one additional stop doubles the linear signal. The cast score is the standard deviation of the three mean **display-encoded** RGB channels of pixels whose display luminance lies between 0.25 and 0.75; it is not an EXR colour-temperature measurement.

## Reproduction and scope

Inspected the retained production PNGs, linear EXRs, scene and per-view records in job `/home/omar/archpipe/villa-render/b1ee556e3d7886fde1d5b502`. Its provenance records clean commit `1a4ba1a`; samples are 256 and resolution is 960 × 640. Current `fb0ba91` agrees on bathroom geometry, all materials, lights and views. Rebuilding also produced nine differing non-bathroom furniture/landscape mesh records; the retained production scene was used for the reproduction instead of silently substituting a rebuilt scene.

Re-ran the current QA on the retained images without changing its inputs:

| View | Cast | Status | White balance | Locked exposure stops | Median display luminance |
|---|---:|---|---:|---:|---:|
| v12 ensuite | 0.048 warm | PASS | 3000 K | −6.00519 | 0.54 |
| v15 family-bath | 0.110 warm | FAIL | 5500 K | −10.33598 | 0.26 |
| v16 guest-WC | 0.049 warm | PASS | 3000 K | −6.00519 | 0.72 |
| v35 family-bath WC | 0.079 warm | PASS | 5500 K | −10.33598 | 0.26 |

The two evening images are therefore not an equal-camera comparison of marble. Their camera gain is 20.12 times the day gain, and their white balance is also different. These are the saved scene settings, not proposed adjustments. Sources: retained per-view records; [exposure definitions and view declarations](../src/archpipe/concept/villa_render.py); [cast implementation](../src/archpipe/render_qa.py).

No presentation images were rendered. Diagnostic transport used 192 × 128 linear EXRs, 512 samples, no denoising, the renderer's normal bounce settings (16 total/diffuse, 8 glossy, 16 transmission/transparent) and zero direct/indirect clamping. Sources retain the view's specified dimmers, with no additional maintenance reduction. Raw EXRs were also developed into temporary diagnostic pixel buffers under the **unchanged saved** day camera, without another render. No diagnostic intervention was written into design input.

## 1. Before and after C4

Built scenes from `git archive 00b6933` and `git archive be10734` in isolated `/tmp` trees, with read-only access to the shared assets. Built the current scene in this worktree. No branch, generated extract or shared asset was modified.

The family-bath IES sources are identical by value in all three builds:

| Source id | CCT | Lumens | Emitter position |
|---|---:|---:|---|
| `DL-family-bath-01` | 2700 K | 732.6 | (10.552, −25.356, 2.670) |
| `DLN-family-bath-02` | 2700 K | 1343.2 | (10.382, −24.241, 2.670) |
| `DLN-family-bath-03` | 2700 K | 1343.2 | (9.627, −25.686, 2.670) |
| `TOE-family-bath-06` | 2200 K | 55.5 | (9.747, −25.686, 0.300) |

The toe strip's night layer is **off** in v15. Two mesh-emitting sconces, `SCONCE-family-bath-04` and `-05`, remain 3000 K, nominally 450 lumens each. The production mesh areas yield 438.773 lumens each, reflecting the sphere's tessellation; this is not a new flux setting. C4 translates every sconce vertex by (0.023, 0, 0) metres to the actual finished wall, moving their centres from (9.337, −26.161/−25.211, 1.600) to (9.360, −26.161/−25.211, 1.600). It does not change their shape, material, CCT or flux. Visible downlight lens glow, restricted to camera/glossy rays, is also unchanged.

All material definitions are exactly equal across the three builds. Family-bath floor, shower base and wall material remain `marble-bath`: Marble014, base tint (0.70, 0.66, 0.58), target reflectance 0.62, nominal roughness 0.30 and tile size 1.20 metres. C4i adds actual closed wall finish solids and moves their occupied faces inward by 0.023 metres. It affects transport geometry and texture sample locations, but does not replace the texture or tint. The window pane faces remain identical: width 0.80 metres, height 0.60 metres, sill 1.70 metres, glass transmittance 0.70 across two interfaces. The sun remains altitude 40.07 degrees, true azimuth 135.34 degrees.

| Build | v15 camera position | Target | Lens | Door leaf |
|---|---|---|---:|---|
| `00b6933`, pre-C4 | (11.127, −25.971, 1.350) | (9.199, −23.673, 1.350) | 16 mm | retained |
| `be10734`, C4i | identical to pre-C4 | identical to pre-C4 | 16 mm | retained |
| `fb0ba91`, after WC/camera change | (10.327, −26.371, 1.350) | (9.301, −23.552, 1.350) | 16 mm | hidden for doorway view |

Thus C4i feeds v15 through finish geometry and corrected sconce mounting. The east-wall WC relocation and camera chooser changes feed it through changed obstruction/reflection geometry, a 0.894-metre camera move, changed aim, an opened doorway and addition of v35 to the day metering cohort. The lens change is a **diagnostic/framing algorithm change**, not a change in v15's actual focal length. Exposure presets are unchanged; adding a cohort member can affect its median meter lock. This comparison holds the saved current lock constant so it does not conflate that effect with transport.

| Exact archived build, diagnostic pixels at the same saved camera settings | Cast | Mean visible-marble linear RGB | Marble luminance |
|---|---:|---|---:|
| Pre-C4 `00b6933` | 0.113 warm | (187.961, 93.926, 36.965) | 109.805 |
| C4i `be10734` | 0.114 warm | (191.877, 95.601, 37.416) | 111.868 |
| Current reproduction | 0.114 warm | (212.176, 108.669, 44.554) | 126.046 |

C4i changes marble luminance by +1.88%, and changes cast by about 0.001 in this bounded diagnostic. It does not explain an onset of orange/dark marble. These are low-resolution diagnostic scores, not claimed production renders or independently re-metered historical sets. They reproduce the failure class on the exact archived builds. Separate retained pre-finish-solid renders also fail: job `8196ee87bd77256a05df0497` scores 0.103 and `7ca879c3159140f4fdf2bd71` scores 0.114. They have the same family-bath IES specifications, marble definition and exposure presets as the archived pre-C4 build, but lack commit provenance, so they are corroboration only.

## 2. What drives the appearance

### Texture and actual assignment

Measured all 2048 × 2048 albedo texels after decoding their sRGB encoding, and applied the actual shader's recorded channel factors and upper bound:

| Material definition | Texture | Raw mean linear RGB | Final shader mean linear RGB | Final mean reflectance |
|---|---|---|---|---:|
| `marble-bath` | Marble014 | (0.638005, 0.553927, 0.442887) | (0.654633, 0.617179, 0.542183) | 0.619727 |
| `marble-ensuite` | Marble020 | (0.446126, 0.367461, 0.305848) | (0.630528, 0.573267, 0.496807) | 0.579920 |

Zero texels clamp in either material. Builder sampling accounts for the sub-0.0003 difference from the stated mean reflectance. The family material is brighter and less warm than the named ensuite material: blue/red ratios 0.828 versus 0.788.

But **the visible marble in v12, v15 and v16 is the same `marble-bath` / Marble014 material**. The room finish map explicitly assigns it to all three bathrooms, including the comment that Marble020 read pink. The `marble-ensuite` definition remains available for other authored parts; the name alone cannot identify the wall finish. This assignment is also present pre-C4. Sources: [finish map](../src/archpipe/concept/villa_render.py), [actual texture shader](../src/archpipe/blender/villa_scene.py), and retained ray readback `out/v15-cast/pixel-readback.json`.

Specific warm v15 pixel hits, with coordinates measured from the image's top-left corner:

| Pixel | Actual first-hit mesh | Linear RGB |
|---|---|---|
| (10, 429) | `finish-layer-2-shell-021-marble-bath` | (287.220, 136.944, 51.147) |
| (690, 429) | `shell-021-marble-bath` | (193.956, 88.067, 29.687) |
| (950, 429) | `finish-layer-18-shell-021-marble-bath` | (132.081, 63.375, 23.819) |

The left finished wall's ray hit is at (9.300, −25.951, 1.158) metres. All three hits use `marble-bath`. A 20-pixel-spaced grid yields 860 direct marble hits in v15, averaging (210.121, 107.063, 44.472). Corresponding marble means are (59.040, 22.818, 4.728) in v12 and (78.771, 28.728, 5.528) in v16. The family bathroom receives **more** raw light; it looks darker because its camera gain is much lower. Glass and mirror first hits are identified separately; these samples are not assertions about reflected/transmitted secondary mesh identity.

### Lamp/daylight transport

Measured contributions over 13,988 pixels whose first visible surface is marble, preserving all saved authored meshes, shadows, materials, light spectra and dimmers. Light groups are switched only for the diagnostic. Each row includes that source group's indirect bounces and reflections:

| Contribution | Mean linear RGB on marble | Luminance | Share of full marble luminance |
|---|---|---:|---:|
| Full scene | (212.176, 108.669, 44.554) | 126.046 | 100% |
| Daylight only | (70.381, 54.278, 33.634) | 56.211 | 44.6% |
| All lamps only | (141.446, 54.219, 10.864) | 69.633 | 55.2% |
| Ambient downlight | (12.950, 4.607, 0.770) | 6.103 | 4.8% |
| Shower downlight | (37.933, 13.925, 2.478) | 18.202 | 14.4% |
| Basin downlight | (53.052, 20.228, 3.867) | 26.025 | 20.6% |
| Two family-bath sconces | (30.931, 13.360, 3.433) | 16.379 | 13.0% |
| Remaining lamps/visible emitters | (7.004, 2.257, 0.349) | 3.128 | 2.5% |

Daylight plus lamps reconstructs the full mean RGB within 0.162% vector-relative error; percentages need not sum to exactly 100% because the paths are independently sampled. The saved production EXR under the same mask averages (211.077, 107.385, 44.482), within 0.8% in luminance of the full diagnostic. The probes include all saved authored meshes but omit imported models, dressing, cloth and curtains; none is in the family bathroom. Small contributions through neighbouring rooms are therefore approximate. These are image-space transport shares, not task-plane lux or a new lighting-compliance verdict.

The lamp contribution's blue/red ratio is 0.0768; daylight's is 0.4779. The mixture stays warm under 5500 K white balance. With the saved camera unchanged, daylight-only diagnostic cast is 0.030; lamp-only is 0.186. Making only the marble albedo equal-channel in an isolated counterfactual, while preserving every texel's luminance, photographed variation, roughness and normal maps, yields cast 0.087 and blue/red ratio 0.2954, versus 0.114 and 0.2100 in the specified scene. Thus the cream material amplifies the warm light, but does not create it. These cast differences are **not additive causal percentages**: tone mapping and the mid-tone pixel selection are nonlinear. The neutral-material intervention is a measurement, not a proposed finish change. Its final measurement is in `contributions-neutral-tint.json`; the earlier uniform-albedo exploratory measurement retained in `contributions.json` is not used for this attribution.

### Metering and the passing WC view

The day lock is −10.33598 stops. v15's own meter proposed −9.68843, so the comparison lock gives it 0.648 stop less gain (factor 0.638). Its median display luminance 0.26 is already reported as a locked-exposure warning. The exposure scalar cannot change raw red/blue ratios, although tone mapping and mid-tone selection can change the display cast score. No exposure change is warranted to fix colour.

v35 has the same lights, materials, day camera preset and lock, but sees different surfaces and reflections. Its directly hit marble averages (176.284, 98.779, 47.694), with blue/red 0.271 versus v15's 0.212. Its passing 0.079 is consistent with this framing-dependent mixture; it does not prove that another angle must pass.

## 3. Recommendation and sources

**Keep the specified finish, lumens, fixture positions, CCTs, white balance, exposure and QA threshold.** The observed cast is a faithful consequence of the current design. A preference for a cooler daytime bathroom requires an explicit lighting/finish design decision, followed by product selection and fresh lighting proof. It is not justified as a rendering bug fix.

The product values were read from the held manufacturer EULUMDAT files, rather than inferred from appearance:

- [iGuzzini LSEVO-AAK3EW](../assets/user/luminaires/iguzzini/LSEVO-AAK3EW/LSEVO-AAK3EW.ldt): lamp-set CCT line 30 is `ww/2700`; lamp flux is 1110 lumens and luminaire output ratio is 66%, yielding 732.6 lumens.
- [iGuzzini LSEVO-AAIIA6](../assets/user/luminaires/iguzzini/LSEVO-AAIIA6/LSEVO-AAIIA6.ldt): line 30 also specifies 2700 K; 1460 lamp lumens at 92% output yields 1343.2 lumens.
- The [authored product choices](../src/archpipe/concept/villa_lighting.py) explicitly choose those 2700 K products. The unbound generic `DLN` fallback says 3000 K, but the bound manufacturer's product supplies 2700 K throughout both lighting and render consumers. This is longstanding explicit product selection, not a new renderer CCT substitution. The generic sconces retain their authored 3000 K / 450-lumen assumption.
- [ADR-0013](decisions/ADR-0013-presentation-renders.md) requires faithful lighting, per-channel material matching and exposure locked across comparisons. [The linear CCT conversion](../src/archpipe/blender/build_scene.py) uses the established unit-luminance blackbody calculation; the existing portable verification of that conversion passed.

No cause-level code defect was demonstrated, so no implementation, threshold change, guard or defect closure is claimed. The QA failure remains available to the lead for image/design review.

## Retained evidence and verification

Evidence in `out/v15-cast/`: three built scene snapshots; `evidence-manifest.json` with SHA-256 content hashes (Secure Hash Algorithm, 256-bit digests) of the original inputs/images and built snapshots; `pixel-readback.json`; `contributions.json`, `contributions-pre-c4.json`, `contributions-c4i.json`, `contributions-neutral-tint.json`; diagnostic EXRs; `developed-probe-metrics.json`; four production QA reports; scripts `read_pixels.py`, `contribution_probe.py`, `develop_probes.py`; execution logs. Temporary diagnostic pixel developments are under `/tmp/v15-cast-development`. The graphics probes acquire the existing workstation graphics lock without modifying its contents. No shared render data or assets were written.

Using the specified interpreter, `PYTHONPATH=src` and `NO_COLOR=1`:

```text
scripts/run_tests.py tests.test_render_qa tests.test_render_standard
  tests.test_villa_exposure_assets tests.test_mounting_finish_layers
  tests.test_sanitary_relocation
  -> exit 0; 99 tests, OK
scripts/verify.py --portable
  -> exit 0; RESULT: ALL PASS
```

Logs: `out/v15-cast/focused-tests.log` and `out/v15-cast/verify-portable.log`. No full suite, native-model rebuild, presentation render or commit was performed.
