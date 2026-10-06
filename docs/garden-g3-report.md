# Garden rebuild R3b-4 — G3 top garden

2026-10-06, based on `7ae430d`. Authored review candidate; no render or commit.
The top garden occupies the deck x = 6.877–12.777 m and roof x =
12.777–15.412 m, both y = −23.591…−20.601 m. Scene coordinates x and y are
horizontal positions in metres; z is elevation in metres. Ground-floor (GF)
scene z = 0 corresponds to street +1.20 m. The existing ramp, study slider,
rails and native specification remain unchanged. G1/G2 planting and furniture
are retained. No real villa design gate or photographic approval is claimed.

## Layout and planting

`knowledge/garden-palette.json` remains the sole species/dimension/spacing
record. Added procedural appearance envelopes are ASSUMED placement intent,
not new verified botanical figures. No new imported plant asset or look-alike
species is introduced. Prostrate rosemary has needle-covered woody shoots and
inward trailing growth over the trough edge; aloe has thick tapered rosette
blades. Authored photographic likeness remains UNVERIFIED pending lead draft.

All three troughs are slim powder-coated steel, 0.25 m high, seated directly
at scene z = 0. Their 3 mm plates and inward folded rims are ASSUMED fabrication
intent. Visible soil is recessed 5 mm below the rim at z = 0.245 m; each plant
root is seated there. No plinth, stone/concrete-look bowl or solid cap is used.
The single named parameter `villa_landscape.TROUGH_COLOUR` is labelled **“dark
bronze, ASSUMED pending client confirmation”**. Its linear red/green/blue values
are [0.12, 0.075, 0.045]; reflectance 0.08 and roughness 0.48 are ASSUMED authored
appearance, **not a manufacturer finish**. Supplier specification remains open.

Rectangles below list (minimum x, minimum y, maximum x, maximum y). Drift
counts mean plants of one species grouped in the same trough. Sun hours mean
the number of direct-sun samples within the nine hourly checks from 09 to 17,
using the existing June-solstice enclosure screen; they are not a detailed
shadow simulation or annual Egypt performance finding.

| Trough | Length × width × height, m | Rectangle, m | Species | Centres, m | Drift | Sun samples per plant |
|---|---|---|---|---|---|---|
| Deck north | 3.20 × 0.34 × 0.25 | (9.20, −21.10, 12.40, −20.76) | Salvia rosmarinus Prostrata Group | (9.80, −20.93), (10.80, −20.93), (11.80, −20.93) | 3 | 8/9 each: 09–16 |
| Roof north | 2.13 × 0.40 × 0.25 | (13.02, −21.16, 15.15, −20.76) | Aloe vera | (13.40, −20.96), (14.10, −20.96), (14.80, −20.96) | 3 | 9/9 each: 09–17 |
| Roof south | 2.13 × 0.40 × 0.25 | (13.02, −23.44, 15.15, −23.04) | Aloe vera | (13.40, −23.24), (14.10, −23.24), (14.80, −23.24) | 3 | 9/9 each: 09–17 |

Rosemary has a measured 1.00 m longitudinal span, 0.32 m young depth and
0.30 m total shoot height including the trails; its verified palette range
is 0.1–0.5 m high and 1–1.5 m spread. Its lower shoots extend approximately
0.071 m inward beyond the trough side. Centre spacing is 1.00 m achieved
versus 0.80 m required by the existing 80%-of-spacing-envelope guard.
Aloe appears at 0.55 m high and 0.36 m maximum span; these are ASSUMED young
sizes because the palette has no numerical source range for aloe dimensions.
The client brief's up-to-0.9 m height is retained as brief intent, not promoted
to a verified botanical source. Aloe spacing is 0.70 m achieved versus 0.40 m
required from its explicitly ASSUMED 0.50 m spacing envelope. Each trough is a
three-plant drift; the drift guard rejects two or six plants without exemption.

The two existing top-pot assemblies are rebuilt as planted terracotta-red
glazed ceramic pots with visible soil, directly on the deck. Centres are
(7.40, −21.20) and (9.30, −22.95) m. The former second location (10.50, −21.20)
would occupy the new north trough planting; this is a layout correction for
the planting/clear access design, not a camera move. Pots are 0.40 m high with
0.18/0.25 m lower/upper radii and 0.259 m rim radius, all ASSUMED geometry.
Both retain Ixora coccinea at the palette's ASSUMED 0.55 m nursery height:
the record contains “full sun for best flowering” and both centres achieve
9/9 direct-sun samples (09–17), above the recorded full-sun threshold of six.
A quote or sun-screen failure replaces these accents with Aloe vera from the
top palette; it cannot silently keep Ixora. Nursery spread/root review remains
open, and top Ixora is the brief's explicit two-pot exception to its normal
north/west placement zones.

