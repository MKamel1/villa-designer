"""Measured garden appearance/view checks, independent of villa identifiers.

Lengths are metres. Face normals are unit outward vectors; z is vertical.
The 0.20 m foliage gap and central image third are authored review criteria,
not horticultural or building standards.
"""
from __future__ import annotations
import math

GROUND_ONLY = frozenset({'paving', 'travertine', 'oak-floor', 'artificial-grass',
                         'lawn', 'garden-gravel', 'garden-pebbles', 'stepping-stone'})
LEAF_GAP_M = .20


def subject_frame_findings(view, scene):
    """Full physical-vertex framing for views declaring that subject intent.

    Horizontal limits are half a sensor width; vertical limits are half the
    image height divided by image width. Lens shift uses sensor-width units.
    Imported appearances use the recorded exact full-height hull vertices.
    """
    if not view.get('require_full_subject_frame'):return []
    import numpy as np
    from .route_geometry import prop_framing_points
    c=view['camera'];eye=np.array(c['position']);yaw=math.atan2(c['target'][1]-eye[1],c['target'][0]-eye[0])
    half=view['resolution'][1]/view['resolution'][0]/2;out=[]
    for subject in view['subjects']:
        points=[p for m in scene['meshes'] if m['id'].startswith(subject) or m.get('label')==subject for face in m['faces'] for p in face]
        for prop in scene.get('props',[]):
            if prop['id'].startswith(subject) or prop.get('label')==subject:points+=prop_framing_points(prop).tolist()
        if not points:
            out.append(view['id']+': unresolved built subject '+subject);continue
        delta=np.asarray(points)-eye
        depth=delta[:,0]*math.cos(yaw)+delta[:,1]*math.sin(yaw)
        if depth.min()<=0:
            out.append(view['id']+': subject behind camera '+subject);continue
        horizontal=c['lens_mm']/c['sensor_mm']*(delta[:,0]*math.sin(yaw)-delta[:,1]*math.cos(yaw))/depth-c.get('shift_x',0.)
        vertical=c['lens_mm']/c['sensor_mm']*delta[:,2]/depth-c.get('shift_y',0.)
        if abs(horizontal).max()>.5 or vertical.min()<-half or vertical.max()>half:
            out.append(view['id']+': whole built subject outside frame '+subject)
    return out


def subject_visibility_evidence(view, scene):
    """First-hit mesh rays for explicitly required visible garden subjects.

    Thirteen samples per subject: bounding centre and twelve evenly indexed
    unique actual vertices (lexicographically sorted, independent of faces).
    Opaque, camera-visible physical meshes occlude; glass and diagnostic or
    surface datums do not. Imported props still require image review.
    Coordinates/distances are metres; direction is a unit vector. This is
    an authored geometric screen, not projected-area or aesthetic proof.
    """
    import numpy as np
    from .render_support import _triangles
    targets = view.get('visibility_targets', [])
    if not targets:
        return []
    eye = np.array(view['camera']['position'], dtype=float)
    meshes = [m for m in scene['meshes'] if not m.get('diagnostic')
              and not m.get('surface') and m.get('visibility', {}).get('camera', True)
              and scene['materials'][m['material']]['kind'] not in ('glass', 'translucent')]
    triangles, owners = _triangles(meshes)
    results = []
    for subject in targets:
        matched = [m for m in meshes if m['id'] == subject]
        if not matched:
            results.append(dict(subject=subject, visible=0, samples=13, first_hits=[]))
            continue
        points = np.unique(np.array([p for m in matched for f in m['faces'] for p in f]), axis=0)
        samples = np.vstack([(points.min(axis=0)+points.max(axis=0))/2,
                             points[np.linspace(0, len(points)-1, 12, dtype=int)]])
        low = np.minimum(points.min(axis=0), eye)-.03
        high = np.maximum(points.max(axis=0), eye)+.03
        nearby = np.all(triangles.min(axis=1) <= high, axis=1) & np.all(triangles.max(axis=1) >= low, axis=1)
        local, indices = triangles[nearby], owners[nearby]
        edge1, edge2 = local[:, 1]-local[:, 0], local[:, 2]-local[:, 0]
        delta = eye-local[:, 0]
        cross_delta = np.cross(delta, edge1)
        hits = []
        for point in samples:
            direction = point-eye
            length = np.linalg.norm(direction)
            if length <= .03:
                hits.append(None)
                continue
            direction /= length
            cross_direction = np.cross(direction, edge2)
            determinant = np.einsum('ij,ij->i', edge1, cross_direction)
            valid = abs(determinant) > 1e-9
            inverse = np.divide(1., determinant, out=np.zeros_like(determinant), where=valid)
            along1 = inverse*np.einsum('ij,ij->i', delta, cross_direction)
            along2 = inverse*(cross_delta@direction)
            distance = inverse*np.einsum('ij,ij->i', edge2, cross_delta)
            # Tiny barycentric roundoff allowance retains actual vertex hits.
            candidates = np.where(valid & (along1 >= -1e-8) & (along2 >= -1e-8)
                                  & (along1+along2 <= 1+1e-8) & (distance > .03)
                                  & (distance <= length+1e-6))[0]
            hits.append(None if not len(candidates) else
                        meshes[int(indices[candidates[np.argmin(distance[candidates])]])]['id'])
        results.append(dict(subject=subject, visible=sum(h == subject for h in hits),
                            samples=len(samples), first_hits=hits))
    return results


