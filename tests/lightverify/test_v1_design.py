"""V1 on the real design, plus the negative: a doubled product lumen value must be caught."""
from pathlib import Path

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
    monkeypatch.setitem(PRODUCTS, "DL", dict(PRODUCTS["DL"], watts=23.6))
    assert any(r.status == "fail" and " W " in r.message for r in V1.check_inputs(Villa()).results)


def test_wrong_spec_cct_is_caught(villa, monkeypatch):
    from archpipe.fixture_record import PRODUCTS
    monkeypatch.setitem(PRODUCTS, "DL", dict(PRODUCTS["DL"], cct=3000))
    assert any(r.status == "fail" and "CCT" in r.message for r in V1.check_inputs(Villa()).results)


def test_bound_pendant_is_one_emitter_at_its_record_flux(villa):
    """L6d: the dining pendant is the iGuzzini Libera RP65 (QA03 retired), read from the binding; instance_problems compares engine flux with the record."""
    f = next(f for f in villa.fixtures if f.kind == "PEN-LIN")
    mine = [p for p in villa.placements if (p.meta.get("parent") or p.id) == f.id]
    from archpipe.fixture_record import bind_products
    assert mine and all(Path(p.meta["ies_path"]).name == Path(bind_products()["PEN-LIN"]["ies"]).name == "IGUZZINI-RP65.ies" for p in mine)
    assert V1.instance_problems(villa) == {}


def test_wrong_pendant_flux_is_still_caught(villa):
    """Negative: a bound emitter whose dimming no longer matches its record is flagged."""
    import dataclasses
    from types import SimpleNamespace
    f = next(f for f in villa.fixtures if f.kind == "PEN-LIN")
    ps = [dataclasses.replace(p, dim=p.dim * 2) if (p.meta.get("parent") or p.id) == f.id else p for p in villa.placements]
    bad = V1.instance_problems(SimpleNamespace(fixtures=villa.fixtures, placements=ps))
    assert f.id in bad and not [k for k in bad if k != f.id]
