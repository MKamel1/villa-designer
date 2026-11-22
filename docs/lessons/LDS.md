# LDS lessons (landscape site analysis)

1. **A thin solid read as shade.** The first build showed a dark 0 h strip at x = 15.375 on the extension roof. Cause: the 50 mm
   guard rail (x 15.362-15.412, z 0-1.1) is a solid triangle prism in the enclosure and a 0.25 m cell centre fell inside it, so every
   sun ray started inside the solid. Found only by LOOKING at the PNG; the numbers looked plausible. Guard:
   `model.classify` drops cells whose centre is inside a solid (`raycast.inside_solid`, odd ray parity, class 10);
   `test_thin_rail_cells_are_dropped_not_reported_as_shade` pins the real cell; `test_inside_solid_parity_positive_and_negative`
   proves the test is neither vacuous nor greedy (open garden and the space under the terrace slab are NOT inside a solid).
2. **Interior doors on an exterior wall line.** The first views run counted lounge, family and kitchen "doors" on y = -23.591: they are
   internal doors of the extension that happen to lie on the east face line. Guard: an exterior door must name `yard` or `deck`;
   `test_views_positive_and_negative` (family-bath excluded, study north window sees 0).
3. **A required screen height is not monotonic the way intuition says.** I first wrote "farther seats need less screen". Computing it
   showed the opposite for downward sightlines (a far target is seen at a shallower angle, so it crosses the boundary higher). The
   `reading` text in privacy.json now says so, and `check.py` enforces the one invariant that must hold: a *visible* sightline always
   crosses above the existing fence top (`test_validator_rejects_a_screen_below_the_existing_fence`).
4. **Orientation names invert the true sun.** Client "east" (+y) is true NNE (bearing 20); client "south" (+x) is true ESE (110); the
   street faces WNW (290). Morning sun therefore comes from the building side of the north court and afternoon sun from the street
   fence; the sun-path intuition from the names is wrong. All sun uses `orientation.sun_direction`; the plots draw both north arrows.
   The "covered" cells under the GF terrace get 1-2 h of high-sun light slipping under the slab edge (independently confirmed:
   `test_raycast_agrees_with_the_project_sun_study_hour_by_hour`).
5. **A negative control is cheap and caught the gap.** Street pedestrians see nothing because the street fence is solid in the model;
   the same check with the fence triangles removed sees the court (test). That is how the missing gate shows up as GAP S4 rather than as
   a false "street is private".
6. **Old numbers can be wrong for a reason you can name.** G2's "nine hours" on the south beds is not reproducible (G2 used a bare-court
   screen); G4 and G6 reproduce. Quote the earlier studies next to ours with the cause, never overwrite them.
7. **Do not cite what you cannot open.** The knowledge index on this workstation is empty and the *Site Analysis* book, *A Pattern
   Language* and BR 209 are not on disk. The checklist is mapped to Time-Saver sec. 220 (which was readable) and the missing books are
   GAP C1. Guard: `check.py` refuses a checklist that drops C1. Eye heights come from Time-Saver p.340-4 because nothing else was found.
8. **A machine under load changes your plan, not your result.** The 32-core box ran at load 30 from the other lanes; the build took
   about 150 s instead of 60. It is vectorised numpy on the CPU (no GPU, no jobq needed).
