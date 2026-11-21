"""The built-scene checks K01-K18 (see docs/lanes/RV1-checks.md).

Every check takes a World (built meshes with element ids) and, where it compares, the intended model
(`intended.load_model`). Checks never import a generator. Each returns a list of Finding.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import sources
from .geom import aabb, penetration, ray_up, tri_cross_segments
from .intended import LEVEL_Z, along_y, of_kind

TOL_SCENE, TOL_EXACT, TOL_FIT = 0.002, 0.00005, 0.010


@dataclass
class Finding:
    check: str
    subject: str
    status: str                      # pass | fail | not_evaluated
    achieved: float | None = None
    required: float | None = None
    unit: str = ""
    message: str = ""
    element_ids: tuple = ()
    source: str = "RV1-TOL-SCENE"

    @property
    def failed(self):
        return self.status == "fail"


def _f(check, subject, ok, ach, req, unit, msg, ids=(), src="RV1-TOL-SCENE"):
    return Finding(check, subject, "pass" if ok else "fail", ach, req, unit, msg, tuple(ids), src)


def _ne(check, subject, why, src="RV1-TOL-SCENE"):
    return Finding(check, subject, "not_evaluated", message=why, source=src)


# ---------------------------------------------------------------- crossings (K01 K02 K03 K17)
def is_box(el, rel=1e-6):
    """True when the element's surfaces are exactly its bounding box (frozen box geometry): then overlap is exact."""
    t = el.tris
    if len(t) != 12:
        return False
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    a = 0.5 * np.linalg.norm(n, axis=1)
    x0, y0, z0, x1, y1, z1 = el.box
    dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
    return abs(a.sum() - 2 * (dx * dy + dy * dz + dx * dz)) <= rel * max(a.sum(), 1e-12)


def box_depth(A, B):
    """Exact interpenetration of two boxes: the smallest overlap extent over the three axes (0 if they do not overlap)."""
    d = [min(A.box[i + 3], B.box[i + 3]) - max(A.box[i], B.box[i]) for i in range(3)]
    return (min(d), tuple(max(A.box[i], B.box[i]) for i in range(3)) + tuple(min(A.box[i + 3], B.box[i + 3]) for i in range(3))) \
        if min(d) > 0 else (0.0, None)


def crossings(check, groupA, groupB, tol=TOL_SCENE, src="RV1-TOL-SCENE", label=""):
    """Pairwise surface crossings between two dicts of Elements; fail where depth > tol."""
    out, n = [], 0
    for ia, A in groupA.items():
        for ib, B in groupB.items():
            if ia == ib:
                continue
            la, ha = A.box[:3], A.box[3:]
            lb, hb = B.box[:3], B.box[3:]
            if any(la[i] > hb[i] + 1e-6 or lb[i] > ha[i] + 1e-6 for i in range(3)):
                continue
            n += 1
            if is_box(A) and is_box(B):
                d, reg = box_depth(A, B)
            else:
                seg, dep = tri_cross_segments(A.tris, B.tris)
                d, reg = penetration(seg, dep)
            if d > tol:
                out.append(_f(check, f"{ia} x {ib}", False, round(d * 1000, 2), tol * 1000, "mm",
                              f"{ia} passes through {ib}: interpenetration {d*1000:.1f} mm where {tol*1000:.2f} mm is allowed"
                              f"; crossing region x{reg[0]:.3f}..{reg[3]:.3f} y{reg[1]:.3f}..{reg[4]:.3f} z{reg[2]:.3f}..{reg[5]:.3f}",
                              (ia, ib), src))
    if not out:
        out.append(_f(check, label or "all", True, 0.0, tol * 1000, "mm",
                      f"{n} box-overlapping pairs tested {label}; none interpenetrates more than {tol*1000:.2f} mm", (), src))
    return out


def k01_stair_structure(w, tol=TOL_SCENE, src="RV1-TOL-SCENE"):
    st = w.of("stair")
    other = {k: e for k, e in w.elements.items() if e.kind in ("column", "beam", "slab", "wall") or k.startswith("env-slab")}
    return crossings("K01", st, other, tol, src, "stair vs column/beam/slab/wall")


