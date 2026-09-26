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


def scene(lay) -> D.Scene:
    sp = RS.build(lay)
    s = D.Scene(notes=["no car parked; no furniture; internal doors closed, open-plan joins open",
                       "garden and deck doors glazed; guard rails solid",
                       "ground outside the plot flat at street level; clean glass (maintenance factor 1)"])
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
        s.add(D.prism_z(_m(e["pts"]), e["z0"] / 1000.0, e["z1"] / 1000.0, "context", "context", "context"))
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
    for w in sp["walls"]:
        z0 = LEVEL_Z[w["level"]]
        ops = _openings_on(w, w["level"], sp["windows"], sp["doors"])
        placed += len(ops)
        s.add(D.wall((w["x0"], w["y0"]), (w["x1"], w["y1"]), z0, w["height"], w["thickness"], ops))
    s.openings = {"spec": len(sp["windows"]) + len(sp["doors"]), "placed": placed}
    for b in sp["stair"]:
        s.add(D.box(*(v / 1000.0 for v in b), "wall"))
    for r in sp.get("roofs", []):
        s.add(D.box(r[0], r[1], -SLAB_T, r[2], r[3], 0.0, "ceiling", top="floor", bottom="ceiling"))
    pk = sp.get("parking2")
    if pk:
        rp = pk["ramp"]
        top = [tuple(p) for p in rp["profile"]]
        s.add(D.prism_section(top + [(x, z - rp["thick"]) for x, z in reversed(top)], "y", rp["y0"], rp["y1"],
                              "ceiling", top="floor"))
        d = pk["deck"]
        s.add(D.box(d["x0"], d["y0"], d["z_top"] - d["thick"], d["x1"], d["y1"], d["z_top"], "ceiling",
                    top="floor", bottom="ceiling"))
        for f in ([sp["infill"]] if sp.get("infill") else []) + sp.get("infills", []) + sp.get("rails", []):
            s.add(D.prism_section([tuple(p) for p in f["profile"]], "y", f["y0"], f["y1"], "wall"))
    # rooms: the habitable and service rooms of both storeys
    for rid, r in lay["rooms"].items():
        x0, y0, x1, y1 = r["rect"]
        s.rooms.append({"id": rid, "name": r["name"], "level": r["level"], "occupancy": r["occupancy"],
                        "z": LEVEL_Z[r["level"]], "polygon": [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]})
    return s
