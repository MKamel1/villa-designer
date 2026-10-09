"""Measured bed fit, independent of room identity and translation.

Coordinates and bounds are metres. Native glTF axes are X across, Y up,
Z along the bed; world axes are X/Y horizontal and Z up. Footprint error
is an absolute length, not a percentage. The 20 mm plan and five percent
height limits are the furniture-phase client instruction, not a standard.
"""
from __future__ import annotations

import math

PLAN_TOLERANCE_M = 0.020
HEIGHT_TOLERANCE = 0.05


def _extents(bounds):
    try:
        low, high = bounds['min'], bounds['max']
        if len(low) != 3 or len(high) != 3:
            raise ValueError
        dimensions = [float(b) - float(a) for a, b in zip(low, high)]
        if not all(math.isfinite(v) for v in low + high + dimensions):
            raise ValueError
        if min(dimensions) <= 0:
            raise ValueError
        return dimensions
    except (KeyError, TypeError, ValueError):
        raise ValueError('bed intake requires finite, positive measured bounds') from None


def fit_bed(bounds, width_m, depth_m, overall_height_m, front_axis, length_axis=None):
    """Find one uniform native-to-world scale or reject the fixed envelope.

    Width/depth are the bed's local footprint, independent of room yaw.
    Overall height is the existing headboard/bunk envelope, not mattress top.
    Front axis must have been measured during asset intake.
    """
    native = _extents(bounds)
    targets = (width_m, depth_m, overall_height_m)
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool)
               and math.isfinite(v) and v > 0 for v in targets):
        raise ValueError('bed fit requires positive footprint and overall height')
    if front_axis not in ('+X', '-X', '+Z', '-Z'):
        raise ValueError('bed fit requires a measured horizontal front axis')
    # A bunk's access front can be its long side. Length direction must then
    # be recorded independently; never infer the mattress axis from a ladder.
    length_axis = length_axis or front_axis[-1]
    if length_axis not in ('X', 'Z'):
        raise ValueError('bed length_axis must be measured X or Z')
    width, depth = (native[0], native[2]) if length_axis == 'Z' else (native[2], native[0])
    scale = min(width_m / width, depth_m / depth)
    achieved = (width * scale, depth * scale, native[1] * scale)
    errors = [abs(achieved[0] - width_m), abs(achieved[1] - depth_m),
              abs(achieved[2] / overall_height_m - 1)]
    reasons = []
    for axis, error in zip(('width', 'depth'), errors[:2]):
        if error > PLAN_TOLERANCE_M + 1e-9:
            reasons.append(f'{axis} misses fixed footprint by {error * 1000:.3f} mm (>20 mm)')
    if errors[2] > HEIGHT_TOLERANCE + 1e-9:
        reasons.append(f'overall height {achieved[2]:.6f} m misses {overall_height_m:.6f} m by {errors[2] * 100:.3f}% (>5%)')
    return dict(ok=not reasons, scale=scale, scaled_size_m=list(achieved),
                footprint_error_m=errors[:2], height_err=errors[2],
                reason='scale-distortion: ' + '; '.join(reasons) if reasons else 'fits')


def placed_bed_findings(native_bounds, world_bounds, footprint, reference_height_m,
                        scale, native_to_world_axes=(0, 2, 1)):
    """Recheck actual imported bounds, including isotropy and position.

    World bounds have min/max triples; footprint is minimum X/Y, maximum X/Y.
    The axis tuple identifies which native axis maps to each world axis after
    the measured up/front conversion and room yaw. Compare extents, so native
    origin changes and room translations cannot hide scale distortion.
    """
    native, actual = _extents(native_bounds), _extents(world_bounds)
    if sorted(native_to_world_axes) != [0, 1, 2]:
        raise ValueError('native_to_world_axes must be a permutation of 0, 1, 2')
    if not isinstance(scale, (int, float)) or isinstance(scale, bool) or not math.isfinite(scale) or scale <= 0:
        raise ValueError('scale-distortion: a bed requires one positive uniform scale')
    if len(footprint) != 4 or not all(math.isfinite(v) for v in footprint) or footprint[2] <= footprint[0] or footprint[3] <= footprint[1]:
        raise ValueError('bed requires a finite, positive fixed footprint')
    if not math.isfinite(reference_height_m) or reference_height_m <= 0:
        raise ValueError('bed requires positive reference height')
    findings = []
    expected = [native[i] * scale for i in native_to_world_axes]
    if any(abs(a - b) > 1e-5 for a, b in zip(actual, expected)):
        findings.append('scale-distortion: actual imported extents disagree with one uniform scale')
    for axis in (0, 1):
        for actual_edge, target_edge in ((world_bounds['min'][axis], footprint[axis]),
                                         (world_bounds['max'][axis], footprint[axis + 2])):
            if abs(actual_edge - target_edge) > PLAN_TOLERANCE_M + 1e-9:
                findings.append(f'scale-distortion: world axis {axis} edge misses footprint by more than 20 mm')
                break
    if abs(actual[2] / reference_height_m - 1) > HEIGHT_TOLERANCE + 1e-9:
        findings.append('scale-distortion: overall height misses reference by more than five percent')
    return findings


