"""Round 7 options (client 2026-09-26), revised after the client review the same day.

The S1 U-stair (now turned lengthwise along the party wall, client: the U across the bar choked the basement) or
the S4 straight stair; secured parking on a deck in the east yard with rooms underneath; more of the east yard used
like option 5.

Parking geometry (street datum, m), revised by the client ("make the ramp reach the ground floor level at the door,
ramp climb faster, shift the door back ... wider sliding door"):
  - the ramp starts at the street gate (+0.00), eases in over 1.0 m at 10 %, climbs at 20 % and eases out over 1.0 m
    at 10 %, reaching the GF level (+1.20) at x 6.877, just before the east-face column at x 7.377;
  - 20 % is the published maximum for a private basement-garage access slope (Neufert, Architects' Data, 2nd
    English ed. 1980, Habitat p. 101 Fig. 4, card neufert-private-garage-slope-max; "where unavoidable"). The
    Metric Handbook limits garage ramps to 10 % (15 % in car parks with vertical transition curves, card
    mh-garage-ramp-max): exceeded by client choice, recorded as a waiver. Transition lengths (1.0 m at half the
    gradient) are ASSUMED, for the civil designer to set;
  - the deck is level with the GF (+1.20): the first GF room opens onto it through a 1.80 m bypass sliding door
    between the east-face columns (1.85 m clear), so with no car parked the deck is a GF-level yard;
  - deck soffit +0.85 (0.35 build-up + slab, ASSUMED): 2.65 m clear over the basement floor (-1.80);
  - under the ramp the clear height rises from 1.45 m at the gate: stores under 2.0 m, rooms above;
  - two cars tightly (2 x 4.9 m, Fig. 38.26) or one car comfortably (4.9 + 1.0 m), from the ramp top.
"""
from __future__ import annotations

import math

from . import stairs as S
from . import villa as V
from . import villa_options as VO
from .villa import _layout, _room

YP, YE, YC, YK, X0, XR = V.YP, V.YE, V.YC, V.YK, V.X0, V.XR
SX0, SX1 = V.SX0, V.SX1
FE, FN = V.FENCE_E, V.FENCE_N
B_FFL = -1.80
DECK_TOP, BUILDUP = 1.20, 0.35                          # deck level with the GF FFL (street +1.20)
SOFFIT = round(DECK_TOP - BUILDUP, 2)                   # +0.85
GRADIENT = 0.20                                         # main slope (Neufert private-garage maximum)
TRANSITION, TRANSITION_G = 1.0, 0.10                    # each end, ASSUMED (half the gradient)
RAMP_X0 = FN
RAMP_X1 = round(RAMP_X0 + 2 * TRANSITION + (DECK_TOP - 2 * TRANSITION * TRANSITION_G) / GRADIENT, 3)   # 6.877
CARS = {2: 9.8, 1: 5.9}
EXT_MIN_END = 14.5         # the rooms under the deck run at least this far (beyond a one-car deck: own roof, like S5)
STUDY_DOOR = (7.377, 9.227)                             # between the east-face column faces: 1.85 m clear
STUDY_DOOR_W = 1.80


def breakpoints():
    """x where the ramp's gradient changes (gate, end of the lower transition, start of the upper, ramp top)."""
    return [RAMP_X0, round(RAMP_X0 + TRANSITION, 3), round(RAMP_X1 - TRANSITION, 3), RAMP_X1]


def top_at(x):
    """Ramp / deck surface (street datum, m) at x."""
    x0, x1, x2, x3 = breakpoints()
    if x <= x0:
        return 0.0
    if x <= x1:
        return (x - x0) * TRANSITION_G
    z1 = TRANSITION * TRANSITION_G
    if x <= x2:
        return z1 + (x - x1) * GRADIENT
    if x <= x3:
        return DECK_TOP - (x3 - x) * TRANSITION_G
    return DECK_TOP


def clear_at(x):
    """Clear height (m) over the basement floor under the ramp / deck at x."""
    return round(top_at(x) - BUILDUP - B_FFL, 3)


