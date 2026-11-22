"""Read-only access to the LDS site layers (knowledge/landscape/site) for the critics, plus the layout's own
shade (trees, pergolas) and sight-line screening computed on top of them."""
from __future__ import annotations

import functools
import json
import math
from datetime import datetime, timedelta, timezone

import numpy as np

from .common import KNOW, species_info

FLOOR_Z = -3.0
ORX, ORY, CELL, NX, NY = -0.5, -30.0, 0.25, 117, 40
EVENING = ("2026-06-21", 16 * 60, 19 * 60)      # 17-20 on the DST clock = 16-19 standard time (lead decision 2026-11-22)
WINTER = ("2026-12-21", 10 * 60, 15 * 60)
# ASSUMED crown density (share of sun blocked under a crown): ours, no source; stated in docs/lanes/LDC.md
CROWN = {"evergreen": 0.8, "deciduous_summer": 0.7, "deciduous_winter": 0.15}


@functools.lru_cache(maxsize=None)
def _json(name):
    return json.loads((KNOW / "site" / name).read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=None)
def layer(file, name):
    rows = _json(file)["layers"][name]
    return np.array([[np.nan if v is None else v for v in r] for r in rows], float)


def sample(file, name, pt):
    """Layer value at model point (x, y); None when outside the grid or not analysed."""
    i, j = int((pt[0] - ORX) // CELL), int((pt[1] - ORY) // CELL)
    if not (0 <= i < NX and 0 <= j < NY): return None
    v = layer(file, name)[j, i]
    return None if np.isnan(v) else float(v)


def doors():
    """Our doors into the garden zones from the LDS inventory: [{id, at, room, faces, zone, width_m}]."""
    out = []
    for zn, z in _json("inventory.json")["zones"].items():
        for o in z.get("openings", []):
            if o["kind"] == "door":
                out.append({"id": o["id"], "at": tuple(o["centre_m"]), "room": o["room"], "faces": o["faces"], "zone": zn, "width_m": o["width_m"]})
    return out


def wind_sets():
    return _json("wind.json")["sets"]


def viewers():
    return _json("privacy.json")["viewers"]


@functools.lru_cache(maxsize=None)
def _suns(day, lo, hi):
    from ... import solar, villa_env as E
    from ...orientation import sun_direction
    out = []
    for m in range(lo, hi, 15):
        mid = m + 7.5
        when = datetime.fromisoformat(day).replace(tzinfo=timezone.utc) + timedelta(minutes=mid) - timedelta(hours=E.TIME_ZONE)
        s = solar.sun_position(when, E.LATITUDE, E.LONGITUDE)
        if s.altitude > 0: out.append(np.array(sun_direction(s.azimuth, s.altitude)))
    return out


def crowns(layout, season):
    """Shading objects from the layout: trees (discs) and canopies/pergolas (rects) as dicts."""
    objs = []
    for t in layout.get("trees", []):
        info = species_info(t["species"], t.get("form"))
        habit = None
        from .common import plants_db, slug
        rec = plants_db().get(slug(t["species"]))
        if rec:
            f = rec["attributes"]["foliage"].get("value")
            habit = f and f.get("habit")
        dens = CROWN["evergreen"] if habit != "deciduous" else CROWN["deciduous_winter" if season == "winter" else "deciduous_summer"]
        H = t.get("mature_height_m") or info["height_m"] or 5.0
        R = (t.get("mature_spread_m") or info["draw_spread_m"]) / 2
        objs.append({"kind": "disc", "c": t["center"], "r": R, "z0": FLOOR_Z + 0.4 * H, "z1": FLOOR_Z + H, "d": dens})
    for c in layout.get("canopies", []) + [s for s in layout.get("screens", []) if s.get("canopy") or s.get("kind") == "pergola"]:
        if c.get("rect"):
            h = c.get("height_m", 2.5)
            objs.append({"kind": "rect", "r": c["rect"], "z0": FLOOR_Z + h, "z1": FLOOR_Z + h, "d": c.get("shade_fraction", 0.5)})
    return objs


def _hit(o, p, d):
    zc = (o["z0"] + o["z1"]) / 2
    if d[2] <= 0: return False
    t = (zc - p[2]) / d[2]
    if t <= 0: return False
    x, y = p[0] + t * d[0], p[1] + t * d[1]
    if o["kind"] == "disc": return math.hypot(x - o["c"][0], y - o["c"][1]) <= o["r"]
    x0, y0, x1, y1 = o["r"]
    return min(x0, x1) <= x <= max(x0, x1) and min(y0, y1) <= y <= max(y0, y1)


def sun_hours(layout, pt, window="evening", dz=0.5):
    """Direct sun hours at a seat: the LDS layer (structure only) reduced by the layout's own crowns and canopies.
    Returns (hours, hours_without_layout, window_hours) or None when the point is off the analysed grid."""
    day, lo, hi = EVENING if window == "evening" else WINTER
    name = "summer_evening_17_20_dst_clock" if window == "evening" else "winter_day_10_15"
    base = sample("sun.json", name, pt)
    if base is None: return None
    suns = _suns(day, lo, hi)
    objs = crowns(layout, "winter" if window == "winter" else "summer")
    p = np.array([pt[0], pt[1], FLOOR_Z + dz])
    if not suns: return (base, base, (hi - lo) / 60)
    blocked = np.mean([1 - np.prod([1 - o["d"] if _hit(o, p, d) else 1 for o in objs]) for d in suns]) if objs else 0.0
    return (base * (1 - blocked), base, (hi - lo) / 60)


def walls_objs(layout):
    out = [{"rect": w["rect"], "top": FLOOR_Z + w.get("height_m", 4.0)} for w in layout.get("walls", [])]
    return out


def screen_objs(layout):
    """Opaque sight-blocking things of the layout: screens/hedges (rect, height above floor), tree crowns count as discs."""
    out = []
    for s in layout.get("screens", []):
        if s.get("rect") and not s.get("canopy") and s.get("kind") != "pergola":
            out.append({"rect": s["rect"], "bottom": FLOOR_Z, "top": FLOOR_Z + s.get("height_m", 1.8), "d": s.get("opacity", 0.9)})
    for c in layout.get("canopies", []) + [q for q in layout.get("screens", []) if q.get("canopy") or q.get("kind") == "pergola"]:
        if c.get("rect") and c.get("shade_fraction", 0.5) >= 0.5:      # a slatted roof cuts sight lines from above
            h = FLOOR_Z + c.get("height_m", 2.5)
            out.append({"rect": c["rect"], "bottom": h - 0.1, "top": h + 0.1, "d": c.get("shade_fraction", 0.5)})
    for t in layout.get("trees", []):
        info = species_info(t["species"], t.get("form"))
        H = t.get("mature_height_m") or info["height_m"] or 5.0
        R = (t.get("mature_spread_m") or info["draw_spread_m"]) / 2
        out.append({"disc": (t["center"], R), "bottom": FLOOR_Z + 0.4 * H, "top": FLOOR_Z + H, "d": 0.6})
    return out


def _seg_blocked(a, b, o):
    """3D segment a->b (x, y, z) crosses the screen object o?"""
    from shapely.geometry import LineString, box, Point
    seg = LineString([a[:2], b[:2]])
    if "rect" in o:
        x0, y0, x1, y1 = o["rect"]; g = box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    else:
        g = Point(o["disc"][0]).buffer(o["disc"][1])
    inter = seg.intersection(g)
    if inter.is_empty: return False
    L = seg.length or 1e-9
    for pt in ([inter.interpolate(0), inter.interpolate(inter.length)] if inter.geom_type == "LineString" else [inter.centroid]):
        t = seg.project(pt) / L
        z = a[2] + t * (b[2] - a[2])
        if o["bottom"] <= z <= o["top"]: return True
    return False


GROUPS = ("apartment_above", "neighbour_east", "neighbour_rear", "sister_openings", "sister_yard")


def overlook(layout, pt, seated=True):
    """(residual_eyes, raw_eyes, {group: residual}). Raw = LDS count of eye points seeing the cell over the existing
    structure. Residual removes viewers of the groups that see the cell whose sight line to the seat is cut by a
    layout screen or tree crown (an approximation: blocked viewers are drawn from those the existing fences do not
    already block, capped at the raw count of their group)."""
    zeye = FLOOR_Z + (1.125 if seated else 1.525)
    a = (pt[0], pt[1], zeye)
    res, raw_tot, byg = 0, 0, {}
    screens = screen_objs(layout)
    existing = [{"rect": w["rect"], "bottom": FLOOR_Z, "top": FLOOR_Z + w.get("height_m", 4.0)} for w in layout.get("walls", []) if w.get("height_m", 4.0) < 4.0]
    for g in GROUPS:
        raw = sample("privacy.json", f"overlooking_eyes_{g}_{'seated' if seated else 'standing'}", pt)
        if raw is None: return None
        vs = [v for v in viewers() if v["group"].replace("-", "_") == g]
        cut = 0
        for v in vs:
            e = tuple(v["eye_m"])
            if any(_seg_blocked(a, e, o) for o in existing): continue
            if any(_seg_blocked(a, e, o) and o.get("d", 1) >= 0.5 for o in screens): cut += 1
        r = max(0, raw - cut)
        byg[g] = r; res += r; raw_tot += raw
    return res, raw_tot, byg
