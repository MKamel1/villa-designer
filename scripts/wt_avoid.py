"""Add planner obstacle boxes for elements that the villa admission found inside the walked envelope (scripts/wt_admit.py), inflated by a margin.
Appends to knowledge/flythrough/evaluated-obstacles.json (the planner blocks these boxes like furniture) and records why.
usage: python scripts/wt_avoid.py MARGIN_M ELEMENT_ID..."""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
f = ROOT/'knowledge/flythrough/evaluated-obstacles.json'; d = json.loads(f.read_text())
margin = float(sys.argv[1]); want = set(sys.argv[2:]); scene = json.loads((ROOT/'out/wt/scene-base.json').read_text())
for m in scene['meshes']:
    if m['id'] in want or want & set(m.get('element_ids') or []):
        pts = np.array([v for face in m['faces'] for v in face]); lo, hi = pts.min(0)-[margin, margin, 0], pts.max(0)+[margin, margin, 0]
        d['boxes'] = [b for b in d['boxes'] if b['id'] != 'avoid-'+m['id']]+[dict(id='avoid-'+m['id'], lo=[round(float(v), 3) for v in lo], hi=[round(float(v), 3) for v in hi])]
        print('avoid', m['id'], lo.round(2), hi.round(2))
d['avoid_basis'] = 'avoid-* boxes: elements the villa admission found inside the swept walking envelope of a tour route (scripts/wt_admit.py); inflated by the margin so the planner keeps clear of them'
f.write_text(json.dumps(d, indent=1))
