# C3 phase 2c — physical parts and final admission

Branch start: `acee29d` on `codex/c3p2c`, from the C5 phase 2 branch. C3 is
the lesson class “proxy lacks physical geometry”; C5 is the lighting fixture
package. D1 is the authored villa capability example. Neither this delivery
nor its previews approve a real villa design gate. No commit or presentation
render is made in this package.

## Evidence scope and counts

Chunk B recorded 163 failures on its earlier scene. The retained branch-start
collection has **169 emission failures with the default view set**, or **178
with no views**. Opening doors for particular views splits and renumbers the
shell material buckets: the nine-record difference is entirely `door-leaf`.
These are later branch-start measurements, not a claim that the historical
163-record scene was reproduced. Both actual collections, their reasons and
their geometry are frozen by value in
`tests/fixtures/c3-phase2c-before.json.gz`. The earlier run's full final scene
is `out/c3-phase2c-before-scene.json`; signatures of every one of its 1,110
parts and its appearance inputs are frozen in
`tests/fixtures/c3-phase2c-baseline-audit.json.gz`.

The intermediate `default-early` collection of 147 was a partial-fix
diagnostic. It is not the baseline or final proof. The final exported
collection must contain **zero failures**, with exceptions disclosed below.

## Groups and construction controls

Counts are failing emitted records, not polygons. The two baseline columns
show the default-view and camera-free collections respectively. The new
physical kinds describe components; `assembly_kind` separately preserves
the assembly's support use. The local axes `x`, `y`, and `z` are the model's
across, front and upward coordinate axes required by the existing Part
contract. Bounds are the smallest and largest coordinate on each axis.

| Original kind / builder group | Default | No views | Control at construction/export boundary |
|---|---:|---:|---|
| `finish-layer`, shell/cove/stacked edge | 69 | 69 | Close each oriented skin into its host side after finish-zone clipping |
| `door-leaf`, shell material buckets | 11 | 20 | Same closure; retain original front polygons and openings |
| `desk`, detailed furniture | 7 | 7 | Retain `cable-tray` as physical `joinery-cable-tray` |
| `wc`, detailed furniture | 3 | 3 | Retain `flush-plate` as `wall-plate` |
| `shower_walkin`, furniture | 3 | 3 | Two wet finishes are `finish-layer`; the closed screen is `glass-pane` |
| `tv_unit`, furniture | 2 | 2 | Separate screen intent: `tv-panel` |
| `screen`, furniture | 1 | 1 | `tv-panel`; retain wall-mounted assembly intent |
| `base_run`, detailed furniture | 1 | 1 | Retain oven glass as `appliance-front` |
| `joinery_end_panel`, fallback furniture | 1 | 1 | Only this assembly's `block` component becomes `wall-panel` |
| `sliding-door-pocketed`, storage furniture | 1 | 1 | Physical `door-leaf` |
| `small-boxes-back`, storage board | 1 | 1 | Physical `cabinet-carcass` |
| `small-boxes-shelf`, storage board | 1 | 1 | Physical `shelf` |
| `luggage-back`, storage board | 1 | 1 | Physical `cabinet-carcass` |
| `luggage-base`, storage board | 1 | 1 | Physical `cabinet-carcass` |
| `seasonal-boxes-back`, storage board | 1 | 1 | Physical `cabinet-carcass` |
| `seasonal-boxes-base`, storage board | 1 | 1 | Physical `cabinet-carcass` |
| `bikes-back`, storage board | 1 | 1 | Physical `cabinet-carcass` |
| `bikes-base`, storage board | 1 | 1 | Physical `cabinet-carcass` |
| `bikes-hooks`, storage fixing plate | 1 | 1 | Physical `wall-plate` |
| `rug`, furnishing | 4 | 4 | Admit existing closed rectangular textile backing with a physical reason |
| `appliance-component`, coffee/downdraft | 5 | 5 | Two trays, two authored square spouts and one vent casing get distinct physical kinds |
| `appliance-housing`, hood | 1 | 1 | Admit authored rectangular canopy enclosure |
| `duct`, hood | 1 | 1 | Admit authored rectangular external casing |
| `shutter-housing`, door detail | 1 | 1 | Admit authored rectangular housing |
| `door-track`, door detail | 1 | 1 | Admit authored rectangular extrusion |
| `curtain-track`, curtain detail | 10 | 10 | Admit authored rectangular extrusion |
| `lamp-housing`, pendant/battens | 4 | 4 | Admit rectangular manufactured housings |
| `light-diffuser`, vanity fixtures | 4 | 4 | Two obsolete side bars already retired by C5; two remaining closed substrates admitted |
| `wall-marker`, lighting | 6 | 6 | Correct emitter winding; retain explicit single-face aperture exemption |
| `vacuum-body`, storage dressing | 1 | 1 | Shape-bound exemption; morphology remains unresolved |
| `vacuum-wand`, storage dressing | 1 | 1 | Shape-bound exemption; circular section would change appearance |
| `luggage`, shelf dressing | 8 | 8 | Shape-bound exemptions for existing shoe/hat envelopes |
| `folded-fabric`, wardrobe dressing | 4 | 4 | Shape-bound exemption; folds would change silhouette |
| `folded-linens`, storage dressing | 1 | 1 | Shape-bound exemption; folds would change silhouette |
| `pillow`, bunk dressing | 1 | 1 | Shape-bound exemption pending the parallel bed package |
| `lamp-cord`, lighting suspension | 6 | 6 | Shape-bound exemption; square-to-round section changes appearance |
| `lamp-wire`, lighting suspension | 2 | 2 | Shape-bound exemption; square-to-round section changes appearance |
| **Total** | **169** | **178** | Final admission checks the actual completed export |

