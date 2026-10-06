"""Physical finish assemblies and independent render-only mounting coverage.

Coordinates and thicknesses are metres. A shell polygon already includes its
openings; triangulating it before extrusion preserves concavities and holes.
Diagnostic host planes remain audit datums, never render geometry.
"""
from collections import Counter
from copy import deepcopy

import numpy as np

from .fitting_mounting import normal
from .render_support import _ear_clip, _triangles, _point_triangle_distance

SURFACE_TOLERANCE_M = .002  # Requested render mounting-face comparison tolerance.


def _key(point):
    return tuple(round(v, 9) for v in point)


def extrude(face, outward, thickness):
    """Close a polygon into an outward-wound solid, including opening reveals.

    Cancel internal triangulation edges; bridge only true boundary edges.
    Thus a keyhole's repeated slit is not an artificial wall across its hole.
    """
    triangles = _ear_clip(face)
    if not triangles or thickness <= 0:
        raise ValueError('Finish extrusion needs a triangulable face and positive thickness')
    edges = {}
    faces = []
    for triangle in triangles:
        back = [list(p) for p in triangle]
        if sum(a*b for a,b in zip(normal(back), outward)) < 0:
            back.reverse()
        front = [[p[i]+thickness*outward[i] for i in range(3)] for p in back]
        faces.extend([front, back[::-1]])
        for a,b in zip(back, back[1:]+back[:1]):
            key = tuple(sorted((_key(a), _key(b))))
            edges.setdefault(key, []).append((a,b))
    for pairs in edges.values():
        if len(pairs) == 1:
            a,b = pairs[0]
            aa = [a[i]+thickness*outward[i] for i in range(3)]
            bb = [b[i]+thickness*outward[i] for i in range(3)]
            faces.append([a,b,bb,aa])
        elif len(pairs) != 2:
            raise ValueError('Nonmanifold finish source polygon')
    return faces


def clip(face, axis, edge, keep_greater):
    """Clip a planar wall contour at a tangent coordinate, retaining holes."""
    if not face:
        return []
    if all((p[axis]>=edge if keep_greater else p[axis]<=edge) for p in face):
        return deepcopy(face)
    result = []
    for a,b in zip(face,face[1:]+face[:1]):
        inside_a = a[axis] >= edge if keep_greater else a[axis] <= edge
        inside_b = b[axis] >= edge if keep_greater else b[axis] <= edge
        if inside_a:
            result.append(list(a))
        if inside_a != inside_b:
            fraction = (edge-a[axis])/(b[axis]-a[axis])
            result.append([a[i]+fraction*(b[i]-a[i]) for i in range(3)])
    if len(result)<3 or max(p[axis] for p in result)-min(p[axis] for p in result)<=1e-9:
        return []
    # Intersecting a keyhole's slit can leave duplicate boundary runs. Repair
    # planar topology before triangulation, never export a nonmanifold notch.
    from shapely.geometry import Polygon, LineString
    from shapely.geometry.polygon import orient
    ring = np.array(face)
    newell = np.cross(ring,np.roll(ring,-1,axis=0)).sum(axis=0)
    dropped = int(np.argmax(np.abs(newell)))
    axes = [i for i in range(3) if i!=dropped]
    projected = [(p[axes[0]],p[axes[1]]) for p in result]
    polygon = Polygon(projected)
    if polygon.is_valid:
        return result
    polygon = polygon.buffer(0)
    if polygon.is_empty:
        return []
    if polygon.geom_type!='Polygon':
        raise ValueError('Finish zone clip has disconnected contours; separate wall zones required')
    signed = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(projected,projected[1:]+projected[:1]))
    polygon = orient(polygon,sign=1 if signed>0 else -1)
    contour = list(polygon.exterior.coords)[:-1]
    for interior in polygon.interiors:
        hole = list(interior.coords)[:-1]
        bridges = [(np.linalg.norm(np.subtract(a,b)),i,j)
                   for i,a in enumerate(contour) for j,b in enumerate(hole)
                   if polygon.covers(LineString([a,b]))]
        if not bridges:
            raise ValueError('Finish zone opening has no visible boundary bridge')
        _,i,j = min(bridges)
        hole = hole[j:]+hole[:j]
        contour = contour[:i+1]+hole+[hole[0],contour[i]]+contour[i+1:]
    result = []
    for a,b in contour:
        p = list(face[0])
        p[axes[0]],p[axes[1]] = a,b
        p[dropped] = (np.dot(newell,face[0])-sum(newell[i]*p[i] for i in axes))/newell[dropped]
        result.append(p)
    return result


