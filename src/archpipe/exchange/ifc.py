"""IFC4 export of the design model (archpipe.model DesignElement list) -> .ifc

Geometry is built as extruded solids (IfcExtrudedAreaSolid) in millimetres, in the REVIT datum (B FFL -1800,
GF FFL +1200). Every element keeps its model id as Name/Tag and a deterministic GlobalId, so a re-export of an
unchanged model gives an identical file and a recipient can trace any object back to the design model.

Nothing is dropped silently: `preflight` runs first and raises ExchangeError for a room without a polygon, a door
without a host wall, a stair without treads and so on.
"""
from __future__ import annotations

import math
import uuid
from pathlib import Path

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.guid

from ..contracts import DesignElement
from . import common as C

NS = uuid.UUID("6f1d3c7e-52a1-4c43-9a55-0e7c1d2a9b01")   # fixed namespace -> deterministic GlobalIds
FIXED_TIMESTAMP = "2026-11-21T00:00:00"
GLASS_T, BAR_T = 20.0, 50.0                               # stair glass panel / wall handrail section, mm
DOOR_LEAF_T, GLAZED_DOOR_T, WINDOW_PANE_T = 45.0, 20.0, 60.0
OPENING_OVERCUT = 40.0                                    # opening depth beyond the wall thickness
MARKER_MM = 100.0                                         # nominal symbol for elements the model gives no size

FURNITURE_CLASS = {"wc": "IfcSanitaryTerminal", "washbasin": "IfcSanitaryTerminal"}


def ifc_class_for(e: DesignElement) -> str:
    """IFC class an element is written as. Single source for the exporter and the round-trip check."""
    k = e.kind
    if k == "room":
        return "IfcSpace"
    if k == "wall":
        return "IfcWall"
    if k == "slab":
        return "IfcSlab"
    if k == "door":
        return "IfcDoor"
    if k == "window":
        return "IfcWindow"
    if k == "stair":
        return "IfcStair"
    if k == "railing":
        return "IfcRailing"
    if k == "column":
        return "IfcColumn"
    if k == "beam":
        return "IfcBeam"
    if k == "furniture":
        return FURNITURE_CLASS.get(e.params.get("type", ""), "IfcFurniture")
    if k == "fixture":
        return "IfcBuildingElementProxy" if e.params.get("fixture_kind") == "wet-zone" else "IfcSanitaryTerminal"
    if k == "luminaire":
        return "IfcLightFixture"
    if k in ("plant", "garden"):
        return "IfcGeographicElement"
    if k == "context":
        return "IfcBuildingElementProxy"
    raise C.ExchangeError([f"{e.id}: no IFC class for kind {k!r}"])


def expected_class_counts(elements: list[DesignElement]) -> dict[str, int]:
    """Class counts the file must contain: one per element, plus the generated void/spatial entities."""
    out: dict[str, int] = {}
    for e in elements:
        out[ifc_class_for(e)] = out.get(ifc_class_for(e), 0) + 1
    # a stair is an IfcStair with one IfcStairFlight; every door/window cuts an IfcOpeningElement
    if any(e.kind == "stair" for e in elements):
        out["IfcStairFlight"] = sum(1 for e in elements if e.kind == "stair")
    n_open = sum(1 for e in elements if e.kind in ("door", "window"))
    if n_open:
        out["IfcOpeningElement"] = n_open
    return out


def guid(key: str) -> str:
    return ifcopenshell.guid.compress(uuid.uuid5(NS, key).hex)


