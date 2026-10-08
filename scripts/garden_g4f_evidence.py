"""G4f neutral candidate construction/search; no presentation or design moves.

Coordinates and lengths are metres; x/y horizontal, z up. Search spacing is
an authored numerical sampling choice, not a design rule. Diagnostic scene
subsets are authored copies, never edited Revit extracts.
"""
from copy import deepcopy
import argparse,json,math,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
from archpipe.concept import garden_g4e as E
from archpipe.concept.garden_render_review import (overhead_cover,garden_camera_findings,
    opening_frame_findings,subject_visibility_evidence,subject_frame_findings,subject_visibility_findings)
from scripts.villa_render_views import camera_proximity_violations,subject_points
OUT=ROOT/'out/garden-g4f'
BASE=ROOT/'out/garden-g4e/integrated-candidate-scene.json'


def save(name,data):
    (OUT/name).write_text(json.dumps(data,separators=(',',':'))+'\n')


def specimens():
    from archpipe.concept import villa_landscape as L
    data=json.loads((OUT/'before-specimens.json').read_text())
    for assembly in data['assemblies']:
        assembly['detail_full_specimen']=True
        assembly['meshes']=[dict(m,**E.clump(m['id'],m['species'],m['center'],m['root_z_m'],
                              L._plant_data(),bed=m['bed'],layer=m['planting_layer'])) for m in assembly['meshes']]
    data['materials'].update(E.materials())
    save('after-specimens.json',data)
    return data


