---
outline:
  - title: Executive Summary
    link: "#executive-summary"
  - title: Overview and Authority
    link: "#overview-and-authority"
  - title: Architectural Inventory by Luminaire Kind
    link: "#architectural-inventory-by-luminaire-kind"
  - title: Villa Architectural Luminaire Kinds
    link: "#villa-architectural-luminaire-kinds"
  - title: Bedroom Capability Example Fixtures
    link: "#bedroom-capability-example-fixtures"
  - title: Attribute Duplication and Inconsistency Audit
    link: "#attribute-duplication-and-inconsistency-audit"
  - title: Phase 2 Unification Target
    link: "#phase-2-unification-target"
executive_summary: >-
  This document provides a comprehensive inventory of luminaire definitions across the villa
  project and the bedroom capability example, mapping where every photometric, physical,
  geometric, and electrical attribute lives today. The audit identifies cross-subsystem
  fragmentation across five independent authoring boundaries, establishing requirements
  for Class C5 Phase 2 unification into a single authoritative FixtureRecord.
---

# Executive Summary

This document provides a comprehensive inventory of luminaire definitions across the villa project and the bedroom capability example, mapping where every photometric, physical, geometric, and electrical attribute lives today. The audit identifies severe cross-subsystem fragmentation where single physical attributes (flux, colour temperature, emitter coordinates, housing bounds, and mounting heights) are duplicated and independently derived across five distinct authoring boundaries. These findings establish the technical requirements for Class C5 Phase 2, where a single typed FixtureRecord will become the sole owner of photometry, emitter, housing, and mount.

# Overview and Authority

In accordance with the Class C5 rule established in [docs/lessons-audit.md](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md), "One fixture record owns photometry, emitter, housing and mount." Historical defects across the project (`l0025`, `l0026`, `l0074`, `l0080`, `l0090`, `l0095`, `l0096`, `l0119`, `l0123`, `l0606`, `l0610`, `l0650`, `l0656`, `l0874`) stemmed from architectural disconnects between:
1. Photometric files declaring flux, distribution, and geometry.
2. Revit families declaring BIM parameters, insertion datums, and symbolic webs.
3. Authored layout and spec files declaring nominal heights, targets, and roles.
4. Render scene builders generating procedural meshes and emissive proxy materials.
5. Lighting calculation engines projecting direct and reflected illuminance.

# Architectural Inventory by Luminaire Kind

## Villa Architectural Luminaire Kinds

The villa lighting scheme defines 23 distinct luminaire kinds in `src/archpipe/concept/villa_lighting.py`:

