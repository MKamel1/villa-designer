"""L6d: two generic strips of the same kind with different flux get their own IES file in the Radiance job (they shared the first one's)."""
from archpipe.lightcalc import synth
from archpipe.lightcalc.direct import Placement
from archpipe.lightcalc.radjob import RadJob, RadParams, Room, Sensor


def _strip(pid, lm, zone):
    t = synth.cosine_ies_text(lm)
    return Placement(pid, synth.load_text(t, "COVE-part"), (1.0, 1.0, 2.5), zone=zone, meta={"ies_text": t, "generic": True})


def test_generic_strips_of_one_kind_with_different_flux_get_separate_files(tmp_path):
    room = Room(((0, 0), (4, 0), (4, 4), (0, 4)), 0.0, 2.7, 0.3, 0.6, 0.8)
    job = RadJob("t", room, [_strip("a", 100.0, "Z1"), _strip("b", 400.0, "Z2"), _strip("c", 400.0, "Z2")], [Sensor(1, 1, 0.8, 0, 0, 1)], RadParams(ab=1))
    job.prepare(tmp_path)
    files = sorted(p.name for p in tmp_path.glob("ies*.ies"))
    assert files == ["ies00.ies", "ies01.ies"]                 # 100 lm and 400 lm: two files; the third (400 lm again) reuses the second


def test_negative_the_old_key_would_have_merged_them():
    a, b = _strip("a", 100.0, "Z1"), _strip("b", 400.0, "Z2")
    old = lambda p: p.photometry.name + "|" + str(p.meta.get("ies_path") or p.photometry.source or "")
    assert old(a) == old(b)
