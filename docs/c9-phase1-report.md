---
Document Outline:
  - "[1. Executive Summary](#1-executive-summary)"
  - "[2. Inventory Counts & Findings](#2-inventory-counts--findings)"
  - "[3. Single Typed Boundary API (archpipe.units)](#3-single-typed-boundary-api-archpipeunits)"
  - "[4. Static Guard Behaviour (archpipe.units_guard)](#4-static-guard-behaviour-archpipeunitsguard)"
  - "[5. Real-Case Proofs & Reconstruction Arithmetic](#5-real-case-proofs--reconstruction-arithmetic)"
  - "[6. Guard Registry Registration](#6-guard-registry-registration)"
  - "[7. Phase 2 Migration Roadmap](#7-phase-2-migration-roadmap)"
  - "[8. Open Questions & Technical Observations](#8-open-questions--technical-observations)"
  - "[9. Exact List of Modified & Created Files](#9-exact-list-of-modified--created-files)"
  - "[10. Fix Round 1: Tokenize Scanner and Exact Arithmetic](#10-fix-round-1-tokenize-scanner-and-exact-arithmetic)"
Executive Summary: |
  This report documents the completion of Phase 1 for Defect Class C9 ("coordinate or unit conversion scattered").
  It delivers the complete conversion inventory, the single typed boundary archpipe.units, the fail-closed static guard archpipe.units_guard,
  exact mathematical reconstructions and unit tests for historical defects (thermal 3.6e6, solar UTC, glTF axes), and registers the C9 guard in the project guard registry.
---

# Defect Class C9: Phase 1 Completion Report

## 1. Executive Summary

Phase 1 of Defect Class C9 (*coordinate or unit conversion scattered*) has been completed following the project discipline: **prevent by construction > fail-closed check > process step**.

