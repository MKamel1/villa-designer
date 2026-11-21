"""L6c substitution loop: each verdict has a positive and a negative case, on the frozen Radiance results of the design.

ACCEPT: the reference product itself (the loop must stay quiet on what it was designed with).
REJECT: a real product of another maker (iGuzzini Laser Evo: 33 deg beam vs a 57 deg wide flood, phase-cut only).
ACCEPT WITH DIMMING CHANGE / REJECT for output: ERCO's own file with its candela scaled (SYNTHETIC: a stand-in for a weaker/stronger
product of the same distribution; the lumens figure in the datasheet is scaled to match, so V1 passes honestly).
"""
import json
import re
from pathlib import Path

import pytest

from archpipe.luminaires import substitute as SUB

ROOT = Path(__file__).resolve().parents[2]
ERCO = ROOT / "knowledge/lighting-products/erco/41321/erco-41321-000-en-ies.ies"
ERCO_DS = ROOT / "docs/lighting-spec/examples/erco-41321.points.json"
IGU = ROOT / "knowledge/lighting-products/iguzzini/LSEVO-AAK3EW/LSEVO-AAK3EW.ies"
IGU_DS = ROOT / "docs/lighting-spec/examples/iguzzini-LSEVO-AAK3EW.points.json"


def scaled(tmp_path, k, name="scaled"):
    """ERCO 41321 with every candela x k (candela multiplier of the first data line), and a datasheet saying so."""
    text = ERCO.read_bytes().decode("latin-1").lstrip("﻿")
    text = re.sub(r"^(TILT=NONE\s*\n\s*\S+\s+\S+\s+)(\S+)", lambda m: m.group(1) + "%.4f" % (float(m.group(2)) * k), text, count=1, flags=re.M)
    f = tmp_path / (name + ".ies")
    f.write_text(text, encoding="utf-8")
    ds = json.loads(ERCO_DS.read_text())
    ds["claims"]["lumens"] = round(1065 * k, 1)
    ds["points"] = [dict(kind="imax", published=round(1147 * k, 1), source="scaled test datasheet")]
    d = tmp_path / (name + ".points.json")
    d.write_text(json.dumps(ds))
    return f, d


def run(tag, ies, ds, tmp_path):
    return SUB.run(tag, ies, ds, out=tmp_path / "out")


def test_accept_the_reference_product(tmp_path):
    rep = run("DL", ERCO, ERCO_DS, tmp_path)
    assert rep["verdict"] == SUB.ACCEPT
    assert all(r["status"] != "fail" for r in rep["checks"])
    assert [r for r in rep["checks"] if r["id"] == "V10" and r["status"] == "pass"]          # its published points reproduce


def test_reject_a_real_product_of_another_maker(tmp_path):
    rep = run("DL", IGU, IGU_DS, tmp_path)
    assert rep["verdict"] == SUB.REJECT
    text = " ".join(rep["reasons"])
    assert "SPEC:beam" in text and "SPEC:dimming" in text and "phase-cut" in text
    assert any(r["id"] == "V10" and r["status"] == "not_evaluated" for r in rep["checks"])       # no published point to reproduce


def test_stronger_product_of_the_same_distribution_is_accepted_with_a_dimming_change(tmp_path):
    f, d = scaled(tmp_path, 1.10)
    rep = run("DL", f, d, tmp_path)
    assert rep["verdict"] == SUB.CHANGE, rep["reasons"]
    changed = {z: v for z, v in rep["drivers"].items() if v["old"] is not None and abs(v["new"] - v["old"]) > 0.02}
    assert changed and all(v["new"] <= 0.80 + 1e-9 for v in rep["drivers"].values())
    assert all(v["new"] < v["old"] for v in changed.values())                # a stronger product is driven lower


def test_a_weaker_product_is_rejected_when_zones_would_pass_80_percent(tmp_path):
    f, d = scaled(tmp_path, 0.85)                  # the design's zones already sit at 0.65-0.76 of the reference output
    rep = run("DL", f, d, tmp_path)
    assert rep["verdict"] == SUB.REJECT
    assert any("V12" in r for r in rep["reasons"])


def test_a_much_stronger_product_is_rejected_when_the_untuned_ambient_overshoots_a_card(tmp_path):
    f, d = scaled(tmp_path, 1.3)
    rep = run("DL", f, d, tmp_path)
    assert rep["verdict"] == SUB.REJECT
    assert any("even with its zones re-driven" in r for r in rep["reasons"])


def test_a_much_weaker_product_is_rejected(tmp_path):
    f, d = scaled(tmp_path, 0.5)
    rep = run("DL", f, d, tmp_path)
    assert rep["verdict"] == SUB.REJECT


def test_lumens_that_disagree_with_the_file_fail_v1(tmp_path):
    f, d = scaled(tmp_path, 1.0)
    ds = json.loads(d.read_text())
    ds["claims"]["lumens"] = 2000                    # the datasheet claims twice what the file integrates to
    d.write_text(json.dumps(ds))
    rep = run("DL", f, d, tmp_path)
    assert rep["verdict"] == SUB.REJECT
    assert any(r["id"] == "V1" and r["status"] == "fail" for r in rep["checks"])


def test_missing_mandatory_figures_reject_as_incomplete(tmp_path):
    f, d = scaled(tmp_path, 1.0)
    ds = json.loads(d.read_text())
    for k in ("cct_k", "cri", "dimming"):
        ds["claims"].pop(k)
    d.write_text(json.dumps(ds))
    rep = run("DL", f, d, tmp_path)
    assert rep["verdict"] == SUB.REJECT
    assert {"SPEC:cct", "SPEC:cri", "SPEC:dimming"} <= {r["id"] for r in rep["checks"] if r["status"] == "missing"}


def test_ldt_input_is_accepted(tmp_path):
    ldt = ROOT / "knowledge/lighting-products/erco/41321/erco-41321-000-en-ldt.ldt"
    rep = run("DL", ldt, ERCO_DS, tmp_path)
    assert rep["verdict"] == SUB.ACCEPT


def test_unknown_tag_raises(tmp_path):
    with pytest.raises(KeyError):
        run("NOPE", ERCO, ERCO_DS, tmp_path)
