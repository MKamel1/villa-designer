"""Sheet-set spec for D1, generated from the design model.

The spec says what the issuable set must contain: sheets, the views on each, the schedules and the counts that the
drawings must reproduce. The Revit read-back (revit/sheets/) and the model-generated fallback are both checked against
it. Fields we do not hold (owner, engineer, Syndicate number, plot address) are `None` and listed in
`missing_title_block_fields`; they are never invented (ER Art.111 data, DS1).
"""
from __future__ import annotations

import datetime as _dt

from archpipe import model as _model
from archpipe.contracts import DesignElement

from . import names, schedules

# Fields the title block must carry (DS1; Egyptian Art.111 list is informative, see a-plus-architecture.md).
TITLE_BLOCK_FIELDS = ("project", "owner", "address", "engineer", "syndicate_no", "scale", "date", "title_en",
                      "title_ar", "sheet_no", "revision", "revision_location", "issue_seq")

PROJECT = {
    "project": "Villa, option D1",
    "owner": None,
    "address": "Sheikh Zayed City, Giza (city-level; plot not surveyed)",
    "engineer": None,
    "syndicate_no": None,
    "revision": "P01",
    "revision_location": "Sheet revision table, this sheet",
}

# kind: plan | elevation | section | schedule | cover; `generated_by`: which producer can make it today.
A1, A2, A3 = "A1 landscape", "A2 landscape", "A3 landscape"
# Composition rule (lead review 2026-11-21, plan-row RV2 fix 1): the paper is the smallest ISO A size on which the view set
# fits at a standard scale (1:20, 1:50, 1:100), the views fill the drawing area (sheetqa.fill_ratio >= 0.60) and printed text
# stays at or above 1.8 mm cap height (room names 2.5 mm). Both floor plans share one sheet at 1:50.
SHEETS = [
    {"no": "A-001", "kind": "cover", "level": None, "scale": "NTS", "views": ["sheet index", "legend", "title block key"]},
    {"no": "A-100", "kind": "site", "level": "SITE", "scale": "1:100", "paper": A2, "views": ["Site plan with context"]},
    {"no": "A-101", "kind": "plan", "variant": "ga", "level": "B+GF", "levels": ["B", "GF"], "scale": "1:50", "paper": A1, "views": ["GA plans B -1.80 and GF +1.20"]},
    {"no": "A-111", "kind": "plan", "variant": "furnished", "level": "B+GF", "levels": ["B", "GF"], "scale": "1:50", "paper": A1, "views": ["Furnished plans B and GF"]},
    {"no": "A-121", "kind": "plan", "variant": "lighting", "level": "B+GF", "levels": ["B", "GF"], "scale": "1:50", "paper": A1, "views": ["Reflected ceiling and lighting plans B and GF"]},
    {"no": "A-131", "kind": "plan", "variant": "colorfill", "level": "B+GF", "levels": ["B", "GF"], "scale": "1:50", "paper": A1, "views": ["Room colour-fill plans B and GF"]},
    {"no": "A-141", "kind": "callout", "variant": "stair", "level": "B", "scale": "1:20", "paper": A2, "views": ["Stair plan B and GF, 1:20"]},
    {"no": "A-142", "kind": "callout", "variant": "wet", "level": "GF", "scale": "1:20", "paper": A2, "views": ["Wet rooms 1:20"]},
    {"no": "A-143", "kind": "callout", "variant": "yardwall", "level": "B", "scale": "1:25", "paper": A3, "views": ["NE yard wall, plan and elevation (client confirmation)"]},
    {"no": "A-201", "kind": "elevation", "level": None, "scale": "1:50", "paper": A1, "views": ["East, North (street), West and South elevations"]},
    {"no": "A-211", "kind": "interior", "level": "GF", "scale": "1:25", "paper": A1, "views": ["Interior elevations: parents' bedroom, kids bedrooms A and B"]},
    {"no": "A-301", "kind": "section", "level": None, "scale": "1:20", "paper": A1, "views": ["Section 1 through the stair"]},
    {"no": "A-302", "kind": "section", "level": None, "scale": "1:50", "paper": A1, "views": ["Section 2 through the sunken garden", "Cross-sections 3, 4 and 5"]},
    {"no": "A-601", "paper": A2, "kind": "schedule", "level": None, "scale": "NTS",
     "views": ["Door schedule", "Window schedule", "Room schedule"]},
    {"no": "A-602", "paper": A3, "kind": "schedule2", "variant": "finish", "level": None, "scale": "NTS", "views": ["Finish schedule"]},
    {"no": "A-603", "paper": A2, "kind": "schedule2", "variant": "furniture", "level": None, "scale": "NTS", "views": ["Furniture schedule"]},
    {"no": "A-604", "paper": A3, "kind": "schedule2", "variant": "luminaire", "level": None, "scale": "NTS", "views": ["Luminaire schedule"]},
]
# L1 (apartment above) is not ours: no A-103 sheet (it is drawn dashed on the site plan only).

