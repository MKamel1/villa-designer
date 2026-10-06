# C4 Phase 2 current CHECKPOINT — incomplete, uncommitted

**2026-10-05 resume:** lead stair decisions 1-4 are applied and all 22 stair
components pass real hosts. Packages b (bathroom) and c (wall lights) have
reached their requested stop. Current evidence, movements and validation:
[packages a/b/c checkpoint](c4-phase2bc-checkpoint.md). There are 58 pending
movement rows and 500 remaining missing hosts. Do not continue packages d/e
in this job. No commit or presentation-scene replacement was made.

The material below is the preserved historical first-fix record; its pending
stair approvals, nine stair findings and counts are superseded by that resume.

Phase 1 is preserved. This is the required first-fix stop after stair diagnosis and the first construction package, not completion of Phase 2. No commit, native Revit rebuild, workstation deployment or replacement of the existing `out/villa/render-d1/scene.json` was made. Candidate files are under `out/c4-phase2a`.

## Authority and scope

The ONE finish build-up record is [finish-build-ups.json](../knowledge/finish-build-ups.json). It contains exactly the lead's verified printed-page figures, the labelled 10 mm porcelain and 20 mm marble assumptions, and the missing ceiling/exterior data. The selected adhered-wall bed is explicitly an assumed 3 mm selection within the verified 3–6 mm range. No slab/board thickness or ceiling clear void is inferred. Existing floor and ceiling design elevations and exterior geometry remain unchanged.

Only the stair party-wall host is consumed by this first package. Hosts for the remaining walls, ceilings, floors, stair supports and joinery panels are still to be declared. Missing hosts cannot be treated as zero error.

## First construction package and new diagnosis

The stair generator now exports its measured CAD outer-wall datum and retained 250 mm tread setback. `revit_spec` carries that datum and its existing 200 mm structural wall thickness; the render no longer hard-codes the outer wall coordinate. The occupied-side structural face is model y = −28.471 m, and the 13 mm two-coat plaster face is −28.458 m. Model x runs from street to garden, model y toward plot east, and model z upward; coordinates are metres.

Twenty-two components have explicit host and fixing contracts: 16 wall stringer bearings, four brackets, one wall stringer plate and one wood handrail. The rail retains its 85 mm nearest-face clearance, 40 mm width and original elevation. The plate retains its 30 mm projection. All horizontal positions and design elevations are checked against 22 frozen phase-1 meshes. The tread ends remain unchanged. Plaster is applied only to existing occupied party-wall faces between the flight ends, not across adjacent-room wall runs.

The inspected [section preview](../out/c4-phase2a/stair-section-preview.png) is a measured diagnostic at model x = 7.557 m, a supported section. It is not a photoreal preview or approval. The full finite-host check exposed nine contacts that the infinite-plane contract alone missed:

| Components | Measured issue |
|---|---|
| `detail-stair-wall-stringer-00` through `-06` | The core/partition return does not provide the declared party-wall finished face across the fixing footprint |
| `detail-stair-wall-rail-bracket-04` | Fixing footprint straddles the ground-floor wall's lower edge |
| `detail-stair-wall-stringer-15` | Bearing reaches 3.529 mm below the basement wall bottom |

The first package is therefore still a candidate. Do not extend or move a structural wall, lower a floor or change a fitting elevation to make these findings disappear. Lead coordination must determine the actual fixing hosts and parent support at the return/slab/floor edges. The candidate has 22 valid plane contracts, but it is **not** a clean migrated scene.

## Guard and evidence

`scripts/verify.py` unconditionally runs `mounting.scene_findings`; the registry is [mounting-guards.json](../knowledge/mounting-guards.json). The guard reports missing hosts, unknown recessed housing or clear void, housing beyond a declared void, stale finished-face exports, and signed measured burial/projection errors. The comparison tolerance is **1 mm**, an assumed model tolerance for whole-millimetre rounding and export arithmetic, not a workmanship allowance. Finite surface-fixing coverage uses that same tolerance and actual exported host polygons.

The frozen l0856 handrail at −28.611…−28.581 m fails the measured guard. Frozen l0119 preserves a 2732 mm housing top and 2700 mm ceiling; its historic void is correctly missing. A separately labelled 25 mm witness fails a 32 mm housing, while a declared 50 mm clean witness passes. Unknown housing depth fails. The actual first candidate's unsupported stringer 04, supported sibling 08 and finite wall panels are frozen independently in `tests/fixtures/c4-stair-host-coverage.json`.

