"""Proof that the build is honest: ids, plan footprints against the layout, nothing floats, nothing clips. Pure Python."""
from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon, box as sbox
from shapely.ops import unary_union

TOL_FOOTPRINT = 0.020      # m, the brief
TOL_CONTACT = 0.002        # m, a part "touches" within this
TOL_CLIP = 0.005           # m, interpenetration deeper than this is a clip
TOL_FOLIAGE = 0.05         # m, soft foliage may touch a rigid object by this much before it is a clip (policy)
ABOVE_GROUND = {"bench", "table", "chair", "bbq", "pot", "wall", "screen", "pergola"}


def F(check, oid, status, achieved=None, required=None, note=""):
    return dict(check=check, id=oid, status=status, achieved=achieved, required=required, note=note)


def _bbox(o):
    b = o.bounds()
    return b[0], b[1], b[3], b[4]


def _union_poly(o):
    return unary_union([sbox(*p.bounds()[:2], *p.bounds()[3:5]) for p in o.parts])


def ids(scene):
    out, seen = [], set()
    for o in scene.objects:
        key = (o.id, o.state)
        ok = o.id.startswith("ld-") and key not in seen
        seen.add(key)
        out.append(F("id", o.id, "pass" if ok else "fail", o.id, "unique, ld-*prefixed"))
    return out


def footprints(scene, state="closed", tol=TOL_FOOTPRINT):
    out = []
    for o in scene.select(state):
        if o.footprint_mode is None or (o.footprint is None and o.footprint_poly is None):
            continue
        if o.footprint_mode == "poly":
            d = _union_poly(o).hausdorff_distance(o.footprint_poly)
            out.append(F("footprint", o.id, "pass" if d <= tol else "fail", "%.1f mm" % (d * 1000), "<= %.0f mm Hausdorff" % (tol * 1000)))
            continue
        b, f = _bbox(o), o.footprint
        if o.footprint_mode == "bbox":
            d = max(abs(b[i] - f[i]) for i in range(4))
            out.append(F("footprint", o.id, "pass" if d <= tol else "fail", "%.1f mm worst edge" % (d * 1000), "<= %.0f mm" % (tol * 1000)))
        else:   # within
            d = max(f[0] - b[0], f[1] - b[1], b[2] - f[2], b[3] - f[3], 0)
            out.append(F("footprint", o.id, "pass" if d <= tol else "fail", "%.1f mm outside" % (d * 1000), "inside the layout rect (+%.0f mm)" % (tol * 1000)))
    return out


def plant_footprints(scene, tol=TOL_FOOTPRINT):
    """Stand-in masses: at maturity the plan extent equals the layout spread; at an age it never exceeds it. Assets: reported against the sourced range."""
    out = []
    for o in scene.objects:
        if o.kind != "plant" or not o.meta.get("layout_spread") or o.meta.get("climbing"):
            continue
        s = o.meta["layout_spread"]
        if o.standin:
            b = _bbox(o)
            w = max(b[2] - b[0], b[3] - b[1])
            if scene.age is None:
                out.append(F("plant-footprint", o.id, "pass" if abs(w - s) <= tol else "fail", "%.3f m" % w, "%.3f m (layout spread) +-%.0f mm" % (s, tol * 1000)))
            else:
                out.append(F("plant-footprint", o.id, "pass" if w <= s + tol else "fail", "%.3f m" % w, "<= %.3f m (layout mature spread)" % s))
        else:
            a = o.asset["bounds"]
            w = max(a[3] - a[0], a[4] - a[1])
            out.append(F("plant-footprint", o.id, "info", "%.2f m (asset aspect)" % w, "layout mature spread %.2f m; asset scaled by height, spread follows the asset" % s))
    return out


def _grounded_parts(o, g):
    """Union-find over the object's parts by contact; returns (list of bounds, list of component ids)."""
    bs = [p.bounds() for p in o.parts] or [o.asset["bounds"]]
    n = len(bs)
    par = list(range(n))
    def f(i):
        while par[i] != i:
            par[i] = par[par[i]]; i = par[i]
        return i
    A = np.array(bs)
    for i in range(n):
        hit = np.all((A[i, :3] - TOL_CONTACT <= A[:, 3:]) & (A[i, 3:] + TOL_CONTACT >= A[:, :3]), axis=1)
        for j in np.nonzero(hit)[0]:
            par[f(i)] = f(int(j))
    return A, [f(i) for i in range(n)]