`construction_solids.backed_polygon` adds an **assumed render backing of
0.001 metres**, not a specified construction build-up. It retains the exact
front polygon, constructs its reversed back and closes only true boundary
edges. Reverse edge pairs used as bridges around openings do not become
walls. The complete polygon's oriented area chooses the host-side direction,
including concave ramp profiles. Already closed solids remain untouched.
All shell finish surfaces become solids; diagnostic host datums remain in
the separate non-render channel.

Closure also carries each original front's runtime material binding with its
skin. Added floor backing/edge faces use the existing `stone-substrate`
finish, keeping ground-only textures off undersides. A malformed source
array is refused before geometry changes; final physical admission rejects
an array whose length differs from the face count.

`component_kinds` uses authored component names and assembly roles, never
identifiers or room names. Board shortcuts apply only to joinery assemblies;
a padded chair back or sofa base retains its assembly kind. Unknown blocks
retain the normal proxy rejection. Rectangular admissions in `physical_part`
each include a physical reason and still require closed outward geometry.

## Explicit exceptions

The 24 retained closed proxy records are listed in
`knowledge/c3-part-exemptions.json`: vacuum body 1, vacuum wand 1, luggage 8,
folded fabric 4, folded linens 1, pillow 1, lamp cords 6 and lamp wires 2.
Their reasons are retained above and in the manifest. They are not a claim
that these objects have correct physical morphology. Replacing them would
change the authored silhouette/content or overlap Codex-B's bed ownership.
Each exemption is bound to a frozen shape digest after translation removal.
Offsets are rounded to a millionth of a metre for the fingerprint, avoiding
floating-point subtraction noise; the stored failure fixtures retain their
original values. Solid geometry and winding are checked independently.
Renaming and translation preserve admission; resizing, opening the shape or
changing its winding fails. No new general box kind was added for these
objects. An exemption never skips geometry validation.

Registered surface exemptions in `physical_part.SURFACE_EXEMPTIONS` are:

- `finish-layer`: ground-cover interface over unbounded terrain; inventing a
  subterranean construction volume is outside this model.
- `soil-bed`: in-ground soil interface, without an authored excavation.
- `tree-pit`: gravel/soil interface, without authored roots or excavation.
- `glass-edge`: optical treatment over an independently closed pane;
  standalone glazing cannot use this exception.
- `light-diffuser`: a single emitting aperture over a physical housing;
  emitting back faces would change the declared luminous flux.
- `wall-marker`: a single emitting aperture on a wall host; the recessed
  product housing/installation remains an explicit construction requirement.

Every surface still requires non-degenerate faces and an occupied-side
direction that agrees with its normal. Unknown surface kinds fail. These
exceptions concern existing terrain or optical interfaces, not cloth: no
new cloth exemption or bed/cloth implementation is included here.

## Checkpoints, measurements and previews

Checkpoint 1 resumed the retained diagnosis: material/room bucketing split
shells, furniture batching erased component names, and later mutation passes
could replace the typed list. Collection at initial emission could therefore
neither close construction interfaces nor certify the final scene.

