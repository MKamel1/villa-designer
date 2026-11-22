"""LV recomputation of the LA4 lying-looking-up sightlines (L6d): positive on the design, negative for a downlight too near a pillow."""
import dataclasses
import json
from pathlib import Path

import pytest

from archpipe import photometry
from archpipe.lightcalc.villa import Villa
from archpipe.lightverify import ies, v_la4 as W

SCENE = Path("/home/omar/archpipe/lanes/L6d/out/L6d/prod/scene.json")


@pytest.fixture(scope="module")
def villa():
    return Villa()


def test_design_sightlines_agree_with_the_engine_and_stay_under_the_cap(villa):
    rows = {r["id"]: r for r in W.run(villa)}
    assert len(rows) == 5 and all(r["eye_in_footprint"] for r in rows.values())
    assert all(r["mine"] <= W.CAP for r in rows.values())
    adj = rows["pb-bed-lying-up-min-y-p2"]                      # the one fitting in view: the bedroom ADJ toward pillow 2 (L6d: 1656)
    assert adj["mine_by"] == "ADJ-parents-bed-05" and abs(adj["mine"] - adj["engine"]) < 0.01 * adj["engine"] and 1500 < adj["mine"] < 1800
    assert all(abs(r["mine"] - r["engine"]) <= 0.02 * max(r["mine"], r["engine"]) + 10 for r in rows.values())


def test_a_downlight_one_metre_from_a_pillow_exceeds_the_cap_and_two_point_three_does_not(villa):
    p0 = next(p for p in villa.placements if p.meta.get("kind") == "DL" and not p.meta.get("generic"))
    d = ies.parse(Path(p0.meta["ies_path"]).read_text(encoding="utf-8-sig", errors="replace").replace("﻿", ""))
    eye = (20.0, -26.0, 0.7)
    near = dataclasses.replace(p0, position=(21.0, -26.0, 2.7), aim=(0, 0, -1))
    far = dataclasses.replace(p0, position=(22.3, -26.0, 2.7), aim=(0, 0, -1))
    assert W.luminance(near, d, eye) > 10 * W.CAP
    assert W.luminance(far, d, eye) < W.CAP


@pytest.mark.skipif(not SCENE.exists(), reason="production scene not on this machine")
def test_other_room_fittings_are_behind_walls_and_a_clear_line_is_not():
    tris = W.shell_triangles(SCENE)
    assert W.segment_hits(tris, (19.93, -26.19, 0.7), (19.93, -27.9, 2.7)) >= 1         # pillow 1 toward the dressing room: a wall crosses
    assert W.segment_hits(tris, (19.93, -25.2, 0.7), (21.0, -24.9, 2.6)) == 0           # inside the bedroom: nothing crosses
