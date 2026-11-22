"""The LDS layers: sun, privacy, views out, wind, inventory. Every number is computed from the model."""
from __future__ import annotations

import csv
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from ... import solar, villa_env as E
from ...orientation import sun_direction
from . import grid as G, model as M, raycast as RC

DATES = {"summer-solstice": "2026-06-21", "equinox": "2026-03-20", "winter-solstice": "2026-12-21"}
STEP_MIN = 15
EPS = 1e-6


# ------------------------------------------------------------------------------------------------ sun
def sunlit_matrix(day, origins, lat=E.LATITUDE, lon=E.LONGITUDE, tz=E.TIME_ZONE, step_min=STEP_MIN):
    """(std_minute_midpoints[T], sunlit[T, n]) for the sun above the horizon at each mid-interval of the day.
    Minutes are local STANDARD time (UTC+tz), as in the project's garden_sun."""
    mids, dirs = [], []
    for m in range(0, 24 * 60, step_min):
        mid = m + step_min / 2
        when = datetime.fromisoformat(day).replace(tzinfo=timezone.utc) + timedelta(minutes=mid) - timedelta(hours=tz)
        s = solar.sun_position(when, lat, lon)
        if s.altitude > 0:
            mids.append(mid)
            dirs.append(np.array(sun_direction(s.azimuth, s.altitude)))
    n, T = len(origins), len(dirs)
    O = np.repeat(origins, T, axis=0)
    D = np.tile(np.array(dirs) * 300.0, (n, 1))
    lit = ~RC.blocked(O, D, 0.001 / 300.0, 1.0)
    return np.array(mids), lit.reshape(n, T).T


def sun_layers(cls, zs, lat=E.LATITUDE, lon=E.LONGITUDE):
    """Hours of direct sun per analysed cell, as (NY, NX) arrays (NaN = not analysed)."""
    idx = np.argwhere(np.isin(cls, M.ANALYSED))
    X, Y = G.centres()
    origins = np.array([[X[j, i], Y[j, i], zs[j, i] + 0.05] for j, i in idx])
    layers = {}
    h = STEP_MIN / 60.0

    def put(name, vals):
        a = np.full((G.NY, G.NX), np.nan)
        a[idx[:, 0], idx[:, 1]] = vals
        layers[name] = a

    for key, day in DATES.items():
        mids, lit = sunlit_matrix(day, origins, lat, lon)
        put("sun_hours_" + key.replace("-", "_"), lit.sum(0) * h)
        if key == "summer-solstice":
            for name, lo, hi in (("summer_evening_17_20_standard_time", 17, 20), ("summer_evening_17_20_dst_clock", 16, 19)):
                w = (mids >= lo * 60) & (mids < hi * 60)
                put(name, lit[w].sum(0) * h)
        if key == "winter-solstice":
            w = (mids >= 10 * 60) & (mids < 15 * 60)
            put("winter_day_10_15", lit[w].sum(0) * h)
    return layers


# ------------------------------------------------------------------------------------------------ privacy
BOUNDARIES = {   # axis ('y' = a line y = value), value, along-range, viewer groups, existing screen top z
    "east-fence": ("y", M.Y1I, (M.X0I, M.X1I), ("neighbour-east",), M.FENCE_TOP_Z),
    "rear-fence": ("x", M.X1I, (M.AXIS, M.Y1I), ("neighbour-rear",), M.FENCE_TOP_Z),
    "sister-line": ("y", M.AXIS, (M.X0I, M.X1I), ("sister-openings", "sister-yard", "entrance-steps"), None),
    "street-fence": ("x", M.X0I, (M.AXIS, M.Y1I), ("street",), M.FENCE_TOP_Z),
}
SEG = 0.5
BANDS = (0.0, 1.0, 2.0, 3.0, 99.0)


