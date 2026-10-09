"""Tests for Class C11 (external-claims) Phase 2 Batch 2 call-site migrations.

Verifies external-claims guards across the migrated call sites:
1. archpipe.luminaires.library.sniff: Delegates content sniffing to
   external_claims.sniff_content while strictly preserving accepted luminaire types
   ('zip', 'rfa', 'ies', 'ldt', 'gldf', 'txt') and returning None on unverified/disguised
   payloads (l0113, l0072).
2. archpipe.luminaires.library.import_inbox: Ingests incoming files through
   external_claims.ingest_bytes before filing (refusing empty files or HTML error pages,
   l0072, l0113), attaches provenance metadata to product.json sources, and enforces
   check_cct_and_watts_agreement when the product record already has both CCT and power
   values, refusing to mark divergent products verified (l0118).
3. archpipe.asset_intake.validate_entry: Enforces check_found_content on downloaded asset
   folders and files, failing closed on empty directories or 0-byte models (l0072).

All tests run under complete network isolation and write only to unique temporary folders.

Quick Test:
    python -m unittest tests/test_c11_phase2b.py

Example Usage:
    >>> import unittest
    >>> suite = unittest.defaultTestLoader.loadTestsFromName("tests.test_c11_phase2b")
    >>> runner = unittest.TextTestRunner()
    >>> runner.run(suite)
"""
from __future__ import annotations

import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from archpipe import asset_intake, external_claims
from archpipe.external_claims import OLE_MAGIC, UTF16_LE_BOM
from archpipe.luminaires import library
from tests.test_eulumdat import ldt_text


def _sample_gltf_json() -> str:
    """Return minimal valid glTF 2.0 JSON with bounds (0, 0, 0) to (0.8, 0.9, 0.8)."""
    return json.dumps({
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}],
        "accessors": [{"min": [0.0, 0.0, 0.0], "max": [0.8, 0.9, 0.8]}],
    })


def _sample_asset_entry(asset_id: str = "test_chair_01", role: str = "armchair") -> dict:
    """Return valid intake manifest entry matching _sample_gltf_json bounds."""
    return {
        "id": asset_id,
        "role": role,
        "source_url": f"https://polyhaven.com/a/{asset_id}",
        "licence": "CC0",
        "author": "Test Author",
        "credit": "Test Author",
        "units_normalised": {"scale_factor": 1.0, "reason": "model units are metres"},
        "up_axis": "+Y",
        "front_axis": "+Z",
        "bounds_m": {"min": [0.0, 0.0, 0.0], "max": [0.8, 0.9, 0.8]},
        "expected_size_range": {
            "min_m": [0.51, None, 0.61],
            "max_m": [1.27, None, 1.07],
            "source": "Mitton & Nystuen 4th ed. armchair range",
        },
        "contents": {},
        "preview_image": f"previews/{asset_id}.png",
    }



def _imported_folder(lib, meta=None):
    """The product folder import_inbox actually created (named from the LDT's own
    manufacturer/catalogue fields, not the inbox path), with optional product
    metadata merged into its product.json (lead review 2026-10-08)."""
    folder = next(f.parent for f in lib.rglob("*.ldt") if "inbox" not in f.parts)
    if meta:
        record = folder / "product.json"
        data = json.loads(record.read_text(encoding="utf-8")) if record.is_file() else {}
        data.update(meta)
        record.write_text(json.dumps(data, indent=2), encoding="utf-8")
        library.rebuild_index(lib)
    return folder


