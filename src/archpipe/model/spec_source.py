"""Design-model elements derived from the design layout and the Revit spec (fast path, a few seconds).

Sources: `villa_r11.design(d)` (rooms, links, entries), `revit_spec.build(lay)` (walls, doors, windows, stair, balustrades,
parking ramp / deck / roofs, wet zones), `villa_env` (columns, beams, context), `villa_lighting` level constants.

Units: millimetres. `placement` is the element's reference point: the centre of its plan footprint, with z measured
from that level's finished floor (walls and stairs: z of the base). Absolute z of every level is in LEVELS.
"""
from __future__ import annotations

import math

from ..contracts import DesignElement

# Scene datum: GF finished floor = 0. Revit datum is 1.2 m higher (spec levels "B -1.80", "GF +1.20").
LEVELS = {
    "B":    dict(ffl_scene_mm=-3000, ffl_revit_mm=-1800, slab_mm=200, name="Basement"),
    "GF":   dict(ffl_scene_mm=0, ffl_revit_mm=1200, slab_mm=200, name="Ground floor"),
    "L1":   dict(ffl_scene_mm=3000, ffl_revit_mm=4200, slab_mm=200, name="First floor (apartment, not ours)"),
    "ROOF": dict(ffl_scene_mm=6000, ffl_revit_mm=7200, slab_mm=200, name="Roof"),
    "SITE": dict(ffl_scene_mm=-3000, ffl_revit_mm=-1800, slab_mm=0, name="Site / garden ground"),
}
CEILING_MM = 2700        # gypsum false ceiling above FFL (villa_lighting.CEILING)
SLAB_SOFFIT_MM = 2800    # structural soffit (villa_lighting.COVE_FIELD)


def mm(v: float) -> float:
    return round(v * 1000.0, 1)


def rect_poly_mm(rect) -> list[list[float]]:
    x0, y0, x1, y1 = rect
    return [[mm(x0), mm(y0)], [mm(x1), mm(y0)], [mm(x1), mm(y1)], [mm(x0), mm(y1)]]


def poly_area_m2(poly_mm) -> float:
    s = 0.0
    for (x0, y0), (x1, y1) in zip(poly_mm, poly_mm[1:] + poly_mm[:1]):
        s += x0 * y1 - x1 * y0
    return round(abs(s) / 2.0 / 1e6, 4)


def _slug(*parts) -> str:
    return "-".join(str(p).replace("/", "-").replace(" ", "-") for p in parts if p not in ("", None))


# ----------------------------------------------------------------------------------------------- rooms
def rooms(lay, sp, finish: dict | None = None) -> list[DesignElement]:
    from ..concept import villa_furnish as F
    from ..concept import villa_lighting as VL
    out = []
    for rid, r in lay["rooms"].items():
        lv = r["level"]
        poly = rect_poly_mm(r["rect"])
        x0, y0, x1, y1 = r["rect"]
        clear = F.clear_rect(lay, rid)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        floor_abs = VL.LEVEL_Z[lv]
        try:
            ceil_abs = VL.ceiling_z(lv, x=cx, y=cy, room=rid, lay=lay, spec=sp)
        except ValueError:
            ceil_abs = floor_abs + VL.CEILING
        clear_h = round((ceil_abs - floor_abs) * 1000.0, 1)
        fin = (finish or {}).get(rid) or {}
        out.append(DesignElement(
            id=f"room-{rid}", kind="room", level=lv,
            placement=(mm(cx), mm(cy), 0.0), size=(mm(x1 - x0), mm(y1 - y0), clear_h),
            room=rid, finish_codes=tuple(sorted(str(v) for v in fin.values())) if isinstance(fin, dict) else (),
            params=dict(
                name=r.get("name", ""), occupancy=r.get("occupancy", ""), polygon_mm=poly,
                area_m2=poly_area_m2(poly), clear_height_mm=clear_h,
                clear_rect_mm=rect_poly_mm(clear), clear_area_m2=poly_area_m2(rect_poly_mm(clear)),
                part_of=r.get("part_of", ""), open_to=[b if a == rid else a for a, b in lay["links"] if rid in (a, b)],
                ceiling_source="villa_lighting.ceiling_z at the room centre (sloped soffits under the ramp: centre value)",
            )))
    return out


# ----------------------------------------------------------------------------------------------- walls / openings
def _wall_id(i, w):
    return f"wall-{w['level']}-{w['kind']}-{i:02d}"


