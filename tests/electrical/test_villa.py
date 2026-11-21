"""Lane L7b: the engine on the D1 villa. Each new rule has a positive and a negative test (LANES.md rule 5)."""
import copy
import dataclasses
import json
import math

import pytest

from archpipe import contracts
from archpipe.contracts import DesignElement
from archpipe.electrical import checks, circuits, d1_run, elv, outputs, placement, villa
from archpipe.electrical.model import Door, Furniture, House, Room, Supply


# ---- polygon-aware walls ------------------------------------------------------------------------------------------
L_POLY = ((0.0, 0.0), (6000.0, 0.0), (6000.0, 3000.0), (3000.0, 3000.0), (3000.0, 6000.0), (0.0, 6000.0))


def l_room():
    return Room("L", "living", (0.0, 0.0, 6000.0, 6000.0), "GF", 2700.0, L_POLY)


def test_rectangle_polygon_gives_the_same_walls_as_the_rect():
    a = placement.room_walls(Room("R", "living", (0, 0, 4000, 3000)))
    b = placement.room_walls(Room("R", "living", (0, 0, 4000, 3000), poly=((0, 0), (4000, 0), (4000, 3000), (0, 3000))))
    assert {k: (w.a, w.b, w.n) for k, w in a.items()} == {k: (w.a, w.b, w.n) for k, w in b.items()}


def test_l_shaped_room_has_six_walls_with_inward_normals():
    r = l_room()
    walls = placement.room_walls(r)
    assert set(walls) == {"S", "W", "E", "E2", "N", "N2"}
    for w in walls.values():
        px, py = w.point(w.length / 2, 100.0)             # 100 mm inside the wall
        assert placement.point_in_room(r, px, py), w.name
        ox, oy = w.point(w.length / 2, -100.0)            # 100 mm outside it
        assert not placement.point_in_room(r, ox, oy), w.name


def test_l_shaped_room_devices_stay_inside_the_polygon_and_use_the_inner_walls():
    r = l_room()
    bed = Furniture("BED", "L", "bed", (1000.0, 5000.0, 2600.0, 6000.0), "N2")        # head against the north-facing wall of the upper arm
    h = House("Lshape", [r], [Door("D1", "L", "S", 2500.0, 900.0)], [bed], [], [], [], Supply())
    devs = placement.place_devices(h)
    assert devs and all(placement.point_in_room(r, d.x, d.y, tol=5.0) for d in devs)
    assert not any(4000 < d.x and 4000 < d.y for d in devs)                        # nothing in the notch
    assert any(abs(d.x - 3000.0) < 1.0 and d.y > 3000.0 for d in devs)             # the inner E2 wall gets general sockets
    bs = [d for d in devs if d.rule == "EA1-bedside-both-sides"]
    assert len(bs) == 2 and all(abs(d.y - 6000.0) < 1.0 for d in bs)


def test_wall_walking_negative_wrong_wall_name_is_not_silently_accepted():
    r = l_room()
    with pytest.raises(KeyError):
        placement.switch_for_door(r, Door("D", "L", "X", 100.0, 900.0))


# ---- door hinge data: present -> not flagged; absent -> policy and flagged -----------------------------------------
def _door_el(params):
    return DesignElement("door-T", "door", "GF", (3000.0, 0.0, 0.0), 0.0, (900.0, 100.0, 2100.0), "", "", "", (), params)


def test_door_with_hinge_data_is_not_flagged():
    rooms = {"A": Room("A", "living", (0, 0, 6000, 4000), "GF")}
    flags: list = []
    ds = villa._door_records([_door_el({"rooms": ["A", "core"], "width_mm": 900.0, "hinge": "end"})], rooms, flags)
    assert len(ds) == 1 and ds[0].hinge_known is True and ds[0].hinge == "end"
    assert "0 of 1 door-room records use the policy" in flags[-1]


def test_door_without_hinge_data_uses_policy_and_is_flagged():
    rooms = {"A": Room("A", "living", (0, 0, 6000, 4000), "GF")}
    flags: list = []
    ds = villa._door_records([_door_el({"rooms": ["A"], "width_mm": 900.0})], rooms, flags)
    assert ds[0].hinge_known is False and ds[0].hinge == "start"          # offset 2550 vs 2550: tie -> start
    assert "1 of 1 door-room records use the policy" in flags[-1]


