"""RA2: attribute every changed architectural face (receipt-era tree vs current) to an approved change by region.

Usage: python arch_attribution.py OLD_scene.json NEW_scene.json OUT.json
Faces are the physical_architecture() records (same keying as the receipt). A face present on one side only is
'changed'. Each changed face is assigned to the FIRST zone whose box contains its bbox; the zone boxes come from
the spec diff (specification section): G1 stair overlap/infill/guards/cupboard, G1 lounge door 3.41->3.71,
G1 core door swing, M wall-corner extensions. Anything left is reported as UNEXPLAINED.
"""
import json, sys
from collections import Counter
from pathlib import Path
from archpipe.concept.furniture_stage2 import physical_architecture, digest
from archpipe.blender.element_ids import without_ids

ZONES = [  # name, cause, (x0, x1, y0, y1)
    ('stair-flight', 'G1 stair (16 mm overlap, infill, guards, cupboard)', (5.0, 9.8, -28.75, -27.3)),
    ('lounge-door', 'G1 lounge street door 3.41 -> 3.71 m', (3.2, 4.1, -29.95, -23.5)),
    ('core-door', 'G1 core door swing', (3.9, 5.6, -31.5, -28.3)),
    ('M-corner-west-B', 'M wall corner GF/B (6.74..6.94)', (6.5, 7.2, -30.0, -28.3)),
    ('M-corner-east-B', 'M wall corner B (17.268..17.468)', (17.0, 17.7, -30.0, -28.3)),
    ('M-corner-GF-19', 'M wall corner GF (19.604..19.804)', (19.4, 20.0, -31.4, -28.3)),
    ('M-corner-GF-22', 'M wall corner GF (22.124..22.324; wall ends at 22.597)', (21.9, 22.65, -31.4, -28.3)),
    ('M-wall-GF-33-finish', 'M wall GF-33 lengthened: finish faces along the wall', (3.0, 20.0, -28.75, -28.3)),
    ('SC2-wall-B-ext-16', 'SC2 wall-B-ext-16 raised 2.65 -> 2.80 m to the roof soffit (its own footprint x 15.212..15.412, y -23.591..-20.601)', (15.2, 15.42, -23.6, -20.59)),
    ('SC3-wall-B-ext-09-roof-strip', 'SC3 infill closing the 150 mm slot above wall-B-ext-09 (x 12.777..15.412, y -20.801..-20.601, z -0.35..-0.20) and its finish layers', (12.77, 15.42, -20.85, -20.55)),
    ('M-wall-B-finish', 'M wall B lengthened: finish faces along the wall', (6.5, 17.7, -28.75, -28.3)),
]


def faces(path):
    scene = without_ids(json.loads(Path(path).read_text()))
    return physical_architecture([r for r in scene['meshes'] if r['group'] in ('shell', 'context')])


def key(r):
    return digest(r)


def bbox(r):
    pts = r['face']
    return [min(p[i] for p in pts) for i in range(3)] + [max(p[i] for p in pts) for i in range(3)]


old, new = faces(sys.argv[1]), faces(sys.argv[2])
so, sn = {key(r): r for r in old}, {key(r): r for r in new}
out = []
for side, keys, src in (('removed', set(so) - set(sn), so), ('added', set(sn) - set(so), sn)):
    for k in keys:
        b = bbox(src[k]); zone = None
        for name, cause, (x0, x1, y0, y1) in ZONES:
            if b[0] >= x0 - 1e-6 and b[3] <= x1 + 1e-6 and b[1] >= y0 - 1e-6 and b[4] <= y1 + 1e-6:
                zone = name; break
        out.append((side, zone or 'UNEXPLAINED', src[k].get('part_kind'), src[k].get('room'), [round(v, 3) for v in b]))
count = Counter((s, z) for s, z, *_ in out)
for k, v in sorted(count.items()): print(k, v)
un = [o for o in out if o[1] == 'UNEXPLAINED']
print('UNEXPLAINED', len(un), Counter((o[2], o[3]) for o in un).most_common(30))
Path(sys.argv[3]).write_text(json.dumps(dict(counts={'%s|%s' % k: v for k, v in count.items()}, unexplained=un), indent=1))
