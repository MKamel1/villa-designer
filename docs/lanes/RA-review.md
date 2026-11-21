# Lane RA: approval-drift review (2026-11-21)

Base: `origin/integ/aplus` `357ba45`. The mounting guards (`mounting_resume.apply_approvals`,
`final_mounting.validate_rows`, `exterior_mounting.apply_lead_review`) are **unchanged**; no code path was weakened.
Machine record: `knowledge/approvals-review/2026-11-review.json`. Tools: `collect_drift.py` (read-only harness),
`review_tool.py` (`make` decides by rule, `apply` re-approves), `build_evidence_scene.py`.

## How the drift was collected

`collect_drift.py` wraps each approval pass *in memory only*: it records every row whose host or old/new bounds differ
from the frozen file by more than 1e-8 m, then lets that pass see current values so the build continues and exposes the next
pass's drift. The approval files on disk were not touched by it. Passes covered: `c4-bc-approvals`, `c4-d-lead-approvals`
(`apply_approvals`), `c4-e-lead-review`, `c4-final-mounting` (alias-aware, as in production).

**7 rows drifted**, all in `knowledge/c4-e-lead-approvals.json`. `c4-bc` (58 rows), `c4-d` (6) and `c4-final` (2 + retired)
have **no drift** on this base. `lamp-SCONCE-family-bath-04` (c4-bc) does **not** drift here: that drift appears only with the
unmerged lighting lane (see "Not evaluable here").

## Rows (rule R1 cause, R2 physical, R3 intent; all three required)

| Row (host) | Approved 2026-10-05 (new bounds) | Now | Delta | Cause | Decision |
|---|---|---|---|---|---|
| `detail-stair-open-stringer` (support-detail-stair-open-stringer, floor) | x 5.317..9.517, z -3.000..-0.203 | x 5.317..**9.509** | x1 -8 mm | G1 LS2 tread overlap 16 mm (lane D) | **accept** |
| `marker-STEP-stair-b-04` (stair-party-wall) | x 7.227..7.327, y -28.458 | x **7.219..7.319** | -8 mm | same | **accept** |
| `marker-STEP-stair-b-05` | x 8.067..8.167 | x **8.059..8.159** | -8 mm | same | **accept** |
| `marker-STEP-stair-b-06` | x 8.907..9.007 | x **8.899..8.999** | -8 mm | same | **accept** |
| `host-face-support-marker-PATH-corridor-07` | x 5.102..19.604, y -28.458 | x 5.102..**19.804** | x1 +200 mm | lane M wall-corner fix (GF-33 lengthened 0.2 m) | **accept** |
| `...-corridor-08` | same | same | +200 mm | same | **accept** |
| `...-corridor-09` | same | same | +200 mm | same | **accept** |

Rejected: none. Unexplained drift: none (see R1).

### Rules and evidence

* **R1 cause (ablation, not inference).** The harness undoes one approved change in memory and rebuilds: with
  `stairs.NOSING_OVERLAP = 0` the four stair rows vanish and the three corridor rows remain; with
  `revit_spec._close_corner_gaps` disabled the three corridor rows vanish and the four stair rows remain; with both undone
  **0 rows drift** (`evidence/ablate-*.json`). So the seven rows are exactly these two changes, to 1e-8 m. Mechanism: the
  treads run 16 mm under the next nosing, so tread-derived stair parts (tread centres, stringer end) move 8 mm; M closed
  the corner notch at (19.704, -28.671) by lengthening wall GF-33, so its inner finished face, the host of three corridor
  path markers, ends 200 mm later.
* **R2 physical (live scene).** Every mounted item sits on its host's finished face: gap 0.000 mm for the stringer
  (bottom z = floor -3.000), the three markers (y = -28.458 = structural -28.471 + 13 mm plaster) and the three corridor
  markers (x 10.14, 13.64, 17.14, inside the lengthened face x 5.102..19.804; none moved). The coordinate along the host
  normal did not move for any row, the host id is unchanged, and no mount floats or penetrates.
