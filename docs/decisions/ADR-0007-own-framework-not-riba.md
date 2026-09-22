# ADR-0007 — A project-specific design method instead of RIBA

- **Status:** accepted
- **Date:** 2026-09-20

## Context

RIBA Plan of Work 2020 was adopted as the process backbone and rejected
on review as a poor fit for a private villa.

## Decision

Define the project's own **Villa Design Method** (`docs/method/`), keeping
RIBA's staged gates and discarding the rest.

## Reasoning

- RIBA is a **procurement framework** — it defines when information passes
  between parties and who is liable. With one client and no tender, that
  machinery is dead weight.
- It is **deliberately silent on how to design**. Its Stage 2 outcome is
  "Architectural Concept approved"; arriving at a good concept is left to
  the designer. That is the part this project needs.
- It **forbids the iteration a house needs**: "Stage 3 is not about
  adjusting the Architectural Concept." Correct for a large commercial
  job, wrong where cheap iteration before commitment is the whole value.
- It has nothing on domestic life, climate-first design, or experience.

## Consequences

- Eight decision-led stages with quality gates, thirteen named backward
  loops (L1-L13), and four thrash-control mechanisms.
- **Risk: a bespoke framework can drift into being unaccountable.**
  Mitigation: the framework is ours, the standards never are. Every rule
  cites Alexander by pattern number, Neufert by figure, or a code clause.
- Alexander's patterns are qualitative by design, so each rule is
  classified `computed` or `advisory`; advisory findings are never
  reported as measurements.

## Alternatives considered

- **Stay with RIBA** — rejected for the reasons above.
- **Pattern Language alone** — rich in design intelligence, but it is a
  catalogue, not a process: no sequencing and no gates.
- **Bioclimatic method alone** — strong on climate and orientation,
  silent on everything social.
