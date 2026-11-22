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

## Round 3 (decided garden: shade trees, half pit, pond section, visualisation)
* **A ground plane under the rim buried every pond.** The far-ground plane (6 cm below the surfaces) ran under the pond openings, so the water (150 mm down) was never
  visible: "the water reads as a flat beige slab" was geometry, not shading, and two rounds of material tuning would not have fixed it. Found by a top-down debug render, not by reading.
  Guard: the ground plane is built with the pond openings left out (`pond_rects` in the spec) and `test_the_ground_plane_has_a_hole_over_every_pond` states it.
* **Two scenes with one tag shared one spec file and a sister-plot scene rendered into the production folder.** `/tmp/ldb-specs/<tag>.spec.json` was keyed by tag only; a main and a
  visualisation render started together overwrote each other, and the main job rendered the visualisation spec (unstamped) into a production directory. Guards: the spec file is keyed by
  tag + output directory, the spec carries `spec_sha` which the receipt must echo (`render` refuses images whose receipt does not match), and the visualisation scene may only be written under
  a directory named `visualisation` and is stamped and re-checked pixel-wise. Tests: `test_render_only_into_a_visualisation_directory`, `test_a_receipt_of_another_spec_is_refused`.
* **A glass block is not water.** A closed refractive solid with volume absorption rendered as an opaque grey slab (caustics off, bump on a smooth interface). Water is now one transparent surface
  with a Fresnel-weighted glossy reflection and a ripple; the depth tint is in the liner (Z-ramp). The measured pond section is kept as a closed solid for the checks but only its top face is rendered.
* **A pond lip outside the layout rect collides with its neighbours.** Edge planting, paths and paving all stand against the pond rect; a coping ring outside it clipped them (13 clips).
  The coping now lies inside the rect, overhanging the water edge on a bearing ledge, and the pond check measures it (top at ground level, a finish unlike the paving).
* **A bounding box is not a fish.** The koi bounds were a square of the fish length, so a 0.7 m koi "stuck out" of a 0.5 m trench; the bounds are the rotated fish box, and the koi swim along the pond.
* **Climber leaf panels clipped the benches they climb behind.** A panel centred on a plant ran 0.2 m past the end of the bench it stood behind. `climb_target` now trims the panel to the free stretch round the plant.
* **Free-text asset metadata is data.** The koi row said "head toward -X, body curves toward +Y": `_front` reads the first signed axis from the text and falls back to -Y; a role with no parsable front is placed
  by symmetry, and the receipt measures the result.

## Round 3 final (2026-11-22)
* **A box hidden from the camera and the shadow rays still blocked the sky light.** The bird's-eye hid the house box with `visible_camera/visible_shadow = False`; the ground under it rendered 11-25 % pure black (it only looked fine when the box was 6 m, not the 9 m of the env model). Found by looking. Guard: the box is hidden from every ray type, the house leaves a footprint slab, and `preview.black_share` records the pure-black share of every view in the receipt and prints a QA warning above `BLACK_MAX` (6 %; honest dark pond views measure < 5 %). Test `test_the_black_hole_guard_fails_on_the_real_defect_and_passes_the_fixed_render` uses the real defective image.
* **"Not on this machine" meant "not as glTF".** LDG reported the Fab plants missing because it looked for `scene.gltf`; they are FBX archives. `resolve` was right to say "file missing" but the cause was the path rule. Guard: `gltf_path` knows Fab archives, a test requires aspidistra, fountain grass and oregano to be drawn and the placed file to be an existing LOD0 FBX; a missing archive still degrades to a labelled stand-in, tested.
* **Megascans single-channel maps are red-only (LDL's defect), so the wiring is a guard of its own.** `fab_blender` reads Opacity and Roughness through `_red`; a test checks the source wiring and measures a real opacity map (red >> green, blue).
* **A mirrored layout is not a mirrored tree.** LDG's visualisation layout mirrors tree centres but not `crown_center`; the crown was drawn 11 m from its trunk and the checks flagged clips only by accident. Guard: a crown centre beyond the declared lean or half a spread is ignored and reported in the build warnings (test), and the finding is listed for LDG.
* **A tree that leans over the table must not lean over the chairs.** The first stems bent from the ground and clipped two chair backs; stems now rise vertically to 1.15 m. Guard: the clip check over the final layout (`test_stems_stay_clear_of_the_chairs_under_the_crown`).
* **Context drawn from assumptions hides the real height.** The previous house box was an assumed 6 m; the environment model says 9 m (basement -3.0 to roof +6.0). Context now comes from `villa_env`, with a test on the heights, and a plot fence is not drawn where the layout's own wall stands.
* **A graded asset is not automatically fit for a role.** The graded crape is one leaf state (flowering); a deciduous shade tree needs both. The schedule row says so (`one leaf state only`) and a test pins it.
