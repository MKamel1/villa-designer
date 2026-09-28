"""D1 render scene (Phase 3/4): the design as a `villa-render/1` scene for the renderer (docs/villa-render-scene.md).

Everything the image shows comes from here, and every piece says what it is:
  - the SHELL is the daylight study's validated scene (`villa_daylight.scene`: walls with every opening placed = spec,
    slabs, columns, stair, ramp, deck and the whole context), re-materialised per room;
  - FINISHES per room (`FINISH`), chosen from the client's taste profile (knowledge/projects/villa-01/taste.json:
    warm contemporary, large-format stone, walnut, oak, boucle, brass, LED coves) — the questionnaire had no finishes
    answers, so they are ASSUMED and listed in every caption; walls and ceilings keep reflectance 0.80 / 0.85, the
    daylight study's assumption, except where stated (bathroom stone, cinema fabric, feature panels);
  - FALSE CEILINGS at 2.70 m and the coves (villa_lighting), FEATURE PANELS (walnut fluted TV wall, oak slatted
    headboard wall) and the GUARD round the stair opening (required, not yet in the Revit model) are DETAILS added
    here and labelled as such;
  - FURNITURE is villa_furnish3d (the checked layout); the TERRACE lounge set is the questionnaire's answer
    ("lounge seating"), authored here;
  - LIGHTS are villa_lighting (verified iGuzzini products where bound, generic photometry otherwise, named);
  - DRESSING (plants, books, vases, art) is listed as dressing, not design.
Units metres, model axes, z absolute (GF FFL 0, basement FFL -3.0).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .. import daylight as D
from . import revit_spec as RS
from . import villa_daylight as VD
from . import villa_furnish as F
from . import villa_furnish3d as F3
from . import villa_lighting as VL
from . import villa_r11 as R

LZ = {"B": -3.0, "GF": 0.0}
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "out" / "villa" / "render-d1"

# ------------------------------------------------------------------ materials (linear rgb; reflectance = target mean)
M = {
    "plaster-warm-white": dict(kind="principled", asset="Plaster001", base_rgb=[0.80, 0.77, 0.72], reflectance=0.80,
                               roughness=0.9, tile_m=2.0, note="warm white mineral paint on plaster (0.80)"),
    "ceiling-white": dict(kind="principled", base_rgb=[0.86, 0.85, 0.83], reflectance=0.85, roughness=0.95,
                          note="gypsum false ceiling, matt white (0.85)"),
    "travertine": dict(kind="principled", asset="Travertine009", base_rgb=[0.62, 0.56, 0.47], reflectance=0.52,
                       roughness=0.45, tile_m=1.2, note="honed travertine, large format 1200 x 600 (ASSUMED)"),
    "oak-floor": dict(kind="principled", asset="WoodFloor051", base_rgb=[0.45, 0.33, 0.22], reflectance=0.33,
                      roughness=0.5, tile_m=2.0, grain_axis="x", note="light oak engineered planks (ASSUMED)"),
    "marble-ensuite": dict(kind="principled", asset="Marble020", base_rgb=[0.66, 0.60, 0.52], reflectance=0.58,
                           roughness=0.25, tile_m=1.2, note="warm cream marble, large format (ASSUMED)"),
    "marble-bath": dict(kind="principled", asset="Marble014", base_rgb=[0.70, 0.66, 0.58], reflectance=0.62,
                        roughness=0.3, tile_m=1.2, note="cream marble, large format (ASSUMED)"),
    "marble-white": dict(kind="principled", asset="Marble012", base_rgb=[0.78, 0.78, 0.76], reflectance=0.72,
                         roughness=0.18, tile_m=1.4, note="white veined stone worktops (ASSUMED)"),
    "walnut": dict(kind="principled", asset="Wood066", base_rgb=[0.20, 0.11, 0.06], reflectance=0.12, roughness=0.45,
                   tile_m=1.0, grain_axis="z", note="walnut veneer joinery (ASSUMED)"),
    "oak": dict(kind="principled", asset="Wood094", base_rgb=[0.52, 0.40, 0.27], reflectance=0.40, roughness=0.5,
                tile_m=1.0, grain_axis="z", note="light oak veneer (ASSUMED)"),
    "greige-lacquer": dict(kind="principled", base_rgb=[0.46, 0.42, 0.37], reflectance=0.43, roughness=0.35,
                           note="matt greige lacquer kitchen fronts (ASSUMED)"),
    "boucle": dict(kind="principled", asset="Fabric082A", base_rgb=[0.74, 0.70, 0.64], reflectance=0.66,
                   roughness=0.95, tile_m=0.3, note="cream boucle upholstery (ASSUMED)"),
    "linen": dict(kind="principled", asset="Fabric036", base_rgb=[0.55, 0.50, 0.43], reflectance=0.48,
                  roughness=0.95, tile_m=0.3, note="oatmeal linen upholstery (ASSUMED)"),
    "sage-fabric": dict(kind="principled", asset="Fabric066", base_rgb=[0.40, 0.44, 0.36], reflectance=0.38,
                        roughness=0.95, tile_m=0.3, note="sage cotton (kids, ASSUMED)"),
    "charcoal-fabric": dict(kind="principled", asset="Fabric030", base_rgb=[0.07, 0.07, 0.07], reflectance=0.07,
                            roughness=0.95, tile_m=0.4, note="charcoal acoustic fabric (cinema walls and loveseat; "
                                                             "0.07, not the 0.80 wall assumption: a media room)"),
    "taupe-fabric": dict(kind="principled", asset="Fabric036", base_rgb=[0.33, 0.28, 0.23], reflectance=0.25,
                         roughness=0.95, tile_m=0.4, note="warm taupe acoustic fabric panels (cinema walls, 0.25; the "
                                                           "first choice, charcoal 0.07, left the room unreadable)"),
    "bedding-white": dict(kind="principled", asset="Fabric081C", base_rgb=[0.82, 0.81, 0.78], reflectance=0.78,
                          roughness=0.95, tile_m=0.3, note="white cotton bedding (dressing of the bed)"),
    "rug": dict(kind="principled", asset="Carpet016", base_rgb=[0.62, 0.58, 0.51], reflectance=0.55, roughness=1.0,
                tile_m=0.8, note="wool rug (ASSUMED)"),
    "leather-brown": dict(kind="principled", asset="Leather030", base_rgb=[0.14, 0.08, 0.05], reflectance=0.10,
                          roughness=0.5, tile_m=0.5, note="cognac leather (ASSUMED)"),
    "brass": dict(kind="principled", base_rgb=[0.80, 0.62, 0.34], reflectance=0.62, roughness=0.3, metallic=1.0,
                  note="brushed brass (flat, no texture held)"),
    "black-metal": dict(kind="principled", base_rgb=[0.03, 0.03, 0.03], reflectance=0.03, roughness=0.4,
                        metallic=1.0, note="black powder-coat metal"),
    "ceramic-white": dict(kind="principled", base_rgb=[0.85, 0.85, 0.84], reflectance=0.84, roughness=0.08,
                          note="glazed sanitary ceramic"),
    "screen-black": dict(kind="principled", base_rgb=[0.01, 0.01, 0.01], reflectance=0.01, roughness=0.05,
                         note="TV screen (off)"),
    "glass-clear": dict(kind="glass", base_rgb=[1, 1, 1], transmittance=0.70, interfaces=1, roughness=0.0,
                        note="clear double glazing, Tv 0.70 (Metric Handbook p. 9-8, the daylight study's value)"),
    "glass-guard": dict(kind="glass", base_rgb=[1, 1, 1], transmittance=0.85, interfaces=2, roughness=0.0,
                        note="laminated glass guard"),
    "door-oak": dict(kind="principled", asset="Wood094", base_rgb=[0.52, 0.40, 0.27], reflectance=0.40,
                     roughness=0.5, tile_m=1.0, grain_axis="z", note="flush oak veneer door, closed (ASSUMED)"),
    "render-exterior": dict(kind="principled", asset="Plaster003", base_rgb=[0.72, 0.66, 0.57], reflectance=0.55,
                            roughness=0.9, tile_m=2.5, note="exterior render, warm sand (ASSUMED; neighbours too)"),
    "paving": dict(kind="principled", asset="PavingStones146", base_rgb=[0.62, 0.58, 0.52], reflectance=0.45,
                   roughness=0.8, tile_m=2.0, note="light stone paving (garden terrace, ASSUMED)"),
    "lawn": dict(kind="principled", asset="Grass004", base_rgb=[0.10, 0.16, 0.05], reflectance=0.12,
                 roughness=1.0, tile_m=2.0, note="lawn (ASSUMED)"),
    "outdoor-fabric": dict(kind="principled", asset="Fabric036", base_rgb=[0.62, 0.58, 0.50], reflectance=0.55,
                           roughness=0.95, tile_m=0.3, note="outdoor acrylic fabric (terrace set)"),
    "teak": dict(kind="principled", asset="Wood094", base_rgb=[0.35, 0.22, 0.12], reflectance=0.22, roughness=0.6,
                 tile_m=1.0, grain_axis="x", note="teak frame (terrace set)"),
    "white-paint-joinery": dict(kind="principled", base_rgb=[0.80, 0.79, 0.76], reflectance=0.78, roughness=0.4,
                                note="white painted joinery (bunk bed, shelving)"),
}

# room -> (floor, wall, ceiling) finishes
PUBLIC_B = ("lounge", "lounge-nook", "stair-b", "hall-b", "entry-b", "family", "kitchen", "kitchen-island", "dining",
            "dining-side", "living", "bar-alcove", "dirty-kitchen", "pantry", "store-ramp")
FINISH = {r: ("travertine", "plaster-warm-white", "ceiling-white") for r in PUBLIC_B}
FINISH.update({
    "cinema": ("rug", "taupe-fabric", "ceiling-white"),
    "guest-wc": ("marble-bath", "marble-bath", "ceiling-white"),
    "family-bath": ("marble-bath", "marble-bath", "ceiling-white"),
    "parents-ensuite": ("marble-ensuite", "marble-ensuite", "ceiling-white"),
})
for r in ("landing-gf", "corridor", "gallery-end", "study-game", "kids-a", "kids-b", "parents-bed", "parents-entry",
          "parents-dressing", "parents-dressing-ext"):
    FINISH[r] = ("oak-floor", "plaster-warm-white", "ceiling-white")
UNDER_SOFFIT = ("cinema", "store-ramp", "guest-wc", "dirty-kitchen")   # ceiling = the ramp/deck soffit lining


# ------------------------------------------------------------------ geometry helpers
def box_faces(x0, y0, z0, x1, y1, z1):
    """Six outward CCW quads of an axis-aligned box."""
    return [[[x0, y0, z0], [x0, y1, z0], [x1, y1, z0], [x1, y0, z0]],          # bottom (normal -z)
            [[x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]],          # top
            [[x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1]],          # -y
            [[x1, y1, z0], [x0, y1, z0], [x0, y1, z1], [x1, y1, z1]],          # +y
            [[x0, y1, z0], [x0, y0, z0], [x0, y0, z1], [x0, y1, z1]],          # -x
            [[x1, y0, z0], [x1, y1, z0], [x1, y1, z1], [x1, y0, z1]]]          # +x


def quad_up(x0, y0, x1, y1, z):
    return [[x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]]


def quad_down(x0, y0, x1, y1, z):
    return [[x0, y0, z], [x0, y1, z], [x1, y1, z], [x1, y0, z]]


def disc_down(cx, cy, z, r, n=16):
    return [[[cx + r * math.cos(-2 * math.pi * k / n), cy + r * math.sin(-2 * math.pi * k / n), z] for k in range(n)]]


def sphere(cx, cy, cz, r, nu=16, nv=10):
    faces = []
    for j in range(nv):
        t0, t1 = math.pi * j / nv, math.pi * (j + 1) / nv
        for i in range(nu):
            p0, p1 = 2 * math.pi * i / nu, 2 * math.pi * (i + 1) / nu
            pts = []
            for t, p in ((t0, p0), (t1, p0), (t1, p1), (t0, p1)):
                pts.append([round(cx + r * math.sin(t) * math.cos(p), 5), round(cy + r * math.sin(t) * math.sin(p), 5),
                            round(cz + r * math.cos(t), 5)])
            uniq = [q for k, q in enumerate(pts) if q not in pts[:k]]
            if len(uniq) >= 3:
                faces.append(uniq)
    return faces


def _normal(pts):
    nx = ny = nz = 0.0
    for a, b in zip(pts, pts[1:] + pts[:1]):
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / L, ny / L, nz / L


def _room_at(lay, x, y, z):
    lv = "B" if z < -0.05 else ("GF" if z < 2.85 else None)
    if lv is None:
        return None
    best = None
    for rid, r in lay["rooms"].items():
        if r["level"] != lv:
            continue
        x0, y0, x1, y1 = r["rect"]
        if x0 - 1e-6 <= x <= x1 + 1e-6 and y0 - 1e-6 <= y <= y1 + 1e-6:
            if best is None or r.get("part_of") is None:
                best = rid
    return best


# ------------------------------------------------------------------ the scene
def build(lay=None, views=None):
    lay = lay or R.design("D1")
    sp = RS.build(lay)
    meshes, notes = [], []
    mats = dict(M)

    SOFT = {"boucle", "linen", "sage-fabric", "taupe-fabric", "charcoal-fabric", "bedding-white", "outdoor-fabric"}

    def mesh(mid, mat, faces, group, room=None, label=None, **kw):
        if group in ("furniture", "dressing") and "bevel_m" not in kw and mat not in ("glass-guard", "rug"):
            # real pieces have no knife edges: 4 mm on hard pieces, soft rounded edges on upholstery and bedding
            if mat in SOFT:
                kw.update(bevel_m=0.02, subdivide=1)
            else:
                kw.update(bevel_m=0.004)
        meshes.append(dict(id=mid, group=group, material=mat, room=room, label=label or mid, faces=faces, **kw))

    # ---- shell: the daylight scene's faces, re-materialised
    shell = VD.scene(lay)
    stair_boxes = [[v / 1000.0 for v in b] for b in sp["stair"]]
    buckets = {}
    for f in shell.faces:
        pts = [list(p) for p in f.points]
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        cz = sum(p[2] for p in pts) / len(pts)
        mat, room = None, None
        if any(all(b[0] - 1e-3 <= p[0] <= b[3] + 1e-3 and b[1] - 1e-3 <= p[1] <= b[4] + 1e-3 and
                   b[2] - 1e-3 <= p[2] <= b[5] + 1e-3 for p in pts) for b in stair_boxes):
            mat = "walnut"                                       # the floating treads
        elif f.material == "glass":
            mat = "glass-clear"
        elif f.material == "door":
            n = _normal(pts)
            room = _room_at(lay, cx + 0.06 * n[0], cy + 0.06 * n[1], cz)
            mat = "door-oak"
        elif f.material in ("context", "white"):
            mat = "render-exterior"
        elif f.material == "ground":
            mat = "paving"
        elif f.material == "floor":
            mat = "travertine"
        elif f.material == "ceiling":
            mat = "ceiling-white"
            n = _normal(pts)
            room = _room_at(lay, cx, cy, cz - 0.1) if n[2] < -0.5 else None
            if room in FINISH and FINISH[room][2] != "ceiling-white":
                mat = FINISH[room][2]
        else:                                                    # "wall": our walls, columns, infills, rails
            n = _normal(pts)
            room = _room_at(lay, cx + 0.06 * n[0], cy + 0.06 * n[1], cz)
            mat = FINISH[room][1] if room in FINISH else ("render-exterior" if abs(n[2]) < 0.5 else "ceiling-white")
        key = (mat, room if mat not in ("render-exterior", "paving", "travertine", "ceiling-white", "glass-clear")
               else None)
        buckets.setdefault(key, []).append(pts)
    for k, ((mat, room), faces) in enumerate(sorted(buckets.items(), key=lambda kv: (kv[0][0], kv[0][1] or ""))):
        grp = "context" if mat == "render-exterior" else "shell"
        mesh("shell-%03d-%s" % (k, mat), mat, faces, grp, room=room, label=room or mat)

    # ---- per-room floor finishes (2 mm over the slab) and false ceilings / coves
    cove_rooms = {f.extra.get("cove_room") for f in VL.design(lay) if f.kind == "COVE" and f.extra.get("cove_room")}
    for rid, r in lay["rooms"].items():
        if rid not in FINISH:
            continue
        x0, y0, x1, y1 = F.clear_rect(lay, rid)
        z = LZ[r["level"]]
        if rid not in ("stair-b",):
            mesh("floor-" + rid, FINISH[rid][0], [quad_up(x0, y0, x1, y1, z + 0.002)], "shell", room=rid,
                 label=rid)
        if rid in UNDER_SOFFIT or rid in ("stair-b",):
            continue
        zc = z + VL.CEILING
        if rid in cove_rooms:
            b = VL.COVE_BAND
            ring = [quad_down(x0, y0, x1, y0 + b, zc), quad_down(x0, y1 - b, x1, y1, zc),
                    quad_down(x0, y0 + b, x0 + b, y1 - b, zc), quad_down(x1 - b, y0 + b, x1, y1 - b, zc)]
            lip = []                                              # the fascia hiding the strip, 80 mm
            for (xa, ya, xb, yb) in ((x0 + b, y0 + b, x1 - b, y0 + b), (x1 - b, y1 - b, x0 + b, y1 - b),
                                     (x0 + b, y1 - b, x0 + b, y0 + b), (x1 - b, y0 + b, x1 - b, y1 - b)):
                lip.append([[xa, ya, zc], [xb, yb, zc], [xb, yb, zc + 0.08], [xa, ya, zc + 0.08]])
            mesh("ceiling-" + rid, "ceiling-white", ring + lip, "shell", room=rid,
                 label="detail: cove ceiling (band at 2.70, field 2.80)")
        else:
            mesh("ceiling-" + rid, "ceiling-white", [quad_down(x0, y0, x1, y1, zc)], "shell", room=rid,
                 label="detail: false ceiling 2.70")
    notes.append("False ceilings at 2.70 m (plenum for the flush fittings; the daylight study assumed 2.80 m).")

    # ---- feature panels and the guard (details added here)
    it = {i["id"]: i for i in F.layout(lay)}
    L = F.clear_rect(lay, "lounge")
    tv = F.footprint(it["lounge-tv"])
    faces = []
    for k in range(int((tv[2] + 0.6 - (tv[0] - 0.6)) / 0.06)):
        xa = tv[0] - 0.6 + k * 0.06
        faces += box_faces(xa, L[3] - 0.04, LZ["B"], xa + 0.04, L[3], LZ["B"] + VL.CEILING)
    mesh("detail-tv-fluting", "walnut", faces, "furniture", room="lounge", label="detail: walnut fluted TV wall")
    PB = F.clear_rect(lay, "parents-bed")
    bed = F.footprint(it["pb-bed"])
    faces = []
    for k in range(int((bed[2] + 0.9 - (bed[0] - 0.6)) / 0.05)):
        xa = bed[0] - 0.6 + k * 0.05
        faces += box_faces(xa, PB[1], 0.0, xa + 0.03, PB[1] + 0.03, VL.CEILING)
    mesh("detail-headboard-slats", "oak", faces, "furniture", room="parents-bed",
         label="detail: oak slatted headboard wall")
    op = sp["gf_opening"]
    gz = 0.0
    guard = [[[op[0], op[3], gz], [op[2], op[3], gz], [op[2], op[3], gz + 1.1], [op[0], op[3], gz + 1.1]],
             [[op[2], op[1], gz], [op[2], op[3], gz], [op[2], op[3], gz + 1.1], [op[2], op[1], gz + 1.1]]]
    mesh("detail-stair-guard", "glass-guard", guard, "furniture", room="stair-gf",
         label="detail: 1.1 m glass guard at the stair opening (required; not yet in the Revit model)")
    notes.append("Details added for the render: fluted walnut TV wall, oak headboard slats, glass guard at the stair "
                 "opening, cove ceilings.")

    # ---- furniture (the checked layout), materials by type and part
    for f in F3.spec(lay):
        z = LZ[f["level"]]
        parts = {}
        for name, b in zip(f["parts"], f["boxes"]):
            parts.setdefault(part_material(f, name), []).extend(box_faces(b[0], b[1], z + b[2], b[3], b[4], z + b[5]))
        for k, (mat, faces) in enumerate(parts.items()):
            mesh("furn-%s-%d" % (f["mark"].replace("#", "-"), k), mat, faces, "furniture", room=f["room"],
                 label=f["mark"].split("#")[0])
    # rugs (design: soft floor where people sit)
    for rid, anchor, (w, d) in (("lounge", "lounge-coffee", (2.6, 1.9)), ("living", "living-coffee", (2.4, 2.0)),
                                ("parents-bed", "pb-bed", (2.2, 2.6)), ("kids-a", "ka-bunk", (1.4, 2.0))):
        q = F.footprint(it[anchor])
        cx, cy = (q[0] + q[2]) / 2, (q[1] + q[3]) / 2
        z = LZ[lay["rooms"][rid]["level"]] + 0.012
        mesh("rug-" + rid, "rug", box_faces(cx - w / 2, cy - d / 2, z - 0.01, cx + w / 2, cy + d / 2, z), "furniture",
             room=rid, label="rug-" + rid)
    notes.append("Rugs in the lounge, garden living, parents' bedroom and kids room A (ASSUMED).")

    # ---- dressing: clothes on the dressing rails, duvets and pillows on the beds (NOT design)
    import random
    rnd = random.Random(7)
    fabrics = ["linen", "boucle", "sage-fabric", "taupe-fabric", "bedding-white", "leather-brown"]
    for wid in ("pd-hang-1", "pd-hang-2"):
        q = F.footprint(it[wid])
        top = LZ["GF"] + it[wid]["h"] - 0.31
        cy = (q[1] + q[3]) / 2
        x = q[0] + 0.06
        k = 0
        while x < q[2] - 0.06:
            L = rnd.choice((0.75, 0.9, 1.05, 1.2))
            mesh("dress-clothes-%s-%d" % (wid, k), rnd.choice(fabrics),
                 box_faces(x, cy - 0.24, top - L, x + 0.035, cy + 0.24, top), "dressing", room=it[wid]["room"],
                 label="dressing: clothes")
            x += rnd.choice((0.05, 0.065, 0.08))
            k += 1
    for bid, duvet in (("pb-bed", "bedding-white"), ("kb-bed", "sage-fabric"), ("ka-bunk", "bedding-white")):
        b_ = it[bid]
        q = F.footprint(b_)
        z = LZ["GF"] + (0.40 if b_["h"] >= 1.5 else b_["h"])
        if b_["rot"] in (0, 180):
            head = q[1] if b_["rot"] == 0 else q[3]
            s_ = 1 if b_["rot"] == 0 else -1
            ya, yb_ = sorted((head + s_ * 0.55, (q[3] + 0.02) if s_ > 0 else (q[1] - 0.02)))
            dv = box_faces(q[0] - 0.03, ya, z, q[2] + 0.03, yb_, z + 0.07)
            n = 2 if q[2] - q[0] > 1.1 else 1
            wpil = (q[2] - q[0] - 0.1) / n
            pil = []
            for k in range(n):
                xa = q[0] + 0.05 + k * wpil
                ya2, yb2 = sorted((head + s_ * 0.08, head + s_ * 0.48))
                pil.append(box_faces(xa + 0.02, ya2, z, xa + wpil - 0.02, yb2, z + 0.14))
        else:
            head = q[0] if b_["rot"] == -90 else q[2]
            s_ = 1 if b_["rot"] == -90 else -1
            xa, xb = sorted((head + s_ * 0.55, (q[2] + 0.02) if s_ > 0 else (q[0] - 0.02)))
            dv = box_faces(xa, q[1] - 0.03, z, xb, q[3] + 0.03, z + 0.07)
            xa2, xb2 = sorted((head + s_ * 0.08, head + s_ * 0.48))
            pil = [box_faces(xa2, q[1] + 0.07, z, xb2, q[3] - 0.07, z + 0.14)]
        mesh("dress-duvet-" + bid, duvet, dv, "dressing", room=b_["room"], label="dressing: duvet")
        for k, pf in enumerate(pil):
            mesh("dress-pillow-%s-%d" % (bid, k), "bedding-white", pf, "dressing", room=b_["room"],
                 label="dressing: pillow")
    notes.append("Dressing: clothes on the dressing rails, duvets and pillows on the beds (not design).")
    notes.append("By day the basement rooms are shown with their ambient and accent lights at 50 % (a basement is "
                 "used with lights on by day); ground-floor day views are daylight only.")

    # ---- terrace lounge set (questionnaire: lounge seating), on paving outside the garden living
    tx0 = 22.6 + 0.6
    zt = LZ["B"]
    mesh("terrace-paving", "paving", [quad_up(22.6, -29.9, 25.9, -20.4, zt + 0.004)], "ground",
         label="terrace paving")
    mesh("garden-lawn", "lawn", [quad_up(25.9, -29.9, 28.5, -20.4, zt + 0.004)], "ground", label="lawn")
    for mid, (x0, y0, x1, y1, h, mat) in {
            "terrace-sofa-base": (tx0 + 1.9, -27.6, tx0 + 2.75, -25.2, 0.40, "teak"),
            "terrace-sofa-cushion": (tx0 + 1.9, -27.55, tx0 + 2.75, -25.25, 0.47, "outdoor-fabric"),
            "terrace-sofa-back": (tx0 + 2.55, -27.6, tx0 + 2.75, -25.2, 0.78, "outdoor-fabric"),
            "terrace-table": (tx0 + 0.95, -26.9, tx0 + 1.55, -25.9, 0.38, "teak"),
            "terrace-chair-1": (tx0 + 0.0, -27.55, tx0 + 0.75, -26.8, 0.45, "outdoor-fabric"),
            "terrace-chair-2": (tx0 + 0.0, -26.0, tx0 + 0.75, -25.25, 0.45, "outdoor-fabric")}.items():
        mesh(mid, mat, box_faces(x0, y0, zt, x1, y1, zt + h), "furniture", label="terrace lounge set")
    notes.append("Terrace lounge set (sofa, two chairs, table) from the questionnaire answer 'lounge seating'.")

    # ---- lights and fixture bodies
    VL.bind_products()
    lights = []
    ies_dir = OUT / "ies"
    for k in VL.KINDS:
        if k not in VL.PRODUCTS and VL.KINDS[k]["mount"] in ("recessed",):
            p = ies_dir / "generic" / (k + ".ies")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(VL.generic_ies(VL.KINDS[k]["lm"], VL.KINDS[k]["beam"], k), encoding="utf-8")
    for f in VL.design(lay):
        k = VL.KINDS[f.kind]
        prod = VL.PRODUCTS.get(f.kind)
        cct = int(prod["cct"]) if prod else k["cct"]
        pinfo = ({"manufacturer": prod["manufacturer"], "code": prod["code"], "generic": False,
                  "substitute": prod["substitute"]} if prod else {"manufacturer": "generic", "code": f.kind,
                                                                  "generic": True})
        if k["mount"] == "recessed":
            ies = ("iguzzini/%s.ies" % prod["code"]) if prod else ("generic/%s.ies" % f.kind)
            lights.append(dict(id=f.id, room=f.room, layer=f.layer, type="ies", position=[f.x, f.y, f.z - 0.03],
                               aim=_unit(f.aim), spin_deg=0.0, ies=ies, lumens=round(f.lumens, 1), cct_k=cct, cri=90,
                               product=pinfo, dimmer=1.0))
            mesh("fix-" + f.id, "black-metal", disc_down(f.x, f.y, f.z - 0.0015, 0.0415), "fixture", room=f.room,
                 label="fitting " + f.id)
            mats.setdefault("lens-%d" % cct, dict(kind="emissive", base_rgb=[1, 1, 1], emission_lm_per_m2=40000.0,
                                                  cct_k=cct, note="visible lens glow (no light contribution)"))
            mesh("lens-" + f.id, "lens-%d" % cct, disc_down(f.x, f.y, f.z - 0.002, 0.018), "fixture",
                 room=f.room, label="fitting " + f.id,
                 visibility={"camera": True, "glossy": True, "diffuse": False, "shadow": False,
                             "transmission": False}, layer=f.layer)
        elif f.kind in ("PEN-GLOBE", "PEN-SMALL", "SCONCE"):
            r = k.get("diameter", 0.2) / 2
            area = 4 * math.pi * r * r
            mname = "opal-%s-%d" % (f.kind.lower(), cct)
            mats[mname] = dict(kind="emissive", base_rgb=[0.95, 0.93, 0.90], emission_lm_per_m2=round(f.lumens / area,
                                                                                                       1),
                               cct_k=cct, note="opal glass globe as a diffuse emitter, %d lm (GENERIC)" % f.lumens)
            cz = f.z + r if f.kind != "SCONCE" else f.z
            mesh("lamp-" + f.id, mname, sphere(f.x, f.y, cz, r), "fixture", room=f.room,
                 label="fitting " + f.id, layer=f.layer)
            top = f.extra.get("hang_from")
            if top:
                zb = LZ[f.level] + top if top < 2.9 and f.level == "B" else top
                if f.level == "B":
                    zb = LZ["B"] + VL.CEILING if top > 0 else top
                mesh("cord-" + f.id, "black-metal", box_faces(f.x - 0.003, f.y - 0.003, cz + r, f.x + 0.003,
                                                              f.y + 0.003, zb), "fixture", room=f.room,
                     label="fitting " + f.id)
                mesh("canopy-" + f.id, "brass", box_faces(f.x - 0.05, f.y - 0.05, zb - 0.02, f.x + 0.05, f.y + 0.05,
                                                          zb), "fixture", room=f.room, label="fitting " + f.id)
        elif f.kind == "PEN-LIN":
            Lg = k["length"]
            zb = f.z
            mesh("lamp-body-" + f.id, "black-metal", box_faces(f.x - Lg / 2, f.y - 0.03, zb, f.x + Lg / 2, f.y + 0.03,
                                                              zb + 0.06), "fixture", room=f.room,
                 label="fitting " + f.id)
            mname = "led-lin-%d" % cct
            mats[mname] = dict(kind="emissive", base_rgb=[1, 1, 1], emission_lm_per_m2=round(
                f.lumens / ((Lg - 0.1) * 0.03), 1), cct_k=cct, note="linear pendant diffuser, %d lm (GENERIC)" %
                f.lumens)
            mesh("lamp-" + f.id, mname, [quad_down(f.x - Lg / 2 + 0.05, f.y - 0.015, f.x + Lg / 2 - 0.05,
                                                   f.y + 0.015, zb - 0.001)], "fixture", room=f.room,
                 label="fitting " + f.id, layer=f.layer)
            ceil = LZ["B"] + VL.CEILING
            for s in (-1, 1):
                mesh("wire-%s-%d" % (f.id, s), "black-metal", box_faces(f.x + s * 0.6 - 0.002, f.y - 0.002, zb + 0.06,
                                                                         f.x + s * 0.6 + 0.002, f.y + 0.002, ceil),
                     "fixture", room=f.room, label="fitting " + f.id)
        elif k["mount"] == "strip":
            lights.append(dict(id=f.id, room=f.room, layer=f.layer, type="line", position=[f.x, f.y, f.z],
                               aim=_unit(f.aim), size=[0.012, f.length], length_dir=list(f.along), spread_deg=120,
                               lumens=round(f.lumens, 1), cct_k=cct, cri=90, product=pinfo, dimmer=1.0))
        elif k["mount"] == "wall-marker":
            w, h = 0.10, 0.04
            mname = "marker-%d" % cct
            mats[mname] = dict(kind="emissive", base_rgb=[1, 1, 1], emission_lm_per_m2=round(f.lumens / (w * h), 1),
                               cct_k=cct, note="recessed wall marker, %d lm (GENERIC)" % f.lumens)
            ay = f.aim[1]
            yy = f.y + (0.001 if ay > 0 else -0.001)
            face = [[f.x - w / 2, yy, f.z - h / 2], [f.x + w / 2, yy, f.z - h / 2], [f.x + w / 2, yy, f.z + h / 2],
                    [f.x - w / 2, yy, f.z + h / 2]]
            if ay < 0:
                face = face[::-1]
            mesh("marker-" + f.id, mname, [face], "fixture", room=f.room, label="fitting " + f.id, layer=f.layer)
    notes.append("Photometry: iGuzzini Laser Evo D75 (DL AAK3EW, DLN AAIIA6, ADJ AAHENX; verified LDTs); wall "
                 "washer positions use AAK3EW as a stated substitute; strips, pendants, sconces and markers are "
                 "GENERIC (named in each caption).")

    scene = {"schema": "villa-render/1", "id": "D1", "north": {"model_y_bearing_deg": 20.0},
             "library_root": "$HOME/archpipe/assets/library", "materials": mats, "meshes": meshes, "lights": lights,
             "props": props(lay), "views": views if views is not None else VIEWS(lay),
             "exposure": EXPOSURE, "sky": {"day": "nishita",
                                           "evening": {"hdri": "belfast_sunset_puresky.exr", "horizontal_lux": 30.0},
                                           "night": {"hdri": "dikhololo_night.exr", "horizontal_lux": 0.3}},
             "measurement_maintenance_factor": VL.MF,
             "measurement_points": [dict(room=room, card=card, position=[x, y, z], label=label,
                                         required_lux=VL.card_value(card))
                                    for room, card, x, y, z, label in VL.task_points(lay)],
             "notes": notes + ["Finishes are ASSUMED from the taste profile (no finishes answers yet).",
                               "Dressing (plants, books, vases, art, pillows) is not design."]}
    return scene


def _unit(v):
    L = math.sqrt(sum(c * c for c in v)) or 1.0
    return [round(c / L, 4) for c in v]


def part_material(f, part):
    t, room = f["type"], f["room"]
    if f["type"] == "chair":
        return "walnut" if part in ("leg", "back") else "boucle"
    if f["type"] == "stool":
        return "leather-brown" if part == "seat" else "brass"
    if t.startswith("bed_"):
        if "mattress" in part:
            return "bedding-white"
        if room in ("kids-a", "kids-b"):
            return "white-paint-joinery" if part != "rail" else "white-paint-joinery"
        return "oak"
    if t.startswith("sofa") or t in ("armchair", "recliner"):
        if room == "cinema":
            return "charcoal-fabric"
        if room == "study-game":
            return "sage-fabric"
        return "boucle" if room in ("lounge", "living") and t.startswith("sofa") else "linen"
    if t == "coffee_table":
        return "walnut" if part != "leg" else "black-metal"
    if t in ("dining_6x",):
        return "walnut"
    if t == "desk":
        return "walnut" if room in ("study-game", "parents-bed") else "oak"
    if t == "island":
        return "marble-white" if part == "worktop" else ("black-metal" if part == "plinth" else "walnut")
    if t == "base_run":
        if part == "worktop":
            return "marble-white"
        if part == "plinth":
            return "black-metal"
        return "greige-lacquer"
    if t in ("bookcase",):
        return "walnut"
    if t in ("pantry_shelving", "store_shelving"):
        return "white-paint-joinery"
    if t in ("wardrobe", "tall_column"):
        return "oak" if room not in ("dirty-kitchen",) else "greige-lacquer"
    if t in ("sideboard", "tv_unit", "bedside_table", "window_bench"):
        return "screen-black" if part == "screen" else "walnut"
    if t == "screen":
        return "screen-black"
    if t in ("wc",):
        return "ceramic-white" if part != "flush-plate" else "brass"
    if t in ("washbasin", "washbasin_double"):
        return "ceramic-white" if part == "basin" else "walnut"
    if t == "bath":
        return "ceramic-white"
    if t == "shower_walkin":
        return "glass-guard" if part == "glass" else ("marble-ensuite" if room == "parents-ensuite" else "marble-bath")
    if t in ("washer_dryer",):
        return "ceramic-white"
    if t in ("folding_counter",):
        return "marble-white" if part == "worktop" else "greige-lacquer"
    return "oak"


# ------------------------------------------------------------------ dressing
def props(lay):
    """Dressing (NOT design): placed on the checked furniture's tops or the floor beside it."""
    it = {i["id"]: i for i in F.layout(lay)}
    fp = {k: F.footprint(v) for k, v in it.items()}
    B, G = LZ["B"], LZ["GF"]
    out = []

    def add(pid, asset, x, y, z, rz=0.0, s=1.0, label=""):
        out.append({"id": pid, "asset": asset, "position": [round(x, 3), round(y, 3), round(z, 3)],
                    "rotation_deg": [0, 0, rz], "scale": s, "label": "dressing: " + (label or asset)})

    def c(k):
        q = fp[k]
        return (q[0] + q[2]) / 2, (q[1] + q[3]) / 2

    x, y = c("k-island")
    add("island-bowl", "wooden_bowl_01", x + 0.6, y + 0.1, B + it["k-island"]["h"], label="bowl on the island")
    x, y = c("dining-table")
    add("dining-vase", "ceramic_vase_01", x, y, B + it["dining-table"]["h"], label="vase on the table")
    x, y = c("dining-sideboard")
    add("sideboard-vase", "ceramic_vase_03", x - 0.5, y, B + it["dining-sideboard"]["h"], label="vase on the sideboard")
    add("sideboard-art", "hanging_picture_frame_01", x, fp["dining-sideboard"][1] + 0.02, B + 1.45, 0, 1.0,
        "art above the sideboard")
    x, y = c("lounge-coffee")
    add("lounge-books", "book_encyclopedia_set_01", x - 0.3, y, B + it["lounge-coffee"]["h"], label="books")
    add("lounge-plant", "pachira_aquatica_01", 4.3, -24.35, B, label="money tree in the corner by the street window")
    x, y = c("living-coffee")
    add("living-plant-table", "potted_plant_04", x + 0.3, y, B + it["living-coffee"]["h"],
        label="single potted table plant, 0.168 x 0.185 m footprint, 0.267 m tall")
    add("living-plant", "potted_plant_02", 22.1, -24.25, B, label="floor plant by the garden door")
    bk = fp["alcove-books"]
    for k in range(3):
        add("library-books-%d" % k, "book_encyclopedia_set_01", bk[0] + 0.5 + k * 1.1, bk[1] + 0.16,
            B + 0.03 + (k + 1) * 0.44, label="books on the library shelves")
    x, y = c("pb-bedside")
    add("bedside-books", "book_encyclopedia_set_01", x, y, G + it["pb-bedside"]["h"], label="books on the bedside")
    add("bedroom-plant", "potted_plant_01", fp["pb-vanity"][0] - 0.2, fp["pb-vanity"][1] - 0.35, G, s=0.58,
        label="single potted plant, 0.341 x 0.367 m footprint, 0.783 m tall")
    add("study-plant", "potted_plant_01", fp["study-sofa"][0] - 0.1, fp["study-sofa"][3] + 0.3, G, label="plant")
    add("terrace-planter-1", "planter_box_01", 25.3, -29.2, B, label="terrace planter")
    add("garden-shrub-1", "shrub_01", 27.4, -28.8, B, label="garden shrub")
    add("garden-shrub-2", "shrub_03", 27.6, -22.0, B, label="garden shrub")
    add("garden-shrub-3", "shrub_01", 27.2, -25.2, B, 40, label="garden shrub")
    for rid, sofa in (("lounge", "lounge-sofa"), ("living", "living-sofa")):
        x, y = c(sofa)
        add("pillows-" + rid, "throw_pillows_01", x, y - 0.05 if rid == "lounge" else y, B + 0.44,
            0 if rid == "lounge" else 0, label="throw pillows")
    return out


