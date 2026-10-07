# Garden G4c — balcony hanging retreat

2026-10-06. Client decision: “a, hang it from the north balcony”.
Implementation and independent neutral-preview review are complete; final
verification results follow below. No presentation renders or commit.

## Scope and construction status

The client's north garden is the street-side sunken court, retained in code
as `west`: x −0.373 to 3.617, y −29.916 to −23.591 metres. Coordinates x and y
are horizontal model axes; z is vertical and increases upward. Court ground
is z −3.0. GF means ground floor. The GF slab strip is over the house-facing
side of this garden; its measured soffit is z −0.2. Client street naming
remains distinct from true-north solar orientation.

The hanging point is (2.40, −24.77, −0.20), toward the end away from the
entrance platform and lounge passage. The basket faces model negative x,
into the foliage/stone/trellis garden, with Aspidistra behind it. The exported
placement states **“client decision 2026-10-06; structural check pending”**.

These are **OPEN CONSTRUCTION ITEMS, UNVERIFIED**, carried in the export:

| Item | Required authority |
|---|---|
| Balcony slab capacity for a dynamic hanging point load | Structural engineer |
| Anchor type, fixing and installation | Structural engineer |
| Chair rated load | Manufacturer |

The disc fixing plate and rope are authored appearances, not selected
hardware or an engineered connection. Geometrical support acceptance does
not establish load capacity. Soil depth, roots, waterproofing and drainage
retain G4's construction limitations.

## Chair source, intake and isolated review

A new **procedural basket** is used; no imported chair geometry, floor stand
or original imported chain is included. Source is
`src/archpipe/concept/garden_swing.py`: original project-authored geometry,
with no third-party mesh licence applicable and no standalone redistribution
grant asserted. It is an **ASSUMED look-alike proxy**, with no manufacturer
identity or rated-load claim.

For size comparison only, Blender imported the existing `sf_egg_chair` and
measured its separated basket-frame, wirework and cushion objects. The
basket union is 1.216 × 1.068 × 1.193 metres across/deep/high before placement.
The source model is “Hanging Egg Chair” by Average3DmodelEnjoyer, recorded
**CC Attribution** in `ops/workstation/library-manifest.json`:
https://sketchfab.com/3d-models/hanging-egg-chair-bfbf84c34eee467389c4feaddcef2023.
Source objects and measured bounds are in
`out/garden-g4c/asset-measurement.json`; the source file and library are intact.
Native glTF is Y-up; Blender imports it Z-up. The procedural basket is
metre-native, Z-up, with local positive y as the front; 90 degrees of
counterclockwise rotation about z makes it face negative x. No external asset
route record was changed or extrapolated.

Authored nominal basket dimensions are 1.20 metres across, 1.00 deep and
1.20 high, comparable to that measured basket. Actual bounds include round
cane thickness and the open front; nominal dimensions are not measured bounds.
Seat top is z −2.55, **ASSUMED 0.45 metres above court** so an adult can sit
with feet near ground; no published seat-height standard is claimed.
The cage bottom is derived from that seat relationship, 0.15 metres above
court. Nominal suspension length is **1.45 metres**, derived from the
z −0.2 soffit and z −1.65 nominal cage apex. The rope ends overlap the cage
and plate; actual cane/plate thickness is measured independently.

Neutral Blender close-up with a 1.8 metre scale reference:
[chair preview](../out/garden-g4c/hanging-chair.png). Independent render critic
review precedes integration. First previews exposed a seat below the cage,
then cushions floating inside it. The final builder includes a crossbar at
actual cage nodes and a back brace meeting the pillow. Guards use physical
underside/rear vertices inside/on closed bearing solids and actual cage-face
joints. Frozen failures, displaced bearings, raised cushions and reordered
faces are retained in `tests/test_garden_g4c.py`. All new curved faces are
triangulated; no planarity tolerance was relaxed.

## Every retained design move

Positions are metres. Counts, species, young managed dimensions and the
existing spacing, layer and 3–5-member drift guards remain in force. Only
this court changes; retained other-garden hashes are checked by G4 tests.

| Item | G4 position/extent | G4c final position/extent | Design reason |
|---|---|---|---|
| Third Fatsia, `west-back-02` | (2.80, −27.70) | (1.10, −24.50) | Dense broad-leaf layer beside/forward of the retreat; screens blank boundary in seated field |
| Third Aspidistra, `west-mid-02` | (2.80, −28.25) | (3.40, −24.17) | Green behind basket, beyond its motion envelope and outside full lounge opening |
| Rhapis accent | (1.20, −24.65) | (1.02, −24.65) | Green beside seat; keep motion and assumed root/path/wall clearance |
| Feature stone | (2.65, −24.05) | (1.02, −24.16) | Move into garden-facing seat cone, clear motion and actual boundary thickness |
| Accent soil bed: min/max x/y | (0.50, −25.20, 1.90, −24.10) | (0.05, −25.20, 1.60, −23.86) | Ground-level soil around the layered enclosure, clear walking stones and motion |
| Rear soil bed | Absent | (3.18, −24.39, 3.61, −23.92) | Ground-level soil for rear Aspidistra |
| Hanging chair | Omitted | Point (2.40, −24.77), facing negative x | Client-authorised retreat below real balcony |

