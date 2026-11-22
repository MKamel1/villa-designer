"""landscape-layout/1  ->  Scene (3D garden geometry with `ld-*` ids). Concept-agnostic: reads only the layout and the LDL plant data."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from shapely.geometry import box as sbox
from shapely.ops import unary_union

from . import elements as E
from . import planting as PL
from . import policy as P

R = E.R


@dataclass
class Scene:
    objects: list
    context: list
    schedule: list
    warnings: list
    age: int | None
    ground_z: float
    source: str = ""
    spec: dict = field(default_factory=dict)

    def select(self, state="closed"):
        return [o for o in self.objects if o.state in (None, state)]

    def by_id(self, oid, state="closed"):
        return next(o for o in self.select(state) if o.id == oid)


def _uid(seen, base):
    n = seen.get(base, 0)
    seen[base] = n + 1
    return base if n == 0 else "%s-r%d" % (base, n)


def _dist_pt_rect(pt, r):
    dx = max(r[0] - pt[0], 0, pt[0] - r[2])
    dy = max(r[1] - pt[1], 0, pt[1] - r[3])
    return math.hypot(dx, dy)


def load_layout(path):
    d = json.loads(Path(path).read_text())
    if d.get("schema") != "landscape-layout/1":
        raise ValueError("not a landscape-layout/1 file: %r" % d.get("schema"))
    return d


def build_scene(layout, age=P.AGE_YEARS, ground_z=None, source=""):
    """`age` = years since planting; None builds the plants at maturity."""
    g = ground_z if ground_z is not None else (layout.get("meta") or {}).get("ground_z", P.GROUND_Z)
    objs, warns, sched = [], [], []
    seen = {}
    feats = layout.get("features", [])
    pitf = next((f for f in feats if f.get("kind") == "firepit"), None)
    if pitf and not pitf.get("flush", True):
        warns.append("firepit %s is not flush: only the flush fire pit is built, it is skipped" % pitf["id"]); pitf = None
    pit = (*pitf["center"], pitf["diameter_m"]) if pitf else None
    path_rects = [R(p["rect"]) for p in layout.get("paths", []) if "rect" in p]
    for p in layout.get("paths", []):
        if "rect" not in p:
            warns.append("path %s has no rect (polyline paths are not built)" % p["id"])
    for k in ("steps", "level_changes"):
        if layout.get(k):
            warns.append("%s: %d entries not built (layout/1 gives no riser height or fall direction)" % (k, len(layout[k])))

    # --- hardscape
    paved = []
    for pa in layout.get("paved_areas", []):
        r = R(pa["rect"]); paved.append(r)
        mine = [q for q in path_rects if sbox(*q).intersects(sbox(*r)) and sbox(*q).intersection(sbox(*r)).area > 1e-6]
        objs.append(E.paving("ld-" + _uid(seen, pa["id"]), pa["id"], r, g, mine, pit))
    for p in layout.get("paths", []):
        if "rect" in p:
            objs.append(E.path("ld-" + _uid(seen, p["id"]), p["id"], R(p["rect"]), g, p.get("class", "path")))
    beds = []
    for gr in layout.get("planting_groups", []):
        beds.append(R(gr["rect"]))
        objs.append(E.bed("ld-" + gr["id"], gr["id"], R(gr["rect"]), g, gr.get("role", "bed")))
    # --- features
    water = []
    for f in feats:
        k = f.get("kind")
        if k == "pond":
            water.append(R(f["rect"])); objs += E.pond("ld-" + f["id"], f["id"], f, g)
        elif k == "firepit" and pitf:
            objs += E.firepit("ld-" + f["id"], f["id"], f, g)
        elif k == "bbq":
            objs.append(E.bbq("ld-" + f["id"], f["id"], f["rect"], g))
        elif k == "herb_bed":
            if R(f["rect"]) in beds:
                next(o for o in objs if o.layout_id and o.kind == "bed" and R(f["rect"]) == o.footprint).meta["also"] = f["id"]
            else:
                beds.append(R(f["rect"])); objs.append(E.bed("ld-" + f["id"], f["id"], R(f["rect"]), g, "herb"))
        else:
            warns.append("feature %s kind %r not built" % (f.get("id"), k))
    # --- seating
    sw = (layout.get("seatwalls") or [{}])[0].get("height_mm", 450) / 1000
    bench_rects = []
    for s in layout.get("seating", []):
        bench_rects.append(R(s["rect"]))
        objs.append(E.bench("ld-" + s["id"], s["id"], R(s["rect"]), g, s.get("seats", 0), sw))
    for t in layout.get("tables", []):
        objs.append(E.table("ld-" + t["id"], t["id"], t["center"], t["size_m"], g, t.get("seats", 0)))
        objs += E.chairs_for(t["id"], t["center"], t["size_m"], t.get("seats", 0), g)
    # --- ground: gravel zones minus built surfaces; whatever is left inside the garden bounds is unspecified ground
    built = unary_union([sbox(*r) for r in paved + beds + water] + [sbox(*r) for r in bench_rects]) if (paved or beds or water or bench_rects) else sbox(0, 0, 0, 0)
    gz = unary_union([sbox(*R(z["rect"])) for z in layout.get("zones", []) if z.get("surface") == "gravel" and "rect" in z] or [sbox(0, 0, 0, 0)])
    gravel = gz.difference(built)
    comps = list(gravel.geoms) if hasattr(gravel, "geoms") else [gravel]
    for i, c in enumerate([c for c in comps if c.area > 1e-4]):
        objs.append(E.surface("ld-gravel-%d" % i, "gravel", "gravel surface (layout zone surface = gravel; depth %d mm ASSUMED)" % int(P.GRAVEL_DEPTH * 1000), "gravel", c, g - P.GRAVEL_DEPTH, g,
                              layout_id="zones:gravel"))
    allr = [sbox(*r) for r in paved + beds + water + bench_rects] + [sbox(*R(z["rect"])) for z in layout.get("zones", []) if "rect" in z]
    blds = unary_union([sbox(*R(b)) for b in layout.get("buildings", [])] or [sbox(0, 0, 0, 0)])
    covered = unary_union([sbox(*r) for r in paved + beds + water + bench_rects] + [gravel])
    merged = unary_union([a.buffer(0.35) for a in allr]).buffer(-0.35 + 0.0)
    regions = [sbox(*c.bounds) for c in (merged.geoms if hasattr(merged, "geoms") else [merged]) if not c.is_empty]
    rest = unary_union(regions).difference(covered).difference(blds)
    for i, c in enumerate([c for c in (rest.geoms if hasattr(rest, "geoms") else [rest]) if c.area > 1e-3]):
        objs.append(E.surface("ld-ground-%d" % i, "ground", "ground with NO built surface in the layout (a zone says paving/other or nothing is drawn): shown as bare compacted ground; a gap in the concept to close", "ground", c,
                              g - P.GRAVEL_DEPTH, g, layout_id="gap"))
    # --- walls, screens, pergolas
    for w in layout.get("walls", []):
        objs.append(E.wall("ld-" + w["id"], w["id"], R(w["rect"]), w["height_m"], g))
    screens = []
    for s in layout.get("screens", []):
        if s.get("kind") == "trellis":
            screens.append((R(s["rect"]), s["height_m"], "ld-" + s["id"]))
            objs.append(E.trellis("ld-" + s["id"], s["id"], R(s["rect"]), s["height_m"], g))
        else:
            warns.append("screen %s kind %r not built" % (s["id"], s.get("kind")))
    avoid = list(bench_rects) + [R(f["rect"]) for f in feats if "rect" in f] + [R(o["rect"]) for o in layout.get("obstacles", []) if o["id"].startswith("pot")]
    avoid += [(t["center"][0] - t["size_m"][0] / 2, t["center"][1] - t["size_m"][1] / 2, t["center"][0] + t["size_m"][0] / 2, t["center"][1] + t["size_m"][1] / 2) for t in layout.get("tables", [])]
    avoid += [(t["center"][0] - .2, t["center"][1] - .2, t["center"][0] + .2, t["center"][1] + .2) for t in layout.get("trees", [])]
    for c in layout.get("canopies", []):
        if c.get("kind") == "pergola":
            objs.append(E.pergola("ld-" + c["id"], c["id"], R(c["rect"]), c["height_m"], g, avoid))
        else:
            warns.append("canopy %s kind %r not built" % (c["id"], c.get("kind")))
    # --- pot
    pot_ids = {}
    for o in layout.get("obstacles", []):
        if o["id"].startswith("pot"):
            po = E.pot("ld-" + o["id"], o["id"], o["rect"], g)
            objs.append(po)
            pot_ids[o["id"]] = (po, R(o["rect"]))
    # --- planting
    hard = [(R(b), "bench") for b in bench_rects] + [(R(f["rect"]), f["id"]) for f in feats if "rect" in f and f.get("kind") in ("bbq", "pond")]
    hard += [(R(o["rect"]), o["id"]) for o in layout.get("obstacles", []) if o["id"].startswith("pot")]
    hard += [((t["center"][0] - t["size_m"][0] / 2, t["center"][1] - t["size_m"][1] / 2, t["center"][0] + t["size_m"][0] / 2, t["center"][1] + t["size_m"][1] / 2), t["id"]) for t in layout.get("tables", [])]
    if pitf:
        hard.append(((pitf["center"][0] - pitf["diameter_m"] / 2, pitf["center"][1] - pitf["diameter_m"] / 2, pitf["center"][0] + pitf["diameter_m"] / 2, pitf["center"][1] + pitf["diameter_m"] / 2), pitf["id"]))
    walls_r = [R(w["rect"]) for w in layout.get("walls", [])] + [sc[0] for sc in screens]
    for t in layout.get("trees", []):
        o, row = PL.plant_objects("ld-" + t["id"], t["species"], t, t["center"], age, g, form=t.get("form"))
        o.meta.update(layout_spread=t.get("mature_spread_m"), at=t["center"], layout_id=t["id"])
        objs.append(o); sched.append(row)
    for gr in layout.get("planting_groups", []):
        for i, pl in enumerate(gr["plants"]):
            sp = pl["species"]
            f = PL.species_facts(sp)
            clb = None
            if PL.is_climber(sp):
                near = [(d, sc) for sc in screens for d in [_dist_pt_rect(pl["at"], sc[0])] if d <= 0.6]
                if near:
                    sr, sh, sid = min(near, key=lambda a: a[0])[1]
                    if (sr[2] - sr[0]) >= (sr[3] - sr[1]):
                        sgn = 1 if pl["at"][1] > (sr[1] + sr[3]) / 2 else -1
                        clb = ((sr[3] if sgn > 0 else sr[1]), sgn, sh)
                    else:
                        warns.append("climber %s: y-long screen not supported, drawn as a mound" % sp)
            oid = "ld-plant-%s-%02d" % (gr["id"], i)
            blocker = next((n for r, n in hard if r[0] <= pl["at"][0] <= r[2] and r[1] <= pl["at"][1] <= r[3]), None)
            if blocker:
                sched.append(dict(id=oid, species=sp, status="omitted", reason="the layout puts this plant inside %s; not built (layout conflict, reported)" % blocker))
                warns.append("%s (%s) at %s lies inside %s: omitted" % (oid, sp, pl["at"], blocker)); continue
            o, row = PL.plant_objects(oid, sp, pl, pl["at"], age, g, climbing=clb, form=pl.get("form"))
            o.meta.update(layout_spread=pl.get("spread_m"), at=pl["at"], layout_id=gr["id"], climbing=bool(clb))
            objs.append(o); sched.append(row)
    for o in layout.get("obstacles", []):
        if o["id"].startswith("pot-"):
            slug = next((s for s in PL._plants() if s.startswith(o["id"].split("-", 2)[-1])), None)
            if slug is None:
                warns.append("pot %s: no species" % o["id"]); continue
            po, r = pot_ids[o["id"]]
            top = g + P.POT["h"] - P.POT["soil_below_rim"]
            ov = (P.POT["plant_h"], 1.2, "ASSUMED: potted size is a GAP in LDL, %.1f m" % P.POT["plant_h"])
            c = ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
            room = min([_dist_pt_rect(c, w) for w in walls_r] or [9.9]) - 0.05          # a pot plant is restrained to the clear room round it
            pobj, row = PL.plant_objects(po.id + "-plant", slug, {}, c, age, g, base_z=top, support=(po.id,), size_override=ov, form="small_tree", max_spread=2 * room)
            pobj.meta.update(layout_id=o["id"], at=((r[0] + r[2]) / 2, (r[1] + r[3]) / 2), layout_spread=None)
            objs.append(pobj); sched.append(row)
    ctx = [dict(id="ctx-building-%d" % i, rect=list(R(b)), z0=g, z1=g + P.BUILDING_H,
                label="context: existing house massing, height ASSUMED %.0f m (footprints carry none)" % P.BUILDING_H) for i, b in enumerate(layout.get("buildings", []))]
    ids = [o.id for o in objs if o.state is None]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise ValueError("duplicate element ids: %s" % sorted(dup))
    return Scene(objs, ctx, sched, warns, age, g, source)
