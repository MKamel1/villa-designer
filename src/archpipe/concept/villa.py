"""Concepts for the real villa (Sheikh Zayed): the fixed envelope, three concepts, and a villa-specific critic.

The envelope is not ours to invent: an 18.98 x 5.08 m bar on two storeys (basement -1.80, GF +1.20) between the
shared core (party wall, no daylight) and the east yard, with the apartment on top and the columns and perimeter
beams fixed (src/archpipe/villa_env.py, docs/villa/environment-model.md). The parti is forced by that: a spine along
the blind party wall for circulation and services, habitable rooms on the east facade band, full-depth rooms at the
street and rear ends. Round 2 (client): the private stair may go anywhere; the straight flight along the blind party\nwall (foot at the street end, top at the GF core door) beats the dog-leg in the 2.2 m facade bay (stair study).

The three concepts differ on the real axes (advisor 2026-09-25): which storey holds the living, whether the basement
extends into the east yard, and what the street-side strip becomes. The critic cites the real project
(knowledge/projects/villa-omar.json) and sourced minimums (catalogue.MIN_AREA_M2 / ROOM_MIN_WIDTH); nothing from the
fictional pilot. Coordinates: metres, Revit project axes (x along the bar from the street, y toward plot-east).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .. import catalogue as cat
from .. import villa_env as E
from .. import vocabulary as vocab

ROOT = Path(__file__).resolve().parents[3]
m = lambda v: round(v / 1000.0, 3)                 # noqa: E731  mm -> m

# ---- envelope (from villa_env, in metres) -----------------------------------------------------------------------
XS, X0, XR = m(E.FRONT[0]), m(E.BAR[0]), m(E.BAR[2])          # strip front face, bar street face, rear face
YP, YE = m(E.BAR[1]), m(E.BAR[3])                             # party-wall outer face, east face
AX = m(E.AXIS_Y)
BUMP = tuple(m(v) for v in E.BUMP)
FRONT_SHARE = (X0, AX, m(E.CORE_B_OURS_FRONT[1]), YP)
REAR_SHARE = (m(E.CORE_B_OURS_REAR[0]), AX, XR, YP)
SHAFT_X = (m(E.SHAFT[0]), m(E.SHAFT[2]))
FENCE_E = round(YE + E.OFFSET_E / 1000.0, 3)                  # fence inner face beyond the east yard
GRID_X = [3.797, 7.197, 9.397, 11.367, 15.157, 18.622, 22.417]   # column centres on the east face (CAD)
EXT_WALL, INT_WALL = 0.20, 0.10                               # generator settings for net areas (CAD walls 0.15-0.18)
DOOR_EDGE = 1.0                                               # m of shared wall a door needs (0.8 leaf + frame)
LEVELS = {"B": -1.80, "GF": 1.20}                              # FFL relative to the street (brief)

# where the villa can be entered (segments on the envelope): the core doors, and the entrance-steps landing
ENTRY_SEGMENTS = {
    "GF": {"core-entrance": ("h", YP, X0, m(8506)), "core-lobby": ("h", YP, m(14134), m(15928)),
           "steps-landing": ("h", YP, XS, X0)},
    "B": {"core-lobby-b": ("h", YP, m(6940), m(8506)), "core-lobby-b2": ("h", YP, m(14134), m(15745)),
          "core-lobby-b-cross": ("v", m(6940), AX, YP)},
}


def envelope(level, extension=None):
    """Rectangles whose union is a storey's usable outline."""
    if level == "GF":
        rects = [(X0, YP, XR, YE), BUMP, (XS, YP, X0, YE)]
    else:
        rects = [(X0, YP, XR, YE), FRONT_SHARE, REAR_SHARE]
        if extension:
            rects.append(extension)
    return rects


def window_faces(level, extension=None):
    """Envelope segments where a window may go: street, east and rear faces. The party wall faces the core
    (blind), the axis line faces the sister, the bathroom projection's sides face the core and a column."""
    if level == "GF":
        faces = [("v", XS, YP, YE), ("h", YE, XS, XR), ("v", XR, YP, YE)]
    else:
        faces = [("v", X0, AX, YE), ("v", XR, AX, YE)]
        east = [(X0, XR)]
        if extension:
            x0, _, x1, y1 = extension
            east = [(a, b) for a, b in ((X0, max(X0, x0)), (min(XR, x1), XR)) if b - a > 1e-6]
            faces.append(("v", x1, YE, y1))                     # the extension's end facing the yard
            if x0 < X0:
                faces.append(("h", YE, x0, X0))                 # its side facing the front yard
            else:
                faces.append(("v", x0, YE, y1))
        faces += [("h", YE, a, b) for a, b in east]
    return faces


SHAFT_FACE = ("h", YP, SHAFT_X[0], SHAFT_X[1])               # vent only (sanitary / utility), both storeys


