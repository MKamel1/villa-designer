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

## Additions from RV2 (2D capabilities not in its brief)

| # | Capability | Decision (draft) |
|---|---|---|
| C7 | Schedules for every category (finish, fixture, luminaire, furniture), not just door/window/room | Replace now |
| C8 | Material-driven cut and surface hatches (poché follows the material) | Replace now |
| C9 | Colour-fill room/area plans with legends | Replace now |
| C10 | Enlarged callouts: stair and wet rooms 1:20, wall sections, 1:5 details | Replace now (stair, wet rooms); details later |
| C11 | View templates, line-weight table per scale, dimension styles incl. EQ | Replace now (one drawing standard) |
| C12 | Spot elevations, ceiling-height and keynote tags | Replace now |
| C13 | Stair UP/DN arrows with break lines; auto-updating section/elevation markers | Replace now |
| C14 | Revision clouds, revision schedule, sheet/view lists, print sets | Replace later (single team) |
| C15 | Linked-model overlays (neighbours, structure) and phasing graphics (kept existing columns) | Replace now (context and existing columns shown distinctly) |
| C16 | Shade and sun-path overlays on elevations | Replace later (client prefers shade; useful) |

**Defect found by RV2:** the existing model-generated plan sheets draw model +y up and label it north.
Client convention: street side (model −x) is NORTH, +y EAST, +x SOUTH, −y WEST; the old Revit sheets have
the street at the top. Fix: map model (x, y) → sheet (y, −x) once before drawing; true north only as a
labelled secondary on the site plan.

**Lead decisions (routine):** plans drawn north-up in the client convention; paper and scale set per
sheet (A3 default; larger only where a drawing needs it, e.g. a full-length section).

## Additions from RV3 (exchange/BIM capabilities and model gaps)

Model gaps Revit used to fill implicitly (these block both drawings and exchange, so they go to the
design model first):

| # | Gap | Decision (draft) |
|---|---|---|
| A9 | No floor slabs for B and GF in the model | Replace now (model) |
| A10 | No layered wall/floor/ceiling build-ups or materials as elements (Revit assemblies) | Replace now (model; build-ups exist in knowledge/finish-build-ups.json) |
| A11 | Ceilings and floor finishes not separate elements | Replace now (model) |
| A12 | Shared types (door/window/furniture/luminaire types) instead of one-off occurrences | Replace now (model + IFC types) |
| A13 | Door handing / operation not authored | Replace now (model; also needed by electrical switch placement and drawings) |
| A14 | Sizes missing for 106 of 142 luminaires and 28 dressing items; plant heights | Replace now (model) |
| A15 | Stair-void guard return edge has no position | Replace now (model) |
| A16 | Georeferencing: survey point, project base point, true north vs client north | Replace later (needs the real plot survey) |
| A17 | Extra levels (apartment L1, roof, roof garden) as storeys | Replace now as context levels |

Exchange capabilities:

| # | Capability | Decision (draft) |
|---|---|---|
| E3 | IFC types with shared property sets; material layer sets | Replace now |
| E4 | Standard property sets and quantities (Pset_*Common, Qto) for walls, doors, slabs, spaces | Replace now |
| E5 | IfcGrid; space boundaries (IfcRelSpaceBoundary) | Replace now |
| E6 | Classification codes (Uniclass) | Replace later (needed when a contractor/QS joins) |
| E7 | Discipline exports: architecture, interior, lighting, electrical (circuits as distribution systems) on a shared origin | Replace now (architecture + lighting + electrical) |
| E8 | BCF issue exchange, IDS delivery spec, revision/delta comparison between exports | Replace later |
| E9 | Design options (D1/D2) as separate IFCs | Replace later |
| E10 | Native .rvt/.dwg | Not producible without Autodesk/ODA tools; DXF + IFC instead. Revisit only if a recipient insists |

## Reconciliation with RV1 (project inventory: 44 uses, 21 defects — docs/lanes/RV1-parity.md)

What the inventory changed:
- **Revit has not touched the design since 2026-09-29.** The later D1 changes were never built or read
  back in Revit, so today nothing independent checks them. Replacing this is urgent, not optional.
- **What Revit could and could not catch.** It caught "the generator built it wrong" (13 of the 21
  defects). It could not catch design-intent errors, because it rebuilt from the same spec; the other 8
  were caught by the client or by looking at exports. The replacement must do at least the 13 and should
  add the 8.
- **Silent dependency.** The model bakes Revit net areas into 27 of 30 rooms and falls back to a larger
  estimate with no error when the untracked read-back is absent. Same class as the daylight issue fixed
  on 2026-11-21.
- **Independence has to be earned.** The scene shell is merged by finish (no per-element meshes), and
  scene coordinates are rounded to 1 mm, so a sub-mm case (D02: landing touching a column by 0.2 mm) is
  below scene resolution.
