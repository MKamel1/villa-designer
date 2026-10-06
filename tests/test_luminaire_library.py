"""The luminaire library: import, verify, search, install -- on synthetic
manufacturer files (real ones are never committed)."""
import io
import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from unittest.mock import patch

from archpipe import photometry as ph
from archpipe.luminaires import eulumdat as eu
from archpipe.luminaires import install
from archpipe.luminaires import library as lib
from tests.test_eulumdat import dist, ldt_text

OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 504      # an .rfa's container signature


def product_ldt(sku="SKU-1", name="Test pendant LED", flux=2000.0, cct="3000", cri="90", watts=20.0):
    t = ldt_text(0, lamp_sets=((1, "LED", flux, cct, cri, watts),)).split("\n")
    t[0], t[8], t[9] = "brand Signify test", name, sku
    return "\n".join(t)


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.lib = Path(tempfile.mkdtemp())
        self.inbox = self.lib / "inbox" / "signify"
        self.inbox.mkdir(parents=True)

    def drop(self, name, data):
        (self.inbox / name).write_bytes(data if isinstance(data, bytes) else data.encode("latin-1"))

    def test_consistent_pair_imports_verified_and_is_searchable(self):
        ldt = product_ldt()
        ies = eu.parse(ldt).to_ies_text(0).replace("[LUMCAT] SKU-1", "[LUMCAT] SKU-1")
        z = io.BytesIO()
        with zipfile.ZipFile(z, "w") as zf:                          # served as a zip, like Signify's IES
            zf.writestr("SKU-1_0.ies", ies)
        self.drop("ldt_download", ldt)
        self.drop("ies_download.json", z.getvalue())                 # content type lies; content decides
        self.drop("Test pendant LED.rfa", OLE)
        rep = lib.import_inbox(self.lib, log=lambda *a: None)
        self.assertEqual(rep["products"], 1)
        rows = lib.search(library=self.lib, mount="pendant")
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["ldt"], "signify/SKU-1/SKU-1.ldt")
        self.assertEqual(r["folder"], "signify/SKU-1")
        self.assertEqual((r["verified"], r["has_rfa"], r["has_mfr_ies"]), (1, 1, 1))
        self.assertTrue(r["pair_check"].startswith("ok"), r["pair_check"])
        self.assertEqual((r["cct_k"], r["cri_ra"], r["watts"]), (3000.0, 90.0, 20.0))

    def test_manufacturer_ies_that_disagrees_fails_and_hides_the_product(self):
        # the axis error this module was proven against: the same product's IES
        # with its distribution turned 90 degrees
        wrong = eu.parse(ldt_text(0, fn=lambda c, g: dist(c + 90, g), lamp_sets=((1, "LED", 2000.0, "3000", "90", 20.0),)))
        self.drop("ldt", product_ldt())
        self.drop("x.ies", wrong.to_ies_text(0).replace("[LUMCAT] T-001", "[LUMCAT] SKU-1"))
        lib.import_inbox(self.lib, log=lambda *a: None)
        self.assertEqual(lib.search(library=self.lib), [])
        r = lib.search(library=self.lib, include_unverified=True)[0]
        self.assertTrue(r["pair_check"].startswith("FAIL"), r["pair_check"])

    def test_install_derives_figures_and_refuses_a_contradiction(self):
        self.drop("ldt", product_ldt())
        self.drop("Test pendant LED.rfa", OLE)
        lib.import_inbox(self.lib, log=lambda *a: None)
        item = {"id": "LT-9", "at": [1000, 1000], "mounting_height": 2000,
                "product": {"manufacturer": "signify", "sku": "SKU-1", "lamp_set": 0}}
        ies_dir = self.lib / "_ies"                     # never the real product folder
        got = install.resolve(item, library=self.lib, ies_dir=ies_dir)
        self.assertEqual((got["lumens"], got["watts"], got["kelvin"]), (2000.0, 20.0, 3000.0))
        self.assertTrue(got["family"].lower().endswith(".rfa"))
        self.assertTrue((ies_dir / got["ies"]).is_file())
        with self.assertRaisesRegex(install.InstallError, "contradicts"):
            install.resolve(dict(item, kelvin=2700), library=self.lib, ies_dir=ies_dir)
        exp = dict((n, ok) for n, ok, _ in install.expectations(got, {"kelvin": 3000, "cri_min": 95}))
        self.assertEqual((exp["colour temperature"], exp["colour rendering"]), (True, False))

    def test_alternate_is_resolved_and_tested_like_the_primary(self):
        self.drop("ldt1", product_ldt())
        self.drop("ldt2", product_ldt(sku="SKU-2", name="Other pendant LED", flux=1800.0, cri="80"))
        self.drop("Test pendant LED.rfa", OLE)
        self.drop("Other pendant LED.rfa", OLE)
        lib.import_inbox(self.lib, log=lambda *a: None)
        item = {"id": "LT-9", "at": [1, 1], "mounting_height": 2000,
                "requirement": {"kelvin": 3000, "cri_min": 90},
                "product": {"manufacturer": "signify", "sku": "SKU-1"},
                "alternate": {"manufacturer": "signify", "sku": "SKU-2"}}
        got = install.resolve(item, library=self.lib, ies_dir=self.lib / "_ies")
        self.assertEqual(got["alternate"]["lumens"], 1800.0)
        rep = install.candidate_report(got)
        cri = {r["check"]: r["passed"] for r in rep["alternate"]}["colour rendering"]
        self.assertFalse(cri)                                    # the alternate's CRI 80 misses 90: reported
        with self.assertRaisesRegex(install.InstallError, "NOPE"):
            install.resolve(dict(item, alternate={"manufacturer": "signify", "sku": "NOPE"}),
                            library=self.lib, ies_dir=self.lib / "_ies")

    def test_unknown_product_is_an_error_with_the_next_step(self):
        with self.assertRaisesRegex(install.InstallError, "links signify NOPE"):
            install.resolve({"id": "X", "product": {"manufacturer": "signify", "sku": "NOPE"}},
                            library=self._empty_library())

    def test_transferred_windows_index_paths_export_and_install_without_reindexing(self):
        frozen = json.loads((Path(__file__).parent / 'fixtures/c4-linux-library-paths.json').read_text())
        # Actual transferred path strings, independent temporary product data.
        for row in frozen:
            folder = self.lib / row['folder'].replace('\\', '/')
            folder.mkdir(parents=True)
            (folder / (row['sku']+'.ldt')).write_text(product_ldt(sku=row['sku']))
            (folder / 'product.json').write_text(json.dumps({
                'manufacturer': row['manufacturer'], 'sku': row['sku']}))
            (folder / 'portable.rfa').write_bytes(OLE)
        lib.rebuild_index(self.lib)
        with sqlite3.connect(self.lib / 'library.sqlite') as con:
            for row in frozen:
                con.execute('update rows set ldt=?, folder=? where sku=?',
                            (row['ldt'], row['folder'], row['sku']))
        before = (self.lib / 'library.sqlite').read_bytes()
        for row in frozen:
            got = lib.get(row['manufacturer'], row['sku'], library=self.lib)
            self.assertEqual(got['ldt'], row['ldt'].replace('\\', '/'))
            self.assertEqual(got['folder'], row['folder'].replace('\\', '/'))
            resolved = install.resolve({'id': 'portable-'+row['sku'], 'product': {
                'manufacturer': row['manufacturer'], 'sku': row['sku']}},
                library=self.lib, ies_dir=self.lib / '_ies')
            self.assertTrue(Path(resolved['family']).is_file())
            self.assertAlmostEqual(ph.load(self.lib / '_ies' / resolved['ies']).total_lumens, 2000)
        self.assertTrue(all('\\' not in r[key] for r in lib.search(library=self.lib)
                            for key in ('ldt', 'folder')))
        self.assertEqual((self.lib / 'library.sqlite').read_bytes(), before)
        # Other identifiers and mixed separators use the same read boundary.
        self.assertEqual(lib._portable_row({'ldt': 'other\\range/file.ldt',
                                          'folder': 'other/range'})['ldt'], 'other/range/file.ldt')

    def _empty_library(self):
        lib.rebuild_index(self.lib)
        return self.lib

    def test_file_server_is_refused(self):
        from archpipe.luminaires import signify
        with self.assertRaises(PermissionError):
            signify.fetch(signify.FILE_SERVER + "/ldt?id=1")

    def test_sniffer_uses_content_not_names(self):
        self.assertEqual(lib.sniff(OLE), "rfa")
        self.assertEqual(lib.sniff(product_ldt().encode("latin-1")), "ldt")
        self.assertEqual(lib.sniff("﻿,Wattage##OTHER##,X##LENGTH##MILLIMETERS\n".encode("utf-16")), "txt")
        self.assertIsNone(lib.sniff(b"<html>not a luminaire</html>"))



