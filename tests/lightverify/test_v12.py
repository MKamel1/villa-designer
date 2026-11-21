import pytest
from archpipe.lightcalc.villa import Villa
from archpipe.lightverify import v12_headroom as V12


@pytest.fixture(scope="module")
def villa():
    return Villa()


def test_current_design_has_headroom_everywhere(villa):
    L = V12.run(villa)
    assert not [r.subject for r in L.results if r.status == "fail"]       # worst zone 0.772 after L6b
    assert any(r.subject == "dining-table" and r.status == "pass" for r in L.results)


def test_quiet_when_every_driver_is_low(villa):
    from archpipe.concept import villa_lighting as VL
    low = {k: 0.5 for k in VL._drivers()}
    assert not [r for r in V12.run(villa, drivers=low).results if r.status == "fail"]


def test_raising_a_driver_is_caught(villa):
    from archpipe.concept import villa_lighting as VL
    d = dict(VL._drivers(), **{"Z-B-GUEST-WC-BASIN-TASK": 0.9})
    assert any(r.subject == "gwc-basin" and r.status == "fail" for r in V12.run(villa, drivers=d).results)


def test_every_card_is_reproduced_by_lvs_own_radiance_results(villa):
    from archpipe.lightverify.__main__ import ROOT
    out = V12.cards_met(villa, ROOT / "knowledge" / "lighting-verify" / "radiance")
    assert len(out) == 20 and all(r.status == "pass" for r in out), [r.message for r in out if r.status != "pass"]


def test_a_card_missed_by_the_radiance_results_is_caught(villa, tmp_path):
    import json, shutil
    from archpipe.lightverify.__main__ import ROOT
    src = ROOT / "knowledge" / "lighting-verify" / "radiance"
    for f in src.glob("*.json"):
        shutil.copy(f, tmp_path)
    d = json.loads((tmp_path / "B-guest-wc.json").read_text())
    for z in d["zones"].values():
        for ab in z:
            z[ab] = [x * 1.5 for x in z[ab]]
    (tmp_path / "B-guest-wc.json").write_text(json.dumps(d))
    bad = [r.subject for r in V12.cards_met(villa, tmp_path) if r.status == "fail"]
    assert bad == ["card/gwc-basin"]
