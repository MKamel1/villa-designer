"""Quantity take-off: per room, the items of a concept and how many (count, m2, linear m).

Quantities come from room geometry where it exists. Geometry may be:
  - the D1 read-back (out/villa/designs-r12/readback.json): room area, doors and windows with sizes;
  - the design model of lane L2 (out/model/d1-elements.json): `kind == "room"` elements whose `params`
    carry area_m2 / perimeter_m / height_m (and door/window elements with `room` and `size`).
A quantity whose basis is not in the geometry is reported as None with the reason, never guessed.
The only derived estimate is the wall-area lower bound from area alone (perimeter >= 4*sqrt(area),
the square room), labelled as such.

A plan line is a dict:
  {"room": "living", "item": "<catalogue id or finish code>", "label": "...", "unit": "count|m2|m",
   "basis": "count|floor_area|ceiling_area|wall_area|perimeter|fixed_m2",
   "qty": 1,                     # count, or fixed_m2 amount, or factor for count-type
   "waste_pct": 10}              # optional; POLICY allowance for cutting (tiles, paint, cloth)
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

BASES = ("count", "floor_area", "ceiling_area", "wall_area", "perimeter", "fixed_m2")
DEFAULT_CEILING_M = None     # no assumed ceiling height: the model or the read-back must supply it


@dataclass
class Room:
    id: str
    name: str = ""
    level: str = ""
    area_m2: float | None = None
    perimeter_m: float | None = None
    height_m: float | None = None
    openings_m2: float | None = None     # doors + windows cut out of the wall area
    source: str = ""                     # where the numbers came from

    def wall_area(self) -> tuple[float | None, str]:
        """(m2, basis) of net wall area, or (None, reason)."""
        if self.height_m is None:
            return None, "no ceiling height in the geometry"
        if self.perimeter_m is not None:
            per, how = self.perimeter_m, "measured perimeter"
        elif self.area_m2:
            per, how = 4 * math.sqrt(self.area_m2), "estimate: perimeter >= 4*sqrt(area) (square room), real value is larger"
        else:
            return None, "no area or perimeter"
        net = per * self.height_m - (self.openings_m2 or 0.0)
        return round(max(net, 0.0), 2), how


def load_rooms_readback(path: Path | str, option: str = "D1", height_m: float | None = None) -> dict[str, Room]:
    """Rooms from a designs read-back. Doors/windows give openings_m2 per room (width*height).
    Heights are not in the read-back; pass height_m only if you have a sourced value."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    opt = next(o for o in data["options"] if o["id"] == option)
    rooms = {r["id"]: Room(r["id"], r.get("name", ""), r.get("level", ""), r.get("area_m2") or None,
                           height_m=height_m, source=f"{Path(path).name}:{option}") for r in opt["rooms"]}
    for d in opt.get("doors", []):
        for rid in d.get("rooms", []):          # a door opens two rooms; count it once for each face
            if rid in rooms:
                rooms[rid].openings_m2 = (rooms[rid].openings_m2 or 0.0) + d["width"] * d["height"]
    for w in opt.get("windows", []):
        rid = w.get("room")
        if rid in rooms:
            rooms[rid].openings_m2 = (rooms[rid].openings_m2 or 0.0) + w["width"] * w["height"]
    for r in rooms.values():
        if r.openings_m2 is not None:
            r.openings_m2 = round(r.openings_m2, 3)
    return rooms


