"""V6 hand calculation (lumen method) per cluster, against the engine's room planes ('full' scene).

    E_hand = MF * Phi * UF / A_floor
    UF = d_f + [sum_i rho_i d_i] / (1 - rho_bar) * A_floor / A_tot
Phi     lumens of the functional (non-night) fittings in the cluster, from the design (record flux x dimmer);
d_i     share of that flux first reaching floor / walls / ceiling, by casting the fittings' rays (candela-weighted) into the room;
rho_bar area-weighted mean reflectance of floor, walls and ceiling (0.33 / 0.80 / 0.85, the engine's ASSUMED values).
Inter-reflection is the uniform closed-room flux transfer  R = Phi sum(rho_i d_i) / (1 - rho_bar)  spread over all surfaces by
area: the same closed form CIE 171:2006 case 5.8 publishes (V4 shows the engine reproducing it to about 1 %).
UF SOURCE: derived here from first-incidence geometry plus that closed form. No published utilisation-factor table is
held, so none is used (never invent a figure). Gross-error check (units, 2x errors), bar +/-25 % (LV-V6-HAND); uniform
inter-reflection is wrong for tall narrow rooms and open plans, so a miss is reported with its numbers, not argued away.
Compared with the area-weighted mean of the cluster's room-* planes (their heights differ: floor, 0.75 m, 0.92 m).
"""
from __future__ import annotations

import math

from .common import LayerResult, check
from .sources import ids

TOL = 0.25
SRC = ids("LV-V6-HAND", "LV-CIE171-58")


def first_incidence(p, poly, floor, ceiling, steps=36, azimuths=24):
    """Flux split of one fitting by the surface its rays first reach: (floor, walls, ceiling) shares, by ray casting
    each sampled direction (weighted by candela x sin) to the floor/ceiling plane and testing the hit against the polygon."""
    from ..lightcalc.geometry import point_in_polygon
    x0, y0, z0 = p.position
    acc = {"f": 0.0, "w": 0.0, "c": 0.0}
    for i in range(steps):
        th = math.pi * (i + 0.5) / steps
        for j in range(azimuths):
            ph = 2 * math.pi * (j + 0.5) / azimuths
            d = (math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th))
            w = p.intensity_toward(d) * math.sin(th)
            if w <= 0:
                continue
            if d[2] < -1e-9:
                t, k, z = (floor - z0) / d[2], "f", floor
            elif d[2] > 1e-9:
                t, k, z = (ceiling - z0) / d[2], "c", ceiling
            else:
                acc["w"] += w
                continue
            hit = (x0 + t * d[0], y0 + t * d[1])
            acc[k if point_in_polygon(hit, poly) else "w"] += w
    tot = sum(acc.values())
    return {k: v / tot for k, v in acc.items()} if tot else acc


def hand_estimate(villa, cluster) -> dict:
    from ..lightcalc import villa_report as VR
    from ..lightcalc.geometry import area, perimeter
    from ..lightcalc.villa import MF
    room = villa.cluster_room(cluster)
    poly = list(room.polygon)
    af = area(poly)
    h = room.ceiling_z - room.floor_z
    aw = perimeter(poly) * h
    at = 2 * af + aw
    rho = (af * room.rho_floor + af * room.rho_ceiling + aw * room.rho_wall) / at
    phi = 0.0
    d = {"f": 0.0, "w": 0.0, "c": 0.0}
    for p in villa.cluster_placements(cluster):
        if p.layer in VR.NIGHT_LAYERS:
            continue
        f = p.dim * p.photometry.integrated_flux()
        phi += f
        for k, v in first_incidence(p, poly, room.floor_z, room.ceiling_z).items():
            d[k] += f * v
    d = {k: v / phi for k, v in d.items()} if phi else d
    r_first = d["f"] * room.rho_floor + d["w"] * room.rho_wall + d["c"] * room.rho_ceiling
    uf = d["f"] + r_first / (1 - rho) * af / at
    return dict(cluster=cluster, phi=phi, direct_floor=d["f"], direct_wall=d["w"], direct_ceiling=d["c"], rho_bar=rho,
                A_floor=af, A_tot=at, UF=uf, E_hand=MF * phi * uf / af)


def run(villa, rad_dir) -> LayerResult:
    from pathlib import Path
    from ..lightcalc import villa_report as VR
    L = LayerResult("V6")
    planes = villa.planes()
    from ..lightcalc.villa import cluster_of
    for jf in sorted(Path(rad_dir).glob("*.json")):
        cl = jf.stem
        mine = [p for p in planes if p.id.startswith("room-") and cluster_of(p.room) == cl]
        if not mine:
            continue
        res = VR.ClusterRes.load(jf)
        lv = VR.full_levels(res)
        from ..lightcalc.geometry import area
        tot = sum(area(list(p.polygon)) for p in mine)
        em = sum(res.stats(p.id, lv).em * area(list(p.polygon)) for p in mine) / tot
        h = hand_estimate(villa, cl)
        ratio = em / h["E_hand"]
        ok = abs(ratio - 1) <= TOL
        L.table.append(dict(h, E_engine=em, ratio=ratio))
        L.results.append(check("LV6", "pass" if ok else "fail", cl, SRC, achieved=round(em, 1), required=round(h["E_hand"], 1), unit="lx",
                               message="engine room-plane mean %.0f lx vs lumen method %.0f lx (%+.0f %%): %.0f lm, first incidence floor %.2f / wall %.2f / ceiling %.2f, rho_bar %.2f, UF %.2f"
                               % (em, h["E_hand"], 100 * (ratio - 1), h["phi"], h["direct_floor"], h["direct_wall"], h["direct_ceiling"], h["rho_bar"], h["UF"])))
        for r in {p.room for p in mine}:
            L.mark(r, "pass" if ok else "fail")
    return L