def thin_axis(t):
    """(axis, thickness, lo, hi) of a wall's thin plan direction from its two largest opposite vertical face planes."""
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    ar = np.linalg.norm(n, axis=1)
    best = None
    for ax in (0, 1):
        sel = (ar > 1e-9) & (np.abs(n[:, ax]) > 0.99 * ar)
        if not sel.any():
            continue
        pl = np.round(t[sel][:, 0, ax], 3)
        w = {}
        for v, a_ in zip(pl, 0.5 * ar[sel]):
            w[v] = w.get(v, 0) + a_
        top = sorted(w, key=w.get, reverse=True)[:2]
        if len(top) == 2:
            th = abs(top[0] - top[1])
            if th >= 0.02 and (best is None or th < best[1]):      # two planes closer than 20 mm are one face seen twice
                best = (ax, th, min(top), max(top))
    return best


def k02_wall_slab(w, tol=TOL_SCENE):
    """A wall passes THROUGH a ramp/deck when its plan overlap with the slab exceeds half the wall's thickness. Up to half a
    thickness is a join at the slab edge (the wall's centre line on the slab boundary, as every Revit option had it)."""
    ramp = {k: e for k, e in w.elements.items() if k in ("slab-ramp", "slab-deck")}
    out, n = [], 0
    for iw, W in w.of("wall").items():
        for ib, B in ramp.items():
            lo, hi = W.box[:3], W.box[3:]
            if any(lo[i] > B.box[i + 3] + 1e-6 or B.box[i] > hi[i] + 1e-6 for i in range(3)):
                continue
            n += 1
            if is_box(W) and is_box(B):
                d, reg = box_depth(W, B)
            else:
                seg, dep = tri_cross_segments(W.tris, B.tris)
                d, reg = penetration(seg, dep)
            if d <= tol:
                continue
            ta = thin_axis(W.tris)
            th = ta[1] if ta else min(W.box[3] - W.box[0], W.box[4] - W.box[1])
            # plan overlap of the wall with the slab (smaller of the x and y overlap extents)
            ov = min(min(W.box[3], B.box[3]) - max(W.box[0], B.box[0]), min(W.box[4], B.box[4]) - max(W.box[1], B.box[1]))
            through = ov > th / 2 + tol
            out.append(_f("K02", f"{iw} x {ib}", not through, round(d * 1000, 2), tol * 1000, "mm",
                          f"{iw} meets {ib}: crossing {d*1000:.0f} mm; plan overlap {ov*1000:.0f} mm against the wall's {th*1000:.0f} mm thickness "
                          f"({'through the slab' if through else 'a join at the slab edge: at most half the thickness'}); "
                          f"region x{reg[0]:.3f}..{reg[3]:.3f} y{reg[1]:.3f}..{reg[4]:.3f} z{reg[2]:.3f}..{reg[5]:.3f}",
                          (iw, ib), "RV1-TOL-SCENE"))
    if not any(f.status == "fail" for f in out):
        out.append(_f("K02", "all", True, 0.0, tol * 1000, "mm", f"{n} wall/slab pairs touch; none passes through (joins at a slab edge ignored)"))
    return out


def k03_opening_column(w, tol=TOL_SCENE, src="RV1-TOL-SCENE"):
    return crossings("K03", {**w.of("door"), **w.of("window")}, w.of("column"), tol, src, "door/window vs column")


# ---------------------------------------------------------------- K04 door head vs soffit
def _soffit_pool(w, skip):
    t = [e.tris for k, e in w.elements.items()
         if k not in skip and e.kind in ("slab", "beam", "room", "env", "spec", "ctx", "wall", "column") and len(e.tris)]
    return np.concatenate(t)


BODY = ("door-leaf", "glass-pane", "window-frame")


def body(el):
    """The moving/glazed body of a door or window (leaf, glass, frame); finish skins and architraves excluded."""
    ts = [p[4] for p in el.parts if p[3] in BODY]
    return np.concatenate(ts) if ts else el.tris


def door_clearance(w, did, host=None, model=None, ref_head=None):
    d = w.elements[did]
    t = d.tris
    lo, hi = t.reshape(-1, 3).min(0), t.reshape(-1, 3).max(0)
    pool = _soffit_pool(w, {did, host} if host else {did})
    best = None
    for fx in (0.25, 0.5, 0.75):
        o = (lo[0] + fx * (hi[0] - lo[0]), lo[1] + fx * (hi[1] - lo[1]), lo[2] + 0.2)
        z = ray_up(pool, o, 0.0)
        if z is not None and (best is None or z < best):
            best = z
    return lo[2], hi[2], best


