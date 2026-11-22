"""L6d (LV open item): the entry-lobby cove is physical in the render scene and the model, not only hidden by orientation.

Before: the strip sat at z 2.73 above the parents' ceiling mesh (2.70, flat) with no upstand, so Cycles' ceiling plane was between the strip and the room
(light blocked) and 'hidden from the pillows' was a property of the aim. Now: a 0.30 m band at 2.70 on the bedroom side with an 80 mm upstand on its
lobby edge, the strip in the coffer above the band and under the 2.80 slab soffit."""
import numpy as np
import pytest

from archpipe.concept import villa_lighting as VL, villa_render as VR
from archpipe.lightcalc import villa as V, villa_checks as VC

ROOM = VL.LOBBY_COVE_ROOM


@pytest.fixture(scope="module")
def scene():
    # geometry only: the furniture/bed receipts are bypassed (they pin the room context, which this lane changes; RA procedure refreshes them)
    from unittest.mock import patch
    with patch("archpipe.concept.furniture_stage2.apply", side_effect=lambda s, *a: s), patch("archpipe.concept.parents_bed.apply", side_effect=lambda s, *a: s):
        return VR.build(views=[])


@pytest.fixture(scope="module")
def cove(scene):
    f = next(f for f in VL.design() if f.kind == "COVE" and f.room == ROOM)
    return f


def _tris(mesh):
    for q in mesh["faces"]:
        for k in range(1, len(q) - 1):
            yield np.array([q[0], q[k], q[k + 1]], float)


def _hits(a, b, tri):
    """Segment a->b crosses the triangle (Moller-Trumbore, both sides)."""
    a, b = np.array(a, float), np.array(b, float)
    d = b - a
    e1, e2 = tri[1] - tri[0], tri[2] - tri[0]
    p = np.cross(d, e2)
    det = e1 @ p
    if abs(det) < 1e-12:
        return False
    t_ = a - tri[0]
    u = (t_ @ p) / det
    q = np.cross(t_, e1)
    v = (d @ q) / det
    t = (e2 @ q) / det
    return u >= 0 and v >= 0 and u + v <= 1 and 0 < t < 1


def _blocked(scene, a, b, prefix="ceiling-"):
    return any(_hits(a, b, tri) for m in scene["meshes"] if m["id"].startswith(prefix) for tri in _tris(m))


def _ends(f, z=None):
    h = f.length / 2
    zz = f.z if z is None else z
    return [(f.x + s * h * f.along[0], f.y + s * h * f.along[1], zz) for s in (-1, 0, 1)]


def test_strip_is_below_the_slab_soffit_and_above_the_band_not_above_a_ceiling(scene, cove):
    band = next(m for m in scene["meshes"] if m["id"] == "ceiling-" + ROOM)
    zs = sorted({round(p[2], 3) for q in band["faces"] for p in q})
    assert zs == [2.70, 2.78], zs                           # the band at 2.70 and its 80 mm upstand
    assert 2.70 < cove.z < VL.COVE_FIELD - 0.02             # in the coffer: above the band, under the 2.80 soffit
    # nothing of the room's ceiling lies above the strip: a vertical ray up from every point of it meets no ceiling mesh
    for p in _ends(cove):
        assert not _blocked(scene, p, (p[0], p[1], VL.COVE_FIELD)), p


def test_the_strips_light_has_a_clear_path_into_the_lobby_over_the_upstand(scene, cove):
    """Along its aim (up and toward the lobby) no ceiling piece is crossed before the slab soffit."""
    aim = np.array(cove.aim, float)
    aim /= np.linalg.norm(aim)
    p = np.array(_ends(cove)[1])
    t = (VL.COVE_FIELD - p[2]) / aim[2]
    assert not _blocked(scene, p, p + aim * t)


def test_the_source_is_hidden_from_both_pillows_by_the_built_band(scene, cove):
    """LA4 lying eyes of the parents' bed: every sight line to the strip (both ends and the middle) crosses the ceiling mesh."""
    v = V.Villa()
    eyes = [s for s in VC.bed_lying_sightlines(v) if s["room"] == "parents-bed"]
    assert len(eyes) == 2
    for s in eyes:
        for p in _ends(cove):
            assert _blocked(scene, s["eye"], p), (s["id"], p)


def test_negative_a_strip_below_the_band_is_seen_from_a_pillow(scene, cove):
    """Guard is not vacuous: the same eyes see the strip if it hangs 0.25 m lower (z 2.48), below the ceiling plane."""
    v = V.Villa()
    eyes = [s for s in VC.bed_lying_sightlines(v) if s["room"] == "parents-bed"]
    assert any(not _blocked(scene, s["eye"], p) for s in eyes for p in _ends(cove, 2.48))


def test_negative_the_old_strip_above_a_flat_ceiling_is_flagged(scene, cove):
    """The old build (flat 2.70 ceiling across the lobby, strip at 2.73): a vertical ray up from the strip IS blocked by the ceiling."""
    flat = {"meshes": [dict(id="ceiling-old", faces=[[[18.0, -28.0, 2.70], [18.0, -26.0, 2.70], [20.0, -26.0, 2.70], [20.0, -28.0, 2.70]]])]}
    p = (_ends(cove)[1][0], _ends(cove)[1][1], 2.73)
    q = (19.0, -27.0, 2.73)
    assert _blocked(flat, (q[0], q[1], 2.73), (q[0], q[1], 2.80))


def test_model_ceiling_of_the_lobby_has_the_band_and_the_raised_field():
    import json
    from pathlib import Path
    els = json.loads((Path(__file__).resolve().parents[2] / "src/archpipe/model/data/d1-elements.json").read_text())["elements"]
    c = next(e for e in els if e["id"] == "ceiling-" + ROOM)
    assert c["params"]["ceiling_kind"] == "cove"
    roles = {z["role"]: z for z in c["params"]["zones"]}
    assert roles["bulkhead band"]["width_mm"] == 300.0 and roles["bulkhead band"]["height_mm"] == 2700.0
    assert roles["raised field"]["height_mm"] == 2800.0
    assert (c["params"]["height_min_mm"], c["params"]["height_max_mm"]) == (2700.0, 2800.0)
    lum = next(e for e in els if e["id"] == "lum-COVE-%s-01" % ROOM)
    assert 2700.0 < lum["placement"][2] < 2800.0                    # the strip is in the coffer