def support(scene, state="closed"):
    """Nothing floats: every connected group of an object's parts reaches the ground (z <= ground) or touches a declared support object."""
    g = scene.ground_z
    by = {o.id: o for o in scene.select(state)}
    out = []
    for o in scene.select(state):
        A, comp = _grounded_parts(o, g)
        sup = []
        for sid in o.rests_on:
            if sid != "ground" and sid in by:
                sup += [p.bounds() for p in by[sid].parts] or [by[sid].asset["bounds"]]
        bad = []
        for c in set(comp):
            idx = [i for i in range(len(comp)) if comp[i] == c]
            z0 = min(A[i, 2] for i in idx)
            if z0 <= g + TOL_CONTACT:
                continue
            touch = any(all(A[i, k] - TOL_CONTACT <= s[k + 3] and A[i, k + 3] + TOL_CONTACT >= s[k] for k in range(3)) for i in idx for s in sup)
            if not touch:
                bad.append(z0 - g)
        sunk = max(0.0, g - A[:, 2].min()) if o.kind in ABOVE_GROUND else 0.0
        if bad:
            out.append(F("support", o.id, "fail", "floats %.0f mm above the ground" % (min(bad) * 1000), "touches the ground or its support"))
        elif sunk > TOL_CONTACT:
            out.append(F("support", o.id, "fail", "sunk %.0f mm below the ground" % (sunk * 1000), "stands on the ground"))
        else:
            out.append(F("support", o.id, "pass", "grounded", "touches the ground or its support"))
    return out


def _ell_hits_box(env, b, shrink=TOL_CLIP):
    cx, cy, cz, rx, ry, rz = env
    c = np.array([cx, cy, cz]); r = np.array([rx, ry, rz]) - shrink
    if (r <= 0).any():
        return False
    q = np.clip(c, np.array(b[:3]), np.array(b[3:]))      # the foliage is shrunk by the tolerance; thin rigid parts (blades) stay as they are
    return float((((q - c) / r) ** 2).sum()) < 1.0


def _prism_hits(a, b):
    if a.poly is not None and b.poly is not None:
        return Polygon(a.poly).buffer(0).intersection(Polygon(b.poly).buffer(0)).area > 2e-5
    return True


def clips(scene, state="closed"):
    """Pairs of different objects whose solids interpenetrate by more than 5 mm (exact for prisms, ellipsoid envelope for plants)."""
    objs = scene.select(state)
    items = []   # (obj index, bounds, part-or-None, envelope-or-None)
    for k, o in enumerate(objs):
        if o.parts:
            for p in o.parts:
                items.append((k, p.bounds(), p, p.envelope))
        else:
            items.append((k, o.asset["bounds"], None, o.meta.get("envelope")))
    B = np.array([i[1] for i in items])
    ok = {}
    for k, o in enumerate(objs):
        ok[k] = {j for j, q in enumerate(objs) if q.id in o.rests_on or o.id in q.rests_on}
    found = {}
    for a in range(len(items)):
        ka = items[a][0]
        m = np.all((B[a, :3] + TOL_CLIP < B[a + 1:, 3:]) & (B[a, 3:] - TOL_CLIP > B[a + 1:, :3]), axis=1)
        for off in np.nonzero(m)[0]:
            b = a + 1 + int(off)
            kb = items[b][0]
            if ka == kb or kb in ok[ka]:
                continue
            ea, eb = items[a][3], items[b][3]
            if ea and eb:          # plant against plant: massing overlap is normal
                continue
            if ea or eb:
                env, other = (ea, items[b][1]) if ea else (eb, items[a][1])
                if not _ell_hits_box(env, other, TOL_FOLIAGE):
                    continue
            else:
                pa, pb = items[a][2], items[b][2]
                if pa is not None and pb is not None and not _prism_hits(pa, pb):
                    continue
            found.setdefault((ka, kb), 0)
            found[(ka, kb)] += 1
    return [F("clip", "%s x %s" % (objs[a].id, objs[b].id), "fail", "%d overlapping part pairs" % n, "no rigid object deeper than %.0f mm (foliage %.0f mm)" % (TOL_CLIP * 1000, TOL_FOLIAGE * 1000)) for (a, b), n in found.items()]


def standins(scene):
    """Every generic mass is labelled STAND-IN in its label and its schedule row; nothing labelled as a species it is not."""
    out = []
    rows = {r["id"]: r for r in scene.schedule}
    for o in scene.objects:
        if o.kind != "plant":
            continue
        r = rows.get(o.id)
        if o.standin:
            good = "STAND-IN" in o.label and r is not None and r["status"] == "standin" and r.get("reason")
            out.append(F("standin", o.id, "pass" if good else "fail", "labelled STAND-IN" if good else "unlabelled generic mass", "STAND-IN label + schedule reason"))
        else:
            good = o.asset is not None and r is not None and r["status"] == "asset" and r.get("grade") in ("A", "B")
            out.append(F("standin", o.id, "pass" if good else "fail", "graded asset %s" % (r or {}).get("asset"), "grade A/B asset of the species or genus"))
    return out


def run_all(scene, state="closed"):
    r = ids(scene) + footprints(scene, state) + plant_footprints(scene) + support(scene, state) + clips(scene, state) + standins(scene)
    return r


def summary(findings):
    from collections import Counter
    c = Counter((f["check"], f["status"]) for f in findings)
    return {"%s:%s" % k: v for k, v in sorted(c.items())}
