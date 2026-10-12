"""Own lighting instrumentation by the exported task surface.

All positions and distances are metres. A binding names a mesh and one of
its upward faces. The plane follows that face after mounting; offset_m is
an explicit task-plane clearance (reading above seating, or grooming above
a basin), captured from the authored task intent before mounting. Surface
work has zero clearance. Neither lighting output nor a lux target places a
probe. SENSOR_OFFSET and CAMERA_OFFSET retain the existing meter geometry.
"""
from __future__ import annotations

import numpy as np

from .concept.render_support import _triangles

SENSOR_OFFSET = 0.001
CAMERA_OFFSET = 0.025
METER_HALF_WIDTH = 0.005  # central 16 of 32 pixels in the 20 mm camera field
LOCAL_PATH_LENGTH = CAMERA_OFFSET - SENSOR_OFFSET


def _name(point):
    return f"{point['room']}/{point['label']} at {point['position']}"


def _surface(face, x, y):
    """Return height on an upward face's plane; reject tilted task hosts."""
    a, b, c = np.asarray(face[:3], dtype=float)
    normal = np.cross(b - a, c - a)
    length = np.linalg.norm(normal)
    if not np.isfinite(normal).all() or not length or normal[2] / length < 0.9:
        raise ValueError('task host needs an upward surface')
    return float(a[2] - (normal[0]*(x-a[0]) + normal[1]*(y-a[1])) / normal[2])


def author_bindings(scene):
    """Capture explicit item ownership before furniture mounting changes faces.

    Contact tasks bind the nearest upward top face of their declared item,
    including a rim around a sink aperture. Reading/grooming intent retains
    its stated clearance above that actual face. Identity is supplied by the
    task producer; this function never searches other furniture or obstacles.
    """
    for point in scene['measurement_points']:
        item = point['host_item']
        prefix = 'furn-' + item.replace('#', '-') + '-'
        hosts = [m for m in scene['meshes'] if m['id'].startswith(prefix)]
        x, y, nominal = point['position']
        rim = point.get('host_reference') == 'rim'
        candidates = []
        for mesh in hosts:
            for index, face in enumerate(mesh['faces']):
                try:
                    height = _surface(face, x, y)
                except ValueError:
                    continue
                vertices = np.asarray(face)
                # Worktop/rim faces may surround an aperture; use their actual
                # height. Other furniture parts outside the task footprint
                # must never become the datum (e.g. a chair back or a tap).
                if not rim and not (vertices[:, 0].min()-1e-8 <= x <= vertices[:, 0].max()+1e-8 and
                        vertices[:, 1].min()-1e-8 <= y <= vertices[:, 1].max()+1e-8):
                    continue
                if height <= nominal + 1e-7:
                    candidates.append((nominal-height, mesh['id'], index, height))
        if not candidates:
            raise ValueError(_name(point) + ': no upward task surface on ' + item)
        gap, mesh_id, index, height = min(candidates)
        contact = point['card'] not in ('ies-res-chair-reading-200', 'ies-res-bed-reading-200',
                                        'ies-res-vanity-grooming-300')
        if contact and gap > 0.010:
            raise ValueError(_name(point) + ': declared contact surface missing on ' + item)
        point['host_surface'] = dict(mesh_id=mesh_id, face_index=index,
                                     offset_m=0.0 if contact else gap,
                                     authored_plane_m=list(point['position']))


def bind_planes(scene):
    """Derive every exported plane from its actual final host face."""
    meshes = {m['id']: m for m in scene['meshes']}
    for point in scene['measurement_points']:
        binding = point.get('host_surface')
        if not binding:
            raise ValueError(_name(point) + ': missing task host surface ownership')
        try:
            face = meshes[binding['mesh_id']]['faces'][binding['face_index']]
            x, y = point['position'][:2]
            height = _surface(face, x, y)
            point['position'] = [x, y, height + binding['offset_m']]
            binding['surface_height_m'] = height
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ValueError(_name(point) + ': invalid task host ' + str(binding)) from exc


def _hit(triangles, owners, meshes, start, end):
    """Nearest triangle on the open segment, using vector ray arithmetic."""
    if not len(triangles):
        return None
    start, end = np.asarray(start), np.asarray(end)
    delta = end-start
    length = np.linalg.norm(delta)
    if length < 1e-10:
        return None
    direction = delta/length
    edge_one = triangles[:, 1]-triangles[:, 0]
    edge_two = triangles[:, 2]-triangles[:, 0]
    cross = np.cross(direction, edge_two)
    determinant = np.einsum('ij,ij->i', edge_one, cross)
    inverse = np.divide(1, determinant, out=np.zeros_like(determinant),
                        where=abs(determinant)>1e-10)
    offset = start-triangles[:, 0]
    across = np.einsum('ij,ij->i', offset, cross)*inverse
    second_cross = np.cross(offset, edge_one)
    along = second_cross @ direction * inverse
    distance = np.einsum('ij,ij->i', edge_two, second_cross)*inverse
    valid = ((abs(determinant)>1e-10) & (across>=-1e-8) & (along>=-1e-8) &
             (across+along<=1+1e-8) & (distance>=0) & (distance<length-1e-8))
    indices = np.flatnonzero(valid)
    if not len(indices):
        return None
    index = indices[np.argmin(distance[indices])]
    return dict(mesh_id=meshes[int(owners[index])]['id'],
                position_m=(start+direction*distance[index]).tolist())


