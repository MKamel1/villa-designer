"""Own lighting instrumentation by the exported task surface.

All positions and distances are metres. A binding names a mesh and one of
its upward faces. The plane follows that face after mounting; offset_m is
an explicit task-plane clearance (reading above seating, or grooming above
a basin), captured from the authored task intent before mounting. Surface
work has zero clearance. Neither lighting output nor a lux target places a
probe. SENSOR_OFFSET and CAMERA_OFFSET retain the existing meter geometry.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache

import numpy as np

from .concept.render_support import _triangles

SENSOR_OFFSET = 0.001
CAMERA_OFFSET = 0.025
METER_HALF_WIDTH = 0.005  # central 16 of 32 pixels in the 20 mm camera field
LOCAL_PATH_LENGTH = CAMERA_OFFSET - SENSOR_OFFSET
SEARCH_STEP = 0.005  # instrument sampling resolution, not a design requirement


@lru_cache(maxsize=None)
def _cached_area_citation(card_id):
    from .guidance import library
    card = library()['evidence'][card_id]
    if card.get('status') != 'verified' or not card.get('original_page_checked'):
        raise ValueError('unverified task area: ' + card_id)
    return dict(card=card_id, source_id=card['source_id'], edition=card['edition'],
                locator=card['locator'], conditions=card['conditions'])


def _area_citation(card_id):
    return deepcopy(_cached_area_citation(card_id))


def probe_position(point):
    """Effective instrument position; the authored target stays in position."""
    return point.get('measurement_position', point['position'])


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
        if contact and not rim:
            point['host_surface']['task_area'] = dict(
                citation=_area_citation(point['card']),
                extent='finite owning host face', decision='lead 2026-10-11')


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
    centres = np.asarray([probe_position(p) for p in points], dtype=float).reshape(-1, 3)
    for mesh in scene['meshes']:
        vertices = np.asarray([v for face in mesh['faces'] for v in face], dtype=float)
        lo, hi = vertices.min(axis=0), vertices.max(axis=0)
        margin = LOCAL_PATH_LENGTH + METER_HALF_WIDTH
        if len(centres) and np.any(np.all((centres >= lo-margin) & (centres <= hi+margin), axis=1)):
            meshes.append(mesh)
    triangles, owners = _triangles(meshes)
    sources = probe_sources(scene)
    for point in points:
        x, y, plane = probe_position(point)
        require_clear_paths([point], sources,
                            lambda start, end: _hit(triangles, owners, meshes, start, end))
        binding = point['host_surface']
        host = next((m for m in scene['meshes'] if m['id'] == binding['mesh_id']), None)
        if host is None:
            raise ValueError(_name(point) + ': missing host ' + binding['mesh_id'])
        face = host['faces'][binding['face_index']]
        if 'measurement_position' in point:
            record = binding.get('surface_search', {})
            if (not np.isfinite(probe_position(point)).all() or
                    record.get('nominal_position_m') != point['position'] or
                    record.get('measurement_position_m') != probe_position(point) or
                    not np.allclose(np.asarray(probe_position(point))-point['position'],
                                    record.get('offset_m', [float('nan')]*3), atol=1e-10, rtol=0) or
                    binding.get('offset_m') != 0 or
                    binding.get('task_area', {}).get('citation') != _area_citation(point['card']) or
                    not all(_inside_face(face, x+dx, y+dy)
                            for dx in (-METER_HALF_WIDTH, METER_HALF_WIDTH)
                            for dy in (-METER_HALF_WIDTH, METER_HALF_WIDTH))):
                raise ValueError(_name(point) + ': invalid surface search record')
        expected = _surface(face, x, y)+binding['offset_m']
        if abs(expected-plane) > 1e-8:
            raise ValueError(_name(point) + ': stale plane for host ' + binding['mesh_id'])


def probe_paths(point, sources):
    """Meter-pixel and local source segments, as (description, start, end)."""
    x, y, plane = probe_position(point)
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


def _inside_face(face, x, y):
    """Finite polygon containment in the horizontal projection, edges included."""
    inside = False
    for a, b in zip(face, face[1:] + face[:1]):
        delta = np.asarray(b[:2])-a[:2]
        relative = np.array([x, y])-a[:2]
        cross = delta[0]*relative[1]-delta[1]*relative[0]
        if abs(cross) < 1e-10 and np.dot(relative, delta) >= -1e-10 and np.dot(relative, delta) <= np.dot(delta, delta)+1e-10:
            return True
        if (a[1] > y) != (b[1] > y) and x < a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]):
            inside = not inside
    return inside


def resolve_surface_probes(scene, first_hit, solid_bounds):
    """Select the nearest clear sampled position on the SAME finite host face.

    Return copied points, never change authored targets or scene objects. The
    nominal point is tested first; clean points are unchanged. Only contact
    tasks covered by a foreign object resting on their host may search. The
    lattice is anchored to the nominal point, spaced 5 mm, ordered by squared
    distance, then signed x and y indices. All metered paths must be clear and
    all four meter footprint corners must remain on the cited task surface.
    Exhausting its finite area fails closed. No lux reading guides the search.
    solid_bounds returns measured world-space minimum/maximum coordinates.
    """
    points = deepcopy(scene['measurement_points'])
    meshes = {m['id']: m for m in scene['meshes']}
    sources = probe_sources(scene)

    def obstruction(point):
        for path, start, end in probe_paths(point, sources):
            hit = first_hit(start, end)
            if hit:
                return dict(path=path, hit=hit)
        return None

    for point in points:
        # Always start from the nominal binding, including on repeated calls.
        point.pop('measurement_position', None)
        binding = point['host_surface']
        binding.pop('surface_search', None)
        blocked = obstruction(point)
        if not blocked:
            continue
        face = meshes[binding['mesh_id']]['faces'][binding['face_index']]
        x, y, plane = point['position']
        area = binding.get('task_area')
        if (not area or area.get('citation') != _area_citation(point['card']) or
                area.get('extent') != 'finite owning host face' or binding['offset_m'] != 0 or
                abs(_surface(face, x, y)-plane) > 1e-8):
            raise ValueError(_name(point) + ': obstruction has no cited contact task area')
        hit = blocked['hit']
        lo, hi = np.asarray(solid_bounds(hit['mesh_id']), dtype=float)
        # The existing 1 mm sensor clearance bounds contact uncertainty; this
        # cannot admit an overhead obstacle or a host hiding its own sensor.
        if (hit['mesh_id'] == binding['mesh_id'] or not np.isfinite([lo, hi]).all() or
                abs(lo[2]-plane) > SENSOR_OFFSET or
                not (lo[0] <= x <= hi[0] and lo[1] <= y <= hi[1]) or
                not _inside_face(face, x, y)):
            raise ValueError(_name(point) + ': obstructing object is not resting on task host')
        vertices = np.asarray(face)
        low = np.ceil((vertices[:, :2].min(axis=0)-[x,y])/SEARCH_STEP).astype(int)
        high = np.floor((vertices[:, :2].max(axis=0)-[x,y])/SEARCH_STEP).astype(int)
        candidates = sorted((i*i+j*j, i, j) for i in range(low[0], high[0]+1)
                            for j in range(low[1], high[1]+1) if i or j)
        attempts = [dict(offset_m=[0.,0.,0.], obstruction=blocked)]
        for distance, i, j in candidates:
            cx, cy = x+i*SEARCH_STEP, y+j*SEARCH_STEP
            if not all(_inside_face(face, cx+dx, cy+dy)
                       for dx in (-METER_HALF_WIDTH, METER_HALF_WIDTH)
                       for dy in (-METER_HALF_WIDTH, METER_HALF_WIDTH)):
                continue
            cz = _surface(face, cx, cy)
            point['measurement_position'] = [cx, cy, cz]
            hit = obstruction(point)
            attempts.append(dict(offset_m=[i*SEARCH_STEP, j*SEARCH_STEP, cz-plane], obstruction=hit))
            if not hit:
                binding['surface_search'] = dict(
                    nominal_position_m=list(point['position']),
                    measurement_position_m=list(point['measurement_position']),
                    offset_m=attempts[-1]['offset_m'], distance_m=float(np.linalg.norm(attempts[-1]['offset_m'])),
                    pattern='nominal-anchored square lattice; increasing squared distance; signed x then y index',
                    step_m=SEARCH_STEP, nearest='nearest clear tested lattice point',
                    task_area=deepcopy(area), original_obstruction=blocked,
                    resting_object_bounds_m=[lo.tolist(), hi.tolist()], attempts=attempts)
                break
        else:
            raise ValueError(_name(point) + ': no unobstructed point within cited task area ' + str(area))
    return points


def probe_sources(scene):
    """Authored analytic lights and luminous mesh centres, all in metres."""
    sources = [(light['id'], np.asarray(light['position'], dtype=float))
               for light in scene.get('lights', [])]
    for mesh in scene['meshes']:
        if scene.get('materials', {}).get(mesh.get('material'), {}).get('kind') == 'emissive':
            vertices = np.asarray([v for face in mesh['faces'] for v in face], dtype=float)
            sources.append((mesh['id'], (vertices.min(axis=0)+vertices.max(axis=0))/2))
    return sources
