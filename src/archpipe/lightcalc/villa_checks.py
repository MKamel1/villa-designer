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
    sightline unless shielded (policy card). Only product-bound fittings (measured opening) are evaluated."""
    plac = []
    for f in v.fixtures:
        if f.kind in RECESSED and f.record.product:
            plac += fixture_placements(f)
    return checks.check_la4_luminance("villa", sightlines, plac)


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
