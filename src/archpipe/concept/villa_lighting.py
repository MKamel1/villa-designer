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
UNDER_SOFFIT = ("cinema", "store-ramp", "guest-wc", "dirty-kitchen")
MF = 0.8                       # maintenance factor (stated, lighting.DEFAULT_MAINTENANCE_FACTOR)

# kind -> the requirement (what a product must meet) and its generic stand-in
KINDS = {
    "DL":   dict(what="flush trimless downlight, wide", mount="recessed", lm=650, beam=55, cct=2700, cri=90,
                 layer="ambient", aperture=0.075),
    "DLN":  dict(what="flush trimless downlight, medium (task)", mount="recessed", lm=750, beam=36, cct=3000,
                 cri=90, layer="task", aperture=0.075),
    "ADJ":  dict(what="flush trimless adjustable accent", mount="recessed", lm=500, beam=24, cct=2700, cri=90,
                 layer="accent", aperture=0.075),
    "WW":   dict(what="flush trimless wall washer", mount="recessed", lm=650, beam=70, cct=2700, cri=90,
                 layer="accent", aperture=0.075),
    "PEN-GLOBE": dict(what="opal glass globe pendant D300", mount="pendant", lm=800, beam=None, cct=2700, cri=90,
                      layer="decorative", diameter=0.30),
    "PEN-SMALL": dict(what="opal glass globe pendant D200 (bedside)", mount="pendant", lm=350, beam=None, cct=2700,
                      cri=90, layer="decorative", diameter=0.20),
    "WALL-READ": dict(what="adjustable wall-mounted swing-arm reading light (ASSUMED product)", mount="wall",
                      lm=350, beam=None, cct=2700, cri=90, layer="decorative", diameter=0.12),
    "SWING": dict(what="movable wall reading light: wall plate, articulated 0.6 m reach and rotating head "
                  "(ASSUMED product; TODO swing-arm-product)", mount="wall", lm=350, beam=None,
                  cct=2700, cri=90, layer="task", diameter=0.12, reach=0.6),
    "PEN-LIN": dict(what="linear pendant 1.6 m, direct/indirect", mount="pendant", lm=1200, beam=90, cct=2700,
                    cri=90, layer="task", length=1.6),
    "SCONCE": dict(what="vanity wall light, opal, each side of the mirror", mount="wall", lm=450, beam=None,
                   cct=3000, cri=90, layer="task", diameter=0.12),
    "COVE": dict(what="LED strip in the cove, 2700 K", mount="strip", lm_per_m=900, cct=2700, cri=90,
                 layer="decorative"),
    "BACK": dict(what="LED strip inside glass-door book cabinet", mount="strip", lm_per_m=400, cct=2700, cri=90,
                 layer="accent"),
    "UC":   dict(what="under-cabinet LED strip", mount="strip", lm_per_m=1000, cct=3000, cri=90, layer="task"),
    "RAIL": dict(what="LED strip over the hanging rail (in-wardrobe)", mount="strip", lm_per_m=500, cct=3000, cri=90,
                 layer="task"),
    "TOE":  dict(what="toe-kick LED strip", mount="strip", lm_per_m=150, cct=2200, cri=90, layer="night"),
    "NL":   dict(what="night-light strip under the bed / plinth", mount="strip", lm_per_m=100, cct=2200, cri=90,
                 layer="night"),
    "DESK": dict(what="adjustable wall-arm desk lamp, shielded head, 3000 K", mount="task-lamp", lm=450, beam=70,
                 cct=3000, cri=90, layer="task"),
    "VSTRIP": dict(what="vertical LED strip at a hanging-section edge (shadow-free dressing light)", mount="strip",
                   lm_per_m=500, cct=3000, cri=90, layer="task"),
    "STORE-BATTEN": dict(what="ASSUMED opal LED storage batten, 0.70 m per shelving bay", mount="strip",
                          lm_per_m=900, cct=3000, cri=90, layer="task"),
    "MIRROR": dict(what="backlit mirror halo, 3000 K", mount="strip", lm_per_m=250, cct=3000, cri=90, layer="task"),
    "VSCONCE": dict(what="vertical opal sconce 0.5 m, each side of the mirror", mount="wall", lm=450, beam=None,
                    cct=3000, cri=90, layer="task", diameter=0.12),
    "STEP": dict(what="recessed step marker in the stair wall", mount="wall-marker", lm=60, beam=None, cct=2200,
                 cri=90, layer="night"),
    "PATH": dict(what="low recessed path marker (0.3 m AFF)", mount="wall-marker", lm=60, beam=None, cct=2200,
                 cri=90, layer="night"),
}

