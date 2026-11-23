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
from . import outdoor as OD
from . import policy as P
from . import context as CX

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
    season: str = "summer"
    visualisation_only: bool = False            # a preview scene that carries the sister-plot garden: never schedules, exports or production

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



def pit_half(layout, pitf):
    """(axis, sign) of the half of a shared-boundary pit that is ours, or None when the pit is wholly ours. Ours = the side where the garden's paving lies."""
    if not pitf.get("shared_boundary"):
        return None
    cx, cy = pitf["center"]
    rs = [R(a["rect"]) for a in layout.get("paved_areas", [])] + [R(z["rect"]) for z in layout.get("zones", []) if "rect" in z]
    if not rs:
        return None
    x0, y0, x1, y1 = min(r[0] for r in rs), min(r[1] for r in rs), max(r[2] for r in rs), max(r[3] for r in rs)
    d = {("y", 1): cy - y0, ("y", -1): y1 - cy, ("x", 1): cx - x0, ("x", -1): x1 - cx}      # distance from the pit to each edge of the garden
    (ax, sg), dist = min(d.items(), key=lambda kv: abs(kv[1]))
    if abs(dist) > 0.05:
        return None
    return (ax, sg)


def grids_for(paved, paths, pitf):
    """[(rect, along)] of the paving and path rects under the pit, largest overlap first: the grids its cover continues."""
    cx, cy = pitf["center"]
    r = pitf["diameter_m"] / 2
    disc = sbox(cx - r, cy - r, cx + r, cy + r)
    rows = [(q, "x") for q in paved] + [(q, "x" if (q[2] - q[0]) >= (q[3] - q[1]) else "y") for q in paths]
    rows = [(q, a) for q, a in rows if sbox(*q).intersection(disc).area > 1e-6]
    return sorted(rows, key=lambda qa: -sbox(*qa[0]).intersection(disc).area)


def koi(f, outdoor, g, warns, sched):
    """Koi at the layout stocking count, if a graded free koi asset exists. Otherwise none, said so (the schedule carries the row)."""
    n = f.get("koi_count") or 0
    if not n:
        return []
    a = outdoor.get("koi")
    if not a:
        sched.append(dict(id="ld-%s-koi" % f["id"], species="koi", status="none", reason="no free koi asset of grade B or better on this machine; the pond is built empty (stocking %d koi is in the layout)" % n))
        warns.append("pond %s: %d koi stocked in the layout, no free koi asset: drawn empty" % (f["id"], n))
        return []
    W, wl, wp, d = E.pond_profile(f, g)
    out = []
    L = f.get("koi_adult_length_cm", 50) / 100.0
    s_mid = d["entry_run"] + d["shelf"] + (W - d["entry_run"] - d["shelf"]) / 2
    zc = wl - 0.5 * d["trench_depth"] * 0.8 - 0.1
    across, _ = E.pond_axes(f)
    for i in range(n):
        u = (i + 0.5) / n
        x, y = E.pond_point(f, s_mid, u)
        head = math.radians((0 if across == "y" else 90) + (180 if i % 2 else 0))       # swimming along the pond, alternate directions
        o = OD.fish_obj("ld-%s-koi-%d" % (f["id"], i), a, (x, y, zc), L, (math.cos(head), math.sin(head)))
        o.rests_on = ("ld-" + f["id"], "ld-%s-water" % f["id"])
        out.append(o)
        sched.append(dict(id=o.id, species="koi", status="asset", asset=a["id"], grade=a["grade"], licence=a["licence"], length_m=L))
    return out


