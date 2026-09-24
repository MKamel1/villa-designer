"""Reusable review boundary for command-line, MCP, and future assistants."""
from dataclasses import asdict

from .from_extract import convert
from .rules import review

ROOM_CONTEXT_RULES = {'SAN-01', 'CIRC-01', 'CIRC-02'}


def review_model(data: dict, *, scope: str = 'dwelling', level: str | None = None) -> dict:
    if scope not in ('room', 'dwelling'):
        raise ValueError('scope must be room or dwelling')
    converted = convert(data)
    findings = review(converted.project, level)
    outside = [f for f in findings if scope == 'room' and f.rule in ROOM_CONTEXT_RULES]
    applicable = [f for f in findings if f not in outside]
    return {
        'scope': scope,
        'disclaimer': 'Design guidance, not code compliance. No jurisdiction pack loaded.',
        'passed': not any(f.severity in ('violation', 'warning') for f in applicable),
        'approval_ready': False,
        'evidence_status': 'Legacy targets unverified; passed describes diagnostic checks only. Use review_stage for approval readiness.',
        'findings': [asdict(f) for f in applicable],
        'not_assessed': [{'rule': name, 'reason': 'Requires a complete dwelling; input is an isolated room.'}
                         for name in sorted(ROOM_CONTEXT_RULES)] if scope == 'room' else [],
        'context_findings': [asdict(f) for f in outside],
        'conversion_notes': converted.notes,
        'furniture_count': len(converted.project.furniture),
    }
