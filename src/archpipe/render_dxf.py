"""L1 renderer: L0 spec -> DXF. No Autodesk dependency, runs anywhere.

Walls are built as polygons and unioned before drawing, which is what
makes junctions clean up by themselves. Drawing each wall as a pair of
offset lines instead would leave the classic crossing-lines mess at
every corner and T-junction.

Openings are subtracted from that union, so the reveal is a real hole
in the wall poche rather than a white rectangle drawn on top.
"""
from __future__ import annotations

import math
from pathlib import Path

import ezdxf
from ezdxf.enums import TextEntityAlignment
from shapely.geometry import Polygon
from shapely.ops import unary_union

from . import layers as std
from .model import Opening, Project, Wall

# How far an opening cut extends past each wall face, so the boolean
# subtraction always breaks through rather than leaving a hairline.
CUT_MARGIN = 5.0

# Furniture layers. Defined here rather than in layers.py only because that
# file was being edited concurrently when these were added; fold them into
# layers.LAYERS when convenient, so the standard stays in one place.
FURNITURE_LAYERS = (
    std.LayerDef("A-FURN",      std.LGREY, 18, description="Furniture footprints"),
    std.LayerDef("A-FURN-CLNC", std.LGREY, 9, "ARCH-DASHED",
                 description="Clearance each piece requires"),
    std.LayerDef("A-FURN-IDEN", std.LGREY, 9, description="Furniture tags"),
)


def _ensure_furniture_layers(doc) -> None:
    for ld in FURNITURE_LAYERS:
        layer = (doc.layers.get(ld.name) if ld.name in doc.layers
                 else doc.layers.add(ld.name))
        layer.color = ld.color
        layer.dxf.lineweight = ld.lineweight
        layer.dxf.linetype = ld.linetype
        layer.description = ld.description


def _wall_polygon(w: Wall, thickness: float) -> Polygon:
    left, right = w.face_offsets(thickness)
    L = w.length
    return Polygon([
        w.point_at(0, left), w.point_at(L, left),
        w.point_at(L, right), w.point_at(0, right),
    ])


def _opening_cut(w: Wall, thickness: float, o: Opening) -> Polygon:
    left, right = w.face_offsets(thickness)
    a, b = o.at - o.width / 2, o.at + o.width / 2
    return Polygon([
        w.point_at(a, left + CUT_MARGIN), w.point_at(b, left + CUT_MARGIN),
        w.point_at(b, right - CUT_MARGIN), w.point_at(a, right - CUT_MARGIN),
    ])


def _polys(geom):
    """Normalise a shapely result to a list of Polygons."""
    if geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    return [g for g in geom.geoms if g.geom_type == "Polygon"]


def _draw_walls(msp, p: Project, level: str) -> None:
    walls = [w for w in p.walls if w.level == level]
    if not walls:
        return

    solid = unary_union([_wall_polygon(w, p.wall_type(w.type).thickness) for w in walls])
    cuts = [
        _opening_cut(w, p.wall_type(w.type).thickness, o)
        for w in walls
        for o in p.openings_of(w.id)
    ]
    if cuts:
        solid = solid.difference(unary_union(cuts))

    for poly in _polys(solid):
        rings = [list(poly.exterior.coords)] + [list(r.coords) for r in poly.interiors]
        for ring in rings:
            msp.add_lwpolyline(ring[:-1], close=True, dxfattribs={"layer": "A-WALL"})

        hatch = msp.add_hatch(color=std.DGREY, dxfattribs={"layer": "A-WALL-PATT"})
        hatch.set_pattern_fill("ANSI31", scale=40.0)
        hatch.paths.add_polyline_path(list(poly.exterior.coords)[:-1], is_closed=True,
                                      flags=ezdxf.const.BOUNDARY_PATH_EXTERNAL)
        for ring in poly.interiors:
            hatch.paths.add_polyline_path(list(ring.coords)[:-1], is_closed=True,
                                          flags=ezdxf.const.BOUNDARY_PATH_OUTERMOST)


def _draw_openings(msp, p: Project, level: str) -> None:
    for w in (w for w in p.walls if w.level == level):
        t = p.wall_type(w.type).thickness
        left, right = w.face_offsets(t)
        dx, dy = w.direction
        base_ang = math.degrees(math.atan2(dy, dx))

        for o in p.openings_of(w.id):
            a, b = o.at - o.width / 2, o.at + o.width / 2
            if o.kind == "window":
                # Frame lines on both faces plus a centre glazing line.
                for off in (left, right):
                    msp.add_line(w.point_at(a, off), w.point_at(b, off),
                                 dxfattribs={"layer": "A-GLAZ"})
                msp.add_line(w.point_at(a, 0), w.point_at(b, 0),
                             dxfattribs={"layer": "A-GLAZ"})
                continue

            # Door: leaf drawn open at 90 degrees, with its swing arc.
            hinge_at, start_ang = (a, base_ang) if o.swing == "left" else (b, base_ang + 90)
            hinge = w.point_at(hinge_at, 0)
            leaf_ang = math.radians(base_ang + 90)
            leaf_end = (hinge[0] + o.width * math.cos(leaf_ang),
                        hinge[1] + o.width * math.sin(leaf_ang))
            msp.add_line(hinge, leaf_end, dxfattribs={"layer": "A-DOOR"})
            msp.add_arc(center=hinge, radius=o.width,
                        start_angle=start_ang, end_angle=start_ang + 90,
                        dxfattribs={"layer": "A-DOOR"})


