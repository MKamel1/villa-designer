import copy, json
from archpipe.landscape import precedents as P

def g(i, a, b, plan=True):
    return {"id": i, "name": i, "page_url": "https://x/" + i, "scaled_plan": plan,
            "passes": {"A": dict(a), "B": dict(b)}}

def test_valid_garden_ok():
    assert P.validate_garden(g("s1", {"area_m2": 50}, {"area_m2": 52})) == []

def test_plan_metric_on_photo_only_garden_rejected():
    assert any("no scaled plan" in x for x in P.validate_garden(g("s1", {"area_m2": 50}, {}, plan=False)))

def test_qualitative_allowed_on_photo_only():
    assert P.validate_garden(g("s1", {"privacy_approach": "hedge"}, {"privacy_approach": "wall"}, plan=False)) == []

def test_unknown_metric_and_bad_value_rejected():
    assert any("unknown" in x for x in P.validate_garden(g("s1", {"beauty": 1}, {})))
    assert any("non-negative" in x for x in P.validate_garden(g("s1", {"area_m2": -4}, {})))

def test_share_sum_must_be_one():
    bad = {"hard_share": .5, "soft_share": .2, "water_share": 0}
    assert any("sums to" in x for x in P.validate_garden(g("s1", bad, {})))
    ok = {"hard_share": .5, "soft_share": .45, "water_share": .05}
    assert P.validate_garden(g("s1", ok, {})) == []

def test_missing_pass_rejected_and_duplicate_ids():
    x = g("s1", {}, {}); del x["passes"]["B"]
    assert P.validate_garden(x)
    assert P.validate_set([g("a", {}, {}), g("a", {}, {})])

def test_spread_and_drop_when_too_large():
    ok = [g(f"o{i}", {"area_m2": 50 + i}, {"area_m2": 52 + i}) for i in range(8)]
    assert P.derive(ok)["area_m2"]["status"] == "range"
    wild = [g(f"w{i}", {"area_m2": 50 + i}, {"area_m2": 120 + i}) for i in range(8)]
    r = P.derive(wild)["area_m2"]
    assert r["status"] == "GAP" and "spread" in r["reason"]   # negative: too-large spread is dropped, not used

def test_too_few_gardens_is_gap():
    assert P.derive([g("a", {"area_m2": 5}, {"area_m2": 5})])["area_m2"]["status"] == "GAP"

def test_range_is_iqr_of_means():
    gs = [g(f"o{i}", {"area_m2": v}, {"area_m2": v}) for i, v in enumerate([10, 20, 30, 40, 50, 60, 70])]
    r = P.derive(gs)["area_m2"]
    assert (r["q1"], r["median"], r["q3"]) == (25, 40, 55)

def test_garden_with_large_disagreement_excluded():
    assert P.garden_value(g("a", {"area_m2": 10}, {"area_m2": 30}), "area_m2") is None

def test_position():
    rec = {"status": "range", "q1": 10, "q3": 20}
    assert [P.position(v, rec) for v in (5, 15, 25)] == ["below", "inside", "above"]
    assert P.position(5, {"status": "GAP"}) == "no range"

def test_freeze_detects_edit(tmp_path):
    t = {"date": "2026-11-22", "ranges": {"a": 1}}
    t["content_sha256"] = P.content_sha(t)
    f = tmp_path / "t.json"; f.write_text(json.dumps(t))
    assert P.check_frozen(f) == []
    t["ranges"]["a"] = 2; f.write_text(json.dumps(t))      # tuned after freezing
    assert P.check_frozen(f)

def test_freeze_file_hash_mismatch(tmp_path):
    t = {"d": 1}; t["content_sha256"] = P.content_sha(t)
    f = tmp_path / "t.json"; f.write_text(json.dumps(t))
    assert P.check_frozen(f, "0" * 64)

def test_committed_data_valid():
    for s in P.SETS:
        try:
            gs = P.load(s)
        except FileNotFoundError:
            continue
        assert P.validate_set(gs) == []
