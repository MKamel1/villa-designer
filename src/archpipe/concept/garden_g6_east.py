"""G6 east-yard young shade planting and evidence-bound light checks.

Model x and y are horizontal coordinates and z is elevation, in metres.
The client east yard lies on model positive y. No botanical safety, nursery
performance or structural approval follows from procedural appearances.
"""
from __future__ import annotations

from copy import deepcopy
from math import sin, cos, pi
import json
import numpy as np

from .garden_sun import DATES, audit_plants, default_study

DWARF = "Pittosporum tobira 'Wheeler's Dwarf'"
MONA = "Plectranthus 'Mona Lavender'"
JASMINE = 'Trachelospermum jasminoides'


def quote_match_findings(plants, *, study=None, data=None):
    """Fail on contradicted light preferences for any ground planting zone.

    More than six midsummer hours is the tracked Royal Horticultural Society
    full-sun definition. A bright, sunny position is screened as a full-sun
    preference (explicit lead G6 decision), not a survival threshold. Winter
    under two hours for partial-shade species is disclosed, never fabricated
    as an acceptance. Indirect-light suitability without foliage rays remains
    unresolved and is not silently counted as a match.
    """
    from . import villa_landscape as L
    study = study or default_study()
    data = data or L._plant_data()
    screen = json.loads(L.PALETTE.read_text())['design_assumptions']['full_sun_screen']
    findings = []
    for plant in plants:
        if plant.get('zone') == 'top' or plant.get('part_kind') == 'climber-branch':
            continue  # Top-pot seasonal trial decisions are separately retained.
        row = data.get(plant.get('species'))
        if row is None:
            findings.append((plant['id'], 'missing light evidence'))
            continue
        light = row['light']; quote = str(light.get('value') or '').lower()
        if not quote or light['status'] in ('UNVERIFIED', 'NOT STATED'):
            findings.append((plant['id'], 'missing verified light quote'))
            continue
        center = plant.get('center')
        if center is None:
            rect = L._rect(plant); center = ((rect[0]+rect[2])/2, (rect[1]+rect[3])/2)
        hours = study.hours(*center, plant.get('root_z_m', L.GROUND), DATES[0])
        has_shade = any(s in quote for s in ('partial shade', 'part shade', 'heavy shade', 'deep shade', 'dappled', 'light shade'))
        flowering_preference = 'full sun for best flowering' in quote
        full_sun_only = 'full sun' in quote and not has_shade
        sunny_position = 'bright, sunny' in quote or 'bright sunny' in quote
        if (flowering_preference or full_sun_only or sunny_position) and len(hours) <= screen['hours']:
            findings.append((plant['id'], 'full-sun/bright-sunny flowering preference requires >%d midsummer hours; achieved %d (%s)' % (screen['hours'],len(hours),hours)))
        elif 'partial shade' in quote and not any(s in quote for s in ('heavy shade','deep shade','dappled')) and len(hours) < 2:
            findings.append((plant['id'], 'quoted partial shade starts at 2 direct hours; achieved %d midsummer hours' % len(hours)))
    return findings



def root_datum_findings(plants, tolerance_m=1e-6):
    """Authored above-soil plant geometry begins at its declared soil datum.

    tolerance_m is numerical coordinate tolerance in metres, not a botanical
    root-depth allowance. No underground root geometry is represented here.
    """
    out=[]
    for plant in plants:
        if 'root_z_m' not in plant or not plant.get('faces'):
            continue
        minimum=min(point[2] for face in plant['faces'] for point in face)
        if abs(minimum-plant['root_z_m'])>tolerance_m:
            out.append((plant['id'],'above-soil geometry base %.6f m differs from root datum %.6f m' % (minimum,plant['root_z_m'])))
    return out


def light_report(plants, *, study=None):
    """Live June/March/December rays plus honest botanical applicability."""
    from . import villa_landscape as L
    study = study or default_study()
    report = audit_plants(plants, study)
    findings = dict(quote_match_findings(plants, study=study))
    data = L._plant_data()
    for row in report:
        if row['id'] in findings:
            row['status'] = 'MISMATCH'; row['reason'] = findings[row['id']]
        elif 'heavy shade' in data[row['species']]['light']['value'].lower():
            row['status'] = 'SUPPORTED_BY_MIDSUMMER_SCREEN'
            row['reason'] = ''
            row['seasonal_limits'] = 'Source includes heavy shade; the direct-ray screen does not measure diffuse light, drainage or local nursery performance.'
        row['decision'] = 'lead decision 2026-10-06: corrected G5 actual-enclosure rays, part-shade replacement; year-round nursery suitability UNVERIFIED'
    return report


