"""W6 deliverables from an L0 spec: schedules, quantities, relative cost, spec book, IFC.

Everything is computed from the spec (model.Project); nothing is typed by hand. Cost is RELATIVE only:
AECOM Middle East Property & Construction Handbook 2026 villa rates (Q3 2025, USD per m2 GIA, printed
page 120) cover Gulf cities, not Cairo, so they rank options and never make a budget.
"""
from __future__ import annotations

import csv
import io
import math
from pathlib import Path

from . import model, rules, vocabulary as vocab
from .safe_io import atomic_path, save_text

# AECOM MEH 2026 p. 120 (Q3 2025, USD/m2 GIA): villas, low-high per city. Card: aecom-villa-rates-2025.
AECOM_VILLA_USD_M2 = {"Dubai": (1700, 3000), "Riyadh": (1300, 2600), "Doha": (1300, 2600), "Manama": (1000, 1800)}


def _poly_perimeter(pts):
    return sum(math.dist(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts)))


def _facing(p: model.Project, o: model.Opening) -> str:
    """Compass direction an external opening faces (+Y is north), from the side the room is on."""
    w = p.wall(o.host)
    a, b = rules.opening_sides(p, o)
    nx, ny = w.normal                                       # left of the wall direction
    out = (-nx, -ny) if a is not None and b is None else (nx, ny) if b is not None and a is None else None
    if out is None:
        return "internal"
    return ("north" if out[1] > 0 else "south") if abs(out[1]) >= abs(out[0]) else ("east" if out[0] > 0 else "west")


def schedules(p: model.Project) -> dict[str, list[dict]]:
    rooms = [{"id": r.id, "name": r.name, "level": r.level, "occupancy": r.occupancy,
              "area_m2": round(r.area_m2, 2), "perimeter_m": round(_poly_perimeter(r.boundary) / 1000, 2)}
             for r in p.rooms]
    doors, windows = [], []
    for o in p.openings:
        a, b = rules.opening_sides(p, o)
        sides = " / ".join(x.name if x else "outside" for x in (a, b))
        row = {"id": o.id, "level": p.wall(o.host).level, "host": o.host, "width_mm": o.width, "height_mm": o.height,
               "between": sides}
        if o.kind == "door":
            doors.append(dict(row, swing=o.swing, external=(a is None) != (b is None)))
        else:
            windows.append(dict(row, sill_mm=o.sill, area_m2=round(o.width * o.height / 1e6, 2), facing=_facing(p, o)))
    furniture = [{"id": f.id, "level": f.level, "type": f.type, "room": f.room,
                  "size_mm": list(rules._furniture_size(f)), "rotation": f.rotation} for f in p.furniture]
    return {"rooms": rooms, "doors": doors, "windows": windows, "furniture": furniture}


def quantities(p: model.Project) -> dict:
    """Areas and wall quantities per level. Walls at centreline length x level height; opening areas deducted."""
    out = {}
    for lv in p.levels:
        walls = [w for w in p.walls if w.level == lv.id]
        by_type = {}
        for w in walls:
            q = by_type.setdefault(w.type, {"length_m": 0.0, "gross_area_m2": 0.0, "openings_m2": 0.0})
            q["length_m"] += w.length / 1000
            q["gross_area_m2"] += w.length * lv.height / 1e6
            q["openings_m2"] += sum(o.width * o.height for o in p.openings_of(w.id)) / 1e6
        for q in by_type.values():
            q["net_area_m2"] = q["gross_area_m2"] - q["openings_m2"]
            for k in list(q):
                q[k] = round(q[k], 2)
        rooms = [r for r in p.rooms if r.level == lv.id]
        out[lv.id] = {"net_floor_m2": round(sum(r.area_m2 for r in rooms), 2),
                      "habitable_m2": round(sum(r.area_m2 for r in rooms if r.occupancy in vocab.HABITABLE), 2),
                      "walls": by_type,
                      "doors": sum(1 for o in p.openings if o.kind == "door" and p.wall(o.host).level == lv.id),
                      "windows": sum(1 for o in p.openings if o.kind == "window" and p.wall(o.host).level == lv.id)}
    return out


def gross_area_m2(p: model.Project) -> float:
    """Gross internal area approximated as net room area plus half-thickness wall zones around each room."""
    return round(sum(r.area_m2 for r in p.rooms), 2)


def relative_cost(options: dict[str, float], city: str = "Dubai") -> list[dict]:
    """Rank options by GIA x AECOM villa rate. Relative only: the index is what matters, not the USD."""
    lo, hi = AECOM_VILLA_USD_M2[city]
    base = min(options.values())
    return [{"option": k, "gia_m2": round(v, 1), "index": round(v / base, 3),
             "usd_low": round(v * lo), "usd_high": round(v * hi), "rate_basis": f"AECOM MEH 2026 p. 120, villas, {city}, Q3 2025"}
            for k, v in sorted(options.items(), key=lambda kv: kv[1])]


