"""Lighting control zones (D1-LIGHT.ifc) and the electrical file (D1-ELEC.ifc), on the shared origin of ifc.py.

Inputs are the committed electrical-lane outputs in tests/electrical/d1/ (device_list.csv, board_schedule_*.csv) and the
board positions from archpipe.electrical.villa. Control zones are L6b's published `knowledge/lighting/zones-d1.json` (layer, dimming
and watts are read from it); if that file is absent the electrical lane's provisional `Z-PROV-*` zones are used and labelled so.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from . import common as C
from . import ifc as I

ROOT = Path(__file__).resolve().parents[3]
ELEC_DIR = ROOT / "tests" / "electrical" / "d1"
BOARD_IDS = ("MDB", "DB-B", "DB-GF")

# device kind -> (IFC class, PredefinedType). Unknown kinds raise: nothing is placed as a guess.
DEVICE_CLASS = {
    "socket": ("IfcOutlet", "POWEROUTLET"), "data": ("IfcOutlet", "DATAOUTLET"), "tv_sat": ("IfcOutlet", "AUDIOVISUALOUTLET"),
    "switch": ("IfcSwitchingDevice", "NOTDEFINED"), "isolator_ac": ("IfcSwitchingDevice", "SWITCHDISCONNECTOR"),
    "fcu": ("IfcElectricAppliance", "NOTDEFINED"), "cooker_unit": ("IfcElectricAppliance", "NOTDEFINED"),
    "smoke": ("IfcSensor", "SMOKESENSOR"), "heat": ("IfcSensor", "HEATSENSOR"),
    "cctv": ("IfcAudioVisualAppliance", "CAMERA"), "ap": ("IfcCommunicationsAppliance", "NETWORKAPPLIANCE"),
    "ap_outdoor": ("IfcCommunicationsAppliance", "NETWORKAPPLIANCE"), "rack": ("IfcElectricDistributionBoard", "USERDEFINED"),
    "intercom_monitor": ("IfcCommunicationsAppliance", "NOTDEFINED"), "intercom_outdoor": ("IfcCommunicationsAppliance", "NOTDEFINED"),
}


def read_csv(name: str, directory: Path | None = None) -> list[dict]:
    path = (directory or ELEC_DIR) / name
    if not path.is_file():
        raise C.ExchangeError([f"electrical output missing: {path}"])
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def light_zones(b: "I._B", directory: Path | None = None) -> int:
    """One IfcGroup per control zone, members = its luminaires. Returns the number of zones."""
    rows = [r for r in read_csv("device_list.csv", directory) if r["family"] == "luminaire"]
    unknown = [r["id"] for r in rows if r["id"] not in b.ent]
    if unknown:
        raise C.ExchangeError([f"device_list luminaires not in the model: {unknown[:6]} ({len(unknown)})"])
    zones: dict[str, list[dict]] = {}
    for r in rows:
        if not r["serves"]:
            raise C.ExchangeError([f"{r['id']}: luminaire has no control zone in device_list.csv"])
        zones.setdefault(r["serves"], []).append(r)
    from ..electrical import villa
    pub = {}
    if villa.ZONES_JSON.exists():
        raw = json.loads(villa.ZONES_JSON.read_text(encoding="utf-8"))
        pub = {q["id"]: q for q in (raw["zones"] if isinstance(raw, dict) else raw)}
    for z, rs in sorted(zones.items()):
        g = b.api.root.create_entity(b.f, ifc_class="IfcGroup", name=z)
        g.GlobalId = I.guid(f"zone-{z}")
        g.ObjectType = "LightingControlZone"
        b.api.group.assign_group(b.f, products=[b.ent[r["id"]] for r in rs], group=g)
        b._pset(g, "ArchPipe_ControlZone", dict(
            Zone=z, Room=rs[0]["room"], Level=rs[0]["level"], Layer=pub[z]["layer"] if z in pub else rs[0]["kind"], Members=len(rs),
            **({"Dimming": pub[z]["dimming"]} if z in pub else {}),
            Circuits=", ".join(sorted({r["circuit"] for r in rs if r["circuit"]})),
            TotalWatts=round(sum(float(b.by[r["id"]].params.get("watts") or 0) for r in rs), 2),
            Basis=("control zone published by lane L6b (knowledge/lighting/zones-d1.json)" if z in pub else
                   "provisional zone from the electrical lane (device_list.csv 'serves'); no L6b zone of this id")))
    return len(zones)


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def build_elec(elements, levels=None, design="D1", directory: Path | None = None):
    """D1-ELEC.ifc: the shared spatial skeleton + boards, devices and circuits (IfcDistributionSystem, ELECTRICAL)."""
    import ifcopenshell.api.group  # noqa: F401
    from ..electrical import villa
    levels = levels or C.DEFAULT_LEVELS
    C.require_clean(elements, levels)
    b = I._B(elements, levels, design, "ELEC")
    b.hosted = {}
    walls = [e for e in elements if e.kind == "wall"]
    dev_rows = read_csv("device_list.csv", directory)
    h = villa.load_villa()
    boards = {}
    for bd in h.boards:
        ang = 0.0
        near = [(C.project_on_wall(w, bd.xy), w) for w in walls if w.level == bd.level]
        near = [(pr, w) for pr, w in near if -1 <= pr[0] <= C.wall_length(w) + 1]
        if near:
            ang = C.wall_angle_deg(min(near, key=lambda t: t[0][1])[1])
        el = b.api.root.create_entity(b.f, ifc_class="IfcElectricDistributionBoard", name=bd.id)
        el.GlobalId = I.guid(f"board-{bd.id}")
        el.Tag = bd.id
        el.PredefinedType = "SWITCHBOARD" if bd.id == "MDB" else "DISTRIBUTIONBOARD"
        el.ObjectPlacement = b._lp(bd.xy[0], bd.xy[1], C.ffl(levels, bd.level), ang)
        el.Representation = b.shape([b.rect(600.0, 150.0, float(bd.height_mm))])
        b.api.spatial.assign_container(b.f, products=[el], relating_structure=b.storey[bd.level])
        b._pset(el, "ArchPipe_Board", dict(
            BoardId=bd.id, Level=bd.level, Room=bd.room, Parent=bd.parent, AmbientC=bd.ambient_c,
            GeometryBasis="600 x 150 mm x board height box on a wall stretch; mounting height and orientation "
                          "not authored (box starts at FFL, aligned to the nearest wall)"))
        boards[bd.id] = el
    placed: dict[str, object] = {}
    n_dev = 0
    for r in dev_rows:
        if r["family"] == "luminaire":
            continue
        if r["kind"] not in DEVICE_CLASS:
            raise C.ExchangeError([f"{r['id']}: no IFC class for device kind {r['kind']!r}"])
        cls, pre = DEVICE_CLASS[r["kind"]]
        el = b.api.root.create_entity(b.f, ifc_class=cls, name=r["id"])
        el.GlobalId = I.guid(f"dev-{r['id']}")
        el.Tag = r["id"]
        el.PredefinedType = pre
        if pre == "USERDEFINED":
            el.ObjectType = "ELV rack / cabinet"
        lv = r["level"]
        z = C.ffl(levels, lv) + (_num(r["z_mm"]) or 0.0)
        el.ObjectPlacement = b._lp(float(r["x_mm"]), float(r["y_mm"]), z - 50)
        el.Representation = b.shape([b.rect(100.0, 100.0, 100.0)])
        b.api.spatial.assign_container(b.f, products=[el], relating_structure=b.container[lv if lv in b.container else "SITE"])
        b._pset(el, "ArchPipe_ElecDevice", dict(
            DeviceId=r["id"], Kind=r["kind"], Family=r["family"], Room=r["room"], Level=lv, Rule=r["rule"],
            Serves=r["serves"], Circuit=r["circuit"], Note=r["note"], HeightAboveLevel_mm=_num(r["z_mm"]),
            GeometryBasis="nominal 100 mm cube marker at the listed point; not product geometry"))
        placed[r["id"]] = el
        n_dev += 1
    lum_by_circuit: dict[str, list[str]] = {}
    for r in dev_rows:
        for c in r["circuit"].split("+") if r["family"] == "luminaire" and r["circuit"] else ():
            lum_by_circuit.setdefault(c, []).append(r["id"])
    n_circ, claimed = 0, set()
    for bid in BOARD_IDS:
        for r in read_csv(f"board_schedule_{bid}.csv", directory):
            cid = r["circuit"]
            sysm = b.api.root.create_entity(b.f, ifc_class="IfcDistributionSystem", name=cid)
            sysm.GlobalId = I.guid(f"circuit-{cid}")
            sysm.PredefinedType = "ELECTRICAL"
            sysm.LongName = r["description"]
            on = [x for x in dev_rows if cid in x["circuit"].split("+")]       # a switch can serve two circuits
            members = [boards[bid]] + [placed[x["id"]] for x in on if x["id"] in placed]
            claimed.update(x["id"] for x in on)
            b.api.group.assign_group(b.f, products=members, group=sysm)
            lums = lum_by_circuit.get(cid, [])
            b._pset(sysm, "ArchPipe_Circuit", dict(
                CircuitId=cid, Board=bid, Phase=r["phase"], Description=r["description"], Protection=r["device"],
                Ib_A=_num(r["ib_a"]), In_A=_num(r["in_a"]), ConnectedW=_num(r["connected_w"]), Cable=r["cable"],
                Method=r["method"], Length_m=_num(r["length_m"]), Iz_A=_num(r["iz_a"]), VoltDropTotalPct=_num(r["vd_total_pct"]),
                VoltDropLimitPct=_num(r["vd_limit_pct"]), FeederTo=r["feeder_to"] or None,
                Devices=len(members) - 1, LuminaireCount=len(lums), LuminaireIds=", ".join(lums) or None,
                Note="route lengths are the electrical lane's estimate (Manhattan x 1.15 + drops), not a surveyed route; "
                     "luminaires live in D1-LIGHT.ifc and are listed by id (GlobalId = deterministic hash of the id)"))
            n_circ += 1
    orphans = [r["id"] for r in dev_rows if r["family"] != "luminaire" and r["circuit"] and r["id"] not in claimed]
    if orphans:
        raise C.ExchangeError([f"devices on circuits with no schedule row: {orphans[:6]}"])
    I.finish_header(b.f, "D1-ELEC.ifc")
    b.f.archpipe_builder = b
    b.counts = dict(boards=len(boards), devices=n_dev, circuits=n_circ)
    return b.f
