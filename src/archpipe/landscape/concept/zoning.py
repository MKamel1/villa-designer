"""Step 2: zoning. Enumerate placements of each use on the LDS layers and score them; the zoning informs the idea templates.

Each enumeration is a grid of positions at 0.25 m (rooms) over the measured zone, scored from layers only (winter-day sun,
summer-evening shade on the DST clock, overlooking by seated eyes, rooms that see the cell, wind exposure). Nothing is drawn.
"""
from __future__ import annotations

import json
import math

from . import site as S
from .courts import E_X0, E_X1, E_Y0, E_Y1, N_OPEN_X1, N_X0, N_X1, N_Y0, N_Y1
from .south import A, B, table_for


def _m(file, key, rect):
    return S.mean(file, key, rect)


def _score_room(rect):
    return {"winter_h_of_5": round(_m("sun", "winter_day_10_15", rect) or 0, 2),
            "evening_sun_h_dst_of_3": round(_m("sun", "summer_evening_17_20_dst_clock", rect) or 0, 2),
            "june_h": round(_m("sun", "sun_hours_summer_solstice", rect) or 0, 2),
            "eyes_seated": round(S.eyes_total(rect, "seated"), 1),
            "rooms_seeing": round(_m("views", "rooms_seeing_cell", rect) or 0, 2)}


def build() -> dict:
    out = {"schema": "ldg-zoning/1", "step": "2 Zoning", "method": "grid enumeration at 0.25 m of each use's room on the LDS layers", "enumerations": {}}
    # --- dining rooms (south): n seats x room size x position along the house face ---------------------
    dine = []
    for n in (4, 5, 6):
        L, W = table_for(n)
        for zd_a in (3.5, 3.75, 4.0, 4.25):
            wd = max(L + 2.4, math.ceil(3.46 * n / zd_a * 4) / 4)
            if wd > B or zd_a > A:
                continue
            b = 0.0
            while b + wd <= B + 1e-9:
                r = S.rect_to_model([0, b, zd_a, b + wd])
                dine.append({"seats": n, "rect_local": [0, round(b, 2), zd_a, round(b + wd, 2)], **_score_room(r)})
                b += 0.25
    out["enumerations"]["south_dining_rooms"] = {"count": len(dine), "ranked_by": "winter sun high, evening sun low, eyes low",
        "best_winter": sorted(dine, key=lambda d: -d["winter_h_of_5"])[:3], "least_overlooked": sorted(dine, key=lambda d: d["eyes_seated"])[:3],
        "finding": "the west half (b < 4.5) has the winter sun (up to 4 h of 5) and the sister-side exposure; the east half has the June sun and the east-neighbour exposure"}
    # --- fire-pit positions ------------------------------------------------------------------------------
    pits = []
    for ia in range(int(2.0 / 0.25) + 1):
        ap = 2.0 + ia * 0.25
        b = 1.0
        while b <= B - 1.5:
            ok_struct = 2.0 + 0.45 <= ap <= A - 2.0 - 0.45 and (B - b) >= 2.45
            r = S.rect_to_model([ap - 1.5, b - 1.5, ap + 1.5, b + 1.5])
            pits.append({"center_local": [round(ap, 2), round(b, 2)], "two_m_to_house_rear_east_fence": ok_struct, **_score_room(r)})
            b += 0.25
    ok = [p for p in pits if p["two_m_to_house_rear_east_fence"]]
    out["enumerations"]["south_fire_pit_positions"] = {"count": len(pits), "meeting_2m_clearance_to_house_rear_and_east_fence": len(ok),
        "clearance_band_a_m": [2.45, round(A - 2.45, 2)], "best_winter": sorted(ok, key=lambda d: -d["winter_h_of_5"])[:3],
        "wind": "75 % of summer-evening wind comes from the client east (5.6 m/s, station level): positions farther from the east fence are more sheltered by it; no site wind data (LDS gap W1)"}
    # --- quiet-seat cells: least overlooked 1.4 m squares --------------------------------------------------
    quiet = {}
    for name, zr in (("south", S.ZONES["south"]), ("north", [N_X0, N_Y0, N_X1, N_Y1]), ("east", S.ZONES["east"])):
        cells = []
        x = zr[0]
        while x + 1.4 <= zr[2] + 1e-9:
            y = zr[1]
            while y + 1.4 <= zr[3] + 1e-9:
                r = [x, y, x + 1.4, y + 1.4]
                cells.append({"rect": [round(v, 2) for v in r], "eyes_seated": round(S.eyes_total(r, "seated"), 1), "eyes_with_cover": round(S.eyes_total(r, "seated", cover_rects=[r]), 1)})
                y += 0.25
            x += 0.25
        quiet[name] = {"count": len(cells), "least_overlooked": sorted(cells, key=lambda d: d["eyes_seated"])[:3], "with_cover": sorted(cells, key=lambda d: d["eyes_with_cover"])[:3]}
    out["enumerations"]["quiet_seat_squares_1_4m"] = quiet
    # --- pond locations: both client options ---------------------------------------------------------------
    ponds = {"north_court": [], "east_yard": []}
    for l in (1.8, 2.6, 3.4):
        for w in (1.0, 1.2):
            x = N_X0 + 0.5
            while x + w <= N_OPEN_X1 + 1e-9:
                y = N_Y0 + 0.5
                while y + l <= N_Y1 - 0.5 + 1e-9:
                    r = [x, y, x + w, y + l]
                    ponds["north_court"].append({"rect": [round(v, 2) for v in r], "area_m2": round(w * l, 2), **_score_room(r)})
                    y += 0.25
                x += 0.25
    for l in (2.0, 3.0, 4.0):
        for w in (1.0, 1.2):
            x = E_X0 + 1.0
            while x + l <= E_X1 - 1.0 + 1e-9:
                y0 = E_Y0 + 1.5
                if y0 + w <= E_Y1 - 0.2:
                    r = [x, y0, x + l, y0 + w]
                    ponds["east_yard"].append({"rect": [round(v, 2) for v in r], "area_m2": round(w * l, 2), **_score_room(r)})
                x += 0.25
    out["enumerations"]["pond_locations"] = {
        k: {"count": len(v), "mean_rooms_seeing": round(sum(d["rooms_seeing"] for d in v) / len(v), 2), "mean_june_sun_h": round(sum(d["june_h"] for d in v) / len(v), 2),
            "mean_winter_sun_h": round(sum(d["winter_h_of_5"] for d in v) / len(v), 2), "mean_eyes_seated": round(sum(d["eyes_seated"] for d in v) / len(v), 1),
            "best_view": sorted(v, key=lambda d: -d["rooms_seeing"])[:3]} for k, v in ponds.items()}
    out["enumerations"]["pond_locations"]["note"] = ("LDS gap S8: there is NO door from the dirty kitchen to the east yard (a 2.59 m full-height window only), so a pond 'in front of the "
                                                    "dirty kitchen' is view-only from the kitchen unless the client adds a door; the dining and living doors do open onto the east yard.")
    # --- herb / fruit sun -----------------------------------------------------------------------------------------
    out["enumerations"]["herb_sun_6h"] = {"south_strip": "east fence strip b >= 8.55 m, about 0.75 m x 4.5 m, mean 6.0 h on 21 June (LDS)", "east_yard": "only 0.5 m2 reaches 6.0 h (x 21.4-22.4, y -21.3..-20.8)"}
    # --- focal points -------------------------------------------------------------------------------------------------
    v = json.load(open(S.SITE / "views.json"))["focal_point_candidates"]
    out["enumerations"]["focal_points_from_rooms"] = {k: x[:3] for k, x in v.items()}
    return out
