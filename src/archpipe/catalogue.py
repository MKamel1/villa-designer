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
        _c(front=457),
        "Mitton & Nystuen, Residential Interior Design 4th ed. p. 84, Fig. 4.6 -- sofa to coffee table 12-18 in (305-457 mm); 12 in only where the table is also minimal, so 18 in (457 mm)",
    ),
    FurnitureType(
        "sofa_2seat", "Sofa, 2 seat", 1500, 900,
        _c(front=457),
        "Mitton & Nystuen, Residential Interior Design 4th ed. p. 84, Fig. 4.6 -- sofa to coffee table 12-18 in (305-457 mm); 12 in only where the table is also minimal, so 18 in (457 mm)",
    ),
    FurnitureType(
        "coffee_table", "Coffee table", 1100, 600,
        _c(front=457, back=457),
        "Mitton & Nystuen, Residential Interior Design 4th ed. p. 84, Fig. 4.6 -- sofa to coffee table 12-18 in (305-457 mm); 12 in only where the table is also minimal, so 18 in (457 mm)",
    ),
    FurnitureType(
        "tv_unit", "TV unit", 1600, 450,
        _c(),
        "No clearance: viewing distance is seat-to-screen, not clear floor space (Mitton p. 86, Fig. 4.10b: 1-1.5x the screen size for 4K, 1.5-2.5x for HD)",
        "The legacy 2.5 m 'clearance' treated viewing distance as free floor space; a coffee table legitimately sits inside it.",
    ),
    # ---- dining --------------------------------------------------------
    FurnitureType(
        "tv_screen", "TV screen (flat panel, 16:9)", 1440, 80,
        _c(),
        "Mitton & Nystuen 4th ed. p. 86, Fig. 4.10b -- viewing distance by screen size (checked by TV-01, not a clearance)",
        "Width is the screen's own width; the diagonal is derived assuming 16:9 (1440 mm wide is a 65 in screen).",
    ),
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
        _c(front=864),
        "Mitton & Nystuen 4th ed. p. 235, Fig. 8.13 -- chair about 24 in (610 mm) plus 10-20 in (254-508 mm) clear: at least 34 in (864 mm) behind the desk",
    ),
    # ---- villa scale (round 12, D1 furnishing) --------------------------------------------------------------------
    # Footprints below are ASSUMED typical product envelopes (replaced by the chosen product's datasheet in Phase 2);
    # the clearances cite a held, verified card where one exists (ENVELOPE) and say DIAGNOSTIC where none does.
    FurnitureType(
        "bed_king", "King bed (principal bedroom)", 1800, 2000,
        _c(front=750, left=750, right=750),
        "card ukadm-bed-principal-750 -- principal double bedroom: 750 mm to both sides and the foot",
        "ENVELOPE: 180 x 200 mattress, frame flush.",
    ),
    FurnitureType(
        "bed_small_double", "Small double bed (one child)", 1200, 2000,
        _c(),
        "card ukadm-bed-single-750 -- a bed for one person: 750 mm clear to one side",
        "ENVELOPE: 120 x 200; slept in by one child, so the single-bed zone applies.",
        clearance_any=(("left", "right"), 750),
    ),
    FurnitureType("bedside_table", "Bedside table", 500, 400, _c(), "ENVELOPE (no clearance of its own)"),
    FurnitureType(
        "sofa_4seat", "Sofa, 4 seat", 2600, 950, _c(front=457),
        "card mitton-sofa-coffee-table-457 -- sofa to coffee table 18 in (457 mm) where the table is not minimal",
        "ENVELOPE.",
    ),
    FurnitureType(
        "sofa_bed", "Sofa bed (closed)", 2000, 950, _c(front=457),
        "card mitton-sofa-coffee-table-457",
        "ENVELOPE. Opened it needs about 2.1 m of depth: the floor in front is kept clear of fixed pieces.",
    ),
    FurnitureType(
        "armchair", "Armchair", 850, 850, _c(front=457),
        "card mitton-sofa-coffee-table-457 (seat to table)", "ENVELOPE.",
    ),
    FurnitureType(
        "dining_6x", "Dining table, 6 (extends to 10)", 1800, 900,
        _c(front=965, back=965, left=813, right=813),
        "card tss-dining-chair-access-813 -- 813 mm for chair plus access; 965 mm (38 in) where the side is also a passage",
        "ENVELOPE 1.8 x 0.9 (client brief D-TABLE); extends to about 2.8 m. Long sides are passages in D1.",
    ),
    FurnitureType(
        "sideboard", "Sideboard", 2000, 450, _c(front=914),
        "card tss-front-of-storage-914 -- 36 in (914 mm) in front of chests and closets", "ENVELOPE.",
    ),
    FurnitureType(
        "bookcase", "Bookcase / shelving", 1200, 350, _c(front=914),
        "card tss-front-of-storage-914", "ENVELOPE; width set per placement.",
    ),
    FurnitureType(
        "daybed_nook", "Recessed daybed nook", 2000, 950, _c(),
        "Client-approved 900 x 2000 mattress; card mitton-path-of-travel-min checks its reached front edge",
        "A person enters from the front; the 914 mm route is checked at the access edge, not along enclosed sides.",
    ),
    FurnitureType(
        "joinery_end_panel", "Fixed joinery end panel", 200, 400, _c(),
        "Fixed infill beside the existing garden column; no cabinet door or working clearance",
    ),
    FurnitureType(
        "pantry_shelving", "Pantry shelving", 1000, 300, _c(front=914),
        "card tss-front-of-storage-914", "ENVELOPE; 300 mm deep so the 1.25 m pantry keeps 914 mm in front.",
    ),
    FurnitureType(
        "store_shelving", "Store shelving", 1000, 500, _c(front=600),
        "DIAGNOSTIC (no held card): 600 mm to reach a store shelf", "ENVELOPE.",
    ),
    FurnitureType(
        "under_stair_storage", "Under-stair fitted storage", 1000, 400, _c(),
        "Client round-3 storage brief; sliding doors keep the route clear; "
        "headroom checked against card mh-dwelling-ceiling-min at the standing access bay",
        "ASSUMED joinery size; TODO under-stair-joinery-product.",
    ),
    FurnitureType(
        "tall_column", "Tall appliance / pantry column", 600, 600, _c(front=1219),
        "card nkba-work-aisle-multi-cook -- the column faces the work aisle: 48 in (1219 mm) for more than one cook",
        "ENVELOPE 600 x 600 (fridge, freezer, oven, coffee columns, panel ready).",
    ),
    FurnitureType(
        "base_run", "Kitchen base run (with modules)", 2400, 600, _c(front=1219),
        "card nkba-work-aisle-multi-cook", "Width set per placement; modules (sink, dishwasher, hob) checked for landing areas.",
    ),
    FurnitureType(
        "island", "Kitchen island (with seating overhang)", 2500, 1200, _c(front=1219, back=1118, left=914, right=914),
        "cards nkba-work-aisle-multi-cook (working side), nkba-seating-walk-past-1118 (seated side: people walk "
        "behind the stools to the tall wall), nkba-walkway-min (ends)",
        "ENVELOPE: 900 mm counter + 300 mm overhang on the seated side; 610 mm per stool (card nkba-seating-width-610).",
    ),
    FurnitureType(
        "washer_dryer", "Washer + dryer stack", 600, 650, _c(front=914),
        "DIAGNOSTIC (no held card): 914 mm to load and unload, as for storage fronts", "ENVELOPE.",
    ),
    FurnitureType(
        "folding_counter", "Laundry folding counter", 1500, 600, _c(front=914),
        "DIAGNOSTIC (no held card)", "ENVELOPE.",
    ),
    FurnitureType(
        "recliner", "Cinema recliner (reclined)", 900, 1650, _c(),
        "DIAGNOSTIC (no held card): the reclined footprint is the envelope", "ENVELOPE 0.9 x 1.65 reclined.",
    ),
    FurnitureType(
        "screen", "Projection screen 100 in (16:9)", 2214, 100, _c(),
        "card mitton-tv-uhd-min/-max -- viewing distance checked separately (TV-01 style)", "Width of a 100 in 16:9 screen.",
    ),
    FurnitureType(
        "washbasin_double", "Double basin vanity", 1200, 500, _c(front=1100),
        "UK AD M Vol 1 (2015) Diagram 2.5 -- basin access zone 1100 mm deep (as washbasin)", "ENVELOPE.",
    ),
    FurnitureType(
        "shower_walkin", "Walk-in shower", 1400, 900, _c(front=762),
        "card nkba-shower-clear-floor-762", "ENVELOPE; size set per placement.",
    ),
    FurnitureType(
        "window_bench", "Window bench", 1000, 500, _c(),
        "ENVELOPE (a seat, no clearance of its own)",
    ),
)}


