"""Cut poche from the DESIGN MODEL solids (walls, slabs, beams, columns, stair treads), not from the scene.

Why: the scene shell is finish skins (1 mm layers), so its sections are not closed solids and give no poche (measured
on the stair section: slabs and walls came out unfilled). The model solids are closed by construction. The scene still
supplies every projected edge (Blender Line Art), so the cut and the view come from two different sources; `check_cut`
compares them (cut outline lines vs scene skin cut segments) and QA reports the max offset.

All values metres in the view frame (u, z); scene z. Classes: "structure" (ours), "context" (not ours).
"""
from __future__ import annotations

from shapely.geometry import LineString, MultiPolygon, Polygon, box
from shapely.ops import unary_union

from archpipe.contracts import DesignElement

from .section import View

MM = 0.001
FAR = 200.0


def _line(view: View):
    """The cut plane as a long line in plan (model x, y metres), parametrised by u."""
    ux, uy = view.u_axis
    cx, cy = view.p0
    u0 = cx * ux + cy * uy
    # a point on the plane at u = 0 and the direction along u
    px, py = cx - u0 * ux, cy - u0 * uy
    return LineString([(px - FAR * ux, py - FAR * uy), (px + FAR * ux, py + FAR * uy)]), (px, py)


def _u_intervals(plan_poly: Polygon, view: View) -> list[tuple[float, float]]:
    ln, (px, py) = _line(view)
    g = ln.intersection(plan_poly)
    parts = [g] if g.geom_type == "LineString" else list(getattr(g, "geoms", []))
    ux, uy = view.u_axis
    out = []
    for p in parts:
        if p.geom_type != "LineString" or p.length < 1e-6:
            continue
        us = [(x - px) * ux + (y - py) * uy for x, y in p.coords]
        out.append((min(us), max(us)))
    return out


def _wall_plan(p: dict) -> Polygon:
    import math
    a, b = (p["x0_mm"] * MM, p["y0_mm"] * MM), (p["x1_mm"] * MM, p["y1_mm"] * MM)
    L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
    n = (-u[1], u[0])
    h = p["thickness_mm"] * MM / 2
    return Polygon([(a[0] - u[0] * h + n[0] * h, a[1] - u[1] * h + n[1] * h), (b[0] + u[0] * h + n[0] * h, b[1] + u[1] * h + n[1] * h),
                    (b[0] + u[0] * h - n[0] * h, b[1] + u[1] * h - n[1] * h), (a[0] - u[0] * h - n[0] * h, a[1] - u[1] * h - n[1] * h)])


def _pts(poly):
    return [(p[0] * MM, p[1] * MM) for p in poly]


