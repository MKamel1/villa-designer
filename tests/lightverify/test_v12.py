import pytest
from archpipe.lightcalc.villa import Villa
from archpipe.lightverify import v12_headroom as V12


@pytest.fixture(scope="module")
def villa():
    return Villa()


def test_names_the_known_exceptions(villa):
    L = V12.run(villa)
    bad = {r.subject for r in L.results if r.status == "fail"}
    assert "fb-basin" in bad and "dirty-kitchen-run" in bad       # drivers 1.21 and 0.95 in zone-drivers.json
    assert "dining-table" not in bad


def test_quiet_when_every_driver_is_low(villa):
    from archpipe.concept import villa_lighting as VL
    low = {k: 0.5 for k in VL._drivers()}
    assert not [r for r in V12.run(villa, drivers=low).results if r.status == "fail"]


def test_raising_a_driver_is_caught(villa):
    from archpipe.concept import villa_lighting as VL
    d = dict(VL._drivers(), **{"Z-B-GUEST-WC-BASIN-TASK": 0.9})
    assert any(r.subject == "gwc-basin" and r.status == "fail" for r in V12.run(villa, drivers=d).results)
