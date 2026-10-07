"""Hourly geometric direct sun on actual opaque scene enclosure, in model metres.

Hourly local-standard-clock samples above the horizon count one hour each.
This is a discrete scene screen, not weather-weighted horticultural illuminance.
Triangles come from building, context and ground; glass, plants and furniture
are excluded. Rays start 50 mm above the declared sampling surface.
"""
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from contextvars import ContextVar
active_study = ContextVar("garden_sun_study", default=None)
import hashlib
import numpy as np
from .. import solar, villa_env as E
from ..orientation import sun_direction, record
from .render_support import _triangles

DATES = ('2026-06-21','2026-03-20','2026-12-21')


class SunStudy:
    def __init__(self, scene):
        bearing=scene.get('north',{}).get('model_y_bearing_deg')
        if bearing is not None and bearing != record()['true_north']['model_y_bearing_deg']:
            raise ValueError('scene true north disagrees with site-orientation record')
        meshes=[m for m in scene['meshes'] if m.get('group') in ('shell','context','ground')
                and scene['materials'][m['material']]['kind'] not in ('glass','translucent')
                and not m['id'].startswith('landscape-')]
        self.triangles,_ = _triangles(meshes)
        if not len(self.triangles):raise ValueError('sun study requires actual enclosure geometry')
        self.geometry_sha256=hashlib.sha256(self.triangles.tobytes()).hexdigest()
        self.a=self.triangles[:,0]
        self.edge1=self.triangles[:,1]-self.a
        self.edge2=self.triangles[:,2]-self.a
        self._cache={}

    def clear(self, point, direction):
        # Two-sided Moller-Trumbore intersection; each wall can screen either face.
        delta=np.asarray(point)-self.a
        cross=np.cross(direction,self.edge2)
        determinant=np.einsum('ij,ij->i',self.edge1,cross)
        inverse=np.divide(1.,determinant,out=np.zeros_like(determinant),where=abs(determinant)>1e-10)
        u=np.einsum('ij,ij->i',delta,cross)*inverse
        q=np.cross(delta,self.edge1)
        v=np.einsum('ij,j->i',q,direction)*inverse
        distance=np.einsum('ij,ij->i',self.edge2,q)*inverse
        return not np.any((abs(determinant)>1e-10)&(u>=-1e-9)&(v>=-1e-9)&(u+v<=1+1e-9)&(distance>.001))

    def hours(self,x,y,ground=-3.,day=DATES[0]):
        key=(x,y,ground,day)
        if key not in self._cache:
            hours=[]
            for hour in range(24):
                when=datetime.fromisoformat(day).replace(tzinfo=timezone.utc)+timedelta(hours=hour-E.TIME_ZONE)
                sun=solar.sun_position(when,E.LATITUDE,E.LONGITUDE)
                if sun.altitude>0 and self.clear((x,y,ground+.05),sun_direction(sun.azimuth,sun.altitude)):
                    hours.append(hour)
            self._cache[key]=hours
        return list(self._cache[key])


@lru_cache(maxsize=1)
def default_study():
    """Standalone candidate uses the same spec-derived architecture as scene build."""
    from . import villa_daylight as VD, villa_r11 as R
    faces=VD.scene(R.design('D1')).faces
    meshes=[dict(id='enclosure-'+str(i),group='shell',material=f.material,faces=[f.points]) for i,f in enumerate(faces)]
    materials={f.material:dict(kind='glass' if f.material=='glass' else 'principled') for f in faces}
    return SunStudy(dict(meshes=meshes,materials=materials))


