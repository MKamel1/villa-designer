"""Lane DF: parents' suite OPTIONS drawn as architectural plans (1:50 A3) and two interior elevations (1:25 A3).
PROPOSAL ONLY: the design model is loaded and varied IN MEMORY (one door moved); nothing is written back.
Walls, doors and windows are drawn by the project's own drawers (documents.plans); furniture detail is drawn here.
Frame: client north-up (orient.to_client): sheet (east, north) = (model y, -model x). Geometry below is MODEL metres; P() converts.
Run: PYTHONPATH=src python scripts/df_plans.py  -> docs/lanes/DF-plans/*.pdf + *.png
"""
import dataclasses, json, math, sys, textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import df_privacy_options as O
import df_dressing_door_study as S
from shapely.geometry import box, Polygon as SP, Point
from shapely.ops import unary_union
from matplotlib.patches import Polygon as MP, Rectangle, Circle, Arc, Wedge

from archpipe import model
from archpipe.documents import plans, sheetset
from archpipe.drawings2d import orient, standard

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/lanes/DF-plans"
EL = model.load("D1")
SPEC = sheetset.build("D1", elements=EL)
SPEC["levels"] = json.loads(Path(model.api.snapshot_path("D1")).read_text(encoding="utf-8")).get("levels", {})
PAPER = standard.PAPERS["A3"]
CROP = (15.8, -31.4, 22.75, -23.4)                 # model x0, y0, x1, y1 (m)
BROWN, TAN, BLUE, RED, GREY = "#7a5c2e", "#fffdf5", "#1f5f99", "#c00000", "#666666"

# ---------------------------------------------------------------- the two options (model metres)
CEIL = 2.70
BED_W, BED_L = 1.6, 2.0
TRAY_PULL, TRAY_V0, TRAY_V1 = 0.25, 0.35, 0.80      # furniture.JOINERY_BED: tray window 0.35..0.80 m from the head, 0.25 m pull
OPT = {
    "1a": dict(head=(20.33, -26.591), toward=(0, 1), hers=(19.627, 21.347), hers_order="from_west", door=None,
               curtain="parked", slat=False, vanity=S.VANITY),
    "R3": dict(head=(20.437, -23.791), toward=(0, -1), hers=(20.477, 22.347), hers_order="from_door", door=19.977,
               curtain="both", slat=True, vanity=S.VANITY),
}
for k in OPT:
    o = OPT[k]
    (hx, hy), (dx, dy) = o["head"], o["toward"]
    o["bed"] = box(min(hx - BED_W / 2, hx - BED_W / 2 + dx * BED_L), min(hy, hy + dy * BED_L) if dy else hy - BED_W / 2,
                   max(hx + BED_W / 2, hx + BED_W / 2 + dx * BED_L), max(hy, hy + dy * BED_L) if dy else hy + BED_W / 2)
ROOM_BED = SP([(18.477, -26.641), (18.477, -23.951), (18.877, -23.951), (18.877, -23.791), (22.237, -23.791), (22.237, -24.101),
               (22.397, -24.101), (22.397, -26.591), (19.527, -26.591), (19.527, -26.641)])
HANG1_Y = (-27.291, -26.691)


def trays(o):
    """Open pull-out trays (dashed): 0.45 m along the bed from 0.35 m off the head, 0.25 m out of each side rail."""
    b = o["bed"]; x0, y0, x1, y1 = b.bounds
    ys = (o["head"][1] + o["toward"][1] * TRAY_V0, o["head"][1] + o["toward"][1] * TRAY_V1)
    ya, yb = min(ys), max(ys)
    return {"W": box(x0 - TRAY_PULL, ya, x0, yb), "E": box(x1, ya, x1 + TRAY_PULL, yb)}


def numbers(key):
    """Re-measure with the sketch engine (same walls, all doors open, furniture ignored for sight, obstacles for routes)."""
    o = OPT[key]
    base = O.opt_defs()["1a" if key == "1a" else "4"]
    solid = O.modelled(base); V = O.vps(base["cx"]); cnt = O.check(solid, V, O.targets())
    h1 = box(o["hers"][0], HANG1_Y[0], o["hers"][1], HANG1_Y[1])
    obst = unary_union([o["bed"], h1, S.HANG2, o["vanity"], S.PLANT])
    free = O.FRAME.difference(solid).difference(obst)
    R = S.route(free, O.P0, S.DRESSPT)
    pts = {"1a": [("W", (19.0, -25.8)), ("E", (21.55, -25.8))], "R3": [("W", (19.0, -24.8)), ("E", (21.6, -25.45))]}[key]
    night = {}
    for lab, p in pts:
        r = S.route(free, p, S.ENSUITE); night[lab] = (r["length"], round(r["widest_m"] * 1000))
    return dict(seeing=len(cnt), viewpoints=len(V), lobby_len=R["length"], lobby_narrow=round(R["widest_m"] * 1000), night=night)


# ---------------------------------------------------------------- sheet helpers
class Fig:
    def __init__(self, scale, ox, oy, crop=CROP, sh=None):
        self.sh = sh or plans._Sheet(0, 0, 0, 0, paper=PAPER, scale=scale)
        self.set(scale, ox, oy, crop)

    def set(self, scale, ox, oy, crop=CROP):
        sh = self.sh
        sh.scale, sh.ox, sh.oy = float(scale), ox, oy
        self.crop = crop
        sh.x0, sh.y0 = crop[1] * 1000, -crop[2] * 1000          # client west edge, client south edge (mm)
        self.w = (crop[3] - crop[1]) * 1000 / scale; self.h = (crop[2] - crop[0]) * 1000 / scale

    def P(self, x, y):
        return self.sh.p(y * 1000, -x * 1000)

    def poly(self, pts, fc="none", ec="k", lw=None, z=6, ls="-", hatch=None, alpha=1):
        lw = lw or standard.lw("proj", self.sh.scale)
        self.sh.ax.add_patch(MP([self.P(*q) for q in pts], closed=True, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls, hatch=hatch, alpha=alpha))

    def rect(self, r, **kw):
        x0, y0, x1, y1 = r.bounds
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], **kw)

    def line(self, a, b, lw=None, color="k", ls="-", z=7):
        self.sh.line(self.P(*a), self.P(*b), lw=lw or standard.lw("fine", self.sh.scale), color=color, ls=ls, z=z)

    def text(self, x, y, s, size=7, **kw):
        self.sh.text(self.P(x, y), s, size=size, **kw)

    def dim(self, a, b, d, label, size=7, z=9):
        """Dimension a->b (model m), line offset d paper-mm to the LEFT of a->b on the sheet; ticks, extension lines, value above."""
        pa, pb = self.P(*a), self.P(*b)
        L = math.hypot(pb[0] - pa[0], pb[1] - pa[1]); tx, ty = (pb[0] - pa[0]) / L, (pb[1] - pa[1]) / L
        nx, ny = -ty, tx
        a2, b2 = (pa[0] + nx * d, pa[1] + ny * d), (pb[0] + nx * d, pb[1] + ny * d)
        sg = 1 if d > 0 else -1
        for p, p2 in ((pa, a2), (pb, b2)):
            self.sh.line((p[0] + nx * sg * 1.0, p[1] + ny * sg * 1.0), (p2[0] + nx * sg * 1.4, p2[1] + ny * sg * 1.4), lw=0.15, z=z)
            self.sh.line((p2[0] - 0.9 * (tx + nx), p2[1] - 0.9 * (ty + ny)), (p2[0] + 0.9 * (tx + nx), p2[1] + 0.9 * (ty + ny)), lw=0.35, z=z)
        self.sh.line(a2, b2, lw=0.15, z=z)
        m = ((a2[0] + b2[0]) / 2 + nx * sg * 1.9, (a2[1] + b2[1]) / 2 + ny * sg * 1.9)
        rot = 0 if abs(tx) >= abs(ty) else 90
        self.sh.text(m, label, size=size, rot=rot, z=z + 1, bg=True)


