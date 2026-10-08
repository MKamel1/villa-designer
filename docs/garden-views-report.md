# Garden view corrections — 2026-10-07

Item 0 is repaired without replacing the frozen snapshot. v19 and v27
have independently reviewed camera corrections. The two terrace stone
stripes are removed at the renderer's construction boundary. G4d is
preserved. Lead decisions on 2026-10-07 retire v07 and v38 from the
review/final presentation batches while retaining their diagnostic definitions.
The approved final v41 candidate is integrated with a rear-chair-only
visibility allowance. No presentation delivery or commit was made.

Coordinates below are repository metres: x and y are horizontal, z is
vertical. Camera targets define aim. All cameras use a 24 mm lens and
level aim; lens shift is expressed in sensor-width units. Quality
assurance (QA) means the existing `archpipe.render_qa` image checks.
Each coordinate triple lists x, y and z; the arrow in the camera table
joins eye position to aim target. A count such as 8/13 means eight of
thirteen tested rays reach the required subject.
Thirteen sightline rays mean the existing bounding-centre sample plus
twelve evenly indexed actual vertices; at least seven must reach each
required subject. The only approved exception is the rear chair in
v41-south-garden-terrace: six of thirteen, as recorded below. These are
authored review criteria, not standards.

## Item 0: explicit later finish decisions

The original orientation migration snapshot predates the client's G4d
approval. Its geometry, transforms, per-item appearances and climber seed
comparisons remain intact. The original snapshot was not edited.
[The explicit allow-list](../tests/fixtures/orientation-approved-appearance-changes.json)
records each item, field, old value, new value and decision:
`G4d, client 2026-10-07: pale gravel and light stepping stones`.

| Exact item identifiers | Field | Frozen value | Approved value |
| --- | --- | --- | --- |
| `landscape-stone-lounge-north-end-0`, `-end-1`, `-00`, `-01`, `-02`, `-03` | material | stepping-stone | north-light-stone |
| `landscape-gravel-north` | material | garden-gravel | north-pale-gravel |

Each stone has its own full identifier in the JSON record. Duplicate,
stale, unused and non-material permissions fail. Any unlisted field
difference still fails. The G6b independent finish-register expectation
now includes both reviewed G4d finishes, already present in
`ALLOWED_MATERIALS`.

Proofs mutate actual listed stone/gravel appearances, an unlisted climber
appearance and a stone vertex by 1 mm: every mutation refuses. Removing
either new registered finish or substituting an arbitrary finish also
refuses. Current input stays quiet. Both complete affected modules passed
15 tests before view work (`out/garden-views/item0-focused.log`).

## Original QA failure attribution

The retained lead scene/image bundle identifies source revision
`3d4fee3`; its immutable workstation path is
`/home/omar/archpipe/villa-render/bef71f6a8927ef2561d0b1b3`.
The task's 13 reviewed drafts are the historical evidence, not a claim
that the current whole set has passed presentation QA.

**v07 dusk clipping.** The original display image has 27,381 clipped
pixels out of 614,400: **4.456%**, against **3%**. Clipped means at least
one 8-bit channel reaches 254. A deterministic 1,500-pixel sample was
ray-cast in the retained camera: 1,348 rays (**89.87%**) miss all geometry;
150 meet imported frangipani object `010`, two object `008`. No opaque
wall or lamp was hit. The remaining hits are alpha-cutout leaf/petal
geometry; geometric hits cannot distinguish a visible petal from sky
through its transparency. The dominant cause is the sky in this frame,
not a traced bright wall or a demonstrated emitter conversion defect.
Evidence: `ray-requests.json`, `ray-evidence.json`, `ray-diagnosis.log`
under `out/garden-views`.

At the same position/aim, complete actual frangipani/sofa framing allows
shift **0.0242302–0.1222590**. Translating the original clipped mask to
the lowest permitted shift still retains 23,866 known clipped pixels,
**3.884%** of the image, before any newly uncovered ground pixels.
Thus pure downward shift cannot solve this particular frame while keeping
complete physical subjects. This is a retained-image projection screen,
not new render QA (`dusk-shift-bound.json`). The first fixed-lock numerical
candidate at shift **0.038** measured **4.1%** clipping, median **0.28**,
near-black pixels **9.9%**, cool cast **0.089**. It was not integrated.
The specified dusk sky's faithful cool cast remains disclosed in the
live caption; exposure and white balance were not compensated.

