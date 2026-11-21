"""V3 measurement validity: every sensor the engine reads, tested against all scene geometry.

For each calculation plane the engine uses (lightcalc.villa_planes) the very grid points `roomcalc` hands to Radiance
(`geometry.grid_in_polygon`) are shot with a vertical ray into the workstation-built scene (`scene_geom`):
  inside   an odd number of distinct surfaces of one object above the point (the vase on the dining-table sensor);
  under    an object's surface within 50 mm above the point (occluded);
  height   for planes that sit ON a surface (table, desk, worktop, basin): the gap to the highest upward surface below
           the point must be within 5 mm.
Ceiling slabs and the storey above are not objects: the ray is cut at the first ceiling hit.
"""
from __future__ import annotations

from collections import defaultdict

from .common import LayerResult, check
from .sources import ids

UNDER_TOL = 0.050
HEIGHT_TOL = 0.005
ROOM_BLOCK_MAX = 0.10          # policy: a general room plane may lose up to 10 % of its points to furniture at 0.75 m
SRC = ids("LV-V3-CLEAR")
HOSTED = {"island-prep", "island-seating", "cooktop", "sink", "dining-table", "homework-end", "dirty-kitchen-run",
          "study-desk", "study-adult-desk", "ka-desk-1", "ka-desk-2", "kb-desk", "cinema-desk",
          "fb-basin", "pe-basin", "gwc-basin"}
CEILING_PREFIX = ("ceiling", "shell-000-ceiling")


def _is_ceiling(owner) -> bool:
    return str(owner).startswith(CEILING_PREFIX)


GRAZE = 0.003


def _inside_owners(ts, x, y, z):
    hits = ts.vertical_hits(x, y, z)
    cut = next((h[0] for h in hits if _is_ceiling(h[1])), None)
    if cut is not None:
        hits = [h for h in hits if h[0] < cut - 1e-6]
    per = defaultdict(list)
    for dz, owner, kind, nz in hits:
        per[owner].append((dz, nz))
    return {o: zs[0][0] for o, zs in per.items() if len(zs) % 2 == 1 and zs[0][1] > 0}


def point_findings(ts, x, y, z):
    """[(kind, owner, dz)] for one sensor point; kind in 'inside' | 'under'.
    A ray that only grazes a silhouette edge is not 'inside': 'inside' must also hold on all 4 rays offset by 3 mm."""
    hits = ts.vertical_hits(x, y, z)
    cut = next((h[0] for h in hits if _is_ceiling(h[1])), None)
    if cut is not None:
        hits = [h for h in hits if h[0] < cut - 1e-6]
    per = defaultdict(list)
    for dz, owner, kind, nz in hits:
        per[owner].append((dz, nz))
    out = []
    for owner, zs in per.items():
        # inside a closed object: an odd number of surfaces above AND the nearest one faces up (we see its inner side);
        # an open sheet (diffuser, curtain) above the sensor has an odd count but faces down.
        if len(zs) % 2 == 1 and zs[0][1] > 0:
            votes = sum(owner in _inside_owners(ts, x + a, y + b, z)
                        for a, b in ((GRAZE, 0), (-GRAZE, 0), (0, GRAZE), (0, -GRAZE)))
            if votes >= 4:
                out.append(("inside", owner, zs[0][0]))
    inside_owners = {o for k, o, _ in out}
    for dz, owner, kind, nz in hits:
        if dz <= UNDER_TOL and owner not in inside_owners:
            out.append(("under", owner, dz))
            break
    return out


def plane_points(pl):
    from ..lightcalc.geometry import grid_in_polygon
    pts, dx, dy = grid_in_polygon(list(pl.polygon), spacing=pl.spacing, border=0.0)
    return pts, dx, dy


def area_blocked(ts, pl, pitch=0.10) -> float:
    """Fraction of the plane polygon (sampled every 100 mm) that lies inside an object: the area view of the same test."""
    from ..lightcalc.geometry import grid_in_polygon
    pts, _, _ = grid_in_polygon(list(pl.polygon), spacing=pitch, border=0.0)
    if not pts:
        return 0.0
    bad = sum(1 for x, y in pts if _inside_owners(ts, x, y, pl.z))
    return bad / len(pts)


def check_plane(ts, pl) -> dict:
    pts, dx, dy = plane_points(pl)
    bad, gaps = [], []
    for x, y in pts:
        f = point_findings(ts, x, y, pl.z)
        if f:
            bad.append((x, y, f))
        sb = ts.surface_below(x, y, pl.z, max_depth=0.25)
        if sb is not None:
            gaps.append(round(sb[0] * 500) / 500)          # 2 mm bins
    hosted = pl.id in HOSTED
    mode_gap = max(set(gaps), key=gaps.count) if gaps else None   # the host top is the surface most points sit on
    row = dict(plane=pl.id, room=pl.room, z=pl.z, n=len(pts), spacing=(dx, dy), blocked=len(bad), hosted=hosted,
               blocked_owners=sorted({o for _, _, f in bad for _, o, _ in f}),
               worst_gap_mm=(abs(mode_gap) * 1000 if gaps else None), n_surface=len(gaps), area_blocked=area_blocked(ts, pl))
    row["first_bad"] = bad[0][:2] if bad else None
    return row


def check_sensors(v, ts) -> LayerResult:
    L = LayerResult("V3")
    for pl in v.planes():
        r = check_plane(ts, pl)
        L.table.append(r)
        general = pl.id.startswith("room-")
        frac = r["blocked"] / max(1, r["n"])
        problems = []
        if r["blocked"] and not general:
            problems.append("%d of %d sensor points inside or under %s (first at x=%.2f y=%.2f)"
                            % (r["blocked"], r["n"], ", ".join(r["blocked_owners"][:4]), *r["first_bad"]))
        if r["blocked"] and general and frac > ROOM_BLOCK_MAX:
            problems.append("%d of %d (%.0f %%) points inside or under %s" % (r["blocked"], r["n"], 100 * frac,
                                                                           ", ".join(r["blocked_owners"][:4])))
        if r["hosted"]:
            if r["n_surface"] == 0:
                problems.append("no host surface found within 100 mm below the plane (plane z=%.3f)" % pl.z)
            elif r["worst_gap_mm"] > HEIGHT_TOL * 1000:
                problems.append("plane %.0f mm above its host surface (limit %.0f mm)" % (r["worst_gap_mm"], HEIGHT_TOL * 1000))
        status = "fail" if problems else "pass"
        L.results.append(check("LV3", status, pl.id, SRC, achieved=float(r["blocked"]), required=0.0, unit="blocked points",
                               message=("; ".join(problems) if problems else
                                        "%d points clear%s" % (r["n"], " (%d of %d blocked, within the room-plane allowance)" % (r["blocked"], r["n"]) if r["blocked"] else "")),
                               element_ids=tuple(r["blocked_owners"][:6])))
        L.mark(pl.room, status)
    return L
