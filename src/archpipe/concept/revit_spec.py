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
from .authored_values import fill_defaults, override

OPEN = {"kitchen", "dining", "living", "hall", "corridor", "entrance", "landing", "stair"}
EXT_T, INT_T = 0.20, 0.10
WALL_H = 2.80                         # storey 3.0 less the 0.2 slab
LEVEL_NAME = {"B": "B -1.80", "GF": "GF +1.20"}
LEVELS_Z = {"B": -3.0, "GF": 0.0}      # model z (m) of the storey FFLs
DOOR_H = 2.10                          # ASSUMED standard leaf (= villa_parking.DOOR_H)
GARDEN_DOOR_H = 2.20                   # sliding garden doors: to the 2.30 head under the beams, less the frame
REVEAL = 0.20                          # wall kept each side of a window or garden door on its run (the runs are
#                                        already cut clear of the columns; was 0.40, which under-glazed every room)
SILL, HEAD = 0.90, 2.30              # head at the beam soffit less finishes (elevation_checks)


def full_height_faces(lay, level):
    """Faces glazed floor to beam over their whole column-free run: {(axis, coordinate): 'street' | 'end'}. The
    basement's street face has a floor-to-beam window today (client 2026-09-26, kept); the end of the east-yard
    extension faces the garden and gets the same, whatever room is behind it (client: P1 had a 0.8 m utility
    window there, P2/P4 none because a store was at the end)."""
    if level != "B":
        return {}
    out = {("v", round(V.X0, 3)): "street"}
    for _, _, x1, _ in V._exts(lay.get("extension")):
        out.setdefault(("v", round(x1, 3)), "end")
    fh = lay.get("basement_full_height")
    if fh:                                           # round 11: every basement face a lived-in room looks out of;
        faces = ("east", "garden") if fh is True else fh   # round 12: north and east only (the garden end glared)
        if "garden" in faces:
            out.setdefault(("v", round(V.XR, 3)), "yard")
        if "east" in faces:
            out.setdefault(("h", round(V.YE, 3)), "yard")
    return out


def street_runs(lay, level):
    """Street-face runs of a living room together with its alcoves (rooms with part_of): [(face, lo, hi, room)],
    one floor-to-beam opening each (client r9: "a very wide window where we need sun")."""
    if level != "B":
        return []
    out = []
    faces = [f for f in V.window_faces(level, lay.get("extension")) if full_height_faces(lay, level).get(
        (f[0], round(f[1], 3))) == "street"]
    for rid, r in lay["rooms"].items():
        kids = [v for v in lay["rooms"].values() if v.get("part_of") == rid]
        if r["level"] != level or not kids:
            continue
        for f in faces:
            spans = sorted((max(e[2], f[2]), min(e[3], f[3])) for v in [r] + kids for e in V.edges(v["rect"])
                           if V.overlap_len(e, f) > 1e-6)
            run = []
            for a, b in spans:
                if run and a <= run[-1][1] + 1e-6:
                    run[-1][1] = max(run[-1][1], b)
                else:
                    run.append([a, b])
            out += [(f, a, b, rid) for a, b in run if b - a >= 1.0]
    return out


def glazing_problems(lay, windows, doors):
    """Post-condition (client r8 review): every run of a full-height face (full_height_faces) that the plan glazes
    carries an opening from the floor to the beam head, nearly as wide as the run. windows/doors: the spec or
    Revit's read-back (width, height and sill as BUILT). Returns problems (empty = pass)."""
    out, tol = [], 0.02
    full = full_height_faces(lay, "B")
    ops = [dict(o, sill=o.get("sill", 0.0), head=o.get("sill", 0.0) + (o.get("height") or 0.0))
           for o in list(windows) + [d for d in doors if d.get("garden")] if o.get("level") in ("B", LEVEL_NAME["B"])]
    for f in V.window_faces("B", lay.get("extension")):
        kind = full.get((f[0], round(f[1], 3)))
        if not kind:
            continue
        runs = {rid: [(lo, hi) for f2, lo, hi, r2 in street_runs(lay, "B") if f2 == f and r2 == rid]
                for rid in lay["rooms"]}
        for rid, r in lay["rooms"].items():
            if r["level"] != "B" or (kind in ("street", "yard") and r["occupancy"] not in vocab.HABITABLE) or                     (r.get("part_of") and kind == "street"):
                continue
            pieces = runs[rid] if kind == "street" and runs[rid] else [
                (max(e[2], f[2]), min(e[3], f[3])) for e in V.edges(r["rect"]) if V.overlap_len(e, f) > 1e-6]
            for lo, hi in pieces:
                L_ = hi - lo
                if L_ < 1.0:
                    continue
                on = [o for o in ops if abs((o["x"] if f[0] == "v" else o["y"]) - f[1]) < 0.05
                      and lo - tol <= (o["y"] if f[0] == "v" else o["x"]) <= hi + tol]
                need_w = L_ - 2 * REVEAL - tol
                # a door's leaf stops under its frame: the leaf reaches the head less the frame zone
                ok = [o for o in on if o["sill"] <= tol and (o.get("width") or 0) >= need_w and
                      o["head"] >= (GARDEN_DOOR_H if o.get("garden") else HEAD) - tol]
                if not ok:
                    got = ", ".join("%.2f wide, %.2f-%.2f" % (o.get("width") or 0, o["sill"], o["head"]) for o in on)
                    out.append("%s %s face %s %.2f (%.2f m run): no floor-to-beam opening %.2f wide (built: %s)"
                               % (rid, kind, f[0], f[1], L_, L_ - 2 * REVEAL, got or "nothing"))
    return out


