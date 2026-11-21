import pytest

from archpipe import model
from archpipe.drawings2d import orient, standard
from archpipe.documents import plans


@pytest.fixture(scope="module")
def els():
    return model.load("D1")


def test_street_wall_is_north_up(els):
    """Street side (model -x) must end at the TOP of the sheet (max Y), east (+y) to the right. Negative: not mirrored."""
    c = {e.id: e for e in orient.to_client(els)}
    street = min((e for e in els if e.kind == "wall"), key=lambda e: e.params["x0_mm"])
    assert c[street.id].params["y0_mm"] == max(e.params["y0_mm"] for e in c.values() if e.kind == "wall")
    assert orient.pt(0, 1000) == (1000, 0)            # +y (east) -> right
    assert orient.pt(1000, 0) == (0, -1000)           # +x (south) -> down
    # a rotation, not a reflection: orientation of a triangle is preserved
    (ax, ay), (bx, by), (cx, cy) = orient.pt(0, 0), orient.pt(1, 0), orient.pt(0, 1)
    assert (bx - ax) * (cy - ay) - (by - ay) * (cx - ax) > 0


def test_compass_words():
    assert orient.compass_of_model_vector(-1, 0) == "N" and orient.compass_of_model_vector(0, 1) == "E"
    assert orient.compass_of_model_vector(1, 0) == "S" and orient.compass_of_model_vector(0, -1) == "W"


def test_roundtrip_and_double_transform_refused(els):
    assert orient.inv(*orient.pt(123.0, -456.0)) == (123.0, -456.0)
    c = orient.to_client(els)
    with pytest.raises(ValueError):
        orient.to_client(c)


def test_swing_hinge_follows_authored_handing(els):
    """The drawn hinge is the jamb nearest the authored hinge_xy_mm (client frame)."""
    s = {"no": "T", "level": "GF", "scale": "1:100", "paper": "A2 landscape", "title_en": "t", "title_ar": "t"}
    spec = {"project": {"project": "p", "owner": None, "address": "", "engineer": None, "syndicate_no": None,
                        "date": "d", "revision": "P01", "revision_location": ""}, "design": "D1",
            "levels": {"GF": {"ffl_revit_mm": 1200}}}
    rep = plans.render_plan(els, spec, s, "/tmp/rv2-test/gf", formats=("png",))
    cel = {e.id: e for e in orient.to_client(els)}
    assert rep["swings"]
    for sw in rep["swings"]:
        hx = cel[sw["id"]].params["hinge_xy_mm"]
        assert abs(sw["hinge_xy"][0] - hx[0]) < 200 and abs(sw["hinge_xy"][1] - hx[1]) < 200


def test_line_weights_grade_with_scale_and_eq():
    assert standard.pen("cut", 20) > standard.pen("cut", 100) > standard.pen("cut", 200)
    assert standard.pen("proj", 100) < standard.pen("cut", 100)
    assert standard.eq_label([1200, 1200, 1200, 800]) == ["1200", "EQ", "EQ", "800"]
    assert standard.eq_label([1200, 1200, 800]) == ["1200", "1200", "800"]      # a pair is not EQ
    assert standard.eq_label([1200, 1203, 1200]) == ["1200", "1203", "1200"]    # tolerance 1 mm
