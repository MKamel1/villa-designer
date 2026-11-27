"""Headings of each full 360 that show nothing new: a blank wall (one wall carries >= 45 % of the rays) or a bright window (glass >= 50 % of the rays or
outside >= 40 %). Read from the audit's own per-frame numbers over the turn's frames, per 30-degree heading bin; a bin is dull when >= 50 % of its frames are.
-> knowledge/flythrough/tour-dull.json; walkthrough_tour sweeps dull bins at the fast rate and never holds the best view on one (client 2026-11-25, the study-game turn).
usage: python scripts/wt_reaim.py <path.json> <audit frames.json>"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
WALL, GLASS, OUT = .45, .5, .4

def dull(r):
    wall = bool(r['top']) and r['top'][0][0].startswith('wall') and r['top'][0][1] >= WALL
    return 'wall' if wall else 'window' if (r['glass_share'] >= GLASS or r['out_share'] >= OUT) else ''

def main(path_file, frames_file):
    P = json.loads(Path(path_file).read_text()); F = {r['i']: r for r in json.loads(Path(frames_file).read_text())}; out = {}
    for s in P['stations']:
        if s['kind'] != 'turn' or not s['room']: continue
        bins = [[] for _ in range(12)]
        for i in range(s['first_frame'], s['last_frame']+1):
            r = F.get(i - i % 2)
            if r: bins[int(round((r['yaw'] % 360)/30.)) % 12].append(dull(r))
        flags = [bool(b) and sum(1 for x in b if x)/len(b) >= .5 for b in bins]
        out[s['room']] = dict(dull=flags, kinds=[max(set(b), key=b.count) if b else '' for b in bins])
        print(s['room'], ''.join('D' if f else '.' for f in flags))
    (ROOT/'knowledge/flythrough/tour-dull.json').write_text(json.dumps(dict(schema='flythrough-tour-dull/1', method=__doc__.split('\n')[0], rule=dict(wall_share=WALL, glass_share=GLASS, out_share=OUT, bin_share=.5), rooms=out), indent=0))

if __name__ == '__main__':
    main(*sys.argv[1:3])
