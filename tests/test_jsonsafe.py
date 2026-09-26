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