def _stair_model(lay):
    from . import stair_options as SO
    return {"u": S.u_in_old_bay, "u-front": SO.u_front_bay, "party-fixed": S.party_flight_fixed, "u-length": S.u_lengthwise_party, "party-r8": S.party_flight_r8}[lay["stair"]]()


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


def is_open(room):
    """Open-plan room: its occupancy is open, or the layout marks it open (client r9: the GF study is open to the
    stair, no wall and no door)."""
    return room["occupancy"] in OPEN or bool(room.get("open"))


def _kind(lay, seg):
    a, b = seg["rooms"]
    if a is None or b is None:
        return "ext"
    ra, rb = lay["rooms"][a], lay["rooms"][b]
    if ra.get("part_of") == b or rb.get("part_of") == a:          # a room and its alcove: one room, no wall
        return "sep"
    return "sep" if is_open(ra) and is_open(rb) else "int"


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
    from .build_cache import derived
    return derived("revit_spec", lay, lambda: _build(lay))


def _build(lay):
    spec = {"id": lay["id"], "title": lay["title"], "levels": LEVEL_NAME, "walls": [], "separations": [],
            "doors": [], "windows": [], "rooms": [], "stair": [], "gf_opening": None,
            "hatches": [], "pocket_buildouts": [], "balustrades": [], "bath_fittings": [], "ventilation": []}
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
            if (is_open(ra) and is_open(rb)) or ra.get("part_of") == b or rb.get("part_of") == a:
                continue                         # open plan (or a room and its alcove): no door
            best = max(((V.overlap_len(e1, e2), e1, e2) for e1 in V.edges(ra["rect"]) for e2 in V.edges(rb["rect"])),
                       key=lambda q: q[0])
            L_, e1, e2 = best
            lo, hi = max(e1[2], e2[2]), min(e1[3], e2[3])
            mid = (lo + hi) / 2
            pinned = (ra.get("door_at") or {}).get(b, (rb.get("door_at") or {}).get(a))
            if pinned is not None and lo + 0.4 <= pinned <= hi - 0.4:   # a door the layout places (furnishing)
                mid = pinned
            else:
                pinned = None
            if {ra["occupancy"], rb["occupancy"]} & {"wc", "bathroom", "ensuite", "store", "utility"}:
                w_ = 0.8
            else:
                w_ = 0.9
            if {a, b} == {"parents-bed", "parents-dressing"}:
                w_ = 0.8  # design lead: clears the 0.35 m bedside table with a 100 mm return to the east wall
            if lay["id"] == "D1" and {a, b} == {"kitchen", "dirty-kitchen"}:
                w_ = 1.2  # client-approved wider sliding link between the two work kitchens
            spec["doors"].append({"level": lv, "x": mid if e1[0] == "h" else e1[1], "y": e1[1] if e1[0] == "h" else mid,
                                  "width": w_, "rooms": [a, b], "span": [e1[0], e1[1], lo, hi],
                                  **({"pinned": True} if pinned is not None else {})})
        for rid, l2, seg in lay["entries"]:
            if l2 != lv:
                continue
            sg = V.ENTRY_SEGMENTS[lv][seg]
            e = max(V.edges(lay["rooms"][rid]["rect"]), key=lambda e_: V.overlap_len(e_, sg))
            lo, hi = max(e[2], sg[2]), min(e[3], sg[3])
            mid = (lo + hi) / 2
            spec["doors"].append({"level": lv, "x": mid if e[0] == "h" else e[1], "y": e[1] if e[0] == "h" else mid,
                                  "width": 1.0, "rooms": [rid, "core"], "entrance": True, "span": [e[0], e[1], lo, hi]})
        # Only if the dressing door's leaf reached into the 0.2 m east wall (an earlier 22.05 centre did, by 53 mm) is
        # a recessed jamb reveal needed; at 21.897 the opening ends 100 mm short of the wall and nothing is cut.
        dd = next((d for d in spec["doors"] if set(d["rooms"]) == {"parents-bed", "parents-dressing"}), None)
        if lv == "GF" and dd is not None and dd["x"] + dd["width"] / 2 > V.XR - EXT_T + 1e-6:
            door = next(d for d in spec["doors"] if set(d["rooms"]) == {"parents-bed", "parents-dressing"})
            rebuilt = []
            for wall in spec["walls"]:
                if (wall["level"] == lv and wall["kind"] == "ext" and abs(wall["x0"] - wall["x1"]) < 1e-6
                        and abs(wall["x0"] - (V.XR - EXT_T / 2)) < 1e-6
                        and min(wall["y0"], wall["y1"]) < door["y"] - 0.45
                        and max(wall["y0"], wall["y1"]) > door["y"] + 0.45):
                    a, b = sorted((wall["y0"], wall["y1"]))
                    for ya, yb, thickness, x in ((a, door["y"] - 0.45, EXT_T, wall["x0"]),
                                                  (door["y"] - 0.45, door["y"] + 0.45, 0.147, V.XR - 0.147 / 2),
                                                  (door["y"] + 0.45, b, EXT_T, wall["x0"])):
                        rebuilt.append({**wall, "x0": x, "x1": x, "y0": ya, "y1": yb, "thickness": thickness})
                else:
                    rebuilt.append(wall)
            spec["walls"] = rebuilt
        # garden doors and windows
        ext = lay.get("extension")
        faces = V.window_faces(lv, ext)
        full = full_height_faces(lay, lv)
        for rid, r in lay["rooms"].items():
            if r["level"] != lv:
                continue
            occ = r["occupancy"]
            for e in V.edges(r["rect"]):
                for f in faces:
                    L_ = V.overlap_len(e, f)
                    if L_ < 1.0:
                        continue
                    lo, hi = max(e[2], f[2]), min(e[3], f[3])
                    mid = (lo + hi) / 2
                    x, y = (mid, e[1]) if e[0] == "h" else (e[1], mid)
                    span = [e[0], e[1], lo, hi]                  # axis, face coordinate, usable run
                    fh = full.get((f[0], round(f[1], 3)))
                    if fh == "street" and (r.get("part_of") or any(v.get("part_of") == rid
                                                                    for v in lay["rooms"].values())):
                        continue                         # glazed as one run with its alcove (street_runs, below)
                    if fh and (fh == "end" or occ in vocab.HABITABLE):
                        # floor to beam across the whole column-free run (client 2026-09-26): the basement's street
                        # face (as built today) and the end of the east-yard extension, whatever room is behind it
                        wd = round(L_ - 2 * REVEAL, 2)
                        if occ in ("living", "dining") and not r.get("part_of"):   # an alcove gets a fixed pane
                            spec["doors"].append({"level": lv, "x": x, "y": y, "width": wd, "rooms": [rid, "yard"],
                                                  "garden": True, "full_height": True, "span": span})
                        else:
                            spec["windows"].append({"level": lv, "x": x, "y": y, "width": wd, "sill": 0.0,
                                                    "height": HEAD, "room": rid, "full_height": True, "span": span})
                        continue
                    if occ not in vocab.HABITABLE and occ not in vocab.SANITARY and occ != "utility":
                        continue
                    garden = lv == "B" and occ in ("living", "dining", "kitchen")
                    if garden and occ in ("living", "dining"):
                        spec["doors"].append({"level": lv, "x": x, "y": y, "width": min(2.4, L_ - 2 * REVEAL), "rooms": [rid, "yard"],
                                              "garden": True, "span": span})
                        continue
                    if occ in vocab.HABITABLE:
                        width = L_ - 0.6 if rid == "study-game" else min(2.4, L_ - 2 * REVEAL)
                        spec["windows"].append({"level": lv, "x": x, "y": y, "width": round(width, 2),
                                                "sill": SILL, "height": HEAD - SILL, "room": rid, "span": span})
                    else:
                        spec["windows"].append({"level": lv, "x": x, "y": y, "width": 0.8, "sill": 1.5,
                                                "height": HEAD - 1.5, "room": rid, "span": span})
        for f, lo, hi, rid in street_runs(lay, lv):
            wd = round(hi - lo - 2 * REVEAL, 2)
            mid = (lo + hi) / 2
            x, y = (f[1], mid) if f[0] == "v" else (mid, f[1])
            spec["doors"].append({"level": lv, "x": x, "y": y, "width": wd, "rooms": [rid, "yard"], "garden": True,
                                  "full_height": True, "span": [f[0], f[1], lo, hi]})
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
        _parking(lay, spec, pk2)
    else:
        spec["roofs"] = [list(r) for r in V._exts(lay.get("extension"))]   # east-yard blocks: roof at the GF floor
    _clear_columns(spec)
    for d in spec["doors"]:                            # every door states its leaf height; Revit types are sized to it
        d.setdefault("height", GARDEN_DOOR_H if d.get("garden") else DOOR_H)
    op = S.clashes(st)["slab_opening_needed"]
    spec["gf_opening"] = [v / 1000 for v in op] if op else None
    # round 11: double-height voids (GF rooms marked void): the GF slab is cut there too
    # (the perimeter beams stay: a void on the envelope stops at the beam's inner face)
    bw = V.E.BEAM_W / 1000.0
    spec["gf_voids"] = []
    for r in lay["rooms"].values():
        if r["level"] == "GF" and r.get("void"):
            x0, y0, x1, y1 = r["rect"]
            spec["gf_voids"].append([round(x0 + (bw if abs(x0 - V.X0) < 1e-6 else 0), 3),
                                     round(y0 + (bw if abs(y0 - V.YP) < 1e-6 else 0), 3),
                                     round(x1 - (bw if abs(x1 - V.XR) < 1e-6 else 0), 3),
                                     round(y1 - (bw if abs(y1 - V.YE) < 1e-6 else 0), 3)])
    if lay["id"] == "D1":
        _d1_details(lay, spec)
    glazing_errors = deck_glazing_problems(spec)
    if glazing_errors:
        raise ValueError("; ".join(glazing_errors))
    return spec


