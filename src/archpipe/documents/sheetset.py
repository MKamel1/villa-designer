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
SHEETS = [
    {"no": "A-001", "kind": "cover", "level": None, "scale": "NTS", "views": ["sheet index", "legend", "title block key"]},
    {"no": "A-101", "kind": "plan", "level": "B", "scale": "1:100", "views": ["GA plan B -1.80"]},
    {"no": "A-102", "kind": "plan", "level": "GF", "scale": "1:100", "views": ["GA plan GF +1.20"]},
    {"no": "A-201", "kind": "elevation", "level": None, "scale": "1:100", "views": ["North elevation", "South elevation"]},
    {"no": "A-202", "kind": "elevation", "level": None, "scale": "1:100", "views": ["East elevation", "West elevation"]},
    {"no": "A-301", "kind": "section", "level": None, "scale": "1:50", "views": ["Section 1 through the stair"]},
    {"no": "A-302", "kind": "section", "level": None, "scale": "1:50", "views": ["Section 2 through the sunken garden"]},
    {"no": "A-601", "kind": "schedule", "level": None, "scale": "NTS",
     "views": ["Door schedule", "Window schedule", "Room schedule"]},
]
# L1 (apartment above) is not ours: no A-103 sheet. Roof/site plan A-100 needs L2 site data: not in this set.

# Plans and schedules come from the model today; elevations and sections need Revit geometry.
GENERATOR = {"cover": "model", "plan": "model", "schedule": "model", "elevation": "revit", "section": "revit"}


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
        rec = dict(s, title_en=t_en, title_ar=t_ar, generator=GENERATOR[s["kind"]], paper="A3 landscape")
        if s["kind"] == "plan":
            rec["expects"] = dict(exp["by_level"].get(lv, {}))
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
