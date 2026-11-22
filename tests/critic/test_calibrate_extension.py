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