def k04_door_soffit(w, model, req=0.0):
    out = []
    for e in of_kind(model, "door"):
        did = e["id"]
        if did not in w.elements:
            out.append(_ne("K04", did, "door not in scene (see K09)", "RV1-SOFFIT-CLEAR")); continue
        # head of the leaf/glass/frame body (architraves excluded: they stand proud of the opening by design)
        head = body(w.elements[did]).reshape(-1, 3).max(0)[2]
        _, _, soff = door_clearance(w, did, e["host"])
        if soff is None:
            out.append(_ne("K04", did, "no surface found overhead", "RV1-SOFFIT-CLEAR")); continue
        clr = soff - head
        out.append(_f("K04", did, clr >= req - TOL_SCENE, round(clr * 1000, 1), req * 1000, "mm",
                      f"head at z {head:.3f}, soffit above at z {soff:.3f}: clearance {clr*1000:.0f} mm, {req*1000:.0f} mm needed",
                      (did,), "RV1-SOFFIT-CLEAR"))
    return out


# ---------------------------------------------------------------- K05/K06 windows and doors as modelled
def _ext(t, e):
    a = t.reshape(-1, 3)
    ax = 1 if along_y(e) else 0
    z0 = LEVEL_Z[e["level"]]
    return a[:, ax].max() - a[:, ax].min(), a[:, 2].min() - z0, a[:, 2].max() - z0


def k05_openings(w, model, tol=TOL_FIT):
    out = []
    for e in of_kind(model, "window"):
        p = e["params"]
        el = w.elements.get(e["id"])
        g = el.sel(material="glass-clear") if el else np.zeros((0, 3, 3))
        if len(g) == 0:
            out.append(_f("K05", e["id"], False, 0.0, p["width_mm"], "mm",
                          f"{e['id']} is credited (gross area {p.get('gross_area_m2')} m2, width {p['width_mm']:.0f} mm) "
                          f"but the scene has no glass surfaces for it", (e["id"],), "RV1-TOL-FIT")); continue
        wd, s0, s1 = _ext(g, e)
        want = (p["width_mm"] / 1000, p.get("sill_mm", 0) / 1000, (p.get("sill_mm", 0) + p["height_mm"]) / 1000)
        dev = max(abs(wd - want[0]), abs(s0 - want[1]), abs(s1 - want[2]))
        out.append(_f("K05", e["id"], dev <= tol, round(dev * 1000, 1), tol * 1000, "mm",
                      f"glass width {wd*1000:.0f}/{want[0]*1000:.0f}, sill {s0*1000:.0f}/{want[1]*1000:.0f}, head {s1*1000:.0f}/{want[2]*1000:.0f} mm (built/modelled); "
                      f"max deviation {dev*1000:.1f} mm", (e["id"],), "RV1-TOL-FIT"))
    for e in of_kind(model, "door"):
        p = e["params"]
        el = w.elements.get(e["id"])
        t = el.sel(part_kind="door-leaf") if el else np.zeros((0, 3, 3))
        if len(t) == 0 and el is not None:
            t = el.sel(material="glass-clear")
        if len(t) == 0:
            out.append(_f("K05", e["id"], False, 0.0, p["width_mm"], "mm",
                          f"{e['id']} has no leaf or glass surfaces in the scene", (e["id"],), "RV1-TOL-FIT")); continue
        a = t.reshape(-1, 3)
        wd = max(a[:, 0].max() - a[:, 0].min(), a[:, 1].max() - a[:, 1].min())   # leaf is thin: width = longer plan side
        hd = a[:, 2].max() - LEVEL_Z[e["level"]]
        dh = abs(hd - p["height_mm"] / 1000)
        if p.get("operation") in ("pocket", "sliding") and not len(el.sel(material="glass-clear")):
            # retracted panels show a stack, not the opening: only the height is measurable
            out.append(_f("K05", e["id"], dh <= tol, round(dh * 1000, 1), tol * 1000, "mm",
                          f"{p['operation']} door, width not measurable from retracted panels; head {hd*1000:.0f}/{p['height_mm']:.0f} mm (built/modelled)",
                          (e["id"],), "RV1-TOL-FIT")); continue
        dev = max(abs(wd - p["width_mm"] / 1000), dh)
        out.append(_f("K05", e["id"], dev <= tol, round(dev * 1000, 1), tol * 1000, "mm",
                      f"door width {wd*1000:.0f}/{p['width_mm']:.0f}, head {hd*1000:.0f}/{p['height_mm']:.0f} mm (built/modelled)",
                      (e["id"],), "RV1-TOL-FIT"))
    return out


