"""Site layers (LDS) sampled on the 0.25 m grid, and the zone frames used by the generator.

Model frame (metres): client north (street) = -x, east = +y, south = +x, west (sister plot) = -y.
S-garden local frame: a = x - 22.597 (0 at the house face, 5.71 at the rear fence), b = y + 29.916
(0 at the open sister line, 9.315 at the east fence).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SITE = ROOT / "knowledge" / "landscape" / "site"
ORIGIN = (-0.5, -30.0)
CELL = 0.25
SX0, SY0 = 22.597, -29.916          # south garden origin
SA, SB = 5.71, 9.315                # depth (a) and width (b)
FLOOR_Z = -3.0

# zone rectangles [x0, y0, x1, y1], from LDS inventory (polygon areas 53.19 / 21.48 / 23.65 m2)
ZONES = {
    "south": [22.597, -29.916, 28.307, -20.601],
    "east": [15.412, -23.591, 22.597, -20.601],
    "north": [-0.123, -29.916, 3.617, -23.591],
}
# north court: usable ground = open (x < 2.0) plus the strip under the GF terrace slab (x 2.0-3.6),
# between the entrance-steps block (y < -28.671) and the yard wall (y > -23.841)
NORTH_USABLE = [-0.123, -28.671, 3.617, -23.841]


def to_model(a: float, b: float) -> tuple[float, float]:
    return SX0 + a, SY0 + b


def rect_to_model(r):
    (x0, y0), (x1, y1) = to_model(r[0], r[1]), to_model(r[2], r[3])
    return [round(min(x0, x1), 3), round(min(y0, y1), 3), round(max(x0, x1), 3), round(max(y0, y1), 3)]


@lru_cache(maxsize=None)
def _file(name):
    return json.load(open(SITE / f"{name}.json"))


@lru_cache(maxsize=None)
def layer(file: str, key: str):
    return _file(file)["layers"][key]


@lru_cache(maxsize=None)
def cell_class():
    return _file("inventory")["cell_class"]


import numpy as np

_CX = ORIGIN[0] + (np.arange(117) + .5) * CELL      # cell centres along x (index i)
_CY = ORIGIN[1] + (np.arange(40) + .5) * CELL       # cell centres along y (index j)


def mask(rect):
    """Boolean (40, 117) array [j, i]: cells whose centre lies in model rect [x0,y0,x1,y1]."""
    x0, y0, x1, y1 = rect
    mx = (_CX >= x0) & (_CX <= x1)
    my = (_CY >= y0) & (_CY <= y1)
    return my[:, None] & mx[None, :]


def cells(rect):
    jj, ii = np.nonzero(mask(rect))
    return list(zip(ii.tolist(), jj.tolist()))


@lru_cache(maxsize=None)
def arr(file: str, key: str):
    rows = layer(file, key)
    return np.array([[np.nan if v is None else v for v in r] for r in rows], dtype=float)


def values(file: str, key: str, rect) -> list[float]:
    a = arr(file, key)[mask(rect)]
    return a[~np.isnan(a)].tolist()


def mean(file: str, key: str, rect) -> float | None:
    v = arr(file, key)[mask(rect)]
    v = v[~np.isnan(v)]
    return float(v.mean()) if v.size else None


def point(file: str, key: str, x: float, y: float):
    i, j = int((x - ORIGIN[0]) / CELL), int((y - ORIGIN[1]) / CELL)
    if not (0 <= i < 117 and 0 <= j < 40):
        return None
    v = layer(file, key)[j][i]
    return v


GROUPS = ("apartment_above", "entrance_steps", "neighbour_east", "neighbour_rear", "sister_openings", "sister_yard", "street")
UPPER = ("apartment_above", "neighbour_east", "neighbour_rear")     # needs overhead cover, not a boundary screen
SISTER = ("sister_openings", "sister_yard")


@lru_cache(maxsize=None)
def _group(g: str, posture: str, screen_top_z):
    """(40,117) eye count of group g per cell after an optional sister-line screen (top z) is built."""
    a = np.nan_to_num(arr("privacy", f"overlooking_eyes_{g}_{posture}"))
    if screen_top_z is None or g not in SISTER:
        return a
    seg = _file("privacy")["boundaries"]["sister-line"]["segments"]
    gk = g.replace("_", "-")
    out = a.copy()
    for j, y in enumerate(_CY):
        d = y - SY0
        band = 0 if d < 1 else 1 if d < 2 else 2 if d < 3 else 3
        for i, x in enumerate(_CX):
            if out[j, i] == 0:
                continue
            need = None
            for sg in seg:
                if sg["along_m"][0] <= x < sg["along_m"][1] + 1e-9:
                    need = sg["by_group"][gk][posture][band]
                    break
            if need is None or screen_top_z >= need:
                out[j, i] = 0.0
    return out


def eyes(rect, posture="seated", *, cover_rects=(), screen_top_z=None, exclude=()) -> dict:
    """Mean number of eye points that still see a cell of `rect` after the design's screening.

    cover: cells under an overhead cover lose the upper-storey groups (apartment above, neighbours' upper
    windows): ASSUMED opaque while closed (GAP-OVERLOOK-ABOVE: no published figure).
    screen_top_z: a screen on the sister line (top z, floor -3.0) removes a sister group where the LDS
    required top z for that distance band is at or below it. `exclude`: groups left out (the client's
    open-to-the-sister-plot choice).
    """
    m = mask(rect)
    valid = ~np.isnan(arr("privacy", f"overlooking_eyes_any_{posture}"))
    m = m & valid
    n = int(m.sum())
    cov = np.zeros_like(m)
    for r in cover_rects:
        cov |= mask(r)
    out = {}
    for g in GROUPS:
        a = _group(g, posture, screen_top_z)
        if g in exclude:
            out[g] = 0.0
            continue
        sel = m & ~cov if g in UPPER else m
        out[g] = float(a[sel].sum() / n) if n else 0.0
    out["n_cells"] = n
    return out


def eyes_total(rect, posture="seated", **kw) -> float:
    e = eyes(rect, posture, **kw)
    return sum(v for k, v in e.items() if k != "n_cells")
