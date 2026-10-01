# C3 phase 2b — Chunk A checkpoint

This is a code and geometry checkpoint for the client-visible bathrooms and external fan grilles. Lead image review is still required. No design fitting or layout position changed; only the v16 camera intent and chosen camera changed. No commit was made.

## Geometry and basis

- Guest and parents' rain heads now have a closed 24 mm diameter brass ceiling drop, a 280 mm diameter by 28 mm thin round brass body, recessed dark nozzle face and circular brass nozzle array. **ASSUMED** size and pattern; no selected product supports the dimensions yet. The authored head centres and elevations remain fixed.
- Both hand showers now have a closed 800 mm round brass rail, upper and lower wall brackets, slider, shaped handset/outlet and curved segmented brass hose. These dimensions and details are **ASSUMED**; the authored fitting positions remain fixed.
- Guest bathroom and dirty-kitchen external grilles now have 240 mm square metal perimeter frames, seven louvres and open slots to the duct. Face size and blade spacing are **ASSUMED**.
- The guest linear drain is one slotted stainless frame with a dark recessed channel at the authored drain coordinates. The redundant furniture drain block is removed. The wet finish is flat in this scene: a construction fall and waterproofing are pending, so the render label states that the fall is **not modelled**.
- `v16-guest-wc` declares the open wet zone, rain head and hand shower as subjects. The view chooser checks high bath fittings against the vertical field of view. Its best 24 mm point puts the rain head top 28.3 degrees above a level eye, outside the 26.6 degree vertical half-frame. The 16 mm choice holds the subjects; the plan guard exits 0 and a wall-sampling check finds clear lines to the two fittings. No design element moved to clear the view.

## Part boundary and review

Each new rain-head, riser-rail, shower-head, shower-hose, rail-bracket, fan-grille and drain record declares its physical kind and is tested as a closed outward solid through `Part`. The initial drain recess was a bare box and was replaced by a channel section after the collector caught it. The two existing rectangular duct records are still open C3 failures outside this chunk.

The first support regression found ten unsupported new hand-shower pieces because the brackets stopped short of the built walls. Brackets now extend from the fixed rail position into the nearest built wall face. The full real scene's support check returns `unsupported []` and the Chunk A collector contains only the two pre-existing duct proxy failures.

Preview each new visible kind in an isolated neutral-light close-up at scale: rain head and nozzle face, riser/slider/brackets, shaped handset and hose, slotted drain with its wet-floor junction, and open fan grille. Then render `v16-guest-wc`, `v12-ensuite` and `v17-dirty-kitchen` at the checkpoint. Review v16 for the open wet zone, drain, rain head and riser all clearly visible, and check there are no dark faces, floating fixings or blocked subjects. Review v12 for brass fittings and v17 for the grille and duct termination. The plan graphic is `out/villa/render-d1/views-plan.png`; it is a geometric preview, not a photographic acceptance image.

Verification: `NO_COLOR=1` focused Part, fixture, support and camera regressions passed (14 tests, exit 0); `scripts/verify.py` exited 0 with `RESULT: ALL PASS`; `scripts/villa_render_views.py` exited 0. Photographic preview and lead approval are pending.
