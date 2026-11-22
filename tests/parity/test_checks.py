"""Each check: a positive (fails on the defect) and a negative (quiet on a legitimate near-case)."""
import numpy as np

from archpipe.parity import checks as C
from archpipe.parity.geom import box_tris
from archpipe.parity.world import Element, world_from_boxes


def fails(fs):
    return [f for f in fs if f.status == "fail"]


def W(**boxes):
    return world_from_boxes({k.replace("_", "-"): v for k, v in boxes.items()})


def test_k01_stair_through_a_column_fails_and_touching_is_quiet():
    bad = W(stair_main=(0, 0, 0, 1, 1, 1), column_01=(0.97, 0.2, -1, 2, 0.8, 5))
    assert fails(C.k01_stair_structure(bad))
    ok = W(stair_main=(0, 0, 0, 1, 1, 1), column_01=(1.0, 0.2, -1, 2, 0.8, 5))          # touching face to face
    assert not fails(C.k01_stair_structure(ok))
    gap = W(stair_main=(0, 0, 0, 1, 1, 1), column_01=(1.005, 0.2, -1, 2, 0.8, 5))
    assert not fails(C.k01_stair_structure(gap))


def test_k01_exact_tolerance_sees_a_sub_millimetre_contact_the_scene_tolerance_cannot():
    w = W(stair_main=(0, 0, 0, 1.0002, 1, 1), column_01=(1.0, 0.2, -1, 2, 0.8, 5))
    assert fails(C.k01_stair_structure(w, tol=C.TOL_EXACT))
    assert not fails(C.k01_stair_structure(w))                                             # 0.2 mm < 2 mm scene tolerance


def test_k02_wall_through_a_ramp_fails_and_a_join_at_the_edge_is_quiet():
    ramp = box_tris((0, 0, -1, 5, 3, 0))
    through = W(wall_B_x=(2, 0.5, -3, 2.1, 2.5, 0.7))                  # 0.7 m above the ramp top, wholly inside its plan
    through.elements["slab-ramp"] = Element("slab-ramp", [("r", "box", None, None, ramp)])
    assert fails(C.k02_wall_slab(through))
    join = W(wall_B_x=(0, 3 - 0.05, -3, 5, 3.05, 0.7))                 # centre line on the ramp edge: overlap is half the thickness
    join.elements["slab-ramp"] = Element("slab-ramp", [("r", "box", None, None, ramp)])
    assert not fails(C.k02_wall_slab(join))


def test_k03_door_through_a_column_fails():
    assert fails(C.k03_opening_column(W(door_x=(0, 0, 0, 0.8, 0.1, 2.1), column_01=(0.5, -1, 0, 1.5, 1, 3))))
    assert not fails(C.k03_opening_column(W(door_x=(0, 0, 0, 0.8, 0.1, 2.1), column_01=(0.805, -1, 0, 1.5, 1, 3))))


def _door_world(head):
    w = W(slab_up=(-1, -1, 2.0, 3, 3, 2.3), wall_h=(0, -0.1, 0, 0.1, 0.1, 2.0))
    leaf = box_tris((0.2, -0.05, 0, 1.0, 0.05, head))
    w.elements["door-x"] = Element("door-x", [("d", "shell", "door-oak", "door-leaf", leaf)])
    return w, {"door-x": dict(id="door-x", kind="door", level="GF", host="wall-h", params={})}


def test_k04_door_taller_than_the_soffit_fails_and_five_mm_below_is_quiet():
    w, m = _door_world(2.10)
    assert fails(C.k04_door_soffit(w, m))
    w, m = _door_world(1.995)
    assert not fails(C.k04_door_soffit(w, m))


def test_k06_full_height_glass_short_of_the_beam_fails():
    def world(top):
        w = W(beam_0=(-1, -1, 2.4, 3, 3, 3.0))
        w.elements["window-a"] = Element("window-a", [("g", "shell", "glass-clear", "glass-pane", box_tris((0.2, 0, -3.0 + 3.0, 1.2, 0.01, top)))])
        return w
    m = {"window-a": dict(id="window-a", kind="window", level="GF", host="", params=dict(full_height=True))}
    assert fails(C.k06_glazing_to_beam(world(2.0), m))
    assert not fails(C.k06_glazing_to_beam(world(2.3), m))


def test_k07_pendant_through_the_ceiling_and_off_datum_fail():
    m = {"lum-p": dict(id="lum-p", kind="luminaire", level="GF", placement=[0, 0, 2000.0], params=dict(mount="pendant"))}

    def world(lo, hi):
        w = W(slab_c=(-1, -1, 2.7, 2, 2, 2.8))
        w.elements["lum-p"] = Element("lum-p", [("l", "fixture", None, None, box_tris((0, 0, lo, 0.3, 0.3, hi)))])
        return w
    assert not fails(C.k07_fixture_ceiling(world(2.0, 2.7), m))
    assert fails(C.k07_fixture_ceiling(world(2.0, 2.72), m))        # shade top through the ceiling (D08)
    assert fails(C.k07_fixture_ceiling(world(2.243, 2.7), m))       # emitter 243 mm off its datum (D08)
    assert not fails(C.k07_fixture_ceiling(world(2.005, 2.7), m))


