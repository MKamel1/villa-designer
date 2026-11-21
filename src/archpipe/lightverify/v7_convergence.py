"""V7 convergence: does the number move when the calculation is made finer?  Bar: < 3 % (LV-V7-CONV).

  bounces  every plane's total Em at ab 6 vs ab 12 (the engine's own cached Radiance runs, 'full' scene);
  grid     the analytic direct Em on the engine grid vs the same plane at half the pitch (direct light is what the grid
           samples; Radiance's ad/as doubling is NOT re-run here: ab doubling is the only Radiance setting varied).
Room-plane grids are coarse by EN 12464-1 cell rule, so a grid change > 3 % is reported as fail, never excused.
"""
from __future__ import annotations

from pathlib import Path

from .common import LayerResult, check
from .sources import ids

TOL = 0.03
SRC = ids("LV-V7-CONV")


def grid_em(pl, placements, spacing):
    from ..lightcalc.direct import direct_illuminance
    from ..lightcalc.geometry import grid_in_polygon
    from ..lightcalc.villa import MF
    pts, dx, dy = grid_in_polygon(list(pl.polygon), spacing=spacing, border=0.0)
    return sum(direct_illuminance(placements, (x, y, pl.z)) for x, y in pts) / len(pts) * MF, (dx, dy)


def run(villa, rad_dir, with_grid=True) -> LayerResult:
    from ..lightcalc import villa_report as VR
    from ..lightcalc.villa import cluster_of
    L = LayerResult("V7")
    planes = villa.planes()
    for jf in sorted(Path(rad_dir).glob("*.json")):
        cl = jf.stem
        res = VR.ClusterRes.load(jf)
        lv = VR.full_levels(res)
        pls = [p for p in planes if p.id in res.slices and cluster_of(p.room) == cl]
        func = [p for p in villa.cluster_placements(cl) if p.layer not in VR.NIGHT_LAYERS]
        for pl in pls:
            msg, bad = [], False
            if res.ab2:
                a, b = res.stats(pl.id, lv).em, res.stats(pl.id, lv, ab=res.ab2).em
                ch = a / b - 1 if b else 0.0
                msg.append("ab %d -> %d: %.1f -> %.1f lx (%+.2f %%)" % (res.ab, res.ab2, a, b, 100 * ch))
                bad |= abs(ch) >= TOL
            else:
                msg.append("no ab doubling run")
                bad = None
            if with_grid and func:
                from .v3_sensors import plane_points
                _, dx, dy = plane_points(pl)
                e1, _ = grid_em(pl, func, pl.spacing)
                e2, (hx, hy) = grid_em(pl, func, min(dx, dy) / 2)
                g = e1 / e2 - 1 if e2 else 0.0
                msg.append("direct grid %.2f m -> %.2f m: %.1f -> %.1f lx (%+.2f %%)" % (min(dx, dy), min(hx, hy), e1, e2, 100 * g))
                bad = True if abs(g) >= TOL else bad
            status = "not_evaluated" if bad is None else ("fail" if bad else "pass")
            L.results.append(check("LV7", status, pl.id, SRC, message="; ".join(msg)))
            L.table.append(dict(plane=pl.id, cluster=cl, status=status, msg="; ".join(msg)))
            L.mark(pl.room, status)
    return L
