"""Deterministic dominant-light grouping under ADR-0013 (2026-10-15).

CCT means correlated colour temperature in kelvin. Flux is emitted lumens.
A fraction is a dimensionless ratio; exposure stops are base-two camera gain.
"""
from __future__ import annotations
import hashlib
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULE_SHA256 = 'be87dd5bc2bbefe668524b5f13febf906cf30ca081c5dd7e21326501ebd5efb6'
VIEW_KEYS = ('id', 'state', 'exposure', 'camera', 'sun', 'layers_on', 'dimmers',
             'hide_meshes', 'resolution', 'max_bounces')
APPEARANCE_KEYS = ('draped_appearances', 'drape_material_overrides', 'drape_policy_sha256',
                   'drape_polish_policy_sha256', 'imported_appearances', 'physical_model_meshes',
                   'imported_admission_policy')
TRANSPORT_KEYS = ('north', 'materials', 'meshes', 'props', 'models', 'cloth', 'curtains',
                  'sky', 'lights', 'library_root') + APPEARANCE_KEYS


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def rule():
    path = ROOT / 'knowledge/exposure-group-rule.json'
    if hashlib.sha256(path.read_bytes()).hexdigest() != RULE_SHA256:
        raise ValueError('Pre-registered dominant-light rule changed')
    return json.loads(path.read_text())


def view_input(view):
    return {key: view[key] for key in VIEW_KEYS if key in view}


def transport_digest(scene):
    return digest({key: scene.get(key) for key in TRANSPORT_KEYS})


def measurement(lamps, daylight, sky_only=None):
    """Reduce equal-position source luminances using the pre-registered mask."""
    if not lamps or len(lamps) != len(daylight) or (sky_only is not None and len(sky_only) != len(lamps)):
        raise ValueError('Source isolation pixel populations differ')
    combined = [a+b for a, b in zip(lamps, daylight)]
    indices = [i for i in sorted(range(len(combined)), key=combined.__getitem__)
               [:int(len(combined)*0.97)] if combined[i] > 0]
    if not indices:
        raise ValueError('No positive metered source light')
    lamp_sum = sum(lamps[i] for i in indices)
    day_sum = sum(daylight[i] for i in indices)
    sky_sum = sum(sky_only[i] for i in indices) if sky_only is not None else None
    return dict(lamp_luminance_sum=lamp_sum, daylight_luminance_sum=day_sum,
                sky_luminance_sum=sky_sum, metered_pixels=len(indices),
                lamp_fraction=lamp_sum/(lamp_sum+day_sum),
                solar_fraction=(max(0., min(1., (day_sum-sky_sum)/day_sum))
                                if sky_sum is not None and day_sum > 0 else None))


def classify(view, row):
    """No view identifier or image-quality verdict participates in assignment."""
    policy = rule()
    original = view['exposure']
    if original in ('evening', 'exterior-dusk'):
        return original
    fraction = row['lamp_fraction']
    if not isinstance(fraction, (int, float)) or not math.isfinite(fraction) or not 0 <= fraction <= 1:
        raise ValueError('Invalid measured lamp fraction')
    if fraction > policy['lamp_fraction_threshold']:
        return 'lamp-dominant'
    if original == 'exterior-day':
        solar = row['solar_fraction']
        if solar is None or not math.isfinite(solar) or not 0 <= solar <= 1:
            raise ValueError('Exterior daylight requires measured sun fraction')
        if solar <= policy['solar_fraction_threshold']:
            return 'exterior-shade'
    return original


def lamp_population(scene, view, emissive_sources):
    """One active analytic lamp or emissive-only source per view, no lens double count."""
    from .villa_render_contract import emissive_mesh_output_factor
    population = []
    for light in scene['lights']:
        factor = (view.get('dimmers', {}).get(light['layer'], 1.) * light.get('dimmer', 1.)
                  if light['layer'] in view['layers_on'] else 0.)
        if factor > 0:
            population.append(dict(id=light['id'], flux_lm=light['lumens']*factor, cct_k=light['cct_k']))
    analytic_ids = {light['id'] for light in scene['lights']}
    meshes = {mesh['id']: mesh for mesh in scene['meshes']}
    for source in emissive_sources:
        if any(source['id'].endswith('-'+ident) for ident in analytic_ids):
            continue
        mesh = meshes[source['id']]
        factor = emissive_mesh_output_factor(mesh, view)
        if factor > 0:
            population.append(dict(id=source['id'], flux_lm=source['emitted_lumens']*factor,
                                   cct_k=scene['materials'][mesh['material']]['cct_k']))
    return population


def freeze(scene, rows, runtime):
    """Bind measured values and automatically derived assignments to live inputs."""
    if set(rows) != {view['id'] for view in scene['views']}:
        raise ValueError('Every authored view requires a source measurement')
    for view in scene['views']:
        row = rows[view['id']]
        row['view_input'] = view_input(view)
        row['group'] = classify(view, row)
    record = dict(schema='exposure-groups/1', rule_sha256=RULE_SHA256,
                  transport_sha256=transport_digest(scene), runtime=runtime, measurements=rows)
    record['measurement_sha256'] = digest(rows)
    record['white_balance_k'] = white_balances(record)
    return record