# ---- geometry helpers -------------------------------------------------------------------------------------------
def edges(rect):
    x0, y0, x1, y1 = rect
    return [("h", y0, x0, x1), ("h", y1, x0, x1), ("v", x0, y0, y1), ("v", x1, y0, y1)]


def overlap_len(a, b, tol=1e-6):
    """Collinear overlap of two axis-aligned segments (axis, coord, lo, hi)."""
    if a[0] != b[0] or abs(a[1] - b[1]) > tol:
        return 0.0
    return max(0.0, min(a[3], b[3]) - max(a[2], b[2]))


def shared_edge(r1, r2):
    return max((overlap_len(e1, e2) for e1 in edges(r1) for e2 in edges(r2)), default=0.0)


def on_faces(rect, faces):
    return sum(overlap_len(e, f) for e in edges(rect) for f in faces)


def covered(rect, rects, step=0.1):
    x0, y0, x1, y1 = rect
    nx, ny = max(2, int((x1 - x0) / step)), max(2, int((y1 - y0) / step))
    for i in range(nx):
        for j in range(ny):
            px, py = x0 + (i + 0.5) * (x1 - x0) / nx, y0 + (j + 0.5) * (y1 - y0) / ny
            if not any(a - 1e-6 <= px <= c + 1e-6 and b - 1e-6 <= py <= d + 1e-6 for a, b, c, d in rects):
                return False
    return True


def area(rect):
    return (rect[2] - rect[0]) * (rect[3] - rect[1])


def boundary_segments(rects):
    """Edges of the union's outline: pieces of rectangle edges with outside on one side."""
    out = []
    for r in rects:
        for e in edges(r):
            ax, c, lo, hi = e
            n = max(1, int((hi - lo) / 0.05))
            for i in range(n):
                a, b = lo + i * (hi - lo) / n, lo + (i + 1) * (hi - lo) / n
                mid = (a + b) / 2
                probes = [(mid, c + 0.01), (mid, c - 0.01)] if ax == "h" else [(c + 0.01, mid), (c - 0.01, mid)]
                inside = [any(x0 <= px <= x1 and y0 <= py <= y1 for x0, y0, x1, y1 in rects) for px, py in probes]
                if inside[0] != inside[1]:
                    out.append((ax, c, a, b))
    return out


def net_dims(rect, outline):
    """Net clear width and depth: inset by half a partition, or a whole external wall on the envelope outline."""
    x0, y0, x1, y1 = rect
    ins = []
    for e in edges(rect):
        on = sum(overlap_len(e, s) for s in outline) > 0.5 * (e[3] - e[2])
        ins.append(EXT_WALL if on else INT_WALL / 2)
    # edges() order: bottom(y0), top(y1), left(x0), right(x1)
    return (x1 - x0) - ins[2] - ins[3], (y1 - y0) - ins[0] - ins[1]


# ---- concepts -----------------------------------------------------------------------------------------------------
YC = round(YP + 1.3, 3)          # spine depth 1.3 m: 0.9 m clear hall after the party wall (AD M para 2.22a)
YK = round(YP + 2.0, 3)          # deeper service spine in the kitchen zone: 1.75 m clear for a galley or a WC
STAIR = (7.197, YC, 9.397, YE)   # "bay": dog-leg in the 2.2 m column bay, stacked on both storeys
# "spine": straight flight along the blind party wall at the street end, 3.6 m run (15 goings x 240, 16 risers x
# 187.5), foot at the street end in the basement, top beside the GF core door. At GF the void needs a 1.1 m gallery
# beside it so the hall can pass.
SPINE_X1 = 7.417                  # 3.60 m clear run from the street wall's inner face (X0 + 0.20)
YS1 = round(YP + 1.2, 3)          # flight zone (0.95 m clear after the party wall)
YS2 = round(YP + 2.3, 3)          # GF: flight void + passing gallery
# Alternative B: secured parking on a street-level deck in the east strip behind a new gate, a room under it
FENCE_N = round(X0 - E.OFFSET_N / 1000.0, 3)                   # street fence inner face
DECK_END = 9.70                                                # two cars in tandem: 9.82 m from the fence
DECK = (FENCE_N, YE, DECK_END, FENCE_E)
DECK_STAIR = (DECK_END, round(FENCE_E - 1.0, 3), round(DECK_END + 2.25, 3), FENCE_E)   # 10 risers x 180, 9 x 250
EXTRA_FFL = -2.75                 # room under the deck: 0.95 m below the basement FFL (see elevation_checks)


def _room(rid, level, rect, occ, name=None, **kw):
    return dict({"id": rid, "level": level, "rect": [round(v, 3) for v in rect], "occupancy": occ,
                 "name": name or rid.replace("-", " ")}, **kw)


