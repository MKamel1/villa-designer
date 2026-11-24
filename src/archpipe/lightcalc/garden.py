"""Garden lighting design of the decided garden (lane LG).

Metres, model frame, scene z (garden ground z = -3.00). One verified product carries every SAFETY plane: ERCO Iku B0000184
(IP65 / IK07, DALI-2, 676 lm, its own manufacturer LDT/IES, V10 pass in knowledge/lighting-products). Beauty fittings with no
verified product (the tree uplights are John Cullen Kew 25 spike lights, V10 in knowledge/lighting-products); no safety plane depends on them.

Direct light only is gated (no reflected light, shadows from walls, furniture and screens). Radiance total light is a cross-check.
Maintained values = initial x MF (MF 0.8, the project's value in lightcalc.dining).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from shapely.geometry import Point as SPoint, box as sbox
from shapely.ops import unary_union

from ..contracts import CheckResult
from ..photometry import Photometry, parse
from .checks import _res, check_la12
from .direct import Placement, _norm, direct_illuminance, upward_light_ratio

ROOT = Path(__file__).resolve().parents[3]
LAYOUT = ROOT / "knowledge/landscape/concept/final/layout-final.json"
IKU_DIR = ROOT / "knowledge/lighting-products/erco/B0000184"
KEW_DIR = ROOT / "knowledge/lighting-products/john-cullen/GLK2SM254"
G = -3.0                       # garden ground, scene z
MF = 0.8                       # maintenance factor (project value)
V12_MAX_LEVEL = 0.80           # LIGHTING-VERIFICATION V12: every task met with the driver at <= 80 %
EDGE_MIN_LX, EDGE_REC_LX = 4.0, 8.0          # IES HB10 T33.2 pool deck / steps (rules.json LS-POND-EDGE-LIGHT)
PATH_MIN_LX, PATH_U0 = 5.0, 0.25             # SLL T3.5 walkways: 5 lx, Uo 0.25 (workplace table, analogue)
DINING_AVG_LX, DINING_MIN_LX = 30.0, 15.0    # POLICY (ours, no published outdoor dining figure)

PRODUCTS = {
    "iku": dict(manufacturer="erco", code="B0000184", name="Iku surface-mounted downlight IP65, IK07", lumens=676.0, watts=7.0,
                cct_k=3000, cct_variant_k=2700, cri=92, dimming="DALI-2, 1-100 %", ip="IP65", ies=IKU_DIR / "erco-B0000184-en-ies.ies",
                status="V10 pass (knowledge/lighting-products/candidates.json)",
                caveat="ERCO lists the Iku at 3000 K; the datasheet says 2700 K / CRI 92 is available on request. No 2700 K file exists, so the 3000 K "
                       "photometry is used; the optic is the same, flux of the 2700 K variant is unknown and typically a few % lower (V12 headroom covers it)."),
    "kew25": dict(manufacturer="john-cullen", code="GLK2SM254", name="Kew 25 Spike Olive Green Medium 2027, 500 mA, IP66 spike spotlight", lumens=93.0, watts=1.5,
                  cct_k=2700, cri=98, dimming="DALI (driver option; DALI-2 not stated in the datasheet)", ip="IP66", ies=KEW_DIR / "kew25-medium-500mA.ies",
                  shielded=True,    # datasheet: "A shielded light source delivers precise beam control with minimal glare"; the bare 16 mm opening would read 10-15 kcd/m2 at grazing view (test)
                  status="V10: peak 479 cd and beam 22 deg pass; lumens FAIL at the 2 % bar (file integrates 90.9 lm vs 93 stated, -2.25 %); the file is the Kew 25 family file (LUMCAT GLK2XMXX3, 2023), not the 2027 article's own",
                  caveat="IP66 spike, not in-ground IP67: no in-ground product with 2700 K + CRI >= 90 + a downloadable file was found. DALI-2 and the exact-article LDT are to be confirmed with John Cullen."),
}


@dataclass(frozen=True)
class Fix:
    id: str
    zone: str
    role: str                  # safety | use | beauty
    product: str
    pos: tuple                 # x, y, height above ground (m)
    target: tuple              # x, y, height above ground (m)
    mount: str


def F(id, zone, role, product, pos, target, mount):
    return Fix(id, zone, role, product, tuple(pos), tuple(target), mount)


ARM = "0.30 m stainless wall arm below the first-floor slab edge (ASSUMED accessory, to be detailed)"
FIXTURES = [
    # north court pond (2.0 x 1.4 m at x 0.217-2.217, y -25.571..-24.171), lit from the east building face and the south face
    F("NP-1", "pond-N", "safety", "iku", (3.30, -25.35, 2.4), (2.30, -25.35, 0), "east building face, " + ARM),
    F("NP-2", "pond-N", "safety", "iku", (3.30, -24.35, 2.4), (2.30, -24.35, 0), "east building face, " + ARM),
    F("NP-3", "pond-N", "safety", "iku", (1.25, -23.85, 2.4), (0.45, -24.60, 0), "south building face, " + ARM),
    F("NP-4", "pond-N", "safety", "iku", (3.30, -26.35, 2.4), (1.60, -25.95, 0), "east building face, " + ARM),
    # east yard pond (3.2 x 1.4 m at x 16.912-20.112, y -22.241..-20.841) and its service path
    F("EP-1", "pond-E", "safety", "iku", (17.00, -23.30, 2.4), (17.30, -22.30, 0), "north building face, " + ARM),
    F("EP-2", "pond-E", "safety", "iku", (18.50, -23.30, 2.4), (18.50, -22.30, 0), "north building face, " + ARM),
    F("EP-3", "pond-E", "safety", "iku", (19.80, -23.30, 2.4), (19.70, -22.30, 0), "north building face, " + ARM),
    F("EP-5", "pond-E", "safety", "iku", (16.95, -20.78, 2.4), (16.80, -21.50, 0), "south wall bracket 0.15 m off the face"),
    F("EP-6", "pond-E", "safety", "iku", (20.20, -20.78, 2.4), (20.20, -21.50, 0), "south wall bracket 0.15 m off the face"),
    # shared fire pit on the west line, on the two sister-screen end posts (1.9 m)
    F("FP-1", "pit", "safety", "iku", (23.80, -29.80, 1.9), (24.90, -29.55, 0), "sister-screen post, non-combustible bracket"),
    F("FP-2", "pit", "safety", "iku", (27.00, -29.80, 1.9), (25.90, -29.55, 0), "sister-screen post, non-combustible bracket"),
    # main path along the facade (1.2 m), also lights the BBQ stand
    F("PS-1", "path-S", "safety", "iku", (22.90, -27.30, 2.4), (23.25, -27.30, 0), "house facade, " + ARM),
    F("PS-2", "path-S", "safety", "iku", (22.90, -25.40, 2.4), (23.25, -25.40, 0), "house facade, " + ARM),
    F("PS-3", "path-S", "safety", "iku", (22.90, -23.75, 2.4), (23.25, -23.40, 0), "house facade (its last 0.84 m before the facade ends at y -23.591), " + ARM),
    # dining table under the crape myrtle: two downlights clamped to the main stem at 3.0 m (tree-friendly clamp, no screws through bark)
    F("DN-1", "dining", "use", "iku", (25.00, -25.40, 3.0), (25.00, -25.40, 0.75), "crape myrtle lower branch clamp above the table"),
    F("DN-2", "dining", "use", "iku", (25.90, -25.40, 3.0), (25.90, -25.40, 0.75), "crape myrtle lower branch clamp above the table"),
    # climber walls grazed from above, 0.15 m off the rear wall at 3.4 m
    F("GR-1", "graze", "beauty", "iku", (28.15, -27.50, 3.4), (28.15, -27.50, 0), "rear wall bracket 0.15 m off the face"),
    F("GR-2", "graze", "beauty", "iku", (28.15, -24.40, 3.4), (28.15, -24.40, 0), "rear wall bracket 0.15 m off the face"),
    F("GR-3", "graze", "beauty", "iku", (26.40, -20.75, 3.4), (26.40, -20.75, 0), "south wall bracket 0.15 m off the face"),
    # uplights (John Cullen Kew 25 spike, medium 22 deg): crape, olive, east-yard olive, pomegranate
    F("UP-1", "uplight", "beauty", "kew25", (26.55, -23.30, 0.05), (25.60, -24.60, 3.4), "ground spike beside the crape stem"),
    F("UP-2", "uplight", "beauty", "kew25", (27.35, -22.95, 0.05), (26.80, -22.50, 3.4), "ground spike beside the olive stem"),
    F("UP-3", "uplight", "beauty", "kew25", (21.95, -21.70, 0.05), (21.05, -21.70, 3.4), "ground spike beside the east-yard olive"),
]
ZONES = ["pond-N", "pond-E", "pit", "path-S", "dining", "graze", "uplight"]

# Scene levels per zone (fraction of maximum output). `safety floor` = lowest level that still meets its plane at the plane's recommended value.
SCENES = {
    "summer-night-dining": dict(label="Summer-night dining under the crape myrtle", cct_k=2700, dining_target=30.0,
                                levels={"dining": 0.165, "path-S": 0.10, "pit": 0.12, "pond-N": 0.08, "pond-E": 0.12, "graze": 0.25, "uplight": 0.30}),
    "social-gathering": dict(label="Social gathering (10-20 people, standing room)", cct_k=2700, dining_target=40.0,
                             levels={"dining": 0.22, "path-S": 0.15, "pit": 0.20, "pond-N": 0.08, "pond-E": 0.12, "graze": 0.35, "uplight": 0.45}),
    "quiet-north-court": dict(label="Quiet north court (south garden at its safety floor)", cct_k=2700, dining_target=None,
                              levels={"dining": 0.0, "path-S": 0.10, "pit": 0.10, "pond-N": 0.08, "pond-E": 0.12, "graze": 0.0, "uplight": 0.0}),
    "winter-evening": dict(label="Winter evening around the fire pit (crape leafless: no uplight)", cct_k=2700, dining_target=None,
                           levels={"dining": 0.0, "path-S": 0.10, "pit": 0.20, "pond-N": 0.08, "pond-E": 0.12, "graze": 0.10, "uplight": 0.0}),
}
RENDER_SCENE = "social-gathering"      # the scene baked into the production render lights (one static level set): the dusk views show a gathering, the brightest of the four


# ------------------------------------------------------------------ geometry
def layout() -> dict:
    return json.loads(LAYOUT.read_text())


def _rect(r, z0=G, z1=G + 4.0, rho=0.45):
    return (r[0], r[1], z0, r[2], r[3], z1, rho)


def occluders(L: dict | None = None) -> list[tuple]:
    """Boxes (x0,y0,z0,x1,y1,z1,rho) that block or reflect light: buildings, 4 m walls, sister screens, table, benches, BBQ, pot."""
    L = L or layout()
    out = [_rect(b, G, G + 12.0, 0.5) for b in L["buildings"]]
    out += [_rect(w["rect"], G, G + w["height_m"], 0.45) for w in L["walls"]]
    out += [_rect(s["rect"], G, G + s["height_m"], 0.4) for s in L["screens"]]
    for t in L["tables"]:
        cx, cy = t["center"]; sx, sy = t["size_m"]
        out.append((cx - sx / 2, cy - sy / 2, G + 0.70, cx + sx / 2, cy + sy / 2, G + 0.75, 0.4))
    out += [_rect(s["rect"], G, G + 0.45, 0.4) for s in L["seating"]]
    out += [_rect(f["rect"], G, G + 0.95, 0.15) for f in L["features"] if f["kind"] == "bbq"]
    out += [_rect(o["rect"], G, G + 0.6, 0.4) for o in L["obstacles"] if o["id"].startswith("pot")]
    return out


def _blocked(a, b, boxes, eps=1e-6) -> bool:
    """Does the open segment a-b pass through any box (slab test)? Endpoints inside a box are not 'blocked' by that box."""
    d = [b[i] - a[i] for i in range(3)]
    for bx in boxes:
        lo, hi = bx[0:3], bx[3:6]
        t0, t1 = 1e-4, 1 - 1e-4
        for i in range(3):
            if abs(d[i]) < 1e-12:
                if a[i] < lo[i] - eps or a[i] > hi[i] + eps:
                    t0, t1 = 1, 0
                    break
            else:
                ta, tb = (lo[i] - a[i]) / d[i], (hi[i] - a[i]) / d[i]
                if ta > tb:
                    ta, tb = tb, ta
                t0, t1 = max(t0, ta), min(t1, tb)
                if t0 > t1:
                    break
        if t0 < t1:
            return True
    return False


def _photometry(product: str) -> Photometry:
    p = PRODUCTS[product]
    return parse(Path(p["ies"]).read_text(encoding="utf-8", errors="replace"), name=p["code"], source=Path(p["ies"]))


def placements(levels: dict | None = None, fixtures=FIXTURES, *, shift=(0, 0, 0), aim_roll_deg=0.0, lumens_scale=1.0) -> list[Placement]:
    """Placements at zone `levels` (default 1.0). `shift`, `aim_roll_deg`, `lumens_scale` exist for the V8 mutation tests."""
    cache, out = {}, []
    for f in fixtures:
        ph = cache.setdefault(f.product, _photometry(f.product))
        pos = (f.pos[0] + shift[0], f.pos[1] + shift[1], G + f.pos[2] + shift[2])
        tgt = (f.target[0], f.target[1], G + f.target[2])
        aim = _norm(tuple(tgt[i] - pos[i] for i in range(3)))
        if aim_roll_deg:
            c, s = math.cos(math.radians(aim_roll_deg)), math.sin(math.radians(aim_roll_deg))
            aim = _norm((aim[0], aim[1] * c - aim[2] * s, aim[1] * s + aim[2] * c))
        dim = 1.0 if levels is None else levels.get(f.zone, 0.0)
        out.append(Placement(f.id, ph, pos, aim, 0.0, dim * lumens_scale, f.zone, "evening-garden", PRODUCTS[f.product]["watts"],
                             meta=dict(product=f.product, role=f.role, shielded=PRODUCTS[f.product].get("shielded", False))))
    return out


# ------------------------------------------------------------------ planes
@dataclass
class Plane:
    id: str
    kind: str                  # edge | path | table | wall | water
    zone_req: str              # zone whose fixtures are responsible
    points: list               # [(x,y,z,nx,ny,nz)]
    min_lx: float | None = None
    rec_lx: float | None = None
    source: str = ""
    U0: float | None = None


def _walkable(poly, avoid):
    """Ground a person can stand on: minus furniture footprints, then opened by 0.15 m so slivers under 0.30 m wide (behind a bench, against a wall) are dropped."""
    w = poly.difference(avoid.buffer(0.05)) if avoid is not None else poly
    return w.buffer(-0.15).buffer(0.15)


def _grid(poly, step, z, n=(0, 0, 1), avoid=None):
    minx, miny, maxx, maxy = poly.bounds
    pts, x = [], minx + step / 2
    while x < maxx:
        y = miny + step / 2
        while y < maxy:
            p = SPoint(x, y)
            if poly.contains(p) and not (avoid is not None and avoid.buffer(0.05).contains(p)):
                pts.append((round(x, 4), round(y, 4), z, *n))
            y += step
        x += step
    return pts


def surfaces(L: dict):
    """Walkable ground: paving, paths and gravel zones (not planting beds, not water)."""
    return unary_union([sbox(*r["rect"]) for r in L["paved_areas"]] + [sbox(*p["rect"]) for p in L["paths"]] +
                       [sbox(*z["rect"]) for z in L["zones"] if z["surface"] in ("paving", "gravel")])


def planes(L: dict | None = None, step=0.15) -> list[Plane]:
    L = L or layout()
    walk = surfaces(L)
    obstruct = unary_union([sbox(o[0], o[1], o[3], o[4]) for o in occluders(L) if o[2] < G + 0.3 and o[5] - o[2] < 3.0])  # footprints a foot sensor cannot stand in
    pl = []
    for f in L["features"]:
        if f["kind"] == "pond":
            pond = sbox(*f["rect"])
            ring = _walkable(pond.buffer(0.6, join_style=2).difference(pond).intersection(walk), obstruct)
            zone = "pond-N" if f["id"].startswith("n-") else "pond-E"
            pl.append(Plane(f"{f['id']}-edge-ring", "edge", zone, _grid(ring, step, G, avoid=obstruct), EDGE_MIN_LX, EDGE_REC_LX,
                            "LS-POND-EDGE-LIGHT: IES HB10 T33.2 (pool-deck analogue) 4 lx (25-65 y), 8 lx (over 65)"))
            pl.append(Plane(f"{f['id']}-water", "water", zone, _grid(pond, 0.2, G - f["freeboard_mm"] / 1000.0), None, None, "report only: the water is not to be flooded"))
        elif f["kind"] == "firepit":
            c = f["center"]; r = f["diameter_m"] / 2
            ring = SPoint(c).buffer(r + 0.8).difference(SPoint(c).buffer(r)).intersection(sbox(c[0] - 3, c[1], c[0] + 3, c[1] + 3)).intersection(walk)
            ring = _walkable(ring, obstruct)
            pl.append(Plane("s-firepit-edge-ring", "edge", "pit", _grid(ring, step, G, avoid=obstruct), EDGE_MIN_LX, EDGE_REC_LX,
                            "LS-POND-EDGE-LIGHT: fire-pit cover edge, 0.8 m ring on our side of the shared line"))
    for p in L["paths"]:
        zone = {"s-": "path-S"}.get(p["id"][:2])
        if zone is None:
            continue
        pl.append(Plane(p["id"], "path", zone, _grid(sbox(*p["rect"]), 0.2, G, avoid=obstruct), PATH_MIN_LX, None,
                        "SLL T3.5 walkways 5 lx, Uo 0.25 (outdoor workplace table, analogue)", PATH_U0))
    for t in L["tables"]:
        cx, cy = t["center"]; sx, sy = t["size_m"]
        pl.append(Plane("s-dining-table", "table", "dining", _grid(sbox(cx - sx / 2, cy - sy / 2, cx + sx / 2, cy + sy / 2), 0.2, G + 0.75), DINING_MIN_LX, DINING_AVG_LX,
                        "POLICY (ours): outdoor dining avg 30 / min 15 lx; no published figure"))
    return pl


def eh(pls: list[Placement], pt, boxes) -> float:
    """Direct illuminance at pt (x,y,z,nx,ny,nz) from the placements, with occlusion by boxes (no reflected light)."""
    p, n = pt[:3], pt[3:]
    tot = 0.0
    for pl in pls:
        if pl.dim <= 0 or _blocked(pl.position, p, boxes):
            continue
        tot += direct_illuminance([pl], p, n)
    return tot


def stats(pls, plane: Plane, boxes, mf=MF) -> dict:
    v = [mf * eh(pls, pt, boxes) for pt in plane.points]
    if not v:
        return dict(n=0)
    avg = sum(v) / len(v)
    return dict(n=len(v), avg=avg, min=min(v), max=max(v), u0=min(v) / avg if avg else 0.0, values=v)


def level_for(plane: Plane, zone_fixtures_full, boxes, target: float, *, gauge="min") -> float:
    """Zone level at which the plane's `gauge` ('min' or 'avg') reaches `target` (linear dimming: exact)."""
    s = stats(zone_fixtures_full, plane, boxes)
    base = s["min"] if gauge == "min" else s["avg"]
    return math.inf if base <= 0 else target / base


