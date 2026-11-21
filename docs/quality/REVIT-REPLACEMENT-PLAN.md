# Revit replacement plan (DRAFT — awaiting RV1 inventory and client approval)

Goal (client, 2026-11-21): go Revit-free **without losing any functionality or capability**,
including capabilities we relied on implicitly. Nothing is built further until this plan is approved.

Method: two independent inventories, reconciled.
1. **Generic** (this draft): what Revit gives an architectural practice, by capability family.
2. **Project-specific** (lane RV1): every place this pipeline actually used Revit, explicitly or
   implicitly, with the defects it caught (knowledge/parity/revit-uses.json).
Any capability that appears in only one list is a gap to resolve. Each row gets: replacement, owner
lane, equivalence proof, risk, and a decision (replace now / replace later / not needed, with reason).

## Generic capability families (to reconcile with RV1)

| # | Family | Revit capability | Used here? (confirm with RV1) | Candidate replacement |
|---|---|---|---|---|
| A1 | Model | Parametric walls/floors/roofs/ceilings with layered assemblies | Yes (spec → Revit build) | Design model + spec; layer build-ups in knowledge |
| A2 | Model | Wall joins, cleanup, hosted openings | Implicit | Model rules + geometry checks |
| A3 | Model | Stairs/railings tools | Yes (stair DirectShapes, read-back) | concept/stairs.py + L1 checks |
| A4 | Model | Parametric families (doors, windows, furniture, fixtures), types | Yes (family placement, bbox checks) | Product/asset library + catalogue figures |
| A5 | Model | Levels, grids, datums | Yes (datum −1.80 vs scene −3.00) | Model levels table (proposed contract change) |
| A6 | Model | Existing vs new (phases), the client's existing structure (omar.rvt) | Yes (kept columns, neighbours, apartment above) | Extracted context in the model; re-extraction path if the existing building changes |
| A7 | Model | Design options (D1/D2/D3) | Partly (option builds) | Model per design id |
| A8 | Model | Rooms/areas: room bounding, net area, volume | Yes (net areas from read-back) | Net/clear areas computed from built walls |
| B1 | Checks | Independent second build of the spec (catches spec errors) | Yes (implicit) | RV1 checks on the BUILT scene (different code path from the spec) |
| B2 | Checks | Interference/clash detection | Yes (stair vs beam) | RV1 clash checks |
| B3 | Checks | Read-back post-conditions (heights, sizes, positions) | Yes (walls through ramp, door under soffit) | RV1 dimension read-back vs model |
| B4 | Checks | Built-in warnings (overlapping walls, room separation, unenclosed rooms) | Implicit | Model validation rules |
| B5 | Checks | Fixture insertion vs emitter position | Yes (pendant drop lever) | Photometric emitter check (L6) + RV1 |
| C1 | Documents | Plans, RCPs, furnished plans, site plan | Yes | documents/ (L5) + RV2 |
| C2 | Documents | Sections, elevations, callouts, details | Partly | RV2 Blender line art |
| C3 | Documents | Tags, dimensions, annotation, legends, keynotes | Yes (partial) | documents/ rule-based annotation |
| C4 | Documents | View templates, line weights, hatches, colour-fill room plans | Unclear | RV2 drawing standard |
| C5 | Documents | Schedules (door, window, room, finish), auto-updated | Yes | documents/ schedules from the model |
| C6 | Documents | Sheets, title blocks, revisions/clouds, print sets, PDF/DWG export | Yes | documents/ + RV3 |
| D1 | Quantities | Material takeoffs, quantity schedules (BOQ) | Not yet (pricing deferred) | Model quantities (later) |
| E1 | Exchange | Native RVT for other professionals | Yes (future hand-over) | RV3 IFC + DXF |
| E2 | Exchange | Linking, worksharing, NWC/gbXML | No | Not needed now (single team) |
| F1 | MEP | Electrical circuits/panels in the model | Planned (L7 E-12) | L7 engine outputs (schedules, SLD) + IFC export |
| G1 | Automation | Revit API / MCP tools | Yes (pyRevit scripts) | Python on the model |

## To complete after RV1 reports
- Reconcile both lists; mark gaps.
- Per row: decision, owner lane (RV1 checks / RV2 2D / RV3 exchange / existing lane), equivalence proof
  (which historical defect or old deliverable it must reproduce), effort, risk.
- Sequence and lane briefs; then client approval.
