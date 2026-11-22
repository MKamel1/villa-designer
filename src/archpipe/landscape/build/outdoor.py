"""Graded free outdoor furniture and koi (knowledge/landscape/build/outdoor-assets.json, written by the asset search). Used only at grade A or B.

`load()` -> {role: asset row} for the roles that have a usable asset on this machine; a role with no row falls back to the labelled simple geometry
(elements.table / elements.chair) or to no fish. Nothing here invents a licence: the row's licence/author/source are carried into the object label.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

from . import policy as P
from .geom import Obj

ROOT = Path(__file__).resolve().parents[4]
TABLE = ROOT / "knowledge/landscape/build/outdoor-assets.json"
ROLES = ("dining_table", "dining_chair", "bench", "koi")


def load(path=TABLE):
    p = Path(path)
    if not p.exists():
        return {}
    rows = json.loads(p.read_text()).get("assets", [])
    out = {}
    for r in sorted(rows, key=lambda r: (r.get("grade") or "Z")):
        if r.get("role") in ROLES and r.get("grade") in ("A", "B") and r.get("role") not in out and Path(os.path.expanduser(r.get("gltf", ""))).exists():
            out[r["role"]] = r
    return out


def _yaw_of(face, front):
    """Rotation about z (deg) that turns the asset's native front direction (a Blender-frame vector, default -y) to point along `face`."""
    fx, fy = front
    return math.degrees(math.atan2(face[1], face[0]) - math.atan2(fy, fx))


def _front(a):
    return {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}[a.get("front", "-y")]


def _asset_dict(a, at, bounds, **kw):
    return dict(asset_id=a["id"], gltf=os.path.expanduser(a["gltf"]), at=list(at), bounds=tuple(bounds), grade=a["grade"], licence=a["licence"], author=a["author"],
                source=a.get("source_url", ""), native_size_m=a["size_m"], **kw)


def table_obj(oid, layout_id, center, size, g, seats, a):
    """Dining table from the graded asset, fitted to the layout table (w x d x 0.75 m). None when no asset, or its proportions do not fit (then simple geometry)."""
    if not a:
        return None
    nx, ny, nz = a["size_m"]
    w, d = size
    if not (0.6 <= (nx / ny) / (w / d) <= 1.6):
        return None
    cx, cy = center
    h = P.TABLE["h"]
    return Obj(oid, "table", "dining table for %d: graded %s asset %s (%s, %s), fitted to %.1f x %.1f x %.2f m" % (seats, a["grade"], a["id"], a["licence"], a["author"], w, d, h),
               rests_on=("ground",), layout_id=layout_id, footprint=(cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2), footprint_mode="bbox",
               asset=_asset_dict(a, (cx, cy, g), (cx - w / 2, cy - d / 2, g, cx + w / 2, cy + d / 2, g + h), mode="box", box_m=[w, d, h], yaw_deg=0.0), meta=dict(seats=seats))


def chairs(table_id, center, size, seats, g, a):
    from . import elements as E
    if not a:
        return E.chairs_for(table_id, center, size, seats, g)
    out = []
    spots = E.chair_spots(center, size, seats)
    for i, ((x, y), face) in enumerate(spots):
        h = P.CHAIR["back_h"]
        nx, ny, nz = a["size_m"]
        sc = h / nz
        yaw = _yaw_of(face, _front(a))
        c, s = abs(math.cos(math.radians(yaw))), abs(math.sin(math.radians(yaw)))
        w, d = (nx * c + ny * s) * sc, (nx * s + ny * c) * sc
        out.append(Obj("ld-%s-chair-%d" % (table_id, i), "chair", "dining chair: graded %s asset %s (%s, %s), scaled to %.2f m high" % (a["grade"], a["id"], a["licence"], a["author"], h),
                       rests_on=("ground",), footprint_mode=None, asset=_asset_dict(a, (x, y, g), (x - w / 2, y - d / 2, g, x + w / 2, y + d / 2, g + h), mode="height", yaw_deg=yaw)))
    return out


def fish_obj(oid, a, pos, length, yaw):
    """Koi swimming at `pos` (x, y, z of its centre), `length` m long, heading `yaw` deg. Mode 'fish' anchors the bbox centre."""
    x, y, z = pos
    nx, ny, nz = a["size_m"]
    sc = length / max(nx, ny, nz)
    r = length / 2
    return Obj(oid, "koi", "koi, graded %s asset %s (%s, %s), %.2f m long" % (a["grade"], a["id"], a["licence"], a["author"], length), footprint_mode=None,
               asset=_asset_dict(a, (x, y, z), (x - r, y - r, z - 0.1, x + r, y + r, z + 0.1), mode="fish", length_m=length, yaw_deg=yaw), meta=dict(species="koi"))
