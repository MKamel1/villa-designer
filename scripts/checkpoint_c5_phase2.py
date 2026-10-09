"""Compare captured C5 checkpoints and create neutral corner preview inputs.

Run with the intended Python and PYTHONPATH=src. This never writes an extract,
shared round3 data, product assets or presentation images.
"""
from copy import deepcopy
import json
from pathlib import Path
import argparse

from archpipe.concept import villa_render as VR
from archpipe.concept.fitting_mounting import bounds
from archpipe.fixture_record import centred_vanity_pair, vanity_pair_findings

ROOT = Path(__file__).resolve().parents[1]
CORRECTED = {'SCONCE-guest-wc-03':(9.36,-23.476), 'SCONCE-guest-wc-04':(9.36,-22.526),
             'VSCONCE-parents-ensuite-04':(19.887,-29.916), 'VSCONCE-parents-ensuite-05':(19.887,-28.966)}


def preview_receipt_findings(receipt, expected_view):
    """Reject a successful preview process that rendered zero requested views."""
    if len(receipt) != 1 or receipt[0].get('id') != expected_view:
        return ['preview receipt must contain exactly the requested view: '+expected_view]
    if not Path(receipt[0]['image']).is_file():
        return ['preview image missing: '+receipt[0]['image']]
    return []


def lead_review(before, current, rejected):
    """Measure the rejected pairs; infeasibility stops placement changes.

    Numeric preservation and design acceptance are separate results. The
    frozen rejection supplies actual mesh bounds and explicitly assumed
    mirror gaps, not a generated extract edited to fit a rule.
    """
    rooms = []
    current_meshes = {mesh['id']:mesh for mesh in current['fixture_meshes']}
    for row in rejected['rooms']:
        interval = (row['room_rect'][1], row['room_rect'][3])
        centres = []
        for mesh in row['meshes']:
            if mesh['id'].startswith('lamp-'):
                actual = current_meshes.get(mesh['id'])
                if actual is None:
                    continue  # The independent pair check rejects missing members.
                extent = bounds(actual)
                centres.append((extent[1]+extent[4])/2)
        arguments = dict(clear_interval=interval, axis=row['axis'],
                         mirror_interval=row['mirror_interval'], half_width=row['half_width'],
                         minimum_gap=row['minimum_gap'], edge_allowance=row['edge_allowance'])
        findings = vanity_pair_findings(centres, **arguments)
        try:
            proposed = centred_vanity_pair(**arguments, authored_separation=row['authored_separation'])
            refusal = None
        except ValueError as exc:
            proposed, refusal = None, str(exc)
        maximum = min(row['authored_separation'],
                      2*(row['axis']-interval[0]-row['half_width']-row['edge_allowance']),
                      2*(interval[1]-row['axis']-row['half_width']-row['edge_allowance']))
        minimum = 2*(max(row['axis']-row['mirror_interval'][0],
                         row['mirror_interval'][1]-row['axis'])+row['half_width']+row['minimum_gap'])
        ordered = sorted(centres)
        gaps = ([row['mirror_interval'][0]-ordered[0]-row['half_width'],
                 ordered[1]-row['half_width']-row['mirror_interval'][1]] if len(ordered)==2 else [])
        rooms.append(dict(room=row['room'], axis_m=row['axis'],
                          mirror_interval_m=row['mirror_interval'], clear_interval_m=interval,
                          measured_centres_m=ordered, measured_gaps_mm=[v*1000 for v in gaps],
                          assumed_minimum_gap_mm=row['minimum_gap']*1000, gap_source=row['gap_source'],
                          maximum_separation_mm=maximum*1000, minimum_separation_mm=minimum*1000,
                          separation_shortfall_mm=max(0,minimum-maximum)*1000,
                          maximum_centred_mirror_gap_mm=(maximum/2-row['half_width']-
                                                        (row['mirror_interval'][1]-row['mirror_interval'][0])/2)*1000,
                          proposed_centres_m=proposed, refusal=refusal, findings=findings))
    return dict(design_passed=all(not row['findings'] and not row['refusal'] for row in rooms),
                placement_changed=False, rooms=rooms,
                grooming_tasks=[dict(original=old, lead_review=current_task)
                                for old,current_task in zip(before['lighting']['tasks'], current['lighting']['tasks'])
                                if old['what'] in ('gwc-basin','pe-basin')],
                unexpected_numeric_differences=numeric_findings(before, before, current))