def clip_new(fig, before):
    """Clip everything drawn since `before` to the crop rectangle on the sheet."""
    ax = fig.sh.ax
    c = fig.crop
    (x0, y0), (x1, y1) = fig.P(c[2], c[1]), fig.P(c[0], c[3])
    r = Rectangle((x0, y0), x1 - x0, y1 - y0, transform=ax.transData, fc="none", ec="none")
    for coll in (ax.patches[before[0]:], ax.lines[before[1]:]):
        for a in coll:
            a.set_clip_path(r)


# ---------------------------------------------------------------- base architecture via the project drawers
def variant_elements(key):
    els = list(EL)
    o = OPT[key]
    if o["door"] is not None:
        out = []
        for e in els:
            if e.id == "door-GF-parents-bed-parents-dressing":
                p = dict(e.params, hinge_xy_mm=[o["door"] * 1000 + 400, -26641.0], hinge_side="south", structural_opening_mm=900.0,
                         swing_basis="PROPOSAL (lane DF): moved to the west end of the head wall, hinged at the south jamb so the open leaf screens the doorway from the lobby",
                         span=["h", -26.641, 19.527, 22.597])
                e = dataclasses.replace(e, placement=[o["door"] * 1000, e.placement[1], e.placement[2]], params=p)
            out.append(e)
        els = out
    return els


def draw_base(fig, key, tags=True):
    sh = fig.sh
    before = (len(sh.ax.patches), len(sh.ax.lines))
    cels = orient.to_client(variant_elements(key))
    geo = plans._level_geometry(cels, "GF")
    c = fig.crop
    cx0, cy0, cx1, cy1 = c[1] * 1000, -c[2] * 1000, c[3] * 1000, -c[0] * 1000
    inside = lambda e: cx0 - 800 <= e.placement[0] <= cx1 + 800 and cy0 - 800 <= e.placement[1] <= cy1 + 800
    geo2 = dict(geo, doors=[e for e in geo["doors"] if inside(e)], windows=[e for e in geo["windows"] if inside(e)],
                walls=[w for w in geo["walls"] if max(w.params["x0_mm"], w.params["x1_mm"]) > cx0 and min(w.params["x0_mm"], w.params["x1_mm"]) < cx1
                       and max(w.params["y0_mm"], w.params["y1_mm"]) > cy0 and min(w.params["y0_mm"], w.params["y1_mm"]) < cy1],
                columns=[], stairs=[])
    plans._draw_walls(sh, geo2)
    rep = {}
    plans._draw_openings(sh, geo2, rep, coded=True)
    clip_new(fig, before)
    return geo2, cels


def sill_marks(fig):
    CROP = fig.crop
    """Window sill/reveal: extra projecting sill line on the room side of every window in the crop (sill height noted in tags)."""
    for e in EL:
        if e.kind != "window" or e.level != "GF" or not (CROP[0] < e.placement[0] / 1000 < CROP[2] and CROP[1] < e.placement[1] / 1000 < CROP[3]):
            continue
        x, y = e.placement[0] / 1000, e.placement[1] / 1000
        w = e.size[0] / 1000
        if abs(e.rotation_deg) < 1:             # window in a wall along model x (client east/west run): window spans x? no: along x
            yface = -23.791 if y > -25 else y
            fig.line((x - w / 2, yface - 0.02), (x + w / 2, yface - 0.02), lw=standard.lw("proj", fig.sh.scale), color=plans.WINDOW_COLOUR)
        else:
            xface = 22.397
            fig.line((xface - 0.02, y - w / 2), (xface - 0.02, y + w / 2), lw=standard.lw("proj", fig.sh.scale), color=plans.WINDOW_COLOUR)
        # tag: sill height
        if abs(e.rotation_deg) < 1:
            fig.text(x, -23.62 + 0.0, "", size=7)


# ---------------------------------------------------------------- furniture
def wavy(fig, a, b, amp, n, color, lw, z=7):
    """Curtain fold line between model points a,b (pleats perpendicular to the run)."""
    ax_, ay_ = a; bx_, by_ = b
    L = math.hypot(bx_ - ax_, by_ - ay_); ux, uy = (bx_ - ax_) / L, (by_ - ay_) / L; nx, ny = -uy, ux
    pts = []
    for i in range(n * 8 + 1):
        t = i / (n * 8); s = amp * math.sin(2 * math.pi * n * t)
        pts.append((ax_ + ux * L * t + nx * s, ay_ + uy * L * t + ny * s))
    for p, q in zip(pts, pts[1:]):
        fig.line(p, q, lw=lw, color=color, z=z)


def bed(fig, o, show_trays=True):
    (hx, hy), (dx, dy) = o["head"], o["toward"]
    loc = lambda a, b: (hx + dx * a + (-dy) * b, hy + dy * a + dx * b)      # a along bed from the head, b across (left of toward)
    rect = lambda a0, a1, b0, b1: [loc(a0, b0), loc(a1, b0), loc(a1, b1), loc(a0, b1)]
    w2 = BED_W / 2
    fig.poly(rect(0, BED_L, -w2, w2), fc="#eef3f7", ec="#345", lw=standard.lw("proj", fig.sh.scale), z=6)
    fig.poly(rect(-0.05, 0, -w2, w2), fc="#c9b79c", ec="#543", lw=standard.lw("fine", fig.sh.scale), z=7)      # 50 mm headboard
    for c in (-0.4, 0.4):
        fig.poly(rect(0.07, 0.52, c - 0.33, c + 0.33), fc="white", ec="#456", lw=standard.lw("fine", fig.sh.scale), z=7)   # pillows 0.45 x 0.66
    fig.line(loc(0.85, -w2), loc(0.85, w2), lw=standard.lw("fine", fig.sh.scale), color="#456")                         # duvet fold
    fig.line(loc(0.85, -w2 + 0.1), loc(1.7, -w2 + 0.1), lw=0.1, color="#9ab", ls=(0, (4, 3)))
    if show_trays:
        for side, tr in trays(o).items():
            fig.rect(tr, fc="#ffffff", ec="#000000", lw=standard.lw("proj", fig.sh.scale), ls=(0, (3, 2)), z=6.8)


