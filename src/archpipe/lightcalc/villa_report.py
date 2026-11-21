"""L6b: scenes, per-plane statistics and the villa CheckResults from cached per-zone Radiance results."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..contracts import CheckResult
from . import checks
from .metrics import GridStats, grid_stats

NIGHT_LAYERS = ("night", "emergency")


@dataclass
class ClusterRes:
    name: str
    mf: float
    slices: dict
    zones: dict          # zone -> {ab(str): [lux per sensor, MF=1]}
    zone_watts: dict
    zone_layer: dict
    ab: int
    ab2: int | None

    @staticmethod
    def load(path: Path) -> "ClusterRes":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        extra = [int(a) for a in d["params"]["ab_extra"] if a > d["params"]["ab"]]
        return ClusterRes(d["cluster"], d["mf"], {k: tuple(v) for k, v in d["slices"].items()}, d["zones"],
                          d["zone_watts"], d["zone_layer"], d["params"]["ab"], max(extra) if extra else None)

    def values(self, plane: str, levels: dict, *, ab: int | None = None, direct: bool = False) -> list[float]:
        a = 0 if direct else (ab if ab is not None else self.ab)
        lo, hi = self.slices[plane]
        out = [0.0] * (hi - lo)
        for z, f in levels.items():
            if f and z in self.zones:
                for i, v in enumerate(self.zones[z][str(a)][lo:hi]):
                    out[i] += f * v
        return [v * self.mf for v in out]

    def stats(self, plane: str, levels: dict, **kw) -> GridStats:
        return grid_stats(self.values(plane, levels, **kw))


def full_levels(res: ClusterRes) -> dict:
    """Every functional zone at 100 %, night/emergency zones off."""
    return {z: (0.0 if res.zone_layer[z] in NIGHT_LAYERS else 1.0) for z in res.zones}


def scene_levels(res: ClusterRes, table: dict, scene: str) -> dict:
    """Levels for a scene from the design's SCENES table: {scene: {zone_suffix_or_'*layer': level}} (missing = 0).
    A key matches a zone when the zone id ends with it ('-DINING-TASK') or equals '*'+layer."""
    spec = table.get(scene, {})
    out = {}
    for z in res.zones:
        lv = 0.0
        for key, val in spec.items():
            if key.startswith("*"):
                if res.zone_layer[z] == key[1:]:
                    lv = val
            elif z.endswith("-" + key.upper()) or z == key.upper():
                lv = val
        out[z] = lv
    return out


def plane_rows(res: ClusterRes, planes: list, scenes: dict) -> list[dict]:
    """One row per plane in the scene that owns its card, plus the full scene for reference."""
    rows = []
    for p in planes:
        if p.id not in res.slices:
            continue
        own = scene_levels(res, scenes, p.scene) if p.scene in scenes else full_levels(res)
        st = res.stats(p.id, own)
        full = res.stats(p.id, full_levels(res))
        d = res.stats(p.id, own, direct=True)
        conv = None
        if res.ab2:
            conv = st.em / res.stats(p.id, own, ab=res.ab2).em - 1.0 if res.stats(p.id, own, ab=res.ab2).em else None
        rows.append({"plane": p.id, "room": p.room, "what": p.what, "card": p.card, "target": p.target, "gauge": p.gauge,
                     "scene": p.scene, "em": st.em, "emin": st.emin, "emax": st.emax, "u0": st.u0, "max_avg": st.max_avg,
                     "ratio": st.em / p.target, "full_em": full.em, "direct_em": d.em, "n": st.n, "convergence": conv})
    return rows


def results_for(rows: list[dict], tag: str) -> list[CheckResult]:
    out = []
    for r in rows:
        subj = "%s/%s/%s" % (tag, r["plane"], r["scene"])
        st = GridStats(r["n"], r["em"], r["emin"], r["emax"], r["u0"], r["max_avg"],
                       (r["em"] / r["emin"]) if r["emin"] > 0 else float("inf"))
        out.append(checks.check_la1(subj, r["em"], r["target"], gauge=r["gauge"]))      # room planes: average must reach the card
        if r["gauge"] == "average":
            out.append(checks.check_la2(subj, r["em"], r["target"]))
        out += checks.check_la3(subj, st)
    return out
