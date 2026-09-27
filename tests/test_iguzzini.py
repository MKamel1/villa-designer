"""Small page excerpts and synthetic photometry; no manufacturer page is copied."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from archpipe.luminaires import catalogue, iguzzini, library
from tests.test_luminaire_library import product_ldt


PAGE = '''<title>Laser Blade XS - iGuzzini</title>
<nav>Category: Recessed trimless</nav>
<div>2700 K · CRI 90 · 750 lm · 8 W · 40° · Ø 60 mm · IP20</div>
<div photometric='{&quot;photometricData&quot;:
[{&quot;url&quot;:&quot;/globalassets/shared-photometric-media/4/5/1/451g/39419/451g_l73t.ldt&quot;},
{&quot;url&quot;:&quot;/globalassets/shared-photometric-media/4/5/1/451g/39419/451g_l73t.ies&quot;}]}'></div>'''


class IGuzziniTests(unittest.TestCase):
    def test_product_parser_and_catalogue_search(self):
        row = iguzzini.parse_product(PAGE, "451g", "https://www.iguzzini.com/en/451g/")
        self.assertEqual((row["sku"], row["mount"], row["cct_k"], row["cri"]),
                         ("451G", "recessed", [2700.0], [90.0]))
        self.assertEqual(set(row["files"]), {"ldt", "ies"})
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            iguzzini.write_catalogue([row], root)
            found = catalogue.search_catalogue(manufacturer="iguzzini", cct=2700, library=root)
            self.assertEqual([r["sku"] for r in found], ["451G"])

    def test_robots_refuses_disallowed_path_even_when_cached(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(iguzzini, "CACHE", Path(folder)):
            url = "https://www.iguzzini.com/en/451g/"
            with patch.object(iguzzini, "_request", return_value=b"User-agent: *\nDisallow: /en/451g/\n"):
                with self.assertRaises(PermissionError):
                    iguzzini.fetch(url)
            with patch.object(iguzzini, "_request", return_value=b"User-agent: *\nAllow: /\n"):
                self.assertEqual(iguzzini.fetch(url), b"User-agent: *\nAllow: /\n")
            with patch.object(iguzzini, "_request", return_value=b"User-agent: *\nDisallow: /en/451g/\n"):
                with self.assertRaises(PermissionError):
                    iguzzini.fetch(url)

    def test_import_uses_product_code_and_preserves_failed_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            row = iguzzini.parse_product(PAGE, "451g", "https://www.iguzzini.com/en/451g/")
            iguzzini.write_catalogue([row], root)
            inbox = root / "inbox" / "iguzzini" / "451G"
            inbox.mkdir(parents=True)
            # The LDT's catalogue field need not match the web product code.
            inbox.joinpath("451G.ldt").write_text(product_ldt(sku="INTERNAL-REFERENCE", name="Laser Blade XS"),
                                                     encoding="latin-1")
            rep = library.import_inbox(root, log=lambda *_: None)
            self.assertEqual(rep["products"], 1)
            found = library.get("iguzzini", "451G", library=root)
            self.assertIsNotNone(found)
            self.assertEqual((found["mount"], found["verified"]), ("recessed", 1))
            self.assertTrue((root / found["ldt"]).is_file())


if __name__ == "__main__":
    unittest.main()
