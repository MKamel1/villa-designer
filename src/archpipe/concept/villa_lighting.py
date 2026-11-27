"""D1 lighting (Phase 3): what each room needs to WORK, what makes it BEAUTIFUL, and the check that the first is met.

Client (2026-09-27): "lighting is what makes or breaks a room; a function but art as well". Ambient light from spots
is FLUSH (trimless recessed downlights, no cans, no track); task light and centrepieces may be pendants and/or
spots. Questionnaire: pendants over the island and the dining table, cove / indirect ceiling light, backlit shelves,
wall washers; night: stair step lights, low path lights to the bathrooms, kids' night lights.

FUNCTION: every room and task names its IES card (IES Lighting Handbook 10th ed. Table 33.2, maintained lux, the
25-65 column) and `check()` computes it: direct-only maintained illuminance (lighting.py, MF 0.8) at the named task
points and averaged over the room's floor. Direct-only UNDERSTATES (no inter-reflection), so a pass is conservative
and a shortfall of less than ~25 % in a light room is advisory, not a fail (ADR-0009); only point targets carry a
verdict (lighting.point_illuminance docstring).

BEAUTY (the layers, lighting-design-basics pp. 58-63): ambient kept soft and dimmable (flush wide-beam downlights,
cross-lighting, never a grid on a table); focal light where the eye should go (library wall backlit, art and
sideboard accented at ~30 deg, card ldb-accent-aim-30); decorative centrepieces (globe pendants at 762 mm over the
island and the table, card rid-pendant-above-table-762; a globe cluster dropping into the stair void; low opal
globes at the parents' bedside); indirect light that makes ceilings float (perimeter coves: the LED level with the
fascia, stopped short of end walls, p. 59); night light low and warm (toe-kicks, step and path markers, 2200 K).

Geometry: metres, model axes; z absolute (GF FFL 0, basement FFL -3.0). Ceilings: a gypsum false ceiling 2.70 m
above the floor (a plenum for the flush fittings and coves under the 2.80 m slab soffit; the daylight study assumed
2.80 m -> noted); under the ramp and deck, 0.10 m below the soffit. Coves: a 0.40 m perimeter band at 2.70 m round a
field raised to 2.80 m, the LED strip on the band's inner edge.

Photometry: if no verified manufacturer file exists for a kind, it uses a GENERIC rotationally symmetric
cosine-power distribution with the kind's stated beam and lumens (`generic_ies`), and every output says so.
"""
from __future__ import annotations
from .authored_values import fill_defaults

import math
from dataclasses import dataclass, field

from . import villa_furnish as F
from . import revit_spec as RS
from . import villa_daylight as VD
from . import villa_r11 as R

LEVEL_Z = {"B": -3.0, "GF": 0.0}
VL_DESK_Z = 0.75 + 0.45          # desk lamp head 450 mm over a 750 mm desk
CEILING = 2.70                 # false ceiling above FFL
COVE_FIELD = 2.80              # the raised field inside a cove (slab soffit)
COVE_BAND = 0.40
# L6d (LV open item): the entry lobby has ONE cove side, on the bedroom side (y1): a 0.30 m lowered band at 2.70 (the bedroom's ceiling carried into
# the lobby) with a 30 mm upstand on its lobby edge, the strip standing on the band 30 mm behind the upstand (z 2.72, under the 2.80 slab soffit) in a closed trough,
# aimed into the lobby. The setback matters: a sight line from a pillow crosses the 2.70 plane up to 11 mm in front of the strip.
LOBBY_COVE_DEPTH = 0.30
LOBBY_COVE_UPSTAND = 0.03
LOBBY_COVE_SETBACK = 0.03
LOBBY_COVE_BACK = 0.02       # the trough's back wall, 20 mm behind the strip: a closed white trough (without it the light is lost in the plenum above the bedroom ceiling)
LOBBY_COVE_LM_PER_M = 900.0  # the COVE kind's own rating: Cycles measured the built coffer at 11 lx (cove alone, 450 lm/m, open trough), 30 lx lobby minimum needs the closed trough AND 900 lm/m
LOBBY_COVE_ROOM = "parents-entry"
# Client 2026-11-24 (reference image12): a light-marble feature panel on the wall behind the ensuite bath, framed by an LED cove
# (PCOVE, iGuzzini ST39). The finish layer (villa_render) and the strips share these numbers; metres. The cove sits in a reveal
# `edge_gap` outside each panel edge and above its top, 8 mm proud of the panel face, emitting across the panel (grazing) and into the room;
# wall_finish: the marble wall layer is 23 mm thick (finish-layer-*-marble-bath faces, measured in the scene: the first panel sat INSIDE it and
# was invisible); the panel and the cove stand on that face.
# the panel starts at the bath rim (z0 = the bath height, asserted in villa_render): the tub stands flush to this wall.
BATH_PANEL = dict(width=1.50, z0=0.55, z1=2.40, thick=0.012, edge_gap=0.03, strip_z0=0.58, strip_off=0.029, wall_finish=0.023, dimmer=0.15)
UNDER_SOFFIT = ("cinema", "store-ramp", "guest-wc", "dirty-kitchen")
MF = 0.8                       # maintenance factor (stated, lighting.DEFAULT_MAINTENANCE_FACTOR)

# Read-only compatibility views; declarations are owned by fixture_record.
from ..fixture_record import FIXTURE_KINDS, KINDS, PRODUCT_CHOICE, PRODUCTS, bind_products, record_for, kind_photometry, vanity_pair_datum, VANITY_DECISIONS, VANITY_DECISION_SOURCE, over_mirror_datum


def products():
    """Resolve the fixture-record product registry before consuming photometry."""
    return bind_products()


@dataclass
class Fixture:
    id: str
    kind: str
    room: str
    level: str
    x: float
    y: float
    z: float                       # emitter, absolute
    aim: tuple = (0.0, 0.0, -1.0)
    length: float = 0.0            # strips: along `along`
    along: tuple = (1.0, 0.0, 0.0)
    why: str = ""
    card: str = ""
    lm: float | None = None        # overrides the kind's (strips: computed from length)
    extra: dict = field(default_factory=dict)

    @property
    def spec(self):
        return KINDS[self.kind]

    @property
    def lumens(self):
        return record_for(self).flux_lm

    @property
    def record(self):
        return record_for(self)

    @property
    def layer(self):
        return self.spec["layer"]


def zone_id(f) -> str:
    """Control-zone id: level x room x (explicit function suffix | layer). A zone is one switched/dimmed circuit group."""
    suffix = "%s-%s" % (f.room, f.extra.get("zone") or f.layer)
    return "Z-%s-%s" % (f.level, suffix.upper())


def zone_layer(f) -> str:
    return f.extra.get("layer") or f.layer


def _drivers():
    """Commissioning table solved by lightcalc.villa_tune from the per-zone Radiance results (knowledge/lighting)."""
    import json
    from pathlib import Path
    import os
    path = Path(os.environ.get("ARCHPIPE_ZONE_DRIVERS") or Path(__file__).resolve().parents[3] / "knowledge" / "lighting" / "zone-drivers.json")
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


SET_OUT_TOL = 0.010            # LA9: a recessed fitting sits on a declared axis within 10 mm
SET_OUT_SNAP = 0.30            # a fitting further than this from every axis is not moved (reported by the check instead)
RECESSED_KINDS = ("DL", "DLN", "ADJ", "WW")


def axes_for_room(rc, it, fp, room):
    """Declared axes of a room: its centre lines and the centre lines/edges of the furniture standing in it."""
    r = rc[room]
    ax, ay = [(r[0] + r[2]) / 2], [(r[1] + r[3]) / 2]
    for k, i in it.items():
        if i["room"] != room:
            continue
        q = fp[k]
        ax += [(q[0] + q[2]) / 2, q[0], q[2]]
        ay += [(q[1] + q[3]) / 2, q[1], q[3]]
    return ax, ay


def symmetric_rows(coords, centres):
    """Coordinates that form a mirrored pair about a declared centre line (a row set out symmetrically about an axis)."""
    out = set()
    cs = sorted({round(c, 3) for c in coords})
    for c0 in centres:
        for i in range(len(cs)):
            for j in range(i + 1, len(cs)):
                if abs((cs[i] + cs[j]) / 2 - c0) <= SET_OUT_TOL:
                    out.update((cs[i], cs[j]))
    return out


def set_out(fixtures, rc, it, fp):
    """L6b RCP setting-out (LA9): move a recessed fitting that is within 0.30 m of a room/furniture axis (one coordinate,
    the nearer) onto it. Fittings in a mirrored row about a centre line are already set out."""
    by = {}
    for f in fixtures:
        if f.kind in RECESSED_KINDS:
            by.setdefault(f.room, []).append(f)
    for room, fs in by.items():
        fs = [f for f in fs if "axis" not in f.extra]          # a fitting that declares its own axis is not snapped
        ax, ay = axes_for_room(rc, it, fp, room)
        sx = symmetric_rows([f.x for f in fs], ax[:1] + ax[1::3])
        sy = symmetric_rows([f.y for f in fs], ay[:1] + ay[1::3])
        for f in fs:
            dx, nx = min((abs(f.x - a), a) for a in ax)
            dy, ny = min((abs(f.y - a), a) for a in ay)
            if dx <= SET_OUT_TOL or dy <= SET_OUT_TOL or round(f.x, 3) in sx or round(f.y, 3) in sy:
                continue
            if min(dx, dy) <= SET_OUT_SNAP:
                if dx <= dy:
                    f.x = round(nx, 3)
                else:
                    f.y = round(ny, 3)
                f.extra["set_out"] = "snapped to a room/furniture axis"
    return fixtures


