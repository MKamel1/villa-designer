"""LDG tests: positive and negative for the own checks, sampler invariants, outputs (A1 traceability, A2 zero fails)."""
import json
import random
from pathlib import Path

import pytest

from archpipe.landscape.concept import checks as K, layout as LY, site as S, south as SO, species
from archpipe.landscape.rules import evaluate, load

OUT = Path(__file__).resolve().parents[3] / "knowledge" / "landscape" / "concept"
RS = load()
POOL = species.pool()


def test_pool_only_viable_or_conditional():
    assert POOL and all(s.verdict in ("viable", "viable_with_conditions") for s in POOL.values())
    data = json.load(open(OUT.parent / "plants" / "plants.json"))["species"]
    allowed = {r["slug"] for r in data if r["site_viability"]["verdict"] in ("viable", "viable_with_conditions")}
    from archpipe.landscape.concept.species import CLIENT_ADMIT
    assert set(POOL) == allowed | set(CLIENT_ADMIT)              # the pool is what plants.json says (LDL) plus the named client admissions
    assert not set(CLIENT_ADMIT) & allowed                       # an admission is only ever for a species LDL holds out
    assert any(r["site_viability"]["verdict"] not in ("viable", "viable_with_conditions") for r in data if r["slug"] not in POOL)


def test_eyes_cover_and_screen_reduce_exposure():
    r = S.ZONES["south"]
    base = S.eyes_total(r)
    assert S.eyes_total(r, cover_rects=[r]) < base
    assert S.eyes_total(r, screen_top_z=-0.9) < base
    assert S.eyes_total(r, cover_rects=[r], screen_top_z=-0.9) < S.eyes_total(r, cover_rects=[r])


def test_eyes_negative_no_cover_no_change():          # stays quiet when nothing is built
    r = S.ZONES["south"]
    assert S.eyes_total(r, cover_rects=[[0, 0, 1, 1]]) == pytest.approx(S.eyes_total(r))


def _cand(idea="W", variant="open"):
    rng = random.Random(11)
    for _ in range(20000):
        c = SO.sample(idea, variant, rng, RS.params)
        if c:
            return c
    pytest.skip("no packing")


def test_sampler_respects_table_clearance():
    c = _cand()
    res = [r for r in evaluate(LY.to_layout(c, None, POOL), RS) if r.criterion == "LS-DINE-CLEAR"]
    assert res and all(r.status == "pass" for r in res)


def test_privacy_check_fails_without_cover():           # negative: an uncovered, unscreened room must fail
    c = _cand("W", "screened") if False else _cand("W", "open")
    c = dict(c, cover=[], screen_top_h=None, variant="screened")
    st = {r.subject: r.status for r in K.south_checks(c, None, POOL) if r.criterion == "LDG-PRIV"}
    assert "fail" in st.values()


def test_tree_spread_check_catches_olive():              # negative: olive canopy (4.6 m minimum spread) cannot fit
    c = _cand()
    c = dict(c, trees=[{"species": "olea_europaea", "center": (5.0, 1.0)}])
    r = [x for x in K.south_checks(c, None, POOL) if x.criterion == "LDG-SPREAD"]
    assert r and r[0].status == "fail"


def test_toxic_near_seat_fails():
    from shapely.geometry import box
    plan = {"beds": {"b": {"instances": [{"species": "zantedeschia_aethiopica", "layer": "aquatic", "positions": [(1, 1)], "count": 1}], "hydrozone": "high"}}, "trees": []}
    res = K.planting_checks("t", {}, plan, POOL, seats=[box(0.5, 0.5, 1.2, 1.2)])
    assert any(r.criterion == "LDG-TOXIC" and r.status == "fail" for r in res)
    res = K.planting_checks("t", {}, plan, POOL, seats=[box(9, 9, 10, 10)])
    assert all(r.status != "fail" for r in res if r.criterion == "LDG-TOXIC")


@pytest.mark.skipif(not (OUT / "summary.json").exists(), reason="run_all not run")
def test_outputs_zero_fails_and_traceable():
    summ = json.load(open(OUT / "summary.json"))
    for idea, pk in summ.items():
        for k, v in pk.items():
            assert v["tally"]["fail"] == 0, (idea, k)
            assert (OUT.parents[2] / v["plan"]).exists()
    tr = json.load(open(OUT / "traceability.json"))
    assert tr and all(not v["untraced"] for v in tr.values())          # A1: 100 %
