"""Real-size bed acceptance, source units and measured mattress datums.

Client decision 2026-10-08: 20 mm per mattress plan dimension. The frame
may overhang; its room clearances are reviewed separately by C8 (geometry
topology). Native glTF uses metres and Y up; reviewed faces use Z up.
"""
from __future__ import annotations

import math

PLAN_TOLERANCE_M = 0.020
CLIENT_SOURCE = 'Client bed fit decision 2026-10-08'


def _extents(bounds):
    try:
        low, high = list(bounds['min']), list(bounds['max'])
        if len(low) != 3 or len(high) != 3:
            raise ValueError
        dimensions = [float(b) - float(a) for a, b in zip(low, high)]
        if not all(math.isfinite(v) for v in low + high + dimensions) or min(dimensions) <= 0:
            raise ValueError
        return dimensions
    except (KeyError, TypeError, ValueError):
        raise ValueError('bed intake requires finite, positive measured bounds') from None


def unit_scale(unit_evidence=None):
    """Only source-declared units convert; absent evidence means glTF metres.

    A non-metre declaration needs a source stating the unit, not an inferred
    factor from a target size. The factor is computed here, never supplied.
    """
    evidence = unit_evidence or {'unit': 'm', 'source': 'glTF 2.0 coordinate system and units'}
    factors = {'m': 1., 'cm': .01, 'mm': .001, 'ft': .3048, 'in': .0254}
    if evidence.get('unit') not in factors or not evidence.get('source'):
        raise ValueError('bed unit conversion requires a source stating m, cm, mm, ft or in')
    return factors[evidence['unit']]


def real_size_findings(scale, unit_evidence=None):
    if isinstance(scale, bool) or not isinstance(scale, (int, float)) or not math.isfinite(scale) or scale <= 0:
        raise ValueError('scale-distortion: a bed requires one positive source-unit scale')
    expected = unit_scale(unit_evidence)
    return ([] if abs(scale - expected) <= 1e-12 else
            [f'scale-distortion: scaled bed refused; scale {scale:.12g}, source-unit conversion {expected:.12g}; {CLIENT_SOURCE}'])


def fit_bed(bounds, width_m, depth_m, overall_height_m, front_axis, length_axis=None,
            *, mattress_bounds=None, scale=1., unit_evidence=None, required_berths=1):
    """Validate actual mattresses at real size, never solve for a fit scale.

    bounds is the complete retained frame in native axes. mattress_bounds is
    a mapping of berth names to actual mattress bounds in those same axes.
    overall_height_m is retained for caller compatibility; it is no longer
    an acceptance limit. Frame height/overhang require room topology review.
    """
    native = _extents(bounds)
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0
               for v in (width_m, depth_m)):
        raise ValueError('bed fit requires positive planned mattress dimensions')
    if front_axis not in ('+X', '-X', '+Z', '-Z'):
        raise ValueError('bed fit requires a measured horizontal front axis')
    length_axis = length_axis or front_axis[-1]
    if length_axis not in ('X', 'Z'):
        raise ValueError('bed length_axis must be measured X or Z')
    if required_berths not in (1, 2):
        raise ValueError('bed requires one or two measured berths')
    reasons = real_size_findings(scale, unit_evidence)
    factor = unit_scale(unit_evidence)
    width, depth = (native[0], native[2]) if length_axis == 'Z' else (native[2], native[0])
    measurements = {}
    if not mattress_bounds or len(mattress_bounds) != required_berths:
        reasons.append('actual mattress geometry required for every berth')
    else:
        for name, box in mattress_bounds.items():
            dimensions = _extents(box)
            achieved = [dimensions[0 if length_axis == 'Z' else 2] * factor,
                        dimensions[2 if length_axis == 'Z' else 0] * factor]
            errors = [abs(a-b) for a,b in zip(achieved,(width_m,depth_m))]
            measurements[name] = dict(size_m=achieved, error_m=errors)
            for axis, a, target, error in zip(('width','length'), achieved, (width_m,depth_m), errors):
                if error > PLAN_TOLERANCE_M + 1e-9:
                    reasons.append(f'{name} mattress {axis}: achieved {a:.6f} m, planned {target:.6f} m, mismatch {error*1000:.3f} mm (>20 mm); {CLIENT_SOURCE}')
    return dict(ok=not reasons, scale=factor, real_size_m=[width*factor,depth*factor,native[1]*factor],
                mattresses=measurements, reason='; '.join(reasons) if reasons else 'real-size mattress fits',
                source=CLIENT_SOURCE)