def _sizing():
    """L6c: rated-lumen multiplier per control zone for GENERIC fittings (no verified product), solved by villa_tune_cli
    --size-generics so the commissioning driver sits at 0.70: a generic fitting is specified at the size the design needs,
    never an oversized one dimmed to the floor. Bound products are never resized (they are what they are)."""
    import json
    from pathlib import Path
    path = Path(__file__).resolve().parents[3] / "knowledge" / "lighting" / "zone-sizing.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def apply_drivers(fixtures):
    """Set each fixture's driver output from its zone's solved factor d: a bound product gets extra['dimmer'] = d (> 1 raises);
    a generic fitting gets lumens scaled by d (it may exceed 1: the generic is sized, not dimmed)."""
    table = _drivers()
    sizing = _sizing()
    for f in fixtures:
        d = table.get(zone_id(f))
        if d is None:
            continue
        if f.kind in PRODUCTS or kind_has_product(f.kind):
            if d > 1.0:      # a bound product cannot exceed its rated output: change the design, never clip the driver
                raise ValueError("zone %s needs %.2f of the rated output of its bound product %s: add or upgrade fittings"
                                 % (zone_id(f), d, f.kind))
            f.extra["dimmer"] = round(d, 3)
        else:
            base = f.lm if f.lm is not None else (KINDS[f.kind]["lm_per_m"] * f.length if "lm_per_m" in KINDS[f.kind]
                                                   else KINDS[f.kind]["lm"])
            f.extra["rated_lm"] = round(base * sizing.get(zone_id(f), 1.0), 1)     # what the supplier specifies (full output)
            f.lm = round(base * sizing.get(zone_id(f), 1.0) * d, 1)
    return fixtures


def kind_has_product(kind):
    return bool(products().get(kind))


def ceiling_z(level, x=None, room=None, y=None, lay=None, spec=None):
    """Finished ceiling above a fitting, using the cove design and the built ramp/deck/roof spec."""
    base = LEVEL_Z[level]
    if level == "B" and room in UNDER_SOFFIT:
        if x is None or y is None:
            raise ValueError("An under-soffit fitting needs both plan coordinates")
        spec = spec if spec is not None else RS.build(lay or R.design("D1"))
        for x0, y0, x1, y1 in spec.get("roofs", []):
            if x0 <= x <= x1 and y0 <= y <= y1:
                return -VD.SLAB_T                  # the extension roof is a GF-level slab
        parking = spec["parking2"]
        deck = parking["deck"]
        if deck["x0"] <= x <= deck["x1"] and deck["y0"] <= y <= deck["y1"]:
            return deck["z_top"] - deck["thick"]
        ramp = parking["ramp"]
        profile = ramp["profile"]
        if ramp["y0"] <= y <= ramp["y1"]:
            for (xa, za), (xb, zb) in zip(profile, profile[1:]):
                if xa <= x <= xb:
                    return za + (zb - za) * (x - xa) / (xb - xa) - ramp["thick"]
        raise ValueError("No Revit-spec soffit above %s at (%.3f, %.3f)" % (room, x, y))
    if room in ("lounge", "living") and x is not None and y is not None:
        x0, y0, x1, y1 = F.clear_rect(lay or R.design("D1"), room)
        if x0 + COVE_BAND < x < x1 - COVE_BAND and y0 + COVE_BAND < y < y1 - COVE_BAND:
            return base + COVE_FIELD              # slab exposed inside the lower perimeter band
    if level == "GF" and room == "stair-gf":
        return base + COVE_FIELD                  # slab over the double-height stair void
    if room == LOBBY_COVE_ROOM and y is not None and lay is not None:
        if y < F.clear_rect(lay, room)[3] - LOBBY_COVE_DEPTH:
            return base + COVE_FIELD              # lobby field: the slab soffit above the cove band (bedroom side)
    return base + CEILING


def _grid(rect, nx, ny, margin=None, mx=None, my=None):
    x0, y0, x1, y1 = rect
    mx = mx if mx is not None else (margin if margin is not None else (x1 - x0) / nx / 2)
    my = my if my is not None else (margin if margin is not None else (y1 - y0) / ny / 2)
    xs = [x0 + mx + i * (x1 - x0 - 2 * mx) / max(1, nx - 1) for i in range(nx)] if nx > 1 else [(x0 + x1) / 2]
    ys = [y0 + my + j * (y1 - y0 - 2 * my) / max(1, ny - 1) for j in range(ny)] if ny > 1 else [(y0 + y1) / 2]
    return [(x, y) for x in xs for y in ys]


