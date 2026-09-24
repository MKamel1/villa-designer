"""Manufacturer-neutral detailed furniture geometry for the bedroom scene.

`build_furniture(item)` turns a placement record into a list of closed,
triangulated meshes ("components") in world millimetres. This is authoring
geometry, not a catalogue of sourced products: no brand names, no imported
mesh data.

COORDINATE CONVENTION (load-bearing, verified against the real bedroom item):

    Each piece is modelled in a LOCAL frame centred on `item['at']`, with
    local +y as the piece's front and local -y as its back (a bed's
    headboard sits at local -y). x runs across the piece's declared
    `width`, y across its `depth`, and z from the floor (0) to `height`.

    A component's final world vertices are its local vertices rotated
    ANTICLOCKWISE by `item['rotation']` degrees about the local origin,
    THEN translated by `item['at']` -- rotate once, translate once, in
    that order, matching how the caller re-extracts and renders the
    placed geometry.

    world = R(rotation) @ local + at,   R = [[cos,-sin],[sin,cos]]

    This was checked against the two facts the task states about the real
    room: a bed at at=(2250,2600), size=(1600,2000), rotation=180 has its
    headboard (local y=-1000) reach world y=3600 -- and a wardrobe at
    rotation=270 has its local +y front face world +x ("east"). Both only
    hold with this exact rotation direction and this transform order.

Every triangle winds so its normal points away from the solid it bounds
("outward winding"): computed once by hand for a box and reused, via
verified index patterns, for every extrusion, loft and lat/long sphere in
this file. Each component is independently closed and manifold; separate
components (e.g. mattress and frame) are not welded to each other, so it
is fine -- and expected -- for two components to touch without sharing
vertices.
"""
from __future__ import annotations

import math

DETAIL_V1 = "warm-contemporary-v1"

MATERIAL_OAK = {"name": "archpipe oak", "rgb": [151, 107, 63]}
MATERIAL_LINEN = {"name": "archpipe warm linen", "rgb": [214, 196, 168]}
MATERIAL_BEDDING = {"name": "archpipe ivory bedding", "rgb": [245, 240, 227]}
MATERIAL_THROW = {"name": "archpipe muted taupe throw", "rgb": [143, 127, 113]}
MATERIAL_METAL = {"name": "archpipe dark metal", "rgb": [45, 45, 48]}


class FurnitureError(ValueError):
    pass


# --------------------------------------------------------------------- mesh
# primitives. Every function below returns (vertices, triangles) in LOCAL
# coordinates, with outward-facing winding, verified by hand once and then
# reused structurally (never re-derived per shape).

def _box(x0, x1, y0, y1, z0, z1):
    v = [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]
    t = [
        (0, 2, 1), (0, 3, 2),   # bottom, -z
        (4, 5, 6), (4, 6, 7),   # top, +z
        (0, 1, 5), (0, 5, 4),   # -y
        (1, 2, 6), (1, 6, 5),   # +x
        (2, 3, 7), (2, 7, 6),   # +y
        (3, 0, 4), (3, 4, 7),   # -x
    ]
    return v, t


