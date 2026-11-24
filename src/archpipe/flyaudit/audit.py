"""Drive the audit: load route + scene, run core, write report.json, frames.json, rooms.md and plan PNGs."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
from . import core
from .geometry import Geometry, extract


def load_route(path):
    d = json.loads(Path(path).read_text())
    frames = d['frames'] if isinstance(d, dict) else d
    settings = d.get('settings', {}) if isinstance(d, dict) else {}
    settings = dict(dict(fps=24, final_resolution=[1920, 1080]), **{k: v for k, v in settings.items() if k in ('fps', 'final_resolution')})
    return dict(frames=frames, settings=settings, stations=d.get('stations', []) if isinstance(d, dict) else [],
                sha=(d.get('sha256') if isinstance(d, dict) else None))


def geometry_for(scene_path, cache_dir):
    cache_dir.mkdir(parents=True, exist_ok=True)
    sp = Path(scene_path)
    cache = cache_dir / f'{sp.parent.name}-{sp.stat().st_size}.npz'
    if not cache.exists() or cache.stat().st_mtime < sp.stat().st_mtime:
        extract(sp, cache)
    return Geometry.load(cache)


def design_rooms():
    from archpipe.concept import villa_r11 as R
    return {n: dict(level=r['level'], rect=list(r['rect'])) for n, r in R.design('D1')['rooms'].items()}


def resolve_subjects(geom, et, views_path):
    names = geom.elem_names; out = []
    rng = np.random.default_rng(0)
    for v in json.loads(Path(views_path).read_text())['views']:
        for s in v.get('subjects') or []:
            if s.startswith('room:'):
                continue
            ids = [i for i, n in enumerate(names) if n == 'furn-' + s or n == s] or [i for i, n in enumerate(names) if n.startswith('furn-' + s)]
            if not ids:
                out.append(dict(id=s, view=v['id'], unresolved=True)); continue
            tri = np.flatnonzero(np.isin(geom.elem, ids))
            pick = rng.choice(tri, min(40, len(tri)), replace=False)
            pts = geom.tris[pick].mean(1).astype(np.float64)
            rooms = set(v.get('covers') or []) | {et['room'][i] for i in ids if et['room'][i]}
            out.append(dict(id=s, view=v['id'], elems=ids, points=pts, rooms=rooms,
                            elem_names=[names[i] for i in ids]))
    return out


def run(route_path, scene_path, out_dir, route_id=None, rooms=None, views=None, cache_dir=None, log=print):
    th = core.thresholds(); R = load_route(route_path); frames = R['frames']; fps = R['settings']['fps']
    stride = th['grid']['frame_stride']
    rooms = rooms or design_rooms()
    geom = geometry_for(scene_path, Path(cache_dir or core.ROOT / 'out/flyaudit'))
    et = core.element_table(geom)
    subj = resolve_subjects(geom, et, views or core.ROOT / 'knowledge/render-set/views.json')
    live = [s for s in subj if not s.get('unresolved')]
    t0 = time.time()
    surface = np.array([core.feature_kind(n, g) is not None for n, g in zip(geom.elem_names, et['grp'])])
    recs, st, sstats = core.analyse_frames(geom, frames, R['settings'], rooms, th, live,
                                           lambda i, n: log(f'  frame {i}/{n} {time.time()-t0:.0f}s'), surface)
    nod1, nod = no_daylight_v1(geom, rooms), no_daylight(geom, rooms, th)
    core.classify(recs, th, nod1, version=1, key='cat_v1')
    core.classify(recs, th, nod)
    report = summarise(recs, st, sstats, subj, geom, et, rooms, th, R, nod)
    out = Path(out_dir) / (route_id or Path(route_path).parent.name or 'route'); out.mkdir(parents=True, exist_ok=True)
    (out / 'report.json').write_text(json.dumps(report, indent=1))
    (out / 'frames.json').write_text(json.dumps(recs, separators=(',', ':')))
    (out / 'rooms.md').write_text(rooms_markdown(report))
    from .plan import plan_pngs
    plan_pngs(recs, rooms, geom, et, out, fps, stride)
    return report, recs


def no_daylight_v1(geom, rooms):
    """Registered v1 proxy. Rooms with no glass triangle within 0.6 m of their rectangle and level slab (the dark-proxy of thresholds.json)."""
    g = geom.tris[geom.cls == 1].mean(1)
    res = set()
    for n, r in rooms.items():
        x0, y0, x1, y1 = r['rect']; z0 = -3. if r['level'] == 'B' else 0.
        near = ((g[:, 0] > x0 - .6) & (g[:, 0] < x1 + .6) & (g[:, 1] > y0 - .6) & (g[:, 1] < y1 + .6) & (g[:, 2] > z0) & (g[:, 2] < z0 + 3.2))
        if not near.any():
            res.add(n)
    return res


def share(recs, cat=None, key='cat'):
    return round(sum(1 for r in recs if cat is None or r[key] == cat) / max(1, len(recs)), 4)


CATS = ['informative', 'wall_dominated', 'blocked', 'backward', 'outward', 'dark']


def summarise(recs, st, sstats, subj, geom, et, rooms, th, R, nod):
    fps, stride = R['settings']['fps'], th['grid']['frame_stride']; dt = stride / fps
    names = geom.elem_names; E = len(names)
    bad_runs = core.runs(recs, fps, stride, th['bad_run_s'])
    per_room = {}; members = core.membership(et, names, rooms)
    for n, r in rooms.items():
        rr = [x for x in recs if x['room'] == n]
        feats = []; k_room = st['rooms'].index(n)
        for i in members[n]:
            if et['area'][i] < .05:
                continue
            k = core.feature_kind(names[i], et['grp'][i])
            if k:
                seen = int(st['room_frames'][k_room, i])
                feats.append(dict(id=names[i], kind=k, area_m2=round(float(et['area'][i]), 2), seen_s=round(seen * dt, 2),
                                  min_dist_m=None if not seen else round(float(st['room_min_d'][k_room, i]), 2)))
        by = {}
        for k in ('wall', 'furniture', 'fixture', 'dressing', 'shell'):
            f = [x for x in feats if x['kind'] == k]
            by[k] = dict(total=len(f), seen=sum(1 for x in f if x['seen_s'] > 0))
        per_room[n] = dict(level=r['level'], seconds=round(len(rr) * dt, 1),
                           cats={c: share(rr, c) for c in CATS} if rr else {},
                           full_360=core.full_360(recs, n, th, fps, stride),
                           no_daylight=n in nod, seen_share=by,
                           never_seen=[x['id'] for x in feats if x['seen_s'] == 0],
                           features=feats,
                           bad_runs=[b for b in bad_runs if b['room'] == n])
    subjects = []
    for s in subj:
        if s.get('unresolved'):
            subjects.append(dict(id=s['id'], view=s['view'], status='UNRESOLVED (no element of that name in the scene)')); continue
        ss = sstats[s['id']]
        status = ('seen' if ss['visible'] else 'BLOCKED' if ss['in_frustum'] else 'NEVER IN FRAME' if ss['frames_room'] else 'room never entered')
        top = sorted(ss['blockers'].items(), key=lambda kv: -kv[1])[:5]
        subjects.append(dict(id=s['id'], view=s['view'], rooms=sorted(s['rooms']), status=status,
                             seconds_visible=round(ss['visible'] * dt, 2), seconds_in_frustum=round(ss['in_frustum'] * dt, 2),
                             seconds_in_room=round(ss['frames_room'] * dt, 2),
                             best_distance_m=None if not ss['best'] else round(ss['best'][2], 2),
                             blockers=[dict(id=k, hits=v) for k, v in top]))
    stair = [r for r in recs if r['stair']]; zs = [R['frames'][r['i']]['ground_m'] for r in stair]
    stair_ids = [i for i, n in enumerate(names) if n == 'stair-main']
    garden = [r for r in recs if r['garden']]
    levels = {lv: dict(seconds=round(sum(1 for r in recs if r['level'] == lv) * dt, 1)) for lv in ('GF', 'B')}
    visited = sorted({r['room'] for r in recs if r['room']})
    whole = dict(seconds=round(len(recs) * dt, 1), frames_sampled=len(recs), stride=stride, levels=levels,
                 rooms_entered=len(visited), rooms_total=len(rooms), rooms_never_entered=sorted(set(rooms) - set(visited)),
                 stair=dict(frames_sampled=len(stair), seconds=round(len(stair) * dt, 1),
                            ground_z_range=[round(min(zs), 2), round(max(zs), 2)] if zs else None,
                            flight_element_seen_s=round(float(sum(st['frames'][i] for i in stair_ids) * dt), 1)),
                 gardens=dict(seconds=round(len(garden) * dt, 1), frames_sampled=len(garden)),
                 cats={c: share(recs, c) for c in CATS},
                 interior_cats={c: share([r for r in recs if not r['garden']], c) for c in CATS},
                 informative_share=share(recs, 'informative'),
                 bad_runs_over_1s=len(bad_runs), bad_run_seconds=round(sum(b['seconds'] for b in bad_runs), 1))
    cal = calibration(recs, R, th)
    return dict(schema='flyaudit/1', route_sha256=R['sha'], thresholds=th, whole=whole, rooms=per_room, subjects=subjects,
                bad_runs=bad_runs, calibration=cal,
                limits=['Geometry is the scene meshes (imported furniture appears as its stand-in/evaluated meshes in the scene file); curtains and cloth are included only if present as meshes.',
                        'Glass is see-through for coverage. Features inside closed cupboards are reported never-seen.',
                        'dark is a proxy (room with no glazing under one house-wide day exposure), not a lux measurement.'])


def calibration(recs, R, th):
    """Statistics on interior frames: all, and the lead's sampling (every 144th interior path frame)."""
    interior = [r for r in recs if not r['garden']]
    every = 144
    sample = [r for r in interior if r['i'] % every < th['grid']['frame_stride']] if False else \
             [r for r in interior if (r['i'] // th['grid']['frame_stride']) % (every // th['grid']['frame_stride']) == 0]
    f = lambda rs, key='cat': dict(n=len(rs), **{c: share(rs, c, key) for c in CATS})
    sens = {}
    for near in (.4, .5, .6):                    # sensitivity of the wall-dominated threshold, reported not tuned
        sens[f'wall_near_share>={near}'] = round(sum(1 for r in interior if r['near_share'] >= near) / max(1, len(interior)), 4)
    return dict(interior_all=f(interior), lead_sampling_every_6s=f(sample), interior_all_v1_registered=f(interior, 'cat_v1'), lead_sampling_every_6s_v1_registered=f(sample, 'cat_v1'), wall_threshold_sensitivity=sens,
                lead_counts_by_eye=dict(wall_dominated=.30, near_black=.12, good=.40))


def rooms_markdown(rep):
    L = ['# Per-room audit', '', '| room | lvl | s in room | informative | wall | blocked | backward | outward | dark | 360 (deg, at) | walls seen | furniture seen | fixtures seen | never seen |', '|' + '---|' * 14]
    for n, r in rep['rooms'].items():
        c = r['cats'] or {}; s = r['seen_share']; z = r['full_360']
        f = lambda k: f"{s[k]['seen']}/{s[k]['total']}"
        L.append(f"| {n} | {r['level']} | {r['seconds']} | {c.get('informative','-')} | {c.get('wall_dominated','-')} | {c.get('blocked','-')} | {c.get('backward','-')} | {c.get('outward','-')} | {c.get('dark','-')} | {z['coverage_deg']}{' OK' if z['full'] else ' NO'} {z['at'] or ''} | {f('wall')} | {f('furniture')} | {f('fixture')} | {len(r['never_seen'])} |")
    L += ['', '## Never-seen features', '']
    for n, r in rep['rooms'].items():
        if r['never_seen']:
            L.append(f"* **{n}**: " + ', '.join(r['never_seen'][:40]) + (' ...' if len(r['never_seen']) > 40 else ''))
    L += ['', '## Key subjects of the still views', '', '| subject | view | status | s visible | s in frustum | s in room | blockers |', '|---|---|---|---|---|---|---|']
    for s in rep['subjects']:
        L.append(f"| {s['id']} | {s['view']} | {s['status']} | {s.get('seconds_visible','')} | {s.get('seconds_in_frustum','')} | {s.get('seconds_in_room','')} | {', '.join(b['id'] for b in s.get('blockers', []))} |")
    L += ['', '## Runs over 1 s of wall-dominated / backward / blocked frames', '']
    for b in rep['bad_runs']:
        L.append(f"* frames {b['start_frame']}-{b['end_frame']} ({b['seconds']} s) in {b['room']} [{b['level']}]: {b['cats']}")
    return '\n'.join(L) + '\n'


def no_daylight(geom, rooms, th):
    """v2 proxy: rooms from whose centre / quarter points no window or glazed door is seen by enough rays."""
    cfg = th['dark_proxy_v2']; az = np.radians(np.arange(0, 360, 5.)); pit = np.radians([-10., 0., 10., 20.])
    A, P = np.meshgrid(az, pit)
    D = np.stack([np.cos(P) * np.cos(A), np.cos(P) * np.sin(A), np.sin(P)], -1).reshape(-1, 3)
    glassy = np.array([n.startswith(('window-', 'door-')) for n in geom.elem_names])
    res = set()
    for n, r in rooms.items():
        x0, y0, x1, y1 = r['rect']; z = (-3. if r['level'] == 'B' else 0.) + 1.35
        best = 0.
        for fx, fy in ((.5, .5), (.25, .25), (.75, .25), (.25, .75), (.75, .75)):
            o = np.array([x0 + (x1 - x0) * fx, y0 + (y1 - y0) * fy, z])
            d, t, gd, gt = geom.cast(np.repeat(o[None], len(D), 0), D)
            ok = (gt >= 0) & (gd < d) & (gd <= cfg['max_glass_dist_m']) & glassy[geom.tri_elem(gt)]
            best = max(best, float(ok.mean()))
        if best < cfg['min_glass_share']:
            res.add(n)
    return res