# kind -> the verified library product that meets it (lighting-library: imported, flux vs LORL and LDT vs the
# manufacturer's IES checked). Strips, pendants, sconces and markers stay GENERIC: iGuzzini Underscore ST49 failed
# its LDT/IES pair check (59.8 %), the Laser Evo wall washer LSEVO-AAKR2I failed it (100 %, asymmetric), and no
# decorative globe pendant with photometry was found. WW is served meanwhile by the soft flood placed 0.3 m off the
# wall (grazing), stated as a substitute.
PRODUCT_CHOICE = {
    "DL": ("iguzzini", "LSEVO-AAK3EW", "Laser Evo recessed D75 Soft, Flood 33 deg, 2700 K CRI97, phase-cut; "
                                       "flush (trimless) accessory"),
    "DLN": ("iguzzini", "LSEVO-AAIIA6", "Laser Evo recessed D75 Cone, Medium 29 deg, 2700 K CRI90, phase-cut; "
                                        "flush (trimless) accessory"),
    "ADJ": ("iguzzini", "LSEVO-AAHENX", "Laser Evo recessed D75 Cone Easy Adjustable, Spot 18 deg, 2700 K CRI97, "
                                        "phase-cut; flush (trimless) accessory"),
    "WW": ("iguzzini", "LSEVO-AAK3EW", "SUBSTITUTE for the wall washer LSEVO-AAKR2I (files failed the pair check): "
                                       "Laser Evo D75 Soft Flood 33 deg grazing from 0.3 m"),
}
PRODUCTS: dict[str, dict] = {}
_products_bound = False


def bind_products(ies_dir=None):
    """Export each chosen verified product's IES (from its LDT) and bind it to its kind; a product missing from the
    library leaves the kind generic (stated in every output)."""
    global _products_bound
    if _products_bound:
        return PRODUCTS
    from pathlib import Path
    from ..luminaires import library as LIB
    ies_dir = Path(ies_dir or Path(__file__).resolve().parents[3] / "out" / "villa" / "render-d1" / "ies")
    for kind, (mfr, sku, what) in PRODUCT_CHOICE.items():
        row = LIB.get(mfr, sku, 0)
        if not row or not row.get("verified"):
            continue
        path = LIB.export_ies(mfr, sku, 0, ies_dir / mfr / (sku + ".ies"))
        PRODUCTS[kind] = {"manufacturer": mfr, "code": sku, "ies": str(path), "lm": float(row["luminaire_lm"]),
                          "watts": row["watts"], "cct": row["cct_k"], "beam": row["beam_deg"], "what": what,
                          "substitute": what.startswith("SUBSTITUTE")}
    _products_bound = True
    return PRODUCTS


