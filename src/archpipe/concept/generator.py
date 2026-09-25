"""Generator v1: parametric footprints per parti, searched and critiqued.

Each parti arranges the programme in rectangular wings. A wing is a stack of
bands (a row of rooms, or a corridor) along one axis; rooms take their
scheduled area at the band's depth, and the last room of a short band
stretches to the wing's length. Random but seeded variation of band depths,
room order and which band holds which block gives many variants per parti;
the critic scores every one the same way.

Generator parameters (corridor width, stair allowance, depths, setback
placeholder) are search settings, not standards; the critic's findings are
what carry a basis.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from . import critic
from . import layout as L

ROOT = Path(__file__).resolve().parents[3]
CORRIDOR = 1.3          # m; generator setting (CIRC-03 width decision is still open)
STAIR_LEN = 2.6         # m along the band; placeholder allowance, not a stair design
MIN_RUN = 1.8           # m; generator setting so every room can take a door off the corridor
SOUTH_OFFSET = 6.0      # m from the road boundary; setbacks are not supplied, placeholder only
LEVELS = {"L00": 0.0, "L01": 3.3}

OCC = {"entry": "entrance", "living": "living", "dining": "dining", "kitchen": "kitchen", "guest": "bedroom",
       "bath-ground": "bathroom", "utility": "utility", "study": "study", "storage": "store",
       "main-bedroom": "bedroom", "dressing": "dressing", "ensuite": "ensuite", "bed-2": "bedroom",
       "bed-3": "bedroom", "bath-family": "bathroom", "family": "living"}
UPPER = {"main-bedroom", "dressing", "ensuite", "bed-2", "bed-3", "bath-family", "family"}
# Blocks keep rooms that must touch together; `links` inside a block become doors.
GROUND_BLOCKS = {"ldk": ["living", "dining", "kitchen"], "guest": ["guest"], "bath-ground": ["bath-ground"],
                 "utility": ["utility"], "study": ["study"], "storage": ["storage"]}
UPPER_BLOCKS = {"suite": ["main-bedroom", "dressing", "ensuite"], "bed-2": ["bed-2"], "bed-3": ["bed-3"],
                "bath-family": ["bath-family"], "family": ["family"]}
INTERNAL = [("living", "dining"), ("dining", "kitchen"), ("main-bedroom", "dressing"), ("dressing", "ensuite")]
VIA = {"dressing", "ensuite"}           # entered through the suite, never from the corridor


def programme(root=ROOT):
    proj = json.loads((root / "knowledge" / "projects" / "villa-pilot.json").read_text(encoding="utf-8"))
    sched = proj["area_schedule"]
    return {r["id"]: r["area_m2"] for r in sched["rooms"]}, sched["available_m2"], sched["circulation_m2"]


def place_wing(level, axis, origin, bands, areas, length=None):
    """Rooms of one wing as rectangles. bands: [{"depth": d, "rooms": [...]} | {"depth": d, "corridor": id}]."""
    def run(b):
        return sum(_run(r, b["depth"], areas) for r in b["rooms"])
    L_ = max([length or 0] + [run(b) for b in bands if "rooms" in b])
    rects, off = {}, 0.0
    for b in bands:
        d = b["depth"]
        if "corridor" in b:
            spans = [(b["corridor"], 0.0, L_)]
        else:
            pos, spans = 0.0, []
            for i, r in enumerate(b["rooms"]):
                ln = _run(r, d, areas)
                end = L_ if i == len(b["rooms"]) - 1 else pos + ln
                spans.append((r, pos, end))
                pos = end
        for r, a, e in spans:
            ox, oy = origin
            rects[r] = ((ox + a, oy + off, ox + e, oy + off + d) if axis == "x"
                        else (ox + off, oy + a, ox + off + d, oy + e))
        off += d
    return rects, L_, off


def _run(room, depth, areas):
    return STAIR_LEN if room.startswith("stair") else max(MIN_RUN, areas[room] / depth)


def _r(v):
    return round(v * 20) / 20          # 50 mm grid


def _blocks(rng, names, table):
    order = list(names)
    rng.shuffle(order)
    out = []
    for n in order:
        rooms = list(table[n])
        if n == "suite" and rng.random() < 0.5:
            rooms.reverse()
        if n == "ldk" and rng.random() < 0.5:
            rooms.reverse()
        out += rooms
    return out


def _split(rng, names, k=2, fixed=None):
    parts = [[] for _ in range(k)]
    for n in names:
        parts[fixed[n] if fixed and n in fixed else rng.randrange(k)].append(n)
    return parts


def _wet_core(rng, ground, upper):
    """Option: put the wet rooms next to the stair on both levels so they stack (a common design move)."""
    if rng.random() < 0.5:
        return ground, upper
    g = [r for r in ground if r not in ("bath-ground", "utility")]
    u = [r for r in upper if r not in ("bath-family", "main-bedroom", "dressing", "ensuite")]
    return (g[:1] + ["bath-ground", "utility"] + g[1:],
            u[:1] + ["bath-family", "ensuite", "dressing", "main-bedroom"] + u[1:])


def bar(rng, areas):
    ds, dn = rng.choice([4.2, 4.8, 5.4]), rng.choice([5.0, 5.6, 6.2])
    g_s, g_n = _split(rng, [b for b in GROUND_BLOCKS if b != "ldk"])
    g = {"S": ["stair", "entry"] + _blocks(rng, g_s, GROUND_BLOCKS),
         "N": _blocks(rng, ["ldk"] + g_n, GROUND_BLOCKS)}
    u_s, u_n = _split(rng, list(UPPER_BLOCKS))
    if not u_n:
        u_n = [u_s.pop()]
    u = {"S": ["stair-up"] + _blocks(rng, u_s, UPPER_BLOCKS), "N": _blocks(rng, u_n, UPPER_BLOCKS)}
    if rng.random() < 0.5:
        wet_g, wet_u = {"bath-ground", "utility"}, {"bath-family", "main-bedroom", "dressing", "ensuite"}
        g["N"] = [r for r in g["N"] if r not in wet_g]
        u["N"] = [r for r in u["N"] if r not in wet_u] or ["family"]
        u["S"] = [r for r in u["S"] if r != "family" or "family" not in u["N"]]
        g["S"], u["S"] = _wet_core(random.Random(0), g["S"] + sorted(wet_g - set(g["S"])),
                                   u["S"] + sorted(wet_u - set(u["S"])))
    rects, Lg, _ = place_wing("L00", "x", (0, 0), [{"depth": ds, "rooms": g["S"]}, {"depth": CORRIDOR, "corridor": "hall"},
                                                   {"depth": dn, "rooms": g["N"]}], areas)
    up, _, _ = place_wing("L01", "x", (0, 0), [{"depth": ds, "rooms": u["S"]}, {"depth": CORRIDOR, "corridor": "landing"},
                                              {"depth": dn, "rooms": u["N"]}], areas)
    return {"L00": rects, "L01": up}, {"corridors": {"L00": ["hall"], "L01": ["landing"]}}


def l_shape(rng, areas):
    da, dw = rng.choice([5.0, 5.6, 6.2]), rng.choice([4.2, 4.8, 5.4])
    a_extra, b_blocks = _split(rng, [b for b in GROUND_BLOCKS if b != "ldk"])
    a_rooms = ["stair"] + _blocks(rng, ["ldk"] + a_extra, GROUND_BLOCKS)
    b_rooms = ["entry"] + _blocks(rng, b_blocks, GROUND_BLOCKS)
    wing_a, La, depth_a = place_wing("L00", "x", (0, 0), [{"depth": CORRIDOR, "corridor": "hall"},
                                                          {"depth": da, "rooms": a_rooms}], areas)
    run_b = sum(_run(r, dw, areas) for r in b_rooms)
    wing_b, _, _ = place_wing("L00", "y", (0, -run_b), [{"depth": dw, "rooms": b_rooms},
                                                        {"depth": CORRIDOR, "corridor": "hall-b"}], areas)
    up_rooms = ["stair-up"] + _blocks(rng, list(UPPER_BLOCKS), UPPER_BLOCKS)
    if "bath-ground" in a_rooms and "utility" in a_rooms:
        a_rooms, up_rooms = _wet_core(rng, a_rooms, up_rooms)
        wing_a, La, depth_a = place_wing("L00", "x", (0, 0), [{"depth": CORRIDOR, "corridor": "hall"},
                                                              {"depth": da, "rooms": a_rooms}], areas)
    up, _, _ = place_wing("L01", "x", (0, 0), [{"depth": CORRIDOR, "corridor": "landing"},
                                               {"depth": da, "rooms": up_rooms}], areas)
    return {"L00": {**wing_a, **wing_b}, "L01": up}, {"corridors": {"L00": ["hall", "hall-b"], "L01": ["landing"]}}


def u_court(rng, areas):
    ds, dw, de = rng.choice([4.2, 4.8, 5.4]), rng.choice([5.0, 5.6]), rng.choice([4.2, 4.8, 5.4])
    rest = [b for b in GROUND_BLOCKS if b != "ldk"]
    s_blocks, e_blocks = _split(rng, rest)
    if not e_blocks:
        e_blocks = [s_blocks.pop()]
    s_rooms = ["stair", "entry"] + _blocks(rng, s_blocks, GROUND_BLOCKS)
    w_rooms = ["kitchen", "dining", "living"]                     # living at the arm's north tip, facing the garden
    e_rooms = _blocks(rng, e_blocks, GROUND_BLOCKS)
    up_rooms = ["stair-up"] + _blocks(rng, list(UPPER_BLOCKS), UPPER_BLOCKS)
    if "bath-ground" in s_rooms and "utility" in s_rooms:
        s_rooms, up_rooms = _wet_core(rng, s_rooms, up_rooms)
    run_up = sum(_run(r, ds, areas) for r in up_rooms)
    court_min = rng.choice([7.0, 9.0, 11.0])
    Ls = max(run_up, sum(_run(r, ds, areas) for r in s_rooms),
             dw + CORRIDOR + court_min + CORRIDOR + de)
    south, _, depth_s = place_wing("L00", "x", (0, 0), [{"depth": ds, "rooms": s_rooms},
                                                        {"depth": CORRIDOR, "corridor": "gallery-s"}], areas, length=Ls)
    west, _, _ = place_wing("L00", "y", (0, depth_s), [{"depth": dw, "rooms": w_rooms},
                                                       {"depth": CORRIDOR, "corridor": "gallery-w"}], areas)
    east, _, _ = place_wing("L00", "y", (Ls - de - CORRIDOR, depth_s), [{"depth": CORRIDOR, "corridor": "gallery-e"},
                                                                        {"depth": de, "rooms": e_rooms}], areas)
    up, _, _ = place_wing("L01", "x", (0, 0), [{"depth": ds, "rooms": up_rooms},
                                               {"depth": CORRIDOR, "corridor": "landing"}], areas, length=Ls)
    return ({"L00": {**south, **west, **east}, "L01": up},
            {"corridors": {"L00": ["gallery-s", "gallery-w", "gallery-e"], "L01": ["landing"]}})


PARTIS = {"bar": bar, "L": l_shape, "U": u_court}


def build(parti, seed, areas):
    rng = random.Random(f"{parti}-{seed}")
    levels, meta = PARTIS[parti](rng, areas)
    allr = [r for lv in levels.values() for r in lv.values()]
    x0, y0 = min(r[0] for r in allr), min(r[1] for r in allr)
    w = max(r[2] for r in allr) - x0
    dx, dy = _r((30.0 - w) / 2) - x0, SOUTH_OFFSET - y0
    rooms = {}
    for lid, rects in levels.items():
        for rid, (a, b, c, d) in rects.items():
            occ = ("stair" if rid.startswith("stair") else "landing" if rid == "landing"
                   else "corridor" if rid in meta["corridors"][lid] else OCC[rid])
            rooms[rid] = {"level": lid, "rect": [_r(a + dx), _r(b + dy), _r(c + dx), _r(d + dy)], "occupancy": occ,
                          "name": rid.replace("-", " ").title(), "target_m2": areas.get(rid)}
    links = [list(p) for p in INTERNAL]
    for lid, cors in meta["corridors"].items():
        for i, c in enumerate(cors):
            links += [[c, o] for o in cors[i + 1:] if _touch(rooms[c]["rect"], rooms[o]["rect"])]
            for rid, r in rooms.items():
                if r["level"] == lid and rid not in cors and rid not in VIA and _touch(r["rect"], rooms[c]["rect"]):
                    links.append([c, rid])
    return {"id": f"{parti}-{seed}", "parti": parti, "plot": {"width_m": 30.0, "depth_m": 40.0}, "levels": dict(LEVELS),
            "rooms": rooms, "links": links, "vertical": [["stair", "stair-up"]], "entrance": "entry"}


def _touch(a, b):
    ox = min(a[2], b[2]) - max(a[0], b[0])
    oy = min(a[3], b[3]) - max(a[1], b[1])
    return (abs(ox) < 1e-6 and oy > 1.2) or (abs(oy) < 1e-6 and ox > 1.2)


def score(result):
    """Rank: fewest failed checks, then least circulation over the allowance, then smallest area deviation.
    Advisory values only order variants; they never pass or fail one."""
    get = {c["check"]: c for c in result["checks"]}
    dev = get["area_match"]["deviation_m2"]
    excess = get["circulation_area"]["excess_m2"] if "circulation_area" in get else 0.0
    return (len(result["fails"]), round(excess + sum(abs(v) for v in dev.values()), 1))  # area_match can fail too


def search(parti, n=400, root=ROOT):
    areas, available, circulation = programme(root)
    best = None
    for seed in range(n):
        lay = build(parti, seed, areas)
        res = critic.critique(lay, available, circulation)
        key = score(res)
        if best is None or key < best[0]:
            best = (key, lay, res)
    return best[1], best[2], n
