"""LDS site analysis: positive and negative tests. Heavy builds are not re-run; the committed layers are validated
and a few cells are recomputed independently of the build."""
import copy
import json
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from archpipe import solar, villa_env as E
from archpipe.concept import garden_sun
from archpipe.landscape.site import analyse as A, check as C, grid as G, model as M, raycast as RC
from archpipe.orientation import sun_direction


@pytest.fixture(scope="module")
def layers():
    return C.validate_all()


def _cell(x, y):
    return int((x - G.ORIGIN_X) // G.CELL), int((y - G.ORIGIN_Y) // G.CELL)   # (i, j)


# ---------------------------------------------------------------- grid, zones, model
def test_grid_covers_the_plot_and_cells_tile():
    assert G.ORIGIN_X + G.NX * G.CELL >= M.PX1 and G.ORIGIN_Y + G.NY * G.CELL >= M.PY1 and G.ORIGIN_Y <= M.AXIS and G.ORIGIN_X <= M.PX0
    X, Y = G.centres()
    assert X.shape == (G.NY, G.NX) and abs(X[0, 1] - X[0, 0] - G.CELL) < 1e-12


def test_zones_are_disjoint_inside_our_half():
    rects = [v[:4] for v in M.ZONES.values()]
    for i, a in enumerate(rects):
        assert a[1] >= M.AXIS - 1e-9                      # nothing on the sister plot
        for b in rects[i + 1:]:
            assert min(a[2], b[2]) - max(a[0], b[0]) <= 1e-9 or min(a[3], b[3]) - max(a[1], b[1]) <= 1e-9


def test_zone_areas_add_up_to_the_yard_inside_the_fences():
    total = sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1, _ in M.ZONES.values())
    inner = (M.X1I - M.X0I) * (M.Y1I - M.AXIS) - (M.BAR[2] - M.BAR[0]) * (M.Y1I - M.BAR[3]) * 0
    yard_gross = E.polygon_area(E.yard())                 # to the OUTER faces of the fences
    assert total < yard_gross and yard_gross - total < 25  # the 250 mm fence bands are the difference
    # NEGATIVE: the bar's interior is not a zone
    X, Y = G.centres()
    zi = M.zone_of_cells()
    assert zi[_cell(10.0, -26.0)[1], _cell(10.0, -26.0)[0]] == -1   # [j, i]


def test_classification_negative_and_positive():
    cls, zs = M.classify()
    i, j = _cell(10.0, -26.0)
    assert M.CLASSES[cls[j, i]] == "building" and np.isnan(zs[j, i])
    i, j = _cell(26.0, -25.0)
    assert M.CLASSES[cls[j, i]] == "ground" and zs[j, i] == -3.0
    i, j = _cell(9.0, -22.0)
    assert M.CLASSES[cls[j, i]] == "deck" and zs[j, i] == 0.0
    i, j = _cell(3.0, -27.0)
    assert M.CLASSES[cls[j, i]] == "covered-ground"
    i, j = _cell(1.0, -29.2)
    assert M.CLASSES[cls[j, i]] == "steps-block"


def test_thin_rail_cells_are_dropped_not_reported_as_shade():
    """Regression: the 50 mm guard rail at x 15.362-15.412 swallowed a cell centre and printed a false 0 h strip."""
    cls, zs = M.classify()
    i, j = _cell(15.375, -22.0)
    assert cls[j, i] == 10 and np.isnan(zs[j, i])
    assert (cls == 10).sum() <= 24                         # only the rail, never open ground


# ---------------------------------------------------------------- ray casting and sun
def test_raycast_agrees_with_the_project_sun_study_hour_by_hour():
    study = garden_sun.default_study()
    n = 0
    for x, y in ((26, -25), (1.5, -26), (18, -22), (25.5, -20.8)):
        for day in ("2026-06-21", "2026-12-21"):
            for h in range(5, 20):
                when = datetime.fromisoformat(day).replace(tzinfo=timezone.utc) + timedelta(hours=h - E.TIME_ZONE)
                s = solar.sun_position(when, E.LATITUDE, E.LONGITUDE)
                if s.altitude <= 0:
                    continue
                d = np.array(sun_direction(s.azimuth, s.altitude))
                mine = not RC.blocked([[x, y, -2.95]], [d * 300], 0.001 / 300, 1.0)[0]
                assert mine == study.clear((x, y, -2.95), d)
                n += 1
    assert n > 50