def numeric_findings(before, unified, after):
    """Fail on every difference outside the two complete pair corrections."""
    # Captures are JSON contracts. Tuple/list representations have identical
    # exported meaning; normalize through that exact serialization boundary.
    before, unified, after = [json.loads(json.dumps(value)) for value in (before,unified,after)]
    failures = []
    for key in ('fixtures','lighting','lights','spec','fixture_meshes'):
        if before[key] != unified[key]:
            failures.append('pure re-expression changed '+key)
    expected = deepcopy(before['fixtures'])
    for fixture in expected:
        if fixture['id'] in CORRECTED:
            fixture['x'],fixture['y']=CORRECTED[fixture['id']]
            fixture['extra']['vanity_pair_source_correction']=True
    if after['fixtures'] != expected:
        failures.append('fixture changes exceed the two complete pair corrections')
    for key in ('lights','spec'):
        if after[key] != before[key]:
            failures.append('unexpected '+key+' change')
    expected = deepcopy(before['lighting'])
    for task in expected['tasks']:
        if task['what']=='pe-basin':task['achieved_lx']=699
        if task['what']=='gwc-basin':task['achieved_lx']=1357
    expected['problems'] = [text.replace('guest-wc/gwc-basin 1354 lx','guest-wc/gwc-basin 1357 lx') for text in expected['problems']]
    if after['lighting'] != expected:
        failures.append('unexpected lighting-check numeric or status change')
    old={m['id']:m for m in before['fixture_meshes']}
    new={m['id']:m for m in after['fixture_meshes']}
    if old.keys()!=new.keys():failures.append('fixture mesh identity changed')
    delta={'SCONCE-guest-wc-03':.050,'SCONCE-guest-wc-04':.149,
           'VSCONCE-parents-ensuite-04':-.160,'VSCONCE-parents-ensuite-05':-.160}
    for name,mesh in new.items():
        root=next((fid for fid in delta if name.endswith('-'+fid)),None)
        if root is None:
            if mesh!=old[name]:failures.append('unrelated fixture changed: '+name)
            continue
        want=deepcopy(old[name])
        want['faces']=[[[p[0],p[1]+delta[root],p[2]] for p in face] for face in want['faces']]
        error=max(abs(p[i]-q[i]) for face,other in zip(mesh['faces'],want['faces'])
                  for p,q in zip(face,other) for i in range(3))
        if error>1e-12:failures.append('unexpected geometry change: '+name)
    return failures


def neutral_input(scene, room, camera):
    """Copy the complete production camera schema before choosing a diagnostic pose."""
    position,target = (([10.7,-23.001,-1.4],[9.3,-23.001,-1.4]) if room=='guest-wc'
                       else ([21.1,-29.441,1.6],[19.827,-29.441,1.6]))
    missing = [key for key in ('position','target','lens_mm','sensor_mm') if key not in camera]
    if missing:
        raise ValueError('Incomplete production camera schema: '+', '.join(missing))
    camera=deepcopy(camera)
    camera.update(position=position,target=target)
    meshes=[m for m in scene['meshes'] if m.get('room')==room
            and m.get('group') in ('shell','fixture','furniture')]
    if room=='parents-ensuite':
        meshes += [m for m in scene['meshes'] if m.get('room')=='parents-dressing-ext'
                   and m.get('group')=='shell']
    names={m['material'] for m in meshes}|{n for m in meshes for n in m.get('face_materials',[])}
    return dict(materials={n:scene['materials'][n] for n in names},meshes=meshes,props=[],
                views=[dict(id=room,camera=camera,resolution=[960,640],
                            subjects=[m['id'] for m in meshes if m['id'].startswith('lamp-')])],
                neutral_preview_fill=[dict(watts=100,size_m=1.5,position_m=position,target_m=target)])


