# Lane RA2: production D1 scene build (2026-11-21)

Base `origin/integ/aplus` `1ebeb1c`. Blockers B1-B5 from `docs/lanes/RA-review.md`. No guard was loosened and no bypass
was used: the production build (`scripts/benchmark_scene_build.py --write-scene`, receipts active, exposure record
required) passes. Mounting guards untouched.

| | decision / change | evidence |
|---|---|---|
| B1 | `landscape-north-mid-02` moved (3.00,-24.17) -> **(3.42,-24.07)** in `knowledge/garden-palette.json` (RA's patch, applied unchanged) | the scene builds past the hanging-swing envelope guard and the lounge-door passage guard; both guards untouched |
| B2 | `furniture-stage2` and `parents-bed` receipts regenerated after the baseline-relative review below | `evidence-ra2/` |
| B3 | `knowledge/exposure-groups.json` re-measured on the production scene (Blender via jobq `RA2-measure-exposure`, GPU lock, `villa_scene.py --measure-exposure-groups`); the measured file is copied byte-for-byte | `require_record` accepts it inside `write()` |
| B4 | `villa_render_contract.validate_scene` starts with `without_ids(scene)` | `tests/approvals/test_render_contract_ids.py` (3 tests) |
| B5 | `test_design_elevations_and_tread_ends_remain_frozen` re-frozen against the G1 stair | `tests/approvals/g1-stair-frozen.json` (derived from the model) + negative checks |
| extra | `test_mounting_finish_layers` compared a mesh to a pre-P2 fixture (same class as B4): compares the stripped mesh | test only |

## B2: room review (what changed, why, is it safe)

Method: build the receipt-era tree (`038e476`, where the receipts were last written) and the current tree as diagnostic
baselines (receipts bypassed, `refresh_furniture_integ5.py export`). **Sanity: the old tree reproduces every one of the
eight stored section digests**, so the comparison is against what the receipt actually froze. Receipts are computed
mid-build, before P2 attaches element ids, so both sides are compared with `without_ids` (a first diff that did not
strip them flagged ~940 meshes whose only difference was the three P2 fields; none is a geometry change).

| section | verdict | cause |
|---|---|---|
| layout, models, props, materials | unchanged | |
| specification | changed, **accepted** | added keys `guards`, `stair_infill`, `stair_infill_spec`, `stair_nosing_overlap_mm`, `understair_cupboard` (G1); `wall_joins_fixed` and 3 walls lengthened 0.2 m (M corner fix); stair 15 treads x-start -16 mm (G1 overlap), balustrade nosing profiles -8 mm (G1); door 9 lounge street door 3.41 -> 3.71 m `tight` (G1), door 16 `swing` (G1 core door). No other spec entry differs |
| furniture | changed, **accepted** | only `stair-flight-store` (this lane's trim, below) |
| meshes | changed, **accepted** | only `marker-PATH-corridor-07/08/09` (M: wall GF-33 lengthened, same cause RA proved by ablation) |
| architecture | changed, **accepted** | 400 faces removed / 400 added, **0 unexplained**: stair flight 92 (G1), lounge door 128 (G1 3.71 m jambs and wall faces), wall GF-33 finish faces 126, corners 11+11+32 (M). `arch_attribution.py` |

FIX1/B1 planting is outside every receipt section (garden props are not in a receipt room), so it changes none.

Reviews: `refresh_furniture_integ5.py review-current` on the current baseline: **16 individual + joint baseline-relative
reviews, all ok, 0 relative findings, no check worse than its baseline**; the 83 absolute `layout_findings` are identical
to the old receipt's (the pre-existing headboard-slat overlap etc. are untouched, not claimed clean).
`evidence-ra2/room-review-summary.json`.

Independent clearance check (`clearance_check.py`, not the review engine): every furniture item and derived chair
against the understair cupboard footprint, the three guards (buffered), every wall rectangle (incl. M extensions), the
3.71 m lounge door opening plus 0.3 m approach, and the core door swing disc (R = 1.0 m). Result: no overlap and no item
within 5 cm, except `pantry-shelves-1/2` which stand against their wall (gap 0.0, by design). Positive control: the old
1.80 m store reports the 0.539 m overlap with the cupboard (lane D's 0.54 m).

Receipts retain their visual approvals (reviewed images and cameras): none of the sixteen items is in a room whose look
changed. The receipts record `refresh_2026_11_21` (reason and evidence). Reproduce:

    python scripts/refresh_furniture_integ5.py export --output out/ra2
    python scripts/refresh_furniture_integ5.py review-current --output out/ra2
    python knowledge/approvals-review/refresh_receipts.py out/ra2 [--write]

## Store furniture vs understair cupboard (decision)

`stair-flight-store` ran x 5.30..7.10; the G1 cupboard starts at x 6.561. **Trimmed to w 1.20 (x 5.30..6.50, 61 mm
from the cupboard); not removed.** Why: it is the smaller change (the D1 checks require both stores, removal fails
`under_stair_storage`, and standing access x 5.30..5.85 must stay), and the cupboard (2.6 m3) now holds the low end the
trimmed part would have. Consequences found and handled:

* fixture numbering is per room (`n[room]`), the `BACK` strips share it with the STEP markers: dropping the seasonal-boxes
  bay renumbered the approved `marker-STEP-stair-b-04..06` and made the approval guard raise. **Kept three bays**
  (0.55 / 0.35 / 0.30) so no approved id moves.
* a lone folded-linens box in the 0.30 m bay was a "bare rectangular proxy" (physical-part guard): the stack is now two
  piles of unequal height (`villa_furnish3d.py`).
* G1's 16 mm overlap made neighbouring tread x-ranges overlap, so the soffit check at x 5.850/6.001 failed on the
  integ base already (`test_d1_round3` red before this lane): each span now stops where a lower tread begins.

These two files are lead-owned (`src/archpipe/concept/villa_furnish.py`, `villa_furnish3d.py`); `lane_guard` reports them.
They were edited because the lead's decision requires the trim; revert them if another route is preferred (then B2
must be redone).

## Scene hashes (production build, receipts and record active, no bypass)

| | |
|---|---|
| scene.json | 631,587,244 bytes, sha256 `f7a7fe76418a04ff1fe75b2fdfe8596e095783bb2923155fd303afa35b9ee7b3` |
| ids stripped (`json.dumps(without_ids(scene), sort_keys=True)`) | sha256 `c6bffd3956699fdbcfe4836e8aae0b55802d4093cb434b6afc5db077e5328688` |
| meshes / lead-approved rows | 1,234 / 64 |
| `source_hash` | `65f77a130fdb7cc5918ae6f196343b728ced3b560143b35dc59b7f568525b508` (build 160 s, linux) |

The file hash includes `provenance` (`git_dirty`, HEAD) and is therefore tied to the build's checkout state.

## Previews (draft: 32 samples, 800x500, jobq GPU job `RA2-render-previews`, each looked at)

`knowledge/approvals-review/previews-ra2/`.

* `v11-stair-void.png`: open-riser flight, glass guard on the open side, timber handrail on brackets, wall stringer.
  **The G1 riser infill bars are not in the scene.** No `infill`, `riser` or `cupboard` mesh exists in the 1,234
  meshes; the infill and the understair cupboard live in the spec and the Revit builder only. Defect for the render lane.
* `v29-under-stair-store.png`: very dark draft (store lights off in this exposure); shows the sliding door and the stair
  soffit; **no cupboard geometry** (same defect). Not judged for lighting.
* `v36-north-garden.png`: planting stands in its bed, dark evening state; nothing floating or buried.
* `v39-north-garden-hanging-retreat.png`: the hanging egg chair beside the lounge glazing with the door side clear,
  consistent with (3.42,-24.07).

## Tests (run on this branch, linux workstation, `NO_COLOR=1`)

| suite | result |
|---|---|
| `tests/approvals`, `tests/pipeline`, `tests/test_exposure_groups.py` | 52 passed |
| `tests/test_mounting*.py` (596 s class builds) | 35 passed, 1 failed (`test_mounting_finish_layers`, P2 ids vs pre-P2 fixture); fixed, rerun: passed |
| `test_mounting_finish_layers`, `test_villa_scene_provenance`, `test_d1_round3` | 18 passed |
| `test_render_views`, `test_darkviews`, `test_d1_wp6` | 37 passed, 1 failed (`test_d1_wp6` pinned 75 details / 59 bodies; the trimmed store has 69 / 53, six fewer bay parts). Pins updated; 8 passed |
| `scripts/verify.py` | not runnable: `ImportError: cannot import name 'SpecError' from 'archpipe.model'`, identical on the untouched base |

Guards left behind: B4 `test_render_contract_ids.py`; B5 negative checks in the stair freeze (1 mm tread-end move, 1 mm
elevation change); the clearance check's positive control (old store -> 0.539 m); the section/attribution scripts
(a new unexplained change shows as `UNEXPLAINED` / a changed section). Lessons: `docs/lessons/RA2.md`.

## Files outside lane ownership (lane_guard reports them; lead decision, see "Store furniture")

`src/archpipe/concept/villa_furnish.py`, `src/archpipe/concept/villa_furnish3d.py`, `tests/test_d1_wp6.py` (pinned counts
that follow the trim).
