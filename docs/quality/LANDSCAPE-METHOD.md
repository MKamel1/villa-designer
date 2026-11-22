# Landscape method: designing the D1 garden without a professional

Lead plan, 2026-11-21. Status: **proposed. Needs the client's yes (new capability) and the garden-use brief.**

## Why

The current garden was never designed as a landscape. `concept/villa_landscape.py` places plants and blocks one at a time as fixed points. The G1–G6 garden lanes fixed render defects (floating trees, shade, cameras) and never asked what the garden is for or how it is structured. Client, 2026-11-21: "the layout, the blocks and plants distribution does not look like a landscape."

## Target, and what "no professional needed" means here

A professional does three things: knows the rules and good practice, invents a coherent scheme, and judges quality. The AI is strong as a critic and weak as an inventor (CLAUDE.md). So the method replaces the professional with three things, and each one is measured:

1. **Codified knowledge.** Every rule cites a held source. Every plant fact cites a source.
2. **Constrained invention.** Schemes are composed from patterns and precedent statistics, many candidates are generated and checks filter them, and nothing is free-drawn.
3. **Calibrated judgement.** Critics that are proven to fail the current garden (known bad) and to pass professional precedents (known good) before their verdicts count.

Acceptance (all required):

| # | Test | Bar |
|---|---|---|
| A1 | Traceability: every element of the plan traces to a use in the brief, a sourced rule or a client decision | 100 %; anything untraced is removed |
| A2 | Hard checks (dimensions, mature spread vs space, tree-to-foundation distance, summer shade cover of the use areas, hydrozones, toxicity near play, sightlines and privacy) | 0 fails; achieved-versus-required reported |
| A3 | Critic calibration before use: the current D1 garden must fail; at least 8 published professional gardens must pass | recall ≥ 90 % on known bad, false-fail ≤ 10 % on known good |
| A4 | Blind plan test: our plan against professional plans of similar size and climate, drawn in the same style, judged by critics that don't know which is ours | not identified as weakest more often than chance |
| A5 | Blind render test: garden views against studio photographs of real gardens | as for L9 |
| A6 | Client gates: brief, concept choice and final plan | explicit yes (silence is not approval) |

**Limits (stated now, not discovered later):** these items stay with a licensed party or a site fact and are not claimed by the method:
- the structural design of retaining walls over about 0.6 m;
- soil and drainage tests;
- irrigation hydraulics (we give hydrozones and demand only);
- nursery availability in Egypt, which needs a supplier list or a phone check;
- tree roots against the existing structure where the depth of the foundations is unknown.

## Sources (held)

- Harris & Dines, *Time-Saver Standards for Landscape Architecture* (2nd ed.) with its dry-climate planting guide: dimensions, grading, hardscape, planting and irrigation data.
- *Site Analysis*: a checklist for the inventory and analysis stage.
- Alexander, *A Pattern Language*, including the outdoor-room, tree-place, garden-seat and garden-growing-wild patterns. These are advisory only and carry no measurement.
- BR 209, for sunlight to outdoor areas.
- The project's own measured sun and shade (`garden_sun.py`, `garden_shade.py`) and the plot, levels and neighbours in `villa_env`.
- Client standing decisions: shade over sun; any beautiful, shading, site-viable plant (not only Mediterranean); colourful drifts; artificial grass; frangipani; terracotta pots.

Precedents (lane LD-P): 20–30 published residential gardens of similar size and a hot-dry climate, for analysis only. Their geometry is measured into statistics and never copied or rendered.

## Stages and lanes

```
LD0 brief (lead + client)
   │
   ├── LD-S site analysis ──┐
   ├── LD-K rules codified ─┤   (parallel, ~0.5 day)
   ├── LD-L plant library ──┤
   └── LD-P precedents ─────┘
              │
        LD-C critics calibrated (needs LD-K, LD-P)
              │
        LD-G generate → check → critique  (~0.5 day)
              │
        client picks 1 of 2–3 concept plans  ← gate
              │
        LD-D detailed design + drawings
              │
        LD-B build in scene → render → critic gate → blind test
```

**LD0 brief.** Uses and who uses them (children, guests, quiet sitting, food, water, service), what must be seen and screened, maintenance appetite and the water budget. Recorded as a client decision.

**LD-S site analysis.** Plot and levels, measured sun hours per square metre (summer and winter), wind, views out and overlooking in (neighbours and the apartment above), access and services, and fixed structure. Output: constraint layers in JSON plus a plan diagram. Check: coverage of the *Site Analysis* checklist; every layer measured from the model, none assumed.

**LD-K rules.** Extract the rules into `rules.Rule` objects with citations, with positive and negative tests for each. Quantitative rules include path and step widths, terrace area per seated person, outdoor riser and going, planting spacing at maturity, distance from tree to building, and shade-tree placement for summer sun. Compositional rules (enclosure, framing, focal points, rhythm and repetition, layering) are advisory, or are checked through the precedent statistics where those give a number.

**LD-L plant library.** Per species: mature height and spread; sun and water need; heat, salt and frost tolerance for the site; flowering season and colour; toxicity; root behaviour; growth rate; and the quality grade of its 3D asset. Each attribute is sourced. Only plants viable on the site are accepted, and a species without an asset of grade B or better is not drawable.

**LD-P precedents.** Measure the published gardens: the share of hard and soft surface, the number and size of outdoor rooms, path hierarchy, tree count per 100 m², group (drift) sizes, layer proportions, and the number of species against the area. This turns "looks like a landscape" into target ranges.

**LD-C critics.** These are independent agents that never see the generator's rationale. They are calibrated (A3) before any verdict counts:
- a landscape-architect critic (space and composition);
- a horticulturist critic (plant fit, layers, seasons, maintenance);
- a user critic (walks each use in the brief);
- a climate critic (shade and water).

They reuse the L3 critic machinery for renders and plan images.

**LD-G generation.** First zoning diagrams, then structure (rooms, paths, edges, levels, trees), then planting (layers and drifts). Candidates come from pattern rules within the precedent ranges, many of them. The hard checks (A2) filter them, the critics rank the survivors, and the generator revises only on named findings. Output: 2–3 distinct concepts with a recommendation, the cost of each, and what was rejected. These go to the client gate.

**LD-D detailed design.**
- A planting plan with species and counts.
- Hardscape and levels.
- Hydrozones.
- Garden lighting handed to the lighting lanes (L6).
- A plan and two sections through `drawings2d`.
- A schedule of quantities (no prices).

**LD-B build and render.**
- Build the plan into the scene by element id. Plants are shown at a stated age (for example three years) and labelled. Nothing floats.
- The asset quality gate rejects faceting, card leaves and low polycount.
- Garden views go through the L3 critic gate, then the A4 and A5 blind tests. A view that fails goes back to the stage that caused it, not to the camera.

## Guards left behind

- The current garden must fail A2 and A3. This proves the checks catch the real defect, not a synthetic one.
- Each rule has a negative test.
- The precedent ranges are frozen before generation, so they cannot be tuned to pass our own plan.
- Blind tests pre-register the pairs and the judging prompt.

## Effort

About 0.5 day for the parallel analysis lanes, 0.5 day for critics and generation, then the client gate. After the choice, 1–2 days for detail, build and render. The GPU is shared with L9. The garden views render in the L9 set and the walkthrough, which wait for LD-B.
