"""Measured furniture fit under the client's 2026-10-09 scaling decision.

Native bounds are glTF coordinates: X/Z horizontal, Y up. Review faces
are converted X/Y horizontal, Z up. All design distances are metres.
sx, sy and sz mean dimensionless width, depth and vertical factors after
source-unit conversion. Distortion means larger plan factor / smaller - 1.
This module measures and proposes factors; room review and activation are
separate gates. An arithmetic fit is never permission to replace furniture.
"""
from __future__ import annotations

from collections.abc import Mapping
import math

CLIENT_SOURCE = 'Client furniture scaling decision 2026-10-09'
MAX_PLAN_DISTORTION = .15


def positive_numbers(*values):
    return all(isinstance(v, (int, float)) and not isinstance(v, bool)
               and math.isfinite(v) and v > 0 for v in values)


def measured_extents(bounds):
    """Return three positive extents from measured minimum/maximum triples."""
    try:
        low, high = list(bounds['min']), list(bounds['max'])
        if len(low) != 3 or len(high) != 3:
            raise ValueError
        if any(isinstance(v, bool) or not isinstance(v, (int, float))
               or not math.isfinite(v) for v in low + high):
            raise ValueError
        dimensions = [float(b) - float(a) for a, b in zip(low, high)]
        if not positive_numbers(*dimensions):
            raise ValueError
        return dimensions
    except (KeyError, TypeError, ValueError):
        raise ValueError('furniture intake requires finite, positive measured bounds') from None


def unit_scale(unit_evidence=None):
    """Only source-declared units convert; absent evidence means glTF metres.

    m, cm, mm, ft and in mean metres, centimetres, millimetres, feet and
    inches. A size guessed from the target is never unit evidence.
    """
    evidence = unit_evidence if unit_evidence is not None else {
        'unit': 'm', 'source': 'glTF 2.0 coordinate system and units'}
    factors = {'m': 1., 'cm': .01, 'mm': .001, 'ft': .3048, 'in': .0254}
    if not isinstance(evidence, Mapping) or evidence.get('unit') not in factors or not evidence.get('source'):
        raise ValueError('furniture unit conversion requires a source stating m, cm, mm, ft or in')
    return factors[evidence['unit']]


def plan_scale_findings(sx, sy, *, source=CLIENT_SOURCE):
    """Refuse factors outside 0.5–2.0 or symmetric plan distortion over 15%."""
    if not positive_numbers(sx, sy):
        raise ValueError('plan factors require finite positive numbers')
    findings = []
    if min(sx, sy) < .5 or max(sx, sy) > 2.:
        findings.append(f'plan scale outside 0.5–2.0: sx={sx:.9f}, sy={sy:.9f}; {source}')
    distortion = max(sx, sy) / min(sx, sy) - 1
    if distortion > MAX_PLAN_DISTORTION + 1e-12:
        findings.append(f'plan distortion {distortion*100:.6f}% exceeds 15%; {source}')
    return findings


def fit_factors(bounds, width_m, depth_m, front_axis, *, height_bounds,
                height_m, height_source, length_axis=None, unit_evidence=None,
                plan_bounds=None, source=CLIENT_SOURCE):
    """Solve one whole-item transform from measured plan and height datums.

    bounds is the retained item, plan_bounds defaults to that complete item
    (beds instead supply the mattress), and height_bounds names actual top
    geometry, such as a seat or desktop. Its maximum Y above retained bottom
    drives sz independently of the plan. length_axis is measured X or Z;
    front_axis is signed X or Z, never inferred from a listing thumbnail.
    height_source identifies authored design input or a read cited figure;
    provenance validation belongs to the item contract below.
    """
    measured_extents(bounds)
    dimensions = measured_extents(bounds if plan_bounds is None else plan_bounds)
    measured_extents(height_bounds)
    if front_axis not in ('+X', '-X', '+Z', '-Z'):
        raise ValueError('furniture fit requires a measured horizontal front axis')
    axis = front_axis[-1] if length_axis is None else length_axis
    if axis not in ('X', 'Z'):
        raise ValueError('furniture depth axis must be measured X or Z')
    if not positive_numbers(width_m, depth_m, height_m) or not height_source:
        raise ValueError('furniture fit requires positive design dimensions and sourced height')
    factor = unit_scale(unit_evidence)
    long, across = (0, 2) if axis == 'X' else (2, 0)
    sx, sy = width_m / (dimensions[across]*factor), depth_m / (dimensions[long]*factor)
    reasons = plan_scale_findings(sx, sy, source=source)
    rise = (height_bounds['max'][1] - bounds['min'][1]) * factor
    if not positive_numbers(rise):
        raise ValueError('height datum must be above retained item bottom')
    sz = height_m / rise
    scale_xyz = ([sy*factor, sx*factor, sz*factor] if axis == 'X'
                 else [sx*factor, sy*factor, sz*factor])
    if not positive_numbers(sx, sy, sz, *scale_xyz):
        raise ValueError('furniture fit factors must remain finite and positive')
    return dict(ok=not reasons, reason='; '.join(reasons) or 'scaled item fits exactly',
                sx=sx, sy=sy, sz=sz, scale_xyz=scale_xyz,
                source_unit_factor=factor, plan_distortion=max(sx, sy)/min(sx, sy)-1,
                height_m=height_m, overall_height_m=measured_extents(bounds)[1]*factor*sz,
                height_source=height_source, source=source)


