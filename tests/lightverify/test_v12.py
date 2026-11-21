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