class StoredPathTests(unittest.TestCase):
    def test_nonrelative_paths_cannot_replace_the_library_root(self):
        for stored in ("/outside/file.ldt", r"C:\outside\file.ldt", "C:file.ldt",
                       r"\\server\share\file.ldt", "../file.ldt", r"other\..\file.ldt"):
            for root in (PurePosixPath("/library"), PureWindowsPath("C:/library")):
                with self.subTest(root=root, stored=stored), self.assertRaises(ValueError):
                    lib.resolve_library_path(root, stored)

    def test_both_separators_resolve_on_both_platforms(self):
        # Freeze the real Linux failure; pure paths exercise Windows on any host.
        parts = ("iguzzini", "LSEVO-AAK3EW", "LSEVO-AAK3EW.ldt")
        for root in (PurePosixPath("/library"), PureWindowsPath("C:/library")):
            for stored in (r"iguzzini\LSEVO-AAK3EW\LSEVO-AAK3EW.ldt",
                           "iguzzini/LSEVO-AAK3EW/LSEVO-AAK3EW.ldt",
                           r"iguzzini/LSEVO-AAK3EW\LSEVO-AAK3EW.ldt"):
                with self.subTest(root=root, stored=stored):
                    self.assertEqual(lib.resolve_library_path(root, stored), root.joinpath(*parts))
                    self.assertEqual(root.joinpath(*parts).relative_to(root).as_posix(),
                                     "iguzzini/LSEVO-AAK3EW/LSEVO-AAK3EW.ldt")

    def test_export_reads_the_real_backslash_stored_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "iguzzini" / "LSEVO-AAK3EW" / "LSEVO-AAK3EW.ldt"
            source.parent.mkdir(parents=True)
            source.write_text(product_ldt(sku="LSEVO-AAK3EW"), encoding="latin-1")
            with patch.object(lib, "get", return_value={
                    "ldt": r"iguzzini\LSEVO-AAK3EW\LSEVO-AAK3EW.ldt"}):
                dest = lib.export_ies("iguzzini", "LSEVO-AAK3EW", 0, root / "export.ies", root)
            self.assertEqual(ph.load(dest).total_lumens, 2000.0)

    def test_install_reads_backslash_folder_sibling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "inbox" / "signify"
            inbox.mkdir(parents=True)
            (inbox / "test.ldt").write_text(product_ldt(), encoding="latin-1")
            (inbox / "Test pendant LED.rfa").write_bytes(OLE)
            lib.import_inbox(root, log=lambda *a: None)
            row = lib.get("signify", "SKU-1", library=root)
            row.update(ldt=r"signify\SKU-1\SKU-1.ldt", folder=r"signify\SKU-1")
            with patch.object(lib, "get", return_value=row):
                result = install.resolve({"id": "portable", "product": {
                    "manufacturer": "signify", "sku": "SKU-1"}}, library=root, ies_dir=root / "_ies")
            self.assertEqual(Path(result["family"]),
                             (root / "signify" / "SKU-1" / "Test pendant LED.rfa").resolve())