def client_decision_findings(before, current):
    """Permit only the dated pair-to-bar decision; protect all retained inputs.

    Captures use the JSON contract. The two room floor averages and grooming
    task values can change; every other measurement, target and status stays
    frozen. Complete fitting geometry is reviewed separately from arithmetic.
    """
    from archpipe.fixture_record import VANITY_DECISIONS
    before,current=[json.loads(json.dumps(s)) for s in (before,current)]
    retired={fid for pair in VANITY_DECISIONS.values() for fid in pair}
    new=[f for f in current['fixtures'] if f['extra'].get('over_mirror')]
    new_ids={f['id'] for f in new}
    failures=[]
    if len(new)!=2 or {f['room'] for f in new}!=set(VANITY_DECISIONS):
        failures.append('expected one over-mirror fitting in each decision room')
    if [f for f in before['fixtures'] if f['id'] not in retired] != [f for f in current['fixtures'] if f['id'] not in new_ids]:
        failures.append('unrelated fixture input changed or retired pair remains')
    for key in ('lights','spec'):
        if before[key]!=current[key]:failures.append('unrelated '+key+' changed')
    old_native=[f for f in before['native_lighting'] if f['id'] not in retired]
    new_native=[f for f in current['native_lighting'] if f['id'] not in new_ids]
    if old_native!=new_native:failures.append('unrelated native lighting changed')
    from archpipe.concept.villa_lighting import Fixture
    native_by_id={f['id']:f for f in current['native_lighting']}
    for fixture in new:
        if native_by_id.get(fixture['id'])!=Fixture(**fixture).record.native_spec():
            failures.append('over-mirror native adapter disagrees with shared record')
    for key in ('tasks','rooms'):
        old,current_rows=before['lighting'][key],current['lighting'][key]
        if len(old)!=len(current_rows):failures.append('lighting measurement identity changed: '+key)
        for a,b in zip(old,current_rows):
            if a['room'] in VANITY_DECISIONS:
                allowed='achieved_lx' if key=='tasks' else 'avg_floor_lx_direct'
                if {k:v for k,v in a.items() if k!=allowed}!={k:v for k,v in b.items() if k!=allowed}:
                    failures.append('decision room target, identity or status changed')
            elif a!=b:failures.append('unrelated lighting measurement changed: '+a['room'])
    for side in ('before','current'):
        report=before['lighting'] if side=='before' else current['lighting']
        filtered=[p for p in report['problems'] if not p.startswith(tuple(r+'/' for r in VANITY_DECISIONS))]
        if side=='before':old_problems=filtered
        elif filtered!=old_problems:failures.append('unrelated lighting diagnostic changed')
    if before['lighting']['note']!=current['lighting']['note']:
        failures.append('lighting method changed')
    expected_kinds=(set(before['lighting']['generic_kinds']) & {f['kind'] for f in current['fixtures']})|{'VANITY-LIN'}
    if set(current['lighting']['generic_kinds'])!=expected_kinds:failures.append('generic photometry family changed')
    old={m['id']:m for m in before['fixture_meshes'] if not any(m['id'].endswith('-'+f) for f in retired)}
    actual={m['id']:m for m in current['fixture_meshes'] if not any(m['id'].endswith('-'+f) for f in new_ids)}
    if old!=actual:failures.append('unrelated fixture mesh changed or retired fitting remains')
    expected_new_meshes={prefix+fid for fid in new_ids for prefix in ('body-','lamp-')}
    actual_new_meshes={m['id'] for m in current['fixture_meshes']
                       if any(m['id'].endswith('-'+fid) for fid in new_ids)}
    if expected_new_meshes!=actual_new_meshes:failures.append('complete over-mirror fitting missing or duplicated')
    return failures


def scene_preservation_findings(before, current):
    """Compare complete exported geometry, including tuple/JSON equivalence."""
    before,current=[json.loads(json.dumps(s)) for s in (before,current)]
    failures=[]
    for group in ('shell','furniture','dressing'):
        a={m['id']:m for m in before['meshes'] if m['group']==group}
        b={m['id']:m for m in current['meshes'] if m['group']==group}
        if a!=b:failures.append('unrelated '+group+' geometry or metadata changed')
    for key in ('props','models','cloth','curtains'):
        if before[key]!=current[key]:failures.append('unrelated '+key+' changed')
    return failures


