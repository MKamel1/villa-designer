"""RA: the approval guards stay closed on drift without an approved cause; the 2026-11 review is consistent."""
import json
from pathlib import Path

import pytest

from archpipe.concept import mounting_resume as MR, final_mounting as FM
from archpipe.concept import exterior_mounting  # noqa: F401  (guard lives there; exercised by tests/test_exterior_mounting.py)

ROOT = Path(__file__).resolve().parents[2]
K = ROOT / 'knowledge'
REVIEW = json.loads((K / 'approvals-review/2026-11-review.json').read_text())


def scene_for(row_new, host='h'):
    box = [0, 0, 0, 1, 1, 1]
    return dict(mounting_movements=[dict(id='m', host_id=host, old=box, new=row_new, proposed_faces=[[[0, 0, 0]]])],
                meshes=[dict(id='m', faces=[], mounting={})])


def authority(tmp_path, new):
    p = tmp_path / 'a.json'
    p.write_text(json.dumps(dict(rows=[dict(id='m', host_id='h', old=[0, 0, 0, 1, 1, 1], new=new)])))
    return p


def test_unexplained_drift_still_fails(tmp_path):
    approved = [0, 0, 0, 1, 1, 1.5]
    drifted = [0, 0, 0, 1, 1, 1.5 + 1e-6]           # 1 micron: far below any physical meaning, still refused
    with pytest.raises(ValueError, match='approved schedule drift; new lead review required'):
        MR.apply_approvals(scene_for(drifted), authority(tmp_path, approved))


def test_host_change_still_fails(tmp_path):
    with pytest.raises(ValueError, match='approved schedule drift'):
        MR.apply_approvals(scene_for([0, 0, 0, 1, 1, 1.5], host='other'), authority(tmp_path, [0, 0, 0, 1, 1, 1.5]))


def test_unchanged_row_stays_quiet(tmp_path):
    s = scene_for([0, 0, 0, 1, 1, 1.5])
    MR.apply_approvals(s, authority(tmp_path, [0, 0, 0, 1, 1, 1.5]))
    assert s['lead_approved_count'] == 1


def test_final_guard_refuses_drift():
    rows = {'m': dict(id='m', host_id='h', old=[0] * 6, new=[1] * 6)}
    with pytest.raises(ValueError, match='final approved schedule drift'):
        FM.validate_rows(rows, [dict(id='m', host_id='h', old=[0] * 6, new=[1, 1, 1, 1, 1, 1.0001])])


def test_review_accepts_only_rows_with_a_cause_and_passing_rules():
    assert REVIEW['rows']
    for r in REVIEW['rows']:
        if r['decision'] == 'accept':
            assert r['caused_by'] and all(r['rules'].values()), r['id']
        else:
            assert not all(r['rules'].values()), r['id']
    assert REVIEW['ablation_remaining']['both'] == []      # nothing unexplained is left over


def test_accepted_rows_are_in_the_approval_file_and_rejected_are_not():
    files = {}
    for r in REVIEW['rows']:
        rows = files.setdefault(r['file'], {x['id']: x for x in json.loads((K / r['file']).read_text())['rows']})
        row = rows[r['id']]
        if r['decision'] == 'accept':
            assert row['old'] == r['new_old'] and row['new'] == r['new_new'] and row['host_id'] == r['host_id']
            assert row['original_2026_10_05']['new'] == r['approved_new']      # audit trail kept
            assert row['re_review']['review'].endswith('2026-11-review.json')
        else:
            assert row['new'] == r['approved_new'] and 're_review' not in row


def test_apply_refuses_a_row_without_cause(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location('review_tool', K / 'approvals-review/review_tool.py')
    tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)
    bad = json.loads(json.dumps(REVIEW)); bad['rows'][0]['caused_by'] = []
    (tmp_path / 'knowledge').mkdir()
    (tmp_path / 'knowledge' / bad['rows'][0]['file']).write_text((K / bad['rows'][0]['file']).read_text())
    monkeypatch.setattr(tool, 'ROOT', tmp_path)
    review = tmp_path / 'r.json'; review.write_text(json.dumps(bad)); monkeypatch.setattr(tool, 'REVIEW', review)
    with pytest.raises(ValueError, match='without an approved cause'):
        tool.apply()


def test_judge_rejects_unexplained_or_floating_rows():
    import importlib.util
    spec = importlib.util.spec_from_file_location('review_tool', K / 'approvals-review/review_tool.py')
    tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)
    evidence = json.loads((K / 'approvals-review/evidence/drift-collected.json').read_text())
    still = {c: set(json.loads((K / f'approvals-review/evidence/ablate-{c}.json').read_text())) for c in (*tool.CAUSES, 'both')}
    row = evidence[0]
    assert tool.judge(row, still)[0] == 'accept'
    unexplained = dict(still, both={row['id']})                    # an ablation that does not remove the drift
    assert tool.judge(row, unexplained)[0] == 'reject'
    floating = json.loads(json.dumps(row)); floating['mesh']['bounds'][2] += 0.003            # floats 3 mm above the floor
    assert tool.judge(floating, still)[0] == 'reject'
    moved_plane = json.loads(json.dumps(row)); moved_plane['new'][2] += 0.005; moved_plane['old'][2] += 0.005
    assert tool.judge(moved_plane, still)[0] == 'reject'
    changed_fix = json.loads(json.dumps(row)); changed_fix['new'][5] += 0.01
    assert tool.judge(changed_fix, still)[0] == 'reject'
