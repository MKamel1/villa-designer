"""LDG pass 2 tests: typology packages (3 concepts x 2 pond options), positive and negative guards."""
import copy
import json
from pathlib import Path

import pytest

from archpipe.landscape.concept import ty_core as C, ty_run as R, ty_south as TS
from archpipe.landscape.concept.species import pool

PLANTS = Path(__file__).resolve().parents[3] / "knowledge" / "landscape" / "plants" / "plants.json"
PACKAGES = [(c, w) for c in "ABC" for w in ("east", "north")]


@pytest.fixture(scope="module")
def built():
    out = {}
    for c, w in PACKAGES:
        L, rooms, covers = R.build(c, w)
        res, seen = R.evaluate_all(L, rooms, covers)
        out[(c, w)] = (L, rooms, covers, res)
    return out


def test_zero_hard_fails_in_every_package(built):
    for k, (_, _, _, res) in built.items():
        assert not R.hard_fails(res), (k, [(r.criterion, r.subject) for r in R.hard_fails(res)])


def test_every_planted_species_is_viable_or_conditional_in_plants_json(built):
    data = {r["slug"]: r["site_viability"]["verdict"] for r in json.load(open(PLANTS))["species"]}
    for k, (L, _, _, _) in built.items():
        used = {p["species"] for g in L["planting_groups"] for p in g["plants"]} | {t["species"] for t in L["trees"]}
        assert used and all(data[s] in ("viable", "viable_with_conditions") for s in used), (k, used)


def test_concepts_are_distinct_in_structure(built):
    pits = {c: next(f for f in built[(c, "east")][0]["features"] if f["kind"] == "firepit")["center"] for c in "ABC"}
    trees = {c: built[(c, "east")][0]["trees"][0]["center"] for c in "ABC"}
    ids = {c: sorted(g["id"] for g in built[(c, "east")][0]["planting_groups"] if g["rect"][0] > 20) for c in "ABC"}
    assert len({round(p[1], 0) for p in pits.values()}) == 3 or max(abs(pits["A"][1] - pits["B"][1]), abs(pits["B"][1] - pits["C"][1])) > 1.0
    assert len({tuple(round(x, 1) for x in t) for t in trees.values()}) == 3
    assert len({tuple(v) for v in ids.values()}) == 3
    # each concept has its OWN north court and east yard (not shared)
    north = {c: sorted(g["id"] for g in built[(c, "east")][0]["planting_groups"] if g["rect"][0] < 5) for c in "ABC"}
    east = {c: sorted(g["id"] for g in built[(c, "east")][0]["planting_groups"] if 14 < g["rect"][0] < 22.5) for c in "ABC"}
    assert len({tuple(v) for v in north.values()}) == 3 and len({tuple(v) for v in east.values()}) == 3


def test_pond_only_in_the_client_choice_locations(built):
    for (c, w), (L, _, _, _) in built.items():
        ponds = [f for f in L["features"] if f["kind"] == "pond"]
        assert len(ponds) == 1 and ((ponds[0]["rect"][0] < 5) == (w == "north")), (c, w)


def test_each_south_concept_has_a_canopy_tree_in_the_precedent_range(built):
    for c in "ABC":
        m = R.metrics(built[(c, "east")][0])
        assert m["canopy_trees"] in (1, 2) and R.PREC["trees"][0] <= m["trees_per_100m2_south"] <= R.PREC["trees"][1], (c, m)


def test_gathering_capacity_states_seated_and_standing(built):
    for c in "ABC":
        m = R.metrics(built[(c, "east")][0])
        s = m["seats"]
        assert s["dining"] == 8 and s["dining"] + s["built_in_and_lounge"] + s["quiet_south"] >= 10
        assert m["standing_at_1.3m2"] >= 15


def test_table_extension_is_measured_not_assumed(built):
    ext = R.extension_checks(built[("A", "east")][0])
    assert ext[8]["status"] == "pass" and ext[12]["clear_mm"] < 1200            # 12 seats do NOT fit: reported, not hidden


