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

Every plant records `generator_version`, `seed`, `atlas_used`, `atlas_species`, `atlas_match` (`species` | `genus` | `none`), `fidelity`, `leaf_len_source`.
`fidelity: species` only if the single atlas is a scan of that species and its outline is scanned. **Species now: star jasmine
(*Trachelospermum jasminoides*) and grape (*Vitis vinifera*, Common Grape Vine scan, client download 2026-11-22).** Pittosporum tobira is `form-class`
with `atlas_match: genus` (Australian Laurel = *P. undulatum*). Everything else is form-class (`none`). `validate_label` refuses a `species` claim whose
atlas is another species or whose outline is generated.

## Client Fab downloads (2026-11-22): manifest, use, rejections

`knowledge/landscape/foliage/assets_manifest.json` (script `knowledge/landscape/foliage/tools/fg_manifest.py`): sha256, listing URL, licence for the 15 Fab zips and the two
Poly Haven textures. Fab: Personal+Professional, commercial use allowed, no standalone redistribution (zips stay out of git). Poly Haven: CC0.
Sprig atlases (Weeping Fig, Chinese Wisteria) are cut into single leaves by erosion; a card keeps only its own leaf (cleaned opacity map in
`generated/`, isolation test, pale/lime leaves dropped for Australian Laurel).

| class | leaf bank | fidelity |
|---|---|---|
| grape | Common Grape Vine | species |
| Pittosporum tobira | Australian Laurel | form-class, genus match |
| Justicia | Weeping Fig | form-class |
| Salvia leucantha | Australian Laurel (narrowed) | form-class |
| Arabian jasmine, Petrea | Chinese Wisteria leaflets | form-class |
| Acorus | African Flag blades | form-class |
| Farfugium | Taro (kept) | form-class |
| Fatsia | generated palmate outline, Taro surface (kept) | form-class |

Tried and not used (sheets rendered, judged by eye): **Spotted Laurel** is *Aucuba* with toothed, yellow-speckled leaves, wrong for Justicia (plain
green): atlas and the 3D FBX not used. **Tree Philodendron** for Fatsia: narrow pinnatifid leaf, the plant reads as a philodendron. **Elephant Ear** for
Farfugium: pointed sagittate leaf, worse than Taro. The Spotted Laurel FBX is unused (not needed by any class).

## Grades (LDL 5 m / 15 m rubric, by eye on `knowledge/landscape/foliage/sheets/`; own rubric, not a standard)

`grades.json` has grade_before, grade, why, sheet, reference photo for each class. Every class was compared with a public reference photo
(Wikimedia Commons, licences CC0 / CC BY / CC BY-SA, recorded in `grades.json`; used for grading only, not committed). Result: vitis C->B, pittosporum
new B, farfugium B->C (stricter against the reference), petrea C, salvia C, the rest unchanged B.
Salvia and Petrea stay C because their identity is the flower (purple spikes, violet calyx racemes) and no scan of either exists; nothing was invented.

## Crape myrtle bark

Compared against two reference photos of *Lagerstroemia indica* (pale grey-tan to pinkish, smooth, mottled, flaking in thin plates): Poly Haven
`bark_platanus` is dark brown and finely cracked (reads as plane/oak); Fab Banyan Bark 4K is pale grey-tan, smoother, mottled. **Banyan Bark chosen**
(`FG_BARK`, default `banyan` in `blender_build.py`; `platanus` and `sakura` selectable). Both were rendered on the same leaf-off tree.
(The previous run's bark path used a directory that may not have existed, so the earlier platanus claim was not verified in the render.)

## For lane GI: mulch and soil (not built here)

Planting-bed ground, in `~/archpipe/shared/assets/user/landscape/fab/unzipped/` (glTF + PNG maps, `Textures/T_<id>_4K_{B,N,ORM,H}.png`):
* `mulch_omsvgjp0_4k_ue_high`: fine bark-chip/gravel mulch (orange and dark chips), scan area 0.74 x 0.74 m, 4096 px. Tile at 0.74 m. Use under shrubs.
* `soil_mulch_sfwnbgba_4k_ue_high`: dark brown fine soil with fibres, scan area 2 x 2 m, 0.07 m relief, tileable. Use for the finer bed.
The glTF is a 2-unit plane: set UV tiling from the physical size above, not from the plane. ORM = occlusion/roughness/metal, H = height.

## Not done / limits

* No flowers: no scan of the species' flowers is held (bougainvillea is not in the layout). Justicia bracts, salvia spikes, Petrea calyces, Fatsia
  umbels and crape panicles are absent; flower-card support is not implemented.
* Grape: no tendrils or bunches (no usable scan cut-outs); lax habit only.
* Creeping fig is a wall *texture* with no cut-out map; keep the LDL texture wall.
* Colour: leaf colours are stated targets, not measured from the reference photos; Salvia's drifts yellow.
* The sheets were rendered on CPU (ARCHPIPE_CPU=1, jobq without `--gpu`) because the GPU queue was occupied.
