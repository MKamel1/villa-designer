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
from . import villa_r11 as R

SIDES = ("front", "back", "left", "right")
DIRS = {0: {"front": (0, 1), "back": (0, -1), "right": (1, 0), "left": (-1, 0)},
        180: {"front": (0, -1), "back": (0, 1), "right": (-1, 0), "left": (1, 0)},
        -90: {"front": (1, 0), "back": (-1, 0), "right": (0, -1), "left": (0, 1)},
        90: {"front": (-1, 0), "back": (1, 0), "right": (0, 1), "left": (0, -1)}}
BODY = 0.914            # card mitton-path-of-travel-min: paths of travel at least 36 in (914 mm)
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


def _ov(a, b, tol=1e-6):
    return min(a[2], b[2]) - max(a[0], b[0]) > tol and min(a[3], b[3]) - max(a[1], b[1]) > tol


# ---- the D1 layout ----------------------------------------------------------------------------------------------
def layout(lay=None):
    lay = lay or R.design("D1")
    r = {k: v["rect"] for k, v in lay["rooms"].items()}
    YE, YP = V.YE, V.YP
    items = []

    def add(it, room, **kw):
        it.update(room=room, **kw)
        items.append(it)

    # -- basement: street lounge (family TV), with the alcove under the stair landing left clear to the pantry
    L = r["lounge"]
    add(against("lounge-tv", L, "y1", 5.0, "tv_unit", w=2.0, h=0.5,
                why="TV wall between the NE column and the column at x 7.0 (east face); 75 in screen"), "lounge",
        screen_in=75)
    add(item("lounge-sofa", None, "sofa_4seat", 6.0, -26.847, 0, h=0.85,
             why="facing the TV, back to the stair balustrade; leaves 0.98 m at its street end to the larder/pantry"),
        "lounge", views="lounge-tv")
    add(item("lounge-coffee", None, "coffee_table", 6.0, -25.61, 0, w=1.2, d=0.6, h=0.4,
             why="457 mm from the sofa (card mitton-sofa-coffee-table-457)"), "lounge")
    add(item("lounge-armchair", None, "armchair", 8.3, -26.2, -90, h=0.85,
             why="fifth seat, facing the family corner and the kitchen; turns to the TV"), "lounge")
    # -- kitchen (bay 4-5): tall wall on the party side, sink run on the east face, island with the hob and 4 stools
    K, KI = r["kitchen"], r["kitchen-island"]
    add(against("k-tall", KI, "y0", 11.197, "base_run", w=2.85, d=0.6, h=2.3,
                modules=[("counter", 0.45), ("fridge", 0.6), ("freezer", 0.6), ("oven", 0.6), ("coffee", 0.6)],
                why="panel-ready columns (fridge, freezer, oven + combi, coffee); 450 counter beside the fridge "
                    "(card nkba-fridge-landing-381)"), "kitchen-island")
    add(against("k-run", K, "y1", 11.537, "base_run", w=2.463, d=0.6, h=0.9,
                modules=[("counter", 0.5), ("sink", 0.9), ("dw", 0.6), ("counter", 0.463)],
                why="sink under the east wall between column 4 and the dirty-kitchen door; dishwasher beside the sink"),
        "kitchen")
    add(item("k-island", None, "island", 12.9, -26.16, 0, w=2.5, d=1.2, h=0.92,
             modules=[("counter", 0.8), ("hob", 0.9), ("counter", 0.8)], stools=4,
             why="hob side faces the sink run (1.37 m work aisle); 4 stools on the party side, 610 mm each (card "
                 "nkba-seating-width-610), with 1.31 m behind them to walk past to the tall wall (card "
                 "nkba-seating-walk-past-1118)"), "kitchen")
    # -- dining (bay 5-6) and its party side
    D, DS = r["dining"], r["dining-side"]
    add(item("dining-table", None, "dining_6x", 16.6, -25.9, 0, h=0.75, chairs=6,
             why="1.8 x 0.9 for 6, extends to 2.8 m for 10; 965 mm passage both long sides"), "dining")
    add(against("dining-sideboard", DS, "y0", 16.2, "sideboard", w=1.9, h=0.8,
                why="serving sideboard on the party wall"), "dining-side")
    # -- garden living + library alcove
    G, A = r["living"], r["bar-alcove"]
    add(item("living-sofa", None, "sofa_3seat", 19.45, -26.6, -90, h=0.85,
             why="faces the rear garden doors; back to the dining (1.0 m behind it)"), "living")
    add(item("living-coffee", None, "coffee_table", 20.657, -26.6, -90, w=1.1, d=0.6, h=0.4,
             why="457 mm from the sofa"), "living")
    add(item("living-chair-1", None, "armchair", 20.657, -28.2, 0, h=0.85, why="conversation pair across the table"),
        "living")
    add(item("living-chair-2", None, "armchair", 20.657, -24.95, 180, h=0.85,
             why="keeps 1.1 m clear to the east garden door"), "living")
    add(against("alcove-books", A, "y0", 18.2, "bookcase", w=3.8, d=0.35, h=2.2,
                why="library wall along the back of the rear share"), "bar-alcove")
    add(against("alcove-bench", A, "x1", -29.816, "window_bench", w=0.95, d=0.5, h=0.45,
                why="reading seat at the garden window"), "bar-alcove")
    # -- cinema under the ramp: screen on the high end wall (x 9.23, 2.65 m clear; the store door is on the low
    #    wall), a row of three recliners toward the low end
    C = r["cinema"]
    add(against("cinema-screen", C, "x1", -22.096 - 1.107, "screen", h=2.0, screen_in=100,
                why="100 in screen on the high end wall (2.65 m clear); the entrance from the lounge is beside it"),
        "cinema")
    for i, yy in enumerate((-21.951, -21.051)):
        add(item("cinema-seat-%d" % (i + 1), None, "recliner", 5.875, yy, -90, h=1.0,
                 why="two recliners and a 1.19 m aisle to the store under the ramp (three would close it: 2.7 m of "
                     "seats in a 2.99 m room)"), "cinema", views="cinema-screen")
    # -- guest WC
    W = r["guest-wc"]
    add(against("gwc-wc", W, "y1", 9.9, "wc", h=0.4, why="pan on the far wall, 1.1 m zone toward the door"), "guest-wc")
    add(against("gwc-basin", W, "x0", -22.9, "washbasin", h=0.85, why="basin on the side wall"), "guest-wc")
    # -- dirty kitchen + laundry
    DK = r["dirty-kitchen"]
    add(against("dk-run", DK, "y1", 11.2, "base_run", w=3.82, d=0.6, h=0.9,
                modules=[("counter", 0.5), ("sink", 0.8), ("dw", 0.6), ("counter", 0.4), ("range", 0.9),
                         ("counter", 0.62)],
                why="gas range, sink and dishwasher on the fence-side wall (NKBA landing areas)"), "dirty-kitchen")
    add(against("dk-laundry", DK, "y0", 11.2, "washer_dryer", h=1.8, why="stacked washer + dryer"), "dirty-kitchen")
    add(against("dk-fold", DK, "y0", 11.9, "folding_counter", h=0.9, why="folding / ironing counter"), "dirty-kitchen")
    # -- stores
    add(against("pantry-shelves", r["pantry"], "y0", 3.7, "pantry_shelving", w=3.1, h=2.2, why="shelving on the back "
                "wall, 300 deep so 914 mm stays clear"), "pantry")
    add(against("store-shelves", r["store-ramp"], "y1", 0.0, "store_shelving", w=2.9, h=1.3,
                why="low shelving under the ramp (1.45-2.0 m clear)"), "store-ramp")

    # -- GF: study / game room
    S = r["study-game"]
    add(against("study-desk", S, "x0", -26.28, "desk", w=2.0, d=0.7, h=0.75,
                why="shared homework desk for two, under the street window (sill 0.9)"), "study-game")
    add(against("study-tv", S, "y1", 5.3, "tv_unit", w=1.7, h=0.5, why="gaming / TV under the high window"),
        "study-game", screen_in=55)
    add(item("study-sofabed", None, "sofa_bed", 6.25, -25.8, 0, h=0.85,
             why="sofa bed facing the TV, back to the stair gallery"), "study-game", views="study-tv")
    # -- family bath
    FB = r["family-bath"]
    add(against("fb-shower", FB, "y1", 9.567, "shower_walkin", w=1.63, d=0.9, h=0.1,
                why="walk-in shower tray between the two east-face columns (glass screen; the high window over it)"),
        "family-bath")
    add(against("fb-wc", FB, "x0", -25.66, "wc", h=0.4, why="WC on the west wall, clear of the shower zone"),
        "family-bath")
    add(against("fb-basin", FB, "x1", -26.3, "washbasin", h=0.85,
                why="single basin: a double basin does not fit beside the WC and shower with their AD M zones"),
        "family-bath")
    # -- kids A (two children: two singles, one desk, one wardrobe)
    KA = r["kids-a"]
    add(item("ka-bed-1", None, "bed_single", 12.54, -24.041, -90, h=0.5,
             why="under the window, head to the west wall"), "kids-a")
    add(item("ka-bed-2", None, "bed_single", 12.54, -25.9, -90, h=0.5,
             why="parallel, 0.96 m between the beds (card ukadm-bed-single-750; a 914 mm path reaches it)"), "kids-a")
    add(against("ka-desk", KA, "y1", 13.65, "desk", w=1.2, d=0.6, h=0.75, why="one desk under the window"), "kids-a")
    add(against("ka-wardrobe", KA, "y0", 13.72, "wardrobe", w=1.2, d=0.55, h=2.2,
                why="wardrobe beside the door"), "kids-a")
    # -- kids B (one child)
    KB = r["kids-b"]
    add(item("kb-bed", None, "bed_small_double", 15.952, -25.4, -90, h=0.5,
             why="120 x 200, head to the west wall"), "kids-b")
    add(against("kb-desk", KB, "y1", 17.0, "desk", w=1.2, d=0.6, h=0.75, why="desk under the window"), "kids-b")
    add(against("kb-wardrobe", KB, "y0", 17.2, "wardrobe", w=1.2, d=0.55, h=2.2, why="wardrobe beside the door"),
        "kids-b")
    # -- parents
    PB = r["parents-bed"]
    add(item("pb-bed", None, "bed_king", 19.427, -25.61, -90, h=0.5,
             why="king, head to the west wall; 750 mm both sides and the foot (principal bedroom), clear of the "
                 "column at the head"), "parents-bed")
    add(item("pb-bedside-1", None, "bedside_table", 18.627, -26.76, -90, h=0.55,
             why="bedside in zone 'a' (card ukadm-bedside-zone-a-600)"), "parents-bed")
    add(item("pb-bedside-2", None, "bedside_table", 18.627, -24.46, -90, h=0.55,
             why="bedside in zone 'a' (card ukadm-bedside-zone-a-600)"), "parents-bed")
    add(item("pb-chair", None, "armchair", 22.02, -26.8, 90, h=0.85, why="reading chair by the garden window"),
        "parents-bed")
    add(against("pd-shelves", r["parents-dressing"], "y0", 19.6, "bookcase", w=0.85, d=0.35, h=2.2,
                why="dressing: 350 mm open shelving (hanging needs a decision: see the report)"), "parents-dressing")
    add(against("pd-shelves-2", r["parents-dressing"], "y0", 21.35, "bookcase", w=0.85, d=0.35, h=2.2,
                why="dressing: open shelving past the ensuite door"), "parents-dressing")
    PE = r["parents-ensuite"]
    add(against("pe-shower", PE, "x1", -31.311, "shower_walkin", w=1.4, d=0.9, h=0.1,
                why="walk-in shower in the far corner"), "parents-ensuite")
    add(against("pe-basins", PE, "x0", -30.3, "washbasin_double", h=0.85, why="double basin on the west wall"),
        "parents-ensuite")
    add(against("pe-wc", PE, "y0", 20.2, "wc", h=0.4, why="WC on the far wall between basin and shower"),
        "parents-ensuite")
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