def white_balances(record):
    result = {group: rule()['white_balance'][group]
              for group in {row['group'] for row in record['measurements'].values()}}
    if 'lamp-dominant' in result:
        lamps = [lamp for row in record['measurements'].values() if row['group'] == 'lamp-dominant'
                 for lamp in row['lamp_population']]
        flux = sum(lamp['flux_lm'] for lamp in lamps)
        if flux <= 0:
            raise ValueError('Lamp-dominant group lacks authored lamp population')
        result['lamp-dominant'] = round(sum(lamp['flux_lm']*lamp['cct_k'] for lamp in lamps)/flux)
    return result


def require_record(scene, record, *, check_transport=True):
    policy = rule()
    if (record.get('schema') != 'exposure-groups/1'
            or record.get('runtime', {}).get('probe') != policy['source_probe']
            or record.get('runtime', {}).get('render_device', {}).get('device') != 'GPU'):
        raise ValueError('Frozen dominant-light source probe settings or GPU evidence differ')
    if (record.get('rule_sha256') != RULE_SHA256 or
            (check_transport and record.get('transport_sha256') != transport_digest(scene))):
        raise ValueError('Stale dominant-light rule or transport measurement')
    rows = record['measurements']
    if record.get('measurement_sha256') != digest(rows):
        raise ValueError('Frozen dominant-light measurements edited')
    if set(rows) != {view['id'] for view in scene['views']}:
        raise ValueError('Dominant-light view inventory differs')
    for view in scene['views']:
        row = rows[view['id']]
        if (row['view_input'] != view_input(view) or row['group'] != classify(view, row)
                or view.get('exposure_group', row['group']) != row['group']):
            raise ValueError('Dominant-light membership differs from measured rule: '+view['id'])
        # Recompute all fractions from frozen source sums too.
        lamps, day, sky = (row[key] for key in ('lamp_luminance_sum', 'daylight_luminance_sum', 'sky_luminance_sum'))
        if min(lamps, day) < 0 or not math.isfinite(lamps+day) or lamps+day <= 0:
            raise ValueError('Invalid frozen source luminance')
        if row['lamp_fraction'] != lamps/(lamps+day):
            raise ValueError('Frozen lamp fraction differs from source measurements')
        solar = max(0., min(1., (day-sky)/day)) if sky is not None and day > 0 else None
        if row['solar_fraction'] != solar:
            raise ValueError('Frozen solar fraction differs from source measurements')
    if record['white_balance_k'] != white_balances(record):
        raise ValueError('Group white balance differs from authored lamp population')
    return record


def group_for(scene, view):
    record = scene.get('exposure_groups')
    return record['measurements'][view['id']]['group'] if record else view['exposure']


def require_receipts(scene, reports, *, transport_checked=False):
    """Check individual rule membership, complete cohorts and shared camera locks."""
    if not scene.get('exposure_groups'):
        if scene.get('exposure_group_mode') == 'dominant-light':
            raise ValueError('Missing frozen dominant-light groups')
        return
    record = require_record(scene, scene['exposure_groups'], check_transport=not transport_checked)
    seen = {}
    views = {view['id']: view for view in scene['views']}
    for report in reports:
        view = views[report['view']]
        group = group_for(scene, view)
        cohort = [v['id'] for v in scene['views'] if group_for(scene, v) == group]
        expected = record['measurements'][view['id']]
        pair = (report['exposure_stops'], report['white_balance_k'])
        if (report.get('exposure_state') != view['exposure']
                or report.get('exposure_group') != group or report.get('exposure_rule_measurement') != expected
                or report.get('exposure_rule_sha256') != RULE_SHA256
                or report.get('exposure_measurement_sha256') != record['measurement_sha256']
                or report.get('exposure_metered_over') != cohort
                or report.get('exposure_locked_per_group') is not True
                or report.get('white_balance_applied') is not True
                or pair[1] != record['white_balance_k'][group]
                or isinstance(pair[0], bool) or not isinstance(pair[0], (int, float)) or not math.isfinite(pair[0])):
            raise ValueError('Render receipt differs from dominant-light group rule: '+view['id'])
        meters = report.get('group_meters', {})
        median = sorted(row['exposure_stops'] for row in meters.values())[len(cohort)//2] if meters else None
        # Blender stores exposure as an IEEE 754 single-precision camera property.
        camera_median = struct.unpack('<f', struct.pack('<f', median))[0] if median is not None else None
        if list(meters) != cohort or pair[0] != camera_median:
            raise ValueError('Group exposure is not the complete-cohort upper median')
        if group in seen and seen[group] != pair:
            raise ValueError('Multiple exposure/white balance values in one group')
        seen[group] = pair
