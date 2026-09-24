"""Content-addressed jobs with process locks, fresh attempts and verified reuse."""
from __future__ import annotations
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import time
import uuid


def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as fh:
        for block in iter(lambda: fh.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',',':'),
                                    allow_nan=False).encode()).hexdigest()


@contextmanager
def process_lock(path):
    """Operating-system lock: process death releases it without a stale PID file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as fh:
        if os.name == 'nt':
            import msvcrt
            if path.stat().st_size == 0:
                fh.write(b'0'); fh.flush()
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == 'nt':
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fh, fcntl.LOCK_UN)


def artifacts_valid(root, records):
    root = Path(root).resolve()
    if not records:
        return False
    for relative, expected in records.items():
        path = (root/relative).resolve()
        if not path.is_relative_to(root) or not path.is_file() or sha_file(path) != expected:
            return False
    return True


def cached_job(root, manifest, action):
    """Execute an action in a fresh directory; only successful intact results reuse."""
    job_id = identity(manifest)
    folder = Path(root)/'jobs'/job_id
    folder.mkdir(parents=True, exist_ok=True)
    with process_lock(folder/'job.lock'):
        saved = folder/'result.json'
        previous = json.loads(saved.read_text()) if saved.is_file() else {}
        if (previous.get('passed') and previous.get('manifest') == manifest
                and artifacts_valid(folder,previous.get('artifacts',{}))):
            return {**previous, 'reused':True}
        attempt = folder/'attempts'/uuid.uuid4().hex
        attempt.mkdir(parents=True)
        (attempt/'manifest.json').write_text(json.dumps(manifest,indent=2))
        started = time.perf_counter()
        result = {'job_id':job_id,'manifest':manifest,'passed':False,'reused':False,
                  'attempt':str(attempt),'artifacts':{}}
        try:
            result['detail'] = action(attempt)
            result['passed'] = True
        except Exception as exc:
            result['error'] = str(exc)
        result['seconds'] = time.perf_counter()-started
        result['finished_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
        result['artifacts'] = {p.relative_to(folder).as_posix():sha_file(p)
                               for p in sorted(attempt.rglob('*')) if p.is_file()}
        temporary = folder/'result.tmp'
        temporary.write_text(json.dumps(result,indent=2))
        temporary.replace(saved)
        return result
