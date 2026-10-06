"""revit/jsonsafe.py: values from real client models (Arabic names, .NET Int64 ids) serialise."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "revit"))
import jsonsafe  # noqa: E402


class Int64:                               # stands in for System.Int64 (float()-able, not a Python int)
    def __init__(self, v):
        self.v = v

    def __float__(self):
        return float(self.v)

    def __int__(self):
        return int(self.v)


Int64.__name__ = "Int64"


class JsonSafe(unittest.TestCase):
    def test_bridge_integer_siblings_preserve_exact_values(self):
        for name, value in (("Int64", 9223372036854775807), ("UInt64", 18446744073709551615),
                            ("Int32", -2147483648), ("UInt32", 4294967295),
                            ("Int16", -32768), ("UInt16", 65535),
                            ("Byte", 255), ("SByte", -128), ("long", 2 ** 80)):
            def forbidden_float(self):
                raise AssertionError("integer bridge reached float")
            bridge = type(name, (), {"__int__": lambda self: value, "__float__": forbidden_float})()
            with self.subTest(name=name):
                got = json.loads(jsonsafe.dumps({"value": bridge}))["value"]
                self.assertEqual(got, value)
                self.assertIs(type(got), int)

    def test_native_integer_subclass_stays_exact(self):
        class Identifier(int):
            def __float__(self):
                raise AssertionError("integer subclass reached float")
        self.assertEqual(json.loads(jsonsafe.dumps(Identifier(2 ** 80))), 2 ** 80)

    def test_real_valued_bridge_keeps_fraction(self):
        for name in ("Double", "Decimal"):
            bridge = type(name, (), {"__float__": lambda self: 22.04,
                                    "__int__": lambda self: 22})()
            self.assertEqual(json.loads(jsonsafe.dumps(bridge)), 22.04)

    def test_failed_integer_conversion_does_not_fall_back_to_float(self):
        class Int64:
            def __int__(self):
                raise ValueError("invalid integer bridge")
            def __float__(self):
                return 1.25
        bridge = Int64()
        self.assertEqual(json.loads(jsonsafe.dumps(bridge)), repr(bridge))

    def test_arabic_names_and_int64_ids(self):
        data = {"name": u"غرفة المعيشة", "id": Int64(1586207),
                "area": 22.04, "nested": [Int64(3), {"k": u"سلم"}]}
        text = jsonsafe.dumps(data, sort_keys=True)
        text.encode("ascii")                                   # plain ASCII on disk
        back = json.loads(text)
        self.assertEqual(back["name"], data["name"])
        self.assertEqual(back["id"], 1586207)
        self.assertIsInstance(back["id"], int)
        self.assertEqual(back["nested"][0], 3)

    def test_the_raw_encoder_fails_where_clean_does_not(self):
        with self.assertRaises(TypeError):
            json.dumps({"id": Int64(1)})                       # the failure mode, reproduced
        self.assertEqual(json.loads(jsonsafe.dumps({"id": Int64(1)})), {"id": 1})

    def test_ascii_output_unchanged(self):
        data = {"a": 1, "b": [1.5, "x"], "c": None, "d": True}
        self.assertEqual(jsonsafe.dumps(data, sort_keys=True), json.dumps(data, sort_keys=True))


if __name__ == "__main__":
    unittest.main()


class OwnEncoder(unittest.TestCase):
    """2026-09-26: IronPython's own json escaper failed on text holding U+0080-U+00FF (mis-decoded Arabic bytes
    such as 0xD8) even after cleaning; jsonsafe now escapes every non-ASCII character itself."""

    def test_identical_to_json_for_ascii_data(self):
        data = {"b": [1, 2.5, -0.0, 1e-07, 123456789012], "a": {"x": None, "y": True, "z": "q\"uote\\slash\ttab"},
                "e": [], "f": {}}
        for kw in ({}, {"sort_keys": True}, {"indent": 2, "sort_keys": True, "separators": (",", ": ")},
                   {"indent": 1, "sort_keys": True}):
            self.assertEqual(jsonsafe.dumps(data, **kw), json.dumps(data, **kw), kw)

    def test_mis_decoded_bytes_and_astral_characters(self):
        data = {"name": u"Ø³Ù\u0084 سلم \U0001f600"}
        text = jsonsafe.dumps(data)
        text.encode("ascii")
        self.assertEqual(json.loads(text), data)
        self.assertEqual(text, json.dumps(data))