def deck_glazing_problems(spec):
    """Exterior bypass sliders onto a deck must carry their glazing and frame intent at spec authoring."""
    out = []
    for d in spec["doors"]:
        if "deck" not in d.get("rooms", ()):
            continue
        if not (d.get("sliding") and d.get("glazed") and d.get("glass") == "clear" and
                d.get("frame") == "aluminium-bronze" and d.get("glass_thickness_m") == .010 and
                d.get("leaf_count") == 2):
            out.append("deck sliding door must have two clear 10 mm glazed leaves and aluminium-bronze frame")
    return out


def _d1_details(lay, spec):
    """Client-approved D1 detail intent, expressed as native-builder inputs (metres from each floor)."""
    from . import villa_furnish as F
    door = next(d for d in spec["doors"] if set(d["rooms"]) == {"kitchen", "dirty-kitchen"})
    door_lo = round(door["x"] - door["width"] / 2, 3)
    pocket_detail = dict(sliding=True, slide_type="telescopic-pocket-3", leaf_count=3, panel_width=0.4,
                         pocket_side="west", pocket_span=[round(door_lo - 0.4, 3), door_lo],
                         pocket_wall_thickness=0.15)
    for key, value in pocket_detail.items():
        if key in door:
            override(door, key, value, "client-approved D1 kitchen dirty-kitchen pocket door detail")
        else:
            fill_defaults(door, {key: value})
    spec["pocket_buildouts"].append(dict(id="kitchen-dirty-pocket", level="B", wall_axis="h", y=door["y"],
                                         x0=door["pocket_span"][0], x1=door["pocket_span"][1],
                                         thickness=0.15, extra_side="dirty-kitchen", height=door["height"]))
    spec["hatches"].append(dict(id="kitchen-sink-pass-through", level="B", wall_axis="h", x0=11.8, x1=13.1,
                                y=-23.591, sill=1.0, head=2.1, above="k-run", closure="roll-up-shutter",
                                shutter_box=[11.8, -23.666, 2.1, 13.1, -23.516, 2.3],
                                card=None, basis="client-approved worktop + upstand and shutter"))
    treads = sorted(([v / 1000 for v in box] for box in spec["stair"] if box[5] - box[2] < 300),
                    key=lambda box: box[0])
    open_y = treads[0][4]
    nosings = [[round((t[0] + t[3]) / 2, 3), open_y, round(t[5], 3)] for t in treads]
    spec["balustrades"].extend([
        dict(id="stair-open-glass", level="B", side="open", stair="party-wall flight",
             material="frameless laminated glass", support="steel stringer", top_edge="clear",
             rail="none", nosing_profile=nosings, height_above_nosing=0.9, thickness_m=None,
             basis="client glass decision; 0.9 m height carried from ASSUMED D1 render, structural size pending"),
        dict(id="stair-wall-handrail", level="B", side="wall", stair="party-wall flight",
             material="wood", support="wall", nosing_profile=[[x, -28.671, z] for x, _, z in nosings],
             height_above_nosing=0.9,
             basis="client wood handrail decision; 0.9 m height carried from ASSUMED D1 render")])
    bath = F.footprint(next(i for i in F.layout(lay, products=False) if i["id"] == "pe-bath"))
    shower = next(i for i in F.layout(lay, products=False) if i["id"] == "gwc-shower")
    wet = F.footprint(shower)
    spec["bath_fittings"].extend([
        dict(id="gwc-rain-head", level="B", room="guest-wc", kind="ceiling-rain-head",
             x=(wet[0] + wet[2]) / 2, y=(wet[1] + wet[3]) / 2, z=2.3, over="gwc-shower"),
        dict(id="gwc-hand-shower", level="B", room="guest-wc", kind="hand-shower",
             x=wet[2] - 0.03, y=(wet[1] + wet[3]) / 2, z=1.1, over="gwc-shower"),
        dict(id="gwc-linear-drain", level="B", room="guest-wc", kind="linear-drain",
             x0=wet[2] - 0.07, x1=wet[2], y0=wet[1] + 0.06, y1=wet[3] - 0.06,
             z=0.0, falls="to linear drain", upstand_m=0.0, enclosure="none",
             basis="ASSUMED 70 mm tile-in grate at wet-zone edge; floor falls, waterproofing/detail pending"),
        dict(id="pe-rain-head", level="GF", room="parents-ensuite", kind="ceiling-rain-head",
             x=(bath[0] + bath[2]) / 2, y=(bath[1] + bath[3]) / 2, z=2.3, over="pe-bath"),
        dict(id="pe-hand-shower", level="GF", room="parents-ensuite", kind="hand-shower",
             x=bath[0] + 0.25, y=bath[1] + 0.05, z=1.1, over="pe-bath"),
        dict(id="pe-bath-screen", level="GF", room="parents-ensuite", kind="fixed-frameless-glass",
             x0=bath[0], x1=bath[0] + 0.9, y=bath[3], sill=0.55, head=2.1,
             transmittance=0.91, ior=1.52,
             optical_note="ASSUMED 10 mm low-iron glass: 0.91 transmittance, 1.52 index of refraction; "
                          "TODO low-iron-glass-optics",
             entry_clear=bath[2] - (bath[0] + 0.9), card="nkba-shower-clear-floor-762")])
    # Approved Document F Vol 1 (2026), cards verified by the lead against the PDF text (Table 1.1 printed p.7,
    # paras 1.21 and 1.51): a room with a shower needs bathroom intermittent extract 15 l/s; 15 min run-on and a
    # 10 mm door undercut; dirty kitchen 30 l/s through its cooker hood ducted to outside (the hood over dk-run's
    # hob), make-up air through the 1.2 m sliding door's running gap.
    for room, fan, door_rooms, kind, rate, card, runon, undercut in (
            ("guest-wc", (10.1, -21.15, 2.45), ["family", "guest-wc"], "extract-fan", None,
             None, 15, 0.010),
            ("dirty-kitchen", (13.827, -20.881, 2.35), ["kitchen", "dirty-kitchen"], "cooker-hood-ducted", 30.0,
             "ukadf-kitchen-intermittent-hood-30", None, None)):
        x, y, z = fan
        if room == "guest-wc":
            card, rate = sanitary_extract_requirement(F.layout(lay, products=False), room)
        spec["ventilation"].append(dict(id=room + "-extract", level="B", room=room, kind=kind,
                                        fan=[x, y, z], duct_route=[[x, y, z], [x, -20.501, z]],
                                        discharge="external-wall", discharge_card="ukadf-extract-to-outside",
                                        makeup_air=dict(path="door-undercut" if undercut else "sliding-door-gap",
                                                        door_rooms=door_rooms, undercut_m=undercut,
                                                        card="ukadf-internal-door-undercut-10" if undercut else None),
                                        operation="intermittent", rate_ls=rate, card=card,
                                        run_on_min=runon, run_on_card="ukadf-runon-timer-15min" if runon else None))


