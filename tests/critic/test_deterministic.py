"""Deterministic critic checks on synthetic images and camera dicts. No VLM, no network."""
import numpy as np
import pytest

from archpipe.critic import calibrate, labels, meta, pixels, verdict, vlm


def img(h=240, w=360, value=0.5):
    return np.full((h, w, 3), value, float)


# ---- R1 / R2 / R3 metadata -------------------------------------------------
def test_r1_24mm_passes():
    assert meta.check_r1({"lens_mm": 24})[0] == 2


def test_r1_wide_with_reason_warns_and_without_fails():
    cam = {"lens_mm": 16, "overrides": [{"field": "lens_mm", "reason": "room needs it"}]}
    assert meta.check_r1(cam)[0] == 1
    assert meta.check_r1({"lens_mm": 16})[0] == 0


def test_r1_missing_is_not_evaluated():
    assert meta.check_r1(None)[0] is None


def test_r2_height_uses_floor_datum():
    assert meta.camera_height_m({"position": [0, 0, -1.65]}) == pytest.approx(1.35)
    assert meta.camera_height_m({"position": [0, 0, 1.35]}) == pytest.approx(1.35)
    assert meta.check_r2({"position": [0, 0, 1.35]})[0] == 2
    assert meta.check_r2({"position": [0, 0, 2.6]})[0] == 0      # 2.6 m above floor 0


def test_r3_meta_pitch():
    level = {"position": [0, 0, 1.35], "target": [3, 0, 1.35]}
    tilted = {"position": [0, 0, 1.35], "target": [3, 0, 1.6]}   # about 4.8 deg
    assert meta.check_r3_meta(level, 0.0)[0] == 2
    assert meta.check_r3_meta(tilted, 0.0)[0] == 0


# ---- R4 subject exposure ---------------------------------------------------
def test_r4_clean_midtone_passes():
    assert pixels.check_r4(img(), [])["score"] == 2


def test_r4_crushed_subject_fails_but_dark_corner_outside_mask_is_ignored():
    a = img()
    a[:, :] = 0.5
    a[:, :60] = 0.0                                   # dark strip, outside the 60 % central fallback
    assert pixels.check_r4(a, [])["score"] == 2
    a[:] = 0.0
    assert pixels.check_r4(a, [])["score"] == 0


def test_r4_clipped_window_inside_subject_box_warns_or_fails():
    a = img()
    box = {"screen": [0.2, 0.2, 0.8, 0.8]}            # y up, central
    a[60:180, 100:260] = 1.0                           # ~39 % of the frame, almost the whole box
    r = pixels.check_r4(a, [box])
    assert r["score"] == 0 and r["clipped"] > 0.03


def test_subject_box_off_frame_is_clipped_and_flipped():
    m, basis = pixels.subject_mask((100, 100), [{"screen": [0.0, -2.0, 0.5, 0.5]}])   # y up: lower half, left
    assert basis == "subject boxes"
    assert m[99, 10] and not m[10, 10] and not m[99, 90]


def test_subject_mask_falls_back_to_centre():
    m, basis = pixels.subject_mask((100, 100), [])
    assert "fallback" in basis and m[50, 50] and not m[2, 2]


# ---- R10 bands -------------------------------------------------------------
def test_edge_band_detected_on_black_left_edge():
    a = img(value=0.5)
    a[:, :12] = 0.0
    r = pixels.check_r10_pixel(a)
    assert r["score"] == 0 and "left" in r["bands"]


def test_no_band_on_plain_frame():
    assert pixels.check_r10_pixel(img())["score"] == 2


def test_dark_frame_is_not_called_a_band():
    assert pixels.check_edge_bands(img(value=0.01))["found"] == {}


# ---- R12 cast --------------------------------------------------------------
def test_r12_neutral_passes_cool_blue_fails():
    assert pixels.check_r12(img())["score"] == 2
    blue = img()
    blue[..., 2] += 0.12
    blue[..., 0] -= 0.05
    assert pixels.check_r12(blue)["score"] == 0


def test_r12_warm_room_within_limit_passes():
    a = img()
    a[..., 0] += 0.07
    a[..., 2] -= 0.07
    assert pixels.check_r12(a)["score"] == 2


