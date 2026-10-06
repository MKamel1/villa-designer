# Family bathroom WC camera correction

The wider lens was selected for a vertical constraint absent from the old
`lens_basis` text. At the former best 24 mm standing point, the WC top was
28.14 degrees below the level eye, beyond the 26.57 degree vertical
half-frame. Its 17.2 degree horizontal need was unrelated to that failure.
The initial camera-standard reproduction exited 1; log:
`out/c4-family-wc-lens-before.log`.

Projecting the built WC also found that the old 16 mm camera clipped its
bottom: 40.05 degrees below the axis, beyond the 36.87 degree vertical
half-frame. The existing chooser tested a low subject's top, and the view
script tested horizontal footprints, so neither guaranteed a whole WC.

`render_views.choose` now measures every physical WC vertex, gives fully
framed candidates priority over aesthetic scoring, and refines failed
whole-WC searches from 0.10 m to 0.025 m spacing. This applies to the WC
kind in any room, without identifier or coordinate exceptions. Other
furniture retains its existing top/footprint framing contract. The exporter
records horizontal, lower-top, upper-fitting and whole-subject needs and
limits for both lenses, along with the searched positions and fitting
candidate counts. The camera-standard assertion still requires an actual
exceeded 24 mm constraint and a successful 16 mm frame; it now checks the
real constraint rather than interpreting caption prose.

Positions and targets below are model coordinates in metres: x and y are
the plan axes, and z is elevation. Both cameras are level at 1.35 m eye
height, use 16 mm on a 36 mm sensor, and have zero lens shift.

| Camera | Position | Target |
|---|---|---|
| Before | [9.727, -24.971, 1.350] | [12.025, -26.899, 1.350] |
| After | [9.602, -24.846, 1.350] | [12.200, -26.346, 1.350] |

The refined best 24 mm point is [9.577, -24.846]: the low top needs
27.41 degrees and the whole WC needs 36.30 degrees vertically, beyond
26.57 degrees. Zero fully framed candidates were found in that search.
The chosen 16 mm point needs 36.62 degrees vertically, within 36.87
degrees; the refined search found 16 fully framed position/aim candidates.
These are bounded standing-point searches at level eye height with zero
shift, not a mathematical proof over all possible continuous camera poses.

The fixture design and east-WC changes are preserved. No fixture position,
rotation, geometry, check threshold or dependency installation changed.
The final comparison normalizes JSON list versus Python tuple containers,
then proves all fixture-layout values unchanged and all 204 unique built
WC vertices exactly equal to the frozen geometry; evidence:
`out/c4-family-wc-unchanged-design.log`. The first unnormalized comparison
failed on container types, the previously recorded coordinate-container
trap, rather than on a changed design value.
The scene was regenerated with `villa_render.write()`. The view script now
projects the exported WC meshes through both frame dimensions and fails
closed on clipping or unresolved geometry. The actual scene passes that
check. The before/after diagnostic projection was inspected:
`out/c4-family-wc-camera-preview.png`. This is a geometry preview, not a
new photoreal presentation render.

Frozen real-input and live-scene regressions prove the former clipping,
clean corrected frame, narrower-lens/wrong-aim/missing-mesh mutations, and
the same behavior with renamed subjects/room and translated geometry.
The guest rain-head test remains the upper-vertical sibling. The first
translated-proof run exited 1 because its test harness assumed every bath
record was a point; the corrected test translates point records and
preserves non-point fitting records. That initial result remains in
`out/c4-family-wc-first-fix.log`.

All requested final checks used
`/home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python`, `PYTHONPATH=src`
and `NO_COLOR=1`. Process exit status is the result.

| Check | Exit | Evidence |
|---|---:|---|
| `python -m unittest tests.test_render_standard` | 0 | 57 tests; `out/c4-family-wc-render-standard.log` |
| `python -m unittest tests.test_render_views` | 0 | 13 tests; `out/c4-family-wc-render-views.log` |
| `python scripts/villa_render_views.py` | 0 | `out/c4-family-wc-views-plan.log`; regenerated `out/villa/render-d1/views-plan.png` |
| `python scripts/verify.py --portable` | 0 | `out/c4-family-wc-verify-portable.log`; ALL PASS |

Controls and proofs are registered under `c4-lens-basis-missing-vertical`
in `knowledge/mounting-guards.json`; the villa-render skill and learning
index describe the revised procedure. No commit was created. The lead
retains the full-suite and photoreal presentation review responsibilities.
