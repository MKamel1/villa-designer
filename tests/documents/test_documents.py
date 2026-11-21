import copy
import json

import pytest

from archpipe import model
from archpipe.documents import arabic, crosscheck, names, plans, schedules, sheetset


@pytest.fixture(scope="module")
def els():
    return model.load("D1")


@pytest.fixture(scope="module")
def spec(els):
    s = sheetset.build("D1", elements=els, date="2026-11-20")
    s["levels"] = {"B": {"ffl_revit_mm": -1800}, "GF": {"ffl_revit_mm": 1200}}
    return s


def test_schedule_counts_equal_model(els):
    c = model.counts(els)
    assert len(schedules.door_schedule(els)) == c["door"] == 18
    assert len(schedules.window_schedule(els)) == c["window"] == 8
    assert len(schedules.room_schedule(els)) == c["room"] == 30


def test_tags_unique_and_stable(els):
    t = schedules.tag_numbers(els)
    assert len(set(t.values())) == len(t) == 56
    assert t == schedules.tag_numbers(list(reversed(els)))


def test_csv_md_roundtrip(els):
    rows = schedules.room_schedule(els)
    csv_text = schedules.to_csv(rows)
    assert csv_text.count("\n") == len(rows) + 1
    assert "## Room schedule (30)" in schedules.to_md(rows, "Room schedule")


def test_sheetset_spec_counts_and_missing_fields(spec, els):
    assert spec["schedules"]["door"] == 18
    assert {"A-001", "A-100", "A-101", "A-111", "A-201", "A-301"} <= {s["no"] for s in spec["sheets"]}
    assert {"owner", "engineer", "syndicate_no"} == set(spec["missing_title_block_fields"])  # never invented
    plan = next(s for s in spec["sheets"] if s["no"] == "A-101")
    assert plan["expects"]["B"]["door"] == 10 and plan["expects"]["B"]["exterior_wall"] == 14
    assert all(s["title_ar"] for s in spec["sheets"])
    json.dumps(spec)


def test_every_room_has_arabic_name():
    assert arabic.is_arabic("غرفة")
    assert all(names.room_ar(e.room) for e in model.load("D1") if e.kind == "room")


@pytest.fixture(scope="module")
def reports(els, spec, tmp_path_factory):
    out = tmp_path_factory.mktemp("sheets")
    reps = []
    for s in spec["sheets"]:
        if s["kind"] == "plan" and s["variant"] == "ga":
            for pr in plans.render_plan(els, spec, s, out / s["no"], formats=("pdf",))["plans"]:
                reps.append((pr, out / (s["no"] + ".pdf")))
    return reps


def test_plan_qa_zero_untagged_and_chains(els, reports):
    for rep, pdf in reports:
        q = plans.qa(els, rep, pdf)
        assert q["untagged_doors"] == q["untagged_windows"] == q["untagged_rooms"] == 0
        assert q["pdf_untagged_doors"] == q["pdf_untagged_windows"] == q["pdf_untagged_rooms"] == 0
        assert q["exterior_walls_without_chains"] == 0 and q["exterior_walls"] > 0


def test_plan_qa_detects_missing_tag_and_chain(els, reports):
    rep, pdf = reports[0]
    bad = copy.deepcopy(rep)
    bad["door_tags"].pop()
    bad["dimensions"] = [d for d in bad["dimensions"] if d["owner"] != bad["wall_side"]["N"][0]]
    q = plans.qa(els, bad)
    assert q["untagged_doors"] == 1
    assert q["exterior_walls_without_chains"] >= 1


def test_sc1_pass_and_negative(els, reports):
    reps = [r for r, _ in reports]
    ok = crosscheck.sc1(els, reps)
    assert ok["ok"] and not ok["evaluated"]                 # Revit counts not run: not_evaluated, never pass
    broken = copy.deepcopy(reps)
    broken[0]["room_tags"].pop()
    assert not crosscheck.sc1(els, broken)["ok"]
    assert crosscheck.sc1(els, reps, {"door": 18, "window": 8, "room": 30})["evaluated"]
    assert not crosscheck.sc1(els, reps, {"door": 17, "window": 8, "room": 30})["ok"]
