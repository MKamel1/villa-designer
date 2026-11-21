"""L6b: solve per-zone driver outputs and scene levels from the per-zone Radiance results.

Light transport is linear, so for a scene with zone levels L_z and driver factors d_z a plane's mean illuminance is
    Em_p = sum_z L_z * d_z * E_pz          (E_pz: Em of plane p from zone z at driver 1.0, level 1.0, from Radiance)
Drivers are the fixed commissioning setting (constant-current output) of a zone; levels are the scene's dim value.
Two solves, both on measured per-zone results:
  drivers(): for every average-gauged task plane, in the scene that owns its card, make Em_p = target by choosing the
             driver factor of the zones that scene lists as tunable (level 1.0 and flagged); least squares on the
             relative error, coordinate descent, bounds [lo, hi].
  nothing else is tuned: other zones keep the scene's stated level.
"""
from __future__ import annotations

from . import villa_report as VR


def solve(res_by_cluster: dict, planes: list, scenes: dict, tunable: set, lo: float = 0.15, hi: float = 3.0,
          init: dict | None = None, sweeps: int = 400) -> dict:
    """Return {zone: d}. scenes: {cluster: {scene: {key: level}}}; tunable: set of zone ids (full ids)."""
    d = {z: 1.0 for z in tunable}
    if init:
        d.update({z: v for z, v in init.items() if z in d})
    rows = []         # (plane, target, {zone: level*E_pz for tunable}, fixed Em)
    for p in planes:
        cl = next((c for c, r in res_by_cluster.items() if p.id in r.slices and r.name.split("-", 1)[-1] == c), None)
        if cl is None or p.gauge != "average":
            continue
        res = res_by_cluster[cl]
        lev = VR.scene_levels(res, scenes[cl], p.scene)
        var, fixed = {}, 0.0
        for z, L in lev.items():
            if not L:
                continue
            em = res.stats(p.id, {z: L}).em
            if z in tunable:
                var[z] = em
            else:
                fixed += em
        if var:
            rows.append((p.id, p.target, var, fixed))
    for _ in range(sweeps):
        for z in d:
            num = den = 0.0
            for _pid, t, var, fixed in rows:
                if z not in var:
                    continue
                rest = fixed + sum(d[k] * v for k, v in var.items() if k != z)
                a = var[z] / t
                num += a * (1.0 - rest / t)
                den += a * a
            if den > 0:
                d[z] = min(hi, max(lo, num / den))
    return d, rows


def residuals(rows: list, d: dict) -> list[tuple]:
    out = []
    for pid, t, var, fixed in rows:
        em = fixed + sum(d[z] * v for z, v in var.items())
        out.append((pid, t, em, em / t))
    return out
