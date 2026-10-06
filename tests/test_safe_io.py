"""Frozen boundary failures from Color, TextNote and stock-window read-back."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from archpipe import safe_io as B


class Byte:
    def __init__(self, value):
        self.value = value

    def __int__(self):
        return self.value


class Color:
    Red, Green, Blue = Byte(0), Byte(180), Byte(255)


class ElementId:
    Value = 9223372036854775807


class XYZ:
    X, Y, Z = 0.0, -1.0, 2.0


class BoundaryTests(unittest.TestCase):
    def test_dotnet_channels_and_native_records(self):
        with self.assertRaises(TypeError):
            json.dumps([Color.Red, Color.Green, Color.Blue])
        self.assertEqual(B.assert_round_trip(Color()), B.Color(0, 180, 255))
        self.assertEqual(B.assert_round_trip(Byte(0)), B.Byte(0))
        self.assertEqual(B.assert_round_trip(ElementId()), B.ElementId(9223372036854775807))
        self.assertEqual(B.assert_round_trip(XYZ()), B.XYZ(0.0, -1.0, 2.0, 'ft'))

    def test_all_portable_types_preserve_values_and_tags(self):
        values = [B.Byte(255), B.Color(10, 20, 30), B.ElementId(-1),
                  B.XYZ(0, 12, -4, 'mm'), B.Quantity(0, 'm'),
                  B.normalized_text('one\rtwo\r\n'), b'\x00\xff',
                  0, False, None, 0.0, {'type': 'null', 'value': 0}, (1, 2)]
        for value in values:
            self.assertEqual(B.assert_round_trip(value), value)
        restored = B.assert_round_trip([0, False, None])
        self.assertIs(type(restored[0]), int)
        self.assertIs(restored[1], False)
        self.assertIsNone(restored[2])

    def test_textnote_line_endings_and_unicode_original(self):
        original = 'Review\rRegistered \u00ae\r\n\n'
        record = B.normalized_text(original)
        self.assertEqual(record.normalized, 'Review\nRegistered \u00ae')
        self.assertEqual(B.assert_round_trip(record).original, original)
        self.assertEqual(B.normalized_text('A\n\nB').normalized, 'A\n\nB')
        self.assertEqual(B.normalized_text('clean').normalized, 'clean')

    def test_real_client_text_with_ironpython_safe_serializer(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'revit'))
        import jsonsafe
        original = '\u00d8\u00b3\u00d9\u0084 \u0633\u0644\u0645 \U0001f600\r'
        record = B.normalized_text(original)
        self.assertEqual(B.assert_round_trip(record, serializer=jsonsafe.dumps), record)

    def test_large_foreign_identifier_never_passes_through_float(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'revit'))
        import jsonsafe
        class Int64:
            def __int__(self):
                return 9223372036854775807
            def __float__(self):
                raise AssertionError('integral identifier converted to float')
        self.assertEqual(json.loads(jsonsafe.dumps({'id': Int64()}))['id'], 9223372036854775807)

    def test_units_are_explicit_and_conversion_preserves_zero(self):
        self.assertEqual(B.convert_length(B.Quantity(1, 'ft'), 'mm'), B.Quantity(304.8, 'mm'))
        self.assertEqual(B.convert_length(B.Quantity(0, 'm'), 'mm'), B.Quantity(0.0, 'mm'))

    def test_rejects_unknowns_and_injected_bad_types(self):
        for value in [object(), B.Byte(256), B.Color(False, 0, 0),
                      B.Quantity(1, 'unknown'), float('nan'), B.Text('a\r', 'wrong')]:
            with self.assertRaises((ValueError, TypeError)):
                B.encode(value)
        with self.assertRaises(ValueError):
            B.decode({'type': 'bool', 'value': 0})

    def test_interrupted_write_leaves_old_file_intact(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'extract.json'
            path.write_bytes(b'old complete extract')
            with self.assertRaises(RuntimeError):
                with B.atomic_path(path) as staged:
                    Path(staged).write_bytes(b'partial')
                    self.assertEqual(Path(staged).parent, path.parent)
                    raise RuntimeError('interrupted')
            self.assertEqual(path.read_bytes(), b'old complete extract')
            self.assertEqual(list(path.parent.glob('*.part')), [])
            with patch.object(B.os, 'replace', side_effect=PermissionError('viewer lock')):
                with self.assertRaises(PermissionError):
                    B.save_bytes(path, b'new', attempts=1)
            self.assertEqual(path.read_bytes(), b'old complete extract')
            B.save_json(path, {'zero': 0, 'off': False, 'missing': None, 'text': '\u00ae'})
            self.assertEqual(B.load_json(path)['zero'], 0)
            self.assertEqual(list(path.parent.glob('*.part')), [])

    def test_encoder_failure_and_fsync_failure_preserve_previous(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'extract.json'
            path.write_bytes(b'old')
            with self.assertRaises(TypeError):
                B.save_json(path, object())
            with patch.object(B.os, 'fsync', side_effect=OSError('disk error')):
                with self.assertRaises(OSError):
                    B.save_bytes(path, b'new', attempts=1)
            self.assertEqual(path.read_bytes(), b'old')

    def test_utf16_catalogue_and_utf8_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'data.json'
            data = {'name': '\u00ae \u0633\u0644\u0645', 'value': 0}
            for encoding in ('utf-16', 'utf-8-sig'):
                path.write_bytes(json.dumps(data, ensure_ascii=False).encode(encoding))
                self.assertEqual(B.load_json(path), data)

    def test_spec_echo_is_rejected_and_true_match_stays_quiet(self):
        authored = {'width': 1200, 'sill': 0}
        measured = {'width': 1000, 'sill': 1500}  # stock type and built instance
        with self.assertRaises(ValueError):
            B.assert_measured_readback(authored, measured, {'width': 'model', 'sill': 'model'})
        with self.assertRaises(ValueError):
            B.assert_measured_readback(authored, authored, {'width': 'spec', 'sill': 'spec'})
        B.assert_measured_readback(measured, measured.copy(), {'width': 'model', 'sill': 'model'})
        B.assert_measured_readback(authored, authored.copy(), {'width': 'model', 'sill': 'model'})

    def test_unique_staging_for_nested_writers(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'same.txt'
            with B.atomic_path(path) as first:
                Path(first).write_bytes(b'first')
                with B.atomic_path(path) as second:
                    self.assertNotEqual(first, second)
                    Path(second).write_bytes(b'second')
            self.assertEqual(path.read_bytes(), b'first')