def subject_visibility_findings(view, scene):
    """ASSUMED majority-ray visibility: at least 7 of 13 target rays reach it.

    Partial foreground foliage is acceptable; a hidden named feature is not.
    An explicit reviewed allowance is bound to one view and one subject.
    All other subjects retain seven rays. Invalid or copied allowances fail
    closed. This screen accompanies actual preview review and full framing.
    """
    allowances = view.get('visibility_allowances', {})
    findings = []
    if not isinstance(allowances, dict):
        findings.append(view['id']+': invalid visibility allowances')
        allowances = {}
    minima = {}
    for subject, allowance in allowances.items():
        if (not isinstance(allowance, dict)
                or allowance.get('view_id') != view['id']
                or subject not in view.get('visibility_targets', [])
                or type(allowance.get('minimum_visible_rays')) is not int
                or not 1 <= allowance['minimum_visible_rays'] <= 13
                or allowance.get('samples') != 13
                or not isinstance(allowance.get('reason'), str)
                or not allowance['reason'].strip()):
            findings.append(view['id']+': invalid visibility allowance for '+subject)
        else:
            minima[subject] = allowance['minimum_visible_rays']
    for result in subject_visibility_evidence(view, scene):
        if result['samples'] != 13 or result['visible'] < minima.get(result['subject'], 7):
            findings.append(view['id']+': named subject obscured '+result['subject'])
    return findings


def overhead_cover(scene, ground_m):
    """Plan union of opaque architectural undersides above the garden floor.

    Coordinates and ground_m are metres; even a low overhang blocks sky.
    Excludes transparent glazing and movable objects, includes built context.
    """
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    return unary_union([
        Polygon([point[:2] for point in face])
        for mesh in scene.get('meshes', [])
        if mesh.get('group') in ('shell', 'context')
        and scene['materials'][mesh['material']]['kind'] not in ('glass', 'translucent')
        and mesh.get('part_kind') not in ('window-frame', 'door-leaf')
        for face in mesh['faces']
        if normal(face)[2] < -.7 and min(point[2] for point in face) > ground_m + .05
    ])


