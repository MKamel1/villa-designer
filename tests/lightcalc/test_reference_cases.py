"""Reference cases: committed workstation run results vs published values; live Radiance run when available.

The committed JSON (knowledge/lighting/L6-reference-results.json) is the output of
`python -m archpipe.lightcalc.refcases --host ai-workstation` (Radiance 6.0.1). A live run is skipped unless
Radiance is installed locally or ARCHPIPE_L6_SSH names a host that has it.
"""
import json
import os
from pathlib import Path

import pytest

from archpipe.lightcalc import refcases
from archpipe.lightcalc.radjob import have_local_radiance

REF = Path(__file__).resolve().parents[2] / "knowledge" / "lighting" / "L6-reference-results.json"
DATA = json.loads(REF.read_text(encoding="utf-8"))


def test_case_5_2_published_values_unchanged():
    exp = {k: v[4] for k, v in refcases.CASE_5_2_POINTS.items()}
    assert exp == {"A": 111.11, "B": 105.21, "C": 90.02, "D": 71.11, "E": 99.73, "F": 85.64, "G": 68.06,
                   "H": 74.36, "I": 59.98, "J": 49.39}
    assert refcases.CASE_5_8_EAV[0.5] == 104.00 and refcases.CASE_5_8_EAV[0.8] == 417.00


def test_case_5_8_published_eav_matches_closed_form():
    """The published Eav row is Phi*rho/(A(1-rho)) with Phi = 10,000 lm, A = 96 m2 (to its printed precision)."""
    for rho, eav in refcases.CASE_5_8_EAV.items():
        cf = 10000 * rho / (96 * (1 - rho))
        assert eav == pytest.approx(cf, rel=0.01), rho


def test_committed_case_5_2_within_5_percent_and_much_better():
    for row in DATA["case_5_2"]["rows"]:
        assert abs(row["radiance_err"]) < 0.05 and abs(row["analytic_err"]) < 0.05
    assert DATA["case_5_2"]["max_abs_err_radiance"] < 0.002


def test_committed_case_5_8_within_5_percent_and_converged():
    rows = DATA["case_5_8"]["rows"]
    assert {r["rho"] for r in rows} >= {0.2, 0.5, 0.8}
    for r in rows:
        assert abs(r["err_vs_published"]) < 0.05, r["rho"]
        assert abs(r["convergence_ab_vs_2ab"]) < 0.01, r["rho"]          # ab N and ab 2N agree to 1 %


def test_negative_a_wrong_reflectance_would_fail_the_comparison():
    """The check can fail: the rho=0.5 run compared against the rho=0.8 published value is far outside 5 %."""
    r = [x for x in DATA["case_5_8"]["rows"] if x["rho"] == 0.5][0]
    assert abs(r["E_indirect_ab2"] / refcases.CASE_5_8_EAV[0.8] - 1) > 0.5


LIVE = have_local_radiance() or os.environ.get("ARCHPIPE_L6_SSH")


@pytest.mark.skipif(not LIVE, reason="no Radiance locally and ARCHPIPE_L6_SSH not set")
def test_live_case_5_2(tmp_path):
    res = refcases.case_5_2(tmp_path, host=os.environ.get("ARCHPIPE_L6_SSH"))
    assert res["max_abs_err_radiance"] < 0.005