def _suite():
    return [_room("parents-dressing", "GF", (18.597, YP, XR, YC), "dressing", "dressing", suite=True),
            _room("parents-ensuite", "GF", BUMP, "ensuite", "en-suite", suite=True)]


def _gf(stair):
    if stair == "bay":
        rooms = [_room("study-game", "GF", (XS, YC, 7.197, YE), "study", "study / game room"),
                 _room("store-gf", "GF", (XS, YP, X0, YC), "store", "store"),
                 _room("corridor", "GF", (X0, YP, 18.597, YC), "corridor", "hall"),
                 _room("stair-gf", "GF", STAIR, "stair", "stair to basement"),
                 _room("kids-a", "GF", (9.397, YC, 12.997, YE), "bedroom", "kids bedroom A"),
                 _room("kids-b", "GF", (12.997, YC, 16.597, YE), "bedroom", "kids bedroom B"),
                 _room("family-bath", "GF", (16.597, YC, 18.597, YE), "bathroom", "family bathroom"),
                 _room("parents-bed", "GF", (18.597, YC, XR, YE), "bedroom", "parents' bedroom", suite=True,
                       first=True)] + _suite()
        links = [("corridor", "stair-gf"), ("corridor", "study-game"), ("corridor", "store-gf"),
                 ("corridor", "kids-a"), ("corridor", "kids-b"), ("corridor", "family-bath"),
                 ("corridor", "parents-dressing"), ("parents-dressing", "parents-bed"),
                 ("parents-dressing", "parents-ensuite")]
    else:
        rooms = [_room("study-game", "GF", (XS, YS2, SPINE_X1, YE), "study", "study / game room"),
                 _room("store-gf", "GF", (XS, YP, X0, YS2), "store", "store"),
                 _room("stair-gf", "GF", (X0, YP, SPINE_X1, YS2), "stair", "stair void + gallery"),
                 _room("corridor", "GF", (SPINE_X1, YP, 18.597, YC), "corridor", "hall"),
                 _room("kids-a", "GF", (SPINE_X1, YC, 11.417, YE), "bedroom", "kids bedroom A"),
                 _room("kids-b", "GF", (11.417, YC, 15.617, YE), "bedroom", "kids bedroom B"),
                 _room("family-bath", "GF", (15.617, YC, 17.547, YE), "bathroom", "family bathroom"),
                 _room("parents-bed", "GF", (17.547, YC, XR, YE), "bedroom", "parents' bedroom", suite=True,
                       first=True)] + _suite()
        links = [("stair-gf", "corridor"), ("stair-gf", "study-game"), ("stair-gf", "store-gf"),
                 ("corridor", "kids-a"), ("corridor", "kids-b"), ("corridor", "family-bath"),
                 ("corridor", "parents-bed"), ("parents-bed", "parents-dressing"),
                 ("parents-dressing", "parents-ensuite")]
    return rooms, links, [("corridor", "GF", "core-entrance")]


def _b(stair, parking=False):
    common = [
        _room("dirty-kitchen", "B", (11.397, YP, 13.797, YK), "utility", "dirty kitchen"),
        _room("guest-wc", "B", (13.797, YP, 15.197, YK), "wc", "guest WC"),
        _room("dining", "B", (15.197, YP, 18.597, YE), "dining", "dining"),
        _room("living", "B", (18.597, YP, XR, YE), "living", "garden living"),
        _room("store-rear", "B", REAR_SHARE, "store", "store"),
    ]
    common_links = [("dirty-kitchen", "kitchen"), ("dining", "guest-wc"), ("kitchen", "dining"), ("dining", "living"),
                    ("living", "store-rear")]
    if stair == "bay":
        rooms = [_room("pantry", "B", FRONT_SHARE, "store", "pantry / store"),
                 _room("laundry", "B", (X0, YP, 7.197, -26.071), "utility", "laundry"),
                 _room("flex", "B", (X0, -26.071, 7.197, YE), "study", "flex room"),
                 _room("hall-b", "B", (7.197, YP, 9.397, YC), "entrance", "entrance hall"),
                 _room("stair-b", "B", STAIR, "stair", "stair to GF"),
                 _room("gallery", "B", (9.397, YP, 11.397, YK), "hall", "gallery"),
                 _room("kitchen", "B", (9.397, YK, 15.197, YE), "kitchen", "open kitchen")] + common
        links = [("hall-b", "stair-b"), ("hall-b", "laundry"), ("hall-b", "gallery"), ("gallery", "kitchen"),
                 ("gallery", "dirty-kitchen"), ("laundry", "pantry"), ("stair-b", "flex")] + common_links
    else:
        rooms = [_room("laundry", "B", FRONT_SHARE, "utility", "laundry"),
                 _room("stair-b", "B", (X0, YP, SPINE_X1, YS1), "stair", "stair to GF"),
                 _room("flex", "B", (X0, YS1, SPINE_X1, YE), "study", "flex room"),
                 _room("hall-b", "B", (SPINE_X1, YP, 9.397, YK), "entrance", "entrance hall"),
                 _room("pantry", "B", (9.397, YP, 11.397, YK), "store", "pantry"),
                 _room("kitchen", "B", (SPINE_X1, YK, 15.197, YE), "kitchen", "open kitchen")] + common
        links = [("hall-b", "stair-b"), ("stair-b", "flex"), ("stair-b", "laundry"), ("hall-b", "kitchen"),
                 ("kitchen", "pantry")] + common_links
    if parking:
        rooms.append(_room("extra-room", "B", DECK, "study", "extra room under the parking (FFL -2.75)",
                           ffl=EXTRA_FFL))
        links.append(("flex", "extra-room"))
    return rooms, links, [("hall-b", "B", "core-lobby-b")]