def climb_target(at, structs, g, blockers=(), reach=P.CLIMBER["reach"]):
    """Nearest wall/screen rect within `reach` of a climber -> dict(axis the panel runs along, face coordinate, side, span, max height); None when none is near."""
    best = min(((_dist_pt_rect(at, r), r, h, sid) for r, h, sid in structs), key=lambda a: a[0], default=None)
    if best is None or best[0] > reach:
        return None
    _, r, h, sid = best
    if (r[2] - r[0]) >= (r[3] - r[1]):
        sgn = 1 if at[1] > (r[1] + r[3]) / 2 else -1
        face, axis, span = (r[3] if sgn > 0 else r[1]), "x", (r[0], r[2])
        near = [(b[0], b[2]) for b in blockers if b[1] < face + 0.1 and b[3] > face - 0.1]
        c = at[0]
    else:
        sgn = 1 if at[0] > (r[0] + r[2]) / 2 else -1
        face, axis, span = (r[2] if sgn > 0 else r[0]), "y", (r[1], r[3])
        near = [(b[1], b[3]) for b in blockers if b[0] < face + 0.1 and b[2] > face - 0.1]
        c = at[1]
    lo, hi = span                                   # the panel stops at a bench / pot / table that stands against the face: it climbs the free stretch round the plant
    for a, b in near:
        if b <= c:
            lo = max(lo, b)
        elif a >= c:
            hi = min(hi, a)
    return dict(axis=axis, face=face, sgn=sgn, span=(lo, hi), max_h=h, on=sid, at=at, keepouts=[tuple(b) for b in blockers])


def load_layout(path):
    d = json.loads(Path(path).read_text())
    if d.get("schema") != "landscape-layout/1":
        raise ValueError("not a landscape-layout/1 file: %r" % d.get("schema"))
    return d