**v19 pane detail.** The failing panes `ear-54` and `ear-55` correspond to
`shell-019-glass-clear-54` and `-55`, the house's own upper-floor parents
room. Their clipped screen rectangles occupy only the last **4.57%** and
**4.45%** of frame width. The original detail scores were **0.0074** and
**0.0077**, below **0.01**. Forty-nine rays per rectangle, traced through
glass, end respectively at facade/interior wall/ceiling in counts
**23/12/14** and **18/14/17**. They show grazing blank ceiling/wall/facade,
not an absent neighbouring context interior or a sky-only gap.

Turning the aim **2 degrees** toward the open garden makes those panes
incidental at the edge; they no longer enter the dominant-window receipt.
The actual tree and living-sofa subjects remain fully framed, with a new
explicit complete-frame requirement. The remaining measured pane scores
are **0.0315, 0.0314, 0.0580, 0.0565**, all above **0.01**. No window check
or geometry was removed. The first numerical probe also measured median
**0.26** and near-black fraction **13.9%**; this is a pane/composition fix,
not a claim that all physical QA passes.

**v27 composition.** The former portrait roof detail passed its declared
plant-only frame, but omitted the bed extent, complete trellis and path.
QA could not protect context absent from the declared intent. The new
level view from the dirty-kitchen window keeps all three original plant
groups, adds the bed, star-jasmine trellis/climber and living stepping
approach, and preserves all three original required visibility targets.
Their measured sightlines are **8/13, 9/13, 12/13**. Full physical framing,
room enclosure, proximity and foreground-opening checks are clean in the
authoritative export. The independent critic accepts the garden as a
coherent whole, with no looming foliage.

Rejected checkpoints are retained: a visually accepted first kitchen
pose gave **3/13, 6/13, 10/13**, and a wider supported roof pose hit
parapet on every target. Neither was integrated. The final window
position clears the counter. Secondary dining-route/pot geometry may
crop at the foreground; that is disclosed in the caption. The legacy
`above` identifier remains for delivery continuity. Historical G6b
portrait proofs now use the frozen reviewed old camera with their
original assertions; separate current-view proofs protect the new intent.
The full focused run also found that a renamed exterior aloe mutation
copied v27's new indoor role, incorrectly selecting its existing **0.15 m**
allowance. It now owns its frozen exterior role and unchanged **1 m**
rule. The actual failing input is reproduced from the authoritative
export; both failed and repaired logs are retained. No clearance threshold
or original refusal assertion was relaxed.

**v38 after G4d.** At the unchanged camera and original day exposure lock,
the small post-G4d numerical probe measures median **0.21** versus the
lead's pre-G4d **0.15**, still below **0.30**. Near-black fraction is
**7.9%** versus the lead's **8.5%**, now below **8%**. Clip fraction is
**0.0%**, cool cast **0.018**. The pale material change improves the
measured shaded court but does not bring its midtones to the shared
exterior-day target. Its visible pale ground remains in deep shade beside
the brighter sky-lit wall; neutral fill cannot certify that physical
contrast. The additional lower-ground framing worsens median luminance
to **0.19**, as it replaces some brighter wall with shaded ground; it
does not solve the target. The original camera is retained. No fill,
exposure or material
adjustment was made to force a pass.

## Lead presentation decisions — 2026-10-07

1. **v07-terrace-dusk retired.** The measured **4.456%** highlight clipping
   is dominated by the specified dusk sky: **89.87%** of sampled clipped
   rays miss all geometry. Best tested cameras retaining the frangipani
   still clip **3.9–4.1%**, above the unchanged **3%** limit. Its cool cast
   is faithful. The south garden is presented by **v19, v40 and the new
   v41-south-garden-terrace**. QA limits, exposure and sky remain unchanged.
2. **v38-north-garden-floor-bed retired.** After G4d its midtone median is
   **0.21**, below **0.30** at the set-locked daylight exposure. Lower-ground
   framing worsens it to **0.19**. The deep-shade court is faithful. The
   north garden is presented by **v36, v37, v39 and the G4d evening view
   v41-north-garden-evening**.