def wardrobe(fig, x0, x1, yback, yfront, modules, kind):
    """Hanging run: carcass outline, module dividers, rail line (dashed) at the middle with hanger ticks on hanging modules."""
    fig.rect(box(x0, min(yback, yfront), x1, max(yback, yfront)), fc=TAN, ec=BROWN, z=6)
    x = x0; ym = (yback + yfront) / 2; sgn = 1 if yfront > yback else -1
    for name, w in modules:
        w = min(w, x1 - x)
        if name != modules[0][0] or x > x0:
            fig.line((x, yback), (x, yfront), lw=standard.lw("fine", fig.sh.scale), color=BROWN)
        if "hang" in name:
            fig.line((x + 0.02, ym), (x + w - 0.02, ym), lw=0.45, color="#222", ls=(0, (6, 1.5)), z=7)
            k = 0.05
            while x + k < x + w - 0.04:
                fig.line((x + k, ym - 0.13), (x + k, ym + 0.13), lw=0.12, color="#8a7a60", z=7); k += 0.09
        lab = {"long-hang": "LH", "double-hang": "DH", "drawers": "DR", "hat-shelf": "HS", "trousers-pullout": "TR", "shelves": "SH"}[name]
        fig.text(x + w / 2, ym + sgn * 0.20 if "hang" in name else ym, lab, size=7, color="#5a431f", z=8)
        x += w


def hers_modules(o):
    mods = [("long-hang", 0.65), ("double-hang", 0.45), ("drawers", 0.42), ("hat-shelf", 0.20)]
    if o["hers_order"] == "from_door":
        mods = [("hat-shelf", 0.20), ("drawers", 0.42), ("double-hang", 0.60), ("long-hang", 0.65)]     # +0.15 added to the double hang
    return mods


def furniture(fig, key):
    o = OPT[key]
    bed(fig, o)
    wardrobe(fig, o["hers"][0], o["hers"][1], HANG1_Y[1], HANG1_Y[0], hers_modules(o), "hers")
    wardrobe(fig, 19.854, 21.200, -28.831, -28.231, [("double-hang", 0.55), ("trousers-pullout", 0.25), ("drawers", 0.35), ("shelves", 0.196)], "his")
    v = o["vanity"]
    fig.rect(v, fc=TAN, ec=BROWN, z=6)
    x0, y0, x1, y1 = v.bounds
    fig.line((x1 - 0.03, y0 + 0.08), (x1 - 0.03, y1 - 0.08), lw=0.6, color="#7aa", z=7)                           # mirror on the wall
    fig.rect(box(x0 - 0.10, (y0 + y1) / 2 - 0.20, x0 + 0.20, (y0 + y1) / 2 + 0.20), fc="none", ec=BROWN, ls=(0, (2, 1.5)), lw=standard.lw("fine", fig.sh.scale), z=6)   # chair, tucked
    fig.poly(SP(S.PLANT).exterior.coords[:-1], fc="#d9ead0", ec="#3a6a2a", z=6) if False else fig.rect(S.PLANT, fc="#d9ead0", ec="#3a6a2a", z=6)
    # ensuite (outlines only)
    for e in EL:
        if e.kind == "furniture" and e.room == "parents-ensuite":
            pts = [(q[0], q[1]) for q in __import__("archpipe.drawings2d.layers", fromlist=["x"]).rect_poly(e.placement[0] / 1000, e.placement[1] / 1000, e.size[0] / 1000, e.size[1] / 1000, e.rotation_deg)]
            fig.poly(pts, fc="#f1f8f8", ec="#4a7f7f", z=6)
    # kids-b pieces in the crop (context)
    for e in EL:
        if e.kind == "furniture" and e.room == "kids-b" and e.level == "GF":
            from archpipe.drawings2d import layers as LL
            pts = LL.rect_poly(e.placement[0] / 1000, e.placement[1] / 1000, e.size[0] / 1000, e.size[1] / 1000, e.rotation_deg)
            fig.poly(pts, fc="#f6f6f6", ec="#999999", z=6)


def curtains(fig, key):
    """Heavy (0.15 m off the clear face) and sheer (0.10 m) on the 2.40 m window in the east wall; ceiling track; stacks 0.18 x width per side (ASSUMED, villa_render)."""
    o = OPT[key]
    xa, xb = 19.357, 21.757                                  # window 2400 centred x 20.557
    yh, ys = -23.791 - 0.15, -23.791 - 0.10
    st = 0.43
    if o["curtain"] == "both":      # R3: the head stands against the glass, so no draw curtain crosses it: fixed side panels + roller blackout in the reveal
        for lo, hi in ((xa - 0.18, xa - 0.18 + st), (xb + 0.18 - st, xb + 0.18)):
            fig.line((lo, yh - 0.05), (hi, yh - 0.05), lw=0.8, color="#444", ls=(0, (7, 1.2)), z=7)
            wavy(fig, (lo, yh), (hi, yh), 0.035, 3, "#444", 0.5)
        fig.line((xa, -23.745), (xb, -23.745), lw=1.1, color="#222", ls=(0, (9, 1.5, 1.5, 1.5)), z=7)
        fig.text(19.62, -24.95, "blackout roller (proposed)", size=7, color="#222", z=9) if False else None
    else:
        fig.line((xa - 0.18, yh - 0.05), (xb + 0.18, yh - 0.05), lw=0.8, color="#444", ls=(0, (7, 1.2)), z=7)               # track
        fig.line((xa, ys), (xb, ys), lw=0.25, color="#8899aa", ls=(0, (1.2, 1.2)), z=7)                                    # sheer drawn across
        a0 = 21.70; wavy(fig, (a0, yh), (22.376, yh), 0.035, 3, "#444", 0.5)
        wavy(fig, (a0, ys), (22.376, ys), 0.02, 3, "#8899aa", 0.3)
    # south window (2040 wide, centre y -25.421): same hanging, track 0.15 off the face; open, stacks at both jambs
    xh, xs = 22.397 - 0.15, 22.397 - 0.10
    ya, yb = -26.441, -24.401
    fig.line((xh - 0.05, ya - 0.18), (xh - 0.05, yb + 0.18), lw=0.8, color="#444", ls=(0, (7, 1.2)), z=7)
    fig.line((xs, ya), (xs, yb), lw=0.25, color="#8899aa", ls=(0, (1.2, 1.2)), z=7)
    wavy(fig, (xh, ya - 0.18), (xh, ya - 0.18 + 0.37), 0.035, 3, "#444", 0.5)
    wavy(fig, (xh, yb + 0.18 - 0.37), (xh, yb + 0.18), 0.035, 3, "#444", 0.5)


def slats(fig, y0, y1, x=18.477, deep=0.06):
    n = int((y1 - y0) / 0.06)
    for i in range(n):
        ya = y0 + i * 0.06 + 0.017
        fig.rect(box(x, ya, x + deep, ya + 0.03), fc="#d9a85f", ec="#6b4a1c", lw=0.12, z=6.5)


