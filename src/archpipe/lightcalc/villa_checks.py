"""L6b: villa checks beyond the Radiance planes: LA6 colour, LA8 layering, LA9 setting-out, LA4 luminance, LA13 night/emergency
route, LA12 exterior, LA15 energy. Each returns CheckResult records (contracts) and never invents a threshold: policy values
are the cards of lightcalc.sources."""
from __future__ import annotations

import math
from collections import defaultdict

from ..contracts import CheckResult
from . import checks
from .direct import Placement
from .villa import fixture_placements

# habitable spaces (rooms that share one living space) for the layering check
SPACES = {
    "lounge": ["lounge", "lounge-nook"], "kitchen": ["kitchen", "kitchen-island"], "dining": ["dining", "dining-side"],
    "living": ["living", "bar-alcove"], "family-corner": ["family", "hall-b", "entry-b"], "cinema": ["cinema"],
    "study-game": ["study-game"], "kids-a": ["kids-a"], "kids-b": ["kids-b"],
    "parents-bed": ["parents-bed", "parents-entry"], "parents-dressing": ["parents-dressing", "parents-dressing-ext"],
    "parents-ensuite": ["parents-ensuite"], "family-bath": ["family-bath"], "guest-wc": ["guest-wc"],
    "dirty-kitchen": ["dirty-kitchen"], "stair": ["stair-b", "stair-gf", "landing-gf"], "corridor": ["corridor", "gallery-end"],
}


def _layer(f):
    from ..concept.villa_lighting import zone_layer
    return zone_layer(f)


def check_la6(fixtures) -> list[CheckResult]:
    """One CCT per layer per room, and the schedule value equals the bound product's CCT."""
    by = defaultdict(set)
    for f in fixtures:
        by[(f.room, _layer(f))].add(f.record.cct_k)
    bad = {k: sorted(v) for k, v in by.items() if len(v) > 1}
    out = [CheckResult("LA6", "L6", "pass" if not bad else "fail", "villa/one-CCT-per-layer-per-room",
                       achieved=float(len(bad)), required=0.0, unit="rooms/layers with >1 CCT",
                       message=("every (room, layer) has a single CCT: 2700 K interior, 2200 K night" if not bad else
                                "mixed CCT: %s" % bad), source_ids=("L6-POLICY-LA6-2700K",))]
    # spec vs bound product
    from ..fixture_record import PRODUCTS, KINDS, bind_products
    bind_products()
    mism = [(k, KINDS[k]["cct"], p["cct"]) for k, p in PRODUCTS.items() if int(KINDS[k]["cct"]) != int(p["cct"])]
    out.append(CheckResult("LA6", "L6", "pass" if not mism else "fail", "villa/spec-vs-product-CCT", achieved=float(len(mism)),
                           required=0.0, unit="kinds", message=("kind spec CCT equals the bound product CCT for every product-bound kind"
                                                                if not mism else "spec vs product: %s" % mism),
                           source_ids=("L6-POLICY-LA6-2700K",)))
    return out


def layers_by_space(fixtures) -> dict:
    out = {}
    for sp, rooms in SPACES.items():
        out[sp] = sorted({_layer(f) for f in fixtures if f.room in rooms})
    return out


def check_la8(fixtures) -> list[CheckResult]:
    out = []
    for sp, layers in layers_by_space(fixtures).items():
        ok = len(layers) >= 2
        out.append(CheckResult("LA8", "L6", "pass" if ok else "fail", "villa/layers/" + sp, achieved=float(len(layers)),
                               required=2.0, unit="independently switched layers",
                               message="layers: %s" % ", ".join(layers), source_ids=("L6-POLICY-LA8-layers",)))
    return out


# ------------------------------------------------------------------ LA9
RECESSED = ("DL", "DLN", "ADJ", "WW")
TOL = 0.010


def room_axes(v, room):
    from ..concept.villa_lighting import axes_for_room
    return axes_for_room(v.rc, v.items, v.fp, room)


def _symmetric_rows(coords, centres):
    """coordinates that form an evenly spaced row (>= 2 members) symmetric about one of the declared centre lines"""
    out = set()
    cs = sorted({round(c, 3) for c in coords})
    if len(cs) < 2:
        return out
    for c0 in centres:
        for i in range(len(cs)):
            for j in range(i + 1, len(cs)):
                if abs((cs[i] + cs[j]) / 2 - c0) <= TOL:       # a mirrored pair about the axis
                    out.update((cs[i], cs[j]))
    return out