| Kind ID | Role & Description | Mount Type | Photometry Source | Flux (lm) | CCT (K) | Emitter Datum | Housing Geometry |
|---|---|---|---|---|---|---|---|
| DL | Flush trimless downlight, wide (ambient) | recessed | `iguzzini/LSEVO-AAK3EW.ies` | 650 (kind) / 670 (prod) | 2700 | `f.z - 0.03` | `disc_down` D83mm, lens D36mm |
| DLN | Flush trimless downlight, medium (task) | recessed | `iguzzini/LSEVO-AAIIA6.ies` | 750 (kind) / 780 (prod) | 3000 (kind) / 2700 (prod) | `f.z - 0.03` | `disc_down` D83mm, lens D36mm |
| ADJ | Flush trimless adjustable accent (accent) | recessed | `iguzzini/LSEVO-AAHENX.ies` | 500 (kind) / 510 (prod) | 2700 | `f.z - 0.03` | `disc_down` D83mm, lens D36mm |
| WW | Flush trimless wall washer substitute | recessed | `iguzzini/LSEVO-AAK3EW.ies` | 650 (kind) / 670 (prod) | 2700 | `f.z - 0.03` | `disc_down` D83mm, lens D36mm |
| PEN-GLOBE | Opal glass globe pendant D300 (decorative) | pendant | `generic/PEN-GLOBE.ies` | 800 | 2700 | `f.z + r` (centre) | Procedural sphere D300, inner bulb D165 |
| PEN-SMALL | Opal glass globe pendant D200 (bedside) | pendant | `generic/PEN-SMALL.ies` | 350 | 2700 | `f.z + r` (centre) | Procedural sphere D200 |
| WALL-READ | Wall swing-arm reading light (decorative) | wall | `generic/WALL-READ.ies` | 350 | 2700 | `f.z` | Procedural bracket & sphere D120 |
| SWING | Articulated wall reading light (task) | wall | `generic/SWING.ies` | 350 | 2700 | `f.z - 0.002` | D100 wall plate, 2x 300mm arms, D120 head |
| PEN-LIN | Linear pendant 1.6 m direct/indirect (task) | pendant | `generic/PEN-LIN.ies` | 1200 | 2700 | `f.z + 0.015` | Extruded bar 1600x60x70mm, cords, canopy |
| SCONCE | Vanity wall light, opal (task) | wall | `generic/SCONCE.ies` | 450 | 3000 | `f.z` | Procedural sphere D120 |
| COVE | Perimeter LED cove strip (decorative) | strip | `generic/COVE.ies` | 900 lm/m | 2700 | `z_cove` | Procedural linear segment |
| BACK | Joinery LED strip inside book cabinet (accent) | strip | `generic/BACK.ies` | 400 lm/m | 2700 | `z_shelf` | Procedural linear segment |
| UC | Under-cabinet kitchen LED strip (task) | strip | `generic/UC.ies` | 1000 lm/m | 3000 | `z_cab - 0.02` | Procedural linear segment |
| RAIL | Wardrobe hanging rail LED strip (task) | strip | `generic/RAIL.ies` | 500 lm/m | 3000 | `z_rail` | Procedural linear segment |
| TOE | Kitchen / joinery toe-kick LED strip (night) | strip | `generic/TOE.ies` | 150 lm/m | 2200 | `z_kick` | Procedural linear segment |
| NL | Plinth / under-bed night light strip (night) | strip | `generic/NL.ies` | 100 lm/m | 2200 | `z_plinth` | Procedural linear segment |
| DESK | Adjustable wall-arm desk lamp (task) | task-lamp | `generic/DESK.ies` | 450 | 3000 | `f.z - 0.03` | Base cylinder, articulated arm, hood |
| VSTRIP | Vertical dressing mirror LED strip (task) | strip | `generic/VSTRIP.ies` | 500 lm/m | 3000 | `z_mid` | Vertical linear segment |
| STORE-BATTEN | Opal LED storage batten 0.7m (task) | strip | `generic/STORE-BATTEN.ies` | 900 lm/m | 3000 | `z_shelf` | Procedural batten segment |
| MIRROR | Backlit vanity mirror halo strip (task) | strip | `generic/MIRROR.ies` | 250 lm/m | 3000 | `z_mirror` | Perimeter rectangular halo strip |
| VSCONCE | Vertical opal sconce 0.5m (task) | wall | `generic/VSCONCE.ies` | 450 | 3000 | `f.z` | Vertical cylindrical diffuser 500mm |
| STEP | Recessed stair step marker (night) | wall-marker | `generic/STEP.ies` | 60 | 2200 | `f.z` | Wall-recessed plate 80x80mm |
| PATH | Low recessed path marker 0.3m AFF (night) | wall-marker | `generic/PATH.ies` | 60 | 2200 | `f.z` | Wall-recessed plate 80x80mm |

## Bedroom Capability Example Fixtures

The bedroom capability example defines 5 native Revit luminaire instances in `spec/bedroom-test.yaml`:

