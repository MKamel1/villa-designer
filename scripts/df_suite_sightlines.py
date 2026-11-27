"""Lane DF round 2, step 1: privacy diagnosis by 2D sightline raster on the design-model walls (plan view, eye level,
furniture ignored = worst case). PROPOSAL ONLY, reads src/archpipe/model/data/d1-elements.json, changes nothing.
Run: python scripts/df_suite_sightlines.py   -> docs/lanes/DF-suite-vestibule-study/sightlines.json"""
import json
from pathlib import Path
from shapely.geometry import box, LineString, Point
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/lanes/DF-suite-vestibule-study"
EL = json.load(open(ROOT / "src/archpipe/model/data/d1-elements.json"))["elements"]
M = 1000.0

def walls_and_doors(extra_walls=(), extra_open=(), shut=()):
    """returns the sight-blocking solid for a given door state. `shut` = ids of doors that are closed (leaf blocks)."""
    solids, cuts = [], []
    for e in EL:
        if e["level"] != "GF": continue
        x, y = e["placement"][:2]; L, t = e["size"][:2]
        if e["kind"] == "wall":
            if "ext-33" in e["id"] or "ext-34" in e["id"] or "ext-19" in e["id"]: pass
            solids.append(box((x-L/2)/M, (y-t/2)/M, (x+L/2)/M, (y+t/2)/M) if e["rotation_deg"] in (0, -0.0) else
                          box((x-t/2)/M, (y-L/2)/M, (x+t/2)/M, (y+L/2)/M))
        elif e["kind"] == "door" and e["id"] not in shut:
            W = e["params"]["width_mm"] if e["params"]["operation"] == "pocket" else e["params"].get("structural_opening_mm", L)
            cuts.append(box((x-W/2)/M, (y-t/2)/M-0.001, (x+W/2)/M, (y+t/2)/M+0.001))
    solids += list(extra_walls)
    return unary_union(solids).difference(unary_union(cuts + list(extra_open)))

def grid(rect, step=0.2):
    x0, y0, x1, y1 = rect; pts = []
    x = x0 + step/2
    while x < x1:
        y = y0 + step/2
        while y < y1: pts.append((round(x, 3), round(y, 3))); y += step
        x += step
    return pts

def visible(solid, a, b):
    return solid.intersection(LineString([a, b])).length < 1e-6   # a ray may graze a corner (a point) but not cross a wall

# clear rooms (m) from d1-elements 'clear_rect_mm' / polygons
DRESS = [r for r in grid((19.577, -28.471, 22.397, -26.691)) ]
DRESS_EXT = grid((19.804, -28.831, 22.124, -28.671))
ENSUITE = grid((19.804, -31.111, 22.124, -28.931))
TARGETS = {"dressing floor": DRESS, "dressing-ext (vanity strip)": DRESS_EXT, "ensuite floor": ENSUITE}
DOOR_PTS = {"dressing head-wall doorway": [(21.497+0.1*i, -26.64) for i in range(0, 8)],
            "ensuite doorway (dressing-ext wall)": [(21.25+0.1*i, -28.881) for i in range(0, 8)]}

VIEW = {   # public viewpoints (clear rectangles, m)
    "corridor (whole length, x 8.89-19.48)": grid((8.887, -28.471, 19.477, -27.421)),
    "stair landing GF": grid((3.817, -28.471, 5.177, -26.371)),
    "stair void / gallery": grid((5.177, -28.471, 8.887, -26.371)),
    "gallery end (family-bath door)": grid((8.887, -27.371, 11.427, -26.421)),
}
THRESH = {"kids-a doorway": (13.215, -27.371), "kids-b doorway": (16.689, -27.371),
          "family-bath doorway": (10.352, -26.371), "stair-landing core door": (4.602, -28.671)}

STATES = {
    "S0 all doors shut": dict(shut=("door-GF-corridor-parents-entry", "door-GF-parents-bed-parents-dressing", "door-GF-parents-dressing-ext-parents-ensuite")),
    "S1 entry door open, others shut": dict(shut=("door-GF-parents-bed-parents-dressing", "door-GF-parents-dressing-ext-parents-ensuite")),
    "S2 entry + dressing doors open, ensuite shut": dict(shut=("door-GF-parents-dressing-ext-parents-ensuite",)),
    "S3 all doors open": dict(shut=()),
}
# the other doors (kids, family bath, landing) are open for every state: worst case for privacy

