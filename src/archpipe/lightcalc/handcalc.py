"""L6c: lumen-method style estimate for a SUB-PLANE of an open-plan cluster (LV V6 had none for dining-table, homework-end, daybed).

The whole-room lumen method E = N Phi UF MF / A needs a room; a table inside an open plan is not one. What can be derived by hand
is the same balance split in two, with no point-sum and no Radiance:

  direct    flux that reaches the plane = integral of the luminaire's candela over the SOLID ANGLE whose rays strike the plane
            (angular integration of I(gamma, C) dOmega, not the engine's sum over grid points), divided by the plane area;
  indirect  the cluster's average inter-reflected illuminance, Phi_total rho / (A_surfaces (1 - rho)) with rho the area-weighted
            reflectance of the closed volume (the textbook cavity balance; uniform, so it over-states a plane far from the walls).

E_hand = MF (E_direct + E_indirect). Stated limits: uniform indirect light; no furniture shadows (the engine has none either).
"""
from __future__ import annotations

import math

from .geometry import bbox


def flux_on_rect(pl, rect: tuple, z: float, dg: float = 0.5, dc: float = 1.0) -> float:
    """Lumens of one placement (its `dim` applied) that strike the horizontal rectangle (x0, y0, x1, y1) at height z, by angular
    integration over the sphere below the luminaire."""
    x, y, zz = pl.position
    h = zz - z
    if h <= 0:
        return 0.0
    x0, y0, x1, y1 = rect
    tot = 0.0
    ng, nc = int(90 / dg), int(360 / dc)
    for i in range(ng):
        g = math.radians((i + 0.5) * dg)                  # polar angle from nadir
        r = h * math.tan(g)
        w = math.sin(g) * math.radians(dg) * math.radians(dc)
        for j in range(nc):
            c = math.radians((j + 0.5) * dc)
            px, py = x + r * math.cos(c), y + r * math.sin(c)
            if x0 <= px <= x1 and y0 <= py <= y1:
                d = (math.sin(g) * math.cos(c), math.sin(g) * math.sin(c), -math.cos(g))
                tot += pl.intensity_toward(d) * w
    return tot


def estimate(placements: list, levels: dict, rect: tuple, z: float, room, mf: float = 0.8) -> dict:
    """placements of the cluster (Placement.zone is the zone id), levels {zone: 0..1}, rect the plane, room the lightcalc Room."""
    ax0, ay0, ax1, ay1 = rect
    area = (ax1 - ax0) * (ay1 - ay0)
    phi_plane = phi_total = 0.0
    for p in placements:
        lv = levels.get(p.zone, 0.0)
        if not lv:
            continue
        phi_total += lv * p.dim * p.photometry.integrated_flux()
        if abs(p.position[0] - (ax0 + ax1) / 2) < 3.0 and abs(p.position[1] - (ay0 + ay1) / 2) < 3.0:
            phi_plane += lv * flux_on_rect(p, rect, z)
    poly = list(room.polygon)
    x0, y0, x1, y1 = bbox(poly)
    per = sum(math.dist(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))
    a_floor = abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))) / 2
    a_wall = per * (room.ceiling_z - room.floor_z)
    a_tot = 2 * a_floor + a_wall
    rho = (a_floor * room.rho_floor + a_floor * room.rho_ceiling + a_wall * room.rho_wall) / a_tot
    e_dir = phi_plane / area
    e_ind = phi_total * rho / (a_tot * (1 - rho))
    return dict(e_direct=mf * e_dir, e_indirect=mf * e_ind, e_hand=mf * (e_dir + e_ind), phi_total=phi_total, rho=rho, area=area, surfaces=a_tot)


def main(res_dir: str, out: str = "knowledge/lighting/v6-subplanes.json") -> dict:
    """Hand estimate vs the Radiance result (ab 12, owning scene) for the three open-plan sub-planes LV could not estimate."""
    import json
    from pathlib import Path

    from ..concept.villa_lighting import SCENES
    from . import villa_report as VR
    from .villa import MF, Villa

    v = Villa()
    res = VR.ClusterRes.load(Path(res_dir) / "B-open.json")
    rows = {}
    for p in v.planes():
        if p.id not in ("dining-table", "homework-end", "daybed"):
            continue
        levels = VR.scene_levels(res, SCENES["B-open"], p.scene)
        xs, ys = [q[0] for q in p.polygon], [q[1] for q in p.polygon]
        h = estimate(v.cluster_placements("B-open"), levels, (min(xs), min(ys), max(xs), max(ys)), p.z, v.cluster_room("B-open"), MF)
        eng = res.stats(p.id, levels).em
        rows[p.id] = dict(scene=p.scene, e_hand=round(h["e_hand"], 1), e_direct=round(h["e_direct"], 1), e_indirect=round(h["e_indirect"], 1),
                          radiance=round(eng, 1), ratio=round(eng / h["e_hand"], 3), rho=round(h["rho"], 3), within_25_percent=abs(eng / h["e_hand"] - 1) <= 0.25)
    Path(out).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return rows


if __name__ == "__main__":
    import sys
    for k, r in main(sys.argv[1]).items():
        print(k, r)