# ---- clearance post-condition ---------------------------------------------------------------------------------------
def _clear_house():
    r = Room("A", "living", (0.0, 0.0, 6000.0, 8000.0), "GF")
    h = House("T", [r], [], [], [], [], [], Supply())
    h.wall_segs = [{"level": "GF", "x0": 0.0, "y0": 8000.0, "x1": 6000.0, "y1": 8000.0, "t": 200.0, "id": "w-n"},
                   {"level": "GF", "x0": 0.0, "y0": 0.0, "x1": 6000.0, "y1": 0.0, "t": 200.0, "id": "w-s"}]
    h.openings = [{"id": "win", "kind": "window", "level": "GF", "x0": 2000.0, "y0": 7850.0, "x1": 4000.0, "y1": 8150.0, "z0": 900.0, "z1": 2300.0}]
    return h


def test_device_in_a_window_fails_the_clearance_check():
    h = _clear_house()
    bad = placement.Device("SOC-1", "socket", "A", 3000.0, 8000.0, 1100.0)
    assert placement.clearance_violations(h, [bad])[0][1].startswith("inside window")
    ok = placement.Device("SOC-2", "socket", "A", 3000.0, 8000.0, 300.0)          # below the sill
    assert placement.clearance_violations(h, [ok]) == []


def test_device_off_every_wall_element_fails_the_clearance_check():
    h = _clear_house()
    edge = placement.Device("SOC-3", "socket", "A", 6000.0, 4000.0, 300.0)         # east edge: no wall element
    assert "not on a wall element" in placement.clearance_violations(h, [edge])[0][1]


def test_placement_slides_a_device_out_of_a_window_and_floor_boxes_open_edges():
    h = _clear_house()
    pt, why = placement.slide_on_wall(h, h.rooms[0], 3000.0, 8000.0, 1100.0)
    assert pt is not None and why.startswith("moved") and placement.clearance(h, "GF", pt[0], pt[1], 1100.0)[0]
    devs = placement.place_devices(h)
    assert placement.clearance_violations(h, devs) == []
    assert any(d.params.get("floor_box") for d in devs)                             # E and W edges have no wall element


def test_ea1_fails_when_a_device_sits_in_a_window():
    h = _clear_house()
    devs = placement.place_devices(h)
    devs.append(placement.Device("SOC-X", "socket", "A", 3000.0, 8000.0, 1100.0, "EA1-general-pitch"))
    res = checks.run_checks(circuits.design(h, devs))
    assert [r for r in res if r.criterion == "EA1" and r.status == "fail" and r.subject == "clearance/SOC-X"]


# ---- the D1 run -----------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def d1(tmp_path_factory):
    t = tmp_path_factory.mktemp("d1")
    return d1_run.run(t / "out", t / "docs", t / "data", t / "checks")


def by(res, crit, status=None, subject=None):
    return [r for r in res if r.criterion == crit and (status is None or r.status == status) and (subject is None or r.subject.startswith(subject))]


def test_d1_no_failures_and_contract_written(d1):
    res = d1["results"]
    assert not [r for r in res if r.status == "fail"], [(r.criterion, r.subject, r.message[:80]) for r in res if r.status == "fail"]
    assert d1["checks_path"].exists() and len(contracts.read_all_results(d1["checks_path"].parent)) == len(res)
    assert {r.criterion for r in res} >= {f"EA{i}" for i in range(1, 16)}


def test_d1_three_boards_one_per_level_plus_main(d1):
    d = d1["design"]
    assert [b.id for b in d.boards] == ["MDB", "DB-B", "DB-GF"]
    assert {b.level for b in d.boards if b.parent} == {"B", "GF"}
    assert set(d.board_feeders) == {"DB-B", "DB-GF"}
    assert all(c.board in {"MDB", "DB-B", "DB-GF"} for c in d.circuits)
    ids = [c.id for c in d.circuits]
    assert len(ids) == len(set(ids))
    for c in d.circuits:                                                          # level boards serve their own level; site loads hang on the MDB
        lvl = {r.id: r.level for r in d.house.rooms}[c.rooms[0]]
        assert c.board == {"B": "DB-B", "GF": "DB-GF"}.get(lvl, "MDB") or c.board == "MDB"


