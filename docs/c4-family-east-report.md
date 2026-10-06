# Family bathroom: client east-wall WC decision

2026-10-06, Linux lane A. Client decision dated 2026-10-05 applied to the authored candidate. No commit, full suite, native Revit build/read-back, or presentation render. Existing C4i finish-layer implementation retained. WC means water closet; GF means ground floor. Positions and bounds below are metres in the existing model axes; clearance values are millimetres. East/west here identify the client's opposite x1/x0 bathroom walls, not a change to project axes or north.

## Position and construction

The WC envelope centre moves from **(9.575000, -26.101000)** to **(11.129000, -25.819500)**: +1554 mm in model x, +281.5 mm in model y. It turns 180 degrees, from rotation -90 (front toward positive x) to +90 (front toward negative x). Heights, pan/seat/plate geometry and room/door/shower/basin positions are retained. The old pre-migration authored centre was (9.552, -26.101); current public layout and native specification use the new finished placement. The basin's measured centre remains **(9.525, -25.686)**; its historical pre-migration centre remains (9.502, -25.686).

C4 host `bath-fb-wc-east` is measured from `shell-024-marble-bath`: structural face x = **11.427**, occupied-side normal (-1, 0, 0), finished face x = **11.404**. Normal means the direction into the room. Build-up uses `knowledge/finish-build-ups.json`: **20 mm ASSUMED marble + 3 mm selected thinset**, an assumed selection within Ching's VERIFIED 3–6 mm bed range (Building Construction Illustrated, printed 10.14). Pan and flush plate bind through the C4 API as wall-hung, with zero back-face projection. C4i constructs the actual closed marble finish solid from the new measured host; diagnostics alone do not supply support. Historical approved mounting movements are preserved.

The authored centre balances the available side-zone margins between the finished south boundary and the shower. The 350 mm interval begins at y = -25.948; the 1000 mm shower-side interval ends at y = -25.691. Their midpoint is -25.8195, leaving **128.5 mm spare on each side-zone requirement**. The full-room review then verifies fronts, shower entry, wet-zone separation, door and route; no fixture moved to satisfy a camera.

**All family clearance rows pass. Both fixture fronts have only 4 mm spare over 1100 mm.** These are candidate-envelope results, not installation tolerance or verified-as-built acceptance.

## Full family-bath clearance table

All numeric columns are millimetres. Non-intersection rows require no overlap, not a sourced splash setback. Door results use the existing conservative swing square. Route width is a lower bound from the existing 20 mm raster, resolved in 10 mm increments and capped at 1500 mm. Access zones may overlap where the source permits; fixture bodies may not occupy them.

| Check | Achieved | Required | Status | Limiter / scope |
|---|---:|---:|---|---|
| fb-shower front approach | 780 | 762 | PASS | limiter: fb-basin |
| fb-wc front approach | 1104 | 1100 | PASS | limiter: fb-basin |
| fb-wc centreline side 350 | 478.5 | 350 | PASS | limiter: finished room boundary; mirrored handedness; basin rear encroachment capped at 300 mm |
| fb-wc centreline side 1000 | 1128.5 | 1000 | PASS | limiter: fb-shower; mirrored handedness; basin rear encroachment capped at 300 mm |
| fb-basin front approach | 1104 | 1100 | PASS | limiter: fb-wc; 700 mm basin approach width |
| fb-wc separation from wet zone | 928.5 | 0 | PASS | Geometric non-intersection with authored wet floor |
| fb-basin separation from wet zone | 780 | 0 | PASS | Geometric non-intersection with authored wet floor |
| shower entry clear-floor width | 1630 | 1219 | PASS | Full shower frontage has the reported front approach depth |
| door swing gallery-end/family-bath | 102 | 0 | PASS | limiter: fb-wc |
| door-to-all-fixtures route | 1090 | 914 | PASS | 20 mm raster; achieved lower bound to 10 mm; all nodes reached |

Sources: [held WC and basin cards](../knowledge/library.json), UK Approved Document M Volume 1, 2015 edition with 2016 amendments, Diagram 2.5 printed p.20 (350/1000 mm centreline sides; 1100 mm fronts; basin strip 700 mm wide); `nkba-shower-clear-floor-762`, NKBA 2nd edition 2016, access-standard clear floor 762 × 1219 mm; `mitton-path-of-travel-min`, Residential Interior Design 4th edition 2022, printed p.68, 914 mm route. Existing original-page-checked cards were retained; held PDF originals are unavailable on this workstation. This is project best-practice guidance, not jurisdictional approval.

The shower's authored wet footprint remains x 9.567–11.197, y -24.691–-23.791 (1630 × 900 mm). The 762 mm card applies to the clear floor at its entry, not its interior depth. Its full 1630 mm frontage has 780 mm clear floor ahead. Basin strip remains 700 mm wide and has 1104 mm depth to the relocated WC.

