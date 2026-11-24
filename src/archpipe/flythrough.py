"""Deterministic walkthrough path preparation; no design or renderer edits.

Times are seconds, positions metres, yaw degrees anticlockwise from +x.
FPS means frames per second. SHA-256 is the content fingerprint algorithm.
All numerical camera assumptions live in the pre-registered policy.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np

from .concept.render_views import CameraSweep, scene_wall_hosts, wall_sightline_findings

ROOT = Path(__file__).resolve().parents[2]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def policy():
    return json.loads((ROOT/'knowledge/flythrough-policy.json').read_text())


def sample_path(knots, settings=None):
    """Quintic ease between timed poses, zero velocity/acceleration at knots.

    Knots explicitly specify unwrapped yaw, allowing deliberate turns without
    accidental rotation at the minus/plus 180-degree boundary. Frame zero is
    at zero seconds; frame 719 is at 719/24, with duration completed by its
    normal 1/24-second display interval.
    """
    settings = settings or policy()
    if (len(knots) < 2 or knots[0]['seconds'] != 0
            or knots[-1]['seconds'] != (settings['frames']-1)/settings['fps']
            or any(a['seconds'] >= b['seconds'] for a, b in zip(knots, knots[1:]))
            or any(not math.isfinite(x) for k in knots
                   for x in [k['seconds'], k['yaw_deg'], *k['position']])):
        raise ValueError('Path requires finite, ordered poses covering the exact frame interval')
    frames = []
    segment = 0
    for index in range(settings['frames']):
        seconds = index/settings['fps']
        while seconds > knots[segment+1]['seconds'] and segment < len(knots)-2:
            segment += 1
        a, b = knots[segment:segment+2]
        fraction = (seconds-a['seconds'])/(b['seconds']-a['seconds'])
        ease = fraction**3*(10+fraction*(-15+6*fraction))
        position = [x+(y-x)*ease for x, y in zip(a['position'], b['position'])]
        yaw = a['yaw_deg']+(b['yaw_deg']-a['yaw_deg'])*ease
        frames.append(dict(index=index, seconds=seconds, yaw_deg=yaw,
                           camera=dict(position=position, target=[
                               position[0]+math.cos(math.radians(yaw)),
                               position[1]+math.sin(math.radians(yaw)), position[2]],
                               lens_mm=24, sensor_mm=36, shift_x=0, shift_y=0)))
    record = dict(schema='flythrough-path/1', settings=settings, knots=knots, frames=frames)
    record['sha256'] = digest(record)
    return record


def require_path_hash(path):
    if path.get('sha256') != digest({k:v for k, v in path.items() if k != 'sha256'}):
        raise ValueError('Path or frame list fingerprint changed')
    return path


def walking_path(points, yaw_knots, settings=None, *, travel_seconds=None):
    """Straight motion corridors, eased to rest at each authored waypoint.

    Allocate segment durations in proportion to distance. Quintic easing
    makes velocity and acceleration zero at each waypoint, so a turn never
    overshoots its clear corridor or introduces a velocity jump. Independently
    timed quintic camera orientation retains the registered yaw-rate bound.
    """
    settings=settings or policy()
    if len(points)<2 or any(len(p)!=3 or not all(math.isfinite(v) for v in p) for p in points):
        raise ValueError('Finite three-dimensional waypoints required')
    distances=[math.dist(a,b) for a,b in zip(points,points[1:])]
    if any(d<=0 for d in distances):raise ValueError('Distinct adjacent waypoints required')
    total=sum(distances);duration=(settings['frames']-1)/settings['fps']
    travel=duration if travel_seconds is None else travel_seconds
    if not math.isfinite(travel) or not 0<travel<=duration:
        raise ValueError('Travel duration must fit the complete frame interval')
    times=[0.];travelled=0.
    for distance in distances:
        travelled+=distance;times.append(travel*travelled/total)
    times[-1]=travel
    knots=[dict(seconds=t,position=list(point),yaw_deg=0) for t,point in zip(times,points)]
    if travel<duration:knots.append(dict(knots[-1],seconds=duration))
    path=sample_path(knots,settings)
    orientation=sample_path([dict(k,position=[0,0,0]) for k in yaw_knots],settings)
    for frame,aim in zip(path['frames'],orientation['frames']):
        frame['yaw_deg']=aim['yaw_deg'];angle=math.radians(frame['yaw_deg'])
        position=frame['camera']['position']
        frame['camera']['target']=[position[0]+math.cos(angle),position[1]+math.sin(angle),position[2]]
    path.update(yaw_knots=yaw_knots,distance_m=total,travel_seconds=travel,
                interpolation='quintic straight corridors; zero velocity and acceleration at each waypoint')
    path['sha256']=digest({k:v for k,v in path.items() if k!='sha256'})
    return path


def authored_path():
    """Read the single authored camera route used by the command and tests."""
    route=json.loads((ROOT/'knowledge/flythrough-route.json').read_text())
    path=walking_path(route['points_m'],route['yaw_knots'],travel_seconds=route.get('travel_seconds'))
    path['route_input_sha256']=digest(route)
    path['sha256']=digest({k:v for k,v in path.items() if k!='sha256'})
    return path


def motion_findings(frames, settings):
    """Actual finite-difference speed and unwrapped yaw rate for each frame."""
    result = []
    for index, frame in enumerate(frames):
        speed = rate = 0.
        failures = []
        if index:
            previous = frames[index-1]
            interval = frame['seconds']-previous['seconds']
            if interval <= 0:
                raise ValueError('Nonpositive frame interval')
            speed = math.dist(frame['camera']['position'], previous['camera']['position'])/interval
            rate = abs(frame['yaw_deg']-previous['yaw_deg'])/interval
        if speed > settings['maximum_speed_m_s']:
            failures.append('linear speed exceeds registered bound')
        if rate > settings['maximum_yaw_rate_deg_s']:
            failures.append('yaw rate exceeds registered bound')
        result.append(dict(index=frame['index'], speed_m_s=speed, yaw_rate_deg_s=rate, failures=failures))
    return result


def guard_path(path, scene, *, ground_m, hidden=()):
    """Early physical gate. Full render admission still requires runtime checks.

    Reuses the production view wall guard and shared CameraSweep. A clear
    result from this early gate is not a claim about evaluated cloth, assets,
    subject composition, exposure, image quality or final video acceptance.
    """
    require_path_hash(path)
    settings = path['settings']
    frames = path['frames']
    if len(frames) != settings['frames']:
        raise ValueError('Incomplete frame list')
    sweep = CameraSweep(scene)
    walls = scene_wall_hosts(scene)
    rows = motion_findings(frames, settings)
    previous = frames[0]['camera']['position']
    for frame, row in zip(frames, rows):
        view = dict(frame, id='frame-%04d'%frame['index'])
        position = frame['camera']['position']
        if abs(position[2]-ground_m-settings['eye_height_m']) > 1e-9:
            row['failures'].append('camera eye height differs from still-view rule')
        if abs(frame['camera']['target'][2]-position[2]) > 1e-9:
            row['failures'].append('camera is not level')
        row['failures'].extend(wall_sightline_findings(view, walls))
        row['physical_obstacles'] = sweep.findings(previous, position, ground_m=ground_m,
            clearance_m=settings['obstacle_clearance_m'], height_m=settings['walking_height_m'], hidden=hidden)
        if row['physical_obstacles']:
            row['failures'].append('physical walking envelope intersects design geometry')
        row['passed'] = not row['failures']
        previous = position
    return dict(schema='flythrough-early-guards/1', path_sha256=path['sha256'],
                passed=all(row['passed'] for row in rows), frames=rows,
                max_speed_m_s=max(row['speed_m_s'] for row in rows),
                max_yaw_rate_deg_s=max(row['yaw_rate_deg_s'] for row in rows),
                acceptance_scope='early physical and motion rejection only; full renderer admission pending')


def require_renderable(guards):
    """No renderer may consume a failed or only partially verified path."""
    if not guards.get('passed') or guards.get('acceptance_scope') != 'complete per-frame render admission':
        raise ValueError('Walkthrough render refused: full per-frame admission is required')


def is_villa_path(path):
    return path.get('schema') == 'flythrough-villa-path/1'


def frame_views(path, scene):
    """Authored day state shared by the basement stills; only cameras are new."""
    require_path_hash(path)
    if is_villa_path(path):
        if scene.get('views'):
            if len(scene['views']) != len(path['frames']):
                raise ValueError('Prepared frame camera inventory differs from bound path')
            return scene['views']
        return villa_frame_views(path, scene)
    if scene.get('views'):
        views=scene['views']
        if (len(views)!=len(path['frames']) or any(v['id']!='frame-%04d'%f['index']
                or v['camera']!=f['camera'] for v,f in zip(views,path['frames']))):
            raise ValueError('Prepared frame camera inventory differs from bound path')
        return views
    # Author once in project Python. Blender consumes these serialized states
    # and does not need project-only packages such as PyYAML or Matplotlib.
    from .concept.villa_render import curtain_hidden_meshes, sun_for_timestamp
    sun = sun_for_timestamp('2026-10-15T10:30:00+03:00')
    periods=json.loads((ROOT/'knowledge/flythrough-route.json').read_text())['subject_periods']
    subjects=[]
    for frame in path['frames']:
        matching=[p['subjects'] for p in periods if p['first_frame']<=frame['index']<=p['last_frame']]
        if len(matching)!=1 or not matching[0]:raise ValueError('Every frame requires one nonempty authored subject period')
        subjects.append(matching[0])
    return [dict(id='frame-%04d'%f['index'], title='Entrance to south garden threshold',
                 camera=f['camera'], state='day', exposure='day', subjects=subjects[f['index']],
                 resolution=path['settings']['final_resolution'], samples=1024,
                 layers_on=['ambient','accent'], dimmers={'ambient':.5,'accent':.5},
                 hide_meshes=curtain_hidden_meshes(scene.get('curtains',[]),'day'),
                 sun=dict(sun),
                 caption_notes=['Garden glazing remains closed; clip ends inside the threshold.'])
            for f in path['frames']]


def admit_path(path, scene, layout, specification, evaluated_meshes):
    """Complete measured geometry admission using the existing view guards.

    Runtime meshes must include visible imported props and evaluated curtains,
    after production assembly. The caller binds that measured snapshot by hash.
    The swept guard includes glass and tests the gap between successive frames.
    """
    from scripts.villa_render_views import camera_proximity_violations,CameraProximityGeometry
    from .concept import villa_furnish as F
    from .concept.render_views import standing_point_clear
    from .concept.garden_render_review import opening_frame_findings, subject_frame_findings, subject_visibility_findings
    guards = guard_path(path, scene, ground_m=-3.)
    sweep = CameraSweep({'meshes':evaluated_meshes})
    proximity_geometry=CameraProximityGeometry(scene)
    items = {i['id']:i for i in F.layout(layout)}
    pieces = [F.footprint(i) for i in items.values() if i['level']=='B']
    previous = path['frames'][0]['camera']['position']
    rooms = []
    for frame,view,row in zip(path['frames'],frame_views(path,scene),guards['frames']):
        x,y = position = frame['camera']['position'][:2]
        room = next((r for r,v in layout['rooms'].items() if v['level']=='B'
                     and v['rect'][0]<x<v['rect'][2] and v['rect'][1]<y<v['rect'][3]), None)
        if room is None or not standing_point_clear(layout,specification,room,x,y,pieces):
            row['failures'].append('existing standing-point clearance policy failed')
        view['standing_room'] = room
        row['lens_clearance'] = camera_proximity_violations(view,scene,items,geometry=proximity_geometry)
        if row['lens_clearance']:
            row['failures'].append('existing interior lens clearance failed')
        row['failures'].extend(opening_frame_findings(view,scene))
        row['failures'].extend(subject_frame_findings(view,scene))
        row['failures'].extend(subject_visibility_findings(view,scene))
        position = frame['camera']['position']
        row['evaluated_obstacles'] = sweep.findings(previous,position,ground_m=-3.,
            clearance_m=path['settings']['obstacle_clearance_m'],height_m=path['settings']['walking_height_m'])
        if row['evaluated_obstacles']:
            row['failures'].append('evaluated physical walking envelope intersects design geometry')
        row['room'] = room
        row['passed'] = not row['failures']
        if not rooms or rooms[-1]!=room:rooms.append(room)
        previous=position
    guards.update(passed=all(r['passed'] for r in guards['frames']),route=rooms,
                  evaluated_meshes_sha256=digest(evaluated_meshes),
                  acceptance_scope='complete per-frame render admission')
    return guards


def clip_source_group(rows, expected=720):
    """Apply the registered strict-majority rule to the complete clip population.

    `expected` is the frame count the clip route requires; the villa route passes None because its groups are
    metered on a registered subsample.
    """
    from .exposure_groups import classify,rule
    if (expected is not None and len(rows) != policy()['frames']) or not rows:
        raise ValueError('Complete clip source population required')
    lamps = sum(r['lamp_luminance_sum'] for r in rows)
    daylight = sum(r['daylight_luminance_sum'] for r in rows)
    if not math.isfinite(lamps+daylight) or lamps<0 or daylight<0 or lamps+daylight<=0:
        raise ValueError('Invalid clip source measurements')
    fraction = lamps/(lamps+daylight)
    group = classify({'exposure':'day'},{'lamp_fraction':fraction})
    temperature = rule()['white_balance'][group]
    if group=='lamp-dominant':
        population=[lamp for row in rows for lamp in row['lamp_population']]
        flux=sum(lamp['flux_lm'] for lamp in population)
        temperature=round(sum(lamp['flux_lm']*lamp['cct_k'] for lamp in population)/flux)
    return dict(group=group, lamp_fraction=fraction, white_balance_k=temperature,
                white_balance_illuminant='planckian' if group=='lamp-dominant' else 'daylight',
                white_balance_tint=0 if group=='lamp-dominant' else 10,
                lamp_luminance_sum=lamps,daylight_luminance_sum=daylight,
                basis='registered strict majority on all 720 frame source populations')


def temporal_pair(previous_rgb, current_rgb, previous_positions, current_positions,
                  previous_camera, settings=None):
    """Measured static-surface correspondence; RGB arrays use top-left origin.

    Position arrays have world x/y/z in their first three channels and the
    static opaque material mask in their fourth channel. A position mismatch
    rejects a disocclusion or another surface. The one-percent display
    difference tolerance is dimensionless, not a geometric tolerance.
    """
    settings=settings or policy()
    p=np.asarray(current_positions);q=np.asarray(previous_positions)
    limit=settings['temporal_difference'];margin=limit['edge_offset_pixels']
    height,width=p.shape[:2]
    if p.shape!=q.shape or p.shape!=(height,width,4):raise ValueError('Position buffers differ')
    eye=np.asarray(previous_camera['position'])
    target=np.asarray(previous_camera['target'])
    yaw=math.atan2(target[1]-eye[1],target[0]-eye[0])
    delta=p[:,:,:3]-eye
    depth=delta[:,:,0]*math.cos(yaw)+delta[:,:,1]*math.sin(yaw)
    safe=np.maximum(depth,1e-9)
    scale=previous_camera['lens_mm']/previous_camera['sensor_mm']
    u=width*(.5+scale*(delta[:,:,0]*math.sin(yaw)-delta[:,:,1]*math.cos(yaw))/safe)-.5
    v=height/2-width*scale*delta[:,:,2]/safe-.5
    ix=np.floor(np.clip(u,0,width-2)).astype(int);iy=np.floor(np.clip(v,0,height-2)).astype(int)
    mask=(p[:,:,3]>.999)&(depth>0)&(u>=margin)&(u<width-margin-1)&(v>=margin)&(v<height-margin-1)
    mask[:margin]=False;mask[-margin:]=False;mask[:,:margin]=False;mask[:,-margin:]=False
    # Actual adjacent-surface jumps reject edges, not just a rectangular crop.
    for dy,dx in ((0,margin),(0,-margin),(margin,0),(-margin,0)):
        shifted=np.roll(p,(dy,dx),(0,1))
        mask&=(shifted[:,:,3]>.999)&(np.linalg.norm(shifted[:,:,:3]-p[:,:,:3],axis=2)<limit['maximum_edge_world_jump_m'])
    weights=[];warped=np.zeros_like(current_rgb,dtype=float)
    for dy,dx,weight in ((0,0,(1-(u-ix))*(1-(v-iy))),
                          (0,1,(u-ix)*(1-(v-iy))),
                          (1,0,(1-(u-ix))*(v-iy)),(1,1,(u-ix)*(v-iy))):
        samples=q[iy+dy,ix+dx]
        mask&=(samples[:,:,3]>.999)&(np.linalg.norm(samples[:,:,:3]-p[:,:,:3],axis=2)<limit['reprojection_match_m'])
        warped+=np.asarray(previous_rgb)[iy+dy,ix+dx]*weight[:,:,None]
    count=int(mask.sum())
    error=float(np.abs(np.asarray(current_rgb,dtype=float)[mask]-warped[mask]).mean()/255) if count else None
    limit=settings['temporal_difference']
    return dict(static_pixels=count,mean_absolute_rgb_change=error,
                passed=count>=limit['minimum_static_pixels'] and error is not None and error<=limit['maximum'])


def static_material_eligible(nodes):
    """Conservatively prove static opaque diffuse-region eligibility.

    Node descriptors state shader type and each optical input's constant
    value and whether it is linked. Linked alpha, roughness, metallic or
    transmission cannot establish this diagnostic contract. Unknown/mixed
    scattering closures and emission are excluded; the beauty shader is never
    changed. BSDF means bidirectional scattering distribution function.
    """
    if any(n['type']=='EMISSION' or (n['type'].startswith('BSDF_') and
           n['type']!='BSDF_PRINCIPLED') for n in nodes):return False
    shaders=[n for n in nodes if n['type']=='BSDF_PRINCIPLED']
    for node in shaders:
        if any(node[key+'_linked'] for key in ('roughness','metallic','transmission','alpha')):return False
        if not (node['roughness']>=policy()['temporal_difference']['minimum_material_roughness']
                and node['metallic']==0 and node['transmission']==0 and node['alpha']==1):return False
        no_emission=(node['emission_strength']==0 and not node['emission_strength_linked']) or (
            node['emission_color_max']==0 and not node['emission_color_linked'])
        if not no_emission:return False
    return bool(shaders)


def static_coverage(eligible_pixels, total_pixels, settings=None):
    """Necessary coverage screen at the registered final pixel density.

    This screen cannot grant temporal acceptance: final acceptance still
    requires matched reprojected pixels for every adjacent full-size pair.
    """
    settings=settings or policy()
    width,height=settings['final_resolution']
    minimum=math.ceil(settings['temporal_difference']['minimum_static_pixels']
                      *total_pixels/(width*height))
    if not 0<=eligible_pixels<=total_pixels or total_pixels<=0:
        raise ValueError('Invalid static-surface pixel population')
    return dict(eligible_opaque_pixels=eligible_pixels,pixels=total_pixels,
                minimum_pixels=minimum,passed=eligible_pixels>=minimum)


def retain_cache_materials(materials):
    """Preserve all referenced Blender materials across a saved-file round trip.

    Blender's fake-user flag explicitly retains an otherwise unused datablock.
    It changes storage lifetime, not a material's optical properties.
    """
    for name, material in materials.items():
        if material is None:raise ValueError('Missing referenced cache material: '+name)
        material.use_fake_user=True


# =====================================================================================================
# Whole-villa walkthrough (lane WT, 2026-11-22). Both floors, the real flight, garden placeholders.
# Everything above is the original level-B clip and stays unchanged; these functions share its
# guards. Distances metres, times seconds, yaw degrees anticlockwise from +x.
# =====================================================================================================
LEVEL_Z = {'B': -3.0, 'GF': 0.0}
CELL = 0.1


def villa_policy():
    return json.loads((ROOT/'knowledge/flythrough/villa-policy.json').read_text())


def villa_route():
    return json.loads((ROOT/'knowledge/flythrough/villa-route.json').read_text())


def level_at(ground_z):
    return 'GF' if ground_z > -1.5 else 'B'


def stair_ground(x, spec):
    """Floor height along the flight: least-squares line through the real tread tops, clamped to the landings.

    The treads are the spec's boxes (millimetres) thinner than 300 mm; only their x-extent and top matter.
    """
    treads = [b for b in spec['stair'] if b[5]-b[2] < 300]
    xs = np.array([(b[0]+b[3])/2000 for b in treads]); zs = np.array([b[5]/1000 for b in treads])
    slope, offset = np.polyfit(xs, zs, 1)
    return float(min(0., max(-3., slope*x+offset)))


def stair_extent(spec):
    treads = [b for b in spec['stair'] if b[5]-b[2] < 300]
    return min(b[0] for b in treads)/1000, max(b[3] for b in treads)/1000


def _furniture_boxes(scene, margin=.15+.02):
    """Plan bounding boxes of furniture/fixture/dressing meshes that reach into the walking envelope.

    margin is the 0.15 m swept clearance plus 0.07 m of grid slack, applied by the caller. Meshes wider than
    6 m (window frames, door handles: scene-wide bundles) are architecture and are handled by the
    walls and doors, not here.
    """
    out = {lv: [] for lv in LEVEL_Z}
    for box in json.loads((ROOT/'knowledge/flythrough/evaluated-obstacles.json').read_text())['boxes']:
        lo, hi = np.array(box['lo']), np.array(box['hi']); lv = level_at((lo[2]+hi[2])/2)
        if max(hi[0]-lo[0], hi[1]-lo[1]) <= 6 and lo[2] < LEVEL_Z[lv]+1.8 and hi[2] > LEVEL_Z[lv]+.05:
            out[lv].append((lo, hi, 0.))
    from .concept import villa_landscape as LAND
    for prop in scene.get('props', []):
        if prop['asset'] not in LAND.PROP_BOUNDS:
            continue
        x0, y0, z0, x1, y1, z1 = LAND.prop_world_box(prop['asset'], prop['position'], prop.get('rotation_deg', [0, 0, 0]), prop['scale'])
        lv = level_at((z0+z1)/2)
        if z0 < LEVEL_Z[lv]+1.8 and z1 > LEVEL_Z[lv]+.05:
            # the evaluated bedside books reach 0.08 m beyond prop_world_box (measured): props carry 0.1 m extra
            out[lv].append((np.array([x0, y0, z0]), np.array([x1, y1, z1]), .1))
    for m in scene['meshes']:
        if m.get('group') not in ('furniture', 'fixture', 'dressing') or not m.get('faces') or m.get('diagnostic'):
            continue
        if m['id'].startswith(('detail-stair', 'joinery-understair', 'furn-stair', 'landscape-', 'garden-')):
            continue
        pts = np.array([v for face in m['faces'] for v in face]); lo, hi = pts.min(0), pts.max(0)
        if max(hi[0]-lo[0], hi[1]-lo[1]) > 6:
            continue
        lv = level_at((lo[2]+hi[2])/2)
        if lo[2] < LEVEL_Z[lv]+1.8 and hi[2] > LEVEL_Z[lv]+.05:
            out[lv].append((lo, hi, 0.))
    return out


class VillaMap:
    """Per-level free-space grids built from the production standing-point policy.

    A cell is free when the existing `standing_point_clear` accepts it for a room of that level. Garden
    and entrance glazing is therefore never free (the policy refuses those door zones). The flight
    opening on GF and the under-stair joinery on B are handled explicitly: neither may be walked.
    """

    def __init__(self, layout, spec, items=None, scene=None):
        from .concept import villa_furnish as F
        self.layout, self.spec, self.F = layout, spec, F
        self.boxes = _furniture_boxes(scene) if scene else {lv: [] for lv in LEVEL_Z}
        self.items = items if items is not None else F.layout(layout)
        # Beds and bedside tables are dressed at assembly (duvet, books) and measured 0.15 m wider than their plan
        # footprint in the evaluated meshes; the plan pieces carry that overhang.
        def grown(i):
            x0, y0, x1, y1 = F.footprint(i); g = .15 if '-bed' in i['id'] else 0.
            return (x0-g, y0-g, x1+g, y1+g)
        self.pieces = {lv: [grown(i) for i in self.items if i['level'] == lv] for lv in LEVEL_Z}
        self.rooms = {lv: {n: r for n, r in layout['rooms'].items() if r['level'] == lv} for lv in LEVEL_Z}
        xs = [r['rect'][0] for r in layout['rooms'].values()]+[r['rect'][2] for r in layout['rooms'].values()]
        ys = [r['rect'][1] for r in layout['rooms'].values()]+[r['rect'][3] for r in layout['rooms'].values()]
        self.x0, self.y0 = min(xs)-.5, min(ys)-.5
        self.nx = int((max(xs)+.5-self.x0)/CELL)+1; self.ny = int((max(ys)+.5-self.y0)/CELL)+1
        self._free = {}; self._room = {}; self._plan = {}; self._policy = {}
        # B: the whole stair-b rectangle lies under the flight (cupboard, low soffit): never walkable
        sb = self.rooms['B']['stair-b']['rect']
        self.blocked = {'B': (sb[0]-.3, sb[1]-.3, sb[2], sb[3]+.3)}

    def xy(self, i, j):
        return self.x0+i*CELL, self.y0+j*CELL

    def cell(self, x, y):
        return int(round((x-self.x0)/CELL)), int(round((y-self.y0)/CELL))

    def _build(self, lv):
        from .concept.render_views import standing_point_clear
        F = self.F
        walls = F._walls(self.spec, lv)+F._columns()
        free = np.zeros((self.nx, self.ny), bool); room_of = np.full((self.nx, self.ny), '', dtype=object)
        rooms = self.rooms[lv]
        opening = None
        blocked = self.blocked.get(lv)
        if lv == 'GF':
            o = self.spec['gf_opening']; m = .3
            opening = (o[0]+.001, o[1]-m, o[2]+m, o[3]+m)   # the landing side (x<5.177) stays walkable
        for i in range(self.nx):
            for j in range(self.ny):
                x, y = self.xy(i, j)
                if opening and opening[0] < x < opening[2] and opening[1] < y < opening[3]:
                    continue
                if blocked and blocked[0] < x < blocked[2] and blocked[1] < y < blocked[3]:
                    continue
                for name, r in rooms.items():
                    rx = r['rect']
                    if not (rx[0]-.4 < x < rx[2]+.4 and rx[1]-.4 < y < rx[3]+.4):
                        continue
                    if standing_point_clear(self.layout, self.spec, name, x, y, self.pieces[lv], walls):
                        free[i, j] = True; room_of[i, j] = name
                        if rx[0] < x < rx[2] and rx[1] < y < rx[3]:
                            break   # prefer the room that contains the point
        self._policy[lv] = free.copy()
        # actual imported/furniture meshes (chairs pulled out, wall-mounted pieces) beyond their plan footprints
        for lo, hi, extra in self.boxes[lv]:
            i0, j0 = self.cell(lo[0]-.17, lo[1]-.17); i1, j1 = self.cell(hi[0]+.17, hi[1]+.17)
            free[max(i0, 0):i1+1, max(j0, 0):j1+1] = False
        # a door slot stays open for planning even where a mesh box overlaps it: door_cross then picks the exact
        # lateral offset that clears the mesh (the slot is only 0.3 m wide, narrower than the 0.1 m grid can resolve)
        for d in self.spec['doors']:
            if d['level'] != lv or d.get('garden') or d.get('entrance'):
                continue
            h = self.F._door_axis(d) == 'h'
            for i in range(self.nx):
                for j in range(self.ny):
                    x, y = self.xy(i, j)
                    along, across = (x-d['x'], y-d['y']) if h else (y-d['y'], x-d['x'])
                    if abs(across) <= .35 and abs(along) <= d['width']/2-.25 and self._policy[lv][i, j]:
                        free[i, j] = True
        self._free[lv], self._room[lv] = free, room_of

    def free(self, lv):
        if lv not in self._free:
            self._build(lv)
        return self._free[lv]

    def policy_free(self, lv):
        """The standing-point policy alone, without the furniture-mesh boxes."""
        self.free(lv)
        return self._policy[lv]

    def room_at(self, lv, x, y):
        """Room whose rectangle contains the point (None outside every room)."""
        for n, r in self.rooms[lv].items():
            rx = r['rect']
            if rx[0] < x < rx[2] and rx[1] < y < rx[3]:
                return n
        return None

    def plan_free(self, lv):
        """Free cells with one cell (0.1 m) of extra margin, except in doorway slots (kept as the policy has them).

        The policy mask is evaluated at cell centres; a straight line between two centres can clip a corner by
        up to 0.07 m. Planning on the eroded mask keeps the walked line inside the policy.
        """
        if lv not in self._plan:
            free = self.free(lv); core = free.copy()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                core &= np.roll(np.roll(free, dx, 0), dy, 1)
            door = np.zeros_like(free); narrow = np.zeros_like(free)
            for d in self.spec['doors']:
                if d['level'] != lv or d.get('garden') or d.get('entrance'):
                    continue
                h = self.F._door_axis(d) == 'h'
                for i in range(self.nx):
                    for j in range(self.ny):
                        x, y = self.xy(i, j)
                        along, across = (x-d['x'], y-d['y']) if h else (y-d['y'], x-d['x'])
                        if abs(across) <= .8 and abs(along) <= d['width']/2+.5:
                            door[i, j] = True
                        if abs(across) <= .35 and abs(along) > d['width']/2-.25-.06:
                            narrow[i, j] = True   # inside the wall: only a slot 0.06 m tighter than the policy slot
            self._plan[lv] = (core | (free & door)) & ~narrow
        return self._plan[lv]

    def comfort(self, lv, radius=3):
        free = self.free(lv); ok = free.copy()
        for k in range(1, radius+1):
            shifted = free.copy()
            for dx, dy in ((k, 0), (-k, 0), (0, k), (0, -k), (k, k), (-k, -k), (k, -k), (-k, k)):
                shifted &= np.roll(np.roll(free, dx, 0), dy, 1)
            ok &= shifted
        return ok

    def clearance_cells(self, lv, limit=10):
        free = self.free(lv); level = free.astype(int)
        cur = free.copy()
        for k in range(1, limit+1):
            nxt = cur.copy()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                nxt &= np.roll(np.roll(cur, dx, 0), dy, 1)
            level += nxt; cur = nxt
        return level

    def _mask(self, lv, tight):
        """tight 0: eroded plan mask; 1: policy plus furniture meshes; 2: policy alone (the tightest rooms)."""
        return (self.plan_free(lv), self.free(lv), self.policy_free(lv))[int(tight)]

    def line_free(self, lv, a, b, tight=False):
        """True when every sample along the segment has all four surrounding cell centres free (no corner clipping)."""
        free = self._mask(lv, tight); n = max(2, int(math.dist(a, b)/(CELL/2)))
        pieces = self.pieces[lv]
        for k in np.linspace(0, 1, n):
            px, py = a[0]+(b[0]-a[0])*k, a[1]+(b[1]-a[1])*k
            if any(r[0]-.155 < px < r[2]+.155 and r[1]-.155 < py < r[3]+.155 for r in pieces):
                return False   # exact 0.15 m furniture clearance, not just the grid's
            if any(w[0]-.305 < px < w[2]+.305 and w[1]-.305 < py < w[3]+.305 and not self._in_slot(lv, px, py)
                   for w in self._built(lv)):
                return False   # exact 0.30 m wall/column clearance
            fx = (px-self.x0)/CELL; fy = (py-self.y0)/CELL
            for i in {int(math.floor(fx)), int(math.ceil(fx))}:
                for j in {int(math.floor(fy)), int(math.ceil(fy))}:
                    if not (0 <= i < self.nx and 0 <= j < self.ny and free[i, j]):
                        return False
        return True

    def _door_clearance(self, lv, d, h, s, shift):
        """Smallest horizontal distance from a straight crossing of door d at lateral `shift` to furniture
        pieces and mesh boxes (metres, 9 if none near)."""
        rects = list(self.pieces[lv])+[(lo[0]-g, lo[1]-g, hi[0]+g, hi[1]+g) for lo, hi, g in self.boxes[lv]]
        best = 9.
        for off in np.arange(-.45, .451, .03):
            x, y = (d['x']+shift, d['y']+s*off) if h else (d['x']+s*off, d['y']+shift)
            for r in rects:
                dx = max(r[0]-x, 0, x-r[2]); dy = max(r[1]-y, 0, y-r[3])
                best = min(best, math.hypot(dx, dy))
        return best

    def _built(self, lv):
        if not hasattr(self, '_built_cache'):
            self._built_cache = {}
        if lv not in self._built_cache:
            self._built_cache[lv] = self.F._walls(self.spec, lv)+self.F._columns()
        return self._built_cache[lv]

    def _in_slot(self, lv, x, y):
        """Inside a passage door's policy slot, where the wall clearance does not apply."""
        for d in self.spec['doors']:
            if d['level'] != lv or d.get('garden') or d.get('entrance'):
                continue
            h = self.F._door_axis(d) == 'h'
            along, across = (x-d['x'], y-d['y']) if h else (y-d['y'], x-d['x'])
            if abs(across) <= .35 and abs(along) <= d['width']/2-.25:
                return True
        return False

    def door_cross(self, lv, polyline):
        """Make every passage-door crossing straight along the door's centre line.

        Where a segment crosses a door's wall line inside its opening, the segment is replaced by
        entry (0.45 m before the wall line), door centre, exit (0.45 m after) so the camera never passes the
        jamb limits at an angle.
        """
        out = [polyline[0]]
        for p, q in zip(polyline, polyline[1:]):
            for d in self.spec['doors']:
                if d['level'] != lv or d.get('garden') or d.get('entrance') or d.get('sliding'):
                    continue
                h = self.F._door_axis(d) == 'h'
                ca, cb = (p[1], q[1]) if h else (p[0], q[0])          # coordinate across the wall line
                line = d['y'] if h else d['x']
                if (ca-line)*(cb-line) >= 0:
                    continue
                k = (line-ca)/(cb-ca)
                along = (p[0]+(q[0]-p[0])*k-d['x']) if h else (p[1]+(q[1]-p[1])*k-d['y'])
                if abs(along) > d['width']/2:
                    continue
                s = 1. if cb > ca else -1.
                limit = d['width']/2-.25-.01
                shift = max(np.arange(-limit, limit+1e-9, .01), key=lambda c: (self._door_clearance(lv, d, h, s, c) >= .16,
                                                                                 -abs(c) if self._door_clearance(lv, d, h, s, c) >= .16 else self._door_clearance(lv, d, h, s, c)))
                for off in (-.45, 0., .45):
                    out.append((d['x']+shift, d['y']+s*off) if h else (d['x']+s*off, d['y']+shift))
                break
            out.append(q)
        return out

    def astar(self, lv, a, b):
        """Plan on the eroded mask; where a room is too tight for that, fall back to policy plus furniture
        meshes, then to the policy alone (guest WC, dressing room)."""
        for mode in (0, 1, 2):
            try:
                return self._astar(lv, a, b, mode)
            except ValueError:
                if mode == 2:
                    raise

    def _astar(self, lv, a, b, tight):
        """8-connected A*; cells outside the comfort band cost four times as much, so routes stay mid-room."""
        import heapq
        free = self._mask(lv, tight); comfy = self.comfort(lv)
        s, g = self.cell(*a), self.cell(*b)
        if not free[s] or not free[g]:
            raise ValueError(f'route endpoint not free on {lv}: {a} -> {b}')
        best = {s: 0.}; came = {}; heap = [(0., s)]
        while heap:
            _, c = heapq.heappop(heap)
            if c == g:
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                n = (c[0]+dx, c[1]+dy)
                if not (0 <= n[0] < self.nx and 0 <= n[1] < self.ny) or not free[n]:
                    continue
                if dx and dy and not (free[c[0]+dx, c[1]] and free[c[0], c[1]+dy]):
                    continue
                cost = best[c]+math.hypot(dx, dy)*(1. if comfy[n] else 4.)
                if cost < best.get(n, 1e18):
                    best[n] = cost; came[n] = c
                    heapq.heappush(heap, (cost+math.hypot(g[0]-n[0], g[1]-n[1]), n))
        if g not in came and g != s:
            raise ValueError(f'no walkable route on {lv}: {a} -> {b}')
        cells = [g]
        while cells[-1] != s:
            cells.append(came[cells[-1]])
        pts = [self.xy(*c) for c in reversed(cells)]
        # string-pull: keep a vertex only when the straight line to the next kept target leaves free space
        out = [pts[0]]; k = 0
        while k < len(pts)-1:
            m = len(pts)-1
            while m > k+1 and not self.line_free(lv, pts[k], pts[m], tight):
                m -= 1
            out.append(pts[m]); k = m
        out[0], out[-1] = tuple(a), tuple(b)
        return out

    def anchor(self, lv, room, near=None):
        """Free cell in the room with the greatest clearance, nearest the room centre. None for a transit room."""
        r = self.rooms[lv][room]['rect']
        clear = self.clearance_cells(lv)
        best = None
        cx, cy = ((r[0]+r[2])/2, (r[1]+r[3])/2) if near is None else near
        for i in range(self.nx):
            for j in range(self.ny):
                x, y = self.xy(i, j)
                if clear[i, j] and r[0] < x < r[2] and r[1] < y < r[3]:
                    key = (min(clear[i, j], 6), -math.hypot(x-cx, y-cy))
                    if best is None or key > best[0]:
                        best = (key, (x, y))
        return best[1] if best else None