def _draw_rooms(msp, p: Project, level: str, scale: float) -> None:
    h_name = std.model_text_height("room_name", scale)
    h_area = std.model_text_height("room_area", scale)

    for r in (r for r in p.rooms if r.level == level):
        msp.add_lwpolyline(r.boundary, close=True, dxfattribs={"layer": "A-ROOM-BDRY"})
        cx, cy = r.centroid
        msp.add_text(
            r.name.upper(), height=h_name,
            dxfattribs={"layer": "A-ROOM-IDEN", "style": std.TEXT_STYLE},
        ).set_placement((cx, cy + h_name * 0.8), align=TextEntityAlignment.MIDDLE_CENTER)
        msp.add_text(
            f"{r.area_m2:.1f} m2", height=h_area,
            dxfattribs={"layer": "A-ROOM-IDEN", "style": std.TEXT_STYLE},
        ).set_placement((cx, cy - h_area * 0.8), align=TextEntityAlignment.MIDDLE_CENTER)


def _draw_furniture(msp, p: Project, level: str, scale: float) -> None:
    """Footprints, plus the clearance each piece needs shown dashed.

    Drawing the clearance is the point: a plan that looks fine at
    footprint level often has pieces that cannot actually be used, and
    the dashed zones make that visible without reading the rule report.
    """
    from . import catalogue as cat

    h = std.model_text_height("room_area", scale) * 0.8
    for f in (f for f in p.furniture if f.level == level):
        t = cat.CATALOGUE.get(f.type)
        w, d = f.size if f.size else (t.width, t.depth)

        msp.add_lwpolyline(f.corners(w, d), close=True,
                           dxfattribs={"layer": "A-FURN"})
        if t:
            zones = dict(t.clearance)
            if t.clearance_any:
                sides, amount = t.clearance_any
                for s in sides:
                    zones.setdefault(s, amount)
            for side, amount in zones.items():
                rect = f.clearance_rect(side, w, d, amount)
                if rect:
                    msp.add_lwpolyline(rect, close=True,
                                       dxfattribs={"layer": "A-FURN-CLNC"})
        msp.add_text(
            f.id, height=h,
            dxfattribs={"layer": "A-FURN-IDEN", "style": std.TEXT_STYLE},
        ).set_placement(f.at, align=TextEntityAlignment.MIDDLE_CENTER)


def _draw_overall_dims(msp, p: Project, level: str, scale: float) -> None:
    """Two overall dimensions on the model bounding box: width and height."""
    walls = [w for w in p.walls if w.level == level]
    if not walls:
        return
    solid = unary_union([_wall_polygon(w, p.wall_type(w.type).thickness) for w in walls])
    minx, miny, maxx, maxy = solid.bounds
    off = std.model_text_height("dim", scale) * 4

    attribs = {"layer": "A-ANNO-DIMS"}
    msp.add_linear_dim(
        base=(minx, miny - off), p1=(minx, miny), p2=(maxx, miny),
        dimstyle=std.DIM_STYLE, dxfattribs=attribs,
    ).render()
    msp.add_linear_dim(
        base=(minx - off, miny), p1=(minx, miny), p2=(minx, maxy),
        angle=90, dimstyle=std.DIM_STYLE, dxfattribs=attribs,
    ).render()


def render(p: Project, path: str | Path, level: str | None = None,
           scale: float = 50.0) -> Path:
    """Render one level of `p` to a DXF at `path`. Returns the path written."""
    level = level or (p.levels[0].id if p.levels else "")

    doc = ezdxf.new("R2018", setup=True)
    doc.header["$INSUNITS"] = 4      # millimetres
    doc.header["$MEASUREMENT"] = 1   # metric
    doc.header["$LUNITS"] = 2        # decimal
    doc.header["$LUPREC"] = 0        # whole mm
    # Linetypes scale with the MODEL, not the sheet. Left at the default 1,
    # a 300 mm dash pattern is read as 300 mm of paper through a viewport,
    # so every dashed line plots solid on the 1:50 sheet.
    doc.header["$PSLTSCALE"] = 0
    std.apply(doc, scale)
    _ensure_furniture_layers(doc)

    msp = doc.modelspace()
    _draw_walls(msp, p, level)
    _draw_openings(msp, p, level)
    _draw_furniture(msp, p, level, scale)
    _draw_rooms(msp, p, level, scale)
    _draw_overall_dims(msp, p, level, scale)

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(out)
    return out
