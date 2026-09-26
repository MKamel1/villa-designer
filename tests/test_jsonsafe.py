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


Int64.__name__ = "Int64"


class JsonSafe(unittest.TestCase):
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
