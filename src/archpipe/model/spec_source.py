"""Design-model elements derived from the design layout and the Revit spec (fast path, a few seconds).

Sources: `villa_r11.design(d)` (rooms, links, entries), `revit_spec.build(lay)` (walls, doors, windows, stair, balustrades,
parking ramp / deck / roofs, wet zones), `villa_env` (columns, beams, context), `villa_lighting` level constants.

Units: millimetres. `placement` is the element's reference point: the centre of its plan footprint, with z measured
from that level's finished floor (walls and stairs: z of the base). Absolute z of every level is in LEVELS.
"""
from __future__ import annotations

import math

from ..contracts import DesignElement
from . import stair_steel as SS

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
def rooms(lay, sp, finish: dict | None = None, net: dict | None = None, reference: dict | None = None) -> list[DesignElement]:
    from ..concept import villa_furnish as F
    from ..concept import villa_lighting as VL
    from .. import villa_env as E
    from . import geometry_net as GN
    net = GN.net_areas(lay, sp, E.COLUMNS) if net is None else net           # from the built wall faces (no Revit input)
    reference = GN.frozen_reference() if reference is None else reference   # frozen Revit areas: comparison only
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
                area_m2=poly_area_m2(poly), gross_area_m2=poly_area_m2(poly), clear_height_mm=clear_h,
                clear_rect_mm=rect_poly_mm(clear), clear_area_m2=poly_area_m2(rect_poly_mm(clear)),
                revit_net_area_m2=reference.get(rid),
                net_area_m2=net[rid]["net_m2"], net_polygon_mm=net[rid]["polygon_mm"],
                net_wall_deduction_m2=net[rid]["walls_m2"], net_column_deduction_m2=net[rid]["columns_m2"],
                net_area_deviation_m2=(round(net[rid]["net_m2"] - reference[rid], 3) if rid in reference else None),
                net_area_basis=("room rectangle minus built wall slabs (axis +/- half thickness), pocket buildouts and "
                                "kept columns (geometry_net); finishes not deducted. Frozen Revit value in "
                                "revit_net_area_m2 is the reference, not an input"),
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
                        span=list(d.get("span", [])), type=d.get("type", ""), **_door_operation(d))))
    return out


def _door_operation(d) -> dict:
    """Operation, swing and clear width of a spec door. The spec authors the leaf width and a door *type*
    (villa_furnish.DOOR_TYPES: pocket, or hinged swinging into one named room); it does not author a hinge side."""
    from ..concept import villa_furnish as F
    key = "/".join(d.get("rooms") or [])
    typ = F.DOOR_TYPES.get(key) or ""
    clear = d["width"]
    if d.get("sliding") or d.get("garden"):
        pocket = "pocket" in str(d.get("slide_type", ""))
        n = d.get("leaf_count") or 1
        if n > 1 and not pocket:
            clear = d["width"] / n          # bypass leaves overlap: one leaf's share of the opening stays covered
        op = "sliding"
        basis = ("pocket leaves retract into the wall: full width clear" if pocket else
                 f"bypass set of {n} leaves: width / {n} is clear at a time" if n > 1 else
                 "single sliding leaf: authored width taken as the opening (leaf overlap not authored)")
    elif typ == "pocket":
        op, basis = "pocket", "pocket leaf slides into the wall; the opening equals the leaf width"
    else:
        op, basis = "hinged", ("upper bound: nominal leaf width; a leaf open at 90 degrees loses its thickness and "
                               "stop (not authored)")
    into = typ[5:] if typ.startswith("into:") else ""
    sw = d.get("swing") or {}
    if sw:                                   # G1 LS4: the spec authors the swing (revit_spec._g1_fixes)
        into = sw["into"]
    return dict(
        operation=op, swing_into=into,
        swing_known=bool(into) or op != "hinged", hinge_side=sw.get("hinge_side", ""),
        swing_direction=sw.get("direction", ""), near_jamb_to_top_step_mm=(
            mm(sw["near_jamb_to_top_step"]) if sw.get("near_jamb_to_top_step") is not None else None),
        swing_basis=(sw["basis"] if sw else "swings into " + into if into else
                     "direction not authored: swing squares kept clear on both sides" if op == "hinged" else "no swing"),
        leaf_width_mm=mm(d["width"]), structural_opening_mm=mm(d["width"] + 0.1),   # leaf + 50 mm frame each side
        clear_width_mm=mm(clear), clear_width_basis=basis,
        leaf_count=d.get("leaf_count", 1 if op == "hinged" else None), garden=bool(d.get("garden")))


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
                        full_height=bool(w.get("full_height", False)), span=list(w.get("span", [])),
                        gross_area_m2=round(w["width"] * w["height"], 4), operation=None, openable_area_m2=None,
                        openable_basis="not authored: the spec records no operable sash, so L1 must apply a policy "
                                       "(gross glazed area is the upper bound)")))
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
    depth = abs(boxes[0][3] - boxes[0][0])                 # plan depth of one tread box (going + nosing overlap)
    tread = round(boxes[0][3] - boxes[1][3], 3) if len(boxes) > 1 else depth      # going: nosing to nosing
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
                    going_mm=tread, tread_depth_mm=depth, nosing_overlap_mm=sp.get("stair_nosing_overlap_mm", 0),
                    tread_thickness_mm=round(boxes[0][5] - boxes[0][2], 1),
                    riser_infill=_riser_infill(sp), infill_waiver=sp.get("stair_infill_waiver") or {},
                    steel=dict(members=SS.members(sp), wall_side_y_mm=mm(SS.clear_y(sp)[0]), open_side_y_mm=mm(SS.clear_y(sp)[1]),
                               basis=SS.BASIS),
                    under_flight=_under_flight(sp),
                    nosing_note="tread_mm is the going (nosing to nosing, unchanged by the overlap); each tread but "
                                "the top one runs tread_depth_mm - going_mm under the next nosing (ADK 1.9a)"))]


