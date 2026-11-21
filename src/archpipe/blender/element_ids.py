"""Element identity for scene meshes (lane P2, Revit plan stage 1, row I09).

Every mesh of the built scene gets two additive fields, set by `attach` as the last step of `villa_render._build`:

    element_ids        list of design-model element ids the mesh represents ([] when none exists)
    faces_by_element   {element id: [face indices]} -- present when the faces were tracked one by one
                       (the shell), so a merged mesh can be split back per element
    element_id_basis   how the ids were obtained (see BASES)

No geometry, material or other field is touched; `strip` removes the three fields again, which is how the
scene hash is proven unchanged. Where ids come from:

  face-tracked   the daylight shell (`villa_daylight.scene`) emits faces with a material tag only. `trace_adds`
                 records which `Scene.add` call produced which faces, and `shell_owners` replays the call order of
                 `villa_daylight.scene` to name the element of every call (and, inside a wall, the door/window
                 whose opening the face fills). The replay is checked: a different call count raises.
  face-registry  later passes (construction skins, door-leaf assembly) rebuild shell faces; their faces find the
                 tracked face they were derived from (same plane within 2 mm, centre inside its box).
  source-mesh    a finish layer records the shell faces it was cut from.
  declared       the generator named the element when it made the mesh (`mesh(..., element_ids=[...])`).
  generator-name the mesh id embeds the source id the generator used (`lens-DL-lounge-01` -> `lum-DL-lounge-01`);
                 resolved against the live id set, longest match, never by position.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from contextlib import contextmanager

FIELDS = ("element_ids", "faces_by_element", "element_id_basis")
BASES = ("declared-stale", "face-tracked", "face-registry", "source-mesh", "declared", "generator-name", "unresolved")
DERIVED_FROM_SHELL = ("shell-", "door-open-", "door-leaf-", "finish-layer-")   # made from tracked daylight-shell faces
TOL = 0.002          # metres: plane / box tolerance when a pass moved a face by its 1 mm backing skin


def key(points, nd=6):
    return tuple(tuple(round(c, nd) for c in p) for p in points)


# ------------------------------------------------------------------------------------------------ shell tracing
@contextmanager
def trace_adds():
    """Record (first, last+1) face indices of every `daylight.Scene.add` call made inside the block."""
    from .. import daylight as D
    calls, original = [], D.Scene.add

    def add(self, faces):
        start = len(self.faces)
        out = original(self, faces)
        calls.append((start, len(self.faces)))
        return out
    D.Scene.add = add
    try:
        yield calls
    finally:
        D.Scene.add = original


def _plan(sp, env, columns):
    """Owner of each `Scene.add` call of `villa_daylight.scene(lay)` (no variant), in call order."""
    from ..model import spec_source as SS
    walls = SS.walls(sp)
    plan = [("site-ground", None)]
    plan += [(e["id"] if e["id"].startswith("beam-") else "ctx-" + e["id"], None)
             for e in env["elements"] if e.get("kind") == "box"]
    plan += [("column-%02d" % i, None) for i in range(len(columns))]
    plan += [("env-" + sl["id"], None) for sl in env["slabs"]]
    plan += [("env-share-front-ceiling", None), ("env-share-rear-ceiling", None)]
    plan += [(w.id, i) for i, w in enumerate(walls)]
    plan += [("stair-main", None) for _ in sp["stair"]]
    plan += [("slab-roof-%d" % i, None) for i, _ in enumerate(sp.get("roofs", []))]
    pk = sp.get("parking2")
    if pk:
        plan += [("slab-ramp", None), ("slab-deck", None)]
        plan += [("spec-ramp-infill", None)] if sp.get("infill") else []
        plan += [("spec-ramp-wall-infill-%d" % i, None) for i, _ in enumerate(sp.get("infills", []))]
        plan += [("rail-edge-%d" % i, None) for i, _ in enumerate(sp.get("rails", []))]
    return plan


def _openings(sp, lay):
    """{wall index: [(element id, kind, along0, along1, z0, z1)]} for the doors and windows each wall owns."""
    from ..concept import villa_daylight as VD
    from ..model import spec_source as SS
    wall_els = SS.walls(sp)
    door_ids = [e.id for e in SS.doors(sp, wall_els)]
    window_ids = [e.id for e in SS.windows(sp, wall_els)]
    holes = [dict(level=h["level"], x=(h["x0"] + h["x1"]) / 2, y=h["y"], width=h["x1"] - h["x0"], sill=h["sill"],
                  height=h["head"] - h["sill"], kind="hole", span=[h["wall_axis"], h["y"], h["x0"], h["x1"]])
             for h in sp.get("hatches", [])]
    cut = sp["windows"] + holes
    owner = VD._owners(sp["walls"], cut, sp["doors"])
    named = [(o, wid) for o, wid in zip(sp["windows"], window_ids)] + [(o, None) for o in holes] \
        + [(o, did) for o, did in zip(sp["doors"], door_ids)]
    out = defaultdict(list)
    index = {id(w): i for i, w in enumerate(sp["walls"])}
    for o, eid in named:
        w = owner.get(id(o))
        if w is None or eid is None:
            continue
        (xa, ya), (xb, yb) = (w["x0"], w["y0"]), (w["x1"], w["y1"])
        length = math.hypot(xb - xa, yb - ya)
        ux, uy = (xb - xa) / length, (yb - ya) / length
        along = (o["x"] - xa) * ux + (o["y"] - ya) * uy
        door = "sill" not in o
        z0 = VD.LEVEL_Z[w["level"]] + (0.0 if door else o["sill"])
        z1 = z0 + (o.get("height", 2.1) if door else o["height"])
        out[index[id(w)]].append((eid, door, (xa, ya, ux, uy), along - o["width"] / 2, along + o["width"] / 2, z0, z1))
    return out


def shell_owners(shell, calls, sp, lay):
    """Element id of every face of the daylight scene `shell` (list parallel to shell.faces)."""
    from .. import villa_env as E
    plan = _plan(sp, E.spec(), E.COLUMNS)
    if len(plan) != len(calls):
        raise ValueError("daylight shell has %d Scene.add calls, the identity replay expects %d: "
                         "villa_daylight.scene changed; update blender/element_ids._plan" % (len(calls), len(plan)))
    openings = _openings(sp, lay)
    owners = [None] * len(shell.faces)
    for (eid, wall_index), (a, b) in zip(plan, calls):
        for i in range(a, b):
            owners[i] = eid
            f = shell.faces[i]
            if wall_index is None or f.material not in ("door", "glass"):
                continue
            c = [sum(p[k] for p in f.points) / len(f.points) for k in range(3)]
            for oid, door, (xa, ya, ux, uy), u0, u1, z0, z1 in openings.get(wall_index, ()):
                u = (c[0] - xa) * ux + (c[1] - ya) * uy
                if u0 - TOL <= u <= u1 + TOL and z0 - TOL <= c[2] <= z1 + TOL:
                    owners[i] = oid
                    break
    return owners


# ------------------------------------------------------------------------------------------------ face registry
class Registry:
    """Tracked shell faces: exact lookup by vertices, nearest-plane lookup for faces a pass derived from them."""

    def __init__(self):
        self.exact, self.entries, self.grid, self.conflicts = {}, [], defaultdict(list), []

    def add(self, points, eid):
        k = key(points)
        if k in self.exact:
            if self.exact[k] != eid:
                self.conflicts.append((self.exact[k], eid))
            return
        self.exact[k] = eid
        n = _normal(points)
        lo = [min(p[i] for p in points) - TOL for i in range(3)]
        hi = [max(p[i] for p in points) + TOL for i in range(3)]
        entry = (eid, n, sum(a * b for a, b in zip(n, points[0])), lo, hi)
        self.entries.append(entry)
        for cell in _cells(lo, hi):
            self.grid[cell].append(entry)

    def lookup(self, points):
        found = self.exact.get(key(points))
        if found:
            return found
        c = [sum(p[i] for p in points) / len(points) for i in range(3)]
        best = None
        for eid, n, d, lo, hi in self.grid.get(_cell(c), ()):
            if all(lo[i] <= c[i] <= hi[i] for i in range(3)):
                gap = abs(sum(a * b for a, b in zip(n, c)) - d)
                vol = math.prod(hi[i] - lo[i] for i in range(3))
                if gap <= TOL and (best is None or (gap, vol) < best[0]):
                    best = ((gap, vol), eid)
        return best[1] if best else None


CELL = 0.5


def _cell(p):
    return tuple(int(math.floor(v / CELL)) for v in p)


def _cells(lo, hi):
    a, b = _cell(lo), _cell(hi)
    return [(x, y, z) for x in range(a[0], b[0] + 1) for y in range(a[1], b[1] + 1) for z in range(a[2], b[2] + 1)]


def _normal(points):
    a = [0.0, 0.0, 0.0]
    for p, q in zip(points, list(points[1:]) + list(points[:1])):
        a[0] += (p[1] - q[1]) * (p[2] + q[2])
        a[1] += (p[2] - q[2]) * (p[0] + q[0])
        a[2] += (p[0] - q[0]) * (p[1] + q[1])
    n = math.sqrt(sum(v * v for v in a)) or 1.0
    return tuple(v / n for v in a)


# ------------------------------------------------------------------------------------------------ name rules
def _longest(mid, ids, prefix, strip=""):
    """Longest model id `prefix+X` such that the mesh id is X or starts with X + '-'."""
    stem = mid[len(strip):] if strip and mid.startswith(strip) else mid
    best = None
    for eid in ids:
        if eid.startswith(prefix):
            x = eid[len(prefix):]
            if (stem == x or stem.startswith(x + "-")) and (best is None or len(eid) > len(best)):
                best = eid
    return best


def _luminaire(mid, ids):
    best = None
    for eid in ids:
        if eid.startswith("lum-"):
            x = eid[4:]
            if (mid.endswith("-" + x) or ("-" + x + "-") in mid) and (best is None or len(eid) > len(best)):
                best = eid
    return best


def resolve_name(mid, ids):
    """Element id a generator-named mesh stands for, or None."""
    if mid.startswith("furn-"):
        return _longest(mid, ids, "furn-", "furn-") or _longest(mid, ids, "joinery-", "furn-")
    lum = _luminaire(mid, ids)
    if lum:
        return lum
    if mid.startswith("mirror-"):
        return mid[7:] and ("furn-" + mid[7:] if ("furn-" + mid[7:]) in ids else None)
    if mid.startswith("detail-"):
        found = _longest(mid, ids, "fixture-", "detail-") or _longest(mid, ids, "wetzone-", "detail-")
        if found:
            return found
        if mid.startswith("detail-stair-glass"):
            return "rail-stair-open-glass"
        if mid.startswith(("detail-stair-wall-stringer", "detail-stair-wall-rail", "detail-stair-wall-plate",
                           "detail-stair-wall-handrail")):
            return "rail-stair-wall-handrail"
        if mid.startswith("detail-stair-guard"):
            return "rail-gf-stair-void"
        if mid.startswith("detail-stair-open-stringer"):
            return "stair-main"
    if mid.startswith("dress-pillow-"):
        return _longest("furn-" + mid[13:], ids, "furn-", "furn-")
    # landscape parts: climber branches / loquat wires belong to their plant; edging, soil and stone to their bed/path
    plantish = re.sub(r"-(body|rim|soil)$", "", mid.replace("-branches", "").replace("-wires", "-plant")
                      .replace("-pot-planter-", "-pot-"))
    for prefix in ("plant-", "prop-", "garden-"):
        for strip in ("", "landscape-", "landscape-g6-"):
            found = _longest(plantish, ids, prefix, strip)
            if found:
                return found
    for strip, prefix in (("landscape-edging-", "garden-bed-"), ("landscape-soil-", "garden-bed-"),
                          ("landscape-stone-", "garden-path-")):
        found = _longest(mid, ids, prefix, strip) if mid.startswith(strip) else None
        if found:
            return found
    if mid.startswith(("floor-", "ceiling-")):
        room = "room-" + mid.split("-", 1)[1]
        return room if room in ids else None
    return None


# ------------------------------------------------------------------------------------------------ attach / strip
def declare(ranges):
    """mesh() kwargs for a mesh whose faces were appended in runs: [(first, end, element id)] -> ids + faces_by_element."""
    fbe = {}
    for a, b, eid in ranges:
        if eid and b > a:
            fbe.setdefault(eid, []).extend(range(a, b))
    return dict(element_ids=list(fbe), faces_by_element=fbe) if fbe else {}


def strip(mesh):
    for f in FIELDS:
        mesh.pop(f, None)
    return mesh


def without_ids(scene):
    """The scene as the pre-identity consumers know it: same objects, meshes minus the identity fields.

    `exposure_groups.transport_digest` (frozen measurements) and the appearance records hash whole mesh dicts, so
    every consumer that checks them is handed this view. It costs one shallow copy per mesh, and only when needed."""
    if not any(f in m for m in scene.get("meshes", ()) for f in FIELDS):
        return scene
    return dict(scene, meshes=[strip(dict(m)) for m in scene["meshes"]])


def attach(scene, registry, ids, declared_by_mesh=None):
    """Add the identity fields to every mesh of `scene` (after all passes). `ids`: set of live model ids."""
    by_mesh = {m["id"]: m for m in scene["meshes"]}
    declared_by_mesh = declared_by_mesh or {}
    garment_owner = {g["id"] + "-": "furn-" + g["wardrobe_id"] for g in scene.get("garment_modules", [])
                     if "furn-" + g["wardrobe_id"] in ids}
    partners = Counter(w.get("partner") for w in scene.get("dressing_wardrobes", []))
    garment_owner.update({"dress-%s-" % w["partner"]: "furn-" + w["id"] for w in scene.get("dressing_wardrobes", [])
                          if partners[w.get("partner")] == 1 and "furn-" + w["id"] in ids})   # shelf boxes, shoes
    for m in scene["meshes"]:
        named = declared_by_mesh.get(m["id"], {})
        declared = named.get("element_ids")
        if named.get("faces_by_element"):
            m["faces_by_element"] = named["faces_by_element"]
        faces = m["faces"]
        tracked = None
        if m.get("group") in ("shell", "context") and not declared and m["id"].startswith(DERIVED_FROM_SHELL):
            tracked = defaultdict(list)
            if m.get("source_mesh") and m.get("source_faces"):
                src = [registry.lookup(f) for f in m["source_faces"]]
                owners = sorted({e for e in src if e})
                if owners:                                # all faces of the finish layer sit on its source wall
                    tracked = {owners[0]: list(range(len(faces)))} if len(owners) == 1 else None
                    basis = "source-mesh"
                    if tracked is None:                   # several hosts: assign each face by proximity
                        tracked = defaultdict(list)
                        basis = "face-registry"
                        for i, f in enumerate(faces):
                            e = registry.lookup(f)
                            if e:
                                tracked[e].append(i)
                else:
                    tracked, basis = None, None
            else:
                basis = "face-tracked"
                for i, f in enumerate(faces):
                    e = registry.lookup(f)
                    if e:
                        tracked[e].append(i)
                if len(tracked) and any(registry.exact.get(key(f)) is None for f in faces):
                    basis = "face-registry"
            if tracked:
                m["element_ids"] = list(tracked)
                m["faces_by_element"] = {e: v for e, v in tracked.items()}
                m["element_id_basis"] = basis
                continue
        if declared:
            m["element_ids"] = list(declared)
            m["element_id_basis"] = "declared"
            fbe = m.get("faces_by_element")
            if fbe and any(i >= len(faces) for v in fbe.values() for i in v):
                del m["faces_by_element"]               # a pass rebuilt the faces: the indices no longer apply
                m["element_id_basis"] = "declared-stale"
            continue
        found = resolve_name(m["id"], ids) or next((o for p, o in garment_owner.items() if m["id"].startswith(p)), None)
        if found is None and m.get("source_mesh") in by_mesh:
            found = (by_mesh[m["source_mesh"]].get("element_ids") or [None])[0]
        m["element_ids"] = [found] if found else []
        m["element_id_basis"] = "generator-name" if found else "unresolved"
    return scene


# ------------------------------------------------------------------------------------------------ coverage
def covered_faces(mesh):
    if mesh.get("faces_by_element"):
        return sum(len(v) for v in mesh["faces_by_element"].values())
    return len(mesh["faces"]) if mesh.get("element_ids") else 0


def coverage(meshes, model_ids=None):
    """{group: dict(meshes, faces, with_id, with_model_id)}; `model_ids` (set) separates design-model ids."""
    out = defaultdict(lambda: Counter())
    for m in meshes:
        g, n = out[m["group"]], len(m["faces"])
        g["meshes"] += 1
        g["faces"] += n
        g["with_id"] += covered_faces(m)
        if model_ids is not None:
            inside = [e for e in m.get("element_ids", []) if e in model_ids]
            if m.get("faces_by_element"):
                g["with_model_id"] += sum(len(v) for e, v in m["faces_by_element"].items() if e in model_ids)
            elif inside:
                g["with_model_id"] += n
    return {k: dict(v) for k, v in out.items()}


def faces_of(scene, element_id):
    """[(mesh, [face points])] of an element: the lookup an independent check uses."""
    out = []
    for m in scene["meshes"]:
        if element_id not in m.get("element_ids", ()):
            continue
        fbe = m.get("faces_by_element")
        idx = fbe[element_id] if fbe else range(len(m["faces"]))
        out.append((m, [m["faces"][i] for i in idx]))
    return out


# Meshes with no design-model element, and why. Checked by the coverage report: an unresolved mesh must match one.
NO_MODEL_ELEMENT = (
    ("rug-", "rugs are not elements of the design model"),
    ("landscape-g6-pergola", "garden structures (pergola, seating, centrepiece bowl, swing, trellis, troughs, pots, "
                             "stepping stones, edging, bench slabs, lawn, gravel) are not elements of the design model"),
    ("landscape-g6-", "garden structures are not elements of the design model"),
    ("landscape-north-", "garden structures are not elements of the design model"),
    ("landscape-top-", "garden structures are not elements of the design model"),
    ("landscape-door-pot-", "garden structures are not elements of the design model"),
    ("landscape-trellis-", "garden structures are not elements of the design model"),
    ("landscape-grass-", "lawn is not an element of the design model"),
    ("landscape-gravel-", "gravel is not an element of the design model"),
    ("landscape-tree-pit", "tree pits are not elements of the design model"),
    ("landscape-accent-bed", "no matching garden-bed element"),
    ("landscape-climber-", "no plant element for this climber (only the east climber is in the design model)"),
    ("garden-uplight-", "garden uplights are not luminaire elements of the design model"),
    ("detail-vent-", "ventilation grilles and valves are not elements of the design model"),
    ("detail-curtain-", "curtain tracks are not elements of the design model (curtains are a scene contract)"),
    ("detail-hatch-", "the kitchen pass-through hatch is not an element of the design model"),
    ("dress-", "wardrobe contents with no unique wardrobe owner"),
)


def no_model_reason(mesh_id):
    return next((why for prefix, why in NO_MODEL_ELEMENT if mesh_id.startswith(prefix)), None)


def main(argv=None):
    """python -m archpipe.blender.element_ids SCENE.json [--model D1-elements.json]: coverage table and unexplained gaps."""
    import argparse
    import json
    from pathlib import Path
    ap = argparse.ArgumentParser(description=main.__doc__)
    ap.add_argument("scene", type=Path)
    ap.add_argument("--model", type=Path, default=Path(__file__).resolve().parents[1] / "model/data/d1-elements.json")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    scene = json.loads(args.scene.read_text())
    data = json.loads(args.model.read_text())
    model_ids = {e["id"] for e in (data["elements"] if isinstance(data, dict) else data)}
    table = coverage(scene["meshes"], model_ids)
    unexplained = [m["id"] for m in scene["meshes"] if covered_faces(m) < len(m["faces"]) and not no_model_reason(m["id"])]
    stale = sorted({e for m in scene["meshes"] for e in m.get("element_ids", ())
                    if e not in model_ids and not e.startswith(("env-", "spec-", "site-"))})
    report = dict(coverage=table, unexplained_uncovered_meshes=unexplained, ids_not_in_model_snapshot=stale)
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.out:
        args.out.write_text(text + "\n")
    return 1 if unexplained else 0


if __name__ == "__main__":
    raise SystemExit(main())
