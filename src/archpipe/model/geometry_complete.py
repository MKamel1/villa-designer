"""Completion of the design model: the things Revit used to fill in silently (plan rows A9-A17, I11).

`complete(elements, lay, sp, finish)` takes the elements the generators produce and returns them with
  * floor slabs for B and GF (A9) and layered build-ups on every wall, slab, floor finish and ceiling (A10);
  * floor-finish and ceiling elements per room, with ceiling heights including cove bands and soffits (A11);
  * shared type elements; each door, window, furniture, dressing and luminaire references one by `params.type_id` (A12);
  * door handing and operation (geometry_doors, A13/I11);
  * sizes derived for luminaires, dressing and plants (geometry_sizes, A14);
  * per-edge records of the stair-void guard, including the return edge (A15);
  * the storeys L1 (apartment above), ROOF and the roof garden as context (A17);
  * the link from each kept column to the frozen existing-structure record (geometry_existing, U15).
Every layer states its source; a thickness the sources do not give stays None with `status` saying why (plan principle:
never invent). Nothing here reads Revit or an untracked file.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from ..contracts import DesignElement
from . import geometry_doors, geometry_existing, geometry_sizes
from .geometry_net import wall_slab
from .spec_source import LEVELS, mm

BUILD_UPS = Path(__file__).resolve().parents[3] / "knowledge" / "finish-build-ups.json"
# wall finish code (villa_render.FINISH) -> assembly in finish-build-ups.json; codes absent here have no recorded build-up
WALL_ASSEMBLY = {"plaster-warm-white": "interior-plaster", "marble-bath": "marble-wall-thinset"}
FUNCTION = {"interior-plaster": "finish", "wall-tile-bed": "substrate", "porcelain-wall-tile": "finish",
            "interior-marble-slab": "finish", "floor-tile-bed": "substrate", "suspended-gypsum-ceiling": "finish",
            "exterior-render": "finish"}
UNSPECIFIED_STRUCTURE = "structure, material not authored (the spec and the CAD give a thickness only)"


class CompletionError(RuntimeError):
    pass


def _records() -> dict:
    d = json.loads(BUILD_UPS.read_text(encoding="utf-8"))
    return d["records"], d["assemblies"]


def _layer(rec_id: str, recs: dict) -> dict:
    r = recs[rec_id]
    return dict(function=FUNCTION.get(rec_id, "finish"), material=rec_id, thickness_mm=r.get("selected_mm"),
                status=r["status"], source=f"knowledge/finish-build-ups.json#{rec_id}",
                note=r.get("selection") or r.get("reason") or "")


def _slug(*parts) -> str:
    return "-".join(str(p).replace("/", "-").replace(" ", "-").replace(".", "_") for p in parts if p not in ("", None))


def _poly(coords_mm) -> Polygon:
    return Polygon([(x, y) for x, y in coords_mm])


def _poly_mm(g) -> list[list[float]]:
    if g.geom_type != "Polygon":
        g = max(g.geoms, key=lambda q: q.area)
    return [[round(x, 1), round(y, 1)] for x, y in g.exterior.coords][:-1]


# ------------------------------------------------------------------------------------------------ levels (A17)
def storeys(sp, els) -> list[DesignElement]:
    roof_slab = next((e for e in els if e.id.startswith("slab-roof")), None)
    rows = [("B", "B", "Basement", True, "our storey: FFL -3000 mm (scene datum)"),
            ("GF", "GF", "Ground floor", True, "our storey: FFL 0 (scene datum)"),
            ("L1", "L1", "First floor: the identical apartment above our GF (not ours)", False,
             "villa_env: apartment floor at +3000, apartment-above prism; context only"),
            ("ROOF", "ROOF", "Roof of the apartment block (not ours)", False,
             "villa_env: apartment roof slab top at +6000 (ASSUMED same 3.0 m storey height, BRIEF)")]
    out = []
    for lv, level, name, ours, basis in rows:
        L = LEVELS[lv]
        out.append(DesignElement(
            id=f"storey-{lv}", kind="storey", level=level, placement=(0.0, 0.0, float(L["ffl_scene_mm"])),
            params=dict(name=name, ours=ours, elevation_scene_mm=L["ffl_scene_mm"], elevation_revit_mm=L["ffl_revit_mm"],
                        slab_mm=L["slab_mm"], context=not ours, basis=basis)))
    top = 0.0 if roof_slab is None else roof_slab.placement[2] + roof_slab.size[2]
    out.append(DesignElement(
        id="storey-roof-garden", kind="storey", level="SITE", placement=(0.0, 0.0, top),
        params=dict(name="Roof garden: the planted extension roof beyond the parking deck", ours=False, context=True,
                    elevation_scene_mm=top, elevation_revit_mm=top + 1200.0, slab_mm=200,
                    basis="top of the extension roof slab (slab-roof-*, revit_spec roofs) in the scene datum; the garden "
                          "'top' zone of villa_landscape stands on it. Not ours as a storey: context for the landscape.")))
    return out


# ------------------------------------------------------------------------------------------------ slabs (A9, A10)
def _footprint(lay, sp, level):
    rects = [box(*r["rect"]) for r in lay["rooms"].values() if r["level"] == level]
    walls = [wall_slab(w) for w in sp["walls"] if w["level"] == level]
    return unary_union(rects + walls)


def floor_slabs(lay, sp, finish, recs) -> list[DesignElement]:
    out = []
    for lv in ("B", "GF"):
        fp = _footprint(lay, sp, lv)
        if lv == "GF":                                    # the stair rises through the GF slab: the opening is the stair void
            fp = fp.difference(box(*sp["gf_opening"]))
        gf_only = fp.geom_type != "Polygon"
        fp = fp.simplify(0.0005)
        polys = list(fp.geoms) if gf_only else [fp]
        thick = LEVELS[lv]["slab_mm"]
        for k, g in enumerate(sorted(polys, key=lambda q: -q.area)):
            x0, y0, x1, y1 = g.bounds
            out.append(DesignElement(
                id=f"slab-{lv}-floor" + (f"-{k + 1}" if k else ""), kind="slab", level=lv,
                placement=(mm((x0 + x1) / 2), mm((y0 + y1) / 2), -float(thick)),
                size=(mm(x1 - x0), mm(y1 - y0), float(thick)),
                params=dict(role=f"{LEVELS[lv]['name']} floor slab (structural), top at the {lv} finished floor level",
                            polygon_mm=_poly_mm(type(g)([(mm(x), mm(y)) for x, y in g.exterior.coords])),
                            holes_mm=[[[mm(x), mm(y)] for x, y in h.coords][:-1] for h in g.interiors],
                            area_m2=round(g.area, 3), thickness_mm=float(thick), top_z_mm=0.0,
                            thickness_basis="levels table slab_mm (spec level slab 200)",
                            outline_basis="union of the level's room rectangles and built wall slabs"
                                          + ("; minus the stair opening (revit_spec gf_opening)" if lv == "GF" else ""),
                            layers=[dict(function="structure", material=UNSPECIFIED_STRUCTURE, thickness_mm=float(thick),
                                         status="AUTHORED thickness, material not authored", source="spec levels")])))
    return out


def add_layers_to_existing_slabs(els) -> None:
    for e in els:
        if e.kind == "slab" and "layers" not in e.params and e.id.startswith(("slab-deck", "slab-ramp", "slab-roof", "slab-gf-terrace")):
            t = e.params.get("thickness_mm", e.size[2])
            e.params["layers"] = [dict(function="structure", material=UNSPECIFIED_STRUCTURE, thickness_mm=float(t),
                                       status="AUTHORED thickness, material not authored", source="spec")]
            e.params.setdefault("thickness_mm", float(t))


# ------------------------------------------------------------------------------------------------ wall layers (A10)
def _room_at(lay, level, x, y):
    for rid, r in lay["rooms"].items():
        x0, y0, x1, y1 = r["rect"]
        if r["level"] == level and x0 <= x <= x1 and y0 <= y <= y1:
            return rid
    return None


def wall_layers(els, lay, finish, recs) -> None:
    for w in (e for e in els if e.kind == "wall"):
        p = w.params
        dx, dy = p["x1_mm"] - p["x0_mm"], p["y1_mm"] - p["y0_mm"]
        n = math.hypot(dx, dy)
        nx, ny = -dy / n, dx / n
        mx, my = w.placement[0] / 1000.0, w.placement[1] / 1000.0
        off = p["thickness_mm"] / 2000.0 + 0.15
        sides = {}
        for tag, s in (("left", 1), ("right", -1)):
            room = _room_at(lay, w.level, mx + s * nx * off, my + s * ny * off)
            code = (finish.get(room) or ("", "", ""))[1] if room else ""
            asm = WALL_ASSEMBLY.get(code)
            if room is None:
                layers = [_layer("exterior-render", recs)]
            elif asm:
                layers = [_layer(r, recs) for r in json.loads(BUILD_UPS.read_text())["assemblies"][asm]]
            else:
                layers = [dict(function="finish", material=code or "unfinished", thickness_mm=None, status="UNVERIFIED",
                               source="villa_render.FINISH", note="no build-up recorded for this finish code")]
            sides[tag] = dict(room=room, finish_code=code, layers=layers)
        core = dict(function="structure", material=UNSPECIFIED_STRUCTURE, thickness_mm=p["thickness_mm"],
                    status="AUTHORED thickness, material not authored", source="spec walls")
        p["layers"] = [dict(side="left", **l) for l in reversed(sides["left"]["layers"])] + [dict(side="core", **core)] + \
                      [dict(side="right", **l) for l in sides["right"]["layers"]]
        p["sides"] = {k: dict(room=v["room"], finish_code=v["finish_code"]) for k, v in sides.items()}
        p["layers_basis"] = ("finish layers are in addition to the authored wall thickness (net areas match the frozen Revit "
                             "areas without deducting them); left/right are relative to the wall direction x0,y0 -> x1,y1")
        w.finish_codes = tuple(sorted({v["finish_code"] for v in sides.values() if v["finish_code"]}))


# ------------------------------------------------------------------------------------------------ floor + ceiling per room (A11)
def room_surfaces(els, lay, sp, finish, recs) -> list[DesignElement]:
    from ..concept import villa_lighting as VL
    out = []
    host = {"B": "slab-B-floor", "GF": "slab-GF-floor"}
    for r in (e for e in els if e.kind == "room"):
        rid, p = r.room, r.params
        floor_code, _wall, ceil_code = finish.get(rid) or ("", "", "")
        poly = _poly(p["net_polygon_mm"])
        x0, y0, x1, y1 = poly.bounds
        fl = [dict(function="finish", material=floor_code or "unfinished", thickness_mm=None, status="UNVERIFIED",
                   source="villa_render.FINISH",
                   note=recs["floor-tile-bed"]["selection"] + " (floor-tile-bed selected_mm is null)")]
        out.append(DesignElement(
            id=f"floor-{rid}", kind="floor", level=r.level, room=rid, host=host[r.level], finish_codes=(floor_code,),
            placement=(round((x0 + x1) / 2, 1), round((y0 + y1) / 2, 1), 0.0), size=(round(x1 - x0, 1), round(y1 - y0, 1), 0.0),
            params=dict(finish_code=floor_code, polygon_mm=p["net_polygon_mm"], area_m2=p["net_area_m2"], top_z_mm=0.0,
                        layers=fl, thickness_basis="not authored: finished floor level is the spec's FFL; no finish thickness is given")))
        base = VL.LEVEL_Z[r.level]
        zs, miss = [], 0
        for i in range(9):
            for j in range(9):
                x, y = (x0 + (x1 - x0) * (i + .5) / 9) / 1000.0, (y0 + (y1 - y0) * (j + .5) / 9) / 1000.0
                if not poly.contains(Point(x * 1000.0, y * 1000.0)):
                    continue
                try:
                    zs.append((VL.ceiling_z(r.level, x=x, y=y, room=rid, lay=lay, spec=sp) - base) * 1000.0)
                except ValueError:
                    miss += 1
        if not zs:
            raise CompletionError(f"{rid}: no ceiling height could be derived at any sample point")
        zmin, zmax = round(min(zs), 1), round(max(zs), 1)
        centre = p["clear_height_mm"]
        if rid in VL.UNDER_SOFFIT:
            kind, why = "soffit-lining", "ceiling is the lining of the ramp / deck / extension-roof soffit above (villa_lighting.ceiling_z)"
        elif rid in ("lounge", "living"):
            kind, why = "cove", ("false ceiling at %.0f mm in a %.0f mm perimeter band (bulkhead), slab soffit exposed at %.0f mm in the "
                                 "field (villa_lighting CEILING / COVE_BAND / COVE_FIELD)" % (VL.CEILING * 1000, VL.COVE_BAND * 1000, VL.COVE_FIELD * 1000))
        elif rid == VL.LOBBY_COVE_ROOM:
            kind, why = "cove", ("one-sided cove on the bedroom side: false ceiling at %.0f mm in a %.0f mm band (bulkhead) with an 80 mm upstand on its lobby edge, "
                                 "the LED strip in the coffer above the band, slab soffit exposed at %.0f mm in the field (villa_lighting CEILING / "
                                 "LOBBY_COVE_DEPTH / COVE_FIELD)" % (VL.CEILING * 1000, VL.LOBBY_COVE_DEPTH * 1000, VL.COVE_FIELD * 1000))
        elif rid == "stair-gf":
            kind, why = "slab-soffit", "slab soffit over the double-height stair void (villa_lighting COVE_FIELD)"
        else:
            kind, why = "flat", "flat false ceiling at villa_lighting CEILING"
        zones = []
        if kind == "cove":
            b = VL.COVE_BAND if rid != VL.LOBBY_COVE_ROOM else 0.0
            fx0, fy0, fx1, fy1 = (v * 1000 for v in (lambda c: (c[0] + b, c[1] + b, c[2] - b, c[3] - b - (VL.LOBBY_COVE_DEPTH if rid == VL.LOBBY_COVE_ROOM else 0.0)))(
                __import__("archpipe.concept.villa_furnish", fromlist=["x"]).clear_rect(lay, rid)))
            zones = [dict(role="bulkhead band", height_mm=round(VL.CEILING * 1000, 1), width_mm=round((VL.COVE_BAND if rid != VL.LOBBY_COVE_ROOM else VL.LOBBY_COVE_DEPTH) * 1000, 1)),
                     dict(role="raised field", height_mm=round(VL.COVE_FIELD * 1000, 1), polygon_mm=[[round(fx0, 1), round(fy0, 1)], [round(fx1, 1), round(fy0, 1)], [round(fx1, 1), round(fy1, 1)], [round(fx0, 1), round(fy1, 1)]])]
        out.append(DesignElement(
            id=f"ceiling-{rid}", kind="ceiling", level=r.level, room=rid, host=host[r.level], finish_codes=(ceil_code,),
            placement=(round((x0 + x1) / 2, 1), round((y0 + y1) / 2, 1), centre), size=(round(x1 - x0, 1), round(y1 - y0, 1), 0.0),
            params=dict(finish_code=ceil_code, ceiling_kind=kind, polygon_mm=p["net_polygon_mm"], area_m2=p["net_area_m2"],
                        height_mm=centre, height_min_mm=zmin, height_max_mm=zmax, zones=zones, basis=why,
                        sampled_points=len(zs), unsampled_points=miss,
                        layers=[dict(function="finish", material="suspended gypsum ceiling", thickness_mm=None, status="UNVERIFIED",
                                     source="knowledge/finish-build-ups.json#suspended-gypsum-ceiling",
                                     note=recs["suspended-gypsum-ceiling"]["selection"])])))
    return out


# ------------------------------------------------------------------------------------------------ shared types (A12)
def _type_key(e: DesignElement):
    p = e.params
    if e.kind == "door":
        return ("door", p["operation"], p["width_mm"], p["height_mm"], p.get("leaf_count"), bool(p.get("garden")))
    if e.kind == "window":
        return ("window", p["width_mm"], p["height_mm"], p["sill_mm"], p["full_height"])
    if e.kind == "furniture":
        return ("furniture", p["type"], e.product_id or "-", *e.size)
    if e.kind == "luminaire":
        return ("luminaire", e.product_id or "-", p["fixture_kind"], p["mount"], e.size[0], e.size[1])
    return None


def _type_id(k) -> str:
    return "type-" + _slug(*[("%g" % v) if isinstance(v, float) else v for v in k])


SHARED = {"door": ("operation", "width_mm", "height_mm", "leaf_count", "garden", "clear_width_mm", "structural_opening_mm"),
          "window": ("width_mm", "height_mm", "sill_mm", "full_height"),
          "furniture": ("type",),
          "luminaire": ("fixture_kind", "mount", "layer", "flux_lm", "watts", "cct_k", "cri", "beam_deg", "photometry")}


def shared_types(els) -> list[DesignElement]:
    groups: dict[tuple, list[DesignElement]] = {}
    for e in els:
        k = _type_key(e)
        if k:
            groups.setdefault(k, []).append(e)
    out = []
    for k, members in groups.items():
        tid = _type_id(k)
        first = members[0]
        shared = {a: first.params.get(a) for a in SHARED[k[0]]}
        for m in members:
            m.params["type_id"] = tid
        out.append(DesignElement(
            id=tid, kind="type", level="SITE", product_id=first.product_id, size=first.size, finish_codes=first.finish_codes,
            params=dict(for_kind=k[0], shared=shared, occurrences=len(members), occurrence_ids=[m.id for m in members],
                        key=list(k), basis="elements of one kind with identical shared parameters, size and product share one type")))
    return out


# ------------------------------------------------------------------------------------------------ stair-void guard (A15)
def guard_edges(els, sp) -> None:
    g = next((e for e in els if e.id == "rail-gf-stair-void"), None)
    if g is None:
        raise CompletionError("rail-gf-stair-void is missing: the GF stair void has no guard element")
    path = g.params["path_mm"]
    x0, y0, x1, y1 = (v * 1000 for v in sp["gf_opening"])
    opening = [("south", (x0, y0), (x1, y0)), ("east-return", (x1, y0), (x1, y1)), ("north", (x1, y1), (x0, y1)), ("west", (x0, y1), (x0, y0))]
    # the spec's opening rect is [x0, y0, x1, y1] = [5.177, -28.421, 8.887, -27.471]; its y1 edge is the guarded gallery edge
    roles = {"y1": "open edge on the gallery side (guarded)", "x1": "return edge at the corridor (guarded)",
             "x0": "stair arrival edge to the GF landing (not guarded: the flight arrives here)",
             "y0": "wall side: the 200 mm GF wall face lies 50 mm beyond the opening edge (not guarded)"}
    edges = []
    for i, (a, b) in enumerate(zip(path, path[1:])):
        edges.append(dict(index=i, start_mm=a[:2], end_mm=b[:2], length_mm=round(math.hypot(b[0] - a[0], b[1] - a[1]), 1),
                          role="open edge on the gallery side" if i == 0 else "return edge at the corridor", guarded=True))
    ret = edges[-1]
    ret["along"] = "y" if abs(ret["start_mm"][0] - ret["end_mm"][0]) < 1e-6 else "x"
    perim = []
    for name, (ax, ay), (bx, by) in [("y1", (x0, y1), (x1, y1)), ("x1", (x1, y1), (x1, y0)), ("y0", (x1, y0), (x0, y0)), ("x0", (x0, y0), (x0, y1))]:
        guarded = any(abs(e["start_mm"][0] - ax) < 1 and abs(e["start_mm"][1] - ay) < 1 and abs(e["end_mm"][0] - bx) < 1
                      and abs(e["end_mm"][1] - by) < 1 for e in edges)
        perim.append(dict(edge=name, start_mm=[round(ax, 1), round(ay, 1)], end_mm=[round(bx, 1), round(by, 1)], role=roles[name], guarded=guarded))
    g.params.update(edges=edges, return_edge=ret, void_perimeter=perim,
                    return_edge_basis="the guard path's second segment: x = %.1f mm, y %.1f to %.1f mm, 1100 mm glass, "
                                      "at the corridor end of the void" % (ret["start_mm"][0], ret["start_mm"][1], ret["end_mm"][1]))
    if not all(p["guarded"] for p in perim[:2]):
        raise CompletionError("the guard path does not follow the stair void's gallery and return edges")


# ------------------------------------------------------------------------------------------------ existing structure (U15)
def link_existing(els) -> None:
    for c in (e for e in els if e.kind == "column"):
        p = c.params
        m = geometry_existing.match_column(p["x0_mm"], p["y0_mm"], p["x1_mm"], p["y1_mm"])
        if m is None:
            raise geometry_existing.ExistingDataError(f"{c.id}: kept column has no record in knowledge/existing/omar-inventory.json")
        p.update(existing_id=m["id"], existing_name=m["name"], existing_source="knowledge/existing/omar-inventory.json",
                 existing_bbox_mm=[m["bbox"]["min"], m["bbox"]["max"]], existing_level=m["level"])


# ------------------------------------------------------------------------------------------------ doors
def door_operations(els, lay, sp) -> None:
    from .. import villa_env as E
    decisions = geometry_doors.decide(sp, lay, els, E.COLUMNS)
    keyed = {}
    for i, d in enumerate(sp["doors"]):
        keyed.setdefault(("door-" + d["level"] + "-" + "-".join(d["rooms"])), []).append(i)
    doors = [e for e in els if e.kind == "door"]
    if len(doors) != len(sp["doors"]):
        raise CompletionError("door element count differs from the spec")
    for e, i in zip(doors, range(len(sp["doors"]))):      # spec_source.doors preserves spec order
        d, dec = sp["doors"][i], decisions[i]
        p = e.params
        if dec["operation"] == "hinged":
            p.update(hinge_side=dec["hinge_side"], swing_into=dec["swing_into"], swing_known=True, handing=dec["handing"],
                     hinge_xy_mm=dec["hinge_xy_mm"], swing_arc_radius_mm=dec["swing_arc_radius_mm"],
                     swing_basis=p.get("swing_basis") if dec["authored"] and d.get("swing") else
                     "swings into %s: %s" % (dec["swing_into"], dec["decided_by"]))
        else:
            p.update(handing=dec["handing"])
        p.update(decided_by=dec["decided_by"], judgement=dec["judgement"], judgement_reasons=dec["judgement_reasons"],
                 swing_clear=dec["swing_clear"])
        if dec["operation"] == "hinged":
            p["swing_stair_clear"] = dec["swing_stair_clear"]


def complete(els: list[DesignElement], lay, sp, finish: dict) -> list[DesignElement]:
    recs, _asm = _records()
    els = list(els)
    link_existing(els)
    door_operations(els, lay, sp)
    wall_layers(els, lay, finish, recs)
    add_layers_to_existing_slabs(els)
    guard_edges(els, sp)
    geometry_sizes.apply(els)
    els += floor_slabs(lay, sp, finish, recs) + storeys(sp, els)
    els += room_surfaces(els, lay, sp, finish, recs)
    els += shared_types(els)
    return els
