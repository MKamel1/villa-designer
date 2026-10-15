# Garment polish

Uncommitted work from `52d30dd`. The original gravity cloth cache remains
byte-for-byte unchanged. Physical garments, supports, rails, slots, wardrobes,
doors and cameras retain their authored values. The bedroom remains a
capability example; this package approves no villa-design gate.

## Construction and evidence

All new tailoring dimensions are **ASSUMED** compressed empty garments on
hangers, not published standards or buyable product specifications. The
[pre-registered policy](../knowledge/drape-polish-policy.json) assumes 40 mm
shirt and 46 mm jacket torso air depth, with a 32 mm shoulder depth, before
wrinkles and fabric thickness. Fabric thickness remains 0.8 mm. Table lengths
below are millimetres (mm).

The relaxed panels come from the retained cache. Separate front/back panels,
eight-segment shoulder returns, a collar stand and fall, front bands and
surface-attached jacket lapels supply the added construction. Folded pieces
have deterministic individual offsets/rotation, rounded edges, slight sag,
a restrained crease, a continuous rear fold and a thin turned front hem.
The repair's `stable_seed` helper supplies all variation; eight bounded
variants per physical folded shape are tested.

A separate [derived cache](../knowledge/drape-polish-cache.json.gz) binds
source, policy, original cloth values and variant. Two independent Python
processes compute all 42 inputs with different process hash salts; their
complete output hashes match. Blender reads these exact meshes. Regenerating
normals in Blender changed 33 local coordinates by about 1e-18 metres and
correctly failed read-back; the frozen reproduction and live read-back test
prevent that recurrence. [Process receipt](../out/drape-polish/polish-determinism.json).

| Screen | Required | Achieved |
|---|---:|---:|
| Shirt torso depth | at least 35 | 44.29; previously 22.77 |
| Jacket torso depth | at least 35 | 50.21; previously 23.25 |
| Shirt / jacket shoulder depth | at least 28 | 41.71 / 45.74; previously 18.80 / 19.08 |
| Collar stand / fall height | at least 12 / 25 | 18.00 / 33.41 |
| Front band width | at least 12 | at least 16.14 |
| Curved shoulder-return displacement | at least 2 | at least 7.62 |
| Front tailoring clearance over body | at least 0.10 | at least 0.54 |
| Fold top relief | at least 0.70 | 2.92–3.62 |
| Fold horizontal centre drift | at least 1.00 | 1.79–4.15 |
| Front-versus-back fold groove contrast | at least 2.00 | 2.25–4.79 |
| Turned front-hem height / depth | at least 2 / 10 | at least 6.19 / 26.67 |
| Hanging-neighbour gap | at least 27 | 32.22 |
| Escape of changed shirts/jackets/folded pieces | zero | zero |

The first shirt shaping trial exceeded its envelope by 0.2824 mm; a narrow
fold variant exceeded its envelope by 0.0686 mm. Both were refused. Continuous
panel shaping and dimension-derived fold offsets/rotation corrected their
causes without enlarging envelopes or moving any physical element. Exact
live-envelope checking also refuses a 40-nanometre overrun hidden by local
cache-key rounding.

Nine **unchanged folded-trouser** appearances retain their earlier 1.9 mm
expansion within the inherited 4 mm drape allowance. Zero-escape claims above
apply to the changed appearances. Forbidden contacts remain zero; all 101
eligible physical pieces retain a bound appearance.

## Neutral GPU previews

All previews use NVIDIA OptiX, 24 samples and a maximum dimension of 960 pixels,
serially through the shared graphics lock. Context cameras, original white
fills, world, exposure and emission suppression remain unchanged. Isolated
staging reuses the original receipt and includes the 1.8 m scale figure.
These are diagnostic images, not presentation renders.

- [v31, hers](../out/drape-polish/context/v31-dressing-hers-neutral.png)
- [v32, his](../out/drape-polish/context/v32-dressing-his-neutral.png)
- Shirt: [full](../out/drape-polish/isolated/shirt.png), [detail](../out/drape-polish/isolated/shirt-detail.png)
- Jacket: [full](../out/drape-polish/isolated/jacket.png), [detail](../out/drape-polish/isolated/jacket-detail.png)
- Folded stack: [full](../out/drape-polish/isolated/folded-stack.png), [detail](../out/drape-polish/isolated/folded-stack-detail.png)
- [Context receipt](../out/drape-polish/context/context-preview-evidence.json), [isolated receipt](../out/drape-polish/isolated/isolated-preview-evidence.json), [independent critic](../out/drape-polish/final-critic-review.md)

