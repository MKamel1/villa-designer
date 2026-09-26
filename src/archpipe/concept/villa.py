"""Concepts for the real villa (Sheikh Zayed): the fixed envelope, three concepts, and a villa-specific critic.

The envelope is not ours to invent: an 18.98 x 5.08 m bar on two storeys (basement -1.80, GF +1.20) between the
shared core (party wall, no daylight) and the east yard, with the apartment on top and the columns and perimeter
beams fixed (src/archpipe/villa_env.py, docs/villa/environment-model.md). The parti is forced by that: a spine along
the blind party wall for circulation and services, habitable rooms on the east facade band, full-depth rooms at the
street and rear ends. Round 4 (client review): the private stair is a U-stair in the old stair bay (the built
opening), checked in 3D against the kept structure in Python and in Revit (concept/stairs.py); the street strip is
an outdoor terrace, not floor area.

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
           },
    "B": {"core-lobby-b": ("h", YP, m(6940), m(8506)), "core-lobby-b2": ("h", YP, m(14134), m(15745)),
          "core-lobby-b-cross": ("v", m(6940), AX, YP)},
}


def _exts(extension):
    """The basement extensions as a list of rectangles (one rect, a list of rects, or None)."""
    if not extension:
        return []
    return [tuple(extension)] if isinstance(extension[0], (int, float)) else [tuple(e) for e in extension]


def envelope(level, extension=None):
    """Rectangles whose union is a storey's usable outline."""
    if level == "GF":
        rects = [(X0, YP, XR, YE), BUMP]              # the street strip is an outdoor terrace
    else:
        rects = [(X0, YP, XR, YE), FRONT_SHARE, REAR_SHARE] + _exts(extension)
    return rects


def window_faces(level, extension=None):
    """Envelope segments where a window may go: street, east and rear faces. The party wall faces the core
    (blind), the axis line faces the sister, the bathroom projection's sides face the core and a column."""
    if level == "GF":
        faces = [("v", X0, YP, YE), ("h", YE, X0, XR), ("v", XR, YP, YE)]   # street face opens onto the terrace
    else:
        faces = [("v", X0, AX, YE), ("v", XR, AX, YE)]
        east = [(X0, XR)]
        for x0, _, x1, y1 in _exts(extension):
            cut = []
            for a, b in east:                                   # the bar's east face is covered where it is built on
                cut += [(a, min(b, x0)), (max(a, x1), b)]
            east = [(a, b) for a, b in cut if b - a > 1e-6]
            faces.append(("v", x1, YE, y1))                     # the extension's end facing the yard
            if x0 < X0:
                pass       # its side toward the front yard stands on the NE yard wall (client 2026-09-26): no window
            else:
                faces.append(("v", x0, YE, y1))
            if y1 < FENCE_E - 0.05:                             # its long side, unless it is built to the fence
                faces.append(("h", y1, x0, x1))
        exts = _exts(extension)                                 # blocks built against each other: the joint is a wall
        faces = [f for f in faces if not (f[0] == "v" and sum(1 for r in exts if abs(r[0] - f[1]) < 1e-6
                                                                   or abs(r[2] - f[1]) < 1e-6) >= 2)]
        faces += [("h", YE, a, b) for a, b in east]
    return _minus_columns(faces)


