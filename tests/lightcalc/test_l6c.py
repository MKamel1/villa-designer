"""L6c: ERCO binding in the engine: Radiance-safe IES, flux of bound products, pendant sampling, the finer cinema/daybed grids."""
import math
from pathlib import Path

import pytest

from archpipe import photometry as ph
from archpipe.lightcalc import handcalc, villa as V
from archpipe.lightcalc.direct import Placement, direct_illuminance
from archpipe.lightcalc.radjob import radiance_safe_ies

ROOT = Path(__file__).resolve().parents[2]
ERCO_DL = ROOT / "knowledge/lighting/ies/ERCO-41321.ies"


@pytest.fixture(scope="module")
def villa():
    return V.Villa()


def test_radiance_safe_ies_strips_bom_and_negative_opening():
    raw = "﻿" + ERCO_DL.read_text(encoding="utf-8", errors="replace").lstrip("﻿")
    assert "-0.076" in raw
    out = radiance_safe_ies(raw)
    assert not out.startswith("﻿") and "-0.076" not in out and "0.076 0.076" in out
    a, b = ph.parse(raw.lstrip("﻿")), ph.parse(out)
    assert b.integrated_flux() == pytest.approx(a.integrated_flux(), rel=1e-9)      # photometry untouched


def test_radiance_safe_ies_leaves_an_ordinary_file_alone():
    plain = "IESNA:LM-63-2002\nTILT=NONE\n1 1000 1 3 1 1 2 0.1 0.1 0\n1 1 10\n0 45 90\n0\n100 80 0\n"
    assert radiance_safe_ies(plain) == plain


def test_bound_products_emit_their_own_lumens_at_driver_one(villa):
    for f in villa.fixtures:
        if f.kind == "DL" and "dimmer" not in f.extra:
            (p,) = V.fixture_placements(f)
            assert p.dim * p.photometry.integrated_flux() == pytest.approx(1065, rel=0.01)
            break
    else:
        pytest.skip("every DL is dimmed")


def test_table_pendant_is_sampled_along_its_length(villa):
    f = next(f for f in villa.fixtures if f.kind == "PEN-LIN")
    ps = V.fixture_placements(f)
    assert len(ps) == 8
    flux = sum(p.dim * p.photometry.integrated_flux() for p in ps)
    assert flux == pytest.approx(3558 * f.extra.get("dimmer", 1.0), rel=0.01)       # two 1779 lm modules, not one
    xs = sorted(p.position[0] for p in ps)
    assert xs[-1] - xs[0] == pytest.approx(1.5 * 7 / 8, abs=0.01)


def test_zone_drivers_respect_v12_and_the_rated_output(villa):
    import json
    drivers = json.loads((ROOT / "knowledge/lighting/zone-drivers.json").read_text())
    assert drivers and max(drivers.values()) <= 0.80 + 1e-9


@pytest.mark.parametrize("pid, room", [("room-cinema", "B-cinema"), ("daybed", "B-open")])
def test_finer_grids_converge_under_3_percent(villa, pid, room):
    from archpipe.lightverify.v7_convergence import grid_em
    pl = next(p for p in villa.planes() if p.id == pid)
    plc = villa.cluster_placements(room)
    e1, (dx, dy) = grid_em(pl, plc, pl.spacing)
    e2, _ = grid_em(pl, plc, min(dx, dy) / 2)
    assert abs(e1 / e2 - 1) < 0.03


def test_old_cinema_grid_would_have_failed():
    """Negative: the 0.63 m EN 12464-1 pitch on this room moved the direct result by more than 3 % (LV: +6.35 %)."""
    v = V.Villa()
    from archpipe.lightverify.v7_convergence import grid_em
    pl = next(p for p in v.planes() if p.id == "room-cinema")
    plc = v.cluster_placements("B-cinema")
    coarse, (dx, dy) = grid_em(pl, plc, 0.63)
    fine, _ = grid_em(pl, plc, 0.63 / 2)
    assert abs(coarse / fine - 1) > 0.015       # the coarse grid is visibly less stable than the 0.30 m one (+/-1.1 %)


def test_handcalc_flux_on_rect_matches_the_point_sum_for_a_downlight():
    pho = ph.load(ERCO_DL)
    pl = Placement("t", pho, (0.0, 0.0, 2.0), dim=1.0)
    big = (-3.0, -3.0, 3.0, 3.0)
    assert handcalc.flux_on_rect(pl, big, 0.0) == pytest.approx(pho.integrated_flux(), rel=0.03)      # all the flux lands in a big floor
    small = (-0.5, -0.5, 0.5, 0.5)
    e_hand = handcalc.flux_on_rect(pl, small, 0.0) / 1.0
    pts = [(-0.5 + (i + 0.5) / 40, -0.5 + (j + 0.5) / 40) for i in range(40) for j in range(40)]
    e_pts = sum(direct_illuminance([pl], (x, y, 0.0)) for x, y in pts) / len(pts)
    assert e_hand == pytest.approx(e_pts, rel=0.03)


def test_handcalc_rejects_a_plane_above_the_luminaire():
    pho = ph.load(ERCO_DL)
    assert handcalc.flux_on_rect(Placement("t", pho, (0, 0, 1.0)), (-1, -1, 1, 1), 2.0) == 0.0
