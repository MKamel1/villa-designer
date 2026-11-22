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

def test_size_band_excludes_big_gardens():
    small = [g(f"s{i}", {"area_m2": 50, "n_rooms": 2}, {"area_m2": 52, "n_rooms": 2}) for i in range(6)]
    huge = [g(f"h{i}", {"area_m2": 500, "n_rooms": 9}, {"area_m2": 520, "n_rooms": 9}) for i in range(6)]
    r = P.derive(small + huge, (30, 150))["n_rooms"]
    assert r["status"] == "range" and r["max"] == 2           # the 500 m2 gardens do not widen the range
    assert P.derive(huge, (30, 150))["n_rooms"]["status"] == "GAP"

def test_freeze_refuses_to_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "DATA", tmp_path)
    (tmp_path / "targets.json").write_text("{}")
    import pytest
    with pytest.raises(FileExistsError):
        P.freeze("2026-11-22")             # negative: the generator cannot re-freeze tuned values

def test_density_metrics_use_wide_band_and_say_not_size_matched(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "DATA", tmp_path)
    import json as j
    for s in P.SETS:
        gs = [g(f"{s}{i}", {"area_m2": 200, "hard_share": .5, "soft_share": .5, "water_share": 0},
                {"area_m2": 200, "hard_share": .5, "soft_share": .5, "water_share": 0}) for i in range(7)]
        (tmp_path / f"{s}.json").write_text(j.dumps({"gardens": gs}))
    t = P.build_targets("2026-11-22")["sets"]["south"]
    assert t["hard_share"]["status"] == "range" and t["hard_share"]["size_matched"] is False
    assert t["area_m2"]["status"] == "GAP"     # 200 m2 is outside the strict south band

def test_frozen_targets_match_hash_in_lane_doc():
    import re
    from pathlib import Path
    doc = (Path(__file__).resolve().parents[3] / "docs/lanes/LDP.md").read_text()
    sha = re.search(r"sha256 = ([0-9a-f]{64})", doc).group(1)
    assert P.check_frozen(expected_file_sha256=sha) == []
