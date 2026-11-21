"""Negative and orientation tests: title block links to nothing; mirrored/rotated frames are caught; north is model -x."""
import copy

import pytest

from archpipe.drawings2d import orient
from archpipe.markup import frames as F, ingest, link, store
from .helpers import mark, fitz


def test_title_block_mark_links_to_nothing(els, sheets, frames_data, tmp_path, root):
    fr = frames_data["sheets"]["A-111"]
    doc = fitz.open(str(sheets / "A-111-plan.pdf"))
    pg = doc[0]
    a = pg.add_text_annot(fitz.Point(pg.rect.width - 60, 120), "wrong project name")
    a.set_info(content="wrong project name", title="c")
    a.update()
    doc.save(str(tmp_path / "A-111-tb.pdf"))
    (rec, _), = ingest.from_pdf(tmp_path / "A-111-tb.pdf", els, root, frames_data)
    assert rec["link_status"] == "miss" and rec["links"] == [] and rec["model_point"] is None
    assert "title block" in rec["link_reason"]


def test_mirrored_and_rotated_frames_are_caught(els, sheets, frames_data):
    pdf = sheets / "A-111-plan.pdf"
    fr = frames_data["sheets"]["A-111"]
    assert F.verify(fr, pdf, els)["verified"]
    for name, bad in (("mirrored east-west", lambda x, y: (-y, -x)),          # D17: mirrored plan
                      ("rotated 180", lambda x, y: (-y, x)),
                      ("old north (+y up)", lambda x, y: (x, y))):
        with pytest.raises(F.FrameError, match="does not match"):
            F.verify(fr, pdf, els, to_client=bad)


def test_ingest_refuses_a_frame_that_no_longer_matches_the_sheet(els, sheets, frames_data, tmp_path, root):
    shifted = copy.deepcopy(frames_data)
    for p in shifted["sheets"]["A-111"]["panels"]:
        p["ox"] += 120.0
    pdf = mark(sheets / "A-111-plan.pdf", tmp_path / "A-111-x.pdf", frames_data, "A-111", "GF", 20000, 2000, "x")
    with pytest.raises(ingest.IngestError, match="does not match"):
        ingest.from_pdf(pdf, els, root, shifted)


def test_rotated_page_refused(els, sheets, frames_data, tmp_path, root):
    pdf = mark(sheets / "A-111-plan.pdf", tmp_path / "A-111-r.pdf", frames_data, "A-111", "GF", 20000, 2000, "x")
    d = fitz.open(str(pdf))
    d[0].set_rotation(90)
    d.save(str(tmp_path / "A-111-rot.pdf"))
    with pytest.raises(ingest.IngestError, match="rotated"):
        ingest.from_pdf(tmp_path / "A-111-rot.pdf", els, root, frames_data)


def test_north_mark_maps_to_model_minus_x(els, sheets, frames_data):
    """A mark on the NORTH (street, top) side of the plan is at lower model x than one on the south side; east is +y."""
    fr = frames_data["sheets"]["A-111"]
    p = next(q for q in fr["panels"] if q["level"] == "GF")
    cx = (p["bbox_client_mm"][0] + p["bbox_client_mm"][2]) / 2
    top = F.model_to_page_client(fr, p, cx, p["bbox_client_mm"][3] - 500)         # near the top of the drawn plan
    bot = F.model_to_page_client(fr, p, cx, p["bbox_client_mm"][1] + 500)
    mt = F.page_to_model(fr, p, *top)
    mb = F.page_to_model(fr, p, *bot)
    assert top[1] < bot[1]                      # PDF y grows downward: top is visually higher
    assert mt[0] < mb[0]                        # north = model -x
    right = F.page_to_model(fr, p, top[0] + 100, top[1])
    assert right[1] > mt[1]                     # to the right on the sheet = east = model +y
    assert orient.compass_of_model_vector(-1, 0) == "N"
    # and on the real sheet: the street-most room tag sits above the rear-most one
    from archpipe.documents import schedules
    from archpipe.drawings2d import sheetqa
    tags, pos = schedules.tag_numbers(els), sheetqa.pdf_tag_positions(sheets / "A-111-plan.pdf")
    gf = sorted((e for e in els if e.kind == "room" and e.level == "GF"), key=lambda e: e.placement[0])
    assert pos[tags[gf[0].id]][1] < pos[tags[gf[-1].id]][1]


def test_area_mark_lists_what_it_encloses(els):
    fr = {"layers": ["luminaires"]}
    lum = [e for e in els if e.kind == "luminaire" and e.level == "GF"][:2]
    pts = [e.placement[:2] for e in lum]
    ring = [(min(p[0] for p in pts) - 300, min(p[1] for p in pts) - 300), (max(p[0] for p in pts) + 300, min(p[1] for p in pts) - 300),
            (max(p[0] for p in pts) + 300, max(p[1] for p in pts) + 300), (min(p[0] for p in pts) - 300, max(p[1] for p in pts) + 300)]
    r = link.hit_area(els, "GF", ring, 50.0, fr["layers"])
    assert r and {x["element_id"] for x in r["alternatives"] if x["kind"] == "luminaire"} >= {lum[0].id, lum[1].id} or r["status"] == "linked"
    assert link.hit_area(els, "GF", [(0, 0), (1, 0), (1, 0)], 50.0, ["luminaires"]) is None      # degenerate ring


def test_empty_space_inside_the_plan_extent_is_a_miss(els, frames_data):
    """Inside the drawn plan's bounding box but outside every room/wall: a miss with a reason, not a guess."""
    from archpipe.markup import ingest
    fr = frames_data["sheets"]["A-111"]
    p = next(q for q in fr["panels"] if q["level"] == "GF")
    bb = p["bbox_client_mm"]
    # east end of the GF plan's south-west corner region (client frame) is outside the L-shaped footprint
    for fx, fy in ((0.97, 0.03), (0.03, 0.03), (0.03, 0.97), (0.97, 0.97), (0.5, 0.5)):
        cx, cy = bb[0] + fx * (bb[2] - bb[0]), bb[1] + fy * (bb[3] - bb[1])
        X, Y = F.model_to_page_client(fr, p, cx, cy)
        r = ingest.resolve(els, fr, X, Y)
        if r["link_status"] == "miss" and r["model_point"]:
            assert "empty space" in r["reason"] and r["links"] == []
            return
    pytest.fail("no empty corner found in the plan bbox to test with")
