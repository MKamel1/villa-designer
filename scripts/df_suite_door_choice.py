"""Lane DF build: choose the suite door's width and hinge for privacy WITH THE DOOR OPEN (built model, 2D, furniture ignored).
For each candidate (leaf width x hinge jamb, leaf swung 90 deg INTO the vestibule) count the vestibule, lobby and bedroom floor points
(0.1 m grid) that any point of the PUBLIC corridor (x < the suite wall) can see, plus the viewpoints that see the protected suite zones.
Run: PYTHONPATH=src python scripts/df_suite_door_choice.py [elements.json]   -> prints a table; numbers copied to docs/lanes/DF-built.md"""
import dataclasses, json, sys
from pathlib import Path
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union
from shapely.prepared import prep
from archpipe.model import api, suite_privacy as SP

ROOT = Path(__file__).resolve().parents[1]
els = api.load_json(sys.argv[1]) if len(sys.argv) > 1 else api.load("D1")
DOOR = "door-GF-corridor-suite-vestibule"
d0 = next(e for e in els if e.id == DOOR)
walls = unary_union([SP._wall_box(e) for e in SP._els(els, "wall")])
other = unary_union([SP.door_opening(e) for e in SP._els(els, "door") if e.id != DOOR])
xs, ys = d0.placement[0] / 1000, d0.placement[1] / 1000
vp = [(x, y) for x, y, lab in SP.viewpoints(els) if lab in ("corridor", "kids-b doorway")]
regions = {"vestibule": SP._clear(els, "suite-vestibule"), "lobby": SP._clear(els, "parents-entry"), "bedroom": SP._clear(els, "parents-bed")}
pts = {k: SP._grid(v, 0.1) for k, v in regions.items()}
Tz = SP.targets(els)
rows = []
for w in (0.80, 0.90, 1.00):
    for hinge in ("north", "south", "none"):
        op = box(xs - 0.06, ys - (w + 0.1) / 2, xs + 0.06, ys + (w + 0.1) / 2)
        blocker = unary_union([walls.difference(unary_union([other, op]))])
        if hinge != "none":
            hy = ys + (w / 2 if hinge == "north" else -w / 2)
            blocker = unary_union([blocker, LineString([(xs, hy), (xs + w, hy)]).buffer(0.02, cap_style="flat")])
        pb = prep(blocker)
        seen = {}
        for k, P in pts.items():
            n = 0
            for t in P:
                if any((not pb.intersects(LineString([v, t]))) or SP.sees(blocker, v, t) for v in vp):
                    n += 1
            seen[k] = (n, len(P))
        prot = sum(1 for v in vp if any((not pb.intersects(LineString([v, t]))) or SP.sees(blocker, v, t) for t in Tz[::3]))
        rows.append((w, hinge, seen, prot))
        print(f"leaf {w:.2f} hinge {hinge:5s}: " + "  ".join(f"{k} {n}/{m}" for k, (n, m) in seen.items()) + f"  | viewpoints seeing protected zones {prot}")
