"""Tests for archpipe.units, archpipe.units_guard, and defect class C9 proofs.

Validates:
1. Exact unit conversion constants (1959 Agreement / NIST SP 811) and functions.
2. Thermal arithmetic reconstruction (l0182): 3.6 million error from EnergyPlus
   Joules vs Ladybug kWh.
3. Solar UTC validation contract (l0473): rejection of naive and aware non-UTC datetimes.
4. glTF axis conversion: gltf_yup_to_scene_zup matching villa_landscape.py:78-80 on
   real sf_frangipani asset bounds from library-manifest.json.
5. Static units guard: fail-closed detection of unallowlisted raw literals (304.8, 0.3048,
   3.28084, 25.4) as multiplication/division operands via tokenize, allowlist bypass for
   registered sites, quietness for comments/docstrings/coordinates, and fail-closed
   UnreadableInputError for unreadable or untokenizable files.
6. Guard registry registration for defect class C9.

Quick Test:
    python -m unittest tests/test_units.py

Example Usage:
    >>> import unittest
    >>> from tests.test_units import TestUnits
    >>> suite = unittest.TestLoader().loadTestsFromTestCase(TestUnits)
    >>> result = unittest.TextTestRunner().run(suite)
    >>> result.wasSuccessful()
    True
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from archpipe.units import (
    FEET_PER_M,
    FEET_PER_MM,
    INCHES_PER_MM,
    JOULES_PER_KWH,
    KWH_PER_JOULE,
    MM_PER_FOOT,
    MM_PER_INCH,
    MM_PER_M,
    M_PER_FOOT,
    M_PER_MM,
    ft_to_m,
    ft_to_mm,
    gltf_yup_to_scene_zup,
    in_to_mm,
    joules_to_kwh,
    kwh_to_joules,
    m_to_ft,
    m_to_mm,
    mm_to_ft,
    mm_to_in,
    mm_to_m,
    require_utc,
)
from archpipe.units_guard import (
    UnitsConversionError,
    UnreadableInputError,
    check_units_guard,
    findings,
)
from archpipe.guard_registry import (
    find_guards_for_lesson,
    get_guard,
)


class TestUnits(unittest.TestCase):
    """Test suite for single typed units boundary, guard, and real C9 defect proofs."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.gettempdir()) / ("archpipe-units-test-" + uuid.uuid4().hex)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 1. Exact Constants and Basic Conversions
    # -------------------------------------------------------------------------

    def test_exact_definitions_and_constants(self) -> None:
        """Verify exact physical constants defined in NIST SP 811 and reciprocal floats."""
        self.assertEqual(M_PER_FOOT, 0.3048)
        self.assertEqual(MM_PER_FOOT, 304.8)
        # FEET_PER_M is genuinely inexact in binary float (1 / 0.3048 has infinite repeating decimals)
        self.assertAlmostEqual(FEET_PER_M, 1.0 / 0.3048, places=12)
        self.assertEqual(MM_PER_M, 1000.0)
        self.assertEqual(M_PER_MM, 0.001)
        self.assertEqual(MM_PER_INCH, 25.4)
        # INCHES_PER_MM is genuinely inexact in binary float (1 / 25.4 has non-power-of-two reciprocal)
        self.assertAlmostEqual(INCHES_PER_MM, 1.0 / 25.4, places=12)
        self.assertEqual(JOULES_PER_KWH, 3_600_000.0)
        # KWH_PER_JOULE is genuinely inexact in binary float (1 / 3.6e6 has non-power-of-two reciprocal)
        self.assertAlmostEqual(KWH_PER_JOULE, 1.0 / 3_600_000.0, places=12)

    def test_length_conversions(self) -> None:
        """Verify round-trip length conversions with exact defining arithmetic."""
        self.assertEqual(ft_to_mm(1.0), 304.8)
        self.assertEqual(mm_to_ft(304.8), 1.0)
        self.assertEqual(ft_to_mm(2.5), 762.0)
        self.assertEqual(mm_to_ft(762.0), 2.5)

        self.assertEqual(m_to_mm(1.5), 1500.0)
        self.assertEqual(mm_to_m(1500.0), 1.5)

        self.assertEqual(ft_to_m(1.0), 0.3048)
        self.assertEqual(m_to_ft(0.3048), 1.0)

        self.assertEqual(in_to_mm(1.0), 25.4)
        self.assertEqual(mm_to_in(25.4), 1.0)

    # -------------------------------------------------------------------------
    # 2. Thermal Arithmetic Reconstruction (l0182)
    # -------------------------------------------------------------------------

    def test_thermal_3_6_million_error_reconstruction(self) -> None:
        """Reconstruct the arithmetic of defect l0182 (thermal results 3.6 million times too small).

        In EnergyPlus, native energy simulation results are emitted in Joules (J).
        Ladybug Tools (SQLiteResult) automatically converts Joules to kilowatt-hours (kWh)
        using the physical conversion factor:
            1 kWh = 1000 W * 3600 s = 3,600,000 J (3.6e6 J).

        Historical Defect (l0182):
        An external consumer or script assumed Ladybug outputs were in Joules and divided
        by 3,600,000 a second time. This made the results exactly 3,600,000 times too small.
        """
        joules_per_kwh = 3_600_000.0
        self.assertEqual(JOULES_PER_KWH, joules_per_kwh)

        # Simulation output: 36,000,000,000 Joules (36 GJ)
        sim_energy_joules = 36_000_000_000.0

        # Ladybug correctly converts Joules to kWh:
        ladybug_kwh = joules_to_kwh(sim_energy_joules)
        self.assertEqual(ladybug_kwh, 10_000.0)

        # Defective secondary division:
        erroneous_value = ladybug_kwh / joules_per_kwh
        self.assertAlmostEqual(erroneous_value, 0.002777777777777778, places=12)

        # The error ratio is exactly 3.6 million:
        ratio = ladybug_kwh / erroneous_value
        self.assertEqual(ratio, 3_600_000.0)

        # Inverse conversion:
        self.assertEqual(kwh_to_joules(ladybug_kwh), sim_energy_joules)

    # -------------------------------------------------------------------------
    # 3. Solar Sun Position UTC Contract (l0473)
    # -------------------------------------------------------------------------

    def test_solar_utc_contract_reconstruction(self) -> None:
        """Reconstruct solar sun_position UTC contract and prove require_utc guard (l0473).

        In solar.py, sun_position computes true solar time directly from when.hour:
            minutes_utc = when.hour * 60 + when.minute + when.second / 60
        without inspecting when.tzinfo.

        If a caller passes a timezone-aware local datetime (e.g. Cairo local time UTC+2
        at 09:30 local time), when.hour is 9 instead of 7 (UTC).
        This 2-hour hour angle error shifts the sun position by 30 degrees in hour angle,
        producing an 81-degree altitude error at 09:30.
        """
        cairo_tz = timezone(timedelta(hours=2))

        # 09:30 Cairo local time (UTC+2) is 07:30 UTC
        cairo_aware_dt = datetime(2026, 6, 21, 9, 30, 0, tzinfo=cairo_tz)
        naive_dt = datetime(2026, 6, 21, 9, 30, 0)
        valid_utc_dt = datetime(2026, 6, 21, 7, 30, 0, tzinfo=timezone.utc)

        # require_utc must accept valid UTC datetime
        self.assertEqual(require_utc(valid_utc_dt), valid_utc_dt)

        # require_utc must reject naive datetime
        with self.assertRaises(ValueError) as ctx_naive:
            require_utc(naive_dt)
        self.assertIn("naive datetime", str(ctx_naive.exception))

        # require_utc must reject aware non-UTC datetime (Cairo UTC+2)
        with self.assertRaises(ValueError) as ctx_cairo:
            require_utc(cairo_aware_dt)
        self.assertIn("offset", str(ctx_cairo.exception))

        # Prove the hour arithmetic discrepancy that caused l0473
        cairo_hour = cairo_aware_dt.hour  # 9
        utc_hour = cairo_aware_dt.astimezone(timezone.utc).hour  # 7
        hour_error = cairo_hour - utc_hour
        self.assertEqual(hour_error, 2)
        # 2 hours corresponds to 30 degrees of Earth rotation / solar hour angle
        hour_angle_degrees_error = hour_error * 15.0
        self.assertEqual(hour_angle_degrees_error, 30.0)

    # -------------------------------------------------------------------------
    # 4. glTF Axis Transformation (sf_frangipani Real Case)
    # -------------------------------------------------------------------------

    def test_gltf_yup_to_scene_zup_real_frangipani_bounds(self) -> None:
        """Verify gltf_yup_to_scene_zup on real sf_frangipani bounds from library-manifest.json.

        In glTF (right-handed, Y-up):
            x is width, y is height (up), z is depth.
        In Blender / scene (right-handed, Z-up):
            x is width, y is depth, z is height (up).
        Point mapping: (x, y, z)_gltf -> (x, -z, y)_scene.

        Matching convention in src/archpipe/concept/villa_landscape.py:78-80:
            lx0, lx1 = gx0, gx1      # scene x = gltf x
            ly0, ly1 = -gz1, -gz0    # scene y = -gltf z
            lz0, lz1 = gy0, gy1      # scene z = gltf y (height)
        """
        manifest_path = ROOT / "ops/workstation/library-manifest.json"
        self.assertTrue(manifest_path.is_file(), f"Manifest file missing: {manifest_path}")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        props = {p["id"]: p for p in manifest.get("props", [])}
        self.assertIn("sf_frangipani", props, "sf_frangipani prop not found in manifest")

        bounds_m = props["sf_frangipani"]["bounds_m"]
        gx0, gy0, gz0 = bounds_m["min"]
        gx1, gy1, gz1 = bounds_m["max"]

        # Recorded real values from ops/workstation/library-manifest.json:
        self.assertEqual(gx0, -1.5852)
        self.assertEqual(gy0, 0.0)
        self.assertEqual(gz0, -2.0063)
        self.assertEqual(gx1, 2.3004)
        self.assertEqual(gy1, 2.7685)
        self.assertEqual(gz1, 1.5307)

        # Test point transformations via helper
        pt_min = gltf_yup_to_scene_zup(gx0, gy0, gz0)
        pt_max = gltf_yup_to_scene_zup(gx1, gy1, gz1)

        self.assertEqual(pt_min, (-1.5852, 2.0063, 0.0))
        self.assertEqual(pt_max, (2.3004, -1.5307, 2.7685))

        # AABB bounds transformation matching villa_landscape.py:78-80
        lx0, lx1 = gx0, gx1
        ly0, ly1 = -gz1, -gz0
        lz0, lz1 = gy0, gy1

        # Scene bounding box extents
        scene_extent_x = lx1 - lx0
        scene_extent_y = ly1 - ly0
        scene_extent_z = lz1 - lz0

        self.assertAlmostEqual(scene_extent_x, 3.8856, places=4)
        self.assertAlmostEqual(scene_extent_y, 3.537, places=4)
        self.assertAlmostEqual(scene_extent_z, 2.7685, places=4)

        # Extents match native_extent_xyz from manifest
        native_extents = props["sf_frangipani"]["native_extent_xyz"]
        self.assertEqual(native_extents, [3.8856, 2.7685, 3.537])
        self.assertAlmostEqual(scene_extent_x, native_extents[0], places=4)
        self.assertAlmostEqual(scene_extent_y, native_extents[2], places=4)  # scene Y is native Z
        self.assertAlmostEqual(scene_extent_z, native_extents[1], places=4)  # scene Z is native Y

    # -------------------------------------------------------------------------
    # 5. Static Fail-Closed Units Guard Proofs
    # -------------------------------------------------------------------------

    def test_guard_catches_unallowlisted_multiplication(self) -> None:
        """Prove guard fails when 'x = y * 304.8' appears in a temp file."""
        test_file = self.temp_dir / "calc.py"
        test_file.write_text("def convert(y):\n    x = y * 304.8\n    return x\n", encoding="utf-8")

        res = findings(root=self.temp_dir)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["matched_literal"], "304.8")
        self.assertEqual(res[0]["line_number"], 2)

        with self.assertRaises(UnitsConversionError) as ctx:
            check_units_guard(root=self.temp_dir)
        self.assertIn("304.8", str(ctx.exception))

    def test_guard_catches_fstring_expression_division(self) -> None:
        """Prove guard flags an f-string expression containing division by a conversion literal."""
        test_file = self.temp_dir / "display.py"
        test_file.write_text('def format_screen(d):\n    return f"{d / 25.4:.0f} in"\n', encoding="utf-8")

        res = findings(root=self.temp_dir)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["matched_literal"], "25.4")
        self.assertEqual(res[0]["line_number"], 2)

        with self.assertRaises(UnitsConversionError) as ctx:
            check_units_guard(root=self.temp_dir)
        self.assertIn("25.4", str(ctx.exception))

    def test_coordinate_argument_is_quiet(self) -> None:
        """Verify that a bare coordinate argument like -25.4 in a call stays quiet."""
        test_file = self.temp_dir / "coords.py"
        test_file.write_text(
            "def place_furniture():\n"
            "    add(item('study-sofa', None, 'sofa_2seat', 6.827, -25.4, -90, h=0.85))\n",
            encoding="utf-8",
        )

        res = findings(root=self.temp_dir)
        self.assertEqual(res, [])
        check_units_guard(root=self.temp_dir)

    def test_comment_and_docstring_literals_are_quiet(self) -> None:
        """Verify that conversion literals in docstrings and comments are ignored."""
        test_file = self.temp_dir / "prose.py"
        test_file.write_text(
            '"""This module notes that feet are 304.8 mm and 1 inch is 25.4 mm."""\n'
            "# Also 0.3048 m per foot and 3.28084 ft per metre in historical notes\n"
            "x = 42\n",
            encoding="utf-8",
        )

        res = findings(root=self.temp_dir)
        self.assertEqual(res, [])
        check_units_guard(root=self.temp_dir)

    def test_guard_passes_allowlisted_exact_line(self) -> None:
        """Prove guard passes when a real conversion site matches the allowlist."""
        allowlist_file = self.temp_dir / "allowlist.json"
        allowlist_data = {
            "_metadata": {
                "description": "Test allowlist",
                "structure": "entries",
                "total_items": 1,
                "last_updated": "2026-10-06T13:30:00Z",
            },
            "entries": [
                {
                    "file": "scripts/build_sheet.py",
                    "line_number": 26,
                    "line_text": "PT_PER_MM = 72.0 / 25.4",
                    "reason": "Points per mm calculation (72 pt per inch / 25.4 mm per inch)",
                    "migration_target": "src/archpipe/units.py",
                }
            ],
        }
        allowlist_file.write_text(json.dumps(allowlist_data), encoding="utf-8")

        sheet_script = self.temp_dir / "scripts/build_sheet.py"
        sheet_script.parent.mkdir(parents=True, exist_ok=True)
        sheet_script.write_text("PT_PER_MM = 72.0 / 25.4\n", encoding="utf-8")

        res = findings(root=self.temp_dir, allowlist_path=allowlist_file)
        self.assertEqual(len(res), 0)
        check_units_guard(root=self.temp_dir, allowlist_path=allowlist_file)

    def test_guard_fails_closed_on_unreadable_file(self) -> None:
        """Prove guard raises UnreadableInputError when a file has corrupt/unreadable bytes."""
        corrupt_file = self.temp_dir / "corrupt.py"
        corrupt_file.write_bytes(b"\xff\xfe\x00\x00\x80\x81\x82")

        with self.assertRaises(UnreadableInputError):
            findings(root=self.temp_dir)

        with self.assertRaises(UnreadableInputError):
            check_units_guard(root=self.temp_dir)

    def test_guard_fails_closed_on_untokenizable_file(self) -> None:
        """Prove guard raises UnreadableInputError when a file has syntax errors / cannot be tokenized."""
        untokenizable = self.temp_dir / "bad_syntax.py"
        untokenizable.write_text("'''unclosed triple quote string\n", encoding="utf-8")

        with self.assertRaises(UnreadableInputError):
            findings(root=self.temp_dir)

        with self.assertRaises(UnreadableInputError):
            check_units_guard(root=self.temp_dir)

    def test_guard_fails_closed_on_missing_allowlist(self) -> None:
        """Prove guard raises UnreadableInputError if allowlist file is missing."""
        missing_allowlist = self.temp_dir / "nonexistent-allowlist.json"
        with self.assertRaises(UnreadableInputError):
            findings(root=self.temp_dir, allowlist_path=missing_allowlist)

    def test_guard_clean_on_active_repository(self) -> None:
        """Prove guard passes with 0 findings on the active repository codebase."""
        res = findings(root=ROOT)
        self.assertEqual(len(res), 0, f"Expected 0 unallowlisted findings, got: {res}")
        check_units_guard(root=ROOT)

    # -------------------------------------------------------------------------
    # 6. Registered Guard in Guard Registry
    # -------------------------------------------------------------------------

    def test_units_conversion_guard_registration(self) -> None:
        """Prove units_conversion_guard is registered and mapped to all C9 lesson IDs."""
        guard = get_guard("units_conversion_guard")
        self.assertIsNotNone(guard)
        self.assertEqual(guard.name, "units_conversion_guard")
        self.assertEqual(guard.tier, 2)

        # Check coverage for all 7 C9 lessons
        c9_lessons = ("l0012", "l0023", "l0114", "l0182", "l0409", "l0473", "l0669")
        for lid in c9_lessons:
            matching = find_guards_for_lesson(lid)
            self.assertTrue(
                any(g.name == "units_conversion_guard" for g in matching),
                f"units_conversion_guard not found for lesson {lid}",
            )

        # Run registered guard on real failing case
        real_res = guard.run_case("real")
        self.assertTrue(real_res.passed, f"Real case failed: {real_res.error_message}")
        self.assertTrue(real_res.fired, "Real case did not fire")

        # Run registered guard on clean quiet case
        clean_res = guard.run_case("clean")
        self.assertTrue(clean_res.passed, f"Clean case failed: {clean_res.error_message}")
        self.assertFalse(clean_res.fired, "Clean case fired unexpectedly")
