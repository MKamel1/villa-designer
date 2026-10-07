"""Tests for material basis and optical record verification (Class C7).

Validates that:
1. Every rule fires on frozen real historical reproductions across C7 lessons:
   - l0016: solid magenta plant box lacking texture asset
   - l0028: Revit paint hue lacking measured optical reflectance record
   - l0049: extracted glass solid lacking transmittance record
   - l0062: emissive fixture color contradicting declared CCT
   - l0064: pure red CAD shade saturated channel
   - l0065: ivory bedding with low reflectance rendering grey
   - l0083: wood veneer lacking declared grain orientation axis
   - l0084: dark bronze specified with excessive pale tan reflectance
   - l0795: wood grain axis rotation collapsing projection span on horizontal surfaces
   - l0891: artificial grass rendered as flat untextured plane
   - l0900: luminaire diffuser using refractive glass instead of translucent opal
   - l0910: ensuite bath screen with single interface causing total internal reflection
2. Every real defect has a renamed/translated sibling case that also fires.
3. Current production materials stay quiet under assert_material_basis and match
   the frozen known-findings baseline (tests/fixtures/c7_known_findings.json).
4. Unreadable or corrupt inputs fail closed across all entry paths.

Quick Test:
    python -m unittest tests/test_material_basis.py

Example Usage:
    >>> import unittest
    >>> from tests.test_material_basis import TestMaterialBasis
    >>> suite = unittest.TestLoader().loadTestsFromTestCase(TestMaterialBasis)
    >>> result = unittest.TextTestRunner().run(suite)
    >>> result.wasSuccessful()
    True
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from archpipe.concept.villa_render import M as PRODUCTION_MATERIALS
from archpipe.material_basis import (
    UnreadableInputError,
    assert_material_basis,
    material_findings,
)


class TestMaterialBasis(unittest.TestCase):
    """Test suite for material appearance basis and physical plausible checks."""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.gettempdir()) / ("archpipe-mat-test-" + uuid.uuid4().hex)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.baseline_path = ROOT / "tests/fixtures/c7_known_findings.json"

    def tearDown(self) -> None:
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # l0016: Solid magenta box
    # -------------------------------------------------------------------------
    def test_l0016_solid_magenta_box_fires_and_sibling(self) -> None:
        """l0016: solid magenta plant box placeholder is rejected as unphysical CAD color."""
        real_case = {
            "materials": {
                "trellis-plant-box": {
                    "kind": "principled",
                    "base_rgb": [1.0, 0.0, 1.0],
                    "reflectance": 0.50,
                    "note": "trellis climber mass box placeholder",
                }
            }
        }
        findings = material_findings(real_case)
        self.assertTrue(any(f["lesson_id"] == "l0016" and f["severity"] == "ERROR" for f in findings))
        with self.assertRaises(ValueError) as ctx:
            assert_material_basis(real_case)
        self.assertIn("l0016", str(ctx.exception))

        # Renamed / translated sibling
        sibling_case = {
            "materials": {
                "creeper-foliage-proxy": {
                    "kind": "principled",
                    "base_rgb": [1.0, 0.0, 1.0],
                    "reflectance": 0.45,
                    "note": "procedural creeper proxy mass",
                }
            }
        }
        sib_findings = material_findings(sibling_case)
        self.assertTrue(any(f["lesson_id"] == "l0016" and f["severity"] == "ERROR" for f in sib_findings))
        with self.assertRaises(ValueError):
            assert_material_basis(sibling_case)

    # -------------------------------------------------------------------------
    # l0064: Pure red lamp shade & CAD color saturation
    # -------------------------------------------------------------------------
    def test_l0064_pure_red_cad_shade_fires_and_sibling(self) -> None:
        """l0064: pure red CAD display shade is rejected as saturated unphysical finish."""
        real_case = {
            "materials": {
                "lamp-shade-cad": {
                    "kind": "principled",
                    "base_rgb": [1.0, 0.0, 0.0],
                    "reflectance": 0.35,
                    "roughness": 0.5,
                    "note": "Revit shade cad color rescaled to 0.35",
                }
            }
        }
        findings = material_findings(real_case)
        self.assertTrue(any(f["lesson_id"] == "l0064" and f["severity"] == "ERROR" for f in findings))
        with self.assertRaises(ValueError) as ctx:
            assert_material_basis(real_case)
        self.assertIn("l0064", str(ctx.exception))

        # Sibling: pure green CAD door trim
        sibling_case = {
            "materials": {
                "door-trim-cad-green": {
                    "kind": "principled",
                    "base_rgb": [0.0, 1.0, 0.0],
                    "reflectance": 0.35,
                    "roughness": 0.5,
                    "note": "Revit door frame CAD display green",
                }
            }
        }
        sib_findings = material_findings(sibling_case)
        self.assertTrue(any(f["lesson_id"] == "l0064" and f["severity"] == "ERROR" for f in sib_findings))
        with self.assertRaises(ValueError):
            assert_material_basis(sibling_case)

    # -------------------------------------------------------------------------
    # l0083 & l0795: Wood grain orientation and collapsed rotation mapping
    # -------------------------------------------------------------------------
    def test_l0083_wood_grain_missing_axis_fires_and_sibling(self) -> None:
        """l0083: wood veneer lacking declared grain_axis fails closed."""
        real_case = {
            "materials": {
                "oak-wardrobe": {
                    "kind": "principled",
                    "asset": "white_oak_veneer",
                    "base_rgb": [0.52, 0.40, 0.27],
                    "reflectance": 0.40,
                    "tile_m": 0.50,
                    "note": "oak wardrobe doors",
                }
            }
        }
        findings = material_findings(real_case)
        self.assertTrue(any(f["lesson_id"] == "l0083" and f["severity"] == "ERROR" for f in findings))
        with self.assertRaises(ValueError) as ctx:
            assert_material_basis(real_case)
        self.assertIn("l0083", str(ctx.exception))

        # Sibling: unoriented walnut joinery
        sibling_case = {
            "materials": {
                "walnut-bookcase": {
                    "kind": "principled",
                    "asset": "natural_walnut_veneer",
                    "base_rgb": [0.20, 0.11, 0.06],
                    "reflectance": 0.12,
                    "tile_m": 1.00,
                    "note": "walnut bookcase end panels",
                }
            }
        }
        sib_findings = material_findings(sibling_case)
        self.assertTrue(any(f["lesson_id"] == "l0083" and f["severity"] == "ERROR" for f in sib_findings))

    def test_l0795_wood_grain_collapsed_span_fires_and_sibling(self) -> None:
        """l0795: grain_axis='z' on horizontal surface collapses mapping span to texel smear."""
        real_case = {
            "materials": {
                "tread-wood": {
                    "kind": "principled",
                    "asset": "natural_walnut_veneer",
                    "base_rgb": [0.20, 0.11, 0.06],
                    "reflectance": 0.12,
                    "tile_m": 1.00,
                    "grain_axis": "z",
                    "application": "horizontal",
                    "note": "stair tread top surface horizontal wood",
                }
            }
        }
        findings = material_findings(real_case)
        self.assertTrue(any(f["lesson_id"] == "l0795" and f["severity"] == "ERROR" for f in findings))
        with self.assertRaises(ValueError) as ctx:
            assert_material_basis(real_case)
        self.assertIn("l0795", str(ctx.exception))

        # Sibling: horizontal oak bed frame with grain_axis='z'
        sibling_case = {
            "materials": {
                "bed-frame-wood": {
                    "kind": "principled",
                    "asset": "white_oak_veneer",
                    "base_rgb": [0.52, 0.40, 0.27],
                    "reflectance": 0.40,
                    "tile_m": 0.50,
                    "grain_axis": "z",
                    "application": "horizontal",
                    "note": "horizontal bed frame rails",
                }
            }
        }
        sib_findings = material_findings(sibling_case)
        self.assertTrue(any(f["lesson_id"] == "l0795" and f["severity"] == "ERROR" for f in sib_findings))
        with self.assertRaises(ValueError):
            assert_material_basis(sibling_case)

    def test_l0795_scene_mesh_grain_horizontal_vs_vertical(self) -> None:
        """l0795: scene mesh with vertical grain_axis='z' on horizontal face fails, while vertical face stays quiet."""
        # Horizontal face mesh (e.g. stair tread top) fails closed reporting mesh ID
        horizontal_scene = {
            "materials": {
                "walnut-joinery": {
                    "kind": "principled",
                    "asset": "natural_walnut_veneer",
                    "base_rgb": [0.20, 0.11, 0.06],
                    "reflectance": 0.12,
                    "tile_m": 1.00,
                    "grain_axis": "z",
                    "note": "walnut veneer joinery",
                }
            },
            "meshes": [
                {
                    "id": "stair-tread-01",
                    "material": "walnut-joinery",
                    "faces": [
                        [[0.0, 0.0, 0.6], [0.9, 0.0, 0.6], [0.9, 0.28, 0.6], [0.0, 0.28, 0.6]],
                        [[0.0, 0.0, 0.54], [0.9, 0.0, 0.54], [0.9, 0.28, 0.54], [0.0, 0.28, 0.54]],
                    ],
                }
            ],
        }
        h_findings = material_findings(horizontal_scene)
        self.assertTrue(any(f["lesson_id"] == "l0795" and f.get("mesh") == "stair-tread-01" for f in h_findings))
        with self.assertRaises(ValueError) as ctx:
            assert_material_basis(horizontal_scene)
        self.assertIn("stair-tread-01", str(ctx.exception))

        # Vertical face mesh (e.g. wardrobe door front) stays quiet
        vertical_scene = {
            "materials": {
                "walnut-joinery": {
                    "kind": "principled",
                    "asset": "natural_walnut_veneer",
                    "base_rgb": [0.20, 0.11, 0.06],
                    "reflectance": 0.12,
                    "tile_m": 1.00,
                    "grain_axis": "z",
                    "note": "walnut veneer joinery",
                }
            },
            "meshes": [
                {
                    "id": "wardrobe-door-front",
                    "material": "walnut-joinery",
                    "faces": [
                        [[0.0, 0.0, 0.0], [0.0, 0.8, 0.0], [0.0, 0.8, 2.4], [0.0, 0.0, 2.4]],
                    ],
                }
            ],
        }
        v_findings = material_findings(vertical_scene)
        self.assertEqual(v_findings, [])
        self.assertEqual(assert_material_basis(vertical_scene), [])

    # -------------------------------------------------------------------------
    # l0084: Dark bronze rendered pale tan
    # -------------------------------------------------------------------------
    def test_l0084_dark_bronze_pale_tan_fires_and_sibling(self) -> None:
        """l0084: dark bronze anodised aluminium rendered with pale tan reflectance > 0.15."""
        real_case = {
            "materials": {
                "alu-bronze-historical": {
                    "kind": "principled",
                    "base_rgb": [0.55, 0.45, 0.35],
                    "reflectance": 0.42,
                    "roughness": 0.35,
                    "metallic": 1.0,
                    "note": "dark bronze anodised aluminium window frames",
                }
            }
        }
        findings = material_findings(real_case)
        self.assertTrue(any(f["lesson_id"] == "l0084" and f["severity"] == "ERROR" for f in findings))
        with self.assertRaises(ValueError) as ctx:
            assert_material_basis(real_case)
        self.assertIn("l0084", str(ctx.exception))

        # Sibling: anodised dark bronze door trim
        sibling_case = {
            "materials": {
                "dark-bronze-door-trim": {
                    "kind": "principled",
                    "base_rgb": [0.50, 0.40, 0.30],
                    "reflectance": 0.38,
                    "roughness": 0.30,
                    "metallic": 1.0,
                    "note": "dark bronze entrance door trim",
                }
            }
        }
        sib_findings = material_findings(sibling_case)
        self.assertTrue(any(f["lesson_id"] == "l0084" and f["severity"] == "ERROR" for f in sib_findings))
        with self.assertRaises(ValueError):
            assert_material_basis(sibling_case)

    # -------------------------------------------------------------------------
    # l0049 & l0910: Glass transmittance and interface count
    # -------------------------------------------------------------------------
    def test_l0049_glass_missing_transmittance_fires_and_sibling(self) -> None:
        """l0049: glass material lacking transmittance record fails closed."""
        real_case = {
            "materials": {
                "glass-unspecified": {
                    "kind": "glass",
                    "base_rgb": [1.0, 1.0, 1.0],
                    "roughness": 0.0,
                    "note": "window glass without transmittance record",
                }
            }
        }
        findings = material_findings(real_case)
        self.assertTrue(any(f["lesson_id"] == "l0049" and f["severity"] == "ERROR" for f in findings))
        with self.assertRaises(ValueError) as ctx:
            assert_material_basis(real_case)
        self.assertIn("l0049", str(ctx.exception))

        # Sibling: terrace sliding glass lacking transmittance
        sibling_case = {
            "materials": {
                "slider-glass-bare": {
                    "kind": "glass",
                    "base_rgb": [1.0, 1.0, 1.0],
                    "roughness": 0.0,
                    "note": "sliding door glass pane",
                }
            }
        }
        sib_findings = material_findings(sibling_case)
        self.assertTrue(any(f["lesson_id"] == "l0049" and f["severity"] == "ERROR" for f in sib_findings))

    def test_l0910_ensuite_bath_screen_interfaces_fires_and_sibling(self) -> None:
        """l0910: bath screen glass with interfaces=1 causes total internal reflection (mirror)."""
        real_case = {
            "materials": {
                "glass-bath-screen-single": {
                    "kind": "glass",
                    "base_rgb": [1.0, 1.0, 1.0],
                    "transmittance": 0.91,
                    "interfaces": 1,
                    "roughness": 0.0,
                    "note": "detail-pe-bath-screen single interface quad",
                }
            }
        }
        findings = material_findings(real_case)
        self.assertTrue(any(f["lesson_id"] == "l0910" and f["severity"] == "ERROR" for f in findings))
        with self.assertRaises(ValueError) as ctx:
            assert_material_basis(real_case)
        self.assertIn("l0910", str(ctx.exception))

        # Sibling: balustrade screen glass with interfaces=1
        sibling_case = {
            "materials": {
                "glass-guard-single": {
                    "kind": "glass",
                    "base_rgb": [1.0, 1.0, 1.0],
                    "transmittance": 0.85,
                    "interfaces": 1,
                    "roughness": 0.0,
                    "note": "stair glass guard single interface",
                }
            }
        }
        sib_findings = material_findings(sibling_case)
        self.assertTrue(any(f["lesson_id"] == "l0910" and f["severity"] == "ERROR" for f in sib_findings))

    # -------------------------------------------------------------------------
    # l0891: Artificial grass missing texture asset
    # -------------------------------------------------------------------------
    def test_l0891_artificial_grass_missing_asset_fires_and_sibling(self) -> None:
        """l0891: artificial grass lacking texture asset renders as flat untextured plane."""
        real_case = {
            "materials": {
                "artificial-grass": {
                    "kind": "principled",
                    "base_rgb": [0.16, 0.235, 0.105],
                    "reflectance": 0.20,
                    "roughness": 0.92,
                    "note": "drained artificial grass flat colour",
                }
            }
        }
        findings = material_findings(real_case)
        self.assertTrue(any(f["lesson_id"] == "l0891" and f["severity"] == "ERROR" for f in findings))
        with self.assertRaises(ValueError) as ctx:
            assert_material_basis(real_case)
        self.assertIn("l0891", str(ctx.exception))

        # Sibling: outdoor pad turf lacking asset
        sibling_case = {
            "materials": {
                "pad-grass-turf": {
                    "kind": "principled",
                    "base_rgb": [0.18, 0.25, 0.12],
                    "reflectance": 0.20,
                    "roughness": 0.90,
                    "note": "outdoor sport pad turf",
                }
            }
        }
        sib_findings = material_findings(sibling_case)
        self.assertTrue(any(f["lesson_id"] == "l0891" and f["severity"] == "ERROR" for f in sib_findings))

    # -------------------------------------------------------------------------
    # l0900: Island / stair-void pendant globe diffuser
    # -------------------------------------------------------------------------
    def test_l0900_pendant_globe_diffuser_glass_fires_and_sibling(self) -> None:
        """l0900: lamp diffuser globe using kind='glass' renders smoky grey without bulk scattering."""
        real_case = {
            "materials": {
                "pen-globe-glass": {
                    "kind": "glass",
                    "base_rgb": [0.97, 0.96, 0.92],
                    "transmittance": 0.70,
                    "interfaces": 2,
                    "roughness": 0.35,
                    "note": "island stair void pendant globe diffuser",
                }
            }
        }
        findings = material_findings(real_case)
        self.assertTrue(any(f["lesson_id"] == "l0900" and f["severity"] == "ERROR" for f in findings))
        with self.assertRaises(ValueError) as ctx:
            assert_material_basis(real_case)
        self.assertIn("l0900", str(ctx.exception))

        # Sibling: dining table pendant globe using glass
        sibling_case = {
            "materials": {
                "dining-globe-glass": {
                    "kind": "glass",
                    "base_rgb": [0.95, 0.95, 0.90],
                    "transmittance": 0.65,
                    "interfaces": 2,
                    "roughness": 0.30,
                    "note": "dining pendant diffuser globe",
                }
            }
        }
        sib_findings = material_findings(sibling_case)
        self.assertTrue(any(f["lesson_id"] == "l0900" and f["severity"] == "ERROR" for f in sib_findings))

    def test_l0900_translucent_globe_dark_transmittance_fires_and_sibling(self) -> None:
        """l0900: translucent diffuser globe with transmittance <= 0.40 fails glowing opal appearance."""
        real_case = {
            "materials": {
                "pen-globe-dark-translucent": {
                    "kind": "translucent",
                    "base_rgb": [0.97, 0.96, 0.92],
                    "transmittance": 0.35,
                    "roughness": 0.22,
                    "note": "island stair void translucent globe diffuser",
                }
            }
        }
        findings = material_findings(real_case)
        self.assertTrue(any(f["lesson_id"] == "l0900" and f["severity"] == "ERROR" for f in findings))
        with self.assertRaises(ValueError):
            assert_material_basis(real_case)

        sibling_case = {
            "materials": {
                "sconce-globe-dark": {
                    "kind": "translucent",
                    "base_rgb": [0.95, 0.93, 0.90],
                    "transmittance": 0.28,
                    "note": "wall sconce diffuser globe",
                }
            }
        }
        sib_findings = material_findings(sibling_case)
        self.assertTrue(any(f["lesson_id"] == "l0900" and f["severity"] == "ERROR" for f in sib_findings))

    # -------------------------------------------------------------------------
    # l0065: Ivory bedding rendered grey
    # -------------------------------------------------------------------------
    def test_l0065_ivory_bedding_reflectance_fires_and_sibling(self) -> None:
        """l0065: ivory bedding with generic furniture reflectance 0.35 renders grey."""
        real_case = {
            "materials": {
                "ivory-bedding-historical": {
                    "kind": "principled",
                    "base_rgb": [0.86, 0.83, 0.76],
                    "reflectance": 0.35,
                    "roughness": 0.6,
                    "note": "ivory bedding dressing reused 0.35 furniture reflectance",
                }
            }
        }
        findings = material_findings(real_case)
        self.assertTrue(any(f["lesson_id"] == "l0065" and f["severity"] == "ERROR" for f in findings))
        with self.assertRaises(ValueError) as ctx:
            assert_material_basis(real_case)
        self.assertIn("l0065", str(ctx.exception))

        # Sibling: white linen bedspread lacking explicit presentation reflectance
        sibling_case = {
            "materials": {
                "white-bedspread-dark": {
                    "kind": "principled",
                    "base_rgb": [0.85, 0.84, 0.80],
                    "reflectance": None,
                    "roughness": 0.65,
                    "note": "white bedding linen duvet lacking explicit reflectance",
                }
            }
        }
        sib_findings = material_findings(sibling_case)
        self.assertTrue(any(f["lesson_id"] == "l0065" and f["severity"] == "ERROR" for f in sib_findings))

    def test_garment_ivory_passes_production_textile_control(self) -> None:
        """garment-ivory (reflectance 0.55) satisfies production textile_reflectance rule and stays quiet."""
        case = {
            "materials": {
                "garment-ivory": {
                    "kind": "principled",
                    "base_rgb": [0.86, 0.83, 0.76],
                    "reflectance": 0.55,
                    "roughness": 0.6,
                    "note": "ASSUMED hanging garment fabric, ivory",
                }
            }
        }
        findings = material_findings(case)
        self.assertEqual(findings, [])
        self.assertEqual(assert_material_basis(case), [])

    # -------------------------------------------------------------------------
    # l0028: Revit paint hue missing basis
    # -------------------------------------------------------------------------
    def test_l0028_revit_paint_hue_missing_basis_fires_and_sibling(self) -> None:
        """l0028: Revit paint hue lacking measured optical reflectance record is flagged."""
        real_case = {
            "materials": {
                "revit-paint-unbacked": {
                    "kind": "principled",
                    "base_rgb": [0.75, 0.70, 0.65],
                    "reflectance": 0.70,
                    "status": "NONE",
                }
            }
        }
        findings = material_findings(real_case)
        self.assertTrue(any(f["lesson_id"] == "l0028" and f["severity"] == "ERROR" for f in findings))
        with self.assertRaises(ValueError) as ctx:
            assert_material_basis(real_case)
        self.assertIn("l0028", str(ctx.exception))

        sibling_case = {
            "materials": {
                "revit-shading-raw": {
                    "kind": "principled",
                    "base_rgb": [0.60, 0.60, 0.60],
                    "reflectance": 0.60,
                    "basis": "NONE",
                }
            }
        }
        sib_findings = material_findings(sibling_case)
        self.assertTrue(any(f["lesson_id"] == "l0028" and f["severity"] == "ERROR" for f in sib_findings))

    # -------------------------------------------------------------------------
    # l0062: Emissive CCT / colour disagreement
    # -------------------------------------------------------------------------
    def test_l0062_emissive_cct_disagreement_fires_and_sibling(self) -> None:
        """l0062: emissive base_rgb contradicting declared CCT is flagged."""
        real_case = {
            "materials": {
                "lamp-emissive-contradictory": {
                    "kind": "emissive",
                    "base_rgb": [1.0, 0.20, 0.0],
                    "cct_k": 5000,
                    "emission_lm_per_m2": 25000.0,
                    "note": "orange-tinted emissive panel declared as 5000K daylight",
                }
            }
        }
        findings = material_findings(real_case)
        self.assertTrue(any(f["lesson_id"] == "l0062" and f["severity"] == "ERROR" for f in findings))
        with self.assertRaises(ValueError) as ctx:
            assert_material_basis(real_case)
        self.assertIn("l0062", str(ctx.exception))

        # Sibling: blue-tinted emissive panel declared as warm 2700K
        sibling_case = {
            "materials": {
                "warm-sconce-blue-tint": {
                    "kind": "emissive",
                    "base_rgb": [0.0, 0.50, 1.0],
                    "cct_k": 2700,
                    "emission_lm_per_m2": 15000.0,
                    "note": "blue-tinted emissive fitting declared as 2700K warm white",
                }
            }
        }
        sib_findings = material_findings(sibling_case)
        self.assertTrue(any(f["lesson_id"] == "l0062" and f["severity"] == "ERROR" for f in sib_findings))

    # -------------------------------------------------------------------------
    # Baseline: Current production villa materials stay quiet and match baseline
    # -------------------------------------------------------------------------
    def test_production_villa_materials_stay_quiet_under_assert(self) -> None:
        """Current production villa materials stay quiet (zero ERROR findings) under assert_material_basis."""
        findings = assert_material_basis(PRODUCTION_MATERIALS)
        self.assertIsInstance(findings, list)
        errors = [f for f in findings if f.get("severity") == "ERROR"]
        self.assertEqual(errors, [])

    def test_production_villa_materials_match_frozen_baseline(self) -> None:
        """Current production villa materials match the frozen known-findings baseline exactly."""
        self.assertTrue(self.baseline_path.exists(), f"Missing baseline file: {self.baseline_path}")
        baseline_data = json.loads(self.baseline_path.read_text(encoding="utf-8"))
        expected_findings = baseline_data["findings"]

        actual_findings = material_findings(PRODUCTION_MATERIALS)

        # Compare findings count
        self.assertEqual(len(actual_findings), len(expected_findings))

        # Compare each finding record by value
        for actual, expected in zip(actual_findings, expected_findings):
            self.assertEqual(actual["material"], expected["material"])
            self.assertEqual(actual["category"], expected["category"])
            self.assertEqual(actual["severity"], expected["severity"])
            self.assertEqual(actual["lesson_id"], expected["lesson_id"])
            self.assertEqual(actual["reason"], expected["reason"])
            self.assertEqual(actual["value"], expected["value"])

    # -------------------------------------------------------------------------
    # Fail-closed on unreadable inputs
    # -------------------------------------------------------------------------
    def test_fail_closed_on_unreadable_inputs(self) -> None:
        """material_findings and assert_material_basis fail closed on missing, empty, or corrupt inputs."""
        # Non-existent file path
        with self.assertRaises(UnreadableInputError):
            material_findings(self.temp_dir / "non_existent.json")

        # Empty string path
        with self.assertRaises(UnreadableInputError):
            material_findings("")

        # Whitespace string path
        with self.assertRaises(UnreadableInputError):
            material_findings("   ")

        # Empty scene file
        empty_file = self.temp_dir / "empty.json"
        empty_file.write_text("", encoding="utf-8")
        with self.assertRaises(UnreadableInputError):
            material_findings(empty_file)

        # Corrupt JSON file
        corrupt_file = self.temp_dir / "corrupt.json"
        corrupt_file.write_text("{invalid json", encoding="utf-8")
        with self.assertRaises(UnreadableInputError):
            material_findings(corrupt_file)

        # Empty dictionary
        with self.assertRaises(UnreadableInputError):
            material_findings({})

        # Non-dict JSON root
        array_file = self.temp_dir / "array.json"
        array_file.write_text("[1, 2, 3]", encoding="utf-8")
        with self.assertRaises(UnreadableInputError):
            material_findings(array_file)

        # Unsupported type
        with self.assertRaises(UnreadableInputError):
            material_findings(12345)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
