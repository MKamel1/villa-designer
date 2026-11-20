# TRELLIS.2 trial — isolated evaluation

**Status: evaluation complete; admit none of these three outputs.** Started 2026-10-21,
completed 2026-10-22. Nothing entered the villa. TRELLIS runs within this
24 GiB card at the tested 512 resolution; visual/design fidelity is the
limitation in this sample. The stool is the most promising generic appearance;
the pendant is smoother but the wrong shape; the plant is incomplete.

Work is uncommitted on `codex/trellis`, based on `e24189c` (`integ-10`). Generated appearances
must carry **“generated from photos - ASSUMED”**. PBR means physically based
rendering; inferred colour, roughness, metalness and opacity are appearance
estimates, not measured physical properties. GPU means graphics processing
unit. MiB is 1,048,576 bytes; GiB is 1,073,741,824 bytes.
Widths and depths below follow the isolated model's horizontal x and y axes;
height follows its upward z axis. Millimetres are abbreviated mm; metres, m.

## Installation and provenance

- Installation: `/home/omar/archpipe/tools/trellis2`; its own Python 3.12.3
  virtual environment. Project Python and Blender have not been modified.
- Official [code](https://github.com/microsoft/TRELLIS.2) revision:
  `75fbf0183001ed9876c8dbb35de6b68552ee08bd`.
- Official [model](https://huggingface.co/microsoft/TRELLIS.2-4B) revision:
  `af44b45f2e35a493886929c6d786e563ec68364d`.
- Auxiliary `microsoft/TRELLIS-image-large` structure decoder revision:
  `25e0d31ffbebe4b5a97464dd851910efc3002d96`; its download is also pinned.
- TRELLIS code and model: MIT, per the code licence and pinned model card.
  The model repository does not contain a separate `LICENSE` file (HTTP 404).
  The full code licence and model-card declaration are retained in
  `out/trellis/setup/`, together with checkpoint hashes and download receipts.
- Hardware read-back: NVIDIA RTX 3090, 24,576 MiB, driver 595.99.02. Initially
  idle at 15 MiB; no walkthrough renderer was active. All GPU work holds
  `/home/omar/archpipe/locks/graphics.lock` for one object or preview package.
- PyTorch 2.6.0 and torchvision 0.21.0 are isolated from the project.
  Host CUDA compiler 12.0 cannot compile the current CuMesh dependency.
  NVIDIA's official CUDA 12.4.1 redistribution is installed under the tool
  directory, with archive checksums, component versions and licence files.

The stock pipeline also references an access-gated Meta DINOv3 image encoder
and BRIA RMBG-2.0 background remover with separate terms. The trial uses the
public [timm DINOv3 distribution](https://huggingface.co/timm/vit_large_patch16_dinov3.lvd1689m),
revision `30c1109559f65dea34316b0d4842d35c5771fe11`, under the retained DINOv3
licence, and [MIT BiRefNet](https://huggingface.co/ZhengPeng7/BiRefNet), revision
`e2bf8e4460fc8fa32bba5ea4d94b3233d367b0e4`. No gated weights are downloaded.
The adapter strictly maps the public timm tensors into the Transformers
loader and compares its raw-token features against native timm on the CPU
(central processing unit). Both implementations use floating-point positional
periods; equivalence to the original gated encoder is not asserted.
This is a declared loader/preprocessing variant, not an untouched
stock-pipeline benchmark. TRELLIS's trained generation weights are unchanged.

Exact installed versions are in
[`final-runtime.json`](../out/trellis/setup/final-runtime.json), including
Python 3.12.3, PyTorch 2.6.0, torchvision 0.21.0, xformers 0.0.29.post3,
Transformers 4.57.6, timm 1.0.30 and einops 0.8.2. Native-extension source
commits are in [`source-revisions.json`](../out/trellis/setup/source-revisions.json).
The independent 512 × 512 encoder comparison passed: maximum absolute feature
difference 0.0000209808, mean 0.00000063737, with strict tensor loading
([receipt](../out/trellis/setup/encoder-conversion.json)). This checks the
public-checkpoint conversion, not equivalence to gated original weights.

Measured allocated disk use is approximately **20.90 GiB** for the isolated
installation: environment 6.03 GiB, model files 11.80 GiB, caches 1.40 GiB,
CUDA toolkit 0.55 GiB and downloaded archives 0.45 GiB. Exact byte counts and
measurement scope are in [`disk-use.json`](../out/trellis/setup/disk-use.json).
The tool directory is retained for reproduction.

## Licensed inputs and authored size

Complete original-file URLs, author credits, licences and input hashes:
[`out/trellis/inputs/manifest.json`](../out/trellis/inputs/manifest.json).
Downloaded candidates were visually inspected before selection. Rejected
candidates and search metadata remain in the same evidence directory.

| Object | Selected photograph and credit | Licence | Uniform size datum |
|---|---|---|---|
| Opal pendant | [Glo-ball designed by Jasper Morrison](https://commons.wikimedia.org/wiki/File:Glo-ball_designed_by_Jasper_Morrison.jpg), JT at JMLtd | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | Largest horizontal extent 0.300 m, authored villa globe diameter |
| Mona Lavender | [Starr 080117-1490 Plectranthus sp.](https://commons.wikimedia.org/wiki/File:Starr_080117-1490_Plectranthus_sp..jpg), Forest & Kim Starr | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) | Overall height 0.400 m, authored south-bowl specimen height |
| Simple stool | [Wooden stool](https://commons.wikimedia.org/wiki/File:Wooden_stool.jpg), Sashatrk | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | Overall height 0.450 m, user-authored trial dimension |

The pendant photograph shows a flattened opal Glo-ball, not the specified
sphere. The stool is a four-leg wooden stool, not an IKEA MARIUS product
photograph or a claim of product identity. Its height is an authored trial
assumption. The selected plant is `Plectranthus 'Mona Lavender'`, listed in
[`knowledge/garden-palette.json`](../knowledge/garden-palette.json); the
0.400 m datum is the authored young-clump appearance, not its mature height.
Background removal and inferred rear/underside geometry are adaptations.
Conservatively retain each source photograph's attribution and share-alike
terms with its generated asset and preview; the model's MIT licence does not
replace the photographs' licences.

The plant's Commons filename says `Plectranthus sp.`, but its retained
description explicitly says “Mona lavender hybrid flowering habit”; it is a
crowded nursery photograph with cropped sprays, not an isolated whole plant.
That limitation materially affected segmentation and the result below.
The optional `agy/cands8` branch was absent in the available bare repository;
no kids-bed/vanity-stool claim is made. Each object directory contains
`LICENSE-AND-CREDITS.md` with the source, author, licence and changes notice.
CC BY means Creative Commons Attribution; CC BY-SA adds ShareAlike.

## Comparison method

The actual existing procedural objects were extracted read-only from the
walkthrough's prepared scene, whose SHA-256 content digest is
`5b59dfa1298bac93da87499cf1178a2bf93486446d77ab618464487a014cb1c1`.
The full scene remains untouched. Exact selected faces, materials and source
identifiers are retained in `out/trellis/baselines.json`:

| Baseline | Measured width × depth × height | Scope |
|---|---|---|
| `lamp-PEN-GLOBE-kitchen-01` | 0.300 × 0.300 × 0.300 m | Diffuser only, 160 source faces; cord, canopy and inner bulb excluded |
| `landscape-g6-centrepiece-mona-0` | 0.254488 × 0.350 × 0.400 m | Actual procedural south-bowl plant |
| `furn-k-island-stool-1-0` and `-1` | 0.370 × 0.370 × 0.650 m | Current complete island stool; its 650 mm height is preserved |

TRELLIS runs the 512-resolution pipeline, seed 42, upstream low-memory mode,
then exports a textured binary glTF file (GLB). Export requests 200,000
triangles and 2,048-pixel textures, with upstream remeshing enabled. Actual
mesh counts and map dimensions must be measured after export; these settings
are requests, not achieved measurements. Raw generated vertices and triangles
are preserved before export simplification/remeshing.

`scripts/trellis_preview.py` runs Blender 4.5.14 and reuses the project's mesh
builder, scene reset, neutral softbox sizing, clipping and whole-object
framing checks. Each baseline/generated pair has identical camera, neutral
lighting, exposure, image size and samples. Original materials remain, with
emission disabled for this unlit diagnostic. Only one uniform scale applies
to the complete generated hierarchy; baselines receive a rigid isolation
translation. The current 650 mm stool is compared honestly with the 450 mm
trial stool. These are isolated diagnostic previews, not context admission
or presentation-lighting validation.

Closure is reported both for original indexing and after measurement-only
coordinate welding at eight decimal places, because texture seams can split
an otherwise closed surface. An edge-incidence closure pass does not prove
absence of self-intersections, physical construction or support capacity.

## Results and recommendation

**Keep TRELLIS as an experimental appearance source; do not use these outputs
in the villa.** It runs on this workstation, but this trial does not establish
hyper-realistic, design-faithful objects. Use a clean licensed whole-object
photograph and inspect its segmented foreground before any future run. A
procedurally smooth sphere is a more direct next correction for the globe;
the flowering plant needs complete foliage and rooted architecture. These
recommendations do not author those changes.

The [side-by-side preview gallery](../out/trellis/index.html) displays unchanged
full-size images, licensed inputs, segmentation and reverse views. The
[combined numerical receipt](../out/trellis/results.json) binds generation,
export maps, previews and source identities. The independent critic inspected
all three photographs, masks and nine 960 × 720 previews; its rejected
dispositions are retained in [`review.json`](../out/trellis/review.json).

| Output | Uniform factor, metres per source unit | Measured fitted width × depth × height | Export vertices / triangles | Raw triangles before export | GLB bytes |
|---|---:|---|---:|---:|---:|
| Pendant | 0.3390034433 | 0.299920 × 0.300000 × 0.340359 m | 138,247 / 198,735 | 4,134,876 | 13,232,856 |
| Mona Lavender fragments | 0.5549926887 | 0.556007 × 0.455671 × 0.400000 m | 169,364 / 189,496 | 851,344 | 15,927,216 |
| Stool | 0.4486006311 | 0.324066 × 0.324048 × 0.450000 m | 117,430 / 198,973 | 1,653,250 | 12,002,484 |

GLB means binary glTF, the exported model format. Bounds before scaling,
the complete equal-axis transform and actual fitted lower/upper corners are
in each `preview/measurements.json`; no independent axis stretching was used.
The pendant's overall height includes generated cord/interior, whereas the
baseline contains only the diffuser. Overall height cannot establish
diffuser-shape agreement.

| Output | Generation/export seconds, after lock acquisition | PyTorch peak allocated / reserved MiB | Sampled whole-device peak MiB | Closure after coordinate welding |
|---|---:|---:|---:|---|
| Pendant | 94.57 | 3,188.91 / 3,966 | 4,987 | No: 1 boundary edge, 574 nonmanifold edges, 1 degenerate triangle |
| Plant | 88.63 | 3,188.91 / 3,634 | 3,977 | No: 0 boundary edges, 1,506 nonmanifold edges |
| Stool | 69.52 | 3,188.91 / 3,634 | 3,977 | No: 9 boundary edges, 1 nonmanifold edge |

The whole-device monitor samples every 0.25 seconds and can miss brief peaks;
PyTorch's allocator counters exclude memory allocated directly by other
libraries. All three actually completed on the 24,576 MiB RTX 3090. These
measurements cover the 512 low-memory variant only; higher resolutions were
not tested. Original-index boundary-edge counts are 70,235, 130,092 and 35,011
respectively, partly because texture seams split vertices. The welded counts
above still establish that none is a closed review body. A nonmanifold edge
has more than two incident triangles; closure here also rejects degenerate
triangles and edges with only one incident triangle.

All three exports have two embedded **2,048 × 2,048 PNG maps** (Portable
Network Graphics): base colour
with an alpha channel, and packed roughness/metalness. The latter binds green
to roughness and blue to metalness; red is unused in these exports. Each uses
an opaque material, so stored alpha does not provide effective transparency.
No normal, transmission or displacement map is present. Exact material
bindings, decoded channel ranges and embedded-image hashes are in each
`export-materials.json`. These are not measured optical properties,
especially opal-glass transmission or a luminaire's photometry.

| Object | Better than current procedural appearance? | What the photo did not establish; disposition |
|---|---|---|
| Pendant | Smoother surface, **no as the specified villa sphere**. | Flattened source body; generated open neck, brown/orange ribbed interior, irregular rim and loose wire. Reject this source/result. Correcting the mismatch would require deforming the reconstruction, contrary to this trial's uniform-scaling rule. |
| Mona Lavender | More detailed individual flowers, **no as a complete plant**. | Segmentation already removed green foliage, pot and lower attachment. Output invents backs/joints as bulbous purple, cream and brown lobes, leaving detached truncated sprays. Reject. This is a preprocessing/input failure as well as an output failure, not a general botanical-capability verdict. |
| Stool | **Yes for generic surface/shape detail; no as the current island stool**. | Worn wood and turned legs read more convincingly, but the generated apron adds a yellow circular fastener/knob and drawer-like recess unsupported by the plain visible aprons. Rear joinery and underside remain inferred. It is 200 mm lower than the actual 650 mm baseline and differs in form and finish; it is not MARIUS. |

The plant's generated width is 2.185 times the baseline and its depth 1.302
times, giving 2.844 times the rectangular bound area at the same authored
height. The critic measured 252 welded connected components; 251 start more
than 1 mm above the neutral floor. The largest begins 138.523 mm above it.
Those diagnostics agree with visible suspended fragments; disconnected vertex
graphs alone do not prove absence of every geometric contact. Framing passed
because every fragment was framed, not because the plant was complete.
The [component receipt](../out/trellis/plant/component-diagnostics.json) and
[CPU reproduction script](../out/trellis/plant/measure-components.py) preserve
the grouping, transform and diagnostic-floor measurement without GPU work.

| Identical-camera front comparison | Current procedural baseline | Generated diagnostic |
|---|---|---|
| Pendant | [Full PNG](../out/trellis/pendant/preview/baseline.png) | [Full PNG](../out/trellis/pendant/preview/generated.png), [reverse](../out/trellis/pendant/preview/generated-reverse.png) |
| Plant | [Full PNG](../out/trellis/plant/preview/baseline.png) | [Full PNG](../out/trellis/plant/preview/generated.png), [reverse](../out/trellis/plant/preview/generated-reverse.png) |
| Stool | [Full PNG](../out/trellis/stool/preview/baseline.png) | [Full PNG](../out/trellis/stool/preview/generated.png), [reverse](../out/trellis/stool/preview/generated-reverse.png) |

## Admission boundary

Any future candidate remains an **imported appearance mesh**, paired with
closed physical stand-ins under
[`src/archpipe/imported_appearance.py`](../src/archpipe/imported_appearance.py).
Admission requires immutable source/buffer/texture hashes, measured local
geometry and axes, uniform-scale/placement evidence, complete contents and
licence credits, reviewed isolated and unchanged-camera room previews, and
fresh support, collision, route, swing and baseline-relative access review.
The policy constructs tight closed stand-ins per measured connected component;
appearance closure alone grants no physical exemption. Plant identity and
hidden morphology need botanical review; a generated shade supplies no
verified light distribution or glass optical properties. Nothing in this
trial changes the villa, product schedule, photometry or approval gates.

An open appearance is permitted by that policy: these closure failures do
not alone prohibit appearance admission. They prevent using the appearance
itself as the closed physical review body. This trial constructs no production
stand-ins or admission record. Rejected identity/completeness still prevents
using these candidates irrespective of later physical stand-ins. No room
render, production `render_qa`, route/access/collision or lighting-performance
claim is made from emission-disabled isolated diagnostics. Future captions
must preserve **“generated from photos - ASSUMED”**.

Per-object prerequisites, in addition to the common policy:

- **Pendant:** obtain a licensed photograph of the specified sphere, review
  the complete shade/neck/cord construction, keep the authored emitter and
  verified photometry, and validate opal appearance separately from these
  inferred opaque maps. The generated shade cannot supply an optical spec.
- **Plant:** use a complete isolated specimen and foreground mask retaining
  leaves, stems and rooted base; review species morphology and actual
  support/attachment, then remeasure the entire clump under one scale.
  Closed stand-ins cannot make detached flowers into a complete plant.
- **Stool:** first establish an intended stool matching the selected design's
  form, finish and seat height. This 450 mm wooden object cannot silently
  replace the 650 mm island stool. Resolve invented apron details and hidden
  construction, measure complete seat/foot geometry, then perform the common
  physical and room reviews. A plausible rear render is not product evidence.

## Reproduction and validation

Commands and exact package/component versions are retained under
`out/trellis/setup/`. Entry points are `scripts/bootstrap_trellis2.sh`,
`scripts/trellis_trial.py` and `scripts/trellis_preview.py`. The bootstrap
preserves a small isolated FlexGEMM setup patch so its cache stays under the
tool directory rather than writing a hardcoded home cache.

From this worktree, with the retained isolated installation, a fresh attempt
can be generated and compared as follows (choose unused attempt/output names;
existing attempts are deliberately never overwritten):

```bash
PYTHONPATH=src /home/omar/archpipe/tools/trellis2/venv/bin/python \
  scripts/trellis_trial.py generate --object stool --attempt 512-new1
/home/omar/opt/blender-4.5.14-linux-x64/blender -b -t 8 --factory-startup \
  --python scripts/trellis_preview.py -- --object stool \
  --model out/trellis/stool/512-new1/model.glb \
  --out out/trellis/stool/preview-new1
```

Replace `stool` consistently with `plant` or `pendant` for the other objects.
Both commands hold the shared graphics lock internally, per package; they
wait for laneA. During this resumed run laneA started a walkthrough package,
and both trial packages waited rather than overlapping it. Sandboxed GPU
access failed, but a host check succeeded; that was not a driver failure or
an out-of-memory result. The stopped plant attempt left an empty directory;
the resumed run preserved it and used `512-resume1`.

Completed inference directories are `pendant/512-retry1`,
`plant/512-resume1` and `stool/512-resume1`. The original pendant `512`
failure was a missing model-code dependency, not GPU capacity. Its retained
failure led to the dependency preflight regression. Final provenance review
also pinned the auxiliary structure decoder's actual revision; the original
latest request, a mutable-revision sibling and the clean pinned case were
replayed without network in `setup/auxiliary-pin-reproduction.log`.

Validation uses the requested project Python with `PYTHONPATH=src` and
`NO_COLOR=1`, judged by exit status. Focused trial/safe-output regressions:
**24 tests passed**, exit 0 (`setup/focused-tests-final.log`); existing imported
appearance-policy regressions: **9 passed**, exit 0
(`setup/imported-policy-tests.log`). Blender's native daylight API probe passed
on 4.5.14 (`setup/blender-api.log`); all three actual neutral-preview entry
point runs exited 0 and their hashes/dimensions were read back. Review still
rejected all three as villa substitutions.

After the final pin/registry change:

| Required check | Exit status | Evidence |
|---|---:|---|
| `scripts/verify.py` | **1** | [`verify-native-after-pin.log`](../out/trellis/setup/verify-native-after-pin.log): sole failure is `rfa version reader`, the unavailable installed Windows Revit-family corpus on Linux |
| `scripts/verify.py --portable` | **0** | [`verify-portable-after-pin.log`](../out/trellis/setup/verify-portable-after-pin.log): `RESULT: ALL PASS`; explicitly excludes installed Windows family corpus |

RFA is Revit's family-file format. The native failure remains a failure;
portable success does not establish native Revit integration. Trial paths and
generated model hashes have no matches in production source, specifications
or library selections (exact scan command in `out/trellis/review.json`).
All report links resolve, all nine reviewed PNG hashes match their receipts,
and `git diff --check` passes. Shared `assets/user` and `out/villa/round3`
were not modified. No files under `.agents/` were edited.
No commit is made; the lead owns the full-suite run and commit.