Other Fatsia/Aspidistra, all Chlorophytum/Ophiopogon, trellis/grape ivy and the
main bed retain their positions. No design was moved for a camera. Gravel
and soil/edging boundaries are rebuilt from these authored extents; competing
paving caps are retired at the actual soil contours, keeping soil at z −3.0.

Rejected intermediate candidates are diagnosis, not retained moves:
three Aspidistra behind the first chair entered the full glazed opening;
one Fatsia at (0.75, −25.45), then (0.50, −25.42), entered or crowded the
walking strip; subsequent (0.50, −24.30) screening was insufficient from the
final seat point. A bounded foliage test rejected (0.65, −24.55),
(0.75, −24.55), (0.90, −24.55), accepting (1.10, −24.50). Earlier rear-bed
extent (3.18, −25.49, 3.61, −24.05) and accent-bed lower edge −25.95 are
retired: the latter overlaid walking stones, reproduced in
`tests/fixtures/garden-g4c-soil-before.json`. Initial stone y −24.03 was
corrected to −24.16 to clear the actual wall. The chair was initially checked
at y −24.84/−24.83/−24.71; final y −24.77 balances wall and route motion
clearance. These changes serve seating/planting/physical clearance.

## Guards and explicitly defined cones

The motion envelope is the measured basket/cushion horizontal bounds,
enlarged by **ASSUMED 0.25 metres on every side**. The existing
`swing_violations` arithmetic checks it against beds, planting, trellis,
measured boundaries and all D2 walking envelopes (D2 is the existing villa
circulation review). The final scene independently intersects the vertical
motion volume with actual shell/column triangles. Anchor fixing vertices
must lie on a live downward-facing balcony soffit polygon, through the C4
finished-surface mounting API; C4 names this project's mounting work package.
Rope, plate, cage and cushions also need physical connections.

Final measured motion rectangle is x 1.790 to 3.159, y −25.635 to
−23.905 metres. Against the actual inner boundary and walking envelope it
retains about 0.064 metres beyond the assumed motion allowance; rear soil
starts at x 3.180, about 0.021 metres beyond that envelope. These are model
clearances, not construction tolerances or a dynamic-use certification.
The actual host is `shell-000-ceiling-white`, a live downward face at
z −0.2 over x 1.787–3.617 and y −28.671–−23.591. The whole 0.09 metre
diameter fixing footprint lies on it. Actual cage bounds are x 2.385–2.909,
y −25.385–−24.155, z −2.865–−1.635; rope z −1.660–−0.210 and plate
z −0.220–−0.200 have physical overlap at both ends. Exact bounds and
independent face/material equality of final versus reviewed geometry are in
`out/garden-g4c/final-measurement.json` (1,024 meshes, 40 props, 121 lights).

The lounge has one full-height glazed garden opening serving as its shared
window/door prospect. Its measured centre is (3.617, −26.156). The lounge
view cone is a horizontal finite sector from that centre toward court centre
(1.622, −26.7535), ending at that centre's distance, with **ASSUMED 18 degree
half angle**. Basket/cushion bounds must not intersect this sector. This is
an authored central-prospect criterion, not a published view standard.
A real chair mutation moved to (3.0, −26.156) must fail it.

Seat eye point is (2.40, −24.77, −1.80): **ASSUMED 1.20 metres above court**,
0.75 above the seat, for a seated-adult view screen. The horizontal cone
faces negative x with **ASSUMED 35 degree half angle**. Actual rays to the
feature stone and foliage must first hit those target meshes. The central
field samples horizontal angles −12, −6, 0, 6, 12 degrees and elevations
−10, 0, 10 degrees, all relative to that front. **ASSUMED majority-field
criterion:** a wall, column or loose furniture may not occupy more than half
of these 15 first-hit samples. Sparse boundary between leaves is disclosed;
this does not claim an entirely vegetation-filled image. The open planted
trellis is garden content. Turning the physical chair 180 degrees toward
positive x/the house must fail stone visibility and this field check.
The clean field has 8 planting/trellis and 7 boundary first hits; the rotated
field has 15 obstructed hits. These are the actual reported limits.
The cone checks prove this bounded geometric screen, not subjective relaxation.

