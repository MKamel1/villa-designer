import math
import sys

import numpy as np
import pytest

from archpipe.lightverify import ies, scene_geom as G, v3_sensors as V3


def iso_ies(lm, lamp_lm=1000.0, mult=1.0):
    ang = [float(a) for a in range(0, 181, 5)]
    cd = [lm / (4 * math.pi) / mult] * len(ang)
    return ("IESNA:LM-63-2002\n[TEST] t\nTILT=NONE\n1 %.1f %.3f %d 1 1 2 0 0 0\n1 1 10\n%s\n0\n%s\n"
            % (lamp_lm, mult, len(ang), " ".join(map(str, ang)), " ".join("%.5f" % c for c in cd)))


def test_isotropic_lumens():
    assert ies.lumens(ies.parse(iso_ies(1000))) == pytest.approx(1000, rel=2e-3)


def test_multiplier_applies_and_stated_lamp_lumens_do_not():
    d = ies.parse(iso_ies(500, lamp_lm=9999, mult=2.0))
    assert ies.lumens(d) == pytest.approx(500, rel=2e-3)      # file says 9999 lm per lamp; the candela say 500


def test_hemisphere_only_counts_given_range():
    t = iso_ies(1000).replace("0 5 10", "0 5 10")
    d = ies.parse(t)
    d.gamma = d.gamma[:19]; d.cd = [d.cd[0][:19]]              # 0..90 only
    assert ies.lumens(d) == pytest.approx(500, rel=5e-3)


def test_non_type_c_refuses():
    d = ies.parse(iso_ies(100).replace("1 1 10", "1 1 10"))
    d.ptype = 2
    with pytest.raises(ValueError):
        ies.candela(d, 10, 0)


def test_quadrant_symmetry_expands():
    ang = [0.0, 45.0, 90.0]
    t = ("IESNA:LM-63-2002\nTILT=NONE\n1 1000 1 3 3 1 2 0 0 0\n1 1 10\n0 45 90\n0 45 90\n"
         + "\n".join(" ".join(["100"] * 3) for _ in ang) + "\n")
    d = ies.parse(t)
    assert ies.candela(d, 45, 200) == pytest.approx(100)


# ---------------------------------------------------------------- V3 on synthetic scenes
def box(x0, y0, z0, x1, y1, z1):
    c = np.array([[x, y, z] for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)])
    return G._tris_from_corners(c)


def scene():
    ts = G.TriSet()
    ts.add(box(0, 0, -0.04, 2, 1, 0.0), "table")                     # table top, top face at z=0
    ts.add(box(0.9, 0.4, 0.0, 1.1, 0.6, 0.4), "vase")                # vase standing on it
    ts.add(box(-1, -1, 1.0, 3, 2, 1.05), "ceiling-room")
    ts.add(box(0, 0, 0.30, 0.5, 0.5, 0.31), "shelf")                  # a thin shelf 30 cm above the table
    ts.build()
    return ts


def test_vase_on_sensor_is_flagged():
    assert [k for k, o, _ in V3.point_findings(scene(), 1.0, 0.5, 0.0)] == ["inside"]


def test_clear_point_on_host_surface_is_quiet():
    assert V3.point_findings(scene(), 1.6, 0.5, 0.0) == []


def test_point_just_under_a_shelf_is_flagged_under():
    f = V3.point_findings(scene(), 0.25, 0.25, 0.27)
    assert f and f[0][0] == "under" and f[0][1] == "shelf"


def test_shelf_far_above_is_quiet():
    assert V3.point_findings(scene(), 0.25, 0.25, 0.0) == []


def test_silhouette_graze_is_not_inside():
    assert V3.point_findings(scene(), 0.9, 0.5, 0.0) == []            # exactly on the vase's side face


def test_surface_below_reports_gap():
    gap, owner = scene().surface_below(1.6, 0.5, 0.030)
    assert owner == "table" and gap == pytest.approx(0.030)


def test_plane_check_flags_height_error_only_for_hosted():
    from archpipe.lightcalc.villa import Plane
    ts = scene()
    hosted = Plane("study-desk", "r", ((1.3, 0.1), (1.9, 0.1), (1.9, 0.9), (1.3, 0.9)), 0.030, "c", 400)
    r = V3.check_plane(ts, hosted)
    assert r["hosted"] and r["worst_gap_mm"] == pytest.approx(30, abs=2)
    ok = Plane("study-desk", "r", ((1.3, 0.1), (1.9, 0.1), (1.9, 0.9), (1.3, 0.9)), 0.0, "c", 400)
    assert V3.check_plane(ts, ok)["worst_gap_mm"] < 2


def _cube_scene(tmp_path, model_extra):
    """A 1 m glTF cube asset and a scene.json placing it as a model with the given extra keys."""
    import base64, json, struct
    v = [(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)]
    idx = [0, 1, 3, 0, 3, 2, 4, 6, 7, 4, 7, 5, 0, 4, 5, 0, 5, 1, 2, 3, 7, 2, 7, 6, 0, 2, 6, 0, 6, 4, 1, 5, 7, 1, 7, 3]
    vb = b"".join(struct.pack("<3f", *p) for p in v)
    ib = struct.pack("<36H", *idx)
    uri = "data:application/octet-stream;base64," + base64.b64encode(vb + ib).decode()
    g = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
         "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
         "buffers": [{"uri": uri, "byteLength": len(vb) + len(ib)}],
         "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(vb)},
                         {"buffer": 0, "byteOffset": len(vb), "byteLength": len(ib)}],
         "accessors": [{"bufferView": 0, "componentType": 5126, "count": 8, "type": "VEC3", "min": [0, 0, 0], "max": [1, 1, 1]},
                       {"bufferView": 1, "componentType": 5123, "count": 36, "type": "SCALAR"}]}
    d = tmp_path / "props" / "cube"
    d.mkdir(parents=True)
    (d / "model.gltf").write_text(json.dumps(g))
    spec = {"id": "m1", "asset": "cube", "position": [0, 0, 0], "rotation_deg": [0, 0, 0], "scale": 1.0, **model_extra}
    sc = tmp_path / "scene.json"
    sc.write_text(json.dumps({"meshes": [], "props": [], "models": [spec], "library_root": str(tmp_path)}))
    return G.load_scene(sc)


def test_load_scene_applies_scale_xyz_of_fitted_models(tmp_path):
    ts = _cube_scene(tmp_path, {"furniture_fitting": {"height_m": 0.75}, "scale_xyz": [1.8, 0.7, 0.75]})
    assert np.allclose(ts.T.reshape(-1, 3).max(axis=0) - ts.T.reshape(-1, 3).min(axis=0), [1.8, 0.7, 0.75])


def test_load_scene_ignores_scale_xyz_when_not_fitted(tmp_path):      # negative: the renderer uses the scalar then
    ts = _cube_scene(tmp_path, {"scale_xyz": [1.8, 0.7, 0.75], "scale": 1.0})
    assert np.allclose(ts.T.reshape(-1, 3).max(axis=0) - ts.T.reshape(-1, 3).min(axis=0), [1, 1, 1])