def sanitary_extract_requirement(items, room):
    """Approved Document F intermittent rate follows the room's actual fittings."""
    has_bath_or_shower = any(i["room"] == room and i["type"] in ("bath", "shower_walkin") for i in items)
    return (("ukadf-bathroom-intermittent-15", 15.0) if has_bath_or_shower else
            ("ukadf-sanitary-intermittent-6", 6.0))


def check_wp1_spec(lay, spec=None):
    """Check the D1 client detail geometry before a native builder consumes these fields."""
    if lay["id"] != "D1":
        return []
    from . import villa_furnish as F
    spec = spec if spec is not None else build(lay)
    errors = []
    door = next((d for d in spec["doors"] if set(d["rooms"]) == {"kitchen", "dirty-kitchen"}), None)
    hatch = next((h for h in spec["hatches"] if h["id"] == "kitchen-sink-pass-through"), None)
    if door is None or abs(door["width"] - 1.2) > 0.001 or not door.get("sliding"):
        errors.append("kitchen/dirty-kitchen door: client-approved 1.2 m sliding opening missing")
    if door and door["width"] < 0.914 - 1e-6:
        errors.append("kitchen/dirty-kitchen opening below 0.914 m route body (card mitton-path-of-travel-min)")
    buildout = next((b for b in spec["pocket_buildouts"] if b["id"] == "kitchen-dirty-pocket"), None)
    if door and (buildout is None or buildout["x0"] != door["pocket_span"][0] or
                 buildout["x1"] != door["pocket_span"][1] or buildout["thickness"] < door["pocket_wall_thickness"]):
        errors.append("sliding door pocket needs its 0.15 m local wall buildout")
    if hatch is None:
        errors.append("kitchen sink pass-through missing")
    else:
        run = next(i for i in F.layout(lay, products=False) if i["id"] == "k-run")
        run_fp = F.footprint(run)
        sink = next((a, b) for kind, a, b in F.module_spans(run) if kind == "sink")
        if hatch["sill"] < run["h"] + 0.1 - 1e-6:
            errors.append("hatch sill below 0.90 m worktop + 0.10 m upstand (client decision)")
        if hatch["x0"] >= sink[1] or hatch["x1"] <= sink[0]:
            errors.append("hatch does not overlap the k-run sink")
        if hatch["x0"] < run_fp[0] - 1e-6 or hatch["x1"] > run_fp[2] + 1e-6:
            errors.append("hatch must stay within the k-run worktop width")
        if any(c[0] < hatch["x1"] - 1e-6 and c[2] > hatch["x0"] + 1e-6 and
               c[1] < hatch["y"] + 0.1 and c[3] > hatch["y"] - 0.1 for c in F._columns()):
            errors.append("hatch overlaps a kept structural column")
        if door and hatch["x1"] > door["pocket_span"][0] - 0.1 + 1e-6:
            errors.append("hatch and sliding-door pocket need a 0.10 m clear wall return")
        box = hatch["shutter_box"]
        if hatch["closure"] != "roll-up-shutter" or box[2] < hatch["head"] - 1e-6 or box[5] <= box[2]:
            errors.append("roll-up shutter box must be above the hatch head")
    glass = next((g for g in spec["balustrades"] if g["id"] == "stair-open-glass"), None)
    rail = next((g for g in spec["balustrades"] if g["id"] == "stair-wall-handrail"), None)
    if not glass or glass["material"] != "frameless laminated glass" or glass["top_edge"] != "clear" or glass["rail"] != "none":
        errors.append("client-approved frameless glass stair edge missing")
    if not rail or rail["material"] != "wood" or rail["side"] != "wall":
        errors.append("client-approved wall-side wood handrail missing")
    bath = F.footprint(next(i for i in F.layout(lay, products=False) if i["id"] == "pe-bath"))
    fittings = {x["id"]: x for x in spec["bath_fittings"]}
    guest_shower = next(i for i in F.layout(lay, products=False) if i["id"] == "gwc-shower")
    wet = F.footprint(guest_shower)
    for name in ("gwc-rain-head", "gwc-hand-shower"):
        f = fittings.get(name)
        if f is None or not (wet[0] <= f["x"] <= wet[2] and wet[1] <= f["y"] <= wet[3]):
            errors.append(name + " must remain over the guest wet zone")
    drain = fittings.get("gwc-linear-drain")
    if drain is None or drain.get("upstand_m") != 0 or drain.get("enclosure") != "none" or \
            not (wet[0] <= drain["x0"] < drain["x1"] <= wet[2] and
                 wet[1] <= drain["y0"] < drain["y1"] <= wet[3]):
        errors.append("guest shower needs a flush linear drain and no enclosure")
    for name in ("pe-rain-head", "pe-hand-shower"):
        f = fittings.get(name)
        if f is None or not (bath[0] <= f["x"] <= bath[2] and bath[1] <= f["y"] <= bath[3]):
            errors.append(name + " must remain over the bath")
    screen = fittings.get("pe-bath-screen")
    if screen is None or screen["x0"] < bath[0] - 1e-6 or screen["x1"] > bath[2] + 1e-6 or \
            screen["y"] < bath[1] - 1e-6 or screen["y"] > bath[3] + 1e-6:
        errors.append("fixed bath screen leaves the bath")
    elif bath[2] - screen["x1"] < 0.762 - 1e-6:
        errors.append("bath entry %.3f m, need 0.762 m (card nkba-shower-clear-floor-762)" %
                      (bath[2] - screen["x1"]))
    if screen and (not 0 < screen.get("transmittance", 0) <= 1 or
                   not 1 <= screen.get("ior", 0) <= 2):
        errors.append("bath screen optical properties absent or outside physical bounds "
                      "(ASSUMED low-iron 10 mm; TODO low-iron-glass-optics)")
    vents = {v["room"]: v for v in spec["ventilation"]}
    for room in ("guest-wc", "dirty-kitchen"):
        vent = vents.get(room)
        if vent is None:
            errors.append(room + " extract placeholder missing")
            continue
        r = F.clear_rect(lay, room)
        x, y, _ = vent["fan"]
        end = vent["duct_route"][-1]
        if not (r[0] <= x <= r[2] and r[1] <= y <= r[3]) or end[1] <= lay["rooms"][room]["rect"][3]:
            errors.append(room + " fan or duct does not reach its external wall")
        need = {"guest-wc": sanitary_extract_requirement(F.layout(lay, products=False), "guest-wc"),
                "dirty-kitchen": ("ukadf-kitchen-intermittent-hood-30", 30.0)}[room]
        if vent["card"] != need[0] or (vent["rate_ls"] or 0) < need[1] - 1e-9:
            errors.append("%s extract %s l/s, need %.0f l/s (card %s)" % (room, vent["rate_ls"], need[1], need[0]))
        if room == "guest-wc" and ((vent.get("run_on_min") or 0) < 15 or
                                   (vent["makeup_air"].get("undercut_m") or 0) < 0.010 - 1e-9):
            errors.append("guest-wc needs a 15 min run-on and a 10 mm undercut (ukadf-runon-timer-15min, "
                          "ukadf-internal-door-undercut-10)")
    return errors


