# Finished-surface mounting

The single thickness authority is `knowledge/finish-build-ups.json`. It records the lead's printed-page checks, assumptions and unknowns separately. A material name is not an assembly. Do not infer board thickness, void clearance or housing depth from an emitter elevation or a difference between ceiling heights.

For each small package, freeze the pre-change geometry by value, derive the near structural face from the structural input, apply the recorded finish, and build the fixing plane through `archpipe.concept.mounting`. Export the host and per-component mounting contract. A wall-hung component's projection is an authored design parameter; it is not a tolerance or an invented universal standoff. Child parts need measured parent support rather than an arbitrary host plane.

`check_mesh` independently measures the vertices along the host's outward normal. The 1 mm comparison tolerance accommodates millimetre coordinate rounding and export arithmetic. It is an assumed model comparison tolerance, not a construction workmanship allowance. Missing hosts, missing recessed housing/void data, excess housing depth, stale finished-face records and signed face discrepancies fail. `scene_findings` covers every phase-1 inventory kind and furniture mesh; `scripts/verify.py` calls it unconditionally. A partial migration therefore leaves verification red.

For the first C4 package, run `scripts/checkpoint_mounting.py`. It writes a candidate scene and diagnostic section under `out/c4-phase2a`; it does not replace `out/villa/render-d1/scene.json`. The movement CSV lists minimum x/y/z and maximum x/y/z bounds in metres, and the largest corresponding-vertex displacement in millimetres. Fixing-end resizing counts as movement. Every movement over 5 mm remains pending lead approval. A face normal indicates the side occupied by the finish; x runs from street to garden, y toward plot east, and z upward.

A plane contract alone does not prove finite host coverage or fixing capacity. `host_coverage_findings` also checks fixing-plane vertices and their centre against actual exported finished host polygons. It reports nine first-package contacts at the core return and floor/wall edges. Review the actual structural face over the fitting's full footprint, especially at changes of wall thickness and at slab/core returns. The first package preserves the existing structural shell; its partition/party-wall overlap is a coordination question for the lead, not permission to add or move structural walls. Native Revit coordination and a photoreal first-fix preview remain separate from the diagnostic section and unit-test result.

Resume only after the first-fix checkpoint review required by the defect-learning and villa-render skills. Next packages are bathroom fittings, wall lights, ceiling fittings, then television/shelves/joinery/trellis/climbers. Read source status and existing heights before each package; do not repair the design to make a numeric guard quiet. Register controls and proving tests in `knowledge/mounting-guards.json`. Render and independently re-measure lighting after approved fixture moves.

When retiring a duplicate camera, select retained review and regression views by identifier rather than their position in the old list. Search ordinal slices as well as the retired name. Retain the scene-content and exposure assertions for every intended surviving view; do not change design cameras to satisfy a list-count check.

## C4 resume, packages a/b/c (2026-10-05)

Lead decisions 1-4 approve the first stair schedule and identify the return,
continuous stacked-wall finish and basement floor bearing. Stringers crossing
the return end use a stepped bearing, not an extended structural wall. The
continuous finish rule bridges only the measured slab-edge gap between
coplanar vertical walls with identical finish records; offsets, different
finishes and gaps greater than the slab depth do not merge.

Use `scripts/checkpoint_mounting_bc.py` for the resumed checkpoint. It exports
the working scene, a separate proposal, movement schedules and measured
diagnostic previews under `out/c4-phase2bc`. Do not use the historical first
candidate as current evidence. The original package-a outputs remain intact.
The final stair schedule measures changes in bounds (minimum then maximum
x/y/z in metres); stringer 06 now has stepped topology, so it is not a
corresponding-vertex comparison. The b/c schedules use maximum corresponding
vertex displacement, in millimetres, including shortened fixing ends.