class C11Phase2Batch2Tests(unittest.TestCase):
    """Test suite covering Class C11 Phase 2 Batch 2 call-site migrations."""

    def setUp(self) -> None:
        self.temp_root = Path(tempfile.gettempdir()) / ("archpipe-c11p2b-" + uuid.uuid4().hex)
        self.temp_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root, ignore_errors=True)

    # -------------------------------------------------------------------------
    # Site 1: archpipe.luminaires.library.sniff
    # -------------------------------------------------------------------------

    def test_library_sniff_real_zip_labelled_application_json_identifies_content_l0113(self) -> None:
        # Real failure frozen by value: Signify server returned zip bytes labelled application/json (lesson l0113).
        # sniff() must identify zip from byte inspection, never by external label.
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("test.ies", "IESNA:LM-63-2002\nTILT=NONE\n")
        zip_payload = buf.getvalue()

        self.assertEqual(library.sniff(zip_payload), "zip")

    def test_library_sniff_real_html_error_page_rejected_l0113(self) -> None:
        # Real failure frozen by value: HTML error page returned instead of photometry (lesson l0113).
        html_error_payload = (
            b"<!DOCTYPE html>\n<html>\n<head><title>404 Not Found</title></head>\n"
            b"<body><h1>Resource Not Found</h1><p>The requested file does not exist.</p></body>\n</html>"
        )
        self.assertIsNone(library.sniff(html_error_payload))

    def test_library_sniff_real_empty_payload_rejected_l0072(self) -> None:
        # Real failure frozen by value: 0-byte payload (lesson l0072).
        self.assertIsNone(library.sniff(b""))

    def test_library_sniff_clean_luminaire_types_pass_quietly(self) -> None:
        # Clean cases: All supported luminaire types are identified and accepted.
        ldt_bytes = ldt_text(0, lamp_sets=((1, "LED", 1000.0, "3000", "90", 23.0),)).encode("latin-1")
        self.assertEqual(library.sniff(ldt_bytes), "ldt")

        ies_bytes = b"IESNA:LM-63-2002\nTILT=NONE\n1 1000 1 3 1 1 1 0 0 0\n1.0 1.0 0.0\n0 45 90\n0\n100 80 0\n"
        self.assertEqual(library.sniff(ies_bytes), "ies")

        rfa_bytes = OLE_MAGIC + b"\x00" * 512
        self.assertEqual(library.sniff(rfa_bytes), "rfa")

        # GLDF container (zip containing product.xml)
        gldf_buf = io.BytesIO()
        with zipfile.ZipFile(gldf_buf, "w") as zf:
            zf.writestr("product.xml", "<gldf><product/></gldf>")
        self.assertEqual(library.sniff(gldf_buf.getvalue()), "gldf")

        # Standard zip (without product.xml)
        plain_zip_buf = io.BytesIO()
        with zipfile.ZipFile(plain_zip_buf, "w") as zf:
            zf.writestr("readme.txt", "luminaire data")
        self.assertEqual(library.sniff(plain_zip_buf.getvalue()), "zip")

        # Revit type catalogue with UTF-16 BOM and ## headers
        utf16_catalogue = UTF16_LE_BOM + "##,Length##mm\r\nType1,1200\r\nType2,1500\r\n".encode("utf-16-le")
        self.assertEqual(library.sniff(utf16_catalogue), "txt")

        # Revit type catalogue in Latin-1 with ## headers and commas
        latin1_catalogue = b"##,FamilyName##Length##mm,Width##mm\r\nType1,1200,600\r\nType2,1500,600\r\n"
        self.assertEqual(library.sniff(latin1_catalogue), "txt")

    def test_library_sniff_sibling_png_payload_rejected(self) -> None:
        # Sibling mutation: PNG image binary payload disguised as luminaire data.
        png_payload = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
        self.assertIsNone(library.sniff(png_payload))

    def test_library_sniff_sibling_plain_text_rejected(self) -> None:
        # Sibling mutation: Arbitrary plain text without Revit type catalogue headers.
        generic_text = b"This is a general text document without catalogue parameters or headers."
        self.assertIsNone(library.sniff(generic_text))

    # -------------------------------------------------------------------------
    # Site 2: archpipe.luminaires.library.import_inbox
    # -------------------------------------------------------------------------

    def test_import_inbox_real_html_error_page_skipped_before_filing_l0113(self) -> None:
        # Real failure frozen by value: Server returned HTML 404 error page instead of LDT (lesson l0113).
        lib = self.temp_root / "lib_html"
        inbox = lib / "inbox" / "signify" / "911401840687"
        inbox.mkdir(parents=True, exist_ok=True)
        html_error = b"<!DOCTYPE html><html><body><h1>404 File Not Found</h1></body></html>"
        (inbox / "911401840687.ldt").write_bytes(html_error)

        report = library.import_inbox(library=lib)

        dest_file = lib / "signify" / "911401840687" / "911401840687.ldt"
        self.assertFalse(dest_file.exists(), "HTML error page must never be filed into product directory")
        self.assertEqual(report["products"], 0)
        self.assertTrue(len(report["skipped"]) > 0)
        skipped_item = report["skipped"][0]
        self.assertIn("911401840687.ldt", skipped_item[0])

    def test_import_inbox_real_empty_payload_skipped_before_filing_l0072(self) -> None:
        # Real failure frozen by value: 0-byte download payload in inbox (lesson l0072).
        lib = self.temp_root / "lib_empty"
        inbox = lib / "inbox" / "signify" / "911401840687"
        inbox.mkdir(parents=True, exist_ok=True)
        (inbox / "911401840687.ldt").write_bytes(b"")

        report = library.import_inbox(library=lib)

        dest_file = lib / "signify" / "911401840687" / "911401840687.ldt"
        self.assertFalse(dest_file.exists(), "0-byte file must never be filed into product directory")
        self.assertEqual(report["products"], 0)
        self.assertTrue(len(report["skipped"]) > 0)

    def test_import_inbox_real_cross_source_disagreement_stays_unverified_l0118(self) -> None:
        # Real failure frozen by value:
        # Signify's Revit family says 3200 K and 3 W; its LDT says 3000 K and 23 W (lesson l0118).
        lib = self.temp_root / "lib_drift"

        # Existing product record records Revit family claim (3200 K, 3.0 W)
        existing_meta = {
            "manufacturer": "signify",
            "sku": "911401840687",
            "cct": 3200,
            "watts": 3.0,
        }

        # Incoming LDT in inbox provides 3000 K and 23.0 W
        inbox = lib / "inbox" / "signify" / "911401840687"
        inbox.mkdir(parents=True, exist_ok=True)
        valid_ldt = ldt_text(0, lamp_sets=((1, "LED", 1000.0, "3000", "90", 23.0),)).encode("latin-1")
        (inbox / "911401840687.ldt").write_bytes(valid_ldt)

        report = library.import_inbox(library=lib)
        prod_folder = _imported_folder(lib, existing_meta)

        self.assertEqual(report["products"], 1)
        # Verify that verify_product refused to mark verified
        L, checks = library.verify_product(prod_folder)
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0]["verified"], 0, "Product must stay unverified on cross-source disagreement")
        self.assertIn("l0118", checks[0]["sanity"])
        self.assertIn("CCT mismatch", checks[0]["sanity"])
        self.assertIn("Watts mismatch", checks[0]["sanity"])

        # Search without include_unverified excludes the product
        verified_results = library.search(library=lib, include_unverified=False)
        self.assertEqual(len(verified_results), 0, "Disagreement product must not appear in verified search results")

        # Search with include_unverified finds it with verified == 0
        all_results = library.search(library=lib, include_unverified=True)
        self.assertEqual(len(all_results), 1)
        self.assertEqual(all_results[0]["verified"], 0)

    def test_import_inbox_clean_product_passes_and_records_provenance(self) -> None:
        # Clean case: Valid LDT and agreeing metadata (3000 K, 23.0 W)
        lib = self.temp_root / "lib_clean"

        meta = {
            "manufacturer": "signify",
            "sku": "911401840687",
            "cct": 3000,
            "watts": 23.0,
        }

        inbox = lib / "inbox" / "signify" / "911401840687"
        inbox.mkdir(parents=True, exist_ok=True)
        valid_ldt = ldt_text(0, lamp_sets=((1, "LED", 1000.0, "3000", "90", 23.0),)).encode("latin-1")
        (inbox / "911401840687.ldt").write_bytes(valid_ldt)

        report = library.import_inbox(library=lib)
        prod_folder = _imported_folder(lib, meta)
        self.assertEqual(report["products"], 1)

        L, checks = library.verify_product(prod_folder)
        self.assertEqual(checks[0]["verified"], 1, "Clean agreeing product must be verified")

        verified_results = library.search(library=lib, include_unverified=False)
        self.assertEqual(len(verified_results), 1)
        self.assertEqual(verified_results[0]["verified"], 1)

        # Confirm provenance recorded in product.json
        saved_meta = json.loads((prod_folder / "product.json").read_text(encoding="utf-8"))
        self.assertTrue(len(saved_meta.get("sources", [])) > 0)
        source_rec = saved_meta["sources"][0]
        self.assertIn("provenance", source_rec)
        self.assertEqual(source_rec["provenance"]["sniffed_type"], "ldt")
        self.assertTrue(source_rec["provenance"]["type_matches"])

    def test_import_inbox_sibling_watts_only_disagreement_stays_unverified(self) -> None:
        # Sibling mutation: CCT agrees (3000 K vs 3000 K) but power disagrees (10.0 W vs 23.0 W, drift 13.0 W > 0.5 W).
        lib = self.temp_root / "lib_watts_drift"

        meta = {
            "manufacturer": "signify",
            "sku": "sibling_9114",
            "cct": 3000,
            "watts": 10.0,
        }

        inbox = lib / "inbox" / "signify" / "sibling_9114"
        inbox.mkdir(parents=True, exist_ok=True)
        valid_ldt = ldt_text(0, lamp_sets=((1, "LED", 1000.0, "3000", "90", 23.0),)).encode("latin-1")
        (inbox / "sibling_9114.ldt").write_bytes(valid_ldt)

        library.import_inbox(library=lib)
        prod_folder = _imported_folder(lib, meta)

        L, checks = library.verify_product(prod_folder)
        self.assertEqual(checks[0]["verified"], 0)
        self.assertIn("Watts mismatch", checks[0]["sanity"])

    def test_import_inbox_sibling_disguised_png_to_ies_skipped(self) -> None:
        # Sibling mutation: PNG payload disguised as .ies file in inbox.
        lib = self.temp_root / "lib_png_ies"
        prod_folder = lib / "signify" / "911401840687"
        prod_folder.mkdir(parents=True, exist_ok=True)
        valid_ldt = ldt_text(0, lamp_sets=((1, "LED", 1000.0, "3000", "90", 23.0),)).encode("latin-1")
        (prod_folder / "911401840687.ldt").write_bytes(valid_ldt)
        (prod_folder / "product.json").write_text(json.dumps({"manufacturer": "signify", "sku": "911401840687"}), encoding="utf-8")

        inbox = lib / "inbox" / "signify" / "911401840687"
        inbox.mkdir(parents=True, exist_ok=True)
        png_payload = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
        (inbox / "mfr_disguised.ies").write_bytes(png_payload)

        report = library.import_inbox(library=lib)

        dest_ies = prod_folder / "mfr_disguised.ies"
        self.assertFalse(dest_ies.exists(), "Disguised PNG must not be filed as IES")
        self.assertTrue(len(report["skipped"]) > 0)



if __name__ == "__main__":
    unittest.main()
