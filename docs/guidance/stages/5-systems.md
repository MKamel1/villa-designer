# 5 — Systems

This is a working stage package. Methods and examples are project-authored; published support is limited to the evidence cards linked below.

## Inputs and interview

Required: comfort_targets, equipment, service_routes, controls, model. Each fact records value, status and provenance; unknown is not an assumed pass.

- Do you read in bed while someone else sleeps?
- Which sounds or temperatures disturb you?

## Method

1. Make a room-by-room schedule for daylight, glare, blackout, sound, temperature, ventilation, sockets, water and controls; name unresolved targets.
2. Overlay luminaires, grilles, detectors, curtains, beams, ducts and access panels on the reflected ceiling plan and a service section.
3. Use existing direct-light arithmetic for diagnostic points. Total-light uniformity, glare, ventilation and thermal predictions require their appropriate methods and verified targets.

## Evidence

- `yourhome-light`: [Lighting](https://www.yourhome.gov.au/energy/lighting), section “Key points”, accessed 2026-09-24. Retrieve its scoped paraphrase with `lookup_evidence`.
- `yourhome-shading`: [Shading](https://www.yourhome.gov.au/passive-design/shading), section “Key points”, accessed 2026-09-24. Retrieve its scoped paraphrase with `lookup_evidence`.
- `yourhome-noise`: [Noise control](https://www.yourhome.gov.au/live-adapt/noise-control), section “Key points”, accessed 2026-09-24. Retrieve its scoped paraphrase with `lookup_evidence`.
- `aia-phases`: [Defining the architect’s basic services](https://www.aia.org/resource-center/defining-the-architects-basic-services), section “Schematic design phase services; Design development phase services”, accessed 2026-09-24. Retrieve its scoped paraphrase with `lookup_evidence`.

## Worked example

Bedroom reader wants a separately controlled bedside task light and a dark sleeping scene. Existing photometric workflow can measure direct light; it cannot prove acoustic privacy or thermal comfort. A duct through the headboard bulkhead triggers a section and noise review. See [pilot diagrams](../pilot-concepts.svg) and [bedroom exercise](../bedroom-worked-example.md).

## Checks and failures

- Measured geometry and source-validated targets where available; otherwise unresolved
- Failure: bright image treated as adequate lighting. Remedy: calculate the defined task plane and explain missing bounce/shadows.
- Failure: ceiling conceals inaccessible equipment. Remedy: show removal path and access panel; reopen Rooms for lost height.

## Deliverables and approval

Deliver: comfort_schedule, coordinated_ceiling, service_access.

- Daylight glare blackout and scenes reviewed
- Cooling ventilation acoustics power water coordinated
- Equipment maintenance access shown
- Measured light distinguished from comfort targets

Record reviewer, current revision, outcome and reasons for every qualitative criterion. Present the recommendation, household reason, visual explanation, evidence and cost/space/maintenance consequences. Request the client’s explicit decision only on a concrete reviewed proposal. Unresolved evidence or missing facts keep the gate open.
