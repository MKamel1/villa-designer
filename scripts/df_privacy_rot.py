"""Lane DF: rotated-bed sketches R1 (head east), R2 (head west), R3 (head north). PROPOSAL ONLY, no model change.
Dressing door = option 4's (west end of south wall, x 19.577..20.377, leaf swings into dressing). Same sightline engine, all doors open.
Run: python scripts/df_privacy_rot.py -> docs/lanes/DF-privacy-options/plan-R{1,2,3}.{svg,png}, results-rot.json"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import df_privacy_options as O
from df_privacy_options import *

BED_X = lambda x0, y0, w, l: box(x0, y0, x0 + w, y0 + l)
# (bed box, vanity box, sleeper points [(label, pt)], head-wall text, trays: side gaps)
CY = -25.191                                      # room y centre
def cfgs():
    c = {}
    c["R1"] = dict(title="R1 BED HEAD ON THE EAST WALL; dressing door at the west end of the south wall; vanity moves to the north window",
        bed=box(20.397, CY-0.8, 22.397, CY+0.8), vanity=box(18.9, -24.191, 19.9, -23.791),
        pts=[("S", (21.4, -26.29)), ("N", (21.4, -24.09))], gaps=("south", 0.600, "north", 0.600),
        under="YES: headboard under the east window (sill 0.9 m, window y -26.44..-24.40 over the whole headboard)",
        slat="NO: the head wall is the east window wall; the slats would have to stop at the 0.9 sill (no whole wall)")
    c["R2"] = dict(title="R2 BED HEAD ON THE WEST WALL; dressing door at the west end of the south wall; vanity stays at the east window",
        bed=box(18.477, CY-0.8, 20.477, CY+0.8), vanity=S.VANITY,
        pts=[("S", (19.5, -26.29)), ("N", (19.5, -24.09))], gaps=("south", 0.600, "north", 0.600),
        under="NO: solid west wall (no window)",
        slat="YES: the west wall is solid and free (2.69 m long, notch only above y -23.95); slats fit behind a 2.0 m head")
    c["R3"] = dict(title="R3 BED HEAD ON THE NORTH WALL (under the window); dressing door at the west end of the south wall; vanity stays east",
        bed=box(19.637, -25.791, 21.237, -23.791), vanity=S.VANITY,
        pts=[("W", (19.14, -24.8)), ("E", (21.617, -25.45))], gaps=("west", 1.160, "east", 1.160),
        under="YES: headboard under the 2.40 m north window (sill 0.9 m); bed 1.6 m sits inside it",
        slat="NO: the north wall is the window; slats would have to stop at the 0.9 sill")
    return c

def build(key, c):
    base = O.opt_defs()["4"]
    solid = modelled(base); V = vps(base["cx"]); cnt = check(solid, V, targets())
    S.VANITY = c["vanity"]
    h1 = box(20.477, -27.291, 22.347, -26.691)
    obst = unary_union([c["bed"], h1, S.HANG2, S.VANITY, S.PLANT])
    free = FRAME.difference(solid).difference(obst)
    R = S.route(free, P0, S.DRESSPT)
    night = {}
    for lab, p in c["pts"]:
        r = S.route(free, p, S.ENSUITE); night[lab] = (r["length"], round(r["widest_m"]*1000))
    foot_south = round(c["bed"].bounds[1] - (-26.591), 3) if key == "R3" else None
    op = dict(base); op.update(title=c["title"], bed_x0=c["bed"].bounds[0], stor=[],
        note=f'Bedsides {c["gaps"][0]} {c["gaps"][1]*1000:.0f} / {c["gaps"][2]} {c["gaps"][3]*1000:.0f} mm (750 needed). Headboard under a window: {c["under"][:3]}. Slat wall: {c["slat"][:3]}.',
        extra=["nights: " + "; ".join(f"{k} bedside to ensuite {v[0]} m, narrowest {v[1]} mm" for k, v in night.items()), "hanging hers 1.87 m (+0.15 vs today 1.72); trays out 250 leave " + f'{(c["gaps"][1]-0.25)*1000:.0f} / {(c["gaps"][3]-0.25)*1000:.0f} mm'])
    ok, far = draw(key, op, solid, R, cnt, V, c["bed"], h1)
    return dict(seeing=len(cnt), viewpoints=len(V), lobby_to_dressing_m=R["length"], lobby_narrowest_mm=round(R["widest_m"]*1000),
                night=night, gaps=c["gaps"], foot_to_south_wall=foot_south, under_window=c["under"], slat=c["slat"])

if __name__ == "__main__":
    res = {k: build(k, c) for k, c in cfgs().items()}
    (OUT / "results-rot.json").write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))
