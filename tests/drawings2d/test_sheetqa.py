import copy
import json
from pathlib import Path

import pytest

from archpipe import model
from archpipe.documents import plans, sheetset
from archpipe.drawings2d import orient, sheetqa, variants


@pytest.fixture(scope="module")
def els():
    return model.load("D1")


@pytest.fixture(scope="module")
def spec(els):
    s = sheetset.build("D1", elements=els, date="2026-11-21")
    s["levels"] = json.loads(Path(model.api.snapshot_path("D1")).read_text())["levels"]
    return s


def _render(els, spec, tmp, no="A-101", level="B", variant="ga"):
    sheet = next(s for s in spec["sheets"] if s["no"] == no)
    out = plans.render_plan(els, spec, sheet, tmp / no, formats=("pdf",), layers=variants.LAYERS[variant])
    return next(p for p in out["plans"] if p["level"] == level), tmp / (no + ".pdf")


def test_correct_plan_has_zero_violations(els, spec, tmp_path):
    rep, pdf = _render(els, spec, tmp_path)
    o = sheetqa.orientation_violations(els, "B", pdf)
    assert o["pairs_checked"] > 100 and o["violations"] == 0
    assert sum(sheetqa.tag_violations(els, rep, pdf).values()) == 0
    assert sum(sheetqa.chain_violations(els, rep).values()) == 0
    assert sum(sheetqa.handing_violations(els, rep).values()) == 0


@pytest.mark.parametrize("name,fn", [("old model-up convention", lambda x, y: (x, y)),
                                     ("mirrored east-west", lambda x, y: (-y, -x)),
                                     ("north-up but flipped", lambda x, y: (y, x))])
def test_orientation_check_catches_wrong_frames(els, spec, tmp_path, monkeypatch, name, fn):
    """The D15/D17 class: a plan in the old +y-up frame, or mirrored, must trip the PDF read-back check."""
    monkeypatch.setattr(orient, "pt", fn)
    rep, pdf = _render(els, spec, tmp_path)
    assert sheetqa.orientation_violations(els, "B", pdf)["violations"] > 20, name


def test_hinge_check_catches_the_real_rotation_defect(els, spec, tmp_path, monkeypatch):
    """Real reproduction: door-B-cinema-store-ramp has rotation 0 on a wall along y. Drawing the opening from its rotation
    (the old behaviour) puts the hinge on the wrong jamb; the check must see it, the host-wall axis must not."""
    def old_frame(e, geo):
        w = plans._wall_of(geo, e.host)
        import math
        horizontal = abs(math.sin(math.radians(e.rotation_deg))) < 0.5
        u = (1.0, 0.0) if horizontal else (0.0, 1.0)
        return u, (-u[1], u[0]), w.params["thickness_mm"] if w else e.size[1]
    monkeypatch.setattr(plans, "_opening_frame", old_frame)
    rep, _ = _render(els, spec, tmp_path)
    assert sheetqa.handing_violations(els, rep)["hinge_off_authored"] >= 1
    assert "door-B-cinema-store-ramp" in sheetqa.opening_axis_findings(els)


def test_all_eight_judgement_doors_flagged(els, spec, tmp_path):
    flagged = set()
    for lv in ("B", "GF"):
        rep, _ = _render(els, spec, tmp_path, "A-101", lv)
        flagged |= set(rep["handing_flags"])
    assert len(flagged) == 8 == sum(1 for e in els if e.kind == "door" and e.params.get("judgement"))


def test_missing_tag_and_chain_corruption_detected(els, spec, tmp_path):
    rep, pdf = _render(els, spec, tmp_path)
    bad = copy.deepcopy(rep)
    bad["dimensions"][0]["segments_mm"][0] += 500
    assert sheetqa.chain_violations(els, bad)["sum_mismatch"] >= 1
    bad2 = copy.deepcopy(rep)
    bad2["handing_flags"] = bad2["handing_flags"][:-1]
    assert sheetqa.handing_violations(els, bad2)["judgement_doors_unflagged"] == 1


def test_view_check_flags_a_mirrored_elevation():
    rep = {"views": [{"name": "N", "kind": "elevation", "u_axis": [0, -1], "stroke_u_range_m": [-31.31, -20.6], "structure_polys": 0}]}
    els = model.load("D1")
    assert sheetqa.view_violations(els, rep)["views_wrong"] == 1                    # mirrored extent (should be 20.6..31.31)
    rep["views"][0]["stroke_u_range_m"] = [20.6, 31.31]
    assert sheetqa.view_violations(els, rep)["views_wrong"] == 0
