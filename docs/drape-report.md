# Draped garment appearance

Continued WIP `1d0d4bc` after integration repair `038e476`; no commits, package
installations, presentation images or shared-data changes. The bedroom remains
an example, and this package approves no real villa-design gate.

The 235 physical dressing parts retain their authored geometry. Rendered
textiles use 101 hash-bound appearances: 25 hanging garments and 76 folded
pieces. Their meshes are separate from the physical Parts collection. C3 means
closed outward solid admission; C4 means mounting/support; C8 means geometric
relationships. Those reviews continue to use the original physical geometry.
Coordinates are metres: x along the rail, y across wardrobe depth, z upwards.

## Construction and admission

Ten unique local inputs are cached in `knowledge/drape-cloth-cache.json.gz`.
Each binds a normalized local shape, garment type, generator, imported pattern
helpers, policy and pinned Blender 4.5.14 LTS runtime. Instance references also
bind the exact unrounded physical part and placement. The source function
hashes include the stable seed, rounded-ring and loft helpers. Every hanging
input uses gravity, 48 frames, solver quality 8 and one thread. The policy
master seed contributes to the complete input-derived stable seed. Both
independent processes use different Python process hash salts, 0 and 987654.
Their complete output hashes match for every input; see
[determinism.json](../out/drape/determinism.json) and its process paths.

The rest patterns use measured shoulder-edge pins, free neck/body vertices,
nonuniform folds, sleeve returns, front openings and rolled collars/lapels.
Fabric thickness is 0.8 mm. Trousers have a continuous curved return and separate
legs. Folded pieces have divided edges and slight deterministic irregularity.
Fabric parameters, cuts, colours, weave and sheen are **ASSUMED**, owned
procedural appearances rather than buyable product specifications.

Scene builds store compact cache/placement references, not duplicated world
face lists. The renderer validates each reference, then expands its mesh.
Physical parts, template, placement, material binding, world mesh hash and
measured envelope remain exact. Shader styling is a separate render override;
physical and shared material dictionaries remain unchanged. Backend-dependent
morphology reductions belong in diagnostics rather than identity fields.

Containment uses exact live physical extrema, even where local cache keys have
rounded coordinates. The sole permitted expansion is the pre-declared 4 mm.
Conservative collision screening includes each neighbour's physical and rendered
envelopes: two permitted cloth expansions can meet in a physical gap. It also
checks joinery and doors, including
fully enclosed material; signed surface angles distinguish joinery cavities
from occupied solids. Only the named physical support may contact a textile.
No output clamp, geometry modifier or design/camera change repairs a refusal.

## Measured results

The policy was pre-registered before the new meshes and marks its screens
ASSUMED. The actual rejected board meshes are frozen by value in
[the fixture](../tests/fixtures/drape-boards-before.json.gz). Every hanging type
fails its original screen; new shells and renamed/translated siblings pass.
These screens establish morphology properties, not photographic quality.

| Screen | Required | Final measured result |
|---|---:|---:|
| Plumb angle between upper/lower quarter centres | at most 3 degrees | maximum 0.139 degrees |
| Mid-height relief after quadratic trend removal | at least 6.5 mm | minimum 10.795 mm |
| Lowest boundary-band height range | at least 1.5 mm | minimum 15.465 mm |
| Escape beyond exact physical envelope | at most 4 mm | maximum 1.900 mm |
| Forbidden contacts | zero | zero |
| Bound physical pieces / appearances | one per eligible piece | 101 / 101 |

A final complete normal-view build took **115.387057 seconds** against the unchanged
120 second budget, exit 0:
[final-current-fresh-evidence.log](../out/drape/final-current-fresh-evidence.log).
The earlier successful checkpoint was 119.582484 seconds
([log](../out/drape/final-fresh-evidence.log)).
Earlier 132.34, 126.36, 124.94 and 124.60 second refusals remain in `out/drape/`.
The full profiler identified repeated float snapshot work and unnecessary
island decomposition of garments disjoint from doorways. The corrections retain
exact coordinates, original overlap thresholds, connected candidates and
finding labels; frozen prior arithmetic/reviewer comparisons prove this.
Normal builds never launch the cloth solver with a warm input cache.

[measurements.json](../out/drape/measurements.json) is the final fresh-build
measurement receipt and includes this complete build's duration. A prior
read-back correctly recorded a null duration instead of claiming a fresh pass.
The final [preview read-back](../out/drape/final-current-preview-readback.json)
confirms that both context and all isolated previews still match the current
geometry/material hashes, cameras and lighting; no new render was needed.