# Everything is generated from the design model; sections and elevations additionally need a built scene (Blender line art).
GENERATOR = {"cover": "model", "plan": "model", "site": "model", "callout": "model", "schedule": "model",
             "schedule2": "model", "interior": "model", "elevation": "lineart", "section": "lineart"}


def expected_counts(elements: list[DesignElement]) -> dict:
    """What every drawing and schedule must reproduce."""
    c = {"door": 0, "window": 0, "room": 0, "exterior_wall": 0}
    by_level: dict[str, dict[str, int]] = {}
    for e in elements:
        key = {"door": "door", "window": "window", "room": "room"}.get(e.kind)
        if e.kind == "wall" and e.params.get("wall_kind") == "ext":
            key = "exterior_wall"
        if key:
            c[key] += 1
            lv = by_level.setdefault(e.level, {"door": 0, "window": 0, "room": 0, "exterior_wall": 0})
            lv[key] += 1
    return {"total": c, "by_level": by_level}


def build(design: str = "D1", *, elements: list[DesignElement] | None = None, date: str | None = None) -> dict:
    els = elements if elements is not None else _model.load(design)
    exp = expected_counts(els)
    rooms = schedules.room_schedule(els)
    sheets = []
    for s in SHEETS:
        t_en, t_ar = names.SHEET_TITLES[s["no"]]
        lv = s["level"]
        rec = dict(s, title_en=t_en, title_ar=t_ar, generator=GENERATOR[s["kind"]])
        rec.setdefault("paper", "A3 landscape")
        if s["kind"] == "plan":
            rec["expects"] = {l: dict(exp["by_level"].get(l, {})) for l in s["levels"]}
            rec["required_graphics"] = ["grids", "level marks", "room tags (name + area)", "door tags", "window tags",
                                        "overall, grid and opening dimension chains on every exterior wall",
                                        "north point", "graphic scale"]
        if s["kind"] == "schedule":
            rec["expects"] = {"door": exp["total"]["door"], "window": exp["total"]["window"],
                              "room": exp["total"]["room"]}
        sheets.append(rec)
    proj = dict(PROJECT, date=date or _dt.date.today().isoformat())
    missing = [k for k in ("owner", "engineer", "syndicate_no") if proj.get(k) is None]
    return {
        "design": design, "schema": "archpipe-sheetset/1", "project": proj,
        "missing_title_block_fields": missing, "title_block_fields": list(TITLE_BLOCK_FIELDS),
        "sheets": sheets,
        "schedules": {"door": exp["total"]["door"], "window": exp["total"]["window"], "room": exp["total"]["room"],
                      "room_area_by_level": schedules.room_area_totals(rooms)},
        "expected": exp,
        "arabic_status": "unreviewed (written by the pipeline, not by a native reader or the engineer)",
    }
