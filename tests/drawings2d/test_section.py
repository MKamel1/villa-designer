import json
from pathlib import Path

import pytest

from archpipe import model
from archpipe.drawings2d import modelcut, orient, section, viewdraw
from archpipe.drawings2d.section import View


def _box(x0, y0, z0, x1, y1, z1, m="plaster"):
    """Closed box with outward normals, as faces for slice_faces / clip_far."""
    q = lambda *c: list(c)                                                                        # noqa: E731
    f = [[q(x0, y0, z0), q(x0, y1, z0), q(x1, y1, z0), q(x1, y0, z0)], [q(x0, y0, z1), q(x1, y0, z1), q(x1, y1, z1), q(x0, y1, z1)],
         [q(x0, y0, z0), q(x1, y0, z0), q(x1, y0, z1), q(x0, y0, z1)], [q(x1, y0, z0), q(x1, y1, z0), q(x1, y1, z1), q(x1, y0, z1)],
         [q(x1, y1, z0), q(x0, y1, z0), q(x0, y1, z1), q(x1, y1, z1)], [q(x0, y1, z0), q(x0, y0, z0), q(x0, y0, z1), q(x0, y1, z1)]]
    return [{"p": p, "m": m} for p in f]


V = View("t", "section", (0.0, 1.0, 0.0), (0.0, 0.0), (0, 0, 10, 10))


def test_slice_and_poche_of_a_box_and_a_union():
    faces = _box(1, -1, 0, 3, 1, 2) + _box(2, -1, 0, 5, 1, 1)        # two overlapping boxes: union, not double
    segs = section.slice_faces(faces, V)
    polys = section.poche(segs)
    area = sum(p.area for p in polys)
    assert area == pytest.approx(2 * 2 + 3 * 1 - 1 * 1, abs=1e-6)     # 4 + 3 - overlap 1
    assert section.poche(section.slice_faces(_box(1, 2, 0, 3, 4, 2), V)) == []     # negative: box wholly beyond the plane is not cut


def test_clip_far_removes_the_viewer_side():
    faces = _box(1, -1, 0, 3, 3, 2)
    far = section.clip_far(faces, V)
    assert far and all(p[1] >= -1e-9 for f in far for p in f)
    assert section.clip_far(_box(1, -3, 0, 3, -1, 2), V) == []


def test_u_axis_is_the_viewers_right():
    for v in viewdraw.ELEVATIONS:
        assert v.u_axis == (v.d[1], -v.d[0])
    # looking east (+y): right is south (+x); the left end is client NORTH (the street)
    assert viewdraw.left_right(viewdraw.SECTION_1) == ("N", "S")
    got = {viewdraw.facade(v): viewdraw.left_right(v) for v in viewdraw.ELEVATIONS}
    # standing on the N (street) side facing south: right is WEST; S facade: right is EAST; E facade: right is NORTH; W: right is SOUTH
    assert got == {"N": ("E", "W"), "S": ("W", "E"), "E": ("S", "N"), "W": ("N", "S")}


def test_elevation_directions_point_at_the_facade():
    """Camera stands on the named side and looks toward the building: -d is that side's model direction."""
    side = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}
    for v in viewdraw.ELEVATIONS:
        assert (-v.d[0], -v.d[1]) == side[viewdraw.facade(v)]


@pytest.fixture(scope="module")
def els():
    return model.load("D1")


def test_model_cut_matches_known_dimensions(els):
    levels = json.loads(Path(model.api.snapshot_path("D1")).read_text())["levels"]
    cut = modelcut.cut_solids(els, levels, viewdraw.SECTION_1)
    ids = {i[0] for i in cut["items"]}
    assert "slab-B-floor" in ids and "slab-GF-floor" in ids and any(i.startswith("stair-main-t") for i in ids)
    slab = [i for i in cut["items"] if i[0] == "slab-B-floor"][0][3]
    assert slab[1] == pytest.approx(-3.2) and slab[3] == pytest.approx(-3.0)           # 200 mm slab, top at the B floor
    # stair orientation against the MODEL: the lowest tread is at the larger x (south) in the east-looking section
    t = sorted((i for i in cut["items"] if i[0].startswith("stair-main-t")), key=lambda i: i[3][1])
    assert t[0][3][0] > t[-1][3][0]
    # GF slab has the stair opening: no slab cut between the void edges at x 5.177..8.887
    gf = [i for i in cut["items"] if i[0] == "slab-GF-floor"]
    assert all(not (b[0] < 7.0 < b[2]) for _, _, _, b in gf)


def test_elevation_has_no_cut_and_section_two_cuts_the_ramp(els):
    levels = json.loads(Path(model.api.snapshot_path("D1")).read_text())["levels"]
    c2 = modelcut.cut_solids(els, levels, viewdraw.SECTION_2)
    assert any(i[1] == "ramp" for i in c2["items"])                                  # plane y -22.2 crosses the car ramp
    c1 = modelcut.cut_solids(els, levels, viewdraw.SECTION_1)
    assert not any(i[1] == "ramp" for i in c1["items"])                              # negative: the stair plane does not


def test_blender_lineart_smoke():
    if not section.BLENDER.exists():
        pytest.skip("Blender not installed")
    faces = _box(1, 2, 0, 3, 4, 2) + _box(1, 6, 0, 3, 8, 2)
    strokes = section.run_lineart([f["p"] for f in faces], V)
    assert strokes
    ys = [p[1] for s in strokes for p in s]
    assert min(ys) < 2.1                                  # the nearer box outline is there
