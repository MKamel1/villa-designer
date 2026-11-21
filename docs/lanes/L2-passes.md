# L2: answers to L1's gap report, and the patch-pass inventory

See [L2-model.md](L2-model.md) for the model itself.

## Answers to L1's model-gap report (2026-11-20)

1. **Net area.** Room `params`: `area_m2` = `gross_area_m2` (polygon), `clear_area_m2` (outline inset by half-wall
   thicknesses), `revit_net_area_m2` (Revit read-back, `out/villa/furnish-d1/revit/readback.json`, option 0; absent for
   cinema and store-ramp, which Revit did not read) and `net_area_m2` = the read-back where present, else the clear
   area (`net_area_basis` says which). Clear area runs 0.0-0.5 m2 above the Revit figure (columns and finishes).
2. **Guards.** The GF stair-void guard exists only as a scene detail (`villa_render` mesh `detail-stair-guard`, 1.1 m
   glass, "required; not yet in the Revit model"): now element `rail-gf-stair-void` (edges 3710 + 950 mm,
   `in_revit_spec: false`). No guard exists anywhere (spec, scene, villa_env) for the GF front terrace edge
   (`slab-gf-terrace`, `drop_to_patio_mm` 3000, `guard_present: false`), the entrance steps (`ctx-entrance-steps`,
   shared with the neighbour, 1200 mm, `guard_present: false`) or the north patio edge (`garden-north-patio`,
   `floor_below_street_mm` 1800, `guard_present: false`). Only the ramp-edge rails (`rail-edge-*`, 1100 mm) exist.
   These are facts about the design, not fixes; adding guards is a design decision for L1's report.
3. **Doors/windows.** Doors carry `operation` (hinged / pocket / sliding), `swing_into` (the room the leaf swings
   into, where authored) with `swing_basis`, `leaf_width_mm`, `structural_opening_mm` (leaf + 100 mm frame),
   `clear_width_mm` and `clear_width_basis`. The spec authors no hinge side, so hinged doors have no swing direction
   (both swing squares are kept clear in the layout checks) and their clear width is the leaf width, an upper bound.
   Windows carry `gross_area_m2` and `openable_area_m2 = null`: the spec records no operable sash (a comment in
   `villa_render` says so), so an openable area would be invented; L1 should apply a stated policy.

## Phase 2: patch-pass inventory (`archpipe.model.passes`)

`villa_render._build` no longer calls the passes inline. `PASSES` holds one record each (order, call, arguments,
`input_revision` scope, knowledge files, purpose); `villa_render` runs three stages. `passes.inventory()` returns the table.

| stage | pass | knowledge file | what it changes |
|---|---|---|---|
| mounting | c4-fitting-migrate | | bind fittings to measured hosts, bounded moves |
| | c4-bc-approvals | c4-bc-approvals.json | apply approved package b/c faces |
| | c4-guest-fixes | | guest WC handset, hose, sconce |
| | c4-vanity-emitters | | current lighting records replace C4 vanity pairs (`input_revision(False)`) |
| | c4-ceiling-migrate | finish-build-ups.json | finished ceilings, void targets |
| | c4-d-lead-approvals | c4-d-lead-approvals.json | apply approved package d rows |
| | garden-g6-mount | garden-palette.json | G6 south garden on measured supports |
| | c4-support-migrate | | support datums, rigid assemblies |
| | c4-e-lead-review | c4-e-lead-approvals.json | exterior supports |
| | c4-final-mounting | c4-final-approvals.json | final lead corrections |
| | wc-slides | | bounded same-wall WC slides |
| | sanitary-family | | 2026-10-05 sanitary relocation |
| | vanity-decision | | client's vanity decision (`input_revision(False)`) |
| assembly | finish-layers, complete-shell, garden-swing, garden-g4d | finish-build-ups.json | finishes, shell, swing, N-court uplights |
| furniture | furniture-stage2, parents-bed | furniture-stage2.json.gz, parents-bed.json.gz | measured furniture, bed omission |

Byte-identity evidence (2026-11-20, Windows laptop): the full D1 scene was built before and after this change with
the last two receipt-bound passes (furniture-stage2, parents-bed) bypassed, and every top-level section hashed
(`json.dumps(sort_keys=True)`): whole-scene sha256 `9c6946750c4e4e2203ddfc1fb8066a92787e45736bf410fad07157c1d2b7797f`
in both runs (about 11 min per build here). The stage-2 receipt itself fails at the base commit on this machine
("furniture fixed-room inputs changed ... changed sections: meshes"), so `scripts/benchmark_scene_build.py`
cannot record a baseline here; the two receipt-bound passes are called through the registry with identical arguments
but were not exercised end to end.

Status: the passes are data-ordered but their geometry logic is unchanged, so none is retired yet. Each is a mesh
transformation against measured hosts (not a placed-object delta); the knowledge files hold approval rows and receipts
that those transformations verify against, so freezing their outputs as data would only be a snapshot.
