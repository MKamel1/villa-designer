# -*- coding: utf-8 -*-
"""JSON that survives real client models under IronPython 2.7 (pyRevit) and plain CPython alike.

Two failures seen on the client's own model (docs/LEARNINGS.md, 2026-09-25): Arabic text in element names broke
IronPython's json encoder, and Revit 2027's ElementId.Value is a .NET Int64 the encoder rejects. Our own test
models had ASCII names and were 2027-native, so the extractor had never met either. `dumps` cleans every value
first and escapes non-ASCII (the output file is plain ASCII, readable by any tool), so no model content can stop
an extract at the last step.
"""
import json


def clean(v):
    """Every value JSON-safe: text as unicode, .NET / long numbers as int or float, anything else as its repr."""
    if v is None or isinstance(v, bool):
        return v
    if isinstance(v, dict):
        return dict((clean(k), clean(x)) for k, x in v.items())
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    name = type(v).__name__
    if isinstance(v, str) or name in ("unicode", "String"):
        try:
            return u"%s" % v
        except Exception:
            return repr(v)
    if isinstance(v, float):
        return v
    if isinstance(v, int) and name == "int":
        return v
    try:                                            # long, Int64, Int32, Double, Decimal and the like
        f = float(v)
        return int(f) if f == int(f) and abs(f) < 2 ** 53 else f
    except Exception:
        return repr(v)


def dumps(data, **kw):
    kw.setdefault("ensure_ascii", True)
    return json.dumps(clean(data), **kw)
