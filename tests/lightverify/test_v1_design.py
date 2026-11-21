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
    monkeypatch.setitem(PRODUCTS, "DL", dict(PRODUCTS["DL"], watts=23.6))
    assert any(r.status == "fail" and " W " in r.message for r in V1.check_inputs(Villa()).results)


def test_wrong_spec_cct_is_caught(villa, monkeypatch):
    from archpipe.fixture_record import PRODUCTS
    monkeypatch.setitem(PRODUCTS, "DL", dict(PRODUCTS["DL"], cct=3000))
    assert any(r.status == "fail" and "CCT" in r.message for r in V1.check_inputs(Villa()).results)


def test_sampled_pendant_is_summed_by_parent(villa):
    """The Jilly pendant is 8 samples of ~58 lm; each alone != the record (462 lm), their sum equals it (L6c)."""
    parts = [p for p in villa.placements if (p.meta.get("parent") or "").startswith("PEN-LIN")]
    assert len(parts) == 8
    assert V1.instance_problems(villa) == {}


def test_wrong_parent_total_is_still_caught(villa):
    """Negative: a sampled fixture whose samples do not add up to its record is flagged."""
    import dataclasses
    from types import SimpleNamespace
    f = next(f for f in villa.fixtures if f.kind == "PEN-LIN")
    mine = [p for p in villa.placements if p.meta.get("parent") == f.id][:4]
    ps = [dataclasses.replace(p, dim=p.dim * 2) if p in mine else p for p in villa.placements]
    bad = V1.instance_problems(SimpleNamespace(fixtures=villa.fixtures, placements=ps))
    assert f.id in bad and not [k for k in bad if k != f.id]