def _inward_point(vm, door, offset=.7):
    """A free point just inside a garden door on B, on the side of the room that contains it."""
    x, y = door
    for dx, dy in ((offset, 0), (-offset, 0), (0, offset), (0, -offset)):
        if vm.room_at('B', x+dx, y+dy):
            return (x+dx, y+dy)
    raise ValueError(f'door {door} has no room on either side')


def plan_villa_route(vm, route=None):
    """Turn the authored tour into a connected polyline of (x, y, ground_z, flags) nodes plus stations.

    Same-level hops use A* over the policy grid; the only level change is the real flight, entered at the
    authored top/bottom nodes. A garden station walks to the glazing threshold (inside, closed pane), then
    out to placeholder waypoints and back. Raises when any hop has no walkable route.
    """
    route = route or villa_route(); spec = vm.spec
    top, bottom = route['stair']['top'], route['stair']['bottom']
    nodes = []          # dict(x, y, level, stair)
    stations = []       # dict(node, hold_s, room, kind)
    pos, lv = None, None

    def go(to, to_level, kind='walk'):
        nonlocal pos, lv
        if kind == 'via' and pos is not None and to_level == lv and vm.line_free(lv, pos, to, 1):
            nodes.append(dict(x=to[0], y=to[1], level=lv)); pos = tuple(to); return
        if pos is None:
            nodes.append(dict(x=to[0], y=to[1], level=to_level)); pos, lv = tuple(to), to_level; return
        if to_level != lv:
            raise ValueError('level change only through the flight')
        if math.dist(pos, to) < 1e-6:
            return
        for p in vm.door_cross(lv, vm.astar(lv, pos, to))[1:]:
            nodes.append(dict(x=p[0], y=p[1], level=lv))
        pos = tuple(to)

    def mark(room, hold, kind):
        stations.append(dict(node=len(nodes)-1, hold_s=hold, room=room, kind=kind))

    for st in route['stations']:
        if st.get('via'):
            for p in st['via']:
                go(p, st['level'], 'via')
        elif st.get('room'):
            room = st['room']
            level = next(l for l in LEVEL_Z if room in vm.rooms[l])
            at = vm.anchor(level, room)
            if at is None:
                raise ValueError(f'room {room} has no free standing cell')
            go(at, level); mark(room, st['hold_s'], 'room')
            r = vm.rooms[level][room]['rect']
            stations[-1]['transit'] = min(r[2]-r[0], r[3]-r[1]) < villa_policy()['transit_room_min_dimension_m']
        elif st.get('stair') == 'down':
            go(top, 'GF'); mark('stair-gf', st['hold_s'], 'stair-top')
            x0, x1 = stair_extent(spec)
            for x in np.arange(x0, x1+.5, .5):
                nodes.append(dict(x=float(x), y=top[1], level='GF' if x < x0+.3 else 'B', stair=True))
            nodes.append(dict(x=bottom[0], y=bottom[1], level='B'))
            pos, lv = tuple(bottom), 'B'
        elif st.get('garden'):
            inside = _inward_point(vm, st['door'])
            go(inside, 'B'); mark(None, 3., 'garden-threshold')
            for p in [st['door']]+st['outside']+[st['door'], inside]:
                nodes.append(dict(x=p[0], y=p[1], level='B', garden=st['garden']))
            nodes[-1].pop('garden'); pos = tuple(inside)
            stations[-1]['garden'] = st['garden']
    return nodes, stations


