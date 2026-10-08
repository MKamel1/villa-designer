"""Tests for Class C11 (external-claims) Phase 2 Batch 1 call-site migrations.

Verifies external-claims guards across the 4 migrated call sites:
1. archpipe.fetch.download: Ingests downloaded bytes via external_claims.ingest_bytes
   before staging file replaces destination, failing closed on content-type mismatches
   or empty payloads (l0113, l0072).
2. archpipe.fetch.get_text: Validates fetched text through external_claims.ingest_bytes,
   rejecting empty payloads (l0072) and non-HTML content (l0113).
3. archpipe.luminaires.iguzzini.fetch_photometry: Validates downloaded photometry through
   external_claims.ingest_bytes before persisting, rejecting non-photometric files (l0113).
4. archpipe.luminaires.iguzzini.crawl_products: Gates catalogue crawl completion using
   external_claims.assert_manifest_complete against requested family count (l0122).

All tests isolate network access by mocking urllib and HTTP fetch layers.

Quick Test:
    python -m unittest tests/test_c11_phase2.py

Example Usage:
    >>> import unittest
    >>> suite = unittest.defaultTestLoader.loadTestsFromName("tests.test_c11_phase2")
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
from unittest.mock import MagicMock, patch
import urllib.robotparser
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from archpipe import external_claims, fetch
from archpipe.luminaires import iguzzini
from tests.test_eulumdat import ldt_text


class DummyHTTPResponse:
    """Mock HTTP response wrapping raw byte payloads."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._io = io.BytesIO(data)

    def read(self, size: int = -1) -> bytes:
        return self._io.read(size)

    def __enter__(self) -> DummyHTTPResponse:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        pass


