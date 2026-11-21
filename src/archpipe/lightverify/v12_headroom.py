"""V12 commissioning headroom: every task card is met in its owning scene with the zone driver at <= 80 % of maximum.

Output fraction of a zone in a scene = scene level x driver factor d (knowledge/lighting/zone-drivers.json, the solved
commissioning output relative to the rated output; no table entry = 1.0). Checked for every zone that has a driver and
that the card's owning scene lights (level > 0) in the plane's cluster. d > 1.0 means the card needs more than the
fitting's rated output (for a bound product the engine silently caps the dimmer at 1.0: see `apply_drivers`).
"""
from __future__ import annotations

from collections import defaultdict

from .common import LayerResult, check
from .sources import CARDS, ids
from ..contracts import SourceCard

LIMIT = 0.80
CARDS["LV-V12-HEAD"] = SourceCard("LV-V12-HEAD", "archpipe lighting verification plan", "2026-11-21", "V12", "",
                                  "zone driver level <= 0.80 of maximum in the scene that owns the task card", "policy",
                                  "docs/quality/LIGHTING-VERIFICATION.md")
SRC = ids("LV-V12-HEAD")


def _level(spec: dict, zone: str, layer: str) -> float:
    lv = 0.0
    for key, val in spec.items():
        if key.startswith("*"):
            if layer == key[1:]:
                lv = val
        elif zone.endswith("-" + key.upper()) or zone == key.upper():
            lv = val
    return lv


def run(v, drivers: dict | None = None, scenes: dict | None = None, limit: float = LIMIT) -> LayerResult:
    from ..concept import villa_lighting as VL
    from ..lightcalc.villa import cluster_of
    from ..lightcalc.villa import zone_id, zone_layer
    L = LayerResult("V12")
    drivers = drivers if drivers is not None else VL._drivers()
    scenes = scenes if scenes is not None else VL.SCENES
    zones = defaultdict(dict)            # cluster -> zone -> (layer, product-bound?)
    for f in v.fixtures:
        zones[cluster_of(f.room)][zone_id(f)] = (zone_layer(f), bool(f.record.product))
    for pl in v.planes():
        if pl.id.startswith("room-"):
            continue
        cl = cluster_of(pl.room)
        spec = scenes.get(cl, {}).get(pl.scene)
        if spec is None:
            L.results.append(check("LV12", "not_evaluated", pl.id, (), message="scene %s not defined for cluster %s" % (pl.scene, cl)))
            L.mark(pl.room, "not_evaluated")
            continue
        rows = []
        for z, (layer, prod) in zones[cl].items():
            if z not in drivers:
                continue
            lv = _level(spec, z, layer)
            if lv > 0:
                rows.append((z, lv * drivers[z], prod))
        if not rows:
            L.results.append(check("LV12", "not_evaluated", pl.id, (), message="no commissioned zone is lit in scene %s" % pl.scene))
            L.mark(pl.room, "not_evaluated")
            continue
        z, worst, prod = max(rows, key=lambda r: r[1])
        ok = worst <= limit
        msg = "%s in %s: zone %s at %.0f %% of maximum (limit %.0f %%)%s" % (pl.id, pl.scene, z, 100 * worst, 100 * limit,
                                                                           "; needs more than rated output" if worst > 1.0 else "")
        L.results.append(check("LV12", "pass" if ok else "fail", pl.id, SRC, achieved=round(worst, 3), required=limit, unit="of max", message=msg,
                               element_ids=(z,)))
        L.table.append(dict(plane=pl.id, scene=pl.scene, zone=z, level=worst, bound=prod, ok=ok))
        L.mark(pl.room, "pass" if ok else "fail")
    return L