Ursinia anthemoides is omitted: its zone is `gf-beds` and its light field is
UNVERIFIED, so its record does not establish this top-trough placement.
Existing top bougainvillea and the wide Ursinia appearance pack are removed.
The round-3 plan's **potted small shade tree is not placed because no verified
top-zone shade-tree species fits the palette**. This remains an open item.

## Routes and benches

D2 is the lead's walking-envelope decision: actual faces/asset triangles may
not enter the vertical volume from the walking surface to 2.0 m above it.
High foliage outside that volume is not walking contact. Every actual stone
also retains its measured-height route guard.

| Route | Achieved | Required / basis |
|---|---|---|
| Study threshold to deck connection | 0.914 m wide, x = 7.820–8.734; y = −23.591…−20.601; existing 1.80 m slider unchanged | ≥0.900 m one-way clear width, retained Time-Saver 2nd ed. 1998 p.340-9, card `lts-path-width-oneway-900`; D2 volume clear |
| Deck gate link | 0.914 m wide, x = 6.877–8.734; y = −22.550…−21.636; intersects study route; stepping stones confined to deck | Same ≥0.900 m and D2 volume; no container/plant/bench contact |
| Street gate to ramp top | Same 0.914 m reserved strip, x = −0.123–6.877, within unchanged 2.990 m driveway; profile z = −1.20, −1.10, −0.10, 0.00 at x = −0.123, 0.877, 5.877, 6.877 | D2 volume checked over the actual sloping floor, not a flat z = 0 envelope; no new ramp paving or geometry changes |

The ramp remains a driveway and its steepness is unchanged; this geometric
walking-contact result is not a claim of accessible ramp compliance or a
separate pedestrian lane. The original route/seat cards are retained verified
project evidence in `knowledge/library.json`; the held-book index was absent
on this workstation, so no fresh original-page read is claimed here.

Both benches are backless `sf_wooden_bench` appearances with the recorded
axiswise scale exception, long axis along scene y. Each is 1.800 m long,
0.405 m wide and 0.400 m seat height above its slab. The retained seat-height
range is 0.350–0.450 m (Time-Saver 2nd ed. p.340-11,
`lts-seatwall-height-350`). Slabs are 12 mm paving, directly on the deck/roof,
not raised plinths; bench bottoms are at scene z = 0.012 m. The asset is
backless/symmetric, so “facing” declares the side with clear knee space.

| Bench | Centre, m | Facing | Knee envelope, m | Achieved / required |
|---|---|---|---|---|
| Deck | (10.60, −22.10) | East, positive x, into central garden | (10.80244, −23.00, 11.40244, −21.20) | 0.600 m clear / 0.600 m ASSUMED design target |
| Roof | (14.00, −22.10) | West, negative x, into central garden | (13.19756, −23.00, 13.79756, −21.20) | 0.600 m clear / 0.600 m ASSUMED design target |

Both seats/slabs are off the study/gate path, and neither knee envelope is
blocked by actual planting or containers. Artificial grass forms the central
field with openings for study/gate paving and bench pads. Container edges and
plant faces stay inside their deck/roof outline clear of the retained 0.12 m
ASSUMED rail mounting strip. No rail is deleted or moved.

## Open decisions and technical limitations

- **Client colour:** dark bronze is the lead recommendation, ASSUMED pending
  client confirmation; no manufacturer coating or durability claim.
- **Supplier/engineer before ordering:** powder-coat weathering in Egyptian
  sun and fully loaded wet soil/plant/container weight on the deck are
  UNVERIFIED. Obtain the supplier data sheet and structural approval; no
  invented load capacity or weight is scheduled.
- **Local nursery:** Egypt performance, young sizes, pruning, container care,
  mature spread and root behaviour are UNVERIFIED. The shallow container
  geometry does not prove shallow roots. No deep-rooted planting is approved
  over the basement slab.
- **Waterproofing/drainage:** root penetration, blocked drainage and water
  retention threaten waterproofing over the basement slab. Nursery and
  waterproofing/structural consultants must confirm root control, membrane
  protection, drainage and irrigation; details are UNVERIFIED.
- **Shade tree:** the round-3 potted small shade tree remains unplaced/open
  because no verified top-zone species fits. A new verified palette entry
  and measured geometry are required before placement.
- **Lead photographic review:** trough finish, rosemary trailing habit, aloe
  rosettes and benches require isolated close-up draft review before scene
  integration. No Blender render was performed in this package.

## Preview, guards and handoff

Measured plan preview: `out/garden-g3-plan.png`, reproduced by
`scripts/garden_top_plan.py`, inspected on this workstation. Dashed leaf
outlines/hulls show actual botanical and imported plant extents. This is a
plan diagnostic, not a photoreal preview or approval.

