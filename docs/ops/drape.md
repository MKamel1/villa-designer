# Hash-bound garment drape

Physical parts remain the unchanged closed garment solids in
`scene['meshes']`. They supply C3 (solid admission), C4 (mounting/support) and
C8 (geometric relationships), slots and occupancy. Never place an appearance
in that list or replace these solids with cloth. `draped_appearances` binds
rendered shells to every eligible physical part by its exact content hash;
the renderer substitutes geometry while preserving identifiers and cameras.

`knowledge/drape-appearance-policy.json` pre-registers ASSUMED morphology and
spacing screens. The envelope is the tight axis-aligned box measured from the
part's unchanged vertices. Containment of all shell vertices also establishes
containment of their linear faces. These bounds are occupied conservative
collision envelopes for neighbouring clothes; forbidden joinery and door
surfaces are checked against the rendered envelope. Only the named physical
support may contact the textile. Cloth is not asserted to lie in the material
of the old extrusion. Internal wardrobe component voids are not solid walls.

Bake with the project Python and `PYTHONPATH=src`:

```text
scripts/drape_build.py
scripts/drape_evidence.py --fresh
```

The build driver runs the pinned workstation Blender twice in separate
processes for each unique input. It hashes source shape, policy, generator and
runtime, validates closed shells, morphology and envelopes, and writes the
owned `knowledge/drape-cloth-cache.json.gz`. Matching intact process results
are reused. A new source shape or stale cache fails closed and requires this
bounded bake. Normal scene builds read the cache and never launch Blender.
Paths and executable identity are explicit, independent of HOME.

The pattern uses regular cloth grids, shoulder pins, gravity, a fixed seed,
48 frames and one solver thread. The policy master seed contributes to the
complete input record; `scene_reproducibility.stable_seed` derives each
pattern seed from that record. Independent processes use Python hash salts
0 and 987654. Procedural shelf textiles use rounded layers
and slight irregularity. Cloth shells have 0.8 mm thickness. Initial patterns
are authored assumptions, not physically measured fabric products. No output
clamping or geometry modifier is permitted to pass an envelope check.
The initial pattern may be corrected and simulated again after diagnosis.
Pins are only measured top shoulder-boundary vertices; an interior upper band
can prevent local shoulder/underarm relaxation. Keep necklines and body cells
free. Store textile shader overrides separately from physical/shared material
dictionaries, and apply them only in renderer/evidence-owned copies.
Normal builds carry compact cache references instead of expanded world face
lists. Each reference binds the physical part, exact local input/template,
placement, world mesh hash, measured bounds and enclosure. Morphology reductions
remain inequality screens and evidence, not cross-backend identity fields.
Unmodified references are reconstructed and compared before collision review; actual world extrema are checked against exact live
physical bounds rather than the rounded local cache key.
Unknown keys, extra/missing fields and altered placement/bounds refuse. The
renderer/evidence reader expands faces only after admission. Cached template
admission binds complete file/input bytes, never mutable object identity.
World mesh hashes bind ordered face lengths and little-endian 64-bit float
coordinates; source/local process receipts use canonical JSON hashes.
Imported pattern helpers (stable seed, rounded ring and loft) have explicit
source-function hashes; the Blender entry point refuses dependency drift.

`--fresh` records the complete authored-view build against the unchanged
120 second budget. Failed timings retain diagnostics and exit nonzero.

Warp/weft topology matters: refining triangle fans can amplify diagonal
wrinkles; paired skins must follow the same folds rather than mirror through
each other. Folded trousers require a curved continuous bar fold and separate legs.
Shirts/jackets have real front openings and rolled collars rather than
single paper-like quads. Sleeve returns remain within the old physical box.
The current one-sheet simulation with post-simulation bulk remains a visual
limitation, as do procedural stack profiles. Numerical screens do not close
those defects. Test one sewn front/back/sleeve pattern in the same isolated and
unchanged context staging before expanding that correction to every cache input.
For forbidden solids, also query enclosed material using signed polygon-fan
surface angles; unsigned ray parity confuses real multi-component joinery
cavities with solid material. Replay the frozen cavity, translated sibling
and fully enclosing solid before accepting that guard.
Neighbour envelopes must include both the physical clearance volume and the
actual rendered bounds: two permitted cloth expansions can meet in a physical
gap without either touching the other's proxy. Replay the frozen actual-layer
gap case, its renamed/translated sibling, the quiet unshifted shapes and the
named-support stack before accepting a contact-check change.

Render only diagnostic previews with the existing graphics-lock reader:

```text
blender -b --python-exit-code 1 -P scripts/garden_g6_preview.py -- --input out/drape/specimens.json --output out/drape/isolated --samples 48
blender -b --python-exit-code 1 -P scripts/garden_g6_preview.py -- --scene --input out/drape/neutral-scene.json --output out/drape/context --views v31-dressing-hers v32-dressing-his --samples 48
```

Do not move slots, rails, wardrobes, doors or context cameras. Context keeps
the original diagnostic world, exposure, emission suppression and two recorded
white area fills. Isolated specimens include the 1.8 m reference and close
views. Read images and warning receipts, record defects plainly, and keep
lead acceptance pending until the lead reviews them. Run `tests.test_drape`,
`tests.test_garments`, the furnishing/dressing and render standard/view tests,
then `scripts/verify.py --portable` under normal and empty HOME. The lead owns
full-suite runs and commits. Report paths in `docs/drape-report.md` and retain
its lessons-to-register line.
