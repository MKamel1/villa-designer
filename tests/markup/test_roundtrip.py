"""The plan's equivalence test on real D1 sheets: marks -> request records -> element ids -> decide/close -> revised sheet."""
import shutil

import pytest

from archpipe.markup import frames as F, ingest, link, revise, store
from archpipe.markup.__main__ import main
from .helpers import mark, fitz, red_rects

LUM_ISO = "lum-DL-lounge-01"


def _el(els, i):
    return next(e for e in els if e.id == i)


def _marked(sheets, tmp_path, frames_data, items):
    """items: (sheet no, level, x, y, text, kwargs)."""
    out = []
    for no, level, x, y, text, kw in items:
        src = sheets / ("%s-plan.pdf" % no)
        dst = tmp_path / ("%s-%d-plan.pdf" % (no, len(out)))
        out.append(mark(src, dst, frames_data, no, level, x, y, text, **kw))
    return out


def test_door_luminaire_ambiguous_and_empty(els, sheets, frames_data, tmp_path, root):
    door = _el(els, "door-GF-corridor-kids-a")
    lum = _el(els, "lum-WALL-READ-parents-bed-02")
    lum2 = _el(els, "lum-VSTRIP-parents-dressing-03")
    mid = ((lum.placement[0] + lum2.placement[0]) / 2, (lum.placement[1] + lum2.placement[1]) / 2)
    pdfs = _marked(sheets, tmp_path, frames_data, [
        ("A-111", "GF", door.placement[0] + 40, door.placement[1] + 30, "door too narrow", {}),
        ("A-121", "GF", mid[0], mid[1], "move this light", {}),
        ("A-121", "GF", 14000, 2000, "what is this empty area?", {}),          # east of the GF building: no room, no wall
    ])
    got = []
    for p in pdfs:
        got += ingest.from_pdf(p, els, root, frames_data)
    d, a, m = (g[0] for g in got)
    assert d["link_status"] == "linked" and d["links"][0]["element_id"] == door.id and d["links"][0]["distance_mm"] == 0.0
    assert d["text"] == "door too narrow" and d["author"] == "Client" and d["source"]["hash"] and d["status"] == "open"
    assert a["link_status"] == "ambiguous" and a["links"] == []
    assert {x["element_id"] for x in a["alternatives"]} >= {lum.id, lum2.id}    # every candidate within tolerance is listed
    assert m["link_status"] == "miss" and m["links"] == []
    # re-ingest is idempotent (same source hash)
    again = ingest.from_pdf(pdfs[0], els, root, frames_data)
    assert [g[1] for g in again] == [False] and len(store.all_requests(root)) == 3

    # decide / close: silence is not approval
    with pytest.raises(store.StoreError):
        store.close(d["id"], "abc1234", root=root)            # still open
    with pytest.raises(store.StoreError):
        store.decide(d["id"], "accept", "  ", root=root)      # no reason
    store.decide(d["id"], "accept", "widen to 900 per brief", root=root)
    with pytest.raises(store.StoreError):
        store.close(a["id"], "abc1234", root=root)            # never decided
    store.decide(a["id"], "accept", "yes", root=root)
    with pytest.raises(store.StoreError):
        store.close(a["id"], "abc1234", root=root)            # ambiguous: no element named
    closed = store.close(a["id"], "feedbee", [lum.id], {e.id for e in els}, root=root)
    assert closed["links"][0]["tier"] == "resolved-by-lead"
    store.decide(m["id"], "reject", "not a design change", root=root)
    with pytest.raises(store.StoreError):
        store.close(m["id"], "abc1234", root=root)             # rejected is final
    store.close(d["id"], "abc1234def", root=root)

    # revised sheets: copy, cloud round the right element, table row
    for no, expect_el in (("A-111", door), ("A-121", lum)):
        src = sheets / ("%s-plan.pdf" % no)
        out = revise.revise_pdf(src, els, root, tmp_path / ("%s-rev.pdf" % no), frames_data)
        assert out != src and src.read_bytes() != out.read_bytes()
        doc = fitz.open(str(out))
        txt = doc[0].get_text()
        assert "REV A" in txt and ("abc1234def" in txt if no == "A-111" else "feedbee" in txt)
        # the cloud is vector drawing: its bbox must surround the element's mapped footprint
        fr = frames_data["sheets"][no]
        p = next(q for q in fr["panels"] if q["level"] == "GF")
        bx = link.bbox_model(expect_el)
        c = F.model_to_page(fr, p, (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2)
        assert any(r.contains(fitz.Point(*c)) for r in red_rects(doc[0]))
        doc.close()
    # one doc table row text
    assert "door too narrow" in fitz.open(str(tmp_path / "A-111-rev.pdf"))[0].get_text()


def test_cloud_follows_a_moved_element(els, sheets, frames_data, tmp_path, root):
    import dataclasses
    lum = _el(els, LUM_ISO)
    pdf = _marked(sheets, tmp_path, frames_data, [("A-121", lum.level, lum.placement[0], lum.placement[1], "move this light", {})])[0]
    (rec, _), = ingest.from_pdf(pdf, els, root, frames_data)
    assert rec["links"][0]["element_id"] == LUM_ISO
    store.decide(rec["id"], "accept", "yes", root=root)
    store.close(rec["id"], "c0ffee1", root=root)
    moved = [dataclasses.replace(e, placement=(e.placement[0] - 1500, e.placement[1], e.placement[2])) if e.id == LUM_ISO else e for e in els]
    cen = {}
    for tag, e_list in (("old", els), ("new", moved)):
        out = revise.revise_pdf(sheets / "A-121-plan.pdf", e_list, root, tmp_path / ("m-%s.pdf" % tag), frames_data)
        d = fitz.open(str(out))[0]
        r = red_rects(d)
        cen[tag] = (sum(q.x0 + q.x1 for q in r) / 2 / len(r), sum(q.y0 + q.y1 for q in r) / 2 / len(r))
    # model -x is north is up the sheet: moving 1500 mm to -x moves the cloud up by 30 mm of paper at 1:50
    assert cen["old"][0] == pytest.approx(cen["new"][0], abs=1) and cen["old"][1] - cen["new"][1] == pytest.approx(1500 / 50 * F.PT_PER_MM, abs=1.5)


def test_cli_exit_codes(els, sheets, frames_data, tmp_path, root, capsys, monkeypatch):
    assert main(["--root", str(root), "ingest", str(tmp_path / "nope.pdf")]) == 2
    assert main(["--root", str(root), "decide", "MK-999", "accept", "--reason", "x"]) == 2
    assert main(["--root", str(root), "revise", str(tmp_path / "nope.pdf")]) == 2
    csvp = tmp_path / "c.csv"
    csvp.write_text("sheet,text,author,date\nA-111,missing position,me,2026-11-21\n")
    assert main(["--root", str(root), "ingest", str(csvp)]) == 2
    csvp.write_text("sheet,element,text,author,date\nA-111,door-GF-corridor-kids-a,door too narrow,lead,2026-11-21\nA-111,door-nope,x,lead,2026-11-21\n")
    assert main(["--root", str(root), "ingest", str(csvp)]) == 0
    recs = store.all_requests(root)
    assert [r["link_status"] for r in recs] == ["linked", "miss"] and recs[0]["links"][0]["tier"] == "named"
    assert main(["--root", str(root), "list"]) == 0
    assert main(["--root", str(root), "decide", "MK-001", "accept", "--reason", "ok"]) == 0
    assert main(["--root", str(root), "close", "MK-001", "--commit", "abc1234"]) == 0
    assert store.get("MK-001", root)["status"] == "closed"


def test_csv_position_on_sheet_mm(els, sheets, frames_data, root):
    """Sheet-mm export (origin lower-left): a pick at the door's own sheet position links the door."""
    door = _el(els, "door-GF-corridor-kids-a")
    fr = frames_data["sheets"]["A-111"]
    p = next(q for q in fr["panels"] if q["level"] == "GF")
    X, Y = F.model_to_page(fr, p, *door.placement[:2])
    rows = [{"sheet": "A-111", "x_mm": X / F.PT_PER_MM, "y_mm": (fr["paper_mm"][1] - Y / F.PT_PER_MM), "text": "door too narrow", "author": "c", "date": "2026-11-21"}]
    r = ingest.resolve(els, fr, X, Y)
    assert r["links"][0]["element_id"] == door.id
