"""Build the payload the web review viewer needs.

Ships the SVG, the model<->SVG transform, and enough of the L0 spec that
a pin can name what it landed on. That last part is the difference
between "comment at pixel 412,308" and "comment in Bedroom 1 at
7200,2100 mm" -- the second can be acted on, the first cannot.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .model import Project, load
from .web import render_svg


def build(spec_path: str | Path, dxf_path: str | Path, level: str | None = None) -> dict:
    p: Project = load(spec_path)
    level = level or (p.levels[0].id if p.levels else "")
    svg_text, tf, meta = render_svg(dxf_path)

    rooms = [
        {"id": r.id, "name": r.name, "area_m2": round(r.area_m2, 2),
         "occupancy": r.occupancy, "boundary": [list(pt) for pt in r.boundary]}
        for r in p.rooms if r.level == level
    ]
    walls = [
        {"id": w.id, "type": w.type,
         "thickness": p.wall_type(w.type).thickness,
         "bearing": p.wall_type(w.type).bearing,
         "start": list(w.start), "end": list(w.end)}
        for w in p.walls if w.level == level
    ]
    openings = [
        {"id": o.id, "host": o.host, "kind": o.kind, "width": o.width,
         "height": o.height, "at": o.at}
        for o in p.openings if p.wall(o.host).level == level
    ]

    return {
        "project": p.name,
        "level": level,
        "units": "mm",
        "svg": svg_text,
        "transform": asdict(tf),
        "extents_mm": meta["extents_mm"],
        "rooms": rooms,
        "walls": walls,
        "openings": openings,
    }


def write(spec_path: str | Path, dxf_path: str | Path, out_path: str | Path,
          level: str | None = None) -> Path:
    data = build(spec_path, dxf_path, level)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    return out
