"""Furniture catalogue: footprints and the clearance each piece demands.

These are legacy diagnostic dimensions, with readable historical citations.
The original edition-specific passages have NOT been verified. See
docs/guidance/rule-audit.md. Neither their numerical values nor a passing
calculation establish a published requirement, accessibility compliance or code
compliance. Resolve conflicting sources by applicability, not by always choosing
the largest dimension. Geometry extracted from a model remains measured geometry.

`codes.py` now carries the pluggable half of that: a jurisdiction pack adds
a **clause citation** to a rule, so a finding can say which clause it
answers to. It does not yet override the VALUES in this file -- a pack that
sets a stricter minimum is the obvious next step and is not built. Until it
is, a stricter local figure has to be applied by reading the finding, not by
loading a pack.

Being a declared occupancy in `vocabulary.py` and having a minimum area
here are separate things. `hall`, `utility`, `store`, `dressing` and
`garage` are all real terms with no published minimum area, so they have no
entry below, and `rules._min_area_key` returning None for them is the
correct answer rather than a gap to fill.

Clearance is the free space a piece needs to be usable -- room to pull a
chair out, to make a bed, to open an oven. It is given per side in
millimetres, in the piece's own frame:

    front = the +Y side before rotation (the working/approach side)
    back / left / right likewise

A clearance of 0 means the piece may sit hard against a wall on that side.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FurnitureType:
    id: str
    label: str
    width: float          # mm, along local X
    depth: float          # mm, along local Y
    clearance: dict       # side -> mm of free space required on THAT side
    source: str
    note: str = ""
    # "at least one of these sides needs this much" -- a single bed legitimately
    # has one long side against a wall, so requiring `left` specifically would
    # flag every correctly-planned single bed.
    clearance_any: tuple[tuple[str, ...], float] | None = None


def _c(front=0.0, back=0.0, left=0.0, right=0.0) -> dict:
    return {"front": front, "back": back, "left": left, "right": right}


CATALOGUE: dict[str, FurnitureType] = {t.id: t for t in (
    # ---- sleeping ------------------------------------------------------
    FurnitureType(
        "bed_single", "Single bed", 900, 2000,
        _c(),
        "UK AD M Vol 1 (2015) para 2.25d -- single and twin beds: 750 mm clear access zone to one side",
        "One long side may abut a wall; AD M asks no zone at the foot of a single bed.",
        clearance_any=(("left", "right"), 750),
    ),
    FurnitureType(
        "bed_double", "Double bed (principal bedroom)", 1600, 2000,
        _c(front=750, left=750, right=750),
        "UK AD M Vol 1 (2015) para 2.25b -- principal bedroom: 750 mm clear access zone to both sides and the foot",
        "The principal double bedroom; other doubles use bed_double_other.",
    ),
    FurnitureType(
        "bed_double_other", "Double bed (other bedrooms)", 1600, 2000,
        _c(front=750),
        "UK AD M Vol 1 (2015) para 2.25c -- other double bedrooms: 750 mm clear access zone to one side and the foot",
        clearance_any=(("left", "right"), 750),
    ),
    FurnitureType(
        "wardrobe", "Wardrobe", 1200, 600,
        _c(front=914),
        "Time-Saver Standards for Interior Design 2nd ed. p. 87 -- 36 in (914 mm) in front of dresser, closet and chest of drawers",
    ),
    # ---- living --------------------------------------------------------
    FurnitureType(
        "sofa_3seat", "Sofa, 3 seat", 2100, 900,
        _c(front=450),
        "Neufert, Architects' Data -- seating: 400-450 mm sofa to coffee table",
    ),
    FurnitureType(
        "sofa_2seat", "Sofa, 2 seat", 1500, 900,
        _c(front=450),
        "Neufert, Architects' Data -- seating: 400-450 mm sofa to coffee table",
    ),
    FurnitureType(
        "coffee_table", "Coffee table", 1100, 600,
        _c(front=450, back=450),
        "Neufert, Architects' Data -- seating groups",
    ),
    FurnitureType(
        "tv_unit", "TV unit", 1600, 450,
        _c(front=2500),
        "General practice: ~2.5 m minimum viewing distance for a domestic screen",
    ),
    # ---- dining --------------------------------------------------------
    FurnitureType(
        "dining_4", "Dining table, 4", 1200, 800,
        _c(front=813, back=813, left=813, right=813),
        "Time-Saver Standards for Interior Design 2nd ed. p. 81 -- 32 in (813 mm) from table edge for chair plus access (NKBA agrees for kitchen seating)",
        "38 in (965 mm) where the side is also a passage (same source).",
    ),
    FurnitureType(
        "dining_6", "Dining table, 6", 1800, 900,
        _c(front=813, back=813, left=813, right=813),
        "Time-Saver Standards for Interior Design 2nd ed. p. 81 -- 32 in (813 mm) from table edge for chair plus access (NKBA agrees for kitchen seating)",
    ),
    # ---- kitchen -------------------------------------------------------
    FurnitureType(
        "kitchen_run", "Kitchen run", 3000, 600,
        _c(front=1219),
        "NKBA Kitchen Planning Guidelines -- work aisle at least 48 in (1219 mm) for multiple cooks",
        "42 in (1067 mm) for one cook (same source); a villa kitchen is planned for more than one cook.",
    ),
    FurnitureType(
        "kitchen_island", "Kitchen island", 1800, 900,
        _c(front=1219, back=1219, left=914, right=914),
        "NKBA Kitchen Planning Guidelines -- work aisles 48 in (1219 mm) multi-cook; walkways 36 in (914 mm) at the ends",
    ),
    FurnitureType(
        "fridge", "Fridge/freezer", 700, 700,
        _c(front=1219),
        "NKBA Kitchen Planning Guidelines -- the fridge faces the work aisle: 48 in (1219 mm) for multiple cooks",
    ),
    # ---- sanitary ------------------------------------------------------
    FurnitureType(
        "wc", "WC pan", 400, 700,
        _c(front=1100),
        "UK AD M Vol 1 (2015) Diagram 2.5 -- WC access zone 1100 mm deep in front of the pan",
        "AD M's zone also extends 1000 mm to one side of the pan centreline; that width is not modelled here.",
    ),
    FurnitureType(
        "washbasin", "Washbasin", 600, 500,
        _c(front=1100),
        "UK AD M Vol 1 (2015) Diagram 2.5 -- basin access zone 1100 mm deep, 700 mm wide",
    ),
    FurnitureType(
        "bath", "Bath", 1700, 750,
        _c(front=700),
        "UK AD M Vol 1 (2015) Diagram 2.5 -- bath access zone 700 mm wide alongside, over 1100 mm of its length",
    ),
    FurnitureType(
        "shower", "Shower tray", 900, 900,
        _c(front=762),
        "NKBA Bathroom Planning Guidelines (Access Standard) -- 30 x 48 in clear floor space at each fixture: at least 30 in (762 mm) in front in either orientation",
        "Code minimum (IRC R307.1, same page) is 24 in (610 mm); the access standard is used because the brief records ageing in place.",
    ),
    # ---- work ----------------------------------------------------------
    FurnitureType(
        "desk", "Desk", 1400, 700,
        _c(front=900),
        "Neufert, Architects' Data -- workplaces: 900 mm for a seated chair zone",
    ),
)}


# ---- non-furniture planning dimensions ---------------------------------
# Each entry: (value_mm, citation). Used by rules.py.
PLANNING = {
    "corridor_min":        (900,  "Neufert, Architects' Data -- circulation: 900 mm minimum clear width in a dwelling"),
    "corridor_preferred":  (1200, "Neufert, Architects' Data -- circulation: 1200 mm for two people to pass"),
    "door_clear_entrance": (775,  "UK AD M Vol 1 (2015) para 2.20 -- principal private entrance: 775 mm minimum clear opening"),
    "ceiling_min":         (2400, "General practice / common code minimum for habitable rooms; Neufert cites 2500 mm as preferred"),
    "wheelchair_turn":     (1500, "Neufert, Architects' Data -- accessibility: 1500 mm turning circle"),
    "daylight_ratio":      (0.08, "IRC R303.1 as quoted in Mitton & Nystuen, Residential Interior Design 4th ed. p. 92 -- glazing area at least 8 % of floor area in habitable rooms (code minimum; the unsourced legacy 1/8 was replaced 2026-09-25)"),
    "room_min_width":      (2134, "IRC R304.2 via Mitton & Nystuen 4th ed. p. 143 -- habitable rooms at least 7 ft (2134 mm) in any horizontal dimension; kitchens excepted"),
}

# Minimum floor areas by occupancy, mm^2 handled as m^2 here.
MIN_AREA_M2 = {
    # Verified 2026-09-25: Metric Handbook 7th ed., p. 22-4, quoting England's Nationally
    # Described Space Standard (evidence cards ndss-*; knowledge/rule-evidence.json).
    # Legacy Neufert values (8.0 / 12.0 m2) had no verified passage.
    "bedroom_single": (7.5,  "Metric Handbook 7th ed. (2022) p. 22-4 -- NDSS: single bedroom at least 7.5 m2"),
    "bedroom":        (11.5, "Metric Handbook 7th ed. (2022) p. 22-4 -- NDSS: double (or twin) bedroom at least 11.5 m2"),
    # IRC R304.1 (quoted in Mitton & Nystuen 4th ed. p. 143): habitable rooms at least 70 sq ft (6.5 m2);
    # kitchens are the stated exception, so they have no entry (NKBA aisles and runs judge them).
    "living":         (6.5,  "IRC R304.1 via Mitton & Nystuen 4th ed. p. 143 -- habitable rooms at least 70 sq ft (6.5 m2); kitchens excepted"),
    "dining":         (6.5,  "IRC R304.1 via Mitton & Nystuen 4th ed. p. 143 -- habitable rooms at least 70 sq ft (6.5 m2); kitchens excepted"),
    "study":          (6.5,  "IRC R304.1 via Mitton & Nystuen 4th ed. p. 143 -- habitable rooms at least 70 sq ft (6.5 m2); kitchens excepted"),
    "bathroom":       (3.5,  "Neufert, Architects' Data -- minimum bathroom with WC, basin and bath/shower"),
    "wc":             (1.4,  "Neufert, Architects' Data -- minimum separate WC compartment"),
}


# UK AD M Vol 1 (2015) Table 2.1: minimum door clear opening by the corridor that approaches it.
# (corridor clear width mm, door clear opening mm); head-on approach needs 750 with a 900 corridor.
DOOR_BY_CORRIDOR = {
    "headon_900":  (900,  750, "UK AD M Vol 1 Table 2.1 -- 750 mm door, 900 mm corridor, approached head on"),
    "side_1200":   (1200, 750, "UK AD M Vol 1 Table 2.1 -- 750 mm door, 1200 mm corridor, not head-on"),
    "side_1050":   (1050, 775, "UK AD M Vol 1 Table 2.1 -- 775 mm door, 1050 mm corridor, not head-on"),
    "side_900":    (900,  800, "UK AD M Vol 1 Table 2.1 -- 800 mm door, 900 mm corridor, not head-on"),
}


ROOM_MIN_WIDTH = {
    # Verified 2026-09-25: Metric Handbook 7th ed., p. 22-4, quoting NDSS (cards ndss-*-width).
    # Other habitable rooms still use PLANNING["room_min_width"] (legacy, unsourced).
    "bedroom_single": (2150, "Metric Handbook 7th ed. (2022) p. 22-4 -- NDSS: single bedroom at least 2.15 m wide"),
    "bedroom":        (2550, "Metric Handbook 7th ed. (2022) p. 22-4 -- NDSS: every other double bedroom at least 2.55 m wide"),
    "bedroom_first":  (2750, "Metric Handbook 7th ed. (2022) p. 22-4 -- NDSS: one double bedroom at least 2.75 m wide"),
}


def get(type_id: str) -> FurnitureType:
    try:
        return CATALOGUE[type_id]
    except KeyError:
        raise KeyError(
            f"unknown furniture type {type_id!r}; known: {', '.join(sorted(CATALOGUE))}"
        ) from None
