# C8 Phase 1: shared geometry relationships

Starting commit: `f8f8cc604aa427eaa17348f8a349f69fc9c20399`, branch `codex/c8`.
No commit made. No layout, scene producer, Revit model or shared-data symlink changed.
Camera/view code, `villa_render_contract.py`, `render_qa.py`, and registry-agent files were untouched. There is no new call site in `villa_render.py`.

C8 means the audit class “geometry relationships omitted”; C4 means the existing finished-host/mounting class. D1, D2 and D3 are existing villa option identifiers. GF means ground floor; B means basement. JSON means JavaScript Object Notation; AST means abstract syntax tree (the parsed Python statements, independent of formatting).

**Implemented:** one read-only topology, production migrations that preserve public messages, frozen historical inputs, numerical relationship findings and explicit unassessed cases. **Not claimed:** complete historical proof for all 29 entries, structural support capacity, a real design approval, or full replacement of the existing controls. The coverage table records these limits individually; entries marked open must not be registered as closed lessons.

## Model and boundaries

`src/archpipe/geometry_topology.py` defines frozen records:

| Record | Existing input retained |
|---|---|
| `Host` | Finite finished faces, kind, bounds, normal where declared, original structural source identifier. Source-face hosts receive their recorded finish once; diagnostic/built faces already on the finished datum receive no second offset. Shell, floor, ceiling, slab and stair geometry remain actual scene faces. |
| `Opening` | Door/window identifier, assigned rooms/storey, authored clear width, motion-envelope basis and approach-route identifiers. Pocket doors have approaches even when their swing envelope is empty. Existing door envelopes are conservative squares/slide approach zones, explicitly labelled; window movement is absent and unassessed. |
| `Obstacle` | Every measurable mesh, prop or furniture item, including unknown types; measured extent, immutable faces/record and explicit accessory parent. Catalogue access eligibility never removes an obstacle. |
| `Support` | Recorded host, actual fixing-side/contact points, generated-part support or explicit plant support, mounting kind and projection. The existing grounded-component engine still resolves inferred chains and excludes circular self-support. |
| `Route` | Walking rectangle, floor and band top, achieved clear width when known, required figure/source, door-to-door or stair-access role and endpoints. A door approach's longitudinal depth is not presented as its passage width. |

Coordinates are metres in scene model axes: x and y horizontal, z upward. Length conversions use `units.mm_to_m`; the pitch-line adapter converts its millimetre result once. Existing villa adapters retain `revit_spec.LEVELS_Z` scene elevations rather than mixing them with the street-relative layout labels. Records and nested mappings are detached, immutable snapshots. `from_inputs` reads supplied inputs; it never calls a layout or scene builder.

Queries include exact object/walking-volume intersection, opening motion versus obstacles, accessory access versus body collisions, unsupported components, signed penetration into a finite named finished host, sampled route headroom, stair pitch-line headroom, intended-versus-recorded host identity, fixed-reference clearance, saved-specification passage obstruction, opening width lost to a crossing wall, occupied-room prop intrusion, module/run fill, built-door connectivity and hall-route width.

Findings carry query name, object/reference identifiers, achieved and required numbers, unit and requirement provenance. Intersection findings report occupied area, not a fabricated remaining width. Connectivity/support findings count reached destinations/grounded contacts; these are not bottleneck measurements. `needs-source` findings keep unavailable quantities null. Generic headroom requires caller-supplied measured floor/pitch-line samples and does not assert unsampled coverage.

Reused controls: `asset_route_record` through `route_geometry`, exact triangle/box intersection, connected mesh islands and grounded support in `render_support`, C4 finite polygon ownership and finish tolerance, `garden_level_rooms`/`extent_violations`, the furnishing disc raster, door axis/cut-wall policy, stair-end edge matching, and independent pitch-line arithmetic. No second route raster, asset-size library or support graph was introduced.

## Production migration and review checkpoints