class C11Phase2Batch1Tests(unittest.TestCase):
    """Test suite covering the 4 Phase 2 Batch 1 call-site migrations."""

    def setUp(self) -> None:
        self.temp_root = Path(tempfile.gettempdir()) / ("archpipe-c11p2-" + uuid.uuid4().hex)
        self.temp_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root, ignore_errors=True)

    # -------------------------------------------------------------------------
    # Site 1: archpipe.fetch.download
    # -------------------------------------------------------------------------

    @patch("archpipe.fetch.allowed", return_value=True)
    @patch("archpipe.fetch._wait", return_value=None)
    def test_fetch_download_real_html_error_page_fails_closed_l0113(
        self, mock_wait: MagicMock, mock_allowed: MagicMock
    ) -> None:
        # Real failure frozen by value: Signify server returned an HTML 404 error page
        # when downloading a photometric .ies asset (lesson l0113).
        html_error_payload = (
            b"<!DOCTYPE html>\n<html>\n<head><title>404 Not Found</title></head>\n"
            b"<body><h1>Resource Not Found</h1><p>The requested IES file does not exist.</p></body>\n</html>"
        )
        dest = self.temp_root / "downloads" / "signify_product.ies"

        with patch("archpipe.fetch._open", return_value=DummyHTTPResponse(html_error_payload)):
            with self.assertRaises(external_claims.ContentTypeMismatchError) as ctx:
                fetch.download("https://assets.signify.com/ies/product.ies", dest)

        self.assertIn("l0113", str(ctx.exception))
        self.assertFalse(dest.exists(), "Destination file must not be created on type mismatch")
        self.assertFalse(
            dest.with_name(dest.name + ".part").exists(),
            "Staged .part file must be cleaned up on verification failure",
        )

    @patch("archpipe.fetch.allowed", return_value=True)
    @patch("archpipe.fetch._wait", return_value=None)
    def test_fetch_download_real_empty_payload_fails_closed_l0072(
        self, mock_wait: MagicMock, mock_allowed: MagicMock
    ) -> None:
        # Real failure frozen by value: 0-byte download payload recorded as successful (lesson l0072).
        empty_payload = b""
        dest = self.temp_root / "downloads" / "chair.gltf"

        with patch("archpipe.fetch._open", return_value=DummyHTTPResponse(empty_payload)):
            with self.assertRaises(external_claims.EmptyContentError) as ctx:
                fetch.download("https://models.example.com/chair.gltf", dest)

        self.assertIn("l0072", str(ctx.exception))
        self.assertFalse(dest.exists(), "Destination file must not be created on empty payload")

    @patch("archpipe.fetch.allowed", return_value=True)
    @patch("archpipe.fetch._wait", return_value=None)
    def test_fetch_download_clean_ies_content_passes_quietly(
        self, mock_wait: MagicMock, mock_allowed: MagicMock
    ) -> None:
        # Clean case: Valid IES photometry downloaded to .ies destination.
        valid_ies_payload = (
            b"IESNA:LM-63-2002\nTILT=NONE\n1 1000 1 3 1 1 1 0 0 0\n1.0 1.0 0.0\n0 45 90\n0\n100 80 0\n"
        )
        dest = self.temp_root / "downloads" / "clean_fixture.ies"

        with patch("archpipe.fetch._open", return_value=DummyHTTPResponse(valid_ies_payload)):
            res = fetch.download("https://assets.signify.com/ies/clean.ies", dest)

        self.assertEqual(res, dest, "download must preserve return type Path")
        self.assertTrue(dest.is_file())
        self.assertEqual(dest.read_bytes(), valid_ies_payload)

    @patch("archpipe.fetch.allowed", return_value=True)
    @patch("archpipe.fetch._wait", return_value=None)
    def test_fetch_download_sibling_png_payload_to_ies_dest_fails(
        self, mock_wait: MagicMock, mock_allowed: MagicMock
    ) -> None:
        # Sibling mutation: PNG binary image payload disguised as .ies extension.
        png_payload = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
        dest = self.temp_root / "downloads" / "disguised_image.ies"

        with patch("archpipe.fetch._open", return_value=DummyHTTPResponse(png_payload)):
            with self.assertRaises(external_claims.ContentTypeMismatchError) as ctx:
                fetch.download("https://assets.signify.com/ies/image.ies", dest)

        self.assertIn("l0113", str(ctx.exception))
        self.assertFalse(dest.exists())

    # -------------------------------------------------------------------------
    # Site 2: archpipe.fetch.get_text
    # -------------------------------------------------------------------------

    @patch("archpipe.fetch.allowed", return_value=True)
    @patch("archpipe.fetch._wait", return_value=None)
    def test_fetch_get_text_real_empty_payload_fails_closed_l0072(
        self, mock_wait: MagicMock, mock_allowed: MagicMock
    ) -> None:
        # Real failure frozen by value: empty response body when fetching page (lesson l0072).
        cache_dir = self.temp_root / "cache"

        with patch("archpipe.fetch._open", return_value=DummyHTTPResponse(b"")):
            with self.assertRaises(external_claims.EmptyContentError) as ctx:
                fetch.get_text("https://catalogue.example.com/page.html", cache_dir)

        self.assertIn("l0072", str(ctx.exception))
        self.assertEqual(len(list(cache_dir.glob("*.html"))), 0, "No cache file written on failure")

    @patch("archpipe.fetch.allowed", return_value=True)
    @patch("archpipe.fetch._wait", return_value=None)
    def test_fetch_get_text_real_binary_zip_payload_fails_closed_l0113(
        self, mock_wait: MagicMock, mock_allowed: MagicMock
    ) -> None:
        # Real failure frozen by value: binary zip payload returned where HTML page was expected (lesson l0113).
        zip_payload = b"PK\x03\x04\x14\x00\x00\x00\x08\x00test_zip_content"
        cache_dir = self.temp_root / "cache"

        with patch("archpipe.fetch._open", return_value=DummyHTTPResponse(zip_payload)):
            with self.assertRaises(external_claims.ContentTypeMismatchError) as ctx:
                fetch.get_text("https://catalogue.example.com/page.html", cache_dir)

        self.assertIn("l0113", str(ctx.exception))
        self.assertEqual(len(list(cache_dir.glob("*.html"))), 0)

    @patch("archpipe.fetch.allowed", return_value=True)
    @patch("archpipe.fetch._wait", return_value=None)
    def test_fetch_get_text_clean_html_passes_and_preserves_cache(
        self, mock_wait: MagicMock, mock_allowed: MagicMock
    ) -> None:
        # Clean case: Valid HTML page is fetched, cached, and returned unchanged.
        html_payload = (
            b"<!DOCTYPE html>\n<html>\n<head><title>Catalogue</title></head>\n"
            b"<body><h1>Product List</h1></body>\n</html>"
        )
        cache_dir = self.temp_root / "cache"
        url = "https://catalogue.example.com/clean.html"

        with patch("archpipe.fetch._open", return_value=DummyHTTPResponse(html_payload)) as mock_open:
            text = fetch.get_text(url, cache_dir)

        self.assertIn("Product List", text)
        self.assertEqual(text, html_payload.decode("utf-8"))
        cache_files = list(cache_dir.glob("*.html"))
        self.assertEqual(len(cache_files), 1)

        # Subsequent call without refresh reads from disk cache without network call
        with patch("archpipe.fetch._open") as mock_open_cached:
            cached_text = fetch.get_text(url, cache_dir, refresh=False)
            mock_open_cached.assert_not_called()

        self.assertEqual(cached_text, text)

    @patch("archpipe.fetch.allowed", return_value=True)
    @patch("archpipe.fetch._wait", return_value=None)
    def test_fetch_get_text_sibling_gltf_payload_fails(
        self, mock_wait: MagicMock, mock_allowed: MagicMock
    ) -> None:
        # Sibling mutation: Binary glTF model payload returned to get_text.
        gltf_payload = b"glTF\x02\x00\x00\x00\x40\x00\x00\x00"
        cache_dir = self.temp_root / "cache"

        with patch("archpipe.fetch._open", return_value=DummyHTTPResponse(gltf_payload)):
            with self.assertRaises(external_claims.ContentTypeMismatchError):
                fetch.get_text("https://catalogue.example.com/asset.html", cache_dir)

        self.assertEqual(len(list(cache_dir.glob("*.html"))), 0)

    # -------------------------------------------------------------------------
    # Site 3: archpipe.luminaires.iguzzini.fetch_photometry
    # -------------------------------------------------------------------------

    def _mock_iguzzini_robots(self) -> urllib.robotparser.RobotFileParser:
        parser = urllib.robotparser.RobotFileParser()
        parser.parse(["User-agent: *", "Allow: /"])
        return parser

    def _sample_product_html(self, sku: str) -> bytes:
        return (
            f"<!DOCTYPE html><html><head><title>{sku} - Laser Blade</title></head>"
            f"<body>"
            f"<a href=\"/globalassets/{sku.lower()}/{sku.lower()}.ldt\">LDT File</a>"
            f"<a href=\"/globalassets/{sku.lower()}/{sku.lower()}.ies\">IES File</a>"
            f"<div>recessed 1000 lm 12 W 3000 K CRI 90 32 deg IP20</div>"
            f"</body></html>"
        ).encode("utf-8")

    @patch("archpipe.luminaires.iguzzini.robots")
    def test_iguzzini_fetch_photometry_real_html_error_fails_closed_l0113(
        self, mock_robots: MagicMock
    ) -> None:
        # Real failure frozen by value: server returned HTML error page instead of .ldt (lesson l0113).
        mock_robots.return_value = self._mock_iguzzini_robots()
        html_page = self._sample_product_html("451G")
        html_error = b"<!DOCTYPE html><html><body><h1>404 File Not Found</h1></body></html>"

        def fake_fetch(url: str, *, rules: object = None, refresh: bool = False) -> bytes:
            if "en/451g" in url:
                return html_page
            return html_error

        with patch("archpipe.luminaires.iguzzini.fetch", side_effect=fake_fetch):
            with self.assertRaises(ValueError) as ctx:
                iguzzini.fetch_photometry("451G", lib=self.temp_root / "lib")

        self.assertIn("451G ldt: downloaded content is not ldt", str(ctx.exception))

    @patch("archpipe.luminaires.iguzzini.robots")
    def test_iguzzini_fetch_photometry_clean_eulumdat_passes_quietly(
        self, mock_robots: MagicMock
    ) -> None:
        # Clean case: Valid Eulumdat LDT and IES payloads downloaded.
        mock_robots.return_value = self._mock_iguzzini_robots()
        html_page = self._sample_product_html("451G")
        valid_ldt = ldt_text(1, lamp_sets=((1, "LED", 1000.0, "3000", "90", 12.0),)).encode("latin-1")
        valid_ies = b"IESNA:LM-63-2002\nTILT=NONE\n1 1000 1 3 1 1 1 0 0 0\n1.0 1.0 0.0\n0 45 90\n0\n100 80 0\n"

        def fake_fetch(url: str, *, rules: object = None, refresh: bool = False) -> bytes:
            if "en/451g" in url:
                return html_page
            if url.endswith(".ldt"):
                return valid_ldt
            if url.endswith(".ies"):
                return valid_ies
            return b""

        lib_dir = self.temp_root / "lib"
        with patch("archpipe.luminaires.iguzzini.fetch", side_effect=fake_fetch):
            with patch("archpipe.luminaires.library.import_inbox", return_value={"imported": 1, "sku": "451G"}):
                res = iguzzini.fetch_photometry("451G", lib=lib_dir)

        self.assertEqual(res, {"imported": 1, "sku": "451G"})
        saved_ldt = lib_dir / "inbox" / "iguzzini" / "451G" / "451G.ldt"
        saved_ies = lib_dir / "inbox" / "iguzzini" / "451G" / "451G.ies"
        self.assertTrue(saved_ldt.is_file())
        self.assertTrue(saved_ies.is_file())
        self.assertEqual(saved_ldt.read_bytes(), valid_ldt)
        self.assertEqual(saved_ies.read_bytes(), valid_ies)

    @patch("archpipe.luminaires.iguzzini.robots")
    def test_iguzzini_fetch_photometry_sibling_format_swap_fails(
        self, mock_robots: MagicMock
    ) -> None:
        # Sibling mutation: IES photometry returned for an LDT download request.
        mock_robots.return_value = self._mock_iguzzini_robots()
        html_page = self._sample_product_html("451G")
        ies_payload = b"IESNA:LM-63-2002\nTILT=NONE\n1 1000 1 3 1 1 1 0 0 0\n1.0 1.0 0.0\n0 45 90\n0\n100 80 0\n"

        def fake_fetch(url: str, *, rules: object = None, refresh: bool = False) -> bytes:
            if "en/451g" in url:
                return html_page
            return ies_payload

        with patch("archpipe.luminaires.iguzzini.fetch", side_effect=fake_fetch):
            with self.assertRaises(ValueError) as ctx:
                iguzzini.fetch_photometry("451G", lib=self.temp_root / "lib")

        self.assertIn("451G ldt: downloaded content is not ldt", str(ctx.exception))

    # -------------------------------------------------------------------------
    # Site 4: archpipe.luminaires.iguzzini.crawl_products
    # -------------------------------------------------------------------------

    @patch("archpipe.luminaires.iguzzini.robots")
    def test_iguzzini_crawl_products_real_shortfall_fails_closed_l0122(
        self, mock_robots: MagicMock
    ) -> None:
        # Real failure frozen by value: crawl lost 158 of 381 families (41% loss) and
        # still looked finished (lesson l0122).
        mock_robots.return_value = self._mock_iguzzini_robots()
        lib_dir = self.temp_root / "lib"

        codes_381 = [f"SK{i:04d}" for i in range(381)]
        unread_158 = set(codes_381[:158])

        def fake_fetch(url: str, *, rules: object = None, refresh: bool = False) -> bytes:
            code = url.rstrip("/").split("/")[-1].upper()
            if code in unread_158:
                raise urllib.error.URLError("Simulated 404 connection drop (l0122)")
            return self._sample_product_html(code)

        with patch("archpipe.luminaires.iguzzini.fetch", side_effect=fake_fetch):
            with self.assertRaises(external_claims.CompletenessShortfallError) as ctx:
                iguzzini.crawl_products(codes=codes_381, lib=lib_dir)

        self.assertIn("l0122", str(ctx.exception))
        self.assertIn("received 223 of 381 expected items", str(ctx.exception))

    @patch("archpipe.luminaires.iguzzini.robots")
    def test_iguzzini_crawl_products_clean_completeness_passes_quietly(
        self, mock_robots: MagicMock
    ) -> None:
        # Clean case: 5 requested product families, all 5 crawled successfully (100% complete).
        mock_robots.return_value = self._mock_iguzzini_robots()
        lib_dir = self.temp_root / "lib"
        codes_5 = [f"CK{i:04d}" for i in range(5)]

        def fake_fetch(url: str, *, rules: object = None, refresh: bool = False) -> bytes:
            code = url.rstrip("/").split("/")[-1].upper()
            return self._sample_product_html(code)

        with patch("archpipe.luminaires.iguzzini.fetch", side_effect=fake_fetch):
            rows = iguzzini.crawl_products(codes=codes_5, lib=lib_dir)

        self.assertEqual(len(rows), 5)
        self.assertEqual({r["sku"] for r in rows}, set(codes_5))

    @patch("archpipe.luminaires.iguzzini.robots")
    def test_iguzzini_crawl_products_sibling_single_missing_item_fails(
        self, mock_robots: MagicMock
    ) -> None:
        # Sibling mutation: 10 items requested, 9 parsed, 1 unread (90% coverage).
        # Must fail closed with CompletenessShortfallError under 100% completeness rule.
        mock_robots.return_value = self._mock_iguzzini_robots()
        lib_dir = self.temp_root / "lib"
        codes_10 = [f"SB{i:04d}" for i in range(10)]

        def fake_fetch(url: str, *, rules: object = None, refresh: bool = False) -> bytes:
            code = url.rstrip("/").split("/")[-1].upper()
            if code == "SB0009":
                raise ValueError("Single family corrupt HTML")
            return self._sample_product_html(code)

        with patch("archpipe.luminaires.iguzzini.fetch", side_effect=fake_fetch):
            with self.assertRaises(external_claims.CompletenessShortfallError) as ctx:
                iguzzini.crawl_products(codes=codes_10, lib=lib_dir)

        self.assertIn("received 9 of 10 expected items", str(ctx.exception))


    # Lead review 2026-10-08: the real callers fetch Poly Haven JSON through
    # get_text and download .exr/.bin/.gltf assets; these must keep working.
    @patch("archpipe.fetch.allowed", return_value=True)
    @patch("archpipe.fetch._wait", return_value=None)
    def test_poly_haven_json_api_text_still_accepted(self, mock_wait, mock_allowed) -> None:
        cache_dir = self.temp_root / "cache"
        with patch("archpipe.fetch._open", return_value=DummyHTTPResponse(b'{"oak_veneer": {"type": 1}}')):
            self.assertEqual(json.loads(fetch.get_text("https://api.polyhaven.com/assets?t=textures", cache_dir)),
                             {"oak_veneer": {"type": 1}})

    @patch("archpipe.fetch.allowed", return_value=True)
    @patch("archpipe.fetch._wait", return_value=None)
    def test_unsniffable_asset_downloads_still_accepted(self, mock_wait, mock_allowed) -> None:
        payloads = {"oak_diff_1k.exr": b"v/1\x01\x02\x00\x00" + bytes(range(64)),
                    "chair.bin": bytes(range(256)),
                    "chair.gltf": b'{"asset": {"version": "2.0"}, "buffers": [{"uri": "chair.bin"}]}'}
        for name, data in payloads.items():
            dest = self.temp_root / "downloads" / name
            with patch("archpipe.fetch._open", return_value=DummyHTTPResponse(data)):
                self.assertEqual(fetch.download("https://dl.polyhaven.org/file/" + name, dest), dest)
            self.assertEqual(dest.read_bytes(), data)

    @patch("archpipe.fetch.allowed", return_value=True)
    @patch("archpipe.fetch._wait", return_value=None)
    def test_html_error_page_for_unsniffable_asset_fails(self, mock_wait, mock_allowed) -> None:
        dest = self.temp_root / "downloads" / "oak_diff_1k.exr"
        page = b"<!DOCTYPE html>\n<html><head><title>404 Not Found</title></head><body>gone</body></html>"
        with patch("archpipe.fetch._open", return_value=DummyHTTPResponse(page)):
            with self.assertRaises(external_claims.ContentTypeMismatchError):
                fetch.download("https://dl.polyhaven.org/file/oak_diff_1k.exr", dest)
        self.assertFalse(dest.exists())

if __name__ == "__main__":
    unittest.main()