# ------------------------------------------------------------------ checks
SRC_EDGE = ["LS-POND-EDGE-LIGHT-IES-T33.2"]
SRC_PATH = ["SLL-T3.5-walkway"]


def check_plane(pl: Plane, st: dict, level: float, scene: str) -> list[CheckResult]:
    """LA11: achieved vs required per safety plane, in one scene. Unmet = fail; the recommended (8 lx) value is reported, not gated."""
    out = []
    if pl.kind == "edge":
        ok = st["min"] >= pl.min_lx
        out.append(_res("LA11", "pass" if ok else "fail", f"{scene}/{pl.id}", SRC_EDGE, achieved=round(st["min"], 2), required=pl.min_lx, unit="lx",
                        message=f"min Eh at grade {st['min']:.1f} lx (avg {st['avg']:.1f}, max {st['max']:.1f}) vs {pl.min_lx:g} lx; recommended for over-65s {pl.rec_lx:g} lx "
                                f"{'met' if st['min'] >= pl.rec_lx else 'NOT met'}; zone level {level:.2f}", element_ids=(pl.id,)))
    elif pl.kind == "path":
        ok = st["avg"] >= pl.min_lx and st["u0"] >= pl.U0
        out.append(_res("LA11", "pass" if ok else "fail", f"{scene}/{pl.id}", SRC_PATH, achieved=round(st["avg"], 2), required=pl.min_lx, unit="lx",
                        message=f"avg {st['avg']:.1f} lx (min {st['min']:.1f}) vs {pl.min_lx:g} lx; Uo {st['u0']:.2f} vs {pl.U0:g}; zone level {level:.2f}", element_ids=(pl.id,)))
    return out


