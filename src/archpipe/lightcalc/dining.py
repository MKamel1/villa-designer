"""Smoke run: the D1 dining area (L-shaped open-plan zone), LA1-LA3 on the table, per scene.

Inputs come from the L2 design model (`archpipe.model.load("D1")`: room polygons, luminaire
placements, aim vectors, photometry references). `extract_input()` freezes them into
knowledge/lighting/d1-dining-input.json so the run reproduces without `out/`.

Two luminaire sets are calculated and both are reported:
  model  : what the L2 model holds for the dining rooms: 4 recessed adjustable spots (LSEVO-AAHENX,
           real iGuzzini photometry) + the linear pendant over the table (generic photometry, 1200 lm,
           90 deg beam; the model flags it `generic`). The pendant is a 1.6 m line source: it is
           subdivided into 8 equal point sources along its axis (a single point source 0.74 m over the
           table would overstate the peak; the subdivision is still an approximation).
  built  : only the 4 spots (the analytic lights of scene.json). NOTE: the render ALSO emits the pendant as an emissive
           Lambertian strip; `render` (L6b) adds it, see docs/lanes/L6b-villa-lighting.md.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from ..contracts import CheckResult
from . import checks, synth
from .direct import Placement
from .geometry import ccw
from .radjob import RadParams, Room
from .roomcalc import RoomCalc, Scene, TaskPlane

ROOT = Path(__file__).resolve().parents[3]
INPUT = ROOT / "knowledge" / "lighting" / "d1-dining-input.json"
IES_DIR = ROOT / "knowledge" / "lighting" / "ies"
TARGET_CARD = "ies-res-dining-informal-100"
TARGET_LUX = 100.0
MF = 0.8


def extract_input(out: Path = INPUT, scene_json: Path | None = None) -> dict:
    from ..model import load
    els = load("D1")
    rooms = {e.id: e for e in els if e.kind == "room" and e.id in ("room-dining", "room-dining-side")}
    z_b = -3.0
    dining = [(x / 1000, y / 1000) for x, y in rooms["room-dining"].params["polygon_mm"]]
    side = [(x / 1000, y / 1000) for x, y in rooms["room-dining-side"].params["polygon_mm"]]
    # union of the two rectangles sharing the edge y = -26.671 (x 15.745..18.367)
    poly = [(14.902, -26.671), (15.745, -26.671), (15.745, -28.671), (18.367, -28.671), (18.367, -23.591), (14.902, -23.591)]
    lums = []
    for e in els:
        if e.kind == "luminaire" and e.room in ("dining", "dining-side"):
            lums.append({"id": e.id, "x": e.placement[0] / 1000, "y": e.placement[1] / 1000,
                         "z": z_b + e.placement[2] / 1000, "aim": e.params["aim"], "layer": e.params["layer"],
                         "kind": e.params["fixture_kind"], "flux_lm": e.params["flux_lm"], "watts": e.params["watts"],
                         "ies": e.params["photometry"]["ies"], "generic": e.params["photometry"]["generic"],
                         "beam_deg": e.params["beam_deg"], "card": e.params["illuminance_card"],
                         "length_m": 1.6 if e.params["fixture_kind"] == "PEN-LIN" else 0.0})
    table = next(e for e in els if e.id == "furn-dining-table")
    tx, ty = table.placement[0] / 1000, table.placement[1] / 1000
    tw, td, th = (v / 1000 for v in table.size)
    data = {"source": "archpipe.model.load('D1') (L2 snapshot)", "room_polygon_m": poly,
            "floor_z": z_b, "ceiling_z": z_b + rooms["room-dining"].params["clear_height_mm"] / 1000,
            "rooms_polygons_m": {"dining": dining, "dining-side": side},
            "open_to": {"dining": rooms["room-dining"].params.get("open_to"),
                        "dining-side": rooms["room-dining-side"].params.get("open_to")},
            "table": {"centre": [tx, ty], "size": [tw, td], "top_z": z_b + th},
            "target": {"card": TARGET_CARD, "lux": TARGET_LUX},
            "luminaires": lums}
    sj = scene_json or Path(r"C:\Users\mmbka\arch-pipeline\out\villa\render-d1\scene.json")
    if sj.exists():
        sc = json.loads(sj.read_text(encoding="utf-8"))
        mats = sc["materials"]
        data["reflectances"] = {"wall": mats["plaster-warm-white"]["reflectance"],
                                "ceiling": mats["ceiling-white"]["reflectance"],
                                "floor": mats["oak-floor"]["reflectance"],
                                "basis": "scene.json materials plaster-warm-white / ceiling-white / oak-floor (ASSUMED finishes)"}
        meas = json.loads((sj.parent / "lighting-measurements.json").read_text(encoding="utf-8"))
        data["cycles_measurement"] = [p for p in meas["points"] if p["room"] == "dining"]
        data["cycles_dining_lights"] = [l["id"] for l in sc["lights"]
                                        if 14.9 <= l["position"][0] <= 18.4 and -28.7 <= l["position"][1] <= -23.5
                                        and -3.0 < l["position"][2] < 0.5 and l["room"] in ("dining", "dining-side")]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return data


def placements(data: dict, include_pendant: bool, pendant_parts: int = 8, lambertian: bool = False) -> list[Placement]:
    """lambertian=True models the pendant as the render emits it (a Lambertian strip, 1200 lm; Cycles truth probe: 343 lx at
    the table centre); False keeps the model's generic cos^n 90 deg beam (about 464 lx there: 35 % too much)."""
    from ..concept.villa_lighting import generic_ies
    out = []
    for l in data["luminaires"]:
        zone = "Z-DIN-PEN" if l["kind"] == "PEN-LIN" else ("Z-DIN-FILL" if l["card"] == TARGET_CARD else "Z-DIN-ACCENT")
        if l["kind"] == "PEN-LIN":
            if not include_pendant:
                continue
            n = pendant_parts
            text = generic_ies(l["flux_lm"] / n, 120 if lambertian else l["beam_deg"], "PEN-LIN part")
            ph = synth.load_text(text, "PEN-LIN-part")
            L = l["length_m"]
            for k in range(n):
                dx = -L / 2 + (k + 0.5) * L / n          # `along` = +x in the model
                out.append(Placement(f"{l['id']}#{k}", ph, (l["x"] + dx, l["y"], l["z"]), zone=zone, layer=l["layer"],
                                     watts=(l["watts"] or 0) / n or None, meta={"ies_text": text, "generic": True}))
            continue
        ies = IES_DIR / Path(l["ies"]).name
        from ..photometry import load as load_ies
        out.append(Placement(l["id"], load_ies(ies), (l["x"], l["y"], l["z"]), aim=tuple(l["aim"]), zone=zone,
                             layer=l["layer"], watts=l["watts"], meta={"ies_path": str(ies)}))
    return out