def check_la9(v) -> list[CheckResult]:
    by_room = defaultdict(list)
    for f in v.fixtures:
        if f.kind in RECESSED:
            by_room[f.room].append(f)
    n = ok = 0
    off = []
    for room, fs in by_room.items():
        ax, ay = room_axes(v, room)
        sx = _symmetric_rows([f.x for f in fs], ax[:1] + ax[1::3])
        sy = _symmetric_rows([f.y for f in fs], ay[:1] + ay[1::3])
        for f in fs:
            n += 1
            dx = min(abs(f.x - a) for a in ax)
            dy = min(abs(f.y - a) for a in ay)
            good = dx <= TOL or dy <= TOL or round(f.x, 3) in sx or round(f.y, 3) in sy or "axis" in f.extra
            if good:
                ok += 1
            else:
                off.append((f.id, round(min(dx, dy) * 1000)))
    pct = 100.0 * ok / n if n else 0.0
    return [CheckResult("LA9", "L6", "pass" if not off else "fail", "villa/ceiling-setting-out", achieved=pct, required=100.0,
                        unit="% on a declared axis", message=("%d/%d recessed fittings on a room axis, furniture axis/edge or a "
                                                              "mirrored row about one (tolerance 10 mm)" % (ok, n))
                        + ("; off-axis (id, nearest-axis offset mm): %s" % off if off else ""),
                        source_ids=("L6-POLICY-LA9-axis-tolerance-10mm",), element_ids=tuple("lum-" + o[0] for o in off))]


# ------------------------------------------------------------------ LA4 luminance
def check_la4(v, sightlines) -> list[CheckResult]:
    """Luminance of recessed product fittings toward the eye of each sightline; 3000 cd/m2 cap within 45 deg of the
    sightline unless shielded (policy card). Only product-bound fittings (measured opening) of the SAME open-plan cluster
    are in view (walls are not modelled, so other rooms are excluded explicitly)."""
    from .villa import cluster_of
    out = []
    for sl in sightlines:
        cl = cluster_of(sl["room"])
        plac = []
        for f in v.fixtures:
            if f.kind in RECESSED and f.record.product and cluster_of(f.room) == cl:
                plac += fixture_placements(f)
        out += checks.check_la4_luminance("villa", [sl], plac)
    return out


# ------------------------------------------------------------------ LA13
def stair_route(v) -> list[tuple]:
    """Centre line of the stair at tread-top height (the stair rises west along the north wall, tread tops from the spec)."""
    from ..concept import villa_lighting as VL
    boxes = sorted(VL._stair_boxes(v.lay), key=lambda b: -b[0])      # from the foot (east) to the top (west)
    pts = []
    for b in boxes:
        x = (b[0] + b[3]) / 2000.0
        y = (b[1] + b[4]) / 2000.0
        pts.append((x, y, b[5] / 1000.0 + 0.001))
    return pts


def check_la13(v, emergency_ids=None) -> list[CheckResult]:
    """>= 1 lx on the centre line of the stair, direct, from the night-layer markers on the route (battery-backed)."""
    ems = []
    for f in v.fixtures:
        if _layer(f) in ("night", "emergency") and f.kind in ("STEP", "PATH", "NL", "TOE"):
            ems += fixture_placements(f)
    route = stair_route(v)
    out = [checks.check_la13("villa/stair", route, ems)]
    for name, poly in basement_routes(v).items():
        out.append(checks.check_la13("villa/" + name, poly, ems))
    return out


def basement_routes(v) -> dict:
    rc = v.rc
    z = -3.0 + 0.001
    h = rc["hall-b"]
    L = rc["lounge"]
    D = rc["dining"]
    return {"basement-route-lounge-to-stair-foot": [(L[0] + 0.6, (L[1] + L[3]) / 2, z), ((L[2] + h[0]) / 2, (L[1] + L[3]) / 2, z),
                                                     ((h[0] + h[2]) / 2, (h[1] + h[3]) / 2, z), (9.45, -27.9, z)],
            "basement-route-dining-to-stair-foot": [((D[0] + D[2]) / 2, (D[1] + D[3]) / 2, z), (h[2], (h[1] + h[3]) / 2, z),
                                                     ((h[0] + h[2]) / 2, (h[1] + h[3]) / 2, z), (9.45, -27.9, z)]}


