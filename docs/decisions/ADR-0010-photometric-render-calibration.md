# ADR-0010 — Photometric calibration of the Cycles render

- **Status:** accepted
- **Date:** 2026-09-22
- **Relates to:** ADR-0004 (compliance calculated, not rendered), ADR-0009
  (no uniformity verdict from direct light)

## Context

The client's requirement, in their words: *"for lighting try to stay
faithful and accurate and precise as much as possible — the whole reason
for the lighting is that we want a faithful representation of lighting as
we render."*

That reframes the lighting work. `archpipe.lighting` is not the
deliverable; it is the **instrument that proves the render is right**.

The bridge did not meet the requirement. It set

```python
light.energy = float(fx.get("watts") or 60) * 10.0
```

A bare point light with a magic factor of ten and no photometric
distribution at all. The resulting image was a picture of *a* lighting
scheme, not *the* one.

## What was measured

Nothing here is taken from documentation or a forum post; Blender's
conventions have changed between releases, and every one of these facts
was established against a case with a closed-form answer.
`src/archpipe/blender/calibrate_photometry.py` reproduces all of it.

**1. Blender's light "Watts" are photometrically usable.** For a point
light of power P at distance d, measured E = P/(4πd²) to within 0.016%.
Linearity in power was exactly 2.000000; inverse-square gave 0.250029
against 0.25.

**2. The IES node does NOT normalise by flux.** This is the trap. Three
synthetic probes settled it:

| Probe | Node output at nadir | Conclusion |
|---|---|---|
| isotropic 1000 cd | 76.583 | — |
| isotropic 500 cd | 38.292 | exactly ½ → raw candela |
| hemisphere 1000 cd (half the flux) | 76.585 | unchanged → flux irrelevant |

So `Fac(θ) = I_raw(θ) / C` with a universal constant. Had Blender
normalised by flux, a wide fitting and a narrow one of equal lumens would
render at the same brightness — silently wrong in every scene.

**3. The constant, and therefore the power.** Since

    E_rendered = P·I(θ)/(C·4πd²)   and   E_true = I(θ)/d²

the correct power is `P = 4πC`, the same for every fitting whatever its
distribution. Fitted across the full angular range rather than at nadir:

    IES_POINT_POWER = 162.624

**4. Validation across the beam.** Nadir agreement proves little, since
the constant was fitted there. Measured at nine radial offsets against
`archpipe.lighting`, which is itself checked against hand calculation:

| | Agreement |
|---|---|
| isotropic control, 2.9°–51° | **±0.02%** |
| real pendant, where light is significant | ±0.5% |
| exactly at nadir | −0.9% |
| beam far tail | large %, **< 0.1 lx absolute** |

The nadir dip is Blender's IES lookup degenerating at the pole, where
azimuth is undefined. One direction out of a hemisphere; not worth
correcting, worth knowing.

## Three errors this found

Calibration is only useful if it catches things. It caught three, none of
which would have raised an exception.

**The measuring surface was not Lambertian.** `L = E·ρ/π` describes a
Lambertian reflector. Blender 4.x's Principled BSDF at roughness 1 adds a
diffuse retro-reflection term, and readings came back exactly right at
normal incidence and a flat 0.92% high from 7° to 45°. Replaced with a
pure Diffuse BSDF.

**Illuminance was read as the mean of RGB, not luminance.** Illuminance
weights the spectrum by the eye's response, which in an RGB renderer is
the Rec. 709 luminance. With the arithmetic mean a 2700 K lamp reads 5.6%
low and a neutral lamp reads correctly — so the error is *invisible*
during calibration with white light and appears only once colour
temperature is set. It showed as a flat 0.951 ratio across a whole room.
Fixing it moved the median agreement from 0.951 to **1.0065**.

**The rooms had no ceiling.** `build_scene.py` built walls and floors and
nothing overhead, so every ray leaving a fitting upward escaped. Adding
16 bounces raised average illuminance by 9.6 lx without a ceiling and
22.6 lx with one. A downlight scheme sends most of its first bounce to
the floor; the ceiling is what returns light to the upper half of the
room.

## And one in the analytical engine

The render disagreed with `interreflected_estimate` by a factor of about
1.7, and the render was right.

`Photometry.total_lumens` is `lamps × lumens_per_lamp` — the flux the
**lamps** produce. What leaves the fitting is less, because reflectors,
lenses and shades absorb. Integrating the measured distribution:

| Fitting | Declared | Emitted | Efficiency |
|---|---|---|---|
| PLD1A21 lensed pendant | 2780 lm | 1758 lm | 63% |
| EWL2A19 lamphead | 780 lm | 503 lm | 64% |
| LGLled narrow LED | 1008 lm | 390 lm | 39% |
| **scheme total** | **5348 lm** | **3154 lm** | **59%** |

`Photometry.integrated_flux()` now provides the emitted figure and
`interreflected_estimate` uses it. The estimate moved from 40–68 lx to
24–40 lx against a measured 22.6 lx — consistent, the render landing just
below because 4 m² of window and door let light escape a 72 m² envelope.

Point-by-point illuminance was never affected: it reads candela directly.

## Decision

1. IES profiles are loaded into Cycles via `ShaderNodeTexIES`, at
   `IES_POINT_POWER = 162.624`, so **rendered illuminance is numerically
   lux**.
