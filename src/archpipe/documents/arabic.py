"""Arabic drawing text. Shaping and right-to-left order are done by the renderer, not here.

Lesson RV2-06: the first version pre-shaped to Presentation Forms and reversed the string for a renderer "with no bidi".
Matplotlib 3.11 (libraqm) already shapes and reorders logical text, so the pre-shaped string was shaped twice and
came out reversed and unjoined on the PDF/PNG. Pass LOGICAL text and name a font with Arabic glyphs
(`FONT_FAMILY`, Noto Naskh Arabic; DejaVu Sans stays first so Latin and digits keep their look). Guarded by
`tests/documents/test_arabic_render.py`, which compares the rendered ink with an independent raqm layout.
"""
from __future__ import annotations

FONT_FAMILY = ["DejaVu Sans", "Noto Naskh Arabic"]


def is_arabic(s: str) -> bool:
    return any("؀" <= c <= "ۿ" for c in s)
