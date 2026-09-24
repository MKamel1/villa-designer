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
