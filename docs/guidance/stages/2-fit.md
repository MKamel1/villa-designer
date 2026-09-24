# 2 — Fit

This is a working stage package. Methods and examples are project-authored; published support is limited to the evidence cards linked below.

## Inputs and interview

Required: area_schedule, budget, available_area, outdoor_priorities. Each fact records value, status and provenance; unknown is not an assumed pass.

- Would you give up a second lounge to keep a larger garden?
- Does the budget include furniture, landscape and professional fees?

## Method

1. Schedule individual usable room areas, then separately add circulation, walls, structural zones and service space without double counting.
2. Compare totals and each storey footprint with supplied physical constraints; statutory inputs, if supplied, remain externally established.
3. Show cost scenarios with currency, date, rate provenance, exclusions and contingency. Without rates report cost unresolved; never invent a local estimate.

## Evidence

- `aia-phases`: [Defining the architect’s basic services](https://www.aia.org/resource-center/defining-the-architects-basic-services), section “Schematic design phase services; Design development phase services”, accessed 2026-09-24. Retrieve its scoped paraphrase with `lookup_evidence`.
- `yourhome-cost`: [Affordability](https://www.yourhome.gov.au/buy-build-renovate/affordability), section “Key points; Costs and savings of sustainability features”, accessed 2026-09-24. Retrieve its scoped paraphrase with `lookup_evidence`.

## Worked example

Pilot usable rooms total 272 square metres. Circulation 40, walls 32, structural zones 12 and services 14 give 370 square metres against a 400 square metre scenario allowance. These allowances are project assumptions; no net-to-gross benchmark is asserted. See [pilot diagrams](../pilot-concepts.svg) and [bedroom exercise](../bedroom-worked-example.md).

## Checks and failures

- Area arithmetic with explicit project assumptions
- Failure: gross area passes but ground-floor rooms exceed the footprint. Remedy: reconcile each level and reopen Order.
- Failure: beautiful courtyard consumes circulation allowance. Remedy: recalculate and present a brief trade-off.

## Deliverables and approval

Deliver: area_schedule, cost_assumptions, tradeoffs.

- Net and gross areas reconciled
- Cost assumptions and exclusions explicit
- Outdoor and service space retained

Record reviewer, current revision, outcome and reasons for every qualitative criterion. Present the recommendation, household reason, visual explanation, evidence and cost/space/maintenance consequences. Request the client’s explicit decision only on a concrete reviewed proposal. Unresolved evidence or missing facts keep the gate open.