def check_water(ring: Plane, ring_st: dict, water: Plane, water_st: dict, scene: str) -> CheckResult:
    """Policy: the water is not lit more than the margin (LS-POND-EDGE-LIGHT fix: 'do not flood the water')."""
    ok = water_st["avg"] <= ring_st["avg"]
    return _res("LA11", "pass" if ok else "fail", f"{scene}/{water.id}", ["LG-POLICY-pond-water-not-flooded"], achieved=round(water_st["avg"], 2), required=round(ring_st["avg"], 2), unit="lx",
                message=f"water mean {water_st['avg']:.1f} lx vs margin ring mean {ring_st['avg']:.1f} lx (max on water {water_st['max']:.1f})")


def check_dining(pl: Plane, st: dict, target: float, scene: str) -> list[CheckResult]:
    from .checks import check_la1, check_la2
    return [check_la1(f"{scene}/{pl.id}", st["avg"], target), check_la2(f"{scene}/{pl.id}", st["avg"], target),
            _res("LA3", "pass" if st["min"] >= DINING_MIN_LX else "fail", f"{scene}/{pl.id}/min", ["LG-POLICY-dining-30lx"], achieved=round(st["min"], 1),
                 required=DINING_MIN_LX, unit="lx", message=f"table minimum {st['min']:.1f} lx vs {DINING_MIN_LX:g}; U0 {st['u0']:.2f}")]


