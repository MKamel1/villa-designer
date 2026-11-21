"""Door, window and room-area schedules computed from the design model (SC1).

Every row is one model element; nothing is invented. Fields the model does not carry (door type mark, finish
schedule, fire rating) are left out, not guessed.
"""
from __future__ import annotations

import csv
import io
import re

from archpipe.contracts import DesignElement

LEVEL_ORDER = {"B": 0, "GF": 1, "L1": 2, "ROOF": 3}


def _lv(e: DesignElement) -> int:
    return LEVEL_ORDER.get(e.level, 9)


def _natural(s: str):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def tag_numbers(elements: list[DesignElement]) -> dict[str, str]:
    """Stable tag per door/window/room: D01.., W01.., R01.. ordered by level then id."""
    out: dict[str, str] = {}
    for kind, prefix in (("door", "D"), ("window", "W"), ("room", "R")):
        items = sorted((e for e in elements if e.kind == kind), key=lambda e: (_lv(e), _natural(e.id)))
        for i, e in enumerate(items, 1):
            out[e.id] = "%s%02d" % (prefix, i)
    return out


def _room_name(rooms: dict[str, DesignElement], rid: str) -> str:
    r = rooms.get(rid)
    return r.params.get("name", rid) if r else rid


def door_schedule(elements: list[DesignElement]) -> list[dict]:
    tags = tag_numbers(elements)
    rooms = {e.room: e for e in elements if e.kind == "room"}
    rows = []
    for e in sorted((e for e in elements if e.kind == "door"), key=lambda e: tags[e.id]):
        p = e.params
        pair = list(p.get("rooms") or [e.room])
        rows.append({
            "tag": tags[e.id], "id": e.id, "level": e.level,
            "from": _room_name(rooms, pair[0]),
            "to": _room_name(rooms, pair[1]) if len(pair) > 1 else "",
            "width_mm": int(p.get("width_mm", e.size[0])), "height_mm": int(p.get("height_mm", e.size[2])),
            "operation": p.get("operation", ""), "glazed_garden_door": bool(p.get("garden")),
            "host_wall": e.host,
        })
    return rows


def window_schedule(elements: list[DesignElement]) -> list[dict]:
    tags = tag_numbers(elements)
    rooms = {e.room: e for e in elements if e.kind == "room"}
    rows = []
    for e in sorted((e for e in elements if e.kind == "window"), key=lambda e: tags[e.id]):
        p = e.params
        rows.append({
            "tag": tags[e.id], "id": e.id, "level": e.level, "room": _room_name(rooms, e.room),
            "width_mm": int(p.get("width_mm", e.size[0])), "height_mm": int(p.get("height_mm", e.size[2])),
            "sill_mm": int(p.get("sill_mm", e.placement[2])),
            "glazed_area_m2": round(float(p.get("gross_area_m2", e.size[0] * e.size[2] / 1e6)), 2),
            "host_wall": e.host,
        })
    return rows


def room_schedule(elements: list[DesignElement]) -> list[dict]:
    tags = tag_numbers(elements)
    rows = []
    for e in sorted((e for e in elements if e.kind == "room"), key=lambda e: tags[e.id]):
        p = e.params
        rows.append({
            "tag": tags[e.id], "id": e.room, "level": e.level, "name": p.get("name", e.room),
            "occupancy": p.get("occupancy", ""),
            "gross_area_m2": round(float(p.get("gross_area_m2", p.get("area_m2", 0.0))), 2),
            "net_area_m2": round(float(p.get("net_area_m2", p.get("area_m2", 0.0))), 2),
            "clear_height_mm": int(p.get("clear_height_mm", 0) or 0),
        })
    return rows


def room_area_totals(rows: list[dict]) -> dict[str, dict[str, float]]:
    tot: dict[str, dict[str, float]] = {}
    for r in rows:
        t = tot.setdefault(r["level"], {"rooms": 0, "gross_area_m2": 0.0, "net_area_m2": 0.0})
        t["rooms"] += 1
        t["gross_area_m2"] = round(t["gross_area_m2"] + r["gross_area_m2"], 2)
        t["net_area_m2"] = round(t["net_area_m2"] + r["net_area_m2"], 2)
    return tot


def to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def to_md(rows: list[dict], title: str) -> str:
    if not rows:
        return "## %s\n\n(none)\n" % title
    cols = list(rows[0])
    lines = ["## %s (%d)" % (title, len(rows)), "", "| " + " | ".join(cols) + " |",
             "|" + "|".join("---" for _ in cols) + "|"]
    for r in rows:
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines) + "\n"
