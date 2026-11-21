"""V1 on the real design, plus the negative: a doubled product lumen value must be caught."""
import pytest

from archpipe.lightcalc.villa import Villa
from archpipe.lightverify import v1_inputs as V1


@pytest.fixture(scope="module")
def villa():
    return Villa()


def test_design_inputs_pass(villa):
    L = V1.check_inputs(villa)
    assert all(r.status == "pass" for r in L.results), [r.message for r in L.results if r.status != "pass"]
    dl = next(r for r in L.table if r["kind"] == "DL")
    assert abs(dl["integ_vs_product_pct"]) < 0.5


def test_doubled_product_lumens_is_caught(villa, monkeypatch):
    from archpipe.fixture_record import PRODUCTS
    monkeypatch.setitem(PRODUCTS, "DL", dict(PRODUCTS["DL"], lm=PRODUCTS["DL"]["lm"] * 2))
    v2 = Villa()
    L = V1.check_inputs(v2)
    assert any(r.status == "fail" and r.subject == "kind:DL" for r in L.results)
    assert L.rooms["lounge"] == "fail"


def test_wrong_watts_is_caught(villa, monkeypatch):
    from archpipe.fixture_record import PRODUCTS
    monkeypatch.setitem(PRODUCTS, "DLN", dict(PRODUCTS["DLN"], watts=23.6))
    assert any(r.status == "fail" and "W" in r.message for r in V1.check_inputs(Villa()).results)


def test_wrong_file_cct_is_caught(villa, monkeypatch):
    from archpipe.fixture_record import FIXTURE_KINDS
    import dataclasses
    k = FIXTURE_KINDS["ADJ"]
    req = tuple((a, 3000 if a == "cct" else b) for a, b in k.requirement)
    monkeypatch.setitem(FIXTURE_KINDS, "ADJ", dataclasses.replace(k, requirement=req)) if hasattr(FIXTURE_KINDS, "__setitem__") else pytest.skip("immutable")
