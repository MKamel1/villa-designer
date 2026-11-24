# WTA lessons

## wall-dominated: a distance cut does not see a flat wall (2026-11-24)
* Missed: the registered rule (share of rays closer than 1.2 m >= 0.5, from the brief) flagged 3 % of old-route interior frames
  against ~30 % counted by eye. The by-eye "wall" frames are one flat surface at 1.4-3 m (kids-a, corridor, parents-bed) filling
  40-70 % of the frame; the floor rays beyond 1.2 m dilute the near share.
* Guard: v2 adds single-surface dominance (one wall/door/furniture element >= 50 % of rays, median hit < 3 m), recorded as a
  post-hoc revision in `thresholds.json` (v1 results are kept beside it, so the change is visible). Regression:
  `OldRouteRegression` in `tests/flyaudit` pins real frames from the client-watched preview (15 by-eye wall frames, 12 flagged;
  3 misses stay documented: stair-gf 360, gallery-end 450, parents-bed 2070).
* The by-eye labels in that regression were read by this lane from WT's contact sheet after seeing v1 numbers: not an independent
  label set. The lead's own count was 30 % wall / 12 % near-black / 40 % good.

## dark proxy by room rectangle mislabels open-plan sub-rooms
* Missed: "no glass within 0.6 m of the room rectangle" marked kitchen-island/dining-side dark although they sit in a daylit hall.
* Guard: v2 asks whether a window or glazed door is *visible* from the room (rays from centre and quarter points).

## a wall in the middle of the view is a wall, not an obstruction
* A camera facing a wall at 0.5 m was labelled `blocked`. `blocked` now requires a non-wall element in the centre; test
  `test_facing_wall_at_half_metre_is_wall_dominated` and `test_close_obstruction_in_centre_is_blocked`.