`fitting_mounting` consumes actual exported room wall polygons and generated
joinery faces; all coplanar triangles of a selected source mesh contribute
finite coverage. Each assembly root names its fixing plane; child projections
are relative to that plane. Suspended rain-head parts bind to the existing
finished ceiling datum without asserting a board thickness or clear void.
Marble uses the ASSUMED 20 mm slab plus the ASSUMED selected 3 mm bed within
the VERIFIED 3-6 mm thinset range. Tiled hosts use the porcelain tile record.

Declare every required host before testing. Apply a move only when its
maximum vertex displacement is at most 5 mm; keep larger moves in the
proposal and keep their working geometry unchanged. Finish-face additions
are movements too. Newly declared host polygons are camera-hidden diagnostic
records, not added visible cladding or proof of integration. Pending finish
polygons retain the source plane in the working scene; the proposal carries
the offset face. Exclude these diagnostic meshes from a future presentation
or probe export when replacing the visible finish; camera visibility alone
does not suppress other ray interactions. Missing finite coverage and face
errors remain failures.

Never choose another room's wall to hide a fitting crossing its intended
wall's end, or flatten a handset/body against a plane to obtain a pass. Only
fixing ends may be shortened; body and emitter geometry is retained. A real
handset collision or wall-edge overrun requires a separate design decision.
Ceiling fittings and TV/shelves/joinery/trellis remain for the next package.

## Approved b/c and ceiling checkpoint (2026-10-05)

Use `scripts/checkpoint_mounting_d.py`. Preserve the historical b/c schedules
and checkpoint; current candidate evidence goes to `out/c4-phase2d`.
`knowledge/c4-bc-approvals.json` freezes the 58 approved identifiers, hosts and
bounds. Geometry drift requires a new decision; approval does not apply to
different bounds. The separate handset correction is another rigid 23 mm
after the schedule's 23 mm. Hose connections follow the corrected handset
and existing riser outlet; generate a hanging spatial curve with 6 mm radius
and an additional assumed 2 mm design clearance. Test connection identity,
all centreline points and generated tube vertices. The sconce's conservative
120 mm fixing envelope moves 99 mm along its existing wall, leaving an assumed
5 mm edge margin; its product back plate is not independently specified.

After sanitary/fitting/finish moves, run `mounting_clearances.review` against
actual moved candidate meshes. Preserve larger authored envelopes, include
projecting fittings and finished wall strips, and rerun all room fronts,
basin widths, door swing squares and routes. Report achieved versus required
for every row. A 700 mm basin approach is wider than a compact basin body;
do not silently use its width. A route obstacle is not a new destination.
Missing drain service/installation or splash-distance criteria stay missing.
Containment and non-intersection are separate from service clearance.

Lead follow-through 2026-10-05: drain installation is a CONSTRUCTION
REQUIREMENT, with `manufacturer installation data required` and no numeric
pass. Wet-floor boundaries must be authored from the finished wall, and
clearances must read the actual generated wet-floor mesh. Translate the
boundary and its drain together; retain the wall fittings. Compute plan
separations from rectangles; a diagonal distance does not decrease by the
amount of a single-axis translation.

Check the whole WC access zone as well as basin frontage: AD M Diagram 2.5
has 350 mm and 1000 mm centreline sides, and only 300 mm permitted rear-wall
washbasin encroachment. Before a same-wall slide, intersect the continuous
centre-position intervals from the side wall, shower approach and basin
strip, testing both possible fixture orders. A necessary-constraint
infeasibility proof is sufficient to leave the layout unchanged; a feasible
interval still needs full zones, door and route checks before application.

Package d selects actual finite downward ceiling polygons, including sloping
soffits. Compute the assembly fixing coordinate using all components of
the measured normal. Batten brackets cut only their upper fixing ends to
their local soffit; housing levels remain retained. Trim geometry and emitter
height are not housing-depth evidence. Recess roots retain missing housing
and missing clear void and fail unresolved; never invent a ceiling void.
Apply at most 5 mm automatically; keep larger moves in the separate proposal.
Nook-top downlights mount in joinery and remain for package e.

