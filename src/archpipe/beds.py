"""Bed acceptance, source units and measured mattress datums.

Client decision 2026-10-08: 20 mm per mattress plan dimension. The frame
may overhang; its room clearances are reviewed separately by C8 (geometry
topology). Native glTF uses metres and Y up; reviewed faces use Z up.
The 2026-10-09 decision permits bounded independent plan factors and a
separate vertical factor. Historical source-size checks remain diagnostic.
"""
from __future__ import annotations

import math

PLAN_TOLERANCE_M = 0.020
CLIENT_SOURCE = 'Client bed fit decision 2026-10-08'
SCALED_CLIENT_SOURCE = 'Client bed scaling decision 2026-10-09'
MAX_PLAN_DISTORTION = .15


def plan_scale_findings(sx, sy):
    """Width factor sx and length factor sy are dimensionless, after units.

    Distortion is larger factor divided by smaller factor, minus one.
    This symmetric definition refuses stretching regardless of axis order.
    """
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool)
               and math.isfinite(v) and v > 0 for v in (sx, sy)):
        raise ValueError('plan factors require finite positive numbers')
    findings = []
    if min(sx, sy) < .5 or max(sx, sy) > 2.:
        findings.append(f'plan scale outside 0.5–2.0: sx={sx:.9f}, sy={sy:.9f}; {SCALED_CLIENT_SOURCE}')
    distortion = max(sx, sy)/min(sx, sy)-1
    if distortion > MAX_PLAN_DISTORTION + 1e-12:
        findings.append(f'plan distortion {distortion*100:.6f}% exceeds 15%; {SCALED_CLIENT_SOURCE}')
    return findings