# ---- negative guards: the checks must fail when the design is wrong -----------------------------------------------------
def _south_layout(concept, **over):
    p = copy.deepcopy(R.PARAMS[concept])
    p.update(over)
    f, rooms, cov = R.SOUTH[concept](p)
    return C.assemble(C.site_frag(), f)


def test_fire_pit_too_near_table_fails():
    L = _south_layout("A", pit=(2.5, 4.4))                 # pit edge 0.55 m from the table end
    r = [x for x in R.hard_fails(C.ldk(L)) if x.criterion == "LS-FIRE-SEAT"]
    assert r


def test_tree_over_paving_fails_rootzone():
    L = _south_layout("B", gravel=(3.2, 7.9, 5.6), tree=(4.4, 8.4))      # the permeable tree floor no longer covers the dripline
    r = [x for x in R.hard_fails(C.ldk(L)) if x.criterion == "LS-ROOTZONE"]
    assert r


def test_shallow_layered_border_fails_policy_depth(built):
    L = copy.deepcopy(built[("A", "east")][0])
    g = next(g for g in L["planting_groups"] if g["id"] == "bed-west")
    g["rect"] = [g["rect"][0], g["rect"][1], g["rect"][2], g["rect"][1] + 0.8]
    res = C.own_checks(L, {}, [], -0.9, None)
    assert any(r.criterion == "LDG-BEDDEPTH" and r.status == "fail" for r in res)


def test_mixed_hydrozone_bed_fails():
    L = copy.deepcopy(_south_layout("A"))
    g = next(g for g in L["planting_groups"] if g["id"] == "bed-west")
    g["plants"].append(C.entry("gazania_rigens", (g["rect"][0] + 1, g["rect"][1] + 0.5)))      # low-water plant in a medium bed
    r = [x for x in R.hard_fails(C.ldk(L)) if x.criterion == "LS-HYDROZONE" and x.subject == "bed-west"]
    assert r


def test_sun_hungry_plant_in_the_dark_north_court_fails(built):
    L = copy.deepcopy(built[("A", "east")][0])
    g = next(g for g in L["planting_groups"] if g["id"] == "n-street")
    g["plants"].append(C.entry("gazania_rigens", (g["rect"][0] + 0.3, g["rect"][1] + 1)))      # full-sun groundcover at 1.4 h
    res, _ = R.sun_checks(L)
    assert res[0].status == "fail"


def test_quiet_when_it_should_be(built):               # stays quiet: a correct package has no overlap/fail from the own checks
    L, rooms, covers, res = built[("C", "east")]
    assert not [r for r in res if r.criterion.startswith("LDG-") and r.status == "fail"]


def test_screened_label_does_not_say_open():
    src = (Path(R.__file__).parent / "plan_draft.py").read_text()
    assert "sister plot open on the left edge" not in src


def test_critics_classify_seats_into_dining_lounge_quiet(built):
    """Guard for the overlapping-zones defect: the critics take the FIRST zone containing a point, so overlapping room rectangles once made
    every seat 'dining' (U-GATHER-GROUPS: 23 dining, 0 lounge). Specific zones must come first."""
    from archpipe.landscape.critic import computed as CP
    for c in "ABC":
        L = built[(c, "east")][0]
        use = {}
        for s in CP.seat_points(L):
            if s["pt"][0] > 22.5:
                use[s["use"]] = use.get(s["use"], 0) + 1
        assert use.get("dining", 0) >= 6 and use.get("lounge", 0) >= 3 and use.get("quiet", 0) >= 1, (c, use)


def test_lone_dot_planting_is_avoided(built):
    """Every bed species forms runs: a bed of three or more plants holds at least one species with >= 3 plants (no lone dots)."""
    for k, (L, _, _, _) in built.items():
        for g in L["planting_groups"]:
            if g["role"] in ("border", "mass") and len(g["plants"]) >= 3:
                counts = {}
                for p in g["plants"]:
                    counts[p["species"]] = counts.get(p["species"], 0) + 1
                assert max(counts.values()) >= 3, (k, g["id"], counts)
