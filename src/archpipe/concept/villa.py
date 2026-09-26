"""Concepts for the real villa (Sheikh Zayed): the fixed envelope, three concepts, and a villa-specific critic.

The envelope is not ours to invent: an 18.98 x 5.08 m bar on two storeys (basement -1.80, GF +1.20) between the
shared core (party wall, no daylight) and the east yard, with the apartment on top and the columns and perimeter
beams fixed (src/archpipe/villa_env.py, docs/villa/environment-model.md). The parti is forced by that: a spine along
the blind party wall for circulation and services, habitable rooms on the east facade band, full-depth rooms at the
street and rear ends, the private stair in the 2.2 m column bay beside the core doors on both storeys.

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
        faces = [("v", X0, AX, YE), ("h", YE, X0, XR), ("v", XR, AX, YE)]
        if extension:
            x0, _, x1, y1 = extension
            faces = [("v", X0, AX, YE), ("h", YE, X0, x0), ("h", YE, x1, XR), ("v", XR, AX, YE),
                     ("v", x0, YE, y1), ("v", x1, YE, y1)]
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


# ---- the three concepts -----------------------------------------------------------------------------------------
YC = round(YP + 1.3, 3)          # spine depth 1.3 m: 0.9 m clear hall after the party wall (AD M para 2.22a)
YK = round(YP + 2.0, 3)          # deeper service spine in the kitchen zone: 1.75 m clear for a galley or a WC
STAIR = (7.197, YC, 9.397, YE)   # dog-leg in the 2.2 m column bay, stacked on both storeys


def _room(rid, level, rect, occ, name=None, **kw):
    return dict({"id": rid, "level": level, "rect": [round(v, 3) for v in rect], "occupancy": occ,
                 "name": name or rid.replace("-", " ")}, **kw)


def _gf_bedrooms(strip_use="study"):
    rooms = []
    if strip_use == "study":
        rooms += [_room("study-game", "GF", (XS, YC, 7.197, YE), "study", "study / game room"),
                  _room("store-gf", "GF", (XS, YP, X0, YC), "store", "store")]
        corridor_from = X0
    else:                                   # the strip becomes our own front door off the shared entrance steps
        rooms += [_room("vestibule", "GF", (XS, YP, X0, YE), "entrance", "private entrance vestibule"),
                  _room("study-game", "GF", (X0, YC, 7.197, YE), "study", "study / game room")]
        corridor_from = X0
    rooms += [
        _room("corridor", "GF", (corridor_from, YP, 18.597, YC), "corridor", "hall"),
        _room("stair-gf", "GF", STAIR, "stair", "stair to basement"),
        _room("kids-a", "GF", (9.397, YC, 12.997, YE), "bedroom", "kids bedroom A"),
        _room("kids-b", "GF", (12.997, YC, 16.597, YE), "bedroom", "kids bedroom B"),
        _room("family-bath", "GF", (16.597, YC, 18.597, YE), "bathroom", "family bathroom"),
        _room("parents-bed", "GF", (18.597, YC, XR, YE), "bedroom", "parents' bedroom", suite=True, first=True),
        _room("parents-dressing", "GF", (18.597, YP, XR, YC), "dressing", "dressing", suite=True),
        _room("parents-ensuite", "GF", BUMP, "ensuite", "en-suite", suite=True),
    ]
    links = [("corridor", "stair-gf"), ("corridor", "study-game"), ("corridor", "kids-a"), ("corridor", "kids-b"),
             ("corridor", "family-bath"), ("corridor", "parents-dressing"), ("parents-dressing", "parents-bed"),
             ("parents-dressing", "parents-ensuite")]
    if strip_use == "study":
        links.append(("corridor", "store-gf"))
        entries = [("corridor", "GF", "core-entrance")]
    else:
        links.append(("vestibule", "corridor"))
        entries = [("vestibule", "GF", "steps-landing"), ("corridor", "GF", "core-entrance")]
    return rooms, links, entries


def _b_living(extension=False):
    rooms = [
        _room("pantry", "B", FRONT_SHARE, "store", "pantry / store"),
        _room("laundry", "B", (X0, YP, 7.197, -26.071), "utility", "laundry"),
        _room("flex", "B", (X0, -26.071, 7.197, YE), "study", "flex (optional)"),
        _room("hall-b", "B", (7.197, YP, 9.397, YC), "entrance", "entrance hall"),
        _room("stair-b", "B", STAIR, "stair", "stair to GF"),
        _room("gallery", "B", (9.397, YP, 11.397, YK), "hall", "gallery"),
        _room("kitchen", "B", (9.397, YK, 15.197, YE), "kitchen", "open kitchen"),
        _room("dirty-kitchen", "B", (11.397, YP, 13.797, YK), "utility", "dirty kitchen"),
        _room("guest-wc", "B", (13.797, YP, 15.197, YK), "wc", "guest WC"),
        _room("dining", "B", (15.197, YP, 18.597, YE), "dining", "dining"),
        _room("living", "B", (18.597, YP, XR, YE), "living", "garden living"),
        _room("store-rear", "B", REAR_SHARE, "store", "store"),
    ]
    links = [("hall-b", "stair-b"), ("hall-b", "laundry"), ("hall-b", "gallery"), ("gallery", "kitchen"),
             ("gallery", "dirty-kitchen"), ("dirty-kitchen", "kitchen"), ("dining", "guest-wc"),
             ("kitchen", "dining"), ("dining", "living"), ("living", "store-rear"), ("laundry", "pantry"),
             ("stair-b", "flex")]
    if extension:
        ext = (11.397, YE, 18.597, FENCE_E)
        rooms.append(_room("family-ext", "B", ext, "living", "family / play (rooflights)",
                           rooflight=True))
        links += [("kitchen", "family-ext"), ("dining", "family-ext")]
    return rooms, links, [("hall-b", "B", "core-lobby-b")]


def concept_a():
    g, gl, ge = _gf_bedrooms("study")
    b, bl, be = _b_living()
    return _layout("A", "Garden living below, bedrooms above", g + b, gl + bl, ge + be,
                   "Living, dining and kitchen at yard level open to the garden, terrace and BBQ; bedrooms on the "
                   "GF above the fence line; the parents' suite at the rear on the existing wet stack.")


def concept_b():
    g, gl, ge = _gf_bedrooms("vestibule")
    b, bl, be = _b_living(extension=True)
    lay = _layout("B", "A + basement extension into the east yard + private front door", g + b, gl + bl, ge + be,
                  "As A, with the basement extended 2.99 m to the east fence under a GF-level deck (family / play "
                  "room, rooflights), and the street strip as our own front door off the shared entrance steps.")
    lay["extension"] = [11.397, YE, 18.597, FENCE_E]
    return lay


def concept_c():
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
        _room("parents-bed", "B", (16.597, YC, XR, YE), "bedroom", "parents' bedroom", suite=True,
              first=True),
        _room("parents-dressing", "B", (18.597, YP, XR, YC), "dressing", "dressing", suite=True),
        _room("parents-ensuite", "B", REAR_SHARE, "ensuite", "en-suite", suite=True),
    ]
    bl = [("corridor-b", "family-bath"), ("corridor-b", "linen"), ("corridor-b", "kids-a"), ("corridor-b", "stair-b"),
          ("corridor-b", "kids-b"), ("corridor-b", "study-game"), ("corridor-b", "parents-bed"),
          ("parents-bed", "parents-dressing"), ("parents-dressing", "parents-ensuite")]
    return _layout("C", "Reverse: living on the GF, bedrooms at yard level", gf + b, gl + bl,
                   [("hall", "GF", "core-entrance"), ("corridor-b", "B", "core-lobby-b")],
                   "Living, kitchen and dining on the entrance storey above the fence line; bedrooms at yard "
                   "level behind the 4 m fence, the parents' suite opening to the private rear garden.")


def _layout(cid, title, rooms, links, entries, summary):
    return {"id": cid, "title": title, "summary": summary, "levels": dict(LEVELS),
            "rooms": {r["id"]: r for r in rooms},
            "links": [list(l) for l in links], "entries": [list(e) for e in entries],
            "vertical": [["stair-b", "stair-gf"]]}


def concepts():
    return [concept_a(), concept_b(), concept_c()]


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
