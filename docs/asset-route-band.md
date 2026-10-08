# Compact portable asset route input

The 2026-10-06 follow-up separates walking geometry from framing geometry in
`knowledge/asset-route-geometry.json.gz`. The compressed tracked record is
**1,482,582 bytes**, down from 5,919,050 bytes (74.95% reduction), below the
1,500,000-byte budget. The obsolete uncompressed record is superseded.
No shared assets, design placements, render or native model are changed.

Walking geometry retains all 421,178 previously selected triangles with their
original face order, winding and vertex connectivity. No convex hull,
decimation, triangle clipping or vertex welding is used for walking checks.
Selection uses the source coordinates before encoding: retain a whole
triangle when its lowest vertex reaches the declared native walking band.
Crossing triangles retain their above-band vertices. The original source base
continues to seat the asset; integer rounding never changes that datum.

## Precision and storage

Frangipani remains bit-for-bit float64 because its continuous translation
search uses a one-micrometre separation. Its coordinate error bound is zero.
For the six other assets, the authored policy permits an integer coordinate
grid whose scene step is at most 1 mm at the largest admitted scale. The native
grid step is 0.001 metres divided by that maximum scale. Round each coordinate
to the nearest grid integer, without merging original vertices. Integer
storage and decoding are lossless at this declared build precision; these
six coordinate arrays are quantised, rather than bit-identical source floats.

Each scene coordinate can move by at most 0.5 mm at maximum scale. A vertex's
Euclidean distance error, combining its three coordinate errors, is at most
0.866026 mm (the square root of three times 0.5 mm). Positive smaller scales
reduce the error, yaw preserves distances, and the bench's separate axis
scales are individually bounded by the same maximum. Walking predicates use
the decoded triangles directly, without an inflated hull or relaxed collision
tolerance. This precision is not a claim about submillimetre source contacts.
The synthetic branch proof places a face 1 mm below the envelope top at the
maximum recorded scale and still detects it; the sibling 1 mm above stays clear.
Frangipani's existing 0.01 mm inward-movement failure and exact continuous
translation minimum remain unchanged.

Vertices are numbered by first use, improving index locality. Coordinates and
index deltas are byte-shuffled, compressed with the Lempel–Ziv–Markov algorithm (LZMA), and encoded as base64.
The JavaScript Object Notation (JSON) container is compressed with deterministic gzip (zero timestamp).
Both compression layers are lossless. Schema version 3 records the coordinate
type, native grid step, maximum scene error, hull count, source bounds, band,
scale range/mode, source glTF and external-buffer SHA-256 hashes, generator
command/date and payload digest. SHA-256 means the content hash used to detect
changed bytes. The digest binds coordinates, indices, hulls and safety metadata.
Generation refuses the complete record before writing either record or
manifest if it exceeds the budget. Portable verification enforces that budget.

## Framing equivalence

Framing stores only the original, unrounded vertices of the three-dimensional
convex hull of the full-height source geometry. Every source point lies in
that hull, and each hull vertex is a source point. A view frustum is an
intersection of linear halfspaces and is convex. It contains every source
point exactly when it contains every hull vertex. Positive scaling, upright
yaw and translation preserve this equivalence, as do plan-coordinate extrema.
The hull never supplies walking triangles. Degenerate point, line and plane
assets are supported. Near-coplanar determinant signs use exact rational
arithmetic on the original binary floating-point coordinates, so a floating
roundoff threshold never authorises dropping an exterior point.

The real frangipani and swing are compared against all full-height vertices
for in-frame, top-clipped, bottom-clipped, horizontally clipped and behind-camera
views. `tests/fixtures/asset-framing-real.json` freezes those all-vertex results
by value, including source hashes, camera definitions and full vertex counts.
Portable tests compare the hull-only consumer with these results. A fresh
source comparison and fixture validation runs without rendering:

```bash
PYTHONPATH=src python scripts/generate_asset_framing_proof.py \
  --library-root /path/to/render-host/library --check
```

Omit `--check` only to regenerate that proof after an intentional source change.

