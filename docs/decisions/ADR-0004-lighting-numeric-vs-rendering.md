# ADR-0004 — Lighting compliance is arithmetic, not rendering

- **Status:** accepted
- **Date:** 2026-09-20

## Context

The requirement is lighting checks, lumen verification, heat maps and a
"hotel-like" result. It was unclear whether this needed rendering.

## Decision

Treat illuminance and appearance as two different problems.

| Layer | Tool | Answers |
|---|---|---|
| Lux grids, uniformity, heat maps | Python, IES photometry, inverse-square + cosine | Is the worktop at 300-500 lux? |
| Layered-lighting design rules | Rule engine | Does this read as hotel, or as a bare bulb? |
| Accurate simulation with inter-reflection and daylight | Radiance, 32 cores | Can the numbers be defended? |
| Photoreal appearance | Blender Cycles, RTX 3090 | Does it feel right? |

## Consequences

- **Compliance needs no renderer.** The rule engine stays pure Python and
  runs anywhere, which keeps it fast and testable.
- Rendering is reserved for judging feel, where it is the only answer.
- The lux engine must be validated against a hand-calculable case
  (single fixture, known IES, known mounting height) before any heat map
  is trusted, then cross-checked against Radiance for one room.
- IES photometric files must come from real manufacturers. Invented
  photometry would make the heat maps confident and wrong.

## Alternatives rejected

- **Render everything and judge by eye** — no numbers, nothing checkable.
- **Revit/Insight cloud lighting analysis only** — consumes credits, and
  the entitlement under an education licence is uncertain.