def k06_glazing_to_beam(w, model, allow=0.15):
    out = []
    for e in of_kind(model, "window"):
        p = e["params"]
        if not p.get("full_height"):
            continue
        el = w.elements.get(e["id"])
        g = el.sel(material="glass-clear") if el else np.zeros((0, 3, 3))
        if len(g) == 0:
            out.append(_ne("K06", e["id"], "no glass in scene (K05 reports it)", "RV1-GLAZE-HEAD")); continue
        a = g.reshape(-1, 3)
        z0 = LEVEL_Z[e["level"]]
        floor_gap = a[:, 2].min() - z0
        c = (a.min(0) + a.max(0)) / 2
        pool = _soffit_pool(w, {e["id"], e["host"]})
        soff = ray_up(pool, (c[0], c[1], a[:, 2].max() - 0.01), 0.0)
        if soff is None:
            out.append(_ne("K06", e["id"], "nothing found above the glass head", "RV1-GLAZE-HEAD")); continue
        gap = soff - a[:, 2].max()
        ok = floor_gap <= TOL_FIT and gap <= allow
        out.append(_f("K06", e["id"], ok, round(gap * 1000, 1), allow * 1000, "mm",
                      f"glass starts {floor_gap*1000:.0f} mm above the floor and ends {gap*1000:.0f} mm below the soffit/beam; {allow*1000:.0f} mm allowed",
                      (e["id"],), "RV1-GLAZE-HEAD"))
    return out


# ---------------------------------------------------------------- K07 fixtures vs ceiling and intended datum
def _lum_pool(w, skip=()):
    return _soffit_pool(w, set(skip))


def k07_fixture_ceiling(w, model, tol=TOL_FIT):
    out, pool = [], None
    for e in of_kind(model, "luminaire"):
        mt = e["params"].get("mount")
        if mt not in ("pendant", "recessed"):
            continue
        el = w.elements.get(e["id"])
        if el is None or not len(el.tris):
            continue                        # absence is K09's finding
        if pool is None:
            pool = _lum_pool(w)
        a = el.tris.reshape(-1, 3)
        lo, hi = a.min(0), a.max(0)
        c = (lo + hi) / 2
        soff = ray_up(pool, (c[0], c[1], lo[2] - 0.001), 0.0)
        z0 = LEVEL_Z[e["level"]]
        if soff is None:
            out.append(_ne("K07", e["id"], "no ceiling surface overhead", "RV1-TOL-FIT")); continue
        if mt == "pendant":
            over = hi[2] - soff
            drop = e["placement"][2] / 1000 + z0
            dev = lo[2] - drop
            ok = over <= TOL_SCENE and abs(dev) <= tol
            out.append(_f("K07", e["id"], ok, round(max(over, abs(dev)) * 1000, 1), tol * 1000, "mm",
                          f"pendant top {over*1000:+.0f} mm relative to the ceiling (must not pass it); emitter datum "
                          f"{lo[2]:.3f} vs intended {drop:.3f} m ({dev*1000:+.0f} mm)", (e["id"],), "RV1-TOL-FIT"))
        else:
            dev = lo[2] - soff
            out.append(_f("K07", e["id"], abs(dev) <= tol, round(abs(dev) * 1000, 1), tol * 1000, "mm",
                          f"recessed lens plane {dev*1000:+.0f} mm from the ceiling plane", (e["id"],), "RV1-TOL-FIT"))
    return out