GUARD_IDS = {"guard-gf-stair-void": "rail-gf-stair-void", "guard-gf-terrace-edge": "rail-gf-terrace-edge",
             "guard-entrance-steps-patio-edge": "rail-patio-steps-edge"}


def _guard_elements(sp) -> list[DesignElement]:
    """The G1 guards (revit_spec._g1_fixes): the GF stair void, the GF front terrace edge and the entrance-steps edge
    over the north patio. Element ids keep the railing prefix `rail-` (the stair's own rails are `rail-stair-*`)."""
    out = []
    for g in sp.get("guards", []):
        path = g["path"]
        segs = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:])]
        xs, ys = [p[0] for p in path], [p[1] for p in path]
        h = mm(g["height_m"])
        out.append(DesignElement(
            id=GUARD_IDS.get(g["id"], "rail-" + g["id"]), kind="railing", level=g["level"],
            placement=(mm((min(xs) + max(xs)) / 2), mm((min(ys) + max(ys)) / 2), mm(path[0][2])),
            size=(mm(max(xs) - min(xs)), mm(max(ys) - min(ys)), h),
            room="stair-gf" if g["id"] == "guard-gf-stair-void" else "",
            params=dict(
                what=g["what"], guard_height_mm=h, material=g["material"], infill=g["infill"],
                glazed=g["infill"] == "glass", max_opening_mm=g["max_opening_mm"], climbable=g["climbable"],
                top_rail=g["top_rail"], thickness_mm=mm(g["thickness_m"]), kind=g["kind"],
                path_mm=[[mm(p[0]), mm(p[1]), mm(p[2])] for p in path], edge_lengths_mm=[mm(v) for v in segs],
                length_mm=mm(sum(segs)), drop_mm=mm(g["drop_m"]),
                drop_min_mm=mm(g["drop_min_m"]) if g.get("drop_min_m") is not None else mm(g["drop_m"]),
                in_revit_spec=True, in_scene=g["id"] == "guard-gf-stair-void",
                scene_mesh="detail-stair-guard" if g["id"] == "guard-gf-stair-void" else "", basis=g["basis"])))
    return out


