"""L6c: the luminaire schedule for the supplier and the performance spec a substitute must meet.

One row per TYPE TAG (a design kind, split by rated lumens when one kind has several sizes). Quantities, rooms and rated lumens come
from the design (`concept.villa_lighting.design()`); the reference product and the performance spec come from `TYPE_SPEC` below.

Evidence rules (CLAUDE.md): a figure printed on a manufacturer datasheet is quoted as such; a figure that is OUR requirement is marked
`policy`; a product we have no manufacturer file for is `ref: none` and is specified by performance only. Nothing here is a code clause.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# ---- requirement values we state ourselves (policy: the client chose best practice over a code, 2026-11)
CCT_TOL_K = 100            # 2700 K +/- 100 K nominal; colour tolerance <= 3 SDCM (ERCO prints 1.5 SDCM)
CRI_MIN = 90               # brief: CRI >= 90 on every interior luminaire
R9_MIN = 50                # policy: R9 >= 50 where the maker states it
HEADROOM = 0.80            # V12: a zone's driver must be <= 80 % of maximum output with the product that is installed
LM_BAND = 0.15             # a substitute's rated lumens within +/-15 % of the reference, else the substitution check decides
BEAM_TOL = 0.15            # beam angle within +/-15 % of the reference (a narrow spot: +/-2 deg minimum)
FLICKER = "TLA SVM <= 0.4 and Pst LM <= 1 (the values printed on the ERCO datasheets); state yours"
DIM_DALI = "DALI-2, 1-100 % constant-current reduction (CCR); no phase-cut"

# type -> reference product + performance spec. `ref` None = no verified product (performance spec only).
# keys: name, role, mount, ref(list), beam, cct, ugr, ip, ik, dimming, size, finish, note
_ERCO_DL = dict(
    ref=[dict(maker="ERCO", code="41321.000", url="https://www.erco.com/41321.000", v10="pass",
              name="Quintessence downlight, wide flood, 12.1 W, 1065 lm, 2700 K, CRI 92, DALI-2")],
    beam=(57, "wide flood, 56-57 deg (50 % angle)"), cct=2700, ugr="cut-off angle 40 deg or better (datasheet); no glare source above 3000 cd/m2 in view",
    ip="IP20", ik="-", dimming=DIM_DALI,
    size="recessed, trim/mounting ring 76 mm diameter (photometric file); ceiling thickness 1-25 mm; cut-out per the maker's drawing - supplier to state",
    finish="white RAL 9002 mounting ring, black reflector surround not visible",
    note="trimless/flush accessory preferred; recess depth <= 500 mm housing allowance (ERCO: cast aluminium housing)")

TYPE_SPEC = {
    "DL": dict(name="Recessed downlight, wide flood", role="Ambient and task (desk, basin, kitchen run) downlight", mount="recessed ceiling", **_ERCO_DL),
    "DLN": dict(name="Recessed downlight, extra wide flood", role="not used in D1", mount="recessed ceiling",
                ref=[dict(maker="ERCO", code="41369.000", url="https://www.erco.com/41369.000", v10="pass",
                          name="Quintessence downlight, extra wide flood, 904 lm, 2700 K, CRI 92, DALI-2")],
                beam=(91, "extra wide flood, 89-91 deg"), cct=2700, ugr="cut-off 40 deg", ip="IP20", ik="-", dimming=DIM_DALI,
                size="as DL", finish="white RAL 9002", note="kept for the library; no D1 fitting uses it"),
    "ADJ": dict(name="Adjustable narrow-spot accent", role="Armchair reading, sideboard and art accent", mount="track or recessed adjustable, ceiling",
                ref=[dict(maker="ERCO", code="A9000028", url="https://www.erco.com/A9000028", v10="partial",
                          name="Optec New spotlight M, narrow spot, 4.2 W, 304 lm, 2700 K, CRI 92, track, on-board dim")],
                beam=(6, "narrow spot; maker publishes 4.7 deg, its photometric file gives 5.7 deg (V10 partial)"), cct=2700,
                ugr="spot is aimed, not in the field of view; tilt >= 30 deg", ip="IP20", ik="-",
                dimming="on-board dim or DALI-2, 1-100 %", size="track adapter (3-circuit) or recessed adjustable, head <= 80 mm",
                finish="black RAL 9011 or white to match ceiling", note="a spot in the 4-8 deg class; a 15-20 deg spot is NOT equivalent here"),
    "WW": dict(name="Recessed wall washer, lens", role="Wall wash: entry, corridor, cinema rear wall, ensuite marble", mount="recessed ceiling",
               ref=[dict(maker="ERCO", code="41374.000", url="https://www.erco.com/41374.000", v10="pass",
                         name="Quintessence lens wallwasher, 8.1 W, 399 lm, 2700 K, CRI 92, DALI-2")],
               beam=(None, "asymmetric wall-wash distribution; compare the IES/LDT, not a beam angle"), cct=2700,
               ugr="cut-off 80 deg (datasheet)", ip="IP20", ik="-", dimming=DIM_DALI,
               size="recessed, size-3 ring, 76 mm trim; ceiling thickness 1-25 mm", finish="white RAL 9002",
               note="wall-wash mean illuminance table on the datasheet (3 m wall, 0.9-1.2 m offset) must be matched +/-10 %"),
    "PEN-LIN": dict(name="Linear pendant over the dining table, direct", role="Dining table task and decorative light", mount="suspended, wire, 762 mm over the table",
                    ref=[dict(maker="ERCO", code="50674.000", url="https://www.erco.com/50674.000", v10="pass",
                              name="Jilly pendant downlight 1500 mm, 27 W, 3558 lm (2 x 1779), 2700 K, CRI 92, DALI-2, UGR 19")],
                    beam=(87, "wide direct distribution, beam 86-89 deg"), cct=2700, ugr="UGR <= 19 (datasheet UGR 19)", ip="IP20", ik="-",
                    dimming=DIM_DALI, size="length 1500 mm, width 41 mm, height 121 mm; two wire suspensions, drop 2500 mm adjustable",
                    finish="white RAL 9002", note="OVERSIZED for the table: the design runs it at about 15 % (Dinner about 7 %); a 1.5 m pendant of "
                    "700-1500 lm with the same 1 % DALI floor is preferred"),
    "DESK": dict(name="Adjustable desk task lamp, shielded", role="Desk lamps: cinema desk, children's desks", mount="desk or wall arm, 450 mm over the desktop",
                 ref=[dict(maker="ERCO", code="31327.000", url="https://www.erco.com/31327.000", v10="pass",
                           name="Lucy task light, wide beam, 9.4 W, 234 lm, 2700 K, CRI 92, on-board dim")],
                 beam=(None, "wide beam, shielded head; compare the IES/LDT"), cct=2700, ugr="shielded head, no direct view of the LED from a seated eye",
                 ip="IP20", ik="-", dimming="on-board push dimmer, 1-100 %", size="desk fixing 10-40 mm bush or clamp", finish="black RAL 9011",
                 note="the lamp must put its light on the desk and not in the sleep zone"),
    "PEN-GLOBE": dict(name="Opal glass globe pendant", role="Kitchen island pendants (D300) and stair-void cluster (D300)", mount="suspended",
                      ref=[], beam=(None, "diffuse, opal glass, near-Lambertian"), cct=2700, ugr="opal diffuser, surface luminance <= 3000 cd/m2 at full output",
                      ip="IP20", ik="-", dimming=DIM_DALI + " or 0-10 V into a DALI gateway", size="globe diameter 300 mm, drop to suit: island 762 mm over the worktop to the globe bottom",
                      finish="opal white glass, brass or black canopy", note="decorative: lumens-only, absorbed by V12 headroom"),
    "COVE": dict(name="LED strip, cove", role="Perimeter cove, lounge/living/headboard", mount="surface in the cove", ref=[dict(maker="iGuzzini", code="ST49", url="https://www.iguzzini.com/en/st49/", v10="lumens-only",
                 name="Underscore15 ledstrip hi performance, 680 lm/m, 5 W/m, 2700 K")], beam=(120, "wide, indirect onto the ceiling"), cct=2700,
                 ugr="not visible (indirect)", ip="IP20 (IP65 if the cove can be wet-cleaned)", ik="-", dimming=DIM_DALI + " via a constant-voltage/current driver",
                 size="strip width <= 12 mm; continuous, no dark gaps", finish="-", note="decorative: lumens-only; CRI >= 90 and 2700 K on the strip itself"),
    "BACK": dict(name="LED strip, cabinet", role="Inside glass book cabinets and under-stair bays", mount="surface, in the cabinet", ref=[dict(maker="iGuzzini", code="ST49",
                 url="https://www.iguzzini.com/en/st49/", v10="lumens-only", name="Underscore15 ledstrip hi performance, 680 lm/m, 2700 K")],
                 beam=(120, "wide"), cct=2700, ugr="shielded from the eye", ip="IP20", ik="-", dimming=DIM_DALI + " zone", size="strip width <= 12 mm",
                 finish="-", note="decorative accent: lumens-only"),
    "TOE": dict(name="LED strip, toe-kick / basin glow (night)", role="Night orientation light", mount="surface, under island / basin", ref=[dict(maker="iGuzzini", code="ST49",
                url="https://www.iguzzini.com/en/st49/", v10="lumens-only", name="Underscore15 ledstrip, 680 lm/m")], beam=(120, "wide, downward"), cct=2200,
                ugr="not visible", ip="IP20 (bathrooms IP44)", ik="-", dimming=DIM_DALI + "; dim to 10 % in the Night scene", size="strip width <= 12 mm",
                finish="-", note="2200 K night colour (design policy); lumens-only"),
    "NL": dict(name="LED strip, night light", role="Night glow under beds, island plinth and cinema floor", mount="surface, low", ref=[dict(maker="iGuzzini", code="ST49",
               url="https://www.iguzzini.com/en/st49/", v10="lumens-only", name="Underscore15 ledstrip, 680 lm/m")], beam=(120, "wide, downward"), cct=2200,
               ugr="not visible", ip="IP20", ik="-", dimming=DIM_DALI, size="strip width <= 12 mm", finish="-", note="2200 K night colour; lumens-only"),
    "UC": dict(name="LED strip, under cabinet", role="Kitchen under-cabinet task", mount="surface, under wall cabinet", ref=[], beam=(120, "wide, forward"), cct=2700,
               ugr="shielded by a cabinet rail", ip="IP20", ik="-", dimming=DIM_DALI, size="strip width <= 12 mm", finish="aluminium profile with opal diffuser",
               note="not used in the current D1 design (no wall cabinets); listed for the kitchen drawing round"),
    "RAIL": dict(name="LED strip, wardrobe rail", role="Light over the hanging rail", mount="surface, in the wardrobe", ref=[], beam=(120, "wide, downward"), cct=2700,
                 ugr="shielded from the eye", ip="IP20", ik="-", dimming=DIM_DALI, size="strip width <= 12 mm, profile <= 20 mm", finish="aluminium profile, opal",
                 note="task: lumens-only, CRI >= 90 and R9 >= 50 matter for clothes"),
    "VSTRIP": dict(name="LED strip, vertical dressing light", role="Shadow-free light at the hanging-section edges", mount="surface, vertical", ref=[], beam=(120, "wide, forward"),
                   cct=2700, ugr="opal, not visible from the aisle", ip="IP20", ik="-", dimming=DIM_DALI, size="strip width <= 12 mm, length 1800 mm",
                   finish="aluminium profile, opal", note="task: lumens-only; client withdrew the earlier 4000 K"),
    "STORE-BATTEN": dict(name="Opal LED batten, storage", role="Store room shelving bays", mount="surface, under soffit", ref=[], beam=(120, "wide, downward"), cct=2700,
                         ugr="opal diffuser", ip="IP20 (store may be damp: IP44 preferred)", ik="IK07 preferred", dimming=DIM_DALI + " or switched",
                         size="length 700 mm, width <= 50 mm", finish="white", note="task: lumens-only"),
    "MIRROR": dict(name="Backlit mirror halo", role="Ensuite mirror", mount="in the mirror", ref=[], beam=(120, "wide, to the wall"), cct=2700, ugr="diffused", ip="IP44",
                   ik="-", dimming=DIM_DALI, size="to the mirror supplier's drawing", finish="-", note="supplied with the mirror; lumens-only"),
    "VANITY-LIN": dict(name="Linear LED bar over mirror", role="Guest WC and ensuite vanity light (client decision 2026-10-08)", mount="wall, above the mirror, 100 mm above its top",
                       ref=[], beam=(None, "wide forward, opal"), cct=2700, ugr="opal diffuser", ip="IP44", ik="-", dimming=DIM_DALI, size="length 500 mm, width/height 40 mm",
                       finish="brushed metal or white", note="vanity task: lumens-only; CRI >= 90 with R9 >= 50 (skin tones)"),
    "SCONCE": dict(name="Vanity wall light, opal", role="Family bath mirror, one each side", mount="wall, 1600 mm AFF, 950 mm apart", ref=[], beam=(None, "diffuse, opal"),
                   cct=2700, ugr="opal, luminance <= 3000 cd/m2", ip="IP44", ik="-", dimming=DIM_DALI, size="diameter 120 mm, projection 60 mm", finish="chrome, brass or black",
                   note="vanity: lumens-only"),
    "VSCONCE": dict(name="Vertical opal sconce, 0.5 m", role="Ensuite mirror, each side", mount="wall", ref=[], beam=(None, "diffuse"), cct=2700,
                    ugr="opal", ip="IP44", ik="-", dimming=DIM_DALI, size="height 500 mm", finish="to match the mirror", note="not used in the current D1 design (over-mirror bar chosen)"),
    "WALL-READ": dict(name="Wall reading light, swing arm", role="Parents' bedside reading", mount="wall, 1450 mm AFF, either side of the bed", ref=[],
                      beam=(60, "adjustable, aimed at the pillow"), cct=2700, ugr="shielded head", ip="IP20", ik="-", dimming=DIM_DALI + " or inline dimmer",
                      size="plate <= 80 mm, reach 300 mm", finish="to match the joinery", note="decorative/accent: lumens-only"),
    "SWING": dict(name="Swing-arm reading lamp", role="Daybed reading, either side of the nook", mount="wall plate 550 mm over the mattress", ref=[],
                  beam=(60, "adjustable"), cct=2700, ugr="shielded head", ip="IP20", ik="-", dimming=DIM_DALI + " or inline dimmer", size="arm reach 600 mm, articulated",
                  finish="to match the joinery", note="task: lumens-only; must reach over the mattress"),
    "STEP": dict(name="Step marker light (night / escape route)", role="Stair wall, night route (battery-backed)", mount="recessed in the stair wall, 250 mm over the tread", ref=[],
                 beam=(None, "asymmetric, down the tread"), cct=2200, ugr="shielded", ip="IP44", ik="IK07", dimming="switched at 100 %, dimmed to 10 % in Night",
                 size="100 x 40 mm face", finish="white or stainless", note="emergency layer: battery-backed, lumens-only"),
    "PATH": dict(name="Low path marker light", role="Corridor and landing night route", mount="recessed in the wall, 300 mm AFF", ref=[], beam=(None, "asymmetric, floor wash"),
                 cct=2200, ugr="shielded", ip="IP44", ik="IK07", dimming="switched or DALI, dimmed to 10 % in Night", size="100 x 40 mm face", finish="white or stainless",
                 note="lumens-only"),
}

_STRIPS = ("COVE", "BACK", "UC", "RAIL", "TOE", "NL", "VSTRIP", "MIRROR")


def _rated_lm(f, kinds):
    """Full-output lumens of ONE fitting as the supplier specifies it (a product: its catalogue lumens; a generic: sized)."""
    k = kinds[f.kind]
    if f.record.product:
        return float(dict(f.record.product)["lm"])
    if "rated_lm" in f.extra:
        return float(f.extra["rated_lm"])
    if f.lm is not None:
        return float(f.lm)
    return float(k["lm_per_m"] * f.length) if "lm_per_m" in k else float(k["lm"])


def build_schedule(fixtures=None, drivers=None) -> list[dict]:
    """Rows keyed by type tag from the design and the commissioning drivers."""
    from ..concept import villa_lighting as VL
    fixtures = fixtures if fixtures is not None else VL.design()
    drivers = drivers if drivers is not None else json.loads((ROOT / "knowledge/lighting/zone-drivers.json").read_text(encoding="utf-8"))
    groups = defaultdict(list)
    for f in fixtures:
        r = _rated_lm(f, VL.KINDS)
        # one tag per kind; a kind with several rated sizes (generic fittings) is split A, B ... by size (strips: by lm/m)
        key = (f.kind, round(r / f.length if f.kind in _STRIPS and f.length else r, -1 if r > 300 else 0))
        groups[key].append((f, r))
    by_kind = defaultdict(list)
    for (kind, size), fs in groups.items():
        by_kind[kind].append((size, fs))
    rows = []
    for kind, subs in by_kind.items():
        subs.sort(key=lambda t: -t[0])
        if kind in _STRIPS or kind in ("PEN-GLOBE", "WALL-READ", "SWING", "RAIL"):
            subs = [(subs[0][0], [x for _s, fs in subs for x in fs])] if len(subs) > 1 and kind in _STRIPS else subs
        for i, (size, fs) in enumerate(subs):
            tag = kind if len(subs) == 1 else "%s-%s" % (kind, "ABCDEFGH"[i])
            spec = TYPE_SPEC[kind]
            rated = sorted({round(r, 0) for _f, r in fs})
            rooms = defaultdict(int)
            for f, _r in fs:
                rooms[f.room] += 1
            ds = [drivers.get(VL.zone_id(f)) for f, _r in fs if drivers.get(VL.zone_id(f)) is not None]
            length = round(sum(f.length for f, _r in fs), 1) if kind in _STRIPS else None
            rows.append(dict(tag=tag, kind=kind, qty=len(fs), length_m=length, rooms=dict(sorted(rooms.items())), rated_lm=rated,
                             lm_per_m=(round(sum(r for _f, r in fs) / length) if length else None),
                             layer=sorted({VL.zone_layer(f) for f, _r in fs}), driver_min=min(ds) if ds else None,
                             driver_max=max(ds) if ds else None, zones=sorted({VL.zone_id(f) for f, _r in fs}), spec=spec))
    order = {k: i for i, k in enumerate(TYPE_SPEC)}
    rows.sort(key=lambda r: (order[r["kind"]], r["tag"]))
    return rows


def spec_for_tag(tag: str) -> dict:
    """The performance spec of a type tag ('DL', 'PEN-GLOBE-A' ...)."""
    kind = tag if tag in TYPE_SPEC else tag.rsplit("-", 1)[0]
    if kind not in TYPE_SPEC:
        raise KeyError("unknown type tag %r (known kinds: %s)" % (tag, ", ".join(TYPE_SPEC)))
    return TYPE_SPEC[kind]