def test_d1_supply_recommendation_is_three_phase_across_the_sensitivity_table(d1):
    sr = d1["summary"]["supply"]
    assert sr["recommendation"] == "three-phase" and sr["max_demand_kva"] > 20
    assert all(row["total_a_1ph_equiv"] > sr["single_phase_limit_a"] for row in sr["sensitivity"])
    ks = [row["kva"] for row in sr["sensitivity"]]
    assert ks == sorted(ks, reverse=True)


def test_supply_recommendation_negative_small_demand_is_single_phase(d1):
    d = copy.copy(d1["design"])
    d.demand = dataclasses.replace(d.demand, total_a=40.0)
    assert outputs.supply_recommendation(d)["recommendation"] == "single-phase"


def test_d1_ea7_not_evaluated_without_ra(d1):
    ea7 = by(d1["results"], "EA7")
    assert len(ea7) == 1 and ea7[0].status == "not_evaluated" and "RA" in ea7[0].message
    assert d1["house"].supply.ra_ohm is None


def test_d1_not_evaluated_stay_not_evaluated(d1):
    for crit in ("EA9", "EA10", "EA14"):
        assert by(d1["results"], crit) and all(r.status == "not_evaluated" for r in by(d1["results"], crit))


def test_d1_equipment_has_status_and_reasons(d1):
    eq = json.loads(villa.EQUIPMENT_JSON.read_text(encoding="utf-8"))
    assert eq["equipment"] and all(e["status"] in ("assumed", "client-confirmed") and len(e["reason"]) > 20 for e in eq["equipment"])
    conf = {e["id"] for e in eq["equipment"] if e["status"] == "client-confirmed"}
    assert "EV-DECK" in conf and "COOK-HOB" not in {e["id"] for e in eq["equipment"]} and all(e["status"] == "client-confirmed" for e in eq["equipment"] if e["kind"] == "ac")
    kinds = {e["kind"] for e in eq["equipment"]}
    assert {"ac", "water_heater", "cooker", "dishwasher", "washer", "fridge", "pump", "gate", "ev"} <= kinds
    assert {h.room for h in [e for e in d1["house"].equipment if e.kind == "ac"]} >= {"kids-a", "kids-b", "parents-bed", "study-game", "lounge", "living", "cinema"}
    assert sum(1 for e in d1["house"].equipment if e.kind == "water_heater") == 3


def test_d1_uses_the_real_l6b_lighting_zones(d1):
    h = d1["house"]
    pub = json.loads(villa.ZONES_JSON.read_text(encoding="utf-8"))["zones"]
    assert not h.provisional_zones and not any(z.id.startswith("Z-PROV") for z in h.zones)
    assert {z.id for z in h.zones} == {z["id"] for z in pub} and len(h.zones) == 69
    assert any("lighting zones from knowledge/lighting/zones-d1.json" in f for f in h.flags) and not any("PROVISIONAL" in f for f in h.flags)
    # published zones never lose watts (sized on rated W where the commissioned W is lower)
    assert all(z.watts >= p["watts"] - 1e-6 for z, p in zip(sorted(h.zones, key=lambda z: z.id), sorted(pub, key=lambda z: z["id"])))
    # every luminaire in exactly one zone, every zone on one circuit (EA13/EA3 joins); escape markers are supplied too
    assert not by(d1["results"], "EA13", "fail") and not by(d1["results"], "EA3", "fail")
    em = [c for c in d1["design"].circuits if c.kind == "lighting" and c.name.startswith("Escape/night marker")]
    assert em and {i for c in em for i in c.load_ids} >= {i for z in h.zones if z.layer == "emergency" for i in z.luminaire_ids}


def test_d1_zones_are_provisional_only_when_the_l6b_file_is_absent(monkeypatch, tmp_path):
    monkeypatch.setattr(villa, "ZONES_JSON", tmp_path / "absent.json")
    h = villa.load_villa()
    assert h.provisional_zones and h.zones and all(z.id.startswith("Z-PROV") for z in h.zones)
    assert any("PROVISIONAL" in f for f in h.flags)


def test_d1_bathroom_zones_use_model_fixtures(d1):
    h = d1["house"]
    wet = {f.id: f for f in h.furniture if f.kind in ("shower", "bath")}
    assert wet["furn-gwc-shower"].params["has_basin"] is False and wet["furn-gwc-shower"].params["outlet_xy"] == [10750.0, -22090.0]
    assert wet["furn-pe-bath"].params["head_h_mm"] == 2300.0
    assert {r.subject for r in by(d1["results"], "EA2", "pass")} >= {"family-bath", "parents-ensuite", "guest-wc"}