def lights(fig, key):
    """Plan marks for the wall reading lights/cove at the head (symbols as luminaires layer): swing-arm = triangle."""
    pass


# ---------------------------------------------------------------- rooms, labels, dimensions, legend
def room_label(fig, x, y, name, area):
    fig.text(x - 0.10, y, name, size=10, weight="bold", z=9)           # model x is the sheet's vertical axis (north = -x)
    fig.text(x + 0.12, y, "%.1f m\u00b2" % area, size=7, z=9)


def areas():
    out = {}
    for e in EL:
        if e.kind == "room" and e.level == "GF":
            out[e.room] = SP([(p[0] / 1000, p[1] / 1000) for p in e.params["net_polygon_mm"]]).area
    return out


def labels(fig, key):
    A = areas()
    room_label(fig, 19.0, -24.9, "BEDROOM", A["parents-bed"])
    room_label(fig, 21.75, -27.85, "DRESSING", A["parents-dressing"])
    room_label(fig, 18.98, -27.0, "LOBBY", A["parents-entry"])
    room_label(fig, 20.9, -29.85, "ENSUITE", A["parents-ensuite"])
    fig.sh.text(fig.P(17.0, -27.95), "CORRIDOR", size=10, weight="bold", rot=90, z=9)
    fig.text(16.65, -25.6, "KIDS B", size=10, weight="bold", z=9)
    for e in EL:                                                         # small fixture / furniture names, 7 pt
        if e.kind == "furniture" and e.level == "GF" and e.room in ("parents-ensuite", "kids-b", "parents-bed") and not e.id.startswith(("furn-pb-bed", "prop")):
            nm = {"bed_small_double": "bed", "washbasin": "basin", "desk": "vanity" if e.room == "parents-bed" else "desk"}.get(e.params["type"], e.params["type"])
            if e.id == "furn-pb-vanity":
                continue
            fig.text(e.placement[0] / 1000, e.placement[1] / 1000, nm, size=7, color="#335", z=9)
    v = OPT[key]["vanity"]; fig.text(v.bounds[0] + 0.30, (v.bounds[1] + v.bounds[3]) / 2, "vanity", size=7, color="#335", z=9)


def legend(fig_or_sh, x, y, key):
    sh = fig_or_sh
    rows = [("LH long hang   DH double hang   DR drawers   HS hat shelf   TR trousers   SH shelves", None),
            ]
    return y


def draw_text_block(sh, x, y, title, lines, width=62, size=7, pitch=3.7):
    sh.text((x, y), title, size=9, ha="left", weight="bold"); y -= 5.2
    for ln in lines:
        for i, w in enumerate(textwrap.wrap(ln, max(8, int(width / (size * 0.205)))) or [""]):
            sh.text((x + (0 if i == 0 else 2.5), y), w, size=size, ha="left"); y -= pitch
        y -= 0.8
    return y


def key_table(sh, x, y, header, rows, widths, size=7):
    """Table with wrapped cells; returns y below. Header is plain weight (bold is reserved for room names in sheetqa)."""
    cx = x
    for h, w in zip(header, widths):
        sh.text((cx, y), h, size=size, ha="left", color="#333333"); cx += w
    sh.line((x, y - 2.0), (x + sum(widths), y - 2.0), lw=0.3)
    y -= 5.2
    for r in rows:
        cx = x; hts = []
        for c, w in zip(r, widths):
            ls = textwrap.wrap(str(c), max(6, int((w - 1.5) / (size * 0.205)))) or [""]
            for i, t in enumerate(ls):
                sh.text((cx, y - i * 3.5), t, size=size, ha="left")
            hts.append(len(ls)); cx += w
        y -= 3.5 * max(hts) + 1.6
        sh.line((x, y + 2.0), (x + sum(widths), y + 2.0), lw=0.1, color="#bbbbbb")
    return y


def finish(sh, no, title, scale_txt, stem):
    """Project title block (plans._title_block) with the banner replaced: these are PROPOSALS, not the design model."""
    sheet = {"no": no, "title_en": title, "title_ar": "اقتراح تصميم، ليس نموذج التصميم المعتمد", "scale": scale_txt, "paper": "A3 landscape"}
    plans._title_block(sh, SPEC, sheet, 1, 1)
    x0 = PAPER[0] - plans.EDGE - plans.STRIP
    sh.ax.add_patch(Rectangle((x0 + 0.3, PAPER[1] - plans.EDGE - 14), plans.STRIP - 0.6, 13.7, fc="#b00020", ec="none", zorder=13))
    sh.text((x0 + plans.STRIP / 2, PAPER[1] - plans.EDGE - 6), "PROPOSAL (lane DF)", size=8, color="white", weight="bold", z=14)
    sh.text((x0 + plans.STRIP / 2, PAPER[1] - plans.EDGE - 11), "not the design model", size=7, color="white", z=14)
    sh.text((plans.LEFT + 4, PAPER[1] - plans.EDGE - 5), title, size=9, ha="left", weight="bold")
    sh.text((plans.LEFT + 4, PAPER[1] - plans.EDGE - 10.5), "%s on A3.  PROPOSAL: base is design model D1, varied in memory; nothing written back.  North is the street side." % scale_txt,
            size=7, ha="left", color="#b00020")
    sh.ax.add_patch(Rectangle((0, 0), PAPER[0], PAPER[1], fc="white", ec="none", zorder=-5))
    OUT.mkdir(parents=True, exist_ok=True)
    sh.fig.savefig(OUT / (stem + ".pdf"), facecolor="white")
    import matplotlib.pyplot as plt
    plt.close(sh.fig)
    import pymupdf
    d = pymupdf.open(str(OUT / (stem + ".pdf")))
    d[0].get_pixmap(dpi=150).save(str(OUT / (stem + ".png")))


# ---------------------------------------------------------------- the two plan sheets
def plan_sheet(key, no, title, stem, N, other):
    o = OPT[key]
    fig = Fig(50, 30, 120)
    sh = fig.sh
    geo, cels = draw_base(fig, key)
    sill_marks(fig)
    furniture(fig, key)
    curtains(fig, key)
    if o["slat"]:
        slats(fig, -26.641, -23.951)
        fig.text(18.66, -25.1, "slat wall (proposed)", size=7, color="#6b4a1c", z=9)
    labels(fig, key)
    # north arrow + scale bar (project drawer)
    gx = dict(geo, bbox=(CROP[1] * 1000, -CROP[2] * 1000, CROP[3] * 1000, -CROP[0] * 1000))
    plans._north_scale(sh, gx, "GF", SPEC["levels"])
    # dimensions (model m): bedsides at y -25.9 (clear of vanity and trays), foot gap, hers run, door leaf
    b = o["bed"]; bx0, by0, bx1, by1 = b.bounds
    fig.dim((18.477, -25.9), (bx0, -25.9), 0, "%d" % round((bx0 - 18.477) * 1000))
    fig.dim((bx1, -25.9), (22.397, -25.9), 0, "%d" % round((22.397 - bx1) * 1000))
    if key == "R3":
        fig.dim((21.0, by0), (21.0, -26.591), 0, "%d" % round((by0 + 26.591) * 1000))
        fig.text(19.95, -26.28, "new door", size=7, color="#a04000", z=9); fig.text(20.1, -26.28, "800 x 2100", size=7, color="#a04000", z=9)
    else:
        fig.dim((20.0, by1), (20.0, -23.791), 0, "%d" % round((-23.791 - by1) * 1000))
    h0, h1 = o["hers"]
    if key == "R3":
        fig.dim((h0, -26.591), (h1, -26.591), 4.5, "hers %d" % round((h1 - h0) * 1000))       # bedroom side of the head wall
    else:
        fig.dim((h0, -27.291), (h1, -27.291), -4.5, "hers %d" % round((h1 - h0) * 1000))      # dressing side (the bed head is on the other face)
    return fig, geo


