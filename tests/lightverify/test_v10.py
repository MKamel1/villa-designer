import pytest
from archpipe.lightverify import ies, ldt, v10_manufacturer as V10


def test_manufacturer_data_reproduced():
    L = V10.run()
    assert not [r.message for r in L.results if r.status == "fail"]
    assert sum(r.status == "pass" for r in L.results) >= 15


def test_ldt_and_ies_agree_on_one_product():
    b = V10.LIB / "LSEVO-AAIIA6"
    di = ies.parse((b / "mfr_LSEVO-AAIIA6.ies").read_text(errors="replace"))
    dl = ldt.parse((b / "LSEVO-AAIIA6.ldt").read_text(errors="replace"))
    assert ies.lumens(dl) == pytest.approx(ies.lumens(di), rel=0.01)


def test_doubled_candela_is_caught(monkeypatch):
    real = ies.parse
    def doubled(t):
        d = real(t)
        d.cd = [[v * 2 for v in r] for r in d.cd]
        return d
    monkeypatch.setattr(V10.ies, "parse", doubled)
    L = V10.run()
    assert any(r.status == "fail" and "ies-vs-ldt" in r.subject for r in L.results)
