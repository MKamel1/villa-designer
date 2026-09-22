# ADR-0001 — Revit is the single source of truth

- **Status:** accepted
- **Date:** 2026-09-20

## Context

The project began with a YAML file as the authored design, rendered to
DXF/DWG by Python. That gave determinism, text diffs and headless
regeneration, but produced only 2D and no BIM data.

The client wants BIM: coordinated 3D, schedules, sections and elevations
derived rather than drawn, and MEP/lighting integration.

## Decision

Revit becomes the single authored artifact. All design and editing happen
in Revit.

## Consequences

**Gained:** real BIM; native families and types; sections, elevations and
schedules generated from one model; a path to MEP and lighting
coordination; an industry-standard deliverable.

**Lost:** headless regeneration. Revit has no `revitcoreconsole`; there is
no supported way to drive it without a session. Iteration slows and CI on
the model becomes impractical. Accepted deliberately.

**Required:** Revit installed (~30 GB) and licensed; pyRevit for
scripting; Windows, since Revit has no Linux build.

## Alternatives rejected

- **Keep YAML as the authored source and generate Revit from it** —
  preserves determinism, but any edit made inside Revit is destroyed on
  the next regeneration. Rejected as unworkable in practice.
- **AutoCAD only** — no BIM, no schedules, no coordination.
- **IFC via IfcOpenShell** — free and Linux-native, but an imported IFC
  arrives in Revit as generic geometry, not native parametric elements.
