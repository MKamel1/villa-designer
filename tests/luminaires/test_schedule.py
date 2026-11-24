"""L6c: the supplier schedule is generated from the design and the bound products, and says what a substitute must meet."""
import json
from pathlib import Path

import pytest

from archpipe import fixture_record as FR
from archpipe.concept import villa_lighting as VL
from archpipe.luminaires import schedule as S

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def sched():
    return S.build_schedule()


def test_bound_kinds_are_the_v10_verified_erco_products():
    cand = json.loads((ROOT / "knowledge/lighting-products/candidates.json").read_text())
    by = {(p["maker"], p["code"]): p for v in cand["kinds"].values() for p in v}
    for kind, row in FR.bind_products().items():
        p = by[(row["manufacturer"], row["code"])]
        assert p["v10_status"] in ("pass", "partial"), kind
        assert row["lm"] == p["lumens"], kind                 # the spec is the product's own catalogue lumens
        assert Path(row["ies"]).exists()
        assert int(row["cct"]) == FR.KINDS[kind]["cct"] == 2700
    assert set(FR.bind_products()) == {"DL", "DLN", "ADJ", "WW", "PEN-LIN", "DESK", "PCOVE"}


def test_every_design_fixture_is_in_exactly_one_schedule_row(sched):
    assert sum(r["qty"] for r in sched) == len(VL.design())
    assert len({r["tag"] for r in sched}) == len(sched)


def test_product_rows_carry_the_reference_lumens(sched):
    dl = next(r for r in sched if r["tag"] == "DL")
    assert dl["rated_lm"] == [1065.0] and dl["spec"]["ref"][0]["code"] == "41321.000"


def test_every_row_has_the_performance_fields(sched):
    for r in sched:
        sp = r["spec"]
        for key in ("name", "role", "mount", "beam", "cct", "ugr", "ip", "ik", "dimming", "size", "finish"):
            assert sp[key] not in (None, ""), (r["tag"], key)
        assert sp["cct"] in (2700, 2200)


def test_generic_kinds_are_marked_without_a_reference_product(sched):
    sconce = next(r for r in sched if r["kind"] == "SCONCE")
    assert sconce["spec"]["ref"] == []


def test_unknown_tag_raises():
    with pytest.raises(KeyError):
        S.spec_for_tag("NOPE")


def test_split_tag_resolves_to_its_kind():
    assert S.spec_for_tag("PEN-GLOBE-B") is S.TYPE_SPEC["PEN-GLOBE"]