| Asset | Scale interval | Walking triangles | Source vertices | Framing hull vertices | Maximum scene error (mm) |
|---|---|---:|---:|---:|---:|
| flower_ursinia | 1.0–1.1 | 24,933 | 19,345 | 115 | 0.866026 |
| outdoor_table_chair_set_01 | 0.9–1.1 | 9,828 | 5,408 | 102 | 0.866026 |
| sf_bougainvillea | 0.9–1.3 | 163,748 | 82,651 | 77 | 0.866026 |
| sf_egg_chair | 1.0–1.1 | 69,928 | 33,677 | 357 | 0.866026 |
| sf_frangipani | 1.18–1.7 | 47,535 of 82,691 | 53,342 | 103 | 0 |
| sf_ixora | 0.63–1.0 | 88,272 | 64,058 | 188 | 0.866026 |
| sf_wooden_bench | 0.5–1.0 per axis | 16,934 | 8,539 | 156 | 0.866026 |
| Total | | 421,178 of 456,334 | 267,020 | 1,098 | |

Independent read-only audit of all seven raw assets confirms exact array
equality to the declared encoding of the selected source triangles. Maximum
measured errors in scene millimetres at maximum scale: ursinia 0.849280,
bistro 0.845918, bougainvillea 0.852803, swing 0.853689, frangipani 0,
ixora 0.849640, bench 0.843013. Every hull point is an original source vertex,
and all three coordinate extrema exactly match full-height geometry.

## Coverage and consumers

`knowledge/asset-route-policy.json` remains authored coverage and precision
input. The native upper bound is the original lowest point plus 2.41 metres
divided by the minimum admitted scale: 2.0 m is the existing walking height;
0.41 m is calculation coverage for the existing lowered-tree diagnostic,
not an ergonomic rule. Placement requires upright geometry, positive scales
in the recorded interval and each actual world walking top within coverage.
Plants use uniform scale; the existing bench retains its documented axiswise
exception. Missing, stale, corrupt or unsupported data fails with the asset
name and regeneration command, even for props overlapping no route.

| Reader | Input |
|---|---|
| `villa_landscape.route_violations` | Indexed band triangles at declared precision; validate all placed assets and actual walking tops. |
| `garden_tree_position.search_position` | Lossless frangipani band triangles; validate every route reachable in the search domain. |
| `villa_render_views.subject_points` | Unrounded full-height hull vertices via `prop_framing_points`. |
| `asset_route_record` | Tracked gzip record and manifest; no HOME or render-library access. |
| `generate_asset_route_geometry` / `asset_route_generator` | Explicit read-only render-host source path. |
| `generate_asset_framing_proof` | Explicit source path for fresh all-vertex evidence. |

Regenerate the record and matching manifest on the render host:

```bash
PYTHONPATH=src python scripts/generate_asset_route_geometry.py \
  --library-root /path/to/render-host/library \
  --assets flower_ursinia outdoor_table_chair_set_01 sf_bougainvillea \
  sf_egg_chair sf_frangipani sf_ixora sf_wooden_bench
```

Review policy, record, manifest and framing proof together. Never widen a
walking tolerance, move a prop or simplify its geometry to meet the budget.
Run the same focused modules as the previous follow-up and `verify.py --portable`
with normal and initially empty HOME. Full-suite validation belongs to the lead.
Historical 172-test logs in `/tmp/asset-route-band-*` describe the superseded
5.9 MB representation, not current storage evidence.

Final validation (2026-10-06): the same 176 focused tests passed with normal
HOME (225.748 seconds) and initially empty HOME (224.926 seconds), both exit 0.
The modules were `test_asset_route_geometry`, `test_landscape`,
`test_villa_render_scene`, `test_climber_placement`, `test_garden_render_subjects`,
`test_render_views`, `test_villa_furnish`, `test_villa_furnish3d`,
`test_villa_exposure_assets`, `test_villa_options`, `test_villa_scene_provenance`
and `test_asset_intake`. `NO_COLOR=1` execution of `verify.py --portable` also
exited 0 in both environments. Adapter checks and `git diff --check` passed.
Current logs: `/tmp/asset-route-compact-*`. No render, commit or full-suite claim.

Compressed-record SHA-256: `8a259ce3a12bcd75f22d45ac933a2377ef39022925ba8d4d5bac48eb277d807e`.