3. **v41-south-garden-terrace integrated.** The final reviewed candidate
   turns **20 degrees** away from the house, leaving approximately **3%**
   right wall band. The caption retains the proposal with the measured
   east-yard naming correction described below. Only the rear chair
   receives the explicit six-of-thirteen allowance below; every other
   required subject retains seven-of-thirteen.

Each view definition records its reason and decision date. Retirement uses
`presentation_retired`, which excludes a view from both `review` and `all`
presentation batches in the local driver and Blender, and from the review
page. Explicit view identifiers remain available for diagnostics. v41 keeps
the reviewed candidate's `final_only` setting and therefore joins `all`;
its accepted neutral preview is retained. The two v41 identifiers refer to
different gardens and remain distinct.

## Two black stone stripes

Four rays at the actual candidate stripe locations meet the tops of
`landscape-stone-living-south-02` and `-00` and their endpoint neighbours,
at **z = −2.988 m**. Each endpoint overlaps the adjacent field stone by
**0.0728333333 m × 0.914 m = 0.0665696667 square metres** at exactly the
same elevation. Here the multiplication gives overlap area from length
and width. The black lines are overlapping closed stone volumes,
not intended thin-member shadows, gaps or material seams.

`archpipe.blender.stone_union.prepare` now partitions each compatible
overlapping group into its exact occupied solid union. Each top/bottom
cell is emitted once; internal vertical faces are omitted. All authored
records stay immutable, original identifiers alias the render object,
materials and substrate slots remain. No stone moves. The control also
covers other routes, not just these two camera pixels.

Frozen real overlaps still fire without preparation; prepared surfaces
have exact plan-union equality, no duplicate top area and closed manifold
edges. All routes, renamed/translated siblings and an isolated clean
stone prove prevention and quietness in `tests/test_garden_views.py`.
Both black stripes disappear in the neutral terrace preview, independently
reviewed after the first fix. Portable verification checks the prepared
stone output as well.

## Camera before and after

| View | Before position → target; shift | Integrated position → target; shift |
| --- | --- | --- |
| v07 | (28.1, −20.81, −1.65) → (25.63201336, −25.15845282, −1.65); 0.073 | Same pose; retired from presentation, kept for diagnostics |
| v19 | (28.3, −20.95, −1.65) → (25.57680482, −25.14335284, −1.65); 0.07514311 | Same position → (25.72480963, −25.23583650, −1.65); 0.07452904 |
| v27 | (15.29, −21.95, 1.35) → (20.22844170, −21.16782767, 1.35); −1.31889205, portrait | (15.2, −22.5, −1.65) → (20.06311516, −21.33805725, −1.65); −0.11996365, landscape |
| v38 | (4.1, −25, −1.65) → (1.6, −27.7, −1.65); −0.18 | Same pose; retired from presentation, kept for diagnostics |
| v41 south terrace | (22.8, −21.6, −1.65) → (23.98021394, −26.45871331, −1.65); 0.02132464 | Integrated: same position → (25.57081615, −25.76204011, −1.65); 0.02504658 |

The final v27 uses a 36 mm landscape sensor, replacing the same physical
sensor's former portrait orientation. Its level eye is 1.35 m above the
kitchen floor. All design geometry remains fixed.

## New v41: approved and integrated

The retained G6b candidate (historically labelled “west”) is turned **20 degrees** away from the house,
reducing the right wall band from approximately **25%** to a thin edge
of approximately **3%**. The 24 mm, level, open-garden eye is unchanged.
The whole pergola can be included explicitly as a physical subject along
with both roof climbers, centrepiece and seating. The tree canopy is
incidental and partly cropped; the user-approved bench screening remains
natural. Integrated caption: “South terrace from the open east-yard approach:
timber pergola with Petrea and star jasmine, planted centrepiece, bench
and two lounge chairs. Bench and lower rear-chair parts are naturally
screened by the centrepiece. The retained frangipani canopy is incidental;
the house is a thin right edge. Authored botanical/furniture appearances
and pergola dimensions are assumed; structure, roots and procurement
remain unverified.”

