"""Reproduce west-court cover and architecture-only sun/sky measurements.

Metres in the scene frame; north bearing is the true bearing of scene +y.
Sky visibility is the unweighted fraction of 512 equal-solid-angle upper
hemisphere rays that clear opaque building geometry. Direct sun is sampled
at 10-minute interval midpoints over 24 hours; glass is excluded, plants and
furniture are not architectural enclosure. These are scene screens, not
weather-weighted light levels or site/nursery acceptance.
"""
import argparse,json,math
from datetime import datetime,timedelta
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon,box
from shapely.ops import unary_union
from archpipe import solar
from archpipe.concept import villa_landscape as L,render_support as S
from archpipe.concept.garden_render_review import overhead_cover


def enclosure(scene,rect,ground):
    meshes=[m for m in scene['meshes'] if m['group'] in ('shell','context') and scene['materials'][m['material']]['kind'] not in ('glass','translucent') and m.get('part_kind') not in ('window-frame','door-leaf')]
    triangles,_=S._triangles(meshes)
    cover=overhead_cover(scene,ground)
    return triangles,cover.intersection(box(*rect))


def clear_rays(triangles,point,directions):
    a=triangles[:,0];e1=triangles[:,1]-a;e2=triangles[:,2]-a
    delta=np.array(point)-a
    q=np.cross(delta,e1)
    out=[]
    for direction in directions:
        p=np.cross(direction,e2);det=np.einsum('ij,ij->i',e1,p)
        inv=np.divide(1,det,out=np.zeros_like(det),where=abs(det)>1e-10)
        u=np.einsum('ij,ij->i',delta,p)*inv;v=q@direction*inv;t=np.einsum('ij,ij->i',e2,q)*inv
        out.append(not np.any((abs(det)>1e-10)&(u>=-1e-9)&(v>=-1e-9)&(u+v<=1+1e-9)&(t>.001)))
    return out


def daylight(triangles,point,day,bearing):
    # Existing city-level source, not a surveyed plot location.
    moments=[datetime.fromisoformat(day+'T00:00:00+02:00')+timedelta(minutes=10*i+5) for i in range(144)]
    directions=[];up=[]
    for i,when in enumerate(moments):
        sun=solar.sun_position(when.astimezone(__import__('datetime').timezone.utc).replace(tzinfo=None),30.05,31)
        if sun.altitude<=0:continue
        alt=math.radians(sun.altitude);az=math.radians(sun.azimuth-bearing)
        up.append(i);directions.append([math.sin(az)*math.cos(alt),math.cos(az)*math.cos(alt),math.sin(alt)])
    visible=clear_rays(triangles,point,directions)
    sky=[]
    for i in range(512):
        z=(i+.5)/512;az=i*math.pi*(3-5**.5);r=math.sqrt(1-z*z)
        sky.append([r*math.cos(az),r*math.sin(az),z])
    sky_clear=clear_rays(triangles,point,sky)
    return dict(day=day,sun_hours=sum(visible)/6,sunlit_intervals=[moments[i].isoformat() for i,yes in zip(up,visible) if yes],sky_view_fraction=sum(sky_clear)/512,sky_ray_count=512,sun_step_minutes=10,point_m=point)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--scene',default='out/garden-g2f/before-scene.json');ap.add_argument('--output',default='out/garden-g2f/court-before.json');args=ap.parse_args()
    s=json.loads(Path(args.scene).read_text());rect=(-.373,-29.91566,3.617,-23.591)
    triangles,cover=enclosure(s,rect,L.GROUND)
    court=box(*rect);r=dict(client_name='North Garden',rect_m=rect,total_area_m2=court.area,covered_area_m2=cover.area,open_area_m2=court.difference(cover).area,cover_wkt=cover.wkt,excluded_roofed_strip_m=(-.373,-23.591,3.617,-20.351),furniture=[])
    balcony=box(-.123,-31.16032,3.617,-28.671)
    bed=box(*L.BEDS['west'])
    r['bed']=dict(area_m2=bed.area,balcony_covered_m2=bed.intersection(balcony).area,all_cover_m2=bed.intersection(cover).area)
    r['balcony_cover_m2']=court.intersection(balcony).area
    r['sun_screen']=dict(latitude_deg=30.05,longitude_deg=31.0,north_bearing_deg=s['north']['model_y_bearing_deg'],timezone='UTC+02:00',opaque_architecture_only=True,weather_weighted=False)
    for p in s['props']:
        if p['asset'] not in ('sf_egg_chair','outdoor_table_chair_set_01'):continue
        footprint=L._rect(p);center=[(footprint[0]+footprint[2])/2,(footprint[1]+footprint[3])/2,L.GROUND+.75]
        area=box(*footprint).area
        r['furniture'].append(dict(id=p['id'],position_m=p['position'],footprint_m=footprint,covered_footprint_m2=box(*footprint).intersection(cover).area,balcony_covered_footprint_m2=box(*footprint).intersection(balcony).area,footprint_area_m2=area,daylight=[daylight(triangles,center,date,s['north']['model_y_bearing_deg']) for date in ('2026-06-21','2026-10-15','2026-12-21')]))
    Path(args.output).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='furniture'},indent=2))
if __name__=='__main__':main()