def scaled_bed_fit(bounds, width_m, depth_m, front_axis, *, mattress_bounds,
                   mattress_top_m, height_source, headboard_bounds,
                   headboard_limit_m, headboard_limit_source, length_axis=None,
                   unit_evidence=None, required_berths=1):
    """Solve width sx, length sy and vertical sz independently.

    Native bounds use X/Z horizontal, Y up. Mattress-top and headboard
    heights are metres above the retained frame's lowest vertex, seated at
    the design floor. Lower berth drives sz; report every resulting top.
    A caller requiring both bunk heights must separately reject a shortfall.
    No source geometry or layout is altered by this arithmetic.
    """
    _extents(bounds)
    if front_axis not in ('+X','-X','+Z','-Z'):
        raise ValueError('scaled bed requires measured horizontal front axis')
    axis = length_axis or front_axis[-1]
    if axis not in ('X','Z') or required_berths not in (1,2):
        raise ValueError('scaled bed requires measured length axis and berth count')
    if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
               and v>0 for v in (width_m,depth_m,mattress_top_m,headboard_limit_m)):
        raise ValueError('scaled bed requires positive design dimensions and height bound')
    if not height_source or not headboard_limit_source:
        raise ValueError('scaled bed requires sourced or explicitly ASSUMED height and bound')
    if set(mattress_bounds or {}) != ({'lower','upper'} if required_berths==2 else {'lower'}):
        return dict(ok=False,reason='actual mattress geometry required for every berth',source=SCALED_CLIENT_SOURCE)
    factor = unit_scale(unit_evidence)
    long, across = (0,2) if axis=='X' else (2,0)
    dimensions = _extents(mattress_bounds['lower'])
    sx, sy = width_m/(dimensions[across]*factor), depth_m/(dimensions[long]*factor)
    reasons = plan_scale_findings(sx,sy)
    rise = (mattress_bounds['lower']['max'][1]-bounds['min'][1])*factor
    if rise <= 0:
        raise ValueError('mattress top must be above retained frame bottom')
    sz = mattress_top_m/rise
    _extents(headboard_bounds)
    headboard_height = (headboard_bounds['max'][1]-bounds['min'][1])*factor*sz
    mattresses = {}
    for name, box in mattress_bounds.items():
        extent = _extents(box)
        size = [extent[across]*factor*sx,extent[long]*factor*sy]
        errors = [abs(a-b) for a,b in zip(size,(width_m,depth_m))]
        # Exactly one whole-model transform: no independently fitted berths.
        if max(errors) > 1e-5:
            reasons.append(f'{name} mattress cannot fit exactly with common factors: width/length errors {errors} m')
        mattresses[name] = dict(size_m=size,error_m=errors,
            top_m=(box['max'][1]-bounds['min'][1])*factor*sz)
    highest_top = max(m['top_m'] for m in mattresses.values())
    if headboard_height < highest_top-1e-9 or headboard_height > headboard_limit_m+1e-9:
        reasons.append(f'headboard height {headboard_height:.6f} m outside mattress top {highest_top:.6f} to bound {headboard_limit_m:.6f} m; {headboard_limit_source}')
    # Converted Blender axes are X/Y/Z. Width may be Blender Y, hence the
    # explicit mapping rather than treating sx as world X at every yaw.
    scale_xyz = [sy*factor,sx*factor,sz*factor] if axis=='X' else [sx*factor,sy*factor,sz*factor]
    return dict(ok=not reasons,reason='; '.join(reasons) or 'scaled mattresses fit exactly',
        sx=sx,sy=sy,sz=sz,scale_xyz=scale_xyz,source_unit_factor=factor,
        plan_distortion=max(sx,sy)/min(sx,sy)-1,mattresses=mattresses,
        headboard_height_m=headboard_height,headboard_limit_m=headboard_limit_m,
        height_source=height_source,headboard_limit_source=headboard_limit_source,source=SCALED_CLIENT_SOURCE)


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
                        unit_evidence=None, scaled_model=None):
    """Check measured frame transform and mattress size/centre after import.

    footprint is the planned mattress rectangle (minimum X/Y, maximum X/Y).
    reference_height_m is historical and imposes no frame height limit.
    Frame edges may extend outside that rectangle; C8 checks their effects.
    """
    native, actual = _extents(native_bounds), _extents(world_bounds)
    if sorted(native_to_world_axes) != [0, 1, 2]:
        raise ValueError('native_to_world_axes must be a permutation of 0, 1, 2')
    if scaled_model is not None:
        import numpy as np
        rows,matrix,offset = model_transform(scaled_model)
        points=np.asarray([p for r in rows for f in r['faces'] for p in f])@matrix.T+offset
        expected_low,expected_high=points.min(0),points.max(0)
        findings=[]
        if any(abs(a-b)>1e-5 for a,b in zip(world_bounds['min']+world_bounds['max'],
                                         [*expected_low,*expected_high])):
            findings.append('scale-distortion: actual imported frame differs from measured independent factors/placement')
        expected_mattresses = model_mattress_bounds(scaled_model,world=True)
        for key,box in (mattress_world_bounds or {}).items():
            if key not in expected_mattresses or any(abs(a-b)>1e-5 for a,b in zip(
                    box['min']+box['max'],expected_mattresses[key]['min']+expected_mattresses[key]['max'])):
                findings.append(key+' mattress differs from measured scaled transform')
    else:
        findings = real_size_findings(scale, unit_evidence)
    if len(footprint) != 4 or not all(math.isfinite(v) for v in footprint) or footprint[2] <= footprint[0] or footprint[3] <= footprint[1]:
        raise ValueError('bed requires a finite, positive planned mattress footprint')
    expected = [native[i]*unit_scale(unit_evidence) for i in native_to_world_axes]
    if scaled_model is None and any(abs(a-b) > 1e-5 for a,b in zip(actual, expected)):
        findings.append('scale-distortion: actual imported extents disagree with one uniform scale from source units')
    if not mattress_world_bounds:
        findings.append('actual imported mattress bounds required')
    for name, box in (mattress_world_bounds or {}).items():
        dimensions = _extents(box)
        for axis in (0, 1):
            planned = footprint[axis+2]-footprint[axis]
            tolerance = 1e-5 if scaled_model is not None else PLAN_TOLERANCE_M + 1e-9
            if abs(dimensions[axis]-planned) > tolerance:
                source = SCALED_CLIENT_SOURCE if scaled_model is not None else CLIENT_SOURCE
                findings.append(f'{name} mattress axis {axis}: achieved {dimensions[axis]:.6f} m, planned {planned:.6f} m; {source}')
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
        if review.get('status') != 'bed-only' or not review.get('basis') or review.get('fused_extras'):
            raise ValueError('bed-only contents review required; inseparable tables, benches and rugs refused')
        if set(review.get('extras', [])) != set(omitted):
            raise ValueError('every accessory must be a separable omitted mesh')
    retained = [r for r in rows if r['name'] not in omitted]
    if not retained:
        raise ValueError('bed has no retained meshes')
    return retained


def _native_box(rows):
    import numpy as np
    points = np.asarray([p for row in rows for f in row['faces'] for p in f])[:,[0,2,1]].copy()
    points[:,2] *= -1
    return dict(min=points.min(0).tolist(),max=points.max(0).tolist())


