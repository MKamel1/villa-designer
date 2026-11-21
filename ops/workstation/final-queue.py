# Reference copy of the flythrough final-queue job (was work/laneA/out/flythrough/final-queue.py, a gitignored path).
# Hard-coded to laneA paths: adapt ROOT/OUT/PYTHON before reuse. For new queues prefer jobq.
"""One bounded walkthrough job; delegates every acceptance decision to existing CLI."""
from pathlib import Path
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = Path('/home/omar/archpipe/work/laneA')
OUT = ROOT / 'out/flythrough'
PYTHON = '/home/omar/archpipe/envs/b16842c6f2161c9d/venv/bin/python'
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from archpipe.safe_io import save_bytes
from scripts.flythrough import require_inputs


def save(value):
    save_bytes(OUT / 'final/queue-status.json', (json.dumps(value, indent=2) + '\n').encode())


def commands():
    # Reuse the existing renderer's receipt admission for all earlier frames.
    ranges = [(0, 335)] + [(first, min(first + 47, 719)) for first in range(336, 720, 48)]
    assert {index for first, last in ranges for index in range(first, last + 1)} == set(range(720))
    result = []
    for first, last in ranges:
        frames = ','.join(map(str, range(first, last + 1)))
        result.append((f'frames-{first:04d}-{last:04d}', ['final', '--frames', frames]))
    result.extend([('temporal-all-719', ['temporal']), ('encode-with-production-qa', ['encode', '--stage', 'final'])])
    return result


def main():
    jobs = commands()
    if '--plan' in sys.argv:
        print(json.dumps([{'name': name, 'operation': args[0]} for name, args in jobs], indent=2))
        return 0
    lock = (OUT / 'final/queue.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    path = require_inputs(OUT)
    state = dict(pid=os.getpid(), path_sha256=path['sha256'],
                 program_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 status='RUNNING', completed=[], started_unix=time.time())
    environment = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), NO_COLOR='1')
    try:
        for name, args in jobs:
            require_inputs(OUT)
            command = [PYTHON, str(ROOT / 'scripts/flythrough.py'), *args]
            log = OUT / 'final' / ('queue-' + name + '.log')
            state.update(active=name, command=command, log=str(log))
            save(state)
            started = time.monotonic()
            with log.open('w') as stream:
                result = subprocess.run(command, cwd=ROOT, env=environment,
                                        stdout=stream, stderr=subprocess.STDOUT)
            row = dict(name=name, exit_code=result.returncode,
                       seconds=time.monotonic() - started, log=str(log))
            state['completed'].append(row)
            save(state)
            if result.returncode:
                raise RuntimeError(f'{name} exited {result.returncode}; inspect {log}')
        state.update(status='NUMERIC_GATES_AND_ENCODE_COMPLETE_VISUAL_REVIEW_PENDING',
                     active=None, finished_unix=time.time())
        save(state)
        return 0
    except BaseException as error:
        state.update(status='FAILED', error=str(error), finished_unix=time.time())
        save(state)
        raise


if __name__ == '__main__':
    raise SystemExit(main())