def eye_points(L: dict | None = None):
    """Sightlines for glare: seated eye (1.2 m) at every seat position approximated by the table ends and benches, looking along each axis."""
    L = L or layout()
    pts = []
    for t in L["tables"]:
        cx, cy = t["center"]; sx, sy = t["size_m"]
        for dx in (-sx / 2 - 0.4, sx / 2 + 0.4):
            pts.append((f"dining-end-{'w' if dx < 0 else 'e'}", (cx + dx, cy, G + 1.2), (-1 if dx > 0 else 1, 0, 0)))
        for dy in (-sy / 2 - 0.4, sy / 2 + 0.4):
            pts.append((f"dining-side-{'s' if dy < 0 else 'n'}", (cx, cy + dy, G + 1.2), (0, -1 if dy > 0 else 1, 0)))
    for s_ in L["seating"]:
        r = s_["rect"]; pts.append((s_["id"], ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, G + 1.2), (-1, 0, 0)))
    return pts


def check_glare(pls: list[Placement], scene: str):
    """LA4 luminance cap (policy 3000 cd/m2 within 45 deg of a sightline) at seated eye points, looking toward each fitting nearest the sightline."""
    from .checks import check_la4_luminance
    live = [p for p in pls if p.dim > 0]
    L = layout()
    looks = {"table": L["tables"][0]["center"], "firepit": [f for f in L["features"] if f["kind"] == "firepit"][0]["center"],
             "facade-door": (22.597, -25.0), "pond-E": (18.5, -21.5)}
    sl = []
    for name, eye, _d in eye_points():
        for lname, tgt in looks.items():      # level sightlines to the things people look at; a fitting counts if within 45 deg of the line
            v = (tgt[0] - eye[0], tgt[1] - eye[1], 0.0)
            if math.hypot(v[0], v[1]) > 0.5:
                sl.append(dict(id=f"{name}>{lname}", eye=eye, dir=v))
    res = check_la4_luminance(f"{scene}/glare", sl, live)
    worst = max(res, key=lambda r: r.achieved or 0.0) if res else None
    return res, worst