# ------------------------------------------------------------------ views
EXPOSURE = {  # PRE-REGISTERED (2026-09-27) before the first render; incident metering EV = log2(E * 100 / 250)
    "day": {"ev100": 8.0, "white_balance_k": 5500},          # interiors lit by daylight, ~100-600 lx
    "evening": {"ev100": 6.0, "white_balance_k": 3200},      # interiors at dusk by their own light, ~100-300 lx
    "exterior-dusk": {"ev100": 4.0, "white_balance_k": 4300},
}


def VIEWS(lay=None):
    """The 14 views: the client's 8 (questionnaire) + 6 more. Camera at eye height 1.55 m (1.2 m for the seated
    cinema), level, framed on plan (check with scripts/villa_render_views.py)."""
    B, G = LZ["B"], LZ["GF"]
    day = "2026-10-15T10:30:00+03:00"
    dusk = "2026-10-15T18:35:00+03:00"
    V = []

    def v(vid, title, state, pos, tgt, lens, subjects, when=None, layers=None, dimmers=None, shift_y=0.0):
        V.append({"id": vid, "title": title, "state": state, "when": when or (day if state == "day" else dusk),
                  "camera": {"position": pos, "target": tgt, "lens_mm": lens, "sensor_mm": 36, "shift_x": 0.0,
                             "shift_y": shift_y},
                  "resolution": [1920, 1280],
                  "layers_on": layers if layers is not None else (["ambient", "task", "accent", "decorative"]
                                                                  if state != "day" else []),
                  "dimmers": dimmers or {}, "exposure": state if state in EXPOSURE else "day",
                  "subjects": subjects, "samples": 1024})

    # client's 8
    BASEMENT_DAY = dict(layers=["ambient", "accent"], dimmers={"ambient": 0.5, "accent": 0.5})  # stated in captions
    v("v01-kitchen-garden", "Kitchen island to the garden", "day", [10.6, -25.15, B + 1.55], [22.3, -26.6, B + 1.2], 20,
      ["k-island", "dining-table", "living-sofa"], **BASEMENT_DAY)
    v("v02-garden-living", "Garden living", "day", [16.3, -24.3, B + 1.55], [22.0, -28.9, B + 1.1], 20,
      ["living-sofa", "alcove-books"], **BASEMENT_DAY)
    v("v03-street-lounge", "Street lounge", "day", [9.3, -27.2, B + 1.55], [4.0, -24.2, B + 1.1], 20,
      ["lounge-sofa", "lounge-tv"], **BASEMENT_DAY)
    v("v04-study-deck", "GF study to the deck", "day", [4.3, -26.0, G + 1.55], [8.6, -23.6, G + 1.2], 20,
      ["study-sofa", "study-adult-desk"])
    v("v05-parents-bedroom", "Parents' bedroom", "evening", [19.1, -24.35, G + 1.55], [21.2, -26.6, G + 0.9], 20,
      ["pb-bed"], dimmers={"ambient": 0.3, "accent": 0.4, "task": 0.5})
    v("v06-kids-room", "Kids' room A", "day", [14.2, -25.4, G + 1.45], [11.8, -25.0, G + 1.0], 18,
      ["ka-bunk", "ka-desk-1"])
    v("v07-terrace-dusk", "Garden and terrace at dusk", "exterior-dusk", [28.2, -21.2, B + 1.6], [21.0, -26.4, B + 1.8],
      20, ["terrace lounge set", "living-sofa"], layers=["ambient", "task", "accent", "decorative"],
      dimmers={"ambient": 0.5, "task": 0.4})
    v("v08-cinema", "Cinema, lights up before a film", "evening", [8.75, -23.2, B + 1.3], [4.4, -21.4, B + 0.9], 18,
      ["cinema-sofa"])
    # six more
    v("v09-dining-evening", "Dining and island at night", "evening", [18.1, -27.9, B + 1.55], [12.5, -25.2, B + 1.0], 20,
      ["dining-table", "k-island"], dimmers={"ambient": 0.35, "task": 0.5})
    v("v10-living-evening", "Garden living at night: cove and library", "evening", [21.8, -24.5, B + 1.55],
      [18.4, -29.2, B + 1.3], 20, ["alcove-books", "living-sofa"], dimmers={"ambient": 0.25, "task": 0.5})
    v("v11-stair-void", "The stair up to the globe cluster in the void", "evening", [10.45, -27.95, B + 1.45],
      [5.8, -27.95, B + 1.75], 16, ["stair-gf", "stair-b"], shift_y=0.18)
    v("v12-ensuite", "Parents' ensuite", "evening", [21.6, -29.1, G + 1.55], [20.2, -30.6, G + 0.9], 16,
      ["pe-bath", "pe-basin"], dimmers={"ambient": 0.5})
    v("v13-kids-b", "Kids' room B at bedtime", "evening", [17.9, -26.4, G + 1.45], [15.4, -24.0, G + 0.9], 18, ["kb-bed", "kb-desk"])
    v("v14-dressing", "Parents' dressing", "evening", [21.95, -27.0, G + 1.55], [19.8, -28.3, G + 1.1], 16,
      ["pd-hang-1", "pd-hang-2"], dimmers={"ambient": 0.6})
    # sun per view (laptop side, archpipe.solar)
    from datetime import datetime
    from ..solar import sun_position
    import yaml
    site = yaml.safe_load((ROOT / "spec" / "villa-site.yaml").read_text(encoding="utf-8"))
    from datetime import timezone
    loc = site["location"]
    for x in V:                                   # Egypt summer time (+03:00) is written into each timestamp
        t = datetime.fromisoformat(x["when"]).astimezone(timezone.utc)
        s = sun_position(t, loc["latitude"], loc["longitude"])
        x["sun"] = {"altitude_deg": round(s.altitude, 2), "azimuth_true_deg": round(s.azimuth, 2)}
    return V


def write(path=None, views=None):
    scene = build(views=views)
    path = Path(path or OUT / "scene.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(scene), encoding="utf-8")
    return path, scene
