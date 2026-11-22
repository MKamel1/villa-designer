"""K17: the same crossing checks on the IFC export, read back through IfcOpenShell's geometry kernel (a second, separate
kernel and a separate build path from the scene). IFC z carries the Revit datum (scene z + 1.2 m); it is shifted back so
reports share one datum with the scene."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from . import checks as C
from .world import Element, World, sha256_file

CLASSES = ("IfcWall", "IfcColumn", "IfcBeam", "IfcSlab", "IfcStairFlight", "IfcDoor", "IfcWindow")
DATUM_SHIFT = -1.2       # IFC z -> scene z (ArchPipe_Source 'Datum': 'Revit datum: z = scene z + 1200 mm')


def load_ifc_world(path, hash_it=True) -> World:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    import ifcopenshell
    import ifcopenshell.geom
    f = ifcopenshell.open(str(path))
    s = ifcopenshell.geom.settings()
    s.set("use-world-coords", True)
    els, bad = {}, []
    for cls in CLASSES:
        for p in f.by_type(cls):
            try:
                sh = ifcopenshell.geom.create_shape(s, p)
            except Exception as e:        # a product the kernel cannot tessellate is reported, never skipped silently
                bad.append((p.Name, str(e)[:80]))
                continue
            v = np.array(sh.geometry.verts, float).reshape(-1, 3)
            v[:, 2] += DATUM_SHIFT
            fa = np.array(sh.geometry.faces, int).reshape(-1, 3)
            name = p.Name or p.GlobalId
            name = "stair-main" if name == "stair-main-flight" else name
            els[name] = Element(name, [(name, "ifc", None, cls, v[fa])])
    w = World(els, [], str(path), sha256_file(path) if hash_it else "")
    w.kernel_failures = bad
    return w


def ifc_clashes(w: World):
    """K01 + K02 + K03 on the IFC geometry; the findings carry check ids K17-K01 / K17-K02 / K17-K03."""
    out = []
    for fn, tag in ((C.k01_stair_structure, "K01"), (C.k02_wall_slab, "K02"), (C.k03_opening_column, "K03")):
        for f in fn(w):
            f.check = f"K17-{tag}"
            out.append(f)
    return out


def agreement(scene_findings, ifc_findings):
    """Per clash pair: scene vs IFC failing or not, with both depths. Pairs that fail in either are listed."""
    def key(f):
        return tuple(sorted(f.element_ids)) if f.element_ids else None
    s = {key(f): f for f in scene_findings if f.status == "fail" and key(f)}
    i = {key(f): f for f in ifc_findings if f.status == "fail" and key(f)}
    rows = []
    for k in sorted(set(s) | set(i)):
        a, b = s.get(k), i.get(k)
        rows.append(dict(pair=" x ".join(k), scene="fail" if a else "quiet", scene_mm=a.achieved if a else None,
                         ifc="fail" if b else "quiet", ifc_mm=b.achieved if b else None, agree=bool(a) == bool(b)))
    return rows


def mutate_ifc_wall_taller(src, dst, wall_name="wall-B-int-11", dz=0.7):
    """Seed an IFC defect for the K17 mutation: the named wall's extrusion is lengthened by `dz` metres (through the ramp)."""
    import ifcopenshell
    import ifcopenshell.util.unit as U
    f = ifcopenshell.open(str(src))
    scale = U.calculate_unit_scale(f)          # metres per file length unit (0.001 for a millimetre file)
    w = next(p for p in f.by_type("IfcWall") if p.Name == wall_name)
    n = 0
    for rep in w.Representation.Representations:
        for it in rep.Items:
            if it.is_a("IfcExtrudedAreaSolid"):
                it.Depth = it.Depth + dz / scale
                n += 1
    if not n:
        raise RuntimeError(f"{wall_name}: no extruded solid to lengthen")
    f.write(str(dst))
    return dst