def scaled_model_fit(model, rows=None):
    """Recompute an explicit 2026-10-09 contract from actual retained faces."""
    rows = retained_model_rows(model) if rows is None else rows
    contract = model['scaling']
    if contract.get('decision_date') != '2026-10-09':
        raise ValueError('scaled bed requires client decision 2026-10-09')
    mattresses = {key:_native_box([r for r in rows if r['name'] in binding['parts']])
                  for key,binding in model['mattress_bindings'].items()}
    heads = [r for r in rows if r['name'] in contract.get('headboard_parts',[])]
    if not heads:
        raise ValueError('scaled bed requires measured headboard parts')
    result = scaled_bed_fit(_native_box(rows), *model['planned_mattress_m'],model['front_axis'],
        length_axis=model.get('length_axis'),mattress_bounds=mattresses,
        mattress_top_m=contract['mattress_top_m'],height_source=contract['height_source'],
        headboard_bounds=_native_box(heads),headboard_limit_m=contract['headboard_limit_m'],
        headboard_limit_source=contract['headboard_limit_source'],
        unit_evidence=model.get('unit_evidence'),required_berths=model.get('required_berths',1))
    return result


def review_selection(model):
    """Bind plan/height factors and semantic cuts along with source units."""
    selection = dict(omitted_meshes=model.get('omitted_meshes',[]),
        mattress_bindings=model['mattress_bindings'],unit_evidence=model.get('unit_evidence'))
    if model.get('scaling'):
        import hashlib
        import json
        selection.update(scaling=model['scaling'],scale_xyz=model['scale_xyz'],
                         part_selections=model.get('part_selections',{}),
                         contents_review=model['contents_review'],
                         position=model['position'],rotation_deg=model['rotation_deg'],
                         geometry_sha256=hashlib.sha256(json.dumps(model['review_geometry'],
                             sort_keys=True,separators=(',',':')).encode()).hexdigest())
    from copy import deepcopy
    return deepcopy(selection)


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
        if model.get('scaling'):
            fit = scaled_model_fit(model, rows)
            findings = [] if fit['ok'] else [fit['reason']]
            supplied = model.get('scale_xyz')
            if (not isinstance(supplied,(list,tuple)) or len(supplied)!=3 or
                    any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v)
                        or abs(v-expected)>1e-12 for v,expected in zip(supplied,fit['scale_xyz']))):
                findings.append('scale-distortion: factors disagree with measured mattress/height contract')
        else:
            findings = real_size_findings(scale, model.get('unit_evidence'))
        if findings:
            raise ValueError('; '.join(findings))
    if isinstance(scale,bool) or not isinstance(scale,(int,float)) or not math.isfinite(scale) or scale<=0:
        raise ValueError('model requires one uniform positive scale')
    if tuple(model['rotation_deg'][:2]) != (0,0):
        raise ValueError('bed review supports measured up axis and yaw only')
    yaw = math.radians(model['rotation_deg'][2]); c,s = math.cos(yaw), math.sin(yaw)
    matrix = np.array([[c,-s,0],[s,c,0],[0,0,1]]) @ np.diag(
        model['scale_xyz'] if model.get('role')=='bed' and model.get('scaling') else [scale]*3)
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
    pillow_prefixes={'dress-pillow-'+m['replaces'].removeprefix('furn-').removesuffix('-')+'-'
                     for m in active if m.get('role')=='bed' and m.get('review_geometry') and m.get('replaces')}
    meshes=[m for m in scene.get('meshes',[]) if m.get('model_instance') not in instance_ids
            and not any(m['id'].startswith(p) for p in prefixes|pillow_prefixes)]
    return dict(scene,meshes=meshes+faces)


def integrate_bed_models(scene, models, layout, specification, furniture):
    """Activate reviewed scaled beds only when unchanged room checks pass.

    Keep procedural faces for runtime missing-file fallback. Blender hides
    them only after successful real import, before model-first cloth.
    """
    items={it['id']:it for it in furniture}
    for model in models:
        if model.get('role')!='bed' or not model.get('scaling'):
            raise ValueError('bed replacement requires explicit scaled-bed contract')
        mark=model['replaces'].removeprefix('furn-').removesuffix('-')
        if mark not in items:
            raise ValueError('bed replacement must refer to an existing planned bed')
        item=items[mark]
        floor=min(p[2] for row in scene['meshes'] if row['id'].startswith(model['replaces'])
                  for face in row['faces'] for p in face)
        if (model['planned_mattress_m']!=[item['w'],item['d']] or
                model.get('required_berths',1)!=item.get('berths',1) or
                any(abs(a-b)>1e-5 for a,b in zip(model['position'],[item['cx'],item['cy'],floor])) or
                model['layout_rotation_deg']!=item['rot']):
            raise ValueError('scaled bed must retain planned mattress, centre, finished floor and head direction')
        require_bed_geometry(model)
        actual=model_mattress_bounds(model,world=True)
        for berth in actual:
            cloth_id='duvet-'+mark+('-upper' if berth=='upper' else '')
            design=next((c for c in scene.get('cloth',[]) if c['id']==cloth_id),None)
            if design is None or abs(actual[berth]['max'][2]-design['mattress_top'])>1e-5:
                raise ValueError('scaled bed must retain every design mattress-top height: '+cloth_id)
    prefixes={m['replaces'] for m in models}
    result=dict(scene,models=[m for m in scene.get('models',[]) if m.get('replaces') not in prefixes]+list(models))
    review=bed_room_review(result,layout,specification,furniture)
    if not review['ok']:
        raise ValueError('scaled bed fails fixed room: '+str(review['findings']))
    result['bed_room_review']=review
    return result


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


