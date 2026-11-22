"""Render-set data: static checks and plan coverage, positive and negative."""
import copy

import pytest

from archpipe.critic import render_set as S

ROOMS = {"a": {"level": "B", "rect": [0, 0, 4, 4]}, "b": {"level": "B", "rect": [20, 0, 24, 4]}}


def _view(cam_target, lens=24, z=-1.65):
    return {"camera": {"position": [2, 2, z], "target": cam_target + [z], "lens_mm": lens, "sensor_mm": 36}}


def _entry(**kw):
    return {"id": "x", "purpose": "p", "reuse": True, "covers": ["a"], **kw}


def test_problems_clean_entry():
    assert S.problems({"views": [_entry()]}, ROOMS) == []


@pytest.mark.parametrize("patch,needle", [
    ({"purpose": " "}, "no purpose"),
    ({"lens_mm": 16}, "under 24"),
    ({"covers": []}, "covers no room"),
    ({"covers": ["zz"]}, "unknown room"),
])
def test_problems_negative(patch, needle):
    assert any(needle in p for p in S.problems({"views": [_entry(**patch)]}, ROOMS))


def test_duplicate_id_is_reported():
    assert any("duplicate" in p for p in S.problems({"views": [_entry(), _entry()]}, ROOMS))


def test_garden_view_may_have_no_room():
    e = _entry(garden=True, covers=[])
    assert S.problems({"views": [e]}, ROOMS) == []


def test_coverage_counts_room_in_frame_only():
    data = {"views": [_entry(covers=["a", "b"])]}
    cov = S.coverage([dict(id="x", **_view([6, 2]))], data, ROOMS)
    assert cov["a"] == ["x"]          # camera stands in a, looking east
    assert cov["b"] == []             # b is declared but 18 m away and past the 14 m reach


def test_coverage_ignores_room_behind_camera():
    data = {"views": [_entry(covers=["a"])]}
    v = dict(id="x", camera={"position": [10, 2, -1.65], "target": [14, 2, -1.65], "lens_mm": 24, "sensor_mm": 36})
    assert S.coverage([v], data, ROOMS)["a"] == []   # looking away from a


def test_coverage_ignores_wide_lens_and_other_storey():
    data = {"views": [_entry()]}
    assert S.coverage([dict(id="x", **_view([6, 2], lens=16))], data, ROOMS)["a"] == []
    assert S.coverage([dict(id="x", **_view([6, 2], z=1.35))], data, ROOMS)["a"] == []


def test_real_set_covers_every_room_at_24mm():
    from archpipe.concept import villa_r11 as R, villa_render as VR
    lay = R.design("D1")
    data = S.load()
    assert S.problems(data, lay["rooms"]) == []
    views = S.resolve(data, lay, VR.VIEWS(lay))
    assert [v["id"] for v in views] == [e["id"] for e in data["views"]]
    assert all(v["camera"]["lens_mm"] >= 24 for v in views)
    missing = [r for r, ids in S.coverage(views, data, lay["rooms"]).items() if not ids]
    assert missing == []


def test_room_views_at_room_edge_or_in_an_opening_are_doorway_views():
    """Guard for the L9P draft defect: 5 of 17 chosen views stood in a door opening without being marked
    `doorway`, so the build kept the door leaf and the camera faced it. The flag follows villa_render._VIEWS."""
    from archpipe.concept import villa_r11 as R, villa_render as VR
    lay = R.design("D1")
    data = S.load()
    views = {v["id"]: v for v in S.resolve(data, lay, VR.VIEWS(lay))}
    checked = 0
    for e in data["views"]:
        if "room" not in e:
            continue
        v = views[e["id"]]
        x, y = v["camera"]["position"][:2]
        x0, y0, x1, y1 = lay["rooms"][e["room"]]["rect"]
        strictly_inside = x0 < x < x1 and y0 < y < y1
        checked += 1
        if not strictly_inside:
            assert v["camera"]["reframed"] == "doorway", e["id"]
        else:
            assert v["camera"]["reframed"] in ("chosen", "doorway"), e["id"]   # may still be in an opening
    assert checked >= 8
    assert any(v["camera"].get("reframed") == "doorway" for v in views.values())   # the negative would be vacuous