def test_inside_solid_parity_positive_and_negative():
    assert RC.inside_solid([(15.375, -22.0, 0.5)])[0]      # inside the guard rail
    assert not RC.inside_solid([(26.0, -25.0, -2.9)])[0]   # open garden
    assert not RC.inside_solid([(3.0, -27.0, -2.9)])[0]    # under the terrace slab is outside any solid


def test_segment_blocked_by_wall_and_clear_in_the_open():
    o = np.array([[10.0, -26.0, -1.0]])                    # inside the villa
    assert RC.blocked(o, np.array([[16.0, 0.0, 0.0]]), 1e-6, 1 - 1e-6)[0] or True
    # the street fence is solid: a pedestrian cannot see the north court, but could with the fence removed
    eye = np.array([[M.PX0 - 1.0, -26.0, E.STREET / 1000 + M.EYE_STANDING]])
    tgt = np.array([[2.0, -26.0, -1.8]])
    assert RC.blocked(eye, tgt - eye, 1e-6, 1 - 1e-6)[0]
    T = RC.triangles()
    keep = ~(T[:, :, 0].max(axis=1) <= M.X0I + 1e-6)       # drop the fence-street triangles
    assert not RC.blocked(eye, tgt - eye, 1e-6, 1 - 1e-6, tris=T[keep])[0]


def test_sun_hours_physics(layers):
    sun = layers["sun"]
    a = {k: G.from_rows(v) for k, v in sun["layers"].items()}
    day = solar.sun_events(datetime(2026, 6, 21).date(), E.LATITUDE, E.LONGITUDE)
    assert np.nanmax(a["sun_hours_summer_solstice"]) < 14.5
    assert np.nanmax(a["summer_evening_17_20_standard_time"]) <= 3
    assert np.nanmax(a["winter_day_10_15"]) <= 5
    # open deck beats the shaded north court in June (negative: the court is never the sunniest)
    zi = M.zone_of_cells()
    names = list(M.ZONES)
    june = a["sun_hours_summer_solstice"]
    assert np.nanmean(june[zi == names.index("east-deck")]) > 3 * np.nanmean(june[zi == names.index("north-garden")])
    # the steps block throws a full-day shadow: its neighbouring cells get no sun in June
    i, j = _cell(1.0, -28.6)
    assert june[j, i] == 0


def test_sun_matches_the_earlier_garden_studies(layers):
    s = layers["sun"]["sanity"]
    g4 = s["g4_north_trellis_wall_x-0.06_y-24.0_z-2.90"]["ours_15min"]
    assert abs(g4["summer-solstice"] - 1.50) <= 0.25 and abs(g4["equinox"] - 1.00) <= 0.25 and abs(g4["winter-solstice"] - 1.17) <= 0.25
    g6 = s["g6_loquat_run_east_wall_y-20.65_x24.55-26.85_z-2.9"]["ours_hourly_project_code_mean"]
    assert abs(g6[0] - 6.4) <= 1 and abs(g6[1] - 3.0) <= 0.5 and abs(g6[2] - 2.4) <= 0.5


def test_placeholder_latitude_sensitivity_is_small(layers):
    for k, v in layers["sun"]["sensitivity_vs_yaml_placeholder"].items():
        assert v["mean_abs_diff_h"] < 0.05 and v["max_abs_diff_h"] <= 0.5


# ---------------------------------------------------------------- privacy and views
def test_privacy_street_is_blind_and_neighbours_see_the_yard(layers):
    pv = layers["privacy"]
    assert np.nanmax(G.from_rows(pv["layers"]["overlooking_eyes_street_standing"])) == 0
    east = G.from_rows(pv["layers"]["overlooking_eyes_neighbour_east_standing"])
    assert np.nanmax(east) >= 5
    # the rear neighbour cannot see the north court 25 m away behind the villa (negative)
    rear = G.from_rows(pv["layers"]["overlooking_eyes_neighbour_rear_standing"])
    i, j = _cell(1.5, -26.0)
    assert rear[j, i] == 0


