"""Net room areas computed from the built wall faces of the model (plan rows A8, U19/U30/U31).

Net area = room rectangle minus the wall slabs (axis +/- half thickness, built from the spec's walls), the pocket
buildout walls and the kept columns that fall inside it. No Revit read-back and no untracked file is used to make the
number; the frozen Revit room areas (knowledge/parity/frozen/d1f-readback.json, option 0) are only the *reference* the
result is compared with (`compare_frozen`). A missing reference or missing input raises `NetAreaError`.
"""
from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import LineString, box
from shapely.ops import unary_union

FROZEN = Path(__file__).resolve().parents[3] / "knowledge" / "parity" / "frozen" / "d1f-readback.json"
# Stated tolerance of the equivalence claim: the largest room-area difference against the frozen Revit value we accept.
TOLERANCE_M2 = 0.15


class NetAreaError(RuntimeError):
    pass


def wall_slab(w: dict):
    """Plan footprint (metres) of a spec wall: axis buffered by half the thickness, flat ends."""
    if (w["x0"], w["y0"]) == (w["x1"], w["y1"]):
        raise NetAreaError(f"zero-length wall at {w['x0']}, {w['y0']}")
    return LineString([(w["x0"], w["y0"]), (w["x1"], w["y1"])]).buffer(w["thickness"] / 2.0, cap_style="flat")


def pocket_slab(pb: dict, lay: dict):
    """A pocket buildout (spec `pocket_buildouts`): a thin wall on the `extra_side` room's side of the wall axis."""
    t = pb["thickness"]
    if pb["wall_axis"] != "h":
        raise NetAreaError(f"pocket buildout {pb['id']}: only horizontal wall axes are supported")
    room = lay["rooms"][pb["extra_side"]]["rect"]
    up = room[1] >= pb["y"] - 1e-6                      # the named room lies on the +y side of the axis
    return box(pb["x0"], pb["y"], pb["x1"], pb["y"] + t) if up else box(pb["x0"], pb["y"] - t, pb["x1"], pb["y"])


def columns_m(columns_mm) -> list:
    return [box(a / 1000.0, b / 1000.0, c / 1000.0, d / 1000.0) for a, b, c, d in columns_mm]


def net_areas(lay: dict, sp: dict, columns_mm) -> dict[str, dict]:
    """{room id: dict(net_m2, gross_m2, walls_m2, columns_m2, polygon_mm)} from the built faces."""
    if not sp.get("walls"):
        raise NetAreaError("the spec has no walls: net areas cannot be computed")
    cols = unary_union(columns_m(columns_mm))
    pockets = [pocket_slab(p, lay) for p in sp.get("pocket_buildouts", [])]
    out = {}
    for rid, r in lay["rooms"].items():
        rect = box(*r["rect"])
        walls = unary_union([wall_slab(w) for w in sp["walls"] if w["level"] == r["level"]]
                            + [p for p, pb in zip(pockets, sp.get("pocket_buildouts", [])) if pb["level"] == r["level"]])
        net = rect.difference(walls).difference(cols)
        geoms = [net] if net.geom_type == "Polygon" else list(net.geoms)
        out[rid] = dict(
            net_m2=round(net.area, 4), gross_m2=round(rect.area, 4),
            walls_m2=round(rect.intersection(walls).area, 4), columns_m2=round(rect.intersection(cols).area, 4),
            polygon_mm=[[round(x * 1000, 1), round(y * 1000, 1)] for x, y in max(geoms, key=lambda g: g.area).exterior.coords][:-1])
    return out


def frozen_reference() -> dict[str, float]:
    """Revit's finished-face room areas of the D1 option build; rooms Revit did not read (area 0) are absent."""
    if not FROZEN.is_file():
        raise NetAreaError(f"frozen Revit reference missing: {FROZEN}")
    rooms = json.loads(FROZEN.read_text(encoding="utf-8"))["options"][0]["rooms"]
    return {r["id"]: r["area_m2"] for r in rooms if r.get("area_m2")}


def compare_frozen(net: dict[str, dict], ref: dict[str, float] | None = None) -> list[dict]:
    """One row per room: model net, Revit value (None when Revit did not read the room), deviation."""
    ref = frozen_reference() if ref is None else ref
    rows = []
    for rid, n in net.items():
        rv = ref.get(rid)
        rows.append(dict(room=rid, model_m2=n["net_m2"], revit_m2=rv, deviation_m2=None if rv is None else round(n["net_m2"] - rv, 3),
                         deviation_pct=None if not rv else round(100 * (n["net_m2"] - rv) / rv, 2)))
    return rows


def max_deviation(rows: list[dict]) -> float:
    return max((abs(r["deviation_m2"]) for r in rows if r["deviation_m2"] is not None), default=0.0)
