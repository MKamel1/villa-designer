"""The villa options as daylight scenes (archpipe.daylight), from the same Revit spec the option models were built
from (concept/revit_spec.py) and the environment model (villa_env: fences, neighbours, sister villa, apartment
above, core, columns, beams, slabs, the kept NE yard wall).

Stated for this study (daylight notes, carried into the report):
  * no car parked on the deck; no furniture; internal doors closed, open-plan joins open, garden and deck doors
    glazed; guard rails drawn solid (a glass balustrade would let more light by);
  * the ground outside our plot is a plane at street level (the neighbours' own sunken yards are not modelled);
  * reflectances and glazing as daylight.MATERIALS; frames and dirt not modelled (clean-glass simulation).
Units: the option spec is metres; the environment spec is millimetres (converted here, once).
"""
from __future__ import annotations

from .. import daylight as D
from .. import villa_env as E
from . import revit_spec as RS
from . import villa as V

LEVEL_Z = {"B": -3.0, "GF": 0.0}
ENV_LEVEL_Z = {"Street +-0.00": -1.2, "B -1.80": -3.0, "GF +1.20": 0.0, "APT +4.20 (not ours)": 3.0,
               "APT roof +7.20": 6.0}
SLAB_T = 0.2


def _m(pts):
    return [(x / 1000.0, y / 1000.0) for x, y in pts]


def _openings_on(wall, level, windows, doors):
    """Openings of the spec that sit on this wall's centreline (within half its thickness + 0.1 m)."""
    (xa, ya), (xb, yb) = (wall["x0"], wall["y0"]), (wall["x1"], wall["y1"])
    L = ((xb - xa) ** 2 + (yb - ya) ** 2) ** 0.5
    ux, uy = (xb - xa) / L, (yb - ya) / L
    out = []
    for o, is_door in [(w, False) for w in windows] + [(d, True) for d in doors]:
        if o["level"] != level:
            continue
        dx, dy = o["x"] - xa, o["y"] - ya
        along, across = dx * ux + dy * uy, abs(-dx * uy + dy * ux)
        if across > wall["thickness"] / 2 + 0.1 or not (-0.01 <= along <= L + 0.01):
            continue
        if is_door:
            kind = "glazed" if (o.get("garden") or o.get("sliding")) else "door"
            sill, head = 0.0, o.get("height", 2.1)
        else:
            kind, sill, head = "window", o["sill"], o["sill"] + o["height"]
        out.append({"offset": along - o["width"] / 2, "width": o["width"], "sill": sill, "head": head, "kind": kind})
    return out


# Mitigation study (client r8: "if we keep the east side expansion, what maximises daylight?"): case -> (option,
# variant). P3-open / P5-open: the one-car option with nothing built beyond the parked car (villa_parking.option(...,
# open_beyond=True)). The pass bar is fixed before the run in MITIGATION_BAR. Client r9 dropped P1/P2 (the U stair)
# before any variant result was read; the same variants now run on the straight-stair options.
VARIANTS = {
    "P3-white": ("P3", {"white": True}),
    "P3-glass": ("P3", {"glass_partitions": True}),
    "P3-open": ("P3-open", {}),
    "P3-slot": ("P3", {"slot": 0.9}),
    "P3-slot-car": ("P3", {"slot": 0.9, "car": True}),
    "P3-combo": ("P3-open", {"white": True, "glass_partitions": True}),
    "P4-white": ("P4", {"white": True}),
    "P4-glass": ("P4", {"glass_partitions": True}),
    "P4-slot": ("P4", {"slot": 0.9}),
    "P4-slot-car": ("P4", {"slot": 0.9, "car": True}),
    "P4-combo": ("P4", {"white": True, "glass_partitions": True}),
    "P5-combo": ("P5-open", {"white": True, "glass_partitions": True}),
}
MITIGATION_BAR = {                     # registered 2026-09-26, before any variant result was seen
    "rooms": ["lounge", "media", "kitchen"],
    "sda300_50_min_pct": ("ies-sda-area-acceptable", 50),
    "adf_min_pct": {"living": ("sll-min-adf-living", 1.5), "kitchen": ("sll-min-adf-kitchen", 2.0)},
    "note": "a room passes when it meets both its IES sDA card and its SLL ADF card; media is a living room by "
            "occupancy but may be the cinema (client), so it is reported, not required",
}


