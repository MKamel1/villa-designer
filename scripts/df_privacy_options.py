"""Lane DF: quick privacy OPTION SKETCHES (1:50 SVG/PNG) for the parents' suite. PROPOSAL ONLY: no spec/model/render change.
Sightlines: 2D, all suite doors OPEN, furniture ignored (worst case), model walls from d1-elements.json (df_privacy_engine).
Run: python scripts/df_privacy_options.py  -> docs/lanes/DF-privacy-options/{plan-*.svg,results.json}  (PNG via inkscape/cairosvg/rsvg if present)"""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from df_privacy_engine import *
import df_dressing_door_study as S
from shapely.geometry import box, Polygon, Point, LineString
from shapely.ops import unary_union

OUT = Path(__file__).resolve().parents[1] / "docs/lanes/DF-privacy-options"
X0, X1, Y0, Y1 = 15.8, 22.8, -31.30, -23.55
FRAME = box(X0, Y0, X1, Y1)
U = 1000.0
sx = lambda x: (x-X0)*U
sy = lambda y: (Y1-y)*U
HW = box(21.497, -26.691, 22.297, -26.591)                    # head-wall door opening (closed with slat-clad wall when moved)
SUITE = box(17.45, CY0, 17.55, CY1); SUITE_CUT = box(17.45, -28.421, 17.55, -27.471)
BED_Y0, BED_W, BED_L = S.BED_Y0, S.BED_W, S.BED_L
P0, DRESSPT = (17.2, -27.95), S.DRESSPT
KIDSB = ((16.239, -27.371), (17.139, -27.371), (16.239, -26.471))
ENS = ((22.05, -28.881), (21.25, -28.881), (22.05, -29.681))

def opt_defs():
    o = {}
    o["1a"] = dict(title="1a TODAY as modelled: dressing door in the head wall (east end)", add=[], cut=[], cx=19.4,
        bed_x0=19.53, hang1=(19.627, 21.347), stor=[], doors=[("sw", *((22.297, -26.641), (21.497, -26.641), (22.297, -27.441))), ("pocket", 18.527, 19.427, -27.371)],
        note="PASSES: the doorway is at the far east of the head wall; no straight line from the corridor reaches it.",
        extra=["arrival to dressing 9.2 m round the bed (earlier study)", "kids-b door: public approach unchanged"])
    o["1b"] = dict(title="1b TODAY + the A3 dressing door we last proposed (lobby wall, sliding)", cx=19.4,
        add=[box(18.427, -27.571, 19.527, -27.471), HW], cut=[box(18.427, -27.421, 19.527, -27.321), box(19.477, -27.471, 19.577, -26.691), box(18.527, -27.571, 19.427, -27.471)],
        bed_x0=20.437-0.8, hang1=(20.31, 22.347), stor=[], doors=[("pocket", 18.527, 19.427, -27.521), ("slide", 19.58, -27.471, -26.691)],
        note="FAILS: shallow rays along the corridor wall pass the open entry pocket and the open lobby door and land in the dressing room.",
        extra=["lobby door 0.78 clear; corridor narrows 1.05 > 0.90 at the lobby", "arrival to dressing 2.3 m"])
    o["2"] = dict(title="2 CLIENT IDEA: annex vestibule, suite door across the corridor, door straight into the dressing room", cx=17.4,
        add=[SUITE, HW], cut=[SUITE_CUT, box(19.477, -28.346, 19.577, -27.546)],
        bed_x0=20.437-0.8, hang1=(19.627, 22.347), stor=[box(17.60, CY0, 18.60, CY0+0.30)],
        doors=[("sw", (17.55, -27.471), (17.55, -28.421), (18.40, -27.471)), ("sw", (19.577, -27.546), (19.477, -27.546), (20.377, -27.546)), ("pocket", 18.527, 19.427, -27.371)],
        note="FAILS: suite door, vestibule and dressing door sit on ONE axis; an open pair shows the dressing room from 14 m away.",
        extra=["vestibule 1.93 x 1.05; suite door 0.85, dressing door 0.80 (leaf)", "kids-b approach stays public (door jamb 17.14, suite door 17.45)"])
    o["3"] = dict(title="3 DOG-LEG: annex vestibule with a cross wall and a 1.2 m south bump-out, so the three openings never line up", cx=17.4,
        add=[SUITE, HW, box(18.5, CY0, 18.6, CY1), box(18.5, -27.421, 18.6, -27.321), box(17.45, -29.771, 17.55, -28.471), box(17.45, -29.771, 19.604, -29.671), box(19.477, -29.771, 19.604, -28.471)],
        cut=[SUITE_CUT, box(19.477, -28.346, 19.577, -27.546), box(18.6, -27.421, 19.427, -27.321), box(17.55, -28.671, 19.477, -28.471)],
        bed_x0=20.437-0.8, hang1=(19.627, 22.347), stor=[box(17.60, -29.671, 19.40, -29.321)],
        doors=[("sw", (17.55, -27.471), (17.55, -28.421), (18.40, -27.471)), ("sw", (19.577, -27.546), (19.477, -27.546), (20.377, -27.546)), ("pocket", 18.6, 19.427, -27.371)],
        note="PASSES: the cross wall closes the axis; the walk turns south round it, east, then north to the dressing door. No ray can turn that corner.",
        extra=["entry bay 0.95 wide; passage 0.85 beside 0.35 storage; pocket re-set 0.83", "needs 1.2 x 1.9 m outside the south facade (planning/site check)"])
    o["4"] = dict(title="4 MINIMAL: no annex; dressing door moved to the WEST end of the head wall", cx=19.4,
        add=[HW], cut=[box(19.577, -26.691, 20.377, -26.591)],
        bed_x0=20.427, hang1=(20.477, 22.347), stor=[],
        doors=[("sw", (20.377, -26.641), (19.577, -26.641), (20.377, -27.441)), ("pocket", 18.527, 19.427, -27.371)],
        note="PASSES the lines, but the bed cannot stay centred: it must sit east of the door.",
        extra=["east bedside 0.37 m (0.12 with a tray out); 750 needed (earlier study B)", "arrival to dressing 3.8 m; head wall broken at the west end"])
    return o