The first resumed full build exposed a support regression in the partial
edits: retyping a kitchen worktop excluded it from the assembly selector,
which proposed placing the coffee machine on a fascia 0.040 metres lower.
The existing frozen approval guard rejected the changed schedule. Evidence
is frozen in `tests/fixtures/c3-phase2c-support-drift.json.gz`. All three
assembly-based support selections now use `assembly_kind`; approved
coordinates and host-selection limits are retained. A translated, renamed
real source reproduces the old wrong choice and proves the corrected one.

Checkpoint 2: the strict scene reaches zero part failures; real frozen shell
faces close with their fronts retained, bridge openings remain open, and
bounded exceptions reject open and resized siblings. Unknown component
roles still fail admission. The remaining detailed-desk cable trays and
fallback end panel were diagnosed from the actual emitted component names,
then typed at their builder rather than allowing generic desk/block proxies.

The first portable verification of that closure caught one mixed-material
sibling: `shell-042-paving` expanded from 63 faces to 339 while retaining
63 material entries. The real before/failure values are frozen in
`tests/fixtures/c3-phase2c-face-materials.json.gz`. The corrected closure
propagates the bindings; the independent ground-face review stays quiet on
the corrected real case and a translated, renamed ground-only finish. The
measurement audit now compares every original front's actual runtime
material as well as the object-level material.

The focused mounting test then found an incorrectly wound stacked slab
bridge. Its fixed vertex order pointed away from the host, so closure added
backing toward the room. `stacked_finish_bridge` now orients against the
measured upper host normal before closure. The original front vertex set
stays exact. Actual rejected geometry is frozen in
`tests/fixtures/c3-phase2c-bridge-winding.json.gz`; the proof covers renamed
and opposite-facing hosts. The real mounting regression now
checks the unchanged front datum and the complete host-side backing interval
rather than requiring a physical solid to remain coplanar.

A cache-path proof also caught omitted policy provenance: revoking the real
vacuum exemption rejected fresh admission but still allowed its cached
scene. Including `knowledge/c3-part-exemptions.json` in scene provenance
prevents that escape; the real revocation now refuses cached consumption.
These findings and the historical downstream-test injection adjustments
are recorded in `docs/LEARNINGS.md` with their causes and proving tests.

The wider focused run also exposed two historical assertions. Its family
floor expected an open face; the proof now requires the exact declared
closure of the frozen front and physical re-admission, while every other
family object remains exact. Its suppressed-finish reproduction expected
51 failures from C4 (the mounting package), although current C5 geometry
retires three side-fitting failures and introduces four over-mirror
body/aperture failures. The actual current total is 52 records across 36 identifiers. All current findings,
the added geometry and explicit retired/new inventories are frozen in
`tests/fixtures/c3-phase2c-suppressed-extra.json.gz`. The original 35-identifier inventory from that 51-record
checkpoint is retained (separate unsupported islands can share one identifier);
the test compares the complete current findings by
value, then demands quiet surface and support checks after finish building.
No count tolerance or production placement was changed.

Measurement command (the interpreter and `PYTHONPATH` are those supplied by
the lead):

```bash
python scripts/c3_phase2c_evidence.py --rebuild
```

It builds a fresh strict scene with no views, re-admits the saved final
values, checks the frozen branch-start signatures and writes
`out/c3-phase2c-measurements.json`. The file contains per-part before/after
bounds and face counts, full scene inventory differences, unchanged
appearance-input proofs, exceptions, preview paths and scene content hashes.
The neutral comparisons use actual geometry, shared framing and neutral
grey faces with no design emissive shaders. They are engineering previews,
not presentation renders or independent optical acceptance. Red arrows
mark the wall-marker and host-bridge face normals. Lead optical review
remains separate.

Fresh measurement execution and independent re-admission exited 0. The final
scene has **1,110 parts and zero collected failures**. Geometry changes are:

| Final kind | Changed records | Faces before | Faces after | Largest bound change |
|---|---:|---:|---:|---:|
| `finish-layer` | 119 | 954 | 5,737 | 0.001 metres |
| `door-leaf` | 20 | 72 | 432 | 0.001 metres |
| `wall-marker` | 6 | 6 | 6 | 0 metres |
| **Total changed** | **145** | **1,032** | **6,175** | **0.001 metres** |