The final [preview read-back](../out/drape-polish/final-preview-readback.json)
confirms current geometry, used materials and lights for all eight images.
Full physical mesh, imported-model, prop, material and view values match the
original saved drape scene exactly; original context cameras and fills match
their original receipts. The existing GPU previews remain current after the
value-preserving cost changes, so this resume required no additional renders.

I inspected the neutral context and detail previews. The independent critic
inspected all eight final images. In v32 the new panels and rounded returns
materially reduce the original paper-thin appearance. Shirt front bands and
jacket lapels remain visible. The production folded hem matches the reviewed
prototype.

**What still looks wrong:** the collar bands remain smooth, collar/lapel tips
and cuffs remain simplified, and the compressed hanging panels look unusually
regular. Folded stacks still have broad smooth, pad-like caps and repeated,
sharp hem endpoints. Their slight irregularity and visible hem improve the
reading, but numerical relief/depth checks do not prove photographic fabric
likeness. Lead visual acceptance remains pending.

## Build cost and validation

The unchanged complete-build budget is 120 seconds. Initial refusals measured
129.990972 seconds and 124.668177 seconds (the latter instrumented by phase).
The first uninstrumented replay after the cost fix measured 120.550091 seconds
and also refused; an unchanged-code replay measured 128.344659 seconds and
refused. These failed receipts remain in `out/drape-polish/`.

The cost fix changes copying and memoization, not geometry or review arithmetic:
validated imported-model pair values use independent canonical JSON copies;
immutable face snapshots cache their exact tuple hash and reconstruct it after
transport. Complete imported-model input keys retain exact finite-float face
buffers and canonical remaining fields, reconstructing the former JSON model
before the unchanged constructor; other coordinate types retain the original
path. On the real saved pair rows, deep copy took 1.137 seconds versus
0.109 seconds for the canonical copy, with equal values. Frozen old-selector,
renamed/translated, mutation and process-transport regressions prove preserved
values, independence and unchanged admission refusal.

The final fresh complete build measured **111.458116 seconds**, below the
unchanged 120-second budget, exit 0:
[log](../out/drape-polish/fresh-build-final.log),
[measurements](../out/drape-polish/measurements.json). It retains all 101
appearances and reports zero forbidden contacts. The earlier critic's timing
paragraph predates this cost correction; its visual findings remain relevant.

Validation uses `NO_COLOR=1` and process exit status:

- Acceptance/affected-regression batch: **160 tests passed, exit 0**;
  [log](../out/drape-polish/acceptance-final.log),
  [receipt](../out/drape-polish/acceptance-final-receipt.json).
  Includes the new polish/build-cost tests, `tests.test_drape`,
  `tests.test_garments`, `tests.test_render_standard`, `tests.test_render_views`,
  physical-part and imported-admission regressions, synchronized agent assets
  and neutral-preview controls. The interrupted earlier acceptance log is
  superseded by this complete run.
- Portable verification, normal HOME: exit 0, all pass;
  [log](../out/drape-polish/verify-portable-normal.log),
  [receipt](../out/drape-polish/verify-portable-normal-receipt.json).
- Portable verification, initially empty HOME: exit 0, all pass;
  [log](../out/drape-polish/verify-portable-empty-home.log),
  [receipt](../out/drape-polish/verify-portable-empty-home-receipt.json),
  including the empty initial directory listing.

The lead owns the full suite and commits. No shared-data symlink was modified,
no package was installed, and no presentation image was rendered.

Lessons to register: `drape-polish-thin-tailoring`, `drape-polish-folded-edge`,
`drape-polish-portable-construction`, and `drape-polish-build-budget`.
Controls/proving tests are mapped in [the registry](../knowledge/drape-guards.json),
indexed in [LEARNINGS.md](LEARNINGS.md), and documented in
[the workflow](ops/drape.md); canonical skill/adapters are synchronized.
