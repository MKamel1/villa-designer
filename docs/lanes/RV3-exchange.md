# Lane RV3: Revit-free exchange (IFC4, DXF, quantity take-off)

Replaces plan rows E1, E3, E4, E5, E7 and stage 2c / 2c+ of `docs/quality/REVIT-REPLACEMENT-PLAN.md`. Built on the completed
model from lane M (696 elements). One command:

    python -m archpipe.exchange --out out/exchange/D1        # exit 0 all checks pass, 1 a check failed, 2 export refused

`out/` is git-ignored: regenerate. The manifest (`manifest.json`) holds counts, sha256 per file and the validation result.
Two consecutive runs give byte-identical IFC files (tested; the ifcopenshell API's random relationship GlobalIds and set
ordering are replaced by content-derived values in `ifc.deterministic_ids`).

## What is produced (D1)

| file | content | size |
|---|---|---|
| `D1-ARCH.ifc` | architecture + interiors: walls, rooms (IfcSpace), floor slabs, slabs, floor and ceiling coverings, doors, windows in wall voids, stair, guards, columns, beams, furniture, fixtures, plants, gardens, context volumes (flagged not ours), 5 storeys, structural grid, space boundaries, types, material layer sets | 1.18 MB |
| `D1-LIGHT.ifc` | 142 luminaires with photometric Psets on 35 IfcLightFixtureTypes; 59 control-zone IfcGroups | 0.46 MB |
| `D1-ELEC.ifc` | 3 boards (MDB, DB-B, DB-GF) + the ELV rack, 273 devices, 59 circuits (57 final + 2 feeders) as IfcDistributionSystem (ELECTRICAL) | 0.58 MB |
| `D1-B.dxf`, `D1-GF.dxf`, `D1-SITE.dxf` | plans, AIA-style layers, mm 1:1 | 0.1 MB each |
| `quantities/D1-takeoff.xlsx` + `D1-{by_type,by_room,by_layer,elements,reconciliation}.csv` | QS take-off, no prices | |

All three IFC files share one origin: same IfcProject / IfcSite / IfcBuilding / IfcBuildingStorey GlobalIds, elevations and
placements (checked, `validate_shared_origin`). Datum is the **Revit datum** (B FFL -1800 mm, GF +1200 mm); the scene datum
is Revit minus 1200 mm. Model x, y are used unchanged. Linking the three files in any federated viewer needs no transform.

### IFC contents against the plan rows

* **E3 types.** 109 model types become IfcDoorType (11), IfcWindowType (7), IfcFurnitureType (52), IfcSanitaryTerminalType (4)
  and IfcLightFixtureType (35), each with `ArchPipe_TypeShared` (the shared parameters) and every occurrence linked by
  IfcRelDefinesByType. Luminaire types carry `Pset_ManufacturerTypeInformation`, `Pset_LightFixtureTypeCommon` and
  `ArchPipe_Photometry` (flux, W, CCT, CRI, beam, IES file name, substitute / generic flags). **IfcMaterialLayerSet**: 102
  walls, slabs, floors and ceilings, built from `params.layers` in order (left finish, core, right finish); identical build-ups
  share one layer set. A layer with no authored thickness (floor tile bed, suspended ceiling, exterior render) is written with
  thickness 0 and a Description saying "thickness not authored (0 here is not a value)"; the full list with status and source
  is in `ArchPipe_Layers`. The wall body is the structural core: the finishes are layers on top, so the layer set total is
  larger than the drawn wall thickness (no layer set *usage* is written).
* **E4.** `Pset_WallCommon / DoorCommon / WindowCommon / SlabCommon / CoveringCommon / SpaceCommon / ColumnCommon / BeamCommon /
  StairCommon / RailingCommon` with only what the model states (IsExternal, Reference, ...); no fire rating or load-bearing
  flag is written because none is authored. Quantities: `Qto_WallBaseQuantities` (length, width, height, gross / net side
  area with openings deducted, gross / net volume), `Qto_SlabBaseQuantities` (area net of the stair opening, depth, perimeter,
  volumes), `Qto_DoorBaseQuantities`, `Qto_WindowBaseQuantities`, `Qto_SpaceBaseQuantities`, `Qto_CoveringBaseQuantities`.