def concept_a(stair="spine"):
    g, gl, ge = _gf(stair)
    b, bl, be = _b(stair)
    cid = "A" if stair == "spine" else "A-bay"
    lay = _layout(cid, "Garden living below, bedrooms above" + ("" if stair == "spine" else " (stair in the facade bay)"),
                  g + b, gl + bl, ge + be,
                  "Living, dining and kitchen at yard level open to the garden, terrace and BBQ; bedrooms on the GF "
                  "above the fence line; the parents' suite at the rear on the existing wet stack; " +
                  ("a straight private stair along the blind party wall, foot at the street end, top at the GF "
                   "core door." if stair == "spine" else "a dog-leg private stair in the 2.2 m column bay."))
    lay["stair"] = stair
    return lay


def concept_b(stair="spine"):
    g, gl, ge = _gf(stair)
    b, bl, be = _b(stair, parking=True)
    lay = _layout("B", "A + secured parking behind the gate, extra room underneath", g + b, gl + bl, ge + be,
                  "As A, with a street-level parking deck for two cars in tandem in the east strip behind a new "
                  "gate, a stair from the deck down to the yard, and an extra room under the deck reached from the "
                  "flex room, its floor lowered to -2.75 for headroom.")
    lay["stair"] = stair
    lay["extension"] = list(DECK)
    lay["parking"] = {"deck": list(DECK), "deck_stair": list(DECK_STAIR), "deck_top": 0.0}
    return lay


def concept_c():
    """Kept for the record (round 1); the client chose A on 2026-09-25."""
    gf = [
        _room("store-gf", "GF", (XS, YP, X0, YC), "store", "store"),
        _room("living", "GF", (XS, YC, 7.197, YE), "living", "living"),
        _room("hall", "GF", (X0, YP, 9.397, YC), "entrance", "entrance hall"),
        _room("stair-gf", "GF", STAIR, "stair", "stair to basement"),
        _room("gallery", "GF", (9.397, YP, 11.397, YK), "hall", "gallery"),
        _room("kitchen", "GF", (9.397, YK, 15.197, YE), "kitchen", "open kitchen"),
        _room("dirty-kitchen", "GF", (11.397, YP, 13.797, YK), "utility", "dirty kitchen"),
        _room("guest-wc", "GF", (13.797, YP, 15.197, YK), "wc", "guest WC"),
        _room("dining", "GF", (15.197, YP, 18.597, YE), "dining", "dining"),
        _room("family", "GF", (18.597, YC, XR, YE), "living", "family room"),
        _room("back-hall", "GF", (18.597, YP, XR, YC), "hall", "back hall"),
        _room("laundry", "GF", BUMP, "utility", "laundry"),
    ]
    gl = [("hall", "store-gf"), ("hall", "living"), ("hall", "stair-gf"), ("hall", "gallery"), ("gallery", "kitchen"),
          ("gallery", "dirty-kitchen"), ("dirty-kitchen", "kitchen"), ("dining", "guest-wc"), ("kitchen", "dining"),
          ("dining", "back-hall"), ("back-hall", "family"), ("back-hall", "laundry")]
    b = [
        _room("family-bath", "B", (X0, AX, 5.8, YC), "bathroom", "family bathroom"),
        _room("linen", "B", (5.8, AX, m(E.CORE_B_OURS_FRONT[1]), YP), "store", "linen / store"),
        _room("corridor-b", "B", (5.8, YP, 18.597, YC), "corridor", "hall"),
        _room("kids-a", "B", (X0, YC, 7.197, YE), "bedroom", "kids bedroom A"),
        _room("stair-b", "B", STAIR, "stair", "stair to GF"),
        _room("kids-b", "B", (9.397, YC, 12.997, YE), "bedroom", "kids bedroom B"),
        _room("study-game", "B", (12.997, YC, 16.597, YE), "study", "study / game room"),
        _room("parents-bed", "B", (16.597, YC, XR, YE), "bedroom", "parents' bedroom", suite=True, first=True),
        _room("parents-dressing", "B", (18.597, YP, XR, YC), "dressing", "dressing", suite=True),
        _room("parents-ensuite", "B", REAR_SHARE, "ensuite", "en-suite", suite=True),
    ]
    bl = [("corridor-b", "family-bath"), ("corridor-b", "linen"), ("corridor-b", "kids-a"), ("corridor-b", "stair-b"),
          ("corridor-b", "kids-b"), ("corridor-b", "study-game"), ("corridor-b", "parents-bed"),
          ("parents-bed", "parents-dressing"), ("parents-dressing", "parents-ensuite")]
    lay = _layout("C", "Reverse: living on the GF, bedrooms at yard level", gf + b, gl + bl,
                  [("hall", "GF", "core-entrance"), ("corridor-b", "B", "core-lobby-b")],
                  "Living, kitchen and dining on the entrance storey above the fence line; bedrooms at yard level.")
    lay["stair"] = "bay"
    return lay


