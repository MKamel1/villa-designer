# RV1: Revit parity inventory (2026-11-21)

Machine-readable twin: `knowledge/parity/revit-uses.json` (44 use rows, 21 defect rows). Frozen Revit read-backs for reproductions:
`knowledge/parity/frozen/` (11 JSON files, about 510 KB, copied unchanged from the untracked `out/villa`).
This is an inventory and a proposal. Owners and replacements are proposals; the plan decisions are the lead's.
No check code was run or built beyond the inventory; nothing was executed on the laptop after the client's workstation-only decision.

## Findings the lead should read first

1. **Revit has not touched the design since 2026-09-29.** Last read-back commits: `2549549`, `183a246` (D1 rounds 2 and 3). The roughly 14 later D1 build patch passes (`docs/lanes/L2-model.md` gaps, `L2-passes.md`) were never built or read back in Revit. Revit's checks have not covered the current D1 for over seven weeks; the Oct-Nov commits touching `revit/` are infrastructure only.
2. **Revit is not runnable now.** 2026-11-20 (`bc3b8fa`, `docs/lanes/L5-drawings.md`): Revit 2027 launched from a shell and never ran the script; most likely an Autodesk sign-in wait (inference, not confirmed). No native sheets, sections, elevations, PDF or read-back exist for D1.
3. **The villa render/lighting/daylight/L2-model chain does not read Revit output.** `concept/revit_spec.py` is a Python generator of walls, doors, windows, rooms, stair solids and the slab opening (the name is historical). It stays; every consumer calls it. The villa chain's only Revit dependency is the untracked `readback.json` (rows U30, U31 below). The bedroom capability example does depend on the Revit extract (U01, U02).
4. **Hidden dependency in committed data.** `src/archpipe/model/data/d1-elements.json` bakes Revit net room areas into 27 of 30 rooms (`net_area_basis: "Revit read-back (finished-face room area)"`). Regenerating the snapshot where `out/` is absent silently falls back to the clear-rectangle estimate, 0.0-0.5 m2 larger, for all 30. No error is raised.
5. **A second build from the same spec cannot catch spec-intent errors.** 8 of the 21 recorded defects were not caught by Revit (D03, D04, D07, D15, D16, D18, D19, D21), several of them found by the client. Revit caught the class "the builder or a generator geometry function got it wrong" (D01, D02, D05, D06, D08-D14). Parity means matching that class, not matching Revit's blind spots.
6. **The scene is less independent of the spec than a Revit rebuild was.** `villa_render` builds its shell from `revit_spec` via `villa_daylight`. A replacement check earns independence only by measuring the built meshes with a different method than the generator (surface/occupancy/ray tests), and by being proven on frozen historic geometry that really failed.
7. **The scene mesh resolution limits one historic catch.** Scene coordinates are rounded to 1 mm. D02 (landing at 3977 vs the column face Revit holds at 3977.2, a 0.2 mm touch that the Python box check passed at its 1 mm tolerance) cannot be seen in the scene. Equivalence for D02 needs either the frozen spec-resolution values or a datum rule (a face within tolerance of a kept column face counts as a clash).
8. **The scene shell lost semantic identity.** `villa_render` re-materialises daylight-scene faces by finish; walls, columns and slabs are not separate meshes (mesh ids are `shell-NNN-<material>` with `source_id` only for beams, core, fence, neighbours). Per-element checks on the scene therefore need geometric classification (faces, normals, z-occupancy), or the build must carry element ids. This is a design question for the lead, with a cheap option: add `element_id` to shell faces at build time on the workstation.

## Counts

44 rows: 31 explicit, 13 implicit.

| category | rows |
|---|---|
| check | 17 |
| data source | 12 |
| other | 9 |
| 2D deliverable | 6 |

Proposed primary owner: RV1 19, RV2 6, RV3 2, already covered 8, retire 4, unowned 5.
Status: clear 33, unclear 7, unowned 4 (U23 is unowned and unclear; counted under unclear).

### Rows still unowned (no proposed owner; need a decision)

