# LDB lessons

* **A box helper with two argument orders hides a 52 m footprint error.** `box(x0,y0,z0,x1,y1,z1)` and `box(x0,y0,x1,y1,z0,z1)` were both written in one
  sitting; the wrong one built every paving slab 52 m away and only the footprint check, run before any render, showed it. Guard: the rect form is a
  separate `rbox`, and `test_layout_rects_are_the_built_extents` compares built extents with the layout rects for the first paving areas.
* **A tolerance that shrinks a thin part erases it.** The foliage-clip tolerance (50 mm) was first applied to both the crown and the box it was tested
  against; a 20 mm louvre blade shrank to nothing, and a mature pomegranate crown passed straight through the pergola roof. Guard:
  `test_mature_pomegranate_hits_the_pergola_louvres_and_the_checker_sees_it` (a real case, not a synthetic one).
* **The layout repeats ids across the three gardens** (`paving-0` three times). Element ids are made unique by region suffix (`ld-paving-0-r1`);
  `test_duplicate_layout_ids_across_gardens_get_distinct_element_ids` keeps it so. LDG should make its ids unique at source.
* **A species the library calls `climber` is not the only climber**: Jasminum sambac is `flowering_shrub` in LDL but RHS says climbing habit; it was drawn as a
  free-standing 1.7 m blob in front of the trellis and clipped it. The climbing test also reads the sourced foliage text.
* **Hiding the house box from the camera leaves it in the light path**: the bird's-eye showed a black hole where the house stood. Hidden-from-camera
  context is also hidden from shadows in the preview (stated in the receipt).
* **GPU queue**: other lanes' jobs hold the lock for minutes to hours. A preview job waits in `queued`; plan one batch per age, not one per view.
