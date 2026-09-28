# ADR-0014 — D1 study windows and parents' dressing door

- **Status:** accepted client direction, pending Revit reconciliation
- **Date:** 2026-09-27
- **Applies to:** D1 concept and authored Revit specification. The study windows were also changed in D2 and D3 (the same study): pending the client's confirmation for those options.

## Context

The north study window was a 2.4 m wide high strip with a 1.7 m sill and a 2.3 m head. The high sill came from the parking/deck privacy adjustment in `revit_spec._parking`, which raised ground-floor windows beside the ramp and deck above a standing viewer's eye. The west study window already had a 0.9 m sill and 2.3 m head. Both overlook the two study desks.

The parents' dressing door was 0.9 m wide at x = 21.847 m. Its opening overlapped the checked bedside table by 0.23 m, and a bedside pendant entered the bed entry passage.

## Client direction

The client requested big, low-sill windows in front of both desks. Both study windows therefore have a 0.9 m sill and 2.3 m head, and their widths use the available column-free wall run with at least 0.3 m returns. This is an explicit exception to the earlier privacy adjustment; privacy treatment must be resolved in the real design without raising these sills.

**Design lead recommendation (not a client decision; awaiting the client's explicit yes):** the parents' dressing door is 0.8 m wide centred at x = 21.897 m, opening 21.497-22.297 m, a 100 mm return to the east wall's inner face (22.397 m), and the bedside table is a slim 0.35 m piece, so neither the table nor any fitting stands in the opening. Bedside pendants are replaced with wall-mounted reading lights on the solid head wall (one of them hung at 1.15 m in the entry passage).

An intermediate version centred the door at 22.05 m; its leaf reached 53 mm into the 0.2 m exterior wall and needed a recessed jamb reveal. That was rejected: no wall is cut. The 0.8 m doorway cannot admit the general 0.914 m route body; this is proposed as a waiver for the private dressing cluster and is NOT accepted until the client confirms it. The project checks 0.750 m there, borrowing the dimension from Approved Document M Volume 1 (2015 edition incorporating 2016 amendments), paragraph 2.25a, printed page 18. That passage is expressly for **bedrooms**, so it does not establish dressing-room compliance; actual clear leaf width and local access requirements need professional review.

## Consequences

These changes alter the authored Revit specification, daylight scene and render shell. They require Revit model updates and read-back verification. The wider study glazing can change daylight, glare, privacy and cooling results; these must be re-evaluated against the real site and selected glazing. The door's clear approach and swing must be checked after Revit reconciliation.


## Further changes after Gate A, pending the client's explicit yes (2026-09-28)

- **Dirty-kitchen fridge.** A full-height integrated fridge replaces the cleaning-cupboard column; cleaning storage
  moves under the folding counter (`villa_furnish.py`). Recommended by the design lead in answer to the client's
  request for appliances in the dirty kitchen; not accepted until confirmed.
- **Parents' bedside table 0.35 m** (was 0.5 m), so it stands clear of the dressing door opening.
- **Bunk ladder** added to kids' room A's bunk in `villa_furnish3d.body`: the Revit furniture specification changes,
  so the 5 mm read-back post-condition will differ from any model built before it.
- **Study windows in D2 and D3** follow D1 (same study).