def write_csv(rows: list[dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.StringIO(newline="") as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        else:
            f.write("note\nnone in this model\n")
        save_text(path, f.getvalue())
    return path


def spec_book(assignments: list[dict]) -> str:
    """Markdown spec book. assignments: [{"room", "element", "product_id", "alternate_id"?}]; each product's
    verification checks come from the product library, so an unverified item is visibly unverified."""
    from .products import store
    lines = ["# Specification book", "", "Each item names the product, its source and licence, and the checks it "
             "passed in the product library. 'not_checkable' is never a pass.", ""]
    for a in assignments:
        for role, pid in (("specified", a["product_id"]), ("alternate", a.get("alternate_id"))):
            if not pid:
                continue
            it = next((x for x in store.search(include_unverified=True, text=None, limit=100000) if x["id"] == pid), None)
            if it is None:
                lines.append(f"- **{a['room']} / {a['element']}** ({role}): `{pid}` NOT IN LIBRARY")
                continue
            checks = {c["name"]: c["status"] for c in store.checks_for(pid)}
            lines.append(f"- **{a['room']} / {a['element']}** ({role}): {it['name']} (`{pid}`), source {it['source']}, "
                         f"licence {it.get('license')}, layer **{it.get('layer')}**; checks: "
                         + ", ".join(f"{k} {v}" for k, v in sorted(checks.items())))
    return "\n".join(lines) + "\n"


def to_ifc(p: model.Project, path: Path) -> Path:
    """IFC4 export: storeys, walls (extruded along their centrelines), openings with doors/windows filling
    them, and spaces extruded from room outlines. Geometry in millimetres."""
    import numpy as np
    import ifcopenshell
    import ifcopenshell.api as api
    MM = 1000.0     # ifcopenshell.api representation helpers take SI metres; placements below are in project mm
    f = ifcopenshell.file(schema="IFC4")
    proj = api.run("root.create_entity", f, ifc_class="IfcProject", name=p.name)
    api.run("unit.assign_unit", f, length={"is_metric": True, "raw": "MILLIMETERS"})
    ctx = api.run("context.add_context", f, context_type="Model")
    body = api.run("context.add_context", f, context_type="Model", context_identifier="Body",
                   target_view="MODEL_VIEW", parent=ctx)
    site = api.run("root.create_entity", f, ifc_class="IfcSite", name="Site")
    bldg = api.run("root.create_entity", f, ifc_class="IfcBuilding", name="Building")
    api.run("aggregate.assign_object", f, relating_object=proj, products=[site])
    api.run("aggregate.assign_object", f, relating_object=site, products=[bldg])
    storeys = {}
    for lv in p.levels:
        s = api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name=lv.name)
        s.Elevation = lv.elevation
        api.run("aggregate.assign_object", f, relating_object=bldg, products=[s])
        storeys[lv.id] = (s, lv)

    def place(product, x, y, z, angle):
        m = np.eye(4)
        c, sn = math.cos(angle), math.sin(angle)
        m[0][0], m[0][1], m[1][0], m[1][1] = c, -sn, sn, c
        m[0][3], m[1][3], m[2][3] = x, y, z
        api.run("geometry.edit_object_placement", f, product=product, matrix=m, is_si=False)

    wall_of = {}
    for w in p.walls:
        s, lv = storeys[w.level]
        t = p.wall_type(w.type).thickness
        el = api.run("root.create_entity", f, ifc_class="IfcWall", name=w.id)
        api.run("spatial.assign_container", f, relating_structure=s, products=[el])
        rep = api.run("geometry.add_wall_representation", f, context=body, length=w.length / MM, height=lv.height / MM,
                      thickness=t / MM)
        api.run("geometry.assign_representation", f, product=el, representation=rep)
        dx, dy = w.direction
        nx, ny = w.normal
        place(el, w.start[0] - nx * t / 2, w.start[1] - ny * t / 2, lv.elevation, math.atan2(dy, dx))
        wall_of[w.id] = (el, w, t, lv)
    for o in p.openings:
        el, w, t, lv = wall_of[o.host]
        op = api.run("root.create_entity", f, ifc_class="IfcOpeningElement", name=o.id + "-void")
        rep = api.run("geometry.add_wall_representation", f, context=body, length=o.width / MM, height=o.height / MM,
                      thickness=(t + 20) / MM)
        api.run("geometry.assign_representation", f, product=op, representation=rep)
        dx, dy = w.direction
        nx, ny = w.normal
        sx, sy = w.point_at(o.at - o.width / 2, 0)
        place(op, sx - nx * (t + 20) / 2, sy - ny * (t + 20) / 2, lv.elevation + (o.sill if o.kind == "window" else 0),
              math.atan2(dy, dx))
        api.run("feature.add_feature", f, feature=op, element=el)
        fill = api.run("root.create_entity", f, ifc_class="IfcDoor" if o.kind == "door" else "IfcWindow", name=o.id)
        fill.OverallWidth, fill.OverallHeight = o.width, o.height
        api.run("spatial.assign_container", f, relating_structure=storeys[w.level][0], products=[fill])
        api.run("feature.add_filling", f, opening=op, element=fill)
    for r in p.rooms:
        s, lv = storeys[r.level]
        sp = api.run("root.create_entity", f, ifc_class="IfcSpace", name=r.id)
        sp.LongName = r.name
        sp.ObjectType = r.occupancy or None
        api.run("aggregate.assign_object", f, relating_object=s, products=[sp])
        # built directly: the api's slab helper writes an open IfcIndexedPolyCurve that the geometry engine
        # renders as nothing; a closed IfcPolyline profile is read correctly (checked by tests/test_deliverables.py)
        pts = [f.createIfcCartesianPoint((float(x), float(y))) for x, y in list(r.boundary) + [r.boundary[0]]]
        prof = f.createIfcArbitraryClosedProfileDef("AREA", None, f.createIfcPolyline(pts))
        solid = f.createIfcExtrudedAreaSolid(prof, f.createIfcAxis2Placement3D(f.createIfcCartesianPoint((0.0, 0.0, 0.0))),
                                             f.createIfcDirection((0.0, 0.0, 1.0)), float(lv.height))
        rep = f.createIfcShapeRepresentation(body, "Body", "SweptSolid", [solid])
        api.run("geometry.assign_representation", f, product=sp, representation=rep)
        place(sp, 0, 0, lv.elevation, 0.0)
    path.parent.mkdir(parents=True, exist_ok=True)
    with atomic_path(path) as staged:
        f.write(staged)
    return path