# ---- R3 pixels ---------------------------------------------------------------
def _stripes(shear=0.0, h=240, w=360):
    y, x = np.mgrid[0:h, 0:w]
    v = 0.5 + 0.4 * np.sin(2 * np.pi * (x + shear * (y - h / 2)) / 16)      # smooth, like an antialiased edge
    return np.stack([v] * 3, axis=-1)


def test_r3_vertical_stripes_pass_and_leaning_stripes_fail():
    assert pixels.check_r3_pixels(_stripes(0.0), min_support=500)["score"] == 2
    lean = pixels.check_r3_pixels(_stripes(0.05), min_support=500)    # 2.9 deg shear
    assert lean["score"] in (0, 1) and lean["achieved"] > 1.5


# ---- verdict rules -----------------------------------------------------------
def _m(**kw):
    base = {c: {"score": 2, "message": ""} for c in ["R1", "R2", "R3", "R4", "R5", "R7", "R8", "R9", "R10", "R11", "R12", "R13"]}
    for k, v in kw.items():
        base[k] = {"score": v, "message": ""}
    return base


def test_verdict_all_pass():
    assert verdict.decide(_m())[0] == "pass"


def test_verdict_one_zero_fails_hero_but_not_non_hero():
    assert verdict.decide(_m(R4=0))[0] == "fail"
    assert verdict.decide(_m(R4=0), hero=False)[0] == "pass"


def test_verdict_one_warn_passes_two_warns_fail():
    assert verdict.decide(_m(R1=1))[0] == "pass"
    v, notes = verdict.decide(_m(R1=1, R4=1))
    assert v == "fail" and "escalate" in notes["reasons"][0]


def test_verdict_non_gating_criterion_does_not_count():
    gating = {"R1", "R2", "R3", "R4", "R10", "R12"}
    assert verdict.decide(_m(R8=0, R5=1, R7=1), gating)[0] == "pass"


def test_verdict_fails_closed_without_vlm():
    assert verdict.decide(_m(), vlm_ok=False)[0] == "fail"


def test_merge_marks_missing_vlm_and_r6_not_evaluated():
    det = {c: {"score": 2, "message": ""} for c in ["R1", "R2", "R3", "R4", "R10", "R12"]}
    merged = verdict.merge(det, None, {})
    assert merged["R5"]["score"] is None and merged["R6"]["score"] is None
    res = verdict.check_results("v", merged, set())
    assert {r.criterion: r.status for r in res}["R6"] == "not_evaluated"
    assert all(r.status != "pass" or r.source_ids for r in res)


def test_r10_takes_min_of_pixel_and_vlm():
    det = {"R10": {"score": 2, "message": "p"}}
    merged = verdict.merge(det, {"R10": {"score": 0, "evidence": "seam"}}, {})
    assert merged["R10"]["score"] == 0


# ---- labels and split --------------------------------------------------------
def test_split_is_deterministic_disjoint_and_stratified():
    lab = {f"v{i:02d}": {"grade": g} for i, g in enumerate(["B", "B", "C", "C", "C", "D", "D", "F", "F", "F"])}
    a, b = labels.stratified_split(lab), labels.stratified_split(lab)
    assert a == b
    assert not set(a["tuning"]) & set(a["held_out"])
    assert len(a["tuning"]) + len(a["held_out"]) == 10
    for g in "BCDF":
        n = sum(lab[v]["grade"] == g for v in a["tuning"]), sum(lab[v]["grade"] == g for v in a["held_out"])
        assert abs(n[0] - n[1]) <= 1


def test_forced_tuning():
    lab = {"v27": {"grade": "D"}, "v28": {"grade": "D"}}
    assert "v27" in labels.stratified_split(lab)["tuning"]


def test_tier_mapping():
    assert labels.tier("D+") == "must_fail" and labels.tier("F") == "must_fail"
    assert labels.tier("B-") == "should_pass" and labels.tier("C") == "middle"


def test_confusion_rates():
    lab = {"a": {"grade": "D"}, "b": {"grade": "F"}, "c": {"grade": "B"}, "d": {"grade": "C"}}
    cm = calibrate.confusion({"a": "fail", "b": "pass", "c": "fail", "d": "pass"}, lab, list(lab))
    assert cm["recall_must_fail"] == (1, 2) and cm["false_fail_should_pass"] == (1, 1)