Integration naming check: the proposed caption originally said “open west
garden.” Under the repository's client compass mapping, the unchanged camera
at (22.8, −21.6) is in the **east-yard approach**. Only that phrase is corrected;
the remainder of the proposed caption and the approved camera are preserved.
The original wording is retained as `caption_before_naming_check` in the
proposal record. This is a measured naming correction, not a caption waiver.

The six retained required feature targets give **11, 13, 13, 6, 8, 7**
visible rays out of thirteen. The rear chair's lower points meet the bowl,
Mona Lavender or nearer chair, although its seat/back read in the reviewed
preview. The lead accepts this natural screening and records exactly:

> rear chair lower parts naturally screened by the centrepiece bowl and planting; seat and back visible; minimum visible feature rays 6 of 13 for this subject only (lead decision 2026-10-07)

The allowance is keyed by `landscape-g6-seating-chair-1` and explicitly bound
to `v41-south-garden-terrace`. A **5/13** result still fails. All five other
subjects keep **7/13**; all other views retain the general guard. An allowance
copied into a different view fails closed. No target is removed, and full
physical framing, garden enclosure, opening and proximity guards remain.
Exact first hits are retained in `terrace-visibility.json`; the accepted
proposal is [garden-views-terrace-proposal.json](../knowledge/garden-views-terrace-proposal.json).
Independent review accepted this composition conditionally before the
lead's explicit screening decision; that decision now resolves the hold.
The final candidate preview is
[v41 neutral](../out/garden-views/final-terrace-candidate/v41-south-garden-terrace-neutral.png).

## Evidence limits and acceptance

Numerical probes use **64 samples, 800 × 534 pixels**, with the saved
whole-set exposure locks, **−2.517188787 stops** for exterior dusk and
**−11.760062218 stops** for exterior day. A stop is a base-two brightness
multiplier. The original cohort receipt, source geometry and photometry
hashes are retained in `numerical-probes/probe-inputs.json`. These small
diagnostics cannot establish final-sample photographic fidelity, and no
presentation delivery was rendered. Existing locked tonal checks may
report WARN instead of FAIL; numeric exceedances above remain unresolved
regardless of that label. Neither QA constants nor locked exposure code
changed.

Additional bounded numerical candidates retain the original physical
guards: dusk aim −3 degrees with shift **0.03124233**, and north shift
**−0.30** for more pale ground. The dusk result is clipping **4.1%**,
median **0.27**, near-black **9.7%**, cool cast **0.083**. The north
result is clipping **0.0%**, median **0.19**, near-black **7.8%**, cool
cast **0.017**. Neither meets the requested tonal target, and neither
is integrated. Results and original locks are retained under
`refined-numerical-probes`; no candidate is promoted merely for improving
a scalar metric.

Final neutral previews for v07, v19, v27 and v38 live in
`out/garden-views/final-neutral`, with the matching
`context-preview-evidence.json`. The independent full-size critic accepts
v19/v27 composition and finds no newly introduced visible defects in
those four previews. Neutral fill plus retained production emitters
cannot certify dusk clipping/cast or north midtones. The v41 neutral
preview is separate and is the candidate approved by the lead above.

Preview links: [v07](../out/garden-views/final-neutral/v07-terrace-dusk-neutral.png),
[v19](../out/garden-views/final-neutral/v19-garden-facade-neutral.png),
[v27](../out/garden-views/final-neutral/v27-east-yard-above-neutral.png),
[v38](../out/garden-views/final-neutral/v38-north-garden-floor-bed-neutral.png).

The retained pre-decision authoritative export is `out/garden-views/scene.json`, source
hash `cbf5acc6ac6e14c7884a9b725923d0528905f9ac55b5a8aa3153a57c03879355`.
Decoded meshes, props, materials, lights and garden-camera domains are
**exactly equal** to the retained G4d delivery, with no coordinate
tolerance or rounding. In that historical export only v19/v27 camera poses changed; v07 gained its
disclosure. The decision implementation adds v41 and retirement metadata
in authored code; the retained generated export is not hand-edited. `authoritative-comparison.json` records exact before/after
values. The shared symlinks were not modified.