def build(data: dict, include_pendant: bool, params: RadParams | None = None, lambertian: bool = False,
          label: str | None = None) -> RoomCalc:
    r = data["reflectances"]
    room = Room(tuple(map(tuple, data["room_polygon_m"])), data["floor_z"], data["ceiling_z"],
                rho_floor=r["floor"], rho_wall=r["wall"], rho_ceiling=r["ceiling"])
    cx, cy = data["table"]["centre"]
    tw, td = data["table"]["size"]
    z = data["table"]["top_z"]
    table = tuple((cx + sx * tw / 2, cy + sy * td / 2) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)))
    pt = tuple((cx + sx * 0.05, cy + sy * 0.05) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)))
    planes = [TaskPlane("table-top", table, z, data["target"]["lux"]),
              TaskPlane("table-centre-point", pt, z, data["target"]["lux"], spacing=0.1)]
    name = label or ("D1-dining" + ("" if include_pendant else "-built"))
    return RoomCalc(name, room, placements(data, include_pendant, lambertian=lambertian),
                    planes, params or RadParams(ab=6, ab_extra=(12,)), mf=MF)


def scene_dimmed(calc: RoomCalc, target: float = TARGET_LUX, accent: float = 1.0) -> Scene:
    """A dinner scene that lights the table to the card. The Em on the table is linear in the zone levels, so with
    the sideboard accent left at `accent` and one common factor f on the table-lighting zones (pendant + fill):
    Em = f * Em_table_zones + accent * Em_accent = target  ->  f = (target - accent * Em_accent) / Em_table_zones."""
    zones = {p.zone for p in calc.placements}
    tab = Scene("tab", {z: (0.0 if z == "Z-DIN-ACCENT" else 1.0) for z in zones})
    acc = Scene("acc", {z: (accent if z == "Z-DIN-ACCENT" else 0.0) for z in zones})
    em_tab = calc.stats("table-top", tab).em
    em_acc = calc.stats("table-top", acc).em
    f = max(0.0, min(1.0, (target - em_acc) / em_tab))
    levels = {z: (accent if z == "Z-DIN-ACCENT" else f) for z in zones}
    return Scene(f"dinner-dimmed(f={f:.2f})", levels)


def run(workdir: Path, host: str | None = None, out_json: Path | None = None, reuse: bool = False) -> dict:
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    report = {"input": str(INPUT.relative_to(ROOT)), "maintenance_factor": MF, "target": data["target"],
              "cycles_measurement_dining": data.get("cycles_measurement"), "variants": {}}
    results: list[CheckResult] = []
    # "render" = what scene.json renders: the 4 spots AND the emissive Lambertian pendant (the old "built" omitted it)
    for name, pend, lam in (("model", True, False), ("built", False, False), ("render", True, True)):
        calc = build(data, pend, lambertian=lam, label="D1-dining-render" if lam else None)
        if reuse:
            calc.load_results(Path(workdir) / name)
        else:
            calc.run(Path(workdir) / name, host)
        full = Scene.full({p.zone for p in calc.placements})
        dim = scene_dimmed(calc)
        spots = [z for z in ("Z-DIN-FILL", "Z-DIN-ACCENT")]
        report["variants"][name] = {"luminaires": [p.id for p in calc.placements],
                                    "direct_cross_check_spots": {pid: calc.direct_cross_check(pid, spots) for pid in ("table-top",)},
                                    "scenes": {s.name: calc.report(s) for s in (full, dim)}}
        for s in (full, dim):
            for r in calc.checks(s):
                if "table-top" in r.subject:
                    results.append(r)
    report["checks"] = [r.__dict__ for r in results]
    if out_json:
        Path(out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(out_json).write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    return {"report": report, "results": results}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["extract", "run"])
    ap.add_argument("--workdir", default="out/L6/dining")
    ap.add_argument("--host", default=None)
    ap.add_argument("--out", default="knowledge/lighting/L6-dining-result.json")
    ap.add_argument("--reuse", action="store_true")
    a = ap.parse_args()
    if a.cmd == "extract":
        d = extract_input()
        print(len(d["luminaires"]), "luminaires", d.get("reflectances"))
    else:
        r = run(Path(a.workdir), a.host, Path(a.out), a.reuse)
        for c in r["results"]:
            print(c.criterion, c.status, c.subject, c.message)
