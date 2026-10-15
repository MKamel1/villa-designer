"""Measured presentation evidence; never an exposure override or QA waiver.

Exposure stops are base-two camera-gain units: one additional stop doubles
gain. A cohort is the complete authored list sharing an exposure state.
"""
from __future__ import annotations

import math


def require_subject_bindings(scene, report):
    """Refuse measured subject rows that omit owned physical assembly meshes."""
    from .villa_render_contract import subject_meshes
    view = next((v for v in scene['views'] if v['id'] == report.get('view')), None)
    rows = report.get('subjects', [])
    declared = view['subjects'] if view is not None else []
    identities = [row['id'] for row in rows]
    if (view is None or len(identities) != len(declared)
            or set(identities) != set(declared)):
        raise ValueError('Measured subject rows do not match declared subjects')
    for row in rows:
        expected = {m['id'] for m in subject_meshes(row['id'], scene['meshes'])}
        if not expected.issubset(set(row.get('matched_objects', []))):
            raise ValueError('Measured subject omits assembly meshes: ' + row['id'])


def caption_evidence(scene, view, report, qa):
    """Keep actual settings and nonpassing measurements beside the image.

    Legacy reports without a named cohort are explicitly unverified. A
    report claiming a current whole-set lock must match the complete scene,
    including diagnostic/retired views that still participate in metering.
    """
    state = report.get('exposure_state')
    cohort = report.get('exposure_metered_over')
    stops = report.get('exposure_stops')
    locked = report.get('exposure_locked_per_state') is True
    verified = False
    legacy_unnamed_lock = locked and state is None and cohort is None
    if locked and not legacy_unnamed_lock:
        expected = [v['id'] for v in scene['views'] if v['exposure'] == view['exposure']]
        if (state != view['exposure'] or report.get('view') != view['id'] or cohort != expected
                or not isinstance(stops, (int, float)) or isinstance(stops, bool) or not math.isfinite(stops)):
            raise ValueError('Measured exposure record does not match the complete authored cohort')
        verified = True
        require_subject_bindings(scene, report)
    checks = qa['checks']
    return {
        'exposure_stops': stops,
        'exposure_state': state,
        'metered_over': cohort,
        'whole_set_lock_verified': verified,
        'exposure_evidence': 'measured whole-set lock' if verified else 'unverified legacy or missing lock record',
        'white_balance_applied': report.get('white_balance_applied'),
        'samples': report.get('samples'),
        'resolution': report.get('resolution'),
        'render_device': report.get('render_device'),
        'device_evidence': ('recorded execution device' if report.get('render_device')
                            else 'legacy device not recorded; do not assume a matching device'),
        'qa_passed': not any(c['status'] == 'FAIL' for c in checks),
        'nonpassing_checks': [dict(c) for c in checks if c['status'] != 'PASS'],
        'disclosure': 'Warnings and failures remain applicable; this record grants no QA or exposure exemption.',
    }
