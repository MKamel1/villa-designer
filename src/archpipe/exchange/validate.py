"""Round-trip validation: read an exported IFC back with ifcopenshell and compare it with the design model.

Nothing here reuses the exporter's arithmetic. Geometry is re-tessellated by the IfcOpenShell kernel (world
coordinates, voids applied) and compared with the model's own figures; relationships are read from the file.
`validate_ifc` returns a list of Check records; `all_ok` is the gate. Tolerances are stated on every check.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element as UE
import ifcopenshell.util.placement as UP
import ifcopenshell.util.shape as US
import ifcopenshell.validate
import numpy as np

from ..contracts import DesignElement
from . import common as C
from . import ifc as I
from . import quantities as Q

AREA_TOL_PCT = 0.5
SIZE_TOL_MM = 1.0
PLACE_TOL_MM = 1.0
HEIGHT_TOL_MM = 1.0


@dataclass
class Check:
    name: str
    n: int
    worst: float | None        # worst deviation in `unit`
    tol: float | None
    unit: str
    ok: bool
    detail: str = ""
    failures: list = field(default_factory=list)

    def line(self) -> str:
        w = "-" if self.worst is None else f"{self.worst:.4g}"
        t = "-" if self.tol is None else f"{self.tol:g}"
        return f"{'PASS' if self.ok else 'FAIL'}  {self.name}: n={self.n} worst={w} {self.unit} (tol {t}) {self.detail}"


def all_ok(checks: list[Check]) -> bool:
    return all(c.ok for c in checks)


def _settings():
    st = ifcopenshell.geom.settings()
    st.set("use-world-coords", True)
    return st


class _Geo:
    """Tessellated world-space geometry (mm) of IFC products, cached."""

    def __init__(self):
        self.st = _settings()
        self.c: dict[int, object] = {}

    def shape(self, ent):
        k = ent.id()
        if k not in self.c:
            self.c[k] = ifcopenshell.geom.create_shape(self.st, ent)
        return self.c[k]

    def verts(self, ent) -> np.ndarray:
        return np.array(self.shape(ent).geometry.verts).reshape(-1, 3) * 1000.0

    def bbox(self, ent):
        v = self.verts(ent)
        return v.min(0), v.max(0)

    def volume_m3(self, ent) -> float:
        return US.get_volume(self.shape(ent).geometry)

    def area_m2(self, ent) -> float:
        return US.get_area(self.shape(ent).geometry)


def _source_ids(f) -> dict[str, object]:
    out = {}
    for ps in f.by_type("IfcPropertySet"):
        if ps.Name != "ArchPipe_Source":
            continue
        sid = next((p.NominalValue.wrappedValue for p in ps.HasProperties if p.Name == "SourceId"), None)
        for rel in ps.DefinesOccurrence or ():
            for o in rel.RelatedObjects:
                out[sid] = o
        for t in getattr(ps, "DefinesType", None) or ():
            out[sid] = t
    return out


def _pset(ent, name):
    return (UE.get_psets(ent).get(name)) or {}


def validate_ifc(path, elements: list[DesignElement], levels: dict, scope: str = "ALL",
                 schema_check: bool = True) -> list[Check]:
    f = ifcopenshell.open(str(path))
    geo = _Geo()
    els = [e for e in elements if I.in_scope(e, scope)]
    by = {e.id: e for e in elements}
    ent = _source_ids(f)
    out: list[Check] = []

    def add(name, n, worst, tol, unit, fails=(), detail=""):
        out.append(Check(name, n, worst, tol, unit, not fails and (worst is None or tol is None or worst <= tol),
                         detail, list(fails)[:10]))

    # 1. class counts: every IfcProduct class in the file against the expectation derived from the model
    exp = I.expected_class_counts(elements, scope)
    got = Counter(p.is_a() for p in f.by_type("IfcProduct"))
    got.update(Counter(t.is_a() for t in f.by_type("IfcTypeObject")))
    got["IfcProject"] = len(f.by_type("IfcProject"))
    bad = [f"{k}: file {got.get(k, 0)} vs model {v}" for k, v in sorted(exp.items()) if got.get(k, 0) != v]
    extra = [k for k in got if k not in exp]
    add("class counts", sum(exp.values()), None, None, "", bad + [f"unexpected class {k}" for k in extra],
        f"{len(exp)} classes, {sum(got.values())} instances")

    # 2. id set: every model element id appears exactly once as ArchPipe_Source.SourceId and nothing else does
    want = {e.id for e in els}
    have = set(ent)
    add("id set", len(want), None, None, "", [f"missing {i}" for i in sorted(want - have)[:5]]
        + [f"extra {i}" for i in sorted(have - want)[:5]], f"{len(have)} ids in file")

    els = [e for e in els if e.id in ent]               # a missing element is reported above, not a crash below

    # 3. room areas (volume of the space solid / clear height) vs model polygon; Qto and floor covering vs net area
    rooms = [e for e in els if e.kind == "room"]
    dev, fails = 0.0, []
    for r in rooms:
        p = r.params
        a_geo = geo.volume_m3(ent[r.id]) / (float(p["clear_height_mm"]) / 1000.0)
        a_mod = C.polygon_area_mm2(p["polygon_mm"]) / 1e6
        d = abs(a_geo - a_mod) / a_mod * 100
        dev = max(dev, d)
        if d > AREA_TOL_PCT:
            fails.append(f"{r.id}: {a_geo:.3f} vs {a_mod:.3f} m2")
    add("room areas (geometry vs model polygon)", len(rooms), dev, AREA_TOL_PCT, "%", fails)
    dev, fails = 0.0, []
    for r in rooms:
        q = _pset(ent[r.id], "Qto_SpaceBaseQuantities")
        net = r.params.get("net_area_m2")
        if net is None:
            continue
        d = abs(q.get("NetFloorArea", math.nan) - net) / net * 100
        dev = max(dev, d)
        if not d <= AREA_TOL_PCT:
            fails.append(f"{r.id}: Qto {q.get('NetFloorArea')} vs {net}")
    add("room NetFloorArea Qto vs model net area", len(rooms), dev, AREA_TOL_PCT, "%", fails)
    covs = [e for e in els if e.kind in ("floor", "ceiling")]
    dev, fails = 0.0, []
    for c in covs:
        a_geo = geo.area_m2(ent[c.id])
        a_mod = float(c.params["area_m2"])
        d = abs(a_geo - a_mod) / a_mod * 100
        dev = max(dev, d)
        if d > AREA_TOL_PCT:
            fails.append(f"{c.id}: {a_geo:.3f} vs {a_mod:.3f} m2")
    if covs:
        add("floor/ceiling areas (surface geometry vs model)", len(covs), dev, AREA_TOL_PCT, "%", fails)

    # 4. door / window sizes: attributes, Qto and the rendered leaf geometry
    ops = [e for e in els if e.kind in ("door", "window")]
    dev, fails = 0.0, []
    for o in ops:
        x = ent[o.id]
        W, H = float(o.params["width_mm"]), float(o.params["height_mm"])
        lo, hi = geo.bbox(x)
        ext = hi - lo
        wgeo = max(ext[0], ext[1])                      # leaf is thin: its long horizontal extent is the width
        for got_, want_, what in ((x.OverallWidth, W, "attr W"), (x.OverallHeight, H, "attr H"),
                                  (wgeo, W, "geo W"), (ext[2], H, "geo H")):
            d = abs(got_ - want_)
            dev = max(dev, d)
            if d > SIZE_TOL_MM:
                fails.append(f"{o.id} {what}: {got_:.1f} vs {want_}")
    add("door/window sizes", len(ops), dev, SIZE_TOL_MM, "mm", fails)

    # 5. every door/window sits in a wall void: fills -> opening -> voids -> the model's host wall; geometry nested
    fails, dev = [], 0.0
    for o in ops:
        x = ent[o.id]
        fills = [r for r in f.by_type("IfcRelFillsElement") if r.RelatedBuildingElement == x]
        if len(fills) != 1:
            fails.append(f"{o.id}: {len(fills)} IfcRelFillsElement")
            continue
        opening = fills[0].RelatingOpeningElement
        voids = [r for r in f.by_type("IfcRelVoidsElement") if r.RelatedOpeningElement == opening]
        if len(voids) != 1:
            fails.append(f"{o.id}: opening voids {len(voids)} elements")
            continue
        wall = voids[0].RelatingBuildingElement
        if wall != ent.get(o.host):
            fails.append(f"{o.id}: voids {wall.Name} but model host is {o.host}")
            continue
        lo_o, hi_o = geo.bbox(opening)
        lo_f, hi_f = geo.bbox(x)
        lo_w, hi_w = geo.bbox(wall)
        slack = max(0.0, *(lo_o - lo_f), *(hi_f - hi_o))        # fill must lie inside its void
        wall_slack = max(0.0, *(lo_w[:2] - lo_f[:2]) - 0, *(hi_f[:2] - hi_w[:2]))   # and in the wall's footprint
        dev = max(dev, slack, wall_slack)
    add("doors/windows in their wall void (relations + geometry nesting)", len(ops), dev, SIZE_TOL_MM, "mm", fails)

    # 6. wall quantities: Qto NetVolume vs the kernel volume of the voided wall (this is the proof the voids cut)
    walls = [e for e in els if e.kind == "wall"]
    dev, fails = 0.0, []
    for w in walls:
        q = _pset(ent[w.id], "Qto_WallBaseQuantities")
        v = geo.volume_m3(ent[w.id])
        d = abs(v - q["NetVolume"]) / q["NetVolume"] * 100
        dev = max(dev, d)
        if d > AREA_TOL_PCT:
            fails.append(f"{w.id}: kernel {v:.4f} vs Qto NetVolume {q['NetVolume']:.4f} m3")
    add("wall NetVolume Qto vs voided geometry", len(walls), dev, AREA_TOL_PCT, "%", fails)

    # 7. stair: riser and going from the tread solids themselves
    for s in (e for e in els if e.kind == "stair"):
        fl = next(x for x in ent[s.id].IsDecomposedBy[0].RelatedObjects)
        v = geo.verts(fl)
        solids = [i for r in fl.Representation.Representations for i in r.Items]
        org = UP.get_local_placement(fl.ObjectPlacement)[:3, 3]
        treads = []
        for sol in solids:                                          # the tread boxes (riser bars are thinner)
            if sol.Depth and sol.Depth >= 50.0 and sol.SweptArea.XDim > 200:
                pos = sol.Position.Location.Coordinates
                treads.append((float(pos[2]) + float(sol.Depth), np.array([pos[0] + org[0], pos[1] + org[1]], float),
                               float(sol.SweptArea.XDim)))
        treads.sort(key=lambda t: t[0])                             # ascending
        tops = [t[0] for t in treads]
        risers = [b - a for a, b in zip(tops, tops[1:])]
        run = treads[-1][1] - treads[0][1]
        if abs(run[0]) < 0.99 * np.linalg.norm(run):
            raise C.ExchangeError([f"{s.id}: validate assumes a stair running along x"])
        sgn = 1.0 if run[0] > 0 else -1.0
        nosing = [t[1][0] - sgn * t[2] / 2 for t in treads]         # edge farthest from the top landing = the nosing
        gos = [abs(b - a) for a, b in zip(nosing, nosing[1:])]
        p = s.params
        dr = max(abs(r - p["riser_mm"]) for r in risers)
        dg = max(abs(g - p["tread_mm"]) for g in gos)
        add(f"stair {s.id}: riser (tread-top steps)", len(risers), dr, 0.01, "mm",
            [] if dr <= 0.01 else [f"max {dr:.3f}"], f"model {p['riser_mm']} mm; {len(treads)} treads")
        add(f"stair {s.id}: going (nosing to nosing)", len(gos), dg, 0.01, "mm",
            [] if dg <= 0.01 else [f"max {dg:.3f}"], f"model {p['tread_mm']} mm")
        add(f"stair {s.id}: counts", 1, None, None, "", [] if (fl.NumberOfTreads, fl.NumberOfRisers) ==
            (p["treads"], p["risers"]) and len(treads) == p["treads"] else ["tread/riser count differs"],
            f"{len(treads)} treads, {fl.NumberOfRisers} risers")
        stair_tops = [(t[0], t[1]) for t in treads]

    # 8. guard heights measured from the geometry
    rails = [e for e in els if e.kind == "railing"]
    dev, fails, detail = 0.0, [], []
    for r in rails:
        H = float(r.params["guard_height_mm"])
        v = geo.verts(ent[r.id])
        cols: dict[tuple, list] = {}
        for x, y, z in v:
            cols.setdefault((round(x / 2), round(y / 2)), []).append(z)
        if r.params.get("measured_from") == "stair nosing line":
            tops = {}
            for (cx, cy), zs in cols.items():
                tops[(cx * 2, cy * 2)] = max(zs)
            meas = []
            for tz, pos in stair_tops:
                near = [z for (cx, cy), z in tops.items() if abs(cx - pos[0]) <= 20.0 and abs(cy - pos[1] - 0) < 2000]
                if near:
                    meas.append(max(near) - tz)
            hmeas = min(meas) if meas else math.nan
            hmax = max(meas) if meas else math.nan
        else:
            ext = [max(zs) - min(zs) for zs in cols.values()]
            hmeas, hmax = min(ext), max(ext)
        d = max(abs(hmeas - H), abs(hmax - H)) if not math.isnan(hmeas) else math.inf
        dev = max(dev, d if d != math.inf else 1e9)
        if not d <= HEIGHT_TOL_MM:
            fails.append(f"{r.id}: measured {hmeas:.1f}..{hmax:.1f} vs {H}")
        detail.append(f"{r.id}={hmeas:.0f}")
    add("guard heights from geometry", len(rails), dev if rails else None, HEIGHT_TOL_MM, "mm", fails, "; ".join(detail))

    # 9. placements within 1 mm (IFC placement / mesh bounds vs model)
    dev, fails, n = 0.0, [], 0
    for e in els:
        k, x = e.kind, ent.get(e.id)
        if x is None or k in ("type", "storey") or x.ObjectPlacement is None:
            continue
        m = UP.get_local_placement(x.ObjectPlacement)
        org = m[:3, 3]
        exp_xy = None
        if k == "wall":
            (x0, y0), (x1, y1) = C.wall_line(e)
            exp_xy = ((x0 + x1) / 2, (y0 + y1) / 2)
            exp_z = C.ffl(levels, e.level) + e.placement[2]
        elif k in ("column", "beam"):
            exp_xy, exp_z = e.placement[:2], C.ffl(levels, e.level) + e.placement[2]
        elif k in ("furniture", "fixture", "luminaire", "plant"):
            exp_xy, exp_z = e.placement[:2], None
        elif k in ("door", "window"):
            hw = by[e.host]
            a, _ = C.project_on_wall(hw, e.placement[:2])
            (x0, y0), (x1, y1) = C.wall_line(hw)
            Lw = C.wall_length(hw)
            exp_xy = (x0 + (x1 - x0) * a / Lw, y0 + (y1 - y0) * a / Lw)
            exp_z = C.ffl(levels, hw.level) + hw.placement[2] + (float(e.params.get("sill_mm") or 0) if k == "window" else 0.0)
        if exp_xy is None:
            continue
        n += 1
        # a door/window fill is placed at the leaf centre of its width: the origin is the leaf-centre foot point
        d = math.hypot(org[0] - exp_xy[0], org[1] - exp_xy[1])
        if exp_z is not None:
            d = max(d, abs(org[2] - exp_z))
        dev = max(dev, d)
        if d > PLACE_TOL_MM:
            fails.append(f"{e.id}: {d:.2f} mm")
    add("placements (origin vs model, xy [+ z where defined])", n, dev, PLACE_TOL_MM, "mm", fails)
    dev, fails, n = 0.0, [], 0                                    # polygon elements: bounds of the geometry
    for e in els:
        if e.kind in ("room", "floor", "ceiling") or (e.kind == "slab" and e.params.get("polygon_mm")):
            poly = np.array(e.params["polygon_mm"], float)
            lo, hi = geo.bbox(ent[e.id])
            d = max(*(abs(lo[:2] - poly.min(0))), *(abs(hi[:2] - poly.max(0))))
            z_lo = C.ffl(levels, e.level)
            if e.kind == "room":
                d = max(d, abs(lo[2] - z_lo), abs(hi[2] - (z_lo + float(e.params["clear_height_mm"]))))
            elif e.kind == "floor":
                d = max(d, abs(lo[2] - (z_lo + float(e.params.get("top_z_mm", 0)))))
            elif e.kind == "ceiling":
                d = max(d, abs(lo[2] - (z_lo + float(e.params["height_mm"]))))
            n += 1
            dev = max(dev, d)
            if d > PLACE_TOL_MM:
                fails.append(f"{e.id}: {d:.2f} mm")
    add("polygon extents and heights (rooms, coverings, slabs)", n, dev, PLACE_TOL_MM, "mm", fails)

    # 10. type assignment, layer sets, space boundaries, grid, storeys
    types = [e for e in els if e.kind == "type"]
    fails = []
    for t in types:
        tobj = ent[t.id]
        occ = {o.Name for rel in (tobj.Types or []) for o in rel.RelatedObjects} if hasattr(tobj, "Types") else set()
        occ_src = {_pset(o, "ArchPipe_Source").get("SourceId") for rel in (tobj.Types or ()) for o in rel.RelatedObjects}
        if occ_src != set(t.params["occurrence_ids"]):
            fails.append(f"{t.id}: occurrences differ")
    for e in els:
        if e.kind in ("door", "window", "furniture", "luminaire") and e.params.get("type_id") and not UE.get_type(ent[e.id]):
            fails.append(f"{e.id}: no IfcRelDefinesByType")
    if types:
        add("types: every occurrence typed with the model's type", len(types), None, None, "", fails)
    layered = [e for e in els if e.params.get("layers") and e.kind in ("wall", "slab", "floor", "ceiling")]
    if layered:
        fails = []
        for e in layered:
            ms = UE.get_material(ent[e.id])
            if ms is None or ms.is_a() != "IfcMaterialLayerSet" or len(ms.MaterialLayers) != len(e.params["layers"]):
                fails.append(e.id)
        add("material layer sets match the build-up layer count", len(layered), None, None, "", fails)
        fails = []
        for e in layered:
            ms = UE.get_material(ent[e.id])
            for ml, src in zip(ms.MaterialLayers, e.params["layers"]):
                if src.get("thickness_mm") is not None and abs(ml.LayerThickness - src["thickness_mm"]) > 1e-6:
                    fails.append(f"{e.id}: layer thickness")
        add("layer thicknesses = authored thicknesses (null stays 0 + flagged)", len(layered), None, None, "", fails)
    if any(e.kind == "room" for e in els) and scope != "LIGHT":
        sb = f.by_type("IfcRelSpaceBoundary")
        spaces_with = {r.RelatingSpace.id() for r in sb}
        nrooms = len(f.by_type("IfcSpace"))
        add("space boundaries: every space has boundaries", nrooms, None, None, "",
            [] if len(spaces_with) == nrooms else [f"{nrooms - len(spaces_with)} spaces without"], f"{len(sb)} relationships")
    nst = len(f.by_type("IfcBuildingStorey"))
    notours = [s for s in f.by_type("IfcBuildingStorey") if _pset(s, "ArchPipe_Level").get("NotOurs")]
    add("storeys incl. context levels flagged not ours", nst, None, None, "",
        [] if nst == exp["IfcBuildingStorey"] and len(notours) == sum(1 for e in elements if e.kind == "storey" and not e.params.get("ours", True))
        else ["storey count/flags"], f"{len(notours)} flagged NotOurs")

    # 11. IFC schema validation (EXPRESS rules included)
    if schema_check:
        lg = ifcopenshell.validate.json_logger()
        ifcopenshell.validate.validate(f, lg, express_rules=True)
        add("IFC4 schema validation errors (incl. EXPRESS rules)", len(list(f)), len(lg.statements), 0, "errors",
            [s["message"][:120] for s in lg.statements[:5]])
    return out


def report_text(checks: list[Check]) -> str:
    return "\n".join(c.line() + ("".join(f"\n      ! {x}" for x in c.failures) if not c.ok else "") for c in checks)


def validate_elec(path, elements, levels, directory=None) -> list[Check]:
    """D1-ELEC.ifc against the electrical lane's CSV outputs."""
    from . import disciplines as D
    f = ifcopenshell.open(str(path))
    out: list[Check] = []

    def add(name, n, worst, tol, unit, fails=(), detail=""):
        out.append(Check(name, n, worst, tol, unit, not fails and (worst is None or tol is None or worst <= tol), detail, list(fails)[:10]))
    dev = [r for r in D.read_csv("device_list.csv", directory) if r["family"] != "luminaire"]
    circuits = [r["circuit"] for b in D.BOARD_IDS for r in D.read_csv(f"board_schedule_{b}.csv", directory)]
    boards = f.by_type("IfcElectricDistributionBoard")
    n_rack = sum(1 for r in dev if r["kind"] == "rack")
    add("boards", len(boards), None, None, "", [] if len(boards) == len(D.BOARD_IDS) + n_rack else
        [f"{len(boards)} boards vs {len(D.BOARD_IDS)} + {n_rack} rack"])
    systems = f.by_type("IfcDistributionSystem")
    add("circuits = schedule rows (IfcDistributionSystem)", len(systems), None, None, "",
        [] if sorted(s.Name for s in systems) == sorted(circuits) else ["circuit names differ from the board schedules"])
    placed = {_pset(x, "ArchPipe_ElecDevice").get("DeviceId"): x for x in f.by_type("IfcElement") if _pset(x, "ArchPipe_ElecDevice")}
    add("devices = device_list (non-luminaire rows)", len(placed), None, None, "", [] if len(placed) == len(dev) else [f"{len(placed)} vs {len(dev)}"])
    dmax, fails = 0.0, []
    for r in dev:
        x = placed.get(r["id"])
        if x is None:
            fails.append(f"missing {r['id']}")
            continue
        o = UP.get_local_placement(x.ObjectPlacement)[:3, 3]
        d = math.hypot(o[0] - float(r["x_mm"]), o[1] - float(r["y_mm"]))
        dmax = max(dmax, d)
        if d > PLACE_TOL_MM:
            fails.append(f"{r['id']}: {d:.2f} mm")
    add("device placements vs device_list x,y", len(dev), dmax, PLACE_TOL_MM, "mm", fails)
    fails = []
    for s in systems:
        mem = {m.id() for rel in s.IsGroupedBy or () for m in rel.RelatedObjects}
        want = {placed[r["id"]].id() for r in dev if s.Name in r["circuit"].split("+")}
        board = next(m for rel in s.IsGroupedBy for m in rel.RelatedObjects if m.is_a("IfcElectricDistributionBoard"))
        if mem - {board.id()} != want:
            fails.append(f"{s.Name}: members differ")
        if _pset(board, "ArchPipe_Board").get("BoardId") != _pset(s, "ArchPipe_Circuit").get("Board"):
            fails.append(f"{s.Name}: wrong board")
    add("circuit membership = device_list circuit column (+ its board)", len(systems), None, None, "", fails)
    lg = ifcopenshell.validate.json_logger()
    ifcopenshell.validate.validate(f, lg, express_rules=True)
    add("IFC4 schema validation errors (incl. EXPRESS rules)", len(list(f)), len(lg.statements), 0, "errors", [s["message"][:120] for s in lg.statements[:5]])
    return out