* **E5.** `IfcGrid` from the nine kept columns: 7 numbered axes and 2 lettered axes (the y positions -23771 to -23921 mm cluster
  within 200 mm into one axis, so column centres sit up to 75 mm off their axis; stated in `ArchPipe_Grid`). 147
  `IfcRelSpaceBoundary` (first level, no connection geometry) relate each space to its wall sides, doors, windows, floor and
  ceiling; plus `IfcRelCoversSpaces` for the 60 coverings.
* **Door `OperationType` from handing.** Hinged: LH -> SINGLE_SWING_LEFT, RH -> SINGLE_SWING_RIGHT, two leaves ->
  DOUBLE_DOOR_SINGLE_SWING; sliding with two leaves -> DOUBLE_DOOR_SLIDING, otherwise USERDEFINED with the leaf count; pocket ->
  USERDEFINED "POCKET_SLIDING". **Open point:** lane M's handing is "seen from the push side"; I have not verified which side
  the IFC LEFT/RIGHT convention views from. `ArchPipe_DoorHanding` therefore carries the exact hinge point (mm), swing room and
  radius, and those take precedence over the enum.
* **E7.** Storeys: B and GF (ours), L1 (apartment above), ROOF and the roof-garden level are written with
  `ArchPipe_Level.NotOurs = true` and no elements. Context volumes are IfcBuildingElementProxy with the Description "NOT OURS".
  **Lighting control zones:** `knowledge/lighting/zones-d1.json` does not exist on any branch of origin (checked
  integ/aplus and all lane branches), so the zones are the electrical lane's provisional ones from `device_list.csv`
  (`serves`, e.g. `Z-PROV-bar-alcove-accent`): 59 IfcGroups (ObjectType `LightingControlZone`), every luminaire in exactly one,
  each labelled provisional. **Electrical:** inputs are `tests/electrical/d1/` (device and board-schedule CSVs) and the board
  positions from `archpipe.electrical.villa`. A circuit's group holds its board and its devices; luminaires are not
  duplicated into this file (they are in D1-LIGHT): each circuit lists `LuminaireIds` and a count. A switch that serves two
  circuits (`DB-B/L1+DB-B/L2`) is a member of both. Cable lengths are the electrical lane's route estimates, said so in the Pset.

## Validation (D1, `validate.py`, re-reads the file; geometry re-tessellated by the IfcOpenShell kernel, world coordinates, voids applied)

| check | n | worst | tolerance |
|---|---|---|---|
| class counts: every IfcProduct / type class vs expectation from the model | 550 (ARCH), 185 (LIGHT) | exact | 0 |
| id set: model element ids vs `ArchPipe_Source.SourceId` | 519 / 182 | exact | 0 |
| room areas, kernel solid volume / clear height vs model polygon | 30 | 1e-11 % | 0.5 % |
| room `NetFloorArea` Qto vs model net area | 30 | 0 % | 0.5 % |
| floor and ceiling surface areas vs model | 60 | 0.001 % | 0.5 % |
| door / window sizes (attributes and leaf geometry) | 26 | 4e-12 mm | 1 mm |
| every door / window: one fills -> one void -> the model's host wall; fill inside void, inside wall footprint | 26 | 0 mm | 1 mm |
| wall `NetVolume` Qto vs voided wall volume from the kernel (proves the voids cut) | 36 | 5e-11 % | 0.5 % |
| stair riser (tread-top steps) / going (nosing to nosing), from the IFC tread solids | 15 / 15 | 0.0004 mm / 0 mm | 0.01 mm |
| guard heights from geometry (stair guards above the tread nosing line, others by vertical extent) | 8 | 0.47 mm | 1 mm |
| placements: IFC origin vs model xy (+z where defined) | 263 + 142 (LIGHT) | 2e-12 mm | 1 mm |
| polygon extents and heights (rooms, coverings, slabs) | 93 | 4e-12 mm | 1 mm |
| types, layer sets, layer thicknesses, space boundaries, storeys flagged | 74 / 102 / 102 / 30 / 5 | exact | |
| **IFC4 schema validation, including EXPRESS rules** (`ifcopenshell.validate`) | ARCH 17 827, LIGHT 6 552, ELEC 9 119 entities | **0 errors** | 0 |
| ELEC: 4 boards, 59 circuits, 273 devices = device_list.csv; placements; membership | | 2e-12 mm | 1 mm |
| LIGHT: every luminaire in exactly one zone | 142 | | |
| shared origin across the three files | 8 spatial entities | identical | |
| DXF: ezdxf audit errors; `$INSUNITS` = 4 (mm) | 3 files | 0 | 0 |