| ID | Description & Spec Role | Mount Type | Photometry (Spec vs Built) | Flux (lm) | CCT (K) | Revit Family Record | Render Mesh Extent |
|---|---|---|---|---|---|---|---|
| LT-01 | Ambient centrepiece pendant | pendant | `PLD1A21.ies` | 2780 | 2700 | `pendant_cone_16inch_106_bimlibrary.co_.rfa` | Cone shade D406mm, cord, canopy D100mm |
| LT-02 | Bedside reading pendant West | pendant | `EWL2A19.ies` | 780 | 2700 | `pendant_cylinder_simple_136_bimlibrary.co_.rfa` | Cylinder D150mm, cord, canopy |
| LT-03 | Bedside reading pendant East | pendant | `EWL2A19.ies` | 780 | 2700 | `pendant_cylinder_simple_136_bimlibrary.co_.rfa` | Cylinder D150mm, cord, canopy |
| LT-04 | Wardrobe accent linear | surface | `LGLled.ies` | 1008 | 3000 | `linear_ceiling_mount_parametric_111_bimlibrary.co_.rfa` | Extruded housing 1829x102x89mm |
| LT-05 | Desk task pendant | pendant | `LGLled.ies` | 1008 | 3000 | `pendant_cylinder_simple_136_bimlibrary.co_.rfa` | Cylinder D150mm, cord, canopy |

# Attribute Duplication and Inconsistency Audit

The inventory reveals 8 core attributes fragmented across disjoint modules:

### 1. Photometric File Path
- Stored in:
  - `src/archpipe/concept/villa_lighting.py:101-110` (`PRODUCT_CHOICE` dictionary)
  - `src/archpipe/concept/villa_lighting.py:128` (`PRODUCTS[kind]["ies"]`)
  - `src/archpipe/concept/villa_lighting.py:625-634` (`photometry_for(kind)`)
  - `src/archpipe/concept/villa_render.py:1785-1787` (writes `ies_dir / generic / (k + ".ies")`)
  - `src/archpipe/concept/villa_render.py:1797,1810` (stored into `scene["lights"][...]["ies"]`)
  - `spec/bedroom-test.yaml:124,148,158,172,187` (hand-typed filenames)
  - `src/archpipe/luminaires/install.py:31-33` (`ies_name`)
  - `src/archpipe/luminaires/library.py` (database field `photometry_file` in SQLite)
- Inconsistency: The render engine synthesizes generic IES files into `out/villa/render-d1/ies/generic` while the luminaire library exports manufacturer files to `out/ies` or `PRODUCT_IES_DIR`. A disconnected filename in `spec/bedroom-test.yaml:187` assigned a 2-ft linear strip file (`LGLled.ies`) to a round drum pendant (`LT-05`), escaping until caught by `l0098`.

### 2. Luminous Flux (Lumens)
- Stored in:
  - `src/archpipe/concept/villa_lighting.py:50-94` (`KINDS[kind]["lm"]` and `"lm_per_m"`)
  - `src/archpipe/concept/villa_lighting.py:129` (`PRODUCTS[kind]["lm"] = float(row["luminaire_lm"])`)
  - `src/archpipe/concept/villa_lighting.py:163-172` (`Fixture.lumens` property with dimmer override)
  - `src/archpipe/concept/villa_render.py:1799,1811` (`scene["lights"][...]["lumens"]`)
  - `src/archpipe/concept/villa_render.py:1803,1913,1932,1941,2010` (emissive material calculations `emission_lm_per_m2`)
  - `spec/bedroom-test.yaml:125,149,159,173,188` (`lumens` hand-typed integers)
  - `src/archpipe/luminaires/install.py:54,85` (`row["lamp_lm"]` vs `row["luminaire_lm"]`)
  - `src/archpipe/photometry.py:27` (`Photometry.total_lumens` and `integrated_flux()`)
- Inconsistency (`l0123`): In `villa_lighting.py:53`, DLN declares 750 lm, but bound product `LSEVO-AAIIA6` provides 780 lm (`villa_lighting.py:129`). In `scripts/luminaire_demo.py`, swapping a 4300 lm CoreLine lamp set into a fixture specified for 2780 lm / 2500-3500 lm band caused direct 501 lx pillow over-lighting.