2. Cycles settings are chosen for energy conservation, not for a pretty
   frame: indirect clamping **off** (it discards exactly the bounced light
   an interior depends on), diffuse bounces raised, denoising off in
   measurement mode.
3. Room surfaces carry **stated photometric reflectances** — ceiling 0.80,
   walls 0.60, floor 0.25 — set through `surface()`, which scales a tint
   to hit the target luminance so choosing a colour cannot quietly change
   the lighting.
4. Colour temperature tints a light **without changing its output**;
   `kelvin_to_rgb` renormalises to unit luminance.
5. `measure_lux.py` turns a render into a lux grid, using a probe plane
   invisible to every ray except the camera's, so it measures without
   perturbing what it measures.
6. Display exposure is a **camera setting, computed** —
   `exposure = log2(π / target_lux)`, about −6 stops at 200 lx. Without
   it a physically correct interior renders pure white, because scene
   values are lux where the display pipeline expects 0–1. Measurement
   mode forces exposure 0 and the Standard transform, so this can never
   touch a number.

## Consequence for ADR-0009

ADR-0009 said a real EN 12464-1 U0 must wait for Radiance, because it
needs total illuminance including inter-reflection.

**Cycles now supplies that.** `measure_lux.py --bounces 16` measures total
illuminance directly; `--bounces 0` reproduces the direct component and
agrees with the analytical engine, which is what makes the total
trustworthy. Radiance is no longer on the critical path.

ADR-0009's decision still stands as written: the *analytical* engine must
not adjudicate uniformity, and `uniformity_direct` keeps its name. What
changes is that a uniformity verdict is now reachable — from a measured
render, on a quantity that is actually defined — and a Stage 5 rule for it
can be written against `measure_lux` output rather than waiting.

## Reproducing

```bash
# the two Blender-side facts
blender -b -P src/archpipe/blender/calibrate_photometry.py -- --ies f.ies

# agreement across the beam
blender -b -P src/archpipe/blender/validate_render_photometry.py -- \
    --ies f.ies --height 2.0

# a room, both ways
blender -b -P src/archpipe/blender/measure_lux.py -- \
    --extract bedroom.json --out lux_direct.json --bounces 0
python scripts/compare_lux.py out/lux_direct.json
```

A full-GI lux grid of the mock bedroom at 192×192 and 2048 samples takes
**3.6 s** on the RTX 3090.

## Addendum (2026-09-22) — three faults the first real room exposed

The calibration above was done entirely on **axially symmetric** probes:
every synthetic file had a single horizontal plane, and the one real
fitting used (PLD1A21) has one too. Running the first Revit-built room
through the same comparison dropped agreement from 1.0065 to **0.80**, and
the causes were three separate bugs, none of which raised anything.

**1. Blender's IES azimuth zero is 90 degrees from LM-63's.** Measured on
`LGLled.ies`, a linear fitting with 19 horizontal planes and real
asymmetry — 167 cd at plane 0 against 681 cd at plane 90 for the same
vertical angle:

| light rotation about Z | rendered at r=0.5 m | analytic at phi=0 |
|---|---|---|
| 0 | 223.4 lx | 60.1 lx |
| **+90** | **57.8 lx** | 60.1 lx |

`IES_AZIMUTH_OFFSET_DEG = 90` is now applied to every IES light, on top of
the fitting's own rotation carried from Revit. Invisible on a symmetric
pendant, a factor of four on a linear one, pointed the wrong way.

**2. Luminous size taken from the family's bounding box.** The extract
reported `luminous_size_mm` from the Revit family's extents — 1219 mm for
a fitting whose IES declares a 594 x 24 x 3 mm luminous opening. Blender
models a point light's size as a sphere of that radius, so a thin strip
became a 0.61 m ball and the rendered peak beneath it fell to 41% of the
calculated value. `make_render_input.py` now reads the opening from the
IES file. The smallest dimension is used, deliberately: a sphere of the
largest would be a bigger source than the fitting is on two of three axes
and would wash out the distribution the file describes. The cost is
slightly sharp shadow penumbrae from linear fittings — a softness
artefact, not an illuminance error.

**3. `build_scene` read `size` where the Revit extract writes `size_mm`.**
Every furniture proxy silently rendered at the 600 x 600 default.

### Agreement after the fixes, on the real model

| | before | after |
|---|---|---|
| mean absolute difference | 52.67 lx | **8.11 lx** (1.27% of peak) |
| median ratio, all points | 0.829 | **0.968** |
| median ratio, clear of furniture | 0.800 | **0.9964** |
| spread | 0.18–3.58 | 0.91–1.05 |

### Two limits now measured rather than assumed

- **Quadrant-symmetric files read ~8% low in Blender.** A synthetic
  isotropic source declared with 5 horizontal planes rendered 229.6 lx
  where the identical source with one plane rendered 247.8 and the true
  answer is 250. Not compensated for, because silently scaling a renderer
  to match a calculation would destroy the independence that makes the
  comparison worth anything.
- **An empty or malformed IES file does not fail.** Blender renders it
  with a fallback distribution and says nothing. `make_render_input.py`
  checks the file parses before writing the path.

The analytical engine models **no occlusion**, so in a furnished room the
two must disagree wherever something is in the way; `compare_lux.py` now
separates clear points from shadowed ones and reports both.