def variant_layouts():
    """{case: (layout, variant)} for the mitigation study."""
    from . import villa_parking as P
    lays = {l["id"]: l for l in P.options() + [P.option("straight", 1, open_beyond=True),
                                               P.option("straight", 1, open_beyond=True, day_room=True)]}
    return {case: (lays[oid], v) for case, (oid, v) in VARIANTS.items()}


def _cut_profile(prof, x):
    """The top profile [(x, z)] split at x: (the part before, the part after), both including x."""
    z = None
    for (xa, za), (xb, zb) in zip(prof, prof[1:]):
        if xa - 1e-9 <= x <= xb + 1e-9:
            z = za + (zb - za) * (x - xa) / (xb - xa) if xb > xa else za
            break
    if z is None:
        return (prof, []) if x >= prof[-1][0] else ([], prof)
    return ([p for p in prof if p[0] < x - 1e-9] + [(x, z)], [(x, z)] + [p for p in prof if p[0] > x + 1e-9])


def _slot_spec(sp, lay, w):
    """Daylight variant: a slot w wide along the basement's east face, from the villa's corner (x X0) to the end of
    the extension, under a drive-over grating in the ramp, deck and roof. The rooms under them start w further out
    (a new wall on y YE + w, up to the soffit); the bar's east face becomes an outside wall, glazed floor to beam
    across each column-free run (REVEAL each side); the link doors across the slot are left out (bridges)."""
    from . import villa_parking as P
    zb = RS.LEVELS_Z["B"]
    sx0, sx1 = V.X0, max(r[2] for r in V._exts(lay.get("extension")))
    ye, yw = V.YE, round(V.YE + w, 3)
    walls = []
    for wl in sp["walls"]:
        horiz = abs(wl["y0"] - wl["y1"]) < 1e-6
        in_x = sx0 - 1e-6 <= min(wl["x0"], wl["x1"]) and max(wl["x0"], wl["x1"]) <= sx1 + 1e-6
        if wl["level"] == "B" and not horiz and in_x and min(wl["y0"], wl["y1"]) < yw and \
                max(wl["y0"], wl["y1"]) > ye + 1e-6:
            a, b = sorted((wl["y0"], wl["y1"]))
            wl = dict(wl, y0=max(a, yw), y1=b)            # the extension's cross walls start beyond the slot
        walls.append(wl)
    on_face = lambda o: o["level"] == "B" and abs(o["y"] - ye) < 0.05 and sx0 <= o["x"] <= sx1   # noqa: E731
    doors = [d for d in sp["doors"] if not on_face(d)]
    wins = [x for x in sp["windows"] if not on_face(x)]
    for _, _, a, b in V._minus_columns([("h", ye, sx0, sx1)]):
        if b - a - 2 * RS.REVEAL >= 0.6:
            wins.append({"level": "B", "x": (a + b) / 2, "y": ye, "width": round(b - a - 2 * RS.REVEAL, 2),
                         "sill": 0.0, "height": RS.HEAD, "room": "slot"})
    soff = [(x, zb + c) for x, c in P.soffit_points(sx0, sx1)]
    return dict(sp, walls=walls, doors=doors, windows=wins,
                slot={"x0": sx0, "x1": sx1, "y0": ye, "y1": yw,
                      "wall": {"profile": [(sx0, zb), (sx1, zb)] + soff[::-1], "y0": yw, "y1": round(yw + 0.1, 3)}})