### 3. Correlated Colour Temperature (CCT / Kelvin)
- Stored in:
  - `src/archpipe/concept/villa_lighting.py:50-94` (`KINDS[kind]["cct"]`)
  - `src/archpipe/concept/villa_lighting.py:130` (`PRODUCTS[kind]["cct"] = row["cct_k"]`)
  - `src/archpipe/concept/villa_render.py:1792` (`cct = int(prod["cct"]) if prod else k["cct"]`)
  - `src/archpipe/concept/villa_render.py:1803,1911,1919,1940,2010` (`mats["lens-%d" % cct]`, `mats["swing-disc-%d" % cct]`)
  - `spec/bedroom-test.yaml:130,151,161,175,190` (`kelvin` integer values)
  - `src/archpipe/luminaires/install.py:54` (`row["cct_k"]`)
  - `src/archpipe/products/lighting.py` (`cct_k`)
- Inconsistency (`l0080`, `l0118`): DLN specifies 3000 K in `KINDS[DLN]`, but bound product `LSEVO-AAIIA6` specifies 2700 K in `library.sqlite`. In `l0080`, display-sRGB blackbody conversion rendered lamps far cooler than 2700 K, prompting invalid camera white-balance tuning. In `l0118`, Signify's Revit family declared 3200 K while its LDT declared 3000 K.

### 4. Emitter Position and Size
- Stored in:
  - `src/archpipe/concept/villa_lighting.py:149` (`Fixture.z` absolute world datum)
  - `src/archpipe/concept/villa_lighting.py:178-206` (`ceiling_z` finished ceiling datum)
  - `src/archpipe/concept/villa_render.py:1798` (render light offset `[f.x, f.y, f.z - 0.03]`)
  - `src/archpipe/concept/villa_render.py:1805` (render lens mesh offset `f.z - 0.002`)
  - `src/archpipe/concept/villa_render.py:1934` (globe pendant centre `cz = f.z + r`)
  - `src/archpipe/concept/villa_render.py:1986` (linear pendant emitter `f.z + 0.015`)
  - `spec/bedroom-test.yaml:121,122` (`at: [x, y]`, `mounting_height: 2233`)
  - `src/archpipe/fixture_source.py:40-54` (`source_point(meshes)` from `light_source_symbol` apex or luminous surface)
  - `src/archpipe/fixture_source.py:57-64` (`lens_extent(meshes)`)
- Inconsistency (`l0095`): In `tests/data/bedroom-fixture-meshes-pre-fix.json`, LT-02 family insertion was placed at 2000 mm, but Revit's Light Source apex sat at 2242.8 mm (242.8 mm disconnect).

### 5. Housing Geometry and Depth
- Stored in:
  - `src/archpipe/concept/villa_lighting.py:50-94` (`aperture`, `diameter`, `length`, `reach` dimensions)
  - `src/archpipe/concept/villa_render.py:1801,1805` (recessed trim disc meshes)
  - `src/archpipe/concept/villa_render.py:1824-1889` (desk lamp procedural cylinders and hood)
  - `src/archpipe/concept/villa_render.py:1890-1910` (swing lamp rods, knuckle joint, conical shade)
  - `src/archpipe/concept/villa_render.py:1955-1959` (pendant cord and brass canopy boxes)
  - `src/archpipe/concept/villa_render.py:1964-1980` (linear pendant extruded member)
  - `tests/data/bedroom-fixture-meshes-pre-fix.json` (extracted native Revit meshes)
  - `scripts/check_bedroom.py:113-117` (`body = [p for m in meshes if role != 'light_source_symbol']`)
- Inconsistency (`l0046`, `l0943`): In `l0046`, uninspected LT-04 geometry possessed a 1828.8 mm housing that penetrated the west wall until fine extraction. In `l0943`, library swing-arm reading lamp rendered as three flat brass boxes until physical subparts were modelled.

