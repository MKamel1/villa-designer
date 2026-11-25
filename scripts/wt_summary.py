"""usage: python scripts/wt_summary.py <audit dir> [<baseline audit dir>]: wall-dominated share per room and mode, bad runs outside the 360s."""
import json, sys, collections
def load(d): return json.load(open(d+'/frames.json'))
def stats(fr):
    by = collections.defaultdict(collections.Counter); tot = collections.Counter()
    for r in fr:
        for k in (r['room'] or '-', '*ALL*'):
            by[k]['n'] += 1; by[k][r['cat']] += 1; by[k]['m-'+r['mode']] += 1; by[k]['w-'+r['mode']] += r['cat'] in ('wall_dominated', 'backward', 'blocked')
    return by
def runs_outside(fr, fps=24, stride=2, min_s=1.0):
    out = []; cur = []
    def flush():
        if cur and len(cur)*stride/fps > min_s and any(r['mode'] != 'sweeping' for r in cur): out.append((cur[0]['i'], len(cur)*stride/fps, cur[0]['room'], collections.Counter(r['mode'] for r in cur)))
    for r in fr:
        if r['cat'] in ('wall_dominated', 'backward', 'blocked') and r['mode'] != 'sweeping': cur.append(r)
        else: flush(); cur = []
    flush(); return out
if __name__ == '__main__':
    a = load(sys.argv[1]); A = stats(a); B = stats(load(sys.argv[2])) if len(sys.argv) > 2 else None
    print('room                    wall before -> after   (sweep/walk/hold wall-bad share after)')
    for k in sorted(A, key=lambda k: -A[k]['wall_dominated']/A[k]['n']):
        c = A[k]; f = lambda c, m: (c['w-'+m]/c['m-'+m]) if c['m-'+m] else float('nan')
        b = f"{B[k]['wall_dominated']/B[k]['n']:.2f}" if B and k in B else '  - '
        print(f"{k:22s} {b} -> {c['wall_dominated']/c['n']:.2f}   sweep {f(c,'sweeping'):.2f} walk {f(c,'walking'):.2f} hold {f(c,'holding'):.2f}")
    r = runs_outside(a); print('runs >1 s of bad frames that are not pure sweeps:', len(r), sum(x[1] for x in r), 's')
    for x in r[:60]: print('  ', x)