def bed_items(items):
    """Include conventional beds and daybeds; no villa-specific identifiers."""
    return [item for item in items if item['type'].startswith('bed_') or item['type'] == 'daybed_nook']


def label_fallbacks(meshes, items, replacements=()):
    """Keep rejected/absent-model geometry visible and explicitly labelled."""
    selected = set(replacements)
    for item in bed_items(items):
        if item['id'] in selected:
            continue
        prefix = 'furn-' + item['id'].replace('#', '-') + '-'
        for mesh in meshes:
            if mesh['id'].startswith(prefix):
                # label is also the existing view subject identity. Keep
                # disclosure separate so an appearance status cannot make
                # the bed disappear from its subjects.
                mesh['fallback_label'] = 'PROCEDURAL BED FALLBACK (stand-in): ' + mesh['label']
                mesh['asset_status'] = 'procedural-bed-fallback'


def model_review_meshes(models):
    """Place measured model faces for portable support, routes and doors.

    review_geometry stores actual imported faces in Blender's converted glTF
    metre axes, before the instance's uniform scale, yaw and floor placement.
    The same actual-vertex centring/base rule is used by the Blender importer.
    Beds require these faces; other legacy models retain envelope-only route
    coverage until their own exact geometry receipts are migrated.
    """
    import numpy as np
    result=[]
    for model in models:
        if model.get('status')=='procedural-bed-fallback':
            continue
        geometry=model.get('review_geometry')
        if geometry is None:
            if model.get('role')=='bed':
                raise ValueError(model['id']+': bed requires measured review_geometry')
            continue
        if geometry.get('schema')!='bed-model-geometry/1' or geometry.get('asset')!=model['asset']:
            raise ValueError(model['id']+': invalid model geometry receipt')
        rows=geometry['meshes']
        points=np.asarray([p for row in rows for f in row['faces'] for p in f],float)
        if points.ndim!=2 or points.shape[1]!=3 or not np.isfinite(points).all():
            raise ValueError(model['id']+': invalid actual model vertices')
        scale=model['scale']
        if isinstance(scale,bool) or not isinstance(scale,(int,float)) or not math.isfinite(scale) or scale<=0:
            raise ValueError(model['id']+': model requires one uniform positive scale')
        rotation=model['rotation_deg']
        if tuple(rotation[:2])!=(0,0):
            raise ValueError(model['id']+': bed review supports measured up axis and yaw only')
        yaw=math.radians(rotation[2]);c,s=math.cos(yaw),math.sin(yaw)
        matrix=np.array([[c,-s,0],[s,c,0],[0,0,1]])*scale
        points=points@matrix.T
        low,high=points.min(0),points.max(0)
        offset=np.asarray(model['position'])-[(low[0]+high[0])/2,(low[1]+high[1])/2,low[2]]
        for row in rows:
            faces=[(np.asarray(f)@matrix.T+offset).tolist() for f in row['faces']]
            result.append(dict(id=model['id']+'::'+row['name'],faces=faces,
                group='furniture',material='imported-model',part_kind='model-part',
                room=model.get('room'),label=model.get('label',model['id']),model_instance=model['id']))
    return result


def scene_with_model_geometry(scene):
    """Expand instance faces once, keeping input scene and fallbacks immutable."""
    models=scene.get('models',[])
    faces=model_review_meshes(models)
    active=[m for m in models if m.get('status')!='procedural-bed-fallback']
    prefixes={m.get('replaces') for m in active if m.get('review_geometry') and m.get('replaces')}
    instance_ids={m['id'] for m in active if m.get('review_geometry')}
    meshes=[m for m in scene.get('meshes',[]) if m.get('model_instance') not in instance_ids
            and not any(m['id'].startswith(p) for p in prefixes)]
    return dict(scene,meshes=meshes+faces)


