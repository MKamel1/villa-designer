"""L6b villa lighting: harness geometry, zones, and the non-Radiance checks (LA6, LA8, LA9, LA10, LA13) with negative cases.
The Villa object is built once (design() takes ~30 s); no Radiance and no external library are needed (frozen products)."""
import copy
import math

import pytest

from archpipe.lightcalc import villa as V
from archpipe.lightcalc import villa_checks as VC
from archpipe.concept import villa_lighting as VL


@pytest.fixture(scope="module")
def villa():
    return V.Villa()


def test_union_of_rectangles_is_one_outline():
    poly = V.union_rects([(0, 0, 2, 1), (0, 1, 1, 3)])          # an L
    assert len(poly) == 6 and abs(sum(poly[i][0] * poly[(i + 1) % 6][1] - poly[(i + 1) % 6][0] * poly[i][1] for i in range(6)) / 2) == pytest.approx(4.0)
    assert len(V.union_rects([(0, 0, 1, 1), (1, 0, 2, 1)])) == 4   # two touching rectangles merge to one rectangle


def test_hemisphere_photometry_conserves_flux():
    from archpipe.lightcalc import synth
    ph = synth.load_text(V.hemisphere_ies(300.0), "h")
    assert ph.integrated_flux() == pytest.approx(300.0, rel=0.02)


def test_every_fixture_has_a_zone_in_its_own_room_and_cluster(villa):
    ids = set()
    for f in villa.fixtures:
        z = VL.zone_id(f)
        assert z.startswith("Z-" + f.level + "-")
        ids.add(z)
        V.cluster_of(f.room)                       # raises for a room outside the cluster table
    assert len(ids) > 40


def test_drivers_cap_products_and_scale_generics(villa):
    for f in villa.fixtures:
        if f.record.product:
            assert 0 < f.extra.get("dimmer", 1.0) <= 1.0


def test_la6_one_cct_per_layer_and_spec_equals_product(villa):
    assert all(r.status == "pass" for r in VC.check_la6(villa.fixtures))


def test_la6_negative_mixed_cct():
    from archpipe.concept.villa_lighting import Fixture
    a = Fixture("A", "DL", "x", "B", 0, 0, 2.7)
    b = Fixture("B", "DESK", "x", "B", 0, 0, 2.7)
    b.extra["layer"] = "ambient"                    # a 2700 K downlight and a (forced) 2200 K night kind in one layer
    c = Fixture("C", "NL", "x", "B", 0, 0, 0.05, length=1.0)
    c.extra["layer"] = "ambient"
    assert any(r.status == "fail" for r in VC.check_la6([a, c])[:1])


def test_la8_every_habitable_space_has_two_layers(villa):
    rows = VC.check_la8(villa.fixtures)
    assert all(r.status == "pass" for r in rows), [r.subject for r in rows if r.status != "pass"]


def test_la8_negative_single_layer(villa):
    one = [f for f in villa.fixtures if f.room == "kids-a" and VL.zone_layer(f) == "ambient"]
    rows = {r.subject: r for r in VC.check_la8(one)}
    assert rows["villa/layers/kids-a"].status == "fail"


def test_la9_all_recessed_fittings_on_declared_axes(villa):
    assert VC.check_la9(villa)[0].status == "pass"


def test_la9_negative_a_moved_fitting_fails(villa):
    v = copy.copy(villa)
    v.fixtures = [copy.copy(f) for f in villa.fixtures]
    f = next(f for f in v.fixtures if f.id.startswith("DL-lounge"))
    f.x += 0.037
    f.y += 0.053
    r = VC.check_la9(v)[0]
    assert r.status == "fail" and "lum-" + f.id in r.element_ids


def test_la13_stair_and_basement_routes_have_one_lux(villa):
    rows = VC.check_la13(villa)
    assert len(rows) == 3 and all(r.status == "pass" and r.achieved >= 1.0 for r in rows)


def test_la13_negative_no_markers(villa):
    v = copy.copy(villa)
    v.fixtures = [f for f in villa.fixtures if VL.zone_layer(f) not in ("night", "emergency")]
    assert any(r.status in ("fail", "not_evaluated") for r in VC.check_la13(v))


def test_la10_night_path_level_and_scene_completeness(villa):
    assert VC.check_la10_night(villa).status == "pass"
    assert all(r.status in ("pass", "not_evaluated") for r in VC.check_la10_scenes(VL.SCENES))
    assert any(r.status == "fail" for r in VC.check_la10_scenes({"B-open": {"Day": {}}}))


def test_la4_luminance_within_cap(villa):
    assert all(r.status == "pass" for r in VC.check_la4(villa, VC.sightlines(villa)))


def test_dining_table_has_no_crossed_spot_pair(villa):
    """The pair of crossed adjustable fills (950 lx on the table centre, truth probe variant A) was cut."""
    assert not [f for f in villa.fixtures if f.kind == "ADJ" and f.room in ("dining", "dining-side")
                and abs(f.aim[2]) < 0.9 and f.aim[0] != 0.0]


def test_zones_file_matches_the_fixtures(villa):
    from archpipe.lightcalc import villa_emit as VE
    zones = VE.build_zones(villa)
    ids = [i for z in zones for i in z.luminaire_ids]
    assert len(ids) == len(set(ids)) == len(villa.fixtures)
    assert {z.layer for z in zones} <= {"ambient", "task", "accent", "decorative", "exterior", "emergency"}
    assert all(z.watts > 0 and z.dimming in ("dali2", "phase_cut", "switched", "0_10v") for z in zones)
