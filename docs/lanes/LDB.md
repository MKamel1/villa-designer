# LDB: landscape-layout/1 -> 3D garden in a Blender preview scene (2026-11-22)

Stage LD-B of `docs/quality/LANDSCAPE-METHOD.md`. **Preview only**: nothing here touches `villa_render.py`, `villa_scene.py` or the production scene
(lane L6d). Built and proven on concept A (pond east); concept-agnostic (all six pass-2 layouts build).

## Round 3 (2026-11-22): the DECIDED garden (layout-final, concept B adapted; shade trees, no pergolas)

**Preview only, as before.** What round 3 added (code `src/archpipe/landscape/build/`, tests `tests/landscape/build/test_build2.py`, 41 tests; legacy suite 47; all 88 green):

| # | feature | where | proof |
|---|---|---|---|
| 1 | **No pergolas.** A pergola canopy is reported (`pergola NOT built`) and not built (`build_scene(..., pergolas=True)` keeps the builder). **Pruned shade trees**: a layout tree with `pruned: {spread_m, height_m, clear_stem_m}` (or `pruned_spread_m`, `canopy`) is built at the PRUNED size, not the species' natural size: a graded asset scaled non-uniformly to the pruned canopy (`mode: xyz`), else a labelled STAND-IN umbrella (trunk + 7 overlapping clumps, clear stem). **Root barrier** where the layout declares `root_barrier` on a tree (ring round its bed, or a 1.0 m ring) or a `root_barrier` feature (rect): 0.9 m deep sheet, top flush with the ground (depth/thickness ASSUMED, no figure is claimed). | `planting.pruned_tree`, `elements.root_barrier`, `provisional.py` (a PROVISIONAL tree to exercise it until LDG's layout declares trees) | `ShadeTree` tests |
| 1b | **Climber panels on every wall and screen** a climber is planted at (0.75 m reach): a thin panel on the garden face, trimmed to the free stretch round the plant (benches, pots, tables stop it); a structure with no climber is a `warn` finding and a build warning, never invented planting. Panel = graded curtain asset (tiled, <= 6 tiles) > graded leaf-scan atlas (`assets.json` `climber_panels`, lane LDL) > procedural leaf-cutout STAND-IN (deciduous ones go bare in the winter render). | `planting._climber_panel`, `build.climb_target`, `checks.climber_coverage` | `Climbers` tests |
| 2 | **Shared fire pit on the west line**: only OUR half is built (chamber, burner, flame, cover), detected from `shared_boundary` and the garden edge; the cover is a steel plate carrying the SAME 0.6 x 0.3 running-bond units on the grid of each paving rect under it (so the pattern runs across the cover); covered and open states (the open cover, paver face up, lies beside the pit). The sister half exists only in the visualisation scene, tagged. | `elements.firepit/cover_parts`, `build.pit_half/grids_for`, `checks.pit_half` | `FirePit` tests incl. a wrong-grid negative |
| 3 | **Pond section as specified**: vertical 150 mm freeboard face, entry slope 1:4 over 0.6 m (150 mm drop) to a 0.3 m shelf at 150 mm below the water, a 0.5 m trench at 900 mm, far wall vertical; rigid grille 40 mm under the water on a rib on the shelf edge and on the walls; 80 mm contrasting flush lip (inside the pond rect, top at ground level, overhanging the water on a bearing ledge). The water is a closed solid in the model (measured) and one transparent surface with a Fresnel reflection and a ripple in the render; the depth tint is in the liner (Z ramp). **Koi at the stocking count** (2 north, 4 east) from the free CC-BY asset `skf_3e1b80c3` (SDPM Esare, Sketchfab, CC Attribution, graded B), swimming along the trench below the grille. | `elements.pond/pond_profile`, `outdoor.fish_obj`, `checks.pond_section` (measured from the built vertices, 9 figures per pond) | `PondSection` tests |
| 4 | **Visualisation build**: our garden + the layout-visualisation garden mirrored on the sister plot + the sister half of the pit; every sister object `ld-vis-*` and tagged; red VISUALISATION ONLY band burned into the top and bottom of EVERY image, re-detected pixel-wise. **Guard** (`guard.py`): `Scene.visualisation_only`; `export.to_villa_scene`, `report.schedule`, `report.element_table` raise; `checks.run_all` filters the sister objects out; a render may only go to a directory named `visualisation`; a scene carrying sister objects without the flag is refused; no module outside `landscape/build` may import `visualisation` (a test scans `src/`); the production outputs are scanned for `ld-vis-`. | `visualisation.py`, `guard.py` | `Visualisation` tests |
| 5 | **Outdoor furniture and koi**: `knowledge/landscape/build/outdoor-assets.json` (28 Sketchfab + 6 Poly Haven downloaded, 19 graded, 16 rejected, licences and attributions in `docs/lanes/LDB-assets.md`). Used: dining table `skf_4febe1ee` (Worn garden table, toxiccrack, CC-BY, B, 648 tris, stretched 0.71 -> 0.9 m wide), 8 chairs `skf_7f558fcd` (Patio Chair, pigfinite, CC-BY, B), koi. The benches are built-in masonry in the layout, so no free bench is used. Anything else keeps the labelled simple geometry. | `outdoor.py` | `OutdoorAssets` tests |
| 6 | Planting at age 3 and at maturity from `assets.json` (unchanged rule: drawn only from a graded A/B asset of the species or genus, else a labelled stand-in). The English-ivy curtain asset (grade B) is a Fab FBX archive that is not extracted on this machine, so it cannot be drawn: it stays a stand-in. | `planting.py` | schedule |
| 7 | Review set through jobq, exposure fixed per group (`preview.EXPOSURE`), see the previews section | `preview.py` | `PreviewGuards` tests |

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

