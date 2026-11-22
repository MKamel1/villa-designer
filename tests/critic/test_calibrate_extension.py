from archpipe.critic import calibrate as C


def test_wilson_known_values():
    lo, hi = C.wilson(8, 8)             # the held-out recall: 8 of 8 -> lower bound about 0.68
    assert round(lo, 2) == 0.68 and hi == 1.0
    lo, hi = C.wilson(1, 2)             # the held-out false-fail: 1 of 2 is nearly uninformative
    assert lo < 0.1 and hi > 0.9


def test_wilson_empty_group_is_vacuous_not_zero():
    assert C.wilson(0, 0) == (0.0, 1.0)


def test_wilson_stays_inside_unit_interval_and_tightens_with_n():
    for k, n in [(0, 5), (5, 5), (3, 10)]:
        lo, hi = C.wilson(k, n)
        assert 0 <= lo <= k / n <= hi <= 1
    assert C.wilson(30, 100)[1] - C.wilson(30, 100)[0] < C.wilson(3, 10)[1] - C.wilson(3, 10)[0]


def test_pooled_adds_groups():
    a = dict(recall_must_fail=(8, 8), false_fail_should_pass=(1, 2), recall_c_or_worse=(14, 16), middle_fail=(6, 8))
    b = dict(recall_must_fail=(2, 2), false_fail_should_pass=(0, 4), recall_c_or_worse=(3, 4), middle_fail=(1, 2))
    p = C.pooled(a, b)
    assert (p["false_fail_should_pass"]["k"], p["false_fail_should_pass"]["n"]) == (1, 6)
    assert (p["recall_must_fail"]["k"], p["recall_must_fail"]["n"]) == (10, 10)


def test_table_counts_recall_and_false_fail_with_intervals():
    from archpipe.critic import extension as X
    labels = {"a": dict(grade="D"), "b": dict(grade="F"), "c": dict(grade="B-"), "d": dict(grade="B-"), "e": dict(grade="C")}
    verdicts = dict(a="fail", b="pass", c="pass", d="fail", e="fail")      # b is a missed bad view, d a false fail
    t = X.table(labels, verdicts)
    assert t["new"]["recall_must_fail"] == (1, 2)
    assert t["new"]["false_fail_should_pass"] == (1, 2)
    p = t["pooled_with_all_38"]["false_fail_should_pass"]
    assert (p["k"], p["n"]) == (1 + 1 + 1, 2 + 2 + 3)          # new + held-out (1/2) + tuning (1/3)


def test_score_set_fails_closed_without_vlm(tmp_path):
    """Negative: with no VLM result a view must not pass, however clean its pixels are."""
    import json
    from PIL import Image
    from archpipe.critic import extension as X, verdict as V
    Image.new("RGB", (300, 200), (128, 128, 128)).save(tmp_path / "x.png")
    (tmp_path / "x.json").write_text(json.dumps(dict(camera=dict(lens_mm=24, position=[0, 0, 1.35], target=[1, 0, 1.35],
                                                                  sensor_mm=36), subjects=[])))
    v, rows, notes = X.score_set({"x": dict(grade="B-")}, tmp_path, None, V.load_rubric())
    assert v["x"] == "fail" and any("VLM" in r or "not evaluated" in r for r in notes["x"]["reasons"])


def test_load_vlm_dir_reads_n_prefixed_views(tmp_path):
    """Regression: glob was 'v*.json', so every new-set view (n01...) scored 'VLM unavailable'."""
    import json
    from archpipe.critic import calibrate as C
    for name in ("n01-x", "v02-y"):
        (tmp_path / f"{name}.json").write_text(json.dumps(dict(view=name, status="ok", scores={"R8": 2})))
    assert set(C.load_vlm_dir(tmp_path)) == {"n01-x", "v02-y"}
