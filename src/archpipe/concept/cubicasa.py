"""Room graphs and window presence from CubiCasa5k floor plans (CC BY-NC-SA 4.0).

Kalervo et al., "CubiCasa5K: A Dataset and an Improved Multi-Task Model for
Floorplan Image Analysis" (2019), https://zenodo.org/record/2613548. Real
Finnish dwelling plans with labelled room polygons, doors and windows, in
image pixels (no absolute scale). Used ONLY to calibrate the critic's
scale-free checks (reachability, windows, privacy base rates), never as
design content.

Extraction is by rasterising the SVG polygons:
- a door joins the rooms its (slightly grown) polygon touches, or a room and
  the outside when it touches only one room (an entrance);
- rooms whose pixels meet with no wall between them are joined as an open
  connection (open-plan kitchen/living);
- a window counts for the room its grown polygon touches.
"""
from __future__ import annotations

import re
from xml.dom import minidom

import numpy as np
from PIL import Image, ImageDraw

HABITABLE = {"Bedroom", "LivingRoom", "Lounge", "Kitchen", "Dining", "EatingArea"}
PRIVATE = {"Bedroom"}
PUBLIC = {"LivingRoom", "Lounge", "Kitchen", "Dining", "EatingArea"}
CIRCULATION = {"Entry", "HallWay", "DraughtLobby", "Hall", "StairWell"}
SANITARY = {"Bath", "Sauna"}
OUTSIDE_ROOMS = {"Outdoor"}
GROW = 3            # px a door/window polygon is grown to reach the rooms beside the wall
OPEN_MIN = 6        # px of direct room-to-room contact that counts as an open connection


def _points(el):
    pts = []
    for poly in el.getElementsByTagName("polygon"):
        raw = [float(v) for v in re.split(r"[ ,]+", poly.getAttribute("points").strip()) if v]
        pts.append(list(zip(raw[0::2], raw[1::2])))
        break
    return pts[0] if pts else None


def _floors(svg):
    floors = [g for g in svg.getElementsByTagName("g") if g.getAttribute("class").split(" ")[0] == "Floor"]
    return floors or [svg.documentElement]


def parse(svg_path):
    """One record per floor: rooms {id: type}, polygons, doors, windows (pixel polygons)."""
    svg = minidom.parse(str(svg_path))
    out = []
    for fi, floor in enumerate(_floors(svg)):
        rooms, doors, windows, walls = {}, [], [], []
        for g in floor.getElementsByTagName("g"):
            cls, gid = g.getAttribute("class"), g.getAttribute("id")
            if cls.startswith("Space "):
                pts = _points(g)
                if pts and len(pts) >= 3:
                    rooms[f"r{len(rooms)}"] = {"type": cls.split(" ")[1], "poly": pts}
            elif gid in ("Door", "Window"):
                pts = _points(g)
                if pts:
                    (doors if gid == "Door" else windows).append(pts)
            elif gid in ("Wall", "Railing"):
                pts = _points(g)
                if pts:
                    walls.append(pts)
        if rooms:
            out.append({"floor": fi, "rooms": rooms, "doors": doors, "windows": windows, "walls": walls})
    return out


def _canvas(rec):
    xs = [x for r in rec["rooms"].values() for x, _ in r["poly"]] + [x for p in rec["walls"] for x, _ in p]
    ys = [y for r in rec["rooms"].values() for _, y in r["poly"]] + [y for p in rec["walls"] for _, y in p]
    return int(max(xs)) + 20, int(max(ys)) + 20


def _mask(size, polys, grow=0):
    im = Image.new("L", size, 0)
    d = ImageDraw.Draw(im)
    for p in polys:
        d.polygon(p, fill=1, outline=1)
    a = np.array(im, dtype=bool)
    for _ in range(grow):
        b = a.copy()
        b[1:] |= a[:-1]; b[:-1] |= a[1:]; b[:, 1:] |= a[:, :-1]; b[:, :-1] |= a[:, 1:]
        a = b
    return a


def graph(rec):
    """The critic's graph form for one floor, plus per-room window counts and extraction notes."""
    size = _canvas(rec)
    ids = list(rec["rooms"])
    label = np.full((size[1], size[0]), -1, dtype=np.int32)
    for i, rid in enumerate(ids):
        m = _mask(size, [rec["rooms"][rid]["poly"]])
        label[m & (label < 0)] = i
    wall = _mask(size, rec["walls"])
    edges, entrances = set(), []
    for d in rec["doors"]:
        m = _mask(size, [d], GROW)
        hit = sorted({ids[v] for v in np.unique(label[m]) if v >= 0})
        inside = [h for h in hit if rec["rooms"][h]["type"] not in OUTSIDE_ROOMS]
        if len(inside) >= 2:
            for a in inside:
                for b in inside:
                    if a < b:
                        edges.add((a, b))
        elif len(inside) == 1:
            entrances.append(inside[0])
    # open connections: horizontally or vertically adjacent pixels of two different rooms, no wall between
    for axis in (0, 1):
        a = label[:-1, :] if axis == 0 else label[:, :-1]
        b = label[1:, :] if axis == 0 else label[:, 1:]
        wa = wall[:-1, :] if axis == 0 else wall[:, :-1]
        touch = (a >= 0) & (b >= 0) & (a != b) & ~wa
        pairs, counts = np.unique(np.stack([np.minimum(a[touch], b[touch]), np.maximum(a[touch], b[touch])]),
                                  axis=1, return_counts=True)
        for (x, y), n in zip(pairs.T, counts):
            if n >= OPEN_MIN:
                edges.add((ids[x], ids[y]))
    windows = {rid: 0 for rid in ids}
    for w in rec["windows"]:
        m = _mask(size, [w], GROW)
        for v in np.unique(label[m]):
            if v >= 0:
                windows[ids[v]] += 1
    types = {rid: r["type"] for rid, r in rec["rooms"].items()}
    kind = {rid: ("private" if t in PRIVATE else "public" if t in PUBLIC else "circulation" if t in CIRCULATION
                  else "exterior" if t in OUTSIDE_ROOMS else "service") for rid, t in types.items()}
    ent = sorted(entrances, key=lambda r: (types[r] not in CIRCULATION, r))
    return {"rooms": kind, "types": types, "connections": [list(e) for e in sorted(edges)],
            "entrance": ent[0] if ent else None, "sanitary": [r for r, t in types.items() if t in SANITARY],
            "windows": windows}


def window_check(g):
    dark = sorted(r for r, t in g["types"].items() if t in HABITABLE and not g["windows"][r])
    return {"check": "window", "status": "fail" if dark else "pass", "rooms": dark}