The six frozen cinema moves now have explicit authority in
`knowledge/c4-d-lead-approvals.json`; approval still checks hosts and bounds.
Stored product body heights can establish housing requirements; trim and
emitter dimensions cannot. `ceiling_requirements.py` reads the selected
manufacturer files and writes `docs/requirements/ceiling-void.md`. The clear
void is the zone's maximum recorded body height plus a separately labelled
installation clearance. Missing manufacturer clearance may use an explicit
lead assumption with its reason, subject to manufacturer confirmation.
Missing housing data stays UNRESOLVED. Host void status must be `requirement`,
never an as-built assertion. A recessed trim measures its fixing plane;
the separate body-depth contract checks required void capacity plus the
allowance. Do not stretch a decorative trim into a fictitious housing.
Current lead evidence goes to `out/c4-phase2d-lead`; historical d evidence and
`docs/c4-phase2d-checkpoint.md` remain intact. Package (e) is the next job.

Keep diagnostic candidate exports separate from the presentation scene and
native extracts. Every camera-hidden diagnostic mesh still carries the full
scene schema, including its label. Focused mounting regression must validate
`villa_render_contract.validate_scene` with the existing complete view records before the full suite. A zero-view diagnostic is intentionally not a renderable scene; do not relax the contract to hide that requirement. Inspect the
diagnostic images at the first fix. Photoreal
neutral-light previews, native coordination and independent lighting probes
remain required before presentation integration. The ceiling, drain and
clearance findings keep the gate closed even when the regression suite passes.

## C4 package (e), bounded support checkpoint

Use `scripts/checkpoint_mounting_e.py`; evidence goes to `out/c4-phase2e`. Keep
all earlier checkpoints and approvals. Missing floor stacks use the actual
modeled finished level, never an assumed oak/underlay thickness. A floor-bearing
assembly has one independent root; every generated child declares its projection
relative to that root. Root contact is checked against actual finite floor
patches. Adjacent coplanar floor/ceiling patches are copied from real source
faces, never extended across a gap. Place full-span shelving from exact floor
edges, preserving width instead of rounding a centre.

Recessed nook fittings bind to the actual joinery-top underside and preserve
the separately sourced construction void requirement. Wall markers retain
missing housing/installation data as construction requirements; a declared
wall host is not an installation pass. Trellises name actual boundary source
identifiers: distance to a wall is a pending design correction, not a fabricated
standoff. Bracket envelopes must intersect their supported rail; anchor
capacity remains unverified. Imported furniture, cloth, props and emitter
positions follow applied assembly movements. Re-measure lighting before integration.

The explicit same-wall WC-slide authority is separate from the 5 mm mounting
limit. Generate exact side-zone candidate events, then rerun every carded
front/side, wet-zone, door and route check before applying. Preserve the family
bath geometry and client options. Mounting movements above 5 mm go to
`movements-over-5mm.csv` and retain old working geometry. Do not commit or
replace presentation/native geometry at this checkpoint.

On a time-limited managed Windows job, run only named modules using
`python scripts/run_focused_tests.py test_mounting_scene test_support_mounting`
and `verify.py` once at the end. The focused runner requires explicit modules,
uses the existing accessible temporary-directory adapter and cannot discover
the full suite. The lead runs the full suite.

## C4 retained package-e lead review
Use `scripts/checkpoint_mounting_f.py`; preserve package-e artifacts and checkpoints.
Authority is frozen in `knowledge/c4-e-lead-approvals.json`: 43 approved rows apply;
two approved inward grille finish-face movements are obsolete and retired,
replaced by modeled exterior-face datums. Revised landscape/grille proposals
remain unapproved, even if their movement is smaller than the rejected proposal.
Declare yard boundary hosts from `villa_landscape.YARD` / `villa_env`; modeled
fence faces keep their measured thickness. For an edge with no modeled wall
solid, state that the polygon edge is the inner structural face and wall
construction is unverified. Finish build-up remains unverified: modeled
exterior paint/render face equals the finished datum. Diagnostics must state
that an unmodeled wall is a construction requirement, never an as-built wall.
Require the entire conservative fixing envelope on one finite convex source
face and at most 300 mm travel from the authored fixing plane (lead-selected
design search limit, not a standard). Refuse concave/incomplete or distant
faces before generating a movement. Never bridge a gap, notch or opening.
External grilles need an inward adjacent authored room and no outward room,
not a hard-coded normal. Apply the same coverage and distance limits.
Room/material labels can split one actual wall: supporting patches must be
copied from actual coplanar source faces with provenance; never extend them.
Approved translation is not approval to hide a remaining finite support
failure. Report working and proposed findings separately, with proposed
movements over 5 mm listed for approval. Focused modules plus `verify.py` only;
the lead runs the full suite. No presentation/native integration or commit.

