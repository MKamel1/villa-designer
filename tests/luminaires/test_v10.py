import json
import re
from pathlib import Path

import pytest

from archpipe import fixture_record as fr
from archpipe.luminaires import v10

ROOT = Path(__file__).resolve().parents[2]
PROD = ROOT / "knowledge/lighting-products"
K3EW = PROD / "iguzzini/LSEVO-AAK3EW/LSEVO-AAK3EW.ies"
G451 = PROD / "iguzzini/451G/451G.ies"


def text(p):
    return p.read_text(encoding="latin-1")


def test_parser_reads_grid_and_absolute_flag():
    t = v10.read_ies(text(K3EW))
    assert len(t.gamma) == 181 and t.gamma[0] == 0 and t.gamma[-1] == 180
    assert t.lumens_stated < 0                      # -1 = absolute photometry
    assert t.cd[0][0] == pytest.approx(2291.0)


def test_parser_rejects_tilt_file():
    with pytest.raises(ValueError):
        v10.read_ies("IESNA:LM-63-2002\nTILT=INCLUDE\n1 1 1 1 1 1 2 0 0 0\n")


def test_lumens_match_product_name_two_ways():
    r = v10.check_lumens(text(K3EW), 730)           # '12W 730lm' in the manufacturer's own file
    assert r["status"] == "pass" and r["worst_error"] < 0.02
    assert abs(r["independent"] - r["archpipe"]) / r["independent"] < 0.01


def test_lumens_negative_wrong_datasheet_figure():
    assert v10.check_lumens(text(K3EW), 730 * 1.10)["status"] == "fail"


def test_lumens_negative_doubled_candela():
    t = text(K3EW)
    doubled = re.sub(r"^1 -1 1 181", "1 -1 2 181", t, count=1, flags=re.M)   # candela multiplier x2
    assert v10.check_lumens(doubled, 730)["status"] == "fail"


def test_published_points_reproduced_by_both_routes():
    for pt in (v10.Point("imax", 5759), v10.Point("beam_angle", 34), v10.Point("lumens", 1957.5)):
        r = v10.reproduce(pt, text(G451), v10.ph.parse(text(G451)))
        assert r["status"] == "pass", r
        assert r["engine"] != r["independent"] or pt.kind == "imax"   # two computations, not one copied


def test_cone_lux_on_axis_and_beam_diameter():
    t, p = text(G451), v10.ph.parse(text(G451))
    i0 = v10.read_ies(t).cd[0][0]
    lux = v10.reproduce(v10.Point("lux_axis", i0 / 2.0 ** 2, 2.0), t, p)
    assert lux["status"] == "pass"
    diam = 2 * 2.0 * 0.3057                        # tan(17 deg) = 0.3057, 34 deg beam at 2 m
    assert v10.reproduce(v10.Point("beam_diameter", diam, 2.0), t, p)["status"] == "pass"


def test_cone_negative_published_value_off_by_ten_percent():
    t, p = text(G451), v10.ph.parse(text(G451))
    i0 = v10.read_ies(t).cd[0][0]
    assert v10.reproduce(v10.Point("lux_axis", 1.10 * i0 / 4.0, 2.0), t, p)["status"] == "fail"
    assert v10.reproduce(v10.Point("imax", 6500), t, p)["status"] == "fail"


def test_no_published_point_is_not_a_pass():
    r = v10.check_product(K3EW, stated_lumens=730, points=[])
    assert r["status"] == "not_evaluated"


def test_candidates_json_is_honest():
    d = json.loads((PROD / "candidates.json").read_text())
    assert set(d["kinds"]) == set(fr.KINDS)         # every design kind has an entry, empty if no product
    for cands in d["kinds"].values():
        for c in cands:
            if c["v10_status"] == "pass":
                assert any(p["kind"] != "lumens" and p["status"] == "pass" for p in c["v10"]["points"])
            assert c["files"]["ldt"]["sha256"] and c["files"]["ies"]["sha256"]