def privacy(cls, zs):
    idx = np.argwhere(np.isin(cls, M.ANALYSED))
    X, Y = G.centres()
    cx = np.array([X[j, i] for j, i in idx]); cy = np.array([Y[j, i] for j, i in idx]); cz = zs[idx[:, 0], idx[:, 1]]
    V = M.viewers()
    groups = sorted({v["group"] for v in V})
    count = {(g, c): np.zeros(len(idx), int) for g in groups for c in ("standing", "seated")}
    seg_n = {b: int(math.ceil((v[2][1] - v[2][0]) / SEG)) for b, v in BOUNDARIES.items()}
    # req[b][(group, class)] -> (segments, bands) array of the highest visible-sightline crossing z
    req = {b: {(g, c): np.full((seg_n[b], len(BANDS) - 1), np.nan) for g in BOUNDARIES[b][3] for c in ("standing", "seated")} for b in BOUNDARIES}
    for v in V:
        eye = np.array(v["eye"])
        for cname, eh in (("standing", M.EYE_STANDING), ("seated", M.EYE_SEATED)):
            tgt = np.stack([cx, cy, cz + eh], 1)
            d = tgt - eye
            vis = ~RC.blocked(np.tile(eye, (len(tgt), 1)), d, EPS, 1 - EPS)
            count[(v["group"], cname)] += vis
            for b, (ax, val, rng, grs, _) in BOUNDARIES.items():
                if v["group"] not in grs:
                    continue
                e_n = eye[1] if ax == "y" else eye[0]
                t_n = tgt[:, 1] if ax == "y" else tgt[:, 0]
                t = (val - e_n) / np.where(t_n == e_n, np.nan, t_n - e_n)
                ok = vis & (t > 0) & (t < 1)
                along = (eye[0] if ax == "y" else eye[1]) + t * ((tgt[:, 0] if ax == "y" else tgt[:, 1]) - (eye[0] if ax == "y" else eye[1]))
                zc = eye[2] + t * (tgt[:, 2] - eye[2])
                dist = np.abs(t_n - val)
                for k in np.nonzero(ok)[0]:
                    s = int((along[k] - rng[0]) // SEG)
                    if 0 <= s < seg_n[b]:
                        bi = int(np.searchsorted(BANDS, dist[k], side="right") - 1)
                        cur = req[b][(v["group"], cname)][s, bi]
                        if np.isnan(cur) or zc[k] > cur:
                            req[b][(v["group"], cname)][s, bi] = zc[k]
    layers = {}
    for g in groups:
        for c in ("standing", "seated"):
            a = np.full((G.NY, G.NX), np.nan); a[idx[:, 0], idx[:, 1]] = count[(g, c)]
            layers["overlooking_eyes_%s_%s" % (g.replace("-", "_"), c)] = a
    anyc = {c: sum(count[(g, c)] for g in groups if g != "street") for c in ("standing", "seated")}
    for c in anyc:
        a = np.full((G.NY, G.NX), np.nan); a[idx[:, 0], idx[:, 1]] = anyc[c]
        layers["overlooking_eyes_any_%s" % c] = a
    return V, groups, layers, req


def boundary_table(req):
    """Per boundary, per 0.5 m segment: the screen TOP (absolute z, m) needed to block every visible sightline that crosses it,
    by distance band of the protected target behind the line, for standing and seated targets; also per viewer group."""
    out = {}
    for b, (ax, val, rng, grs, top) in BOUNDARIES.items():
        n = next(iter(req[b].values())).shape[0]
        rows = []
        for s in range(n):
            row = {"along_m": [round(rng[0] + s * SEG, 3), round(min(rng[0] + (s + 1) * SEG, rng[1]), 3)], "by_group": {}}
            for c in ("standing", "seated"):
                st = np.stack([req[b][(g, c)][s] for g in grs])
                r = np.where(np.all(np.isnan(st), axis=0), np.nan, np.nanmax(np.where(np.isnan(st), -1e9, st), axis=0))
                row["required_top_z_" + c] = [None if np.isnan(x) else round(float(x), 3) for x in r]
                allv = r[~np.isnan(r)]
                row["required_top_z_%s_any_band" % c] = round(float(allv.max()), 3) if len(allv) else None
            for g in grs:
                row["by_group"][g] = {c: [None if np.isnan(x) else round(float(x), 3) for x in req[b][(g, c)][s]] for c in ("standing", "seated")}
            rows.append(row)
        out[b] = dict(axis=ax, line_m=round(val, 3), along_range_m=[round(rng[0], 3), round(rng[1], 3)],
                      viewer_groups=list(grs), existing_screen_top_z_m=top, ground_z_m=M.GROUND_Z,
                      distance_bands_m=[[BANDS[i], BANDS[i + 1] if BANDS[i + 1] < 90 else None] for i in range(len(BANDS) - 1)],
                      segments=rows)
    return out


# ------------------------------------------------------------------------------------------------ views out
ROOM_EYE = {"kitchen": M.EYE_STANDING, "dirty-kitchen": M.EYE_STANDING}   # standing at the counter; others seated
INSET = 1.0                                                                # eye this far inside the aperture plane (policy)


def views(cls, zs, openings):
    idx = np.argwhere(np.isin(cls, M.ANALYSED))
    X, Y = G.centres()
    tx = np.array([X[j, i] for j, i in idx]); ty = np.array([Y[j, i] for j, i in idx]); tz0 = zs[idx[:, 0], idx[:, 1]]
    seen = {}   # room -> bool per cell
    per_opening = {}
    for o in openings:
        if o["level"] == "APT" or o["room"] in ("?", "family-bath"):
            continue
        floor = M.LEVEL_Z[o["level"]]
        eh = ROOM_EYE.get(o["room"], M.EYE_SEATED)
        n = o["n"]
        ax = 0 if n[0] else 1                      # axis normal to the face
        lat = 1 - ax
        vis = np.zeros(len(idx), bool)
        for off in (-o["w"] / 4, 0.0, o["w"] / 4):
            eye = np.zeros(3); eye[ax] = o["f"] - n[ax] * INSET; eye[lat] = o["c"] + off; eye[2] = floor + eh
            tgt = np.stack([tx, ty, tz0 + M.EYE_SEATED], 1)
            d = tgt - eye
            tn = (o["f"] - eye[ax]) / np.where(d[:, ax] == 0, np.nan, d[:, ax])
            P = eye + tn[:, None] * d
            ok = (tn > 0) & (tn < 1) & (np.abs(P[:, lat] - o["c"]) <= o["w"] / 2) \
                & (P[:, 2] >= floor + o["sill"]) & (P[:, 2] <= floor + o["head"])
            sel = np.nonzero(ok)[0]
            if not len(sel):
                continue
            unit = d[sel] / np.linalg.norm(d[sel], axis=1)[:, None]
            start = P[sel] + 0.02 * unit
            clear = ~RC.blocked(start, tgt[sel] - start, EPS, 1 - EPS)
            vis[sel[clear]] = True
        per_opening[o["id"]] = dict(room=o["room"], level=o["level"], zone=M.opening_zone(o), cells_seen=int(vis.sum()),
                                    eye_z_m=round(floor + eh, 3))
        seen[o["room"]] = seen.get(o["room"], np.zeros(len(idx), bool)) | vis
    rooms = sorted(seen)
    n_rooms = np.full((G.NY, G.NX), np.nan); n_rooms[idx[:, 0], idx[:, 1]] = sum(seen[r].astype(int) for r in rooms)
    per_room = {}
    for r in rooms:
        a = np.full((G.NY, G.NX), np.nan); a[idx[:, 0], idx[:, 1]] = seen[r].astype(float)
        per_room[r] = a
    return per_opening, n_rooms, per_room


def focal_candidates(n_rooms, per_room, zone_idx, cls, k=3, patch=6):
    """Per zone the k best non-overlapping patch x patch (1.5 m) areas by mean number of rooms that see the cell.
    Patches lie wholly inside one zone on analysed cells."""
    out = {}
    names = list(M.ZONES)
    for zi, zn in enumerate(names):
        if zn in ("east-ramp", "east-deck"):
            continue                                   # car ramp and parking deck: structure, not garden
        ok = (zone_idx == zi) & np.isin(cls, M.ANALYSED)
        score = np.full((G.NY, G.NX), -1.0)
        for j in range(G.NY - patch + 1):
            for i in range(G.NX - patch + 1):
                if ok[j:j + patch, i:i + patch].all():
                    score[j, i] = np.nanmean(n_rooms[j:j + patch, i:i + patch])
        picks = []
        used = np.zeros_like(ok)
        for _ in range(k):
            s = np.where(used, -1.0, score)
            if s.max() <= 0:
                break
            j, i = np.unravel_index(np.argmax(s), s.shape)
            used[max(0, j - patch + 1):j + patch, max(0, i - patch + 1):i + patch] = True
            sl = (slice(j, j + patch), slice(i, i + patch))
            seeing = [r for r, a in per_room.items() if np.nanmean(a[sl]) >= 0.5]
            picks.append(dict(centre_m=[round(G.ORIGIN_X + (i + patch / 2) * G.CELL, 3), round(G.ORIGIN_Y + (j + patch / 2) * G.CELL, 3)],
                              patch_m=patch * G.CELL, mean_rooms_seeing=round(float(s[j, i]), 2), rooms_seeing_half_or_more=seeing))
        out[zn] = picks
    return out


# ------------------------------------------------------------------------------------------------ wind (held TMYx weather)
EPW = Path.home() / "archpipe" / "weather" / "EGY_QH_Cairo.West.AP.623680_TMYx.epw"
SECTORS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
# TRUE bearing the client's sides face (site-orientation.json: model +y bearing 20 deg; the street (-x) faces 290)
CLIENT_SIDE_BEARING = {"north (street, -x)": 290.0, "east (+y)": 20.0, "south (+x)": 110.0, "west (sister, -y)": 200.0}


def wind(epw=EPW):
    rows = []
    with open(epw, newline="") as f:
        for k, r in enumerate(csv.reader(f)):
            if k >= 8:
                rows.append((int(r[1]), int(r[3]), float(r[20]), float(r[21])))   # month, hour-ending, dir (from), speed m/s
    sets = {
        "all-year": lambda m, h: True,
        "summer-evening-17-20 (Jun-Aug)": lambda m, h: m in (6, 7, 8) and h in (18, 19, 20),
        "winter-day-10-15 (Dec-Feb)": lambda m, h: m in (12, 1, 2) and 11 <= h <= 15,
    }
    out = {}
    for name, f in sets.items():
        sel = [(d, s) for m, h, d, s in rows if f(m, h)]
        n = len(sel)
        sec = []
        for k, sn in enumerate(SECTORS):
            c = k * 22.5
            members = [s for d, s in sel if s > 0 and abs((d - c + 180) % 360 - 180) <= 11.25]
            sec.append(dict(sector=sn, from_bearing_true=c, share_pct=round(100 * len(members) / n, 2),
                            mean_speed_ms=round(sum(members) / len(members), 2) if members else None))
        calm = sum(1 for d, s in sel if s == 0)
        side = {}
        for sname, b in CLIENT_SIDE_BEARING.items():
            side[sname] = round(100 * sum(1 for d, s in sel if s > 0 and abs((d - b + 180) % 360 - 180) <= 45) / n, 2)
        out[name] = dict(hours=n, calm_pct=round(100 * calm / n, 2), mean_speed_ms=round(sum(s for d, s in sel) / n, 2),
                         sectors=sec, share_by_client_side_pct=side)
    return out
