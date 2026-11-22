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


def _indirect_path(scene, strip_pt, floor_pt, field):
    """Light from the strip reaches `floor_pt` by one bounce off the slab soffit: some soffit point P in `field` (x0, y0, x1, y1) with strip->P and
    P->floor both clear of every ceiling mesh."""
    x0, y0, x1, y1 = field
    for i in range(9):
        for j in range(9):
            P = (x0 + (x1 - x0) * (i + .5) / 9, y0 + (y1 - y0) * (j + .5) / 9, VL.COVE_FIELD)
            if not _blocked(scene, strip_pt, P) and not _blocked(scene, P, floor_pt):
                return P
    return None


def _lobby_rects():
    from archpipe.concept import villa_furnish as F, villa_r11 as R
    x0, y0, x1, y1 = F.clear_rect(R.design("D1"), ROOM)
    return (x0, y0, x1, y1), (x0, y0, x1, y1 - VL.LOBBY_COVE_DEPTH)


def test_strip_is_below_the_slab_soffit_and_stands_on_the_band(scene, cove):
    band = next(m for m in scene["meshes"] if m["id"] == "ceiling-" + ROOM)
    zs = sorted({round(p[2], 3) for q in band["faces"] for p in q})
    assert zs[0] == 2.70 and zs[-1] == round(2.70 + VL.LOBBY_COVE_UPSTAND, 3) and set(zs) <= {2.70, 2.701, zs[-1]}, zs     # band + its upstand (+ 1 mm sheet)
    trough = next(m for m in scene["meshes"] if m["id"] == "ceiling-" + ROOM + "-trough")      # the closed trough's back wall, band to soffit
    assert sorted({round(p[2], 3) for q in trough["faces"] for p in q}) == [2.70, VL.COVE_FIELD]
    assert cove.lm == pytest.approx(VL.LOBBY_COVE_LM_PER_M * cove.length)
    assert 2.70 < cove.z < VL.COVE_FIELD - 0.05             # in the coffer: above the band, under the 2.80 soffit
    assert cove.z < 2.70 + VL.LOBBY_COVE_UPSTAND            # below the upstand's top: not visible over it from the lobby
    lobby, field = _lobby_rects()
    for p in _ends(cove):
        assert lobby[1] + VL.LOBBY_COVE_DEPTH - 1e-6 <= p[1]    # on the band, not over the open field
        assert not _blocked(scene, p, (p[0], p[1], VL.COVE_FIELD)), p      # nothing above it up to the soffit


def test_the_strips_light_reaches_the_lobby_floor_by_bouncing_off_the_soffit(scene, cove):
    """The Cycles failure class: with the strip above a flat ceiling the light has no path into the room."""
    lobby, field = _lobby_rects()
    floor = ((lobby[0] + lobby[2]) / 2, (field[1] + field[3]) / 2, 0.0)
    for p in _ends(cove):
        assert _indirect_path(scene, p, floor, field) is not None, p


def test_negative_the_old_flat_ceiling_over_the_strip_leaves_no_path(scene, cove):
    """The old build: a flat 2.70 ceiling across the whole lobby, the strip at 2.73 above it: no path from the strip to the lobby floor."""
    lobby, field = _lobby_rects()
    x0, y0, x1, y1 = lobby
    flat = {"meshes": [dict(id="ceiling-old", faces=[[[x0, y0, 2.70], [x0, y1, 2.70], [x1, y1, 2.70], [x1, y0, 2.70]]])]}
    floor = ((x0 + x1) / 2, (field[1] + field[3]) / 2, 0.0)
    strip_pt = (cove.x, y1 - 0.10, 2.73)
    assert _indirect_path(flat, strip_pt, floor, field) is None


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
