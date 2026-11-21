"""V2 placement on the real design, plus seeded errors that must be caught (V8 depends on these)."""
import dataclasses

import pytest

from archpipe.lightcalc.villa import Villa
from archpipe.lightverify import v2_placement as V2


@pytest.fixture(scope="module")
def villa():
    return Villa()


def _mutate(villa, fid, **kw):
    fx = [dataclasses.replace(f, **kw) if f.id == fid else f for f in villa.fixtures]
    return Villa(fixtures=fx)


def test_design_has_no_placement_failure(villa):
    L = V2.check_placement(villa)
    assert not [r.subject + ": " + r.message for r in L.results if r.status == "fail"]


def test_shift_300mm_into_ceiling_is_caught(villa):
    f = next(f for f in villa.fixtures if f.id == "DL-lounge-01")
    L = V2.check_placement(_mutate(villa, f.id, z=f.z + 0.30))
    bad = [r for r in L.results if r.subject == f.id]
    assert bad[0].status == "fail" and "slab" in bad[0].message


def test_datum_swap_is_caught(villa):
    f = next(f for f in villa.fixtures if f.id == "DL-lounge-01")
    L = V2.check_placement(_mutate(villa, f.id, z=f.z + 1.2))       # Revit datum used instead of the scene datum
    assert [r for r in L.results if r.subject == f.id][0].status == "fail"


def test_fixture_outside_its_room_is_caught(villa):
    f = next(f for f in villa.fixtures if f.id == "DL-lounge-01")
    L = V2.check_placement(_mutate(villa, f.id, x=f.x + 20.0))
    assert "outside room" in [r for r in L.results if r.subject == f.id][0].message


def test_upward_aimed_downlight_is_caught(villa):
    f = next(f for f in villa.fixtures if f.id == "DL-lounge-01")
    L = V2.check_placement(_mutate(villa, f.id, aim=(0.0, 0.0, 1.0)))
    assert "off nadir" in [r for r in L.results if r.subject == f.id][0].message


def test_untouched_fixture_stays_quiet(villa):
    f = next(f for f in villa.fixtures if f.id == "DL-lounge-01")
    L = V2.check_placement(_mutate(villa, f.id, z=f.z - 0.05))      # 50 mm lower is still a legal recess
    assert [r for r in L.results if r.subject == f.id][0].status != "fail"
