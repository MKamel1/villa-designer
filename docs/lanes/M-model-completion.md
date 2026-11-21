# Lane M: model completion (Revit replacement plan, stage 0)

Fills the gaps Revit used to fill silently, so drawings (RV2), checks (RV1) and IFC / quantities (RV3) build on the
design model. Everything below is in the committed snapshot `src/archpipe/model/data/d1-elements.json`
(schema `archpipe-model/1`, `schema_revision` 2: additive; no existing field changed meaning).

## What was added (plan rows)

| Row | Added | Where |
|---|---|---|
| A9 | Floor slabs `slab-B-floor`, `slab-GF-floor` (outline = room rectangles + built wall slabs; the GF slab has the stair opening as a hole; 200 mm from the levels table). The GF front terrace slab already existed (`slab-gf-terrace`) and now carries a build-up too | `geometry_complete.floor_slabs` |
| A10 | `params.layers` on every wall (finish / core / finish per side, from `knowledge/finish-build-ups.json` by the room finish code), slab, floor finish and ceiling. Each layer has material, thickness, function, status and source. Thickness is `None` where the knowledge file has none (floor-tile-bed, suspended ceiling, exterior render): never invented | `geometry_complete.wall_layers`, `add_layers_to_existing_slabs` |
| A11 | `floor-<room>` and `ceiling-<room>` elements for all 30 rooms. Ceilings carry height at the room centre, min / max over the net outline, kind (flat / cove / slab-soffit / soffit-lining) and for coves the bulkhead band and raised field | `geometry_complete.room_surfaces` |
| A12 | `type` elements (109) with the shared parameters; every door, window, furniture, dressing and luminaire has `params.type_id` | `geometry_complete.shared_types` |
| I11 / A13 | Handing and operation for every door (table below) | `geometry_doors.py` |
| A14 | Sizes with `params.size_basis` on luminaires, dressing and plants (below) | `geometry_sizes.py`, `data/derived-sizes.json` |
| A15 | `rail-gf-stair-void` has per-edge records, `return_edge` (x = 8887 mm, y -27471 to -28421 mm, along y) and `void_perimeter` (gallery edge and return guarded; arrival edge and wall side not) | `geometry_complete.guard_edges` |
| A17 | Storeys `storey-B`, `-GF` (ours), `-L1` (apartment above), `-ROOF`, `-roof-garden` (context) | `geometry_complete.storeys` |
| U15 / U16 | `knowledge/existing/` (below); each kept column links to its existing record (`existing_id`) | `geometry_existing.py` |
| A8 / U19 / U30 / U31 | Net areas from built wall faces (below); the model no longer reads `out/` | `geometry_net.py` |
| I05 | Validation rules (below); the generator refuses to export a model with an error finding | `validate_rules.py`, `api.generate` |

## Element counts before -> after (D1 snapshot)

| kind | before | after |
|---|---|---|
| beam | 24 | 24 |
| ceiling | 0 | 30 |
| column | 9 | 9 |
| context | 58 | 58 |
| door | 18 | 18 |
| fixture | 7 | 7 |
| floor | 0 | 30 |
| furniture | 81 | 81 |
| garden | 14 | 14 |
| luminaire | 142 | 142 |
| plant | 80 | 80 |
| railing | 8 | 8 |
| room | 30 | 30 |
| slab | 4 | 6 |
| stair | 1 | 1 |
| storey | 0 | 5 |
| type | 0 | 109 |
| wall | 36 | 36 |
| window | 8 | 8 |
| **total** | 517 | 696 |

## Net areas from built wall faces vs the frozen Revit values

Net area = room rectangle minus wall slabs (axis +/- half thickness), the pocket buildout and the nine kept columns
(columns run through both levels). Reference: `knowledge/parity/frozen/d1f-readback.json`, option 0 (finished-face room
area). **Max deviation 0.099 m2 (kids-a); all 27 comparable rooms within 0.10 m2 (+0.43 % to +1.42 %)**; the model is
never below Revit by more than 0.021 m2. Stated tolerance in code: 0.15 m2 (`geometry_net.TOLERANCE_M2`, tested).
The residual (+0.03 to +0.10 m2 in the GF bedrooms and corridor) is not explained: finishes are not deducted by us and
Revit's built walls are not available to measure. Revit did not read three rooms (area 0): `store-ramp`, `cinema`,
`parents-dressing-ext`; they have a model value and no reference.

