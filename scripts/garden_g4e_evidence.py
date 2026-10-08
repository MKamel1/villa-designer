"""Repeatable G4e appearance/camera evidence; local outputs, no presentation."""
from copy import deepcopy
import json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from archpipe.concept import garden_g4e as E,villa_landscape as L,garden_g4d as D
from archpipe.concept.garden_render_review import garden_camera_findings,subject_frame_findings,subject_visibility_evidence,opening_frame_findings
from scripts.villa_render_views import camera_proximity_violations,subject_points
OUT=Path('out/garden-g4e')


def save(name,value): (OUT/name).write_text(json.dumps(value,indent=2)+'\n')


def appearance_scene():
    scene=json.loads((OUT/'before-scene.json').read_text())
    scene['materials'].update(E.materials())
    for i,m in enumerate(scene['meshes']):
        if m.get('species') in ('Rhapis excelsa','Aspidistra elatior'):
            scene['meshes'][i]=E.clump(m['id'],m['species'],m['center'],m['root_z_m'],L._plant_data(),bed=m['bed'],layer=m['planting_layer'])
    return scene


def search(scene):
    before=next(v for v in scene['views'] if v['id']=='v41-north-garden-evening')
    points=np.asarray([p for subject in before['subjects'] for p in subject_points(subject,scene)])
    from archpipe.concept.garden_render_review import overhead_cover
    from shapely.geometry import Point,Polygon
    yard=Polygon(scene['garden_camera_domain']['yard_polygon_m']);cover=overhead_cover(scene,-3.)
    obstacles=[]
    for m in scene['meshes']:
        if m.get('group') not in ('furniture','dressing','landscape'):continue
        p=np.asarray([p for f in m['faces'] for p in f]);obstacles.append((m,p.min(axis=0),p.max(axis=0)))
    candidates=[];counts=dict(searched=0,framed=0,fixture_clear=0,physically_clear=0)
    for x in np.arange(0.,7.36,.15):
        for y in np.arange(-28.35,-23.6,.15):
            counts['searched']+=1
            lounge=scene['garden_camera_domain']['rooms']['lounge']['rect_m']
            in_lounge=lounge[0]+.15<x<lounge[2]-.15 and lounge[1]+.15<y<lounge[3]-.15
            if not in_lounge and (not yard.covers(Point(x,y)) or cover.covers(Point(x,y))):continue
            eye=np.array([x,y,-1.65]);delta=points-eye;mean=np.arctan2(delta[:,1].mean(),delta[:,0].mean());bearings=(np.arctan2(delta[:,1],delta[:,0])-mean+math.pi)%math.tau-math.pi
            yaw=mean+(bearings.min()+bearings.max())/2;depth=delta[:,0]*math.cos(yaw)+delta[:,1]*math.sin(yaw)
            if depth.min()<=0:continue
            horizontal=(2/3)*(delta[:,0]*math.sin(yaw)-delta[:,1]*math.cos(yaw))/depth;vertical=(2/3)*delta[:,2]/depth
            if abs(horizontal).max()>.48 or np.ptp(vertical)>.63:continue
            counts['framed']+=1
            view=deepcopy(before);view['id']='v42-north-garden-evening';view['aliases']=[before['id']]
            if in_lounge:view['standing_room']='lounge'
            view['camera'].update(position=eye.tolist(),target=(eye+np.array([3*math.cos(yaw),3*math.sin(yaw),0])).tolist(),shift_y=float((vertical.min()+vertical.max())/2))
            # Cache-screen irrelevant objects before exact clearance queries.
            local=[m for m,lo,hi in obstacles if np.linalg.norm(np.maximum(np.maximum(lo-eye,eye-hi),0))<1.]
            if camera_proximity_violations(view,dict(meshes=local,props=scene['props']),{}):continue
            counts['physically_clear']+=1
            if E.foreground_fixture_findings(view,scene):continue
            if opening_frame_findings(view,scene):continue
            counts['fixture_clear']+=1
            candidates.append(dict(view=view,score=float(np.linalg.norm(eye-np.asarray(before['camera']['position'])))))
    candidates.sort(key=lambda r:r['score']);tested=[]
    for candidate in candidates:
        rays=subject_visibility_evidence(candidate['view'],scene);candidate['visibility']=rays
        tested.append(candidate)
        if all(r['visible']>=7 for r in rays):
            save('camera-search.json',dict(counts=counts,tested=tested));save('candidate-view.json',candidate['view']);return candidate['view']
    save('camera-search.json',dict(counts=counts,tested=tested));raise ValueError('No valid fixed-design camera')