Stair: 17 risers, 16 treads, riser 176.471 mm, going 280 mm; the model's riser bars (15 horizontal flats) are now exported too.
The exact figures from the latest run are in `out/exchange/D1/validation.txt` (59 PASS, 0 FAIL).

A check can only be believed if it can fail. `tests/exchange/test_exchange.py` (28 tests) re-validates the exported file
against a *perturbed* model and demands a FAIL: door width +5 mm, a room polygon scaled 5 %, a guard height 100 mm lower, a
stair riser changed, a ghost element id, a column moved 5 mm, and a fills relation deleted from the file itself. Export
refusals are tested too: door with no host, door hosted by a room, room without a polygon, stair without treads, unknown element
kind, luminaire in the device list that is not in the model. Round-trip, XLSX sheets, DXF layers / extents / swing arcs,
determinism and the take-off reconciliation (with a deliberately inconsistent floor) are tested. Run: `python -m pytest tests/exchange -q`.

Not a second viewer: the only IFC reader on this workstation is IfcOpenShell (parsing, kernel, EXPRESS validation). The plan's
"files open in a second viewer" gate is therefore **not yet met**; the recipient's own tool will be the first independent
check (see below). DXF files were additionally rendered through ezdxf's drawing backend and looked at.

## DXF and DWG

Per level (B, GF) and a site plan: walls (outline of centreline +/- half thickness), doors with leaf and swing arc from the hinge
point, windows, rooms with name and net area, slab outlines (the GF slab has the stair opening), stair treads, guards, columns,
beams, furniture, fixtures, luminaires, grid with bubbles; the site sheet adds exterior walls, gardens, plants at canopy
spread, context volumes, guards. Layers: A-WALL, A-DOOR, A-GLAZ, A-FLOR-OTLN, A-FLOR-STRS, A-FLOR-HRAL, A-FLOR-FIXT, A-AREA-IDEN,
A-FURN, E-LITE, S-COLS, S-BEAM, A-GRID, G-ANNO-TTLB, L-PLNT, L-SITE, X-CNTX (AIA-style names; I did not check them against the
AIA guideline text, which is not held here). R2018, `$INSUNITS` 4, coordinates 1:1 in model coordinates. No dimensions or tags:
these are plan symbols for coordination, not a drawing set (RV2).

