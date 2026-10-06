# -*- coding: utf-8 -*-
"""JSON that survives real client models under IronPython 2.7 (pyRevit) and plain CPython alike.

Failures seen on the client's own model (docs/LEARNINGS.md): Arabic text in element names, Revit 2027's
ElementId.Value as a .NET Int64, and text holding characters U+0080-U+00FF (Arabic stored as mis-decoded bytes,
e.g. from an old CAD import). The last one breaks INSIDE IronPython's own json string escaper, which tries to
re-decode such text as UTF-8 ("can't decode byte 0xd8"), so cleaning the values first was not enough (found by
running the extractor on the real model, 2026-09-26). This module therefore writes JSON itself: every non-ASCII
character is escaped as \\uXXXX here, the output is plain ASCII, and for ASCII data it is byte-identical to
json.dumps with the same options (tested).
"""
import json

try:
    unicode                                         # IronPython 2 / Python 2
except NameError:                                   # Python 3
    unicode = str


def clean(v):
    """Every value JSON-safe: text as unicode, .NET / long numbers as int or float, anything else as its repr."""
    if v is None or isinstance(v, bool):
        return v
    if isinstance(v, dict):
        return dict((clean(k), clean(x)) for k, x in v.items())
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    name = type(v).__name__
    if isinstance(v, (str, unicode)) or name in ("unicode", "String"):
        try:
            return u"%s" % v
        except Exception:
            return repr(v)
    if isinstance(v, float):
        return v
    if isinstance(v, int) or name in ("long", "Byte", "SByte", "Int16", "UInt16",
                                     "Int32", "UInt32", "Int64", "UInt64"):
        # Integral bridge types supply __int__, which float() need not accept.
        # Keep identifiers exact on CPython 3.12/3.14 and IronPython 2.7;
        # a failed integer conversion must never fall back through float.
        try:
            return int(v)
        except Exception:
            return repr(v)
    try:                                            # Double, Decimal and other real-valued bridges
        f = float(v)
        return int(f) if f == int(f) and abs(f) < 2 ** 53 else f
    except Exception:
        return repr(v)


_ESC = {'"': '\\"', "\\": "\\\\", "\n": "\\n", "\r": "\\r", "\t": "\\t", "\b": "\\b", "\f": "\\f"}


def _string(s):
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch in _ESC:
            out.append(_ESC[ch])
        elif 0x20 <= o < 0x7F:
            out.append(ch)
        elif o < 0x10000:
            out.append("\\u%04x" % o)
        else:                                       # astral: a surrogate pair, as json does
            o -= 0x10000
            out.append("\\u%04x\\u%04x" % (0xD800 | (o >> 10), 0xDC00 | (o & 0x3FF)))
    out.append('"')
    return "".join(out)


def _number(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        if v != v or v in (float("inf"), float("-inf")):
            return {True: "Infinity", False: "-Infinity"}[v > 0] if v == v else "NaN"
        return repr(v)
    return str(v)


def _encode(v, indent, sort_keys, item_sep, key_sep, level):
    if v is None:
        return "null"
    if isinstance(v, bool) or isinstance(v, (int, float)) or type(v).__name__ == "long":
        return _number(v)
    if isinstance(v, (str, unicode)):
        return _string(v)
    if isinstance(v, dict):
        if not v:
            return "{}"
        keys = sorted(v) if sort_keys else list(v)
        parts = [_string(k if isinstance(k, (str, unicode)) else _number(k)) + key_sep +
                 _encode(v[k], indent, sort_keys, item_sep, key_sep, level + 1) for k in keys]
        return _wrap("{", "}", parts, indent, item_sep, level)
    if isinstance(v, (list, tuple)):
        if not v:
            return "[]"
        parts = [_encode(x, indent, sort_keys, item_sep, key_sep, level + 1) for x in v]
        return _wrap("[", "]", parts, indent, item_sep, level)
    return _string(repr(v))


def _wrap(o, c, parts, indent, item_sep, level):
    if indent is None:
        return o + item_sep.join(parts) + c
    pad = "\n" + " " * (indent * (level + 1))
    return o + pad + (item_sep.rstrip() + pad).join(parts) + "\n" + " " * (indent * level) + c


def dumps(data, indent=None, sort_keys=False, separators=None, **_ignored):
    """json.dumps(clean(data), ensure_ascii=True, ...) without calling the platform's string escaper."""
    if separators is None:
        separators = (", ", ": ") if indent is None else (",", ": ")
    return _encode(clean(data), indent, sort_keys, separators[0], separators[1], 0)
