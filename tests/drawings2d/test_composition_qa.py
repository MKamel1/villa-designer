"""Lead review 2026-11-21: drawings filled ~20 % of the sheet, text too small for print, stair section lacked its detail.
Each new check is proven on the OLD sheets (copied from the first RV2 hand-back into fixtures/) and on the new ones."""
import json
from pathlib import Path

import pytest

from archpipe import model
from archpipe.documents import plans, sheetset
from archpipe.drawings2d import callouts, interior, sheetqa, stairdetail, standard, variants, viewdraw

FX = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def els():
    return model.load("D1")


@pytest.fixture(scope="module")
def spec(els):
    s = sheetset.build("D1", elements=els, date="2026-11-21")
    s["levels"] = json.loads(Path(model.api.snapshot_path("D1")).read_text())["levels"]
    return s


def _room_names(els):
    return [n for e in els if e.kind == "room" for n in {e.params["name"], e.params["name"].split(" (")[0]}]


# ---- fill ratio ----------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("old", ["old-A-112-plan.pdf", "old-A-301-section.pdf", "old-A-201-elevation.pdf"])
def test_fill_check_fails_on_the_old_sheets(old):
    assert sheetqa.fill_ratio(FX / old)["fill"] < 0.40 < sheetqa.MIN_FILL


def test_fill_not_fooled_by_a_stray_legend_in_a_far_corner(tmp_path):
    sh = plans._Sheet(0, 0, 0, 0, paper=standard.PAPERS["A1"])
    sh.text((30, 560), "legend", size=7)
    sh.text((500, 30), "note", size=7)
    sh.fig.savefig(tmp_path / "t.pdf")
    assert sheetqa.fill_ratio(tmp_path / "t.pdf")["fill"] < 0.05


def test_new_plan_sheets_fill_the_area(els, spec, tmp_path):
    for no in ("A-101", "A-111", "A-121", "A-131"):
        s = next(x for x in spec["sheets"] if x["no"] == no)
        plans.render_plan(els, spec, s, tmp_path / no, formats=("pdf",), layers=variants.LAYERS[s["variant"]], extras=variants.extras_for(s["variant"]))
        assert sheetqa.fill_ratio(tmp_path / (no + ".pdf"))["fill"] >= sheetqa.MIN_FILL, no


# ---- printed text height ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("old", ["old-A-112-plan.pdf", "old-A-301-section.pdf"])
def test_text_check_fails_on_the_old_sheets(els, old):
    t = sheetqa.text_violations(FX / old, _room_names(els))
    assert t["min_cap_mm"] < 1.0 and t["text_below_min"] > 40


def test_old_room_names_were_below_the_room_name_minimum(els):
    t = sheetqa.text_violations(FX / "old-A-112-plan.pdf", _room_names(els))
    assert t["room_names_below_min"] >= 5          # bold 5.2 pt = 1.3 mm cap height against 2.5 mm


def test_new_plan_text_meets_the_standard_and_room_names_are_found(els, spec, tmp_path):
    s = next(x for x in spec["sheets"] if x["no"] == "A-111")
    plans.render_plan(els, spec, s, tmp_path / "p", formats=("pdf",), layers=variants.LAYERS["furnished"], extras=variants.extras_for("furnished"))
    t = sheetqa.text_violations(tmp_path / "p.pdf", _room_names(els))
    assert t["text_below_min"] == 0 and t["room_names_below_min"] == 0 and t["room_name_spans"] >= 30
    assert t["min_cap_mm"] >= standard.TEXT_MIN_PT * sheetqa.PT_MM * sheetqa.CAP - 0.02


def test_text_floor_clamps_small_requests(tmp_path):
    sh = plans._Sheet(0, 0, 0, 0)
    sh.text((50, 50), "tiny", size=2.0)
    sh.fig.savefig(tmp_path / "t.pdf")
    assert sheetqa.text_violations(tmp_path / "t.pdf")["text_below_min"] == 0


# ---- stair detail ------------------------------------------------------------------------------------------------------
def test_stair_detail_missing_on_the_old_section(els):
    v = sheetqa.stair_detail_violations(els, FX / "old-A-301-section.pdf", 50.0)
    assert v["bars_missing"] == 15 and v["guards_missing"] == 2 and v["cupboard_walls_missing"] == 3


