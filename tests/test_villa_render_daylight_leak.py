"""RF defect 9 guard: a view of a windowless room may not carry a measurable share of daylight.

The frozen exposure record holds, per view, the lamps-only and daylight-only luminance of the same mask. The east hall
(n10, L9P draft) reads 35 % daylight; its lamps-off render is evenly blue. A ray probe from the hall (20 000 directions
per origin, shell and context without glazing) is closed everywhere except the hall's WEST end (36 of 20 000 rays escape
from x 12.5 m, none from x >= 15 m): the daylight arrives down the hall from the open plan. The group's white balance is
its lamps' 2700 K (pre-registered rule), so that daylight reads blue (B/R 1.27 on the plaster). Not a geometry leak.
"""
import json
from pathlib import Path

import pytest

RECORD = Path(__file__).resolve().parents[1] / "knowledge/render-set/exposure-groups.json"
WINDOWLESS = ["n10-gf-hall-east-day", "v30-under-ramp-store", "n05-pantry-evening", "v08-cinema"]
MAX_DAYLIGHT_FRACTION = 0.10      # ASSUMED policy: leakage below 10 % of the metered luminance is not a visible cast


def daylight_fraction(measure):
    total = measure["lamp_luminance_sum"] + measure["daylight_luminance_sum"]
    return measure["daylight_luminance_sum"] / total if total else 0.0


def test_fraction_arithmetic():                                    # positive and negative controls on synthetic rows
    assert daylight_fraction({"lamp_luminance_sum": 65, "daylight_luminance_sum": 35}) == pytest.approx(0.35)
    assert daylight_fraction({"lamp_luminance_sum": 100, "daylight_luminance_sum": 0}) == 0.0


@pytest.mark.parametrize("view", [v for v in WINDOWLESS if v != "n10-gf-hall-east-day"])
def test_windowless_views_are_lamp_lit(view):
    m = json.loads(RECORD.read_text())["measurements"][view]
    assert daylight_fraction(m) <= MAX_DAYLIGHT_FRACTION


def test_east_hall_has_no_daylight_leak():
    m = json.loads(RECORD.read_text())["measurements"]["n10-gf-hall-east-day"]
    assert daylight_fraction(m) <= MAX_DAYLIGHT_FRACTION