def _layout(cid, title, rooms, links, entries, summary):
    return {"id": cid, "title": title, "summary": summary, "levels": dict(LEVELS),
            "rooms": {r["id"]: r for r in rooms},
            "links": [list(l) for l in links], "entries": [list(e) for e in entries],
            "vertical": [["stair-b", "stair-gf"]]}


def concepts():
    """Round 2 (client 2026-09-25): A chosen with the flex room; the stair study (A vs A-bay); alternative B."""
    return [concept_a("spine"), concept_a("bay"), concept_b("spine")]


# ---- critic -----------------------------------------------------------------------------------------------------
PROJECT = "knowledge/projects/villa-omar.json"
BASIS = {
    "within_envelope": "Envelope from the client's CAD/Revit and the confirmed core (docs/villa/environment-model.md).",
    "no_overlap": "Rooms may not overlap.",
    "min_area": "catalogue.MIN_AREA_M2 (NDSS via Metric Handbook 7th ed. p. 22-4; IRC R304.1 via Mitton p. 143). "
                "Bathroom/WC M4(2) sizes are a PREFERENCE for this client (brief: ageing in place), so a shortfall "
                "is a warning.",
    "min_width": "catalogue.ROOM_MIN_WIDTH (NDSS via Metric Handbook 7th ed. p. 22-4).",
    "window": "SLL Code for Lighting minimum ADF cards (bedroom/living/kitchen): a room with no window cannot meet "
              "them. Windows only on the street, east and rear faces; the party wall faces the shared core.",
    "links_built": "Each intended door needs >= 1.0 m of shared wall (0.8 m leaf + frame; AD M Table 2.1 widths).",
    "entrances": "Entrances only where the core or the entrance steps meet our envelope (environment model).",
    "reachability": "Every room reachable from an entrance.",
    "suite_privacy": f"Client (brief, {PROJECT} fact 'privacy'): the parents' suite is reached without crossing "
                     "living, dining or kitchen, and no other room is reached only through it.",
    "wc_access": "UK AD G para 4.8 with M4(1) (card ukadg-dwelling-wc-entrance-storey): a WC on each entrance storey, "
                 "reached without entering a bedroom.",
    "wet_stack": "Advisory: GF wet rooms over basement wet/service rooms shorten drainage; the existing GF bathroom "
                 "(bump) sits under the apartment's bathroom (core), the only wet stack known above us.",
    "overlooking": "Advisory, no pass/fail threshold held: distance from east-facing windows to the 12 m "
                   "neighbour's facade (with windows on every storey) across the east yard.",
    "basement_sky": "Advisory: angle to the top of the 4.0 m fence (from basement level) seen from a basement window "
                    "centre at 1.6 m, per facade. For the daylight run, not a pass/fail.",
    "circulation": "Advisory: circulation share of net area.",
}


def _chk(name, status, **kw):
    return dict({"check": name, "status": status, "basis": BASIS[name]}, **kw)


