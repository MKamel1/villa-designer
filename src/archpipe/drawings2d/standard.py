"""Drawing standard (Revit view templates replaced, plan row C11): one place for line weights, text sizes, dimension style.

Line weights are pen widths in mm on paper, chosen by plan scale (ISO 128-style graded pens: finer pens as the scale
gets larger so lines do not clog; the grading is a house standard, not a quoted clause). Text heights are paper mm.
"""
from __future__ import annotations

PT = 25.4 / 72.0                    # mm per point

# pen width (mm) per role and scale denominator. Roles: cut (section cut / wall cut edge), proj (projected edge),
# beyond (distant edge), ctx (neighbours, context), dim (dimension, extension), grid, hatch, fine.
_PENS = {
    20:  {"cut": 0.50, "proj": 0.25, "beyond": 0.13, "ctx": 0.13, "dim": 0.13, "grid": 0.13, "hatch": 0.09, "fine": 0.09},
    50:  {"cut": 0.50, "proj": 0.25, "beyond": 0.13, "ctx": 0.13, "dim": 0.13, "grid": 0.13, "hatch": 0.09, "fine": 0.09},
    100: {"cut": 0.35, "proj": 0.18, "beyond": 0.10, "ctx": 0.10, "dim": 0.10, "grid": 0.10, "hatch": 0.07, "fine": 0.07},
    200: {"cut": 0.25, "proj": 0.13, "beyond": 0.09, "ctx": 0.09, "dim": 0.09, "grid": 0.09, "hatch": 0.06, "fine": 0.06},
    500: {"cut": 0.18, "proj": 0.10, "beyond": 0.07, "ctx": 0.07, "dim": 0.07, "grid": 0.07, "hatch": 0.05, "fine": 0.05},
}

# text cap-height-ish sizes in pt (matplotlib font size) by role; same on every scale (text is paper-size, not model-size)
TEXT = {"sheet_title": 9.0, "view_title": 7.5, "room_name": 5.2, "room_tag": 4.6, "small": 3.6, "dim": 3.8,
        "tag": 3.4, "note": 4.6, "legend": 4.4, "schedule": 3.8, "level": 4.5}

DIM = {"tick_mm": 0.9, "ext_mm": 1.4, "offset_mm": 6.5, "eq_tol_mm": 1.0}


def pen(role: str, scale: float) -> float:
    """Pen width in mm for `role` at 1:`scale` (nearest standard scale at or above)."""
    key = min((k for k in _PENS if k >= scale), default=max(_PENS))
    return _PENS[key][role]


def lw(role: str, scale: float) -> float:
    """Matplotlib line width (points) for the pen."""
    return pen(role, scale) / PT


def eq_label(segments: list[int]) -> list[str]:
    """Dimension labels for a chain; equal runs (within DIM['eq_tol_mm']) of three or more are 'EQ' with the pitch once.

    Returns one label per segment: 'EQ' for the 2nd.. segments of an equal run is written as 'EQ' and the first keeps
    its value, so '1200  EQ  EQ'; shorter runs keep every number (a pair of equal dimensions is not 'EQ').
    """
    out = [str(s) for s in segments]
    i = 0
    while i < len(segments):
        j = i
        while j + 1 < len(segments) and abs(segments[j + 1] - segments[i]) <= DIM["eq_tol_mm"]:
            j += 1
        if j - i + 1 >= 3:
            for k in range(i + 1, j + 1):
                out[k] = "EQ"
        i = j + 1
    return out


PAPERS = {"A4": (297.0, 210.0), "A3": (420.0, 297.0), "A2": (594.0, 420.0), "A1": (841.0, 594.0)}
