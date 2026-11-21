"""Reduce a built scene.json (600+ MB) to the faces a section or elevation needs, as a small JSON (metres, scene z).

Kept: `shell` meshes (walls, slabs, glass, stair, rails: our building) and `context` meshes whose centre lies inside our
footprint (apartment above, shared core). Dropped: ground (drawn analytically), furniture, dressing, fixtures,
neighbours, fence and street (they hide the building in an elevation; the fence top is annotated instead).
Scene z: B floor -3.0, GF 0, L1 3.0, roof 6.0; Revit level = scene + 1.2.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

# Shell meshes are merged by material across the whole plot (fence, sister villa and neighbour faces share a mesh with
# ours), so the filter is per FACE: a face with any vertex beyond the box (street / rear / east fence boxes and their long
# top faces, the sister's side, the plot ground) is dropped.
FACE_BOX = (-0.15, -31.4, 22.8, -20.5)       # x0, y0, x1, y1: a face with any vertex outside is not ours
FOOTPRINT = (3.4, -31.3, 22.8, -23.4)     # model x0, y0, x1, y1 metres, our bar plus the core ends (villa_env.BAR +- 0.2)
Z_REVIT_OFFSET = 1.2


def _centre(faces):
    xs = [p[0] for f in faces for p in f]
    ys = [p[1] for f in faces for p in f]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2


def slim(scene_path: Path | str, out_path: Path | str) -> dict:
    raw = Path(scene_path).read_bytes()
    d = json.loads(raw)
    x0, y0, x1, y1 = FOOTPRINT
    polys, kept, dropped = [], {"shell": 0, "context": 0}, 0
    for m in d["meshes"]:
        g = m.get("group")
        if g not in ("shell", "context") or "paving" in m["id"] or not m["faces"]:
            continue
        if g == "context":
            cx, cy = _centre(m["faces"])
            if not (x0 <= cx <= x1 and y0 <= cy <= y1):
                continue
        kept[g] += 1
        for f in m["faces"]:
            xs, ys = [v[0] for v in f], [v[1] for v in f]
            if min(xs) < FACE_BOX[0] or max(xs) > FACE_BOX[2] or min(ys) < FACE_BOX[1] or max(ys) > FACE_BOX[3]:
                dropped += 1
                continue
            polys.append({"p": [[round(c, 4) for c in v] for v in f], "m": m["material"], "g": g})
    out = {"schema": "archpipe-slim-scene/1", "source_sha256": hashlib.sha256(raw).hexdigest(), "scene_id": d.get("id"),
           "kept_meshes": kept, "faces_dropped_outside_plot_box": dropped, "faces": polys}
    Path(out_path).write_text(json.dumps(out), encoding="utf-8")
    return {"faces": len(polys), "kept": kept, "source_sha256": out["source_sha256"]}
