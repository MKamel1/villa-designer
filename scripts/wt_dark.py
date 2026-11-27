"""Guard: runs of near-black frames in a rendered lookdev set (lane WT; revision 8: the parents' dressing walk and a family-room arc rendered black).
A frame is dark when the mean display value of its 1/8-size image is below DARK (0-255); a run of >= MIN_S seconds of route time is reported.
usage: python scripts/wt_dark.py <out dir> [--stage lookdev] [--step 2]   exit 1 when any run is found"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
DARK, MIN_S, FPS = 12.0, 1.0, 24
def luma(p): return float(np.asarray(Image.open(p).convert('L').reduce(8), dtype=np.float32).mean())
def runs(vals, step, dark=DARK, min_s=MIN_S):
    """vals: {frame index: mean luma}; returns [(first, last, seconds)] of consecutive rendered frames below `dark` lasting >= min_s."""
    out, cur = [], []
    for i in sorted(vals):
        if vals[i] < dark and (not cur or i-cur[-1] == step): cur.append(i)
        else:
            if cur: out.append(cur)
            cur = [i] if vals[i] < dark else []
    if cur: out.append(cur)
    return [(c[0], c[-1], (c[-1]-c[0]+step)/FPS) for c in out if (c[-1]-c[0]+step)/FPS >= min_s]
if __name__ == '__main__':
    root = Path(sys.argv[1]); stage = sys.argv[sys.argv.index('--stage')+1] if '--stage' in sys.argv else 'lookdev'; step = int(sys.argv[sys.argv.index('--step')+1]) if '--step' in sys.argv else 2
    vals = {int(p.stem.split('-')[1]): luma(p) for p in sorted((root/stage).glob('frame-*.png'))}
    path = json.loads((root/'path.json').read_text())['frames']; r = runs(vals, step)
    rows = [dict(first=a, last=b, seconds=round(s, 2), room=path[a]['room'], phase=path[a]['phase'], group=path[a].get('exposure_group')) for a, b, s in r]
    (root/f'dark-runs-{stage}.json').write_text(json.dumps(dict(dark_below=DARK, min_s=MIN_S, frames=len(vals), runs=rows), indent=1))
    print(len(vals), 'frames;', len(rows), 'dark runs >=', MIN_S, 's:'); [print(x) for x in rows]; sys.exit(1 if rows else 0)
