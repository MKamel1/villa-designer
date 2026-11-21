import json
from pathlib import Path

import pytest

from archpipe.lightcalc import dining, emit

ROOT = Path(__file__).resolve().parents[2]
RES = json.loads((ROOT / "knowledge/lighting/L6-dining-result.json").read_text(encoding="utf-8"))
INP = json.loads((ROOT / "knowledge/lighting/d1-dining-input.json").read_text(encoding="utf-8"))


def _checks(variant, scene_prefix, crit):
    return [c for c in RES["checks"] if c["subject"].startswith(f"D1-dining{variant}/table-top/{scene_prefix}")
            and c["criterion"] == crit]


def test_input_is_the_l2_model_dining_zone():
    assert len(INP["room_polygon_m"]) == 6                       # L-shaped, non-rectangular
    kinds = sorted(l["kind"] for l in INP["luminaires"])
    assert kinds == ["ADJ", "ADJ", "ADJ", "ADJ", "PEN-LIN"]
    assert INP["table"]["top_z"] == pytest.approx(-2.25)
    assert INP["target"]["lux"] == 100.0


def test_la2_fails_in_the_design_scene_with_numbers():
    full_model = _checks("", "full", "LA2")[0]
    full_built = _checks("-built", "full", "LA2")[0]
    assert full_model["status"] == "fail" and full_built["status"] == "fail"
    assert full_model["required"] == 150.0 and full_model["achieved"] > 600      # ~7x target
    assert 150.0 < full_built["achieved"] < 600                                   # ~3.9x target
    assert "x target" in full_model["message"]


def test_dimmed_scene_passes_la1_and_la2():
    for variant in ("", "-built"):
        assert _checks(variant, "dinner-dimmed", "LA1")[0]["status"] == "pass"
        assert _checks(variant, "dinner-dimmed", "LA2")[0]["status"] == "pass"


def test_radiance_total_light_is_internally_consistent():
    for v in RES["variants"].values():
        x = v["direct_cross_check_spots"]["table-top"]                 # Radiance ab0 vs analytic, real IES files
        assert x["max_abs_rel_err"] < 0.01
        for sc in v["scenes"].values():
            for pl in sc["planes"].values():
                assert pl["total"]["em"] > pl["direct_only"]["em"]       # inter-reflection adds light
                assert abs(pl["convergence_ab_vs_2ab"]) < 0.03           # ab 6 vs 12


def test_emit_builds_valid_contract_records():
    res = emit.reference_results() + emit.dining_results()
    assert res and all(r.lane == "L6" for r in res)
    assert any(r.criterion == "LA4" and r.status == "not_evaluated" for r in res)       # open item is explicit
    assert all(r.status != "pass" or r.source_ids for r in res)
