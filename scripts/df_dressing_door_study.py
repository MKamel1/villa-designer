"""Lane DF layout study: where the parents' dressing-room door goes. PROPOSAL ONLY: reads the design-model numbers
typed below (taken from src/archpipe/model/data/d1-elements.json clear polygons), changes nothing, and writes plan
sketches (1:50) plus results.json under docs/lanes/DF-dressing-door-study/.  Run: python scripts/df_dressing_door_study.py"""
import heapq, json, math
from pathlib import Path
from shapely.geometry import box, Polygon, LineString, Point
from shapely.ops import unary_union

OUT = Path(__file__).resolve().parents[1] / "docs/lanes/DF-dressing-door-study"
R_ROUTE = 0.375            # 750 mm route (ukadm-bedroom-route-750) -> disc radius
BED_W, BED_L, BED_Y0 = 1.6, 2.0, -26.591     # bed head on the head-wall face; foot at -24.591
TRAY = 0.25
HANG_E = 22.347            # east end of the head-wall hanging (east wall clear face 22.397 - 0.05)
DRAWERS_HAT = 0.62         # drawers .42 + hat-shelf .20 stay in the run (modules of furn-pd-hang-1)

def P(pts): return Polygon(pts)
BED_ROOM = P([(18.477,-26.641),(18.477,-23.951),(18.877,-23.951),(18.877,-23.791),(22.237,-23.791),(22.237,-24.101),
              (22.397,-24.101),(22.397,-26.591),(19.527,-26.591),(19.527,-26.641)])
LOBBY_LINK = box(18.477,-26.70,19.477,-26.54)          # lobby is open to the bedroom
DRESS = P([(19.804,-28.471),(19.577,-28.471),(19.577,-26.691),(22.397,-26.691),(22.397,-28.161),(22.237,-28.161),
           (22.237,-28.471),(22.124,-28.471),(22.124,-28.831),(19.804,-28.831)])
VANITY = box(21.997,-25.30,22.397,-24.30); PLANT = box(22.056,-24.164,22.397,-23.796)
HANG2 = box(19.854,-28.831,21.200,-28.231)
ENTRY, DRESSPT, ENSUITE = (18.977,-27.30), (21.0,-27.76), (21.65,-28.60)

def corridor(dy):   # dy = how far the lobby's corridor wall moves south (A3)
    return P([(18.0,-28.471),(19.477,-28.471),(19.477,-27.421-dy),(18.427,-27.421-dy),(18.427,-27.421),(18.0,-27.421)])
def lobby(dy): return box(18.477,-27.321-dy,19.477,-26.641)
def main_door(dy): return box(18.527,-27.421-dy,19.427,-27.321-dy)

def options():
    o = {}
    # reference: today
    o["O"] = dict(title="Today: door at the east end of the head wall", bed_x0=19.53, dy=0,
                  links=[box(21.497,-26.691,22.297,-26.591)], hang=(19.627, 21.347), door=("swing",(22.297,-26.641),(-1,0),(0,-1),0.8))
    # A: lobby -> dressing, west wall x 19.527
    o["A1"] = dict(title="A1: hinged door lobby -> dressing (as the wall allows)", bed_x0=20.437-0.8, dy=0,
                   links=[box(19.477,-27.321,19.577,-26.691)], hang=None, hang_from_door=19.577, door=("slide",))
    o["A2"] = dict(title="A2: sliding door lobby -> dressing, lobby unchanged", bed_x0=20.437-0.8, dy=0,
                   links=[box(19.477,-27.321,19.577,-26.691)], hang=None, hang_from_door=19.577, door=("slide",))
    o["A3"] = dict(title="A3: sliding door, lobby enlarged 0.15 m into the corridor", bed_x0=20.437-0.8, dy=0.15,
                   links=[box(19.477,-27.471,19.577,-26.691)], hang=None, hang_from_door=19.577, door=("slide",))
    # D: A3 plus the old head-wall door kept, clad flush in slats (jib door)
    o["D"] = dict(title="D: A3 plus the head-wall door kept, hidden behind the slats", bed_x0=20.437-0.8, dy=0.15,
                  links=[box(19.477,-27.471,19.577,-26.691), box(21.497,-26.691,22.297,-26.591)], hang=None, hang_from_door=19.577,
                  hang_end=21.347, conceal=True, door=("swing",(22.297,-26.641),(-1,0),(0,-1),0.8))
    # B: head wall, west end
    o["B"] = dict(title="B: door in the west end of the head wall", bed_x0=None, dy=0,
                  links=[box(19.577,-26.691,20.377,-26.591)], hang=(20.477, HANG_E), door=("swing",(19.577,-26.641),(1,0),(0,-1),0.8))
    # C: corridor end
    o["C"] = dict(title="C: door from the corridor's east end into the dressing room", bed_x0=20.437-0.8, dy=0,
                  links=[box(19.477,-28.30,19.577,-27.50)], hang=(19.627, HANG_E), door=("swing",(19.477,-28.30),(0,1),(-1,0),0.8))
    return o

