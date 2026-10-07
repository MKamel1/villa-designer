# Garden change 4 (G4) — north garden

2026-10-06. Implemented in the scene pipeline; focused acceptance and
diagnostic critic review complete. No presentation rendering or commit.

## Naming, authority and scope

Client names follow the street. In the model, x runs north to south, y runs
west to east, and z runs vertically upward; coordinates and dimensions below
are metres. Negative x is north, positive y east, positive x south, negative y
west. True north is used only for solar calculations. Current identifiers follow knowledge/site-orientation.json; frozen historical IDs resolve through its explicit alias table.

Only the client's north garden changes. Its authored
scope is x −0.373 to 3.617 and y −29.916 to −23.591; gravel is intersected with
the actual yard boundary at y −29.91566. Ground soil elevation is z −3.0.
The top garden, east yard and south garden retain their landscape meshes,
props and objects: frozen pre-change hashes are compared in regression tests.
The lead's uncommitted grape-ivy record is retained and extended without
retiring the earlier garden fixes. The withdrawn top-garden removal request
is not applied.

Botanical authority is [garden-palette.json](../knowledge/garden-palette.json),
from the lead's NC State page checks on 2026-10-06 and supplied research in
`out/agy-research/shade-palette.md` / `.json` and `shade-climber.md`.
VERIFIED denotes checked source evidence, ASSUMED denotes design/appearance
intent, PARTIAL denotes incomplete site applicability, and UNVERIFIED denotes
missing local evidence. Pet non-toxic tags do not establish human safety.
No local Egypt performance or procurement is claimed.

## Contents and planting

- Bistro table and chairs: **removed per client 2026-10-06**, with no relocation.
- Both lounge door pots, their soil/plant assemblies and every raised container
  in this court: **removed per client 2026-10-06**.
- Ixora and Strelitzia: removed from this garden; retained in the unchanged east
  yard/top garden as applicable.
- Swing: omitted. Its old placement is covered. A fixed-scale/orientation search
  of 9,672 translations on a 0.05 m grid finds 232 open motion envelopes, zero
  clear of the fixed landscape/boundary obstacles. This is a bounded screen,
  not a continuous feasibility proof. **Client to confirm swing removal.**
- Open timber trellis: retained, moved 0.16 m along its boundary wall toward the
  brighter end, and planted in Cissus alata. No route is blocked.
- Under the ground-floor balcony: gravel only.

The main soil bed is x −0.05 to 3.45, y −28.50 to −26.90. The accent bed is
x 0.50 to 1.90, y −25.20 to −24.10. Soil is at court level; assumed timber edging
is 15 mm thick and rises 18 mm. Existing paving caps are cut back over exactly
5.60 and 1.54 square metres so the soil surface is visible without raising it.
Mineral gravel paths/mulch surround the beds, and an irregular feature stone
at (2.65, −24.05) has an ASSUMED appearance, not a supplier product identity.

| Species | Count and layer | Authored height by spread | Evidence / remaining limit |
|---|---|---|---|
| Rhapis excelsa | One tall accent | 1.70 by 1.00 | Young managed clump ASSUMED; deep shade VERIFIED; root barrier ASSUMED |
| Fatsia japonica | Three bold back-layer plants | 1.40 by 0.85 | Pruned young envelope ASSUMED; deep shade VERIFIED |
| Aspidistra elatior | Three mid-layer clumps | 0.50 by 0.40 | Existing appearance and added checked deep-shade evidence |
| Chlorophytum comosum | Three variegated ground-cover clumps | 0.40 by 0.50 | Young appearance ASSUMED; shade quote VERIFIED; winter nights UNVERIFIED |
| Ophiopogon japonicus | Five fine edge clumps, open portion | 0.22 by 0.30 | Light applicability PARTIAL; nursery trial required |
| Cissus alata | Young trained trellis climber | Within the 1.50 by 2.20 frame | Tendrils VERIFIED; light applicability PARTIAL; winter nights UNVERIFIED |

