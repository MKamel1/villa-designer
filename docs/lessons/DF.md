# DF lessons (parents' bedroom: the way to the dressing room)

Client, walkthrough v3 at 6:21: "something is blocking the way to the dressing room, near the night stand."

* **The obstacle was the bedside books, not the chair.** `props()` placed the book set with its glTF origin at the bedside's centre.
  The asset's bounds are x -0.019..0.532 (origin at the left end, 0.551 m wide), so at scale 1 the set ran x 21.286..21.837 over a
  0.35 m bedside (x 21.13..21.48): 0.357 m hung past the top, floating at 0.55 m in front of the dressing door's opening
  (x 21.497..22.297). Evidence: `knowledge/flythrough/evaluated-obstacles.json` (`prop-bedside-books-000..019`) and the client's frame.
  *Why it was missed:* WT recorded a pinch but named the chair; nothing compared a prop's measured box with the surface it stands on
  (the plant guard checked only the plant's *centre* against its support), and the walkthrough admission planner treats props as
  0.15 m-envelope obstacles, so it routed round the books instead of reporting them.
  **Guard:** `villa_render.dressing_overhang_violations` runs in `props()`: any prop whose base is at a furniture top and whose
  measured world box touches that piece's footprint must lie wholly inside it. Tested against the real old placement
  (`tests/model/test_circulation.py::DressingOverhang`).
* **The vanity chair was a real second pinch.** The generated desk chair stands 0.30 m out from the vanity; the duvet is 0.10 m past
  the bed; between them 0.46 m (WT: 0.47). `villa_furnish.check` rasterises routes against plan pieces over 0.3 m only, so loose
  seats were not in it and the principal bedroom passed. **Fix:** the vanity's chair is staged
  tucked under the top (`villa_furnish3d.TUCKED_SEAT`, designed furniture, not a render trick). Its back cannot go under
  (its back is 0.85 m, the top 0.75 m).
  **Guard:** `model/circulation.py` raster-tests the widest path between every door approach of every cluster with chairs and
  stools as obstacles; `villa_render._build` raises `staged circulation` on any route under its requirement. Positive test: the
  pre-fix staging (`chair_pulled_out=True`) fails at 0.56 m where 0.75 m is needed; negative: the tucked design and every other
  cluster pass.
* **Dressed-bed sensitivity (not gated, reported).** With the evaluated duvet and curtain stacks as obstacles the route round the
  bed foot is 0.63 m (duvet 0.155 m past the mattress foot) and 0.45 m at the curtain stacks. Those are simulated cloth, so the
  gate uses plan pieces plus loose seats; the numbers are in the DF hand-back for the lead.