def walls(sp) -> list[DesignElement]:
    out = []
    for i, w in enumerate(sp["walls"]):
        dx, dy = w["x1"] - w["x0"], w["y1"] - w["y0"]
        length = math.hypot(dx, dy)
        out.append(DesignElement(
            id=_wall_id(i, w), kind="wall", level=w["level"],
            placement=(mm((w["x0"] + w["x1"]) / 2), mm((w["y0"] + w["y1"]) / 2), 0.0),
            rotation_deg=round(math.degrees(math.atan2(dy, dx)), 3),
            size=(mm(length), mm(w["thickness"]), mm(w["height"])),
            params=dict(wall_kind=w["kind"], x0_mm=mm(w["x0"]), y0_mm=mm(w["y0"]), x1_mm=mm(w["x1"]),
                        y1_mm=mm(w["y1"]), thickness_mm=mm(w["thickness"]), height_mm=mm(w["height"]))))
    return out


def _host_wall(walls_el: list[DesignElement], level: str, x: float, y: float) -> str:
    """The wall element whose axis passes closest to the opening centre (opening in metres)."""
    best, best_d = "", 1e9
    for w in walls_el:
        if w.level != level:
            continue
        p = w.params
        ax, ay, bx, by = p["x0_mm"], p["y0_mm"], p["x1_mm"], p["y1_mm"]
        px, py = x * 1000, y * 1000
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
        d = math.hypot(px - (ax + t * dx), py - (ay + t * dy))
        if d < best_d:
            best, best_d = w.id, d
    return best if best_d <= 150 else ""


def doors(sp, wall_els) -> list[DesignElement]:
    out = []
    seen: dict[str, int] = {}
    for d in sp["doors"]:
        a, b = d["rooms"][0], d["rooms"][1] if len(d["rooms"]) > 1 else ""
        axis = (d.get("span") or ["h"])[0]
        rot = 0.0 if axis == "h" else 90.0
        did = _slug("door", d["level"], a, b)
        seen[did] = seen.get(did, 0) + 1
        if seen[did] > 1:
            did = f"{did}-{seen[did]}"
        out.append(DesignElement(
            id=did, kind="door", level=d["level"],
            placement=(mm(d["x"]), mm(d["y"]), 0.0), rotation_deg=rot,
            size=(mm(d["width"]), mm(wall_thick(wall_els, d)), mm(d["height"])),
            host=_host_wall(wall_els, d["level"], d["x"], d["y"]), room=a,
            params=dict(rooms=list(d["rooms"]), width_mm=mm(d["width"]), height_mm=mm(d["height"]),
                        clear_mm=mm(d["clear"]) if d.get("clear") else None, fit=d.get("fit", ""),
                        span=list(d.get("span", [])), type=d.get("type", ""))))
    return out


def wall_thick(wall_els, d) -> float:
    h = _host_wall(wall_els, d["level"], d["x"], d["y"])
    for w in wall_els:
        if w.id == h:
            return w.params["thickness_mm"] / 1000.0
    return 0.2


def windows(sp, wall_els) -> list[DesignElement]:
    out = []
    for i, w in enumerate(sp["windows"]):
        axis = (w.get("span") or ["h"])[0]
        out.append(DesignElement(
            id=_slug("window", w["level"], w["room"], i), kind="window", level=w["level"],
            placement=(mm(w["x"]), mm(w["y"]), mm(w["sill"])), rotation_deg=0.0 if axis == "h" else 90.0,
            size=(mm(w["width"]), mm(wall_thick(wall_els, dict(w))), mm(w["height"])),
            host=_host_wall(wall_els, w["level"], w["x"], w["y"]), room=w["room"],
            params=dict(width_mm=mm(w["width"]), sill_mm=mm(w["sill"]), height_mm=mm(w["height"]),
                        full_height=bool(w.get("full_height", False)), span=list(w.get("span", [])))))
    return out


# ----------------------------------------------------------------------------------------------- stair / railings
def stairs(lay, sp) -> list[DesignElement]:
    boxes = sp["stair"]          # [x0, y0, z0, x1, y1, z1] mm per tread, scene datum (GF FFL = 0)
    n_treads = len(boxes)
    z_tops = [b[5] for b in boxes]
    # The flight runs from the basement FFL to the GF FFL: n_treads + 1 risers.
    rise = 0 - LEVELS["B"]["ffl_scene_mm"]
    risers = n_treads + 1
    xs = [b[0] for b in boxes] + [b[3] for b in boxes]
    ys = [b[1] for b in boxes] + [b[4] for b in boxes]
    tread = abs(boxes[0][3] - boxes[0][0])
    riser = round(rise / risers, 3)
    width = max(ys) - min(ys)
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    return [DesignElement(
        id="stair-main", kind="stair", level="B",
        placement=((x0 + x1) / 2, (y0 + y1) / 2, 0.0), rotation_deg=180.0,   # climbs towards -x (street = north)
        size=(x1 - x0, y1 - y0, float(rise)), room="stair-b",
        params=dict(name=sp.get("stair_name", ""), risers=risers, treads=n_treads, riser_mm=riser,
                    tread_mm=tread, width_mm=width, rise_mm=rise, run_mm=x1 - x0,
                    tread_boxes_mm=[list(b) for b in boxes], top_landing_room="stair-gf",
                    tread_top_z_mm=[round(z, 1) for z in z_tops],
                    nosing_note="tread depth is the going between riser faces as authored in revit_spec (no nosing overlap)"))]