def _minus_columns(faces, margin=0.1):
    """Face segments with the kept columns (and a frame margin) cut out: a window cannot sit on a column (round 8:
    the kitchen was credited with a 1.5 m face that a column split into two 0.5 m pieces, and the Revit spec
    dropped the window)."""
    cols = {}
    for x0, y0, x1, y1 in ((m(v) for v in c) for c in E.COLUMNS):
        for key, lo, hi, near in ((("h", YE), x0, x1, abs(y1 - YE) < 0.06), (("h", YP), x0, x1, abs(y0 - YP) < 0.06),
                                  (("v", X0), y0, y1, abs(x0 - X0) < 0.06), (("v", XR), y0, y1, abs(x1 - XR) < 0.06)):
            if near:
                cols.setdefault(key, []).append((lo - margin, hi + margin))
    out = []
    for ax, c, a, b in faces:
        runs = [(a, b)]
        for k, spans in cols.items():
            if k[0] != ax or abs(k[1] - c) > 1e-6:
                continue
            for s0, s1 in spans:
                runs = [r for lo, hi in runs for r in ((lo, min(hi, s0)), (max(lo, s1), hi)) if r[1] - r[0] > 1e-6]
        out += [(ax, c, lo, hi) for lo, hi in runs]
    return out


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
# Round 4 (client: "the stairs are wrong ... check the model and the pdf"): the U-stair in the OLD STAIR BAY. The
# DWG marks the built stair opening there (A-DETL, x 7.377-9.387); the old PDF has a U-stair there (goings 280, flights
# across the bar, corridor along the core wall). The well runs between the facade columns' faces (x 7.377-9.227), the
# half landing stops short of their inner face (y -24.101). 3D solids and clash checks: concept/stairs.py (Python)
# and revit/build_villa_stairs.py (Revit). The straight flight along the party wall (rounds 2-3) ran into column
# 1590377 and the front and party-wall beams.
SX0, SX1 = 7.377, 9.227
STAIR = (SX0, YC, SX1, YE)
TERRACE = (XS, YP, X0, YE)        # the street strip is an OUTDOOR terrace (Revit: 900 mm parapet walls, sliding door)
# Alternative B: secured parking on a street-level deck in the east strip behind a new gate, a room under it
FENCE_N = round(X0 - E.OFFSET_N / 1000.0, 3)                   # street fence inner face
DECK_END = 9.70                                                # two cars in tandem: 9.82 m from the fence
DECK = (FENCE_N, YE, DECK_END, FENCE_E)
DECK_STAIR = (DECK_END, round(FENCE_E - 1.0, 3), round(DECK_END + 2.25, 3), FENCE_E)   # 10 risers x 180, 9 x 250
EXTRA_FFL = -2.75                 # room under the deck: 0.95 m below the basement FFL (see elevation_checks)


def _room(rid, level, rect, occ, name=None, **kw):
    return dict({"id": rid, "level": level, "rect": [round(v, 3) for v in rect], "occupancy": occ,
                 "name": name or rid.replace("-", " ")}, **kw)


def _gf():
    rooms = [_room("study-game", "GF", (X0, YC, SX0, YE), "study", "study / game room (door to the terrace)"),
             _room("corridor", "GF", (X0, YP, 19.527, YC), "corridor", "hall"),
             _room("stair-gf", "GF", STAIR, "stair", "stair (U, from the basement)", ends=[["h", YC, SX1 - 0.9, SX1]]),
             _room("kids-a", "GF", (SX1, YC, 12.827, YE), "bedroom", "kids bedroom A"),
             _room("kids-b", "GF", (12.827, YC, 16.427, YE), "bedroom", "kids bedroom B"),
             _room("family-bath", "GF", (16.427, YC, 18.427, YE), "bathroom", "family bathroom"),
             _room("parents-bed", "GF", (18.427, YC, XR, YE), "bedroom", "parents' bedroom", suite=True, first=True),
             _room("parents-dressing", "GF", (19.527, YP, XR, YC), "dressing", "dressing", suite=True),
             _room("parents-ensuite", "GF", BUMP, "ensuite", "en-suite", suite=True)]
    links = [("corridor", "study-game"), ("corridor", "stair-gf"), ("corridor", "kids-a"), ("corridor", "kids-b"),
             ("corridor", "family-bath"), ("corridor", "parents-bed"), ("parents-bed", "parents-dressing"),
             ("parents-dressing", "parents-ensuite")]
    return rooms, links, [("corridor", "GF", "core-entrance")]


def _b(parking=False):
    rooms = [_room("laundry", "B", FRONT_SHARE, "utility", "laundry / pantry"),
             _room("hall-b", "B", (X0, YP, SX1, YC), "entrance", "entrance hall"),
             _room("flex", "B", (X0, YC, SX0, YE), "study", "flex room"),
             _room("stair-b", "B", STAIR, "stair", "stair (U, to the GF)", ends=[["h", YC, SX0, SX0 + 0.9]]),
             _room("gallery", "B", (SX1, YP, 11.397, YK), "hall", "gallery"),
             _room("kitchen", "B", (SX1, YK, 15.197, YE), "kitchen", "open kitchen"),
             _room("dirty-kitchen", "B", (11.397, YP, 13.797, YK), "utility", "dirty kitchen"),
             _room("guest-wc", "B", (13.797, YP, 15.197, YK), "wc", "guest WC"),
             _room("dining", "B", (15.197, YP, 18.597, YE), "dining", "dining"),
             _room("living", "B", (18.597, YP, XR, YE), "living", "garden living"),
             _room("store-rear", "B", REAR_SHARE, "store", "store")]
    links = [("hall-b", "laundry"), ("hall-b", "flex"), ("hall-b", "stair-b"), ("hall-b", "gallery"),
             ("gallery", "kitchen"), ("gallery", "dirty-kitchen"), ("dirty-kitchen", "kitchen"), ("dining", "guest-wc"),
             ("kitchen", "dining"), ("dining", "living"), ("living", "store-rear")]
    if parking:
        rooms.append(_room("extra-room", "B", DECK, "study", "extra room under the parking (FFL -2.75)",
                           ffl=EXTRA_FFL))
        links.append(("flex", "extra-room"))
    return rooms, links, [("hall-b", "B", "core-lobby-b")]