- Items in both lists: A1–A8, B1–B5, C1–C6, E1, G1. Only in RV1: U02/U03/U04 (bedroom and fixture
  probes), U16 (stair-zone and wet-room probes of the existing building), U23 (Revit-shipped IES and
  templates), I09 (element identity and counts), D15/D17/D18 (problems seen only by looking at exports).
  Only in the generic list or RV2/RV3: C7–C16, A9–A17, E3–E10. No row is left unowned below.

## Principles

1. **Every input a check depends on is tracked in git or fetched explicitly; a missing input fails
   loudly.** Never silently fall back.
2. **Independence by construction.** Checks measure the built scene with their own geometry code, and a
   second, separate kernel (the IFC export read back through IfcOpenShell's geometry engine) is used for
   clashes. Neither path reuses the spec generator's arithmetic.
3. **Element identity end to end.** The scene build carries model element ids onto every mesh, so checks
   are per element, not per surface soup.
4. **Equivalence is proven, not asserted.** Each check must FAIL on the frozen historic defect it replaces,
   PASS on current D1, and catch a seeded mutation set (wall into the ramp, door head lowered, window
   removed, fixture through the ceiling, tread into a column, rotation dropped). Recall is reported per
   defect; nothing is tuned to pass. Resolution limits are stated beside each check.
5. **The design model is completed before drawings and exchange build on it.**

## Decisions on the open rows

| Row | Decision |
|---|---|
| U15/I03 omar.rvt (existing structure) | Freeze: commit the extract JSON (kept columns, framing, slabs, levels, grids, ids) with its hash as tracked data. Any future change to the existing building comes from a new survey, not Revit. |
| U16 stair-zone / wet-room probes | Freeze the two probe JSONs as tracked data; they are one-off facts about the existing building. |
| U23 Revit-shipped IES and templates | Audit: fail loudly if any path still resolves a Revit-shipped IES; replace any hit with frozen IES in knowledge/lighting/ies. Templates retire. |
| I11 door handing and swing | Model gap (A13): author for every door. |
| U01 bedroom example Revit path | Retire. The bedroom stays as a calibrated photometry example through the scene path only. |
| I01 independent second build | Principle 2: built-scene checks plus the IFC-kernel clash check. |
| I05 wall joins and room bounding | Model validation: wall-to-wall join and room-closure checks, with the room-bounding result compared to the frozen Revit room areas. |
| D02 sub-mm contact | Check exact contacts on the model geometry (no rounding), not the scene. |
| D15/D17/D18 visible only in exports | Sheet QA in RV2 (orientation and mirroring check against the model; tags; level lines) plus the render critic. |
| U27/I07 who receives files, U29 markup round trip | **Client questions** (below). |

## Workstreams, in order

| Stage | Lane | Work | Proof of equivalence | Size |
|---|---|---|---|---|
| 0 | M (model completion) | A9–A15, A17, I11: floor slabs, layered build-ups and materials, ceilings and floor finishes as elements, shared types, door handing, luminaire/dressing sizes, stair-void guard return, context levels; net areas computed from built walls with the frozen Revit areas as reference (report max deviation; fail loudly if inputs are missing); freeze omar extracts and probes (U15, U16) | Model validation rules (joins, closure, hosts); areas within a stated tolerance of the frozen Revit values | 1–2 days |
| 1 | P2 (scene identity) | Carry element ids onto every scene mesh (I09, principle 3) | Scene hash changes only by the added id field; render appearance unchanged | ½ day |
| 2a | RV1 (checks) | Built-scene checks for U02–U04, U10–U13, U17–U19, I04, I08–I10, D01–D14, D16, D19, D21 + the IFC-kernel clash check + the mutation set | Historic recall table (13 Revit-caught defects + the others where data exists); mutation recall; D1 passes | 2–3 days |
| 2b | RV2 (2D) | North-up fix first; drawing standard (C11); plans, furnished, lighting/RCP and site plans; Blender line-art sections and elevations (incl. stair 1:50); schedules for every category (C5, C7); hatches (C8); colour-fill room plans (C9); callouts for stair and wet rooms (C10); annotation (C12, C13); context and kept-columns graphics (C15); sheet QA for orientation, mirroring, tags and level lines (D15, D17, D18) | Side-by-side parity table against every old Revit 2D output (U08, U09, U14, U17, U21, U22); sheet QA counts at zero | 3–4 days |
| 2c | RV3 (exchange) | IFC4 with types and material layer sets (E3), standard Psets and Qto (E4), grids and space boundaries (E5), discipline files for architecture, lighting and electrical (E7); DXF per level and site | Round-trip counts and dimensions vs the model; schema validation 0 errors; files open in a second viewer | 1–2 days |
| Later | — | C14 revisions and print sets, C16 sun overlays, D1 BOQ quantities, A16 georeferencing (needs the survey), E6 classification, E8 BCF/IDS, E9 design options | — | when needed |

Stages 2a, 2b and 2c run in parallel on the workstation after stages 0 and 1. Revit stays optional: if the
client signs in again, a Revit rebuild becomes one more independent check, never a dependency.
