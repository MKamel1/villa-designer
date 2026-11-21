"""Minimal Arabic shaping for drawing text, so titles render connected without an extra dependency.

Maps base letters to Presentation Forms-B (isolated/initial/medial/final) using the Unicode data, applies the
joining rules (right-joining letters do not connect to the next letter), the lam-alef ligature, and returns the
string in visual (left-to-right) order for renderers with no bidi support (matplotlib). Latin runs and digits
inside an Arabic string keep their reading order. Not a full UAX #9 implementation: no diacritic stacking, and
only the basic Arabic block is joined.
"""
from __future__ import annotations

import unicodedata

_FORMS: dict[str, dict[str, str]] = {}
for _cp in range(0xFE70, 0xFEFD):
    _ch = chr(_cp)
    _d = unicodedata.decomposition(_ch)
    if not _d.startswith("<"):
        continue
    _tag, _, _base = _d.partition(" ")
    _tag = _tag.strip("<>")
    if _tag in ("isolated", "initial", "medial", "final") and " " not in _base:
        _FORMS.setdefault(chr(int(_base, 16)), {})[_tag] = _ch

# Letters that join to the previous letter only (never to the next one).
_RIGHT_ONLY = set("اآأإدذرزوةىء")
_LAM, _ALEFS = "ل", "آأإا"
_LIGA = {  # lam + alef -> ligature (isolated, final)
    "آ": ("ﻵ", "ﻶ"), "أ": ("ﻷ", "ﻸ"),
    "إ": ("ﻹ", "ﻺ"), "ا": ("ﻻ", "ﻼ"),
}


def is_arabic(s: str) -> bool:
    return any("؀" <= c <= "ۿ" for c in s)


def _joins_next(c: str) -> bool:
    return c in _FORMS and c not in _RIGHT_ONLY and "initial" in _FORMS[c]


def _joins_prev(c: str) -> bool:
    return c in _FORMS and "final" in _FORMS[c]


def shape(word: str) -> str:
    """Shape one run of Arabic letters; returns logical order of presentation forms."""
    out: list[str] = []
    i = 0
    n = len(word)
    while i < n:
        c = word[i]
        prev_joins = i > 0 and _joins_next(word[i - 1]) and not (out and out[-1] == "\0")
        if c == _LAM and i + 1 < n and word[i + 1] in _ALEFS:
            iso, fin = _LIGA[word[i + 1]]
            out.append(fin if prev_joins else iso)
            i += 2
            continue
        f = _FORMS.get(c)
        if not f:
            out.append(c)
            i += 1
            continue
        nxt = i + 1 < n and _joins_prev(word[i + 1]) and _joins_next(c)
        if prev_joins and nxt and "medial" in f:
            out.append(f["medial"])
        elif prev_joins and "final" in f:
            out.append(f["final"])
        elif nxt and "initial" in f:
            out.append(f["initial"])
        else:
            out.append(f.get("isolated", c))
        i += 1
    return "".join(out)


def visual(s: str) -> str:
    """Return `s` ready for a left-to-right renderer: Arabic shaped and reversed, other runs kept readable."""
    if not is_arabic(s):
        return s
    runs: list[tuple[bool, str]] = []
    cur, kind = "", None
    for ch in s:
        k = "؀" <= ch <= "ۿ"
        neutral = ch in " ()-/,.:" or ch.isdigit() or ch.isascii() and ch.isalpha()
        if not k:
            k = None if not neutral else False
        if kind is None or k == kind or (k is None and kind):
            cur += ch
            kind = kind if kind is not None else k
        else:
            runs.append((bool(kind), cur))
            cur, kind = ch, k
    if cur:
        runs.append((bool(kind), cur))
    # Within an Arabic paragraph the run order is right-to-left; Arabic runs are reversed, Latin/digit runs not.
    out = []
    for is_ar, text in reversed(runs):
        out.append(shape(text)[::-1] if is_ar else text)
    return "".join(out)