def design(lay=None):
    """The authored D1 scheme: [Fixture]. Each placement is relative to the room's clear rect or a furniture piece."""
    lay = lay or R.design("D1")
    rc = {k: F.clear_rect(lay, k) for k in lay["rooms"]}
    it = {i["id"]: i for i in F.layout(lay)}
    fp = {k: F.footprint(v) for k, v in it.items()}
    out = []
    n = {}
    spec = RS.build(lay)

    def add(kind, room, x, y, z=None, why="", card="", level=None, zone=None, **kw):
        level = level or lay["rooms"][room]["level"]
        if zone:                                   # L6b: an explicit control-zone suffix (room x function)
            zname, _, zl = zone.partition(":")        # "suffix" or "suffix:layer" (layer overrides the kind's)
            kw["extra"] = dict(kw.get("extra") or {}, zone=zname, **({"layer": zl} if zl else {}))
        if not (rc[room][0] - 1e-6 <= x <= rc[room][2] + 1e-6 and rc[room][1] - 1e-6 <= y <= rc[room][3] + 1e-6):
            for other in F._cluster(lay, room):          # an open-plan neighbour holds it: label it truthfully
                q = rc[other]
                if q[0] <= x <= q[2] and q[1] <= y <= q[3]:
                    room = other
                    break
        count = kw.pop("identity_slots", 1)
        n[room] = n.get(room, 0) + 1
        z = z if z is not None else ceiling_z(level, x, room, y, lay, spec)
        out.append(Fixture("%s-%s-%02d" % (kind, room, n[room]), kind, room, level, round(x, 3), round(y, 3),
                           round(z, 3), why=why, card=card, **kw))
        n[room] += count - 1

    def strip(kind, room, a, b, z, aim, why="", card="", level=None, lm_per_m=450.0):
        """A straight LED strip from a to b (x, y) at height z, emitting along aim."""
        (xa, ya), (xb, yb) = a, b
        L = math.hypot(xb - xa, yb - ya)
        add(kind, room, (xa + xb) / 2, (ya + yb) / 2, z, why, card, level, aim=aim, length=round(L, 3),
            along=((xb - xa) / L, (yb - ya) / L, 0.0),
            **({"lm": lm_per_m * round(L, 3)} if kind == "COVE" else {}))    # L6b: 450 lm/m: a soft wash, not 900

    def cove(room, sides, why):
        """Perimeter cove: strips on the band's inner edge along the named sides, stopped 0.3 m short of the end walls
        (p. 59), emitting up and inward onto the raised field."""
        x0, y0, x1, y1 = rc[room]
        z = LEVEL_Z[lay["rooms"][room]["level"]] + CEILING + 0.03
        b, s = COVE_BAND, 0.30
        for side in sides:
            if side == "x0":
                strip("COVE", room, (x0 + b, y0 + b + s), (x0 + b, y1 - b - s), z, (0.4, 0, 1), why)
            if side == "x1":
                strip("COVE", room, (x1 - b, y0 + b + s), (x1 - b, y1 - b - s), z, (-0.4, 0, 1), why)
            if side == "y0":
                strip("COVE", room, (x0 + b + s, y0 + b), (x1 - b - s, y0 + b), z, (0, 0.4, 1), why)
            if side == "y1":
                strip("COVE", room, (x0 + b + s, y1 - b), (x1 - b - s, y1 - b), z, (0, -0.4, 1), why)
        out[-1].extra["cove_room"] = room

    # =============== BASEMENT ===============
    L = rc["lounge"]
    for x, y in _grid((L[0], L[1], L[2], L[3]), 2, 2, mx=1.6, my=0.95):
        add("DL", "lounge", x, y, why="soft ambient, dimmable; 2 x 2 clear of the cove band (L6b: 6 -> 4, 4 m2 per fitting)",
            card="ies-res-family-room-100")
    cove("lounge", ("x0", "y0"), "cove along the street and stair sides: the ceiling floats over the family TV room")
    for x in (L[0] + 0.9, (L[0] + L[2]) / 2 + 0.9):
        add("DL", "lounge", x, (L[1] + L[3]) / 2, zone="route-night:night", extra={"dimmer": 0.15},
            why="L6b LA13: basement escape/night route from the TV room to the stair foot: battery-backed downlight at 15 % "
                "output (110 lm) on the lounge centre line; part of the night layer")
    a = fp["lounge-armchair"]
    add("ADJ", "lounge", (a[0] + a[2]) / 2 - 0.4, (a[1] + a[3]) / 2, aim=(0.35, 0, -1), zone="armchair-reading:task",
        why="reading light over the armchair, aimed ~20 deg", card="ies-res-chair-reading-200")
    from . import villa_furnish3d as F3
    for store in (piece for piece in it.values() if piece["type"] == "under_stair_storage"):
        backs = [(name, F3.to_world(store, box)) for name, box in F3.body(store)
                 if name.endswith("-back")]
        for kind, _ in store["modules"]:
            bay = [box for name, box in backs if name == kind + "-back"]
            if not bay:
                continue
            xa, xb = min(box[0] for box in bay) + 0.035, max(box[3] for box in bay) - 0.035
            y = bay[0][4] + 0.008  # on the inside face of the back panel
            z = LEVEL_Z[store["level"]] + min(box[5] for box in bay) - 0.055
            strip("BACK", store["room"], (xa, y), (xb, y), z, (0, 1, -0.35),
                  why="ASSUMED internal LED strip on the back of each open under-stair bay")
    add("DL", "lounge-nook", (rc["lounge-nook"][0] + rc["lounge-nook"][2]) / 2, (rc["lounge-nook"][1] +
        rc["lounge-nook"][3]) / 2, why="the way to the pantry", card="ies-res-passage-30")
    Pn = rc["pantry"]
    for x, y in _grid(Pn, 1, 1):          # L6c: 2 -> 1 (ERCO DL 1065 lm)
        add("DL", "pantry", x, y, why="pantry shelves", card="ies-res-storage-frequent-50")
    # stair: step markers in the party-wall side of the flight every 3rd tread, and a light at the foot
    walls_b = F._walls(spec, "B")
    for k, b in enumerate(sorted(lay and _stair_boxes(lay), key=lambda b: b[0])):
        if k % 3 == 1 and b[5] / 1000.0 + 0.25 < -0.65:        # below the beam soffit (-0.60): never in a beam
            # ON the party wall's face (the nearest wall below the tread): the treads stop 50-200 mm short of the
            # wall in the spec, and a marker set 20 mm in from the tread edge floated in the air
            xm, y0 = (b[0] + b[3]) / 2 / 1000.0, b[1] / 1000.0
            face = max(w[3] for w in walls_b if w[0] <= xm <= w[2] and w[3] <= y0 + 1e-6)
            add("STEP", "stair-b", xm, face + 0.002,
                z=b[5] / 1000.0 + 0.25, aim=(0, 1, -0.3), why="step marker 0.25 m above the tread, party wall",
                card="ies-res-stairs-50", level="B")
    H = rc["hall-b"]
    add("DL", "hall-b", (H[0] + H[2]) / 2, (H[1] + H[3]) / 2, why="stair foot and hall (L6b: 2 -> 1 on the hall centre)",
        card="ies-res-passage-30")
    E = rc["entry-b"]
    add("DL", "entry-b", (E[0] + E[2]) / 2, (E[1] + E[3]) / 2, why="entrance", card="ies-res-passage-30")
    add("WW", "entry-b", (E[0] + E[2]) / 2, E[1] + 0.35, aim=(0, -0.25, -1),
        why="washes the party wall at the entrance: a lit wall reads as welcome")
    Fm = rc["family"]
    add("DL", "family", (Fm[0] + Fm[2]) / 2, (Fm[1] + Fm[3]) / 2, why="family corner ambient (L6b: 2 -> 1 on the room centre)",
        card="ies-res-family-room-100")
    strip("NL", "family", (Fm[0] + 0.25, Fm[1] + 0.6), (Fm[0] + 0.25, Fm[3] - 0.6), LEVEL_Z["B"] + 0.05, (0.3, 0, -1),
          why="L6b: night layer on the basement route: low warm glow along the west wall (second switched layer)")
    # kitchen: globe pendants over the island (centrepiece AND the seating-side light), downlights over the run
    isl = fp["k-island"]
    top = LEVEL_Z["B"] + it["k-island"]["h"]
    cy = (isl[1] + isl[3]) / 2
    for k in range(3):
        x = isl[0] + (k + 0.5) * (isl[2] - isl[0]) / 3
        add("PEN-GLOBE", "kitchen", x, cy, z=top + 0.762 + 0.15, lm=1400, zone="island-pendants:decorative",
            why="three opal globes over the island, bottom 762 mm above the worktop; ASSUMED 1400 lm each: they light "
                "the seating side to its card", card="rid-pendant-above-table-762", extra={"hang_from": ceiling_z("B")})
    # L6b: prep light cut at source: three flush downlights (DL flood, not the 1343 lm DLN) on the prep line of the
    # counter spans + one over the induction zone; hob and prep are separate zones (300 vs 500 lx cards)
    spans = [(a_, b_) for kind, a_, b_ in F.module_spans(it["k-island"]) if kind == "counter" and b_ - a_ >= 0.5]
    prep_x = [(spans[0][0] + spans[0][1]) / 2, spans[-1][0] + (spans[-1][1] - spans[-1][0]) / 3,
              spans[-1][0] + 2 * (spans[-1][1] - spans[-1][0]) / 3]
    icx = (isl[0] + isl[2]) / 2
    # L6b iteration 4: the induction zone (300 lx) lies inside the prep strip (500 lx), so the middle downlight (over the hob)
    # is its own zone and a third prep downlight is added at the far end, away from the hob (the three on one driver gave
    # 351 lx at the hob and 371 lx on the prep strip)
    third = (isl[2] - isl[0]) / 3
    # L6c: the ERCO DL is 1065 lm (was 732): the separate hob downlight went to the 15 % floor of the driver range, so it is cut;
    # the three prep downlights (one over the hob's side, one each side) light both the 500 lx strip and the 300 lx induction zone
    # four prep downlights in two mirrored pairs about the island centre (+/-1.2 m and +/-1.5 m): a pair close to the hob lifts the
    # 300 lx induction zone to 1.2x its card when the strip reaches 500 lx (analytic search over positions, then Radiance)
    for x, zn, cd in ((icx - 1.5, "island-prep", "ies-res-kitchen-prep-500"), (icx - 1.2, "island-prep", "ies-res-kitchen-prep-500"),
                      (icx + 1.2, "island-prep", "ies-res-kitchen-prep-500"), (icx + 1.5, "island-prep", "ies-res-kitchen-prep-500"),
                      (spans[-1][0] + (spans[-1][1] - spans[-1][0]) / 2, "island-prep", "ies-res-kitchen-prep-500")):
        # V12: four DL needed 0.86 of their output at 500 lx; a fifth on the centre line of the right-hand counter module (an
        # axis of the island's own module grid, declared) brings it under 0.80 without lifting the hob (analytic search)
        # y: the prep line 200 mm inside the counter edge (the hob's 0.5 m plane then gets less of it than at 300 mm: analytic search)
        add("DL", "kitchen", x, isl[3] - 0.20, why="prep downlight on the prep line: two mirrored pairs about the island centre and one on "
            "the centre of the right-hand counter module; none over the hob", card=cd, zone=zn + ":task",
            extra={"axis": "prep line 200 mm inside the island's prep edge; x on the island centre line (+/-1.2 m, +/-1.5 m) or the "
                           "centre line of the right-hand counter module"})
    run = fp["k-run"]
    for x in ((run[0] + run[2]) / 2 - 0.45, (run[0] + run[2]) / 2 + 0.45):
        add("DL", "kitchen", x, run[3] - 0.65, why="650 mm from the wall face over the counter's front edge, 0.9 m pitch "
            "(L6b: 3 DLN -> 2 DL at the sink)", card="ies-res-kitchen-sink-300", zone="run-task:task")
    add("DL", "kitchen", (rc["kitchen"][0] + isl[0]) / 2 + 0.2, cy + 0.9, why="kitchen general",
        card="ies-res-kitchen-general-50")
    KI = rc["kitchen-island"]
    for x in (KI[0] + 0.7, KI[2] - 0.7):
        add("DL", "kitchen-island", x, (KI[1] + isl[1]) / 2, why="aisle behind the island stools",
            card="ies-res-kitchen-general-50")
    strip("TOE", "kitchen", (isl[0] + 0.05, isl[3] - 0.05), (isl[2] - 0.05, isl[3] - 0.05), LEVEL_Z["B"] + 0.05,
          (0, 0.3, -1), why="island plinth glow: night light and the island floats")
    # dining: pendant over the table (task + decorative), two adjustable fills crossing, sideboard accent
    # Client decision 2026-11-22 (docs/decisions/dining-pendant-2026-11-22.md): the single iGuzzini QA03 (O59 x 250 mm) read as an afterthought
    # over the 1.8 m table; the table gets a decorative pendant scaled to it. iGuzzini Libera System RP65 (1140 mm slim blade, 1079 lm,
    # UGR<19, 2700 K, CRI 90): 1.14 m = 63 % of the table length (policy: <= 2/3), centred on the table, 762 mm above it. The 1.5 m ERCO
    # Jilly (3558 lm) is out of policy and ran at 3.9 % of its output; the QA03 was too small. The task function is in the pendant (it must
    # meet the cards alone at <= 0.80 driver and every scene >= 15 %; see test_l6d.py), a discreet downlight is added only if it cannot.
    tb = fp["dining-table"]
    add("PEN-LIN", "dining", (tb[0] + tb[2]) / 2, (tb[1] + tb[3]) / 2,
        z=LEVEL_Z["B"] + it["dining-table"]["h"] + 0.762, extra={"hang_from": ceiling_z("B"), "zone": "table-pendant"},
        length=1.14, along=(1.0, 0.0, 0.0) if (tb[2] - tb[0]) >= (tb[3] - tb[1]) else (0.0, 1.0, 0.0),
        why="decorative linear pendant along the table, 762 mm above it", card="rid-pendant-above-table-762")
    # L6b: the two crossed adjustable fills put ~950 lx on the table centre (9x the 100 lx card; truth probe, variant A):
    # cut. The pendant is the table's light (Dinner dims it, Day lifts the homework end); the sideboard accent stays.
    sb = fp["dining-sideboard"]
    for x in (sb[0] + 0.45, sb[2] - 0.45):
        add("ADJ", "dining-side", x, sb[3] + 0.9, aim=(0, -0.55, -1), zone="sideboard-accent",
            why="accent on the sideboard and the art above it, ~30 deg", card="ldb-accent-aim-30")
    # garden living: cove, lit glass cabinets, reading in the daybed nook, soft downlights
    Lv = rc["living"]
    cove("living", ("x0", "y0"), "cove on the dining and library sides: the garden living glows at night")
    for x, y in _grid((Lv[0] + 0.3, Lv[1] + 0.3, Lv[2], Lv[3]), 2, 1, mx=0.9, my=0.9):      # L6c: 4 -> 2 (ERCO DL 1065 lm)
        add("DL", "living", x, y, why="ambient, dimmable", card="ies-res-living-30")
    for name in ("library-cabinet-left", "library-cabinet-right"):
        bk, bfp = it[name], fp[name]
        nsh = max(2, int(bk["h"] / 0.38))
        for k in range(1, nsh):
            z = LEVEL_Z["B"] + k * bk["h"] / nsh - 0.03
            strip("BACK", "bar-alcove", (bfp[0] + 0.05, bfp[1] + 0.05), (bfp[2] - 0.05, bfp[1] + 0.05), z,
                  (0, 0.3, -1), why="inside the glass-door cabinet, behind the books")
    nook = fp["library-daybed"]
    # The 25 mm nook-side panels are in F3.body. Mount on their finished INNER faces, not their centrelines.
    # ASSUMED plate/emitter height: 0.55 m above the authored 0.45 m mattress top, within seated arm reach.
    for side, face_x, direction in (("left", nook[0] + 0.025, 1), ("right", nook[2] - 0.025, -1)):
        y = (nook[1] + nook[3]) / 2
        add("SWING", "bar-alcove", face_x + direction * 0.59, y, z=LEVEL_Z["B"] + it["library-daybed"]["h"] + 0.55,
            zone="daybed-reading:task",
            why="ASSUMED side-panel plate 0.55 m above mattress; articulated arm swings over mattress",
            card="ies-res-chair-reading-200", extra={"wall_plate": (face_x, y), "mount_side": side,
                                                       "reach": 0.6, "swept_x": (min(face_x, face_x + direction * 0.6),
                                                                                  max(face_x, face_x + direction * 0.6)),
                                                       "swept_y": (y, y + math.sqrt(0.30**2 - (0.59 / 2)**2))})
    # L6b: the two recessed nook-top fills (DLN, then DL) needed a 26 % driver for a 0.7 x 0.5 m reading area: cut; the
    # two swing arms are the daybed's reading lights
    # cinema: dim wall-wash on the rear wall, low path glow, no light on the screen
    C = rc["cinema"]
    cs = fp["cinema-sofa"]
    for y in (cs[1] + 0.4, cs[3] - 0.4):
        add("DL", "cinema", (cs[0] + cs[2]) / 2 + 0.2, y, why="soft ambient over the loveseat, dimmed to off for "
            "films (the draft render showed a room with no ambient light at all)", card="ies-res-media-lcd-20")
    for y in (C[1] + 0.7, (C[1] + C[3]) / 2, C[3] - 0.7):
        add("WW", "cinema", C[0] + 0.45, y, aim=(-0.25, 0, -1), why="rear wall wash, dimmed for films (no light on "
            "the screen)", card="ies-res-media-lcd-20")
    strip("NL", "cinema", (C[0] + 0.3, C[1] + 0.05), (C[2] - 0.3, C[1] + 0.05), LEVEL_Z["B"] + 0.05, (0, 0.3, -1),
          why="low path glow to the door during a film")
    desk = fp["cinema-desk"]
    for x in (desk[0] + 0.31, desk[2] - 0.31):
        add("DESK", "cinema", x, desk[1] + 0.28, z=LEVEL_Z["B"] + VL_DESK_Z, lm=250,
            why="two shielded task lamps at the cinema desk, switched off for films (L6b: 450 -> 250 lm)",
            card="ies-res-desk-400")
    Sr = rc["store-ramp"]
    shelf = fp["store-shelves"]
    for bay in range(3):
        xa = shelf[0] + bay * (shelf[2] - shelf[0]) / 3 + 0.125
        xb = xa + 0.70
        y = min(Sr[3] - 0.25, shelf[1] - 0.28)
        z = min(ceiling_z("B", xa, "store-ramp", y, lay, spec),
                ceiling_z("B", xb, "store-ramp", y, lay, spec)) - 0.08
        strip("STORE-BATTEN", "store-ramp", (xa, y), (xb, y), z, (0, 0, -1),
              why="one downward opal batten for each height-zoned shelving bay; ASSUMED product",
              card="ies-res-storage-frequent-50")
    G = rc["guest-wc"]
    bs = fp["gwc-basin"]
    add("DL", "guest-wc", (G[0] + G[2]) / 2, (G[1] + G[3]) / 2, why="guest WC ambient", card="ies-res-shower-50")
    _sconces(add, "guest-wc", bs, lay, rc)
    DK = rc["dirty-kitchen"]
    dk = fp["dk-run"]
    n_dk = 4                                      # L6c: ERCO DL 1065 lm (was 732): 5 -> 4 evenly spaced
    for x in [dk[0] + 0.4 + i * (dk[2] - dk[0] - 0.8) / (n_dk - 1) for i in range(n_dk)]:
        add("DL", "dirty-kitchen", x, dk[1] - 0.1, why="over the heavy-cooking run (L6b: DLN 1343 lm -> DL 732 lm; V12: 4 -> 5)",
            card="ies-res-kitchen-prep-500", zone="run-task:task")
    for x in (DK[0] + 1.2, DK[2] - 1.2):
        add("DL", "dirty-kitchen", x, DK[1] + 0.9, why="laundry and folding", card="ies-res-laundry-200")
    # =============== GROUND FLOOR ===============
    # the stair void: a cluster of globes dropping into it (centrepiece seen from both floors)
    op = _gf_opening(lay)
    for k, (fx, fy, dz) in enumerate(((0.3, 0.35, 1.0), (0.55, 0.6, 1.6), (0.8, 0.4, 1.25))):
        add("PEN-GLOBE", "stair-gf", op[0] + fx * (op[2] - op[0]), op[1] + fy * (op[3] - op[1]), z=CEILING - dz,
            level="GF", extra={"hang_from": ceiling_z("GF", room="stair-gf")}, why="globe cluster dropping into the stair void: lights the "
            "flight from above and marks the heart of the house", card="ies-res-stairs-50")
    Lg = rc["landing-gf"]
    # Wall markers are +y-facing only (support_mounting hosts them on a +y shell face; the marker mesh is built in an xz
    # plane). The west-wall position (x = Lg[0]+0.02, aim +x) had no such face: 01 passed only by hosting on a hidden
    # wall end-cap 0.19 m away, 02 had nothing within 250 mm. The landing's one real +y face is the 0.285 m stub of its
    # south wall west of the door (x 3.817..4.102), so both markers sit on it, aimed along the landing toward the flight.
    for dx, aim in ((0.07, (1, 0.6, -0.2)), (0.20, (0.4, 1, -0.2))):
        add("PATH", "landing-gf", Lg[0] + dx, Lg[1] + 0.02, z=0.30, aim=aim, level="GF",
            why="L6b LA13: low marker on the landing's south wall stub: lights the top treads of the flight and the landing (night layer)")
    add("DL", "landing-gf", (Lg[0] + Lg[2]) / 2, (Lg[1] + Lg[3]) / 2, why="stair top", card="ies-res-stairs-50")
    Co = rc["corridor"]
    # client FINAL 2026-11-26: the corridor end past kids-b (x >= 17.45) is annexed to the suite as its vestibule. The row is laid out to the OLD corridor end so
    # every fixture keeps its position; the last washer (x 18.537) is inside the vestibule and is built as WW-suite-vestibule-01, while the corridor's counter skips its old
    # slot so the approved marker rows (marker-PATH-corridor-07..09) keep their ids.
    corridor_end = rc["suite-vestibule"][2]
    xs = [Co[0] + 0.9 + i * 1.75 for i in range(int((corridor_end - Co[0] - 1.0) / 1.75) + 1)]
    for x in xs:
        if x > Co[2]:        # past the suite door: the vestibule's own wall washer; the corridor's numbering keeps its slot (06) so marker-PATH-corridor-07..09 stay put
            add("WW", "suite-vestibule", x, Co[1] + 0.30, aim=(0, -0.25, -1), why="the corridor's last wall washer, now inside the suite vestibule",
                card="ies-res-passage-30")
            n["corridor"] = n.get("corridor", 0) + 1
            continue
        add("WW", "corridor", x, Co[1] + 0.30, aim=(0, -0.25, -1), why="grazing the long party wall: the corridor "
            "is lit by its wall, not by a row of spots", card="ies-res-passage-30")
    for x in xs[::2]:
        add("PATH", "corridor", x + 0.4, Co[1] + 0.02, z=0.30, aim=(0, 1, -0.4), level="GF",
            why="low path light to the bathrooms at night")
    SVr = rc["suite-vestibule"]       # client FINAL 2026-11-26: the annexed corridor end has its own ambient light (WW-corridor-06 only washes its far wall)
    add("DL", "suite-vestibule", (SVr[0] + SVr[2]) / 2, (SVr[1] + SVr[3]) / 2, why="suite vestibule ambient (the corridor's lights stop at the suite door)",
        card="ies-res-passage-30")
    Ge = rc["gallery-end"]
    add("DL", "gallery-end", (Ge[0] + Ge[2]) / 2, (Ge[1] + Ge[3]) / 2, why="gallery end", card="ies-res-passage-30")
    S = rc["study-game"]
    for x, y in _grid(S, 2, 1, mx=1.5, my=0.8):
        add("DL", "study-game", x, (S[1] + S[3]) / 2, why="study ambient (L6b: 4 -> 2)", card="ies-res-game-digital-6")
    d1 = fp["study-desk"]
    for y in (d1[1] + 0.45, d1[3] - 0.45):
        add("DL", "study-game", d1[2] - 0.05, y, why="desk light over the shared homework desk's front edge "
            "(no shadow of the head); L6b: DL", card="ies-res-desk-400", zone="desk-task:task")
    d2 = fp["study-adult-desk"]
    for x in ((d2[0] + d2[2]) / 2,):       # L6c: 2 -> 1 (ERCO DL 1065 lm)
        add("DL", "study-game", x, d2[1] - 0.05, why="desk light over the adult desk; L6b: DL (V12: 1 -> 2, one needed 1.12 of driver output)",
            card="ies-res-desk-400", zone="desk-adult:task")
    FB = rc["family-bath"]
    add("DL", "family-bath", (FB[0] + FB[2]) / 2 + 0.2, (FB[1] + FB[3]) / 2 - 0.3, why="bath ambient",
        card="ies-res-shower-50")
    sh = fp["fb-shower"]
    add("DL", "family-bath", (sh[0] + sh[2]) / 2, (sh[1] + sh[3]) / 2, why="shower (wet-rated); L6b: DL",
        card="ies-res-shower-50", zone="shower:task")
    _sconces(add, "family-bath", fp["fb-basin"], lay, rc, counter=True)    # L6b V12: the two sconces alone needed 1.20 of driver output; the counter downlight is back
    bb = fp["fb-basin"]
    strip("TOE", "family-bath", (bb[2] + 0.02, bb[1] + 0.03), (bb[2] + 0.02, bb[3] - 0.03), 0.30, (0.3, 0, -1),
          level="GF", why="glow under the basin: night light")
    for room, desks, beds in (("kids-a", ("ka-desk-1", "ka-desk-2"), ("ka-loft-1", "ka-loft-2")), ("kids-b", ("kb-desk",), ("kb-bed",))):
        K = rc[room]
        for x, y in _grid(K, 1, 1, mx=0.9):          # L6c: 2 -> 1 ambient (ERCO DL 1065 lm); each desk gets its own task downlight
            if room == "kids-b":     # L6d LA4 (lying, looking up): the bed's pillow end is the west wall; a DL within 45 deg of the vertical
                x = (fp["kb-desk"][0] + fp["kb-desk"][2]) / 2         # over it was 113 931 cd/m2; over the desk axis it is 2.25 m from the pillow
            add("DL", room, x, (K[1] + K[3]) / 2 - 0.3, why="bedroom ambient", card="ies-res-bedroom-general-50")
        for d in desks:
            q = fp[d]
            if room == "kids-a":
                # client 2026-11-25: the desk is under a loft bed, so a ceiling downlight is shaded by the bed above (the engine does not
                # model shadows): the task light is an under-loft strip (iGuzzini Underscore15 ST49 basis, 680 lm/m) + the child's own lamp
                (xa, xb) = (q[0] + 0.15, q[2] - 0.15) if it[d]["rot"] in (0, 180) else (None, None)
                if xa is None:                                     # desk along y against a side wall: strip along y, 0.20 m off the wall
                    x_ = (q[0] + 0.20) if it[d]["rot"] == -90 else (q[2] - 0.20)
                    strip("UC", room, (x_, q[1] + 0.10), (x_, q[3] - 0.10), LEVEL_Z["GF"] + 1.40, (0, 0, -1), level="GF",
                          why="under-loft desk strip (loft underside 1.42 m): task light for the desk below, shielded by the frame")
                add("DESK", room, (q[0] + q[2]) / 2, (q[1] + q[3]) / 2 + 0.05, z=VL_DESK_Z, level="GF",
                    why="each child's own adjustable, shielded desk lamp (advisory KID-DESK): its light stays on the desk, "
                        "out of the sleep zone", card="ies-res-desk-400")
                continue
            add("DL", room, (q[0] + q[2]) / 2, (q[1] + q[3]) / 2 + 0.10, why="L6c: desk downlight in front of the child (Lucy alone "
                "(234 lm) cannot reach 400 lx at a safe driver setting)", card="ies-res-desk-400", zone="task:task")
            add("DESK", room, (q[0] + q[2]) / 2, (q[1] + q[3]) / 2 + 0.05, z=VL_DESK_Z, level="GF", 
                why="each child's own adjustable, shielded desk lamp (advisory KID-DESK): its light stays on the desk, "
                    "out of the sleep zone", card="ies-res-desk-400")
        for bed in beds:
            q = fp[bed]
            if room == "kids-a":                        # the loft stands on the south wall: glow at its foot, inside the room
                strip("NL", room, (q[0] + 0.05, q[1] + 0.03), (q[2] - 0.05, q[1] + 0.03), 0.08, (0, 0.3, -1), level="GF",
                      why="warm glow at the foot of the loft bed: kids' night light")
                continue
            strip("NL", room, (q[0] + 0.05, q[1] - 0.02), (q[2] - 0.05, q[1] - 0.02), 0.08, (0, -0.3, -1), level="GF",
                  why="warm glow under the bed side: kids' night light")
    # parents' bedroom: headboard cove, swing-arm bedside lights, reading spots, vanity accent, soft ambient
    PB = rc["parents-bed"]
    b = fp["pb-bed"]
    # client FINAL 2026-11-26 (R3): the head is on the window wall, so the cove (which must not face glass) moves to the slat wall, the
    # corridor-side west wall x = PB[0]: the strip stands 0.12 m off it and aims along the slats, up and into the room
    strip("COVE", "parents-bed", (PB[0] + 0.12, PB[1] + 0.15), (PB[0] + 0.12, PB[3] - 0.15), CEILING + 0.03,
          (0.4, 0, 1), why="slat-wall cove: warm light grazing the slat feature wall (client R3: the cove must not face the glass behind the head)")
    # Reading lights: swing arms CLAMPED TO THE HEAD PANEL (its top rail is at the 0.90 m sill), the head 0.10 m in front of the panel face and
    # 1.30 m up, aimed at the pillow. Supply: 24 V DC from the panel-integrated driver (electrical device `bed_head_supply`, see docs/lanes/DF-built.md).
    for x in (b[0] + 0.18, b[2] - 0.18):
        add("WALL-READ", "parents-bed", x, b[3] - 0.10, z=1.30, aim=(0, -0.3, -0.55), zone="bed-reading:task", lm=300,
            why="swing arm clamped to the low head panel's top rail, aimed at the pillow; clear of both passages")
    # L6b: the two straight-down adjustable reading spots gave 790 lx on each pillow (4x the 200 lx card): cut; the
    # swing-arm lamps on the head wall are the reading lights
    # L6c: 2 -> 1 ambient (ERCO DL 1065 lm). The one kept is the west one by the entry: the bed-foot one is 23 000 cd/m2 into the eye
    # of a person lying on the bed (LA4 cap 3000), which the old 732 lm fittings did not show
    # L6d LA4 'lying, looking up': that DL (19.03, -25.19) was 89 953 cd/m2 at 39.4 deg off the vertical of a person lying on the pillow
    # (118 820 at pillow 1, 34 deg). The 45 deg cone over the pillows (eye 0.7 m, ceiling 2.7 m) has a 2.0 m radius: the ambient DL
    # now stands at the foot of the bed on its axis, 0.16 m off the south wall, 2.28 m from the nearer pillow
    for x, y in (((b[0] + b[2]) / 2, PB[1] + 0.16),):       # R3: the foot of the bed is now on the south side (head on the window wall)
        add("DL", "parents-bed", x, y, why="ambient, dimmable (foot of the bed: outside the 45 deg cone over the pillows)",
            card="ies-res-bedroom-general-50", zone="ambient")
    v = fp["pb-vanity"]
    add("ADJ", "parents-bed", v[0] - 0.35, (v[1] + v[3]) / 2, aim=(0.35, 0, -1), why="vanity light",
        card="ies-res-vanity-grooming-300")
    PE = rc["parents-entry"]
    ys = PE[3] - LOBBY_COVE_DEPTH + LOBBY_COVE_SETBACK     # on the band, behind the upstand
    strip("COVE", "parents-entry", (PE[0] + 0.1, ys), (PE[2] - 0.1, ys), CEILING + 0.02, (0, -0.4, 1),
          why="entry lobby cove on the bedroom side, aimed up and into the lobby: a 0.30 m band at 2.70 with a 30 mm upstand, the strip standing on the band "
              "30 mm behind the upstand (z 2.72) in a closed trough under the 2.80 soffit: hidden from the pillows by the band, from the lobby by the upstand (LA4)",
          card="ies-res-passage-30", lm_per_m=LOBBY_COVE_LM_PER_M)
    out[-1].extra["cove_band"] = dict(room="parents-entry", side="y1", depth=LOBBY_COVE_DEPTH)
    # L6d LA4: the entry lobby DL (18.98, -26.98) is open to the bed (no door: it is the passage into the bedroom) and 1.2-1.8 m
    # from the pillows, inside the 45 deg cone (122 595 cd/m2). No point of the 1.0 x 0.68 m lobby is 2.0 m from both pillows, so the
    # downlight is replaced by the cove above (generic, hidden behind its upstand: ASSUMED, not an LA4 product check).
    # dressing: light inside the hanging, and an aisle light
    for w in ("pd-hang-1", "pd-hang-2"):
        q = fp[w]
        strip("RAIL", "parents-dressing" if w == "pd-hang-1" else "parents-dressing-ext",
              (q[0] + 0.05, (q[1] + q[3]) / 2), (q[2] - 0.05, (q[1] + q[3]) / 2), 2.05, (0, 0, -1), level="GF",
              why="LED over the rail: clothes lit from the front-top", card="ies-res-walkin-closet-300")
    for w in ("pd-hang-1", "pd-hang-2"):
        q = fp[w]
        room_ = "parents-dressing" if w == "pd-hang-1" else "parents-dressing-ext"
        n_ = max(1, int(round((q[2] - q[0]) / 1.0)))
        front = q[1] if it[w]["rot"] == 0 else q[3]
        for k in range(n_ + 1):
            x_ = q[0] + 0.03 + k * (q[2] - q[0] - 0.06) / n_
            add("VSTRIP", room_, x_, front, z=1.10, level="GF", length=1.8, along=(0.0, 0.0, 1.0),
                aim=(0, -1 if it[w]["rot"] == 0 else 1, 0),
                why="vertical strip at a section edge: shadow-free light on the clothes (advisory C-LIGHT; its "
                    "4000 K withdrawn by the client)", card="ies-res-walkin-closet-300")
    D = rc["parents-dressing"]
    for x in (D[0] + 0.7, D[2] - 0.8):
        add("DL", "parents-dressing", x, (fp["pd-hang-1"][1] + fp["pd-hang-2"][3]) / 2, why="dressing aisle",
            card="ies-res-dressing-general-100")
    PEn = rc["parents-ensuite"]
    bt = fp["pe-bath"]
    ym = (bt[3] + PEn[3]) / 2                         # between the bath's edge and the door wall: not over the tub
    for x in (PEn[0] + 0.30, PEn[2] - 0.30):
        add("WW", "parents-ensuite", x, ym, aim=(-0.25 if x < (PEn[0] + PEn[2]) / 2 else 0.25, 0, -1),
            why="washes the marble wall; no direct downlight over the tub (advisory B-NODOWN)", card="ies-res-shower-50")
    _sconces(add, "parents-ensuite", fp["pe-basin"], lay, rc, vertical=True)
    pw, eg = BATH_PANEL["width"] / 2, BATH_PANEL["edge_gap"]
    pcx, wy = (bt[0] + bt[2]) / 2, PEn[1] + BATH_PANEL["strip_off"]       # the panel is centred on the bath, on the wall behind it
    zc, zh = (BATH_PANEL["strip_z0"] + BATH_PANEL["z1"]) / 2, BATH_PANEL["z1"] - BATH_PANEL["strip_z0"]
    for s_, side in ((-1, "left"), (1, "right")):
        add("PCOVE", "parents-ensuite", pcx + s_ * (pw + eg), wy, z=zc, level="GF", length=round(zh, 3), along=(0.0, 0.0, 1.0),
            aim=(-0.8 * s_, 0.6, 0.0), zone="pcove:decorative", extra=dict(dimmer=BATH_PANEL["dimmer"]),
            why="LED cove, %s edge of the bath feature panel (client reference image12)" % side)
    add("PCOVE", "parents-ensuite", pcx, wy, z=BATH_PANEL["z1"] + eg, level="GF", length=round(2 * (pw + eg), 3), along=(1.0, 0.0, 0.0),
        aim=(0.0, 0.5, -0.87), zone="pcove:decorative", extra=dict(dimmer=BATH_PANEL["dimmer"]),
        why="LED cove, top edge of the bath feature panel: washes the panel face from above")
    # ASSUMED initial driver setting; final dimmer scene is measured in the render.
    for fixture in out:
        if fixture.room == "parents-ensuite" and fixture.layer != "task":      # L6c: the tuned task layer gets its driver from the table
            fill_defaults(fixture.extra, {"dimmer": 0.4})
    pb_ = fp["pe-basin"]
    strip("TOE", "parents-ensuite", (pb_[2] + 0.02, pb_[1] + 0.03), (pb_[2] + 0.02, pb_[3] - 0.03), 0.30,
          (0.3, 0, -1), level="GF", why="glow under the vanity: night light")
    # client 2026-11-25: wall cupboards over the sink run shade the back of the worktop from the two sink downlights (probe: direct
    # 288 -> 270 lx, min 127 -> 6 lx at the wall); an under-cupboard strip (iGuzzini Underscore15 ST49 basis) lights it. Appended last so
    # no existing kitchen fixture id changes.
    kr = fp["k-run"]
    strip("UC", "kitchen", (kr[0] + 0.03, kr[3] - 0.27), (kr[2] - 0.03, kr[3] - 0.27), LEVEL_Z["B"] + 1.48, (0, 0.5, -1),
          why="under-cupboard task strip over the sink run (cupboard underside 1.50 m, 0.27 m off the wall)", card="ies-res-kitchen-sink-300")
    out[-1].extra["zone"] = "run-uc"
    set_out(out, rc, it, fp)
    apply_drivers(out)
    return out


