"""Render and enforce the registered production grey-card reciprocity check.

Uses the workstation shared graphics lock, a pinned Blender runtime and five
small renders. --analyse-only replays retained PNGs without using the GPU.
"""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from archpipe.execution_context import Tool, project_context, write_record
from archpipe.render_qa import grey_card_check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'out/wbcheck/current')
    parser.add_argument('--blender', type=Path, default=Path('/home/omar/opt/blender/blender'))
    parser.add_argument('--analyse-only', action='store_true')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if not args.analyse_only:
        context = project_context(ROOT, Path(__file__).resolve(), 'white-balance-reciprocity',
                                  output=out, tools=[Tool('blender', args.blender.resolve(), '4.5.14')])
        write_record(context, out / 'execution-context.json')
        sources = [ROOT / 'src/archpipe/blender' / name for name in
                   ('grey_card.py', 'photoreal.py', 'build_scene.py', 'villa_scene.py', 'sky_compat.py')]
        hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
        command = [str(args.blender.resolve()), '-b', '-t', '8', '--python-exit-code', '1',
                   '-P', str(sources[0]), '--', str(out)]
        with Path('/home/omar/archpipe/locks/graphics.lock').open('rb') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            with (out / 'render.log').open('w') as log:
                status = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT).returncode
        (out / 'process.json').write_text(json.dumps(dict(command=command, exit_code=status, sources=hashes), indent=2)+'\n')
        if status:
            return status
        if any(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != value for name, value in hashes.items()):
            raise RuntimeError('Colour-path sources changed during measurement')
    rows = json.loads((out / 'readings.json').read_text())
    if [(r['kind'], r['temperature']) for r in rows] != [('lamp', t) for t in (2700, 3000, 4300, 5500)] + [('daylight', 5500)]:
        raise ValueError('The complete registered grey-card set is required')
    for row in rows:
        row.update(grey_card_check(out / row['png']))
    report = dict(passed=all(row['passed'] for row in rows), cases=rows)
    (out / 'guard.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(passed=report['passed'], report=str(out / 'guard.json'))))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
