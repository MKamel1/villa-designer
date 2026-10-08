"""Measure the real scene producer and require byte identity to a saved baseline.

Uses sorted standard JSON without provenance stamping or rendering. Baselines
are full producer output, never generated extracts or shared output edits.
"""
import argparse
import cProfile
import hashlib
import json
from pathlib import Path
import time

from archpipe.concept import villa_render


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--record-baseline', action='store_true')
    parser.add_argument('--profile', type=Path)
    parser.add_argument('--metrics', type=Path)
    args = parser.parse_args()
    if args.record_baseline and args.baseline.exists():
        parser.error('refusing to overwrite an existing baseline')
    if not args.record_baseline and not args.baseline.is_file():
        parser.error('baseline must be captured from the starting source before edits')
    source_before = villa_render.source_provenance()
    profile = cProfile.Profile() if args.profile else None
    start = time.perf_counter()
    if profile:
        profile.enable()
    scene = villa_render.build()
    if profile:
        profile.disable()
    elapsed = time.perf_counter()-start
    source_after = villa_render.source_provenance()
    if source_before['source_hash'] != source_after['source_hash']:
        print('Refusing benchmark: source changed during build; freeze the producer and retry.', flush=True)
        return 1
    raw = json.dumps(scene, sort_keys=True).encode()
    digest = hashlib.sha256(raw).hexdigest()
    if args.record_baseline:
        args.baseline.write_bytes(raw)
        identical = True
    else:
        # Compare every byte in blocks without loading another full scene.
        with args.baseline.open('rb') as baseline:
            identical = True
            for index in range(0, len(raw), 1024*1024):
                if baseline.read(1024*1024) != raw[index:index+1024*1024]:
                    identical = False
                    break
            identical = identical and not baseline.read(1)
    if profile:
        profile.dump_stats(str(args.profile))
    result = dict(build_seconds=elapsed, profiled=bool(profile), scene_bytes=len(raw),
                  sha256=digest, byte_identical=identical, source_hash=source_after['source_hash'])
    print(json.dumps(result, indent=2), flush=True)
    if args.metrics:
        args.metrics.write_text(json.dumps(result, indent=2)+'\n')
    return 0 if identical else 1


if __name__ == '__main__':
    raise SystemExit(main())
