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


def _hinge_client(e: DesignElement) -> str:
    """Hinge side as a client compass word (N street .. S, E +y, W -y) from the exact hinge point, or ''."""
    hx = e.params.get("hinge_xy_mm")
    if not hx or e.params.get("operation") != "hinged":
        return ""
    dx, dy = hx[0] - e.placement[0], hx[1] - e.placement[1]
    return {"S": "south", "N": "north", "E": "east", "W": "west"}[
        "S" if abs(dx) >= abs(dy) and dx > 0 else "N" if abs(dx) >= abs(dy) else "E" if dy > 0 else "W"]


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
            "operation": p.get("operation", ""), "handing": p.get("handing", ""),
            "hinge_side": _hinge_client(e), "swing_into": _room_name(rooms, p["swing_into"]) if p.get("swing_into") else "",
            "to_confirm": "YES" if p.get("judgement") else "", "glazed_garden_door": bool(p.get("garden")),
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


def _by_room(elements: list[DesignElement], kind: str) -> dict[str, DesignElement]:
    return {e.id.split("-", 1)[1]: e for e in elements if e.kind == kind}


def finish_schedule(elements: list[DesignElement]) -> list[dict]:
    """One row per room: floor, wall (from the wall sides that face the room) and ceiling finish codes, ceiling kind
    and height. Codes are the model's own; nothing is inferred when a code is empty (shown blank)."""
    floors, ceilings = _by_room(elements, "floor"), _by_room(elements, "ceiling")
    walls: dict[str, set[str]] = {}
    for w in elements:
        if w.kind == "wall":
            for side in w.params.get("sides", {}).values():
                if side and side.get("room"):
                    walls.setdefault(side["room"], set()).add(side.get("finish_code") or "")
    tags = tag_numbers(elements)
    rows = []
    for e in sorted((e for e in elements if e.kind == "room"), key=lambda e: tags[e.id]):
        f, c = floors.get(e.room), ceilings.get(e.room)
        rows.append({"tag": tags[e.id], "level": e.level, "name": e.params.get("name", e.room),
                     "floor": f.params.get("finish_code", "") if f else "",
                     "walls": ", ".join(sorted(x for x in walls.get(e.room, ()) if x)),
                     "ceiling": c.params.get("finish_code", "") if c else "",
                     "ceiling_kind": c.params.get("ceiling_kind", "") if c else "",
                     "ceiling_mm": int(c.params.get("height_mm", 0)) if c else 0})
    return rows


def furniture_schedule(elements: list[DesignElement]) -> list[dict]:
    """Furniture by type and room (dressing props excluded: they are not furniture and are listed by the render lane)."""
    rooms = {e.room: e.params.get("name", e.room) for e in elements if e.kind == "room"}
    rows = []
    for e in sorted((e for e in elements if e.kind == "furniture" and e.params.get("type") != "dressing"),
                    key=lambda e: (_lv(e), e.room, e.params.get("type", ""), e.id)):
        rows.append({"id": e.id, "level": e.level, "room": rooms.get(e.room, e.room), "type": e.params.get("type", ""),
                     "w_mm": int(e.size[0]), "d_mm": int(e.size[1]), "h_mm": int(e.size[2]),
                     "product": e.product_id or ""})
    return rows


def luminaire_schedule(elements: list[DesignElement]) -> list[dict]:
    """One row per luminaire type (kind, product code, what, photometry), with counts per level and total watts."""
    g: dict[tuple, dict] = {}
    for e in elements:
        if e.kind != "luminaire":
            continue
        p = e.params
        ph = p.get("photometry") or {}
        key = (p.get("fixture_kind", ""), ph.get("manufacturer", ""), ph.get("code", ""), p.get("what", ""))
        r = g.setdefault(key, {"mark": key[0], "manufacturer": key[1], "code": key[2], "description": key[3],
                               "cct_k": p.get("cct_k"), "lumens": p.get("flux_lm"), "watts": p.get("watts") or 0.0,
                               "count_B": 0, "count_GF": 0, "total_watts": 0.0, "type_id": p.get("type_id", "")})
        r["count_" + e.level] = r.get("count_" + e.level, 0) + 1
        r["total_watts"] = round(r["total_watts"] + (p.get("watts") or 0.0), 1)
    return sorted(g.values(), key=lambda r: (r["mark"], r["code"]))
