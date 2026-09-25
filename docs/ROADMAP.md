# Villa system roadmap and example acceptance

Updated 2026-09-23. The bedroom is a capability example, not the villa
design and not approval to pass a real design gate. Read the full
[product requirements](PRD.md) and [eight-stage method](method/villa-design-method.md).

## Full system

| Stage | Intended work | Current evidence and remaining work |
|---|---|---|
| 0 Intent | Household interview, lifestyle, budget, taste | Brief schema and gates exist; real interview remains open |
| 1 Ground | Real plot, statutory envelope, climate, orientation | Site schema and solar checks exist; placeholder site is not a real survey |
| 2 Fit | Area feasibility and cheapest remedies | Engine verified; real brief/site approval still required |
| 3 Order | Zoning, adjacency, privacy, circulation, massing | Stage-aware criticism exists; concept authoring is not complete |
| 4 Rooms | Dimensions, openings, furniture, access | Revit round-trip and cited geometry rules exercised on the bedroom; multi-room coordination remains |
| 5 Systems | Layered lighting and technical coordination | Analytical light calculations and calibrated Cycles probes exist; Radiance, full services and jurisdiction packs remain |
| 6 Substance | Materials, details, construction | Painted finishes read back and used for render hue; full assemblies, manufacturer assets and measured optical properties remain |
| 7 Proof | Native drawings, coordinated model, review, rendering | Bedroom native views/sheets, synthetic markup and rendering exercise the chain; this is not a construction package |

The thirteen backward loops and four controls in the method remain the
framework. Agents propose and explain; deterministic tools measure;
the client owns real brief, site, aesthetic choices and design approvals.

## Approved bedroom example

Source: Claude session `02db61f0-bee7-4f37-bea3-95928d4943d2`, plan
`witty-cooking-sundae.md`. The original plan is preserved at
[bedroom-approved-original.md](plans/bedroom-approved-original.md).
Historical statements about Revit versions/content and direct-light
uniformity are superseded by decisions 0009–0011 and measured learnings.

Required sequence:

1. Text specification builds a real Revit 2027 model.
2. Re-extract the saved model; compare dimensions, placement, rotation,
   heights and authored finishes with the input.
3. Run the rule engine on the extract, preserving measured furniture
   dimensions and all obstacles. Declare room versus dwelling scope.
4. Native Revit floor plan, reflected ceiling plan, two interior
   elevations, section and 3D view; place them on sheets and export PDF.
5. Lighting report from actual fixture positions and the explicit
   photometric specification, including failure cases.
6. Rebuild the scene on the rendering workstation; fetch and inspect the
   image, and independently compare direct-light probe values.
7. Synthetic Revit text and revision cloud survive save and extraction.
8. Record passing evidence, limitations, and reusable lessons. A useful
   demonstration does not close the remaining villa milestones.

The drawing requirement is **native Revit views**, not the earlier DXF
drawing path. Revit is the primary review surface for this test; web
markup and in-page chat remain a separate milestone.

Run `.venv/Scripts/python scripts/run_bedroom.py`. Each invocation writes
`out/bedroom-acceptance.json`, initially failed and only marked passed
after every gate completes. Generated artifacts include content hashes.
The report is current execution evidence; this roadmap is intended scope.
See [the validation record](bedroom-validation.md) for tested deliverables,
limitations and the reusable system produced by the example.

## Reusable automation and learning

- [LEARNINGS.md](LEARNINGS.md) is the shared evidence index. Hypotheses,
  observed behavior and limitations are distinguished.
- `.agents/skills/` contains the canonical workflow skills.
- `agents/roles.json` contains narrow agent roles. Generated Claude and
  Codex adapters point to the same workflows. Run
  `scripts/sync_agent_assets.py --check` to detect drift.
- [MCP.md](MCP.md) documents the tested local Model Context Protocol
  server. This is not a claim that Autodesk's private Assistant server
  has been connected; that integration remains a separate investigation.