def placed_bed_findings(native_bounds, world_bounds, footprint, reference_height_m,
                        scale, native_to_world_axes=(0, 2, 1), *, mattress_world_bounds=None,
                        unit_evidence=None):
    """Check frame isotropy and mattress size/centre after actual import.

    footprint is the planned mattress rectangle (minimum X/Y, maximum X/Y).
    reference_height_m is historical and imposes no frame height limit.
    Frame edges may extend outside that rectangle; C8 checks their effects.
    """
    native, actual = _extents(native_bounds), _extents(world_bounds)
    if sorted(native_to_world_axes) != [0, 1, 2]:
        raise ValueError('native_to_world_axes must be a permutation of 0, 1, 2')
    findings = real_size_findings(scale, unit_evidence)
    if len(footprint) != 4 or not all(math.isfinite(v) for v in footprint) or footprint[2] <= footprint[0] or footprint[3] <= footprint[1]:
        raise ValueError('bed requires a finite, positive planned mattress footprint')
    expected = [native[i]*unit_scale(unit_evidence) for i in native_to_world_axes]
    if any(abs(a-b) > 1e-5 for a,b in zip(actual, expected)):
        findings.append('scale-distortion: actual imported extents disagree with one uniform scale from source units')
    if not mattress_world_bounds:
        findings.append('actual imported mattress bounds required')
    for name, box in (mattress_world_bounds or {}).items():
        dimensions = _extents(box)
        for axis in (0, 1):
            planned = footprint[axis+2]-footprint[axis]
            if abs(dimensions[axis]-planned) > PLAN_TOLERANCE_M + 1e-9:
                findings.append(f'{name} mattress axis {axis}: achieved {dimensions[axis]:.6f} m, planned {planned:.6f} m; {CLIENT_SOURCE}')
            centre = (box['min'][axis]+box['max'][axis])/2
            if abs(centre-(footprint[axis]+footprint[axis+2])/2) > 1e-5:
                findings.append(f'{name} mattress centre moved from planned axis {axis} datum')
    return findings


def retained_model_rows(model):
    """Omit only explicitly reviewed, separately named accessory meshes."""
    rows = model['review_geometry']['meshes']
    names = [r['name'] for r in rows]
    omitted = model.get('omitted_meshes', [])
    review = model.get('contents_review') or {}
    if len(names) != len(set(names)) or len(omitted) != len(set(omitted)) or not set(omitted) <= set(names):
        raise ValueError('bed mesh names/omissions must be unique and measured')
    if model.get('role') == 'bed':
        if review.get('status') != 'bed-only' or not review.get('basis'):
            raise ValueError('bed-only contents review required; inseparable tables, benches and rugs refused')
        if set(review.get('extras', [])) != set(omitted):
            raise ValueError('every accessory must be a separable omitted mesh')
    retained = [r for r in rows if r['name'] not in omitted]
    if not retained:
        raise ValueError('bed has no retained meshes')
    return retained


def model_transform(model):
    """One placement transform shared by portable review and Blender.

    Mattress plan centre stays at position X/Y; retained frame bottom seats
    at position Z. Yaw preserves the measured head direction and head wall.
    Non-bed models retain their historical whole-model centre convention.
    """
    import numpy as np
    rows = retained_model_rows(model)
    scale = model['scale']
    if model.get('role') == 'bed':
        findings = real_size_findings(scale, model.get('unit_evidence'))
        if findings:
            raise ValueError('; '.join(findings))
    if isinstance(scale,bool) or not isinstance(scale,(int,float)) or not math.isfinite(scale) or scale<=0:
        raise ValueError('model requires one uniform positive scale')
    if tuple(model['rotation_deg'][:2]) != (0,0):
        raise ValueError('bed review supports measured up axis and yaw only')
    yaw = math.radians(model['rotation_deg'][2]); c,s = math.cos(yaw), math.sin(yaw)
    matrix = np.array([[c,-s,0],[s,c,0],[0,0,1]])*scale
    points = np.asarray([p for r in rows for f in r['faces'] for p in f],float)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError('invalid actual model vertices')
    points = points@matrix.T
    low,high = points.min(0),points.max(0)
    centre = (low+high)/2
    if model.get('role') == 'bed':
        bindings = model.get('mattress_bindings') or {}
        if set(bindings) != ({'lower','upper'} if model.get('required_berths',1)==2 else {'lower'}):
            raise ValueError('actual mattress binding required for every berth')
        centres = []
        for binding in bindings.values():
            names = binding.get('parts') or []
            if not names or not set(names) <= {r['name'] for r in rows} or type(binding.get('head_at_max')) is not bool:
                raise ValueError('measured retained mattress parts and head direction required')
            mattress = np.asarray([p for r in rows if r['name'] in names for f in r['faces'] for p in f])@matrix.T
            centres.append((mattress.min(0)+mattress.max(0))/2)
        centre = centres[0]
        if any(np.max(np.abs(p[:2]-centre[:2]))>1e-5 for p in centres[1:]):
            raise ValueError('bunk mattress centres disagree; fixed layout cannot align both')
    offset = np.asarray(model['position'])-[centre[0],centre[1],low[2]]
    return rows, matrix, offset


