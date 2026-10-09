# Furniture phase, step 1: beds

**Round 2 decision: retain all four labelled procedural beds.** All five
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