def require_bed_geometry(spec, library_root=None, *, neutral_diagnostic=False):
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
    statuses = ('pending','accepted') if neutral_diagnostic else ('accepted',)
    if (orientation.get('front_axis')!=spec.get('front_axis') or not orientation.get('basis')
            or (spec.get('neutral_review') or {}).get('status') not in statuses):
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
    fit = (scaled_model_fit(spec) if spec.get('scaling') else
        fit_bed(spec['native_bounds'], width, depth, None, spec['front_axis'],
        spec.get('length_axis'), mattress_bounds=mattresses, scale=spec['scale'],
        unit_evidence=spec.get('unit_evidence'), required_berths=spec.get('required_berths',1)))
    if not fit['ok']:
        raise ValueError(spec['id']+': '+fit['reason'])
    # Omissions and mattress selection change what was reviewed even with identical files.
    selection = review_selection(spec)
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
            if spec['id'] not in ('duvet-'+mark,'duvet-'+mark+'-upper','throw-'+mark):
                continue
            key='upper' if spec['id'].endswith('-upper') else 'lower'
            binding=(model.get('mattress_bindings') or {}).get(key)
            if not binding or not binding.get('parts') or type(binding.get('head_at_max')) is not bool:
                raise ValueError(spec['id']+': measured '+key+' mattress binding required')
            spec.update(model_instance=model['id'],mattress_parts=binding['parts'],
                        head_at_max=binding['head_at_max'],model_cloth_kind='throw' if spec['id']=='throw-'+mark else 'duvet')
        result.append(spec)
    return result


def mattress_cloth(spec, faces, head_at_max, *, collider_faces=None, collider_ceiling_m=None,
                   initialization_ceiling_m=None):
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
    surface_top=float(high[2])
    if collider_faces is not None:
        cut_low=[c-s/2 for c,s in zip(center,size)];cut_high=[c+s/2 for c,s in zip(center,size)]
        for face in collider_faces:
            vertices=np.asarray(face,float)
            if (vertices.ndim!=2 or vertices.shape[1]!=3 or not np.isfinite(vertices).all()):
                raise ValueError('cloth initialization requires finite actual collider faces')
            limit=initialization_ceiling_m if initialization_ceiling_m is not None else collider_ceiling_m
            if limit is not None and vertices[:,2].max()>=limit:
                continue
            if all(vertices[:,i].max()>=cut_low[i] and vertices[:,i].min()<=cut_high[i] for i in (0,1)):
                surface_top=max(surface_top,float(vertices[:,2].max()))
    if collider_ceiling_m is not None and surface_top+.08>=collider_ceiling_m:
        raise ValueError('cloth cannot start clear of colliders inside its own bunk berth')
    return dict(spec,center=center,size=size,z_start=surface_top+.08,
        pin=[axis,float(start),.03],mattress_top=float(high[2]),
        initial_collider_top_m=surface_top,
        collider_ceiling_m=collider_ceiling_m,
        initialization_ceiling_m=initialization_ceiling_m,
        mattress_span=[float(low[long]),float(high[long])],geometry_basis='actual imported mattress faces')


def mattress_pin_indices(spec, mattress_faces, points):
    """Pin the authored heading band only across the actual mattress width.

    points are world cloth vertices in metres. Overhang vertices stay free
    to drape; pin width is the existing along-length heading band in metres.
    """
    import numpy as np
    mattress=np.asarray([p for f in mattress_faces for p in f])
    low,high=mattress.min(0),mattress.max(0)
    axis,value,width=spec['pin'];long=0 if axis=='x' else 1;across=1-long
    return [i for i,p in enumerate(points) if abs(p[long]-value)<=width
            and low[across]<=p[across]<=high[across]]