### 6. Mount Type and Mounting Height
- Stored in:
  - `src/archpipe/concept/villa_lighting.py:50-94` (`mount`: `"recessed"`, `"pendant"`, `"wall"`, `"strip"`, `"task-lamp"`, `"wall-marker"`)
  - `src/archpipe/concept/villa_lighting.py:178-206` (`ceiling_z` computing elevation by room soffit/ramp)
  - `src/archpipe/concept/villa_render.py:2046-2136` (`_seat_recessed_on_soffit` verifying ceiling contact)
  - `src/archpipe/luminaires/library.py:70-79` (`MOUNT_WORDS` keyword heuristic)
  - `spec/bedroom-test.yaml:122,123` (`mounting_height: 2233`, `host: ceiling`)
  - `scripts/check_bedroom.py:117-128` (mount-aware ceiling penetration check)
- Inconsistency (`l0096`, `l0119`): In `l0096`, LT-01 specified mounting height 2400 mm, pushing the 16-inch cone shade top to 2717 mm through the 2700 mm ceiling. In `l0119`, Signify CoreLine recessed housing top stood at 2732 mm over 2700 mm ceiling; a naive check treated the ceiling void penetration as a geometric clash rather than a recess depth coordination requirement.

### 7. Revit Family and Specification Record
- Stored in:
  - `spec/bedroom-test.yaml:131,152,162,176,191` (`family` string filename)
  - `src/archpipe/luminaires/install.py:50,55` (`row["folder"]`, `derived["family"]`)
  - `revit/build_bedroom.py` (family loading and type symbol activation)
  - `revit/extract_model.py` (extracting placed family instances, marks, and transform matrices)
  - `src/archpipe/concept/revit_spec.py` (villa Revit generator currently lacks native lighting placement)
- Inconsistency (`l0025`): Third-party BIM families frequently embed internal photometric parameters that override host project settings even after programmatic API parameter writes appear successful.

### 8. Render Emitter Representation
- Stored in:
  - `src/archpipe/concept/villa_render.py:1798-1812` (`scene["lights"]` array with IES profile, position, aim, flux, CCT)
  - `src/archpipe/concept/villa_render.py:1803,1911,1919,1940,2010` (`scene["materials"]` emissive materials with `emission_lm_per_m2`)
  - `src/archpipe/concept/villa_render.py:1805,1914,1935,1942,2022` (`scene["meshes"]` luminous lenses, discs, diffusers, and bulbs)
  - `scripts/make_render_input.py` (bedroom render input generator)
- Inconsistency (`l0068`, `l0650`): In `l0068`, fallback render driver paths lost IES file bindings and rendered fixtures as isotropic point lights. In `l0650`, sensor camera placed 25 mm above task surface with 100 mm near clip saw inside worktops, reading 0 lx on all surfaces.

# Phase 2 Unification Target

To eliminate these systematic escapes, Phase 2 will introduce a single typed `FixtureRecord` class in `src/archpipe/fixture_record.py` that unifies all subsystems under one immutable record:

```text
+-----------------------------------------------------------------------------------------+
|                                    FIXTURE RECORD                                       |
+-----------------------------------------------------------------------------------------+
| - Identity: id, role, layer, room, level                                                |
| - Photometry: manufacturer, sku, lamp_set, ies_path, declared_lm, cct_k, cri, beam_deg  |
| - Physical Housing: mount_type, housing_extent_mm, recess_depth_mm, weight_kg           |
| - Luminous Emitter: emitter_shape, luminous_extent_mm, emitter_offset_mm, beam_vector   |
| - Native BIM Family: family_name, family_path, symbol_type, rvt_category                |
| - Render Binding: mesh_generator, emissive_material, ies_render_path, aim_vector       |
+-----------------------------------------------------------------------------------------+
```

Every downstream consumer (Revit model builder, Blender scene exporter, Radiance daylight engine, and analytic lux verifier) will read solely from this authoritative record.