def beams():
    """The kept structural beams (villa_env), metres: (id, x0, y0, x1, y1, z0, z1)."""
    from .. import villa_env as E
    out = []
    for e in E.spec()["elements"]:
        if e["id"].startswith("beam-"):
            xs = [q[0] / 1000 for q in e["pts"]]
            ys = [q[1] / 1000 for q in e["pts"]]
            out.append((e["id"], min(xs), min(ys), max(xs), max(ys), e["z0"] / 1000, e["z1"] / 1000))
    return out


def beam_free_x(x, y, margin=0.12):
    """The largest x' <= x such that (x', y) is clear of every basement-ceiling beam over that y."""
    for b in beams():
        if b[2] <= y <= b[4] and b[1] - margin <= x <= b[3] + margin and b[5] < -0.25:
            x = min(x, b[1] - margin)
    return x


def beam_clashes(fixtures):
    """Fittings recessed into / mounted on a kept beam: a fitting cannot be recessed into structure."""
    out = []
    for f in fixtures:
        if VL_MOUNTS.get(KINDS[f.kind]["mount"]) is None:
            continue
        for b in beams():
            if b[1] - 0.04 <= f.x <= b[3] + 0.04 and b[2] - 0.04 <= f.y <= b[4] + 0.04 and \
                    b[5] - 0.05 <= f.z <= b[6] + 0.05:
                out.append("%s in or on %s" % (f.id, b[0]))
    return out