def retained_model_rows(model, *, require_item_only=False):
    """Keep only reviewed item meshes; omit explicitly named separable extras.

    bed-only is accepted for existing bed contracts. New desk/chair intake
    requires item-only, a review basis, and exact correspondence between
    listed extras and measured omitted meshes. Fused extras always refuse.
    Legacy non-furniture consumers retain their existing omission convention.
    """
    rows = model['review_geometry']['meshes']
    names = [r['name'] for r in rows]
    omitted = model.get('omitted_meshes', [])
    review = model.get('contents_review') or {}
    if len(names) != len(set(names)) or len(omitted) != len(set(omitted)) or not set(omitted) <= set(names):
        raise ValueError('furniture mesh names/omissions must be unique and measured')
    bed = model.get('role') == 'bed'
    strict = require_item_only or bed or model.get('role') in ('desk', 'chair', 'task_chair')
    if strict:
        allowed = ('item-only', 'bed-only') if bed else ('item-only',)
        if review.get('status') not in allowed or not review.get('basis') or review.get('fused_extras'):
            raise ValueError(('bed-only or item-only' if bed else 'item-only') +
                             ' contents review required; fused extras refused')
        extras = review.get('extras', [])
        if len(extras) != len(set(extras)) or set(extras) != set(omitted):
            raise ValueError('every accessory must be a separable omitted mesh')
    retained = [r for r in rows if r['name'] not in omitted]
    if not retained:
        raise ValueError('furniture has no retained meshes')
    return retained


def native_box(rows):
    """Measure converted review faces back in native glTF axes, without edits."""
    import numpy as np
    points = np.asarray([p for row in rows for f in row['faces'] for p in f], float)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError('furniture requires finite actual review vertices')
    points = points[:, [0, 2, 1]].copy()
    points[:, 2] *= -1
    box = dict(min=points.min(0).tolist(), max=points.max(0).tolist())
    measured_extents(box)
    return box


def fit_furniture(model, width_m, depth_m, *, height_parts, height_m,
                  height_source, height_basis, height_constraints=None):
    """Strict desk/chair intake from retained faces and a semantic height datum.

    height_basis is design or citation. height_source must name the design
    field or cited publication/page; ASSUMED design inputs remain labelled
    assumptions and are not ergonomic verification. height_parts names the
    complete actual desktop or seat geometry, not overall model height.
    No individual leg, seat or back is stretched separately. The resulting
    overall height is reported for later design and room checks.
    height_constraints optionally maps named additional datums (such as back)
    to parts, height_m, height_source and height_basis. All use the same sz;
    a mismatch over 0.00001 m (arithmetic precision, not an ergonomic allowance)
    refuses the fit. Pass every required design height before acceptance.
    """
    if height_basis not in ('design', 'citation') or not isinstance(height_source, str) or not height_source.strip():
        raise ValueError('height requires design input or a cited figure')
    rows = retained_model_rows(model, require_item_only=True)
    names = {row['name'] for row in rows}
    if (not isinstance(height_parts, (list, tuple)) or not height_parts
            or len(height_parts) != len(set(height_parts)) or not set(height_parts) <= names):
        raise ValueError('height datum requires measured retained parts')
    result = fit_factors(native_box(rows), width_m, depth_m, model.get('front_axis'),
                         height_bounds=native_box([r for r in rows if r['name'] in height_parts]),
                         height_m=height_m, height_source=height_source,
                         length_axis=model.get('length_axis'), unit_evidence=model.get('unit_evidence'))
    result['height_basis'] = height_basis
    reasons = [] if result['ok'] else [result['reason']]
    result['heights'] = {}
    for name, contract in (height_constraints or {}).items():
        parts = contract.get('parts') or []
        target = contract.get('height_m')
        source = contract.get('height_source')
        if (contract.get('height_basis') not in ('design', 'citation')
                or not isinstance(source, str) or not source.strip() or not positive_numbers(target)
                or not parts or len(parts) != len(set(parts)) or not set(parts) <= names):
            raise ValueError('additional heights require measured retained parts and design or citation')
        box = native_box([r for r in rows if r['name'] in parts])
        achieved = (box['max'][1] - native_box(rows)['min'][1])*result['source_unit_factor']*result['sz']
        result['heights'][name] = dict(achieved_m=achieved, required_m=target, source=source)
        if abs(achieved-target) > 1e-5:
            reasons.append(f'{name} height {achieved:.6f} m differs from required {target:.6f} m; {source}')
    result.update(ok=not reasons, reason='; '.join(reasons) or 'scaled item fits exactly')
    return result