def _rounded_rect_polygon(x0, x1, y0, y1, radius, seg=4):
    r = max(0.0, min(radius, (x1 - x0) / 2.0, (y1 - y0) / 2.0))
    if r <= 1e-9:
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    corners = [
        (x1 - r, y0 + r, -90.0, 0.0),
        (x1 - r, y1 - r, 0.0, 90.0),
        (x0 + r, y1 - r, 90.0, 180.0),
        (x0 + r, y0 + r, 180.0, 270.0),
    ]
    pts = []
    for cx, cy, a0, a1 in corners:
        for i in range(seg + 1):
            a = math.radians(a0 + (a1 - a0) * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _extrude_polygon(poly, z0, z1):
    """Closed prism over a convex, CCW (anticlockwise) polygon in the xy
    plane, extruded from z0 to z1. z1 must be > z0 for outward winding."""
    n = len(poly)
    v = [(x, y, z0) for x, y in poly] + [(x, y, z1) for x, y in poly]
    t = []
    for i in range(1, n - 1):
        t.append((0, i + 1, i))                       # bottom cap, -z
    for i in range(1, n - 1):
        t.append((n, n + i, n + i + 1))                # top cap, +z
    for i in range(n):
        j = (i + 1) % n
        b0, b1, t0, t1 = i, j, n + i, n + j
        t.append((b0, b1, t1))
        t.append((b0, t1, t0))
    return v, t


def _prism(x0, x1, y0, y1, z0, z1, radius=0.0, seg=4):
    poly = _rounded_rect_polygon(x0, x1, y0, y1, radius, seg)
    return _extrude_polygon(poly, z0, z1)


def _cylinder(cx, cy, z0, z1, radius, seg=16):
    poly = [(cx + radius * math.cos(2 * math.pi * i / seg),
             cy + radius * math.sin(2 * math.pi * i / seg)) for i in range(seg)]
    return _extrude_polygon(poly, z0, z1)


def _loft_rings(rings, seg):
    """Closed loft through rounded-rect rings (x0, x1, y0, y1, z, radius),
    bottom to top. Every ring uses the same `seg`, so every ring polygon
    has the same point count and can be stitched to its neighbour with the
    same verified side-wall pattern as `_extrude_polygon`."""
    polys = [_rounded_rect_polygon(x0, x1, y0, y1, radius, seg)
             for x0, x1, y0, y1, _z, radius in rings]
    n = len(polys[0])
    verts = []
    for poly, ring in zip(polys, rings):
        z = ring[4]
        verts.extend((x, y, z) for x, y in poly)
    tris = []
    for i in range(1, n - 1):
        tris.append((0, i + 1, i))
    top = (len(rings) - 1) * n
    for i in range(1, n - 1):
        tris.append((top, top + i, top + i + 1))
    for r in range(len(rings) - 1):
        base, nxt = r * n, (r + 1) * n
        for i in range(n):
            j = (i + 1) % n
            b0, b1, t0, t1 = base + i, base + j, nxt + i, nxt + j
            tris.append((b0, b1, t1))
            tris.append((b0, t1, t0))
    return verts, tris


def _beveled_box(x0, x1, y0, y1, z0, z1, radius, bevel, seg=4):
    """A box with its top and bottom edges softened by a short inward
    taper -- reads as a cushioned slab (mattress, tabletop) rather than a
    sharp-edged block, while the middle rings still touch x0/x1/y0/y1
    exactly, so the local bounding box is unaffected."""
    bevel = max(0.0, min(bevel, (z1 - z0) / 2.0 - 1e-6,
                          (x1 - x0) / 2.0 - 1e-3, (y1 - y0) / 2.0 - 1e-3))
    r_in = max(radius - bevel, 0.5)
    rings = [
        (x0 + bevel, x1 - bevel, y0 + bevel, y1 - bevel, z0, r_in),
        (x0, x1, y0, y1, z0 + bevel, radius),
        (x0, x1, y0, y1, z1 - bevel, radius),
        (x0 + bevel, x1 - bevel, y0 + bevel, y1 - bevel, z1, r_in),
    ]
    return _loft_rings(rings, seg)


def _ellipsoid(cx, cy, cz, rx, ry, rz, seg_u=16, seg_v=10):
    if seg_u < 3 or seg_v < 2:
        raise FurnitureError("ellipsoid needs seg_u>=3 and seg_v>=2")
    verts = [(cx, cy, cz - rz)]
    ring_start = {}
    for i in range(1, seg_v):
        v = math.pi * i / seg_v
        z = cz - rz * math.cos(v)
        s = math.sin(v)
        ring_start[i] = len(verts)
        for j in range(seg_u):
            u = 2 * math.pi * j / seg_u
            verts.append((cx + rx * s * math.cos(u), cy + ry * s * math.sin(u), z))
    north = len(verts)
    verts.append((cx, cy, cz + rz))

    def ring(i, j):
        return ring_start[i] + (j % seg_u)

    tris = []
    for j in range(seg_u):
        tris.append((0, ring(1, j + 1), ring(1, j)))
    for i in range(1, seg_v - 1):
        for j in range(seg_u):
            b0, b1, t0, t1 = ring(i, j), ring(i, j + 1), ring(i + 1, j), ring(i + 1, j + 1)
            tris.append((b0, b1, t1))
            tris.append((b0, t1, t0))
    for j in range(seg_u):
        tris.append((north, ring(seg_v - 1, j), ring(seg_v - 1, j + 1)))
    return verts, tris


def _heightfield_slab(x0, x1, y0, y1, z_base, height_fn, nx=10, ny=10):
    """A closed slab whose top surface follows `height_fn(x, y)` (a small
    offset above z_base) -- used for the duvet's soft undulation -- with a
    flat underside and stitched perimeter walls."""
    xs = [x0 + (x1 - x0) * i / nx for i in range(nx + 1)]
    ys = [y0 + (y1 - y0) * j / ny for j in range(ny + 1)]
    verts = [(x, y, z_base + height_fn(x, y)) for y in ys for x in xs]
    bstart = len(verts)
    verts += [(x, y, z_base) for y in ys for x in xs]

    def ti(i, j):
        return j * (nx + 1) + i

    def bi(i, j):
        return bstart + j * (nx + 1) + i

    tris = []
    for j in range(ny):
        for i in range(nx):
            a, b, c, d = ti(i, j), ti(i + 1, j), ti(i, j + 1), ti(i + 1, j + 1)
            tris.append((a, b, d))
            tris.append((a, d, c))
    for j in range(ny):
        for i in range(nx):
            a, b, c, d = bi(i, j), bi(i + 1, j), bi(i, j + 1), bi(i + 1, j + 1)
            tris.append((a, d, b))
            tris.append((a, c, d))
    for i in range(nx):
        b0, b1, t0, t1 = bi(i, 0), bi(i + 1, 0), ti(i, 0), ti(i + 1, 0)
        tris.append((b0, b1, t1)); tris.append((b0, t1, t0))
    for i in range(nx):
        b0, b1, t0, t1 = bi(i, ny), bi(i + 1, ny), ti(i, ny), ti(i + 1, ny)
        tris.append((b1, b0, t0)); tris.append((b1, t0, t1))
    for j in range(ny):
        b0, b1, t0, t1 = bi(0, j), bi(0, j + 1), ti(0, j), ti(0, j + 1)
        tris.append((b1, b0, t0)); tris.append((b1, t0, t1))
    for j in range(ny):
        b0, b1, t0, t1 = bi(nx, j), bi(nx, j + 1), ti(nx, j), ti(nx, j + 1)
        tris.append((b0, b1, t1)); tris.append((b0, t1, t0))
    return verts, tris


def _extrude_along_y(poly_zx, y0, y1):
    """Prism extruded along y from a profile given as (z, x) pairs -- for
    the headboard, whose cross-section (rounded top corners, seen from the
    front) varies across x and z but is constant through the depth y.

    `_extrude_polygon` extrudes a (a, b) polygon along its own third
    axis, producing points (a, b, extrude). Passing (z, x) as the polygon
    and y as the extrude axis yields (z, x, y); permuting to (x, y, z) is
    the cyclic map (a, b, c) -> (b, c, a), which has determinant +1 (a
    rotation of axes, not a mirror), so the verified outward winding
    survives unchanged.
    """
    v, t = _extrude_polygon(poly_zx, y0, y1)
    v = [(b, c, a) for a, b, c in v]
    return v, t


def _smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


# ------------------------------------------------------------------ rotation

def _rotation_components(rotation_deg):
    r = rotation_deg % 360.0
    if r == 0.0:
        return 1.0, 0.0
    if r == 90.0:
        return 0.0, 1.0
    if r == 180.0:
        return -1.0, 0.0
    if r == 270.0:
        return 0.0, -1.0
    a = math.radians(rotation_deg)
    return math.cos(a), math.sin(a)


def _transform(p, ca, sa, at):
    x, y, z = p
    return (x * ca - y * sa + at[0], x * sa + y * ca + at[1], z)


# ---------------------------------------------------------------- validation

def _num(value, label, item_id):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FurnitureError(f"{label} must be a number for item {item_id!r}, got {value!r}")
    f = float(value)
    if not math.isfinite(f):
        raise FurnitureError(f"{label} is not finite for item {item_id!r}: {value!r}")
    return f


def _validate_item(item):
    if not isinstance(item, dict):
        raise FurnitureError(f"furniture item must be a dict, got {item!r}")
    for key in ("id", "type", "at", "size", "height", "rotation"):
        if key not in item:
            raise FurnitureError(f"furniture item missing field {key!r}: {item!r}")
    item_id = item["id"]
    ftype = item["type"]
    if ftype not in _BUILDERS:
        raise FurnitureError(f"unknown furniture type {ftype!r} (item {item_id!r})")

    at, size = item["at"], item["size"]
    if not (isinstance(at, (list, tuple)) and len(at) == 2):
        raise FurnitureError(f"at must be [x, y] for item {item_id!r}, got {at!r}")
    if not (isinstance(size, (list, tuple)) and len(size) == 2):
        raise FurnitureError(f"size must be [width, depth] for item {item_id!r}, got {size!r}")

    at_x = _num(at[0], "at.x", item_id)
    at_y = _num(at[1], "at.y", item_id)
    width = _num(size[0], "width", item_id)
    depth = _num(size[1], "depth", item_id)
    height = _num(item["height"], "height", item_id)
    rotation = _num(item["rotation"], "rotation", item_id)
    for label, val in (("width", width), ("depth", depth), ("height", height)):
        if val <= 0:
            raise FurnitureError(f"{label} must be positive for item {item_id!r}, got {val!r}")

    return item_id, ftype, (at_x, at_y), width, depth, height, rotation


def _check_envelope(item_id, name, verts, width, depth, height, eps=1e-6):
    hw, hd = width / 2.0, depth / 2.0
    for x, y, z in verts:
        if not (-hw - eps <= x <= hw + eps and -hd - eps <= y <= hd + eps
                and -eps <= z <= height + eps):
            raise FurnitureError(
                f"item {item_id!r} component {name!r} vertex {(x, y, z)!r} "
                f"escapes the declared width/depth/height envelope "
                f"({width!r}x{depth!r}x{height!r})")


# --------------------------------------------------------------------- build

def build_furniture(item):
    item_id, ftype, at, width, depth, height, rotation = _validate_item(item)
    components = _BUILDERS[ftype](width, depth, height)

    ca, sa = _rotation_components(rotation)
    out = []
    for name, verts, tris, material in components:
        _check_envelope(item_id, name, verts, width, depth, height)
        world_verts = [_transform(v, ca, sa, at) for v in verts]
        out.append({
            "name": f"{item_id}:{name}",
            "vertices_mm": [list(v) for v in world_verts],
            "triangles": [list(t) for t in tris],
            "material": {"name": material["name"], "rgb": list(material["rgb"])},
        })
    return out


# --------------------------------------------------------------- bed_double

def _build_bed_double(w, d, h):
    hw, hd = w / 2.0, d / 2.0
    comps = []

    leg_h = 0.08 * h
    rail_h = 0.09 * h
    frame_top = leg_h + rail_h
    hb_depth = max(40.0, min(0.11 * d, 220.0))
    hb_y1 = -hd + hb_depth

    leg_margin = min(60.0, 0.2 * min(w, d))
    leg_radius = min(25.0, leg_margin * 0.4)
    leg_y_back = hb_y1 + leg_margin
    leg_y_front = hd - leg_margin
    for i, (lx, ly) in enumerate((
        (-hw + leg_margin, leg_y_back), (hw - leg_margin, leg_y_back),
        (-hw + leg_margin, leg_y_front), (hw - leg_margin, leg_y_front),
    )):
        v, t = _cylinder(lx, ly, 0.0, leg_h, leg_radius, seg=14)
        comps.append((f"leg_{i}", v, t, MATERIAL_OAK))

    frame_radius = min(20.0, 0.3 * min(w, hd - hb_y1))
    v, t = _prism(-hw, hw, hb_y1, hd, leg_h, frame_top, frame_radius, seg=4)
    comps.append(("frame", v, t, MATERIAL_OAK))

    rc = max(1.0, min(0.3 * hw, 0.18 * h, 90.0))
    seg = 6
    pts = [(0.0, -hw), (0.0, hw), (h - rc, hw)]
    c_r = (h - rc, hw - rc)
    for k in range(1, seg + 1):
        a = math.radians(90.0 - 90.0 * k / seg)
        pts.append((c_r[0] + rc * math.cos(a), c_r[1] + rc * math.sin(a)))
    pts.append((h, -hw + rc))
    c_l = (h - rc, -hw + rc)
    for k in range(1, seg + 1):
        a = math.radians(0.0 - 90.0 * k / seg)
        pts.append((c_l[0] + rc * math.cos(a), c_l[1] + rc * math.sin(a)))
    # The hand-authored profile walks clockwise in its (height, width)
    # plane. Reverse it before the extrusion's counterclockwise contract.
    v, t = _extrude_along_y(list(reversed(pts)), -hd, hb_y1)
    comps.append(("headboard", v, t, MATERIAL_LINEN))

    mattress_bottom = frame_top
    mattress_top = 0.5 * h
    inset_m = min(40.0, 0.05 * min(w, d))
    mx0, mx1 = -hw + inset_m, hw - inset_m
    my0, my1 = hb_y1 + 30.0, hd - 40.0
    m_radius = max(1.0, min(40.0, 0.2 * min(mx1 - mx0, my1 - my0)))
    v, t = _beveled_box(mx0, mx1, my0, my1, mattress_bottom, mattress_top,
                         m_radius, min(30.0, 0.15 * (mattress_top - mattress_bottom)))
    comps.append(("mattress", v, t, MATERIAL_BEDDING))

    margin, gap = 80.0, 40.0
    avail = max(200.0, w - 2 * margin - gap)
    prx = avail / 4.0
    pry = min(220.0, (my1 - my0) * 0.3)
    prz = 0.068 * h
    pcz = mattress_top + prz * 0.85
    pcy = my0 + pry + 20.0
    for name, cx in (("pillow_left", -(prx + gap / 2.0)), ("pillow_right", prx + gap / 2.0)):
        v, t = _ellipsoid(cx, pcy, pcz, prx, pry, prz, seg_u=16, seg_v=10)
        comps.append((name, v, t, MATERIAL_BEDDING))

    dx0, dx1 = -hw + 40.0, hw - 40.0
    dy0 = pcy + pry + 60.0
    dy1 = hd - 20.0
    base_t, amp = 0.06 * h, 0.02 * h
    edge_margin = max(1.0, 0.15 * min(dx1 - dx0, dy1 - dy0))

    def duvet_height(x, y):
        dx = min(x - dx0, dx1 - x)
        dy = min(y - dy0, dy1 - y)
        taper = _smoothstep(dx / edge_margin) * _smoothstep(dy / edge_margin)
        wave = 0.5 + 0.5 * math.sin(x / 220.0) * math.cos(y / 260.0)
        return base_t * 0.4 + (base_t * 0.6 + amp * wave) * taper

    v, t = _heightfield_slab(dx0, dx1, dy0, dy1, mattress_top, duvet_height, nx=12, ny=14)
    comps.append(("duvet", v, t, MATERIAL_BEDDING))

    throw_z0 = mattress_top + base_t * 0.4
    throw_layer_t = 0.03 * h
    ty1 = dy1 - 20.0
    ty0 = ty1 - min(500.0, (dy1 - dy0) * 0.3)
    tx0, tx1 = dx0 + 20.0, dx1 - 20.0
    v, t = _beveled_box(tx0, tx1, ty0, ty1, throw_z0, throw_z0 + throw_layer_t, 15.0, 6.0, seg=3)
    comps.append(("throw_base", v, t, MATERIAL_THROW))
    fx0, fx1 = tx0 + 40.0, tx1 - 40.0
    fy0, fy1 = ty0 + 60.0, ty1
    v, t = _beveled_box(fx0, fx1, fy0, fy1, throw_z0 + throw_layer_t,
                         throw_z0 + 2 * throw_layer_t, 15.0, 6.0, seg=3)
    comps.append(("throw_fold", v, t, MATERIAL_THROW))

    return comps


# ----------------------------------------------------------------- wardrobe

def _build_wardrobe(w, d, h):
    hw, hd = w / 2.0, d / 2.0
    comps = []

    panel_t = min(18.0, 0.03 * min(w, d))
    plinth_h = min(100.0, 0.06 * h)

    v, t = _prism(-hw, hw, -hd, hd, 0.0, plinth_h, min(15.0, panel_t), seg=3)
    comps.append(("plinth", v, t, MATERIAL_OAK))

    side_z0, side_z1 = plinth_h, h - panel_t
    v, t = _box(-hw, -hw + panel_t, -hd, hd, side_z0, side_z1)
    comps.append(("side_left", v, t, MATERIAL_OAK))
    v, t = _box(hw - panel_t, hw, -hd, hd, side_z0, side_z1)
    comps.append(("side_right", v, t, MATERIAL_OAK))
    v, t = _box(-hw + panel_t, hw - panel_t, -hd, -hd + panel_t, side_z0, side_z1)
    comps.append(("back", v, t, MATERIAL_OAK))
    v, t = _box(-hw, hw, -hd, hd, h - panel_t, h)
    comps.append(("top", v, t, MATERIAL_OAK))

    reveal = 15.0
    door_front_y1 = hd - reveal
    door_front_y0 = door_front_y1 - panel_t
    inner_x0, inner_x1 = -hw + panel_t + 5.0, hw - panel_t - 5.0
    gap = 10.0
    door_w = (inner_x1 - inner_x0 - gap) / 2.0
    door_z0, door_z1 = plinth_h + 20.0, h - panel_t - 20.0

    doors = [
        ("door_left", inner_x0, inner_x0 + door_w),
        ("door_right", inner_x1 - door_w, inner_x1),
    ]
    for name, dx0, dx1 in doors:
        v, t = _box(dx0, dx1, door_front_y0, door_front_y1, door_z0, door_z1)
        comps.append((name, v, t, MATERIAL_OAK))

    handle_z0 = (door_z0 + door_z1) / 2.0 - 60.0
    handle_z1 = (door_z0 + door_z1) / 2.0 + 60.0
    handle_y0, handle_y1 = door_front_y1, door_front_y1 + 8.0
    for name, dx0, dx1 in doors:
        hx = dx1 - 30.0 if name == "door_left" else dx0 + 30.0 - 15.0
        v, t = _box(hx, hx + 15.0, handle_y0, handle_y1, handle_z0, handle_z1)
        comps.append((name + "_handle", v, t, MATERIAL_METAL))

    return comps


# --------------------------------------------------------------------- desk

def _build_desk(w, d, h):
    hw, hd = w / 2.0, d / 2.0
    comps = []

    top_thickness = min(35.0, 0.05 * h)
    leg_margin = min(45.0, 0.06 * min(w, d))
    leg_radius = min(20.0, leg_margin * 0.4)
    leg_top = h - top_thickness

    leg_x = hw - leg_margin
    leg_y = hd - leg_margin
    for i, (lx, ly) in enumerate((
        (-leg_x, -leg_y), (leg_x, -leg_y), (-leg_x, leg_y), (leg_x, leg_y),
    )):
        v, t = _cylinder(lx, ly, 0.0, leg_top, leg_radius, seg=14)
        comps.append((f"leg_{i}", v, t, MATERIAL_OAK))

    apron_h = min(70.0, 0.1 * h)
    apron_t = min(20.0, 0.04 * min(w, d))
    apron_z0, apron_z1 = leg_top - apron_h, leg_top
    v, t = _box(-leg_x - apron_t / 2.0, -leg_x + apron_t / 2.0, -leg_y, leg_y, apron_z0, apron_z1)
    comps.append(("apron_left", v, t, MATERIAL_OAK))
    v, t = _box(leg_x - apron_t / 2.0, leg_x + apron_t / 2.0, -leg_y, leg_y, apron_z0, apron_z1)
    comps.append(("apron_right", v, t, MATERIAL_OAK))
    v, t = _box(-leg_x, leg_x, -leg_y - apron_t / 2.0, -leg_y + apron_t / 2.0, apron_z0, apron_z1)
    comps.append(("apron_back", v, t, MATERIAL_OAK))

    drawer_w = min(600.0, 0.5 * w)
    housing_h = min(80.0, 0.12 * h)
    housing_z1 = leg_top
    housing_z0 = housing_z1 - housing_h
    housing_y1 = leg_y - 30.0
    housing_y0 = housing_y1 - 120.0
    v, t = _box(-drawer_w / 2.0 - 5.0, drawer_w / 2.0 + 5.0, housing_y0, housing_y1,
                housing_z0, housing_z1)
    comps.append(("drawer_housing", v, t, MATERIAL_OAK))

    front_y0, front_y1 = housing_y1, housing_y1 + 14.0
    front_z0, front_z1 = housing_z0 + 5.0, housing_z1 - 5.0
    v, t = _box(-drawer_w / 2.0, drawer_w / 2.0, front_y0, front_y1, front_z0, front_z1)
    comps.append(("drawer_front", v, t, MATERIAL_OAK))

    handle_z = (front_z0 + front_z1) / 2.0
    v, t = _box(-40.0, 40.0, front_y1, front_y1 + 7.0, handle_z - 6.0, handle_z + 6.0)
    comps.append(("drawer_handle", v, t, MATERIAL_METAL))

    top_radius = min(20.0, 0.3 * min(w, d))
    v, t = _beveled_box(-hw, hw, -hd, hd, leg_top, h, top_radius, min(8.0, top_thickness * 0.3), seg=5)
    comps.append(("tabletop", v, t, MATERIAL_OAK))

    return comps


# -------------------------------------------------------------- bedside_table

def _build_bedside_table(w, d, h):
    hw, hd = w / 2.0, d / 2.0
    comps = []

    top_thickness = min(28.0, 0.06 * h)
    leg_margin = min(30.0, 0.08 * min(w, d))
    leg_radius = min(14.0, leg_margin * 0.4)
    leg_top = h - top_thickness

    leg_x, leg_y = hw - leg_margin, hd - leg_margin
    for i, (lx, ly) in enumerate((
        (-leg_x, -leg_y), (leg_x, -leg_y), (-leg_x, leg_y), (leg_x, leg_y),
    )):
        v, t = _cylinder(lx, ly, 0.0, leg_top, leg_radius, seg=12)
        comps.append((f"leg_{i}", v, t, MATERIAL_OAK))

    car_x0, car_x1 = -leg_x + 10.0, leg_x - 10.0
    car_y1 = leg_y - 40.0
    car_y0 = -leg_y + 10.0
    car_z0, car_z1 = 0.1 * h, leg_top
    v, t = _prism(car_x0, car_x1, car_y0, car_y1, car_z0, car_z1, 10.0, seg=3)
    comps.append(("carcass", v, t, MATERIAL_OAK))

    drawer_gap = 15.0
    usable = (car_z1 - 20.0) - (car_z0 + 20.0) - drawer_gap
    drawer_h = usable / 2.0
    dx0, dx1 = car_x0 + 15.0, car_x1 - 15.0
    front_y0, front_y1 = car_y1, car_y1 + 14.0

    z_top0 = car_z1 - 20.0 - drawer_h
    z_top1 = car_z1 - 20.0
    z_bot0 = car_z0 + 20.0
    z_bot1 = car_z0 + 20.0 + drawer_h
    for name, z0, z1 in (("drawer_top", z_top0, z_top1), ("drawer_bottom", z_bot0, z_bot1)):
        v, t = _box(dx0, dx1, front_y0, front_y1, z0, z1)
        comps.append((name, v, t, MATERIAL_OAK))
        hz = (z0 + z1) / 2.0
        v, t = _box(-30.0, 30.0, front_y1, front_y1 + 7.0, hz - 5.0, hz + 5.0)
        comps.append((name + "_handle", v, t, MATERIAL_METAL))

    top_radius = min(15.0, 0.3 * min(w, d))
    v, t = _beveled_box(-hw, hw, -hd, hd, leg_top, h, top_radius, min(6.0, top_thickness * 0.3), seg=4)
    comps.append(("tabletop", v, t, MATERIAL_OAK))

    return comps


_BUILDERS = {
    "bed_double": _build_bed_double,
    "bedside_table": _build_bedside_table,
    "wardrobe": _build_wardrobe,
    "desk": _build_desk,
}