def modelled(op):
    add, cut = op["add"], op["cut"]
    return solid_for(add, cut)

def route_len(op, solid):
    bed = box(op["bed_x0"], BED_Y0, op["bed_x0"]+BED_W, BED_Y0+BED_L)
    h1 = box(op["hang1"][0], -27.291, op["hang1"][1], -26.691)
    obst = unary_union([bed, h1, S.HANG2, S.VANITY, S.PLANT, *op["stor"]])
    free = FRAME.difference(solid).difference(obst)
    return S.route(free, P0, DRESSPT), bed, h1

def poly_path(g, fill, stroke="none", op=1.0, sw=4, dash=""):
    gs = g.geoms if hasattr(g, "geoms") else [g]
    d = ""
    for p in gs:
        if p.is_empty or p.geom_type != "Polygon": continue
        for ring in [p.exterior, *p.interiors]:
            d += "M" + " L".join(f"{sx(x):.0f},{sy(y):.0f}" for x, y in ring.coords) + "Z "
    return f'<path d="{d}" fill="{fill}" fill-opacity="{op}" fill-rule="evenodd" stroke="{stroke}" stroke-width="{sw}" {dash}/>'
def T(x, y, s, size=55, fill="#222", anchor="middle", w="normal"):
    return f'<text x="{sx(x):.0f}" y="{sy(y):.0f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-family="Arial" font-weight="{w}">{s}</text>'