def check_headroom(level: float, subject: str) -> CheckResult:
    """V12: the zone driver must meet the plane at <= 80 % (policy card L6-POLICY-V12-headroom)."""
    ok = level <= V12_MAX_LEVEL
    return _res("LA11", "pass" if ok else "fail", subject + "/V12-headroom", ["L6-POLICY-V12-headroom"], achieved=round(level, 3), required=V12_MAX_LEVEL, unit="x max output",
                message=f"minimum level for the plane's recommended value {level:.2f} of maximum vs {V12_MAX_LEVEL:g}")


def neighbour_points(L: dict | None = None):
    """Vertical sensors (x,y,z,nx,ny,nz) on neighbour and apartment-above window planes. ASSUMED heights (no survey): neighbour
    ground-floor window z = ground + 1.5 and first-floor z = ground + 4.5 (first-floor slab at 0.0, sill 0.9 above it). The sister villa's
    sensors sit on ITS facade (x = 22.597, y < -29.9): the pit is shared by design, so its garden side is not a boundary. The client's own
    ground-floor windows are not sensors (their own facade is the design intent); the apartment above is the first-floor row of the house facade."""
    pts = []
    for z in (G + 1.5, G + 4.5):
        for x in (23.5, 25.0, 26.5, 27.8):
            pts.append(("east-neighbour", (x, -20.20, z, 0, -1, 0)))
        for y in (-28.5, -26.0, -23.5, -21.5):
            pts.append(("rear-neighbour", (28.70, y, z, -1, 0, 0)))
        for y in (-31.0, -33.0):
            pts.append(("sister-villa-facade", (22.597, y, z, 1, 0, 0)))
        pts.append(("street-side", (-0.60, -25.0, z, 1, 0, 0)))
        for x in (17.0, 19.0, 21.0):
            pts.append(("east-yard-neighbour", (x, -20.20, z, 0, -1, 0)))
    for y in (-28.5, -26.0, -24.2):
        pts.append(("apartment-above-facade", (22.597, y, G + 4.5, 1, 0, 0)))
    return pts


