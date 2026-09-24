"""Evidence-aware villa guidance. Calculations are not design approval.

All paths are project-relative. Shared knowledge contains no client taste.
Evidence locators refer to an exact edition or a dated web section.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATEGORIES = {'technical_requirement', 'professional_recommendation',
              'qualitative_principle', 'project_target'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def local_path(path, root=ROOT):
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError('path must stay inside this project')
    return resolved


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


@lru_cache(maxsize=8)
def _indexed(content):
    data = json.loads(content)
    for collection in ('sources', 'evidence', 'precedents', 'stages'):
        rows = data[collection]
        keys = [row['id'] for row in rows]
        if len(set(keys)) != len(keys):
            raise ValueError('duplicate identifiers in ' + collection)
        data[collection] = dict(zip(keys, rows))
    return data


def library(root=ROOT):
    # Content, rather than timestamps, invalidates editions and corrected passages.
    return deepcopy(_indexed((root / 'knowledge/library.json').read_text(encoding='utf-8')))


def evidence_status(card, sources, facts=None, numerical=False):
    """Fail closed on edition, locator, units, verification and applicability."""
    reasons = []
    source = sources.get(card.get('source_id'), {})
    if card.get('category') not in CATEGORIES:
        reasons.append('unknown evidence category')
    if source.get('status') != 'content_verified' or card.get('status') != 'verified':
        reasons.append('source passage has not been verified')
    if not card.get('locator') or not card.get('edition') or card.get('edition') != source.get('edition'):
        reasons.append('missing locator or wrong edition')
    if not card.get('verification') or not card.get('conditions'):
        reasons.append('verification method or applicability conditions missing')
    for key, allowed in card.get('applies_when', {}).items():
        fact = (facts or {}).get(key, {})
        if fact.get('status') not in ('confirmed', 'example') or fact.get('value') not in allowed:
            reasons.append('applicability unresolved or incompatible: ' + key)
    if numerical:
        if card.get('category') not in ('technical_requirement', 'professional_recommendation'):
            reasons.append('qualitative advice or project preference is not a published numerical rule')
        if not card.get('unit') or not card.get('original_page_checked'):
            reasons.append('units or original-page numerical verification missing')
        if not card.get('regression_test'):
            reasons.append('numerical rule lacks a regression check')
    return {'status': 'unresolved' if reasons else 'applicable', 'reasons': reasons}


def numerical_target(card, sources, value, unit, facts=None):
    """Validate a proposed threshold against a checked transcription; never convert units implicitly."""
    result = evidence_status(card, sources, facts, numerical=True)
    reasons = result['reasons']
    if unit != card.get('unit'):
        reasons.append('target units differ from the verified passage')
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value != card.get('verified_value')):
        reasons.append('target dimension differs from the verified original value')
    return {'enabled': not reasons, 'status': 'unresolved' if reasons else 'verified', 'reasons': reasons}


def lookup_evidence(query='', stage=None, facts=None, limit=8, root=ROOT):
    if stage is not None and (type(stage) is not int or stage not in range(8)):
        raise ValueError('stage must be an integer from 0 to 7')
    if not 1 <= limit <= 20:
        raise ValueError('limit must be 1 to 20')
    data = library(root)
    terms = query.lower().split()
    candidates = []
    for collection in ('evidence', 'precedents'):
        for card in data[collection].values():
            if stage is not None and stage not in card['stages']:
                continue
            haystack = json.dumps(card).lower()
            score = sum(term in haystack for term in terms)
            if terms and not score:
                continue
            result = deepcopy(card)
            result['source'] = data['sources'].get(card['source_id'], {})
            result['applicability'] = evidence_status(card, data['sources'], facts)
            candidates.append((score, result))
    candidates.sort(key=lambda entry: (-entry[0], entry[1]['id']))
    return {'results': [v for _, v in candidates[:limit]], 'total': len(candidates),
            'unresolved': [] if candidates else ['No matching verified or identified evidence; do not invent a passage.']}


def rule_audit():
    from .rules import RULES
    return [{'id': rule.id, 'stage': rule.stage, 'kind': rule.kind,
             'reference': rule.reference, 'evidence_refs': list(rule.evidence_refs),
             'status': 'unresolved', 'enabled_for_approval': False,
             'reason': 'Readable citation has no verified edition-specific passage. Legacy computation is diagnostic only.'}
            for rule in RULES.values()]


def artifact_status(record, root=ROOT):
    try:
        path = local_path(record['path'], root)
        return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == record.get('sha256')
    except (KeyError, ValueError, OSError, TypeError):
        return False


def _project(path, root):
    project = read_json(local_path(path, root))
    if not project.get('id') or not project.get('revision'):
        raise ValueError('project needs id and revision')
    return project


def stage_context(stage, project_path='knowledge/projects/villa-pilot.json', root=ROOT):
    if type(stage) is not int or stage not in range(8):
        raise ValueError('stage must be an integer from 0 to 7')
    project, data = _project(project_path, root), library(root)
    package = data['stages'][str(stage)]
    facts = project.get('facts', {})
    missing = [name for name in package['inputs'] if
               facts.get(name, {}).get('value') is None or
               facts.get(name, {}).get('status') not in ('confirmed', 'example')]
    relevant = [v for v in project.get('decisions', []) if stage in v.get('affects', [])]
    selected = {name: facts.get(name) for name in package['inputs']}
    evidence = [dict(data['evidence'][key], applicability=evidence_status(
        data['evidence'][key], data['sources'], facts)) for key in package['evidence']]
    return {'stage': stage, 'name': package['name'], 'project': project['id'],
            'revision': project['revision'], 'example': project.get('example', False),
            'brief': project.get('brief', {}), 'facts': selected, 'decisions': relevant,
            'missing_inputs': missing, 'knowledge': evidence,
            'package': package, 'next_deliverables': package['deliverables'],
            'dependency_key': digest([project['id'], project['revision'], selected, relevant, package, evidence,
                                      [data['sources'][v['source_id']] for v in evidence]])}


def _positive(value, label, zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or (value < 0 if zero else value <= 0):
        raise ValueError(label + ' must be a finite ' + ('nonnegative' if zero else 'positive') + ' number')
    return value


def area_check(schedule):
    """Add explicitly separate areas; no invented net-to-gross standard."""
    rows = schedule['rooms']
    if not rows or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('area schedule needs unique room identifiers')
    net = sum(_positive(r['area_m2'], r['id']) for r in rows)
    allowances = {key: _positive(schedule[key], key, zero=True)
                  for key in ('circulation_m2', 'walls_m2', 'structure_m2', 'services_m2')}
    gross = net + sum(allowances.values())
    available = _positive(schedule['available_m2'], 'available_m2')
    return {'check': 'area', 'status': 'pass' if gross <= available else 'fail',
            'net_m2': net, 'gross_m2': gross, 'available_m2': available,
            'remaining_m2': available - gross, 'allowances': allowances,
            'basis': 'Project area allowances, not published dimensional standards.'}


def concept_checks(concept):
    """Client privacy intent and declared coordination gaps; not span certification."""
    rooms = concept.get('rooms', {})
    links = concept.get('connections', [])
    if not rooms or any(len(edge) != 2 or any(node not in rooms for node in edge) for edge in links):
        raise ValueError('concept connections must name two existing rooms')
    start = concept.get('entrance')
    if start not in rooms:
        raise ValueError('concept needs an entrance room')
    private = [key for key, kind in rooms.items() if kind == 'private']
    visited, pending = set(), [start]
    while pending:
        node = pending.pop()
        if node in visited or rooms[node] == 'public':
            continue
        visited.add(node)
        pending.extend(b if a == node else a for a, b in links if node in (a, b))
    blocked = [node for node in private if node not in visited]
    return [{'check': 'private_access', 'status': 'fail' if blocked else 'pass',
             'rooms': blocked, 'basis': 'Pilot household requires private access without crossing entertaining rooms.'},
            {'check': 'structural_coordination', 'status': 'unresolved' if concept.get('unsupported_spans') else 'not_certified',
             'issues': concept.get('unsupported_spans', []), 'basis': 'Engineering sizing and certification excluded.'},
            {'check': 'comfort', 'status': 'unresolved' if concept.get('comfort_issues') else 'not_measured',
             'issues': concept.get('comfort_issues', [])}]


_REVIEWS = {}


def review_stage(stage, project_path='knowledge/projects/villa-pilot.json', root=ROOT):
    context = stage_context(stage, project_path, root)
    project = _project(project_path, root)
    state = project.get('stages', {}).get(str(stage), {})
    package = context['package']
    artifacts = state.get('artifacts', {})
    freshness = {name: artifact_status(record, root) for name, record in artifacts.items()}
    model_record = project.get('model', {}) if stage in (4, 5, 7) else {}
    model_fresh = artifact_status(model_record, root) if model_record else False
    binding = project.get('render_binding', {}) if stage == 7 else {}
    requirements = project.get('requirements', []) if stage == 7 else []
    presentation_freshness = {
        'render': artifact_status(binding.get('render', {}), root),
        'input': artifact_status(binding.get('input', {}), root),
        'requirements': [artifact_status(r.get('artifact', {}), root) for r in requirements],
    } if stage == 7 else {}
    audits = [row for row in rule_audit() if row['stage'] == stage or stage == 7]
    previous_reviews = [review_stage(earlier, project_path, root) for earlier in range(stage)] if not project.get('example') else []
    review_state = {name:value for name,value in state.items() if name != 'approval'}
    key = digest([context, review_state, freshness, model_record, model_fresh, audits,
                  project.get('area_schedule') if stage == 2 else None,
                  project.get('concepts') if stage in (3, 7) else None,
                  project.get('render_binding') if stage == 7 else None,
                  project.get('requirements') if stage == 7 else None, presentation_freshness,
                  project.get('scope'), project.get('example'), project.get('selected_concept'),
                  [(v['dependency_key'], v['approved']) for v in previous_reviews]])
    cache_key = digest([key, state.get('approval', {})])
    if cache_key in _REVIEWS:
        return dict(deepcopy(_REVIEWS[cache_key]), reused=True)
    unresolved = ['Missing project fact: ' + name for name in context['missing_inputs']]
    unresolved += ['Evidence: ' + card['id'] for card in context['knowledge']
                   if card['applicability']['status'] != 'applicable']
    unresolved += ['Deliverable missing or changed: ' + name for name in package['deliverables']
                   if not freshness.get(name)]
    qualitative = []
    for item in package['approval']:
        entry = state.get('qualitative', {}).get(item, {})
        valid = (entry.get('status') == 'pass' and entry.get('reviewer') and entry.get('notes')
                 and entry.get('revision') == project['revision'])
        qualitative.append({'criterion': item, 'review': entry, 'resolved': bool(valid)})
        if not valid:
            unresolved.append('Qualitative review: ' + item)
    checks = []
    if stage == 2:
        if project.get('area_schedule'):
            checks.append(area_check(project['area_schedule']))
        else:
            unresolved.append('Area schedule missing')
    if stage in (3, 7):
        concepts = project.get('concepts', [])
        if len(concepts) < 3 or len({v['id'] for v in concepts}) < 3:
            unresolved.append('Three distinct concept alternatives required')
        for concept in concepts:
            checks.extend(dict(c, concept=concept['id']) for c in concept_checks(concept))
        chosen = project.get('selected_concept')
        if chosen not in [v['id'] for v in concepts]:
            unresolved.append('Concept recommendation missing')
        for check in checks:
            if check.get('concept') == chosen and check['status'] in ('fail', 'unresolved'):
                unresolved.append('Selected concept: ' + check['check'])
    if stage in (4, 5, 7):
        if model_fresh:
            from .review_extract import review_model
            result = review_model(read_json(local_path(model_record['path'], root)),
                                  scope=project.get('scope', 'dwelling'))
            checks.append({'check': 'legacy_geometry', 'status': 'diagnostic', 'result': result})
        else:
            unresolved.append('Measured model missing or changed')
    if stage in (3, 4, 5, 7):
        unresolved += ['Unverified legacy rule: ' + row['id'] for row in audits]
    if stage == 7:
        if (not binding or not presentation_freshness['render']
                or not presentation_freshness['input']
                or binding.get('model_sha256') != model_record.get('sha256')
                or binding.get('revision') != project['revision']):
            unresolved.append('Presentation is not bound to the reviewed revision, model and rendering input')
        if not requirements or any(not r.get('response') for r in requirements) or not all(presentation_freshness['requirements']):
            unresolved.append('Client requirement traceability incomplete')
    if any(c['status'] == 'fail' and 'concept' not in c for c in checks):
        unresolved.append('Deterministic check failed')
    if project.get('example'):
        unresolved.append('Capability example cannot approve a real villa')
    elif stage:
        for earlier, previous in enumerate(previous_reviews):
            if not previous['approved']:
                unresolved.append('Earlier stage approval missing or stale: ' + str(earlier))
    if any(f.get('status') == 'example' for f in context['facts'].values() if f):
        unresolved.append('Example facts must be replaced for real design approval')
    approval = state.get('approval', {})
    ready = not unresolved
    approved = bool(ready and approval.get('status') == 'approved' and approval.get('by')
                    and approval.get('date') and approval.get('revision') == project['revision']
                    and approval.get('review_key') == key)
    output = {'stage': stage, 'revision': project['revision'], 'checks': checks,
              'qualitative': qualitative, 'unresolved': unresolved,
              'ready_for_client_approval': ready, 'approved': approved,
              'evidence_audit': audits, 'dependency_key': key, 'reused': False,
              'limitations': 'Design guidance only; no local-code, permit or engineering certification. Readiness never records client approval.'}
    if len(_REVIEWS) >= 64:
        _REVIEWS.clear()
    _REVIEWS[cache_key] = deepcopy(output)
    return output