VL_MOUNTS = {"recessed": True, "wall-marker": True}


def _stair_boxes(lay):
    from . import revit_spec as RS
    return [b for b in RS.build(lay)["stair"] if b[5] - b[2] < 300]      # treads (mm), not the landing slab


def _gf_opening(lay):
    from . import revit_spec as RS
    return RS.build(lay)["gf_opening"]


def _sconces(add, room, basin, lay, rc, vertical=False, counter=True):
    """Two sconces either side of the mirror over a basin on a wall, 0.95 m apart at 1.60 m AFF (card
    rid-vanity-sconces-914: 914-1016 mm apart, eye level)."""
    kind = "VSCONCE" if vertical else "SCONCE"
    housing = FIXTURE_KINDS[kind].housing
    wall_offset = housing["wall_offset"]
    half_spacing = housing["vanity_half_spacing"]
    x0, y0, x1, y1 = basin
    r = rc[room]
    lv = lay["rooms"][room]["level"]
    z = LEVEL_Z[lv] + 1.60
    # Eh on the counter needs light from above: a task downlight 0.3 m in front of the mirror wall (the sconces
    # give the face its vertical light, Ev)
    if counter:
        if abs(x0 - r[0]) < 0.05 or abs(x1 - r[2]) < 0.05:
            dx = r[0] + 0.35 if abs(x0 - r[0]) < 0.05 else r[2] - 0.35
            add("DL", room, dx, (y0 + y1) / 2, why="basin counter light, in front of the mirror (L6b: DL, driver set to the card)",
                card="ies-res-vanity-grooming-300", level=lv, zone="basin-task:task")
        else:
            dy = r[1] + 0.35 if abs(y0 - r[1]) < 0.05 else r[3] - 0.35
            add("DL", room, (x0 + x1) / 2, dy, why="basin counter light, in front of the mirror (L6b: DL, driver set to the card)",
                card="ies-res-vanity-grooming-300", level=lv, zone="basin-task:task")
    if abs(x0 - r[0]) < 0.05 or abs(x1 - r[2]) < 0.05:           # basin against an x wall: mirror on that wall
        wx = r[0] + wall_offset if abs(x0 - r[0]) < 0.05 else r[2] - wall_offset
        cy = (y0 + y1) / 2
        from .sanitary_relocation import historical_input
        correction = False
        if not historical_input() and room not in VANITY_DECISIONS:
            cy, correction = vanity_pair_datum(r, cy, kind)
            if correction:
                from .mounting import finish_from_record
                # The already-approved marble finish shifts the fixing face.
                wx += (1 if wx < (r[0]+r[2])/2 else -1)*finish_from_record('marble-wall-thinset').thickness_m
        if not historical_input() and room in VANITY_DECISIONS:
            from .mounting import finish_from_record
            basin_item = next(i for i in F.layout(lay) if F.footprint(i) == basin and i['room'] == room)
            mirror_width = min(basin_item['w']-.04,.78)
            mirror_top = LEVEL_Z[lv]+basin_item['h']+.95
            normal = 1 if abs(x0-r[0]) < .05 else -1
            finished_wall = (r[0] if normal > 0 else r[2])+normal*finish_from_record('marble-wall-thinset').thickness_m
            bx, by, bz = over_mirror_datum(r,basin,mirror_width,mirror_top,finished_wall,normal)
            h = FIXTURE_KINDS['VANITY-LIN'].housing
            add('VANITY-LIN',room,bx,by,z=bz,aim=(normal,0,0),length=h['length'],along=(0,1,0),
                identity_slots=2, why=VANITY_DECISION_SOURCE+'; ASSUMED over-mirror linear LED bar',
                card='ies-res-vanity-grooming-300',level=lv,
                extra=dict(over_mirror=True,decision_source=VANITY_DECISION_SOURCE,
                    retired_fixture_ids=VANITY_DECISIONS[room],mirror_id='mirror-'+basin_item['id'],
                    room_rect=r,finished_wall=finished_wall,ceiling_z=ceiling_z(lv,bx,room,by,lay),
                    assumptions=('ASSUMED authored: %g mm length, %g mm height, %g mm depth; '
                        'centre %g mm above mirror top; %g lm raw; no verified product' %
                        (h['length']*1000,h['half_height']*2000,h['half_depth']*2000,
                         h['centre_above_mirror']*1000,FIXTURE_KINDS['VANITY-LIN'].spec['lm']))))
        else:
            for s in (-1, 1):
                add(kind, room, wx, cy + s * half_spacing, z=z,
                    aim=(1 if wx < (r[0] + r[2]) / 2 else -1, 0, 0),
                    why="grooming light each side of the mirror", card="rid-vanity-sconces-914", level=lv,
                    **({'extra': {'vanity_pair_source_correction': True}} if correction else {}))
        if vertical:                                  # backlit mirror halo (advisory B-VANITY)
            wx = r[0] + wall_offset if abs(x0-r[0]) < 0.05 else r[2] - wall_offset
            cy = (y0+y1)/2
            add("MIRROR", room, wx + (0.01 if wx < (r[0] + r[2]) / 2 else -0.01), cy, z=z, level=lv, length=0.7,
                along=(0.0, 1.0, 0.0), aim=(1 if wx < (r[0] + r[2]) / 2 else -1, 0, 0),
                why="backlit mirror: soft light behind the glass (advisory B-VANITY)")
    else:
        wy = r[1] + wall_offset if abs(y0 - r[1]) < 0.05 else r[3] - wall_offset
        cx = (x0 + x1) / 2
        for s in (-1, 1):
            add("SCONCE", room, cx + s * half_spacing, wy, z=z, aim=(0, 1 if wy < (r[1] + r[3]) / 2 else -1, 0),
                why="grooming light each side of the mirror", card="rid-vanity-sconces-914", level=lv)


