"""L6b: quick analytic reports on the current design (no Radiance): LA13 route, LA9, LA8, LA6, LPD.

    PYTHONPATH=src python -m archpipe.lightcalc.villa_probe
"""
from __future__ import annotations

from . import villa_checks as VC
from .villa import Villa


def main():
    v = Villa()
    for r in VC.check_la13(v) + VC.check_la9(v) + VC.check_la6(v.fixtures) + VC.check_la8(v.fixtures):
        print(r.criterion, r.status, r.subject, "|", r.message)
    rows = VC.lpd_rows(v)
    tot_w = sum(r["watts"] for r in rows)
    tot_a = sum(r["area_m2"] for r in rows)
    print("LPD overall %.2f W/m2 (%.0f W over %.0f m2)" % (tot_w / tot_a, tot_w, tot_a))


if __name__ == "__main__":
    main()