class _B:
    """The builder: one instance per export."""

    def __init__(self, elements: list[DesignElement], levels: dict, design: str):
        self.els = elements
        self.by = {e.id: e for e in elements}
        self.levels = levels
        self.design = design
        self.f = f = ifcopenshell.file(schema="IFC4")
        api = ifcopenshell.api
        self.api = api
        self.proj = api.root.create_entity(f, ifc_class="IfcProject", name=f"villa-{design}")
        self.proj.GlobalId = guid("project")
        units = [api.unit.add_si_unit(f, unit_type="LENGTHUNIT", prefix="MILLI"),
                 api.unit.add_si_unit(f, unit_type="AREAUNIT"),
                 api.unit.add_si_unit(f, unit_type="VOLUMEUNIT"),
                 api.unit.add_si_unit(f, unit_type="PLANEANGLEUNIT")]
        api.unit.assign_unit(f, units=units)
        ctx = api.context.add_context(f, context_type="Model")
        self.body = api.context.add_context(f, context_type="Model", context_identifier="Body",
                                            target_view="MODEL_VIEW", parent=ctx)
        self.site = self._spatial("IfcSite", "site", f"Site {design}")
        self.bldg = self._spatial("IfcBuilding", "building", f"Villa {design}")
        api.aggregate.assign_object(f, relating_object=self.proj, products=[self.site])
        api.aggregate.assign_object(f, relating_object=self.site, products=[self.bldg])
        self.storey = {}
        for lv in C.STOREY_LEVELS:
            s = self._spatial("IfcBuildingStorey", f"storey-{lv}", f"{lv} {C.ffl(levels, lv) / 1000:+.2f}")
            s.LongName = levels[lv]["name"]
            s.Elevation = C.ffl(levels, lv)
            s.ObjectPlacement = self._lp(0, 0, C.ffl(levels, lv))
            api.aggregate.assign_object(f, relating_object=self.bldg, products=[s])
            self.storey[lv] = s
            self._pset(s, "ArchPipe_Level", {"FFL_RevitDatum_mm": C.ffl(levels, lv),
                                             "FFL_SceneDatum_mm": float(levels[lv]["ffl_scene_mm"]),
                                             "DatumNote": "Revit datum = scene datum + 1200 mm"})
        self.container = dict(self.storey, SITE=self.site)
        self.walls: dict[str, object] = {}

    # --- primitives -----------------------------------------------------------------------------------------
    def _spatial(self, cls, key, name):
        s = self.api.root.create_entity(self.f, ifc_class=cls, name=name)
        s.GlobalId = guid(key)
        if cls != "IfcBuildingStorey":
            s.ObjectPlacement = self._lp(0, 0, 0)
        return s

    def _pt(self, *xyz):
        return self.f.createIfcCartesianPoint([float(v) for v in xyz])

    def _dir(self, *xyz):
        return self.f.createIfcDirection([float(v) for v in xyz])

    def _axis(self, x, y, z, angle_deg=0.0, zdir=(0, 0, 1), xdir=None):
        if xdir is None:
            a = math.radians(angle_deg)
            xdir = (math.cos(a), math.sin(a), 0.0)
        return self.f.createIfcAxis2Placement3D(self._pt(x, y, z), self._dir(*zdir), self._dir(*xdir))

    def _lp(self, x, y, z, angle_deg=0.0, rel=None):
        return self.f.createIfcLocalPlacement(rel, self._axis(x, y, z, angle_deg))

    def _solid(self, profile, position, depth, direction=(0, 0, 1)):
        return self.f.createIfcExtrudedAreaSolid(profile, position, self._dir(*direction), float(depth))

    def rect(self, w, d, h, x=0.0, y=0.0, z=0.0, angle_deg=0.0):
        prof = self.f.createIfcRectangleProfileDef("AREA", None, self.f.createIfcAxis2Placement2D(self._pt(0, 0), None),
                                                   float(w), float(d))
        return self._solid(prof, self._axis(x, y, z, angle_deg), h)

    def disc(self, dia, h, x=0.0, y=0.0, z=0.0):
        prof = self.f.createIfcCircleProfileDef("AREA", None, self.f.createIfcAxis2Placement2D(self._pt(0, 0), None),
                                                float(dia) / 2)
        return self._solid(prof, self._axis(x, y, z), h)

    def prism(self, pts, h, z=0.0):
        """Polygon (x, y) extruded upwards from height z. Closed polyline profile (checked by the round trip)."""
        pl = [self._pt(x, y) for x, y in list(pts) + [pts[0]]]
        prof = self.f.createIfcArbitraryClosedProfileDef("AREA", None, self.f.createIfcPolyline(pl))
        return self._solid(prof, self._axis(0, 0, z), h)

    def vpanel(self, uv, thickness, base_xy, udir_xy):
        """Polygon in a vertical plane (u along udir_xy from base_xy, v = world z) extruded `thickness`, centred on it."""
        ux, uy = udir_xy
        n = (uy, -ux)
        pl = [self._pt(u, v) for u, v in list(uv) + [uv[0]]]
        prof = self.f.createIfcArbitraryClosedProfileDef("AREA", None, self.f.createIfcPolyline(pl))
        pos = self.f.createIfcAxis2Placement3D(
            self._pt(base_xy[0] - n[0] * thickness / 2, base_xy[1] - n[1] * thickness / 2, 0.0),
            self._dir(n[0], n[1], 0.0), self._dir(ux, uy, 0.0))
        return self._solid(prof, pos, thickness)

    def shape(self, solids):
        rep = self.f.createIfcShapeRepresentation(self.body, "Body", "SweptSolid", list(solids))
        return self.f.createIfcProductDefinitionShape(None, None, [rep])

    # --- entity creation ------------------------------------------------------------------------------------
    def new(self, e, cls=None, name=None, key=None):
        el = self.api.root.create_entity(self.f, ifc_class=cls or ifc_class_for(e), name=name or e.id)
        el.GlobalId = guid(key or e.id)
        if hasattr(el, "Tag") and el.Tag is None:
            el.Tag = e.id
        return el

    def _pset(self, el, name, props):
        props = {k: v for k, v in props.items() if v not in (None, "")}
        if not props:
            return
        clean = {}
        for k, v in props.items():
            if isinstance(v, (list, tuple, dict)):
                v = str(v)
            if isinstance(v, str) and len(v) > 250:
                v = self.f.createIfcText(v)
            clean[k] = v
        ps = self.api.pset.add_pset(self.f, product=el, name=name)
        self.api.pset.edit_pset(self.f, pset=ps, properties=clean)

    def _qto(self, el, name, props):
        q = self.api.pset.add_qto(self.f, product=el, name=name)
        self.api.pset.edit_qto(self.f, qto=q, properties={k: float(v) for k, v in props.items() if v is not None})

    def contain(self, el, e, level=None):
        lv = level or e.level
        cont = self.container.get(lv)
        if cont is None:
            raise C.ExchangeError([f"{e.id}: level {lv!r} has no IFC container (only {sorted(self.container)})"])
        self.api.spatial.assign_container(self.f, products=[el], relating_structure=cont)

    def provenance(self, el, e, extra=None):
        notes = "; ".join(f"{k}: {e.params[k]}" for k in ("note", "basis", "why", "what", "name") if e.params.get(k))
        self._pset(el, "ArchPipe_Source", dict(
            SourceId=e.id, SourceKind=e.kind, Level=e.level, Room=e.room or None, Host=e.host or None,
            ProductId=e.product_id or None, FinishCodes=", ".join(e.finish_codes) or None, Notes=notes or None,
            Datum="Revit datum: z = scene z + 1200 mm", **(extra or {})))

    def z(self, e, dz=None):
        """World z (Revit datum) of an element whose placement.z is level-relative."""
        return C.ffl(self.levels, e.level) + (e.placement[2] if dz is None else dz)

    # --- kinds ----------------------------------------------------------------------------------------------
    def wall(self, e):
        p = e.params
        (x0, y0), (x1, y1) = C.wall_line(e)
        L, t, h = C.wall_length(e), float(p["thickness_mm"]), float(p["height_mm"])
        el = self.new(e)
        ang = C.wall_angle_deg(e)
        base = C.ffl(self.levels, e.level) + e.placement[2]
        el.ObjectPlacement = self._lp((x0 + x1) / 2, (y0 + y1) / 2, base, ang)
        el.Representation = self.shape([self.rect(L, t, h)])
        self.contain(el, e)
        ext = p.get("wall_kind") == "ext"
        self._pset(el, "Pset_WallCommon", {"IsExternal": ext})
        self._qto(el, "Qto_WallBaseQuantities", {"Length": L, "Width": t, "Height": h})
        self.provenance(el, e, {"WallKind": p.get("wall_kind")})
        self.walls[e.id] = (el, e, L, t, base, ang)

    def opening(self, e):
        el_w, w, L, t, wbase, ang = self.walls[e.host]
        p = e.params
        W, H = float(p["width_mm"]), float(p["height_mm"])
        along, _ = C.project_on_wall(w, e.placement[:2])
        sill = float(p.get("sill_mm") or 0.0) if e.kind == "window" else 0.0
        rel = el_w.ObjectPlacement
        lx = along - L / 2
        op = self.new(e, cls="IfcOpeningElement", name=f"{e.id}-void", key=f"{e.id}-void")
        op.ObjectPlacement = self._lp(lx, 0, sill, 0, rel=rel)
        op.Representation = self.shape([self.rect(W, t + OPENING_OVERCUT, H)])
        self.f.createIfcRelVoidsElement(guid(f"{e.id}-rv"), None, None, None, el_w, op)
        glazed = bool(p.get("garden")) or e.kind == "window"
        cls = "IfcDoor" if e.kind == "door" else "IfcWindow"
        fill = self.new(e, cls=cls)
        fill.ObjectPlacement = self._lp(lx, 0, sill, 0, rel=rel)
        leaf = WINDOW_PANE_T if e.kind == "window" else (GLAZED_DOOR_T if glazed else DOOR_LEAF_T)
        fill.Representation = self.shape([self.rect(W, leaf, H)])
        fill.OverallWidth, fill.OverallHeight = W, H
        self.f.createIfcRelFillsElement(guid(f"{e.id}-rf"), None, None, None, op, fill)
        self.contain(fill, e)
        ext = self.by[e.host].params.get("wall_kind") == "ext"
        self._pset(fill, f"Pset_{'Door' if e.kind == 'door' else 'Window'}Common", {"IsExternal": ext})
        self.provenance(fill, e, {k: p.get(k) for k in ("operation", "swing_into", "leaf_count", "sill_mm",
                                                         "structural_opening_mm", "clear_width_mm", "full_height")})

    def room(self, e):
        p = e.params
        poly = [(float(x), float(y)) for x, y in p["polygon_mm"]]
        el = self.new(e, name=e.id[5:] if e.id.startswith("room-") else e.id)
        el.LongName = p.get("name") or None
        el.ObjectPlacement = self._lp(0, 0, C.ffl(self.levels, e.level))
        h = float(p["clear_height_mm"])
        el.Representation = self.shape([self.prism(poly, h)])
        self.api.aggregate.assign_object(self.f, relating_object=self.storey[e.level], products=[el])
        gross = p.get("gross_area_m2") or p.get("area_m2")
        net = p.get("net_area_m2")
        self._qto(el, "Qto_SpaceBaseQuantities", {"GrossFloorArea": gross, "NetFloorArea": net,
                                                  "Height": h, "FinishCeilingHeight": h})
        self._pset(el, "Pset_SpaceCommon", {"Reference": e.id, "OccupancyType": p.get("occupancy"),
                                            "IsExternal": False})
        self.provenance(el, e, {"NetAreaBasis": p.get("net_area_basis"), "ClearAreaM2": p.get("clear_area_m2"),
                                "OpenTo": ", ".join(p.get("open_to") or []) or None,
                                "PolygonAreaM2": round(C.polygon_area_mm2(poly) / 1e6, 4),
                                "CeilingSource": p.get("ceiling_source")})

    def slab(self, e):
        p = e.params
        el = self.new(e)
        role = p.get("role", "")
        el.PredefinedType = "ROOF" if "roof" in role else ("FLOOR" if "deck" in role or "terrace" in role else "NOTDEFINED")
        el.ObjectType = role or None
        if p.get("profile_xz_mm"):
            top = [(float(x), float(z) + C.DATUM_SHIFT_MM) for x, z in p["profile_xz_mm"]]
            t = float(p["thickness_mm"])
            uv = top + [(x, z - t) for x, z in reversed(top)]
            ty = e.size[1]
            el.ObjectPlacement = self._lp(0, 0, 0)
            el.Representation = self.shape([self.vpanel(uv, ty, (0.0, e.placement[1]), (1.0, 0.0))])
        elif p.get("polygon_mm"):
            poly = [(float(x), float(y)) for x, y in p["polygon_mm"]]
            t = float(p.get("thickness_mm") or e.size[2])
            el.ObjectPlacement = self._lp(0, 0, self.z(e))
            el.Representation = self.shape([self.prism(poly, t)])
        else:
            el.ObjectPlacement = self._lp(e.placement[0], e.placement[1], self.z(e), e.rotation_deg)
            el.Representation = self.shape([self.rect(*e.size)])
        self.contain(el, e)
        self.provenance(el, e, {"Role": role, "SlopePct": p.get("slope_pct"), "GuardPresent": p.get("guard_present")})

    def box_element(self, e, cls_extra=None):
        w, d, h = e.size
        el = self.new(e)
        el.ObjectPlacement = self._lp(e.placement[0], e.placement[1], self.z(e), e.rotation_deg)
        el.Representation = self.shape([self.rect(w, d, h)])
        self.contain(el, e)
        self.provenance(el, e)
        return el

    def column(self, e):
        self._pset(self.box_element(e), "Pset_ColumnCommon", {"IsExternal": False})

    def beam(self, e):
        self._pset(self.box_element(e), "Pset_BeamCommon", {"IsExternal": False})

    def stair(self, e):
        p = e.params
        st = self.new(e)
        st.ObjectPlacement = self._lp(e.placement[0], e.placement[1], 0)
        st.PredefinedType = "STRAIGHT_RUN_STAIR"
        ox, oy = e.placement[0], e.placement[1]
        solids = []
        for x0, y0, z0, x1, y1, z1 in p["tread_boxes_mm"]:
            solids.append(self.rect(x1 - x0, y1 - y0, z1 - z0, (x0 + x1) / 2 - ox, (y0 + y1) / 2 - oy,
                                    float(z0) + C.DATUM_SHIFT_MM))
        fl = self.new(e, cls="IfcStairFlight", name=f"{e.id}-flight", key=f"{e.id}-flight")
        fl.ObjectPlacement = self._lp(ox, oy, 0)
        fl.Representation = self.shape(solids)
        fl.NumberOfRisers, fl.NumberOfTreads = int(p["risers"]), int(p["treads"])
        fl.RiserHeight, fl.TreadLength = float(p["riser_mm"]), float(p["tread_mm"])
        fl.PredefinedType = "STRAIGHT"
        self.api.aggregate.assign_object(self.f, relating_object=st, products=[fl])
        self.contain(st, e)
        self._pset(st, "Pset_StairCommon", {"NumberOfRiser": int(p["risers"]), "NumberOfTreads": int(p["treads"]),
                                            "RiserHeight": float(p["riser_mm"]), "TreadLength": float(p["tread_mm"]),
                                            "RequiredHeadroom": None, "IsExternal": False})
        self._pset(st, "ArchPipe_Stair", {"WidthMm": float(p["width_mm"]), "RiseMm": float(p.get("rise_mm") or 0),
                                          "RunMm": p.get("run_mm"), "TopLandingRoom": p.get("top_landing_room"),
                                          "Risers": "open: tread plates only, as authored (no riser plates, no stringer)"})
        self.provenance(st, e)

    def railing(self, e):
        p = e.params
        H = float(p["guard_height_mm"])
        el = self.new(e)
        glazed = bool(p.get("glazed", True))
        prof = p.get("profile_mm")
        ox, oy = e.placement[0], e.placement[1]
        if prof and len(prof[0]) == 3:                                   # stair guard: nosing polyline in scene z
            pts = [(float(x), float(y), float(z) + C.DATUM_SHIFT_MM) for x, y, z in prof]
            dx, dy = pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]
            Ln = math.hypot(dx, dy)
            if Ln < 1e-6:
                raise C.ExchangeError([f"{e.id}: stair guard polyline has no plan length"])
            u = (dx / Ln, dy / Ln)
            n = (u[1], -u[0])
            for x, y, _ in pts:
                if abs((x - pts[0][0]) * n[0] + (y - pts[0][1]) * n[1]) > 1.0:
                    raise C.ExchangeError([f"{e.id}: stair guard polyline is not straight in plan"])
            s = [((x - pts[0][0]) * u[0] + (y - pts[0][1]) * u[1], z) for x, y, z in pts]
            if glazed:
                uv = [(a, z) for a, z in s] + [(a, z + H) for a, z in reversed(s)]
                thick = GLASS_T
            else:
                uv = [(a, z + H - BAR_T) for a, z in s] + [(a, z + H) for a, z in reversed(s)]
                thick = BAR_T
            el.ObjectPlacement = self._lp(ox, oy, 0)
            el.Representation = self.shape([self.vpanel(uv, thick, (pts[0][0] - ox, pts[0][1] - oy), u)])
        elif prof:                                                       # ramp-edge guard: closed XZ polygon (scene z)
            uv = [(float(x), float(z) + C.DATUM_SHIFT_MM) for x, z in prof]
            ty = e.size[1] or 50.0
            el.ObjectPlacement = self._lp(ox, oy, 0)
            el.Representation = self.shape([self.vpanel(uv, ty, (-ox, 0.0), (1.0, 0.0))])
        else:                                                            # straight panel from its size
            el.ObjectPlacement = self._lp(ox, oy, self.z(e), e.rotation_deg)
            el.Representation = self.shape([self.rect(e.size[0], e.size[1] or GLASS_T, H)])
        el.PredefinedType = "HANDRAIL" if (p.get("side") == "wall") else "GUARDRAIL"
        self.contain(el, e)
        self._pset(el, "Pset_RailingCommon", {"Height": H, "IsExternal": e.level == "GF" or "edge" in e.id})
        self._pset(el, "ArchPipe_Railing", {"GuardHeightMm": H, "Material": p.get("material"),
                                            "InfillGlass": glazed if p.get("glazed") is not None else None,
                                            "MeasuredFrom": p.get("measured_from"),
                                            "InRevitSpec": p.get("in_revit_spec"),
                                            "UnmodelledReturnEdgesMm": (p.get("edge_lengths_mm") or [None, None])[1]
                                            if p.get("edge_lengths_mm") else None})
        self.provenance(el, e)

    def furniture(self, e):
        el = self.new(e)
        w, d, h = e.size
        zero = not all(v > 0 for v in e.size)
        if zero:
            w = d = h = MARKER_MM
        el.ObjectPlacement = self._lp(e.placement[0], e.placement[1], self.z(e) - (h / 2 if zero else 0), e.rotation_deg)
        el.Representation = self.shape([self.rect(w, d, h)])
        el.ObjectType = e.params.get("type") or None
        self.contain(el, e)
        self._pset(el, "ArchPipe_Furniture", {"Type": e.params.get("type"),
                                              "GeometryBasis": "nominal 100 mm marker: model gives no size" if zero
                                              else "bounding box from the design model"})
        self.provenance(el, e)

    def fixture(self, e):
        el = self.new(e)
        w, d, h = e.size
        zero = not all(v > 0 for v in e.size)
        if zero:                                                         # a fixture with one zero dim is a plane/line
            w, d, h = (v if v > 0 else MARKER_MM for v in e.size)
        el.ObjectPlacement = self._lp(e.placement[0], e.placement[1], self.z(e) - (h / 2 if zero else 0), e.rotation_deg)
        el.Representation = self.shape([self.rect(w, d, h)])
        el.ObjectType = e.params.get("fixture_kind")
        self.contain(el, e)
        self._pset(el, "ArchPipe_Fixture", {"Kind": e.params.get("fixture_kind"), "Over": e.params.get("over"),
                                            "GeometryBasis": "nominal marker on zero-size dimensions" if zero else None})
        self.provenance(el, e)

    def luminaire(self, e):
        p = e.params
        ph = p.get("photometry") or {}
        el = self.new(e)
        ln = float(p.get("length_mm") or 0.0)
        along = p.get("along") or [1.0, 0.0, 0.0]
        z = self.z(e)
        if all(v > 0 for v in e.size):
            w, d, h = e.size
            el.ObjectPlacement = self._lp(e.placement[0], e.placement[1], z - h / 2, e.rotation_deg)
            sol = self.rect(w, d, h)
            basis = "bounding box from the design model"
        elif ln > 0:
            el.ObjectPlacement = self._lp(e.placement[0], e.placement[1], z - 20, math.degrees(math.atan2(along[1], along[0])))
            sol = self.rect(ln, 40.0, 40.0)
            basis = "linear symbol of the model's length_mm (section 40 x 40 nominal)"
        else:
            el.ObjectPlacement = self._lp(e.placement[0], e.placement[1], z - 15)
            sol = self.disc(MARKER_MM, 30.0)
            basis = "nominal 100 mm disc symbol at the emitter height, not product geometry"
        el.Representation = self.shape([sol])
        el.ObjectType = p.get("fixture_kind")
        self.contain(el, e)
        self._pset(el, "Pset_ManufacturerTypeInformation", {"Manufacturer": ph.get("manufacturer"),
                                                            "ModelReference": ph.get("code")})
        self._pset(el, "Pset_LightFixtureTypeCommon", {"TotalWattage": p.get("watts"), "NumberOfSources": 1})
        self._pset(el, "ArchPipe_Luminaire", dict(
            Manufacturer=ph.get("manufacturer"), ProductCode=ph.get("code"), LuminousFluxLm=p.get("flux_lm"),
            PowerW=p.get("watts"), CCT_K=p.get("cct_k"), CRI=p.get("cri"), BeamAngleDeg=p.get("beam_deg"),
            IESFile=ph.get("ies"), PhotometrySubstitute=ph.get("substitute"), PhotometryGeneric=ph.get("generic"),
            FixtureKind=p.get("fixture_kind"), Layer=p.get("layer"), Mount=p.get("mount"),
            EmitterHeightAboveFFL_mm=e.placement[2], IlluminanceCard=p.get("illuminance_card"), GeometryBasis=basis))
        self.provenance(el, e)

    def plant(self, e):
        p = e.params
        el = self.new(e)
        dia = max(e.size[0], 100.0)
        el.ObjectPlacement = self._lp(e.placement[0], e.placement[1], self.z(e))
        el.Representation = self.shape([self.disc(dia, 20.0)])
        el.ObjectType = "plant"
        self.contain(el, e)
        self._pset(el, "ArchPipe_Plant", {"Species": p.get("species"), "Bed": p.get("bed"), "Layer": p.get("layer"),
                                          "SpreadM": p.get("spread_m"), "HeightM": p.get("height_m"),
                                          "GeometryBasis": "canopy-spread footprint disc, 20 mm thick; plant height is not in the model"})
        self.provenance(el, e)

    def garden(self, e):
        poly = [(float(x), float(y)) for x, y in e.params["polygon_mm"]]
        el = self.new(e)
        el.ObjectPlacement = self._lp(0, 0, self.z(e))
        el.Representation = self.shape([self.prism(poly, 20.0)])
        el.ObjectType = e.params.get("role") or "garden"
        self.contain(el, e)
        self._pset(el, "ArchPipe_Garden", {"Role": e.params.get("role"), "AreaM2": e.params.get("area_m2"),
                                           "Sunken": e.params.get("sunken"), "GuardPresent": e.params.get("guard_present"),
                                           "GeometryBasis": "plan footprint, 20 mm thick marker"})
        self.provenance(el, e)

    def context(self, e):
        p = e.params
        w, d, h = e.size
        z0 = C.scene_to_revit(p["z0_scene_mm"]) if p.get("z0_scene_mm") is not None else self.z(e, e.placement[2])
        el = self.new(e)
        el.ObjectPlacement = self._lp(e.placement[0], e.placement[1], z0, e.rotation_deg)
        el.Representation = self.shape([self.rect(w, d, h)])
        el.ObjectType = f"context:{p.get('what', '')}"
        el.Description = "NOT OURS: neighbouring/context volume for sun and sight-line studies, not a design element"
        self.contain(el, e, level="SITE")
        self._pset(el, "ArchPipe_Context", {"NotOurs": True, "What": p.get("what"), "Category": p.get("category"),
                                            "Note": p.get("note")})
        self.provenance(el, e)

    def build(self):
        order = {"wall": 0, "room": 1, "slab": 2, "column": 2, "beam": 2, "stair": 3, "railing": 3, "door": 4,
                 "window": 4}
        for e in sorted(self.els, key=lambda x: order.get(x.kind, 9)):
            k = e.kind
            if k in ("door", "window"):
                self.opening(e)
            elif k in ("plant", "garden", "context", "room", "wall", "slab", "column", "beam", "stair", "railing",
                       "furniture", "fixture", "luminaire"):
                getattr(self, k)(e)
            else:
                raise C.ExchangeError([f"{e.id}: kind {k!r} is not exportable"])
        return self.f


def build_ifc(elements: list[DesignElement], levels: dict | None = None, design: str = "D1"):
    """Return an in-memory ifcopenshell file. Raises ExchangeError (before building) on an unexportable model."""
    levels = levels or C.DEFAULT_LEVELS
    C.require_clean(elements, levels)
    for lv in C.STOREY_LEVELS:
        if lv not in levels:
            raise C.ExchangeError([f"level table lacks {lv}"])
    f = _B(elements, levels, design).build()
    f.wrapped_data.header.file_name.time_stamp = FIXED_TIMESTAMP
    f.wrapped_data.header.file_name.author = ("archpipe",)
    f.wrapped_data.header.file_name.organization = ("arch-pipeline",)
    f.wrapped_data.header.file_name.originating_system = "archpipe.exchange"
    return f


def write_ifc(elements: list[DesignElement], path: Path | str, levels: dict | None = None, design: str = "D1") -> Path:
    f = build_ifc(elements, levels, design)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    f.write(str(path))
    return path
