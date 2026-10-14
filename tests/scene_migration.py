"""Replay the exact authored contents migration against a reviewed full scene.

Every changed/new row must match its frozen value. Unrelated rows still enter
the original complete-scene hash; no indoor or outdoor content is excluded.
This numerical receipt does not grant visual approval to the garments.
"""
from copy import deepcopy
import gzip
import json
from pathlib import Path


def prior_reviewed_rows(rows):
    record = json.loads(gzip.decompress((Path(__file__).parent/'fixtures/integ6-scene-migration.json.gz').read_bytes()))
    by_id = {m['id']:m for m in rows}
    if len(by_id) != len(rows):
        raise ValueError('duplicate scene identifiers')
    for row in record['added']:
        if by_id.get(row['id']) != row:
            raise ValueError(row['id']+': changed integration-6 addition')
        del by_id[row['id']]
    for change in record['changed']:
        row = change['after']
        if by_id.get(row['id']) != row:
            raise ValueError(row['id']+': changed integration-6 replacement')
        by_id[row['id']] = change['before']
    for row in record['removed']:
        if row['id'] in by_id:
            raise ValueError(row['id']+': retired proxy survives')
        by_id[row['id']] = row
    if set(by_id) != set(record['reviewed_ids']):
        raise ValueError('full reviewed scene inventory changed')
    return [deepcopy(by_id[k]) for k in record['reviewed_ids']]