def test_d1_every_wall_device_is_clear_of_openings_and_walls(d1):
    h, d = d1["house"], d1["design"]
    assert placement.clearance_violations(h, d.devices) == []
    assert h.wall_segs and h.openings


def test_d1_boards_are_on_walls(d1):
    h = d1["house"]
    for b in h.boards:
        assert placement.clearance(h, b.level, b.xy[0], b.xy[1], b.height_mm)[0], b.id


# ---- EA12 per-board SLD ------------------------------------------------------------------------------------------------------
def test_ea12_fails_when_a_circuit_is_missing_from_a_board_sld(d1):
    d = d1["design"]
    svgs = {b.id: outputs.sld_board_svg(d, b.id) for b in d.boards}
    first = next(c.id for c in d.circuits if c.board == "DB-B")
    svgs["DB-B"] = svgs["DB-B"].replace(f'<g id="{first}">', '<g id="X">')
    res = checks.run_checks(d, svgs=svgs, elv=d1["layout"])
    assert by(res, "EA12", "fail", "schedule=SLD=model")


def test_ea12_spare_ways_per_board(d1):
    assert len(by(d1["results"], "EA12", "pass", "spare ways")) == 3


# ---- EA15: ADB grade, cinema waiver, coverage -------------------------------------------------------------------------------------
def test_adb_requirement_by_storey_area():
    small = elv.adb_requirement({"B": 168.6, "GF": 117.5}, 1)
    assert (small["grade"], small["category"]) == ("D2", "LD3")
    two = elv.adb_requirement({"B": 150.0, "GF": 210.0}, 2)
    assert (two["grade"], two["category"]) == ("A", "LD3")
    three = elv.adb_requirement({"GF": 150.0, "L1": 210.0, "L2": 100.0}, 3)
    assert (three["grade"], three["category"]) == ("A", "LD2")


def test_d1_storey_areas_are_computed_from_the_model(d1):
    a = d1["layout"].storey_area_m2
    assert 150 < a["B"]["net"] < 160 and 100 < a["GF"]["net"] < 106
    assert d1["layout"].adb["grade"] == "D2" and d1["layout"].adb["category"] == "LD3"
    assert by(d1["results"], "EA15", "pass", "alarm-grade")


def test_ea15_alarm_grade_fails_when_a_storey_exceeds_200_m2(d1):
    h = copy.deepcopy(d1["house"])
    h.policy["storey_area_m2"]["B"] = {"net": 230.0, "walls": 20.0, "gross": 250.0}
    lay = elv.build_layout(h, d1["design"].devices)
    assert lay.adb["grade"] == "A"
    r = [x for x in elv.lint(h, lay) if x["subject"] == "alarm-grade"][0]
    assert r["status"] == "fail"


def test_ea15_g1_cinema_mitigation_present_and_fails_when_removed(d1):
    ok = by(d1["results"], "EA15", "pass", "G1-cinema-waiver")
    assert {r.subject for r in ok} == {"G1-cinema-waiver/lounge", "G1-cinema-waiver/cinema"}
    lay = copy.copy(d1["layout"])
    lay.devices = [x for x in lay.devices if not (x.kind == "smoke" and x.room == "cinema")]
    bad = [x for x in elv.lint(d1["house"], lay) if x["subject"] == "G1-cinema-waiver/cinema"]
    assert bad and bad[0]["status"] == "fail"


def test_ea15_detectors_cover_rooms_and_never_sit_in_bathrooms(d1):
    lay, h = d1["layout"], d1["house"]
    kinds = {r.id: r.kind for r in h.rooms}
    assert not [x for x in lay.of("smoke", "heat") if kinds[x.room] == "bathroom"]
    assert {x.room for x in lay.of("heat")} >= {"kitchen", "dirty-kitchen"}
    assert {x.level for x in lay.of("smoke")} == {"B", "GF"}
    assert by(d1["results"], "EA15", "pass", "alarm-coverage")


def test_ea15_coverage_fails_when_a_detector_is_removed(d1):
    lay = copy.copy(d1["layout"])
    lay.devices = [x for x in lay.devices if not (x.kind == "smoke" and x.room == "lounge")]
    r = [x for x in elv.lint(d1["house"], lay) if x["subject"] == "alarm-coverage"][0]
    assert r["status"] == "fail"


