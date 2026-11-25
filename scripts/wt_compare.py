"""usage: python scripts/wt_compare.py <before audit dir> <after audit dir> <path.json of the after route> -> markdown table per room.

Wall-dominated share of the room's frames, informative share, full 360 (audit's own check), lens of the room's 360, from the two flyaudit reports."""
import json, sys
b = json.load(open(sys.argv[1]+'/report.json')); a = json.load(open(sys.argv[2]+'/report.json'))
path = json.load(open(sys.argv[3])); lens = {}
for f in path['frames']:
    if f['phase'] == 'turn' and f['station']: lens[f['station']] = min(lens.get(f['station'], 99), f['camera']['lens_mm'])
fb = json.load(open(sys.argv[1]+'/frames.json')); fa = json.load(open(sys.argv[2]+'/frames.json'))
def sweep(fr, room):
    s = [r for r in fr if r['room'] == room and r['mode'] in ('sweeping', 'holding')]
    return sum(r['cat'] == 'wall_dominated' for r in s)/len(s) if s else float('nan')
print('| room | lens of the 360 | wall-dominated, room before -> after | wall-dominated in the 360 before -> after | informative before -> after | full 360 before -> after |')
print('|---|---|---|---|---|---|')
rows = sorted(a['rooms'], key=lambda k: -(b['rooms'][k]['cats'].get('wall_dominated', 0) if b['rooms'][k]['cats'] else 0))
for k in rows:
    cb, ca = b['rooms'][k]['cats'], a['rooms'][k]['cats']
    f = lambda c, key: f"{c.get(key, 0):.0%}" if c else '-'
    l = lens.get(k); tag = f'{l:.0f} mm' if l else 'transit (walk-and-look)'
    print(f"| {k} | {tag} | {f(cb,'wall_dominated')} -> {f(ca,'wall_dominated')} | {sweep(fb,k):.0%} -> {sweep(fa,k):.0%} | {f(cb,'informative')} -> {f(ca,'informative')} | {'yes' if b['rooms'][k]['full_360']['full'] else 'no'} -> {'yes' if a['rooms'][k]['full_360']['full'] else 'no (transit)' if not l else 'no'} |")
wb, wa = b['whole'], a['whole']
print(); print('whole route:', {k: (wb['cats'][k], wa['cats'][k]) for k in wb['cats']})