- `villa.critique` obtains the same stair-end dictionaries/messages through topology.
- `villa_furnish._ov` forwards the same strict overlap arithmetic and tolerance.
- `villa_furnish.route_problems` retains its public signature/messages and calls topology; the original complete raster body is retained unchanged as `_route_problems`. The frozen AST test proves this, including half-open fills, exact disc distances, middle-of-side nodes, stair/void exclusion, overlap requirements, pulled-out chairs and width policy.
- The furnishing crossing-wall door check calls `opening_host_collisions`, retaining its exact messages and per-level position in the review.
- `villa_landscape.route_violations` converts topology findings back to the original ordered pairs. Its asset validation order/errors and numeric policies are preserved; differential tests use the frozen starting implementation.
- `blocked_openings` and `gf_route_width` accept optional saved specifications. Their default production behavior is unchanged. The topology queries pass frozen specifications so historical geometry is not regenerated during review.

Checkpoint 1 diagnosed disconnected representations and recovered original source revisions before the migration. Checkpoint 2 proved real/clean/sibling route, stair, passage, penetration and support cases. No visible design geometry changed, so no presentation preview was generated or integrated.

The current-design trial initially exposed a legitimate C4 representation missing from the first adapter: the stair's finite finished faces are in diagnostics, not `source_faces`. The adapter now follows the existing finite-coverage representation. A translated diagnostic-face regression proves there is no second finish offset; an infinite-plane record still refuses admission. Review also caught a proposed 10 mm module-sum tolerance; it was corrected to the existing 1 mm and a 4 mm sibling proves it cannot hide an overrun. These escapes and the workflow correction are recorded in `LEARNINGS.md`; the villa-render skill and its Claude adapter were synchronised.

## Frozen evidence

All inputs live under `tests/fixtures/`, independent of live `out/`:

| Fixture | Origin |
|---|---|
| `c8-round2.json.gz` | Actual concept A at `eb3283b`, including the original straight stair and surrounding rooms. |
| `c8-round8.json.gz` | Actual P1 at `2e8ae9f`; retained as historical context, not falsely labelled the failing stair-turn design. |
| `c8-round8-P3.json.gz` | Actual P3 at `2e8ae9f`, with the failing gallery turn. |
| `c8-first-furnished.json.gz`, `c8-before-finished-faces.json.gz` | Actual layouts/specifications/furniture at `cd6defc` and `d8e0935`. Those commits already contain several fixes; they are not proof of every uncommitted first draft. |
| `c8-pitch-line-stair.json` | Actual flight geometry at `1276e08`, immediately after the independent pitch-line guard; the same round-8 flight, before later datum migrations. |
| `c8-draft9.json.gz` | Actual scene produced by archived `5533227` source, with that revision's matching layout/specification/furniture frozen alongside it. |
| `c8-round2-render.json.gz` | Actual corrected scene and matching inputs produced by archived `60d753d` source. |
| `c8-measured-lessons.json` | Historical measured figures transcribed from LEARNINGS and existing regressions; provenance distinguishes measurements from complete geometry. |
| `c8-bath-v1-fragment.json` | The recorded 6 square metre bath in a 5 m band with a 1.2 m corridor edge, reconstructed in local coordinates. Absolute coordinates/full original plan were not retained. |
| `c8-route-before.py`, `c8-furnished-route-before.py` | Starting-commit algorithm/AST evidence only; never used as a second production implementation. |
| Existing `bedroom-from-revit.json` | Actual native measured chair/desk/bedside geometry and accessory relationships. |

The two archived render producers read the current luminaire library; a runtime path-separator adapter allowed the old reader to open transferred files. This dependency is disclosed in the frozen records. Only geometry is asserted: these are not historical photometric/exposure reproductions. No packages were installed, secrets read/copied, or shared assets changed.

## All 29 lessons

“Measured fragment” means the numerical relationship is frozen, but full historical object geometry is unavailable. A synthetic assertion about a requirement is not counted as a historical layout proof. The proving tests are in `tests/test_geometry_topology.py`; the existing focused regressions remain in place.

