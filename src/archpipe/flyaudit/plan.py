"""Plan PNG per floor: room outlines, furniture boxes, camera path coloured by category, view cones every 1 s."""
from __future__ import annotations
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Wedge

COLOURS = dict(informative='#2e9e44', wall_dominated='#e6a100', blocked='#d62728', backward='#8e24aa', outward='#1f77b4', dark='#222222')


def plan_pngs(recs, rooms, geom, et, out, fps, stride):
    for lv in ('GF', 'B'):
        rs = [r for r in recs if r['level'] == lv]
        if not rs:
            continue
        fig, ax = plt.subplots(figsize=(16, 9), dpi=110)
        for n, r in rooms.items():
            if r['level'] != lv:
                continue
            x0, y0, x1, y1 = r['rect']
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec='#555', lw=1.2))
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, n, ha='center', va='center', fontsize=7, color='#777')
        z0 = -3. if lv == 'B' else 0.
        for i, nm in enumerate(geom.elem_names):
            if et['grp'][i] == 4 and z0 - .1 < et['lo'][i][2] < z0 + 1.5 and np.prod(et['hi'][i][:2] - et['lo'][i][:2]) < 12:
                ax.add_patch(Rectangle(et['lo'][i][:2], *(et['hi'][i][:2] - et['lo'][i][:2]), fc='#d9d9d9', ec='none', alpha=.7))
        X = np.array([[r['x'], r['y']] for r in rs]); C = [COLOURS[r['cat']] for r in rs]
        ax.scatter(X[:, 0], X[:, 1], c=C, s=5, zorder=3)
        step = max(1, int(fps / stride))                     # one cone per second
        for r in rs[::step]:
            d = min(r['median_dist'] or 2., 2.5)
            ax.add_patch(Wedge((r['x'], r['y']), d, r['yaw'] - 36.9, r['yaw'] + 36.9, fc=COLOURS[r['cat']], ec='none', alpha=.18, zorder=2))
        for k, c in COLOURS.items():
            ax.scatter([], [], c=c, label=k, s=20)
        ax.legend(loc='upper right', fontsize=8); ax.set_aspect('equal'); ax.set_title(f'Level {lv}: camera path, cones every 1 s (length = median hit distance, max 2.5 m)')
        ax.autoscale_view(); fig.tight_layout(); fig.savefig(out / f'plan-{lv}.png'); plt.close(fig)
