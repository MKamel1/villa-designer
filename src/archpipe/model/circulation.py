"""Staged-furniture circulation: the widest path a body has between every door approach of every room cluster, with
the furniture AS STAGED in the design model (loose chairs and stools, the dressed bed's duvet) and not only the
checked plan pieces.

Why it exists: `villa_furnish.check` raster-tests routes against plan pieces taller than 0.3 m. A pulled-out vanity
chair (a separate element, `villa_furnish3d.extras`) was not in it, so the principal
bedroom passed while the walkthrough found a 0.46 m gap on the only way to the dressing door (docs/lessons/DF.md).

Requirements are the project's existing ones, not new figures: 0.914 m path of travel (card
mitton-path-of-travel-min), 0.750 m inside a bedroom (card ukadm-bedroom-route-750) and for the private dressing
suite (project waiver already recorded in villa_furnish._route_problems). Achieved width is the diameter of the widest
disc that can travel the route (clearance field at CELL resolution, so +-CELL/2)."""
import heapq
import json
from pathlib import Path

import numpy as np

from ..concept import villa_furnish as F
from ..concept import villa_furnish3d as F3

CELL = 0.02
ROOT = Path(__file__).resolve().parents[3]
DUVET_FALLBACK = 0.10   # ASSUMED m beyond a bed where it has no measured duvet (measured: pb-bed 0.104 E / 0.143 W)


def _measured_duvets():
    p = ROOT / "knowledge/flythrough/evaluated-obstacles.json"
    if not p.exists():
        return {}
    return {b["id"][len("cloth-duvet-"):]: (b["lo"][0], b["lo"][1], b["hi"][0], b["hi"][1])
            for b in json.loads(p.read_text())["boxes"] if b["id"].startswith("cloth-duvet-")}


def staged_items(lay, items=None, dressed=False):
    """The plan pieces plus what stands loose around them: chairs/stools as world boxes (`extras`, honouring each
    piece's own staging). dressed=True also adds each bed's duvet envelope (measured where the walkthrough measured it,
    else DUVET_FALLBACK beyond the bed): a sensitivity, because the cloth is render dressing and its drape is simulated.
    Pseudo-items are footprint-compatible dicts."""
    items = list(items if items is not None else F.layout(lay))
    duvets = _measured_duvets()
    out = []
    for it in items:
        out.append(it)
        if dressed and it["type"].startswith("bed_"):
            x0, y0, x1, y1 = F.footprint(it)
            box = duvets.get(it["id"]) or (x0 - DUVET_FALLBACK, y0 - DUVET_FALLBACK, x1 + DUVET_FALLBACK, y1 + DUVET_FALLBACK)
            out.append(dict(it, id=it["id"] + "+duvet", type="duvet", cx=(box[0] + box[2]) / 2, cy=(box[1] + box[3]) / 2,
                            w=box[2] - box[0], d=box[3] - box[1], rot=0, extra_of=it["id"]))
        for suf, parts in F3.extras(it):
            ws = [F3.to_world(it, b) for _, b in parts]
            x0, y0, x1, y1 = min(w[0] for w in ws), min(w[1] for w in ws), max(w[3] for w in ws), max(w[4] for w in ws)
            out.append(dict(id="%s#%s" % (it["id"], suf), room=it["room"], level=it["level"], type="loose_seat",
                            cx=(x0 + x1) / 2, cy=(y0 + y1) / 2, w=x1 - x0, d=y1 - y0, rot=0,
                            h=max(w[5] for w in ws), extra_of=it["id"]))
    return out


def _required(lay, cl):
    if all(lay["rooms"][c]["occupancy"] == "bedroom" for c in cl) or cl == {"parents-dressing", "parents-dressing-ext"}:
        return min(F.BODY, F.BEDROOM_ROUTE), "ukadm-bedroom-route-750 (private dressing: project waiver)"
    return F.BODY, "mitton-path-of-travel-min"


def _widest(clear, ok_free, start_mask, cell):
    """Widest-path (max-min clearance) from the start cells to every cell: heap over cells, best clearance first."""
    best = np.full(clear.shape, -1.0)
    heap = []
    for i, j in zip(*np.nonzero(start_mask & ok_free)):
        best[i, j] = clear[i, j]
        heap.append((-clear[i, j], i, j))
    heapq.heapify(heap)
    nx, ny = clear.shape
    while heap:
        c, i, j = heapq.heappop(heap)
        c = -c
        if c < best[i, j]:
            continue
        for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
            if 0 <= a < nx and 0 <= b < ny and ok_free[a, b]:
                v = min(c, clear[a, b])
                if v > best[a, b]:
                    best[a, b] = v
                    heapq.heappush(heap, (-v, a, b))
    return best