def railings(sp) -> list[DesignElement]:
    out = []
    for b in sp.get("balustrades", []):
        prof = b.get("nosing_profile") or []
        xs = [p[0] for p in prof]; ys = [p[1] for p in prof]
        out.append(DesignElement(
            id=f"rail-{b['id']}", kind="railing", level=b["level"],
            placement=(mm((min(xs) + max(xs)) / 2), mm((min(ys) + max(ys)) / 2), 0.0),
            size=(mm(max(xs) - min(xs)), mm(max(ys) - min(ys)), mm(b.get("height_above_nosing", 0.0))),
            host="stair-main",
            params=dict(side=b.get("side"), material=b.get("material"), support=b.get("support"),
                        guard_height_mm=mm(b.get("height_above_nosing", 0.0)),
                        measured_from="stair nosing line", glazed=("glass" in str(b.get("material"))),
                        profile_mm=[[mm(p[0]), mm(p[1]), mm(p[2])] for p in prof], basis=b.get("basis", ""))))
    for i, r in enumerate(sp.get("rails", [])):
        prof = r.get("profile") or []
        out.append(DesignElement(
            id=f"rail-edge-{i}", kind="railing", level="B",
            placement=(0.0, mm((r["y0"] + r["y1"]) / 2), 0.0),
            size=(0.0, mm(abs(r["y1"] - r["y0"])), 0.0),
            params=dict(what=r.get("what", ""), profile_mm=[[mm(a), mm(b)] for a, b in prof],
                        guard_height_mm=1100.0, note="ramp-edge guard over the north patio (card ukadk-guarding-height-external)")))
    return out


# ----------------------------------------------------------------------------------------------- slabs / ramp / deck / roofs
def slabs(sp) -> list[DesignElement]:
    p = sp["parking2"]
    out = []
    d = p["deck"]
    out.append(DesignElement(
        id="slab-deck", kind="slab", level="GF",
        placement=(mm((d["x0"] + d["x1"]) / 2), mm((d["y0"] + d["y1"]) / 2), mm(d["z_top"] - d["thick"])),
        size=(mm(d["x1"] - d["x0"]), mm(d["y1"] - d["y0"]), mm(d["thick"])),
        params=dict(role="parking deck over the basement extension", z_top_mm=mm(d["z_top"]), thickness_mm=mm(d["thick"]))))
    r = p["ramp"]
    xs = [pt[0] for pt in r["profile"]]
    out.append(DesignElement(
        id="slab-ramp", kind="slab", level="GF",
        placement=(mm((min(xs) + max(xs)) / 2), mm((r["y0"] + r["y1"]) / 2), 0.0),
        size=(mm(max(xs) - min(xs)), mm(r["y1"] - r["y0"]), mm(r["thick"])),
        params=dict(role="car ramp", profile_xz_mm=[[mm(a), mm(b)] for a, b in r["profile"]],
                    thickness_mm=mm(r["thick"]),
                    slope_pct=round(100 * (r["profile"][-1][1] - r["profile"][0][1]) / (r["profile"][-1][0] - r["profile"][0][0]), 2))))
    for i, (x0, y0, x1, y1) in enumerate(sp.get("roofs", [])):
        out.append(DesignElement(
            id=f"slab-roof-{i}", kind="slab", level="GF",
            placement=(mm((x0 + x1) / 2), mm((y0 + y1) / 2), -200.0), size=(mm(x1 - x0), mm(y1 - y0), 200.0),
            params=dict(role="extension roof (planted beyond the deck)")))
    return out