# ---------------------------------------------------------------- K08 bbox vs catalogue figure (built vs requested size)
def k08_bbox_vs_figure(items, rel=0.05, absmm=10.0):
    """items: list of (id, built_dims_mm (3), figure_dims_mm (3)). Two-sided, sorted dims, so yaw does not matter."""
    out = []
    for i, built, fig in items:
        b, f = sorted(built), sorted(fig)
        dev = max(abs(x - y) / max(y, 1e-9) for x, y in zip(b, f))
        ok = all(abs(x - y) <= max(absmm, rel * y) for x, y in zip(b, f))
        out.append(_f("K08", i, ok, round(dev * 100, 1), rel * 100, "%",
                      f"built {sorted(built)} mm vs figure {sorted(fig)} mm, largest deviation {dev*100:.1f} %",
                      (i,), "RV1-TOL-CAT"))
    return out


def k08_bbox_vs_figure_partial(items, rel=0.05, absmm=10.0):
    """items: (id, built_dims_mm, figure_dims_mm with 1-3 entries). Each stated figure must match some built dimension."""
    out = []
    for i, built, fig in items:
        b = sorted(built)
        used, worst = [], 0.0
        for f in sorted(fig, reverse=True):
            j = min((k for k in range(3) if k not in used), key=lambda k: abs(b[k] - f))
            used.append(j)
            worst = max(worst, abs(b[j] - f) / f)
        ok = all(abs(b[j] - f) <= max(absmm, rel * f) for j, f in zip(used, sorted(fig, reverse=True)))
        out.append(_f("K08", i, ok, round(worst * 100, 1), rel * 100, "%",
                      f"{i}: built bbox {[round(x) for x in built]} mm vs stated size {[round(x) for x in fig]} mm, worst {worst*100:.1f} %",
                      (i,), "RV1-TOL-CAT"))
    return out


# ---------------------------------------------------------------- K09 identity / K13 detail solids
def _dup_tris(t, q=1000):
    k = np.round(np.sort(t.reshape(len(t), -1, 3).round(3), 1) * q).astype(np.int64).reshape(len(t), -1)
    _, cnt = np.unique(k, axis=0, return_counts=True)
    return int((cnt - 1).sum())


WANT = ("wall", "door", "window", "column", "beam", "slab", "stair", "rail", "furn", "lum", "fixture", "joinery")


def k09_identity(w, model):
    out = []
    want = [e for e in model.values() if e["kind"] in ("wall", "door", "window", "column", "beam", "slab", "stair",
                                                         "railing", "furniture", "luminaire", "fixture")]
    missing = [e["id"] for e in want if e["id"] not in w.elements or not len(w.elements[e["id"]].tris)]
    for i in missing:
        out.append(_f("K09", i, False, 0, 1, "built", f"{i} is in the model and has no surfaces in the scene (built 0 times)", (i,), "RV1-TOL-SCENE"))
    dups = {}
    for e in want:
        el = w.elements.get(e["id"])
        if el is not None and len(el.tris):
            d = _dup_tris(el.tris)
            if d >= 0.5 * len(el.tris):
                dups[e["id"]] = d
    for i, d in dups.items():
        out.append(_f("K09", i, False, d, 0, "duplicate triangles", f"{i}: {d} coincident duplicate triangles (built more than once)", (i,)))
    extra = sorted(k for k in w.elements if k not in model and w.elements[k].kind not in ("env", "spec", "ctx", "site", "room", "garden", "plant"))
    for i in extra:
        out.append(_ne("K09", i, "scene element id with no design-model element (informational)"))
    if not missing and not dups:
        out.append(_f("K09", "model elements", True, len(want), len(want), "elements", f"all {len(want)} modelled elements are built exactly once"))
    return out


def k13_detail_solids(w):
    """Every detail/finish solid carries an element id (D10: 'Opening has no Mark -> built 0 times')."""
    out = []
    for mid, grp, n in w.unowned:
        out.append(_f("K13", mid, False, n, 0, "faces without id",
                      f"mesh {mid} (group {grp}) has {n} faces and no design-model element id; identity cannot be checked",
                      (), "RV1-TOL-SCENE"))
    if not w.unowned:
        out.append(_f("K13", "all meshes", True, 0, 0, "faces without id", "every scene face carries an element id"))
    return out


def k09_ids(expected, built, label="K09"):
    """expected: ids the design asks for; built: ids found in the as-built record (repeats = built more than once)."""
    out, seen = [], {}
    for b in built:
        seen[b] = seen.get(b, 0) + 1
    for e in expected:
        n = seen.get(e, 0)
        if n != 1:
            out.append(_f(label, e, False, n, 1, "built", f"{e}: built {n} times where exactly 1 is expected", (e,)))
    if not out:
        out.append(_f(label, "ids", True, len(expected), len(expected), "elements", f"all {len(expected)} expected ids built exactly once"))
    return out


