# Furniture phase, step 1: beds

**Round 6 client decision, 2026-10-09: keep the layout and use slim frames.**
The mattress scaling rule remains unchanged; frame parts receive their own
plan factors. No downloaded bed is activated after the round-6 checks below.

**Round 5 client decision, 2026-10-09: bounded model scaling is permitted.**
Cyberfox parents and sparshgupta ladder bunk fit the exact planned mattress
sizes with eligible plan factors, and their generated cloth passes actual
model clearance. Both fail unchanged room checks; the bunk also misses its
upper design height. No kids B candidate has a verified eligible scale fit.
Retain the procedural beds pending those failures; the library daybed stays
procedural. Full round-5 measurements, neutral previews and checks are below.

**Round 4 decision: retain the labelled procedural beds.** All seven new
downloads fail source-size mattress dimensions or complete identification.
No replacement is integrated. Exact measurements and reviewed neutral previews
are recorded in the round-4 section below.

**Round 3 decision (client source: 2026-10-08): real-size beds only.**
All five downloaded candidates fail actual mattress size or identification.
All four labelled procedural fallbacks remain; no replacement is integrated.
The new download shortlist is in `docs/beds-candidates-round3.json`.

**Historical round 2 decision: retain all four labelled procedural beds.** All five
downloaded candidates were measured and reviewed; each fails its fixed
envelope. Importer/cloth/model-topology capability changes are implemented
and demonstrated separately. See the round-2 evidence below.

The following round-1 record is historical. Authentication is now resolved
by the lead's authorized downloads; no token was accessed in this worktree.

**Round 1: replacement acceptance was blocked; no replacement integrated.**
The cached free model fails the fixed footprint and height requirements.
Five alternatives require authenticated downloads (HTTP 401); the expected
`sketchfab-api.txt` is absent from this worktree and a filename search of the
workstation found none. A token-path question is pending; no token was printed,
copied or created, and no login/password was used.

Branch: `codex/beds`, from the existing integration worktree. No commit.
Lighting, `revit_spec`, `guard_registry.py` and its tests are untouched.
`assets/user` and `out/villa/round3` were not modified. All preview/output work
is under this worktree's `out/beds`.

D1 is the current villa layout option. C2 is the existing asset-intake control;
C4 is finished-face mounting; C8 is geometry-topology review. glTF means GL
Transmission Format, the model-file format used by the existing importer.

## Existing beds retained

All four beds are explicitly **procedural fallback stand-ins**, not real products.
Their source is the existing authored scene builders; model source URL,
licence and external author are not applicable to these generated shapes.
Scale is 1.0 because their actual scene coordinates already use metres.
Bounds below come from every actual bed-mesh vertex, including the daybed's
joinery surround, in the rebuilt D1 scene. Finished floor is 0.002 m on the
upper floor and −2.998 m on the basement; all bed roots use those physical datums.

| Bed / room | Preserved footprint (m) | Measured world bounds: minimum → maximum (m) | Overall height / mattress top above finished floor (m) |
|---|---|---|---|
| `pb-bed`, parents | 1.600 × 2.000 | (19.530, −26.591, 0.002) → (21.130, −24.591, 1.052) | 1.050 / 0.525 |
| `kb-bed`, kids B | 1.200 × 2.000, rotated −90° | (15.002, −25.900, 0.002) → (17.002, −24.700, 0.952) | 0.950 / 0.475 |
| `ka-bunk`, kids A | 0.900 × 2.000 | (11.527, −26.450, 0.002) → (12.427, −24.450, 1.702) | 1.700 / lower 0.400, upper 1.400 |
| `library-daybed`, library alcove | 2.000 × 0.950 | (18.668, −29.716, −2.998) → (20.668, −28.766, −0.898) | surround 2.100 / mattress 0.450 |

No guest bed or sofa bed exists in D1. The daybed's surround remains architectural
joinery; any mattress/model replacement must retain its fixed envelope.
`catalogue.py` defines bed widths, depths and access clearances, **no mattress-top
height range**. The heights above are measured authored values, not a claimed
published catalogue range. That requested acceptance item needs an explicit
height-range source/decision before a model can be approved.

Existing cloth duvets and the parents' throw are simulated against unchanged
procedural mattress geometry in the diagnostic images. The library daybed has
its existing mattress/cushions and no authored duvet. No cloth/model intersection
claim is made for an unavailable replacement.

## Rejected measured model