def critique(lay):
    rooms = lay["rooms"]
    ext = lay.get("extension")
    out = []
    bad_env, overlaps = [], []
    outline = {lv: boundary_segments(envelope(lv, ext)) for lv in LEVELS}
    for rid, r in rooms.items():
        if not covered(r["rect"], envelope(r["level"], ext)):
            bad_env.append(rid)
    ids = list(rooms)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            ra, rb = rooms[a], rooms[b]
            if ra["level"] == rb["level"]:
                x0, y0 = max(ra["rect"][0], rb["rect"][0]), max(ra["rect"][1], rb["rect"][1])
                x1, y1 = min(ra["rect"][2], rb["rect"][2]), min(ra["rect"][3], rb["rect"][3])
                if x1 - x0 > 1e-3 and y1 - y0 > 1e-3:
                    overlaps.append([a, b])
    out.append(_chk("within_envelope", "fail" if bad_env else "pass", rooms=bad_env))
    out.append(_chk("no_overlap", "fail" if overlaps else "pass", pairs=overlaps))
    # sizes
    small, warn, narrow, sizes = [], [], [], {}
    for rid, r in rooms.items():
        w, d = net_dims(r["rect"], outline[r["level"]])
        sizes[rid] = {"net_w": round(w, 2), "net_d": round(d, 2), "net_m2": round(w * d, 1)}
        occ = r["occupancy"]
        key = "bedroom" if occ == "bedroom" else occ if occ in ("living", "dining", "study") else \
            "bathroom" if occ in ("bathroom", "ensuite") else "wc" if occ == "wc" else None
        if key and key in cat.MIN_AREA_M2:
            need = cat.MIN_AREA_M2[key][0]
            if w * d < need:
                (warn if key in ("bathroom", "wc") else small).append(
                    {"room": rid, "achieved_m2": round(w * d, 1), "required_m2": need})
        if occ == "bedroom":
            wk = "bedroom_first" if r.get("first") else "bedroom"
            need = cat.ROOM_MIN_WIDTH[wk][0] / 1000
            if min(w, d) < need:
                narrow.append({"room": rid, "achieved_m": round(min(w, d), 2), "required_m": need})
    out.append(_chk("min_area", "fail" if small else ("warning" if warn else "pass"), rooms=small, preference=warn))
    out.append(_chk("min_width", "fail" if narrow else "pass", rooms=narrow))
    # windows
    dark, win_len = [], {}
    for rid, r in rooms.items():
        faces = window_faces(r["level"], ext)
        L_ = on_faces(r["rect"], faces)
        win_len[rid] = round(L_, 2)
        if r["occupancy"] in vocab.HABITABLE and L_ < 1.0 and not r.get("rooflight"):
            dark.append(rid)
    out.append(_chk("window", "fail" if dark else "pass", rooms=dark))
    # doors and entrances
    unbuilt = [l for l in lay["links"] if rooms[l[0]]["level"] != rooms[l[1]]["level"]
               or shared_edge(rooms[l[0]]["rect"], rooms[l[1]]["rect"]) < DOOR_EDGE]
    out.append(_chk("links_built", "fail" if unbuilt else "pass", links=unbuilt))
    bad_entry = []
    for rid, lv, seg in lay["entries"]:
        s = ENTRY_SEGMENTS[lv][seg]
        if max(overlap_len(e, s) for e in edges(rooms[rid]["rect"])) < DOOR_EDGE:
            bad_entry.append([rid, seg])
    out.append(_chk("entrances", "fail" if bad_entry else "pass", entries=bad_entry))
    # graph
    graph = [tuple(l) for l in lay["links"] if l not in unbuilt] + [tuple(v) for v in lay["vertical"]]
    starts = [e[0] for e in lay["entries"] if [e[0], e[2]] not in bad_entry]

    def reach(blocked=lambda r: False):
        seen, todo = set(), list(starts)
        while todo:
            n = todo.pop()
            if n in seen:
                continue
            seen.add(n)
            if n not in starts and blocked(n):
                continue
            todo += [b if a == n else a for a, b in graph if n in (a, b)]
        return seen

    unreached = sorted(set(rooms) - reach())
    out.append(_chk("reachability", "fail" if unreached else "pass", rooms=unreached))
    public = {"living", "dining", "kitchen"}
    suite = [r for r, v in rooms.items() if v.get("suite")]
    via_public = [r for r in suite if r not in reach(lambda n: rooms[n]["occupancy"] in public)]
    through_suite = sorted(set(rooms) - set(suite) - reach(lambda n: n in suite))
    out.append(_chk("suite_privacy", "fail" if via_public or through_suite else "pass",
                    crossing_public=via_public, reached_only_through_suite=through_suite))
    no_wc = []
    for lv in sorted({e[1] for e in lay["entries"]}):
        wcs = [r for r, v in rooms.items() if v["level"] == lv and v["occupancy"] in vocab.SANITARY]
        ok = reach(lambda n: rooms[n]["occupancy"] in ("bedroom",) or rooms[n].get("suite"))
        if not any(w in ok and not rooms[w].get("suite") for w in wcs):
            no_wc.append(lv)
    out.append(_chk("wc_access", "fail" if no_wc else "pass", storeys=no_wc))
    # advisories
    wet = lambda v: v["occupancy"] in vocab.SANITARY or v["occupancy"] == "utility"   # noqa: E731
    stack = []
    for rid, r in rooms.items():
        if r["level"] == "GF" and wet(r):
            below = sum(_ov(r["rect"], v["rect"]) for v in rooms.values() if v["level"] == "B" and
                        (wet(v) or v["occupancy"] == "store"))
            stack.append({"room": rid, "over_wet_or_store": round(below / area(r["rect"]), 2),
                          "under_apartment_bath": _ov(r["rect"], BUMP) > 0.5 * area(r["rect"])})
    out.append(_chk("wet_stack", "advisory", rooms=stack))
    gap = round(FENCE_E - YE + E.FENCE_T / 1000 + E.OFFSET_E / 1000, 2)
    east = sorted(rid for rid, r in rooms.items() if r["occupancy"] in vocab.HABITABLE and
                  on_faces(r["rect"], [("h", YE, XS, XR)]) >= 1.0)
    out.append(_chk("overlooking", "advisory", distance_to_neighbour_facade_m=gap, east_facing_rooms=east,
                    note="The fence top is 1.00 m above the GF floor; the neighbour's upper storeys "
                         "look down over it."))
    sky = {}
    for name, dist in (("street", E.OFFSET_N / 1000), ("east", E.OFFSET_E / 1000), ("rear", E.OFFSET_S / 1000)):
        sky[name] = round(math.degrees(math.atan2(E.FENCE_H / 1000 - 1.6, dist)), 1)
    out.append(_chk("basement_sky", "advisory", fence_top_elevation_angle_deg=sky,
                    basement_habitable=sorted(r for r, v in rooms.items()
                                              if v["level"] == "B" and v["occupancy"] in vocab.HABITABLE)))
    net = {lv: sum(s["net_m2"] for r, s in sizes.items() if rooms[r]["level"] == lv) for lv in LEVELS}
    circ = {lv: sum(s["net_m2"] for r, s in sizes.items() if rooms[r]["level"] == lv and
                    rooms[r]["occupancy"] in vocab.CIRCULATION) for lv in LEVELS}
    out.append(_chk("circulation", "advisory", net_m2={k: round(v, 1) for k, v in net.items()},
                    circulation_m2={k: round(v, 1) for k, v in circ.items()},
                    share={k: round(circ[k] / net[k], 2) for k in LEVELS}))
    fails = [c["check"] for c in out if c["status"] == "fail"]
    warns = [c["check"] for c in out if c["status"] == "warning"]
    return {"id": lay["id"], "checks": out, "fails": fails, "warnings": warns, "sizes": sizes,
            "window_m": win_len}