| Lesson | Real case and topology result | Clean and sibling proof / remaining limit |
|---|---|---|
| `l0013-dropping-unknown-chairs` | Actual native FN-CHR footprint remains an obstacle without catalogue access eligibility; access-zone intrusion fires. | Clear zone quiet; footprint and zone translated/renamed together still fire. Existing extract-review tests preserve unknown-type and physical-collision behavior. |
| `l0017-desk-chair-occupies` | Actual native desk/chair accessory relationship exempts parent access only. | Parent quiet; unrelated access and body overlap fire, including renamed obstacle. Complete translated desk/chair intent round-trip remains the existing native regression's responsibility. |
| `l0200-critic-caught-through` | Measured bath/corridor-edge reconstruction fires `unbuilt-link` and `room-reachability`. | 1.8 m control quiet; translated/renamed fragment fires. Original complete generator-v1 failing plan is unavailable; **fragment coverage only**. |
| `l0209-guards` | Record bundles circulation allowance, area-match and unsupported upper floor. | **Open:** these are not all topology queries. The original upper overhang geometry was not retained; generator history already includes minimum-run fixes. Existing `test_concept` guards are retained, not duplicated or claimed closed. |
| `l0307-villa-concept-round` | Actual round-2 straight stair has zero end declarations; declaring the foot on its actual street edge also finds zero circulation neighbours. | D1/D2/D3 stairs quiet; full room geometry translated/renamed and foot-end case still fire. |
| `l0310-critic-treated-stair` | Same actual round-2 stair is rejected independently of its intended room graph. | Same clean/sibling proof; no whole-room reachability shortcut substitutes for ends. |
| `l0319-check-stair-by` | Both-end declaration/ownership query catches the round-2 geometry. | Clean/sibling proof present. **Client-sketch direction intent remains open**; topology does not infer approval from a plan. |
| `l0504-headroom-measured-from` | Frozen pitch-line flight and opening ending at 8.537 m yield approximately 1.824 m versus cited 2.000 m. | Current opening quiet; actual limiting pitch sample/soffit translated in all three axes retains the same failure. |
| `l0512-way-from-stair` | Actual archived P3 geometry gives 0.59 m by the existing raster versus cited 0.90 m hall width. The review's reported nominal 0.69 m is separately retained. | Current design gives 0.91 m; entire floor/void geometry translated together still fails. P1 is not substituted for P3. |
| `l0518-r9-follow-ups` | Record combines duplicated corner opening ownership, `part_of` alcove glazing and cinema ceiling coverage. | **Open:** original failing opening meshes and cinema boundary are not frozen in the available records. Existing opening-owner/ceiling controls remain; no fabricated topology proof. |
| `l0528-20-mm-grid` | Checker false positive: shared floor edges were lost by strict raster inequalities. | Original corrected half-open raster preserved by frozen AST comparison and furnishing regressions. **No recovered complete pre-fix arithmetic input**; topology must stay quiet on actual continuous floor, not report a design defect. |
| `l0531-body-rounded-down` | Frozen measured 0.909 m gap fails against the held 0.914 m card without grid rounding. | 0.914 m quiet; renamed reference same result. **Measurement-only**: original pair positions were not retained. |
| `l0534-corner-not-side` | Record gives a final-centimetre grazing condition, not the complete body path. | `_middle` node logic is preserved unchanged and existing route negatives run. **Open historical geometry**; no invented bed/path coordinates. |
| `l0536-seating-card-assumed` | Held traffic card is 1.118 m. Recorded 0.813 m was the wrong requirement, not an achieved aisle. | Requirement-selection test and 1.31 m measured clean control; renamed reference test. **Open full first-draft geometry**; the 0.813 m assertion is explicitly not a historical achieved measurement. |
| `l0542-stair-flight-counted` | Existing real console-at-foot regression frozen by literal placement values fires stair-access route failure. | Actual current basement quiet; renamed console fires. Entire unchanged raster retains flight/void exclusion and meaningful node overlap. Original 9 mm sliver is measurement-only. |
| `l0551-furniture-placed-against` | 50–200 mm historical burial range retained; named finished-host query and real rail sibling prove signed/finite penetration behavior. | Current D1 named-host penetration quiet. **Open original furniture body coordinates**; committed furniture snapshots already use corrected faces. |
| `l0557-door-can-run` | Saved contemporary walls plus recorded x=22.10 m and width=0.90 m reproduce exactly 0.153 m loss: achieved 0.747 m versus authored 0.900 m. | Current clean; renamed door still fires. Current-design regression at that centre separately retains its 50 mm loss rather than pretending it is the historical 153 mm. |
| `l0570-pocket-door-gave` | Actual parents' pocket door retains two approach nodes and no swing envelope; frozen chest regression blocks its route. | Actual current GF quiet; renamed chest still blocks the approach. |
| `l0576-square-body-failed` | Original square-body rejection was a checker error; current disc-route design stays quiet. | Existing 0.24 m hanging-rail shift fires, including renamed rail. **Original wrong-square implementation not recovered**; unchanged disc arithmetic and real route regressions retained. |
| `l0591-run-s-modules` | Recorded 40 mm module overrun reproduced on the authored run; measured sum versus run width reported. | Current modules quiet; renamed 4 mm sibling fires at the existing 1 mm tolerance. **Historical overrun magnitude frozen; original module list unavailable.** |
| `l0692-open-item-not` | Recorded tread/wall gaps 50–200 mm retained. | **Needs structural source/intent:** a wall gap alone does not prove unsupported tread; stringer/bearing/cantilever capacity is consultant scope. Existing geometry/support controls retained. No fabricated zero-gap requirement. |
| `l0695-floating-objects-found` | Actual archived draft-9 markers/fittings lack grounded support paths; query reports zero versus one grounded path. | Corrected round-2 scene quiet; all faces/props translated and all instance names replaced retain the same failing set. Actual current D1 also quiet. |
| `l0713-parents-entrance-closed` | Actual frozen slats and pendants block parents' entry and dressing passage using their matching saved openings. | Corrected saved scene and current D1 quiet; renamed details/fixtures fire. Existing semantic role prefixes are retained because the legacy doorless policy uses them. |
| `l0720-codex-fix-cut` | Saved contemporary wall geometry plus x=22.05 m, width=0.80 m reproduce exactly 53 mm loss. | Current opening quiet; renamed doorway query still fires. No wall/reveal correction applied. |
| `l0741-plants-placed-without` | Plant positions exist in archived scenes, but their relationship to the original vanity chair/new window changed during the uncommitted review. | **Open:** no trustworthy matching failing chair/window geometry or sourced plant-specific use margin. Existing indoor-plant/support controls run; no invented “place one here” rule. |
| `l0820-prop-extent-guard` | Frozen real searsia at (13.25, -21.65, -2.62 m), scale 0.7 enters the dirty kitchen by measured full extent, not trunk position. | Current landscape quiet; renamed shrub fires; clear outside-room control quiet. Level-B ownership is reused. |
| `l0834-landscape-change-must` | Real frozen teak-sofa footprint intersects the living-south walking route. | Current landscape quiet; footprint and route translated/renamed together fire. **Broad lesson remains partial:** roof rail, spacing and swing assumptions stay in their existing dedicated controls; route proof does not close every garden-change obligation. |
| `l0849-dirty-kitchen-duct` | Frozen fan x=13.300 m versus chimney x=13.827 m and half-width 0.115 m gives signed containment clearance -0.412 m versus required 0. | Current fan measured against its actual hob-derived chimney quiet; renamed fixed-reference sibling fails. **Measurement/footprint proof only**, not original duct mesh or service engineering. |
| `l0856-stair-s-wall` | Exact original rail polygon projects 0.140 m behind the finite plaster face. | Current D1 quiet; polygon/reference translated together still report -0.140 m; measured moved-front control quiet. |

