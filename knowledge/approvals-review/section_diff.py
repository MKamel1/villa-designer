"""RA2: item-level diff of the furniture room-context inputs, receipt-era tree (038e476) vs current build.

Usage: python section_diff.py OLD_procedural-scene.json NEW_procedural-scene.json OUT.json
Both scenes are diagnostic exports (receipts bypassed). Output lists, per receipt section, whether the
digest changed and which items (by id) were added / removed / changed, so each can be attributed to a cause.
"""
import gzip, json, sys
from pathlib import Path
from archpipe.concept.furniture_stage2 import digest, room_context_inputs
from archpipe.blender.element_ids import without_ids  # the receipt is computed mid-build, before P2 attaches ids

ROOT = Path(__file__).resolve().parents[2]
load = lambda p: json.loads(gzip.decompress(Path(p).read_bytes()) if str(p).endswith('.gz') else Path(p).read_text())
fr = load(ROOT / 'knowledge/furniture-stage2.json.gz'); br = load(ROOT / 'knowledge/parents-bed.json.gz')
models = [dict(m, review_geometry=fr['geometry'][m['asset']]) for m in fr['models']] + br['models']


def inputs(path):
    raw = without_ids(load(path)); c = raw['authoring_room_context']
    return room_context_inputs(raw, c['layout'], c['specification'], c['furniture'], models)


def keyed(section, rows):
    if section == 'architecture':
        return {i: r for i, r in enumerate(rows)}
    if isinstance(rows, dict):
        return rows
    return {r.get('id', i) if isinstance(r, dict) else i: r for i, r in enumerate(rows)}


old, new = inputs(sys.argv[1]), inputs(sys.argv[2])
report = {}
for sec in new:
    same = digest(old[sec]) == digest(new[sec])
    entry = dict(changed=not same, receipt_component=fr['room_context_components_sha256'].get(sec) == digest(old[sec]))
    if not same:
        if sec == 'architecture':
            a = {digest(r): r for r in old[sec]}; b = {digest(r): r for r in new[sec]}
            entry.update(faces_removed=len(set(a) - set(b)), faces_added=len(set(b) - set(a)),
                         removed_sample=[dict(part_kind=a[k].get('part_kind'), host=a[k].get('source_id'), room=a[k].get('room')) for k in list(set(a) - set(b))[:400]],
                         added_sample=[dict(part_kind=b[k].get('part_kind'), host=b[k].get('source_id'), room=b[k].get('room')) for k in list(set(b) - set(a))[:400]])
        else:
            a, b = keyed(sec, old[sec]), keyed(sec, new[sec])
            entry.update(added=sorted(map(str, set(b) - set(a))), removed=sorted(map(str, set(a) - set(b))),
                         changed_ids=sorted(str(k) for k in set(a) & set(b) if digest(a[k]) != digest(b[k])))
    report[sec] = entry
Path(sys.argv[3]).write_text(json.dumps(report, indent=1, default=str))
for sec, e in report.items():
    print(sec, 'CHANGED' if e['changed'] else 'same', 'receipt-matches-old-tree' if e['receipt_component'] else 'RECEIPT-DIFFERS-FROM-OLD-TREE')
