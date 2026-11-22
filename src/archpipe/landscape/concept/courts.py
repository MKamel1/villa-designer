"""North court and east yard candidates (model frame), each with and without the koi pond.

North court: open ground x -0.123..1.75 (full sun 2 h on 21 Jun at most), strip under the GF terrace slab x 1.75..3.617
(covered), y -28.671..-23.841; the lounge door (3.617, -26.156) opens onto it. East yard: x 15.412..22.597,
y -23.591..-20.601, the dining and living doors on its north (house) side, the dirty-kitchen window at its west end.
"""
from __future__ import annotations

import random

from shapely.geometry import box

from . import site as S
from .geom import R, circle, rbox

N_X0, N_X1, N_Y0, N_Y1 = -0.123, 3.617, -28.671, -23.841
N_OPEN_X1 = 1.75
E_X0, E_X1, E_Y0, E_Y1 = 15.412, 22.597, -23.591, -20.601


def _fits(r, bad, gap=0.0):
    b = rbox(r)
    return all(b.distance(o) >= gap - 1e-9 for o in bad)


def pond_spec(rect, rng, depth_choices=(900, 1000, 1100)):
    area = (rect[2] - rect[0]) * (rect[3] - rect[1])
    depth = rng.choice(depth_choices)
    # unaerated limit 28.7 in/m2 (LS-POND-STOCK); adult koi 70 cm = 27.6 in, so n = floor(limit*area/27.6)
    n_koi = max(2, int(28.7 * area / 27.6))
    return {"area_m2": round(area, 2), "depth_mm": depth, "volume_m3_est": round(0.7 * depth / 1000 * area, 2), "koi_count": n_koi,
            "koi_adult_length_cm": 70, "aerated": False}


def sample_north(pond: bool, rng: random.Random) -> dict | None:
    """Relaxation court: a 2-seat bench with a view, paving, planting strips, optionally the flush pond."""
    house = box(N_X1, N_Y0 - 1, N_X1 + 5, N_Y1 + 1)
    street = box(-5, N_Y0 - 1, N_X0, N_Y1 + 1)
    st = rng.choice([0.3, 0.6, 0.8, 1.0, 1.2])           # street-fence bed depth
    wst = rng.choice([0.3, 0.45])                    # bed against the steps block (south-west end)
    ewn = rng.choice([0.3, 0.45])                    # bed against the NE yard wall
    beds = [{"id": "bed-street", "rect": R(N_X0, N_Y0, N_X0 + st, N_Y1), "role": "street"},
            {"id": "bed-steps", "rect": R(N_X0 + st, N_Y0, N_OPEN_X1, N_Y0 + wst), "role": "edge"},
            {"id": "bed-wall", "rect": R(N_X0 + st, N_Y1 - ewn, N_OPEN_X1, N_Y1), "role": "edge"}]
    out = {"zone": "north", "pond": None, "beds": beds}
    pr = None
    if pond:
        w = rng.choice([1.0, 1.1, 1.2])
        l = rng.choice([1.8, 2.2, 2.6, 3.0, 3.4])
        x0 = rng.uniform(N_X0 + st + 0.3, N_OPEN_X1 - w - 0.05)
        y0 = rng.uniform(N_Y0 + wst + 0.3, N_Y1 - ewn - 0.3 - l) if N_Y1 - ewn - 0.3 - l > N_Y0 + wst + 0.3 else None
        if y0 is None or x0 + w > N_OPEN_X1:
            return None
        pr = R(x0, y0, x0 + w, y0 + l)
        out["pond"] = {"rect": pr, **pond_spec(pr, rng), "edge": "soft", "freeboard_mm": 150}
    # bench: free-standing, 0.55 x 1.4 (2 seats), on the covered paving strip, facing the open ground
    bx = rng.uniform(N_OPEN_X1, N_X1 - 1.2 - 0.55)
    by = rng.uniform(N_Y0 + 0.3, N_Y1 - 1.7)
    bench = R(bx, by, bx + 0.55, by + 1.4)
    if not _fits(bench, [house], 1.2 - 1.2 + 0.0):
        return None
    if pr and rbox(bench).distance(rbox(pr)) < 0.4:
        return None
    # door apron: 1.2 m clear in front of the lounge door, not crossed by the bench
    door = R(N_X1 - 1.2, -28.0, N_X1, -24.3)
    if rbox(door).intersects(rbox(bench)):
        return None
    out.update({"bench": bench, "quiet": R(bench[0] - 0.4, bench[1] - 0.3, bench[2] + 0.3, bench[3] + 0.3), "path": door})
    return out


def sample_east(pond: bool, rng: random.Random) -> dict | None:
    """East yard: main path along the house face (dining and living doors), planted strip to the east fence,
    optionally the flush pond between them, seen from the dining and living rooms and the dirty kitchen."""
    path = R(E_X0 + 0.5, E_Y0, E_X1, E_Y0 + 1.2)
    bw = rng.choice([0.3, 0.4, 0.5])           # planted buffer between path and pond / bed
    out = {"zone": "east", "pond": None, "path": path}
    beds = []
    ebd = rng.choice([0.4, 0.6, 0.8])           # fence-side bed depth when no pond
    if pond:
        w = rng.choice([1.0, 1.1, 1.2, 1.3])
        l = rng.choice([2.0, 2.5, 3.0, 3.5, 4.0])
        y0 = E_Y0 + 1.2 + bw
        y1 = y0 + w
        if y1 + 0.2 > E_Y1 - 0.2:
            return None
        x0 = rng.uniform(E_X0 + 1.0, E_X1 - 1.5 - l)
        pr = R(x0, y0, x0 + l, y1)
        out["pond"] = {"rect": pr, **pond_spec(pr, rng), "edge": "soft", "freeboard_mm": 150}
        beds = [{"id": "bed-pond-path", "rect": R(x0 - 0.3, E_Y0 + 1.2, x0 + l + 0.3, y0), "role": "pond-edge"},
                {"id": "bed-pond-fence", "rect": R(x0 - 0.3, y1, x0 + l + 0.3, E_Y1), "role": "pond-edge"},
                {"id": "bed-pond-end-w", "rect": R(x0 - 0.3, y0, x0, y1), "role": "pond-edge"},
                {"id": "bed-pond-end-e", "rect": R(x0 + l, y0, x0 + l + 0.3, y1), "role": "pond-edge"},
                {"id": "bed-yard-west", "rect": R(E_X0, E_Y0 + 1.2, x0 - 0.3, E_Y1), "role": "yard"},
                {"id": "bed-yard-east", "rect": R(x0 + l + 0.3, E_Y0 + 1.2, E_X1 - 0.0, E_Y1), "role": "yard"}]
        if x0 + l + 0.3 < 19.9:
            beds[-1]["rect"] = R(max(x0 + l + 0.3, 19.9), E_Y0 + 1.2, E_X1, E_Y1)
        beds = [b for b in beds if (b["rect"][2] - b["rect"][0]) > 0.25 and (b["rect"][3] - b["rect"][1]) > 0.25]
    else:
        beds = [{"id": "bed-yard", "rect": R(E_X0, E_Y1 - ebd, 19.9, E_Y1), "role": "yard"},
                {"id": "bed-yard-herb", "rect": R(rng.choice([19.9, 20.4, 20.9]), E_Y1 - rng.choice([1.0, 1.2, 1.5]), E_X1, E_Y1), "role": "yard"}]
    out["beds"] = beds
    return out
