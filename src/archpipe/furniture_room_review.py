"""Compare identical fixed-room reviews under the 2026-10-09 decision.

All access distances are metres. The 0.005 m allowance is the client's
five-millimetre replacement allowance, not an access standard. Inherited
findings remain in both input reports. Body screens may retain an existing
fixed-element conflict, but cannot introduce one with another fixed element.
"""
from __future__ import annotations

import re

CLIENT_SOURCE = 'Lead/client fixed-layout replacement decision 2026-10-09'
ACCESS_ALLOWANCE_M = .005


def baseline_relative_review(baseline, candidate, *, target_prefixes, fixed_items=()):
    """Fail closed on missing side measurements or new physical findings.

    target_prefixes includes procedural part prefixes and imported instance
    prefixes. fixed_items maps existing furniture IDs to their part prefixes;
    this joins their physical meshes and planning proxies without hiding a
    conflict with a different item. Boundary distance is the maximum outside
    bounds-corner distance in the existing boundary screen's detail field.
    """
    prefixes = tuple(target_prefixes)
    fixed = sorted(fixed_items, key=len, reverse=True)
    def canonical(identifier):
        if identifier.startswith(prefixes):
            return 'replacement'
        for mark in fixed:
            if identifier == mark or identifier.startswith(('furn-'+mark+'-', 'dress-pillow-'+mark+'-')):
                return mark
        return identifier
    def key(row):
        pair = [canonical(row['source_id']), canonical(row['reference_id'])]
        if row['query']=='body-overlap':
            pair.sort()
        return row['query'], *pair
    def boundary(report):
        rows = [r for r in report['findings'] if r['query']=='bed-part-room-boundary']
        distances = []
        for row in rows:
            match = re.search(r'distance ([0-9.eE+-]+) m', row.get('detail',''))
            if not match:
                raise ValueError('boundary comparison requires measured outside distance')
            distances.append(float(match.group(1)))
        return max(distances, default=0.)
    failures=[];columns=[]
    old={(r['item'],r['side']):r for r in baseline['clearances']}
    new={(r['item'],r['side']):r for r in candidate['clearances']}
    if len(old)!=len(baseline['clearances']) or len(new)!=len(candidate['clearances']):
        raise ValueError('room comparison requires unique access sides')
    for identity in sorted(old.keys() | new.keys()):
        before,after=old.get(identity),new.get(identity)
        if before is None or after is None:
            failures.append(dict(check='access',item=identity[0],side=identity[1],reason='missing same-card measurement'))
            continue
        if before['source']!=after['source'] or before['required_m']!=after['required_m']:
            raise ValueError('baseline and candidate must use identical access cards')
        passes=after['achieved_m']>=before['achieved_m']-ACCESS_ALLOWANCE_M-1e-9
        row=dict(check='access',item=identity[0],side=identity[1],baseline_m=before['achieved_m'],
            candidate_m=after['achieved_m'],required_m=after['required_m'],ok=passes,source=after['source'])
        columns.append(row)
        if not passes:failures.append(row)
    before_distance,after_distance=boundary(baseline),boundary(candidate)
    columns.append(dict(check='boundary',baseline_m=before_distance,candidate_m=after_distance,
                        required_m=0.,ok=after_distance<=before_distance+1e-9))
    if after_distance>before_distance+1e-9:failures.append(columns[-1])
    old_findings={key(r) for r in baseline['findings']
                  if r['query'] not in ('bed/storage-clearance','bed-part-room-boundary')}
    for row in candidate['findings']:
        if row['query'] in ('bed/storage-clearance','bed-part-room-boundary'):
            continue
        if key(row) not in old_findings:
            failures.append(dict(check=row['query'],finding=row,reason='new conflict/failure versus procedural baseline'))
    return dict(ok=not failures,findings=failures,comparison=columns,source=CLIENT_SOURCE,
                baseline=baseline,candidate=candidate,
                layout_findings=baseline['findings'],allowance_m=ACCESS_ALLOWANCE_M)