| room | level | gross m2 | model net m2 | Revit m2 | deviation m2 |
|---|---|---|---|---|---|
| landing-gf | GF | 3.588 | 2.806 | 2.81 | -0.004 |
| stair-gf | GF | 8.533 | 7.791 | 7.79 | +0.001 |
| corridor | GF | 13.832 | 11.249 | 11.16 | +0.089 |
| study-game | GF | 15.596 | 13.660 | 13.63 | +0.030 |
| kids-a | GF | 13.136 | 11.909 | 11.81 | +0.099 |
| kids-b | GF | 13.136 | 11.847 | 11.75 | +0.097 |
| family-bath | GF | 6.255 | 5.244 | 5.18 | +0.064 |
| parents-bed | GF | 12.719 | 10.915 | 10.86 | +0.055 |
| parents-dressing | GF | 6.232 | 5.434 | 5.43 | +0.004 |
| parents-ensuite | GF | 6.610 | 5.058 | 5.03 | +0.028 |
| gallery-end | GF | 2.590 | 2.430 | 2.4 | +0.030 |
| parents-entry | GF | 0.803 | 0.680 | 0.66 | +0.020 |
| parents-dressing-ext | GF | 0.571 | 0.371 | not read by Revit |  |
| lounge | B | 23.435 | 21.964 | 21.87 | +0.094 |
| lounge-nook | B | 1.872 | 1.490 | 1.48 | +0.010 |
| stair-b | B | 5.376 | 4.714 | 4.71 | +0.004 |
| pantry | B | 4.137 | 2.908 | 2.88 | +0.028 |
| hall-b | B | 3.080 | 2.772 | 2.77 | +0.002 |
| entry-b | B | 3.222 | 2.900 | 2.9 | -0.000 |
| family | B | 4.743 | 4.666 | 4.65 | +0.016 |
| kitchen | B | 11.411 | 11.019 | 10.99 | +0.029 |
| kitchen-island | B | 5.874 | 5.287 | 5.29 | -0.003 |
| dining | B | 10.672 | 9.898 | 9.9 | -0.002 |
| dining-side | B | 5.244 | 4.899 | 4.92 | -0.021 |
| living | B | 21.488 | 19.454 | 19.45 | +0.004 |
| bar-alcove | B | 6.635 | 5.151 | 5.15 | +0.001 |
| store-ramp | B | 9.711 | 8.364 | not read by Revit |  |
| cinema | B | 18.245 | 16.468 | not read by Revit |  |
| guest-wc | B | 5.899 | 5.132 | 5.06 | +0.072 |
| dirty-kitchen | B | 12.594 | 10.816 | 10.79 | +0.026 |

Before this lane the model took the Revit value for 27 of 30 rooms and, when `out/villa/furnish-d1/revit/readback.json`
was missing, silently fell back to a clear-rectangle estimate. `ARCHPIPE_REVIT_READBACK` is **no longer read anywhere**
(a test sets it to a bad path and checks nothing changes). The frozen Revit values are only a comparison.

## Door handing and operation (I11 / A13)

Rules (module docstring of `geometry_doors.py`): R1 never swing across a stair landing; R2 swing into the room that is
entered, ranked by privacy; R3 hinge on the jamb whose 90-degree sector overlaps least with furniture, columns, stair and
other doors, then nearer the room end wall. Authored swings (G1 core door, DOOR_TYPES, under-stair cupboard) are kept.
`hinge_side` uses model-axis words (west/east = -x/+x for a wall along x; south/north = -y/+y for a wall along y),
as the authored G1 doors do, **not** the client compass; `hinge_xy_mm` is exact. `handing` is LH/RH seen from the push
side. Clear width stays the nominal leaf width for hinged doors (an upper bound; no source for the stop and leaf
thickness).

