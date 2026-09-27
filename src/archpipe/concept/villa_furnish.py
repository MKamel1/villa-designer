"""D1 furnished (client r12: "furnish D1, make sure the sizes are reasonable and follow best practice; it must pass
every check before lighting, finishes and renders").

The layout is AUTHORED, not generated (the AI is a critic, not an inventor): each piece is placed against a named
wall of its room with a one-line reason, then every check below runs against the placement. Sizes come from
`catalogue.py` (ENVELOPE = an assumed product size until the product is chosen); clearances cite held cards.
Answers assumed: the questionnaire's suggested defaults (out/villa/questionnaire), until the client changes them.

Units: metres, Revit project axes (x from the street to the garden, y from the party wall YP to the east face YE).
An item's local frame: front = +Y (the side used), right = +X; `rot` turns it: 0 front +y, 180 front -y,
-90 front +x, 90 front -x. Clearances are given per local side in catalogue.py (mm).
"""
from __future__ import annotations

import collections

import numpy as np

from .. import catalogue as cat
from . import revit_spec as RS
from . import villa as V
from . import villa_parking as VP
from . import villa_r11 as R

SIDES = ("front", "back", "left", "right")
DIRS = {0: {"front": (0, 1), "back": (0, -1), "right": (1, 0), "left": (-1, 0)},
        180: {"front": (0, -1), "back": (0, 1), "right": (-1, 0), "left": (1, 0)},
        -90: {"front": (1, 0), "back": (-1, 0), "right": (0, -1), "left": (0, 1)},
        90: {"front": (-1, 0), "back": (1, 0), "right": (0, 1), "left": (0, -1)}}
BODY = 0.914            # card mitton-path-of-travel-min: paths of travel at least 36 in (914 mm)
PRINCIPAL_BEDROOM = "parents-bed"
BEDROOM_ROUTE = 0.750   # card ukadm-bedroom-route-750: inside a bedroom, a 750 mm access route from the doorway
SEAT_EYE = 0.45         # eye behind the seat front (ASSUMED) for viewing distances


def item(iid, room, typ, cx, cy, rot=0, w=None, d=None, h=0.8, why="", **kw):
    t = cat.get(typ)
    return dict(id=iid, room=room, type=typ, cx=round(cx, 3), cy=round(cy, 3), rot=rot,
                w=w if w is not None else t.width / 1000, d=d if d is not None else t.depth / 1000, h=h, why=why, **kw)


def against(iid, room_rect, edge, start, typ, w=None, d=None, gap=0.0, **kw):
    """A piece with its back on one edge of the room ('x0' street side, 'x1' garden side, 'y0' party side, 'y1' east
    side), starting at `start` along that edge (increasing x or y)."""
    t = cat.get(typ)
    w = w if w is not None else t.width / 1000
    d = d if d is not None else t.depth / 1000
    x0, y0, x1, y1 = room_rect
    if edge == "y0":
        return item(iid, None, typ, start + w / 2, y0 + gap + d / 2, 0, w, d, **kw)
    if edge == "y1":
        return item(iid, None, typ, start + w / 2, y1 - gap - d / 2, 180, w, d, **kw)
    if edge == "x0":
        return item(iid, None, typ, x0 + gap + d / 2, start + w / 2, -90, w, d, **kw)
    return item(iid, None, typ, x1 - gap - d / 2, start + w / 2, 90, w, d, **kw)


def footprint(it):
    hw, hd = (it["w"] / 2, it["d"] / 2) if it["rot"] in (0, 180) else (it["d"] / 2, it["w"] / 2)
    return (it["cx"] - hw, it["cy"] - hd, it["cx"] + hw, it["cy"] + hd)


def side_zone(it, side, depth):
    """The rectangle of `depth` m beside one local side, as wide as that side."""
    x0, y0, x1, y1 = footprint(it)
    dx, dy = DIRS[it["rot"]][side]
    if dx > 0:
        return (x1, y0, x1 + depth, y1)
    if dx < 0:
        return (x0 - depth, y0, x0, y1)
    if dy > 0:
        return (x0, y1, x1, y1 + depth)
    return (x0, y0 - depth, x1, y0)


def module_spans(it):
    """World spans [(kind, a, b)] of a run's modules along its length (x for rot 0/180, y for +-90), left to right
    in the item's own frame."""
    x0, y0, x1, y1 = footprint(it)
    lo, hi = (x0, x1) if it["rot"] in (0, 180) else (y0, y1)
    sign = 1 if (it["rot"] in (0, 90)) else -1        # local +x runs along +world for rot 0 and 90
    out, pos = [], 0.0
    for kind, w in it.get("modules", []):
        a, b = pos, pos + w
        pos = b
        out.append((kind, lo + a, lo + b) if sign > 0 else (kind, hi - b, hi - a))
    return out


ZONE_A = 0.600          # card ukadm-bedside-zone-a-600: bedside furniture may stand in the 600 mm at the bed head


def head_zone(it, length):
    """The band `length` m long at a bed's head end (its local back), across the bed and its side zones."""
    x0, y0, x1, y1 = footprint(it)
    dx, dy = DIRS[it["rot"]]["back"]
    big = 5.0
    if dx < 0:
        return (x0, y0 - big, x0 + length, y1 + big)
    if dx > 0:
        return (x1 - length, y0 - big, x1, y1 + big)
    if dy < 0:
        return (x0 - big, y0, x1 + big, y0 + length)
    return (x0 - big, y1 - length, x1 + big, y1)


def _ov(a, b, tol=1e-3):            # 1 mm: a piece set against a wall touches it, it does not overlap
    return min(a[2], b[2]) - max(a[0], b[0]) > tol and min(a[3], b[3]) - max(a[1], b[1]) > tol