## Current design and figures still needed

`docs/c8-current-findings.json` is the generated current-D1 review output: 512 hosts, 26 openings, 902 obstacles, 646 explicit support records and 31 route/approach records. Zero failures in opening-host collision, stair access, module fill, furnishing routes on both storeys, named-host penetration, inferred support, landscape walking routes and occupied-room prop intrusion. Additional current hall measurement: **0.91 m achieved / 0.90 m required**, card `ukadm-hall-min-m42`.

Eight window movement envelopes are absent. They are `needs-source`, not passes. Motion sweeps/hinge/slide specifications require measured supplier or native data. Door envelopes retain the existing conservative policy and do not certify actual swept leaf meshes.

Other unresolved figures/authority: original 0.25 m swing allowance; 0.60 m bench knee allowance; 0.12 m rail strip; stair 0.085 m handrail and 0.030 m plate projections; plant/window/vanity use margins; tread bearing/support capacity and service-duct engineering. These are recorded assumptions/project geometry or missing engineering, not published architectural thresholds. The model does not silently promote them to standards. The 0.750 m private dressing route remains the existing pending project waiver, distinguished from AD M bedroom applicability. No waiver was granted here.

Signed zero penetration, occupied area zero, one opening/contact/path and original numerical comparison tolerances are geometric/identity policies, explicitly named in findings, not new ergonomic standards. Applicable numeric cards are reused with their edition, locator and conditions.

