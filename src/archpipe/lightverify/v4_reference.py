"""V4 published reference cases, run through the engine again here (not the L6 frozen numbers).

Expected values are the CIE 171:2006 values as reproduced in DAU Design and Consulting, "Validation of NVIDIA Iray
against CIE 171:2006" (28 Jan 2016; developer.nvidia.com ... Validation of NVIDIA's Iray against CIE 171_20160217.pdf):
  Table 7   case 5.2, second photometry ("CIE T9"): I (cd) and E (lx) at 10 points, 3 m below a point source;
  Table 7   case 5.2, first photometry (I = 1000 cos);
  Table 15  case 5.8, average indirect illuminance Eav for rho = 0.05 ... 0.95 (we run the values the first L6 run skipped).
Not run, with the reason:
  5.3 (area sources) the DAU report gives only charts, no tabulated values;
  5.5 / 5.9-5.14 glass and sky (daylight cases, not the electric-lighting engine);
  5.6 geometry exists only as sketches in the report, no coordinates; 5.7 the report itself marks the table erroneous.
CIE 171 itself is not held; DAU's text is the source and says so on each result.
"""
from __future__ import annotations

import math
from pathlib import Path

from ..lightcalc import refcases as R, synth
from ..lightcalc.direct import Placement, direct_illuminance
from ..lightcalc.radjob import RadJob, RadParams, Sensor, execute
from .common import LayerResult, check
from .sources import CARDS, ids
from ..contracts import SourceCard

TOL = 0.05
SRC52, SRC52B, SRC58 = ids("LV-CIE171-52", "LV-V4-TOL"), ids("LV-CIE171-T9", "LV-V4-TOL"), ids("LV-CIE171-58", "LV-V4-TOL")

# DAU Table 7, second photometry: point -> (incidence deg, d m, I cd, E lx)
T9 = {"A": (0.0, 3.0, 1000.0, 111.11), "B": (9.46, 3.041, 1146.1, 122.25), "C": (18.43, 3.162, 1307.7, 124.08),
      "D": (26.57, 3.354, 1475.5, 117.31), "E": (13.26, 3.082, 1109.1, 113.65), "F": (20.44, 3.202, 1240.9, 113.41),
      "G": (27.79, 3.391, 1335.4, 102.74), "H": (25.24, 3.317, 1113.8, 91.57), "I": (31.0, 3.5, 1166.8, 81.65),
      "J": (35.26, 3.674, 1027.5, 62.16)}


def t9_ies() -> str:
    pts = sorted((v[0], v[2]) for v in T9.values())
    ang = [a for a, _ in pts] + [40.0, 90.0, 180.0]
    cd = [i for _, i in pts] + [0.0, 0.0, 0.0]
    return synth._ies("CIE T9 photometry (axisymmetric through the published points)", ang, cd)


def case_5_2_t9(workdir: Path) -> list[dict]:
    text = t9_ies()
    pl = Placement("S", synth.load_text(text, "t9"), (0.0, 0.0, 3.0), meta={"ies_text": text})
    sens, ks = [], []
    for k, (inc, d, i, e) in T9.items():
        r = 3.0 * math.tan(math.radians(inc))
        sens.append(Sensor(r, 0.0, 0.0))
        ks.append(k)
    res = execute(RadJob("c52t9", None, [pl], sens, RadParams(ab=0)), workdir, host=None)["Z1"][0]
    rows = []
    for k, s, rad in zip(ks, sens, res):
        ana = direct_illuminance([pl], (s.x, s.y, s.z))
        e = T9[k][3]
        rows.append(dict(point=k, published=e, analytic=ana, radiance=rad, err_analytic=ana / e - 1, err_radiance=rad / e - 1))
    return rows


def run(workdir="out/LV/ref", rhos=(0.05, 0.1, 0.3, 0.4, 0.6, 0.7, 0.8)) -> LayerResult:
    wd = Path(workdir)
    L = LayerResult("V4")
    c52 = R.case_5_2(wd / "c52")
    for r in c52["rows"]:
        L.results.append(check("LV4", "pass" if abs(r["analytic_err"]) <= TOL and abs(r["radiance_err"]) <= TOL else "fail",
                               "5.2-diffuse/" + r["point"], SRC52, achieved=r["analytic_lx"], required=r["expected_E_lx"], unit="lx",
                               message="analytic %.2f lx, Radiance %.2f lx, published %.2f lx" % (r["analytic_lx"], r["radiance_lx"], r["expected_E_lx"])))
    for r in case_5_2_t9(wd / "c52t9"):
        ok = abs(r["err_analytic"]) <= TOL and abs(r["err_radiance"]) <= TOL
        L.results.append(check("LV4", "pass" if ok else "fail", "5.2-T9/" + r["point"], SRC52B, achieved=round(r["analytic"], 2),
                               required=r["published"], unit="lx",
                               message="analytic %.2f lx, Radiance %.2f lx, published %.2f lx" % (r["analytic"], r["radiance"], r["published"])))
        L.table.append(dict(case="5.2-T9", **r))
    c58 = R.case_5_8(wd / "c58", rhos=tuple(rhos))
    for r in c58["rows"]:
        err = r["err_vs_published"]
        L.results.append(check("LV4", "pass" if abs(err) <= TOL else "fail", "5.8/rho=%.2f" % r["rho"], SRC58,
                               achieved=round(r["E_indirect_ab2"], 2), required=r["published_Eav"], unit="lx",
                               message="Radiance indirect Eav %.2f lx vs published %.2f lx (%+.1f %%); closed form %.2f lx; ab %d vs %d differ %.2f %%"
                               % (r["E_indirect_ab2"], r["published_Eav"], 100 * err, r["closed_form_indirect"], r["ab"], r["ab2"],
                                  100 * r["convergence_ab_vs_2ab"])))
        L.table.append(dict(case="5.8", **{k: r[k] for k in ("rho", "E_indirect_ab2", "published_Eav", "err_vs_published")}))
    L.notes.append("not run: 5.3 (charts only), 5.5 and 5.9-5.14 (glass/sky), 5.6 (sketch geometry only), 5.7 (table erroneous in the source)")
    return L