def add_key(fig, key, N, other, title_note, items_right):
    sh = fig.sh
    # right column: legend + notes
    xr = 30 + fig.w + 14
    y = 257.0
    y = draw_text_block(sh, xr, y, "Legend", [
        "Walls: dark = external, hatched = internal (cut).  Orange = doors with swing arc, blue = window glazing and sill line.",
        "Hanging runs: dashed = hanging rail with hanger ticks.  LH long hang, DH double hang, DR drawers, HS hat shelf, TR trousers, SH shelves.",
        "Bed: head panel (tan), pillows, duvet fold; trays DASHED = pulled out 250 mm (model J[tray_pull_m]).",
        "Curtains: heavy 0.15 m, sheer 0.10 m off the wall, track dashed; stacks 0.18 x width per side (assumed in villa_render).",
        "Compass: client convention, street side = NORTH, sheet north-up. The earlier sketches were drawn in model axes "
        "(model +y up), so their 'north / west / south / east' = this sheet's EAST / NORTH / WEST / SOUTH."], width=116)
    y -= 2
    draw_text_block(sh, xr, y, items_right[0], items_right[1], width=116)


def key_dims_table(sh, x, y, N):
    rows = [
        ["Bedsides W / E (clear to wall, 750 benchmark)", N["1a"]["beds"], N["R3"]["beds"], "UK AD M 2.25a bedroom route 750, card ukadm-bedroom-route-750; benchmark, not code compliance"],
        ["Trays pulled 250: width left W / E", N["1a"]["trays"], N["R3"]["trays"], "East tray in R3 faces the vanity; 750 needed"],
        ["Lobby route to dressing: length, narrowest", N["1a"]["lobby"], N["R3"]["lobby"], "route from the public corridor (x 17.2), 20 mm grid, widest disc; narrowest = the 800 door leaf"],
        ["Night route bedside to ensuite: length, narrowest", N["1a"]["night"], N["R3"]["night"], "same engine; furniture as shown, trays closed"],
        ["Privacy, ALL suite doors open (451 outside viewpoints)", N["1a"]["priv"], N["R3"]["priv"], "scripts/df_privacy_rot.py engine; furniture and leaves ignored (worst case)"],
    ]
    return key_table(sh, x, y, ["Key dimension", "1a TODAY", "R3", "Basis"], rows, [64, 52, 52, 134])


def make_N():
    N = {}
    for k in ("1a", "R3"):
        n = numbers(k); o = OPT[k]; b = o["bed"]; bx0, _, bx1, _ = b.bounds
        w, e = bx0 - 18.477, 22.397 - bx1
        tw, te = w - TRAY_PULL, e - TRAY_PULL
        d = dict(seeing=n["seeing"], vp=n["viewpoints"])
        d["beds"] = "%d / %d mm" % (round(w * 1000), round(e * 1000)) + (" (%d at the vanity)" % round((21.997 - bx1) * 1000) if k == "R3" else "")
        d["trays"] = "%d / %d mm" % (round(tw * 1000), round(te * 1000)) + (" (%d at the vanity)" % round((21.997 - bx1 - TRAY_PULL) * 1000) if k == "R3" else "")
        d["lobby"] = "%s m, %d mm" % (n["lobby_len"], n["lobby_narrow"])
        nn = n["night"]
        d["night"] = "W %s m / %d mm;  E %s m / %d mm" % (nn["W"][0], nn["W"][1], nn["E"][0], nn["E"][1])
        d["priv"] = "%s: %d of %d see in" % ("PASS" if n["seeing"] == 0 else "FAIL", n["seeing"], n["viewpoints"])
        N[k] = d
    return N


def self_check():
    """Overlap guard: nothing drawn overlaps; trays inside the room; the open leaf clears the hanging and the bed (positive + one negative)."""
    for k, o in OPT.items():
        h1 = box(o["hers"][0], HANG1_Y[0], o["hers"][1], HANG1_Y[1])
        things = {"bed": o["bed"], "hers": h1, "vanity": o["vanity"], "plant": S.PLANT}
        names = list(things)
        for i, a in enumerate(names):
            for b_ in names[i + 1:]:
                assert not things[a].intersects(things[b_]), (k, a, b_)
        for s, t in trays(o).items():
            assert ROOM_BED.contains(t), (k, "tray", s)
        if o["door"] is not None:
            hinge = (o["door"] + 0.4, -26.641)
            leaf = SP([(hinge[0] - 0.02, hinge[1]), (hinge[0] + 0.02, hinge[1]), (hinge[0] + 0.02, hinge[1] - 0.8), (hinge[0] - 0.02, hinge[1] - 0.8)])
            assert not leaf.intersects(h1) and not leaf.intersects(o["bed"]), "open leaf hits"
            assert leaf.distance(h1) >= 0.07, leaf.distance(h1)      # 80 mm between the open leaf face and the hanging end
    # negative: a bed pushed 0.3 m onto the vanity must be caught
    from shapely import affinity
    assert affinity.translate(OPT["R3"]["bed"], 0.9, 0).intersects(OPT["R3"]["vanity"])
    assert affinity.translate(OPT["R3"]["bed"], 0, -0.5).intersects(box(19.9, -26.7, 20.4, -26.0)) 


def handing_study():
    """Which jamb should carry the hinge? Share of the dressing floor visible, with the open leaf as an obstacle, from (a) the lobby mouth
    just inside the bedroom and (b) the pillows of the R3 bed. Walls from the sketch engine (all doors open); furniture ignored."""
    base = O.opt_defs()["4"]; solid = O.modelled(base)
    T = [t for t in O.targets() if O.DRESS_Z.contains(Point(t))]
    sets = {"lobby mouth (bedroom, x 18.55..19.45)": [(round(18.55 + 0.1 * i, 2), -26.55) for i in range(10)],
            "R3 pillows (bed head)": [(20.04, -24.1), (20.84, -24.1)]}
    leaf = {"none": None,
            "hinge SOUTH jamb (x 20.377)": box(20.357, -27.441, 20.397, -26.641),
            "hinge NORTH jamb (x 19.577)": box(19.557, -27.441, 19.597, -26.641)}
    out = {}
    for ln, lf in leaf.items():
        sol = solid if lf is None else unary_union([solid, lf])
        out[ln] = {}
        for sn, V in sets.items():
            seen = set(t for v in V for t in T if O.sees(sol, v, t))
            out[ln][sn] = round(100 * len(seen) / len(T))
    return out