# ---- the D1 layout ----------------------------------------------------------------------------------------------
def clear_rect(lay, rid):
    """The room's floor clear of its walls: inset 0.20 m on the building envelope (external walls sit inside the outer
    face), half a partition (0.05 m) where it meets a closed room, nothing where it opens into its own open-plan
    cluster. Round 12: pieces were first placed against the room outlines, i.e. inside the walls."""
    r = lay["rooms"][rid]
    lv = r["level"]
    outline = V.boundary_segments(V.envelope(lv, lay.get("extension")))
    cl = _cluster(lay, rid) - {rid}
    x0, y0, x1, y1 = r["rect"]
    ins = []
    for e in V.edges(r["rect"]):                       # bottom (y0), top (y1), left (x0), right (x1)
        L = e[3] - e[2]
        if sum(V.overlap_len(e, s) for s in outline) > 0.5 * L:
            ins.append(RS.EXT_T)
        elif sum(V.overlap_len(e, f) for c in cl for f in V.edges(lay["rooms"][c]["rect"])) > 0.5 * L:
            ins.append(0.0)
        else:
            ins.append(RS.INT_T / 2)
    return (round(x0 + ins[2], 3), round(y0 + ins[0], 3), round(x1 - ins[3], 3), round(y1 - ins[1], 3))