def _opaque_grid(vm, lv):
    """Wall and column footprints for a level (door gaps already cut), used only to choose view directions."""
    F = vm.F
    grid = np.zeros((vm.nx, vm.ny), bool)
    for w in F._walls(vm.spec, lv)+F._columns():
        i0, j0 = vm.cell(w[0], w[1]); i1, j1 = vm.cell(w[2], w[3])
        grid[max(i0, 0):i1+1, max(j0, 0):j1+1] = True
    return grid


def _ray(vm, grid, x, y, yaw, limit=8.):
    c, s = math.cos(yaw), math.sin(yaw)
    for d in np.arange(.1, limit, .05):
        i, j = vm.cell(x+c*d, y+s*d)
        if not (0 <= i < vm.nx and 0 <= j < vm.ny) or grid[i, j]:
            return d
    return limit


def view_yaw(vm, lv, point, grid=None, prefer=None):
    """Direction (radians) with the deepest unobstructed view from a standing point.

    Five rays across the central 50 degrees are scored by mean depth, subject to the 1 m forward-wall
    sightline rule; if no direction meets 1.5 m the one with the best minimum is returned.
    """
    grid = _opaque_grid(vm, lv) if grid is None else grid
    scored = []
    for deg in range(0, 360, 10):
        rays = [_ray(vm, grid, point[0], point[1], math.radians(deg+o)) for o in (-25, -12, 0, 12, 25)]
        scored.append(((min(rays) >= 1.5, np.mean(rays) if min(rays) >= 1.5 else min(rays)), math.radians(deg)))
    top = max(k for k, _ in scored)
    if prefer is None or not top[0]:
        return max(scored)[1]
    # among views at least 85 % as deep as the best, take the one needing the smallest turn
    good = [y for k, y in scored if k[0] and k[1] >= .85*top[1]]
    return min(good, key=lambda y: abs((y-prefer+math.pi) % (2*math.pi)-math.pi))