# ------------------------------------------------------------------ photometry
def generic_ies(lm, beam_deg, name="GENERIC"):
    """LM-63-2002 text for a rotationally symmetric I = I0 cos^n(theta) distribution with FWHM beam_deg and total
    flux lm (downward hemisphere). n from cos^n(beam/2) = 1/2; flux 2 pi I0 / (n + 1). beam None: an isotropic
    sphere (opal globe), I = lm / (4 pi) in all directions."""
    angles = [float(a) for a in range(0, 181, 5)]
    if beam_deg is None:
        cd = [lm / (4 * math.pi)] * len(angles)
    else:
        nn = math.log(0.5) / math.log(math.cos(math.radians(beam_deg / 2)))
        i0 = lm * (nn + 1) / (2 * math.pi)
        cd = [i0 * max(0.0, math.cos(math.radians(a))) ** nn if a < 90 else 0.0 for a in angles]
    lines = ["IESNA:LM-63-2002", "[TEST] archpipe generic", "[MANUFAC] GENERIC (not a product)",
             "[LUMINAIRE] %s cos^n beam %s deg, %d lm" % (name, beam_deg, lm), "TILT=NONE",
             "1 %.3f 1 %d 1 1 2 0 0 0" % (lm, len(angles)), "1 1 0",
             " ".join("%.1f" % a for a in angles), "0.0", " ".join("%.3f" % c for c in cd)]
    return "\n".join(lines) + "\n"