def client_decision_capture(folder):
    """Build current source, measure lux and export same-camera neutral inputs."""
    from dataclasses import asdict
    from archpipe.concept import villa_lighting as VL, villa_r11 as R, revit_spec as RS
    from archpipe.fixture_record import vanity_scene_findings, VANITY_DECISION_SOURCE
    folder.mkdir(parents=True,exist_ok=True)
    lay=R.design('D1');fixtures=VL.design(lay)
    scene=VR.build(lay,views=[])
    current=dict(fixtures=[asdict(f) for f in fixtures],lighting=VL.check(lay,fixtures),
                 lights=scene['lights'],spec=RS.build(lay),native_lighting=RS.lighting_spec(lay),
                 fixture_meshes=[m for m in scene['meshes'] if m['group']=='fixture'])
    # The final checkpoint includes the completed dimension consolidation;
    # after.json predates it and is retained only as historical evidence.
    before=json.loads((folder.parent/'final-after.json').read_text())
    failures=client_decision_findings(before,current)+vanity_scene_findings(scene,[f.record for f in fixtures])
    from archpipe.concept.mounting import scene_findings
    failures+=scene_findings(scene)
    # Check the complete saved scene too, so mirror/basin/furniture changes
    # cannot hide behind the fixture-only comparison.
    old_scene=json.loads((folder.parent/'after-scene.json').read_text())
    failures+=scene_preservation_findings(old_scene,scene)
    no_bars=VL.check(lay,[f for f in fixtures if not f.extra.get('over_mirror')])
    tasks=[]
    for what in ('gwc-basin','pe-basin'):
        row=lambda report:next(t for t in report['tasks'] if t['what']==what)
        tasks.append(dict(before=row(before['lighting']),after=row(current['lighting']),
                          retained_lights_only=row(no_bars)))
    previews=[]
    for room in ('guest-wc','parents-ensuite'):
        reference=json.loads((folder.parent/'lead-review/previews-unchanged'/room/'context-preview-evidence.json').read_text())[0]
        data=neutral_input(scene,room,reference['camera'])
        data['views'][0]['camera']=deepcopy(reference['camera'])
        if data['neutral_preview_fill']!=reference['neutral_preview_fill']:
            failures.append('neutral fill changed: '+room)
        path=folder/(room+'-preview-input.json');path.write_text(json.dumps(data))
        previews.append(dict(room=room,input=str(path),camera=reference['camera'],
                             neutral_fill=reference['neutral_preview_fill']))
    (folder/'current.json').write_text(json.dumps(current,indent=2)+'\n')
    report=dict(source=VANITY_DECISION_SOURCE,passed=not failures,failures=failures,
                fixture_count_before=len(before['fixtures']),fixture_count_after=len(fixtures),
                replacements=scene['vanity_client_decisions'],grooming_tasks=tasks,
                lighting=current['lighting'],previews=previews,
                lighting_limitation='ASSUMED generic isotropic family; direct maintained task points, '
                    'maintenance factor 0.8, no furniture shadows or inter-reflection; '
                    'no new independent Blender lighting or native Revit read-back')
    (folder/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=report['passed'],failures=failures,grooming_tasks=tasks)))
    return 0 if report['passed'] else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',type=Path,default=ROOT/'out/c5-phase2')
    parser.add_argument('--previews',action='store_true')
    parser.add_argument('--lead-review',action='store_true',help='Fail closed on symmetry or an infeasible centred pair')
    parser.add_argument('--client-decision',action='store_true',help='Validate the 2026-10-08 single over-mirror decision')
    args=parser.parse_args()
    from archpipe.execution_context import project_context
    project_context(ROOT, Path(__file__).resolve(), 'c5-phase2-checkpoint')
    if args.client_decision:
        return client_decision_capture(args.folder/'client-decision')
    before,unified,after=[json.loads((args.folder/(name+'.json')).read_text())
                          for name in ('before','unified','after')]
    failures=numeric_findings(before,unified,after)
    summary=dict(failures=failures,fixture_count=len(before['fixtures']),
                 unchanged_light_count=len(before['lights']),unchanged_revit_shell=before['spec']==after['spec'],
                 corrected_fixture_count=len(CORRECTED),unchanged_floor_average_count=len(before['lighting']['rooms']),
                 task_changes=[dict(before=a,after=b) for a,b in zip(before['lighting']['tasks'],after['lighting']['tasks']) if a!=b],
                 mesh_changes=[dict(id=m['id'],before=bounds(old),after=bounds(m))
                               for old,m in zip(before['fixture_meshes'],after['fixture_meshes']) if old['faces']!=m['faces']])
    (args.folder/'numeric-comparison.json').write_text(json.dumps(summary,indent=2)+'\n')
    rejected=json.loads((ROOT/'tests/fixtures/c5_lead_rejected_pairs.json').read_text())
    review=lead_review(before,after,rejected)
    (args.folder/'lead-review-comparison.json').write_text(json.dumps(review,indent=2)+'\n')
    if args.lead_review:
        from dataclasses import asdict
        from archpipe.concept import villa_lighting as VL, villa_r11 as R
        current=deepcopy(after)
        layout=R.design('D1')
        fixtures=VL.design(layout)
        current['fixtures']=[asdict(f) for f in fixtures]
        current['lighting']=VL.check(layout,fixtures)
        report=lead_review(before,current,rejected)
        (args.folder/'lead-review-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(dict(design_passed=report['design_passed'], placement_changed=False,
                              unexpected_numeric_differences=report['unexpected_numeric_differences'],
                              report=str(args.folder/'lead-review-comparison.json'))))
        return 0 if report['design_passed'] and not report['unexpected_numeric_differences'] else 1
    if args.previews:
        # Reuse the authored 24 mm full-frame camera schema; pose is diagnostic.
        camera=VR.VIEWS(resolve=False)[0]['camera']
        for name in ('scene','after-scene'):
            scene=json.loads((args.folder/(name+'.json')).read_text())
            for room in ('guest-wc','parents-ensuite'):
                path=args.folder/(room+'-'+name+'-preview-input.json')
                path.write_text(json.dumps(neutral_input(scene,room,camera)))
    print(json.dumps({k:v for k,v in summary.items() if k not in ('mesh_changes','task_changes')}))
    # Numerical preservation is necessary but cannot override rejected design.
    return 1 if failures or not review['design_passed'] else 0


if __name__=='__main__':
    raise SystemExit(main())