def _ov(a, b):
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def write(lay, res, folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"concept-{lay['id']}.json").write_text(json.dumps({"layout": lay, "critique": res}, indent=1),
                                                      encoding="utf-8")


# ---- elevation / section checks -----------------------------------------------------------------------------------
STOREY = 3.0                 # floor-to-floor (REVIT columns 0-3000; client confirmed the apartment repeats it)
SLAB, BEAM = 0.20, 0.60      # REVIT slab type 200; perimeter beam depth ASSUMED (environment model)
FLOOR_BUILDUP = 0.10         # screed + finish, ASSUMED
DECK_BUILDUP, DECK_SLAB = 0.10, 0.25   # falls/waterproofing/finish and car-deck slab, ASSUMED (structural consultant)


def _card(cid):
    from .. import guidance
    c = guidance.library()["evidence"][cid]
    return c["verified_value"], f"{cid} ({c['locator']})"


def _row(item, achieved, required, card, ok, unit="m", note=""):
    return {"item": item, "achieved": achieved, "required": required, "unit": unit, "card": card,
            "status": "advisory" if required == "-" else "pass" if ok else "fail", "note": note}


def stair_geometry(stair):
    """Rise/going of the private stair between the basement (-1.80) and the GF (+1.20)."""
    risers = 16
    rise = STOREY * 1000 / risers
    if stair == "spine":
        going, flights = 240.0, [15]
        run = (SPINE_X1 - (X0 + EXT_WALL)) * 1000
        fits = flights[0] * going <= run + 1e-6
    else:
        going, flights = 250.0, [7, 7]                        # two flights of 8 risers around a half landing
        run = (YE - EXT_WALL - (YC + INT_WALL / 2)) * 1000     # the bay's clear depth across the bar
        fits = max(flights) * going + 1000 <= run + 1e-6       # a flight plus a half landing as deep as the width
    return {"risers": risers, "rise": round(rise, 1), "going": going, "flights": flights, "run_needed": sum(flights) * going
            if stair == "spine" else max(flights) * going + 1000, "run_available": round(run), "fits": fits,
            "pitch_deg": round(math.degrees(math.atan2(rise, going)), 1), "two_r_plus_g": round(2 * rise + going)}