def _riser_infill(sp) -> dict:
    """The open-riser infill (G1 LS2): one horizontal flat bar per gap between treads; {} when the spec has none."""
    spec = sp.get("stair_infill_spec") or {}
    if not spec:
        return {}
    bars = sp.get("stair_infill") or []
    return dict(spec, present=True, bar_boxes_mm=[list(b) for b in bars], sphere_test_mm=100.0,
                openings_above_and_below_bar_mm=spec["max_clear_opening_mm"], basis=(
                    "a horizontal flat bar %d x %d mm centred in each %.1f mm gap between treads leaves two openings of "
                    "%.1f mm: no 100 mm sphere passes (ADK 1.9)" % (spec["bar_h_mm"], spec["bar_t_mm"], spec["gap_mm"],
                                                                   spec["max_clear_opening_mm"])))


def _under_flight(sp) -> dict:
    cb = sp.get("understair_cupboard")
    if not cb:
        return dict(enclosed=False)
    return dict(enclosed=True, cupboard_id="joinery-" + cb["id"], treads_enclosed=cb["treads"],
                soffit_min_mm=mm(cb["soffit_min_m"]), soffit_max_mm=mm(cb["soffit_max_m"]))


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
    out += _guard_elements(sp)
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


def context(sp=None) -> list[DesignElement]:
    from .. import villa_env as E
    guarded = any(g["id"] == "guard-entrance-steps-patio-edge" for g in (sp or {}).get("guards", []))
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
                        z0_scene_mm=e["z0"], z1_scene_mm=e["z1"],
                        **(dict(guard_present=guarded, guard_id="rail-patio-steps-edge" if guarded else "",
                                drop_mm=e["z1"] - e["z0"],
                                guard_basis=("shared entrance steps (not ours): G1 guard on their edge over the open "
                                             "patio court (rail-patio-steps-edge)") if guarded else
                                "shared entrance steps (not ours); no guard in villa_env, spec or scene")
                           if e["id"] == "entrance-steps" else {}))))
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


def sunken_gardens(lay, sp=None) -> list[DesignElement]:
    ids = {g["id"] for g in (sp or {}).get("guards", [])}
    out = []
    np_ = lay.get("north_patio")
    if np_:
        x0, y0, x1, y1 = np_["rect"]
        out.append(DesignElement(
            id="garden-north-patio", kind="garden", level="SITE", placement=(mm((x0 + x1) / 2), mm((y0 + y1) / 2), 0.0),
            size=(mm(x1 - x0), mm(y1 - y0), 0.0),
            params=dict(name=np_.get("name", ""), polygon_mm=rect_poly_mm(np_["rect"]),
                        area_m2=poly_area_m2(rect_poly_mm(np_["rect"])), sunken=True, ground_scene_mm=-3000,
                        floor_below_street_mm=1800.0,
                        guard_present=bool(ids & {"guard-gf-terrace-edge", "guard-entrance-steps-patio-edge"}),
                        guard_ids=[GUARD_IDS[i] for i in sorted(ids) if i in GUARD_IDS and i != "guard-gf-stair-void"],
                        guard_basis="the patio is the low side: its edges are guarded from above (ramp-edge rail, GF "
                                    "terrace edge, entrance-steps edge); occupants are at the bottom of the drop",
                        covered_rect_mm=rect_poly_mm(np_["covered"]) if np_.get("covered") else None)))
    return out


def terrace(lay, sp=None) -> list[DesignElement]:
    """The GF front terrace slab (lay["terrace"]). No guard exists for its edge anywhere in the spec or the scene."""
    t = lay.get("terrace")
    if not t:
        return []
    x0, y0, x1, y1 = t
    return [DesignElement(
        id="slab-gf-terrace", kind="slab", level="GF", placement=(mm((x0 + x1) / 2), mm((y0 + y1) / 2), -200.0),
        size=(mm(x1 - x0), mm(y1 - y0), 200.0),
        params=dict(role="GF front (street-side) terrace", polygon_mm=rect_poly_mm(t), area_m2=poly_area_m2(rect_poly_mm(t)),
                    drop_to_patio_mm=3000.0, drop_to_street_mm=1200.0,
                    **_terrace_guard(sp)))]