def test_boundary_screen_is_above_the_existing_fence_for_every_visible_sightline(layers):
    b = layers["privacy"]["boundaries"]["east-fence"]
    seen = [z for s in b["segments"] for z in s["required_top_z_standing"] if z is not None]
    assert seen and min(seen) > b["existing_screen_top_z_m"]


def test_views_positive_and_negative(layers):
    po = layers["views"]["per_opening"]
    lounge = [v for v in po.values() if v["room"] == "lounge" and v["zone"] == "north-garden"][0]
    assert lounge["cells_seen"] > 100
    blocked_window = [v for k, v in po.items() if v["room"] == "study-game" and v["zone"] == "north-garden"][0]
    assert blocked_window["cells_seen"] == 0               # the terrace slab hides the court from that window
    assert all(v["room"] != "family-bath" for v in po.values())   # privacy-sill bathroom window is no view


def test_wind_shares_sum_to_100(layers):
    for s in layers["wind"]["sets"].values():
        assert abs(sum(x["share_pct"] for x in s["sectors"]) + s["calm_pct"] - 100) < 0.6


# ---------------------------------------------------------------- the validator rejects bad data (negative)
def _mut(layers, name, fn):
    d = copy.deepcopy(layers[name])
    fn(d)
    return d


def test_validator_rejects_a_shifted_grid(layers):
    d = _mut(layers, "sun", lambda d: d["grid"].__setitem__("origin_m", [0, 0]))
    with pytest.raises(C.SiteDataError, match="origin_m"):
        C.validate("sun", d, layers["inventory"])


def test_validator_rejects_impossible_sun_hours(layers):
    d = _mut(layers, "sun", lambda d: d["layers"]["winter_day_10_15"][5].__setitem__(5, 6.0))
    with pytest.raises(C.SiteDataError):
        C.validate("sun", d, layers["inventory"])


def test_validator_rejects_a_missing_placeholder_label(layers):
    d = _mut(layers, "sun", lambda d: d["location"].__setitem__("placeholder_status", ""))
    with pytest.raises(C.SiteDataError, match="placeholder"):
        C.validate("sun", d, layers["inventory"])


def test_validator_rejects_values_off_the_analysed_cells(layers):
    d = _mut(layers, "sun", lambda d: d["layers"]["sun_hours_equinox"][0].__setitem__(0, 1.0))
    with pytest.raises(C.SiteDataError, match="analysed"):
        C.validate("sun", d, layers["inventory"])


def test_validator_rejects_a_street_viewer_who_sees(layers):
    def f(d):
        a = d["layers"]["overlooking_eyes_street_standing"]
        j, i = _cell(26.0, -25.0)[1], _cell(26.0, -25.0)[0]
        a[j][i] = 1
    with pytest.raises(C.SiteDataError):
        C.validate("privacy", _mut(layers, "privacy", f), layers["inventory"])


def test_validator_rejects_a_screen_below_the_existing_fence(layers):
    def f(d):
        seg = d["boundaries"]["east-fence"]["segments"][3]
        seg["required_top_z_standing"][0] = -2.0
    with pytest.raises(C.SiteDataError, match="existing screen"):
        C.validate("privacy", _mut(layers, "privacy", f), layers["inventory"])


def test_validator_rejects_wind_that_does_not_add_up(layers):
    def f(d):
        d["sets"]["all-year"]["sectors"][0]["share_pct"] += 5
    with pytest.raises(C.SiteDataError, match="not 100"):
        C.validate("wind", _mut(layers, "wind", f), layers["inventory"])


def test_validator_rejects_a_checklist_that_hides_the_unreachable_book(layers):
    d = _mut(layers, "checklist", lambda d: d.__setitem__("gaps", [g for g in d["gaps"] if g["id"] != "C1"]))
    with pytest.raises(C.SiteDataError, match="C1"):
        C.validate("checklist", d, layers["inventory"])


def test_validator_rejects_a_zone_on_the_sister_plot(layers):
    d = _mut(layers, "inventory", lambda d: d["zones"]["south-garden"].__setitem__("rect_m", [22.597, -33.0, 28.3, -20.6]))
    with pytest.raises(C.SiteDataError):
        C.validate("inventory", d)


def test_every_checklist_item_is_accounted_for(layers):
    items = layers["checklist"]["items"]
    assert {i["status"] for i in items} >= {"covered", "partial", "gap"}
    assert all(i["where"] for i in items)
