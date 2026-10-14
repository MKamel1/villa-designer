"""Two isolated numerical Blender runs, bound evaluated geometry and lux checks.

Uses the existing workstation graphics lock; renders probe images only.
Relative illuminance differences must be at most 0.001 (0.1 percent).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from archpipe.scene_reproducibility import compare_receipts


def compare_measurements(first, second):
    findings = compare_receipts(first['scene_receipt'], second['scene_receipt'])
    before = {(i,p['room'],p['label']): p for i,p in enumerate(first['points'])}
    after = {(i,p['room'],p['label']): p for i,p in enumerate(second['points'])}
    deltas = []
    if set(before) != set(after) or len(before) != len(first['points']) or len(after) != len(second['points']):
        findings.append('missing or duplicate task points')
    for ident in sorted(set(before) & set(after)):
        a, b = before[ident], after[ident]
        row = dict(index=ident[0]+1,room=ident[1],label=ident[2])
        task_name = str(ident[0]+1)+': '+ident[1]+'/'+ident[2]
        for key in ('position', 'measurement_position', 'required_lux'):
            if a.get(key) != b.get(key): findings.append(task_name+': changed '+key)
        for mode in ('direct', 'total'):
            value = mode+'_lux'
            delta = b[value]-a[value]
            relative = abs(delta)/max(abs(a[value]), 1e-12)
            row[mode+'_delta_lux'] = delta
            row[mode+'_relative_difference'] = relative
            if relative > .001: findings.append(task_name+': '+mode+' drift exceeds 0.1 percent')
        deltas.append(row)
    return dict(passed=not findings, allowance_fraction=.001, findings=findings,
                point_count=len(before), deltas=deltas,
                all_targets_met=first['all_targets_met'] and second['all_targets_met'])


def optical_file_hashes(scene, folder):
    """Require all referenced photometry before expensive scene construction."""
    folder = Path(folder).resolve()
    hashes = {}
    for name in sorted({l['ies'] for l in scene['lights'] if l['type'] == 'ies'}):
        path = (folder/name).resolve()
        if not path.is_relative_to(folder) or not path.is_file():
            raise FileNotFoundError('Missing or escaping scene photometry: '+str(path))
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def runtime_sources():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT/'src/archpipe').rglob('*.py'))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', type=Path, required=True)
    parser.add_argument('--ies-dir', type=Path, required=True)
    parser.add_argument('--library-root', type=Path, required=True)
    parser.add_argument('--blender', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--samples', type=int, default=256)
    parser.add_argument('--compare-recorded', action='store_true', help='Compare completed isolated processes without rerunning Blender')
    args = parser.parse_args()
    root = args.out.resolve(); root.mkdir(parents=True, exist_ok=True)
    from archpipe.execution_context import Tool, project_context
    project_context(ROOT, Path(__file__).resolve(), 'reproducibility',
                              inputs=[args.scene.resolve()], output=root,
                              tools=[Tool('blender', args.blender.resolve(), '4.5.14')])
    scene = json.loads(args.scene.read_text())
    optics = optical_file_hashes(scene, args.ies_dir)
    code = runtime_sources()
    records = []
    if args.compare_recorded:
        old_inputs = json.loads((root/'inputs.json').read_text())
        if old_inputs != dict(photometry_sha256=optics, runtime_sources_sha256=code):
            raise RuntimeError('Recorded replay inputs/runtime differ from current files')
        from archpipe.imported_appearance import digest
        authored_sha256 = digest(scene)
        for salt in ('0', '987654'):
            folder=root/('seed-'+salt)
            process=json.loads((folder/'process.json').read_text())
            if process['exit_code'] != 0 or not process['runtime_sources_unchanged']:
                raise RuntimeError('Recorded Blender process failed')
            if process['log_sha256'] != hashlib.sha256((folder/'process.log').read_bytes()).hexdigest():
                raise RuntimeError('Recorded Blender log changed')
            measurement=json.loads((folder/'lighting-measurements.json').read_text())
            if measurement['scene_receipt']['authored_scene_sha256'] != authored_sha256:
                raise RuntimeError('Recorded replay scene differs from declared authored input')
            records.append(measurement)
        return write_comparison(records, root)
    (root/'inputs.json').write_text(json.dumps(dict(photometry_sha256=optics, runtime_sources_sha256=code), indent=2)+'\n')
    import fcntl
    # Acquire the configured shared graphics lock read-only. Never remove it.
    with Path('/home/omar/archpipe/locks/graphics.lock').open('rb') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for salt in ('0', '987654'):
            out = root/('seed-'+salt)
            if out.exists(): parser.error('refusing to reuse an existing process output: '+str(out))
            out.mkdir()
            command = [str(args.blender.resolve()), '-b', '-t', '8', '--python-exit-code', '1', '--python',
                       str(ROOT/'src/archpipe/blender/villa_scene.py'), '--', '--scene', str(args.scene.resolve()),
                       '--ies-dir', str(args.ies_dir.resolve()), '--library-root', str(args.library_root.resolve()),
                       '--views', 'none', '--measure-lighting', '--samples', str(args.samples), '--out', str(out)]
            env = dict(os.environ, PYTHONHASHSEED=salt, NO_COLOR='1', PYTHONPATH=str(ROOT/'src'),
                       OMP_NUM_THREADS='8', OPENBLAS_NUM_THREADS='8')
            started = time.time()
            with (out/'process.log').open('w') as log:
                result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            record = dict(command=command, hash_seed=salt, exit_code=result.returncode,
                          photometry_sha256=optics, runtime_sources_unchanged=runtime_sources()==code,
                          started=started, finished=time.time(),
                          log_sha256=hashlib.sha256((out/'process.log').read_bytes()).hexdigest())
            (out/'process.json').write_text(json.dumps(record, indent=2)+'\n')
            if runtime_sources()!=code: raise RuntimeError('Runtime source changed during replay')
            if optical_file_hashes(scene, args.ies_dir)!=optics: raise RuntimeError('Photometry changed during replay')
            if result.returncode: raise RuntimeError('Blender failed: '+str(out/'process.log'))
            records.append(json.loads((out/'lighting-measurements.json').read_text()))
            print('Completed process hash seed '+salt, flush=True)
    return write_comparison(records, root)


def write_comparison(records, root):
    comparison = compare_measurements(*records)
    (root/'comparison.json').write_text(json.dumps(comparison, indent=2)+'\n')
    baseline = dict(records[0], baseline_note='New deterministic-pleat baseline. The historical receipt used a '
                    'process-random built-in hash pleat seed; equality with that receipt is not claimed.',
                    reproducibility=comparison)
    (root/'baseline-receipt.json').write_text(json.dumps(baseline, indent=2)+'\n')
    print(json.dumps({k:v for k,v in comparison.items() if k!='deltas'}, indent=2), flush=True)
    return 0 if comparison['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
