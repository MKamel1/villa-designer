"""A villa layout (concept.villa / villa_options) as buildable Revit elements: walls, doors, windows, rooms, the
stair solids and the GF slab opening. Consumed by revit/build_villa_option.py.

Walls follow the room edges: an edge with outside on one side is an external wall (0.20 m, set inside the outer
face); an edge between two rooms is a partition (0.10 m, centred), except between two OPEN rooms (kitchen, dining,
living, halls, stair), which get a room-separation line instead so the open plan stays open. Doors go on every
intended link that crosses a wall and on every entrance; garden doors on the basement living and dining facades;
windows on the allowed facades (street, east, rear) of habitable and sanitary rooms, heads under the 0.6 m beams.
Units: metres, Revit project axes; storey z from the level (B -1.80 -> model -3000 mm, GF +1.20 -> model 0).
"""
from __future__ import annotations

from .. import vocabulary as vocab
from . import stairs as S
from . import villa as V

OPEN = {"kitchen", "dining", "living", "hall", "corridor", "entrance", "landing", "stair"}
EXT_T, INT_T = 0.20, 0.10
WALL_H = 2.80                         # storey 3.0 less the 0.2 slab
LEVEL_NAME = {"B": "B -1.80", "GF": "GF +1.20"}
LEVELS_Z = {"B": -3.0, "GF": 0.0}      # model z (m) of the storey FFLs
DOOR_H = 2.10                          # ASSUMED standard leaf (= villa_parking.DOOR_H)
GARDEN_DOOR_H = 2.20                   # sliding garden doors: to the 2.30 head under the beams, less the frame
SILL, HEAD = 0.90, 2.30              # head at the beam soffit less finishes (elevation_checks)


def _stair_model(lay):
    from . import stair_options as SO
    return {"u": S.u_in_old_bay, "u-front": SO.u_front_bay, "party-fixed": S.party_flight_fixed}[lay["stair"]]()


def _room_at(lay, level, x, y):
    for rid, r in lay["rooms"].items():
        x0, y0, x1, y1 = r["rect"]
        if r["level"] == level and x0 - 1e-6 <= x <= x1 + 1e-6 and y0 - 1e-6 <= y <= y1 + 1e-6:
            return rid
    return None


def segments(lay, level):
    """Atomic edge pieces with the room on each side (None = outside)."""
    rooms = [r for r in lay["rooms"].values() if r["level"] == level]
    lines = {}
    for r in rooms:
        x0, y0, x1, y1 = r["rect"]
        for ax, c, a, b in (("h", y0, x0, x1), ("h", y1, x0, x1), ("v", x0, y0, y1), ("v", x1, y0, y1)):
            lines.setdefault((ax, round(c, 4)), []).append((a, b))
    out = []
    for (ax, c), spans in lines.items():
        cuts = sorted({round(v, 4) for s in spans for v in s})
        for a, b in zip(cuts, cuts[1:]):
            if not any(s0 - 1e-6 <= a and b <= s1 + 1e-6 for s0, s1 in spans):
                continue
            m = (a + b) / 2
            if ax == "h":
                s1_, s2_ = _room_at_strict(lay, level, m, c + 0.01), _room_at_strict(lay, level, m, c - 0.01)
            else:
                s1_, s2_ = _room_at_strict(lay, level, c + 0.01, m), _room_at_strict(lay, level, c - 0.01, m)
            if s1_ is None and s2_ is None:
                continue
            out.append({"axis": ax, "c": c, "a": a, "b": b, "rooms": (s1_, s2_)})
    return out


def _room_at_strict(lay, level, x, y):
    for rid, r in lay["rooms"].items():
        x0, y0, x1, y1 = r["rect"]
        if r["level"] == level and x0 < x < x1 and y0 < y < y1:
            return rid
    return None


def _kind(lay, seg):
    a, b = seg["rooms"]
    if a is None or b is None:
        return "ext"
    oa, ob = lay["rooms"][a]["occupancy"], lay["rooms"][b]["occupancy"]
    return "sep" if oa in OPEN and ob in OPEN else "int"


def _merge(segs):
    """Join collinear touching pieces of the same kind (and same outside side for external walls)."""
    segs = sorted(segs, key=lambda s: (s["axis"], s["c"], s["kind"], s["side"], s["a"]))
    out = []
    for s in segs:
        if out and all(out[-1][k] == s[k] for k in ("axis", "c", "kind", "side")) and abs(out[-1]["b"] - s["a"]) < 1e-6:
            out[-1]["b"] = s["b"]
        else:
            out.append(dict(s))
    return out


