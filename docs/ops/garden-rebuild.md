# Garden rebuild procedure — G1/G2 follow-up, 2026-10-06

Read `docs/garden-g2-report.md` and the historical G1 checkpoint. The canonical villa-render skill is read-only in this workstation mount; this tracked addendum supplies the changed procedure for the lead to reconcile with that skill.

1. Use `knowledge/garden-palette.json` as the sole species, dimensions, spacing, botanical source and placement-assumption authority. Do not revive generated/shared palettes or local botanical constants.
2. Check full canopy bounds against property/building faces separately from walking occupancy. Every prop uses actual asset triangles from route ground to 2.0 m; procedural plants use actual faces. Missing overlapping asset geometry fails closed. Then check actual door passage volumes as well as the narrower garden paths before the first preview.
3. Derive layer scope from actual bed data, and use `planting_layer`, not the renderer's lighting `layer` field. Keep same-species drifts to 3–5 and spacing to the authoritative record. Report all sun-hour samples and the enclosure-screen limitations.
4. Author changed trellises on finite C4 boundary faces. Retire obsolete approval rows as data, preserving their coordinates and frozen failure proofs. Hash changed authority data in scene provenance.
5. Procedural plant geometry uses metres explicitly. Do not call millimetre furniture helpers with metre dimensions. Transform fresh coordinates, and triangulate swept/curved faces at construction time. Check closed outward geometry and the render contract on an isolated real clump before whole-scene diagnosis.
6. Resolve imported props as subjects from measured geometry and the actual imported Blender meshes, without marker aliases. Keep frozen removed-assembly camera proofs separate from current content. Reframe cameras only; do not change design for a view.
7. A low branch in the walking volume remains a physical blocker. Report it and retain refusal at `build()`. Neither a tree exemption nor a floating tree is a clean placement. Height-band mutation proofs are diagnostic inputs only.
8. A no-render task may hand over a measured candidate. Diagnostic builds that expose it for tests must not export or render it, must retain conflict notes and must never be reported as authoritative acceptance. Lead previews and photographic review remain required before integration.

Renderer consumers also need a producer-to-consumer wiring proof when their arguments change. `test_garden_render_subjects` executes the actual QA function and actual render-call expression with camera projection/context stubs; it preserves the real wrong-import-result-name failure. Label that as a consumer test, not evidence of a Blender render.

D4 placement procedure (2026-10-06): a lead-authorised route remedy may move the tree/pit for the brief's clear door route; this does not authorise camera-driven design moves. Run `PYTHONPATH=src python scripts/garden_tree_position.py` to reproduce the continuous whole-lawn minimum with actual triangle height-band clipping. The horizontal centre-line band, model canopy and mature-circle bounds are intersected before subtracting every route/stone forbidden translation region. Record the resulting centre and numerical separation in the sole palette. Turf and pit are rebuilt around that recorded centre; never shift an exported mesh by hand. Retain the frozen centred low-branch reproduction. Confirm every authoritative landscape guard, `unsupported` and `blocked_openings`, then export and check plan framing. Independent asset-placement metadata must be refreshed when scale changes; run `tests.test_asset_intake` and portable verification against the authoritative scene, because a blocked upstream build can hide downstream drift. D4 changes position only; D1 supplies the unchanged scale.

The west overview camera is on the sister side of the shared axis, in the modelled lower front-yard strip without a dividing fence. Its caption must state that vantage. It uses 24 mm, level aim and 1.35 m standing eye height with vertical lens shift; no ground, plant, furniture or route moved for the camera. Lead draft and photographic sightline review remain required; the plan/projection preview is numerical evidence only.

G3 top-garden procedure (2026-10-06): build slim hollow steel troughs from a
single named assumed coating parameter, at the measured deck datum. Join root
seating to actual recessed soil and benches to real paving slabs. Review the
built outer envelope, including folded rims and trailing shoots, against the
deck/roof and retained rail strip; declared schedule rectangles alone cannot
prove clearance. Keep trough drifts to 3–5 of one species. Check study and
connecting deck paths with D2 floor-to-2 m occupancy; check the street-gate
continuation over the unchanged driveway by subtracting its measured sloping
floor from actual triangles, segment by segment. Do not construct flat paving
over the ramp. Ixora in the two top pots requires both the checked flowering
quote and measured full-sun samples; otherwise use the top palette. Ursinia
needs checked top placement and light evidence before placement. Regenerate
tracked asset geometry for new imports; do not read the library during build.