def garden_camera_findings(view, scene):
    """Garden views stand inside the yard, in open sky, or a named room.

    Garden subjects identify this class independently of view identifiers.
    Lower and upper garden datums select the relevant overhead enclosure.
    Through-door views declare
    standing_room; its measured rectangle and level must contain the lens.
    """
    from shapely.geometry import Point, Polygon, box
    if not any(subject.startswith('landscape-') for subject in view.get('subjects', [])):
        return []
    from .garden_g4e import foreground_fixture_findings
    foreground=foreground_fixture_findings(view,scene) if 'evening-garden' in view.get('layers_on',[]) else []
    domain = scene.get('garden_camera_domain')
    if domain is None:
        return [view['id'] + ': MISSING garden camera standing domain']
    x, y, z = view['camera']['position']
    if 'standing_ground_m' in view:
        # A close roof-edge camera must have an actual upward standing
        # surface below it; yard containment alone admits the sunken void.
        from .render_support import _Surfaces,_triangles
        surfaces=[m for m in scene.get('meshes',[])
                  if m.get('group') in ('shell','ground','context')
                  and not m.get('material','').startswith('glass')]
        triangles,owners=_triangles(surfaces)
        physical=_Surfaces(triangles,owners)
        supported=physical.meets(physical.up,x,y,view['standing_ground_m'])
        if not supported:return [view['id']+': no actual standing floor at recorded camera datum']
    ground = domain['upper_datum_m'] if z >= domain['upper_datum_m'] else domain['ground_m']
    point = Point(x, y)
    room_id = view.get('standing_room')
    if room_id:
        room = domain['rooms'].get(room_id)
        if room and room['ground_m'] < z < room['ground_m'] + room['height_m'] and box(*room['rect_m']).covers(point):
            return foreground
        return [view['id'] + ': camera outside declared standing room']
    if not Polygon(domain['yard_polygon_m']).covers(point):
        return [view['id'] + ': exterior garden camera outside yard polygon']
    if overhead_cover(scene, ground).covers(point):
        return [view['id'] + ': exterior garden camera under architectural cover']
    return foreground


def normal(face):
    a, b, c = face[:3]
    u, v = [b[k]-a[k] for k in range(3)], [c[k]-a[k] for k in range(3)]
    n = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
    length = math.sqrt(sum(x*x for x in n))
    return [x/length for x in n] if length else [0, 0, 0]


def downward_ground_findings(scene):
    """Inspect every face, including buried faces; no object/tag exemptions."""
    out = []
    for mesh in scene.get('meshes', []):
        bad=[]
        assigned=mesh.get('face_materials', [mesh['material']]*len(mesh.get('faces', [])))
        for index,face in enumerate(mesh.get('faces', [])):
            material=assigned[index]
            if (material in GROUND_ONLY or scene.get('materials', {}).get(material, {}).get('surface_use') == 'ground-only') and normal(face)[2]<-.7:
                bad.append(material)
        if bad:
            out.append(f"{mesh['id']}: {len(bad)} downward faces use ground-only {', '.join(sorted(set(bad)))}")
    return out