def free_space(op, bed_x0, hang):
    bed = box(bed_x0, BED_Y0, bed_x0+BED_W, BED_Y0+BED_L)
    hang1 = box(hang[0], -27.291, hang[1], -26.691) if hang else Polygon()
    dy = op["dy"]
    floors = unary_union([BED_ROOM, LOBBY_LINK, lobby(dy), corridor(dy), main_door(dy), DRESS, *op["links"]])
    obst = unary_union([bed, hang1, HANG2, VANITY, PLANT])
    return floors.difference(obst), bed, hang1

def reachable(free, r, a, b):
    g = free.buffer(-r)
    if g.is_empty: return False
    parts = list(g.geoms) if hasattr(g, "geoms") else [g]
    # an endpoint need only lie in the free space within r of the eroded region (so a start inside a doorway counts)
    def comp(pt):
        c = min(parts, key=lambda q: q.distance(Point(pt)))
        return c if c.distance(Point(pt)) <= r + 1e-3 else None
    ca, cb = comp(a), comp(b)
    return ca is not None and ca is cb

def bottleneck(free, a, b):
    lo, hi = 0.0, 0.5
    if not reachable(free, 0.005, a, b): return 0.0
    for _ in range(14):
        m = (lo+hi)/2
        if reachable(free, m, a, b): lo = m
        else: hi = m
    return 2*lo

def shortest(free, a, b, r):
    g = free.buffer(-r)
    parts = list(g.geoms) if hasattr(g, "geoms") else [g]
    poly = min(parts, key=lambda q: q.distance(Point(a)) + q.distance(Point(b)))
    if poly.distance(Point(a)) > r + 1e-3 or poly.distance(Point(b)) > r + 1e-3: return None, None
    nodes = [a, b]
    for ring in [poly.exterior, *poly.interiors]:
        nodes += list(ring.coords)[:-1]
    pb = poly.buffer(2e-3).union(Point(a).buffer(r + 1e-3)).union(Point(b).buffer(r + 1e-3))
    def ok(p, q): return pb.contains(LineString([p, q]))
    dist = {0: 0.0}; prev = {}; pq = [(0.0, 0)]
    while pq:
        d, i = heapq.heappop(pq)
        if d > dist.get(i, 1e9): continue
        if i == 1: break
        for j in range(len(nodes)):
            if j == i: continue
            w = math.dist(nodes[i], nodes[j])
            if d + w < dist.get(j, 1e9) and ok(nodes[i], nodes[j]):
                dist[j] = d + w; prev[j] = i; heapq.heappush(pq, (d + w, j))
    if 1 not in dist: return None, None
    path, k = [1], 1
    while k != 0: k = prev[k]; path.append(k)
    return dist[1], [nodes[i] for i in path[::-1]]

def route(free, a, b):
    w = bottleneck(free, a, b)
    r = min(R_ROUTE, max(w/2*0.97, 0.01))
    L, path = shortest(free, a, b, r)
    return dict(length=None if L is None else round(L, 2), widest_m=round(w, 3), at_750=w >= 0.75, path=path)

def hang_start(op, bed_x0):
    """smallest hang-1 start (0.01 steps) for which a 750 route runs door -> dressing walkway; else None"""
    x = op["hang_from_door"]
    while x < 21.0:
        free, _, _ = free_space(op, bed_x0, (x, HANG_E))
        if bottleneck(free, ENTRY, DRESSPT) >= 0.75: return round(x, 2)
        x += 0.01
    return None

