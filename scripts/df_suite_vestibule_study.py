"""Lane DF round 2: annex the east end of the GF corridor into the parents' suite (suite door + private vestibule).
PROPOSAL ONLY. Reads the design-model numbers (src/archpipe/model/data/d1-elements.json, clear faces), changes nothing, writes
1:50 plan sketches + results.json to docs/lanes/DF-suite-vestibule-study/.   Run: python scripts/df_suite_vestibule_study.py
Reuses the router and drawing helpers of the round-1 study (scripts/df_dressing_door_study.py)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import df_dressing_door_study as S
import df_suite_sightlines as SL
from shapely.geometry import box, Polygon, LineString
from shapely.ops import unary_union

OUT = S.OUT.parent / "DF-suite-vestibule-study"
S.X0, S.X1 = 15.80, 22.80                     # wider frame: the corridor west of the new door is drawn
XD = 17.50                                    # suite door wall centre (faces 17.45 / 17.55)
KB_JAMB_E, KB_HINGE = 17.139, 16.239          # kids-b leaf x 16.239..17.139 (door-GF-corridor-kids-b, hinge west, swings into kids-b)
CY0, CY1 = -28.471, -27.421                   # corridor clear faces (south wall 200 mm, north wall 100 mm axis -27.371)
END_X = 19.477                                # corridor end = face of wall-GF-int-32
BED_X0 = 20.437 - 0.8                         # bed centred on the room (x 20.437)

def build(store_d=0.30, store=(17.60, 18.60), xd_hinge="N", end_hinge="S", end_y=(-28.396, -27.496), end_leaf=0.80):
    xdoor = box(XD-0.05, -28.421, XD+0.05, -27.471)            # opening 0.95, leaf 0.85, 50 mm returns
    vest = box(XD+0.05, CY0, END_X, CY1)
    corr_w = box(S.X0, CY0, XD-0.05, CY1)
    pocket = box(18.527, CY1, 19.427, -27.321)                 # old parents-entry pocket door, unchanged
    lobby = S.box(18.477, -27.321, 19.477, -26.641)
    end_open = box(END_X, end_y[0], END_X+0.10, end_y[1])
    floors = unary_union([S.BED_ROOM, S.LOBBY_LINK, lobby, vest, corr_w, xdoor, pocket, S.DRESS, end_open])
    stor = box(store[0], CY0, store[1], CY0+store_d) if store_d else Polygon()
    # open leaves (conservative: a leaf at 90 deg is an obstacle 40 mm thick)
    leaf_x = box(XD+0.05, -27.471-0.04, XD+0.05+0.85, -27.471) if xd_hinge == "N" else box(XD+0.05, -28.421, XD+0.05+0.85, -28.421+0.04)
    if end_hinge == "S":
        leaf_e = box(END_X-end_leaf, end_y[0], END_X, end_y[0]+0.04)
    elif end_hinge == "N":
        leaf_e = box(END_X-end_leaf, end_y[1]-0.04, END_X, end_y[1])
    else:   # swings into the dressing, hinge north
        leaf_e = box(END_X+0.10, end_y[1]-0.04, END_X+0.10+end_leaf, end_y[1])
    hang1 = box(19.627, -27.291, S.HANG_E, -26.691)            # hers: whole head wall now free, 2.72 m run
    bed = box(BED_X0, S.BED_Y0, BED_X0+S.BED_W, S.BED_Y0+S.BED_L)
    obst = unary_union([bed, hang1, S.HANG2, S.VANITY, S.PLANT, stor, leaf_x, leaf_e])
    return dict(floors=floors, free=floors.difference(obst), bed=bed, hang1=hang1, stor=stor, leaf_x=leaf_x, leaf_e=leaf_e, xdoor=xdoor,
                vest=vest, end_open=end_open, store=store, store_d=store_d)

PUB = (17.20, -27.946)          # public side, just west of the suite door
PW = (BED_X0-0.40, -25.6); PE = (BED_X0+S.BED_W+0.40, -25.6)
def routes(g):
    f = g["free"]; R = {}
    R["public>bed (W side)"] = S.route(f, PUB, PW)
    R["public>dressing"] = S.route(f, PUB, S.DRESSPT)
    R["public>ensuite"] = S.route(f, PUB, S.ENSUITE)
    R["bedW>ensuite"] = S.route(f, PW, S.ENSUITE)
    R["bedE>ensuite"] = S.route(f, PE, S.ENSUITE)
    return R

def draw(key, title, g, R, extra_lines=()):
    S.sx = lambda x: (x - S.X0) * S.S
    floors = g["floors"]; W = (S.X1-S.X0)*S.S; H = (S.Y1-S.Y0)*-S.S*-1
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W/50:.1f}mm" height="{H/50+38:.1f}mm" viewBox="0 0 {W:.0f} {H+1900:.0f}">',
         f'<rect width="{W:.0f}" height="{H+1900:.0f}" fill="#fff"/>', f'<rect width="{W:.0f}" height="{H:.0f}" fill="#9a9a9a"/>',
         S.poly_svg(floors, fill="#fbf7ef", stroke="none")]
    # public part of the corridor tinted, suite vestibule tinted differently
    s.append(S.poly_svg(box(S.X0, CY0, XD-0.05, CY1), fill="#e9e9f2", stroke="none"))
    s.append(S.poly_svg(g["vest"], fill="#f3e9d6", stroke="none"))
    # kids-b door: opening, hinge, leaf at 90 deg (into kids-b), swing arc, approach strip 0.30 m
    s.append(S.poly_svg(box(KB_HINGE, -27.421, KB_JAMB_E, -27.321), fill="#fbf7ef", stroke="none"))
    s.append(f'<line x1="{S.sx(KB_HINGE):.0f}" y1="{S.sy(-27.371):.0f}" x2="{S.sx(KB_HINGE):.0f}" y2="{S.sy(-26.471):.0f}" stroke="#036" stroke-width="12"/>')
    s.append(f'<path d="M{S.sx(KB_JAMB_E):.0f},{S.sy(-27.371):.0f} A900,900 0 0 0 {S.sx(KB_HINGE):.0f},{S.sy(-26.471):.0f}" fill="none" stroke="#036" stroke-width="5" stroke-dasharray="20 14"/>')
    s.append(S.poly_svg(box(KB_HINGE, -27.721, KB_JAMB_E, -27.421), fill="#9bd", fill_opacity=".35", stroke="#369", stroke_width=4, stroke_dasharray="10 8"))
    s.append(S.poly_svg(box(17.20, -27.321, 18.377, -26.721), fill="#e5d3b3", stroke="#543", stroke_width=5))
    s.append(S.txt(17.79, -27.0, "kids-b wardrobe", 52, "#432", "middle"))
    s.append(S.txt(16.69, -26.95, "kids-b door 0.90", 52, "#036", "middle")); s.append(S.txt(16.69, -27.62, "approach 0.30", 46, "#369", "middle"))
    # suite door
    s.append(S.poly_svg(box(XD-0.05, CY0, XD+0.05, CY1), fill="#555", stroke="none"))
    s.append(S.poly_svg(g["xdoor"], fill="#fbf7ef", stroke="none"))
    lx = g["leaf_x"].bounds
    s.append(S.poly_svg(g["leaf_x"], fill="#036", stroke="#036", stroke_width=4))
    hy = -27.471
    s.append(f'<path d="M{S.sx(lx[2]):.0f},{S.sy(hy):.0f} A850,850 0 0 1 {S.sx(XD+0.05):.0f},{S.sy(hy-0.85):.0f}" fill="none" stroke="#036" stroke-width="5" stroke-dasharray="20 14"/>')
    s.append(S.txt(XD, -28.60, "suite door 0.85", 50, "#036", "middle"))
    # dressing door leaf (conservative: parked at 90 deg)
    s.append(S.poly_svg(g["leaf_e"], fill="#036", stroke="#036", stroke_width=4))
    # storage
    if not g["stor"].is_empty:
        s.append(S.poly_svg(g["stor"], fill="#e5d3b3", stroke="#543", stroke_width=5))
        b = g["stor"].bounds; s.append(S.txt((b[0]+b[2])/2, -28.34, f"storage {g['store_d']*1000:.0f}", 50, "#432", "middle"))
    # head wall slats, bed, trays, furniture (same style as round 1)
    for p, q in [(19.527, 22.397)]:
        s.append(f'<rect x="{S.sx(p):.0f}" y="{S.sy(-26.591)-4:.0f}" width="{(q-p)*S.S:.0f}" height="60" fill="#8b5a2b"/>')
    s.append(S.txt(20.96, -26.50, "slat wall (solid, no door)", 55, "#fff", "middle"))
    s.append(S.poly_svg(g["bed"], fill="#d8e4ee", stroke="#345", stroke_width=6)); s.append(S.txt(BED_X0+0.8, -25.4, "bed 1.60 x 2.00", 70, "#234", "middle"))
    for xs_, sign in ((BED_X0, -1), (BED_X0+S.BED_W, 1)):
        t = box(min(xs_, xs_+sign*S.TRAY), -25.9, max(xs_, xs_+sign*S.TRAY), -25.0)
        s.append(S.poly_svg(t, fill="none", stroke="#c33", stroke_width=5, stroke_dasharray="25 15"))
    s.append(S.poly_svg(S.VANITY, fill="#e6dccb", stroke="#543", stroke_width=5)); s.append(S.poly_svg(S.PLANT, fill="#cfe5c4", stroke="#363", stroke_width=5))
    s.append(S.poly_svg(S.HANG2, fill="#e5d3b3", stroke="#543", stroke_width=5)); s.append(S.txt(20.53, -28.55, "his hanging", 60, "#432", "middle"))
    s.append(S.poly_svg(g["hang1"], fill="#e5d3b3", stroke="#543", stroke_width=5)); s.append(S.txt(21.0, -27.03, "hers hanging 2.72 m", 60, "#432", "middle"))
    cols = {"public>bed (W side)": "#d62", "public>dressing": "#07a", "bedW>ensuite": "#a0a", "bedE>ensuite": "#090"}
    for n, c in cols.items():
        r = R[n]
        if r.get("path"):
            s.append(f'<polyline points="{" ".join(f"{S.sx(x):.0f},{S.sy(y):.0f}" for x, y in r["path"])}" fill="none" stroke="{c}" stroke-width="14" stroke-opacity=".85" stroke-linejoin="round"/>')
    for x, y, t in ((16.0, -28.1, "public corridor"), (18.5, -28.0, "VESTIBULE (private)"), (19.0, -26.95, "lobby"), (20.9, -24.0, "bedroom"),
                    (21.0, -27.76, "dressing walkway"), (19.0, -27.37+0.07, "old entry pocket door 0.90")):
        s.append(S.txt(x, y, t, 52, "#556", "middle"))
    s.append(S.txt(16.0, -27.0, "to stair <-- kids' escape route", 50, "#a00", "middle"))
    s.append(f'<line x1="{S.sx(16.0):.0f}" y1="{S.sy(-23.75):.0f}" x2="{S.sx(17.0):.0f}" y2="{S.sy(-23.75):.0f}" stroke="#000" stroke-width="14"/>' + S.txt(16.5, -23.68, "1 m", 55, "#000", "middle"))
    s.append(f'<text x="30" y="{H+90:.0f}" font-size="85" font-weight="bold" font-family="Arial">{title}</text>')
    def f(n):
        r = R[n]; L = "no route" if r["length"] is None else f'{r["length"]:.1f} m'
        return f'{L} (widest {r["widest_m"]*1000:.0f})'
    lines = [f'orange public>bed (W) {f("public>bed (W side)")}', f'blue public>dressing {f("public>dressing")}',
             f'purple W bedside>ensuite {f("bedW>ensuite")}', f'green E bedside>ensuite {f("bedE>ensuite")}', *extra_lines,
             "scale 1:50 at print size; design-model metres; routes = centrelines of a 750 body where one exists, widest = narrowest clear point (mm); open leaves drawn at 90 deg"]
    for i, l in enumerate(lines): s.append(f'<text x="30" y="{H+190+i*105:.0f}" font-size="62" font-family="Arial" fill="#222">{l}</text>')
    s.append("</svg>"); (OUT / f"plan-{key}.svg").write_text("\n".join(s))

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    res = {}
    VAR = {
      "E1": ("E1: suite door + vestibule, 0.30 storage, dressing door out-swing to the vestibule (hinge S)", dict(end_hinge="S", store=(17.60, 18.60))),
      "E2": ("E2: as E1 but dressing door swings into the dressing room (hinge N), storage the full vestibule", dict(end_hinge="I", store=(17.60, 19.15))),
      "E3": ("E3: no storage in the vestibule (reference: widest route)", dict(store_d=0, end_hinge="S")),
      "E4": ("E4: 0.60 hanging along the south wall (Neufert depth) - fails the passage", dict(store_d=0.60, end_hinge="S", store=(17.60, 18.60))),
    }
    for k, (title, kw) in VAR.items():
        g = build(**kw); R = routes(g)
        pubw = g["free"].intersection(box(XD+0.05, CY0, END_X, CY1))
        res[k] = dict(title=title, routes={n: {a: b for a, b in r.items() if a != "path"} for n, r in R.items()},
                      vest_len=round(END_X-(XD+0.05), 3), vest_w=round(CY1-CY0, 3), store_d=kw.get("store_d", 0.30),
                      passage_beside_store=round((CY1-CY0)-kw.get("store_d", 0.30), 3))
        draw(k, title, g, R)
    (OUT / "results.json").write_text(json.dumps(res, indent=1))
    for k, v in res.items():
        print(k, v["title"], "passage", v["passage_beside_store"])
        for n, r in v["routes"].items(): print("   ", n, r["length"], r["widest_m"], r["at_750"])
