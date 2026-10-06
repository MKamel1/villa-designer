"""Tests for archpipe.external_claims: content sniffing, provenance, completeness,
cross-source agreement, found content verification, search relevance, and destination isolation.

Reproduces real defect cases from docs/LEARNINGS.md frozen by value:
- l0113: Zip bytes labelled application/json (Signify IES endpoint) and UTF-16 BOM catalogue.
- l0118: 3200 K / 3 W (Revit family) vs 3000 K / 23 W (LDT file) cross-source disagreement.
- l0122: Catalogue crawl that lost 158 of 381 families (41%) refuses to report complete.
- l0072: Props recorded as downloaded with empty folders are rejected.
- l0191: Nonsense search query returning a page hit is rejected by relevance check.
- l0098: Strip-light photometric file (594x24 mm) attached to a round drum fitting (276x276 mm).
- l0120: Tests write only to temporary directories; deployed stores are protected.
Plus corresponding quiet (passing) cases for each guard.

Quick Test:
    python -m unittest tests/test_external_claims.py
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from archpipe.evidence import (
    EvidenceRecord,
    EvidenceStatus,
    UNVERIFIED,
    VERIFIED,
)
from archpipe.external_claims import (
    CompletenessShortfallError,
    ContentTypeMismatchError,
    EmptyContentError,
    OLE_MAGIC,
    ProvenanceRecord,
    UnsafeDestinationError,
    UTF16_LE_BOM,
    assert_found_content,
    assert_manifest_complete,
    check_cct_and_watts_agreement,
    check_found_content,
    check_manifest_completeness,
    check_photometry_fitting_agreement,
    check_safe_destination,
    check_search_relevance,
    filter_search_results,
    ingest_bytes,
    sniff_content,
)


class ExternalClaimsTests(unittest.TestCase):
    """Test suite covering the 13 external claims defects and guards."""

    def setUp(self) -> None:
        # Create a unique temporary directory for this test case (l0120)
        self.temp_root = Path(tempfile.gettempdir()) / ("archpipe-ext-test-" + uuid.uuid4().hex)
        self.temp_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root, ignore_errors=True)

    # -------------------------------------------------------------------------
    # l0113: Zip bytes labelled application/json and UTF-16 BOM catalogues
    # -------------------------------------------------------------------------

    def test_zip_labelled_application_json_fails_and_quiet_case_passes_l0113(self) -> None:
        # Signify's server returned zip bytes declared as application/json
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("photometry.ies", "IESNA:LM-63-2002\nTILT=NONE\n")
        zip_bytes = buf.getvalue()

        # Sniffing correctly identifies zip by bytes regardless of declared type
        sniffed_type, encoding = sniff_content(zip_bytes)
        self.assertEqual(sniffed_type, "zip")
        self.assertIsNone(encoding)

        # Ingestion with contradictory declared type application/json stays UNVERIFIED
        rec_mismatch = ingest_bytes(
            zip_bytes,
            declared_type="application/json",
            url="https://api.signify.com/photometry/download?sku=123",
        )
        self.assertEqual(rec_mismatch.status, UNVERIFIED)
        self.assertTrue(any("l0113" in reason for reason in rec_mismatch.reasons))
        self.assertTrue(any("disagrees with sniffed" in reason for reason in rec_mismatch.reasons))
        self.assertEqual(rec_mismatch.value["provenance"]["sniffed_type"], "zip")
        self.assertEqual(rec_mismatch.value["provenance"]["declared_type"], "application/json")
        self.assertFalse(rec_mismatch.value["provenance"]["type_matches"])

        # Quiet case: zip bytes declared with matching type application/zip or .zip
        rec_quiet = ingest_bytes(
            zip_bytes,
            declared_type="application/zip",
            url="https://api.signify.com/photometry/download?sku=123",
        )
        self.assertEqual(rec_quiet.status, VERIFIED)
        self.assertEqual(rec_quiet.value["provenance"]["sniffed_type"], "zip")
        self.assertTrue(rec_quiet.value["provenance"]["type_matches"])

    def test_utf16_bom_type_catalogue_sniffed_and_quiet_case_passes_l0113(self) -> None:
        # Revit type catalogues are UTF-16 with a BOM and '##' headers
        catalogue_text = "##,FamilyName##Length##mm\r\nType1,1200\r\nType2,1500\r\n"
        catalogue_bytes = UTF16_LE_BOM + catalogue_text.encode("utf-16-le")

        sniffed_type, encoding = sniff_content(catalogue_bytes)
        self.assertEqual(sniffed_type, "txt")
        self.assertEqual(encoding, "utf-16-le")

        # Ingestion with declared type revit_type_catalogue or txt succeeds
        rec = ingest_bytes(
            catalogue_bytes,
            declared_type="revit_type_catalogue",
            url="file:///catalogues/Fixture.txt",
        )
        self.assertEqual(rec.status, VERIFIED)
        self.assertEqual(rec.value["provenance"]["encoding"], "utf-16-le")
        self.assertTrue(rec.value["provenance"]["type_matches"])

        # Quiet case: UTF-8 JSON correctly identified as json
        json_bytes = b'{"name": "luminaire", "watts": 23.5}'
        rec_json = ingest_bytes(json_bytes, declared_type="application/json")
        self.assertEqual(rec_json.status, VERIFIED)
        self.assertEqual(rec_json.value["provenance"]["sniffed_type"], "json")

    # -------------------------------------------------------------------------
    # l0118: 3200 K / 3 W vs 3000 K / 23 W cross-source disagreement
    # -------------------------------------------------------------------------

    def test_cross_source_cct_and_watts_disagreement_stays_unverified_l0118(self) -> None:
        # Source 1 (Revit family BIM metadata): claims 3200 K and 3 W
        revit_source = {"cct": 3200, "watts": 3.0, "format": "rfa", "source_id": "Signify_Family"}
        # Source 2 (Eulumdat LDT file): claims 3000 K and 23 W
        ldt_source = {"cct": 3000, "watts": 23.0, "format": "ldt", "source_id": "Signify_LDT"}

        # Cross-source check with standard tolerances (50 K, 0.5 W)
        rec = check_cct_and_watts_agreement(
            revit_source,
            ldt_source,
            cct_tolerance_k=50.0,
            watts_tolerance_w=0.5,
            source_a_label="revit_family",
            source_b_label="ldt_file",
        )

        # Must stay UNVERIFIED and preserve BOTH values (l0118)
        self.assertEqual(rec.status, UNVERIFIED)
        self.assertFalse(rec.value["agreed"])
        self.assertEqual(rec.value["cct"]["revit_family"], 3200)
        self.assertEqual(rec.value["cct"]["ldt_file"], 3000)
        self.assertEqual(rec.value["cct"]["drift"], 200)
        self.assertEqual(rec.value["watts"]["revit_family"], 3.0)
        self.assertEqual(rec.value["watts"]["ldt_file"], 23.0)
        self.assertEqual(rec.value["watts"]["drift"], 20.0)

        # Audit reasons cite the defect
        self.assertTrue(any("l0118" in reason for reason in rec.reasons))
        self.assertTrue(any("CCT mismatch" in reason for reason in rec.reasons))
        self.assertTrue(any("Watts mismatch" in reason for reason in rec.reasons))

        # Quiet case: Revit family and LDT agree within tolerance (e.g. 3000 K vs 3000 K, 23.0 W vs 23.2 W)
        ldt_matching = {"cct": 3000, "watts": 23.2, "format": "ldt"}
        revit_matching = {"cct": 3000, "watts": 23.0, "format": "rfa"}
        rec_quiet = check_cct_and_watts_agreement(
            revit_matching,
            ldt_matching,
            cct_tolerance_k=50.0,
            watts_tolerance_w=0.5,
        )
        self.assertEqual(rec_quiet.status, VERIFIED)
        self.assertTrue(rec_quiet.value["agreed"])
        self.assertEqual(rec_quiet.reasons, ("CCT and watts agree within tolerance",))

    # -------------------------------------------------------------------------
    # l0122: 223 of 381 families crawl completeness shortfall
    # -------------------------------------------------------------------------

    def test_crawl_shortfall_refuses_to_report_complete_l0122(self) -> None:
        # Crawl listed 381 families but only read 223 (158 lost, 41% loss)
        rec = check_manifest_completeness(
            expected_count=381,
            received_count=223,
            label="Luminaire Catalogue Crawl",
            min_coverage_ratio=0.95,
        )

        self.assertEqual(rec.status, UNVERIFIED)
        self.assertFalse(rec.value["complete"])
        self.assertEqual(rec.value["expected"], 381)
        self.assertEqual(rec.value["received"], 223)
        self.assertEqual(rec.value["missing_count"], 158)
        self.assertAlmostEqual(rec.value["coverage"], 223 / 381, places=3)
        self.assertTrue(any("l0122" in reason for reason in rec.reasons))
        self.assertTrue(any("refuses to report complete" in reason for reason in rec.reasons))

        # Assertion function raises
        with self.assertRaises(CompletenessShortfallError):
            assert_manifest_complete(381, 223, label="Luminaire Catalogue Crawl")

        # Quiet case: 381 expected, 381 received (100% complete)
        rec_quiet = check_manifest_completeness(
            expected_count=381,
            received_count=381,
            label="Luminaire Catalogue Crawl",
        )
        self.assertEqual(rec_quiet.status, VERIFIED)
        self.assertTrue(rec_quiet.value["complete"])
        self.assertEqual(rec_quiet.value["missing_count"], 0)

    # -------------------------------------------------------------------------
    # l0072: Empty download folders recorded as downloaded
    # -------------------------------------------------------------------------

    def test_empty_download_folder_is_rejected_l0072(self) -> None:
        empty_folder = self.temp_root / "downloaded_props" / "chair_01"
        empty_folder.mkdir(parents=True, exist_ok=True)

        # Folder exists on disk but holds no non-empty files
        rec = check_found_content(empty_folder, name="chair_01")
        self.assertEqual(rec.status, UNVERIFIED)
        self.assertFalse(rec.source.verified)
        self.assertTrue(any("l0072" in reason for reason in rec.reasons))
        self.assertTrue(any("contains no non-empty files" in reason for reason in rec.reasons))

        with self.assertRaises(EmptyContentError):
            assert_found_content(empty_folder, name="chair_01")

        # Empty 0-byte file is also rejected
        empty_file = self.temp_root / "model.gltf"
        empty_file.write_bytes(b"")
        rec_file = check_found_content(empty_file, name="model.gltf")
        self.assertEqual(rec_file.status, UNVERIFIED)
        self.assertTrue(any("file" in reason and "0 bytes" in reason for reason in rec_file.reasons))

        # Quiet case: Directory containing non-empty content passes
        good_folder = self.temp_root / "downloaded_props" / "chair_02"
        good_folder.mkdir(parents=True, exist_ok=True)
        (good_folder / "model.gltf").write_bytes(b'{"asset": {"version": "2.0"}}')
        rec_good = check_found_content(good_folder, name="chair_02")
        self.assertEqual(rec_good.status, VERIFIED)
        self.assertEqual(rec_good.value["file_count"], 1)
        self.assertGreater(rec_good.value["total_bytes"], 0)

    # -------------------------------------------------------------------------
    # l0191: Nonsense search query returning a page hit
    # -------------------------------------------------------------------------

    def test_nonsense_search_query_is_rejected_by_relevance_check_l0191(self) -> None:
        # Nonsense query with 3 non-stop words
        nonsense_query = "xylophonic quasar marmalade"
        # Candidate page text that happens to contain one word ('marmalade')
        candidate_text = "The breakfast dining table is served with toast and citrus marmalade preserve."

        rec = check_search_relevance(nonsense_query, candidate_text)
        self.assertEqual(rec.status, UNVERIFIED)
        self.assertFalse(rec.value["hit"])
        self.assertEqual(rec.value["matched_count"], 1)
        self.assertEqual(rec.value["needed_count"], 2)  # At least 2 of 3 words required
        self.assertTrue(any("l0191" in reason for reason in rec.reasons))
        self.assertTrue(any("rejected by relevance check" in reason for reason in rec.reasons))

        # filter_search_results drops the nonsense hit
        results = [
            {"id": "doc1", "text": candidate_text},
            {"id": "doc2", "text": "Unrelated chapter on building structures"},
        ]
        filtered = filter_search_results(nonsense_query, results)
        self.assertEqual(filtered, [])

        # Quiet case: query from l0190 where multiple terms match
        valid_query = "overheating criteria operative temperature"
        lechner_text = (
            "Thermal comfort assessment relies on criteria for operative temperature "
            "to prevent summer overheating in residential rooms."
        )
        rec_valid = check_search_relevance(valid_query, lechner_text)
        self.assertEqual(rec_valid.status, VERIFIED)
        self.assertTrue(rec_valid.value["hit"])
        self.assertGreaterEqual(rec_valid.value["matched_count"], 2)

        # Single word query matching text
        rec_single = check_search_relevance("neufert", "According to Neufert Architects Data...")
        self.assertEqual(rec_single.status, VERIFIED)
        self.assertTrue(rec_single.value["hit"])

    # -------------------------------------------------------------------------
    # l0098: Strip-light photometric file attached to a round drum
    # -------------------------------------------------------------------------

    def test_strip_photometry_on_round_drum_rejected_l0098(self) -> None:
        # A 594 x 24 mm linear strip file attached to a 276 x 276 mm round drum
        ies_strip_dims = (594.0, 24.0)       # 24.8:1 aspect ratio
        drum_lens_dims = (276.0, 276.0)     # 1:1 aspect ratio

        rec = check_photometry_fitting_agreement(
            ies_strip_dims,
            drum_lens_dims,
            size_ratio_max=2.0,
            aspect_ratio_max=3.0,
            fitting_label="LT-05 Round Drum",
        )

        self.assertEqual(rec.status, UNVERIFIED)
        self.assertFalse(rec.value["agreed"])
        # Size ratio 594 / 276 = 2.15 > 2.0
        self.assertGreater(rec.value["size_ratio"], 2.0)
        # Aspect ratio 24.8 / 1.0 = 24.8 > 3.0
        self.assertGreater(rec.value["aspect_ratio"], 3.0)
        self.assertTrue(any("l0098" in reason for reason in rec.reasons))
        self.assertTrue(any("different product" in reason for reason in rec.reasons))

        # Quiet case: Round downlight IES attached to round drum fitting
        ies_round_dims = (280.0, 280.0)
        rec_quiet = check_photometry_fitting_agreement(
            ies_round_dims,
            drum_lens_dims,
            size_ratio_max=2.0,
            aspect_ratio_max=3.0,
            fitting_label="LT-05 Round Drum",
        )
        self.assertEqual(rec_quiet.status, VERIFIED)
        self.assertTrue(rec_quiet.value["agreed"])
        self.assertEqual(rec_quiet.value["problems"], [])

    # -------------------------------------------------------------------------
    # l0120: Tests write only to temporary directories
    # -------------------------------------------------------------------------

    def test_destination_isolation_guards_deployed_store_l0120(self) -> None:
        # Attempting to write into deployed assets/user or assets/props raises
        deployed_dest = ROOT / "assets/user/luminaires/signify/test_sku/test.ies"
        with self.assertRaises(UnsafeDestinationError) as ctx:
            check_safe_destination(deployed_dest)
        self.assertIn("l0120", str(ctx.exception))

        props_dest = ROOT / "assets/props/bed_01/model.gltf"
        with self.assertRaises(UnsafeDestinationError):
            check_safe_destination(props_dest)

        # Writing to temporary test directory passes
        safe_temp_dest = self.temp_root / "test.ies"
        checked_dest = check_safe_destination(safe_temp_dest, allowed_roots=[self.temp_root])
        self.assertEqual(checked_dest, safe_temp_dest)
        checked_dest.write_text("IESNA:LM-63-2002\n", encoding="utf-8")
        self.assertTrue(checked_dest.exists())


if __name__ == "__main__":
    unittest.main()