def _tube(a, b, radius=.007, sides=8):
    """Closed triangulated round stem with exact endpoint caps."""
    a,b = np.array(a,dtype=float),np.array(b,dtype=float)
    axis=b-a;axis/=np.linalg.norm(axis)
    helper=np.array([0.,0.,1.]) if abs(axis[2])<.9 else np.array([1.,0.,0.])
    u=np.cross(axis,helper);u/=np.linalg.norm(u);v=np.cross(axis,u)
    low,high=[[(point+radius*(u*cos(k*2*pi/sides)+v*sin(k*2*pi/sides))).tolist() for k in range(sides)] for point in (a,b)]
    faces=[low[::-1],high]+[[low[k],low[(k+1)%sides],high[(k+1)%sides],high[k]] for k in range(sides)]
    return [[f[0],f[k],f[k+1]] for f in faces for k in range(1,len(f)-1)]


def _leaf(root, sign, phase):
    """Closed oval leaf rising from a physically joined petiole tip."""
    root=np.asarray(root); across=np.array([float(sign),0.,.2]);across/=np.linalg.norm(across)
    side=np.array([-across[2],0.,across[0]]);normal=np.cross(across,side);center=root+across*.071
    ring=[(center+across*.071*cos(k*pi/6)+side*.024*sin(k*pi/6)).tolist() for k in range(12)]
    top=(center+normal*.003).tolist();bottom=(center-normal*.003).tolist()
    return [[top,ring[k],ring[(k+1)%12]] for k in range(12)]+[[bottom,ring[(k+1)%12],ring[k]] for k in range(12)]


def trellis(data=None):
    """Grounded timber with connected jasmine leaves; visible open members.

    ASSUMED young frame cover is measured from projected leaf polygon union;
    the denominator is the whole 1.5 by 2.2 metre frame rectangle.
    """
    from . import villa_landscape as L
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    data=data or L._plant_data();row=L.require_species(JASMINE,data)
    ground=L.GROUND; x0,x1,y0,y1=18.,19.5,-20.641,-20.601
    frame=[]
    for fraction in (0,.25,.5,.75,1):
        x=x0+(x1-x0)*fraction
        frame+=L._box(x-.012,y0,ground,x+.012,y1,ground+2.2)
    for z in (.18,1.05,2.17):frame+=L._box(x0,y0,ground+z,x1,y1,ground+z+.025)
    timber=L._mesh('trellis-east','furniture','trellis',frame,'ASSUMED retained open timber frame; lead decision 2026-10-06 jasmine replacement; anchors and weather durability UNVERIFIED',kind='trellis')
    stems=[];leaves=[];petioles=[];flowers=[];connections=[]
    for stem_index in range(3):
        base_x=x0+.21+stem_index*.54
        root=(base_x+.12*sin(stem_index),y1-.006,ground)
        # A horizontal basal cap sits exactly on soil; a sloped first cap
        # would project the tube radius below grade despite a grounded axis.
        points=[root,(root[0],root[1],ground+.025)]+[(base_x+.12*sin(k*.74+stem_index),y1-.006,ground+2.12*k/36) for k in range(1,37)]
        for a,b in zip(points,points[1:]):stems+=_tube(a,b,.006)
        for node,point in enumerate(points[1:-1]):
            for sign in (-1,1):
                tip=np.asarray(point)+np.array([sign*.020,-.030,.016])
                petioles+=_tube(point,tip,.0025)
                start=len(leaves);leaf=_leaf(tip,sign,node);leaves+=leaf
                connections.append(dict(stem_point=list(point),leaf_root=tip.tolist(),face_indices=list(range(start,start+len(leaf)))))
            if node%6==3:
                tip=np.asarray(point)+np.array([.025,-.080,.035])
                petioles+=_tube(point,tip,.0025)
                for petal in range(5):
                    angle=petal*2*pi/5;end=tip+np.array([.025*cos(angle),-.006,.025*sin(angle)])
                    flowers+=_tube(tip,end,.006,6)
    branch=L._mesh('climber-branches-east','dressing','trellis',stems,'ASSUMED connected young jasmine twining stems rooted in ground bed',kind='climber-branch')
    leaf_start=len(stems)+len(petioles)
    faces=stems+petioles+leaves+flowers
    coverage=unary_union([Polygon([(p[0],p[2]) for p in f]) for f in leaves if Polygon([(p[0],p[2]) for p in f]).area>1e-10]).area/(1.5*2.2)
    plant=L._mesh('climber-east','dressing','garden-foliage',faces,'ASSUMED young star jasmine; white star-shaped flowers; NC State lists Poisonous, details NOT STATED; client accepted 2026-10-06; nursery procurement and photographic likeness UNVERIFIED; '+row['source_url']['value'],kind='climber')
    plant.update(explicit_geometry=True,appearance_key='procedural-trellis',species=JASMINE,center=(18.75,y1-.006),spread_m=1.5,bed='east',planting_layer='climber',root_z_m=ground,leaf_face_indices=list(range(leaf_start,leaf_start+len(leaves))),leaf_connections=connections,stem_mesh=branch['id'],frame_id=timber['id'],coverage_fraction=float(coverage),coverage_denominator='whole timber frame rectangle 1.5m x 2.2m',face_materials=['trellis']*leaf_start+['garden-foliage']*len(leaves)+['g6-white-flower']*len(flowers))
    branch.update(species=JASMINE,appearance_key='procedural-trellis',root_z_m=ground,center=plant['center'],bed='east',planting_layer='climber')
    return [timber,branch,plant],[plant]