def analyse(key, op):
    out = dict(title=op["title"])
    bed_x0 = op["bed_x0"]
    hang = op["hang"]
    if key == "B":    # largest bed x such that nothing covers the door: search for the best symmetric-ish fit
        bed_x0 = op["links"][0].bounds[2] + 0.05        # bed starts 50 mm east of the door's far jamb
    if hang is None:
        xs = hang_start(op, bed_x0)
        hang = (xs if xs else 20.33, op.get("hang_end", HANG_E))
        if key == "A1": hang = (hang[0], hang[1])
    free, bed, hang1 = free_space(op, bed_x0, hang)
    obst = unary_union([bed, hang1, HANG2, VANITY, PLANT]); clips = []
    for l in op["links"]:
        b = l.bounds
        if (b[2]-b[0]) < (b[3]-b[1]):      # door in a N-S wall: strips 0.30 m deep either side
            ss = [box(b[0]-0.30, b[1], b[0], b[3]), box(b[2], b[1], b[2]+0.30, b[3])]
        else:
            ss = [box(b[0], b[1]-0.30, b[2], b[1]), box(b[0], b[3], b[2], b[3]+0.30)]
        clips += [round(sx_.intersection(obst).area*1e4, 1) for sx_ in ss]
    out["approach_strip_overlap_cm2"] = clips
    west = bed_x0 - 18.477; east = 22.397 - (bed_x0 + BED_W)
    out["bed_x0"] = round(bed_x0, 3); out["bed_centre_x"] = round(bed_x0 + 0.8, 3)
    out["west_side_m"] = round(west, 3); out["east_side_m"] = round(east, 3)
    out["east_with_tray_m"] = round(east - TRAY, 3); out["west_with_tray_m"] = round(west - TRAY, 3)
    out["foot_m"] = round(-23.791 - (BED_Y0 + BED_L), 3)
    out["hang1"] = [round(hang[0], 3), round(hang[1], 3)]; run = hang[1]-hang[0]
    out["hang1_run_m"] = round(run, 2); out["hang1_rail_m"] = round(run - DRESSING_RAIL_OFF, 2)
    out["bed_centred_on_wall_x20.962_east_gap_m"] = round(22.397 - (20.962 + 0.8), 3)
    pw = (bed_x0 - 0.40, -25.6); pe = (bed_x0 + BED_W + 0.40, -25.6)
    R = {}
    R["entry>bed (W side)"] = route(free, ENTRY, pw)
    R["entry>dressing"] = route(free, ENTRY, DRESSPT)
    R["entry>ensuite"] = route(free, ENTRY, ENSUITE)
    R["bedW>ensuite"] = route(free, pw, ENSUITE)
    R["bedE>ensuite"] = route(free, pe, ENSUITE) if east >= 0.75 else dict(length=None, widest_m=round(east, 3), at_750=False, path=None)
    out["routes"] = R
    out["lobby_depth_m"] = round(0.68 + op["dy"], 2)
    out["_geom"] = (free, bed, hang1, bed_x0)
    return out

DRESSING_RAIL_OFF = DRAWERS_HAT

# ---------------------------------------------------------------- drawing (1:50: 1 mm on paper = 50 mm real)
X0, X1, Y0, Y1 = 18.10, 22.80, -29.00, -23.55
S = 1000.0
def sx(x): return (x - X0) * S
def sy(y): return (Y1 - y) * S
def poly_svg(g, **kw):
    attrs = " ".join(f'{k.replace("_","-")}="{v}"' for k, v in kw.items())
    geoms = g.geoms if hasattr(g, "geoms") else [g]
    d = ""
    for p in geoms:
        if p.is_empty: continue
        for ring in [p.exterior, *p.interiors]:
            d += "M" + " L".join(f"{sx(x):.0f},{sy(y):.0f}" for x, y in ring.coords) + "Z "
    return f'<path d="{d}" fill-rule="evenodd" {attrs}/>'
def txt(x, y, s, size=70, fill="#000", anchor="start", weight="normal"):
    return f'<text x="{sx(x):.0f}" y="{sy(y):.0f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-family="Arial" font-weight="{weight}">{s}</text>'