def layout(lay=None):
    """D1, furnished for the client's questionnaire answers (2026-09-27)."""
    lay = lay or R.design("D1")
    r = {k: clear_rect(lay, k) for k in lay["rooms"]}
    items = []

    def add(it, room, **kw):
        it.update(room=room, **kw)
        items.append(it)

    # ================= basement =================
    # -- street lounge (family TV): 4-seat sofa + armchair, 75 in TV; the way to the pantry and the patio door kept
    L = r["lounge"]
    add(against("lounge-tv", L, "y1", 5.0, "tv_unit", w=2.0, h=0.5,
                why="TV wall between the NE column and the column at x 7.0 (east face); 75 in screen"), "lounge",
        screen_in=75)
    add(item("lounge-sofa", None, "sofa_4seat", 6.22, L[1] + 0.575, 0, h=0.85,
             why="facing the TV, back to the stair balustrade; 1.10 m clear at its street end, past the nook column, to the pantry"),
        "lounge", views="lounge-tv")
    add(item("lounge-coffee", None, "coffee_table", 6.22, L[1] + 0.1 + 0.95 + 0.462 + 0.3, 0, w=1.2, d=0.6, h=0.4,
             why="457 mm from the sofa (card mitton-sofa-coffee-table-457)"), "lounge")
    add(item("lounge-armchair", None, "armchair", 8.3, -26.2, -90, h=0.85,
             why="fifth seat, turned to the TV and the family corner"), "lounge")
    # -- kitchen: tall wall (fridge-freezer, oven + combi) on the party side, sink run on the east face, 5-seat island
    K, KI = r["kitchen"], r["kitchen-island"]
    add(against("k-tall", KI, "y0", KI[0], "base_run", w=2.25, d=0.6, h=2.3,
                modules=[("counter", 0.45), ("fridge", 0.6), ("oven", 0.6), ("counter", 0.6)],
                why="integrated fridge-freezer and an oven + combi column (answers); 450 counter beside the fridge "
                    "(card nkba-fridge-landing-381); coffee machine on the counter"), "kitchen-island")
    add(against("k-run", K, "y1", 11.54, "base_run", w=2.41, d=0.6, h=0.9,
                modules=[("counter", 0.5), ("sink", 0.9), ("dw", 0.6), ("counter", 0.41)],
                why="sink under the east wall between column 4 and the dirty-kitchen door; the one dishwasher beside it"),
        "kitchen")
    run_front = K[3] - 0.6
    add(item("k-island", None, "island", 13.075, run_front - 1.219 - 0.55, 0, w=3.05, d=1.1, h=0.92,
             modules=[("counter", 1.05), ("hob", 0.9), ("counter", 1.1)], stools=5,
             why="5 stools at 610 mm (card nkba-seating-width-610) on the party side, 1118 mm behind them to walk "
                 "past to the tall wall (card nkba-seating-walk-past-1118); hob side faces the sink run across a 1.22 m "
                 "aisle; 800 mm counter + 300 mm overhang"), "kitchen")
    # -- dining (bay 5-6): table for 6, extends to 10
    D, DS = r["dining"], r["dining-side"]
    add(item("dining-table", None, "dining_6x", 16.95, -25.9, 0, h=0.75, chairs=6,
             why="1.8 x 0.9 for 6, extends to 2.8 m for 10 (the largest gatherings of 20 need a second table: garden "
                 "or living); 965 mm passage both long sides"), "dining")
    add(against("dining-sideboard", DS, "y0", 16.3, "sideboard", w=1.8, h=0.8, why="serving sideboard"), "dining-side")
    # -- garden living + library alcove
    G, A = r["living"], r["bar-alcove"]
    add(item("living-sofa", None, "sofa_3seat", 20.35, -28.0, 0, h=0.85,
             why="back to the library alcove, facing the east garden door; both garden doors stay open to reach"),
        "living")
    add(item("living-coffee", None, "coffee_table", 20.35, -26.793, 0, w=1.1, d=0.6, h=0.4,
             why="457 mm from the sofa"), "living")
    add(item("living-chair-1", None, "armchair", 19.925, -25.611, 180, h=0.85,
             why="facing the sofa across the table"), "living")
    add(item("living-chair-2", None, "armchair", 20.825, -25.611, 180, h=0.85,
             why="facing the sofa across the table; 1.4 m to the east garden door"), "living")
    add(against("alcove-books", A, "y0", 18.45, "bookcase", w=3.3, d=0.3, h=2.2,
                why="library wall along the back of the rear share (backlit shelves: answers)"), "bar-alcove")
    add(against("alcove-bench", A, "x1", A[1] + 0.05, "window_bench", w=0.85, d=0.5, h=0.45,
                why="reading seat at the garden window"), "bar-alcove")
    # -- cinema: 85 in TV on the high end wall, a loveseat + floor cushions (answers)
    C = r["cinema"]
    add(against("cinema-tv", C, "x1", C[3] - 1.885, "screen", w=1.88, d=0.1, h=1.5, screen_in=85,
                why="85 in TV on the high end wall (2.65 m clear), clear of the door from the lounge"), "cinema")
    add(item("cinema-sofa", None, "sofa_2seat", C[2] - 0.1 - 2.7 - 0.45 + 0.45, C[3] - 0.95, -90, w=1.6,
             d=0.95, h=0.9, why="loveseat for two, 2.5 m from the screen; floor cushions in front (not fixed)"),
        "cinema", views="cinema-tv")
    # -- guest WC
    W = r["guest-wc"]
    add(against("gwc-wc", W, "y1", 9.9, "wc", d=0.55, h=0.4, why="wall-hung pan on the far wall"), "guest-wc")
    add(against("gwc-basin", W, "x0", -22.9, "washbasin", h=0.85, why="basin on the side wall"), "guest-wc")
    # -- dirty kitchen + laundry: gas hob 60 + oven, sink, washer (line drying: answers)
    DK = r["dirty-kitchen"]
    add(against("dk-run", DK, "y1", DK[0], "base_run", w=3.6, d=0.6, h=0.9,
                modules=[("washer", 0.6), ("counter", 0.62), ("sink", 0.8), ("counter", 0.62), ("hob", 0.6),
                         ("counter", 0.36)],
                why="heavy cooking here (answers): gas hob 60 + oven under, sink; washer at the end of the run"),
        "dirty-kitchen")
    add(against("dk-fold", DK, "y0", DK[0] + 0.1, "folding_counter", w=1.5, h=0.9,
                why="folding counter; drying rack and cleaning cupboard beside it"), "dirty-kitchen")
    add(against("dk-clean", DK, "y0", DK[0] + 1.7, "tall_column", w=0.6, d=0.6, h=2.2,
                why="cleaning cupboard (answers: in the dirty kitchen)"), "dirty-kitchen")
    # -- stores
    PP = r["pantry"]
    add(against("pantry-shelves-1", PP, "x0", PP[1], "pantry_shelving", w=PP[3] - PP[1], h=2.2,
                why="shelving on the end wall: the pantry is 1.0 m deep clear, too shallow for a back-wall run with "
                    "914 mm in front"), "pantry")
    add(against("pantry-shelves-2", PP, "x1", PP[1], "pantry_shelving", w=PP[3] - PP[1], h=2.2,
                why="shelving on the other end wall"), "pantry")
    add(against("store-shelves", r["store-ramp"], "y1", r["store-ramp"][0] + 0.1, "store_shelving", w=2.85, h=1.3,
                why="low shelving under the ramp: luggage, seasonal clothes, cushions, tools, bikes (answers)"),
        "store-ramp")

    # ================= ground floor =================
    # -- study: shared homework desk (street window), adult work desk (east wall), gaming sofa + TV (answers)
    S = r["study-game"]
    add(against("study-desk", S, "x0", -26.3, "desk", w=1.8, d=0.7, h=0.75,
                why="shared homework desk for two, under the street window (sill 0.9)"), "study-game")
    add(against("study-adult-desk", S, "y1", 4.6, "desk", w=1.4, d=0.7, h=0.75,
                why="adult work desk (one adult most days) under the high window; plain wall behind for calls"),
        "study-game")
    add(against("study-tv", S, "x1", -26.2, "tv_unit", w=1.6, h=0.5, why="gaming / TV on the bathroom wall"),
        "study-game", screen_in=55)
    add(item("study-sofa", None, "sofa_2seat", 6.827 + 0.45 - 0.45, -25.4, -90, h=0.85,
             why="gaming sofa facing the TV (no sofa bed: answers)"), "study-game", views="study-tv")
    # -- family bath: walk-in shower, WC, basin (a bath does not also fit: answers asked 'if they fit')
    FB = r["family-bath"]
    add(against("fb-shower", FB, "y1", 9.567, "shower_walkin", w=1.63, d=0.9, h=0.1,
                why="walk-in shower between the two east-face columns"), "family-bath")
    add(against("fb-wc", FB, "x0", FB[1] + 0.02, "wc", d=0.55, h=0.4, why="wall-hung WC"), "family-bath")
    add(against("fb-basin", FB, "x0", FB[1] + 0.42, "washbasin", w=0.43, d=0.45, h=0.85,
                why="compact basin beside the WC"),
        "family-bath")
    # -- kids A (two girls): bunk bed, two desks, a 1.5 m wardrobe
    KA = r["kids-a"]
    add(item("ka-bunk", None, "bed_single", KA[0] + 0.45, -25.45, 0, h=1.7,
             why="bunk bed against the west wall (answers)"), "kids-a")
    add(against("ka-desk-1", KA, "y1", 12.62, "desk", w=1.1, d=0.6, h=0.75, why="desk, girl 1"), "kids-a")
    add(against("ka-desk-2", KA, "y1", 13.76, "desk", w=1.1, d=0.6, h=0.75, why="desk, girl 2"), "kids-a")
    add(against("ka-wardrobe", KA, "x1", KA[1] + 0.02, "wardrobe", w=1.5, d=0.6, h=2.2, why="1.5 m wardrobe"),
        "kids-a")
    # -- kids B (boy): 120 bed, desk, 1.5 m wardrobe
    KB = r["kids-b"]
    add(item("kb-bed", None, "bed_small_double", KB[0] + 1.0, -25.3, -90, h=0.5, why="120 x 200, head to the west wall"),
        "kids-b")
    add(against("kb-desk", KB, "y1", 17.05, "desk", w=1.2, d=0.6, h=0.75, why="desk under the window"), "kids-b")
    add(against("kb-wardrobe", KB, "y0", 17.2, "wardrobe", w=1.5 if KB[2] - 17.2 >= 1.5 else KB[2] - 17.2, d=0.6,
                h=2.2, why="wardrobe beside the door"), "kids-b")
    # -- parents: queen bed, head on the dressing wall; vanity at the garden window (answers)
    PB = r["parents-bed"]
    add(item("pb-bed", None, "bed_double", 20.33, PB[1] + 1.0, 0, h=0.5,
             why="queen 160 x 200 (answers), head on the dressing wall, east of the entry; 750 mm both sides and "
                 "the foot"), "parents-bed")
    add(item("pb-bedside", None, "bedside_table", 20.33 + 0.8 + 0.25, PB[1] + 0.2, 0, h=0.55,
             why="bedside in zone a; the other side has a wall shelf so the way in from the entry stays clear"),
        "parents-bed")
    add(against("pb-vanity", PB, "x1", -25.3, "desk", w=1.0, d=0.4, h=0.75,
                why="vanity / dressing table at the garden window (answers), clear of the bed zone"), "parents-bed")
    # -- dressing: hanging on both long walls
    PD = r["parents-dressing"]
    add(against("pd-hang-1", PD, "y1", PD[0] + 0.05, "wardrobe", w=VP.DRESSING_DOOR_X - 0.5 - PD[0] - 0.05, d=0.6,
                h=2.2,
                why="hanging along the bedroom wall, up to the bedroom door"), "parents-dressing")
    add(against("pd-hang-2", r["parents-dressing-ext"], "y0", r["parents-dressing-ext"][0] + 0.05, "wardrobe",
                w=21.2 - r["parents-dressing-ext"][0] - 0.05,
                d=0.6, h=2.2, why="hanging along the ensuite wall, up to the ensuite door"), "parents-dressing-ext")
    # -- ensuite: bath, shower, double basin; WC on the south (garden) wall (client)
    PE = r["parents-ensuite"]
    add(against("pe-wc", PE, "x1", PE[1] + 0.86, "wc", d=0.5, h=0.4, why="WC on the south wall (client)"),
        "parents-ensuite")
    add(against("pe-bath", PE, "y0", PE[0] + 0.05, "bath", h=0.55,
                why="bath with a shower over it: a separate shower does not also fit (answers asked for both)"),
        "parents-ensuite")
    add(against("pe-basin", PE, "x0", PE[3] - 0.65, "washbasin", h=0.85,
                why="single basin: with the ensuite 0.21 m shorter for the dressing, a double basin zone reaches "
                    "the bath"), "parents-ensuite")
    for it in items:
        it["level"] = lay["rooms"][it["room"]]["level"]
    return items