def _stair_sheet(els, tmp_path, draw: bool):
    sh = plans._Sheet(0, 0, 0, 0, paper=standard.PAPERS["A1"], scale=20.0)
    v = viewdraw.SECTION_1
    P = lambda u, z: (30 + (u - v.window[0]) * 1000 / 20.0, 40 + (z - v.window[1]) * 1000 / 20.0)    # noqa: E731
    assert stairdetail.applies(els, v)
    if draw:
        stairdetail.draw(sh, P, els, v, 20.0, 0.3, 0.2)
    sh.fig.savefig(tmp_path / "s.pdf")
    return sheetqa.stair_detail_violations(els, tmp_path / "s.pdf", 20.0)


def test_stair_detail_counts_match_the_model_when_drawn(els, tmp_path):
    v = _stair_sheet(els, tmp_path, True)
    assert v["bars_found"] == v["bars_expected"] == 15
    assert v["guards_missing"] == v["cupboard_walls_missing"] == 0


def test_stair_detail_check_fails_when_not_drawn(els, tmp_path):
    v = _stair_sheet(els, tmp_path, False)
    assert v["bars_missing"] == 15 and v["guards_missing"] == 2


def test_stair_detail_not_applied_to_sections_away_from_the_stair(els):
    assert not stairdetail.applies(els, viewdraw.SECTION_2)


# ---- parity sheets -----------------------------------------------------------------------------------------------------
def test_interior_elevations_tag_every_opening(els, spec, tmp_path):
    s = next(x for x in spec["sheets"] if x["no"] == "A-211")
    rep = interior.render_interior(els, spec, s, tmp_path / "i", formats=("pdf",))
    v = sheetqa.interior_violations(els, rep, tmp_path / "i.pdf")
    assert v["openings_untagged"] == 0 and v["openings_expected"] == 7 and v["elevations"] == v["elevations_expected"] == 12
    assert sheetqa.fill_ratio(tmp_path / "i.pdf")["fill"] >= sheetqa.MIN_FILL


def test_interior_check_fails_on_a_sheet_without_the_openings(els, spec, tmp_path):
    s = next(x for x in spec["sheets"] if x["no"] == "A-111")
    plans.render_plan(els, spec, s, tmp_path / "x", formats=("pdf",), layers=("furniture",))     # a plan with no door/window tags
    v = sheetqa.interior_violations(els, {"elevations": []}, tmp_path / "x.pdf")
    assert v["openings_untagged"] == v["openings_expected"] and v["elevations"] == 0


def test_yard_wall_sheet_prints_the_model_dimensions(els, spec, tmp_path):
    s = next(x for x in spec["sheets"] if x["no"] == "A-143")
    rep = callouts.render_yard_wall(els, spec, s, tmp_path / "y", formats=("pdf",))
    assert sheetqa.yardwall_violations(els, tmp_path / "y.pdf")["dimensions_missing"] == 0
    assert rep["wall"]["length_mm"] == 3740 and rep["wall"]["height_mm"] == 1400


def test_clearance_zones_follow_the_catalogue_and_stay_quiet_without_clearance(els, spec, tmp_path):
    from archpipe.drawings2d import layers as L, orient
    sh = plans._Sheet(0, 0, 0, 0, paper=standard.PAPERS["A1"], scale=50.0)
    cels = orient.to_client(els)
    n = L.clearance_zones(sh, cels, "GF")
    assert n > 0
    assert L.clearance_zones(sh, [e for e in cels if e.params.get("type") == "bedside_table"], "GF") == 0   # catalogue: no clearance of its own


def test_site_plan_draws_the_grid(els, spec, tmp_path):
    from archpipe.drawings2d import siteplan
    s = next(x for x in spec["sheets"] if x["no"] == "A-100")
    rep = siteplan.render_site(els, spec, s, tmp_path / "s", formats=("pdf",))
    assert len(rep["grid"]["x"]) == 2 and len(rep["grid"]["y"]) == 7
    assert sheetqa.fill_ratio(tmp_path / "s.pdf")["fill"] >= sheetqa.MIN_FILL
