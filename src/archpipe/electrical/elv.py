"""ELV and fire layout (EA15, E-10) as device lists: smoke/heat detection, data points, Wi-Fi APs, CCTV, intercom.

Smoke/heat grade follows Approved Document B vol. 1 (UK; the Egyptian fire code is not carded): minimum Grade D2 LD3, or
Grade A LD3 (two storeys) / LD2 (three or more storeys, basements excluded) when a storey exceeds 200 m2. The design
adopts Grade D1 at LD2 or better (all circulation, living, sleeping and storage rooms, heat in kitchens) with every
alarm interlinked, and keeps the lounge and the cinema on the same network (G1 cinema waiver mitigation).
Coverage radii, AP radius and cable limits are policy (EL-POL-ELV), not code values.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import placement
from .model import House, Room

SMOKE_R_MM = 7500.0
HEAT_R_MM = 5300.0
AP_R_MM = 8000.0
DATA_LINK_MAX_M = 90.0
ROUTE = 1.15
SMOKE_KINDS = {"stair", "landing", "corridor", "hall", "entrance", "living", "dining", "study", "media", "bedroom", "dressing", "store"}
HEAT_KINDS = {"kitchen", "utility"}
CIRCULATION = {"stair", "landing", "corridor", "hall", "entrance"}
GRADE_RANK = {"D2": 1, "D1": 2, "A": 3}
CAT_RANK = {"LD3": 1, "LD2": 2, "LD1": 3}
DESIGN_GRADE, DESIGN_CAT = "D1", "LD2"
RACK_ROOM = "stair-b"


@dataclass
class ElvDevice:
    id: str
    kind: str          # smoke | heat | data | tv_sat | ap | ap_outdoor | cctv | intercom_outdoor | intercom_monitor | rack
    room: str
    level: str
    x: float
    y: float
    z: float
    rule: str = ""
    note: str = ""


@dataclass
class ElvLayout:
    devices: list[ElvDevice]
    adb: dict
    storey_area_m2: dict
    notes: list[str] = field(default_factory=list)

    def of(self, *kinds) -> list[ElvDevice]:
        return [d for d in self.devices if d.kind in kinds]


def polygon_area_m2(poly) -> float:
    n = len(poly)
    return abs(sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))) / 2e6


def adb_requirement(storey_area_m2: dict[str, float], above_ground_storeys: int) -> dict:
    """Minimum grade/category per ADB 1.1, 1.5-1.7 from storey areas (gross floor area incl. walls, the larger measure)."""
    big = {k: v for k, v in storey_area_m2.items() if v > 200.0}
    if not big:
        return {"grade": "D2", "category": "LD3", "cards": ["UK-ADB1-2019-1.1-alarm-grade", "UK-ADB1-2019-1.5-large-definition"],
                "reason": "no storey exceeds 200 m2 (" + ", ".join(f"{k} {v:.1f} m2" for k, v in storey_area_m2.items()) + "), so the dwelling is not 'large'"}
    if above_ground_storeys >= 3:
        return {"grade": "A", "category": "LD2", "cards": ["UK-ADB1-2019-1.7-large-three-storeys", "UK-ADB1-2019-1.5-large-definition"],
                "reason": f"storey(s) over 200 m2: {big}, three or more storeys above ground"}
    return {"grade": "A", "category": "LD3", "cards": ["UK-ADB1-2019-1.6-large-two-storeys", "UK-ADB1-2019-1.5-large-definition"],
            "reason": f"storey(s) over 200 m2: {big}, two storeys"}


def grid_points(rect, radius_mm: float) -> list[tuple[float, float]]:
    x0, y0, x1, y1 = rect
    w, h = x1 - x0, y1 - y0
    nx = max(1, math.ceil(w / (radius_mm * math.sqrt(2))))
    ny = max(1, math.ceil(h / (radius_mm * math.sqrt(2))))
    return [(x0 + w * (i + 0.5) / nx, y0 + h * (j + 0.5) / ny) for i in range(nx) for j in range(ny)]


def _area(r: Room) -> float:
    return polygon_area_m2(r.poly) if r.poly else (r.rect[2] - r.rect[0]) * (r.rect[3] - r.rect[1]) / 1e6


def _centroid(r: Room):
    return ((r.rect[0] + r.rect[2]) / 2.0, (r.rect[1] + r.rect[3]) / 2.0)


def _sample(r: Room, step: float = 500.0):
    x0, y0, x1, y1 = r.rect
    xs = [x0 + step / 2 + i * step for i in range(int((x1 - x0) // step) + 1) if x0 + step / 2 + i * step < x1]
    ys = [y0 + step / 2 + j * step for j in range(int((y1 - y0) // step) + 1) if y0 + step / 2 + j * step < y1]
    pts = [(x, y) for x in xs for y in ys if placement.point_in_room(r, x, y)]
    return pts or [_centroid(r)]


def build_layout(h: House, devs: list[placement.Device]) -> ElvLayout:
    areas = h.policy.get("storey_area_m2", {})
    gross = {k: v["gross"] for k, v in areas.items()}
    adb = adb_requirement(gross, above_ground_storeys=int(h.policy.get("storeys_above_ground", 1)))
    out: list[ElvDevice] = []
    n = [0]

    def add(kind, room, level, x, y, z, rule, note=""):
        n[0] += 1
        out.append(ElvDevice(f"{kind.upper()}-{n[0]:03d}", kind, room, level, x, y, z, rule, note))

    rooms = [r for r in h.rooms if r.kind != "outdoor"]
    # ---- smoke and heat ------------------------------------------------------------------------
    for r in sorted(rooms, key=lambda r: -(r.rect[2] - r.rect[0]) * (r.rect[3] - r.rect[1])):
        area = polygon_area_m2(r.poly) if r.poly else (r.rect[2] - r.rect[0]) * (r.rect[3] - r.rect[1]) / 1e6
        kind = "heat" if r.kind in HEAT_KINDS else "smoke" if r.kind in SMOKE_KINDS else None
        if kind is None:
            continue                                   # bathrooms/WCs: no alarm (BS 5839-6)
        rad = HEAT_R_MM if kind == "heat" else SMOKE_R_MM
        cx, cy = _centroid(r)
        if area < 2.0:
            continue                                   # cupboard-sized: covered by the neighbour (checked by the coverage lint)
        if area < 6.0 and any(o in {q.id for q in rooms if q.level == r.level} and any(d.kind == kind and d.room == o and math.hypot(d.x - cx, d.y - cy) <= 0.8 * rad for d in out) for o in r.open_to):
            continue                                   # small open-plan sub-area under a neighbour's detector
        for (x, y) in grid_points(r.rect, rad):
            add(kind, r.id, r.level, x, y, r.ceiling_mm, "EA15-" + ("heat" if kind == "heat" else "smoke") + "-room",
                "interlinked, mains + sealed battery (Grade D1)" if True else "")
    # ---- data points, TV/SAT from the placed devices ---------------------------------------------
    for d in devs:
        if d.kind in ("data", "tv_sat") and d.room in {r.id for r in rooms}:
            r = h.room(d.room)
            add(d.kind, d.room, r.level, d.x, d.y, d.z, d.rule)
    # one data point per bedroom/study without one (e.g. no desk placed)
    for r in rooms:
        if r.kind in ("bedroom", "study") and _area(r) >= 2.0 and not any(o.kind == "data" and o.room == r.id for o in out):
            wn = max(placement.room_walls(r), key=lambda w: placement.room_walls(r)[w].length)
            W = placement.room_walls(r)[wn]
            x, y = W.point(W.length / 2)
            add("data", r.id, r.level, x, y, 300.0, "EA15-data-bedroom-study", "added: no desk or TV wall in the model")
    # ---- rack and access points --------------------------------------------------------------------
    rr = h.room(RACK_ROOM)
    rack_xy = _centroid(rr)
    fu = next((f for f in h.furniture if f.room == RACK_ROOM), None)
    if fu:
        rack_xy = ((fu.rect[0] + fu.rect[2]) / 2, (fu.rect[1] + fu.rect[3]) / 2)
    add("rack", RACK_ROOM, rr.level, rack_xy[0], rack_xy[1], 1200.0, "EA15-rack", "ELV cabinet assumed in the under-stair cupboard (client to confirm)")
    for lvl in sorted({r.level for r in rooms}):
        lr = [r for r in rooms if r.level == lvl and r.kind not in ("bathroom",)]
        aps: list[tuple[float, float, str]] = []
        unc = [r for r in lr]
        while unc:
            # farthest-first: pick the room centroid that covers the most uncovered centroids
            best = max(unc, key=lambda c: sum(1 for q in unc if math.hypot(_centroid(q)[0] - _centroid(c)[0], _centroid(q)[1] - _centroid(c)[1]) <= AP_R_MM))
            cx, cy = _centroid(best)
            aps.append((cx, cy, best.id))
            unc = [q for q in unc if math.hypot(_centroid(q)[0] - cx, _centroid(q)[1] - cy) > AP_R_MM]
        for cx, cy, rid in aps:
            add("ap", rid, lvl, cx, cy, h.room(rid).ceiling_mm - 100.0, "EA15-ap-coverage", f"ceiling AP, {AP_R_MM / 1000:g} m radius (policy)")
    gard = h.policy.get("garden_ap_xy")
    if gard:
        add("ap_outdoor", "site-garden", "SITE", gard[0], gard[1], 2800.0, "EA15-ap-outdoor", "outdoor AP on the building face covering the garden")
    # ---- CCTV and intercom --------------------------------------------------------------------------
    site = h.policy.get("site_points", {})
    for key, (x, y) in site.get("cctv", {}).items():
        add("cctv", "site-gate" if key == "gate" else "site-garden", "SITE", x, y, 3000.0, f"EA15-cctv-{key}")
    if "intercom_gate" in site:
        x, y = site["intercom_gate"]
        add("intercom_outdoor", "site-gate", "SITE", x, y, 1400.0, "EA15-intercom-gate", "video door station at the vehicle/pedestrian gate")
    for rid in site.get("intercom_monitors", []):
        r = h.room(rid)
        W = max(placement.room_walls(r).values(), key=lambda w: w.length)
        x, y = W.point(W.length / 2)
        add("intercom_monitor", rid, r.level, x, y, 1500.0, "EA15-intercom-monitor")
    return ElvLayout(out, adb, areas, [])


# ---- lint (EA15) ------------------------------------------------------------------------------------------
def lint(h: House, lay: ElvLayout, devs=None) -> list[dict]:
    """Layout checks. Each result: subject, status, message, sources, achieved, required, unit."""
    R: list[dict] = []
    rooms = [r for r in h.rooms if r.kind != "outdoor"]
    byroom = {r.id: r for r in rooms}
    sm = lay.of("smoke")
    ht = lay.of("heat")

    def res(subject, ok, msg, src, ach=None, req=None, unit=""):
        R.append({"subject": subject, "status": "pass" if ok else "fail", "message": msg, "sources": src, "achieved": ach, "required": req, "unit": unit})

    # ADB minimum grade
    adb = lay.adb
    ok = GRADE_RANK[DESIGN_GRADE] >= GRADE_RANK[adb["grade"]] and CAT_RANK[DESIGN_CAT] >= CAT_RANK[adb["category"]]
    res("alarm-grade", ok, f"design Grade {DESIGN_GRADE} {DESIGN_CAT} vs ADB minimum Grade {adb['grade']} Category {adb['category']}: {adb['reason']}",
        adb["cards"] + ["BS5839-6-grade-D1", "BS5839-6-LD2"], GRADE_RANK[DESIGN_GRADE], GRADE_RANK[adb["grade"]], "grade rank")
    # a smoke detector on each level and in the stair(s)
    for lvl in sorted({r.level for r in rooms}):
        n = sum(1 for d in sm if d.level == lvl)
        res(f"smoke/{lvl}", n >= 1, f"{n} smoke detectors on level {lvl}", ["UK-ADB1-2019-1.1-alarm-grade", "BS5839-6-LD3"], n, 1, "detectors")
    for r in rooms:
        if r.kind in CIRCULATION:
            ok = any(d.kind == "smoke" and (d.room == r.id or math.hypot(d.x - _centroid(r)[0], d.y - _centroid(r)[1]) <= SMOKE_R_MM and d.level == r.level) for d in lay.devices)
            if r.kind == "stair":
                ok = any(d.kind == "smoke" and d.room == r.id for d in lay.devices)
            res(f"smoke/{r.id}", ok, f"{r.kind} {r.id}: smoke detector {'in the space or within 7.5 m' if ok else 'missing'}", ["BS5839-6-LD3", "UK-ADB1-2019-1.1-alarm-grade"], 1 if ok else 0, 1, "detector")
    # heat in the kitchens
    for r in rooms:
        if r.kind in HEAT_KINDS:
            n = sum(1 for d in ht if d.room == r.id)
            cov = n >= 1 or any(d.level == r.level and math.hypot(d.x - _centroid(r)[0], d.y - _centroid(r)[1]) <= HEAT_R_MM for d in ht)
            res(f"heat/{r.id}", cov, f"{r.id}: {n} heat detector(s) in the room" + ("" if n else "; covered by a neighbour" if cov else "; none"), ["EL-POL-ELV", "BS5839-6-LD2"], n, 1, "detectors")
    # coverage of every alarm room
    worst_s = 0.0
    bad = []
    for r in rooms:
        kind = "heat" if r.kind in HEAT_KINDS else "smoke" if r.kind in SMOKE_KINDS else None
        if kind is None:
            continue
        rad = HEAT_R_MM if kind == "heat" else SMOKE_R_MM
        ds = [d for d in lay.devices if d.kind == kind and d.level == r.level]
        far = max(min(math.hypot(d.x - px, d.y - py) for d in ds) if ds else 1e9 for px, py in _sample(r))
        worst_s = max(worst_s, far / rad)
        if far > rad:
            bad.append((r.id, round(far)))
    res("alarm-coverage", not bad, f"every point of {sum(1 for r in rooms if r.kind in SMOKE_KINDS | HEAT_KINDS)} alarm rooms is within the detector radius (smoke {SMOKE_R_MM / 1000:g} m, heat {HEAT_R_MM / 1000:g} m)" if not bad else f"points outside the radius: {bad}",
        ["EL-POL-ELV"], round(worst_s, 2), 1.0, "worst point / radius")
    # no alarm in bathrooms
    wet = [d for d in lay.devices if d.kind in ("smoke", "heat") and byroom.get(d.room) and byroom[d.room].kind == "bathroom"]
    res("alarm-not-in-baths", not wet, f"{len(wet)} alarms in bathrooms/WCs", ["BS5839-6-no-alarm-in-baths"], len(wet), 0, "alarms")
    # G1 cinema waiver: lounge and cinema both on the interlinked network
    for rid in ("lounge", "cinema"):
        n = sum(1 for d in sm if d.room == rid)
        res(f"G1-cinema-waiver/{rid}", n >= 1, f"{n} interlinked smoke detector(s) in {rid} (G1 waiver mitigation: lounge and cinema interlinked)", ["EL-G1-CINEMA", "BS5839-6-grade-D1"], n, 1, "detectors")
    # data: bedrooms, study, TV walls
    dat = lay.of("data")
    for r in rooms:
        if r.kind in ("bedroom", "study") and _area(r) >= 2.0:
            n = sum(1 for d in dat if d.room == r.id)
            res(f"data/{r.id}", n >= 1, f"{n} data point(s) in {r.id}", ["EL-POL-ELV"], n, 1, "points")
    for f in h.furniture:
        if f.kind == "tv":
            n = sum(1 for d in dat if d.room == f.room and math.hypot((d.x - (f.rect[0] + f.rect[2]) / 2), (d.y - (f.rect[1] + f.rect[3]) / 2)) < 1500.0)
            s = sum(1 for d in lay.of("tv_sat") if d.room == f.room)
            res(f"tv/{f.id}", n >= 1 and s >= 1, f"TV wall {f.id}: {n} data, {s} TV/SAT outlets within 1.5 m", ["EL-POL-ELV"], min(n, s), 1, "outlets")
    # AP coverage
    aps = lay.of("ap")
    for r in rooms:
        if r.kind == "bathroom":
            continue
        cx, cy = _centroid(r)
        d = min((math.hypot(a.x - cx, a.y - cy) for a in aps if a.level == r.level), default=1e9)
        if d > AP_R_MM:
            res(f"ap/{r.id}", False, f"{r.id} centre is {d / 1000:.1f} m from the nearest AP on level {r.level} (> {AP_R_MM / 1000:g} m)", ["EL-POL-ELV"], d / 1000, AP_R_MM / 1000, "m")
    res("ap-coverage", not any(x["subject"].startswith("ap/") for x in R), f"every room centre on both levels is within {AP_R_MM / 1000:g} m of an AP ({len(aps)} APs, {len(lay.of('ap_outdoor'))} outdoor)", ["EL-POL-ELV"], len(aps), None, "APs")
    # data link lengths to the rack
    rack = next(d for d in lay.devices if d.kind == "rack")
    z = h.level_z_mm
    worst = 0.0
    for d in lay.devices:
        if d.kind in ("data", "ap", "ap_outdoor", "cctv", "intercom_outdoor", "intercom_monitor", "tv_sat"):
            dz = abs(z.get(d.level, 0.0) - z.get(rack.level, 0.0)) / 1000.0
            L = (abs(d.x - rack.x) + abs(d.y - rack.y)) / 1000.0 * ROUTE + dz + 4.0
            worst = max(worst, L)
    res("data-link-length", worst <= DATA_LINK_MAX_M, f"longest ELV cable from the rack {worst:.0f} m (Manhattan x 1.15 + storey rise + 4 m) vs {DATA_LINK_MAX_M:g} m permanent link", ["EL-POL-ELV"], round(worst, 1), DATA_LINK_MAX_M, "m")
    # CCTV
    cc = lay.of("cctv")
    gate = [d for d in cc if d.rule.endswith("gate")]
    res("cctv-gate", len(gate) >= 1, f"{len(gate)} camera(s) at the gate", ["EL-POL-ELV"], len(gate), 1, "cameras")
    per = [d for d in cc if d.rule.startswith("EA15-cctv-corner")]
    res("cctv-perimeter", len(per) >= 4, f"{len(per)} perimeter cameras (plot corners)", ["EL-POL-ELV"], len(per), 4, "cameras")
    ic = lay.of("intercom_outdoor")
    res("intercom", len(ic) >= 1 and len(lay.of("intercom_monitor")) >= 1, f"{len(ic)} gate station, {len(lay.of('intercom_monitor'))} indoor monitors", ["EL-POL-ELV"], len(ic), 1, "stations")
    return R
