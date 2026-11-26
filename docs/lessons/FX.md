# Lessons, lane FX (2026-11-25)

* `kitchen-wall-units-shade-the-worktop`: wall cupboards above a lit worktop were not in the lighting engine's model (stated limit: no furniture shadows), so the
  sink plane would still have "passed" at 300.7 lx. Own probe (ray test of each downlight against the unit box): direct 288 -> 270 lx, minimum 127 -> 6 lx at the
  wall. Missed because the engine ignores occluders by design. Guard: an under-cupboard `UC` strip is part of the design (appended last so no fixture id moves)
  and `tests/test_villa_render_fx.py` keeps the units inside Neufert/Mitton limits (`wall_unit_problems`, with negatives).
* `loft-desk-ceiling-light-is-shaded`: the per-desk ceiling downlights of kids A (L6c) would sit above the loft bed. They are replaced by an under-loft strip plus the
  child's own lamp. Guard: `villa_furnish.check` stacking rule is explicit (`under=`), a loft in front of the window or on the door swing still fails
  (`test_a_loft_at_the_window_wall_is_refused`).
* `bare-box-parts-are-refused`: the physical-part guard refused the loft's single-box mattress/slats and box pillows (`bare rectangular proxy`). They are now rounded
  slabs and an inflated pillow shell; no exemption was added to `knowledge/c3-part-exemptions.json`.
* `stage2-receipt-binds-the-fitted-footprint`: the Stage-2 receipt held fitted desk models for `ka-desk-1/2`; moving and enlarging the desks made integration refuse.
  The four kids-A desk/chair models were dropped from the receipt (procedural desks again) and the receipt refreshed baseline-relative (11 + joint, 0 findings);
  `v06-kids-room` was removed from `reviewed_cameras` because its subject list changed.
* `ownership-vs-the-brief`: the FX ownership list did not include `villa_furnish.py`, `villa_furniture_detail.py`, `villa_lighting.py`, `villa_checks.py`,
  `revit_spec`-adjacent tests or `knowledge/lighting/sensor-obstructions.json`, yet the requested changes live there. They were edited and are listed in the hand-back.