# ---------------------------------------------------------------- elevations (1:25)
ESC = 25.0


class Elev:
    def __init__(self, ox, oy):
        self.sh = plans._Sheet(0, 0, 0, 0, paper=PAPER, scale=ESC)
        self.ox, self.oy = ox, oy

    def U(self, u, z):
        return (self.ox + u * 1000 / ESC, self.oy + z * 1000 / ESC)

    def rect(self, u0, z0, u1, z1, fc="none", ec="k", lw=None, ls="-", z=4, hatch=None):
        a, b = self.U(u0, z0), self.U(u1, z1)
        self.sh.ax.add_patch(Rectangle(a, b[0] - a[0], b[1] - a[1], fc=fc, ec=ec, lw=lw or standard.lw("proj", ESC), ls=ls, zorder=z, hatch=hatch))

    def line(self, a, b, lw=None, color="k", ls="-", z=5):
        self.sh.line(self.U(*a), self.U(*b), lw=lw or standard.lw("fine", ESC), color=color, ls=ls, z=z)

    def text(self, u, z, t, size=7, **kw):
        self.sh.text(self.U(u, z), t, size=size, **kw)

    def dim(self, a, b, d, label, size=7):
        """a,b in (u,z) metres; d = paper-mm offset to the left of a->b."""
        pa, pb = self.U(*a), self.U(*b)
        L = math.hypot(pb[0] - pa[0], pb[1] - pa[1]); tx, ty = (pb[0] - pa[0]) / L, (pb[1] - pa[1]) / L; nx, ny = -ty, tx
        a2, b2 = (pa[0] + nx * d, pa[1] + ny * d), (pb[0] + nx * d, pb[1] + ny * d)
        sg = 1 if d > 0 else -1
        for p, p2 in ((pa, a2), (pb, b2)):
            self.sh.line((p[0] + nx * sg, p[1] + ny * sg), (p2[0] + nx * sg * 1.4, p2[1] + ny * sg * 1.4), lw=0.12, z=9)
            self.sh.line((p2[0] - 0.9 * (tx + nx), p2[1] - 0.9 * (ty + ny)), (p2[0] + 0.9 * (tx + nx), p2[1] + 0.9 * (ty + ny)), lw=0.35, z=9)
        self.sh.line(a2, b2, lw=0.15, z=9)
        m = ((a2[0] + b2[0]) / 2 + nx * sg * 2.0, (a2[1] + b2[1]) / 2 + ny * sg * 2.0)
        self.sh.text(m, label, size=size, rot=0 if abs(tx) >= abs(ty) else 90, z=10, bg=True)

    def room(self, W, H, left_label, right_label):
        """Floor, ceiling, the two cut end walls (poche), wall face outline."""
        self.rect(0, 0, W, H, fc="white", lw=standard.lw("fine", ESC), z=1)
        self.rect(-0.10, -0.05, 0, H + 0.05, fc="#d9d9d9", lw=standard.lw("cut", ESC), hatch="//////", z=3)
        self.rect(W, -0.05, W + 0.10, H + 0.05, fc="#d9d9d9", lw=standard.lw("cut", ESC), hatch="//////", z=3)
        self.line((-0.3, 0), (W + 0.4, 0), lw=standard.lw("cut", ESC), z=6)
        self.line((-0.3, H), (W + 0.4, H), lw=standard.lw("cut", ESC), z=6)
        self.text(-0.12, H * 0.5, left_label, size=7, ha="right", rot=90, color="#444")
        self.text(W + 0.12, H * 0.5, right_label, size=7, ha="left", rot=90, color="#444")


def pleats(e, u0, u1, z0, z1, color="#445", n=None):
    n = n or max(3, int((u1 - u0) / 0.055))
    for i in range(n + 1):
        u = u0 + (u1 - u0) * i / n
        e.line((u, z0), (u, z1), lw=0.2, color=color, z=5)


def elevation_bed_wall():
    """East window wall of R3 (the sketches' 'north'), seen from inside looking east. u = model x - 18.477, 0 at the slat (north) wall."""
    E = Elev(52, 146)
    W, H = 3.92, 2.70
    E.room(W, H, "", "")
    wa, wb = 19.357 - 18.477, 21.757 - 18.477                          # window 2400, piers 880 / 640
    E.rect(wa, 0.90, wb, 2.30, fc="#eaf4fb", ec=plans.WINDOW_COLOUR, z=2, lw=standard.lw("proj", ESC))
    E.rect(wa + 0.04, 0.94, wb - 0.04, 2.26, fc="none", ec=plans.WINDOW_COLOUR, z=2, lw=standard.lw("fine", ESC))
    E.line((wa - 0.03, 0.90), (wb + 0.03, 0.90), lw=standard.lw("cut", ESC), color="#222", z=5)                     # projecting sill
    # cove over the head: 2100 mm run (lum-COVE-parents-bed-01), at the ceiling
    bu0, bu1 = 20.437 - 0.8 - 18.477, 20.437 + 0.8 - 18.477            # bed 1.16..2.76
    cu0, cu1 = 20.437 - 1.05 - 18.477, 20.437 + 1.05 - 18.477
    E.rect(cu0, 2.58, cu1, 2.70, fc="#fff6cc", ec="#b8860b", z=5, lw=standard.lw("proj", ESC))
    for k in range(7):
        E.line((cu0 + 0.1 + k * 0.3, 2.64), (cu0 + 0.3 + k * 0.3, 2.64), lw=0.6, color="#b8860b", ls=(0, (3, 1.5)))
    # blackout roller in the reveal: cassette at the head, fabric drawn half down (dashed)
    E.rect(wa, 2.22, wb, 2.30, fc="#555", ec="k", z=5, lw=standard.lw("fine", ESC))
    E.rect(wa, 1.55, wb, 2.22, fc="none", ec="#222", ls=(0, (6, 2)), z=5, lw=standard.lw("fine", ESC))
    # fixed side drapes (heavy) beyond the jambs, floor to ceiling, track at the ceiling
    for lo, hi in ((wa - 0.18, wa - 0.18 + 0.43), (wb + 0.18 - 0.43, wb + 0.18)):
        E.rect(lo, 0.0, hi, 2.66, fc="#dcdfe6", ec="#445", z=4, lw=standard.lw("fine", ESC))
        pleats(E, lo, hi, 0.0, 2.66)
    E.line((wa - 0.20, 2.66), (wb + 0.20, 2.66), lw=0.8, color="#444", ls=(0, (7, 1.2)))
    # bed: deck to 0.525, 1.60 wide; MODEL headboard 1.35 (dashed) and the proposed low panel to the sill
    E.rect(bu0, 0.0, bu1, 0.525, fc="#eef3f7", ec="#345", z=6, lw=standard.lw("proj", ESC))
    E.rect(bu0, 0.525, bu1, 1.35, fc="none", ec="#a33", ls=(0, (6, 2)), z=7, lw=standard.lw("proj", ESC))
    E.rect(bu0, 0.525, bu1, 0.90, fc="#c9b79c", ec="#543", z=7, lw=standard.lw("proj", ESC))
    for c in (bu0 + 0.40, bu1 - 0.40):                                       # pillows
        E.rect(c - 0.33, 0.525, c + 0.33, 0.80, fc="white", ec="#456", z=8, lw=standard.lw("fine", ESC))
        # reading light clamped to the panel: post, arm, lamp head
        E.line((c, 0.90), (c, 1.20), lw=0.5, color="#222", z=9)
        E.line((c, 1.20), (c + 0.20, 1.12), lw=0.5, color="#222", z=9)
        E.rect(c + 0.15, 1.04, c + 0.28, 1.14, fc="#fff3c4", ec="#b8860b", z=9, lw=standard.lw("proj", ESC))
    E.text(bu0 + 0.80, 0.26, "bed 1600 x 2000, joinery, head to the glass", size=7)
    E.text(bu0 + 0.80, 0.835, "proposed low upholstered panel", size=7)
    E.text(wa + 1.2, 2.02, "window 2400 x 1400, sill 900", size=7, color=plans.WINDOW_COLOUR)
    E.text(wa + 1.2, 1.88, "roller blackout (proposed), shown half drawn", size=7, color="#222")
    E.text(wa + 1.2, 1.74, "reading lights clamped to the panel (proposed)", size=7, color="#222")
    E.text(wa + 1.2, 1.30, "model headboard to 1350", size=7, color="#a33")
    E.text((cu0 + cu1) / 2, 2.45, "cove 2100, LED 2700 K", size=7, color="#7a5a00")
    # dimensions: bottom chain, left vertical chain
    E.dim((0, 0), (wa, 0), -6, "880"); E.dim((wa, 0), (wb, 0), -6, "2400"); E.dim((wb, 0), (W, 0), -6, "640")
    E.dim((0, 0), (W, 0), -13, "3920 clear")
    E.dim((bu0, 0), (bu1, 0), -20, "bed 1600 (starts 1160 from the north wall)")
    x = -0.45
    for a_, b_, t in ((0, 0.525, "525"), (0.525, 0.90, "375"), (0.90, 2.30, "1400"), (2.30, 2.70, "400")):
        E.dim((x, a_), (x, b_), 0, t)
    E.dim((x - 0.35, 0), (x - 0.35, 2.70), 0, "CH 2700")
    E.text(W / 2, H + 0.30, "Seen from inside, looking east. Left = north (slat) wall, right = south wall (vanity window).", size=7, color="#444")
    return E, dict(window=(wa, wb), bed=(bu0, bu1))


