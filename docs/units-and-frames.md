---
Document Outline:
  - "[1. Executive Summary](#1-executive-summary)"
  - "[2. Overview & Architectural Motivation](#2-overview--architectural-motivation)"
  - "[3. Defect Class C9 Historical Lessons](#3-defect-class-c9-historical-lessons)"
  - "[4. Comprehensive Inventory of Conversion Sites](#4-comprehensive-inventory-of-conversion-sites)"
  - "[5. Analysis of Existing Partial Boundaries](#5-analysis-of-existing-partial-boundaries)"
  - "[6. The Single Typed Boundary: archpipe.units](#6-the-single-typed-boundary-archpipeunits)"
  - "[7. Static Guard & Fail-Closed Enforcement](#7-static-guard--fail-closed-enforcement)"
  - "[8. Phase 2 Migration Roadmap](#8-phase-2-migration-roadmap)"
Executive Summary: |
  This document provides the Phase 1 audit and inventory for defect class C9 ("coordinate or unit conversion scattered").
  It inventories all conversion sites across src/, revit/, and scripts/ (length, energy, photometric angle, solar UTC, and coordinate frames).
  It establishes the single typed boundary in src/archpipe/units.py, registers a fail-closed static guard, and outlines the Phase 2 caller migration plan.
---

# Units and Coordinate Frames: Audit, Inventory, and Boundary Architecture

## 1. Executive Summary

Defect class C9 (*coordinate or unit conversion scattered*) covers recurring errors where physical units (decimal feet, millimetres, metres, inches, Joules, kilowatt-hours), photometric axes, solar timeframes, or coordinate frame transformations (glTF Y-up vs Blender Z-up, DirectShape baked rotations, Revit view directions) are converted inline using raw literals or scattered functions rather than routed through a single typed boundary.

