"""Bounded 24 mm G6 camera search; geometry remains fixed.

All positions are model metres; x/y are plan, z height. The full actual
subject convex hull preserves perspective extrema at positive depth.
"""
import json
import math
from pathlib import Path
import numpy as np
from scripts.villa_render_views import subject_points, camera_proximity_violations
from archpipe.concept.garden_render_review import garden_camera_findings, overhead_cover
from shapely.geometry import Point,Polygon

OUT=Path('out/garden-g6')
SUBJECTS=['landscape-g6-petrea-roof','landscape-g6-jasmine-roof','landscape-g6-centrepiece','landscape-g6-seating','landscape-g6-loquat-plant']


def main():
    scene=json.loads((OUT/'scene.json').read_text())
    points=np.unique(np.array([p for s in SUBJECTS for p in subject_points(s,scene)]),axis=0)
    hull=points  # Use every actual vertex; no optional hull dependency.
    candidates=[];clear=0;best=100.
    yard=Polygon(scene['garden_camera_domain']['yard_polygon_m'])
    cover=overhead_cover(scene,-3.)
    positions=([(x,y) for x in np.arange(27.8,28.301,.1) for y in np.arange(-29.9,-27.6,.1)]+
               [(x,y) for x in np.arange(15.5,22.41,.2) for y in np.arange(-23.4,-20.60,.2)])
    for x,y in positions:
        eye=[round(x,3),round(y,3),-1.65]
        view=dict(id='v40-south-garden-pergola',subjects=SUBJECTS,resolution=[1920,1280],camera=dict(position=eye,lens_mm=24,sensor_mm=36,target=[24.5,-25,-1.65]))
        if not yard.covers(Point(x,y)) or cover.covers(Point(x,y)):continue
        clear+=1
        bearings=np.arctan2(hull[:,1]-y,hull[:,0]-x)
        target=np.arctan2(hull[:,1].mean()-y,hull[:,0].mean()-x)
        angles=(bearings-target+math.pi)%(2*math.pi)-math.pi
        yaw=target+(angles.min()+angles.max())/2
        forward=(hull[:,0]-x)*math.cos(yaw)+(hull[:,1]-y)*math.sin(yaw)
        if forward.min()<=0:continue
        horizontal=2/3*((hull[:,0]-x)*math.sin(yaw)-(hull[:,1]-y)*math.cos(yaw))/forward
        vertical=2/3*(hull[:,2]+1.65)/forward
        ratio=max(float(max(abs(horizontal))/.5),float((vertical.max()-vertical.min())/(2/3)))
        best=min(best,ratio)
        if ratio>1:continue
        if camera_proximity_violations(view,scene,{}):continue
        view['camera'].update(target=[x+5*math.cos(yaw),y+5*math.sin(yaw),-1.65],shift_y=float((vertical.min()+vertical.max())/2))
        view['framing_ratio']=ratio
        view['distance_to_pergola_plan_m']=math.hypot(max(22.75-x,0,x-25.75),max(-29.81-y,0,y+26.81))
        candidates.append(view)
    candidates.sort(key=lambda v:(v['distance_to_pergola_plan_m'],v['framing_ratio']))
    result=dict(points=len(positions),clear_points=clear,best_framing_ratio=best,actual_subject_vertices=len(points),convex_hull_vertices=len(hull),candidates=candidates)
    (OUT/'camera-search-final.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='candidates'}),flush=True)
    print(json.dumps(candidates[:3],indent=2),flush=True)


if __name__=='__main__':main()