## Refactor audit and validation

The required audit was run against the starting commit without an allowlist: **133 removals reported, exit 1**. Each is individually recorded with source path/scope/name and justification in `docs/c8-refactor-audit.json`. No removal was ignored.

The audit was then rerun with `--allow docs/c8-refactor-allow.json`: **exit 0**. Groups: stair-end loop moved to topology; landscape walking collision moved to topology; overlap primitive forwarded; crossing-wall door loop moved with unchanged arithmetic/messages; original furnished-route body/nested `touching` function moved unchanged to `_route_problems`. AST equality is a regression, not merely a prose justification. Additive saved-specification parameters remove no old behavior. The allowlist is task-specific and not installed as a repository-wide default.

Validation uses the supplied interpreter, `PYTHONPATH=src`, `NO_COLOR=1` and process exit status. Initial focused batch: 62 tests, exit 0. Broader final focused results and final portable results are recorded below after completion. The lead retains full-suite execution. Native models were not authored, so the native bedroom runner was not invoked.

## Lessons to register

Registration remains the registry agent's responsibility. Functions below are in `archpipe.geometry_topology`; methods are on `GeometryTopology`. Register proof scope accurately; **pending** entries are not closure claims.

- `l0013-dropping-unknown-chairs` → `GeometryTopology.access_zone_findings` (native obstacle retention).
- `l0017-desk-chair-occupies` → `GeometryTopology.access_zone_findings`, `GeometryTopology.object_overlaps` (parent-only exemption).
- `l0200-critic-caught-through` → `GeometryTopology.room_connectivity` (**fragment scope**).
- `l0209-guards` → **pending**, retain existing `concept.critic` controls.
- `l0307-villa-concept-round` → `stair_access_findings`.
- `l0310-critic-treated-stair` → `stair_access_findings`.
- `l0319-check-stair-by` → `stair_access_findings` (**ends only; sketch intent pending**).
- `l0504-headroom-measured-from` → `pitch_headroom_findings`.
- `l0512-way-from-stair` → `GeometryTopology.hall_route_clearance`.
- `l0518-r9-follow-ups` → **pending**, retain existing owner/ceiling controls.
- `l0528-20-mm-grid` → `GeometryTopology.furnished_routes` (**existing corrected raster/AST preservation; original checker reproduction pending**).
- `l0531-body-rounded-down` → `GeometryTopology.clearance_from_fixed_reference`, `GeometryTopology.furnished_routes` (**measurement scope**).
- `l0534-corner-not-side` → **pending historical proof**, existing `_route_problems` middle-node control retained.
- `l0536-seating-card-assumed` → `GeometryTopology.clearance_from_fixed_reference` (**requirement-selection scope; historical geometry pending**).
- `l0542-stair-flight-counted` → `GeometryTopology.furnished_routes` (real console regression; sliver fragment limitation).
- `l0551-furniture-placed-against` → `GeometryTopology.object_penetrating_host` (**class/sibling proof; original furniture coordinates pending**).
- `l0557-door-can-run` → `GeometryTopology.opening_host_collisions`.
- `l0570-pocket-door-gave` → `GeometryTopology.furnished_routes`.
- `l0576-square-body-failed` → `GeometryTopology.furnished_routes` (**disc preservation and aisle regression; old square implementation pending**).
- `l0591-run-s-modules` → `GeometryTopology.module_run_overflow` (**measured-overrun scope**).
- `l0692-open-item-not` → **pending structural intent/source**, no zero-gap guard.
- `l0695-floating-objects-found` → `support_findings`.
- `l0713-parents-entrance-closed` → `GeometryTopology.passage_obstructions`.
- `l0720-codex-fix-cut` → `GeometryTopology.opening_host_collisions`.
- `l0741-plants-placed-without` → **pending historical relationship/source**.
- `l0820-prop-extent-guard` → `GeometryTopology.occupied_room_intrusions`.
- `l0834-landscape-change-must` → `landscape_route_findings` (**route scope; other garden obligations retained**).
- `l0849-dirty-kitchen-duct` → `GeometryTopology.clearance_from_fixed_reference` (**fixed-footprint scope**).
- `l0856-stair-s-wall` → `GeometryTopology.object_penetrating_host`.
