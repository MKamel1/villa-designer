# C4i — physical finished surfaces

Implemented separate **closed finish-layer solids**, preserving source geometry
and the mounting audit datums. Moving shell planes alone would omit the exposed
finish edges and opening reveals. `finish_layers.build` extrudes measured wall
contours by the host's authoritative build-up (23 mm marble/bed; 13 mm plaster),
with outward winding and the host's finish material (18 solids). Covered original polygons
are replaced, preventing coincident shell interfaces. Host/support bookkeeping
remains in `diagnostic_meshes`. Existing stair surfaces already at their finished
planes retain their geometry. Shared polygons serving different room finishes
are partitioned at room boundaries; supplemental support patches are restricted
to their host room. Ordinary hosts retain their complete measured wall extent.

The material name selects the same Blender shader, tint, texture projection and
metre scale as existing shell marble. No exposure or material substitution was
used. Opening contours survive triangulation/extrusion; tests cover a keyhole
window, reverse normals, translated geometry and a zone boundary through a
window edge. Invalid clipped keyhole topology is repaired before extrusion;
disconnected contours fail closed and require separately declared wall zones.

## Guard and reproduction

`surface_findings` compares each nonzero-finish mounted item's projected mounting
side against actual render building triangles facing the host direction, within
2 mm. Diagnostic meshes, glass, nearby floors and perpendicular reveals cannot
supply wall support. `solid_findings` checks two faces per edge, opposed edge
winding and positive enclosed volume. Both run unconditionally in `verify.py`.
Registry: `knowledge/mounting-guards.json`, lesson text:
“fittings mounted to a finished face float when the finish layer is bookkeeping-only”.

The real scene built with finish construction suppressed reproduces the original
51 unsupported islands (35 unique mesh IDs, frozen by value). The new guard also
catches plaster siblings previously inside the older 15 mm support tolerance.
Repaired and suppressed evidence: `out/c4i/geometry-evidence.json`.

## Three regressions

- **Support source lookup:** finite yard-edge hosts are diagnostic geometry;
  the test searched only render meshes. It now resolves the source across both
  channels while retaining the source-identity, travel and pending-pose checks.
- **Missing ceiling label:** validation still requires render mesh labels.
  The frozen host moved to diagnostics, so replacing it in the render list was
  a no-op. The reproduction explicitly reinserts the frozen missing-label mesh;
  the sibling removes the label from a real rendered ceiling surface. Both fail
  validation without changing the diagnostic-only contract.
- **19.537 versus 19.480:** `detail-headboard-slats` was correctly trimmed by
  `c4-final-approvals.json` (`headboard_margin_m = 0.01`), after the earlier
  `c4-e-lead-approvals.json` mounting approval. 19.537 m is the correct final
  first-vertex coordinate; the width changes from 1980 to 1586 mm about the
  unchanged bed centre. Both coffee bodies likewise receive the final approved
  12 mm assembly seating. These final operations omitted movement records.
  They now append immutable final records for the panel and every coffee member.
  Exact face equality remains asserted against the latest record, and every
  frozen approved host/bounds pair must still exist with applied status. No
  geometry approval was applied twice and no approved pose was undone.

The ensuite hand-shower rail is intentionally 63 mm off the finished face,
86 mm off the original shell. Both of its own brackets reach the finished wall
and intersect its rail sides. Removing both brackets makes the rail unsupported;
its geometry and fitting data are retained.

## Preview and verification

Neutral Blender close-ups: `out/c4i/ensuite-rail-before.png` and
`out/c4i/ensuite-rail-after.png`, 960 × 640 pixels, 256 samples, identical camera
and light. Independent render critic accepts the lit textured marble and apparent
bracket seating; measured tests certify contact. Faint shadows, faceted procedural
fittings and angular hose remain disclosed. These views compare the floating
shell case to the physical layer; they do not reproduce the older black-wall
render. Review: `out/c4i/preview-review.md`. Presentation, native and lighting
acceptance remain separate; this task makes no such claim.

Final focused-test and portable verification exit evidence is recorded below.

- All **108 focused tests pass**, exit **0**, using the supplied interpreter,
  `PYTHONPATH=src` and `NO_COLOR=1`. Includes all requested modules and the new
  finish-layer regressions. `render_support.unsupported(VR.build()) == []`.
- `scripts/verify.py --portable` exits **1 only for the three reserved family-bath
  items**: WC side clearance 197/350 mm, opposite side 200/1000 mm, basin approach
  0/1100 mm (achieved/required). Family-bath fitting geometry remains unchanged.
- Suppression: **51 unsupported islands; 52 render-surface findings**. Repaired:
  **18 closed solids; zero unsupported items, surface findings or solid findings**.
- Logs: `out/c4i/baseline-tests.log`, `focused-tests.log`, `verify-portable.log`.
  HEAD remains `9069c24`; no commit, native rebuild or shared-data modification.
