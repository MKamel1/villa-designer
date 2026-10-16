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


def frame_views(path, scene):
    """Authored day state shared by the basement stills; only cameras are new."""
    require_path_hash(path)
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


def clip_source_group(rows):
    """Apply the registered strict-majority rule to the complete clip population."""
    from .exposure_groups import classify,rule
    if len(rows) != policy()['frames']:
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