def build(scene, room_rectangles):
    """Render every nonzero host finish once over its complete source face.

    Replace the covered source polygon with the solid's back interface: no
    coplanar duplicate remains in the render channel. Duplicate host records
    sharing a face share one layer. Already-built finished stair faces remain
    authoritative and are not offset a second time.
    """
    sources = {m['id']:m for m in scene['meshes']}
    layers = {}
    rooms = {m['finished_host_id']:m['room'] for m in scene.get('diagnostic_meshes', [])
             if m.get('finished_host_id') and m.get('room')}
    plans = []
    for host in scene['mounting_hosts'].values():
        thickness = host['finish']['thickness_m']
        if not thickness:
            continue
        source = sources.get(host.get('source_mesh'))
        if source is None:
            # Stair faces are already built on their finished datum.
            if any(m.get('finished_host_id')==host['id'] for m in scene['meshes']):
                continue
            raise ValueError(host['id']+': MISSING render source for finish layer')
        room = rooms.get(host['id'],source.get('room'))
        if room not in room_rectangles:
            raise ValueError(host['id']+': MISSING finite finish wall zone')
        plans.extend((host,source,face,room,False) for face in host['source_faces'])
        for datum in scene.get('diagnostic_meshes', []):
            if datum.get('finished_host_id') == host['id'] and datum.get('source_mesh') in sources:
                plans.extend((host,sources[datum['source_mesh']],face,room,True)
                             for face in datum['source_faces'])
    finishes = {}
    for host,source,face,room,supplementary in plans:
        key = (source['id'],tuple(_key(p) for p in face))
        finishes.setdefault(key,set()).add((host['finish']['thickness_m'],host['source_material']))
    for host,source,original_face,room,supplementary in plans:
        thickness = host['finish']['thickness_m']
        outward = host['normal']
        axis = 0 if abs(outward[1])>.999999 else 1
        key = (source['id'],tuple(_key(p) for p in original_face))
        # Ordinary hosts cover their complete measured wall zone. Shared
        # shell buckets can span rooms with different finish assemblies;
        # partition those at room limits instead of overlapping two solids.
        # Supplementary coplanar patches cannot extend into unrelated rooms.
        if supplementary or len(finishes[key])>1:
            rect = room_rectangles[room]
            zone_low,zone_high = rect[axis],rect[axis+2]
        else:
            zone_low = min(p[axis] for p in original_face)
            zone_high = max(p[axis] for p in original_face)
        face = clip(clip(original_face,axis,zone_low,True),axis,zone_high,False)
        if not face:
            continue
        key = (source['id'], tuple(_key(p) for p in face), tuple(outward), thickness)
        if key in layers:
            if host['id'] not in layers[key]['finish_host_ids']:
                layers[key]['finish_host_ids'].append(host['id'])
            continue
        layer = dict(id='finish-layer-'+str(len(layers))+'-'+source['id'],
            faces=extrude(face, outward, thickness), group=source['group'],
            material=host['source_material'], room=room,
            part_kind='finish-layer', label='Physical '+host['finish']['name'],
            source_mesh=source['id'], source_faces=[deepcopy(face)],
            source_face=deepcopy(original_face), zone_axis=axis, zone_bounds_m=[zone_low,zone_high],
            thickness_m=thickness, finish_normal=list(outward),
            finish_host_ids=[host['id']], local_axes=['x','y','z'], basis='authored-procedural')
        layers[key] = layer
    for source in sources.values():
        replacement = []
        for face in source['faces']:
            remaining = [face]
            for layer in layers.values():
                if layer['source_mesh']!=source['id'] or layer['source_face']!=face:
                    continue
                axis = layer['zone_axis']
                low,high = layer['zone_bounds_m']
                remaining = [piece for part in remaining
                             for piece in (clip(part,axis,low,False),clip(part,axis,high,True)) if piece]
            replacement.extend(remaining)
        source['faces'] = replacement
    scene['meshes'].extend(layers.values())
    # Empty source buckets have no renderable geometry; records keep their
    # immutable source polygons and layers carry provenance to the source id.
    scene['meshes'] = [m for m in scene['meshes'] if m['faces']]


