import json
import shutil
from pathlib import Path

import pytest

from archpipe.lightcalc.villa import Villa
from archpipe.lightverify import v5_engines as V5, v6_handcalc as V6, v7_convergence as V7

RAD = Path(__file__).resolve().parents[2] / "knowledge" / "lighting-verify" / "radiance"


@pytest.fixture(scope="module")
def villa():
    return Villa()


def _scaled(tmp_path, cluster, k_base=1.0, k_extra=1.0, k_all=1.0):   # base = params.ab (12), extra = the doubled run (24)
    d = json.loads((RAD / (cluster + ".json")).read_text())
    for z in d["zones"].values():
        for ab in z:
            z[ab] = [v * k_all * (k_base if ab == str(d["params"]["ab"]) else k_extra) for v in z[ab]]
    (tmp_path / (cluster + ".json")).write_text(json.dumps(d))
    return tmp_path


def _only_guest_wc():
    V5.run.headline_only = True
    keep = dict(V5.ROOMS)
    V5.ROOMS.clear()
    V5.ROOMS["guest WC"] = keep["guest WC (small wet room)"]
    return keep


def test_v5_direct_agrees_on_real_results(villa, tmp_path):
    shutil.copy(RAD / "B-guest-wc.json", tmp_path)
    keep = _only_guest_wc()
    try:
        L = V5.run(villa, tmp_path, with_cycles=False)
    finally:
        V5.ROOMS.update(keep); V5.run.headline_only = False
    assert abs(L.table[0]["ad_vs_rd"]) < 0.03


def test_v5_catches_a_doubled_engine_output(villa, tmp_path):
    keep = _only_guest_wc()
    try:
        L = V5.run(villa, _scaled(tmp_path, "B-guest-wc", k_all=2.0), with_cycles=False)
    finally:
        V5.ROOMS.update(keep); V5.run.headline_only = False
    assert [r for r in L.results if r.subject == "guest WC"][0].status == "fail"


def test_v6_hand_calc_within_bar_for_a_simple_room(villa):
    L = V6.run(villa, RAD)
    row = next(r for r in L.results if r.subject == "B-guest-wc")
    assert row.status == "pass"


def test_v6_catches_doubled_output(villa, tmp_path):
    L = V6.run(villa, _scaled(tmp_path, "B-guest-wc", k_all=2.0))
    assert [r for r in L.results if r.subject == "B-guest-wc"][0].status == "fail"


def test_v6_parents_bedroom_now_agrees_and_a_wrong_volume_would_not(villa, tmp_path):
    """The 0.68 m2 volume bug is fixed (L6b): the real results agree (+6 %); results scaled to what the entry-sized
    volume produced (143 vs 246 lx) are still caught."""
    row = next(r for r in V6.run(villa, RAD).results if r.subject == "GF-parents-bed")
    assert row.status == "pass"
    bad = next(r for r in V6.run(villa, _scaled(tmp_path, "GF-parents-bed", k_all=0.15)).results if r.subject == "GF-parents-bed")
    assert bad.status == "fail"


def test_v7_flags_unconverged_and_stays_quiet_when_converged(villa, tmp_path):
    bad = V7.run(villa, _scaled(tmp_path, "B-guest-wc", k_extra=1.10), with_grid=False)   # the ab 24 run 10 % above ab 12
    assert any(r.status == "fail" for r in bad.results)
    d = json.loads((RAD / "B-guest-wc.json").read_text())
    for z in d["zones"].values():
        z["24"] = list(z["12"])                      # a run whose doubled-bounce result equals the first
    (tmp_path / "B-guest-wc.json").write_text(json.dumps(d))
    good = V7.run(villa, tmp_path, with_grid=False)
    assert all(r.status == "pass" for r in good.results)