def build(lay):
    spec = {"id": lay["id"], "title": lay["title"], "levels": LEVEL_NAME, "walls": [], "separations": [],
            "doors": [], "windows": [], "rooms": [], "stair": [], "gf_opening": None}
    for lv in ("B", "GF"):
        raw = []
        for s in segments(lay, lv):
            k = _kind(lay, s)
            side = 0
            if k == "ext":                       # which side is inside: +1 = the +axis side holds the room
                side = 1 if s["rooms"][0] is not None else -1
            raw.append(dict(s, kind=k, side=side))
        for w in _merge(raw):
            if w["kind"] == "sep":
                spec["separations"].append({"level": lv, **_line(w, 0.0)})
                continue
            t = EXT_T if w["kind"] == "ext" else INT_T
            off = (t / 2) * w["side"] if w["kind"] == "ext" else 0.0
            spec["walls"].append({"level": lv, "kind": w["kind"], "thickness": t, "height": WALL_H, **_line(w, off)})
        # doors
        for a, b in lay["links"]:
            ra, rb = lay["rooms"][a], lay["rooms"][b]
            if ra["level"] != lv or rb["level"] != lv:
                continue
            if ra["occupancy"] in OPEN and rb["occupancy"] in OPEN:
                continue                         # open plan: no door
            best = max(((V.overlap_len(e1, e2), e1, e2) for e1 in V.edges(ra["rect"]) for e2 in V.edges(rb["rect"])),
                       key=lambda q: q[0])
            L_, e1, e2 = best
            lo, hi = max(e1[2], e2[2]), min(e1[3], e2[3])
            mid = (lo + hi) / 2
            if {ra["occupancy"], rb["occupancy"]} & {"wc", "bathroom", "ensuite", "store", "utility"}:
                w_ = 0.8
            else:
                w_ = 0.9
            spec["doors"].append({"level": lv, "x": mid if e1[0] == "h" else e1[1], "y": e1[1] if e1[0] == "h" else mid,
                                  "width": w_, "rooms": [a, b]})
        for rid, l2, seg in lay["entries"]:
            if l2 != lv:
                continue
            sg = V.ENTRY_SEGMENTS[lv][seg]
            e = max(V.edges(lay["rooms"][rid]["rect"]), key=lambda e_: V.overlap_len(e_, sg))
            lo, hi = max(e[2], sg[2]), min(e[3], sg[3])
            mid = (lo + hi) / 2
            spec["doors"].append({"level": lv, "x": mid if e[0] == "h" else e[1], "y": e[1] if e[0] == "h" else mid,
                                  "width": 1.0, "rooms": [rid, "core"], "entrance": True})
        # garden doors and windows
        ext = lay.get("extension")
        faces = V.window_faces(lv, ext)
        for rid, r in lay["rooms"].items():
            if r["level"] != lv:
                continue
            occ = r["occupancy"]
            if occ not in vocab.HABITABLE and occ not in vocab.SANITARY and occ != "utility":
                continue
            for e in V.edges(r["rect"]):
                for f in faces:
                    L_ = V.overlap_len(e, f)
                    if L_ < 1.0:
                        continue
                    lo, hi = max(e[2], f[2]), min(e[3], f[3])
                    mid = (lo + hi) / 2
                    x, y = (mid, e[1]) if e[0] == "h" else (e[1], mid)
                    garden = lv == "B" and occ in ("living", "dining", "kitchen")
                    if garden and occ in ("living", "dining"):
                        spec["doors"].append({"level": lv, "x": x, "y": y, "width": min(2.4, L_ - 0.8), "rooms": [rid, "yard"],
                                              "garden": True})
                        continue
                    if occ in vocab.HABITABLE:
                        spec["windows"].append({"level": lv, "x": x, "y": y, "width": round(min(2.4, L_ - 0.8), 2),
                                                "sill": SILL, "height": HEAD - SILL, "room": rid})
                    else:
                        spec["windows"].append({"level": lv, "x": x, "y": y, "width": 0.8, "sill": 1.5,
                                                "height": HEAD - 1.5, "room": rid})
        for rid, r in lay["rooms"].items():
            if r["level"] == lv:
                x0, y0, x1, y1 = r["rect"]
                spec["rooms"].append({"level": lv, "id": rid, "name": r["name"], "x": (x0 + x1) / 2,
                                      "y": (y0 + y1) / 2})
    st = _stair_model(lay)
    spec["stair"] = [p["box"] for p in st["parts"] if "headroom" not in p["what"]]
    spec["stair_name"] = st["name"]
    pk2 = lay.get("parking2")
    if pk2:
        from . import villa_parking as P
        street = -1.2                                   # street level in model metres (GF FFL = 0)
        r0, _, r1, _ = pk2["ramp"]
        d0, y0, d1, y1 = pk2["deck"]
        spec["parking2"] = {
            "ramp": {"x0": r0, "x1": r1, "y0": y0, "y1": y1, "z_top0": street + 0.0,
                     "z_top1": street + pk2["deck_top"], "thick": P.BUILDUP},
            "deck": {"x0": d0, "x1": d1, "y0": y0, "y1": y1, "z_top": street + pk2["deck_top"], "thick": P.BUILDUP},
            "cars": [[d0 + 0.2 + i * 4.9, (y0 + y1) / 2 - 0.9, d0 + 0.2 + i * 4.9 + 4.6, (y0 + y1) / 2 + 0.9,
                      street + pk2["deck_top"], street + pk2["deck_top"] + 1.45] for i in range(pk2["cars"])]}
        # walls of the rooms under the ramp and deck stop at the soffit above them (client review r7: they came
        # through the ramp): a cross wall takes the clear height at its low face; a wall along the ramp is split at
        # the ramp's top end, takes the clear height at its low end and gets a sloped infill up to the soffit
        zb = LEVELS_Z["B"]
        walls, spec["infills"] = [], []
        for w in spec["walls"]:
            if w["level"] != "B" or max(w["y0"], w["y1"]) <= V.YE + EXT_T:
                walls.append(w)                        # inside the villa, or on its east face line
                continue
            if abs(w["y0"] - w["y1"]) > 1e-6:          # cross wall (constant x)
                walls.append(dict(w, height=round(min(WALL_H, P.clear_at(w["x0"] - w["thickness"] / 2)), 3)))
                continue
            a, b = sorted((w["x0"], w["x1"]))
            cuts = [a] + [c for c in (P.RAMP_X1,) if a + 1e-6 < c < b - 1e-6] + [b]
            for s, e in zip(cuts, cuts[1:]):
                h0, h1 = P.clear_at(s), P.clear_at(e)
                walls.append(dict(w, x0=s, x1=e, height=round(min(WALL_H, h0), 3)))
                if h1 - h0 > 0.005:
                    t = w["thickness"] / 2
                    spec["infills"].append({"what": "wall top up to the ramp soffit", "y0": round(w["y0"] - t, 3),
                                            "y1": round(w["y0"] + t, 3), "profile": [
                                                [s, round(zb + h0, 3)], [e, round(zb + h0, 3)], [e, round(zb + h1, 3)]]})
        spec["walls"] = walls
        # doors into the rooms under the ramp: at the wall's high end, leaf sized to the clear height
        ext_ids = {r["id"] for r in lay["rooms"].values() if r.get("ext")}
        for d in spec["doors"]:
            ids = [i for i in d.get("rooms", []) if i in ext_ids]
            if d["level"] != "B" or not ids:
                continue
            ra, rb_ = (lay["rooms"][i]["rect"] for i in d["rooms"])
            if abs(d["y"] - V.YE) < 1e-6:                        # on the villa's east face: slides along x
                lo, hi = max(ra[0], rb_[0]), min(ra[2], rb_[2])
                d["x"], d["height"], d["clear"], d["fit"] = P.door_fit(lo, hi, d["width"],
                                                                         lay["rooms"][ids[0]]["occupancy"])
            else:                                               # a cross wall: the clear height is fixed there
                c = P.clear_at(d["x"])
                d["height"], d["clear"] = min(P.DOOR_H, round(c - P.HEAD_ZONE, 2)), c
                d["fit"] = "full" if d["height"] >= P.DOOR_H - 1e-9 else "reduced"
        # the kept NE yard wall is the store's side from the gate to the villa: no new wall there, only an infill
        # from the wall top (1.40 m) up to the ramp soffit, whose profile slopes with the ramp
        from .. import villa_env as E
        wx0, wy0, wx1, wy1 = (v / 1000 for v in E.YARD_WALL)
        spec["walls"] = [w for w in spec["walls"] if not (
            w["level"] == "B" and abs(w["y0"] - w["y1"]) < 1e-6 and abs(w["y0"] - V.YE) < EXT_T
            and max(w["x0"], w["x1"]) <= wx1 + 1e-6)]
        top = LEVELS_Z["B"] + E.YARD_WALL_H / 1000
        spec["infill"] = {"y0": wy0, "y1": wy1, "profile": [
            [wx0, top], [wx1, top], [wx1, round(LEVELS_Z["B"] + P.clear_at(wx1), 3)],
            [wx0, round(LEVELS_Z["B"] + P.clear_at(wx0), 3)]]}
        # GF windows over the ramp / deck: high sills (a person on the deck sees over a 0.9 m sill)
        for wdw in spec["windows"]:
            if wdw["level"] == "GF" and abs(wdw["y"] - V.YE) < 1e-6 and r0 - 1e-6 <= wdw["x"] <= d1 + 1e-6:
                wdw["sill"], wdw["height"] = 1.5, round(HEAD - 1.5, 2)
        spec["roofs"] = []
    else:
        spec["roofs"] = [list(r) for r in V._exts(lay.get("extension"))]   # east-yard blocks: roof at the GF floor
    for d in spec["doors"]:                            # every door states its leaf height; Revit types are sized to it
        d.setdefault("height", GARDEN_DOOR_H if d.get("garden") else DOOR_H)
    op = S.clashes(st)["slab_opening_needed"]
    spec["gf_opening"] = [v / 1000 for v in op] if op else None
    return spec