* **R3 intent.** The approved movement vector (new - old) is identical for all seven rows (to 1e-8): same fix, only the
  extent shifted. The stringer's 33.529 mm relocation to the finished floor is unchanged.
* Re-approval: `review_tool.py apply` rewrote the seven rows' `old`/`new`; each keeps `original_2026_10_05` (audit
  trail) and gets `re_review` (date, cause, rules); the file gains `review_notes`. The guard code was not touched.

## Observations (not caused by this drift, not changed)

* `detail-stair-wall-stringer-00..06` (host stair-party-wall) extend y -28.608..-28.396, i.e. 150 mm into the wall behind
  the finished face, as "tread bearing" (label: ASSUMED steel wall stringer and tread bearing; add to Revit). Pre-existing
  and approved; flagged only because a reviewer measuring "no intersection" will see it.

## Defects found (build blockers beyond the approvals; none is in lane RA paths)

* **B1 (FIX1) hanging-swing envelope.** FIX1 moved `landscape-north-mid-02` to (3.00, -24.17) to clear the 3.71 m lounge door
  passage (x 3.27..3.97). The swing at (2.40, -24.77), 1.0 x 1.2 m plus the assumed 0.25 m allowance, spans x 1.65..3.15, so the
  scene guard fails: `hanging swing: [('landscape-north-mid-02', 'swing envelope')]`. FIX1's own candidate check does not
  run this scene-level guard. A position that clears both (door passage and swing envelope) is **(3.42, -24.07)** inside the
  swing back bed (3.18..3.61 x -24.39..-23.92): scene builds past the guard. It is a one-coordinate change in
  `knowledge/garden-palette.json` (FIX1-owned), saved as `knowledge/approvals-review/fix1-swing-overlay.patch` and **not
  committed**; the lead or FIX1 must apply or choose another position. Guard left as is.
* **B2 furniture receipts.** After the mounting stage, `furniture-stage2` raises "furniture fixed-room inputs changed ...
  (changed sections: specification, architecture, meshes)". The frozen receipts `knowledge/furniture-stage2.json.gz` and
  `parents-bed.json.gz` hash the spec, shell architecture and room furniture; G1 (spec keys, stair infill, guards,
  cupboard) and M (wall corners) changed them. Regenerating them needs the baseline-relative room review and previews the
  guard demands; that is a lead decision and was **not** done (not a lane RA path).
* **B3 exposure record stale.** `knowledge/exposure-groups.json` binds `transport_sha256` of the whole scene; any geometry
  change (all of the above) makes `require_record` raise "Stale dominant-light rule or transport measurement". It
  must be re-measured on the GPU (`--measure-exposure-groups`) **after** B1 and B2 settle, on the final production scene.
  Measuring now on an evidence scene would bind the record to a scene production cannot build, so it was not committed.

Consequence: **a production full scene build does not pass on this branch**. The approval stage passes; the build then stops
at B1 -> B2 -> B3, in that order. The evidence scene below was built with B1's overlay and with the two receipt passes
bypassed in the harness (`--bypass-receipts`: no measured desks / replaced parents bed; mounting unaffected).

## Exposure digest

`exposure_groups.transport_digest` now hashes the scene through `element_ids.without_ids`, so the three P2 fields
(`element_ids`, `faces_by_element`, `element_id_basis`) no longer enter the frozen digest. Tests
`tests/approvals/test_transport_digest.py`: same digest with and without ids; geometry, material, mesh-count, north and a
new mesh field each still change it; the scene is not mutated.

## Not evaluable here

`lamp-SCONCE-family-bath-04` (c4-bc, lane LV/L6b): merging `origin/lane/L6b` into a scratch worktree on this base
fails earlier, in `c4-fitting-migrate`: `support-marker-PATH-landing-gf-02: no real host at authored fixing anchor`. So the
sconce row cannot be judged, and was neither approved nor touched; it needs its own review once the lighting lane merges.

## Evidence scene and previews