| id | what | why it matters |
|---|---|---|
| U15 / I03 | omar.rvt: the client's existing-structure model (kept columns, framing, slabs, levels, grids, ids) and its probes | Only artefact with exact ids and sub-mm values; a `.rvt` cannot be read without Revit. Freeze with hashes; any later correction needs Revit once more or a client IFC/DWG. |
| U16 | stair-zone and wet-room probes of the existing GF (`omar-stairzone.json`, `omar-wet.json`) | Where the apartment's wet stacks and the old stair bay are. One-off, freeze. |
| U23 | Revit-shipped IES (141), family templates, template door/window types | Unclear whether any current path still resolves an IES through `photometry.revit_ies_dir()`. |
| I11 | door handing and swing | Revit did not hold it either (L1 LS4 says "not in model"); listed so it is not assumed covered. |

### Rows flagged unclear

U01 (bedroom extract: keep or retire the bedroom Revit path), U23, U27 and I07 (whether any `.rvt`/IFC is demanded by a third party; none recorded), U29 (whether the client still wants a review-markup round trip), I01 (independence of the replacement), I05 (wall joins and room bounding: Revit swallowed warnings, which are unrecorded, so what it silently repaired is unknown).

## What each Revit use was (one line each)

Explicit (31):

| id | use | category | proposed owner | status |
|---|---|---|---|---|
| U01 | L0 model extractor (`extract_model.py`, `from_extract.py`) | data source | covered: L2 model (villa); bedroom unowned | unclear |
| U02 | bedroom spec -> Revit build -> `check_bedroom.py` read-back | check | RV1 | clear |
| U03 | fixture insertion vs emitter probes (`probe_fixture_*`, `fixture_source`) | check | RV1 | clear |
| U04 | family placement gate; family bbox vs catalogue figures | check | RV1 | clear |
| U05 | `.rfa` version screening, family download | other | retire | clear |
| U06 | manufacturer luminaire Revit families, type catalogues | other | covered: external_claims | clear |
| U07 | unattended plumbing, pyRevit runner, probes, jsonsafe, launch-context pin | other | retire | clear |
| U08 | native bedroom views, sheets, PDF, markup (`export_views.py`) | 2D deliverable | RV2 | clear |
| U09 | option plans and 3D cutaways, per-option PDFs | 2D deliverable | RV2 | clear |
| U10 | read-back: walls through ramp/deck, doors vs soffit | check | RV1 | clear |
| U11 | read-back: openings vs kept columns, window credit, glazing intent | check | RV1 | clear |
| U12 | stair vs kept structure, Revit intersection filter vs Python | check | RV1 | clear |
| U13 | environment model build and read-back vs spec | check | RV1 | clear |
| U14 | environment site plan PDF, 3D context views | 2D deliverable | RV2 | clear |
| U15 | omar.rvt inventory (kept structure) | data source | unowned | unowned |
| U16 | stair-zone and wet-room probes | data source | unowned | unowned |
| U17 | NE yard wall read-back and dimensioned PDF | check | RV1 (+RV2 for the PDF) | clear |
| U18 | D1 furniture/fixture/detail read-back post-conditions | check | RV1 | clear |
| U19 | net room areas from Revit rooms | data source | RV1 | clear |
| U20 | Revit 2027 MCP inventory and our MCP wrapper | check | retire | clear |
| U21 | native drawing set: sheets, schedules, tags, sections, elevations (L5) | 2D deliverable | RV2 | clear |
| U22 | furnished plans/lighting packs (Python-drawn; Revit only as a hash input) | 2D deliverable | covered; RV2 re-points inputs | clear |
| U23 | Revit-shipped IES, templates, content corpus | data source | unowned | unclear |
| U24 | units guard, known-geometry test model | other | covered: units_guard | clear |
| U25 | scene/radiance code that only mentions Revit | other | covered | clear |
| U26 | model file lifecycle (lock, upgrade, copy-only) | other | retire | clear |
| U27 | IFC export and checker | other | RV3 | unclear |
| U28 | spec-side checks named after Revit (`check_wp1_spec`, ...) | check | covered: revit_spec | clear |
| U29 | markup and revision-cloud round trip | data source | RV2 | unclear |
| U30 | L2 snapshot carries Revit areas | data source | RV1 | clear |
| U31 | L1 compliance model reads read-back for areas, marks, counts | data source | RV1 | clear |