def door_svg(d):
    s = []
    if d[0] == "sw":
        _, h, c, o = d; r = math.dist(h, c)
        s.append(f'<line x1="{sx(h[0]):.0f}" y1="{sy(h[1]):.0f}" x2="{sx(o[0]):.0f}" y2="{sy(o[1]):.0f}" stroke="#036" stroke-width="14"/>')
        cross = (c[0]-h[0])*(o[1]-h[1]) - (c[1]-h[1])*(o[0]-h[0]); sweep = 0 if cross > 0 else 1
        s.append(f'<path d="M{sx(c[0]):.0f},{sy(c[1]):.0f} A{r*U:.0f},{r*U:.0f} 0 0 {1-sweep} {sx(o[0]):.0f},{sy(o[1]):.0f}" fill="none" stroke="#036" stroke-width="5" stroke-dasharray="20 14"/>')
    elif d[0] == "pocket":
        _, a, b, y = d
        s.append(f'<rect x="{sx(a):.0f}" y="{sy(y)-70:.0f}" width="{(b-a)*U:.0f}" height="40" fill="none" stroke="#036" stroke-width="7" stroke-dasharray="25 12"/>')
        s.append(T((a+b)/2, y+0.14, "pocket door (open)", 38, "#036"))
    elif d[0] == "slide":
        _, x, y0, y1 = d
        s.append(f'<rect x="{sx(x):.0f}" y="{sy(y1):.0f}" width="40" height="{(y1-y0)*U:.0f}" fill="none" stroke="#036" stroke-width="8" stroke-dasharray="30 12"/>')
    return "\n".join(s)

