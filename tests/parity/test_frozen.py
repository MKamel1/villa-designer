"""The frozen historic reproductions: every row must give the result it is expected to give."""
import pytest

from archpipe.parity import frozen as F


@pytest.fixture(scope="module")
def rows():
    return F.run_all()


def test_every_reproduction_row_gives_its_expected_result(rows):
    bad = [(r["row"], r["source"], r.get("option") or r.get("subject"), r["expect"], r["got"]) for r in rows if not r["ok"]]
    assert not bad, bad


def test_d01_every_revit_intersection_is_found(rows):
    d01 = [r for r in rows if r["row"] == "D01"]
    assert len(d01) == 6 and all(not r["missed"] for r in d01) and d01[0]["caught"] == 33


def test_d02_is_caught_on_exact_geometry_and_not_at_scene_resolution(rows):
    r = next(r for r in rows if r["row"] == "D02")
    assert r["got"] == "fail" and "not seen" in r["scene_resolution"]


def test_d16_reproduces_the_learnings_numbers(rows):
    r8 = next(r for r in rows if r["row"] == "D16" and "8.537" in r["subject"])
    fixed = next(r for r in rows if r["row"] == "D16" and "8.887" in r["subject"])
    assert "1818 mm" in r8["detail"] and "2045 mm" in fixed["detail"]
