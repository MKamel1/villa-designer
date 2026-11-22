# RV1 lessons (independent built-scene checks)

Each entry: what went wrong, why it was missed, which guard now catches it.

1. **A fan triangulation covered the stair opening.** `fan()` triangulated every face from its first vertex. A concave slab
   underside with the stair opening cut out became triangles that spanned the opening, so a ray above the stair hit a
   "ceiling" that does not exist (K16: 64 mm headroom, K01: a 23 mm crossing; both false). Missed because both numbers looked
   plausible next to a real design question (is the stair under the slab?). Guard: `geom.fan` ear-clips non-triangles;
   `tests/parity/test_geom.py` fails on the concave-L and the bridged-hole polygons (area 3 and 12, the fan gave 4 and 16).
2. **Face-attributed bounding boxes are not element boxes.** P2 tags faces by registry/name; finish skins of neighbouring rooms
   are tagged to the slab or wall they touch. Walls came out 50-160 mm too big, a column 1.2 m too wide, a "deck" 50 mm too
   far south (it produced a false "wall through the deck"). Guard: K02 reads the slab footprint from its VERTICAL faces, K12
   asks only that a face exists within 2 mm of each reference plane, K10 asks that the built footprint CONTAINS the carcass;
   none trusts an AABB of everything tagged to an id. Mutation choices read intended column faces from the model for the same reason.
3. **A mutation can be valid geometry.** Moving a wall that is already sized to the ramp soffit under the ramp (M1) is not a
   defect; counting it a "check miss" would have been wrong and counting it a catch would have been tuning. It is reported as a
   miss with that cause and an added mutation (M1b, a cross wall made 0.7 m taller) carries the claim.
4. **A read-back that rounds cannot carry an exact tolerance.** The frozen Revit wall tops are to 10 mm; a fixed wall at -1.01
   touched the ramp soffit at -1.0104. D03 reproductions use a 10 mm tolerance and say so; D02 (sub-mm) uses exact box geometry.
5. **A check keyed on one field misses identity.** The D10 historic false negative came from keying the post-condition on Mark.
   K09 keys on the element id (and the frozen read-back on any of mark/spec_id/app_id), and K13 fails any scene mesh with no id.
6. **A wall join is not a clash.** With the wall centre line on the ramp/deck edge (every Revit option) half the wall's thickness
   overlaps the slab by construction. K02 allows half a thickness of plan overlap and fails beyond it; the through-wall cases
   (D03) overlap by the whole thickness.