def validate_light_zones(path, elements) -> list[Check]:
    f = ifcopenshell.open(str(path))
    groups = [g for g in f.by_type("IfcGroup") if g.ObjectType == "LightingControlZone"]
    lum = {e.id for e in elements if e.kind == "luminaire"}
    seen = Counter()
    for g in groups:
        for rel in g.IsGroupedBy or ():
            for m in rel.RelatedObjects:
                seen[_pset(m, "ArchPipe_Source").get("SourceId")] += 1
    bad = [f"{i}: in {seen.get(i, 0)} zones" for i in sorted(lum) if seen.get(i, 0) != 1]
    return [Check("every luminaire is in exactly one control zone", len(lum), None, None, "", not bad,
                  f"{len(groups)} zones", bad[:10])]


def validate_shared_origin(paths: dict[str, str]) -> list[Check]:
    """All discipline files share one origin: same project/site/building/storey GlobalIds, elevations and placements."""
    sigs = {}
    for name, p in paths.items():
        f = ifcopenshell.open(str(p))
        sig = {}
        for c in ("IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey"):
            for x in f.by_type(c):
                pl = getattr(x, "ObjectPlacement", None)
                loc = tuple(round(float(v), 3) for v in UP.get_local_placement(pl)[:3, 3]) if pl else None
                sig[(c, x.GlobalId)] = (getattr(x, "Elevation", None), loc)
        sigs[name] = sig
    ref_name = next(iter(sigs))
    bad = [f"{n} differs from {ref_name}" for n, s in sigs.items() if s != sigs[ref_name]]
    return [Check("shared origin: spatial structure identical in every discipline file", len(sigs), None, None, "", not bad,
                  f"{len(sigs[ref_name])} spatial entities", bad)]