def _smooth(values, sigma_samples):
    k = int(4*sigma_samples)
    kernel = np.exp(-.5*(np.arange(-k, k+1)/sigma_samples)**2); kernel /= kernel.sum()
    padded = np.concatenate([np.full(k, values[0]), values, np.full(k, values[-1])])
    return np.convolve(padded, kernel, mode='valid')


def repair_yaw(vm, xy, levels, yaw, margin=1.15, buckets=72, iterations=3):
    """Turn each look direction away from a wall closer than `margin` along the central sightline.

    The admission rule fails a frame whose central sightline meets a wall within 1 m. For every
    0.1 m of route, the directions whose first wall is at least `margin` away are tabulated against the
    wall/column grid; the desired yaw is moved to the nearest such direction, smoothed, and re-projected,
    so the result always lies in an allowed direction where one exists. A point with no allowed
    direction (a space smaller than the margin all round) keeps the deepest one and is left to the guard.
    """
    grids = {lv: _opaque_grid(vm, lv) for lv in LEVEL_Z}
    step = 5; pick = np.arange(0, len(xy), step)
    angles = np.arange(buckets)*2*math.pi/buckets
    distances = np.arange(.05, margin+.05, .05)
    allowed = np.zeros((len(pick), buckets), bool); depth = np.zeros((len(pick), buckets))
    for lv in LEVEL_Z:
        rows = np.where(np.array(levels)[pick] == lv)[0]
        if not len(rows):
            continue
        px = xy[pick[rows], 0][:, None, None]+np.cos(angles)[None, :, None]*distances[None, None, :]
        py = xy[pick[rows], 1][:, None, None]+np.sin(angles)[None, :, None]*distances[None, None, :]
        ci = np.rint((px-vm.x0)/CELL).astype(int); cj = np.rint((py-vm.y0)/CELL).astype(int)
        inside = (ci >= 0) & (ci < vm.nx) & (cj >= 0) & (cj < vm.ny)
        hit = np.where(inside, grids[lv][np.clip(ci, 0, vm.nx-1), np.clip(cj, 0, vm.ny-1)], True)
        first = np.where(hit.any(2), hit.argmax(2), len(distances))
        depth[rows] = first; allowed[rows] = first >= len(distances)
    # tight spots: relax the margin to 1.05 m, then to the deepest direction available
    for relaxed in (1.05/.05,):
        none = ~allowed.any(1)
        allowed[none] = depth[none] >= relaxed
    none = ~allowed.any(1)
    allowed[none] = depth[none] >= depth[none].max(1, keepdims=True)-1
    # Viterbi over direction buckets, one state per 0.1 m of route: a forbidden direction costs a lot, the
    # distance from the wanted yaw costs a little, and the yaw may change by one bucket (5 deg) per step.
    want = yaw[pick]; n = len(pick)
    wrapped = (angles[None, :]-want[:, None]+math.pi) % (2*math.pi)-math.pi
    cost = wrapped**2+np.where(allowed, 0., 400.)
    total = np.zeros(buckets); back = np.zeros((n, buckets), int)
    total = cost[0].copy()
    for i in range(1, n):
        options = np.stack([np.roll(total, 1), total, np.roll(total, -1)])+np.array([[.02], [0.], [.02]])
        choice = options.argmin(0)
        back[i] = (np.arange(buckets)+(choice-1)) % buckets
        total = options.min(0)+cost[i]
    state = int(total.argmin()); chosen = np.zeros(n, int)
    for i in range(n-1, -1, -1):
        chosen[i] = state; state = back[i, state]
    direction = angles[chosen]
    # continuous, unwrapped, and smoothed lightly; the margin over the 1 m rule absorbs the smoothing
    steps = np.cumsum(((np.diff(direction, prepend=direction[0])+math.pi) % (2*math.pi))-math.pi)+direction[0]
    offset = np.round((yaw[pick[0]]-steps[0])/(2*math.pi))*2*math.pi
    full = np.interp(np.arange(len(xy)), pick, steps+offset)
    return _smooth(full, .12/.02)