# ---- checks -------------------------------------------------------------------------------------------------------
def _cluster(lay, rid):
    """The room plus every room joined to it without a wall (open plan, alcoves), transitively."""
    rooms = lay["rooms"]
    seen, todo = {rid}, [rid]
    while todo:
        a = todo.pop()
        for b, rb in rooms.items():
            if b in seen or rb["level"] != rooms[a]["level"]:
                continue
            joined = (RS.is_open(rooms[a]) and RS.is_open(rb)) or rb.get("part_of") == a or rooms[a].get("part_of") == b
            if joined and V.shared_edge(rooms[a]["rect"], rb["rect"]) > 0.05:
                seen.add(b)
                todo.append(b)
    return seen


def _inside(rect, rects, step=0.05):
    xs = np.arange(rect[0] + step / 2, rect[2], step)
    ys = np.arange(rect[1] + step / 2, rect[3], step)
    if not len(xs) or not len(ys):
        return True
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    ok = np.zeros(X.shape, bool)
    for a, b, c, d in rects:
        ok |= (X >= a - 1e-6) & (X <= c + 1e-6) & (Y >= b - 1e-6) & (Y <= d + 1e-6)
    return bool(ok.all())


def _door_axis(d):
    """"h" for a door in a wall along x, "v" along y: its span when the spec gives one, else by whether it sits on
    the building's long faces (a missing span once defaulted to "h", so the cinema door was never cut from its
    wall)."""
    return (d.get("span") or [None])[0] or ("h" if any(abs(d["y"] - e) < 0.06 for e in (V.YE, V.YP)) else "v")


def _walls(sp, level):
    """The built walls of a storey as rectangles (the spec's centre lines and thicknesses; external walls already sit
    inside the outer face), each cut at its doors. Pieces and their zones must not overlap them."""
    gaps = []
    for d in sp["doors"]:
        if d["level"] == level:
            ax = _door_axis(d)
            gaps.append(((d["x"] - d["width"] / 2, d["y"] - 0.2, d["x"] + d["width"] / 2, d["y"] + 0.2), "h") if ax == "h"
                        else ((d["x"] - 0.2, d["y"] - d["width"] / 2, d["x"] + 0.2, d["y"] + d["width"] / 2), "v"))
    out = []
    for w in sp["walls"]:
        if w["level"] != level:
            continue
        t = w["thickness"] / 2
        horiz = abs(w["y0"] - w["y1"]) < 1e-6
        c = w["y0"] if horiz else w["x0"]
        a, b = sorted((w["x0"], w["x1"])) if horiz else sorted((w["y0"], w["y1"]))
        cuts = sorted(((g[0], g[2]) if horiz else (g[1], g[3])) for g, gax in gaps
                      if gax == ("h" if horiz else "v") and (g[1] <= c <= g[3] if horiz else g[0] <= c <= g[2]))
        pos = a
        pieces = []
        for g0, g1 in cuts:
            if g1 > pos and g0 < b:
                if g0 > pos:
                    pieces.append((pos, g0))
                pos = max(pos, g1)
        if pos < b:
            pieces.append((pos, b))
        out += [(p0, c - t, p1, c + t) if horiz else (c - t, p0, c + t, p1) for p0, p1 in pieces]
    return out


