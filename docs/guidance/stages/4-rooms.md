# 4 — Rooms

This is a working stage package. Methods and examples are project-authored; published support is limited to the evidence cards linked below.

## Inputs and interview

Required: furniture, openings, room_activities, accessibility, model. Each fact records value, status and provenance; unknown is not an assumed pass.

- Where do you put luggage, laundry and devices?
- Can one person dress while another sleeps?

## Method

1. Use measured geometry for room boundaries and actual furniture sizes; show doors, drawers, chair use, luggage and bed-making routes.
2. Resolve kitchens, bathrooms, dressing rooms and storage in plan and elevation; draw ceiling heights, reveals and shading in section.
3. Report achieved geometry separately from unverified access targets; verify the source passage before turning a diagnostic into a required minimum.

## Evidence

- `aia-phases`: [Defining the architect’s basic services](https://www.aia.org/resource-center/defining-the-architects-basic-services), section “Schematic design phase services; Design development phase services”, accessed 2026-09-24. Retrieve its scoped paraphrase with `lookup_evidence`.
- `yourhome-light`: [Lighting](https://www.yourhome.gov.au/energy/lighting), section “Key points”, accessed 2026-09-24. Retrieve its scoped paraphrase with `lookup_evidence`.
- `yourhome-noise`: [Noise control](https://www.yourhome.gov.au/live-adapt/noise-control), section “Key points”, accessed 2026-09-24. Retrieve its scoped paraphrase with `lookup_evidence`.

## Worked example

Bedroom fixture contains six furniture objects. Review keeps the unknown chair as an obstacle. Moving a bedside table onto the bed must expose a physical clash even when it is marked as a bed accessory. Existing access thresholds remain unverified. See [pilot diagrams](../pilot-concepts.svg) and [bedroom exercise](../bedroom-worked-example.md).

## Checks and failures

- Measured geometry and source-validated targets where available; otherwise unresolved
- Failure: replacing measured furniture by catalogue sizes. Remedy: retain extracted footprints and inspect disagreement.
- Failure: plan fits but curtains collide with a wardrobe. Remedy: review opening and joinery elevations; return to Order if wall length changes.

## Deliverables and approval

Deliver: dimensioned_rooms, furniture_access, opening_schedule.

- Daily activities and furniture access tested
- Doors curtains and storage coordinate
- Interior and exterior dimensions reconcile

Record reviewer, current revision, outcome and reasons for every qualitative criterion. Present the recommendation, household reason, visual explanation, evidence and cost/space/maintenance consequences. Request the client’s explicit decision only on a concrete reviewed proposal. Unresolved evidence or missing facts keep the gate open.