def model_mattress_bounds(model, *, world=False):
    """Measure named mattress faces; return native glTF or placed world bounds."""
    import numpy as np
    rows,matrix,offset = model_transform(model)
    result = {}
    for name,binding in model['mattress_bindings'].items():
        points = np.asarray([p for r in rows if r['name'] in binding['parts'] for f in r['faces'] for p in f])
        if world:
            points = points@matrix.T+offset
        else:
            points = points[:,[0,2,1]].copy(); points[:,2] *= -1
        result[name] = dict(min=points.min(0).tolist(),max=points.max(0).tolist())
    return result


def model_native_bounds(model):
    """Bounds of retained actual frame faces in native glTF axes."""
    import numpy as np
    rows, _, _ = model_transform(model)
    points = np.asarray([p for row in rows for face in row['faces'] for p in face])[:,[0,2,1]].copy()
    points[:,2] *= -1
    return dict(min=points.min(0).tolist(),max=points.max(0).tolist())


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
    axes, before source-unit conversion, yaw and floor placement. Mattress
    centring and the retained frame floor datum also drive Blender import.
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
        rows, matrix, offset = model_transform(model)
        for row in rows:
            faces=[(np.asarray(f)@matrix.T+offset).tolist() for f in row['faces']]
            result.append(dict(id=model['id']+'::'+row['name'],faces=faces,
                group='furniture',material='imported-model',part_kind='model-part',
                room=model.get('room'),label=model.get('label',model['id']),model_instance=model['id']))
    return result


def bed_frame_items(scene, furniture):
    """Review-only frame envelopes; preserve layout/mattress and other items.

    The route solver consumes these measured frames instead of planned
    mattress rectangles. Actual C8 collision/support still uses every face.
    """
    import numpy as np
    if not furniture:
        return []
    replacements = {}
    for model in scene.get('models',[]):
        if model.get('role')!='bed' or model.get('status')=='procedural-bed-fallback':
            continue
        mark = model['replaces'].removeprefix('furn-').removesuffix('-')
        rows,matrix,offset = model_transform(model)
        points = np.asarray([p for r in rows for f in r['faces'] for p in f])@matrix.T+offset
        replacements[mark] = (points.min(0),points.max(0))
    result = []
    for item in furniture:
        if item['id'] not in replacements:
            result.append(dict(item)); continue
        low,high = replacements[item['id']]
        width,depth = high[0]-low[0],high[1]-low[1]
        if item['rot'] in (-90,90):
            width,depth = depth,width
        result.append(dict(item,cx=float((low[0]+high[0])/2),cy=float((low[1]+high[1])/2),
            w=float(width),d=float(depth),h=float(high[2]-low[2]),geometry_basis='real retained bed frame'))
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
    # Diagnostic staging choice, not a bed-size or physical contact tolerance.
    gap=min(.005,float((high-low).max())*.0025)
    if gap <= 0:
        raise ValueError('preview requires a positive actual extent')
    return dict(bounds_m=[low.tolist(),high.tolist()],floor_z_m=float(low[2]-gap),staging_gap_m=gap,
                figure_foot_z_m=float(low[2]))


def preview_clip_range(points, camera_position, camera_target):
    """Construct clipping planes from actual camera-space vertex depths.

    All positions are in metres. The direction points from the camera to
    its target; depth is each vertex's distance along that direction.
    Geometry behind the camera cannot supply an honest isolated preview.
    """
    import numpy as np
    vertices = np.asarray(points, float)
    camera = np.asarray(camera_position, float)
    direction = np.asarray(camera_target, float) - camera
    if (vertices.ndim != 2 or vertices.shape[1] != 3 or not len(vertices)
            or camera.shape != (3,) or direction.shape != (3,)
            or not all(np.isfinite(a).all() for a in (vertices, camera, direction))
            or np.linalg.norm(direction) == 0):
        raise ValueError('preview clipping requires finite vertices and a camera direction')
    depths = (vertices - camera) @ (direction / np.linalg.norm(direction))
    if depths.min() <= 0:
        raise ValueError('isolated preview has vertices behind its camera')
    return dict(clip_start_m=float(depths.min() * .5),
                clip_end_m=float(depths.max() * 1.1))