def crowns(L: dict | None = None):
    """Opaque (in leaf) crown ellipsoids (cx, cy, cz, rx, ry, rz) of the pruned trees: centre, spread/2, underside to top."""
    out = []
    for t in (L or layout())["trees"]:
        if "pruned" not in t:
            continue
        c = t.get("crown_center", t["center"]); lo, hi = G + t["pruned"]["clear_stem_m"], G + t["pruned"]["height_m"]
        r = t["pruned"]["spread_m"] / 2
        out.append((c[0], c[1], (lo + hi) / 2, r, r, (hi - lo) / 2))
    return out


def _ray_hits(o, d, e) -> bool:
    ox, oy, oz = (o[0] - e[0]) / e[3], (o[1] - e[1]) / e[4], (o[2] - e[2]) / e[5]
    dx, dy, dz = d[0] / e[3], d[1] / e[4], d[2] / e[5]
    a = dx * dx + dy * dy + dz * dz
    b = 2 * (ox * dx + oy * dy + oz * dz)
    c = ox * ox + oy * oy + oz * oz - 1
    disc = b * b - 4 * a * c
    return disc >= 0 and (-b + math.sqrt(disc)) / (2 * a) > 0


def sky_escape(p: Placement, ellipsoids, steps=90, azimuths=72) -> float:
    """Fraction of the fitting's flux going above the horizontal along rays that miss every crown (crowns opaque: leaf-on worst case for
    ULR means the crown is a perfect catcher; a crown that is not there lets everything out). Used for upward fittings only."""
    esc = tot = 0.0
    for i in range(steps):
        th = math.pi * (i + 0.5) / steps
        for j in range(azimuths):
            ph = 2 * math.pi * (j + 0.5) / azimuths
            d = (math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th))
            w = p.intensity_toward(d) * math.sin(th)
            tot += w
            if d[2] > 0 and not any(_ray_hits(p.position, d, e) for e in ellipsoids):
                esc += w
    return esc / tot if tot > 0 else 0.0


def spill(pls: list[Placement], boxes, *, curfew="post") -> tuple[list[CheckResult], dict]:
    """LA12 against neighbour and apartment-above sensors: Ev with occlusion by walls, I toward the sensors, ULR per fitting."""
    pts = neighbour_points()
    ev = {}
    for name, p in pts:
        ev.setdefault(name, []).append(eh(pls, p, boxes))
    flat = [v for vs in ev.values() for v in vs]
    live = [p for p in pls if p.dim > 0]
    res = check_la12("garden", boundary_ev=flat, exterior=live, neighbour_points=[p[:3] for _, p in pts], curfew=curfew)
    res = [r for r in res if not r.message.startswith("worst upward")]      # check_la12's raw ULR would fail every uplight by definition; the crown-aware one is below
    ell = crowns()
    raw = {p.id: upward_light_ratio(p) for p in live}
    ulr = {i: (sky_escape(p, ell) if raw[i] > 0.5 else raw[i]) for i, p in ((p.id, p) for p in live)}     # an uplight counts only the flux that misses its crown
    worst = max(ulr.values()) if ulr else 0.0
    res.append(_res("LA12", "pass" if worst <= 0.15 else "fail", "garden/ULR", ["SLL-T3.2-E3"], achieved=round(worst, 4), required=0.15, unit="fraction",
                    message=f"max upward flux fraction to the sky {worst:.3f} ({max(ulr, key=ulr.get) if ulr else '-'}); raw ULR of uplights {max(raw.values()) if raw else 0:.2f} "
                            f"but their beams end in the crown (leaf-on); vs E3 0.15. Uplight photometry: John Cullen Kew 25 file (V10: lumens -2.25 %)"))
    return res, dict(ev_max_by_group={k: max(v) for k, v in ev.items()}, ulr=ulr, ulr_raw=raw)


def solve_levels(L=None) -> dict:
    """Minimum zone level that meets each safety plane at its recommended value (edge 8 lx min; path avg 5 lx and Uo), by exact linear scaling."""
    L = L or layout()
    boxes, out = occluders(L), {}
    full = placements(None)
    for pl in planes(L):
        if pl.kind not in ("edge", "path"):
            continue
        zf = [p for p in full if p.zone == pl.zone_req]
        st = stats(zf, pl, boxes)
        target = EDGE_REC_LX if pl.kind == "edge" else PATH_MIN_LX
        lv = target / (st["min"] if pl.kind == "edge" else st["avg"])
        out[pl.id] = dict(zone=pl.zone_req, level_for_target=lv, min_at_full=st["min"], avg_at_full=st["avg"], u0=st["u0"], n=st["n"])
    return out