def build_scene(layout, age=P.AGE_YEARS, ground_z=None, source="", pergolas=False, season="summer", outdoor=None, site_context=True, star_jasmine=True):
    """`age` = years since planting; None builds the plants at maturity. `pergolas=False`: the client replaced pergolas by pruned shade trees (2026-11-22), so a
    pergola canopy in the layout is reported and not built. `site_context` adds the neighbour/street/fence massing of villa_env (previews of OUR design). `outdoor` = graded outdoor furniture/koi table (outdoor.load()); None loads the shipped one."""
    outdoor = OD.load() if outdoor is None else outdoor
    g = ground_z if ground_z is not None else (layout.get("meta") or {}).get("ground_z", P.GROUND_Z)
    objs, warns, sched = [], [], []
    seen = {}
    feats = layout.get("features", [])
    pitf = next((f for f in feats if f.get("kind") == "firepit"), None)
    if pitf and not pitf.get("flush", True):
        warns.append("firepit %s is not flush: only the flush fire pit is built, it is skipped" % pitf["id"]); pitf = None
    pit = (*pitf["center"], pitf["diameter_m"]) if pitf else None
    half = pit_half(layout, pitf) if pitf else None
    ponds = [R(f["rect"]) for f in feats if f.get("kind") == "pond"]
    pond_holes = list(ponds)
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
        objs.append(E.paving("ld-" + _uid(seen, pa["id"]), pa["id"], r, g, mine, pit, pond_holes))
    for p in layout.get("paths", []):
        if "rect" in p:
            objs.append(E.path("ld-" + _uid(seen, p["id"]), p["id"], R(p["rect"]), g, p.get("class", "path")))
    beds = []
    for gr in layout.get("planting_groups", []):
        beds.append(R(gr["rect"]))
        objs.append(E.bed("ld-" + gr["id"], gr["id"], R(gr["rect"]), g, gr.get("role", "bed")))
        objs.append(E.edging("ld-" + gr["id"] + "-edging", "ld-" + gr["id"], R(gr["rect"]), g))
    # --- features
    water = []
    for f in feats:
        k = f.get("kind")
        if k == "pond":
            water.append(R(f["rect"])); objs += E.pond("ld-" + f["id"], f["id"], f, g)
            objs += koi(f, outdoor, g, warns, sched)
        elif k == "firepit" and pitf:
            objs += E.firepit("ld-" + f["id"], f["id"], f, g, half=half, grids=grids_for(paved, path_rects, pitf))
        elif k == "bbq":
            objs.append(OD.bbq_obj("ld-" + f["id"], f["id"], f["rect"], g, outdoor.get("bbq")) or E.bbq("ld-" + f["id"], f["id"], f["rect"], g))
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
        tb = OD.table_obj("ld-" + t["id"], t["id"], t["center"], t["size_m"], g, t.get("seats", 0), outdoor.get("dining_table"))
        objs.append(tb or E.table("ld-" + t["id"], t["id"], t["center"], t["size_m"], g, t.get("seats", 0)))
        objs += OD.chairs(t["id"], t["center"], t["size_m"], t.get("seats", 0), g, outdoor.get("dining_chair"))
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
        objs.append(E.coping("ld-" + w["id"] + "-coping", "ld-" + w["id"], R(w["rect"]), w["height_m"], g))
    screens = []
    for s in layout.get("screens", []):
        if s.get("kind") == "trellis":
            screens.append((R(s["rect"]), s["height_m"], "ld-" + s["id"]))
            objs.append(E.trellis("ld-" + s["id"], s["id"], R(s["rect"]), s["height_m"], g))
        else:
            warns.append("screen %s kind %r not built" % (s["id"], s.get("kind")))
    avoid = list(bench_rects) + [R(f["rect"]) for f in feats if "rect" in f] + [R(o["rect"]) for o in layout.get("obstacles", []) if o["id"].startswith("pot")]
    cl = P.CHAIR["off"] + P.CHAIR["seat"] / 2 + 0.1          # chairs stand round the table: keep intermediate posts out of that ring
    avoid += [(t["center"][0] - t["size_m"][0] / 2 - cl, t["center"][1] - t["size_m"][1] / 2 - cl, t["center"][0] + t["size_m"][0] / 2 + cl, t["center"][1] + t["size_m"][1] / 2 + cl) for t in layout.get("tables", [])]
    avoid += [(t["center"][0] - .2, t["center"][1] - .2, t["center"][0] + .2, t["center"][1] + .2) for t in layout.get("trees", [])]
    for c in layout.get("canopies", []):
        if c.get("kind") == "pergola" and not pergolas:
            warns.append("canopy %s: pergola NOT built (client change 2026-11-22: pruned shade trees replace pergolas); shade comes from the trees" % c["id"])
        elif c.get("kind") == "pergola":
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
    structs = [(R(w["rect"]), w["height_m"], w["id"]) for w in layout.get("walls", [])] + [(sc[0], sc[1], sc[2][3:]) for sc in screens]
    climbed = set()
    seat_rects = list(bench_rects) + [(t["center"][0] - t["size_m"][0] / 2 - .6, t["center"][1] - t["size_m"][1] / 2 - .6, t["center"][0] + t["size_m"][0] / 2 + .6, t["center"][1] + t["size_m"][1] / 2 + .6) for t in layout.get("tables", [])] \
        + [R(o["rect"]) for o in layout.get("obstacles", []) if o["id"].startswith("pot")] + [R(gr["rect"]) for gr in layout.get("planting_groups", []) if gr.get("role") == "herb" or "herb" in gr["id"]]
    seat_rects = seat_rects or [(1e6, 1e6, 1e6, 1e6)]
    has_star = any(p["species"] == "trachelospermum_jasminoides" for gr in layout.get("planting_groups", []) for p in gr["plants"])      # a layout that names star jasmine already follows the 2026-11-22 climber decision: it is authoritative
    beds_by_rect = [R(gr["rect"]) for gr in layout.get("planting_groups", [])]
    for t in layout.get("trees", []):
        if t.get("pruned") or t.get("pruned_spread_m") or t.get("canopy"):
            o, row = PL.pruned_tree("ld-" + t["id"], t["species"], t, age, g)
        else:
            o, row = PL.plant_objects("ld-" + t["id"], t["species"], t, t["center"], age, g, form=t.get("form"))
        o.meta.update(layout_spread=t.get("pruned_spread_m") or (t.get("pruned") or {}).get("spread_m") or t.get("mature_spread_m"), at=t["center"], layout_id=t["id"])
        if o.meta.get("pruned"):
            o.meta["layout_spread"] = None                       # a pruned canopy is held under the layout's mature spread by pruning: no spread assertion
        objs.append(o); sched.append(row)
        if row.get("crown_center_ignored"):
            warns.append("%s: %s" % (o.id, row["crown_center_ignored"]))
        rb = t.get("root_barrier")
        if rb:
            rr = R(rb["rect"]) if isinstance(rb, dict) and rb.get("rect") else next((b for b in beds_by_rect if b[0] <= t["center"][0] <= b[2] and b[1] <= t["center"][1] <= b[3]), None)
            bed_obj = next((o for o in objs if o.kind == "bed" and rr is not None and o.footprint == rr), None)
            rbo = E.root_barrier("ld-%s-root-barrier" % t["id"], t["id"], t["center"], rr, rb.get("radius_m") if isinstance(rb, dict) else None, g,
                                 (rb.get("depth_m") if isinstance(rb, dict) else None) or P.ROOT_BARRIER["depth"])
            if bed_obj:
                rbo.rests_on = ("ground", bed_obj.id)            # the sheet stands in the bed's soil: it passes through the soil layer by design
            objs.append(rbo)
    for f in feats:
        if f.get("kind") == "root_barrier":
            objs.append(E.root_barrier("ld-" + f["id"], f["id"], None, R(f["rect"]), None, g, f.get("depth_m") or P.ROOT_BARRIER["depth"]))
    for gr in layout.get("planting_groups", []):
        for i, pl in enumerate(gr["plants"]):
            sp = pl["species"]
            f = PL.species_facts(sp)
            clb = None
            if PL.is_climber(sp):
                clb = climb_target(pl["at"], structs, g, [b for b, _ in hard])
                if clb is None:
                    warns.append("climber %s at %s is more than 0.6 m from any wall or screen: drawn as a mound" % (sp, pl["at"]))
            oid = "ld-plant-%s-%02d" % (gr["id"], i)
            if star_jasmine and sp == "jasminum_sambac" and clb and not has_star:      # client 2026-11-22: star jasmine on screens and walls AWAY from the seats and herbs; Arabian jasmine stays by them
                if min(_dist_pt_rect(pl["at"], r) for r in seat_rects) >= P.STAR_JASMINE_MIN_FROM_SEAT:
                    sp, f = "trachelospermum_jasminoides", PL.species_facts("trachelospermum_jasminoides")
                    pl = dict(pl, species=sp, swapped_from="jasminum_sambac")
            blocker = next((n for r, n in hard if r[0] <= pl["at"][0] <= r[2] and r[1] <= pl["at"][1] <= r[3]), None)
            if blocker:
                sched.append(dict(id=oid, species=sp, status="omitted", reason="the layout puts this plant inside %s; not built (layout conflict, reported)" % blocker))
                warns.append("%s (%s) at %s lies inside %s: omitted" % (oid, sp, pl["at"], blocker)); continue
            if clb:
                climbed.add(clb["on"])
            o, row = PL.plant_objects(oid, sp, pl, pl["at"], age, g, climbing=clb, form=pl.get("form"))
            if pl.get("swapped_from"):
                row["swapped_from"] = pl["swapped_from"]
                o.label += " [client rule 2026-11-22: star jasmine away from seats; the layout names %s here]" % pl["swapped_from"]
            if f.get("habit") == "deciduous":
                o.meta["deciduous"] = True
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
    for rect, h_, sid in structs:
        if sid not in climbed:
            warns.append("climber coverage: %s (%.1f m) carries no climber in the layout: no panel built, a layout gap" % (sid, h_))
    spec = dict(ponds={f["id"]: list(R(f["rect"])) for f in feats if f.get("kind") == "pond"}, pit=(list(pitf["center"]) if pitf else None), table=(layout.get("tables") or [{}])[0].get("center"), table_w=((layout.get("tables") or [{}])[0].get("size_m") or [2.4])[0], pit_half=half, structures=[sid for _, _, sid in structs], climbed=sorted(climbed), koi=("asset" if outdoor.get("koi") else "none"))
    hh = CX.house_height(g)
    ctx = [dict(id="ctx-building-%d" % i, rect=list(R(b)), z0=g, z1=g + hh,
                label="context: our house massing, height %.0f m from villa_env (basement %.1f, roof %.1f)" % (hh, g, g + hh)) for i, b in enumerate(layout.get("buildings", []))]
    ctx += [dict(id="ctx-footprint-%d" % i, rect=list(R(b)), z0=g, z1=g + 0.03, material="ctx-footprint",
                 label="context: our house footprint on the ground (the massing above is hidden in the bird's-eye views)") for i, b in enumerate(layout.get("buildings", []))]
    if site_context:
        ctx += CX.site_context([R(w["rect"]) for w in layout.get("walls", [])])
    ids = [o.id for o in objs if o.state is None]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise ValueError("duplicate element ids: %s" % sorted(dup))
    return Scene(objs, ctx, sched, warns, age, g, source, spec=spec, season=season)
