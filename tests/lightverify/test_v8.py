"""The mutation runner on the cheap mutations (the vase and plane-height ones run against the real scene in the CLI)."""
from archpipe.lightcalc.villa import Villa
from archpipe.lightverify import v8_mutation as V8


def test_mutations_that_need_no_scene_are_all_caught(tmp_path):
    from pathlib import Path
    v = Villa()
    rad = Path(__file__).resolve().parents[2] / "knowledge" / "lighting-verify" / "radiance"
    L = V8.run(v, rad, ts=None)
    assert not [r.message for r in L.results if r.status == "fail"], L.notes


def test_a_mutation_that_changes_nothing_is_reported_missed(monkeypatch):
    monkeypatch.setattr(V8, "m_wrong_watts", lambda villa: ("V1", set(), "no-op mutation"))
    from pathlib import Path
    rad = Path(__file__).resolve().parents[2] / "knowledge" / "lighting-verify" / "radiance"
    L = V8.run(Villa(), rad, ts=None)
    assert any(r.status == "fail" and "MISSED" in r.message for r in L.results)