def test_ea15_cctv_gate_and_perimeter(d1):
    lay = d1["layout"]
    assert len(lay.of("cctv")) >= 5 and lay.of("intercom_outdoor") and lay.of("rack")
    lay2 = copy.copy(lay)
    lay2.devices = [x for x in lay.devices if x.kind != "cctv"]
    res = {x["subject"]: x["status"] for x in elv.lint(d1["house"], lay2)}
    assert res["cctv-gate"] == "fail" and res["cctv-perimeter"] == "fail"


# ---- routes --------------------------------------------------------------------------------------------------------------------
def test_garden_radial_is_measured_through_all_its_outlets(d1):
    d = d1["design"]
    g = next(c for c in d.circuits if c.name.startswith("Garden sockets"))
    b = next(x for x in d.boards if x.id == g.board)
    far = max(abs(p[0] - b.xy[0]) + abs(p[1] - b.xy[1]) for p in g.points) / 1000.0 * 1.15 + d.house.supply.drop_m
    assert g.length_m > far and g.external and g.vd_total_pct <= 5.0


def test_outputs_written(d1):
    out = d1["out_dir"]
    for f in ("board_schedule_MDB.csv", "board_schedule_DB-B.csv", "board_schedule_DB-GF.csv", "sld_MDB.svg", "sld_DB-B.svg", "sld_DB-GF.svg", "cable_schedule.csv",
              "load_schedule.md", "device_list.csv", "elv_devices.csv", "summary.json", "L7.json"):
        assert (out / f).stat().st_size > 100, f
    assert (out / "sld_DB-B.svg").read_text(encoding="utf-8").startswith("<svg")


# ---- review fixes: wall ends, floor-box keep-outs, vacuous EA4 -----------------------------------------------------------------
def test_device_past_the_end_of_a_wall_is_not_on_the_wall():
    h = _clear_house()
    on = placement.Device("S-1", "socket", "A", 5900.0, 8000.0, 300.0)
    past = placement.Device("S-2", "socket", "A", 6200.0, 8000.0, 300.0)          # 200 mm beyond the wall end
    assert placement.clearance_violations(h, [on]) == []
    assert "not on a wall element" in placement.clearance_violations(h, [past])[0][1]


def test_floor_box_is_dropped_inside_a_keepout():
    h = _clear_house()
    h.keepouts = [{"id": "stair-x", "level": "GF", "x0": 5000.0, "y0": 0.0, "x1": 6000.0, "y1": 8000.0}]
    devs = placement.place_devices(h)
    assert not [d for d in devs if d.params.get("floor_box") and d.x > 4300]
    assert any("stair-x" in m for m in h.dropped)


def test_d1_floor_boxes_avoid_the_stair_and_furniture_and_stairs_get_no_sockets(d1):
    h, d = d1["house"], d1["design"]
    rooms = {r.id: r for r in h.rooms}
    boxes = [x for x in d.devices if x.params.get("floor_box")]
    assert boxes
    for x in boxes:
        assert not placement._in_keepout(h, rooms[x.room], x.x, x.y, margin=0.0), (x.id, x.room)
    assert not [x for x in d.devices if rooms[x.room].kind == "stair" and x.kind == "socket"]


def test_d1_ea4_records_are_not_evaluated_without_a_limit_but_reference_cases_pass(d1):
    res = d1["results"]
    inst = by(res, "EA4", subject="installation")
    assert inst and all(r.status == "not_evaluated" for r in inst) and "kVA" in inst[0].message
    assert all(r.status == "not_evaluated" for r in by(res, "EA4", subject="board"))
    assert len(by(res, "EA4", "pass", "REF")) == 5


def test_d1_boards_have_a_600_mm_clear_wall_stretch(d1):
    h = d1["house"]
    rooms = {r.id: r for r in h.rooms}
    for b in h.boards:
        w = min(placement.room_walls(rooms[b.room]).values(), key=lambda w: abs(w.depth_of(*b.xy)))
        a = w.along_of(*b.xy)
        assert all(placement.clearance(h, b.level, *w.point(a + dx), b.height_mm)[0] for dx in (-300.0, 0.0, 300.0)), b.id