def _columns():
    return [tuple(v / 1000 for v in c) for c in V.E.COLUMNS]


DOOR_TYPES = {
    # "into:<room>": swings into that room only (the other side keeps no swing zone)
    "lounge-nook/pantry": "into:lounge-nook",       # the pantry is 1.0 m deep with its shelving: the door opens out
    # door (rooms joined by "/") -> "pocket": a sliding door into the wall, so it sweeps no floor. Parents: the king
    # bed's 750 mm zone and its bedside table sit where a swing would go; the wall beside the door has 1.18 m for
    # the pocket (Phase 2 builds it as a sliding door).
    "corridor/parents-entry": "pocket",
    "parents-bed/parents-dressing": "into:parents-dressing",
}


def _door_zones(sp, lay, level):
    """Rects that must stay clear at each door: a swing square (width x width) on each side for hinged doors, 0.9 m
    inside for sliding / garden doors, nothing for pocket doors (DOOR_TYPES)."""
    out = []
    for d in sp["doors"]:
        if d["level"] != level or DOOR_TYPES.get("/".join(d.get("rooms") or [])) == "pocket":
            continue
        w = d["width"]
        horiz = abs(d["y"] - round(d["y"], 3)) < 1e-9 and any(abs(d["y"] - e[1]) < 0.06 for e in
                                                                [(0, V.YE), (0, V.YP)]) or d.get("span", [None])[0] == "h"
        span = d.get("span")
        axis = span[0] if span else ("h" if horiz else "v")
        depth = 0.9 if (d.get("garden") or d.get("sliding")) else w
        into = (DOOR_TYPES.get("/".join(d.get("rooms") or [])) or "")
        into = into[5:] if into.startswith("into:") else None
        for s in (-1, 1):
            if axis == "h":
                z = (d["x"] - w / 2, d["y"], d["x"] + w / 2, d["y"] + s * depth)
            else:
                z = (d["x"], d["y"] - w / 2, d["x"] + s * depth, d["y"] + w / 2)
            z = (min(z[0], z[2]), min(z[1], z[3]), max(z[0], z[2]), max(z[1], z[3]))
            mid = ((z[0] + z[2]) / 2, (z[1] + z[3]) / 2)
            if RS._room_at(lay, level, *mid) and (into is None or RS._room_at(lay, level, *mid) == into):
                out.append({"door": "/".join(d.get("rooms") or []), "rect": z, "garden": bool(d.get("garden"))})
    return out


def _door_approaches(sp, lay, level):
    """The floor a body must reach at every door, whatever its type: a strip 0.3 m deep and the door's width on
    each side. Route nodes come from these, not from the swing zones, which a pocket door (no swing) or a door
    swinging one way lacks on a side: the parents' cluster lost its entry node that way and started its route from
    a piece of furniture."""
    out = []
    for d in sp["doors"]:
        if d["level"] != level:
            continue
        w = d["width"]
        axis = _door_axis(d)
        for s_ in (-1, 1):
            if axis == "h":
                z = (d["x"] - w / 2, d["y"], d["x"] + w / 2, d["y"] + s_ * 0.3)
            else:
                z = (d["x"], d["y"] - w / 2, d["x"] + s_ * 0.3, d["y"] + w / 2)
            z = (min(z[0], z[2]), min(z[1], z[3]), max(z[0], z[2]), max(z[1], z[3]))
            if RS._room_at(lay, level, (z[0] + z[2]) / 2, (z[1] + z[3]) / 2):
                out.append({"door": "/".join(d.get("rooms") or []), "rect": z})
    return out


EXTENDED_TABLE = 2.8    # the dining table opened for 10 (ASSUMED leaf length: 10 x 600 mm place settings, less ends)