The Rhapis centre is (1.20, −24.65), at least 1.049 m from the measured nearby
path/walls under the authored guard. Mature dimensions remain in the palette;
the appearance table does not substitute smaller rendered plants for mature
botanical evidence. Fatsia spacing is 1.00–1.15 m, and the existing spread-based
spacing/layer checks pass. Ground-bed species drifts contain three to five;
the single Rhapis is an explicitly separate accent bed. Liriope is recorded
but omitted because of its fruit caution with the three-year-old household.
Excluded foliage/climbers and the unplanted Asian star-jasmine runner-up are
recorded with their evidence/reasons in the palette.

All new plants are authored species-specific procedural appearances. No new
external plant model was imported, no licence or manufacturer identity is
invented, and no asset route record is extrapolated. Existing retained imports
continue through the tracked route-geometry records and their focused tests.

## Sun and architectural cover

Lead ray-cast summary: 20 open-part samples average about 0.9 direct hours in
June, 0.8 in March, 0.3 in December. Eight balcony samples average zero in
June/March and 1.1 in December; the winter result must not be silently omitted.
These are scene enclosure screens, not Egypt nursery performance evidence.

Five new boundary-wall ground samples at x −0.06, z −2.90 use the scene's true
bearing and 10-minute midpoint sun rays against opaque architecture. At model
−24.0 in y, measured direct hours are 1.50 / 1.00 / 1.17 for June / March /
December; the old trellis vicinity around y −25.0 gives 1.17 / 1.00 / 0.00.
The selected trellis begins at (−0.123, −25.24) and ends at y −23.74, toward
that brighter endpoint. Samples establish a preference, not every leaf's
sun exposure. Detailed results: `out/garden-g4/trellis-sun.json`, copied into
the tracked palette for reproducibility.

The ground-floor balcony/entrance platform spans x −0.123 to 3.617 and covers
the court below y −28.671, about 4.655 square metres of actual yard. Its portion
is gravel. The current scene also contains an upper-storey projection and
other opaque architectural cover: the full overhead union within the authored
court is 14.4302 square metres. This exceeds the client's description that
the rest is open to sky. **Model/client cover discrepancy remains for the lead
to resolve**; this landscape job changes no architectural cover. v36 stands
in the measured open-sky domain.

## Previews, views and defect controls

Isolated neutral previews, with a 1.8 m scale reference, cover Rhapis, Fatsia,
spider plant, mondo, feature stone, ground bed and grape-ivy trellis in
`out/garden-g4`. The render critic accepted the revised isolated forms before
integration. First previews exposed narrow disconnected Fatsia blades,
repeated Rhapis tiers/pointed tips and a regular stone; their frozen inputs,
construction fixes and guards are retained. Ivy now has closed physical
petioles connecting every trifoliate cluster to the actual training stems.
The specimen's projected foliage coverage is 34.18%; the final scene's
projected leaf-area union is 0.6875 square metres within a 2.0608-square-metre
training envelope, or 33.36%, against the ASSUMED approximately 35% young
training coverage intent. The entire measured timber-frame bounding rectangle
is 3.3528 square metres, so foliage occupies 20.51% of that whole frame;
the two denominators must not be interchanged. The critic confirmed both.
All 181 leaf clusters have closed connecting petioles and
the physical connection check is empty. Frame visibility remains explicit;
no flowers are represented. Read-back: `out/garden-g4/botanical-readback.json`.

The contextual preview then exposed coplanar paving over both soil beds.
The finish is now removed at bed boundaries and `soil_visibility_findings`
checks actual faces. Before images are retained as `*-before-soil.png`.
This changes render finish construction; it does not engineer slab excavation,
soil depth, waterproofing, irrigation, drainage or root-barrier specifications.

All cameras remain level at 24 mm and 1.35 m standing eye height:

