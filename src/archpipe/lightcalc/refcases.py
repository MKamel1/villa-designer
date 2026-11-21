"""Reference cases for the lighting engine, with published expected values.

Source of every expected number below: CIE 171:2006 "Test cases to assess the accuracy of lighting
computer programs", AS REPRODUCED in DAU Design and Consulting, "Validation of NVIDIA Iray against
CIE 171:2006" (2016), tables 7 and 15, because the CIE report itself (paywalled) is not held. Table 19
(case 5.7) is listed there as erroneous in the original, so case 5.7 is NOT used.
Nothing here is invented; the Iray program's own computed values are not used as expected values.

  CASE_5_2 : point source, diffuse (cosine) photometry I = 1000 cos(theta) cd, ten points on a plane
             3 m below the source. Expected E = CIE column 'Diffuse photometry / Experimental'.
  CASE_5_8 : 4 x 4 x 4 m room, all surfaces uniform diffusers, isotropic point source 10,000 lm at the
             centre. Expected: average indirect illuminance over the surfaces, the CIE 'Eav' row
             (0.5 -> 104.00, 0.8 -> 417.00, ...), which also equals the closed form
             Phi * rho / (A (1 - rho)) with Phi = 10,000 lm, A = 96 m2.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from . import synth
from .direct import Placement, direct_illuminance
from .radjob import RadJob, RadParams, Room, Sensor, execute, total_lux

# --- CIE 171:2006 case 5.2 (DAU Table 7, 'Diffuse photometry', CIE experimental column) ---
CASE_5_2_H = 3.0
CASE_5_2_POINTS = {   # id: (x, y offsets from the point under the source [m], d [m], incidence [deg], I [cd], E [lx])
    "A": ((0.0, 0.0), 3.0, 0.0, 1000.0, 111.11),
    "B": ((0.5, 0.0), 3.041, 9.46, 986.4, 105.21),
    "C": ((1.0, 0.0), 3.162, 18.43, 948.7, 90.02),
    "D": ((1.5, 0.0), 3.354, 26.57, 894.4, 71.11),
    "E": ((0.5, 0.5), 3.082, 13.26, 973.3, 99.73),
    "F": ((1.0, 0.5), 3.202, 20.44, 937.0, 85.64),
    "G": ((1.5, 0.5), 3.391, 27.79, 884.7, 68.06),
    "H": ((1.0, 1.0), 3.317, 25.24, 904.5, 74.36),
    "I": ((1.5, 1.0), 3.5, 31.0, 857.2, 59.98),
    "J": ((1.5, 1.5), 3.674, 35.26, 816.5, 49.39),
}
# NB: the (x, y) offsets are DERIVED here from the published d and incidence columns
# (r = H tan(incidence)); the published table does not list coordinates in the DAU text layer.

# --- CIE 171:2006 case 5.8 (DAU Table 15, 'Eav' = average INDIRECT illuminance, lx) ---
CASE_5_8_FLUX = 10000.0
CASE_5_8_SIDE = 4.0
CASE_5_8_EAV = {0.05: 5.48, 0.10: 11.60, 0.20: 26.00, 0.30: 44.60, 0.40: 69.40, 0.50: 104.00,
                0.60: 156.00, 0.70: 243.00, 0.80: 417.00, 0.90: 937.00, 0.95: 1979.00}


def case_5_2_expected_check() -> list[dict]:
    """The published rows must satisfy their own closed form E = I cos(inc)/d^2 (guards the transcription)."""
    rows = []
    for k, ((x, y), d, inc, i, e) in CASE_5_2_POINTS.items():
        calc = i * math.cos(math.radians(inc)) / d ** 2
        r = math.hypot(x, y)
        rows.append({"point": k, "published_E": e, "formula_E": round(calc, 2),
                     "d_from_xy": round(math.hypot(r, CASE_5_2_H), 3), "d_published": d,
                     "rel_err_formula": abs(calc - e) / e})
    return rows


def case_5_2(workdir: Path, host: str | None = None) -> dict:
    ies = synth.cosine_ies_text(1000.0)
    ph = synth.load_text(ies, "cosine1000")
    pl = Placement("S", ph, (0.0, 0.0, CASE_5_2_H), meta={"ies_text": ies})
    sensors, ids = [], []
    for k, ((x, y), *_r) in CASE_5_2_POINTS.items():
        sensors.append(Sensor(x, y, 0.0)); ids.append(k)
    job = RadJob("case_5_2", None, [pl], sensors, RadParams(ab=0))
    res = execute(job, workdir, host=host)
    rad = res["Z1"][0]
    rows = []
    for k, e_rad, s in zip(ids, rad, sensors):
        exp = CASE_5_2_POINTS[k][4]
        ana = direct_illuminance([pl], (s.x, s.y, s.z))
        rows.append({"point": k, "expected_E_lx": exp, "analytic_lx": round(ana, 3), "radiance_lx": round(e_rad, 3),
                     "analytic_err": round(ana / exp - 1, 5), "radiance_err": round(e_rad / exp - 1, 5)})
    return {"case": "CIE 171:2006 5.2 (diffuse photometry)", "rows": rows,
            "max_abs_err_analytic": max(abs(r["analytic_err"]) for r in rows),
            "max_abs_err_radiance": max(abs(r["radiance_err"]) for r in rows)}


def cube_face_sensors(side: float, n: int, eps: float = 0.0005) -> list[Sensor]:
    """n x n cell-centred sensors on each of the six faces of a cube [0,side]^3, normals pointing inward."""
    out = []
    c = [(i + 0.5) * side / n for i in range(n)]
    for u in c:
        for v in c:
            out += [Sensor(u, v, eps, 0, 0, 1), Sensor(u, v, side - eps, 0, 0, -1),
                    Sensor(u, eps, v, 0, 1, 0), Sensor(u, side - eps, v, 0, -1, 0),
                    Sensor(eps, u, v, 1, 0, 0), Sensor(side - eps, u, v, -1, 0, 0)]
    return out


def case_5_8(workdir: Path, rhos=(0.2, 0.5, 0.8), host: str | None = None, n: int = 6) -> dict:
    side = CASE_5_8_SIDE
    ies = synth.isotropic_ies_text(CASE_5_8_FLUX / (4 * math.pi))
    ph = synth.load_text(ies, "iso10klm")
    pl = Placement("S", ph, (side / 2, side / 2, side / 2), meta={"ies_text": ies})
    sensors = cube_face_sensors(side, n)
    area = 6 * side * side
    rows = []
    for rho in rhos:
        poly = ((0, 0), (side, 0), (side, side), (0, side))
        room = Room(poly, 0.0, side, rho_floor=rho, rho_wall=rho, rho_ceiling=rho)
        # bounces needed so that the truncated tail rho^(ab+1) is under ~1 % of the indirect term, and a doubled run for convergence
        ab = max(8, math.ceil(math.log(0.01) / math.log(rho)))
        job = RadJob(f"case_5_8_rho{int(round(rho * 100)):02d}", room, [pl], sensors,
                     RadParams(ab=ab, ab_extra=(2 * ab,), ad=1024, as_=512, aa=0.1))
        res = execute(job, Path(workdir) / f"rho{int(round(rho * 100)):02d}", host=host)
        r = res["Z1"]
        n_s = len(sensors)
        e0 = sum(r[0]) / n_s
        out = {"rho": rho, "ab": ab, "ab2": 2 * ab}
        for key, a in (("ab", ab), ("ab2", 2 * ab)):
            out[f"E_indirect_{key}"] = sum(r[a]) / n_s - e0
        out["E_direct_avg_radiance"] = e0
        out["E_direct_avg_closed_form"] = CASE_5_8_FLUX / area
        out["closed_form_indirect"] = CASE_5_8_FLUX * rho / (area * (1 - rho))
        out["published_Eav"] = CASE_5_8_EAV.get(rho)
        out["err_vs_published"] = out["E_indirect_ab2"] / out["published_Eav"] - 1 if out["published_Eav"] else None
        out["err_vs_closed_form"] = out["E_indirect_ab2"] / out["closed_form_indirect"] - 1
        out["convergence_ab_vs_2ab"] = out["E_indirect_ab"] / out["E_indirect_ab2"] - 1
        rows.append(out)
    return {"case": "CIE 171:2006 5.8 (internal reflected component)", "sensors_per_run": len(sensors), "rows": rows}


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default="out/L6/refcases")
    ap.add_argument("--host", default=None)
    ap.add_argument("--out", default="knowledge/lighting/L6-reference-results.json")
    ap.add_argument("--rhos", default="0.2,0.5,0.8")
    a = ap.parse_args(argv)
    wd = Path(a.workdir)
    result = {
        "case_5_2_transcription_check": case_5_2_expected_check(),
        "case_5_2": case_5_2(wd / "c52", a.host),
        "case_5_8": case_5_8(wd / "c58", tuple(float(x) for x in a.rhos.split(",")), a.host),
        "source": ("CIE 171:2006 expected values as reproduced in DAU 'Validation of NVIDIA Iray against CIE 171:2006' "
                   "(2016) Tables 7 and 15; CIE 171 itself not held"),
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps({"c52_max_err_analytic": result["case_5_2"]["max_abs_err_analytic"],
                      "c52_max_err_radiance": result["case_5_2"]["max_abs_err_radiance"],
                      "c58": [(r["rho"], round(r["err_vs_published"], 4), round(r["convergence_ab_vs_2ab"], 4))
                              for r in result["case_5_8"]["rows"]]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
