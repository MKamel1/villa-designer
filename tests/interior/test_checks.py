"""I1-I4 style checks: each rule has a positive and a negative case."""
import pytest

from archpipe.contracts import CheckResult
from archpipe.interior import (Concept, MaterialDef, PaletteColour, check_i1, check_i2, check_i3, check_i4,
                               load_placed, run_checks)


def concept(**kw) -> Concept:
    base = dict(
        name="Test", statement="s",
        palette=[PaletteColour("chalk", "ceiling", 85), PaletteColour("sand", "wall", 55),
                 PaletteColour("terracotta tile", "floor", 25), PaletteColour("indigo", "accent", 8)],
        materials=[MaterialDef("oak", "wood"), MaterialDef("travertine", "stone"), MaterialDef("brass", "metal"),
                   MaterialDef("linen", "textile")],
        banned=["zig-zag", "grey-green"])
    base.update(kw)
    return Concept(**base)


def by_subject(results, subject):
    return next(r for r in results if r.subject == subject)


# I2 ------------------------------------------------------------------------
def test_i2_pass_all_lrv():
    r = check_i2(concept(), None)
    assert r[0].status == "pass" and r[0].achieved == 4
    assert r[1].status == "not_evaluated"            # no calc inputs: never a pass


def test_i2_fail_missing_lrv():
    c = concept()
    c.palette.append(PaletteColour("mystery", "accent", None))
    r = check_i2(c)[0]
    assert r.status == "fail" and "mystery" in r.message


def test_i2_fail_lrv_out_of_range():
    c = concept()
    c.palette[0].lrv = 140
    assert check_i2(c)[0].status == "fail"


def test_i2_bands_pass_and_fail():
    ok = check_i2(concept(), {"ceiling": 0.80, "wall": 50, "floor": 20})
    assert all(r.status == "pass" for r in ok[1:])
    bad = check_i2(concept(), {"ceiling": 0.65 * 0.5, "wall": 50, "floor": 20})   # 32.5 vs 85
    assert by_subject(bad, "Test/ceiling").status == "fail"
    assert by_subject(bad, "Test/wall").status == "pass"


def test_i2_band_role_without_palette_colour_fails():
    c = concept(palette=[PaletteColour("chalk", "ceiling", 85)])
    r = check_i2(c, {"ceiling": 80, "wall": 50, "floor": 20})
    assert by_subject(r, "Test/wall").status == "fail"


def test_i2_empty_palette_not_evaluated():
    assert check_i2(concept(palette=[]))[0].status == "not_evaluated"


# I3 ------------------------------------------------------------------------
def placed_ok():
    return {"living": [{"id": "s1", "name": "sofa", "category": "sofa", "materials": ["oak", "linen"]},
                       {"id": "t1", "name": "table", "category": "table", "materials": ["travertine", "brass"]}]}


def test_i3_pass():
    r = check_i3(concept(), placed_ok())
    assert r[0].status == "pass"


def test_i3_too_many_woods_stones():
    c = concept(materials=concept().materials + [MaterialDef("walnut", "wood"), MaterialDef("marble", "stone")])
    p = {"living": [{"id": "a", "materials": ["oak", "walnut", "travertine", "marble"]}]}
    r = check_i3(c, p)[0]
    assert r.status == "fail" and "4 woods/stones" in r.message


def test_i3_too_many_metals():
    c = concept(materials=concept().materials + [MaterialDef("steel", "metal"), MaterialDef("copper", "metal")])
    p = {"kitchen": [{"id": "a", "materials": ["brass", "steel", "copper"]}]}
    assert check_i3(c, p)[0].status == "fail"


def test_i3_material_off_board():
    p = {"living": [{"id": "a", "materials": ["oak", "chrome"]}]}      # chrome inferred as metal, not on board
    r = check_i3(concept(), p)[0]
    assert r.status == "fail" and "chrome" in r.message


def test_i3_no_materials_not_evaluated():
    assert check_i3(concept(), {"hall": [{"id": "x"}]})[0].status == "not_evaluated"


# I4 ------------------------------------------------------------------------
def test_i4_clone_sofa_across_rooms_fails():
    p = {"living": [{"id": "a", "category": "sofa", "product_id": "eg:ikea:1"}],
         "family": [{"id": "b", "category": "sofa", "product_id": "eg:ikea:1"}]}
    r = check_i4(concept(), p)
    assert r[0].status == "fail" and set(r[0].element_ids) == {"a", "b"}


def test_i4_clone_by_name_and_materials_without_product_id():
    p = {"living": [{"id": "a", "name": "Zigzag cushion set", "category": "cushion", "materials": ["wool"]}],
         "bed1": [{"id": "b", "name": "zigzag cushion set", "category": "cushion", "materials": ["wool"]}]}
    assert check_i4(concept(), p)[0].status == "fail"


def test_i4_distinct_heroes_pass():
    p = {"living": [{"id": "a", "category": "sofa", "product_id": "p1"}],
         "family": [{"id": "b", "category": "sofa", "product_id": "p2"}],
         "dining": [{"id": "c", "category": "pendant", "product_id": "p3"}]}
    assert check_i4(concept(), p)[0].status == "pass"


def test_i4_allowed_repeat_passes():
    p = {"a": [{"id": "1", "category": "pendant", "product_id": "p9"}],
         "b": [{"id": "2", "category": "pendant", "product_id": "p9"}]}
    assert check_i4(concept(allowed_repeats=["p9"]), p)[0].status == "pass"


def test_i4_non_hero_repeat_is_fine():
    p = {"a": [{"id": "1", "category": "chair", "product_id": "p9"}],
         "b": [{"id": "2", "category": "chair", "product_id": "p9"}]}
    assert check_i4(concept(), p)[0].status == "not_evaluated"     # no hero items at all


# I1 ------------------------------------------------------------------------
def test_i1_banned_item_rejected_and_clean_room_passes():
    p = {"living": [{"id": "c1", "name": "Orange zig-zag cushion", "category": "cushion"}],
         "bed1": [{"id": "b1", "name": "Linen bed", "category": "bed"}]}
    r = check_i1(concept(), p)
    assert by_subject(r, "living").status == "fail" and by_subject(r, "bed1").status == "pass"


# generic -------------------------------------------------------------------
def test_empty_placed_is_not_evaluated_everywhere():
    for fn in (check_i1, check_i3, check_i4):
        assert fn(concept(), {})[0].status == "not_evaluated"


def test_pass_fail_results_carry_source_ids_and_run_checks():
    res = run_checks(concept(), placed_ok(), {"ceiling": 85, "wall": 55, "floor": 25})
    assert all(isinstance(r, CheckResult) for r in res)
    assert all(r.source_ids for r in res if r.status in ("pass", "fail"))
    assert all(r.lane == "L4" for r in res)


def test_load_placed_accepts_wrapped_and_bare():
    assert load_placed({"rooms": {"a": []}}) == {"a": []}
    assert load_placed({"a": []}) == {"a": []}