def draw(key, op, a):
    free, bed, hang1, bed_x0 = a["_geom"]
    dy = op["dy"]
    floors = unary_union([BED_ROOM, LOBBY_LINK, lobby(dy), corridor(dy), main_door(dy), DRESS, *op["links"]])
    W, H = (X1 - X0) * S, (Y1 - Y0) * -S * -1
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W/50:.1f}mm" height="{H/50+34:.1f}mm" viewBox="0 0 {W:.0f} {H+1700:.0f}">',
         f'<rect width="{W:.0f}" height="{H+1700:.0f}" fill="#fff"/>',
         f'<rect x="0" y="0" width="{W:.0f}" height="{H:.0f}" fill="#9a9a9a"/>',
         poly_svg(floors, fill="#fbf7ef", stroke="none")]
    # slat feature on the head wall (solid) or its remaining length
    hw_x0, hw_x1 = 19.527, 22.397
    segs = [(hw_x0, hw_x1)]
    for l in op["links"]:
        b = l.bounds
        if not op.get("conceal") and abs(b[1]+26.691) < 0.01 and abs(b[3]+26.591) < 0.01:
            segs = [(hw_x0, b[0]-0.0), (b[2], hw_x1)]
            segs = [(p, q) for p, q in segs if q-p > 0.01]
    for p, q in segs:
        s.append(f'<rect x="{sx(p):.0f}" y="{sy(-26.591)-4:.0f}" width="{(q-p)*S:.0f}" height="60" fill="#8b5a2b"/>')
        for i in range(int((q-p)/0.06)):
            s.append(f'<line x1="{sx(p+0.03+i*0.06):.0f}" y1="{sy(-26.591):.0f}" x2="{sx(p+0.03+i*0.06):.0f}" y2="{sy(-26.591)+60:.0f}" stroke="#f3d9a8" stroke-width="8"/>')
    s.append(txt(20.96, -26.50, "slat wall" if len(segs) == 1 else "slat wall (broken by the door)", 55, "#fff", "middle"))
    # furniture
    s.append(poly_svg(bed, fill="#d8e4ee", stroke="#345", stroke_width=6))
    cx = bed_x0 + 0.8
    s.append(txt(cx, -25.4, f"bed 1.60 x 2.00", 70, "#234", "middle"))
    for xs_, sign in ((bed_x0, -1), (bed_x0 + BED_W, 1)):   # trays 250 mm
        t = box(min(xs_, xs_ + sign*TRAY), -25.9, max(xs_, xs_ + sign*TRAY), -25.0)
        s.append(poly_svg(t, fill="none", stroke="#c33", stroke_width=5, stroke_dasharray="25 15"))
    s.append(poly_svg(VANITY, fill="#e6dccb", stroke="#543", stroke_width=5)); s.append(poly_svg(PLANT, fill="#cfe5c4", stroke="#363", stroke_width=5))
    h2 = HANG2
    s.append(poly_svg(h2, fill="#e5d3b3", stroke="#543", stroke_width=5)); s.append(txt(20.53, -28.55, "his hanging", 60, "#432", "middle"))
    if not hang1.is_empty:
        s.append(poly_svg(hang1, fill="#e5d3b3", stroke="#543", stroke_width=5))
        s.append(txt((hang1.bounds[0]+hang1.bounds[2])/2, -27.03, f"hers hanging {a['hang1_run_m']:.2f} m", 60, "#432", "middle"))
    # door symbols
    d = op["door"]
    if d[0] == "swing":
        hx, hy = d[1]; cdir = d[2]; odir = d[3]; w = d[4]
        ex, ey = hx + cdir[0]*w, hy + cdir[1]*w
        ox, oy = hx + odir[0]*w, hy + odir[1]*w
        s.append(f'<line x1="{sx(hx):.0f}" y1="{sy(hy):.0f}" x2="{sx(ox):.0f}" y2="{sy(oy):.0f}" stroke="#036" stroke-width="12"/>')
        sweep = 1 if (cdir[0]*odir[1]-cdir[1]*odir[0]) < 0 else 0
        s.append(f'<path d="M{sx(ex):.0f},{sy(ey):.0f} A{w*S:.0f},{w*S:.0f} 0 0 {sweep} {sx(ox):.0f},{sy(oy):.0f}" fill="none" stroke="#036" stroke-width="5" stroke-dasharray="20 14"/>')
    if key in ("A1", "A2", "A3", "D"):
        b = op["links"][0].bounds
        s.append(f'<rect x="{sx(19.577):.0f}" y="{sy(b[3]):.0f}" width="40" height="{(b[3]-b[1])*S:.0f}" fill="none" stroke="#036" stroke-width="8" stroke-dasharray="30 12"/>')
        s.append(txt(19.60, b[1]-0.12, "sliding leaf", 50, "#036"))
    # routes
    colours = {"entry>bed (W side)": "#d62", "entry>dressing": "#07a", "bedW>ensuite": "#a0a", "bedE>ensuite": "#090"}
    for name, c in colours.items():
        r = a["routes"][name]
        if r["path"]:
            pts = " ".join(f"{sx(x):.0f},{sy(y):.0f}" for x, y in r["path"])
            s.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="14" stroke-opacity=".85" stroke-linejoin="round"/>')
    for x, y, t in ((18.9, -28.0, "corridor"), (18.98, -26.95, "lobby"), (20.9, -24.0, "bedroom"), (21.0, -27.76, "dressing walkway"),
                    (21.65, -28.74, "ensuite door"), (18.977, -27.37 - dy, "main door 0.90")):
        s.append(txt(x, y, t, 55, "#556", "middle"))
    s.append(f'<line x1="{sx(18.2):.0f}" y1="{sy(-23.75):.0f}" x2="{sx(19.2):.0f}" y2="{sy(-23.75):.0f}" stroke="#000" stroke-width="14"/>' + txt(18.7, -23.68, "1 m", 55, "#000", "middle"))
    # captions
    s.append(f'<text x="30" y="{H+90:.0f}" font-size="85" font-weight="bold" font-family="Arial">{op["title"]}</text>')
    rr = a["routes"]
    def f(n):
        r = rr[n]; L = "no route" if r["length"] is None else f'{r["length"]:.1f} m'
        return f'{L} (widest {r["widest_m"]*1000:.0f})'
    lines = [f'bed x {a["bed_x0"]:.3f}..{a["bed_x0"]+1.6:.3f}  sides W {a["west_side_m"]*1000:.0f} / E {a["east_side_m"]*1000:.0f} mm; with 250 trays W {a["west_with_tray_m"]*1000:.0f} / E {a["east_with_tray_m"]*1000:.0f}; foot {a["foot_m"]*1000:.0f} (750 needed)',
             f'hers hanging run {a["hang1_run_m"]:.2f} m (today 1.72), rail {a["hang1_rail_m"]:.2f} (today 1.10)',
             f'orange entry>bed {f("entry>bed (W side)")}', f'blue entry>dressing {f("entry>dressing")}',
             f'purple W bedside>ensuite {f("bedW>ensuite")}', f'green E bedside>ensuite {f("bedE>ensuite")}',
             "scale 1:50 at print size; metres in the design model frame; routes are centrelines, widest = clear width of the narrowest point (mm)"]
    for i, l in enumerate(lines):
        s.append(f'<text x="30" y="{H+190+i*105:.0f}" font-size="62" font-family="Arial" fill="#222">{l}</text>')
    s.append("</svg>")
    return "\n".join(s)

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    ops = options(); res = {}
    for k, op in ops.items():
        a = analyse(k, op)
        (OUT / f"plan-{k}.svg").write_text(draw(k, op, a))
        a.pop("_geom")
        for r in a["routes"].values(): r.pop("path")
        res[k] = a
    (OUT / "results.json").write_text(json.dumps(res, indent=1))
    # self-checks: the router reproduces the known 0.80 m foot passage of today, and stays quiet/loud where it should
    assert abs(res["O"]["routes"]["entry>dressing"]["widest_m"] - 0.80) < 0.01        # = foot gap, cf. docs/lanes/DF.md
    assert not res["A2"]["routes"]["entry>dressing"]["at_750"] and res["A3"]["routes"]["entry>dressing"]["at_750"]
    assert res["B"]["east_side_m"] < 0.75 and res["A3"]["east_with_tray_m"] >= 0.75
    for k, a in res.items():
        print(k, a["title"]); print("  bed", a["bed_x0"], "W", a["west_side_m"], "E", a["east_side_m"], "trayE", a["east_with_tray_m"], "hang", a["hang1"], a["hang1_run_m"], a["hang1_rail_m"])
        for n, r in a["routes"].items(): print("   ", n, r["length"], r["widest_m"], r["at_750"])
