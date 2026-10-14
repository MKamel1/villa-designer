# Dressing contents verification and neutral review

`archpipe.concept.garments` owns procedural dressing appearances. They are
labelled ASSUMED, not product selections. The authored native wardrobe payload
is unchanged; render export replaces its content envelopes and keeps structural
plinths, backs and dividers. Physical contents remain unchanged. The renderer uses separate hash-bound
cloth appearances; follow [the drape workflow](drape.md). Never feed appearance
faces to physical support, collision, C8 room or occupancy checks.

Build the final scene with `villa_render.build()`, saving the returned scene to
`out/garments/final-scene.json`. The builder runs `contents_findings` after all
historical mounting migrations and rejects missing slots, missing supports,
cycles, proxies, garment morphology/profile failures, hanger intrusion or a separated saddle,
stale drops, overlaps and escaped
modules. Never hand-edit that scene. Each new part has a live floor-bearing
joinery root and a separately checked named contact chain. Old bracket approvals
remain historical: their exact frozen rows are retired only in the new contents
contract, never reused as approval of new geometry.

Before repeating expensive acceptance, run `scripts/garments_evidence.py
--candidate --context` to checkpoint the current contents against the unchanged
saved architectural context and existing cameras. Candidate previews are labelled
pending; a fresh `villa_render.build()` is still required. Then run
`scripts/garments_evidence.py` to derive isolated samples from that fresh scene. `--first-fix` uses the real frozen l0923 input for the small checkpoint.
Run the existing neutral reader `scripts/garden_g6_preview.py` under Blender,
with `--input out/garments/specimens.json --output out/garments/isolated`.
The reader acquires the workstation graphics lock and includes a 1.8 m reference.
Use `scripts/garments_evidence.py --context` to derive `neutral-scene.json`,
then use the same reader with `--scene --input out/garments/neutral-scene.json`
and the existing v31/v32 views. Disable all design emissions and record separate white diagnostic
fill; do not change camera, design geometry, exposure policy or presentation QA.
Inspect every sample and both context images before integration. Front-omitted
drawer samples are expressly diagnostic; production drawer fronts stay closed.

Audit preview warning receipts as well as images. The current shared Blender
reader can falsely reverse small outward meshes when single-precision volume
arithmetic uses world coordinates. The real garment reproductions are in
`tests/fixtures/garment-importer-precision-before.json.gz`; this remains an OPEN
shared-importer issue for the integration lead. Preserve physical placement and
source winding; the correction belongs in local-origin double-precision volume
arithmetic, never in a design translation or source-face reversal. Source C3
admission alone cannot prove the reader preserves winding.

Run `tests.test_garments`, dressing/furnishing tests, `tests.test_render_standard`,
`tests.test_render_views` and `scripts/verify.py --portable` with normal and empty
HOME. Judge each command by its exit status. Keep receipts, image paths and
limitations in `docs/garments-report.md`; ask the integration lead to register
the new guard, since this branch may not edit the registry. C3 means closed,
outward solid admission; C4 means support/mounting; C8 means geometric
relationships. Contact checks do not establish fixing or shelf load capacity.