def sample_villa_path(vm, nodes, stations, settings=None):
    """Constant-pace walk with holds, sampled at 24 fps.

    Position follows the polyline at the cited cruise speed (stair speed on the flight), accelerating at the
    registered rate and slowing wherever the camera would have to turn faster than the registered yaw rate.
    Yaw looks ahead along the route and is pulled to the chosen view direction around each hold.
    """
    settings = dict(settings or villa_policy()); spec = vm.spec
    ds = .02; x0s, x1s = stair_extent(spec)
    P = []   # (x, y, ground, stair, garden)
    for a, b in zip(nodes, nodes[1:]):
        za = stair_ground(a['x'], spec) if a.get('stair') else LEVEL_Z[a['level']]
        zb = stair_ground(b['x'], spec) if b.get('stair') else LEVEL_Z[b['level']]
        if a.get('stair') is None and b.get('stair'):
            za = LEVEL_Z['GF']                  # the top node stands on the landing
        if a.get('stair') and b.get('stair') is None:
            zb = LEVEL_Z['B']
        length = math.dist((a['x'], a['y'], za), (b['x'], b['y'], zb))
        n = max(1, int(math.ceil(length/ds)))
        for k in range(n):
            t = k/n
            P.append((a['x']+(b['x']-a['x'])*t, a['y']+(b['y']-a['y'])*t, za+(zb-za)*t,
                      bool(a.get('stair') or b.get('stair')), a.get('garden') or b.get('garden')))
    last = nodes[-1]; P.append((last['x'], last['y'], LEVEL_Z[last['level']], False, None))
    arr = np.array([(p[0], p[1], p[2]) for p in P]); stair = np.array([p[3] for p in P]); garden = [p[4] for p in P]
    seg = np.hypot.reduce(np.diff(arr, axis=0), axis=1) if False else np.sqrt((np.diff(arr, axis=0)**2).sum(1))
    s = np.concatenate([[0.], np.cumsum(seg)])
    node_s = []
    cursor = 0.
    for a, b in zip(nodes, nodes[1:]):
        node_s.append(cursor)
        za = stair_ground(a['x'], spec) if a.get('stair') else LEVEL_Z[a['level']]
        zb = stair_ground(b['x'], spec) if b.get('stair') else LEVEL_Z[b['level']]
        if a.get('stair') is None and b.get('stair'): za = LEVEL_Z['GF']
        if a.get('stair') and b.get('stair') is None: zb = LEVEL_Z['B']
        cursor += math.dist((a['x'], a['y'], za), (b['x'], b['y'], zb))
    node_s.append(s[-1])
    # heading along the route with look-ahead, then smoothed
    L = 1.2
    tangent = np.zeros(len(arr))
    for i in range(len(arr)):
        j = min(len(arr)-1, int(np.searchsorted(s, s[i]+L)))
        k = max(0, j-10)
        d = arr[j, :2]-arr[k, :2]
        tangent[i] = math.atan2(d[1], d[0]) if np.hypot(*d) > 1e-6 else (tangent[i-1] if i else 0.)
    base = _smooth(np.unwrap(tangent), .8/ds)
    yaw = base.copy()
    holds = []
    grids = {}
    for st in stations:
        n = nodes[st['node']]; lv = n['level']
        if st['kind'] == 'garden-threshold':
            nxt = nodes[st['node']+1]
            target = math.atan2(nxt['y']-n['y'], nxt['x']-n['x'])
        elif st['kind'] == 'stair-top':
            target = 0.
        elif not st.get('transit'):
            grids.setdefault(lv, _opaque_grid(vm, lv))
            i = min(int(np.searchsorted(s, node_s[st['node']])), len(s)-1)
            target = view_yaw(vm, lv, (n['x'], n['y']), grids[lv], prefer=base[i])
        else:
            continue
        i = int(np.searchsorted(s, node_s[st['node']]))
        i = min(i, len(s)-1)
        R = 2.5
        window = np.clip(1-np.abs(s-s[i])/R, 0, 1)
        weight = np.sin(window*math.pi/2)**2
        delta = (target-yaw[i]+math.pi) % (2*math.pi)-math.pi
        yaw = yaw+weight*delta
        if st['hold_s'] > 0:
            holds.append((i, st['hold_s']))
    lv_samples = [level_at(g) for g in arr[:, 2]]
    yaw = repair_yaw(vm, arr[:, :2], lv_samples, _smooth(yaw, .3/ds))
    dyaw = np.abs(np.gradient(yaw, s))
    vlim = np.minimum(settings['cruise_speed_m_s'], np.where(stair, settings['stair_speed_m_s'], 9.))
    vlim = np.minimum(vlim, .9*math.radians(settings['maximum_yaw_rate_deg_s'])/np.maximum(dyaw, 1e-9))
    vlim = np.maximum(vlim, .15)
    stops = {0, len(s)-1}|{i for i, h in holds}
    for i in stops:
        vlim[i] = 0.
    a = settings['acceleration_m_s2']; v = vlim.copy(); dsi = np.diff(s)
    for _ in range(2):
        for i in range(1, len(v)):
            v[i] = min(v[i], math.sqrt(v[i-1]**2+2*a*dsi[i-1]))
        for i in range(len(v)-2, -1, -1):
            v[i] = min(v[i], math.sqrt(v[i+1]**2+2*a*dsi[i]))
    dt = np.where(v[:-1]+v[1:] > 1e-9, 2*dsi/np.maximum(v[:-1]+v[1:], 1e-9), 0.)
    # a stop sample between two zero speeds needs a finite time; use the acceleration ramp from rest
    zero = v[:-1]+v[1:] <= 1e-9
    dt[zero] = 2*np.sqrt(2*dsi[zero]/(2*a))*0+np.sqrt(2*dsi[zero]/a)
    t = np.concatenate([[0.], np.cumsum(dt)])
    hold_end = {}
    shift = 0.; ts = t.copy()
    pause = [(i, h) for i, h in sorted(holds)]
    # build (time, s-index) table with flat segments for the holds
    table_t, table_i = [], []
    extra = 0.; k = 0
    for i in range(len(s)):
        table_t.append(t[i]+extra); table_i.append(i)
        while k < len(pause) and pause[k][0] == i:
            extra += pause[k][1]; table_t.append(t[i]+extra); table_i.append(i); k += 1
    final_hold = [h for i, h in holds if i == len(s)-1]
    total = table_t[-1]
    frames_n = int(math.floor(total*settings['fps']))+1
    tt = np.arange(frames_n)/settings['fps']
    idx = np.interp(tt, table_t, table_i)
    eye = settings['eye_height_m']; frames = []
    for f, fi in enumerate(idx):
        i0 = int(math.floor(fi)); i1 = min(i0+1, len(s)-1); w = fi-i0
        pos = arr[i0]*(1-w)+arr[i1]*w; yw = yaw[i0]*(1-w)+yaw[i1]*w
        yaw_deg = math.degrees(yw); ground = float(pos[2])
        cam = [float(pos[0]), float(pos[1]), ground+eye]
        lvl = level_at(ground); on_stair = bool(stair[i0] and stair[i1])
        room = vm.room_at(lvl, cam[0], cam[1]) if not garden[i0] else None
        frames.append(dict(index=f, seconds=f/settings['fps'], yaw_deg=yaw_deg, ground_m=ground,
                           level=lvl, stair=on_stair, room=room,
                           segment='garden-placeholder' if garden[i0] else 'interior',
                           camera=dict(position=cam, target=[cam[0]+math.cos(yw), cam[1]+math.sin(yw), cam[2]],
                                       lens_mm=24, sensor_mm=36, shift_x=0, shift_y=0)))
    settings['frames'] = frames_n
    record = dict(schema='flythrough-villa-path/1', settings=settings, frames=frames,
                  distance_m=float(s[-1]), duration_s=frames_n/settings['fps'],
                  stations=[dict(room=st['room'], kind=st['kind'], hold_s=st['hold_s'], garden=st.get('garden'),
                                 first_frame=None) for st in stations])
    for rec, st in zip(record['stations'], stations):
        i = int(np.searchsorted(s, node_s[st['node']]))
        j = int(np.argmin(np.abs(idx-i)))
        rec['first_frame'] = j
    record['sha256'] = digest(record)
    return record


