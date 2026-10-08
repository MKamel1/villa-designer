"""Bounded camera-only 24 mm terrace search on an exported physical scene.

All coordinates are metres; yaw is horizontal direction in radians. The
frame limits are fractions of sensor width. All physical vertices establish
projection extremes; every survivor uses actual surface proximity,
open-sky enclosure and first-hit sightlines before it is proposed.
"""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import numpy as np
from shapely.geometry import Point, Polygon, box

from archpipe.concept.garden_render_review import (
    overhead_cover, subject_visibility_evidence, garden_camera_findings)
from scripts.villa_render_views import subject_points, camera_proximity_violations

SUBJECTS=['landscape-g6-petrea-roof','landscape-g6-jasmine-roof',
          'landscape-g6-centrepiece','landscape-g6-seating']
TARGETS=['landscape-g6-centrepiece-dome','landscape-g6-seating-bench',
         'landscape-g6-seating-chair-0','landscape-g6-seating-chair-1',
         'landscape-g6-petrea-roof','landscape-g6-jasmine-roof']


def require_current_scene(scene, current_provenance):
    """Refuse unstamped or stale input before claiming an actual-scene search."""
    recorded=scene.get('provenance') or {}
    if not recorded.get('source_hash') or recorded['source_hash']!=current_provenance['source_hash']:
        raise ValueError('Camera search requires a current authoritative scene export')


def search(scene, eye_height_m=1.35):
    arrays=[]
    for subject in SUBJECTS:
        points=np.unique(np.asarray(subject_points(subject,scene)),axis=0)
        arrays.append(points)
    points=np.vstack(arrays)
    cover=overhead_cover(scene,-3.)
    yard=Polygon(scene['garden_camera_domain']['yard_polygon_m'])
    pergola=box(*scene['garden_g6']['assumptions']['pergola_rect_m'])
    # Cache immutable physical bounds once. An exact triangle query is needed
    # only when its conservative box lies within the existing 1 m limit.
    obstacles=[]
    for mesh in scene['meshes']:
        if mesh.get('group') not in ('furniture','dressing','landscape'):continue
        pts=np.asarray([p for face in mesh['faces'] for p in face])
        obstacles.append((mesh,pts.min(axis=0),pts.max(axis=0)))
    candidates=[];counts=dict(searched=0,open_sky=0,framed=0,clear=0)
    for x in np.arange(22.8,28.41,.10):
        for y in np.arange(-30.0,-20.69,.10):
            counts['searched']+=1
            position=Point(x,y)
            if not yard.covers(position) or cover.covers(position) or pergola.covers(position):continue
            counts['open_sky']+=1
            eye=np.array([x,y,scene['garden_camera_domain']['ground_m']+eye_height_m]);delta=points-eye
            target=math.atan2(delta[:,1].mean(),delta[:,0].mean())
            bearings=(np.arctan2(delta[:,1],delta[:,0])-target+math.pi)%(2*math.pi)-math.pi
            yaw=target+(bearings.max()+bearings.min())/2
            forward=delta[:,0]*math.cos(yaw)+delta[:,1]*math.sin(yaw)
            if forward.min()<=0:continue
            horizontal=(2/3)*(delta[:,0]*math.sin(yaw)-delta[:,1]*math.cos(yaw))/forward
            vertical=(2/3)*delta[:,2]/forward
            ratio=max(abs(horizontal).max()/.5,np.ptp(vertical)/(2/3))
            if ratio>.98:continue
            counts['framed']+=1
            view=dict(id='v41-south-garden-terrace',subjects=SUBJECTS,resolution=[1920,1280],
                      visibility_targets=TARGETS,
                      camera=dict(position=eye.tolist(),target=[x+5*math.cos(yaw),y+5*math.sin(yaw),float(eye[2])],
                                  lens_mm=24,sensor_mm=36,shift_y=float((vertical.max()+vertical.min())/2)))
            if camera_proximity_violations(view,dict(meshes=[],props=scene['props']),{}):continue
            nearby=[mesh for mesh,lo,hi in obstacles if np.linalg.norm(np.maximum(np.maximum(lo-eye,eye-hi),0))<1.]
            local=dict(meshes=nearby,props=scene['props'])
            if camera_proximity_violations(view,local,{}):continue
            counts['clear']+=1
            candidates.append(dict(view=view,framing_ratio=float(ratio),pergola_distance_m=position.distance(pergola)))
    candidates.sort(key=lambda row:(row['pergola_distance_m'],row['framing_ratio']))
    print('Projection and clearance search:',counts,'candidates',len(candidates),flush=True)
    checked=[]
    for candidate in candidates:
        evidence=subject_visibility_evidence(candidate['view'],scene)
        candidate['visibility']=evidence
        candidate['enclosure']=garden_camera_findings(candidate['view'],scene)
        checked.append(candidate)
        print('Sightlines',len(checked),candidate['view']['camera']['position'],
              [row['visible'] for row in evidence],flush=True)
        if not candidate['enclosure'] and all(row['visible']>=7 for row in evidence):
            return dict(counts=counts,checked=checked,selected=candidate)
    return dict(counts=counts,checked=checked,selected=None)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=Path('out/garden-g6b/scene.json'))
    parser.add_argument('--output',type=Path,default=Path('out/garden-g6b/terrace-camera-search.json'))
    parser.add_argument('--eye-height-m',type=float,default=1.35,
                        help='Assumed standing-eye height above the recorded yard soil, in metres.')
    args=parser.parse_args()
    from archpipe.concept.villa_render import source_provenance
    scene=json.loads(args.input.read_text())
    require_current_scene(scene,source_provenance())
    result=search(scene,args.eye_height_m)
    require_current_scene(scene,source_provenance())
    result['source_provenance']=scene['provenance']
    result['eye_height_m']=args.eye_height_m
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    if result['selected']:
        args.output.with_name('candidate-terrace-view.json').write_text(json.dumps(result['selected']['view'],indent=2)+'\n')
    print(json.dumps(dict(counts=result['counts'],selected=result['selected']),indent=2),flush=True)
    raise SystemExit(0 if result['selected'] else 1)
