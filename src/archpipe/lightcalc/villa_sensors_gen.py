"""L6b: regenerate knowledge/lighting/sensor-obstructions.json, the cells of every calculation plane where a sensor would
be invalid (inside an object, within 50 mm under one, or, for a plane that sits ON a host, over a hole in the host such as a
basin bowl or sink cutout).

    PYTHONPATH=src python -m archpipe.lightcalc.villa_sensors_gen /path/to/scene.json

Uses the independent scene-triangle test of lane LV (`archpipe.lightverify.scene_geom` / `v3_sensors`, available once LV is
merged), which reads the built scene and nothing from this engine. Planes are tested at 20 mm cells; the engine drops every
sensor point that falls in a stored rectangle (`villa_planes.blocked_rects`).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

CELL = 0.02
SKIP = ("detail", "rug", "model-rug", "shell", "floor", "ceiling", "landscape", "garden", "finish")
HOLE = 0.005                  # a hosted plane's sensor must lie within 5 mm of a host surface
UNDER, ON_SURFACE = 0.050, 0.005      # objects whose lowest point is within 50 mm over the plane; a surface within 5 mm is the host


def generate(scene_path: str, out: Path):
    import numpy as np
    from ..lightverify import scene_geom, v3_sensors
    from .villa import Villa
    from .villa_planes import build_planes
    ts = scene_geom.load_scene(scene_path)
    objs = {}
    for k, o in enumerate(ts.owner):
        if not str(o).startswith(SKIP):
            objs.setdefault(o, []).append(k)
    box = {}
    for o, idx in objs.items():
        T = ts.T[idx].reshape(-1, 3)
        box[o] = (T.min(0), T.max(0))
    data = {"source": "scene.json sha256 %s" % hashlib.sha256(Path(scene_path).read_bytes()).hexdigest()[:16],
            "cell_m": CELL, "planes": {}}
    for pl in build_planes(Villa(), filtered=False):
        xs, ys = [p[0] for p in pl.polygon], [p[1] for p in pl.polygon]
        hosted = pl.id in v3_sensors.HOSTED
        cand = [(lo, hi) for lo, hi in box.values()
                if lo[2] < pl.z + UNDER and hi[2] > pl.z + ON_SURFACE
                and lo[0] < max(xs) and hi[0] > min(xs) and lo[1] < max(ys) and hi[1] > min(ys)]
        rects = []
        nx, ny = int(np.ceil((max(xs) - min(xs)) / CELL)), int(np.ceil((max(ys) - min(ys)) / CELL))
        for j in range(ny):
            run = None
            y = min(ys) + (j + 0.5) * CELL
            for i in range(nx):
                x = min(xs) + (i + 0.5) * CELL
                bad = False
                if hosted:
                    sb = ts.surface_below(x, y, pl.z, max_depth=0.5)
                    bad = sb is None or sb[0] > HOLE
                if not bad and any(lo[0] <= x <= hi[0] and lo[1] <= y <= hi[1] for lo, hi in cand):
                    bad = bool(v3_sensors.point_findings(ts, x, y, pl.z))
                if bad and run is None:
                    run = i
                if (not bad or i == nx - 1) and run is not None:
                    end = i + 1 if bad else i
                    rects.append([round(min(xs) + run * CELL, 3), round(y - CELL / 2, 3), round(min(xs) + end * CELL, 3),
                                  round(y + CELL / 2, 3)])
                    run = None
        from .geometry import grid_in_polygon
        pts = [(x, y) for x, y in grid_in_polygon(list(pl.polygon), spacing=pl.spacing)[0]
               if not any(r[0] <= x <= r[2] and r[1] <= y <= r[3] for r in rects)]
        gaps = [ts.surface_below(x, y, pl.z, max_depth=0.5) for x, y in pts]
        data["planes"][pl.id] = {"z": round(pl.z, 4), "poly": [[round(a, 3), round(b, 3)] for a, b in pl.polygon],
                                 "rects": rects, "n_sensors": len(pts), "hosted": hosted,
                                 # worst gap (mm) from a sensor down to the host surface it sits on; None = not a hosted plane
                                 "host_gap_mm": (max((g[0] if g else 9.9) for g in gaps) * 1000 if hosted and pts else None)}
    out.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    return data


if __name__ == "__main__":
    d = generate(sys.argv[1], Path(__file__).resolve().parents[3] / "knowledge/lighting/sensor-obstructions.json")
    print({k: len(v["rects"]) for k, v in d["planes"].items()})