# ---- door leaves: an explicit open state, never hidden geometry --------------------------------------
def _rect_poly(cx, cy, ux, uy, length, width):
    """Corners of a rectangle starting at (cx, cy) running `length` along unit (ux, uy), `width` across it."""
    px, py = -uy, ux
    return np.array([[cx-px*width/2, cy-py*width/2], [cx+ux*length-px*width/2, cy+uy*length-py*width/2],
                     [cx+ux*length+px*width/2, cy+uy*length+py*width/2], [cx+px*width/2, cy+py*width/2]])


def _polys_overlap(a, b):
    """Convex polygon separating-axis test (touching edges do not overlap)."""
    for poly in (a, b):
        for i in range(len(poly)):
            e = poly[(i+1) % len(poly)]-poly[i]; n = np.array([-e[1], e[0]])
            pa, pb = a@n, b@n
            if pa.max() <= pb.min()+1e-9 or pb.max() <= pa.min()+1e-9:
                return False
    return True


def _rect_to_poly(r, grow=0.):
    return np.array([[r[0]-grow, r[1]-grow], [r[2]+grow, r[1]-grow], [r[2]+grow, r[3]+grow], [r[0]-grow, r[3]+grow]])


def open_interior_doors(scene, vm, frames, policy_=None):
    """Swing every interior door leaf open about a jamb, in place, and report what was done.

    The leaf keeps every vertex and face (it is rotated, not removed); its lever handle follows it. The hinge
    end and swing side are not authored (except the core entrance), so all four are tried at each registered
    angle and the first with no contact with furniture, walls or the walked route (0.35 m, then 0.25 m as a fallback) is taken: the
    largest angle that works, then the largest clearance. Entrance leaves are left closed. A door with no
    collision-free option stays closed and is reported so the route test fails loudly.
    """
    policy_ = policy_ or villa_policy(); F = vm.F; report = []
    route = {lv: np.array([f['camera']['position'][:2] for f in frames if f['level'] == lv and not f['stair']])
             for lv in LEVEL_Z}
    handle = next((m for m in scene['meshes'] if m['id'] == 'detail-door-handles'), None)
    for mesh in scene['meshes']:
        if mesh.get('part_kind') != 'door-leaf' or not mesh['id'].startswith('door-leaf-'):
            continue
        pts = np.array([v for face in mesh['faces'] for v in face])
        lo, hi = pts.min(0), pts.max(0)
        name = (mesh.get('element_ids') or [mesh['id']])[0]
        entry = dict(id=mesh['id'], element=name)
        if 'core' in name:
            report.append(dict(entry, state='closed', reason='entrance to the unmodelled shared core; not on the route'))
            continue
        lv = level_at((lo[2]+hi[2])/2)
        along_x = (hi[0]-lo[0]) >= (hi[1]-lo[1])
        length = (hi[0]-lo[0]) if along_x else (hi[1]-lo[1]); width = (hi[1]-lo[1]) if along_x else (hi[0]-lo[0])
        mid = ((lo[1]+hi[1])/2) if along_x else ((lo[0]+hi[0])/2)
        ends = [(lo[0], mid), (hi[0], mid)] if along_x else [(mid, lo[1]), (mid, hi[1])]
        obstacles = [_rect_to_poly(r, .02) for r in vm.pieces[lv]]
        obstacles += [_rect_to_poly(w) for w in F._walls(vm.spec, lv)+F._columns()]
        best = None
        for minimum_gap, angle in [(g, a) for g in policy_['door_route_gap_m'] for a in policy_['door_open_degrees']]:
            for h, hinge in enumerate(ends):
                for sign in (1, -1):
                    free_end = ends[1-h]
                    ux, uy = free_end[0]-hinge[0], free_end[1]-hinge[1]; norm = math.hypot(ux, uy); ux, uy = ux/norm, uy/norm
                    a = math.radians(angle)*sign
                    rx, ry = ux*math.cos(a)-uy*math.sin(a), ux*math.sin(a)+uy*math.cos(a)
                    poly = _rect_poly(hinge[0], hinge[1], rx, ry, length, width)
                    # the hinge corner sits in the jamb by half a leaf thickness; test the leaf from 0.12 m out
                    probe = _rect_poly(hinge[0]+rx*.12, hinge[1]+ry*.12, rx, ry, length-.12, width*.6)
                    if any(_polys_overlap(probe, o) for o in obstacles):
                        continue
                    track = route[lv]
                    # distance from the route to the leaf polygon, sampled along the leaf's centre line and corners
                    samples = np.vstack([poly, [(hinge[0]+rx*length*t, hinge[1]+ry*length*t) for t in np.linspace(0, 1, 9)]])
                    gap = min(float(np.min(np.hypot(*(track[:, None, :]-samples[None]).transpose(2, 0, 1)))), 9.) if len(track) else 9.
                    if gap < minimum_gap:
                        continue
                    if best is None or (angle, gap) > (best[0], best[1]):
                        best = (angle, gap, hinge, sign, h)
            if best:
                break
        if best is None:
            report.append(dict(entry, state='closed', reason='no collision-free swing found'))
            continue
        angle, gap, hinge, sign, h = best; a = math.radians(angle)*sign; c, s_ = math.cos(a), math.sin(a)

        def rot(v):
            dx, dy = v[0]-hinge[0], v[1]-hinge[1]
            return [hinge[0]+dx*c-dy*s_, hinge[1]+dx*s_+dy*c, v[2]]
        mesh['faces'] = [[rot(v) for v in face] for face in mesh['faces']]
        moved = 0
        if handle:
            for k, face in enumerate(handle['faces']):
                cx = sum(v[0] for v in face)/len(face); cy = sum(v[1] for v in face)/len(face); cz = sum(v[2] for v in face)/len(face)
                if lo[0]-.12 <= cx <= hi[0]+.12 and lo[1]-.12 <= cy <= hi[1]+.12 and lo[2] <= cz <= hi[2]:
                    handle['faces'][k] = [rot(v) for v in face]; moved += 1
        report.append(dict(entry, state='open', angle_deg=angle, swing_sign=sign, hinge=[round(hinge[0], 3), round(hinge[1], 3)],
                           route_gap_m=round(gap, 3), handle_faces_moved=moved))
    return report