def cloth_support_envelope(points, collider_faces, cell_size_m, *, ceiling_m=None, gap_m=.008):
    """Construct support heights above each vertex's real subdivision ring.

    points are initial world vertices in metres; cell_size_m contains grid
    spacing across world X and Y. The one-cell ring contains the neighbors
    used by subdivision, so interpolating their anchors cannot cut a source
    wrinkle between point samples. Face bounds give a conservative support
    envelope, not a claim of exact contact. Missing support leaves a free
    overhang at its collision-safe initial height. gap_m is the existing
    collider and cloth collision offsets added together.
    """
    import numpy as np
    faces=[np.asarray(f,float) for f in collider_faces
           if ceiling_m is None or max(p[2] for p in f)<ceiling_m]
    if not faces or len(cell_size_m)!=2 or min(cell_size_m)<=0:
        raise ValueError('cloth support requires actual faces and positive grid spacing')
    low=np.asarray([f.min(0) for f in faces]);high=np.asarray([f.max(0) for f in faces])
    result=[]
    for point in points:
        reach=np.asarray(cell_size_m)
        matches=np.all(high[:,:2]>=np.asarray(point[:2])-reach,axis=1)&np.all(low[:,:2]<=np.asarray(point[:2])+reach,axis=1)
        height=float(high[matches,2].max()+gap_m) if matches.any() else float(point[2])
        result.append(height)
    return result


def bed_room_review(scene, layout, specification, furniture):
    """C8 real-frame report, preserving every authored item and room.

    C8 is the geometry-topology review. Its collision measures may be area,
    gap or reached destinations; shortfall uses the same unit, never pretends
    a route count or overlap area measures remaining passage width. Clearance
    strips below report metres achieved versus the held card's required value.
    Wardrobe/drawer fronts use the existing storage-front clearance card;
    actual animated drawer/leaf travel needs its own measured motion receipt.
    """
    from dataclasses import asdict, replace
    from .geometry_topology import GeometryTopology, Finding, Requirement
    from .concept import villa_furnish as furnishing
    from . import catalogue
    reviewed = bed_frame_items(scene,furniture)
    topology = GeometryTopology.from_inputs(scene=scene,layout=layout,
        specification=specification,furniture=furniture)
    baseline = GeometryTopology.from_inputs(scene=dict(scene,models=[m for m in scene.get('models',[]) if m.get('role')!='bed']),
        layout=layout,specification=specification,furniture=furniture)
    findings = []
    bed_marks={m['replaces'].removeprefix('furn-').removesuffix('-') for m in scene.get('models',[])
               if m.get('role')=='bed' and m.get('status')!='procedural-bed-fallback'}
    for query in (topology.unsupported_floating,
                  topology.swing_envelope_vs_obstacle,topology.passage_obstructions,
                  topology.occupied_room_intrusions,topology.object_overlaps):
        # A route/access proxy is not another manufactured body. Physical
        # queries use actual parts; the proxy remains only in route grids.
        physical=replace(topology,obstacles=tuple(o for o in topology.obstacles if o.source_id not in bed_marks))
        results=getattr(physical,query.__name__)()
        old={(f.query,f.source_id,f.reference_id,f.achieved,f.required) for f in getattr(baseline,query.__name__)()}
        for finding in results:
            # Parts of the same manufactured bed intentionally touch/intersect.
            if finding.query=='body-overlap' and '::' in finding.source_id and finding.source_id.split('::')[0]==finding.reference_id.split('::')[0]:
                continue
            if (finding.query,finding.source_id,finding.reference_id,finding.achieved,finding.required) not in old:
                findings.append(finding)
    # This report measures bed-induced changes. Unchanged unrelated props
    # must not be sent through a new route intake merely to discard their
    # findings afterwards. The complete scene still participates in body,
    # support and access checks; walking triangles here are actual bed faces.
    bed_instances={m['id'] for m in scene.get('models',[]) if m.get('role')=='bed'
                   and m.get('status')!='procedural-bed-fallback'}
    route_topology=replace(topology,obstacles=tuple(o for o in topology.obstacles
        if '::' in o.source_id and o.source_id.split('::')[0] in bed_instances))
    findings.extend(route_topology.object_in_route())
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
            'Body overlap is a conservative measured-part bounding-box screen, not exact solid penetration.',
            'Storage front access is checked; individual animated wardrobe doors/drawers need measured motion geometry.',
            'Floor contact is geometric support, not structural load capacity.'])
