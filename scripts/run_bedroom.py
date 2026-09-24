"""Run the bedroom capability example, with fresh outputs and explicit gates.

Use --skip-revit to resume downstream work on a model whose build report
matches the current specification. Revit and rendering remain sequential
and only generated files under out/ are replaced.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from archpipe.review_extract import review_model


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def input_hashes():
    paths = [ROOT/'spec/bedroom-test.yaml', ROOT/'requirements.txt',ROOT/'requirements-worker.txt']
    paths += list((ROOT/'src/archpipe').glob('*.py'))
    paths += list((ROOT/'src/archpipe/blender').glob('*.py'))
    paths += [ROOT/'revit'/name for name in ['build_bedroom.py','extract_model.py','export_views.py']]
    paths += [ROOT/'scripts'/name for name in ['run_bedroom.py','make_bedroom_spec.py',
              'check_bedroom.py','make_render_input.py','lighting_report.py','compare_lux.py',
              'render_remote.py','workstation.py','worker_entry.py']]
    paths += list((ROOT/'ops/workstation').glob('*.py'))
    return {str(p.relative_to(ROOT)).replace('\\','/'): digest(p) for p in sorted(paths)}


def artifacts_match(records):
    return bool(records) and all((ROOT/'out'/name).is_file() and
               digest(ROOT/'out'/name) == record['sha256'] for name, record in records.items())


def run(argv, label, env=None, expected=None, timeout=360):
    started = time.time_ns()
    res = subprocess.run([str(v) for v in argv], cwd=ROOT, env=env,
                         stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding='utf-8',
                         errors='replace', timeout=timeout)
    logs = ROOT / 'out/run-logs'
    logs.mkdir(parents=True, exist_ok=True)
    (logs / (label + '.log')).write_text(res.stdout + res.stderr, encoding='utf-8')
    if res.returncode:
        raise RuntimeError(label + ' failed; see ' + str(logs / (label + '.log')))
    if expected and (not expected.is_file() or expected.stat().st_mtime_ns < started):
        raise RuntimeError(label + ' produced no fresh output; exit zero is insufficient')
    print('PASS ' + label, flush=True)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--skip-revit', action='store_true')
    ap.add_argument('--resume', action='store_true', help='reuse only content-verified stages')
    ap.add_argument('--samples', type=int, default=512)
    a = ap.parse_args()
    if not 32 <= a.samples <= 4096:
        ap.error('samples must be between 32 and 4096')
    out = ROOT / 'out'
    out.mkdir(exist_ok=True)
    acceptance = out / 'bedroom-acceptance.json'
    inputs = input_hashes()
    previous = json.loads(acceptance.read_text()) if acceptance.is_file() else {}
    # Reuse requires the actual worker environment as well as project
    # inputs. Changed applications, packages or assets invalidate evidence.
    try:
        run([sys.executable,ROOT/'scripts/workstation.py','status'], 'worker_status',
            expected=out/'workstation/status-latest.json',timeout=120)
        runtime = json.loads((out/'workstation/status-latest.json').read_text())['runtime']
    except Exception as exc:
        failure = {'passed':False,'stage':'worker_status','error':str(exc),
                   'input_hashes':inputs,'samples':a.samples,
                   'scope':'capability example, not villa approval',
                   'finished_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
        acceptance.write_text(json.dumps(failure,indent=2),encoding='utf-8')
        print('FAIL '+str(exc),file=sys.stderr)
        return 1
    runtime_id = hashlib.sha256(json.dumps(runtime,sort_keys=True).encode()).hexdigest()
    if (a.resume and previous.get('passed') and previous.get('input_hashes') == inputs
            and previous.get('worker_runtime') == runtime_id
            and previous.get('samples') == a.samples and artifacts_match(previous.get('artifacts', {}))):
        print('PASS unchanged inputs and artifacts; reused complete verified run')
        print(acceptance)
        return 0
    revit_inputs = {k:v for k,v in inputs.items() if k.startswith('revit/') or
                    k in ['spec/bedroom-test.yaml', 'scripts/make_bedroom_spec.py',
                          'src/archpipe/furniture.py']}
    if (a.resume and previous.get('revit_inputs') == revit_inputs and
            artifacts_match(previous.get('revit_artifacts', {}))):
        a.skip_revit = True
    result = {'passed': False, 'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'scope': 'capability example, not villa approval', 'checks': {}, 'artifacts': {},
              'input_hashes': inputs, 'samples': a.samples, 'reused_revit': a.skip_revit,
              'worker_runtime':runtime_id}
    acceptance.write_text(json.dumps(result, indent=2))
    env = {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONPATH': str(ROOT / 'src')}
    try:
        run([sys.executable, ROOT/'scripts/make_bedroom_spec.py'], 'spec', env)
        env.update(ARCHPIPE_SPEC=str(out/'bedroom-spec.json'),
                   ARCHPIPE_FAMILY_DIR=str(out/'families'),
                   ARCHPIPE_IES_DIR=r'C:\ProgramData\Autodesk\RVT 2027\IES',
                   ARCHPIPE_BEDROOM_OUT=str(out/'revit2027/bedroom.rvt'),
                   ARCHPIPE_BUILD_REPORT=str(out/'bedroom_build.json'),
                   ARCHPIPE_MODEL=str(out/'revit2027/bedroom.rvt'),
                   ARCHPIPE_VIEWS_OUT=str(out/'bedroom-native'),
                   ARCHPIPE_EXTRACT_OUT=str(out/'bedroom-from-revit.json'))
        pr = Path(os.environ['APPDATA'])/'pyRevit-Master/bin/pyrevit.exe'
        if not a.skip_revit:
            for script, expected in [
                ('build_bedroom.py', out/'bedroom_build.json'),
                ('export_views.py', out/'bedroom-native/views-report.json'),
                ('extract_model.py', out/'bedroom-from-revit.json')]:
                run([pr, 'run', ROOT/'revit'/script, '--revit=2027'], script[:-3], env, expected)
        build = json.loads((out/'bedroom_build.json').read_text())
        if build.get('spec_sha256') != digest(out/'bedroom-spec.json'):
            raise RuntimeError('Saved model build does not match the current spec; rebuild required')
        if build.get('errors') or any(not x.get('placed') for k in ['openings','furniture','lighting'] for x in build[k]):
            raise RuntimeError('Revit build report contains errors or unplaced items')
        result['revit_inputs'] = revit_inputs
        result['revit_artifacts'] = {name: {'sha256': digest(out/name)} for name in [
            'revit2027/bedroom.rvt', 'bedroom-from-revit.json', 'bedroom_build.json',
            'bedroom-native/views-report.json', 'bedroom-native/bedroom-native-views.pdf']}
        run([sys.executable, ROOT/'scripts/check_bedroom.py'], 'roundtrip', env)
        extract = json.loads((out/'bedroom-from-revit.json').read_text())
        reviewed = review_model(extract, scope='room')
        (out/'bedroom-review.json').write_text(json.dumps(reviewed, indent=2), encoding='utf-8')
        if not reviewed['passed']:
            raise RuntimeError('Room review still has warnings or violations; see out/bedroom-review.json')
        result['checks']['room_review'] = 'pass; dwelling-context checks explicitly excluded'
        finishes = {f['role']: [p['name'] for p in f['paint']] for f in extract['finishes']}
        for role, name in {'walls':'painted','floor':'timber','ceiling':'plaster'}.items():
            if 'archpipe '+name not in finishes.get(role, []):
                raise RuntimeError('Missing authored finish: '+role)
        result['checks']['finishes'] = finishes
        views = json.loads((out/'bedroom-native/views-report.json').read_text())
        by_id = {m['id']: m for m in extract['markup']}
        note = by_id.get(views['markup']['text_id'], {})
        cloud = by_id.get(views['markup']['cloud_id'], {})
        # Revit stores TextNote line breaks as carriage returns, not LF.
        # Compare logical lines while still requiring the actual text.
        if note.get('text', '').strip().splitlines() != views['markup']['text'].strip().splitlines() or cloud.get('boundary') != views['markup']['boundary_mm']:
            raise RuntimeError('Synthetic markup failed read-back')
        result['checks']['markup'] = 'text and four-sided revision cloud read back from saved Revit model'
        import pymupdf
        pdf = out/'bedroom-native/bedroom-native-views.pdf'
        with pymupdf.open(pdf) as doc:
            if len(doc) != 6 or any(len(p.get_drawings()) < 10 for p in doc):
                raise RuntimeError('Native drawing export is missing views or geometry')
            for index, page in enumerate(doc):
                page.get_pixmap(matrix=pymupdf.Matrix(1.25,1.25)).save(str(out/f'bedroom-native/page-{index+1}.png'))
        result['checks']['native_views'] = views['views']
        # Worker jobs bind each IES filename to a hashed deployed asset.
        run([sys.executable, ROOT/'scripts/make_render_input.py', '--ies-dir', 'assets/ies'], 'render_input', env)
        run([sys.executable, ROOT/'scripts/lighting_report.py'], 'lighting', env)
        result['checks']['lighting'] = json.loads((out/'bedroom-lighting.json').read_text())
        run([sys.executable,ROOT/'scripts/workstation.py','bedroom','--samples',str(a.samples),
             '--resolution','1600x1000'], 'worker_bedroom',env,
             out/'workstation/bedroom-latest.json',timeout=1800)
        batch = json.loads((out/'workstation/bedroom-latest.json').read_text())
        if not batch['passed']:
            raise RuntimeError('Workstation batch did not pass')
        bundle = out/'workstation'/batch['batch_id']
        result['checks']['workstation'] = {'batch_id':batch['batch_id'],'jobs':len(batch['jobs']),
                                         'reused':batch['reused']}
        for job in batch['jobs']:
            folder = bundle/job['job_id'][:16]
            kind = job['manifest']['kind']
            if kind=='render':
                camera = job['manifest']['parameters']['camera']
                shutil.copyfile(folder/'render.png',out/('bedroom-'+camera+'.png'))
                if camera=='bed':
                    shutil.copyfile(folder/'render.png',out/'bedroom.png')
                    shutil.copyfile(folder/'render.log',out/'run-logs/remote-build_scene.py.log')
            elif kind=='probe':
                shutil.copyfile(folder/'lux.json',out/'lux-direct.json')
                shutil.copyfile(folder/'probe.log',out/'run-logs/remote-measure_lux.py.log')
            elif kind=='radiance':
                shutil.copyfile(folder/'radiance-report.json',out/'radiance-report.json')
                result['checks']['radiance'] = job['detail']
        run([sys.executable, ROOT/'scripts/compare_lux.py', out/'lux-direct.json',
             '--extract', out/'bedroom-render.json'], 'photometry_agreement', env)
        result['checks']['photometry_agreement'] = 'see out/run-logs/photometry_agreement.log'
        for name in ['revit2027/bedroom.rvt','bedroom-from-revit.json','bedroom-native/bedroom-native-views.pdf',
                     'bedroom.png','bedroom-bed.png','bedroom-window.png','bedroom-overview.png',
                     'bedroom-review.json','bedroom-lighting.json','bedroom-render.json',
                     'lux-direct.json','radiance-report.json']:
            p = out/name
            result['artifacts'][name] = {'bytes': p.stat().st_size, 'sha256': digest(p)}
        result['spec_sha256'] = digest(ROOT/'spec/bedroom-test.yaml')
        if input_hashes() != inputs:
            raise RuntimeError('Source changed during this run; rerun to verify one consistent version')
        result['passed'] = True
        result['limitations'] = ['Five furniture items are manufacturer-neutral procedural detail, not specified commercial products; the chair is an existing native family.',
            'Paint hue is extracted; optical reflectances are stated assumptions, not measurements.',
            'Procedural material grain/weave are presentation assumptions. Native light-source display webs are excluded; photometric data governs fixture optics.',
            'Radiance daylight is an illustrative normalized overcast sky, not site/weather analysis; working-plane exclusions use conservative furniture bounds.',
            'Photometry is joined from the authored specification; third-party family light definitions may override Revit parameters.',
            'Direct-only lighting has no compliance verdict for uniformity; no real site or jurisdiction is specified.',
            'Synthetic markup tests transport; it is not client approval.']
    except Exception as exc:
        result['error'] = str(exc)
        print('FAIL', exc, file=sys.stderr)
    result['finished_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    acceptance.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(acceptance)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    lock = ROOT/'out/bedroom-run.lock'
    lock.parent.mkdir(exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise SystemExit('Another bedroom run owns out/bedroom-run.lock; inspect its process before retrying.')
    try:
        with os.fdopen(fd, 'w') as fh:
            fh.write(str(os.getpid()))
        raise SystemExit(main())
    finally:
        lock.unlink(missing_ok=True)