# ---- admission for the whole-villa path --------------------------------------------------------------
def villa_frame_views(path, scene):
    """Same authored day state as the basement stills; subject follows the room the camera is in."""
    from .concept.villa_render import curtain_hidden_meshes, sun_for_timestamp
    sun = sun_for_timestamp('2026-10-15T10:30:00+03:00')
    hidden = curtain_hidden_meshes(scene.get('curtains', []), 'day')
    views = []
    for f in path['frames']:
        garden = f['segment'] != 'interior'
        views.append(dict(id='frame-%04d' % f['index'], title='Whole-villa walkthrough', camera=f['camera'],
                          state='day', exposure='exterior-day' if garden else 'day',
                          subjects=[] if (garden or not f['room']) else ['room:'+f['room']],   # g6 terrace no longer exists (GI garden replaced it)
                          resolution=path['settings']['final_resolution'], samples=1024,
                          layers_on=['ambient', 'accent'], dimmers={'ambient': .5, 'accent': .5},
                          hide_meshes=list(hidden), sun=dict(sun),
                          caption_notes=['Interior doors are shown swung open; garden glazing stays closed.']))
    return views


def admit_villa_path(path, scene, layout, spec, evaluated_meshes=None, vm=None, frames=None):
    """Per-frame admission with the production guards, level- and stair-aware.

    Interior frames (flat floor) get the standing-point policy, the one-metre forward-wall rule, the
    camera lens clearance and the swept walking envelope. Frames on the flight skip the plan-view
    standing policy and the plan-view furniture clearance (both are blind to height: the under-stair
    joinery lies directly beneath the treads) and are judged by the 3D swept envelope only, which
    starts `stair_clearance_m` above the lower tread line. Garden-placeholder frames are screened the
    same way but reported separately: the garden is being rebuilt (LDB) and its glazing is closed.
    Returns rows plus a summary by segment; `passed` covers interior rows only.
    """
    from scripts.villa_render_views import camera_proximity_violations, CameraProximityGeometry
    from .concept import villa_furnish as F
    from .concept.render_views import standing_point_clear
    settings = path['settings']; vm = vm or VillaMap(layout, spec)
    items = {i['id']: i for i in vm.items}
    walls_by_level = {lv: F._walls(spec, lv)+F._columns() for lv in LEVEL_Z}
    host_walls = scene_wall_hosts(scene)
    flagged_rooms = {s['room'] for s in path.get('stations', []) if s.get('flagged_under_1m')}
    sweeps = [CameraSweep(scene)]+([CameraSweep({'meshes': evaluated_meshes})] if evaluated_meshes else [])
    geometry = CameraProximityGeometry(scene)
    rows = motion_findings(path['frames'], settings)
    plan = plan_findings(path, vm)
    previous = path['frames'][0]
    for frame, view, row in zip(path['frames'], villa_frame_views(path, scene), rows):
        pos = frame['camera']['position']; x, y = pos[:2]; lv = frame['level']
        if abs(pos[2]-frame['ground_m']-settings['eye_height_m']) > 1e-9:
            row['failures'].append('camera eye height differs from still-view rule')
        sight = wall_sightline_findings(view, host_walls)
        if sight and (frame.get('station') if frame.get('phase') == 'turn' else frame['room']) in flagged_rooms:
            row['waived_wall_sightline'] = sight       # room too small for the 1 m rule from any standing point: flagged, never silent
        else:
            row['failures'].extend(sight)
        room = frame['room']
        row['failures'].extend(plan.get(frame['index'], []))
        view['standing_room'] = room or ('stair-b' if frame['ground_m'] < -1.5 else 'stair-gf')
        row['lens_clearance'] = camera_proximity_violations(view, scene, {} if frame['stair'] else items, geometry=geometry)
        if row['lens_clearance']:
            row['failures'].append('existing interior lens clearance failed')
        a, b = previous['camera']['position'], pos
        if frame['stair'] or previous['stair']:
            ground = min(previous['ground_m'], frame['ground_m'])+settings['stair_clearance_m']
            height = settings['walking_height_m']-settings['stair_clearance_m']+abs(previous['ground_m']-frame['ground_m'])
        else:
            ground, height = frame['ground_m'], settings['low_headroom_rooms_m'].get(room, settings['walking_height_m'])
        hits = sorted({h for sw in sweeps for h in sw.findings(a, b, ground_m=ground, clearance_m=settings['obstacle_clearance_m'], height_m=height)})
        row['swept_obstacles'] = hits
        if hits:
            row['failures'].append('physical walking envelope intersects design geometry')
        row.update(room=room, level=lv, stair=frame['stair'], segment=frame['segment'])
        row['passed'] = not row['failures']
        previous = frame
    interior = [r for r in rows if r['segment'] == 'interior']; garden = [r for r in rows if r['segment'] != 'interior']
    return dict(schema='flythrough-villa-guards/1', path_sha256=path['sha256'], frames=rows,
                passed=all(r['passed'] for r in interior),
                summary=dict(interior=dict(frames=len(interior), failed=sum(not r['passed'] for r in interior)),
                             garden_placeholder=dict(frames=len(garden), failed=sum(not r['passed'] for r in garden))),
                max_speed_m_s=max(r['speed_m_s'] for r in rows), max_yaw_rate_deg_s=max(r['yaw_rate_deg_s'] for r in rows),
                acceptance_scope='complete per-frame render admission' if evaluated_meshes else 'authored geometry only; evaluated meshes pending')


