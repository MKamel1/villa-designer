"""Plan-only dry run of the tour (no scene build): uses the dumped obstacle boxes."""
import json, os, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
import numpy as np
from archpipe.concept import villa_r11 as R, revit_spec as RS
from archpipe import flythrough as FT, walkthrough_tour as WT

def vmap(boxes=None):
    boxes = boxes or os.environ.get('BOXES', 'out/wt/villa4/boxes.json')
    layout = R.design('D1'); spec = RS.build(layout)
    vm = FT.VillaMap(layout, spec)
    b = json.loads((ROOT/boxes).read_text())
    vm.boxes = {lv: [(np.array(lo), np.array(hi), e) for lo, hi, e in b[lv]] for lv in FT.LEVEL_Z}
    return layout, spec, vm

if __name__ == '__main__':
    t = time.time(); layout, spec, vm = vmap(); path = WT.plan_tour(vm)
    out = ROOT/'out/wt/villa4/plan-only.json'; out.write_text(json.dumps(path))
    bad = FT.plan_findings(path, vm); print('plan_findings (standing policy, wall crossing):', len(bad), sorted(bad)[:3])
    print('frames', len(path['frames']), 'dur', path['duration_s'], 'dist', path['distance_m'], 'sec', time.time()-t)
    for s in path['stations']:
        print(s['room'] or s['garden'], s['kind'], [round(v, 2) for v in s['point']], s['first_frame'], round(s['seconds'], 1), 'wall', s['wall_min_m'] and round(s['wall_min_m'], 2), 'FLAG' if s['flagged_under_1m'] else '', s['best_view'])
    print('dir', WT.direction_findings(path['frames'])[:5]); print('stair', WT.stair_findings(path['frames']))
    print('cov', WT.coverage_findings(path['frames'], [s['room'] for s in path['stations'] if s['room']]))
    import collections
    bad = WT.direction_findings(path['frames'])
    print(len(bad), collections.Counter((path['frames'][i]['phase'], path['frames'][i]['room']) for i, _ in bad).most_common(8))
    print(bad[::max(1, len(bad)//12)])
