"""RV3 exchange tests: positive round trips, negative (must fail loudly) cases, DXF, take-off reconciliation."""
import copy
import csv
import hashlib
import json
import shutil
from dataclasses import replace
from pathlib import Path

import ezdxf
import ifcopenshell
import pytest

from archpipe.exchange import __main__ as CLI
from archpipe.exchange import common as C
from archpipe.exchange import disciplines as D
from archpipe.exchange import dxf as X
from archpipe.exchange import ifc as I
from archpipe.exchange import quantities as Q
from archpipe.exchange import validate as V
from archpipe.model import api


@pytest.fixture(scope="module")
def model():
    return api.load("D1")


@pytest.fixture(scope="module")
def levels():
    return C.load_levels("D1")


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    d = tmp_path_factory.mktemp("exchange")
    man = CLI.run(d)
    return d, man


def mutate(model, eid, **params):
    """Copy of the model with one element's params changed (deep copy: the fixture stays clean)."""
    out = []
    for e in model:
        if e.id == eid:
            e = replace(e, params={**copy.deepcopy(e.params), **params})
        out.append(e)
    return out


def failed(checks):
    return [c.name for c in checks if not c.ok]


# ---------------------------------------------------------------- positive ------------------------------------------
def test_cli_run_all_validation_passes(out):
    d, man = out
    assert man["ok"], man["validation"]
    assert all(not v["failed"] for v in man["validation"].values())
    for n in ("D1-ARCH.ifc", "D1-LIGHT.ifc", "D1-ELEC.ifc", "D1-B.dxf", "D1-GF.dxf", "D1-SITE.dxf",
              "quantities/D1-takeoff.xlsx", "quantities/D1-by_room.csv", "manifest.json", "validation.txt"):
        assert (d / n).is_file(), n
    assert man["dwg"]["produced"] is False


def test_export_is_deterministic(model, levels, tmp_path):
    a = I.write_ifc(model, tmp_path / "a.ifc", levels, "D1", "ARCH")
    b = I.write_ifc(model, tmp_path / "b.ifc", levels, "D1", "ARCH")
    assert hashlib.sha256(a.read_bytes()).hexdigest() == hashlib.sha256(b.read_bytes()).hexdigest()


def test_elec_counts_match_electrical_outputs(out):
    f = ifcopenshell.open(str(out[0] / "D1-ELEC.ifc"))
    assert len(f.by_type("IfcElectricDistributionBoard")) == 4            # MDB, DB-B, DB-GF + the ELV rack
    summ = json.load(open(Path(__file__).resolve().parents[1] / "electrical" / "d1" / "summary.json"))
    assert len(f.by_type("IfcDistributionSystem")) == summ["circuits"]["total"] + 2 == 60   # 58 final circuits + 2 feeders, in step with the electrical design
    assert not any(s.is_a("IfcLightFixture") for s in f)                  # luminaires live in D1-LIGHT only


def test_door_operation_follows_handing(out, model):
    f = ifcopenshell.open(str(out[0] / "D1-ARCH.ifc"))
    by_tag = {d.Tag: d for d in f.by_type("IfcDoor")}
    lh = next(e for e in model if e.kind == "door" and e.params.get("handing") == "LH")
    rh = next(e for e in model if e.kind == "door" and e.params.get("handing") == "RH")
    assert by_tag[lh.id].OperationType == "SINGLE_SWING_LEFT"
    assert by_tag[rh.id].OperationType == "SINGLE_SWING_RIGHT"
    sliding = next(e for e in model if e.kind == "door" and e.params.get("operation") == "sliding")
    assert by_tag[sliding.id].OperationType in ("DOUBLE_DOOR_SLIDING", "USERDEFINED")


def test_context_levels_flagged_not_ours(out):
    f = ifcopenshell.open(str(out[0] / "D1-ARCH.ifc"))
    flags = {s.Name.split()[0]: V._pset(s, "ArchPipe_Level").get("NotOurs") for s in f.by_type("IfcBuildingStorey")}
    assert flags["B"] is False and flags["GF"] is False
    assert flags["L1"] is True and flags["ROOF"] is True


def test_types_and_photometric_psets(out):
    f = ifcopenshell.open(str(out[0] / "D1-LIGHT.ifc"))
    t = f.by_type("IfcLightFixtureType")[0]
    ps = V._pset(t, "ArchPipe_Photometry")
    assert ps["LuminousFluxLm"] > 0 and "IESFile" in ps
    assert V._pset(t, "Pset_LightFixtureTypeCommon")["TotalWattage"] > 0