def _columns():
    return [tuple(v / 1000 for v in c) for c in V.E.COLUMNS]


DOOR_TYPES = {
    # door (rooms joined by "/") -> "pocket": a sliding door into the wall, so it sweeps no floor. Parents: the king
    # bed's 750 mm zone and its bedside table sit where a swing would go; the wall beside the door has 1.18 m for
    # the pocket (Phase 2 builds it as a sliding door).
    "corridor/parents-bed": "pocket",
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
        for s in (-1, 1):
            if axis == "h":
                z = (d["x"] - w / 2, d["y"], d["x"] + w / 2, d["y"] + s * depth)
            else:
                z = (d["x"], d["y"] - w / 2, d["x"] + s * depth, d["y"] + w / 2)
            z = (min(z[0], z[2]), min(z[1], z[3]), max(z[0], z[2]), max(z[1], z[3]))
            mid = ((z[0] + z[2]) / 2, (z[1] + z[3]) / 2)
            if RS._room_at(lay, level, *mid):
                out.append({"door": "/".join(d.get("rooms") or []), "rect": z, "garden": bool(d.get("garden"))})
    return out


def check(items=None, lay=None):
    """Every furniture check; returns {check: {"status", "problems": [...], "measured": {...}}}."""
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
    for it in items:
        fp = footprint(it)
        cl = _cluster(lay, it["room"])
        rects = [lay["rooms"][c]["rect"] for c in cl]
        if not _inside(fp, rects):
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


def route_problems(lay, sp, items, level, cell=0.02):
    """In each open cluster of rooms, a 914 mm body (card mitton-path-of-travel-min) must get from every door of
    the cluster to every other door and to every piece's working side. Furniture over 0.3 m and the columns are
    obstacles; walls are the cluster's own edges. Returns [(problem, measured)]."""
    out = []
    done = set()
    zones = _door_zones(sp, lay, level)
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
        obst = [footprint(it) for it in items if it["room"] in cl and it["h"] >= 0.3] + _columns()
        for a, b, c, d in obst:
            free &= ~((X > a) & (X < c) & (Y > b) & (Y < d))
        k = max(1, int(np.ceil(BODY / cell - 1e-9)))   # never kinder than the card: the body rounds UP (0.92 m)
        s = np.pad(np.cumsum(np.cumsum(free.astype(np.int32), 0), 1), ((1, 0), (1, 0)))
        if k > min(nx, ny):
            continue
        win = s[k:, k:] - s[:-k, k:] - s[k:, :-k] + s[:-k, :-k]
        ok = win == k * k
        ax0, ay0 = gx[:ok.shape[0]] - cell / 2, gy[:ok.shape[1]] - cell / 2
        AX, AY = np.meshgrid(ax0, ay0, indexing="ij")
        body = k * cell

        def touching(rect):
            return ok & (AX < rect[2]) & (AX + body > rect[0]) & (AY < rect[3]) & (AY + body > rect[1])
        nodes = []
        for z in zones:
            zc = ((z["rect"][0] + z["rect"][2]) / 2, (z["rect"][1] + z["rect"][3]) / 2)
            if any(q[0] <= zc[0] <= q[2] and q[1] <= zc[1] <= q[3] for q in rects):
                nodes.append(("door " + z["door"], [z["rect"]]))
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
            elif t.clearance["front"] > 0:
                nodes.append((it["id"], [_middle(side_zone(it, "front", 0.3))]))
        if len(nodes) < 2:
            continue
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
        for name, rs_ in nodes[1:]:
            if not any((touching(rect) & seen).any() for rect in rs_):
                out.append(("%s (%s): not reached by a 914 mm path from %s" % (name, "+".join(sorted(cl)),
                                                                                  nodes[0][0]), {}))
    return out
