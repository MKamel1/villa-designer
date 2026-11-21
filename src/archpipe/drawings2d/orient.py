"""Client orientation for drawings (plan convention, lane RV2 step 1).

Client convention (memory `feedback_orientation_naming`): the street side (model -x) is NORTH, model +y is EAST,
model +x is SOUTH, model -y is WEST. A plan is drawn north-up, so sheet (X right, Y up) = (model y, -model x):
a pure rotation by -90 degrees, no mirroring. `to_client` returns copies of the design elements already in that frame
so the plan drawing code (which treats +Y as north) needs no further change. True north (site plan only, 70 degrees clockwise of sheet-up) is a
labelled secondary.
"""
from __future__ import annotations

import dataclasses

from archpipe.contracts import DesignElement

TRUE_NORTH_CW_FROM_CLIENT_NORTH_DEG = 70.0   # street facade faces true azimuth 290 (villa_env.STREET_FACADE_AZIMUTH), so true N is 70 deg clockwise of sheet-up
LOCAL_FRAME_KINDS = {"door", "window", "furniture", "luminaire", "fixture", "plant", "device"}   # size in own frame


def pt(x: float, y: float) -> tuple[float, float]:
    """Model (x, y) -> client sheet frame (east, north)."""
    return (y, -x)


def inv(x: float, y: float) -> tuple[float, float]:
    """Client sheet frame -> model (x, y)."""
    return (-y, x)


def _poly(v):
    return [pt(p[0], p[1]) for p in v]


def _box(b):          # [x0, y0, z0, x1, y1, z1] mm
    xs = sorted((b[0], b[3]))
    ys = sorted((b[1], b[4]))
    return [ys[0], -xs[1], b[2], ys[1], -xs[0], b[5]]


_SKIP = {"profile_xz_mm", "tread_top_z_mm", "edge_lengths_mm"}


def _num(v):
    return isinstance(v, (int, float))


def _val(k: str, v):
    """Transform one `*_mm` value by shape: point lists, 6-number boxes, [x0,y0,x1,y1] rects, one point."""
    if not isinstance(v, (list, tuple)) or not v or k in _SKIP:
        return v
    if all(isinstance(q, (list, tuple)) for q in v):
        if all(len(q) == 6 for q in v):
            return [_box(q) for q in v]
        if all(len(q) in (2, 3) and all(_num(c) for c in q) for q in v):
            return [[*pt(q[0], q[1]), *q[2:]] for q in v]
        return [_val(k, q) for q in v]
    if len(v) == 2 and all(_num(c) for c in v):
        return list(pt(*v))
    if len(v) == 4 and all(_num(c) for c in v):
        a, b = pt(v[0], v[1]), pt(v[2], v[3])
        return [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]
    return v


def _params(p: dict) -> dict:
    q = dict(p)
    if all(k in q for k in ("x0_mm", "y0_mm", "x1_mm", "y1_mm")):
        q["x0_mm"], q["y0_mm"] = pt(p["x0_mm"], p["y0_mm"])
        q["x1_mm"], q["y1_mm"] = pt(p["x1_mm"], p["y1_mm"])
    for k, v in p.items():
        if k.endswith("_mm") and isinstance(v, (list, tuple)):
            q[k] = _val(k, v)
    for k in ("along", "aim"):
        if isinstance(q.get(k), (list, tuple)) and len(q[k]) == 3:
            q[k] = [q[k][1], -q[k][0], q[k][2]]
    q["frame"] = "client"
    return q


def to_client(els: list[DesignElement]) -> list[DesignElement]:
    out = []
    for e in els:
        if e.params.get("frame") == "client":
            raise ValueError("%s is already in the client frame" % e.id)
        x, y = pt(e.placement[0], e.placement[1])
        if e.kind in LOCAL_FRAME_KINDS:
            size, rot = e.size, e.rotation_deg - 90.0
        else:
            size, rot = (e.size[1], e.size[0], e.size[2]), e.rotation_deg
        out.append(dataclasses.replace(e, placement=(x, y, e.placement[2]), size=size, rotation_deg=rot,
                                       params=_params(e.params)))
    return out


def compass_of_model_vector(dx: float, dy: float) -> str:
    """Client compass word for a model direction: -x N, +y E, +x S, -y W (dominant axis)."""
    if abs(dx) >= abs(dy):
        return "S" if dx > 0 else "N"
    return "E" if dy > 0 else "W"