def check(items=None, lay=None, _extended=False):
    """Every furniture check; returns {check: {"status", "problems": [...], "measured": {...}}}. Also re-runs them
    all with the dining table extended (key "extended_table")."""
    lay = lay or R.design("D1")
    items = items or layout(lay)
    sp = RS.build(lay)
    out = {}
    probs = collections.defaultdict(list)
    meas = collections.defaultdict(dict)
    cols = _columns()
    by_level = collections.defaultdict(list)
    for it in items:
        by_level[it["level"]].append(it)
    walls = {lv: _walls(sp, lv) for lv in ("B", "GF")}
    for it in items:
        fp = footprint(it)
        cl = _cluster(lay, it["room"])
        rects = [lay["rooms"][c]["rect"] for c in cl]
        cols = _columns() + walls[it["level"]]         # walls and columns alike are obstacles
        if not _inside(fp, rects) or any(_ov(fp, w) for w in walls[it["level"]]):
            probs["inside_room"].append("%s leaves %s" % (it["id"], it["room"]))
        for c in cols:
            if _ov(fp, c):
                probs["columns"].append("%s overlaps a column at x %.2f" % (it["id"], c[0]))
        t = cat.get(it["type"])
        zones = [(s, t.clearance[s] / 1000) for s in SIDES if t.clearance[s] > 0]
        if t.clearance_any:
            sides, dep = t.clearance_any
            best = None
            for s in sides:
                z = side_zone(it, s, dep / 1000)
                bad = [o["id"] for o in by_level[it["level"]] if o is not it and _ov(z, footprint(o))] + \
                      (["walls"] if not _inside(z, rects) else [])
                if not bad:
                    best = s
            meas["clearances"][it["id"]] = "one side %d mm: %s" % (dep, best or "NONE clear")
            if best is None:
                probs["clearances"].append("%s: no side keeps %d mm clear" % (it["id"], dep))
        for s, dep in zones:
            z = side_zone(it, s, dep)
            hit = [o["id"] for o in by_level[it["level"]] if o is not it and _ov(z, footprint(o))
                   and not (it["type"].startswith("bed") and s in ("left", "right") and o["type"] == "bedside_table"
                            and _inside(footprint(o), [head_zone(it, ZONE_A)]))]
            wall = not _inside(z, rects)
            colh = [c for c in cols if _ov(z, c)]
            if hit or wall or colh:
                probs["clearances"].append("%s %s %d mm: %s" % (it["id"], s, round(dep * 1000),
                                                                ", ".join(hit + (["a wall"] if wall else []) +
                                                                          (["a column"] if colh else []))))
    for lv, its in by_level.items():
        for i, a in enumerate(its):
            for b in its[i + 1:]:
                if _ov(footprint(a), footprint(b)):
                    probs["overlap"].append("%s / %s" % (a["id"], b["id"]))
        for z in _door_zones(sp, lay, lv):
            for it in its:
                if _ov(z["rect"], footprint(it)):
                    probs["doors"].append("%s blocks the door %s" % (it["id"], z["door"]))
        wl = _walls(sp, lv)
        for d in sp["doors"]:                       # an opening must not run into a wall across it (the dressing
            if d["level"] != lv:                    # door at 22.10 ran 0.15 m into the south wall)
                continue
            h_ = _door_axis(d) == "h"
            o = (d["x"] - d["width"] / 2, d["y"] - 0.01, d["x"] + d["width"] / 2, d["y"] + 0.01) if h_ else \
                (d["x"] - 0.01, d["y"] - d["width"] / 2, d["x"] + 0.01, d["y"] + d["width"] / 2)
            for q in wl:
                if _ov(o, q):
                    lost = (min(o[2], q[2]) - max(o[0], q[0])) if h_ else (min(o[3], q[3]) - max(o[1], q[1]))
                    probs["doors"].append("door %s runs %d mm into a wall" % ("/".join(d.get("rooms") or []),
                                                                            round(lost * 1000)))
        for w in sp["windows"]:
            if w["level"] != lv:
                continue
            ax = w.get("span", ["h"])[0]
            half = w["width"] / 2
            z = (w["x"] - half, w["y"] - 0.3, w["x"] + half, w["y"] + 0.3) if ax == "h" else \
                (w["x"] - 0.3, w["y"] - half, w["x"] + 0.3, w["y"] + half)
            for it in its:
                if _ov(z, footprint(it)) and it["h"] > w["sill"] + 0.05:
                    probs["windows"].append("%s (%.2f m high) stands in front of the %s window (sill %.2f)"
                                            % (it["id"], it["h"], w.get("room"), w["sill"]))
    # kitchen landing areas and dishwasher distance (NKBA 2nd ed.)
    need = {"sink": (0.610, 0.457, "cards nkba-sink-landing-610/457"),
            "hob": (0.381, 0.305, "cards nkba-hob-landing-381/305"),
            "range": (0.381, 0.305, "cards nkba-hob-landing-381/305")}
    landing = ("counter", "dw")
    for it in items:
        mods = module_spans(it)
        if mods and abs(sum(w for _, w in it["modules"]) - it["w"]) > 1e-3:   # the dirty-kitchen run's modules
            probs["kitchen"].append("%s: modules add up to %.2f m, the run is %.2f m"   # once overran it by 40 mm
                                    % (it["id"], sum(w for _, w in it["modules"]), it["w"]))
        for i, (kind, a, b) in enumerate(mods):
            if kind in need:
                left = right = 0.0
                j = i - 1
                while j >= 0 and mods[j][0] in landing:
                    left += mods[j][2] - mods[j][1]
                    j -= 1
                j = i + 1
                while j < len(mods) and mods[j][0] in landing:
                    right += mods[j][2] - mods[j][1]
                    j += 1
                big, small, card = need[kind]
                ok = max(left, right) >= big - 1e-6 and min(left, right) >= small - 1e-6
                meas["kitchen"]["%s %s" % (it["id"], kind)] = "landing %.2f / %.2f m (need %.3f / %.3f)" % (
                    left, right, big, small)
                if not ok:
                    probs["kitchen"].append("%s %s landing %.2f / %.2f m, need %.3f and %.3f (%s)"
                                            % (it["id"], kind, left, right, big, small, card))
            if kind == "fridge":
                adj = [m for m in (mods[i - 1] if i else None, mods[i + 1] if i + 1 < len(mods) else None)
                       if m and m[0] == "counter" and m[2] - m[1] >= 0.381 - 1e-6]
                if not adj:
                    probs["kitchen"].append("%s fridge has no 381 mm landing beside it (card nkba-fridge-landing-381)"
                                            % it["id"])
        sinks = [m for m in mods if m[0] == "sink"]
        dws = [m for m in mods if m[0] == "dw"]
        for dw in dws:
            gap = min(max(0.0, max(s[1], dw[1]) - min(s[2], dw[2])) for s in sinks) if sinks else 99
            meas["kitchen"]["%s dishwasher to sink" % it["id"]] = "%.2f m (max 0.914)" % gap
            if gap > 0.914:
                probs["kitchen"].append("%s dishwasher %.2f m from the sink (card nkba-dishwasher-to-sink-max)"
                                        % (it["id"], gap))
    # viewing distance (cards mitton-tv-uhd-min / -max: 1.0-1.5 x the screen size)
    ids = {it["id"]: it for it in items}
    for it in items:
        scr = ids.get(it.get("views"))
        if not scr:
            continue
        diag = scr["screen_in"] * 0.0254
        fx, fy = DIRS[scr["rot"]]["front"]
        sfp = footprint(scr)
        face = sfp[3] if fy > 0 else sfp[1] if fy < 0 else sfp[2] if fx > 0 else sfp[0]
        dx, dy = DIRS[it["rot"]]["front"]
        ifp = footprint(it)
        seat_front = ifp[3] if dy > 0 else ifp[1] if dy < 0 else ifp[2] if dx > 0 else ifp[0]
        eye = seat_front - (dy or dx) * SEAT_EYE
        dist = abs(eye - face)
        ratio = dist / diag
        meas["viewing"][it["id"]] = "%.2f m from a %d in screen = %.2f x (1.0-1.5)" % (dist, scr["screen_in"], ratio)
        if not (1.0 - 1e-6 <= ratio <= 1.5 + 1e-6):
            probs["viewing"].append("%s: %.2f m from the %d in screen (%.2f x; UHD 1.0-1.5 x)"
                                    % (it["id"], dist, scr["screen_in"], ratio))
    # furnished routes
    for lv in by_level:
        for p, m in route_problems(lay, sp, by_level[lv], lv):
            probs["routes"].append(p)
            meas["routes"].update(m)
    for k in ("inside_room", "columns", "overlap", "clearances", "doors", "windows", "kitchen", "viewing", "routes"):
        out[k] = {"status": "fail" if probs[k] else "pass", "problems": probs[k], "measured": dict(meas[k])}
    if not _extended:
        # the brief's other configuration: the dining table extended for 10 (client brief D-TABLE: 1.8 m for 6)
        ext = [dict(it, w=EXTENDED_TABLE) if it["type"] == "dining_6x" else it for it in items]
        if ext != items:
            r2 = check(ext, lay, _extended=True)
            bad = ["%s: %s" % (k, p) for k, v in r2.items() for p in v["problems"]]
            out["extended_table"] = {"status": "fail" if bad else "pass", "problems": bad,
                                     "measured": {"table": "%.1f m long, every check above re-run" % EXTENDED_TABLE}}
    return out