[Chelsea bed with storage](https://sketchfab.com/3d-models/chelsea-bed-with-storage-3d-model-cbe6e0dcc10a414a84acc5cc08171b87),
by **bertosalotti**, **CC Attribution (CC-BY)**. Credit remains in the asset
manifest. This is a manufacturer-authored product appearance, retained as a
rejected stand-in candidate; it is not the specified D1 bed.

C2 asset intake measures native glTF bounds (X across, Y up, Z length):
minimum (−0.980064988, 0.000451000, −1.064903975), maximum
(0.994147003, 1.054821014, 1.205989003) metres. Extents:
**1.974211991 × 1.054370014 × 2.270892978 m** in that native axis order.
Up axis +Y, front +Z; front statistics and the cached preview agree that the
headboard occupies the opposite end. Unit conversion is 1.0. Actual indexed
geometry contains **105,298 triangles and 56,112 position vertices**; every
referenced texture exists. Buffer and texture hashes are in
`out/beds/chelsea-intake.json`; frozen source/buffer measurements are in
`tests/fixtures/bed-chelsea-measured-rejection.json`.

Best uniform scale into parents' unchanged envelope: **0.8104499453094023**.
Result: **1.600000 × 1.840445 × 0.854514 m** (width, depth, overall height).
Depth misses by **159.555 mm**, versus allowed 20 mm; overall height misses the
existing 1.050 m headboard envelope by **18.618%**, versus allowed five percent.
Independent width/depth/height scaling would distort the real mesh and is refused.
C2 additionally reports height/depth outside the manifest's manufacturer-cited
0.95–1.03 m / 2.14–2.24 m ranges. Those discrepancies remain failures, not an
override or a corrected scale. Rejection reasons: footprint, height and
manufacturer-range disagreement. No selection or layout change.

## Download candidates for the lead

Sketchfab and API robots.txt permit the queried public model/API paths.
Poly Haven robots/API requests returned HTTP 403, so no direct download was
attempted. Its public [bed catalogue](https://polyhaven.com/models/furniture/beds)
lists Gothic Bed, Old Bed Frame and Vintage Day Bed; those appearance listings
were screened out for the requested warm minimal / Scandinavian bedroom styles.
They were not downloaded or measured and carry no geometric rejection claim.

The following API records were checked for CC Attribution and downloadable
status. All download endpoints returned HTTP 401 without a token. Bounds,
units, axes, scale and texture quality remain **unmeasured**; none enters the
manifest or scene as an accepted asset. API evidence:
`out/beds/download-candidates.json`.

| Candidate | Author | Source | Next action |
|---|---|---|---|
| Upholstered Bed / Free model | cyberfox3d | [Sketchfab](https://sketchfab.com/3d-models/7602267cc32e4caf8c92c60b677539be) | Parents candidate; authorized download, measure, fit and review |
| Simple wooden bunk bed | 3DWorkbench | [Sketchfab](https://sketchfab.com/3d-models/a7685bd7b2354157b4c1a8264892acf0) | Kids A candidate; same checks, including ladder and both mattresses |
| Home Series – Bunk Bed | spazio_silvestre | [Sketchfab](https://sketchfab.com/3d-models/2ba8ccae518d4dc1be00dcdff0d4ac01) | Alternate kids A candidate; style remains pending preview |
| Bed FORSSA | leonardgraylar | [Sketchfab](https://sketchfab.com/3d-models/0e4ec2bb5aff42d8a324b3f8ab9ac9de) | Screen actual width/height/style for kids B after download |
| Stained Bare Scandinavian Bed | JudeNavarre | [Sketchfab](https://sketchfab.com/3d-models/3af9fc8452ca4c1180ce9ae7a9600b79) | Screen timber/bedding/geometry after download |

## Neutral previews

Blender 4.5.14, 32 samples, white world and separately recorded 500 W neutral
softbox, design lights absent, emission disabled, production glass interfaces
retained. Isolated views include a measured 1.8 m scale figure. In-room views
preserve the existing camera; they show actual architecture and room furniture,
with incidental props/curtains omitted as recorded in the receipt. These are
**diagnostic fallback/rejection previews**, not presentation images or approved
replacement previews.

| Bed | Isolated preview | Existing-camera room preview |
|---|---|---|
| Parents | `out/beds/previews-after/pb-bed-isolated-neutral.png` | `out/beds/previews-after/pb-bed-room-neutral.png`, `v22-parents-day` |
| Kids B | `out/beds/previews-after/kb-bed-isolated-neutral.png` | `out/beds/previews-after/kb-bed-room-neutral.png`, `v13-kids-b` |
| Kids A | `out/beds/previews-after/ka-bunk-isolated-neutral.png` | `out/beds/previews-after/ka-bunk-room-neutral.png`, `v06-kids-room` |
| Library | `out/beds/previews-after/library-daybed-isolated-neutral.png` | `out/beds/previews-after/library-daybed-room-neutral.png`, `v24-bar-alcove` |
| Rejected Chelsea | `out/beds/previews-after/chelsea-rejected-native-isolated-neutral.png`, native scale 1.0 | None: fit is refused before placement |

Receipts: `out/beds/previews-after/evidence.json`. Independent review:
`out/beds/preview-review.md`. Existing parents/kids views crop bed bottoms;
isolated images provide whole-bed diagnostic coverage. Chelsea's rear-facing
isolate shows native size/headboard but is insufficient for bedding/style
approval; numerical rejection already prevents its selection.

The first disclosure fix changed `label`, which broke built-subject lookup.
The initial attribution of the parent crop to changed camera placement was
incorrect: measured before/after camera records are identical. Corrected
`fallback_label` / `asset_status` preserve subject identity; before images and
labels are retained separately for regression evidence.

## Changes and verification

`archpipe.beds` enforces absolute footprint and height tolerances, detects
axiswise distortion independently of box fit, rejects missing/nonfinite bounds
and preserves fallback subject labels. Beds no longer inherit the selected
product's unconditional `ok=True` override. C2 manifest records are measured;
wrong manufacturer ranges remain flagged. New tests use frozen real Chelsea
bounds and `tests/fixtures/bed-real-distortion.json`: all 105,298 actual
indexed triangles remeasured after independent root-node axis scaling in
`out/beds/distorted-case/model.gltf`. The diagnostic references the original
read-only buffers/textures; it never edits or integrates the source asset.
They cover the distorted measured case, translated/rotated siblings,
clean mechanical controls and the actual furnished D1 fallbacks.

Portable verification completed with **exit 0, 159 passing checks** in both
normal and empty HOME. Logs: `out/beds/verify-portable-final.log` and
`out/beds/verify-empty-home-final.log`. The focused batch completed with
**exit 0, 171 tests**: `test_beds`, `test_villa_furnish`, `test_render_standard`,
`test_render_views`, `test_geometry_topology` and `test_asset_intake`.
Receipt: `out/tests-result.json`; log: `out/beds/focused-tests.log`.
The earlier normal-HOME verification
failed an over-strict label assertion that omitted pillow label suffixes;
the final check preserves full existing labels and requires explicit status.
The real-triangle distortion fixture was refined while the batch was running;
the final eight fit tests were rerun separately, **exit 0**
(`out/beds/bed-fit-final.log`).
No full-suite claim; the lead owns that run.

At the end of round 1, production cloth still simulated before model import
and C8 did not directly review model instances. Those consumer gaps are now
implemented and demonstrated in round 2 below. No accepted D1 replacement
exists; any future fitting candidate still needs its own in-room cloth, support
and route acceptance. Workflow: [bed intake and review](ops/beds.md).

## Lessons to register

- `beds-selection-fit-bypass`: product selection must not override fixed bed
  envelope checks; registered data/proofs in `knowledge/bed-guards.json`.
- `beds-fallback-subject-identity`: disclosure must preserve identity-based
  subject lookup; real frozen labels, renamed/idempotent proofs and diagnostic
  review. Registered data/proofs in the same file.
- `beds-library-fallback-appearance`: newly observed member-level grain mapping
  collapse, captured by value, **unresolved**; no remedy/guard closure claimed.
- Central Python registry adapters remain for **agy**, who owns those files.
  No new lesson is represented as closed imported-replacement acceptance.
- Existing context crops and library fallback appearance limitations remain
  diagnostic observations, not an authorization to change the layout, cameras
  or joinery during this phase.


## Round 2 — downloaded candidates, retained beds and importer proof

The existing shared asset folders added in the stopped run are retained under
`/home/omar/archpipe/assets/library/props/<id>/`. Every inbox file was checked
byte-for-byte against its corresponding shared copy, including provenance,
licence and textures. `model.gltf` is the existing importer-compatible copy of
`scene.gltf`; both originals remain. No existing unrelated library folder,
`assets/user`, or `out/villa/round3` was modified. Full CC-BY credit from each
`license.txt` and source author/URL are in `ops/workstation/library-manifest.json`.
No source texture/normal repair or axiswise stretch was applied. These are
appearance candidates, without a verified purchasable specification.

### Per-bed decisions

| Bed | Chosen replacement | Preserved footprint / overall height (m) | Retained scale and evidence |
|---|---|---|---|
| Parents, `pb-bed` | None; labelled procedural fallback | 1.600 × 2.000 / 1.050 | 1.0; `round2/retained-previews/pb-bed-isolated-neutral.png` and `pb-bed-room-neutral.png` |
| Kids A, `ka-bunk` | None; labelled procedural fallback | 0.900 × 2.000 / 1.700 | 1.0; `round2/retained-previews/ka-bunk-isolated-neutral.png` and `ka-bunk-room-neutral.png` |
| Kids B, `kb-bed` | None; labelled procedural fallback | 1.200 × 2.000 / 0.950 | 1.0; `round2/retained-previews/kb-bed-isolated-neutral.png` and `kb-bed-room-neutral.png` |
| Library, `library-daybed` | Procedural daybed/joinery retained | 2.000 × 0.950 / surround 2.100 | 1.0; `round2/retained-previews/library-daybed-isolated-neutral.png` and `library-daybed-room-neutral.png` |

Paths in this section are relative to `out/beds/`. Retained world bounds and
mattress datums remain the round-1 measured values above. Fresh Blender previews
use the identical source `scene-fixed.json` and existing cameras: parents
`v22-parents-day`, kids A `v06-kids-room`, kids B `v13-kids-b`, library
`v24-bar-alcove`. No rejected candidate is placed into a room. All five also fail the daybed's
0.950 × 2.000 m footprint screen; `round2/library-screen.json` records
that secondary rejection. The architectural surround is retained.

### Measurements and rejections

Native glTF bounds use X across the file, Y up, Z horizontal; they are not
assumed semantic width/length. Each listed multiplier applies uniformly to
all axes. Fitted sizes use semantic width × length × overall height.
Client fit limits remain 20 mm per footprint dimension and five percent
overall height. Those are task requirements, not catalogue rules.

| Candidate / author | Actual native minimum → maximum (m) | Uniform scale; fitted size (m) | Rejection |
| `sf_bed_forssa`, leonardgraylar | (-1.190037, -0.005809, -1.491849) → (1.208580, 1.099827, 0.683258) | 0.500288250; 1.200000 × 1.088180 × 0.553137 | Depth short 911.820 mm; height short 41.775%. Credible upholstered double bed, unsuitable proportions for fixed kids B width. |
| `sf_bed_scandi_bare`, JudeNavarre | (-2.164110, 0.017163, -1.304135) → (2.283993, 1.317585, 1.225815) | 0.449629908; 1.137541 × 2.000000 × 0.584709 | Width short 62.459 mm; height short 38.452%. Baked brown mattress stains and no required headboard; reject without retouching. |
| `sf_bed_upholstered_cyberfox`, cyberfox3d | (-1.050000, -0.000146, -1.284404) → (1.197053, 1.506506, 1.270896) | 0.626149601; 1.600000 × 1.406992 × 0.943389 | Depth short 593.008 mm; height short 10.153%. Best upholstery appearance, but fixed footprint fails. Broad source duvet folds remain stylized. |
| `sf_bunk_home_series`, spazio_silvestre | (-1.792738, -0.030531, -3.311194) → (3.377335, 6.922248, 3.376924) | 0.174078795; 0.900000 × 1.164259 × 1.210331 | Depth short 835.741 mm; height short 28.804%. Ladder is part of full envelope. Black glossy bedding/couch-like lower dressing are style reservations. Lower head/foot unresolved. |
| `sf_bunk_simple_3dworkbench`, 3DWorkbench | (-7.674592, -1.000000, -6.464382) → (11.292938, 10.400000, 5.749197) | 0.073688471; 0.900000 × 1.397688 × 0.840049 | Depth short 602.312 mm; height short 50.585%. Stylized solid panels/basic bedding; no visible ladder. Open-side direction does not establish a ladder route. |

Exact indexed triangle counts: FORSSA 94,044; Scandi 1,160; Cyberfox 29,358;
Home Series 208,464; simple bunk 19,326. Every referenced buffer/texture exists;
no obvious broken normals or missing-texture symptom was found in the neutral
review. Each `<id>-intake.json` contains actual vertices/bounds, conservative
accessor envelopes, hashes and C2 violations. Missing published expected-size
ranges and library-local preview entries remain explicit C2 failures;
repo-local neutral previews are separately referenced. No fake catalogue range,
size override, procurement identity or complete intake pass is claimed.

### Lead-verifiable front/access evidence

`round2/axes-measured.json` is reproducible with `scripts/bed_axis_evidence.py`
from unchanged `round2/geometry/*.json.gz` receipts; those receipts carry all
source hashes and actual imported faces. X/Z refer to native glTF, Y is up.
The script measures end bands covering ten percent of each horizontal extent
(an authored diagnostic statistic), upper twenty-percent vertices and connected
pillow components welded at 0.01 mm position precision. It does not guess a
semantic front from symmetric bounds. The reviewed part interpretation is:

- Cyberfox: head at +X, foot −X. Tall headboard vertices occupy X 1.050701 to
  1.195498 m, spanning Z −0.991287 to 0.980353 m. The provisional +Z axis in
  the first interrupted-run preview was wrong. Corrected fit and previews
  supersede it; original evidence is retained.
- FORSSA: head −Z, foot +Z. Headboard parts `Plane003` / `Shape014` occupy
  Z −1.491849 to −1.382881 m; main pillows lie toward −Z.
- Scandi: head −X, foot +X. Pillow `Object_12` occupies X −1.9848 to −1.0247 m.
- Home Series: length Z; upper head +Z, upper foot −Z; access +X. Two upper
  pillow components occupy Z 1.013 to 3.078 m and Y 5.813 to 6.671 m. Mattress
  width ends at X ±1.5797 m; the ladder/frame extends to X 3.3773 m. Lower
  pillow components occupy both ends, so lower direction is explicitly
  unresolved. No common automatic front-axis estimate is accepted for it.
- Simple bunk: length X; head −X, foot +X; open long side +Z. The low-X end
  band reaches Y 10.4000 m, versus 2.8300 m at the high-X end, consistent with
  the neutral silhouette. No ladder component is identified; +Z records the
  open-side approach only, not a proven ladder route.

The manifest's `front_axis` records head-to-foot; `length_axis` and
`orientation_evidence.access_axis` are separate. Home Series front applies
to the upper bed only. This is measured evidence for lead verification,
not a claim of lead approval or bunk safety compliance.

### Neutral evidence and visible limits

All five corrected isolates include a 1.8 m figure and opposing views:
`round2/candidates-preview-corrected/<id>-plus-y.png` and `<id>-minus-y.png`.
Filename sides are Blender camera directions, not source bed-front labels.
The staging floor sits 5 mm below each actual lowest vertex, and the figure's
foot datum matches that vertex height. Actual vertices replace transformed
local boxes for contact/centering. Original wrong-scale Cyberfox and floating
Home Series diagnostics remain preserved in `round2/candidates-preview`.

Independent review: `round2/preview-review-final.md`; all 19 corrected-candidate,
retained-bed and mechanical-cloth images were inspected at original resolution.
It confirms grounded isolates and rejection decisions. Existing parents camera
crops three of four floor-level footprint corners; kids cameras crop two each.
Library context contains the daybed. Isolated previews provide full-bed coverage.
Existing library joinery grain/black-patch observations remain unresolved,
as documented in round 1. No design geometry or camera was moved to conceal
a defect. These images are neutral diagnostics; no presentation images were
rendered. Design emitters/material emission are disabled and the separately
recorded neutral softbox is 500 W.

### Importer, duvet and C8 capability proof

Implemented step 5: whole models import before cloth; actual mattress part
bindings drive duvet cut/top; every real part collides; procedural replacement
parts are excluded; bed decimation is disabled. Lower/upper bunk bindings
require separate names and measured directions. Activating a fitting bed
requires actual geometry plus accepted neutral review bound to unchanged
source hashes/orientation. Pending/rejected review fails closed.

C8 and render_support now consume transformed model faces. Repeated expansion
is idempotent; original faces remain immutable. Missing files restore visible
labelled physical fallback in the whole-model importer, and runtime fallback
status keeps C8 on those retained faces. Legacy non-bed models gain conservative
route envelopes, without a new exact-support claim. The initially reused prop
origin shifted FORSSA's legacy review box; a frozen real-case regression
reproduced it, and the envelope now follows the whole-model centred/floor-seated
placement convention. Rotated/translated controls pass.

`round2/importer-proof.json` demonstrates the rejected Scandi asset at its own
mechanical envelope, scale 0.45, using actual mattress `Object_14` and all seven
real meshes. The evaluated duvet has **zero surface crossings, zero enclosed
vertices, minimum distance 4.916925 mm**, 23,322 evaluated vertices versus
1,160 model triangles. A crossing plane and translated sibling each produce
six crossings; a contained sheet produces nine enclosed vertices; the clean
sheet stays quiet. Portable and Blender instance bounds agree within
0.000036 mm. Missing-file physical fallback passes. The harness mocks only
C2 registration to exercise this rejected asset; production gates are never
bypassed. This is capability evidence, not replacement acceptance for D1.

Preview: `round2/mechanical-scandi-cloth-neutral.png`. The independent reviewer
finds no gross penetration, grounded feet and side/foot drape; a raised head
fold and original mattress stains remain visible. Tests on frozen actual
Scandi faces show C8 floor support and an unobstructed route pass, while
lifted, rotated and route-obstructing cases fire. Frozen FORSSA mattress faces
prove the measured cut and translated/rotated sibling; separate bunk bindings
fail when either mattress direction is unresolved. No D1 imported bed passes
acceptance because none passes fit. Library has no authored duvet.

### Verification

Portable verification finished with **exit 0, 159 checks, ALL PASS**; the final ten
model regressions finished with **exit 0**. The affected focused batch finished with **exit 0, 178 tests**. Results
are recorded
in `round2/focused-tests.log`, `round2/model-tests-final.log` and
`round2/verify-final.log`. After the final legacy-envelope correction, the
actual furnished-scene support/routes/bed-swing test also finished with
**exit 0** (`round2/centred-envelope-scene-test.log`). Blender importer/cloth proof and all neutral
preview runs complete with exit 0. The first portable process terminated with
exit 143 before a result; its failed log is retained, and a fresh run uses
unbuffered output. No full-suite or native Revit acceptance claim is made;
this task changes rendering/import review, and the lead owns the full suite.
No commit. Round-1 edits are retained. Lessons, bed guard registration and the
operating workflow were updated together. Canonical `.agents` files were not
edited, so adapter regeneration is not required.


## Round 3 — real-size mattress rule

Source: **client decision 2026-10-08**. Execution resumed on 2026-10-09
from the interrupted run's uncommitted edits and evidence. Round-1/2 records
above are historical; their whole-model footprint/height fitting rule is
superseded. No fit scale is permitted. glTF coordinates use metres unless
source evidence explicitly declares another unit ([glTF 2.0, coordinate
system and units](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#coordinate-system-and-units)); the source-unit conversion
is computed, never inferred from a desired bed size. Original FBX dimensions
in centimetres do not by themselves authorize shrinking a glTF export.
The unit keys `m`, `cm`, `mm`, `ft` and `in` mean metres, centimetres,
millimetres, feet and inches respectively. FBX is the original model-file
format named by the listing; a glTF export has its own unit contract.

Actual mattress dimensions, not the frame box, must match parents
1.600 × 2.000 m, kids A 0.900 × 2.000 m **per berth**, and kids B
1.200 × 2.000 m within 20 mm in each dimension. A frame/headboard may extend
outside these dimensions. Separate accessory meshes can be omitted only
with a recorded bed-only contents review. Actual mattress centre, existing
head direction, layout and cameras remain fixed; the frame is seated at the
existing finished floor. All other items remain untouched.

### Re-evaluation of the five cached candidates

`scripts/recheck_beds_round3.py` rechecks the unchanged source/buffer/texture
hashes and measures actual round-2 imported faces. Full receipt:
`out/beds/round3/recheck.json`. All units below are metres; width precedes
length. Every old round-2 fit scale is explicitly refused as a scaled bed.

| Candidate / intended bed | Actual mattress width × length at source size | Result against planned mattress |
|---|---|---|
| FORSSA / kids B | 2.014246 × 2.010975 | Width mismatch 814.246 mm; length within tolerance |
| Stained Bare Scandinavian / kids B | 2.412432 × 4.241483 | Width mismatch 1212.432 mm; length mismatch 2241.483 mm |
| Cyberfox upholstered / parents | 1.781747 × 1.999221 | Width mismatch 181.747 mm; length within tolerance |
| Home Series bunk / kids A | Both berths 3.159433 × 6.223846 | Per berth: width mismatch 2259.433 mm; length mismatch 4223.846 mm |
| Simple wooden bunk / kids A | Unresolved naked mattress geometry | Fused bedding/mattress surfaces; no verified ladder in inspected silhouette; refused |

FORSSA's named mattress and Scandi's existing mattress-cut mesh supply their
measurements. Cyberfox's mattress is a measured connected component inside
`Object_4`; it is not a production mesh binding. Its two imported meshes and
eleven connected components, together with the retained neutral silhouette,
show no bedside tables, benches or rugs to remove: **omitted meshes: none**.
The reviewed image is `out/beds/round2/candidates-preview-corrected/sf_bed_upholstered_cyberfox-plus-y.png`. Home Series'
two mattress components share one mesh; lower head direction remains
unresolved. No unit declaration permits correcting either oversized model.
Component measurement alone does not activate a fused candidate.

All five fail mattress intake, so no candidate reaches in-room acceptance.
No replacement is integrated and no passing-bed neutral previews are due.
Existing labelled procedural fallbacks and round-2 previews remain unchanged.
The library daybed has no new replacement candidate in this task.

### Construction, placement and room checks

`archpipe.beds` now computes source-unit-only scale, requires each actual
mattress, reviews retained bed-only meshes and binds acceptance to source
hashes, orientation, omissions, mattress selections and units. The same
mattress-centred transform drives portable geometry and Blender. Frame and
headboard dimensions no longer inherit the old 20 mm frame-edge or five
percent height limits. Actual Blender vertex read-back still rejects
axiswise distortion and displacement of the mattress centre.

C8 (geometry-topology review) consumes retained frame faces for contact,
collisions, room intrusion, passages and conservative door-swing envelopes,
and real frame envelopes for route/access review. `bed_room_review` reports
new frame-related findings with achieved, required, cited source and
signed difference, plus explicit metre-valued clearance shortfalls. It
compares against the existing scene; unrelated pre-existing findings are
not presented as bed-induced failures. It never modifies the authored layout.

Frozen real Scandi geometry at its own mattress dimensions exercises another
room: **441.241 mm achieved against 750 mm required, shortfall 308.759 mm**;
the larger-room control passes. Source re-read on 2026-10-09: UK Approved
Document M Volume 1, 2015 incorporating 2016 amendments, paragraph 2.25d,
printed p.18, one accessible side for each single/twin bed. Principal double
beds use paragraph 2.25b; other double beds use 2.25c. Storage-front screening
uses Time-Saver Standards for Interior Design and Space Planning, 2nd edition,
printed p.87: 36 inches (the existing verified card rounds this to 914 mm).
These are the project's adopted planning guidance, not an Egyptian code claim.

Door swings retain the existing conservative envelopes. Storage-front access
is screened; individual animated wardrobe-door/drawer travel requires
measured motion geometry and remains an explicit limitation. Geometric floor
contact does not establish structural capacity. No failed mattress candidate
is assigned an invented in-room clearance pass or shortfall.

### Cloth, collider and fallback evidence

Model-first import, actual mattress cuts, all retained frame/mattress/source
bedding colliders, evaluated cloth penetration refusal and physical
missing-file fallback remain in place. Interrupted-run real-size mechanical
Scandi read-back agrees with portable bounds within 0.0000001192 m; fallback
and clean/crossing/contained/translated collision probes pass. Its oversized
cloth stress case **fails**, with 1347 surface crossings and 2899 enclosed
vertices (`out/beds/round3/importer-proof.json`). It supplies no accepted
cloth preview. The old harness caught and recorded this failure but exited
zero. It now raises after writing evidence; a frozen real-failure regression,
renamed sibling and clean control prove propagation. No model, simulation
settings or collision tolerance was altered to turn that failure into a pass.

### New download shortlist

`docs/beds-candidates-round3.json` lists **two parents, three kids A and two
kids B** candidates, each with UID (Sketchfab unique model identifier), direct
URL, author, licence, downloadable status, stated dimensions when available,
style and bed-only screen, fit rationale and next gate. Public unauthenticated
API metadata for all seven was rechecked on 2026-10-09 against robots.txt;
raw receipts and the inspected listing contact sheet are in `out/beds/round3`.
No login, token or model download was used.

Modern bed is the primary upholstered parents lead; Dark Modern Bed is the
alternate and states an overall 214 × 200 × 90 cm model box, **not a mattress
size**. The kids A leads have visible ladders; the kids B leads have light-oak
forms. No eligible new listing states the required mattress dimensions;
paid 120×200 listings were excluded. None has a claimed numeric fit until
the lead downloads it and its actual source-size mattress is measured.
Bed-only mesh contents also remain pending download. Keep the neutral
isolated figure preview and unchanged-camera room preview as gates for any
candidate that later passes intake and C8.

### Verification

Portable verification on the final code passed with **exit 0** for both normal
and empty HOME (`out/beds/round3/verify-final-normal.log`,
`out/beds/round3/verify-final-empty-home.log`). **31 bed tests passed, exit 0** (`out/beds/round3/bed-tests-final.log`).
An additional 22 final changed-path and adapter tests passed, exit 0
(`out/beds/round3/changed-paths-final.log`). Both portable runs completed
162 checks. The affected scene/topology/camera batch passed **149 tests, exit 0**
(`out/beds/round3/affected-tests-resume.log`). Machine-readable final receipt:
`out/beds/round3/acceptance.json`. Adapter regeneration and its check passed;
`git diff --check` passed.
No full-suite, native Revit or real-villa design gate approval is claimed.
No commit; shared `assets/user` and `out/villa/round3` are untouched.


## Round 4 — seven lead-downloaded beds at source size

Executed 2026-10-09 on the Linux `codex/beds` worktree; round-3 uncommitted
work is preserved. **No passing replacement for parents, kids A or kids B.**
Their labelled procedural beds remain, as does the library daybed/joinery.
No layout, mattress datum, room camera, source geometry or texture changed.

### Library intake and source evidence

All seven inbox folders were copied into **new folders only** under
`/home/omar/archpipe/assets/library/props/<id>/`. Every inbox file, including
`scene.gltf`, `scene.bin`, textures, `provenance.json` and `license.txt`, was
hash-verified against its copy. `model.gltf` is a byte-identical importer alias;
original files remain intact. Receipt: `out/beds/round4/copy-receipt.json`.
Only new candidate entries were added to `ops/workstation/library-manifest.json`.
Each retains the original full CC-BY attribution, author URL and source URL.
No existing library folder, `assets/user` or `out/villa/round3` was modified.
No token was accessed or copied. All are appearance candidates, without a
verified buyable specification.

The embedded author credit for Bed Wood Oak PBR is **AHMED KCHIKICH
(inven2000)**; the round-3 listing display name was AK STUDIO. The actual
licence attribution is preserved rather than replaced with the display name.
Other credits: ArchVibe 3D, Ren Viro Store, Blender3D, AM ARCHITECTURE,
sparshgupta and WOODPORT.

`scripts/prepare_bed_geometry.py` extracted every actual imported face at
unchanged source size. `scripts/measure_bed.py` independently measured indexed
triangles; all referenced textures exist. Exact triangle counts, in table
order below: **341,838; 21,526; 9,324; 110,385; 88,208; 19,500; 275,209**.
Per-candidate intake JSON and compressed geometry receipts are under
`out/beds/round4`. Conservative accessor envelopes remain separate from actual
physical vertex bounds. Complete measurements and selection recipes:
`docs/beds-intake-round4.json`, reproducible by `scripts/recheck_beds_round4.py`;
full result: `out/beds/round4/recheck.json`.

Source-unit multiplier is **1.0 for all seven**. The supplied files and retained
listing metadata contain no alternate unit declaration authorizing correction
of the glTF coordinates. Dark Modern Bed's stated overall box in centimetres
is not a declaration that the downloaded glTF uses millimetres. Oversized
Simple Bunk Bed and oak geometry, and the tiny AM bunk, remain at their actual
source sizes. No factor is inferred from the client’s desired mattress.

### Mattress results and exact refusals

Width precedes length. Planned dimensions are parents **1.600 × 2.000 m**,
kids A **0.900 × 2.000 m per berth**, kids B **1.200 × 2.000 m**. The
20 mm tolerance applies independently to each complete mattress dimension.
The signed differences below are achieved minus planned; positive means too
large and negative means too small. Missing mattress geometry has no invented
numeric fit verdict. Native glTF axes X/Z are horizontal and Y is up; imported
Blender axes X/Y are horizontal and Z is up. Front denotes head-to-foot and
is distinct from a bunk’s ladder/access side.

| Candidate / intended bed | Actual complete mattress width × length (m) | Difference in width / length (mm) | Refusal / measured basis |
|---|---|---|---|
| Modern bed, `sf_bed3_dff77bbd` / parents | 3.662326 × 3.827348 | +2062.326 / +1827.348 | Both dimensions fail. `Object_4` rounded mattress component has 3036 welded vertices; separate four-vertex lower plane is excluded. Headboard at minimum X. |
| Dark Modern Bed, `sf_bed3_d3aeb724` / parents | 1708.963379 × 1876.869080 | +1707363.379 / +1874869.080 | Both fail; millimetre-looking coordinates are still glTF metres. Unique 942-vertex full mattress component inside the fused bed mesh; component measurement is diagnostic, not a production binding. |
| Simple Bunk Bed, `sf_bed3_9fb7c547` / kids A | Lower 9.554575 × 16.422628; upper 9.554575 × 16.422628 | Each +8654.575 / +14422.628 | Both berths fail. Actual full solids `Object_8` lower and `Object_5` upper; source mattress material and opposing preview silhouettes agree. |
| bunk bed, `sf_bed3_0e134823` / kids A | Lower 0.014194 × 0.022578; upper 0.010499 × 0.022459 | Lower −885.806 / −1977.422; upper −889.501 / −1977.541 | Both fail. Each bevelled mattress shell comprises seven named meshes: Mesh2–8 lower, Mesh10–16 upper; source duvets are excluded. Upper head direction unresolved; no activation orientation claimed. |
| Simple Bunk Bed 3D Model, `sf_bed3_2cabd354` / kids A | Lower 0.834516 × 1.829794; upper 0.834516 × 1.829794 | Each −65.484 / −170.206 | Closest new candidate, still fails by **45.484 / 150.206 mm beyond tolerance** per berth. Two separate 361-vertex mattress components within the fused fabric mesh; blankets and pillows excluded. |
| Bed Wood Oak PBR, `sf_bed3_28a8b705` / kids B | Complete naked mattress unresolved | Not measurable | Three meshes contain pillows, fused wooden base/headboard and cloth. The 59.055119 × 78.740189 m base component is a frame/surface assembly, not a proven mattress. No naked-mattress bounds or unit correction invented. |
| Engi bed, `sf_bed3_fe3c50e1` / kids B | Complete naked mattress unresolved | Not measurable for a full mattress | The only independent exposed head patch is **1.829067 × 0.571583 m**: already 629.067 mm wider than the target, but its short length does not measure a full mattress. Support platform 1.874794 × 2.332060 m is not a mattress. Source name `Engi160x200` cannot establish an actual 1.200 × 2.000 m mattress. |

All five identified candidates fail at source-size mattress intake. Both
unidentified candidates fail closed. No candidate is placed in its room, so
no rejected model receives a made-up C8 clearance/route/door/wardrobe/access/
support result. No replacement cloth simulation or collider acceptance is
claimed. The model-first, actual-collider and evaluated-cloth refusal controls
remain covered by the affected tests and prior mechanical evidence. Existing
wardrobe-motion and structural-capacity limits from round 3 remain.

No source accessories were removed or meshes modified; **omitted meshes:
none**. Neutral contents review shows bed/frame/bedding components without
freestanding bedside tables, benches or rugs. Measurement components within
fused meshes are not promoted into production part bindings.

### Neutral previews and diagnostic construction fixes

Final seven-candidate isolates, both opposing sides, are in
`out/beds/round4/candidate-previews-final/<id>-plus-y.png` and `-minus-y.png`.
Every primary isolate includes an actual **1.8 m figure** at the model’s lowest
vertex datum. Extreme-size AM, oak, Simple Bunk and Dark candidates also have
`-plus-y-close.png` / `-minus-y-close.png`; these omit the figure and frame the
unchanged source-size model. The Dark figure is subpixel at its enormous size;
the AM model is tiny beside its figure. Close-ups disclose appearance without
pretending either has credible scale. Receipts bind actual geometry, source
material hashes, camera clipping, staging and per-image diagnostic lights.
`out/beds/round4/preview-bindings.json` joins every final image hash to source
file hashes, geometry receipt hash and authored measurement selection; all
copied source bytes were rechecked after rendering. The final contact sheet
is `out/beds/round4/contact-sheet-final.png`.
These are rejection diagnostics, not approved presentation renders.

Fresh retained-bed previews use the rebuilt current scene
`out/beds/round4/scene.json` and original cameras. Parents: `pb-bed-room-neutral.png`
/ `pb-bed-isolated-neutral.png`, camera `v22-parents-day`; kids A:
`ka-bunk-room-neutral.png` / `ka-bunk-isolated-neutral.png`, `v06-kids-room`;
kids B: `kb-bed-room-neutral.png` / `kb-bed-isolated-neutral.png`, `v13-kids-b`.
All six are under `out/beds/round4/retained-previews`. Actual architecture and
room furniture are present; diagnostic props/curtains are omitted, design
emission/lights disabled. Room fills are recorded separately. Current fallback
bounds match the retained round-1/2/3 datums (`round4/fallbacks.json`). The
unchanged library retains its prior reviewed diagnostic images and known grain
mapping limitation; it has no new candidate in this round.

Independent reviewer: `out/beds/round4/preview-review.md`. Initial diagnosis
preserved three real diagnostic defects: default camera far clipping hid Dark
Modern Bed; a fixed 5 mm floor gap made the tiny AM source visibly float; a
fixed softbox intersected oversized Simple Bunk bedding (14 blanket triangles
and one mattress triangle), causing a bright patch. Frozen real inputs, sibling/
quiet proofs and records are in `tests/fixtures/bed-round4-*.json`,
`tests/test_bed_models.py`, `knowledge/bed-guards.json` and `docs/LEARNINGS.md`.
The corrections construct clipping, staging and diagnostic emitter placement
from actual vertices. Every emitter corner stays above the model/figure.
Diagnostic power scales with measured span squared; source geometry, exposure,
world colour, design lighting and client size limits are unchanged. Before,
first-fix and final previews/logs remain. The workflow and canonical skill were
updated together and adapters regenerated.

### Verification

Final receipt: `out/beds/round4/acceptance.json`. **38 bed/adapter tests
passed, exit 0** (`round4/bed-tests-final.log`); **159 affected scene, camera,
topology and intake tests passed, exit 0** (`round4/affected-tests-final.log`).
The final changed-guard/adapter batch also passed six tests, exit 0
(`round4/final-changed-tests.log`). **Portable verification passed all 166
checks, exit 0**, both under normal and empty HOME (`round4/verify-normal.log`,
`round4/verify-empty-home.log`). Adapter check passed for all 38 adapters;
`git diff --check` passed.

The earlier combined batch completed 196 tests, exit 1, with only the stale
absolute-gap assertion failing. A direct one-test reproduction also exited 1.
Both failed logs remain; the contact/figure-datum regression was updated and
all final bed tests passed. No other initial-batch failure occurred.

All **22 final candidate images and six fresh fallback images** were independently
reviewed at full size. Framing/clipping and diagnostic emitter clearance were
measured; the three diagnostic construction defects are resolved. No candidate
passed actual mattress intake, and neither numerical test success nor diagnostic
preview review is presented as replacement acceptance.
No full-suite, native Revit or real-villa design-gate claim; the lead owns the
full suite. No commit. Shared symlink targets and original library folders are
unchanged; round-3 work is preserved.

## Round 5 — client permits bounded scaling, 2026-10-09

This **client decision dated 2026-10-09 supersedes the 2026-10-08 no-scaling
rule** after all twelve candidates missed. Work resumed from the interrupted
run's uncommitted changes and actual round-5 evidence. Source library files,
shared symlink targets, layout, other furniture and existing room cameras
remain unchanged. No presentation render or replacement approval is claimed.

Width factor **sx** is planned mattress width divided by measured width;
length factor **sy** is planned mattress length divided by measured length.
Both are dimensionless after source-unit conversion. Distortion is the larger
factor divided by the smaller, minus one: this symmetric percentage cannot
exceed 15%, and each factor must be in 0.5–2.0. Vertical factor **sz** is design
mattress-top height above floor divided by measured lower mattress-top height
above the retained frame's lowest vertex. It is independent of the plan
factors. The whole retained model receives one transform about the measured
mattress plan centre, seats at the finished floor, and preserves head direction.
Bunk berths share that transform; no berth is independently reshaped.
World X and Y are horizontal coordinate axes; world Z is vertical elevation.

`archpipe.beds.scaled_bed_fit`, `scaled_model_fit` and `model_transform` enforce
this contract. `require_bed_geometry` binds source hashes, measured orientation,
contents, omissions, face selections, geometry digest, factors and placement to
an independent review snapshot. Pending models import only into explicit
neutral diagnostics. `villa_render.build(bed_replacements=...)` requires accepted
review, unchanged placement, every design berth height and passing real-frame
C8 before activation. C8 means the existing geometry-topology review.

### Appearance-first selection and measured factors

| Bed | Appearance choice / credit | Actual mattress at source size, metres | sx / sy / sz | Distortion | Scaled headboard height above floor | Omitted meshes / outcome |
|---|---|---|---|---|---|---|
| Parents queen | **Upholstered Bed / Free model**, `sf_bed_upholstered_cyberfox`, CyberFox 3D Studio (`cyberfox3d`), CC-BY-4.0 | 1.781747 × 1.999221 | 0.897994856 / 1.000389787 / 0.905497481 | 11.402619% | 1.364269 m; permitted diagnostic range 0.525–1.800 m | None. Exact 1.600 × 2.000 m mattress; unchanged-room C8 fails. |
| Kids A bunk | **Simple Bunk Bed 3D Model**, `sf_bed3_2cabd354`, `sparshgupta`, CC-BY-4.0 | Both approximately 0.834516 × 1.829794 | 1.078469605 / 1.093019185 / 0.691409911 | 1.349095% | 1.333853 m; permitted diagnostic range 1.122637–2.400 m | None. Each 0.900 × 2.000 m mattress within numerical precision; C8 and upper height fail. |
| Kids B | **No eligible downloaded model.** Appearance preference is Stained Bare Scandinavian Bed, `sf_bed_scandi_bare`, `JudeNavarre`, CC-BY-4.0, but it is refused. | 2.412432 × 4.241483 | Refused proposal: 0.497423405 / 0.471533138 / 0.453999812 | 5.490657% | No accepted transformed headboard | None. Both plan factors below 0.5; retain labelled procedural 1.200 × 2.000 m bed. |

Source credits and permitted modifications are retained in
`ops/workstation/library-manifest.json` and the regression credit record.
CC-BY-4.0 means Creative Commons Attribution 4.0.
The downloaded models are appearance proxies, not verified buyable products.
Parents' detailed upholstered head and bedding are the closest eligible
appearance; bouclé, walnut/brass accents and procurement correspondence are
not established by this grey fabric model. Modern bed's plan distortion is
19.610451%; Dark Modern Bed needs factors about 0.001. The ladder bunk has
the required visible ladder and the smallest eligible distortion; its source
painted timber appearance is preserved. Kids B's bare Scandinavian form is
the closest style but is distressed rather than verified light oak, and its
scale refusal takes precedence. No third downloaded fit can truthfully be
accepted from this library under the client's bounds.

The remaining nine candidates' outcomes, together with the three above,
are reproduced in `out/beds/round5/intake.json` by
`scripts/prepare_beds_round5.py` from the unchanged round-3/4 measurements:

| Candidate | Intended bed | sx / sy | Refusal |
|---|---|---|---|
| FORSSA | Kids B | 0.595756307 / 0.994542211 | 66.937756% distortion, above 15%. |
| Home Series bunk | Kids A | 0.284861228 / 0.321344689 | Both factors below 0.5. |
| Simple wooden bunk, 3DWorkbench | Kids A | Unresolved | No verified complete naked mattresses for both berths. |
| Modern bed, `dff77bbd` | Parents | 0.436880812 / 0.522555109 | Width below 0.5; 19.610451% distortion. |
| Dark Modern Bed, `d3aeb724` | Parents | 0.000936240 / 0.001065604 | Both factors below 0.5. |
| Simple Bunk Bed, `9fb7c547` | Kids A | 0.094195713 / 0.121783185 | Both below 0.5; 29.287397% distortion. |
| AM bunk, `0e134823` | Kids A | 63.405459016 / 88.583440328 | Both above 2.0; **39.709485% distortion**; common factors also miss upper width by 234.337 mm and length by 10.524 mm. |
| Bed Wood Oak PBR, `28a8b705` | Kids B | Unresolved | No verified complete naked mattress; its roughly 59 × 79 m source base is not a mattress. |
| Engi bed, `fe3c50e1` | Kids B | Unresolved | Exposed patch 1.829067 × 0.571583 m does not measure the whole mattress; frame/name cannot supply its missing length. |

All selected contents are bed, frame and source bedding; no separable tables,
benches or rugs were present to omit. Generated connected-component mattress
cuts identify existing faces while retaining every source triangle once:
**29,358 parents / 88,208 bunk triangles**. This is a semantic binding, never
permission to cut fused accessories away. A fused-extras declaration refuses
before import, even on an otherwise valid fit and a renamed model. The
regression injects that declaration into real measured candidate geometry;
it does not claim an actual bundled bench was found in these downloads.

### Height basis, placement and fixed-room C8 results

The height targets are **ASSUMED authored design values**, not published
bed-height requirements. `src/archpipe/concept/villa_render.py`, generated-bed
mapping and bedding block, reads parents/kids B mattress vertices from
`src/archpipe/furniture.py`: generated total heights 1.05/0.95 m use a
mattress top at half the total height. The finished-floor datum is 0.002 m.
Thus parents top is **0.527 m world / 0.525 m above floor**; kids B fallback
is **0.477 / 0.475 m**. The bunk bedding block uses **0.402 / 0.400 m lower**
and **1.402 / 1.400 m upper**. These exact datums are recorded in the unchanged
`out/beds/round4/scene.json` cloth specification.

The headboard upper caps, **ASSUMED 1.8 m single / 2.4 m bunk**, are explicit
visual plausibility screens, not safety standards. They are generous relative
to existing authored heads of 0.95/1.05 m and the 1.70 m procedural bunk and
remain below the room ceiling. A head below the highest actual mattress top
or above its cap refuses. Source part maxima supply the reported head heights.
The unchanged ceiling faces in all three rooms are at 2.700 m world height.

Parents mattress centre is **(20.330, −25.591) m**, bunk centre
**(11.977, −25.450) m**, both on floor **0.002 m**. These are the unchanged
layout coordinates; the heads remain at the planned head walls. Scaled
parents top is **0.527000 m**. Scaled bunk tops are **0.402000 / 1.124637 m**:
the upper misses its unchanged target by **277.363 mm**. Upper underside is
1.044831 m, leaving 642.831 mm above the lower naked mattress; this is a
measured gap, not a bunk safety certification. Exact arithmetic allows only
about 0.0001 mm residual plan error from the source's unequal berth vertices.

`scripts/review_beds_round5.py` regenerates both complete per-bed reports
against the unchanged room, specification and furniture. Fresh output is
`out/beds/round5/c8-complete.json`: parents **28 findings** (22 conservative
body screens, four route destinations, two access shortfalls), kids A
**15 findings** (11 body screens, two access shortfalls, one real-frame swing,
one boundary intrusion). Both report `activation_allowed: false`. Actual retained
parts replace their procedural bed/pillow faces. Route proxies participate in
route/access grids but are excluded from physical collision/swing/support
queries, so the proxy is not counted as a second manufactured bed. Unrelated
existing props are preserved without a new unrelated route intake.

| Review | Parents | Kids A |
|---|---|---|
| Bedside access | Foot **750.000 / 750 mm**, passes; left **714.552 / 750 mm**, **35.448 mm short**; right effectively **0 / 750 mm**, **750 mm short** | Best side **1.000 / 750 mm**, **749 mm short**; other side effectively 0. Only one passing side is required, but neither passes. |
| Routes | Four destinations newly unreachable by a **750 mm** route: corridor/parents entry, window, bed and vanity | No additional route-connectivity failure reported; this does not waive failed side access or door swing. |
| Door swing | No new swing-envelope failure reported | Real timber frame overlaps corridor/kids-A conservative swing envelope by **0.019684 m²**, required **0 m²**. |
| Room boundary | No frame-boundary finding | Frame extends **76.987 mm beyond the minimum-X room boundary**, required zero intrusion. |
| Body conflicts | Conservative part-envelope overlap screens remain; e.g. fixed headboard slats **30 mm / 0 mm** | Conservative screens remain; e.g. desk/frame **15.976 mm / 0 mm**. |
| Wardrobe/drawers | Storage-front planning screen reports no new affected-front shortfall | No new affected-front shortfall reported |
| Support | No unsupported-bed finding; real frame bottom meets the floor | Same |
| Activation | **Refused by fixed-room review** | **Refused by fixed-room review and upper mattress height** |

The access source is the held **UK Approved Document M, Volume 1 Dwellings,
2015 edition incorporating 2016 amendments**, printed p.18: paragraph 2.25a
for doorway-to-window routes, 2.25b for principal-bed sides/foot, 2.25d for
single/twin beds. Storage uses **Time-Saver Standards for Interior Design and
Space Planning, 2nd edition**, printed p.87, 36 inches in front of dresser,
closet and drawers; the verified project card rounds 914.4 to 914 mm.
Read page text and images are retained in `round5/source-ukadm.*` and
`round5/source-storage.*`, with verified cards in `knowledge/library.json`.
This is adopted planning guidance under the ageing-in-place brief, not a claim
of local code compliance.

Body-envelope depths are conservative screens, **not confirmed solid
penetration**. Door squares are not measured animated leaf sweeps. Actual
wardrobe-door/drawer motion geometry is still absent, so front access is not a
proof of opening travel. Geometric floor contact does not prove load capacity.
Kids B fails mattress intake and therefore receives no invented scaled-frame
C8 result; its existing fallback is shown honestly. No other item was moved.

### Model-first cloth and neutral review

Fresh mechanical proof: `out/beds/round5/importer-cloth-support-final.json`.
Actual imported/portable bounds agree to **0.001064 mm parents / 0.000642 mm
bunk**, every source triangle is retained, the procedural fallback hides
only after real import, and a forced missing-file test restores it physically.
Duvets are cut from the real scaled mattress; all retained frame, mattress,
pillows and source blankets collide. Source quilts/throws remain beneath the
added cloth, explicitly layered rather than claimed removed.

| Generated soft good | Surface crossings / enclosed / unresolved vertices | Minimum evaluated surface distance |
|---|---|---|
| Parents duvet | **0 / 0 / 0** | **5.003 mm** |
| Parents throw, checked against actual bed and evaluated duvet | **0 / 0 / 0** | **7.173 mm** |
| Bunk lower duvet | **0 / 0 / 0** | **7.513 mm** |
| Bunk upper duvet | **0 / 0 / 0** | **8.381 mm** |

The interrupted run exposed three cloth construction issues: naked-top
initialization inside source quilts; a concave nearest-face sign mistaken for
containment; and source-clear initial planes becoming permanently raised pin
headings. Frozen real inputs and failed attempts remain. Final construction
uses measured source-clear starts, lower-bunk initialization below the midpoint
to the upper underside, closed-shell ray containment, and local one-cell
support envelopes for mattress-width anchors. Inset bunk covers begin on
that envelope; free parents overhangs retain their collision-safe plane.
Existing cloth cut, physics, loft, thickness and crossing tolerance are
preserved. Throws now bind to real model geometry and evaluated duvet too.
These controls are documented with reproductions, sibling/clean proofs and
registration in `docs/LEARNINGS.md`, `knowledge/bed-guards.json` and the updated
villa-render skill/adapters. Image review remains independent of test success.

All six fresh neutral images are under **`out/beds/round5/previews-supported`**:

- Parents: `pb-bed-isolated-neutral.png` with the **1.8 m figure**, and
  `pb-bed-room-neutral.png` from unchanged **v22-parents-day**.
- Kids A: `ka-bunk-isolated-neutral.png` with the **1.8 m figure**, and
  `ka-bunk-room-neutral.png` from unchanged **v06-kids-room**.
- Kids B labelled procedural fallback: `kb-bed-isolated-neutral.png` with the
  **1.8 m figure**, and `kb-bed-room-neutral.png` from unchanged **v13-kids-b**.

`evidence.json` binds selection/source/material/cloth hashes, actual imported
bounds, simulation measurements, camera and diagnostic staging. The isolates
show the complete beds. Existing room views crop bed feet/lower frames; parents'
headboard is not displayed by its existing room camera. These are disclosed
comparison limitations; the cameras were not changed. Neutral world/fill,
disabled design emission and omitted incidental props/curtains are recorded.
Visible diagnostic softbox reflections are lighting aids, not design fixtures.
Independent final review is `out/beds/round5/preview-review-supported.md`.
The reviewer verified all six image hashes, both current model selections and
source bindings against `out/beds/round5/source-preview-bindings-current.json`
and the fresh C8 report; the raised-heading repair is visibly improved. These
are neutral comparison reviews, without integration or presentation approval.

### Round-5 verification and limits

Final execution receipt and exact test/check counts are recorded in
`out/beds/round5/acceptance.json`. **55 bed/scaling/fallback/clearance/adapter
tests passed, exit 0** (`bed-tests-current.log`); **159 affected scene, camera,
topology, intake and furnishing tests passed, exit 0**
(`affected-tests-current.log`). The **19 final changed tests passed, exit 0**
(`final-changed-tests.log`); this repeats the scale/adapter subset and adds
the two focused runner controls. **Portable verification passed all 170
checks, exit 0**, under both normal and empty HOME (`verify-normal-final.log`,
`verify-empty-home-final.log`). Adapter synchronization checked all 38 adapters
and `git diff --check` passed.

The preliminary affected command included two nonexistent module names and
exited 1 after 159 valid tests plus two loader errors; that failed invocation
is retained, not counted as acceptance. `run_tests.py` now refuses collected
loader errors before executing valid suites, with exit 1 and zero executed
tests. Frozen actual missing names, renamed siblings, clean module/method
controls and an expected failure against the unchanged historical runner
prove this procedural fix. The initial regression harness lacked the output
directory normally created by preflight; its fixture was corrected and final
controls pass. The workflow and execution-context documentation were updated.

Historical failed logs remain, including
undefined scoped-builder option, initial cloth refusals and raised-heading
experiments; current logs are separately named. Full-suite and native Revit
claims are outside this package. No commit; the lead owns the full suite and
integration decision. Shared data and the procedural library daybed remain
unchanged. Numerical guard acceptance is not room-fit or client approval.

## Round 6 — slim frames, client decision 2026-10-09

**Keep the layout; use slim frames.** This decision changes frame plan
scaling only. The round-5 mattress rule remains: exact planned mattress,
each width/length factor between 0.5 and 2.0, with the larger divided by
the smaller minus one no greater than 15%. Mattress and source bedding
share those factors. Every other retained mesh is classified as frame and
gets separate plan factors about the measured source mattress centre.
Frame sides and foot may extend at most **50 mm** beyond the mattress;
the head may extend **100 mm** for headboard depth. Heights retain round-5
values except the bunk's vertical factor now derives from the upper top.

`slim_frame_fit` derives and records frame factors; `slim_frame_findings`
independently measures transformed faces, including Blender read-back.
The minimum frame factor is **0.5**: compression beyond half size refuses
because it can visibly deform frame members and the complete ladder.
The mattress's 15% proportion rule is not applied to the frame. Eligible
factors still need visual review for distortion. No source mesh was removed,
no mattress was moved, and no layout, furniture or room camera was changed.

### Measured transforms and refusal

Converted source X and Y are horizontal axes before placement; converted
Z is up. glTF means Graphics Library Transmission Format. Source glTF X
maps to converted X, source glTF Z to converted
negative Y. All factors below are dimensionless after conversion to metres.
Width and length factors refer to the measured mattress axes, not necessarily
world X and Y after rotation. Vertical factor is independent of plan factors.

| Bed | Mattress width / length factors | Frame converted X / Y factors | Vertical factor | Outcome |
|---|---|---|---|---|
| Parents, unchanged CyberFox model | 0.897994856 / 1.000389787 | **0.918923103 / 0.852559449** (length / width) | 0.905497481 | Frame eligible; room and generated-cloth gates refuse. |
| Kids A, unchanged sparshgupta ladder bunk | 1.078469605 / 1.093019185 | **0.456000612 / 1.067624260** (width / length) | **0.862232651**, upper driven | Width factor below 0.5; diagnostic proposal only, never imported or activated. |
| Kids B | No eligible mattress transform among twelve sources | No frame transform accepted | Fallback unchanged | Retain procedural bed. |

Parents mattress remains **1.600 × 2.000 m**, top **0.527 m world**;
headboard remains **1.364269 m above floor**. Its rigid frame extends
**36.468 / 50.000 mm** at the two sides, against **50 / 50 mm** maxima,
and **100.000 mm** at the head against **100 mm**. Its foot is **35.131 mm
inside** the mattress edge, so has no positive extension against the 50 mm
maximum. The planning envelope including mattress is **1.686468 × 2.100 m**.
Retained bedding is wider than that frame and remains in physical room checks.

Kids A mattresses remain **0.900 × 2.000 m** per berth within the same
round-5 numerical precision. The below-bound proposed frame would give
**50.000 mm** at one side and place the other **209.067 mm inside** its
mattress edge; foot/head extensions would be **50.000 / 46.012 mm**.
These edge measurements do not authorize the required **0.456000612**
width factor. The complete timber mesh includes the ladder; it cannot be
compressed further or split into separately stretched structural members.

One vertical factor cannot meet both bunk datums. The lower-driven factor
from round 5 is **0.691409911**; upper-driven factor is **0.862232651**.
Upper top now reaches **1.402000 / 1.402000 m world**, but lower top becomes
**0.500826 / 0.402000 m**, **98.826 mm too high**. Upper mattress underside
is **1.302478 m**; naked lower-berth clearance is **801.652 mm**, compared
with the authored procedural **850.000 mm**, **48.348 mm less**. The
procedural underside was measured at 1.252 m in the unchanged scene.
These are authored design comparisons, not published bunk safety limits;
bedding and guard/ladder safety need separate proof. The two heights remain
independent activation gates. Arithmetic is retained in
`out/beds/round6/height-recheck.json`.

### Fixed-room C8 review

C8 means the geometry-topology room review. The current report is
`out/beds/round6/c8-accepted-code.json`, regenerated against the unchanged
round-4 scene, the authored layout identified as D1, and specification.
The parents and kids A proposals
are reviewed separately; kids A remains diagnostic because frame intake
already refuses. Rigid frame plus mattress supplies planning access strips;
all retained frame, mattress and source-bedding faces supply physical checks.
Unrelated existing furniture remains present. This is the same scoped
bed-induced review as round 5; baseline findings are not silently re-approved.

The verified access cards are **`ukadm-bed-principal-750`** (both principal
bed sides and foot), **`ukadm-bed-single-750`** (one side of each single bed),
and **`ukadm-bedroom-route-750`** (doorway to window). They cite UK Approved
Document M, Volume 1 Dwellings, 2015 incorporating 2016 amendments, printed
p.18, paragraphs 2.25b, 2.25d and 2.25a respectively. The held text and page
image were read again; receipts remain `round5/source-ukadm.txt` and `.png`.
Storage card **`tss-front-of-storage-914`** cites Time-Saver Standards for
Interior Design and Space Planning, 2nd edition, printed p.87: 36 inches
in front of dresser, closet and drawers, rounded by the verified card to
914 mm. Its held text and image are `round5/source-storage.txt` and `.png`.
Cards are in `knowledge/library.json`. This is adopted ageing-in-place
planning guidance, not local code certification.

| Review | Parents | Kids A proposed frame, intake already refused |
|---|---|---|
| Bedside access | Foot **750 / 750 mm**, passes; left **1.000 / 750 mm**, **749 mm short**; right effectively **0 / 750 mm**, **750 mm short**. | Best/right side **750 / 750 mm**, passes the one-side card. Left **1.000 mm**; it need not independently meet 750 mm once the other side passes. |
| Routes | **0 additional unreachable destinations**, required zero, with **750 mm** route width. The four round-5 route-delta failures are absent with the slim planning frame. | **0 additional unreachable destinations**, required zero, with **750 mm** route width. |
| Door swings / passages | **0 new conflicts / 0 allowed** in the existing conservative checks. | **0 new conflicts / 0 allowed**; round-5 frame swing conflict is absent. |
| Room boundary | Head reaches **50.000 mm beyond** the bedroom/entry cluster, required **0 mm**; conservative frame bounds outside area **0.082650 / 0 m²**. | Rigid frame and mattress have no boundary failure. Retained source bedding reaches **76.987 mm beyond** the room, required **0 mm**; outside bound area **0.152295238 / 0 m²**. |
| Body conflicts | **13 conservative overlap screens**; e.g. fixed headboard slats **30 / 0 mm**, source bedding/bedside table **350 / 0 mm**. | **7 conservative overlap screens**; e.g. retained bedding/adjacent bathroom furniture **3.987 / 0 mm**. |
| Storage fronts | **0 new affected-front shortfalls**; required planning depth **914 mm**. No affected wardrobe/drawer front was selected by this scoped delta, so no achieved opening-travel width is asserted. | Same. |
| Support | Frame floor gap **0 / 0 mm**, finished-floor elevation **0.002 m**; no new unsupported-bed finding. | Same for proposed geometry; this does not authorize its below-bound frame factor. |
| Activation | **Refused**: room access/boundary and generated cloth. | **Refused**: frame factor, competing berth heights and retained-part room findings. |

The final report has **16 parents findings** (13 body screens, two access,
one boundary) and **8 kids A findings** (seven body screens, one boundary).
Both record `activation_allowed: false`. The intermediate resumed report
(`c8-resumed.json`, 15/7 findings) exposed a boundary escape: its old check
skipped combined rooms and omitted bedding after frame planning was separated.
The new unconditional retained-part check compares against the complete
room-cluster union, including concave clusters. The actual pre-fix C8
dispatcher regression fails; renamed/translated and clean controls pass
after the fix. Evidence, causes and registration are in
`LEARNINGS.md`, lesson **`beds-room-cluster-boundary`**. Earlier `c8-complete.json`
is an intermediate iteration, superseded by the final report above.

The change adds findings without moving or reshaping any design geometry;
the reviewed images remain current. Boundary/body bounds are conservative
screens, not exact solid-penetration measurements. Swing squares are not
animated door sweeps; storage access is not proof of door/drawer travel;
geometric support is not structural load capacity. Route results are scoped
bed-induced changes, not blanket approval of unchanged baseline findings.

### Neutral previews and physical limits

All six existing round-6 images in `out/beds/round6/previews` were inspected
again during resume. `preview-review.md` preserves their independent visual
review and image hashes; `previews/evidence.json` binds actual geometry,
source files, materials, cloth, unchanged cameras and diagnostic lights.
Regenerated proposals match the reviewed proposals byte for byte.
`preview-review-resumed.json` additionally confirms every image hash, current
selection/source bindings, original geometry/material/cloth receipts and
unchanged room cameras.

Parents **`pb-bed-isolated-neutral.png`** shows the complete slim-frame model
with a **1.8 m figure**; **`pb-bed-room-neutral.png`** uses unchanged
v22-parents-day. No obvious frame warping was identified in the reviewed
isolate. Portable and Blender whole-model bounds agree within **0.000838 mm**,
and all **29,358** source triangles remain. The room camera crops the foot
and does not show the complete headboard. This limited view cannot prove
bedside clearance or head depth.

The parents generated throw has **0 crossings, 0 enclosed vertices,
1 unresolved vertex**, minimum surface distance **7.411 mm**. The preview
process correctly exited **1**. It saved diagnostic images with **raw source
bedding**, without the refused generated duvet/throw. They establish frame
appearance only; physical cloth acceptance remains refused. The actual
refusal and renamed/clean controls are frozen in
`bed-round6-throw-refusal.json` and tested. No tolerance was relaxed.

Kids A **`ka-bunk-isolated-neutral.png` / `ka-bunk-room-neutral.png`** and
kids B **`kb-bed-isolated-neutral.png` / `kb-bed-room-neutral.png`** show
labelled procedural fallbacks with the same scale figure and unchanged
v06-kids-room / v13-kids-b cameras. They are not previews of accepted
downloaded replacements. No imported bed passes every gate in this round;
therefore none is activated. The procedural library daybed also stays unchanged.

### Kids B: all twelve models tried again

`scripts/prepare_beds_round6.py` re-screens every source against the fixed
**1.200 × 2.000 m** kids B mattress, including models originally sought
for parents or kids A. Source-file hashes are checked against unchanged
round-2/4 measured geometry. Frame proportions are not a mattress refusal.
Nevertheless **0 of 12** passes the unchanged mattress rule, so none reaches
eligible frame fitting, replacement room review or imported preview.
No incomplete mattress is inferred from a frame, quilt or model name.

| Library model | Mattress width / length factors for kids B | Decisive mattress refusal |
|---|---|---|
| FORSSA | 0.595756 / 0.994542 | 66.938% distortion, maximum 15%. |
| Stained Bare Scandinavian Bed | 0.497423 / 0.471533 | Both below 0.5. |
| CyberFox upholstered bed | 0.673496 / 1.000390 | 48.537% distortion. |
| Home Series bunk | 0.379815 / 0.321345 | Both below 0.5; also 18.196% distortion. |
| Simple wooden bunk, 3DWorkbench | Unresolved | Complete naked mattresses not independently identified. |
| Modern bed, dff77bbd | 0.327661 / 0.522555 | Width below 0.5; also 59.481% distortion. |
| Dark Modern Bed, d3aeb724 | 0.000702 / 0.001066 | Both below 0.5. |
| Simple Bunk Bed, 9fb7c547 | 0.125594 / 0.121783 | Both below 0.5. |
| AM bunk, 0e134823 | 84.540612 / 88.583440 | Both above 2.0; common factors also miss upper width by 312.449 mm and length by 10.524 mm. |
| Simple Bunk Bed, sparshgupta | 1.437959 / 1.093019 | 31.558% distortion. |
| Bed Wood Oak PBR, 28a8b705 | Unresolved | No independently identified complete mattress. |
| Engi bed, fe3c50e1 | Unresolved | Exposed mattress patch does not establish complete length. |

Full numbers, additional refusals and source hashes are in
`out/beds/round6/kids-b-rescreen.json`. The existing procedural kids B bed
remains the fallback; relaxing only frame proportions does not make an
ineligible mattress acceptable.

### Round-6 verification and hand-off

Final bed/fit/clearance/adapter execution: **77 tests passed, exit 0**,
339.913 seconds (`out/beds/round6/bed-tests-accepted-code.log`). The final
unmocked joined/concave-room generalisation group also passes **10 tests,
exit 0** (`boundary-generalization-corrected.log`); it overlaps the slim
subset rather than representing ten additional unique tests.

The affected scene, camera, geometry-topology, intake, furnishing and legacy
furniture-model modules passed **179 tests, exit 0**
(`out/beds/round6/affected-tests-resumed.log`). These modules do not call
the changed bed-room dispatcher; its actual old-failure/new-success proof
and bed regressions are in the final focused batch above. Complete execution
receipts and final artifact hashes are in `out/beds/round6/acceptance.json`.

**Portable verification: 174 checks passed, exit 0 under both normal and
initially empty HOME.** Current logs are `verify-normal-accepted-code.log`
and `verify-empty-home-accepted-code.log`; the empty-HOME receipt records
`initially_empty: true` and `exit_code: 0`. The fresh final C8 script exits
0 while correctly recording both activation gates closed. Diagnostic
execution success does not approve a bed. All 38 generated adapters match
after synchronization; `git diff --check` passes.

The interrupted run's previews and earlier failed attempts are preserved.
The throw refusal remains open; no physical cloth acceptance is inferred
from its diagnostic images. The boundary escape is repaired and registered
with actual dispatcher, sibling and clean proofs. Source meshes, shared
`assets/user` / `out/villa/round3` data, authored layout and cameras remain
unchanged. Desks stage-1 work is retained on `codex/desks`. The supplied
interpreter, `PYTHONPATH=src` and `NO_COLOR=1` were used; no packages installed,
no native Revit or real design-gate approval claimed, no commit made.
The lead owns the full suite and any commit.
