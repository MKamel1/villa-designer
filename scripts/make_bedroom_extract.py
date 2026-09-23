"""Write the mock bedroom as an extract JSON, for the Blender bridge.

    python scripts/make_bedroom_extract.py --ies-dir /home/x/archpipe/ies \
        --out out/bedroom.json

This stands in for `revit/build_bedroom.py` until Revit content exists.
The geometry and the fixture layout are identical to
`scripts/demo_bedroom_lighting.py`, so the analytical lux grid and the
rendered one describe the same room -- which is the entire point: two
independent implementations of the same scene are what make the
comparison evidence rather than decoration.

`--ies-dir` is a path on the machine that will RENDER, not this one.
Blender resolves the IES file at render time.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

W, D = 4200.0, 3600.0          # internal, mm
WALL_T = 200.0
HEIGHT = 2700.0
HALF = WALL_T / 2.0

# Wall centrelines enclose the internal rectangle.
X0, Y0 = -HALF, -HALF
X1, Y1 = W + HALF, D + HALF

FIXTURES = [
    # id,     ies file,        x,     y,      z,     layer,   lumens, K
    ("LT-01", "PLD1A21.ies", W / 2, D / 2, 2400.0, "ambient", 2780.0, 2700),
    ("LT-02", "EWL2A19.ies", 1100.0, 3300.0, 1200.0, "task", 780.0, 2700),
    ("LT-03", "EWL2A19.ies", 3100.0, 3300.0, 1200.0, "task", 780.0, 2700),
    ("LT-04", "LGLled.ies", 400.0, 1800.0, 2400.0, "accent", 1008.0, 3000),
]


def build(ies_dir: str) -> dict:
    walls = [
        {"id": "W-S", "start": [X0, Y0], "end": [X1, Y0]},
        {"id": "W-E", "start": [X1, Y0], "end": [X1, Y1]},
        {"id": "W-N", "start": [X1, Y1], "end": [X0, Y1]},
        {"id": "W-W", "start": [X0, Y1], "end": [X0, Y0]},
    ]
    for w in walls:
        w.update({"thickness": WALL_T, "height": HEIGHT, "level": "L0",
                  "type": "EXT-200"})

    return {
        "units": "mm",
        "source": "scripts/make_bedroom_extract.py (mock, not Revit)",
        "levels": [{"id": "L0", "name": "Ground", "elevation": 0.0}],
        "walls": walls,
        "rooms": [{
            "id": "R-BED-01", "name": "Bedroom 01", "level": "L0",
            "occupancy": "bedroom",
            "boundary": [[0.0, 0.0], [W, 0.0], [W, D], [0.0, D]],
            "area": W * D / 1e6,
        }],
        "openings": [
            # Window on the south wall. `at` is measured along the wall from
            # its start point, so the 2100 mm room centre is 2200 mm along a
            # centreline that begins 100 mm outside the room.
            {"id": "WD-01", "host": "W-S", "kind": "window", "at": 2200.0,
             "width": 1500.0, "height": 1400.0, "sill": 900.0},
            {"id": "DR-01", "host": "W-E", "kind": "door", "at": 900.0,
             "width": 900.0, "height": 2100.0, "sill": 0.0},
        ],
        "lighting": [
            {"id": fid, "at": [x, y], "mounting_height": z, "layer": layer,
             "ies": f"{ies_dir.rstrip('/')}/{ies}", "ies_file": ies,
             "lumens": lm, "kelvin": k, "output": 1.0,
             "luminous_size_mm": 200.0 if layer == "ambient" else 60.0}
            for fid, ies, x, y, z, layer, lm, k in FIXTURES
        ],
        "furniture": [],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ies-dir", required=True,
                    help="IES folder path ON THE RENDERING MACHINE")
    ap.add_argument("--out", type=Path, default=Path("out/bedroom.json"))
    a = ap.parse_args()

    data = build(a.ies_dir)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"{a.out}  {len(data['walls'])} walls, {len(data['rooms'])} room, "
          f"{len(data['openings'])} openings, "
          f"{len(data['lighting'])} fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
