# ADR-0009 — No uniformity verdict from a direct-light calculation

- **Status:** accepted
- **Date:** 2026-09-22
- **Relates to:** ADR-0004 (lighting compliance is calculated, not rendered)

## Context

Stage 5 needs to judge lighting. `src/archpipe/lighting.py` computes
point-by-point illuminance from measured IES photometry using the
inverse-square cosine law. It models the **direct** component only:
light arriving at the working plane straight from a luminaire, with no
inter-reflection between room surfaces.

The obvious metric to reach for is EN 12464-1's overall uniformity,
`U0 = Emin / Eavg`, with the usual threshold of 0.40. The first
implementation computed exactly that and it looked reasonable in a
synthetic test with an isotropic source.

On the mock bedroom with real fittings it returned **0.00**, and the
reason turned out to be structural rather than a bug.

### What the measurement showed

The specified scheme is a lensed pendant, two bedside lamps and a
wardrobe strip — all directional. The pendant emits **0 cd beyond about
60°**, which is not a defect; a lensed downlight is supposed to control
its beam. The far corner of the room therefore receives, by direct
light, either nothing at all or almost nothing:

| | |
|---|---|
| Emin, direct | **0.33 lx** |
| Eavg, direct | 152 lx |
| Emin/Eavg | 0.002 |
| Estimated inter-reflected component at that corner | **32–54 lx** |

The unmodelled term at the point that sets the metric is roughly **100×
the modelled one**. The corner is not dark; it is lit almost entirely by
light bouncing off the walls and ceiling, which this engine does not
compute.

Gating on "did the sample receive any direct light at all" does not
rescue it. 0.33 lx passes that test and is still swamped.

### Why the missing term cannot simply be added

The classical inter-reflected component,
`E_ir = F·ρ / (A·(1 − ρ))`, assumes first-bounce flux lands on surfaces
in proportion to their **area**. A downlight scheme violates that: most
flux goes to the floor, the lowest-reflectance surface, while the
area-weighted figure credits the ceiling with intercepting its area
share. Both treatments were computed for the mock bedroom:

| First-bounce weighting | Inter-reflected estimate |
|---|---|
| By surface area (ρ = 0.48) | 68 lx |
| Towards the floor, as a downlight behaves (ρ = 0.25–0.32) | 36–45 lx |

A factor of **1.9 on the term that would dominate the metric**. A
uniformity figure resting on that cannot carry a pass/fail with a
measurement attached — which discipline 3 in `CLAUDE.md` requires of
every non-advisory finding.

## Decision

**A direct-light calculation does not produce a uniformity verdict, and
does not expose a property named `uniformity`.**

1. The ratio is available as `LuxGrid.uniformity_direct`, named so the
   caveat travels to the call site. `summary()` prints it labelled
   `Emin/Eavg(direct only, NOT U0)`.
2. No Stage 5 rule adjudicates it. `scripts/verify.py` asserts the bare
   names are absent, so reintroducing one fails the suite.
3. `interreflected_estimate()` returns a **range**, never a single
   number, and its own note says it is not a basis for a uniformity
   verdict.
4. Stage 5 rules are built on what the calculation does support:
   - **average illuminance** over the room
   - **illuminance at named task points** — bedside, desk; the task
     fitting is close and aimed, so the direct component dominates and
     the missing term is a small conservative correction
   - **layer count** — pure topology, no photometric uncertainty
   - **installed power density** — arithmetic, given a stated wattage

## Alternatives rejected

**Return `0.00` and let the rule fire.** Rejected: it reports a
catastrophic violation where the truth is that the engine cannot say.
This is the exact failure discipline 4 exists to prevent.

**Return `None` when a sample is unlit.** Considered and implemented
first. Rejected after measurement: the threshold is arbitrary, and 0.33
lx passes "is it lit" while being 100× smaller than the unmodelled term.
Naming the quantity honestly is a stronger guard than a number that
would need defending.

**Add the inter-reflected component and compute U0 on the total.**
Rejected: the 1.9× spread above. It would convert an obviously-wrong
0.00 into a plausibly-wrong 0.43, which is worse — the first invites
investigation, the second gets quoted.

## Consequences

- A real U0 waits for **Radiance**, which models inter-reflection.
  Already noted as a source build in
  `docs/ops/workstation-changes.md`; this ADR is the reason it matters
  rather than a nice-to-have.
- Until then, lighting findings say what they measured and stay silent
  on uniformity. The heat map still shows the distribution, so a gloomy
  corner remains **visible** — it is simply not adjudicated.
- A related trap is recorded in the same module: the IES files Revit
  ships are legacy incandescent and T12 photometry at 16–35 lm/W. Their
  **distributions** are reusable and are what we use; their **wattages**
  describe lamps nobody would specify. `Luminaire.watts` must therefore
  be stated explicitly, and power density is unreported until it is,
  rather than defaulting to a figure that would fail every scheme.