The actual old top pot rim reaches x = 6.991 m, beyond the rail-clear boundary
x = 6.997 m, although its declared rectangle starts at 7.000 m. Frozen input
`tests/fixtures/garden-g3-before.json` reproduces that escaped physical-envelope
failure. New `top_garden_violations` checks built faces, measured assets,
rail/edge limits, deck contact, root seating, routes, slab seating and knee
space. Real and renamed rim failures, raised/sunk/edge/route troughs, trailing
plant blockers, absent slabs, wrong facing and translated/nonzero-datum
siblings prove failure, clean silence and generality. Build refuses conflicts.
`gate_route_violations` checks actual sloped-driveway triangles; independent
floor/coordinate and head-clear cases prevent a flat-floor substitution.

The first aloe construction collapsed its tip cap to a line. Actual frozen
`garden-g3-aloe-tip-before.json` fails physical geometry checks. Nonzero tip
thickness now prevents that class by construction; clean aloe/rosemary and a
renamed degenerate-leaf mutation prove the guard. All existing extent, object,
rail, spacing, drift, bed-layer, route, bench, stand-in, species, dimension,
unsupported and opening guards remain unconditional. Controls are registered
in `knowledge/mounting-guards.json`; learning and operating procedure were
updated together. Canonical skills are mounted read-only here.

The existing measured bench asset record was regenerated from the read-only
library with `scripts/generate_asset_route_geometry.py --assets sf_wooden_bench`.
It retains all 16,934 walking triangles and 156 framing hull vertices; permitted
maximum scene rounding error is 0.866025 mm. The tracked gzip record is
1,482,510 bytes, below the 1,500,000-byte budget. Scene build still reads only
`knowledge/asset-route-geometry.json.gz`, never the host library. The appearance
keeps its measured bounds/axes and CC Attribution credit. Existing Ixora asset
records are reused at the unchanged approved scale.

Both `v25-top-garden-gate` and `v26-top-garden-north` name actual top benches,
troughs and rosemary/aloe meshes, without marker aliases. Captions note
“trough colour: dark bronze, pending client confirmation”. V25 retains its
existing gate-approach camera. V26 moves only the camera to
(6.95, −23.20, 1.35), targeting (13.40, −21.80, 1.35), 24 mm, level, vertical
shift −0.10. Built vertices/hulls frame wholly and camera proximity is clear.
Design geometry is not moved for either camera. Both are final-only views:
the lead must render their own drafts before the final batch.

Whole-set review also found unchanged v27 only 0.521 m from the new second
Ixora against the retained 1.0 m lens-clearance requirement. The frozen
`garden-g3-v27-before.json` still fires. Only that camera moves to
(14.60, −22.10, 1.35), target (19.00, −21.80, 1.35), 24 mm level, vertical
shift −0.61. Subjects are the actual north back/mid/front planting strata
and trellis. All their vertices/hulls frame wholly; the caption explicitly
states the full soil-bed extent is outside the frame and points to v28 at
ground level. The proximity checker now also includes procedural top plant
and container meshes. No design moves for this follow-up; final-only v27
needs a lead draft and photographic sightline review as well.

## Validation

Commands use `/home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python`,
`PYTHONPATH=src`, `NO_COLOR=1`; results are judged by process exit status.
| Check | Result |
|---|---|
| Required landscape/render-standard/render-views/final-mounting/support-mounting/provenance/garden-subject modules, plus affected asset-route/physical-part/asset-intake modules | **175 tests, exit 0**, before camera-only v27 follow-up |
| Affected render-view and garden-subject modules after final camera/proximity correction | **19 tests, exit 0** |
| `scripts/verify.py --portable` after all source/registry changes | **exit 0, RESULT: ALL PASS** |
| Authoritative `VR.write()` (ordinary `VR.build`, no substitutions) | **exit 0**, scene contract and provenance stamped |
| `render_support.unsupported` on that authoritative final scene | **[]** |
| `render_support.blocked_openings` on that same scene | **[]** |
| `scripts/villa_render_views.py` on the final scene | **exit 0**, complete view-set framing/proximity and regenerated `views-plan.png` |
| `scripts/garden_top_plan.py` | **exit 0**, measured top-plan preview produced and inspected |
| `git diff --check` | **exit 0** |

Logs are `/tmp/garden-g3-focused-final.log`, `/tmp/garden-g3-camera-final.log`,
`/tmp/garden-g3-verify-handoff.log`, `/tmp/garden-g3-handoff-final.log` and
`/tmp/garden-g3-views-final.log`. The earlier 173-test run's sole missing
finish-registration failure is superseded by the 175-test passing run; its
real old finish-list failure and sibling mutation remain tested. The camera
follow-up changes only v27, adds equivalent procedural-mesh proximity checks,
and is independently rerun against the final views. The full view-plan preview
was inspected after regeneration. Passing geometry/tests does not close the
lead's photographic appearance/sightline review.
Shared `out/villa/round3` and `assets/user` were not modified; no package
installation, full-suite run, render, native-model modification or commit.