## Neutral previews

All images are diagnostic, with ASSUMED appearance declared in their receipts.
Both context cameras and their original white area fills compare exactly with
`out/garments/context/context-preview-evidence.json`; world, exposure, emission
suppression and diagnostic render settings follow that original reader.

- [v31, hers](../out/drape/context/v31-dressing-hers-neutral.png)
- [v32, his](../out/drape/context/v32-dressing-his-neutral.png)
- [Context receipt](../out/drape/context/context-preview-evidence.json)

Every main isolated image includes the 1.8 m reference figure. Close detail views
are additional diagnostic crops.

| Specimen | Full figure preview | Detail |
|---|---|---|
| Dress | [dress.png](../out/drape/isolated/dress.png) | [dress-detail.png](../out/drape/isolated/dress-detail.png) |
| Abaya | [abaya.png](../out/drape/isolated/abaya.png) | [abaya-detail.png](../out/drape/isolated/abaya-detail.png) |
| Shirt | [shirt.png](../out/drape/isolated/shirt.png) | [shirt-detail.png](../out/drape/isolated/shirt-detail.png) |
| Jacket | [jacket.png](../out/drape/isolated/jacket.png) | [jacket-detail.png](../out/drape/isolated/jacket-detail.png) |
| Trousers | [trousers.png](../out/drape/isolated/trousers.png) | [trousers-detail.png](../out/drape/isolated/trousers-detail.png) |
| Folded stack | [folded-stack.png](../out/drape/isolated/folded-stack.png) | [folded-stack-detail.png](../out/drape/isolated/folded-stack-detail.png) |

[Isolated receipt](../out/drape/isolated/isolated-preview-evidence.json).
The shoulder-edge experiment also preserves its prior staging, materials and
lighting in `out/drape/edge-pin-before/` and `edge-pin-after/`.

I inspected both wardrobe views, all six full specimens and the shirt comparison.
The garments now read as fabric, with plumb soft folds and recognisable collars,
sleeves and hems. What still looks wrong: wardrobe views expose thin profiles;
cuffs and collars remain stylised; fronts/backs derive from one simulated sheet
with sewn bulk constructed afterward; folded stacks remain too smooth and
regular. These images do **not** establish the bedroom photographic benchmark.
Its named image was unavailable locally for direct comparison. The independent
[critic review](../out/drape/final-critic-review.md) confirms all current specimen
hashes and original context cameras/fills, and leaves lead photographic approval
pending. Existing context subject crops were preserved, not repaired by moving
cameras. No presentation set was rendered.

## Validation

Results are judged by process exit status with `NO_COLOR=1`. The lead owns the
full suite and commits.

- Required garment, dressing/furnishing, render standard/view and affected
  regression batch: 210 tests, 209 passed and one frozen-reviewer import error,
  exit 1; [log](../out/drape/final-acceptance-tests.log). The error came from
  loading a fixture outside its original import package; the package-aware
  loader fixes it without altering frozen review arithmetic.
- Final complete drape replay after the fixture correction and rendered-neighbour
  extension: all 20 tests pass, exit 0;
  [log](../out/drape/final-drape-tests-after-contact-guard.log). Together the batch
  and replay cover 211 unique acceptance/regression tests with no outstanding
  failure. The gap mutation, translated sibling, quiet separated geometry and
  support checks also pass their [focused proof](../out/drape/neighbour-gap-proof.log).
- Portable verification, normal HOME: exit 0, all pass;
  [log](../out/drape/final-verify-portable-after-contact-guard.log).
- Portable verification, initially empty HOME: exit 0, all pass;
  [log](../out/drape/final-verify-portable-empty-home-after-contact-guard.log),
  [environment receipt](../out/drape/final-portable-empty-home-after-contact-guard-receipt.json).

Lessons to register: `drape-rigid-soft-goods`, `drape-cavity-containment`,
`drape-cache-build-cost`, `drape-physical-material-state`,
`drape-opening-review-cost`, `drape-runtime-diagnostic-identity`, and
`drape-neighbour-rendered-envelope`.
Construction/checks and proving tests are mapped in
[the registry](../knowledge/drape-guards.json), indexed in
[LEARNINGS.md](LEARNINGS.md), and documented in
[the workflow](ops/drape.md); canonical skill/adapters are synchronized.
