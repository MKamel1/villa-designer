"""Synthetic parser probes; no proprietary native family files leave Windows."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from archpipe import rfa


class PortableFamilyParserTests(unittest.TestCase):
    def probe(self, text, offset=0):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'synthetic.rfa'
            path.write_bytes(rfa.OLE_MAGIC+b'\0'*(512+offset)+text.encode('utf-16-le')+b'\0'*512)
            return rfa.read(path)

    def test_explicit_release_and_both_byte_alignments(self):
        for offset in (0,1):
            info=self.probe('Revit Build: Autodesk Revit 2027 (Build: 27.0.1)\nFormat: 2027',offset)
            self.assertEqual(info.format_year,2027)
            self.assertFalse(info.usable_in(2025))
            self.assertTrue(info.is_ole)

    def test_unknown_and_build_date_remain_distinct(self):
        self.assertIsNone(self.probe('No version marker').usable_in(2027))
        dated=self.probe('Revit Build: 20080602_1900')
        self.assertEqual(dated.format_year,2009)
        self.assertTrue(dated.year_is_derived)


if __name__=='__main__':
    unittest.main()