Tests cover proud/buried mutations, missing/stale records, reversed wall normal, floor mounting, removal of a genuine host surface, tolerance-rounding negative cases and the shared stair datum on D1/D2/D3. The genuinely supported subset stays quiet. Full-scene verification deliberately remains red: **560 unbound components plus nine finite-host failures = 569 findings**. Details: [mounting report](../out/c4-phase2a/mounting-report.json).

The two defects remain OPEN in `docs/LEARNINGS.md`; the repeatable procedure is [finished-surface mounting](ops/finished-surface-mounting.md). The finite-coverage check samples fixing-plane vertices and their centre; it does not certify anchors, fixing capacity or containment across every possible opening. Native coordination remains required.

## Movements awaiting lead approval

Every displacement over 5 mm is listed by identifier, old bounds, new bounds, millimetres and reason in [movements-over-5mm.csv](../out/c4-phase2a/movements-over-5mm.csv). Bounds list minimum x/y/z followed by maximum x/y/z, in metres. Movement is the maximum corresponding-vertex displacement; reshaping a fixing end counts, not just translating a whole object.

There are 23 rows: rail and plate translate 13 mm; 16 stringer wall ends and four bracket wall ends move 213 mm from the old outer-wall line to the candidate finished face; one finish-face row records the 13 mm plaster addition. Bracket rail ends move 13 mm; tread ends and all elevations are retained. Every row is marked PENDING. The 213 mm correction is a shortened visible bearing/bracket envelope, not proof of a designed structural anchorage.

## Camera cleanup

`v14-dressing` is retired. `v31-dressing-hers` retains its subjects, camera selection and dimming, and now participates in the regular review list. `v32-dressing-his` is retained. Captions, the C3 review list and the exposure-cohort regression use the retained pair. Recompute the evening exposure cohort from the retained full view set; do not reuse an old duplicate-weighted lock.

## Verification

All test processes used `NO_COLOR=1`; exit status, not text filtering, determines the outcome. **Final full suite: 691 tests in 374.014 seconds, exit 0.** Final affected modules: `test_mounting_scene` (12 tests, exit 0) and `test_render_views` (10 tests, exit 0). The five original phase-1 mounting tests remain present and pass in the full suite. The earlier 691-test run exposed one ordinal camera-selector regression; selecting by identifier fixed its cause, and the final full suite passed. Its failing log is preserved separately. `verify.py` completed with **exit 1** on the 569 mounting findings; its remaining checks passed. `checkpoint_mounting.py` completed with **exit 1** because the candidate has nine unresolved host contacts, while still writing the review artifacts. Unit-test success does not approve this candidate or complete Phase 2.

Logs: `out/c4-phase2a-full-tests.log`, `out/c4-phase2a-full-tests-final.log`, `out/c4-phase2a-full-tests-before-camera-selector-fix.log`, `out/c4-phase2a-focused-final.log`, `out/c4-phase2a-camera-tests-final.log`, `out/c4-phase2a-verify-final.log`, and `out/c4-phase2a-checkpoint.log`. No native model acceptance is claimed.

## Lead render/review list and next package

First review the movement CSV and the actual core/slab/floor host contacts. Obtain an isolated neutral-light photoreal stair close-up with a scale figure before integrating the first package. The relevant skill instruction is “stop-and-report … after the first fix (with its preview)” in [villa-render/SKILL.md](../.agents/skills/villa-render/SKILL.md), Integration discipline 9; defect-learning also requires CHECKPOINT 2 before closing a defect. These requirements are the reason work stops here before the next construction package.

The lead's room views, after resolving host contacts and approving movements, are:

- Stair: `v11-stair-void`, including the core return and low-end bearing close-ups.
- Bathrooms: `v12-ensuite`, `v15-family-bath`, `v16-guest-wc`.
- Cove: `v10-living-evening`, with ceiling/trim and cove-detail close-ups.
- Lounge: `v03-street-lounge`; include `v08-cinema` for the other wall-mounted screen.
- Dressing: `v31-dressing-hers`, `v32-dressing-his`; no v14 duplicate.

Remaining Phase 2 work: resolve the first package's real support hosts; finish all host declarations; migrate bathroom fittings, then wall lights, then ceiling fittings, then TV/shelves/joinery/trellis/climbers. Remove each local face offset only when its intended fixing/projection is declared. Unknown downlight housing depths and ceiling voids must continue to report missing; no clean whole-scene claim or defect closure is justified yet.