Built on `lane/RA` + the B1 overlay + `--bypass-receipts` (`build_evidence_scene.py`, production approval guards, 64 approved
rows applied, `lead_approved_count` 64): 1,242 meshes, all carrying the three P2 id fields.

| item | value |
|---|---|
| scene.json (written, ids kept, no exposure record) | 428,226,964 bytes, sha256 `c523d524f45c6759a2d3452471538eb9dc2657612e93b8273bc16842c6210da8` |
| same scene, ids stripped (`json.dumps(without_ids(scene), sort_keys=True)`) | sha256 `13d487054f49872621a832c46e9cf75f1c26b64766c6bbb2c6dc1ba0c9c32d35` |
| render scene (+ freshly measured exposure record) | sha256 `48569b66e66ab93af1cf512c91cd769a746cfc75cc75ce3772e10d7167ac6a05` |

These hashes belong to the evidence scene, **not** to a production build (B1-B3). The new `transport_digest` accepted the
scene with ids against a record measured by Blender on that same scene (`require_record` passed; GPU job `RA-measure-exposure`,
42 views, exit 0). That measured record is **not** committed as `knowledge/exposure-groups.json` (it describes a scene
production cannot build, B3).

Draft renders (`jobq submit --gpu`, job `RA-render-previews`, 32 samples, 800x500, Blender 4.5.14, no `render_qa` gate,
not for presentation); PNGs in `knowledge/approvals-review/previews/`, each looked at:

* `v11-stair-void.png` (stair): open-riser flight, glass guard on its stringer, wall stringer, brackets and handrail sit on
  the plastered party wall; no tread floats and nothing pierces a tread. The G1 flat-bar riser infill is **not visible**: it
  exists in the spec and the Revit builder, but the scene's stair parts (`detail-stair-*`) carry no infill bars. Open item for the
  render lane, not caused by the approvals.
* `v15-family-bath.png` (family-bath sconce): the globe sconce sits flush on the marble wall beside the mirror, not floating,
  not buried. Colour cast is the draft day lighting, not a mounting matter.
* `v03-street-lounge.png` (lounge door and planting): the widened glazed door is clear; the egg-chair swing and trellis planting
  stand beyond it with the passage open, consistent with the B1 position (3.42, -24.07).
* `v36-north-garden.png`: close view of the north bed planting (dark, evening state): plants stand in their bed.

## Tests

* `tests/approvals` + `tests/pipeline`: 39 passed. `tests/test_exposure_groups.py`: 10 passed.
* `tests/test_exterior_mounting.py`, `test_mounting_scene.py`, `test_villa_scene_provenance.py`, `test_final_mounting.py`
  (596 s): 35 passed, 6 failed, 6 errors. **Ten** of the twelve are the B2 furniture-receipt `ValueError` (full-scene builds).
  The other two are separate defects, neither in lane RA paths:
  * **B4 `villa_render_contract.validate_scene` rejects any scene that carries P2 ids**: `drape admission: stale or unbound
    drape cache reference: dress-hers-long-hang-0-garment-0-0` (`test_ceiling_unknowns_are_unresolved_and_small_moves_only`).
    Reproduced on the evidence scene: `validate_scene(scene)` returns that error, `validate_scene(without_ids(scene))` returns
    `[]`. Same class as the exposure digest (P2's "request to the lead"). Fix, lead-owned file: start `validate_scene` with
    `scene = without_ids(scene)`.
  * **B5 stale frozen stair test**: `test_design_elevations_and_tread_ends_remain_frozen` pins stair x coordinates to
    `tests/fixtures/c4-stair-phase1.json` (pre-G1); the wall stringer starts at x 5.441 now against 5.457 frozen, the 16 mm tread
    overlap. It needs the fixture re-frozen with the G1 geometry (not my paths).
* `tests/test_villa_exposure_assets.py`: 2 fail on missing `out/villa/round3/stage-props/*` assets in this worktree.
* `python scripts/lane_guard.py RA`: clean.