def surface_findings(scene):
    """Every built nonzero-finish mounting datum must reach render building.

    Project the item's finite geometry onto the host's finished plane. An
    assembly child's wall stand-off is carried by its brackets; it is not
    mistaken for a required body-to-wall contact. Nearest distances use true
    triangles, so bounding boxes cannot certify a fixing across an opening.
    """
    building = [m for m in scene['meshes'] if m.get('group') in ('shell','context')
                and not m.get('diagnostic') and m.get('material') != 'glass-clear']
    triangles, _ = _triangles(building)
    low = triangles.min(axis=1) if len(triangles) else np.empty((0,3))
    high = triangles.max(axis=1) if len(triangles) else np.empty((0,3))
    normals = np.cross(triangles[:,1]-triangles[:,0], triangles[:,2]-triangles[:,0])
    normals /= np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-12)
    failures = []
    for mesh in scene['meshes']:
        contract = mesh.get('mounting', {})
        host = scene.get('mounting_hosts', {}).get(contract.get('host_id'))
        if not host or not host['finish']['thickness_m']:
            continue
        outward = np.array(host['normal'])
        plane = np.array(host['structural_point']) + outward*host['finish']['thickness_m']
        vertices = np.array([p for f in mesh['faces'] for p in f])
        # Host plane point is an arbitrary polygon corner, not the fixing.
        # Use the complete mounting side. A rail or hood can overhang a
        # finite wall patch while its bracket/fixing footprint reaches it.
        gaps = (vertices-plane) @ outward
        fixing = vertices[gaps <= gaps.min()+1e-9]
        fixing = fixing-np.outer((fixing-plane) @ outward, outward)
        distances = []
        # A floor or perpendicular reveal beside a wall fixing does not
        # substitute for the finished wall face itself.
        same_direction = normals @ outward > .999999
        for point in np.unique(fixing, axis=0):
            candidates = triangles[same_direction & np.all(low <= point+SURFACE_TOLERANCE_M, axis=1) &
                                   np.all(high >= point-SURFACE_TOLERANCE_M, axis=1)]
            if len(candidates):
                distances.append(float(_point_triangle_distance(point[None,:], candidates).min()))
        distance = min(distances, default=float('inf'))
        if distance > SURFACE_TOLERANCE_M+1e-9:
            failures.append(mesh['id']+': MISSING render building surface within 2 mm of finished mounting face')
    return failures


def solid_findings(scene):
    """Check watertight oriented edges and outward cap/reveal directions."""
    failures = []
    for mesh in scene['meshes']:
        if not mesh['id'].startswith('finish-layer-'):
            continue
        counts = Counter()
        directions = Counter()
        for face in mesh['faces']:
            for a,b in zip(face,face[1:]+face[:1]):
                aa,bb = _key(a),_key(b)
                counts[tuple(sorted((aa,bb)))] += 1
                directions[(aa,bb)] += 1
        closed = all(v==2 for v in counts.values())
        oriented = all(directions[(a,b)]==directions[(b,a)] for a,b in counts)
        # A closed consistently wound solid has positive signed volume iff
        # its normals point out; subtract an origin to avoid cancellation.
        triangles, _ = _triangles([mesh])
        triangles -= triangles[0,0].copy()
        volume = np.einsum('ij,ij->i',triangles[:,0],np.cross(triangles[:,1],triangles[:,2])).sum()/6
        if not closed or not oriented or volume <= 0:
            failures.append(mesh['id']+': finish solid must be closed with outward normals')
    return failures