def products():
    """Return the cached verified bindings, creating them before any lighting consumer reads them."""
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
        dimmer = self.extra.get("dimmer", 1.0)
        product = products().get(self.kind)
        if product:                               # a real product emits its own flux (dimming is per scene)
            return product["lm"] * dimmer
        if self.lm is not None:
            return self.lm * dimmer
        k = self.spec
        return (k["lm_per_m"] * self.length if "lm_per_m" in k else k["lm"]) * dimmer

    @property
    def layer(self):
        return self.spec["layer"]


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

    def add(kind, room, x, y, z=None, why="", card="", level=None, **kw):
        level = level or lay["rooms"][room]["level"]
        if not (rc[room][0] - 1e-6 <= x <= rc[room][2] + 1e-6 and rc[room][1] - 1e-6 <= y <= rc[room][3] + 1e-6):
            for other in F._cluster(lay, room):          # an open-plan neighbour holds it: label it truthfully
                q = rc[other]
                if q[0] <= x <= q[2] and q[1] <= y <= q[3]:
                    room = other
                    break
        n[room] = n.get(room, 0) + 1
        z = z if z is not None else ceiling_z(level, x, room, y, lay, spec)
        out.append(Fixture("%s-%s-%02d" % (kind, room, n[room]), kind, room, level, round(x, 3), round(y, 3),
                           round(z, 3), why=why, card=card, **kw))

    def strip(kind, room, a, b, z, aim, why="", card="", level=None):
        """A straight LED strip from a to b (x, y) at height z, emitting along aim."""
        (xa, ya), (xb, yb) = a, b
        L = math.hypot(xb - xa, yb - ya)
        add(kind, room, (xa + xb) / 2, (ya + yb) / 2, z, why, card, level, aim=aim, length=round(L, 3),
            along=((xb - xa) / L, (yb - ya) / L, 0.0))

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
    for x, y in _grid((L[0], L[1], L[2], L[3]), 3, 2, mx=1.0, my=0.95):
        add("DL", "lounge", x, y, why="soft ambient, dimmable; 3 x 2 clear of the cove band",
            card="ies-res-family-room-100")
    cove("lounge", ("x0", "y0"), "cove along the street and stair sides: the ceiling floats over the family TV room")
    a = fp["lounge-armchair"]
    add("ADJ", "lounge", (a[0] + a[2]) / 2 - 0.4, (a[1] + a[3]) / 2, aim=(0.35, 0, -1),
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
    for x, y in _grid(Pn, 2, 1):
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
    for x, y in _grid(H, 1, 2):
        add("DL", "hall-b", x, y, why="stair foot and hall", card="ies-res-passage-30")
    E = rc["entry-b"]
    add("DL", "entry-b", (E[0] + E[2]) / 2, (E[1] + E[3]) / 2, why="entrance", card="ies-res-passage-30")
    add("WW", "entry-b", (E[0] + E[2]) / 2, E[1] + 0.35, aim=(0, -0.25, -1),
        why="washes the party wall at the entrance: a lit wall reads as welcome")
    Fm = rc["family"]
    for x, y in _grid(Fm, 1, 2):
        add("DL", "family", x, y, why="family corner ambient", card="ies-res-family-room-100")
    # kitchen: globe pendants over the island (centrepiece), task downlights over the run
    isl = fp["k-island"]
    top = LEVEL_Z["B"] + it["k-island"]["h"]
    cy = (isl[1] + isl[3]) / 2
    for k in range(3):
        x = isl[0] + (k + 0.5) * (isl[2] - isl[0]) / 3
        add("PEN-GLOBE", "kitchen", x, cy, z=top + 0.762 + 0.15, why="three opal globes over the island, bottom 762 mm "
            "above the worktop", card="rid-pendant-above-table-762", extra={"hang_from": ceiling_z("B")})
    globe_x = [isl[0] + (k + 0.5) * (isl[2] - isl[0]) / 3 for k in range(3)]
    for x in (isl[0] + 0.05, (globe_x[0] + globe_x[1]) / 2,
              (globe_x[1] + globe_x[2]) / 2, isl[2] - 0.05):
        add("DLN", "kitchen", x, cy, why="prep cone between opal globes, clear of their diffusing bodies",
            card="ies-res-kitchen-prep-500")
    run = fp["k-run"]
    for x in (run[0] + 0.25, (run[0] + run[2]) / 2, run[2] - 0.25):
        add("DLN", "kitchen", x, run[3] - 0.65, why="650 mm from the wall face, over the counter's front edge, 1.0 m "
            "pitch (advisory K-SPOT-OFF / K-SPOT-PITCH)", card="ies-res-kitchen-sink-300")
    add("DL", "kitchen", (rc["kitchen"][0] + isl[0]) / 2 + 0.2, cy + 0.9, why="kitchen general",
        card="ies-res-kitchen-general-50")
    KI = rc["kitchen-island"]
    for x in (KI[0] + 0.7, KI[2] - 0.7):
        add("DL", "kitchen-island", x, (KI[1] + isl[1]) / 2, why="aisle behind the island stools",
            card="ies-res-kitchen-general-50")
    strip("TOE", "kitchen", (isl[0] + 0.05, isl[3] - 0.05), (isl[2] - 0.05, isl[3] - 0.05), LEVEL_Z["B"] + 0.05,
          (0, 0.3, -1), why="island plinth glow: night light and the island floats")
    # dining: linear pendant over the table (task + decorative), two adjustable fills crossing, sideboard accent
    tb = fp["dining-table"]
    add("PEN-LIN", "dining", (tb[0] + tb[2]) / 2, (tb[1] + tb[3]) / 2,
        z=LEVEL_Z["B"] + it["dining-table"]["h"] + 0.762, extra={"hang_from": ceiling_z("B")},
        why="linear pendant along the table, 762 mm above it", card="rid-pendant-above-table-762")
    tcx, tcy = (tb[0] + tb[2]) / 2, (tb[1] + tb[3]) / 2
    for x, y in ((tb[0] + 0.2, tb[1] - 0.75), (tb[2] - 0.2, tb[3] + 0.75)):   # opposite diagonal corners
        add("ADJ", "dining", x, y, aim=(tcx - x, tcy - y, -1.95),
            why="adjustable fill crossing the table from opposite corners, not straight down (p. 95)",
            card="ies-res-dining-informal-100")
    sb = fp["dining-sideboard"]
    for x in (sb[0] + 0.45, sb[2] - 0.45):
        add("ADJ", "dining-side", x, sb[3] + 0.9, aim=(0, -0.55, -1), why="accent on the sideboard and the art "
            "above it, ~30 deg", card="ldb-accent-aim-30")
    # garden living: cove, lit glass cabinets, reading in the daybed nook, soft downlights
    Lv = rc["living"]
    cove("living", ("x0", "y0"), "cove on the dining and library sides: the garden living glows at night")
    for x, y in _grid((Lv[0] + 0.3, Lv[1] + 0.3, Lv[2], Lv[3]), 2, 2, mx=0.9, my=0.9):
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
            why="ASSUMED side-panel plate 0.55 m above mattress; articulated arm swings over mattress",
            card="ies-res-chair-reading-200", extra={"wall_plate": (face_x, y), "mount_side": side,
                                                       "reach": 0.6, "swept_x": (min(face_x, face_x + direction * 0.6),
                                                                                  max(face_x, face_x + direction * 0.6)),
                                                       "swept_y": (y, y + math.sqrt(0.30**2 - (0.59 / 2)**2))})
    for x in (nook[0] + 0.47, nook[2] - 0.47):
        add("DLN", "bar-alcove", x, nook[1] + 0.11,
            z=LEVEL_Z["B"] + it["library-daybed"]["nook_top"] - 0.025,
            why="recessed in the 2.1 m nook top; task fill", card="ies-res-chair-reading-200",
            extra={"dimmer": 0.4})
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
        add("DESK", "cinema", x, desk[1] + 0.28, z=LEVEL_Z["B"] + VL_DESK_Z,
            why="two shielded task lamps at the cinema desk, switched off for films", card="ies-res-desk-400")
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
    for x in (dk[0] + 0.5, dk[0] + 1.5, dk[0] + 2.5, dk[2] - 0.4):
        add("DLN", "dirty-kitchen", x, dk[1] - 0.1, why="over the heavy-cooking run (1000 lm package)",
            card="ies-res-kitchen-prep-500", lm=1000)
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
    add("DL", "landing-gf", (Lg[0] + Lg[2]) / 2, (Lg[1] + Lg[3]) / 2, why="stair top", card="ies-res-stairs-50")
    Co = rc["corridor"]
    xs = [Co[0] + 0.9 + i * 1.75 for i in range(int((Co[2] - Co[0] - 1.0) / 1.75) + 1)]
    for x in xs:
        add("WW", "corridor", x, Co[1] + 0.30, aim=(0, -0.25, -1), why="grazing the long party wall: the corridor "
            "is lit by its wall, not by a row of spots", card="ies-res-passage-30")
    for x in xs[::2]:
        add("PATH", "corridor", x + 0.4, Co[1] + 0.02, z=0.30, aim=(0, 1, -0.4), level="GF",
            why="low path light to the bathrooms at night")
    Ge = rc["gallery-end"]
    add("DL", "gallery-end", (Ge[0] + Ge[2]) / 2, (Ge[1] + Ge[3]) / 2, why="gallery end", card="ies-res-passage-30")
    S = rc["study-game"]
    for x, y in _grid(S, 2, 2, mx=1.2, my=0.8):
        add("DL", "study-game", x, y, why="study ambient", card="ies-res-game-digital-6")
    d1 = fp["study-desk"]
    for y in (d1[1] + 0.45, d1[3] - 0.45):
        add("DLN", "study-game", d1[2] - 0.05, y, why="desk light over the shared homework desk's front edge "
            "(no shadow of the head)", card="ies-res-desk-400")
    d2 = fp["study-adult-desk"]
    add("DLN", "study-game", (d2[0] + d2[2]) / 2, d2[1] - 0.05, why="desk light over the adult desk",
        card="ies-res-desk-400")
    FB = rc["family-bath"]
    add("DL", "family-bath", (FB[0] + FB[2]) / 2 + 0.2, (FB[1] + FB[3]) / 2 - 0.3, why="bath ambient",
        card="ies-res-shower-50")
    sh = fp["fb-shower"]
    add("DLN", "family-bath", (sh[0] + sh[2]) / 2, (sh[1] + sh[3]) / 2, why="shower (wet-rated)",
        card="ies-res-shower-50")
    _sconces(add, "family-bath", fp["fb-basin"], lay, rc)
    bb = fp["fb-basin"]
    strip("TOE", "family-bath", (bb[2] + 0.02, bb[1] + 0.03), (bb[2] + 0.02, bb[3] - 0.03), 0.30, (0.3, 0, -1),
          level="GF", why="glow under the basin: night light")
    for room, desks, bed in (("kids-a", ("ka-desk-1", "ka-desk-2"), "ka-bunk"), ("kids-b", ("kb-desk",), "kb-bed")):
        K = rc[room]
        for x, y in _grid(K, 2, 1, mx=0.9):
            add("DL", room, x, (K[1] + K[3]) / 2 - 0.3, why="bedroom ambient", card="ies-res-bedroom-general-50")
        for d in desks:
            q = fp[d]
            add("DESK", room, (q[0] + q[2]) / 2, (q[1] + q[3]) / 2 + 0.05, z=VL_DESK_Z, level="GF",
                why="each child's own adjustable, shielded desk lamp (advisory KID-DESK): its light stays on the desk, "
                    "out of the sleep zone", card="ies-res-desk-400")
        q = fp[bed]
        strip("NL", room, (q[0] + 0.05, q[1] - 0.02), (q[2] - 0.05, q[1] - 0.02), 0.08, (0, -0.3, -1), level="GF",
              why="warm glow under the bed side: kids' night light")
    # parents' bedroom: headboard cove, swing-arm bedside lights, reading spots, vanity accent, soft ambient
    PB = rc["parents-bed"]
    b = fp["pb-bed"]
    strip("COVE", "parents-bed", (b[0] - 0.25, PB[1] + 0.12), (b[2] + 0.25, PB[1] + 0.12), CEILING + 0.03,
          (0, 0.4, 1), why="headboard cove: warm light grazing the bed wall (taste: 2700 K cove at the headboard)")
    for x in (b[0] + 0.18, b[2] - 0.18):
        add("WALL-READ", "parents-bed", x, PB[1] + 0.13, z=1.45, aim=(0, 0.45, -0.35),
            why="wall-mounted swing arm on the solid head wall, aimed at the pillow; clear of both passages")
    for x in (b[0] + 0.4, b[2] - 0.4):
        add("ADJ", "parents-bed", x, b[1] + 0.35, why="reading spot straight over the reading position (the tilted "
            "first aim landed 0.6 m down the bed: measured 135-142 lx in the scene)",
            card="ies-res-bed-reading-200")
    for x, y in ((PB[0] + 0.55, (PB[1] + PB[3]) / 2), ((b[0] + b[2]) / 2, b[3] + 0.45)):
        add("DL", "parents-bed", x, y, why="ambient, dimmable", card="ies-res-bedroom-general-50")
    v = fp["pb-vanity"]
    add("ADJ", "parents-bed", v[0] - 0.35, (v[1] + v[3]) / 2, aim=(0.35, 0, -1), why="vanity light",
        card="ies-res-vanity-grooming-300")
    PE = rc["parents-entry"]
    add("DL", "parents-entry", (PE[0] + PE[2]) / 2, (PE[1] + PE[3]) / 2, why="entry lobby", card="ies-res-passage-30")
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
    # ASSUMED initial driver setting; final dimmer scene is measured in the render.
    for fixture in out:
        if fixture.room == "parents-ensuite":
            fill_defaults(fixture.extra, {"dimmer": 0.4})
    pb_ = fp["pe-basin"]
    strip("TOE", "parents-ensuite", (pb_[2] + 0.02, pb_[1] + 0.03), (pb_[2] + 0.02, pb_[3] - 0.03), 0.30,
          (0.3, 0, -1), level="GF", why="glow under the vanity: night light")
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


