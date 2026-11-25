"""Dump the walking-obstacle boxes of a scene (planning iterations need only these).

usage: python scripts/wt_boxes.py [scene.json out.json]   (no arguments: build the production scene, write out/wt/villa4/boxes.json)"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
from archpipe import flythrough as FT
if len(sys.argv) == 3:
    scene = json.loads(Path(sys.argv[1]).read_text()); out = Path(sys.argv[2])
else:
    from archpipe.concept import villa_render as V
    scene = V.build(views=[]); out = ROOT/'out/wt/villa4/boxes.json'
boxes = FT._furniture_boxes(scene)
out.write_text(json.dumps({lv: [[list(map(float, lo)), list(map(float, hi)), e] for lo, hi, e in b] for lv, b in boxes.items()}))
print('boxes', {k: len(v) for k, v in boxes.items()})