def scene(lay, variant=None) -> D.Scene:
    """variant (daylight mitigation studies; None = the option as specified):
       white: fences, the NE yard wall and our walls and ceilings flat white (0.80);
       glass_partitions: the walls between the bar and the extension glazed floor to beam;
       slot: width (m) of a grated slot along the basement's east face (_slot_spec);
       car: the car(s) parked on the deck."""
    v = variant or {}
    sp = RS.build(lay)
    if v.get("slot"):
        sp = _slot_spec(sp, lay, v["slot"])
    s = D.Scene(notes=["car(s) parked on the deck" if v.get("car") else "no car parked",
                       "no furniture; internal doors closed, open-plan joins open",
                       "garden and deck doors glazed; guard rails solid",
                       "ground outside the plot flat at street level; clean glass (maintenance factor 1)"]
                + (["variant: " + ", ".join("%s=%s" % kv for kv in sorted(v.items()))] if v else []))
    env = E.spec()
    # ground outside the plot at street level, as a ring round the plot
    px0, py0, px1, py1 = (v / 1000.0 for v in E.plot())
    R = 60.0
    outer = [(px0 - R, py0 - R), (px1 + R, py0 - R), (px1 + R, py1 + R), (px0 - R, py1 + R)]
    s.add([D.Face([(x, y, -1.2) for x, y in D.with_holes(outer, [[(px0, py0), (px1, py0), (px1, py1), (px0, py1)]])],
                  "ground")])
    # environment solids (fences, neighbours, sister, apartment, core, beams, steps, street, the NE yard wall ...)
    for e in env["elements"]:
        if e.get("kind") != "box":
            continue
        mat = "white" if v.get("white") and (e["id"].startswith("fence") or e["id"] == "yard-wall-ne") else "context"
        s.add(D.prism_z(_m(e["pts"]), e["z0"] / 1000.0, e["z1"] / 1000.0, mat, mat, mat))
    for c in E.COLUMNS:                                        # the kept columns, three storeys
        x0, y0, x1, y1 = (v / 1000.0 for v in c)
        s.add(D.box(x0, y0, -3.0, x1, y1, 6.0, "wall"))
    # slabs: floor on top, ceiling underneath; our GF slab with the stair opening cut
    op = sp.get("gf_opening")
    for sl in env["slabs"]:
        z = ENV_LEVEL_Z[sl["level"]]
        poly = _m(sl["pts"])
        holes = []
        if sl["id"] == "slab-GF" and op:
            holes = [[(op[0], op[1]), (op[2], op[1]), (op[2], op[3]), (op[0], op[3])]]
        top = "ground" if sl["id"].startswith("yard") else "floor"
        s.add(D.prism_z(poly, z - SLAB_T, z, top, "ceiling", "wall", holes=holes))
    for rect in (V.FRONT_SHARE, V.REAR_SHARE):              # the GF-level ceiling over our basement core shares
        s.add(D.box(rect[0], rect[1], -SLAB_T, rect[2], rect[3], 0.0, "ceiling", top="floor", bottom="ceiling"))
    # the option: walls with their openings, stair, block roofs / parking structures
    placed = 0
    ext_x1 = max([r[2] for r in V._exts(lay.get("extension"))] or [0.0])
    for w in sp["walls"]:
        z0 = LEVEL_Z[w["level"]]
        ops = _openings_on(w, w["level"], sp["windows"], sp["doors"])
        placed += len(ops)
        if v.get("glass_partitions") and w["level"] == "B" and abs(w["y0"] - w["y1"]) < 1e-6 and \
                abs(w["y0"] - V.YE) < RS.EXT_T and V.X0 - 1e-6 <= min(w["x0"], w["x1"]) and \
                max(w["x0"], w["x1"]) <= ext_x1 + 1e-6:
            # bar | extension: one glass wall, floor to beam
            ops = [{"offset": 0.0, "width": abs(w["x1"] - w["x0"]), "sill": 0.0, "head": RS.HEAD, "kind": "glazed"}]
        s.add(D.wall((w["x0"], w["y0"]), (w["x1"], w["y1"]), z0, w["height"], w["thickness"], ops))
    s.openings = {"spec": len(sp["windows"]) + len(sp["doors"]), "placed": placed}
    for b in sp["stair"]:
        s.add(D.box(*(v / 1000.0 for v in b), "wall"))
    slot = sp.get("slot")

    def solid_strips(x0, x1, y0, y1):
        """Plan pieces of a ramp/deck/roof strip with the slot's part taken out."""
        if not slot or x1 <= slot["x0"] + 1e-9 or x0 >= slot["x1"] - 1e-9:
            return [(x0, x1, y0, y1)]
        out = [(x0, slot["x0"], y0, y1)] if x0 < slot["x0"] - 1e-9 else []
        out.append((max(x0, slot["x0"]), min(x1, slot["x1"]), slot["y1"], y1))
        if x1 > slot["x1"] + 1e-9:
            out.append((slot["x1"], x1, y0, y1))
        return out

    def grating(xa, za, xb, zb_):
        a, b = max(xa, slot["x0"]), min(xb, slot["x1"])
        if b - a > 1e-6:                                  # ONE face: a second would square the transmittance
            za_, zb2 = (za + (zb_ - za) * (t - xa) / (xb - xa) if xb > xa else za for t in (a, b))
            s.add([D.Face([(a, slot["y0"], za_), (b, slot["y0"], zb2), (b, slot["y1"], zb2), (a, slot["y1"], za_)],
                          "grating")])

    for r in sp.get("roofs", []):
        for x0, x1, y0, y1 in solid_strips(r[0], r[2], r[1], r[3]):
            s.add(D.box(x0, y0, -SLAB_T, x1, y1, 0.0, "ceiling", top="floor", bottom="ceiling"))
        if slot:
            grating(r[0], 0.0, r[2], 0.0)
    pk = sp.get("parking2")
    if pk:
        rp = pk["ramp"]
        top = [tuple(p) for p in rp["profile"]]
        pieces = [(top, rp["y0"])]
        if slot:
            before, after = _cut_profile(top, slot["x0"])
            pieces = [(before, rp["y0"]), (after, slot["y1"])]
            for (xa, za), (xb, zb_) in zip(after, after[1:]):
                grating(xa, za, xb, zb_)
        for prof, y0 in pieces:
            if len(prof) >= 2:
                s.add(D.prism_section(prof + [(x, z - rp["thick"]) for x, z in reversed(prof)], "y", y0, rp["y1"],
                                      "ceiling", top="floor"))
        d = pk["deck"]
        for x0, x1, y0, y1 in solid_strips(d["x0"], d["x1"], d["y0"], d["y1"]):
            s.add(D.box(x0, y0, d["z_top"] - d["thick"], x1, y1, d["z_top"], "ceiling", top="floor", bottom="ceiling"))
        if slot:
            grating(d["x0"], d["z_top"], d["x1"], d["z_top"])
            f = slot["wall"]
            s.add(D.prism_section([tuple(p) for p in f["profile"]], "y", f["y0"], f["y1"], "wall"))
        for f in ([sp["infill"]] if sp.get("infill") else []) + sp.get("infills", []) + sp.get("rails", []):
            s.add(D.prism_section([tuple(p) for p in f["profile"]], "y", f["y0"], f["y1"], "wall"))
        if v.get("car"):
            for c in pk["cars"]:
                s.add(D.box(c[0], c[1], c[4], c[2], c[3], c[5], "car"))
    # rooms: the habitable and service rooms of both storeys
    for rid, r in lay["rooms"].items():
        x0, y0, x1, y1 = r["rect"]
        if slot and r.get("ext") and x1 > slot["x0"] + 1e-6:
            y0 = max(y0, slot["y1"] + 0.1)                # the room starts beyond the slot and its new wall
        s.rooms.append({"id": rid, "name": r["name"], "level": r["level"], "occupancy": r["occupancy"],
                        "z": LEVEL_Z[r["level"]], "polygon": [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]})
    if v.get("white"):
        s.faces = [D.Face(f.points, "white") if f.material in ("wall", "ceiling") else f for f in s.faces]
    return s
