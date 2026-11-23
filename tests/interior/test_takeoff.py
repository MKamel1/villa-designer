"""Quantity take-off: quantities from geometry, never guessed."""
import json
import math

import pytest

from archpipe.interior.takeoff import Room, load_rooms_elements, load_rooms_readback, takeoff, to_markdown, totals

ROOMS = {"living": Room("living", area_m2=20.0, perimeter_m=18.0, height_m=2.5, openings_m2=6.0),
         "bed": Room("bed", area_m2=12.0, height_m=2.6),
         "bare": Room("bare")}


def row(plan_line):
    return takeoff([plan_line], ROOMS)[0]


def test_floor_area_with_waste():
    r = row({"room": "living", "item": "tile", "unit": "m2", "basis": "floor_area", "waste_pct": 10})
    assert r.qty == 22.0 and r.evidence == "measured"


def test_wall_area_measured_perimeter_minus_openings():
    r = row({"room": "living", "item": "paint", "unit": "m2", "basis": "wall_area"})
    assert r.qty == 18.0 * 2.5 - 6.0 and r.evidence == "measured"


def test_wall_area_estimate_is_labelled_lower_bound():
    r = row({"room": "bed", "item": "paint", "unit": "m2", "basis": "wall_area"})
    assert r.evidence == "estimate"
    assert r.qty == round(4 * math.sqrt(12.0) * 2.6, 2)


def test_wall_area_without_height_is_none():
    r = row({"room": "bare", "item": "paint", "unit": "m2", "basis": "wall_area"})
    assert r.qty is None and "height" in r.note
    r = takeoff([{"room": "living", "item": "p", "unit": "m2", "basis": "wall_area"}],
                {"living": Room("living", area_m2=10.0)})[0]
    assert r.qty is None


def test_missing_room_and_missing_area_are_none_not_zero():
    assert row({"room": "nowhere", "item": "x", "unit": "m2", "basis": "floor_area"}).qty is None
    assert row({"room": "bare", "item": "x", "unit": "m2", "basis": "floor_area"}).qty is None
    assert row({"room": "bed", "item": "x", "unit": "m", "basis": "perimeter"}).qty is None


def test_count_and_fixed_and_bad_basis():
    assert row({"room": "bed", "item": "bed", "unit": "count", "basis": "count", "qty": 2}).qty == 2
    assert row({"room": "bed", "item": "rug", "unit": "m2", "basis": "fixed_m2", "qty": 6.0}).qty == 6.0
    with pytest.raises(ValueError):
        row({"room": "bed", "item": "x", "unit": "m2", "basis": "magic"})


def test_totals_flags_incomplete():
    rows = takeoff([{"room": "living", "item": "tile", "unit": "m2", "basis": "floor_area"},
                    {"room": "bare", "item": "tile", "unit": "m2", "basis": "floor_area"}], ROOMS)
    t = totals(rows)
    assert t["tile"]["qty"] == 20.0 and t["tile"]["incomplete"]
    assert "n/a" in to_markdown(rows)


def test_readback_loader(tmp_path):
    rb = {"options": [{"id": "D1", "rooms": [{"id": "a", "name": "A", "level": "B", "area_m2": 10.0}],
                       "doors": [{"rooms": ["a", "b"], "width": 0.9, "height": 2.1}],
                       "windows": [{"room": "a", "width": 2.0, "height": 1.0}]}]}
    p = tmp_path / "rb.json"
    p.write_text(json.dumps(rb))
    r = load_rooms_readback(p)["a"]
    assert r.area_m2 == 10.0 and r.openings_m2 == round(0.9 * 2.1 + 2.0, 3) and r.height_m is None


def test_elements_loader(tmp_path):
    els = [{"id": "r1", "kind": "room", "level": "B", "params": {"area_m2": 9.0, "perimeter_m": 12.0, "height_m": 2.4}},
           {"id": "w1", "kind": "window", "room": "r1", "size": [1500, 150, 1200]}]
    p = tmp_path / "e.json"
    p.write_text(json.dumps({"elements": els}))
    r = load_rooms_elements(p)["r1"]
    assert r.perimeter_m == 12.0 and r.openings_m2 == pytest.approx(1.8)
    assert r.wall_area() == (round(12.0 * 2.4 - 1.8, 2), "measured perimeter")