def elevation_checks(lay):
    """Levels and heights checked against the held cards. Datum: street = 0.00 (brief)."""
    out = []
    ceil_min, ceil_card = _card("mh-dwelling-ceiling-min")
    for name, ffl in (("basement", LEVELS["B"]), ("ground floor", LEVELS["GF"])):
        under_slab = STOREY - SLAB - FLOOR_BUILDUP
        under_beam = STOREY - BEAM - FLOOR_BUILDUP
        out.append(_row(f"{name} (FFL {ffl:+.2f}) clear height under the slab", round(under_slab, 2), ceil_min,
                        ceil_card, under_slab >= ceil_min - 1e-9))
        out.append(_row(f"{name} clear height under the perimeter beams (window heads)", round(under_beam, 2), ceil_min,
                        ceil_card, under_beam >= ceil_min - 1e-9,
                        note="2.4 m is the book's preferable height; beam depth assumed 0.60"))
    g = stair_geometry(lay.get("stair", "spine"))
    rise_max, rc = _card("ukadk-private-stair-rise-max")
    going_min, gc = _card("ukadk-private-stair-going-min")
    pitch_max, pc = _card("ukadk-private-stair-pitch-max")
    lo, lc = _card("ukadk-2r-plus-g-min")
    hi, _ = _card("ukadk-2r-plus-g-max")
    head, hc = _card("ukadk-stair-headroom-min")
    out += [_row("private stair rise (16 risers over 3.00 m)", g["rise"], rise_max, rc, g["rise"] <= rise_max, "mm"),
            _row("private stair going", g["going"], going_min, gc, g["going"] >= going_min, "mm"),
            _row("private stair pitch", g["pitch_deg"], pitch_max, pc, g["pitch_deg"] <= pitch_max, "deg"),
            _row("private stair 2R+G", g["two_r_plus_g"], f"{lo}-{hi}", lc, lo <= g["two_r_plus_g"] <= hi, "mm"),
            _row("private stair run fits its zone", g["run_available"], g["run_needed"], "geometry", g["fits"], "mm")]
    if lay.get("stair") == "spine":
        soffit = STOREY - SLAB                                  # GF slab soffit above the basement floor
        covered = (soffit - head / 1000) / (g["rise"] / g["going"])
        out.append(_row("stair headroom: GF floor may overhang the foot of the flight by at most", round(covered, 2),
                        "headroom >= 2.00 over the pitch line", hc, covered > 0,
                        note=f"GF slab opening from x = {X0 + EXT_WALL + covered:.2f} to {SPINE_X1:.2f}; keep the flight "
                             "50 mm off the party wall where a perimeter beam may run"))
    if lay.get("parking"):
        drop = 0.0 - LEVELS["B"]
        soffit = 0.0 - DECK_BUILDUP - DECK_SLAB
        clear = soffit - EXTRA_FFL
        out.append(_row("room under the deck: clear height (deck +/-0.00, soffit -0.35, FFL -2.75)", round(clear, 2),
                        ceil_min, ceil_card, clear >= ceil_min - 1e-9, note="2.40 = the book's preferable height"))
        step = LEVELS["B"] - EXTRA_FFL
        n = math.ceil(round(step * 1000, 3) / rise_max)
        r = step * 1000 / n if n else 0.0
        out.append(_row(f"steps down from the basement to the room ({n} risers)", round(r, 1), rise_max, rc,
                        r <= rise_max, "mm"))
        g_drop, gd = _card("ukadk-guarding-drop-dwelling")
        g_ext, ge = _card("ukadk-guarding-height-external")
        out.append(_row("deck edge over the yard: drop", round(drop * 1000), g_drop, gd, True, "mm",
                        note=f"guarding required (drop > {g_drop} mm): {g_ext} mm high ({ge})"))
        dn = math.ceil(drop * 1000 / 185)
        dr = drop * 1000 / dn
        dg = round((DECK_STAIR[2] - DECK_STAIR[0]) * 1000 / (dn - 1))
        out.append(_row(f"deck-to-yard stair ({dn} risers)", round(dr, 1), rise_max, rc, dr <= rise_max, "mm",
                        note=f"going {dg} mm (min {going_min}); 2R+G {round(2 * dr + dg)} (range {lo}-{hi})"))
        w_need, wc = _card("mh-garage-passenger-width")
        l_need, lcard = _card("mh-garage-min-length")
        width = (FENCE_E - YE) * 1000
        length = (DECK_END - FENCE_N) * 1000
        out.append(_row("parking width, building face to fence", round(width), w_need, wc, width >= w_need, "mm"))
        out.append(_row("parking length for two cars in tandem", round(length), 2 * l_need, lcard,
                        length >= 2 * l_need - 1e-6, "mm", note="the second car blocks the first (tandem)"))
        out.append(_row("excavation below the basement floor for the room", round(LEVELS["B"] - (EXTRA_FFL - 0.25), 2),
                        "-", "structural consultant", True,
                        note="about 1.2 m below the basement FFL beside the fence and the building's east footings: "
                             "underpinning / retaining and waterproofing to be designed"))
    out.append(_row("fence top above the GF floor (sill needed to see over it)", round(E.FENCE_H / 1000 + LEVELS["B"] -
                    LEVELS["GF"], 2), "-", "environment model", True))
    return out