def routes(lay=None, items=None, level=None, dressed=False):
    """[{cluster, from, to, required, source, achieved, ok}] for every door approach of every cluster, as staged.
    `achieved` is 0.0 where there is no path at all."""
    lay = lay or F.R.design("D1")
    sp = F.RS.build(lay)
    items = staged_items(lay, items, dressed)
    out, done = [], set()
    for rid, r in lay["rooms"].items():
        if rid in done or (level and r["level"] != level):
            continue
        cl = F._cluster(lay, rid)
        done |= cl
        lv = r["level"]
        rects = [lay["rooms"][c]["rect"] for c in cl]
        x0, y0 = min(q[0] for q in rects), min(q[1] for q in rects)
        x1, y1 = max(q[2] for q in rects), max(q[3] for q in rects)
        nx, ny = int((x1 - x0) / CELL) + 1, int((y1 - y0) / CELL) + 1
        X, Y = np.meshgrid(x0 + (np.arange(nx) + 0.5) * CELL, y0 + (np.arange(ny) + 0.5) * CELL, indexing="ij")
        free = np.zeros((nx, ny), bool)
        for a, b, c, d in rects:
            free |= (X >= a - 1e-9) & (X < c - 1e-9) & (Y >= b - 1e-9) & (Y < d - 1e-9)
        obst = [F.footprint(it) for it in items if it["room"] in cl and it["h"] >= 0.3 and not it.get("mounting_obstacle")]
        obst += F._columns() + F._walls(sp, lv)
        obst += [lay["rooms"][c]["rect"] for c in cl if lay["rooms"][c]["occupancy"] == "stair" and lv == "B"]
        if lv == "GF":
            obst += ([sp["gf_opening"]] if sp.get("gf_opening") else []) + sp.get("gf_voids", [])
        for a, b, c, d in obst:
            free &= ~((X > a) & (X < c) & (Y > b) & (Y < d))
        need, src = _required(lay, cl)
        clear = np.full((nx, ny), np.inf)
        for a, b, c, d in obst:
            if c < x0 - 2 or a > x1 + 2 or d < y0 - 2 or b > y1 + 2:
                continue
            clear = np.minimum(clear, np.hypot(np.maximum(np.maximum(a - X, X - c), 0.0),
                                               np.maximum(np.maximum(b - Y, Y - d), 0.0)))
        nodes = []
        for z in F._door_approaches(sp, lay, lv):
            zc = ((z["rect"][0] + z["rect"][2]) / 2, (z["rect"][1] + z["rect"][3]) / 2)
            if any(q[0] <= zc[0] <= q[2] and q[1] <= zc[1] <= q[3] for q in rects):
                nodes.append(("door " + z["door"], z["rect"]))
        def mask(rect):
            # as villa_furnish._route_problems.touching: a body reaches a zone when its disc overlaps the zone by up to
            # 0.1 m each way (a body grazing the zone's edge is not in it), not only when its centre is inside
            ex, ey = min(0.1, (rect[2] - rect[0]) / 2 - 1e-6), min(0.1, (rect[3] - rect[1]) / 2 - 1e-6)
            dx = np.maximum(np.maximum(rect[0] + ex - X, X - (rect[2] - ex)), 0.0)
            dy = np.maximum(np.maximum(rect[1] + ey - Y, Y - (rect[3] - ey)), 0.0)
            return np.hypot(dx, dy) < need / 2
        ok_free = free & (clear > 0)
        for name, rect in nodes:                      # the approach itself: a body must fit in front of the door
            m = mask(rect) & ok_free
            width = 2 * float(clear[m].max()) if m.any() else 0.0
            out.append(dict(cluster="+".join(sorted(cl)), level=lv, frm=name, to="its own approach", required=need,
                            source=src, achieved=round(width, 3), ok=width >= need - CELL))
        if len(nodes) < 2:
            continue
        best = _widest(clear, ok_free, mask(nodes[0][1]), CELL)
        for name, rect in nodes[1:]:
            m = mask(rect) & (best > 0)
            width = 2 * float(best[m].max()) if m.any() else 0.0
            out.append(dict(cluster="+".join(sorted(cl)), level=lv, frm=nodes[0][0], to=name, required=need,
                            source=src, achieved=round(width, 3), ok=width >= need - CELL))
    return out


def pinches(lay=None, items=None, dressed=False):
    """The routes that fail, with achieved versus required."""
    return [r for r in routes(lay, items, dressed=dressed) if not r["ok"]]


def describe(r):
    return "%s: %s -> %s: %.3f m clear where %.3f m is needed (%s)" % (
        r["cluster"], r["frm"], r["to"], r["achieved"], r["required"], r["source"])
