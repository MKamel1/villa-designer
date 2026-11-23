"""V10 for the bound products (read from the binding, L6d: ERCO A9003138 + iGuzzini RP65, alternate RP25): data-sheet numbers parsed by this lane, against the files the engine loads."""
import pytest

from archpipe.lightverify import v10_erco as V


@pytest.fixture(scope="module")
def layer():
    return V.run()


def _rows(layer, kind):
    return next(t for t in layer.table if t["kind"] == kind)["rows"]


def test_datasheet_parser_reads_every_row_of_the_cone_table():
    ds = V.datasheet(V.pdf_text("A9003138"))
    assert [c[0] for c in ds["cone"]] == [1.0, 2.0, 3.0, 4.0, 5.0]      # the 1 m row sits beside other text on its line
    assert ds["cone"][0] == (1.0, 3014.0, 0.50) and ds["lumens"] == 760 and ds["imax"] == [3014.0] and ds["beam_angle"] == 28.0


def test_iguzzini_page_is_read_by_label_not_by_the_description_text():
    ds = V.datasheet_of("iguzzini", "RP65")
    assert (ds["lumens"], ds["watts"], ds["imax"], ds["lor"], ds["above90"], ds["cri"]) == (1079.0, 9.7, [998.0], 83.0, 26.0, 90.0)
    assert V.datasheet_of("iguzzini", "QA11")["cri"] is not None      # the older QA layout (label and value on separate lines) still parses


def test_tables_follow_the_binding_not_ids_in_the_code(layer):
    from archpipe.fixture_record import bind_products
    got = {t["kind"]: t["code"] for t in layer.table if t["kind"] != "ALT"}
    assert got == {k: p["code"] for k, p in bind_products().items()}
    assert {"A9003138", "RP65"} <= set(got.values()) and "QA03" not in got.values()      # the retired pendant is gone


def test_every_bound_product_and_alternate_passes_every_point(layer):
    for t in layer.table:
        assert all(s == "pass" for _, s, _ in t["rows"]), (t["kind"], t["code"], [r for r in t["rows"] if r[1] != "pass"])
    assert {t["code"] for t in layer.table if t["kind"] == "ALT"} == {"68887", "68119", "QA11", "RP25"}


def test_a_product_change_in_the_binding_is_verified_without_touching_the_code(monkeypatch):
    """Rebind ADJ to the Starpoint's files: V10 verifies that product (and its bound file) from the binding alone."""
    from archpipe.fixture_record import PRODUCTS
    f = V.ERCO / "68887" / "erco-68887-000-en-ies.ies"
    monkeypatch.setitem(PRODUCTS, "ADJ", dict(PRODUCTS["ADJ"], code="68887", ies=str(f)))
    rows = _rows(V.run(), "ADJ")
    assert next(s for n, s, m in rows if n == "lumens") == "pass" and "551" in next(m for n, s, m in rows if n == "lumens")


def test_a_wrong_iguzzini_lumen_figure_is_caught(monkeypatch):
    real = V.datasheet_of
    monkeypatch.setattr(V, "datasheet_of", lambda mk, c: dict(real(mk, c), lumens=1200.0) if c == "RP65" else real(mk, c))
    rows = _rows(V.run(), "PEN-LIN")
    assert next(s for n, s, _ in rows if n == "lumens") == "fail"


def test_a_wrong_datasheet_lumen_figure_is_caught(monkeypatch):
    real = V.pdf_text
    monkeypatch.setattr(V, "pdf_text", lambda c: real(c).replace("1065lm", "1500lm") if c == "41321" else real(c))
    rows = _rows(V.run(), "DL")
    assert next(s for n, s, _ in rows if n == "lumens") == "fail"


def test_a_wrong_peak_intensity_is_caught(monkeypatch):
    real = V.pdf_text
    monkeypatch.setattr(V, "pdf_text", lambda c: real(c).replace("Imax=1147cd", "Imax=1500cd") if c == "41321" else real(c))
    rows = _rows(V.run(), "DL")
    assert next(s for n, s, _ in rows if n == "imax") == "fail"


def test_the_bound_file_must_be_the_download(monkeypatch, tmp_path):
    from archpipe.fixture_record import PRODUCTS
    other = tmp_path / "x.ies"
    other.write_bytes((V.ERCO / "41321" / "erco-41321-000-en-ies.ies").read_bytes() + b"\n")
    monkeypatch.setitem(PRODUCTS, "DL", dict(PRODUCTS["DL"], ies=str(other)))
    rows = _rows(V.run(), "DL")
    assert next(s for n, s, _ in rows if n == "bound-file") == "fail"


def test_cri_overstated_in_the_record_fails_and_understated_is_flagged(monkeypatch):
    real = V._bound_row
    monkeypatch.setattr(V, "_bound_row", lambda mk, c: dict(real(mk, c), cri=95.0) if c in ("A9003138", "RP65") else real(mk, c))
    rows = V.run().table
    for code in ("A9003138", "RP65"):
        assert next(s for n, s, _ in next(t for t in rows if t["code"] == code)["rows"] if n == "cri") == "fail"
    monkeypatch.setattr(V, "_bound_row", lambda mk, c: dict(real(mk, c), cri=85.0) if c == "RP65" else real(mk, c))
    rp = next(t for t in V.run().table if t["code"] == "RP65")["rows"]
    assert "understates" in next(m for n, _, m in rp if n == "cri")      # record below the page's CRI 90: flagged, not failed
    assert next(s for n, s, _ in rp if n == "cri") == "pass"