def _sconces(add, room, basin, lay, rc, vertical=False):
    """Two sconces either side of the mirror over a basin on a wall, 0.95 m apart at 1.60 m AFF (card
    rid-vanity-sconces-914: 914-1016 mm apart, eye level)."""
    x0, y0, x1, y1 = basin
    r = rc[room]
    lv = lay["rooms"][room]["level"]
    z = LEVEL_Z[lv] + 1.60
    # Eh on the counter needs light from above: a task downlight 0.3 m in front of the mirror wall (the sconces
    # give the face its vertical light, Ev)
    if abs(x0 - r[0]) < 0.05 or abs(x1 - r[2]) < 0.05:
        dx = r[0] + 0.35 if abs(x0 - r[0]) < 0.05 else r[2] - 0.35
        add("DLN", room, dx, (y0 + y1) / 2, why="basin counter light, in front of the mirror",
            card="ies-res-vanity-grooming-300", level=lv, lm=900)
    else:
        dy = r[1] + 0.35 if abs(y0 - r[1]) < 0.05 else r[3] - 0.35
        add("DLN", room, (x0 + x1) / 2, dy, why="basin counter light, in front of the mirror",
            card="ies-res-vanity-grooming-300", level=lv, lm=900)
    if abs(x0 - r[0]) < 0.05 or abs(x1 - r[2]) < 0.05:           # basin against an x wall: mirror on that wall
        wx = r[0] + 0.06 if abs(x0 - r[0]) < 0.05 else r[2] - 0.06
        cy = (y0 + y1) / 2
        for s in (-1, 1):
            add("VSCONCE" if vertical else "SCONCE", room, wx, cy + s * 0.475, z=z,
                aim=(1 if wx < (r[0] + r[2]) / 2 else -1, 0, 0),
                why="grooming light each side of the mirror", card="rid-vanity-sconces-914", level=lv)
        if vertical:                                  # backlit mirror halo (advisory B-VANITY)
            add("MIRROR", room, wx + (0.01 if wx < (r[0] + r[2]) / 2 else -0.01), cy, z=z, level=lv, length=0.7,
                along=(0.0, 1.0, 0.0), aim=(1 if wx < (r[0] + r[2]) / 2 else -1, 0, 0),
                why="backlit mirror: soft light behind the glass (advisory B-VANITY)")
    else:
        wy = r[1] + 0.06 if abs(y0 - r[1]) < 0.05 else r[3] - 0.06
        cx = (x0 + x1) / 2
        for s in (-1, 1):
            add("SCONCE", room, cx + s * 0.475, wy, z=z, aim=(0, 1 if wy < (r[1] + r[3]) / 2 else -1, 0),
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
    from .. import photometry as ph
    k = KINDS[kind]
    product = products().get(kind)
    if product:
        return ph.load(product["ies"]), False
    lm = k.get("lm") or k.get("lm_per_m", 100)
    beam = k.get("beam", 120) if k["mount"] != "strip" else 120
    return ph.parse(generic_ies(lm, beam), name=kind), True


# ------------------------------------------------------------------ the check
def task_points(lay=None):
    """(room, card, x, y, plane z absolute, label): the carded task planes of D1."""
    lay = lay or R.design("D1")
    it = {i["id"]: i for i in F.layout(lay)}
    fp = {k: F.footprint(v) for k, v in it.items()}
    B, G = LEVEL_Z["B"], LEVEL_Z["GF"]
    pts = []

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
        pts.append(("kitchen", "ies-res-kitchen-prep-500", x, isl[3] - 0.3, B + 0.92, "island prep side"))
        pts.append(("kitchen", "ies-res-breakfast-200", x, isl[1] + 0.2, B + 0.92, "island seating side"))
    burner = next((a, b) for kind, a, b in F.module_spans(it["k-island"]) if kind == "single-induction")
    pts.append(("kitchen", "ies-res-kitchen-cooktop-300", (burner[0] + burner[1]) / 2,
                (isl[1] + isl[3]) / 2, B + 0.926, "single induction zone"))
    run = fp["k-run"]
    pts.append(("kitchen", "ies-res-kitchen-sink-300", (run[0] + run[2]) / 2, run[1] + 0.25, B + 0.9, "sink"))
    pts.append(("dining", "ies-res-dining-informal-100", *c("dining-table"), B + 0.75, "dining table centre"))
    dt = fp["dining-table"]
    pts.append(("dining", "ies-res-dining-study-200", dt[0] + 0.3, (dt[1] + dt[3]) / 2, B + 0.75, "table end (homework)"))
    dk = fp["dk-run"]
    pts.append(("dirty-kitchen", "ies-res-kitchen-prep-500", dk[0] + 1.5, dk[1] + 0.3, B + 0.9, "dirty kitchen run"))
    for d, lv in (("study-desk", G), ("study-adult-desk", G), ("ka-desk-1", G), ("ka-desk-2", G), ("kb-desk", G)):
        pts.append((it[d]["room"], "ies-res-desk-400", *c(d), lv + 0.75, d))
    b = fp["pb-bed"]
    for x in (b[0] + 0.4, b[2] - 0.4):
        pts.append(("parents-bed", "ies-res-bed-reading-200", x, b[1] + 0.35, G + 0.9, "pillow"))
    for basin, room in (("fb-basin", "family-bath"), ("pe-basin", "parents-ensuite"), ("gwc-basin", "guest-wc")):
        lv = B if room == "guest-wc" else G
        pts.append((room, "ies-res-vanity-grooming-300", *c(basin), lv + 0.91, basin))
    a = fp["lounge-armchair"]
    pts.append(("lounge", "ies-res-chair-reading-200", *c("lounge-armchair"), B + 0.76, "armchair"))
    pts.append(("bar-alcove", "ies-res-chair-reading-200", *c("library-daybed"), B + 0.76, "daybed nook"))
    desk = fp["cinema-desk"]
    for x in (desk[0] + 0.31, desk[2] - 0.31):
        pts.append(("cinema", "ies-res-desk-400", x, (desk[1] + desk[3]) / 2, B + 0.75, "cinema desk"))
    return pts


ROOM_TARGETS = {   # room -> general card (floor average, direct only: advisory)
    "lounge": "ies-res-family-room-100", "family": "ies-res-family-room-100", "living": "ies-res-living-30",
    "kitchen": "ies-res-kitchen-general-50", "kitchen-island": "ies-res-kitchen-general-50",
    "hall-b": "ies-res-passage-30", "corridor": "ies-res-passage-30", "study-game": "ies-res-game-digital-6",
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
    """Point emitters of a fixture: one for a point source, one per 0.25 m for a strip."""
    if f.length and f.length > 0:
        nseg = max(1, int(round(f.length / 0.25)))
        out = []
        for k in range(nseg):
            t = (k + 0.5) / nseg - 0.5
            out.append((f.x + f.along[0] * t * f.length, f.y + f.along[1] * t * f.length,
                        f.z + f.along[2] * t * f.length, f.lumens / nseg))
        return out
    return [(f.x, f.y, f.z, f.lumens)]