## Concept A result (age 3, `knowledge/landscape/build/A-pond-east/`)
114 objects (113 + the second cover state). Individuals: **2 drawn from graded assets** (pomegranate `skf3_f697f7da` grade B, species fit; potted frangipani `sf_frangipani` grade A, genus fit),
**53 generic stand-ins** (9 species: salvia, justicia, pennisetum, jasminum, petrea, origanum, aspidistra, acorus, alpinia: none has a drawable asset), **1 omitted** (a justicia the layout puts inside the pot).
Checks (`checks.json`): ids 114/114; footprints 97/97 within 20 mm (both cover states); stand-ins 55/55 labelled; support 225/225 grounded; **clips: 1 real conflict** (below). At maturity: 7 clips (the pomegranate
through both pergola roofs and the fence, a jasminum at the fence, two salvia/justicia touching the dining pergola, the pot/justicia), reported not hidden.
Blender receipt (`previews/age3.receipt.json`, measured in the render): both assets stand on the ground (base error 0.0 mm) and reach their target height.
Previews (`previews/`): `age3-bird-south-east`, `age3-bird-north-court`, `age3-eye-living-door`, `age3-eye-dining-door`, `age3-firepit-closed`, `age3-firepit-open`, `mature-*` (3). Cycles 128/96 samples, Nishita
sky at a fixed 52 degrees, AgX, house box hidden from camera and shadows in the bird's-eye views. **Not exposure-locked, not a production render.**

### What reads as real, what reads as fake (I looked at each image)
* Real: the paving (running bond, joints, cut around the pit), louvred pergolas with correct cast shadow stripes, the trellis with its lattice, the plaster wall with the built-in seat wall, the pit opening with liner and burner
  (open state), the young pomegranate (airy, real leaves) as a tree of the right age.
* Fake: **every stand-in plant** (smooth eggs and discs in one flat green: honest, but nobody would take them for plants; at maturity they merge into lumps); the table and chairs (cardboard-simple, no joinery);
  the **pond water reads as a flat grey slab** (it mirrors a white wall and has no koi, no marginal planting that is drawable, no bottom detail); the closed fire-pit cover is a plain disc, so the pavers do not run
  across it and it reads as a round plate, not as continuous paving; the bird's-eye ground outside the plot is an empty beige plane; the house is hidden. The dining-door view is dominated by a blank white fence.

## Layout findings for LDG (real, from the checks)
1. `pergola-bench` rect starts at y -28.216 while the pomegranate trunk is at y -28.116: **the tree stands inside the pergola footprint**, 0.49 m from a corner post (clip at age 3), and its mature crown (3.7 m) goes through the louvres at 2.6 m.
2. A justicia at (27.857, -21.416) sits inside the pot rect (pot-0-plumeria). Omitted by the build.
3. The pot is 0.31 m from the rear fence: a frangipani crown cannot develop; the build restrains it to a 1.1 m crown (0.8 m high at age 3). The frangipani size is a GAP in LDL (assumed 1.8 m).
4. `LS-POND-EDGE-SLOPE` 1:4 cannot be built in a 1.0 m wide, 0.85 m deep (below the water) pond; the slope applies to a margin, not the water body: say which.
5. The layout reuses ids (`paving-0` in each garden); and 6.2 m2 of the north court and 8.7 m2 of 'gravel' dining zone area have no surface in `paved_areas`/`zones` agreement (built as labelled `ld-ground-*`).
6. Concepts B and C carry polyline paths (not built, warned); chairs at the pergola corner posts clip in B and C (corner posts cannot move).

