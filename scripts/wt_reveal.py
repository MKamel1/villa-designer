"""Per-frame proof that a feature a door leaf hides is seen when the leaf is closed (lane WT).
usage: scripts/wt_py.sh scripts/wt_reveal.py <plan.json> <door element> <feature element> [first last]
Prints, per 4 frames, leaf state, camera heading, in-view (90 % of the half-FOV) and the share of the feature's sample points reached by an unobstructed ray;
then totals: frames in view, frames seen (>= 30 % of points, the audit's rule), frames seen with the leaf >= 99 % closed."""
import json, math, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src')]
from archpipe.flyaudit import audit, core


def reveal(plan, door, feature, first=0, last=None, scene=None, step=1):
    R = audit.load_route(plan); frames = R['frames']; th = core.thresholds()
    geom = audit.geometry_for(scene or ROOT/'out/wt/villa8/scene.json', ROOT/'out/flyaudit'); et = core.element_table(geom)
    geom = geom.animate(R['door_anim']); names = geom.elem_names
    i = next(k for k, n in enumerate(names) if n == feature)
    tri = np.flatnonzero(geom.elem == i); pts = geom.tris[np.random.default_rng(0).choice(tri, min(12, len(tri)), replace=False)].mean(1).astype(np.float64)
    rows = []
    for fi in range(first, last if last is not None else len(frames), step):
        f = frames[fi]; c = f['camera']; pos = np.array(c['position']); fwd = np.array(c['target'])-pos; fwd /= np.linalg.norm(fwd)
        hf = 2*math.atan(.5*c['sensor_mm']/c['lens_mm']); v = pts-pos; d = np.linalg.norm(v, axis=1); u = v/d[:, None]
        infr = (u @ fwd) > math.cos(hf/2*.9)
        if not infr.any():
            rows.append((fi, f.get('doors', {}).get(door, 1.), False, 0.)); continue
        od, ot, _, _ = geom.cast(np.repeat(pos[None], int(infr.sum()), 0), u[infr], doors=f.get('doors'))
        ok = (od >= d[infr]-.05) | (geom.tri_elem(ot) == i)
        rows.append((fi, f.get('doors', {}).get(door, 1.), True, float(ok.mean())))
    return rows


if __name__ == '__main__':
    a = sys.argv; first, last = (int(a[4]), int(a[5])) if len(a) > 5 else (0, None)
    rows = reveal(a[1], a[2], a[3], first, last)
    for r in rows[::4]: print(r[0], f'leaf {r[1]:.2f}', 'IN' if r[2] else '--', f'{r[3]:.2f}')
    inv = [r for r in rows if r[2]]; seen = [r for r in inv if r[3] >= .3]; closed = [r for r in seen if r[1] <= .01]
    print(f'frames {len(rows)} in view {len(inv)} seen {len(seen)} seen with leaf closed {len(closed)}; closed frames in range: {sum(1 for r in rows if r[1] <= .01)}')
