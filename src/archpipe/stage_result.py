"""Atomic stage-result contract, shared by CPython and IronPython 2.7.

Records bind actual file inputs and outputs to source provenance. The writer
uses safe_io and completes serialization before publishing. Native hosts use
exactly the same schema and hashing algorithm as portable jobs.
"""
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import time
from archpipe.safe_io import load_json, save_json

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    string_types = (basestring,)
except NameError:
    string_types = (str,)
try:
    missing_file_error = FileNotFoundError
except NameError:
    missing_file_error = IOError

class StageResultError(RuntimeError):
    """Stage result contract violation."""
class StaleInputError(StageResultError):
    """Inputs changed or disappeared."""
StaleStageError = StaleInputError
class IncompleteOutputError(StageResultError):
    """Output missing, empty or modified."""
class FailedStageError(StageResultError):
    """Stage reported failure."""
class CodeDriftError(StageResultError):
    """Source differs from recorded provenance."""


def _path(path, root=None):
    return os.path.realpath(os.path.join(str(root), str(path))) if root is not None else os.path.realpath(str(path))


def _rel_path(path, root):
    absolute = _path(path, root)
    relative = os.path.relpath(absolute, str(root))
    if relative == os.pardir or relative.startswith(os.pardir + os.sep):
        return absolute.replace(os.sep, '/')
    return relative.replace(os.sep, '/')