Mutations and cone records are reproducible with
`scripts/garden_g4c_proof.py`, with results in
`out/garden-g4c/mutation-proof.json`. Guards run unconditionally in candidate,
scene construction, exported contract and portable verification as applicable.
The learning registry and [garden rebuild workflow](ops/garden-rebuild.md)
carry these controls.

## Views and final acceptance

v36 retains its open-sky left-bed view; the swing is behind that camera's
current field. New **v39-north-garden-hanging-retreat** shows the basket and
cushions at 24 mm, level eye z −1.65, camera (1.75, −26.20) in actual open sky.
Plate/upper rope extend above this basket view and the caption says so;
the isolated close-up records the whole suspension. v37 includes the moved
Fatsia with the trellis/Rhapis/stone. Its camera moves from (5.35, −25.45,
−1.65) to (4.00, −27.40, −1.65), keeping target, 24 mm lens and shift fixed;
the restored basket obscured the subjects from the former point. Sorted
unique actual target vertices supply 12 evenly indexed samples plus the
bounding centre. ASSUMED majority first-hit visibility (at least 7/13) is
required for the stone, Rhapis and moved Fatsia: clean counts 8/13, 12/13,
13/13; the actual former view fails all three although framing passed.
Transparent glazing, diagnostic and surface-datum meshes do not occlude in
this screen; imported props/glass appearance and aesthetics need the actual
preview review, which the independent critic performed. A renamed/translated
real sibling fails, clean/reordered geometry stays quiet. No standard or
projected-area visibility claim is made. The new rear soil also gets its own
`landscape-soil-` identifier, avoiding accidental main-bed subject matching.
v38 keeps its camera and shows the main
bed and retained members; its caption discloses relocated members and the
existing partly screened corner. Plant appearances, procurement and Egypt
performance remain ASSUMED/UNVERIFIED as in G4.

Independent context critic accepted the corrected v37, refreshed v39, and
[actual-seat-eye diagnostic](../out/garden-g4c/seat-g4c-neutral.png) with the
stone visible at a narrow lower margin. The
[critic record](../out/garden-g4c/critic-review.md) records that bounded
acceptance; final actual faces/materials and the corrected camera match the
reviewed preview.
[Through-lounge diagnostic](../out/garden-g4c/v37-g4c-neutral.png) and
[retreat diagnostic](../out/garden-g4c/v39-g4c-neutral.png) use neutral
Blender lighting, with no presentation-light recipe or quality approval.

Final acceptance: **PASS**, exit status 0 for each completed command below.

| Check | Result / evidence in `out/garden-g4c` |
|---|---|
| Focused landscape, G4/G4c, render standard/views, final/support mounting, provenance, garden subjects, asset route geometry | 162 tests pass, `focused-final-pass.log` (741.380 seconds) |
| `scripts/verify.py --portable`, normal environment, `NO_COLOR=1` | Exit 0, `verify-final-pass.log` |
| Same verifier, fresh empty HOME (TemporaryDirectory; asserted empty before launch) | Exit 0, `verify-empty-fresh-pass.log`, `empty-home-evidence.json` |
| Current source export and authoritative acceptance | Exit 0; `unsupported == []`, `blocked_openings == []`; mounting/swing/soil/contract/frame/proximity findings also empty; current source hash matches; `acceptance.json` |
| Actual chair before lounge opening / actual seat rotated to house | Required failures reproduced; clean scene quiet; exit 0, `mutation-proof.json` |
| Existing complete view-plan checker, redirected to this isolated export folder | Exit 0, `views-plan-final.log` / `views-plan.png` |
| Reviewed preview versus final actual geometry/camera | Exact decoded face/material hashes and corrected camera match; exit 0, `final-measurement.json` |

All Python commands use `/home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python`
with `PYTHONPATH=src`; the view-plan module invocation additionally makes
repository scripts importable. Focused test modules: `test_landscape`,
`test_garden_g4`, `test_garden_g4c`, `test_render_standard`, `test_render_views`,
`test_final_mounting`, `test_support_mounting`, `test_villa_scene_provenance`,
`test_garden_render_subjects`, `test_asset_route_geometry`. Git diff whitespace
check is clean. Exit receipts are collected in `exit-statuses.json`.

The earlier nominal empty-HOME run reused a directory that had acquired a
cache; only the fresh asserted-empty run above is the final evidence. An
initial preview-camera comparison helper also selected the wrong view;
identifier-map selection and asserted matching identifiers fix it, retaining
`measurement-before.log` as diagnostic history. Neither changed the design.
The lead owns the full suite and commit. `assets/user` and
`out/villa/round3`, including shared targets, remain untouched. No packages
are installed and no presentation image or native-model approval is claimed.