Prior to these lead decisions, normal and newly empty HOME portable verification both exited **0**:
`verify-normal-final.log`, `verify-empty-home-final.log`,
`portable-final-exit-status.json`. The first normal run correctly caught
a raw photometry-copy writer in the new diagnostic; the script now uses
the repository's shared atomic writer. Failed evidence is retained;
the resolution/preflight regression also covers missing manufacturer
files, generated precedence and escaping paths.

Prior acceptance covered **204 tests** across render-standard,
render-views, all garden modules, landscape and orientation. The initial
204-test run exits **1** for the single historical fixture-role error
described above; the other **184 tests** outside the view module pass.
After correcting that test's role, the **complete 20-test render-view
module exits 0** (`render-views-retry.log`). No other source or tested
module changed. Acceptance validation confirms identical affected-module
test coverage and refuses any extra failure; it exits 0 and records both
observed test-run statuses in `focused-acceptance.json`. Failed evidence
is retained, rather than presenting
the first run as a pass. The lead reruns the full suite and commits.

Historical integrity evidence confirmed its source hash matched the
export and all **five** neutral-preview receipts, including the then-held
v41 proposal, share the exact source geometry hash. Agent adapters match
their sources (`sync_agent_assets.py --check`, exit 0, 38 adapters), and
`git diff --check` is clean. That earlier package introduced no agent-source edits; pre-existing G4d
skill changes remain preserved. The current decision package updates the
villa-render workflow and regenerates its adapters.

The learning index and guard registry were updated with the snapshot,
whole-court intent, stone-overlap and probe-input controls. Repeatable
procedure: [garden-views workflow](ops/garden-views.md). This garden
example does not approve the villa's eight design stages or native-model
gates.


## Verification of the lead decisions

Current decision regressions: `lead-decisions/final-garden-views-tests.log`
passes **11 tests**, exit **0**. The integrated candidate measures the retained
feature-ray counts **11, 13, 13, 6, 8, 7**. Removing the allowance restores
the rear-chair failure; changing its result to **5/13** fails, changing any
other subject to **6/13** fails, and copying the allowance to another view
fails. Both retired definitions are absent from review/all batches while
explicit diagnostic identifiers remain selectable. The actual Blender
selector and the local driver's generic sibling are exercised.

The scene's canonical mesh hash exactly matches the frozen reviewed neutral
preview receipt: `9e03d4414b2f9c21e4349e03bcb9cb4bc80452ace9ccff8d1474098069f3a01f`.
SHA-256 means Secure Hash Algorithm with a 256-bit output: a content
fingerprint of the mesh records, using sorted JSON keys and compact separators. The regression freezes that digest by value;
it does not require optional render outputs or regenerate its expected value.
No new preview or presentation render was produced.

The first focused attempt exposed the proposed caption's incorrect west
vantage and an existing Blender unit-test extractor missing the newly added
stone-union dependency. Its failure evidence is retained in
`lead-decisions/first-focused-failure.log`. The caption now uses the measured
east-yard approach and the existing camera-side annotation; the original
wording remains recorded. The extractor loads actual Blender sibling modules
and preserves the batching/detail assertions. Portable verification now
also checks resolved view captions instead of relying on a scene with its
views omitted. No compass guard or image-quality limit was waived.


Final portable verification exits **0** in normal HOME and **0** in a freshly
created HOME asserted empty before launch, both with `NO_COLOR=1`:
`out/garden-views/lead-decisions/verify-normal-accepted.log` and
`out/garden-views/lead-decisions/verify-empty-home-accepted.log`.
`portable-acceptance.json` records the observed statuses and source provenance.
The villa-render skill was updated and `scripts/sync_agent_assets.py` run;
all **38** generated adapters match their sources. `git diff --check` is clean.
The shared symlinks and existing view-fix work remain preserved. No commit
was made; the lead runs the full suite and commits.


Completed verification **2026-10-08**: the wider focused run passes **243
tests**, exit **0** (`out/garden-views/lead-decisions/focused-tests.log`). The
complete current garden-view module separately passes **11 tests**, exit
**0**, including the frozen preview-geometry hash case added after wider
collection. Together the logs cover **244 distinct tests** across
render_views, render_standard, garden modules, landscape, orientation,
the affected render driver/contract and agent adapters. No failure is
excluded. `portable-acceptance.json` records the observed exits, test-file
hashes and unchanged source provenance. The lead still runs the full suite.