## What the production integration needs (not done here)
* **Hook**: `villa_render._build` calls `LAND.build(sp, lay)` and extends `meshes`/`props`/`notes`. A new `LDB` branch of that call would be `export.to_villa_scene(build.build_scene(layout, age=3))`
  (meshes with `element_ids`, props with `gltf`, `scale_to_height_m`, `base_at`). Replace, not add to, the existing garden meshes (G-series `landscape-*` ids).
* **Materials**: the scene's material table has none of `paving-unit`, `paving-joint`, `path-unit`, `bed-soil`, `gravel`, `ground`, `wall-render`, `trellis-timber`, `pergola-alu`, `table/chair/seat-timber`, `terracotta`,
  `pond-concrete`, `pond-edge`, `grille-steel`, `water`, `pit-steel`, `lava-rock`, `burner`, `cover-top`, `flame`, `bbq-steel`, `standin:r,g,b`. Each needs a stated finish (the preview's are procedural stand-ins), water needs the glass/transmission rules.
* **Assets**: the production prop loader reads `assets/library/props/<id>/model.gltf`. The `skf3_*` assets live in `~/archpipe/shared/assets/user/landscape/sketchfab/<hash>/scene.gltf` and are not in `ops/workstation/library-manifest.json`; add them (CC-BY: author credit in the credits list) and give the loader the scale-to-height and base-centroid placement (`preview_blender.place_asset` is the reference).
* **Receipts**: whole-mesh hashing consumers (`exposure_groups.transport_digest`, drape/appearance records) will see new meshes: the garden receipts, exposure record and `furniture_stage2` hashes must be re-derived after the swap (see INT2 lessons). `export.py` declares `element_ids` at creation (P2 'declared'), so no `element_ids.attach` change is needed, but `without_ids` consumers should keep working.
* **Exposure groups**: the garden views use `exterior-day` (EV100 14, 5500 K). Water, the open-pit flame (emissive) and any garden lighting (L6) are separate dominant-light concerns: the open-state flame view needs its own group; the flame here is a prop, not photometry.
* **States**: the fire pit cover has two states under one id; the production view table needs a per-view `state` (`closed` default) that hides the other mesh set.
* **Plant realism** is the blocking quality gate: stand-in eggs will fail a realism critic. Needs more drawable species (LDL: 45 species still without a graded free asset) or a better honest mass (e.g. a leafy volume, not a smooth ellipsoid).

## Open items
Polyline paths and `steps`/`level_changes` (none in A); the closed cover has no paver pattern across it; pond finish and koi; water and plant look; supplier certificates (grille, cover, pond) stay with the suppliers;
a growth curve for age (policy numbers are ours); the chair/table library gap (outdoor furniture assets); pergola beam sizing (the 5.4 m bench pergola beam is unsupported on the bench side).

## Round 3 previews (`knowledge/landscape/build/round3/`, CPU Cycles through jobq, 1500 px, 64 samples, exposure fixed per group: bird/eye/court/grape/vis -3.2, pond -2.8)
**The scene is the final layout plus a PROVISIONAL olive (`provisional.py`), because LDG's layout still declared pergolas and one tree when this was built; re-run when LDG lands.**
Files: `age3-bird-south-east`, `age3-eye-living-door`, `age3-eye-dining-firepit`, `age3-firepit-closed/open`, `age3-court-north-pond`, `age3-yard-east-pond`, `age3-pond-close-*`, `age3-pond-koi-e-pond`, `age3-grape-summer`, `age3-winter-grape-winter`, `mature-*`, `visualisation/age3-vis-bird` (band verified).
* Reads as real: the pond water (dark, reflective, grille and the koi visible below the surface, lip contrasts), the weathered table and patio chairs (free assets), running-bond paving with the cover continuing the joints, rhapis/date palms.
* Reads as fake: every stand-in plant (green balls, incl. the row on the pond edges), the olive stand-in (a pale cloud on a stick), the climber panels (a flat speckled veil; winter is a twig network that looks like cracked glass), the huge empty beige ground plane with hard shadow edges in the bird's-eye, the fire-pit flame (a tiny dot), the grille (reads as a glass-block grid).
* Not shown: tree winter state (asset crowns cannot go bare); fire pit sister half only in the visualisation.

## Production integration needs
Material names to map (`water`, `pond-liner`, `pond-edge`, `grille-steel`, `climber:*`, `trunk-bark`, `root-barrier`, `paving-unit` on the cover); props carry `placement` (mode, scale_xyz, box_m, yaw, tiles); water must be a top surface only; ground plane must be opened over ponds; `guard.refuse` must stay at the seam; supplier certificates for cover, grille, pit.