def k10_boxes(pairs, tol=TOL_FIT, label="K10"):
    """pairs: (id, spec_box, built_box) boxes (x0,y0,z0,x1,y1,z1) in one unit; worst face difference vs tol."""
    out = []
    for i, a, b in pairs:
        d = float(np.abs(np.array(a, float) - np.array(b, float)).max())
        out.append(_f(label, i, d <= tol, round(d * 1000, 1), tol * 1000, "mm", f"{i}: largest box-face difference {d*1000:.1f} mm", (i,), "RV1-TOL-FIT"))
    return out


# ---------------------------------------------------------------- K10 placement and yaw
def k10_placement(w, model, tol=TOL_FIT):
    out = []
    for e in of_kind(model, "furniture"):
        el = w.elements.get(e["id"])
        if el is None or not len(el.tris):
            continue
        sx, sy = e["size"][0] / 1000, e["size"][1] / 1000
        r = round(e["rotation_deg"]) % 180
        ex, ey = (sx, sy) if r == 0 else (sy, sx) if r == 90 else (None, None)
        if ex is None:
            out.append(_ne("K10", e["id"], f"rotation {e['rotation_deg']} not a quarter turn: footprint yaw not measured")); continue
        a = el.tris.reshape(-1, 3)
        d = a.max(0) - a.min(0)
        c = (a.max(0) + a.min(0)) / 2
        p = e["placement"]
        short = max(ex - d[0], ey - d[1], 0.0)          # built footprint must contain the modelled carcass
        off = max(abs(c[0] - p[0] / 1000), abs(c[1] - p[1] / 1000))
        # accessories (stools, chairs) enlarge the footprint and shift its centre by up to half the excess; beyond that,
        # a centre more than half the carcass's smaller side away is a placement/yaw error (placement convention is
        # not uniform across plumbing items, so a tighter centre bound is not claimed)
        slack = max(d[0] - ex, d[1] - ey, 0.0) / 2
        bad = short > tol or off > slack + min(ex, ey) / 2
        out.append(_f("K10", e["id"], not bad, round(max(short, off - slack) * 1000, 1), tol * 1000, "mm",
                      f"footprint {d[0]*1000:.0f}x{d[1]*1000:.0f} mm vs carcass {ex*1000:.0f}x{ey*1000:.0f} at rotation {e['rotation_deg']:.0f}; "
                      f"short by {short*1000:.0f} mm, centre off by {off*1000:.0f} mm (slack {slack*1000:.0f})", (e["id"],), "RV1-TOL-FIT"))
    return out


# ---------------------------------------------------------------- K11 net areas
def floor_area(w, room):
    t = w.mesh_tris.get(f"floor-{room}")
    if t is None or not len(t):
        return None
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    up = n[:, 2] > 0
    return float(0.5 * np.abs(n[up, 2]).sum())


def k11_net_area(w, ref_areas, rel=0.01):
    """ref_areas: room id -> frozen Revit net area m2."""
    out = []
    for rid, ref in sorted(ref_areas.items()):
        a = floor_area(w, rid)
        if a is None:
            out.append(_ne("K11", rid, "no floor-<room> mesh in the scene", "RV1-TOL-AREA")); continue
        if ref <= 0:
            out.append(_ne("K11", rid, "frozen Revit area is zero", "RV1-TOL-AREA")); continue
        dev = abs(a - ref) / ref
        out.append(_f("K11", rid, dev <= rel, round(a, 3), round(ref, 3), "m2",
                      f"scene floor area {a:.3f} m2 vs frozen Revit net area {ref:.3f} m2 ({dev*100:.2f} %, {rel*100:.0f} % allowed)",
                      (f"room-{rid}",), "RV1-TOL-AREA"))
    return out


# ---------------------------------------------------------------- K12 / K18 environment and datum
def plane_dev(t, axis, val):
    """Smallest distance from `val` to any face plane of `t` perpendicular to `axis` (robust to faces
    attributed to the wrong element: only the presence of a face where the reference has one is asked)."""
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    ln = np.linalg.norm(n, axis=1)
    sel = (ln > 1e-9) & (np.abs(n[:, axis]) > 0.99 * ln)
    if not sel.any():
        return None
    return float(np.abs(t[sel][:, 0, axis] - val).min())


