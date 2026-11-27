# SOFT lessons (client 2026-11-25: "the pillow on couch and beds looks very unrealistic and rigid and bad texture")

## Rigid, board-like cushions with a stretched carpet-photo texture

**What was wrong (diagnosed on the 2026-11-25 scene, 14 scatter cushions, 5 throws, 1 box pillow, `out/soft/base`):**
- *Shape.* `interior/soft_dressing.pillow()` is a formula shell: dead-flat crown (front-face normals fan out 31-35 deg at the 90th
  percentile; the real scanned Poly Haven pillows 70-71), knife-edge rim, symmetric about a mid-plane. The bunk-bed pillow is a
  6-face box. The throws were flat sheets (spread 0 deg).
- *Fabric.* The `fin-cushion-*` materials sit outside the fabric list in `villa_scene.add_material`: no sheen, no bump, roughness
  0.5 (plastic). The bouclé cushion was `Carpet016` at `tile_m` 1.7 m: loops of 10 mm where bouclé is about 3-9 mm. The
  white bedding is `Fabric081C` at 0.18 m: an 8.8 mm weave on a cotton sheet.
- *Contact.* On the procedural cinema, lounge and study sofas the rigid cushions sank 50-66 mm into the seat and back cushions
  (they were authored for the library living sofa's geometry). Nothing flagged it: `render_support.unsupported` only tests
  support from below, not sinking.
- The living, parents' and library sofas are imported scans; their proxies are hidden. Only the cushions, throws and the
  procedural sofas were ours.

**Why it was missed.** Every earlier check measured placement (inside the frame, supported, inside the envelope), never the
*form* of a soft object or the scale of its weave. The photoreal-render skill's step 6 ("soft goods drape?") was only enforced for
duvets. A look-alike texture's tile was taken from the scan size without comparing the weave it produces with the real fabric.

**Fix.** `blender/soft_goods.py` (render-time, like the cloth duvets): pressure-inflated two-panel cloth baked once
(`blender/soft_bake.py` -> `knowledge/soft-cushion-bakes.json.gz`), fitted to each rigid cushion's footprint, base on its
old rear plane, a karate-chop dent on one in three, then moved out of any host it sinks into (up out of a seat, forward out of a
back). Throws are a baked cloth drop over a rolled lump. Fabric classes (`knowledge/soft-fabric-classes.json.gz`) set tile from
the measured texture feature size, roughness 0.9, sheen/fuzz scaled to the colour (a dark cloth's sheen is dark), a
mm-scaled bump and a few-cm mottle. Colours are untouched (maker-image means, client schedule).

**Guards (all fail on the real defect, all stay quiet on the scan):**
- `critic/furniture_realism.py`: `soft-shape` (crown spread < 45 deg; throws < 25), `scale`, `box`, `flat`, `float`, `penetrate`
  plus the VLM question per crop. `tests/critic/test_furniture_realism.py` uses the real rigid cushions (fixture) as positives and the
  scanned pillow and the baked cushions as negatives.
- `soft_goods.assert_soft_goods_real` runs inside `villa_scene.render`: a rigid or sunk cushion cannot reach a render
  (`--no-soft` is for before/after comparison only).

**Limits, stated.** The thresholds and fabric feature bands are ours (`policy`): the held books have no weave, cushion-shape or
edge-radius figures (knowledge search 2026-11-25, no hits). The check measures what is in the scene; imported scans are judged by the
VLM crop only. The VLM is a second opinion, not a gate.


## Round 2 (2026-11-25): the throw, the weave scale, the edges

**The throw: why it was a plate and why the first cloth attempt "fell through".** Two separate causes, found in a small scene
(`blender/soft_drape.py`, one throw, one sofa, a box host in `scratch`):
1. *The authored position was off the sofa.* `soft_dressing.seat_dressing` places the throw from a seat frame; on the lounge, study and
   cinema sofas 0.2-0.4 m of it hung past the seat end or front, and the living sofa's imported scan has a different seat from
   its proxy. A baked lump fitted to that footprint is a plate cantilevered into air. The drape now first moves the drop point to
   where most of the footprint has host surface under it (`landing_spot`), and the bake refuses a throw with under 60 % support.
2. *The first sim had no floor and too little friction.* A 0.65 x 1.3 m sheet slid off the seat over 40 frames (cloth friction 10)
   and fell out of the world: z -13 m looked like "through the sofa". Fixes, each measured in the small scene: collision friction 50,
   a floor plane at the host's lowest point, cloth quality 20 / collision quality 8, a distance of 4 mm.
3. *The host mesh must be one watertight shell.* glTF parts overlap, carry fins and inconsistent winding; the sheet tunnelled
   through 3-8 vertices at the seat front (clearance measured against the product as imported: 164 intersections). A 4 mm voxel remesh of
   the joined hosts as the collider gives 0 intersections, 0 inside, 3-12 mm minimum clearance against the original meshes.
   (Not a cause, tried: self-collision at a 2 cm grid needs `self_distance_min` below the cell; a 0.01 object scale; world offset
   of 27 m, which did no harm in the box test.)

The result is baked once per throw (`knowledge/soft-throw-drapes.json.gz`, Blender 4.5.14, ~6 min for five) and used at render
time only while its hosts match their stored signature (ids, triangle counts, boxes to 2 mm, model poses): a changed sofa
falls back to the old lump and is named in `report["stale_throw_drapes"]`. Re-bake: `blender -b -P src/archpipe/blender/soft_drape.py
-- --scene SCENE.json --out knowledge/soft-throw-drapes.json.gz`. The bake refuses a throw with any host intersection or vertex inside a host
(it retries turned 0.2 rad steps first; the cinema sofa needed one).
*Guard:* `tests/critic/test_soft_goods.py::ThrowDrape` (closed shell, not a plate, signature tolerance, stale fallback); the bake itself.
*Why missed:* the realism check measured the throw's shape in isolation (crown spread) and sink into proxies that are hidden for the imported
sofa; it never asked "is there a seat under it". Now the bake asks, and refuses.

**Weave scale on every fabric.** `soften_materials` retiled only cushion and throw materials; the dining chairs, vanity chair and lounge sofa
share `boucle` and kept 1.2 mm loops. It now applies to every fabric material on a visible furniture or dressing mesh (garments excluded),
so one rule covers the next chair. *Guard:* `FabricScaleEverywhere`; the realism check's `scale` finding.

**Edges.** The generators authored `bevel_m=0` for the garment-module joinery and 1.5 mm on some cabinets, and the check's floor is 2 mm.
`soft_goods.ease_edges` (one rule, in `soften_scene`) raises case goods to 2 mm and upholstered boxes to 6 mm, smooth-shaded; glass,
garments, hidden proxies and already-rounded pieces are left alone. *Guard:* `EasedEdges`; the realism check's `box` finding.
*Left:* the seven imported desk scans (85-89 % axis-aligned): their geometry is the product's, not ours.
