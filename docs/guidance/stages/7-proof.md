# 7 — Proof

This is a working stage package. Methods and examples are project-authored; published support is limited to the evidence cards linked below.

## Inputs and interview

Required: reviewed_revision, model, render_input, requirements, open_issues. Each fact records value, status and provenance; unknown is not an assumed pass.

- Does the arrival and evening atmosphere match the agreed direction?
- Which unresolved trade-off needs your decision?

## Method

1. Compare day/night views, measured model, plans, sections, interiors and landscape together. Show sightlines and routes that hero views can hide.
2. Bind render inputs and image files to the reviewed model and project revision using content hashes; rerun affected review after any change.
3. Trace every client requirement to an artifact; distinguish unresolved issues, rejected alternatives and accepted trade-offs. Presentation readiness does not authorize a real gate.

## Evidence

- `aia-phases`: [Defining the architect’s basic services](https://www.aia.org/resource-center/defining-the-architects-basic-services), section “Schematic design phase services; Design development phase services”, accessed 2026-09-24. Retrieve its scoped paraphrase with `lookup_evidence`.
- `norm-copenhagen`: [1 Hotel Copenhagen](https://normcph.com/project/1-hotel-copenhagen/), section “Project introduction and arrival description, before first image”, accessed 2026-09-24. Retrieve its scoped paraphrase with `lookup_evidence`.

## Worked example

Pilot pavilion can look convincing in a garden view while its graph fails private access. Bedroom presentation must match its measured extract and rendering-input hashes; replacing an image or changing a model invalidates the binding. See [pilot diagrams](../pilot-concepts.svg) and [bedroom exercise](../bedroom-worked-example.md).

## Checks and failures

- Measured geometry and source-validated targets where available; otherwise unresolved
- Failure: beautiful image suppresses unresolved glare. Remedy: include the issue in the presentation and keep approval readiness closed.
- Failure: cached review survives a changed source edition. Remedy: invalidate evidence-dependent review and recheck applicability.

## Deliverables and approval

Deliver: coordinated_presentation, requirements_trace, open_issue_log.

- Plans sections renders and schedules describe one revision
- Every priority requirement has a design response
- Independent critique and unresolved issues visible
- Client approval explicitly recorded

Record reviewer, current revision, outcome and reasons for every qualitative criterion. Present the recommendation, household reason, visual explanation, evidence and cost/space/maintenance consequences. Request the client’s explicit decision only on a concrete reviewed proposal. Unresolved evidence or missing facts keep the gate open.