def run():
    out = {}
    for sname, st in STATES.items():
        solid = walls_and_doors(shut=st["shut"])
        res = {"viewpoints": {}, "thresholds": {}}
        for vname, vps in VIEW.items():
            for tname, tps in {**TARGETS, **{k: v for k, v in DOOR_PTS.items()}}.items():
                n = 0; best = None; first = None
                for v in vps:
                    if any(visible(solid, v, t) for t in tps):
                        n += 1
                        if first is None: first = v
                res["viewpoints"].setdefault(vname, {})[tname] = dict(seeing=n, of=len(vps), pct=round(100*n/len(vps), 1), example_from=first)
        for hname, h in THRESH.items():
            for tname, tps in {**TARGETS, **DOOR_PTS}.items():
                seen = [t for t in tps if visible(solid, h, t)]
                res["thresholds"].setdefault(hname, {})[tname] = dict(seen=len(seen), of=len(tps), example_to=seen[0] if seen else None)
        # what the open entry door DOES show: bedroom floor points seen from the corridor
        bed = grid((18.477, -26.591, 22.397, -23.791), 0.2)
        cor = VIEW["corridor (whole length, x 8.89-19.48)"]
        seen = {b for b in bed for v in cor if visible(solid, v, b)}
        res["bedroom_floor_seen_from_corridor_pct"] = round(100*len(seen)/len(bed), 1)
        xs = [b[0] for b in seen]; ys = [b[1] for b in seen]
        res["bedroom_seen_extent"] = [min(xs), max(xs), min(ys), max(ys)] if seen else None
        out[sname] = res
    return out

def exposure():
    """what the OPEN entry door exposes today: named bedroom targets seen from public viewpoints (pocket open, others shut)."""
    solid = walls_and_doors(shut=("door-GF-parents-bed-parents-dressing", "door-GF-parents-dressing-ext-parents-ensuite"))
    T = {"lobby floor": grid((18.477, -27.321, 19.477, -26.641)), "bedroom floor (whole)": grid((18.477, -26.591, 22.397, -23.791)),
         "bed footprint (x 19.53-21.13, y -26.59..-24.59)": grid((19.53, -26.591, 21.13, -24.591)),
         "head-wall dressing door, bedroom face": [(21.497+0.1*i, -26.58) for i in range(0, 8)],
         "head-wall dressing door at 3 m or less": []}
    out = {}
    for vname, vps in {**VIEW, **{k: [v] for k, v in THRESH.items()}}.items():
        for tname, tps in T.items():
            if not tps: continue
            hit = [v for v in vps if any(visible(solid, v, t) for t in tps)]
            out.setdefault(vname, {})[tname] = dict(viewpoints_seeing=len(hit), of=len(vps),
                                                    x_range=[min(h[0] for h in hit), max(h[0] for h in hit)] if hit else None)
    # negative control: pocket door shut -> must see nothing
    shut = walls_and_doors(shut=("door-GF-corridor-parents-entry", "door-GF-parents-bed-parents-dressing", "door-GF-parents-dressing-ext-parents-ensuite"))
    assert not any(visible(shut, v, t) for v in VIEW["corridor (whole length, x 8.89-19.48)"] for t in T["bedroom floor (whole)"])
    # positive control: from inside the bedroom the open dressing door DOES show the dressing floor
    op = walls_and_doors(shut=("door-GF-parents-dressing-ext-parents-ensuite",))
    assert any(visible(op, (21.9, -25.5), t) for t in TARGETS["dressing floor"])
    return out

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    r = run(); r["exposure_entry_open"] = exposure(); (OUT / "sightlines.json").write_text(json.dumps(r, indent=1))
    print(json.dumps(r["exposure_entry_open"], indent=1)); raise SystemExit
    for s, res in r.items():
        print("==", s, "bedroom floor seen from corridor %", res["bedroom_floor_seen_from_corridor_pct"], res["bedroom_seen_extent"])
        for v, d in res["viewpoints"].items():
            print("  ", v, {k: f'{x["pct"]}%' for k, x in d.items()})
        for h, d in res["thresholds"].items():
            print("  ", h, {k: x["seen"] for k, x in d.items()})