def model_fit(model):
    """Recompute the whole-item contract; supplied factors are never authority."""
    contract=model['furniture_fitting']
    if contract.get('decision_date')!='2026-10-09':
        raise ValueError('furniture replacement requires client decision 2026-10-09')
    return fit_furniture(model,*contract['footprint_m'],height_parts=contract['height_parts'],
        height_m=contract['height_m'],height_source=contract['height_source'],
        height_basis=contract['height_basis'],height_constraints=contract.get('height_constraints'))


def review_selection(model):
    """Freeze factors, geometry, contents, orientation and unchanged placement."""
    from copy import deepcopy
    import hashlib,json
    return deepcopy(dict(furniture_fitting=model['furniture_fitting'],scale_xyz=model['scale_xyz'],
        contents_review=model['contents_review'],omitted_meshes=model.get('omitted_meshes',[]),
        part_selections=model.get('part_selections',{}),unit_evidence=model.get('unit_evidence'),
        orientation_evidence=model['orientation_evidence'],position=model['position'],rotation_deg=model['rotation_deg'],
        replacement_mesh_ids=model['replacement_mesh_ids'],
        geometry_sha256=hashlib.sha256(json.dumps(model['review_geometry'],sort_keys=True,separators=(',',':')).encode()).hexdigest()))


def require_furniture_geometry(model, library_root=None, *, neutral_diagnostic=False):
    """Refuse unreviewed/stale/altered desk and chair fit before real import."""
    from pathlib import Path
    import hashlib
    fit=model_fit(model)
    if not fit['ok']:raise ValueError(model['id']+': '+fit['reason'])
    if any(abs(a-b)>1e-12 for a,b in zip(model['scale_xyz'],fit['scale_xyz'])) or len(model['scale_xyz'])!=3:
        raise ValueError('furniture factors disagree with measured geometry')
    geometry=model['review_geometry'];orientation=model.get('orientation_evidence',{})
    replacements=model.get('replacement_mesh_ids',[])
    prefix=model['replaces']
    if (not replacements or len(replacements)!=len(set(replacements)) or
            any(not name.startswith(prefix) or (model.get('role')=='desk' and name.startswith(prefix+'chair-')) for name in replacements)):
        raise ValueError('furniture replacement requires exact own body meshes; derived chairs stay independent')
    if geometry.get('schema') not in ('furniture-model-geometry/1','bed-model-geometry/1') or geometry.get('asset')!=model['asset']:
        raise ValueError('furniture requires measured geometry receipt')
    if orientation.get('front_axis')!=model.get('front_axis') or not orientation.get('basis'):
        raise ValueError('furniture requires measured front orientation')
    review=model.get('neutral_review',{})
    if review.get('status') not in (('pending','accepted') if neutral_diagnostic else ('accepted',)):
        raise ValueError('furniture requires accepted neutral review')
    if review.get('selection')!=review_selection(model) or review.get('source_sha256')!=geometry['source_sha256']:
        raise ValueError('furniture neutral review is not bound to current selection')
    if library_root is not None:
        root=(Path(library_root)/'props'/model['asset']).resolve()
        for relative,digest in geometry['source_sha256'].items():
            path=(root/relative).resolve()
            if not path.is_relative_to(root) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
                raise ValueError('stale furniture source receipt: '+relative)