def test_k08_bbox_vs_stated_size():
    assert fails(C.k08_bbox_vs_figure_partial([("f", [822, 918, 1645], [711, 813])]))
    assert not fails(C.k08_bbox_vs_figure_partial([("f", [715, 815, 1645], [711, 813])]))


def test_k09_missing_duplicate_and_unowned():
    assert fails(C.k09_ids(["a", "b"], ["a"]))
    assert fails(C.k09_ids(["a"], ["a", "a"]))
    assert not fails(C.k09_ids(["a", "b"], ["a", "b"]))
    w = W(); w.unowned = [("m", "shell", 6)]
    assert fails(C.k13_detail_solids(w))
    w.unowned = []
    assert not fails(C.k13_detail_solids(w))


def _furn(rot, built):
    m = {"furn-s": dict(id="furn-s", kind="furniture", level="GF", rotation_deg=rot, size=[2000.0, 800.0, 800.0], placement=[0, 0, 0], params={})}
    w = world_from_boxes({"furn-s": built})
    return w, m


def test_k10_rotation_dropped_fails_and_correct_yaw_is_quiet():
    w, m = _furn(90, (-0.4, -1.0, 0, 0.4, 1.0, 0.8))               # built turned: 0.8 x 2.0
    assert not fails(C.k10_placement(w, m))
    w, m = _furn(90, (-1.0, -0.4, 0, 1.0, 0.4, 0.8))               # rotation dropped: still 2.0 x 0.8
    assert fails(C.k10_placement(w, m))


def test_k11_area_band():
    w = W(); w.mesh_tris["floor-r"] = box_tris((0, 0, 0, 5, 4, 0.0001))[:0]
    from archpipe.parity.geom import fan
    w.mesh_tris["floor-r"] = fan([[0, 0, 0], [5, 0, 0], [5, 4, 0], [0, 4, 0]])
    assert not fails(C.k11_net_area(w, {"r": 20.1}))
    assert fails(C.k11_net_area(w, {"r": 19.0}))


def test_k14_missing_guard_fails_and_k15_mounting():
    m = {"rail-x": dict(id="rail-x", kind="railing", params=dict(kind="guard", guard_height_mm=1100.0))}
    assert fails(C.k14_guards(W(), m))
    assert not fails(C.k14_guards(W(rail_x=(0, 0, 0, 3, 0.02, 1.1)), m))
    assert fails(C.k14_guards(W(rail_x=(0, 0, 0, 3, 0.02, 0.9)), m))


def test_k16_headroom_from_the_pitch_line():
    # a straight flight of 0.176 m risers, 0.28 m goings ascending toward -x, with a slab soffit over its low end
    tr = [box_tris((9.4 - 0.28 * i, 0, -3 + 0.176 * i, 9.4 - 0.28 * i + 0.28, 1, -3 + 0.176 * i + 0.06)) for i in range(17)]
    def world(edge):
        w = W(slab_x=(edge, -1, -0.3, 11, 2, 0))
        w.elements["stair-main"] = Element("stair-main", [("s", "shell", None, None, np.concatenate(tr))])
        return w
    assert fails(C.k16_headroom(world(8.4)))
    assert not fails(C.k16_headroom(world(9.2)))


def test_k09_element_contract_listed_light_only_id_passes_and_unlisted_still_fails():
    model = {"lum-a": dict(id="lum-a", kind="luminaire"), "lum-b": dict(id="lum-b", kind="luminaire"),
             "wall-1": dict(id="wall-1", kind="wall")}
    w = W(wall_1=(0, 0, 0, 1, 1, 1))                          # neither luminaire has a mesh
    contract = {"light_only": {"lum-a": dict(kind="COVE", reason="concealed")}, "imported_props": {}}
    got = C.k09_identity(w, model, contract)
    assert [f.subject for f in fails(got)] == ["lum-b"]       # lum-b is not in the contract: still "built 0 times"
    assert not fails(C.k09_identity(w, model, {"light_only": {"lum-a": {}, "lum-b": {}}}))       # both listed: quiet
    assert [f.subject for f in fails(C.k09_identity(w, model))] == ["lum-a", "lum-b"]            # no contract: as before


def test_k09_element_contract_entry_naming_no_model_element_fails():
    model = {"wall-1": dict(id="wall-1", kind="wall")}
    w = W(wall_1=(0, 0, 0, 1, 1, 1))
    bad = C.k09_identity(w, model, {"imported_props": {"prop-ghost": dict(asset="x.glb")}})
    assert [f.subject for f in fails(bad)] == ["prop-ghost"]
    assert not fails(C.k09_identity(w, model, {"light_only": {}, "imported_props": {}}))