All requirements of the Phase 1 specification have been implemented and documented:
1. **Inventory**: Audited [`src/archpipe`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe), [`revit/`](file:///C:/Users/mmbka/arch-pipeline-agy2/revit), and [`scripts/`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts) for all conversion sites (length, energy, photometric azimuth, solar time, and coordinate frames). Documented findings in [`docs/units-and-frames.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/units-and-frames.md).
2. **Single Typed Boundary**: Implemented [`src/archpipe/units.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/units.py) containing exact definitions based on the 1959 International Yard and Pound Agreement (NIST SP 811), typed conversion helpers, timezone validator `require_utc(dt)`, and glTF-to-scene frame transformer `gltf_yup_to_scene_zup(x, y, z)`.
3. **Fail-Closed Static Guard**: Implemented [`src/archpipe/units_guard.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/units_guard.py) and seeded [`knowledge/unit-conversion-allowlist.json`](file:///C:/Users/mmbka/arch-pipeline-agy2/knowledge/unit-conversion-allowlist.json) with current historical sites. Unallowlisted literals fail closed; unreadable or corrupt files raise `UnreadableInputError`.
4. **Real-Case Proofs**: Implemented [`tests/test_units.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_units.py) with exact mathematical reconstructions for thermal energy scaling ($3.6 \times 10^6$ ratio, `l0182`), solar UTC hour angle error (`l0473`), glTF axis mapping on real `sf_frangipani` bounds, and guard mutation/allowlist/error proofs.
5. **Registry Integration**: Registered `units_conversion_guard` in [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/guard_registry.py) covering all 7 C9 lessons (`l0012`, `l0023`, `l0114`, `l0182`, `l0409`, `l0473`, `l0669`).
6. **Learnings Record**: Added entry `units-and-frames-phase1` to [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/LEARNINGS.md).

---

## 2. Inventory Counts & Findings

### Summary Counts
- **Total Conversion Sites Inventoried**: 21 sites across [`src/archpipe`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe), [`revit/`](file:///C:/Users/mmbka/arch-pipeline-agy2/revit), and [`scripts/`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts).
- **Sites Currently Outside a Shared Typed Boundary**: 15 sites (using local helper functions, module constants, or inline arithmetic).
- **Raw Literal Occurrences Scanned**: 5 occurrences of `304.8` and `0.3048` across 4 files (no occurrences of `3.28084` or `25.4` exist in active code).
- **Allow-list Entries Seeded**: 5 entries in [`knowledge/unit-conversion-allowlist.json`](file:///C:/Users/mmbka/arch-pipeline-agy2/knowledge/unit-conversion-allowlist.json).

### The Five Allow-Listed Raw Literal Sites
1. [`src/archpipe/safe_io.py:40`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/safe_io.py#L40): Docstring mentioning `304.8 mm`.
2. [`src/archpipe/safe_io.py:42`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/safe_io.py#L42): `scales = {'ft': 304.8, 'mm': 1.0, 'm': 1000.0}` in `convert_length`.
3. [`src/archpipe/photometry.py:51`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/photometry.py#L51): `FEET_TO_M = 0.3048` constant in IES parser.
4. [`revit/build_bedroom.py:41`](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/build_bedroom.py#L41): Docstring explaining `304.8x wrong` Revit internal units trap.
5. [`scripts/verify.py:560`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/verify.py#L560): Comment explaining `304.8x wrong` Revit extract check.

### Semantic Collision Identified
The inventory revealed a severe naming collision between Revit extraction and daylight simulation:
- [`revit/extract_model.py:52`](file:///C:/Users/mmbka/arch-pipeline-agy2/revit/extract_model.py#L52): `def mm(value)` converts **decimal feet to millimetres**.
- [`src/archpipe/radiance.py:172`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/radiance.py#L172): `def mm(v)` converts **millimetres to metres**.
- [`src/archpipe/blender/build_scene.py:36`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/blender/build_scene.py#L36): `def m(mm)` converts **millimetres to metres**.

Both modules claim to be "the only place this conversion happens", creating confusion across subsystems.

---

## 3. Single Typed Boundary API (`archpipe.units`)

[`src/archpipe/units.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/units.py) establishes the authoritative boundary:

### Physical Constants (NIST SP 811 / International Agreement 1959)
```python
M_PER_FOOT: float = 0.3048              # Exact definition
MM_PER_FOOT: float = 304.8             # Exact definition
FEET_PER_M: float = 1.0 / 0.3048
FEET_PER_MM: float = 1.0 / 304.8

MM_PER_M: float = 1000.0
M_PER_MM: float = 0.001

MM_PER_INCH: float = 25.4              # Exact definition
INCHES_PER_MM: float = 1.0 / 25.4

JOULES_PER_KWH: float = 3_600_000.0    # 1000 W * 3600 s exact
KWH_PER_JOULE: float = 1.0 / 3_600_000.0
```

### Typed Conversion Functions
- `mm_to_ft(val: float) -> float`: `val / MM_PER_FOOT`
- `ft_to_mm(val: float) -> float`: `val * MM_PER_FOOT`
- `m_to_mm(val: float) -> float`: `val * MM_PER_M`
- `mm_to_m(val: float) -> float`: `val * M_PER_MM`
- `m_to_ft(val: float) -> float`: `val * FEET_PER_M`
- `ft_to_m(val: float) -> float`: `val * M_PER_FOOT`
- `in_to_mm(val: float) -> float`: `val * MM_PER_INCH`
- `mm_to_in(val: float) -> float`: `val * INCHES_PER_MM`
- `joules_to_kwh(val: float) -> float`: `val / JOULES_PER_KWH`
- `kwh_to_joules(val: float) -> float`: `val * JOULES_PER_KWH`

### Contract Validator: `require_utc`
```python
def require_utc(dt: datetime) -> datetime:
    """Enforce timezone-aware UTC datetime (offset 0). Raises ValueError on naive or non-UTC."""
```

### Frame Helper: `gltf_yup_to_scene_zup`
```python
def gltf_yup_to_scene_zup(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Right-handed glTF Y-up (x, y, z) to right-handed scene Z-up (x, -z, y)."""
    return (float(x), -float(z), float(y))
```
Matches the convention cited from [`src/archpipe/concept/villa_landscape.py:78-80`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/concept/villa_landscape.py#L78-L80).

---

## 4. Static Guard Behaviour (`archpipe.units_guard`)

[`src/archpipe/units_guard.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/units_guard.py) enforces that no new scattered conversion literals enter the codebase:
- **Scan Targets**: Scans all `.py` files under `src/archpipe`, `revit`, and `scripts`. Excludes [`src/archpipe/units.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/units.py).
- **Regex**: `(?<![0-9.])(?:304\.8|0\.3048|3\.28084|25\.4)(?![0-9.])`.
- **Allowlist Matching**: Compares `(relative_file_path, line.strip())` against [`knowledge/unit-conversion-allowlist.json`](file:///C:/Users/mmbka/arch-pipeline-agy2/knowledge/unit-conversion-allowlist.json).
- **Fail Closed Discipline**:
  - Missing or unreadable root directory raises `UnreadableInputError`.
  - Missing, unreadable, or invalid allowlist JSON raises `UnreadableInputError`.
  - Any file that cannot be decoded as UTF-8 raises `UnreadableInputError`.
  - Any unallowlisted literal raises `UnitsConversionError(ValueError)` with a complete report of line numbers and content.

---

## 5. Real-Case Proofs & Reconstruction Arithmetic

All proofs in [`tests/test_units.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_units.py) use exact mathematical reconstructions from project defect records:

### 1. Thermal 3.6 Million Error Reconstruction (`l0182`)
- **Physics**: EnergyPlus records energy consumption in Joules ($\text{J}$).
  ```latex
  1\text{ kWh} = 1000\text{ W} \times 3600\text{ s} = 3,600,000\text{ J} = 3.6 \times 10^6\text{ J}
  ```
- **Reconstruction**:
  - Simulation energy output: $E_{\text{sim}} = 36,000,000,000\text{ J}$ ($36\text{ GJ}$).
  - Ladybug `SQLiteResult` collection reader converted Joules to $\text{kWh}$:
    ```latex
    E_{\text{ladybug}} = \frac{36,000,000,000\text{ J}}{3,600,000\text{ J/kWh}} = 10,000.0\text{ kWh}
    ```
  - Defective secondary division:
    ```latex
    E_{\text{erroneous}} = \frac{10,000.0\text{ kWh}}{3,600,000} = 0.002777777777777778\text{ kWh}
    ```
  - Exact ratio:
    ```latex
    \frac{E_{\text{ladybug}}}{E_{\text{erroneous}}} = 3,600,000.0\quad (3.6\text{ million})
    ```
- **Proof**: `test_thermal_3_6_million_error_reconstruction` proves that `joules_to_kwh` and `kwh_to_joules` preserve exact physical equivalence and prevent redundant conversions.

### 2. Solar UTC Contract Reconstruction (`l0473`)
- **Cause**: [`src/archpipe/solar.py:91`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/solar.py#L91) computed `minutes_utc = when.hour * 60 + when.minute + when.second / 60` directly from `when.hour`.
- **Reconstruction**:
  - Passing Cairo local time (UTC+2) at 09:30 AM (`2026-06-21 09:30:00+02:00`):
    - Caller local hour: $9$
    - True UTC hour: $7$
    - Hour discrepancy: $9 - 7 = 2\text{ hours}$
    - Earth rotation / hour angle error: $2\text{ hr} \times 15^\circ/\text{hr} = 30^\circ$
    - Resulted in calculated solar altitude off by $81^\circ$.
- **Proof**: `test_solar_utc_contract_reconstruction` proves that `require_utc(dt)` accepts valid UTC datetimes, raises `ValueError` on naive datetimes, and raises `ValueError` on aware non-UTC datetimes.

### 3. glTF Frame Conversion on Real `sf_frangipani` Asset
- **Asset**: `sf_frangipani` from [`ops/workstation/library-manifest.json`](file:///C:/Users/mmbka/arch-pipeline-agy2/ops/workstation/library-manifest.json).
- **Native Bounds (glTF Y-up)**:
  - min: `[-1.5852, 0.0, -2.0063]`
  - max: `[2.3004, 2.7685, 1.5307]`
  - native extent: `[3.8856, 2.7685, 3.537]`
- **Transformed Bounds (Scene Z-up)** via `gltf_yup_to_scene_zup`:
  - $x_{\text{scene}} = x_{\text{gltf}} \in [-1.5852, 2.3004]$ (width $3.8856\text{ m}$)
  - $y_{\text{scene}} = -z_{\text{gltf}} \in [-1.5307, 2.0063]$ (depth $3.537\text{ m}$)
  - $z_{\text{scene}} = y_{\text{gltf}} \in [0.0, 2.7685]$ (height $2.7685\text{ m}$)
- **Proof**: `test_gltf_yup_to_scene_zup_real_frangipani_bounds` verifies exact mathematical agreement with [`src/archpipe/concept/villa_landscape.py:78-80`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/concept/villa_landscape.py#L78-L80).

### 4. Static Guard Proofs
- `test_guard_catches_unallowlisted_literal`: Temp directory with `x = 304.8` raises `UnitsConversionError`.
- `test_guard_passes_allowlisted_literal`: Allowlisted mock `scales = {'ft': 304.8, ...}` passes quietly.
- `test_guard_fails_closed_on_unreadable_file`: Corrupt byte sequence raises `UnreadableInputError`.
- `test_guard_fails_closed_on_missing_allowlist`: Missing allowlist file raises `UnreadableInputError`.
- `test_guard_clean_on_active_repository`: Scans current active repository and returns $0$ findings.

---

## 6. Guard Registry Registration

Registered in [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/guard_registry.py):
```python
register_guard(
    fn=_guard_c9_units_conversion,
    name="units_conversion_guard",
    lesson_ids=(
        "l0012-directshape-rotation-bak", "l0012",
        "l0023-revit-s-viewdirection", "l0023",
        "l0114-converted-ldt-agreed", "l0114",
        "l0182-thermal-results-3", "l0182",
        "l0409-section-drawn-mirrored", "l0409",
        "l0473-solar-sun-position", "l0473",
        "l0669-parents-bed-rendered", "l0669",
    ),
    real_case=case(ROOT / "tests/fixtures/c9_unallowlisted_case"),
    clean_case=case(ROOT),
    expected_real=UnitsConversionError,
    expected_clean=True,
    tier=2,
    description="Fails closed on raw unit conversion literals (304.8, 0.3048, 3.28084, 25.4) outside units boundary (C9)",
)
```
- Real failing case uses frozen fixture [`tests/fixtures/c9_unallowlisted_case/bad_code.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/fixtures/c9_unallowlisted_case/bad_code.py).
- Clean case uses repository `ROOT` which passes quietly.
- Coverage audit in `guard_registry` now tracks all 7 C9 lessons as covered by `units_conversion_guard`.

---

## 7. Phase 2 Migration Roadmap

Phase 1 established the boundary and static guard without refactoring existing callers. Phase 2 will execute the planned migrations:
1. `src/archpipe/safe_io.py:42`: replace raw dictionary scales with `MM_PER_FOOT` and `MM_PER_M`.
2. `src/archpipe/photometry.py:51, 174`: replace `FEET_TO_M = 0.3048` with `units.M_PER_FOOT` and `units.ft_to_m`.
3. `src/archpipe/radiance.py:118, 172-174`: replace `MM_TO_M = 0.001` and local `mm()` with `units.mm_to_m`.
4. `src/archpipe/blender/build_scene.py:33, 36-38`: replace `MM_TO_M = 0.001` and local `m()` with `units.mm_to_m`.
5. `src/archpipe/solar.py:49, 91`: apply `units.require_utc(when)` at the entry point of `sun_position`.
6. `src/archpipe/luminaires/eulumdat.py:168-177`: replace raw `/ 1000.0` with `units.mm_to_m`.
7. `src/archpipe/thermal.py:345`: replace raw `* 1000.0` with explicit power conversion.
8. `knowledge/unit-conversion-allowlist.json`: retire allowlist entries as migration checkpoints are completed.

---

## 8. Open Questions & Technical Observations

1. **Revit IronPython Compatibility**:
   `revit/build_bedroom.py` and `revit/extract_model.py` run under IronPython 2.7 / pyRevit. While they currently wrap Revit's native `UnitUtils.ConvertToInternalUnits` / `ConvertFromInternalUnits`, any future migration to import `archpipe.units` in native Revit scripts must preserve IronPython 2.7 syntax compatibility (avoiding Python 3.10+ match statements or type union operators `|`).
2. **`solar.py` Caller Migration**:
   In Phase 2, when `require_utc(when)` is integrated into `solar.sun_position`, all callers (e.g. `scripts/villa_daylight_finished.py`, `src/archpipe/concept/villa_landscape.py`) must be verified to ensure they pass aware UTC datetimes (e.g. using `datetime.now(timezone.utc)` or explicit `timezone.utc`).

---

## 9. Exact List of Modified & Created Files

The following 10 files were created or modified during Phase 1:

### Created Files
1. [`src/archpipe/units.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/units.py)
2. [`src/archpipe/units_guard.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/units_guard.py)
3. [`knowledge/unit-conversion-allowlist.json`](file:///C:/Users/mmbka/arch-pipeline-agy2/knowledge/unit-conversion-allowlist.json)
4. [`tests/fixtures/c9_unallowlisted_case/bad_code.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/fixtures/c9_unallowlisted_case/bad_code.py)
5. [`tests/test_units.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_units.py)
6. [`docs/units-and-frames.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/units-and-frames.md)
7. [`docs/c9-phase1-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/c9-phase1-report.md)

### Modified Files
8. [`src/archpipe/guard_registry.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/guard_registry.py)
9. [`docs/guard-registry.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/guard-registry.md)
10. [`docs/LEARNINGS.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/LEARNINGS.md)

---

## 10. Fix Round 1: Tokenize Scanner and Exact Arithmetic

### 10.1 Lead Test Failures Diagnosis
During verification of the initial Phase 1 delivery, running `scripts/run_tests.py tests.test_units tests.test_guard_registry` resulted in 4 failures across 21 tests:
1. `test_guard_clean_on_active_repository`, `test_units_conversion_guard_registration`, and `test_registered_guards_run_on_both_cases`:
   The raw regex text scanner reported 7 false-positive or unallowlisted findings:
   - `revit/build_test_model.py:7`: Docstring prose containing `"by a factor of 304.8"`.
   - `revit/place_families_test.py:30`: Comment prose containing `"304.8x wrong"`.
   - `scripts/build_sheet.py:26`: Real conversion literal `PT_PER_MM = 72.0 / 25.4` missing from allowlist.
   - `src/archpipe/concept/villa_furnish.py:349`: Bare y-coordinate `-25.4` passed as call argument in metres, not a unit conversion.
   - `src/archpipe/guard_registry.py:911`: Guard description string literal mentioning conversion numbers.
   - `src/archpipe/rules.py:1212`: Real inch conversion inside f-string expression `{diag / 25.4:.0f}` missing from allowlist.
   - `src/archpipe/units_guard.py:4`: Docstring mentioning conversion numbers.
2. `test_length_conversions`:
   `mm_to_in(25.4)` returned `0.9999999999999999` instead of `1.0` due to multiplying by the reciprocal `INCHES_PER_MM = 1.0 / 25.4` rather than dividing by the exact defining constant `MM_PER_INCH = 25.4`.

### 10.2 Implemented Design Changes
1. **Code Tokenization via `tokenize`**:
   [`src/archpipe/units_guard.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/units_guard.py) now parses source code with Python's standard `tokenize` module, evaluating only `NUMBER` tokens. Comments, docstrings, ordinary string literals, and function annotations are represented as `COMMENT` or `STRING` tokens and stay completely quiet. On Python 3.12+, expression parts of f-strings yield `NUMBER` tokens and are properly inspected. Any file that cannot be read or tokenized raises `UnreadableInputError` (fail closed).
2. **Multiplication and Division Operand Rule**:
   A target `NUMBER` token is flagged if and only if it is an operand of multiplication or division:
   - The previous or next significant token (skipping `NL` and `COMMENT`) is in `CONVERSION_OPERATORS = {"*", "/", "//", "*=", "/="}`.
   - Unary signs (`+`, `-`) are inspected: a coordinate such as `-25.4` passed to a function call has previous token `-` and next token `,` (neither being a multiplicative operator) and stays quiet.
   - Known blind spot documented in [`docs/units-and-frames.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/units-and-frames.md): an isolated constant assigned alone without arithmetic (e.g. `FEET_TO_M = 0.3048`) is not an operand of `*` or `/` at assignment and stays quiet until used in arithmetic.
3. **Inventory Re-check and Allow-listing**:
   - `scripts/build_sheet.py:26`: `PT_PER_MM = 72.0 / 25.4` allowlisted with reason and migration target.
   - `src/archpipe/rules.py:1212`: `f"{s.id} sits {d:.0f} mm from the {diag / 25.4:.0f} in screen {tv.id}; UHD viewing wants "` allowlisted with reason and migration target.
   - Full repository re-scan confirmed that no other multiplicative conversion literals exist outside the typed boundary.
4. **Exact Defining Arithmetic in `archpipe.units`**:
   Updated all functions in [`src/archpipe/units.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/units.py) to divide or multiply by the exact defining constants (`MM_PER_INCH = 25.4`, `MM_PER_FOOT = 304.8`, `M_PER_FOOT = 0.3048`, `MM_PER_M = 1000.0`):
   - `mm_to_in(val)`: `val / MM_PER_INCH` -> `mm_to_in(25.4) == 1.0` exactly.
   - `in_to_mm(val)`: `val * MM_PER_INCH` -> `in_to_mm(1.0) == 25.4` exactly.
   - `m_to_ft(val)`: `val / M_PER_FOOT` -> `m_to_ft(0.3048) == 1.0` exactly.
   - `ft_to_m(val)`: `val * M_PER_FOOT` -> `ft_to_m(1.0) == 0.3048` exactly.
   - `mm_to_m(val)`: `val / MM_PER_M` -> `mm_to_m(1000.0) == 1.0` exactly.
   - `assertAlmostEqual` is preserved exclusively for inexact reciprocal constants (`FEET_PER_M`, `INCHES_PER_MM`, `KWH_PER_JOULE`).
5. **New Unit Tests**:
   Added regression coverage to [`tests/test_units.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_units.py):
   - `test_coordinate_argument_is_quiet`: `-25.4` in function call produces 0 findings.
   - `test_comment_and_docstring_literals_are_quiet`: Literals in comments/docstrings produce 0 findings.
   - `test_guard_catches_unallowlisted_multiplication`: `x = y * 304.8` is flagged and raises `UnitsConversionError`.
   - `test_guard_catches_fstring_expression_division`: `f"{d / 25.4:.0f}"` is flagged and raises `UnitsConversionError`.
   - `test_guard_passes_allowlisted_exact_line`: Real conversion matching allowlist passes cleanly.
   - `test_guard_fails_closed_on_unreadable_file`: Corrupt bytes raise `UnreadableInputError`.
   - `test_guard_fails_closed_on_untokenizable_file`: Unclosed triple-quote raises `UnreadableInputError`.
   - `test_guard_clean_on_active_repository`: Scans current repository with 0 findings.

### 10.3 Clean Repository Allow-List Walkthrough
Reading through each allow-listed site against the active repository confirms zero findings:
- [`scripts/build_sheet.py:26`](file:///C:/Users/mmbka/arch-pipeline-agy2/scripts/build_sheet.py#L26): Line `PT_PER_MM = 72.0 / 25.4` matches allowlist entry; bypassed.
- [`src/archpipe/rules.py:1212`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/rules.py#L1212): Line `f"{s.id} sits {d:.0f} mm from the {diag / 25.4:.0f} in screen {tv.id}; UHD viewing wants "` matches allowlist entry; bypassed.
- [`src/archpipe/safe_io.py:42`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/safe_io.py#L42): `scales = {'ft': 304.8, 'mm': 1.0, 'm': 1000.0}` is an isolated dictionary definition (not operand of `*` or `/`) and matches allowlist entry; bypassed.
- [`src/archpipe/photometry.py:51`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/photometry.py#L51): `FEET_TO_M = 0.3048` is an isolated constant assignment (not operand of `*` or `/`) and matches allowlist entry; bypassed.

### 10.4 Files Actually Changed in Fix Round 1
The following 6 files were modified during Fix Round 1:
1. [`src/archpipe/units.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/units.py)
2. [`src/archpipe/units_guard.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/src/archpipe/units_guard.py)
3. [`knowledge/unit-conversion-allowlist.json`](file:///C:/Users/mmbka/arch-pipeline-agy2/knowledge/unit-conversion-allowlist.json)
4. [`tests/test_units.py`](file:///C:/Users/mmbka/arch-pipeline-agy2/tests/test_units.py)
5. [`docs/units-and-frames.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/units-and-frames.md)
6. [`docs/c9-phase1-report.md`](file:///C:/Users/mmbka/arch-pipeline-agy2/docs/c9-phase1-report.md)