def k12_environment(w, env, model, tol=0.002):
    """env: frozen env read-back (columns, shapes). Each Revit face plane (mm) must have a scene face within `tol`.
    Columns are linked to scene ids through the model's existing_id; shapes by name (ctx-<name>)."""
    out = []
    by_rvt = {e["params"].get("existing_id"): e["id"] for e in of_kind(model, "column")}
    for c in env["columns"]:
        cid = by_rvt.get(c["id"])
        if cid is None or cid not in w.elements:
            continue                                    # a neighbour's column: not ours
        b = np.array(c["bbox"]) / 1000
        t = w.elements[cid].tris
        devs = [plane_dev(t, ax, b[ax + k]) for ax in (0, 1) for k in (0, 3)]
        d = max(x for x in devs if x is not None) if any(x is not None for x in devs) else None
        out.append(_f("K12", f"column {c['id']} = {cid}", d is not None and d <= tol, None if d is None else round(d * 1000, 2),
                      tol * 1000, "mm", f"nearest scene face to each of the 4 plan faces of Revit column {c['id']}: worst {None if d is None else round(d*1000,2)} mm",
                      (cid,), "RV1-ENV"))
    for s in env["shapes"]:
        el = w.elements.get("ctx-" + s["id"]) or w.elements.get(s["id"])
        if el is None:
            continue
        b = np.array(s["bbox"]) / 1000
        devs = [plane_dev(el.tris, ax, b[ax + k]) for ax in (0, 1, 2) for k in (0, 3)]
        devs = [x for x in devs if x is not None]
        d = max(devs) if devs else None
        out.append(_f("K12", s["id"], d is not None and d <= tol, None if d is None else round(d * 1000, 2), tol * 1000, "mm",
                      f"worst nearest-face distance over the 6 box faces of Revit shape {s['id']}: {None if d is None else round(d*1000,2)} mm",
                      (el.id,), "RV1-ENV"))
    return out


def k18_datum(w, levels, model):
    """levels: frozen name->z mm. Built anchors: basement and ground door-leaf soles, column base and top."""
    z = {n.split()[0]: v / 1000 for n, v in ((lv["name"], lv["z"]) for lv in levels)}
    out = []
    for lvl, want in (("B", z.get("B", -3.0)), ("GF", z.get("GF", 0.0))):
        soles = []
        for e in of_kind(model, "door"):
            if e["level"] == lvl and e["id"] in w.elements and e["params"].get("operation") == "hinged":
                lf = w.elements[e["id"]].sel(part_kind="door-leaf")
                if len(lf):
                    soles.append(lf.reshape(-1, 3)[:, 2].min())
        if not soles:
            out.append(_ne("K18", lvl, "no hinged door sole to anchor the level", "RV1-ENV")); continue
        med = float(np.median(soles))
        out.append(_f("K18", f"level {lvl}", abs(med - want) <= TOL_FIT, round(med, 4), want, "m",
                      f"median door sole {med:.4f} m vs frozen Revit level {want:.3f} m", (), "RV1-TOL-FIT"))
    return out


# ---------------------------------------------------------------- K14 guards
def k14_guards(w, model, tol=TOL_FIT):
    """Every modelled guard is built, and as tall as modelled. A guard the model calls required but the scene lacks fails
    (D21: no guard at the stair opening / terrace / patio edges)."""
    out = []
    for e in of_kind(model, "railing"):
        p = e["params"]
        if p.get("kind") != "guard":
            continue
        el = w.elements.get(e["id"])
        want = p["guard_height_mm"] / 1000
        if el is None or not len(el.tris):
            out.append(_f("K14", e["id"], False, 0.0, want * 1000, "mm",
                          f"{e['id']}: modelled guard ({want*1000:.0f} mm, drop {p.get('drop_mm')} mm) has no geometry in the scene",
                          (e["id"],), "RV1-GUARD")); continue
        a = el.tris.reshape(-1, 3)
        h = a[:, 2].max() - a[:, 2].min()
        out.append(_f("K14", e["id"], h >= want - tol, round(h * 1000, 1), want * 1000, "mm",
                      f"built height {h*1000:.0f} mm, modelled {want*1000:.0f} mm", (e["id"],), "RV1-GUARD"))
    return out