FACADE_COLUMNS = None


def facade_columns():
    """Column spans on the villa's faces: {("h", y) or ("v", x): [(lo, hi), ...]} in metres (villa_env.COLUMNS)."""
    global FACADE_COLUMNS
    if FACADE_COLUMNS is None:
        from .. import villa_env as E
        out = {}
        for x0, y0, x1, y1 in ((v / 1000 for v in c) for c in E.COLUMNS):
            for key, lo, hi, near in ((("h", V.YE), x0, x1, abs(y1 - V.YE) < 0.06),
                                      (("h", V.YP), x0, x1, abs(y0 - V.YP) < 0.06),
                                      (("v", V.X0), y0, y1, abs(x0 - V.X0) < 0.06),
                                      (("v", V.XR), y0, y1, abs(x1 - V.XR) < 0.06)):
                if near:
                    out.setdefault(key, []).append((round(lo, 3), round(hi, 3)))
        FACADE_COLUMNS = out
    return FACADE_COLUMNS


def _free_runs(lo, hi, blocks, margin=0.1):
    runs = [(lo, hi)]
    for b0, b1 in blocks:
        nxt = []
        for a, b in runs:
            if b1 + margin <= a or b0 - margin >= b:
                nxt.append((a, b))
            else:
                nxt += [(a, min(b, b0 - margin)), (max(a, b1 + margin), b)]
        runs = [(a, b) for a, b in nxt if b - a > 1e-6]
    return runs


