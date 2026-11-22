"""Seeded mutation set (pre-registered in docs/lanes/RV1-checks.md). Each mutation edits an in-memory copy of the D1 scene.

`run_mutations(world, model, ...)` returns rows: {id, check, kind: mutation|negative, expect, caught, detail}.
A mutation is CAUGHT when the check reports a failing subject the unmutated scene did not (or a worse one).
Nothing is retried or tuned: a miss is a miss.
"""
from __future__ import annotations

import numpy as np

from . import checks as C
from .geom import aabb
from .intended import of_kind
from .world import Element, World


def _copy(w: World) -> World:
    return World(dict(w.elements), list(w.unowned), w.source, w.sha256, dict(w.mesh_tris))


def _edit(w: World, eid: str, fn, part_filter=None) -> World:
    """Return a copy of `w` where the element's parts' triangles are replaced by fn(tris)."""
    w2 = _copy(w)
    e = w.elements[eid]
    parts = [(p[0], p[1], p[2], p[3], fn(p[4]) if (part_filter is None or part_filter(p)) else p[4]) for p in e.parts]
    w2.elements[eid] = Element(eid, parts)
    return w2


def _shift(d):
    d = np.asarray(d, float)
    return lambda t: t + d


def _fails(fs):
    return {f.subject: (f.achieved if f.achieved is not None else 0.0) for f in fs if f.status == "fail"}


def caught(base, mut, slack=1.0, only=None):
    """`only`: judge just the failing subjects that contain this text (a shifted stair also meets other elements)."""
    nb, nm = _fails(base), _fails(mut)
    if only:
        nb, nm = {k: v for k, v in nb.items() if only in k}, {k: v for k, v in nm.items() if only in k}
    new = sorted(set(nm) - set(nb))
    worse = sorted(k for k in nb if k in nm and abs(nm[k]) > abs(nb[k]) + slack)
    return bool(new or worse), new + worse


def _nearest_column_shift(w, eid, margin, model):
    """Axis-aligned shift that moves element `eid` into its nearest kept column by `margin` (negative margin = leaves a gap).
    The column faces come from the intended model (scene face-attribution noise makes a scene column box unreliable)."""
    A = w.elements[eid].box
    best = None
    for c in of_kind(model, "column"):
        cid = c["id"]
        p = c["params"]
        B = (p["x0_mm"] / 1e3, p["y0_mm"] / 1e3, -3.0, p["x1_mm"] / 1e3, p["y1_mm"] / 1e3, 6.0)
        for ax in (0, 1):
            o = 1 - ax
            if min(A[o + 3], B[o + 3]) - max(A[o], B[o]) <= 0 or min(A[5], B[5]) - max(A[2], B[2]) <= 0:
                continue
            gap_pos = B[ax] - A[ax + 3]     # move +ax to reach the column's low face
            gap_neg = A[ax] - B[ax + 3]
            for g, sgn in ((gap_pos, 1), (gap_neg, -1)):
                if g >= -1e-9 and (best is None or g < best[0]):
                    best = (g, ax, sgn, cid)
    if best is None:
        return None
    g, ax, sgn, cid = best
    d = np.zeros(3)
    d[ax] = sgn * (g + margin)
    return d, cid, g