def _yield_to_steel(cb, sp):
    """The cupboard as built: joinery yields to the stair steel (lane SC2). The back face is the wall-stringer bearings'
    face and the side wall's outer face is the open-side shoe's, not the structural face and the tread edge the spec
    drew, so its walls, interior, depth and volume follow."""
    back, yo = SS.clear_y(sp)
    wt = cb["walls"][0]["thickness"]
    ym, y_in = round(yo - wt / 2, 4), round(yo - wt, 4)
    walls = [dict(w, y0=ym, y1=ym) if w["id"].endswith("side") else dict(w, y0=back, y1=yo) for w in cb["walls"]]
    x0, x1 = cb["x0"], cb["x1"]
    vol = sum((xa - xb - (wt if xb == x0 else 0) - (wt if xa == x1 else 0)) * (y_in - back) * h
              for xa, xb, h in cb["walls"][0]["top_profile"])
    return dict(cb, y0=back, y1=yo, interior=[round(x0 + wt, 3), back, round(x1 - wt, 3), y_in], walls=walls, door=dict(cb["door"], y=ym),
                volume_m3=round(vol, 2))


def cupboard(sp) -> list[DesignElement]:
    """The cupboard enclosing the space under the lowest treads (G1 LS1): one joinery element carrying its walls and door."""
    cb = sp.get("understair_cupboard")
    if not cb:
        return []
    cb = _yield_to_steel(cb, sp)
    w = [dict(id=x["id"], role=x["role"], x0_mm=mm(x["x0"]), y0_mm=mm(x["y0"]), x1_mm=mm(x["x1"]), y1_mm=mm(x["y1"]),
              thickness_mm=mm(x["thickness"]),
              height_mm=mm(x["height"]) if "height" in x else None,
              top_profile_mm=[[mm(a), mm(b), mm(h)] for a, b, h in x["top_profile"]] if "top_profile" in x else None)
         for x in cb["walls"]]
    d = cb["door"]
    return [DesignElement(
        id="joinery-" + cb["id"], kind="furniture", level="B", room=cb["room"],
        placement=(mm((cb["x0"] + cb["x1"]) / 2), mm((cb["y0"] + cb["y1"]) / 2), 0.0),
        size=(mm(cb["x1"] - cb["x0"]), mm(cb["y1"] - cb["y0"]), mm(cb["soffit_max_m"])),
        params=dict(type="understair-cupboard", enclosed=cb["enclosed"], treads_enclosed=cb["treads"],
                    interior_mm=[mm(v) for v in cb["interior"]], soffit_min_mm=mm(cb["soffit_min_m"]),
                    soffit_max_mm=mm(cb["soffit_max_m"]), volume_m3=cb["volume_m3"], walls=w,
                    door=dict(id=d["id"], x_mm=mm(d["x"]), y_mm=mm(d["y"]), width_mm=mm(d["width"]),
                              height_mm=mm(d["height"]), operation=d["operation"], hinge_side=d["hinge_side"],
                              swing_into=d["swing_into"], soffit_over_door_mm=mm(d["soffit_over_door_m"]), basis=d["basis"]),
                    basis=cb["basis"]))]


def _terrace_guard(sp) -> dict:
    g = next((g for g in (sp or {}).get("guards", []) if g["id"] == "guard-gf-terrace-edge"), None)
    if g is None:
        return dict(guard_present=False, guard_basis="no guard or parapet for the terrace edge in revit_spec, "
                    "villa_render or villa_env (the apartment-above terrace has an assumed 1.1 m parapet zone, not ours)")
    return dict(guard_present=True, guard_id="rail-gf-terrace-edge", guard_height_mm=mm(g["height_m"]),
                guard_basis="G1 guard on the terrace edge (west edge and ramp side), " + g["basis"])


def all_from_spec(lay, sp, finish=None) -> list[DesignElement]:
    wall_els = walls(sp)
    return (rooms(lay, sp, finish) + wall_els + doors(sp, wall_els) + windows(sp, wall_els) + stairs(lay, sp)
            + railings(sp) + slabs(sp) + terrace(lay, sp) + columns_beams() + context(sp) + bath_fittings(sp)
            + sunken_gardens(lay, sp) + cupboard(sp))