def concept_a():
    g, gl, ge = _gf()
    b, bl, be = _b()
    lay = _layout("A", "Garden living below, bedrooms above", g + b, gl + bl, ge + be,
                  "Living, dining and kitchen at yard level open to the garden, terrace and BBQ; bedrooms on the GF "
                  "above the fence line; the parents' suite at the rear on the existing wet stack; the private stair "
                  "is a U-stair in the old stair bay (built opening), both ends on the hall along the core wall.")
    lay["stair"] = "u"
    lay["terrace"] = list(TERRACE)
    return lay


def concept_b():
    g, gl, ge = _gf()
    b, bl, be = _b(parking=True)
    lay = _layout("B", "A + secured parking behind the gate, extra room underneath", g + b, gl + bl, ge + be,
                  "As A, with a street-level parking deck for two cars in tandem in the east strip behind a new "
                  "gate, a stair from the deck down to the yard, and an extra room under the deck reached from the "
                  "flex room, its floor lowered to -2.75 for headroom.")
    lay["stair"] = "u"
    lay["terrace"] = list(TERRACE)
    lay["extension"] = list(DECK)
    lay["parking"] = {"deck": list(DECK), "deck_stair": list(DECK_STAIR), "deck_top": 0.0}
    return lay


def _layout(cid, title, rooms, links, entries, summary):
    return {"id": cid, "title": title, "summary": summary, "levels": dict(LEVELS),
            "rooms": {r["id"]: r for r in rooms},
            "links": [list(l) for l in links], "entries": [list(e) for e in entries],
            "vertical": [["stair-b", "stair-gf"]]}


def concepts():
    """Round 4 (client 2026-09-25): A with the flex room and the U-stair; alternative B with parking."""
    return [concept_a(), concept_b()]


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
    "stair_structure": "The stair as 3D solids (treads, landing, 2.0 m headroom: card ukadk-stair-headroom-min) must "
                       "not intersect the columns and beams we must keep (client); Revit's intersection filter is the "
                       "independent second check (scripts/villa_stairs.py compare). Round 3's flight hit column 1590377.",
    "stair_access": "Each end of a stair (the foot on the lower storey, the arrival on the upper) must open onto "
                    "circulation, so people reach it without crossing a room; a stair modelled as one room joined to "
                    "a hall hid a foot that only a flex room and a laundry touched (LEARNINGS 2026-09-25).",
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
    # an open-plan zone with no window of its own, joined without a wall to a room that has one, borrows light:
    # reported as a warning (it is darker, and says so), not hidden and not a failure
    open_occ = {"kitchen", "dining", "living", "hall", "corridor", "entrance", "landing"}
    lit = {r for r in rooms if r not in dark and rooms[r]["occupancy"] in vocab.HABITABLE}
    comp = {r: r for r in rooms}                           # open-plan areas: rooms joined without a wall

    def root(r):
        while comp[r] != r:
            r = comp[r]
        return r
    for a, b in lay["links"]:
        if (rooms[a]["occupancy"] in open_occ and rooms[b]["occupancy"] in open_occ
                and rooms[a]["level"] == rooms[b]["level"]):
            comp[root(a)] = root(b)
    lit_roots = {root(r) for r in lit}
    borrowed = sorted(r for r in dark if rooms[r]["occupancy"] in open_occ and root(r) in lit_roots)
    hard = [r for r in dark if r not in borrowed]
    out.append(_chk("window", "fail" if hard else ("warning" if borrowed else "pass"), rooms=hard,
                    borrowed_light=borrowed))
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
    blocked_ends = []
    for rid, r in rooms.items():
        if r["occupancy"] != "stair":
            continue
        if not r.get("ends"):
            blocked_ends.append({"stair": rid, "problem": "ends not declared"})
            continue
        for end in r["ends"]:
            seg = tuple(end)
            across = [o for o, v in rooms.items() if o != rid and v["level"] == r["level"] and
                      max(overlap_len(e, seg) for e in edges(v["rect"])) >= 0.8]   # a 0.9 m flight, float-safe
            if not any(rooms[o]["occupancy"] in vocab.CIRCULATION for o in across):
                blocked_ends.append({"stair": rid, "end": list(seg), "opens_onto": across or ["nothing"]})
    out.append(_chk("stair_access", "fail" if blocked_ends else "pass", ends=blocked_ends))
    from . import stairs as S
    cl = S.clashes(stair_model(lay.get("stair", "u")))
    hits = sorted({h["structure"] for h in cl["hits"]})
    out.append(_chk("stair_structure", "fail" if hits else "pass", clashes=hits,
                    gf_slab_opening_needed_mm=[round(v) for v in cl["slab_opening_needed"]]))
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


