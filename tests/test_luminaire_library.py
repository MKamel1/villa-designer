"""The luminaire library: import, verify, search, install -- on synthetic
manufacturer files (real ones are never committed)."""
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

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

    def test_unknown_product_is_an_error_with_the_next_step(self):
        with self.assertRaisesRegex(install.InstallError, "links signify NOPE"):
            install.resolve({"id": "X", "product": {"manufacturer": "signify", "sku": "NOPE"}},
                            library=self._empty_library())

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


if __name__ == "__main__":
    unittest.main()
