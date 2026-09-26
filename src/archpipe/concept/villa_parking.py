"""Round 7 options (client 2026-09-26): the S1 U-stair or the S4 straight stair, secured parking on a raised deck in
the east yard with rooms underneath, and more of the east yard used like option 5.

Parking geometry (street datum, m):
  - the ramp starts at the street gate (+0.00) and rises at 10 % (Metric Handbook p. 38-12, card mh-garage-ramp-max)
    to the deck at +0.85;
  - the deck soffit is at +0.50 (0.35 build-up + slab, ASSUMED): 2.30 m clear over the basement floor (-1.80), the
    basement's own clear height under its beams ("on the beam level", client) and the Metric Handbook minimum;
  - under the ramp the clear height rises from 1.45 m at the gate to 2.30 m at the deck: stores where it is under
    2.0 m, the laundry between 2.0 and 2.3 m ("working height", client), full rooms under the deck;
  - two cars tightly (2 x 4.9 m, Fig. 38.26) or one car comfortably (4.9 + 1.0 m).
The ramp and deck cover the basement's east facade from the street to the deck end, so the plan zones by light:
street-end flex / TV lounge (street window), the stair, a TV / media zone in the darker middle (the villa_01
home-cinema wish), and kitchen, dining and garden living at the rear where the east and rear windows remain.
"""
from __future__ import annotations

from . import villa as V
from . import villa_options as VO
from .villa import _layout, _room

YP, YE, YC, YK, X0, XR = V.YP, V.YE, V.YC, V.YK, V.X0, V.XR
SX0, SX1 = V.SX0, V.SX1
FE, FN = V.FENCE_E, V.FENCE_N
B_FFL = -1.80
DECK_TOP, BUILDUP = 0.85, 0.35
SOFFIT = round(DECK_TOP - BUILDUP, 2)                   # +0.50
GRADIENT = 0.10
RAMP_X0 = FN
RAMP_X1 = round(RAMP_X0 + DECK_TOP / GRADIENT, 3)      # 8.377
CARS = {2: 9.8, 1: 5.9}


def clear_at(x):
    """Clear height (m) over the basement floor under the ramp / deck at x."""
    top = DECK_TOP * min(1.0, max(0.0, (x - RAMP_X0) / (RAMP_X1 - RAMP_X0)))
    return round(top - BUILDUP - B_FFL, 3)


X_LOW = round(RAMP_X0 + (2.0 + B_FFL + BUILDUP) / DECK_TOP * (RAMP_X1 - RAMP_X0), 3)   # clear = 2.0 m (5.377)
DOOR_H = 2.10            # ASSUMED standard door leaf height; the Revit types are sized to it (build_villa_option)
HEAD_ZONE = 0.10         # frame + lintel above the leaf, ASSUMED
WORK_H = 2.0             # client: under 2.0 m clear is storage; a room door under the ramp may drop to this leaf
LOW_DOOR_MIN = 1.20      # a store under the low end of the ramp gets a cupboard-height door, not a room door


def door_fit(lo, hi, width, occupancy):
    """A door on a wall under the ramp between x lo..hi: slide it to the high (deck) end and size its leaf to the
    clear height less the frame. Returns (x_centre, leaf_height, clear_at_low_jamb, kind): 'full' (2.10 leaf),
    'reduced' (2.0-2.1 leaf, a room door where the ramp limits it), 'low' (a store's cupboard door, >= 1.2) or
    'none' (no door fits: the check fails)."""
    x0 = max(lo + 0.1, hi - 0.1 - width)
    xc = round(x0 + width / 2, 3)
    clear = clear_at(x0)
    leaf = min(DOOR_H, round(int((clear - HEAD_ZONE + 1e-9) * 100) / 100.0, 2))
    if leaf >= DOOR_H - 1e-9:
        return xc, DOOR_H, clear, "full"
    if leaf >= WORK_H - 1e-9:
        return xc, leaf, clear, "reduced"
    if occupancy == "store" and leaf >= LOW_DOOR_MIN:
        return xc, leaf, clear, "low"
    return xc, leaf, clear, "none"