def audit():
    import hashlib
    from archpipe.concept import villa_render as V
    from archpipe.villa_render_contract import validate_scene
    # Compare serialized scene values: Python tuples and JSON arrays are
    # different container types but identical exported geometry/data.
    scene=json.loads(json.dumps(V.build()))
    base=json.loads(BASE.read_text())
    old={m['id']:m for m in base['meshes']};new={m['id']:m for m in scene['meshes']}
    changed=[k for k in new if new[k]['faces']!=old[k]['faces']]
    preserved={k:scene[k]==base[k] for k in ('lights','sky','exposure','materials')}
    preserved['props_by_identity']={p['id']:p for p in scene['props']}=={p['id']:p for p in base['props']}
    positions={k:all(new[k][f]==old[k][f] for f in ('center','root_z_m','bed','planting_layer','spread_m')) for k in changed}
    digest=hashlib.sha256(json.dumps(scene['meshes'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    report=dict(geometry_sha256=digest,geometry_status='PENDING LEAD ACCEPTANCE',changed_faces=changed,
                preserved=preserved,plant_placement_preserved=positions,
                metrics={k:E.aspidistra_habit_metrics(new[k]) for k in changed},contract_findings=validate_scene(scene))
    save('source-audit.json',report)
    save('integrated-source-scene.json',scene)
    save('context-source-scene.json',neutral_subset(scene))
    print(json.dumps({k:v for k,v in report.items() if k!='metrics'}),flush=True)
    assert len(changed)==9 and all(new[k].get('species')=='Aspidistra elatior' for k in changed),changed
    assert all(preserved.values()),preserved
    assert all(positions.values()),positions
    assert not report['contract_findings'],report['contract_findings']


def candidate_scene():
    scene=json.loads(BASE.read_text());plants=json.loads((OUT/'after-specimens.json').read_text())
    replacement={m['id']:m for a in plants['assemblies'] for m in a['meshes']}
    scene['meshes']=[replacement.get(m['id'],m) for m in scene['meshes']]
    return scene


def camera_checks(view,scene):
    return dict(standing=garden_camera_findings(view,scene),frame=subject_frame_findings(view,scene),
                opening_frame=opening_frame_findings(view,scene),
                lens_clearance=camera_proximity_violations(view,scene,{}),
                visibility=subject_visibility_findings(view,scene),
                first_hits=subject_visibility_evidence(view,scene))


def search(scene):
    from shapely.geometry import Point,Polygon
    original=next(v for v in scene['views'] if v['id']=='v42-north-garden-evening')
    original=deepcopy(original)
    # G4f intent is the two directly uplit planting subjects; v39 owns
    # the swing seat. Full framing and all visibility guards still apply.
    original['subjects']=original['subjects'][:2]
    original['visibility_targets']=original['subjects'][:]
    points=np.asarray([p for subject in original['subjects'] for p in subject_points(subject,scene)])
    yard=Polygon(scene['garden_camera_domain']['yard_polygon_m']);cover=overhead_cover(scene,-3.)
    obstacles=[]
    for m in scene['meshes']:
        if m.get('group') not in ('furniture','dressing','landscape'):continue
        p=np.asarray([p for f in m['faces'] for p in f]);obstacles.append((m,p.min(axis=0),p.max(axis=0)))
    # Ray/standing shortlist retains every face intersecting the north-camera
    # volume. Final acceptance reruns unchanged guards on the complete scene.
    subset=[]
    for m in scene['meshes']:
        selected=[]
        for face in m['faces']:
            p=np.asarray(face)
            if np.all(p.min(axis=0)<[10,-19,5]) and np.all(p.max(axis=0)>[-5,-32,-4]):selected.append(face)
        if selected:subset.append(dict(m,faces=selected))
    ray_scene=dict(scene,meshes=subset)
    from archpipe.concept.render_support import _Surfaces,_triangles
    physical=_Surfaces(*_triangles([m for m in subset if m.get('group') in ('shell','ground','context') and not m.get('material','').startswith('glass')]))
    candidates=[];counts=dict(domain=0,framed=0,clear=0,fixture_clear=0,opening_clear=0)
    # Open-court standing points. West/south faces are the retained uplights'
    # side of the leaves; do not prioritise proximity to the rejected camera.
    for ground in (-3.,0.):
        cover=overhead_cover(scene,ground)
        for x in np.arange(-.10,7.36,.15):
            for y in np.arange(-29.65,-23.60,.15):
                if not yard.covers(Point(x,y)) or cover.covers(Point(x,y)):continue
                counts["domain"]+=1
                eye=np.array([x,y,ground+1.35]);delta=points-eye;mean=math.atan2(delta[:,1].mean(),delta[:,0].mean())
                bearings=(np.arctan2(delta[:,1],delta[:,0])-mean+math.pi)%math.tau-math.pi
                yaw=mean+(bearings.min()+bearings.max())/2;depth=delta[:,0]*math.cos(yaw)+delta[:,1]*math.sin(yaw)
                if depth.min()<=0:continue
                horizontal=(2/3)*(delta[:,0]*math.sin(yaw)-delta[:,1]*math.cos(yaw))/depth;vertical=(2/3)*delta[:,2]/depth
                if abs(horizontal).max()>.48 or np.ptp(vertical)>.63:continue
                counts["framed"]+=1
                view=deepcopy(original);view.pop('standing_room',None)
                view['standing_ground_m']=ground
                # Keep the lowest actual plant vertices just above the
                # frame bottom. Nearer ground hardware can then fall outside
                # the view without changing the plant or any fixture.
                view['camera'].update(position=eye.tolist(),target=(eye+np.array([3*math.cos(yaw),3*math.sin(yaw),0])).tolist(),shift_y=float(vertical.min()+1/3-.012))
                local=[m for m,lo,hi in obstacles if np.linalg.norm(np.maximum(np.maximum(lo-eye,eye-hi),0))<1.]
                if camera_proximity_violations(view,dict(meshes=local,props=scene['props']),{}):continue
                counts['clear']+=1
                if E.foreground_fixture_findings(view,ray_scene):continue
                counts['fixture_clear']+=1
                if opening_frame_findings(view,ray_scene):continue
                counts['opening_clear']+=1
                if not physical.meets(physical.up,x,y,ground):continue
                # Score front-side visibility and frame occupation before probes.
                palm=np.array([1.02,-24.65]);direction=eye[:2]-palm;direction/=np.linalg.norm(direction)
                score=-direction[0] * .7 + np.ptp(horizontal)*.3 + (1. if ground<0 else 0.)
                candidates.append(dict(view=view,score=float(score)))
        print('Search domain complete',ground,counts,len(candidates),flush=True)
    candidates.sort(key=lambda r:-r['score']);tested=[];valid=[]
    for candidate in candidates:
        evidence=subject_visibility_evidence(candidate['view'],ray_scene);candidate['first_hits']=evidence;tested.append(candidate)
        if all(r['visible']>=7 for r in evidence):
            valid.append(candidate)
            print('Valid camera',len(valid),candidate['view']['camera'],[r['visible'] for r in evidence],flush=True)
            if len(valid)>=5:break
    save('camera-search.json',dict(counts=counts,candidates=len(candidates),tested=tested,valid=valid))
    if not valid:raise ValueError('No valid open-court camera')
    save('candidate-v42.json',valid[0]['view'])
    return valid[0]['view']


def neutral_subset(scene):
    subset=[]
    for m in scene['meshes']:
        p=np.asarray([p for f in m['faces'] for p in f])
        if np.all(p.min(axis=0)<[10,-19,5]) and np.all(p.max(axis=0)>[-5,-32,-4]):subset.append(m)
    result=dict(scene,meshes=subset,props=[p for p in scene['props'] if p['position'][0]<10 and p['position'][1]<-19])
    result['neutral_preview_fill']=[dict(watts=1000.,size_m=3.,position_m=[.2,-26.5,-.1],target_m=[1.3,-25.2,-1.7])]
    return result


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--search',action='store_true');ap.add_argument('--specimens',action='store_true');ap.add_argument('--audit',action='store_true');args=ap.parse_args()
    if args.specimens:
        specimens();sys.exit(0)
    if args.audit:
        audit();sys.exit(0)
    OUT.mkdir(parents=True,exist_ok=True);scene=candidate_scene()
    if args.search:search(scene)
    else:
        view=json.loads((OUT/'candidate-v42.json').read_text());scene['views']=[view if v['id']==view['id'] else v for v in scene['views']]
        save('candidate-scene.json',scene);save('context-before-scene.json',neutral_subset(json.loads(BASE.read_text())))
        save('context-after-scene.json',neutral_subset(scene));save('candidate-v42-checks.json',camera_checks(view,scene))