# ------------------------------------------------------------------ LA15 / energy
def lpd_rows(v) -> list[dict]:
    """Installed W per room area (nominal, product watts x driver output; generic watts ASSUMED 90 lm/W)."""
    by = defaultdict(float)
    for f in v.fixtures:
        for p in fixture_placements(f):
            by[f.room] += p.watts or 0.0
    rows = []
    for room, w in sorted(by.items()):
        r = v.rc[room]
        a = (r[2] - r[0]) * (r[3] - r[1])
        rows.append({"room": room, "watts": round(w, 1), "area_m2": round(a, 1), "w_per_m2": round(w / a, 2)})
    return rows


# ------------------------------------------------------------------ LA10 scenes, LA4 sightlines, LA13 night level
REQUIRED_SCENES = {"B-open": ("Day", "Evening", "Dinner", "Film", "Night"), "B-cinema": ("Day", "Evening", "Film", "Night"),
                   "GF-parents-bed": ("Day", "Evening", "Night"), "GF-kids-a": ("Day", "Evening", "Night"),
                   "GF-kids-b": ("Day", "Evening", "Night"), "GF-circulation": ("Day", "Evening", "Night")}


def check_la10_scenes(scenes: dict) -> list[CheckResult]:
    out = []
    for cl, need in REQUIRED_SCENES.items():
        have = set(scenes.get(cl, {}))
        miss = [n for n in need if n not in have]
        out.append(CheckResult("LA10", "L6", "pass" if not miss else "fail", "villa/scenes/" + cl, achieved=float(len(need) - len(miss)),
                               required=float(len(need)), unit="scenes", source_ids=("L6-POLICY-LA10-scenes",),
                               message="scenes defined: %s; missing: %s ('Off' is every zone at 0)" % (sorted(have), miss or "none")))
    out.append(CheckResult("LA10", "L6", "not_evaluated", "villa/two-way-switching",
                           message="two-way switching at the stair and rooms with 2 doors is a device layout (L7 electrical lane); "
                                   "not evaluated here. Scene CSV export for a DALI/Lutron import is not implemented."))
    return out


def check_la10_night(v, level: float = 0.1, cap: float = 5.0) -> CheckResult:
    """The Night scene (night layer at `level`) must keep the stair/route centre line <= 5 lx (policy: a comfortable path,
    not a glare source). Direct light from the night-layer markers; the mains-failure >= 1 lx at full output is LA13."""
    from .direct import direct_illuminance
    ems = []
    for f in v.fixtures:
        if _layer(f) in ("night", "emergency") and f.kind in ("STEP", "PATH", "NL", "TOE", "DL"):
            ems += fixture_placements(f)
    worst = 0.0
    for poly in [stair_route(v)] + list(basement_routes(v).values()):
        for p in poly:
            worst = max(worst, level * direct_illuminance(ems, p))
    return CheckResult("LA10", "L6", "pass" if worst <= cap else "fail", "villa/night-path-level", achieved=worst, required=cap,
                       unit="lx", source_ids=("L6-POLICY-LA10-scenes",),
                       message="Night scene: max route centre-line illuminance %.2f lx at %.0f %% of the night-layer output vs <= %.0f lx"
                               % (worst, 100 * level, cap))


def sightlines(v) -> list[dict]:
    """Eye points and directions: seated 1.2 m (sofa, dining chair), reclined on the bed (0.7 m above the floor)."""
    B, G = -3.0, 0.0
    fp = v.fp
    sofa = fp["lounge-sofa"]
    lsf = fp["living-sofa"]
    dt = fp["dining-table"]
    bed = fp["pb-bed"]
    return [
        {"id": "lounge-sofa-to-TV", "room": "lounge", "eye": ((sofa[0] + sofa[2]) / 2, (sofa[1] + sofa[3]) / 2, B + 1.2), "dir": (0, 1, 0)},
        {"id": "living-sofa-to-garden", "room": "living", "eye": ((lsf[0] + lsf[2]) / 2, (lsf[1] + lsf[3]) / 2, B + 1.2), "dir": (0, 1, 0)},
        {"id": "dining-seat-along-table", "room": "dining", "eye": (dt[0] + 0.5, (dt[1] + dt[3]) / 2, B + 1.2), "dir": (1, 0, 0)},
        {"id": "dining-seat-to-sideboard", "room": "dining", "eye": ((dt[0] + dt[2]) / 2, dt[1] + 0.2, B + 1.2), "dir": (0, -1, 0)},
        {"id": "parents-bed-lying", "room": "parents-bed", "eye": ((bed[0] + bed[2]) / 2, bed[1] + 0.4, G + 0.7), "dir": (0, 1, 0.3)},
    ] + bed_lying_sightlines(v)


