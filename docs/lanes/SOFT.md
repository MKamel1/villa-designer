# SOFT: photoreal soft furnishings and the furniture realism check (client 2026-11-25, item 2)

Client: "the pillow on couch and beds looks very unrealistic and rigid and bad texture. make it hyperrealistic. make this check for
all furniture." Root cause, fix and guards are in `docs/lessons/SOFT.md`. The full ranked list of flagged furniture is
`docs/lanes/SOFT-furniture-realism-ranked.md` (regenerate: `python -m archpipe.critic.furniture_realism --soft --scene SCENE
--library-root LIB --out OUT.json --md docs/lanes/SOFT-furniture-realism-ranked.md`).

## What changed

| path | what |
|---|---|
| `blender/soft_bake.py` | bakes pressure-inflated two-panel cloth cushions (12 shapes) and cloth-drop throws (3) once, in Blender 4.5.14 |
| `knowledge/soft-cushion-bakes.json.gz` | the bakes (committed; a rebake is deliberate, Blender-version bound) |
| `blender/soft_goods.py` | render-time `soften_scene`: fits a bake to each rigid cushion's footprint, rests it on its host, inflates procedural upholstery, assigns fabric classes; post-condition `assert_soft_goods_real` |
| `blender/fabric_nodes.py`, `knowledge/soft-fabric-classes.json.gz` | sheen, fuzz, mm-scaled bump, mottle; tile from the measured texture feature size |
| `blender/villa_scene.py` | calls the above (not in the measuring modes; `--no-soft` renders the rigid goods for comparison) |
| `critic/furniture_realism.py`, `critic/furniture_vlm.py`, `blender/gltf_check.py` | the check |
| `tests/critic/test_furniture_realism.py`, `test_soft_goods.py` + fixtures | positive tests on the real rigid cushions, negative tests on a real scan (Poly Haven `throw_pillows_01`, CC0) and on the baked cushions |
| `knowledge/exposure-groups.json`, `knowledge/render-set/exposure-groups.json` | re-measured (see below) |

## The check, on the 2026-11-25 scene (merged integ/aplus)

Before the fix 185 findings on 173 objects, after 153 on 153 (the soft goods all pass):

| | before | after |
|---|---|---|
| soft goods: sunk into the sofa (`penetrate`, 50-66 mm) | 8 | 0 |
| soft goods: flat crown (`soft-shape`; cushions 31-35 deg against a floor of 45, throws 0 against 25) | 19 | 0 |
| soft goods: wrong weave scale (`scale`) | 3 | 0 |
| upholstery: wrong weave scale | 10 | 8 |
| upholstery: pure box, no bevel | 3 | 3 |
| case goods: pure box, no edge radius | 142 (incl. 7 imported desk scans at 85-89 %) | 142 |