def draw(key, op, solid, R, cnt, V, bed, h1):
    W, H = (X1-X0)*U, (Y1-Y0)*-U*-1
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W/50:.1f}mm" height="{(H+2100)/50:.1f}mm" viewBox="0 0 {W:.0f} {H+2100:.0f}">',
         f'<rect width="{W:.0f}" height="{H+2100:.0f}" fill="#fff"/>', f'<rect width="{W:.0f}" height="{H:.0f}" fill="#fafafa"/>']
    # fans from three worst-case public viewpoints
    views = [(9.0, -27.5), (15.4, -27.5), (16.689, -27.3)]
    ins = [v for v in cnt]
    if ins: views[0] = min(ins, key=lambda v: v[0])[:2]            # farthest viewpoint that sees in (if any)
    redz = unary_union([DRESS_Z, ENS_Z, ENS_DOOR_Z])
    fans = unary_union([fan(solid, v) for v in views]).intersection(FRAME)
    s.append(poly_path(fans, "#ffd84d", op=0.40))
    s.append(poly_path(fans.intersection(redz), "#e01010", op=0.55))
    for v in views: s.append(f'<circle cx="{sx(v[0]):.0f}" cy="{sy(v[1]):.0f}" r="35" fill="#a60" />')
    # red rays: from the far viewpoint to visible protected points
    if ins:
        v0 = views[0]; seen = cnt[min(ins, key=lambda v: v[0])]
        for t in seen[:: max(1, len(seen)//14)]:
            s.append(f'<line x1="{sx(v0[0]):.0f}" y1="{sy(v0[1]):.0f}" x2="{sx(t[0]):.0f}" y2="{sy(t[1]):.0f}" stroke="#c00" stroke-width="5" stroke-opacity=".7"/>')
    # walls
    s.append(poly_path(solid.intersection(FRAME), "#5a5a5a"))
    # protected zone outline
    s.append(poly_path(DRESS_Z, "none", "#c00", sw=8, dash='stroke-dasharray="30 14"'))
    s.append(poly_path(ENS_Z, "none", "#c00", sw=8, dash='stroke-dasharray="30 14"'))
    # furniture
    s.append(poly_path(bed, "#d8e4ee", "#345", sw=6)); s.append(T((bed.bounds[0]+bed.bounds[2])/2, -25.4, "bed 1.60 x 2.00", 60, "#234"))
    s.append(poly_path(h1, "#e5d3b3", "#543", sw=5)); s.append(T((h1.bounds[0]+h1.bounds[2])/2, -27.03, f"hers hanging {h1.bounds[2]-h1.bounds[0]:.2f} m", 48, "#432"))
    s.append(poly_path(S.HANG2, "#e5d3b3", "#543", sw=5)); s.append(T(20.5, -28.55, "his hanging", 48, "#432"))
    s.append(poly_path(S.VANITY, "#e6dccb", "#543", sw=5)); s.append(poly_path(S.PLANT, "#cfe5c4", "#363", sw=5))
    for st in op["stor"]:
        s.append(poly_path(st, "#e5d3b3", "#543", sw=5)); b = st.bounds; s.append(T((b[0]+b[2])/2, (b[1]+b[3])/2-0.05, f"storage {(b[3]-b[1])*1000:.0f}", 44, "#432"))
    s.append(f'<rect x="{sx(op["bed_x0"] if key!="1a" else 19.53):.0f}" y="{sy(-26.591)-4:.0f}" width="0" height="0"/>')
    # doors
    for d in [("sw", *KIDSB), ("sw", *ENS)] + op["doors"]: s.append(door_svg(d))
    for x, y, t in ((16.3, -28.1, "public corridor"), (21.0, -24.2, "bedroom"), (21.0, -27.8, "dressing"), (21.15, -29.95, "ensuite"), (16.69, -27.55, "kids-b door 0.90"),
                    (17.78, -26.95, "kids-b"), (20.9, -26.52, "head wall")):
        s.append(T(x, y, t, 46, "#556"))
    s.append(T(16.0, -23.7, "yellow = what a person outside sees (3 viewpoints, all doors open). RED = sightline reaches the dressing room / ensuite", 40, "#222", "start"))
    s.append(f'<line x1="{sx(16.0):.0f}" y1="{sy(-30.9):.0f}" x2="{sx(17.0):.0f}" y2="{sy(-30.9):.0f}" stroke="#000" stroke-width="14"/>' + T(16.5, -30.82, "1 m", 50, "#000"))
    if op.get("vest"): pass
    # caption
    ok = not cnt; col = "#080" if ok else "#c00"
    s.append(f'<text x="30" y="{H+90:.0f}" font-size="78" font-weight="bold" font-family="Arial">{op["title"]}</text>')
    far = max((math.dist(v[:2], t) for v in cnt for t in cnt[v]), default=0)
    verdict = ("PASS: 0 of %d outside viewpoints see the ensuite exit, dressing room or route" % len(V)) if ok else \
              ("FAIL: %d of %d outside viewpoints see into the dressing room / ensuite (up to %.0f m away; incl. the stair landing)" % (len(cnt), len(V), far))
    s.append(f'<text x="30" y="{H+195:.0f}" font-size="70" font-weight="bold" fill="{col}" font-family="Arial">{verdict}</text>')
    L = "no 750 route" if R["length"] is None else f'{R["length"]:.1f} m'
    lines = [op["note"], f'public corridor (x 17.2) to the dressing room: {L}, narrowest clear {R["widest_m"]*1000:.0f} mm (750 needed); ' + "; ".join(op["extra"][:1]),
             op["extra"][1] if len(op["extra"]) > 1 else "", "1:50 at print size; design-model metres; open leaves shown at 90 deg; walls 100 mm; sightlines ignore furniture (worst case)"]
    for i, l in enumerate(lines): s.append(f'<text x="30" y="{H+300+i*105:.0f}" font-size="58" font-family="Arial" fill="#222">{l}</text>')
    s.append("</svg>"); (OUT / f"plan-{key}.svg").write_text("\n".join(s))
    return ok, far

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    Tg = targets(); res = {}
    for k, op in opt_defs().items():
        solid = modelled(op); V = vps(op["cx"]); cnt = check(solid, V, Tg)
        R, bed, h1 = route_len(op, solid)
        ok, far = draw(k, op, solid, R, cnt, V, bed, h1)
        res[k] = dict(title=op["title"], viewpoints=len(V), seeing=len(cnt), pass_=ok, farthest_m=round(far, 1),
                      route_m=R["length"], narrowest_mm=round(R["widest_m"]*1000), landing_sees=any(v[2] == "stair landing" for v in cnt),
                      kidsb_sees=any(v[2].startswith("kids-b") for v in cnt))
        print(k, res[k])
    (OUT / "results.json").write_text(json.dumps(res, indent=1))
