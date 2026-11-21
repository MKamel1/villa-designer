import math
import os
from pathlib import Path

import pytest

from archpipe.lightcalc import radjob, synth
from archpipe.lightcalc.direct import Placement, aim_angles
from archpipe.lightcalc.radjob import RadJob, RadParams, Room, Sensor, have_local_radiance, room_scene_text, xform_chain
from archpipe.lightcalc.roomcalc import RoomCalc, Scene, TaskPlane

L_SHAPE = ((0, 0), (4, 0), (4, 2), (2, 2), (2, 4), (0, 4))


def _pl(zone, dim=1.0, pos=(1.0, 1.0, 2.5)):
    t = synth.cosine_ies_text(1000.0)
    return Placement(f"S-{zone}", synth.load_text(t, "c"), pos, zone=zone, dim=dim, meta={"ies_text": t})


def test_polygon_room_scene_has_one_wall_per_edge_and_floor_ceiling():
    txt = room_scene_text(Room(L_SHAPE, 0.0, 2.7, 0.3, 0.6, 0.8))
    assert txt.count(" polygon wall") == 6 and txt.count(" polygon floor") == 1 and txt.count(" polygon ceiling") == 1
    assert "void plastic m_wall" in txt and "5 0.6000 0.6000 0.6000 0 0" in txt
    # wall quads all span floor to ceiling
    assert " 2.700000" in txt and " 0.000000" in txt


def test_reflectance_is_clamped_below_one():
    assert "0.9900" in room_scene_text(Room(L_SHAPE, 0, 2.7, 1.0, 1.0, 1.0))


def test_xform_chain_for_aim_and_spin():
    assert xform_chain(_pl("a")) == ["-t", "1.000000", "1.000000", "2.500000"]
    p = Placement("x", _pl("a").photometry, (0, 0, 3), aim=(1, 0, -1), spin_deg=10.0)
    tilt, az = aim_angles(p.aim)
    assert tilt == pytest.approx(45.0) and az == pytest.approx(0.0)
    assert xform_chain(p)[:6] == ["-rz", "10.000000", "-ry", "-45.000000", "-rz", "0.000000"]


def test_job_writes_per_zone_octrees_points_and_ab_levels(tmp_path):
    job = RadJob("t", Room(L_SHAPE), [_pl("A"), _pl("B", pos=(3, 1, 2.5))], [Sensor(1, 1, 0.85), Sensor(3, 1, 0.85)],
                 RadParams(ab=4, ab_extra=(8,)))
    sh = job.prepare(tmp_path).read_text()
    for z in ("A", "B"):
        assert f"oconv room.rad" in sh and f"scene_{z}.oct" in sh
        for ab in (0, 4, 8):
            assert f"-ab {ab} " in sh and f"out_{z}_ab{ab}.txt" in sh
    assert (tmp_path / "points.txt").read_text().count("\n") == 2
    assert (tmp_path / "ies00.ies").exists()                         # luminaire file staged once per photometry
    assert "\r" not in sh                                            # runs under bash


def test_job_parse_roundtrip(tmp_path):
    job = RadJob("t", None, [_pl("A")], [Sensor(0, 0, 0), Sensor(1, 0, 0)], RadParams(ab=1))
    job.prepare(tmp_path)
    for ab in job.ab_levels():
        (tmp_path / f"out_A_ab{ab}.txt").write_text("1.0 1.0 1.0\n0.5 0.5 0.5\n")
    res = job.parse(tmp_path)
    assert res["A"][0][0] == pytest.approx(179.0, rel=1e-6) and res["A"][1][1] == pytest.approx(89.5, rel=1e-6)
    (tmp_path / "out_A_ab1.txt").write_text("1.0 1.0 1.0\n")
    with pytest.raises(Exception):
        job.parse(tmp_path)                       # truncated output must not parse


def _calc_with_fake_results():
    plane = TaskPlane("task", ((0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5)), 0.85, 100.0, spacing=0.5)
    calc = RoomCalc("R", Room(L_SHAPE), [_pl("A"), _pl("B")], [plane], RadParams(ab=4), mf=0.8)
    n = len(calc.sensors())
    calc.results = {"A": {0: [100.0] * n, 4: [150.0] * n}, "B": {0: [40.0] * n, 4: [60.0] * n}}
    return calc, n


def test_scene_recombination_is_linear_in_zone_levels():
    calc, n = _calc_with_fake_results()
    full = Scene.full(["A", "B"])
    assert calc.stats("task", full).em == pytest.approx((150 + 60) * 0.8)          # MF applied once
    assert calc.stats("task", full, direct=True).em == pytest.approx((100 + 40) * 0.8)
    dim = Scene("dim", {"A": 0.5, "B": 0.0})
    assert calc.stats("task", dim).em == pytest.approx(75 * 0.8)
    off = Scene("off", {})
    assert calc.stats("task", off).em == 0.0
    with pytest.raises(ValueError):
        calc.stats("task", Scene("bad", {"A": 1.5}))


def test_scene_checks_flip_with_dimming_la2():
    calc, _ = _calc_with_fake_results()
    full = calc.checks(Scene.full(["A", "B"]))
    la2 = [r for r in full if r.criterion == "LA2"][0]
    assert la2.status == "fail" and la2.achieved == pytest.approx(168.0)          # 1.68 x target
    dim = calc.checks(Scene("dim", {"A": 0.5, "B": 0.0}))
    assert [r for r in dim if r.criterion == "LA2"][0].status == "pass"           # 60 lx
    assert [r for r in dim if r.criterion == "LA1"][0].status == "fail"           # 60 lx is below 90 lx: under-lit
    mid = calc.checks(Scene("mid", {"A": 0.8, "B": 0.0}))
    assert [r for r in mid if r.criterion == "LA1"][0].status == "pass"           # 0.8*150*0.8 = 96 lx, inside 90-110
    assert [r for r in mid if r.criterion == "LA2"][0].status == "pass"