The remaining 153 items are not soft goods; see the ranked file for each with the fix. In short: 8 upholstered pieces (6 dining chairs
and the vanity chair, the lounge sofa) carry a bouclé finish whose weave is 1.2 mm where bouclé loops are 3-9 mm (retile, or choose a
nubby texture); 3 upholstered boxes (two kids' beds, the library daybed) need rounded edges; the 142 case-good boxes need a 2 mm eased edge.

## Honest limits

- Thresholds and fabric bands are ours (`policy`): the held books have no weave, cushion-shape or edge-radius figures (no hits in the knowledge search of 2026-11-25).
- **The VLM cannot gate.** gemma4:12b and qwen2.5vl:7b, three prompt designs (absolute "is it real", a three-observation rubric,
  a pairwise comparison against the scan), tried on the rigid cushions, the baked ones and the real scan: none separated them (all 0, all 2, always the in-scene crop). The VLM text is kept
  as advisory evidence per crop (`critic/furniture_vlm.py`). The positive and negative tests that gate are geometric and use real data.
- The imported scans (living, parents', library sofas, armchairs, desks, the bed) are judged by their own geometry only (`box`), and by
  `render_support.unsupported` for floating. Their upholstery is not re-modelled.
- Not hand-modelled bouclé loops: the loop look is a Voronoi bump at 5 mm. A 12 mm sunk tolerance (render_support REST) applies.

## Round 2 (2026-11-25, same scene)

| item | change | where |
|---|---|---|
| 1 throw | each throw is a cloth sheet (0.65 x 1.3 m, two plies = 8 mm) dropped, once, onto the real host: the imported living sofa scan, or the procedural sofa and its softened cushions. Seated on seat and arm or back, 0 intersections and 0 vertices inside the hosts measured against the product as imported, 3-12 mm clearance | `blender/soft_drape.py` (bake), `knowledge/soft-throw-drapes.json.gz`, `soft_goods.soften_throws` |
| 2 weave scale | one rule for every fabric on visible furniture (not only cushions and throws): the tile that puts the measured weave in the class band. Dining chairs (geometry untouched), vanity chair, lounge sofa: 1.2 mm -> 5.3 mm loops | `soft_goods.soften_materials` |
| 3 upholstered boxes | 6 mm arris on `furn-kb-bed-2/-3` and `furn-library-daybed-0` (the kids-a bunk is untouched) | `soft_goods.ease_edges` |
| 4 case goods | 2 mm eased edge on every case good below it (135 meshes: garment-module joinery authored at 0, cabinets at 1.5 mm, the 3 rugs) | `soft_goods.ease_edges` |

All render-time: scene.json, receipts and exposure records are unchanged (no shared-file regeneration). Findings from the root cause are in
`docs/lessons/SOFT.md`, "Round 2".

Realism check on the merged scene (`--soft`): 153 flagged objects after round 1 -> **7 after round 2**; the 7 are imported desk scans
(85-89 % of face area axis-aligned: the product's own geometry, not ours; fix is a better asset or an import-time bevel).
Soft goods 0 (shape, scale, float, penetrate), upholstery 0 (scale 8 -> 0, box 3 -> 0), case goods 142 -> 7 (the scans).

## Tests (fresh clone of origin/lane/SOFT, `/home/omar/archpipe/scratch/soft-fresh`)

| group | result |
|---|---|
| luminaires, compliance, design, model, electrical, lightcalc, critic, ops | 596 passed, 3 skipped, 1 xfailed (`SOFT-suite-a1x-1`) |
| lightverify | see hand-back (`SOFT-suite-a1y-1`) |
| documents, drawings2d, pipeline, exchange, approvals, test_villa_lighting, test_exposure_groups, test_mounting*, test_d1_* | 242 passed (`SOFT-suite-a2-1`) |
| tests/interior, tests/test_villa_render*.py | 148 passed (`SOFT-suite-b-2`) |
| `tests/critic` (own) | 84 passed (new: 9 in test_soft_goods, 21 in test_furniture_realism) |
| `run_d1` | exit 0; gates 79 rows: 73 pass, 0 fail, 0 warn, 6 not evaluated |
| `scripts/verify.py` | ALL PASS (207 PASS, 5 SKIP) |

## Shared-file rule (integ/aplus merged last, 2026-11-25)

- Merged `origin/integ/aplus` (DF slim-headboard commits) clean; the production scene rebuilt with receipts and exposure records active,
  no bypass (`SOFT-rebuild-2`, exit 0). SOFT changes no scene file, so the receipts are unchanged baseline-relative (nothing to regenerate).
- Exposure re-measured with a new id (`SOFT-measure-exposure-6`, prod and render-set scenes, 48 views each): **0 membership flips**,
  largest lamp-fraction change 0.0009 (prod) and 0.0005 (set). The committed records stay: they still pass the build and `test_exposure_groups`.
- A finding worth keeping: `villa_scene` mutated `scene_data` (softening) before `--measure-exposure-groups` recorded the transport digest, so a record
  measured that way failed the authored scene's digest ("Stale dominant-light rule or transport measurement", `SOFT-rebuild-1`). Guard: softening is
  skipped in the measuring modes, and `tests/critic/test_soft_goods.py::RenderWiring` pins it.
- Renders: `SOFT-final-after-2/3` (after) and `SOFT-final-before-5` (before, `--no-soft`), 96 samples, 1600x1067, six views.