def preview_datums(points):
    """Staging uses actual world vertices, never rotated bounding boxes."""
    import numpy as np
    vertices=np.asarray(points,float)
    if vertices.ndim!=2 or vertices.shape[1]!=3 or not len(vertices) or not np.isfinite(vertices).all():
        raise ValueError('preview requires finite actual vertices')
    low,high=vertices.min(0),vertices.max(0)
    return dict(bounds_m=[low.tolist(),high.tolist()],floor_z_m=float(low[2]-.005),
                figure_foot_z_m=float(low[2]))


def require_bed_geometry(spec, library_root=None):
    """Bind reviewed faces and semantic orientation to unchanged asset bytes.

    Library paths are relative to the asset folder. A pending/rejected neutral
    review cannot activate a replacement. Legacy non-bed models are unaffected.
    """
    from pathlib import Path
    import hashlib
    geometry=spec.get('review_geometry') or {}
    orientation=spec.get('orientation_evidence') or {}
    if (geometry.get('schema')!='bed-model-geometry/1' or geometry.get('asset')!=spec['asset']
            or not geometry.get('meshes') or not geometry.get('source_sha256')):
        raise ValueError(spec['id']+': bed requires measured review_geometry')
    if (orientation.get('front_axis')!=spec.get('front_axis') or not orientation.get('basis')
            or (spec.get('neutral_review') or {}).get('status')!='accepted'):
        raise ValueError(spec['id']+': bed requires measured orientation and accepted neutral review')
    review=spec['neutral_review']
    if (review.get('source_sha256')!=geometry['source_sha256']
            or review.get('orientation_evidence')!=orientation):
        raise ValueError(spec['id']+': neutral review is not bound to measured geometry and orientation')
    if library_root is None:
        return
    root=(Path(library_root)/'props'/spec['asset']).resolve()
    for relative,expected in geometry['source_sha256'].items():
        path=(root/relative).resolve()
        if not path.is_relative_to(root) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError(spec['id']+': stale model geometry receipt: '+relative)


def bind_model_cloth(cloth_specs, model_specs):
    """Every replacement duvet needs its own lower/upper mattress binding.

    The model's replaces prefix identifies the existing bed; head_at_max is
    a measured world-axis direction, never inferred from bunk symmetry.
    """
    result=[]
    for spec in cloth_specs:
        spec=dict(spec)
        for model in model_specs:
            if model.get('role')!='bed' or model.get('status')=='procedural-bed-fallback':
                continue
            mark=model['replaces'].removeprefix('furn-').removesuffix('-')
            if spec['id'] not in ('duvet-'+mark,'duvet-'+mark+'-upper'):
                continue
            key='upper' if spec['id'].endswith('-upper') else 'lower'
            binding=(model.get('mattress_bindings') or {}).get(key)
            if not binding or not binding.get('parts') or type(binding.get('head_at_max')) is not bool:
                raise ValueError(spec['id']+': measured '+key+' mattress binding required')
            spec.update(model_instance=model['id'],mattress_parts=binding['parts'],
                        head_at_max=binding['head_at_max'])
        result.append(spec)
    return result


def mattress_cloth(spec, faces, head_at_max):
    """Cut existing cloth from measured rectangular mattress faces in metres.

    head_at_max states which end of the existing length_axis holds the head.
    The duvet's authored side/foot drops, pin offset, material and physics
    remain in spec. For rounded mattresses, bounds describe the rectangular
    cut; all actual mattress/frame surfaces remain simulation colliders.
    """
    import numpy as np
    points=np.asarray([p for f in faces for p in f],float)
    if points.ndim!=2 or points.shape[1]!=3 or not np.isfinite(points).all():
        raise ValueError('model bedding requires finite actual mattress faces')
    low,high=points.min(0),points.max(0)
    axis=spec['length_axis'];long=0 if axis=='x' else 1;across=1-long
    head,foot=(high[long],low[long]) if head_at_max else (low[long],high[long])
    sign=-1 if head_at_max else 1
    cut=spec['cut'];start=head+sign*cut['head_to_pin_m'];end=foot+sign*cut['foot_overhang_m']
    width=high[across]-low[across]+2*cut['side_overhang_m']
    if width<=0 or (end-start)*sign<=0:
        raise ValueError('actual mattress cannot accommodate authored duvet cut')
    center=[0.,0.];size=[0.,0.]
    center[long]=(start+end)/2;center[across]=(low[across]+high[across])/2
    size[long]=abs(end-start);size[across]=width
    return dict(spec,center=center,size=size,z_start=float(high[2]+.08),
        pin=[axis,float(start),.03],mattress_top=float(high[2]),
        mattress_span=[float(low[long]),float(high[long])],geometry_basis='actual imported mattress faces')