- [Compute placement](ops/compute-placement.md) records current laptop/
  Ubuntu responsibilities and the next worker infrastructure work.
- Reproduced bugs belong in regression tests. New project decisions
  belong in decision records, not hidden in an agent's memory.

## Next work after the example

Choose the real brief/site when available; until then improve reusable
capabilities: exact family mesh/local footprints, explicit catalogue
bindings, door handing, named lighting targets with verified sources,
multi-room dependencies, edit/read-back commands, and an Autodesk
Assistant adapter if its public extension boundary can be verified.
Do not silently promote this example into a generic villa generator.

## Expert-guided design system — 2026-09-24

The [guidance library](guidance/README.md) adds all eight stage packages, source acquisition manifest, legacy-rule audit, project quality brief, a fictional three-concept villa pilot and the measured-bedroom exercise. Three read-only tools supply stage context, focused evidence and approval-aware review. Public-source qualitative passages are verified; licensed numerical passages remain unresolved. This capability does not close real design gates or complete engineering, budget, comfort studies or final villa drawings.

## Sole-expert capability plan — 2026-09-24

There is no other architect, interior or lighting designer on these
projects, so the AI's judgements must rest on sources that have been
obtained and read. Approved work, in phases:

| Work | Status |
|---|---|
| Purchase list (UK + US practice, tiered, from `knowledge/library.json`) and intake of readable copies | Done: `scripts/sources.py list/intake` |
| Method steps added: façade, climate/thermal window study, landscape, FF&E, cost at every gate, consultant hand-off, acoustics end-check, taste profile, critic calibration | Done: method v1.1 and stage packages |
| Rule verification from the held books (13 audited rules first, then kitchen/bath, lighting, daylight/overheating) | Done: every rule sourced from held books or free standards (AD B/G/K/M, NDSS, IRC via Mitton, NKBA, Time-Saver, Metric Handbook, TM59), values re-read from the originals by tests; all enabled for approval except CIRC-01 (privacy is a brief requirement). New rules FIRE-01, TV-01. See docs/guidance/rule-audit.md |
| Concept design by generate-and-critique: precedent corpus, typology catalogue, constraint-solver variants, calibrated critic, three concepts | Done v1 (ADR-0016): critic calibrated on published graphs, CubiCasa5k (window, reachability) and Swiss Dwellings (area, width, principal double); wet stack shown to be a brief check; per-room TM59 screen per concept; MCP tools. Needs the real brief and plot to run for the villa |
| Thermal/cooling/daylight toolchain (Ladybug Tools + EnergyPlus + Radiance on the workstation, Cairo weather) | Done (ADR-0017): window study with fins; Radiance daylight validated; TM59:2026 criteria (free, held) evaluated per room; concept screen per room |
| Product library for every category (surfaces, sanitary, kitchen, glazing, furniture, plants), broad index + 300–500 verified items | Done for the free sources (ADR-0015): about 3,550 indexed; 469 verified (135 Poly Haven, 90 ambientCG, 91 Fab Megascans, 153 Sketchfab), balanced over furniture, surfaces, fabrics, paints, plants and decor; texture brightness checked against Time-Saver p. 1636 reflectances. Still open: glazing (IGDB, optional token), brand portals for sanitary/kitchen, and BIMobject families via the client's app |
| Schedules, specification book, quantities and relative cost, IFC for consultants | Done: archpipe.deliverables + scripts/handoff.py (schedules CSV, quantities, AECOM relative cost, spec book from the product library, IFC4 verified against the spec to 0.000 mm, MISSING consultant scope). Example: docs/handoff/pilot-bar |

**Consultant scope, missing in-house:** glare (DGP), HVAC design,
electrical, plumbing and drainage, structural design, permits.

**Needs from the client to go further:**
- the Sheikh Zayed brief and plot, to run the concept generator and critic for the real villa;
- a rotated Sketchfab token (the old one appeared in chat);
- optional: BS EN 17037 (EVS edition, about €20–50) and BR 209 (£75), for sunlight-exposure and garden-sun pass marks.