def _back(cars, spine_entry=None):
    """Media zone, kitchen, dining, garden living (+ rear store). With two cars the deck covers the facade to x 18.2,
    so the kitchen and dining become one open room beside the garden living (its only daylight). spine_entry:
    (x0, x1) of an entrance hall in the kitchen spine (straight-stair options: the basement door moves to the second
    core lobby)."""
    k1 = 18.597 if cars == 2 else 15.745 if spine_entry else 16.0
    rooms = [_room("living", "B", (18.597, YP, XR, YE), "living", "garden living"),
             _room("store-rear", "B", V.REAR_SHARE, "store", "store")]
    links = [("living", "store-rear"), ("media", "kitchen"), ("kitchen", "living" if cars == 2 else "dining")]
    kname = "open kitchen + dining" if cars == 2 else "open kitchen"
    if cars == 1:
        rooms.append(_room("dining", "B", (k1, YP, 18.597, YE), "dining", "dining"))
        links.append(("dining", "living"))
    if spine_entry:
        e0, e1 = spine_entry
        rooms += [_room("kitchen", "B", (12.0, YK, k1, YE), "kitchen", kname),
                  _room("kitchen-island", "B", (12.0, YP, e0, YK), "kitchen", "open kitchen (island)"),
                  _room("entry-b", "B", (e0, YP, e1, YK), "entrance", "entrance (second core lobby)")]
        links += [("kitchen", "kitchen-island"), ("kitchen-island", "entry-b"), ("entry-b", "kitchen"),
                  ("hall-b", "kitchen-island")]
        if cars == 2:
            rooms.append(_room("dining-spine", "B", (e1, YP, k1, YK), "kitchen", "kitchen + dining (spine)"))
            links += [("entry-b", "dining-spine"), ("dining-spine", "kitchen"), ("dining-spine", "living")]
        else:
            links.append(("entry-b", "dining"))
    else:
        rooms.append(_room("kitchen", "B", (12.0, YP, k1, YE), "kitchen", kname))
    return rooms, links


def _under(cars, first_x):
    """Rooms under the ramp and deck (east yard, to the fence), from the street gate to the deck end."""
    deck_end = round(RAMP_X1 + CARS[cars], 3)
    rooms = [_room("store-ramp", "B", (FN, YE, X_LOW, FE), "store",
                   "store under the ramp (1.45-2.0 m clear)", ext=True),
             _room("laundry", "B", (X_LOW, YE, first_x, FE), "utility", "laundry (2.0-2.3 m clear, under the ramp)",
                   ext=True),
             _room("guest-wc", "B", (first_x, YE, 11.2, FE), "wc", "guest WC (under the deck)", ext=True),
             _room("dirty-kitchen", "B", (11.2, YE, min(deck_end, 15.0), FE), "utility",
                   "dirty kitchen (under the deck, door from the kitchen)", ext=True)]
    links = [("lounge", "store-ramp"), ("lounge", "laundry"), ("media", "guest-wc"), ("kitchen", "dirty-kitchen")]
    if deck_end > 15.0 + 1e-6:
        rooms.append(_room("store-deck", "B", (15.0, YE, deck_end, FE), "store", "store / plant (under the deck)",
                           ext=True))
        links.append(("dirty-kitchen", "store-deck"))
    return rooms, links, deck_end


