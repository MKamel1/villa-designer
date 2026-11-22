"""V10 for the ERCO products bound by L6c: data-sheet numbers parsed from the PDFs, against the files the engine loads."""
import pytest

from archpipe.lightverify import v10_erco as V


@pytest.fixture(scope="module")
def layer():
    return V.run()


def _rows(layer, kind):
    return next(t for t in layer.table if t["kind"] == kind)["rows"]


def test_datasheet_parser_reads_every_row_of_the_cone_table():
    ds = V.datasheet(V.pdf_text("A9000028"))
    assert [c[0] for c in ds["cone"]] == [1.0, 2.0, 3.0, 4.0, 5.0]      # the 1 m row sits beside other text on its line
    assert ds["cone"][0] == (1.0, 22846.0, 0.08) and ds["lumens"] == 304 and ds["imax"] == [22846.0]


def test_every_bound_product_but_the_adjustable_spot_passes_every_point(layer):
    for kind in ("DL", "DLN", "WW", "PEN-LIN", "DESK"):
        assert all(s == "pass" for _, s, _ in _rows(layer, kind)), (kind, [r for r in _rows(layer, kind) if r[1] != "pass"])


def test_adjustable_spot_is_partial_not_hidden(layer):
    rows = _rows(layer, "ADJ")
    bad = {n for n, s, _ in rows if s == "fail"}
    assert "beam-angle" in bad and {"beam-dia-1m", "beam-dia-5m"} <= bad       # the unreproduced published beam
    good = {n for n, s, _ in rows if s == "pass"}
    assert {"lumens", "imax", "lux-1m", "lux-5m", "bound-file"} <= good


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
    other = tmp_path / "x.ies"
    other.write_bytes((V.ERCO / "41321" / "erco-41321-000-en-ies.ies").read_bytes() + b"\n")
    real = V._bound_path
    monkeypatch.setattr(V, "_bound_path", lambda kind: other if kind == "DL" else real(kind))
    rows = _rows(V.run(), "DL")
    assert next(s for n, s, _ in rows if n == "bound-file") == "fail"