| door | operation | swing into | hinge | handing | leaf / clear mm | judgement? |
|---|---|---|---|---|---|---|
| B-lounge-nook-pantry | hinged | lounge-nook | east | RH | 800 / 800 | no |
| B-lounge-cinema | hinged | cinema | east | RH | 900 / 900 | YES: both rooms rank equally for privacy (cinema, lounge): chose the room with the lower swing-sector conflict |
| B-cinema-store-ramp | hinged | store-ramp | south | LH | 800 / 800 | YES: the two hinge jambs are equivalent within 50 mm of the room end wall: hinge side is a free choice |
| B-family-guest-wc | hinged | guest-wc | east | RH | 800 / 800 | no |
| B-kitchen-dirty-kitchen | sliding | - | - | n/a | 1200 / 1200 | no |
| B-entry-b-core | hinged | entry-b | west | LH | 1000 / 1000 | YES: entrance door: swings into the villa by default (the GF core door is authored outward, G1 LS4); the two hinge jambs are equivalent within 50 mm of the room end wall: hinge side is a free choice |
| B-dining-yard | sliding | - | - | n/a | 2350 / 2350 | no |
| B-living-yard | sliding | - | - | n/a | 2760 / 2760 | no |
| B-living-yard-2 | sliding | - | - | n/a | 2400 / 2400 | no |
| B-lounge-yard | sliding | - | - | n/a | 3710 / 3710 | no |
| GF-corridor-kids-a | hinged | kids-a | east | RH | 900 / 900 | YES: the two hinge jambs are equivalent within 50 mm of the room end wall: hinge side is a free choice |
| GF-corridor-kids-b | hinged | kids-b | west | LH | 900 / 900 | YES: the two hinge jambs are equivalent within 50 mm of the room end wall: hinge side is a free choice |
| GF-parents-bed-parents-dressing | hinged | parents-dressing | east | LH | 800 / 800 | no |
| GF-gallery-end-family-bath | hinged | family-bath | west | LH | 800 / 800 | YES: the two hinge jambs are equivalent within 50 mm of the room end wall: hinge side is a free choice |
| GF-corridor-parents-entry | pocket | - | - | n/a | 900 / 900 | YES: pocket side not authored: the leaf retracts to one side of the opening and the spec does not say which |
| GF-parents-dressing-ext-parents-ensuite | hinged | parents-ensuite | east | LH | 800 / 800 | YES: both rooms rank equally for privacy (parents-dressing, parents-ensuite): chose the room with the lower swing-sector conflict |
| GF-landing-gf-core | hinged | core | west | RH | 1000 / 1000 | no |
| GF-study-game-deck | sliding | - | - | n/a | 1800 / 900 | no |

All 11 hinged swing sectors are clear of furniture, columns, stair and each other's sectors (`swing_clear`,
`swing_stair_clear`). 8 of the 18 doors carry `judgement: true` with the reason on the element; they are the client's
or lead's to confirm: ties between equally ranked rooms (lounge/cinema, dressing-ext/ensuite), jambs that are
equivalent because the door is centred in its wall, the entrance door's swing direction (into the villa here, outward at
GF by G1 LS4), and the side the pocket leaf retracts to.

## Existing structure (U15 / U16): `knowledge/existing/`

`MANIFEST.json` carries the sha256 of every file and of the original it came from. `omar-inventory.json` (15 structural
columns with Revit ids and bboxes, 3 floors, levels, 0 grids, 0 framing), `omar-wet.json` (wet-room probe),
`omar-stairzone.json.gz` (stair-zone probe), `omar-2027-extract.nomesh.json.gz` (the 425 MB Revit 2027 extract without
mesh triangles: 63 walls, 27 openings, wall types, levels, site; 10 KB). `geometry_existing` verifies the hash on every
read and raises `ExistingDataError` on a missing or edited file. The model's nine columns are matched to their existing
ids within 1 mm (the other six existing columns are outside our plot). `omar-extract.json` (the 2025 attempt) was 0 bytes
and is not frozen. A change to the existing building comes from a new survey, which replaces files and manifest together.