**True `.dwg` cannot be produced here**: no ODA File Converter, Teigha, `dwg2dxf` / `dwgwrite` or LibreDWG on this machine
(`which` and a filesystem search found none; LibreOffice's snap exists but does not write DWG). The manifest records
`dwg.produced = false`. Any AutoCAD-family tool opens the DXF and saves DWG in one step; install the ODA File Converter if
a recipient insists on DWG (plan row E10).

## Quantity take-off (no prices)

`quantities/D1-takeoff.xlsx` sheets: README, by_type (194 rows), by_room (30), by_layer (112), elements (696, one row each, the
finest grain: every other table is a sum of it), reconciliation (15). Summary D1:

| item | quantity |
|---|---|
| rooms, net floor area | 227.29 m2 (B 137.90, GF 89.39); gross 257.24 m2; floor and ceiling finish areas equal it |
| walls | 36; 173.35 m long; net face area 391.23 m2 (one face, openings deducted); structural volume 64.80 m3 |
| wall finish surfaces in rooms | 525.64 m2 (one count per side); all finish layers 899.18 m2; skirting candidate 192.9 m |
| slabs | 6; plan area 309.46 m2; structural volume 67.68 m3 (basement floor 153.64 m2, GF floor 100.08 m2 net of the stair opening, deck, ramp, roof, terrace) |
| columns / beams | 9 (15.15 m3, 81.0 m run) / 24 (24.03 m3, 160.2 m run) |
| doors / windows | 18 (52.65 m2) / 8 (24.57 m2), by type and room |
| guards and handrails | 8; 39.51 m |
| stair | 1; 16 treads (4.48 m2 in plan), 17 risers, 15 riser bars |
| luminaires / furniture | 142 (984.8 W total) / 81, by type and room |

Layers: 46 layer rows have a thickness and a volume; 66 finish rows have **no authored thickness** and carry an area and a blank
volume. Reconciliation (all PASS): element count equals the model (582 exported kinds); room areas against the model and against
the SC1 room schedule (0.005 m2 net, 0.009 m2 gross, schedule rounds to 0.01); door and window counts against the schedules;
wall core and finish layer areas against face area times layers per side computed a second way; wall and slab volumes by layer
against net volumes; luminaires against the electrical `device_list.csv`; and `test_ifc_qto_equal_takeoff` ties the IFC Qto sums
to the take-off. Caveats stated in the README sheet: wall and slab **material is not authored** (volumes are of the structural
body, not "concrete"); skirting is not authored (the figure is a candidate); cable lengths are the electrical lane's estimates
(`tests/electrical/d1/cable_schedule.csv`); context elements are flagged not ours.

## How each recipient opens the files

* **Engineer / architect:** load `D1-ARCH.ifc`, then `D1-LIGHT.ifc` and `D1-ELEC.ifc` in any IFC4 viewer or BIM tool
  (they align without transform). For CAD, open `D1-*.dxf`. Trace any object to the design model through
  `ArchPipe_Source.SourceId`. Hand-over of DWG needs the DXF saved as DWG (above).
* **Contractor / quantity surveyor:** open `quantities/D1-takeoff.xlsx`; start at README, then by_room and by_type; by_layer
  gives finish areas per room and layer; `elements` traces each number to a model id. The CSVs carry the same tables.
* **Family:** the plans are in the DXF/PDF drawings and the renders; the IFC is not meant for them. Give them the room list
  (by_room sheet) and the photoreal renders.

## Known losses against a native .rvt

No parametric families (furniture and luminaires are boxes, discs or short bars, labelled as such in `GeometryBasis`); no
editable walls, no Revit constraints, schedules or sheets; no door swing geometry in IFC (the hinge point is a property; the
arc is in the DXF); coverings are zero-thickness surfaces because no finish thickness is authored; ceilings are one surface at
the room-centre height (cove and soffit variation is in the Pset); the stair is a straight run of tread plates plus riser bars
as authored, no stringer; guards are panels (flat-bar infill drawn solid); luminaire geometry is the nominal opening, not the
product body; lighting zones are provisional; electrical routes are not drawn (lengths only); IFC LEFT/RIGHT door
convention unverified; no second viewer yet; no DWG; no Revit-specific category or workset data. No jurisdiction pack is loaded:
nothing here is code compliance.

## Decisions I made (no one to ask)

1. Discipline split: ARCH holds interiors (furniture, fixtures) too; LIGHT only luminaires; ELEC only electrical. Scope `ALL`
   (ARCH + LIGHT in one file) exists in the API for a single-file hand-off but is not written by the CLI.
2. Control zones from `device_list.csv`, labelled provisional, because `zones-d1.json` does not exist.
3. Floors and ceilings as zero-thickness surfaces; a 0 layer thickness in IFC means "not authored" and says so.
4. `IfcElectricDistributionBoard` with USERDEFINED for the ELV rack (the IFC4 enum has no frame type); boards are 600 x 150 mm x
   authored height boxes on the nearest wall, starting at FFL (mounting height and orientation not authored).
5. Grid axes are clustered column centres, not a design grid (none exists).
6. `openpyxl` is needed for XLSX. `requirements.txt` is not an RV3 path, so I did not edit it: the lead should add
   `openpyxl==3.1.5` (installed into `laneP-venv`). Without it the CLI stops with a clear error rather than writing CSV only.

## Lessons (defect -> guard)

* *Random GlobalIds and set ordering made two exports of one model differ.* Missed because exports were only compared
  structurally. Guard: `test_export_is_deterministic` (byte-level) plus `deterministic_ids`.
* *Space boundaries were silently empty (0 relations) because spaces were keyed `room-x` and walls refer to `x`.* Class counts
  passed. Guard: the validator checks every space has boundaries; it failed on the real file before the fix.
* *Lane M changed railing parameters (`path_mm`, `edge_lengths_mm`) and the old exporter crashed with IndexError.* The crash was
  the right behaviour (loud); the exporter now builds path guards, and the guard-height check measures them from geometry.
* *The validator itself crashed (KeyError) when an element was missing from the file,* hiding the real finding. Guard: missing
  elements are reported by the id-set check and excluded downstream (`test_validator_catches_missing_and_extra_ids`).
