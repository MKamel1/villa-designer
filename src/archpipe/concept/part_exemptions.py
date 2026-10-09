"""Bounded, explicit legacy dressing exceptions for the C3 migration.

Only the frozen translated shape is exempt from the proxy screen. Solid
geometry, winding, axes and material admission still apply. These records
retain existing appearance under the phase 2c constraint; they do not certify
the represented object's morphology. Renaming is irrelevant to admission.
"""
import hashlib
import json
from pathlib import Path

from .physical_part import PartError

RECORD = Path(__file__).resolve().parents[3] / 'knowledge/c3-part-exemptions.json'


def shape_digest(faces):
    points = [p for f in faces for p in f]
    low = [min(p[i] for p in points) for i in range(3)]
    normalized = []
    for face in faces:
        vertices = [tuple(round(p[i]-low[i], 6) for i in range(3)) for p in face]
        normalized.append(min(tuple(vertices[j:]+vertices[:j]) for j in range(len(vertices))))
    return hashlib.sha256(json.dumps(sorted(normalized), separators=(',', ':')).encode()).hexdigest()


def records():
    from .build_cache import immutable
    value = RECORD.read_text(encoding='utf-8')
    return immutable('c3-part-exemptions', value, lambda: json.loads(value)['records'])


def exemption_for(kind, faces):
    matching = [r for r in records() if r['kind'] == kind]
    if not matching:
        return None
    digest = shape_digest(faces)
    match = next((r for r in matching if digest in r['shape_sha256']), None)
    return {'code': match['code'], 'reason': match['reason']} if match else None


def validate_exemption(kind, faces, exemption):
    if exemption != exemption_for(kind, faces) or exemption is None:
        raise PartError('unregistered or changed proxy exemption for '+kind)


def annotate(record):
    """Called by the legacy dressing/cord builders, never by the admission sink."""
    exemption = exemption_for(record['part_kind'], record['faces'])
    if exemption:
        record['proxy_exemption'] = exemption
    return record
