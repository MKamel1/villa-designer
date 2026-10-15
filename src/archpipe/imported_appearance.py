"""Lead policy 2026-10-13: immutable appearance and closed review bodies.

Coordinates and tolerances are metres. Component connectivity welds only
for grouping at eight decimal places; source vertices are never moved.
Tight boxes use each model's scaled local x/y/z axes, then its measured yaw
and placement. They are conservative review volumes, never render objects.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from collections.abc import Mapping
from functools import lru_cache
import gzip
import math
from pathlib import Path

import numpy as np

POLICY_SOURCE = 'Lead decision 2026-10-13, imported-model admission policy'
APPEARANCE_CLASS = 'imported appearance mesh'
ENCLOSURE_TOLERANCE_M = 0.000010
ROOT = Path(__file__).resolve().parents[2]
LEGACY_RECORD = ROOT/'knowledge/imported-legacy-components.json.gz'


def encoded(value):
    def mapping(item):
        if isinstance(item, Mapping):
            return dict(item)
        raise TypeError('unserializable admission input')
    return json.dumps(value, default=mapping, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def components(faces):
    """Partition all face indices by shared measured vertices, without edits."""
    parent = list(range(len(faces)))
    seen = {}
    def root(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index
    for index, face in enumerate(faces):
        for point in face:
            key = tuple(round(float(v), 8) for v in point)
            if key in seen:
                parent[root(index)] = root(seen[key])
            else:
                seen[key] = index
    groups = {}
    for index in range(len(faces)):
        groups.setdefault(root(index), []).append(index)
    return list(groups.values())


@lru_cache(maxsize=256)
def _bounds_by_value(lengths, coordinates):
    points = np.frombuffer(coordinates, dtype=np.float64).reshape(-1, 3)
    ends = np.cumsum((0,)+lengths)
    faces = [points[start:end] for start, end in zip(ends[:-1], ends[1:])]
    return tuple((tuple(indices), tuple(vertices.min(0)), tuple(vertices.max(0)))
                 for indices in components(faces)
                 for vertices in [np.asarray([p for i in indices for p in faces[i]])])


def _component_bounds(faces):
    # Exact face boundaries and float bytes invalidate cached measurements.
    points = np.asarray([p for f in faces for p in f], dtype=np.float64)
    return _bounds_by_value(tuple(len(f) for f in faces), points.tobytes())


@lru_cache(maxsize=4)
def _legacy_inputs(record_bytes, policy_bytes, manifest_bytes):
    """Parse measurements once per exact file content, never per path/mtime."""
    return (json.loads(gzip.decompress(record_bytes)), json.loads(policy_bytes),
            json.loads(manifest_bytes))


def _legacy_geometry(model):
    record, policy, manifest = _legacy_inputs(LEGACY_RECORD.read_bytes(),
        (ROOT/'knowledge/imported-component-policy.json').read_bytes(),
        (ROOT/'ops/workstation/library-manifest.json').read_bytes())
    if record.get('schema') != 'imported-component-measurements/1' or model['asset'] not in record['assets']:
        raise ValueError(model['id']+': imported appearance has no measured physical stand-in source')
    geometry = record['assets'][model['asset']]
    if geometry.get('component_policy_sha256') != digest(policy):
        raise ValueError(model['id']+': stale imported component decomposition policy')
    entry = next(r for r in manifest['props'] if r['id'] == model['asset'])
    if (geometry['source_sha256']['model.gltf'] != entry['source_sha256'] or
            any(geometry['source_sha256'].get(k) != v for k,v in entry.get('geometry_buffer_sha256', {}).items()) or
            digest(geometry) != entry.get('imported_component_geometry_sha256')):
        raise ValueError(model['id']+': stale imported source/buffer measurements')
    return geometry


def _legacy_transform(model, rows):
    if tuple(model['rotation_deg'][:2]) != (0,0):
        raise ValueError('imported stand-in requires measured up axis and yaw')
    if (isinstance(model['scale'],bool) or not math.isfinite(model['scale']) or model['scale'] <= 0):
        raise ValueError('imported stand-in requires positive measured scale')
    yaw_remainder = model['rotation_deg'][2] % 90
    if min(yaw_remainder,90-yaw_remainder) > 1e-6:
        # Component bounds retain exact orthogonal extrema, but cannot
        # establish the renderer's vertex-derived anchor after an arbitrary
        # yaw. Full review faces are required for that placement.
        raise ValueError(model['id']+': nonorthogonal legacy yaw requires measured review_geometry for its source anchor')
    angle = math.radians(model['rotation_deg'][2]);c,s = math.cos(angle),math.sin(angle)
    matrix = np.asarray([[c,-s,0],[s,c,0],[0,0,1]])*model['scale']
    corners = np.asarray([[x,y,z] for row in rows for part in row['components']
        for x in (part['low'][0],part['high'][0]) for y in (part['low'][1],part['high'][1])
        for z in (part['low'][2],part['high'][2])])@matrix.T
    low,high = corners.min(0),corners.max(0)
    return matrix,np.asarray(model['position'])-[(low[0]+high[0])/2,(low[1]+high[1])/2,low[2]]


def require_legacy_source(model, library_root):
    """Bind portable measurements to actual glTF, buffers and used textures."""
    geometry = _legacy_geometry(model)
    root = (Path(library_root)/'props'/model['asset']).resolve()
    for name, expected in geometry['source_sha256'].items():
        path = (root/name).resolve()
        if (not path.is_relative_to(root) or not path.is_file() or
                hashlib.sha256(path.read_bytes()).hexdigest() != expected):
            raise ValueError(model['id']+': stale imported appearance source: '+name)


def _construct_model(model):
    """Construct the pair by measurement; no appearance mesh is a Part."""
    from .beds import model_transform
    from .concept.physical_part import PartMeshList
    from .concept.villa_render import box_faces
    if model.get('physical_part') is True or model.get('mesh_class') not in (None, APPEARANCE_CLASS):
        raise ValueError(model['id']+': imported appearance mesh cannot be presented as a physical part')
    measured_faces = bool(model.get('review_geometry'))
    geometry = model['review_geometry'] if measured_faces else model['review_component_measurements']
    hashes = geometry.get('source_sha256')
    if not isinstance(hashes, Mapping) or not hashes or any(
            not isinstance(v, str) or len(v) != 64 or any(c not in '0123456789abcdef' for c in v)
            for v in hashes.values()):
        raise ValueError(model['id']+': appearance requires source/buffer hashes')
    if measured_faces:
        rows, matrix, offset = model_transform(model)
    else:
        rows = geometry['meshes']
        matrix, offset = _legacy_transform(model, rows)
    scale = np.linalg.norm(matrix, axis=0)
    rotation = matrix / scale
    parts = PartMeshList()
    appearances = []
    for row in rows:
        identifier = model['id']+'::'+row['name']
        faces = []
        measurements = []
        bounds = (_component_bounds(row['faces']) if measured_faces else
                  [((), part['low'], part['high']) for part in row['components']])
        for number, (indices, low, high) in enumerate(bounds):
            low, high = np.asarray(low)*scale, np.asarray(high)*scale
            # A planar source component needs physical thickness. Only that
            # axis expands; nonzero measured extents remain exactly tight.
            short = high-low < 2*ENCLOSURE_TOLERANCE_M
            low[short] -= ENCLOSURE_TOLERANCE_M
            high[short] += ENCLOSURE_TOLERANCE_M
            local_faces = box_faces(*low, *high)
            start = len(faces)
            faces.extend([(np.asarray(face)@rotation.T+offset).tolist() for face in local_faces])
            measurements.append(dict(source_face_indices=list(indices),
                local_bounds_m=[low.tolist(), high.tolist()], standin_face_start=start,
                standin_face_count=len(local_faces)))
            if not measured_faces:
                measurements[-1].update(source_face_count=row['components'][number]['source_face_count'],
                    source_face_indices_sha256=row['components'][number]['source_face_indices_sha256'])
        face_hash = digest(row['faces']) if measured_faces else row['source_faces_sha256']
        part = dict(id=identifier, faces=faces, material='imported-model', group='furniture',
            part_kind='imported-physical-standin', basis=POLICY_SOURCE,
            local_axes=['x','y','z'], local_frame=dict(rotation=rotation.tolist(), origin_m=offset.tolist()),
            model_instance=model['id'], room=model.get('room'), label=model.get('label', model['id']),
            render=False, components=measurements, source_faces_sha256=face_hash)
        parts.append(part)
        appearances.append(dict(id=identifier, mesh_class=APPEARANCE_CLASS,
            policy_source=POLICY_SOURCE, physical_part=False, render=True,
            source_sha256=dict(hashes), source_faces_sha256=face_hash,
            source_placement_sha256=digest(dict(source_faces_sha256=face_hash,
                matrix=matrix.tolist(),offset=offset.tolist())),
            standin_id=identifier, standin_sha256=digest(part),
            enclosure_tolerance_m=ENCLOSURE_TOLERANCE_M))
    return appearances, parts


@lru_cache(maxsize=32)
def _cached_pair(input_sha256, model_bytes):
    # Construction admits the physical parts once. Cache their canonical
    # serialized value; the C JSON reader clones large face-index tables
    # without millions of Python deepcopy calls on unchanged scalar leaves.
    return encoded(_construct_model(json.loads(model_bytes)))


def _binary_model_input(model):
    """Exact finite-float face buffers plus canonical remaining JSON fields.

    This is only an internal value key. Every face boundary/order and every
    unrounded 64-bit coordinate bit is retained. Integer, boolean, string or
    other coordinate types use the original canonical JSON path so its source
    face hash cannot be aliased by numeric conversion. Source records are never
    mutated, and every non-face field remains in the complete canonical key.
    """
    geometry=model.get('review_geometry')
    if not isinstance(geometry,Mapping) or not isinstance(geometry.get('meshes'),(list,tuple)):
        return None
    rows=[];buffers=[]
    for row in geometry['meshes']:
        faces=row.get('faces')
        if not isinstance(faces,(list,tuple)):return None
        points=[p for face in faces for p in face]
        if not all(len(p)==3 and type(p[0]) is float and type(p[1]) is float and type(p[2]) is float for p in points):
            return None
        array=np.asarray(points,dtype='<f8')
        if not np.isfinite(array).all():return None
        buffers.append((tuple(len(f) for f in faces),array.tobytes()))
        rows.append(dict(row,faces=None))
    metadata=dict(model,review_geometry=dict(geometry,meshes=rows))
    return encoded(metadata),tuple(buffers)


@lru_cache(maxsize=32)
def _cached_binary_pair(metadata_bytes,buffers):
    model=json.loads(metadata_bytes)
    for row,(lengths,coordinates) in zip(model['review_geometry']['meshes'],buffers):
        points=np.frombuffer(coordinates,dtype='<f8').reshape(-1,3)
        ends=np.cumsum((0,)+lengths)
        row['faces']=[points[a:b].tolist() for a,b in zip(ends[:-1],ends[1:])]
    return encoded(_construct_model(model))


def build_model(model):
    """Reuse only byte-identical inputs; callers own independent pair records."""
    if not model.get('review_geometry'):
        model = dict(model, review_component_measurements=_legacy_geometry(model))
    binary=_binary_model_input(model)
    if binary is not None:
        appearance,physical=json.loads(_cached_binary_pair(*binary))
    else:
        model_bytes = encoded(model)
        appearance, physical = json.loads(_cached_pair(hashlib.sha256(model_bytes).hexdigest(), model_bytes))
    return appearance, physical


def build_pairs(models):
    appearances, parts = [], []
    for model in models:
        if model.get('status') == 'procedural-bed-fallback':
            continue
        if not model.get('review_geometry') and (model.get('role') == 'bed' or model.get('furniture_fitting')):
            raise ValueError(model['id']+': measured review_geometry required')
        appearance, physical = build_model(model)
        appearances.extend(appearance)
        parts.extend(physical)
    return appearances, parts


def bind_scene(scene):
    appearance, parts = build_pairs(scene.get('models', []))
    scene['imported_appearances'] = appearance
    scene['physical_model_meshes'] = parts
    scene['imported_admission_policy'] = POLICY_SOURCE
    return scene


def with_models(scene, models):
    """Author a new selection atomically, retaining strict incoming admission.

    A source scene's pairs certify its old model list. Validate those pairs
    before selecting; construct the new pairs from the new authored list.
    Select on authored scenes, before physical expansion. Expanded meshes
    would retain orphan colliders when a model is removed.
    """
    bound = any(k in scene for k in
            ('imported_appearances', 'physical_model_meshes', 'imported_admission_policy'))
    if needs_scene_admission(scene) and bound:
        require_scene(scene)
    selected = list(models)
    if not bound or not isinstance(scene.get('physical_model_meshes'), list):
        return bind_scene(dict(scene, models=selected))
    # Reuse only models that are the exact incoming objects just validated.
    # New objects (even with matching IDs) require complete source construction.
    # Copy pairs so a new selection cannot mutate the admitted source scene.
    appearances, parts = [], []
    old = {m['id']:m for m in scene.get('models', [])}
    by_model = {}
    by_part = {a['standin_id']:a for a in scene['imported_appearances']}
    for part in scene['physical_model_meshes']:
        by_model.setdefault(part['model_instance'], []).append(part)
    for model in selected:
        if model.get('status') == 'procedural-bed-fallback':
            continue
        if model is old.get(model['id']):
            # Incoming JSON pair values have just passed complete admission.
            # Clone their canonical values in the C decoder; Python recursive
            # deepcopy repeatedly walks the large immutable face-index tables.
            physical = json.loads(encoded(by_model.get(model['id'], [])))
            appearance = json.loads(encoded([by_part[p['id']] for p in physical]))
        else:
            appearance, physical = build_pairs([model])
        appearances.extend(appearance)
        parts.extend(physical)
    return dict(scene, models=selected, imported_appearances=appearances,
                physical_model_meshes=parts, imported_admission_policy=POLICY_SOURCE)


def has_imported_rows(scene):
    """Recognize orphaned imports even when their pair metadata was stripped."""
    rows = scene.get('meshes', [])
    return isinstance(rows, (list, tuple)) and any(isinstance(row, Mapping) and (
        row.get('mesh_class') == APPEARANCE_CLASS or
        row.get('part_kind') == 'imported-physical-standin')
        for row in rows)


def needs_scene_admission(scene):
    return bool(scene.get('models')) or has_imported_rows(scene) or any(
        key in scene for key in ('imported_appearances', 'physical_model_meshes', 'imported_admission_policy'))


def require_scene(scene, *, physical_review=False):
    """Validate actual exported pairs, strict solids and source containment.

    Reconstructing the tight measured bodies also rejects an oversized or
    misplaced stand-in even if its own digest has been recomputed.
    """
    from .concept.physical_part import PartMeshList
    expected_appearance, expected_parts = build_pairs(scene.get('models', []))
    if any(m.get('mesh_class') == APPEARANCE_CLASS or
           (m.get('part_kind') == 'imported-physical-standin' and not physical_review)
           for m in scene.get('meshes', [])):
        raise ValueError('imported appearance and physical stand-ins must stay outside rendered authored parts')
    if (scene.get('imported_admission_policy') != POLICY_SOURCE or
            digest(scene.get('imported_appearances')) != digest(expected_appearance) or
            digest(scene.get('physical_model_meshes')) != digest(expected_parts)):
        raise ValueError('imported appearance missing, stale or non-enclosing physical stand-in')
    PartMeshList().extend(scene['physical_model_meshes'])
    for part in scene['physical_model_meshes']:
        if part.get('render') is not False:
            raise ValueError(part['id']+': physical stand-in must never render')
    return scene['physical_model_meshes']


def physical_meshes(scene):
    if has_imported_rows(scene) or any(k in scene for k in ('imported_appearances','physical_model_meshes','imported_admission_policy')):
        return require_scene(scene, physical_review=True)
    # Internal review inputs construct their pair before any physical query.
    return build_pairs(scene.get('models', []))[1]
