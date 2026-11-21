"""CLI behaviour with the VLM mocked or off. No network."""
import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image

from archpipe import contracts
from archpipe.critic import meta, verdict

ROOT = Path(__file__).resolve().parents[2]


def load_cli():
    spec = importlib.util.spec_from_file_location("critic_run", ROOT / "scripts" / "critic_run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_png(tmp_path, name="v99-test.png", value=0.5):
    arr = (np.full((200, 300, 3), value) * 255).astype("uint8")
    p = tmp_path / name
    Image.fromarray(arr).save(p)
    p.with_suffix(".json").write_text(json.dumps({
        "resolution": [300, 200], "camera_pitch_deg": 0.0, "subjects": [],
        "exposure_rule_measurement": {"view_input": {"camera": {
            "position": [0, 0, 1.35], "target": [3, 0, 1.35], "lens_mm": 24}}}}), encoding="utf-8")
    return p


def test_cli_without_vlm_fails_closed_and_writes_check_results(tmp_path, capsys):
    cli = load_cli()
    png = make_png(tmp_path)
    assert cli.main([str(png), "--vlm", "off", "--checks-dir", str(tmp_path / "checks")]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["verdict"] == "fail" and out["notes"]["vlm"] == "unavailable"
    assert out["lens_mm"] == 24 and out["camera_height_m"] == 1.35
    results = contracts.read_all_results(tmp_path / "checks")
    status = {r.criterion: r.status for r in results}
    assert status["R1"] == "pass" and status["R5"] == "not_evaluated" and status["R6"] == "not_evaluated"
    assert all(r.lane == "L3" for r in results)


def test_cli_with_cached_vlm_scores(tmp_path, capsys):
    cli = load_cli()
    png = make_png(tmp_path)
    cache = tmp_path / "cache"
    cache.mkdir()
    scores = {c: {"score": 2, "evidence": "ok"} for c in ("R5", "R7", "R8", "R9", "R10", "R11", "R13")}
    (cache / "v99.json").write_text(json.dumps({"view": "v99", "status": "ok", "scores": scores}), encoding="utf-8")
    cli.main([str(png), "--vlm", str(cache), "--checks-dir", str(tmp_path / "checks")])
    out = json.loads(capsys.readouterr().out)
    assert out["notes"]["vlm"] == "ok"
    assert out["scores"]["R7"] == 2 and out["scores"]["R6"] is None


def test_visible_assets_projects_bounds():
    view = {"camera": {"position": [0, 0, 1.35], "target": [5, 0, 1.35], "lens_mm": 24},
            "resolution": [1920, 1280],
            "imported_models": [
                {"asset": "front", "bounds": [4.5, -0.5, 0.0, 5.5, 0.5, 1.0]},
                {"asset": "behind", "bounds": [-5.5, -0.5, 0.0, -4.5, 0.5, 1.0]},
                {"asset": "far_left", "bounds": [4.5, 9.5, 0.0, 5.5, 10.5, 1.0]}]}
    assert meta.visible_assets(view) == {"front"}


def test_clone_report_needs_four_views():
    v = {"camera": {"position": [0, 0, 1.35], "target": [5, 0, 1.35], "lens_mm": 24}, "resolution": [1920, 1280],
         "imported_models": [{"asset": "sofa", "bounds": [4.5, -0.5, 0, 5.5, 0.5, 1]}]}
    assert meta.clone_report({f"v{i}": v for i in range(3)}) == {}
    assert list(meta.clone_report({f"v{i}": v for i in range(4)})) == ["sofa"]


def test_rubric_declares_gating_after_freeze_or_defaults_to_all():
    rub = verdict.load_rubric()
    if str(rub["version"]).startswith("frozen"):
        assert set(rub["gating"]["vlm"]) <= set(verdict.VLM_CRITERIA)