def _clear_columns(spec):
    """Windows and garden doors sit in the widest stretch of their facade run clear of the kept columns and of
    other openings on that run (client review r7 class: an opening through a column was never checked)."""
    cols = facade_columns()
    fixed = [d for d in spec["doors"] if d.get("fixed_span")]
    keep_w = []
    for o in [w for w in spec["windows"]] + [d for d in spec["doors"] if d.get("span")]:
        ax, c, lo, hi = o["span"]
        blocks = [bl for (a, cc), spans in cols.items() if a == ax and abs(cc - c) < 0.06 for bl in spans]
        blocks += [tuple(d["fixed_span"]) for d in fixed if d["level"] == o["level"] and d["fixed_span_face"] == [ax, c]]
        is_door = o in spec["doors"] and not o.get("garden")
        if o.get("pinned"):                            # placed by the layout: keep it unless it hits a column
            p = o["x"] if ax == "h" else o["y"]
            if not any(s0 - 0.05 < p + o["width"] / 2 and p - o["width"] / 2 < s1 + 0.05 for s0, s1 in blocks):
                continue
        runs = _free_runs(lo, hi, blocks, margin=0.05 if is_door else 0.1)
        min_w = 1.2 if o.get("garden") else 0.6
        if not runs:
            if not is_door:
                o["dropped"] = "no column-free run"
            continue                                   # a door with no free run stays: opening_problems reports it
        a, b = max(runs, key=lambda r: r[1] - r[0])
        if is_door:
            if b - a < o["width"] + 0.1 - 1e-9:       # leaf + a 50 mm frame each side
                continue                               # does not fit: left in place for the post-condition to catch
            mid = round((a + b) / 2, 3)
        else:
            width = round(min(o["width"], b - a - 0.2), 2)
            if width < min_w:
                o["dropped"] = "column-free run %.2f m" % (b - a)
                continue
            mid = round((a + b) / 2, 3)
            override(o, "width", width, "column-free facade run limits opening width")
        if ax == "h":
            override(o, "x", mid, "centre opening in the selected column-free facade run")
        else:
            override(o, "y", mid, "centre opening in the selected column-free facade run")
    spec["dropped"] = [{"room": o.get("room") or "/".join(o.get("rooms", [])), "level": o["level"],
                        "reason": o["dropped"]} for o in spec["windows"] + spec["doors"] if "dropped" in o]
    spec["windows"] = [w for w in spec["windows"] if "dropped" not in w]
    spec["doors"] = [d for d in spec["doors"] if "dropped" not in d]