def x_at_clear(c):
    """The first x where the clear height under the ramp reaches c (m)."""
    lo, hi = RAMP_X0, RAMP_X1
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if clear_at(mid) < c else (lo, mid)
    x = math.ceil(hi * 1000) / 1000                     # up to the mm, so the clear height there is >= c
    while clear_at(x) < c - 1e-9:
        x = round(x + 0.001, 3)
    return x


def soffit_points(a, b):
    """(x, clear height) along a..b at a, the gradient breakpoints inside and b: the soffit is straight between."""
    xs = [a] + [x for x in breakpoints() if a + 1e-6 < x < b - 1e-6] + [b]
    return [(round(x, 3), clear_at(x)) for x in xs]


def ramp_profile():
    """The ramp's top surface (x, street z) from the gate to the ramp top."""
    return [(x, round(top_at(x), 3)) for x in breakpoints()]


X_LOW = x_at_clear(2.0)                                 # 3.127: stores before, rooms after
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
    return (xc,) + leaf_for(clear, occupancy)


def leaf_for(clear, occupancy):
    """(leaf height, clear, kind) for a door under a soffit `clear` m above the floor (see door_fit)."""
    leaf = min(DOOR_H, round(int((clear - HEAD_ZONE + 1e-9) * 100) / 100.0, 2))
    if leaf >= DOOR_H - 1e-9:
        return DOOR_H, clear, "full"
    if leaf >= WORK_H - 1e-9:
        return leaf, clear, "reduced"
    if occupancy == "store" and leaf >= LOW_DOOR_MIN:
        return leaf, clear, "low"
    return leaf, clear, "none"


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


def _under(cars):
    """Rooms under the ramp and deck (east yard, to the fence), from the street gate. They run at least to x 14.5
    so the dirty kitchen opens off the kitchen; beyond a one-car deck they get their own roof, level with the deck
    (like option 5's blocks)."""
    deck_end = round(RAMP_X1 + CARS[cars], 3)
    ext_end = max(deck_end, EXT_MIN_END)
    rooms = [_room("store-ramp", "B", (FN, YE, X_LOW, FE), "store", "store under the ramp (1.45-2.0 m clear)",
                   ext=True),
             _room("laundry", "B", (X_LOW, YE, 7.2, FE), "utility", "laundry (under the ramp)", ext=True),
             _room("guest-wc", "B", (7.2, YE, SX1, FE), "wc", "guest WC (under the ramp top)", ext=True),
             _room("store-mid", "B", (SX1, YE, 11.2, FE), "store", "store (under the deck)", ext=True),
             _room("dirty-kitchen", "B", (11.2, YE, min(ext_end, 15.0), FE), "utility",
                   "dirty kitchen (door from the kitchen)", ext=True)]
    links = [("laundry", "store-ramp"), ("lounge", "laundry"), ("lounge", "guest-wc"), ("media", "store-mid"),
             ("kitchen", "dirty-kitchen")]
    if ext_end > 15.0 + 1e-6:
        rooms.append(_room("store-deck", "B", (15.0, YE, ext_end, FE), "store", "store / plant (under the deck)",
                           ext=True))
        links.append(("dirty-kitchen", "store-deck"))
    return rooms, links, deck_end, ext_end


def _gf_u_lengthwise():
    """GF for the U along the party wall: the stair void at the street end on the party side, the corridor from its
    arrival (x 6.887), and the study across the full street end (to x 9.227, the old U bay) with the deck door."""
    st = S.u_lengthwise_party()
    x_top, y_mid = st["top_x"] / 1000, st["landing"][3] / 1000          # 6.887, -26.571
    rooms, links, entries = V._gf()
    keep = [r for r in rooms if r["id"] not in ("study-game", "corridor", "stair-gf")]
    rooms = keep + [
        _room("stair-gf", "GF", (X0, YP, x_top, y_mid), "stair", "stair void (U, from the basement)",
              ends=[["v", x_top, st["flight2"][0] / 1000, st["flight2"][1] / 1000]]),
        _room("corridor", "GF", (x_top, YP, 19.527, YC), "corridor", "hall"),
        _room("landing-gf", "GF", (x_top, YC, SX1, y_mid), "corridor", "landing"),
        _room("study-game", "GF", (X0, y_mid, SX1, YE), "study",
              "study / game room (door to the terrace; sliding door to the deck)")]
    links = [l for l in links if "study-game" not in l and "stair-gf" not in l] + [
        ("corridor", "stair-gf"), ("corridor", "landing-gf"), ("landing-gf", "study-game")]
    return rooms, links, entries