def plant_form_findings(meshes):
    """Require real leaf surfaces, not stem minima, within 0.20 m of root soil.

    Face indices identify leaf geometry at construction. Missing indices or
    root datum refuse procedural clumps. Thin climbing foliage is generated
    separately and checked from its actual deterministic leaf placements.
    """
    from .garden_shade import form_findings
    from .garden_g4e import habit_findings
    out = form_findings(meshes) + habit_findings(meshes)
    for mesh in meshes:
        if mesh.get('part_kind') == 'climber':
            from ..blender.climber_placement import placements,density_for_coverage,SIZE
            points=[q for face in mesh['faces'] for q in face]
            bounds=[min(q[k] for q in points) for k in range(3)]+[max(q[k] for q in points) for k in range(3)]
            root=mesh.get('root_z_m')
            leaves=[]
            if mesh.get('explicit_geometry'):
                indices=mesh.get('leaf_face_indices',[])
                if any(type(i) is not int or not 0 <= i < len(mesh['faces']) for i in indices):
                    out.append(mesh['id']+': invalid measured climbing leaf indices');continue
                leaves=[q[2] for i in indices for q in mesh['faces'][i]]
            elif mesh.get('species')=='Cissus alata':
                from ..blender.climber_placement import grape_ivy_geometry,ivy_connection_findings
                stems=next((m for m in meshes if m['id']==mesh.get('stem_mesh')),None)
                if stems is None:
                    out.append(mesh['id']+': missing physical training stems');continue
                foliage,petioles,_=grape_ivy_geometry(bounds,stems['faces'],mesh.get('appearance_seed',sum(map(ord,mesh['id']))))
                out.extend(mesh['id']+': '+f for f in ivy_connection_findings(foliage,petioles,stems['faces']))
                leaves=[q[2] for f in foliage for q in f]
            else:
                leaves=[z-SIZE['leaf'] for x,y,z,kind in placements(bounds,density_for_coverage(),mesh.get('appearance_seed',sum(map(ord,mesh['id'])))) if kind=='leaf']
            if root is None or not leaves:
                out.append(mesh['id']+': MISSING measured climbing leaves/root soil datum')
            elif min(leaves)-root>LEAF_GAP_M+1e-9:
                out.append(f"{mesh['id']}: climbing leaf mass {min(leaves)-root:.3f} m above soil; limit {LEAF_GAP_M:.2f} m")
            continue
        if mesh.get('part_kind') != 'plant-clump':
            continue
        indices, root = mesh.get('leaf_face_indices'), mesh.get('root_z_m')
        if not indices or root is None or any(type(i) is not int or not 0 <= i < len(mesh['faces']) for i in indices):
            out.append(mesh['id']+': MISSING measured leaf faces/root soil datum')
            continue
        low = min(q[2] for i in indices for q in mesh['faces'][i])
        gap = low-root
        for blade in mesh.get('blade_records', []):
            import numpy as np
            points=np.unique(np.array([mesh['faces'][i] for i in blade['face_indices']]).reshape(-1,3),axis=0)
            _,_,axes=np.linalg.svd(points-points.mean(axis=0))
            spans=np.ptp(points@axes.T,axis=0)
            ratio=spans[0]/spans[1]
            if not 3 <= ratio <= 4:
                out.append(f"{mesh['id']}: measured paddle length:width {ratio:.3f} outside 3:1--4:1")
        if gap > LEAF_GAP_M + 1e-9:
            out.append(f"{mesh['id']}: leaf mass {gap:.3f} m above soil; limit {LEAF_GAP_M:.2f} m")
    return out


def project(camera, point):
    """Return forward depth and image coordinates, centred on zero.

    Horizontal units are fractions of image width. Vertical units use the
    same width, so a 3:2 image spans -1/3 to +1/3 vertically.
    """
    px, py, pz = camera['position']; tx, ty, _ = camera['target']
    yaw = math.atan2(ty-py, tx-px)
    dx, dy = point[0]-px, point[1]-py
    depth = dx*math.cos(yaw)+dy*math.sin(yaw)
    scale = camera['lens_mm']/camera['sensor_mm']
    if depth <= 0:
        return depth, 0., 0.
    return depth, scale*(dx*math.sin(yaw)-dy*math.cos(yaw))/depth-camera.get('shift_x', 0), scale*(point[2]-pz)/depth-camera.get('shift_y', 0)