# bed -> (room, head end, eye height above the floor). Head ends from the furnishing spec: the parents' bed head is on the north
# wall (wall reading lights at its head), kids' B "head to the west wall"; the bunk's is not declared, so both ends are tested.
# Eye heights: 0.7 m on a 0.5 m bed (as the reclined sightline above); upper berth 1.5 m (ASSUMED: furnishing h = 1.7 m).
BEDS = {"pb-bed": ("parents-bed", ("min-y",), 0.7), "kb-bed": ("kids-b", ("min-x",), 0.7), "ka-bunk": ("kids-a", ("min-y", "max-y"), 1.5)}
PILLOW_OFFSET = 0.4      # m from the head end to the eye of a person lying on the pillow


def bed_lying_sightlines(v) -> list[dict]:
    """LA4 'lying, looking up': for every bed in every bedroom, the eye on each pillow looking straight up (policy card)."""
    out = []
    for bid, (room, heads, eye_z) in BEDS.items():
        x0, y0, x1, y1 = v.fp[bid]
        for head in heads:
            along_x = head.endswith("x")
            width = (y1 - y0) if along_x else (x1 - x0)
            offs = (-0.4, 0.4) if width >= 1.4 else (0.0,)        # a double bed has two pillows
            for k, off in enumerate(offs):
                a = {"min-x": x0 + PILLOW_OFFSET, "max-x": x1 - PILLOW_OFFSET, "min-y": y0 + PILLOW_OFFSET, "max-y": y1 - PILLOW_OFFSET}[head]
                c = ((y0 + y1) / 2 if along_x else (x0 + x1) / 2) + off
                eye = (a, c, eye_z) if along_x else (c, a, eye_z)
                out.append({"id": "%s-lying-up-%s%s" % (bid, head, "" if len(offs) == 1 else "-p%d" % (k + 1)), "room": room, "eye": eye,
                            "dir": (0, 0, 1), "cards": ("L6-POLICY-LA4-bed-lying-looking-up",)})
    return out


# ------------------------------------------------------------------ LA12 exterior (what exists: 4 garden uplights in the render scene)
def exterior_placements() -> list[Placement]:
    import json
    from pathlib import Path
    from ..photometry import load as load_ies
    root = Path(__file__).resolve().parents[3] / "knowledge" / "lighting"
    data = json.loads((root / "exterior-lights-scene.json").read_text(encoding="utf-8"))
    ph = load_ies(root / "ies" / "GARDEN-UP.ies")
    return [Placement(l["id"], ph, tuple(l["position"]), aim=tuple(l["aim"])) for l in data["lights"]]


def check_la12(v=None) -> list[CheckResult]:
    """Obtrusive light for the exterior luminaires that exist (four ASSUMED garden uplights in the render scene; none in the
    L2 model): ULR in the installed attitude and intensity toward neighbour eye points beyond the west boundary (E3, SLL T3.2).
    The boundary Ev grid and facade luminance need an exterior Radiance run (not done): reported not_evaluated."""
    ext = exterior_placements()
    nb = [(-1.5, y, -3.0 + 1.5) for y in (-24.5, -27.7)]
    out = []
    for curfew in ("pre", "post"):
        out += [r for r in checks.check_la12("villa/exterior", exterior=ext, neighbour_points=nb, curfew=curfew)
                if "ULR" not in r.subject or curfew == "pre"]
    out.append(CheckResult("LA12", "L6", "not_evaluated", "villa/exterior/boundary-Ev",
                           message="boundary vertical illuminance and facade luminance need an exterior Radiance grid: not run"))
    return out


def check_v12(drivers: dict, cap: float = 0.80) -> list[CheckResult]:
    """V12: every tuned zone driver (fraction of maximum output) is <= cap, so commissioning has >= 25 % headroom."""
    return [CheckResult("LA10", "L6", "pass" if d <= cap + 1e-9 else "fail", "villa/V12-driver/" + z, achieved=d, required=cap,
                        unit="x max output", source_ids=("L6-POLICY-V12-headroom",),
                        message="zone driver %.3f of maximum output vs <= %.2f (V12 headroom for commissioning)" % (d, cap))
            for z, d in sorted(drivers.items())]
