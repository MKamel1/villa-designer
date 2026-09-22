# ADR-0002 — The text model is a generated extract, never authored

- **Status:** accepted
- **Date:** 2026-09-20

## Context

With Revit as the authored artifact (ADR-0001), the text model still has
three jobs nothing else does:

1. **It is how the AI sees the design.** The agent cannot open Revit and
   look; it reads the text.
2. **It is what the rule engine checks.**
3. **It is what makes review possible.** A text diff says "Bedroom 2 lost
   1.2 m2, window WD-03 moved 400 mm". A .rvt file is a binary blob that
   neither party can diff.

The risk is drift: if both the Revit model and the text can be edited,
they disagree and nobody knows which is right.

## Decision

The text model is **generated from Revit and never hand-edited**. It is a
derived artifact, like a compiled output, committed to git for history.

## Consequences

- Drift is structurally impossible: only one artifact is authored.
- Full readability, diffability and traceability are preserved.
- The agent can read the design without a Revit session running.
- The export must be **deterministic** — same model in, byte-identical
  file out — or every export is a noisy diff and the benefit is lost.
  Everything is sorted by stable id.
- Everything already built on the schema (rule engine, furniture
  catalogue, web viewer, coordinate transform) keeps working unchanged.

## Alternatives rejected

- **Bidirectional sync** — the classic two-sources-of-truth trap.
- **Drop the text model, read Revit directly** — ties every check to a
  running Revit session and destroys reviewability by diff.