# ---- VLM plumbing with the model mocked --------------------------------------
def test_clean_score_rejects_bad_scores():
    assert vlm.clean_score({"score": 2, "evidence": "ok"})["score"] == 2
    assert vlm.clean_score({"score": 7})["score"] is None
    assert vlm.clean_score({"score": "1"})["score"] == 1


def test_pair_score_requires_agreement_across_orders():
    win = {"more_photographic": "A", "render_is": "A", "margin": "clear"}
    lose_clear = {"more_photographic": "A", "render_is": "B", "margin": "clear"}
    lose_slight = {"more_photographic": "B", "render_is": "A", "margin": "slight"}
    assert vlm.pair_score(win, dict(win, more_photographic="B", render_is="B"))["score"] == 2
    assert vlm.pair_score(lose_clear, dict(lose_clear))["score"] == 0
    assert vlm.pair_score(lose_slight, dict(lose_slight))["score"] == 1
    assert vlm.pair_score(win, lose_clear)["score"] == 1            # position bias -> warn


def test_score_view_with_mocked_model(monkeypatch, tmp_path):
    calls = []

    def fake_chat(host, model, prompt, images, options, schema, think=False, timeout=0):
        calls.append((len(images), "more_photographic" in schema["properties"]))
        if "more_photographic" in schema["properties"]:
            return {"more_photographic": "equal", "margin": "slight", "evidence": "tie"}
        return {"score": 1, "evidence": "mock"}
    monkeypatch.setattr(vlm, "chat", fake_chat)
    jpg = tmp_path / "a.jpg"
    jpg.write_bytes(b"x")
    rub = verdict.load_rubric()
    out = vlm.score_view("http://none", rub, str(jpg), str(jpg), "Kitchen")
    assert set(out) == {"R5", "R7", "R8", "R9", "R10", "R11", "R13"}
    assert out["R13"]["score"] == 2 and out["R8"]["score"] == 1
    assert calls.count((2, True)) == 2                              # both orders


def test_chat_retries_truncated_json_then_gives_empty(monkeypatch):
    import io
    import json as _json
    replies = iter(['{"evidence": "cut off', '{"evidence": "ok", "score": 1}'])
    seen = []

    class R(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_open(req, timeout=0):
        seen.append(_json.loads(req.data)["options"])
        return R(_json.dumps({"message": {"content": next(replies)}}).encode())
    monkeypatch.setattr(vlm.urllib.request, "urlopen", fake_open)
    out = vlm.chat("http://x", "m", "p", [], {"num_predict": 100}, vlm.SCORE_SCHEMA)
    assert out["score"] == 1
    assert seen[0]["num_predict"] == 100 and seen[1]["num_predict"] == 300
    assert all(not k.startswith("_") for o in seen for k in o)
    replies = iter(["{bad", "{bad"])                        # unparsable twice -> {} -> not_evaluated
    assert vlm.chat("http://x", "m", "p", [], {"num_predict": 100}, vlm.SCORE_SCHEMA) == {}
    assert vlm.clean_score({})["score"] is None
    assert vlm.pair_score({"render_is": "A"}, {"render_is": "B"})["score"] is None


def test_vlm_unreachable_raises_unavailable():
    with pytest.raises(vlm.VlmUnavailable):
        vlm.chat("http://127.0.0.1:9", "m", "p", [], {}, vlm.SCORE_SCHEMA, timeout=2)


def test_rubric_prompts_cover_all_vlm_criteria_and_title_slot():
    rub = verdict.load_rubric()
    for spec in rub["criteria"].values():
        if spec["kind"].startswith("vlm"):
            assert spec["prompt"] in rub["prompts"]
    assert "{title}" in rub["prompts"]["R11_TRUTH"]
    assert "Kitchen" in vlm.render_prompt(rub, "R11_TRUTH", "Kitchen")


def test_parse_audit_reads_real_table():
    lab = labels.parse_audit(verdict.ROOT / "docs" / "reviews" / "2026-11" / "visual-audit.md")
    assert len(lab) == 38 and lab["v30"]["grade"] == "F" and lab["v30"]["false_pass"]
