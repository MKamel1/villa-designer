import pytest

from archpipe import model
from archpipe.documents import schedules
from archpipe.drawings2d import callouts, orient, siteplan


@pytest.fixture(scope="module")
def els():
    return model.load("D1")


def test_door_schedule_carries_handing_and_confirm_flags(els):
    rows = schedules.door_schedule(els)
    hinged = [r for r in rows if r["operation"] == "hinged"]
    assert len(hinged) == 12 and all(r["handing"] in ("LH", "RH") and r["hinge_side"] for r in hinged)  # +1 hinged door: corridor-suite-vestibule, client FINAL 2026-11-26
    assert sum(1 for r in rows if r["to_confirm"] == "YES") == 8            # lane M's 8 judgement calls


def test_schedules_cover_model(els):
    assert len(schedules.finish_schedule(els)) == 31  # +1: suite-vestibule, client FINAL 2026-11-26
    assert len(schedules.furniture_schedule(els)) == sum(1 for e in els if e.kind == "furniture" and e.params.get("type") != "dressing")
    lum = schedules.luminaire_schedule(els)
    assert sum(r["count_B"] + r["count_GF"] for r in lum) == 137 == sum(1 for e in els if e.kind == "luminaire")
    bad = [e for e in els if e.kind == "luminaire"][:1]
    assert schedules.luminaire_schedule(bad)[0]["count_B"] + schedules.luminaire_schedule(bad)[0]["count_GF"] == 1   # negative: no cross-count


def test_setbacks_in_client_compass(els):
    sb = siteplan.setbacks(els)
    assert sb["N"] == pytest.approx(3.99, abs=0.05)        # street side: fence 3.74 m + 0.25 to the GF terrace
    assert sb["S"] > sb["N"] and sb["W"] > sb["E"]          # rear garden deeper than the street strip; sister side wider


def test_callout_panels_inside_stair_rooms(els):
    cels = orient.to_client(els)
    for p in callouts.panels_for("stair", cels) + callouts.panels_for("wet", cels):
        x0, y0, x1, y1 = p["crop"]
        assert x1 > x0 and y1 > y0 and (x1 - x0) < 6000