# ---------------------------------------------------------------- K15 mounting host contact
def k15_mounting(w, hosts, ids, tol=0.010):
    """hosts: scene['mounting_hosts'] (structural_point + normal); ids: host key -> luminaire element id."""
    out = []
    for key, lid in ids.items():
        h = hosts.get(key)
        el = w.elements.get(lid)
        if h is None or el is None:
            out.append(_ne("K15", key, "no host record or element", "RV1-MOUNT")); continue
        plate = el.sel(part_kind="wall-plate")
        if not len(plate):
            out.append(_ne("K15", key, "no wall-plate surfaces", "RV1-MOUNT")); continue
        n = np.array(h["normal"], float)
        p0 = np.array(h["structural_point"], float)
        d = (plate.reshape(-1, 3) - p0) @ n            # signed distance of plate vertices from the host face
        back = d.min()
        ok = abs(back) <= tol
        out.append(_f("K15", key, ok, round(back * 1000, 1), tol * 1000, "mm",
                      f"plate back is {back*1000:+.1f} mm from host face of {h['id']} (normal {tuple(n)}); front stands {d.max()*1000:.0f} mm proud",
                      (lid,), "RV1-MOUNT"))
    return out


# ---------------------------------------------------------------- K16 stair headroom
def pitch_points(t, up_axis_pair=None):
    """Points on the pitch line of a flight built from `t` (stair surfaces): one at each tread's nosing (the edge nearest the
    tread below) and and a 20 mm sampling between nosings. Returns [(x, y, z)]. Treads are the up-facing triangles grouped by height."""
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    top = n[:, 2] > 1e-9
    tt = t[top]
    z = np.round(tt.mean(1)[:, 2], 3)
    groups = {}
    for tri, zz in zip(tt, z):
        groups.setdefault(zz, []).append(tri)
    zs = sorted(groups)
    if len(zs) < 3:
        return []
    cen = np.array([np.concatenate(groups[k]).mean(0) for k in zs])
    d = cen[-1, :2] - cen[0, :2]
    d = d / np.linalg.norm(d)
    pts = []
    for k, c in zip(zs, cen):
        pts_k = np.concatenate(groups[k])
        s = pts_k[:, :2] @ d
        lat = pts_k[:, :2] @ np.array([-d[1], d[0]])
        s0 = s.min()
        p = d * s0 + np.array([-d[1], d[0]]) * (lat.min() + lat.max()) / 2
        pts.append((p[0], p[1], k))
    dense = []
    for a, b in zip(pts, pts[1:]):                    # the pitch line is straight between nosings: sample every 20 mm
        n = max(2, int(np.ceil(np.hypot(b[0] - a[0], b[1] - a[1]) / 0.02)))
        dense += [tuple(np.array(a) + (np.array(b) - np.array(a)) * i / n) for i in range(n)]
    return pts + dense


def k16_headroom(w, req=2.0, stair="stair-main", src="ukadk-stair-headroom-min"):
    """Vertical clearance above the PITCH line (not the tread tops: D16). Source: Approved Document K Diagram 1.3, 2 m."""
    st = w.elements.get(stair)
    if st is None:
        return [_ne("K16", stair, "no stair in scene", src)]
    pts = pitch_points(st.sel(group="shell"))
    if not pts:
        return [_ne("K16", stair, "no treads found", src)]
    pool = _soffit_pool(w, {stair})
    best = None
    for x, y, z in pts:
        zz = ray_up(pool, (x, y, z + 0.001), 0.0)
        if zz is None:
            continue
        hr = zz - z
        if best is None or hr < best[0]:
            best = (hr, x, y, z)
    if best is None:
        return [_ne("K16", stair, "no surface overhead the pitch line", src)]
    hr, x, y, z = best
    return [_f("K16", stair, hr >= req - TOL_SCENE, round(hr * 1000, 1), req * 1000, "mm",
               f"least clearance above the pitch line {hr*1000:.0f} mm at x{x:.3f} y{y:.3f} z{z:.3f}; {req*1000:.0f} mm needed",
               (stair,), src)]
