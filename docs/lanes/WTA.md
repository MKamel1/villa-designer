# WTA: independent geometric audit of walkthrough routes (2026-11-24)

`python -m archpipe.flyaudit <path.json> --scene <scene.json> [--id ROUTE_ID]` judges a route **without rendering**.
Run with `~/archpipe/envs/wta-venv/bin/python` (lane venv + `embreex`; see "Dependency"). Output: `knowledge/flyaudit/<id>/`
`report.json` (whole route, per room, key subjects, bad runs, calibration), `rooms.md` (per-room tables), `frames.json`
(every 2nd frame: metrics + category), `plan-GF.png`, `plan-B.png` (path coloured by category, view cone every 1 s).
A 7,507-frame route audits in ~12 s and ~4 GB (first run per scene adds an 8 s, 4 GB extract of the 1.4 GB scene.json to `out/flyaudit/*.npz`).

## Method
* Input: the path (`flythrough-villa-path/1`: per frame camera position/target, lens 24 mm, sensor 36 mm, 16:9) and the production scene
  meshes (1.79 M triangles from `scene.json`, door leaves already swung open, element id per triangle from `faces_by_element`; glass is
  see-through; markers ignored). Rooms = the design model's rectangles (`villa_r11.design('D1')`).
* Per frame (every 2nd, 12 fps): 64x36 pinhole ray grid from the real FOV (73.7 x 45.7 deg), first opaque hit (Embree BVH), hit
  distance, share < 1.2 m, share of rays that leave through glass / hit ground or context / nothing, element pixel shares, angle between
  view and travel direction (positions +-0.5 s), room under the camera by own point-in-rectangle test.
* Categories, priority backward > blocked > wall_dominated > outward > dark > informative; thresholds in
  `knowledge/flyaudit/thresholds.json` (policy, ours, pre-registered; revisions listed there).
* Per room: seconds, 360 check (union of view intervals of frames within 1 m of one standing point >= 342 deg), features (walls,
  furniture, fixtures, dressing) seen >= 3 rays in a frame with the hit inside the room rectangle: seconds seen, nearest distance;
  never-seen list; runs > 1 s of wall/backward/blocked frames.
* Key subjects: `knowledge/render-set/views.json` subjects (16 resolve to a `furn-` element, none unresolved): 40 sample points on
  the subject, cast from the eye while the camera is in a room that view covers. Status seen / BLOCKED (in frustum, occluded; blocker
  element ids and hit counts) / NEVER IN FRAME / room never entered.
* Whole route: seconds per level, stair frames and ground-z range, flight element seen, garden seconds, informative share.

## Limits (stated, not hidden)
Scene meshes only; closed cupboards report never-seen; `dark` is a proxy (no window/glazed door visible from the room under one
house-wide day exposure), not lux; `outward` is not counted informative in interior frames (garden threshold holds looking out are
therefore counted against the route); coverage is by the 64x36 grid (a feature needs >= 3 rays).

## Dependency
`embreex` (Embree wheel) is new: ~17 M rays against 1.8 M triangles is not feasible in numpy. It is installed in a private venv
(`~/archpipe/envs/wta-venv`, system-site-packages of the lane venv), not in the shared one. Without it `Geometry` falls back to a numpy
brute-force caster for scenes under 20,000 triangles, so `tests/flyaudit` (11 tests) runs in the normal lane venv; the full scene needs embreex.

## Calibration against the first villa preview (old route)
See `docs/lessons/WTA.md` and the hand-back; numbers are in `knowledge/flyaudit/villa-route-wt-villa3/report.json` (`calibration`).

## Results (2026-11-24)
| | old route (villa3, 312.8 s) | WT tour (villa4, 670.5 s, path sha af05502b84f4) |
|---|---|---|
| informative | 68.2% | 58.9% (65.0% outside 360 sweeps) |
| wall-dominated | 9.9% | 30.1% |
| backward | 13.4% | 0.6% |
| blocked / dark | 1.6% / 6.8% | 2.4% / 8.0% |
| rooms with a full 360 | 0 / 30 | 28 / 30 (not the two stair rooms) |
| runs > 1 s of wall/backward/blocked | 18 (67.9 s) | 66 (206.2 s) |
| garden frames | 54.8 s placeholders | none (all frames inside the footprint) |

Calibration of the old route: lead by eye ~30 % wall / ~12 % near-black / ~40 % good. Registered v1: interior wall 3.0%, dark 7.0%; v2 (post-hoc, see lessons): wall 12.0%, dark 8.3%, informative 63.1%.
Cross-check of the new route against WT's own Blender Workbench depth grid (`crosscheck-workbench.json`, 8,000 frames): non-informative share 40.8 % (audit) vs 41.1 % (Workbench), per-frame agreement 76.5 %, near-share correlation 0.74, median-depth correlation 0.60.
