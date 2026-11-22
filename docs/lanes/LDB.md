# LDB: landscape-layout/1 -> 3D garden in a Blender preview scene (2026-11-22)

Stage LD-B of `docs/quality/LANDSCAPE-METHOD.md`. **Preview only**: nothing here touches `villa_render.py`, `villa_scene.py` or the production scene
(lane L6d). Built and proven on concept A (pond east); concept-agnostic (all six pass-2 layouts build).

## Use
```
python -m archpipe.landscape.build.report knowledge/landscape/concept/pass2/layout-A-pond-east.json knowledge/landscape/build/A-pond-east [--render]
```
```python
from archpipe.landscape.build import build, checks, preview, export
scene = build.build_scene(build.load_layout(path), age=3)     # age=None builds the plants at maturity
checks.run_all(scene, "closed")                                # ids, footprints, floating, clipping, stand-ins; state "open" = fire pit open
preview.render(scene, out_dir, "age3")                         # Blender through jobq; returns the receipt (measured asset placement)
meshes, props = export.to_villa_scene(scene)                   # the seam for the production scene (not wired in)
```
Code `src/archpipe/landscape/build/`: `geom.py` (primitives, Obj/Part), `policy.py` (every ASSUMED dimension in one place), `elements.py` (builders),
`planting.py` (species, drawability, size at age), `build.py` (layout -> Scene), `checks.py`, `preview.py` + `preview_blender.py`, `export.py`, `report.py`.
Tests `tests/landscape/build/`. Output `knowledge/landscape/build/`.

## What it builds (all with `ld-*` ids; the layout id is kept in `Obj.layout_id`)
* **Hardscape**: `ld-paving-*` = bedding slab (joint colour) + 0.6 x 0.3 m running-bond units with 8 mm joints, cut around the fire-pit opening and the path
  areas; `ld-path-*` = units laid along the route; `ld-gravel-*` (gravel zones minus built surfaces); `ld-ground-*` (area with no built surface: a gap, labelled).
  `steps` / `level_changes` are warned and not built: concept A has none and layout/1 gives no riser or fall direction.
* **Walls and the 2.1 m west screen**: `ld-fence-*` 4.0 m rendered walls; `ld-sister-screen` trellis (posts <= 1.5 m, rails, 25 mm batten lattice at 150 mm) with
  climbers drawn on its garden face.
* **Pergolas** `ld-pergola-*`: posts (corners + intermediate where the plan is free), two beams, tilted louvre blades at 160 mm (aluminium, ASSUMED sections).
* **Flush pond** `ld-pond-e` (+ `-water`, `-grille`): rim at ground level, water 150 mm below it (layout freeboard), 80 mm contrasting flush lip, safety shelf
  250 mm wide at 150 mm below the water (ASSUMED: GAP-POND-EDGE-SAFETY), rigid grille 40 mm under the surface resting on the shelf, floor at the layout depth.
  The layout's 1:4 edge slope is **not modelled**: with a 0.85 m freeboard-to-floor drop it needs 3.4 m of run in a 1.0 m wide pond. Label says so.
* **Flush gas fire pit** `ld-firepit` (chamber, burner), `ld-firepit-cover` in two states (`closed`: paving-faced disc 6 mm proud = layout lip; `open`: set aside on the paving)
  and `ld-firepit-flame` (open only, an emissive cone, not simulated fire).
* **Furniture**: built-in benches `ld-bench-*` (masonry plinth + timber seat, 450 mm from the layout seat-wall spec), `ld-dining-table` + 8 `ld-dining-table-chair-*`,
  `ld-bbq`, `ld-pot-*`. The library has no outdoor dining table or chair that fits (its only dining chair is an indoor bouclé upholstered chair; the bistro set is
  absent from the manifest), so table, chairs and BBQ are **simple geometry, labelled SIMPLE GEOMETRY**, not products.
* **Planting**: see below.

## Planting rule (garden brief 2026-11-22)
`planting.resolve(slug)`: drawable only when the LDL asset table says `drawable` AND a grade A/B asset of that species or genus exists on this machine AND the table does not flag
it as a look-alike (the orange keeps its lemon asset out). Drawn: the graded glTF, scaled to the sourced height at the stated age. Otherwise: a **generic ellipsoid
mass** at the species' spread (layout) and height (layout or source mid-range) in the foliage colour read from the sourced foliage text (default green, said so), labelled
`STAND-IN` in the object label and the schedule row with the reason. Never another species.
Size at age is **policy** (no growth curve is held): fraction = 0.25 + 0.75 x age / T, T = 5 / 8 / 15 years for fast / moderate / slow (GAP = 8), 3 years for ground cover,
herbs, perennials, grasses. Default age 3, `age=None` = mature. A plant the layout puts inside a pot, bench or other solid is **omitted and reported**, not built through it.
A potted plant is restrained to the clear room round the pot (a pot 0.3 m from a fence cannot carry a full crown).

## Proof (`checks.py`, all pure Python, run on both fire-pit states)
| check | rule | negative test |
|---|---|---|
| ids | every object `ld-*`, unique per state; every layout element has an object | duplicate / missing |
| footprint | plan bbox of each rect-declared object within 20 mm of the layout rect (`bbox`), inside it (`within`), or Hausdorff <= 20 mm (gravel, ground) | 30 mm off, 150 mm too thick |
| plant footprint | stand-in at maturity = layout spread +-20 mm; at an age never wider. Assets: reported, not asserted (the spread follows the asset) | |
| support | every connected group of an object's parts reaches the ground or touches a declared support; above-ground kinds are not sunk | floating 50 mm, sunk 100 mm |
| clip | different objects interpenetrating > 5 mm (exact for prisms; ellipsoid envelope for plants, 50 mm foliage tolerance) | through the table; touching is not a clip; mature pomegranate in the pergola (real case) |
| standin | every generic mass labelled in object and schedule; every drawn plant a grade A/B asset | |

## Open items and layout findings (for LDG)
See the hand-back message and `knowledge/landscape/build/A-pond-east/SCHEDULE.md`.