def cut_solids(els: list[DesignElement], levels: dict, view: View) -> dict:
    """{class: [Polygon (u,z)]}, plus {"items": [(id, kind, class, [(u0,u1,z0,z1)])]} for QA and tests."""
    ffl = {k: v["ffl_scene_mm"] * MM for k, v in levels.items() if "ffl_scene_mm" in v}
    items = []

    def add(eid, kind, cls, plan_poly, z0, z1, holes=()):
        for u0, u1 in _u_intervals(plan_poly, view):
            r = box(u0, z0, u1, z1)
            for h in holes:
                r = r.difference(h)
            if not r.is_empty:
                items.append((eid, kind, cls, r))

    openings: dict[str, list] = {}
    for e in els:
        if e.kind in ("door", "window") and e.host:
            openings.setdefault(e.host, []).append(e)

    for e in els:
        p = e.params
        base = ffl.get(e.level, 0.0)
        if e.kind == "wall":
            plan = _wall_plan(p)
            z0 = base + e.placement[2] * MM
            holes = []
            for o in openings.get(e.id, []):
                import math
                ow = o.size[0] * MM
                horiz = abs(p["y1_mm"] - p["y0_mm"]) < 1
                c = (o.placement[0] * MM, o.placement[1] * MM)
                t = p["thickness_mm"] * MM / 2 + 0.01
                fp = box(c[0] - ow / 2, c[1] - t, c[0] + ow / 2, c[1] + t) if horiz else box(c[0] - t, c[1] - ow / 2, c[0] + t, c[1] + ow / 2)
                sill = (o.params.get("sill_mm") or 0.0) * MM if o.kind == "window" else 0.0
                oh = (o.params.get("height_mm") or o.size[2]) * MM
                for u0, u1 in _u_intervals(fp, view):
                    holes.append(box(u0, z0 + sill, u1, z0 + sill + oh))
            add(e.id, "wall", "structure", plan, z0, z0 + p["height_mm"] * MM, holes)
        elif e.kind == "slab":
            t = p["thickness_mm"] * MM
            if "profile_xz_mm" in p:
                # ramp: top-line profile in absolute model (x, scene z), thickness measured vertically, extruded over y.
                y0, y1 = (e.placement[1] - e.size[1] / 2) * MM, (e.placement[1] + e.size[1] / 2) * MM
                cy = view.p0[1]
                if abs(view.u_axis[0] - 1.0) < 1e-9 and y0 <= cy <= y1:
                    top = [(q[0] * MM, q[1] * MM) for q in p["profile_xz_mm"]]
                    items.append((e.id, "ramp", "structure", Polygon(top + [(x, z - t) for x, z in reversed(top)])))
                continue
            if p.get("polygon_mm"):
                plan = Polygon(_pts(p["polygon_mm"]), [_pts(h) for h in p.get("holes_mm", [])])
            else:
                plan = box((e.placement[0] - e.size[0] / 2) * MM, (e.placement[1] - e.size[1] / 2) * MM,
                           (e.placement[0] + e.size[0] / 2) * MM, (e.placement[1] + e.size[1] / 2) * MM)
            top = base + p.get("z_top_mm", e.placement[2] + e.size[2]) * MM if "z_top_mm" in p else base + (e.placement[2] + t / MM) * MM
            add(e.id, "slab", "structure", plan, top - t, top)
        elif e.kind == "beam":
            plan = box((e.placement[0] - e.size[0] / 2) * MM, (e.placement[1] - e.size[1] / 2) * MM,
                       (e.placement[0] + e.size[0] / 2) * MM, (e.placement[1] + e.size[1] / 2) * MM)
            add(e.id, "beam", "structure", plan, p["z0_scene_mm"] * MM, p["z1_scene_mm"] * MM)
        elif e.kind == "column":
            plan = box(p["x0_mm"] * MM, p["y0_mm"] * MM, p["x1_mm"] * MM, p["y1_mm"] * MM)
            add(e.id, "column", "structure", plan, ffl["B"], ffl["B"] + e.size[2] * MM)
        elif e.kind == "stair":
            for i, b in enumerate(p["tread_boxes_mm"]):
                plan = box(min(b[0], b[3]) * MM, min(b[1], b[4]) * MM, max(b[0], b[3]) * MM, max(b[1], b[4]) * MM)
                add("%s-t%02d" % (e.id, i), "tread", "structure", plan, min(b[2], b[5]) * MM, max(b[2], b[5]) * MM)
        elif e.kind == "context" and p.get("what") in ("apartment", "core") and "z0_scene_mm" in p:
            plan = box((e.placement[0] - e.size[0] / 2) * MM, (e.placement[1] - e.size[1] / 2) * MM,
                       (e.placement[0] + e.size[0] / 2) * MM, (e.placement[1] + e.size[1] / 2) * MM)
            add(e.id, "context-" + p["what"], "context", plan, p["z0_scene_mm"] * MM, p["z1_scene_mm"] * MM)
    # storey slabs from the apartment box footprint: L1 slab (2.8..3.0) is our ceiling slab, ROOF slab is not ours
    apt = next((e for e in els if e.id == "ctx-apartment-above"), None)
    if apt is not None:
        plan = box((apt.placement[0] - apt.size[0] / 2) * MM, (apt.placement[1] - apt.size[1] / 2) * MM,
                   (apt.placement[0] + apt.size[0] / 2) * MM, (apt.placement[1] + apt.size[1] / 2) * MM)
        for sid, cls in (("storey-L1", "structure"), ("storey-ROOF", "context")):
            st = levels.get(sid.split("-")[1])
            if st:
                top = st["ffl_scene_mm"] * MM
                add(sid + "-slab", "storey-slab", cls, plan, top - st["slab_mm"] * MM, top)
    out: dict = {"structure": [], "context": [], "items": [(i, k, c, r.bounds) for i, k, c, r in items]}
    for cls in ("structure", "context"):
        u = unary_union([r for _, _, c, r in items if c == cls])
        out[cls] = [] if u.is_empty else (list(u.geoms) if isinstance(u, MultiPolygon) else [u])
    return out
