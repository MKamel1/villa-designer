# -*- coding: utf-8 -*-
"""Command-only native stage proof. No Autodesk imports; IronPython 2.7 syntax.

Inputs are frozen before work because native drawing export updates its input
model in place. Completed models survive any later report or image failure.
"""
import glob
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
from archpipe import safe_io, stage_result


def files(paths):
    """Expand explicitly declared input directories; never traverse user assets."""
    result = []
    for path in paths:
        if not path:
            continue
        if os.path.isdir(path):
            for folder, _, names in os.walk(path):
                result.extend(os.path.join(folder, n) for n in names if n.lower().endswith(('.rfa', '.ies')))
        elif os.path.isfile(path):
            result.append(path)
    return sorted(set(result))


def report(path):
    return safe_io.load_json(path) if os.path.isfile(path) else {}


def images(folder):
    return sorted(glob.glob(os.path.join(folder, '*.png')))


def run(stage, action, record_path, inputs, outputs, failed, app):
    """Run only from a __main__ guard; preserve a failed proof when action raises."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    inputs = files(inputs)
    frozen = stage_result.build_file_manifest(inputs, root=root)
    code = sorted(glob.glob(os.path.join(root, 'revit', '*.py'))) + [
        os.path.join(root, 'src', 'archpipe', 'stage_result.py'),
        os.path.join(root, 'src', 'archpipe', 'safe_io.py')]
    provenance = stage_result.compute_code_provenance(root=root, code_paths=code)
    error = None
    value = None
    try:
        value = action()
    except Exception as exc:
        error = '%s: %s' % (type(exc).__name__, exc)
    runtime = {'python': sys.version, 'revit_version': str(app.VersionNumber),
               'revit_build': str(app.VersionBuild)}
    record = stage_result.write_stage_result(stage, record_path=record_path,
        inputs=inputs, outputs=outputs(value), root=root, code_paths=code,
        input_manifest=frozen, code_provenance=provenance,
        exit_code=1 if error or failed(value) else 0,
        metadata={'runtime': runtime, 'error': error,
                  'runtime_proof': 'requires live Revit; portable tests are static only'})
    return stage_result.enforce_clean_verdict(record, message=stage + ' failed')
