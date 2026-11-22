"""LV check of L6d's LA4 'lying, looking up' sightlines (engine: `villa_checks.bed_lying_sightlines`), computed here from scratch.

For each pillow eye the engine lists: (1) the eye lies inside the bed's footprint at the bed's eye height; (2) every product-bound fitting of
the villa within 45 deg of straight up has its luminance I(gamma)/A_proj computed with THIS lane's IES reader and the opening written in the
file (LM-63 line 'width length height', negative = disc); the maximum is compared with the engine's own value and the 3000 cd/m2 cap.
Asymmetric files (several C planes): the maximum over C is used (an upper bound; the engine uses the true azimuth), so my value >= engine's.
Generic fittings (cove, strips, markers) have no opening in a file: reported separately as 'no luminance computable', never counted as pass.
"""
from __future__ import annotations

import math
from pathlib import Path

from . import ies

CAP = 3000.0
CONE = 45.0
FT = 0.3048


def opening_area_m2(d: ies.IesData) -> float:
    w, l, _ = d.opening
    k = 1.0 if d.units == 2 else FT
    if w < 0 or l < 0:
        return math.pi / 4 * abs(w) * k * abs(l if l else w) * k
    return (w * k) * ((l or w) * k)


def _unit(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def luminance(p, d: ies.IesData, eye) -> float:
    v = _unit(tuple(eye[i] - p.position[i] for i in range(3)))
    aim = _unit(p.aim)
    cos_t = sum(v[i] * aim[i] for i in range(3))
    if cos_t <= 0:
        return 0.0
    g = math.degrees(math.acos(min(1.0, cos_t)))
    cs = (0.0,) if len(d.cang) == 1 else tuple(i * 5.0 for i in range(72))
    return max(ies.candela(d, g, c) for c in cs) / (opening_area_m2(d) * cos_t)


def shell_triangles(scene_json):
    """Triangles of the scene's shell finish layers (walls, floors, slabs): what can hide a fitting in another room from an eye (vertical faces only)."""
    import json
    import numpy as np
    d = json.load(open(scene_json))
    tris = []
    for m in d["meshes"]:
        if m.get("group") == "shell" and m.get("part_kind") == "finish-layer":
            for f in m["faces"]:
                for i in range(1, len(f) - 1):
                    tris.append((f[0], f[i], f[i + 1]))
    t = np.array(tris, dtype=float)
    nz = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    return t[np.abs(nz[:, 2]) < 0.1 * np.linalg.norm(nz, axis=1) + 1e-12]       # vertical faces only: walls (a ceiling pierced by its own fitting is not a hiding wall)


def segment_hits(tris, a, b) -> int:
    """Number of shell triangles crossed by the open segment a-b (Moller-Trumbore, 1 mm end margins)."""
    import numpy as np
    a, b = np.array(a, float), np.array(b, float)
    dvec = b - a
    L = np.linalg.norm(dvec)
    dvec = dvec / L
    v0, v1, v2 = tris[:, 0], tris[:, 1], tris[:, 2]
    e1, e2 = v1 - v0, v2 - v0
    h = np.cross(dvec, e2)
    det = np.einsum("ij,ij->i", e1, h)
    ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    sv = a - v0
    u = inv * np.einsum("ij,ij->i", sv, h)
    q = np.cross(sv, e1)
    w = inv * (q @ dvec)
    t = inv * np.einsum("ij,ij->i", e2, q)
    return int(np.sum(ok & (u >= 0) & (w >= 0) & (u + w <= 1) & (t > 0.001) & (t < L - 0.001)))


def run(villa, scene_json=None) -> list[dict]:
    """One row per sightline. `mine` = worst product-bound fitting of the bed's own cluster (the engine's rule: walls are not modelled, so a
    fitting in another room is not in view); `behind_walls` = fittings of other clusters inside the cone with their luminance (listed, not judged)."""
    from ..lightcalc import villa_checks as VC
    from ..lightcalc.checks import check_la4_luminance
    from ..lightcalc.villa import cluster_of
    cache = {}
    byid = {f.id: f for f in villa.fixtures}
    rows = []
    tris = shell_triangles(scene_json) if scene_json else None
    for sl in VC.bed_lying_sightlines(villa):
        bid = sl["id"].split("-lying-up")[0]
        room = VC.BEDS[bid][0]
        x0, y0, x1, y1 = villa.fp[bid]
        eye = sl["eye"]
        mine, who, behind, generic = 0.0, "", [], set()
        mine_pl = []
        for p in villa.placements:
            fid = p.meta.get("parent") or p.id
            same = cluster_of(byid[fid].room) == cluster_of(room)
            if p.meta.get("generic"):
                if same and p.position[2] > eye[2] and math.dist(p.position[:2], eye[:2]) < 3.0:
                    generic.add(fid)
                continue
            v = _unit(tuple(p.position[i] - eye[i] for i in range(3)))
            if math.degrees(math.acos(max(-1.0, min(1.0, v[2])))) > CONE:
                continue
            path = p.meta["ies_path"]
            if path not in cache:
                cache[path] = ies.parse(Path(path).read_text(encoding="utf-8-sig", errors="replace").replace("\ufeff", ""))
            lum = luminance(p, cache[path], eye) * p.dim      # at the output the design drives it (the engine's convention)
            if same:
                mine_pl.append(p)
                if lum > mine:
                    mine, who = lum, fid
            else:
                behind.append((fid, byid[fid].room, round(lum)))
        if tris is not None:
            pos = {p.meta.get("parent") or p.id: p.position for p in villa.placements}
            behind = [(f, r, lum, segment_hits(tris, eye, pos[f])) for f, r, lum in behind]
        e = check_la4_luminance("LV", [sl], mine_pl)[0]
        rows.append(dict(id=sl["id"], eye=eye, eye_in_footprint=x0 <= eye[0] <= x1 and y0 <= eye[1] <= y1, mine=mine, mine_by=who,
                         engine=e.achieved or 0.0, engine_by=e.element_ids[0] if e.element_ids else "", generic_in_room=sorted(generic), behind_walls=behind))
    return rows


def results(villa, scene_json=None) -> list:
    """CheckResults (criterion LV2): the pillow eye lies in the bed, my worst luminance is under the cap and equals the engine's, and every
    fitting of another room inside the cone is behind a wall (when a scene is given; else that part is not_evaluated)."""
    from .common import check
    from .sources import ids
    out = []
    for r in run(villa, scene_json):
        bad = []
        if not r["eye_in_footprint"]:
            bad.append("eye %s is outside the bed footprint" % (tuple(round(x, 2) for x in r["eye"]),))
        if r["mine"] > CAP:
            bad.append("luminance %.0f cd/m2 over the %.0f cap (%s)" % (r["mine"], CAP, r["mine_by"]))
        if abs(r["mine"] - r["engine"]) > 0.02 * max(r["mine"], r["engine"]) + 10:
            bad.append("engine says %.0f cd/m2, this lane %.0f" % (r["engine"], r["mine"]))
        out.append(check("LV2", "fail" if bad else "pass", "la4-lying/" + r["id"], ids("LV-LM63"), achieved=round(r["mine"]), required=CAP, unit="cd/m2",
                         message="eye in bed %s; worst fitting in the bed's cluster %.0f cd/m2 (%s), engine %.0f; other-room fittings in the 45 deg cone: %s%s"
                         % (r["eye_in_footprint"], r["mine"], r["mine_by"] or "none", r["engine"], r["behind_walls"] or "none",
                            "; " + "; ".join(bad) if bad else "")))
        exposed = [b for b in r["behind_walls"] if len(b) > 3 and b[3] == 0]
        if r["behind_walls"] and scene_json is None:
            out.append(check("LV2", "not_evaluated", "la4-lying-walls/" + r["id"], (), message="no scene: cannot test that other rooms' fittings are behind walls"))
        elif exposed:
            out.append(check("LV2", "fail", "la4-lying-walls/" + r["id"], ids("LV-LM63"), message="fittings in the cone with no wall in between: %s" % exposed))
    return out


if __name__ == "__main__":
    from ..lightcalc.villa import Villa
    import sys
    for r in run(Villa(), sys.argv[1] if len(sys.argv) > 1 else None):
        print("%-34s eye in bed %s  mine %7.0f cd/m2 (%s)  engine %7.0f (%s)  generic above: %s  other rooms (fixture, room, cd/m2, shell faces crossed): %s" % (
            r["id"], r["eye_in_footprint"], r["mine"], r["mine_by"], r["engine"], r["engine_by"], r["generic_in_room"], r["behind_walls"]))