Solid tapered plant blades must retain nonzero tip thickness. Run both physical
part and render-contract checks on the isolated new botanical mesh, then the
whole scene. `scripts/garden_top_plan.py` supplies a reproducible measured plan
preview without Blender. Record eight/nine sun samples individually, not a
uniform nine-hour assertion; the enclosure screen is not a detailed shadow or
Egypt performance study. Never infer photographic approval from this schematic
or passing tests: the lead reviews close-up draft troughs, foliage and benches
before integration. Supplier weathering and loaded-weight data, nursery root
behaviour and waterproofing, dark-bronze client colour confirmation, and the
unplaced potted shade tree remain explicit open items.

G3 finish-consumer follow-up: add a named authored material and its independent
`tests/test_render_standard.py::ALLOWED_MATERIALS` registration together.
Preserve the explicit finish-list refusal for unknown appearances. An isolated
mesh contract accepting a declared material does not prove its whole-scene
finish registration; execute that consumer before handing off a render scene.

G3 camera-neighbour follow-up: run the whole exterior camera set immediately
after the first fixed layout, before the long acceptance batch. Review adjacent
views as well as the two named top views. Proximity checks include actual
procedural top foliage and containers as well as imported props. If a clear
standing point cannot hold the full soil-bed extent, retain the design, declare
honest actual planting subjects, and caption the omitted extent and companion
view. Final-only v27 also needs its own lead draft after camera correction.

G4 north-garden procedure (2026-10-06): client naming follows the street:
model −x is north, +y east, +x south, −y west. Existing identifiers remain
unchanged; true bearing is solar input only. The legacy west court is the
client's north garden. Use its tracked deep-shade palette, retaining PARTIAL
light applicability for grape ivy/mondo and UNVERIFIED Cairo winter/nursery
performance. Under the ground-floor balcony, use Aspidistra or gravel only.
Do not revive the withdrawn top-garden removal instruction.

Build soil at the court datum, with slim edging, and retire the old paving
finish at each actual bed boundary through `reveal_ground_soil`. An isolated
soil preview cannot prove it remains visible over the architectural backing:
run `soil_visibility_findings` and review a contextual neutral preview before
handoff. Keep soil elevation fixed when correcting a competing finish. No
slab excavation, soil depth, root barrier, waterproofing or drainage is
engineered by this render-finish operation; the nursery/engineer owns those.

Use continuous Fatsia laminae, independent Rhapis fan nodes and truncate
segments, and explicitly connected grape-ivy petioles. Run the shared form
checks on the isolated elements and the complete scene; retained/imported
plants do not establish a new species identity. New external plants still
require the complete licence, author, bounds, unit, facing and route-record
intake. Authored procedural appearances need no invented external licence.
Preview/review each new species, stone, bed and climber; neutral diagnostics
are not presentation lighting approval.

Check the actual door-passage width in the landscape candidate as well as the
narrower path. Include ground procedural foliage and all beds in swing/camera
clearance. Cameras move; the garden stays fixed. If the full bed cannot be
framed from a clear open-sky position, declare honest visible subjects and a
through-lounge companion. Report the actual overhead union separately from
the ground-floor balcony; a client naming correction is not authority to
silently remove modelled architecture.
Check actual bed-corner sightlines as well as projected bounds. v38's near
corner is screened by the existing lounge frame and its caption discloses
that screen. Related views receive one shared authored-appearance,
photographic-likeness and procurement-limit note instead of separate copies.
For caption-only changes, compare decoded before/after exported meshes,
props, lights and cameras exactly; do not compare JSON lists directly with
the builder's tuple-bearing in-memory structures or round geometry values.
Measure climber coverage as projected leaf-area union and state its
denominator: training-envelope coverage and whole timber-frame coverage are
different quantities. G4's 33.36% and 20.51% respectively must remain distinct.

Resolve output paths before reporting a shared-data write. `build` no longer
generates generic photometry into global OUT; `write(path)` creates generic
files beside the explicit export. Existing verified catalogue binding remains
its separate workflow. In this worktree, `out/villa/render-d1` resolves locally,
while `out/villa/round3` and `assets/user` resolve to protected shared data.
Keep every G4 export, preview and log under `out/garden-g4`. Never infer an
actual mutation from similar folder names or a potentially writing branch.