def _gf_straight():
    """GF of option S4 with the study run on to x 9.227 (the deck door between the east-face columns) and the
    bedrooms shifted to the U layout's positions."""
    base = VO.s4()
    rooms = {r["id"]: dict(r) for r in base["rooms"].values() if r["level"] == "GF"}
    dx = 0.3                                          # the flight moved 0.3 m to the rear (stairs.party_flight_r8)
    for rid in ("landing-gf", "stair-gf", "corridor"):
        r = list(rooms[rid]["rect"])
        if rid == "landing-gf":
            r[2] = round(r[2] + dx, 3)
        elif rid == "stair-gf":
            r[0], r[2] = round(r[0] + dx, 3), round(r[2] + dx, 3)
            rooms[rid]["ends"] = [[e[0], round(e[1] + dx, 3)] + e[2:] for e in rooms[rid]["ends"]]
        else:
            r[0] = round(r[0] + dx, 3)
        rooms[rid]["rect"] = r
    x0, y0, _, y1 = rooms["study-game"]["rect"]
    rooms["study-game"]["rect"] = [x0, y0, SX1, y1]
    rooms["study-game"]["name"] = "study / game room (sliding door to the deck)"
    for rid, (a, b) in {"kids-a": (SX1, 12.827), "kids-b": (12.827, 16.427), "family-bath": (16.427, 18.427),
                        "parents-bed": (18.427, XR)}.items():
        r = rooms[rid]["rect"]
        rooms[rid]["rect"] = [a, r[1], b, r[3]]
    cx0 = rooms["corridor"]["rect"][0]                # the corner the study's run-on leaves beside the gallery
    rooms["gallery-end"] = _room("gallery-end", "GF", (cx0, YC, SX1, y0), "corridor", "gallery end")
    links = [l for l in base["links"] if base["rooms"][l[0]]["level"] == "GF"] + [("stair-gf", "gallery-end")]
    entries = [e for e in base["entries"] if e[1] == "GF"]
    return list(rooms.values()), links, entries