def test_layer_set_has_flagged_unauthored_thickness(out):
    f = ifcopenshell.open(str(out[0] / "D1-ARCH.ifc"))
    floor = next(c for c in f.by_type("IfcCovering") if c.Name.startswith("floor-"))
    ml = ifcopenshell.util.element.get_material(floor).MaterialLayers[0]
    assert ml.LayerThickness == 0.0 and "not authored" in ml.Description


# ---------------------------------------------------------------- negative: export must refuse ----------------------
def test_missing_door_host_fails_loudly(model, levels):
    bad = [replace(e, host="") if e.kind == "door" and e.id.endswith("B-lounge-nook-pantry") else e for e in model]
    with pytest.raises(C.ExchangeError, match="no host wall"):
        I.build_ifc(bad, levels)


def test_door_host_not_a_wall_fails(model, levels):
    bad = [replace(e, host="room-lounge") if e.id == "door-B-lounge-cinema" else e for e in model]
    with pytest.raises(C.ExchangeError, match="is not a wall"):
        I.build_ifc(bad, levels)


def test_room_without_polygon_fails_loudly(model, levels):
    bad = mutate(model, "room-lounge", polygon_mm=[])
    with pytest.raises(C.ExchangeError, match="no polygon"):
        I.build_ifc(bad, levels)


def test_stair_without_treads_fails(model, levels):
    bad = mutate(model, "stair-main", tread_boxes_mm=[])
    with pytest.raises(C.ExchangeError, match="tread"):
        I.build_ifc(bad, levels)


def test_unknown_kind_fails(model, levels):
    bad = list(model) + [C.DesignElement(id="x-1", kind="spaceship", level="B")] if hasattr(C, "DesignElement") else None
    with pytest.raises(C.ExchangeError):
        I.build_ifc(bad, levels)


