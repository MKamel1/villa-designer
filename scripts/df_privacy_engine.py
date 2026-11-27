"""Lane DF privacy options: 2D sightline engine (all suite doors OPEN, furniture ignored = worst case).
PROPOSAL ONLY. Walls/doors from src/archpipe/model/data/d1-elements.json (via df_suite_sightlines); options add/remove rectangles."""
import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import df_suite_sightlines as SL
from shapely.geometry import box, LineString, Point, Polygon
from shapely.ops import unary_union

CY0, CY1 = -28.471, -27.421
DRESS_Z = unary_union([box(19.577, -28.471, 22.397, -26.691), box(19.804, -28.831, 22.124, -28.471)])
ENS_Z = box(19.804, -31.111, 22.124, -28.931)
ENS_DOOR_Z = box(21.25, -29.6, 22.05, -28.831)          # ensuite doorway + zone just outside it (dressing-ext side)
PROT = unary_union([DRESS_Z, ENS_Z])

def targets(step=0.2, extra=()):
    pts = []
    for poly in (DRESS_Z, ENS_Z):
        x0, y0, x1, y1 = poly.bounds
        x = x0 + step/2
        while x < x1:
            y = y0 + step/2
            while y < y1:
                if poly.contains(Point(x, y)): pts.append((round(x, 3), round(y, 3)))
                y += step
            x += step
    return pts + list(extra)

def vps(corr_x1, step=0.25):
    """public viewpoints: corridor x 8.9..corr_x1 (full width), stair landing, kids doorways, gallery"""
    out = []
    x = 8.9
    while x <= corr_x1:
        y = CY0 + 0.05
        while y < CY1: out.append((round(x, 3), round(y, 3), "corridor")); y += 0.1
        x += step
    for x in (3.9, 4.4, 4.9): 
        for y in (-28.3, -27.6, -26.9): out.append((x, y, "stair landing"))
    for n, p in SL.THRESH.items(): out.append((*p, n))
    for x in (6.0, 7.5, 8.5):
        for y in (-27.9, -27.0): out.append((x, y, "stair void"))
    # inside kids-b doorway apron (just inside the room)
    out += [(16.689, -27.2, "kids-b doorway (inside)"), (16.689, -27.3, "kids-b doorway (inside)")]
    return out

def solid_for(mods_add=(), mods_cut=()):
    s = SL.walls_and_doors(shut=())                    # all existing doors open
    s = unary_union([s, *mods_add])
    return s.difference(unary_union(list(mods_cut))) if mods_cut else s

def sees(solid, a, b): return solid.intersection(LineString([a, b])).length < 1e-6

def check(solid, V, T):
    """returns (n_pairs, worst viewpoint (max targets seen), per-viewpoint counts, example far viewpoint)"""
    cnt = {}
    for v in V:
        n = [t for t in T if sees(solid, v[:2], t)]
        if n: cnt[v] = n
    return cnt

def fan(solid, v, R=14.0, n=720):
    """visibility polygon from v: ray cast"""
    pts = []
    for i in range(n):
        a = 2*math.pi*i/n; d = (math.cos(a), math.sin(a))
        ray = LineString([v, (v[0]+R*d[0], v[1]+R*d[1])])
        inter = solid.intersection(ray)
        if inter.is_empty: pts.append(ray.coords[1]); continue
        best = min(Point(v).distance(g) for g in (inter.geoms if hasattr(inter, "geoms") else [inter]))
        pts.append((v[0]+best*d[0], v[1]+best*d[1]))
    return Polygon(pts).buffer(0)