def require_clear_probes(scene):
    """Refuse hidden meter pixels or local source approaches before rendering.

    The camera looks down onto an upward sensor. Trace all central metered
    pixel centres, and the last 24 mm of source-to-sensor approaches. Remote
    furniture shadows are legitimate lighting transport, not instrumentation
    faults. Every solid, including glass and the declared host, is checked
    irrespective of material, room or object naming.
    """
    points = scene.get('measurement_points', [])
    for point in points:
        binding = point.get('host_surface')
        if not binding:
            raise ValueError(_name(point) + ': missing task host surface ownership')
        if (not np.isfinite(point['position']).all() or
                len(point['position']) != 3 or
                type(binding.get('face_index')) is not int or binding['face_index'] < 0 or
                not np.isfinite(binding.get('offset_m', float('nan'))) or binding['offset_m'] < 0):
            raise ValueError(_name(point) + ': invalid task host binding')
    # Avoid triangulating distant garden meshes; retain any solid whose bounds
    # can intersect the local camera or source segments for any task point.
    meshes = []
    centres = np.asarray([p['position'] for p in points], dtype=float).reshape(-1, 3)
    for mesh in scene['meshes']:
        vertices = np.asarray([v for face in mesh['faces'] for v in face], dtype=float)
        lo, hi = vertices.min(axis=0), vertices.max(axis=0)
        margin = LOCAL_PATH_LENGTH + METER_HALF_WIDTH
        if len(centres) and np.any(np.all((centres >= lo-margin) & (centres <= hi+margin), axis=1)):
            meshes.append(mesh)
    triangles, owners = _triangles(meshes)
    sources = probe_sources(scene)
    for point in points:
        x, y, plane = point['position']
        require_clear_paths([point], sources,
                            lambda start, end: _hit(triangles, owners, meshes, start, end))
        binding = point['host_surface']
        host = next((m for m in scene['meshes'] if m['id'] == binding['mesh_id']), None)
        if host is None:
            raise ValueError(_name(point) + ': missing host ' + binding['mesh_id'])
        expected = _surface(host['faces'][binding['face_index']], x, y)+binding['offset_m']
        if abs(expected-plane) > 1e-8:
            raise ValueError(_name(point) + ': stale plane for host ' + binding['mesh_id'])


def probe_paths(point, sources):
    """Meter-pixel and local source segments, as (description, start, end)."""
    x, y, plane = point['position']
    sensor = np.array([x, y, plane+SENSOR_OFFSET])
    paths = []
    # Match the actual averaged pixel population, not just its centre.
    for dx in (np.arange(16)+0.5-8)*0.02/32:
        for dy in (np.arange(16)+0.5-8)*0.02/32:
            end = sensor + [dx, dy, 0]
            paths.append(('upward view', end+[0, 0, LOCAL_PATH_LENGTH], end))
    for name, source in sources:
        direction = source-sensor
        length = np.linalg.norm(direction)
        if length and direction[2] > 0:
            paths.append(('source '+name, sensor+direction/length*min(length, LOCAL_PATH_LENGTH), sensor))
    return paths


def require_clear_paths(points, sources, first_hit):
    """Use an independent ray provider (including Blender evaluated geometry)."""
    for point in points:
        for path, start, end in probe_paths(point, sources):
            hit = first_hit(start, end)
            if hit:
                raise ValueError(_name(point) + ': ' + path + ' hits ' + hit['mesh_id'] +
                                 ' at ' + str(hit['position_m']) + ' before sensor plane')


def probe_sources(scene):
    """Authored analytic lights and luminous mesh centres, all in metres."""
    sources = [(light['id'], np.asarray(light['position'], dtype=float))
               for light in scene.get('lights', [])]
    for mesh in scene['meshes']:
        if scene.get('materials', {}).get(mesh.get('material'), {}).get('kind') == 'emissive':
            vertices = np.asarray([v for face in mesh['faces'] for v in face], dtype=float)
            sources.append((mesh['id'], (vertices.min(axis=0)+vertices.max(axis=0))/2))
    return sources