def run_mutations(w: World, model: dict, hosts=None, env=None, areas=None, levels=None, host_ids=None, baselines=None, contract=None):
    rows = []
    B = baselines or {}

    def rec(mid, check, kind, expect, base, mut, detail="", only=None):
        c, why = caught(base, mut, only=only)
        rows.append(dict(id=mid, check=check, kind=kind, expect=expect, caught=c,
                         ok=(c if expect == "catch" else not c), via=why[:4], detail=detail))

    # M1 wall into the ramp
    base = B.get("K02") or C.k02_wall_slab(w)
    w2 = _edit(w, "wall-B-ext-07", _shift((0, -0.5, 0)))
    rec("M1", "K02", "mutation", "catch", base, C.k02_wall_slab(w2), "wall-B-ext-07 translated (0,-0.5,0) into the ramp")
    w2 = _edit(w, "wall-B-ext-07", _shift((0, 0.5, 0)))
    rec("N-K02", "K02", "negative", "quiet", base, C.k02_wall_slab(w2), "wall moved 0.5 m away from the ramp")

    # M1b (added after the first run: M1 moved a wall that was sized to the soffit, which is valid geometry): wall 0.7 m taller
    def taller(dz):
        def g(t):
            top = t.reshape(-1, 3)[:, 2].max()
            t = t.copy(); t[..., 2] = np.where(t[..., 2] > top - 1e-6, t[..., 2] + dz, t[..., 2])
            return t
        return g
    w2 = _edit(w, "wall-B-int-11", taller(0.7))
    rec("M1b", "K02", "mutation", "catch", base, C.k02_wall_slab(w2), "cross wall wall-B-int-11 (top 10 mm under the ramp soffit) raised 0.7 m through the ramp")

    # M2 door head against the soffit
    did = "door-B-cinema-store-ramp"
    base = B.get("K04") or C.k04_door_soffit(w, model)
    clr = next(f.achieved for f in base if f.subject == did) / 1000

    def lift(dz):
        def f(t):
            mid = (t.reshape(-1, 3)[:, 2].min() + t.reshape(-1, 3)[:, 2].max()) / 2
            t = t.copy()
            t[..., 2] = np.where(t[..., 2] > mid, t[..., 2] + dz, t[..., 2])
            return t
        return f
    rec("M2", "K04", "mutation", "catch", base, C.k04_door_soffit(_edit(w, did, lift(0.30)), model),
        f"door-B-cinema-store-ramp head raised 0.30 m (clearance was {clr*1000:.0f} mm)")
    rec("N-K04", "K04", "negative", "quiet", base, C.k04_door_soffit(_edit(w, did, lift(clr - 0.005)), model),
        "head raised to leave 5 mm below the soffit")

    # M3 window removed while credited / K05b glass narrowed
    wid = "window-GF-kids-a-3"
    base = B.get("K05") or C.k05_openings(w, model)
    w2 = _copy(w); del w2.elements[wid]
    rec("M3", "K05", "mutation", "catch", base, C.k05_openings(w2, model), "all surfaces of window-GF-kids-a-3 deleted")

    def narrow(f):
        def g(t):
            c = t.reshape(-1, 3).mean(0)
            t = t.copy()
            t[..., 0] = c[0] + (t[..., 0] - c[0]) * f   # kids-a-3 is in a wall along x
            return t
        return g
    gl = lambda p: p[2] == "glass-clear"
    rec("M-K05b", "K05", "mutation", "catch", base, C.k05_openings(_edit(w, wid, narrow(0.5), gl), model), "glass width halved")
    rec("N-K05", "K05", "negative", "quiet", base, C.k05_openings(_edit(w, wid, narrow(1 - 0.003 / 2.4), gl), model), "glass 3 mm narrower")

    # M4 fixture through the ceiling / K07b datum
    lid = "lum-PEN-GLOBE-kitchen-01"
    base = B.get("K07") or C.k07_fixture_ceiling(w, model)
    rec("M4", "K07", "mutation", "catch", base, C.k07_fixture_ceiling(_edit(w, lid, _shift((0, 0, 0.6))), model), "pendant raised 0.60 m")
    rec("M-K07b", "K07", "mutation", "catch", base, C.k07_fixture_ceiling(_edit(w, lid, _shift((0, 0, -0.25))), model), "emitter datum 0.25 m too low")
    rec("N-K07", "K07", "negative", "quiet", base, C.k07_fixture_ceiling(_edit(w, lid, _shift((0, 0, -0.005))), model), "pendant 5 mm low")

    # M5 tread into a column / negatives / K03
    base = B.get("K01") or C.k01_stair_structure(w)
    sh = _nearest_column_shift(w, "stair-main", 0.030, model)
    if sh is None:
        rows.append(dict(id="M5", check="K01", kind="mutation", expect="catch", caught=False, ok=False, via=[],
                         detail="no column faces the stair: mutation not applicable"))
    else:
        d, cid, gap = sh
        rec("M5", "K01", "mutation", "catch", base, C.k01_stair_structure(_edit(w, "stair-main", _shift(d))),
            f"stair-main shifted {np.round(d, 3).tolist()} m: 30 mm into {cid} (gap was {gap*1000:.0f} mm)", only=cid)
        d2 = d.copy(); d2[np.nonzero(d2)[0][0]] = np.sign(d2[np.nonzero(d2)[0][0]]) * gap      # exactly touching
        rec("N-K01-touch", "K01", "negative", "quiet", base, C.k01_stair_structure(_edit(w, "stair-main", _shift(d2))), "stair exactly touching the column", only=cid)
        d3 = d.copy(); d3[np.nonzero(d3)[0][0]] = np.sign(d3[np.nonzero(d3)[0][0]]) * (gap - 0.005)
        rec("N-K01-gap", "K01", "negative", "quiet", base, C.k01_stair_structure(_edit(w, "stair-main", _shift(d3))), "stair 5 mm short of the column", only=cid)
    base = B.get("K03") or C.k03_opening_column(w)
    sh = _nearest_column_shift(w, "door-B-dining-yard", 0.050, model)
    if sh:
        rec("M-K03", "K03", "mutation", "catch", base, C.k03_opening_column(_edit(w, "door-B-dining-yard", _shift(sh[0]))),
            f"door-B-dining-yard 50 mm into {sh[1]}")
    sh = _nearest_column_shift(w, "door-B-dining-yard", -0.005, model)
    if sh:
        rec("N-K03", "K03", "negative", "quiet", base, C.k03_opening_column(_edit(w, "door-B-dining-yard", _shift(sh[0]))), "door 5 mm clear of the column")

    # M6 rotation dropped (90 and 180) / K08 / K10 / K09
    base = B.get("K10") or C.k10_placement(w, model)
    cand = [e for e in of_kind(model, "furniture") if e["id"] in w.elements and e["size"][0] != e["size"][1]]
    for rot in (90, 180):
        c = next((e for e in cand if abs(round(e["rotation_deg"])) % 360 in ((90, 270) if rot == 90 else (180,))
                  and abs(e["size"][0] - e["size"][1]) > 100 and e["id"] not in _fails(base)), None)
        if c is None:
            rows.append(dict(id=f"M6-{rot}", check="K10", kind="mutation", expect="catch", caught=False, ok=False, via=[], detail="no candidate"))
            continue
        a = np.radians(-c["rotation_deg"])
        R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])

        def rotb(t, R=R):
            cc = t.reshape(-1, 3).mean(0) if False else None
            return t
        el = w.elements[c["id"]]
        ctr = (np.array(el.box[:3]) + np.array(el.box[3:])) / 2

        def unrot(t, R=R, ctr=ctr):
            t = t.copy()
            xy = t[..., :2] - ctr[:2]
            t[..., :2] = xy @ R.T + ctr[:2]
            return t
        rec(f"M6-{rot}", "K10", "mutation", "catch", base, C.k10_placement(_edit(w, c["id"], unrot), model),
            f"{c['id']} (model rotation {c['rotation_deg']:.0f}, carcass {c['size'][0]:.0f}x{c['size'][1]:.0f}) rotated back to 0")
    c0 = next(e for e in cand if e["id"] not in _fails(base) and min(e["size"][:2]) > 600)
    rec("M-K10-move", "K10", "mutation", "catch", base, C.k10_placement(_edit(w, c0["id"], _shift((1.0, 0, 0))), model), f"{c0['id']} moved 1.0 m")
    rec("M-K10-move0.1", "K10", "mutation", "catch", base, C.k10_placement(_edit(w, c0["id"], _shift((0.1, 0, 0))), model),
        f"{c0['id']} moved 0.1 m (the centre bound is half the smaller side: expected to be missed)")
    rec("N-K10", "K10", "negative", "quiet", base, C.k10_placement(_edit(w, c0["id"], _shift((0.02, 0, 0))), model), f"{c0['id']} moved 20 mm")
    # K09 delete / duplicate
    base = B.get("K09") or C.k09_identity(w, model, contract)
    w2 = _copy(w); del w2.elements[c0["id"]]
    rec("M-K09-del", "K09", "mutation", "catch", base, C.k09_identity(w2, model, contract), f"{c0['id']} deleted")
    e = w.elements[c0["id"]]
    w2 = _copy(w); w2.elements[c0["id"]] = Element(c0["id"], e.parts + e.parts)
    rec("M-K09-dup", "K09", "mutation", "catch", base, C.k09_identity(w2, model, contract), f"{c0['id']} built twice")
    # K08 scale
    def k08(wx):
        el = wx.elements[c0["id"]]
        a = el.tris.reshape(-1, 3)
        d = (a.max(0) - a.min(0)) * 1000
        return C.k08_bbox_vs_figure_partial([(c0["id"], [float(x) for x in d], [c0["size"][0], c0["size"][1]])])
    def scale(f):
        def g(t):
            c = (np.array(el.box[:3]) + np.array(el.box[3:])) / 2
            return (t - c) * f + c
        return g
    el = w.elements[c0["id"]]
    base8 = k08(w)
    rec("M-K08-down", "K08", "mutation", "catch", base8, k08(_edit(w, c0["id"], scale(0.85))), f"{c0['id']} scaled 0.85")
    rec("M-K08-up", "K08", "mutation", "catch", base8, k08(_edit(w, c0["id"], scale(1.15))), f"{c0['id']} scaled 1.15")
    rec("N-K08", "K08", "negative", "quiet", base8, k08(_edit(w, c0["id"], scale(1.002))), f"{c0['id']} scaled 1.002")

    # K11 floor strip
    if areas:
        base = B.get("K11") or C.k11_net_area(w, areas)
        rid = next(r for r in sorted(areas) if r not in _fails(base) and C.floor_area(w, r))
        def trim(f):
            def g(t):
                c = t.reshape(-1, 3)[:, 0].mean()
                t = t.copy(); t[..., 0] = c + (t[..., 0] - c) * f
                return t
            return g
        def edit_mesh(f):
            w2 = _copy(w); w2.mesh_tris = dict(w.mesh_tris); w2.mesh_tris[f"floor-{rid}"] = trim(f)(w.mesh_tris[f"floor-{rid}"])
            return w2
        rec("M-K11", "K11", "mutation", "catch", base, C.k11_net_area(edit_mesh(0.9), areas), f"floor of {rid} shortened by 10 %")
        rec("N-K11", "K11", "negative", "quiet", base, C.k11_net_area(edit_mesh(0.9995), areas), f"floor of {rid} 0.05 % smaller")
    # K12 column moved
    if env:
        base = B.get("K12") or C.k12_environment(w, env, model)
        rec("M-K12", "K12", "mutation", "catch", base, C.k12_environment(_edit(w, "column-00", _shift((0.02, 0, 0))), env, model), "column-00 moved 20 mm")
        rec("N-K12", "K12", "negative", "quiet", base, C.k12_environment(_edit(w, "column-00", _shift((0.001, 0, 0))), env, model), "column-00 moved 1 mm")
    # K13 id stripped
    base = B.get("K13") or C.k13_detail_solids(w)
    w2 = _copy(w); w2.unowned = w.unowned + [("rug-extra", "furniture", 6)]
    rec("M-K13", "K13", "mutation", "catch", base, C.k13_detail_solids(w2), "one more mesh without an element id")
    # K14 guard deleted
    base = B.get("K14") or C.k14_guards(w, model)
    w2 = _copy(w); del w2.elements["rail-gf-stair-void"]
    rec("M-K14", "K14", "mutation", "catch", base, C.k14_guards(w2, model), "rail-gf-stair-void deleted")
    # K15 sconce off its wall
    if hosts and host_ids:
        base = B.get("K15") or C.k15_mounting(w, hosts, host_ids)
        k0 = next(iter(host_ids)); n = np.array(hosts[k0]["normal"], float)
        rec("M-K15", "K15", "mutation", "catch", base, C.k15_mounting(_edit(w, host_ids[k0], _shift(n * 0.30)), hosts, host_ids), f"{host_ids[k0]} moved 0.30 m off its host")
        rec("N-K15", "K15", "negative", "quiet", base, C.k15_mounting(_edit(w, host_ids[k0], _shift(n * 0.005)), hosts, host_ids), "plate 5 mm off")
    # K16 soffit lowered over the stair (a box dropped over the flight)
    from .geom import box_tris
    base = B.get("K16") or C.k16_headroom(w)
    pts = C.pitch_points(w.elements["stair-main"].sel(group="shell"))
    px, py, pz = min(pts, key=lambda p: p[0])            # the pitch point nearest the stair's low-x end
    xm, ym, zm = sorted(pts, key=lambda p: abs(p[0] - 7.5))[0]

    def with_soffit(z_under):
        w2 = _copy(w)
        w2.elements["slab-mut"] = Element("slab-mut", [("m", "shell", None, None, box_tris((xm - 0.3, ym - 0.4, z_under, xm + 0.3, ym + 0.4, z_under + 0.2)))])
        return w2
    rec("M-K16", "K16", "mutation", "catch", base, C.k16_headroom(with_soffit(zm + 1.70)), f"a soffit 1.70 m above the pitch line at x{xm:.2f}")
    rec("N-K16", "K16", "negative", "quiet", base, C.k16_headroom(with_soffit(zm + 2.26)), "a soffit 2.26 m above the pitch line at the sample (2.07 m above the highest pitch point under its 0.6 m width)")
    # K18 datum
    if levels:
        base = B.get("K18") or C.k18_datum(w, levels, model)
        w2 = _copy(w)
        for e in of_kind(model, "door"):
            if e["level"] == "B" and e["id"] in w.elements:
                w2 = _edit(w2, e["id"], _shift((0, 0, 0.10)))
        rec("M-K18", "K18", "mutation", "catch", base, C.k18_datum(w2, levels, model), "every B-level door shifted +0.10 m")
        w3 = _copy(w)
        for e in of_kind(model, "door"):
            if e["level"] == "B" and e["id"] in w.elements:
                w3 = _edit(w3, e["id"], _shift((0, 0, 0.005)))
        rec("N-K18", "K18", "negative", "quiet", base, C.k18_datum(w3, levels, model), "every B-level door shifted +5 mm")
    return rows