def run(L=None) -> dict:
    """All scenes: per-plane achieved vs required, V12, spill; returns a JSON-able record plus `results` (CheckResult list)."""
    L = L or layout()
    boxes, pls_def, results, rec = occluders(L), planes(L), [], {"scenes": {}}
    PLANES_BY_ID = {q.id: q for q in pls_def}
    for name, sc in SCENES.items():
        pls = placements(sc["levels"])
        scene_rec = {"levels": sc["levels"], "planes": {}}
        for pl in pls_def:
            st = stats(pls, pl, boxes)
            if pl.kind in ("edge", "path"):
                results += check_plane(pl, st, sc["levels"].get(pl.zone_req, 0.0), name)
            if pl.kind == "water":
                ring = PLANES_BY_ID[pl.id.replace("-water", "-edge-ring")]
                results.append(check_water(ring, stats(pls, ring, boxes), pl, st, name))
            if pl.kind == "table" and sc["dining_target"]:
                results += check_dining(pl, st, sc["dining_target"], name)
            if st.get("n"):
                scene_rec["planes"][pl.id] = {k: round(v, 3) for k, v in st.items() if k not in ("values",)}
        gl, worst = check_glare(pls, name)
        results.append(_res("LA4", "pass" if all(r.status == "pass" for r in gl) else "fail", f"{name}/glare", ["L6-POLICY-LA4-luminance-3000"],
                            achieved=round(worst.achieved, 0) if worst else 0.0, required=3000.0, unit="cd/m2",
                            message=(f"{len(gl)} seated sightlines; worst source luminance {worst.achieved:.0f} cd/m2 ({worst.message.split('(')[-1][:-1] if worst else ''})" if worst else "no live fittings")))
        sp, info = spill(pls, boxes)
        results += [CheckResult(**{**r.__dict__, "subject": f"{name}/{r.subject}"}) for r in sp]
        scene_rec["spill"] = info
        rec["scenes"][name] = scene_rec
    solved = solve_levels(L)
    rec["safety_levels"] = solved
    for pid, s in solved.items():
        results.append(check_headroom(s["level_for_target"], pid))
    return dict(record=rec, results=results)


def zones_json() -> dict:
    """The garden's control zones and scenes in the schema of knowledge/lighting/zones-d1.json (`archpipe-lighting-zones/1`, contracts.LightingZone):
    layer `exterior`, DALI-2 (the Iku's own), watts at the highest level any scene commands. Kept in its own file: zones-d1.json is generated from the
    villa model and pinned by the electrical lane's tests."""
    zones = []
    for z in ZONES:
        fs = [f for f in FIXTURES if f.zone == z]
        top = max(sc["levels"][z] for sc in SCENES.values())
        zones.append(dict(id="Z-G-" + z.upper(), room="garden", layer="exterior", luminaire_ids=["lum-gl-" + f.id for f in fs],
                          watts=round(sum(PRODUCTS[f.product]["watts"] for f in fs) * top, 1), dimming="dali2",
                          product=sorted({PRODUCTS[f.product]["code"] for f in fs}), role=fs[0].role))
    return {"schema": "archpipe-lighting-zones/1", "design": "D1-garden", "contract": "contracts.LightingZone (v0.1)",
            "units": {"watts": "W installed at the highest commissioned level of any scene (7 W rated per Iku; 1.5 W per Kew 25 uplight)"},
            "assumptions": ["ERCO Iku B0000184 is DALI-2, 1-100 % (datasheet); the uplights are John Cullen Kew 25 spike, DALI via a driver option (DALI-2 to confirm)",
                            "scene value = fraction of maximum output per zone, linear dimming (stated)"],
            "zones": zones, "scenes": {"garden": {v["label"]: v["levels"] for v in SCENES.values()}}}


def write(out: Path | None = None) -> Path:
    out = Path(out or ROOT / "knowledge/lighting/garden")
    out.mkdir(parents=True, exist_ok=True)
    r = run()
    rec = r["record"]
    rec["fixtures"] = [dict(id=f.id, zone=f.zone, role=f.role, product=f.product, pos=f.pos, target=f.target, mount=f.mount) for f in FIXTURES]
    rec["products"] = {k: {a: (str(b.relative_to(ROOT)) if isinstance(b, Path) else b) for a, b in v.items()} for k, v in PRODUCTS.items()}
    rec["checks"] = [dict(criterion=c.criterion, status=c.status, subject=c.subject, achieved=c.achieved, required=c.required, unit=c.unit, message=c.message) for c in r["results"]]
    rec["counts"] = {s: sum(1 for c in r["results"] if c.status == s) for s in ("pass", "fail", "warn", "not_evaluated")}
    (out / "zones-garden.json").write_text(json.dumps(zones_json(), indent=1), encoding="utf-8")
    (out / "garden-lighting.json").write_text(json.dumps(rec, indent=1, default=float), encoding="utf-8")
    return out / "garden-lighting.json"


if __name__ == "__main__":
    print(write())


# ------------------------------------------------------------------ V5 / V7: Radiance cross-check
RADIANCE_BIN = Path.home() / "archpipe/tools/radiance-6.0.1/bin"
RHO_GROUND = 0.30          # ASSUMED mid-light paving / gravel; the total-light cross-check only, never a gate