def preview_neutral_light(points):
    """Construct a diagnostic square emitter entirely above its subjects.

    Span is the longest measured extent in metres, including any figure.
    The emitter centre is one span above the highest vertex. Its square
    side is 0.75 span; even a tilted corner stays above all subjects.
    Power scales with span squared to retain comparable diagnostic fill.
    These ratios are staging choices, not design lighting specifications.
    """
    import numpy as np
    datums=preview_datums(points)
    low,high=np.asarray(datums['bounds_m'])
    centre=(low+high)/2
    span=float((high-low).max())
    size=.75*span
    position=[float(centre[0]+.5*span),float(centre[1]+.75*span),float(high[2]+span)]
    return dict(position_m=position,target_m=centre.tolist(),size_m=size,
                power_watts=500*(span/2)**2,
                minimum_emitter_z_bound_m=position[2]-size/math.sqrt(2))


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
    actual_bounds = model_native_bounds(spec)
    if spec.get('native_bounds') and any(abs(a-b)>1e-5 for key in ('min','max')
            for a,b in zip(actual_bounds[key],spec['native_bounds'][key])):
        raise ValueError(spec['id']+': native bounds must measure retained bed meshes after omissions')
    mattresses = model_mattress_bounds(spec)
    if not spec.get('native_bounds') or not spec.get('planned_mattress_m'):
        raise ValueError(spec['id']+': real-size planned mattress contract required')
    width, depth = spec['planned_mattress_m']
    fit = fit_bed(spec['native_bounds'], width, depth, None, spec['front_axis'],
        spec.get('length_axis'), mattress_bounds=mattresses, scale=spec['scale'],
        unit_evidence=spec.get('unit_evidence'), required_berths=spec.get('required_berths',1))
    if not fit['ok']:
        raise ValueError(spec['id']+': '+fit['reason'])
    # Omissions and mattress selection change what was reviewed even with identical files.
    selection = dict(omitted_meshes=spec.get('omitted_meshes',[]),
        mattress_bindings=spec['mattress_bindings'],unit_evidence=spec.get('unit_evidence'))
    if review.get('selection') != selection:
        raise ValueError(spec['id']+': neutral review is not bound to retained bed/mattress selection and units')
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


