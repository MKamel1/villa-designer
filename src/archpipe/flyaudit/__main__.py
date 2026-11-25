"""python -m archpipe.flyaudit <route.json> --scene <scene.json> [--out knowledge/flyaudit] [--id ROUTE_ID]"""
import argparse, sys
from pathlib import Path
from . import audit, core


def main(argv=None):
    ap = argparse.ArgumentParser(prog='archpipe.flyaudit')
    ap.add_argument('route'); ap.add_argument('--scene', required=True)
    ap.add_argument('--out', default=str(core.ROOT / 'knowledge/flyaudit')); ap.add_argument('--id')
    ap.add_argument('--cache', default=str(core.ROOT / 'out/flyaudit'))
    a = ap.parse_args(argv)
    rep, _ = audit.run(a.route, a.scene, a.out, a.id, cache_dir=a.cache, log=lambda m: print(m, flush=True))
    w = rep['whole']
    print(f"informative {w['informative_share']:.1%}; cats {w['cats']}; bad runs >1 s: {w['bad_runs_over_1s']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
