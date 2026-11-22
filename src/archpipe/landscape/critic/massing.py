"""Quick 3D massing view of a `landscape-layout/1`: `massing_png(layout, path)` writes an oblique bird's-eye clay render.

Trees are canopy ellipsoids at MATURE spread and height on a trunk; drifts are low domes per plant (height capped at DRIFT_CAP_M);
beds, paving and water are slabs; screens, walls, the pergola (posts + beams + roof slats), tables and seats are boxes; the house
is a context box (BUILDING_H_M is ASSUMED: footprints carry no height); boundary fences and walls over 2.5 m are drawn see-through. The Blender run goes through jobq (docs/lanes/L8-runner.md).
It is a spatial read of the plan, not a render of materials or light: judge enclosure, scale and shade, not finish.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
from pathlib import Path

from .common import extent, plant_positions, rect_poly, species_info
from .plan import _kind_of

BUILDING_H_M = 6.0          # assumed context height (no height in the layout)
FENCE_H_M = 4.0            # LDS boundary fence height; drawn see-through
DRIFT_CAP_M = 1.2           # beds are shown as low masses
BLENDER = os.path.expanduser("~/opt/blender/blender")
JOBQ = os.path.expanduser("~/archpipe/bin/jobq")
SCRIPT = Path(__file__).with_name("massing_blender.py")


def _p(pt):                 # model (x south, y east) -> plot (east, north)
    return (pt[1], -pt[0])


def _rect(r):
    xs = [r[1], r[3]]; ys = [-r[0], -r[2]]
    return (min(xs), min(ys), max(xs), max(ys))


def build_spec(layout: dict, view=None, azimuth=25.0, elevation=52.0, size=(1400, 900)) -> dict:
    mx0, my0, mx1, my1 = view or extent(layout, pad=2.0)
    bounds = (my0, -mx1, my1, -mx0)                          # plot frame
    sol = []
    slab = lambda poly, z0, z1, mt: sol.append({"kind": "slab", "poly": [list(q) for q in poly], "z0": z0, "z1": z1, "mat": mt})
    box = lambda r, z0, z1, mt: sol.append({"kind": "box", "rect": list(_rect(r)), "z0": z0, "z1": z1, "mat": mt})
    seen = set()
    for b in layout.get("buildings", []):
        k = tuple(round(v, 2) for v in b)
        if k not in seen: seen.add(k); box(b, 0, BUILDING_H_M, "house")
    for z in layout.get("zones", []):
        if z.get("surface") == "water" and z.get("rect"): box(z["rect"], -0.2, 0.02, "water")
    for a in layout.get("paved_areas", []):
        if a.get("rect"): box(a["rect"], 0, 0.05, "paving" if _kind_of(a.get("material", "")) != "deck" else "wood")
    for g in layout.get("planting_groups", []):
        if g.get("rect"): box(g["rect"], 0, 0.12, "bed")
    for f in layout.get("features", []):
        if f.get("kind") == "pond":
            if f.get("rect"): box(f["rect"], -0.3, 0.03, "water")
            elif f.get("center"):
                c = _p(f["center"]); r = (f.get("diameter_m") or 1) / 2
                sol.append({"kind": "cylinder", "at": [c[0], c[1]], "z0": -0.3, "z1": 0.03, "r": r, "mat": "water"})
        elif f.get("kind") == "bbq" and f.get("rect"): box(f["rect"], 0, 0.9, "furn")
    for p in layout.get("paths", []):
        if p.get("rect"): box(p["rect"], 0, 0.06, "paving")
    for s in layout.get("seating", []):
        if s.get("rect"): box(s["rect"], 0, 0.45, "furn")
    for t in layout.get("tables", []):
        c = t["center"]; sz = t.get("size_m") or [t.get("diameter_m", 1.0)] * 2
        box([c[0] - sz[0] / 2, c[1] - sz[1] / 2, c[0] + sz[0] / 2, c[1] + sz[1] / 2], 0, 0.75, "furn")
    for sc in layout.get("screens", []):
        if sc.get("rect"): box(sc["rect"], 0, sc.get("height_m", 2.0), "screen" if sc.get("kind") == "hedge" else "wall")
    for w in layout.get("walls", []):
        if w.get("rect"): box(w["rect"], 0, w.get("height_m", 2.0), "ghost" if w.get("height_m", 2.0) > 2.5 else "wall")
    for o in layout.get("obstacles", []):
        if o.get("rect"): box(o["rect"], 0, FENCE_H_M, "ghost")
    for cn in layout.get("canopies", []):
        if not cn.get("rect"): continue
        h = cn.get("height_m", 3.0); x0, y0, x1, y1 = _rect(cn["rect"])
        for qx, qy in ((x0, y0), (x0, y1), (x1, y0), (x1, y1)): sol.append({"kind": "box", "rect": [qx - .08, qy - .08, qx + .08, qy + .08], "z0": 0, "z1": h, "mat": "wood"})
        n = max(2, int((x1 - x0) / 0.5)) if (x1 - x0) >= (y1 - y0) else max(2, int((y1 - y0) / 0.5))
        for i in range(n):
            t = (i + .5) / n
            r = [x0 + (x1 - x0) * t - .04, y0, x0 + (x1 - x0) * t + .04, y1] if (x1 - x0) >= (y1 - y0) else [x0, y0 + (y1 - y0) * t - .04, x1, y0 + (y1 - y0) * t + .04]
            sol.append({"kind": "box", "rect": r, "z0": h, "z1": h + .12, "mat": "wood"})
    pls = plant_positions(layout)
    drifts = {}
    for q in pls:
        if q["layer"] in ("canopy", "understorey"):
            info = species_info(q["species"], q["form"]); h = max(2.0, info["height_m"] or q["spread"] * 1.1)
            for t in layout.get("trees", []):
                if t["id"] == q["group"] and t.get("mature_height_m"): h = t["mature_height_m"]
            c = _p(q["at"]); r = q["spread"] / 2; trunk = max(1.0, 0.3 * h)
            sol.append({"kind": "cylinder", "at": [c[0], c[1]], "z0": 0, "z1": trunk + .2, "r": .12, "mat": "trunk"})
            sol.append({"kind": "ellipsoid", "at": [c[0], c[1], trunk + (h - trunk) / 2], "rx": r, "rz": (h - trunk) / 2, "mat": "tree"})
        else:
            drifts.setdefault((q["group"], q["species"]), []).append(q)
    for (_, sp), qs in drifts.items():                       # a drift = its plants' mature spreads as low domes (they overlap into one mass)
        info = species_info(sp, qs[0]["form"]); h = min(DRIFT_CAP_M, max(0.3, info["height_m"] or 0.6))
        for q in qs:
            c = _p(q["at"])
            sol.append({"kind": "ellipsoid", "at": [c[0], c[1], 0.12 + h / 2], "rx": q["spread"] / 2, "rz": h / 2, "mat": "drift"})
    W, H = bounds[2] - bounds[0], bounds[3] - bounds[1]
    return {"bounds": list(bounds), "solids": sol, "azimuth": azimuth, "elevation": elevation, "size": list(size),
            "distance": round(max(W, H) * 1.0 + 5, 1), "assumed": {"building_height_m": BUILDING_H_M, "drift_cap_m": DRIFT_CAP_M}}


def massing_png(layout: dict, path: str, view=None, azimuth: float = 25.0, elevation: float = 52.0, timeout_s: int = 900) -> str:
    """Render the clay massing view to `path` (through jobq, GPU lock). `view` = [x0, y0, x1, y1] model metres. Raises if the job fails."""
    spec = build_spec(layout, view, azimuth, elevation)
    path = str(Path(path).resolve()); Path(path).parent.mkdir(parents=True, exist_ok=True)
    jid = "ldc-massing-" + hashlib.sha1((json.dumps(spec, sort_keys=True) + path).encode()).hexdigest()[:12]
    sp = Path(path).with_suffix(".spec.json"); sp.write_text(json.dumps(spec))
    cmd = [JOBQ, "submit", "--gpu", "--timeout", str(timeout_s), "--id", jid, "--",
           BLENDER, "-b", "--factory-startup", "--python-exit-code", "1", "-P", str(SCRIPT), "--", str(sp), path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0: r = subprocess.run([JOBQ, "wait", jid], capture_output=True, text=True)
    if r.returncode != 0 or not Path(path).exists():
        raise RuntimeError(f"massing job {jid} failed (exit {r.returncode}): {r.stdout[-400:]} {r.stderr[-400:]}; log: ~/archpipe/queue/jobs/{jid}/job.log")
    return path