REVIT_STAIR_COMPARED = {"u", "party-fixed", "u-length", "party-r8"}   # scripts/villa_stairs.py compare agreed


def stair_model(key="u"):
    """The layout's private stair as 3D solids (concept/stairs.py), by the layout's 'stair' key."""
    from . import stairs as S
    from . import stair_options as SO
    return {"u": S.u_in_old_bay, "r3": S.r3_party_flight, "spine": S.r3_party_flight,    # spine: the r2/r3 flight
            "party-fixed": S.party_flight_fixed,
            "u-length": S.u_lengthwise_party, "party-r8": S.party_flight_r8, "u-front": SO.u_front_bay}[key]()


def stair_geometry(stair="u"):
    """Rise/going of the private stair (basement -1.80 to GF +1.20), from the layout's own 3D model. The 'run fits
    its zone' figure applies to the U across the bar (its half landing short of the facade columns); for the
    other stairs the 3D clash check is the fit test."""
    from . import stairs as S
    st = stair_model(stair)
    rise, going = st["rise"], st["going"]
    out = {"risers": st["risers"], "rise": round(rise, 1), "going": going, "name": st["name"],
           "pitch_deg": round(math.degrees(math.atan2(rise, going)), 1), "two_r_plus_g": round(2 * rise + going)}
    if stair == "u":
        run_needed = (8 * going + S.LANDING_DEPTH)             # the longer flight plus the half landing
        run_available = (U_LANDING_LIMIT - YC) * 1000
        out.update(run_needed=round(run_needed), run_available=round(run_available),
                   fits=run_needed <= run_available)
    return out


