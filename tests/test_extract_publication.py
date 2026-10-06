"""Exercise native exporter publication on Linux without claiming Revit coverage."""
import json
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, patch

from archpipe import safe_io

ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = ROOT / "revit/extract_model.py"
RIBBON = ROOT / "revit/archpipe.extension/archpipe.tab/Model.panel/Extract Model.pushbutton/script.py"


class Int64:
    def __int__(self):
        return 9223372036854775807

    def __float__(self):
        raise AssertionError("identifier converted to float")


class ExtractPublicationTests(unittest.TestCase):
    def setUp(self):
        # Only the native API is stubbed; execute the real serializer and writer.
        with patch.dict(sys.modules, {name: MagicMock() for name in
                        ("Autodesk", "Autodesk.Revit", "Autodesk.Revit.DB")}), \
                patch.object(sys, "path", sys.path.copy()):
            self.extractor = runpy.run_path(str(EXTRACTOR))

    def test_cli_and_ribbon_share_atomic_writer_and_preserve_native_values(self):
        data = {"id": Int64(), "name": "سلم", "zero": 0}
        writer = Mock(wraps=self.extractor["write_extract"])
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "extract.json"
            dest.write_bytes(b"previous complete extract")
            doc = Mock(PathName="saved.rvt")
            main = self.extractor["main"]
            with patch.dict(main.__globals__, resolve_doc=lambda: doc, build=lambda _: data,
                            destination=lambda _: str(dest), write_extract=writer):
                self.assertEqual(main(), str(dest))
            expected = {"id": 9223372036854775807, "name": "سلم", "zero": 0}
            self.assertEqual(json.loads(dest.read_bytes()), expected)
            cli_bytes = dest.read_bytes()
            native = Mock(build=lambda _: data, destination=lambda _: str(dest), write_extract=writer)
            pyrevit = MagicMock()
            pyrevit.revit.doc = doc
            with patch.dict(sys.modules, pyrevit=pyrevit, extract_model=native), \
                    patch.object(sys, "path", sys.path.copy()):
                runpy.run_path(str(RIBBON))
            pyrevit.forms.alert.assert_not_called()
            self.assertEqual(writer.call_count, 2)
            self.assertEqual(dest.read_bytes(), cli_bytes)
            self.assertEqual(list(Path(tmp).glob("*.part")), [])

    def test_serialization_failure_preserves_previous_extract(self):
        writer = self.extractor["write_extract"]
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "extract.json"
            dest.write_bytes(b"previous complete extract")
            with patch.object(writer.__globals__["jsonsafe"], "dumps", side_effect=ValueError("bad value")):
                with self.assertRaises(ValueError):
                    writer(str(dest), {"id": Int64()})
            self.assertEqual(dest.read_bytes(), b"previous complete extract")
            self.assertEqual(list(Path(tmp).glob("*.part")), [])

    def test_interrupted_atomic_publication_preserves_previous_extract(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "extract.json"
            dest.write_bytes(b"previous complete extract")
            with patch.object(safe_io.os, "fsync", side_effect=OSError("interrupted flush")):
                with self.assertRaises(OSError):
                    self.extractor["write_extract"](str(dest), {"id": Int64()})
            self.assertEqual(dest.read_bytes(), b"previous complete extract")
            self.assertEqual(list(Path(tmp).glob("*.part")), [])