Whole-scene face counts are 1,702,812 before and 1,707,955 after. Another
65 records change kind without changing geometry. All original front
polygons **and their runtime material assignments** are retained. There are
no added or removed render meshes. Lights, imported models, props, cloth,
curtains, exposure, sky, complete material definitions and view inputs have
identical content signatures. The backing measurement's floating-point
maximum is 0.0010000000000012221 metres; no tolerance was widened to hide
a design change.

The remaining surface exception counts are: terrain finish 6, in-ground soil
9, tree pit 1, glass-edge treatment 5, wall-marker apertures 6 and diffuser
apertures 4. The 24 closed proxy exceptions are additional to these surfaces.

Neutral engineering previews were visually inspected on 2026-10-09. The
shell and cove openings retain their voids; doors, floors and shell extents
stay in place. The wall-marker comparison shows the corrected occupied-side
normal at unchanged coordinates. The host-bridge comparison shows its
corrected host-side orientation without moving the front. The initial depth-sorted diagnostic glyph
was obscured, so the reviewed plot draws the glyph clearly and states its
direction in words. Review receipt and image content hashes:
`out/c3-phase2c-preview-review.json`. This is a geometry review, with no
photometric or client design approval implied.

- `out/c3-phase2c-previews/shell-opening.png` — opening bridges and compound shell bucket.
- `out/c3-phase2c-previews/shell.png` — plain shell skin closure.
- `out/c3-phase2c-previews/door.png` — door bucket closure.
- `out/c3-phase2c-previews/host-bridge.png` — host-facing bridge orientation and closure.
- `out/c3-phase2c-previews/floor.png` — finish backing below the existing datum.
- `out/c3-phase2c-previews/cove.png` — band and vertical fascia closure.
- `out/c3-phase2c-previews/marker.png` — winding-only visible direction correction.

Acceptance runs use `NO_COLOR=1`, `PYTHONPATH=src` and
`/home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python`. Results are judged
by process exit status:

- `scripts/verify.py --portable`: **exit 0, ALL PASS**;
  `out/c3-phase2c-verify-portable.log`, with execution/context/result records
  copied to `out/c3-phase2c-normal-verify-*.json`.
- The same portable command with a new initially empty temporary `HOME`:
  **exit 0, ALL PASS**; `out/c3-phase2c-verify-empty-home.log`, records copied
  to `out/c3-phase2c-empty-home-verify-*.json`.
- Focused acceptance: **129 tests, all three batch processes exit 0**:
  part/C3/render-standard 82, mounting-scene 27, finish/support/adapters/
  provenance 20. Logs: `out/c3-phase2c-parts-render-final.log`,
  `out/c3-phase2c-mounting-final.log`,
  `out/c3-phase2c-finish-support-final.log`. Each batch has a corresponding
  absolute-path `*-final-result.json` execution receipt.
  Modules: `tests.test_c3_phase2c`, `tests.test_physical_part`,
  `tests.test_render_standard`, `tests.test_mounting_scene`,
  `tests.test_mounting_finish_layers`, `tests.test_support_mounting`,
  `tests.test_agent_assets`, `tests.test_villa_scene_provenance`.
  Run through `scripts/run_tests.py` with verbose unittest output retained
  in the separate final `out/c3-phase2c-*-final.log` files. The earlier
  combined 129-test run exited 1 on the two historical assertions described
  above; retained as `out/c3-phase2c-focused-before-final-harness.log`.
  Subsequent batches passed the 82 required part/render tests and 27 mounting
  tests but exited 1 when a scratch receipt callback used a relative path;
  their `*-receipt-failure.log` files remain rejected acceptance evidence.
  That run also exposed the erroneous inference of 51 unique identifiers:
  the retained historical inventory has 35. Final receipt paths are resolved
  and checked before running, and the migration uses actual finding values.
- `scripts/sync_agent_assets.py`: **exit 0**, generated 38 adapters after
  the canonical skill edit. `git diff --check`: **exit 0**.

Final acceptance receipt: `out/c3-phase2c-acceptance.json`. It joins all
five exit-zero execution records, the zero-failure scene and the reviewed
seven-preview receipt. The preview hashes and saved scene content hash were
checked again after acceptance; all match.

Earlier meaningful nonzero runs exposed support schedule drift,
material-cardinality drift, bridge direction and omitted cache policy, as
recorded above. Historical downstream tests also required plain-list
injection harnesses to reach their intended guards. Intermediate
runs interrupted while narrowing the component migration are not passing
evidence. The lead retains responsibility for the full suite and commit.