def test_elec_refuses_unmodelled_luminaire(model, levels, tmp_path):
    src = D.ELEC_DIR
    for n in src.iterdir():
        if n.suffix == ".csv":
            shutil.copy(n, tmp_path / n.name)
    rows = list(csv.DictReader((tmp_path / "device_list.csv").open()))
    first = next(r for r in rows if r["family"] == "luminaire")
    first["id"] = "lum-DOES-NOT-EXIST"
    with (tmp_path / "device_list.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    b = I._B(model, levels, "D1", "LIGHT")
    b.build()
    with pytest.raises(C.ExchangeError, match="not in the model"):
        D.light_zones(b, tmp_path)


# ---------------------------------------------------------------- negative: the validator must notice -----------------
@pytest.fixture(scope="module")
def arch_file(model, levels, tmp_path_factory):
    return I.write_ifc(model, tmp_path_factory.mktemp("v") / "arch.ifc", levels, "D1", "ARCH")


def test_validator_clean_on_untouched_model(arch_file, model, levels):
    assert not failed(V.validate_ifc(arch_file, model, levels, "ARCH"))


def test_validator_catches_changed_door_width(arch_file, model, levels):
    bad = mutate(model, "door-B-lounge-cinema", width_mm=905.0)
    assert "door/window sizes" in failed(V.validate_ifc(arch_file, bad, levels, "ARCH", schema_check=False))


def test_validator_catches_changed_room_polygon(arch_file, model, levels):
    r = next(e for e in model if e.id == "room-lounge")
    poly = [[x * 1.05, y] for x, y in r.params["polygon_mm"]]
    bad = mutate(model, "room-lounge", polygon_mm=poly)
    names = failed(V.validate_ifc(arch_file, bad, levels, "ARCH", schema_check=False))
    assert any(n.startswith("room areas") for n in names)


def test_validator_catches_guard_height(arch_file, model, levels):
    bad = mutate(model, "rail-gf-terrace-edge", guard_height_mm=1000.0)
    assert "guard heights from geometry" in failed(V.validate_ifc(arch_file, bad, levels, "ARCH", schema_check=False))


def test_validator_catches_stair_riser(arch_file, model, levels):
    bad = mutate(model, "stair-main", riser_mm=180.0)
    assert any("riser" in n for n in failed(V.validate_ifc(arch_file, bad, levels, "ARCH", schema_check=False)))


def test_validator_catches_missing_and_extra_ids(arch_file, model, levels):
    extra = list(model) + [replace(next(e for e in model if e.kind == "furniture"), id="furn-ghost")]
    assert "id set" in failed(V.validate_ifc(arch_file, extra, levels, "ARCH", schema_check=False))


def test_validator_catches_moved_element(arch_file, model, levels):
    e = next(x for x in model if x.kind == "column")
    moved = [replace(x, placement=(x.placement[0] + 5, x.placement[1], x.placement[2])) if x.id == e.id else x for x in model]
    assert any(n.startswith("placements") for n in failed(V.validate_ifc(arch_file, moved, levels, "ARCH", schema_check=False)))


def test_door_outside_its_void_is_caught(model, levels, tmp_path):
    """Build the file, then break the void relation in the file itself: the validator must see it."""
    f = I.build_ifc(model, levels, "D1", "ARCH")
    rel = f.by_type("IfcRelFillsElement")[0]
    f.remove(rel)
    p = tmp_path / "broken.ifc"
    f.write(str(p))
    assert "doors/windows in their wall void (relations + geometry nesting)" in failed(
        V.validate_ifc(p, model, levels, "ARCH", schema_check=False))


# ---------------------------------------------------------------- DXF ----------------------------------------------
def test_dxf_layers_units_and_wall_extents(out, model):
    d = ezdxf.readfile(str(out[0] / "D1-B.dxf"))
    assert d.units == 4
    layers = {l.dxf.name for l in d.layers}
    assert {"A-WALL", "A-DOOR", "A-GLAZ", "A-AREA-IDEN", "S-COLS", "A-GRID"} <= layers
    walls = [e for e in d.modelspace().query("LWPOLYLINE[layer=='A-WALL']")]
    assert len(walls) == sum(1 for e in model if e.kind == "wall" and e.level == "B")
    xs = [p[0] for w in walls for p in w.get_points("xy")]
    mx = []                                                   # min x of each wall's rectangle, worked out per orientation
    for e in model:
        if e.kind == "wall" and e.level == "B":
            q = e.params
            along_x = abs(q["y1_mm"] - q["y0_mm"]) < 1e-6
            mx.append(min(q["x0_mm"], q["x1_mm"]) - (0 if along_x else q["thickness_mm"] / 2))
    assert min(xs) == pytest.approx(min(mx), abs=1.0)


def test_dxf_audit_clean_and_swing_arcs(out):
    d = ezdxf.readfile(str(out[0] / "D1-GF.dxf"))
    aud = ezdxf.audit.Auditor(d)
    aud.run()
    assert not aud.errors
    assert len(d.modelspace().query("ARC[layer=='A-DOOR']")) >= 1


# ---------------------------------------------------------------- quantities -----------------------------------------
def test_takeoff_reconciles(model):
    dev = D.read_csv("device_list.csv")
    bad = [r for r in Q.reconcile(model, dev) if not r["ok"]]
    assert not bad, bad


def test_takeoff_reconciliation_catches_inconsistency(model):
    fl = next(e for e in model if e.kind == "floor")
    bad = mutate(model, fl.id, area_m2=fl.params["area_m2"] + 1.0)
    assert any(not r["ok"] for r in Q.reconcile(bad, None))


def test_ifc_qto_equal_takeoff(out, model):
    f = ifcopenshell.open(str(out[0] / "D1-ARCH.ifc"))
    qa = sum(V._pset(w, "Qto_WallBaseQuantities")["NetSideArea"] for w in f.by_type("IfcWall"))
    qv = sum(V._pset(s, "Qto_SlabBaseQuantities")["NetVolume"] for s in f.by_type("IfcSlab"))
    el = Q.element_rows(model)
    assert qa == pytest.approx(sum(r["area_m2"] for r in el if r["kind"] == "wall"), abs=1e-3)
    assert qv == pytest.approx(sum(r["volume_m3"] for r in el if r["kind"] == "slab"), abs=1e-3)


def test_layer_without_thickness_has_no_volume(model):
    rows = Q.layer_rows(model)
    unauth = [r for r in rows if r["thickness_mm"] is None]
    assert unauth and all(r["volume_m3"] is None and r["area_m2"] > 0 for r in unauth)
    assert all(r["volume_m3"] is not None for r in rows if r["thickness_mm"] is not None)


def test_xlsx_sheets(out):
    import openpyxl
    wb = openpyxl.load_workbook(out[0] / "quantities" / "D1-takeoff.xlsx")
    assert {"README", "by_type", "by_room", "by_layer", "elements", "reconciliation"} <= set(wb.sheetnames)
    assert wb["by_room"].max_row == 31


def test_light_zones_are_the_published_l6b_zones(out):
    from archpipe.electrical import villa
    f = ifcopenshell.open(str(out[0] / "D1-LIGHT.ifc"))
    pub = {z["id"] for z in json.loads(villa.ZONES_JSON.read_text(encoding="utf-8"))["zones"]}
    groups = [g for g in f.by_type("IfcGroup") if g.ObjectType == "LightingControlZone"]
    assert {g.Name for g in groups} == pub and len(groups) == 68          # none provisional (negative: no Z-PROV-*)
    assert not any(g.Name.startswith("Z-PROV") for g in groups)
