"""Glass width seen from each garden-pan standing point -> knowledge/flythrough/tour-pans.json (the pan sweeps this width once, not +-30 deg and back).
The glass is the contiguous run (gaps <= 1.0 m) of glazing triangles in the wall plane through the garden door, found in the audit geometry cache.
usage: python scripts/wt_pans.py"""
import json, math, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src'), str(ROOT/'scripts')]
import numpy as np
from wt_plan import vmap
from archpipe import walkthrough_tour as WT

def main():
    layout, spec, vm = vmap(); pol = WT.tour_policy(); route = WT.tour_route()
    z = np.load(sorted((ROOT/'out/flyaudit').glob('villa4-*.npz'))[-1]); tr, cls = z['tris'], z['cls']
    g = tr[cls == 1]; c = g.mean(1); out = {}
    for st in route['stations']:
        if not st.get('garden'): continue
        p, face = WT._inward(vm, st['door'], pol['garden_inward_offsets_m']); f = math.radians(face); fx, fy = math.cos(f), math.sin(f)
        d = st['door']; depth_door = (d[0]-p[0])*fx+(d[1]-p[1])*fy
        dep = (c[:, 0]-p[0])*fx+(c[:, 1]-p[1])*fy; lat = -(c[:, 0]-p[0])*fy+(c[:, 1]-p[1])*fx
        ok = (np.abs(dep-depth_door) < .6) & (c[:, 2] > -3) & (c[:, 2] < -.3) & (np.abs(lat) < 8)
        T = g[ok]; lt = -(T[:, :, 0]-p[0])*fy+(T[:, :, 1]-p[1])*fx; iv = sorted(zip(lt.min(1).tolist(), lt.max(1).tolist()))
        runs = []; a, b = iv[0]
        for lo_, hi_ in iv[1:]:
            if lo_-b <= .6: b = max(b, hi_)
            else: runs.append((a, b)); a, b = lo_, hi_
        runs.append((a, b)); r = next((r for r in runs if r[0]-.3 <= 0 <= r[1]+.3), max(runs, key=lambda r: r[1]-r[0]))
        a0, a1 = (math.degrees(math.atan2(r[0], depth_door)), math.degrees(math.atan2(r[1], depth_door)))
        out[st['garden']] = dict(point=[round(v, 3) for v in p], face_deg=face, glass_lateral_m=[round(float(r[0]), 2), round(float(r[1]), 2)], glass_width_m=round(float(r[1]-r[0]), 2),
                                 distance_m=round(float(depth_door), 2), glass_angle_deg=[round(float(a0), 1), round(float(a1), 1)])
        print(st['garden'], out[st['garden']])
    (ROOT/'knowledge/flythrough/tour-pans.json').write_text(json.dumps(dict(schema='flythrough-tour-pans/1', method=__doc__.split('\n')[0], gardens=out), indent=1))
main()