def opening_problems(spec):
    """Post-condition: no window or door (by its width) overlaps a kept column on the facade line it sits in."""
    cols, out = facade_columns(), []
    for o in spec["windows"] + spec["doors"]:
        for (ax, c), spans in cols.items():
            on = abs((o["y"] if ax == "h" else o["x"]) - c) < 0.06
            if not on:
                continue
            m = o["x"] if ax == "h" else o["y"]
            for b0, b1 in spans:
                if m - o["width"] / 2 < b1 - 1e-6 and m + o["width"] / 2 > b0 + 1e-6:
                    out.append("%s at %s %.2f (w %.2f, %s) overlaps the column %.3f-%.3f"
                               % ("door" if o in spec["doors"] else "window", ax, m, o["width"], o.get("level"), b0, b1))
    return out


def _parking(lay, spec, pk2):
    from . import villa_parking as P
    from .. import villa_env as E
    street, zb = -1.2, LEVELS_Z["B"]                   # model z of the street and the basement FFL (m)
    r0, _, r1, _ = pk2["ramp"]
    d0, y0, d1, y1 = pk2["deck"]
    deck_z = street + pk2["deck_top"]
    spec["parking2"] = {
        "ramp": {"profile": [[x, round(street + z, 3)] for x, z in pk2["profile"]], "y0": y0, "y1": y1,
                 "thick": P.BUILDUP},
        "deck": {"x0": d0, "x1": d1, "y0": y0, "y1": y1, "z_top": deck_z, "thick": P.BUILDUP},
        "cars": [[d0 + 0.2 + i * 4.9, (y0 + y1) / 2 - 0.9, d0 + 0.2 + i * 4.9 + 4.6, (y0 + y1) / 2 + 0.9,
                  deck_z, deck_z + 1.45] for i in range(pk2["cars"])]}
    beyond = pk2.get("roof_beyond_deck")
    spec["roofs"] = [list(beyond)] if beyond else []   # the rooms beyond a one-car deck: roof level with the deck
    # walls of the rooms under the ramp and deck stop at the soffit above them (client review r7: they came through
    # the ramp): a cross wall takes the clear height at its low face; a wall along the ramp is split at the ramp's
    # slope breaks, takes the clear height at each piece's low end and gets a sloped infill up to the soffit
    walls, spec["infills"] = [], []
    for w in spec["walls"]:
        if w["level"] != "B" or max(w["y0"], w["y1"]) <= V.YE + EXT_T:
            walls.append(w)                            # inside the villa, or on its east face line
            continue
        if abs(w["y0"] - w["y1"]) > 1e-6:              # cross wall (constant x)
            walls.append(dict(w, height=round(min(WALL_H, P.clear_at(w["x0"] - w["thickness"] / 2)), 3)))
            continue
        a, b = sorted((w["x0"], w["x1"]))
        pts = P.soffit_points(a, b)
        for (s_, h0), (e_, h1) in zip(pts, pts[1:]):
            walls.append(dict(w, x0=s_, x1=e_, height=round(min(WALL_H, h0), 3)))
            if h1 - h0 > 0.005:
                t = w["thickness"] / 2
                spec["infills"].append({"what": "wall top up to the ramp soffit", "y0": round(w["y0"] - t, 3),
                                        "y1": round(w["y0"] + t, 3), "profile": [
                                            [s_, round(zb + h0, 3)], [e_, round(zb + h0, 3)], [e_, round(zb + h1, 3)]]})
    spec["walls"] = walls
    # doors into the rooms under the ramp: at the wall's high end, leaf sized to the clear height
    ext_ids = {r["id"] for r in lay["rooms"].values() if r.get("ext")}
    for d in spec["doors"]:
        ids = [i for i in d.get("rooms", []) if i in ext_ids]
        if d["level"] != "B" or not ids:
            continue
        occ = lay["rooms"][ids[-1]]["occupancy"]
        ra, rb_ = (lay["rooms"][i]["rect"] for i in d["rooms"])
        d.pop("span", None)                            # placed here, by clear height, not by _clear_columns
        if abs(d["y"] - V.YE) < 1e-6:                  # on the villa's east face: slides along x
            lo, hi = max(ra[0], rb_[0]), min(ra[2], rb_[2])
            runs = [r for r in _free_runs(lo, hi, facade_columns().get(("h", V.YE), []), margin=0.0)
                    if r[1] - r[0] >= d["width"] + 0.2 - 1e-9] or [(lo, hi)]
            a_, b_ = max(runs, key=lambda r: r[1])     # the highest stretch the door fits in
            d["x"], d["height"], d["clear"], d["fit"] = P.door_fit(a_, b_, d["width"], occ)
        else:                                          # a cross wall: the clear height is fixed there
            d["height"], d["clear"], d["fit"] = P.leaf_for(min(P.clear_at(d["x"] - 0.1), P.clear_at(d["x"] + 0.1)), occ)
    # the kept NE yard wall is the store's side from the gate to the villa: no new wall there, only an infill from
    # the wall top (1.40 m) up to the ramp soffit, which follows the ramp's slope breaks
    wx0, wy0, wx1, wy1 = (v / 1000 for v in E.YARD_WALL)
    spec["walls"] = [w for w in spec["walls"] if not (
        w["level"] == "B" and abs(w["y0"] - w["y1"]) < 1e-6 and abs(w["y0"] - V.YE) < EXT_T
        and max(w["x0"], w["x1"]) <= wx1 + 1e-6)]
    top = zb + E.YARD_WALL_H / 1000
    soff = [[x, round(zb + c, 3)] for x, c in P.soffit_points(wx0, wx1)]
    spec["infill"] = {"y0": wy0, "y1": wy1, "profile": [[wx0, top], [wx1, top]] + soff[::-1]}
    # the GF door onto the deck: a bypass sliding door between the east-face columns, sill level with the deck
    dd = lay.get("deck_door")
    if dd:
        spec["doors"].append({"level": "GF", "x": round((dd["x0"] + dd["x1"]) / 2, 3), "y": V.YE,
                              "width": dd["width"], "height": P.DOOR_H, "rooms": [dd["room"], "deck"],
                              "sliding": True, "slide_type": "bypass", "glazed": True,
                              "frame": "aluminium-bronze", "glass": "clear", "glass_thickness_m": 0.010,
                              "leaf_count": 2, "panel_width": dd["width"] / 2,
                              "fixed_span": [dd["x0"], dd["x1"]], "fixed_span_face": ["h", V.YE]})
    # GF windows beside the ramp and deck: sills above the eye of a person standing on them (privacy)
    eye = max(z for _, z in pk2["profile"]) + 1.6 - 1.2  # above the GF FFL
    for wdw in spec["windows"]:
        if (wdw["level"] == "GF" and wdw["room"] != "study-game" and abs(wdw["y"] - V.YE) < 1e-6
                and r0 - 1e-6 <= wdw["x"] <= d1 + 1e-6):
            sill = round(eye + 0.1, 2)
            override(wdw, "sill", sill, "raise ramp-facing window above standing eye level for privacy")
            override(wdw, "height", round(HEAD - sill, 2),
                     "retain the authored window head after privacy sill rises")
    # guarding (1.1 m, card ukadk-guarding-height-external): the ramp's west edge over the sunken north patio, the
    # deck and the ramp's top along the east fence where the fence is under 1.1 m above them, and the deck end
    g, rails = 1.1, []
    prof = [[x, round(street + z, 3)] for x, z in pk2["profile"]]
    patio = [p for p in prof if p[0] <= wx1 + 1e-6] + [[wx1, round(street + P.top_at(wx1), 3)]]
    rails.append({"what": "guard rail on the ramp edge over the north patio", "y0": round(V.YE - 0.05, 3),
                  "y1": V.YE, "profile": [[x, z] for x, z in patio] + [[x, round(z + g, 3)] for x, z in patio[::-1]]})
    fence_top = zb + E.FENCE_H / 1000
    x_low = next((x for x in [i / 100 for i in range(int(r0 * 100), int(d1 * 100) + 1)]
                  if fence_top - (street + P.top_at(x)) < g - 1e-9), None)
    end = beyond[2] if beyond else d1
    if x_low is not None:
        zs = [[x_low, round(street + P.top_at(x_low), 3)]] + [p for p in prof if p[0] > x_low] + [[end, deck_z]]
        rails.append({"what": "guard rail along the east fence (fence under 1.1 m above the deck)",
                      "y0": round(y1 - 0.10, 3), "y1": round(y1 - 0.05, 3),
                      "profile": zs + [[x, round(z + g, 3)] for x, z in zs[::-1]]})
    rails.append({"what": "guard rail at the deck end over the yard", "y0": y0, "y1": y1, "profile": [
        [end - 0.05, deck_z], [end, deck_z], [end, round(deck_z + g, 3)], [end - 0.05, round(deck_z + g, 3)]]})
    spec["rails"] = rails


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
        if abs(d["y"] - V.YE) < 1e-6:                  # in the east face: the leaf runs along x under the slope
            low = min(P.clear_at(d["x"] - d["width"] / 2), P.clear_at(d["x"] + d["width"] / 2))
        else:                                          # in a cross wall: both faces of the wall
            low = min(P.clear_at(d["x"] - 0.1), P.clear_at(d["x"] + 0.1))
        if d["height"] + P.HEAD_ZONE > low + tol:
            out.append("door x %.2f (%s): %.2f m leaf + %.2f frame under %.2f m clear"
                       % (d["x"], "/".join(d.get("rooms") or []), d["height"], P.HEAD_ZONE, low))
    return out


def window_credit_problems(lay, windows, doors):
    """Post-condition (round 8): every habitable room the critic credits with its own window has a window or a
    garden door in what is built (the spec, or Revit's read-back). The column pass once dropped a kitchen window
    while the critic still counted the kitchen as lit."""
    res = V.critique(lay)
    w = [c for c in res["checks"] if c["check"] == "window"][0]
    unlit = set(w.get("rooms") or []) | set(w.get("borrowed_light") or [])
    have = {o.get("room") for o in windows} | {r for d in doors if d.get("garden") for r in d.get("rooms", [])}
    have |= {rid for rid, r in lay["rooms"].items() if r.get("part_of") in have}     # an alcove shares its room's
    out = []
    for rid, r in lay["rooms"].items():
        if r["occupancy"] in vocab.HABITABLE and rid not in unlit and rid not in have:
            out.append("%s (%s) is credited with a window but none is built" % (rid, r["level"]))
    return out