## Validation rules (I05) and what they found on D1

Rules: wall-end joins (corner-only contact is a gap), wall overlaps, room-boundary closure (walls, infills, columns,
separations, openings, or a linked neighbour), hosted openings (host exists and is on the level, within the wall's
length, head below the wall top, no two openings overlap), unique ids, type / host / room references.
Result on D1 **before fixing**: 5 findings, all corner-only joins: wall B-2 at both ends (6.94 and 17.268 m), B-17 at
(17.368, -28.671), GF-33 and GF-34 at (19.704 / 22.224, -28.671): 100-200 mm notches where a wall meets the
perpendicular wall corner-to-corner. **Fix** (`revit_spec._close_corner_gaps`, applied inside `revit_spec.build`): lengthen
the end across the notch (4 walls changed; `spec["wall_joins_fixed"]` lists them). The B-4 / B-16 corner is filled by a kept
column and is left alone. Side effect: stair-b, parents-dressing and dining-side net areas moved towards the Revit
values (stair-b +0.034 -> +0.004, parents-dressing +0.067 -> +0.004). Closure, overlap, host and id rules found nothing
on D1 and each has a negative test (a removed wall, a duplicate wall, an oversize door, a missing host, a duplicate id).

## Sizes (A14): bases

| basis | elements |
|---|---|
| IES LM-63 luminous opening (diameter 31 / 69 / 72 mm; the file gives no housing) | 82 product luminaires |
| authored strip run length (section not authored) | 36 |
| dimension written in the requirement text (D300, 1.6 m, 0.6 m, 0.3 m) | 12 |
| glTF POSITION bounding box times placed scale | 28 dressing items |
| garden palette height of the species (placed height ASSUMED within the verified range) | 80 plants |
| **not derivable** (generic fixture, no product, no dimension in its text) | 12 luminaires: STEP x3, DESK x5, SCONCE x2, WALL-READ x2 |

IES files and glTF assets are outside git, so the values read from them are frozen with their sha256 in
`data/derived-sizes.json`; re-run `python -m archpipe.model.geometry_sizes --refresh` where the libraries exist.

## Judgement calls (mine, for the lead to veto)

1. Schema stays `archpipe-model/1` with `schema_revision: 2`; new kinds `storey`, `floor`, `ceiling`, `type` (additive).
2. Net area is the rectangle minus wall slabs, pocket buildout and columns; finishes are not deducted (the match to Revit
   is better without). Wall build-up finish layers are **in addition to** the authored thickness for the same reason.
3. Wall core material is "not authored": the spec and CAD give a thickness only. Structural material is not guessed.
4. The roof garden storey is the top of the extension roof slab (`slab-roof-*`), because villa_env has no roof-garden
   level; flagged as context.
5. Wall cleanup changes the spec geometry (4 walls longer by 0.2 m / 0.1 m). It changes the scene too (a hole in a wall
   corner closes); it was chosen over leaving a validator exception because the notch is real in the built model.
6. Ceiling heights come from `villa_lighting.ceiling_z`; no board thickness or void is stated (the build-up record is UNVERIFIED).
7. Luminous opening is not the luminaire housing: sizes of product luminaires are marked as such.

## Remaining gaps

- 12 generic luminaires have no size (STEP markers, desk lamps, vanity sconces, wall reading lights): needs a product choice.
- Floor-finish, ceiling-board and render thicknesses are unknown (knowledge records are null/UNVERIFIED); structural
  material of walls and slabs is not authored; the 3 rooms Revit did not read have no reference value.
- The GF slab outline ignores the terrace and the deck (separate slabs); slab edges at the B extension under the ramp are
  the room outline, not a surveyed edge.
- Roof garden elevation is derived, not surveyed. A16 georeferencing stays deferred.
- The six existing columns outside our plot, the 63 existing walls and the 27 existing openings are frozen but not yet
  turned into context elements.
- Legacy tests listed in the hand-back: see the final report.