def elevation_slat_wall():
    """North wall of R3 (the sketches' 'west'), seen from inside looking north. u = model y + 27.371, 0 at the lobby's south end."""
    E = Elev(52, 146)
    W, H = 3.58, 2.70                                                    # to the east window wall; wall plane ends at u 3.42, return 3.42..3.58
    E.room(W, H, "", "")
    E.rect(3.42, 0, W, H, fc="#efefef", ec="k", z=2, lw=standard.lw("fine", ESC))                 # 160 mm return face (x 18.877)
    E.text(3.50, 1.35, "return 160", size=7, rot=90, color="#444")
    E.rect(0.0, 0.0, 0.73, H, fc="#f7f7f7", ec="k", z=2, lw=standard.lw("fine", ESC))             # lobby portion, plain
    E.text(0.365, 1.35, "LOBBY\n(plain)", size=7, color="#444")
    u0, u1 = 0.73, 3.42
    E.rect(u0, 0.0, u1, H, fc="#4a3822", ec="#2b1f10", z=2, lw=standard.lw("proj", ESC))          # shadow gap / backing
    n = int(round((u1 - u0) / 0.06))
    for i in range(n):
        a = u0 + i * 0.06 + 0.015
        E.rect(a, 0.0, a + 0.03, H, fc="#d9a85f", ec="#6b4a1c", z=3, lw=0.08)
    # the R3 bed seen side-on in front of the wall (dashed): deck 0.525 and low panel to 0.90 at the head (east) end
    b0, b1 = -25.791 + 27.371, -23.791 + 27.371
    E.rect(b0, 0.0, b1, 0.525, fc="none", ec="#fff", ls=(0, (5, 2)), z=6, lw=standard.lw("proj", ESC))
    E.rect(b0, 0.0, b1, 0.525, fc="none", ec="#222", ls=(0, (2, 5)), z=6, lw=standard.lw("proj", ESC))
    E.rect(b1 - 0.05, 0.525, b1, 0.90, fc="#c9b79c", ec="#543", z=6, lw=standard.lw("fine", ESC))
    E.text((b0 + b1) / 2, 0.26, "R3 bed in front, 1160 off the wall (side view, dashed)", size=7, color="#fff")
    E.text((u0 + u1) / 2, 1.9, "SLAT FEATURE (proposed)", size=10, color="#fff", weight="bold") if False else None
    E.dim((0, 0), (0.73, 0), -6, "730"); E.dim((u0, 0), (u1, 0), -6, "2690 slats (solid wall run)")
    E.dim((0, 0), (3.42, 0), -13, "3420 wall run, 3580 to the window wall")
    E.dim((-0.45, 0), (-0.45, H), 0, "CH 2700")
    E.text(W / 2, H + 0.30, "Seen from inside, looking north. Left = west (dressing-side) wall, right = east window wall.", size=7, color="#444")
    return E, dict(slats=(u0, u1), n=n)


def key_plan(E, x, y, hl, view):
    """Small 1:100 R3 key plan on the elevation sheet; arrow shows the viewing direction. (x, y) = paper mm of the crop's SW corner."""
    crop = (17.4, -29.0, 22.75, -23.4)
    fig = Fig(100, x, y, crop, sh=E.sh)
    draw_base(fig, "R3"); sill_marks(fig)
    o = OPT["R3"]
    bed(fig, o, show_trays=False)
    h1 = o["hers"]; fig.rect(box(h1[0], HANG1_Y[0], h1[1], HANG1_Y[1]), fc=TAN, ec=BROWN, z=6)
    fig.rect(S.HANG2, fc=TAN, ec=BROWN, z=6)
    fig.rect(o["vanity"], fc=TAN, ec=BROWN, z=6)
    slats(fig, -26.641, -23.951)
    (px, py), (qx, qy) = view
    a, b = fig.P(px, py), fig.P(qx, qy)
    E.sh.ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", color="#c00", lw=1.0), zorder=12)
    E.sh.text((a[0], a[1] - 3.5), "view", size=7, color="#c00", z=12)
    E.sh.text((x, y - 3.5), "Key plan 1:100 (R3), N up", size=7, ha="left")
    return fig


