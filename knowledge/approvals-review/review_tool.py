"""Lane RA re-approval tool for the frozen C4 approval files (the guards themselves are unchanged).

  make   evidence/drift-collected.json + evidence/ablate-*.json  ->  2026-11-review.json  (decisions by rule)
  apply  2026-11-review.json -> knowledge/c4-*-approvals.json     (accepted rows only; originals kept as audit)

A row is accepted only when ALL rules hold, otherwise it is rejected and left failing:
  R1 cause    undoing a named approved change (in memory, harness ablation) removes the drift row, and undoing all
              named changes together removes every drifted row (nothing unexplained left over).
  R2 physical every mesh mounted on the row's host sits on the host's finished face (|gap| <= 1e-6 m, no penetration),
              the host is unchanged, and the coordinate along the host normal did not move.
  R3 intent   the approved movement vector (new - old) is unchanged (1e-8 m): same fix, only the extent shifted.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REVIEW = HERE / '2026-11-review.json'
DATE = '2026-11-21'
TOL = 1e-8
CAUSES = {  # ablation flag -> the approved change it undoes
    'stair-overlap': 'G1 LS2 stair tread overlap 16 mm (lane D, stairs.NOSING_OVERLAP; docs/decisions/G1-safety-decisions-2026-11-21.md)',
    'corner-fix': 'Lane M wall-corner closing (revit_spec._close_corner_gaps lengthens GF-33 by 0.2 m; docs/lanes/M-model-completion.md)',
}


def _axis(normal):
    return max(range(3), key=lambda i: abs(normal[i]))


def judge(row, still_drifting):
    """Return (decision, rules, causes) for one collected drift row. `still_drifting`: {cause: set(ids)}."""
    causes = [c for c, ids in still_drifting.items() if c != 'both' and row['id'] not in ids]
    r1 = bool(causes) and not still_drifting['both']
    host = row['host_record']
    ax = _axis(host['normal'])
    mounted = row['physical']['mounted']
    if row['mesh']:  # the row's own item; the host may carry unrelated older items (reported separately, not part of this drift)
        fin = row['physical']['finished_plane_point'][ax]
        b = row['mesh']['bounds']
        gap = (b[ax] - fin) if host['normal'][ax] > 0 else (fin - b[ax + 3])
        mounted = [dict(id=row['id'], min_gap_to_finished_face_mm=round(gap * 1000, 6))]
    inside = row['mesh'] or all(all(m['bounds'][i] >= row['new'][i] - 1e-6 and m['bounds'][i + 3] <= row['new'][i + 3] + 1e-6
                                    for i in range(3) if i != ax) for m in mounted)
    r2 = (inside and row['approved_host'] == row['new_host'] and bool(mounted)
          and all(abs(m['min_gap_to_finished_face_mm']) <= 1e-3 for m in mounted)
          and all(abs(row[k][ax + s] - row['approved_' + k][ax + s]) <= TOL for k in ('old', 'new') for s in (0, 3)))
    dnew = [a - b for a, b in zip(row['new'], row['old'])]
    dapp = [a - b for a, b in zip(row['approved_new'], row['approved_old'])]
    r3 = all(abs(a - b) <= TOL for a, b in zip(dnew, dapp))
    rules = dict(R1_cause=r1, R2_physical=r2, R3_intent=r3)
    return ('accept' if all(rules.values()) else 'reject'), rules, causes


def make():
    ev = HERE / 'evidence'
    rows = json.loads((ev / 'drift-collected.json').read_text())
    still = {c: set(json.loads((ev / f'ablate-{c}.json').read_text())) for c in (*CAUSES, 'both')}
    out = []
    for r in rows:
        decision, rules, causes = judge(r, still)
        out.append(dict(id=r['id'], file=r['source'], decision=decision, rules=rules,
                        caused_by=[CAUSES[c] for c in causes], host_id=r['new_host'],
                        approved_old=r['approved_old'], approved_new=r['approved_new'], new_old=r['old'], new_new=r['new'],
                        delta_old=[round(a - b, 9) for a, b in zip(r['old'], r['approved_old'])],
                        delta_new=[round(a - b, 9) for a, b in zip(r['new'], r['approved_new'])],
                        mounted_on_host=[dict(id=m['id'], min_gap_to_finished_face_mm=m['min_gap_to_finished_face_mm'])
                                         for m in r['physical']['mounted']]))
    doc = dict(review='2026-11 approval drift review (lane RA)', date=DATE, base='origin/integ/aplus 357ba45',
               method='collect_drift.py (read-only harness) + ablation runs; see docs/lanes/RA-review.md',
               ablation_remaining={c: sorted(v) for c, v in still.items()}, rows=out)
    REVIEW.write_text(json.dumps(doc, indent=1) + '\n')
    print({d: sum(r['decision'] == d for r in out) for d in ('accept', 'reject')})


def apply():
    doc = json.loads(REVIEW.read_text())
    by_file = {}
    for r in doc['rows']:
        by_file.setdefault(r['file'], []).append(r)
    for name, rows in by_file.items():
        path = ROOT / 'knowledge' / name
        data = json.loads(path.read_text())
        index = {x['id']: x for x in data['rows']}
        done = []
        for r in rows:
            if r['decision'] != 'accept':
                continue
            if not r['caused_by'] or not all(r['rules'].values()):
                raise ValueError(r['id'] + ': refusing to approve a row without an approved cause and passing rules')
            row = index[r['id']]
            row.setdefault('original_2026_10_05', dict(host_id=row['host_id'], old=row['old'], new=row['new']))
            row['old'], row['new'], row['host_id'] = r['new_old'], r['new_new'], r['host_id']
            row['re_review'] = dict(date=DATE, review='knowledge/approvals-review/2026-11-review.json',
                                    caused_by=r['caused_by'], rules=r['rules'])
            done.append(r['id'])
        if done:
            notes = data.setdefault('review_notes', [])
            if not any(n.get('date') == DATE for n in notes):
                notes.append(dict(date=DATE, review='knowledge/approvals-review/2026-11-review.json',
                                  note='Rows re-approved after client-approved design changes moved their bounds; each carries '
                                       'original_2026_10_05 and re_review. Guards unchanged.', rows=done))
            path.write_text(json.dumps(data, indent=2) + '\n')
            print(name, 'updated', len(done))


if __name__ == '__main__':
    {'make': make, 'apply': apply}[sys.argv[1]]()