def photometry_for(kind):
    return kind_photometry(kind)


# ------------------------------------------------------------------ the check
def task_points(lay=None, *, with_hosts=False):
    """(room, card, x, y, plane z absolute, label): the carded task planes of D1.

    with_hosts appends the authored furniture item identity; x/y/z are metres."""
    lay = lay or R.design("D1")
    it = {i["id"]: i for i in F.layout(lay)}
    fp = {k: F.footprint(v) for k, v in it.items()}
    B, G = LEVEL_Z["B"], LEVEL_Z["GF"]
    pts = []

    def add(host, point):
        pts.append((*point, host) if with_hosts else point)

    def c(k):
        q = fp[k]
        return (q[0] + q[2]) / 2, (q[1] + q[3]) / 2

    isl = fp["k-island"]
    prep_spans = [(a, b) for kind, a, b in F.module_spans(it["k-island"])
                  if kind == "counter" and b - a >= 0.5]
    prep_x = [(prep_spans[0][0] + prep_spans[0][1]) / 2,
              prep_spans[-1][0] + (prep_spans[-1][1] - prep_spans[-1][0]) / 3,
              prep_spans[-1][0] + 2 * (prep_spans[-1][1] - prep_spans[-1][0]) / 3]
    for x in prep_x:
        add("k-island", ("kitchen", "ies-res-kitchen-prep-500", x, isl[3] - 0.3, B + 0.92, "island prep side"))
        add("k-island", ("kitchen", "ies-res-breakfast-200", x, isl[1] + 0.2, B + 0.92, "island seating side"))
    burner = next((a, b) for kind, a, b in F.module_spans(it["k-island"]) if kind == "single-induction")
    add("k-island", ("kitchen", "ies-res-kitchen-cooktop-300", (burner[0] + burner[1]) / 2,
                (isl[1] + isl[3]) / 2, B + 0.926, "single induction zone"))
    run = fp["k-run"]
    add("k-run", ("kitchen", "ies-res-kitchen-sink-300", (run[0] + run[2]) / 2, run[1] + 0.25, B + 0.9, "sink"))
    add("dining-table", ("dining", "ies-res-dining-informal-100", *c("dining-table"), B + 0.75, "dining table centre"))
    dt = fp["dining-table"]
    add("dining-table", ("dining", "ies-res-dining-study-200", dt[0] + 0.3, (dt[1] + dt[3]) / 2, B + 0.75, "table end (homework)"))
    dk = fp["dk-run"]
    add("dk-run", ("dirty-kitchen", "ies-res-kitchen-prep-500", dk[0] + 1.5, dk[1] + 0.3, B + 0.9, "dirty kitchen run"))
    for d, lv in (("study-desk", G), ("study-adult-desk", G), ("ka-desk-1", G), ("ka-desk-2", G), ("kb-desk", G)):
        add(d, (it[d]["room"], "ies-res-desk-400", *c(d), lv + 0.75, d))
    b = fp["pb-bed"]
    for x in (b[0] + 0.4, b[2] - 0.4):
        add("pb-bed", ("parents-bed", "ies-res-bed-reading-200", x, b[3] - 0.35, G + 0.9, "pillow"))
    for basin, room in (("fb-basin", "family-bath"), ("pe-basin", "parents-ensuite"), ("gwc-basin", "guest-wc")):
        lv = B if room == "guest-wc" else G
        add(basin, (room, "ies-res-vanity-grooming-300", *c(basin), lv + 0.91, basin))
    a = fp["lounge-armchair"]
    add("lounge-armchair", ("lounge", "ies-res-chair-reading-200", *c("lounge-armchair"), B + 0.76, "armchair"))
    add("library-daybed", ("bar-alcove", "ies-res-chair-reading-200", *c("library-daybed"), B + 0.76, "daybed nook"))
    desk = fp["cinema-desk"]
    for x in (desk[0] + 0.31, desk[2] - 0.31):
        add("cinema-desk", ("cinema", "ies-res-desk-400", x, (desk[1] + desk[3]) / 2, B + 0.75, "cinema desk"))
    return pts


ROOM_TARGETS = {   # room -> general card (floor average, direct only: advisory)
    "lounge": "ies-res-family-room-100", "family": "ies-res-family-room-100", "living": "ies-res-living-30",
    "kitchen": "ies-res-kitchen-general-50", "kitchen-island": "ies-res-kitchen-general-50",
    "hall-b": "ies-res-passage-30", "corridor": "ies-res-passage-30", "suite-vestibule": "ies-res-passage-30", "study-game": "ies-res-game-digital-6",
    "kids-a": "ies-res-bedroom-general-50", "kids-b": "ies-res-bedroom-general-50",
    "parents-bed": "ies-res-bedroom-general-50", "parents-dressing": "ies-res-dressing-general-100",
    "cinema": "ies-res-media-lcd-20", "dirty-kitchen": "ies-res-laundry-200", "pantry": "ies-res-storage-frequent-50",
    "store-ramp": "ies-res-storage-frequent-50",
    "family-bath": "ies-res-shower-50", "parents-ensuite": "ies-res-shower-50", "guest-wc": "ies-res-shower-50",
}


def card_value(cid):
    import json
    from pathlib import Path
    lib = json.loads((Path(__file__).resolve().parents[3] / "knowledge" / "library.json").read_text(encoding="utf-8"))
    return next(c["verified_value"] for c in lib["evidence"] if c["id"] == cid)


def task_beam_obstructions(lay, fixtures):
    """Report diffusing fixture spheres that intersect a downward task cone above its task plane.

    The beam angle is the fixture/product specification; the body diameter is the fixture specification.
    A sphere/cone overlap is a conservative shadow warning (IES task cards name the task plane).
    """
    planes = task_points(lay)
    problems = []
    for task in fixtures:
        if task.kind != "DLN" or task.aim != (0.0, 0.0, -1.0):
            continue
        beam = products().get(task.kind, {}).get("beam", task.spec["beam"])
        radius_slope = math.tan(math.radians(beam / 2))
        for body in fixtures:
            if body is task or body.level != task.level or "diameter" not in body.spec:
                continue
            if not _same_space(lay, body.room, task.room):
                continue
            radius = body.spec["diameter"] / 2
            center_z = body.z + radius if body.spec["mount"] == "pendant" else body.z
            if center_z + radius >= task.z or not any(room == task.room and zp < center_z - radius
                                                       for room, _, _, _, zp, _ in planes):
                continue
            lateral = math.hypot(task.x - body.x, task.y - body.y)
            cone_radius = (task.z - center_z) * radius_slope
            if lateral < cone_radius + radius - 1e-6:
                problems.append("%s cone intersects %s: lateral %.3f m, cone+body %.3f m "
                                "(beam %.1f deg; card %s)" %
                                (task.id, body.id, lateral, cone_radius + radius, beam, task.card))
    return problems


