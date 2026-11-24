"""Build the production scene once and dump the walking-obstacle boxes (planning iterations need only these)."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
from archpipe.concept import villa_render as V
from archpipe import flythrough as FT
scene = V.build(views=[])
boxes = FT._furniture_boxes(scene)
out = ROOT/'out/wt/villa4/boxes.json'
out.write_text(json.dumps({lv: [[list(map(float, lo)), list(map(float, hi)), e] for lo, hi, e in b] for lv, b in boxes.items()}))
print('boxes', {k: len(v) for k, v in boxes.items()})
