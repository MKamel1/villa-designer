"""Derive the rooms that get the 16 mm lens from a flyaudit run of a 24 mm route, by the rule in tour-policy.json.

usage: python scripts/lens_rooms.py knowledge/flyaudit/wt-villa4-tour/frames.json
Writes knowledge/flythrough/lens-rooms.json (shares per room and the chosen list). The rule is the audit's own wall_dominated
category over the sweeping and holding frames of the room; nothing here is judged by eye.
"""
import collections, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def derive(frames, rule):
    n = collections.Counter(); w = collections.Counter()
    for r in frames:
        if r['mode'] in rule['modes'] and r['room']:
            n[r['room']] += 1; w[r['room']] += r['cat'] == 'wall_dominated'
    share = {k: round(w[k]/n[k], 3) for k in n}
    return share, sorted(k for k, v in share.items() if v >= rule['min_wall_dominated_share'])


if __name__ == '__main__':
    rule = json.loads((ROOT/'knowledge/flythrough/tour-policy.json').read_text())['lens_room_rule']
    frames = json.loads(Path(sys.argv[1]).read_text())
    share, rooms = derive(frames, rule)
    out = dict(schema='flythrough-lens-rooms/1', source=sys.argv[1], rule=rule, wall_dominated_share_at_24mm=share, rooms=rooms)
    (ROOT/'knowledge/flythrough/lens-rooms.json').write_text(json.dumps(out, indent=1))
    print(len(rooms), rooms)