def option(stair, cars):
    oid = {("u", 1): "P1", ("u", 2): "P2", ("straight", 1): "P3", ("straight", 2): "P4"}[(stair, cars)]
    car_txt = "one car" if cars == 1 else "two cars in tandem"
    if stair == "u":
        st = S.u_lengthwise_party()
        xf, y_mid = st["foot_x"] / 1000, st["landing"][3] / 1000         # 7.167, -26.571
        yf2 = st["flight2"][1] / 1000 - 0.05                             # -27.571: under the upper flight only
        x_pass = 5.9                                                     # >= 2.0 m clear under the upper flight
        gf, gl, ge = _gf_u_lengthwise()
        b = [_room("hall-b", "B", (xf, YP, SX1, y_mid), "entrance", "entrance hall (stair foot)"),
             _room("pass-stair", "B", (x_pass, YP, xf, yf2), "corridor", "passage under the upper flight"),
             _room("store-stair", "B", (X0, YP, x_pass, yf2), "store", "store under the landing"),
             _room("stair-b", "B", (X0, yf2, xf, y_mid), "stair", "stair (U along the party wall, to the GF)",
                   ends=[["v", xf, st["flight1"][0] / 1000, st["flight1"][1] / 1000]]),
             _room("pantry", "B", V.FRONT_SHARE, "store", "pantry / store"),
             _room("lounge", "B", (X0, y_mid, SX1, YE), "living", "flex / TV lounge (open to the hall)"),
             _room("media", "B", (SX1, YP, 12.0, YE), "living", "TV / media (cinema; borrowed light)")]
        bl = [("hall-b", "stair-b"), ("hall-b", "pass-stair"), ("pass-stair", "pantry"),
              ("pass-stair", "store-stair"), ("hall-b", "lounge"), ("hall-b", "media"), ("lounge", "media")]
        back, backl = _back(cars)
        entries = ge + [("hall-b", "B", "core-lobby-b")]
        stair_key = "u-length"
    else:
        gf, gl, ge = _gf_straight()
        ys = round(YP + 1.2, 3)
        st = S.party_flight_r8()
        xt, xf = st["ends"]["top"][1] / 1000, st["ends"]["foot"][1] / 1000      # 5.177, 9.657
        b = [_room("laundry-landing", "B", (X0, YP, xt, ys), "utility", "utility (under the top landing)"),
             _room("stair-b", "B", (xt, YP, xf, ys), "stair", "stair (straight, to the GF)",
                   ends=[["v", xf, YP + 0.25, ys]]),
             _room("pantry", "B", V.FRONT_SHARE, "store", "pantry / store"),
             _room("lounge", "B", (X0, ys, xf, YE), "living", "flex / TV lounge"),
             _room("hall-b", "B", (xf, YP, 12.0, YK), "hall", "hall at the stair foot"),
             _room("media", "B", (xf, YK, 12.0, YE), "living", "TV / media (cinema; borrowed light)")]
        bl = [("hall-b", "stair-b"), ("hall-b", "media"), ("media", "lounge"), ("lounge", "laundry-landing"),
              ("laundry-landing", "pantry")]
        back, backl = _back(cars, spine_entry=(14.134, 15.745))
        entries = ge + [("entry-b", "B", "core-lobby-b2")]
        stair_key = "party-r8"
    under, underl, deck_end, ext_end = _under(cars)
    if stair != "u":                                  # the straight option already has a utility under its landing
        under = [dict(r, id="laundry-ramp") if r["id"] == "laundry" else r for r in under]
        underl = [tuple("laundry-ramp" if n == "laundry" else n for n in l) for l in underl]
    title = ("Option %s: %s stair, parking for %s on a GF-level deck, rooms underneath"
             % (oid, "U (along the party wall)" if stair == "u" else "straight", car_txt))
    summary = ("Street gate, ramp (20 %% with 10 %% ends) up to a deck level with the GF (+1.20), %s; the study "
               "opens onto it through a 1.80 m sliding door, so with no car it is a GF-level yard. Rooms under the "
               "ramp and deck by clear height (stores, laundry, guest WC, dirty kitchen off the kitchen). Basement: "
               "flex / TV lounge at the street end onto the sunken north patio, the stair, TV / media in the middle, "
               "kitchen, dining and garden living at the rear." % car_txt)
    lay = _layout(oid, title, gf + b + back + under, gl + bl + backl + underl, entries, summary)
    lay.update(stair=stair_key, terrace=list(V.TERRACE),
               extension=[list(r["rect"]) for r in under],
               parking2={"cars": cars, "ramp": [RAMP_X0, YE, RAMP_X1, FE], "deck": [RAMP_X1, YE, deck_end, FE],
                         "deck_top": DECK_TOP, "soffit": SOFFIT, "gradient": GRADIENT,
                         "transition": [TRANSITION, TRANSITION_G], "profile": ramp_profile(),
                         "roof_beyond_deck": [deck_end, YE, ext_end, FE] if ext_end > deck_end + 1e-6 else None},
               deck_door={"room": "study-game", "x0": STUDY_DOOR[0], "x1": STUDY_DOOR[1], "width": STUDY_DOOR_W,
                          "sliding": True},
               # the sunken front (north) yard: the lounge's patio. Half is covered by the GF street terrace (a
               # loggia), half open to the sky; the kept NE yard wall and the ramp above close its east side.
               north_patio={"rect": [FN, YP, X0, round(V.m(V.E.YARD_WALL[1]), 3)],
                            "covered": [V.XS, YP, X0, round(V.m(V.E.YARD_WALL[1]), 3)],
                            "name": "sunken patio off the lounge (covered loggia under the GF terrace + open court)"})
    return lay


def options():
    return [option("u", 1), option("u", 2), option("straight", 1), option("straight", 2)]
