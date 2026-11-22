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


def test_a_renderer_source_change_invalidates_the_cycles_cache(tmp_path, monkeypatch):
    """L6d: a villa_scene.py fix was invisible to a re-run because the key covered only the job. Now the renderer sources are in it."""
    import json
    import subprocess
    from archpipe.lightverify import v5_engines as V5
    src = tmp_path / "blender"
    src.mkdir()
    (src / "villa_scene.py").write_text("GAIN = 1.0\n")
    monkeypatch.setattr(V5, "RENDERER_DIR", src)
    ids = []

    def fake(cmd, **kw):
        if "submit" in cmd:
            ids.append(cmd[cmd.index("--id") + 1])
            op = [c for c in cmd][-1]
            open(op, "w").write(json.dumps({"readings": []}))
        return subprocess.CompletedProcess(cmd, 0, "", "")
    monkeypatch.setattr(V5.subprocess, "run", fake)
    job, w = {"k": 1}, tmp_path / "w"
    V5.run_cycles(job, w)
    V5.run_cycles(job, w)
    assert len(ids) == 1                                     # unchanged renderer: cached
    (src / "villa_scene.py").write_text("GAIN = 1.094\n")    # the renderer fix
    V5.run_cycles(job, w)
    assert len(ids) == 2 and ids[0] != ids[1]                # changed: re-submitted under a new jobq id


def _sub_file(tmp_path, **edits):
    rows = json.loads(V6.SUBPLANES.read_text())
    for pid, e in edits.items():
        rows[pid].update(e)
    f = tmp_path / "sub.json"
    f.write_text(json.dumps(rows))
    return f


def test_v6_judges_the_three_subplanes_from_the_engine_lanes_file(villa):
    from archpipe.lightverify.common import LayerResult
    L = LayerResult("V6")
    V6.subplanes(villa, RAD, L)
    assert set(L.planes) == {"dining-table", "homework-end", "daybed"}
    assert all(s == "pass" for s in L.planes.values()), [r.message for r in L.results]


def test_v6_subplane_with_a_stale_radiance_value_or_wrong_estimate_fails(villa, tmp_path):
    from archpipe.lightverify.common import LayerResult
    L = LayerResult("V6")
    V6.subplanes(villa, RAD, L, _sub_file(tmp_path, **{"daybed": {"radiance": 150.0}, "dining-table": {"e_hand": 60.0, "e_direct": 40.0, "e_indirect": 20.0}}))
    assert L.planes["daybed"] == "fail" and "stale" in next(r.message for r in L.results if r.subject == "daybed")
    assert L.planes["dining-table"] == "fail"                # hand 60 lx vs ~104 lx engine: outside +/-25 %
    assert L.planes["homework-end"] == "pass"