def load_rooms_elements(path: Path | str) -> dict[str, Room]:
    """Rooms from the L2 design model JSON (list of DesignElement dicts, or {"elements": [...]}).
    Reads kind=="room" with params area_m2 / perimeter_m / height_m; door and window elements add openings.
    Sizes are millimetres (contracts.DesignElement); areas in params are m2."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    els = data["elements"] if isinstance(data, dict) else data
    rooms: dict[str, Room] = {}
    for e in els:
        if e.get("kind") != "room":
            continue
        p = e.get("params", {})
        area = p.get("area_m2")
        if area is None and e.get("size") and e["size"][0] and e["size"][1]:
            area = None          # a bounding box is not a room area; do not derive one
        rooms[e["id"]] = Room(e["id"], p.get("name", ""), e.get("level", ""), area, p.get("perimeter_m"),
                              p.get("height_m"), source=Path(path).name)
    for e in els:
        if e.get("kind") in ("door", "window") and e.get("room") in rooms:
            w, _d, h = e.get("size", (0, 0, 0))
            r = rooms[e["room"]]
            r.openings_m2 = (r.openings_m2 or 0.0) + w * h / 1e6
    return rooms


@dataclass
class Row:
    room: str
    item: str
    label: str
    unit: str
    qty: float | None
    basis: str
    note: str = ""
    evidence: str = ""            # "measured" | "estimate" | "fixed" | "count"


def takeoff(plan: list[dict], rooms: dict[str, Room]) -> list[Row]:
    out: list[Row] = []
    for ln in plan:
        basis = ln["basis"]
        if basis not in BASES:
            raise ValueError(f"basis {basis!r} not in {BASES}")
        room = rooms.get(ln["room"])
        base = dict(room=ln["room"], item=ln["item"], label=ln.get("label", ""), unit=ln["unit"], basis=basis)
        waste = 1 + ln.get("waste_pct", 0) / 100
        wnote = f"+{ln['waste_pct']}% waste (POLICY)" if ln.get("waste_pct") else ""
        if basis == "count":
            out.append(Row(qty=ln.get("qty", 1), evidence="count", note=ln.get("note", ""), **base))
            continue
        if basis == "fixed_m2":
            out.append(Row(qty=round(ln["qty"] * waste, 2), evidence="fixed", note=" ".join(filter(None, [ln.get("note", ""), wnote])), **base))
            continue
        if room is None:
            out.append(Row(qty=None, evidence="", note=f"room {ln['room']!r} not in the geometry", **base))
            continue
        if basis in ("floor_area", "ceiling_area"):
            if room.area_m2 is None:
                out.append(Row(qty=None, evidence="", note="room has no area in the geometry", **base))
            else:
                out.append(Row(qty=round(room.area_m2 * ln.get("qty", 1) * waste, 2), evidence="measured",
                               note=" ".join(filter(None, [f"room area {room.area_m2} m2 ({room.source})", wnote])), **base))
        elif basis == "wall_area":
            wa, how = room.wall_area()
            if wa is None:
                out.append(Row(qty=None, evidence="", note=how, **base))
            else:
                ev = "estimate" if how.startswith("estimate") else "measured"
                out.append(Row(qty=round(wa * waste, 2), evidence=ev, note=" ".join(filter(None, [how, wnote])), **base))
        elif basis == "perimeter":
            if room.perimeter_m is None:
                out.append(Row(qty=None, evidence="", note="no perimeter in the geometry", **base))
            else:
                out.append(Row(qty=round(room.perimeter_m * waste, 2), evidence="measured", note=wnote, **base))
    return out


def totals(rows: list[Row]) -> dict[str, dict]:
    """Per item: summed quantity and unit; items with any unresolved row are flagged incomplete."""
    t: dict[str, dict] = {}
    for r in rows:
        e = t.setdefault(r.item, {"label": r.label, "unit": r.unit, "qty": 0.0, "incomplete": False})
        if r.qty is None:
            e["incomplete"] = True
        else:
            e["qty"] = round(e["qty"] + r.qty, 2)
    return t


def to_markdown(rows: list[Row]) -> str:
    lines = ["| room | item | qty | unit | basis |", "|---|---|---|---|---|"]
    for r in rows:
        q = "n/a" if r.qty is None else f"{r.qty:g}"
        lines.append(f"| {r.room} | {r.label or r.item} | {q} | {r.unit} | {r.evidence or r.note} |")
    return "\n".join(lines)
