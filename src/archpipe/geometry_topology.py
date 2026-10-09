"""Read-only relationships over authored layout and measured scene geometry.

Lengths and model coordinates are metres, with x/y horizontal and z upward.
A bounds tuple is (minimum x, minimum y, minimum z, maximum x, maximum y,
maximum z); a rectangle is (minimum x, minimum y, maximum x, maximum y).
Source identifiers name the input record, never a catalogue substitute.
Exact asset triangles, finished mounting faces, and the existing route and
support engines remain authoritative. No layout or scene is built or moved.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from types import MappingProxyType
from collections.abc import Mapping

import numpy as np
from .units import mm_to_m


def _freeze(value):
    if isinstance(value, MappingProxyType):
        return value
    if isinstance(value, Mapping):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    return value


def _thaw(value):
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return value


def _faces(faces):
    if isinstance(faces, tuple):
        return faces
    return tuple(tuple(tuple(float(v) for v in p) for p in f) for f in faces)


def bounds_of(faces):
    points = np.array([p for f in faces for p in f], dtype=float)
    if points.size == 0 or points.shape[1:] != (3,) or not np.isfinite(points).all():
        raise ValueError('Topology requires finite measured vertices')
    return tuple(points.min(axis=0)) + tuple(points.max(axis=0))


def rectangle_overlap(a, b, tolerance=0.001):
    """Positive overlap on both axes, retaining the caller's numeric tolerance."""
    return min(a[2], b[2])-max(a[0], b[0]) > tolerance and min(a[3], b[3])-max(a[1], b[1]) > tolerance


def overlap_area(a, b):
    return max(0, min(a[2], b[2])-max(a[0], b[0])) * max(0, min(a[3], b[3])-max(a[1], b[1]))


@dataclass(frozen=True)
class Requirement:
    value: float | None
    source: str
    unit: str = 'm'
    needs_source: bool = False

    def __post_init__(self):
        if not self.source or (self.value is not None and not math.isfinite(self.value)):
            raise ValueError('Requirement needs provenance and a finite figure')

    @classmethod
    def card(cls, identifier):
        # Reuse the held verified card, including its applicability and edition.
        from .guidance import library
        data = library()
        row = data['evidence'][identifier]
        if not row.get('original_page_checked') or row.get('status') != 'verified':
            return cls(None, 'knowledge/library.json#'+identifier, needs_source=True)
        value = row['verified_value']
        if row['unit'] == 'mm':
            value = mm_to_m(value)
        elif row['unit'] != 'm':
            raise ValueError('Length query requires a length evidence card')
        return cls(value, identifier+'; '+row['edition']+'; '+row['locator']+'; '+row['conditions'])


@dataclass(frozen=True)
class Finding:
    query: str
    source_id: str
    reference_id: str
    achieved: float | None
    required: float | None
    source: str
    unit: str = 'm'
    status: str = 'fail'
    detail: str = ''


def _finding(query, source_id, reference, achieved, requirement, detail=''):
    return Finding(query, source_id, reference, achieved, requirement.value,
                   requirement.source, requirement.unit,
                   'needs-source' if requirement.needs_source else 'fail', detail)


@dataclass(frozen=True)
class Host:
    source_id: str
    kind: str
    finished_faces: tuple
    bounds: tuple
    normal: tuple | None = None
    room: str | None = None
    structural_source_id: str | None = None


@dataclass(frozen=True)
class Opening:
    source_id: str
    kind: str
    envelope: tuple  # Rectangles occupied by swing or slide, not route nodes.
    clear_route: tuple  # Route source identifiers on both sides, even for pockets.
    clear_width_m: float
    rooms: tuple
    level: str
    motion_basis: str
    ground_m: float | None = None
    top_m: float | None = None


@dataclass(frozen=True)
class Obstacle:
    source_id: str
    kind: str
    bounds: tuple
    faces: tuple = ()
    record: object = None
    accessory_to: str | None = None