SEATS = {"sofa_2seat", "sofa_3seat", "sofa_4seat", "sofa_bed", "armchair", "recliner"}


def _middle(rect):
    """The rect with a quarter of its long side (at most 0.3 m) trimmed off each end."""
    x0, y0, x1, y1 = rect
    if x1 - x0 >= y1 - y0:
        t = min(0.3, (x1 - x0) / 4)
        return (x0 + t, y0, x1 - t, y1)
    t = min(0.3, (y1 - y0) / 4)
    return (x0, y0 + t, x1, y1 - t)


def _outside(rects, margin):
    """The part of the rooms' bounding box (grown by margin) not covered by the rooms, as rectangles: the rooms'
    edges cut the box into a grid; uncovered cells are merged along y within each column."""
    x0 = min(q[0] for q in rects) - margin; y0 = min(q[1] for q in rects) - margin
    x1 = max(q[2] for q in rects) + margin; y1 = max(q[3] for q in rects) + margin
    xs = sorted({x0, x1} | {q[0] for q in rects} | {q[2] for q in rects})
    ys = sorted({y0, y1} | {q[1] for q in rects} | {q[3] for q in rects})
    out = []
    for xa, xb in zip(xs, xs[1:]):
        run = None
        for ya, yb in zip(ys, ys[1:]):
            mx, my = (xa + xb) / 2, (ya + yb) / 2
            cov = any(q[0] <= mx <= q[2] and q[1] <= my <= q[3] for q in rects)
            if not cov:
                run = (run[0], yb) if run else (ya, yb)
            elif run:
                out.append((xa, run[0], xb, run[1])); run = None
        if run:
            out.append((xa, run[0], xb, run[1]))
    return out


TRACE = None   # set to {} to keep each cluster's raster