def _line(w, off):
    if w["axis"] == "h":
        return {"x0": w["a"], "y0": w["c"] + off, "x1": w["b"], "y1": w["c"] + off}
    return {"x0": w["c"] + off, "y0": w["a"], "x1": w["c"] + off, "y1": w["b"]}


def clearance_problems(lay, walls, doors, infills=()):
    """Post-condition for the rooms under the ramp and deck (client review r7: walls came through the ramp, a
    2.1 m door opened under a 1.9 m soffit). walls: dicts with level, x0, y0, x1, y1 and z_top (model m) or height;
    doors: level, x, y, width, height. Returns a list of problems (empty = pass). Works on the spec and on Revit's
    read-back alike."""
    pk2 = lay.get("parking2")
    if not pk2:
        return []
    from . import villa_parking as P
    zb, tol = LEVELS_Z["B"], 0.01
    soffit = lambda x: zb + P.clear_at(x)                                     # noqa: E731
    out = []
    for w in walls:
        if w["level"] not in ("B", LEVEL_NAME["B"]) or max(w["y0"], w["y1"]) <= V.YE + EXT_T:
            continue
        top = w["z_top"] if "z_top" in w else zb + w["height"]
        a, b = sorted((w["x0"], w["x1"]))
        worst = min(soffit(a), soffit(b))
        if top > worst + tol:
            out.append("wall x %.2f-%.2f y %.2f: top %.2f is %.0f mm above the ramp/deck soffit"
                       % (a, b, w["y0"], top, (top - worst) * 1000))
        if abs(w["y0"] - w["y1"]) < 1e-6:                                   # along the ramp: gap under the soffit?
            cover = max([f["profile"][-1][1] for f in infills
                         if abs((f["y0"] + f["y1"]) / 2 - w["y0"]) < 0.2 and abs(f["profile"][-1][0] - b) < 0.01]
                        or [top])
            if soffit(b) - cover > 0.02:
                out.append("wall x %.2f-%.2f y %.2f: %.0f mm open under the soffit at its high end"
                           % (a, b, w["y0"], (soffit(b) - cover) * 1000))
    for d in doors:
        if d["level"] not in ("B", LEVEL_NAME["B"]) or not (P.RAMP_X0 <= d["x"] <= pk2["deck"][2]):
            continue
        rooms = [lay["rooms"].get(r) for r in d.get("rooms") or []]
        if not any(r and r.get("ext") for r in rooms):
            continue
        low = min(P.clear_at(d["x"] - d["width"] / 2), P.clear_at(d["x"] + d["width"] / 2))
        if d["height"] + P.HEAD_ZONE > low + tol:
            out.append("door x %.2f (%s): %.2f m leaf + %.2f frame under %.2f m clear"
                       % (d["x"], "/".join(d.get("rooms") or []), d["height"], P.HEAD_ZONE, low))
    return out