def materials():
    return {'g6-white-flower':dict(kind='principled',base_rgb=[.80,.78,.70],reflectance=.78,roughness=.65,basis='ASSUMED creamy-white jasmine bloom appearance; no measured optical claim')}


def build(data=None):
    """Return east meshes, plant records, soil rectangles and live light table.

    Integration replaces the old east-only bed/drifts/trellis; the north
    garden, top pots, artificial lawn and stepping paths remain authored by
    the main builder. No imported assets are introduced by this package.
    """
    from . import villa_landscape as L, garden_shade as SHADE, garden_g6 as SOUTH
    data=data or L._plant_data()
    record=json.loads(L.PALETTE.read_text())['design_assumptions']['east_yard_g6']
    meshes=[];plants=[];beds=[tuple(r) for r in record['soil_rects_m']]
    for i,rect in enumerate(beds):
        mesh=L._mesh('bed-east' if i==0 else 'soil-east-shade-strip','ground','garden-soil',L._quad(*rect,L.GROUND),'lead decision 2026-10-06: in-ground east shade bed; soil/drainage/roots over basement UNVERIFIED',kind='soil-bed',surface=True,occupied_side=(0,0,1))
        meshes.append(mesh)
    for drift in record['drifts']:
        name=drift['species'];layer=drift['layer']
        for i,center in enumerate(drift['centers_m']):
            identifier='east-%s-%02d'%(layer,i)
            if name== 'Fatsia japonica':
                local=deepcopy(data);size=local[name]['placement_assumptions']['procedural-east-clump']
                local[name]['placement_assumptions']['procedural-clump']=size
                plant=SHADE.clump(identifier,name,center,L.GROUND,local,bed='east',layer=layer)
                plant.update(appearance_key='procedural-east-clump',spread_m=.65)
            elif name=='Aspidistra elatior':
                plant=L._botanical_clump(identifier,name,center,L.GROUND,data,bed='east',layer=layer)
                plant['label']+='; shadier boundary strip; actual June2-3h direct rays, foliage-shade/indirect-light suitability UNRESOLVED'
            else:
                plant=SOUTH.clump(identifier,name,center,L.GROUND,data,bed='east',layer=layer)
                plant.pop('g6_element')  # South content policy does not name east-yard plants.
            meshes.append(plant);plants.append(plant)
    vines,vine_plants=trellis(data);meshes+=vines;plants+=vine_plants
    return meshes,plants,beds,light_report(plants)