def swing_envelope_problems(lay, fixtures):
    nook = next(i for i in F.layout(lay) if i["id"] == "library-daybed")
    x0, y0, x1, y1 = F.footprint(nook)
    out = []
    for lamp in (f for f in fixtures if f.kind == "SWING" and f.room == "bar-alcove"):
        plate = lamp.extra.get("wall_plate")
        sweep = lamp.extra.get("swept_x")
        sweep_y = lamp.extra.get("swept_y")
        side = lamp.extra.get("mount_side")
        reach = lamp.extra.get("reach", 0)
        face_x = x0 + 0.025 if side == "left" else x1 - 0.025 if side == "right" else None
        if not plate or not sweep or not sweep_y or face_x is None or not (
                abs(plate[0] - face_x) <= 1e-6 and y0 + 0.06 <= plate[1] <= y1 - 0.06 and
                x0 + 0.025 <= sweep[0] <= sweep[1] <= x1 - 0.025 and
                y0 + 0.06 <= sweep_y[0] <= sweep_y[1] <= y1 - 0.06 and
                x0 + 0.06 <= lamp.x <= x1 - 0.06 and y0 + 0.06 <= lamp.y <= y1 - 0.06 and
                (lamp.x - plate[0]) * (1 if side == "left" else -1) > 0 and
                math.dist((lamp.x, lamp.y), plate) <= reach + 1e-6):
            out.append("%s arm leaves the mattress/nook or exceeds %.2f m ASSUMED reach "
                       "(TODO swing-arm-product; card ies-res-chair-reading-200)" % (lamp.id, reach))
    return out


def check(lay=None, fixtures=None):
    """Achieved vs required. Task points: direct maintained lux from every fixture of the room's level above the
    plane (points carry a verdict). Rooms: floor-average direct lux (advisory). Strips count as a row of points."""
    from .. import lighting as Lx
    lay = lay or R.design("D1")
    fixtures = fixtures or design(lay)
    lums, generic, cache = {}, set(), {}
    for f in fixtures:
        if f.kind in ("COVE",):                     # indirect: lights the ceiling, not the plane directly
            continue
        if f.kind not in cache:
            pho, gen = photometry_for(f.kind)
            cache[f.kind] = (pho, gen, pho.integrated_flux())
        pho, gen, flux = cache[f.kind]
        if gen:
            generic.add(f.kind)
        for x, y, z, lm in _emitters(f):          # the file's SHAPE, the spec's lumens
            lums.setdefault(f.level, []).append((f, x, y, z, pho, lm / flux if flux else 0.0))
    rows = []
    for room, card, x, y, zp, label in task_points(lay):
        lv = lay["rooms"][room]["level"]
        e = MF * sum(s * p.illuminance_at(x - fx, y - fy, fz - zp) for f, fx, fy, fz, p, s in lums.get(lv, [])
                     if fz > zp and _same_space(lay, f.room, room))
        need = card_value(card)
        rows.append({"room": room, "what": label, "card": card, "achieved_lx": round(e), "required_lx": need,
                     "status": "pass" if e >= need else "fail"})
    rooms = []
    for room, card in ROOM_TARGETS.items():
        r = lay["rooms"][room]
        x0, y0, x1, y1 = F.clear_rect(lay, room)
        zp = LEVEL_Z[r["level"]]
        # the open cluster is a property of the room, not of each grid point: computing it once per room took the
        # check from 180 s to seconds (it had been recomputed for every fixture at every point)
        space = {room} | set(F._cluster(lay, room))
        here = [(fx, fy, fz, p, s) for f, fx, fy, fz, p, s in lums.get(r["level"], []) if fz > zp and f.room in space]
        vals = []
        for i in range(int((x1 - x0) / 0.25)):
            for j in range(int((y1 - y0) / 0.25)):
                x, y = x0 + (i + 0.5) * 0.25, y0 + (j + 0.5) * 0.25
                vals.append(MF * sum(s * p.illuminance_at(x - fx, y - fy, fz - zp) for fx, fy, fz, p, s in here))
        avg = sum(vals) / max(1, len(vals))
        need = card_value(card)
        rooms.append({"room": room, "card": card, "avg_floor_lx_direct": round(avg), "required_lx": need,
                      "status": "pass" if avg >= need else ("advisory" if avg >= 0.75 * need else "fail")})
    # ASSUMED maximum 3.0 times the task target; TODO ies-task-excess-ratio.
    excess = ["%s/%s %d lx, target %d lx, ASSUMED maximum %d lx (3.0 x; TODO ies-task-excess-ratio)" %
              (row["room"], row["what"], row["achieved_lx"], row["required_lx"], 3 * row["required_lx"])
              for row in rows if row["achieved_lx"] > 3 * row["required_lx"]]
    return {"tasks": rows, "rooms": rooms, "generic_kinds": sorted(generic),
            "problems": task_beam_obstructions(lay, fixtures) + swing_envelope_problems(lay, fixtures) + excess,
            "note": "maintained (MF %.1f), DIRECT ONLY (inter-reflection ignored: conservative); coves excluded "
                    "(indirect); excess ratio ASSUMED 3.0 (TODO ies-task-excess-ratio)" % MF}


def _same_space(lay, a, b):
    """A fixture lights a point if both are in the same open cluster (open-plan joins; walls block otherwise)."""
    return a == b or a in F._cluster(lay, b)


def _emitters(f):
    """Analytic emitters: one point, or one sample per 0.25 metre of strip."""
    record = f.record
    x, y, z = record.position
    if record.length and record.length > 0:
        nseg = max(1, int(round(record.length / 0.25)))
        out = []
        for k in range(nseg):
            t = (k + 0.5) / nseg - 0.5
            out.append((x + record.along[0] * t * record.length, y + record.along[1] * t * record.length,
                        z + record.along[2] * t * record.length, record.flux_lm / nseg))
        return out
    return [(x, y, z, record.flux_lm)]


# ------------------------------------------------------------------ scenes (LA10)
# Level (0..1) of each control zone per scene, per Radiance cluster. A key is '*layer' (every zone of that layer) or a
# zone-id suffix ('island-prep' matches Z-B-KITCHEN-ISLAND-PREP); later keys override earlier ones; missing = off.
# Owners: each IES task card is met in ONE scene (Dinner 100 lx table, Cook 500 lx prep, Day 200 lx seating/homework and
# the desks/basins, Reading 200 lx armchair/daybed/pillow). Night = low path/marker level; Film = cinema and lounge.
_DAY = {"*ambient": 1.0, "*task": 1.0, "*accent": 1.0, "*decorative": 1.0}
_EVENING = {"*ambient": 0.4, "*accent": 0.7, "*decorative": 0.7}
_NIGHT = {"*night": 0.1}
SCENES = {
    "B-open": {
        "Day": {"*ambient": 1.0, "island-pendants": 1.0, "table-pendant": 1.0, "*accent": 0.5},
        "Cook": {"*ambient": 1.0, "island-pendants": 0.3, "island-prep": 1.0, "run-task": 1.0},
        "Dinner": {"table-pendant": 0.41, "island-pendants": 0.3, "*decorative": 0.3, "living-ambient": 0.2,
                   "sideboard-accent": 1.0},
        "Evening": {"*ambient": 0.4, "*decorative": 0.7, "*accent": 0.7, "table-pendant": 0.42, "island-pendants": 0.4},
        # L6d: every zone in every scene runs at >= 15 % of its output unless it is a night/film orientation level (see test_l6d.py): the table
        # pendant (RP65 since the client decision of 2026-11-22, driver 0.37) at 0.41 / 0.42 in Dinner / Evening = 15.2 / 15.5 %, the island globes (driver 0.70) at 0.22 in Reading = 15.4 % (was 0.2 = 14 %)
        "Reading": {"armchair-reading": 1.0, "daybed-reading": 1.0, "*ambient": 0.15, "*decorative": 0.2, "island-pendants": 0.22},
        "Film": {"lounge-decorative": 0.15, "*night": 0.1},
        "Night": _NIGHT,
    },
    "B-cinema": {"Day": _DAY, "Evening": _EVENING, "Film": {"cinema-accent": 0.15, "*night": 0.3}, "Night": _NIGHT},
    "GF-circulation": {"Day": _DAY, "Evening": _EVENING, "Night": _NIGHT},
    "GF-kids-a": {"Day": _DAY, "Evening": _EVENING, "Night": _NIGHT},
    "GF-kids-b": {"Day": _DAY, "Evening": _EVENING, "Night": _NIGHT},
    "GF-parents-bed": {"Day": _DAY, "Evening": _EVENING, "Night": _NIGHT,
                       "Reading": {"bed-reading": 1.0, "*decorative": 0.3}},
    "GF-parents-dressing": {"Day": _DAY, "Night": _NIGHT},
    "GF-parents-ensuite": {"Day": dict(_DAY, **{"*accent": 0.4}), "Night": _NIGHT},   # marble-wall washers at 40 % by day
    "GF-family-bath": {"Day": _DAY, "Night": _NIGHT},
    "B-guest-wc": {"Day": _DAY, "Night": _NIGHT},
    "B-dirty-kitchen": {"Day": _DAY},
    "B-pantry": {"Day": _DAY},
    "B-store": {"Day": _DAY},
}