Implicit (13), capabilities we relied on without a script naming them:

| id | capability | category | proposed owner | status |
|---|---|---|---|---|
| I01 | independent second build of the design (catches generator errors) | check | RV1 | unclear |
| I02 | units and datum authority (project coordinates = CAD; B -1.80 vs -3000) | data source | RV1 | clear |
| I03 | holder of the client's existing-structure model | data source | unowned | unowned |
| I04 | parametric door/window families at exact size | data source | RV1 | clear |
| I05 | wall joins, cleanup, room bounding | check | RV1 | unclear |
| I06 | visual 3D review surface the client reads | 2D deliverable | RV2 | clear |
| I07 | the file format other professionals expect (.rvt, .rfa, IFC) | other | RV3 | unclear |
| I08 | solid interference engine (`ElementIntersectsSolidFilter`), stairs only | check | RV1 | clear |
| I09 | element identity and counts (Mark, spec_id) | check | RV1 | clear |
| I10 | detail solids carried as native elements (hatch, buildouts, rails, vent, swing lamps) | check | RV1 | clear |
| I11 | door handing and swing (a gap) | check | unowned | unowned |
| I12 | material/finish read (paint hue only) | data source | covered: material_basis | clear |
| I13 | false positives: grep hits that are not Revit uses | other | covered: revit_spec | clear |

Full detail per row (files, consumers, what it caught, usage, proposed replacement, how to prove equivalence) is in the JSON.

## Real defects and who caught them (the parity contract)

LEARNINGS line numbers are `docs/LEARNINGS.md` lines. "Revit" means the Revit model/read-back/intersection filter caught it.

| id | defect | caught by | reproduction data | proposed owner |
|---|---|---|---|---|
| D01 | stair treads 13-15 + headroom hit column 1590377 / 1614989, beams 1615162/1615163, slab 1615037 (r3 flight) | Revit intersection filter (LEARNINGS 600-627) | `frozen/stairs-readback.json`, `stairs-spec.json`, `env-readback.json` | RV1 |
| D02 | landing at x 3977 touching column face held at 3977.2 | Revit; Python passed (697-706) | same; sub-mm, below scene resolution | RV1 |
| D03 | walls 0.5-1.35 m through ramp/deck; fence wall 850 mm open | client, then read-back post-condition (659-683) | `frozen/options-r7-readback.json`, `options-r7-spec.json` | RV1 |
| D04 | 2.10 m door + frame under 1.91 m soffit | client (659-683) | `options-r7-readback.json` doors | RV1 |
| D05 | doors/windows through kept columns | read-back post-condition (708-713) | options read-backs + env columns | RV1 |
| D06 | window credited but not built | read-back post-condition (714-720) | `designs-r12-readback.json`, `options-r1-readback.json` | RV1 |
| D07 | faces not glazed floor to beam; read-back echoed spec | client; guard proven on r7 read-back (762-779) | `options-r7-readback.json` windows | RV1 |
| D08 | fixture insertion vs emitter (2243 mm, 57-466 mm, shade through ceiling) | Revit probe (LEARNINGS 48, 60; CLAUDE.md) | `tests/data/bedroom-fixture-meshes-pre-fix.json` (committed) | RV1 |
| D09 | free-family traps; bbox vs catalogue | Revit placement gate | `tests/fixtures/revit2027-place-families.json` | RV1 |
| D10 | wall Opening has no Mark: "built 0 times" | D1F read-back (1141-1147) | `d1f-readback.json` hatches | RV1 |
| D11 | approved details ignored by the builder | post-condition (865) | `d1f-options-spec.json` vs `d1f-readback.json` | RV1 |
| D12 | furniture as built vs spec (65/65, then 71) | post-condition (861) | `d1f-readback.json` furniture | RV1 |
| D13 | environment read-back vs spec (levels, site, azimuth, slabs, 27 columns) | `villa_env.py check` (568-582) | `env-readback.json`, `env-spec.json` | RV1 |
| D14 | net areas concept vs Revit (12.4 vs 12.17; 16.6 vs 16.66) | Revit rooms (630-646) | `d1f-readback.json` rooms (30) | RV1 |
| D15 | Mass shapes hidden in views, read-back passed | looking at the export (568-582) | none | RV2 / render_qa (a geometric check cannot see it) |
| D16 | stair headroom from the wrong datum and soffit | client r9; Revit used the same boxes (780-803) | stairs.py test, 1824 mm opening | RV1 |
| D17 | section drawn mirrored; elevation direction | Revit export used as the reference (298, 685-691) | none | RV2 (loses its reference) |
| D18 | export dark canvas, missing tags, level lines | reading the export (630-646) | none | retire |
| D19 | swing-lamp plates on the wrong face; deck slider opaque | client; Revit repeated the spec error (1306-1307) | none | RV1 (mounting host checks exist) |
| D20 | units 304.8x, IFC 1000x, level datum -1.80 vs -3000 | known-geometry test model (545-557) | `tests/fixtures/revit2027-test-model.json` | covered: units_guard + RV1 level table |
| D21 | no guards at stair opening/terrace/patio, core door swing unknown | L1 (L1-safety-report-D1.md) | none | RV1 + L1 |