- **v36**: caption “North garden”; (1.75, −26.20, −1.65), in measured open sky.
  Honest fully framed left planting group. The searched clear exterior points
  cannot frame the complete bed; no plant or bed was moved for a camera.
- **v37**: retained identifier, through the lounge. Trellis, grape ivy, Rhapis
  and feature stone; no bistro or pot subject remains.
- **v38**: added through-lounge companion at (4.10, −25.00, −1.65), showing the
  overall bed extent and its primary drifts. The near soil corner is partly
  screened by the existing lounge window frame; the caption discloses this.
  Opening-frame and proximity checks pass, but those do not prove every
  footprint corner unobstructed.

The critic accepted visible ground-bed construction and the diagnostic
botanical forms in all three final neutral images, then independently closed
both caption corrections. Authored-appearance limits and the screened-corner
disclosure are explicit in the final export. Review evidence:
`out/garden-g4/context-critic-review.md`. The pre-caption scene is preserved
as `out/garden-g4/scene-before-caption.json`; the final export is checked for
unchanged geometry/cameras. No presentation quality is approved.

The spatial content/soil-level guard rejects the real committed bistro/pots,
renamed/translated siblings, raised soil, incompatible plants and covered
swings. A first Fatsia door conflict is now checked in the landscape candidate,
not only after export. Camera proximity now includes procedural ground
foliage. Plant continuity, fan construction, stone irregularity and ivy
connections carry separate checks. Proofs are in `tests/test_garden_g4.py` and
`tests/test_render_views.py`; controls are registered in
`knowledge/garden-render-guards.json` and indexed in `docs/LEARNINGS.md`.

## Verification and operational limits

The final authoritative export has `unsupported == []`,
`blocked_openings == []` and `soil_visibility == []`; the whole view-plan
checker exits 0. After caption corrections, all 1,017 meshes, 40 props,
121 lights, materials and cameras match the reviewed export exactly.
Evidence: `out/garden-g4/acceptance.json`, `export-readback-final.log` and
`context-critic-review.md`. Portable verification exits 0 with normal HOME
and with HOME set to the empty `/tmp/g4-empty-home`; final logs are
`verify-caption-final.log` and `verify-empty-caption-final.log`.

The final focused batch **passes all 153 tests**, exit 0, in 586.718 seconds:
landscape, G4, render standard/views, final/support mounting, provenance,
garden subjects and asset route geometry. Log: `focused-final-pass.log`.
It includes the corrected provenance mock's contract-required empty lights
list and the caption disclosures. The initial 152-of-153 pass/error log is
retained, along with the interrupted stale-test batch; neither is counted
as final acceptance. `git diff --check` also passes. Logs and scene evidence
live under `out/garden-g4`; the lead owns the full test suite and commit.

An operational finding was corrected during this task: the builder generated
generic desk-lamp photometry in global OUT. I initially misidentified its
resolved destination as shared; direct path inspection showed it was this
worktree's `out/villa/render-d1`. Neither `out/villa/round3` nor `assets/user`
nor their shared targets was changed. Generic generation now occurs beside an
explicit exported scene, with unchanged photometric function/lumens/beam;
the disposable-symlink regression proves write location and byte equivalence.
Existing verified-product catalogue binding retains its separate workflow.

No packages installed, presentation images rendered, native model rebuilt,
shared target modified, or commit made. Neutral geometry/appearance previews
are diagnostic evidence; photographic species likeness, final lighting,
local nursery suitability and real design/construction gates remain open.

Current naming authority: [site orientation](../knowledge/site-orientation.json). Historical numeric sun-proxy results in this report are superseded by [the orientation and ray-cast report](orientation-naming-report.md).

<!-- garden-side: -x; name: north -->
<!-- garden-side: +y; name: east -->
<!-- garden-side: +x; name: south -->
<!-- garden-side: -y; name: west -->
