"""Read-only drift collector for the C4 approval guards (lane RA).

Builds the scene with the guards intact in production code. Around each approval pass it records every row whose
host or old/new bounds differ from the frozen authority by >1e-8 m, then lets that pass see an in-memory authority
carrying the current values so the build can continue and expose the *next* pass's drift. Nothing is written to
knowledge/c4-*-approvals.json; this only enumerates. Usage: python collect_drift.py OUT.json
"""
import json, sys, tempfile
from pathlib import Path
from archpipe.concept.fitting_mounting import bounds
from archpipe.concept import mounting_resume as MR, final_mounting as FM, exterior_mounting as EM, villa_render

ROOT = Path(MR.__file__).resolve().parents[3]
FOUND = []


def drift_rows(scene, authority, source):
    rows = {r['id']: r for r in scene['mounting_movements']}
    out = []
    for a in authority['rows']:
        r = rows.get(a['id'])
        if r is None:
            continue
        if r['host_id'] != a['host_id'] or any(abs(x-y) > 1e-8 for k in ('old', 'new') for x, y in zip(r[k], a[k])):
            out.append(dict(id=a['id'], source=source, approved_host=a['host_id'], new_host=r['host_id'],
                            approved_old=a['old'], approved_new=a['new'], old=r['old'], new=r['new'],
                            package=r.get('package'), why=r.get('why'), mm=r.get('mm')))
            a['old'], a['new'], a['host_id'] = r['old'], r['new'], r['host_id']
    return out


def patch_read(name, rewritten):
    orig = Path.read_text
    def read_text(self, *a, **k):
        return json.dumps(rewritten) if self.name == name else orig(self, *a, **k)
    Path.read_text = read_text
    return lambda: setattr(Path, 'read_text', orig)


def wrap_apply_approvals(orig):
    def f(scene, authority_path=MR.APPROVALS):
        auth = json.loads(Path(authority_path).read_text())
        FOUND.extend(drift_rows(scene, auth, Path(authority_path).name))
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as t:
            json.dump(auth, t)
        return orig(scene, Path(t.name))
    return f


def wrap_named(orig, name, hist):
    def f(scene, *a):
        import copy
        raw = json.loads((ROOT/'knowledge'/name).read_text())
        auth = copy.deepcopy(raw)
        if hist:
            from archpipe.orientation import historical_aliases
            auth = historical_aliases(auth)
        FOUND.extend(drift_rows(scene, auth, name))
        # rows are index-aligned between raw and aliased; copy the current values back to the raw rows
        for rr, aa in zip(raw['rows'], auth['rows']):
            rr['old'], rr['new'], rr['host_id'] = aa['old'], aa['new'], aa['host_id']
        undo = patch_read(name, raw)
        try:
            return orig(scene, *a)
        finally:
            undo()
    return f


if '--bypass-receipts' in sys.argv:
    # EVIDENCE ONLY, never production: the frozen furniture-stage2 / parents-bed receipts also fail on the base
    # (docs/lanes/RA-review.md, blocker B2). Measured desks/bed replacements are skipped; mounting is unaffected.
    from archpipe.concept import furniture_stage2 as FS, parents_bed as PB
    FS.apply = lambda scene, *a: scene
    PB.apply = lambda scene, *a: scene
    sys.argv.remove('--bypass-receipts')
for flag in [a for a in sys.argv if a.startswith('--ablate-')]:
    # Causal ablation (evidence only): undo ONE approved change in memory and see which drift rows vanish.
    sys.argv.remove(flag)
    if flag == '--ablate-stair-overlap':
        from archpipe.concept import stairs
        stairs.NOSING_OVERLAP = 0
    elif flag == '--ablate-corner-fix':
        from archpipe.concept import revit_spec
        revit_spec._close_corner_gaps = lambda spec, *a, **k: spec
MR.apply_approvals = wrap_apply_approvals(MR.apply_approvals)
EM.apply_lead_review = wrap_named(EM.apply_lead_review, 'c4-e-lead-approvals.json', True)
FM.apply = wrap_named(FM.apply, 'c4-final-approvals.json', True)
try:
    scene = villa_render.build()
    ids = {r['id'] for r in FOUND}
    hosts = scene['mounting_hosts']
    detail = {}
    for m in scene['meshes'] + scene.get('diagnostic_meshes', []):
        if m['id'] in ids:
            detail[m['id']] = dict(bounds=bounds(m), mounting=m.get('mounting'), host=hosts.get(m.get('mounting', {}).get('host_id')))
    # Physical evidence, computed from the live scene: every mesh mounted on a drifted row's host (or the row's own mesh)
    # against that host's finished plane, and the extent of shell wall faces coplanar with the host's structural plane.
    import numpy as np
    def physical(host_id):
        h = hosts[host_id]; n = np.array(h['normal'], float)
        fin = np.array(h['structural_point'], float) + n*h['finish']['thickness_m']
        out = []
        for m in scene['meshes'] + scene.get('diagnostic_meshes', []):
            if (m.get('mounting') or {}).get('host_id') != host_id:
                continue
            pts = np.array([q for f in m['faces'] for q in f], float)
            gap = float(((pts-fin)@n).min())
            out.append(dict(id=m['id'], bounds=bounds(m), min_gap_to_finished_face_mm=round(gap*1000, 6)))
        shell = []
        for m in scene['meshes']:
            if m.get('group') == 'shell':
                for f in m['faces']:
                    q = np.array(f, float)
                    if np.allclose((q-np.array(h['structural_point']))@n, 0, atol=1e-6):
                        shell.append(q)
        ext = None
        if shell:
            a = np.vstack(shell); ext = [a.min(axis=0).round(4).tolist(), a.max(axis=0).round(4).tolist()]
        return dict(finished_plane_point=fin.round(6).tolist(), mounted=out, coplanar_shell_extent=ext)
    for r in FOUND:
        r['physical'] = physical(r['new_host'])
        r['host_record'] = hosts.get(r['new_host'])
        r['mesh'] = detail.get(r['id'])
    json.dump(dict(scene_summary=dict(meshes=len(scene['meshes'])), stair_parts=[(m['id'], bounds(m)) for m in scene['meshes']
        if m['id'].startswith(('detail-stair','furn-stair-cupboard','joinery-understair')) or 'understair' in m['id']]),
        open(Path(sys.argv[1]).with_suffix('.extra.json'), 'w'), default=list)
finally:
    Path(sys.argv[1]).write_text(json.dumps(FOUND, indent=1))
print('drifted rows:', len(FOUND), [r['id'] for r in FOUND])