In Phase 1, we:
1. Conducted an exhaustive inventory of all conversion sites across [`src/archpipe`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe), [`revit/`](file:///C:/Users/mmbka/arch-pipeline-agy2/revit), and [`scripts/`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts).
2. Defined the single typed boundary in [`src/archpipe/units.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/units.py) grounded in exact international standards (NIST SP 811 / 1959 International Yard and Pound Agreement).
3. Created the fail-closed static scanner [`src/archpipe/units_guard.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/units_guard.py) and allowlist [`knowledge/unit-conversion-allowlist.json`](file:///C:/Users/mmbka/arch-pipeline-agy2/knowledge/unit-conversion-allowlist.json).
4. Provided exact mathematical reconstructions and regression proofs for historical defects (`l0182`, `l0473`, `l0012`, `l0114`, and glTF frame transformations).

---

## 2. Overview & Architectural Motivation

In architectural computation, geometry engines, BIM platforms, rendering engines, and daylight/energy simulators each adopt distinct coordinate conventions and measurement units:
- **Revit Internal Geometry**: Decimal feet ($1\text{ ft} = 0.3048\text{ m} = 304.8\text{ mm}$ exactly). A unit confusion does not raise an exception; it silently yields a model $304.8\times$ too small or too large that looks visually intact.
- **Architectural Specifications & Drawing Production**: Millimetres ($\text{mm}$).
- **Scientific Simulation (Radiance, EnergyPlus, Ladybug)**: SI Metres ($\text{m}$), Joules ($\text{J}$), or Kilowatt-hours ($\text{kWh}$).
- **glTF Asset Representation**: Right-handed Cartesian coordinate system with $+Y$ as up ($+X$ right, $+Z$ forward).
- **Blender & Radiance World Frame**: Right-handed Cartesian coordinate system with $+Z$ as up ($+X$ right, $+Y$ back, $-Y$ forward).
- **Solar Calculations**: Solar time computed from Greenwich Mean Time / UTC; passing local time with an unparsed timezone causes massive hour angle shifts.
- **Photometry (EULUMDAT vs IES LM-63)**: EULUMDAT $C0$ azimuth is offset by $90^\circ$ relative to IES LM-63 $H0$ azimuth.

When individual modules write their own inline conversion factors (`304.8`, `0.3048`, `0.001`, `1000.0`, `90.0`, `3.6e6`), systemic bugs arise:
1. Two different modules define `mm()` with opposite semantics: in [`revit/extract_model.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/extract_model.py#L52), `mm(value)` converts decimal feet to millimetres; in [`src/archpipe/radiance.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/radiance.py#L172), `mm(v)` converts millimetres to metres!
2. EnergyPlus results in Joules converted by Ladybug into $\text{kWh}$ are divided by $3.6 \times 10^6$ a second time, collapsing calculated energy loads by $3.6 \times 10^6$.
3. Solar positions computed from timezone-aware local datetimes ignore `tzinfo`, computing sun elevation for the wrong UTC hour.
4. Imported 3D assets rotate or flip axes, causing beds to render head-to-foot or foliage to grow inside rooms.

---

## 3. Defect Class C9 Historical Lessons

An audit of [`docs/lessons-audit.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/lessons-audit.md) and [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/LEARNINGS.md) identifies 7 recorded lessons in class C9:

| Lesson ID | Summary | Defect Description & Historical Consequence | Control Mechanism |
|---|---|---|---|
| `l0012` | DirectShape rotation baked | DirectShape rotation in Revit is baked into geometry; world bounding box is already rotated; family insertion point is not footprint centre. Quarter-turn reversal is exact; arbitrary rotation requires a local footprint. | Single typed coordinate boundary [`archpipe.units`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/units.py). |
| `l0023` | Revit ViewDirection points toward viewer | Revit's `ViewDirection` points toward the viewer (as documented in API reference). An elevation looking northward has vector $(0, -1, 0)$ and shows the south wall. Inverting it drew elevations looking backward. | Documented coordinate vector orientation and read-back assertion. |
| `l0114` | Converted LDT agreed with IES in flux but differed up to 34% in single directions | EULUMDAT $C0$ and IES $0^\circ$ are different axes. Totals and peaks matched, but directional intensity rotated by $90^\circ$: ```latex H_{\text{IES}} = C_{\text{EULUMDAT}} + 90^\circ ```. | Single photometric converter in [`src/archpipe/luminaires/eulumdat.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/luminaires/eulumdat.py). |
| `l0182` | Thermal results 3.6 million times too small | EnergyPlus native energy unit is Joules ($\text{J}$). Ladybug `SQLiteResult` already converts $\text{J}$ to $\text{kWh}$ ($1\text{ kWh} = 3.6 \times 10^6\text{ J}$). Downstream script divided by $3.6 \times 10^6$ a second time. | Typed conversion [`joules_to_kwh`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/units.py#L96) and unit assertions. |
| `l0409` | Section drawn mirrored | Coordinate system handedness or view cut plane direction inverted, drawing cross-sections mirrored horizontally relative to floor plans. | Explicit right-handed coordinate frame convention. |
| `l0473` | `solar.sun_position` takes UTC and ignores tzinfo | `solar.py` computed solar minutes directly from `when.hour`. Passing Cairo local time (UTC+2) at 09:30 evaluated as 09:30 UTC instead of 07:30 UTC, producing an $81^\circ$ sun altitude error. | [`require_utc(dt)`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/units.py#L114) enforcing timezone-aware UTC datetime. |
| `l0669` | Parents' bed rendered head-to-foot | Generator rotation map swapped $0^\circ$ and $180^\circ$ against generator docstring; headboard stood at foot and duvet draped over headboard. | Verified rotation map and footprint alignment tests. |

---

## 4. Comprehensive Inventory of Conversion Sites

The table below catalogs conversion sites across the repository, classifying what is converted, from/to units or frames, whether a named boundary is used, and the Phase 2 migration status.

| File & Line | What Converts | From Unit / Frame | To Unit / Frame | Through Named Boundary? | Existing Boundary Name | Phase 2 Migration Target |
|---|---|---|---|---|---|---|
| [`src/archpipe/safe_io.py:40`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/safe_io.py#L40) | Length docstring citation | ft | mm | Yes | `safe_io.convert_length` | Document reference to `units.MM_PER_FOOT` |
| [`src/archpipe/safe_io.py:42`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/safe_io.py#L42) | Length conversion scales | ft, mm, m | mm | Yes | `safe_io.convert_length` | Migrate `scales` to `units.MM_PER_FOOT`, `units.MM_PER_M` |
| [`src/archpipe/photometry.py:51`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/photometry.py#L51) | Luminous opening dimensions | decimal feet | metres | No (module constant) | `FEET_TO_M = 0.3048` | Migrate to `units.M_PER_FOOT` |
| [`src/archpipe/photometry.py:174`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/photometry.py#L174) | Luminous opening dimensions | feet / metres | metres | Yes | `Photometry.luminous_dimensions_m` | Use `units.ft_to_m` |
| [`revit/build_bedroom.py:41`](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/build_bedroom.py#L41) | Docstring explanation | feet | mm | Yes | `build_bedroom.ft()`, `mm()` | Reference `units.MM_PER_FOOT` |
| [`revit/build_bedroom.py:79-82`](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/build_bedroom.py#L79-L82) | Length (millimetres to internal) | mm | Revit decimal feet | Yes | `UnitUtils.ConvertToInternalUnits` (`ft`) | Retain Revit API wrapper |
| [`revit/build_bedroom.py:84-87`](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/build_bedroom.py#L84-L87) | Length (internal to millimetres) | Revit decimal feet | mm | Yes | `UnitUtils.ConvertFromInternalUnits` (`mm`) | Retain Revit API wrapper |
| [`revit/extract_model.py:52-55`](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/extract_model.py#L52-L55) | Length (internal to millimetres) | Revit decimal feet | mm | Yes | `UnitUtils.ConvertFromInternalUnits` (`mm`) | Retain Revit API wrapper |
| [`scripts/verify.py:560`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/verify.py#L560) | Comment explanation | feet | mm | No (comment) | None | Reference `units.MM_PER_FOOT` |
| [`src/archpipe/radiance.py:118`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/radiance.py#L118) | Millimetres to metres scale | mm | m | No (module constant) | `MM_TO_M = 0.001` | Migrate to `units.M_PER_MM` |
| [`src/archpipe/radiance.py:172-174`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/radiance.py#L172-L174) | Millimetres to metres helper | mm | m | Yes (local helper) | `radiance.mm(v)` | Rename / migrate to `units.mm_to_m` |
| [`src/archpipe/blender/build_scene.py:33`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/blender/build_scene.py#L33) | Millimetres to metres scale | mm | m | No (module constant) | `MM_TO_M = 0.001` | Migrate to `units.M_PER_MM` |
| [`src/archpipe/blender/build_scene.py:36-38`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/blender/build_scene.py#L36-L38) | Millimetres to metres helper | mm | m | Yes (local helper) | `build_scene.m(mm)` | Migrate to `units.mm_to_m` |
| [`src/archpipe/solar.py:91`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/solar.py#L91) | Solar minutes from datetime | datetime | UTC minutes | Partial (ignores `tzinfo`) | `solar.sun_position` | Guard with `units.require_utc(when)` |
| [`src/archpipe/luminaires/eulumdat.py:144`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/luminaires/eulumdat.py#L144) | Photometric azimuth offset | EULUMDAT $C0$ | IES $0^\circ$ ($+90^\circ$) | Yes | `IES_FROM_C_OFFSET_DEG = 90.0` | Migrate to `units` constant |
| [`src/archpipe/luminaires/eulumdat.py:168-177`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/luminaires/eulumdat.py#L168-L177) | Luminous opening mm to m | mm | m | No (inline `/ 1000.0`) | None | Migrate to `units.mm_to_m` |
| [`src/archpipe/thermal.py:327-333`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/thermal.py#L327-L333) | Ladybug energy unit validation | Joules / kWh | kWh | Yes | Unit assertion (`kWh`) | Bind to `units.joules_to_kwh` |
| [`src/archpipe/thermal.py:345`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/thermal.py#L345) | Power conversion | kW | W | No (inline `* 1000.0`) | None | Migrate to `units.kw_to_w` |
| [`src/archpipe/concept/villa_landscape.py:78-80`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/concept/villa_landscape.py#L78-L80) | glTF Y-up to scene Z-up | $(x, y, z)$ | $(x, -z, y)$ | Yes | `villa_landscape.prop_world_box` | Migrate to `units.gltf_yup_to_scene_zup` |
| [`src/archpipe/furniture_orientation.py:6-16`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/furniture_orientation.py#L6-L16) | Asset front axis to layout front | glTF $+Z, -Z, +X, -X$ | Scene $-Y$ | Yes | `model_yaw` | Retain domain mapper |
| [`src/archpipe/concept/villa_furnish3d.py:43-55`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/concept/villa_furnish3d.py#L43-L55) | Local to world planar rotation | $0^\circ, 90^\circ, 180^\circ, -90^\circ$ | $(dx, dy)$ offset | Yes | `_to_world` | Retain planar rotation map |

---

## 5. Analysis of Existing Partial Boundaries

### The Name Collision Between `revit/extract_model.py` and `src/archpipe/radiance.py`
In Revit extraction:
```python
# revit/extract_model.py:52-55
def mm(value):
    """Revit internal (feet) -> millimetres. The single unit boundary."""
    return round(UnitUtils.ConvertFromInternalUnits(value, UnitTypeId.Millimeters), PRECISION)
```
In Radiance daylight calculations:
```python
# src/archpipe/radiance.py:172-174
def mm(v: float) -> float:
    """Millimetres -> metres. The only place this conversion happens."""
    return float(v) * MM_TO_M
```
Both modules label their local helper as "the single boundary", yet:
- Revit's `mm()` converts **decimal feet to millimetres**.
- Radiance's `mm()` converts **millimetres to metres**.
- Blender's `build_scene.py` introduces a third variant, `m(mm)`:
```python
# src/archpipe/blender/build_scene.py:36-38
def m(mm):
    """Millimetres -> metres. The only place this conversion happens."""
    return float(mm) * MM_TO_M
```
This semantic divergence is dangerous for developers working across Revit extraction, daylight simulation, and scene building. A single typed boundary eliminates this ambiguity.

### The Thermal 3.6 Million Energy Defect (`l0182`)
EnergyPlus records energy results in Joules ($\text{J}$). The physical relationship between Joules and kilowatt-hours is:
```latex
1\text{ kWh} = 1000\text{ W} \times 3600\text{ s} = 3,600,000\text{ J} = 3.6 \times 10^6\text{ J}
```
Ladybug Tools' `SQLiteResult` collection reader automatically divides raw EnergyPlus Joules by $3,600,000$ to emit data with `unit: kWh`.
When downstream consumers assumed the numbers were raw Joules, they applied an additional division by $3.6 \times 10^6$:
```latex
E_{\text{erroneous}} = \frac{E_{\text{ladybug}}}{3,600,000} = \frac{E_{\text{sim}}}{(3,600,000)^2}
```
An annual cooling load of $36\text{ GJ}$ ($10,000\text{ kWh}$) became $0.002778\text{ kWh}$, collapsing to zero.
In [`src/archpipe/units.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/units.py#L96), `joules_to_kwh(joules)` and `kwh_to_joules(kwh)` formalize the exact factor $3,600,000.0$.

### The Solar UTC Datetime Contract (`l0473`)
[`src/archpipe/solar.py:91`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/solar.py#L91) calculates:
```python
minutes_utc = when.hour * 60 + when.minute + when.second / 60
```
This directly accesses `when.hour`. If a caller passes Cairo local time (UTC+2) at 09:30 AM with `tzinfo` attached, `when.hour` is `9` rather than the UTC hour `7`. This advances the solar hour angle by $2\text{ hours} \times 15^\circ/\text{hr} = 30^\circ$, producing an $81^\circ$ sun altitude error.
[`require_utc(dt)`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/units.py#L114) validates that `dt` is timezone-aware with UTC offset zero, rejecting naive datetimes and aware non-UTC datetimes.

### glTF Y-up to Blender/Scene Z-up Coordinate Mapping
In glTF (right-handed, Y-up):
- $x$ represents width
- $y$ represents vertical elevation (up)
- $z$ represents depth (forward/back)

In Blender and scene coordinates (right-handed, Z-up):
- $x$ represents width
- $y$ represents depth
- $z$ represents vertical elevation (up)

The established point transformation in [`src/archpipe/concept/villa_landscape.py:78-80`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/concept/villa_landscape.py#L78-L80) maps:
```latex
\begin{pmatrix} x_{\text{scene}} \\ y_{\text{scene}} \\ z_{\text{scene}} \end{pmatrix} = \begin{pmatrix} x_{\text{gltf}} \\ -z_{\text{gltf}} \\ y_{\text{gltf}} \end{pmatrix}
```
For bounding box extents $[gx_0, gx_1]$, $[gy_0, gy_1]$, $[gz_0, gz_1]$, the resulting scene bounds are:
```latex
\begin{aligned}
lx_0 &= gx_0, & lx_1 &= gx_1 \\
ly_0 &= -gz_1, & ly_1 &= -gz_0 \\
lz_0 &= gy_0, & lz_1 &= gy_1
\end{aligned}
```
For `sf_frangipani` recorded in [`ops/workstation/library-manifest.json`](file:///C:/Users/mmbka/arch-pipeline-agy2/ops/workstation/library-manifest.json):
- Native bounds: min `[-1.5852, 0.0, -2.0063]`, max `[2.3004, 2.7685, 1.5307]`
- Native extents: width $3.8856\text{ m}$, height $2.7685\text{ m}$, depth $3.537\text{ m}$.
- Transformed scene bounds:
  - $x \in [-1.5852, 2.3004]$ (width $3.8856\text{ m}$)
  - $y \in [-1.5307, 2.0063]$ (depth $3.537\text{ m}$)
  - $z \in [0.0, 2.7685]$ (height $2.7685\text{ m}$)
The helper [`gltf_yup_to_scene_zup(x, y, z)`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/units.py#L137) encapsulates this transformation.

---

## 6. The Single Typed Boundary: archpipe.units

The single boundary [`src/archpipe/units.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/units.py) exports:
- **Constants**:
  - `M_PER_FOOT = 0.3048` (exact, NIST SP 811)
  - `MM_PER_FOOT = 304.8` (exact)
  - `FEET_PER_M = 1.0 / 0.3048`
  - `FEET_PER_MM = 1.0 / 304.8`
  - `MM_PER_M = 1000.0`
  - `M_PER_MM = 0.001`
  - `MM_PER_INCH = 25.4` (exact)
  - `INCHES_PER_MM = 1.0 / 25.4`
  - `JOULES_PER_KWH = 3_600_000.0` (exact)
  - `KWH_PER_JOULE = 1.0 / 3_600_000.0`
- **Functions**:
  - `mm_to_ft(val)` / `ft_to_mm(val)`
  - `m_to_mm(val)` / `mm_to_m(val)`
  - `m_to_ft(val)` / `ft_to_m(val)`
  - `in_to_mm(val)` / `mm_to_in(val)`
  - `joules_to_kwh(val)` / `kwh_to_joules(val)`
  - `require_utc(dt)`
  - `gltf_yup_to_scene_zup(x, y, z)`

---

## 7. Static Guard & Fail-Closed Enforcement

[`src/archpipe/units_guard.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/units_guard.py) scans Python sources in `src/archpipe`, `revit`, and `scripts` using the Python standard library `tokenize` module to inspect code rather than raw text:

1. **Tokenize Code Inspection**:
   Only `NUMBER` tokens matching the conversion values (`304.8`, `0.3048`, `3.28084`, `25.4`) are evaluated. Comments, docstrings, and ordinary string literals are tokenized as `COMMENT` or `STRING` and stay quiet. On Python 3.12+, expression parts within f-strings yield `NUMBER` tokens and are properly flagged (e.g. `{diag / 25.4:.0f}`).
2. **Multiplication and Division Operand Rule**:
   A target `NUMBER` token is flagged if and only if it is an operand of multiplication or division:
   - The previous significant token or next significant token is one of `*`, `/`, `//`, `*=`, `/=`.
   - `NL` (non-logical newline) and `COMMENT` tokens are skipped when determining neighbouring tokens.
   - Unary signs (`+`, `-`) preceding the literal are inspected: a bare coordinate such as `-25.4` passed to a function call has previous token `-` and next token `,` (neither being a multiplicative operator) and stays quiet.
3. **Known Blind Spot**:
   A conversion constant assigned alone without inline arithmetic (e.g. `FEET_TO_M = 0.3048` or a dictionary entry `scales = {'ft': 304.8}`) is not an operand of `*` or `/` at assignment time. The guard does not perform cross-variable dataflow tracking; such isolated definitions stay quiet unless/until multiplied or divided downstream.
4. **Fail-Closed Discipline**:
   Any file or directory that is missing, unreadable, undecodable, or fails tokenization (e.g. syntax error or unclosed string) raises `UnreadableInputError` (fail closed); files are never silently skipped. A missing or corrupt allowlist also raises `UnreadableInputError`. Unallowlisted active sites raise `UnitsConversionError`.
5. **Allowlist Mechanism**:
   Existing historical sites outside the typed boundary are registered in [`knowledge/unit-conversion-allowlist.json`](file:///C:/Users/mmbka/arch-pipeline-agy2/knowledge/unit-conversion-allowlist.json) with exact file, line text, reason, and migration targets.

---

## 8. Phase 2 Migration Roadmap

Phase 2 will migrate callers across the codebase to the typed boundary without breaking behavioral invariants:
1. `src/archpipe/safe_io.py:42`: replace raw dictionary scales with `MM_PER_FOOT` and `MM_PER_M`.
2. `src/archpipe/photometry.py:51, 174`: replace `FEET_TO_M = 0.3048` with `units.M_PER_FOOT` and `units.ft_to_m`.
3. `src/archpipe/radiance.py:118, 172-174`: replace `MM_TO_M = 0.001` and local `mm()` with `units.mm_to_m`.
4. `src/archpipe/blender/build_scene.py:33, 36-38`: replace `MM_TO_M = 0.001` and local `m()` with `units.mm_to_m`.
5. `src/archpipe/solar.py:91`: apply `units.require_utc(when)` before computing `minutes_utc`.
6. `src/archpipe/luminaires/eulumdat.py:168-177`: replace raw `/ 1000.0` with `units.mm_to_m`.
7. `src/archpipe/thermal.py:345`: replace raw `* 1000.0` with explicit power conversion.
8. Retire allowlist entries in `knowledge/unit-conversion-allowlist.json` as call sites are migrated.