# ----------------------------------------------------------------------------------------------- structure
def columns_beams() -> list[DesignElement]:
    from .. import villa_env as E
    out = []
    for i, (x0, y0, x1, y1) in enumerate(E.COLUMNS):
        out.append(DesignElement(
            id=f"column-{i:02d}", kind="column", level="B",
            placement=((x0 + x1) / 2, (y0 + y1) / 2, 0.0), size=(x1 - x0, y1 - y0, 9000.0),
            params=dict(note="kept existing column, basement FFL (-3.0 m) to +6.0 m (three storeys), villa_daylight.scene",
                        x0_mm=x0, y0_mm=y0, x1_mm=x1, y1_mm=y1)))
    for e in E.spec()["elements"]:
        if not e["id"].startswith("beam-"):
            continue
        xs = [q[0] for q in e["pts"]]; ys = [q[1] for q in e["pts"]]
        out.append(DesignElement(
            id=e["id"], kind="beam", level="B",
            placement=((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, e["z0"] - LEVELS["B"]["ffl_scene_mm"]),
            size=(max(xs) - min(xs), max(ys) - min(ys), e["z1"] - e["z0"]),
            params=dict(note=e.get("note", ""), z0_scene_mm=e["z0"], z1_scene_mm=e["z1"])))
    return out


CONTEXT_PREFIXES = ("neighbour", "sister", "core", "apartment", "fence", "yard", "entrance", "street")


def context() -> list[DesignElement]:
    from .. import villa_env as E
    out = []
    for e in E.spec()["elements"]:
        if e["id"].startswith("beam-") or e.get("kind") != "box":
            continue
        xs = [q[0] for q in e["pts"]]; ys = [q[1] for q in e["pts"]]
        out.append(DesignElement(
            id=f"ctx-{e['id']}", kind="context", level="SITE",
            placement=((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, e["z0"]),
            size=(max(xs) - min(xs), max(ys) - min(ys), e["z1"] - e["z0"]),
            params=dict(category=e.get("category", ""), what=e["id"].split("-")[0], note=e.get("note", ""),
                        z0_scene_mm=e["z0"], z1_scene_mm=e["z1"])))
    return out


# ----------------------------------------------------------------------------------------------- fittings, gardens
def bath_fittings(sp) -> list[DesignElement]:
    out = []
    for f in sp.get("bath_fittings", []):
        x0 = f.get("x0", f.get("x")); x1 = f.get("x1", f.get("x")); y0 = f.get("y0", f.get("y")); y1 = f.get("y1", f.get("y"))
        z = f.get("z", f.get("sill", 0.0))
        h = (f["head"] - f["sill"]) if "head" in f else 0.0
        out.append(DesignElement(
            id=f"fixture-{f['id']}", kind="fixture", level=f["level"],
            placement=(mm((x0 + x1) / 2), mm((y0 + y1) / 2), mm(z)),
            size=(mm(abs(x1 - x0)), mm(abs(y1 - y0)), mm(h)), room=f["room"],
            params=dict(fixture_kind=f["kind"], over=f.get("over", ""),
                        basis=f.get("basis", f.get("optical_note", "")))))
    for z in sp.get("wet_zones", []):
        x0, y0, x1, y1 = z["rect"]
        out.append(DesignElement(
            id=f"wetzone-{z['id']}", kind="fixture", level="B", placement=(mm((x0 + x1) / 2), mm((y0 + y1) / 2), 0.0),
            size=(mm(x1 - x0), mm(y1 - y0), 0.0), room=z["room"],
            params=dict(fixture_kind="wet-zone", finished_depth_m=z.get("finished_depth_m"), status=z.get("status", ""))))
    return out


def sunken_gardens(lay) -> list[DesignElement]:
    out = []
    np_ = lay.get("north_patio")
    if np_:
        x0, y0, x1, y1 = np_["rect"]
        out.append(DesignElement(
            id="garden-north-patio", kind="garden", level="SITE", placement=(mm((x0 + x1) / 2), mm((y0 + y1) / 2), 0.0),
            size=(mm(x1 - x0), mm(y1 - y0), 0.0),
            params=dict(name=np_.get("name", ""), polygon_mm=rect_poly_mm(np_["rect"]),
                        area_m2=poly_area_m2(rect_poly_mm(np_["rect"])), sunken=True, ground_scene_mm=-3000,
                        covered_rect_mm=rect_poly_mm(np_["covered"]) if np_.get("covered") else None)))
    return out


def all_from_spec(lay, sp, finish=None) -> list[DesignElement]:
    wall_els = walls(sp)
    return (rooms(lay, sp, finish) + wall_els + doors(sp, wall_els) + windows(sp, wall_els) + stairs(lay, sp)
            + railings(sp) + slabs(sp) + columns_beams() + context() + bath_fittings(sp) + sunken_gardens(lay))