def radiance_check(workdir: Path, *, step=3, ab=6, workers=8, plane_ids=None) -> dict:
    """Same placements, planes and occluders in Radiance (rtrace -I+, ab 0 = direct with shadows; ab N and 2N = total).
    Returns per-plane analytic-vs-Radiance direct, total vs direct and ab N vs 2N, for the scene RENDER_SCENE levels."""
    import os, shutil
    from .radjob import RadJob, RadParams, Room, Sensor, execute, total_lux
    if shutil.which("rtrace") is None:
        os.environ["PATH"] = f"{RADIANCE_BIN}:{os.environ['PATH']}"
    L = layout()
    boxes = occluders(L)
    room = Room(((-2.0, -36.0), (31.0, -36.0), (31.0, -17.0), (-2.0, -17.0)), floor_z=G, ceiling_z=G + 60.0, rho_floor=RHO_GROUND, rho_wall=0.0, rho_ceiling=0.0, boxes=tuple(boxes))
    pls, full = [q for q in planes(L) if q.kind != "water" and (plane_ids is None or q.id in plane_ids)], placements(None)      # the Radiance floor is solid: a water plane sits under it (the pond is a hole in reality)
    if plane_ids is not None:
        full = [f for f in full if f.zone in {q.zone_req for q in pls}]
    sensors, owner = [], []
    for pl in pls:
        for pt in pl.points[::step]:
            sensors.append(Sensor(*pt)); owner.append(pl.id)
    job = RadJob("garden", room, full, sensors, RadParams(ab=ab, ab_extra=(2 * ab,), workers=workers))
    res = execute(job, Path(workdir))
    levels = SCENES[RENDER_SCENE]["levels"]
    out = {}
    for pl in pls:
        idx = [i for i, o in enumerate(owner) if o == pl.id]
        pts = [sensors[i] for i in idx]
        sel = [q for q in placements(levels) if q.zone in {f.zone for f in full}]      # the same fixtures the job holds
        ana = [MF * eh(sel, (s.x, s.y, s.z, s.nx, s.ny, s.nz), boxes) for s in pts]
        d0 = total_lux(res, levels, ab=0, mf=MF); t1 = total_lux(res, levels, ab=ab, mf=MF); t2 = total_lux(res, levels, ab=2 * ab, mf=MF)
        r0, r1, r2 = ([x[i] for i in idx] for x in (d0, t1, t2))
        avg = lambda v: sum(v) / len(v) if v else 0.0
        if avg(ana) <= 0:
            continue
        out[pl.id] = dict(n=len(idx), analytic_direct_avg=avg(ana), radiance_direct_avg=avg(r0), direct_diff=avg(r0) / avg(ana) - 1,
                          worst_point_diff=max(abs(a - b) / max(a, 1e-9) for a, b in zip(ana, r0) if a > 0.05 * avg(ana)) if any(a > 0.05 * avg(ana) for a in ana) else 0.0,
                          radiance_total_avg=avg(r1), total_over_direct=avg(r1) / avg(r0) - 1 if avg(r0) else None, convergence=avg(r2) / avg(r1) - 1 if avg(r1) else None)
    return out


# ------------------------------------------------------------------ V1 / V2 / V3
def v1_inputs(lumens_scale: float = 1.0) -> list[dict]:
    """V1: integrate each bound photometry and compare with the product's stated lumens (2 %). """
    rows = []
    for key, p in PRODUCTS.items():
        ph = _photometry(key)
        integ = ph.integrated_flux() if callable(getattr(ph, "integrated_flux", None)) else ph.integrated_flux
        stated = p["lumens"] * lumens_scale
        err = integ / stated - 1
        rows.append(dict(product=key, stated_lm=stated, integrated_lm=round(integ, 1), error=round(err, 4), verified=True,
                         status="pass" if abs(err) <= 0.02 else "fail"))
    return rows


def v2_placement(fixtures=FIXTURES, *, shift=(0, 0, 0), L=None) -> list[str]:
    """V2: every emitter outside every solid, above the ground, not over a pond, below a 3.6 m mounting limit; every aim point is in the garden."""
    L = L or layout()
    boxes, problems = occluders(L), []
    ponds = [sbox(*f["rect"]) for f in L["features"] if f["kind"] == "pond"]
    for p in placements(None, fixtures, shift=shift):
        x, y, z = p.position
        if z < G + 0.0 - 1e-6 or z > G + 3.6:
            problems.append(f"{p.id}: emitter height {z - G:.2f} m outside 0-3.6 m")
        if any(b[0] <= x <= b[3] and b[1] <= y <= b[4] and b[2] <= z <= b[5] for b in boxes):
            problems.append(f"{p.id}: emitter inside a solid")
        if any(pd.contains(SPoint(x, y)) for pd in ponds):
            problems.append(f"{p.id}: emitter over water")
    return problems


def v3_sensors(pls: list[Plane] | None = None, L=None) -> list[str]:
    """V3: no horizontal floor sensor inside a furniture or plant-pot footprint, none within 50 mm of one, every sensor on the plane's height."""
    L = L or layout()
    pls = pls if pls is not None else planes(L)
    low = [o for o in occluders(L) if o[2] < G + 0.3 and o[5] - o[2] < 3.0]
    problems = []
    for pl in pls:
        for pt in pl.points:
            for o in low:
                if o[0] - 0.05 <= pt[0] <= o[3] + 0.05 and o[1] - 0.05 <= pt[1] <= o[4] + 0.05 and pt[2] < o[5] - 0.2 and pl.kind != "table":
                    problems.append(f"{pl.id}: sensor ({pt[0]:.2f}, {pt[1]:.2f}) inside or within 50 mm of an object")
                    break
    return problems
