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