def opening_frame_findings(view, scene):
    """Frame members between the lens and a subject cannot enter its centre third.

    Uses actual member faces and camera frustum clipping, not frame centroids.
    Only openings through which a subject ray passes count: remote windows
    seen on another facade are not foreground openings. No view-id exceptions.
    """
    from .route_geometry import prop_framing_points
    from shapely.geometry import Polygon
    cam = view['camera']; half_height = view['resolution'][1]/view['resolution'][0]/2
    # Resolve intended subjects directly; never import a drawing script here.
    points = [q for subject in view['subjects'] for mesh in scene['meshes']
              if mesh['id'].startswith(subject) or mesh.get('label') == subject
              for face in mesh['faces'] for q in face]
    for subject in view['subjects']:
        for prop in scene.get('props', []):
            if prop['id'].startswith(subject): points.extend(prop_framing_points(prop).tolist())
    primary=view['subjects'][0] if view.get('subjects') else None
    primary_points=[q for mesh in scene['meshes'] if primary and (mesh['id'].startswith(primary) or mesh.get('label')==primary) for face in mesh['faces'] for q in face]
    for prop in scene.get('props', []):
        if primary and prop['id'].startswith(primary):primary_points.extend(prop_framing_points(prop).tolist())
    primary_depths=[project(cam,p)[0] for p in primary_points if project(cam,p)[0]>0]
    foreground_depth=min(primary_depths) if primary_depths else float('inf')
    import numpy as np
    targets = np.asarray(points, dtype=float).reshape(-1, 3)
    origin = np.asarray(cam['position'])
    yaw = math.atan2(cam['target'][1]-origin[1], cam['target'][0]-origin[0])
    forward_axis = np.array([math.cos(yaw), math.sin(yaw), 0.])
    openings = []
    for pane in scene['meshes']:
        if pane.get('part_kind') != 'glass-pane' or pane.get('material') != 'glass-clear': continue
        # Shell meshes batch many panes: six faces form each closed pane.
        for offset in range(0, len(pane['faces']), 6):
            pts = [q for f in pane['faces'][offset:offset+6] for q in f]
            low = [min(q[k] for q in pts) for k in range(3)]; high = [max(q[k] for q in pts) for k in range(3)]
            axis = min((0, 1), key=lambda k: high[k]-low[k]); across = 1-axis
            plane = (low[axis]+high[axis])/2
            delta = targets[:, axis] - origin[axis]
            fractions = np.divide(plane-origin[axis], delta, out=np.zeros_like(delta), where=abs(delta)>1e-9)
            hits = origin + fractions[:, None]*(targets-origin)
            valid = ((fractions > 0) & (fractions < 1) &
                     ((hits-origin) @ forward_axis < foreground_depth) &
                     (hits[:, across] >= low[across]) & (hits[:, across] <= high[across]) &
                     (hits[:, 2] >= low[2]) & (hits[:, 2] <= high[2]))
            if np.any(valid):
                openings.append((axis, plane, across, low, high))
    findings=[]
    for mesh in scene['meshes']:
        if mesh.get('part_kind') != 'window-frame':continue
        hit_faces=[]
        for index,face in enumerate(mesh['faces']):
            if not any(all(abs(q[axis]-plane)<.045 and low[across]-.06<=q[across]<=high[across]+.06 and low[2]-.06<=q[2]<=high[2]+.06 for q in face) for axis,plane,across,low,high in openings):continue
            # Clip world face to the near plane before perspective projection.
            poly=face
            clipped=[]
            for a,b in zip(poly,poly[1:]+poly[:1]):
                da,db=project(cam,a)[0],project(cam,b)[0]
                if da>=.001:clipped.append(a)
                if (da>=.001)!=(db>=.001):
                    t=(.001-da)/(db-da);clipped.append([a[k]+t*(b[k]-a[k]) for k in range(3)])
            if len(clipped)<3:continue
            projected=[project(cam,q)[1:] for q in clipped]
            polygon=Polygon(projected)
            if not polygon.is_valid:polygon=polygon.buffer(0)
            from shapely.geometry import box
            if polygon.intersection(box(-1/6,-half_height,1/6,half_height)).area>1e-10:hit_faces.append(index)
        if hit_faces:findings.append(dict(view=view['id'],mesh=mesh['id'],face_indices=hit_faces,reason='foreground opening frame occupies central third'))
    return findings


def soil_visibility_findings(scene):
    """Refuse mineral floor faces covering ground-bed soil at its elevation.

    Each soil surface comes from actual faces. Plant foliage and slim edging
    are intentional above soil; architectural floor finishes are competing
    surfaces and cannot be coplanar with it. No court or item-id exemptions.
    """
    from shapely.geometry import Polygon
    out=[]
    beds=[(m,Polygon([q[:2] for q in m['faces'][0]]),m['faces'][0][0][2]) for m in scene['meshes'] if m.get('part_kind')=='soil-bed']
    for soil,bed,z in beds:
        for m in scene['meshes']:
            if m.get('part_kind') in ('soil-bed','bed-edge') or m.get('group') not in ('shell','context','ground'):continue
            slots=m.get('face_materials',[m['material']]*len(m['faces']))
            area=0.
            for face,material in zip(m['faces'],slots):
                if material=='garden-soil' or normal(face)[2]<.999:continue
                if min(q[2] for q in face)<z-1e-6 or max(q[2] for q in face)>z+.02:continue
                area+=Polygon([q[:2] for q in face]).intersection(bed).area
            if area>1e-6:out.append('%s: %.6f m2 soil obscured by %s'%(soil['id'],area,m['id']))
    return out