# ---- non-furniture planning dimensions ---------------------------------
# Each entry: (value_mm, citation). Used by rules.py.
PLANNING = {
    "corridor_min":        (900,  "UK AD M Vol 1 para 2.22a -- hall or landing at least 900 mm clear (Mitton p. 68: 36 in)"),
    "door_clear_entrance": (775,  "UK AD M Vol 1 (2015) para 2.20 -- principal private entrance: 775 mm minimum clear opening"),
    "daylight_ratio":      (0.08, "IRC R303.1 as quoted in Mitton & Nystuen, Residential Interior Design 4th ed. p. 92 -- glazing area at least 8 % of floor area in habitable rooms (code minimum; the unsourced legacy 1/8 was replaced 2026-09-25)"),
    "tv_view_min_ratio":   (1.0,  "Mitton & Nystuen 4th ed. p. 86, Fig. 4.10b -- UHD/4K: viewing distance 1 to 1.5 times the screen size"),
    "tv_view_max_ratio":   (1.5,  "Mitton & Nystuen 4th ed. p. 86, Fig. 4.10b -- UHD/4K: viewing distance 1 to 1.5 times the screen size"),
    "escape_window_area_m2":   (0.33, "UK AD B Vol 1 para 2.10a(i) -- emergency escape window: unobstructed openable area at least 0.33 m2"),
    "escape_window_min_mm":    (450,  "UK AD B Vol 1 para 2.10a(ii) -- emergency escape window: at least 450 mm high and 450 mm wide"),
    "escape_window_sill_max":  (1100, "UK AD B Vol 1 para 2.10a(iii) -- bottom of the openable area at most 1100 mm above the floor"),
    "inner_room_storey_max":   (4500, "UK AD B Vol 1 para 2.11e -- an inner room on a storey at most 4.5 m above ground, with an escape window"),
    "door_open_deg":       (90,   "UK AD M Vol 1 (2015) Appendix A -- clear opening width is measured with the door open at 90 degrees"),
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
    # Metric Handbook 7th ed. Fig. 22.12 (pp. 22-10/11), accessible and adaptable dwellings (AD M M4(2)),
    # chosen because the brief records ageing in place; the plain minimum WC/cloakroom is 1050 x 1500.
    "bathroom":       (4.30, "Metric Handbook 7th ed. Fig. 22.12d -- accessible and adaptable dwelling bathroom 2150 x 2000 mm"),
    "wc":             (2.61, "Metric Handbook 7th ed. Fig. 22.12c -- accessible and adaptable dwelling WC 1450 x 1800 mm"),
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
