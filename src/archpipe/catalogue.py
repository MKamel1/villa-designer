"""Furniture catalogue: footprints and the clearance each piece demands.

Every figure here is a published general-practice dimension, cited on the
entry. The dominant source is Neufert, *Architects' Data* (the standard
reference for residential dimensions); where a value is ordinary trade
practice rather than a specific Neufert figure, it says so.

These are DESIGN GUIDANCE, not building code. They are jurisdiction-neutral
and deliberately conservative. Where a local code is stricter it wins, and
a `site.jurisdiction` layer should override these values rather than edit
them here.

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
        _c(front=750),
        "Neufert, Architects' Data -- bedrooms: 750 mm access to one long side",
        "One long side may abut a wall; the foot needs access.",
        clearance_any=(("left", "right"), 750),
    ),
    FurnitureType(
        "bed_double", "Double bed", 1600, 2000,
        _c(front=750, left=750, right=750),
        "Neufert, Architects' Data -- bedrooms: 750 mm access to BOTH long sides",
        "A double bed with one side against a wall is a recognised planning fault.",
    ),
    FurnitureType(
        "wardrobe", "Wardrobe", 1200, 600,
        _c(front=750),
        "Neufert, Architects' Data -- storage: 750 mm to open doors and stand",
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
        _c(front=800, back=800, left=800, right=800),
        "Neufert, Architects' Data -- dining: 800 mm per side to seat and rise",
        "1000 mm is preferred where the side is also a circulation route.",
    ),
    FurnitureType(
        "dining_6", "Dining table, 6", 1800, 900,
        _c(front=800, back=800, left=800, right=800),
        "Neufert, Architects' Data -- dining: 800 mm per side to seat and rise",
    ),
    # ---- kitchen -------------------------------------------------------
    FurnitureType(
        "kitchen_run", "Kitchen run", 3000, 600,
        _c(front=1200),
        "Neufert, Architects' Data -- kitchens: 1200 mm working aisle",
        "900 mm is the absolute minimum for a single-person galley.",
    ),
    FurnitureType(
        "kitchen_island", "Kitchen island", 1800, 900,
        _c(front=1200, back=1200, left=1000, right=1000),
        "Neufert, Architects' Data -- kitchens: 1200 mm working aisle",
    ),
    FurnitureType(
        "fridge", "Fridge/freezer", 700, 700,
        _c(front=1100),
        "General practice: door swing plus standing room",
    ),
    # ---- sanitary ------------------------------------------------------
    FurnitureType(
        "wc", "WC pan", 400, 700,
        _c(front=600, left=200, right=200),
        "Neufert, Architects' Data -- sanitary: 600 mm clear in front of the pan",
    ),
    FurnitureType(
        "washbasin", "Washbasin", 600, 500,
        _c(front=700),
        "Neufert, Architects' Data -- sanitary: 700 mm standing room at a basin",
    ),
    FurnitureType(
        "bath", "Bath", 1700, 750,
        _c(front=700),
        "Neufert, Architects' Data -- sanitary: 700 mm alongside for access",
    ),
    FurnitureType(
        "shower", "Shower tray", 900, 900,
        _c(front=700),
        "Neufert, Architects' Data -- sanitary: 900x900 minimum practical tray",
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
    "door_clear_habitable":(800,  "Neufert, Architects' Data -- doors: 800 mm clear width to habitable rooms"),
    "door_clear_entrance": (900,  "Neufert, Architects' Data -- doors: 900 mm at a dwelling entrance"),
    "door_clear_wc":       (700,  "Neufert, Architects' Data -- doors: 700 mm minimum to a WC"),
    "ceiling_min":         (2400, "General practice / common code minimum for habitable rooms; Neufert cites 2500 mm as preferred"),
    "wheelchair_turn":     (1500, "Neufert, Architects' Data -- accessibility: 1500 mm turning circle"),
    "daylight_ratio":      (0.125,"Neufert, Architects' Data -- daylight: glazing area at least 1/8 of floor area in habitable rooms"),
    "room_min_width":      (2400, "General practice: below ~2.4 m a room will not take a bed plus circulation"),
}

# Minimum floor areas by occupancy, mm^2 handled as m^2 here.
MIN_AREA_M2 = {
    "bedroom_single": (8.0,  "Neufert, Architects' Data -- minimum single bedroom"),
    "bedroom":        (12.0, "Neufert, Architects' Data -- minimum double bedroom"),
    "living":         (16.0, "Neufert, Architects' Data -- minimum living room for a small dwelling"),
    "kitchen":        (6.0,  "Neufert, Architects' Data -- minimum separate kitchen"),
    "bathroom":       (3.5,  "Neufert, Architects' Data -- minimum bathroom with WC, basin and bath/shower"),
    "wc":             (1.4,  "Neufert, Architects' Data -- minimum separate WC compartment"),
}


def get(type_id: str) -> FurnitureType:
    try:
        return CATALOGUE[type_id]
    except KeyError:
        raise KeyError(
            f"unknown furniture type {type_id!r}; known: {', '.join(sorted(CATALOGUE))}"
        ) from None
