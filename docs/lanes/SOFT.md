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

Before the fix 188 findings on 173 objects, after 153 on 153 (the soft goods all pass):

| | before | after |
|---|---|---|
| soft goods: sunk into the sofa (`penetrate`, 50-66 mm) | 8 | 0 |
| soft goods: flat crown (`soft-shape`; cushions 31-35 deg against a floor of 45, throws 0 against 25) | 19 | 0 |
| soft goods: wrong weave scale (`scale`) | 3 | 0 |
| upholstery: wrong weave scale | 10 | 8 |
| upholstery: pure box, no bevel | 3 | 3 |
| case goods: pure box, no edge radius | 142 (incl. 7 imported desk scans at 85-89 %) | 142 |
| case goods: wrong weave scale (rugs) | 3 | 0 (a carpet is meant to be coarse) |

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

## Throws (open)

The throw is the weakest soft good. It is a baked cloth drop (knit finish, rounded by a Laplacian pass), but it is shaped over a rolled
lump, not over the sofa. On the scanned living sofa its proxy is not the scan, so the throw reads as a stiff folded plate
cantilevered off the arm (as before the fix). A render-time cloth drop onto the host's real render geometry (`drape_cloth`'s
approach) was tried: the solver let the sheet fall through the sofa (min z 7-12 m below the floor) and I could not isolate why in the time
available, so it was removed. Next step: debug that sim in a small scene, then drape every `dress-throw-*` onto the imported model objects.

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