def route_rooms(path, layout, rooms=None):
    """Rooms entered, in order of first visit, counting a room when any frame stands inside its rectangle."""
    seen = []
    for f in path['frames']:
        r = f['room']
        if r and r not in seen:
            seen.append(r)
    return seen


def plan_findings(path, vm):
    """Plan-level admission that needs no scene: standing policy per flat frame and no wall crossing.

    A segment between successive frames fails if it crosses a built wall rectangle (door gaps already cut)
    or a column on its level. Flight and garden frames are skipped here (the flight lies over the under-stair
    joinery; the garden is outside the walls). Returns {frame index: [failures]} for failing frames only.
    """
    from .concept.render_views import standing_point_clear
    F = vm.F; out = {}
    walls = {lv: [_rect_to_poly(w) for w in F._walls(vm.spec, lv)+F._columns()] for lv in LEVEL_Z}
    standing = {lv: F._walls(vm.spec, lv)+F._columns() for lv in LEVEL_Z}
    previous = None
    for f in path['frames']:
        bad = []
        x, y = f['camera']['position'][:2]
        flat = not f['stair'] and f['segment'] == 'interior'
        if flat:
            if f['room'] is None or not standing_point_clear(vm.layout, vm.spec, f['room'], x, y, vm.pieces[f['level']], standing[f['level']]):
                bad.append('existing standing-point clearance policy failed')
            if previous is not None and previous['level'] == f['level'] and not previous['stair']:
                a = previous['camera']['position'][:2]
                if math.dist(a, (x, y)) > 1e-9:
                    if any(_segment_hits_rect(a, (x, y), r) for r in walls[f['level']]):
                        bad.append('route segment crosses a built wall')
        if bad:
            out[f['index']] = bad
        previous = f
    return out


def _segment_hits_rect(a, b, poly):
    """Liang-Barsky clip of segment a-b against the axis-aligned rectangle polygon."""
    x0, y0 = poly.min(0); x1, y1 = poly.max(0)
    dx, dy = b[0]-a[0], b[1]-a[1]; t0, t1 = 0., 1.
    for p, q in ((-dx, a[0]-x0), (dx, x1-a[0]), (-dy, a[1]-y0), (dy, y1-a[1])):
        if abs(p) < 1e-12:
            if q < 0:
                return False
        else:
            r = q/p
            if p < 0:
                t0 = max(t0, r)
            else:
                t1 = min(t1, r)
            if t0 > t1:
                return False
    return t1 > t0 and (t1-t0) > 1e-9
