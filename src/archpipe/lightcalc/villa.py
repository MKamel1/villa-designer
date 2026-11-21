"""L6b: villa-wide lighting calculation. Turns the authored scheme (`concept.villa_lighting.design`) into Radiance jobs.

One Radiance job per open-plan cluster (rooms joined without a wall share one volume, so inter-reflection is not
overstated by closing each room), one octree per control zone (so every scene is an exact linear recombination), task
planes and room planes as sensor grids. Zones are room x layer (or an explicit `extra["zone"]` suffix).

Stated limits: furniture, pendant bodies and door/window openings are not in the Radiance scene (no shadows, no daylight,
walls closed on the cluster outline only). Reflectances are the render's own materials (wall 0.80, ceiling 0.85,
floor 0.33; ASSUMED finishes). Dimming is linear. Generic photometry is named as such wherever it is used.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from .direct import Placement
from .geometry import Point
from .radjob import RadJob, RadParams, Room, execute
from .roomcalc import RoomCalc, TaskPlane
from . import synth

ROOT = Path(__file__).resolve().parents[3]
LEVEL_Z = {"B": -3.0, "GF": 0.0}
RHO = {"wall": 0.80, "ceiling": 0.85, "floor": 0.33}
MF = 0.8
ASSUMED_LM_PER_W = 90.0            # ASSUMED efficacy of generic (unspecified) LED fittings, for the zone watts
PROJECT_EDGE = 0.30                 # strip sample pitch in the calc (m)

# Open-plan clusters (villa_furnish._cluster, which L2 uses): name -> member rooms
CLUSTERS = {
    "B-open": ["lounge", "lounge-nook", "stair-b", "hall-b", "entry-b", "family", "kitchen", "kitchen-island", "dining",
               "dining-side", "living", "bar-alcove"],
    "B-pantry": ["pantry"], "B-store": ["store-ramp"], "B-cinema": ["cinema"], "B-guest-wc": ["guest-wc"],
    "B-dirty-kitchen": ["dirty-kitchen"],
    "GF-circulation": ["corridor", "gallery-end", "landing-gf", "stair-gf", "study-game"],
    "GF-kids-a": ["kids-a"], "GF-kids-b": ["kids-b"], "GF-family-bath": ["family-bath"],
    "GF-parents-bed": ["parents-bed", "parents-entry"], "GF-parents-dressing": ["parents-dressing", "parents-dressing-ext"],
    "GF-parents-ensuite": ["parents-ensuite"],
}
CEILING_OVERRIDE = {"B-open": 2.8}       # the lounge and living coves rise to the 2.80 m slab; the rest is 2.70 m


def cluster_of(room: str) -> str:
    for k, v in CLUSTERS.items():
        if room in v:
            return k
    raise KeyError(room)


# ------------------------------------------------------------------ geometry helpers
def union_rects(rects: list[tuple[float, float, float, float]]) -> list[Point]:
    """Outline of a union of axis-aligned rectangles that form one simply connected region (CCW, collinear points merged)."""
    xs = sorted({round(v, 6) for r in rects for v in (r[0], r[2])})
    ys = sorted({round(v, 6) for r in rects for v in (r[1], r[3])})

    def filled(i, j):
        if i < 0 or j < 0 or i >= len(xs) - 1 or j >= len(ys) - 1:
            return False
        cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
        return any(r[0] <= cx <= r[2] and r[1] <= cy <= r[3] for r in rects)

    edges = {}
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            if not filled(i, j):
                continue
            x0, x1, y0, y1 = xs[i], xs[i + 1], ys[j], ys[j + 1]
            if not filled(i, j - 1):
                edges[(x0, y0)] = (x1, y0)
            if not filled(i + 1, j):
                edges[(x1, y0)] = (x1, y1)
            if not filled(i, j + 1):
                edges[(x1, y1)] = (x0, y1)
            if not filled(i - 1, j):
                edges[(x0, y1)] = (x0, y0)
    start = min(edges)
    loop, cur = [start], edges[start]
    while cur != start:
        loop.append(cur)
        cur = edges[cur]
    out = []
    for k, p in enumerate(loop):          # drop collinear vertices
        a, b = loop[k - 1], loop[(k + 1) % len(loop)]
        if abs((p[0] - a[0]) * (b[1] - p[1]) - (p[1] - a[1]) * (b[0] - p[0])) > 1e-9:
            out.append(p)
    return out


@dataclass
class Plane:
    id: str
    room: str
    polygon: tuple
    z: float
    card: str
    target: float
    gauge: str = "average"       # 'average' (+/-10 %) | 'minimum'
    scene: str = "Day"           # the scene that owns this card (LA10)
    what: str = ""
    spacing: float | None = None


# ------------------------------------------------------------------ fixtures -> placements
def zone_id(f) -> str:
    from ..concept.villa_lighting import zone_id as z
    return z(f)


def zone_layer(f) -> str:
    from ..concept.villa_lighting import zone_layer as z
    return z(f)


def hemisphere_ies(lm: float, name: str = "hemi") -> str:
    """Constant intensity lm / 2 pi over the hemisphere around the aim axis, zero behind (wall-mounted opal fittings)."""
    angles = [float(a) for a in list(range(0, 90, 5)) + [89, 90] + list(range(95, 181, 5))]
    angles = sorted(set(angles))
    i0 = lm / (2 * math.pi)
    cd = [i0 if a < 90 else 0.0 for a in angles]
    lines = ["IESNA:LM-63-2002", "[TEST] archpipe hemisphere", "[MANUFAC] GENERIC (not a product)",
             "[LUMINAIRE] %s hemisphere %d lm" % (name, lm), "TILT=NONE", "1 %.3f 1 %d 1 1 2 0 0 0" % (lm, len(angles)),
             "1 1 0", " ".join("%.1f" % a for a in angles), "0.0", " ".join("%.3f" % c for c in cd)]
    return "\n".join(lines) + "\n"


def _generic_text(rec, lm: float, name: str) -> str:
    from ..concept.villa_lighting import generic_ies
    spec = rec.definition.spec
    kind = rec.definition.kind
    mount = rec.mount
    if kind == "PEN-LIN":
        return generic_ies(lm, 120, name)         # Lambertian strip: what the render emits (truth probe, 343 lx), not cos^2
    if mount == "strip":
        return generic_ies(lm, 120, name)
    beam = spec.get("beam")
    if beam is None:
        return hemisphere_ies(lm, name) if mount in ("wall", "wall-marker") else generic_ies(lm, None, name)
    return generic_ies(lm, beam, name)


def fixture_placements(f) -> list[Placement]:
    """Analytic/Radiance sources for one fixture: one point for a spot, 0.3 m samples for a strip, 8 for the pendant."""
    rec = f.record
    zone, layer = zone_id(f), zone_layer(f)
    x, y, z = rec.position
    aim = tuple(rec.aim)
    if rec.product:
        from ..photometry import load as load_ies
        prod = dict(rec.product)
        pho = load_ies(prod["ies"])
        scale = rec.flux_lm / pho.integrated_flux()
        watts = float(prod.get("watts") or 0.0) * f.extra.get("dimmer", 1.0)
        return [Placement(f.id, pho, (x, y, z), aim=aim, dim=scale, zone=zone, layer=layer, watts=watts,
                          meta={"ies_path": prod["ies"], "generic": False, "kind": f.kind})]
    out = []
    if rec.length and rec.length > 0:
        n = 8 if f.kind == "PEN-LIN" else max(1, int(round(rec.length / PROJECT_EDGE)))
        for k in range(n):
            t = (k + 0.5) / n - 0.5
            pos = tuple(c + a * t * rec.length for c, a in zip((x, y, z), rec.along))
            lm = rec.flux_lm / n
            text = _generic_text(rec, lm, f.kind + "-part")
            out.append(Placement("%s#%d" % (f.id, k), synth.load_text(text, f.kind + "-part"), pos, aim=aim, zone=zone,
                                 layer=layer, watts=rec.flux_lm / n / ASSUMED_LM_PER_W,
                                 meta={"ies_text": text, "generic": True, "kind": f.kind, "parent": f.id}))
        return out
    text = _generic_text(rec, rec.flux_lm, f.kind)
    return [Placement(f.id, synth.load_text(text, f.kind), (x, y, z), aim=aim, zone=zone, layer=layer,
                      watts=rec.flux_lm / ASSUMED_LM_PER_W,
                      meta={"ies_text": text, "generic": True, "kind": f.kind})]


# ------------------------------------------------------------------ parallel run script
class ParRadJob(RadJob):
    """RadJob whose rtrace lines run in parallel (xargs -P), 4 threads each: the per-zone octrees are independent."""

    def prepare(self, workdir):
        path = super().prepare(workdir)
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        head = [l for l in lines if not l.startswith("rtrace") and l != "echo DONE > done.flag"]
        rt = [l.replace("-n %d" % self.params.workers, "-n 2") for l in lines if l.startswith("rtrace")]
        Path(path).with_name("rt.cmds").write_text("\n".join(rt) + "\n", encoding="utf-8", newline="\n")
        body = head + ["xargs -P 14 -d '\\n' -I{} sh -c '{}' < rt.cmds", "echo DONE > done.flag"]
        Path(path).write_text("\n".join(body) + "\n", encoding="utf-8", newline="\n")
        return path


# ------------------------------------------------------------------ the villa model
class Villa:
    """Everything the lighting calculation needs, built once from the design function."""

    def __init__(self, fixtures=None, lay=None):
        from ..concept import villa_furnish as F, villa_r11 as R, villa_lighting as VL
        self.F, self.VL = F, VL
        self.lay = lay or R.design("D1")
        self.fixtures = fixtures if fixtures is not None else VL.design(self.lay)
        self.items = {i["id"]: i for i in F.layout(self.lay)}
        self.fp = {k: F.footprint(v) for k, v in self.items.items()}
        self.rc = {k: F.clear_rect(self.lay, k) for k in self.lay["rooms"]}
        self.placements = []
        for f in self.fixtures:
            self.placements += fixture_placements(f)

    # -- geometry
    def cluster_room(self, name: str) -> Room:
        rooms = CLUSTERS[name]
        level = self.lay["rooms"][rooms[0]]["level"]
        poly = union_rects([self.rc[r] for r in rooms])
        floor = LEVEL_Z[level]
        ceil = floor + CEILING_OVERRIDE.get(name, self._ceiling(rooms[0]))
        top = max((p.position[2] for p in self.cluster_placements(name) if p.meta.get("kind") != "PEN-GLOBE"), default=ceil)
        ceil = max(ceil, top + 0.01)          # a sloped soffit (cinema, store) can sit above the centre value: keep sources inside
        return Room(tuple(poly), floor, ceil, RHO["floor"], RHO["wall"], RHO["ceiling"])

    def _ceiling(self, room: str) -> float:
        r = self.rc[room]
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        lv = self.lay["rooms"][room]["level"]
        return self.VL.ceiling_z(lv, cx, room, cy, self.lay) - LEVEL_Z[lv]

    def cluster_placements(self, name: str) -> list[Placement]:
        rooms = set(CLUSTERS[name])
        by_id = {f.id: f for f in self.fixtures}
        out = []
        for p in self.placements:
            fid = p.meta.get("parent") or p.id
            if by_id[fid].room in rooms:
                out.append(p)
        return out

    # -- planes
    def planes(self) -> list[Plane]:
        from .villa_planes import build_planes
        return build_planes(self)

    def calc(self, name: str, planes: list[Plane], params: RadParams | None = None, fast: bool = False) -> RoomCalc:
        mine = [p for p in planes if cluster_of(p.room) == name]
        tps = [TaskPlane(p.id, tuple(p.polygon), p.z, p.target, p.gauge, p.spacing) for p in mine]
        return RoomCalc(name, self.cluster_room(name), self.cluster_placements(name), tps,
                        params or RadParams(ab=6, ab_extra=() if fast else (12,), workers=4), mf=MF)


def run_cluster(calc: RoomCalc, workdir: Path, host: str | None = None, reuse: bool = False):
    if reuse:
        calc.load_results(workdir)
        return calc
    job = ParRadJob(calc.name, calc.room, calc.placements, calc.sensors(), calc.params)
    import os
    local = os.environ.get("ARCHPIPE_L6_LOCAL")           # set on the workstation itself: run rtrace in place, no ssh
    calc.results = execute(job, workdir, host=None if local else (host or "ai-workstation"), timeout=3600)
    return calc