def bed_room_review(scene, layout, specification, furniture):
    """C8 real-frame report, preserving every authored item and room.

    C8 is the geometry-topology review. Its collision measures may be area,
    gap or reached destinations; shortfall uses the same unit, never pretends
    a route count or overlap area measures remaining passage width. Clearance
    strips below report metres achieved versus the held card's required value.
    Wardrobe/drawer fronts use the existing storage-front clearance card;
    actual animated drawer/leaf travel needs its own measured motion receipt.
    """
    from dataclasses import asdict
    from .geometry_topology import GeometryTopology, Finding, Requirement
    from .concept import villa_furnish as furnishing
    from . import catalogue
    reviewed = bed_frame_items(scene,furniture)
    topology = GeometryTopology.from_inputs(scene=scene,layout=layout,
        specification=specification,furniture=furniture)
    baseline = GeometryTopology.from_inputs(scene=dict(scene,models=[m for m in scene.get('models',[]) if m.get('role')!='bed']),
        layout=layout,specification=specification,furniture=furniture)
    findings = []
    for query in (topology.unsupported_floating,topology.object_in_route,
                  topology.swing_envelope_vs_obstacle,topology.passage_obstructions,
                  topology.occupied_room_intrusions,topology.object_overlaps):
        old={(f.query,f.source_id,f.reference_id,f.achieved,f.required) for f in getattr(baseline,query.__name__)()}
        for finding in query():
            # Parts of the same manufactured bed intentionally touch/intersect.
            if finding.query=='body-overlap' and '::' in finding.source_id and finding.source_id.split('::')[0]==finding.reference_id.split('::')[0]:
                continue
            if (finding.query,finding.source_id,finding.reference_id,finding.achieved,finding.required) not in old:
                findings.append(finding)
    for level in sorted({it['level'] for it in reviewed}):
        old={f.source_id for f in baseline.furnished_routes(level)}
        findings.extend(f for f in topology.furnished_routes(level) if f.source_id not in old)
    active_marks = {m['replaces'].removeprefix('furn-').removesuffix('-') for m in scene.get('models',[])
                    if m.get('role')=='bed' and m.get('status')!='procedural-bed-fallback'}
    originals = {it['id']:it for it in furniture}
    clearances = []
    checks = ['support','routes','door swings','passages','body collisions','room boundaries','bedside access','storage fronts']
    for item in reviewed:
        # Check beds and every storage front a growing bed can obstruct.
        if item['id'] not in active_marks and item['type'] not in ('wardrobe','chest_drawers'):
            continue
        if item['id'] not in active_marks and not any(
                other['id'] in active_marks and furnishing._ov(furnishing.side_zone(item,'front',.914),furnishing.footprint(other))
                for other in reviewed):
            continue
        kind = catalogue.get(item['type'])
        card = ('tss-front-of-storage-914' if item['type'] in ('wardrobe','chest_drawers') else
                'ukadm-bed-principal-750' if item['type'] in ('bed_double','bed_king') else
                'ukadm-bed-other-double-750' if item['type']=='bed_double_other' else 'ukadm-bed-single-750')
        requirement = Requirement.card(card)
        if requirement.needs_source:
            raise ValueError('bed room review requires verified clearance card '+card)
        sides = [(side,dep/1000) for side,dep in kind.clearance.items() if dep>0]
        either = set()
        if kind.clearance_any:
            either = set(kind.clearance_any[0])
            sides += [(side,kind.clearance_any[1]/1000) for side in either]
        rooms = [layout['rooms'][r]['rect'] for r in furnishing._cluster(layout,item['room'])]
        if item['id'] in active_marks and len(rooms)==1:
            frame = furnishing.footprint(item); room = rooms[0]
            for side,achieved in [('minimum X',frame[0]-room[0]),('minimum Y',frame[1]-room[1]),
                                  ('maximum X',room[2]-frame[2]),('maximum Y',room[3]-frame[3])]:
                if achieved < -1e-6:
                    findings.append(Finding('bed-frame-room-boundary',item['id'],side,achieved,0.,
                        'Actual room boundary from existing layout; physical exclusion, no layout change'))
        walls = furnishing._walls(specification,item['level'])+furnishing._columns()
        neighbours = [it for it in reviewed if it['id']!=item['id'] and it['level']==item['level']]
        side_rows = []
        for side,required in sides:
            if abs(required-requirement.value)>1e-6:
                raise ValueError('catalogue clearance disagrees with held card '+card)
            def clear(distance):
                zone = furnishing.side_zone(item,side,distance)
                from shapely.geometry import box
                from shapely.ops import unary_union
                inside = box(*zone).difference(unary_union([box(*r) for r in rooms])).area <= 1e-10
                return (inside and not any(furnishing._ov(zone,w) for w in walls)
                    and not any(furnishing._ov(zone,furnishing.footprint(other)) for other in neighbours
                        if not (item['id'] in active_marks and side in ('left','right')
                            and other['type']=='bedside_table' and furnishing._inside(furnishing.footprint(other),
                                [furnishing.head_zone(originals[item['id']],furnishing.ZONE_A)]))))
            low,high = 0.,required
            if clear(required):
                low=required
            else:
                for _ in range(35):
                    mid=(low+high)/2
                    if clear(mid):low=mid
                    else:high=mid
            side_rows.append(dict(item=item['id'],side=side,achieved_m=low,required_m=required,
                shortfall_m=max(0.,required-low),source=requirement.source,
                status='pass' if low>=required-1e-6 else 'fail',choice='one side' if side in either else 'every side'))
        if either:
            best=max((row for row in side_rows if row['side'] in either),key=lambda row:row['achieved_m'])
            for row in side_rows:
                if row['side'] in either:row['status']='pass' if best['status']=='pass' else 'fail'
        clearances.extend(side_rows)
    for row in clearances:
        if row['status']=='fail':
            findings.append(Finding('bed/storage-clearance',row['item'],row['side'],row['achieved_m'],
                row['required_m'],row['source'],detail='real frame; layout fixed'))
    serialized = [dict(asdict(f),difference_from_required=(None if f.achieved is None or f.required is None
                                                        else f.achieved-f.required)) for f in findings]
    return dict(ok=not findings,findings=serialized,clearances=clearances,checks=checks,
        scope='Real frame support, body/room/route/passage/door-swing and bed/storage access; fixed layout',
        limitations=['Door swing squares are the existing conservative envelopes, not measured animated leaf sweeps.',
            'Storage front access is checked; individual animated wardrobe doors/drawers need measured motion geometry.',
            'Floor contact is geometric support, not structural load capacity.'])