def digest_file(path):
    """Return the SHA-256 content digest and byte count (SHA means Secure Hash Algorithm)."""
    resolved = _path(path)
    if not os.path.isfile(resolved):
        raise missing_file_error("File not found: %s" % resolved)
    h = hashlib.sha256()
    size = 0
    with open(resolved, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
            size += len(block)
    return h.hexdigest(), size


def _git(args, root):
    try:
        process = subprocess.Popen(['git'] + args, cwd=root,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, _ = process.communicate()
        return stdout.decode('utf-8').strip() if process.returncode == 0 else None
    except OSError:
        return None


def compute_code_provenance(root=None, code_paths=None):
    """Hash source names and bytes; git HEAD and dirty state are audit information."""
    root = _path(root or ROOT)
    if code_paths is None:
        paths = []
        for folder, _, names in os.walk(os.path.join(root, 'src', 'archpipe')):
            paths.extend(os.path.join(folder, n) for n in names if n.endswith('.py'))
        paths.extend(os.path.join(root, n) for n in (
            'ops/workstation/library-manifest.json', 'out/villa/round3/plant-palette.json',
            'spec/villa-site.yaml', 'knowledge/library.json',
            'knowledge/projects/villa-01/brief-requirements.json',
            'knowledge/projects/villa-01/taste.json'))
    else:
        paths = [_path(p, root) for p in code_paths]
    h = hashlib.sha256()
    for path in sorted(set(paths), key=lambda p: _rel_path(p, root)):
        if not os.path.isfile(path):
            continue
        name = _rel_path(path, root).encode('utf-8')
        with open(path, 'rb') as stream:
            data = stream.read()
        h.update(struct.pack('>I', len(name)) + name)
        h.update(struct.pack('>Q', len(data)) + data)
    status = _git(['status', '--porcelain', '--untracked-files=no'], root)
    return {'source_hash': h.hexdigest(), 'git_head': _git(['rev-parse', 'HEAD'], root),
            'git_dirty': bool(status) if status is not None else None,
            'code_paths': sorted(_rel_path(p, root) for p in set(paths) if os.path.isfile(p))}


def build_file_manifest(paths, root=None, require_exists=True):
    root = _path(root or ROOT)
    manifest = {}
    for path in sorted(paths, key=str):
        resolved = _path(path, root)
        exists = os.path.isfile(resolved)
        if not exists and require_exists:
            raise missing_file_error('Required artifact does not exist: %s' % resolved)
        sha, size = digest_file(resolved) if exists else (None, 0)
        manifest[_rel_path(resolved, root)] = {
            'path': resolved, 'sha256': sha, 'size_bytes': size, 'exists': exists}
    return manifest


def evaluate_completeness(expected_outputs, output_manifest, root=None):
    root = _path(root or ROOT)
    keys = [_rel_path(p, root) for p in expected_outputs]
    missing, empty = [], []
    for key in keys:
        info = output_manifest.get(key)
        if not info or not info.get('exists', False):
            missing.append(key)
        elif (info.get('size_bytes') or 0) <= 0:
            empty.append(key)
    return {'complete': not missing and not empty, 'expected_outputs': keys,
            'missing_outputs': missing, 'empty_outputs': empty}


def write_stage_result(stage, record_path, outputs, inputs=(), expected_outputs=None,
                       exit_code=0, status=None, root=None, code_paths=None,
                       metadata=None, started_utc=None, finished_utc=None,
                       input_manifest=None, code_provenance=None):
    """Publish one atomic proof. Only declared expected outputs affect completeness."""
    root = _path(root or ROOT)
    target = _path(record_path, root)
    parent = os.path.dirname(target)
    if not os.path.isdir(parent):
        os.makedirs(parent)
    clean_outputs = [p for p in outputs if _path(p, root) != target]
    expected = clean_outputs if expected_outputs is None else [
        p for p in expected_outputs if _path(p, root) != target]
    if input_manifest is None:
        input_manifest = build_file_manifest(inputs, root)
    output_manifest = build_file_manifest(clean_outputs, root, require_exists=False)
    completeness = evaluate_completeness(expected, output_manifest, root)
    if not completeness['complete'] and exit_code == 0:
        exit_code = 1
    if status is None:
        status = 'ok' if exit_code == 0 and completeness['complete'] else 'fail'
    elif not completeness['complete'] and status == 'ok':
        status = 'fail'
    now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    record = {'_metadata': {
        'description': "Atomic stage result record for pipeline stage '%s'" % stage,
        'structure': 'stage, status, exit_code, code_provenance, inputs, outputs, completeness, metadata',
        'total_items': len(output_manifest), 'last_updated': now},
        'schema': 'stage-result/1', 'stage': stage, 'status': status, 'exit_code': exit_code,
        'started_utc': started_utc or now, 'finished_utc': finished_utc or now,
        'code_provenance': code_provenance if code_provenance is not None else compute_code_provenance(root, code_paths),
        'inputs': input_manifest, 'outputs': output_manifest,
        'overwritten_inputs': sorted(key for key, info in input_manifest.items()
            if key in output_manifest and info['path'] == output_manifest[key]['path']
            and info['sha256'] != output_manifest[key]['sha256']),
        'completeness': completeness, 'metadata': metadata or {}}
    save_json(target, record, indent=2)
    return record


def validate_stage_result(record_or_path, root=None, current_inputs=None,
                          check_code_provenance=False, raise_on_error=True, code_paths=None):
    """Refuse stale results; intentional input overwrites validate as produced outputs."""
    root = _path(root or ROOT)
    def reject(error, reason, record):
        if raise_on_error:
            raise error(reason)
        return False, reason, record
    if not isinstance(record_or_path, dict):
        path = _path(record_or_path, root)
        if not os.path.isfile(path):
            return reject(IncompleteOutputError, 'Stage result record does not exist: %s' % path, {})
        record = load_json(path)
    else:
        record = record_or_path
    name = record.get('stage', 'unnamed_stage')
    complete = record.get('completeness', {})
    if not complete.get('complete', False):
        return reject(IncompleteOutputError,
            "Stage '%s' record is incomplete (missing: %s, empty: %s)" % (
                name, complete.get('missing_outputs', []), complete.get('empty_outputs', [])), record)
    for relative, info in record.get('outputs', {}).items():
        path = info.get('path') or _path(relative, root)
        if not os.path.isfile(path):
            return reject(IncompleteOutputError, "Stage '%s' output is missing on disk: %s" % (name, relative), record)
        sha, size = digest_file(path)
        required = complete.get('expected_outputs', list(record.get('outputs', {})))
        if size == 0 and relative in required:
            return reject(IncompleteOutputError, "Stage '%s' output is empty (0 bytes) on disk: %s" % (name, relative), record)
        if sha != info.get('sha256'):
            return reject(IncompleteOutputError, "Stage '%s' output was modified on disk: %s" % (name, relative), record)
    inputs = record.get('inputs', {})
    for relative, info in inputs.items():
        # An intentional in-place save consumes the old revision and produces
        # a new one. Its current bytes were already checked as an output.
        produced = record.get('outputs', {}).get(relative, {})
        if (relative in record.get('overwritten_inputs', []) and produced.get('exists')
                and produced.get('path') == info.get('path')):
            continue
        path = info.get('path') or _path(relative, root)
        if not os.path.isfile(path):
            return reject(StaleInputError, "Stage '%s' input missing on disk: %s" % (name, relative), record)
        if digest_file(path)[0] != info.get('sha256'):
            return reject(StaleInputError, "Stage '%s' input is stale / modified: %s" % (name, relative), record)
    if current_inputs is not None:
        for path in current_inputs:
            relative = _rel_path(path, root)
            if relative not in inputs:
                return reject(StaleInputError, "Stage '%s' was not executed with required input: %s" % (name, relative), record)
    if check_code_provenance:
        if code_paths is None:
            code_paths = record.get('code_provenance', {}).get('code_paths')
        if record.get('code_provenance', {}).get('source_hash') != compute_code_provenance(root, code_paths)['source_hash']:
            return reject(CodeDriftError, "Stage '%s' code provenance mismatch" % name, record)
    if record.get('exit_code', 0) != 0 or record.get('status') != 'ok':
        return reject(FailedStageError, "Stage '%s' failed with exit code %s (status: %s)" % (
            name, record.get('exit_code', 0), record.get('status')), record)
    return True, 'ok', record


def report_has_failure(report_or_verdict):
    """Inspect a report, verdict, text or object and determine if it indicates failure.

    Returns (has_failure: bool, reasons: list[str]).
    """
    if report_or_verdict is None:
        return (False, [])
    if isinstance(report_or_verdict, bool):
        return (not report_or_verdict, ['Boolean verdict was False'] if not report_or_verdict else [])
    if isinstance(report_or_verdict, (int, float)):
        bad_count = int(report_or_verdict)
        return (bad_count > 0, ['Failure count is {0}'.format(bad_count)] if bad_count > 0 else [])
    if isinstance(report_or_verdict, string_types):
        if re.search('\\b(FAIL|FAILED)\\b', report_or_verdict) or 'VERDICT: FAIL' in report_or_verdict or 'QA FAIL' in report_or_verdict:
            return (True, ['Report text contains failure: {0}'.format(report_or_verdict.strip()[:200])])
        return (False, [])
    if isinstance(report_or_verdict, (list, tuple)):
        reasons = []
        for item in report_or_verdict:
            sub_fail, sub_reasons = report_has_failure(item)
            if sub_fail:
                reasons.extend(sub_reasons)
        return (len(reasons) > 0, reasons)
    if isinstance(report_or_verdict, dict):
        reasons = []
        if report_or_verdict.get('passed') is False:
            reasons.append("Field 'passed' is False")
        if report_or_verdict.get('exit_code', 0) != 0:
            reasons.append("Field 'exit_code' is non-zero ({0})".format(report_or_verdict.get('exit_code')))
        status = report_or_verdict.get('status')
        if status in ('FAIL', 'FAILED', 'fail', 'failed', 'DIAGNOSTIC', 'error'):
            reasons.append("Status is '{0}'".format(status))
        failures = report_or_verdict.get('failures')
        if failures:
            reasons.append('Failures reported: {0}'.format(failures))
        failed = report_or_verdict.get('failed')
        if failed:
            reasons.append('Failed items reported: {0}'.format(failed))
        for chk in report_or_verdict.get('checks', []):
            if isinstance(chk, dict):
                if chk.get('passed') is False or chk.get('status') == 'FAIL' or chk.get('pass') is False:
                    reasons.append('Check failed: {0}'.format(chk.get('check', chk)))
        for v in report_or_verdict.get('verdicts', []):
            if isinstance(v, dict):
                if v.get('pass') is False or v.get('passed') is False or v.get('status') == 'FAIL':
                    reasons.append('Verdict failed: {0}'.format(v.get('check', v)))
        return (len(reasons) > 0, reasons)
    return (False, [])

def enforce_clean_verdict(report_or_verdict, message='Stage report indicates FAIL', exit_code=1):
    """Exit non-zero if the report or verdict contains any FAIL.

    Shared fail-closed helper preventing l0029 (script printing FAIL but returning 0).
    Returns 0 if clean.
    """
    failed, reasons = report_has_failure(report_or_verdict)
    if failed:
        detail = '; '.join(reasons) if reasons else message
        sys.stderr.write('FAIL: {0} ({1})'.format(message, detail) + '\n')
        sys.exit(exit_code)
    return 0

def fail_closed_exit(report_or_verdict, message='Stage report indicates FAIL', exit_code=1):
    """Alias for enforce_clean_verdict."""
    return enforce_clean_verdict(report_or_verdict, message=message, exit_code=exit_code)