Caught by Revit: 13. Not caught by Revit: 8 (D03, D04, D07, D15, D16, D18, D19, D21).

## Frequency of use

34 commits touch `revit/` (2026-09-21 to 2026-11-20). Revit models on disk: bedroom (numbered saves 0028-0030 suggest about 30 builds; inferred, not counted), test/place models, 2 environment builds, 1 stair-options model (6 options), and about 13 villa option or design rounds Sep 25-29 (S1-S5, P1-P4, r8-r10, D1-D4, D1-D3, D1F x3). omar.rvt read 3 times (17 min Revit 2021 to 2027 upgrade each). Stair intersection compare: 3 rounds, 6 options.

## Proposed equivalence method (for the lead to accept or change)

1. For each defect row with reproduction data, rebuild the historic geometry from the frozen read-back as solids in the same schema the scene uses, and require the replacement check to FAIL on it; require it to PASS on the current D1 scene built on the workstation. Report recall per defect; never tune a check to pass.
2. Where Revit was a measurement (areas, door/window sizes, furniture bboxes, columns, levels), use the frozen Revit numbers as reference values and report the maximum deviation of the scene-derived value before any basis is switched.
3. Seed a mutation set into D1 (rotation dropped, wall moved into the ramp, door head lowered, window removed, fixture through ceiling, stair tread into a column) and report recall on the seeded defects, separately from the historic cases.
4. State resolution limits (1 mm scene rounding, mesh classification) beside each check so a pass is never overstated.

## Data notes

- Read-backs live untracked in `C:\Users\mmbka\arch-pipeline\out\villa`. Eleven small ones are now frozen under `knowledge/parity/frozen/` (listed in the JSON). The large ones (`omar-extract.json`, `omar-2027-extract.json`, `omar-inventory.json`, `omar-stairzone.json`, `omar-wet.json`) are shipped to `~/archpipe/work/RV1-data` on the workstation and not committed.
- Scene built on the workstation for later check work: job `RV1-scene-build` (`/tmp/RV1-scene/scene.json`); an older scene from lane P is at `/tmp/laneP-scene/scene.json`. Scene schema observed: `meshes[]` with `id, group (shell|context|furniture|fixture|dressing|ground), material, source_id, room, faces (polygons, metres)`; `lights[]`; `models[]`; `mounting_hosts{}` (wall/floor/ceiling hosts with finished faces); shell meshes are surface soup re-materialised by finish (finding 8).
- Mislabelled names to avoid confusion: `revit_spec` (Python), "Revit axes" (a coordinate convention), "55 Revit spec builds" (Python calls).
