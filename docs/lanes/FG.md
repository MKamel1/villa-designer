# FG: generated foliage (client-approved 2026-11-22)

Plants grown from each species' sourced habit and the client's Fab leaf scans, replacing the egg stand-ins and the
candelabra crape. Code `src/archpipe/landscape/foliage/`, data `knowledge/landscape/foliage/`, tests
`tests/landscape/foliage/` (17). Free items still to download: `knowledge/landscape/foliage/DOWNLOADS.md`.

## What it is

| piece | file | what it does |
|---|---|---|
| leaf banks | `banks.py` -> `banks.json` | finds every single, live, green leaf in a Megascans atlas's Opacity map (RED channel), orients it (PCA, base = stalk end or broader end), cuts the petiole off. Dead-leaf filter (G/R >= 1.0), petal filter, merge/hole filters. Star jasmine: 20 cut-outs, 5 dead dropped, 15 kept. Also two **generated outlines** (Fatsia-like 9-lobed, grape-like 5-lobed) whose *surface* is a Colocasia scan |
| habit | `species.py` | form + leaf bank + leaf size per species (ours, marked `policy`). Height/spread RANGES are never stored: read from `plants.json` (sourced) |
| skeleton + leaves | `generate.py` | numpy, deterministic per seed. Skeleton: polylines with jitter, light/gravity tropism, pipe-model taper, golden-angle branching at normal-distributed angles, pruned to a superellipsoid habit envelope. Leaves: scan cut-out cards on twig nodes (opposite/alternate), phototropic normal, droop (`arch`), per-leaf colour variation. Forms: shrub, climber (grows in the x-z plane, faces +y), tree, basal, petioled, strap, cane |
| Blender | `blender_build.py` | tube meshes + bent, V-folded 3x5 leaf cards; material = scan BaseColor x per-leaf vertex tint, Opacity from the RED channel, Roughness, Normal, 30 % translucent BSDF (two-sided); `sheet` mode renders the LDL rubric sheets; `glb` mode exports |
| library | `library.py` | `plant_for`, labels, `validate_label`, `caption`, `schedule`, manifest |

## Integration note for lane GI (placing generated plants like graded assets)

Same contract as a graded asset: **built at the size you pass, base on the ground at the origin, stable by element id.**

```python
from archpipe.landscape.foliage import library as FL
plant = FL.plant_for(species_slug, element_id, height_m, spread_m, state="leaf-on")   # seed = crc32(element_id)
plant.label      # generator_version, seed, atlas_used, atlas_species, fidelity, caption  -> put in the schedule/receipt
FL.caption(plant.label, close_up=True)   # the ONLY text a caption may use; a form-class plant is never named as the species
```
* **Inside a Blender job** (best: full material with translucency): `from archpipe.landscape.foliage.blender_build import build_plant; objs = build_plant(plant)`;
  parent `objs` to an empty at the plant position; rotate about +z. Climbers grow in the x-z plane with leaves facing **+y**:
  rotate so +y is the wall's garden-side normal; width = `spread_m`, height = the structure height (`height_m`). Trees:
  `state="leaf-on"|"leaf-off"` (same skeleton), `lean=(dx, dy)` shifts the crown (layout `crown_lean_m`), `height_m`/`spread_m` from `pruned`.
* **Portable glb** (no Blender import of our code): `python -m archpipe.landscape.foliage.library bake` once, then
  `blender -b -P src/archpipe/landscape/foliage/blender_build.py -- glb --out DIR --spec slug:seed:H:S:state` (jobq `--gpu` not needed; CPU is fine).
  glTF cannot carry the translucency or red-channel wiring: the glb has RGBA atlas cut-outs + COLOR_0 tint (checked: imports into Blender with leaves cut out and tinted).
  Built glbs for the demo seeds are in `~/archpipe/shared/assets/generated/foliage/glb/` (not in git: 5-37 MB each).
* Size: crape 24k leaf cards ~ 0.4 M triangles (`lod=1` halves leaf count, `lod=2` quarters it, leaves enlarged to keep the mass); shrubs 2-6k cards.
* Scale rule: pass the **layout** `spread_m` and the height from `planting.mature_size`; the generator fits the measured bounding box (leaf tips included) to both.
* Do not reuse the egg/candelabra stand-ins for species listed in `schedule.json`; keep the stand-in only as the fallback when this package is absent.

## Labelling (non-negotiable)

Every plant records `generator_version`, `seed`, `atlas_used`, `atlas_species`, `fidelity`, `leaf_len_source`. `fidelity: species` only if the
single atlas is a scan of that species and its outline is scanned. In the current library **only star jasmine (*Trachelospermum jasminoides*) is
`species`**; everything else is `form-class`: no scan of that species is held (Arabian jasmine, petrea, justicia, salvia leucantha, acorus, farfugium,
fatsia, grape, alpinia, crape myrtle). `validate_label` refuses a `species` claim whose atlas is another species or whose outline is generated.

## Grades (LDL 5 m / 15 m rubric, by eye on `knowledge/landscape/foliage/sheets/`; own rubric, not a standard)

See `grades.json` for the table with sheet paths; summary in the hand-back. Reference photos of the species were NOT fetched in this unattended run: the
comparison is against the sourced habit text and my knowledge of the plants, which is a weaker check than the rubric asks for (open item).

## Not done / limits

* No flowers: the only flower scan held is bougainvillea, and bougainvillea is not in the layout (petrea's calyces would be an invented flower). Justicia
  bracts, salvia spikes, fatsia umbels, crape panicles are absent. Flower-card support is not implemented because nothing may use it.
* Creeping fig is a wall *texture* with no cut-out map, so it cannot be generated; keep the LDL texture wall for it.
* Colour: leaf colours are stated targets (`colour` in `species.py`, policy) applied to the scan's mean colour, not measured from reference photos.
* Crape bark: Poly Haven `bark_platanus` (CC0) - mottled smooth bark, not a crape-myrtle scan.