## Movement list and coordinated records

Each bounding list is [minimum x, minimum y, minimum z, maximum x, maximum y, maximum z], metres. Maximum vertex travel includes the turn and differs from envelope-centre travel.

| Record | Before bounds | After bounds | Maximum vertex travel mm |
|---|---|---|---:|
| `host-face-bath-fb-wc-east` | 11.427000, -27.371000, 0.000000, 11.427000, -23.591000, 2.800000 | 11.404000, -27.371000, 0.000000, 11.404000, -23.591000, 2.800000 | 23.000000 |
| `furn-fb-wc-0` | 9.300000, -26.301000, 0.120000, 9.850000, -25.901000, 0.400000 | 10.854000, -26.019500, 0.120000, 11.404000, -25.619500, 0.400000 | 2141.098625 |
| `furn-fb-wc-1` | 9.300000, -26.221000, 0.950000, 9.320000, -25.981000, 1.120000 | 11.384000, -25.939500, 0.950000, 11.404000, -25.699500, 1.120000 | 2167.666545 |

- `furn-fb-wc-0` carries the procedural pan and seat; `furn-fb-wc-1` is its flush plate. Native furniture emits pan, seat and flush plate as three boxes at the matching pose; the native body union is checked against render body bounds. Rigid child ownership is recorded after the rotation, and split movement fails the existing assembly guard. No other WC-related visible fitting exists in this scene.
- `villa_furnish.layout`, `revit_spec.build` sanitary placement, `villa_furnish3d.spec`, mounting contracts and movement records agree. Native export is reviewable in `out/c4-family-east/native-spec.json`; it is generated output, not a hand-edited extract.
- No concealed cistern/carrier solid or soil-stack location was previously modeled. Their installation/flush-plate connections are now specified at the east-wall installation in `fb-wc-east-services`, with the exact note **services coordination pending** and no invented coordinates.
- Basin, mirror, vanity lights, shower, door, walls' authored source polygons and lighting photometry are unchanged. The new east finished layer is constructed using C4i.

## Preview, guards and validation

Inspected [diagnostic before/after plan](../out/c4-family-east/preview.png). It shows the west-wall collision clearing, opposite-wall pan and plate installation, overlapping allowed access zones, unchanged door/shower and tight front gap. It is not a photoreal preview or native model review.

| Command / focused modules | Result | Exit | Log |
|---|---|---:|---|
| `test_sanitary_relocation`, `test_final_mounting`, `test_mounting_finish_layers`, `test_mounting_scene`, `test_support_mounting`, `test_render_views`, `test_rfa_portable` | 57 tests passed | 0 | `out/c4-family-east/focused.log` |
| `test_villa_furnish`, `test_villa_furnish3d`, `test_evidence_values` | 44 tests, OK; 1 original-source availability check skipped | 0 | `out/c4-family-east/furnish-focused.log` |
| final `test_sanitary_relocation` rerun after entry-width source correction | 4 tests passed | 0 | `out/c4-family-east/sanitary-final.log` |
| `test_render_standard.RenderStandard.test_nothing_floats`, `.test_openings_passable` | 2 tests passed on default `VR.build()` | 0 | `out/c4-family-east/render-support-focused.log` |
| `scripts/verify.py --portable` final | ALL PASS; installed Windows Revit family corpus explicitly skipped | 0 | `out/c4-family-east/verify.log` |
| `scripts/checkpoint_family_east.py` final | mounting [], unsupported [], family clearance failures [] | 0 | `out/c4-family-east/checkpoint-final.log` |

All use `/home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python`, `PYTHONPATH=src`, `NO_COLOR=1`. The first focused run failed on two proof assumptions: native pan/seat boxes had been mistaken for one part, and open wet floor was treated like an enclosure in side-zone review. Actual part bounds and the existing permitted open-zone overlap resolve them; the retained first log is `out/c4-family-east/first-focused.log`, exit 1. No threshold was relaxed. Final checks prove frozen west-wall failures, clean current geometry, an injected deficient side gap, renamed/translated rigid assemblies, stale/split plate movement, native agreement and C4i physical support. Registry and operating workflow updated together. The lead runs the full suite.

## Views to render

- **v15-family-bath**: basin and shower, day with bathroom lights on. Current chosen camera (10.327, -26.371, 1.35), 16 mm lens. Its intent does not include the WC.
- **v35-family-bath-wc**: added separate WC subject, day with lights on. Chosen camera (9.727, -24.971, 1.35), 16 mm lens, level eye; complete WC framing checked. Both wide lenses are explained by the chooser's recorded frame limits. Camera coordinates are metres.

View records: `out/c4-family-east/views.json`. Run the separate WC draft as it is final-only; final-only does not waive preview review. Native Revit build/save/extract and measured read-back, lighting remeasurement and photoreal/render review remain with the lead before integration. No real villa stage gate is approved by this candidate.