def option(stair, cars):
    oid = {("u", 1): "P1", ("u", 2): "P2", ("straight", 1): "P3", ("straight", 2): "P4"}[(stair, cars)]
    car_txt = "one car" if cars == 1 else "two cars in tandem"
    if stair == "u":
        gf, gl, ge = V._gf()
        b = [_room("hall-b", "B", (X0, YP, SX1, YC), "entrance", "entrance hall"),
             _room("lounge", "B", (X0, YC, SX0, YE), "living", "flex / TV lounge (sliding doors)"),
             _room("stair-b", "B", V.STAIR, "stair", "stair (U, to the GF)", ends=[["h", YC, SX0, SX0 + 0.9]]),
             _room("pantry", "B", V.FRONT_SHARE, "store", "pantry / store"),
             _room("media", "B", (SX1, YP, 12.0, YE), "living", "TV / media (cinema; borrowed light)")]
        bl = [("hall-b", "stair-b"), ("hall-b", "lounge"), ("hall-b", "pantry"), ("hall-b", "media")]
        back, backl = _back(cars)
        under, underl, deck_end = _under(cars, SX1)
        entries = ge + [("hall-b", "B", "core-lobby-b")]
        stair_key = "u"
    else:
        base = VO.s4()
        gf = [r for r in base["rooms"].values() if r["level"] == "GF"]
        gl = [l for l in base["links"] if base["rooms"][l[0]]["level"] == "GF"]
        ge = [e for e in base["entries"] if e[1] == "GF"]
        ys = round(YP + 1.2, 3)
        b = [_room("laundry-landing", "B", (X0, YP, 4.877, ys), "utility", "utility (under the top landing)"),
             _room("stair-b", "B", (4.877, YP, 9.357, ys), "stair", "stair (straight, to the GF)",
                   ends=[["v", 9.357, YP + 0.25, ys]]),
             _room("pantry", "B", V.FRONT_SHARE, "store", "pantry / store"),
             _room("lounge", "B", (X0, ys, 9.357, YE), "living", "flex / TV lounge (sliding doors)"),
             _room("hall-b", "B", (9.357, YP, 12.0, YK), "hall", "hall at the stair foot"),
             _room("media", "B", (9.357, YK, 12.0, YE), "living", "TV / media (cinema; borrowed light)")]
        bl = [("hall-b", "stair-b"), ("hall-b", "media"), ("media", "lounge"), ("lounge", "laundry-landing"),
              ("laundry-landing", "pantry")]
        back, backl = _back(cars, spine_entry=(14.134, 15.745))
        under, underl, deck_end = _under(cars, 9.357)
        under = [dict(r, id="laundry-ramp") if r["id"] == "laundry" else r for r in under]
        underl = [tuple("laundry-ramp" if n == "laundry" else n for n in l) for l in underl]
        entries = ge + [("entry-b", "B", "core-lobby-b2")]
        stair_key = "party-fixed"
    title = ("Option %s: %s stair, parking for %s on a raised deck, rooms underneath"
             % (oid, "U" if stair == "u" else "straight", car_txt))
    summary = ("Street gate, 10 %% ramp to a deck at +0.85, %s; rooms under the ramp and deck by working height "
               "(stores, laundry, guest WC, dirty kitchen off the kitchen); basement zoned by light: flex / TV lounge "
               "at the street end opening onto the sunken north patio (loggia under the GF terrace + open court, "
               "closed on the east by the kept 1.40 m yard wall), stair, TV / media in the middle, kitchen, dining and garden living at the rear."
               % car_txt)
    lay = _layout(oid, title, gf + b + back + under, gl + bl + backl + underl, entries, summary)
    lay.update(stair=stair_key, terrace=list(V.TERRACE),
               extension=[list(r["rect"]) for r in under],
               parking2={"cars": cars, "ramp": [RAMP_X0, YE, RAMP_X1, FE], "deck": [RAMP_X1, YE, deck_end, FE],
                         "deck_top": DECK_TOP, "soffit": SOFFIT, "gradient": GRADIENT},
               # the sunken front (north) yard: the lounge's patio. Half is covered by the GF street terrace (a
               # loggia), half open to the sky; the kept NE yard wall and the ramp above close its east side.
               north_patio={"rect": [FN, YP, X0, round(V.m(V.E.YARD_WALL[1]), 3)],
                            "covered": [V.XS, YP, X0, round(V.m(V.E.YARD_WALL[1]), 3)],
                            "name": "sunken patio off the lounge (covered loggia under the GF terrace + open court)"})
    return lay


def options():
    return [option("u", 1), option("u", 2), option("straight", 1), option("straight", 2)]