## Refactor audit against branch start

- No authoring input, layout position, camera, material selection, product
  asset, bed/cloth code, library manifest or shared data is changed here.
- Replace the initial `collect_part_failures=True` default with strict final
  admission. The internal working list remains diagnostic because mounting
  and finish-zone clipping operate on interfaces. The final unconditional
  admission checks the completed faces and returns a strict `PartMeshList`.
- Replace discarded component names with preserved `physical_components`
  and separate assembly intent. Replace assembly-support reads of
  `part_kind` with `assembly_kind`. No mounting route, threshold or approved
  movement is removed or loosened.
- Replace generic coffee/downdraft kind declarations with exact physical
  component kinds. Their geometry stays identical.
- Replace the wall-marker reverse-winding condition to face the declared
  occupied side. Its bounds, material, flux and mounting coordinates stay
  identical; the visible direction change has a neutral preview.
- Orient the stacked bridge by its measured host direction. No front vertex
  is moved; backing now occupies the intended host side. Add the exemption
  policy to source provenance so cached consumers cannot retain revoked
  permission.
- Preserve historical open-datum injections as plain lists only inside
  downstream mounting tests, following the existing render-standard harness.
  Update the completed bridge assertion to test a front plus host-side
  backing. No production admission or downstream finding is waived.
- Replace the family floor's open-face equality with the exact declared
  construction transformation of its frozen front. Reconcile the historical
  suppressed-finish fixture through the measured C5 retirement/addition;
  retain the old inventory and compare the entire new failure list by value.
- Remove `surface`, `occupied_side` and the stale surface reason only when
  construction completion has made a shell record solid. This strengthens
  the part contract instead of waiving a malformed bucket.
- Replace historical emission failure metadata with actual final admission
  findings. The original values remain in frozen regression fixtures.
- The historical `lamp-VSCONCE-parents-ensuite-04` and `-05` disappear in the
  pre-existing C5 vanity replacement on the branch start. Phase 2c adds no
  deletion remedy. The full camera-free final inventory audit proves that
  the phase 2c geometry has no added or removed render mesh records.
- `guard_registry.py` and its tests remain with agy. Registry handoff is the
  explicit list below; no registration is claimed by this package.

## Lessons to register

1. Extend `c3-proxy-physical-geometry`: construction completion in
   `construction_solids`, component typing in `component_kinds`, strict
   final `villa_render.build` admission, `PartMeshList`, bounded exemptions
   and the two `verify.py` checks. Proofs: all tests in
   `tests.test_c3_phase2c`, retained `tests.test_physical_part` and the
   before/after evidence script. Stage: completed scene export before any
   render consumption. Remaining morphology exceptions stay open.
2. Add `c3-component-type-erased-support-intent`: separate assembly support
   intent from physical component kind and use it consistently at all three
   support selectors. Proof:
   `FrozenPhysicalGroups.test_real_retyped_worktop_preserves_approved_support_and_renamed_sibling`
   plus the real scene support regressions. Stage: support construction.
3. Preserve the process rule: migration inventories must freeze actual
   values at both emission and final export, record view-dependent counts,
   compare all final geometry/appearance inputs, and disclose exceptions.
   A historical checkpoint count or an initial admission pass cannot
   certify a later mutated scene.
4. Add `c3-closure-stale-face-materials` under the C3 control: topology
   construction must carry face attributes, reject malformed sources before
   mutation, and fail closed on face/material cardinality mismatch. Proof:
   `FrozenPhysicalGroups.test_real_material_slots_follow_closure_and_ground_siblings`.
   Stage: topology construction and final physical admission. Extend the
   migration audit to runtime front bindings; whole-object material equality
   is insufficient.
5. Add `c3-stacked-bridge-host-side`: construct bridge orientation from the
   host before closure; a closed outward solid alone cannot prove correct
   host occupancy. Proof:
   `FrozenPhysicalGroups.test_real_stacked_bridge_front_follows_host_before_closure`
   and the real mounting regression. Stage: finish construction before closure.
6. Add `c3-exemption-cache-provenance`: admission policy is a scene dependency;
   a cached renderer must refuse after revocation. Proof:
   `VillaSceneProvenance.test_real_c3_exemption_revocation_invalidates_cached_scene`.
   Stage: cache provenance before scene consumption.
