"""Order the stops chosen by wt_cover.py select along the walking distance and write the station list of villa-tour.json.

Basement: starts at the entry, visits every stop and the three garden thresholds, ends at the foot of the flight. GF: starts at the top of the flight.
Nearest-neighbour then 2-opt on A* walking length (open path, fixed ends). usage: scripts/wt_py.sh scripts/tour_order.py
"""
import json, math, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src'), str(ROOT/'scripts')]
from archpipe import walkthrough_tour as WT
from wt_plan import vmap

def order(vm, lv, nodes, start, end):
    """nodes [(id, (x,y))]; returns ids ordered start -> ... -> end (end None = free)."""
    pts = [start]+[p for _, p in nodes]+([end] if end else []); n = len(pts); D = np.zeros((n, n))
    for a in range(n):
        for b in range(a+1, n):
            try: pa = vm.astar(lv, pts[a], pts[b]); D[a, b] = D[b, a] = sum(math.dist(pa[k][:2], pa[k+1][:2]) for k in range(len(pa)-1))
            except ValueError: D[a, b] = D[b, a] = 1e3
    m = len(nodes); seq = []; left = set(range(1, m+1)); cur = 0
    while left:
        nx = min(left, key=lambda j: D[cur, j]); seq.append(nx); left.remove(nx); cur = nx
    tail = [n-1] if end else []
    cost = lambda s: sum(D[a, b] for a, b in zip([0]+s+tail, s+tail))
    better = True
    while better:
        better = False
        for i in range(len(seq)):
            for j in range(i+1, len(seq)):
                t = seq[:i]+seq[i:j+1][::-1]+seq[j+1:]
                if cost(t) < cost(seq)-1e-9: seq = t; better = True
    return [nodes[k-1][0] for k in seq], cost(seq)

if __name__ == '__main__':
    layout, spec, vm = vmap(); route = WT.tour_route(); sp = json.loads((ROOT/'knowledge/flythrough/tour-spaces.json').read_text())['stations']
    by = {s['id']: s for s in sp}; gardens = route.get('orig_gardens') or [s for s in route['stations'] if s.get('garden')]
    via = {}      # the old authored pinch via-points (door at x 21.897) are gone: DF moved the dressing door to x 19.977 and the A* finds the 0.849 m door-to-door route
    stop = lambda i: dict(space=i, **({'via': via[by[i]['room']]} if by[i]['room'] in via else {}))
    entry = tuple(WT.tour_points()['entry-b']); top = tuple(route['stair']['top']); foot = (route['stair']['bottom'][0]+0., route['stair']['bottom'][1])
    out = [dict(start=list(entry))]
    nodesB = [(s['id'], tuple(s['point'])) for s in sp if s['level'] == 'B']
    G = {}
    for g in gardens:
        p, _ = WT._inward(vm, g['door'], WT.tour_policy()['garden_inward_offsets_m']); G['garden:'+g['garden']] = (g, p); nodesB.append(('garden:'+g['garden'], tuple(p)))
    seqB, cB = order(vm, 'B', nodesB, entry, foot)
    for i in seqB:
        out.append(dict(G[i][0]) if i in G else stop(i))
    out.append(dict(stair='up'))
    seqG, cG = order(vm, 'GF', [(s['id'], tuple(s['point'])) for s in sp if s['level'] == 'GF'], top, None)
    for i in seqG:
        out.append(stop(i))
    new = dict(route, stations=out, orig_gardens=gardens)
    (ROOT/'knowledge/flythrough/villa-tour.json').write_text(json.dumps(new, indent=1))
    print('B', round(cB, 1), 'm', seqB); print('GF', round(cG, 1), 'm', seqG)