def companion_search(scene):
    before=next(v for v in scene['views'] if v['id']=='v37-north-garden-lounge')
    points=np.asarray([p for subject in before['subjects'] for p in subject_points(subject,scene)])
    candidates=[]
    obstacles=[]
    for m in scene['meshes']:
        if m.get('group') not in ('furniture','dressing','landscape'):continue
        p=np.asarray([p for f in m['faces'] for p in f]);obstacles.append((m,p.min(axis=0),p.max(axis=0)))
    room=scene['garden_camera_domain']['rooms']['lounge-nook']['rect_m']
    for x in np.arange(room[0]+.15,room[2]-.15,.10):
        for y in np.arange(room[1]+.15,room[3]-.15,.10):
            eye=np.array([x,y,-1.65]);delta=points-eye;yaw=math.atan2(delta[:,1].mean(),delta[:,0].mean())
            depth=delta[:,0]*math.cos(yaw)+delta[:,1]*math.sin(yaw)
            if depth.min()<=0:continue
            horizontal=(2/3)*(delta[:,0]*math.sin(yaw)-delta[:,1]*math.cos(yaw))/depth;vertical=(2/3)*delta[:,2]/depth
            if abs(horizontal).max()>.48 or np.ptp(vertical)>.63:continue
            view=deepcopy(before);view['standing_room']='lounge-nook';view['camera'].update(position=eye.tolist(),target=(eye+np.array([3*math.cos(yaw),3*math.sin(yaw),0])).tolist(),shift_y=float((vertical.min()+vertical.max())/2))
            local=[m for m,lo,hi in obstacles if np.linalg.norm(np.maximum(np.maximum(lo-eye,eye-hi),0))<1.]
            if camera_proximity_violations(view,dict(meshes=local,props=scene['props']),{}):continue
            if opening_frame_findings(view,scene):continue
            candidates.append(dict(view=view,distance=float(np.linalg.norm(eye-np.asarray(before['camera']['position'])))))
    candidates.sort(key=lambda r:r['distance']);tested=[]
    local_meshes=[]
    for m in scene['meshes']:
        p=np.asarray([p for f in m['faces'] for p in f]);lo=p.min(axis=0);hi=p.max(axis=0)
        if np.all(lo<np.array([7,-23,1])) and np.all(hi>np.array([-1,-28,-3.2])):local_meshes.append(m)
    ray_scene=dict(scene,meshes=local_meshes)
    for candidate in candidates:
        evidence=subject_visibility_evidence(candidate['view'],ray_scene);candidate['visibility']=evidence;tested.append(candidate)
        if len(tested)%10==0:print('Companion ray candidates checked',len(tested),flush=True)
        if all(r['visible']>=7 for r in evidence):
            save('companion-search.json',dict(tested=tested,candidates=len(candidates)));save('candidate-v37.json',candidate['view']);return candidate['view']
    save('companion-search.json',dict(tested=tested,candidates=len(candidates)));raise ValueError('No clear companion camera')


if __name__=='__main__':
    scene=appearance_scene();view=companion_search(scene)
    scene['views']=[view if v['id']==view['id'] else v for v in scene['views']]
    save('companion-candidate-scene.json',scene)
    print(json.dumps(dict(view=view['camera'],framing=subject_frame_findings(view,scene),standing=garden_camera_findings(view,scene)),indent=2))