def audit_plants(plants, study):
    """Report every retained species against its tracked quote; never move plants.

    Numeric shade categories come only from the palette's checked quotes.
    Missing quotes and unmeasured canopy shade remain explicitly unresolved.
    """
    from . import villa_landscape as L
    rows=L._plant_data();out=[]
    for plant in plants:
        row=rows[plant['species']];light=row['light'];quote=str(light['value'] or '')
        center=plant.get('center')
        if center is None:
            rect=L._rect(plant);center=((rect[0]+rect[2])/2,(rect[1]+rect[3])/2)
        ground=float(plant.get('root_z_m',0. if plant.get('zone')=='top' else -3.))
        dates={date:study.hours(*center,ground,date) for date in DATES}
        june=len(dates[DATES[0]]);q=quote.lower();status='SUPPORTED_BY_MIDSUMMER_SCREEN';reason=''
        if not quote:status='UNVERIFIED';reason='No checked light quote; hours cannot establish suitability.'
        elif 'intolerant of direct sun' in q and max(map(len,dates.values()))>0:
            status='MISMATCH';reason='Quote excludes direct sunlight; enclosure-only rays reach this plant.'
        elif ((('full sun' in q and not any(s in q for s in ('partial shade','part shade','heavy shade','deep shade','dappled','light shade')))
               or 'full sun for best flowering' in q or 'bright, sunny' in q or 'bright sunny' in q) and june<=6):
            status='MISMATCH';reason='Full-sun preference/best flowering not met: midsummer requires more than six direct hours (tracked RHS definition).'
        elif ('bright, indirect' in q or 'shaded spot' in q) and june>0:
            status='UNRESOLVED';reason='Direct rays reach the sampling point; neighbouring foliage shade is excluded, so indirect-light suitability is unproven.'
        elif light['status']=='PARTIAL' and june<2:
            status='MISMATCH';reason='Deep shade screen; quoted dappled/partial shade does not establish deep-shade applicability. Retain recorded client trial risk.'
        elif light['status']=='PARTIAL':status='PARTIAL';reason=light.get('applicability','Quote applicability remains partial.')
        seasonal=''
        if quote and ('sun' in q or 'partial shade' in q) and not any(s in q for s in ('deep shade','heavy shade')) and len(dates[DATES[2]])<2:
            seasonal='Winter measures fewer than two direct hours; this screen cannot establish the quoted sun/partial-shade applicability in winter.'
        # A root near a building corner may be nearer a different house face.
        # Garden identity follows the recorded ground domains, not that face.
        zone='top'
        if ground<0:
            zone=L.geometry_zone(*center)
            rect=L.SOUTH
            if rect[0]<=center[0]<=rect[2] and rect[1]<=center[1]<=rect[3]:zone='south'
        out.append(dict(id=plant['id'],species=plant['species'],zone=zone,
                        center_m=list(center),ground_m=ground,quote=light['value'],quote_status=light['status'],
                        source_url=row['source_url']['value'],sunlit_local_standard_hours=dates,
                        status=status,reason=reason,seasonal_limits=seasonal))
    return out


def scene_findings(scene):
    """Fail closed on missing, stale or proxy-based solar evidence."""
    expected={p['id'] for p in scene['meshes']+scene.get('props',[]) if
              (p['id'].startswith('landscape-') or p.get('zone') in ('lower','top'))
              and p.get('species') and p.get('part_kind')!='climber-branch'}
    evidence=scene.get('garden_sun_evidence')
    # An interior-only generic render contract has no garden-sun requirement.
    # Actual landscape content or a declared garden domain requires evidence.
    if evidence is None:
        return ['scene has no recorded garden sun evidence'] if expected or 'garden_camera_domain' in scene or 'garden_zones' in scene else []
    study=SunStudy(scene);out=[]
    if evidence.get('geometry_sha256')!=study.geometry_sha256:out.append('sun evidence does not bind actual enclosure geometry')
    if evidence.get('dates')!=list(DATES) or evidence.get('step_hours')!=1 or evidence.get('timezone')!='UTC+02:00':out.append('sun evidence dates, hourly step or timezone disagree')
    rows=evidence.get('plants',[])
    if {r['id'] for r in rows}!=expected or len(rows)!=len(expected):out.append('sun evidence must cover every actual landscape plant exactly once')
    for row in rows:
        for day in DATES:
            if row.get('sunlit_local_standard_hours',{}).get(day)!=study.hours(*row['center_m'],row['ground_m'],day):out.append(row['id']+': sun evidence differs from actual scene ray casts')
    return out