class SignifyCrawlTests(unittest.TestCase):
    def test_family_url_keeps_prof_segment(self):
        """The crawler rebuilt /global/indoor-... without prof/ and lost every
        global-only family to a real 404 (158 of 381)."""
        import inspect
        from archpipe.luminaires import signify
        src = inspect.getsource(signify.crawl)
        self.assertIn('fam.split("/")[2:]', src)
        fam = "/global/prof/indoor-luminaires/recessed/x/LP_CF_1_EU/family"
        self.assertEqual("/global/" + "/".join(fam.split("/")[2:]), fam)


class TwoCandidateTests(unittest.TestCase):
    """Stage 5 rule: two widely available products from different ranges."""

    def setUp(self):
        self.lib = Path(tempfile.mkdtemp())
        from archpipe.luminaires import signify
        mk = lambda sku, rng, lm, k, markets: {
            "sku": sku, "region": "EU", "title": f"{rng} {lm} lm {k} K", "family": rng,
            "url": f"https://www.signify.com/global/prof/indoor-luminaires/recessed/{rng}/{sku}_EU/product",
            "description": "", "lm": [lm], "watts": [lm / 100], "cct_k": [k], "cri": [], "ugr": None,
            "beam_deg": [], "size_mm": [70.0], "ip": "IP20", "category": "recessed", "section": "indoor-luminaires",
            "mount": "recessed", "markets": markets, "files": {}}
        signify.write_catalogue([mk("A1", "range-a", 800, 3000, ["EG", "AE", "SA"]),
                                 mk("A2", "range-a", 900, 3000, ["EG", "AE", "SA", "GB"]),
                                 mk("B1", "range-b", 700, 3000, ["EG"]),
                                 mk("C1", "range-c", 800, 4000, ["EG", "AE", "SA", "GB"])], self.lib)

    def test_two_ranges_ranked_by_findability(self):
        from archpipe.luminaires import catalogue as cat
        got = cat.propose({"mount": "recessed", "kelvin": 3000, "lumens": [600, 1000]}, market="EG",
                          verify_live=False, library=self.lib)
        self.assertEqual([g["sku"] for g in got], ["A2", "B1"])      # best of range-a, then range-b

    def test_shortfall_names_the_excluding_constraint(self):
        from archpipe.luminaires import catalogue as cat
        req = {"mount": "recessed", "kelvin": 2700}
        self.assertEqual(cat.propose(req, verify_live=False, library=self.lib), [])
        self.assertEqual(cat.shortfall(req, library=self.lib)["excluded_by"], {"colour temperature": 4})


if __name__ == "__main__":
    unittest.main()