def route_problems(lay, sp, items, level, cell=0.02):
    """In each open cluster of rooms, a 914 mm body (card mitton-path-of-travel-min) must get from every door of
    the cluster to every other door and to every piece's working side. Furniture over 0.3 m and the columns are
    obstacles; walls are the cluster's own edges. Returns [(problem, measured)]."""
    out = []
    done = set()
    zones = _door_approaches(sp, lay, level)
    for rid, r in lay["rooms"].items():
        if r["level"] != level or rid in done:
            continue
        cl = _cluster(lay, rid)
        done |= cl
        rects = [lay["rooms"][c]["rect"] for c in cl]
        x0 = min(q[0] for q in rects); y0 = min(q[1] for q in rects)
        x1 = max(q[2] for q in rects); y1 = max(q[3] for q in rects)
        nx, ny = int((x1 - x0) / cell) + 1, int((y1 - y0) / cell) + 1
        gx, gy = x0 + (np.arange(nx) + 0.5) * cell, y0 + (np.arange(ny) + 0.5) * cell
        X, Y = np.meshgrid(gx, gy, indexing="ij")
        free = np.zeros((nx, ny), bool)
        for a, b, c, d in rects:                  # half-open, so a cell centred on a shared edge is not lost
            free |= (X >= a - 1e-9) & (X < c - 1e-9) & (Y >= b - 1e-9) & (Y < d - 1e-9)
        walls_l = _walls(sp, level)
        obst = [footprint(it) for it in items if it["room"] in cl and it["h"] >= 0.3] + _columns() + walls_l
        # not floor: the basement flight (you stand at its foot, not on it), the GF stair opening and any voids
        obst += [lay["rooms"][c]["rect"] for c in cl if lay["rooms"][c]["occupancy"] == "stair" and level == "B"]
        if level == "GF":
            obst += ([sp["gf_opening"]] if sp.get("gf_opening") else []) + sp.get("gf_voids", [])
        for a, b, c, d in obst:
            free &= ~((X > a) & (X < c) & (Y > b) & (Y < d))
        bedroom = all(lay["rooms"][c]["occupancy"] == "bedroom" for c in cl)
        width = min(BODY, BEDROOM_ROUTE) if bedroom else BODY
        # The body is a DISC of the path width: a path's width is measured across the direction of travel, so a
        # disc is what a 914 mm path admits, on the straight and round a corner alike. (A square body of the same
        # side, used before, failed corners the path itself turns: its corner sweeps outside the path width.)
        # Clearance is the exact distance from a cell centre to each obstacle rectangle, and to the cluster's own
        # edge (open joins to other clusters), which is the outside of its rooms cut into rectangles.
        clear = np.full((nx, ny), np.inf)
        for a, b, c, d in obst + _outside(rects, width):
            if c < x0 - width or a > x1 + width or d < y0 - width or b > y1 + width:
                continue
            dx = np.maximum(np.maximum(a - X, X - c), 0.0)
            dy = np.maximum(np.maximum(b - Y, Y - d), 0.0)
            clear = np.minimum(clear, np.hypot(dx, dy))
        ok = free & (clear >= width / 2 - 1e-9)

        def touching(rect):
            # a real overlap (up to 0.1 m each way), not a sliver: a body grazing a zone's edge is not in it
            ex = min(0.1, (rect[2] - rect[0]) / 2 - 1e-6)
            ey = min(0.1, (rect[3] - rect[1]) / 2 - 1e-6)
            dx = np.maximum(np.maximum(rect[0] + ex - X, X - (rect[2] - ex)), 0.0)
            dy = np.maximum(np.maximum(rect[1] + ey - Y, Y - (rect[3] - ey)), 0.0)
            return ok & (np.hypot(dx, dy) < width / 2)
        nodes = []
        for z in zones:
            zc = ((z["rect"][0] + z["rect"][2]) / 2, (z["rect"][1] + z["rect"][3]) / 2)
            if any(q[0] <= zc[0] <= q[2] and q[1] <= zc[1] <= q[3] for q in rects):
                nodes.append(("door " + z["door"], [z["rect"]]))
        for sid in cl:                                   # stair arrivals: the floor in front of each stair end
            srm = lay["rooms"][sid]
            for end in srm.get("ends") or []:
                ax_, c, a, b = end
                x0s, y0s, x1s, y1s = srm["rect"]
                if ax_ == "v":
                    z = (c, a, c + 0.3, b) if abs(c - x1s) < 1e-6 else (c - 0.3, a, c, b)
                else:
                    z = (a, c, b, c + 0.3) if abs(c - y1s) < 1e-6 else (a, c - 0.3, b, c)
                nodes.append(("stair end of " + sid, [z]))
        for rid in cl:                                   # the principal bedroom's windows (AD M Diagram 2.4 note 1)
            if rid == PRINCIPAL_BEDROOM:                 # keyed on the room, not the bed type (a queen bed hid it)
                for w in sp["windows"]:
                    if w["level"] == level and w.get("room") == rid:
                        half = w["width"] / 2
                        ax_ = (w.get("span") or ["h"])[0]
                        rr = lay["rooms"][rid]["rect"]
                        # the strip starts at the wall's INNER face (a 0.2 m external wall swallowed a strip drawn
                        # from its line)
                        wr = next((q for q in walls_l if q[0] - 1e-6 <= w["x"] <= q[2] + 1e-6
                                   and q[1] - 1e-6 <= w["y"] <= q[3] + 1e-6), None)
                        if ax_ == "h":
                            hi = abs(w["y"] - rr[3]) < 0.06
                            y = (wr[1] if hi else wr[3]) if wr else w["y"]
                            z = (w["x"] - half, y - 0.3, w["x"] + half, y) if hi else \
                                (w["x"] - half, y, w["x"] + half, y + 0.3)
                        else:
                            hi = abs(w["x"] - rr[2]) < 0.06
                            x = (wr[0] if hi else wr[2]) if wr else w["x"]
                            z = (x - 0.3, w["y"] - half, x, w["y"] + half) if hi else \
                                (x, w["y"] - half, x + 0.3, w["y"] + half)
                        nodes.append(("window of " + rid, [_middle(z)]))
        for it in items:
            if it["room"] not in cl:
                continue
            t = cat.get(it["type"])
            # a side is reached along its middle, not at a corner (a body grazing a bed's foot corner is not at
            # the bedside): trim a quarter of the side, at most 0.3 m, off each end
            if t.clearance_any:                          # a single bed is reached on either long side
                nodes.append((it["id"], [_middle(side_zone(it, sd, 0.3)) for sd in t.clearance_any[0]]))
            elif it["type"] in SEATS:                    # a seat facing a table is reached from its front or a side
                nodes.append((it["id"], [_middle(side_zone(it, sd, 0.3)) for sd in ("front", "left", "right")]))
            elif it["type"] == "coffee_table":          # a table among seats is reached from any side
                nodes.append((it["id"], [_middle(side_zone(it, sd, 0.3)) for sd in SIDES]))
            elif t.clearance["front"] > 0:
                nodes.append((it["id"], [_middle(side_zone(it, "front", 0.3))]))
        if len(nodes) < 2:
            continue
        nodes.sort(key=lambda n: 0 if n[0].startswith("stair end") else 1)   # start at the stair where there is one
        seen = np.zeros(ok.shape, bool)
        start = touching(nodes[0][1][0])
        q = collections.deque(zip(*np.nonzero(start)))
        seen[start] = True
        while q:
            i, j = q.popleft()
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = i + di, j + dj
                if 0 <= a < ok.shape[0] and 0 <= b < ok.shape[1] and ok[a, b] and not seen[a, b]:
                    seen[a, b] = True
                    q.append((a, b))
        if TRACE is not None:                            # for plotting a cluster when a route fails
            TRACE["+".join(sorted(cl))] = dict(ok=ok, seen=seen, nodes=nodes, origin=(gx[0], gy[0]), cell=cell,
                                               body=width, obst=obst)
        for name, rs_ in nodes[1:]:
            if not any((touching(rect) & seen).any() for rect in rs_):
                out.append(("%s (%s): not reached by a %d mm path from %s" % (name, "+".join(sorted(cl)),
                                                                                 round(width * 1000), nodes[0][0]),
                            {}))
    return out
