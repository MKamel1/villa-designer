"""Features that a door leaf hides: per (feature, door), the route frames in which the feature is inside the view but its sample points are
blocked by that door's leaf, and the frames in which it is seen. Uses the per-frame leaf state (frame['doors'])."""
from __future__ import annotations
import math
import numpy as np
from . import core


def door_blocked(geom, frames, rooms, et, th, door_anim=None, fps=24, points=12, min_frames=3, seed=0):
    names = geom.elem_names; stride = th['grid']['frame_stride']; rng = np.random.default_rng(seed)
    members = core.membership(et, names, rooms)
    door_ids = {i for i, n in enumerate(names) if n.startswith('door-') and 'core' not in n}
    anim = {r['element'] for r in (door_anim or [])}
    hfov = 2*math.atan(.5*36/24); out = {}
    feats = {}
    for room, ids in members.items():
        for i in ids:
            if et['area'][i] < .05 or core.feature_kind(names[i], et['grp'][i]) not in ('furniture', 'fixture', 'dressing'):
                continue
            tri = np.flatnonzero(geom.elem == i)
            if not len(tri):
                continue
            pts = geom.tris[rng.choice(tri, min(points, len(tri)), replace=False)].mean(1).astype(np.float64)
            feats.setdefault(room, []).append((i, pts))
    for fi in range(0, len(frames), stride):
        f = frames[fi]; room = core.room_at(rooms, f['level'], *f['camera']['position'][:2])
        if room not in feats:
            continue
        c = f['camera']; pos = np.array(c['position']); fwd = np.array(c['target'])-pos; fwd /= np.linalg.norm(fwd)
        hf = 2*math.atan(.5*c['sensor_mm']/c['lens_mm'])
        for i, pts in feats[room]:
            v = pts-pos; d = np.linalg.norm(v, axis=1); u = v/d[:, None]
            infr = (u @ fwd) > math.cos(hf/2*.9)
            if not infr.any():
                continue
            od, ot, _, _ = geom.cast(np.repeat(pos[None], int(infr.sum()), 0), u[infr], doors=f.get('doors'))
            te = geom.tri_elem(ot); ok = (od >= d[infr]-.05) | (te == i)
            rec = out.setdefault(names[i], dict(room=room, in_frustum=0, seen=0, blocked_by_door={}, unseen_frames={}))
            rec['in_frustum'] += 1
            if ok.mean() >= .3:
                rec['seen'] += 1
            else:
                hit = [names[k] for k in te[~ok] if k in door_ids]
                for dn in set(hit):
                    rec['blocked_by_door'][dn] = rec['blocked_by_door'].get(dn, 0)+hit.count(dn)
                if hit:
                    rec['unseen_frames'].setdefault(max(set(hit), key=hit.count), []).append(fi)
    dt = stride/fps; res = []
    for n, r in out.items():
        top = max(r['blocked_by_door'].items(), key=lambda kv: kv[1], default=(None, 0))
        if top[0] and len(r['unseen_frames'].get(top[0], [])) >= min_frames:
            res.append(dict(feature=n, room=r['room'], door=top[0], animated=top[0] in anim, frames_in_view_unseen=r['in_frustum']-r['seen'], n_door_blocked_frames=len(r['unseen_frames'][top[0]]), door_blocked_frames=r['unseen_frames'].get(top[0], []),
                            seconds_seen=round(r['seen']*dt, 2), seconds_in_view=round(r['in_frustum']*dt, 2)))
    blocked = [x for x in res if x['seconds_seen'] == 0]
    return dict(rule=f'a furniture/fixture/dressing element whose sample points ({points}) are blocked by a door leaf in >= {min_frames} frames with the element in view; "blocked" = never seen in the route',
                blocked_features=len(blocked), features_hidden_some_frames=len(res), blocked=blocked, partly=[x for x in res if x['seconds_seen'] > 0])