@dataclass(frozen=True)
class Support:
    source_id: str
    object_id: str
    host_id: str | None
    contact: tuple
    kind: str
    offset_m: float | None
    source: str


@dataclass(frozen=True)
class Route:
    source_id: str
    rect: tuple
    ground_m: float
    top_m: float
    clear_width: Requirement
    kind: str = 'walk'
    endpoints: tuple = ()
    achieved_width_m: float | None = None


@dataclass(frozen=True)
class GeometryTopology:
    hosts: tuple[Host, ...] = ()
    openings: tuple[Opening, ...] = ()
    obstacles: tuple[Obstacle, ...] = ()
    supports: tuple[Support, ...] = ()
    routes: tuple[Route, ...] = ()
    layout: object = None
    scene: object = None
    specification: object = None
    furniture: tuple = ()

    @classmethod
    def from_inputs(cls, *, layout=None, scene=None, specification=None, furniture=(),
                    items=(), routes=None, route_ground=None):
        """Snapshot existing inputs, never call a design/scene builder.

        Rect-only legacy landscape objects retain the original conservative
        walking-height policy. Imported assets use their measured library
        bounds; walking collision uses asset_route_record through route_geometry.
        Unknown furniture types are retained as obstacles.
        """
        from .concept import villa_landscape as landscape
        from .concept import villa_furnish as furnishing
        scene = _freeze(scene)
        hosts, openings, obstacles, supports, paths = [], [], [], [], []
        if scene is not None:
            for identifier, row in scene.get('mounting_hosts', {}).items():
                outward = tuple(row['normal'])
                thickness = row['finish']['thickness_m']
                faces = _faces([[[p[i]+thickness*outward[i] for i in range(3)] for p in f]
                                for f in row.get('source_faces', [])])
                if not faces:
                    # Stair and legacy C4 hosts store their actual finished
                    # polygons in diagnostics, rather than source_faces. These
                    # faces already include finish: never apply it twice.
                    plane = tuple(row['structural_point'][i]+thickness*outward[i] for i in range(3))
                    faces = tuple(f for mesh in tuple(scene.get('diagnostic_meshes', ()))+tuple(scene.get('meshes', ()))
                                  if mesh.get('finished_host_id') == identifier for f in mesh['faces']
                                  if all(abs(sum((p[i]-plane[i])*outward[i] for i in range(3))) < 1e-8 for p in f))
                if not faces:
                    raise ValueError(identifier+': missing finite finished host faces')
                hosts.append(Host(identifier, 'stair' if row['kind'] == 'stair-stringer' else row['kind'], faces, bounds_of(faces), outward,
                                  structural_source_id=row.get('source_mesh', identifier)))
            for mesh in scene.get('meshes', ()):
                faces = _faces(mesh['faces'])
                if mesh.get('diagnostic') or not faces:
                    continue
                bb = bounds_of(faces)
                if mesh['group'] in ('shell', 'context'):
                    # The built faces already include finish layers; no second offset.
                    kind = ('stair' if 'stair' in mesh['id'] else
                            'ceiling' if mesh.get('material') == 'ceiling-white' else
                            'floor' if str(mesh.get('part_kind', '')).startswith(('floor', 'stepping')) or mesh.get('material') in ('floor-oak', 'floor-stone', 'paving', 'lawn') else
                            'wall' if mesh.get('part_kind') == 'finish-layer' else 'slab')
                    hosts.append(Host(mesh['id'], kind, faces, bb, room=mesh.get('room')))
                elif mesh['group'] in ('furniture', 'fixture', 'dressing'):
                    obstacles.append(Obstacle(mesh['id'], mesh.get('part_kind', mesh['group']), bb,
                                              faces, _freeze(mesh)))
                contract = mesh.get('mounting')
                if contract:
                    host = next((h for h in hosts if h.source_id == contract.get('host_id') and h.normal), None)
                    contact = _faces([contract['fixing_footprint']]) if contract.get('fixing_footprint') else ()
                    if host and not contact:
                        points = tuple(p for f in faces for p in f)
                        signed = [sum((p[i]-host.finished_faces[0][0][i])*host.normal[i] for i in range(3)) for p in points]
                        minimum = min(signed)
                        contact = (tuple(p for p, gap in zip(points, signed) if gap <= minimum+1e-9),)
                    supports.append(Support(mesh['id'], mesh['id'], contract.get('host_id'),
                        contact,
                        contract['kind'], contract.get('offset_m'), 'C4 mounting record'))
                elif mesh.get('support'):
                    supports.append(Support(mesh['id'], mesh['id'], None, tuple(mesh['support']),
                                            'physical-part', None, 'physical_part.Part.support'))
            items = tuple(items) + tuple(scene.get('props', ()))
        for item in items:
            if 'asset' in item and item['asset'] in landscape.PROP_BOUNDS:
                bb = landscape.prop_world_box(item['asset'], item['position'], item.get('rotation_deg', [0,0,0]), item.get('scale', 1.0))
            elif 'asset' in item:
                # Assets known only to the route-geometry record (no PROP_BOUNDS
                # entry) take their extent from the same placed walking triangles
                # route collision uses (integration review 2026-10-08).
                # An asset in neither table fails closed in recorded_geometry
                # (ValueError naming the generator remedy).
                from .concept.route_geometry import prop_triangles
                placed = prop_triangles(item).reshape(-1, 3)
                bb = (*placed.min(axis=0), *placed.max(axis=0))
            elif 'faces' in item:
                bb = bounds_of(item['faces'])
            else:
                rect = item['rect']
                # No fabricated height: unspecified rects are the legacy full walking band.
                bb = (rect[0], rect[1], item.get('bottom_m', -math.inf), rect[2], rect[3], item.get('top_m', math.inf))
            if 'rect' in item:
                rect = item['rect']
                bb = (rect[0], rect[1], bb[2], rect[2], rect[3], bb[5])
            obstacles.append(Obstacle(item['id'], item.get('part_kind', 'prop' if 'asset' in item else 'legacy-rectangle'),
                                      tuple(bb), _faces(item.get('faces', ())), _freeze(item), item.get('accessory_to')))
            if item.get('mounting') or item.get('support_id'):
                contract = item.get('mounting', {})
                supports.append(Support(item['id'], item['id'], contract.get('host_id', item.get('support_id')),
                    tuple(item.get('position', ())), contract.get('kind', 'resting'), contract.get('offset_m'), 'C4 plant support'))
        for item in furniture:
            rect = furnishing.footprint(item)
            if not layout or item['room'] not in layout['rooms']:
                raise ValueError(item['id']+': missing room datum')
            from .concept.revit_spec import LEVELS_Z
            ground = LEVELS_Z[item['level']]
            obstacles.append(Obstacle(item['id'], item['type'], (rect[0], rect[1], ground, rect[2], rect[3], ground+item['h']),
                                      record=_freeze(item), accessory_to=item.get('accessory_to')))
        if routes:
            for name, rect in routes.items():
                ground = (route_ground or {}).get(name, landscape.TOP_SURFACE if name in ('study', 'gate-link') else landscape.GROUND)
                paths.append(Route(name, tuple(rect), ground, ground+2.0,
                    Requirement(min(rect[2]-rect[0], rect[3]-rect[1]), 'authored route rectangle'),
                    endpoints=(name,), achieved_width_m=min(rect[2]-rect[0],rect[3]-rect[1])))
        if specification is not None:
            from .concept.revit_spec import LEVELS_Z
            route_requirement = Requirement.card('mitton-path-of-travel-min')
            for index, door in enumerate(specification.get('doors', ())):
                identifier = door.get('id', 'door:'+str(index)+':'+('/'.join(door.get('rooms') or [])))
                # Existing envelope and approach ownership/direction policies are reused.
                mini = dict(specification, doors=[door])
                approaches = furnishing._door_approaches(mini, layout, door['level']) if layout else []
                zones = furnishing._door_zones(mini, layout, door['level']) if layout else []
                route_ids = []
                for side, approach in enumerate(approaches):
                    name = identifier+':approach:'+str(side)
                    route_ids.append(name)
                    ground = LEVELS_Z[door['level']]
                    paths.append(Route(name, tuple(approach['rect']), ground, ground+2.0,
                                       route_requirement, 'door-to-door', tuple(door.get('rooms') or []), door['width']))
                openings.append(Opening(identifier, 'door', tuple(tuple(z['rect']) for z in zones), tuple(route_ids),
                    door['width'], tuple(door.get('rooms') or []), door['level'],
                    'villa_furnish._door_zones; conservative swing squares/slide approach; not measured leaf sweep',
                    LEVELS_Z[door['level']], LEVELS_Z[door['level']]+door['height']))
            for index, window in enumerate(specification.get('windows', ())):
                openings.append(Opening(window.get('id', 'window:'+str(index)), 'window', (), (), window['width'],
                    (window.get('room'),), window['level'], 'Window motion envelope absent from input: needs-source'))
        if layout:
            from .concept.revit_spec import LEVELS_Z
            for name, room in layout['rooms'].items():
                for index, end in enumerate(room.get('ends', ())):
                    axis, line, low, high = end
                    rect = (line, low, line, high) if axis == 'v' else (low, line, high, line)
                    ground = LEVELS_Z.get(room['level'], 0)
                    paths.append(Route(name+':end:'+str(index), rect, ground, ground+2,
                        Requirement(.8, 'villa.critique: 0.9 m flight matching tolerance 0.8 m; project topology policy'), 'stair-access', (name,), high-low))
        return cls(tuple(hosts), tuple(openings), tuple(obstacles), tuple(supports), tuple(paths),
                   _freeze(layout), _freeze(scene), _freeze(specification), _freeze(furniture))

    def object_in_route(self):
        """Exact triangle/walking-volume query; no full canopy approximation.

        Achieved is the overlap of broad extents in square metres, accompanying
        an exact triangle collision verdict. It is not the remaining path width.
        Zero overlap is a physical exclusion policy, not an ergonomic threshold.
        """
        from .concept.route_geometry import prop_triangles
        from .concept.render_support import _triangles, _tri_box_overlap
        out = []
        for obstacle in self.obstacles:
            record = _thaw(obstacle.record) if obstacle.record is not None else {}
            triangles = prop_triangles(record) if 'asset' in record else None
            bb = obstacle.bounds
            rect = (bb[0], bb[1], bb[3], bb[4])
            candidates = [r for r in self.routes if overlap_area(rect, r.rect) > 1e-6]
            if not candidates:
                continue
            if obstacle.faces and triangles is None:
                triangles, _ = _triangles([{'faces': obstacle.faces}])
            for route in candidates:
                if 'asset' in record:
                    prop_triangles(record, walking_top_m=route.top_m)
                low = np.array([route.rect[0], route.rect[1], route.ground_m])
                high = np.array([route.rect[2], route.rect[3], route.top_m])
                if triangles is not None:
                    nearby = np.all(triangles.min(axis=1) <= high, axis=1) & np.all(triangles.max(axis=1) >= low, axis=1)
                    blocked = nearby.any() and _tri_box_overlap(triangles[nearby], (low+high)/2, (high-low)/2).any()
                else:
                    blocked = bb[2] < high[2] and bb[5] > low[2]
                if blocked:
                    out.append(_finding('object-in-route', obstacle.source_id, route.source_id, overlap_area(rect, route.rect),
                        Requirement(0, 'villa_landscape.route_violations: physical exclusion; 1e-6 m2 numeric intersection tolerance', 'm2'),
                        'Walking band '+str(route.ground_m)+'..'+str(route.top_m)+' m; width basis: '+route.clear_width.source))
        return out

    def swing_envelope_vs_obstacle(self):
        out = []
        for opening in self.openings:
            for rect in opening.envelope:
                for obstacle in self.obstacles:
                    bb = obstacle.bounds
                    if opening.ground_m is not None and opening.top_m is not None and (bb[2] >= opening.top_m or bb[5] <= opening.ground_m):
                        continue
                    area = overlap_area(rect, (bb[0], bb[1], bb[3], bb[4]))
                    if obstacle.source_id != opening.source_id and area > 1e-6:
                        out.append(_finding('swing-envelope-vs-obstacle', obstacle.source_id, opening.source_id, area,
                            Requirement(0, opening.motion_basis, 'm2', 'ASSUMED' in opening.motion_basis)))
        return out

    def access_zone_findings(self, parent_id, rect, requirement):
        """Intent exempts an accessory only from its parent's access zone.

        Body collisions and unrelated route exclusions never use that exemption.
        The achieved figure is occupied horizontal area, not a guessed free width.
        """
        out = []
        for obstacle in self.obstacles:
            if obstacle.source_id == parent_id or obstacle.accessory_to == parent_id:
                continue
            bounds = obstacle.bounds
            area = overlap_area(rect, (bounds[0],bounds[1],bounds[3],bounds[4]))
            if area > 1e-6:
                out.append(_finding('access-zone-obstruction', obstacle.source_id, parent_id, area,
                    Requirement(0, requirement.source+'; exclude occupied area of access zone', 'm2', requirement.needs_source)))
        return out

    def object_overlaps(self):
        """Measured body overlap, with no accessory exemptions (1 mm tolerance)."""
        out = []
        for index, first in enumerate(self.obstacles):
            for second in self.obstacles[index+1:]:
                overlap = tuple(min(first.bounds[i+3],second.bounds[i+3])-max(first.bounds[i],second.bounds[i]) for i in range(3))
                if min(overlap) > .001:
                    out.append(_finding('body-overlap', first.source_id, second.source_id, min(overlap),
                        Requirement(0, 'villa_furnish._ov: physical body exclusion; 1 mm numeric contact tolerance')))
        return out

    def needs_source_findings(self):
        out = []
        for opening in self.openings:
            if 'needs-source' in opening.motion_basis:
                out.append(_finding('opening-motion', opening.source_id, 'measured motion envelope', None,
                    Requirement(None, opening.motion_basis, needs_source=True)))
        for route in self.routes:
            if route.clear_width.needs_source:
                out.append(_finding('route-width', route.source_id, 'required clear width', min(route.rect[2]-route.rect[0],route.rect[3]-route.rect[1]), route.clear_width))
        return out

    def unsupported_floating(self):
        """Reuse island/grounded-component support (no circular self-support).

        Numeric output is the frozen bounds' bottom elevation; the existing
        engine's verdict is contact-based, not a made-up nearest-distance limit.
        Missing contact is measured as zero grounded contacts against one.
        """
        from .concept.render_support import unsupported
        if self.scene is None:
            raise ValueError('Support query requires actual scene faces')
        return [_finding('unsupported/floating', identifier, 'building-grounded support chain', 0,
                        Requirement(1, 'render_support.unsupported: one grounded contact path; rest/hanging comparison 12 mm, building fixing comparison 15 mm, touching parts comparison 10 mm; pre-registered 2026-09-27', 'contacts'), str(box))
                for identifier, box in unsupported(self.scene)]

    def object_penetrating_host(self, object_id=None, host_id=None):
        """Signed penetration into the named finished host (not an infinite wall).

        Reuse C4 finite polygon ownership. A plane outside its real face cannot
        become a host. Recessed housings retain their existing C4 exception.
        """
        from .concept.mounting import _on_polygon, FACE_TOLERANCE_M
        hosts = {h.source_id: h for h in self.hosts if h.normal}
        out = []
        for obstacle in self.obstacles:
            record = obstacle.record or {}
            contract = record.get('mounting', {})
            if object_id is not None and obstacle.source_id != object_id:
                continue
            host = hosts.get(host_id or contract.get('host_id'))
            if not host or contract.get('kind') == 'recessed':
                continue
            gaps = []
            geometry = obstacle.faces
            if not geometry:
                low, high = obstacle.bounds[:3], obstacle.bounds[3:]
                geometry = (tuple((x,y,z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])),)
            for face in geometry:
                for point in face:
                    for surface in host.finished_faces:
                        signed = sum((point[i]-surface[0][i])*host.normal[i] for i in range(3))
                        projected = tuple(point[i]-signed*host.normal[i] for i in range(3))
                        if _on_polygon(projected, surface, host.normal):
                            gaps.append(signed)
            if gaps and min(gaps) < -FACE_TOLERANCE_M-1e-9:
                out.append(_finding('object-penetrating-host', obstacle.source_id, host.source_id, min(gaps),
                    Requirement(0, 'C4 mounting finished-face contact; mounting.FACE_TOLERANCE_M=1 mm comparison tolerance')))
        return out

    def headroom(self, route_id, samples, requirement):
        """Vertical rays from supplied route floor/pitch-line sample points.

        Samples are measured (x,y,z) on the route or pitch line, never tread
        tops substituted for it. Exact host triangles interpolate sloped faces.
        Sampling extent/resolution remains the caller's declared responsibility.
        """
        from .concept.render_support import _triangles
        triangles, _ = _triangles([{'faces': h.finished_faces} for h in self.hosts])
        best = math.inf
        for x, y, z in samples:
            for triangle in triangles:
                a, b, c = triangle
                denominator = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
                if abs(denominator) < 1e-12:
                    continue
                first = ((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/denominator
                second = ((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/denominator
                third = 1-first-second
                top = first*a[2]+second*b[2]+third*c[2]
                if min(first, second, third) >= -1e-9 and top > z+1e-9:
                    best = min(best, top-z)
        if requirement.needs_source or requirement.value is None:
            return [_finding('headroom', route_id, 'overhead hosts', best if math.isfinite(best) else None, requirement)]
        return [_finding('headroom', route_id, 'overhead hosts', best, requirement)] if best < requirement.value else []

    def passage_obstructions(self):
        """Reuse the existing connected-part door and doorless passage policy.

        The 5 mm comparison, 0.6..1.6 m passage recognition and exclusions
        remain the existing diagnostic policy, not new architectural standards.
        An actual saved specification is supplied so historical openings cannot
        be replaced by the current generator while being reviewed.
        """
        from .concept.render_support import blocked_openings
        if self.scene is None or self.layout is None or self.specification is None:
            raise ValueError('Passages require scene, layout and existing specification')
        return [_finding('passage-obstruction', identifier, opening, 0,
                         Requirement(1, 'render_support.blocked_openings: one passable opening; 5 mm numeric overlap policy', 'passable openings'))
                for identifier, opening in blocked_openings(self.scene, _thaw(self.layout), specification=_thaw(self.specification))]

    def occupied_room_intrusions(self):
        """Reuse garden-level ownership and measured full-extent policy.

        These are declared occupied rooms, not invented solid wall hosts.
        The reported value is horizontal overlap area, with the actual object's
        height eligibility retained by extent_violations (including level B).
        """
        from .concept import villa_landscape as landscape
        if self.layout is None:
            raise ValueError('Room intrusions require layout ownership')
        records = [_thaw(o.record) for o in self.obstacles if o.record is not None and 'asset' in o.record]
        rooms = landscape.garden_level_rooms(self.layout)
        legacy = landscape.extent_violations(records, rooms)
        out = []
        by_id = {o.source_id:o for o in self.obstacles}
        for identifier, message in legacy:
            if 'garden-level room' not in message and 'building footprint' not in message:
                continue
            bb = by_id[identifier].bounds
            rect = bb[0],bb[1],bb[3],bb[4]
            references = rooms if 'garden-level room' in message else tuple((*r, 'GF occupied footprint') for r in landscape.BUILDING_RECTS)
            for *area, name in references:
                achieved = overlap_area(rect, area)
                if achieved > 1e-6:
                    out.append(_finding('occupied-room-intrusion', identifier, name, achieved,
                        Requirement(0, 'villa_landscape.extent_violations; physical exclusion of full measured extent from occupied room', 'm2'), message))
                    break
        return out

    def opening_host_collisions(self):
        """Opening-width loss against parallel-cut walls; same door axis policy."""
        from .concept import villa_furnish as furnishing
        if self.specification is None:
            raise ValueError('Opening query requires the existing specification')
        specification = _thaw(self.specification)
        out = []
        for index, door in enumerate(specification['doors']):
            horizontal = furnishing._door_axis(door) == 'h'
            width = door['width']/2
            rect = (door['x']-width, door['y']-.01, door['x']+width, door['y']+.01) if horizontal else (door['x']-.01, door['y']-width, door['x']+.01, door['y']+width)
            for index_wall, wall in enumerate(furnishing._walls(specification, door['level'])):
                if rectangle_overlap(rect, wall):
                    lost = min(rect[2],wall[2])-max(rect[0],wall[0]) if horizontal else min(rect[3],wall[3])-max(rect[1],wall[1])
                    out.append(_finding('opening-penetrating-host', 'door:'+str(index)+':'+('/'.join(door.get('rooms') or [])),
                        door['level']+':wall-piece:'+str(index_wall), door['width']-lost,
                        Requirement(door['width'], 'Authored opening clear width; villa_furnish doors check; 1 mm numeric overlap tolerance'),
                        'door %s runs %d mm into a wall' % ('/'.join(door.get('rooms') or []), round(lost*1000))))
        return out

    def hall_route_clearance(self):
        """Existing stair-top-to-corridor raster, evaluated on saved void geometry."""
        from .concept.villa import gf_route_width
        if self.layout is None or self.specification is None:
            raise ValueError('Hall route requires layout and saved specification')
        achieved = gf_route_width(_thaw(self.layout), specification=_thaw(self.specification))
        return self.clearance_from_fixed_reference('stair-top to corridor-end', 'walls/void/balustrade',
                                                   achieved, Requirement.card('ukadm-hall-min-m42'))

    def room_connectivity(self):
        """Reuse the concept's actual built-door graph, not intended adjacency."""
        from .concept import critic, layout as room_layout
        if self.layout is None:
            raise ValueError('Connectivity requires a layout')
        layout = _thaw(self.layout)
        out = []
        for level in layout['levels']:
            _, _, unbuilt = room_layout.openings(layout, level)
            for first, second in unbuilt:
                out.append(_finding('unbuilt-link', first, second, 0,
                    Requirement(1, 'concept.layout.openings: one physically placed opening per intended link', 'openings')))
        graph = critic.layout_graph(layout)
        for check in critic.graph_checks(graph):
            if check['check'] == 'reachability':
                for room in check['rooms']:
                    out.append(_finding('room-reachability', room, graph['entrance'], 0,
                        Requirement(1, 'concept.critic.graph_checks: each room reachable by the built graph', 'reachable rooms')))
        return out

    def module_run_overflow(self):
        """Modules fill their authored run within existing 1 mm sum tolerance."""
        out = []
        for item in self.furniture:
            if not item.get('modules'):
                continue
            achieved = sum(width for _, width in item['modules'])
            if abs(achieved-item['w']) > 1e-3:
                out.append(_finding('module-run-fill', item['id'], 'authored run', achieved,
                    Requirement(item['w'], 'villa_furnish kitchen check: authored run width; 1 mm sum tolerance'),
                    'Difference '+str(achieved-item['w'])+' m'))
        return out

    def element_against_wrong_host(self, object_id, intended_host_id):
        """Compare explicit intended host with recorded host; no inferred intent."""
        found = [s for s in self.supports if s.object_id == object_id]
        if not found or any(s.host_id != intended_host_id for s in found):
            return [_finding('element-against-wrong-host', object_id, intended_host_id,
                sum(s.host_id == intended_host_id for s in found),
                Requirement(1, 'Explicit intended host supplied by caller; identity relationship', 'matching hosts'))]
        return []

    def clearance_from_fixed_reference(self, object_id, reference_id, achieved_m, requirement):
        """Caller supplies a measured gap to a fixed face/edge, never a room label."""
        if requirement.needs_source or requirement.value is None or achieved_m < requirement.value:
            return [_finding('clearance-from-fixed-reference', object_id, reference_id, achieved_m, requirement)]
        return []

    def stair_end_access(self):
        from .concept import villa
        from . import vocabulary as vocab
        if self.layout is None:
            raise ValueError('Stair access requires the layout')
        rooms = self.layout['rooms']
        out = []
        for identifier, room in rooms.items():
            if room['occupancy'] != 'stair':
                continue
            if not room.get('ends'):
                out.append(_finding('stair-end-access', identifier, 'declared ends', 0,
                    Requirement(1, 'villa.critique: stair ends must be declared', 'declarations'), 'ends not declared'))
                continue
            for end in room['ends']:
                across = [name for name, other in rooms.items() if name != identifier and other['level'] == room['level']
                          and max(villa.overlap_len(e, end) for e in villa.edges(other['rect'])) >= .8]
                matches = [name for name in across if rooms[name]['occupancy'] in vocab.CIRCULATION]
                if not matches:
                    out.append(_finding('stair-end-access', identifier, repr(tuple(end)), len(matches),
                        Requirement(1, 'villa.critique: each end opens onto circulation; 0.8 m shared-edge matching for 0.9 m flight', 'circulation neighbours'),
                        repr({'stair': identifier, 'end': list(end), 'opens_onto': across or ['nothing']})))
        return out

    def legacy_stair_ends(self):
        import ast
        return [dict(stair=f.source_id, problem='ends not declared') if f.detail == 'ends not declared'
                else ast.literal_eval(f.detail) for f in self.stair_end_access()]

    def furnished_routes(self, level, cell=.02, room_ids=None):
        """Same disc-distance raster, half-open floor and meaningful node overlap.

        Preserve its public messages. A disconnected destination supplies a
        count measurement (0 reached, 1 required), not an invented bottleneck.
        """
        from .concept.villa_furnish import _route_problems
        if self.layout is None or self.specification is None:
            raise ValueError('Routes require a layout and existing specification')
        legacy = _route_problems(_thaw(self.layout), _thaw(self.specification), _thaw(self.furniture), level, cell, room_ids)
        return [_finding('route-connectivity', problem, level, 0,
                         Requirement(1, 'villa_furnish.route_problems; mitton-path-of-travel-min; ukadm-bedroom-route-750; private dressing project waiver (pending)', 'reached destinations'), problem)
                for problem, _ in legacy]

    @staticmethod
    def stair_headroom(stair_mm, opening_mm):
        """Reuse the independent pitch-line engine; one mm-to-m boundary."""
        from .concept.stairs import pitch_headroom
        achieved, position = pitch_headroom(stair_mm, opening_mm)
        requirement = Requirement.card('ukadk-stair-headroom-min')
        return [_finding('headroom', stair_mm['name'], 'slab soffit/beams', mm_to_m(achieved), requirement,
                         'Pitch-line sample x='+str(mm_to_m(position))+' m')] if mm_to_m(achieved) < requirement.value else []


def landscape_route_findings(items, routes, route_ground=None):
    # Preserve public validation order and errors before the read-only adapter.
    from .concept.route_geometry import prop_triangles
    from .concept.villa_landscape import _rect
    items = tuple(items)
    for item in items:
        if 'asset' in item:
            prop_triangles(item)
        _rect(item)
    return GeometryTopology.from_inputs(items=items, routes=routes, route_ground=route_ground).object_in_route()


def stair_access_findings(layout):
    return GeometryTopology.from_inputs(layout=layout).stair_end_access()


def support_findings(scene):
    return GeometryTopology.from_inputs(scene=scene).unsupported_floating()


def pitch_headroom_findings(stair_mm, opening_mm):
    return GeometryTopology.stair_headroom(stair_mm, opening_mm)