U_LANDING_LIMIT = -24.101           # inner face of the facade columns 1585908 / 1585915 (CAD)


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
    g = stair_geometry(lay.get("stair", "u"))
    rise_max, rc = _card("ukadk-private-stair-rise-max")
    going_min, gc = _card("ukadk-private-stair-going-min")
    pitch_max, pc = _card("ukadk-private-stair-pitch-max")
    lo, lc = _card("ukadk-2r-plus-g-min")
    hi, _ = _card("ukadk-2r-plus-g-max")
    head, hc = _card("ukadk-stair-headroom-min")
    out += [_row(f"private stair rise ({g['risers']} risers over 3.00 m)", g["rise"], rise_max, rc, g["rise"] <= rise_max, "mm"),
            _row("private stair going", g["going"], going_min, gc, g["going"] >= going_min, "mm"),
            _row("private stair pitch", g["pitch_deg"], pitch_max, pc, g["pitch_deg"] <= pitch_max, "deg"),
            _row("private stair 2R+G", g["two_r_plus_g"], f"{lo}-{hi}", lc, lo <= g["two_r_plus_g"] <= hi, "mm")]
    if "fits" in g:
        out.append(_row("private stair run fits its zone", g["run_available"], g["run_needed"], "geometry", g["fits"],
                        "mm"))
    from . import stairs as S
    key = lay.get("stair", "u")
    cl = S.clashes(stair_model(key))
    hits = sorted({h["structure"] for h in cl["hits"]})
    agree = ("Revit read-back agrees (scripts/villa_stairs.py compare)" if key in REVIT_STAIR_COMPARED else
             "Python 3D check only (no Revit clash compare for this stair yet)")
    out.append(_row("stair in 3D vs kept columns and beams (%s)" % g["name"], len(hits), 0, hc,
                    not hits, "clashes", note=("; ".join(hits) if hits else "none; " + agree) +
                    "; GF slab opening needed x %.2f to %.2f, y %.2f to %.2f" % tuple(
                        cl["slab_opening_needed"][i] / 1000 for i in (0, 2, 1, 3))))
    pk2 = lay.get("parking2")
    if pk2:
        from . import villa_parking as P
        g = pk2["gradient"] * 100
        nmax, nc = _card("neufert-private-garage-slope-max")
        gmax, gc = _card("mh-garage-ramp-max")
        length = pk2["ramp"][2] - pk2["ramp"][0]
        out.append(_row("parking ramp: main gradient vs private basement-garage maximum", round(g, 1), nmax, nc,
                        g <= nmax + 1e-9, "%", note="ramp %.1f m from the gate, up to the GF level (+%.2f)"
                                                     % (length, pk2["deck_top"])))
        row = _row("parking ramp: main gradient vs garage-ramp limit", round(g, 1), gmax, gc, g <= gmax + 1e-9, "%")
        if row["status"] == "fail":                   # client decision, recorded as a waiver (CLAUDE.md authority)
            row.update(status="waived", note="client 2026-09-26: 'make the ramp reach the ground floor level at "
                                             "the door (ramp climb faster)'; at 10 % the ramp would need 12 m")
        out.append(row)
        t_len, t_g = pk2.get("transition", (0, 0))
        out.append(_row("parking ramp: eased ends (vertical transitions)", "%.1f m at %d %%" % (t_len, t_g * 100),
                        "-", gc, True, "", note="MH p. 38-12: steep gradients need vertical transition curves at each "
                        "end and should be avoided near the back of the pavement; lengths ASSUMED, civil designer"))
        out.append(_row("room under the deck: clear height (floor -1.80, soffit +%.2f)" % pk2["soffit"],
                        round(pk2["soffit"] - LEVELS["B"], 2), ceil_min, ceil_card,
                        pk2["soffit"] - LEVELS["B"] >= ceil_min - 1e-9,
                        note="the deck is level with the GF, so the rooms under it are taller than the basement"))
        for rid, r in lay["rooms"].items():
            if not r.get("ext") or r["rect"][0] >= P.RAMP_X1 - 1e-6:
                continue
            lo, hi = P.clear_at(max(r["rect"][0], P.RAMP_X0)), P.clear_at(min(r["rect"][2], P.RAMP_X1))
            need = 2.0 if r["occupancy"] in ("utility", "wc") else None
            out.append(_row("%s: clear height under the ramp" % r["name"].split(" (")[0], "%.2f-%.2f" % (lo, hi),
                            "-" if need is None else need, "project judgement (client: working height; 2.0 m = "
                            "door height)", need is None or lo >= need - 1e-9, "m"))
        g_drop, gd = _card("ukadk-guarding-drop-dwelling")
        g_ext, ge = _card("ukadk-guarding-height-external")
        drop = pk2["deck_top"] - LEVELS["B"]
        out.append(_row("deck end over the yard: drop", round(drop * 1000), g_drop, gd, True, "mm",
                        note="guard rail %d mm modelled (%s)" % (g_ext, ge.split(" (")[0])))
        wx1 = E.YARD_WALL[2] / 1000
        edge_drop = P.top_at(wx1) - LEVELS["B"]
        out.append(_row("ramp's west edge over the sunken north patio: drop (at the villa)", round(edge_drop * 1000),
                        g_drop, gd, True, "mm", note="guard rail %d mm modelled along the ramp edge" % g_ext))
        fence_above = E.FENCE_H / 1000 + LEVELS["B"] - pk2["deck_top"]
        rail = g_ext if fence_above * 1000 < g_ext else round(fence_above * 1000)
        out.append(_row("guarding along the east fence above the deck", rail, g_ext, ge, rail >= g_ext, "mm",
                        note="the fence is only %d mm above the deck: a %d mm guard rail is modelled along it"
                             % (round(fence_above * 1000), g_ext) if rail != round(fence_above * 1000) else
                        "the fence itself"))
        eye = pk2["deck_top"] + 1.6 - LEVELS["GF"]
        out.append(_row("GF windows beside the deck: sill above the eye of a person on the deck", round(eye + 0.1, 2),
                        round(eye, 2), "geometry (privacy; eye 1.6 m ASSUMED)", True, "m",
                        note="the deck is level with the GF: windows there are high strips (%.2f-%.2f m)"
                             % (eye + 0.1, 2.30)))
        dd = lay.get("deck_door")
        if dd:
            out.append(_row("study door onto the deck: threshold vs deck", round(pk2["deck_top"], 2),
                            LEVELS["GF"], "geometry", abs(pk2["deck_top"] - LEVELS["GF"]) < 1e-6, "m",
                            note="%.2f m bypass sliding door between the columns at x %.3f-%.3f; level threshold "
                                 "with a linear drain (ASSUMED detail)" % (dd["width"], dd["x0"], dd["x1"])))
            out.append(_row("ramp top reached before the study door", round(P.RAMP_X1, 3), dd["x0"], "geometry",
                            P.RAMP_X1 <= dd["x0"] + 1e-6, "m (x)"))
        out.append(_row("people on the deck overlook the neighbour (eye vs fence top)",
                        round(pk2["deck_top"] + 1.6, 2), round(E.FENCE_H / 1000 + LEVELS["B"], 2),
                        "geometry (street datum)", True, "-", note="advisory: the fence is %.2f m above the deck"
                                                                    % fence_above))
        out[-1]["status"] = "advisory"
        w_need, wc = _card("mh-garage-passenger-width")
        l_need, lcard = _card("mh-garage-min-length")
        length = (pk2["deck"][2] - pk2["deck"][0]) * 1000
        out.append(_row("parking width, building face to fence", round((FENCE_E - YE) * 1000), w_need, wc,
                        (FENCE_E - YE) * 1000 >= w_need, "mm"))
        out.append(_row("parking deck length for %d car(s)" % pk2["cars"], round(length), pk2["cars"] * l_need, lcard,
                        length >= pk2["cars"] * l_need - 1e-6, "mm",
                        note="tandem, tight" if pk2["cars"] == 2 else "one car with 1.0 m to spare"))
        # the NE yard wall (client 2026-09-26) runs under the ramp's west edge from the gate to the NE column
        wx0, wy0, wx1, wy1 = (v / 1000 for v in E.YARD_WALL)
        w_top = LEVELS["B"] + E.YARD_WALL_H / 1000
        gaps = [round((P.clear_at(x) + LEVELS["B"]) - w_top, 2) for x in (wx0, wx1)]
        out.append(_row("NE yard wall top (street %.2f) under the ramp soffit: gap gate / column" % w_top,
                        "%.2f / %.2f" % tuple(gaps), 0.0, "geometry (environment model)", min(gaps) >= -1e-9, "m",
                        note="the ramp clears the kept wall; it can bear on it with a %d-%d mm upstand (structural "
                             "consultant)" % (gaps[0] * 1000, gaps[1] * 1000)))
        np_ = lay.get("north_patio")
        if np_:
            a, b, c, d = np_["rect"]
            ca, _, cc, _ = np_["covered"]
            out.append(_row("north sunken patio: open-sky depth vs street fence height", round(ca - a, 2),
                            "-", "geometry (environment model)", True, "m",
                            note="%.1f m2 at -1.80 (%.1f m2 under the GF terrace); from the lounge glass at 0.9 m the "
                                 "sky shows only between the fence top (%.0f deg) and the terrace soffit (%.0f deg)"
                                 % ((c - a) * (d - b), (cc - ca) * (d - b),
                                    math.degrees(math.atan2(E.FENCE_H / 1000 - 0.9, cc - a)),
                                    math.degrees(math.atan2(2.8 - 0.9, cc - ca)))))
        from . import revit_spec as RS                                  # lazy: revit_spec imports this module
        sp = RS.build(lay)
        for d in sp["doors"]:
            if "fit" not in d:
                continue
            kind = {"full": "room door", "reduced": "room door, leaf reduced by the ramp",
                    "low": "cupboard-height door (store)", "none": "NO door fits"}[d["fit"]]
            out.append(_row("door %s: leaf + frame under the ramp/deck" % " -> ".join(d["rooms"]),
                            round(d["height"] + P.HEAD_ZONE, 2), round(d["clear"], 2),
                            "geometry; leaf %.2f (%s), frame %.2f ASSUMED" % (d["height"], kind, P.HEAD_ZONE),
                            d["fit"] != "none", "m"))
        probs = RS.clearance_problems(lay, sp["walls"], sp["doors"], sp.get("infills", []))
        out.append(_row("walls and doors under the ramp/deck fit under its soffit (spec)", len(probs), 0,
                        "geometry post-condition (revit_spec.clearance_problems)", not probs, "problems",
                        note="; ".join(probs[:3])))
        gate = round((FENCE_E - wy1) * 1000)
        out.append(_row("car gate: yard wall to east fence", gate, w_need, wc, gate >= w_need, "mm"))
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