def elevation_sheet(kind, N):
    if kind == "bed":
        E, info = elevation_bed_wall(); no, title, stem = "DF-103", "Parents' bedroom R3: bed wall elevation (east window wall)", "DF-103-elevation-R3-bed-wall"
        view = ((20.437, -26.0), (20.437, -24.9))             # looking east = +y
    else:
        E, info = elevation_slat_wall(); no, title, stem = "DF-104", "Parents' bedroom R3: slat wall elevation (north wall)", "DF-104-elevation-R3-slat-wall"
        view = ((20.0, -25.0), (19.0, -25.0))                 # looking north = -x
    sh = E.sh
    key_plan(E, 240, 204, None, view)
    draw_text_block(sh, 222, 196, "Notes", ELEV_NOTES[kind], width=96)
    key_dims_table(sh, 30, 92, N)
    return finish(sh, no, title, "1:25 (key plan 1:100)", stem)


ELEV_NOTES = {
    "bed": [
        "Window 2400 x 1400, sill 900, head 2300 (model window-GF-parents-bed-6); it is centred 120 mm south of the room centre (x 20.557 against 20.437).",
        "The bed is centred on the ROOM, so its head sits 120 mm off the glass centre: piers 880 north / 640 south of the glass, bed 1160 from the north wall.",
        "Model headboard is 50 mm thick and rises to 1350 (furniture.JOINERY_BED panel_z1): against this window it would hide the glass from 900 to 1350.",
        "Proposed: low upholstered panel, top at the sill (900). Reading lights move from the old head wall (1450 high, model) to arms clamped on the panel; supply needs a floor box (not designed).",
        "Heavy curtain track hangs 0.15 m off the wall in the model: with the head against the glass a draw curtain would cut through the pillows (pillows start 0.07 m off the wall). Drawn instead: fixed side drapes (stack 0.43 each) and a roller blackout in the reveal. Proposal, not in the model.",
        "Cove (2100, 2700 K, aim to the wall) is drawn where it is asked for; it will graze black glass at night. See hand-back."],
    "slat": [
        "Slat wall = the corridor-side wall of the bedroom (wall-GF-int-31, 100 partition, hatched). Solid run 2690 between the lobby and the 160 mm return; no door, no window, no socket drawn.",
        "Slats 30 x 40 at 60 pitch on a dark backing are ASSUMED sizes for the drawing; no slat detail is held for this wall. Existing model detail 'detail-headboard-slats' applies to the old head wall only.",
        "The bed is 1160 from this wall: the slat wall is a visible side wall, not a head wall. Nothing is fixed to it, so the trays and the west bedside are not affected.",
        "Running the slats through the lobby (730) would make the run 3420 and hide the lobby opening's edge; shown plain as the sketch assumed."],
}


def plan_notes(key, N, H):
    if key == "1a":
        return ("Today (1a), as in the design model", [
            "Bed 1600 x 2000, head on the dressing wall, centred x 20.33 (room centre 20.437: 107 mm east of centre; wall fittings are bound to it). Trays pull 250 mm from each rail.",
            "Dressing door 800 x 2100 at the SOUTH end of the head wall, hinged at the south jamb, leaf swings INTO the dressing room; pocket door 900 from the corridor into the lobby.",
            "Hers: hanging run 1720 along the head wall; his: 1346 along the ensuite wall.",
            "Curtains: heavy and sheer on the 2.4 m window, one-way draw, stacks parked east (CURTAIN_PARK); the south window is also curtained.",
            "Vanity 1000 x 400 under the south window; its floor-length curtain track runs through the vanity (0.15 m off a wall the vanity leans on): see hand-back.",
            "Privacy: all suite doors open, 0 of 451 outside viewpoints see the dressing room or ensuite."])
    return ("R3 proposal: what changes against today", [
        "1. Bed turned: head on the east window wall, centred on the room (x 20.437), 1160 clear each side, 800 at the foot.",
        "2. Dressing door moved to the north end of the west wall (model x 19.577..20.377): 800 x 2100 leaf, HINGED AT THE SOUTH JAMB, swings INTO the dressing room, pushed from the bedroom; hinges on your left as you face it from the bedroom.",
        "   Why the south jamb: open at 90 deg the leaf lies across the doorway side that a person coming from the lobby mouth looks along. Of the dressing floor seen from the lobby mouth: no leaf %d%%, south-hinged %d%%, north-hinged %d%%; from the pillows: %d / %d / %d%%." % (
            H["none"]["lobby mouth (bedroom, x 18.55..19.45)"], H["hinge SOUTH jamb (x 20.377)"]["lobby mouth (bedroom, x 18.55..19.45)"], H["hinge NORTH jamb (x 19.577)"]["lobby mouth (bedroom, x 18.55..19.45)"],
            H["none"]["R3 pillows (bed head)"], H["hinge SOUTH jamb (x 20.377)"]["R3 pillows (bed head)"], H["hinge NORTH jamb (x 19.577)"]["R3 pillows (bed head)"]),
        "3. Old dressing door (south end of the west wall) closed and built in; wall continuous behind hers.",
        "4. Hers hanging 1870 (+150 on the double hang) from the door jamb to the south wall; open leaf stops 80 mm short of it. His unchanged. Vanity kept south.",
        "5. Slat feature on the north (corridor-side) wall, 2690. Curtains: fixed side drapes + roller blackout; low upholstered head panel at the sill height (see DF-103).",
        "Not changed: walls, windows, ensuite, lobby, pocket door, ceilings."])


def build_plan(key, no, title, stem, N, H):
    fig, geo = plan_sheet(key, no, title, stem, N, None)
    sh = fig.sh
    xr = 30 + fig.w + 14
    y = 257.0
    y = draw_text_block(sh, xr, y, *plan_notes(key, N, H), width=116)
    y -= 2
    draw_text_block(sh, xr, y, "Legend", [
        "Walls: dark = external, hatched = internal (cut). Orange = door leaf and swing, blue = glazing and sill.",
        "Hanging: dashed rail with hanger ticks. LH long hang, DH double hang, DR drawers, HS hat shelf, TR trousers, SH shelves.",
        "Bed: head panel (tan), pillows, duvet fold. DASHED boxes = trays pulled out 250 mm.",
        "Curtains: wavy = gathered drapes, dashed bar = track, dotted = sheer.",
        "Compass: client convention, street side = NORTH, sheet north-up. The earlier sketches used model axes: their 'north / west / south / east' are this sheet's EAST / NORTH / WEST / SOUTH."], width=116)
    key_dims_table(sh, 30, 100, N)
    return finish(sh, no, title, "1:50", stem)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    self_check()
    N = make_N(); H = handing_study()
    print(json.dumps(N, indent=1)); print(json.dumps(H, indent=1))
    (OUT / "numbers.json").write_text(json.dumps(dict(numbers=N, handing=H), indent=1))
    build_plan("1a", "DF-101", "Parents' suite, TODAY (1a): furnished plan", "DF-101-plan-today-1a", N, H)
    build_plan("R3", "DF-102", "Parents' suite, R3 proposal: furnished plan", "DF-102-plan-R3", N, H)
    elevation_sheet("bed", N)
    elevation_sheet("slat", N)