Run this checkout with `.venv/Scripts/python.exe`: the default system Python
lacks Shapely. An import failure is a failed start, not a review finding.
Approved appliance roots carry all attached parts, and approved emitter
geometry carries the corresponding light record with unchanged photometry.
Export these carried translations separately and prove rigid vertex and
emitter displacement. Preserve visible geometry and construction limitations;
independent lighting probes remain required before integration. Diagnostic
preview limits use the complete before/after bounds, never fixed tangent
widths that crop the support relationship.
Before approving an appliance fixing plane, inspect all its attached parts,
including the lowest tray. Associated parts are checked against the root?s
actual finished support half-space. A frozen approved translation that
introduces child penetration remains applied and reported; do not deform the
child or silently revise the approved pose to hide the collision.

## Final C4 authority and attached assembly construction
The final lead decisions supersede the pending landscape/grille status above.
Keep package-f evidence intact. Run `scripts/checkpoint_mounting_final.py`;
`knowledge/c4-final-approvals.json` freezes all 14 approved revised rows.
The builder declares attached coffee/hood children through `attached_assembly.bind`;
all parent moves use `attached_assembly.translate`, including automatic small
corrections in `fitting_mounting.package` and historical approval
application. Complete lowest-part support defines coffee seating, with retained
part projections; never seat a body independently of a lower tray. `scene_findings`
checks rigid relative positions unconditionally. Test parent-only moves, both real
coffee machines, the hood sibling and renamed/translated assemblies.
Headboard width fits a full-height finite wall patch with the lead's 10 mm margin,
symmetrically about the unchanged bed centreline where possible. Preserve bed
geometry, cameras and family-bath layout. New explicit authority allows corrected
coffee seating; earlier frozen approvals remain historical evidence.
Focused modules and project-interpreter `verify.py` only; the lead runs the full
suite and renders the listed diagnostic views. Inspect local before/after previews
before checkpoint delivery; no native or presentation integration is implied.

For the Linux lane-A continuation, use
`/home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python` with `PYTHONPATH=src`
and `NO_COLOR=1`; the Windows interpreter paths above are historical. Set
`MPLCONFIGDIR` to a writable task directory. Transferred luminaire indexes
must be consumed through the portable library row readers; never change the
shared library to repair separators. When ignored historical `out` artifacts
are absent, reconstruct candidate baselines through the builder with subsequent
approval steps disabled, and label their provenance as reconstructed on this
host. Such baselines provide geometry comparisons, not historical execution
evidence. Retain the checkpoint documents, failed-start logs and frozen fixtures.
Use the existing `scripts/verify.py --portable` mode with focused
`test_rfa_portable` on Ubuntu; record the Windows installed-family corpus as
skipped coverage. Plain verification still requires that unavailable native
corpus. The lead retains native integration checks and the full suite.

## C4 plant support datum follow-through

Package (e) seats furniture and plants on the modeled floor finish 2 mm above
the nominal room level. Indoor plants name their floor or furniture support;
`support_mounting.plant_support_face` measures its finite upward contact face.
Record a plant contract for that face, never a furniture floor-root contract.
After migration, pass the scene to `indoor_plant_violations`; without it, migrated
props fail closed. `scene_findings` independently checks actual support geometry,
plant base and recorded datum with the unchanged 1 mm comparison tolerance.
Moved or removed supports and stale records remain failures.
